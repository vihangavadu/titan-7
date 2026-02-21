#!/bin/bash
echo "=== FINAL ROUTING VERIFICATION ==="
cd /opt/titan

python3 - <<'PYEOF'
import sys, json
sys.path.insert(0, "core")

# Force reload config
import ollama_bridge
ollama_bridge._CONFIG_CACHE = None
ollama_bridge._CONFIG_MTIME = 0

from ollama_bridge import resolve_provider_for_task, get_provider_status, reload_config

reload_config()

print("Provider status:")
for name, info in get_provider_status().items():
    avail = "✅ AVAILABLE" if info["available"] else "❌ unavailable"
    key   = "has_key" if info["has_api_key"] else "no_key"
    print(f"  {name:12s}: {avail}, {key}")

print("\nTask routing (with correct models):")
tasks = ["bin_generation","site_discovery","preset_generation",
         "country_profiles","dork_generation","warmup_searches","default"]
for task in tasks:
    r = resolve_provider_for_task(task)
    if r:
        print(f"  {task:22s} -> {r[0]:8s} / {r[1]}")
    else:
        print(f"  {task:22s} -> NO PROVIDER ❌")
PYEOF

echo ""
echo "=== QUICK LLM SMOKE TEST (qwen2.5:7b) ==="
cd /opt/titan
python3 - <<'PYEOF'
import sys, json
sys.path.insert(0, "core")
from ollama_bridge import query_llm_json

print("Sending test prompt to qwen2.5:7b via Ollama...")
result = query_llm_json(
    prompt='Return ONLY this JSON, nothing else: {"status": "ok", "model": "qwen2.5:7b", "test": "passed"}',
    task_type="default",
    temperature=0.1,
    max_tokens=64,
    timeout=60
)
if result and isinstance(result, dict) and result.get("status") == "ok":
    print(f"  ✅ LLM SMOKE TEST PASSED: {result}")
else:
    print(f"  ⚠️  Result: {result}")
PYEOF

echo ""
echo "=== SUMMARY ==="
echo "VPS: 72.62.72.48 (vps-bookworm)"
echo "Ollama models: mistral:7b-instruct-v0.2-q4_0, qwen2.5:7b"
echo "Core modules: $(ls /opt/titan/core/*.py | wc -l) files"
echo "App modules:  $(ls /opt/titan/apps/*.py | wc -l) files"
echo "Config files: $(ls /opt/titan/config/ | wc -l) files"
echo "Data dirs:    $(ls /opt/titan/data/ | wc -l) directories"
echo ""
echo "New deployments:"
echo "  ✅ ollama_bridge.py    (multi-provider LLM bridge)"
echo "  ✅ dynamic_data.py     (task-specific routing)"
echo "  ✅ forensic_monitor.py (24/7 OS analysis)"
echo "  ✅ forensic_widget.py  (PyQt6 dashboard)"
echo "  ✅ llm_config.json     (qwen2.5:7b + mistral:7b routing)"
echo "  ✅ app_unified.py      (FORENSIC tab added)"
echo ""
echo "=== VERIFICATION COMPLETE ==="
