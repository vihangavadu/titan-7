#!/usr/bin/env python3
"""
TITAN V7.0.3 — KYC Motion Asset Generator
Generates synthetic motion driving videos for liveness challenge bypass.

Usage:
    python3 generate_motions.py [--output-dir /opt/titan/assets/motions]

Each motion video is a 512x512 MP4 at 30fps showing subtle facial movements.
These are used as driving videos for LivePortrait neural reenactment, or
streamed directly via ffmpeg as a fallback.

Requirements:
    pip3 install opencv-python numpy
"""

import argparse
import sys
import os
import math
import struct
from pathlib import Path

# Motion specifications: name, duration_seconds, description
MOTIONS = [
    ("neutral",      10, "Subtle idle movement with natural micro-shifts"),
    ("blink",         2, "Single natural eye blink"),
    ("blink_twice",   3, "Two consecutive blinks with pause"),
    ("smile",         3, "Natural smile expression building and relaxing"),
    ("head_left",     3, "Gradual head turn to the left"),
    ("head_right",    3, "Gradual head turn to the right"),
    ("head_nod",      3, "Gentle head nod up and down"),
    ("look_up",       2, "Eyes and slight head tilt upward"),
    ("look_down",     2, "Eyes and slight head tilt downward"),
]

FPS = 30
SIZE = 512


