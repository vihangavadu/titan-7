#!/bin/bash
set -euo pipefail

echo "=== [1] Redis ==="
if ! systemctl is-active redis-server >/dev/null 2>&1; then
    apt-get install -y redis-server 2>&1 | tail -3
    systemctl enable --now redis-server
fi
echo "redis-server: $(systemctl is-active redis-server 2>/dev/null || echo missing)"

echo ""
echo "=== [2] ntfy ==="
if ! which ntfy >/dev/null 2>&1; then
    curl -sSL https://archive.heckel.io/apt/pubkey.txt | gpg --dearmor -o /usr/share/keyrings/ntfy-archive-keyring.gpg 2>/dev/null || true
    echo "deb [signed-by=/usr/share/keyrings/ntfy-archive-keyring.gpg] https://archive.heckel.io/apt debian main" > /etc/apt/sources.list.d/ntfy.list
    apt-get update -qq 2>&1 | tail -2
    apt-get install -y ntfy 2>&1 | tail -5
fi
systemctl enable --now ntfy 2>/dev/null || true
echo "ntfy: $(systemctl is-active ntfy 2>/dev/null || echo missing)"

echo ""
echo "=== [3] Ollama restart ==="
systemctl restart ollama 2>/dev/null || true
sleep 3
echo "ollama: $(systemctl is-active ollama 2>/dev/null || echo missing)"

echo ""
echo "=== [4] WireGuard ==="
apt-get install -y wireguard-tools 2>&1 | tail -3
echo "wg: $(which wg 2>/dev/null || echo not-found)"

echo ""
echo "=== [5] Kernel headers + DKMS rebuild ==="
KVER=$(uname -r)
apt-get install -y "linux-headers-${KVER}" 2>&1 | tail -3
echo "DKMS status before: $(dkms status 2>&1)"
dkms build titan-hw/6.2.0 -k "${KVER}" 2>&1 | tail -5 || true
dkms install titan-hw/6.2.0 -k "${KVER}" 2>&1 | tail -5 || true
echo "DKMS status after: $(dkms status 2>&1)"
if ls /lib/modules/${KVER}/updates/dkms/titan_hw.ko* 2>/dev/null; then
    echo "titan_hw.ko: FOUND"
    modprobe titan_hw 2>/dev/null && echo "titan_hw: loaded" || echo "titan_hw: modprobe failed (may need reboot)"
else
    echo "titan_hw.ko: NOT FOUND (check /tmp/titan_dkms_build.log)"
fi

echo ""
echo "=== [6] ONNX model dir ==="
mkdir -p /opt/titan/models/onnx
echo "Created /opt/titan/models/onnx"

echo ""
echo "=== [7] Titan API quick test ==="
cd /opt/titan
PYTHONPATH="/opt/titan:/opt/titan/core:/opt/titan/apps" python3 -c "
import sys
sys.path.insert(0, '/opt/titan/core')
sys.path.insert(0, '/opt/titan/apps')
try:
    from titan_api import TitanAPI
    print('TitanAPI import: OK')
except Exception as e:
    print(f'TitanAPI import: FAIL ({e})')
try:
    from integration_bridge import TitanIntegrationBridge
    print('IntegrationBridge import: OK')
except Exception as e:
    print(f'IntegrationBridge import: FAIL ({e})')
try:
    from titan_session import TitanSession
    print('TitanSession import: OK')
except Exception as e:
    print(f'TitanSession import: FAIL ({e})')
" 2>&1

echo ""
echo "=== [8] Final service summary ==="
for svc in redis-server ollama xray ntfy tailscaled; do
    STATUS=$(systemctl is-active "$svc" 2>/dev/null || echo "missing")
    echo "  ${svc}: ${STATUS}"
done

echo ""
echo "=== [9] Disk usage ==="
df -h / | tail -1

echo ""
echo "=== POST-INSTALL FIX COMPLETE ==="
