#!/bin/bash
# TITAN VPS — Apply Gap Fixes from Deep Audit

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  TITAN VPS — APPLYING GAP FIXES                                      ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"

# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "FIX 1: Load titan_hw.ko kernel module"
echo "─────────────────────────────────────"
if lsmod | grep -q titan; then
    echo "  ✅ titan module already loaded"
else
    if [ -f /opt/titan/kernel-modules/titan_hw.ko ]; then
        insmod /opt/titan/kernel-modules/titan_hw.ko 2>/dev/null
        if lsmod | grep -q titan; then
            echo "  ✅ titan_hw.ko loaded successfully"
        else
            echo "  ⚠️  insmod failed — trying modprobe path"
            # Try loading via service
            systemctl start titan-hw-shield.service 2>/dev/null
            sleep 2
            systemctl is-active titan-hw-shield && echo "  ✅ titan-hw-shield service started" || echo "  ❌ Service failed to start"
        fi
    else
        echo "  ❌ titan_hw.ko not found at /opt/titan/kernel-modules/"
    fi
fi

echo ""
echo "  DMI after fix attempt:"
echo "  sys_vendor: $(cat /sys/class/dmi/id/sys_vendor 2>/dev/null)"
echo "  product_name: $(cat /sys/class/dmi/id/product_name 2>/dev/null)"
echo "  CPU: $(grep 'model name' /proc/cpuinfo | head -1 | cut -d: -f2 | xargs)"

# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "FIX 2: Make resolv.conf immutable"
echo "──────────────────────────────────"
# Ensure correct DNS first
cat > /etc/resolv.conf << 'EOF'
nameserver 127.0.0.1
nameserver 1.1.1.1
nameserver 8.8.8.8
EOF
chattr +i /etc/resolv.conf 2>/dev/null
if lsattr /etc/resolv.conf 2>/dev/null | grep -q '\-i\-'; then
    echo "  ✅ resolv.conf is now immutable"
else
    echo "  ⚠️  chattr +i may not be supported on this filesystem"
fi
echo "  DNS config:"
cat /etc/resolv.conf

# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "FIX 3: Start titan-backend service"
echo "────────────────────────────────────"
systemctl start titan-backend.service 2>/dev/null
sleep 2
if systemctl is-active --quiet titan-backend; then
    echo "  ✅ titan-backend.service is now active"
    ss -tlnp | grep 8000 && echo "  ✅ Port 8000 listening" || echo "  ⚠️  Port 8000 not yet listening"
else
    echo "  ❌ titan-backend failed to start"
    echo "  Last 5 log lines:"
    journalctl -u titan-backend --no-pager -n 5 2>/dev/null
fi

# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "FIX 4: Load eBPF/XDP network shield"
echo "─────────────────────────────────────"
systemctl start titan-network-shield.service 2>/dev/null
sleep 1
if systemctl is-active --quiet titan-network-shield; then
    echo "  ✅ titan-network-shield.service active"
else
    echo "  ⚠️  titan-network-shield not active — trying lucid-ebpf"
    systemctl start lucid-ebpf.service 2>/dev/null
    sleep 1
    systemctl is-active lucid-ebpf && echo "  ✅ lucid-ebpf started" || echo "  ❌ eBPF service failed"
fi

# Check XDP programs
echo "  eBPF programs after fix:"
bpftool prog list 2>/dev/null | grep -E "xdp|tc" | head -5 || echo "  No XDP programs loaded"

# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "FIX 5: Verify fontconfig rejectfont rules"
echo "──────────────────────────────────────────"
FONT_CONF="/etc/fonts/local.conf"
REJECT_COUNT=$(grep -c "rejectfont" "$FONT_CONF" 2>/dev/null || echo 0)
echo "  Current rejectfont rules: $REJECT_COUNT"

if [ "$REJECT_COUNT" -lt 10 ]; then
    echo "  Checking font_sanitizer.py for apply method..."
    cd /opt/titan && python3 -c "
import sys
sys.path.insert(0, 'core')
try:
    from font_sanitizer import FontSanitizer
    fs = FontSanitizer()
    if hasattr(fs, 'apply'):
        fs.apply()
        print('  ✅ FontSanitizer.apply() executed')
    elif hasattr(fs, 'sanitize'):
        fs.sanitize()
        print('  ✅ FontSanitizer.sanitize() executed')
    elif hasattr(fs, 'install'):
        fs.install()
        print('  ✅ FontSanitizer.install() executed')
    else:
        methods = [m for m in dir(fs) if not m.startswith('_')]
        print(f'  Available methods: {methods}')
except Exception as e:
    print(f'  Error: {e}')
" 2>/dev/null
    NEW_COUNT=$(grep -c "rejectfont" "$FONT_CONF" 2>/dev/null || echo 0)
    echo "  Rejectfont rules after fix: $NEW_COUNT"
fi

# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════════════════"
echo "POST-FIX STATUS SUMMARY"
echo "═══════════════════════════════════════════════════════════════════════"

echo ""
echo "Ring 0 — Hardware Shield:"
lsmod | grep titan && echo "  ✅ titan_hw.ko LOADED" || echo "  ❌ titan_hw.ko NOT loaded"
echo "  DMI: $(cat /sys/class/dmi/id/sys_vendor 2>/dev/null)"
echo "  TTL: $(sysctl -n net.ipv4.ip_default_ttl)"

echo ""
echo "Ring 1 — Network Shield:"
systemctl is-active titan-network-shield 2>/dev/null || echo "  inactive"
echo "  TTL: $(sysctl -n net.ipv4.ip_default_ttl) (128=Windows ✅)"

echo ""
echo "Ring 2 — OS Hardening:"
echo "  TZ: $(timedatectl | grep 'Time zone' | xargs)"
lsattr /etc/resolv.conf 2>/dev/null | grep -q '\-i\-' && echo "  resolv.conf: immutable ✅" || echo "  resolv.conf: NOT immutable ⚠️"

echo ""
echo "Ring 3 — Applications:"
systemctl is-active titan-backend 2>/dev/null && echo "  titan-backend: active ✅" || echo "  titan-backend: inactive ❌"
ss -tlnp | grep 8000 && echo "  Port 8000: listening ✅" || echo "  Port 8000: not listening ❌"

echo ""
echo "LLM / Ollama:"
systemctl is-active ollama && echo "  ollama: active ✅" || echo "  ollama: inactive ❌"
ollama list 2>/dev/null | grep -v NAME | awk '{print "  Model: "$1}'

echo ""
echo "Profile:"
du -sh /opt/titan/profiles/ 2>/dev/null
ls /opt/titan/profiles/ 2>/dev/null

echo ""
echo "═══════════════════════════════════════════════════════════════════════"
echo "FIXES APPLIED — AUDIT COMPLETE"
echo "═══════════════════════════════════════════════════════════════════════"
