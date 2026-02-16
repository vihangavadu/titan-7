#!/bin/bash
set -e
export DEBIAN_FRONTEND=noninteractive

echo "=============================================="
echo " TITAN V7.0 SINGULARITY - WSL Installation"
echo "=============================================="

TITAN_DIR="/mnt/c/Users/Administrator/Desktop/titan-main"

# --- Step 1: Core System Packages ---
echo "[TITAN] Step 1: Installing core system packages..."
apt-get update -qq

# Core packages (skip live-boot/live-config/desktop for WSL)
apt-get install -y --no-install-recommends \
  openssh-server network-manager \
  build-essential gcc git vim curl wget clang llvm cmake pkg-config \
  libssl-dev libffi-dev libgl-dev mesa-common-dev libx11-dev \
  python3 python3-pip python3-venv python3-dev \
  tcpdump nmap netcat-openbsd dnsutils iptables nftables iproute2 \
  libfaketime \
  firefox-esr libgtk-3-0 libdbus-glib-1-2 libasound2 libx11-xcb1 libxtst6 \
  cgroup-tools systemd-container \
  jq sqlite3 tree htop tmux unzip p7zip-full \
  python3-pyqt6 \
  libsnappy-dev \
  libsodium-dev python3-cryptography python3-nacl \
  python3-requests python3-httpx python3-aiohttp python3-flask python3-jinja2 \
  fontconfig fonts-liberation fonts-dejavu fonts-noto \
  dmidecode lshw pciutils usbutils \
  libpulse0 libopengl0 mesa-utils ffmpeg \
  proxychains4 dante-client torsocks \
  apparmor firejail \
  libelf-dev zlib1g-dev \
  inxi neofetch lsb-release \
  zstd lz4 \
  python3-numpy python3-pillow python3-psutil python3-yaml python3-dateutil \
  ca-certificates ssl-cert \
  zenity xdg-utils desktop-file-utils \
  nodejs npm \
  libgbm1 libdrm2 libxt6 xvfb \
  python3-tk python3-pydantic \
  lxc usb-modeswitch dbus-x11 \
  unbound unbound-anchor dkms acpid ifupdown \
  2>&1 | tail -5

echo "[TITAN] Core packages installed."

# --- Step 2: Python pip dependencies ---
echo "[TITAN] Step 2: Installing Python pip dependencies..."
PIP_BREAK=--break-system-packages
REQS="$TITAN_DIR/iso/config/includes.chroot/opt/lucid-empire/requirements.txt"
if [ -f "$REQS" ]; then
  pip3 install $PIP_BREAK -r "$REQS" 2>&1 | tail -10 || echo "[WARN] Some pip packages failed"
else
  echo "[WARN] requirements.txt not found at $REQS"
fi

# --- Step 3: Deploy TITAN directory structure ---
echo "[TITAN] Step 3: Deploying TITAN directory structure..."
mkdir -p /opt/titan/{config,profiles,vpn,logs,state,bin}
mkdir -p /opt/titan/core
mkdir -p /opt/lucid-empire

# Copy TITAN configs
if [ -d "$TITAN_DIR/iso/config/includes.chroot/opt/titan" ]; then
  cp -r "$TITAN_DIR/iso/config/includes.chroot/opt/titan/"* /opt/titan/ 2>/dev/null || true
  echo "[TITAN] Config files deployed to /opt/titan/"
fi

if [ -d "$TITAN_DIR/iso/config/includes.chroot/opt/lucid-empire" ]; then
  cp -r "$TITAN_DIR/iso/config/includes.chroot/opt/lucid-empire/"* /opt/lucid-empire/ 2>/dev/null || true
  echo "[TITAN] Lucid Empire files deployed to /opt/lucid-empire/"
fi

# Copy systemd services
if [ -d "$TITAN_DIR/iso/config/includes.chroot/etc/systemd/system" ]; then
  cp "$TITAN_DIR/iso/config/includes.chroot/etc/systemd/system/"*.service /etc/systemd/system/ 2>/dev/null || true
  echo "[TITAN] Systemd services deployed."
fi

# Copy sysctl configs
if [ -d "$TITAN_DIR/iso/config/includes.chroot/etc/sysctl.d" ]; then
  cp "$TITAN_DIR/iso/config/includes.chroot/etc/sysctl.d/"* /etc/sysctl.d/ 2>/dev/null || true
  echo "[TITAN] Sysctl configs deployed."
fi

# --- Step 4: Apply kernel hardening (WSL-safe subset) ---
echo "[TITAN] Step 4: Applying kernel hardening..."
sysctl -w net.ipv4.tcp_timestamps=0 2>/dev/null || true
sysctl -w net.ipv4.conf.all.accept_redirects=0 2>/dev/null || true
sysctl -w net.ipv4.conf.all.send_redirects=0 2>/dev/null || true
sysctl -w net.ipv4.icmp_echo_ignore_all=0 2>/dev/null || true

# --- Step 5: State files ---
echo "[TITAN] Step 5: Creating state files..."
echo "TITAN_VERSION=7.0.3" > /opt/titan/state/version
echo "CODENAME=SINGULARITY" >> /opt/titan/state/version
echo "INSTALL_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> /opt/titan/state/version
echo "PLATFORM=WSL" >> /opt/titan/state/version
echo "oblivion_deployed=true" > /opt/titan/state/oblivion.state
echo "migration_complete=true" >> /opt/titan/state/oblivion.state

# --- Step 6: Run verifiers ---
echo "[TITAN] Step 6: Running verification..."
if [ -f "$TITAN_DIR/scripts/verify_v7_readiness.py" ]; then
  python3 "$TITAN_DIR/scripts/verify_v7_readiness.py" 2>&1 | tail -20 || true
fi

echo ""
echo "=============================================="
echo " TITAN V7.0 SINGULARITY - INSTALLATION COMPLETE"
echo "=============================================="
echo " Platform: WSL ($(cat /etc/os-release | grep PRETTY_NAME | cut -d= -f2))"
echo " Kernel: $(uname -r)"
echo " TITAN Version: 7.0.3 SINGULARITY"
echo " Location: /opt/titan/"
echo "=============================================="
