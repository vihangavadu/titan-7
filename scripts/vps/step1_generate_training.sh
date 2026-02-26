#!/bin/bash
echo "=== STEP 1: Generate Operator Training Data ==="
export PYTHONPATH="/opt/titan:/opt/titan/core:/opt/titan/apps"
cd /opt/titan/training/phase2
python3 generate_operator_training_data.py --count 200 --validate
echo ""
echo "Files:"
ls -lh /opt/titan/training/data_v10_operator/*.jsonl 2>/dev/null
echo "=== STEP 1 DONE ==="
