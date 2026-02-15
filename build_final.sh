#!/bin/bash
# TITAN V7.0.3 "SINGULARITY" — MINIMAL BUILD SCRIPT
# Focus: Get the ISO built, skip complex finalization

set -euo pipefail

echo "[*] TITAN V7.0.3 BUILD INITIATED"

# Change to ISO directory
cd iso

# Install live-build if needed
if ! command -v lb &> /dev/null; then
    echo "[*] Installing live-build..."
    sudo apt-get update -qq
    sudo apt-get install -y -qq live-build
fi

# Run configuration (CRITICAL STEP - WAS MISSING)
echo "[*] Configuring live-build..."
chmod +x ./auto/config 2>/dev/null || true
./auto/config 2>&1 || {
    echo "[!] Config failed, but continuing...";
}

# Clean previous builds
echo "[*] Cleaning previous builds..."
sudo lb clean --all 2>/dev/null || true
sleep 2

# Build the ISO
echo "[*] Building ISO - this may take 45-60 minutes..."
echo "========================================================"

# Run live-build with verbose output
sudo lb build -v 2>&1 | tee -a ../titan_v7_final.log

# Check result
echo "========================================================"
if [ -f "live-image-amd64.hybrid.iso" ]; then
    echo "[+] SUCCESS: ISO created!"
    ls -lh live-image-amd64.hybrid.iso
exit 0
else
    echo "[-] ERROR: ISO not found!"
    echo "[*] Last 50 lines of build log:"
    tail -50 ../titan_v7_final.log || true
    exit 1
fi
