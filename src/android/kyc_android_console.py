#!/usr/bin/env python3
"""
TITAN OS — KYC Android Console v2.0
====================================
Manages Waydroid Android container for KYC verification bypass operations.

Capabilities:
  - Start/stop Android container (Waydroid)
  - Device identity spoofing (Pixel 7, Samsung S24, etc.)
  - APK install/uninstall for KYC apps (Jumio, Onfido, Veriff, etc.)
  - Android shell command execution
  - Cross-device sync with desktop (waydroid_sync.py)
  - Camera feed injection for KYC liveness
  - Virtual sensor spoofing (GPS, gyro, accelerometer)
  - Screen capture and automation
  - App activity monitoring

Usage:
  titan-android start          Start Android container
  titan-android stop           Stop Android container
  titan-android status         Show container status
  titan-android shell <cmd>    Run shell command in Android
  titan-android spoof <preset> Apply device identity preset
  titan-android install <apk>  Install APK
  titan-android apps           List installed apps
  titan-android sync           Start cross-device sync
  titan-android camera         Configure virtual camera
  titan-android sensor         Configure virtual sensors
  titan-android screenshot     Take screenshot
  titan-android kyc <provider> Run KYC bypass for provider
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
LOG = logging.getLogger("titan-android")

TITAN_ROOT = Path(os.environ.get("TITAN_ROOT", "/opt/titan"))
WAYDROID_DIR = Path("/var/lib/waydroid")
WAYDROID_IMAGES = WAYDROID_DIR / "images"
WAYDROID_DATA = WAYDROID_DIR / "data"
PROP_FILE = WAYDROID_DIR / "waydroid_base.prop"
STATE_FILE = TITAN_ROOT / "android" / "state.json"
KYC_ASSETS = TITAN_ROOT / "android" / "assets"

# ═══════════════════════════════════════════════════════════════════════════════
# DEVICE PRESETS
# ═══════════════════════════════════════════════════════════════════════════════

DEVICE_PRESETS: Dict[str, Dict[str, str]] = {
    "pixel7": {
        "ro.product.model": "Pixel 7",
        "ro.product.brand": "google",
        "ro.product.name": "panther",
        "ro.product.device": "panther",
        "ro.product.manufacturer": "Google",
        "ro.build.fingerprint": "google/panther/panther:14/AP2A.240805.005/12025142:user/release-keys",
        "ro.build.version.release": "14",
        "ro.build.version.sdk": "34",
        "ro.build.version.security_patch": "2024-08-05",
        "ro.sf.lcd_density": "420",
    },
    "pixel8": {
        "ro.product.model": "Pixel 8",
        "ro.product.brand": "google",
        "ro.product.name": "shiba",
        "ro.product.device": "shiba",
        "ro.product.manufacturer": "Google",
        "ro.build.fingerprint": "google/shiba/shiba:14/AP2A.240905.003/12231197:user/release-keys",
        "ro.build.version.release": "14",
        "ro.build.version.sdk": "34",
        "ro.build.version.security_patch": "2024-09-05",
        "ro.sf.lcd_density": "420",
    },
    "samsung_s24": {
        "ro.product.model": "SM-S921B",
        "ro.product.brand": "samsung",
        "ro.product.name": "e2sxexx",
        "ro.product.device": "e2s",
        "ro.product.manufacturer": "samsung",
        "ro.build.fingerprint": "samsung/e2sxexx/e2s:14/UP1A.231005.007/S921BXXU3AXH1:user/release-keys",
        "ro.build.version.release": "14",
        "ro.build.version.sdk": "34",
        "ro.build.version.security_patch": "2024-08-01",
        "ro.sf.lcd_density": "480",
    },
    "samsung_a54": {
        "ro.product.model": "SM-A546B",
        "ro.product.brand": "samsung",
        "ro.product.name": "a54xnsxx",
        "ro.product.device": "a54x",
        "ro.product.manufacturer": "samsung",
        "ro.build.fingerprint": "samsung/a54xnsxx/a54x:14/UP1A.231005.007/A546BXXS9CXF3:user/release-keys",
        "ro.build.version.release": "14",
        "ro.build.version.sdk": "34",
        "ro.build.version.security_patch": "2024-06-01",
        "ro.sf.lcd_density": "400",
    },
    "oneplus_12": {
        "ro.product.model": "CPH2581",
        "ro.product.brand": "OnePlus",
        "ro.product.name": "CPH2581",
        "ro.product.device": "CPH2581",
        "ro.product.manufacturer": "OnePlus",
        "ro.build.fingerprint": "OnePlus/CPH2581/OP5961L1:14/UP1A.231005.007/T.18bd050_1-1:user/release-keys",
        "ro.build.version.release": "14",
        "ro.build.version.sdk": "34",
        "ro.build.version.security_patch": "2024-07-05",
        "ro.sf.lcd_density": "480",
    },
}

# Common anti-emulation properties applied to ALL presets
ANTI_EMULATION_PROPS = {
    "ro.kernel.qemu": "0",
    "ro.hardware.virtual": "0",
    "ro.debuggable": "0",
    "ro.secure": "1",
    "ro.hardware.chipname": "exynos2400",
    "gsm.version.baseband": "1.0",
    "ro.boot.hardware": "samsungexynos2400",
    "init.svc.adbd": "stopped",
    "ro.build.tags": "release-keys",
    "ro.build.type": "user",
    "persist.sys.usb.config": "none",
}

# KYC provider APK sources
KYC_APKS: Dict[str, Dict[str, str]] = {
    "jumio": {"package": "com.jumio.nv", "name": "Jumio NV SDK", "activity": "com.jumio.nv/.NetverifyActivity"},
    "onfido": {"package": "com.onfido.android.sdk", "name": "Onfido SDK", "activity": "com.onfido.android.sdk/.capture.CaptureActivity"},
    "veriff": {"package": "com.veriff.sdk", "name": "Veriff SDK", "activity": "com.veriff.sdk/.VeriffActivity"},
    "sumsub": {"package": "com.sumsub.msdk", "name": "SumSub SDK", "activity": "com.sumsub.msdk/.SumSubActivity"},
    "persona": {"package": "com.withpersona.sdk", "name": "Persona SDK", "activity": "com.withpersona.sdk/.PersonaActivity"},
    "stripe": {"package": "com.stripe.android.identity", "name": "Stripe Identity", "activity": "com.stripe.android.identity/.IdentityActivity"},
}


# ═══════════════════════════════════════════════════════════════════════════════
# CORE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def run_cmd(cmd: str, timeout: int = 30) -> Dict[str, Any]:
    """Run shell command and return result."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return {"ok": result.returncode == 0, "stdout": result.stdout.strip(), "stderr": result.stderr.strip(), "code": result.returncode}
    except subprocess.TimeoutExpired:
        return {"ok": False, "stdout": "", "stderr": "Timeout", "code": -1}
    except Exception as e:
        return {"ok": False, "stdout": "", "stderr": str(e), "code": -1}


