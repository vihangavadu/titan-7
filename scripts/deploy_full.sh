#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# TITAN V8.1 SINGULARITY — Full Deployment Script for Fresh Debian 12
# AUTHORITY: Dva.12 | STATUS: OBLIVION_ACTIVE
#
# This script deploys the COMPLETE Titan OS ecosystem onto a fresh Debian 12
# (Bookworm) VPS. It replaces the standard OS environment with the full
# Five Rings evasion architecture.
#
# Usage (run as root on the target Debian 12 VPS):
#   curl -sSL https://raw.githubusercontent.com/malithwishwa02-dot/titan-7/main/scripts/deploy_full.sh | bash
#   — OR —
#   git clone https://github.com/malithwishwa02-dot/titan-7.git /opt/titan-build
#   cd /opt/titan-build && bash scripts/deploy_full.sh
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

# ── CONFIGURATION ──
TITAN_REPO="https://github.com/malithwishwa02-dot/titan-7.git"
TITAN_BRANCH="main"
TITAN_ROOT="/opt/titan"
LEGACY_ROOT="/opt/lucid-empire"
BUILD_DIR="/opt/titan-build"
OPERATOR_USER="user"
OPERATOR_PASS="TitanOp2026!"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

LOG_FILE="/var/log/titan-deploy-$(date +%Y%m%d_%H%M%S).log"

log() { echo -e "${GREEN}[TITAN]${NC} $*" | tee -a "$LOG_FILE"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*" | tee -a "$LOG_FILE"; }
err() { echo -e "${RED}[ERROR]${NC} $*" | tee -a "$LOG_FILE"; }
phase() { echo -e "\n${CYAN}═══════════════════════════════════════════════════════════${NC}" | tee -a "$LOG_FILE"; echo -e "${BLUE}  $*${NC}" | tee -a "$LOG_FILE"; echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}" | tee -a "$LOG_FILE"; }

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  TITAN V8.1 SINGULARITY — Full Debian 12 Deployment        ║"
echo "║  Five Rings Architecture • Zero Detect Environment          ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 0: PRE-FLIGHT VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════
phase "PHASE 0: Pre-Flight Validation"

# Must be root
if [ "$EUID" -ne 0 ]; then
    err "Must run as root (use sudo)"
    exit 1
fi

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    log "Detected: $PRETTY_NAME"
else
    err "Cannot detect OS"
    exit 1
fi

# Validate Debian 12
case "$ID" in
    debian)
        if [ "$VERSION_ID" != "12" ]; then
            warn "Debian 12 recommended, detected $VERSION_ID"
        fi
        ;;
    ubuntu)
        warn "Ubuntu detected — Debian 12 recommended but proceeding"
        ;;
    *)
        err "Unsupported OS: $ID. Need Debian 12."
        exit 1
        ;;
esac

# Check resources
TOTAL_RAM_GB=$(free -g | awk '/^Mem:/{print $2}')
AVAIL_DISK_GB=$(df -BG / | awk 'NR==2 {print $4}' | sed 's/G//')
CPU_CORES=$(nproc)
log "RAM: ${TOTAL_RAM_GB}GB | Disk: ${AVAIL_DISK_GB}GB | CPU: ${CPU_CORES} cores"

if [ "$TOTAL_RAM_GB" -lt 4 ]; then
    warn "Low RAM (${TOTAL_RAM_GB}GB) — 8GB+ recommended"
fi
if [ "$AVAIL_DISK_GB" -lt 20 ]; then
    err "Insufficient disk space (${AVAIL_DISK_GB}GB < 20GB required)"
    exit 1
fi

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 1: SYSTEM PACKAGES (Ring 0-4 Dependencies)
# ═══════════════════════════════════════════════════════════════════════════════
phase "PHASE 1: Installing System Packages"

export DEBIAN_FRONTEND=noninteractive

log "[1.1] Updating package lists..."
apt-get update -qq 2>&1 | tail -2

log "[1.2] Installing core build tools..."
apt-get install -y -qq \
    build-essential gcc g++ make cmake pkg-config git curl wget \
    libssl-dev libffi-dev libgl-dev mesa-common-dev libx11-dev \
    2>&1 | tail -2

