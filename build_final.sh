#!/bin/bash
# TITAN V7.0.3 "SINGULARITY" — KINETIC BUILD SCRIPT
# Authority: Dva.12 | Status: OBLIVION_ACTIVE
# Focus: Maximum reliability with proper privilege escalation

set -euo pipefail

echo "════════════════════════════════════════════════════════"
echo "  TITAN V7.0.3 SINGULARITY — KINETIC ISO BUILD"
echo "════════════════════════════════════════════════════════"

# Verify we're in correct directory
if [ ! -f "iso/auto/config" ]; then
    echo "[!] ERROR: iso/auto/config not found. Run from workspace root."
    exit 1
fi

# Change to ISO directory
cd iso

# Install live-build if needed
if ! command -v lb &> /dev/null; then
    echo "[*] Installing live-build..."
    sudo apt-get update -qq
    sudo apt-get install -y -qq live-build
fi

# Show resource status
echo "[*] Building with current resources:"
df -h / | tail -1
free -h | grep Mem

# Run configuration (CRITICAL)
echo "[*] Configuring live-build environment..."
chmod +x ./auto/config 2>/dev/null || true
./auto/config 2>&1 || echo "[!] Config warning (continuing...)"

# Clean previous builds (CRITICAL to free space)
echo "[*] Cleaning previous builds..."
sudo lb clean --all 2>/dev/null || true
sleep 2

# Verify clean state
echo "[*] Pre-build state:"
du -sh build 2>/dev/null || echo "  build dir clean"
df -h / | tail -1

# Build the ISO with verbose logging
echo "[*] Initiating live-build process..."
echo "    Expected duration: 45-60 minutes"
echo "    Logs available in: ../titan_v7_final.log"
echo "════════════════════════════════════════════════════════"

# Run live-build as root with proper privilege escalation
if ! sudo lb build -v 2>&1 | tee -a ../titan_v7_final.log; then
    echo ""
    echo "[!] Build process encountered an error."
    echo "[*] Checking for ISO despite error..."
fi

echo "════════════════════════════════════════════════════════"

# Verify output
if [ -f "live-image-amd64.hybrid.iso" ]; then
    ISO_SIZE=$(stat -c%s live-image-amd64.hybrid.iso 2>/dev/null | numfmt --to=iec-i --suffix=B 2>/dev/null || du -h live-image-amd64.hybrid.iso | cut -f1)
    echo "[+] SUCCESS: ISO created!"
    echo "    File: live-image-amd64.hybrid.iso"
    echo "    Size: $ISO_SIZE"
    ls -lh live-image-amd64.hybrid.iso
    exit 0
else
    echo "[-] ERROR: ISO not found after build attempt"
    echo "[*] Last 100 lines of build log:"
    tail -100 ../titan_v7_final.log || true
    exit 1
fi
