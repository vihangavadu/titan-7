#!/usr/bin/env python3
# LUCID TITAN KYC MODULE :: CAMERA INJECTOR
# Authority: Dva.12 | Status: TITAN_ACTIVE
# Purpose: Manages v4l2loopback kernel module and FFmpeg stream piping for synthetic video injection.

import subprocess
import os
import time
import logging

class CameraInjector:
    def __init__(self, video_device="/dev/video10", label="Integrated Camera"):
        self.video_device = video_device
        self.label = label
        self.process = None
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("CameraInjector")

    def load_kernel_module(self):
        """
        Loads the v4l2loopback kernel module with specific parameters to bypass detection.
        Section 3.2.1: Bypassing "Virtual" Label Detection
        """
        self.logger.info(f"Loading v4l2loopback module for {self.video_device}...")
        
        # Unload if exists
        subprocess.run(["modprobe", "-r", "v4l2loopback"], check=False)
        
        # Load with spoofed label and exclusive_caps
        # exclusive_caps=1 ensures Chrome sees it as a capture device
        cmd = [
            "modprobe", "v4l2loopback",
            "devices=1",
            f"video_nr={self.video_device.replace('/dev/video', '')}",
            f"card_label={self.label}",
            "exclusive_caps=1"
        ]
        
        try:
            subprocess.run(cmd, check=True)
            self.logger.info("Kernel module loaded successfully.")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to load kernel module: {e}")
            raise

    def _sample_ambient_luminance(self, background_device: str = "/dev/video0") -> dict:
        """
        GAP-5 FIX: Sample the real background camera feed to extract ambient
        luminance, color temperature, and tint. Returns correction params
        to apply to the synthetic face stream so it matches the environment.

        Uses ffprobe to extract a single frame and measure mean brightness/color.
        Falls back to neutral values if background device is unavailable.
        """
        params = {"brightness": 0.0, "contrast": 1.0, "saturation": 1.0,
                  "gamma": 1.0, "color_temp_k": 5500}
        try:
            # Grab one frame from the real background camera
            probe_cmd = [
                "ffprobe", "-v", "quiet",
                "-select_streams", "v:0",
                "-show_entries", "frame_tags=lavfi.signalstats.YAVG,lavfi.signalstats.UAVG,lavfi.signalstats.VAVG",
                "-f", "lavfi",
                f"movie={background_device},signalstats",
                "-of", "csv=p=0",
                "-frames:v", "1"
            ]
            result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                parts = result.stdout.strip().split(",")
                if len(parts) >= 3:
                    y_avg = float(parts[0]) / 255.0   # Normalized 0-1
                    u_avg = float(parts[1]) / 255.0
                    v_avg = float(parts[2]) / 255.0

                    # Map Y (luma) to brightness correction
                    # Target: synthetic face should match ambient luma
                    target_luma = 0.45  # Neutral reference
                    params["brightness"] = round((y_avg - target_luma) * 0.6, 3)

                    # Estimate color temperature from U/V chrominance
                    # Warm light (tungsten ~3200K): high V, low U
                    # Cool light (daylight ~6500K): high U, low V
                    uv_ratio = (v_avg - 0.5) - (u_avg - 0.5)
                    if uv_ratio > 0.05:
                        params["color_temp_k"] = 3200   # Warm/tungsten
                    elif uv_ratio < -0.05:
                        params["color_temp_k"] = 6500   # Cool/daylight
                    else:
                        params["color_temp_k"] = 5500   # Neutral

                    # Contrast: low ambient = reduce contrast (flat lighting)
                    params["contrast"] = round(0.85 + y_avg * 0.3, 3)
                    self.logger.info(
                        f"Ambient sample: luma={y_avg:.2f}, temp={params['color_temp_k']}K, "
                        f"brightness_adj={params['brightness']:.3f}"
                    )
        except Exception as e:
            self.logger.warning(f"Ambient sampling failed (using neutral): {e}")
        return params

    def _build_ambient_filter(self, ambient: dict, base_filters: str) -> str:
        """
        Build FFmpeg filter chain that applies ambient lighting correction
        to the synthetic face stream, matching the real background environment.
        Defeats Tier-1 'Ambient Discontinuity' KYC alerts.
        """
        brightness = ambient.get("brightness", 0.0)
        contrast = ambient.get("contrast", 1.0)
        color_temp_k = ambient.get("color_temp_k", 5500)

        # Map color temperature to RGB channel multipliers
        # Warm (3200K): boost red/green, reduce blue
        # Cool (6500K): boost blue, reduce red
        if color_temp_k <= 3500:
            r_mult, g_mult, b_mult = 1.08, 1.02, 0.88
        elif color_temp_k >= 6000:
            r_mult, g_mult, b_mult = 0.92, 0.98, 1.10
        else:
            r_mult, g_mult, b_mult = 1.0, 1.0, 1.0

        # Build eq filter for brightness/contrast
        eq_filter = f"eq=brightness={brightness:.3f}:contrast={contrast:.3f}:saturation=1.0"

        # Build colorchannelmixer for color temperature matching
        cc_filter = (
            f"colorchannelmixer="
            f"rr={r_mult:.3f}:gg={g_mult:.3f}:bb={b_mult:.3f}"
        )

        # Combine: base degradation → ambient eq → color temp matching
        return f"{base_filters},{eq_filter},{cc_filter}"

    def start_stream(self, source_file, degraded=True, background_device: str = "/dev/video0"):
        """
        Pipes the synthetic video stream to the virtual camera device.
        Section 3.2.2 & 5.2.1: FFmpeg Filter Chain for Webcam Simulation

        GAP-5 FIX: Samples ambient lighting from background_device and applies
        luminance/color-temperature correction to match the real environment,
        defeating Tier-1 Ambient Discontinuity KYC detection.
        """
        if not os.path.exists(source_file):
            self.logger.error(f"Source file not found: {source_file}")
            return

        self.logger.info(f"Starting injection from {source_file} to {self.video_device}...")

        # Sample ambient lighting from real background camera
        ambient = self._sample_ambient_luminance(background_device)

        # Base FFmpeg command
        cmd = ["ffmpeg", "-re", "-i", source_file]

        if degraded:
            # Section 5.2.1: Synthetic Degradation Pipeline
            # 1. Sensor Noise  2. Lens Distortion  3. Ambient Lighting Match
            base_filters = "noise=alls=10:allf=t+u,lenscorrection=k1=-0.05:k2=-0.05"
            filters = self._build_ambient_filter(ambient, base_filters)
            cmd.extend(["-vf", filters])
            self.logger.info(
                f"Applying degradation + ambient correction filters "
                f"(temp={ambient['color_temp_k']}K, brightness_adj={ambient['brightness']:.3f})."
            )
        else:
            # Even without degradation, apply ambient correction
            ambient_only = self._build_ambient_filter(ambient, "null")
            cmd.extend(["-vf", ambient_only])

        # Output to v4l2 device
        cmd.extend(["-map", "0:v", "-f", "v4l2", self.video_device])

        try:
            self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.logger.info(f"Stream started (PID: {self.process.pid})")
        except Exception as e:
            self.logger.error(f"Failed to start FFmpeg: {e}")

    def stop_stream(self):
        if self.process:
            self.process.terminate()
            self.logger.info("Stream stopped.")
            self.process = None

if __name__ == "__main__":
    # Example usage
    injector = CameraInjector()
    try:
        injector.load_kernel_module()
        # In a real scenario, this would be triggered by the TitanController
        # injector.start_stream("/opt/lucid-empire/research/synthetic_kyc_video.mp4")
    except Exception as e:
        print(f"Error: {e}")
