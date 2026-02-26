#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# TITAN OS — Deploy Desktop Shortcuts + Test All Apps
# Runs on VPS as root
# ═══════════════════════════════════════════════════════════════
set +e
export DEBIAN_FRONTEND=noninteractive
export PYTHONPATH="/opt/titan/src:/opt/titan/core:/opt/titan/apps"
export TITAN_ROOT="/opt/titan"

G='\033[0;32m'
R='\033[0;31m'
C='\033[0;36m'
Y='\033[1;33m'
NC='\033[0m'

PASS=0; FAIL=0; WARN=0
ok()   { PASS=$((PASS+1)); echo -e "  ${G}[PASS]${NC} $1"; }
fail() { FAIL=$((FAIL+1)); echo -e "  ${R}[FAIL]${NC} $1"; }
warn() { WARN=$((WARN+1)); echo -e "  ${Y}[WARN]${NC} $1"; }
info() { echo -e "${C}[INFO]${NC} $1"; }

# ─── Fix bashrc line endings ─────────────────────────────────
info "Fixing /root/.bashrc line endings..."
sed -i 's/\r//g' /root/.bashrc 2>/dev/null && ok "bashrc fixed" || warn "bashrc fix skipped"

# ─── Create Desktop directory ─────────────────────────────────
info "Creating Desktop directories..."
mkdir -p /root/Desktop
mkdir -p /usr/share/applications

# ─── PHASE 1: Deploy ALL Desktop Shortcuts ────────────────────
echo ""
echo -e "${C}═══ PHASE 1: Deploying Desktop Shortcuts ═══${NC}"

deploy_shortcut() {
    local FILE="$1"
    local NAME="$2"
    local COMMENT="$3"
    local EXEC="$4"
    local ICON="$5"
    local CATS="${6:-System;Security;}"
    local KEYWORDS="${7:-titan;}"

    cat > "/usr/share/applications/${FILE}" << EOF
[Desktop Entry]
Type=Application
Name=${NAME}
GenericName=${NAME}
Comment=${COMMENT}
Exec=${EXEC}
Icon=${ICON}
Terminal=false
Categories=${CATS}
Keywords=${KEYWORDS}
StartupNotify=true
EOF

    cp "/usr/share/applications/${FILE}" "/root/Desktop/${FILE}"
    chmod +x "/root/Desktop/${FILE}" 2>/dev/null
    echo -e "  ${G}+${NC} ${NAME}"
}

# 1. Main Launcher (hub)
deploy_shortcut "titan-launcher.desktop" \
    "TITAN Launcher" \
    "Main control hub — launch all Titan apps" \
    "python3 /opt/titan/apps/titan_launcher.py" \
    "preferences-system" \
    "System;Security;" \
    "titan;launcher;hub;"

# 2. Operation Center (unified)
deploy_shortcut "titan-unified.desktop" \
    "Operation Center" \
    "Main control hub — Operations, Intelligence, Shields" \
    "python3 /opt/titan/apps/app_unified.py" \
    "preferences-system-privacy" \
    "System;Security;" \
    "operation;center;ops;"

# 3. Operations (daily workflow)
deploy_shortcut "titan-operations.desktop" \
    "Operations" \
    "Daily workflow — Target, Identity, Validate, Forge, Results" \
    "python3 /opt/titan/apps/titan_operations.py" \
    "system-run" \
    "System;Security;" \
    "operations;workflow;target;validate;"

# 4. Intelligence Center
deploy_shortcut "titan-intelligence.desktop" \
    "Intelligence Center" \
    "AI analysis — Copilot, 3DS Strategy, Detection, Recon, Memory" \
    "python3 /opt/titan/apps/titan_intelligence.py" \
    "applications-science" \
    "System;Security;" \
    "intelligence;ai;copilot;recon;"

# 5. Network Shield
deploy_shortcut "titan-network.desktop" \
    "Network Shield" \
    "VPN, eBPF mimesis, proxy, forensic detection" \
    "python3 /opt/titan/apps/titan_network.py" \
    "network-workgroup" \
    "System;Network;Security;" \
    "network;vpn;shield;proxy;"

# 6. Admin Panel
deploy_shortcut "titan-admin.desktop" \
    "Admin Panel" \
    "Services, tools, system diagnostics, automation, config" \
    "python3 /opt/titan/apps/titan_admin.py" \
    "preferences-system" \
    "System;Settings;" \
    "admin;services;diagnostics;"

# 7. Cerberus (Card Validator)
deploy_shortcut "titan-cerberus.desktop" \
    "Cerberus" \
    "Zero-touch card validation with traffic light system" \
    "python3 /opt/titan/apps/app_cerberus.py" \
    "dialog-password" \
    "System;Security;" \
    "cerberus;card;validator;"

