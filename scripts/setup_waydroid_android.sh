#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# TITAN OS — Waydroid Android VM Setup
# Installs Waydroid (Android container) on Debian 12 VPS with:
#   - LineageOS 18.1 (Android 11) system image from official OTA
#   - GAPPS variant (Google Play Services for KYC app compatibility)
#   - Pre-configured for headless operation via XRDP/VNC
#   - Custom KYC app deployment into the Android container
#
# Usage:
#   bash setup_waydroid_android.sh [--gapps|--vanilla] [--headless]
#
# Requirements:
#   - Debian 12 (bookworm) or Ubuntu 22.04+
#   - Linux kernel 5.15+ with binder/ashmem support
#   - At least 4GB RAM, 10GB disk
# ═══════════════════════════════════════════════════════════════════════════

set -euo pipefail

TITAN_ROOT="/opt/titan"
WAYDROID_DIR="/var/lib/waydroid"
WAYDROID_IMAGES="${WAYDROID_DIR}/images"
ANDROID_DATA="${WAYDROID_DIR}/data"
LOG_FILE="/var/log/titan-waydroid-setup.log"
VARIANT="${1:---gapps}"  # --gapps or --vanilla
HEADLESS="${2:-}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log() { echo -e "${CYAN}[TITAN-WAYDROID]${NC} $1" | tee -a "$LOG_FILE"; }
ok()  { echo -e "${GREEN}[✓]${NC} $1" | tee -a "$LOG_FILE"; }
warn(){ echo -e "${YELLOW}[!]${NC} $1" | tee -a "$LOG_FILE"; }
err() { echo -e "${RED}[✗]${NC} $1" | tee -a "$LOG_FILE"; }

# ───────────────────────────────────────────────────────────────────────────
# STEP 1: Kernel Check — Waydroid needs binder + ashmem
# ───────────────────────────────────────────────────────────────────────────
check_kernel() {
    log "Checking kernel compatibility..."

    KERNEL_VER=$(uname -r)
    log "Kernel: ${KERNEL_VER}"

    # Check for binder support (required by Android container)
    if [ -e /dev/binderfs/binder ] || [ -e /dev/binder ]; then
        ok "Binder device found"
    elif modprobe binder_linux 2>/dev/null; then
        ok "binder_linux module loaded"
    elif grep -q "CONFIG_ANDROID_BINDER_IPC=y" /boot/config-$(uname -r) 2>/dev/null; then
        ok "Binder compiled into kernel"
    else
        warn "Binder not found — will install DKMS modules"
        NEED_BINDER_DKMS=1
    fi

    # Check for ashmem
    if [ -e /dev/ashmem ]; then
        ok "Ashmem device found"
    elif modprobe ashmem_linux 2>/dev/null; then
        ok "ashmem_linux module loaded"
    else
        warn "Ashmem not found — will install DKMS modules"
        NEED_ASHMEM_DKMS=1
    fi
}

# ───────────────────────────────────────────────────────────────────────────
# STEP 2: Install Dependencies
# ───────────────────────────────────────────────────────────────────────────
install_deps() {
    log "Installing dependencies..."

    # Add Waydroid repo (official)
    if [ ! -f /usr/share/keyrings/waydroid.gpg ]; then
        log "Adding Waydroid repository..."
        apt-get install -y curl ca-certificates gnupg lsb-release 2>&1 | tail -1
        curl -fsSL https://repo.waydro.id/waydroid.gpg | gpg --dearmor -o /usr/share/keyrings/waydroid.gpg
        echo "deb [signed-by=/usr/share/keyrings/waydroid.gpg] https://repo.waydro.id/ bookworm main" > /etc/apt/sources.list.d/waydroid.list
        ok "Waydroid repository added"
    fi

    apt-get update -qq 2>&1 | tail -1

    # Install Waydroid and dependencies
    PACKAGES=(
        waydroid
        python3-gbinder
        lxc
        dnsmasq-base
        iptables
    )

    # Install binder/ashmem DKMS if needed
    if [ "${NEED_BINDER_DKMS:-0}" = "1" ] || [ "${NEED_ASHMEM_DKMS:-0}" = "1" ]; then
        PACKAGES+=(linux-headers-$(uname -r) dkms)
    fi

    # For headless: install weston compositor
    if [ "$HEADLESS" = "--headless" ] || [ ! -d /tmp/.X11-unix ]; then
        PACKAGES+=(weston)
    fi

    apt-get install -y "${PACKAGES[@]}" 2>&1 | tail -5
    ok "Dependencies installed"

    # Install binder DKMS if needed
    if [ "${NEED_BINDER_DKMS:-0}" = "1" ]; then
        log "Building binder DKMS modules..."
        if ! dpkg -l | grep -q "anbox-modules-dkms"; then
            # Build from source if package not available
            if [ ! -d /usr/src/anbox-modules ]; then
                git clone https://github.com/AsteroidOS/anbox-modules.git /usr/src/anbox-modules 2>&1 | tail -2
                cd /usr/src/anbox-modules
                ./INSTALL.sh 2>&1 | tail -3
            fi
        fi
        modprobe binder_linux 2>/dev/null || true
        modprobe ashmem_linux 2>/dev/null || true
    fi
}

