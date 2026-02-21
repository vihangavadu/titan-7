#!/bin/bash
# TITAN V7.5 — Deep Audit: Genesis, Cerberus, KYC (app by app)
cd /opt/titan

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  TITAN V7.5 — TRINITY APP-BY-APP DEEP AUDIT                         ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"

########################################################################
# APP_GENESIS
########################################################################
echo ""
echo "┌──────────────────────────────────────────────────────────────────┐"
echo "│  APP_GENESIS.PY                                                  │"
echo "└──────────────────────────────────────────────────────────────────┘"
G="apps/app_genesis.py"
echo "  Lines: $(wc -l < $G)"
echo "  Version: $(grep -oP 'V7\.\d+\.?\d*' $G | head -1)"
echo "  Title: $(grep 'setWindowTitle' $G | head -1 | sed 's/.*setWindowTitle(//' | sed 's/).*//')"
echo ""
echo "  Classes:"
grep "^class " $G | sed 's/^/    /'
echo ""
echo "  Methods ($(grep -c 'def ' $G)):"
grep "def " $G | sed 's/^[[:space:]]*/    /'
echo ""
echo "  Imports:"
grep "^from \|^import " $G | sed 's/^/    /'
echo ""
echo "  Core module refs:"
for mod in genesis_core cerberus_core target_presets advanced_profile_generator ai_intelligence_engine tls_parrot ghost_motor_v6 fingerprint_injector ollama_bridge; do
    refs=$(grep -c "$mod" $G 2>/dev/null)
    [ "$refs" -gt 0 ] && echo "    ✅ $mod ($refs refs)" || echo "    ❌ $mod (0 refs)"
done
echo ""
echo "  UI Widgets:"
echo "    QPushButton: $(grep -c 'QPushButton' $G)"
echo "    QLabel: $(grep -c 'QLabel' $G)"
echo "    QTextEdit: $(grep -c 'QTextEdit' $G)"
echo "    QComboBox: $(grep -c 'QComboBox' $G)"
echo "    QLineEdit: $(grep -c 'QLineEdit' $G)"
echo "    QTabWidget: $(grep -c 'QTabWidget' $G)"
echo "    QProgressBar: $(grep -c 'QProgressBar' $G)"
echo "    QGroupBox: $(grep -c 'QGroupBox' $G)"
echo ""
echo "  Feature check:"
python3 - <<'PYEOF'
with open("apps/app_genesis.py") as f:
    c = f.read()
checks = {
    "Profile generation": "forge_profile" in c or "generate" in c.lower(),
    "Target presets": "target_preset" in c.lower() or "TARGET_PRESETS" in c,
    "Browser launch": "launch_browser" in c or "camoufox" in c.lower(),
    "Advanced profiles": "AdvancedProfile" in c or "advanced_profile" in c,
    "Dark theme": "QPalette" in c or "palette" in c.lower() or "setStyleSheet" in c,
    "Status bar": "statusBar" in c or "status_bar" in c,
    "Progress feedback": "QProgressBar" in c or "progress" in c.lower(),
    "Profile path output": "profile_path" in c or "output" in c.lower(),
    "Error handling": "except" in c,
    "V7.5 version": "V7.5" in c,
}
present = sum(1 for v in checks.values() if v)
for k, v in checks.items():
    print(f"    {'✅' if v else '❌'} {k}")
print(f"  Score: {present}/{len(checks)}")
PYEOF

