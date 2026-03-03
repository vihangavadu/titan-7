#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# Genesis AppX Launcher
# Starts the Genesis Bridge API + Modified Multilogin 6 Electron shell
# ═══════════════════════════════════════════════════════════════════════════

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
GENESIS_APPX_DIR="${GENESIS_APPX_DIR:-/opt/genesis-appx}"
ML6_DIR="${ML6_DIR:-/opt/Multilogin}"
BRIDGE_PORT="${GENESIS_BRIDGE_PORT:-36200}"
BRIDGE_PID=""
TITAN_ROOT="${TITAN_ROOT:-/opt/titan}"

export TITAN_ROOT
export GENESIS_BRIDGE_PORT="$BRIDGE_PORT"
export GENESIS_PROFILES_DIR="$HOME/.genesis_appx/profiles"
export GENESIS_CONFIG_DIR="$HOME/.genesis_appx"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log() { echo -e "${CYAN}[Genesis AppX]${NC} $1"; }
ok()  { echo -e "${GREEN}[OK]${NC} $1"; }
err() { echo -e "${RED}[ERROR]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

cleanup() {
    log "Shutting down..."
    if [ -n "$BRIDGE_PID" ] && kill -0 "$BRIDGE_PID" 2>/dev/null; then
        kill "$BRIDGE_PID" 2>/dev/null || true
        wait "$BRIDGE_PID" 2>/dev/null || true
        ok "Bridge API stopped"
    fi
}
trap cleanup EXIT INT TERM

# ─── Pre-flight checks ──────────────────────────────────────────────────

log "Genesis AppX v1.0 - Powered by Titan OS"
echo ""

# Check ML6 binary
if [ ! -f "$ML6_DIR/multilogin" ]; then
    err "Multilogin binary not found at $ML6_DIR/multilogin"
    err "Install Multilogin 6 first: dpkg -i multilogin.deb"
    exit 1
fi

# Check patched app.asar
if [ -f "$GENESIS_APPX_DIR/app.asar" ]; then
    # Use patched version
    if [ ! -L "$ML6_DIR/resources/app.asar.original" ] && [ ! -f "$ML6_DIR/resources/app.asar.original" ]; then
        log "Backing up original app.asar..."
        cp "$ML6_DIR/resources/app.asar" "$ML6_DIR/resources/app.asar.original"
    fi
    if ! cmp -s "$ML6_DIR/resources/app.asar" "$GENESIS_APPX_DIR/app.asar" 2>/dev/null; then
        log "Installing patched app.asar..."
        cp "$GENESIS_APPX_DIR/app.asar" "$ML6_DIR/resources/app.asar"
        ok "Patched app.asar installed"
    fi
else
    warn "No patched app.asar found at $GENESIS_APPX_DIR/app.asar"
    warn "Run: python3 patch_ml6_asar.py first"
fi

# Check Python + Flask
if ! command -v python3 &>/dev/null; then
    err "Python3 not found"
    exit 1
fi

python3 -c "import flask" 2>/dev/null || {
    log "Installing Flask..."
    pip3 install flask flask-cors -q
}

# Create directories
mkdir -p "$HOME/.genesis_appx/profiles"
mkdir -p "$HOME/.genesis_appx/logs"

# ─── Start Genesis Bridge API ────────────────────────────────────────────

log "Starting Genesis Bridge API on port $BRIDGE_PORT..."

BRIDGE_SCRIPT="$SCRIPT_DIR/genesis_bridge_api.py"
if [ ! -f "$BRIDGE_SCRIPT" ]; then
    BRIDGE_SCRIPT="$GENESIS_APPX_DIR/genesis_bridge_api.py"
fi

if [ ! -f "$BRIDGE_SCRIPT" ]; then
    err "genesis_bridge_api.py not found"
    exit 1
fi

python3 "$BRIDGE_SCRIPT" > "$HOME/.genesis_appx/logs/bridge.log" 2>&1 &
BRIDGE_PID=$!

# Wait for bridge to start
for i in $(seq 1 15); do
    if curl -s "http://127.0.0.1:$BRIDGE_PORT/health" >/dev/null 2>&1; then
        ok "Bridge API ready (PID: $BRIDGE_PID)"
        break
    fi
    sleep 0.5
done

if ! curl -s "http://127.0.0.1:$BRIDGE_PORT/health" >/dev/null 2>&1; then
    err "Bridge API failed to start. Check $HOME/.genesis_appx/logs/bridge.log"
    cat "$HOME/.genesis_appx/logs/bridge.log" | tail -20
    exit 1
fi

# Show status
HEALTH=$(curl -s "http://127.0.0.1:$BRIDGE_PORT/health")
log "Bridge status: $HEALTH"

# ─── Start Genesis AppX (Modified ML6 Electron) ─────────────────────────

log "Launching Genesis AppX..."
echo ""

# Set environment for Electron
export ELECTRON_DISABLE_SECURITY_WARNINGS=true

# V9.2 FIX: Auto-detect active X display and auth cookie
# Works whether launched from RDP session, SSH, or desktop shortcut
if [ -z "$DISPLAY" ]; then
    # Try to find active display from running Xorg
    for d in 10 1 0 2; do
        if [ -S "/tmp/.X11-unix/X${d}" ]; then
            export DISPLAY=":${d}"
            log "Auto-detected DISPLAY=:${d}"
            break
        fi
    done
    # Last resort
    export DISPLAY="${DISPLAY:-:10}"
fi

if [ -z "$XAUTHORITY" ] || [ ! -f "$XAUTHORITY" ]; then
    # Try common xauthority locations
    for xauth_path in "$HOME/.Xauthority" "/root/.Xauthority" "/var/run/xrdp/xauth_${DISPLAY#:}" "/tmp/.xauth_${DISPLAY#:}"; do
        if [ -f "$xauth_path" ]; then
            export XAUTHORITY="$xauth_path"
            log "Using XAUTHORITY: $xauth_path"
            break
        fi
    done
fi

log "Display: $DISPLAY | XAUTH: ${XAUTHORITY:-none}"

# V9.2 FIX: Software rendering for VPS (no GPU/DRI device)
# Fixes white/blank screen on headless VPS environments
export LIBGL_ALWAYS_SOFTWARE=1
export GALLIUM_DRIVER=llvmpipe
export MESA_GL_VERSION_OVERRIDE=4.5

# V9.2 FIX: Electron GPU flags for no-GPU VPS
ML6_FLAGS=(
    --no-sandbox
    --disable-gpu
    --disable-gpu-compositing
    --disable-software-rasterizer
    --disable-dev-shm-usage
    --disable-background-networking
    --no-first-run
    --in-process-gpu
)

# Launch ML6 with Genesis modifications
"$ML6_DIR/multilogin" "${ML6_FLAGS[@]}" "$@" &
ML6_PID=$!

ok "Genesis AppX launched (PID: $ML6_PID)"
log "Bridge API: http://127.0.0.1:$BRIDGE_PORT"
log "Health check: http://127.0.0.1:$BRIDGE_PORT/health"
echo ""

# Wait for ML6 to exit
wait "$ML6_PID" 2>/dev/null || true

log "Genesis AppX closed"
