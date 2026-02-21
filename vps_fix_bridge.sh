#!/bin/bash
cd /opt/titan

echo "=== Diagnosing analyze_bin fallback ==="

python3 - << 'PYEOF'
import sys, time, json, logging
sys.path.insert(0, "core")

# Enable debug to see what's happening
logging.basicConfig(level=logging.DEBUG, format='%(name)s: %(message)s')

# Test bridge directly first
from ollama_bridge import query_llm, query_llm_json, _check_ollama

print(f"Ollama available: {_check_ollama()}")

# Test titan-mistral directly
t0 = time.time()
r = query_llm('Say OK', task_type="bin_generation", timeout=60)
print(f"Direct bridge test: {r[:50] if r else 'None'} ({time.time()-t0:.1f}s)")

# Test JSON query
t0 = time.time()
r2 = query_llm_json('{"test": "ok"}', task_type="bin_generation", timeout=60)
print(f"JSON bridge test: {r2} ({time.time()-t0:.1f}s)")
PYEOF
