#!/bin/bash
cd /opt/titan

python3 - << 'PYEOF'
import sys, time, json, urllib.request
sys.path.insert(0, "core")

OLLAMA = "http://127.0.0.1:11434/api/generate"

def raw_query(model, prompt, max_tokens=400):
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.15, "num_predict": max_tokens}
    }).encode()
    req = urllib.request.Request(OLLAMA, data=payload,
        headers={"Content-Type": "application/json"}, method="POST")
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=120) as resp:
        r = json.loads(resp.read())
        elapsed = time.time() - t0
        return r.get("response", ""), elapsed, r.get("eval_count", 0)

# ── Pull the EXACT prompts from ai_intelligence_engine.py ────────────────────
import ai_intelligence_engine as eng

# Patch to intercept the actual prompt sent
captured = {}
orig_query = eng._query_ollama_json
def capture_query(prompt, task_type="default", **kw):
    captured["prompt"] = prompt
    captured["task_type"] = task_type
    return orig_query(prompt, task_type=task_type, **kw)
eng._query_ollama_json = capture_query

print("╔══════════════════════════════════════════════════════════════════════╗")
print("║  HOW TITAN AI ANALYSIS WORKS — FULL TRACE                            ║")
print("╚══════════════════════════════════════════════════════════════════════╝")

# ── TEST 1: BIN ANALYSIS ─────────────────────────────────────────────────────
print()
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print("  [1] BIN ANALYSIS — analyze_bin('476173', 'nike.com', 180)")
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
eng._bin_cache.clear()
t0 = time.time()
result = eng.analyze_bin("476173", "nike.com", 180)
elapsed = time.time() - t0

print(f"\n  PROMPT SENT TO titan-mistral:")
print(f"  {'─'*60}")
for line in captured.get("prompt","").split("\n"):
    print(f"  {line}")
print(f"  {'─'*60}")

print(f"\n  RAW AI RESPONSE (what mistral returned):")
print(f"  {'─'*60}")
raw, _, _ = raw_query("titan-mistral", captured.get("prompt",""), 400)
for line in raw.split("\n"):
    print(f"  {line}")
print(f"  {'─'*60}")

print(f"\n  PARSED RESULT (AIBINAnalysis dataclass):")
print(f"    bank_name          : {result.bank_name}")
print(f"    country            : {result.country}")
print(f"    card_type          : {result.card_type}")
print(f"    risk_level         : {result.risk_level.value}")
print(f"    ai_score           : {result.ai_score}")
print(f"    success_prediction : {result.success_prediction}")
print(f"    timing_advice      : {result.timing_advice}")
print(f"    best_targets       : {result.best_targets}")
print(f"    avoid_targets      : {result.avoid_targets}")
print(f"    ai_powered         : {result.ai_powered}  ← True = real AI, False = static fallback")
print(f"    response_time      : {elapsed:.1f}s")

# ── TEST 2: TARGET RECON ─────────────────────────────────────────────────────
print()
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print("  [2] TARGET RECON — recon_target('stockx.com')")
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
eng._target_cache.clear()
captured.clear()
t0 = time.time()
result2 = eng.recon_target("stockx.com", "sneakers")
elapsed2 = time.time() - t0

print(f"\n  PROMPT SENT TO titan-mistral:")
print(f"  {'─'*60}")
for line in captured.get("prompt","").split("\n"):
    print(f"  {line}")
print(f"  {'─'*60}")

print(f"\n  PARSED RESULT (AITargetRecon dataclass):")
for field, val in result2.__dict__.items():
    print(f"    {field:<22} : {val}")
print(f"    response_time          : {elapsed2:.1f}s")

# ── HOW IT WORKS EXPLANATION ─────────────────────────────────────────────────
print()
print("╔══════════════════════════════════════════════════════════════════════╗")
print("║  HOW THE ANALYSIS PIPELINE WORKS                                     ║")
print("╠══════════════════════════════════════════════════════════════════════╣")
print("║                                                                      ║")
print("║  1. App calls analyze_bin(bin, target, amount)                       ║")
print("║  2. Engine checks _bin_cache (skip Ollama if cached)                 ║")
print("║  3. Looks up static BIN DB (bank name, country, card type)           ║")
print("║  4. Builds structured JSON prompt with static data as context        ║")
print("║  5. Sends prompt → ollama_bridge → llm_config.json routing           ║")
print("║  6. llm_config picks: titan-mistral (primary) → mistral (fallback)   ║")
print("║  7. titan-mistral returns JSON with risk/score/strategy fields        ║")
print("║  8. Engine parses JSON → fills AIBINAnalysis dataclass               ║")
print("║  9. Sets ai_powered=True, stores in cache                            ║")
print("║  10. App displays result in GUI tab                                  ║")
print("║                                                                      ║")
print("║  If Ollama fails at step 7 → static fallback (ai_powered=False)      ║")
print("╚══════════════════════════════════════════════════════════════════════╝")
PYEOF
