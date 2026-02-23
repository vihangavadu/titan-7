#!/bin/bash
# Start training monitor web app on port 5000

cd /opt/titan/training

# Kill existing monitor if running
pkill -f "training_monitor.py" 2>/dev/null

# Start Flask app in background
nohup python3 training_monitor.py > /opt/titan/training/logs/monitor.log 2>&1 &
MONITOR_PID=$!

echo "Training Monitor started (PID: $MONITOR_PID)"
echo "Access at: http://72.62.72.48:5000"

# Wait for Flask to start
sleep 3

# Test if it's running
if curl -s http://localhost:5000/api/status > /dev/null; then
    echo "✓ Monitor is running and accessible"
    echo "✓ Public URL: http://72.62.72.48:5000"
else
    echo "✗ Monitor failed to start. Check logs:"
    tail -20 /opt/titan/training/logs/monitor.log
fi
