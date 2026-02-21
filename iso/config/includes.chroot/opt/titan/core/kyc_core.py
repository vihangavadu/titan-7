"""
TITAN V7.0 SINGULARITY - KYC Core Engine
The Mask: System-level virtual camera controller for identity verification bypass

This is the CORE LOGIC for the KYC GUI App.
Controls v4l2loopback at the SYSTEM level - works with ANY app (Browser, Zoom, Telegram).
NOT coupled to browser context - this is a standalone virtual camera controller.
"""

import os
import subprocess
import signal
import json
import shutil
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, List, Any, Callable
import threading
import time
import logging

logger = logging.getLogger("TITAN-V7-KYC-CORE")


class CameraState(Enum):
    """Virtual camera state"""
    STOPPED = "stopped"
    STREAMING = "streaming"
    PAUSED = "paused"
    ERROR = "error"


class MotionType(Enum):
    """Pre-recorded motion types for liveness challenges"""
    NEUTRAL = "neutral"
    BLINK = "blink"
    BLINK_TWICE = "blink_twice"
    SMILE = "smile"
    HEAD_LEFT = "head_left"
    HEAD_RIGHT = "head_right"
    HEAD_NOD = "head_nod"
    LOOK_UP = "look_up"
    LOOK_DOWN = "look_down"
    OPEN_MOUTH = "open_mouth"


@dataclass
class ReenactmentConfig:
    """Configuration for neural reenactment"""
    source_image: str  # Path to ID photo or generated face
    motion_type: MotionType = MotionType.NEUTRAL
    output_fps: int = 30
    output_resolution: tuple = (1280, 720)
    loop: bool = True
    
    # Reenactment parameters (sliders in GUI)
    head_rotation_intensity: float = 1.0  # 0.0 - 2.0
    expression_intensity: float = 1.0     # 0.0 - 2.0
    blink_frequency: float = 0.3          # blinks per second
    micro_movement: float = 0.1           # subtle head movement


@dataclass
class VirtualCameraConfig:
    """Virtual camera device configuration"""
    device_path: str = "/dev/video2"
    device_name: str = "Integrated Webcam"
    width: int = 1280
    height: int = 720
    fps: int = 30
    pixel_format: str = "yuyv422"


