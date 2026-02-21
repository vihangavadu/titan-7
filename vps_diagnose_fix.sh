#!/bin/bash
# Diagnose and fix titan_hw.ko and titan-backend failures

echo "═══════════════════════════════════════════════════════════════════════"
echo "DIAGNOSE 1: titan_hw.ko load failure"
echo "═══════════════════════════════════════════════════════════════════════"

echo "[1.1] Kernel version:"
uname -r

echo ""
echo "[1.2] Module info:"
modinfo /opt/titan/kernel-modules/titan_hw.ko 2>&1 | head -20

echo ""
echo "[1.3] Try insmod with verbose:"
insmod /opt/titan/kernel-modules/titan_hw.ko 2>&1 || true

echo ""
echo "[1.4] dmesg last 10 lines after insmod attempt:"
dmesg | tail -10

echo ""
echo "[1.5] titan-hw-shield service unit file:"
cat /etc/systemd/system/titan-hw-shield.service 2>/dev/null

echo ""
echo "[1.6] Service journal:"
journalctl -u titan-hw-shield --no-pager -n 20 2>/dev/null

echo ""
echo "═══════════════════════════════════════════════════════════════════════"
echo "DIAGNOSE 2: titan-backend failure"
echo "═══════════════════════════════════════════════════════════════════════"

echo "[2.1] Service unit file:"
cat /etc/systemd/system/titan-backend.service 2>/dev/null

echo ""
echo "[2.2] Full service journal:"
journalctl -u titan-backend --no-pager -n 30 2>/dev/null

echo ""
echo "[2.3] Try manual start:"
cd /opt/titan
# Find what the service actually runs
EXEC=$(grep ExecStart /etc/systemd/system/titan-backend.service 2>/dev/null | head -1 | sed 's/ExecStart=//')
echo "ExecStart: $EXEC"

echo ""
echo "[2.4] Test backend manually:"
cd /opt/titan
python3 -c "
import sys
sys.path.insert(0, 'core')
sys.path.insert(0, 'apps')
# Try to find what titan-backend runs
import os
for f in ['titan_services.py', 'cockpit_daemon.py', 'integration_bridge.py']:
    p = f'core/{f}'
    if os.path.exists(p):
        print(f'Found: {p}')
" 2>&1

echo ""
echo "[2.5] Check port 8000 current state:"
ss -tlnp | grep 8000

echo ""
echo "[2.6] What's running on 8000:"
fuser 8000/tcp 2>/dev/null && echo "Process found" || echo "Nothing on 8000"

echo ""
echo "═══════════════════════════════════════════════════════════════════════"
echo "DIAGNOSE 3: FontSanitizer correct usage"
echo "═══════════════════════════════════════════════════════════════════════"

cd /opt/titan
python3 - <<'PYEOF'
import sys, inspect
sys.path.insert(0, "core")
from font_sanitizer import FontSanitizer
sig = inspect.signature(FontSanitizer.__init__)
print(f"FontSanitizer.__init__ signature: {sig}")
methods = [m for m in dir(FontSanitizer) if not m.startswith('_')]
print(f"Public methods: {methods}")
PYEOF

echo ""
echo "═══════════════════════════════════════════════════════════════════════"
echo "DIAGNOSE 4: lucid-empire backend"
echo "═══════════════════════════════════════════════════════════════════════"

echo "[4.1] lucid-cerberus service:"
cat /etc/systemd/system/lucid-cerberus.service 2>/dev/null

echo ""
echo "[4.2] lucid-titan service:"
cat /etc/systemd/system/lucid-titan.service 2>/dev/null

echo ""
echo "[4.3] lucid-empire server.py:"
head -30 /opt/lucid-empire/backend/server.py 2>/dev/null

echo ""
echo "[4.4] .env files:"
cat /opt/titan/.env.cognitive 2>/dev/null
echo "---"
cat /opt/lucid-empire/.env.cerberus 2>/dev/null

echo ""
echo "DIAGNOSIS COMPLETE"
