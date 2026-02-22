#!/bin/bash
# TITAN V8.0 — Dev Hub Operational Readiness Verification
# Full real report — no shortcuts

PASS=0
FAIL=0
WARN=0
REPORT=""

log_pass() { echo "  ✅ $1"; PASS=$((PASS+1)); REPORT="$REPORT\n  [PASS] $1"; }
log_fail() { echo "  ❌ $1"; FAIL=$((FAIL+1)); REPORT="$REPORT\n  [FAIL] $1"; }
log_warn() { echo "  ⚠️  $1"; WARN=$((WARN+1)); REPORT="$REPORT\n  [WARN] $1"; }
log_info() { echo "  ℹ️  $1"; REPORT="$REPORT\n  [INFO] $1"; }

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  TITAN V8.0 — DEV HUB OPERATIONAL READINESS REPORT          ║"
echo "║  VPS: 72.62.72.48  |  $(date '+%Y-%m-%d %H:%M:%S UTC')          ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# ── SECTION 1: OS IDENTITY ─────────────────────────────────────────
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  [1] OS IDENTITY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

PRETTY=$(grep PRETTY_NAME /etc/os-release 2>/dev/null | cut -d= -f2 | tr -d '"')
ID=$(grep "^ID=" /etc/os-release 2>/dev/null | cut -d= -f2)
ID_LIKE=$(grep "^ID_LIKE=" /etc/os-release 2>/dev/null)
HOSTNAME=$(hostname)

log_info "OS: $PRETTY"
log_info "ID: $ID | Hostname: $HOSTNAME"

if echo "$PRETTY" | grep -q "Titan OS V8.0"; then
    log_pass "OS identity: Titan OS V8.0 Maximum"
else
    log_fail "OS identity: NOT Titan OS V8.0 — got: $PRETTY"
fi

if [ -z "$ID_LIKE" ]; then
    log_pass "ID_LIKE: absent (no base distro leak)"
else
    log_fail "ID_LIKE: PRESENT — $ID_LIKE"
fi

if grep -qi "debian\|bookworm" /etc/os-release 2>/dev/null; then
    log_fail "Debian refs found in /etc/os-release"
else
    log_pass "No Debian/Bookworm refs in /etc/os-release"
fi

echo ""

# ── SECTION 2: TITAN DEV HUB FILE INTEGRITY ────────────────────────
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  [2] DEV HUB FILE INTEGRITY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

DEVHUB="/opt/titan/apps/titan_dev_hub.py"
if [ -f "$DEVHUB" ]; then
    log_pass "titan_dev_hub.py: exists"
    SIZE=$(wc -c < "$DEVHUB")
    LINES=$(wc -l < "$DEVHUB")
    log_info "Size: ${SIZE} bytes | Lines: ${LINES}"
else
    log_fail "titan_dev_hub.py: NOT FOUND at $DEVHUB"
fi

# Version check
if grep -q "Version: 8.0.0" "$DEVHUB" 2>/dev/null; then
    log_pass "Version: 8.0.0 confirmed"
else
    VER=$(grep "Version:" "$DEVHUB" 2>/dev/null | head -1)
    log_fail "Version: expected 8.0.0, got: $VER"
fi

# V8.0 branding
if grep -q "V8.0 MAXIMUM" "$DEVHUB" 2>/dev/null; then
    log_pass "V8.0 MAXIMUM branding present"
else
    log_fail "V8.0 MAXIMUM branding missing"
fi

# Windsurf provider
if grep -q '"windsurf"' "$DEVHUB" 2>/dev/null; then
    log_pass "Windsurf/Codeium provider: configured"
else
    log_fail "Windsurf provider: missing"
fi

# Copilot provider
if grep -q '"copilot"' "$DEVHUB" 2>/dev/null; then
    log_pass "GitHub Copilot provider: configured"
else
    log_fail "GitHub Copilot provider: missing"
fi

# System editor
if grep -q "SystemEditor\|system_editor\|SafeFileEditor" "$DEVHUB" 2>/dev/null; then
    log_pass "System file editor: present"
else
    log_warn "System file editor: not found in dev hub"
fi

# AI provider manager
if grep -q "AIProviderManager" "$DEVHUB" 2>/dev/null; then
    log_pass "AIProviderManager class: present"
