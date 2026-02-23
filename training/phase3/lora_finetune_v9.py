#!/usr/bin/env python3
"""
TITAN V9.0 — CPU-Optimized LoRA Fine-Tuning (57 Tasks)
========================================================
Fine-tunes Ollama models using LoRA adapters on CPU.
Optimized for AMD EPYC 9354P (8 vCPU, 32GB RAM, AVX-512 BF16/VNNI).

V9.0 Changes from V8.3:
    - 57 tasks (was 10): analyst=23, strategist=21, fast=13
    - LoRA rank 16 (was 8) for broader task coverage
    - Max seq length 1536 (was 1024) for complex JSON
    - 4 epochs (was 3) for convergence on more tasks
    - Learning rate 1.5e-4 (was 2e-4) for stability

Usage:
    python3 lora_finetune_v9.py --task analyst --epochs 4
    python3 lora_finetune_v9.py --task strategist --epochs 4
    python3 lora_finetune_v9.py --task fast --epochs 4

    # Background:
    nohup python3 lora_finetune_v9.py --task analyst --epochs 4 > /opt/titan/training/logs/v9_analyst.log 2>&1 &

Timeline (AMD EPYC 8 vCPU, 32GB, BF16):
    - analyst:    ~6,900 examples × 4 epochs ≈ 28-32 hours
    - strategist: ~6,300 examples × 4 epochs ≈ 26-30 hours
    - fast:       ~3,900 examples × 4 epochs ≈ 16-20 hours
    - TOTAL:      ~70-82 hours sequential
"""

import argparse
import json
import os
import sys
import time
import signal
from datetime import datetime, timedelta
from pathlib import Path

# ═══════════════════════════════════════════════════════════════
# CPU OPTIMIZATION: Set environment BEFORE importing torch
# ═══════════════════════════════════════════════════════════════
os.environ["OMP_NUM_THREADS"] = "8"
os.environ["MKL_NUM_THREADS"] = "8"
os.environ["OPENBLAS_NUM_THREADS"] = "8"
os.environ["OMP_SCHEDULE"] = "static"
os.environ["OMP_PROC_BIND"] = "close"
os.environ["OMP_PLACES"] = "cores"
os.environ["DNNL_MAX_CPU_ISA"] = "AVX512_CORE_VNNI"
os.environ["MALLOC_ARENA_MAX"] = "2"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

TRAINING_DATA_DIR = "/opt/titan/training/data_v9"
OUTPUT_DIR = "/opt/titan/training/models_v9"
LOGS_DIR = "/opt/titan/training/logs"
ONNX_DIR = "/opt/titan/training/onnx_v9"

# V9.0 — Complete task-to-model mapping (57 tasks)
TASK_GROUPS = {
    "analyst": [
        "bin_analysis", "bin_generation", "target_recon", "site_discovery",
        "profile_audit", "persona_enrichment", "coherence_check", "preset_generation",
        "country_profiles", "fingerprint_coherence", "identity_graph", "environment_coherence",
        "avs_prevalidation", "live_target_scoring", "profile_optimization",
        "persona_consistency_check", "card_target_matching", "operation_pattern_mining",
        "autofill_data_generation", "tls_profile_selection", "intel_synthesis",
        "storage_pattern_planning", "hardware_profile_coherence",
    ],
    "strategist": [
        "three_ds_strategy", "operation_planning", "detection_analysis", "decline_analysis",
        "preflight_advisor", "bug_analysis", "session_rhythm", "card_rotation",
        "velocity_schedule", "defense_tracking", "decline_autopsy", "cross_session",
        "copilot_abort_prediction", "detection_root_cause", "first_session_warmup_plan",
        "issuer_behavior_prediction", "patch_reasoning", "intel_prioritization",
        "history_pattern_planning", "kyc_strategy", "validation_strategy",
    ],
    "fast": [
        "behavioral_tuning", "copilot_guidance", "warmup_searches", "dork_generation",
        "general_query", "navigation_path", "form_fill_cadence", "trajectory_tuning",
        "biometric_profile_tuning", "cookie_value_generation", "detection_prediction",
        "purchase_history_generation", "ga_event_planning",
    ],
}

# Base models
BASE_MODELS = {
    "analyst": "qwen2.5:7b",
    "strategist": "deepseek-r1:8b",
    "fast": "mistral:7b",
}

