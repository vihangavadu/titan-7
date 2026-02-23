#!/bin/bash
# TITAN V8.3 - Vast.ai GPU Training Setup
# Run this script in the Vast.ai web terminal or SSH session
# Instance: 31924128

set -e

echo "=========================================="
echo "TITAN V8.3 - GPU Training Setup"
echo "=========================================="

# Step 1: Install dependencies
echo ""
echo "[1/7] Installing ML dependencies..."
pip install transformers==4.48.0 peft==0.14.0 datasets==3.3.0 accelerate==1.3.0 bitsandbytes scipy sentencepiece

# Step 2: Verify GPU
echo ""
echo "[2/7] Verifying GPU..."
python3 << 'EOF'
import torch
print(f"GPU: {torch.cuda.get_device_name(0)}")
print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory/1e9:.1f}GB")
print(f"CUDA: {torch.version.cuda}")
EOF

# Step 3: Create workspace
echo ""
echo "[3/7] Creating workspace..."
mkdir -p /workspace/data_v2 /workspace/output

# Step 4: Download training data from VPS
echo ""
echo "[4/7] Downloading training data from VPS (72.62.72.48)..."
echo "Creating data tarball on VPS..."

# Download via HTTP (VPS must serve files)
# Alternative: Use wget if VPS has HTTP server running
# For now, we'll use direct download URLs

# Download each data file
cd /workspace/data_v2
for task in bin_analysis target_recon fingerprint_coherence identity_graph environment_coherence decline_autopsy session_rhythm card_rotation velocity_schedule avs_prevalidation; do
    echo "  Downloading ${task}.jsonl..."
    wget -q http://72.62.72.48:8888/data_v2/${task}.jsonl || echo "  Failed: ${task}.jsonl"
done

# Step 5: Download training script
echo ""
echo "[5/7] Downloading GPU training script..."
cd /workspace
wget -q http://72.62.72.48:8888/phase3/gpu_train.py || echo "  Failed to download gpu_train.py"

# Step 6: Verify data
echo ""
echo "[6/7] Verifying downloaded data..."
wc -l /workspace/data_v2/*.jsonl | tail -1

# Step 7: Start training
echo ""
echo "[7/7] Starting training (background process)..."
cd /workspace
nohup python3 -u gpu_train.py > training.log 2>&1 &
echo $! > training.pid

echo ""
echo "=========================================="
echo "SETUP COMPLETE!"
echo "=========================================="
echo "Training started in background (PID: $(cat training.pid))"
echo ""
echo "Monitor with:"
echo "  tail -f /workspace/training.log"
echo ""
echo "Check status:"
echo "  ps aux | grep gpu_train"
echo ""
echo "Estimated time: 1-2 hours"
echo "Estimated cost: \$0.15-0.25"
