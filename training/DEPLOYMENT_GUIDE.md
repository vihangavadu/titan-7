# TITAN V8.3 Training Monitor — Deployment Guide

## Overview

Real-time web-based countdown display for LoRA fine-tuning progress.

**Public URL**: `http://72.62.72.48:5000`

Updates every second with:
- ⏱️ Countdown timer (remaining time)
- 📊 Progress bar (% complete)
- 📈 Training metrics (epoch, step, loss, speed)
- 📋 Live log tail (last 20 lines)
- 💻 Server info (VPS specs, last update time)

---

## Files Created (Local - Ready to Deploy)

### 1. Training Monitor Web App
- **`training/training_monitor.py`** — Flask web server (port 5000)
- **`training/templates/countdown.html`** — Real-time countdown UI

### 2. Deployment Scripts
- **`training/start_monitor.sh`** — Launch web monitor
- **`training/start_training.sh`** — Start titan-analyst training

### 3. Analysis & Documentation
- **`docs/OPERATION_FAILURE_ANALYSIS.md`** — 12 critical failure vectors identified
- **`training/phase3/lora_finetune.py`** — AMD EPYC optimized (BF16, gradient checkpointing)

---

## Deployment Steps

### Step 1: Upload Scripts to VPS

```powershell
# Already uploaded:
# ✓ training_monitor.py
# ✓ templates/countdown.html

# Upload deployment scripts:
$plink = "c:\Users\Administrator\Downloads\titan-7\titan-7\titan-7\plink.exe"
$server = "root@72.62.72.48"
$pw = "Chilaw@123@llm"

# Upload start_monitor.sh
Get-Content -Raw "training\start_monitor.sh" | & $plink -ssh $server -pw $pw -batch "cat > /opt/titan/training/start_monitor.sh && chmod +x /opt/titan/training/start_monitor.sh"

# Upload start_training.sh
Get-Content -Raw "training\start_training.sh" | & $plink -ssh $server -pw $pw -batch "cat > /opt/titan/training/start_training.sh && chmod +x /opt/titan/training/start_training.sh"
```

### Step 2: Launch Training Monitor

```bash
# SSH to VPS
ssh root@72.62.72.48

# Start web monitor
bash /opt/titan/training/start_monitor.sh

# Expected output:
# Training Monitor started (PID: 12345)
# Access at: http://72.62.72.48:5000
# ✓ Monitor is running and accessible
# ✓ Public URL: http://72.62.72.48:5000
```

### Step 3: Start Training

```bash
# Start titan-analyst LoRA training
bash /opt/titan/training/start_training.sh

# Expected output:
# Training started (PID: 12346)
# Task: analyst
# Examples: 300
# Epochs: 3
# Estimated time: 14 hours
# Monitor at: http://72.62.72.48:5000
```

### Step 4: Access Countdown Display

Open in browser: **http://72.62.72.48:5000**

---

## What You'll See

### Header
- **Title**: TITAN V8.3 TRAINING MONITOR
- **Status Badge**: 🔥 TRAINING IN PROGRESS (pulsing green) or ⏸️ IDLE (gray)

### Countdown Display (Large)
```
TIME REMAINING
  12:34:56
```

### Info Cards (3 columns)
1. **Elapsed Time** — How long training has been running
2. **Estimated Total** — Total time based on current progress
3. **Current Task** — analyst / strategist / fast

### Progress Bar
- Visual progress bar (0-100%)
- Color gradient: cyan → green
- Glowing effect

### Training Metrics (4 boxes)
- **Epoch**: 2 / 3
- **Step**: 45 / 112
- **Training Loss**: 2.345
- **Speed**: 1.23 steps/s

### Live Log Tail
Last 20 lines from training log, auto-scrolling

### Server Info Footer
- VPS IP and port
- CPU specs (AMD EPYC 9354P)
- RAM (32GB)
- Compute type (BFloat16 AVX-512)
- Last update timestamp

---

## API Endpoints

### GET `/`
Main countdown display page (HTML)

### GET `/api/status`
JSON status endpoint (updates every 1 second)

**Response**:
```json
{
  "running": true,
  "task": "analyst",
  "start_time": "2026-02-23T13:45:00",
  "elapsed_seconds": 3600,
  "elapsed_human": "1:00:00",
  "estimated_total_seconds": 50400,
  "estimated_total_human": "14:00:00",
  "remaining_seconds": 46800,
  "remaining_human": "13:00:00",
  "progress_percent": 7,
  "current_epoch": 1,
  "total_epochs": 3,
  "current_step": 8,
  "total_steps": 112,
  "loss": 2.456,
  "speed": "1.15 steps/s",
  "log_tail": ["[line 1]", "[line 2]", "..."],
  "last_update": "2026-02-23T14:45:00"
}
```

