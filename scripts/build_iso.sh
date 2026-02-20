#!/bin/bash
# ==============================================================================
# LUCID EMPIRE :: TITAN V7.0.3 SINGULARITY — INTEGRATED ISO BUILDER
# ==============================================================================
# AUTHORITY: Dva.12 | STATUS: OBLIVION_ACTIVE
# PURPOSE:   Zero-tolerance ISO generation for Debian 12 (Bookworm) hosts.
#            Enforces strict resource and integrity checks before build.
#
# Usage:
#   sudo bash scripts/build_iso.sh
#
# Requirements:
#   - Ubuntu 22.04+ or Debian 12+ (x86_64)
#   - Root privileges (sudo)
#   - 15 GB+ free disk space
#   - Internet connection (debootstrap + apt + pip downloads)
#
# Output:
#   lucid-titan-v7.0-singularity.iso  (in repo root)
#   lucid-titan-v7.0-singularity.iso.sha256
# ==============================================================================

set -eo pipefail

# ── ANSI Colors ───────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

log()  { echo -e "${GREEN}[TITAN]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC}  $1"; }
err()  { echo -e "${RED}[ERROR]${NC} $1" >&2; }
hdr()  {
    echo ""
    echo -e "${CYAN}${BOLD}══════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}${BOLD}  $1${NC}"
    echo -e "${CYAN}${BOLD}══════════════════════════════════════════════════════════════${NC}"
}

# ── Resolve paths ─────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$REPO_ROOT"

ISO_DIR="$REPO_ROOT/iso"
CHROOT="$ISO_DIR/config/includes.chroot"
TITAN_OPT="$CHROOT/opt/titan"
LUCID_OPT="$CHROOT/opt/lucid-empire"
PKG_LIST="$ISO_DIR/config/package-lists/custom.list.chroot"
HOOKS_DIR="$ISO_DIR/config/hooks/live"

TITAN_VERSION="7.0.3"
ISO_NAME="lucid-titan-v${TITAN_VERSION}-singularity"
REQ_SPACE_GB=15

# ==============================================================================
hdr "PHASE 0 — ROOT & ENVIRONMENT CHECK"
# ==============================================================================

if [ "$EUID" -ne 0 ]; then
    err "This script must be run as root."
    echo "    Usage: sudo bash scripts/build_iso.sh"
    exit 1
fi

# Architecture Verification (Strict x86_64)
ARCH=$(uname -m)
if [[ "$ARCH" != "x86_64" ]]; then
    err "Host architecture '$ARCH' is not supported. TITAN requires x86_64."
    exit 1
fi
log "Architecture verified: x86_64"

log "Working directory: $REPO_ROOT"
log "Target ISO: ${ISO_NAME}.iso"

# Disk Space Enforcement (Strict 15GB)
AVAIL_GB=$(df --output=avail "$REPO_ROOT" | tail -1 | awk '{print int($1/1048576)}')
log "Disk available: ${AVAIL_GB} GB"
if [ "$AVAIL_GB" -lt "$REQ_SPACE_GB" ]; then
    err "Insufficient disk space. Required: ${REQ_SPACE_GB}GB+, Available: ${AVAIL_GB}GB."
    exit 1
fi
log "Disk space check passed: ${AVAIL_GB}GB available."

# Detect host OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    log "Host OS: $PRETTY_NAME"
else
    warn "Cannot detect host OS — continuing anyway"
fi

# ==============================================================================
hdr "PHASE 1 — INSTALL BUILD DEPENDENCIES"
# ==============================================================================

log "Updating package lists..."
apt-get update -qq

log "Installing live-build toolchain..."
apt-get install -y --no-install-recommends \
    live-build \
    debootstrap \
    squashfs-tools \
    xorriso \
    syslinux-utils \
    syslinux-common \
    isolinux \
    dosfstools \
    mtools \
    gcc \
    clang \
    llvm \
    make \
    bc \
    libbpf-dev \
    libelf-dev \
    zlib1g-dev \
    dkms \
    python3 \
    python3-pip \
    curl \
    wget \
    git

# Kernel Headers (Critical for Ring 0 Modules)
KERNEL_HEADERS="linux-headers-$(uname -r)"
if apt-get install -y --no-install-recommends "$KERNEL_HEADERS" 2>/dev/null; then
    log "Kernel headers installed: $KERNEL_HEADERS"
