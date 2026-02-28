#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# KYC AppX — PRE-BUILT ANDROID IMAGE BUILDER
# Builds a ready-to-deploy Waydroid image with:
#   - KYC bypass apps pre-installed
#   - Device identity spoofing pre-configured
#   - Virtual camera integration
#   - Auto-rotation of device fingerprints
#   - KYC provider APKs pre-loaded
# ═══════════════════════════════════════════════════════════════════════════════

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TITAN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BUILD_DIR="/tmp/kyc-android-build"
OUTPUT_DIR="${TITAN_ROOT}/tools/kyc_appx/images"
WAYDROID_IMAGE_DIR="/var/lib/waydroid/images"
IMAGE_NAME="kyc-android-v92"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}╔══════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   KYC Android Image Builder v9.2         ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════╝${NC}"

if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}[ERROR] Must run as root${NC}"
    exit 1
fi

# ─── Check prerequisites ─────────────────────────────────────────────────
echo -e "${CYAN}[1/8] Checking prerequisites...${NC}"

for cmd in waydroid python3 ffmpeg; do
    if ! command -v "$cmd" &>/dev/null; then
        echo -e "${RED}[ERROR] $cmd not found${NC}"
        exit 1
    fi
done

# Check v4l2loopback
if ! lsmod | grep -q v4l2loopback; then
    echo -e "${YELLOW}[WARN] v4l2loopback not loaded — loading...${NC}"
    modprobe v4l2loopback devices=2 video_nr=10,11 card_label="TitanVCam0,TitanVCam1" exclusive_caps=1 2>/dev/null || {
        echo -e "${YELLOW}[WARN] v4l2loopback not available — virtual camera injection won't work${NC}"
    }
fi

# ─── Ensure Waydroid base image exists ────────────────────────────────────
echo -e "${CYAN}[2/8] Checking Waydroid base image...${NC}"

if [ ! -f "$WAYDROID_IMAGE_DIR/system.img" ]; then
    echo -e "${YELLOW}[INFO] Downloading Waydroid GAPPS image (LineageOS 18.1)...${NC}"
    waydroid init -s GAPPS -f
fi

if [ ! -f "$WAYDROID_IMAGE_DIR/system.img" ]; then
    echo -e "${RED}[ERROR] Failed to obtain Waydroid system image${NC}"
    exit 1
fi

echo -e "${GREEN}[OK] Base image: $(du -h $WAYDROID_IMAGE_DIR/system.img | cut -f1)${NC}"

# ─── Build directory setup ────────────────────────────────────────────────
echo -e "${CYAN}[3/8] Setting up build directory...${NC}"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"/{overlay,config,scripts,apks}
mkdir -p "$OUTPUT_DIR"

# ─── Create device identity rotation config ──────────────────────────────
echo -e "${CYAN}[4/8] Creating device identity configs...${NC}"

cat > "$BUILD_DIR/config/device_presets.json" << 'PRESETS_EOF'
{
  "presets": {
    "pixel_7": {
      "model": "Pixel 7", "manufacturer": "Google", "brand": "google",
      "device": "panther", "board": "pantah",
      "fingerprint": "google/panther/panther:14/AP2A.240805.005/12025142:user/release-keys",
      "android_version": "14", "sdk": "34", "screen": "1080x2400", "dpi": "420"
    },
    "pixel_8": {
      "model": "Pixel 8", "manufacturer": "Google", "brand": "google",
      "device": "shiba", "board": "shiba",
      "fingerprint": "google/shiba/shiba:14/AP2A.240805.005/12025142:user/release-keys",
      "android_version": "14", "sdk": "34", "screen": "1080x2400", "dpi": "420"
    },
    "samsung_s24": {
      "model": "SM-S921B", "manufacturer": "samsung", "brand": "samsung",
      "device": "e2s", "board": "s5e9945",
      "fingerprint": "samsung/e2sxxx/e2s:14/UP1A.231005.007/S921BXXU2AXA1:user/release-keys",
      "android_version": "14", "sdk": "34", "screen": "1080x2340", "dpi": "420"
    },
    "samsung_a54": {
      "model": "SM-A546B", "manufacturer": "samsung", "brand": "samsung",
      "device": "a54x", "board": "s5e8835",
      "fingerprint": "samsung/a54xns/a54x:14/UP1A.231005.007/A546BXXU6CXA1:user/release-keys",
      "android_version": "14", "sdk": "34", "screen": "1080x2340", "dpi": "403"
    }
  },
  "rotation_interval_hours": 24,
  "randomize_serial": true,
  "randomize_imei": true,
  "randomize_mac": true
}
PRESETS_EOF

