#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# TITAN V7.0.3 — VPS/RDP DEPLOYMENT SCRIPT
# AUTHORITY: Dva.12 | STATUS: OBLIVION_ACTIVE
# OBJECTIVE: Deploy Titan OS build environment on remote VPS/RDP servers
#
# Supported Platforms:
#   - Debian 12 (Bookworm) VPS
#   - Ubuntu 22.04/24.04 VPS
#   - Windows Server 2019/2022 RDP (via WSL2)
#
# Usage:
#   wget https://raw.githubusercontent.com/YOUR_REPO/titan-main/deploy_vps.sh
#   chmod +x deploy_vps.sh
#   sudo ./deploy_vps.sh
# ═══════════════════════════════════════════════════════════════════════════

set -euo pipefail

# ── CONFIGURATION ──
TITAN_REPO="https://github.com/YOUR_USERNAME/titan-main.git"
TITAN_BRANCH="main"
INSTALL_DIR="/opt/titan-build"
BUILD_USER="titan"
MIN_RAM_GB=8
MIN_DISK_GB=50

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  TITAN V7.0.3 VPS/RDP DEPLOYMENT                           ║"
echo "║  Remote Build Environment Setup                            ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 1: SYSTEM VALIDATION
# ═══════════════════════════════════════════════════════════════════════════
echo -e "${BLUE}[1/7] System Validation${NC}"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}[!] ERROR: Must run as root (use sudo)${NC}"
    exit 1
fi

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS_NAME="$ID"
    OS_VERSION="$VERSION_ID"
    echo "  [+] Detected: $PRETTY_NAME"
else
    echo -e "${RED}[!] ERROR: Cannot detect OS${NC}"
    exit 1
fi

# Validate supported OS
case "$OS_NAME" in
    debian)
        if [ "$OS_VERSION" != "12" ]; then
            echo -e "${YELLOW}[!] WARNING: Debian 12 recommended, detected $OS_VERSION${NC}"
        fi
        ;;
    ubuntu)
        if [[ ! "$OS_VERSION" =~ ^(22.04|24.04)$ ]]; then
            echo -e "${YELLOW}[!] WARNING: Ubuntu 22.04/24.04 recommended, detected $OS_VERSION${NC}"
        fi
        ;;
    *)
        echo -e "${RED}[!] ERROR: Unsupported OS: $OS_NAME${NC}"
        echo "    Supported: Debian 12, Ubuntu 22.04/24.04"
        exit 1
        ;;
esac

# Check RAM
TOTAL_RAM_GB=$(free -g | awk '/^Mem:/{print $2}')
if [ "$TOTAL_RAM_GB" -lt "$MIN_RAM_GB" ]; then
    echo -e "${RED}[!] ERROR: Insufficient RAM (${TOTAL_RAM_GB}GB < ${MIN_RAM_GB}GB required)${NC}"
    exit 1
fi
echo "  [+] RAM: ${TOTAL_RAM_GB}GB (>= ${MIN_RAM_GB}GB required)"

# Check disk space
AVAIL_DISK_GB=$(df -BG / | awk 'NR==2 {print $4}' | sed 's/G//')
if [ "$AVAIL_DISK_GB" -lt "$MIN_DISK_GB" ]; then
    echo -e "${RED}[!] ERROR: Insufficient disk space (${AVAIL_DISK_GB}GB < ${MIN_DISK_GB}GB required)${NC}"
    exit 1
fi
echo "  [+] Disk: ${AVAIL_DISK_GB}GB available (>= ${MIN_DISK_GB}GB required)"

# Check CPU cores
CPU_CORES=$(nproc)
echo "  [+] CPU: ${CPU_CORES} cores"

echo ""

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 2: PACKAGE INSTALLATION
# ═══════════════════════════════════════════════════════════════════════════
echo -e "${BLUE}[2/7] Installing Build Dependencies${NC}"

export DEBIAN_FRONTEND=noninteractive

echo "  [2.1] Updating package lists..."
apt-get update -qq

echo "  [2.2] Installing live-build and stealth tools..."
apt-get install -y -qq live-build debootstrap squashfs-tools xorriso isolinux syslinux-efi grub-pc-bin grub-efi-amd64-bin mtools dosfstools tor proxychains4 torsocks

echo "  [2.3] Configuring Proxychains for Tor..."
if [ -f /etc/proxychains4.conf ]; then
    cp /etc/proxychains4.conf /etc/proxychains4.conf.bak
fi
cat > /etc/proxychains4.conf << 'EOFPC'
strict_chain
proxy_dns
remote_dns_res
tcp_read_time_out 15000
tcp_connect_time_out 8000
[ProxyList]
socks5 127.0.0.1 9050
EOFPC

echo "  [2.4] Starting Tor service..."
systemctl start tor
systemctl enable tor || true

echo "  [2.5] Installing development tools..."
apt-get install -y -qq build-essential gcc g++ make cmake pkg-config git curl wget

echo "  [2.4] Installing kernel headers and DKMS..."
apt-get install -y -qq linux-headers-$(uname -r || echo "amd64") dkms

