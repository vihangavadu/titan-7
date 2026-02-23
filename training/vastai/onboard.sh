#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# TITAN V9.0 — Vast.ai Instance Onboard Script
# ═══════════════════════════════════════════════════════════════
# Runs on the Vast.ai GPU instance after creation.
# Sets up deps, generates training data, runs GPU LoRA fine-tuning.
#
# Usage (run inside the Vast.ai instance):
#   bash /workspace/training/vastai/onboard.sh
# ═══════════════════════════════════════════════════════════════

set -e

WORKSPACE="/workspace"
TRAINING="$WORKSPACE/training"
DATA_DIR="$TRAINING/data_v9"
LOG_DIR="$TRAINING/logs"

mkdir -p "$DATA_DIR" "$LOG_DIR"

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo " TITAN V9.0 — Vast.ai GPU Training Onboard"
echo "═══════════════════════════════════════════════════════════════"
echo " GPU: $(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null || echo 'unknown')"
echo " CUDA: $(nvcc --version 2>/dev/null | grep release | awk '{print $5}' | tr -d ',' || echo 'unknown')"
echo " PyTorch: $(python3 -c 'import torch; print(torch.__version__, "CUDA:", torch.cuda.is_available())' 2>/dev/null || echo 'not installed')"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# ═══════════════════════════════════════════════════════════════
# PHASE 1: Install dependencies
# ═══════════════════════════════════════════════════════════════
echo "[1/4] Installing dependencies..."
pip install -q transformers>=4.45.0 datasets>=3.0.0 peft>=0.13.0 accelerate>=1.0.0 sentencepiece safetensors 2>&1 | tail -5
echo "  Dependencies installed."

# Verify GPU
python3 -c "
import torch
assert torch.cuda.is_available(), 'CUDA not available!'
print(f'  GPU: {torch.cuda.get_device_name(0)}')
print(f'  VRAM: {torch.cuda.get_device_properties(0).total_mem/1e9:.1f} GB')
print(f'  BF16: {torch.cuda.is_bf16_supported()}')
print(f'  PyTorch: {torch.__version__}')
"

# ═══════════════════════════════════════════════════════════════
# PHASE 2: Generate training data (all 57 tasks)
# ═══════════════════════════════════════════════════════════════
echo ""
echo "[2/4] Generating training data (57 tasks × 300 examples)..."
cd "$TRAINING/phase2"
python3 generate_training_data_v9.py --count 300 --output "$DATA_DIR" --validate --combined 2>&1 | tee "$LOG_DIR/datagen.log"

TASK_FILES=$(ls "$DATA_DIR"/*.jsonl 2>/dev/null | grep -v combined | wc -l)
TOTAL_LINES=$(cat "$DATA_DIR"/*.jsonl 2>/dev/null | wc -l)
echo "  Generated: $TASK_FILES task files, $TOTAL_LINES total examples"

# ═══════════════════════════════════════════════════════════════
# PHASE 3: GPU LoRA Fine-Tuning (all 3 models)
# ═══════════════════════════════════════════════════════════════
echo ""
echo "[3/4] Starting GPU LoRA fine-tuning (3 models)..."
echo "  Estimated: ~2-4 hours per model on RTX 3090"
echo ""

cd "$TRAINING/vastai"
python3 gpu_lora_finetune.py --task all 2>&1 | tee "$LOG_DIR/gpu_training.log"

# ═══════════════════════════════════════════════════════════════
# PHASE 4: Package results
# ═══════════════════════════════════════════════════════════════
echo ""
echo "[4/4] Packaging results..."
cd "$TRAINING"
tar czf /workspace/titan_v9_lora_models.tar.gz models_v9/ logs/ 2>/dev/null || true

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo " TRAINING COMPLETE"
echo "═══════════════════════════════════════════════════════════════"
echo " LoRA adapters: $TRAINING/models_v9/"
echo " Logs:          $TRAINING/logs/"
echo " Package:       /workspace/titan_v9_lora_models.tar.gz"
echo ""
echo " Download results with:"
echo "   scp -P PORT root@IP:/workspace/titan_v9_lora_models.tar.gz ."
echo ""
echo " Then deploy to VPS (72.62.72.48):"
echo "   scp titan_v9_lora_models.tar.gz root@72.62.72.48:/opt/titan/training/"
echo "═══════════════════════════════════════════════════════════════"