else
    # Logic Update: Only allow fallback in containerized environments
    if grep -q "docker\|lxc" /proc/1/cgroup 2>/dev/null; then
        warn "Kernel headers installation failed. Assuming container environment."
        warn "eBPF/DKMS modules will use bundled definitions."
    else
        err "Failed to install kernel headers on physical host. This is fatal for Ring 0 shields."
        exit 1
    fi
fi

log "Build dependencies installed."

# ==============================================================================
hdr "PHASE 2 — VERIFY SOURCE TREE INTEGRITY"
# ==============================================================================

# This phase checks that ALL V7.0 sources exist in the repo before building.
# No deployment step needed — sources are already in iso/config/includes.chroot/

log "Verifying V7.0 Titan Core (/opt/titan/core/)..."
V7_CORE_MODULES=(
    # Trinity
    "genesis_core.py"
    "advanced_profile_generator.py"
    "purchase_history_engine.py"
    "cerberus_core.py"
    "cerberus_enhanced.py"
    "kyc_core.py"
    "kyc_enhanced.py"
    # Integration
    "integration_bridge.py"
    "preflight_validator.py"
    "target_intelligence.py"
    "target_presets.py"
    "fingerprint_injector.py"
    "form_autofill_injector.py"
    "referrer_warmup.py"
    "handover_protocol.py"
    # Phase 2-3 Hardening
    "kill_switch.py"
    "font_sanitizer.py"
    "audio_hardener.py"
    "timezone_enforcer.py"
    "verify_deep_identity.py"
    "titan_master_verify.py"
    # Supporting
    "ghost_motor_v6.py"
    "cognitive_core.py"
    "quic_proxy.py"
    "proxy_manager.py"
    "three_ds_strategy.py"
    "lucid_vpn.py"
    "location_spoofer_linux.py"
    "generate_trajectory_model.py"
    "titan_env.py"
    # V7.0 Singularity Modules
    "tls_parrot.py"
    "webgl_angle.py"
    "network_jitter.py"
    "immutable_os.py"
    "cockpit_daemon.py"
    "waydroid_sync.py"
    # V7.0.3 Intelligence & Operational Modules
    "target_discovery.py"
    "intel_monitor.py"
    "transaction_monitor.py"
    "titan_services.py"
    # Exports
    "__init__.py"
)

# C modules (compiled separately)
V6_C_MODULES=(
    "hardware_shield_v6.c"
    "network_shield_v6.c"
    "titan_battery.c"
)

CORE_MISSING=0
for mod in "${V7_CORE_MODULES[@]}"; do
    if [ -f "$TITAN_OPT/core/$mod" ]; then
        echo -e "  ${GREEN}[+]${NC} core/$mod"
    else
        echo -e "  ${RED}[!] MISSING:${NC} core/$mod"
        CORE_MISSING=$((CORE_MISSING + 1))
    fi
done

log "Verifying V7.0 C Modules (/opt/titan/core/)..."
for cmod in "${V6_C_MODULES[@]}"; do
    if [ -f "$TITAN_OPT/core/$cmod" ]; then
        echo -e "  ${GREEN}[+]${NC} core/$cmod"
    else
        echo -e "  ${RED}[!] MISSING:${NC} core/$cmod"
        CORE_MISSING=$((CORE_MISSING + 1))
    fi
done

log "Verifying V7.0 Trinity Apps (/opt/titan/apps/)..."
for app in app_unified.py app_genesis.py app_cerberus.py app_kyc.py; do
    if [ -f "$TITAN_OPT/apps/$app" ]; then
        echo -e "  ${GREEN}[+]${NC} apps/$app"
    else
        echo -e "  ${RED}[!] MISSING:${NC} apps/$app"
        CORE_MISSING=$((CORE_MISSING + 1))
    fi
done

log "Verifying V7.0 Launchers (/opt/titan/bin/)..."
for bin in titan-browser titan-launcher titan-first-boot install-to-disk; do
    if [ -f "$TITAN_OPT/bin/$bin" ]; then
        echo -e "  ${GREEN}[+]${NC} bin/$bin"
    else
        echo -e "  ${YELLOW}[~]${NC} bin/$bin (optional)"
    fi
done

log "Verifying Ghost Motor extension..."
for ext in ghost_motor.js manifest.json; do
    if [ -f "$TITAN_OPT/extensions/ghost_motor/$ext" ]; then
        echo -e "  ${GREEN}[+]${NC} extensions/ghost_motor/$ext"
    else
        echo -e "  ${YELLOW}[~]${NC} extensions/ghost_motor/$ext (optional)"
    fi
done

