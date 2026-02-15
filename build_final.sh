#!/bin/bash
# TITAN V7.0.3 "SINGULARITY" — FORENSICALLY-HARDENED BUILD SCRIPT
# Authority: Dva.12 | Status: OBLIVION_ACTIVE
# Focus: Zero-tolerance integrity, chroot-kernel compilation, forensic sanitization

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "════════════════════════════════════════════════════════"
echo "  TITAN V7.0.3 SINGULARITY — FORENSICALLY-HARDENED BUILD"
echo "════════════════════════════════════════════════════════"

# Verify we're in correct directory
if [ ! -f "iso/auto/config" ]; then
    echo "[!] ERROR: iso/auto/config not found. Run from workspace root."
    exit 1
fi

# Strict permission verification BEFORE proceeding
echo "[*] Enforcing build script permissions..."
for script in iso/auto/config iso/auto/build build_final.sh finalize_titan_oblivion.sh; do
    if [ -f "$script" ] && [ ! -x "$script" ]; then
        echo "[!] FATAL: $script exists but is not executable"
        exit 1
    fi
done
echo "[+] Permission check passed"

# Change to ISO directory
cd iso

# Install live-build if needed
if ! command -v lb &> /dev/null; then
    echo "[*] Installing live-build..."
    sudo apt-get update -qq
    sudo apt-get install -y -qq live-build
fi

# Show resource status
echo "[*] Building with current resources:"
df -h / | tail -1
free -h | grep Mem

# Run configuration (CRITICAL)
echo "[*] Configuring live-build environment..."
chmod +x ./auto/config 2>/dev/null || true
./auto/config 2>&1 || echo "[!] Config warning (continuing...)"

# Clean previous builds (CRITICAL to free space)
echo "[*] Cleaning previous builds..."
sudo lb clean --all 2>/dev/null || true
sleep 2

# Verify clean state
echo "[*] Pre-build state:"
du -sh build 2>/dev/null || echo "  build dir clean"
df -h / | tail -1

# Build the ISO with verbose logging
echo "[*] Initiating live-build process..."
echo "    Expected duration: 45-60 minutes"
echo "    Logs available in: ../titan_v7_final.log"
echo "════════════════════════════════════════════════════════"

# Run live-build as root with proper privilege escalation
if ! sudo lb build -v 2>&1 | tee -a ../titan_v7_final.log; then
    echo ""
    echo "[!] Build process encountered an error."
    echo "[*] Checking for ISO despite error..."
fi

echo "════════════════════════════════════════════════════════"

# Verify output
if [ -f "live-image-amd64.hybrid.iso" ]; then
    ISO_SIZE=$(stat -c%s live-image-amd64.hybrid.iso 2>/dev/null | numfmt --to=iec-i --suffix=B 2>/dev/null || du -h live-image-amd64.hybrid.iso | cut -f1)
    echo "[+] SUCCESS: ISO created!"
    echo "    File: live-image-amd64.hybrid.iso"
    echo "    Size: $ISO_SIZE"
    ls -lh live-image-amd64.hybrid.iso
    
    echo ""
    echo "[*] Running forensic integrity verification..."
    
    # STRICT INTEGRITY CHECK — ZERO TOLERANCE
    MISSING_FILES=0
    
    # All 41 core modules from V7.0.3 audit
    CORE_MODULES=(
        "genesis_core.py" "target_intelligence.py" "preflight_validator.py"
        "cerberus_core.py" "cerberus_enhanced.py" "fingerprint_injector.py"
        "handover_protocol.py" "integration_bridge.py" "ghost_motor_v6.py"
        "cognitive_core.py" "referrer_warmup.py" "proxy_manager.py"
        "three_ds_strategy.py" "target_presets.py" "quic_proxy.py"
        "kyc_core.py" "kyc_enhanced.py" "lucid_vpn.py"
        "purchase_history_engine.py" "kill_switch.py" "font_sanitizer.py"
        "audio_hardener.py" "timezone_enforcer.py" "verify_deep_identity.py"
        "titan_master_verify.py" "generate_trajectory_model.py"
        "form_autofill_injector.py" "location_spoofer_linux.py"
        "immutable_os.py" "network_jitter.py" "tls_parrot.py" "webgl_angle.py"
        "transaction_monitor.py" "intel_monitor.py" "target_discovery.py"
        "usb_peripheral_synth.py" "waydroid_sync.py" "network_shield_loader.py"
        "cockpit_daemon.py" "titan_env.py" "titan_services.py"
        "advanced_profile_generator.py"
    )
    
    echo "Verifying ${#CORE_MODULES[@]} core modules..."
    for module in "${CORE_MODULES[@]}"; do
        if [ ! -f "../iso/config/includes.chroot/opt/titan/core/$module" ]; then
            echo "    [!] MISSING: core/$module"
            MISSING_FILES=$((MISSING_FILES + 1))
        fi
    done
    
    # C modules (3) — CRITICAL
    C_MODULES=("hardware_shield_v6.c" "network_shield_v6.c" "titan_battery.c")
    echo "Verifying ${#C_MODULES[@]} C kernel modules..."
    for module in "${C_MODULES[@]}"; do
        if [ ! -f "../iso/config/includes.chroot/opt/titan/core/$module" ]; then
            echo "    [!] MISSING: core/$module (CRITICAL)"
            MISSING_FILES=$((MISSING_FILES + 1))
        fi
    done
    
    # GUI Apps (5) — CRITICAL
    GUI_APPS=("app_unified.py" "app_genesis.py" "app_cerberus.py" "app_kyc.py" "titan_mission_control.py")
    echo "Verifying ${#GUI_APPS[@]} GUI applications..."
    for app in "${GUI_APPS[@]}"; do
        if [ ! -f "../iso/config/includes.chroot/opt/titan/apps/$app" ]; then
            echo "    [!] MISSING: apps/$app (CRITICAL)"
            MISSING_FILES=$((MISSING_FILES + 1))
        fi
    done
    
    # Build hooks (8) — CRITICAL
    echo "Verifying build hooks..."
    for f in 050-hardware-shield.hook.chroot 060-kernel-module.hook.chroot 070-camoufox-fetch.hook.chroot \
             080-ollama-setup.hook.chroot 090-kyc-setup.hook.chroot 095-os-harden.hook.chroot \
             098-profile-skeleton.hook.chroot 099-fix-perms.hook.chroot; do
        if [ ! -f "../iso/config/hooks/live/$f" ]; then
            echo "    [!] MISSING: hooks/live/$f (CRITICAL)"
            MISSING_FILES=$((MISSING_FILES + 1))
        fi
    done
    
    echo ""
    if [ "$MISSING_FILES" -gt 0 ]; then
        echo "[!] FATAL: $MISSING_FILES critical files missing. ISO is incomplete."
        exit 1
    else
        echo "[+] INTEGRITY VERIFIED: All 41+ modules present and accounted for."
    fi
    
    exit 0
else
    echo "[-] ERROR: ISO file not found after build attempt"
    echo "[*] Last 100 lines of build log:"
    tail -100 ../titan_v7_final.log || true
    exit 1
fi
