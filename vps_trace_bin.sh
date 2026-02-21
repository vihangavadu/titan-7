#!/bin/bash
cd /opt/titan

python3 - << 'PYEOF'
import sys, time, json, logging
sys.path.insert(0, "core")

logging.basicConfig(level=logging.DEBUG, format='%(name)s: %(message)s')

import ai_intelligence_engine as eng

# Patch _query_ollama_json to trace
orig = eng._query_ollama_json
def traced(prompt, task_type="default", **kw):
    print(f"[TRACE] _query_ollama_json task={task_type} timeout={kw.get('timeout',60)}")
    r = orig(prompt, task_type=task_type, **kw)
    print(f"[TRACE] result={type(r).__name__}: {str(r)[:150] if r else 'None'}")
    return r
eng._query_ollama_json = traced

eng._bin_cache.clear()
t0 = time.time()
r = eng.analyze_bin("476173", "nike.com", 180)
print(f"\nRESULT: ai_powered={r.ai_powered} bank={r.bank_name} time={time.time()-t0:.1f}s")
PYEOF
