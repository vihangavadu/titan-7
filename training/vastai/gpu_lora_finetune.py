#!/usr/bin/env python3
"""
TITAN V9.0 — GPU-Optimized LoRA Fine-Tuning for Vast.ai
=========================================================
Designed for single RTX 3090/4090/A100 GPU instances.
~2-4 hours per model vs 24-30h on CPU.

Usage:
    python3 gpu_lora_finetune.py --task analyst
    python3 gpu_lora_finetune.py --task strategist
    python3 gpu_lora_finetune.py --task fast
    python3 gpu_lora_finetune.py --task all    # Sequential all 3
"""

import argparse
import json
import os
import sys
import time
import signal
from datetime import datetime, timedelta
from pathlib import Path

os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

DATA_DIR = "/workspace/training/data_v9"
OUTPUT_DIR = "/workspace/training/models_v9"
LOGS_DIR = "/workspace/training/logs"

TASK_GROUPS = {
    "analyst": [
        "bin_analysis","bin_generation","target_recon","site_discovery",
        "profile_audit","persona_enrichment","coherence_check","preset_generation",
        "country_profiles","fingerprint_coherence","identity_graph","environment_coherence",
        "avs_prevalidation","live_target_scoring","profile_optimization",
        "persona_consistency_check","card_target_matching","operation_pattern_mining",
        "autofill_data_generation","tls_profile_selection","intel_synthesis",
        "storage_pattern_planning","hardware_profile_coherence",
    ],
    "strategist": [
        "three_ds_strategy","operation_planning","detection_analysis","decline_analysis",
        "preflight_advisor","bug_analysis","session_rhythm","card_rotation",
        "velocity_schedule","defense_tracking","decline_autopsy","cross_session",
        "copilot_abort_prediction","detection_root_cause","first_session_warmup_plan",
        "issuer_behavior_prediction","patch_reasoning","intel_prioritization",
        "history_pattern_planning","kyc_strategy","validation_strategy",
    ],
    "fast": [
        "behavioral_tuning","copilot_guidance","warmup_searches","dork_generation",
        "general_query","navigation_path","form_fill_cadence","trajectory_tuning",
        "biometric_profile_tuning","cookie_value_generation","detection_prediction",
        "purchase_history_generation","ga_event_planning",
    ],
}

BASE_MODELS = {
    "analyst": "Qwen/Qwen2.5-7B",
    "strategist": "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B",
    "fast": "mistralai/Mistral-7B-v0.3",
}

GPU_LORA_CONFIG = {
    "analyst":    {"r":16, "alpha":32, "dropout":0.05, "lr":2e-4, "epochs":4, "max_seq":1024, "batch":1, "grad_accum":8},
    "strategist": {"r":16, "alpha":32, "dropout":0.05, "lr":1.5e-4, "epochs":4, "max_seq":1024, "batch":1, "grad_accum":8},
    "fast":       {"r":12, "alpha":24, "dropout":0.05, "lr":2.5e-4, "epochs":4, "max_seq":768, "batch":2, "grad_accum":4},
}


def load_data(task_group):
    tasks = TASK_GROUPS.get(task_group, [])
    examples = []
    for task in tasks:
        fp = os.path.join(DATA_DIR, f"{task}.jsonl")
        if os.path.exists(fp):
            tc = 0
            with open(fp) as f:
                for line in f:
                    try:
                        ex = json.loads(line)
                        examples.append({"instruction": ex["prompt"], "output": ex["response"], "task": ex.get("task", task)})
                        tc += 1
                    except: pass
            print(f"    {task}: {tc}")
        else:
            print(f"    {task}: MISSING")
    return examples


def to_hf(examples, task_group):
    formatted = []
    for ex in examples:
        if task_group == "strategist":
            text = f"### Instruction:\n{ex['instruction']}\n\nThink step-by-step.\n\n### Response:\n{ex['output']}"
        else:
            text = f"### Instruction:\n{ex['instruction']}\n\n### Response:\n{ex['output']}"
        formatted.append({"text": text})
    return formatted


