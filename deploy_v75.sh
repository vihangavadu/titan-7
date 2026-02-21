#!/bin/bash
# TITAN V7.5 DEPLOYMENT — Upload all new files and run provisioners
set -e

VPS="root@72.62.72.48"
LOCAL_BASE="/c/Users/Administrator/Downloads/titan-7/titan-7/iso/config/includes.chroot/opt/titan"
REMOTE_BASE="/opt/titan"

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  TITAN V7.5 DEPLOYMENT                                               ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"

# Upload new V7.5 files
echo ""
echo "[1/6] Uploading V7.5 Ring 0 files..."
scp -o StrictHostKeyChecking=no \
    "$LOCAL_BASE/core/hardware_shield_v6.c" \
    "$LOCAL_BASE/core/cpuid_rdtsc_shield.py" \
    "$LOCAL_BASE/core/initramfs_dmi_hook.sh" \
    "$VPS:$REMOTE_BASE/core/"

echo ""
echo "[2/6] Uploading V7.5 Ring 1 files..."
scp -o StrictHostKeyChecking=no \
    "$LOCAL_BASE/core/network_shield_v6.c" \
    "$VPS:$REMOTE_BASE/core/"

echo ""
echo "[3/6] Uploading V7.5 Ring 2/3 files..."
scp -o StrictHostKeyChecking=no \
    "$LOCAL_BASE/core/canvas_subpixel_shim.py" \
    "$LOCAL_BASE/core/windows_font_provisioner.py" \
    "$VPS:$REMOTE_BASE/core/"

echo ""
echo "[4/6] Setting permissions..."
ssh -o StrictHostKeyChecking=no "$VPS" "chmod +x $REMOTE_BASE/core/cpuid_rdtsc_shield.py $REMOTE_BASE/core/initramfs_dmi_hook.sh $REMOTE_BASE/core/canvas_subpixel_shim.py $REMOTE_BASE/core/windows_font_provisioner.py"

echo ""
echo "[5/6] Running CPUID/RDTSC shield..."
ssh -o StrictHostKeyChecking=no "$VPS" "cd /opt/titan && python3 core/cpuid_rdtsc_shield.py 2>&1" || true

echo ""
echo "[6/6] Running Windows font provisioner..."
ssh -o StrictHostKeyChecking=no "$VPS" "cd /opt/titan && python3 core/windows_font_provisioner.py 2>&1" || true

echo ""
echo "═══════════════════════════════════════════════════════════════════════"
echo "DEPLOYMENT COMPLETE"
echo "═══════════════════════════════════════════════════════════════════════"
