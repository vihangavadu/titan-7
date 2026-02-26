#!/bin/bash
echo "=== AI MODEL + TRAINING DATA RESEARCH ==="

echo "[1] CPU SPECS"
lscpu | grep -E "Model name|CPU\(s\)|Thread|MHz|Cache"

echo ""
echo "[2] RAM"
free -h | head -2

echo ""
echo "[3] CURRENT OLLAMA MODELS"
ollama list

echo ""
echo "[4] ONNX RUNTIME CHECK"
python3 << 'PYEOF'
try:
    import onnxruntime as ort
    print(f"ONNX Runtime: {ort.__version__}")
    print(f"Providers: {ort.get_available_providers()}")
except ImportError:
    print("onnxruntime NOT installed")
    print("Install: pip install onnxruntime")
PYEOF

echo ""
echo "[5] EXISTING TRAINING DATA STRUCTURE"
echo "-- training/ directory --"
find /opt/titan/training -maxdepth 2 -type f -name "*.py" -o -name "*.jsonl" -o -name "*.json" -o -name "*.sh" -o -name "*.md" -o -name "*.modelfile" 2>/dev/null | sort

echo ""
echo "-- training data generators --"
ls -la /opt/titan/training/phase2/generate_training_data*.py 2>/dev/null
ls -la /opt/titan/training/phase2/v9_*.py 2>/dev/null

echo ""
echo "[6] CURRENT TASK ROUTING (what AI does)"
python3 << 'PYEOF'
import json, os
cfg_path = "/opt/titan/config/llm_config.json"
if os.path.exists(cfg_path):
    cfg = json.load(open(cfg_path))
    tr = cfg.get("task_routing", {})
    actual = {k:v for k,v in tr.items() if not k.startswith("_")}
    print(f"  Total task routes: {len(actual)}")
    for k,v in sorted(actual.items()):
        model = v if isinstance(v, str) else v.get("model", str(v)[:50])
        print(f"    {k}")
else:
    print("  llm_config.json not found")
PYEOF

echo ""
echo "[7] MODELFILE ANALYSIS"
for mf in /opt/titan/training/phase1/*.modelfile /opt/titan/modelfiles/*.modelfile 2>/dev/null; do
    name=$(basename "$mf")
    lines=$(wc -l < "$mf")
    echo "  $name ($lines lines)"
done

echo ""
echo "[8] DISK SPACE FOR NEW MODELS"
df -h / | tail -1

echo ""
echo "=== DONE ==="
