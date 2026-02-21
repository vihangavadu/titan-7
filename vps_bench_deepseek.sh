#!/bin/bash
cd /opt/titan

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  deepseek-r1:8b vs mistral:7b — HEAD TO HEAD                         ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""

python3 - <<'PYEOF'
import json, time, urllib.request

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"

def query(model, prompt, max_tokens=250, temperature=0.1, timeout=120):
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature, "num_predict": max_tokens}
    }).encode()
    req = urllib.request.Request(OLLAMA_URL, data=payload,
                                  headers={"Content-Type": "application/json"}, method="POST")
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            r = json.loads(resp.read().decode())
            elapsed = time.time() - t0
            tokens = r.get("eval_count", 0)
            return {
                "text": r.get("response", "").strip(),
                "tokens": tokens,
                "elapsed": elapsed,
                "tps": tokens / max(elapsed, 0.1),
                "ok": True
            }
    except Exception as e:
        return {"text": f"ERROR: {e}", "tokens": 0, "elapsed": 0, "tps": 0, "ok": False}

MODELS = ["deepseek-r1:8b", "mistral:7b-instruct-v0.2-q4_0"]

TESTS = [
    {
        "name": "T1: JSON BIN analysis",
        "prompt": 'Analyze BIN 476173 for nike.com $180. Respond ONLY with JSON (no markdown, no thinking): {"bank_name":"...","country":"...","card_type":"...","risk_level":"low/medium/high","ai_score":0-100,"success_prediction":0.0-1.0,"timing_advice":"...","strategic_notes":"...","best_targets":[],"avoid_targets":[]}',
        "check": lambda r: "{" in r and "bank_name" in r and "risk_level" in r,
        "weight": 3
    },
    {
        "name": "T2: Fraud engine ID",
        "prompt": "What fraud detection system does stockx.com use? Answer with ONE word only from: Forter, Riskified, Sift, Kount, Other.",
        "check": lambda r: any(x in r.lower() for x in ["forter","riskified","sift","kount","other"]) and len(r.split()) <= 5,
        "weight": 2
    },
    {
        "name": "T3: 3DS strategy",
        "prompt": 'For $500 on amazon.com Visa credit card, give 3DS strategy. JSON only: {"approach":"...","success_probability":0.0-1.0,"timing_window":"...","amount_strategy":"..."}',
        "check": lambda r: "{" in r and "approach" in r,
        "weight": 2
    },
    {
        "name": "T4: Behavioral params",
        "prompt": 'Forter evasion behavioral params. JSON only: {"mouse_speed_range":[min,max],"click_delay_ms":[min,max],"typing_wpm_range":[min,max],"typing_error_rate":0.0-1.0,"scroll_behavior":"...","form_fill_strategy":"..."}',
        "check": lambda r: "{" in r and "mouse_speed_range" in r,
        "weight": 2
    },
    {
        "name": "T5: Speed (short answer)",
        "prompt": "What is a payment card BIN? One sentence only.",
        "check": lambda r: len(r) > 20 and len(r) < 300,
        "weight": 1
    },
]

results = {}

for model in MODELS:
    print(f"\n{'═'*68}")
    print(f"  MODEL: {model}")
    print(f"{'═'*68}")
    results[model] = {"pass": 0, "total_tps": 0, "total_time": 0, "weighted_score": 0, "tests": []}

    for test in TESTS:
        r = query(model, test["prompt"])
        # Strip deepseek <think> tags from response
        text = r["text"]
        if "<think>" in text:
            # Remove chain-of-thought, keep only final answer
            if "</think>" in text:
                text = text.split("</think>")[-1].strip()
        
        passed = test["check"](text) if r["ok"] else False
        results[model]["tests"].append({
            "name": test["name"],
            "passed": passed,
            "tps": r["tps"],
            "elapsed": r["elapsed"],
            "text": text[:120]
        })
        if passed:
            results[model]["pass"] += 1
            results[model]["weighted_score"] += test["weight"]
        results[model]["total_tps"] += r["tps"]
        results[model]["total_time"] += r["elapsed"]

        icon = "✅" if passed else "❌"
        print(f"  {icon} {test['name']:<28} {r['tps']:>5.1f} tok/s | {r['elapsed']:>5.1f}s")
        print(f"     → {text[:90].replace(chr(10),' ')}")

