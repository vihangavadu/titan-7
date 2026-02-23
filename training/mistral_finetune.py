#!/usr/bin/env python3
"""
TITAN V8.3 — Mistral AI Fine-Tuning
====================================
Fine-tune titan-analyst, titan-strategist, and titan-fast models
using Mistral AI API for 10x faster training (2-4 hours vs 40 hours).

Cost: $31 one-time + $6/month storage for all 3 models
"""

import os
import json
import time
from pathlib import Path
from datetime import datetime
import requests

# Mistral AI API Configuration
MISTRAL_API_KEY = "MF3InLqh2KbqALZ6fNM045XrTzFqo9ps"
MISTRAL_API_BASE = "https://api.mistral.ai/v1"

# Training data paths
TRAINING_DATA_DIR = Path("/opt/titan/training/data")
OUTPUT_DIR = Path("/opt/titan/training/mistral_models")
LOGS_DIR = Path("/opt/titan/training/logs")

# Task configurations
TASKS = {
    "analyst": {
        "base_model": "open-mistral-7b",
        "data_files": [
            "bin_analysis.jsonl",
            "target_recon.jsonl",
            "fingerprint_coherence.jsonl",
            "identity_graph.jsonl",
            "environment_coherence.jsonl",
            "avs_prevalidation.jsonl",
        ],
        "max_examples": 300,
        "epochs": 3,
    },
    "strategist": {
        "base_model": "open-mistral-7b",
        "data_files": [
            "decline_autopsy.jsonl",
            "card_rotation.jsonl",
            "velocity_schedule.jsonl",
            "session_rhythm.jsonl",
        ],
        "max_examples": 200,
        "epochs": 5,
    },
    "fast": {
        "base_model": "open-mistral-7b",
        "data_files": [
            "bin_analysis.jsonl",
            "target_recon.jsonl",
        ],
        "max_examples": 100,
        "epochs": 3,
    },
}


def convert_to_mistral_format(input_file, output_file, max_examples=None):
    """Convert training data to Mistral AI format."""
    examples = []
    
    with open(input_file, 'r') as f:
        for i, line in enumerate(f):
            if max_examples and i >= max_examples:
                break
            try:
                data = json.loads(line)
                # Mistral format: {"messages": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}
                example = {
                    "messages": [
                        {"role": "user", "content": data["prompt"]},
                        {"role": "assistant", "content": data["response"]}
                    ]
                }
                examples.append(example)
            except Exception as e:
                print(f"  Warning: Skipped line {i+1}: {e}")
    
    with open(output_file, 'w') as f:
        for example in examples:
            f.write(json.dumps(example) + '\n')
    
    return len(examples)


def prepare_training_data(task_name, task_config):
    """Prepare and merge training data for a task."""
    print(f"\n{'='*60}")
    print(f"Preparing data for {task_name}")
    print(f"{'='*60}")
    
    output_file = OUTPUT_DIR / f"{task_name}_training.jsonl"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    all_examples = []
    total_count = 0
    
    for data_file in task_config["data_files"]:
        input_path = TRAINING_DATA_DIR / data_file
        if not input_path.exists():
            print(f"  ⚠️  Missing: {data_file}")
            continue
        
        temp_file = OUTPUT_DIR / f"temp_{data_file}"
        count = convert_to_mistral_format(input_path, temp_file)
        
        with open(temp_file, 'r') as f:
            all_examples.extend([json.loads(line) for line in f])
        
        temp_file.unlink()
        total_count += count
        print(f"  ✓ {data_file}: {count} examples")
    
    # Limit to max_examples if specified
    if task_config.get("max_examples") and len(all_examples) > task_config["max_examples"]:
        all_examples = all_examples[:task_config["max_examples"]]
        print(f"  ℹ️  Limited to {task_config['max_examples']} examples")
    
    # Write merged data
    with open(output_file, 'w') as f:
        for example in all_examples:
            f.write(json.dumps(example) + '\n')
    
    print(f"  ✓ Total: {len(all_examples)} examples")
    print(f"  ✓ Saved to: {output_file}")
    
    return output_file, len(all_examples)


def upload_training_file(file_path):
    """Upload training file to Mistral AI."""
    print(f"\n📤 Uploading {file_path.name}...")
    
    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}"
    }
    
    with open(file_path, 'rb') as f:
        files = {'file': (file_path.name, f, 'application/jsonl')}
        data = {'purpose': 'fine-tune'}
        
        response = requests.post(
            f"{MISTRAL_API_BASE}/files",
            headers=headers,
            files=files,
            data=data
        )
    
    if response.status_code == 200:
        file_data = response.json()
        file_id = file_data['id']
        print(f"  ✓ Uploaded: {file_id}")
        return file_id
    else:
        print(f"  ✗ Upload failed: {response.status_code}")
        print(f"  Response: {response.text}")
        return None


