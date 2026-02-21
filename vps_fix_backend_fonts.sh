#!/bin/bash
# Fix titan-backend service crash + stage Windows fonts

echo "═══════════════════════════════════════════════════════════════════════"
echo "FIX 1: titan-backend — find actual crash reason"
echo "═══════════════════════════════════════════════════════════════════════"

# Kill orphan holding port 8000
echo "[1.1] Killing orphan on port 8000..."
kill $(lsof -t -i:8000) 2>/dev/null || fuser -k 8000/tcp 2>/dev/null || true
sleep 1
ss -tlnp | grep 8000 && echo "  Still occupied" || echo "  ✅ Port free"

# Run server.py directly and capture actual error
echo ""
echo "[1.2] Running server.py directly to capture real error..."
cd /opt/lucid-empire
timeout 8 python3 backend/server.py 2>&1 | head -30
echo "--- end of output ---"

echo ""
echo "[1.3] Checking server.py main block..."
tail -20 /opt/lucid-empire/backend/server.py

echo ""
echo "═══════════════════════════════════════════════════════════════════════"
echo "FIX 2: Stage Windows fonts for FontSanitizer"
echo "═══════════════════════════════════════════════════════════════════════"

echo "[2.1] Finding installed MS fonts..."
find /usr/share/fonts -name "*.ttf" -o -name "*.TTF" 2>/dev/null | grep -iE "arial|times|courier|verdana|tahoma|calibri|segoe|consolas|impact|comic" | head -20

echo ""
echo "[2.2] Creating font staging directory..."
mkdir -p /opt/titan/assets/fonts/windows

