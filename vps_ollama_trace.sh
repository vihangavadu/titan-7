#!/bin/bash
# Real Ollama trace — verify AI engine actually calls Ollama now
cd /opt/titan

python3 -m compileall -q -f core/ai_intelligence_engine.py 2>/dev/null

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  OLLAMA REAL CALL TRACE                                              ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"

# Clear any caches first
python3 - <<'PYEOF'
import sys, time, logging, subprocess, json
sys.path.insert(0, "core")
logging.basicConfig(level=logging.INFO, format="[%(name)s] %(message)s")

# Flush module caches
import importlib
if "ai_intelligence_engine" in sys.modules:
    importlib.reload(sys.modules["ai_intelligence_engine"])

from ai_intelligence_engine import (
    analyze_bin, recon_target, advise_3ds, tune_behavior,
    _bin_cache, _target_cache, _is_ollama_available
)

# Clear all caches
_bin_cache.clear()
_target_cache.clear()

print(f"\n  Ollama available: {_is_ollama_available()}")

# Monkey-patch subprocess to trace curl calls to Ollama
original_run = subprocess.run
ollama_calls = []

def tracing_run(args, **kwargs):
    if isinstance(args, list) and any("11434" in str(a) for a in args):
        ollama_calls.append({"cmd": " ".join(str(a)[:60] for a in args[:5]), "time": time.time()})
    return original_run(args, **kwargs)

subprocess.run = tracing_run

# Also patch urllib
import urllib.request
original_urlopen = urllib.request.urlopen

def tracing_urlopen(req, **kwargs):
    url = req if isinstance(req, str) else getattr(req, 'full_url', str(req))
    if "11434" in str(url):
        ollama_calls.append({"cmd": f"urllib {url}", "time": time.time()})
    return original_urlopen(req, **kwargs)

urllib.request.urlopen = tracing_urlopen

# Test 1: analyze_bin with UNKNOWN BIN (forces Ollama)
print("\n═══ TEST 1: analyze_bin('529483', 'bestbuy.com', 299) ═══")
ollama_calls.clear()
t0 = time.time()
b = analyze_bin("529483", "bestbuy.com", 299)
elapsed = time.time() - t0
print(f"  Ollama calls: {len(ollama_calls)}")
for c in ollama_calls:
    print(f"    → {c['cmd']}")
print(f"  ai_powered: {b.ai_powered}")
print(f"  Result: bank={b.bank_name} score={b.ai_score} risk={b.risk_level.value}")
print(f"  Time: {elapsed:.1f}s")

# Test 2: recon_target with KNOWN target (should STILL call Ollama now)
print("\n═══ TEST 2: recon_target('amazon.com') — known target ═══")
ollama_calls.clear()
t0 = time.time()
t = recon_target("amazon.com")
elapsed = time.time() - t0
print(f"  Ollama calls: {len(ollama_calls)}")
for c in ollama_calls:
    print(f"    → {c['cmd']}")
print(f"  ai_powered: {t.ai_powered}")
print(f"  Result: fraud={t.fraud_engine_guess} psp={t.payment_processor_guess}")
print(f"  Time: {elapsed:.1f}s")

# Test 3: recon_target with UNKNOWN target
print("\n═══ TEST 3: recon_target('stockx.com') — unknown target ═══")
ollama_calls.clear()
t0 = time.time()
t2 = recon_target("stockx.com")
elapsed = time.time() - t0
print(f"  Ollama calls: {len(ollama_calls)}")
for c in ollama_calls:
    print(f"    → {c['cmd']}")
print(f"  ai_powered: {t2.ai_powered}")
print(f"  Result: fraud={t2.fraud_engine_guess} psp={t2.payment_processor_guess}")
print(f"  Time: {elapsed:.1f}s")

# Test 4: advise_3ds
print("\n═══ TEST 4: advise_3ds('529483', 'bestbuy.com', 299) ═══")
ollama_calls.clear()
t0 = time.time()
s = advise_3ds("529483", "bestbuy.com", 299)
elapsed = time.time() - t0
print(f"  Ollama calls: {len(ollama_calls)}")
for c in ollama_calls:
    print(f"    → {c['cmd']}")
print(f"  ai_powered: {s.ai_powered}")
print(f"  Result: approach={s.recommended_approach} success={s.success_probability:.0%}")
print(f"  Time: {elapsed:.1f}s")

# Test 5: tune_behavior
print("\n═══ TEST 5: tune_behavior('amazon.com', 'forter') ═══")
ollama_calls.clear()
t0 = time.time()
bh = tune_behavior("amazon.com", fraud_engine="forter")
elapsed = time.time() - t0
print(f"  Ollama calls: {len(ollama_calls)}")
for c in ollama_calls:
    print(f"    → {c['cmd']}")
print(f"  ai_powered: {bh.ai_powered}")
print(f"  Result: typing={bh.typing_wpm_range} mouse={bh.mouse_speed_range}")
print(f"  Time: {elapsed:.1f}s")

# Restore
subprocess.run = original_run
urllib.request.urlopen = original_urlopen

# Summary
print("\n═══ SUMMARY ═══")
print(f"  Hardcoded '421783' in app_unified: {open('apps/app_unified.py').read().count('421783')}")
print(f"  Hardcoded '421783' in app_cerberus: {open('apps/app_cerberus.py').read().count('421783')}")
print(f"  Hardcoded '421783' in ai_engine: {open('core/ai_intelligence_engine.py').read().count('421783')}")
PYEOF

echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  TRACE COMPLETE                                                      ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
