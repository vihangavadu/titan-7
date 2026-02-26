#!/bin/bash
# TITAN OS V9.1 — ISO Build v2 (fixed: no tee pipe on lb build)
set -e
ISO_DIR="/opt/titan/iso"
TITAN_SRC="/opt/titan"
INCLUDES_DIR="$ISO_DIR/config/includes.chroot"
LOG="/tmp/titan_iso_build.log"

log() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }

log "=== TITAN OS V9.1 ISO BUILD ==="

# Phase 0: Pre-flight
log "[0/8] Pre-flight..."
FREE_GB=$(df -BG / | awk 'NR==2{print $4}' | tr -d 'G')
log "  Disk: ${FREE_GB}GB | RAM: $(free -h | awk '/^Mem:/{print $2}') | CPU: $(nproc)"

# Phase 1: Already installed
log "[1/8] Build deps already installed"

# Phase 2: Sync codebase
log "[2/8] Syncing codebase into ISO includes..."
for d in core apps profgen config lib bin tools extensions patches vpn assets branding docs; do
    mkdir -p "$INCLUDES_DIR/opt/titan/$d"
done
for d in core apps profgen config lib bin tools extensions patches vpn assets branding; do
    if [ -d "$TITAN_SRC/$d" ]; then
        rsync -a --exclude="__pycache__" --exclude="*.pyc" --exclude="*.bin" \
            --exclude="*.safetensors" --exclude="*.gguf" --exclude="*.bat" \
            "$TITAN_SRC/$d/" "$INCLUDES_DIR/opt/titan/$d/" 2>/dev/null || true
    fi
done
for f in build.sh smoke_test.py verify_all.py; do
    [ -f "$TITAN_SRC/$f" ] && cp "$TITAN_SRC/$f" "$INCLUDES_DIR/opt/titan/" || true
done
CORE_N=$(ls "$INCLUDES_DIR/opt/titan/core/"*.py 2>/dev/null | wc -l)
APP_N=$(ls "$INCLUDES_DIR/opt/titan/apps/"*.py 2>/dev/null | wc -l)
log "  Synced: $CORE_N core modules, $APP_N app files"

# Phase 3: /etc includes
log "[3/8] Writing /etc includes..."
mkdir -p "$INCLUDES_DIR/etc/profile.d" "$INCLUDES_DIR/etc/sysctl.d"

cat > "$INCLUDES_DIR/etc/profile.d/titan.sh" << 'PEOF'
#!/bin/bash
export PYTHONPATH="/opt/titan:/opt/titan/core:/opt/titan/apps:$PYTHONPATH"
export TITAN_ROOT="/opt/titan"
export TITAN_VERSION="9.1"
export HISTSIZE=0
unset HISTFILE
PEOF
chmod +x "$INCLUDES_DIR/etc/profile.d/titan.sh"

cat > "$INCLUDES_DIR/etc/os-release" << 'OEOF'
PRETTY_NAME="Titan OS V9.1"
NAME="TitanOS"
VERSION_ID="9.1"
VERSION="9.1"
ID=titanos
ID_LIKE=debian
OEOF

echo "titan" > "$INCLUDES_DIR/etc/hostname"

cat > "$INCLUDES_DIR/etc/sysctl.d/99-titan.conf" << 'SEOF'
net.ipv6.conf.all.disable_ipv6 = 1
net.ipv6.conf.default.disable_ipv6 = 1
net.ipv4.tcp_timestamps = 0
kernel.dmesg_restrict = 1
SEOF

# Phase 4: Hooks already in place
log "[4/8] Hooks already in place ($(ls $ISO_DIR/config/hooks/live/*.hook.chroot 2>/dev/null | wc -l) hooks)"

# Phase 5: lb config
log "[5/8] Running lb config..."
cd "$ISO_DIR"

lb config noauto \
    --mode debian \
    --distribution bookworm \
    --parent-distribution bookworm \
    --parent-mirror-bootstrap http://deb.debian.org/debian \
    --parent-mirror-chroot http://deb.debian.org/debian \
    --parent-mirror-chroot-security http://security.debian.org/debian-security \
    --parent-mirror-binary http://deb.debian.org/debian \
    --parent-mirror-binary-security http://security.debian.org/debian-security \
    --mirror-bootstrap http://deb.debian.org/debian \
    --mirror-chroot http://deb.debian.org/debian \
    --mirror-chroot-security http://security.debian.org/debian-security \
    --mirror-binary http://deb.debian.org/debian \
    --mirror-binary-security http://security.debian.org/debian-security \
    --keyring-packages debian-archive-keyring \
    --archive-areas "main contrib non-free non-free-firmware" \
    --architectures amd64 \
    --binary-images iso-hybrid \
    --bootappend-live "boot=live components quiet splash toram persistence username=user locales=en_US.UTF-8 ipv6.disable=1" \
    --debian-installer none \
    --security true \
    --backports false \
    --linux-flavours amd64 \
    --bootloader grub-efi \
    --system live \
    --initramfs live-boot \
    --initsystem systemd \
    --linux-packages "linux-image linux-headers" \
    --apt-indices false \
    --apt-recommends false \
    --iso-application "Titan OS V9.1" \
    --iso-publisher "Titan" \
    --iso-volume "TITAN-V91" \
    --firmware-chroot true \
    --cache true \
    --cache-packages true >> "$LOG" 2>&1

log "  lb config done"

# Phase 6: Swap
log "[6/8] Adding swap..."
SWAP="/swapfile_build"
if [ ! -f "$SWAP" ]; then
    fallocate -l 8G "$SWAP" 2>/dev/null || dd if=/dev/zero of="$SWAP" bs=1M count=8192 status=none
    chmod 600 "$SWAP"
    mkswap "$SWAP" -q
    swapon "$SWAP"
fi
log "  Swap: $(free -h | awk '/^Swap:/{print $2}')"

# Phase 7: lb build (NO tee pipe — direct redirect to log)
log "[7/8] Running lb build — this takes 30-90 minutes..."
log "  Started: $(date)"
log "  Monitor: tail -f $LOG"

lb build >> "$LOG" 2>&1
BUILD_EXIT=$?

# Cleanup swap
swapoff "$SWAP" 2>/dev/null || true
rm -f "$SWAP" 2>/dev/null || true

# Phase 8: Report
log "[8/8] Build exit=$BUILD_EXIT"
if [ $BUILD_EXIT -eq 0 ]; then
    ISO_FILE=$(ls "$ISO_DIR"/*.iso 2>/dev/null | head -1)
    if [ -n "$ISO_FILE" ]; then
        ISO_SIZE=$(du -h "$ISO_FILE" | cut -f1)
        ISO_SHA=$(sha256sum "$ISO_FILE" | cut -d' ' -f1)
        log "=== BUILD SUCCESS ==="
        log "  File: $ISO_FILE"
        log "  Size: $ISO_SIZE"
        log "  SHA256: $ISO_SHA"
        log "  Download: scp root@72.62.72.48:$ISO_FILE ."
    fi
else
    log "=== BUILD FAILED (exit=$BUILD_EXIT) ==="
    log "Last 40 lines:"
    tail -40 "$LOG" >> "$LOG.fail" 2>/dev/null
    tail -40 "$LOG"
fi
