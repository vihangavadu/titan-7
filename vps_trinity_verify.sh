#!/bin/bash
cd /opt/titan

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  TITAN V7.5 — TRINITY APP FINAL VERIFICATION                        ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"

# Recompile
python3 -m compileall -q -f apps/ core/ 2>/dev/null

# Syntax check
echo ""
echo "═══ SYNTAX CHECK ═══"
for app in app_genesis app_cerberus app_kyc app_unified; do
    python3 -c "import py_compile; py_compile.compile('apps/${app}.py', doraise=True)" 2>&1 && echo "  ✅ ${app}.py" || echo "  ❌ ${app}.py SYNTAX ERROR"
done

# Line counts
echo ""
echo "═══ LINE COUNTS ═══"
for app in app_unified app_genesis app_cerberus app_kyc; do
    echo "  ${app}.py: $(wc -l < apps/${app}.py) lines"
done

# Per-app feature verification
echo ""
echo "═══ APP_GENESIS FEATURES ═══"
python3 - <<'PYEOF'
with open("apps/app_genesis.py") as f:
    c = f.read()
checks = {
    "Profile generation": "forge_profile" in c,
    "Target presets import": "target_presets" in c,
    "Browser launch": "launch_browser" in c,
    "Advanced profiles": "AdvancedProfile" in c or "advanced_profile" in c,
    "Dark theme": "enterprise_theme" in c or "setStyleSheet" in c,
    "Status bar": "statusBar" in c,
    "Progress bar": "QProgressBar" in c,
    "Profile history tab": "History" in c and "addTab" in c,
    "Profile inspector tab": "Inspector" in c,
    "Batch synthesis tab": "Batch" in c,
    "AI Audit tab": "AI Audit" in c or "ai_audit" in c,
    "AI profile audit": "_run_ai_audit" in c,
    "Fingerprint inject": "_inject_fingerprint" in c,
    "AI import": "ai_intelligence_engine" in c,
    "V7.5 version": "V7.5" in c,
    "Quick forge": "quick_forge" in c,
    "Export profile": "export" in c.lower(),
    "Delete profile": "delete" in c.lower(),
}
present = sum(1 for v in checks.values() if v)
for k, v in sorted(checks.items()):
    print(f"  {'✅' if v else '❌'} {k}")
print(f"  Score: {present}/{len(checks)} ({present/len(checks)*100:.0f}%)")
PYEOF

echo ""
echo "═══ APP_CERBERUS FEATURES ═══"
python3 - <<'PYEOF'
with open("apps/app_cerberus.py") as f:
    c = f.read()
checks = {
    "Card validation": "validate_card" in c,
    "BIN lookup": "_lookup_bin" in c,
    "BIN scoring": "score_bin" in c or "_score_bin" in c,
    "AVS check": "check_avs" in c or "avs" in c.lower(),
    "Target database": "_load_target_database" in c,
    "Target filtering": "_filter_targets" in c,
    "Discovery engine": "discovery" in c.lower(),
    "OSINT generation": "osint" in c.lower(),
    "MaxDrain planner": "MaxDrain" in c or "drain" in c.lower(),
    "Card quality grader": "CardQualityGrader" in c or "_grade_card" in c,
    "Geo match checker": "geo" in c.lower(),
    "Bulk validation": "bulk_validate" in c,
    "Dark theme": "enterprise_theme" in c or "apply_dark_theme" in c,
    "Tabs": "QTabWidget" in c,
    "AI Intelligence tab": "AI Intel" in c or "ai_tab" in c,
    "AI BIN analysis": "_ai_analyze_bin" in c,
    "AI target recon": "_ai_recon_target" in c,
    "AI 3DS strategy": "_ai_3ds_advise" in c,
    "Ghost Motor params": "forter_safe" in c.lower() or "get_forter_safe" in c,
    "Warmup pattern": "warmup_pattern" in c or "get_warmup" in c,
    "AI status": "_show_ai_status" in c,
    "AI import": "ai_intelligence_engine" in c,
    "TLS parrot import": "tls_parrot" in c,
    "Ghost motor import": "ghost_motor" in c,
    "V7.5 version": "V7.5" in c,
}
present = sum(1 for v in checks.values() if v)
for k, v in sorted(checks.items()):
    print(f"  {'✅' if v else '❌'} {k}")
