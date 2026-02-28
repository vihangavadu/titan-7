#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# CERBERUS AppX DEPLOYMENT SCRIPT
# Deploys Cerberus AppX to /opt/titan with systemd service
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

echo -e "${RED}╔══════════════════════════════════════════╗${NC}"
echo -e "${RED}║   CERBERUS AppX DEPLOYMENT v9.2          ║${NC}"
echo -e "${RED}╚══════════════════════════════════════════╝${NC}"

# Must be root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}[ERROR] Must run as root${NC}"
    exit 1
fi

# ─── Install Python dependencies ──────────────────────────────────────────
echo -e "${CYAN}[1/5] Installing dependencies...${NC}"
pip3 install flask flask-cors aiohttp PyQt6 2>/dev/null || {
    echo -e "${YELLOW}[WARN] Some pip packages may have failed — check manually${NC}"
}

# ─── Deploy app_cerberus.py ───────────────────────────────────────────────
echo -e "${CYAN}[2/5] Deploying Cerberus AppX GUI...${NC}"
cp -v "$TITAN_ROOT/src/apps/app_cerberus.py" "$INSTALL_DIR/apps/app_cerberus.py"
chmod +x "$INSTALL_DIR/apps/app_cerberus.py"

# ─── Deploy Bridge API ────────────────────────────────────────────────────
echo -e "${CYAN}[3/5] Deploying Cerberus Bridge API...${NC}"
mkdir -p "$INSTALL_DIR/tools/cerberus_appx"
cp -v "$SCRIPT_DIR/cerberus_bridge_api.py" "$INSTALL_DIR/tools/cerberus_appx/cerberus_bridge_api.py"
cp -v "$SCRIPT_DIR/launch_cerberus_appx.sh" "$INSTALL_DIR/tools/cerberus_appx/launch_cerberus_appx.sh"
chmod +x "$INSTALL_DIR/tools/cerberus_appx/"*.sh

# ─── Create systemd service ──────────────────────────────────────────────
echo -e "${CYAN}[4/5] Creating systemd service...${NC}"
cat > /etc/systemd/system/cerberus-bridge.service << 'SYSTEMD_EOF'
[Unit]
Description=Cerberus Bridge API — Card Validation Engine
After=network.target redis-server.service
Wants=redis-server.service

[Service]
Type=simple
User=root
Environment=PYTHONPATH=/opt/titan:/opt/titan/core:/opt/titan/apps
Environment=CERBERUS_BRIDGE_PORT=36300
Environment=CERBERUS_BRIDGE_HOST=127.0.0.1
ExecStart=/usr/bin/python3 /opt/titan/tools/cerberus_appx/cerberus_bridge_api.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SYSTEMD_EOF

systemctl daemon-reload
systemctl enable cerberus-bridge.service
systemctl restart cerberus-bridge.service

sleep 2
if systemctl is-active --quiet cerberus-bridge.service; then
    echo -e "${GREEN}[OK] cerberus-bridge.service is active${NC}"
else
    echo -e "${YELLOW}[WARN] cerberus-bridge.service may not have started — check: journalctl -u cerberus-bridge${NC}"
fi

# ─── Create desktop entry + CLI command ───────────────────────────────────
echo -e "${CYAN}[5/5] Creating desktop entry and CLI...${NC}"

cat > /usr/share/applications/cerberus-appx.desktop << 'DESKTOP_EOF'
[Desktop Entry]
Name=Cerberus AppX
Comment=Zero-Touch Card Validation Intelligence
Exec=/usr/bin/python3 /opt/titan/apps/app_cerberus.py
Icon=security-high
Terminal=false
Type=Application
Categories=Utility;Security;
DESKTOP_EOF

cat > /usr/local/bin/cerberus-appx << 'CLI_EOF'
#!/bin/bash
export PYTHONPATH="/opt/titan:/opt/titan/core:/opt/titan/apps"
python3 /opt/titan/apps/app_cerberus.py "$@"
CLI_EOF
chmod +x /usr/local/bin/cerberus-appx

# ─── Verify ──────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo -e "${GREEN}  CERBERUS AppX DEPLOYMENT COMPLETE${NC}"
echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo -e "  Bridge API:  http://127.0.0.1:36300/api/v1/health"
echo -e "  Desktop:     cerberus-appx"
echo -e "  Service:     systemctl status cerberus-bridge"
echo -e "  Logs:        journalctl -u cerberus-bridge -f"
echo ""

# Quick health check
curl -s http://127.0.0.1:36300/api/v1/status 2>/dev/null | python3 -m json.tool 2>/dev/null || true
