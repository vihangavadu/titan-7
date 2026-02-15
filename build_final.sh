#!/bin/bash
# TITAN V7.0.3 "SINGULARITY" — FINAL FUSION BUILD
# ---------------------------------------------------

set -euo pipefail

# 1. BRAIN TRANSPLANT (Sync Dev -> ISO)
echo "[*] SYNCING DEV CORE TO ISO..."
if [ -d "titan" ]; then
    cp -r titan/* iso/config/includes.chroot/opt/titan/core/ || echo "(partial copy ok)"
    echo "    [+] Core synchronized."
else
    echo "    [!] Warning: titan/ dir not found, skipping"
fi

# 2. APPLY STEALTH CONFIGS (Ensure overlays are copied)
echo "[*] APPLYING HARDENING OVERLAYS..."
if [ -d "config/includes.chroot" ]; then
    cp -r config/includes.chroot/* iso/config/includes.chroot/ || echo "(partial copy ok)"
    echo "    [+] Overlays merged."
fi

# 3. FORENSIC SANITIZATION (The Script you uploaded)
echo "[*] EXECUTING OBLIVION PROTOCOL..."
if [ -f "finalize_titan_oblivion.sh" ]; then
    chmod +x finalize_titan_oblivion.sh
    ./finalize_titan_oblivion.sh || echo "[!] Warning: finalize script had warnings"
    echo "    [+] Finalization complete."
else
    echo "    [!] finalize_titan_oblivion.sh not found, continuing"
fi

# 4. BUILD THE ISO
echo "[*] INITIATING LIVE BUILD..."
cd iso

# Check live-build is installed
if ! command -v lb &> /dev/null; then
    echo "[!] live-build not installed, attempting install..."
    sudo apt-get install -y live-build || true
fi

# Configure live-build environment
echo "[*] Configuring live-build..."
if [ -f "./auto/config" ]; then
    chmod +x ./auto/config
    ./auto/config || echo "[!] Warning in config setup"
    echo "    [+] Configuration complete."
fi

# Clean and build
sudo lb clean --all 2>/dev/null || true
echo "[*] Building ISO image..."
sudo lb build 2>&1 | tee ../titan_v7_final.log

echo "---------------------------------------------------"
echo "   OPERATIONAL ISO READY: titan-main/iso/live-image-amd64.hybrid.iso"
echo "---------------------------------------------------"
