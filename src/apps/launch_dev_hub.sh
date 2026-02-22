#!/bin/bash
# TITAN Development Hub Launcher

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# TITAN paths
TITAN_ROOT="/opt/titan"
DEV_HUB="$TITAN_ROOT/apps/titan_dev_hub.py"
CONFIG_DIR="$TITAN_ROOT/config"
SESSIONS_DIR="$TITAN_ROOT/sessions"

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}           TITAN OS Development Hub - Launcher${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo

# Check if running as root for system-wide features
if [[ $EUID -eq 0 ]]; then
    echo -e "${YELLOW}Running as root - full system integration available${NC}"
    SYSTEM_MODE=true
else
    echo -e "${YELLOW}Running in user mode - limited features${NC}"
    SYSTEM_MODE=false
fi

# Create necessary directories
mkdir -p "$SESSIONS_DIR"
mkdir -p "$CONFIG_DIR"

# Check Python installation
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is required but not installed${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo -e "${GREEN}Python version: $PYTHON_VERSION${NC}"

# Check if Dev Hub exists
if [[ ! -f "$DEV_HUB" ]]; then
    echo -e "${RED}Error: TITAN Dev Hub not found at $DEV_HUB${NC}"
    exit 1
fi

# Install dependencies if needed
echo -e "${YELLOW}Checking dependencies...${NC}"
if [[ -f "$TITAN_ROOT/apps/requirements.txt" ]]; then
    python3 -m pip install -r "$TITAN_ROOT/apps/requirements.txt" --user --quiet
    echo -e "${GREEN}Dependencies checked${NC}"
fi

# Check for display (GUI)
if command -v xhost &> /dev/null; then
    GUI_AVAILABLE=true
    echo -e "${GREEN}GUI mode available${NC}"
else
    GUI_AVAILABLE=false
    echo -e "${YELLOW}GUI not available - will run in CLI mode${NC}"
fi

# Set environment variables
export PYTHONPATH="$TITAN_ROOT/core:$PYTHONPATH"
export TITAN_ROOT="$TITAN_ROOT"
export TITAN_DEV_MODE="true"

# Check for Git repo
if [[ -d "$TITAN_ROOT/.git" ]]; then
    echo -e "${GREEN}Git repository detected${NC}"
    cd "$TITAN_ROOT"
    
    # Show current branch and status
    BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
    echo -e "${BLUE}Current branch: $BRANCH${NC}"
    
    # Check for uncommitted changes
    if ! git diff --quiet || ! git diff --cached --quiet; then
        echo -e "${YELLOW}Warning: Uncommitted changes detected${NC}"
    fi
else
    echo -e "${YELLOW}Not a Git repository - version control limited${NC}"
fi

# Parse command line arguments
MODE="gui"
DEBUG=false
SESSION_ID=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --cli)
            MODE="cli"
            shift
            ;;
        --gui)
            MODE="gui"
            shift
            ;;
        --debug)
            DEBUG=true
            shift
            ;;
        --session)
            SESSION_ID="$2"
            shift 2
            ;;
        --help|-h)
            echo "TITAN Development Hub Launcher"
            echo
            echo "Usage: $0 [OPTIONS]"
            echo
            echo "Options:"
            echo "  --cli      Force CLI mode"
            echo "  --gui      Force GUI mode (default)"
            echo "  --debug    Enable debug logging"
            echo "  --session  Load specific session"
            echo "  --help     Show this help"
            echo
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Debug mode setup
if [[ "$DEBUG" == "true" ]]; then
    export TITAN_DEBUG="true"
    echo -e "${YELLOW}Debug mode enabled${NC}"
fi

# Launch the application
echo
echo -e "${GREEN}Launching TITAN Development Hub...${NC}"
echo -e "${BLUE}Mode: $MODE${NC}"

if [[ "$MODE" == "gui" && "$GUI_AVAILABLE" == "true" ]]; then
    # GUI mode
    echo -e "${GREEN}Starting GUI interface...${NC}"
    python3 "$DEV_HUB" --gui
elif [[ "$MODE" == "cli" || "$GUI_AVAILABLE" == "false" ]]; then
    # CLI mode
    echo -e "${GREEN}Starting CLI interface...${NC}"
    python3 "$DEV_HUB" --cli
else
    echo -e "${RED}Failed to start - no GUI available${NC}"
    exit 1
fi

# Check exit status
if [[ $? -eq 0 ]]; then
    echo
    echo -e "${GREEN}Session completed successfully${NC}"
    
    # Show session info
    LATEST_SESSION=$(ls -t "$SESSIONS_DIR"/*.json 2>/dev/null | head -1)
    if [[ -n "$LATEST_SESSION" ]]; then
        echo -e "${BLUE}Session saved: $(basename "$LATEST_SESSION")${NC}"
    fi
else
    echo -e "${RED}Session ended with errors${NC}"
    exit 1
fi

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