# HuggingFace model IDs
HF_MODEL_IDS = {
    "qwen2.5:7b": "Qwen/Qwen2.5-7B",
    "deepseek-r1:8b": "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B",
    "mistral:7b": "mistralai/Mistral-7B-v0.3",
}

# V9.0 LoRA hyperparameters (optimized for 57-task coverage)
V9_LORA_CONFIG = {
    "analyst": {"r": 16, "alpha": 32, "dropout": 0.05, "lr": 1.5e-4, "epochs": 4, "max_seq": 1536},
    "strategist": {"r": 16, "alpha": 32, "dropout": 0.05, "lr": 1.2e-4, "epochs": 4, "max_seq": 1536},
    "fast": {"r": 12, "alpha": 24, "dropout": 0.05, "lr": 1.8e-4, "epochs": 4, "max_seq": 1024},
}


def load_training_data(task_group):
    """Load and combine JSONL training data for a task group."""
    tasks = TASK_GROUPS.get(task_group, [])
    examples = []
    for task in tasks:
        data_file = os.path.join(TRAINING_DATA_DIR, f"{task}.jsonl")
        if os.path.exists(data_file):
            task_count = 0
            with open(data_file) as f:
                for line in f:
                    try:
                        ex = json.loads(line)
                        examples.append({
                            "instruction": ex["prompt"],
                            "output": ex["response"],
                            "task": ex.get("task", task),
                        })
                        task_count += 1
                    except Exception:
                        pass
            print(f"    {task}: {task_count} examples")
        else:
            print(f"    {task}: MISSING — run generate_training_data_v9.py first")
    return examples


def convert_to_hf_format(examples, task_group):
    """Convert examples to Hugging Face format with model-specific prompting."""
    formatted = []
    for ex in examples:
        if task_group == "analyst":
            text = f"### Instruction:\n{ex['instruction']}\n\n### Response:\n{ex['output']}"
        elif task_group == "strategist":
            text = f"### Instruction:\n{ex['instruction']}\n\nThink step-by-step.\n\n### Response:\n{ex['output']}"
        else:
            text = f"### Instruction:\n{ex['instruction']}\n\n### Response:\n{ex['output']}"
        formatted.append({"text": text, "instruction": ex["instruction"], "output": ex["output"]})
    return formatted


def estimate_time(num_examples, epochs, use_bf16=True):
    """Estimate training time for CPU-based LoRA."""
    spe = 15.0 if use_bf16 else 30.0
    return timedelta(seconds=int(num_examples * epochs * spe))


def check_bf16():
    """Check AVX-512 BF16 support."""
    try:
        with open("/proc/cpuinfo") as f:
            return "avx512_bf16" in f.read()
    except Exception:
        return False


