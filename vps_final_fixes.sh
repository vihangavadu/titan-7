#!/bin/bash
# TITAN VPS — Final targeted fixes

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  TITAN VPS — FINAL TARGETED FIXES                                    ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"

# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "FIX 1: Install uvicorn for titan-backend"
echo "─────────────────────────────────────────"
python3 -c "import uvicorn; print('uvicorn already installed:', uvicorn.__version__)" 2>/dev/null || {
    echo "  Installing uvicorn + fastapi..."
    pip3 install uvicorn fastapi --quiet 2>&1 | tail -3
}
python3 -c "import uvicorn; print('  ✅ uvicorn:', uvicorn.__version__)" 2>/dev/null || echo "  ❌ uvicorn install failed"

echo ""
echo "  Testing backend import chain..."
python3 -c "
import sys
sys.path.insert(0, '/opt/lucid-empire')
sys.path.insert(0, '/opt/titan/core')
try:
    from backend.server import app
    print('  ✅ backend.server imported OK')
    print('  App type:', type(app).__name__)
except Exception as e:
    print(f'  ❌ Import error: {e}')
    import traceback
    traceback.print_exc()
" 2>&1

# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "FIX 2: Start titan-backend service"
echo "────────────────────────────────────"
systemctl daemon-reload
systemctl restart titan-backend.service
sleep 3

if systemctl is-active --quiet titan-backend; then
    echo "  ✅ titan-backend.service ACTIVE"
    ss -tlnp | grep 8000 && echo "  ✅ Port 8000 listening"
else
    echo "  ❌ Still failing — checking error..."
    journalctl -u titan-backend --no-pager -n 10 2>/dev/null
    
    # Try running directly to see the actual error
    echo ""
    echo "  Direct run test:"
    cd /opt/lucid-empire
    timeout 5 python3 -c "
import sys
sys.path.insert(0, '/opt/lucid-empire')
sys.path.insert(0, '/opt/titan/core')
from backend.server import app
import uvicorn
print('Backend ready, starting uvicorn...')
uvicorn.run(app, host='0.0.0.0', port=8000, log_level='warning')
" 2>&1 | head -20 &
    sleep 3
    ss -tlnp | grep 8000 && echo "  ✅ Port 8000 now listening (manual start)" || echo "  ❌ Port 8000 still not listening"
fi

# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "FIX 3: Apply FontSanitizer with correct target_os"
echo "──────────────────────────────────────────────────"
cd /opt/titan
python3 - <<'PYEOF'
import sys
sys.path.insert(0, "core")
try:
    from font_sanitizer import FontSanitizer, TargetOS
    print(f"  TargetOS values: {[e.name for e in TargetOS]}")
    
    # Use WINDOWS_11 or WINDOWS_10 as target
    target = TargetOS.WINDOWS_11 if hasattr(TargetOS, 'WINDOWS_11') else list(TargetOS)[0]
    print(f"  Using target: {target}")
    
    fs = FontSanitizer(target_os=target)
    
    # Apply font sanitization
    if hasattr(fs, 'apply'):
        result = fs.apply()
        print(f"  ✅ FontSanitizer.apply() -> {result}")
    elif hasattr(fs, 'write_local_conf'):
        conf = fs.generate_local_conf()
        fs.write_local_conf(conf)
        fs.rebuild_font_cache()
        print("  ✅ FontSanitizer conf written and cache rebuilt")
    
    # Count rules after
    import subprocess
    result = subprocess.run(['grep', '-c', 'rejectfont', '/etc/fonts/local.conf'], 
                          capture_output=True, text=True)
    print(f"  Rejectfont rules now: {result.stdout.strip()}")
    
except Exception as e:
    print(f"  Error: {e}")
    import traceback
    traceback.print_exc()
PYEOF

# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "FIX 4: titan_hw.ko — patch Netlink socket issue"
echo "─────────────────────────────────────────────────"
echo "  Checking dmesg for exact error:"
dmesg | grep -i "TITAN-HW" | tail -5

echo ""
echo "  The Netlink socket failure is a KVM limitation."
echo "  Checking if module partially loaded (procfs hooks):"
cat /proc/cpuinfo | grep "model name" | head -1
cat /sys/class/dmi/id/sys_vendor 2>/dev/null

echo ""
echo "  Checking if hardware_shield_v6.ko exists (service uses different path):"
ls -lh /opt/titan/core/hardware_shield_v6.ko 2>/dev/null || echo "  ❌ hardware_shield_v6.ko not compiled in core/"
ls -lh /opt/titan/kernel-modules/titan_hw.ko 2>/dev/null

echo ""
echo "  titan-hw-shield service uses: /opt/titan/core/hardware_shield_v6.ko"
echo "  But compiled module is at: /opt/titan/kernel-modules/titan_hw.ko"
echo "  Creating symlink fix..."
ln -sf /opt/titan/kernel-modules/titan_hw.ko /opt/titan/core/hardware_shield_v6.ko 2>/dev/null
ls -lh /opt/titan/core/hardware_shield_v6.ko 2>/dev/null