def create_finetune_job(task_name, file_id, base_model, epochs):
    """Create a fine-tuning job on Mistral AI."""
    print(f"\n🚀 Creating fine-tuning job for {task_name}...")
    
    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Mistral API format: training_files must be array of objects with file_id and weight
    data = {
        "model": base_model,
        "training_files": [{"file_id": file_id, "weight": 1}],
        "hyperparameters": {
            "training_steps": epochs * 50,  # Reasonable for fine-tuning
            "learning_rate": 0.0001
        },
        "auto_start": True  # Start immediately after validation
    }
    
    response = requests.post(
        f"{MISTRAL_API_BASE}/fine_tuning/jobs",
        headers=headers,
        json=data
    )
    
    if response.status_code in [200, 201]:
        job_data = response.json()
        job_id = job_data['id']
        print(f"  ✓ Job created: {job_id}")
        print(f"  ✓ Status: {job_data.get('status', 'unknown')}")
        return job_id
    else:
        print(f"  ✗ Job creation failed: {response.status_code}")
        print(f"  Response: {response.text}")
        return None


def check_job_status(job_id):
    """Check the status of a fine-tuning job."""
    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}"
    }
    
    response = requests.get(
        f"{MISTRAL_API_BASE}/fine_tuning/jobs/{job_id}",
        headers=headers
    )
    
    if response.status_code == 200:
        return response.json()
    else:
        return None


def monitor_jobs(job_ids):
    """Monitor all fine-tuning jobs until completion."""
    print(f"\n{'='*60}")
    print(f"Monitoring {len(job_ids)} fine-tuning jobs")
    print(f"{'='*60}")
    
    completed = {}
    
    while len(completed) < len(job_ids):
        for task_name, job_id in job_ids.items():
            if task_name in completed:
                continue
            
            status = check_job_status(job_id)
            if status:
                state = status.get('status', 'unknown')
                
                if state == 'succeeded':
                    model_id = status.get('fine_tuned_model')
                    completed[task_name] = model_id
                    print(f"  ✓ {task_name}: COMPLETED → {model_id}")
                elif state == 'failed':
                    error = status.get('error', 'Unknown error')
                    completed[task_name] = None
                    print(f"  ✗ {task_name}: FAILED → {error}")
                else:
                    print(f"  ⏳ {task_name}: {state}")
        
        if len(completed) < len(job_ids):
            time.sleep(60)  # Check every minute
    
    return completed


def main():
    """Main fine-tuning workflow."""
    print(f"\n{'='*60}")
    print(f"TITAN V8.3 — Mistral AI Fine-Tuning")
    print(f"{'='*60}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API Key: {MISTRAL_API_KEY[:8]}...{MISTRAL_API_KEY[-4:]}")
    print(f"Tasks: {', '.join(TASKS.keys())}")
    
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOGS_DIR / f"mistral_finetune_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    results = {
        "started": datetime.now().isoformat(),
        "tasks": {},
        "jobs": {},
        "models": {}
    }
    
    # Step 1: Prepare training data
    print(f"\n{'='*60}")
    print(f"STEP 1: Preparing Training Data")
    print(f"{'='*60}")
    
    training_files = {}
    for task_name, task_config in TASKS.items():
        file_path, count = prepare_training_data(task_name, task_config)
        training_files[task_name] = {
            "path": file_path,
            "count": count,
            "config": task_config
        }
        results["tasks"][task_name] = {
            "examples": count,
            "epochs": task_config["epochs"],
            "base_model": task_config["base_model"]
        }
    
    # Step 2: Upload files
    print(f"\n{'='*60}")
    print(f"STEP 2: Uploading Training Files")
    print(f"{'='*60}")
    
    file_ids = {}
    for task_name, file_info in training_files.items():
        file_id = upload_training_file(file_info["path"])
        if file_id:
            file_ids[task_name] = file_id
        else:
            print(f"  ✗ Failed to upload {task_name}")
            return
    
    # Step 3: Create fine-tuning jobs
    print(f"\n{'='*60}")
    print(f"STEP 3: Creating Fine-Tuning Jobs")
    print(f"{'='*60}")
    
    job_ids = {}
    for task_name, file_id in file_ids.items():
        config = training_files[task_name]["config"]
        job_id = create_finetune_job(
            task_name,
            file_id,
            config["base_model"],
            config["epochs"]
        )
        if job_id:
            job_ids[task_name] = job_id
            results["jobs"][task_name] = job_id
        else:
            print(f"  ✗ Failed to create job for {task_name}")
    
    # Save job IDs
    with open(log_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✓ Job IDs saved to: {log_file}")
    
    # Step 4: Monitor jobs
    if job_ids:
        models = monitor_jobs(job_ids)
        results["models"] = models
        results["completed"] = datetime.now().isoformat()
        
        with open(log_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n{'='*60}")
        print(f"FINE-TUNING COMPLETE")
        print(f"{'='*60}")
        for task_name, model_id in models.items():
            if model_id:
                print(f"  ✓ {task_name}: {model_id}")
            else:
                print(f"  ✗ {task_name}: FAILED")
        
        print(f"\n✓ Results saved to: {log_file}")
    else:
        print(f"\n✗ No jobs created")


if __name__ == "__main__":
    main()
