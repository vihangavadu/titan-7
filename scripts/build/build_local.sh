#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# TITAN V8.1 — LOCAL BUILD SCRIPT
# AUTHORITY: Dva.12 | STATUS: OBLIVION_ACTIVE
# OBJECTIVE: Build Titan OS ISO on local Debian 12 machine
#
# Prerequisites:
#   - Debian 12 (Bookworm) host
#   - 8GB+ RAM, 50GB+ free disk
#   - Root/sudo access
#
# Usage:
#   cd titan-main/
#   chmod +x build_local.sh
#   sudo ./build_local.sh
# ═══════════════════════════════════════════════════════════════════════════

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Paths
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ISO_DIR="${REPO_ROOT}/iso"
PROFGEN_DIR="${REPO_ROOT}/profgen"

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  TITAN V8.1 SINGULARITY — LOCAL ISO BUILD                   ║"
echo "║  Authority: Dva.12 | Status: OBLIVION_ACTIVE               ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 1: PREFLIGHT CHECKS
# ═══════════════════════════════════════════════════════════════════════════
echo -e "${BLUE}[1/5] Preflight Checks${NC}"

# Check root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}[!] ERROR: Must run as root (use sudo)${NC}"
    exit 1
fi
echo "  [+] Running as root"

# Check OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    if [ "$ID" != "debian" ] || [ "$VERSION_ID" != "12" ]; then
        echo -e "${YELLOW}[!] WARNING: Debian 12 recommended, detected: $PRETTY_NAME${NC}"
        read -p "  Continue anyway? (y/N): " -n 1 -r
        echo
        [[ ! $REPLY =~ ^[Yy]$ ]] && exit 1
    else
        echo "  [+] OS: Debian 12 (Bookworm)"
    fi
else
    echo -e "${RED}[!] ERROR: Cannot detect OS${NC}"
    exit 1
fi

# Check RAM
TOTAL_RAM_GB=$(free -g | awk '/^Mem:/{print $2}')
if [ "$TOTAL_RAM_GB" -lt 8 ]; then
    echo -e "${YELLOW}[!] WARNING: Low RAM (${TOTAL_RAM_GB}GB, 8GB+ recommended)${NC}"
else
    echo "  [+] RAM: ${TOTAL_RAM_GB}GB"
fi

# Check disk space
AVAIL_DISK_GB=$(df -BG "$ISO_DIR" | awk 'NR==2 {print $4}' | sed 's/G//')
if [ "$AVAIL_DISK_GB" -lt 30 ]; then
    echo -e "${RED}[!] ERROR: Insufficient disk space (${AVAIL_DISK_GB}GB < 30GB required)${NC}"
    exit 1
fi
echo "  [+] Disk: ${AVAIL_DISK_GB}GB available"

# Check CPU
CPU_CORES=$(nproc)
echo "  [+] CPU: ${CPU_CORES} cores"

# Check directories
if [ ! -d "$ISO_DIR" ]; then
    echo -e "${RED}[!] ERROR: iso/ directory not found${NC}"
    exit 1
fi
if [ ! -d "$PROFGEN_DIR" ]; then
    echo -e "${YELLOW}[!] WARNING: profgen/ directory not found${NC}"
fi
echo "  [+] Directory structure verified"

echo ""

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 2: DEPENDENCY CHECK & INSTALLATION
# ═══════════════════════════════════════════════════════════════════════════
echo -e "${BLUE}[2/5] Dependency Check${NC}"

MISSING_DEPS=()

# Check live-build
if ! command -v lb &> /dev/null; then
    MISSING_DEPS+=("live-build")
fi

# Check debootstrap
if ! command -v debootstrap &> /dev/null; then
    MISSING_DEPS+=("debootstrap")
fi

# Check squashfs-tools
if ! command -v mksquashfs &> /dev/null; then
    MISSING_DEPS+=("squashfs-tools")
fi

# Check xorriso
if ! command -v xorriso &> /dev/null; then
    MISSING_DEPS+=("xorriso")
fi

