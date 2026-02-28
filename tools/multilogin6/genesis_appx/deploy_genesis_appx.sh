#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# Genesis AppX - Full Deployment Script
# ═══════════════════════════════════════════════════════════════════════════
# Installs ML6 .deb, patches it with Genesis modifications, sets up
# Bridge API, desktop shortcut, and systemd service.
#
# Run on target Linux system (Debian/Ubuntu):
#   bash deploy_genesis_appx.sh /path/to/multilogin.deb
# ═══════════════════════════════════════════════════════════════════════════

set -e

DEB_PATH="${1:-}"
GENESIS_APPX_DIR="/opt/genesis-appx"
ML6_DIR="/opt/Multilogin"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TITAN_ROOT="${TITAN_ROOT:-/opt/titan}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

log()  { echo -e "${CYAN}[Genesis AppX]${NC} $1"; }
ok()   { echo -e "${GREEN}[OK]${NC} $1"; }
err()  { echo -e "${RED}[ERROR]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
step() { echo -e "\n${BOLD}=== $1 ===${NC}"; }

echo -e "${BOLD}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║           GENESIS APPX - DEPLOYMENT INSTALLER               ║"
echo "║     Multilogin 6 + Titan OS Genesis Engine Combined         ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# ─── Pre-checks ──────────────────────────────────────────────────────────

if [ "$(id -u)" -ne 0 ]; then
    err "Must run as root"
    exit 1
fi

if [ -z "$DEB_PATH" ]; then
    # Look for .deb in common locations
    for candidate in \
        "$SCRIPT_DIR/../multilogin.deb" \
        "$SCRIPT_DIR/../extracted/data/../../../multilogin.deb" \
        "/tmp/multilogin.deb" \
        "$HOME/multilogin.deb"; do
        if [ -f "$candidate" ]; then
            DEB_PATH="$candidate"
            break
        fi
    done
fi

# Also check if already extracted
if [ -z "$DEB_PATH" ] && [ -d "$SCRIPT_DIR/../extracted/data/opt/Multilogin" ]; then
    DEB_PATH="ALREADY_EXTRACTED"
    log "Using pre-extracted ML6 files"
fi

if [ -z "$DEB_PATH" ]; then
    err "Usage: $0 /path/to/multilogin-6.5-0-linux_x86_64.deb"
    err "  Or place multilogin.deb in /tmp/"
    exit 1
fi

# ─── Step 1: Install ML6 .deb ───────────────────────────────────────────

step "Step 1: Installing Multilogin 6 base"

if [ "$DEB_PATH" = "ALREADY_EXTRACTED" ]; then
    # Copy pre-extracted files
    log "Copying pre-extracted ML6 files..."
    mkdir -p "$ML6_DIR"
    cp -r "$SCRIPT_DIR/../extracted/data/opt/Multilogin/"* "$ML6_DIR/"
    
    # Copy desktop file
    mkdir -p /usr/share/applications/
    if [ -f "$SCRIPT_DIR/../extracted/data/usr/share/applications/multilogin.desktop" ]; then
        cp "$SCRIPT_DIR/../extracted/data/usr/share/applications/multilogin.desktop" /usr/share/applications/
    fi
    
    # Copy icons
    for size in 16x16 32x32 48x48 64x64 128x128 256x256; do
        src="$SCRIPT_DIR/../extracted/data/usr/share/icons/hicolor/${size}/apps/multilogin.png"
        if [ -f "$src" ]; then
            mkdir -p "/usr/share/icons/hicolor/${size}/apps/"
            cp "$src" "/usr/share/icons/hicolor/${size}/apps/multilogin.png"
            cp "$src" "/usr/share/icons/hicolor/${size}/apps/genesis-appx.png"
        fi
    done
    
    # Create symlink
    ln -sf "$ML6_DIR/multilogin" /usr/bin/multilogin
    chmod 4755 "$ML6_DIR/chrome-sandbox" 2>/dev/null || true
elif [ -f "$DEB_PATH" ]; then
    log "Installing $DEB_PATH..."
    dpkg -i "$DEB_PATH" 2>/dev/null || {
        apt-get install -f -y 2>/dev/null || true
        dpkg -i "$DEB_PATH"
    }
else
    err "DEB file not found: $DEB_PATH"
    exit 1
fi

# Verify ML6 installed
if [ ! -f "$ML6_DIR/multilogin" ]; then
    err "ML6 binary not found after install"
    exit 1
fi
ok "Multilogin 6 base installed at $ML6_DIR"

# ─── Step 2: Install Python dependencies ─────────────────────────────────

step "Step 2: Installing Python dependencies"

apt-get update -qq
apt-get install -y -qq python3 python3-pip curl >/dev/null 2>&1

pip3 install flask flask-cors -q 2>/dev/null || pip install flask flask-cors -q
ok "Python + Flask ready"

# ─── Step 3: Deploy Genesis AppX files ───────────────────────────────────

step "Step 3: Deploying Genesis AppX files"

mkdir -p "$GENESIS_APPX_DIR"

# Copy bridge API
cp "$SCRIPT_DIR/genesis_bridge_api.py" "$GENESIS_APPX_DIR/"
ok "Bridge API deployed"

# Copy launcher
cp "$SCRIPT_DIR/launch_genesis_appx.sh" "$GENESIS_APPX_DIR/"
chmod +x "$GENESIS_APPX_DIR/launch_genesis_appx.sh"
ok "Launcher deployed"

# Create CLI shortcut
cat > /usr/local/bin/genesis-appx << 'GEOF'
#!/bin/bash
exec /opt/genesis-appx/launch_genesis_appx.sh "$@"
GEOF
chmod +x /usr/local/bin/genesis-appx
ok "CLI shortcut: genesis-appx"

# ─── Step 4: Patch app.asar ─────────────────────────────────────────────

step "Step 4: Patching ML6 app.asar with Genesis modifications"

# Backup original
if [ ! -f "$ML6_DIR/resources/app.asar.original" ]; then
    cp "$ML6_DIR/resources/app.asar" "$ML6_DIR/resources/app.asar.original"
    ok "Original app.asar backed up"
fi

# Run the patcher
log "Running ASAR patcher..."
python3 "$SCRIPT_DIR/patch_ml6_asar.py" \
    --source "$ML6_DIR/resources/app.asar.original" \
    --output "$GENESIS_APPX_DIR"

# Install patched ASAR
if [ -f "$GENESIS_APPX_DIR/app.asar" ]; then
    cp "$GENESIS_APPX_DIR/app.asar" "$ML6_DIR/resources/app.asar"
    ok "Patched app.asar installed"
else
    warn "Patched ASAR not found - will use extracted files method"
fi

# ─── Step 5: Desktop integration ────────────────────────────────────────

step "Step 5: Desktop integration"

# Install desktop file
cat > /usr/share/applications/genesis-appx.desktop << 'EOF'
[Desktop Entry]
Name=Genesis AppX
Exec=/opt/genesis-appx/launch_genesis_appx.sh
Terminal=false
Type=Application
Icon=genesis-appx
StartupWMClass=Multilogin
Comment=Genesis AppX - Titan OS Anti-Detect Browser
Categories=Network;WebBrowser;Utility;
Keywords=browser;profile;fingerprint;anti-detect;genesis;titan;
EOF

# Copy icon (reuse ML6 icon for now, or use genesis icon if available)
for size in 16x16 32x32 48x48 64x64 128x128 256x256; do
    src="/usr/share/icons/hicolor/${size}/apps/multilogin.png"
    dst="/usr/share/icons/hicolor/${size}/apps/genesis-appx.png"
    if [ -f "$src" ] && [ ! -f "$dst" ]; then
        cp "$src" "$dst"
    fi
done

update-desktop-database /usr/share/applications/ 2>/dev/null || true
ok "Desktop shortcut installed"

# Also put shortcut on desktop if XFCE
for user_home in /root /home/*; do
    desktop_dir="$user_home/Desktop"
    if [ -d "$desktop_dir" ]; then
        cp /usr/share/applications/genesis-appx.desktop "$desktop_dir/"
        chmod +x "$desktop_dir/genesis-appx.desktop" 2>/dev/null || true
    fi
done

# ─── Step 6: Systemd service for Bridge API ──────────────────────────────

step "Step 6: Creating systemd service for Bridge API"

cat > /etc/systemd/system/genesis-bridge.service << EOF
[Unit]
Description=Genesis AppX Bridge API
After=network.target
Wants=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$GENESIS_APPX_DIR
Environment=TITAN_ROOT=$TITAN_ROOT
Environment=GENESIS_BRIDGE_PORT=36200
Environment=GENESIS_PROFILES_DIR=/root/.genesis_appx/profiles
Environment=GENESIS_CONFIG_DIR=/root/.genesis_appx
ExecStart=/usr/bin/python3 $GENESIS_APPX_DIR/genesis_bridge_api.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable genesis-bridge.service
systemctl start genesis-bridge.service

# Wait and verify
sleep 2
if systemctl is-active --quiet genesis-bridge.service; then
    ok "Bridge API service active"
    HEALTH=$(curl -s http://127.0.0.1:36200/health 2>/dev/null || echo "connecting...")
    log "Health: $HEALTH"
else
    warn "Bridge API service failed to start"
    journalctl -u genesis-bridge.service --no-pager -n 10
fi

# ─── Step 7: Create user config directory ────────────────────────────────

step "Step 7: Initializing user configuration"

mkdir -p /root/.genesis_appx/profiles
mkdir -p /root/.genesis_appx/logs

# Create default config
cat > /root/.genesis_appx/config.json << 'EOF'
{
  "version": "1.0.0",
  "app_name": "Genesis AppX",
  "bridge_port": 36200,
  "profiles_dir": "/root/.genesis_appx/profiles",
  "titan_root": "/opt/titan",
  "default_browser": "stealthfox",
  "default_archetype": "casual_shopper",
  "default_target": "amazon_us",
  "default_age_days": 90,
  "ai_enabled": true,
  "auto_forge": true,
  "theme": "dark"
}
EOF
ok "Config initialized"

# ─── Summary ─────────────────────────────────────────────────────────────

step "DEPLOYMENT COMPLETE"

echo ""
echo -e "${BOLD}Genesis AppX is ready!${NC}"
echo ""
echo "  Components installed:"
echo "    - ML6 Electron shell: $ML6_DIR/"
echo "    - Genesis Bridge API: $GENESIS_APPX_DIR/genesis_bridge_api.py"
echo "    - Patched app.asar:   $ML6_DIR/resources/app.asar"
echo "    - Desktop shortcut:   /usr/share/applications/genesis-appx.desktop"
echo "    - CLI command:        genesis-appx"
echo "    - Systemd service:    genesis-bridge.service"
echo ""
echo "  Directories:"
echo "    - Profiles:  /root/.genesis_appx/profiles/"
echo "    - Config:    /root/.genesis_appx/config.json"
echo "    - Logs:      /root/.genesis_appx/logs/"
echo ""
echo "  Launch:"
echo "    genesis-appx               # From terminal"
echo "    # Or click 'Genesis AppX' on desktop"
echo ""
echo "  Bridge API:"
echo "    http://127.0.0.1:36200/health"
echo "    http://127.0.0.1:36200/api/v1/genesis/targets"
echo "    http://127.0.0.1:36200/api/v1/genesis/archetypes"
echo ""
echo -e "${GREEN}Powered by Titan OS Genesis Engine${NC}"