### GET `/api/start/<task>`
Start training for a task (analyst/strategist/fast)

---

## Monitoring Commands

### Check if monitor is running
```bash
ps aux | grep training_monitor.py
curl http://localhost:5000/api/status
```

### Check if training is running
```bash
ps aux | grep lora_finetune.py
cat /opt/titan/training/logs/training.pid
```

### View live training log
```bash
tail -f /opt/titan/training/logs/analyst_train.log
```

### Check monitor log
```bash
tail -f /opt/titan/training/logs/monitor.log
```

### Stop monitor
```bash
pkill -f training_monitor.py
```

### Stop training
```bash
kill $(cat /opt/titan/training/logs/training.pid)
```

---

## Firewall Configuration

Port 5000 must be open for public access:

```bash
# Check if port is open
netstat -tulpn | grep :5000

# If using ufw:
ufw allow 5000/tcp

# If using iptables:
iptables -A INPUT -p tcp --dport 5000 -j ACCEPT
```

**Note**: Hostinger VPS typically has ports open by default. If you can't access the monitor, check VPS firewall settings in hPanel.

---

## Troubleshooting

### Monitor not accessible
```bash
# Check if Flask is running
ps aux | grep training_monitor.py

# Check logs
tail -50 /opt/titan/training/logs/monitor.log

# Restart monitor
bash /opt/titan/training/start_monitor.sh
```

### Training not starting
```bash
# Check Python environment
source /etc/profile.d/titan_ml.sh
python3 -c "import torch, transformers, peft; print('OK')"

# Check disk space
df -h /opt/titan

# Check RAM
free -m

# Manually start training
cd /opt/titan/training/phase3
python3 lora_finetune.py --task analyst --epochs 3 --max-examples 300
```

### Progress not updating
```bash
# Check if training process is alive
ps aux | grep lora_finetune.py

# Check log file is being written
ls -lh /opt/titan/training/logs/analyst_train.log
tail -20 /opt/titan/training/logs/analyst_train.log
```

---

## Training Timeline

### titan-analyst (Current)
- **Examples**: 300
- **Epochs**: 3
- **Estimated**: 14 hours
- **Start**: When you launch
- **Complete**: ~14 hours later

### titan-strategist (Next)
- **Examples**: 200
- **Epochs**: 5
- **Estimated**: 10 hours
- **Start**: After analyst completes
- **Complete**: +10 hours

### titan-fast (Final)
- **Examples**: 100
- **Epochs**: 3
- **Estimated**: 3 hours
- **Start**: After strategist completes
- **Complete**: +3 hours

**Total Pipeline**: ~27 hours (1 day 3 hours)

---

## Post-Training

After training completes:

1. **Check results**:
   ```bash
   ls -lh /opt/titan/training/models/titan-analyst-v83-lora/
   cat /opt/titan/training/logs/titan-analyst-v83-lora_*.json
   ```

2. **ONNX export** (automatic during training):
   ```bash
   ls -lh /opt/titan/training/onnx/titan-analyst-v83-lora/
   ```

3. **Sync all local changes to VPS**:
   - OPERATION_FAILURE_ANALYSIS.md
   - Any critical fixes implemented
   - Updated documentation

4. **Launch next training job**:
   ```bash
   # Edit start_training.sh to use "strategist"
   bash /opt/titan/training/start_training.sh
   ```

---

## Security Notes

⚠️ **Important**: The monitor is publicly accessible on port 5000 without authentication.

**Recommendations**:
- Monitor is read-only (no sensitive data exposed)
- Training logs don't contain credentials
- Consider adding basic auth if needed:
  ```python
  from flask_httpauth import HTTPBasicAuth
  auth = HTTPBasicAuth()
  # Add @auth.login_required to routes
  ```

---

## Summary

✅ **Created**:
- Real-time countdown web monitor
- Flask API with 1-second updates
- Beautiful gradient UI with live metrics
- Deployment scripts for easy launch

✅ **Ready to Deploy**:
- Upload scripts to VPS
- Launch monitor on port 5000
- Start training
- Access via http://72.62.72.48:5000

✅ **Features**:
- Live countdown timer
- Progress bar with percentage
- Training metrics (epoch, step, loss, speed)
- Log tail (last 20 lines)
- Auto-refresh every second
- Mobile-responsive design

**Next Step**: Upload deployment scripts and launch when ready!
