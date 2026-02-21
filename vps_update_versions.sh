#!/bin/bash
# Update version strings on VPS apps + verify GUI

echo "═══ [1] Update version strings ═══"
# app_genesis.py
sed -i 's/TITAN V7.0.3/TITAN V7.5/g' /opt/titan/apps/app_genesis.py
echo "  app_genesis: $(grep 'setWindowTitle' /opt/titan/apps/app_genesis.py | head -1 | xargs)"

# app_kyc.py
sed -i 's/TITAN V7.0.3/TITAN V7.5/g' /opt/titan/apps/app_kyc.py
echo "  app_kyc: $(grep 'setWindowTitle' /opt/titan/apps/app_kyc.py | head -1 | xargs)"

# app_cerberus.py — update title
sed -i 's/TITAN V7.0.3/TITAN V7.5/g' /opt/titan/apps/app_cerberus.py 2>/dev/null
echo "  app_cerberus: $(grep 'setWindowTitle' /opt/titan/apps/app_cerberus.py | head -1 | xargs)"

# splash screen build string
sed -i 's/BUILD: 7.0.3-FINAL/BUILD: 7.5.0-SINGULARITY/g' /opt/titan/apps/app_unified.py
echo "  splash: $(grep 'BUILD:' /opt/titan/apps/app_unified.py | head -1 | xargs)"

echo ""
echo "═══ [2] Recompile bytecode ═══"
python3 -m compileall -q -f /opt/titan/apps/ 2>/dev/null
echo "  ✅ Apps recompiled"

echo ""
echo "═══ [3] Verify app_unified tabs ═══"
echo "  Main tabs:"
grep "main_tabs.addTab" /opt/titan/apps/app_unified.py | sed 's/.*addTab.*,/  /' | sed 's/)//'
echo ""
echo "  AI sub-tabs:"
grep "ai_tabs.addTab" /opt/titan/apps/app_unified.py | sed 's/.*addTab.*,/  /' | sed 's/)//'

echo ""
echo "═══ [4] Verify AI imports ═══"
cd /opt/titan && python3 -c "
import sys; sys.path.insert(0,'core'); sys.path.insert(0,'apps')
try:
    from ai_intelligence_engine import is_ai_available, get_ai_status
    s = get_ai_status()
    print(f'  AI Engine: {\"ONLINE\" if s[\"available\"] else \"OFFLINE\"}')
    print(f'  Features: {len(s[\"features\"])}')
except Exception as e:
    print(f'  Error: {e}')
try:
    from tls_parrot import TLSParrotEngine
    e = TLSParrotEngine()
    print(f'  TLS Parrot: {len(e.templates)} templates')
except Exception as e:
    print(f'  TLS Error: {e}')
"

echo ""
echo "═══ [5] Verify feature completeness ═══"
cd /opt/titan && python3 - <<'PYEOF'
import sys
sys.path.insert(0, "core")
sys.path.insert(0, "apps")

with open("apps/app_unified.py") as f:
    content = f.read()

checks = {
    "AI Intelligence Tab": "AI INTEL" in content,
    "AI BIN Analysis button": "ai_analyze_bin" in content or "_ai_analyze_bin" in content,
    "AI Target Recon button": "ai_recon_target" in content or "_ai_recon_target" in content,
    "AI Operation Planner": "ai_run_plan" in content or "_ai_run_plan" in content,
    "AI Behavioral Tuning": "ai_tune_behavior" in content or "_ai_tune_behavior" in content,
    "AI Profile Audit": "ai_audit_profile" in content or "_ai_audit_profile" in content,
    "AI 3DS Advisor": "ai_3ds_advise" in content or "_ai_3ds_advise" in content,
    "TLS Parrot Status": "ai_tls_status" in content or "_ai_tls_status" in content,
    "AI Status Panel": "ai_refresh_status" in content or "_ai_refresh_status" in content,
    "Forensic Monitor Tab": "FORENSIC" in content,
    "Forensic Widget": "forensic_widget" in content,
    "Ghost Motor Controls": "ghost_motor" in content.lower(),
    "Profile Generator": "genesis" in content.lower(),
    "BIN Scoring": "bin_scor" in content.lower() or "BINScor" in content,
    "Target Intelligence": "target_intel" in content.lower(),
    "Preflight Validator": "preflight" in content.lower(),
    "Browser Launch": "launch_browser" in content.lower(),
    "Proxy Config": "proxy" in content.lower(),
    "Dark Theme": "palette" in content.lower() or "QPalette" in content,
    "Status Bar": "statusBar" in content,
    "Real-time Logs": "QTextEdit" in content,
    "TX Monitor Tab": "TX MONITOR" in content,
    "Discovery Tab": "DISCOVERY" in content,
    "Non-VBV BINs": "Non-VBV" in content,
    "3DS Bypass Tab": "3DS Bypass" in content,
}

present = sum(1 for v in checks.values() if v)
total = len(checks)
print(f"  Feature Score: {present}/{total} ({present/total*100:.0f}%)")
print()
for feature, found in sorted(checks.items(), key=lambda x: x[1]):
    icon = "✅" if found else "❌"
    print(f"  {icon} {feature}")
PYEOF

echo ""
echo "═══ [6] App line counts ═══"
for app in app_unified app_genesis app_cerberus app_kyc; do
    lines=$(wc -l < /opt/titan/apps/${app}.py)
    echo "  ${app}.py: $lines lines"
done

echo ""
echo "═══ [7] Tab count summary ═══"
MAIN_TABS=$(grep -c "main_tabs.addTab" /opt/titan/apps/app_unified.py)
AI_TABS=$(grep -c "ai_tabs.addTab" /opt/titan/apps/app_unified.py)
INTEL_TABS=$(grep -c "intel_tabs.addTab" /opt/titan/apps/app_unified.py)
SHIELD_TABS=$(grep -c "shields_tabs.addTab" /opt/titan/apps/app_unified.py)
DISC_TABS=$(grep -c "disc_tabs.addTab" /opt/titan/apps/app_unified.py)
echo "  Main tabs: $MAIN_TABS"
echo "  AI sub-tabs: $AI_TABS"
echo "  Intelligence sub-tabs: $INTEL_TABS"
echo "  Shield sub-tabs: $SHIELD_TABS"
echo "  Discovery sub-tabs: $DISC_TABS"
echo "  TOTAL tabs: $((MAIN_TABS + AI_TABS + INTEL_TABS + SHIELD_TABS + DISC_TABS))"

echo ""
echo "═══ DONE ═══"