class KYCController:
    """
    The Mask - System-level virtual camera controller.
    
    This controller:
    1. Manages v4l2loopback kernel module
    2. Streams video to virtual camera device
    3. Works with ANY application that uses webcam
    4. Provides GUI sliders for real-time reenactment control
    
    Architecture:
    - v4l2loopback creates /dev/video2 (virtual camera)
    - ffmpeg streams video to /dev/video2
    - Any app (Browser, Zoom, etc.) sees /dev/video2 as real webcam
    - Neural reenactment generates video from static image + motion
    """
    
    MOTION_ASSETS_PATH = Path("/opt/titan/assets/motions")
    MODELS_PATH = Path("/opt/titan/models")
    
    def __init__(self, config: Optional[VirtualCameraConfig] = None):
        self.config = config or VirtualCameraConfig()
        self.state = CameraState.STOPPED
        self.ffmpeg_process: Optional[subprocess.Popen] = None
        self.reenactment_process: Optional[subprocess.Popen] = None
        self._stream_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # Current reenactment config
        self.current_reenactment: Optional[ReenactmentConfig] = None
        
        # Callbacks for GUI updates
        self.on_state_change: Optional[Callable[[CameraState], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
    
    def setup_virtual_camera(self) -> bool:
        """
        Initialize v4l2loopback virtual camera device.
        Must be called before streaming.
        """
        try:
            # Check if v4l2loopback is already loaded
            result = subprocess.run(
                ["lsmod"],
                capture_output=True,
                text=True
            )
            
            if "v4l2loopback" not in result.stdout:
                # Load v4l2loopback module
                subprocess.run([
                    "modprobe", "v4l2loopback",
                    f"devices=1",
                    f"video_nr={self.config.device_path.split('video')[-1]}",
                    f"card_label={self.config.device_name}",
                    "exclusive_caps=1"
                ], check=True)
            
            # Verify device exists
            if not os.path.exists(self.config.device_path):
                if self.on_error:
                    self.on_error(f"Virtual camera device {self.config.device_path} not found")
                return False
            
            return True
            
        except subprocess.CalledProcessError as e:
            if self.on_error:
                self.on_error(f"Failed to setup virtual camera: {e}")
            return False
        except Exception as e:
            if self.on_error:
                self.on_error(f"Error setting up virtual camera: {e}")
            return False
    
    def stream_video(self, video_path: str, loop: bool = True) -> bool:
        """
        Stream a video file to the virtual camera.
        
        Args:
            video_path: Path to video file
            loop: Whether to loop the video
        """
        if not os.path.exists(video_path):
            if self.on_error:
                self.on_error(f"Video file not found: {video_path}")
            return False
        
        self.stop_stream()
        
        try:
            loop_args = ["-stream_loop", "-1"] if loop else []
            
            cmd = [
                "ffmpeg",
                "-re",  # Read input at native frame rate
                *loop_args,
                "-i", video_path,
                "-vf", f"scale={self.config.width}:{self.config.height}",
                "-f", "v4l2",
                "-pix_fmt", self.config.pixel_format,
                "-r", str(self.config.fps),
                self.config.device_path
            ]
            
            self.ffmpeg_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE
            )
            
            self._set_state(CameraState.STREAMING)
            return True
            
        except Exception as e:
            if self.on_error:
                self.on_error(f"Failed to start stream: {e}")
            self._set_state(CameraState.ERROR)
            return False
    
    def stream_image(self, image_path: str) -> bool:
        """
        Stream a static image to the virtual camera.
        Useful for document verification where no motion is needed.
        """
        if not os.path.exists(image_path):
            if self.on_error:
                self.on_error(f"Image file not found: {image_path}")
            return False
        
        self.stop_stream()
        
        try:
            cmd = [
                "ffmpeg",
                "-loop", "1",
                "-re",
                "-i", image_path,
                "-vf", f"scale={self.config.width}:{self.config.height}",
                "-f", "v4l2",
                "-pix_fmt", self.config.pixel_format,
                "-r", str(self.config.fps),
                self.config.device_path
            ]
            
            self.ffmpeg_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE
            )
            
            self._set_state(CameraState.STREAMING)
            return True
            
        except Exception as e:
            if self.on_error:
                self.on_error(f"Failed to stream image: {e}")
            self._set_state(CameraState.ERROR)
            return False
    
    def start_reenactment(self, config: ReenactmentConfig) -> bool:
        """
        Start neural reenactment - animate a static face image.
        
        This uses LivePortrait or similar model to:
        1. Take a source image (ID photo)
        2. Apply motion from driving video
        3. Output animated video to virtual camera
        
        The GUI provides sliders to control:
        - Head rotation intensity
        - Expression intensity
        - Blink frequency
        - Micro-movements
        """
        if not os.path.exists(config.source_image):
            if self.on_error:
                self.on_error(f"Source image not found: {config.source_image}")
            return False
        
        self.stop_stream()
        self.current_reenactment = config
        
        # Get motion driving video
        motion_video = self._get_motion_video(config.motion_type)
        if not motion_video:
            if self.on_error:
                self.on_error(f"Motion asset not found for: {config.motion_type.value}")
            return False
        
        try:
            # Start reenactment in background thread
            self._stop_event.clear()
            self._stream_thread = threading.Thread(
                target=self._reenactment_loop,
                args=(config, motion_video)
            )
            self._stream_thread.start()
            
            self._set_state(CameraState.STREAMING)
            return True
            
        except Exception as e:
            if self.on_error:
                self.on_error(f"Failed to start reenactment: {e}")
            self._set_state(CameraState.ERROR)
            return False
    
    def _reenactment_loop(self, config: ReenactmentConfig, motion_video: str):
        """
        Background thread for continuous reenactment.
        Generates video frames and pipes to ffmpeg -> v4l2loopback.
        """
        try:
            # Create named pipe for video output
            pipe_path = "/tmp/titan_reenact_pipe"
            if os.path.exists(pipe_path):
                os.remove(pipe_path)
            os.mkfifo(pipe_path)
            
            # Start ffmpeg to read from pipe and output to v4l2
            ffmpeg_cmd = [
                "ffmpeg",
                "-f", "rawvideo",
                "-pix_fmt", "rgb24",
                "-s", f"{config.output_resolution[0]}x{config.output_resolution[1]}",
                "-r", str(config.output_fps),
                "-i", pipe_path,
                "-f", "v4l2",
                "-pix_fmt", self.config.pixel_format,
                self.config.device_path
            ]
            
            self.ffmpeg_process = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # Start reenactment engine (LivePortrait if installed, motion video fallback)
            self._run_reenactment_engine(config, motion_video, pipe_path)
            
        except Exception as e:
            if self.on_error:
                self.on_error(f"Reenactment error: {e}")
            self._set_state(CameraState.ERROR)
        finally:
            if os.path.exists("/tmp/titan_reenact_pipe"):
                os.remove("/tmp/titan_reenact_pipe")
    
    def _run_reenactment_engine(self, config: ReenactmentConfig, 
                                 motion_video: str, output_pipe: str):
        """
        Run the neural reenactment engine.
        
        Two operational modes:
        1. LIVE MODE: LivePortrait model installed at /opt/titan/models/liveportrait
           → Real neural reenactment: source image + driving motion = animated face
        2. FALLBACK MODE: No model installed
           → Streams pre-recorded motion video via ffmpeg (degraded but functional)
        """
        # Check if LivePortrait model exists
        model_path = self.MODELS_PATH / "liveportrait"
        
        if model_path.exists():
            # Real reenactment with LivePortrait
            cmd = [
                "python3", "-m", "liveportrait.inference",
                "--source", config.source_image,
                "--driving", motion_video,
                "--output", output_pipe,
                "--head_rotation", str(config.head_rotation_intensity),
                "--expression", str(config.expression_intensity),
                "--fps", str(config.output_fps)
            ]
            
            self.reenactment_process = subprocess.Popen(
                cmd,
                cwd=str(model_path),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE
            )
            
            # Wait for process or stop event
            while not self._stop_event.is_set():
                if self.reenactment_process.poll() is not None:
                    if config.loop:
                        # Restart for looping
                        self.reenactment_process = subprocess.Popen(
                            cmd,
                            cwd=str(model_path),
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.PIPE
                        )
                    else:
                        break
                time.sleep(0.1)
        else:
            # V7.5 FIX: Fallback mode — stream pre-recorded motion video directly
            # Used when LivePortrait model is not installed on this system
            logger.info("[*] LivePortrait not found, using fallback motion video mode")
            ffmpeg_cmd = [
                "ffmpeg",
                "-stream_loop", "-1" if config.loop else "0",
                "-i", motion_video,
                "-f", "rawvideo",
                "-pix_fmt", "rgb24",
                "-s", f"{config.output_resolution[0]}x{config.output_resolution[1]}",
                output_pipe
            ]
            
            ffmpeg_process = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            while not self._stop_event.is_set():
                if ffmpeg_process.poll() is not None:
                    break
                time.sleep(0.1)
            
            ffmpeg_process.terminate()
    
    def _get_motion_video(self, motion_type: MotionType) -> Optional[str]:
        """Get path to motion driving video"""
        motion_file = self.MOTION_ASSETS_PATH / f"{motion_type.value}.mp4"
        
        if motion_file.exists():
            return str(motion_file)
        
        # Check for pkl format (LivePortrait motion data)
        pkl_file = self.MOTION_ASSETS_PATH / f"{motion_type.value}.pkl"
        if pkl_file.exists():
            return str(pkl_file)
        
        return None
    
    def update_reenactment_params(self, 
                                   head_rotation: Optional[float] = None,
                                   expression: Optional[float] = None,
                                   blink_freq: Optional[float] = None,
                                   micro_movement: Optional[float] = None):
        """
        Update reenactment parameters in real-time (from GUI sliders).
        """
        if not self.current_reenactment:
            return
        
        if head_rotation is not None:
            self.current_reenactment.head_rotation_intensity = head_rotation
        if expression is not None:
            self.current_reenactment.expression_intensity = expression
        if blink_freq is not None:
            self.current_reenactment.blink_frequency = blink_freq
        if micro_movement is not None:
            self.current_reenactment.micro_movement = micro_movement
        
        # Parameters are applied on next reenactment restart
        # Real-time updates require LivePortrait's streaming API (if available)
    
    def stop_stream(self):
        """Stop all streaming"""
        self._stop_event.set()
        
        if self.ffmpeg_process:
            self.ffmpeg_process.terminate()
            try:
                self.ffmpeg_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.ffmpeg_process.kill()
            self.ffmpeg_process = None
        
        if self.reenactment_process:
            self.reenactment_process.terminate()
            try:
                self.reenactment_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.reenactment_process.kill()
            self.reenactment_process = None
        
        if self._stream_thread and self._stream_thread.is_alive():
            self._stream_thread.join(timeout=3)
        
        self._set_state(CameraState.STOPPED)
    
    def pause_stream(self):
        """Pause streaming (send black frames)"""
        if self.state == CameraState.STREAMING:
            # Send SIGSTOP to ffmpeg
            if self.ffmpeg_process:
                self.ffmpeg_process.send_signal(signal.SIGSTOP)
            self._set_state(CameraState.PAUSED)
    
    def resume_stream(self):
        """Resume paused stream"""
        if self.state == CameraState.PAUSED:
            if self.ffmpeg_process:
                self.ffmpeg_process.send_signal(signal.SIGCONT)
            self._set_state(CameraState.STREAMING)
    
    def _set_state(self, state: CameraState):
        """Update state and notify callback"""
        self.state = state
        if self.on_state_change:
            self.on_state_change(state)
    
    def get_available_cameras(self) -> List[Dict[str, str]]:
        """List all video devices (real and virtual)"""
        cameras = []
        
        for i in range(10):
            device = f"/dev/video{i}"
            if os.path.exists(device):
                # Get device name
                try:
                    result = subprocess.run(
                        ["v4l2-ctl", "-d", device, "--info"],
                        capture_output=True,
                        text=True
                    )
                    name = "Unknown"
                    for line in result.stdout.split('\n'):
                        if "Card type" in line:
                            name = line.split(':')[1].strip()
                            break
                    
                    cameras.append({
                        "device": device,
                        "name": name,
                        "is_virtual": "v4l2loopback" in result.stdout or 
                                     device == self.config.device_path
                    })
                except Exception:
                    cameras.append({
                        "device": device,
                        "name": "Unknown",
                        "is_virtual": device == self.config.device_path
                    })
        
        return cameras
    
    def cleanup(self):
        """Cleanup resources"""
        self.stop_stream()
        
        # Optionally unload v4l2loopback
        # subprocess.run(["modprobe", "-r", "v4l2loopback"])
    
    @staticmethod
    def get_available_motions() -> List[Dict[str, Any]]:
        """Get list of available motion presets for GUI dropdown"""
        return [
            {
                "type": MotionType.NEUTRAL,
                "name": "Neutral",
                "description": "Subtle idle movement, natural breathing",
                "duration": "continuous"
            },
            {
                "type": MotionType.BLINK,
                "name": "Single Blink",
                "description": "Natural single eye blink",
                "duration": "2s"
            },
            {
                "type": MotionType.BLINK_TWICE,
                "name": "Blink Twice",
                "description": "Two consecutive blinks (common liveness check)",
                "duration": "3s"
            },
            {
                "type": MotionType.SMILE,
                "name": "Smile",
                "description": "Natural smile expression",
                "duration": "2s"
            },
            {
                "type": MotionType.HEAD_LEFT,
                "name": "Turn Head Left",
                "description": "Turn head to the left",
                "duration": "3s"
            },
            {
                "type": MotionType.HEAD_RIGHT,
                "name": "Turn Head Right",
                "description": "Turn head to the right",
                "duration": "3s"
            },
            {
                "type": MotionType.HEAD_NOD,
                "name": "Nod Yes/No",
                "description": "Nodding motion",
                "duration": "3s"
            },
            {
                "type": MotionType.LOOK_UP,
                "name": "Look Up",
                "description": "Look upward",
                "duration": "2s"
            },
            {
                "type": MotionType.LOOK_DOWN,
                "name": "Look Down",
                "description": "Look downward",
                "duration": "2s"
            },
            {
                "type": MotionType.OPEN_MOUTH,
                "name": "Open Mouth",
                "description": "Open mouth (common liveness check)",
                "duration": "2s"
            },
        ]


