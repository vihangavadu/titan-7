#!/usr/bin/env python3
"""
TITAN V8.3 — Phase 2: Model Evaluation Harness
================================================
Benchmarks AI model accuracy across all task types.
Compares old vs new models. Scores JSON validity, field completeness,
and domain-specific accuracy.

Usage:
    python3 evaluate_models.py --model titan-analyst --tasks all --count 10
    python3 evaluate_models.py --model titan-analyst --compare titan-analyst-old --tasks bin_analysis
"""

import argparse
import json
import os
import time
import subprocess
import hashlib
from datetime import datetime
from pathlib import Path

RESULTS_DIR = "/opt/titan/training/eval_results"
DATA_DIR = "/opt/titan/training/data"

# ═══════════════════════════════════════════════════════════════
# SCORING FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def score_json_validity(response_text):
    """Score 0-100 for JSON parsing success."""
    text = response_text.strip()
    # Remove markdown code blocks
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(l for l in lines if not l.startswith("```"))

    try:
        parsed = json.loads(text)
        return 100, parsed
    except json.JSONDecodeError:
        pass

    # Try to extract JSON
    import re
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group())
            return 70, parsed  # Penalty for needing extraction
        except json.JSONDecodeError:
            pass
    return 0, None


def score_field_completeness(parsed, required_fields):
    """Score 0-100 for required field presence."""
    if not parsed or not isinstance(parsed, dict):
        return 0
    present = sum(1 for f in required_fields if f in parsed)
    return int(100 * present / len(required_fields)) if required_fields else 100


def score_value_validity(parsed, validators):
    """Score 0-100 for value correctness."""
    if not parsed or not isinstance(parsed, dict):
        return 0
    total = len(validators)
    valid = 0
    for field, validator_fn in validators.items():
        if field in parsed:
            try:
                if validator_fn(parsed[field]):
                    valid += 1
            except Exception:
                pass
    return int(100 * valid / total) if total else 100


# ═══════════════════════════════════════════════════════════════
# TASK-SPECIFIC EVALUATION
# ═══════════════════════════════════════════════════════════════

TASK_CONFIGS = {
    "bin_analysis": {
        "required_fields": ["bank_name", "country", "network", "card_type", "card_level", "risk_level", "success_prediction", "ai_score"],
        "validators": {
            "network": lambda v: v.lower() in ("visa", "mastercard", "amex", "discover", "jcb"),
            "card_type": lambda v: v.lower() in ("credit", "debit", "prepaid", "charge"),
            "success_prediction": lambda v: 0 <= float(v) <= 1,
            "ai_score": lambda v: 0 <= int(v) <= 100,
        },
    },
    "target_recon": {
        "required_fields": ["domain", "fraud_engine_guess", "payment_processor_guess", "three_ds_probability", "difficulty_score"],
        "validators": {
            "fraud_engine_guess": lambda v: v.lower() in ("forter", "riskified", "seon", "stripe_radar", "cybersource", "kount", "accertify", "internal", "unknown"),
            "three_ds_probability": lambda v: 0 <= float(v) <= 1,
            "difficulty_score": lambda v: 0 <= int(v) <= 100,
        },
    },
    "fingerprint_coherence": {
        "required_fields": ["coherent", "score", "mismatches", "leak_vectors", "fixes"],
        "validators": {
            "coherent": lambda v: isinstance(v, bool),
            "score": lambda v: 0 <= float(v) <= 100,
            "mismatches": lambda v: isinstance(v, list),
        },
    },
    "identity_graph": {
        "required_fields": ["plausible", "score", "anomalies", "graph_links_missing", "fixes"],
        "validators": {
            "plausible": lambda v: isinstance(v, bool),
            "score": lambda v: 0 <= float(v) <= 100,
            "anomalies": lambda v: isinstance(v, list),
        },
    },
    "environment_coherence": {
        "required_fields": ["coherent", "score", "mismatches", "fixes"],
        "validators": {
            "coherent": lambda v: isinstance(v, bool),
            "score": lambda v: 0 <= float(v) <= 100,
        },
    },
    "decline_autopsy": {
        "required_fields": ["root_cause", "category", "is_retriable", "wait_time_min", "patches", "next_action"],
        "validators": {
            "category": lambda v: v.lower() in ("network", "fingerprint", "behavioral", "payment", "identity", "velocity"),
            "is_retriable": lambda v: isinstance(v, bool),
            "wait_time_min": lambda v: int(v) >= 0,
            "patches": lambda v: isinstance(v, list),
        },
    },
    "session_rhythm": {
        "required_fields": ["warmup_pages", "browse_pages", "cart_dwell_s", "checkout_dwell_s", "total_session_s"],
        "validators": {
            "warmup_pages": lambda v: isinstance(v, list) and len(v) >= 1,
            "total_session_s": lambda v: int(v) >= 120,
        },
    },
    "card_rotation": {
        "required_fields": ["recommended_card_bin", "recommended_target", "recommended_amount", "reasoning"],
        "validators": {
            "recommended_amount": lambda v: float(v) > 0,
        },
    },
    "velocity_schedule": {
        "required_fields": ["max_attempts_per_hour", "max_attempts_per_day", "cooldown_after_decline_min", "optimal_spacing_min"],
        "validators": {
            "max_attempts_per_hour": lambda v: 1 <= int(v) <= 10,
            "max_attempts_per_day": lambda v: 1 <= int(v) <= 20,
        },
    },
    "avs_prevalidation": {
        "required_fields": ["avs_likely_pass", "confidence", "issues", "address_fixes", "zip_format_ok"],
        "validators": {
            "avs_likely_pass": lambda v: isinstance(v, bool),
            "confidence": lambda v: 0 <= float(v) <= 1,
            "zip_format_ok": lambda v: isinstance(v, bool),
        },
    },
}


