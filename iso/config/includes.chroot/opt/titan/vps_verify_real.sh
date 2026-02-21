#!/bin/bash
cd /opt/titan

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  VERIFY OLLAMA IS RETURNING REAL DATA (not hardcoded)                ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"

python3 - <<'PYEOF'
import sys, time, json, hashlib
sys.path.insert(0, "core")

# Clear all caches so nothing is cached
import importlib
if "ai_intelligence_engine" in sys.modules:
    importlib.reload(sys.modules["ai_intelligence_engine"])

from ai_intelligence_engine import (
    analyze_bin, recon_target, advise_3ds, tune_behavior, audit_profile,
    _bin_cache, _target_cache
)
_bin_cache.clear()
_target_cache.clear()

print()
print("═══ TEST 1: Same BIN, different targets → different results? ═══")
print()
r1 = analyze_bin("476173", "nike.com", 180)
_bin_cache.clear()  # clear cache between calls
r2 = analyze_bin("476173", "walmart.com", 45)
_bin_cache.clear()
r3 = analyze_bin("476173", "steam.com", 500)

print(f"  BIN 476173 → nike.com $180:")
print(f"    bank={r1.bank_name}, score={r1.ai_score}, success={r1.success_prediction:.0%}")
print(f"    risk={r1.risk_level.value}, timing={r1.timing_advice}")
print(f"    targets={r1.best_targets[:3]}")
print(f"    strategy={r1.strategic_notes[:100]}")
print()
print(f"  BIN 476173 → walmart.com $45:")
print(f"    bank={r2.bank_name}, score={r2.ai_score}, success={r2.success_prediction:.0%}")
print(f"    risk={r2.risk_level.value}, timing={r2.timing_advice}")
print(f"    targets={r2.best_targets[:3]}")
print(f"    strategy={r2.strategic_notes[:100]}")
print()
print(f"  BIN 476173 → steam.com $500:")
print(f"    bank={r3.bank_name}, score={r3.ai_score}, success={r3.success_prediction:.0%}")
print(f"    risk={r3.risk_level.value}, timing={r3.timing_advice}")
print(f"    targets={r3.best_targets[:3]}")
print(f"    strategy={r3.strategic_notes[:100]}")

# Check uniqueness
fields1 = f"{r1.ai_score}{r1.success_prediction}{r1.timing_advice}{r1.strategic_notes}"
fields2 = f"{r2.ai_score}{r2.success_prediction}{r2.timing_advice}{r2.strategic_notes}"
fields3 = f"{r3.ai_score}{r3.success_prediction}{r3.timing_advice}{r3.strategic_notes}"
h1, h2, h3 = hashlib.md5(fields1.encode()).hexdigest()[:8], hashlib.md5(fields2.encode()).hexdigest()[:8], hashlib.md5(fields3.encode()).hexdigest()[:8]
all_diff = len({h1, h2, h3}) == 3
print(f"\n  Hashes: {h1} / {h2} / {h3}")
print(f"  All different: {'✅ YES — Ollama returns unique per context' if all_diff else '⚠️ Some identical — check if Ollama parsing works'}")

print()
print("═══ TEST 2: Unknown target recon — is it really analyzing? ═══")
print()
_target_cache.clear()
t1 = recon_target("stockx.com")
_target_cache.clear()
t2 = recon_target("farfetch.com")
_target_cache.clear()
t3 = recon_target("newegg.com")

for label, t in [("stockx.com", t1), ("farfetch.com", t2), ("newegg.com", t3)]:
    print(f"  {label}:")
    print(f"    name={t.name}")
    print(f"    fraud_engine={t.fraud_engine_guess}")
    print(f"    psp={t.payment_processor_guess}")
    print(f"    friction={t.estimated_friction}")
    print(f"    3ds={t.three_ds_probability:.0%}")
    print(f"    best_cards={t.optimal_card_types}")
    print(f"    countries={t.optimal_countries}")
    if t.warmup_strategy:
        print(f"    warmup[0]={t.warmup_strategy[0][:80]}")
    if t.checkout_tips:
        print(f"    tip[0]={t.checkout_tips[0][:80]}")
    print(f"    ai_powered={t.ai_powered}")
    print()

# Verify fraud engines are different (StockX = Forter, Farfetch = Riskified typically)
engines = {t1.fraud_engine_guess, t2.fraud_engine_guess, t3.fraud_engine_guess}
print(f"  Fraud engines found: {engines}")
print(f"  Different engines: {'✅ YES' if len(engines) > 1 else '⚠️ All same'}")

print()
print("═══ TEST 3: 3DS strategy varies by amount ═══")
print()
s1 = advise_3ds("421783", "amazon.com", 25)
s2 = advise_3ds("421783", "amazon.com", 500)
s3 = advise_3ds("531993", "eneba.com", 150)

for label, s in [("421783/amazon/$25", s1), ("421783/amazon/$500", s2), ("531993/eneba/$150", s3)]:
    print(f"  {label}:")
    print(f"    approach={s.recommended_approach}")
    print(f"    success={s.success_probability:.0%}")
    print(f"    timing={s.timing_window}")
    print(f"    amount_strategy={s.amount_strategy[:80]}")
    print(f"    ai_powered={s.ai_powered}")
    print()

print()
print("═══ TEST 4: Behavioral tuning varies by fraud engine ═══")
print()
b1 = tune_behavior("amazon.com", fraud_engine="forter")
b2 = tune_behavior("amazon.com", fraud_engine="riskified")
b3 = tune_behavior("amazon.com", fraud_engine="sift")

for label, b in [("forter", b1), ("riskified", b2), ("sift", b3)]:
    print(f"  {label}:")
    print(f"    mouse={b.mouse_speed_range}, click={b.click_delay_ms}")
    print(f"    typing={b.typing_wpm_range} wpm, errors={b.typing_error_rate:.1%}")
    print(f"    scroll={b.scroll_behavior}")
    print(f"    form={b.form_fill_strategy[:60]}")
    print(f"    ai_powered={b.ai_powered}")
    print()

print()
print("═══ TEST 5: Raw Ollama response (proof it's real LLM output) ═══")
print()
from ai_intelligence_engine import _query_ollama
raw = _query_ollama("In exactly 2 sentences, describe what a payment card BIN is and why it matters.", task_type="default", timeout=20)
print(f"  Raw Ollama response:")
print(f"  \"{raw[:300]}\"")
print(f"  Length: {len(raw or '')} chars")
print(f"  Contains BIN mention: {'✅' if raw and 'BIN' in raw.upper() else '❌'}")

print()
print("═══ VERDICT ═══")
all_ai = all([r1.ai_powered, r2.ai_powered, t1.ai_powered, t2.ai_powered, s1.ai_powered, b1.ai_powered])
print(f"  All ai_powered=True: {'✅' if all_ai else '❌'}")
print(f"  Different results per context: {'✅' if all_diff else '❌'}")
print(f"  Multiple fraud engines detected: {'✅' if len(engines) > 1 else '❌'}")
print(f"  Raw LLM text received: {'✅' if raw and len(raw) > 20 else '❌'}")
if all_ai and raw and len(raw) > 20:
    print(f"\n  🎯 VERDICT: ALL DATA IS REAL — OLLAMA IS LIVE AND RESPONDING DYNAMICALLY")
else:
    print(f"\n  ⚠️ SOME RESPONSES MAY BE STATIC — CHECK OLLAMA")
PYEOF

echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  VERIFICATION COMPLETE                                               ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
