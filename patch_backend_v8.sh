#!/bin/bash
# Patch /opt/lucid-empire/backend/server.py to V8.0 MAXIMUM
set -e

FILE="/opt/lucid-empire/backend/server.py"

# Backup first
cp "$FILE" "${FILE}.bak_v7"
echo "  Backup: ${FILE}.bak_v7"

# Apply patches with sed
sed -i 's/TITAN V7\.0 SINGULARITY/TITAN V8.0 MAXIMUM/g' "$FILE"
sed -i 's/TITAN V7\.0 SINGULARITY API/TITAN V8.0 MAXIMUM API/g' "$FILE"
sed -i 's/version="7\.0\.0"/version="8.0.0"/g' "$FILE"
sed -i 's/"version": "7\.0\.0"/"version": "8.0.0"/g' "$FILE"
sed -i 's/Starting TITAN V7\.0 Backend/Starting TITAN V8.0 Backend/g' "$FILE"

echo "  Patched: $FILE"
echo ""
echo "  Verification:"
grep -n "V8.0\|8\.0\.0" "$FILE" | head -10

echo ""
echo "  Restarting backend service..."
# Find the uvicorn process and restart it
UVICORN_PID=$(pgrep -f "uvicorn backend.server" | head -1)
if [ -n "$UVICORN_PID" ]; then
    # Find the parent process (the one that launched uvicorn)
    PARENT_PID=$(ps -o ppid= -p "$UVICORN_PID" | tr -d ' ')
    echo "  Uvicorn PID: $UVICORN_PID (parent: $PARENT_PID)"
    
    # Kill all uvicorn workers for this app
    pkill -f "uvicorn backend.server" 2>/dev/null || true
    sleep 2
    
    # Restart in background
    cd /opt/lucid-empire
    nohup python3 -m uvicorn backend.server:app \
        --host 0.0.0.0 \
        --port 8000 \
        --workers 4 \
        --log-level warning \
        >> /var/log/titan-backend.log 2>&1 &
    
    sleep 3
    
    # Verify it's back up
    NEW_PID=$(pgrep -f "uvicorn backend.server" | head -1)
    if [ -n "$NEW_PID" ]; then
        echo "  ✅ Backend restarted (PID: $NEW_PID)"
    else
        echo "  ❌ Backend failed to restart — check /var/log/titan-backend.log"
    fi
else
    echo "  ⚠️  Uvicorn not running — starting fresh..."
    cd /opt/lucid-empire
    nohup python3 -m uvicorn backend.server:app \
        --host 0.0.0.0 \
        --port 8000 \
        --workers 4 \
        --log-level warning \
        >> /var/log/titan-backend.log 2>&1 &
    sleep 3
    echo "  ✅ Backend started"
fi

# Verify API response
sleep 2
echo ""
echo "  API health check:"
curl -s http://localhost:8000/api/health | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'  Status: {d.get(\"status\",\"?\")} | Version: {d.get(\"version\",\"?\")} | Service: {d.get(\"service\",\"?\")}' )" 2>/dev/null || echo "  ⚠️  API not yet responding"

echo ""
echo "  API version check:"
curl -s http://localhost:8000/openapi.json | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'  Title: {d[\"info\"][\"title\"]} | Version: {d[\"info\"][\"version\"]}')" 2>/dev/null || echo "  ⚠️  OpenAPI not responding"
