#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# TITAN X — First Boot Readiness Script  v10.0
# ═══════════════════════════════════════════════════════════════════════════════
# Runs automatically on first boot (or manually to restore health).
# Performs 15 readiness steps and produces a JSON report.
#
# Usage:
#   bash /opt/titan/bin/titan-first-boot          # full run
#   bash /opt/titan/bin/titan-first-boot --quick  # skip downloads
#   bash /opt/titan/bin/titan-first-boot --check  # check only, no fixes
#
# After first run, operator only needs to:
#   1. Add Mullvad account:    mullvad account set <ACCOUNT_NUMBER>
#   2. Add proxy credentials:  edit /opt/titan/config/titan.env
#   3. Add Groq API key:       edit /opt/titan/config/titan.env
#   4. Connect VPN:            mullvad connect
#   5. Open Titan X launcher:  python3 /opt/titan/src/apps/titan_launcher.py
# ═══════════════════════════════════════════════════════════════════════════════
set -uo pipefail

TITAN_DIR="${TITAN_DIR:-/opt/titan}"
REPORT_FILE="$TITAN_DIR/state/first_boot_report.json"
MODE="${1:---full}"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
PASS=0
WARN=0
FAIL=0

mkdir -p "$TITAN_DIR/state" "$TITAN_DIR/logs"
LOG="$TITAN_DIR/logs/first_boot_$(date +%Y%m%d_%H%M%S).log"
exec > >(tee -a "$LOG") 2>&1

echo "═══════════════════════════════════════════════════════════════════════"
echo "  TITAN X — First Boot Readiness  v10.0  ($TIMESTAMP)"
echo "  Mode: $MODE | Titan dir: $TITAN_DIR"
echo "═══════════════════════════════════════════════════════════════════════"
echo ""

RESULTS=()

step_pass() { echo "  ✅  $1"; PASS=$((PASS+1)); RESULTS+=("{\"step\":\"$1\",\"status\":\"pass\"}"); }
step_warn() { echo "  ⚠️   $1"; WARN=$((WARN+1)); RESULTS+=("{\"step\":\"$1\",\"status\":\"warn\",\"note\":\"$2\"}"); }
step_fail() { echo "  ❌  $1"; FAIL=$((FAIL+1)); RESULTS+=("{\"step\":\"$1\",\"status\":\"fail\",\"note\":\"$2\"}"); }

# ── Step 1: Codebase integrity ───────────────────────────────────────────────
echo "[ 1/15] Codebase integrity..."
CORE_COUNT=$(find "$TITAN_DIR/src/core" -name "*.py" 2>/dev/null | wc -l)
APP_COUNT=$(find "$TITAN_DIR/src/apps" -name "*.py" 2>/dev/null | wc -l)
if [ "$CORE_COUNT" -ge 100 ] && [ "$APP_COUNT" -ge 15 ]; then
    step_pass "Codebase: $CORE_COUNT core modules, $APP_COUNT apps"
elif [ "$CORE_COUNT" -ge 50 ]; then
    step_warn "Codebase: $CORE_COUNT modules (expected 100+)" "some modules may be missing"
else
    step_fail "Codebase incomplete: only $CORE_COUNT core modules" "re-deploy from git repo"
fi

# ── Step 2: Python syntax check ──────────────────────────────────────────────
echo "[ 2/15] Python syntax check (core + apps)..."
SYNTAX_ERRORS=0
for f in "$TITAN_DIR/src/core/"*.py "$TITAN_DIR/src/apps/"*.py; do
    [ -f "$f" ] || continue
    python3 -m py_compile "$f" 2>/dev/null || SYNTAX_ERRORS=$((SYNTAX_ERRORS+1))
done
if [ "$SYNTAX_ERRORS" -eq 0 ]; then
    step_pass "Python syntax: all files OK"
else
    step_fail "Python syntax: $SYNTAX_ERRORS files have errors" "check logs for details"
fi

# ── Step 3: Ollama AI service ────────────────────────────────────────────────
echo "[ 3/15] Ollama AI service..."
if curl -s --max-time 5 "http://127.0.0.1:11434/api/tags" | grep -q '"models"'; then
    MODEL_COUNT=$(curl -s "http://127.0.0.1:11434/api/tags" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('models',[])))" 2>/dev/null || echo "?")
    step_pass "Ollama AI: online, $MODEL_COUNT models loaded"
