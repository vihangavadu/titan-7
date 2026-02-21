#!/bin/bash
# TITAN V7.5 — Deep Hardcoded Values & Ollama Hookup Scan
cd /opt/titan

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  HARDCODED VALUES & OLLAMA HOOKUP AUDIT                              ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"

########################################################################
# 1. SCAN AI ENGINE FOR HARDCODED FALLBACKS vs REAL OLLAMA CALLS
########################################################################
echo ""
echo "═══ [1] AI ENGINE — HARDCODED vs OLLAMA ═══"
echo ""
echo "  ai_intelligence_engine.py:"
echo "    Ollama calls (real AI):"
grep -n "ollama_bridge\|_call_ollama\|_query_llm\|requests.post.*11434\|generate\|chat" core/ai_intelligence_engine.py | head -20
echo ""
echo "    Hardcoded fallback data:"
grep -n "fallback\|FALLBACK\|default_\|hardcoded\|static\|_mock\|fake_" core/ai_intelligence_engine.py | head -20
echo ""
echo "    Hardcoded BIN data:"
grep -n "'421783'\|'455360'\|'476173'\|'531993'\|'552289'" core/ai_intelligence_engine.py | head -10
echo ""
echo "    Hardcoded target data:"
grep -n "'amazon\|'eneba\|'g2a\|'steam\|'shopify" core/ai_intelligence_engine.py | head -10
echo ""
echo "    Hardcoded scores/percentages:"
grep -n "= 0\.\|= 65\|= 70\|= 75\|= 80\|= 85\|= 50\|= 100" core/ai_intelligence_engine.py | grep -v "range\|setRange\|import\|#" | head -15

echo ""
echo "═══ [2] OLLAMA BRIDGE — ACTUAL API CALLS ═══"
echo ""
echo "  ollama_bridge.py:"
echo "    HTTP calls:"
grep -n "requests\.\|urllib\|http\|11434\|/api/" core/ollama_bridge.py | head -15
echo ""
echo "    Model references:"
grep -n "qwen\|mistral\|llama\|model" core/ollama_bridge.py | head -10
echo ""
echo "    Hardcoded responses:"
grep -n "hardcoded\|fallback\|mock\|fake\|static.*response\|default.*response" core/ollama_bridge.py | head -10

########################################################################
# 3. TRACE: Does analyze_bin() ACTUALLY call Ollama?
########################################################################
echo ""
echo "═══ [3] TRACE: analyze_bin() FLOW ═══"
python3 - <<'PYEOF'
import sys, json
sys.path.insert(0, "core")

# Monkey-patch requests to see if Ollama is actually called
import requests
original_post = requests.post
calls = []

def tracking_post(url, **kwargs):
    calls.append({"url": url, "data_keys": list(kwargs.get("json", {}).keys()) if isinstance(kwargs.get("json"), dict) else "raw"})
    return original_post(url, **kwargs)

requests.post = tracking_post

from ai_intelligence_engine import analyze_bin, recon_target, advise_3ds, tune_behavior

print("  Testing analyze_bin('421783', 'eneba.com', 150)...")
calls.clear()
b = analyze_bin("421783", "eneba.com", 150)
print(f"    Ollama calls made: {len(calls)}")
for c in calls:
    print(f"      POST {c['url']} keys={c['data_keys']}")
print(f"    ai_powered: {b.ai_powered}")
print(f"    Result: score={b.ai_score} bank={b.bank_name}")

print()
print("  Testing recon_target('amazon.com')...")
calls.clear()
t = recon_target("amazon.com")
print(f"    Ollama calls made: {len(calls)}")
for c in calls:
    print(f"      POST {c['url']} keys={c['data_keys']}")
print(f"    ai_powered: {t.ai_powered}")
print(f"    Result: fraud={t.fraud_engine_guess} psp={t.payment_processor_guess}")

print()
print("  Testing advise_3ds('421783', 'eneba.com', 150)...")
calls.clear()
s = advise_3ds("421783", "eneba.com", 150)
print(f"    Ollama calls made: {len(calls)}")
for c in calls:
    print(f"      POST {c['url']} keys={c['data_keys']}")
