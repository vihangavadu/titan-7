#!/usr/bin/env python3
"""Rent a fast GPU on Vast.ai and start strategist+fast training in parallel.
The existing RTX 3090 Ti instance keeps training analyst.
"""
import requests, json, time, subprocess, sys, os

API_KEY = "460557583433320c6f66efd5848cd43497f10cac9b4d9965377926885a24a6ff"
BASE = "https://console.vast.ai/api/v0"
HEADERS = {"Authorization": "Bearer " + API_KEY, "Content-Type": "application/json"}
IMAGE = "pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime"
VPS_SSH_KEY = "/root/.ssh/id_rsa"

TARGET_OFFER_ID = None  # Will be set by search

def api(method, endpoint, payload=None):
    url = BASE + "/" + endpoint
    try:
        if method == "GET":
            r = requests.get(url, headers=HEADERS, timeout=30)
        elif method == "POST":
            r = requests.post(url, headers=HEADERS, json=payload, timeout=30)
        elif method == "PUT":
            r = requests.put(url, headers=HEADERS, json=payload, timeout=30)
        elif method == "DELETE":
            r = requests.delete(url, headers=HEADERS, timeout=30)
        else:
            return None
        if r.status_code in (200, 201):
            return r.json()
        print("API %d: %s" % (r.status_code, r.text[:200]))
        return None
    except Exception as e:
        print("API error: %s" % e)
        return None


def find_best_gpu():
    """Find best available GPU: prefer H100 > A100 > RTX 6000 Ada > L40S > RTX 5090."""
    print("[1/6] Searching for fast GPU...")
    body = {
        "verified": {"eq": True},
        "rentable": {"eq": True},
        "rented": {"eq": False},
        "num_gpus": {"eq": 1},
        "gpu_ram": {"gte": 40000},
        "disk_space": {"gte": 50},
        "reliability": {"gte": 0.90},
        "cuda_max_good": {"gte": 12.4},
        "order": [["dph_total", "asc"]],
        "limit": 20,
        "type": "ondemand"
    }
    data = api("POST", "bundles/", body)
    if not data or not data.get("offers"):
        print("No offers found!")
        return None

    # Rank by preference: H100 > A100 80GB > L40S > RTX 6000 Ada > A100 40GB > A40
    priority = {
        "H100": 1, "H100_SXM": 1, "H100_PCIE": 1,
        "A100 SXM4": 2, "A100 PCIE": 3, "A100_SXM4": 2, "A100_PCIE": 3,
        "L40S": 4, "RTX 6000Ada": 5, "RTX 6000 Ada": 5,
        "A40": 6, "RTX 5090": 7,
    }
    offers = data["offers"]

    # Filter: max $3.50/hr to stay in budget
    offers = [o for o in offers if o.get("dph_total", 99) <= 3.50]

    # Sort by: priority tier first, then price
    def rank(o):
        name = o.get("gpu_name", "")
        tier = priority.get(name, 10)
        return (tier, o.get("dph_total", 99))

    offers.sort(key=rank)

    best = offers[0]
    print("  Best: %s @ $%.3f/hr | %dMB VRAM | %s" % (
        best.get("gpu_name"), best.get("dph_total", 0),
        best.get("gpu_ram", 0), best.get("geolocation", "?")))
    return best


def rent_instance(offer):
    """Rent the GPU instance."""
    offer_id = offer["id"]
    print("[2/6] Renting instance (offer %s)..." % offer_id)

    body = {
        "client_id": "me",
        "image": IMAGE,
        "disk": 60,
        "onstart": "",
        "runtype": "ssh ssh_proxy",
        "label": "titan-v9-parallel"
    }
    result = api("PUT", "asks/%s/" % offer_id, body)
    if not result:
        print("Failed to rent!")
        return None

    instance_id = result.get("new_contract")
    if not instance_id:
        print("No instance ID in response: %s" % json.dumps(result)[:200])
        return None

    print("  Instance created: %s" % instance_id)
    return instance_id


def wait_for_instance(instance_id, timeout=300):
    """Wait for instance to be ready with SSH."""
    print("[3/6] Waiting for instance to start...")
    start = time.time()
    while time.time() - start < timeout:
        data = api("GET", "instances/")
        if data:
            for inst in data.get("instances", []):
                if inst.get("id") == instance_id:
                    status = inst.get("actual_status", "?")
                    ssh_host = inst.get("ssh_host", "")
                    ssh_port = inst.get("ssh_port", 0)
                    print("  status=%s  ssh=%s:%s" % (status, ssh_host, ssh_port))
                    if status == "running" and ssh_host and ssh_port:
                        time.sleep(15)  # Wait for SSH daemon
                        return ssh_host, ssh_port
        time.sleep(10)
    print("Timeout waiting for instance!")
    return None, None