else
    if [ "$MODE" != "--check" ]; then
        echo "       → Starting Ollama service..."
        systemctl start ollama 2>/dev/null || ollama serve &>/dev/null &
        sleep 5
        if curl -s --max-time 5 "http://127.0.0.1:11434/api/tags" | grep -q '"models"'; then
            step_pass "Ollama AI: started successfully"
        else
            step_warn "Ollama AI: could not start" "run: systemctl start ollama"
        fi
    else
        step_warn "Ollama AI: offline" "run: systemctl start ollama"
    fi
fi

# ── Step 4: Required AI models ───────────────────────────────────────────────
echo "[ 4/15] Required AI models (titan-*)..."
REQUIRED_MODELS=("titan-analyst" "titan-strategist" "titan-fast" "titan-operator")
MISSING_MODELS=()
for m in "${REQUIRED_MODELS[@]}"; do
    if ! ollama list 2>/dev/null | grep -q "^$m"; then
        MISSING_MODELS+=("$m")
    fi
done
if [ ${#MISSING_MODELS[@]} -eq 0 ]; then
    step_pass "AI models: all 4 required models present"
elif [ ${#MISSING_MODELS[@]} -le 2 ]; then
    step_warn "AI models: missing ${MISSING_MODELS[*]}" "pull with: ollama pull <model>"
else
    step_fail "AI models: missing ${#MISSING_MODELS[@]} models" "check training/deployment docs"
fi

# ── Step 5: Redis cache ──────────────────────────────────────────────────────
echo "[ 5/15] Redis cache..."
if redis-cli ping 2>/dev/null | grep -q "PONG"; then
    step_pass "Redis: PONG"
else
    if [ "$MODE" != "--check" ]; then
        systemctl start redis-server 2>/dev/null || true
        sleep 2
        if redis-cli ping 2>/dev/null | grep -q "PONG"; then
            step_pass "Redis: started"
        else
            step_warn "Redis: could not start" "run: systemctl start redis-server"
        fi
    else
        step_warn "Redis: offline" "run: systemctl start redis-server"
    fi
fi

# ── Step 6: Mullvad VPN ──────────────────────────────────────────────────────
echo "[ 6/15] Mullvad VPN..."
if command -v mullvad &>/dev/null; then
    VPN_STATUS=$(mullvad status 2>/dev/null || echo "unknown")
    if echo "$VPN_STATUS" | grep -q "Connected"; then
        step_pass "Mullvad VPN: Connected"
    else
        step_warn "Mullvad VPN: installed but $VPN_STATUS" "set account: mullvad account set <16-digit>"
    fi
else
    step_fail "Mullvad VPN: not installed" "install: apt install mullvad-vpn"
fi

# ── Step 7: Proxy configuration ──────────────────────────────────────────────
echo "[ 7/15] Proxy configuration..."
TITAN_ENV="$TITAN_DIR/config/titan.env"
if [ -f "$TITAN_ENV" ] && grep -q "TITAN_PROXY_USERNAME=" "$TITAN_ENV"; then
    PROXY_USER=$(grep "TITAN_PROXY_USERNAME=" "$TITAN_ENV" | cut -d= -f2)
    if [ -n "$PROXY_USER" ] && [ "$PROXY_USER" != "your_proxy_username_here" ]; then
        step_pass "Proxy: configured (provider=$(grep 'TITAN_PROXY_PROVIDER' "$TITAN_ENV" 2>/dev/null | cut -d= -f2 || echo 'custom'))"
    else
        step_fail "Proxy: placeholder credentials" "edit $TITAN_ENV and set TITAN_PROXY_USERNAME/PASSWORD"
    fi
else
    step_fail "Proxy: not configured" "edit $TITAN_ENV — required for checkout operations"
fi

# ── Step 8: API keys ─────────────────────────────────────────────────────────
echo "[ 8/15] API keys..."
KEYS_OK=0
[ -f "$TITAN_ENV" ] && grep -q "TITAN_GROQ_API_KEY=gsk_" "$TITAN_ENV" && KEYS_OK=$((KEYS_OK+1))
[ -f "$TITAN_ENV" ] && grep -q "TITAN_OPENAI_API_KEY=sk-" "$TITAN_ENV" && KEYS_OK=$((KEYS_OK+1))
if [ "$KEYS_OK" -ge 1 ]; then
    step_pass "API keys: $KEYS_OK external key(s) configured"
else
    step_warn "API keys: none configured" "add TITAN_GROQ_API_KEY=gsk_... to $TITAN_ENV (free at console.groq.com)"
fi

# ── Step 9: Camoufox browser ─────────────────────────────────────────────────
echo "[ 9/15] Camoufox browser engine..."
if python3 -c "import camoufox" 2>/dev/null; then
    CAMFOX_VER=$(python3 -c "import camoufox; print(getattr(camoufox,'__version__','?'))" 2>/dev/null || echo "?")
    step_pass "Camoufox: v$CAMFOX_VER"
else
    if [ "$MODE" != "--check" ]; then
        pip3 install camoufox[geoip] --quiet 2>&1 | tail -3
        python3 -c "import camoufox" 2>/dev/null && \
            step_pass "Camoufox: installed" || \
            step_fail "Camoufox: install failed" "run: pip3 install camoufox[geoip]"
    else
        step_fail "Camoufox: not installed" "run: pip3 install camoufox[geoip]"
    fi
fi

# ── Step 10: Waydroid (Android VM) ───────────────────────────────────────────
echo "[10/15] Waydroid (Android VM for KYC)..."
if command -v waydroid &>/dev/null; then
    WD_STATUS=$(waydroid status 2>/dev/null | head -3 || echo "stopped")
    if echo "$WD_STATUS" | grep -qi "running\|RUNNING\|active"; then
        step_pass "Waydroid: running"
    else
        step_warn "Waydroid: installed but stopped" "start: waydroid session start"
    fi
else
    step_warn "Waydroid: not installed" "optional — needed for KYC mobile verification flow"
fi

# ── Step 11: Bridge API services ─────────────────────────────────────────────
echo "[11/15] Bridge API services..."
BRIDGES_UP=0
BRIDGE_SCRIPTS=(
    "$TITAN_DIR/tools/kyc_appx/launch_kyc_appx.sh"
    "$TITAN_DIR/tools/cerberus_appx/launch_cerberus_appx.sh"
    "$TITAN_DIR/tools/kyc_appx/kyc_bridge_api.py"
)
for port in 36200 36300 36400; do
    if curl -s --max-time 2 "http://127.0.0.1:$port/health" | grep -q "."; then
        BRIDGES_UP=$((BRIDGES_UP+1))
    fi
done
if [ "$BRIDGES_UP" -eq 3 ]; then
    step_pass "Bridge APIs: all 3 up (genesis:36200, cerberus:36300, kyc:36400)"
elif [ "$BRIDGES_UP" -gt 0 ]; then
    step_warn "Bridge APIs: $BRIDGES_UP/3 up" "start missing bridges via Admin app"
else
    step_warn "Bridge APIs: all offline" "start via Admin → Services tab or titan-services.sh"
fi

# ── Step 12: DISPLAY / X11 ───────────────────────────────────────────────────
echo "[12/15] Display environment (X11/XFCE)..."
DISPLAY_OK=false
if [ -n "${DISPLAY:-}" ]; then
    if xdpyinfo -display "$DISPLAY" &>/dev/null 2>&1; then
        DISPLAY_OK=true
    fi
fi
if ! $DISPLAY_OK; then
    for disp in :10 :0 :1; do
        if xdpyinfo -display "$disp" &>/dev/null 2>&1; then
            export DISPLAY="$disp"
            DISPLAY_OK=true
            break
        fi
    done
fi
if $DISPLAY_OK; then
    step_pass "Display: DISPLAY=$DISPLAY (X11 available)"
else
    step_warn "Display: no X11 display found" "connect via RDP (port 3389) to get XFCE desktop"
fi

# ── Step 13: Environment file ─────────────────────────────────────────────────
echo "[13/15] titan.env configuration..."
if [ ! -f "$TITAN_ENV" ]; then
    if [ "$MODE" != "--check" ]; then
        mkdir -p "$TITAN_DIR/config"
        cat > "$TITAN_ENV" << 'ENVFILE'
# TITAN X Configuration
# Edit this file to configure your installation.
# Required (for operations):
TITAN_PROXY_PROVIDER=brightdata
TITAN_PROXY_USERNAME=your_proxy_username_here
TITAN_PROXY_PASSWORD=your_proxy_password_here
TITAN_MULLVAD_ACCOUNT=your_16_digit_account_here

# Recommended (for AI features):
TITAN_GROQ_API_KEY=gsk_your_groq_key_here

# Optional:
TITAN_OPENAI_API_KEY=
TITAN_ANTHROPIC_API_KEY=
SERPAPI_KEY=
ENVFILE
        step_pass "titan.env: created with template"
    else
        step_warn "titan.env: missing" "will be created on first run"
    fi
else
    step_pass "titan.env: exists"
fi

# ── Step 14: ONNX models ─────────────────────────────────────────────────────
echo "[14/15] ONNX models (lightweight CPU inference)..."
ONNX_DIR="$TITAN_DIR/models/onnx"
if [ -f "$ONNX_DIR/registry.json" ]; then
    ONNX_MODELS=$(find "$ONNX_DIR" -name "*.onnx" 2>/dev/null | wc -l)
    if [ "$ONNX_MODELS" -ge 1 ]; then
        step_pass "ONNX models: $ONNX_MODELS model files found"
    else
        step_warn "ONNX models: registry exists but no .onnx files" "run: bash $TITAN_DIR/scripts/install_onnx_models.sh"
    fi
else
    if [ "$MODE" = "--full" ]; then
        echo "       → Installing ONNX models (this takes 10-20 min)..."
        bash "$(dirname "$0")/install_onnx_models.sh" 2>&1 | tail -10 || true
        [ -f "$ONNX_DIR/registry.json" ] && \
            step_pass "ONNX models: installed" || \
            step_warn "ONNX models: install had issues" "check $LOG"
    else
        step_warn "ONNX models: not installed" "run: bash $TITAN_DIR/scripts/install_onnx_models.sh --quick"
    fi
fi

# ── Step 15: Write state and branding ────────────────────────────────────────
echo "[15/15] Finalizing..."
mkdir -p "$TITAN_DIR/state" "$TITAN_DIR/data/profiles" "$TITAN_DIR/data/ops"

# Persist DISPLAY if found
if [ -n "${DISPLAY:-}" ]; then
    echo "export DISPLAY=$DISPLAY" >> /etc/profile.d/titan-display.sh 2>/dev/null || true
    echo "export DISPLAY=$DISPLAY" >> /root/.bashrc 2>/dev/null || true
fi

# Create systemd environment override for DISPLAY
if command -v systemctl &>/dev/null; then
    mkdir -p /etc/systemd/system/titan.service.d 2>/dev/null || true
fi

step_pass "State files and directories initialized"

# ── Final report ─────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════════════════"
TOTAL=$((PASS+WARN+FAIL))
PCT=$((PASS*100/TOTAL))

echo "  TITAN X READINESS REPORT"
echo "  Timestamp : $TIMESTAMP"
echo "  Pass      : $PASS / $TOTAL  ($PCT%)"
echo "  Warnings  : $WARN"
echo "  Failures  : $FAIL"
echo ""

if [ "$PCT" -ge 87 ]; then
    echo "  STATUS: ✅ OPERATIONAL — system is ready for live operations"
    echo ""
    echo "  OPERATOR CHECKLIST (mandatory before first operation):"
    echo "    1. Set Mullvad account:   mullvad account set <16-digit-number>"
    echo "    2. Connect VPN:           mullvad connect"
    echo "    3. Set proxy creds:       nano $TITAN_ENV"
    echo "    4. Set Groq API key:      nano $TITAN_ENV  (free at console.groq.com)"
    echo "    5. Open Titan X:          python3 $TITAN_DIR/src/apps/titan_launcher.py"
elif [ "$PCT" -ge 60 ]; then
    echo "  STATUS: ⚠️  DEGRADED — fix warnings above for best results"
    echo ""
    echo "  CRITICAL FIXES NEEDED:"
    [ "$FAIL" -gt 0 ] && echo "    → Fix all ❌ failures before attempting operations"
    echo "    → At minimum: configure proxy + VPN + run First-Run Wizard"
else
    echo "  STATUS: ❌ NOT READY — system needs significant configuration"
    echo ""
    echo "  Run this script again with --full after fixing failures"
fi
echo ""
echo "  Full log: $LOG"
echo "═══════════════════════════════════════════════════════════════════════"

# Write JSON report
cat > "$REPORT_FILE" << JSONREPORT
{
  "version": "10.0",
  "timestamp": "$TIMESTAMP",
  "mode": "$MODE",
  "score": $PCT,
  "pass": $PASS,
  "warn": $WARN,
  "fail": $FAIL,
  "total": $TOTAL,
  "status": "$([ $PCT -ge 87 ] && echo 'operational' || ([ $PCT -ge 60 ] && echo 'degraded' || echo 'not_ready'))",
  "log": "$LOG"
}
JSONREPORT

echo "  Report saved: $REPORT_FILE"

exit $([ $FAIL -eq 0 ] && echo 0 || echo 1)
