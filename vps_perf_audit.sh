#!/bin/bash
# TITAN V7.5 — Deep Performance Audit
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  TITAN V7.5 — DEEP PERFORMANCE AUDIT                                ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"

# ─── 1. SYSTEM RESOURCES ─────────────────────────────────────────────────
echo ""
echo "═══ [1] SYSTEM RESOURCES ═══"
echo "CPU:"
nproc && grep "model name" /proc/cpuinfo | head -1
echo ""
echo "RAM:"
free -h | head -2
echo ""
echo "Swap:"
swapon --show 2>/dev/null || echo "  No swap configured"
echo ""
echo "Disk:"
df -h / | tail -1
echo ""
echo "Disk I/O speed (quick test):"
dd if=/dev/zero of=/tmp/testfile bs=1M count=256 oflag=dsync 2>&1 | tail -1
rm -f /tmp/testfile
echo ""
echo "Load average:"
uptime

# ─── 2. MEMORY BREAKDOWN ─────────────────────────────────────────────────
echo ""
echo "═══ [2] MEMORY BREAKDOWN (top consumers) ═══"
ps aux --sort=-%mem | head -15 | awk '{printf "%-6s %-5s %-5s %s\n", $1, $4"%", $6/1024"MB", $11}'

# ─── 3. OLLAMA PERFORMANCE ───────────────────────────────────────────────
echo ""
echo "═══ [3] OLLAMA PERFORMANCE ═══"
echo "Models loaded:"
ollama list 2>/dev/null
echo ""
echo "Ollama process memory:"
ps aux | grep ollama | grep -v grep | awk '{print "  PID:", $2, "MEM:", $4"%", "RSS:", $6/1024"MB", "VSZ:", $5/1024"MB"}'
echo ""
echo "GPU/VRAM (if any):"
nvidia-smi 2>/dev/null || echo "  No GPU detected — Ollama running on CPU"
echo ""
echo "Ollama inference benchmark (short prompt):"
T0=$(date +%s%N)
curl -s http://127.0.0.1:11434/api/generate -d '{"model":"qwen2.5:7b","prompt":"Say hello in 3 words","stream":false,"options":{"num_predict":10}}' | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'  Tokens: {d.get(\"eval_count\",0)}, Eval: {d.get(\"eval_duration\",0)/1e9:.2f}s, Speed: {d.get(\"eval_count\",1)/(d.get(\"eval_duration\",1)/1e9):.1f} tok/s')" 2>/dev/null
T1=$(date +%s%N)
echo "  Wall time: $(( (T1 - T0) / 1000000 ))ms"

# ─── 4. SERVICE STARTUP TIMES ────────────────────────────────────────────
echo ""
echo "═══ [4] SERVICE STARTUP TIMES ═══"
systemd-analyze blame 2>/dev/null | head -15

# ─── 5. ACTIVE SERVICES & PORTS ──────────────────────────────────────────
echo ""
echo "═══ [5] ACTIVE SERVICES & PORTS ═══"
echo "Listening ports:"
ss -tlnp | grep -v "State"
echo ""
echo "Titan services:"
for svc in titan-backend titan-hw-shield titan-network-shield titan-dns titan-vnc ollama; do
    STATUS=$(systemctl is-active $svc 2>/dev/null)
    ENABLED=$(systemctl is-enabled $svc 2>/dev/null)
    echo "  $svc: $STATUS ($ENABLED)"
done

# ─── 6. PYTHON IMPORT PROFILING ──────────────────────────────────────────
echo ""
echo "═══ [6] PYTHON IMPORT PROFILING ═══"
cd /opt/titan && python3 - <<'PYEOF'
import time, sys
sys.path.insert(0, "core")

modules = [
    ("ollama_bridge", "core"),
    ("ai_intelligence_engine", "core"),
    ("cerberus_enhanced", "core"),
    ("target_intelligence", "core"),
    ("three_ds_strategy", "core"),
    ("preflight_validator", "core"),
    ("tls_parrot", "core"),
    ("font_sanitizer", "core"),
    ("forensic_monitor", "core"),
    ("dynamic_data", "core"),
    ("genesis_core", "core"),
    ("ghost_motor_v6", "core"),
    ("fingerprint_injector", "core"),
    ("canvas_subpixel_shim", "core"),
    ("cpuid_rdtsc_shield", "core"),
    ("windows_font_provisioner", "core"),
]

results = []
for mod_name, _ in modules:
    t0 = time.monotonic()
    try:
        __import__(mod_name)
        t1 = time.monotonic()
        ms = (t1 - t0) * 1000
        results.append((mod_name, ms, "OK"))
    except Exception as e:
        t1 = time.monotonic()
        ms = (t1 - t0) * 1000
        results.append((mod_name, ms, str(e)[:40]))

