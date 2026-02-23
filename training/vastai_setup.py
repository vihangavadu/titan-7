#!/usr/bin/env python3
"""
TITAN V8.3 — Vast.ai GPU Training Setup
========================================
Automated GPU training on Vast.ai for 40x faster fine-tuning.
Cost: ~$1 for all 3 models (2 hours on RTX 3090/4090)
"""

import os
import json
import time
import requests
from pathlib import Path
from datetime import datetime

# Vast.ai API Configuration
VASTAI_API_KEY = "460557583433320c6f66efd5848cd43497f10cac9b4d9965377926885a24a6ff"
VASTAI_API_BASE = "https://console.vast.ai/api/v0"

# Training configuration
TRAINING_DATA_DIR = Path("/opt/titan/training/data")
OUTPUT_DIR = Path("/opt/titan/training/vastai_models")
LOGS_DIR = Path("/opt/titan/training/logs")

# GPU preferences (in order of preference)
GPU_PREFERENCES = [
    {"gpu_name": "RTX 3090", "max_price": 0.35},
    {"gpu_name": "RTX 4090", "max_price": 0.60},
    {"gpu_name": "RTX 3080", "max_price": 0.30},
    {"gpu_name": "A40", "max_price": 0.80},
]

def vastai_request(endpoint, method="GET", data=None):
    """Make request to Vast.ai API."""
    headers = {"Accept": "application/json"}
    url = f"{VASTAI_API_BASE}/{endpoint}?api_key={VASTAI_API_KEY}"
    
    if method == "GET":
        response = requests.get(url, headers=headers)
    elif method == "POST":
        response = requests.post(url, headers=headers, json=data)
    elif method == "PUT":
        response = requests.put(url, headers=headers, json=data)
    elif method == "DELETE":
        response = requests.delete(url, headers=headers)
    
    if response.status_code in [200, 201]:
        return response.json()
    else:
        print(f"API Error {response.status_code}: {response.text}")
        return None


def find_best_gpu():
    """Find the cheapest available GPU that meets requirements."""
    print("\n🔍 Searching for available GPUs...")
    
    offers = vastai_request("bundles")
    if not offers:
        print("❌ Failed to fetch GPU offers")
        return None
    
    # Filter and sort offers
    suitable_offers = []
    for offer in offers.get("offers", []):
        gpu_name = offer.get("gpu_name", "")
        dph_total = offer.get("dph_total", 999)  # dollars per hour
        gpu_ram = offer.get("gpu_ram", 0)
        disk_space = offer.get("disk_space", 0)
        
        # Requirements: 24GB+ VRAM, 50GB+ disk
        if gpu_ram >= 24000 and disk_space >= 50:
            for pref in GPU_PREFERENCES:
                if pref["gpu_name"] in gpu_name and dph_total <= pref["max_price"]:
                    suitable_offers.append({
                        "id": offer.get("id"),
                        "gpu_name": gpu_name,
                        "price": dph_total,
                        "gpu_ram": gpu_ram / 1000,  # Convert to GB
                        "disk_space": disk_space,
                        "cuda_vers": offer.get("cuda_max_good", ""),
                    })
                    break
    
    if not suitable_offers:
        print("❌ No suitable GPUs found")
        return None
    
    # Sort by price
    suitable_offers.sort(key=lambda x: x["price"])
    
    print(f"\n✅ Found {len(suitable_offers)} suitable GPUs:")
    for i, offer in enumerate(suitable_offers[:5], 1):
        print(f"  {i}. {offer['gpu_name']} - ${offer['price']:.3f}/hr - {offer['gpu_ram']:.0f}GB VRAM")
    
    return suitable_offers[0]


