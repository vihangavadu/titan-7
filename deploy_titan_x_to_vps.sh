#!/bin/bash
# TITAN X V10.0 — Deploy to Hostinger VPS with Gap Analysis
# Usage: ./deploy_titan_x_to_vps.sh root@72.62.72.48

set -e

VPS_HOST="${1:-root@72.62.72.48}"
TITAN_LOCAL="/root/Downloads/titan-7/titan-7/titan-7"
TITAN_REMOTE="/opt/titan"
REPORT_FILE="/tmp/titan_vps_gap_report_$(date +%Y%m%d_%H%M%S).txt"

echo "=========================================="
echo "TITAN X V10.0 — VPS Deployment & Gap Analysis"
echo "=========================================="
echo "VPS: $VPS_HOST"
echo "Local: $TITAN_LOCAL"
echo "Remote: $TITAN_REMOTE"
echo "Report: $REPORT_FILE"
echo ""

# Create report header
cat > "$REPORT_FILE" << EOF
TITAN X V10.0 — VPS Gap Analysis Report
Generated: $(date)
VPS: $VPS_HOST
========================================

EOF

# 1. Check VPS connectivity
echo "1. Checking VPS connectivity..."
if ssh -o ConnectTimeout=10 "$VPS_HOST" "echo 'VPS connected'"; then
    echo "✓ VPS reachable"
    echo "✓ VPS reachable" >> "$REPORT_FILE"
else
    echo "✗ Cannot connect to VPS"
    echo "✗ Cannot connect to VPS" >> "$REPORT_FILE"
    exit 1
fi

# 2. Check current Titan version on VPS
echo ""
echo "2. Checking current Titan version on VPS..."
VPS_VERSION=$(ssh "$VPS_HOST" "cd $TITAN_REMOTE/src/core 2>/dev/null && python3 -c 'from __init__ import __version__; print(__version__)' 2>/dev/null || echo 'NOT_FOUND'")
echo "VPS version: $VPS_VERSION"
echo "VPS version: $VPS_VERSION" >> "$REPORT_FILE"

LOCAL_VERSION=$(cd "$TITAN_LOCAL/src/core" && python3 -c "from __init__ import __version__; print(__version__)")
echo "Local version: $LOCAL_VERSION"
echo "Local version: $LOCAL_VERSION" >> "$REPORT_FILE"

# 3. Deploy updated codebase
echo ""
echo "3. Deploying updated codebase to VPS..."
echo "Syncing files (excluding large binaries)..." | tee -a "$REPORT_FILE"

rsync -avz --delete \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='tools/multilogin6/multilogin.deb' \
    --exclude='tools/multilogin6/extracted' \
    --exclude='.venv' \
    --exclude='node_modules' \
    --exclude='*.log' \
    --exclude='*.cache' \
    "$TITAN_LOCAL/" "$VPS_HOST:$TITAN_REMOTE/" | tee -a "$REPORT_FILE"

echo "✓ Codebase synced" | tee -a "$REPORT_FILE"

