#!/usr/bin/env python3
"""
TITAN V8.3 — Advanced GPU Training Script
==========================================
Runs on Vast.ai RTX 4090 (or any CUDA GPU).
Trains all 3 models: titan-analyst, titan-strategist, titan-fast

Features:
- LoRA rank 32 with 7 target modules (attention + MLP)
- Cosine LR schedule with warmup
- FP16 mixed precision on GPU
- Train/validation split (90/10)
- Per-epoch evaluation and checkpointing
- Automatic model merging and GGUF export
"""

import os
import sys
import json
import torch
import gc
from pathlib import Path
from datetime import datetime
from datasets import load_dataset, Dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling,
)
from peft import LoraConfig, get_peft_model, PeftModel

# ═══════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════

DATA_DIR = Path("/workspace/data_v2")
OUTPUT_DIR = Path("/workspace/output")
RESULTS_FILE = OUTPUT_DIR / "training_results.json"

TASKS = {
    "analyst": {
        "base_model": "Qwen/Qwen2.5-7B-Instruct",
        "data_files": [
            "bin_analysis.jsonl",
            "target_recon.jsonl",
            "fingerprint_coherence.jsonl",
            "identity_graph.jsonl",
            "environment_coherence.jsonl",
            "avs_prevalidation.jsonl",
        ],
        "system_prompt": (
            "You are titan-analyst, an expert AI for payment intelligence analysis. "
            "You provide detailed BIN analysis, target reconnaissance, fingerprint validation, "
            "identity graph scoring, environment coherence checks, and AVS pre-validation. "
            "Always respond with valid JSON containing a 'reasoning' field explaining your analysis, "
            "followed by structured data fields. Be precise, calibrated, and thorough."
        ),
        "epochs": 3,
        "max_examples": 1200,
        "lora_rank": 32,
        "learning_rate": 2e-4,
    },
    "strategist": {
        "base_model": "Qwen/Qwen2.5-7B-Instruct",
        "data_files": [
            "decline_autopsy.jsonl",
            "card_rotation.jsonl",
            "velocity_schedule.jsonl",
            "session_rhythm.jsonl",
        ],
        "system_prompt": (
            "You are titan-strategist, an expert AI for strategic planning and optimization. "
            "You perform decline root-cause analysis, card rotation optimization, velocity scheduling, "
            "and session rhythm planning. Always respond with valid JSON containing a 'reasoning' field "
            "with detailed chain-of-thought analysis, followed by actionable recommendations. "
            "Consider multiple factors, provide alternatives, and explain causal relationships."
        ),
        "epochs": 5,
        "max_examples": 800,
        "lora_rank": 32,
        "learning_rate": 2e-4,
    },
    "fast": {
        "base_model": "mistralai/Mistral-7B-Instruct-v0.2",
        "data_files": [
            "bin_analysis.jsonl",
            "target_recon.jsonl",
            "session_rhythm.jsonl",
            "velocity_schedule.jsonl",
        ],
        "system_prompt": (
            "You are titan-fast, a quick-response AI for real-time decisions. "
            "Provide concise JSON responses with a brief 'reasoning' field. "
            "Optimize for speed and accuracy. Focus on actionable outputs."
        ),
        "epochs": 3,
        "max_examples": 800,
        "lora_rank": 16,
        "learning_rate": 3e-4,
    },
}

# ═══════════════════════════════════════════════════════════════
# DATA PROCESSING
# ═══════════════════════════════════════════════════════════════

def format_chat_example(example, system_prompt, tokenizer, max_length=2048):
    """Format training example as chat conversation."""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": example["prompt"]},
        {"role": "assistant", "content": example["response"]},
    ]
    
    text = tokenizer.apply_chat_template(
        messages, 
        tokenize=False, 
        add_generation_prompt=False
    )
    
    tokenized = tokenizer(
        text,
        truncation=True,
        max_length=max_length,
        padding="max_length",
        return_tensors=None,
    )
    tokenized["labels"] = tokenized["input_ids"].copy()
    
    return tokenized