results.sort(key=lambda x: -x[1])
total = sum(r[1] for r in results)
print(f"  Total import time: {total:.0f}ms")
print(f"  {'Module':<35} {'Time':>8} {'Status'}")
print(f"  {'─'*35} {'─'*8} {'─'*20}")
for name, ms, status in results:
    flag = "⚠️" if ms > 500 else "✅" if status == "OK" else "❌"
    print(f"  {flag} {name:<33} {ms:>6.0f}ms {status if status != 'OK' else ''}")
PYEOF

# ─── 7. DISK USAGE BREAKDOWN ─────────────────────────────────────────────
echo ""
echo "═══ [7] DISK USAGE BREAKDOWN ═══"
echo "  /opt/titan:"
du -sh /opt/titan/core/ /opt/titan/apps/ /opt/titan/profiles/ /opt/titan/profgen/ /opt/titan/extensions/ /opt/titan/config/ /opt/titan/assets/ /opt/titan/data/ 2>/dev/null | sort -rh
echo ""
echo "  /opt/lucid-empire:"
du -sh /opt/lucid-empire/ 2>/dev/null
echo ""
echo "  Ollama models:"
du -sh /root/.ollama/models/ 2>/dev/null || du -sh /usr/share/ollama/.ollama/models/ 2>/dev/null || echo "  Unknown location"
echo ""
echo "  Total /opt:"
du -sh /opt/ 2>/dev/null

# ─── 8. NETWORK PERFORMANCE ──────────────────────────────────────────────
echo ""
echo "═══ [8] NETWORK PERFORMANCE ═══"
echo "DNS resolution speed:"
T0=$(date +%s%N)
dig +short google.com @127.0.0.1 2>/dev/null || host google.com 127.0.0.1 2>/dev/null
T1=$(date +%s%N)
echo "  DNS time: $(( (T1 - T0) / 1000000 ))ms"
echo ""
echo "sysctl network tuning:"
for p in net.ipv4.ip_default_ttl net.core.somaxconn net.ipv4.tcp_max_syn_backlog net.ipv4.tcp_fin_timeout net.ipv4.tcp_keepalive_time net.core.rmem_max net.core.wmem_max net.ipv4.tcp_fastopen; do
    val=$(sysctl -n $p 2>/dev/null)
    echo "  $p = $val"
done

# ─── 9. CAMOUFOX READINESS ───────────────────────────────────────────────
echo ""
echo "═══ [9] CAMOUFOX READINESS ═══"
echo "Binary:"
which camoufox 2>/dev/null && camoufox --version 2>/dev/null | head -1 || echo "  Not found"
echo ""
echo "Dependencies:"
for lib in libgtk-3-0 libdbus-glib-1-2 libasound2 libx11-xcb1 libxcomposite1; do
    dpkg -s $lib 2>/dev/null | grep -q "installed" && echo "  ✅ $lib" || echo "  ❌ $lib MISSING"
