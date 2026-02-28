#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# CERBERUS AppX LAUNCHER
# Starts Cerberus Bridge API + Desktop GUI
# ═══════════════════════════════════════════════════════════════════════════════

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TITAN_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BRIDGE_PID=""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

cleanup() {
    echo -e "${YELLOW}[CERBERUS] Shutting down...${NC}"
    if [ -n "$BRIDGE_PID" ] && kill -0 "$BRIDGE_PID" 2>/dev/null; then
        kill "$BRIDGE_PID"
        echo -e "${GREEN}[CERBERUS] Bridge API stopped${NC}"
    fi
    exit 0
}
trap cleanup EXIT INT TERM

echo -e "${RED}╔══════════════════════════════════════╗${NC}"
echo -e "${RED}║      CERBERUS AppX v9.2              ║${NC}"
echo -e "${RED}║  Zero-Touch Card Validation          ║${NC}"
echo -e "${RED}╚══════════════════════════════════════╝${NC}"

# Check Python
if ! command -v python3 &>/dev/null; then
    echo -e "${RED}[ERROR] python3 not found${NC}"
    exit 1
fi

# Check PyQt6
python3 -c "import PyQt6" 2>/dev/null || {
    echo -e "${YELLOW}[WARN] PyQt6 not installed. Install: pip install PyQt6${NC}"
}

# Start Bridge API in background
echo -e "${GREEN}[CERBERUS] Starting Bridge API on port 36300...${NC}"
export PYTHONPATH="$TITAN_ROOT/src/core:$TITAN_ROOT/src/apps:$PYTHONPATH"

python3 "$SCRIPT_DIR/cerberus_bridge_api.py" &
BRIDGE_PID=$!

sleep 2

# Verify Bridge API
if curl -s http://127.0.0.1:36300/api/v1/health | grep -q '"ok"'; then
    echo -e "${GREEN}[CERBERUS] Bridge API running (PID: $BRIDGE_PID)${NC}"
else
    echo -e "${YELLOW}[WARN] Bridge API may not have started correctly${NC}"
fi

# Launch Desktop GUI
echo -e "${GREEN}[CERBERUS] Launching Cerberus AppX GUI...${NC}"
python3 "$TITAN_ROOT/src/apps/app_cerberus.py"

echo -e "${GREEN}[CERBERUS] Cerberus AppX closed${NC}"
