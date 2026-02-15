#!/bin/bash
# =============================================================================
# TITAN V7.0 Backend Init — Kernel Shield + Profile Loader
# =============================================================================
# Called by lucid-titan.service at boot (before GUI session starts)
# Loads kernel modules and prepares the identity synthesis environment.
# The GUI (app_unified.py) launches separately via XDG autostart.
# =============================================================================

set -u

TITAN_HOME="/opt/lucid-empire"
LOG_TAG="TITAN-INIT"

log() { echo "[$LOG_TAG] $*"; logger -t "$LOG_TAG" "$*"; }
warn() { echo "[$LOG_TAG] WARNING: $*"; logger -t "$LOG_TAG" -p user.warning "$*"; }

log "=== TITAN V7.0 Backend Initialization ==="

# ── 1. Load Hardware Shield kernel module ─────────────────────────────────────
TITAN_KO="$TITAN_HOME/kernel-modules/titan_hw.ko"
if lsmod | grep -q titan_hw; then
    log "Hardware Shield already loaded"
elif [ -f "$TITAN_KO" ]; then
    log "Loading Hardware Shield (titan_hw.ko)..."
    if insmod "$TITAN_KO"; then
        log "Hardware Shield: ACTIVE"
    else
        warn "Hardware Shield: FAILED to load (insmod error)"
    fi
else
    warn "Hardware Shield: titan_hw.ko not found at $TITAN_KO"
    # Try DKMS-installed module
    if modprobe titan_hw 2>/dev/null; then
        log "Hardware Shield: ACTIVE (via DKMS)"
    else
        warn "Hardware Shield: NOT AVAILABLE"
    fi
fi

# ── 2. Load Synthetic Battery module ──────────────────────────────────────────
BATTERY_KO="$TITAN_HOME/kernel-modules/titan_battery.ko"
if lsmod | grep -q titan_battery; then
    log "Battery Shield already loaded"
elif [ -f "$BATTERY_KO" ]; then
    log "Loading Battery Shield (titan_battery.ko)..."
    if insmod "$BATTERY_KO"; then
        log "Battery Shield: ACTIVE"
    else
        warn "Battery Shield: FAILED to load"
    fi
else
    if modprobe titan_battery 2>/dev/null; then
        log "Battery Shield: ACTIVE (via DKMS)"
    else
        log "Battery Shield: not available (optional for desktop personas)"
    fi
fi

# ── 3. Load v4l2loopback (Virtual Camera for KYC) ────────────────────────────
if lsmod | grep -q v4l2loopback; then
    log "v4l2loopback already loaded"
else
    log "Loading v4l2loopback (Virtual Camera)..."
    if modprobe v4l2loopback devices=1 video_nr=2 card_label="Integrated Camera" exclusive_caps=1 2>/dev/null; then
        log "Virtual Camera: ACTIVE (/dev/video2)"
    else
        warn "v4l2loopback: not available (install v4l2loopback-dkms)"
    fi
fi

# ── 4. Create runtime directories ────────────────────────────────────────────
mkdir -p /run/lucid-empire
mkdir -p /tmp/lucid-empire/{cache,kyc_output}
chmod 777 /tmp/lucid-empire /tmp/lucid-empire/cache /tmp/lucid-empire/kyc_output

# ── 5. Profile symlink check ─────────────────────────────────────────────────
PROFILES="$TITAN_HOME/profiles"
if [ -L "$PROFILES/active" ]; then
    ACTIVE_TARGET=$(readlink -f "$PROFILES/active")
    log "Active profile: $ACTIVE_TARGET"
else
    log "No active profile symlink — creating default"
    ln -sf "$PROFILES/default" "$PROFILES/active" 2>/dev/null || true
fi

# ── 6. Set permissions for live user ──────────────────────────────────────────
# Debian live boots as 'user' — ensure they can access Lucid Empire files
LIVE_USER="user"
if id "$LIVE_USER" &>/dev/null; then
    log "Setting permissions for live user: $LIVE_USER"
    chown -R "$LIVE_USER:$LIVE_USER" /tmp/lucid-empire 2>/dev/null || true
    # Allow the live user to run privileged commands needed by the console
    if [ ! -f /etc/sudoers.d/lucid-titan ]; then
        cat > /etc/sudoers.d/lucid-titan << 'SUDOEOF'
# TITAN V7.0 — Allow live user to manage kernel modules and network
user ALL=(root) NOPASSWD: /sbin/insmod, /sbin/rmmod, /sbin/modprobe
user ALL=(root) NOPASSWD: /usr/sbin/tc, /sbin/ip
user ALL=(root) NOPASSWD: /opt/lucid-empire/bin/load-ebpf.sh
user ALL=(root) NOPASSWD: /opt/lucid-empire/bin/titan-backend-init.sh
SUDOEOF
        chmod 440 /etc/sudoers.d/lucid-titan
        log "Sudoers configured for live user"
    fi
fi

# ── 7. Start FastAPI backend server (if available) ────────────────────────────
BACKEND_SERVER="$TITAN_HOME/backend/server.py"
if [ -f "$BACKEND_SERVER" ]; then
    log "Starting FastAPI backend on :8000..."
    export PYTHONPATH="/opt/titan/core:/opt/titan/apps:/opt/lucid-empire:/opt/lucid-empire/backend:${PYTHONPATH:-}"
    nohup python3 "$BACKEND_SERVER" > /tmp/lucid-empire/backend.log 2>&1 &
    log "Backend PID: $!"
else
    log "Backend server not found — web dashboard unavailable"
fi

log "=== TITAN V7.0 Backend Ready ==="
log "GUI will launch via XDG autostart in user session"
