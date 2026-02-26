#!/bin/bash
echo "══════════════════════════════════════════════════════════"
echo "  TITAN OS — Final VPS Verification"
echo "  $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "══════════════════════════════════════════════════════════"

echo ""
echo "=== [1] System ==="
printf "  %-20s %s\n" "Kernel:" "$(uname -r)"
printf "  %-20s %s\n" "Debian:" "$(cat /etc/debian_version)"
printf "  %-20s %s\n" "Hostname:" "$(hostname)"
printf "  %-20s %s\n" "CPU:" "$(nproc) vCPU"
printf "  %-20s %s\n" "RAM:" "$(free -h | awk '/Mem:/{print $2}')"
printf "  %-20s %s\n" "Disk:" "$(df -h / | awk 'NR==2{print $3 "/" $2 " (" $5 " used)"}')"
printf "  %-20s %s\n" "Python:" "$(python3 --version 2>&1)"

echo ""
echo "=== [2] Services ==="
for svc in redis-server ollama xray ntfy tailscaled ssh cron; do
    STATUS=$(systemctl is-active "$svc" 2>/dev/null || echo "missing")
    printf "  %-20s %s\n" "$svc:" "$STATUS"
done

echo ""
echo "=== [3] Ollama Models ==="
ollama list 2>/dev/null || echo "  ollama not responding"

echo ""
echo "=== [4] File Counts ==="
printf "  %-20s %s\n" "core/ .py:" "$(find /opt/titan/core -maxdepth 1 -name '*.py' 2>/dev/null | wc -l)"
printf "  %-20s %s\n" "core/ .c:" "$(find /opt/titan/core -maxdepth 1 -name '*.c' 2>/dev/null | wc -l)"
printf "  %-20s %s\n" "apps/ .py:" "$(find /opt/titan/apps -maxdepth 1 -name '*.py' 2>/dev/null | wc -l)"
printf "  %-20s %s\n" "scripts/:" "$(find /opt/titan/scripts -type f 2>/dev/null | wc -l)"
printf "  %-20s %s\n" "docs/ .md:" "$(find /opt/titan/docs -name '*.md' 2>/dev/null | wc -l)"
printf "  %-20s %s\n" "tests/:" "$(find /opt/titan/tests -type f 2>/dev/null | wc -l)"
printf "  %-20s %s\n" "training/:" "$(find /opt/titan/training -type f 2>/dev/null | wc -l)"
printf "  %-20s %s\n" "Total:" "$(find /opt/titan -type f 2>/dev/null | wc -l)"

echo ""
echo "=== [5] Key Imports ==="
PYTHONPATH="/opt/titan:/opt/titan/core:/opt/titan/apps" python3 << 'PYEOF'
import sys
sys.path.insert(0, "/opt/titan/core")
sys.path.insert(0, "/opt/titan/apps")
modules = [
    "integration_bridge", "titan_api", "titan_master_automation",
    "ai_intelligence_engine", "ollama_bridge", "cognitive_core",
    "genesis_core", "fingerprint_injector", "proxy_manager",
    "cerberus_core", "kill_switch", "forensic_monitor",
    "titan_env", "titan_session", "kyc_core",
]
ok = fail = 0
for m in modules:
    try:
        __import__(m)
        ok += 1
    except Exception as e:
        print(f"  [FAIL] {m}: {e}")
        fail += 1
print(f"  Imports: {ok} OK, {fail} FAIL (of {len(modules)})")
PYEOF

echo ""
echo "=== [6] SSH Protection ==="
printf "  %-20s %s\n" "nftables guard:" "$(nft list tables 2>/dev/null | grep -c titan_ssh_guard) table(s)"
printf "  %-20s %s\n" "Watchdog cron:" "$(crontab -l 2>/dev/null | grep -c titan-ssh-watchdog) entry"
printf "  %-20s %s\n" "SSHD alive:" "$(ss -tlnp | grep -c ':22 ') listener(s)"
printf "  %-20s %s\n" "ClientAlive:" "$(grep '^ClientAlive' /etc/ssh/sshd_config 2>/dev/null | tr '\n' ' ')"

echo ""
echo "=== [7] Network ==="
printf "  %-20s %s\n" "Public IP:" "$(curl -sf --max-time 5 ifconfig.me || echo 'timeout')"
printf "  %-20s %s\n" "Tailscale:" "$(tailscale status 2>/dev/null | head -1 || echo 'not connected')"
printf "  %-20s %s\n" "Redis ping:" "$(redis-cli ping 2>/dev/null || echo 'failed')"

echo ""
echo "=== [8] Ports ==="
ss -tlnp | grep -E ':22 |:5000 |:6379 |:8877 |:11434 ' | awk '{printf "  %-20s %s\n", $4, $6}' || true

echo ""
echo "══════════════════════════════════════════════════════════"
echo "  VERIFICATION COMPLETE"
echo "══════════════════════════════════════════════════════════"
