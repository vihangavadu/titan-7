#!/bin/bash
# TITAN V7.0 SINGULARITY — Pre-Build Verification Script
# Run from titan-main/ directory: bash scripts/verify_iso.sh

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0
WARN=0

pass() { echo -e "  ${GREEN}[PASS]${NC} $1"; ((PASS++)); }
fail() { echo -e "  ${RED}[FAIL]${NC} $1"; ((FAIL++)); }
warn() { echo -e "  ${YELLOW}[WARN]${NC} $1"; ((WARN++)); }

check_file() {
    if [ -f "$1" ]; then
        pass "$2"
    else
        fail "$2 — MISSING: $1"
    fi
}

check_dir() {
    if [ -d "$1" ]; then
        pass "$2"
    else
        fail "$2 — MISSING: $1"
    fi
}

ISO="iso/config"
CHROOT="$ISO/includes.chroot"
CORE="$CHROOT/opt/titan/core"
HOOKS="$ISO/hooks/live"

echo "╔══════════════════════════════════════════════════╗"
echo "║  TITAN V7.0 SINGULARITY — Pre-Build Verification ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# ═══ V1: ISO Configuration ═══
echo "═══ V1: ISO Configuration ═══"
check_file "$ISO/bootstrap" "bootstrap config"
check_file "$ISO/common" "common config"
check_file "$ISO/chroot" "chroot config"
check_file "$ISO/binary" "binary config"
check_file "iso/auto/config" "auto/config"

if [ -f "$ISO/bootstrap" ]; then
    if grep -q "deb.debian.org" "$ISO/bootstrap"; then
        pass "Debian mirrors (not Ubuntu)"
    else
        fail "Mirrors not set to deb.debian.org"
    fi
fi

if [ -f "$ISO/common" ]; then
    if grep -q 'LB_MODE="debian"' "$ISO/common"; then
        pass "LB_MODE=debian"
    else
        fail "LB_MODE not set to debian"
    fi
fi

# ═══ V2: Package List ═══
echo ""
echo "═══ V2: Package List ═══"
PKGLIST="$ISO/package-lists/custom.list.chroot"
check_file "$PKGLIST" "Package list exists"
if [ -f "$PKGLIST" ]; then
    for pkg in task-xfce-desktop rofi nftables apparmor firejail unbound dkms python3-pyqt6 libfaketime; do
        if grep -q "$pkg" "$PKGLIST"; then
            pass "Package: $pkg"
        else
            fail "Package missing: $pkg"
        fi
    done
fi

# ═══ V3: Build Hooks ═══
echo ""
echo "═══ V3: Build Hooks ═══"
for hook in 050-hardware-shield 060-kernel-module 070-camoufox-fetch 080-ollama-setup 090-kyc-setup 095-os-harden 99-fix-perms; do
    check_file "$HOOKS/$hook.hook.chroot" "Hook: $hook"
done

# ═══ V4: Core Modules ═══
echo ""
echo "═══ V4: Core Modules ═══"
check_dir "$CORE" "Core directory"
PY_COUNT=$(find "$CORE" -name "*.py" -type f 2>/dev/null | wc -l)
if [ "$PY_COUNT" -ge 29 ]; then
    pass "Python modules: $PY_COUNT (≥29)"
else
    fail "Python modules: $PY_COUNT (<29)"
fi

for mod in genesis_core cerberus_core cognitive_core ghost_motor_v6 fingerprint_injector audio_hardener font_sanitizer timezone_enforcer integration_bridge titan_env __init__; do
    check_file "$CORE/$mod.py" "Module: $mod"
done

# NetlinkHWBridge check
if [ -f "$CORE/fingerprint_injector.py" ]; then
    if grep -q "NetlinkHWBridge" "$CORE/fingerprint_injector.py"; then
        pass "NetlinkHWBridge in fingerprint_injector.py"
    else
        fail "NetlinkHWBridge MISSING from fingerprint_injector.py"
    fi
fi

# Audio jitter seed check
if [ -f "$CORE/audio_hardener.py" ]; then
    if grep -q "_derive_jitter_seed" "$CORE/audio_hardener.py"; then
        pass "Audio jitter seed in audio_hardener.py"
    else
        fail "Audio jitter seed MISSING from audio_hardener.py"
    fi
fi

# __init__.py NetlinkHWBridge export
if [ -f "$CORE/__init__.py" ]; then
    if grep -q "NetlinkHWBridge" "$CORE/__init__.py"; then
        pass "NetlinkHWBridge exported in __init__.py"
    else
        fail "NetlinkHWBridge NOT exported in __init__.py"
    fi
fi

# C files
for cfile in hardware_shield_v6.c network_shield_v6.c; do
    check_file "$CORE/$cfile" "C module: $cfile"
done

# ═══ V5: Legacy Bridge ═══
echo ""
echo "═══ V5: Legacy Bridge ═══"
LEGACY="$CHROOT/opt/lucid-empire"
check_dir "$LEGACY" "Legacy directory"
check_dir "$LEGACY/backend" "Legacy backend"
check_dir "$LEGACY/bin" "Legacy bin"

if [ -f "$CORE/integration_bridge.py" ]; then
    if grep -q "/opt/lucid-empire/" "$CORE/integration_bridge.py"; then
        pass "Legacy path in integration_bridge.py"
    else
        fail "Legacy path MISSING from integration_bridge.py"
    fi
fi