# ── COMPARISON ────────────────────────────────────────────────────────────────
print(f"\n\n{'═'*68}")
print("  HEAD TO HEAD RESULTS")
print(f"{'═'*68}\n")

ds = results["deepseek-r1:8b"]
ms = results["mistral:7b-instruct-v0.2-q4_0"]
total_weight = sum(t["weight"] for t in TESTS)

ds_avg_tps = ds["total_tps"] / len(TESTS)
ms_avg_tps = ms["total_tps"] / len(TESTS)

print(f"  {'Metric':<35} {'deepseek-r1:8b':>15} {'mistral:7b':>12}")
print(f"  {'─'*65}")
print(f"  {'Tasks passed':<35} {ds['pass']}/{len(TESTS):>13} {ms['pass']}/{len(TESTS):>10}")
print(f"  {'Weighted quality score':<35} {ds['weighted_score']}/{total_weight:>11} {ms['weighted_score']}/{total_weight:>8}")
print(f"  {'Avg tokens/sec':<35} {ds_avg_tps:>14.1f} {ms_avg_tps:>11.1f}")
print(f"  {'Total time (5 tests)':<35} {ds['total_time']:>13.1f}s {ms['total_time']:>10.1f}s")

# Composite: 60% quality, 40% speed
max_tps = max(ds_avg_tps, ms_avg_tps)
ds_score = (ds["weighted_score"] / total_weight * 100) * 0.6 + (ds_avg_tps / max_tps * 100) * 0.4
ms_score = (ms["weighted_score"] / total_weight * 100) * 0.6 + (ms_avg_tps / max_tps * 100) * 0.4

print(f"\n  Composite score (60% quality + 40% speed):")
print(f"    deepseek-r1:8b              → {ds_score:.1f}/100")
print(f"    mistral:7b-instruct-v0.2-q4 → {ms_score:.1f}/100")

print(f"\n{'═'*68}")
if ds_score > ms_score:
    diff = ds_score - ms_score
    print(f"  🏆 WINNER: deepseek-r1:8b  (+{diff:.1f} pts)")
    print(f"  ACTION: Switching primary model to deepseek-r1:8b")
    winner = "deepseek-r1:8b"
else:
    diff = ms_score - ds_score
    print(f"  🏆 WINNER: mistral:7b-instruct-v0.2-q4_0  (+{diff:.1f} pts)")
    print(f"  ACTION: Keeping mistral as primary (deepseek did not beat it)")
    winner = "mistral:7b-instruct-v0.2-q4_0"

print(f"{'═'*68}")

# Write winner to file for shell to pick up
with open("/tmp/llm_winner.txt", "w") as f:
    f.write(winner)
PYEOF

# Read winner and apply to config
WINNER=$(cat /tmp/llm_winner.txt 2>/dev/null)
echo ""
echo "Applying winner: $WINNER"

python3 - <<PYEOF2
import json

winner = open("/tmp/llm_winner.txt").read().strip()
cfg_path = "/opt/titan/config/llm_config.json"

with open(cfg_path) as f:
    cfg = json.load(f)

entry = {"provider": "ollama", "model": winner}

for task in cfg["task_routing"]:
    if task == "_doc":
        continue
    others = [e for e in cfg["task_routing"][task] if e.get("provider") != "ollama"]
    cfg["task_routing"][task] = [entry] + others

cfg["providers"]["ollama"]["default_model"] = winner

with open(cfg_path, "w") as f:
    json.dump(cfg, f, indent=2)

print(f"  ✅ llm_config.json updated — primary: {winner}")
PYEOF2

# Also update ai_intelligence_engine.py fallback
WINNER=$(cat /tmp/llm_winner.txt 2>/dev/null)
sed -i "s/\"model\": \"mistral:7b-instruct-v0.2-q4_0\"/\"model\": \"$WINNER\"/" /opt/titan/core/ai_intelligence_engine.py
sed -i "s/\"model\": \"qwen2.5:7b\"/\"model\": \"$WINNER\"/" /opt/titan/core/ai_intelligence_engine.py
echo "  ✅ ai_intelligence_engine.py fallback updated to: $WINNER"

echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  BENCHMARK COMPLETE — PRIMARY MODEL UPDATED                          ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