def setup_instance(ssh_host, ssh_port):
    """Install deps and transfer training data."""
    print("[4/6] Setting up instance...")

    def ssh_cmd(cmd, timeout=300):
        full = [
            "ssh", "-p", str(ssh_port),
            "-o", "StrictHostKeyChecking=no",
            "-o", "ConnectTimeout=15",
            "-i", VPS_SSH_KEY,
            "root@%s" % ssh_host,
            cmd
        ]
        try:
            r = subprocess.run(full, capture_output=True, text=True, timeout=timeout)
            return r.stdout + r.stderr
        except Exception as e:
            return "ERROR: %s" % e

    def scp_cmd(local, remote, timeout=120):
        full = [
            "scp", "-P", str(ssh_port),
            "-o", "StrictHostKeyChecking=no",
            "-i", VPS_SSH_KEY,
            local,
            "root@%s:%s" % (ssh_host, remote)
        ]
        try:
            r = subprocess.run(full, capture_output=True, text=True, timeout=timeout)
            return r.stdout + r.stderr
        except Exception as e:
            return "ERROR: %s" % e

    # Install ML deps
    print("  Installing dependencies...")
    out = ssh_cmd("pip install transformers peft datasets accelerate bitsandbytes sentencepiece scipy 2>&1 | tail -5")
    print("  " + out.strip().split("\n")[-1] if out.strip() else "  (done)")

    # Check GPU
    out = ssh_cmd("nvidia-smi --query-gpu=name,memory.total --format=csv,noheader")
    print("  GPU: %s" % out.strip())

    # Create workspace
    ssh_cmd("mkdir -p /workspace/training/data_v9 /workspace/training/models_v9 /workspace/training/logs")

    # Transfer training data from VPS local data
    print("  Transferring training data (this may take a minute)...")

    # Pack data on VPS first
    pack_result = subprocess.run([
        "tar", "czf", "/tmp/titan_parallel_data.tar.gz",
        "-C", "/opt/titan/training",
        "data_v9/"
    ], capture_output=True, text=True, timeout=120)

    # SCP the archive to the new instance
    scp_result = scp_cmd("/tmp/titan_parallel_data.tar.gz", "/workspace/titan_parallel_data.tar.gz", timeout=300)
    print("  SCP: %s" % scp_result.strip().split("\n")[-1] if scp_result.strip() else "  (done)")

    # Extract
    out = ssh_cmd("cd /workspace && tar xzf titan_parallel_data.tar.gz -C training/ && ls training/data_v9/ | wc -l")
    print("  Files extracted: %s" % out.strip().split("\n")[-1])

    return ssh_cmd, scp_cmd


def create_training_script():
    """Create the GPU training script optimized for 48GB VRAM."""
    script = r'''#!/usr/bin/env python3
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
    print("  Loaded: %.1fB params on %s" % (param_b, next(model.parameters()).device))

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
'''

    with open("/tmp/gpu_train_parallel.py", "w") as f:
        f.write(script)
    return "/tmp/gpu_train_parallel.py"


def main():
    # Step 1: Find best GPU
    offer = find_best_gpu()
    if not offer:
        sys.exit(1)

    cost_hr = offer.get("dph_total", 0)
    gpu_name = offer.get("gpu_name", "?")
    vram = offer.get("gpu_ram", 0)

    # Estimate time: strategist ~1.5h + fast ~0.8h on 48GB GPU
    est_hours = 3.0  # conservative
    est_cost = est_hours * cost_hr
    existing_cost = 3.5 * 0.072  # remaining analyst on 3090 Ti
    total_est = est_cost + existing_cost
    print("  Estimated: %.1fh @ $%.3f/hr = $%.2f (+ $%.2f existing = $%.2f total)" % (
        est_hours, cost_hr, est_cost, existing_cost, total_est))

    if total_est > 15.0:
        print("WARNING: Estimated cost $%.2f exceeds $15 budget!" % total_est)

    # Step 2: Rent instance
    instance_id = rent_instance(offer)
    if not instance_id:
        sys.exit(1)

    # Step 3: Wait for it
    ssh_host, ssh_port = wait_for_instance(instance_id)
    if not ssh_host:
        print("Destroying failed instance...")
        api("DELETE", "instances/%s/" % instance_id)
        sys.exit(1)

    print("  SSH ready: %s:%s" % (ssh_host, ssh_port))

    # Step 4: Setup
    ssh_cmd, scp_cmd = setup_instance(ssh_host, ssh_port)

    # Step 5: Upload training script
    print("[5/6] Uploading training script...")
    script_path = create_training_script()
    scp_result = subprocess.run([
        "scp", "-P", str(ssh_port),
        "-o", "StrictHostKeyChecking=no",
        "-i", VPS_SSH_KEY,
        script_path,
        "root@%s:/workspace/training/gpu_train_parallel.py" % ssh_host
    ], capture_output=True, text=True, timeout=60)
    print("  Uploaded training script")

    # Step 6: Start training in tmux
    print("[6/6] Starting parallel training in tmux...")
    out = ssh_cmd(
        "tmux new-session -d -s training 'cd /workspace/training && "
        "python3 -u gpu_train_parallel.py 2>&1 | tee logs/parallel_training.log'"
    )
    time.sleep(5)
    out = ssh_cmd("tmux list-sessions 2>&1")
    print("  tmux: %s" % out.strip())

    # Summary
    print("\n" + "=" * 60)
    print(" PARALLEL TRAINING LAUNCHED!")
    print("=" * 60)
    print(" New instance: %s (%s, %dMB VRAM)" % (instance_id, gpu_name, vram))
    print(" Cost: $%.3f/hr" % cost_hr)
    print(" SSH: ssh -p %s -i %s root@%s" % (ssh_port, VPS_SSH_KEY, ssh_host))
    print(" Training: strategist + fast (analyst continues on 3090 Ti)")
    print(" Monitor: ssh -p %s root@%s 'tail -20 /workspace/training/logs/parallel_training.log'" % (ssh_port, ssh_host))
    print(" Destroy: python3 -c 'import requests; requests.delete(\"%s/instances/%s/\", headers={\"Authorization\": \"Bearer %s\"})'" % (BASE, instance_id, API_KEY))
    print("=" * 60)


if __name__ == "__main__":
    main()
