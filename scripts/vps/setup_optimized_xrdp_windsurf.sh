#!/bin/bash
set -e

echo "=========================================="
echo "Titan OS - Optimized XRDP + Windsurf Setup"
echo "VPS: 187.77.186.252 (Fresh Debian 12)"
echo "=========================================="

# Update system
echo "[1/8] Updating system packages..."
apt-get update
apt-get upgrade -y

# Install XFCE (lightweight desktop) + XRDP with optimizations
echo "[2/8] Installing XFCE desktop + XRDP..."
DEBIAN_FRONTEND=noninteractive apt-get install -y \
    xfce4 xfce4-goodies \
    xrdp \
    dbus-x11 \
    xorgxrdp \
    pulseaudio \
    firefox-esr \
    git curl wget unzip zip \
    build-essential \
    python3 python3-pip python3-venv \
    fonts-liberation fonts-dejavu \
    thunar-archive-plugin \
    xarchiver

# Configure XRDP for optimal performance
echo "[3/8] Optimizing XRDP configuration..."

# XRDP main config - reduce latency
cat > /etc/xrdp/xrdp.ini <<'EOF'
[Globals]
ini_version=1
fork=true
port=3389
tcp_nodelay=true
tcp_keepalive=true
security_layer=negotiate
crypt_level=high
certificate=
key_file=
ssl_protocols=TLSv1.2, TLSv1.3
autorun=
allow_channels=true
allow_multimon=true
bitmap_cache=true
bitmap_compression=true
bulk_compression=true
max_bpp=32
new_cursors=true
use_fastpath=both
tcp_send_buffer_bytes=32768
tcp_recv_buffer_bytes=32768

[Xorg]
name=Xorg
lib=libxup.so
username=ask
password=ask
ip=127.0.0.1
port=-1
code=20
EOF

# XRDP session config - use XFCE
cat > /etc/xrdp/startwm.sh <<'EOF'
#!/bin/sh
if [ -r /etc/default/locale ]; then
  . /etc/default/locale
  export LANG LANGUAGE
fi

# Disable compositing for better performance
xfconf-query -c xfwm4 -p /general/use_compositing -s false 2>/dev/null || true
xfconf-query -c xfwm4 -p /general/frame_opacity -s 100 2>/dev/null || true
xfconf-query -c xfwm4 -p /general/inactive_opacity -s 100 2>/dev/null || true

# Start XFCE session
startxfce4
EOF

chmod +x /etc/xrdp/startwm.sh

# Enable and start XRDP
systemctl enable xrdp
systemctl restart xrdp

# Configure firewall for XRDP
echo "[4/8] Configuring firewall..."
if command -v ufw >/dev/null 2>&1; then
    ufw allow 3389/tcp
    ufw --force enable
fi

# Install Windsurf IDE
echo "[5/8] Installing Windsurf IDE..."
cd /tmp

# Download Windsurf (using latest Linux x64 .deb)
WINDSURF_URL="https://windsurf-stable.codeiumdata.com/linux-x64/stable"
wget -O windsurf.deb "$WINDSURF_URL" || {
    echo "Trying alternative download method..."
    curl -L -o windsurf.deb "$WINDSURF_URL"
}

# Install Windsurf
dpkg -i windsurf.deb || apt-get install -f -y
rm -f windsurf.deb

# Create desktop shortcut for all users
echo "[6/8] Creating Windsurf desktop shortcut..."
mkdir -p /etc/skel/Desktop
cat > /etc/skel/Desktop/windsurf.desktop <<'EOF'
[Desktop Entry]
Name=Windsurf IDE
Comment=AI-powered code editor
Exec=/usr/bin/windsurf %F
Icon=windsurf
Terminal=false
Type=Application
Categories=Development;IDE;
StartupNotify=true
EOF

chmod +x /etc/skel/Desktop/windsurf.desktop

# Create workspace directory
echo "[7/8] Creating workspace structure..."
mkdir -p /root/workspace
mkdir -p /root/workspace/titan-7
mkdir -p /root/workspace/projects
mkdir -p /root/workspace/memories

# Copy desktop shortcut to root
mkdir -p /root/Desktop
cp /etc/skel/Desktop/windsurf.desktop /root/Desktop/
chmod +x /root/Desktop/windsurf.desktop

# Install essential Python packages
echo "[8/12] Installing Python development tools..."
pip3 install --upgrade pip
pip3 install \
    flask \
    requests \
    redis \
    pyyaml \
    python-dotenv \
    psutil \
    camoufox

# Install Google Chrome
echo "[9/12] Installing Google Chrome..."
wget -q -O /tmp/google-chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
dpkg -i /tmp/google-chrome.deb || apt-get install -f -y
rm -f /tmp/google-chrome.deb

# Install Chromium (backup browser)
echo "[10/12] Installing Chromium..."
apt-get install -y chromium chromium-driver

# Install Camoufox browser dependencies
echo "[11/12] Setting up Camoufox browser..."
mkdir -p /opt/camoufox
cd /opt/camoufox

# Camoufox will be managed via Python package (already installed via pip)
# Create launcher script
cat > /usr/local/bin/camoufox-browser <<'CAMEOF'
#!/bin/bash
python3 -c "from camoufox.sync_api import Camoufox; browser = Camoufox(headless=False); browser.new_page(); input('Press Enter to close...')"
CAMEOF
chmod +x /usr/local/bin/camoufox-browser