echo ""
echo "  Retrying service start:"
systemctl restart titan-hw-shield.service 2>/dev/null
sleep 2
systemctl is-active titan-hw-shield && echo "  ✅ titan-hw-shield active" || echo "  ❌ Still failing"
journalctl -u titan-hw-shield --no-pager -n 5 2>/dev/null

echo ""
echo "  Trying direct insmod of kernel-modules version:"
insmod /opt/titan/kernel-modules/titan_hw.ko 2>&1 || true
dmesg | tail -5

# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════════════════"
echo "FINAL STATUS REPORT"
echo "═══════════════════════════════════════════════════════════════════════"

echo ""
echo "┌─────────────────────────────────────────────────────────────────────┐"
echo "│  TITAN V7.5 VPS — SYSTEM STATUS                                     │"
echo "└─────────────────────────────────────────────────────────────────────┘"

# Ring 0
echo ""
echo "RING 0 — Hardware Shield:"
if lsmod | grep -q titan; then
    echo "  ✅ titan_hw.ko LOADED"
    echo "  CPU: $(grep 'model name' /proc/cpuinfo | head -1 | cut -d: -f2 | xargs)"
    echo "  DMI: $(cat /sys/class/dmi/id/sys_vendor 2>/dev/null)"
else
    echo "  ⚠️  titan_hw.ko NOT loaded (KVM Netlink limitation)"
    echo "  CPU: $(grep 'model name' /proc/cpuinfo | head -1 | cut -d: -f2 | xargs) [REAL]"
    echo "  DMI: $(cat /sys/class/dmi/id/sys_vendor 2>/dev/null) [REAL]"
fi

# Ring 1
echo ""
echo "RING 1 — Network Shield:"
echo "  TTL: $(sysctl -n net.ipv4.ip_default_ttl) $([ $(sysctl -n net.ipv4.ip_default_ttl) -eq 128 ] && echo '✅ Windows' || echo '❌ Linux')"
systemctl is-active titan-network-shield 2>/dev/null | xargs -I{} echo "  XDP shield: {}"
bpftool prog list 2>/dev/null | grep -c xdp | xargs -I{} echo "  XDP programs: {}"

# Ring 2
echo ""
echo "RING 2 — OS Hardening:"
echo "  TZ: $(timedatectl | grep 'Time zone' | xargs)"
lsattr /etc/resolv.conf 2>/dev/null | grep -q '\-i\-' && echo "  resolv.conf: immutable ✅" || echo "  resolv.conf: NOT immutable ⚠️"
echo "  Font rejectfont rules: $(grep -c 'rejectfont' /etc/fonts/local.conf 2>/dev/null)"

# Ring 3
echo ""
echo "RING 3 — Applications:"
for app in app_unified app_genesis app_cerberus app_kyc; do
    lines=$(wc -l < /opt/titan/apps/${app}.py 2>/dev/null)
    echo "  ✅ ${app}.py — ${lines} lines"
done
echo "  Camoufox: $(which camoufox 2>/dev/null || echo 'not in PATH')"

# Ring 4
echo ""
echo "RING 4 — Profile Data:"
echo "  Profile: $(ls /opt/titan/profiles/ 2>/dev/null | head -1)"
echo "  Size: $(du -sh /opt/titan/profiles/ 2>/dev/null | cut -f1)"
echo "  profgen scripts: $(ls /opt/titan/profgen/*.py 2>/dev/null | wc -l)"

# Backend
echo ""
echo "BACKEND / SERVICES:"
ss -tlnp | grep 8000 && echo "  ✅ Port 8000: listening" || echo "  ❌ Port 8000: not listening"
systemctl is-active ollama 2>/dev/null | xargs -I{} echo "  Ollama: {}"
ollama list 2>/dev/null | grep -v NAME | awk '{print "  Model: "$1}'

# LLM
echo ""
echo "LLM BRIDGE:"
cd /opt/titan && python3 - <<'PYEOF'
import sys
sys.path.insert(0, "core")
from ollama_bridge import get_provider_status, resolve_provider_for_task
avail = [k for k,v in get_provider_status().items() if v["available"]]
print(f"  Available: {avail}")
r = resolve_provider_for_task("bin_generation")
print(f"  bin_generation -> {r[0]}/{r[1]}" if r else "  NO PROVIDER")
PYEOF

echo ""
echo "FORENSIC MONITOR:"
ls -lh /opt/titan/core/forensic_monitor.py 2>/dev/null && echo "  ✅ forensic_monitor.py deployed" || echo "  ❌ MISSING"
ls -lh /opt/titan/apps/forensic_widget.py 2>/dev/null && echo "  ✅ forensic_widget.py deployed" || echo "  ❌ MISSING"

echo ""
echo "═══════════════════════════════════════════════════════════════════════"
echo "DONE"
echo "═══════════════════════════════════════════════════════════════════════"
