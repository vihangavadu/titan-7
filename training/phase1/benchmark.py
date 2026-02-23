#!/usr/bin/env python3
"""Phase 1 benchmark: Test new V8.3 models on representative queries."""
import requests
import json
import time

OLLAMA_URL = "http://localhost:11434/api/generate"

tests = [
    {
        "model": "titan-analyst",
        "name": "BIN Analysis",
        "prompt": "Analyze BIN 421783 for target eneba.com, amount 150. Provide complete BIN intelligence as JSON."
    },
    {
        "model": "titan-analyst",
        "name": "Fingerprint Coherence",
        "prompt": 'Validate fingerprint coherence for this config: {"user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131", "webgl_renderer": "Mesa DRI Intel(R) UHD Graphics 630", "hardware_concurrency": 32, "screen_resolution": "1920x1080", "timezone": "America/New_York", "locale": "en-US", "platform": "Win32"}'
    },
    {
        "model": "titan-strategist",
        "name": "Decline Autopsy",
        "prompt": "Perform decline autopsy: code=card_declined, category=fraud_block, target=stockx.com, psp=stripe, amount=220, bin=414720 (Chase Visa), proxy=US residential, profile_age=45 days, session_duration=95s"
    },
    {
        "model": "titan-fast",
        "name": "Copilot Advice",
        "prompt": "My checkout was declined on Eneba with code card_declined. BIN 421783, amount 85 USD. What happened and what should I do?"
    },
    {
        "model": "titan-analyst",
        "name": "Identity Graph",
        "prompt": 'Validate identity graph plausibility: {"name": "Takeshi Yamamoto", "email": "takeshi.y@gmail.com", "phone": "+1-205-555-0142", "street": "4521 County Road 12", "city": "Tuscaloosa", "state": "AL", "zip": "35401", "card_bin": "421783", "card_network": "visa"}'
    },
]

print("=" * 70)
print("TITAN V8.3 — Phase 1 Model Benchmark")
print("=" * 70)

results = []
for test in tests:
    t0 = time.time()
    try:
        r = requests.post(OLLAMA_URL, json={
            "model": test["model"],
            "prompt": test["prompt"],
            "stream": False,
        }, timeout=180)
        data = r.json()
        resp = data.get("response", "")
        elapsed = time.time() - t0

        # Check if response is valid JSON
        is_json = False
        try:
            # Try to extract JSON
            import re
            match = re.search(r'\{.*\}', resp, re.DOTALL)
            if match:
                json.loads(match.group())
                is_json = True
        except Exception:
            pass

        print(f"\n{'='*70}")
        print(f"TEST: {test['name']} | Model: {test['model']} | Time: {elapsed:.1f}s | JSON: {'YES' if is_json else 'NO'}")
        print(f"{'='*70}")
        print(resp[:800])
        if len(resp) > 800:
            print(f"... ({len(resp)} chars total)")

        results.append({
            "name": test["name"],
            "model": test["model"],
            "time_s": round(elapsed, 1),
            "response_len": len(resp),
            "is_json": is_json,
        })
    except Exception as e:
        elapsed = time.time() - t0
        print(f"\nERROR: {test['name']} ({test['model']}): {e}")
        results.append({
            "name": test["name"],
            "model": test["model"],
            "time_s": round(elapsed, 1),
            "response_len": 0,
            "is_json": False,
            "error": str(e)[:100],
        })

print(f"\n{'='*70}")
print("BENCHMARK SUMMARY")
print(f"{'='*70}")
for r in results:
    status = "OK-JSON" if r.get("is_json") else ("OK-TEXT" if r.get("response_len", 0) > 0 else "FAIL")
    print(f"  {r['name']:25s} | {r['model']:20s} | {r['time_s']:5.1f}s | {r['response_len']:5d} chars | {status}")

avg_time = sum(r["time_s"] for r in results) / len(results) if results else 0
json_rate = sum(1 for r in results if r.get("is_json")) / len(results) * 100 if results else 0
print(f"\nAvg response time: {avg_time:.1f}s")
print(f"JSON validity rate: {json_rate:.0f}%")

# Save results
with open("/opt/titan/training/phase1/benchmark_results.json", "w") as f:
    json.dump({"results": results, "avg_time_s": avg_time, "json_rate_pct": json_rate}, f, indent=2)
print(f"Results saved to /opt/titan/training/phase1/benchmark_results.json")
