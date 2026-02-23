#!/bin/bash
# Vast.ai GPU Training Deployment Script
# Finds cheapest GPU and provides manual deployment instructions

VASTAI_API_KEY="460557583433320c6f66efd5848cd43497f10cac9b4d9965377926885a24a6ff"

echo "=========================================="
echo "TITAN V8.3 — Vast.ai GPU Training"
echo "=========================================="
echo ""

# Install vastai CLI if not present
if ! command -v vastai &> /dev/null; then
    echo "📦 Installing Vast.ai CLI..."
    pip3 install --break-system-packages vastai 2>&1 | tail -3
fi

# Set API key
vastai set api-key $VASTAI_API_KEY

echo ""
echo "🔍 Searching for cheapest RTX 3090/4090..."
echo ""

# Search for available GPUs
vastai search offers 'reliability > 0.95 num_gpus=1 gpu_ram >= 24 disk_space >= 50 gpu_name=RTX_3090 gpu_name=RTX_4090' \
    --order 'dph_total' | head -20

echo ""
echo "=========================================="
echo "MANUAL DEPLOYMENT STEPS"
echo "=========================================="
echo ""
echo "1. Choose a GPU from the list above (note the ID)"
echo ""
echo "2. Create instance:"
echo "   vastai create instance <ID> --image pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime --disk 50"
echo ""
echo "3. Wait for instance to start:"
echo "   vastai show instances"
echo ""
echo "4. SSH into instance (get SSH command from 'vastai show instances')"
echo ""
echo "5. Install dependencies:"
echo "   pip install transformers==4.48.0 peft==0.14.0 datasets==3.3.0 accelerate==1.3.0 bitsandbytes"
echo ""
echo "6. Upload training data from VPS:"
echo "   scp -r /opt/titan/training/data root@<instance-ip>:/workspace/"
echo ""
echo "7. Upload training script:"
echo "   scp /opt/titan/training/vastai_train.py root@<instance-ip>:/workspace/"
echo ""
echo "8. Run training:"
echo "   python3 /workspace/vastai_train.py"
echo ""
echo "9. Download models after training:"
echo "   scp -r root@<instance-ip>:/workspace/output /opt/titan/training/vastai_models/"
echo ""
echo "10. Destroy instance to stop billing:"
echo "    vastai destroy instance <instance-id>"
echo ""
echo "=========================================="
echo "Estimated cost: $0.30-0.60/hour × 2 hours = $0.60-1.20"
echo "=========================================="
