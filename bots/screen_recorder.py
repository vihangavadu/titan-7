#!/usr/bin/env python3
"""
TITAN GUI TEST BOT — Screen Recorder
FFmpeg-based X11 screen recording with timestamp overlay.
"""

import subprocess
import signal
import time
import logging
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

logger = logging.getLogger("titan_bot.recorder")

RECORDINGS_DIR = Path("/opt/titan/test_recordings")
SCREENSHOTS_DIR = Path("/opt/titan/test_screenshots")


class ScreenRecorder:
    """FFmpeg-based screen recorder for X11 sessions."""

    def __init__(self, output_dir: Optional[Path] = None, fps: int = 15,
                 resolution: str = "1920x1080", display: str = ":10.0"):
        self.output_dir = output_dir or RECORDINGS_DIR
        self.screenshots_dir = SCREENSHOTS_DIR
        self.fps = fps
        self.resolution = resolution
        self.display = display
        self._process: Optional[subprocess.Popen] = None
        self._recording_path: Optional[Path] = None
        self._start_time: Optional[float] = None

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)

    @property
    def is_recording(self) -> bool:
        return self._process is not None and self._process.poll() is None

    @property
    def recording_path(self) -> Optional[Path]:
        return self._recording_path

    @property
    def elapsed_seconds(self) -> float:
        if self._start_time is None:
            return 0.0
        return time.time() - self._start_time

    def start(self, filename: Optional[str] = None) -> Path:
        """Start screen recording. Returns the output file path."""
        if self.is_recording:
            logger.warning("Recording already in progress")
            return self._recording_path

        if filename is None:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"titan_test_{ts}.mp4"

        self._recording_path = self.output_dir / filename

        # Build FFmpeg command for X11 capture with timestamp overlay
        cmd = [
            "ffmpeg", "-y",
            "-f", "x11grab",
            "-framerate", str(self.fps),
            "-video_size", self.resolution,
            "-i", self.display,
            "-vf", (
                "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf:"
                "text='%{localtime}  |  TITAN TEST BOT':"
                "fontcolor=white:fontsize=16:box=1:boxcolor=black@0.6:"
                "boxborderw=5:x=10:y=10"
            ),
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "28",
            "-pix_fmt", "yuv420p",
            str(self._recording_path),
        ]

        logger.info(f"Starting screen recording → {self._recording_path}")
        try:
            self._process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            self._start_time = time.time()
            time.sleep(1)  # Allow FFmpeg to initialize
            if self._process.poll() is not None:
                stderr = self._process.stderr.read().decode(errors="replace")
                logger.error(f"FFmpeg failed to start: {stderr[:500]}")
                raise RuntimeError(f"FFmpeg exited immediately: {stderr[:200]}")
            logger.info("Screen recording started successfully")
        except FileNotFoundError:
            logger.error("FFmpeg not found. Install with: apt-get install ffmpeg")
            raise

        return self._recording_path

    def stop(self) -> Optional[Path]:
        """Stop screen recording. Returns the output file path."""
        if not self.is_recording:
            logger.warning("No recording in progress")
            return self._recording_path

        logger.info("Stopping screen recording...")
        try:
            self._process.stdin.write(b"q")
            self._process.stdin.flush()
        except (BrokenPipeError, OSError):
            pass

        try:
            self._process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            logger.warning("FFmpeg did not stop gracefully, sending SIGTERM")
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait()

        elapsed = self.elapsed_seconds
        self._process = None
        self._start_time = None

        if self._recording_path and self._recording_path.exists():
            size_mb = self._recording_path.stat().st_size / (1024 * 1024)
            logger.info(
                f"Recording saved: {self._recording_path} "
                f"({size_mb:.1f} MB, {elapsed:.0f}s)"
            )
            return self._recording_path
        else:
            logger.error("Recording file not found after stop")
            return None

    def take_screenshot(self, name: str = "") -> Path:
        """Take a screenshot using import (ImageMagick) or scrot."""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        suffix = f"_{name}" if name else ""
        filename = f"screenshot_{ts}{suffix}.png"
        filepath = self.screenshots_dir / filename

        # Try import (ImageMagick) first, then scrot, then xdotool+ffmpeg
        for cmd in [
            ["import", "-window", "root", str(filepath)],
            ["scrot", str(filepath)],
            ["xwd", "-root", "-silent", "|", "convert", "xwd:-", str(filepath)],
        ]:
            try:
                if "|" in cmd:
                    subprocess.run(
                        " ".join(cmd), shell=True, check=True,
                        timeout=5, capture_output=True,
                    )
                else:
                    subprocess.run(cmd, check=True, timeout=5, capture_output=True)
                if filepath.exists():
                    logger.debug(f"Screenshot saved: {filepath}")
                    return filepath
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                continue

        # Fallback: use Python + PIL
        try:
            import pyautogui
            img = pyautogui.screenshot()
            img.save(str(filepath))
            if filepath.exists():
                logger.debug(f"Screenshot (pyautogui): {filepath}")
                return filepath
        except Exception as e:
            logger.error(f"All screenshot methods failed: {e}")

        return filepath

    def get_video_timestamp(self) -> str:
        """Get current timestamp in HH:MM:SS format for video reference."""
        elapsed = self.elapsed_seconds
        h = int(elapsed // 3600)
        m = int((elapsed % 3600) // 60)
        s = int(elapsed % 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    def cleanup(self):
        """Stop recording if active."""
        if self.is_recording:
            self.stop()
