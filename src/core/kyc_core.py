"""
TITAN V8.1 SINGULARITY - KYC Core Engine
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
from typing import Optional, Dict, List, Any, Callable, Tuple
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
    RAISE_EYEBROWS = "raise_eyebrows"
    FROWN = "frown"
    HEAD_TILT_LEFT = "head_tilt_left"
    HEAD_TILT_RIGHT = "head_tilt_right"
    CLOSE_EYES = "close_eyes"
    WINK_LEFT = "wink_left"
    WINK_RIGHT = "wink_right"


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


# ═══════════════════════════════════════════════════════════════════════════
# V7.6 P0 UPGRADE: LIVENESS DETECTION BYPASS
# Counter common liveness challenges used by KYC providers
# ═══════════════════════════════════════════════════════════════════════════

class LivenessDetectionBypass:
    """
    V7.6: Bypasses liveness detection challenges used by KYC providers.
    
    Common liveness challenges:
    - Blink detection (2-3 blinks in sequence)
    - Smile detection (natural smile progression)
    - Head turn (left/right/up/down)
    - Random text reading (lip movement)
    - 3D depth check (parallax movement)
    
    This engine provides motion sequences to pass each challenge type.
    """
    
    # Challenge timing profiles per provider
    PROVIDER_TIMING = {
        'onfido': {
            'blink_count': 2,
            'blink_interval_ms': 800,
            'head_turn_duration_ms': 1500,
            'smile_ramp_ms': 600,
        },
        'jumio': {
            'blink_count': 3,
            'blink_interval_ms': 700,
            'head_turn_duration_ms': 2000,
            'smile_ramp_ms': 800,
        },
        'veriff': {
            'blink_count': 2,
            'blink_interval_ms': 900,
            'head_turn_duration_ms': 1800,
            'smile_ramp_ms': 700,
        },
        'sumsub': {
            'blink_count': 2,
            'blink_interval_ms': 750,
            'head_turn_duration_ms': 1600,
            'smile_ramp_ms': 650,
        },
        'default': {
            'blink_count': 2,
            'blink_interval_ms': 800,
            'head_turn_duration_ms': 1500,
            'smile_ramp_ms': 600,
        },
    }
    
    def __init__(self, provider: str = 'default'):
        self.provider = provider
        self.timing = self.PROVIDER_TIMING.get(provider, self.PROVIDER_TIMING['default'])
        self._motion_queue = []
    
    def generate_blink_sequence(self) -> List[Dict]:
        """Generate natural blink sequence keyframes."""
        sequence = []
        for i in range(self.timing['blink_count']):
            # Each blink: eyes open -> close -> open
            base_time = i * self.timing['blink_interval_ms']
            sequence.extend([
                {'time_ms': base_time, 'eyes_closed': 0.0},
                {'time_ms': base_time + 80, 'eyes_closed': 0.9},  # Fast close
                {'time_ms': base_time + 160, 'eyes_closed': 0.0},  # Open
            ])
        return sequence
    
    def generate_head_turn_sequence(self, direction: str = 'left') -> List[Dict]:
        """Generate head turn sequence (left, right, up, down, or circular)."""
        duration = self.timing['head_turn_duration_ms']
        
        if direction == 'circular':
            # Full circular motion for 3D depth check
            return [
                {'time_ms': 0, 'yaw': 0, 'pitch': 0},
                {'time_ms': duration * 0.25, 'yaw': -15, 'pitch': 0},
                {'time_ms': duration * 0.5, 'yaw': 0, 'pitch': -10},
                {'time_ms': duration * 0.75, 'yaw': 15, 'pitch': 0},
                {'time_ms': duration, 'yaw': 0, 'pitch': 10},
                {'time_ms': duration * 1.25, 'yaw': 0, 'pitch': 0},
            ]
        
        # Direction mapping
        angles = {
            'left': {'yaw': -20, 'pitch': 0},
            'right': {'yaw': 20, 'pitch': 0},
            'up': {'yaw': 0, 'pitch': -15},
            'down': {'yaw': 0, 'pitch': 15},
        }
        target = angles.get(direction, angles['left'])
        
        return [
            {'time_ms': 0, 'yaw': 0, 'pitch': 0},
            {'time_ms': duration * 0.4, 'yaw': target['yaw'], 'pitch': target['pitch']},
            {'time_ms': duration * 0.6, 'yaw': target['yaw'], 'pitch': target['pitch']},
            {'time_ms': duration, 'yaw': 0, 'pitch': 0},
        ]
    
    def generate_smile_sequence(self) -> List[Dict]:
        """Generate natural smile progression."""
        ramp = self.timing['smile_ramp_ms']
        return [
            {'time_ms': 0, 'smile': 0.0, 'mouth_open': 0.0},
            {'time_ms': ramp * 0.3, 'smile': 0.2, 'mouth_open': 0.05},
            {'time_ms': ramp * 0.6, 'smile': 0.5, 'mouth_open': 0.1},
            {'time_ms': ramp, 'smile': 0.8, 'mouth_open': 0.15},
            {'time_ms': ramp * 1.5, 'smile': 0.9, 'mouth_open': 0.2},
            {'time_ms': ramp * 2.5, 'smile': 0.5, 'mouth_open': 0.1},
            {'time_ms': ramp * 3, 'smile': 0.0, 'mouth_open': 0.0},
        ]
    
    def generate_3d_depth_sequence(self) -> List[Dict]:
        """Generate subtle parallax movement for 3D depth verification."""
        return [
            {'time_ms': 0, 'x_offset': 0, 'y_offset': 0, 'scale': 1.0},
            {'time_ms': 500, 'x_offset': -3, 'y_offset': 0, 'scale': 1.01},
            {'time_ms': 1000, 'x_offset': 0, 'y_offset': -2, 'scale': 1.02},
            {'time_ms': 1500, 'x_offset': 3, 'y_offset': 0, 'scale': 1.01},
            {'time_ms': 2000, 'x_offset': 0, 'y_offset': 2, 'scale': 1.0},
            {'time_ms': 2500, 'x_offset': 0, 'y_offset': 0, 'scale': 1.0},
        ]
    
    def get_full_liveness_sequence(self, challenges: List[str]) -> List[Dict]:
        """Generate complete sequence for list of challenges."""
        sequence = []
        current_time = 0
        
        for challenge in challenges:
            if challenge == 'blink':
                frames = self.generate_blink_sequence()
            elif challenge.startswith('turn_'):
                direction = challenge.replace('turn_', '')
                frames = self.generate_head_turn_sequence(direction)
            elif challenge == 'smile':
                frames = self.generate_smile_sequence()
            elif challenge == '3d_depth':
                frames = self.generate_3d_depth_sequence()
            else:
                continue
            
            # Offset times and add to sequence
            for frame in frames:
                frame['time_ms'] += current_time
                sequence.append(frame)
            
            # Add gap between challenges
            if frames:
                current_time = max(f['time_ms'] for f in frames) + 500
        
        return sequence


# ═══════════════════════════════════════════════════════════════════════════
# V7.6 P0 UPGRADE: KYC PROVIDER DETECTOR
# Auto-detect which KYC provider is being used
# ═══════════════════════════════════════════════════════════════════════════

class KYCProviderDetector:
    """
    V7.6: Auto-detect KYC provider from page content.
    
    Different providers have different:
    - Challenge sequences
    - Timing requirements
    - Detection methods
    - Bypass strategies
    
    Detection via DOM signatures, API endpoints, and JS fingerprints.
    """
    
    # Provider signatures in page content
    SIGNATURES = {
        'onfido': {
            'dom': ['onfido-sdk', 'onfido-mount', 'onfido__'],
            'scripts': ['onfido.min.js', 'onfido-sdk'],
            'api': ['api.onfido.com', 'sdk.onfido.com'],
        },
        'jumio': {
            'dom': ['jumio-', 'netverify', 'jumioiframe'],
            'scripts': ['jumio', 'netverify'],
            'api': ['netverify.com', 'jumio.com'],
        },
        'veriff': {
            'dom': ['veriff-', 'veriff__', 'Veriff'],
            'scripts': ['veriff', 'cdn.veriff.me'],
            'api': ['api.veriff.me', 'magic.veriff.me'],
        },
        'sumsub': {
            'dom': ['sumsub-', 'idensic', 'WebSDK'],
            'scripts': ['sumsub', 'idensic', 'websdk'],
            'api': ['api.sumsub.com', 'test-api.sumsub.com'],
        },
        'shufti': {
            'dom': ['shuftipro', 'shufti-'],
            'scripts': ['shuftipro'],
            'api': ['api.shuftipro.com'],
        },
        'persona': {
            'dom': ['persona-', 'withpersona'],
            'scripts': ['persona'],
            'api': ['withpersona.com'],
        },
        'idenfy': {
            'dom': ['idenfy-', 'iDenfySDK'],
            'scripts': ['idenfy', 'sdk.idenfy.com'],
            'api': ['ivs.idenfy.com'],
        },
    }
    
    # Provider-specific capabilities
    CAPABILITIES = {
        'onfido': {
            'liveness_type': 'video',
            'document_capture': True,
            'nfc_supported': True,
            'challenges': ['blink', 'smile', 'turn_left', 'turn_right'],
            'bypass_difficulty': 'high',
        },
        'jumio': {
            'liveness_type': 'photo_sequence',
            'document_capture': True,
            'nfc_supported': True,
            'challenges': ['blink', '3d_depth'],
            'bypass_difficulty': 'medium',
        },
        'veriff': {
            'liveness_type': 'video',
            'document_capture': True,
            'nfc_supported': False,
            'challenges': ['blink', 'smile', 'turn_left', 'turn_right', 'turn_up'],
            'bypass_difficulty': 'high',
        },
        'sumsub': {
            'liveness_type': 'photo_sequence',
            'document_capture': True,
            'nfc_supported': True,
            'challenges': ['blink', 'smile'],
            'bypass_difficulty': 'medium',
        },
        'default': {
            'liveness_type': 'photo',
            'document_capture': True,
            'nfc_supported': False,
            'challenges': ['blink'],
            'bypass_difficulty': 'low',
        },
    }
    
    @classmethod
    def detect_from_html(cls, html_content: str) -> Tuple[str, float]:
        """
        Detect KYC provider from HTML content.
        
        Returns: (provider_name, confidence)
        """
        html_lower = html_content.lower()
        scores = {}
        
        for provider, sig in cls.SIGNATURES.items():
            score = 0
            
            # Check DOM signatures
            for dom_sig in sig['dom']:
                if dom_sig.lower() in html_lower:
                    score += 3
            
            # Check script signatures
            for script_sig in sig['scripts']:
                if script_sig.lower() in html_lower:
                    score += 2
            
            # Check API signatures
            for api_sig in sig['api']:
                if api_sig.lower() in html_lower:
                    score += 4
            
            if score > 0:
                scores[provider] = score
        
        if not scores:
            return ('unknown', 0.0)
        
        # Get highest scoring provider
        best_provider = max(scores, key=scores.get)
        max_possible = len(cls.SIGNATURES[best_provider]['dom']) * 3 + \
                       len(cls.SIGNATURES[best_provider]['scripts']) * 2 + \
                       len(cls.SIGNATURES[best_provider]['api']) * 4
        confidence = min(scores[best_provider] / max_possible, 1.0)
        
        return (best_provider, confidence)
    
    @classmethod
    def detect_from_network(cls, requests: List[Dict]) -> Tuple[str, float]:
        """
        Detect KYC provider from network requests.
        
        Args:
            requests: List of {url, method, headers} dicts
        """
        for provider, sig in cls.SIGNATURES.items():
            for req in requests:
                url = req.get('url', '').lower()
                for api_endpoint in sig['api']:
                    if api_endpoint.lower() in url:
                        return (provider, 0.95)
        
        return ('unknown', 0.0)
    
    @classmethod
    def get_bypass_strategy(cls, provider: str) -> Dict:
        """Get optimal bypass strategy for detected provider."""
        caps = cls.CAPABILITIES.get(provider, cls.CAPABILITIES['default'])
        
        return {
            'provider': provider,
            'liveness_type': caps['liveness_type'],
            'expected_challenges': caps['challenges'],
            'use_video_reenactment': caps['liveness_type'] == 'video',
            'recommended_motions': cls._get_recommended_motions(provider),
            'timing_profile': LivenessDetectionBypass.PROVIDER_TIMING.get(
                provider, LivenessDetectionBypass.PROVIDER_TIMING['default']
            ),
        }
    
    @classmethod
    def _get_recommended_motions(cls, provider: str) -> List[str]:
        """Get recommended motion files for provider."""
        caps = cls.CAPABILITIES.get(provider, cls.CAPABILITIES['default'])
        motions = []
        
        for challenge in caps.get('challenges', []):
            if challenge == 'blink':
                motions.append('natural_blink_x2.mp4')
            elif challenge == 'smile':
                motions.append('warm_smile.mp4')
            elif challenge.startswith('turn_'):
                motions.append(f'head_{challenge}.mp4')
            elif challenge == '3d_depth':
                motions.append('subtle_parallax.mp4')
        
        return motions


# ═══════════════════════════════════════════════════════════════════════════
# V7.6 P0 UPGRADE: KYC SESSION MANAGER
# Full KYC session orchestration with retry logic
# ═══════════════════════════════════════════════════════════════════════════

class KYCSessionManager:
    """
    V7.6: Orchestrates complete KYC bypass sessions.
    
    Manages:
    - Provider detection
    - Document preparation
    - Liveness challenge handling
    - Failure recovery with different strategies
    - Session timing to appear natural
    """
    
    def __init__(self, controller: 'KYCController'):
        self.controller = controller
        self.provider = 'unknown'
        self.provider_confidence = 0.0
        self.current_stage = 'init'
        self.attempts = 0
        self.max_attempts = 3
        self.session_start = None
        self._event_log = []
    
    def start_session(self, html_content: str = None) -> Dict:
        """
        Start a KYC bypass session.
        
        Args:
            html_content: Optional page HTML for provider detection
        """
        import time
        self.session_start = time.time()
        self.attempts = 0
        
        # Detect provider
        if html_content:
            self.provider, self.provider_confidence = \
                KYCProviderDetector.detect_from_html(html_content)
            self._log_event('provider_detected', {
                'provider': self.provider,
                'confidence': self.provider_confidence
            })
        
        # Get bypass strategy
        strategy = KYCProviderDetector.get_bypass_strategy(self.provider)
        
        # Initialize liveness bypass
        self.liveness_bypass = LivenessDetectionBypass(self.provider)
        
        self.current_stage = 'ready'
        return {
            'status': 'ready',
            'provider': self.provider,
            'confidence': self.provider_confidence,
            'strategy': strategy,
        }
    
    def handle_document_stage(self, document_path: str) -> Dict:
        """Handle document capture stage."""
        self.current_stage = 'document'
        self._log_event('document_stage', {'document': document_path})
        
        # Stream document image to virtual camera
        success = self.controller.stream_image(document_path)
        
        return {
            'status': 'success' if success else 'failed',
            'stage': 'document',
        }
    
    def handle_liveness_stage(self, face_image: str, 
                               challenges: List[str] = None) -> Dict:
        """
        Handle liveness detection stage.
        
        Args:
            face_image: Path to face image for reenactment
            challenges: List of expected challenges (auto-detected if None)
        """
        self.current_stage = 'liveness'
        self.attempts += 1
        
        # Use provider-specific challenges if not specified
        if challenges is None:
            strategy = KYCProviderDetector.get_bypass_strategy(self.provider)
            challenges = strategy['expected_challenges']
        
        self._log_event('liveness_stage', {
            'attempt': self.attempts,
            'challenges': challenges
        })
        
        # Generate motion sequence
        sequence = self.liveness_bypass.get_full_liveness_sequence(challenges)
        
        # Determine motion type based on challenges
        motion_type = MotionType.BLINK_NATURAL
        if 'smile' in challenges:
            motion_type = MotionType.FULL_RANGE
        elif any(c.startswith('turn_') for c in challenges):
            motion_type = MotionType.HEAD_NOD
        
        # Start reenactment
        config = ReenactmentConfig(
            source_image=face_image,
            motion_type=motion_type,
            expression_scale=0.8,
            pose_scale=0.7,
        )
        
        success = self.controller.start_reenactment(config)
        
        return {
            'status': 'streaming' if success else 'failed',
            'stage': 'liveness',
            'attempt': self.attempts,
            'motion_sequence': sequence,
        }
    
    def handle_failure(self, error_type: str) -> Dict:
        """
        Handle KYC failure with recovery strategy.
        
        Args:
            error_type: Type of failure (liveness_failed, document_rejected, timeout)
        """
        self._log_event('failure', {'type': error_type, 'attempt': self.attempts})
        
        if self.attempts >= self.max_attempts:
            return {
                'status': 'max_attempts_reached',
                'action': 'abort',
                'total_attempts': self.attempts,
            }
        
        # Determine recovery strategy
        recovery = {
            'liveness_failed': {
                'action': 'retry_different_motion',
                'suggestion': 'Use slower, more natural movements',
                'wait_seconds': 5,
            },
            'document_rejected': {
                'action': 'retry_different_angle',
                'suggestion': 'Adjust document lighting and angle',
                'wait_seconds': 3,
            },
            'timeout': {
                'action': 'retry_immediately',
                'suggestion': 'Check network and camera connection',
                'wait_seconds': 2,
            },
            'face_not_detected': {
                'action': 'adjust_position',
                'suggestion': 'Center face in frame, improve lighting',
                'wait_seconds': 3,
            },
        }
        
        return {
            'status': 'recovery',
            'error_type': error_type,
            **recovery.get(error_type, recovery['timeout']),
            'remaining_attempts': self.max_attempts - self.attempts,
        }
    
    def end_session(self, success: bool = False) -> Dict:
        """End the KYC session and return summary."""
        import time
        
        self.controller.stop_stream()
        duration = time.time() - self.session_start if self.session_start else 0
        
        summary = {
            'status': 'success' if success else 'failed',
            'provider': self.provider,
            'total_attempts': self.attempts,
            'duration_seconds': round(duration, 1),
            'event_log': self._event_log,
        }
        
        self._log_event('session_end', summary)
        self.current_stage = 'ended'
        
        return summary
    
    def _log_event(self, event_type: str, data: Dict):
        """Log session event for debugging."""
        import time
        self._event_log.append({
            'timestamp': time.time(),
            'type': event_type,
            'data': data,
        })


# V7.6 Convenience exports
def create_liveness_bypass(provider: str = 'default'):
    """V7.6: Create liveness detection bypass"""
    return LivenessDetectionBypass(provider)

def detect_kyc_provider(html_content: str) -> Tuple[str, float]:
    """V7.6: Detect KYC provider from HTML"""
    return KYCProviderDetector.detect_from_html(html_content)

def get_kyc_bypass_strategy(provider: str) -> Dict:
    """V7.6: Get bypass strategy for KYC provider"""
    return KYCProviderDetector.get_bypass_strategy(provider)
