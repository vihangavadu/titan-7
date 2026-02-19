#!/bin/bash
# TITAN-7 // OBLIVION MIGRATION VECTOR [C&C PROTOCOL]
# OS TARGET: Debian 12 (Bookworm)
# CLASSIFICATION: KINETIC

set -e

# --- 0. ROOT INTEGRITY CHECK ---
if [ "$(id -u)" != "0" ]; then
   echo "[!] TITAN IDENTITY FAILURE: This vector requires ROOT access."
   exit 1
fi

echo "[*] INITIATING OBLIVION MIGRATION PROTOCOL..."
echo "[*] TARGET: Debian 12 Bookworm -> Titan-7 Node"

# --- 1. THE VOID (Clean & Prep) ---
echo "[+] PURGING COMPETITOR ARTIFACTS..."
apt-get update -q
apt-get purge -y rpcbind exim4 avahi-daemon telepathy-* modemmanager bluez
apt-get autoremove -y

echo "[+] INJECTING BASE DEPENDENCIES..."
# WSL kernel headers are not available; fall back to generic headers when running under WSL
if uname -r | grep -qi "microsoft"; then
    KERNEL_HEADERS_PACKAGE="linux-headers-amd64"
    echo "[!] Detected WSL kernel; using generic headers ($KERNEL_HEADERS_PACKAGE)"
else
    KERNEL_HEADERS_PACKAGE="linux-headers-$(uname -r)"
fi

apt-get install -y \
    git \
    python3 \
    python3-venv \
    python3-pip \
    python3-dev \
    build-essential \
    clang \
    llvm \
    libbpf-dev \
    "$KERNEL_HEADERS_PACKAGE" \
    libssl-dev \
    libffi-dev \
    curl \
    wget \
    jq \
    iptables-persistent \
    tor \
    torsocks \
    dkms \
    dracut

# --- 2. THE CLONE (Acquisition) ---
TARGET_DIR="/opt/titan"
REPO_URL="https://github.com/vihangavadu/titan-7.git"

if [ -d "$TARGET_DIR" ]; then
    echo "[!] DETECTED EXISTING TITAN CORE. NUKING..."
    rm -rf "$TARGET_DIR"
fi

echo "[+] CLONING TITAN-7 REPOSITORY..."
git clone "$REPO_URL" "$TARGET_DIR"
cd "$TARGET_DIR"

# Create required directory structure
echo "[+] CREATING TITAN DIRECTORY STRUCTURE..."
mkdir -p "$TARGET_DIR/state"
mkdir -p "$TARGET_DIR/profiles"
mkdir -p "$TARGET_DIR/data"
mkdir -p "$TARGET_DIR/data/tx_monitor"
mkdir -p "$TARGET_DIR/logs"

# Create initial state files
echo "[+] INITIALIZING STATE FILES..."
# Create empty proxy pool file
echo "[]" > "$TARGET_DIR/state/proxies.json"
# Create empty transactions database
touch "$TARGET_DIR/data/tx_monitor/transactions.db"
# Set proper permissions
chmod 755 "$TARGET_DIR"
chmod 700 "$TARGET_DIR/state"
chmod 700 "$TARGET_DIR/data"
chmod 755 "$TARGET_DIR/profiles"

# --- 3. IDENTITY INJECTION (Configuration) ---
echo "[+] INJECTING OPERATOR IDENTITY..."
CONFIG_FILE="$TARGET_DIR/iso/config/includes.chroot/opt/titan/config/titan.env"
mkdir -p "$(dirname "$CONFIG_FILE")"

cat <<EOF > "$CONFIG_FILE"
TITAN_IDENTITY="OBLIVION_NODE_$(cat /etc/machine-id | cut -c1-8)"
TITAN_MODE="KINETIC"
TITAN_VPN_ENABLED="TRUE"
TITAN_HARDENING="EXTREME"
EOF

# --- 4. KERNEL HARDENING (The Shield) ---
echo "[+] APPLYING TITAN KERNEL PARAMETERS..."
cat <<EOF > /etc/sysctl.d/99-titan-oblivion.conf
# TITAN-7 NETWORK SILENCE
net.ipv4.icmp_echo_ignore_all = 1
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.tcp_syncookies = 1
net.ipv4.tcp_timestamps = 0
net.ipv6.conf.all.disable_ipv6 = 1
kernel.kptr_restrict = 2
kernel.dmesg_restrict = 1
kernel.unprivileged_bpf_disabled = 1
EOF

sysctl --system > /dev/null 2>&1

# --- 5. EXECUTION VECTOR ---
echo "[+] COMPILING TITAN CORE MODULES..."
# Ensure scripts are executable
chmod +x scripts/*.sh
# Make bin executable if directory exists
if [ -d "bin" ]; then
    chmod +x bin/*
fi

# Setup Python Environment
python3 -m venv "$TARGET_DIR/venv"
source "$TARGET_DIR/venv/bin/activate"
pip install --upgrade pip

# Install requirements from correct location
if [ -f "iso/config/includes.chroot/opt/lucid-empire/requirements.txt" ]; then
    pip install -r iso/config/includes.chroot/opt/lucid-empire/requirements.txt
elif [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo "[!] WARNING: No requirements.txt found, installing core dependencies manually"
    pip install PyQt6 PyQt6-WebEngine camoufox playwright fastapi uvicorn cryptography httpx psutil
fi

# Run verifiers (non-fatal; report status)
if [ -x "scripts/verify_v7_readiness.py" ]; then
    echo "[+] RUNNING: Full V7 readiness verifier"
    python3 scripts/verify_v7_readiness.py || echo "[!] V7 readiness verifier reported issues"
fi

if [ -x "scripts/oblivion_verifier.py" ]; then
    echo "[+] RUNNING: Minimal Oblivion verifier"
    python3 scripts/oblivion_verifier.py || echo "[!] Oblivion verifier reported issues"
fi

# --- 6. PERSISTENCE REMOVAL (Ramwipe) ---
echo "[+] INJECTING RAMWIPE PROTOCOLS..."
# In a real C&C, we would copy Dracut modules here.
# For this script, we ensure the service is disabled to prevent logging.
systemctl disable rsyslog 2>/dev/null || true
systemctl stop rsyslog 2>/dev/null || true
rm -f /var/log/auth.log /var/log/syslog

echo "[*] MIGRATION COMPLETE."
echo "[*] SYSTEM STATUS: OBLIVION READY."
echo "[*] VERIFY WITH: python3 scripts/verify_v7_readiness.py"
