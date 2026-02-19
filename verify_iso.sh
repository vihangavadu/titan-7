#!/bin/bash
# ==============================================================================
# LUCID EMPIRE :: TITAN V7.0 SINGULARITY — POST-BUILD ISO VERIFIER
# ==============================================================================
# AUTHORITY: Dva.12
# PURPOSE:   Comprehensive verification of built ISO — checks every component.
#
# Usage:
#   sudo bash scripts/verify_iso.sh [path-to-iso]
#   bash scripts/verify_iso.sh --source-only
# ==============================================================================

set -eo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

PASS=0; FAIL=0; WARN=0; TOTAL=0

pass() { PASS=$((PASS+1)); TOTAL=$((TOTAL+1)); echo -e "  ${GREEN}[PASS]${NC} $1"; }
fail() { FAIL=$((FAIL+1)); TOTAL=$((TOTAL+1)); echo -e "  ${RED}[FAIL]${NC} $1"; }
skip() { WARN=$((WARN+1)); TOTAL=$((TOTAL+1)); echo -e "  ${YELLOW}[WARN]${NC} $1"; }

hdr() {
    echo ""
    echo -e "${CYAN}${BOLD}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}${BOLD}  $1${NC}"
    echo -e "${CYAN}${BOLD}═══════════════════════════════════════════════════════════${NC}"
}