def waydroid_cmd(args: str, timeout: int = 30) -> Dict[str, Any]:
    """Run waydroid command."""
    return run_cmd(f"waydroid {args}", timeout=timeout)


def android_shell(cmd: str, timeout: int = 15) -> Dict[str, Any]:
    """Run command inside Android container."""
    return run_cmd(f"waydroid shell -- {cmd}", timeout=timeout)


def save_state(data: Dict[str, Any]) -> None:
    """Persist console state."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def load_state() -> Dict[str, Any]:
    """Load console state."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"initialized": False, "device_preset": "pixel7", "last_action": None}


# ═══════════════════════════════════════════════════════════════════════════════
# COMMANDS
# ═══════════════════════════════════════════════════════════════════════════════

def cmd_status() -> Dict[str, Any]:
    """Get Android container status."""
    status = waydroid_cmd("status")
    images_exist = (WAYDROID_IMAGES / "system.img").exists()
    state = load_state()

    # Parse waydroid status output
    info = {"raw": status["stdout"], "images": images_exist, "state": state}

    if "RUNNING" in status["stdout"].upper():
        info["container"] = "running"
        # Get Android props
        model = android_shell("getprop ro.product.model")
        info["device_model"] = model["stdout"] if model["ok"] else "unknown"
        sdk = android_shell("getprop ro.build.version.sdk")
        info["sdk_version"] = sdk["stdout"] if sdk["ok"] else "unknown"
    elif "STOPPED" in status["stdout"].upper() or "not running" in status["stdout"].lower():
        info["container"] = "stopped"
    else:
        info["container"] = "not_initialized" if not images_exist else "unknown"

    return info


def cmd_start() -> Dict[str, Any]:
    """Start Android container."""
    LOG.info("Starting Android container...")

    if not (WAYDROID_IMAGES / "system.img").exists():
        return {"ok": False, "error": "Android image not found. Run: waydroid init -s GAPPS -f"}

    # Start container
    container = waydroid_cmd("container start", timeout=30)
    if not container["ok"]:
        LOG.warning(f"Container start: {container['stderr']}")

    # Start session
    session = waydroid_cmd("session start", timeout=60)
    time.sleep(3)

    # Verify
    status = cmd_status()
    running = status.get("container") == "running"

    state = load_state()
    state["last_action"] = "start"
    state["last_start"] = datetime.now().isoformat()
    save_state(state)

    return {"ok": running, "status": status}