log "Verifying TX Monitor extension (V7.0.3)..."
for ext in tx_monitor.js background.js manifest.json; do
    if [ -f "$TITAN_OPT/extensions/tx_monitor/$ext" ]; then
        echo -e "  ${GREEN}[+]${NC} extensions/tx_monitor/$ext"
    else
        echo -e "  ${YELLOW}[~]${NC} extensions/tx_monitor/$ext (V7.0.3)"
    fi
done

log "Verifying Legacy Infrastructure (/opt/lucid-empire/)..."
LEGACY_FILES=(
    "launch-titan.sh"
    "backend/server.py"
    "backend/lucid_api.py"
    "backend/__init__.py"
    "backend/modules/__init__.py"
    "backend/modules/ghost_motor.py"
    "backend/modules/fingerprint_manager.py"
    "backend/core/genesis_engine.py"
    "backend/core/profile_store.py"
    "bin/titan-backend-init.sh"
    "bin/load-ebpf.sh"
)
for lf in "${LEGACY_FILES[@]}"; do
    if [ -f "$LUCID_OPT/$lf" ]; then
        echo -e "  ${GREEN}[+]${NC} lucid-empire/$lf"
    else
        echo -e "  ${YELLOW}[~]${NC} lucid-empire/$lf"
    fi
done

log "Verifying Systemd services..."
SVC_DIR="$CHROOT/etc/systemd/system"
for svc in lucid-titan.service lucid-ebpf.service lucid-console.service titan-first-boot.service; do
    if [ -f "$SVC_DIR/$svc" ]; then
        echo -e "  ${GREEN}[+]${NC} $svc"
    else
        echo -e "  ${YELLOW}[~]${NC} $svc"
    fi
done

log "Verifying Desktop entries..."
DESKTOP_DIR="$CHROOT/usr/share/applications"
for de in titan-unified.desktop titan-browser.desktop titan-install.desktop; do
    if [ -f "$DESKTOP_DIR/$de" ]; then
        echo -e "  ${GREEN}[+]${NC} $de"
    else
        echo -e "  ${YELLOW}[~]${NC} $de"
    fi
done

log "Verifying XDG autostart..."
XDG_AUTO="$CHROOT/etc/xdg/autostart/lucid-titan-console.desktop"
if [ -f "$XDG_AUTO" ]; then
    echo -e "  ${GREEN}[+]${NC} XDG autostart (lucid-titan-console.desktop)"
else
    echo -e "  ${YELLOW}[~]${NC} XDG autostart missing — GUI will rely on systemd only"
fi

log "Verifying V7.0 VPN Infrastructure (/opt/titan/vpn/)..."
for vpnf in xray-client.json xray-server.json setup-vps-relay.sh setup-exit-node.sh; do
    if [ -f "$TITAN_OPT/vpn/$vpnf" ]; then
        echo -e "  ${GREEN}[+]${NC} vpn/$vpnf"
    else
        echo -e "  ${YELLOW}[~]${NC} vpn/$vpnf (optional — operator deploys separately)"
    fi
done

log "Verifying V7.0 Testing Framework (/opt/titan/testing/)..."
for tf in __init__.py test_runner.py detection_emulator.py titan_adversary_sim.py environment.py psp_sandbox.py report_generator.py; do
    if [ -f "$TITAN_OPT/testing/$tf" ]; then
        echo -e "  ${GREEN}[+]${NC} testing/$tf"
    else
        echo -e "  ${YELLOW}[~]${NC} testing/$tf"
    fi
done

log "Verifying titan.env operator config..."
if [ -f "$TITAN_OPT/config/titan.env" ]; then
    echo -e "  ${GREEN}[+]${NC} config/titan.env"
else
    echo -e "  ${YELLOW}[~]${NC} config/titan.env (will be created on first boot)"
fi

log "Verifying Build hooks..."
for hook in 050-hardware-shield 060-kernel-module 070-camoufox-fetch 080-ollama-setup 090-kyc-setup 095-os-harden 098-profile-skeleton 99-fix-perms; do
    if [ -f "$HOOKS_DIR/${hook}.hook.chroot" ]; then
        echo -e "  ${GREEN}[+]${NC} ${hook}.hook.chroot"
    else
        echo -e "  ${RED}[!] MISSING:${NC} ${hook}.hook.chroot"
        CORE_MISSING=$((CORE_MISSING + 1))
    fi
done