print(f"  Score: {present}/{len(checks)} ({present/len(checks)*100:.0f}%)")
PYEOF

echo ""
echo "═══ APP_KYC FEATURES ═══"
python3 - <<'PYEOF'
with open("apps/app_kyc.py") as f:
    c = f.read()
checks = {
    "Face reenactment": "reenact" in c.lower() or "selfie" in c.lower(),
    "Virtual camera": "camera" in c.lower(),
    "Voice synthesis": "voice" in c.lower(),
    "Liveness detection": "liveness" in c.lower() or "blink" in c.lower(),
    "Mobile activity": "mobile" in c.lower() and "activity" in c.lower(),
    "Document generation": "document" in c.lower(),
    "Waydroid integration": "waydroid" in c.lower(),
    "Cognitive core import": "cognitive_core" in c,
    "AI import": "ai_intelligence_engine" in c,
    "Ghost motor import": "ghost_motor" in c,
    "Stream controls": "start_stream" in c,
    "Dark theme": "enterprise_theme" in c or "apply_dark_theme" in c,
    "Tabs": "QTabWidget" in c,
    "Voice tab": "voice" in c.lower() and "tab" in c.lower(),
    "Document tab": "document_tab" in c or "Document" in c,
    "Mobile tab": "mobile_tab" in c or "Mobile" in c,
    "V7.5 version": "V7.5" in c,
    "KYC enhanced": "kyc_enhanced" in c,
    "KYC voice engine": "kyc_voice_engine" in c,
}
present = sum(1 for v in checks.values() if v)
for k, v in sorted(checks.items()):
    print(f"  {'✅' if v else '❌'} {k}")
print(f"  Score: {present}/{len(checks)} ({present/len(checks)*100:.0f}%)")
PYEOF

# Tab counts per app
echo ""
echo "═══ TAB COUNTS ═══"
for app in app_genesis app_cerberus app_kyc app_unified; do
    tabs=$(grep -c "addTab" apps/${app}.py)
    buttons=$(grep -c "QPushButton" apps/${app}.py)
    methods=$(grep -c "def " apps/${app}.py)
    echo "  ${app}: $tabs tabs, $buttons buttons, $methods methods"
done

# Import test
echo ""
echo "═══ IMPORT TEST ═══"
python3 -c "
import sys; sys.path.insert(0,'core'); sys.path.insert(0,'apps')
for mod in ['ai_intelligence_engine','tls_parrot','ghost_motor_v6','fingerprint_injector','cognitive_core','target_presets']:
    try:
        __import__(mod)
        print(f'  ✅ {mod}')
    except Exception as e:
        print(f'  ❌ {mod}: {e}')
"

# AI smoke test
echo ""
echo "═══ AI SMOKE TEST ═══"
cd /opt/titan && python3 -c "
import sys; sys.path.insert(0,'core')
from ai_intelligence_engine import analyze_bin, recon_target, get_ai_status
s = get_ai_status()
print(f'  AI: {\"ONLINE\" if s[\"available\"] else \"OFFLINE\"} ({len(s[\"features\"])} features)')
b = analyze_bin('421783','eneba.com',150)
print(f'  BIN 421783: score={b.ai_score}/100 risk={b.risk_level.value}')
t = recon_target('eneba.com')
print(f'  eneba.com: fraud={t.fraud_engine_guess} 3ds={t.three_ds_probability:.0%}')
" 2>&1 || echo "  ⚠️ AI test failed"

echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  TRINITY VERIFICATION COMPLETE                                       ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
