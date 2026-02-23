#!/bin/bash
# TITAN V8.3 - Complete Vast.ai GPU Training Setup
# Download this file and run it in the Vast.ai web terminal

set -e

echo "=========================================="
echo "TITAN V8.3 - GPU Training Pipeline"
echo "=========================================="
echo ""

# Step 1: Install ML dependencies
echo "[1/6] Installing ML dependencies..."
pip install -q transformers==4.48.0 peft==0.14.0 datasets==3.3.0 accelerate==1.3.0 bitsandbytes scipy sentencepiece
echo "  ✓ Dependencies installed"

# Step 2: Verify GPU
echo ""
echo "[2/6] Verifying GPU..."
python3 << 'PYEOF'
import torch
print(f"  GPU: {torch.cuda.get_device_name(0)}")
print(f"  VRAM: {torch.cuda.get_device_properties(0).total_memory/1e9:.1f}GB")
print(f"  CUDA: {torch.version.cuda}")
PYEOF

# Step 3: Create workspace
echo ""
echo "[3/6] Creating workspace..."
mkdir -p /workspace
cd /workspace
echo "  ✓ Workspace created: /workspace"

# Step 4: Download training package
echo ""
echo "[4/6] Downloading training package from VPS..."
wget -q --show-progress http://72.62.72.48:8888/titan_training_package.tar.gz
echo "  ✓ Downloaded: titan_training_package.tar.gz"

# Step 5: Extract
echo ""
echo "[5/6] Extracting training data and scripts..."
tar -xzf titan_training_package.tar.gz
echo "  ✓ Extracted"

# Verify data
echo ""
echo "Training data summary:"
wc -l data_v2/*.jsonl | tail -1

# Step 6: Start training
echo ""
echo "[6/6] Starting GPU training..."
nohup python3 -u phase3/gpu_train.py > training.log 2>&1 &
TRAIN_PID=$!
echo $TRAIN_PID > training.pid

echo ""
echo "=========================================="
echo "TRAINING STARTED!"
echo "=========================================="
echo "Process ID: $TRAIN_PID"
echo "Log file: /workspace/training.log"
echo ""
echo "Monitor progress:"
echo "  tail -f /workspace/training.log"
echo ""
echo "Check if running:"
echo "  ps aux | grep gpu_train"
echo ""
echo "Estimated time: 1-2 hours"
echo "Estimated cost: \$0.15-0.25"
echo ""
echo "Training will continue even if you disconnect."
echo "=========================================="

# Show initial log output
sleep 3
echo ""
echo "Initial training output:"
tail -20 /workspace/training.log