# ═══ V6: OS Hardening Configs ═══
echo ""
echo "═══ V6: OS Hardening Configs ═══"
check_file "$CHROOT/etc/sysctl.d/99-titan-hardening.conf" "Kernel sysctl hardening"
check_file "$CHROOT/etc/nftables.conf" "nftables firewall"
check_file "$CHROOT/etc/NetworkManager/conf.d/10-titan-privacy.conf" "MAC randomization"
check_file "$CHROOT/etc/fonts/local.conf" "Font fingerprint masking"
check_file "$CHROOT/etc/pulse/daemon.conf" "Audio stack masking"
check_file "$CHROOT/etc/sudoers.d/titan-ops" "Sudo rules"
check_file "$CHROOT/etc/polkit-1/localauthority/50-local.d/10-titan-nopasswd.pkla" "Polkit rules"
check_file "$CHROOT/etc/udev/rules.d/99-titan-usb.rules" "USB rules"
check_file "$CHROOT/etc/hosts" "Hosts file"

# nftables output policy check
if [ -f "$CHROOT/etc/nftables.conf" ]; then
    if grep -q "policy drop" "$CHROOT/etc/nftables.conf"; then
        pass "nftables: all chains policy drop"
    else
        fail "nftables: output chain NOT policy drop"
    fi
fi

# Font masking check
if [ -f "$CHROOT/etc/fonts/local.conf" ]; then
    if grep -q "DejaVu" "$CHROOT/etc/fonts/local.conf"; then
        pass "Font masking: DejaVu rejection rules"
    else
        fail "Font masking: DejaVu rules missing"
    fi
fi

# Audio check
if [ -f "$CHROOT/etc/pulse/daemon.conf" ]; then
    if grep -q "44100" "$CHROOT/etc/pulse/daemon.conf"; then
        pass "Audio: 44100Hz sample rate"
    else
        fail "Audio: NOT 44100Hz"
    fi
fi

# ═══ V7: Systemd Services ═══
echo ""
echo "═══ V7: Systemd Services ═══"
for svc in lucid-titan lucid-ebpf lucid-console titan-first-boot titan-dns; do
    check_file "$CHROOT/etc/systemd/system/$svc.service" "Service: $svc"
done
check_file "$CHROOT/etc/systemd/journald.conf.d/titan-privacy.conf" "Journald privacy"
check_file "$CHROOT/etc/systemd/coredump.conf.d/titan-no-coredump.conf" "Coredump disabled"

# ═══ V8: DNS Privacy ═══
echo ""
echo "═══ V8: DNS Privacy ═══"
check_file "$CHROOT/etc/unbound/unbound.conf.d/titan-dns.conf" "Unbound DNS-over-TLS"

# ═══ V9: Desktop Environment ═══
echo ""
echo "═══ V9: Desktop Environment ═══"
check_file "$CHROOT/etc/lightdm/lightdm.conf" "LightDM config"
check_file "$CHROOT/etc/lightdm/lightdm-gtk-greeter.conf" "LightDM greeter"
check_file "$CHROOT/etc/skel/.bashrc" "Shell environment"
check_file "$CHROOT/etc/issue" "Login banner"
check_file "$CHROOT/etc/default/grub.d/titan-branding.cfg" "GRUB branding"

for desk in titan-browser titan-configure titan-install titan-unified; do
    check_file "$CHROOT/usr/share/applications/$desk.desktop" "Desktop: $desk"
done

# ═══ V10: Firefox ESR Hardening ═══
echo ""
echo "═══ V10: Firefox ESR Hardening ═══"
check_file "$CHROOT/usr/lib/firefox-esr/defaults/pref/titan-hardening.js" "Firefox ESR prefs"
if [ -f "$CHROOT/usr/lib/firefox-esr/defaults/pref/titan-hardening.js" ]; then
    if grep -q "peerconnection.enabled" "$CHROOT/usr/lib/firefox-esr/defaults/pref/titan-hardening.js"; then
        pass "WebRTC disabled in Firefox ESR"
    else
        fail "WebRTC NOT disabled in Firefox ESR"
    fi
fi

# ═══ V11: Kernel Module ═══
echo ""
echo "═══ V11: Kernel Module ═══"
check_file "$CHROOT/usr/src/titan-hw-7.0.0/titan_hw.c" "Kernel module source"
check_file "$CHROOT/usr/src/titan-hw-7.0.0/Makefile" "Kernel module Makefile"
check_file "$CHROOT/usr/src/titan-hw-7.0.0/dkms.conf" "DKMS config"

# Python syntax check (if available)
echo ""
echo "═══ Syntax Check ═══"
if command -v python3 &> /dev/null; then
    SYNTAX_FAIL=0
    for pyfile in $(find "$CORE" -name "*.py" -type f 2>/dev/null); do
        if ! python3 -m py_compile "$pyfile" 2>/dev/null; then
            fail "Syntax error: $pyfile"
            ((SYNTAX_FAIL++))
        fi
    done
    if [ "$SYNTAX_FAIL" -eq 0 ]; then
        pass "All Python files pass syntax check"
    fi
else
    warn "Python3 not available — syntax check deferred to build environment"
fi

# ═══ FINAL VERDICT ═══
echo ""
echo "════════════════════════════════════════════════"
TOTAL=$((PASS + FAIL + WARN))
echo -e "  ${GREEN}PASS: $PASS${NC}  ${RED}FAIL: $FAIL${NC}  ${YELLOW}WARN: $WARN${NC}  TOTAL: $TOTAL"

if [ "$FAIL" -eq 0 ]; then
    echo -e "  ${GREEN}STATUS: READY FOR BUILD${NC}"
    echo "════════════════════════════════════════════════"
    exit 0
else
    echo -e "  ${RED}STATUS: $FAIL FAILURES — FIX BEFORE BUILD${NC}"
    echo "════════════════════════════════════════════════"
    exit 1
fi
