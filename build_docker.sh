#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# TITAN V7.0.3 — DOCKER/WSL BUILD SCRIPT
# AUTHORITY: Dva.12 | STATUS: OBLIVION_ACTIVE
# PURPOSE: Build Titan ISO using Docker in WSL Ubuntu environment
#
# Prerequisites:
#   - WSL2 with Ubuntu installed
#   - Docker Desktop for Windows or Docker Engine in WSL
#   - This script in titan-main directory
#
# Usage:
#   chmod +x build_docker.sh
#   ./build_docker.sh
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
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKER_IMAGE="titan-build:latest"
CONTAINER_NAME="titan-build-$(date +%s)"

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  TITAN V7.0.3 SINGULARITY — Docker/WSL Build              ║"
echo "║  Authority: Dva.12 | Status: OBLIVION_ACTIVE               ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 1: ENVIRONMENT CHECK
# ═══════════════════════════════════════════════════════════════════════════
echo -e "${BLUE}[1/5] Environment Check${NC}"

# Check if we're in WSL
if ! grep -q Microsoft /proc/version 2>/dev/null; then
    echo -e "${YELLOW}[!] WARNING: Not running in WSL. Script optimized for WSL2.${NC}"
fi
echo "  [+] Environment: $(uname -r)"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}[!] ERROR: Docker not found${NC}"
    echo "  Install Docker Desktop for Windows or Docker in WSL:"
    echo "  https://docs.docker.com/desktop/windows/install/"
    exit 1
fi
echo "  [+] Docker: $(docker --version)"

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo -e "${RED}[!] ERROR: Docker not running${NC}"
    echo "  Start Docker Desktop or run: sudo service docker start"
    exit 1
fi
echo "  [+] Docker daemon: Running"

# Check available disk space
AVAIL_SPACE=$(df -BG . | awk 'NR==2 {print $4}' | sed 's/G//')
if [ "$AVAIL_SPACE" -lt 10 ]; then
    echo -e "${RED}[!] ERROR: Insufficient disk space (${AVAIL_SPACE}GB < 10GB required)${NC}"
    exit 1
fi
echo "  [+] Available disk: ${AVAIL_SPACE}GB"

# Verify we're in titan-main directory
if [ ! -f "iso/finalize_titan.sh" ]; then
    echo -e "${RED}[!] ERROR: Not in titan-main directory${NC}"
    echo "  Run this script from: /path/to/titan-main/"
    exit 1
fi
echo "  [+] Source directory: $SCRIPT_DIR"

echo ""

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 2: BUILD DOCKER IMAGE
# ═══════════════════════════════════════════════════════════════════════════
echo -e "${BLUE}[2/5] Building Docker Image${NC}"

if docker images | grep -q "$DOCKER_IMAGE"; then
    echo "  [!] Docker image '$DOCKER_IMAGE' already exists"
    read -p "  Rebuild? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "  [*] Rebuilding image..."
        docker build -t "$DOCKER_IMAGE" -f Dockerfile.build .
    else
        echo "  [+] Using existing image"
    fi
else
    echo "  [*] Building Docker image..."
    echo "  This will download Debian 12 base image and install dependencies (5-10 minutes)..."
    docker build -t "$DOCKER_IMAGE" -f Dockerfile.build .
fi

if ! docker images | grep -q "$DOCKER_IMAGE"; then
    echo -e "${RED}[!] ERROR: Docker image build failed${NC}"
    exit 1
fi
echo "  [+] Docker image ready: $DOCKER_IMAGE"
echo ""

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 3: PREPARE BUILD ENVIRONMENT
# ═══════════════════════════════════════════════════════════════════════════
echo -e "${BLUE}[3/5] Preparing Build Environment${NC}"

# Clean any previous containers
echo "  [3.1] Cleaning previous containers..."
docker ps -a --filter "name=titan-build-" --format "{{.Names}}" | xargs -r docker rm -f 2>/dev/null || true

# Create volume for persistent build artifacts
echo "  [3.2] Creating build volume..."
docker volume create titan-build-cache 2>/dev/null || true