########################################################################
# APP_CERBERUS
########################################################################
echo ""
echo "┌──────────────────────────────────────────────────────────────────┐"
echo "│  APP_CERBERUS.PY                                                 │"
echo "└──────────────────────────────────────────────────────────────────┘"
C="apps/app_cerberus.py"
echo "  Lines: $(wc -l < $C)"
echo "  Version: $(grep -oP 'V7\.\d+\.?\d*' $C | head -1)"
echo "  Title: $(grep 'setWindowTitle' $C | head -1 | sed 's/.*setWindowTitle(//' | sed 's/).*//')"
echo ""
echo "  Classes:"
grep "^class " $C | sed 's/^/    /'
echo ""
echo "  Methods ($(grep -c 'def ' $C)):"
grep "def " $C | sed 's/^[[:space:]]*/    /'
echo ""
echo "  Imports:"
grep "^from \|^import " $C | sed 's/^/    /'
echo ""
echo "  Tabs:"
grep "addTab" $C | sed 's/.*addTab.*,/    /' | sed 's/)//'
echo ""
echo "  Core module refs:"
for mod in cerberus_core cerberus_enhanced target_presets three_ds_strategy target_discovery target_intelligence ai_intelligence_engine ghost_motor_v6 tls_parrot ollama_bridge score_bin BINScoringEngine; do
    refs=$(grep -c "$mod" $C 2>/dev/null)
    [ "$refs" -gt 0 ] && echo "    ✅ $mod ($refs refs)" || echo "    ❌ $mod (0 refs)"
done
echo ""
echo "  UI Widgets:"
echo "    QPushButton: $(grep -c 'QPushButton' $C)"
echo "    QLabel: $(grep -c 'QLabel' $C)"
echo "    QTextEdit: $(grep -c 'QTextEdit' $C)"
echo "    QTabWidget: $(grep -c 'QTabWidget' $C)"
echo "    QTableWidget: $(grep -c 'QTableWidget' $C)"
echo "    QComboBox: $(grep -c 'QComboBox' $C)"
echo "    QLineEdit: $(grep -c 'QLineEdit' $C)"
echo "    QGroupBox: $(grep -c 'QGroupBox' $C)"
echo ""
echo "  Feature check:"
python3 - <<'PYEOF'
with open("apps/app_cerberus.py") as f:
    c = f.read()
checks = {
    "BIN lookup": "_lookup_bin" in c or "lookup_bin" in c,
    "BIN scoring": "score_bin" in c or "_score_bin" in c,
    "Card validation": "validate" in c.lower(),
    "AVS check": "avs" in c.lower() or "check_avs" in c,
    "Target database": "target" in c.lower() and "database" in c.lower(),
    "Target filtering": "_filter_targets" in c,
    "Discovery engine": "discovery" in c.lower(),
    "OSINT generation": "osint" in c.lower(),
    "MaxDrain planner": "MaxDrain" in c or "drain" in c.lower(),
    "3DS intelligence": "3ds" in c.lower() or "three_ds" in c,
    "Dark theme": "QPalette" in c or "setStyleSheet" in c,
    "Tabs": "QTabWidget" in c,
    "Error handling": "except" in c,
    "V7.5 version": "V7.5" in c,
}
present = sum(1 for v in checks.values() if v)
for k, v in checks.items():
    print(f"    {'✅' if v else '❌'} {k}")
print(f"  Score: {present}/{len(checks)}")
PYEOF

########################################################################
# APP_KYC
########################################################################
echo ""
echo "┌──────────────────────────────────────────────────────────────────┐"
echo "│  APP_KYC.PY                                                      │"
echo "└──────────────────────────────────────────────────────────────────┘"
K="apps/app_kyc.py"
echo "  Lines: $(wc -l < $K)"
echo "  Version: $(grep -oP 'V7\.\d+\.?\d*' $K | head -1)"
echo "  Title: $(grep 'setWindowTitle' $K | head -1 | sed 's/.*setWindowTitle(//' | sed 's/).*//')"
echo ""
echo "  Classes:"
grep "^class " $K | sed 's/^/    /'
echo ""
echo "  Methods ($(grep -c 'def ' $K)):"
grep "def " $K | sed 's/^[[:space:]]*/    /'
echo ""
echo "  Imports:"
grep "^from \|^import " $K | sed 's/^/    /'
echo ""
echo "  Core module refs:"
for mod in kyc_core kyc_enhanced kyc_voice_engine cognitive_core ai_intelligence_engine waydroid_sync ollama_bridge ghost_motor_v6; do
    refs=$(grep -c "$mod" $K 2>/dev/null)
    [ "$refs" -gt 0 ] && echo "    ✅ $mod ($refs refs)" || echo "    ❌ $mod (0 refs)"