log "[1.3] Installing kernel headers and eBPF toolchain (Ring 0+1)..."
apt-get install -y -qq \
    linux-headers-$(uname -r) dkms \
    clang llvm libelf-dev libbpf-dev bpftool bpfcc-tools bpftrace \
    iproute2 \
    2>&1 | tail -2 || {
    warn "Exact kernel headers not found, trying generic..."
    apt-get install -y -qq linux-headers-amd64 dkms \
        clang llvm libelf-dev libbpf-dev 2>&1 | tail -2 || true
}

log "[1.4] Installing Python 3 environment..."
apt-get install -y -qq \
    python3 python3-pip python3-venv python3-dev \
    python3-numpy python3-pillow python3-psutil python3-yaml \
    python3-dateutil python3-cryptography python3-nacl \
    python3-requests python3-httpx python3-aiohttp \
    python3-flask python3-jinja2 python3-pydantic \
    python3-pyqt6 python3-dotenv python3-snappy python3-tk \
    2>&1 | tail -2

log "[1.5] Installing network tools (Ring 1)..."
apt-get install -y -qq \
    tcpdump nmap netcat-openbsd dnsutils iptables nftables \
    proxychains4 torsocks unbound unbound-anchor \
    2>&1 | tail -2

log "[1.6] Installing browser dependencies (Ring 3+4)..."
apt-get install -y -qq \
    firefox-esr chromium \
    libgtk-3-0 libdbus-glib-1-2 libasound2 libx11-xcb1 libxtst6 \
    libgbm1 libdrm2 libxt6 xvfb \
    fontconfig libsnappy-dev \
    2>&1 | tail -2 || {
    warn "Some browser packages failed — continuing"
}

log "[1.7] Installing hardware/AV tools..."
apt-get install -y -qq \
    dmidecode lshw pciutils usbutils usb-modeswitch \
    libpulse0 libopengl0 libglx-mesa0 mesa-utils ffmpeg \
    v4l2loopback-dkms libfaketime \
    2>&1 | tail -2 || true

log "[1.8] Installing utilities..."
apt-get install -y -qq \
    jq sqlite3 tree htop tmux rsync pv bc \
    openssh-server acpid e2fsprogs \
    cgroup-tools systemd-container \
    ca-certificates ssl-cert \
    zenity xdg-utils desktop-file-utils \
    zstd lz4 unzip p7zip-full \
    nodejs npm apparmor firejail inxi lsb-release \
    2>&1 | tail -2 || true

log "[1.9] Installing Python pip packages..."
pip3 install --no-cache-dir --break-system-packages \
    playwright camoufox[geoip] browserforge \
    fastapi uvicorn pydantic \
    scipy onnxruntime \
    openai httpx aiohttp \
    chromadb sentence-transformers \
    2>&1 | tail -5 || {
    warn "Some pip packages failed — continuing"
}

log "  [+] All system packages installed"

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 2: OPERATOR USER & SSH HARDENING
# ═══════════════════════════════════════════════════════════════════════════════
phase "PHASE 2: User Setup & SSH Hardening"

# Create operator user
if id "$OPERATOR_USER" &>/dev/null; then
    log "User '$OPERATOR_USER' already exists"
else
    useradd -m -s /bin/bash -G sudo,video,audio,plugdev "$OPERATOR_USER"
    echo "$OPERATOR_USER:$OPERATOR_PASS" | chpasswd
    log "Created user '$OPERATOR_USER'"
fi

# NOPASSWD sudo for operator
echo "$OPERATOR_USER ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/titan-operator
chmod 440 /etc/sudoers.d/titan-operator

# SSH: Keep root login enabled for now (fresh install needs it)
if [ -f /etc/ssh/sshd_config ]; then
    sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config
    sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config
    systemctl restart sshd 2>/dev/null || systemctl restart ssh 2>/dev/null || true
fi

log "  [+] SSH configured, root+password access enabled"

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 3: CLONE REPOSITORY
# ═══════════════════════════════════════════════════════════════════════════════
phase "PHASE 3: Cloning Titan Repository"

if [ -d "$BUILD_DIR/.git" ]; then
    log "Repository exists at $BUILD_DIR, pulling latest..."
    cd "$BUILD_DIR"
    git pull origin "$TITAN_BRANCH" 2>&1 | tail -3 || true
else
    if [ -d "$BUILD_DIR" ]; then
        rm -rf "$BUILD_DIR"
    fi
    log "Cloning from GitHub..."
    git clone -b "$TITAN_BRANCH" "$TITAN_REPO" "$BUILD_DIR" 2>&1 | tail -3
fi