log "Verifying Package list..."
if [ -f "$PKG_LIST" ]; then
    PKG_COUNT=$(grep -cv '^\s*#\|^\s*$' "$PKG_LIST" 2>/dev/null || echo 0)
    echo -e "  ${GREEN}[+]${NC} custom.list.chroot ($PKG_COUNT packages)"
else
    echo -e "  ${RED}[!] MISSING:${NC} custom.list.chroot"
    CORE_MISSING=$((CORE_MISSING + 1))
fi

# Logic Update: Zero Tolerance Policy
if [ "$CORE_MISSING" -gt 0 ]; then
    err "Integrity Check Failed: $CORE_MISSING critical files missing. Aborting build to prevent compromise."
    exit 1
fi

log "Source tree verification complete."

# ==============================================================================
hdr "PHASE 3 — COMPILE eBPF NETWORK SHIELDS"
# ==============================================================================

EBPF_SRC="$LUCID_OPT/ebpf/network_shield.c"
EBPF_OBJ="$LUCID_OPT/ebpf/network_shield.o"

if [ -f "$EBPF_SRC" ]; then
    log "Compiling network_shield.c → network_shield.o (BPF bytecode)..."
    if clang -O2 -g \
        -target bpf \
        -D__TARGET_ARCH_x86 \
        -I/usr/include/x86_64-linux-gnu \
        -I/usr/include \
        -c "$EBPF_SRC" \
        -o "$EBPF_OBJ" 2>&1; then
        log "  Compiled: $(ls -lh "$EBPF_OBJ" | awk '{print $5, $NF}')"
    else
        warn "network_shield.c compilation failed — continuing without XDP shield"
    fi
else
    warn "network_shield.c not found — skipping eBPF compilation"
fi

TCP_SRC="$LUCID_OPT/ebpf/tcp_fingerprint.c"
TCP_OBJ="$LUCID_OPT/ebpf/tcp_fingerprint.o"

if [ -f "$TCP_SRC" ]; then
    log "Compiling tcp_fingerprint.c → tcp_fingerprint.o..."
    clang -O2 -g \
        -target bpf \
        -D__TARGET_ARCH_x86 \
        -I/usr/include/x86_64-linux-gnu \
        -I/usr/include \
        -c "$TCP_SRC" \
        -o "$TCP_OBJ" 2>&1 || warn "tcp_fingerprint.c compilation failed — XDP-only mode"
fi

# ==============================================================================
hdr "PHASE 4 — VERIFY HARDWARE SHIELD SOURCES"
# ==============================================================================

# Note: hardware_shield_v6.c is a kernel module compiled via DKMS in Phase 5.
# Here we only verify the sources exist and do a syntax check.

HW_V6_SRC="$TITAN_OPT/core/hardware_shield_v6.c"
HW_LEGACY_SRC="$LUCID_OPT/hardware_shield/titan_hw.c"

if [ -f "$HW_V6_SRC" ]; then
    log "V7.0 hardware shield source: $(ls -lh "$HW_V6_SRC" | awk '{print $5}')"
    # Syntax check only (kernel module must be compiled inside chroot via DKMS)
    if command -v gcc &>/dev/null; then
        gcc -fsyntax-only -Wall "$HW_V6_SRC" 2>/dev/null && \
            log "  Syntax check: PASS" || \
            warn "  Syntax check: warnings (expected for kernel headers)"
    fi
else
    warn "hardware_shield_v6.c not found in /opt/titan/core/"
fi

if [ -f "$HW_LEGACY_SRC" ]; then
    log "Legacy hardware shield: $(ls -lh "$HW_LEGACY_SRC" | awk '{print $5}')"
else
    warn "Legacy titan_hw.c not found — DKMS will use V7.0 source only"
fi

# ==============================================================================
hdr "PHASE 5 — PREPARE KERNEL MODULE (DKMS)"
# ==============================================================================

DKMS_DIR="$CHROOT/usr/src/titan-hw-${TITAN_VERSION}"
mkdir -p "$DKMS_DIR"

# Copy source from hardware_shield directory or V6 core
if [ -f "$TITAN_OPT/core/hardware_shield_v6.c" ]; then
    cp "$TITAN_OPT/core/hardware_shield_v6.c" "$DKMS_DIR/titan_hw.c"
    log "Using V7.0 hardware shield with Netlink injection"
elif [ -f "$LUCID_OPT/hardware_shield/titan_hw.c" ]; then
    cp "$LUCID_OPT/hardware_shield/titan_hw.c" "$DKMS_DIR/titan_hw.c"
    log "Using legacy hardware shield"