echo "  [2.5] Installing Single-Terminal Execution Block..."
cat > /usr/local/bin/titan-migrate << 'EOF_MIGRATE'
#!/bin/bash
# TITAN V7.0.3 — SINGLE-TERMINAL MIGRATION BLOCK
# AUTHORITY: Dva.12 | STATUS: OBLIVION_ACTIVE

set -euo pipefail

echo "[*] INITIATING TITAN OBLIVION MIGRATION..."

# 1. Enforce Stealth Networking
echo "[1] Hardening Network Stack..."
sysctl -p /opt/titan-build/iso/config/includes.chroot/etc/sysctl.d/99-titan-hardening.conf

# 2. Sync Configuration
echo "[2] Syncing Configuration..."
cp /opt/titan-build/iso/config/includes.chroot/etc/sysctl.d/99-titan-hardening.conf /etc/sysctl.d/
cp /opt/titan-build/iso/config/includes.chroot/etc/security/limits.d/disable-cores.conf /etc/security/limits.d/ 2>/dev/null || true

# 3. Finalize Source
echo "[3] Running Finalization Protocol..."
cd /opt/titan-build/iso && ./finalize_titan.sh

# 4. Initiate Build
echo "[4] Launching Build Engine..."
cd /opt/titan-build && ./start_build.sh

echo "[+] MIGRATION INITIALIZED. ATTACH TO TMUX TO MONITOR."
EOF_MIGRATE
chmod +x /usr/local/bin/titan-migrate

echo "  [2.6] Installing Python 3.11+..."
apt-get install -y -qq python3 python3-pip python3-venv python3-dev

echo "  [2.7] Installing eBPF toolchain..."
apt-get install -y -qq clang llvm libelf-dev libbpf-dev bpftool

echo "  [2.8] Installing additional utilities..."
apt-get install -y -qq jq bc rsync pv htop tmux iproute2 procps

echo "  [+] All dependencies installed"
echo ""

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 3: USER SETUP
# ═══════════════════════════════════════════════════════════════════════════
echo -e "${BLUE}[3/7] Creating Build User${NC}"

if id "$BUILD_USER" &>/dev/null; then
    echo "  [+] User '$BUILD_USER' already exists"
else
    useradd -m -s /bin/bash -G sudo "$BUILD_USER"
    echo "  [+] Created user '$BUILD_USER'"
    
    # Set random password
    RANDOM_PASS=$(openssl rand -base64 16)
    echo "$BUILD_USER:$RANDOM_PASS" | chpasswd
    echo "  [+] Password set (saved to /root/.titan_build_pass)"
    echo "$RANDOM_PASS" > /root/.titan_build_pass
    chmod 600 /root/.titan_build_pass
fi

# Allow passwordless sudo for build operations
if ! grep -q "^$BUILD_USER ALL=(ALL) NOPASSWD: /usr/sbin/lb" /etc/sudoers.d/titan-build 2>/dev/null; then
    echo "$BUILD_USER ALL=(ALL) NOPASSWD: /usr/sbin/lb" > /etc/sudoers.d/titan-build
    chmod 440 /etc/sudoers.d/titan-build
    echo "  [+] Configured passwordless sudo for lb commands"
fi

echo ""

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 4: REPOSITORY CLONE
# ═══════════════════════════════════════════════════════════════════════════
echo -e "${BLUE}[4/7] Cloning Titan Repository${NC}"

if [ -d "$INSTALL_DIR" ]; then
    echo "  [!] Directory $INSTALL_DIR already exists"
    read -p "  Remove and re-clone? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$INSTALL_DIR"
    else
        echo "  [+] Using existing repository"
        cd "$INSTALL_DIR"
        git pull origin "$TITAN_BRANCH" || true
    fi
fi

if [ ! -d "$INSTALL_DIR" ]; then
    echo "  [+] Cloning from $TITAN_REPO via Proxychains (Ghost Acquisition)..."
    # Wait for Tor to be ready
    for i in {1..30}; do
        if ss -tulpn | grep -q 9050; then
            echo "  [+] Tor is ready."
            break
        fi
        echo -n "."
        sleep 2
    done
    proxychains4 git clone -b "$TITAN_BRANCH" "$TITAN_REPO" "$INSTALL_DIR"
    echo "  [+] Repository cloned"
fi

chown -R "$BUILD_USER:$BUILD_USER" "$INSTALL_DIR"
echo "  [+] Ownership set to $BUILD_USER"
echo ""

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 5: PYTHON ENVIRONMENT
# ═══════════════════════════════════════════════════════════════════════════
echo -e "${BLUE}[5/7] Setting Up Python Environment${NC}"

cd "$INSTALL_DIR"

if [ ! -d "venv" ]; then
    echo "  [+] Creating Python virtual environment..."
    sudo -u "$BUILD_USER" python3 -m venv venv
fi

echo "  [+] Installing Python dependencies..."
sudo -u "$BUILD_USER" bash -c "source venv/bin/activate && pip install --upgrade pip setuptools wheel"