def create_instance(offer_id):
    """Create a Vast.ai instance."""
    print(f"\n🚀 Creating instance {offer_id}...")
    
    # Docker image with PyTorch + transformers + PEFT
    image = "pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime"
    
    # Startup script to install dependencies
    onstart = """#!/bin/bash
apt-get update && apt-get install -y git wget
pip install transformers==4.48.0 peft==0.14.0 datasets==3.3.0 accelerate==1.3.0 bitsandbytes scipy
mkdir -p /workspace/training
echo "Setup complete"
"""
    
    data = {
        "client_id": "me",
        "image": image,
        "disk": 50,
        "onstart": onstart,
        "runtype": "ssh",
    }
    
    result = vastai_request(f"asks/{offer_id}/", method="PUT", data=data)
    
    if result and result.get("success"):
        instance_id = result.get("new_contract")
        print(f"✅ Instance created: {instance_id}")
        return instance_id
    else:
        print("❌ Failed to create instance")
        return None


def wait_for_instance(instance_id, timeout=300):
    """Wait for instance to be ready."""
    print(f"\n⏳ Waiting for instance {instance_id} to start...")
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        instances = vastai_request("instances")
        if instances:
            for inst in instances.get("instances", []):
                if inst.get("id") == instance_id:
                    status = inst.get("actual_status")
                    if status == "running":
                        ssh_host = inst.get("ssh_host")
                        ssh_port = inst.get("ssh_port")
                        print(f"✅ Instance running: {ssh_host}:{ssh_port}")
                        return {
                            "ssh_host": ssh_host,
                            "ssh_port": ssh_port,
                            "id": instance_id
                        }
                    else:
                        print(f"  Status: {status}")
        
        time.sleep(10)
    
    print("❌ Timeout waiting for instance")
    return None


def upload_training_data(instance_info):
    """Upload training data to instance via SCP."""
    print("\n📤 Uploading training data...")
    
    # Create tarball of training data
    import tarfile
    tarball_path = OUTPUT_DIR / "training_data.tar.gz"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    with tarfile.open(tarball_path, "w:gz") as tar:
        tar.add(TRAINING_DATA_DIR, arcname="data")
    
    print(f"  ✓ Created tarball: {tarball_path} ({tarball_path.stat().st_size / 1024:.1f} KB)")
    
    # SCP upload command
    ssh_host = instance_info["ssh_host"]
    ssh_port = instance_info["ssh_port"]
    
    scp_cmd = f'scp -P {ssh_port} -o StrictHostKeyChecking=no {tarball_path} root@{ssh_host}:/workspace/training_data.tar.gz'
    
    print(f"  Upload command: {scp_cmd}")
    print("  ⚠️  You'll need to run this manually (Vast.ai uses SSH keys)")
    
    return str(tarball_path)


