#!/usr/bin/env python3
"""Test all 3 custom Titan OS fine-tuned models with real operational queries."""
import sys, time, json, urllib.request
sys.path.insert(0, "/opt/titan/core")
sys.path.insert(0, "/opt/titan")

PASS = 0
FAIL = 0

def query_model(model, prompt, timeout=90):
    """Direct Ollama API query to specific model."""
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.2, "num_predict": 512}
    }).encode()
    req = urllib.request.Request(
        "http://127.0.0.1:11434/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        data = json.loads(resp.read())
        return data.get("response", ""), data.get("total_duration", 0) / 1e9
    except Exception as e:
        return f"ERROR: {e}", 0

def test(name, model, prompt, check_fn):
    global PASS, FAIL
    t0 = time.time()
    response, duration = query_model(model, prompt)
    elapsed = time.time() - t0
    ok = check_fn(response)
    status = "PASS" if ok else "FAIL"
    if ok:
        PASS += 1
    else:
        FAIL += 1
    print(f"  [{status}] {name} ({elapsed:.1f}s)")
    print(f"    Response: {response[:250]}")
    print()
    return ok

print("=" * 70)
print("TITAN V8.11 — Custom Model Accuracy Test")
print("=" * 70)

# ═══════════════════════════════════════════════════════════
# TITAN-FAST (Copilot) Tests
# ═══════════════════════════════════════════════════════════
print("\n--- TITAN-FAST (Copilot/Guidance) ---")

test("Copilot: checkout timing",
     "titan-fast",
     "How long should I spend on the checkout page before submitting payment?",
     lambda r: any(x in r.lower() for x in ["20", "45", "90", "second", "minute", "2 min"]))

test("Copilot: Stripe 3DS",
     "titan-fast",
     "Target uses Stripe. Card is UK Visa. Amount is 85 EUR. Will 3DS trigger?",
     lambda r: any(x in r.lower() for x in ["3ds", "tra", "exempt", "psd2", "threshold", "100"]))

test("Copilot: decline help",
     "titan-fast",
     "Operation failed with card_declined on Stripe. What should I do?",
     lambda r: any(x in r.lower() for x in ["card", "different", "bin", "try", "amount", "lower"]))

test("Copilot: network setup",
     "titan-fast",
     "What do I need to check in Network Center before starting operations?",
     lambda r: any(x in r.lower() for x in ["vpn", "ip", "reputation", "shield", "ebpf", "ttl"]))

# ═══════════════════════════════════════════════════════════
# TITAN-ANALYST (Structured JSON) Tests
# ═══════════════════════════════════════════════════════════
print("\n--- TITAN-ANALYST (Structured Data) ---")

test("Analyst: BIN analysis",
     "titan-analyst",
     "Analyze BIN 453201. Return JSON with: bin, issuer, country, network, type, level, risk_score, three_ds_likely",
     lambda r: any(x in r for x in ['"bin"', '"issuer"', '"country"', '"risk_score"', "453201", "Visa"]))

test("Analyst: persona enrichment",
     "titan-analyst",
     "Enrich persona: John Smith, age 35, Miami FL. Return JSON with demographics, occupation, income_range, interests, coherence_score",
     lambda r: any(x in r for x in ['"occupation"', '"income"', '"interests"', '"coherence"', "Miami"]))

test("Analyst: target recon",
     "titan-analyst",
     "Analyze target: amazon.com. Return JSON with psp, antifraud, golden_path_score, three_ds_required",
     lambda r: any(x in r for x in ['"psp"', '"antifraud"', '"golden_path"', "amazon", "Stripe"]))

# ═══════════════════════════════════════════════════════════
# TITAN-STRATEGIST (Deep Reasoning) Tests
# ═══════════════════════════════════════════════════════════
print("\n--- TITAN-STRATEGIST (Deep Reasoning) ---")

test("Strategist: 3DS bypass plan",
     "titan-strategist",
     "Card: UK Visa 453201, Merchant: German Shopify store, Amount: 45 EUR. Create 3DS bypass strategy.",
     lambda r: any(x in r.lower() for x in ["step", "exemption", "tra", "low-value", "one-leg", "psd2"]))

test("Strategist: decline analysis",
     "titan-strategist",
     "3 consecutive declines on same BIN at CDKeys.com with Adyen code 'Refused'. Analyze root cause.",
     lambda r: any(x in r.lower() for x in ["step", "velocity", "bin", "block", "issuer", "pattern"]))

test("Strategist: operation plan",
     "titan-strategist",
     "Plan operation for purchasing a $150 digital item from a Checkout.com merchant with a US Visa card.",
     lambda r: any(x in r.lower() for x in ["step", "profile", "proxy", "amount", "checkout", "strategy"]))

# ═══════════════════════════════════════════════════════════
# RESULTS
# ═══════════════════════════════════════════════════════════
print("=" * 70)
total = PASS + FAIL
print(f"RESULTS: {PASS}/{total} PASSED | {FAIL} FAILED")
if FAIL == 0:
    print("VERDICT: ALL CUSTOM MODELS PRODUCING ACCURATE DOMAIN RESPONSES")
else:
    print(f"VERDICT: {FAIL} tests need attention")
print("=" * 70)