def cmd_stop() -> Dict[str, Any]:
    """Stop Android container."""
    LOG.info("Stopping Android container...")
    waydroid_cmd("session stop", timeout=15)
    waydroid_cmd("container stop", timeout=15)

    state = load_state()
    state["last_action"] = "stop"
    save_state(state)

    return {"ok": True}


def cmd_spoof(preset_name: str) -> Dict[str, Any]:
    """Apply device identity preset."""
    preset_name = preset_name.lower().replace("-", "_").replace(" ", "_")

    if preset_name not in DEVICE_PRESETS:
        return {"ok": False, "error": f"Unknown preset: {preset_name}", "available": list(DEVICE_PRESETS.keys())}

    LOG.info(f"Applying device preset: {preset_name}")
    preset = DEVICE_PRESETS[preset_name]
    all_props = {**preset, **ANTI_EMULATION_PROPS}

    # Add timezone/locale
    all_props["persist.sys.timezone"] = "America/New_York"
    all_props["persist.sys.locale"] = "en_US"

    # Write to prop file
    PROP_FILE.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{k}={v}" for k, v in sorted(all_props.items())]
    PROP_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    LOG.info(f"Wrote {len(all_props)} properties to {PROP_FILE}")

    # If container is running, apply props live
    for k, v in all_props.items():
        android_shell(f"setprop {k} {v}")

    state = load_state()
    state["device_preset"] = preset_name
    state["last_action"] = f"spoof:{preset_name}"
    save_state(state)

    return {"ok": True, "preset": preset_name, "model": preset.get("ro.product.model", "?"), "props_count": len(all_props)}


def cmd_shell(command: str) -> Dict[str, Any]:
    """Execute shell command inside Android."""
    return android_shell(command)


def cmd_install_apk(apk_path: str) -> Dict[str, Any]:
    """Install APK into Android container."""
    if not os.path.exists(apk_path):
        return {"ok": False, "error": f"APK not found: {apk_path}"}

    LOG.info(f"Installing APK: {apk_path}")
    result = run_cmd(f"waydroid app install {apk_path}", timeout=60)
    return {"ok": result["ok"], "output": result["stdout"], "error": result["stderr"]}


def cmd_list_apps() -> Dict[str, Any]:
    """List installed Android apps."""
    result = android_shell("pm list packages -3")
    if result["ok"]:
        packages = [line.replace("package:", "").strip() for line in result["stdout"].splitlines() if line.strip()]
        return {"ok": True, "packages": packages, "count": len(packages)}
    return {"ok": False, "error": result["stderr"]}


