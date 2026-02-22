#!/bin/bash
# ==============================================================================
# LUCID EMPIRE :: TITAN V8.1 — USB DEPLOYMENT SCRIPT
# ==============================================================================
# Writes the TITAN ISO to a USB drive for live boot deployment.
#
# Usage:
#   sudo bash scripts/write_usb.sh /dev/sdX
#   sudo bash scripts/write_usb.sh /dev/sdX path/to/custom.iso
#
# Requirements:
#   - Root privileges
#   - USB drive (8GB+ recommended)
#   - ISO file in repo root (auto-detected) or specified as second argument
# ==============================================================================

set -eo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

log()  { echo -e "${GREEN}[TITAN]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC}  $1"; }
err()  { echo -e "${RED}[ERROR]${NC} $1" >&2; }

# ── Argument parsing ──────────────────────────────────────────────────
DEVICE="$1"
ISO_FILE="$2"

if [ -z "$DEVICE" ]; then
    echo ""
    echo -e "${CYAN}${BOLD}TITAN V8.1 — USB Deployment${NC}"
    echo ""
    echo "Usage: sudo bash $0 /dev/sdX [path/to/iso]"
    echo ""
    echo "Available USB devices:"
    lsblk -o NAME,SIZE,TYPE,MOUNTPOINT | grep -E "disk|part" | grep -v "loop\|sr"
    echo ""
    echo "WARNING: This will ERASE ALL DATA on the selected device."
    exit 1
fi

# ── Root check ────────────────────────────────────────────────────────
if [ "$EUID" -ne 0 ]; then
    err "This script must be run as root."
    echo "    Usage: sudo bash $0 /dev/sdX"
    exit 1
fi

# ── Device validation ─────────────────────────────────────────────────
if [ ! -b "$DEVICE" ]; then
    err "$DEVICE is not a valid block device."
    exit 1
fi

# Safety: prevent writing to system disk
ROOT_DISK=$(lsblk -no PKNAME "$(findmnt -no SOURCE /)" 2>/dev/null || echo "")
if [ "/dev/$ROOT_DISK" = "$DEVICE" ]; then
    err "REFUSED: $DEVICE appears to be the system disk."
    err "This would destroy your running operating system."
    exit 1
fi

# ── Find ISO ──────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

if [ -z "$ISO_FILE" ]; then
    # Auto-detect ISO in repo root
    ISO_FILE=$(find "$REPO_ROOT" -maxdepth 1 -name "*.iso" -type f | head -1)
    if [ -z "$ISO_FILE" ]; then
        err "No ISO file found in $REPO_ROOT"
        err "Build the ISO first: sudo bash scripts/build_iso.sh"
        exit 1
    fi
fi

if [ ! -f "$ISO_FILE" ]; then
    err "ISO file not found: $ISO_FILE"
    exit 1
fi

ISO_SIZE=$(ls -lh "$ISO_FILE" | awk '{print $5}')
ISO_NAME=$(basename "$ISO_FILE")

# ── Device info ───────────────────────────────────────────────────────
DEV_SIZE=$(lsblk -bno SIZE "$DEVICE" | head -1)
DEV_SIZE_GB=$(echo "scale=1; $DEV_SIZE / 1073741824" | bc 2>/dev/null || echo "?")
DEV_MODEL=$(lsblk -no MODEL "$DEVICE" | head -1 | xargs)

echo ""
echo -e "${CYAN}${BOLD}═══════════════════════════════════════════════════${NC}"
echo -e "${CYAN}${BOLD}  TITAN V8.1 — USB DEPLOYMENT                   ${NC}"
echo -e "${CYAN}${BOLD}═══════════════════════════════════════════════════${NC}"
echo ""
echo -e "  ISO:     ${GREEN}$ISO_NAME${NC} ($ISO_SIZE)"
echo -e "  Device:  ${YELLOW}$DEVICE${NC} ($DEV_SIZE_GB GB) ${DEV_MODEL}"
echo ""
echo -e "  ${RED}${BOLD}WARNING: ALL DATA ON $DEVICE WILL BE DESTROYED${NC}"
echo ""

# ── Confirmation ──────────────────────────────────────────────────────
read -p "Type 'YES' to proceed: " CONFIRM
if [ "$CONFIRM" != "YES" ]; then
    log "Aborted."
    exit 0
fi

# ── Unmount any mounted partitions ────────────────────────────────────
log "Unmounting $DEVICE partitions..."
umount "${DEVICE}"* 2>/dev/null || true
sleep 1

# ── Write ISO ─────────────────────────────────────────────────────────
log "Writing ISO to $DEVICE... (this may take 5-15 minutes)"
echo ""

dd if="$ISO_FILE" of="$DEVICE" bs=4M status=progress oflag=sync conv=fdatasync

sync
sleep 2

# ── Verify ────────────────────────────────────────────────────────────
log "Verifying write..."
SHA_FILE="${ISO_FILE}.sha256"
if [ -f "$SHA_FILE" ]; then
    EXPECTED=$(awk '{print $1}' "$SHA_FILE")
    ISO_BYTES=$(stat -c%s "$ISO_FILE")
    ACTUAL=$(dd if="$DEVICE" bs=4M count=$((ISO_BYTES / 4194304 + 1)) 2>/dev/null | sha256sum | awk '{print $1}')
    if [ "$EXPECTED" = "$ACTUAL" ]; then
        log "Verification: PASS (SHA256 matches)"
    else
        warn "Verification: SHA256 mismatch — write may be corrupted, try again"
    fi
else
    warn "No .sha256 file found — skipping verification"
fi

# ── Done ──────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}═══════════════════════════════════════════════════${NC}"
echo -e "${GREEN}${BOLD}  USB DEPLOYMENT COMPLETE                          ${NC}"
echo -e "${GREEN}${BOLD}═══════════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${CYAN}Next steps:${NC}"
echo -e "  1. Remove USB safely: eject $DEVICE"
echo -e "  2. Insert USB into target machine"
echo -e "  3. Boot from USB (Enter BIOS → F2/F12/DEL → Boot from USB)"
echo -e "  4. TITAN desktop loads in ~30 seconds"
echo -e "  5. Edit /opt/titan/config/titan.env (set proxy credentials)"
echo -e "  6. Launch: python3 /opt/titan/apps/app_unified.py"
echo ""
echo -e "  ${YELLOW}For VPS deployment instead:${NC}"
echo -e "  sudo /opt/titan/bin/install-to-disk /dev/vda"
echo ""