echo "  [+] Environment prepared"
echo ""

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 4: BUILD ISO IN CONTAINER
# ═══════════════════════════════════════════════════════════════════════════
echo -e "${BLUE}[4/5] Building ISO in Container${NC}"
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║  CONTAINER BUILD STARTING                                 ║${NC}"
echo -e "${CYAN}║  This will take 30-60 minutes                              ║${NC}"
echo -e "${CYAN}║  Container: $CONTAINER_NAME${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Run build container
docker run -it --rm \
    --name "$CONTAINER_NAME" \
    -v "$SCRIPT_DIR:/workspace" \
    -v titan-build-cache:/var/cache/apt \
    -v titan-build-cache:/var/lib/apt/lists \
    --cap-add SYS_ADMIN \
    --device /dev/fuse \
    --security-opt apparmor:unconfined \
    "$DOCKER_IMAGE" \
    /usr/local/bin/build-titan.sh

BUILD_EXIT=$?

echo ""
if [ $BUILD_EXIT -eq 0 ]; then
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  CONTAINER BUILD COMPLETE                                ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
else
    echo -e "${RED}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║  CONTAINER BUILD FAILED                                   ║${NC}"
    echo -e "${RED}║  Exit code: $BUILD_EXIT                                           ║${NC}"
    echo -e "${RED}╚══════════════════════════════════════════════════════════════╝${NC}"
    exit $BUILD_EXIT
fi
echo ""

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 5: VERIFY OUTPUT
# ═══════════════════════════════════════════════════════════════════════════
echo -e "${BLUE}[5/5] Verifying Output${NC}"

ISO_FILE="$SCRIPT_DIR/iso/titan-v7.0.3-singularity.iso"

if [ -f "$ISO_FILE" ]; then
    ISO_SIZE=$(du -h "$ISO_FILE" | cut -f1)
    echo "  [+] ISO created: $ISO_FILE"
    echo "  [+] Size: $ISO_SIZE"
    
    # Generate checksum if missing
    if [ ! -f "${ISO_FILE}.sha256" ]; then
        echo "  [*] Generating checksum..."
        (cd "$(dirname "$ISO_FILE")" && sha256sum "$(basename "$ISO_FILE")" > "$(basename "$ISO_FILE").sha256")
    fi
    
    # Verify checksum
    if [ -f "${ISO_FILE}.sha256" ]; then
        echo "  [*] Verifying checksum..."
        (cd "$(dirname "$ISO_FILE")" && sha256sum -c "$(basename "$ISO_FILE").sha256")
    fi
    
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  BUILD COMPLETE                                             ║${NC}"
    echo -e "${GREEN}╠══════════════════════════════════════════════════════════════╣${NC}"
    echo -e "${GREEN}║  ISO:        $ISO_FILE${NC}"
    echo -e "${GREEN}║  Size:       $ISO_SIZE${NC}"
    echo -e "${GREEN}║  Location:   Windows: ${SCRIPT_DIR//\/mnt\/c/C:}\\\\iso\\\\${NC}"
    echo -e "${GREEN}║              WSL:     $ISO_FILE${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${CYAN}Next Steps:${NC}"
    echo ""
    echo "1. Test ISO in VM:"
    echo "   qemu-system-x86_64 -m 4096 -enable-kvm -cdrom \"$ISO_FILE\""
    echo ""
    echo "2. Write to USB (DESTRUCTIVE):"
    echo "   sudo dd if=\"$ISO_FILE\" of=/dev/sdX bs=4M status=progress && sync"
    echo ""
    echo "3. Windows path for VM software:"
    echo "   ${ISO_FILE//\/mnt\/c/C:}"
    echo ""
else
    echo -e "${RED}[!] ERROR: ISO file not found${NC}"
    echo "  Check build logs in container output above"
    exit 1
fi

# Clean up container (already removed with --rm flag)
echo "  [+] Container cleaned up"
echo ""

echo -e "${GREEN}TITAN V7.0.3 Docker/WSL build complete!${NC}"
