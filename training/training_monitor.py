#!/usr/bin/env python3
"""
TITAN V8.3 — Real-Time Training Monitor Web App
================================================
Flask web app that displays live training progress with countdown timer.
Updates every second with current status, remaining time, and metrics.

Accessible via: http://72.62.72.48:5000
"""

from flask import Flask, render_template, jsonify
from flask_cors import CORS
import os
import json
import time
import re
from datetime import datetime, timedelta
from pathlib import Path
import subprocess
import psutil

app = Flask(__name__)
CORS(app)  # Enable CORS for API access

# Training configuration
TRAINING_LOG = "/opt/titan/training/logs/analyst_train.log"
TRAINING_PID_FILE = "/opt/titan/training/logs/training.pid"
TRAINING_START_FILE = "/opt/titan/training/logs/training_start.json"

# Estimated times (in seconds) - Updated based on BF16 benchmarks
ESTIMATED_TIMES = {
    "analyst": 12 * 3600,      # 12 hours for 300 examples, 3 epochs (BF16 optimized)
    "strategist": 9 * 3600,    # 9 hours for 200 examples, 5 epochs
    "fast": 2.5 * 3600,        # 2.5 hours for 100 examples, 3 epochs
}

def get_training_status():
    """Get current training status from log files and process."""
    status = {
        "running": False,
        "task": "analyst",
        "start_time": None,
        "elapsed_seconds": 0,
        "elapsed_human": "0:00:00",
        "estimated_total_seconds": ESTIMATED_TIMES["analyst"],
        "estimated_total_human": "14:00:00",
        "remaining_seconds": ESTIMATED_TIMES["analyst"],
        "remaining_human": "14:00:00",
        "progress_percent": 0,
        "current_epoch": 0,
        "total_epochs": 3,
        "current_step": 0,
        "total_steps": 0,
        "loss": 0.0,
        "examples_processed": 0,
        "total_examples": 300,
        "speed": "0 examples/s",
        "last_update": datetime.now().isoformat(),
        "log_tail": [],
    }
    
    # Check if training process is running (improved with psutil)
    if os.path.exists(TRAINING_PID_FILE):
        try:
            with open(TRAINING_PID_FILE) as f:
                pid = int(f.read().strip())
            # Check if PID exists and is actually python training process
            if psutil.pid_exists(pid):
                proc = psutil.Process(pid)
                cmdline = ' '.join(proc.cmdline())
                status["running"] = 'lora_finetune.py' in cmdline
            else:
                status["running"] = False
        except Exception as e:
            status["running"] = False
    
    # Load start time
    if os.path.exists(TRAINING_START_FILE):
        try:
            with open(TRAINING_START_FILE) as f:
                start_data = json.load(f)
                status["task"] = start_data.get("task", "analyst")
                status["start_time"] = start_data.get("start_time")
                status["total_examples"] = start_data.get("total_examples", 300)
                status["total_epochs"] = start_data.get("epochs", 3)
                status["estimated_total_seconds"] = start_data.get("estimated_seconds", ESTIMATED_TIMES["analyst"])
        except Exception:
            pass
    
    # Calculate elapsed time
    if status["start_time"]:
        start_dt = datetime.fromisoformat(status["start_time"])
        elapsed = datetime.now() - start_dt
        status["elapsed_seconds"] = int(elapsed.total_seconds())
        status["elapsed_human"] = str(timedelta(seconds=status["elapsed_seconds"]))
    
    # Parse log file for progress
    if os.path.exists(TRAINING_LOG):
        try:
            with open(TRAINING_LOG, 'r') as f:
                lines = f.readlines()
                
            # Get last 20 lines for display
            status["log_tail"] = [l.strip() for l in lines[-20:] if l.strip()]
            
            # Parse progress from log
            for line in reversed(lines[-100:]):  # Check last 100 lines
                # Look for epoch/step info
                # Example: "Epoch 1/3 | Step 25/112 | Loss: 2.345"
                epoch_match = re.search(r'Epoch\s+(\d+)/(\d+)', line)
                if epoch_match:
                    status["current_epoch"] = int(epoch_match.group(1))
                    status["total_epochs"] = int(epoch_match.group(2))
                
                step_match = re.search(r'Step\s+(\d+)/(\d+)', line)
                if step_match:
                    status["current_step"] = int(step_match.group(1))
                    status["total_steps"] = int(step_match.group(2))
                
                loss_match = re.search(r'Loss:\s+([\d.]+)', line)
                if loss_match:
                    status["loss"] = float(loss_match.group(1))
                
                # Calculate progress
                if status["total_steps"] > 0:
                    total_progress = (status["current_epoch"] - 1) * status["total_steps"] + status["current_step"]
                    total_max = status["total_epochs"] * status["total_steps"]
                    status["progress_percent"] = int((total_progress / total_max) * 100) if total_max > 0 else 0
                    break
        except Exception as e:
            status["log_tail"].append(f"Error reading log: {e}")
    
    # Calculate remaining time
    if status["progress_percent"] > 0 and status["elapsed_seconds"] > 0:
        # Estimate based on actual progress
        estimated_total = (status["elapsed_seconds"] / status["progress_percent"]) * 100
        status["estimated_total_seconds"] = int(estimated_total)
        status["remaining_seconds"] = int(estimated_total - status["elapsed_seconds"])
    else:
        # Use initial estimate
        status["remaining_seconds"] = status["estimated_total_seconds"] - status["elapsed_seconds"]
    
    if status["remaining_seconds"] < 0:
        status["remaining_seconds"] = 0
    
    status["remaining_human"] = str(timedelta(seconds=status["remaining_seconds"]))
    status["estimated_total_human"] = str(timedelta(seconds=status["estimated_total_seconds"]))
    
    # Calculate speed
    if status["elapsed_seconds"] > 0 and status["current_step"] > 0:
        examples_per_sec = status["current_step"] / status["elapsed_seconds"]
        status["speed"] = f"{examples_per_sec:.2f} steps/s"
    
    return status


@app.route('/')
def index():
    """Main countdown display page."""
    return render_template('countdown.html')


@app.route('/api/status')
def api_status():
    """API endpoint for real-time status updates."""
    return jsonify(get_training_status())


@app.route('/api/start/<task>')
def api_start_training(task):
    """Start training for a specific task."""
    if task not in ["analyst", "strategist", "fast"]:
        return jsonify({"error": "Invalid task"}), 400
    
    # Save start time
    start_data = {
        "task": task,
        "start_time": datetime.now().isoformat(),
        "total_examples": {"analyst": 300, "strategist": 200, "fast": 100}[task],
        "epochs": {"analyst": 3, "strategist": 5, "fast": 3}[task],
        "estimated_seconds": ESTIMATED_TIMES[task],
    }
    
    os.makedirs("/opt/titan/training/logs", exist_ok=True)
    with open(TRAINING_START_FILE, 'w') as f:
        json.dump(start_data, f, indent=2)
    
    # Launch training in background
    cmd = f"cd /opt/titan/training/phase3 && nohup python3 lora_finetune.py --task {task} --epochs {start_data['epochs']} --max-examples {start_data['total_examples']} > {TRAINING_LOG} 2>&1 & echo $! > {TRAINING_PID_FILE}"
    
    try:
        subprocess.run(cmd, shell=True, check=True)
        return jsonify({"success": True, "task": task, "message": "Training started"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    # Run on all interfaces (0.0.0.0) to be accessible via public IP
    app.run(host='0.0.0.0', port=5000, debug=False)
