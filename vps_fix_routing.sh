#!/bin/bash
# Fix llm_config.json — put ollama FIRST in every task route
# so it's tried immediately (cloud providers have no API keys)

python3 - <<'PYEOF'
import json

cfg_path = "/opt/titan/config/llm_config.json"
with open(cfg_path) as f:
    cfg = json.load(f)

ollama_model = "mistral:7b-instruct-v0.2-q4_0"
ollama_entry = {"provider": "ollama", "model": ollama_model}

# For every task route, move ollama to position 0
for task, entries in cfg["task_routing"].items():
    if task == "_doc":
        continue
    # Remove any existing ollama entries
    non_ollama = [e for e in entries if e.get("provider") != "ollama"]
    # Put ollama first, then cloud providers as fallback
    cfg["task_routing"][task] = [ollama_entry] + non_ollama

# Also update the default_model in providers section
cfg["providers"]["ollama"]["default_model"] = ollama_model

with open(cfg_path, "w") as f:
    json.dump(cfg, f, indent=2)

print("✅ llm_config.json updated — ollama is now FIRST in all task routes")
print()
print("Task routing order (first entry = first tried):")
for task, entries in cfg["task_routing"].items():
    if task == "_doc":
        continue
    first = entries[0]
    print(f"  {task:<20} → {first['provider']}/{first['model']}")
PYEOF

echo ""
echo "=== Verifying fix — quick AI engine test ==="
cd /opt/titan && python3 - <<'PYEOF'
import sys, time
sys.path.insert(0, "core")

# Clear caches
from ai_intelligence_engine import _bin_cache, _target_cache
_bin_cache.clear()
_target_cache.clear()

t0 = time.time()
from ai_intelligence_engine import analyze_bin
r = analyze_bin("476173", "nike.com", 150)
elapsed = time.time() - t0

print(f"  BIN 476173 → nike.com $150")
print(f"  bank       : {r.bank_name}")
print(f"  ai_score   : {r.ai_score}")
print(f"  ai_powered : {r.ai_powered}")
print(f"  elapsed    : {elapsed:.1f}s")
print(f"  strategy   : {r.strategic_notes[:100]}")
print()
if r.ai_powered:
    print(f"  ✅ MISTRAL IS NOW PRIMARY — AI ENGINE FULLY OPERATIONAL")
else:
    print(f"  ❌ Still falling back — check ollama bridge logs")
    # Debug: test bridge directly
    from ollama_bridge import query_llm, _check_ollama
    print(f"  Ollama available: {_check_ollama()}")
    result = query_llm("Say OK", task_type="default", timeout=30)
    print(f"  Direct bridge test: {result[:50] if result else 'None'}")
PYEOF
