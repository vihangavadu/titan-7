#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# KYC AppX LAUNCHER
# Starts KYC Bridge API + Waydroid + Virtual Camera + Desktop GUI
# ═══════════════════════════════════════════════════════════════════════════════

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TITAN_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BRIDGE_PID=""
WAYDROID_STARTED=0

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

cleanup() {
    echo -e "${YELLOW}[KYC] Shutting down...${NC}"
    if [ -n "$BRIDGE_PID" ] && kill -0 "$BRIDGE_PID" 2>/dev/null; then
        kill "$BRIDGE_PID"
        echo -e "${GREEN}[KYC] Bridge API stopped${NC}"
    fi
    if [ "$WAYDROID_STARTED" -eq 1 ]; then
        waydroid session stop 2>/dev/null || true
        echo -e "${GREEN}[KYC] Waydroid session stopped${NC}"
    fi
    # Unload v4l2loopback if we loaded it
    # (commented out — leave loaded for other apps)
    # modprobe -r v4l2loopback 2>/dev/null || true
    exit 0
}
trap cleanup EXIT INT TERM

echo -e "${CYAN}╔══════════════════════════════════════╗${NC}"
echo -e "${CYAN}║      KYC AppX v9.2                   ║${NC}"
echo -e "${CYAN}║  Identity Verification + Waydroid     ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════╝${NC}"

# Check Python
if ! command -v python3 &>/dev/null; then
    echo -e "${RED}[ERROR] python3 not found${NC}"
    exit 1
fi

# ─── Set up virtual camera (v4l2loopback) ─────────────────────────────────
echo -e "${CYAN}[KYC] Setting up virtual camera...${NC}"
if ! lsmod | grep -q v4l2loopback; then
    modprobe v4l2loopback devices=1 video_nr=2 \
        card_label="Integrated Webcam" exclusive_caps=1 2>/dev/null && {
        echo -e "${GREEN}[KYC] Virtual camera loaded (/dev/video2)${NC}"
    } || {
        echo -e "${YELLOW}[WARN] v4l2loopback not available — camera injection disabled${NC}"
    }
else
    echo -e "${GREEN}[KYC] Virtual camera already loaded${NC}"
fi

# ─── Start Waydroid if available ──────────────────────────────────────────
echo -e "${CYAN}[KYC] Checking Waydroid...${NC}"
if command -v waydroid &>/dev/null; then
    WAYDROID_STATUS=$(waydroid status 2>/dev/null | grep -i "session" | head -1 || echo "UNKNOWN")
    if echo "$WAYDROID_STATUS" | grep -qi "running"; then
        echo -e "${GREEN}[KYC] Waydroid session already running${NC}"
    else
        echo -e "${CYAN}[KYC] Starting Waydroid session...${NC}"
        waydroid session start &>/dev/null &
        WAYDROID_STARTED=1
        sleep 3
        echo -e "${GREEN}[KYC] Waydroid session started${NC}"
    fi
else
    echo -e "${YELLOW}[WARN] Waydroid not installed — Android features disabled${NC}"
fi

# ─── Start Bridge API in background ───────────────────────────────────────
echo -e "${CYAN}[KYC] Starting Bridge API on port 36400...${NC}"
export PYTHONPATH="$TITAN_ROOT/src/core:$TITAN_ROOT/src/apps:$TITAN_ROOT/src/android:$PYTHONPATH"

python3 "$SCRIPT_DIR/kyc_bridge_api.py" &
BRIDGE_PID=$!

sleep 2

# Verify Bridge API
if curl -s http://127.0.0.1:36400/api/v1/health 2>/dev/null | grep -q '"ok"'; then
    echo -e "${GREEN}[KYC] Bridge API running (PID: $BRIDGE_PID)${NC}"
else
    echo -e "${YELLOW}[WARN] Bridge API may not have started correctly${NC}"
fi

# ─── Show status ──────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}KYC AppX Ready:${NC}"
echo -e "  Bridge API:  http://127.0.0.1:36400/api/v1/status"
echo -e "  Camera:      $([ -c /dev/video2 ] && echo '/dev/video2 ready' || echo 'not available')"
echo -e "  Waydroid:    $(command -v waydroid &>/dev/null && echo 'available' || echo 'not installed')"
echo ""

# ─── Launch Desktop GUI ──────────────────────────────────────────────────
if [ "${1}" = "--headless" ] || [ "${1}" = "-H" ]; then
    echo -e "${CYAN}[KYC] Running in headless mode — Bridge API only${NC}"
    echo -e "${CYAN}[KYC] Press Ctrl+C to stop${NC}"
    wait "$BRIDGE_PID"
else
    echo -e "${GREEN}[KYC] Launching KYC AppX GUI...${NC}"
    python3 "$TITAN_ROOT/src/apps/app_kyc.py" 2>/dev/null || {
        echo -e "${YELLOW}[KYC] GUI launch failed (headless?) — running in API-only mode${NC}"
        echo -e "${CYAN}[KYC] Press Ctrl+C to stop${NC}"
        wait "$BRIDGE_PID"
    }
fi

echo -e "${GREEN}[KYC] KYC AppX closed${NC}"
