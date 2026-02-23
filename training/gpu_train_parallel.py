#!/usr/bin/env python3
"""TITAN V9.0 - Parallel GPU Training (strategist + fast only)."""
import os, sys, json, time, subprocess
from datetime import datetime
from pathlib import Path

os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True,max_split_size_mb:512"

DATA_DIR = "/workspace/training/data_v9"
OUT_DIR = "/workspace/training/models_v9"
LOG_DIR = "/workspace/training/logs"

TASK_GROUPS = {
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

HF_MODELS = {
    "strategist": "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B",
    "fast": "mistralai/Mistral-7B-v0.3",
}

LORA_CFG = {
    "strategist": {"r": 16, "alpha": 32, "dropout": 0.05, "lr": 1.2e-4, "epochs": 4, "max_seq": 1536, "batch": 4, "grad_accum": 4},
    "fast":       {"r": 12, "alpha": 24, "dropout": 0.05, "lr": 1.8e-4, "epochs": 4, "max_seq": 1024, "batch": 8, "grad_accum": 2},
}

def load_data(group):
    tasks = TASK_GROUPS[group]
    examples = []
    for task in tasks:
        fp = os.path.join(DATA_DIR, task + ".jsonl")
        if os.path.exists(fp):
            count = 0
            for line in open(fp):
                try:
                    d = json.loads(line)
                    examples.append({"instruction": d["prompt"], "output": d["response"], "task": task})
                    count += 1
                except:
                    pass
            print("  %s: %d" % (task, count))
        else:
            print("  %s: MISSING" % task)
    return examples

def train_model(group):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer, DataCollatorForLanguageModeling
    from peft import get_peft_model, LoraConfig, TaskType
    from datasets import Dataset

    cfg = LORA_CFG[group]
    hf_model = HF_MODELS[group]
    output_path = os.path.join(OUT_DIR, "titan-%s-v9-lora" % group)
    os.makedirs(output_path, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)

    vram = torch.cuda.get_device_properties(0).total_memory / 1e9
    print("\n" + "=" * 60)
    print(" TITAN V9.0 Parallel Training: %s" % group)
    print(" GPU: %s (%.1fGB)" % (torch.cuda.get_device_name(0), vram))
    print(" Model: %s" % hf_model)
    print(" LoRA: r=%d alpha=%d batch=%d grad_accum=%d" % (cfg["r"], cfg["alpha"], cfg["batch"], cfg["grad_accum"]))
    print("=" * 60)

    print("\n[1/5] Loading data...")
    examples = load_data(group)
    print("  Total: %d examples" % len(examples))
    if len(examples) == 0:
        print("  ERROR: No training data found! Skipping %s." % group)
        return False

    formatted = []
    for ex in examples:
        if group == "strategist":
            text = "### Instruction:\n%s\n\nThink step-by-step.\n\n### Response:\n%s" % (ex["instruction"], ex["output"])
        else:
            text = "### Instruction:\n%s\n\n### Response:\n%s" % (ex["instruction"], ex["output"])
        formatted.append({"text": text})

    dataset = Dataset.from_list(formatted)

    print("\n[2/5] Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(hf_model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        tokenizer.pad_token_id = tokenizer.eos_token_id

    max_seq = cfg["max_seq"]
    def tokenize_fn(batch):
        t = tokenizer(batch["text"], truncation=True, max_length=max_seq, padding="max_length", return_tensors=None)
        t["labels"] = t["input_ids"].copy()
        return t

    tokenized = dataset.map(tokenize_fn, batched=True, remove_columns=dataset.column_names, num_proc=4)
    print("  Tokenized: %d examples, max_seq=%d" % (len(tokenized), max_seq))

    print("\n[3/5] Loading model...")
    model = AutoModelForCausalLM.from_pretrained(
        hf_model, torch_dtype=torch.bfloat16, device_map="auto",
        trust_remote_code=True, low_cpu_mem_usage=True,
        attn_implementation="eager"
    )
    model.gradient_checkpointing_enable()
    model.config.use_cache = False
    param_b = sum(p.numel() for p in model.parameters()) / 1e9
    print("  Loaded: %.1fB params" % param_b)

    print("\n[4/5] Applying LoRA...")
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=cfg["r"], lora_alpha=cfg["alpha"], lora_dropout=cfg["dropout"],
        target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
        bias="none",
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    total_steps = len(tokenized) * cfg["epochs"] // (cfg["batch"] * cfg["grad_accum"])
    warmup = min(100, total_steps // 10)
    print("  Total steps: %d, warmup: %d" % (total_steps, warmup))

    print("\n[5/5] Training...")
    training_args = TrainingArguments(
        output_dir=output_path,
        num_train_epochs=cfg["epochs"],
        per_device_train_batch_size=cfg["batch"],
        gradient_accumulation_steps=cfg["grad_accum"],
        learning_rate=cfg["lr"],
        warmup_steps=warmup,
        weight_decay=0.01,
        logging_steps=10,
        save_strategy="epoch",
        bf16=True,
        optim="adamw_torch",
        lr_scheduler_type="cosine",
        dataloader_num_workers=2,
        report_to="none",
        gradient_checkpointing=True,
        remove_unused_columns=False,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized,
        data_collator=DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False),
        processing_class=tokenizer,
    )

    start_time = time.time()
    trainer.train()
    elapsed = time.time() - start_time
    print("\n  %s training complete in %.1f minutes" % (group, elapsed / 60))

    # Save
    model.save_pretrained(output_path)
    tokenizer.save_pretrained(output_path)
    print("  Model saved to %s" % output_path)

    # Log
    log = {
        "group": group, "model": hf_model,
        "examples": len(examples), "epochs": cfg["epochs"],
        "steps": total_steps, "elapsed_sec": int(elapsed),
        "timestamp": datetime.now().isoformat()
    }
    log_path = os.path.join(LOG_DIR, "parallel_%s.json" % group)
    with open(log_path, "w") as f:
        json.dump(log, f, indent=2)
    return True


if __name__ == "__main__":
    print("=" * 60)
    print(" TITAN V9.0 — Parallel GPU Training")
    print(" Training: strategist + fast (analyst on other GPU)")
    print("=" * 60)

    for group in ["strategist", "fast"]:
        try:
            ok = train_model(group)
            if ok:
                print("\n[OK] %s complete!" % group)
        except Exception as e:
            print("\n[ERROR] %s failed: %s" % (group, e))
            import traceback
            traceback.print_exc()

    # Pack results
    print("\n[PACK] Creating results archive...")
    os.system("cd /workspace/training && tar czf /workspace/titan_v9_parallel_models.tar.gz models_v9/ logs/")
    print("[DONE] All parallel training complete!")
    print("  Results: /workspace/titan_v9_parallel_models.tar.gz")