print(f"    ai_powered: {s.ai_powered}")

print()
print("  Testing tune_behavior('amazon.com')...")
calls.clear()
bh = tune_behavior("amazon.com")
print(f"    Ollama calls made: {len(calls)}")
for c in calls:
    print(f"      POST {c['url']} keys={c['data_keys']}")
print(f"    ai_powered: {bh.ai_powered}")

requests.post = original_post
PYEOF

########################################################################
# 4. SCAN APPS FOR HARDCODED VALUES IN AI CALLS
########################################################################
echo ""
echo "═══ [4] APPS — HARDCODED VALUES IN AI CALLS ═══"
echo ""
echo "  app_unified.py — AI handler calls:"
grep -n "analyze_bin\|recon_target\|advise_3ds\|tune_behavior\|plan_operation\|audit_profile" apps/app_unified.py | grep -v "def \|import \|#\|placeholder\|Placeholder" | head -20
echo ""
echo "  Hardcoded fallback BINs in AI calls (should use self.ai_*_input):"
grep -n "\"421783\"\|'421783'" apps/app_unified.py | head -5
echo ""
echo "  app_cerberus.py — AI handler calls:"
grep -n "analyze_bin\|recon_target\|advise_3ds" apps/app_cerberus.py | grep -v "def \|import \|#\|placeholder" | head -10
echo ""
echo "  Hardcoded fallback BINs:"
grep -n "\"421783\"\|'421783'" apps/app_cerberus.py | head -5

########################################################################
# 5. CHECK: Are results dynamic or always the same?
########################################################################
echo ""
echo "═══ [5] DYNAMIC OUTPUT TEST — Same input, different BINs ═══"
python3 - <<'PYEOF'
import sys
sys.path.insert(0, "core")
from ai_intelligence_engine import analyze_bin, recon_target

# Test with different BINs — should give different results
bins = ["421783", "455360", "531993", "376211", "601100"]
print("  BIN analysis across 5 different BINs:")
for b in bins:
    r = analyze_bin(b, "amazon.com", 200)
    print(f"    {b}: bank={r.bank_name:20s} score={r.ai_score:5.1f} risk={r.risk_level.value:8s} success={r.success_prediction:.0%}")

# Test with different targets — should give different results
targets = ["amazon.com", "eneba.com", "g2a.com", "steam.com", "walmart.com"]
print()
print("  Target recon across 5 different targets:")
for t in targets:
    r = recon_target(t)
    print(f"    {t:15s}: fraud={r.fraud_engine_guess:12s} psp={r.payment_processor_guess:10s} 3ds={r.three_ds_probability:.0%}")
PYEOF

########################################################################
# 6. CHECK: Ollama is actually running and responding
########################################################################
echo ""
echo "═══ [6] OLLAMA LIVE STATUS ═══"
echo "  Service: $(systemctl is-active ollama)"
echo "  Models loaded:"
curl -s http://127.0.0.1:11434/api/tags 2>/dev/null | python3 -c "
import sys,json
try:
    d=json.load(sys.stdin)
    for m in d.get('models',[]):
        print(f\"    {m['name']}: {m['size']/1e9:.1f}GB\")
except: print('    Error reading models')
"
echo ""
echo "  Quick inference test:"
curl -s http://127.0.0.1:11434/api/generate -d '{"model":"qwen2.5:7b","prompt":"What is 2+2? Answer with just the number.","stream":false,"options":{"num_predict":5}}' 2>/dev/null | python3 -c "
import sys,json
try:
    d=json.load(sys.stdin)
    print(f\"    Response: {d.get('response','').strip()}\")
    print(f\"    Tokens: {d.get('eval_count',0)}\")
    print(f\"    Speed: {d.get('eval_count',0)/(d.get('eval_duration',1)/1e9):.1f} tok/s\")
except: print('    Ollama not responding')
"

echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  HARDCODE AUDIT COMPLETE                                             ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