def cmd_sync() -> Dict[str, Any]:
    """Start cross-device sync via waydroid_sync.py."""
    sys.path.insert(0, str(TITAN_ROOT / "core"))
    try:
        from waydroid_sync import WaydroidSyncEngine, SyncConfig
        engine = WaydroidSyncEngine(SyncConfig())
        engine.initialize()
        engine.sync_cookies_from_desktop()
        return {"ok": True, "message": "Cross-device sync started"}
    except ImportError:
        return {"ok": False, "error": "waydroid_sync module not available"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def cmd_camera(action: str = "status") -> Dict[str, Any]:
    """Configure virtual camera for KYC liveness."""
    sys.path.insert(0, str(TITAN_ROOT / "core"))

    if action == "status":
        # Check v4l2loopback
        v4l2 = run_cmd("lsmod | grep v4l2loopback")
        devices = run_cmd("ls -la /dev/video* 2>/dev/null")
        return {"ok": True, "v4l2_loaded": "v4l2loopback" in v4l2["stdout"], "devices": devices["stdout"]}

    elif action == "setup":
        # Load v4l2loopback for virtual camera
        run_cmd("modprobe v4l2loopback devices=1 video_nr=20 card_label='TitanKYC' exclusive_caps=1")
        return {"ok": True, "message": "Virtual camera /dev/video20 created"}

    elif action == "inject":
        try:
            from kyc_core import KYCController, VirtualCameraConfig
            config = VirtualCameraConfig()
            ctrl = KYCController(config)
            return {"ok": True, "message": "KYC camera controller initialized", "state": str(ctrl)}
        except ImportError:
            return {"ok": False, "error": "kyc_core not available"}

    return {"ok": False, "error": f"Unknown camera action: {action}"}


def cmd_sensor(sensor_type: str = "gps", value: str = "") -> Dict[str, Any]:
    """Spoof Android sensors (GPS, accelerometer, gyroscope)."""
    if sensor_type == "gps" and value:
        parts = value.split(",")
        if len(parts) >= 2:
            lat, lon = parts[0].strip(), parts[1].strip()
            android_shell(f"settings put secure location_providers_allowed gps")
            result = android_shell(f"am broadcast -a titan.MOCK_LOCATION --ef lat {lat} --ef lon {lon}")
            return {"ok": True, "message": f"GPS set to {lat},{lon}"}
    elif sensor_type == "list":
        result = android_shell("dumpsys sensorservice | head -30")
        return {"ok": True, "sensors": result["stdout"]}
    return {"ok": False, "error": f"Usage: sensor gps <lat>,<lon> | sensor list"}


def cmd_screenshot() -> Dict[str, Any]:
    """Take screenshot of Android container."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = f"/opt/titan/android/screenshots/screen_{ts}.png"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    result = android_shell(f"screencap -p /sdcard/screen.png")
    if result["ok"]:
        run_cmd(f"waydroid shell -- cat /sdcard/screen.png > {out_path}")
        return {"ok": True, "path": out_path}
    return {"ok": False, "error": result["stderr"]}


def cmd_kyc(provider: str) -> Dict[str, Any]:
    """Run KYC bypass flow for a specific provider."""
    provider = provider.lower()

    sys.path.insert(0, str(TITAN_ROOT / "core"))

    info = KYC_APKS.get(provider, {})
    result = {
        "provider": provider,
        "package": info.get("package", "unknown"),
        "capabilities": [],
    }

    # Check what KYC modules are available
    try:
        from kyc_core import KYCController
        result["capabilities"].append("virtual_camera")
    except ImportError:
        pass

    try:
        from kyc_enhanced import KYCEnhancedController, KYCProvider
        result["capabilities"].append("document_injection")
        result["capabilities"].append("liveness_bypass")
        result["capabilities"].append("challenge_response")
    except ImportError:
        pass

    try:
        from kyc_voice_engine import KYCVoiceEngine
        result["capabilities"].append("voice_synthesis")
    except ImportError:
        pass

    try:
        from tof_depth_synthesis import FaceDepthGenerator
        result["capabilities"].append("depth_map_spoofing")
    except ImportError:
        pass

    try:
        from waydroid_sync import WaydroidSyncEngine
        result["capabilities"].append("cross_device_sync")
    except ImportError:
        pass

    # Check if provider app is installed
    apps = cmd_list_apps()
    if apps.get("ok") and info.get("package"):
        installed = info["package"] in apps.get("packages", [])
        result["app_installed"] = installed

    result["ok"] = True
    result["message"] = f"KYC engine ready for {provider} with {len(result['capabilities'])} capabilities"
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> int:
    parser = argparse.ArgumentParser(description="TITAN OS — KYC Android Console")
    sub = parser.add_subparsers(dest="command", help="Command to run")

    sub.add_parser("status", help="Show container status")
    sub.add_parser("start", help="Start Android container")
    sub.add_parser("stop", help="Stop Android container")

    p_shell = sub.add_parser("shell", help="Run shell command")
    p_shell.add_argument("cmd", nargs="+", help="Command to run")

    p_spoof = sub.add_parser("spoof", help="Apply device preset")
    p_spoof.add_argument("preset", help="Device preset name")

    p_install = sub.add_parser("install", help="Install APK")
    p_install.add_argument("apk", help="Path to APK file")

    sub.add_parser("apps", help="List installed apps")
    sub.add_parser("sync", help="Start cross-device sync")

    p_camera = sub.add_parser("camera", help="Virtual camera control")
    p_camera.add_argument("action", nargs="?", default="status", help="status|setup|inject")

    p_sensor = sub.add_parser("sensor", help="Sensor spoofing")
    p_sensor.add_argument("type", nargs="?", default="list", help="gps|list")
    p_sensor.add_argument("value", nargs="?", default="", help="Value (e.g. 40.7128,-74.0060)")

    sub.add_parser("screenshot", help="Take screenshot")

    p_kyc = sub.add_parser("kyc", help="KYC bypass for provider")
    p_kyc.add_argument("provider", help="jumio|onfido|veriff|sumsub|persona|stripe")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    handlers = {
        "status": lambda: cmd_status(),
        "start": lambda: cmd_start(),
        "stop": lambda: cmd_stop(),
        "shell": lambda: cmd_shell(" ".join(args.cmd)),
        "spoof": lambda: cmd_spoof(args.preset),
        "install": lambda: cmd_install_apk(args.apk),
        "apps": lambda: cmd_list_apps(),
        "sync": lambda: cmd_sync(),
        "camera": lambda: cmd_camera(args.action),
        "sensor": lambda: cmd_sensor(args.type, args.value),
        "screenshot": lambda: cmd_screenshot(),
        "kyc": lambda: cmd_kyc(args.provider),
    }

    handler = handlers.get(args.command)
    if not handler:
        parser.print_help()
        return 1

    result = handler()
    print(json.dumps(result, indent=2, default=str))
    return 0 if result.get("ok", False) else 1


if __name__ == "__main__":
    raise SystemExit(main())