def run_training(task_group, epochs=None, batch_size=1, learning_rate=None, max_examples=None):
    """Run LoRA fine-tuning with V9.0 optimized configuration."""
    try:
        import torch
        from transformers import (
            AutoModelForCausalLM, AutoTokenizer,
            TrainingArguments, Trainer, DataCollatorForLanguageModeling,
        )
        from peft import get_peft_model, LoraConfig, TaskType
        from datasets import Dataset
    except ImportError as e:
        print(f"ERROR: Missing dependency: {e}")
        sys.exit(1)

    # V9 config
    cfg = V9_LORA_CONFIG[task_group]
    epochs = epochs or cfg["epochs"]
    learning_rate = learning_rate or cfg["lr"]
    max_seq_len = cfg["max_seq"]
    lora_r = cfg["r"]
    lora_alpha = cfg["alpha"]
    lora_dropout = cfg["dropout"]

    # CPU config
    torch.set_num_threads(8)
    torch.set_num_interop_threads(4)
    use_bf16 = check_bf16()
    compute_dtype = torch.bfloat16 if use_bf16 else torch.float32

    base_model = BASE_MODELS[task_group]
    hf_model_id = HF_MODEL_IDS[base_model]
    output_name = f"titan-{task_group}-v9-lora"
    output_path = os.path.join(OUTPUT_DIR, output_name)
    onnx_path = os.path.join(ONNX_DIR, output_name)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_path = os.path.join(LOGS_DIR, f"{output_name}_{timestamp}.json")

    for d in [OUTPUT_DIR, LOGS_DIR, ONNX_DIR]:
        os.makedirs(d, exist_ok=True)

    # Banner
    try:
        ram_gb = os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES') / (1024**3)
    except Exception:
        ram_gb = 32.0

    print(f"\n{'='*65}")
    print(f" TITAN V9.0 — CPU-Optimized LoRA Fine-Tuning")
    print(f"{'='*65}")
    print(f" Task group:    {task_group} ({len(TASK_GROUPS[task_group])} tasks)")
    print(f" Base model:    {base_model} → {hf_model_id}")
    print(f" Output:        {output_path}")
    print(f" Epochs:        {epochs}")
    print(f" LoRA rank:     {lora_r} (alpha={lora_alpha})")
    print(f" Learning rate: {learning_rate}")
    print(f" Max seq len:   {max_seq_len}")
    print(f" Compute dtype: {'BFloat16 (AVX-512)' if use_bf16 else 'Float32'}")
    print(f" RAM:           {ram_gb:.1f} GB")
    print(f"{'='*65}\n")

    # Load data
    print("[1/7] Loading training data...")
    examples = load_training_data(task_group)
    if max_examples:
        examples = examples[:max_examples]
    print(f"  Total: {len(examples)} examples across {len(TASK_GROUPS[task_group])} tasks")

    est = estimate_time(len(examples), epochs, use_bf16)
    print(f"  Estimated time: {est}")

    if len(examples) == 0:
        print("ERROR: No training data. Run generate_training_data_v9.py first.")
        sys.exit(1)

    # Prepare dataset
    print("\n[2/7] Preparing dataset...")
    hf_data = convert_to_hf_format(examples, task_group)
    dataset = Dataset.from_list(hf_data)

    # Tokenizer
    print(f"\n[3/7] Loading tokenizer from {hf_model_id}...")
    tokenizer = AutoTokenizer.from_pretrained(hf_model_id, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        tokenizer.pad_token_id = tokenizer.eos_token_id

    def tokenize_fn(batch):
        tokenized = tokenizer(batch["text"], truncation=True, max_length=max_seq_len, padding="max_length", return_tensors=None)
        tokenized["labels"] = tokenized["input_ids"].copy()
        return tokenized

    print("  Tokenizing...")
    tokenized_dataset = dataset.map(tokenize_fn, batched=True, remove_columns=dataset.column_names, num_proc=4)
    print(f"  Done: {len(tokenized_dataset)} examples, max_seq={max_seq_len}")

    # Load model
    print(f"\n[4/7] Loading {hf_model_id}...")
    model = AutoModelForCausalLM.from_pretrained(hf_model_id, torch_dtype=compute_dtype, device_map="cpu", trust_remote_code=True, low_cpu_mem_usage=True)
    model.gradient_checkpointing_enable()
    model.config.use_cache = False
    print(f"  Loaded: {sum(p.numel() for p in model.parameters())/1e9:.1f}B params")

    # LoRA
    print(f"\n[5/7] Applying LoRA (r={lora_r}, alpha={lora_alpha})...")
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=lora_r, lora_alpha=lora_alpha, lora_dropout=lora_dropout,
        target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
        bias="none",
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # Training args
    print("\n[6/7] Configuring training...")
    grad_accum = 8
    training_args = TrainingArguments(
        output_dir=output_path, overwrite_output_dir=True, num_train_epochs=epochs,
        per_device_train_batch_size=batch_size, gradient_accumulation_steps=grad_accum,
        learning_rate=learning_rate, lr_scheduler_type="cosine", weight_decay=0.01,
        warmup_ratio=0.05, max_grad_norm=1.0,
        fp16=False, bf16=use_bf16, no_cuda=True, use_cpu=True,
        gradient_checkpointing=True, optim="adamw_torch",
        dataloader_pin_memory=False, dataloader_num_workers=4, dataloader_prefetch_factor=2,
        logging_steps=10, logging_first_step=True, save_steps=200, save_total_limit=2,
        report_to="none", evaluation_strategy="no", push_to_hub=False,
    )

    trainer = Trainer(
        model=model, args=training_args, train_dataset=tokenized_dataset,
        data_collator=DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False),
        tokenizer=tokenizer,
    )

    # Train
    print(f"\n[7/7] Starting training...")
    print(f"  Effective batch: {batch_size * grad_accum}")
    print(f"  Steps/epoch: {len(tokenized_dataset) // (batch_size * grad_accum)}")
    print(f"  Total steps: {len(tokenized_dataset) * epochs // (batch_size * grad_accum)}")
    print(f"  Estimated: {est}")
    print(f"  BFloat16: {'YES' if use_bf16 else 'NO'}")
    print()

    start = time.time()

    def sig_handler(sig, frame):
        elapsed = timedelta(seconds=int(time.time() - start))
        print(f"\n\nInterrupted after {elapsed}. Saving checkpoint...")
        trainer.save_model(output_path + "-interrupted")
        tokenizer.save_pretrained(output_path + "-interrupted")
        print(f"Checkpoint: {output_path}-interrupted")
        sys.exit(0)

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    result = trainer.train()
    elapsed = time.time() - start
    metrics = result.metrics
    metrics["total_time_s"] = int(elapsed)
    metrics["total_time"] = str(timedelta(seconds=int(elapsed)))

    print(f"\n{'='*65}")
    print(f" Training complete in {timedelta(seconds=int(elapsed))}")
    print(f" Loss: {metrics.get('train_loss', '?')}")
    print(f"{'='*65}")

    # Save
    print(f"\nSaving LoRA adapter → {output_path}")
    model.save_pretrained(output_path)
    tokenizer.save_pretrained(output_path)

    # ONNX export
    print(f"\nExporting ONNX...")
    try:
        from optimum.onnxruntime import ORTModelForCausalLM
        ort = ORTModelForCausalLM.from_pretrained(output_path, export=True, provider="CPUExecutionProvider")
        ort.save_pretrained(onnx_path)
        print(f"  ONNX → {onnx_path}")
    except Exception as e:
        print(f"  ONNX skipped: {e}")

    # Log
    log_data = {
        "version": "v9.0", "task_group": task_group, "tasks": TASK_GROUPS[task_group],
        "base_model": base_model, "hf_model_id": hf_model_id,
        "output_path": output_path, "epochs": epochs, "lora_r": lora_r,
        "lora_alpha": lora_alpha, "lr": learning_rate, "max_seq": max_seq_len,
        "num_examples": len(examples), "dtype": "bf16" if use_bf16 else "fp32",
        "metrics": {k: str(v) for k, v in metrics.items()},
        "time_s": int(elapsed), "time_human": str(timedelta(seconds=int(elapsed))),
        "timestamp": datetime.now().isoformat(),
    }
    with open(log_path, "w") as f:
        json.dump(log_data, f, indent=2)

    print(f"\n{'='*65}")
    print(f" DONE!")
    print(f"   LoRA:  {output_path}")
    print(f"   ONNX:  {onnx_path}")
    print(f"   Log:   {log_path}")
    print(f"")
    print(f" Next: Merge LoRA → GGUF → Ollama")
    print(f"   python3 -c \"from peft import AutoPeftModelForCausalLM; \\")
    print(f"     m=AutoPeftModelForCausalLM.from_pretrained('{output_path}'); \\")
    print(f"     m.merge_and_unload().save_pretrained('{output_path}-merged')\"")
    print(f"   python3 llama.cpp/convert_hf_to_gguf.py {output_path}-merged")
    print(f"   ollama create titan-{task_group}-v9 -f titan-{task_group}-v9.modelfile")
    print(f"{'='*65}")


def main():
    parser = argparse.ArgumentParser(
        description="TITAN V9.0 LoRA Fine-Tuning (57 tasks, AMD EPYC AVX-512 BF16)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Task groups:
  analyst    = 23 tasks (qwen2.5:7b base, ~6,900 examples, ~30h)
  strategist = 21 tasks (deepseek-r1:8b base, ~6,300 examples, ~28h)
  fast       = 13 tasks (mistral:7b base, ~3,900 examples, ~16h)

Examples:
  python3 lora_finetune_v9.py --task analyst --epochs 4
  python3 lora_finetune_v9.py --task strategist --epochs 4
  python3 lora_finetune_v9.py --task fast --epochs 4 --max-examples 500
        """
    )
    parser.add_argument("--task", required=True, choices=["analyst","strategist","fast"])
    parser.add_argument("--epochs", type=int, default=None, help="Override epochs (default: 4)")
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--lr", type=float, default=None, help="Override learning rate")
    parser.add_argument("--max-examples", type=int, default=None, help="Limit examples (testing)")
    args = parser.parse_args()

    run_training(args.task, args.epochs, args.batch_size, args.lr, args.max_examples)


if __name__ == "__main__":
    main()