def load_task_data(task_config, system_prompt, tokenizer):
    """Load and tokenize all data files for a task."""
    all_examples = []
    
    for data_file in task_config["data_files"]:
        file_path = DATA_DIR / data_file
        if not file_path.exists():
            print(f"  ⚠️  Missing: {data_file}")
            continue
        
        with open(file_path) as f:
            for line in f:
                try:
                    example = json.loads(line)
                    all_examples.append(example)
                except json.JSONDecodeError:
                    continue
        
        print(f"  ✓ {data_file}: {len(all_examples)} total")
    
    # Limit examples
    if task_config.get("max_examples") and len(all_examples) > task_config["max_examples"]:
        import random
        random.shuffle(all_examples)
        all_examples = all_examples[:task_config["max_examples"]]
        print(f"  ℹ️  Limited to {task_config['max_examples']} examples")
    
    # Split: 90% train, 10% validation
    split_idx = int(len(all_examples) * 0.9)
    train_examples = all_examples[:split_idx]
    val_examples = all_examples[split_idx:]
    
    print(f"  ✓ Split: {len(train_examples)} train, {len(val_examples)} validation")
    
    # Tokenize
    train_data = []
    for ex in train_examples:
        tokenized = format_chat_example(ex, system_prompt, tokenizer)
        train_data.append(tokenized)
    
    val_data = []
    for ex in val_examples:
        tokenized = format_chat_example(ex, system_prompt, tokenizer)
        val_data.append(tokenized)
    
    train_dataset = Dataset.from_list(train_data)
    val_dataset = Dataset.from_list(val_data)
    
    return train_dataset, val_dataset


# ═══════════════════════════════════════════════════════════════
# TRAINING
# ═══════════════════════════════════════════════════════════════

def train_model(task_name, task_config):
    """Train a single model with advanced LoRA configuration."""
    print(f"\n{'='*60}")
    print(f"🚀 Training titan-{task_name}")
    print(f"{'='*60}")
    
    base_model = task_config["base_model"]
    output_dir = OUTPUT_DIR / task_name
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load tokenizer
    print(f"  Loading tokenizer: {base_model}")
    tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        tokenizer.pad_token_id = tokenizer.eos_token_id
    
    # Load model
    print(f"  Loading model: {base_model}")
    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        torch_dtype=torch.float16,
        device_map="auto",
        trust_remote_code=True,
    )
    model.config.use_cache = False
    
    # LoRA configuration — expanded target modules for deeper fine-tuning
    lora_rank = task_config.get("lora_rank", 32)
    
    # Detect target modules based on model architecture
    if "qwen" in base_model.lower():
        target_modules = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
    elif "mistral" in base_model.lower():
        target_modules = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
    else:
        target_modules = ["q_proj", "k_proj", "v_proj", "o_proj"]
    
    lora_config = LoraConfig(
        r=lora_rank,
        lora_alpha=lora_rank * 2,
        target_modules=target_modules,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )
    
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    
    # Load data
    print(f"\n  Loading training data...")
    train_dataset, val_dataset = load_task_data(
        task_config, task_config["system_prompt"], tokenizer
    )
    
    # Training arguments — advanced configuration
    num_train_examples = len(train_dataset)
    batch_size = 4
    grad_accum = 4
    effective_batch = batch_size * grad_accum
    steps_per_epoch = max(1, num_train_examples // effective_batch)
    total_steps = steps_per_epoch * task_config["epochs"]
    warmup_steps = max(1, int(total_steps * 0.10))
    
    print(f"\n  Training configuration:")
    print(f"    Examples: {num_train_examples} train, {len(val_dataset)} val")
    print(f"    Batch size: {batch_size} × {grad_accum} = {effective_batch} effective")
    print(f"    Steps/epoch: {steps_per_epoch}")
    print(f"    Total steps: {total_steps}")
    print(f"    Warmup steps: {warmup_steps}")
    print(f"    LoRA rank: {lora_rank}, alpha: {lora_rank * 2}")
    print(f"    Target modules: {target_modules}")
    print(f"    Learning rate: {task_config['learning_rate']}")
    
    training_args = TrainingArguments(
        output_dir=str(output_dir / "checkpoints"),
        num_train_epochs=task_config["epochs"],
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        gradient_accumulation_steps=grad_accum,
        learning_rate=task_config["learning_rate"],
        lr_scheduler_type="cosine",
        warmup_steps=warmup_steps,
        fp16=True,
        logging_steps=10,
        eval_strategy="epoch",
        save_strategy="epoch",
        save_total_limit=2,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        optim="adamw_torch",
        weight_decay=0.01,
        max_grad_norm=1.0,
        report_to="none",
        dataloader_num_workers=2,
        remove_unused_columns=False,
    )
    
    # Data collator
    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False,
    )
    
    # Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        data_collator=data_collator,
    )
    
    # Train
    print(f"\n  🔥 Starting training...")
    start_time = datetime.now()
    train_result = trainer.train()
    elapsed = (datetime.now() - start_time).total_seconds()
    
    # Save final LoRA adapter
    lora_output = output_dir / "lora_adapter"
    model.save_pretrained(str(lora_output))
    tokenizer.save_pretrained(str(lora_output))
    
    # Get metrics
    metrics = train_result.metrics
    eval_metrics = trainer.evaluate()
    
    print(f"\n  ✅ titan-{task_name} training complete!")
    print(f"    Time: {elapsed/60:.1f} minutes")
    print(f"    Final train loss: {metrics.get('train_loss', 'N/A')}")
    print(f"    Final eval loss: {eval_metrics.get('eval_loss', 'N/A')}")
    print(f"    LoRA saved to: {lora_output}")
    
    result = {
        "task": task_name,
        "base_model": base_model,
        "train_time_seconds": elapsed,
        "train_loss": metrics.get("train_loss"),
        "eval_loss": eval_metrics.get("eval_loss"),
        "train_examples": num_train_examples,
        "val_examples": len(val_dataset),
        "epochs": task_config["epochs"],
        "lora_rank": lora_rank,
        "lora_path": str(lora_output),
    }
    
    # Cleanup GPU memory
    del model, trainer
    gc.collect()
    torch.cuda.empty_cache()
    
    return result