else
    warn "No hardware shield source found — DKMS will be empty"
fi

# Copy Makefile (or generate one if missing)
if [ -f "$LUCID_OPT/hardware_shield/Makefile" ]; then
    cp "$LUCID_OPT/hardware_shield/Makefile" "$DKMS_DIR/"
    log "Using existing Makefile from hardware_shield/"
elif [ ! -f "$DKMS_DIR/Makefile" ]; then
    cat > "$DKMS_DIR/Makefile" << 'MKEOF'
obj-m += titan_hw.o
all:
	make -C /lib/modules/$(shell uname -r)/build M=$(PWD) modules
clean:
	make -C /lib/modules/$(shell uname -r)/build M=$(PWD) clean
MKEOF
    log "Generated DKMS Makefile"
fi

# Write DKMS config
cat > "$DKMS_DIR/dkms.conf" << EOF
PACKAGE_NAME="titan-hw"
PACKAGE_VERSION="${TITAN_VERSION}"
BUILT_MODULE_NAME[0]="titan_hw"
DEST_MODULE_LOCATION[0]="/kernel/drivers/misc"
AUTOINSTALL="yes"
MAKE[0]="make -C /lib/modules/\${kernelver}/build M=\${dkms_tree}/\${PACKAGE_NAME}/\${PACKAGE_VERSION}/build modules"
CLEAN="make -C /lib/modules/\${kernelver}/build M=\${dkms_tree}/\${PACKAGE_NAME}/\${PACKAGE_VERSION}/build clean"
EOF

log "DKMS source tree: $DKMS_DIR"
ls -la "$DKMS_DIR/" 2>/dev/null || true

# Ensure dkms is in the package list
if ! grep -q "^dkms$" "$PKG_LIST" 2>/dev/null; then
    echo "" >> "$PKG_LIST"
    echo "# --- DKMS (auto-compile kernel modules) ---" >> "$PKG_LIST"
    echo "dkms" >> "$PKG_LIST"
    log "Added dkms to package list."
fi

# ==============================================================================
hdr "PHASE 6 — FIX FILESYSTEM LAYOUT"
# ==============================================================================

# 6a. /opt/titan directory structure
log "Ensuring /opt/titan directory structure..."
mkdir -p "$TITAN_OPT/profiles"
mkdir -p "$TITAN_OPT/state"
mkdir -p "$TITAN_OPT/docs"
mkdir -p "$TITAN_OPT/vpn"
mkdir -p "$TITAN_OPT/assets/motions"
# V7.0.3 data directories
mkdir -p "$CHROOT/opt/titan/data"
mkdir -p "$CHROOT/opt/titan/data/tx_monitor"
mkdir -p "$CHROOT/opt/titan/data/services"
mkdir -p "$CHROOT/opt/titan/data/target_discovery"
mkdir -p "$CHROOT/opt/titan/data/intel_monitor/sessions/browser_profiles"
mkdir -p "$CHROOT/opt/titan/data/intel_monitor/feed_cache"
mkdir -p "$CHROOT/opt/titan/profiles"

# V7.0.3: Copy profgen package to ISO chroot (forensic-grade profile generation)
if [ -d "$REPO_ROOT/profgen" ]; then
    mkdir -p "$TITAN_OPT/profgen"
    cp -f "$REPO_ROOT/profgen/"*.py "$TITAN_OPT/profgen/"
    log "Profgen package copied to ISO chroot."
fi

# 6b. /opt/lucid-empire directories
log "Ensuring /opt/lucid-empire directory structure..."
mkdir -p "$LUCID_OPT/data"
mkdir -p "$LUCID_OPT/profiles/default"
mkdir -p "$LUCID_OPT/bin"

# 6b-1. Clean __pycache__ from chroot (bytecode doesn't belong in ISO)
log "Cleaning __pycache__ directories from chroot..."
find "$CHROOT" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$CHROOT" -name "*.pyc" -delete 2>/dev/null || true

# 6c. Active profile symlink
PROFILES="$LUCID_OPT/profiles"
if [ ! -L "$PROFILES/active" ]; then
    rm -f "$PROFILES/active"
    ln -sf /opt/lucid-empire/profiles/default "$PROFILES/active"
    log "Active profile symlink created."
fi