def generate_motion_video_cv2(name, duration, description, output_dir):
    """Generate motion video using OpenCV with synthetic face landmarks."""
    import cv2
    import numpy as np

    output_path = output_dir / f"{name}.mp4"
    num_frames = int(duration * FPS)

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(str(output_path), fourcc, FPS, (SIZE, SIZE))

    cx, cy = SIZE // 2, SIZE // 2
    face_rx, face_ry = 120, 160

    for i in range(num_frames):
        t = i / num_frames
        frame = np.zeros((SIZE, SIZE, 3), dtype=np.uint8)
        frame[:] = (40, 40, 45)

        dx, dy = 0, 0
        eye_open = 1.0
        mouth_curve = 0.0
        brow_raise = 0.0

        if name == "neutral":
            dx = math.sin(t * 2 * math.pi * 0.3) * 3
            dy = math.cos(t * 2 * math.pi * 0.2) * 2
            if 0.15 < (t % 0.33) < 0.18:
                eye_open = 0.1

        elif name == "blink":
            peak = 0.5
            dist = abs(t - peak)
            if dist < 0.15:
                eye_open = max(0.05, dist / 0.15)

        elif name == "blink_twice":
            for peak in [0.3, 0.7]:
                dist = abs(t - peak)
                if dist < 0.12:
                    eye_open = min(eye_open, max(0.05, dist / 0.12))

        elif name == "smile":
            mouth_curve = math.sin(t * math.pi) * 15
            brow_raise = math.sin(t * math.pi) * 5

        elif name == "head_left":
            dx = -math.sin(t * math.pi) * 40

        elif name == "head_right":
            dx = math.sin(t * math.pi) * 40

        elif name == "head_nod":
            dy = -math.sin(t * 2 * math.pi) * 25

        elif name == "look_up":
            dy = -math.sin(t * math.pi) * 30
            brow_raise = math.sin(t * math.pi) * 8

        elif name == "look_down":
            dy = math.sin(t * math.pi) * 30

        fcx = int(cx + dx)
        fcy = int(cy + dy)

        cv2.ellipse(frame, (fcx, fcy), (face_rx, face_ry), 0, 0, 360, (180, 160, 140), -1)
        cv2.ellipse(frame, (fcx, fcy), (face_rx, face_ry), 0, 0, 360, (140, 120, 100), 2)

        le_cx, re_cx = fcx - 40, fcx + 40
        eye_cy = fcy - 30 - int(brow_raise)
        eye_h = max(1, int(12 * eye_open))
        cv2.ellipse(frame, (le_cx, eye_cy), (18, eye_h), 0, 0, 360, (240, 240, 240), -1)
        cv2.ellipse(frame, (re_cx, eye_cy), (18, eye_h), 0, 0, 360, (240, 240, 240), -1)
        if eye_open > 0.3:
            cv2.circle(frame, (le_cx, eye_cy), 7, (60, 40, 20), -1)
            cv2.circle(frame, (re_cx, eye_cy), 7, (60, 40, 20), -1)
            cv2.circle(frame, (le_cx - 2, eye_cy - 2), 2, (255, 255, 255), -1)
            cv2.circle(frame, (re_cx - 2, eye_cy - 2), 2, (255, 255, 255), -1)

        brow_y = eye_cy - 22
        cv2.line(frame, (le_cx - 20, brow_y), (le_cx + 20, brow_y - 3), (100, 80, 60), 2)
        cv2.line(frame, (re_cx - 20, brow_y - 3), (re_cx + 20, brow_y), (100, 80, 60), 2)

        nose_tip = (fcx, fcy + 15)
        cv2.line(frame, (fcx, fcy - 10), nose_tip, (160, 140, 120), 2)
        cv2.line(frame, (fcx - 8, fcy + 15), nose_tip, (160, 140, 120), 1)
        cv2.line(frame, (fcx + 8, fcy + 15), nose_tip, (160, 140, 120), 1)

        mouth_y = fcy + 50
        mc = int(mouth_curve)
        pts_upper = [(fcx - 30, mouth_y), (fcx - 15, mouth_y - 5 - mc // 2),
                     (fcx, mouth_y - 3 - mc // 2), (fcx + 15, mouth_y - 5 - mc // 2),
                     (fcx + 30, mouth_y)]
        pts_lower = [(fcx - 30, mouth_y), (fcx - 15, mouth_y + 5 + mc),
                     (fcx, mouth_y + 8 + mc), (fcx + 15, mouth_y + 5 + mc),
                     (fcx + 30, mouth_y)]
        for j in range(len(pts_upper) - 1):
            cv2.line(frame, pts_upper[j], pts_upper[j + 1], (140, 100, 100), 2)
        for j in range(len(pts_lower) - 1):
            cv2.line(frame, pts_lower[j], pts_lower[j + 1], (140, 100, 100), 2)

        writer.write(frame)

    writer.release()
    print(f"  [+] {name}.mp4 ({duration}s, {num_frames} frames)")
    return output_path


def generate_motion_video_raw(name, duration, description, output_dir):
    """
    Generate a minimal valid MP4 file without OpenCV.
    Uses ffmpeg with lavfi to create synthetic test patterns.
    """
    import subprocess

    output_path = output_dir / f"{name}.mp4"
    num_frames = int(duration * FPS)

    filter_expr = (
        f"color=c=gray:s={SIZE}x{SIZE}:d={duration}:r={FPS},"
        f"drawtext=text='{name}':fontsize=48:fontcolor=white:"
        f"x=(w-text_w)/2:y=(h-text_h)/2"
    )

    cmd = [
        "ffmpeg", "-y", "-f", "lavfi", "-i", filter_expr,
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-t", str(duration), str(output_path)
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print(f"  [+] {name}.mp4 ({duration}s) [ffmpeg]")
            return output_path
        else:
            print(f"  [!] ffmpeg failed for {name}: {result.stderr[:200]}")
            return None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print(f"  [!] ffmpeg not available for {name}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Generate KYC motion driving videos")
    parser.add_argument("--output-dir", default=str(Path(__file__).parent),
                        help="Output directory for motion videos")
    parser.add_argument("--method", choices=["cv2", "ffmpeg", "auto"], default="auto",
                        help="Generation method")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("  TITAN V7.0.3 — KYC Motion Asset Generator")
    print("=" * 60)

    method = args.method
    if method == "auto":
        try:
            import cv2
            method = "cv2"
            print(f"  Using OpenCV ({cv2.__version__})")
        except ImportError:
            method = "ffmpeg"
            print("  OpenCV not available, using ffmpeg")

    generated = 0
    for name, duration, description in MOTIONS:
        output_file = output_dir / f"{name}.mp4"
        if output_file.exists():
            print(f"  [=] {name}.mp4 already exists, skipping")
            generated += 1
            continue

        if method == "cv2":
            result = generate_motion_video_cv2(name, duration, description, output_dir)
        else:
            result = generate_motion_video_raw(name, duration, description, output_dir)

        if result:
            generated += 1

    print(f"\n  Generated: {generated}/{len(MOTIONS)} motion assets")
    if generated == len(MOTIONS):
        print("  STATUS: ALL MOTION ASSETS READY")
    else:
        print("  STATUS: SOME ASSETS MISSING — install opencv-python or ffmpeg")
    print("=" * 60)


if __name__ == "__main__":
    main()
