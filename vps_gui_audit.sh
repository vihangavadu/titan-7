#!/bin/bash
# TITAN V7.5 — GUI/UX/Trinity Apps Deep Audit
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  TITAN V7.5 — GUI / UX / TRINITY APPS DEEP AUDIT                    ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"

# ─── 1. APP FILES ON VPS ─────────────────────────────────────────────────
echo ""
echo "═══ [1] APP FILES ═══"
for app in app_unified app_genesis app_cerberus app_kyc; do
    f="/opt/titan/apps/${app}.py"
    if [ -f "$f" ]; then
        lines=$(wc -l < "$f")
        size=$(du -h "$f" | cut -f1)
        echo "  ✅ ${app}.py — $lines lines ($size)"
    else
        echo "  ❌ ${app}.py — MISSING"
    fi
done
echo ""
echo "  Other app files:"
ls -lh /opt/titan/apps/*.py 2>/dev/null | awk '{print "    "$NF, $5}'

# ─── 2. TABS IN APP_UNIFIED ──────────────────────────────────────────────
echo ""
echo "═══ [2] TABS IN app_unified.py ═══"
grep -n "addTab\|QTabWidget\|tab_widget\|Tab(" /opt/titan/apps/app_unified.py | head -30
echo ""
echo "  Tab names found:"
grep -oP "addTab\([^,]+,\s*['\"]([^'\"]+)['\"]" /opt/titan/apps/app_unified.py | sed 's/addTab.*"/  /' | sed "s/addTab.*'/  /"

# ─── 3. CLASS STRUCTURE ──────────────────────────────────────────────────
echo ""
echo "═══ [3] CLASS STRUCTURE ═══"
echo "  app_unified.py classes:"
grep -n "^class " /opt/titan/apps/app_unified.py
echo ""
echo "  app_genesis.py classes:"
grep -n "^class " /opt/titan/apps/app_genesis.py
echo ""
echo "  app_cerberus.py classes:"
grep -n "^class " /opt/titan/apps/app_cerberus.py
echo ""
echo "  app_kyc.py classes:"
grep -n "^class " /opt/titan/apps/app_kyc.py

# ─── 4. AI INTEGRATION CHECK ─────────────────────────────────────────────
echo ""
echo "═══ [4] AI INTEGRATION IN APPS ═══"
for app in app_unified app_genesis app_cerberus app_kyc; do
    f="/opt/titan/apps/${app}.py"
    echo "  ${app}.py:"
    ai_imports=$(grep -c "ai_intelligence_engine\|ollama_bridge\|plan_operation\|analyze_bin\|recon_target\|advise_3ds\|tune_behavior\|audit_profile" "$f" 2>/dev/null)
    echo "    AI references: $ai_imports"
    ollama_refs=$(grep -c "ollama\|Ollama\|OLLAMA\|LLM\|llm" "$f" 2>/dev/null)
    echo "    Ollama/LLM refs: $ollama_refs"
done

# ─── 5. FEATURE INVENTORY ────────────────────────────────────────────────
echo ""
echo "═══ [5] FEATURE INVENTORY — app_unified.py ═══"
echo "  Methods/functions:"
grep -c "def " /opt/titan/apps/app_unified.py | xargs echo "    Total methods:"
echo ""
echo "  Key features (by method name):"
grep "def " /opt/titan/apps/app_unified.py | grep -iE "genesis|cerberus|kyc|forensic|ai|intel|profile|browser|launch|scan|monitor|bin|target|3ds|preflight|ghost|motor" | head -30

# ─── 6. FEATURE INVENTORY — OTHER APPS ───────────────────────────────────
echo ""
echo "═══ [6] FEATURE INVENTORY — Other Apps ═══"
for app in app_genesis app_cerberus app_kyc; do
    f="/opt/titan/apps/${app}.py"
    echo "  ${app}.py:"
    grep -c "def " "$f" | xargs echo "    Methods:"
    echo "    Key features:"
    grep "def " "$f" | grep -iE "start|run|launch|generate|scan|validate|check|score|analyze|ai|ollama|bin|target|profile|browser" | head -10
    echo ""
done

# ─── 7. UI WIDGETS CHECK ─────────────────────────────────────────────────
echo ""
echo "═══ [7] UI WIDGETS IN app_unified.py ═══"
echo "  QTabWidget:"
grep -c "QTabWidget" /opt/titan/apps/app_unified.py
echo "  QPushButton:"
grep -c "QPushButton" /opt/titan/apps/app_unified.py
echo "  QLabel:"
grep -c "QLabel" /opt/titan/apps/app_unified.py
echo "  QTextEdit/QPlainTextEdit:"
grep -c "QTextEdit\|QPlainTextEdit" /opt/titan/apps/app_unified.py
echo "  QTableWidget:"
grep -c "QTableWidget" /opt/titan/apps/app_unified.py
echo "  QComboBox:"
grep -c "QComboBox" /opt/titan/apps/app_unified.py
echo "  QLineEdit:"
grep -c "QLineEdit" /opt/titan/apps/app_unified.py
echo "  QProgressBar:"
grep -c "QProgressBar" /opt/titan/apps/app_unified.py
echo "  QGroupBox:"
grep -c "QGroupBox" /opt/titan/apps/app_unified.py
echo "  QStatusBar:"
grep -c "QStatusBar\|statusBar" /opt/titan/apps/app_unified.py

# ─── 8. FORENSIC TAB CHECK ───────────────────────────────────────────────
echo ""
echo "═══ [8] FORENSIC TAB ═══"
grep -n "FORENSIC\|forensic_tab\|forensic_widget\|ForensicMonitor" /opt/titan/apps/app_unified.py | head -10

# ─── 9. VERSION STRINGS ──────────────────────────────────────────────────
echo ""
echo "═══ [9] VERSION STRINGS ═══"
for app in app_unified app_genesis app_cerberus app_kyc; do
    f="/opt/titan/apps/${app}.py"
    ver=$(grep -oP "__version__\s*=\s*['\"]([^'\"]+)" "$f" 2>/dev/null | head -1)
    title=$(grep -oP "setWindowTitle\(['\"]([^'\"]+)" "$f" 2>/dev/null | head -1)
    echo "  ${app}: version=$ver title=$title"
done

# ─── 10. MISSING FEATURES SCAN ───────────────────────────────────────────
echo ""
echo "═══ [10] MISSING FEATURES SCAN ═══"
cd /opt/titan && python3 - <<'PYEOF'
import sys
sys.path.insert(0, "core")
sys.path.insert(0, "apps")

missing = []
present = []

# Check app_unified for key V7.5 features
with open("apps/app_unified.py") as f:
    content = f.read()

checks = {
    "AI Intelligence Tab": "ai_intelligence" in content.lower() or "AI Intel" in content or "ai_tab" in content,
    "AI BIN Analysis button": "analyze_bin" in content or "ai_bin" in content.lower(),
    "AI Target Recon button": "recon_target" in content or "ai_target" in content.lower(),
    "AI 3DS Strategy": "advise_3ds" in content or "3ds_strategy" in content.lower() or "3DS" in content,
    "AI Operation Planner": "plan_operation" in content or "operation_plan" in content.lower(),
    "AI Behavioral Tuning": "tune_behavior" in content or "behavioral" in content.lower(),
    "AI Profile Audit": "audit_profile" in content or "profile_audit" in content.lower(),
    "Forensic Monitor Tab": "FORENSIC" in content or "forensic_tab" in content,
    "Forensic Widget": "forensic_widget" in content or "ForensicWidget" in content,
    "Ghost Motor Controls": "ghost_motor" in content.lower() or "Ghost Motor" in content,
    "TLS Parrot Status": "tls_parrot" in content.lower() or "TLS" in content,
    "Profile Generator": "genesis" in content.lower() or "profile_gen" in content.lower(),
    "BIN Scoring": "bin_scor" in content.lower() or "BINScor" in content,
    "Target Intelligence": "target_intel" in content.lower() or "TargetIntel" in content,
    "Preflight Validator": "preflight" in content.lower() or "PreFlight" in content,
    "Browser Launch": "launch_browser" in content.lower() or "camoufox" in content.lower(),
    "Proxy Config": "proxy" in content.lower(),
    "Dark Theme": "dark" in content.lower() or "palette" in content.lower() or "QPalette" in content,
    "Status Bar": "statusBar" in content or "status_bar" in content,
    "Real-time Logs": "QTextEdit" in content or "log_output" in content.lower(),
}

for feature, found in checks.items():
    if found:
        present.append(feature)
    else:
        missing.append(feature)

print(f"  Present: {len(present)}/{len(checks)}")
for f in present:
    print(f"    ✅ {f}")
print(f"\n  Missing: {len(missing)}/{len(checks)}")
for f in missing:
    print(f"    ❌ {f}")
PYEOF

echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  GUI AUDIT COMPLETE                                                  ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
