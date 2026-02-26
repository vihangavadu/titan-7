#!/bin/bash
# TITAN OS V9.1 — ISO Build Part 2: lb config + lb build
# Called by build_iso_vps.sh after hooks are written
set -e
ISO_DIR="/opt/titan/iso"
LOG="/tmp/titan_iso_build.log"

echo ""
echo "[5/8] Configuring live-build..."
cd "$ISO_DIR"

# Clean previous build state (keep config)
lb clean --purge 2>/dev/null || true

# Run lb config
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
    --bootappend-live "boot=live components quiet splash toram persistence username=user locales=en_US.UTF-8 ipv6.disable=1 net.ifnames=0" \
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
    --cache-packages true \
    2>&1 | tee -a "$LOG"

echo "  lb config complete"

echo ""
echo "[6/8] Adding swap for build (live-build needs ~8GB RAM+swap)..."
SWAP_FILE="/swapfile_titan_build"
if [ ! -f "$SWAP_FILE" ]; then
    fallocate -l 8G "$SWAP_FILE" 2>/dev/null || dd if=/dev/zero of="$SWAP_FILE" bs=1M count=8192 status=progress
    chmod 600 "$SWAP_FILE"
    mkswap "$SWAP_FILE"
    swapon "$SWAP_FILE"
    echo "  Swap added: 8GB"
else
    echo "  Swap already exists"
fi
echo "  Total swap: $(free -h | awk '/^Swap:/{print $2}')"

echo ""
echo "[7/8] Running lb build (this takes 30-90 minutes)..."
echo "  Started: $(date)"
echo "  Log: $LOG"
echo "  Monitor: tail -f $LOG"

# Run the actual build
lb build 2>&1 | tee -a "$LOG"

BUILD_EXIT=$?
BUILD_END=$(date +%s)
BUILD_START_FILE="/tmp/titan_build_start"
[ -f "$BUILD_START_FILE" ] && BUILD_START=$(cat "$BUILD_START_FILE") || BUILD_START=$BUILD_END
ELAPSED=$(( (BUILD_END - BUILD_START) / 60 ))

echo ""
echo "[8/8] Build complete (exit=$BUILD_EXIT, elapsed=${ELAPSED}min)"

if [ $BUILD_EXIT -eq 0 ]; then
    ISO_FILE=$(ls "$ISO_DIR"/*.iso 2>/dev/null | head -1)
    if [ -n "$ISO_FILE" ]; then
        ISO_SIZE=$(du -h "$ISO_FILE" | cut -f1)
        ISO_SHA=$(sha256sum "$ISO_FILE" | cut -d' ' -f1)
        echo ""
        echo "============================================================"
        echo "  TITAN OS V9.1 ISO BUILD SUCCESSFUL"
        echo "============================================================"
        echo "  File:    $ISO_FILE"
        echo "  Size:    $ISO_SIZE"
        echo "  SHA256:  $ISO_SHA"
        echo "  Time:    ${ELAPSED} minutes"
        echo ""
        echo "  Download:"
        echo "    scp -P 22 root@72.62.72.48:$ISO_FILE ."
        echo "============================================================"

        # Save build info
        cat > /tmp/titan_iso_info.txt << INFOEOF
TITAN_ISO=$ISO_FILE
TITAN_ISO_SIZE=$ISO_SIZE
TITAN_ISO_SHA256=$ISO_SHA
BUILD_TIME_MIN=$ELAPSED
BUILD_DATE=$(date)
INFOEOF
    else
        echo "ERROR: Build succeeded but no ISO file found in $ISO_DIR"
        ls -la "$ISO_DIR"/*.iso 2>/dev/null || true
    fi
else
    echo ""
    echo "============================================================"
    echo "  BUILD FAILED (exit=$BUILD_EXIT)"
    echo "  Check log: $LOG"
    echo "  Last 30 lines:"
    echo "============================================================"
    tail -30 "$LOG"
fi

# Cleanup swap
swapoff "$SWAP_FILE" 2>/dev/null || true
rm -f "$SWAP_FILE" 2>/dev/null || true
