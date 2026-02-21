#!/bin/bash
cd /opt/titan

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  TITAN OS — MISTRAL FULL OPTIMIZATION                                ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"

# ─── 1. Create optimized Modelfile for TITAN-tuned mistral ───────────────────
echo ""
echo "═══ [1] Creating TITAN-optimized Modelfile ═══"

cat > /tmp/Modelfile.titan-mistral << 'MODELEOF'
FROM mistral:7b-instruct-v0.2-q4_0

SYSTEM """You are TITAN AI — a precision intelligence engine for payment card analysis and fraud detection research. You respond ONLY with valid JSON when asked for structured data. No markdown, no code fences, no explanations unless explicitly asked. Be concise, accurate, and direct."""

PARAMETER temperature 0.15
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER repeat_penalty 1.1
PARAMETER num_ctx 4096
PARAMETER num_predict 1024
MODELEOF

echo "Creating titan-mistral model..."
ollama create titan-mistral -f /tmp/Modelfile.titan-mistral 2>&1
echo ""
echo "Models after creation:"
ollama list

# ─── 2. Update llm_config.json to use titan-mistral ─────────────────────────
echo ""
echo "═══ [2] Updating llm_config.json to use titan-mistral ═══"

python3 - << 'PYEOF'
import json

cfg_path = "/opt/titan/config/llm_config.json"
with open(cfg_path) as f:
    cfg = json.load(f)

# Primary: titan-mistral (TITAN-tuned), fallback: mistral:7b
primary = {"provider": "ollama", "model": "titan-mistral"}
fallback = {"provider": "ollama", "model": "mistral:7b-instruct-v0.2-q4_0"}

for task in cfg["task_routing"]:
    if task == "_doc":
        continue
    # Remove existing ollama entries
    others = [e for e in cfg["task_routing"][task] if e.get("provider") != "ollama"]
    # Put titan-mistral first, then mistral as fallback, then cloud
    cfg["task_routing"][task] = [primary, fallback] + others

cfg["providers"]["ollama"]["default_model"] = "titan-mistral"

# Optimize ollama provider settings
cfg["providers"]["ollama"]["timeout"] = 120
cfg["providers"]["ollama"]["max_retries"] = 2
cfg["providers"]["ollama"]["context_length"] = 4096
cfg["providers"]["ollama"]["num_gpu"] = 0

with open(cfg_path, "w") as f:
    json.dump(cfg, f, indent=2)

print("  ✅ llm_config.json updated")
print("  Primary  : titan-mistral (TITAN-tuned)")
print("  Fallback : mistral:7b-instruct-v0.2-q4_0")
print("  Tasks    : all 7 routes updated")
PYEOF

# ─── 3. Update ai_intelligence_engine.py direct fallback ────────────────────
echo ""
echo "═══ [3] Updating ai_intelligence_engine.py direct fallback ═══"
sed -i 's/"model": "mistral:7b-instruct-v0.2-q4_0"/"model": "titan-mistral"/' /opt/titan/core/ai_intelligence_engine.py
grep '"model":' /opt/titan/core/ai_intelligence_engine.py | head -2
echo "  ✅ Direct fallback updated to titan-mistral"

# ─── 4. Tune Ollama service for CPU performance ──────────────────────────────
echo ""
echo "═══ [4] Tuning Ollama service for CPU performance ═══"

mkdir -p /etc/systemd/system/ollama.service.d
cat > /etc/systemd/system/ollama.service.d/titan-tune.conf << 'SVCEOF'
[Service]
Environment="OLLAMA_NUM_PARALLEL=2"
Environment="OLLAMA_MAX_LOADED_MODELS=2"
Environment="OLLAMA_KEEP_ALIVE=30m"
Environment="OLLAMA_FLASH_ATTENTION=1"
Environment="GOMAXPROCS=8"
SVCEOF

systemctl daemon-reload
systemctl restart ollama
sleep 5
echo "  ✅ Ollama service tuned (parallel=2, keep_alive=30m, flash_attn=1)"

# ─── 5. Warm up titan-mistral model ─────────────────────────────────────────
echo ""
echo "═══ [5] Warming up titan-mistral ═══"
python3 - << 'PYEOF'
import json, time, urllib.request

payload = json.dumps({
    "model": "titan-mistral",
    "prompt": "Ready.",
    "stream": False,
    "options": {"num_predict": 5, "temperature": 0.1}
}).encode()

req = urllib.request.Request(
    "http://127.0.0.1:11434/api/generate",
    data=payload,
    headers={"Content-Type": "application/json"},
    method="POST"
)
t0 = time.time()
with urllib.request.urlopen(req, timeout=60) as resp:
    r = json.loads(resp.read())
    elapsed = time.time() - t0
    print(f"  ✅ titan-mistral warmed up in {elapsed:.1f}s")
    print(f"  Response: {r.get('response','').strip()}")
PYEOF

# ─── 6. Full end-to-end TITAN AI test ───────────────────────────────────────
echo ""
echo "═══ [6] Full TITAN AI engine test ═══"
python3 - << 'PYEOF'
import sys, time
sys.path.insert(0, "core")
from ai_intelligence_engine import _bin_cache, _target_cache, analyze_bin, recon_target

_bin_cache.clear()
_target_cache.clear()

# Test 1: BIN analysis
t0 = time.time()
r = analyze_bin("476173", "nike.com", 180)
t1 = time.time() - t0
print(f"  BIN 476173 → nike.com $180")
print(f"    bank       : {r.bank_name}")
print(f"    risk       : {r.risk_level.value}")
print(f"    ai_score   : {r.ai_score}")
print(f"    ai_powered : {r.ai_powered}")
print(f"    time       : {t1:.1f}s")
print(f"    status     : {'✅ TITAN-MISTRAL LIVE' if r.ai_powered else '❌ FALLBACK'}")

print()

# Test 2: Target recon
_target_cache.clear()
t0 = time.time()
r2 = recon_target("stockx.com", "sneakers")
t2 = time.time() - t0
print(f"  Target: stockx.com")
print(f"    fraud_engine : {r2.fraud_engine}")
print(f"    risk_score   : {r2.risk_score}")
print(f"    ai_powered   : {r2.ai_powered}")
print(f"    time         : {t2:.1f}s")
print(f"    status       : {'✅ TITAN-MISTRAL LIVE' if r2.ai_powered else '❌ FALLBACK'}")
PYEOF

# ─── 7. Final status ─────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  OPTIMIZATION COMPLETE — TITAN OS STATUS                             ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Models:"
ollama list
echo ""
echo "Services:"
for svc in ollama titan-backend xrdp; do
    status=$(systemctl is-active $svc 2>/dev/null)
    icon=$([ "$status" = "active" ] && echo "✅" || echo "❌")
    echo "  $icon $svc: $status"
done
echo ""
echo "llm_config primary model:"
python3 -c "import json; c=json.load(open('/opt/titan/config/llm_config.json')); print('  ' + c['task_routing']['bin_generation'][0]['model'])"