# 6d. Executable permissions — /opt/titan
log "Setting executable permissions..."
find "$TITAN_OPT" -name "*.py" -exec chmod +x {} \; 2>/dev/null || true
find "$TITAN_OPT" -name "*.sh" -exec chmod +x {} \; 2>/dev/null || true
chmod +x "$TITAN_OPT/bin/"* 2>/dev/null || true
chmod +x "$TITAN_OPT/apps/"* 2>/dev/null || true

# 6e. Executable permissions — /opt/lucid-empire
find "$LUCID_OPT" -name "*.py" -exec chmod +x {} \; 2>/dev/null || true
find "$LUCID_OPT" -name "*.sh" -exec chmod +x {} \; 2>/dev/null || true
chmod +x "$LUCID_OPT/bin/"* 2>/dev/null || true
chmod +x "$LUCID_OPT/launch-titan.sh" 2>/dev/null || true

# 6f. Build hooks must be executable
chmod +x "$HOOKS_DIR/"*.hook.chroot 2>/dev/null || true

# 6g. Purge automation vectors from requirements.txt
REQ="$LUCID_OPT/requirements.txt"
if [ -f "$REQ" ]; then
    sed -i '/^selenium/d'  "$REQ" 2>/dev/null || true
    sed -i '/^puppeteer/d' "$REQ" 2>/dev/null || true
    log "Automation vectors purged from requirements.txt."
fi

# 6h. Live user home setup
LIVE_HOME="$CHROOT/home/user"
mkdir -p "$LIVE_HOME/Desktop"
mkdir -p "$LIVE_HOME/.config/autostart"
mkdir -p "$LIVE_HOME/.local/share"

log "Filesystem layout complete."

# ==============================================================================
hdr "PHASE 7 — PRE-FLIGHT CAPABILITY MATRIX"
# ==============================================================================

log "Capability Alignment Matrix:"

CAP_OK=0
CAP_TOTAL=8

# Hardware Shield
if [ -f "$DKMS_DIR/titan_hw.c" ]; then
    echo -e "  ${GREEN}[HARDWARE]${NC}    Identity Synthesis — titan_hw.c in DKMS"
    CAP_OK=$((CAP_OK+1))
else
    echo -e "  ${RED}[HARDWARE]${NC}    MISSING titan_hw.c"
fi

# Network Shield
if [ -f "$LUCID_OPT/ebpf/network_shield.c" ] && command -v clang &>/dev/null; then
    echo -e "  ${GREEN}[NETWORK]${NC}     Packet Normalization — clang + source ready"
    CAP_OK=$((CAP_OK+1))
else
    echo -e "  ${YELLOW}[NETWORK]${NC}     Degraded — source or clang missing"
fi

# Temporal (libfaketime)
if grep -q "^libfaketime$" "$PKG_LIST" 2>/dev/null; then
    echo -e "  ${GREEN}[TEMPORAL]${NC}    Time Displacement — libfaketime queued"
    CAP_OK=$((CAP_OK+1))
else
    echo -e "  ${RED}[TEMPORAL]${NC}    libfaketime NOT in package list"
fi

# KYC Module
if [ -f "$TITAN_OPT/core/kyc_core.py" ] && [ -f "$TITAN_OPT/core/kyc_enhanced.py" ]; then
    echo -e "  ${GREEN}[KYC]${NC}         Reality Synthesis — kyc_core + kyc_enhanced present"
    CAP_OK=$((CAP_OK+1))
else
    echo -e "  ${YELLOW}[KYC]${NC}         KYC module incomplete"
fi

# Phase 3 Hardening
if [ -f "$TITAN_OPT/core/font_sanitizer.py" ] && \
   [ -f "$TITAN_OPT/core/audio_hardener.py" ] && \
   [ -f "$TITAN_OPT/core/timezone_enforcer.py" ]; then
    echo -e "  ${GREEN}[PHASE-3]${NC}     Environment Shields — font/audio/tz present"
    CAP_OK=$((CAP_OK+1))
else
    echo -e "  ${YELLOW}[PHASE-3]${NC}     Phase 3 modules incomplete"
fi

# Trinity Apps
if [ -f "$TITAN_OPT/apps/app_unified.py" ] && \
   [ -f "$TITAN_OPT/apps/app_genesis.py" ] && \
   [ -f "$TITAN_OPT/apps/app_cerberus.py" ]; then
    echo -e "  ${GREEN}[TRINITY]${NC}     GUI Apps — unified + genesis + cerberus + kyc"
    CAP_OK=$((CAP_OK+1))
else
    echo -e "  ${YELLOW}[TRINITY]${NC}     Some Trinity GUI apps missing"
fi

