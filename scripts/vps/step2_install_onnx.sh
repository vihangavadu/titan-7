#!/bin/bash
echo "=== STEP 2: Install ONNX Runtime + Download Model ==="

echo "[1] Installing onnxruntime-genai..."
pip install --pre onnxruntime-genai 2>&1 | tail -5
pip install huggingface_hub 2>&1 | tail -3

echo ""
echo "[2] Checking installs..."
python3 -c "import onnxruntime as ort; print('onnxruntime:', ort.__version__)" 2>&1
python3 -c "import onnxruntime_genai as og; print('onnxruntime-genai: OK')" 2>&1 || echo "onnxruntime-genai not available"

echo ""
echo "[3] Downloading Phi-4-mini ONNX INT4 (~2.2GB)..."
echo "    This may take 5-10 minutes..."
mkdir -p /opt/titan/models/phi4-mini-onnx

ONNX_COUNT=$(find /opt/titan/models/phi4-mini-onnx -name "*.onnx" 2>/dev/null | wc -l)
if [ "$ONNX_COUNT" -gt 0 ]; then
    echo "    Already downloaded ($ONNX_COUNT .onnx files)"
else
    huggingface-cli download microsoft/Phi-4-mini-instruct-onnx \
        --include "cpu_and_mobile/cpu-int4-rtn-block-32-acc-level-4/*" \
        --local-dir /opt/titan/models/phi4-mini-onnx 2>&1 | tail -15
fi

echo ""
echo "[4] Model files:"
find /opt/titan/models/phi4-mini-onnx -name "*.onnx" -exec ls -lh {} \; 2>/dev/null
du -sh /opt/titan/models/phi4-mini-onnx 2>/dev/null

echo ""
echo "[5] Disk space:"
df -h / | tail -1

echo "=== STEP 2 DONE ==="