# 4. Verify deployment
echo ""
echo "4. Verifying deployment on VPS..."
ssh "$VPS_HOST" bash -c "
cd $TITAN_REMOTE
echo '=== File Counts ==='
echo 'Core Python files:' \$(find src/core -name '*.py' | wc -l)
echo 'App Python files:' \$(find src/apps -name '*.py' | wc -l)
echo 'Genesis AppX files:' \$(find tools/multilogin6/genesis_appx -name '*.py' | wc -l)
echo ''
echo '=== Key Files Check ==='
for f in 'src/core/__init__.py' 'src/core/genesis_core.py' 'src/apps/titan_launcher.py' 'tools/multilogin6/genesis_appx/genesis_bridge_api.py' 'scripts/build_iso.sh'; do
    if [ -f \"\$f\" ]; then
        echo \"✓ \$f\"
    else
        echo \"✗ \$f MISSING\"
    fi
done
" | tee -a "$REPORT_FILE"

# 5. Check services
echo ""
echo "5. Checking services on VPS..."
ssh "$VPS_HOST" bash -c "
echo '=== Service Status ==='
systemctl is-active titan-api 2>/dev/null || echo 'titan-api: NOT FOUND'
systemctl is-active titan-services 2>/dev/null || echo 'titan-services: NOT FOUND'
systemctl is-active genesis-appx-bridge 2>/dev/null || echo 'genesis-appx-bridge: NOT FOUND'
echo ''
echo '=== Python Dependencies ==="
python3 -c \"import titan_onnx_engine; print('✓ ONNX engine available')\" 2>/dev/null || echo \"✗ ONNX engine missing\"
python3 -c \"import ollama_bridge; print('✓ Ollama bridge available')\" 2>/dev/null || echo \"✗ Ollama bridge missing\"
python3 -c \"import genesis_core; print('✓ Genesis core available')\" 2>/dev/null || echo \"✗ Genesis core missing\"
" | tee -a "$REPORT_FILE"

# 6. Check AI models
echo ""
echo "6. Checking AI models on VPS..."
ssh "$VPS_HOST" bash -c "
if command -v ollama &>/dev/null; then
    echo '=== Ollama Models ==='
    ollama list 2>/dev/null || echo 'Ollama not responding'
else
    echo '✗ Ollama not installed'
fi
echo ''
if [ -f $TITAN_REMOTE/src/config/llm_config.json ]; then
    echo '=== LLM Config Routes ==='
    python3 -c \"import json; cfg=json.load(open('$TITAN_REMOTE/src/config/llm_config.json')); routes=[k for k in cfg.get('task_routing',{}).keys() if not k.startswith('_')]; print(f'Task routes: {len(routes)}')\"
else
    echo '✗ llm_config.json not found'
fi
" | tee -a "$REPORT_FILE"

# 7. Check Genesis AppX
echo ""
echo "7. Checking Genesis AppX on VPS..."
ssh "$VPS_HOST" bash -c "
echo '=== Genesis AppX Status ==='
if [ -d /opt/genesis-appx ]; then
    echo '✓ /opt/genesis-appx exists'
    echo 'Files:' \$(find /opt/genesis-appx -name '*.py' | wc -l)
    if [ -f /opt/genesis-appx/genesis_bridge_api.py ]; then
        echo '✓ Bridge API exists'
        echo 'Endpoints:' \$(grep -c '@app.route' /opt/genesis-appx/genesis_bridge_api.py)
    else
        echo '✗ Bridge API missing'
    fi
else
    echo '✗ /opt/genesis-appx not found'
fi
echo ''
if [ -d /opt/Multilogin ]; then
    echo '✓ ML6 installed at /opt/Multilogin'
else
    echo '✗ ML6 not installed'
fi
" | tee -a "$REPORT_FILE"

# 8. Generate gap summary
echo "" | tee -a "$REPORT_FILE"
echo "8. Gap Summary:" | tee -a "$REPORT_FILE"
echo "==============" | tee -a "$REPORT_FILE"

if [ "$VPS_VERSION" != "$LOCAL_VERSION" ]; then
    echo "⚠ VERSION MISMATCH: VPS=$VPS_VERSION, Local=$LOCAL_VERSION" | tee -a "$REPORT_FILE"
else
    echo "✓ Versions match" | tee -a "$REPORT_FILE"
fi

# Check for missing critical files
MISSING_COUNT=$(ssh "$VPS_HOST" "cd $TITAN_REMOTE && for f in 'src/core/genesis_core.py' 'src/apps/titan_operations.py' 'tools/multilogin6/genesis_appx/genesis_bridge_api.py'; do [ ! -f \"\$f\" ] && echo missing; done | wc -l")
if [ "$MISSING_COUNT" -gt 0 ]; then
    echo "⚠ $MISSING_COUNT critical files missing" | tee -a "$REPORT_FILE"
else
    echo "✓ All critical files present" | tee -a "$REPORT_FILE"
fi

# 9. Recommendations
echo "" | tee -a "$REPORT_FILE"
echo "9. Recommendations:" | tee -a "$REPORT_FILE"
echo "==================" | tee -a "$REPORT_FILE"

if [ "$VPS_VERSION" != "$LOCAL_VERSION" ]; then
    echo "→ Restart services to load new version:" | tee -a "$REPORT_FILE"
    echo "  ssh $VPS_HOST 'systemctl restart titan-api titan-services'" | tee -a "$REPORT_FILE"
fi

echo "→ Verify all apps launch:" | tee -a "$REPORT_FILE"
echo "  ssh $VPS_HOST 'cd $TITAN_REMOTE && python3 src/apps/titan_launcher.py'" | tee -a "$REPORT_FILE"

echo "→ Check logs if issues:" | tee -a "$REPORT_FILE"
echo "  ssh $VPS_HOST 'journalctl -u titan-api -f'" | tee -a "$REPORT_FILE"

echo ""
echo "========================================"
echo "Deployment complete!"
echo "Report saved to: $REPORT_FILE"
echo "========================================"

# Show report
echo ""
cat "$REPORT_FILE"
