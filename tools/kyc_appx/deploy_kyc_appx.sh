#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# KYC AppX DEPLOYMENT SCRIPT
# Deploys KYC AppX + Waydroid Android VM to /opt/titan with systemd services
# ═══════════════════════════════════════════════════════════════════════════════

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TITAN_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
INSTALL_DIR="/opt/titan"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}╔══════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   KYC AppX DEPLOYMENT v9.2               ║${NC}"
echo -e "${CYAN}║   Identity Verification + Waydroid        ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════╝${NC}"

if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}[ERROR] Must run as root${NC}"
    exit 1
fi

# ─── 1. Install Python dependencies ──────────────────────────────────────
echo -e "${CYAN}[1/8] Installing Python dependencies...${NC}"
pip3 install --break-system-packages \
    flask flask-cors aiohttp requests Pillow 2>/dev/null || {
    echo -e "${YELLOW}[WARN] Some pip packages may have failed — check manually${NC}"
}

# ─── 2. Install system dependencies (v4l2loopback, ffmpeg, TTS) ─────────
echo -e "${CYAN}[2/8] Installing system dependencies...${NC}"
apt-get update -qq
apt-get install -y -q \
    v4l2loopback-dkms v4l2loopback-utils v4l-utils \
    ffmpeg \
    espeak-ng \
    python3-opencv \
    gstreamer1.0-tools gstreamer1.0-plugins-good \
    2>/dev/null || {
    echo -e "${YELLOW}[WARN] Some system packages may have failed${NC}"
}

# Load v4l2loopback kernel module
if ! lsmod | grep -q v4l2loopback; then
    modprobe v4l2loopback devices=1 \
        video_nr=2 \
        card_label="Integrated Webcam" \
        exclusive_caps=1 2>/dev/null || {
        echo -e "${YELLOW}[WARN] v4l2loopback module load failed — may need kernel headers${NC}"
    }
fi

# Persist v4l2loopback on boot
if [ ! -f /etc/modules-load.d/v4l2loopback.conf ]; then
    echo "v4l2loopback" > /etc/modules-load.d/v4l2loopback.conf
    cat > /etc/modprobe.d/v4l2loopback.conf << 'MODEOF'
options v4l2loopback devices=1 video_nr=2 card_label="Integrated Webcam" exclusive_caps=1
MODEOF
fi

echo -e "${GREEN}[OK] System dependencies${NC}"

# ─── 3. Deploy KYC core modules ─────────────────────────────────────────
echo -e "${CYAN}[3/8] Deploying KYC core modules...${NC}"
mkdir -p "$INSTALL_DIR/core" "$INSTALL_DIR/apps" "$INSTALL_DIR/android"

for f in kyc_core.py kyc_enhanced.py kyc_voice_engine.py waydroid_sync.py \
         tof_depth_synthesis.py biometric_mimicry.py ai_intelligence_engine.py; do
    if [ -f "$TITAN_ROOT/src/core/$f" ]; then
        cp -v "$TITAN_ROOT/src/core/$f" "$INSTALL_DIR/core/$f"
    else
        echo -e "${YELLOW}[SKIP] $f not found in src/core/${NC}"
    fi
done

# Deploy KYC GUI app
if [ -f "$TITAN_ROOT/src/apps/app_kyc.py" ]; then
    cp -v "$TITAN_ROOT/src/apps/app_kyc.py" "$INSTALL_DIR/apps/app_kyc.py"
    chmod +x "$INSTALL_DIR/apps/app_kyc.py"
fi

# Deploy Android console
if [ -f "$TITAN_ROOT/src/android/kyc_android_console.py" ]; then
    cp -v "$TITAN_ROOT/src/android/kyc_android_console.py" "$INSTALL_DIR/android/kyc_android_console.py"
    chmod +x "$INSTALL_DIR/android/kyc_android_console.py"
fi

echo -e "${GREEN}[OK] Core modules deployed${NC}"

# ─── 4. Deploy Bridge API ────────────────────────────────────────────────
echo -e "${CYAN}[4/8] Deploying KYC Bridge API...${NC}"
mkdir -p "$INSTALL_DIR/tools/kyc_appx"
cp -v "$SCRIPT_DIR/kyc_bridge_api.py" "$INSTALL_DIR/tools/kyc_appx/kyc_bridge_api.py"
cp -v "$SCRIPT_DIR/launch_kyc_appx.sh" "$INSTALL_DIR/tools/kyc_appx/launch_kyc_appx.sh"
chmod +x "$INSTALL_DIR/tools/kyc_appx/"*.sh
echo -e "${GREEN}[OK] Bridge API deployed${NC}"

# ─── 5. Create systemd service for KYC Bridge ────────────────────────────
echo -e "${CYAN}[5/8] Creating systemd service...${NC}"
cat > /etc/systemd/system/kyc-bridge.service << 'SYSTEMD_EOF'
[Unit]
Description=KYC Bridge API — Identity Verification Engine
After=network.target

[Service]
Type=simple
User=root
Environment=PYTHONPATH=/opt/titan:/opt/titan/core:/opt/titan/apps:/opt/titan/android
Environment=KYC_BRIDGE_PORT=36400
Environment=KYC_BRIDGE_HOST=127.0.0.1
ExecStart=/usr/bin/python3 /opt/titan/tools/kyc_appx/kyc_bridge_api.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SYSTEMD_EOF

systemctl daemon-reload
systemctl enable kyc-bridge.service
systemctl restart kyc-bridge.service

sleep 2
if systemctl is-active --quiet kyc-bridge.service; then
    echo -e "${GREEN}[OK] kyc-bridge.service is active${NC}"
