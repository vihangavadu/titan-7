#!/usr/bin/env python3
"""
TITAN V8.3 — Phase 3: CPU-Optimized LoRA Fine-Tuning
======================================================
Fine-tunes Ollama models using LoRA adapters on CPU.
Optimized for AMD EPYC 9354P (8 vCPU, 32GB RAM, AVX-512 BF16/VNNI).

Hardware Profile:
    CPU:  AMD EPYC 9354P (Zen 4, AVX-512 BF16, VNNI)
    RAM:  32GB DDR5
    Disk: NVMe-class SSD (~980 MB/s)
    OS:   Debian 12

CPU Optimizations Applied:
    1. BFloat16 training (native AVX-512 BF16 on Zen 4)
    2. Gradient checkpointing (fits 7B model in 32GB)
    3. OMP thread pinning (8 threads, close binding)
    4. OpenBLAS with AVX-512 (775 GFLOPS measured)
    5. ONNX Runtime export for fast post-training inference
    6. Memory-mapped dataset loading (NVMe-backed)
    7. Gradient accumulation (effective batch=8 with micro-batch=1)

Prerequisites (already installed on VPS):
    pip install torch --index-url https://download.pytorch.org/whl/cpu
    pip install transformers==4.48.0 datasets==3.3.0 peft==0.14.0
    pip install accelerate==1.3.0 sentencepiece onnx optimum[onnxruntime]

Usage:
    python3 lora_finetune.py --task analyst --epochs 3
    python3 lora_finetune.py --task strategist --epochs 5
    python3 lora_finetune.py --task fast --epochs 3 --max-examples 200

    # Run in background with nohup:
    nohup python3 lora_finetune.py --task analyst --epochs 3 > /opt/titan/training/logs/analyst.log 2>&1 &

Timeline estimate (AMD EPYC 8 vCPU, 32GB, BF16):
    - 300 examples, 3 epochs, BF16: ~8-16 hours per model
    - 500 examples, 5 epochs, BF16: ~1-3 days per model
    (BF16 gives ~1.5-2x speedup over FP32 on Zen 4)
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

TRAINING_DATA_DIR = "/opt/titan/training/data"
OUTPUT_DIR = "/opt/titan/training/models"
LOGS_DIR = "/opt/titan/training/logs"
ONNX_DIR = "/opt/titan/training/onnx"

# Task-to-training-data mapping
TASK_GROUPS = {
    "analyst": [
        "bin_analysis", "target_recon", "fingerprint_coherence",
        "identity_graph", "environment_coherence", "avs_prevalidation",
    ],
    "strategist": [
        "decline_autopsy", "card_rotation", "velocity_schedule",
        "session_rhythm",
    ],
    "fast": [
        "bin_analysis", "target_recon",
    ],
}

# Model name mapping
BASE_MODELS = {
    "analyst": "qwen2.5:7b",
    "strategist": "qwen2.5:7b",
    "fast": "mistral:7b",
}


def load_training_data(task_group):
    """Load and combine JSONL training data for a task group."""
    tasks = TASK_GROUPS.get(task_group, [])
    examples = []
    for task in tasks:
        data_file = os.path.join(TRAINING_DATA_DIR, f"{task}.jsonl")
        if os.path.exists(data_file):
            with open(data_file) as f:
                for line in f:
                    try:
                        ex = json.loads(line)
                        examples.append({
                            "instruction": ex["prompt"],
                            "output": ex["response"],
                            "task": ex.get("task", task),
                        })
                    except Exception:
                        pass
            print(f"  Loaded {task}: {sum(1 for e in examples if e['task'] == task)} examples")
        else:
            print(f"  WARNING: No data file for {task}")
    return examples


def convert_to_hf_format(examples):
    """Convert examples to Hugging Face datasets format."""
    formatted = []
    for ex in examples:
        formatted.append({
            "text": f"### Instruction:\n{ex['instruction']}\n\n### Response:\n{ex['output']}",
            "instruction": ex["instruction"],
            "output": ex["output"],
        })
    return formatted


def estimate_training_time(num_examples, epochs, num_cpus=8, use_bf16=True):
    """Estimate training time for CPU-based LoRA on AMD EPYC."""
    # BF16 on Zen 4 AVX-512: ~15s per example per epoch
    # FP32 fallback: ~30s per example per epoch
    seconds_per_example = 15.0 if use_bf16 else 30.0
    seconds_per_example *= (8 / num_cpus)
    total_seconds = num_examples * epochs * seconds_per_example
    return timedelta(seconds=int(total_seconds))


def check_bf16_support():
    """Check if CPU supports BFloat16 (AVX-512 BF16 on Zen 4+)."""
    try:
        with open("/proc/cpuinfo") as f:
            flags = f.read()
        return "avx512_bf16" in flags
    except Exception:
        return False


def run_training(task_group, epochs=3, batch_size=1, learning_rate=2e-4, max_examples=None):
    """Run LoRA fine-tuning on CPU with AMD EPYC optimizations."""
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
        print("Run: bash /opt/titan/training/setup_cpu_optimized.sh")
        sys.exit(1)

    # ═══════════════════════════════════════════════════════════
    # CPU OPTIMIZATION: Configure PyTorch for AMD EPYC
    # ═══════════════════════════════════════════════════════════
    torch.set_num_threads(8)
    torch.set_num_interop_threads(4)

    # BFloat16 check — AMD EPYC 9354P has native AVX-512 BF16
    use_bf16 = check_bf16_support()
    compute_dtype = torch.bfloat16 if use_bf16 else torch.float32

    base_model_name = BASE_MODELS.get(task_group, "qwen2.5:7b")
    output_name = f"titan-{task_group}-v83-lora"
    output_path = os.path.join(OUTPUT_DIR, output_name)
    onnx_path = os.path.join(ONNX_DIR, output_name)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_path = os.path.join(LOGS_DIR, f"{output_name}_{timestamp}.json")

    for d in [OUTPUT_DIR, LOGS_DIR, ONNX_DIR]:
        os.makedirs(d, exist_ok=True)

    # HuggingFace model IDs
    hf_model_ids = {
        "qwen2.5:7b": "Qwen/Qwen2.5-7B",
        "mistral:7b": "mistralai/Mistral-7B-v0.3",
    }
    hf_model_id = hf_model_ids.get(base_model_name)
    if not hf_model_id:
        print(f"ERROR: No HF model ID mapping for {base_model_name}")
        sys.exit(1)

    # ═══════════════════════════════════════════════════════════
    # BANNER
    # ═══════════════════════════════════════════════════════════
    ram_gb = os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES') / (1024**3)
    print(f"\n{'='*65}")
    print(f" TITAN V8.3 — CPU-Optimized LoRA Fine-Tuning")
    print(f"{'='*65}")
    print(f" Task group:    {task_group}")
    print(f" Base model:    {base_model_name} → {hf_model_id}")
    print(f" Output:        {output_path}")
    print(f" Epochs:        {epochs}")
    print(f" Learning rate: {learning_rate}")
    print(f" Device:        CPU ({os.cpu_count()} cores, AMD EPYC)")
    print(f" RAM:           {ram_gb:.1f} GB")
    print(f" Compute dtype: {'BFloat16 (AVX-512 BF16 native)' if use_bf16 else 'Float32'}")
    print(f" OMP threads:   {os.environ.get('OMP_NUM_THREADS', '?')}")
    print(f" DNNL ISA:      {os.environ.get('DNNL_MAX_CPU_ISA', '?')}")
    print(f"{'='*65}\n")

    # ═══════════════════════════════════════════════════════════
    # LOAD TRAINING DATA
    # ═══════════════════════════════════════════════════════════
    print("[1/7] Loading training data...")
    examples = load_training_data(task_group)
    if max_examples:
        examples = examples[:max_examples]
    print(f"  Total examples: {len(examples)}")

    estimate = estimate_training_time(len(examples), epochs, use_bf16=use_bf16)
    print(f"  Estimated training time: {estimate}")

    if len(examples) == 0:
        print("ERROR: No training data found. Run generate_training_data.py first.")
        sys.exit(1)

    # ═══════════════════════════════════════════════════════════
    # PREPARE DATASET
    # ═══════════════════════════════════════════════════════════
    print("\n[2/7] Preparing dataset...")
    hf_data = convert_to_hf_format(examples)
    dataset = Dataset.from_list(hf_data)

    # ═══════════════════════════════════════════════════════════
    # LOAD TOKENIZER
    # ═══════════════════════════════════════════════════════════
    print(f"\n[3/7] Loading tokenizer from {hf_model_id}...")
    tokenizer = AutoTokenizer.from_pretrained(hf_model_id, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        tokenizer.pad_token_id = tokenizer.eos_token_id

    # Tokenize with optimized settings
    max_seq_len = 1024  # Shorter sequences = faster training on CPU
    def tokenize_fn(batch):
        tokenized = tokenizer(
            batch["text"],
            truncation=True,
            max_length=max_seq_len,
            padding="max_length",
            return_tensors=None,
        )
        tokenized["labels"] = tokenized["input_ids"].copy()
        return tokenized

    print("  Tokenizing dataset...")
    tokenized_dataset = dataset.map(
        tokenize_fn, batched=True,
        remove_columns=dataset.column_names,
        num_proc=4,  # Parallel tokenization on NVMe
    )
    print(f"  Tokenized: {len(tokenized_dataset)} examples, max_seq_len={max_seq_len}")

    # ═══════════════════════════════════════════════════════════
    # LOAD MODEL with memory optimizations
    # ═══════════════════════════════════════════════════════════
    print(f"\n[4/7] Loading base model {hf_model_id}...")
    print(f"  dtype={compute_dtype}, gradient_checkpointing=True")

    model = AutoModelForCausalLM.from_pretrained(
        hf_model_id,
        torch_dtype=compute_dtype,
        device_map="cpu",
        trust_remote_code=True,
        low_cpu_mem_usage=True,   # Stream weights to reduce peak RAM
    )

    # Enable gradient checkpointing (critical for 7B model in 32GB RAM)
    model.gradient_checkpointing_enable()
    # Disable KV cache during training (saves memory)
    model.config.use_cache = False

    print(f"  Model loaded: {sum(p.numel() for p in model.parameters()) / 1e9:.1f}B parameters")

    # ═══════════════════════════════════════════════════════════
    # APPLY LoRA (rank=8, targeting all attention projections)
    # ═══════════════════════════════════════════════════════════
    print("\n[5/7] Applying LoRA adapter...")
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=8,                          # Rank 8 = good quality/speed balance
        lora_alpha=16,                # Scaling factor (alpha/r = 2x)
        lora_dropout=0.05,
        target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
        bias="none",
        modules_to_save=None,
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # ═══════════════════════════════════════════════════════════
    # TRAINING ARGUMENTS — AMD EPYC Optimized
    # ═══════════════════════════════════════════════════════════
    print("\n[6/7] Configuring training...")

    # Effective batch size = micro_batch * gradient_accumulation = 1 * 8 = 8
    gradient_accumulation = 8

    training_args = TrainingArguments(
        output_dir=output_path,
        overwrite_output_dir=True,
        num_train_epochs=epochs,

        # Batch settings
        per_device_train_batch_size=batch_size,
        gradient_accumulation_steps=gradient_accumulation,

        # Learning rate schedule
        learning_rate=learning_rate,
        lr_scheduler_type="cosine",
        weight_decay=0.01,
        warmup_ratio=0.05,
        max_grad_norm=1.0,

        # CPU Optimization flags
        fp16=False,
        bf16=use_bf16,                     # AMD EPYC Zen 4 native BF16
        no_cuda=True,
        use_cpu=True,

        # Memory optimization
        gradient_checkpointing=True,
        optim="adamw_torch",              # Native PyTorch AdamW
        dataloader_pin_memory=False,       # No GPU, no pinning needed

        # I/O optimization (NVMe disk)
        dataloader_num_workers=4,
        dataloader_prefetch_factor=2,

        # Logging and saving
        logging_steps=10,
        logging_first_step=True,
        save_steps=100,
        save_total_limit=2,
        report_to="none",
        logging_dir=os.path.join(LOGS_DIR, f"tb_{output_name}"),

        # Disable unused features
        evaluation_strategy="no",
        push_to_hub=False,
        remove_unused_columns=True,
    )

    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False,  # Causal LM, not masked
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset,
        data_collator=data_collator,
        tokenizer=tokenizer,
    )

    # ═══════════════════════════════════════════════════════════
    # TRAIN
    # ═══════════════════════════════════════════════════════════
    print(f"\n[7/7] Starting training...")
    print(f"  Effective batch size: {batch_size * gradient_accumulation}")
    print(f"  Steps per epoch: {len(tokenized_dataset) // (batch_size * gradient_accumulation)}")
    print(f"  Total steps: {len(tokenized_dataset) * epochs // (batch_size * gradient_accumulation)}")
    print(f"  Estimated time: {estimate}")
    print(f"  BFloat16: {'YES (1.5-2x speedup)' if use_bf16 else 'NO (FP32 fallback)'}")
    print(f"  Gradient checkpointing: YES (saves ~40% RAM)")
    print()

    start_time = time.time()

    # Graceful interrupt handler
    def signal_handler(sig, frame):
        print(f"\n\nInterrupted after {timedelta(seconds=int(time.time() - start_time))}")
        print("Saving checkpoint...")
        trainer.save_model(output_path + "-interrupted")
        tokenizer.save_pretrained(output_path + "-interrupted")
        print(f"Checkpoint saved to: {output_path}-interrupted")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    train_result = trainer.train()

    elapsed = time.time() - start_time
    metrics = train_result.metrics
    metrics["total_time_seconds"] = int(elapsed)
    metrics["total_time_human"] = str(timedelta(seconds=int(elapsed)))

    print(f"\n{'='*65}")
    print(f" Training complete in {timedelta(seconds=int(elapsed))}")
    print(f" Training loss: {metrics.get('train_loss', '?')}")
    print(f"{'='*65}")

    # ═══════════════════════════════════════════════════════════
    # SAVE LoRA adapter
    # ═══════════════════════════════════════════════════════════
    print(f"\nSaving LoRA adapter to {output_path}...")
    model.save_pretrained(output_path)
    tokenizer.save_pretrained(output_path)

    # ═══════════════════════════════════════════════════════════
    # EXPORT TO ONNX (for fast CPU inference via ONNX Runtime)
    # ═══════════════════════════════════════════════════════════
    print(f"\nExporting to ONNX for fast inference...")
    try:
        from optimum.onnxruntime import ORTModelForCausalLM
        ort_model = ORTModelForCausalLM.from_pretrained(
            output_path,
            export=True,
            provider="CPUExecutionProvider",
        )
        ort_model.save_pretrained(onnx_path)
        print(f"  ONNX model saved to: {onnx_path}")
    except Exception as e:
        print(f"  ONNX export skipped: {e}")
        print(f"  (You can export later with: optimum-cli export onnx --model {output_path} {onnx_path})")

    # ═══════════════════════════════════════════════════════════
    # LOG RESULTS
    # ═══════════════════════════════════════════════════════════
    log_data = {
        "task_group": task_group,
        "base_model": base_model_name,
        "hf_model_id": hf_model_id,
        "output_path": output_path,
        "onnx_path": onnx_path,
        "epochs": epochs,
        "batch_size": batch_size,
        "effective_batch_size": batch_size * gradient_accumulation,
        "learning_rate": learning_rate,
        "max_seq_len": max_seq_len,
        "num_examples": len(examples),
        "compute_dtype": "bfloat16" if use_bf16 else "float32",
        "gradient_checkpointing": True,
        "lora_r": 8,
        "lora_alpha": 16,
        "metrics": {k: str(v) for k, v in metrics.items()},
        "training_time_seconds": int(elapsed),
        "training_time_human": str(timedelta(seconds=int(elapsed))),
        "cpu": "AMD EPYC 9354P",
        "avx512_bf16": use_bf16,
        "timestamp": datetime.now().isoformat(),
    }
    with open(log_path, "w") as f:
        json.dump(log_data, f, indent=2)

    print(f"\n{'='*65}")
    print(f" DONE! Results:")
    print(f"   LoRA adapter: {output_path}")
    print(f"   ONNX model:   {onnx_path}")
    print(f"   Training log: {log_path}")
    print(f"")
    print(f" Next steps to import into Ollama:")
    print(f"   1. Merge LoRA into base model:")
    print(f"      python3 -c \"from peft import AutoPeftModelForCausalLM; \\")
    print(f"        m = AutoPeftModelForCausalLM.from_pretrained('{output_path}'); \\")
    print(f"        merged = m.merge_and_unload(); \\")
    print(f"        merged.save_pretrained('{output_path}-merged')\"")
    print(f"   2. Convert to GGUF (install llama.cpp first):")
    print(f"      python3 llama.cpp/convert_hf_to_gguf.py {output_path}-merged")
    print(f"   3. Create Ollama model:")
    print(f"      ollama create titan-{task_group}-v83-ft -f <modelfile>")
    print(f"{'='*65}")


def main():
    parser = argparse.ArgumentParser(
        description="Titan V8.3 CPU-Optimized LoRA Fine-Tuning (AMD EPYC AVX-512 BF16)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 lora_finetune.py --task analyst --epochs 3
  python3 lora_finetune.py --task strategist --epochs 5
  python3 lora_finetune.py --task fast --epochs 3 --max-examples 200

  # Background training with nohup:
  nohup python3 lora_finetune.py --task analyst --epochs 3 > analyst.log 2>&1 &
        """
    )
    parser.add_argument("--task", required=True, choices=["analyst", "strategist", "fast"],
                        help="Task group to fine-tune (analyst=6 tasks, strategist=4 tasks, fast=2 tasks)")
    parser.add_argument("--epochs", type=int, default=3, help="Training epochs (default: 3)")
    parser.add_argument("--batch-size", type=int, default=1, help="Micro batch size (default: 1, effective=8 with grad accum)")
    parser.add_argument("--lr", type=float, default=2e-4, help="Learning rate (default: 2e-4)")
    parser.add_argument("--max-examples", type=int, default=None, help="Limit training examples (for testing)")
    args = parser.parse_args()

    run_training(args.task, args.epochs, args.batch_size, args.lr, args.max_examples)


if __name__ == "__main__":
    main()
