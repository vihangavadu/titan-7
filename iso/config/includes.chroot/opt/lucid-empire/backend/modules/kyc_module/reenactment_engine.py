#!/usr/bin/env python3
"""
TITAN V8.1 SINGULARITY :: KYC REENACTMENT ENGINE
Authority: Dva.12 | Status: TITAN_ACTIVE

Production-ready neural face reenactment using LivePortrait.
Generates liveness-check videos from a static ID photo + driving motion.

Architecture:
    1. LivePortrait model generates animated frames from source image + motion
    2. ffmpeg encodes frames to v4l2loopback virtual camera
    3. Supports: neutral, blink, smile, head_turn, nod motions
    4. Fallback: pre-recorded motion video streamed via ffmpeg (degraded mode)
"""

import os
import subprocess
import time
import logging
import shutil
from pathlib import Path
from typing import Optional

logger = logging.getLogger("TITAN-KYC-REENACT")

MODELS_DIR = Path("/opt/lucid-empire/models/LivePortrait")
ASSETS_DIR = Path(os.path.dirname(os.path.abspath(__file__))) / "assets"
TITAN_ASSETS_DIR = Path("/opt/titan/assets/motions")


class ReenactmentEngine:
    """
    Production neural face reenactment engine.
    
    Uses LivePortrait (or FasterLivePortrait with TensorRT) to animate
    a static face image with driving motion data, outputting video
    suitable for streaming to a virtual webcam via v4l2loopback.
    
    Operational modes:
        1. LIVE: LivePortrait model installed → real-time neural reenactment
        2. PRERECORDED: No model → streams pre-recorded motion videos with ffmpeg
    """
    
    DRIVING_ASSETS = {
        "neutral": "driving_neutral",
        "smile": "driving_smile",
        "blink": "driving_blink",
        "blink_twice": "driving_blink_twice",
        "head_turn": "driving_turn",
        "head_nod": "driving_nod",
        "look_up": "driving_look_up",
        "look_down": "driving_look_down",
    }
    
    def __init__(self, model_path: str = None):
        self.model_path = Path(model_path) if model_path else MODELS_DIR
        self.initialized = False
        self.mode = "unknown"  # "live" or "prerecorded"
        self._process: Optional[subprocess.Popen] = None
    
    def initialize_engine(self) -> bool:
        """
        Initialize the reenactment engine.
        Detects whether LivePortrait model is available.
        
        Returns:
            True if engine is ready (either live or prerecorded mode)
        """
        # Check for LivePortrait installation
        lp_script = self.model_path / "inference.py"
        lp_module = shutil.which("liveportrait") or shutil.which("faster_liveportrait")
        
        if lp_script.exists() or lp_module:
            self.mode = "live"
            logger.info(f"LivePortrait engine found at {self.model_path} — LIVE mode")
        else:
            # Check for pre-recorded motion assets as fallback
            has_assets = any(
                self._find_driving_asset(motion) is not None
                for motion in ["neutral", "blink", "head_turn"]
            )
            if has_assets:
                self.mode = "prerecorded"
                logger.info("LivePortrait not found — PRERECORDED mode (motion videos)")
            else:
                logger.error("No reenactment engine or motion assets found")
                self.initialized = False
                return False
        
        self.initialized = True
        return True
    
    def generate_liveness_video(
        self,
        source_image_path: str,
        driving_video_type: str = "neutral",
        output_path: str = None,
        fps: int = 30,
        duration: float = 8.0,
        loop: bool = True,
    ) -> Optional[str]:
        """
        Generate a reenactment video for KYC liveness verification.
        
        Args:
            source_image_path: Path to the ID photo or generated face
            driving_video_type: Motion type (neutral/smile/blink/head_turn/head_nod)
            output_path: Output video path (auto-generated if None)
            fps: Output frame rate
            duration: Video duration in seconds
            loop: Whether to loop the driving motion
            
        Returns:
            Path to generated video, or None on failure
        """
        if not self.initialized:
            if not self.initialize_engine():
                return None
        
        if not os.path.exists(source_image_path):
            logger.error(f"Source image not found: {source_image_path}")
            return None
        
        if not output_path:
            output_path = f"/tmp/kyc_reenact_{driving_video_type}_{int(time.time())}.mp4"
        
        driving_asset = self._find_driving_asset(driving_video_type)
        if not driving_asset:
            logger.error(f"No driving asset found for motion: {driving_video_type}")
            return None
        
        if self.mode == "live":
            return self._generate_live(source_image_path, driving_asset, output_path, fps, duration)
        else:
            return self._generate_prerecorded(driving_asset, output_path, fps, duration, loop)
    
    def _generate_live(
        self, source: str, driving: str, output: str, fps: int, duration: float
    ) -> Optional[str]:
        """Generate video using LivePortrait neural reenactment."""
        try:
            # Try FasterLivePortrait CLI first (TensorRT accelerated)
            faster_lp = shutil.which("faster_liveportrait")
            if faster_lp:
                cmd = [
                    faster_lp,
                    "--source", source,
                    "--driving", driving,
                    "--output", output,
                    "--fps", str(fps),
                    "--max-duration", str(duration),
                ]
            else:
                # Fall back to standard LivePortrait Python module
                cmd = [
                    "python3", "-m", "liveportrait.inference",
                    "--source", source,
                    "--driving", driving,
                    "--output", output,
                    "--fps", str(fps),
                ]
            
            logger.info(f"Running LivePortrait: {' '.join(cmd[:6])}...")
            self._process = subprocess.Popen(
                cmd,
                cwd=str(self.model_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            
            stdout, stderr = self._process.communicate(timeout=120)
            
            if self._process.returncode == 0 and os.path.exists(output):
                logger.info(f"Reenactment complete: {output}")
                return output
            else:
                logger.error(f"LivePortrait failed (rc={self._process.returncode}): {stderr.decode()[:500]}")
                return None
                
        except subprocess.TimeoutExpired:
            logger.error("LivePortrait inference timed out (120s)")
            if self._process:
                self._process.kill()
            return None
        except Exception as e:
            logger.error(f"LivePortrait error: {e}")
            return None
    
    def _generate_prerecorded(
        self, driving: str, output: str, fps: int, duration: float, loop: bool
    ) -> Optional[str]:
        """Generate video by re-encoding a pre-recorded motion asset with ffmpeg."""
        try:
            loop_args = ["-stream_loop", "-1"] if loop else []
            cmd = [
                "ffmpeg", "-y",
                *loop_args,
                "-i", driving,
                "-t", str(duration),
                "-r", str(fps),
                "-c:v", "libx264",
                "-preset", "fast",
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
                output,
            ]
            
            logger.info(f"Generating from pre-recorded: {driving}")
            result = subprocess.run(cmd, capture_output=True, timeout=60)
            
            if result.returncode == 0 and os.path.exists(output):
                logger.info(f"Pre-recorded video ready: {output}")
                return output
            else:
                logger.error(f"ffmpeg failed: {result.stderr.decode()[:300]}")
                return None
                
        except subprocess.TimeoutExpired:
            logger.error("ffmpeg encoding timed out")
            return None
        except Exception as e:
            logger.error(f"Pre-recorded generation error: {e}")
            return None
    
    def stream_to_camera(
        self, video_path: str, device: str = "/dev/video10", loop: bool = True
    ) -> Optional[subprocess.Popen]:
        """
        Stream a generated video directly to v4l2loopback virtual camera.
        
        Returns:
            ffmpeg Popen process handle (caller manages lifecycle)
        """
        if not os.path.exists(video_path):
            logger.error(f"Video not found: {video_path}")
            return None
        
        loop_args = ["-stream_loop", "-1"] if loop else []
        cmd = [
            "ffmpeg",
            "-re",
            *loop_args,
            "-i", video_path,
            "-f", "v4l2",
            "-pix_fmt", "yuyv422",
            device,
        ]
        
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            logger.info(f"Streaming to {device} (PID: {proc.pid})")
            return proc
        except Exception as e:
            logger.error(f"Failed to stream: {e}")
            return None
    
    def stop(self):
        """Stop any running reenactment or streaming process."""
        if self._process and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
            self._process = None
    
    def _find_driving_asset(self, motion_type: str) -> Optional[str]:
        """Find a driving motion asset (video or pkl) for the given type."""
        base_name = self.DRIVING_ASSETS.get(motion_type, f"driving_{motion_type}")
        
        # Search in multiple locations
        search_dirs = [ASSETS_DIR, TITAN_ASSETS_DIR, self.model_path / "assets"]
        extensions = [".mp4", ".pkl", ".avi", ".mov"]
        
        for search_dir in search_dirs:
            if not search_dir.exists():
                continue
            for ext in extensions:
                candidate = search_dir / f"{base_name}{ext}"
                if candidate.exists():
                    return str(candidate)
        
        return None
    
    def get_status(self) -> dict:
        """Get engine operational status."""
        return {
            "initialized": self.initialized,
            "mode": self.mode,
            "model_path": str(self.model_path),
            "model_exists": self.model_path.exists(),
            "available_motions": [
                m for m in self.DRIVING_ASSETS
                if self._find_driving_asset(m) is not None
            ],
            "process_running": self._process is not None and self._process.poll() is None,
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(name)s | %(message)s")
    
    engine = ReenactmentEngine()
    engine.initialize_engine()
    
    status = engine.get_status()
    print(f"Mode: {status['mode']}")
    print(f"Available motions: {status['available_motions']}")
    
    if status["initialized"]:
        print("Engine is operational and ready for KYC reenactment.")