def query_ollama(model, prompt, timeout=60):
    """Query Ollama model and return response text + latency."""
    t0 = time.time()
    try:
        result = subprocess.run(
            ["ollama", "run", model, prompt],
            capture_output=True, text=True, timeout=timeout
        )
        latency = time.time() - t0
        return result.stdout.strip(), latency
    except subprocess.TimeoutExpired:
        return "", time.time() - t0
    except Exception as e:
        return f"ERROR: {e}", time.time() - t0


def evaluate_task(model, task_type, count=10):
    """Evaluate model on a specific task type."""
    config = TASK_CONFIGS.get(task_type)
    if not config:
        print(f"No evaluation config for task '{task_type}'")
        return None

    # Load test prompts from training data
    data_file = os.path.join(DATA_DIR, f"{task_type}.jsonl")
    test_prompts = []
    if os.path.exists(data_file):
        with open(data_file) as f:
            for line in f:
                try:
                    example = json.loads(line)
                    test_prompts.append(example["prompt"])
                except Exception:
                    pass
    else:
        print(f"No training data found at {data_file} — generating on the fly")
        return None

    # Limit to count
    test_prompts = test_prompts[:count]

    results = []
    for i, prompt in enumerate(test_prompts):
        print(f"  [{task_type}] {i+1}/{len(test_prompts)}...", end=" ", flush=True)
        response, latency = query_ollama(model, prompt)

        json_score, parsed = score_json_validity(response)
        field_score = score_field_completeness(parsed, config["required_fields"])
        value_score = score_value_validity(parsed, config.get("validators", {}))

        composite = int(json_score * 0.4 + field_score * 0.3 + value_score * 0.3)

        results.append({
            "prompt": prompt[:100],
            "json_score": json_score,
            "field_score": field_score,
            "value_score": value_score,
            "composite": composite,
            "latency_s": round(latency, 1),
        })
        print(f"composite={composite}, latency={latency:.1f}s")

    # Aggregate
    avg_composite = sum(r["composite"] for r in results) / len(results) if results else 0
    avg_json = sum(r["json_score"] for r in results) / len(results) if results else 0
    avg_field = sum(r["field_score"] for r in results) / len(results) if results else 0
    avg_value = sum(r["value_score"] for r in results) / len(results) if results else 0
    avg_latency = sum(r["latency_s"] for r in results) / len(results) if results else 0

    return {
        "model": model,
        "task": task_type,
        "count": len(results),
        "avg_composite": round(avg_composite, 1),
        "avg_json_validity": round(avg_json, 1),
        "avg_field_completeness": round(avg_field, 1),
        "avg_value_validity": round(avg_value, 1),
        "avg_latency_s": round(avg_latency, 1),
        "details": results,
        "timestamp": datetime.now().isoformat(),
    }


def main():
    parser = argparse.ArgumentParser(description="Titan V8.3 Model Evaluation")
    parser.add_argument("--model", required=True, help="Model name (e.g., titan-analyst)")
    parser.add_argument("--compare", default="", help="Compare against this model")
    parser.add_argument("--tasks", default="all", help="Comma-separated tasks or 'all'")
    parser.add_argument("--count", type=int, default=10, help="Test examples per task")
    parser.add_argument("--output", default=RESULTS_DIR, help="Output directory")
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    if args.tasks == "all":
        tasks = list(TASK_CONFIGS.keys())
    else:
        tasks = [t.strip() for t in args.tasks.split(",")]

    print(f"=== Evaluating {args.model} on {len(tasks)} tasks ({args.count} examples each) ===\n")

    all_results = []
    for task in tasks:
        result = evaluate_task(args.model, task, args.count)
        if result:
            all_results.append(result)
            print(f"  → {task}: composite={result['avg_composite']}/100, "
                  f"json={result['avg_json_validity']}, fields={result['avg_field_completeness']}, "
                  f"values={result['avg_value_validity']}, latency={result['avg_latency_s']}s\n")

    # Compare if requested
    if args.compare:
        print(f"\n=== Comparing against {args.compare} ===\n")
        compare_results = []
        for task in tasks:
            result = evaluate_task(args.compare, task, args.count)
            if result:
                compare_results.append(result)

    # Save results
    output_file = os.path.join(args.output, f"eval_{args.model}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(output_file, "w") as f:
        json.dump({
            "model": args.model,
            "compare": args.compare,
            "timestamp": datetime.now().isoformat(),
            "results": all_results,
        }, f, indent=2)

    # Summary
    print("\n" + "=" * 60)
    print(f"EVALUATION SUMMARY: {args.model}")
    print("=" * 60)
    if all_results:
        overall = sum(r["avg_composite"] for r in all_results) / len(all_results)
        print(f"Overall composite score: {overall:.1f}/100")
        print(f"Tasks evaluated: {len(all_results)}")
        for r in sorted(all_results, key=lambda x: x["avg_composite"], reverse=True):
            print(f"  {r['task']:30s} {r['avg_composite']:5.1f}/100  (json={r['avg_json_validity']:.0f} field={r['avg_field_completeness']:.0f} value={r['avg_value_validity']:.0f}) {r['avg_latency_s']:.1f}s")
    print(f"\nResults saved to: {output_file}")


if __name__ == "__main__":
    main()
