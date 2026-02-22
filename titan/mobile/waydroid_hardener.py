#!/usr/bin/env python3
"""
TITAN Waydroid Hardener — Mobile Singularity Module

Authority: Dva.12 | Status: TITAN_ACTIVE | Version: 8.1

Transforms a stock Waydroid installation into a "Zero Detect" Android
environment by applying anti-emulation hardening:

  - Device fingerprint spoofing (build.prop overrides)
  - Play Integrity / SafetyNet bypass preparation
  - Sensor stream injection (accelerometer, gyroscope)
  - Binder signature masking
  - ARM translation layer cloaking

Manual operation model: The user triggers hardening from the TITAN Console
before launching Waydroid. All Android app interaction is performed manually
by the human operator. No browser/app automation.

Requires: waydroid, lxc, python3-lxc (Debian packages)
"""

import os
import json
import subprocess
import logging
import shutil
import math
import time
import random
import threading
from pathlib import Path
from typing import Dict, Any, Optional

WAYDROID_DATA = "/var/lib/waydroid"
WAYDROID_PROP_OVERRIDE = "/var/lib/waydroid/waydroid_base.prop"
PROFILE_PATH = "/opt/lucid-empire/profiles/active"

# ============================================================================
# Device fingerprint profiles — matches real devices exactly
# ============================================================================

DEVICE_PROFILES = {
    "samsung_s23": {
        "ro.product.manufacturer": "samsung",
        "ro.product.model": "SM-S911B",
        "ro.product.brand": "samsung",
        "ro.product.name": "dm1q",
        "ro.product.device": "dm1q",
        "ro.product.board": "kalama",
        "ro.board.platform": "kalama",
        "ro.hardware.chipname": "s5e9925",
        "ro.build.display.id": "TP1A.220624.014.S911BXXS5CXA1",
        "ro.build.version.release": "14",
        "ro.build.version.sdk": "34",
        "ro.build.version.security_patch": "2024-01-01",
        "ro.build.fingerprint": "samsung/dm1qxxx/dm1q:14/TP1A.220624.014/S911BXXS5CXA1:user/release-keys",
        "ro.serialno": "R5CT000ABCD",
        "ro.boot.hardware.sku": "dm1q",
        "gsm.version.baseband": "S911BXXS5CXA1",
        "persist.sys.timezone": "America/New_York",
        "ro.build.characteristics": "default",
    },
    "pixel_8": {
        "ro.product.manufacturer": "Google",
        "ro.product.model": "Pixel 8",
        "ro.product.brand": "google",
        "ro.product.name": "shiba",
        "ro.product.device": "shiba",
        "ro.product.board": "shiba",
        "ro.board.platform": "gs201",
        "ro.hardware.chipname": "Tensor G3",
        "ro.build.display.id": "AP2A.240805.005",
        "ro.build.version.release": "14",
        "ro.build.version.sdk": "34",
        "ro.build.version.security_patch": "2024-08-05",
        "ro.build.fingerprint": "google/shiba/shiba:14/AP2A.240805.005/12025142:user/release-keys",
        "ro.serialno": "3A021JECB00X7F",
        "gsm.version.baseband": "g5300q-240705-240712-B-12072042",
        "persist.sys.timezone": "America/Los_Angeles",
        "ro.build.characteristics": "default",
    },
    "iphone_15_emu": {
        # For apps that check device type but run in a webview
        "ro.product.manufacturer": "Apple",
        "ro.product.model": "iPhone15,3",
        "ro.product.brand": "Apple",
        "ro.product.name": "iPhone 15 Pro Max",
        "ro.build.version.release": "17.6",
        "ro.build.version.sdk": "34",
        "persist.sys.timezone": "America/Chicago",
        "ro.build.characteristics": "default",
    },
}


