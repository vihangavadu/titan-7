#!/bin/bash
# TITAN V7.0.3 "SINGULARITY" — FINAL FUSION BUILD
# ---------------------------------------------------

set -e

BUILD_START=$(date)
echo "[*] BUILD STARTED: $BUILD_START"
echo "============================================================"

# 1. BRAIN TRANSPLANT (Sync Dev -> ISO)
echo "[*] SYNCING DEV CORE TO ISO..."
if [ -d "titan" ]; then
    mkdir -p iso/config/includes.chroot/opt/titan/core/
    cp -r titan/* iso/config/includes.chroot/opt/titan/core/ 2>/dev/null || echo "    [!] Some files skipped due to permissions"
    echo "    [+] Core synchronized."
else
    echo "    [!] titan directory not found, skipping sync"
fi

# 2. APPLY STEALTH CONFIGS (Ensure overlays are copied)
echo "[*] APPLYING HARDENING OVERLAYS..."
if [ -d "config/includes.chroot" ]; then
    cp -r config/includes.chroot/* iso/config/includes.chroot/ 2>/dev/null || echo "    [!] Some overlays skipped"
    echo "    [+] Overlays merged."
fi

# 3. FORENSIC SANITIZATION (The Script you uploaded)
echo "[*] EXECUTING OBLIVION PROTOCOL..."
if [ -f "finalize_titan_oblivion.sh" ]; then
    chmod +x finalize_titan_oblivion.sh
    bash finalize_titan_oblivion.sh || echo "    [!] Sanitization completed with warnings"
else
    echo "    [!] finalize_titan_oblivion.sh not found"
fi

# 4. PRE-BUILD CHECKS
echo "[*] RUNNING PRE-BUILD CHECKS..."
cd iso

# Clean previous build to avoid tar issues
echo "[*] Cleaning previous build artifacts..."
if command -v lb &> /dev/null; then
    sudo lb clean --all || echo "    [!] Cleanup returned non-zero (this is OK)"
fi

# Verify critical directories exist
mkdir -p config/includes.chroot/opt/titan/{core,bin,config}
mkdir -p config/includes.chroot/usr/src

echo "    [+] Pre-build checks complete"

# 5. BUILD THE ISO
echo "[*] INITIATING LIVE BUILD..."
echo "=================================================="
echo "   STARTING: debian/bookworm/amd64 ISO COMPILATION  "
echo "=================================================="

# Run live-build with verbose output
sudo lb build 2>&1 | tee ../titan_v7_final.log

BUILD_END=$(date)
echo "[*] BUILD COMPLETED: $BUILD_END"

# Verify ISO was created
if [ -f "live-image-amd64.hybrid.iso" ]; then
    ISO_SIZE=$(du -h live-image-amd64.hybrid.iso | cut -f1)
    ISO_SHA=$(sha256sum live-image-amd64.hybrid.iso | awk '{print $1}')
    echo "=================================================="
    echo "   ✓ OPERATIONAL ISO READY"
    echo "=================================================="
    echo "   File:   live-image-amd64.hybrid.iso"
    echo "   Size:   $ISO_SIZE"
    echo "   SHA256: $ISO_SHA"
    echo "=================================================="
else
    echo "=================================================="
    echo "   ✗ BUILD FAILED OR ISO NOT CREATED"
    echo "=================================================="
    echo "Check build log: ../titan_v7_final.log"
    exit 1
fi
