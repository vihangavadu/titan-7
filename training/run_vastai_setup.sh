#!/bin/bash
# Vast.ai GPU Instance Setup & Training Launch
# Instance: 31924128, SSH: ssh2.vast.ai:14128

set -e

VAST_HOST="ssh2.vast.ai"
VAST_PORT="14128"
SSH_OPTS="-o StrictHostKeyChecking=no -o ConnectTimeout=15"

echo "=========================================="
echo "TITAN V8.3 — Vast.ai GPU Setup"
echo "=========================================="

# Generate SSH key if not exists
if [ ! -f /root/.ssh/id_rsa ]; then
    echo "Generating SSH key..."
    ssh-keygen -t rsa -N "" -f /root/.ssh/id_rsa
fi

# Wait for SSH to be ready
echo ""
echo "[1/6] Waiting for SSH..."
for i in $(seq 1 20); do
    if ssh $SSH_OPTS -p $VAST_PORT root@$VAST_HOST "echo ready" 2>/dev/null; then
        echo "SSH ready!"
        break
    fi
    echo "  Attempt $i/20..."
    sleep 10
done

# Install dependencies
echo ""
echo "[2/6] Installing ML dependencies..."
ssh $SSH_OPTS -p $VAST_PORT root@$VAST_HOST "pip install transformers==4.48.0 peft==0.14.0 datasets==3.3.0 accelerate==1.3.0 bitsandbytes scipy sentencepiece 2>&1 | tail -5"

# Create workspace
echo ""
echo "[3/6] Creating workspace..."
ssh $SSH_OPTS -p $VAST_PORT root@$VAST_HOST "mkdir -p /workspace/data_v2 /workspace/output"

# Upload training data
echo ""
echo "[4/6] Uploading training data (2000 examples)..."
cd /opt/titan/training
tar -czf /tmp/titan_data_v2.tar.gz data_v2/
scp $SSH_OPTS -P $VAST_PORT /tmp/titan_data_v2.tar.gz root@$VAST_HOST:/workspace/
ssh $SSH_OPTS -p $VAST_PORT root@$VAST_HOST "cd /workspace && tar -xzf titan_data_v2.tar.gz && echo 'Data extracted' && wc -l data_v2/*.jsonl | tail -1"

# Upload training script
echo ""
echo "[5/6] Uploading GPU training script..."
scp $SSH_OPTS -P $VAST_PORT /opt/titan/training/phase3/gpu_train.py root@$VAST_HOST:/workspace/

# Verify GPU
echo ""
echo "[6/6] Verifying GPU..."
ssh $SSH_OPTS -p $VAST_PORT root@$VAST_HOST "python3 -c 'import torch; print(f\"GPU: {torch.cuda.get_device_name(0)}\"); print(f\"VRAM: {torch.cuda.get_device_properties(0).total_mem/1e9:.1f}GB\"); print(f\"CUDA: {torch.version.cuda}\")'"

echo ""
echo "=========================================="
echo "SETUP COMPLETE! Starting training..."
echo "=========================================="

# Launch training in background
ssh $SSH_OPTS -p $VAST_PORT root@$VAST_HOST "cd /workspace && nohup python3 -u gpu_train.py > training.log 2>&1 &"
echo "Training launched in background on GPU!"
echo ""
echo "Monitor with:"
echo "  ssh $SSH_OPTS -p $VAST_PORT root@$VAST_HOST 'tail -f /workspace/training.log'"
echo ""
echo "Check if running:"
echo "  ssh $SSH_OPTS -p $VAST_PORT root@$VAST_HOST 'pgrep -a gpu_train'"