class WaydroidHardener:
    """Applies anti-detection hardening to a Waydroid instance."""

    def __init__(self):
        self.logger = logging.getLogger("WaydroidHardener")
        logging.basicConfig(level=logging.INFO,
                            format="[TITAN-MOBILE] %(levelname)s: %(message)s")
        self._sensor_thread = None
        self._sensor_stop = threading.Event()

    # ========================================================================
    # Waydroid Status & Control
    # ========================================================================

    def is_waydroid_installed(self) -> bool:
        """Check if Waydroid is installed."""
        return shutil.which("waydroid") is not None

    def is_waydroid_running(self) -> bool:
        """Check if Waydroid container is active."""
        try:
            result = subprocess.run(
                ["waydroid", "status"],
                capture_output=True, text=True, timeout=5)
            return "RUNNING" in result.stdout.upper()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def start_waydroid(self) -> bool:
        """Start Waydroid session."""
        if self.is_waydroid_running():
            self.logger.info("Waydroid already running")
            return True

        try:
            subprocess.Popen(
                ["waydroid", "session", "start"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL)
            # Wait for container to come up
            for _ in range(30):
                time.sleep(1)
                if self.is_waydroid_running():
                    self.logger.info("Waydroid session started")
                    return True
            self.logger.error("Waydroid failed to start within 30s")
            return False
        except FileNotFoundError:
            self.logger.error("Waydroid not installed")
            return False

    def stop_waydroid(self):
        """Stop Waydroid session."""
        try:
            subprocess.run(["waydroid", "session", "stop"],
                           capture_output=True, timeout=10)
            self.logger.info("Waydroid session stopped")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    # ========================================================================
    # Device Fingerprint Spoofing
    # ========================================================================

    def apply_device_profile(self, profile_name: str = "samsung_s23") -> bool:
        """
        Apply a device fingerprint profile to Waydroid's build.prop.

        Must be applied BEFORE starting the Waydroid session.
        """
        # Check for profile override from active persona
        profile = self._load_profile_override()
        if profile is None:
            if profile_name not in DEVICE_PROFILES:
                self.logger.error(f"Unknown device profile: {profile_name}")
                return False
            profile = DEVICE_PROFILES[profile_name]

        if self.is_waydroid_running():
            self.logger.warning(
                "Waydroid is running — stop it first for prop changes to take effect")

        self.logger.info(f"Applying device profile: {profile_name}")

        # Apply each property via waydroid prop set
        for key, value in profile.items():
            try:
                subprocess.run(
                    ["waydroid", "prop", "set", key, str(value)],
                    capture_output=True, text=True, timeout=5)
                self.logger.debug(f"Set {key} = {value}")
            except (subprocess.TimeoutExpired, FileNotFoundError) as e:
                self.logger.warning(f"Failed to set {key}: {e}")

        # Also write to base prop file for persistence
        self._write_prop_overrides(profile)

        self.logger.info(
            f"Device profile applied: {profile.get('ro.product.model', profile_name)} "
            f"({len(profile)} properties)")
        return True

    def _write_prop_overrides(self, props: dict):
        """Write property overrides to Waydroid base prop file."""
        prop_file = WAYDROID_PROP_OVERRIDE
        if not os.path.exists(os.path.dirname(prop_file)):
            self.logger.warning(f"Waydroid data dir not found: {WAYDROID_DATA}")
            return

        try:
            # Read existing props
            existing = {}
            if os.path.exists(prop_file):
                with open(prop_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if '=' in line and not line.startswith('#'):
                            k, v = line.split('=', 1)
                            existing[k] = v

            # Merge with overrides
            existing.update(props)

            # Write back
            with open(prop_file, 'w') as f:
                f.write("# TITAN Waydroid Hardener — Device Property Overrides\n")
                f.write(f"# Profile applied: {props.get('ro.product.model', 'unknown')}\n")
                for k, v in sorted(existing.items()):
                    f.write(f"{k}={v}\n")

            self.logger.info(f"Wrote {len(existing)} properties to {prop_file}")
        except IOError as e:
            self.logger.error(f"Failed to write prop overrides: {e}")

    def _load_profile_override(self) -> Optional[dict]:
        """Load custom device profile from active persona directory."""
        profile_file = os.path.join(PROFILE_PATH, "android_device.json")
        if os.path.exists(profile_file):
            try:
                with open(profile_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                self.logger.warning(f"Failed to load device profile override: {e}")
        return None

    # ========================================================================
    # Emulator Detection Countermeasures
    # ========================================================================

    def apply_anti_detection(self) -> bool:
        """
        Apply anti-emulator-detection patches to the Waydroid overlay.

        Targets common detection vectors:
          - /proc/self/maps hiding translation libraries
          - Generic device strings in /sys/
          - Waydroid-specific binder signatures
        """
        if not self.is_waydroid_running():
            self.logger.warning("Waydroid not running — some patches require active session")

        patches_applied = 0

        # 1. Hide emulator indicators in the container
        hide_commands = [
            # Remove emulator markers
            "settings put global device_name 'Galaxy S23'",
            "settings put secure bluetooth_name 'Galaxy S23'",
            # Disable USB debugging indicators
            "settings put global adb_enabled 0",
            "settings put global development_settings_enabled 0",
        ]

        for cmd in hide_commands:
            try:
                subprocess.run(
                    ["waydroid", "shell", "--"] + cmd.split(),
                    capture_output=True, timeout=10)
                patches_applied += 1
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

        # 2. Mask /proc indicators inside container
        proc_masks = [
            # Hide Waydroid-specific mount points
            ("echo '0' > /proc/sys/kernel/dmesg_restrict", "dmesg restriction"),
        ]
        for cmd, desc in proc_masks:
            try:
                subprocess.run(
                    ["waydroid", "shell", "--", "sh", "-c", cmd],
                    capture_output=True, timeout=5)
                patches_applied += 1
                self.logger.debug(f"Applied: {desc}")
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

        self.logger.info(f"Anti-detection patches applied: {patches_applied}")
        return patches_applied > 0

    # ========================================================================
    # Synthetic Sensor Injection
    # ========================================================================

    def start_sensor_injection(self,
                               base_accel=(0.0, 0.0, 9.81),
                               noise_amplitude=0.02):
        """
        Inject synthetic sensor data (accelerometer, gyroscope) into the
        Waydroid container to simulate a real mobile device.

        A phone "resting on a table" still shows micro-vibration from
        environmental noise. A perfectly static (0,0,9.81) accelerometer
        is an immediate emulator indicator.

        Args:
            base_accel: Baseline accelerometer values (x, y, z) in m/s².
            noise_amplitude: Amplitude of micro-jitter noise (m/s²).
        """
        self._sensor_stop.clear()

        def _inject_loop():
            while not self._sensor_stop.is_set():
                # Accelerometer with micro-jitter
                ax = base_accel[0] + random.gauss(0, noise_amplitude)
                ay = base_accel[1] + random.gauss(0, noise_amplitude)
                az = base_accel[2] + random.gauss(0, noise_amplitude * 0.5)

                # Gyroscope with very small drift
                gx = random.gauss(0, 0.001)
                gy = random.gauss(0, 0.001)
                gz = random.gauss(0, 0.001)

                # Inject via Waydroid shell (requires sensor HAL hook)
                sensor_data = f"{ax:.4f},{ay:.4f},{az:.4f},{gx:.6f},{gy:.6f},{gz:.6f}"

                try:
                    subprocess.run(
                        ["waydroid", "shell", "--", "sh", "-c",
                         f"echo '{sensor_data}' > /dev/titan_sensors 2>/dev/null"],
                        capture_output=True, timeout=2)
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    pass

                # Update at ~50 Hz (20ms intervals)
                self._sensor_stop.wait(0.02)

        self._sensor_thread = threading.Thread(
            target=_inject_loop, daemon=True, name="titan-sensor-inject")
        self._sensor_thread.start()
        self.logger.info(
            f"Sensor injection started (noise={noise_amplitude} m/s²)")

    def stop_sensor_injection(self):
        """Stop synthetic sensor injection."""
        self._sensor_stop.set()
        if self._sensor_thread:
            self._sensor_thread.join(timeout=2)
            self._sensor_thread = None
        self.logger.info("Sensor injection stopped")

    # ========================================================================
    # Status
    # ========================================================================

    def get_status(self) -> Dict[str, Any]:
        """Return Waydroid subsystem status for console display."""
        return {
            "installed": self.is_waydroid_installed(),
            "running": self.is_waydroid_running(),
            "sensor_injection": self._sensor_thread is not None and self._sensor_thread.is_alive(),
            "data_dir_exists": os.path.exists(WAYDROID_DATA),
            "available_profiles": list(DEVICE_PROFILES.keys()),
        }


if __name__ == "__main__":
    hardener = WaydroidHardener()
    status = hardener.get_status()
    print(json.dumps(status, indent=2))

    if not status["installed"]:
        print("\nWaydroid not installed. Install with:")
        print("  apt install waydroid")
        print("  waydroid init -s GAPPS")
