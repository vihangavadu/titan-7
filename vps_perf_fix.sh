#!/bin/bash
# TITAN V7.5 — Apply All Performance Fixes
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  TITAN V7.5 — APPLYING PERFORMANCE FIXES                            ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"

# ─── FIX 1: Create 8GB swap (OOM protection for Ollama + browser) ─────────
echo ""
echo "[1/12] Creating 8GB swap file..."
if swapon --show 2>/dev/null | grep -q "/swapfile"; then
    echo "  ✅ Swap already exists"
else
    fallocate -l 8G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo "/swapfile none swap sw 0 0" >> /etc/fstab
    echo "  ✅ 8GB swap created and enabled"
fi
swapon --show

# ─── FIX 2: Pre-compile Python bytecode ──────────────────────────────────
echo ""
echo "[2/12] Pre-compiling Python bytecode..."
python3 -m compileall -q /opt/titan/core /opt/titan/apps /opt/lucid-empire/backend 2>/dev/null
PYCACHE=$(find /opt/titan -name "__pycache__" -type d | wc -l)
echo "  ✅ $PYCACHE __pycache__ directories created"

# ─── FIX 3: Upgrade uvicorn to multi-worker ──────────────────────────────
echo ""
echo "[3/12] Upgrading titan-backend to 4 workers..."
cat > /etc/systemd/system/titan-backend.service << 'EOF'
[Unit]
Description=TITAN Backend API Server
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/lucid-empire
Environment=PYTHONPATH=/opt/lucid-empire:/opt/titan/core
Environment=PYTHONDONTWRITEBYTECODE=1
ExecStart=/usr/bin/python3 -m uvicorn backend.server:app --host 0.0.0.0 --port 8000 --workers 4 --log-level warning
Restart=on-failure
RestartSec=5
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF
echo "  ✅ Service file updated with 4 workers"

# ─── FIX 4: Network buffer tuning ────────────────────────────────────────
echo ""
echo "[4/12] Tuning network buffers..."
cat > /etc/sysctl.d/99-titan-perf.conf << 'EOF'
# TITAN V7.5 Performance Tuning
# Network buffers
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.core.rmem_default = 1048576
net.core.wmem_default = 1048576
net.ipv4.tcp_rmem = 4096 1048576 16777216
net.ipv4.tcp_wmem = 4096 1048576 16777216

# Connection handling
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65536
net.ipv4.tcp_fastopen = 3
net.ipv4.tcp_fin_timeout = 15
net.ipv4.tcp_keepalive_time = 300
net.ipv4.tcp_keepalive_intvl = 15
net.ipv4.tcp_keepalive_probes = 5
net.ipv4.tcp_tw_reuse = 1

# Memory
vm.swappiness = 10
vm.dirty_ratio = 15
vm.dirty_background_ratio = 5
vm.vfs_cache_pressure = 50

# File descriptors
fs.file-max = 2097152
fs.inotify.max_user_watches = 524288

# Windows TTL spoof (Ring 1)
net.ipv4.ip_default_ttl = 128
EOF
sysctl -p /etc/sysctl.d/99-titan-perf.conf 2>/dev/null | tail -5
echo "  ✅ Network buffers + VM tuning applied"

# ─── FIX 5: Ollama optimization ──────────────────────────────────────────
echo ""
echo "[5/12] Optimizing Ollama service..."
mkdir -p /etc/systemd/system/ollama.service.d
cat > /etc/systemd/system/ollama.service.d/override.conf << 'EOF'
[Service]
Environment="OLLAMA_NUM_PARALLEL=2"
Environment="OLLAMA_MAX_LOADED_MODELS=1"
Environment="OLLAMA_KEEP_ALIVE=10m"
Environment="OLLAMA_FLASH_ATTENTION=1"
LimitNOFILE=65536
EOF
echo "  ✅ Ollama: parallel=2, max_loaded=1, keep_alive=10m, flash_attention=1"

# ─── FIX 6: Set Ollama context length in llm_config.json ─────────────────
echo ""
echo "[6/12] Setting Ollama context length to 4096..."
cd /opt/titan/config
python3 - <<'PYEOF'
import json
try:
    with open("llm_config.json") as f:
        cfg = json.load(f)
    
    ollama = cfg.get("providers", {}).get("ollama", {})
    ollama["context_length"] = 4096
    ollama["num_gpu"] = 0  # CPU-only, avoid GPU detection overhead
    cfg["providers"]["ollama"] = ollama
    
    with open("llm_config.json", "w") as f:
        json.dump(cfg, f, indent=2)
    print("  ✅ context_length=4096 set in llm_config.json")
except Exception as e:
    print(f"  ⚠️  {e}")
PYEOF

