#!/bin/bash
echo "=== llm_config.json primary ollama model ==="
grep -A1 '"provider": "ollama"' /opt/titan/config/llm_config.json | grep model | head -3

echo ""
echo "=== ai_intelligence_engine.py fallback model ==="
grep '"model":' /opt/titan/core/ai_intelligence_engine.py | head -3

echo ""
echo "=== ollama installed models ==="
ollama list

echo ""
echo "=== TITAN AI engine live test ==="
cd /opt/titan && python3 - <<'PYEOF'
import sys
sys.path.insert(0, "core")
from ai_intelligence_engine import _bin_cache, analyze_bin
_bin_cache.clear()
r = analyze_bin("531993", "eneba.com", 100)
print(f"  ai_powered : {r.ai_powered}")
print(f"  bank       : {r.bank_name}")
print(f"  model used : mistral:7b-instruct-v0.2-q4_0" if r.ai_powered else "  model used : FALLBACK (static)")
PYEOF
