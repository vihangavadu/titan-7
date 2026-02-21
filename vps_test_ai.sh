#!/bin/bash
# Test AI Intelligence Engine on VPS
cd /opt/titan && python3 - <<'PYEOF'
import sys, time, json
sys.path.insert(0, "core")

print("=" * 70)
print("  TITAN V7.5 AI INTELLIGENCE ENGINE — LIVE TEST")
print("=" * 70)

from ai_intelligence_engine import (
    is_ai_available, get_ai_status,
    analyze_bin, recon_target, advise_3ds,
    tune_behavior, plan_operation, audit_profile
)

status = get_ai_status()
print(f"\nAI Status: {'ONLINE' if status['available'] else 'OFFLINE'}")
print(f"Provider: {status['provider']}")
print(f"Features: {len(status['features'])}")

if not status['available']:
    print("\nOllama offline — cannot run tests")
    sys.exit(1)

# ── Test 1: BIN Deep Analysis ──
print("\n" + "─" * 70)
print("TEST 1: AI BIN Deep Analysis")
print("─" * 70)
t0 = time.time()
result = analyze_bin("421783", "eneba.com", 150)
t1 = time.time()
print(f"  BIN: {result.bin_number}")
print(f"  Bank: {result.bank_name}")
print(f"  Country: {result.country} | Type: {result.card_type} | Level: {result.card_level}")
print(f"  Network: {result.network}")
print(f"  AI Score: {result.ai_score}/100")
print(f"  Success Prediction: {result.success_prediction:.0%}")
print(f"  Risk Level: {result.risk_level.value}")
print(f"  Best Targets: {result.best_targets[:3]}")
print(f"  Avoid Targets: {result.avoid_targets[:3]}")
print(f"  Optimal Amount: ${result.optimal_amount_range[0]:.0f}-${result.optimal_amount_range[1]:.0f}")
print(f"  Timing: {result.timing_advice}")
print(f"  Risk Factors: {result.risk_factors[:2]}")
print(f"  Strategy: {result.strategic_notes[:100]}")
print(f"  AI Powered: {result.ai_powered} | Time: {t1-t0:.1f}s")

# ── Test 2: Target Recon ──
print("\n" + "─" * 70)
print("TEST 2: AI Target Recon (unknown target)")
print("─" * 70)
t0 = time.time()
result = recon_target("stockx.com", "sneakers/fashion")
t1 = time.time()
print(f"  Target: {result.domain}")
print(f"  Name: {result.name}")
print(f"  Fraud Engine: {result.fraud_engine_guess}")
print(f"  Payment PSP: {result.payment_processor_guess}")
print(f"  Friction: {result.estimated_friction}")
print(f"  3DS Probability: {result.three_ds_probability:.0%}")
print(f"  Optimal Cards: {result.optimal_card_types}")
print(f"  Optimal Countries: {result.optimal_countries}")
print(f"  Warmup: {result.warmup_strategy[:2]}")
print(f"  Tips: {result.checkout_tips[:2]}")
print(f"  AI Powered: {result.ai_powered} | Time: {t1-t0:.1f}s")

# ── Test 3: 3DS Strategy ──
print("\n" + "─" * 70)
print("TEST 3: AI 3DS Bypass Strategy")
print("─" * 70)
t0 = time.time()
result = advise_3ds("421783", "eneba.com", 150,
                    card_info={"country": "US", "type": "credit", "level": "platinum"},
                    target_info={"fraud_engine": "seon", "three_ds_rate": 0.15})
t1 = time.time()
print(f"  Approach: {result.recommended_approach}")
print(f"  Success: {result.success_probability:.0%}")
print(f"  Timing: {result.timing_window}")
print(f"  Amount Strategy: {result.amount_strategy}")
print(f"  Card Pref: {result.card_type_preference}")
print(f"  Flow: {result.checkout_flow[:3]}")
print(f"  Fallback: {result.fallback_plan}")
print(f"  AI Powered: {result.ai_powered} | Time: {t1-t0:.1f}s")

# ── Test 4: Behavioral Tuning ──
print("\n" + "─" * 70)
print("TEST 4: AI Behavioral Tuning (Ghost Motor)")
print("─" * 70)
t0 = time.time()
result = tune_behavior("amazon.com", fraud_engine="forter",
                       persona="US adult 30-45, frequent Amazon shopper")
t1 = time.time()
print(f"  Target: {result.target}")
print(f"  Mouse Speed: {result.mouse_speed_range}")
print(f"  Click Delay: {result.click_delay_ms}ms")
print(f"  Scroll: {result.scroll_behavior}")
print(f"  Typing: {result.typing_wpm_range} WPM")
print(f"  Error Rate: {result.typing_error_rate:.1%}")
print(f"  Idle: {result.idle_pattern[:60]}")
print(f"  Form Fill: {result.form_fill_strategy[:60]}")
print(f"  Page Dwell: {result.page_dwell_seconds}s")
print(f"  AI Powered: {result.ai_powered} | Time: {t1-t0:.1f}s")

# ── Test 5: Full Operation Plan ──
print("\n" + "─" * 70)
print("TEST 5: Full AI Operation Plan")
print("─" * 70)
t0 = time.time()
plan = plan_operation("421783", "eneba.com", 150,
                      card_info={"country": "US", "type": "credit", "level": "platinum"})
t1 = time.time()
print(f"  Decision: {'GO' if plan.go_decision else 'NO-GO'}")
print(f"  Overall Score: {plan.overall_score}/100")
print(f"  Summary: {plan.executive_summary}")
print(f"  AI Powered: {plan.ai_powered} | Total Time: {t1-t0:.1f}s")

# ── Test 6: Known target from static DB ──
print("\n" + "─" * 70)
print("TEST 6: Static Target (from intelligence DB)")
print("─" * 70)
result = recon_target("g2a.com")
print(f"  Target: {result.domain}")
print(f"  Engine: {result.fraud_engine_guess}")
print(f"  PSP: {result.payment_processor_guess}")
print(f"  AI Powered: {result.ai_powered} (should be False for known targets)")

print("\n" + "=" * 70)
print("  ALL TESTS COMPLETE")
print("=" * 70)
PYEOF