done
echo ""
echo "  UI Widgets:"
echo "    QPushButton: $(grep -c 'QPushButton' $K)"
echo "    QLabel: $(grep -c 'QLabel' $K)"
echo "    QTextEdit: $(grep -c 'QTextEdit' $K)"
echo "    QComboBox: $(grep -c 'QComboBox' $K)"
echo "    QLineEdit: $(grep -c 'QLineEdit' $K)"
echo "    QTabWidget: $(grep -c 'QTabWidget' $K)"
echo "    QGroupBox: $(grep -c 'QGroupBox' $K)"
echo "    QSlider: $(grep -c 'QSlider' $K)"
echo ""
echo "  Feature check:"
python3 - <<'PYEOF'
with open("apps/app_kyc.py") as f:
    c = f.read()
checks = {
    "Face reenactment": "reenact" in c.lower() or "selfie" in c.lower(),
    "Virtual camera": "virtual_cam" in c.lower() or "v4l2" in c.lower() or "camera" in c.lower(),
    "Voice synthesis": "voice" in c.lower(),
    "Liveness detection": "liveness" in c.lower() or "blink" in c.lower(),
    "Mobile activity sim": "mobile" in c.lower() and "activity" in c.lower(),
    "Document generation": "document" in c.lower() or "id_card" in c.lower(),
    "Waydroid integration": "waydroid" in c.lower(),
    "Cognitive core": "cognitive" in c.lower(),
    "Stream controls": "start_stream" in c or "stop_stream" in c,
    "Dark theme": "QPalette" in c or "setStyleSheet" in c,
    "Tabs": "QTabWidget" in c,
    "Error handling": "except" in c,
    "V7.5 version": "V7.5" in c,
}
present = sum(1 for v in checks.values() if v)
for k, v in checks.items():
    print(f"    {'✅' if v else '❌'} {k}")
print(f"  Score: {present}/{len(checks)}")
PYEOF

########################################################################
# CROSS-APP GAPS
########################################################################
echo ""
echo "┌──────────────────────────────────────────────────────────────────┐"
echo "│  CROSS-APP GAP ANALYSIS                                          │"
echo "└──────────────────────────────────────────────────────────────────┘"
echo ""
echo "  Modules used ONLY in app_unified but NOT in standalone apps:"
for mod in ai_intelligence_engine tls_parrot ghost_motor_v6 fingerprint_injector canvas_subpixel_shim cpuid_rdtsc_shield windows_font_provisioner immutable_os ollama_bridge; do
    in_gen=$(grep -c "$mod" apps/app_genesis.py 2>/dev/null)
    in_cer=$(grep -c "$mod" apps/app_cerberus.py 2>/dev/null)
    in_kyc=$(grep -c "$mod" apps/app_kyc.py 2>/dev/null)
    in_uni=$(grep -c "$mod" apps/app_unified.py 2>/dev/null)
    total=$((in_gen + in_cer + in_kyc))
    if [ "$total" -eq 0 ] && [ "$in_uni" -gt 0 ]; then
        echo "    ⚠️  $mod: unified=$in_uni, genesis=$in_gen, cerberus=$in_cer, kyc=$in_kyc"
    fi
done

echo ""
echo "  Syntax check all apps:"
for app in app_unified app_genesis app_cerberus app_kyc; do
    python3 -c "import py_compile; py_compile.compile('apps/${app}.py', doraise=True)" 2>&1 && echo "    ✅ ${app}.py" || echo "    ❌ ${app}.py SYNTAX ERROR"
done

echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  TRINITY AUDIT COMPLETE                                              ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
