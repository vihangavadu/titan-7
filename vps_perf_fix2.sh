#!/bin/bash
# Fix remaining issues from perf pass 1

echo "=== Fix fail2ban ==="
# fail2ban needs auth.log
touch /var/log/auth.log
systemctl restart fail2ban 2>/dev/null
sleep 1
systemctl is-active fail2ban && echo "  ✅ fail2ban active" || {
    journalctl -u fail2ban --no-pager -n 5 2>/dev/null
    # Try without jail.local if it's causing issues
    rm -f /etc/fail2ban/jail.local
    cat > /etc/fail2ban/jail.d/sshd.conf << 'EOF'
[sshd]
enabled = true
port = ssh
maxretry = 5
bantime = 3600
EOF
    systemctl restart fail2ban 2>/dev/null
    sleep 1
    systemctl is-active fail2ban && echo "  ✅ fail2ban active (fixed)" || echo "  ⚠️  fail2ban still failing"
}

echo ""
echo "=== Fix Python bytecode (force compile all) ==="
python3 -m compileall -q -f /opt/titan/core/ 2>/dev/null
python3 -m compileall -q -f /opt/titan/apps/ 2>/dev/null
python3 -m compileall -q -f /opt/lucid-empire/backend/ 2>/dev/null
python3 -m compileall -q -f /opt/lucid-empire/backend/modules/ 2>/dev/null
PYCACHE=$(find /opt/titan /opt/lucid-empire -name "__pycache__" -type d 2>/dev/null | wc -l)
echo "  ✅ $PYCACHE __pycache__ directories now"

echo ""
echo "=== Verify backend workers ==="
WORKERS=$(ps aux | grep "uvicorn" | grep -v grep | wc -l)
echo "  uvicorn processes: $WORKERS"
ss -tlnp | grep 8000

echo ""
echo "=== Quick Ollama benchmark after restart ==="
curl -s http://127.0.0.1:11434/api/generate -d '{"model":"qwen2.5:7b","prompt":"Say OK","stream":false,"options":{"num_predict":5}}' 2>/dev/null | python3 -c "
import sys,json
try:
    d=json.load(sys.stdin)
    tc=d.get('eval_count',0)
    dur=d.get('eval_duration',1)/1e9
    load=d.get('load_duration',0)/1e9
    print(f'  Model load: {load:.1f}s')
    print(f'  Tokens: {tc}, Speed: {tc/max(dur,0.001):.1f} tok/s')
except: print('  Ollama not ready yet')
"

echo ""
echo "=== Final memory state ==="
free -h
echo ""
echo "=== Process count ==="
echo "  Total: $(ps aux | wc -l)"
echo "  Python: $(ps aux | grep python | grep -v grep | wc -l)"
echo "  app_unified: $(ps aux | grep app_unified | grep -v grep | wc -l)"

echo ""
echo "=== DONE ==="