# ───────────────────────────────────────────────────────────────────────────
# STEP 3: Initialize Waydroid with Android Image
# ───────────────────────────────────────────────────────────────────────────
init_waydroid() {
    log "Initializing Waydroid..."

    # Determine image type
    if [ "$VARIANT" = "--gapps" ]; then
        IMAGE_TYPE="GAPPS"
        log "Using GAPPS image (Google Play Services — required for most KYC apps)"
    else
        IMAGE_TYPE="VANILLA"
        log "Using VANILLA image (no Google services)"
    fi

    # Waydroid init downloads LineageOS 18.1 (Android 11) images automatically
    # from the official OTA server: https://ota.waydro.id/
    # Images: system.img (~800MB) + vendor.img (~250MB)
    # These are the best prebuilt images for Waydroid — maintained by the project
    waydroid init -s $IMAGE_TYPE -f 2>&1 | tee -a "$LOG_FILE"

    # Verify images were downloaded
    if [ -f "${WAYDROID_IMAGES}/system.img" ] && [ -f "${WAYDROID_IMAGES}/vendor.img" ]; then
        SYSTEM_SIZE=$(du -sh "${WAYDROID_IMAGES}/system.img" | cut -f1)
        VENDOR_SIZE=$(du -sh "${WAYDROID_IMAGES}/vendor.img" | cut -f1)
        ok "Android images downloaded: system.img=${SYSTEM_SIZE}, vendor.img=${VENDOR_SIZE}"
    else
        err "Failed to download Android images!"
        err "Manual fallback: download from https://ota.waydro.id/system"
        err "Place system.img and vendor.img in ${WAYDROID_IMAGES}/"
        exit 1
    fi

    ok "Waydroid initialized with LineageOS 18.1 (Android 11) ${IMAGE_TYPE}"
}

# ───────────────────────────────────────────────────────────────────────────
# STEP 4: Configure Android Properties (Device Spoofing)
# ───────────────────────────────────────────────────────────────────────────
configure_android_props() {
    log "Configuring Android device properties..."

    PROP_FILE="/var/lib/waydroid/waydroid_base.prop"

    # These props make the Android container appear as a real Pixel 7
    # Critical for passing SafetyNet/Play Integrity and KYC device checks
    cat > "$PROP_FILE" << 'PROPS'
# ═══════════════════════════════════════════════════════════════════
# TITAN OS — Android Device Properties (Pixel 7 identity)
# Applied at Waydroid container boot
# ═══════════════════════════════════════════════════════════════════

# Device identity — Pixel 7 (panther)
ro.product.model=Pixel 7
ro.product.brand=google
ro.product.name=panther
ro.product.device=panther
ro.product.manufacturer=Google
ro.product.board=pantah

# Build fingerprint — must match real Pixel 7 builds
ro.build.fingerprint=google/panther/panther:14/AP2A.240805.005/12025142:user/release-keys
ro.build.display.id=AP2A.240805.005
ro.build.version.release=14
ro.build.version.sdk=34
ro.build.version.security_patch=2024-08-05

# Hardware props
ro.hardware.chipname=Tensor G2
persist.sys.dalvik.vm.lib.2=libart.so

# Screen
ro.sf.lcd_density=420
persist.sys.display_size=1080x2400

# Locale/timezone (overridden at runtime by waydroid_sync.py)
persist.sys.timezone=America/New_York
persist.sys.locale=en_US
persist.sys.language=en
persist.sys.country=US

# Network — look like a real cellular device
gsm.version.baseband=g5300g-230420-240506-B-11648009
gsm.sim.operator.numeric=310260
gsm.operator.alpha=T-Mobile
gsm.operator.numeric=310260

# Google Play Services compatibility
ro.com.google.gmsversion=14_202408
ro.com.google.clientidbase=android-google

# Hide emulator/container indicators
ro.kernel.qemu=0
ro.hardware.virtual=0
ro.boot.container=0
ro.debuggable=0
ro.secure=1
PROPS

    ok "Android device properties configured (Pixel 7 identity)"
}

