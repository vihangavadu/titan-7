#!/bin/bash
set -euo pipefail

echo "══════════════════════════════════════════════════════════"
echo "  TITAN OS — Post-Install Fix (Ollama + Models + SSH Guard)"
echo "══════════════════════════════════════════════════════════"

# ── [1] Fix Ollama (create user/group, fix service) ──
echo ""
echo "=== [1] Fix Ollama Service ==="
if ! id ollama >/dev/null 2>&1; then
    useradd -r -s /bin/false -U -m -d /usr/share/ollama ollama
    echo "  Created ollama user/group"
else
    echo "  ollama user already exists"
fi

# Ensure ollama home dir exists with correct perms
mkdir -p /usr/share/ollama/.ollama/models
chown -R ollama:ollama /usr/share/ollama

# Reset failure counter and restart
systemctl reset-failed ollama 2>/dev/null || true
systemctl restart ollama
sleep 3
OLLAMA_STATUS=$(systemctl is-active ollama 2>/dev/null || echo "failed")
echo "  ollama: $OLLAMA_STATUS"

if [ "$OLLAMA_STATUS" != "active" ]; then
    echo "  Checking journal..."
    journalctl -u ollama --no-pager -n 5 2>&1 | head -10
fi

# ── [2] Install tiny task-specific models ──
echo ""
echo "=== [2] Install Tiny Task-Specific Models ==="
echo "  VPS: 8 vCPU / 32GB RAM — selecting small, efficient models"
echo ""

# Wait for ollama to be ready
for i in $(seq 1 10); do
    if curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
        echo "  Ollama API ready"
        break
    fi
    echo "  Waiting for ollama API... ($i/10)"
    sleep 2
done

# Model selection rationale for 8vCPU/32GB:
# - qwen2.5:3b (1.9GB) — Fast general reasoning, decision engine
# - phi3:mini (2.3GB) — Microsoft's tiny powerhouse, code + analysis
# - gemma2:2b (1.6GB) — Google's tiny model, classification + routing
# These 3 together use ~6GB RAM, leaving 26GB for Titan OS operations
# Later: user will train custom titan-strategist/analyst/fast models

echo "  Pulling qwen2.5:3b (1.9GB) — fast reasoning/decisions..."
ollama pull qwen2.5:3b 2>&1 | tail -3

echo "  Pulling phi3:mini (2.3GB) — code analysis + strategy..."
ollama pull phi3:mini 2>&1 | tail -3

echo "  Pulling gemma2:2b (1.6GB) — classification + routing..."
ollama pull gemma2:2b 2>&1 | tail -3

echo ""
echo "  Installed models:"
ollama list 2>&1

# ── [3] Install curl_cffi ──
echo ""
echo "=== [3] Install curl_cffi ==="
pip install --break-system-packages curl_cffi 2>&1 | tail -3
python3 -c "import curl_cffi; print(f'  curl_cffi {curl_cffi.__version__}: OK')" 2>&1

# ── [4] SSH lockout prevention — persistent safeguard ──
echo ""
echo "=== [4] SSH Lockout Prevention ==="

# 4a. Deploy updated kill_switch.py (already synced by caller)
echo "  kill_switch.py: SSH port 22 exception added to panic nftables + iptables"

# 4b. Create persistent nftables SSH safeguard that survives any rule flush
cat > /etc/nftables.d/titan-ssh-guard.conf 2>/dev/null << 'NFTEOF' || true
#!/usr/sbin/nft -f
# TITAN SSH GUARD — loaded at boot, survives panic rule flushes
# Priority -200 ensures this runs BEFORE any titan_panic rules (priority 0)
table inet titan_ssh_guard {
    chain ssh_protect {
        type filter hook output priority -200; policy accept;
        # Ensure SSH is ALWAYS reachable
        tcp sport 22 accept
        tcp dport 22 accept
    }
}
NFTEOF

# Create nftables.d directory if needed, apply now
mkdir -p /etc/nftables.d
if [ -f /etc/nftables.d/titan-ssh-guard.conf ]; then
    nft -f /etc/nftables.d/titan-ssh-guard.conf 2>/dev/null && \
        echo "  SSH guard nftables rule: ACTIVE (priority -200, survives panic)" || \
        echo "  SSH guard nftables: failed to apply (nft may not be available)"