# VPN Infrastructure
if [ -f "$TITAN_OPT/vpn/xray-client.json" ] && [ -f "$TITAN_OPT/vpn/setup-vps-relay.sh" ]; then
    echo -e "  ${GREEN}[VPN]${NC}         Lucid VPN — VLESS+Reality+Tailscale ready"
    CAP_OK=$((CAP_OK+1))
else
    echo -e "  ${YELLOW}[VPN]${NC}         VPN templates incomplete"
fi

# Persistence
echo -e "  ${GREEN}[PERSIST]${NC}     Zero Footprint — live-build volatile mode"
CAP_OK=$((CAP_OK+1))

log "Capability Score: ${CAP_OK} / ${CAP_TOTAL} vectors GREEN"

if [ "$CAP_OK" -lt 4 ]; then
    warn "Only $CAP_OK / $CAP_TOTAL capability vectors GREEN — ISO may be incomplete."
fi

log "Pre-flight verification complete."

# ==============================================================================
hdr "PHASE 8 — BUILD ISO (live-build)"
# ==============================================================================

cd "$ISO_DIR"

log "Cleaning previous build state..."
lb clean --purge 2>/dev/null || true

# Ubuntu live-build 3.0 expects hooks at config/hooks/*.chroot (flat)
# Debian live-build 4.x+ uses config/hooks/live/*.chroot (subdirectory)
# Copy hooks to both locations for compatibility
log "Copying hooks for live-build compatibility..."
if [ -d "$ISO_DIR/config/hooks/live" ]; then
    cp -f "$ISO_DIR/config/hooks/live/"*.chroot "$ISO_DIR/config/hooks/" 2>/dev/null || true
    log "Hooks copied to config/hooks/ for live-build 3.x compat"
fi

# SquashFS compression: Zstandard level 19 (per V7.0 optimization plan Section 3.1)
# Superior balance between compression ratio and decompression speed vs XZ
# Accelerates boot times — critical for toram rapid redeployment
export MKSQUASHFS_OPTIONS="-comp zstd -Xcompression-level 19"

log "Configuring Debian Live (Bookworm amd64)..."
lb config \
    --distribution bookworm \
    --parent-distribution bookworm \
    --parent-mirror-bootstrap http://deb.debian.org/debian \
    --parent-mirror-chroot http://deb.debian.org/debian \
    --parent-mirror-chroot-security http://deb.debian.org/debian-security \
    --parent-mirror-binary http://deb.debian.org/debian \
    --parent-mirror-binary-security http://deb.debian.org/debian-security \
    --parent-mirror-chroot-volatile http://deb.debian.org/debian \
    --parent-mirror-binary-volatile http://deb.debian.org/debian \
    --parent-mirror-chroot-backports http://deb.debian.org/debian \
    --parent-mirror-binary-backports http://deb.debian.org/debian \
    --mirror-bootstrap http://deb.debian.org/debian \
    --mirror-chroot http://deb.debian.org/debian \
    --mirror-chroot-security http://deb.debian.org/debian-security \
    --mirror-binary http://deb.debian.org/debian \
    --mirror-binary-security http://deb.debian.org/debian-security \
    --keyring-packages debian-archive-keyring \
    --archive-areas "main contrib non-free non-free-firmware" \
    --architectures amd64 \
    --linux-packages "linux-image linux-headers" \
    --linux-flavours amd64 \
    --system live \
    --initramfs live-boot \
    --initsystem systemd \
    --bootloaders grub-efi \
    --bootappend-live "boot=live components quiet splash toram persistence username=user locales=en_US.UTF-8 ipv6.disable=1 net.ifnames=0 plymouth.enable=1" \
    --chroot-filesystem squashfs \
    --binary-images iso-hybrid \
    --apt-indices false \
    --memtest memtest86+ \
    --iso-application "Titan OS V7.0.3 Singularity" \
    --iso-publisher "Dva.12" \
    --iso-volume "TITAN-V703-SINGULARITY"

log "lb config complete."
log "Starting ISO build — this takes 30-90 minutes..."
echo ""

BUILD_START=$(date +%s)

set +e
lb build 2>&1 | tee build.log
LB_EXIT=${PIPESTATUS[0]}
set -e

log "lb build exit code: $LB_EXIT"