# ─── FIX 7: Install fail2ban for SSH protection ──────────────────────────
echo ""
echo "[7/12] Installing fail2ban..."
DEBIAN_FRONTEND=noninteractive apt-get install -y fail2ban 2>/dev/null | tail -3
cat > /etc/fail2ban/jail.local << 'EOF'
[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 5
bantime = 3600
findtime = 600
EOF
systemctl enable fail2ban 2>/dev/null
systemctl start fail2ban 2>/dev/null
echo "  ✅ fail2ban installed and configured"

# ─── FIX 8: Configure firewall ───────────────────────────────────────────
echo ""
echo "[8/12] Configuring iptables firewall..."
# Allow established connections
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
# Allow loopback
iptables -A INPUT -i lo -j ACCEPT
# Allow SSH
iptables -A INPUT -p tcp --dport 22 -j ACCEPT
# Allow RDP
iptables -A INPUT -p tcp --dport 3389 -j ACCEPT
# Allow backend API (localhost only)
iptables -A INPUT -p tcp --dport 8000 -s 127.0.0.1 -j ACCEPT
# Allow Ollama (localhost only)
iptables -A INPUT -p tcp --dport 11434 -s 127.0.0.1 -j ACCEPT
# Allow DNS (localhost only)
iptables -A INPUT -p tcp --dport 53 -s 127.0.0.1 -j ACCEPT
iptables -A INPUT -p udp --dport 53 -s 127.0.0.1 -j ACCEPT
# Allow Tailscale
iptables -A INPUT -p udp --dport 41641 -j ACCEPT
# Drop everything else (commented out for safety — enable manually)
# iptables -P INPUT DROP
echo "  ✅ Firewall rules added (policy still ACCEPT — enable DROP manually)"

# ─── FIX 9: Clean temp files ─────────────────────────────────────────────
echo ""
echo "[9/12] Cleaning temp files..."
BEFORE=$(ls /tmp/titan_* /tmp/vps_* 2>/dev/null | wc -l)
rm -f /tmp/titan_* /tmp/vps_*.sh
AFTER=$(ls /tmp/titan_* /tmp/vps_* 2>/dev/null | wc -l)
echo "  ✅ Cleaned $((BEFORE - AFTER)) temp files"

# ─── FIX 10: Trim journal logs ───────────────────────────────────────────
echo ""
echo "[10/12] Trimming journal logs..."
journalctl --vacuum-size=100M 2>/dev/null | tail -1
echo "  ✅ Journal trimmed to 100MB max"

# ─── FIX 11: Kill duplicate app_unified processes ─────────────────────────
echo ""
echo "[11/12] Cleaning duplicate app_unified processes..."
PIDS=$(ps aux | grep "app_unified.py" | grep -v grep | awk '{print $2}')
COUNT=$(echo "$PIDS" | wc -w)
if [ "$COUNT" -gt 1 ]; then
    # Keep newest, kill older ones
    NEWEST=$(echo "$PIDS" | tail -1)
    for pid in $PIDS; do
        if [ "$pid" != "$NEWEST" ]; then
            kill "$pid" 2>/dev/null
            echo "  Killed stale app_unified PID $pid"
        fi
    done
    echo "  ✅ Kept newest PID $NEWEST, killed $((COUNT - 1)) stale processes"
else
    echo "  ✅ No duplicates found"
fi

# ─── FIX 12: Restart services with new config ────────────────────────────
echo ""
echo "[12/12] Restarting services..."
# Kill old backend holding port 8000
fuser -k 8000/tcp 2>/dev/null; sleep 1
systemctl daemon-reload
systemctl restart ollama
sleep 2
systemctl restart titan-backend
sleep 3

# Verify
echo ""
echo "═══════════════════════════════════════════════════════════════════════"
echo "POST-FIX VERIFICATION"
echo "═══════════════════════════════════════════════════════════════════════"
echo ""
echo "Swap:"
free -h | grep Swap
echo ""
echo "Backend:"
systemctl is-active titan-backend | xargs echo "  titan-backend:"
ss -tlnp | grep 8000 | head -1
WORKERS=$(ps aux | grep "uvicorn" | grep -v grep | wc -l)
echo "  Workers: $WORKERS"
echo ""
echo "Ollama:"
systemctl is-active ollama | xargs echo "  ollama:"
echo ""
echo "Fail2ban:"
systemctl is-active fail2ban | xargs echo "  fail2ban:"
echo ""
echo "Network buffers:"
echo "  rmem_max: $(sysctl -n net.core.rmem_max)"
echo "  wmem_max: $(sysctl -n net.core.wmem_max)"
echo "  swappiness: $(sysctl -n vm.swappiness)"
echo ""
echo "Python bytecode:"
echo "  __pycache__ dirs: $(find /opt/titan -name '__pycache__' -type d | wc -l)"
echo ""
echo "Memory after fixes:"
free -h | head -2
echo ""
echo "Backend health:"
curl -s http://localhost:8000/api/health 2>/dev/null || echo "  Waiting for startup..."

echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  ALL PERFORMANCE FIXES APPLIED                                       ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