class IntegrityShield:
    """
    Bypass integrity checks that detect virtual cameras.
    
    Some KYC apps check for:
    - v4l2loopback module
    - Virtual camera devices
    - Screen recording
    - Root/jailbreak
    
    This class provides LD_PRELOAD hooks to hide these.
    """
    
    SHIELD_LIB_PATH = Path("/opt/titan/lib/integrity_shield.so")
    
    @staticmethod
    def is_available() -> bool:
        """Check if integrity shield library is available"""
        return IntegrityShield.SHIELD_LIB_PATH.exists()
    
    @staticmethod
    def get_env_vars() -> Dict[str, str]:
        """Get environment variables to enable integrity shield"""
        if not IntegrityShield.is_available():
            return {}
        
        return {
            "LD_PRELOAD": str(IntegrityShield.SHIELD_LIB_PATH),
            "TITAN_HIDE_VIRTUAL_CAM": "1",
            "TITAN_HIDE_V4L2LOOPBACK": "1"
        }
    
    @staticmethod
    def launch_with_shield(command: List[str], **kwargs) -> subprocess.Popen:
        """Launch a process with integrity shield enabled"""
        env = os.environ.copy()
        env.update(IntegrityShield.get_env_vars())
        
        return subprocess.Popen(command, env=env, **kwargs)
