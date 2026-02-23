#!/bin/bash
# Fix countdown by creating proper start time metadata

cd /opt/titan/training/logs

# Calculate start time (training started at 11:20, it's now ~12:06, so 46 minutes ago)
START_TIME=$(python3 << 'PYEOF'
from datetime import datetime, timedelta
start = datetime.now() - timedelta(minutes=46)
print(start.isoformat())
PYEOF
)

# Create training start metadata
cat > training_start.json << EOF
{
  "task": "analyst",
  "start_time": "$START_TIME",
  "total_examples": 300,
  "epochs": 3,
  "estimated_seconds": 13500
}
EOF

echo "Created training_start.json:"
cat training_start.json

# Verify API now shows countdown
echo ""
echo "Testing API:"
curl -s http://localhost:5000/api/status | python3 -c "import sys, json; d=json.load(sys.stdin); print(f'Running: {d[\"running\"]}'); print(f'Start time: {d[\"start_time\"]}'); print(f'Elapsed: {d[\"elapsed_human\"]}'); print(f'Remaining: {d[\"remaining_human\"]}'); print(f'Progress: {d[\"progress_percent\"]}%')"