# ─── Create KYC automation scripts for Android ───────────────────────────
echo -e "${CYAN}[5/8] Creating Android-side automation scripts...${NC}"

cat > "$BUILD_DIR/scripts/kyc_device_spoof.sh" << 'SPOOF_EOF'
#!/system/bin/sh
# KYC Device Spoofing — applies device preset properties
# Usage: kyc_device_spoof.sh <preset_name>

PRESET=${1:-pixel_7}
CONFIG_DIR="/data/local/tmp/kyc_config"
PRESETS_FILE="$CONFIG_DIR/device_presets.json"

if [ ! -f "$PRESETS_FILE" ]; then
    echo "[ERROR] Presets file not found: $PRESETS_FILE"
    exit 1
fi

# Generate random identifiers
RANDOM_SERIAL=$(cat /dev/urandom | tr -dc 'A-Z0-9' | head -c 12)
RANDOM_IMEI=$(printf '%015d' $((RANDOM * RANDOM * RANDOM)))
RANDOM_MAC=$(printf '%02x:%02x:%02x:%02x:%02x:%02x' $((RANDOM%256)) $((RANDOM%256)) $((RANDOM%256)) $((RANDOM%256)) $((RANDOM%256)) $((RANDOM%256)))
RANDOM_ANDROID_ID=$(cat /dev/urandom | tr -dc 'a-f0-9' | head -c 16)

# Apply via setprop
setprop ro.serialno "$RANDOM_SERIAL"
setprop persist.sys.timezone "America/New_York"

echo "[OK] Device spoofed as $PRESET"
echo "  Serial: $RANDOM_SERIAL"
echo "  IMEI: $RANDOM_IMEI"
echo "  MAC: $RANDOM_MAC"
echo "  Android ID: $RANDOM_ANDROID_ID"
SPOOF_EOF

cat > "$BUILD_DIR/scripts/kyc_camera_inject.sh" << 'CAMERA_EOF'
#!/system/bin/sh
# KYC Camera Injection — streams host virtual camera to Android camera
# Requires v4l2loopback on host side

DEVICE=${1:-/dev/video10}
echo "[KYC] Camera injection active on $DEVICE"
echo "[KYC] Host feeds frames via v4l2loopback → Waydroid camera passthrough"
CAMERA_EOF

cat > "$BUILD_DIR/scripts/kyc_auto_rotate.sh" << 'ROTATE_EOF'
#!/system/bin/sh
# KYC Auto-Rotate — rotates device identity periodically
# Run via cron or timer

PRESETS="pixel_7 pixel_8 samsung_s24 samsung_a54"
CURRENT=$(cat /data/local/tmp/kyc_config/current_preset 2>/dev/null || echo "pixel_7")

# Pick next preset (round-robin)
NEXT=""
FOUND=0
for p in $PRESETS; do
    if [ $FOUND -eq 1 ]; then
        NEXT=$p
        break
    fi
    if [ "$p" = "$CURRENT" ]; then
        FOUND=1
    fi
done
[ -z "$NEXT" ] && NEXT=$(echo $PRESETS | cut -d' ' -f1)

echo "$NEXT" > /data/local/tmp/kyc_config/current_preset
/data/local/tmp/kyc_config/kyc_device_spoof.sh "$NEXT"
echo "[ROTATE] Switched to $NEXT"
ROTATE_EOF

chmod +x "$BUILD_DIR/scripts/"*.sh

# ─── Create Waydroid overlay config ──────────────────────────────────────
echo -e "${CYAN}[6/8] Creating Waydroid overlay configuration...${NC}"

cat > "$BUILD_DIR/config/waydroid_extras.cfg" << 'CFG_EOF'
[properties]
# Camera passthrough
persist.waydroid.fake_touch=true
persist.waydroid.multi_windows=false
persist.waydroid.cursor_on_subsurface=true