else
    log_fail "AIProviderManager class: missing"
fi

# Issue processor
if grep -q "IssueProcessor" "$DEVHUB" 2>/dev/null; then
    log_pass "IssueProcessor class: present"
else
    log_fail "IssueProcessor class: missing"
fi

# Upgrade manager
if grep -q "UpgradeManager" "$DEVHUB" 2>/dev/null; then
    log_pass "UpgradeManager class: present"
else
    log_fail "UpgradeManager class: missing"
fi

echo ""

# ── SECTION 3: PYTHON SYNTAX CHECK ─────────────────────────────────
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  [3] PYTHON SYNTAX VALIDATION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

SYNTAX_OUT=$(python3 -m py_compile /opt/titan/apps/titan_dev_hub.py 2>&1)
if [ $? -eq 0 ]; then
    log_pass "titan_dev_hub.py: syntax valid"
else
    log_fail "titan_dev_hub.py: SYNTAX ERROR — $SYNTAX_OUT"
fi

# Check all GUI apps
for APP in app_unified.py app_genesis.py app_cerberus.py app_kyc.py app_bug_reporter.py; do
    APPPATH="/opt/titan/apps/$APP"
    if [ -f "$APPPATH" ]; then
        ERR=$(python3 -m py_compile "$APPPATH" 2>&1)
        if [ $? -eq 0 ]; then
            log_pass "$APP: syntax valid"
        else
            log_fail "$APP: SYNTAX ERROR — $ERR"
        fi
    else
        log_warn "$APP: not found"
    fi
done

echo ""

# ── SECTION 4: V8.0 CORE MODULE IMPORTS ────────────────────────────
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  [4] V8.0 CORE MODULE IMPORTS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cd /opt/titan
python3 << 'PYEOF'
import sys
sys.path.insert(0, '/opt/titan/core')

modules = [
    ("ja4_permutation_engine",        "JA4+ Permutation Engine"),
    ("indexeddb_lsng_synthesis",      "IndexedDB LSNG Synthesis"),
    ("tra_exemption_engine",          "TRA Exemption Engine (3DS v2.2)"),
    ("tof_depth_synthesis",           "ToF Depth Map Synthesis"),
    ("issuer_algo_defense",           "Issuer Algorithmic Defense"),
    ("first_session_bias_eliminator", "First-Session Bias Eliminator"),
    ("titan_api",                     "Titan API (Flask backend)"),
    ("titan_services",                "Titan Service Manager"),
    ("kill_switch",                   "Kill Switch"),
    ("quic_proxy",                    "QUIC Proxy"),
    ("genesis_core",                  "Genesis Core"),
    ("cerberus_core",                 "Cerberus Core"),
    ("cognitive_core",                "Cognitive Core"),
    ("ai_intelligence_engine",        "AI Intelligence Engine"),
    ("font_sanitizer",                "Font Sanitizer"),
    ("verify_deep_identity",          "Deep Identity Verifier"),
]

ok = 0
fail = 0
for mod, label in modules:
    try:
        __import__(mod)
        print(f"  ✅ {label}")
        ok += 1
    except ImportError as e:
        print(f"  ❌ {label} — ImportError: {e}")
        fail += 1
    except Exception as e:
        print(f"  ⚠️  {label} — {type(e).__name__}: {e}")
        fail += 1

print(f"\n  Modules: {ok} OK / {fail} FAILED / {ok+fail} total")
PYEOF

echo ""

# ── SECTION 5: AI PROVIDER ENDPOINTS ───────────────────────────────
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  [5] AI PROVIDER ENDPOINT REACHABILITY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

check_endpoint() {
    local NAME=$1
    local URL=$2
    local CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 --max-time 8 "$URL" 2>/dev/null)
    if [ "$CODE" = "200" ] || [ "$CODE" = "401" ] || [ "$CODE" = "403" ] || [ "$CODE" = "404" ]; then
        log_pass "$NAME endpoint reachable (HTTP $CODE)"
    elif [ "$CODE" = "000" ]; then
        log_fail "$NAME endpoint: UNREACHABLE (timeout/DNS)"
    else
        log_warn "$NAME endpoint: HTTP $CODE"
    fi
}

