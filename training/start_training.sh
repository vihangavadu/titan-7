#!/bin/bash
# Start titan-analyst LoRA training with monitoring

TASK="analyst"
EPOCHS=3
MAX_EXAMPLES=300

# Create start metadata
cat > /opt/titan/training/logs/training_start.json << EOF
{
  "task": "$TASK",
  "start_time": "$(date -Iseconds)",
  "total_examples": $MAX_EXAMPLES,
  "epochs": $EPOCHS,
  "estimated_seconds": 50400
}
EOF

# Source environment variables
source /etc/profile.d/titan_ml.sh 2>/dev/null

# Start training in background
cd /opt/titan/training/phase3
nohup python3 lora_finetune.py \
    --task $TASK \
    --epochs $EPOCHS \
    --max-examples $MAX_EXAMPLES \
    > /opt/titan/training/logs/analyst_train.log 2>&1 &

TRAIN_PID=$!
echo $TRAIN_PID > /opt/titan/training/logs/training.pid

echo "Training started (PID: $TRAIN_PID)"
echo "Task: $TASK"
echo "Examples: $MAX_EXAMPLES"
echo "Epochs: $EPOCHS"
echo "Estimated time: 14 hours"
echo ""
echo "Monitor at: http://72.62.72.48:5000"
echo "Log file: /opt/titan/training/logs/analyst_train.log"
echo ""
echo "To check progress:"
echo "  tail -f /opt/titan/training/logs/analyst_train.log"