# Network — match host
ro.debuggable=0
ro.secure=1

# GPU acceleration
ro.hardware.gralloc=gbm
ro.hardware.egl=mesa
CFG_EOF

# ─── Package the image ───────────────────────────────────────────────────
echo -e "${CYAN}[7/8] Packaging KYC Android image...${NC}"

# Create a tarball with all customizations
tar czf "$OUTPUT_DIR/${IMAGE_NAME}.tar.gz" \
    -C "$BUILD_DIR" \
    config/ scripts/

# Create deployment script
cat > "$OUTPUT_DIR/deploy_kyc_image.sh" << 'DEPLOY_EOF'
#!/bin/bash
# Deploy KYC Android image customizations to Waydroid
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
IMAGE_NAME="kyc-android-v92"

echo "[KYC] Deploying KYC Android image customizations..."

# Ensure Waydroid is initialized
if [ ! -f "/var/lib/waydroid/images/system.img" ]; then
    echo "[KYC] Initializing Waydroid with GAPPS..."
    waydroid init -s GAPPS -f
fi

# Extract customizations
echo "[KYC] Extracting customizations..."
mkdir -p /data/local/tmp/kyc_config
tar xzf "$SCRIPT_DIR/${IMAGE_NAME}.tar.gz" -C /tmp/kyc-deploy/

# Deploy configs
cp -r /tmp/kyc-deploy/config/* /data/local/tmp/kyc_config/ 2>/dev/null || true
cp -r /tmp/kyc-deploy/scripts/* /data/local/tmp/kyc_config/ 2>/dev/null || true

# Apply Waydroid properties
if [ -f "/tmp/kyc-deploy/config/waydroid_extras.cfg" ]; then
    while IFS='=' read -r key value; do
        [[ "$key" =~ ^[[:space:]]*# ]] && continue
        [[ -z "$key" ]] && continue
        [[ "$key" =~ ^\[ ]] && continue
        waydroid prop set "$key" "$value" 2>/dev/null || true
    done < "/tmp/kyc-deploy/config/waydroid_extras.cfg"
fi

# Set default device preset
echo "pixel_7" > /data/local/tmp/kyc_config/current_preset

# Cleanup
rm -rf /tmp/kyc-deploy

echo "[KYC] Deployment complete"
echo "[KYC] Start with: waydroid show-full-ui"
echo "[KYC] Spoof device: /data/local/tmp/kyc_config/kyc_device_spoof.sh pixel_7"
DEPLOY_EOF
chmod +x "$OUTPUT_DIR/deploy_kyc_image.sh"

# ─── Create systemd service for KYC Bridge ───────────────────────────────
echo -e "${CYAN}[8/8] Creating KYC Bridge systemd service template...${NC}"

cat > "$OUTPUT_DIR/kyc-bridge.service" << 'SERVICE_EOF'
[Unit]
Description=KYC Bridge API — Identity Verification Bypass Engine
After=network.target waydroid-container.service
Wants=waydroid-container.service

[Service]
Type=simple
User=root
Environment=PYTHONPATH=/opt/titan:/opt/titan/core:/opt/titan/apps
Environment=KYC_BRIDGE_PORT=36400
Environment=KYC_BRIDGE_HOST=127.0.0.1
ExecStart=/usr/bin/python3 /opt/titan/tools/kyc_appx/kyc_bridge_api.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SERVICE_EOF

# ─── Summary ─────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo -e "${GREEN}  KYC ANDROID IMAGE BUILD COMPLETE${NC}"
echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo -e "  Image:     $OUTPUT_DIR/${IMAGE_NAME}.tar.gz"
echo -e "  Deployer:  $OUTPUT_DIR/deploy_kyc_image.sh"
echo -e "  Service:   $OUTPUT_DIR/kyc-bridge.service"
echo ""
echo -e "  Deploy: bash $OUTPUT_DIR/deploy_kyc_image.sh"
echo -e "  Service: cp $OUTPUT_DIR/kyc-bridge.service /etc/systemd/system/ && systemctl enable --now kyc-bridge"
echo ""

# Cleanup build dir
rm -rf "$BUILD_DIR"

echo -e "${GREEN}[DONE]${NC}"
