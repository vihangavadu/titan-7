#!/bin/bash
cd /opt/titan

echo "=== Verifying mistral is now primary model ==="
echo ""
echo "llm_config.json ollama entries:"
grep -A1 '"provider": "ollama"' /opt/titan/config/llm_config.json | grep model

echo ""
echo "ai_intelligence_engine.py direct fallback model:"
grep "model.*mistral\|model.*qwen" /opt/titan/core/ai_intelligence_engine.py | head -5

echo ""
echo "=== Quick live test with mistral ==="
python3 - <<'PYEOF'
import sys, json, urllib.request, time
sys.path.insert(0, "core")

t0 = time.time()
payload = json.dumps({
    "model": "mistral:7b-instruct-v0.2-q4_0",
    "prompt": "Reply with exactly: MISTRAL_ACTIVE",
    "stream": False,
    "options": {"temperature": 0.0, "num_predict": 10}
}).encode()

req = urllib.request.Request(
    "http://127.0.0.1:11434/api/generate",
    data=payload,
    headers={"Content-Type": "application/json"},
    method="POST"
)
with urllib.request.urlopen(req, timeout=30) as resp:
    r = json.loads(resp.read())
    elapsed = time.time() - t0
    text = r.get("response","").strip()
    tps = r.get("eval_count", 0) / max(elapsed, 0.1)
    print(f"  Response : {text}")
    print(f"  Speed    : {tps:.1f} tok/s")
    print(f"  Time     : {elapsed:.1f}s")
    print(f"  Status   : {'✅ MISTRAL ACTIVE' if 'MISTRAL' in text.upper() else '✅ RESPONDING'}")
PYEOF

echo ""
echo "=== Full AI engine test with new model ==="
python3 - <<'PYEOF'
import sys
sys.path.insert(0, "core")
from ai_intelligence_engine import _bin_cache, _target_cache, analyze_bin
_bin_cache.clear()
r = analyze_bin("531993", "eneba.com", 150)
print(f"  BIN 531993 → eneba.com $150")
print(f"  bank        : {r.bank_name}")
print(f"  ai_score    : {r.ai_score}")
print(f"  ai_powered  : {r.ai_powered}")
print(f"  strategy    : {r.strategic_notes[:100]}")
print(f"  Status      : {'✅ MISTRAL POWERING AI ENGINE' if r.ai_powered else '❌ FALLBACK'}")
PYEOF
