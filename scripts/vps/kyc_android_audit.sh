#!/bin/bash
echo "=== KYC ANDROID MODULE AUDIT ==="

echo ""
echo "[1] Waydroid status..."
waydroid status 2>&1 || echo "  waydroid status failed"

echo ""
echo "[2] Android images..."
ls -lh /var/lib/waydroid/images/ 2>/dev/null || echo "  No images dir"

echo ""
echo "[3] Waydroid container..."
waydroid container status 2>&1 || echo "  container status failed"

echo ""
echo "[4] Device props..."
cat /var/lib/waydroid/waydroid_base.prop 2>/dev/null || echo "  No props file"

echo ""
echo "[5] Android console..."
ls -la /opt/titan/android/ 2>/dev/null
ls -la /usr/local/bin/titan-android 2>/dev/null || echo "  No titan-android CLI"

echo ""
echo "[6] Waydroid config..."
cat /var/lib/waydroid/waydroid.cfg 2>/dev/null | head -30 || echo "  No waydroid.cfg"

echo ""
echo "[7] Binder check..."
ls -la /dev/binder* 2>/dev/null || echo "  No /dev/binder"
ls -la /dev/binderfs/ 2>/dev/null || echo "  No /dev/binderfs"
lsmod | grep -i binder 2>/dev/null || echo "  No binder module loaded"

echo ""
echo "[8] Kernel version + binder support..."
uname -r
grep -c "BINDER\|ASHMEM" /boot/config-$(uname -r) 2>/dev/null || echo "  Cannot check kernel config"

echo ""
echo "[9] LXC container..."
lxc-ls 2>/dev/null || echo "  No LXC containers"

echo ""
echo "[10] Waydroid session test..."
waydroid session start 2>&1 | head -5 || echo "  session start failed"
sleep 2
waydroid shell -- getprop ro.product.model 2>&1 || echo "  shell access failed"

echo ""
echo "=== AUDIT DONE ==="
