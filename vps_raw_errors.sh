#!/bin/bash
echo "=== DMESG TITAN/HW ERRORS ==="
dmesg | grep -iE "titan|hardware_shield|netlink|cpuinfo|meminfo|TITAN-HW" | tail -50

echo ""
echo "=== DMESG ALL ERRORS ==="
dmesg | grep -iE "error|fail|warn|oom" | tail -30

echo ""
echo "=== JOURNAL ERRORS (last 50) ==="
journalctl -p err -n 50 --no-pager 2>/dev/null

echo ""
echo "=== LOADED KERNEL MODULES (titan) ==="
lsmod | grep -i titan || echo "No titan modules loaded"

echo ""
echo "=== ALL .ko FILES ==="
find /opt/titan /lib/modules /root -name "*.ko" 2>/dev/null || echo "None found"

echo ""
echo "=== SYSTEMD FAILED UNITS ==="
systemctl --failed --no-pager

echo ""
echo "=== TITAN BACKEND STATUS ==="
systemctl status titan-backend --no-pager 2>/dev/null || echo "titan-backend not found"

echo ""
echo "=== OLLAMA STATUS ==="
systemctl status ollama --no-pager 2>/dev/null | head -20

echo ""
echo "=== XRDP STATUS ==="
systemctl status xrdp --no-pager 2>/dev/null | head -10

echo ""
echo "=== DISK USAGE DETAIL ==="
df -h
du -sh /opt/titan/* 2>/dev/null | sort -rh | head -10

echo ""
echo "=== MEMORY DETAIL ==="
free -h
cat /proc/meminfo | grep -E "MemTotal|MemFree|MemAvailable|SwapTotal|SwapFree"

echo ""
echo "=== NETWORK INTERFACES ==="
ip addr show
ip route show

echo ""
echo "=== TITAN CORE MODULE IMPORTS TEST ==="
cd /opt/titan && python3 -c "
import sys
sys.path.insert(0, 'core')
mods = ['ai_intelligence_engine','ollama_bridge','ghost_motor_v6','tls_parrot',
        'canvas_subpixel_shim','cpuid_rdtsc_shield','fingerprint_injector',
        'immutable_os','forensic_monitor','dynamic_data']
for m in mods:
    try:
        __import__(m)
        print(f'  OK: {m}')
    except Exception as e:
        print(f'  FAIL: {m} — {e}')
" 2>&1

echo ""
echo "=== BACKEND API HEALTH ==="
curl -s http://127.0.0.1:8000/health 2>/dev/null || echo "Backend not responding"
curl -s http://127.0.0.1:8000/ 2>/dev/null | head -3 || echo "No response"

echo ""
echo "=== OLLAMA API HEALTH ==="
curl -s http://127.0.0.1:11434/api/tags 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); [print(f'  Model: {m[\"name\"]}') for m in d.get('models',[])]" 2>/dev/null || echo "Ollama API not responding"