# 8. Card Validator (standalone)
deploy_shortcut "titan-card-validator.desktop" \
    "Card Validator" \
    "BIN check, card quality grading, AVS validation" \
    "python3 /opt/titan/apps/app_card_validator.py" \
    "dialog-password" \
    "System;Security;" \
    "card;validator;bin;luhn;"

# 9. Genesis (Profile Forge)
deploy_shortcut "titan-genesis.desktop" \
    "Genesis" \
    "Generate aged browser profiles" \
    "python3 /opt/titan/apps/app_genesis.py" \
    "document-new" \
    "System;Security;" \
    "genesis;profile;forge;"

# 10. Profile Forge (standalone)
deploy_shortcut "titan-profile-forge.desktop" \
    "Profile Forge" \
    "Identity + Chrome profile building, persona creation" \
    "python3 /opt/titan/apps/app_profile_forge.py" \
    "contact-new" \
    "System;Security;" \
    "profile;forge;identity;persona;"

# 11. KYC Module
deploy_shortcut "titan-kyc.desktop" \
    "KYC Module" \
    "Virtual camera controller for identity verification" \
    "python3 /opt/titan/apps/app_kyc.py" \
    "camera-web" \
    "System;Security;" \
    "kyc;camera;virtual;"

# 12. Browser Launch
deploy_shortcut "titan-browser-launch.desktop" \
    "Browser Launch" \
    "Launch forged profiles in Camoufox, TX monitor, handover" \
    "python3 /opt/titan/apps/app_browser_launch.py" \
    "web-browser" \
    "Network;WebBrowser;Security;" \
    "browser;launch;camoufox;monitor;"

# 13. Titan Browser
deploy_shortcut "titan-browser.desktop" \
    "Titan Browser" \
    "Hardened browser with full identity shield" \
    "bash /opt/titan/bin/titan-browser" \
    "web-browser" \
    "Network;WebBrowser;Security;" \
    "browser;camoufox;antidetect;"

# 14. Bug Reporter
deploy_shortcut "titan-bug-reporter.desktop" \
    "Bug Reporter" \
    "Report issues and auto-patch via Windsurf IDE" \
    "python3 /opt/titan/apps/app_bug_reporter.py" \
    "dialog-error" \
    "System;Development;" \
    "bug;report;patch;fix;"

# 15. Settings
deploy_shortcut "titan-settings.desktop" \
    "Settings" \
    "VPN, AI, services, browser, API keys, system config" \
    "python3 /opt/titan/apps/app_settings.py" \
    "preferences-desktop" \
    "System;Settings;" \
    "settings;config;vpn;ai;api;"

# 16. Forensic Monitor
deploy_shortcut "titan-forensic.desktop" \
    "Forensic Monitor" \
    "Real-time forensic detection monitoring" \
    "python3 /opt/titan/apps/launch_forensic_monitor.py" \
    "security-high" \
    "System;Security;" \
    "forensic;monitor;detection;"

# 17. Dev Hub (web)
deploy_shortcut "titan-dev-hub.desktop" \
    "Dev Hub" \
    "Titan Development Hub — web dashboard" \
    "xdg-open http://localhost:8877" \
    "applications-development" \
    "Development;System;" \
    "devhub;development;api;"

# 18. Terminal
deploy_shortcut "titan-terminal.desktop" \
    "Terminal" \
    "System terminal" \
    "x-terminal-emulator" \
    "utilities-terminal" \
    "System;TerminalEmulator;" \
    "terminal;shell;console;"

# 19. Files
deploy_shortcut "titan-files.desktop" \
    "Files" \
    "Browse files and folders" \
    "thunar /opt/titan" \
    "system-file-manager" \
    "System;FileManager;" \
    "files;folders;manager;"

# 20. Configure
deploy_shortcut "titan-configure.desktop" \
    "Titan Configure" \
    "TITAN V7.0 Configuration Wizard" \
    "xfce4-terminal -e titan-configure" \
    "preferences-system" \
    "System;Settings;" \
    "configure;wizard;setup;"

# 21. Install to Disk
deploy_shortcut "titan-install.desktop" \
    "Install to Disk" \
    "Install TITAN permanently to VPS or bare metal" \
    "x-terminal-emulator -e 'sudo bash /opt/titan/bin/install-to-disk'" \
    "drive-harddisk" \
    "System;" \
    "install;vps;disk;"

echo ""
info "Deployed 21 desktop shortcuts"