else
    echo -e "${YELLOW}[WARN] kyc-bridge.service may not have started — check: journalctl -u kyc-bridge${NC}"
fi

# ─── 6. Set up Waydroid (if kernel supports it) ─────────────────────────
echo -e "${CYAN}[6/8] Setting up Waydroid Android container...${NC}"

WAYDROID_READY=0

# Check for binder support
if [ -e /dev/binderfs/binder ] || [ -e /dev/binder ] || \
   modprobe binder_linux 2>/dev/null || \
   grep -q "CONFIG_ANDROID_BINDER_IPC=y" /boot/config-$(uname -r) 2>/dev/null; then
    echo -e "${GREEN}  Binder support: YES${NC}"

    # Install Waydroid
    if ! command -v waydroid &>/dev/null; then
        echo "  Installing Waydroid..."
        # Add Waydroid repo
        if [ ! -f /usr/share/keyrings/waydroid.gpg ]; then
            curl -fsSL https://repo.waydro.id/waydroid.gpg | gpg --dearmor -o /usr/share/keyrings/waydroid.gpg 2>/dev/null || true
        fi
        if [ ! -f /etc/apt/sources.list.d/waydroid.list ]; then
            echo "deb [signed-by=/usr/share/keyrings/waydroid.gpg] https://repo.waydro.id/ bookworm main" > /etc/apt/sources.list.d/waydroid.list
        fi
        apt-get update -qq
        apt-get install -y -q waydroid 2>/dev/null || {
            echo -e "${YELLOW}  [WARN] Waydroid install failed — kernel may not support binder${NC}"
        }
    fi

    # Initialize Waydroid with GAPPS image
    if command -v waydroid &>/dev/null; then
        if [ ! -d /var/lib/waydroid/images ]; then
            echo "  Downloading LineageOS 18.1 GAPPS image..."
            waydroid init -s GAPPS -f 2>/dev/null || {
                echo -e "${YELLOW}  [WARN] waydroid init failed — may need manual setup${NC}"
            }
        fi

        # Create Waydroid systemd service
        cat > /etc/systemd/system/waydroid-container.service << 'WDEOF'
[Unit]
Description=Waydroid Android Container
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/waydroid container start
ExecStop=/usr/bin/waydroid container stop
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
WDEOF
        systemctl daemon-reload
        systemctl enable waydroid-container.service 2>/dev/null || true
        WAYDROID_READY=1
        echo -e "${GREEN}  Waydroid: INSTALLED${NC}"
    fi
else
    echo -e "${YELLOW}  Binder support: NO — Waydroid requires kernel with binder/ashmem${NC}"
    echo -e "${YELLOW}  To enable: install kernel with CONFIG_ANDROID_BINDER_IPC=y${NC}"
    echo -e "${YELLOW}  Or install binder DKMS: apt install binder-dkms${NC}"
fi

# ─── 7. Create desktop entry + CLI ──────────────────────────────────────
echo -e "${CYAN}[7/8] Creating desktop entry and CLI...${NC}"

cat > /usr/share/applications/kyc-appx.desktop << 'DESKTOP_EOF'
[Desktop Entry]
Name=KYC AppX
Comment=Identity Verification Bypass + Waydroid Android
Exec=/usr/bin/python3 /opt/titan/apps/app_kyc.py
Icon=preferences-desktop-user
Terminal=false
Type=Application
Categories=Utility;Security;
DESKTOP_EOF

cat > /usr/local/bin/kyc-appx << 'CLI_EOF'
#!/bin/bash
export PYTHONPATH="/opt/titan:/opt/titan/core:/opt/titan/apps:/opt/titan/android"
python3 /opt/titan/apps/app_kyc.py "$@"
CLI_EOF
chmod +x /usr/local/bin/kyc-appx

cat > /usr/local/bin/titan-android << 'ANDROID_EOF'
#!/bin/bash
export PYTHONPATH="/opt/titan:/opt/titan/core:/opt/titan/apps:/opt/titan/android"
python3 /opt/titan/android/kyc_android_console.py "$@"
ANDROID_EOF
chmod +x /usr/local/bin/titan-android

echo -e "${GREEN}[OK] Desktop + CLI commands created${NC}"

# ─── 8. Verify ──────────────────────────────────────────────────────────
echo -e "${CYAN}[8/8] Verifying deployment...${NC}"

echo ""
echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo -e "${GREEN}  KYC AppX DEPLOYMENT COMPLETE${NC}"
echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo ""
echo -e "  Bridge API:     http://127.0.0.1:36400/api/v1/health"
echo -e "  Desktop:        kyc-appx"
echo -e "  Android CLI:    titan-android"
echo -e "  Service:        systemctl status kyc-bridge"
echo -e "  Logs:           journalctl -u kyc-bridge -f"
echo -e "  Waydroid:       $([ $WAYDROID_READY -eq 1 ] && echo 'READY' || echo 'NOT AVAILABLE (kernel lacks binder)')"
echo ""
echo -e "  Modules deployed:"
for m in kyc_core kyc_enhanced kyc_voice_engine waydroid_sync tof_depth_synthesis; do
    if [ -f "$INSTALL_DIR/core/${m}.py" ]; then
        echo -e "    ${GREEN}✓${NC} ${m}.py"
    else
        echo -e "    ${RED}✗${NC} ${m}.py"
    fi
done
echo ""

# Quick health check
curl -s http://127.0.0.1:36400/api/v1/status 2>/dev/null | python3 -m json.tool 2>/dev/null || true
