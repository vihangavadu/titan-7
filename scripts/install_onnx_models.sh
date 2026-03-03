#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# TITAN X — ONNX INT4 Model Installer
# Downloads and installs 4 lightweight ONNX INT4 models for CPU inference
# on the VPS (no GPU required). Uses onnxruntime-genai for generation.
#
# Models selected for minimum size + maximum task coverage:
#   1. phi-3-mini-4k-instruct-int4  (~2.0 GB) — fast reasoning, all tasks
#   2. qwen2.5-1.5b-instruct-int4   (~0.9 GB) — ultra-fast responses  
#   3. llama-3.2-1b-instruct-int4   (~0.7 GB) — minimal footprint
#   4. smollm2-1.7b-instruct-int4   (~1.0 GB) — small, smart
#
# Total: ~4.6 GB vs ~12 GB for old Ollama models
# ═══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

ONNX_DIR="/opt/titan/models/onnx"
VENV_PY="/opt/titan/venv/bin/python3"
PY="${VENV_PY:-python3}"
HF_BASE="https://huggingface.co"

echo "═══════════════════════════════════════════════════"
echo "  TITAN X — ONNX INT4 Model Installer"
echo "═══════════════════════════════════════════════════"
echo ""

# Create model directory
mkdir -p "$ONNX_DIR"
echo "[1/5] Model directory: $ONNX_DIR"

# Install onnxruntime-genai (CPU build)
echo ""
echo "[2/5] Installing onnxruntime-genai (CPU)..."
if command -v pip3 &>/dev/null; then
    pip3 install --quiet onnxruntime-genai onnxruntime --upgrade 2>&1 | tail -5
    echo "  ✓ onnxruntime-genai installed"
elif $PY -m pip install --quiet onnxruntime-genai onnxruntime --upgrade 2>&1 | tail -5; then
    echo "  ✓ onnxruntime-genai installed"
else
    echo "  ⚠ pip not available — install manually: pip install onnxruntime-genai"
fi

# Install huggingface_hub for downloads
pip3 install --quiet huggingface_hub 2>/dev/null || true

echo ""
echo "[3/5] Downloading ONNX INT4 models (this may take 10-20 min)..."

download_model() {
    local repo="$1"
    local name="$2"
    local dest="$ONNX_DIR/$name"
    
    if [ -d "$dest" ] && [ -f "$dest/model.onnx" ]; then
        echo "  ✓ $name already exists, skipping"
        return 0
    fi
    
    echo "  → Downloading $name from $repo ..."
    mkdir -p "$dest"
    
    # Try huggingface_hub first
    if python3 -c "from huggingface_hub import snapshot_download; snapshot_download('$repo', local_dir='$dest', ignore_patterns=['*.md','*.txt','*.bin','*.safetensors'])" 2>/dev/null; then
        echo "    ✓ $name downloaded"
    else
        # Fallback: wget key files
        echo "    → huggingface_hub failed, trying direct download..."
        local base_url="$HF_BASE/$repo/resolve/main"
        for f in model.onnx model.onnx.data tokenizer.json tokenizer_config.json generation_config.json config.json; do
            wget -q --no-clobber -O "$dest/$f" "$base_url/$f" 2>/dev/null || true
        done
        if [ -f "$dest/model.onnx" ]; then
            echo "    ✓ $name downloaded (direct)"
        else
            echo "    ⚠ $name download failed — check network or download manually"
        fi
    fi
}

# Model 1: Phi-3 Mini INT4 (Microsoft, ONNX-optimized)
download_model "microsoft/Phi-3-mini-4k-instruct-onnx" "phi3-mini-int4"

# Model 2: Qwen 2.5 1.5B INT4 
download_model "Qwen/Qwen2.5-1.5B-Instruct-ONNX-INT4" "qwen2.5-1.5b-int4"

# Model 3: LLaMA 3.2 1B INT4
download_model "onnx-community/Llama-3.2-1B-Instruct-ONNX-INT4" "llama3.2-1b-int4"

# Model 4: SmolLM2 1.7B INT4
download_model "HuggingFaceTB/SmolLM2-1.7B-Instruct-ONNX-INT4" "smollm2-1.7b-int4"

echo ""
echo "[4/5] Writing model registry..."
cat > "$ONNX_DIR/registry.json" << 'REGISTRY'
{
  "version": "10.0",
  "engine": "onnxruntime-genai",
  "models": {
    "titan-fast-onnx": {
      "path": "/opt/titan/models/onnx/qwen2.5-1.5b-int4",
      "type": "onnx-int4",
      "size_gb": 0.9,
      "tasks": ["form_fill", "trajectory_tuning", "cookie_value_generation", "autofill_data_generation"],
      "max_tokens": 512,
      "ctx_length": 4096
    },
    "titan-analyst-onnx": {
      "path": "/opt/titan/models/onnx/phi3-mini-int4",
      "type": "onnx-int4",
      "size_gb": 2.0,
      "tasks": ["live_target_scoring", "profile_optimization", "persona_consistency_check", "card_target_matching", "validation_strategy"],
      "max_tokens": 2048,
      "ctx_length": 4096
    },
    "titan-strategist-onnx": {
      "path": "/opt/titan/models/onnx/llama3.2-1b-int4",
      "type": "onnx-int4",
      "size_gb": 0.7,
      "tasks": ["detection_root_cause", "issuer_behavior_prediction", "first_session_warmup_plan", "copilot_abort_prediction"],
      "max_tokens": 2048,
      "ctx_length": 4096
    },
    "titan-nano-onnx": {
      "path": "/opt/titan/models/onnx/smollm2-1.7b-int4",
      "type": "onnx-int4",
      "size_gb": 1.0,
      "tasks": ["quick_classification", "bin_lookup", "ga_event_planning", "hardware_profile_coherence"],
      "max_tokens": 256,
      "ctx_length": 2048
    }
  },
  "fallback_order": ["ollama:titan-analyst", "ollama:titan-strategist", "ollama:titan-fast", "ollama:titan-operator"]
}
REGISTRY

echo "  ✓ Registry written to $ONNX_DIR/registry.json"

echo ""
echo "[5/5] Verifying installation..."
python3 -c "
import onnxruntime
import os
print(f'  ✓ onnxruntime version: {onnxruntime.__version__}')
print(f'  ✓ Providers: {onnxruntime.get_available_providers()}')
models_dir = '/opt/titan/models/onnx'
installed = [d for d in os.listdir(models_dir) if os.path.isdir(f'{models_dir}/{d}') and d != '__pycache__'] if os.path.exists(models_dir) else []
print(f'  ✓ ONNX models installed: {len(installed)} — {installed}')
" 2>/dev/null || echo "  ⚠ onnxruntime not yet importable (may need: pip install onnxruntime)"

echo ""
echo "═══════════════════════════════════════════════════"
echo "  ONNX installation complete."
echo "  Models: $ONNX_DIR"
echo "  Fallback: Ollama (titan-analyst, titan-strategist, titan-fast, titan-operator)"
echo "═══════════════════════════════════════════════════"
