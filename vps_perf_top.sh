#!/bin/bash
echo "=== RAM ==="
free -h
echo ""
echo "=== SWAP ==="
swapon --show 2>/dev/null || echo "No swap"
echo ""
echo "=== TOP MEM CONSUMERS ==="
ps aux --sort=-%mem | head -12
echo ""
echo "=== OLLAMA ==="
ollama list 2>/dev/null
ps aux | grep ollama | grep -v grep
echo ""
echo "=== IMPORT TIMES ==="
cd /opt/titan && python3 - <<'PYEOF'
import time, sys
sys.path.insert(0, "core")
modules = ["ollama_bridge","ai_intelligence_engine","cerberus_enhanced","target_intelligence",
           "three_ds_strategy","preflight_validator","tls_parrot","font_sanitizer",
           "forensic_monitor","dynamic_data","genesis_core","ghost_motor_v6",
           "fingerprint_injector","canvas_subpixel_shim","cpuid_rdtsc_shield"]
results = []
for m in modules:
    t0 = time.monotonic()
    try:
        __import__(m)
        ms = (time.monotonic()-t0)*1000
        results.append((m, ms, "OK"))
    except Exception as e:
        ms = (time.monotonic()-t0)*1000
        results.append((m, ms, str(e)[:40]))
results.sort(key=lambda x: -x[1])
total = sum(r[1] for r in results)
print(f"Total: {total:.0f}ms")
for name, ms, status in results:
    flag = "SLOW" if ms > 500 else "OK"
    print(f"  {flag:4} {name:<35} {ms:>6.0f}ms {'' if status=='OK' else status}")
PYEOF
echo ""
echo "=== NETWORK BUFFERS ==="
sysctl net.core.rmem_max net.core.wmem_max net.core.somaxconn net.ipv4.tcp_fastopen 2>/dev/null
echo ""
echo "=== DISK SPEED ==="
dd if=/dev/zero of=/tmp/disktest bs=1M count=256 oflag=dsync 2>&1 | tail -1
rm -f /tmp/disktest
echo ""
echo "=== FIREWALL ==="
iptables -L INPUT -n 2>/dev/null | head -5
echo ""
echo "=== FAIL2BAN ==="
systemctl is-active fail2ban 2>/dev/null || echo "NOT INSTALLED"