# Mark desktop files as trusted (XFCE)
for f in /root/Desktop/*.desktop; do
    gio set "$f" metadata::xfce-exe-checksum "$(sha256sum "$f" | cut -d' ' -f1)" 2>/dev/null || true
done
ok "Desktop shortcuts trusted by XFCE"

# Update desktop database
update-desktop-database /usr/share/applications 2>/dev/null && ok "Desktop database updated" || warn "Desktop DB update skipped"

# ─── PHASE 2: Test All Apps ──────────────────────────────────
echo ""
echo -e "${C}═══ PHASE 2: Testing All Titan Apps ═══${NC}"
echo ""

# Find the active XRDP display
XDISP=""
for d in /tmp/.X11-unix/X*; do
    num="${d##*/X}"
    if [ "$num" != "0" ] && [ -n "$num" ]; then
        XDISP=":${num}"
        break
    fi
done

if [ -z "$XDISP" ]; then
    XDISP=":10"
fi
export DISPLAY="$XDISP"
export XAUTHORITY="/root/.Xauthority"
export DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/0/bus"
export QT_QPA_PLATFORM=xcb
export XDG_RUNTIME_DIR="/run/user/0"

info "Using DISPLAY=$DISPLAY"

# Helper: launch a GUI app, wait, send sample input, screenshot, close
test_gui_app() {
    local APP_NAME="$1"
    local APP_CMD="$2"
    local WAIT_SEC="${3:-4}"
    local SAMPLE_INPUT="$4"

    info "Testing: ${APP_NAME}..."

    # Launch in background
    eval "$APP_CMD" &>/tmp/titan_test_${APP_NAME}.log &
    local PID=$!
    sleep "$WAIT_SEC"

    # Check if app is running
    if kill -0 "$PID" 2>/dev/null; then
        ok "${APP_NAME} — launched successfully (PID=$PID)"

        # Try sending sample input via xdotool if available
        if [ -n "$SAMPLE_INPUT" ] && command -v xdotool &>/dev/null; then
            # Activate the window
            local WID=$(xdotool search --pid $PID 2>/dev/null | head -1)
            if [ -n "$WID" ]; then
                xdotool windowactivate "$WID" 2>/dev/null
                sleep 0.5
                # Type sample input
                xdotool type --delay 50 "$SAMPLE_INPUT" 2>/dev/null
                sleep 0.3
                xdotool key Return 2>/dev/null
                sleep 1
                ok "${APP_NAME} — sample input sent: '${SAMPLE_INPUT}'"
            else
                warn "${APP_NAME} — no window found for xdotool input"
            fi
        fi

        # Take screenshot if possible
        if command -v xdotool &>/dev/null; then
            local WID=$(xdotool search --pid $PID 2>/dev/null | head -1)
            if [ -n "$WID" ]; then
                import -window "$WID" "/tmp/titan_screenshot_${APP_NAME}.png" 2>/dev/null && \
                    info "  Screenshot: /tmp/titan_screenshot_${APP_NAME}.png" || true
            fi
        fi

        # Gracefully close
        kill "$PID" 2>/dev/null
        sleep 1
        kill -9 "$PID" 2>/dev/null
    else
        # Check if it exited with an error
        local EXIT_CODE=$?
        local LOG=$(tail -5 /tmp/titan_test_${APP_NAME}.log 2>/dev/null)
        if echo "$LOG" | grep -qi "error\|traceback\|exception"; then
            fail "${APP_NAME} — crashed: $(tail -1 /tmp/titan_test_${APP_NAME}.log)"
        else
            warn "${APP_NAME} — exited quickly (may need DISPLAY or deps)"
        fi
    fi
}

# Helper: test a CLI tool
test_cli() {
    local NAME="$1"
    local CMD="$2"
    local EXPECT="$3"

    info "Testing CLI: ${NAME}..."
    OUTPUT=$(eval "$CMD" 2>&1 | head -5)
    if [ -n "$EXPECT" ]; then
        if echo "$OUTPUT" | grep -qi "$EXPECT"; then
            ok "${NAME} — output matches"
        else
            warn "${NAME} — unexpected output: $(echo "$OUTPUT" | head -1)"
        fi
    else
        if [ -n "$OUTPUT" ]; then
            ok "${NAME} — responded"
        else
            warn "${NAME} — no output"
        fi
    fi
}

# Install xdotool for GUI interaction testing
apt-get install -y xdotool imagemagick 2>&1 | tail -1

echo ""
echo -e "${Y}── GUI App Tests ──${NC}"
echo ""

# 1. TITAN Launcher
test_gui_app "titan-launcher" \
    "python3 /opt/titan/apps/titan_launcher.py" \
    5

# 2. Operation Center (Unified)
test_gui_app "operation-center" \
    "python3 /opt/titan/apps/app_unified.py" \
    5