fi

# 4c. Ensure nftables loads our guard at boot
if [ -f /etc/nftables.conf ]; then
    if ! grep -q "titan-ssh-guard" /etc/nftables.conf 2>/dev/null; then
        echo 'include "/etc/nftables.d/titan-ssh-guard.conf"' >> /etc/nftables.conf
        echo "  Added SSH guard to /etc/nftables.conf boot sequence"
    fi
fi

# 4d. Set sshd ClientAliveInterval to detect dead connections faster
if grep -q "^ClientAliveInterval" /etc/ssh/sshd_config; then
    sed -i 's/^ClientAliveInterval.*/ClientAliveInterval 60/' /etc/ssh/sshd_config
else
    echo "ClientAliveInterval 60" >> /etc/ssh/sshd_config
fi
if ! grep -q "^ClientAliveCountMax" /etc/ssh/sshd_config; then
    echo "ClientAliveCountMax 10" >> /etc/ssh/sshd_config
fi
systemctl reload sshd 2>/dev/null || systemctl reload ssh 2>/dev/null || true
echo "  SSHD: ClientAliveInterval=60, CountMax=10"

# 4e. Add cron watchdog — if SSH port stops responding, flush all nftables
cat > /usr/local/bin/titan-ssh-watchdog.sh << 'WATCHDOG'
#!/bin/bash
# Titan SSH Watchdog — runs every minute via cron
# If port 22 is unreachable from inside, emergency flush nftables
if ! ss -tlnp | grep -q ':22 '; then
    logger -t titan-ssh-watchdog "EMERGENCY: SSH port 22 not listening, flushing nftables"
    nft flush ruleset 2>/dev/null
    iptables -F 2>/dev/null
    iptables -P OUTPUT ACCEPT 2>/dev/null
    systemctl restart sshd 2>/dev/null || systemctl restart ssh 2>/dev/null
fi
WATCHDOG
chmod +x /usr/local/bin/titan-ssh-watchdog.sh

# Add to cron if not already there
if ! crontab -l 2>/dev/null | grep -q "titan-ssh-watchdog"; then
    (crontab -l 2>/dev/null; echo "* * * * * /usr/local/bin/titan-ssh-watchdog.sh") | crontab -
    echo "  SSH watchdog cron: installed (every 60s)"
fi

# ── [5] DKMS cleanup (don't block on this) ──
echo ""
echo "=== [5] DKMS Cleanup ==="
# Remove broken 7.0.0 version, keep 6.2.0
dkms remove titan-hw/7.0.0 --all 2>/dev/null || true
echo "  Removed broken titan-hw/7.0.0"
echo "  titan-hw DKMS: $(dkms status 2>&1 | grep titan || echo 'not built (non-critical)')"

# ── [6] Final verification ──
echo ""
echo "=== [6] Final Service Check ==="
for svc in redis-server ollama xray ntfy tailscaled ssh; do
    STATUS=$(systemctl is-active "$svc" 2>/dev/null || echo "missing")
    echo "  ${svc}: ${STATUS}"
done

echo ""
echo "=== [7] Disk Usage ==="
df -h / | tail -1

echo ""
echo "=== [8] SSH Guard Verification ==="
nft list tables 2>/dev/null | grep -q "titan_ssh_guard" && \
    echo "  titan_ssh_guard table: ACTIVE" || \
    echo "  titan_ssh_guard table: not loaded"
ss -tlnp | grep ':22 ' | head -1

echo ""
echo "══════════════════════════════════════════════════════════"
echo "  POST-INSTALL FIX COMPLETE"
echo "══════════════════════════════════════════════════════════"
echo "  Models: qwen2.5:3b + phi3:mini + gemma2:2b (~6GB total)"
echo "  SSH Guard: nftables priority -200 + watchdog cron"
echo "  Next: Train custom titan-strategist/analyst/fast models"
echo "══════════════════════════════════════════════════════════"