def merge_lora_weights(task_name, task_config):
    """Merge LoRA adapter into base model for deployment."""
    print(f"\n  Merging LoRA weights for titan-{task_name}...")
    
    lora_path = OUTPUT_DIR / task_name / "lora_adapter"
    merged_path = OUTPUT_DIR / task_name / "merged"
    
    # Load base model
    base_model = task_config["base_model"]
    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        torch_dtype=torch.float16,
        device_map="auto",
        trust_remote_code=True,
    )
    tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
    
    # Load and merge LoRA
    model = PeftModel.from_pretrained(model, str(lora_path))
    model = model.merge_and_unload()
    
    # Save merged model
    model.save_pretrained(str(merged_path))
    tokenizer.save_pretrained(str(merged_path))
    
    print(f"  ✅ Merged model saved to: {merged_path}")
    
    del model
    gc.collect()
    torch.cuda.empty_cache()
    
    return str(merged_path)


# ═══════════════════════════════════════════════════════════════
# EVALUATION
# ═══════════════════════════════════════════════════════════════

def evaluate_model(task_name, task_config):
    """Evaluate fine-tuned model on test prompts."""
    print(f"\n  📊 Evaluating titan-{task_name}...")
    
    lora_path = OUTPUT_DIR / task_name / "lora_adapter"
    base_model = task_config["base_model"]
    
    # Load model with LoRA
    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        torch_dtype=torch.float16,
        device_map="auto",
        trust_remote_code=True,
    )
    tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    model = PeftModel.from_pretrained(model, str(lora_path))
    model.eval()
    
    # Load test prompts (first 20 from each data file)
    test_prompts = []
    for data_file in task_config["data_files"][:2]:
        file_path = DATA_DIR / data_file
        if file_path.exists():
            with open(file_path) as f:
                for i, line in enumerate(f):
                    if i >= 10:
                        break
                    example = json.loads(line)
                    test_prompts.append(example)
    
    # Generate and evaluate
    json_valid = 0
    has_reasoning = 0
    total = len(test_prompts)
    
    for prompt_data in test_prompts[:20]:
        messages = [
            {"role": "system", "content": task_config["system_prompt"]},
            {"role": "user", "content": prompt_data["prompt"]},
        ]
        
        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(text, return_tensors="pt").to(model.device)
        
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=1024,
                temperature=0.1,
                do_sample=True,
                top_p=0.9,
            )
        
        response = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        
        # Check JSON validity
        try:
            parsed = json.loads(response)
            json_valid += 1
            if "reasoning" in parsed:
                has_reasoning += 1
        except json.JSONDecodeError:
            # Try extracting JSON from response
            try:
                start = response.index("{")
                end = response.rindex("}") + 1
                parsed = json.loads(response[start:end])
                json_valid += 1
                if "reasoning" in parsed:
                    has_reasoning += 1
            except (ValueError, json.JSONDecodeError):
                pass
    
    eval_result = {
        "json_validity": json_valid / total if total > 0 else 0,
        "reasoning_rate": has_reasoning / total if total > 0 else 0,
        "total_tested": total,
    }
    
    print(f"    JSON validity: {json_valid}/{total} ({eval_result['json_validity']*100:.0f}%)")
    print(f"    Reasoning present: {has_reasoning}/{total} ({eval_result['reasoning_rate']*100:.0f}%)")
    
    del model
    gc.collect()
    torch.cuda.empty_cache()
    
    return eval_result


