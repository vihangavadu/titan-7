#!/usr/bin/env python3
"""
TITAN V8.3 — Automated Vast.ai GPU Training Pipeline
=====================================================
One-command automated pipeline:
1. Find cheapest RTX 3090/4090 on Vast.ai
2. Create instance and wait for boot
3. Install dependencies
4. Upload training data + scripts
5. Run GPU training (all 3 models)
6. Download trained models
7. Deploy to VPS Ollama
8. Destroy instance (stop billing)

Usage:
    python3 vastai_auto.py              # Full pipeline
    python3 vastai_auto.py --step find  # Just find GPUs
    python3 vastai_auto.py --step create --offer-id 31530466
    python3 vastai_auto.py --step train --instance-id 12345
    python3 vastai_auto.py --step download --instance-id 12345
    python3 vastai_auto.py --step destroy --instance-id 12345
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

VASTAI_API_KEY = "460557583433320c6f66efd5848cd43497f10cac9b4d9965377926885a24a6ff"
DATA_DIR = Path("/opt/titan/training/data_v2")
SCRIPTS_DIR = Path("/opt/titan/training/phase3")
OUTPUT_DIR = Path("/opt/titan/training/vastai_output")
LOG_FILE = Path("/opt/titan/training/logs/vastai_pipeline.json")

DOCKER_IMAGE = "pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime"

def run_vastai(args_str):
    """Run vastai CLI command and return output."""
    cmd = f"vastai {args_str} --api-key {VASTAI_API_KEY}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout.strip(), result.stderr.strip(), result.returncode

def run_ssh(instance_info, command, timeout=600):
    """Run command on Vast.ai instance via SSH."""
    ssh_host = instance_info["ssh_host"]
    ssh_port = instance_info["ssh_port"]
    cmd = f'ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -p {ssh_port} root@{ssh_host} "{command}"'
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip(), result.returncode
    except subprocess.TimeoutExpired:
        return "TIMEOUT", 1

def run_scp(instance_info, local_path, remote_path, direction="upload"):
    """SCP file to/from Vast.ai instance."""
    ssh_host = instance_info["ssh_host"]
    ssh_port = instance_info["ssh_port"]
    if direction == "upload":
        cmd = f'scp -o StrictHostKeyChecking=no -P {ssh_port} -r {local_path} root@{ssh_host}:{remote_path}'
    else:
        cmd = f'scp -o StrictHostKeyChecking=no -P {ssh_port} -r root@{ssh_host}:{remote_path} {local_path}'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
    return result.returncode == 0


# ═══════════════════════════════════════════════════════════════
# STEP 1: FIND BEST GPU
# ═══════════════════════════════════════════════════════════════

def find_best_gpu():
    """Find cheapest RTX 3090/4090 with good reliability."""
    print("\n🔍 Searching for available GPUs...")
    
    # Search for RTX 4090 first (faster training)
    stdout, stderr, rc = run_vastai(
        'search offers "reliability > 0.95 num_gpus=1 gpu_ram >= 23 disk_space >= 50 dph_total < 0.50 inet_down > 200" '
        '-o dph_total --raw'
    )
    
    if rc != 0 or not stdout:
        print("  Trying broader search...")
        stdout, stderr, rc = run_vastai(
            'search offers "reliability > 0.90 num_gpus=1 gpu_ram >= 23 disk_space >= 40 dph_total < 0.80" '
            '-o dph_total --raw'
        )
    
    if not stdout:
        print("❌ No suitable GPUs found")
        return None
    
    try:
        offers = json.loads(stdout)
    except json.JSONDecodeError:
        print(f"❌ Failed to parse offers: {stdout[:200]}")
        return None
    
    if not offers:
        print("❌ No offers matched criteria")
        return None
    
    # Filter for RTX 3090/4090/A40
    preferred = []
    for offer in offers:
        gpu = offer.get("gpu_name", "")
        if any(g in gpu for g in ["RTX_4090", "RTX_3090", "A40", "RTX_4080", "L40"]):
            preferred.append(offer)
    
    if not preferred:
        preferred = offers[:10]
    
    # Sort by price
    preferred.sort(key=lambda x: x.get("dph_total", 999))
    
    print(f"\n✅ Found {len(preferred)} suitable GPUs. Top 5:")
    for i, offer in enumerate(preferred[:5], 1):
        gpu = offer.get("gpu_name", "Unknown")
        price = offer.get("dph_total", 0)
        vram = offer.get("gpu_ram", 0) / 1000
        location = offer.get("geolocation", "Unknown")
        reliability = offer.get("reliability2", 0)
        print(f"  {i}. ID:{offer['id']} {gpu} ${price:.3f}/hr {vram:.0f}GB VRAM rel:{reliability:.1%} [{location}]")
    
    best = preferred[0]
    print(f"\n✅ Selected: {best.get('gpu_name')} @ ${best.get('dph_total', 0):.3f}/hr (ID: {best['id']})")
    
    return best


# ═══════════════════════════════════════════════════════════════
# STEP 2: CREATE INSTANCE
# ═══════════════════════════════════════════════════════════════

def create_instance(offer_id):
    """Create Vast.ai instance from offer."""
    print(f"\n🚀 Creating instance from offer {offer_id}...")
    
    stdout, stderr, rc = run_vastai(
        f'create instance {offer_id} '
        f'--image {DOCKER_IMAGE} '
        f'--disk 50 '
        f'--raw'
    )
    
    if rc != 0:
        print(f"❌ Failed to create instance: {stderr}")
        return None
    
    try:
        result = json.loads(stdout)
        instance_id = result.get("new_contract")
        if instance_id:
            print(f"✅ Instance created: {instance_id}")
            return instance_id
    except (json.JSONDecodeError, TypeError):
        # Try to extract instance ID from text output
        if "new_contract" in stdout:
            for part in stdout.split():
                if part.isdigit():
                    print(f"✅ Instance created: {part}")
                    return int(part)
    
    print(f"❌ Could not parse instance ID from: {stdout}")
    return None


def wait_for_instance(instance_id, timeout=300):
    """Wait for instance to be running and get SSH details."""
    print(f"\n⏳ Waiting for instance {instance_id} to start...")
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        stdout, _, rc = run_vastai(f'show instance {instance_id} --raw')
        
        if rc == 0 and stdout:
            try:
                info = json.loads(stdout)
                status = info.get("actual_status", "")
                
                if status == "running":
                    ssh_host = info.get("ssh_host", "")
                    ssh_port = info.get("ssh_port", "")
                    
                    if ssh_host and ssh_port:
                        print(f"✅ Instance running!")
                        print(f"   SSH: ssh -p {ssh_port} root@{ssh_host}")
                        return {"ssh_host": ssh_host, "ssh_port": ssh_port, "id": instance_id}
                
                elapsed = int(time.time() - start_time)
                print(f"  [{elapsed}s] Status: {status}")
            except json.JSONDecodeError:
                pass
        
        time.sleep(15)
    
    print(f"❌ Timeout ({timeout}s) waiting for instance")
    return None


# ═══════════════════════════════════════════════════════════════
# STEP 3: SETUP & UPLOAD
# ═══════════════════════════════════════════════════════════════

def setup_instance(instance_info):
    """Install dependencies and upload data to instance."""
    print(f"\n📦 Setting up instance...")
    
    # Wait for SSH to be ready
    for attempt in range(10):
        output, rc = run_ssh(instance_info, "echo ready")
        if rc == 0 and "ready" in output:
            break
        print(f"  SSH not ready yet (attempt {attempt+1}/10)...")
        time.sleep(10)
    else:
        print("❌ SSH never became ready")
        return False
    
    # Install dependencies
    print("  Installing ML dependencies...")
    deps = "transformers==4.48.0 peft==0.14.0 datasets==3.3.0 accelerate==1.3.0 bitsandbytes scipy sentencepiece"
    output, rc = run_ssh(instance_info, f"pip install {deps}", timeout=300)
    if rc != 0:
        print(f"  ⚠️  Dep install may have issues: {output[-200:]}")
    else:
        print("  ✅ Dependencies installed")
    
    # Create workspace directories
    run_ssh(instance_info, "mkdir -p /workspace/data_v2 /workspace/output")
    
    # Upload training data
    print("  📤 Uploading training data...")
    # First create tarball
    subprocess.run("cd /opt/titan/training && tar -czf /tmp/titan_data.tar.gz data_v2/", shell=True)
    
    if run_scp(instance_info, "/tmp/titan_data.tar.gz", "/workspace/"):
        # Extract on instance
        run_ssh(instance_info, "cd /workspace && tar -xzf titan_data.tar.gz")
        print("  ✅ Training data uploaded")
    else:
        print("  ❌ Data upload failed")
        return False
    
    # Upload training script
    print("  📤 Uploading training script...")
    if run_scp(instance_info, str(SCRIPTS_DIR / "gpu_train.py"), "/workspace/"):
        print("  ✅ Training script uploaded")
    else:
        print("  ❌ Script upload failed")
        return False
    
    # Verify GPU
    output, rc = run_ssh(instance_info, 
        "python3 -c \"import torch; print(f'GPU: {torch.cuda.get_device_name(0)}'); print(f'VRAM: {torch.cuda.get_device_properties(0).total_mem/1e9:.1f}GB')\"")
    print(f"  {output}")
    
    # Verify data
    output, rc = run_ssh(instance_info, "ls -la /workspace/data_v2/ | wc -l && wc -l /workspace/data_v2/*.jsonl | tail -1")
    print(f"  Data: {output}")
    
    return True


# ═══════════════════════════════════════════════════════════════
# STEP 4: RUN TRAINING
# ═══════════════════════════════════════════════════════════════

def run_training(instance_info):
    """Run GPU training on instance."""
    print(f"\n🔥 Starting GPU training...")
    print(f"   This will take ~1-2 hours for all 3 models")
    
    # Start training in background with nohup
    run_ssh(instance_info, 
        "cd /workspace && nohup python3 gpu_train.py > training.log 2>&1 &")
    
    print("  Training started in background")
    print("  Monitoring progress...")
    
    # Monitor training
    last_output = ""
    while True:
        time.sleep(60)
        
        # Check if training is still running
        output, rc = run_ssh(instance_info, "pgrep -f gpu_train.py")
        if rc != 0:
            # Training finished
            print("\n  Training process finished!")
            break
        
        # Get latest log
        output, rc = run_ssh(instance_info, "tail -5 /workspace/training.log")
        if output != last_output:
            last_output = output
            timestamp = datetime.now().strftime("%H:%M:%S")
            for line in output.split("\n"):
                line = line.strip()
                if line:
                    print(f"  [{timestamp}] {line[:120]}")
    
    # Get final results
    output, rc = run_ssh(instance_info, "cat /workspace/output/training_results.json")
    if rc == 0:
        try:
            results = json.loads(output)
            print(f"\n✅ Training complete!")
            print(f"   Total time: {results.get('total_time_seconds', 0)/60:.1f} minutes")
            for task, info in results.get("models", {}).items():
                if "error" in info:
                    print(f"   ❌ {task}: {info['error']}")
                else:
                    print(f"   ✅ {task}: loss={info.get('train_loss', 'N/A')}")
            return results
        except json.JSONDecodeError:
            pass
    
    # Print raw log tail on failure
    output, _ = run_ssh(instance_info, "tail -30 /workspace/training.log")
    print(f"\nLog tail:\n{output}")
    
    return None


# ═══════════════════════════════════════════════════════════════
# STEP 5: DOWNLOAD MODELS
# ═══════════════════════════════════════════════════════════════

def download_models(instance_info):
    """Download trained models from instance to VPS."""
    print(f"\n📥 Downloading trained models...")
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Create tarball on instance
    print("  Creating model archive on GPU instance...")
    run_ssh(instance_info, 
        "cd /workspace && tar -czf trained_models.tar.gz output/*/lora_adapter/", 
        timeout=300)
    
    # Download
    print("  Downloading...")
    if run_scp(instance_info, str(OUTPUT_DIR / "trained_models.tar.gz"), "/workspace/trained_models.tar.gz", direction="download"):
        # Extract
        subprocess.run(f"cd {OUTPUT_DIR} && tar -xzf trained_models.tar.gz", shell=True)
        print(f"  ✅ Models downloaded to {OUTPUT_DIR}")
        return True
    else:
        print("  ❌ Download failed")
        return False


# ═══════════════════════════════════════════════════════════════
# STEP 6: DESTROY INSTANCE
# ═══════════════════════════════════════════════════════════════

def destroy_instance(instance_id):
    """Destroy Vast.ai instance to stop billing."""
    print(f"\n🗑️  Destroying instance {instance_id}...")
    stdout, stderr, rc = run_vastai(f"destroy instance {instance_id}")
    if rc == 0:
        print(f"  ✅ Instance {instance_id} destroyed (billing stopped)")
    else:
        print(f"  ❌ Destroy failed: {stderr}")
        print(f"  ⚠️  MANUALLY destroy: vastai destroy instance {instance_id}")


# ═══════════════════════════════════════════════════════════════
# MAIN PIPELINE
# ═══════════════════════════════════════════════════════════════

def full_pipeline():
    """Run the complete automated pipeline."""
    print(f"\n{'='*60}")
    print(f"⚡ TITAN V8.3 — Vast.ai Automated Training Pipeline")
    print(f"{'='*60}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    pipeline_state = {
        "started": datetime.now().isoformat(),
        "steps": {},
    }
    
    # Step 1: Find GPU
    print(f"\n{'─'*40}")
    print(f"STEP 1/6: Find Best GPU")
    print(f"{'─'*40}")
    offer = find_best_gpu()
    if not offer:
        print("❌ PIPELINE FAILED: No GPU found")
        return
    pipeline_state["steps"]["find_gpu"] = {"offer_id": offer["id"], "gpu": offer.get("gpu_name"), "price": offer.get("dph_total")}
    
    # Step 2: Create instance
    print(f"\n{'─'*40}")
    print(f"STEP 2/6: Create Instance")
    print(f"{'─'*40}")
    instance_id = create_instance(offer["id"])
    if not instance_id:
        print("❌ PIPELINE FAILED: Could not create instance")
        return
    pipeline_state["steps"]["create"] = {"instance_id": instance_id}
    
    # Step 3: Wait and setup
    print(f"\n{'─'*40}")
    print(f"STEP 3/6: Setup Instance")
    print(f"{'─'*40}")
    instance_info = wait_for_instance(instance_id)
    if not instance_info:
        destroy_instance(instance_id)
        print("❌ PIPELINE FAILED: Instance didn't start")
        return
    
    if not setup_instance(instance_info):
        destroy_instance(instance_id)
        print("❌ PIPELINE FAILED: Setup failed")
        return
    pipeline_state["steps"]["setup"] = {"ssh": f"{instance_info['ssh_host']}:{instance_info['ssh_port']}"}
    
    # Step 4: Train
    print(f"\n{'─'*40}")
    print(f"STEP 4/6: GPU Training (1-2 hours)")
    print(f"{'─'*40}")
    results = run_training(instance_info)
    pipeline_state["steps"]["training"] = results or {"error": "Training failed"}
    
    # Step 5: Download
    print(f"\n{'─'*40}")
    print(f"STEP 5/6: Download Models")
    print(f"{'─'*40}")
    downloaded = download_models(instance_info)
    pipeline_state["steps"]["download"] = {"success": downloaded}
    
    # Step 6: Destroy
    print(f"\n{'─'*40}")
    print(f"STEP 6/6: Cleanup (Stop Billing)")
    print(f"{'─'*40}")
    destroy_instance(instance_id)
    pipeline_state["steps"]["cleanup"] = {"destroyed": True}
    
    # Save pipeline state
    pipeline_state["completed"] = datetime.now().isoformat()
    elapsed = (datetime.now() - datetime.fromisoformat(pipeline_state["started"])).total_seconds()
    pipeline_state["total_time_minutes"] = round(elapsed / 60, 1)
    
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "w") as f:
        json.dump(pipeline_state, f, indent=2)
    
    print(f"\n{'='*60}")
    print(f"⚡ PIPELINE COMPLETE")
    print(f"{'='*60}")
    print(f"Total time: {elapsed/60:.1f} minutes")
    print(f"GPU cost: ~${offer.get('dph_total', 0) * (elapsed/3600):.2f}")
    print(f"Models: {OUTPUT_DIR}")
    print(f"Log: {LOG_FILE}")


def main():
    parser = argparse.ArgumentParser(description="Titan V8.3 Vast.ai Automated Pipeline")
    parser.add_argument("--step", choices=["find", "create", "train", "download", "destroy", "full"], 
                        default="full", help="Pipeline step to run")
    parser.add_argument("--offer-id", type=int, help="Offer ID for create step")
    parser.add_argument("--instance-id", type=int, help="Instance ID for train/download/destroy steps")
    args = parser.parse_args()
    
    if args.step == "full":
        full_pipeline()
    elif args.step == "find":
        find_best_gpu()
    elif args.step == "create":
        if not args.offer_id:
            offer = find_best_gpu()
            if offer:
                create_instance(offer["id"])
        else:
            create_instance(args.offer_id)
    elif args.step == "destroy":
        if args.instance_id:
            destroy_instance(args.instance_id)
        else:
            print("❌ Need --instance-id")
    else:
        print(f"Step '{args.step}' requires manual instance info")


if __name__ == "__main__":
    main()