# ───────────────────────────────────────────────────────────────────────────
# STEP 5: Configure Waydroid Networking
# ───────────────────────────────────────────────────────────────────────────
configure_networking() {
    log "Configuring Waydroid networking..."

    # Enable IP forwarding for Android container
    sysctl -w net.ipv4.ip_forward=1 > /dev/null
    echo "net.ipv4.ip_forward=1" >> /etc/sysctl.d/99-titan-waydroid.conf 2>/dev/null || true

    # NAT for Android container traffic (uses waydroid0 bridge)
    iptables -t nat -A POSTROUTING -s 192.168.240.0/24 -o eth0 -j MASQUERADE 2>/dev/null || true

    # Persist iptables rules
    if command -v iptables-save &>/dev/null; then
        iptables-save > /etc/iptables/rules.v4 2>/dev/null || true
    fi

    ok "Networking configured (NAT + forwarding)"
}

# ───────────────────────────────────────────────────────────────────────────
# STEP 6: Create Systemd Service for Waydroid Container
# ───────────────────────────────────────────────────────────────────────────
create_service() {
    log "Creating systemd service..."

    cat > /etc/systemd/system/titan-waydroid.service << 'SERVICE'
[Unit]
Description=TITAN OS — Waydroid Android Container
After=network-online.target
Wants=network-online.target
After=waydroid-container.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStartPre=/usr/bin/waydroid container start
ExecStart=/usr/bin/waydroid session start
ExecStop=/usr/bin/waydroid session stop
ExecStopPost=/usr/bin/waydroid container stop
TimeoutStartSec=60
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
SERVICE

    systemctl daemon-reload
    systemctl enable titan-waydroid.service 2>/dev/null || true
    ok "Systemd service created (titan-waydroid.service)"
}