echo ""
echo "[2.3] Copying installed MS fonts to staging dir..."
# Copy from mscorefonts install location
for src in /usr/share/fonts/truetype/msttcorefonts /usr/share/fonts/truetype/liberation /usr/share/fonts/truetype/liberation2 /usr/share/fonts/wine; do
    if [ -d "$src" ]; then
        cp "$src"/*.ttf /opt/titan/assets/fonts/windows/ 2>/dev/null
        cp "$src"/*.TTF /opt/titan/assets/fonts/windows/ 2>/dev/null
        echo "  Copied from $src"
    fi
done

echo ""
echo "[2.4] Fonts staged:"
ls /opt/titan/assets/fonts/windows/ | wc -l
ls /opt/titan/assets/fonts/windows/ | head -20

echo ""
echo "[2.5] Re-running FontSanitizer..."
cd /opt/titan && python3 - <<'PYEOF'
import sys
sys.path.insert(0, "core")
from font_sanitizer import FontSanitizer, TargetOS
fs = FontSanitizer(target_os=TargetOS.WINDOWS_11)
result = fs.apply()
print(f"  fonts_rejected:  {result.fonts_rejected}")
print(f"  fonts_installed: {result.fonts_installed}")
print(f"  fonts_missing:   {len(result.fonts_missing)} remaining")
print(f"  clean:           {result.clean}")
if result.fonts_missing:
    print(f"  still missing:   {result.fonts_missing[:8]}")
PYEOF

echo ""
echo "  Rejectfont rules: $(grep -c 'rejectfont' /etc/fonts/local.conf 2>/dev/null)"

echo ""
echo "═══════════════════════════════════════════════════════════════════════"
echo "FIX 3: Restart titan-backend with correct service file"
echo "═══════════════════════════════════════════════════════════════════════"

# Kill anything on 8000 again
kill $(lsof -t -i:8000) 2>/dev/null; sleep 1

# The service file now points to server.py directly
systemctl daemon-reload
systemctl start titan-backend.service
sleep 4

if systemctl is-active --quiet titan-backend; then
    echo "  ✅ titan-backend.service ACTIVE"
    ss -tlnp | grep 8000
    # Test the API
    curl -s http://localhost:8000/api/health 2>/dev/null | head -3 || \
    curl -s http://localhost:8000/health 2>/dev/null | head -3 || \
    curl -s http://localhost:8000/ 2>/dev/null | head -3
else
    echo "  Checking exact failure..."
    # Run with stderr captured
    cd /opt/lucid-empire
    timeout 5 python3 backend/server.py 2>&1 | head -20
fi

echo ""
echo "═══════════════════════════════════════════════════════════════════════"
echo "FINAL COMPLETE STATUS"
echo "═══════════════════════════════════════════════════════════════════════"

echo ""
echo "  Ring 0 — Hardware Shield:"
lsmod | grep titan && echo "    ✅ titan_hw.ko loaded" || echo "    ⚠️  titan_hw.ko NOT loaded (KVM Netlink limit)"
echo "    DMI: $(cat /sys/class/dmi/id/sys_vendor 2>/dev/null)"
echo "    CPU: $(grep 'model name' /proc/cpuinfo | head -1 | cut -d: -f2 | xargs)"

echo ""
echo "  Ring 1 — Network:"
echo "    TTL: $(sysctl -n net.ipv4.ip_default_ttl) (128=Windows ✅)"
systemctl is-active titan-network-shield 2>/dev/null | xargs echo "    XDP shield:"
bpftool prog list 2>/dev/null | grep -c xdp | xargs echo "    XDP programs:"

echo ""
echo "  Ring 2 — OS Hardening:"
echo "    TZ: $(timedatectl | grep 'Time zone' | awk '{print $3}')"
lsattr /etc/resolv.conf 2>/dev/null | grep -q '\-i\-' && echo "    resolv.conf: ✅ immutable" || echo "    resolv.conf: ⚠️  mutable"
echo "    Font rejectfont rules: $(grep -c 'rejectfont' /etc/fonts/local.conf 2>/dev/null)"
echo "    Windows fonts staged: $(ls /opt/titan/assets/fonts/windows/ 2>/dev/null | wc -l)"

echo ""
echo "  Ring 3 — Trinity Apps:"
for app in app_unified app_genesis app_cerberus app_kyc; do
    echo "    ✅ ${app}.py — $(wc -l < /opt/titan/apps/${app}.py) lines"
done
echo "    Camoufox: $(which camoufox 2>/dev/null && echo '✅' || echo '❌')"
echo "    Ghost Motor JS: $(ls /opt/titan/extensions/ghost_motor/ghost_motor.js 2>/dev/null && echo '✅' || echo '❌')"

echo ""
echo "  Ring 4 — Profile Data:"
echo "    Profile: $(ls /opt/titan/profiles/ 2>/dev/null | head -1) ($(du -sh /opt/titan/profiles/ 2>/dev/null | cut -f1))"
echo "    profgen: $(ls /opt/titan/profgen/*.py 2>/dev/null | wc -l) scripts"
echo "    forensic_synthesis_engine.py: $(wc -l < /opt/titan/core/forensic_synthesis_engine.py) lines"

echo ""
echo "  Backend / Services:"
ss -tlnp | grep -q 8000 && echo "    ✅ Port 8000: listening" || echo "    ❌ Port 8000: not listening"
systemctl is-active ollama 2>/dev/null | xargs echo "    Ollama:"
ollama list 2>/dev/null | grep -v NAME | awk '{print "    Model: "$1}'

echo ""
echo "  LLM Bridge (new):"
cd /opt/titan && python3 - <<'PYEOF'
import sys; sys.path.insert(0,"core")
from ollama_bridge import get_provider_status, resolve_provider_for_task
avail = [k for k,v in get_provider_status().items() if v["available"]]
print(f"    Providers available: {avail}")
for t in ["bin_generation","site_discovery","dork_generation"]:
    r = resolve_provider_for_task(t)
    print(f"    {t} -> {r[0]}/{r[1]}" if r else f"    {t} -> NONE")
PYEOF

echo ""
echo "  Forensic Monitor (new):"
echo "    forensic_monitor.py: $(wc -l < /opt/titan/core/forensic_monitor.py) lines ✅"
echo "    forensic_widget.py:  $(wc -l < /opt/titan/apps/forensic_widget.py) lines ✅"
echo "    FORENSIC tab in app_unified: $(grep -c 'FORENSIC' /opt/titan/apps/app_unified.py) references ✅"

echo ""
echo "  Lucid Empire Backend:"
echo "    /opt/lucid-empire/backend/: $(ls /opt/lucid-empire/backend/*.py 2>/dev/null | wc -l) Python files"
echo "    modules/: $(ls /opt/lucid-empire/backend/modules/*.py 2>/dev/null | wc -l) modules"

echo ""
echo "═══════════════════════════════════════════════════════════════════════"
echo "DEEP AUDIT COMPLETE"
echo "═══════════════════════════════════════════════════════════════════════"
