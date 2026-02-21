#!/bin/bash
cd /opt/titan

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  TITAN — LLM MODEL BENCHMARK (find best model for this VPS)          ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""
echo "VPS: 8 CPU cores, 32GB RAM, no GPU — CPU inference only"
echo "Models installed: qwen2.5:7b | mistral:7b-instruct-v0.2-q4_0"
echo ""

python3 - <<'PYEOF'
import json, time, urllib.request, urllib.error, sys

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODELS = ["qwen2.5:7b", "mistral:7b-instruct-v0.2-q4_0"]

def query(model, prompt, max_tokens=300, temperature=0.1):
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
        with urllib.request.urlopen(req, timeout=120) as resp:
            r = json.loads(resp.read().decode())
            elapsed = time.time() - t0
            return {
                "text": r.get("response", ""),
                "tokens": r.get("eval_count", 0),
                "prompt_tokens": r.get("prompt_eval_count", 0),
                "elapsed": elapsed,
                "tok_per_sec": r.get("eval_count", 0) / max(elapsed, 0.1),
                "eval_duration_s": r.get("eval_duration", 0) / 1e9,
                "load_duration_s": r.get("load_duration", 0) / 1e9,
            }
    except Exception as e:
        return {"text": f"ERROR: {e}", "tokens": 0, "elapsed": 0, "tok_per_sec": 0,
                "eval_duration_s": 0, "load_duration_s": 0, "prompt_tokens": 0}

# ── TEST SUITE ────────────────────────────────────────────────────────────────
TESTS = [
    {
        "name": "T1: JSON structured output (BIN analysis)",
        "prompt": 'Analyze BIN 476173 for use on nike.com with $180 purchase. Respond ONLY with valid JSON: {"bank":"...","country":"...","card_type":"...","risk_score":0-100,"recommended":true/false,"reason":"..."}',
        "check": lambda r: r.strip().startswith("{") and "bank" in r and "risk_score" in r,
        "check_label": "Valid JSON with required fields"
    },
    {
        "name": "T2: Fraud engine detection (target recon)",
        "prompt": 'What fraud detection system does stockx.com use? Answer in one word only: Forter, Riskified, Sift, Kount, or Other.',
        "check": lambda r: any(x in r.lower() for x in ["forter","riskified","sift","kount","other"]),
        "check_label": "Returns known fraud engine name"
    },
    {
        "name": "T3: 3DS strategy (instruction following)",
        "prompt": 'For a $500 purchase on amazon.com with a Visa credit card, what 3DS bypass strategy should be used? Reply in exactly 2 sentences.',
        "check": lambda r: len(r.split(".")) >= 2 and len(r) > 50,
        "check_label": "2+ sentences, substantive answer"
    },
    {
        "name": "T4: Behavioral params (numeric output)",
        "prompt": 'For evading Forter fraud detection, give mouse speed range and typing WPM range. Respond ONLY with JSON: {"mouse_min":0,"mouse_max":0,"wpm_min":0,"wpm_max":0}',
        "check": lambda r: "mouse_min" in r and "wpm_min" in r,
        "check_label": "JSON with numeric behavioral params"
    },
    {
        "name": "T5: Speed test (short factual)",
        "prompt": 'What is a BIN number? Answer in exactly one sentence.',
        "check": lambda r: len(r) > 20 and len(r.split(".")) >= 1,
        "check_label": "Short factual answer"
    },
]

results = {}

for model in MODELS:
    print(f"\n{'═'*70}")
    print(f"  MODEL: {model}")
    print(f"{'═'*70}")
    results[model] = {"tests": [], "total_tokens": 0, "total_time": 0, "pass": 0}

    for test in TESTS:
        print(f"\n  {test['name']}")
        r = query(model, test["prompt"], max_tokens=250)
        passed = test["check"](r["text"]) if not r["text"].startswith("ERROR") else False
        results[model]["tests"].append({
            "name": test["name"],
            "passed": passed,
            "tokens": r["tokens"],
            "elapsed": r["elapsed"],
            "tok_per_sec": r["tok_per_sec"],
            "text_preview": r["text"][:120].replace("\n", " ")
        })
        results[model]["total_tokens"] += r["tokens"]
        results[model]["total_time"] += r["elapsed"]
        if passed:
            results[model]["pass"] += 1

        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"    {status} | {r['tokens']} tokens | {r['elapsed']:.1f}s | {r['tok_per_sec']:.1f} tok/s")
        print(f"    Check: {test['check_label']}")
        print(f"    Output: \"{r['text'][:100].strip()}...\"")