def train_one(task_group):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer, DataCollatorForLanguageModeling
    from peft import get_peft_model, LoraConfig, TaskType
    from datasets import Dataset

    cfg = GPU_LORA_CONFIG[task_group]
    hf_model_id = BASE_MODELS[task_group]
    output_path = os.path.join(OUTPUT_DIR, f"titan-{task_group}-v9-lora")
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_path = os.path.join(LOGS_DIR, f"gpu_{task_group}_{ts}.json")

    for d in [OUTPUT_DIR, LOGS_DIR]:
        os.makedirs(d, exist_ok=True)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    gpu_name = torch.cuda.get_device_name(0) if device == "cuda" else "CPU"
    gpu_mem = torch.cuda.get_device_properties(0).total_memory / 1e9 if device == "cuda" else 0

    print(f"\n{'='*65}")
    print(f" TITAN V9.0 — GPU LoRA Fine-Tuning")
    print(f"{'='*65}")
    print(f" Task:     {task_group} ({len(TASK_GROUPS[task_group])} tasks)")
    print(f" Model:    {hf_model_id}")
    print(f" Device:   {gpu_name} ({gpu_mem:.1f} GB)")
    print(f" LoRA:     r={cfg['r']}, alpha={cfg['alpha']}")
    print(f" Batch:    {cfg['batch']} × {cfg['grad_accum']} = {cfg['batch']*cfg['grad_accum']} effective")
    print(f" Epochs:   {cfg['epochs']}")
    print(f" Seq len:  {cfg['max_seq']}")
    print(f"{'='*65}\n")

    # Load data
    print("[1/6] Loading training data...")
    examples = load_data(task_group)
    if not examples:
        print("ERROR: No data. Run generate_training_data_v9.py first.")
        return
    print(f"  Total: {len(examples)} examples")

    # Prepare dataset
    print("\n[2/6] Preparing dataset...")
    hf_data = to_hf(examples, task_group)
    dataset = Dataset.from_list(hf_data)

    # Tokenizer
    print(f"\n[3/6] Loading tokenizer {hf_model_id}...")
    tokenizer = AutoTokenizer.from_pretrained(hf_model_id, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        tokenizer.pad_token_id = tokenizer.eos_token_id

    def tokenize(batch):
        t = tokenizer(batch["text"], truncation=True, max_length=cfg["max_seq"], padding="max_length", return_tensors=None)
        t["labels"] = t["input_ids"].copy()
        return t

    tokenized = dataset.map(tokenize, batched=True, remove_columns=dataset.column_names, num_proc=4)
    print(f"  Tokenized: {len(tokenized)} examples")

    # Load model
    print(f"\n[4/6] Loading model...")
    use_bf16 = device == "cuda" and torch.cuda.is_bf16_supported()
    dtype = torch.bfloat16 if use_bf16 else torch.float16 if device == "cuda" else torch.float32

    model = AutoModelForCausalLM.from_pretrained(
        hf_model_id, torch_dtype=dtype, device_map="auto",
        trust_remote_code=True, low_cpu_mem_usage=True,
    )
    model.gradient_checkpointing_enable()
    model.config.use_cache = False
    print(f"  Loaded: {sum(p.numel() for p in model.parameters())/1e9:.1f}B params, dtype={dtype}")

    # LoRA
    print(f"\n[5/6] Applying LoRA (r={cfg['r']})...")
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM, r=cfg["r"], lora_alpha=cfg["alpha"],
        lora_dropout=cfg["dropout"],
        target_modules=["q_proj","v_proj","k_proj","o_proj"],
        bias="none",
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # Training
    print(f"\n[6/6] Training...")
    training_args = TrainingArguments(
        output_dir=output_path, num_train_epochs=cfg["epochs"],
        per_device_train_batch_size=cfg["batch"],
        gradient_accumulation_steps=cfg["grad_accum"],
        learning_rate=cfg["lr"], lr_scheduler_type="cosine",
        weight_decay=0.01, warmup_steps=50, max_grad_norm=1.0,
        fp16=(dtype == torch.float16), bf16=use_bf16,
        gradient_checkpointing=True, optim="adamw_torch",
        dataloader_pin_memory=True, dataloader_num_workers=4,
        logging_steps=10,
        save_steps=500, save_total_limit=2,
        report_to="none", eval_strategy="no", push_to_hub=False,
    )

    trainer = Trainer(
        model=model, args=training_args, train_dataset=tokenized,
        data_collator=DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False),
        processing_class=tokenizer,
    )

    steps_per_epoch = len(tokenized) // (cfg["batch"] * cfg["grad_accum"])
    total_steps = steps_per_epoch * cfg["epochs"]
    print(f"  Steps/epoch: {steps_per_epoch}, Total: {total_steps}")

    start = time.time()

    def sig_handler(sig, frame):
        print(f"\n\nInterrupted. Saving checkpoint...")
        trainer.save_model(output_path + "-interrupted")
        tokenizer.save_pretrained(output_path + "-interrupted")
        sys.exit(0)

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    result = trainer.train()
    elapsed = time.time() - start
    metrics = result.metrics

    print(f"\n{'='*65}")
    print(f" DONE in {timedelta(seconds=int(elapsed))}")
    print(f" Loss: {metrics.get('train_loss', '?')}")
    print(f"{'='*65}")

    # Save
    model.save_pretrained(output_path)
    tokenizer.save_pretrained(output_path)
    print(f" Saved → {output_path}")

    # Log
    log = {
        "version": "v9.0-gpu", "task_group": task_group,
        "tasks": TASK_GROUPS[task_group], "model": hf_model_id,
        "gpu": gpu_name, "gpu_mem_gb": round(gpu_mem, 1),
        "lora_r": cfg["r"], "epochs": cfg["epochs"],
        "examples": len(examples), "dtype": str(dtype),
        "loss": metrics.get("train_loss"), "time_s": int(elapsed),
        "time_human": str(timedelta(seconds=int(elapsed))),
        "timestamp": datetime.now().isoformat(),
    }
    with open(log_path, "w") as f:
        json.dump(log, f, indent=2)
    print(f" Log → {log_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="TITAN V9.0 GPU LoRA Fine-Tuning (Vast.ai)")
    parser.add_argument("--task", required=True, choices=["analyst","strategist","fast","all"])
    args = parser.parse_args()

    if args.task == "all":
        for t in ["analyst", "strategist", "fast"]:
            print(f"\n{'#'*65}")
            print(f" TRAINING: titan-{t}")
            print(f"{'#'*65}")
            train_one(t)
    else:
        train_one(args.task)

    print(f"\n{'='*65}")
    print(f" ALL TRAINING COMPLETE")
    print(f" Models saved to: {OUTPUT_DIR}")
    print(f"{'='*65}")


if __name__ == "__main__":
    main()