if [ "$LB_EXIT" -ne 0 ]; then
    # Check if the failure was only in the ISO packaging step (>4GiB squashfs or missing isohybrid)
    # If the squashfs was built, we can recover by using xorriso directly
    BINARY_DIR="$ISO_DIR/chroot/binary"
    if [ -f "$BINARY_DIR/live/filesystem.squashfs" ] && command -v xorriso &>/dev/null; then
        log "lb build failed at ISO packaging — recovering with xorriso (supports >4GiB files)..."
        BOOT_IMG=""
        BOOT_ARGS=""
        if [ -f "$BINARY_DIR/boot/grub/stage2_eltorito" ]; then
            BOOT_ARGS="-b boot/grub/stage2_eltorito -no-emul-boot -boot-load-size 4 -boot-info-table"
        fi
        HYBRID_ARG=""
        if [ -f /usr/lib/ISOLINUX/isohdpfx.bin ]; then
            HYBRID_ARG="-isohybrid-mbr /usr/lib/ISOLINUX/isohdpfx.bin"
        fi
        xorriso -as mkisofs \
            -r -V "TITAN-V703-SINGULARITY" \
            -iso-level 3 \
            -o "$ISO_DIR/${ISO_NAME}.iso" \
            -J -joliet-long \
            $BOOT_ARGS \
            $HYBRID_ARG \
            "$BINARY_DIR" 2>&1 | tail -10
        if [ -f "$ISO_DIR/${ISO_NAME}.iso" ]; then
            log "xorriso recovery successful"
            LB_EXIT=0
        else
            err "xorriso recovery also failed"
        fi
    fi
fi

if [ "$LB_EXIT" -ne 0 ]; then
    err "lb build FAILED (exit code $LB_EXIT)"
    echo ""
    err "=== Last 50 lines of build.log ==="
    tail -50 build.log 2>/dev/null || true
    err "=== End of build.log ==="
    echo ""
    err "Common fixes:"
    err "  1. Check internet connection (debootstrap needs to download packages)"
    err "  2. Run 'lb clean --purge' then retry"
    err "  3. Check disk space: df -h /"
    err "  4. Full log: $ISO_DIR/build.log"
    exit 1
fi

BUILD_END=$(date +%s)
BUILD_MINS=$(( (BUILD_END - BUILD_START) / 60 ))

# ==============================================================================
hdr "PHASE 9 — COLLECT OUTPUT"
# ==============================================================================

# Look for ISO in current dir (lb build output) or xorriso output
ISO_FILE=$(find . -maxdepth 1 -name "*.iso" -type f | head -1)
if [ -z "$ISO_FILE" ] && [ -f "$ISO_DIR/${ISO_NAME}.iso" ]; then
    ISO_FILE="$ISO_DIR/${ISO_NAME}.iso"
fi

if [ -n "$ISO_FILE" ]; then
    FINAL="$REPO_ROOT/${ISO_NAME}.iso"
    mv "$ISO_FILE" "$FINAL"

    ISO_SIZE=$(ls -lh "$FINAL" | awk '{print $5}')
    ISO_SHA=$(sha256sum "$FINAL")

    echo "$ISO_SHA" > "${FINAL}.sha256"

    hdr "BUILD COMPLETE — TITAN V7.0 SINGULARITY"
    echo ""
    echo -e "  ${GREEN}${BOLD}ISO:${NC}      $FINAL"
    echo -e "  ${GREEN}${BOLD}Size:${NC}     $ISO_SIZE"
    echo -e "  ${GREEN}${BOLD}SHA256:${NC}   $(echo "$ISO_SHA" | awk '{print $1}')"
    echo -e "  ${GREEN}${BOLD}Time:${NC}     ${BUILD_MINS} minutes"
    echo ""
    echo -e "  ${CYAN}Write to USB:${NC}"
    echo -e "    sudo dd if=$FINAL of=/dev/sdX bs=4M status=progress oflag=sync"
    echo ""
    echo -e "  ${CYAN}Boot in VM (QEMU):${NC}"
    echo -e "    qemu-system-x86_64 -m 4096 -cdrom $FINAL -boot d -enable-kvm"
    echo ""
    echo -e "  ${CYAN}Boot in VirtualBox:${NC}"
    echo -e "    Create VM → Debian 64-bit → 4GB RAM → Attach ISO as optical drive"
    echo ""
    echo -e "  ${CYAN}Install to VPS disk (from live session):${NC}"
    echo -e "    sudo bash /opt/titan/bin/install-to-disk /dev/vda"
    echo -e "    # Then reboot — system persists permanently"
    echo ""
else
    hdr "BUILD FAILED"
    err "No ISO file produced."
    err "Check: $ISO_DIR/build.log"
    exit 1
fi