# Install profgen dependencies
if [ -f "profgen/requirements.txt" ]; then
    sudo -u "$BUILD_USER" bash -c "source venv/bin/activate && pip install -r profgen/requirements.txt"
else
    # Fallback: install common dependencies
    sudo -u "$BUILD_USER" bash -c "source venv/bin/activate && pip install pydantic requests"
fi

echo "  [+] Python environment ready"
echo ""

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 6: BUILD ENVIRONMENT CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════
echo -e "${BLUE}[6/7] Configuring Build Environment${NC}"

# Create build script wrapper
cat > "$INSTALL_DIR/build_iso.sh" << 'EOFBUILD'
#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/iso"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  TITAN V7.0.3 ISO BUILD                                     ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Run finalization
if [ -f "finalize_titan.sh" ]; then
    echo "[*] Running finalization protocol..."
    bash finalize_titan.sh
    echo ""
else
    echo "[!] WARNING: finalize_titan.sh not found, skipping finalization"
fi

# Clean previous build
echo "[*] Cleaning previous build artifacts..."
sudo lb clean --purge

# Build ISO
echo "[*] Starting ISO build (this will take 30-60 minutes)..."
START_TIME=$(date +%s)

sudo lb build 2>&1 | tee titan_v7_build_$(date +%Y%m%d_%H%M%S).log

END_TIME=$(date +%s)
BUILD_DURATION=$((END_TIME - START_TIME))
BUILD_MINUTES=$((BUILD_DURATION / 60))

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  BUILD COMPLETE                                             ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  Duration: ${BUILD_MINUTES} minutes                                    ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Find ISO
ISO_FILE=$(find . -maxdepth 1 -name "*.iso" -type f | head -n 1)
if [ -n "$ISO_FILE" ]; then
    ISO_SIZE=$(du -h "$ISO_FILE" | cut -f1)
    echo "ISO created: $ISO_FILE ($ISO_SIZE)"
    echo ""
    echo "Download command:"
    echo "  scp $(whoami)@$(hostname -I | awk '{print $1}'):$(pwd)/$ISO_FILE ."
else
    echo "[!] ERROR: ISO file not found"
    exit 1
fi
EOFBUILD

chmod +x "$INSTALL_DIR/build_iso.sh"
chown "$BUILD_USER:$BUILD_USER" "$INSTALL_DIR/build_iso.sh"

echo "  [+] Created build_iso.sh wrapper"

# Create tmux session script
cat > "$INSTALL_DIR/start_build.sh" << 'EOFTMUX'
#!/bin/bash
tmux new-session -d -s titan-build "cd $(dirname "$0") && ./build_iso.sh"
echo "Build started in tmux session 'titan-build'"
echo "Attach with: tmux attach -t titan-build"
echo "Detach with: Ctrl+B then D"
EOFTMUX

chmod +x "$INSTALL_DIR/start_build.sh"
chown "$BUILD_USER:$BUILD_USER" "$INSTALL_DIR/start_build.sh"

echo "  [+] Created start_build.sh (tmux wrapper)"

# Create systemd service for auto-build (optional)
cat > /etc/systemd/system/titan-build.service << EOFSVC
[Unit]
Description=TITAN V7.0.3 ISO Build Service
After=network.target

[Service]
Type=oneshot
User=$BUILD_USER
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/build_iso.sh
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOFSVC

systemctl daemon-reload
echo "  [+] Created systemd service (disabled by default)"
echo "      Enable with: systemctl enable titan-build.service"

echo ""

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 7: FINAL INSTRUCTIONS
# ═══════════════════════════════════════════════════════════════════════════
echo -e "${BLUE}[7/7] Deployment Complete${NC}"
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  TITAN V7.0.3 VPS DEPLOYMENT SUCCESSFUL                    ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  Build Directory: $INSTALL_DIR"
echo "║  Build User:      $BUILD_USER"
echo "║  Build Script:    $INSTALL_DIR/build_iso.sh"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo -e "${GREEN}Next Steps:${NC}"
echo ""
echo "1. Switch to build user:"
echo "   sudo su - $BUILD_USER"
echo ""
echo "2. Navigate to build directory:"
echo "   cd $INSTALL_DIR"
echo ""
echo "3. Start build (in tmux session):"
echo "   ./start_build.sh"
echo ""
echo "4. Or build directly:"
echo "   ./build_iso.sh"
echo ""
echo "5. Monitor build progress:"
echo "   tmux attach -t titan-build"
echo ""
echo -e "${YELLOW}Build Notes:${NC}"
echo "  - Build time: 30-60 minutes (depends on CPU/network)"
echo "  - ISO output: $INSTALL_DIR/iso/*.iso"
echo "  - Logs: $INSTALL_DIR/iso/*.log"
echo ""
echo -e "${YELLOW}Security Notes:${NC}"
echo "  - Build user password saved to: /root/.titan_build_pass"
echo "  - Firewall: Ensure only SSH (port 22) is exposed"
echo "  - After build: Download ISO and destroy VPS"
echo ""
echo -e "${GREEN}Build user password:${NC} $(cat /root/.titan_build_pass 2>/dev/null || echo 'N/A')"
echo ""