# ═══════════════════════════════════════════════════════════════
# MAIN PIPELINE
# ═══════════════════════════════════════════════════════════════

def main():
    print(f"\n{'='*60}")
    print(f"⚡ TITAN V8.3 — Advanced GPU Training Pipeline")
    print(f"{'='*60}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")
    if torch.cuda.is_available():
        print(f"VRAM: {torch.cuda.get_device_properties(0).total_mem / 1e9:.1f}GB")
    print(f"Tasks: {', '.join(TASKS.keys())}")
    print(f"Data dir: {DATA_DIR}")
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    results = {
        "started": datetime.now().isoformat(),
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU",
        "models": {},
    }
    
    total_start = datetime.now()
    
    # Train each model
    for task_name, task_config in TASKS.items():
        try:
            # Stage 1: Train
            train_result = train_model(task_name, task_config)
            results["models"][task_name] = train_result
            
            # Stage 2: Evaluate
            eval_result = evaluate_model(task_name, task_config)
            results["models"][task_name]["evaluation"] = eval_result
            
            # Stage 3: Merge LoRA
            merged_path = merge_lora_weights(task_name, task_config)
            results["models"][task_name]["merged_path"] = merged_path
            
        except Exception as e:
            print(f"\n  ❌ Failed training titan-{task_name}: {e}")
            import traceback
            traceback.print_exc()
            results["models"][task_name] = {"error": str(e)}
    
    total_elapsed = (datetime.now() - total_start).total_seconds()
    results["total_time_seconds"] = total_elapsed
    results["completed"] = datetime.now().isoformat()
    
    # Save results
    with open(RESULTS_FILE, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n{'='*60}")
    print(f"⚡ ALL TRAINING COMPLETE")
    print(f"{'='*60}")
    print(f"Total time: {total_elapsed/60:.1f} minutes")
    
    for task_name, result in results["models"].items():
        if "error" in result:
            print(f"  ❌ titan-{task_name}: FAILED — {result['error']}")
        else:
            eval_info = result.get("evaluation", {})
            print(f"  ✅ titan-{task_name}: loss={result.get('train_loss', 'N/A'):.4f}, "
                  f"eval={result.get('eval_loss', 'N/A'):.4f}, "
                  f"json={eval_info.get('json_validity', 0)*100:.0f}%, "
                  f"time={result.get('train_time_seconds', 0)/60:.1f}min")
    
    print(f"\nResults: {RESULTS_FILE}")


if __name__ == "__main__":
    main()
