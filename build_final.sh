#!/bin/bash
# TITAN V7.0.3 "SINGULARITY" — FINAL FUSION BUILD
# ---------------------------------------------------

# 1. BRAIN TRANSPLANT (Sync Dev -> ISO)
echo "[*] SYNCING DEV CORE TO ISO..."
cp -r titan/* iso/config/includes.chroot/opt/titan/core/
echo "    [+] Core synchronized."

# 2. APPLY STEALTH CONFIGS (Ensure overlays are copied)
echo "[*] APPLYING HARDENING OVERLAYS..."
cp -r config/includes.chroot/* iso/config/includes.chroot/
echo "    [+] Overlays merged."

# 3. FORENSIC SANITIZATION (The Script you uploaded)
echo "[*] EXECUTING OBLIVION PROTOCOL..."
chmod +x finalize_titan_oblivion.sh
./finalize_titan_oblivion.sh

# 4. BUILD THE ISO
echo "[*] INITIATING LIVE BUILD..."
cd iso
sudo lb clean
lb config
sudo lb build 2>&1 | tee ../titan_v7_final.log

echo "---------------------------------------------------"
echo "   OPERATIONAL ISO READY: titan-main/iso/live-image-amd64.hybrid.iso"
echo "---------------------------------------------------"