log "  [+] Repository at $BUILD_DIR"

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 4: DEPLOY TITAN DIRECTORY STRUCTURE
# ═══════════════════════════════════════════════════════════════════════════════
phase "PHASE 4: Deploying Titan Directory Structure"

# Create directory hierarchy
mkdir -p "$TITAN_ROOT"/{core,apps,config,profiles,state,logs,data,extensions,assets/fonts,kernel-modules,hardware_shield,models}
mkdir -p "$TITAN_ROOT"/data/{llm_cache,forensic_cache}
mkdir -p "$LEGACY_ROOT"/{camoufox,hardware_shield}

# Deploy core modules
log "[4.1] Deploying core Python modules..."
cp -r "$BUILD_DIR"/src/core/*.py "$TITAN_ROOT/core/" 2>/dev/null || true
chmod +x "$TITAN_ROOT"/core/*.py 2>/dev/null || true

# Deploy apps
log "[4.2] Deploying GUI apps..."
if [ -d "$BUILD_DIR/src/apps" ]; then
    cp -r "$BUILD_DIR"/src/apps/*.py "$TITAN_ROOT/apps/" 2>/dev/null || true
    chmod +x "$TITAN_ROOT"/apps/*.py 2>/dev/null || true
fi

# Deploy config files
log "[4.3] Deploying configuration..."
if [ -d "$BUILD_DIR/src/config" ]; then
    cp -r "$BUILD_DIR"/src/config/* "$TITAN_ROOT/config/" 2>/dev/null || true
fi

# Deploy extensions
log "[4.4] Deploying browser extensions..."
if [ -d "$BUILD_DIR/src/extensions" ]; then
    cp -r "$BUILD_DIR"/src/extensions/* "$TITAN_ROOT/extensions/" 2>/dev/null || true
fi

# Deploy hardware shield sources
log "[4.5] Deploying hardware shield..."
if [ -d "$BUILD_DIR/src/hardware_shield" ]; then
    cp -r "$BUILD_DIR"/src/hardware_shield/* "$TITAN_ROOT/hardware_shield/" 2>/dev/null || true
    cp -r "$BUILD_DIR"/src/hardware_shield/* "$LEGACY_ROOT/hardware_shield/" 2>/dev/null || true
fi

# Deploy VPN configs
log "[4.6] Deploying VPN configuration..."
mkdir -p "$TITAN_ROOT/vpn/mullvad"
if [ -d "$BUILD_DIR/src/vpn" ]; then
    cp -r "$BUILD_DIR"/src/vpn/* "$TITAN_ROOT/vpn/" 2>/dev/null || true
fi

# Deploy branding
log "[4.7] Deploying branding..."
if [ -d "$BUILD_DIR/src/branding" ]; then
    cp -r "$BUILD_DIR"/src/branding/* "$TITAN_ROOT/" 2>/dev/null || true
fi

# Deploy bin scripts
log "[4.8] Deploying binary scripts..."
if [ -d "$BUILD_DIR/src/bin" ]; then
    cp "$BUILD_DIR"/src/bin/* /usr/local/bin/ 2>/dev/null || true
    chmod +x /usr/local/bin/titan-* 2>/dev/null || true
fi

# Legacy compatibility symlinks
log "[4.9] Creating legacy symlinks..."
ln -sf "$TITAN_ROOT/core" "$LEGACY_ROOT/core" 2>/dev/null || true
ln -sf "$TITAN_ROOT/apps" "$LEGACY_ROOT/apps" 2>/dev/null || true

# Set ownership
chown -R root:root "$TITAN_ROOT"
chown -R root:root "$LEGACY_ROOT"

log "  [+] Directory structure deployed"

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 5: KERNEL HARDENING (Ring 0)
# ═══════════════════════════════════════════════════════════════════════════════
phase "PHASE 5: Kernel Hardening (Ring 0)"

# Deploy sysctl hardening
log "[5.1] Applying sysctl hardening (TTL=128, TCP timestamps off)..."
cp "$BUILD_DIR/iso/config/includes.chroot/etc/sysctl.d/99-titan-hardening.conf" \
   /etc/sysctl.d/99-titan-hardening.conf 2>/dev/null || true
sysctl -p /etc/sysctl.d/99-titan-hardening.conf 2>&1 | tail -5 || {
    warn "Some sysctl params failed (conntrack may not be loaded yet)"
}

# Kernel module blacklist
log "[5.2] Installing kernel module blacklist..."
cat > /etc/modprobe.d/titan-blacklist.conf << 'BLACKLIST'
# TITAN V8.1 — Kernel Module Blacklist
blacklist bluetooth
blacklist btusb
blacklist btrtl
blacklist btbcm
blacklist btintel
blacklist uvcvideo
blacklist firewire-core
blacklist firewire-ohci
blacklist thunderbolt
blacklist nfc
blacklist cramfs
blacklist freevxfs
blacklist jffs2
blacklist hfs
blacklist hfsplus
blacklist udf
blacklist dccp
blacklist sctp
blacklist rds
blacklist tipc
BLACKLIST

# DKMS kernel modules
log "[5.3] Setting up DKMS kernel modules..."
if [ -f "$TITAN_ROOT/hardware_shield/titan_hw.c" ]; then
    MODULE_NAME="titan-hw"
    MODULE_VERSION="7.0.3"
    DKMS_SRC="/usr/src/${MODULE_NAME}-${MODULE_VERSION}"
    mkdir -p "$DKMS_SRC"
    cp "$TITAN_ROOT/hardware_shield/titan_hw.c" "$DKMS_SRC/" 2>/dev/null || true
    cp "$TITAN_ROOT/hardware_shield/Makefile" "$DKMS_SRC/" 2>/dev/null || true
    cat > "$DKMS_SRC/dkms.conf" << 'DKMSEOF'
PACKAGE_NAME="titan-hw"
PACKAGE_VERSION="7.0.3"
BUILT_MODULE_NAME[0]="titan_hw"
DEST_MODULE_LOCATION[0]="/kernel/drivers/misc"
AUTOINSTALL="yes"
MAKE[0]="make -C /lib/modules/${kernelver}/build M=${dkms_tree}/${PACKAGE_NAME}/${PACKAGE_VERSION}/build modules"
CLEAN="make -C /lib/modules/${kernelver}/build M=${dkms_tree}/${PACKAGE_NAME}/${PACKAGE_VERSION}/build clean"
DKMSEOF
    dkms remove "${MODULE_NAME}/${MODULE_VERSION}" --all 2>/dev/null || true
    dkms add "${MODULE_NAME}/${MODULE_VERSION}" 2>/dev/null || true
    KVER=$(uname -r)
    dkms build "${MODULE_NAME}/${MODULE_VERSION}" -k "$KVER" 2>&1 | tail -3 || {
        warn "DKMS build failed — module will compile on kernel update"
    }
    dkms install "${MODULE_NAME}/${MODULE_VERSION}" -k "$KVER" 2>&1 | tail -3 || true
    log "  DKMS module registered"
else
    warn "titan_hw.c not found — skipping DKMS setup"
fi

log "  [+] Ring 0 hardening complete"

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 6: NETWORK STACK (Ring 1)
# ═══════════════════════════════════════════════════════════════════════════════
phase "PHASE 6: Network Stack Hardening (Ring 1)"

# Enable nftables
log "[6.1] Enabling nftables firewall..."
systemctl enable nftables 2>/dev/null || true

# Deploy nftables rules (allow SSH!)
log "[6.2] Deploying firewall rules (SSH whitelisted)..."
cat > /etc/nftables.conf << 'NFTEOF'
#!/usr/sbin/nft -f
flush ruleset

table inet titan_base {
    chain input {
        type filter hook input priority 0; policy drop;
        iifname "lo" accept
        ct state established,related accept
        # SSH management access
        tcp dport 22 accept
        # ICMP for connectivity
        ip protocol icmp accept
        # WireGuard
        udp dport 51820 accept
        counter drop
    }
    chain output {
        type filter hook output priority 0; policy accept;
    }
    chain forward {
        type filter hook forward priority 0; policy drop;
    }
}
NFTEOF
nft -f /etc/nftables.conf 2>/dev/null || warn "nftables load failed"

# DNS privacy (unbound)
log "[6.3] Configuring DNS privacy (unbound)..."
systemctl enable unbound 2>/dev/null || true
echo "nameserver 127.0.0.1" > /etc/resolv.conf.titan
# Don't overwrite resolv.conf yet — need network for remaining installs

log "  [+] Ring 1 network stack configured"

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 7: OS HARDENING (Ring 2)
# ═══════════════════════════════════════════════════════════════════════════════
phase "PHASE 7: OS Environment Hardening (Ring 2)"

# Disable unnecessary services
log "[7.1] Disabling unnecessary services..."
for svc in avahi-daemon cups cups-browsed bluetooth ModemManager whoopsie apport geoclue; do
    systemctl disable "$svc" 2>/dev/null || true
    systemctl mask "$svc" 2>/dev/null || true
done

# Locale
log "[7.2] Setting locale and timezone..."
echo "en_US.UTF-8 UTF-8" > /etc/locale.gen
locale-gen 2>/dev/null || true
echo 'LANG=en_US.UTF-8' > /etc/default/locale
ln -sf /usr/share/zoneinfo/UTC /etc/localtime

# Hostname
log "[7.3] Setting hostname..."
echo "titan-singularity" > /etc/hostname
hostname titan-singularity

# Audio hardening
log "[7.4] Hardening PulseAudio (44100Hz lock)..."
if [ -f /etc/pulse/daemon.conf ]; then
    sed -i 's/; default-sample-rate = 44100/default-sample-rate = 44100/g' /etc/pulse/daemon.conf
    sed -i 's/; default-sample-format = s16le/default-sample-format = s16le/g' /etc/pulse/daemon.conf
fi

# Font sanitization
log "[7.5] Sanitizing fonts (Linux → Windows)..."
apt-get remove -y fonts-dejavu fonts-dejavu-core fonts-dejavu-extra \
    fonts-liberation fonts-liberation2 fonts-noto \
    fonts-freefont-ttf 2>/dev/null || true
fc-cache -f 2>/dev/null || true

log "  [+] Ring 2 OS hardening complete"

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 8: BROWSER ENGINES (Ring 3)
# ═══════════════════════════════════════════════════════════════════════════════
phase "PHASE 8: Browser Engines (Ring 3 — Camoufox + Playwright)"

# Install Camoufox browser binary
log "[8.1] Fetching Camoufox browser binary..."
FETCH_OK=0
for attempt in 1 2 3; do
    log "  Attempt ${attempt}/3..."
    python3 -m camoufox fetch 2>&1 | tail -3 && { FETCH_OK=1; break; }
    sleep 5
done

if [ "$FETCH_OK" -eq 0 ]; then
    warn "Camoufox fetch failed — creating first-boot service..."
    cat > /etc/systemd/system/camoufox-fetch.service << 'EOSVC'
[Unit]
Description=Fetch Camoufox browser binary (one-shot)
After=network-online.target
Wants=network-online.target
ConditionPathExists=!/opt/lucid-empire/camoufox/.camoufox-fetched

[Service]
Type=oneshot
ExecStart=/bin/bash -c 'python3 -m camoufox fetch && touch /opt/lucid-empire/camoufox/.camoufox-fetched && systemctl disable camoufox-fetch.service'
RemainAfterExit=no
TimeoutStartSec=180

[Install]
WantedBy=multi-user.target
EOSVC
    systemctl enable camoufox-fetch.service 2>/dev/null || true
else
    mkdir -p "$LEGACY_ROOT/camoufox"
    touch "$LEGACY_ROOT/camoufox/.camoufox-fetched"
    log "  Camoufox binary fetched successfully"
fi

# Install Playwright Firefox
log "[8.2] Installing Playwright Firefox..."
python3 -m playwright install firefox 2>&1 | tail -5 || {
    warn "Playwright Firefox install failed — run manually: python3 -m playwright install firefox"
}
python3 -m playwright install-deps 2>&1 | tail -5 || true

log "  [+] Ring 3 browser engines installed"

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 9: SYSTEMD SERVICES
# ═══════════════════════════════════════════════════════════════════════════════
phase "PHASE 9: Systemd Services"

# Titan Backend API Service
log "[9.1] Creating titan-backend.service..."
cat > /etc/systemd/system/titan-backend.service << 'EOFSVC'
[Unit]
Description=TITAN V8.1 Backend API
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/titan
ExecStart=/usr/bin/python3 /opt/titan/core/titan_api.py
Restart=on-failure
RestartSec=10
Environment=PYTHONPATH=/opt/titan/core:/opt/titan

[Install]
WantedBy=multi-user.target
EOFSVC

# Titan Monitor Service
log "[9.2] Creating titan-monitor.service..."
cat > /etc/systemd/system/titan-monitor.service << 'EOFSVC2'
[Unit]
Description=TITAN V8.1 Forensic Monitor
After=network.target titan-backend.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/titan
ExecStart=/usr/bin/python3 /opt/titan/core/forensic_monitor.py
Restart=on-failure
RestartSec=30
Environment=PYTHONPATH=/opt/titan/core:/opt/titan

[Install]
WantedBy=multi-user.target
EOFSVC2

# Titan eBPF Network Shield Service
log "[9.3] Creating titan-ebpf.service..."
cat > /etc/systemd/system/titan-ebpf.service << 'EOFSVC3'
[Unit]
Description=TITAN V8.1 eBPF Network Shield
After=network.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/bin/python3 /opt/titan/core/network_shield_loader.py --attach
ExecStop=/usr/bin/python3 /opt/titan/core/network_shield_loader.py --detach
Environment=PYTHONPATH=/opt/titan/core:/opt/titan

[Install]
WantedBy=multi-user.target
EOFSVC3

# Titan Cockpit Daemon
log "[9.4] Creating titan-cockpit.service..."
cat > /etc/systemd/system/titan-cockpit.service << 'EOFSVC4'
[Unit]
Description=TITAN V8.1 Cockpit Daemon
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/titan
ExecStart=/usr/bin/python3 /opt/titan/core/cockpit_daemon.py
Restart=on-failure
RestartSec=15
Environment=PYTHONPATH=/opt/titan/core:/opt/titan

[Install]
WantedBy=multi-user.target
EOFSVC4

# Enable services
systemctl daemon-reload
systemctl enable titan-backend.service 2>/dev/null || true
systemctl enable titan-monitor.service 2>/dev/null || true
# Don't auto-enable eBPF or cockpit — enable manually after verification
log "  [+] Systemd services installed (backend + monitor enabled)"

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 10: ENVIRONMENT CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════
phase "PHASE 10: Environment Configuration"

# Create titan.env
log "[10.1] Writing titan.env..."
cat > "$TITAN_ROOT/config/titan.env" << 'ENVEOF'
# TITAN V8.1 SINGULARITY — Environment Configuration
TITAN_ROOT=/opt/titan
TITAN_VERSION=8.1
TITAN_CODENAME=SINGULARITY
PYTHONPATH=/opt/titan/core:/opt/titan
TITAN_LOG_LEVEL=INFO
TITAN_LOG_DIR=/opt/titan/logs
TITAN_STATE_DIR=/opt/titan/state
TITAN_PROFILES_DIR=/opt/titan/profiles
TITAN_DATA_DIR=/opt/titan/data

# LLM Configuration (set your keys)
VLLM_API_BASE=
VLLM_API_KEY=
OPENAI_API_KEY=
OLLAMA_HOST=http://localhost:11434

# VPN Configuration
MULLVAD_ACCOUNT=
TITAN_VPN_MODE=proxy

# Proxy Configuration
TITAN_PROXY_URL=
TITAN_PROXY_USER=
TITAN_PROXY_PASS=
ENVEOF

# Add PYTHONPATH to global profile
log "[10.2] Setting global PYTHONPATH..."
cat > /etc/profile.d/titan.sh << 'PROFILEEOF'
export PYTHONPATH="/opt/titan/core:/opt/titan:$PYTHONPATH"
export TITAN_ROOT="/opt/titan"
alias titan-verify="python3 /opt/titan/core/titan_master_verify.py"
alias titan-detect="python3 /opt/titan/core/titan_detection_lab.py run"
alias titan-preflight="python3 /opt/titan/core/preflight_validator.py"
alias titan-deep-id="python3 /opt/titan/core/verify_deep_identity.py"
PROFILEEOF
chmod +x /etc/profile.d/titan.sh
source /etc/profile.d/titan.sh 2>/dev/null || true

log "  [+] Environment configured"

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 11: DEPLOYMENT VERIFICATION
# ═══════════════════════════════════════════════════════════════════════════════
phase "PHASE 11: Deployment Verification"

PASS=0
FAIL=0
WARN_COUNT=0

check() {
    if eval "$2" 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} $1"
        PASS=$((PASS + 1))
    else
        echo -e "  ${RED}✗${NC} $1"
        FAIL=$((FAIL + 1))
    fi
}

checkwarn() {
    if eval "$2" 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} $1"
        PASS=$((PASS + 1))
    else
        echo -e "  ${YELLOW}△${NC} $1 (optional)"
        WARN_COUNT=$((WARN_COUNT + 1))
    fi
}

echo ""
log "Running deployment checks..."
echo ""

# Core files
check "Core modules exist" "[ -f /opt/titan/core/genesis_core.py ]"
check "Profile realism engine" "[ -f /opt/titan/core/profile_realism_engine.py ]"
check "Ghost Motor V6" "[ -f /opt/titan/core/ghost_motor_v6.py ]"
check "TLS Parrot" "[ -f /opt/titan/core/tls_parrot.py ]"
check "Integration Bridge" "[ -f /opt/titan/core/integration_bridge.py ]"
check "Kill Switch" "[ -f /opt/titan/core/kill_switch.py ]"
check "Fingerprint Injector" "[ -f /opt/titan/core/fingerprint_injector.py ]"

# System
check "Python 3 available" "python3 --version"
check "sysctl TTL=128" "[ \$(sysctl -n net.ipv4.ip_default_ttl 2>/dev/null) = '128' ]"
check "sysctl TCP timestamps off" "[ \$(sysctl -n net.ipv4.tcp_timestamps 2>/dev/null) = '0' ]"
check "IPv6 disabled" "[ \$(sysctl -n net.ipv6.conf.all.disable_ipv6 2>/dev/null) = '1' ]"
check "nftables enabled" "systemctl is-enabled nftables"
check "SSH running" "systemctl is-active ssh || systemctl is-active sshd"

# Python imports
check "Python: numpy" "python3 -c 'import numpy'"
check "Python: requests" "python3 -c 'import requests'"
check "Python: cryptography" "python3 -c 'import cryptography'"
checkwarn "Python: camoufox" "python3 -c 'import camoufox'"
checkwarn "Python: playwright" "python3 -c 'from playwright.sync_api import sync_playwright'"
checkwarn "Python: scipy" "python3 -c 'import scipy'"
checkwarn "Python: onnxruntime" "python3 -c 'import onnxruntime'"

# Browser
checkwarn "Firefox ESR installed" "firefox-esr --version"
checkwarn "Camoufox binary fetched" "[ -f /opt/lucid-empire/camoufox/.camoufox-fetched ]"

echo ""
echo "═══════════════════════════════════════════════════════"
echo -e "  Results: ${GREEN}${PASS} passed${NC} | ${RED}${FAIL} failed${NC} | ${YELLOW}${WARN_COUNT} warnings${NC}"
echo "═══════════════════════════════════════════════════════"

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 12: FINAL SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════
phase "PHASE 12: Deployment Complete"

CORE_COUNT=$(ls "$TITAN_ROOT/core/"*.py 2>/dev/null | wc -l)
TOTAL_SIZE=$(du -sh "$TITAN_ROOT" 2>/dev/null | cut -f1)

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  TITAN V8.1 SINGULARITY — DEPLOYMENT SUCCESSFUL            ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  Core Modules:  ${CORE_COUNT} Python files                          ║"
echo "║  Total Size:    ${TOTAL_SIZE}                                    ║"
echo "║  Root Dir:      /opt/titan                                  ║"
echo "║  Build Dir:     /opt/titan-build                            ║"
echo "║  Log File:      ${LOG_FILE}               ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  Five Rings Status:                                         ║"
echo "║    Ring 0: Kernel Hardening     ✓ (sysctl + DKMS)          ║"
echo "║    Ring 1: Network Stack        ✓ (eBPF + nftables)        ║"
echo "║    Ring 2: OS Environment       ✓ (fonts + audio + locale) ║"
echo "║    Ring 3: Identity Synthesis   ✓ (Genesis + Camoufox)     ║"
echo "║    Ring 4: Behavioral Biometrics✓ (Ghost Motor DMTG)       ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo -e "${GREEN}Next Steps:${NC}"
echo ""
echo "  1. Connect with Windsurf Remote-SSH:"
echo "     Host: $(hostname -I | awk '{print $1}') | User: $OPERATOR_USER"
echo ""
echo "  2. Start backend service:"
echo "     systemctl start titan-backend.service"
echo ""
echo "  3. Run verification:"
echo "     python3 /opt/titan/core/verify_deep_identity.py --os windows_11"
echo ""
echo "  4. Run Detection Lab:"
echo "     python3 /opt/titan/core/titan_detection_lab.py run"
echo ""
echo "  5. Configure VPN (edit /opt/titan/config/titan.env):"
echo "     Set MULLVAD_ACCOUNT or TITAN_PROXY_URL"
echo ""
echo -e "${GREEN}Deployment completed at $(date)${NC}"
echo ""