check_endpoint "OpenAI"     "https://api.openai.com/v1/models"
check_endpoint "Anthropic"  "https://api.anthropic.com/v1/models"
check_endpoint "Codeium"    "https://api.codeium.com/v1"
check_endpoint "GitHub API" "https://api.github.com"

# Local Ollama
OLLAMA_STATUS=$(curl -s --connect-timeout 3 http://localhost:11434/api/tags 2>/dev/null)
if echo "$OLLAMA_STATUS" | grep -q "models"; then
    MODELS=$(echo "$OLLAMA_STATUS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(', '.join([m['name'] for m in d.get('models',[])]))" 2>/dev/null)
    log_pass "Local Ollama: ONLINE — Models: $MODELS"
elif [ -n "$OLLAMA_STATUS" ]; then
    log_warn "Local Ollama: responding but no models — $OLLAMA_STATUS"
else
    log_fail "Local Ollama: OFFLINE (port 11434 not responding)"
fi

echo ""

# ── SECTION 6: SYSTEM FILE EDITOR CAPABILITY ───────────────────────
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  [6] SYSTEM FILE EDITOR CAPABILITY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Test write to temp file
TEST_FILE="/tmp/titan_devhub_write_test_$$"
echo "test" > "$TEST_FILE" 2>/dev/null
if [ -f "$TEST_FILE" ]; then
    log_pass "File write capability: OK"
    rm -f "$TEST_FILE"
else
    log_fail "File write capability: FAILED"
fi

# Test backup dir
BACKUP_DIR="/opt/titan/backups"
if [ -d "$BACKUP_DIR" ]; then
    log_pass "Backup directory: exists ($BACKUP_DIR)"
    BACKUPS=$(ls "$BACKUP_DIR" | wc -l)
    log_info "Existing backups: $BACKUPS"
else
    mkdir -p "$BACKUP_DIR" && log_pass "Backup directory: created" || log_fail "Backup directory: cannot create"
fi

# Test Python ast module (needed for syntax validation before applying patches)
python3 -c "import ast; ast.parse('x=1')" 2>/dev/null && log_pass "Python ast module: OK" || log_fail "Python ast module: FAILED"

# Test difflib (needed for patch generation)
python3 -c "import difflib; list(difflib.unified_diff(['a\n'],['b\n']))" 2>/dev/null && log_pass "Python difflib: OK" || log_fail "Python difflib: FAILED"

echo ""

# ── SECTION 7: TITAN API BACKEND ───────────────────────────────────
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  [7] TITAN API BACKEND (port 8000)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

API_STATUS=$(curl -s --connect-timeout 3 http://localhost:8000/api/health 2>/dev/null)
if echo "$API_STATUS" | grep -q "version\|status\|titan"; then
    VERSION=$(echo "$API_STATUS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('version','?'))" 2>/dev/null)
    TITLE=$(curl -s http://localhost:8000/openapi.json | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['info']['title'])" 2>/dev/null)
    log_pass "Titan API: ONLINE — $TITLE v$VERSION"
elif [ -n "$API_STATUS" ]; then
    log_warn "Titan API: responding but unexpected — $API_STATUS"
else
    log_warn "Titan API: OFFLINE — start with: cd /opt/lucid-empire && python3 -m uvicorn backend.server:app --host 0.0.0.0 --port 8000"
fi

# Check if backend process is running (uvicorn or titan_api)
if pgrep -f "uvicorn backend.server" > /dev/null 2>&1; then
    log_pass "Backend process: RUNNING (uvicorn, PID: $(pgrep -f 'uvicorn backend.server' | head -1))"
elif pgrep -f "titan_api" > /dev/null 2>&1; then
    log_pass "Backend process: RUNNING (titan_api, PID: $(pgrep -f titan_api | head -1))"
else
    log_warn "Backend process: not running"
fi

echo ""

# ── SECTION 8: GUI APPS READINESS ──────────────────────────────────
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  [8] GUI APPS V8.0 READINESS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

python3 << 'PYEOF'
import subprocess, os

apps = {
    "app_unified.py":       "Unified Operations Dashboard",
    "app_genesis.py":       "Genesis Profile Forge",
    "app_cerberus.py":      "Cerberus Asset Validation",
    "app_kyc.py":           "KYC Compliance Module",
    "app_bug_reporter.py":  "Diagnostic Reporter",
    "titan_dev_hub.py":     "Dev Hub (AI IDE)",
    "titan_enterprise_theme.py": "Enterprise Theme Engine",
}

apps_dir = "/opt/titan/apps"
ok = 0
fail = 0

for fname, label in apps.items():
    fpath = os.path.join(apps_dir, fname)
    if not os.path.exists(fpath):
        print(f"  ❌ {label}: FILE MISSING")
        fail += 1
        continue

    # Check V8.0 branding
    with open(fpath, 'r', errors='ignore') as f:
        content = f.read()

    has_v8 = "V8.0" in content
    size_kb = len(content) // 1024

    # Syntax check
    result = subprocess.run(
        ["python3", "-m", "py_compile", fpath],
        capture_output=True, text=True
    )
    syntax_ok = result.returncode == 0

    if syntax_ok and has_v8:
        print(f"  ✅ {label} ({size_kb}KB, V8.0 branded, syntax OK)")
        ok += 1
    elif syntax_ok and not has_v8:
        print(f"  ⚠️  {label} ({size_kb}KB, syntax OK but V8.0 branding missing)")
        ok += 1
    else:
        print(f"  ❌ {label}: SYNTAX ERROR — {result.stderr[:80]}")
        fail += 1

print(f"\n  Apps: {ok} ready / {fail} failed / {ok+fail} total")
PYEOF

echo ""

# ── SECTION 9: DISK & RESOURCE STATUS ──────────────────────────────
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  [9] SYSTEM RESOURCES"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

DISK=$(df -h /opt/titan 2>/dev/null | tail -1 | awk '{print "Used: "$3" / "$2" ("$5")"}')
MEM=$(free -h | grep Mem | awk '{print "Used: "$3" / "$2}')
UPTIME=$(uptime -p 2>/dev/null || uptime)
PYTHON_VER=$(python3 --version 2>&1)
CORE_COUNT=$(ls /opt/titan/core/*.py 2>/dev/null | wc -l)
APPS_COUNT=$(ls /opt/titan/apps/*.py 2>/dev/null | wc -l)

log_info "Disk: $DISK"
log_info "Memory: $MEM"
log_info "Uptime: $UPTIME"
log_info "Python: $PYTHON_VER"
log_info "Core modules: $CORE_COUNT | App modules: $APPS_COUNT"

# Check pip packages needed by dev hub
python3 -c "import requests" 2>/dev/null && log_pass "requests: installed" || log_fail "requests: MISSING (pip install requests)"
python3 -c "import flask" 2>/dev/null && log_pass "flask: installed" || log_warn "flask: not installed (needed for API)"
python3 -c "import PyQt6" 2>/dev/null && log_pass "PyQt6: installed" || log_warn "PyQt6: not installed (needed for GUI apps)"
python3 -c "import openai" 2>/dev/null && log_pass "openai SDK: installed" || log_warn "openai SDK: not installed (optional)"
python3 -c "import anthropic" 2>/dev/null && log_pass "anthropic SDK: installed" || log_warn "anthropic SDK: not installed (optional)"

echo ""

# ── FINAL REPORT ───────────────────────────────────────────────────
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  FINAL READINESS REPORT                                      ║"
echo "╠══════════════════════════════════════════════════════════════╣"
printf "║  ✅ PASSED:  %-3s                                            ║\n" "$PASS"
printf "║  ❌ FAILED:  %-3s                                            ║\n" "$FAIL"
printf "║  ⚠️  WARNINGS: %-3s                                           ║\n" "$WARN"
echo "╠══════════════════════════════════════════════════════════════╣"

TOTAL=$((PASS+FAIL+WARN))
if [ "$FAIL" -eq 0 ]; then
    echo "║  STATUS: 🟢 OPERATIONAL — Dev Hub is ready                   ║"
elif [ "$FAIL" -le 2 ]; then
    echo "║  STATUS: 🟡 MOSTLY READY — Minor issues, check FAILs above   ║"
else
    echo "║  STATUS: 🔴 NOT READY — Multiple failures, action required   ║"
fi
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