cf() { if [ -f "$1" ]; then pass "$2"; else fail "$2"; fi; }
cd2() { if [ -d "$1" ]; then pass "$2"; else fail "$2"; fi; }
cx() { if [ -x "$1" ]; then pass "$2"; elif [ -f "$1" ]; then skip "$2 (not +x)"; else fail "$2"; fi; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Detect repo root: if script is in scripts/, go up one; otherwise script is at repo root
if [ -d "$SCRIPT_DIR/iso" ]; then
    REPO_ROOT="$SCRIPT_DIR"
else
    REPO_ROOT="$(dirname "$SCRIPT_DIR")"
fi
cd "$REPO_ROOT"

ISO_DIR="$REPO_ROOT/iso"
SOURCE_MODE=false; ISO_MOUNTED=false; MOUNT_DIR=""; ROOT=""

if [ "${1:-}" = "--source-only" ]; then
    SOURCE_MODE=true
    ROOT="$ISO_DIR/config/includes.chroot"
elif [ -n "${1:-}" ] && [ -f "$1" ]; then
    ISO_PATH="$1"
elif ls "$REPO_ROOT"/*.iso 1>/dev/null 2>&1; then
    ISO_PATH=$(ls -t "$REPO_ROOT"/*.iso | head -1)
    echo -e "${CYAN}Auto-detected: ${ISO_PATH}${NC}"
else
    SOURCE_MODE=true
    ROOT="$ISO_DIR/config/includes.chroot"
    echo -e "${YELLOW}No ISO found — source-tree mode${NC}"
fi

if [ "$SOURCE_MODE" = false ]; then
    [ "$EUID" -ne 0 ] && { echo -e "${RED}Need root to mount ISO. Use --source-only${NC}"; exit 1; }
    MOUNT_DIR=$(mktemp -d /tmp/titan-verify.XXXXXX)
    SQUASH_DIR=$(mktemp -d /tmp/titan-squash.XXXXXX)
    mount -o loop,ro "$ISO_PATH" "$MOUNT_DIR" 2>/dev/null || { echo -e "${RED}Mount failed${NC}"; exit 1; }
    ISO_MOUNTED=true
    SQUASH_FILE=$(find "$MOUNT_DIR" -name "*.squashfs" -type f 2>/dev/null | head -1)
    if [ -n "$SQUASH_FILE" ]; then
        mount -o loop,ro "$SQUASH_FILE" "$SQUASH_DIR" 2>/dev/null || { umount "$MOUNT_DIR"; exit 1; }
        ROOT="$SQUASH_DIR"
    else
        ROOT="$MOUNT_DIR"
    fi
fi

cleanup() {
    if [ "$ISO_MOUNTED" = true ]; then
        umount "$SQUASH_DIR" 2>/dev/null || true
        umount "$MOUNT_DIR" 2>/dev/null || true
        rmdir "$SQUASH_DIR" "$MOUNT_DIR" 2>/dev/null || true
    fi
}
trap cleanup EXIT

T="$ROOT/opt/titan"
L="$ROOT/opt/lucid-empire"
SV="$ROOT/etc/systemd/system"
DT="$ROOT/usr/share/applications"
XDG="$ROOT/etc/xdg/autostart"
HK="$ISO_DIR/config/hooks/live"
PL="$ISO_DIR/config/package-lists/custom.list.chroot"

hdr "TITAN V7.0 POST-BUILD VERIFIER"
echo -e "  Root: ${ROOT}"
echo -e "  Time: $(date)"

# ── 1. CORE MODULES ─────────────────────────────────────────────────────────
hdr "1/15 — TITAN CORE MODULES"
for m in genesis_core.py advanced_profile_generator.py purchase_history_engine.py \
         cerberus_core.py cerberus_enhanced.py kyc_core.py kyc_enhanced.py \
         integration_bridge.py preflight_validator.py target_intelligence.py \
         target_presets.py fingerprint_injector.py form_autofill_injector.py \
         referrer_warmup.py handover_protocol.py kill_switch.py font_sanitizer.py \
         audio_hardener.py timezone_enforcer.py verify_deep_identity.py \
         titan_master_verify.py ghost_motor_v6.py cognitive_core.py quic_proxy.py \
         proxy_manager.py three_ds_strategy.py lucid_vpn.py location_spoofer_linux.py \
         generate_trajectory_model.py titan_env.py \
         tls_parrot.py webgl_angle.py network_jitter.py \
         immutable_os.py cockpit_daemon.py waydroid_sync.py \
         __init__.py; do
    cf "$T/core/$m" "core/$m"
done
cf "$T/core/hardware_shield_v6.c" "hardware_shield_v6.c (C)"
cf "$T/core/network_shield_v6.c"  "network_shield_v6.c (C)"
cf "$T/core/Makefile"              "Core Makefile"
cx "$T/core/build_ebpf.sh"        "build_ebpf.sh"

# ── 2. GUI APPS ─────────────────────────────────────────────────────────────
hdr "2/15 — GUI APPLICATIONS"
cf "$T/apps/app_unified.py"  "Unified Operation Center"
cf "$T/apps/app_genesis.py"  "Genesis Engine GUI"
cf "$T/apps/app_cerberus.py" "Cerberus Intelligence GUI"
cf "$T/apps/app_kyc.py"      "KYC Reality Synthesis GUI"

# ── 3. LAUNCHERS ─────────────────────────────────────────────────────────────
hdr "3/15 — LAUNCHERS & BIN SCRIPTS"
for b in titan-browser titan-launcher titan-first-boot install-to-disk titan-test titan-vpn-setup; do
    cx "$T/bin/$b" "bin/$b"
done

# ── 4. EXTENSIONS ────────────────────────────────────────────────────────────
hdr "4/15 — EXTENSIONS"
cf "$T/extensions/ghost_motor/ghost_motor.js" "Ghost Motor JS"
cf "$T/extensions/ghost_motor/manifest.json"  "Ghost Motor Manifest"

# ── 5. TESTING ───────────────────────────────────────────────────────────────
hdr "5/15 — TESTING FRAMEWORK"
for t in __init__.py test_runner.py detection_emulator.py titan_adversary_sim.py \
         environment.py psp_sandbox.py report_generator.py; do
    cf "$T/testing/$t" "testing/$t"
done

# ── 6. VPN ───────────────────────────────────────────────────────────────────
hdr "6/15 — VPN INFRASTRUCTURE"
cf "$T/vpn/xray-client.json"     "Xray Client Config"
cf "$T/vpn/xray-server.json"     "Xray Server Config"
cx "$T/vpn/setup-vps-relay.sh"   "VPS Relay Setup"
cx "$T/vpn/setup-exit-node.sh"   "Exit Node Setup"

# ── 7. CONFIG & STATE ────────────────────────────────────────────────────────
hdr "7/15 — CONFIGURATION & STATE"
cf  "$T/config/titan.env" "titan.env"
cd2 "$T/state"            "State dir"
cd2 "$T/profiles"         "Profiles dir"
cd2 "$T/assets/motions"   "Motion assets dir"

# ── 8. BACKEND ───────────────────────────────────────────────────────────────
hdr "8/15 — LUCID-EMPIRE BACKEND"
cx "$L/launch-titan.sh" "Main Launcher"
for bf in server.py lucid_api.py lucid_commander.py lucid_manager.py profile_manager.py \
          warming_engine.py zero_detect.py genesis_engine.py firefox_injector.py \
          firefox_injector_v2.py commerce_injector.py blacklist_validator.py \
          handover_protocol.py __init__.py; do
    cf "$L/backend/$bf" "backend/$bf"
done
for bc in __init__.py genesis_engine.py profile_store.py cortex.py ebpf_loader.py \
          bin_finder.py font_config.py time_displacement.py time_machine.py; do
    cf "$L/backend/core/$bc" "backend/core/$bc"
done
for bm in __init__.py ghost_motor.py fingerprint_manager.py biometric_mimicry.py \
          canvas_noise.py commerce_injector.py commerce_vault.py humanization.py \
          location_spoofer.py tls_masquerade.py ai_assistant.py firefox_injector.py \
          firefox_injector_v2.py; do
    cf "$L/backend/modules/$bm" "backend/modules/$bm"
done
for cer in __init__.py harvester.py validator.py ai_analyst.py; do
    cf "$L/backend/modules/cerberus/$cer" "cerberus/$cer"
done
for kyc in __init__.py app.py camera_injector.py reenactment_engine.py renderer_3d.js package.json; do
    cf "$L/backend/modules/kyc_module/$kyc" "kyc_module/$kyc"
done

# ── 9. LUCID-EMPIRE INFRA ───────────────────────────────────────────────────
hdr "9/15 — LUCID-EMPIRE INFRASTRUCTURE"
cx "$L/bin/titan-backend-init.sh"     "Backend Init"
cx "$L/bin/load-ebpf.sh"             "eBPF Loader"
cf "$L/bin/generate-hw-profile.py"    "HW Profile Generator"
cf "$L/bin/validate-kernel-masking.py" "Kernel Masking Validator"
cf "$L/ebpf/network_shield.c"         "eBPF Network Shield (C)"
cf "$L/ebpf/tcp_fingerprint.c"        "eBPF TCP Fingerprint (C)"
cf "$L/ebpf/network_shield_loader.py" "eBPF Python Loader"
cf "$L/hardware_shield/titan_hw.c"    "Hardware Shield (legacy C)"
cf "$L/hardware_shield/Makefile"      "Hardware Shield Makefile"
cf "$L/data/bins.csv"                  "BIN Database"

# ── 10. SYSTEMD SERVICES ────────────────────────────────────────────────────
hdr "10/15 — SYSTEMD SERVICES"
cf "$SV/lucid-titan.service"      "Backend Service"
cf "$SV/lucid-ebpf.service"      "eBPF Service"
cf "$SV/lucid-console.service"   "GUI Console Service"
cf "$SV/titan-first-boot.service" "First Boot Service"

# Verify service targets correct executables
for svc_check in \
    "lucid-titan.service:titan-backend-init" \
    "lucid-ebpf.service:load-ebpf" \
    "lucid-console.service:app_unified" \
    "titan-first-boot.service:titan-first-boot"; do
    svc="${svc_check%%:*}"; expect="${svc_check##*:}"
    if [ -f "$SV/$svc" ] && grep -q "$expect" "$SV/$svc" 2>/dev/null; then
        pass "$svc → $expect (ExecStart OK)"
    elif [ -f "$SV/$svc" ]; then
        fail "$svc — ExecStart doesn't reference $expect"
    fi
done

# ── 11. DESKTOP ENTRIES ─────────────────────────────────────────────────────
hdr "11/15 — DESKTOP ENTRIES & AUTOSTART"
cf "$DT/titan-unified.desktop" "Operation Center Desktop Icon"
cf "$DT/titan-browser.desktop" "Titan Browser Desktop Icon"
cf "$DT/titan-install.desktop" "Install to Disk Desktop Icon"
cf "$XDG/lucid-titan-console.desktop" "XDG Autostart (GUI on login)"

# Verify Exec lines
if [ -f "$DT/titan-unified.desktop" ] && grep -q "app_unified.py" "$DT/titan-unified.desktop"; then
    pass "titan-unified.desktop Exec → app_unified.py"
else
    [ -f "$DT/titan-unified.desktop" ] && fail "titan-unified.desktop bad Exec"
fi
if [ -f "$DT/titan-browser.desktop" ] && grep -q "titan-browser" "$DT/titan-browser.desktop"; then
    pass "titan-browser.desktop Exec → titan-browser"
else
    [ -f "$DT/titan-browser.desktop" ] && fail "titan-browser.desktop bad Exec"
fi

# ── 12. BUILD HOOKS ──────────────────────────────────────────────────────────
hdr "12/15 — BUILD HOOKS"
for h in 050-hardware-shield 060-kernel-module 070-camoufox-fetch 080-ollama-setup 090-kyc-setup 99-fix-perms; do
    cx "$HK/${h}.hook.chroot" "${h}.hook.chroot"
done

# ── 13. PACKAGE LIST ─────────────────────────────────────────────────────────
hdr "13/15 — PACKAGE LIST AUDIT"
if [ -f "$PL" ]; then
    PKG_COUNT=$(grep -cv '^\s*#\|^\s*$' "$PL" 2>/dev/null || echo 0)
    pass "custom.list.chroot ($PKG_COUNT packages)"

    REQUIRED_PKGS=(
        task-xfce-desktop rofi live-boot live-config live-config-systemd
        build-essential gcc clang llvm
        linux-headers-amd64 bpfcc-tools libbpf-dev
        python3 python3-pip python3-dev python3-venv
        firefox-esr chromium
        python3-pyqt6 python3-tk
        libfaketime v4l2loopback-dkms dkms
        nodejs npm
        ffmpeg proxychains4
        ca-certificates network-manager
        dbus-x11 xdg-utils desktop-file-utils
        unbound
    )
    for pkg in "${REQUIRED_PKGS[@]}"; do
        if grep -qP "^${pkg}\r?$" "$PL" 2>/dev/null || grep -q "^${pkg}[[:space:]]*$" "$PL" 2>/dev/null; then
            pass "pkg: $pkg"
        else
            fail "pkg: $pkg — NOT in package list"
        fi
    done
else
    fail "custom.list.chroot MISSING"
fi

# ── 14. AUTO/CONFIG ──────────────────────────────────────────────────────────
hdr "14/15 — LIVE-BUILD CONFIG (auto/config)"
AUTO_CFG="$ISO_DIR/auto/config"
if [ -f "$AUTO_CFG" ]; then
    pass "auto/config exists"
    if grep -q "username=user" "$AUTO_CFG"; then
        pass "username=user (matches services)"
    else
        fail "username MISMATCH — must be 'user' to match systemd/hooks"
    fi
    if grep -q "bookworm" "$AUTO_CFG"; then pass "distribution=bookworm"; else fail "distribution not bookworm"; fi
    if grep -q "grub-efi" "$AUTO_CFG"; then pass "bootloader=grub-efi"; else skip "bootloader not grub-efi"; fi
    if grep -q "persistence" "$AUTO_CFG"; then pass "persistence enabled"; else skip "no persistence"; fi
    if grep -q "amd64" "$AUTO_CFG"; then pass "architecture=amd64"; else fail "architecture not amd64"; fi
    if grep -q "linux-headers" "$AUTO_CFG"; then pass "linux-headers included"; else skip "no linux-headers"; fi
else
    fail "auto/config MISSING"
fi

# ── 15. FIRST-BOOT READINESS ────────────────────────────────────────────────
hdr "15/15 — FIRST-BOOT EXPERIENCE READINESS"

# Verify first-boot script checks all critical components
FB="$T/bin/titan-first-boot"
if [ -f "$FB" ]; then
    pass "titan-first-boot script exists"
    for fb_check in "Camoufox" "Playwright" "Python dependencies" "Ghost Motor" \
                    "core modules" "Intelligence" "GUI apps" "Phase 3" "titan.env" "eBPF" "Readiness"; do
        if grep -qi "$fb_check" "$FB" 2>/dev/null; then
            pass "first-boot checks: $fb_check"
        else
            skip "first-boot missing check: $fb_check"
        fi
    done
    # Verify marker file path
    if grep -q "first-boot-complete" "$FB" 2>/dev/null; then
        pass "first-boot completion marker configured"
    else
        fail "first-boot missing completion marker"
    fi
else
    fail "titan-first-boot MISSING — first boot will not run readiness checks"
fi

# Verify the service is ConditionPathExists gated
if [ -f "$SV/titan-first-boot.service" ] && grep -q "ConditionPathExists" "$SV/titan-first-boot.service"; then
    pass "first-boot service: one-shot gated by ConditionPathExists"
else
    [ -f "$SV/titan-first-boot.service" ] && skip "first-boot service: no ConditionPathExists gate"
fi

# ══════════════════════════════════════════════════════════════════════════════
hdr "VERIFICATION SUMMARY"
# ══════════════════════════════════════════════════════════════════════════════

echo ""
echo -e "  ${GREEN}${BOLD}PASSED:${NC}  ${PASS}"
echo -e "  ${RED}${BOLD}FAILED:${NC}  ${FAIL}"
echo -e "  ${YELLOW}${BOLD}WARNED:${NC}  ${WARN}"
echo -e "  ${BOLD}TOTAL:${NC}   ${TOTAL}"
echo ""

PCT=$((PASS * 100 / TOTAL))
echo -e "  ${BOLD}Score: ${PCT}%${NC} (${PASS}/${TOTAL})"
echo ""

if [ "$FAIL" -eq 0 ]; then
    echo -e "  ${GREEN}${BOLD}╔═══════════════════════════════════════════════╗${NC}"
    echo -e "  ${GREEN}${BOLD}║   ✓ ALL CHECKS PASSED — ISO IS COMPLETE      ║${NC}"
    echo -e "  ${GREEN}${BOLD}╚═══════════════════════════════════════════════╝${NC}"
    exit 0
elif [ "$FAIL" -le 3 ]; then
    echo -e "  ${YELLOW}${BOLD}╔═══════════════════════════════════════════════╗${NC}"
    echo -e "  ${YELLOW}${BOLD}║   ~ MINOR ISSUES — ISO MOSTLY COMPLETE       ║${NC}"
    echo -e "  ${YELLOW}${BOLD}╚═══════════════════════════════════════════════╝${NC}"
    exit 0
else
    echo -e "  ${RED}${BOLD}╔═══════════════════════════════════════════════╗${NC}"
    echo -e "  ${RED}${BOLD}║   ✗ CRITICAL FAILURES — ISO INCOMPLETE       ║${NC}"
    echo -e "  ${RED}${BOLD}╚═══════════════════════════════════════════════╝${NC}"
    exit 1
fi