# Create Camoufox desktop shortcut
cat > /root/Desktop/camoufox.desktop <<'EOF'
[Desktop Entry]
Name=Camoufox Browser
Comment=Anti-detect browser
Exec=/usr/local/bin/camoufox-browser
Icon=firefox
Terminal=false
Type=Application
Categories=Network;WebBrowser;
EOF
chmod +x /root/Desktop/camoufox.desktop

# Install Multilogin X and Multilogin X Luna
echo "[12/12] Installing Multilogin X and Multilogin X Luna..."
mkdir -p /opt/multilogin

# Note: Multilogin X requires manual download from multilogin.com
# Creating placeholder structure and instructions
cat > /opt/multilogin/INSTALL_INSTRUCTIONS.txt <<'MLEOF'
Multilogin X Installation Instructions
========================================

Multilogin X and Multilogin X Luna are commercial products.
To install:

1. Download from: https://multilogin.com/download/
2. Choose "Multilogin X" for Linux
3. Extract to /opt/multilogin/
4. Run: chmod +x /opt/multilogin/multilogin-x
5. Create desktop shortcut

Alternative: Use Multilogin cloud version via web interface
URL: https://app.multilogin.com/

For Luna browser profiles:
- Luna is integrated within Multilogin X
- Access via Multilogin X interface
- Create new profile and select "Luna" browser engine

Credentials needed:
- Multilogin account (requires subscription)
- License key

MLEOF

# Create placeholder desktop shortcuts
cat > /root/Desktop/multilogin-x.desktop <<'EOF'
[Desktop Entry]
Name=Multilogin X
Comment=Anti-detect browser platform
Exec=xdg-open https://app.multilogin.com/
Icon=web-browser
Terminal=false
Type=Application
Categories=Network;WebBrowser;
EOF
chmod +x /root/Desktop/multilogin-x.desktop

cat > /root/Desktop/multilogin-luna.desktop <<'EOF'
[Desktop Entry]
Name=Multilogin Luna
Comment=Multilogin Luna browser profile
Exec=xdg-open https://app.multilogin.com/
Icon=web-browser
Terminal=false
Type=Application
Categories=Network;WebBrowser;
EOF
chmod +x /root/Desktop/multilogin-luna.desktop

# Create Chrome desktop shortcut
cat > /root/Desktop/google-chrome.desktop <<'EOF'
[Desktop Entry]
Name=Google Chrome
Comment=Web Browser
Exec=/usr/bin/google-chrome-stable %U
Icon=google-chrome
Terminal=false
Type=Application
Categories=Network;WebBrowser;
EOF
chmod +x /root/Desktop/google-chrome.desktop

# Firefox ESR is already installed, create desktop shortcut
cat > /root/Desktop/firefox.desktop <<'EOF'
[Desktop Entry]
Name=Firefox ESR
Comment=Web Browser
Exec=/usr/bin/firefox-esr %u
Icon=firefox-esr
Terminal=false
Type=Application
Categories=Network;WebBrowser;
EOF
chmod +x /root/Desktop/firefox.desktop

# Performance tuning
cat >> /etc/sysctl.conf <<'EOF'

# XRDP Performance Tuning
net.core.rmem_max=134217728
net.core.wmem_max=134217728
net.ipv4.tcp_rmem=4096 87380 67108864
net.ipv4.tcp_wmem=4096 65536 67108864
net.ipv4.tcp_congestion_control=bbr
net.core.default_qdisc=fq
EOF

sysctl -p

echo ""
echo "=========================================="
echo "✓ XRDP + Windsurf + Browsers Setup Complete!"
echo "=========================================="
echo ""
echo "XRDP Connection Details:"
echo "  IP: 187.77.186.252"
echo "  Port: 3389"
echo "  Username: root"
echo "  Password: Chilaw@123@llm"
echo ""
echo "Installed Software:"
echo "  ✓ Windsurf IDE (/usr/bin/windsurf)"
echo "  ✓ Google Chrome (/usr/bin/google-chrome-stable)"
echo "  ✓ Firefox ESR (/usr/bin/firefox-esr)"
echo "  ✓ Chromium (/usr/bin/chromium)"
echo "  ✓ Camoufox (Python package + launcher)"
echo "  ✓ Multilogin X (web interface ready)"
echo ""
echo "Desktop Shortcuts Created:"
echo "  - Windsurf IDE"
echo "  - Google Chrome"
echo "  - Firefox ESR"
echo "  - Camoufox Browser"
echo "  - Multilogin X"
echo "  - Multilogin Luna"
echo ""
echo "Workspace ready at: /root/workspace/"
echo "  - /root/workspace/titan-7 (for codebase)"
echo "  - /root/workspace/projects (for other projects)"
echo "  - /root/workspace/memories (for context)"
echo ""
echo "Next steps:"
echo "  1. Connect via RDP to 187.77.186.252:3389"
echo "  2. Transfer titan-7.zip to /root/workspace/"
echo "  3. Launch Windsurf from desktop"
echo "  4. For Multilogin X: See /opt/multilogin/INSTALL_INSTRUCTIONS.txt"
echo "=========================================="