# Check isolinux
if [ ! -f /usr/lib/ISOLINUX/isolinux.bin ]; then
    MISSING_DEPS+=("isolinux")
fi

# Check syslinux-efi
if [ ! -f /usr/lib/syslinux/modules/efi64/ldlinux.e64 ]; then
    MISSING_DEPS+=("syslinux-efi")
fi

# Check grub
if ! command -v grub-mkimage &> /dev/null; then
    MISSING_DEPS+=("grub-pc-bin" "grub-efi-amd64-bin")
fi

# Check build tools
if ! command -v gcc &> /dev/null; then
    MISSING_DEPS+=("build-essential")
fi

# Check kernel headers
if [ ! -d "/usr/src/linux-headers-$(uname -r)" ]; then
    MISSING_DEPS+=("linux-headers-$(uname -r)")
fi

# Check DKMS
if ! command -v dkms &> /dev/null; then
    MISSING_DEPS+=("dkms")
fi

# Check eBPF tools
if ! command -v clang &> /dev/null; then
    MISSING_DEPS+=("clang" "llvm" "libelf-dev" "libbpf-dev")
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    MISSING_DEPS+=("python3" "python3-pip")
fi

if [ ${#MISSING_DEPS[@]} -gt 0 ]; then
    echo -e "${YELLOW}[!] Missing dependencies detected${NC}"
    echo "  Required packages: ${MISSING_DEPS[*]}"
    echo ""
    read -p "  Install missing dependencies? (Y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        echo "  [*] Installing dependencies..."
        export DEBIAN_FRONTEND=noninteractive
        apt-get update -qq
        apt-get install -y -qq "${MISSING_DEPS[@]}" mtools dosfstools
        echo "  [+] Dependencies installed"
    else
        echo -e "${RED}[!] Cannot proceed without dependencies${NC}"
        exit 1
    fi
else
    echo "  [+] All dependencies satisfied"
fi

echo ""

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 3: FINALIZATION PROTOCOL
# ═══════════════════════════════════════════════════════════════════════════
echo -e "${BLUE}[3/5] Finalization Protocol${NC}"

cd "$ISO_DIR"

if [ -f "finalize_titan.sh" ]; then
    echo "  [*] Running finalization protocol..."
    bash finalize_titan.sh
    FINALIZE_EXIT=$?
    if [ $FINALIZE_EXIT -ne 0 ]; then
        echo -e "${RED}[!] Finalization failed with exit code $FINALIZE_EXIT${NC}"
        exit 1
    fi
    echo "  [+] Finalization complete"
else
    echo -e "${YELLOW}[!] WARNING: finalize_titan.sh not found${NC}"
    echo "  Skipping finalization (NOT RECOMMENDED)"
    read -p "  Continue without finalization? (y/N): " -n 1 -r
    echo
    [[ ! $REPLY =~ ^[Yy]$ ]] && exit 1
fi

echo ""

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 4: ISO BUILD
# ═══════════════════════════════════════════════════════════════════════════
echo -e "${BLUE}[4/5] ISO Build${NC}"

# Clean previous build
echo "  [4.1] Cleaning previous build artifacts..."
lb clean --purge 2>&1 | grep -v "^I:" || true
echo "  [+] Clean complete"

# Start build
echo "  [4.2] Starting ISO build..."
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║  BUILD IN PROGRESS — This will take 30-60 minutes          ║${NC}"
echo -e "${CYAN}║  Log: iso/titan_v7_build_$(date +%Y%m%d_%H%M%S).log                    ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

START_TIME=$(date +%s)
BUILD_LOG="titan_v7_build_$(date +%Y%m%d_%H%M%S).log"

# Run build with progress indicator
lb build 2>&1 | tee "$BUILD_LOG" | while IFS= read -r line; do
    # Show only important lines to avoid spam
    if [[ "$line" =~ ^P:|^E:|^W:|Retrieving|Unpacking|Setting\ up|Building ]]; then
        echo "$line"
    fi
done

BUILD_EXIT=${PIPESTATUS[0]}
END_TIME=$(date +%s)
BUILD_DURATION=$((END_TIME - START_TIME))
BUILD_MINUTES=$((BUILD_DURATION / 60))
BUILD_SECONDS=$((BUILD_DURATION % 60))

echo ""

if [ $BUILD_EXIT -ne 0 ]; then
    echo -e "${RED}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║  BUILD FAILED                                               ║${NC}"
    echo -e "${RED}╠══════════════════════════════════════════════════════════════╣${NC}"
    echo -e "${RED}║  Exit code: $BUILD_EXIT                                            ║${NC}"
    echo -e "${RED}║  Log file:  $BUILD_LOG${NC}"
    echo -e "${RED}╚══════════════════════════════════════════════════════════════╝${NC}"
    exit 1
fi

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 5: POST-BUILD VERIFICATION
# ═══════════════════════════════════════════════════════════════════════════
echo -e "${BLUE}[5/5] Post-Build Verification${NC}"

# Find ISO
ISO_FILE=$(find . -maxdepth 1 -name "*.iso" -type f | head -n 1)

if [ -z "$ISO_FILE" ]; then
    echo -e "${RED}[!] ERROR: ISO file not found${NC}"
    exit 1
fi

ISO_SIZE=$(du -h "$ISO_FILE" | cut -f1)
ISO_SIZE_MB=$(du -m "$ISO_FILE" | cut -f1)
ISO_NAME=$(basename "$ISO_FILE")

echo "  [+] ISO created: $ISO_NAME"
echo "  [+] Size: $ISO_SIZE (${ISO_SIZE_MB}MB)"

# Generate SHA256
echo "  [*] Generating SHA256 checksum..."
SHA256=$(sha256sum "$ISO_FILE" | awk '{print $1}')
echo "$SHA256  $ISO_NAME" > "${ISO_NAME}.sha256"
echo "  [+] SHA256: $SHA256"

# Verify ISO structure
echo "  [*] Verifying ISO structure..."
if xorriso -indev "$ISO_FILE" -find / 2>/dev/null | grep -q "isolinux/isolinux.bin"; then
    echo "  [+] BIOS boot: OK"
else
    echo -e "${YELLOW}  [!] BIOS boot: NOT FOUND${NC}"
fi

if xorriso -indev "$ISO_FILE" -find / 2>/dev/null | grep -q "EFI/BOOT"; then
    echo "  [+] UEFI boot: OK"
else
    echo -e "${YELLOW}  [!] UEFI boot: NOT FOUND${NC}"
fi

echo ""

# ═══════════════════════════════════════════════════════════════════════════
# FINAL REPORT
# ═══════════════════════════════════════════════════════════════════════════
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  BUILD COMPLETE                                             ║${NC}"
echo -e "${GREEN}╠══════════════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║  ISO File:     $ISO_NAME${NC}"
echo -e "${GREEN}║  Size:         $ISO_SIZE (${ISO_SIZE_MB}MB)${NC}"
echo -e "${GREEN}║  SHA256:       ${SHA256:0:16}...${NC}"
echo -e "${GREEN}║  Build Time:   ${BUILD_MINUTES}m ${BUILD_SECONDS}s${NC}"
echo -e "${GREEN}║  Log:          $BUILD_LOG${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}Next Steps:${NC}"
echo ""
echo "1. Test ISO in VM:"
echo "   qemu-system-x86_64 -m 4096 -enable-kvm -cdrom $ISO_FILE"
echo ""
echo "2. Write to USB (DESTRUCTIVE - verify device first!):"
echo "   sudo dd if=$ISO_FILE of=/dev/sdX bs=4M status=progress && sync"
echo ""
echo "3. Verify checksum:"
echo "   sha256sum -c ${ISO_NAME}.sha256"
echo ""
echo -e "${YELLOW}Security Reminder:${NC}"
echo "  - Test in isolated VM before production use"
echo "  - Verify all post-build checks in TITAN_V703_SINGULARITY.md"
echo "  - Securely wipe build artifacts after deployment"
echo ""