# ───────────────────────────────────────────────────────────────────────────
# STEP 7: Deploy KYC Console App into Android Container
# ───────────────────────────────────────────────────────────────────────────
deploy_kyc_app() {
    log "Deploying KYC console app into Android container..."

    # Create the KYC controller script that runs inside Android
    KYC_CONSOLE_DIR="${TITAN_ROOT}/android"
    mkdir -p "$KYC_CONSOLE_DIR"

    cat > "${KYC_CONSOLE_DIR}/kyc_android_console.py" << 'PYSCRIPT'
#!/usr/bin/env python3
"""
TITAN OS — KYC Android Console Controller
Manages the Waydroid Android container for KYC operations.

This console provides:
1. Container lifecycle management (start/stop/status)
2. Device property manipulation (spoof device identity)
3. App installation and management
4. ADB-over-Waydroid shell commands
5. Camera/sensor injection coordination
6. Cross-device sync with desktop browser

Usage:
    python3 kyc_android_console.py [command] [args]

Commands:
    status          Show container and device status
    start           Start Waydroid session
    stop            Stop Waydroid session
    shell <cmd>     Execute shell command in Android
    install <apk>   Install APK into container
    uninstall <pkg> Uninstall package
    prop <key> <val> Set system property
    spoof <device>  Apply device preset (pixel7/s24/iphone_spoof)
    camera          Show camera injection status
    sync            Trigger cross-device cookie sync
    apps            List installed apps
    screenshot      Take screenshot of Android screen
    input <event>   Send input event (tap/swipe/key)
    logcat [filter] Show Android logcat
"""

import os
import sys
import json
import subprocess
import time
import argparse
from pathlib import Path
from typing import Optional, Dict, List, Tuple

WAYDROID_DIR = "/var/lib/waydroid"
TITAN_ROOT = "/opt/titan"
PROP_FILE = f"{WAYDROID_DIR}/waydroid_base.prop"

# Device presets for quick spoofing
DEVICE_PRESETS = {
    "pixel7": {
        "ro.product.model": "Pixel 7",
        "ro.product.brand": "google",
        "ro.product.device": "panther",
        "ro.build.fingerprint": "google/panther/panther:14/AP2A.240805.005/12025142:user/release-keys",
        "ro.build.version.release": "14",
        "ro.build.version.sdk": "34",
        "ro.sf.lcd_density": "420",
    },
    "pixel8pro": {
        "ro.product.model": "Pixel 8 Pro",
        "ro.product.brand": "google",
        "ro.product.device": "husky",
        "ro.build.fingerprint": "google/husky/husky:14/AP2A.240805.005/12025142:user/release-keys",
        "ro.build.version.release": "14",
        "ro.build.version.sdk": "34",
        "ro.sf.lcd_density": "420",
    },
    "s24": {
        "ro.product.model": "SM-S921B",
        "ro.product.brand": "samsung",
        "ro.product.device": "e1s",
        "ro.build.fingerprint": "samsung/e1sxxx/e1s:14/UP1A.231005.007/S921BXXU1AXA6:user/release-keys",
        "ro.build.version.release": "14",
        "ro.build.version.sdk": "34",
        "ro.sf.lcd_density": "480",
    },
    "s23": {
        "ro.product.model": "SM-S911B",
        "ro.product.brand": "samsung",
        "ro.product.device": "dm1q",
        "ro.build.fingerprint": "samsung/dm1qxxx/dm1q:14/UP1A.231005.007/S911BXXU5CXA4:user/release-keys",
        "ro.build.version.release": "14",
        "ro.build.version.sdk": "34",
        "ro.sf.lcd_density": "425",
    },
    "oneplus12": {
        "ro.product.model": "CPH2583",
        "ro.product.brand": "OnePlus",
        "ro.product.device": "CPH2583",
        "ro.build.fingerprint": "OnePlus/CPH2583/CPH2583:14/UKQ1.230924.001/V1.0.1:user/release-keys",
        "ro.build.version.release": "14",
        "ro.build.version.sdk": "34",
        "ro.sf.lcd_density": "480",
    },
}

# Common KYC-related apps to install
KYC_TARGET_APPS = {
    "chrome": "com.android.chrome",
    "gmail": "com.google.android.gm",
    "maps": "com.google.android.apps.maps",
    "play_store": "com.android.vending",
    "camera": "com.android.camera2",
}


def waydroid_shell(cmd: str, timeout: int = 15) -> Tuple[bool, str]:
    """Execute command in Waydroid Android shell."""
    try:
        result = subprocess.run(
            ["waydroid", "shell", "--", "sh", "-c", cmd],
            capture_output=True, text=True, timeout=timeout,
        )
        return result.returncode == 0, result.stdout.strip()
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except FileNotFoundError:
        return False, "waydroid not installed"


def waydroid_cmd(args: List[str], timeout: int = 30) -> Tuple[bool, str]:
    """Execute waydroid command."""
    try:
        result = subprocess.run(
            ["waydroid"] + args,
            capture_output=True, text=True, timeout=timeout,
        )
        return result.returncode == 0, result.stdout.strip()
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except FileNotFoundError:
        return False, "waydroid not installed"


def cmd_status():
    """Show container and device status."""
    print("=" * 60)
    print("  TITAN OS — Android Container Status")
    print("=" * 60)

    # Waydroid status
    ok, output = waydroid_cmd(["status"])
    if ok:
        for line in output.split("\n"):
            print(f"  {line}")
    else:
        print(f"  Waydroid: NOT RUNNING ({output})")

    # Check images
    sys_img = Path(f"{WAYDROID_DIR}/images/system.img")
    vendor_img = Path(f"{WAYDROID_DIR}/images/vendor.img")
    print(f"\n  System image:  {'EXISTS' if sys_img.exists() else 'MISSING'}")
    print(f"  Vendor image:  {'EXISTS' if vendor_img.exists() else 'MISSING'}")

    # Device props
    if Path(PROP_FILE).exists():
        props = Path(PROP_FILE).read_text()
        for key in ["ro.product.model", "ro.build.version.release", "persist.sys.timezone"]:
            for line in props.split("\n"):
                if line.startswith(key):
                    print(f"  {line}")
                    break

    # Android shell test
    ok, output = waydroid_shell("getprop ro.product.model")
    if ok:
        print(f"\n  Live device model: {output}")
    else:
        print(f"\n  Android shell: not available")

    print("=" * 60)


def cmd_start():
    """Start Waydroid session."""
    print("[*] Starting Waydroid container...")
    ok, out = waydroid_cmd(["container", "start"])
    if not ok:
        print(f"[!] Container start failed: {out}")
        return

    time.sleep(2)
    print("[*] Starting Waydroid session...")
    ok, out = waydroid_cmd(["session", "start"])
    if ok:
        print("[+] Waydroid session started")
    else:
        print(f"[!] Session start failed: {out}")


def cmd_stop():
    """Stop Waydroid session."""
    print("[*] Stopping Waydroid session...")
    waydroid_cmd(["session", "stop"])
    waydroid_cmd(["container", "stop"])
    print("[+] Waydroid stopped")


def cmd_shell(command: str):
    """Execute shell command in Android."""
    ok, output = waydroid_shell(command, timeout=30)
    if ok:
        print(output)
    else:
        print(f"[!] Command failed: {output}")


def cmd_install(apk_path: str):
    """Install APK into Android container."""
    if not os.path.exists(apk_path):
        print(f"[!] APK not found: {apk_path}")
        return
    print(f"[*] Installing {apk_path}...")
    ok, out = waydroid_cmd(["app", "install", apk_path])
    if ok:
        print(f"[+] Installed: {apk_path}")
    else:
        print(f"[!] Install failed: {out}")


def cmd_uninstall(package: str):
    """Uninstall package from Android container."""
    print(f"[*] Uninstalling {package}...")
    ok, out = waydroid_shell(f"pm uninstall {package}")
    print(f"[+] {out}" if ok else f"[!] Failed: {out}")


def cmd_prop(key: str, value: str):
    """Set system property in Android container."""
    # Set live
    ok, _ = waydroid_shell(f"setprop {key} '{value}'")

    # Also persist to prop file
    prop_path = Path(PROP_FILE)
    if prop_path.exists():
        lines = prop_path.read_text().split("\n")
        found = False
        for i, line in enumerate(lines):
            if line.startswith(f"{key}="):
                lines[i] = f"{key}={value}"
                found = True
                break
        if not found:
            lines.append(f"{key}={value}")
        prop_path.write_text("\n".join(lines))

    print(f"[+] {key}={value}")


def cmd_spoof(device_name: str):
    """Apply device preset."""
    preset = DEVICE_PRESETS.get(device_name)
    if not preset:
        print(f"[!] Unknown device: {device_name}")
        print(f"    Available: {', '.join(DEVICE_PRESETS.keys())}")
        return

    print(f"[*] Applying device preset: {device_name}")
    for key, value in preset.items():
        cmd_prop(key, value)
    print(f"[+] Device spoofed as {preset.get('ro.product.model', device_name)}")
    print("[!] Restart Waydroid session for full effect")


def cmd_apps():
    """List installed apps."""
    ok, output = waydroid_shell("pm list packages -3")
    if ok:
        packages = [line.replace("package:", "") for line in output.split("\n") if line]
        print(f"Installed apps ({len(packages)}):")
        for pkg in sorted(packages):
            print(f"  {pkg}")
    else:
        print(f"[!] Could not list apps: {output}")


def cmd_screenshot():
    """Take screenshot of Android screen."""
    out_path = "/tmp/titan_android_screenshot.png"
    ok, _ = waydroid_shell(f"screencap -p /sdcard/screenshot.png")
    if ok:
        # Pull from Android
        subprocess.run(["cp", f"{WAYDROID_DIR}/data/media/0/screenshot.png", out_path],
                       capture_output=True)
        print(f"[+] Screenshot saved: {out_path}")
    else:
        print("[!] Screenshot failed — is session running?")


def cmd_input(event_str: str):
    """Send input event to Android."""
    ok, out = waydroid_shell(f"input {event_str}")
    if ok:
        print(f"[+] Input sent: {event_str}")
    else:
        print(f"[!] Input failed: {out}")


def cmd_logcat(filter_str: str = ""):
    """Show Android logcat."""
    cmd = ["waydroid", "logcat"]
    if filter_str:
        cmd.extend(["-s", filter_str])
    try:
        subprocess.run(cmd, timeout=10)
    except subprocess.TimeoutExpired:
        pass
    except KeyboardInterrupt:
        pass


def cmd_sync():
    """Trigger cross-device cookie sync."""
    sys.path.insert(0, f"{TITAN_ROOT}/core")
    try:
        from waydroid_sync import WaydroidSyncEngine, SyncConfig
        engine = WaydroidSyncEngine()
        config = SyncConfig()
        if engine.initialize(config):
            print("[+] Cross-device sync initialized")
            engine.start_background_activity(target="")
            print("[+] Background mobile activity started")
        else:
            print("[!] Sync initialization failed — is Waydroid running?")
    except ImportError:
        print("[!] waydroid_sync module not found in /opt/titan/core/")
    except Exception as e:
        print(f"[!] Sync error: {e}")


def cmd_camera():
    """Show camera injection status."""
    print("Camera Injection Status:")
    # Check v4l2loopback
    ok, out = subprocess.run(["lsmod"], capture_output=True, text=True).stdout, ""
    if "v4l2loopback" in (ok if isinstance(ok, str) else ""):
        print("  v4l2loopback: LOADED")
    else:
        print("  v4l2loopback: NOT LOADED")

    # Check /dev/video devices
    for i in range(10):
        dev = f"/dev/video{i}"
        if os.path.exists(dev):
            print(f"  {dev}: exists")


def main():
    parser = argparse.ArgumentParser(
        description="TITAN OS — KYC Android Console Controller",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status", help="Show container status")
    sub.add_parser("start", help="Start Waydroid session")
    sub.add_parser("stop", help="Stop Waydroid session")
    p = sub.add_parser("shell", help="Execute Android shell command")
    p.add_argument("cmd", nargs="+")
    p = sub.add_parser("install", help="Install APK")
    p.add_argument("apk")
    p = sub.add_parser("uninstall", help="Uninstall package")
    p.add_argument("package")
    p = sub.add_parser("prop", help="Set system property")
    p.add_argument("key")
    p.add_argument("value")
    p = sub.add_parser("spoof", help="Apply device preset")
    p.add_argument("device", choices=list(DEVICE_PRESETS.keys()))
    sub.add_parser("apps", help="List installed apps")
    sub.add_parser("screenshot", help="Take screenshot")
    p = sub.add_parser("input", help="Send input event")
    p.add_argument("event", nargs="+")
    p = sub.add_parser("logcat", help="Show logcat")
    p.add_argument("filter", nargs="?", default="")
    sub.add_parser("sync", help="Trigger cross-device sync")
    sub.add_parser("camera", help="Show camera status")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    commands = {
        "status": cmd_status,
        "start": cmd_start,
        "stop": cmd_stop,
        "shell": lambda: cmd_shell(" ".join(args.cmd)),
        "install": lambda: cmd_install(args.apk),
        "uninstall": lambda: cmd_uninstall(args.package),
        "prop": lambda: cmd_prop(args.key, args.value),
        "spoof": lambda: cmd_spoof(args.device),
        "apps": cmd_apps,
        "screenshot": cmd_screenshot,
        "input": lambda: cmd_input(" ".join(args.event)),
        "logcat": lambda: cmd_logcat(args.filter),
        "sync": cmd_sync,
        "camera": cmd_camera,
    }
    commands[args.command]()


if __name__ == "__main__":
    main()
PYSCRIPT

    chmod +x "${KYC_CONSOLE_DIR}/kyc_android_console.py"

    # Create convenience wrapper
    cat > /usr/local/bin/titan-android << 'WRAPPER'
#!/bin/bash
# TITAN OS — Android Console shortcut
exec python3 /opt/titan/android/kyc_android_console.py "$@"
WRAPPER
    chmod +x /usr/local/bin/titan-android

    ok "KYC Android console deployed: titan-android [command]"
}

# ───────────────────────────────────────────────────────────────────────────
# STEP 8: Create Waydroid Hardening Config
# ───────────────────────────────────────────────────────────────────────────
harden_waydroid() {
    log "Applying Waydroid hardening..."

    WAYDROID_CFG="/var/lib/waydroid/waydroid.cfg"

    if [ -f "$WAYDROID_CFG" ]; then
        # Ensure GPU rendering mode (software fallback for VPS)
        if ! grep -q "ro.hardware.gralloc" "$WAYDROID_CFG"; then
            cat >> "$WAYDROID_CFG" << 'HARDENCFG'

# TITAN OS Hardening
[properties]
ro.hardware.gralloc=default
ro.hardware.egl=swiftshader
persist.waydroid.multi_windows=true
persist.waydroid.fake_touch=1
persist.waydroid.width=1080
persist.waydroid.height=2400
HARDENCFG
        fi
    fi

    # Hide Waydroid indicators from Android apps
    waydroid_shell "settings put global development_settings_enabled 0" 2>/dev/null || true
    waydroid_shell "settings put global adb_enabled 0" 2>/dev/null || true

    ok "Waydroid hardened (SwiftShader GPU, hidden dev settings)"
}

# ───────────────────────────────────────────────────────────────────────────
# STEP 9: Integration Test
# ───────────────────────────────────────────────────────────────────────────
run_tests() {
    log "Running integration tests..."

    PASS=0
    FAIL=0

    # Test 1: Waydroid binary exists
    if command -v waydroid &>/dev/null; then
        ok "waydroid binary: found"
        ((PASS++))
    else
        err "waydroid binary: NOT FOUND"
        ((FAIL++))
    fi

    # Test 2: System image exists
    if [ -f "${WAYDROID_IMAGES}/system.img" ]; then
        ok "system.img: exists"
        ((PASS++))
    else
        err "system.img: MISSING"
        ((FAIL++))
    fi

    # Test 3: Vendor image exists
    if [ -f "${WAYDROID_IMAGES}/vendor.img" ]; then
        ok "vendor.img: exists"
        ((PASS++))
    else
        err "vendor.img: MISSING"
        ((FAIL++))
    fi

    # Test 4: Prop file exists
    if [ -f "$PROP_FILE" ]; then
        ok "waydroid_base.prop: configured"
        ((PASS++))
    else
        err "waydroid_base.prop: MISSING"
        ((FAIL++))
    fi

    # Test 5: KYC console exists
    if [ -f "${TITAN_ROOT}/android/kyc_android_console.py" ]; then
        ok "KYC Android console: deployed"
        ((PASS++))
    else
        err "KYC Android console: MISSING"
        ((FAIL++))
    fi

    # Test 6: titan-android wrapper
    if [ -f "/usr/local/bin/titan-android" ]; then
        ok "titan-android CLI: installed"
        ((PASS++))
    else
        err "titan-android CLI: MISSING"
        ((FAIL++))
    fi

    # Test 7: Systemd service
    if systemctl list-unit-files | grep -q "titan-waydroid"; then
        ok "titan-waydroid.service: registered"
        ((PASS++))
    else
        err "titan-waydroid.service: NOT REGISTERED"
        ((FAIL++))
    fi

    # Test 8: Python core modules
    if python3 -c "import sys; sys.path.insert(0, '${TITAN_ROOT}/core'); from waydroid_sync import WaydroidSyncEngine" 2>/dev/null; then
        ok "waydroid_sync.py: importable"
        ((PASS++))
    else
        err "waydroid_sync.py: IMPORT FAILED"
        ((FAIL++))
    fi

    echo ""
    echo "═══════════════════════════════════════════════════════"
    echo "  Results: ${PASS} passed, ${FAIL} failed"
    echo "═══════════════════════════════════════════════════════"
}

# ───────────────────────────────────────────────────────────────────────────
# MAIN
# ───────────────────────────────────────────────────────────────────────────

echo "═══════════════════════════════════════════════════════════════════"
echo "  TITAN OS — Waydroid Android VM Setup"
echo "  Image: LineageOS 18.1 (Android 11) from official OTA"
echo "  Variant: ${VARIANT}"
echo "═══════════════════════════════════════════════════════════════════"
echo ""

# Must be root
if [ "$(id -u)" -ne 0 ]; then
    err "This script must be run as root"
    exit 1
fi

mkdir -p "$(dirname "$LOG_FILE")"
echo "[$(date)] Waydroid setup started" > "$LOG_FILE"

check_kernel
install_deps
init_waydroid
configure_android_props
configure_networking
create_service
deploy_kyc_app
harden_waydroid

echo ""
log "Starting Waydroid for first boot..."
waydroid container start 2>/dev/null || true
sleep 3
waydroid session start 2>/dev/null || true
sleep 5

harden_waydroid

echo ""
run_tests

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "  Setup complete!"
echo ""
echo "  Quick start:"
echo "    titan-android status     # Check container status"
echo "    titan-android start      # Start Android session"
echo "    titan-android spoof pixel7  # Spoof as Pixel 7"
echo "    titan-android shell 'getprop ro.product.model'"
echo "    titan-android sync       # Start cross-device sync"
echo "    titan-android apps       # List installed apps"
echo "═══════════════════════════════════════════════════════════════════"