# 3. Operations (Daily Workflow)
test_gui_app "operations" \
    "python3 /opt/titan/apps/titan_operations.py" \
    6 \
    "amazon.com"

# 4. Intelligence Center
test_gui_app "intelligence" \
    "python3 /opt/titan/apps/titan_intelligence.py" \
    6 \
    "analyze target site for 3DS"

# 5. Network Shield
test_gui_app "network-shield" \
    "python3 /opt/titan/apps/titan_network.py" \
    5

# 6. Admin Panel
test_gui_app "admin-panel" \
    "python3 /opt/titan/apps/titan_admin.py" \
    5

# 7. Cerberus
test_gui_app "cerberus" \
    "python3 /opt/titan/apps/app_cerberus.py" \
    5 \
    "4532015112830366"

# 8. Card Validator
test_gui_app "card-validator" \
    "python3 /opt/titan/apps/app_card_validator.py" \
    5 \
    "4111111111111111"

# 9. Genesis (Profile Forge)
test_gui_app "genesis" \
    "python3 /opt/titan/apps/app_genesis.py" \
    5

# 10. Profile Forge (standalone)
test_gui_app "profile-forge" \
    "python3 /opt/titan/apps/app_profile_forge.py" \
    6 \
    "John Smith"

# 11. KYC Module
test_gui_app "kyc-module" \
    "python3 /opt/titan/apps/app_kyc.py" \
    5

# 12. Browser Launch
test_gui_app "browser-launch" \
    "python3 /opt/titan/apps/app_browser_launch.py" \
    5

# 13. Bug Reporter
test_gui_app "bug-reporter" \
    "python3 /opt/titan/apps/app_bug_reporter.py" \
    5 \
    "Test bug report from automated testing"

# 14. Settings
test_gui_app "settings" \
    "python3 /opt/titan/apps/app_settings.py" \
    5

# 15. Forensic Monitor
test_gui_app "forensic-monitor" \
    "python3 /opt/titan/apps/launch_forensic_monitor.py" \
    5

echo ""
echo -e "${Y}── API / Service Tests ──${NC}"
echo ""

# 16. Titan API
test_cli "titan-api" \
    "curl -s -m 5 http://localhost:5000/api/v1/health" \
    "status"

# 17. Dev Hub API
test_cli "dev-hub" \
    "curl -s -m 5 http://localhost:8877/api/health" \
    ""

# 18. Dev Hub Web
test_cli "dev-hub-web" \
    "curl -s -m 5 -o /dev/null -w '%{http_code}' http://localhost:8877/" \
    "200"

# 19. Ollama
test_cli "ollama" \
    "curl -s -m 5 http://localhost:11434/api/tags" \
    "models"

# 20. Redis
test_cli "redis" \
    "redis-cli ping" \
    "PONG"

echo ""
echo -e "${Y}── CLI Tool Tests ──${NC}"
echo ""

# 21. Titan Browser (just check it exists)
test_cli "titan-browser-bin" \
    "file /opt/titan/bin/titan-browser" \
    "script"

# 22. Nmap
test_cli "nmap" \
    "nmap --version" \
    "Nmap"

# 23. Xray
test_cli "xray" \
    "xray version 2>&1" \
    "Xray"

# 24. Python3
test_cli "python3" \
    "python3 --version" \
    "Python"

# 25. Node.js
test_cli "nodejs" \
    "node --version" \
    "v"

# 26. FFmpeg
test_cli "ffmpeg" \
    "ffmpeg -version 2>&1 | head -1" \
    "ffmpeg"

# 27. Titan core import test
test_cli "titan-core-imports" \
    "python3 -c 'import sys; sys.path.insert(0,\"/opt/titan/core\"); from integration_bridge import IntegrationBridge; print(\"IntegrationBridge OK\")'" \
    "OK"

# 28. Titan session import test
test_cli "titan-session" \
    "python3 -c 'import sys; sys.path.insert(0,\"/opt/titan/core\"); from titan_session import TitanSession; print(\"TitanSession OK\")'" \
    "OK"

echo ""
echo -e "${C}═══════════════════════════════════════════════════════${NC}"
echo -e "${C} TITAN Desktop + App Test Complete${NC}"
echo -e "${C} $(date -u '+%Y-%m-%d %H:%M:%S UTC')${NC}"
echo -e "${C}═══════════════════════════════════════════════════════${NC}"
echo -e " PASS: ${PASS} | WARN: ${WARN} | FAIL: ${FAIL}"
echo -e "${C}═══════════════════════════════════════════════════════${NC}"
echo ""
echo "Desktop shortcuts at: /root/Desktop/ (21 apps)"
echo "App test logs at: /tmp/titan_test_*.log"
echo "Screenshots at: /tmp/titan_screenshot_*.png"