# ── COMPARISON SUMMARY ────────────────────────────────────────────────────────
print(f"\n\n{'═'*70}")
print("  BENCHMARK RESULTS SUMMARY")
print(f"{'═'*70}\n")

print(f"  {'Metric':<35} {'qwen2.5:7b':>15} {'mistral:7b':>15}")
print(f"  {'-'*65}")

for model in MODELS:
    r = results[model]
    avg_tps = r["total_tokens"] / max(r["total_time"], 0.1)
    r["avg_tps"] = avg_tps
    r["pass_rate"] = r["pass"] / len(TESTS) * 100

q = results["qwen2.5:7b"]
m = results["mistral:7b-instruct-v0.2-q4_0"]

print(f"  {'Tests passed':<35} {q['pass']}/{len(TESTS):>13} {m['pass']}/{len(TESTS):>13}")
print(f"  {'Pass rate':<35} {q['pass_rate']:>14.0f}% {m['pass_rate']:>14.0f}%")
print(f"  {'Total tokens generated':<35} {q['total_tokens']:>15} {m['total_tokens']:>15}")
print(f"  {'Total time (all 5 tests)':<35} {q['total_time']:>13.1f}s {m['total_time']:>13.1f}s")
print(f"  {'Avg tokens/sec':<35} {q['avg_tps']:>13.1f} {m['avg_tps']:>13.1f}")
print(f"  {'Avg time per test':<35} {q['total_time']/len(TESTS):>13.1f}s {m['total_time']/len(TESTS):>13.1f}s")

# ── VERDICT ───────────────────────────────────────────────────────────────────
print(f"\n{'═'*70}")
print("  VERDICT")
print(f"{'═'*70}\n")

q_score = q["pass_rate"] * 0.6 + min(q["avg_tps"] / 20 * 100, 100) * 0.4
m_score = m["pass_rate"] * 0.6 + min(m["avg_tps"] / 20 * 100, 100) * 0.4

print(f"  Composite score (60% quality + 40% speed):")
print(f"    qwen2.5:7b                  → {q_score:.1f}/100")
print(f"    mistral:7b-instruct-v0.2-q4 → {m_score:.1f}/100")
print()

if q_score > m_score:
    diff = q_score - m_score
    print(f"  🏆 WINNER: qwen2.5:7b  (+{diff:.1f} points)")
    print(f"  RECOMMENDATION: Set qwen2.5:7b as primary model in ai_intelligence_engine.py")
    winner = "qwen2.5:7b"
elif m_score > q_score:
    diff = m_score - q_score
    print(f"  🏆 WINNER: mistral:7b-instruct-v0.2-q4_0  (+{diff:.1f} points)")
    print(f"  RECOMMENDATION: Set mistral:7b as primary model in ai_intelligence_engine.py")
    winner = "mistral:7b-instruct-v0.2-q4_0"
else:
    print(f"  🤝 TIE — both models perform equally")
    winner = "qwen2.5:7b"

print()
print(f"  Current primary model in ai_intelligence_engine.py:")
import subprocess
cur = subprocess.run(["grep", "-n", "PRIMARY_MODEL\|qwen\|mistral\|model.*=", 
                      "/opt/titan/core/ai_intelligence_engine.py"],
                     capture_output=True, text=True)
for line in cur.stdout.strip().split("\n")[:5]:
    print(f"    {line}")

PYEOF

echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  BENCHMARK COMPLETE                                                   ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
