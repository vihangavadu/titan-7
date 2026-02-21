#!/bin/bash
cd /opt/titan

python3 - <<'PYEOF'
import sys, json, logging
sys.path.insert(0, "core")

# Enable debug logging to see what's happening
logging.basicConfig(level=logging.DEBUG, format='%(name)s: %(message)s')

# Patch _query_ollama_json to trace what it returns
import ai_intelligence_engine as eng

original_query = eng._query_ollama_json

def traced_query(prompt, task_type="default", **kwargs):
    print(f"\n[TRACE] _query_ollama_json called")
    print(f"[TRACE] task_type={task_type}")
    print(f"[TRACE] prompt[:100]={prompt[:100]}")
    result = original_query(prompt, task_type=task_type, **kwargs)
    print(f"[TRACE] result type={type(result)}")
    print(f"[TRACE] result={str(result)[:200] if result else 'None'}")
    return result

eng._query_ollama_json = traced_query

# Also trace the bridge
from ollama_bridge import _query_ollama as bridge_ollama
import ollama_bridge

original_bridge = ollama_bridge._query_ollama

def traced_bridge(prompt, model, temperature, max_tokens, timeout):
    print(f"\n[BRIDGE] _query_ollama called model={model} timeout={timeout}")
    result = original_bridge(prompt, model, temperature, max_tokens, timeout)
    print(f"[BRIDGE] result={str(result)[:200] if result else 'None'}")
    return result

ollama_bridge._query_ollama = traced_bridge

# Clear cache and run
eng._bin_cache.clear()
print("\n=== Running analyze_bin ===")
r = eng.analyze_bin("476173", "nike.com", 150)
print(f"\n=== RESULT ===")
print(f"ai_powered: {r.ai_powered}")
print(f"ai_score: {r.ai_score}")
print(f"bank: {r.bank_name}")
PYEOF