def create_training_script():
    """Create GPU training script for Vast.ai instance."""
    script = """#!/usr/bin/env python3
import os
import json
import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from datasets import load_dataset
from datetime import datetime

print(f"GPU Available: {torch.cuda.is_available()}")
print(f"GPU Name: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None'}")
print(f"GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f}GB")

# Training configuration
TASKS = {
    "analyst": {
        "base_model": "Qwen/Qwen2.5-7B-Instruct",
        "data_files": ["bin_analysis.jsonl", "target_recon.jsonl", "fingerprint_coherence.jsonl", 
                      "identity_graph.jsonl", "environment_coherence.jsonl", "avs_prevalidation.jsonl"],
        "epochs": 3,
        "max_examples": 300,
    },
    "strategist": {
        "base_model": "Qwen/Qwen2.5-7B-Instruct",
        "data_files": ["decline_autopsy.jsonl", "card_rotation.jsonl", "velocity_schedule.jsonl", "session_rhythm.jsonl"],
        "epochs": 5,
        "max_examples": 200,
    },
    "fast": {
        "base_model": "mistralai/Mistral-7B-Instruct-v0.2",
        "data_files": ["bin_analysis.jsonl", "target_recon.jsonl"],
        "epochs": 3,
        "max_examples": 100,
    },
}

def train_model(task_name, config):
    print(f"\\n{'='*60}")
    print(f"Training {task_name}")
    print(f"{'='*60}")
    
    # Load model
    print(f"Loading {config['base_model']}...")
    model = AutoModelForCausalLM.from_pretrained(
        config['base_model'],
        torch_dtype=torch.float16,
        device_map="auto",
        trust_remote_code=True,
    )
    tokenizer = AutoTokenizer.from_pretrained(config['base_model'], trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token
    
    # LoRA configuration
    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )
    
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    
    # Load dataset
    dataset = load_dataset("json", data_files={"train": [f"data/{f}" for f in config['data_files']]})
    
    # Training arguments
    training_args = TrainingArguments(
        output_dir=f"/workspace/output/{task_name}",
        num_train_epochs=config['epochs'],
        per_device_train_batch_size=4,
        gradient_accumulation_steps=2,
        learning_rate=2e-4,
        fp16=True,
        logging_steps=10,
        save_strategy="epoch",
        optim="adamw_torch",
    )
    
    # Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset["train"],
    )
    
    # Train
    print(f"Starting training...")
    start_time = datetime.now()
    trainer.train()
    elapsed = (datetime.now() - start_time).total_seconds()
    
    # Save
    model.save_pretrained(f"/workspace/output/{task_name}_lora")
    tokenizer.save_pretrained(f"/workspace/output/{task_name}_lora")
    
    print(f"✅ {task_name} complete in {elapsed/60:.1f} minutes")
    
    return elapsed

# Extract training data
os.system("cd /workspace && tar -xzf training_data.tar.gz")

# Train all models
results = {}
total_start = datetime.now()

for task_name, config in TASKS.items():
    try:
        elapsed = train_model(task_name, config)
        results[task_name] = {"success": True, "time": elapsed}
    except Exception as e:
        print(f"❌ {task_name} failed: {e}")
        results[task_name] = {"success": False, "error": str(e)}

total_elapsed = (datetime.now() - total_start).total_seconds()

# Save results
with open("/workspace/output/training_results.json", "w") as f:
    json.dump({
        "results": results,
        "total_time": total_elapsed,
        "completed": datetime.now().isoformat(),
    }, f, indent=2)

print(f"\\n{'='*60}")
print(f"ALL TRAINING COMPLETE")
print(f"Total time: {total_elapsed/60:.1f} minutes")
print(f"{'='*60}")
"""
    
    script_path = OUTPUT_DIR / "vastai_train.py"
    with open(script_path, "w") as f:
        f.write(script)
    
    print(f"\n✅ Training script created: {script_path}")
    return script_path


def main():
    """Main Vast.ai setup workflow."""
    print(f"\n{'='*60}")
    print(f"TITAN V8.3 — Vast.ai GPU Training Setup")
    print(f"{'='*60}")
    print(f"API Key: {VASTAI_API_KEY[:16]}...{VASTAI_API_KEY[-8:]}")
    
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOGS_DIR / f"vastai_setup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    # Step 1: Find best GPU
    best_gpu = find_best_gpu()
    if not best_gpu:
        return
    
    print(f"\n✅ Selected: {best_gpu['gpu_name']} @ ${best_gpu['price']:.3f}/hour")
    print(f"   Estimated cost for 2 hours: ${best_gpu['price'] * 2:.2f}")
    
    # Step 2: Create training script
    script_path = create_training_script()
    
    # Step 3: Create tarball
    print("\n📦 Preparing training data...")
    tarball_path = upload_training_data({"ssh_host": "pending", "ssh_port": "pending"})
    
    # Save setup info
    setup_info = {
        "gpu": best_gpu,
        "script": str(script_path),
        "tarball": tarball_path,
        "created": datetime.now().isoformat(),
        "next_steps": [
            "1. Review GPU selection and pricing",
            "2. Run: python vastai_deploy.py to create instance",
            "3. Upload data and script to instance",
            "4. Run training script on GPU",
            "5. Download trained models",
        ]
    }
    
    with open(log_file, "w") as f:
        json.dump(setup_info, f, indent=2)
    
    print(f"\n{'='*60}")
    print(f"SETUP COMPLETE")
    print(f"{'='*60}")
    print(f"GPU: {best_gpu['gpu_name']}")
    print(f"Price: ${best_gpu['price']:.3f}/hour")
    print(f"Estimated total: ${best_gpu['price'] * 2:.2f}")
    print(f"\nSetup saved to: {log_file}")
    print(f"\nNext: Run vastai_deploy.py to create instance")


if __name__ == "__main__":
    main()