done
echo ""
echo "Profile size:"
du -sh /opt/titan/profiles/*/ 2>/dev/null | head -3

# ─── 10. SECURITY / HARDENING STATUS ─────────────────────────────────────
echo ""
echo "═══ [10] SECURITY & HARDENING ═══"
echo "Firewall:"
ufw status 2>/dev/null || iptables -L -n 2>/dev/null | head -5
echo ""
echo "Open ports (external):"
ss -tlnp | grep -v "127.0.0.1" | grep -v "::1"
echo ""
echo "Fail2ban:"
systemctl is-active fail2ban 2>/dev/null || echo "  Not installed"
echo ""
echo "Unattended upgrades:"
systemctl is-active unattended-upgrades 2>/dev/null || echo "  Not running"

# ─── 11. CRON / SCHEDULED TASKS ──────────────────────────────────────────
echo ""
echo "═══ [11] CRON / SCHEDULED TASKS ═══"
crontab -l 2>/dev/null || echo "  No crontab"
echo ""
echo "Systemd timers:"
systemctl list-timers --no-pager 2>/dev/null | head -10

# ─── 12. BACKEND API PERFORMANCE ─────────────────────────────────────────
echo ""
echo "═══ [12] BACKEND API PERFORMANCE ═══"
echo "Health check:"
T0=$(date +%s%N)
curl -s http://localhost:8000/api/health 2>/dev/null || curl -s http://localhost:8000/ 2>/dev/null | head -1
T1=$(date +%s%N)
echo ""
echo "  Response time: $(( (T1 - T0) / 1000000 ))ms"
echo ""
echo "Backend workers:"
ps aux | grep -E "uvicorn|gunicorn|python.*server" | grep -v grep | wc -l | xargs echo "  Worker processes:"

# ─── 13. POTENTIAL OPTIMIZATIONS SCAN ─────────────────────────────────────
echo ""
echo "═══ [13] OPTIMIZATION OPPORTUNITIES ═══"
cd /opt/titan && python3 - <<'PYEOF'
import os, sys, subprocess
sys.path.insert(0, "core")

issues = []
recommendations = []

# 1. Check swap
try:
    result = subprocess.run(["swapon", "--show"], capture_output=True, text=True)
    if not result.stdout.strip():
        issues.append("NO SWAP configured — OOM risk with Ollama + browser")
        recommendations.append("CREATE 8GB swap: fallocate -l 8G /swapfile && mkswap /swapfile && swapon /swapfile")
except: pass

# 2. Check Ollama quantization
try:
    result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
    for line in result.stdout.split("\n"):
        if "q4_0" in line.lower():
            pass  # Already quantized
        elif "q8" in line.lower() or "f16" in line.lower() or "f32" in line.lower():
            model = line.split()[0]
            issues.append(f"Ollama model {model} is NOT quantized — high RAM usage")
            recommendations.append(f"Replace with q4_0 variant: ollama pull {model.split(':')[0]}:q4_0")
except: pass

# 3. Check Python __pycache__
pycache_count = 0
for root, dirs, files in os.walk("/opt/titan"):
    if "__pycache__" in dirs:
        pycache_count += 1
if pycache_count < 5:
    issues.append(f"Only {pycache_count} __pycache__ dirs — Python recompiles .pyc on every import")
    recommendations.append("Pre-compile: python3 -m compileall /opt/titan/core /opt/titan/apps")

# 4. Check if uvicorn has multiple workers
try:
    result = subprocess.run(["ps", "aux"], capture_output=True, text=True)
    uvicorn_count = result.stdout.count("uvicorn")
    if uvicorn_count <= 1:
        issues.append("Backend running single uvicorn worker — no parallelism")
        recommendations.append("Add --workers 4 to uvicorn for parallel request handling")
except: pass

# 5. Check TCP fastopen
try:
    tfo = open("/proc/sys/net/ipv4/tcp_fastopen").read().strip()
    if tfo == "0" or tfo == "1":
        issues.append(f"TCP Fast Open = {tfo} — not fully enabled")
        recommendations.append("sysctl -w net.ipv4.tcp_fastopen=3 (enable client+server)")
except: pass

# 6. Check somaxconn
try:
    val = int(open("/proc/sys/net/core/somaxconn").read().strip())
    if val < 1024:
        issues.append(f"somaxconn = {val} — low for concurrent connections")
        recommendations.append("sysctl -w net.core.somaxconn=4096")
except: pass

# 7. Check if Ollama is using NUMA
try:
    result = subprocess.run(["numactl", "--show"], capture_output=True, text=True)
except FileNotFoundError:
    issues.append("numactl not installed — Ollama may not use optimal NUMA policy")
    recommendations.append("apt install numactl && OLLAMA_NUM_THREADS=8 in service file")

# 8. Check journal size
try:
    result = subprocess.run(["journalctl", "--disk-usage"], capture_output=True, text=True)
    if result.stdout:
        size_line = result.stdout.strip()
        if "G" in size_line:
            issues.append(f"Journal logs large: {size_line}")
            recommendations.append("journalctl --vacuum-size=100M")
except: pass

# 9. Check tmp cleanup
try:
    import glob
    tmp_files = glob.glob("/tmp/titan_*") + glob.glob("/tmp/vps_*")
    if len(tmp_files) > 5:
        issues.append(f"{len(tmp_files)} temp files in /tmp — cleanup needed")
        recommendations.append("rm -f /tmp/titan_* /tmp/vps_*")
except: pass

# 10. Check if profile is on SSD or tmpfs
try:
    result = subprocess.run(["findmnt", "-n", "-o", "FSTYPE", "/opt/titan/profiles"], capture_output=True, text=True)
    fstype = result.stdout.strip()
    if fstype and fstype not in ("tmpfs", "ext4"):
        issues.append(f"Profiles on {fstype} — may be slow for browser launch")
except: pass

# 11. Check Ollama context size
try:
    from ollama_bridge import _load_config
    cfg = _load_config()
    ollama_cfg = cfg.get("providers", {}).get("ollama", {})
    ctx = ollama_cfg.get("context_length", 0)
    if ctx > 8192:
        issues.append(f"Ollama context_length={ctx} — high RAM usage per request")
        recommendations.append("Reduce to 4096 in llm_config.json for faster inference")
    elif ctx == 0:
        issues.append("Ollama context_length not set — using model default (may be large)")
        recommendations.append("Set context_length: 4096 in llm_config.json")
except: pass

# 12. Check if font cache is current
try:
    result = subprocess.run(["fc-cache", "--force", "--verbose"], capture_output=True, text=True, timeout=10)
    if "failed" in result.stderr.lower():
        issues.append("Font cache has errors")
        recommendations.append("fc-cache -fv")
except: pass

print(f"\n  Found {len(issues)} optimization opportunities:\n")
for i, (issue, rec) in enumerate(zip(issues, recommendations), 1):
    print(f"  [{i}] ISSUE: {issue}")
    print(f"      FIX:   {rec}")
    print()

if not issues:
    print("  No major issues found — system is well-optimized")
PYEOF

echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  PERFORMANCE AUDIT COMPLETE                                          ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
