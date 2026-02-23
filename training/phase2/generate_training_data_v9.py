#!/usr/bin/env python3
"""
TITAN V9.0 — Complete Training Data Generator
==============================================
ALL 57 AI tasks | 300 examples per task | 17,100 total
Chain-of-thought reasoning | 30% hard negatives | Multi-signal correlation

Usage:
    python3 generate_training_data_v9.py --count 300
    python3 generate_training_data_v9.py --count 300 --tasks bin_analysis,trajectory_tuning
    python3 generate_training_data_v9.py --count 50 --group analyst
    python3 generate_training_data_v9.py --count 300 --validate
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from v9_generators_card import (
    gen_bin_analysis, gen_bin_generation, gen_card_target_matching,
    gen_validation_strategy, gen_issuer_behavior_prediction,
    gen_target_recon, gen_site_discovery, gen_live_target_scoring,
    gen_preset_generation,
    gen_fingerprint_coherence, gen_environment_coherence,
    gen_hardware_profile_coherence, gen_tls_profile_selection,
    gen_coherence_check,
)
from v9_generators_identity import (
    gen_identity_graph, gen_persona_enrichment, gen_persona_consistency_check,
    gen_profile_audit, gen_profile_optimization,
    gen_session_rhythm, gen_behavioral_tuning, gen_trajectory_tuning,
    gen_biometric_profile_tuning, gen_form_fill_cadence,
    gen_navigation_path, gen_first_session_warmup_plan,
)
from v9_generators_strategy import (
    gen_three_ds_strategy, gen_operation_planning, gen_preflight_advisor,
    gen_copilot_abort_prediction,
    gen_decline_autopsy, gen_decline_analysis, gen_detection_analysis,
    gen_detection_root_cause, gen_detection_prediction, gen_defense_tracking,
    gen_card_rotation, gen_velocity_schedule,
)
from v9_generators_content import (
    gen_warmup_searches, gen_dork_generation, gen_cookie_value_generation,
    gen_purchase_history_generation, gen_ga_event_planning,
    gen_history_pattern_planning, gen_autofill_data_generation,
    gen_storage_pattern_planning,
    gen_copilot_guidance, gen_general_query, gen_country_profiles,
    gen_bug_analysis, gen_intel_prioritization, gen_intel_synthesis,
    gen_operation_pattern_mining, gen_cross_session, gen_patch_reasoning,
    gen_kyc_strategy, gen_avs_prevalidation,
)

OUTPUT_DIR = "/opt/titan/training/data_v9"

# ═══════════════════════════════════════════════════════════════
# COMPLETE REGISTRY: ALL 57 TASKS
# ═══════════════════════════════════════════════════════════════

GENERATORS = {
    # --- titan-analyst tasks (23) ---
    "bin_analysis": gen_bin_analysis,
    "bin_generation": gen_bin_generation,
    "target_recon": gen_target_recon,
    "site_discovery": gen_site_discovery,
    "profile_audit": gen_profile_audit,
    "persona_enrichment": gen_persona_enrichment,
    "coherence_check": gen_coherence_check,
    "preset_generation": gen_preset_generation,
    "country_profiles": gen_country_profiles,
    "fingerprint_coherence": gen_fingerprint_coherence,
    "identity_graph": gen_identity_graph,
    "environment_coherence": gen_environment_coherence,
    "avs_prevalidation": gen_avs_prevalidation,
    "live_target_scoring": gen_live_target_scoring,
    "profile_optimization": gen_profile_optimization,
    "persona_consistency_check": gen_persona_consistency_check,
    "card_target_matching": gen_card_target_matching,
    "operation_pattern_mining": gen_operation_pattern_mining,
    "autofill_data_generation": gen_autofill_data_generation,
    "tls_profile_selection": gen_tls_profile_selection,
    "intel_synthesis": gen_intel_synthesis,
    "storage_pattern_planning": gen_storage_pattern_planning,
    "hardware_profile_coherence": gen_hardware_profile_coherence,

    # --- titan-strategist tasks (21) ---
    "three_ds_strategy": gen_three_ds_strategy,
    "operation_planning": gen_operation_planning,
    "detection_analysis": gen_detection_analysis,
    "decline_analysis": gen_decline_analysis,
    "preflight_advisor": gen_preflight_advisor,
    "bug_analysis": gen_bug_analysis,
    "session_rhythm": gen_session_rhythm,
    "card_rotation": gen_card_rotation,
    "velocity_schedule": gen_velocity_schedule,
    "defense_tracking": gen_defense_tracking,
    "decline_autopsy": gen_decline_autopsy,
    "cross_session": gen_cross_session,
    "copilot_abort_prediction": gen_copilot_abort_prediction,
    "detection_root_cause": gen_detection_root_cause,
    "first_session_warmup_plan": gen_first_session_warmup_plan,
    "issuer_behavior_prediction": gen_issuer_behavior_prediction,
    "patch_reasoning": gen_patch_reasoning,
    "intel_prioritization": gen_intel_prioritization,
    "history_pattern_planning": gen_history_pattern_planning,
    "kyc_strategy": gen_kyc_strategy,
    "validation_strategy": gen_validation_strategy,

    # --- titan-fast tasks (13) ---
    "behavioral_tuning": gen_behavioral_tuning,
    "copilot_guidance": gen_copilot_guidance,
    "warmup_searches": gen_warmup_searches,
    "dork_generation": gen_dork_generation,
    "general_query": gen_general_query,
    "navigation_path": gen_navigation_path,
    "form_fill_cadence": gen_form_fill_cadence,
    "trajectory_tuning": gen_trajectory_tuning,
    "biometric_profile_tuning": gen_biometric_profile_tuning,
    "cookie_value_generation": gen_cookie_value_generation,
    "detection_prediction": gen_detection_prediction,
    "purchase_history_generation": gen_purchase_history_generation,
    "ga_event_planning": gen_ga_event_planning,
}

# Model groupings for --group flag
MODEL_GROUPS = {
    "analyst": [
        "bin_analysis","bin_generation","target_recon","site_discovery","profile_audit",
        "persona_enrichment","coherence_check","preset_generation","country_profiles",
        "fingerprint_coherence","identity_graph","environment_coherence","avs_prevalidation",
        "live_target_scoring","profile_optimization","persona_consistency_check",
        "card_target_matching","operation_pattern_mining","autofill_data_generation",
        "tls_profile_selection","intel_synthesis","storage_pattern_planning","hardware_profile_coherence",
    ],
    "strategist": [
        "three_ds_strategy","operation_planning","detection_analysis","decline_analysis",
        "preflight_advisor","bug_analysis","session_rhythm","card_rotation","velocity_schedule",
        "defense_tracking","decline_autopsy","cross_session","copilot_abort_prediction",
        "detection_root_cause","first_session_warmup_plan","issuer_behavior_prediction",
        "patch_reasoning","intel_prioritization","history_pattern_planning","kyc_strategy",
        "validation_strategy",
    ],
    "fast": [
        "behavioral_tuning","copilot_guidance","warmup_searches","dork_generation",
        "general_query","navigation_path","form_fill_cadence","trajectory_tuning",
        "biometric_profile_tuning","cookie_value_generation","detection_prediction",
        "purchase_history_generation","ga_event_planning",
    ],
}


def validate_example(example):
    """Validate generated example quality."""
    try:
        response = json.loads(example["response"]) if isinstance(example["response"], str) else example["response"]
        if "reasoning" not in response:
            return False, "Missing reasoning field"
        reasoning = response["reasoning"]
        if len(reasoning) < 30:
            return False, f"Reasoning too short ({len(reasoning)} chars)"
        return True, "OK"
    except (json.JSONDecodeError, TypeError) as e:
        return False, f"Invalid JSON: {e}"


def main():
    parser = argparse.ArgumentParser(
        description="TITAN V9.0 — Complete Training Data Generator (57 tasks)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 generate_training_data_v9.py --count 300                    # All 57 tasks, 300 each
  python3 generate_training_data_v9.py --count 300 --group analyst    # Only analyst tasks
  python3 generate_training_data_v9.py --count 50 --tasks bin_analysis,trajectory_tuning
  python3 generate_training_data_v9.py --count 300 --validate         # With quality validation

Task counts:
  titan-analyst:    23 tasks (structured analysis, JSON output)
  titan-strategist: 21 tasks (deep reasoning, step-by-step)
  titan-fast:       13 tasks (real-time guidance, concise)
  TOTAL:            57 tasks × 300 = 17,100 examples
        """
    )
    parser.add_argument("--tasks", default="all", help="Comma-separated task types, 'all', or model group name")
    parser.add_argument("--group", choices=["analyst","strategist","fast"], help="Generate only for specific model group")
    parser.add_argument("--count", type=int, default=300, help="Examples per task (default: 300)")
    parser.add_argument("--output", default=OUTPUT_DIR, help="Output directory")
    parser.add_argument("--validate", action="store_true", help="Validate all generated examples")
    parser.add_argument("--combined", action="store_true", help="Also output combined per-model JSONL files")
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    # Determine which tasks to generate
    if args.group:
        tasks = MODEL_GROUPS[args.group]
    elif args.tasks == "all":
        tasks = list(GENERATORS.keys())
    else:
        tasks = [t.strip() for t in args.tasks.split(",")]

    start_time = time.time()
    total = 0
    total_valid = 0
    task_stats = {}

    print(f"\n{'='*65}")
    print(f" TITAN V9.0 — Training Data Generator")
    print(f"{'='*65}")
    print(f" Tasks:     {len(tasks)} / {len(GENERATORS)} total")
    print(f" Per task:  {args.count} examples")
    print(f" Total:     {len(tasks) * args.count} examples")
    print(f" Output:    {args.output}")
    print(f" Validate:  {'YES' if args.validate else 'NO'}")
    print(f"{'='*65}\n")

    # Per-model combined files
    combined = {"analyst": [], "strategist": [], "fast": []}

    for task_idx, task in enumerate(tasks, 1):
        gen_func = GENERATORS.get(task)
        if not gen_func:
            print(f"  WARNING: No generator for '{task}', skipping")
            continue

        # Determine model group for combined output
        model = "analyst" if task in MODEL_GROUPS["analyst"] else "strategist" if task in MODEL_GROUPS["strategist"] else "fast"

        output_file = os.path.join(args.output, f"{task}.jsonl")
        count = 0
        valid_count = 0
        errors = 0

        with open(output_file, "w") as f:
            for i in range(args.count):
                try:
                    example = gen_func()
                    if args.validate:
                        ok, msg = validate_example(example)
                        if ok:
                            valid_count += 1
                        else:
                            if errors < 3:
                                print(f"    INVALID {task}#{i}: {msg}")
                            errors += 1
                    f.write(json.dumps(example) + "\n")
                    if args.combined:
                        combined[model].append(example)
                    count += 1
                except Exception as e:
                    errors += 1
                    if errors <= 3:
                        print(f"    ERROR {task}#{i}: {e}")

        total += count
        total_valid += valid_count if args.validate else count
        task_stats[task] = {"count": count, "valid": valid_count if args.validate else count, "errors": errors, "model": model}

        valid_str = f" ({valid_count}/{count} valid)" if args.validate else ""
        err_str = f" [{errors} errors]" if errors > 0 else ""
        pct = f"[{task_idx}/{len(tasks)}]"
        print(f"  {pct:>8} {task:.<40} {count:>4} examples{valid_str}{err_str} → {model}")

    # Write combined per-model files
    if args.combined:
        print(f"\n  Writing combined per-model files...")
        for model_name, examples in combined.items():
            if examples:
                combined_file = os.path.join(args.output, f"combined_{model_name}.jsonl")
                with open(combined_file, "w") as f:
                    for ex in examples:
                        f.write(json.dumps(ex) + "\n")
                print(f"    {model_name}: {len(examples)} examples → {combined_file}")

    elapsed = time.time() - start_time

    # Summary
    print(f"\n{'='*65}")
    print(f" GENERATION COMPLETE")
    print(f"{'='*65}")
    print(f" Total examples: {total} across {len(task_stats)} tasks")
    if args.validate:
        vr = total_valid/max(total,1)*100
        print(f" Valid:          {total_valid}/{total} ({vr:.1f}%)")
    print(f" Time:           {elapsed:.1f}s ({total/max(elapsed,0.1):.0f} examples/sec)")
    print(f" Output:         {args.output}")

    # Per-model breakdown
    for model_name in ["analyst","strategist","fast"]:
        model_tasks = {k:v for k,v in task_stats.items() if v["model"]==model_name}
        model_total = sum(v["count"] for v in model_tasks.values())
        print(f"   titan-{model_name}: {len(model_tasks)} tasks, {model_total} examples")

    total_errors = sum(v["errors"] for v in task_stats.values())
    if total_errors > 0:
        print(f" Errors:         {total_errors} total")
    print(f"{'='*65}")

    # Write stats file
    stats_file = os.path.join(args.output, "generation_stats.json")
    with open(stats_file, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total_examples": total,
            "total_tasks": len(task_stats),
            "examples_per_task": args.count,
            "validation_enabled": args.validate,
            "valid_count": total_valid,
            "generation_time_s": round(elapsed, 1),
            "task_stats": task_stats,
        }, f, indent=2)
    print(f"\n Stats saved to: {stats_file}")


if __name__ == "__main__":
    main()
