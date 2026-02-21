#!/bin/bash
cd /opt/titan

python3 - << 'PYEOF'
import sys, time, json, urllib.request
sys.path.insert(0, "core")

OLLAMA = "http://127.0.0.1:11434/api/generate"

def query(model, prompt, max_tokens=300):
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.15, "num_predict": max_tokens}
    }).encode()
    req = urllib.request.Request(OLLAMA, data=payload,
        headers={"Content-Type": "application/json"}, method="POST")
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            r = json.loads(resp.read())
            elapsed = time.time() - t0
            tokens = r.get("eval_count", 0)
            return elapsed, tokens, tokens / max(elapsed, 0.01)
    except Exception as e:
        return time.time() - t0, 0, 0

print("╔══════════════════════════════════════════════════════════════════════╗")
print("║  TITAN OS — RESPONSE TIME BENCHMARK (titan-mistral)                  ║")
print("╚══════════════════════════════════════════════════════════════════════╝")
print()

TASKS = [
    ("BIN Analysis (JSON)",
     'Analyze BIN 476173 for nike.com $180. JSON only: {"bank_name":"...","country":"...","card_type":"...","risk_level":"low/medium/high","ai_score":0-100,"success_prediction":0.0-1.0,"timing_advice":"...","strategic_notes":"...","best_targets":[],"avoid_targets":[]}'),

    ("Target Recon (JSON)",
     'Analyze stockx.com for card testing. JSON only: {"fraud_engine":"...","risk_score":0-100,"detection_methods":[],"recommended_approach":"...","success_rate":0.0-1.0}'),

    ("3DS Strategy (JSON)",
     'Give 3DS bypass strategy for $500 amazon.com Visa. JSON only: {"approach":"...","success_probability":0.0-1.0,"timing_window":"...","amount_strategy":"..."}'),

    ("Behavioral Params (JSON)",
     'Forter evasion behavioral params. JSON only: {"mouse_speed_range":[min,max],"click_delay_ms":[min,max],"typing_wpm_range":[min,max],"typing_error_rate":0.0-1.0,"scroll_behavior":"...","form_fill_strategy":"..."}'),

    ("Operation Plan (text)",
     'Create a brief 3-step operation plan for testing a Visa card on a medium-risk e-commerce site. Be concise.'),

    ("Profile Audit (JSON)",
     'Audit this profile for fraud detection risk. Name: John Smith, DOB: 1990-05-15, Email: jsmith90@gmail.com. JSON only: {"risk_score":0-100,"flags":[],"recommendations":[],"overall_assessment":"..."}'),

    ("Short answer (speed test)",
     'What is a BIN number? One sentence.'),
]

results = []
total_time = 0

print(f"  {'Task':<30} {'Time':>8} {'Tokens':>8} {'Tok/s':>8}  Status")
print(f"  {'─'*65}")

for name, prompt in TASKS:
    elapsed, tokens, tps = query("titan-mistral", prompt)
    total_time += elapsed
    status = "✅" if elapsed < 60 and tokens > 0 else "⚠️ " if elapsed >= 60 else "❌"
    results.append((name, elapsed, tokens, tps))
    print(f"  {status} {name:<30} {elapsed:>6.1f}s {tokens:>7} {tps:>7.1f}")

print(f"  {'─'*65}")
print(f"  {'TOTAL / AVERAGE':<30} {total_time:>6.1f}s {'':>7} {sum(r[3] for r in results)/len(results):>7.1f}")

avg_time = total_time / len(TASKS)
avg_tps  = sum(r[3] for r in results) / len(results)

print()
print("╔══════════════════════════════════════════════════════════════════════╗")
print("║  SUMMARY                                                             ║")
print("╠══════════════════════════════════════════════════════════════════════╣")
print(f"║  Average response time : {avg_time:>6.1f}s per task                          ║")
print(f"║  Average throughput    : {avg_tps:>6.1f} tokens/sec                         ║")
print(f"║  Total benchmark time  : {total_time:>6.1f}s ({len(TASKS)} tasks)                      ║")
print(f"║  Model                 : titan-mistral (mistral:7b q4_0 TITAN-tuned) ║")
print(f"║  Hardware              : 8 CPU cores, 32GB RAM, no GPU (CPU only)    ║")

# Rating
if avg_time < 20:
    rating = "EXCELLENT ⚡"
elif avg_time < 35:
    rating = "GOOD ✅"
elif avg_time < 60:
    rating = "ACCEPTABLE ⚠️"
else:
    rating = "SLOW ❌"

print(f"║  Rating                : {rating:<44}║")
print("╚══════════════════════════════════════════════════════════════════════╝")
PYEOF
