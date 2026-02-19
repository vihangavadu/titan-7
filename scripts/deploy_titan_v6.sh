#!/bin/bash
# LUCID EMPIRE: TITAN V7.0 DEPLOYMENT BRIDGE
# ----------------------------------------
# Deploys TITAN V6 source code into the ISO build structure.
# Handles BOTH legacy /opt/lucid-empire AND new /opt/titan/ paths.

set -eo pipefail

echo "[*] LUCID TITAN V7.0 :: DEPLOYMENT SEQUENCE STARTED"

# 1. Define Paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

SOURCE_ROOT="$REPO_ROOT/titan"
ISO_DEST_LEGACY="$REPO_ROOT/iso/config/includes.chroot/opt/lucid-empire"
ISO_DEST_V6="$REPO_ROOT/iso/config/includes.chroot/opt/titan"
SYSTEMD_DIR="$REPO_ROOT/iso/config/includes.chroot/etc/systemd/system"

# 2. Ensure destinations
mkdir -p "$ISO_DEST_LEGACY"
mkdir -p "$ISO_DEST_LEGACY/ebpf"
mkdir -p "$ISO_DEST_LEGACY/hardware_shield"
mkdir -p "$ISO_DEST_V6/core"
mkdir -p "$ISO_DEST_V6/apps"
mkdir -p "$ISO_DEST_V6/bin"
mkdir -p "$ISO_DEST_V6/extensions/ghost_motor"
mkdir -p "$SYSTEMD_DIR"

# 3. Legacy core removed in V7.0 — all user-facing code is in /opt/titan/
echo "[*] V7.0: Legacy core (TITAN_CONSOLE.py, titan_core.py) removed — using app_unified.py"

# 4. Deploy eBPF Network Shield (no-clobber)
if [ -d "$SOURCE_ROOT/ebpf" ]; then
    echo "[*] Migrating eBPF Network Shield..."
    for f in "$SOURCE_ROOT/ebpf/"*; do
        BASENAME=$(basename "$f")
        if [ ! -f "$ISO_DEST_LEGACY/ebpf/$BASENAME" ]; then
            cp -r "$f" "$ISO_DEST_LEGACY/ebpf/" && echo "  [+] Deployed: $BASENAME"
        else
            echo "  [=] Already exists: $BASENAME (preserving ISO version)"
        fi
    done
else
    echo "[!] Warning: $SOURCE_ROOT/ebpf not found; skipping eBPF copy"
fi

# 5. Deploy Hardware Kernel Module Source (no-clobber)
if [ -d "$SOURCE_ROOT/hardware_shield" ]; then
    echo "[*] Migrating Hardware Shield Source..."
    for f in "$SOURCE_ROOT/hardware_shield/"*; do
        BASENAME=$(basename "$f")
        if [ ! -f "$ISO_DEST_LEGACY/hardware_shield/$BASENAME" ]; then
            cp -r "$f" "$ISO_DEST_LEGACY/hardware_shield/" && echo "  [+] Deployed: $BASENAME"
        else
            echo "  [=] Already exists: $BASENAME (preserving ISO version)"
        fi
    done
else
    echo "[!] Warning: $SOURCE_ROOT/hardware_shield not found; skipping"
fi

# 6. Deploy Mobile Singularity Module (no-clobber)
if [ -d "$SOURCE_ROOT/mobile" ]; then
    echo "[*] Migrating Mobile Singularity Module..."
    mkdir -p "$ISO_DEST_LEGACY/mobile"
    for f in "$SOURCE_ROOT/mobile/"*; do
        BASENAME=$(basename "$f")
        if [ ! -f "$ISO_DEST_LEGACY/mobile/$BASENAME" ]; then
            cp -r "$f" "$ISO_DEST_LEGACY/mobile/" && echo "  [+] Deployed: $BASENAME"
        else
            echo "  [=] Already exists: $BASENAME (preserving ISO version)"
        fi
    done
fi

# 7. V7.0: Ensure /opt/titan/ core library is present
echo "[*] Verifying V7.0 Core Library at $ISO_DEST_V6/core/..."
for f in __init__.py genesis_core.py cerberus_core.py kyc_core.py \
         advanced_profile_generator.py purchase_history_engine.py \
         cerberus_enhanced.py kyc_enhanced.py \
         cognitive_core.py ghost_motor_v6.py quic_proxy.py \
         integration_bridge.py preflight_validator.py target_intelligence.py \
         target_presets.py form_autofill_injector.py \
         location_spoofer_linux.py generate_trajectory_model.py \
         font_sanitizer.py audio_hardener.py timezone_enforcer.py \
         kill_switch.py verify_deep_identity.py titan_master_verify.py \
         fingerprint_injector.py referrer_warmup.py three_ds_strategy.py \
         proxy_manager.py lucid_vpn.py handover_protocol.py \
         network_shield_v6.c hardware_shield_v6.c; do
    if [ -f "$ISO_DEST_V6/core/$f" ]; then
        echo "  [+] V7.0 Core: $f"
    else
        echo "  [!] MISSING V7.0 Core: $f"
    fi
done

# 8. V7.0: Ensure Trinity Apps are present (including Unified Operation Center)
echo "[*] Verifying V7.0 Trinity Apps at $ISO_DEST_V6/apps/..."
for f in app_unified.py app_genesis.py app_cerberus.py app_kyc.py; do
    if [ -f "$ISO_DEST_V6/apps/$f" ]; then
        echo "  [+] V7.0 App: $f"
    else
        echo "  [!] MISSING V7.0 App: $f"
    fi
done

# 9. V7.0: Ensure Ghost Motor extension is present
echo "[*] Verifying V7.0 Ghost Motor Extension..."
for f in manifest.json ghost_motor.js; do
    if [ -f "$ISO_DEST_V6/extensions/ghost_motor/$f" ]; then
        echo "  [+] V7.0 Extension: $f"
    else
        echo "  [!] MISSING V7.0 Extension: $f"
    fi
done

# 10. V7.0: Verify launchers
echo "[*] Verifying V7.0 Launchers at $ISO_DEST_V6/bin/..."
for f in titan-browser titan-launcher titan-first-boot; do
    if [ -f "$ISO_DEST_V6/bin/$f" ]; then
        echo "  [+] V7.0 Bin: $f"
    else
        echo "  [~] Optional: $f"
    fi
done

echo "[+] DEPLOYMENT COMPLETE."
echo "    Next Step: Run 'sudo bash scripts/build_iso.sh' to build the V7.0 ISO."
