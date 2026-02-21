#!/bin/bash
# Final verification after all fixes
cd /opt/titan

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  TITAN V7.5 — FINAL FEATURE VERIFICATION                            ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"

# Fix ollama_bridge version
sed -i 's/V7.0 SINGULARITY/V7.5 SINGULARITY/' core/ollama_bridge.py 2>/dev/null

# Recompile
python3 -m compileall -q -f apps/ core/ 2>/dev/null

echo ""
echo "═══ [1] APP LINE COUNTS ═══"
for app in app_unified app_genesis app_cerberus app_kyc; do
    echo "  ${app}.py: $(wc -l < apps/${app}.py) lines"
done

echo ""
echo "═══ [2] MAIN TABS ═══"
grep "main_tabs.addTab" apps/app_unified.py | sed 's/.*addTab.*,/  /' | sed 's/)//'

echo ""
echo "═══ [3] ALL SUB-TABS ═══"
echo "  AI Intel:"
grep "ai_tabs.addTab" apps/app_unified.py | sed 's/.*addTab.*,/    /' | sed 's/)//'
echo "  Intelligence:"
grep "intel_tabs.addTab" apps/app_unified.py | sed 's/.*addTab.*,/    /' | sed 's/)//'
echo "  Shields:"
grep "shields_tabs.addTab" apps/app_unified.py | sed 's/.*addTab.*,/    /' | sed 's/)//'
echo "  Discovery:"
grep "disc_tabs.addTab" apps/app_unified.py | sed 's/.*addTab.*,/    /' | sed 's/)//'

echo ""
echo "═══ [4] BUTTON COUNT ═══"
BUTTONS=$(grep -c "QPushButton" apps/app_unified.py)
CONNECTED=$(grep -c "clicked.connect" apps/app_unified.py)
echo "  Buttons: $BUTTONS"
echo "  Connected: $CONNECTED"

echo ""
echo "═══ [5] FULL FEATURE CHECK ═══"
python3 - <<'PYEOF'
import sys
sys.path.insert(0, "core")
sys.path.insert(0, "apps")

with open("apps/app_unified.py") as f:
    content = f.read()

checks = {
    # Main tabs
    "OPERATION tab": '"OPERATION"' in content,
    "INTELLIGENCE tab": '"INTELLIGENCE"' in content,
    "SHIELDS tab": '"SHIELDS"' in content,
    "KYC tab": '"KYC"' in content,
    "HEALTH tab": '"HEALTH"' in content,
    "FORENSIC tab": '"FORENSIC"' in content,
    "TX MONITOR tab": '"TX MONITOR"' in content,
    "DISCOVERY tab": '"DISCOVERY"' in content,
    "AI INTEL tab": "AI INTEL" in content,
    # AI sub-tabs
    "AI Op Planner": "_ai_run_plan" in content,
    "AI BIN Analysis": "_ai_analyze_bin" in content,
    "AI Target Recon": "_ai_recon_target" in content,
    "AI 3DS Advisor": "_ai_3ds_advise" in content,
    "AI Behavioral Tuning": "_ai_tune_behavior" in content,
    "AI Profile Audit": "_ai_audit_profile" in content,
    "AI TLS Parrot": "_ai_tls_status" in content,
    "AI Status Panel": "_ai_refresh_status" in content,
    # V7.5 Shield buttons
    "Canvas Shim button": "_run_canvas_shim" in content,
    "CPUID Shield button": "_run_cpuid_shield" in content,
    "Font Provisioner button": "_run_font_provisioner" in content,
    "Immutable OS button": "_run_immutable_os" in content,
    "Ghost Motor button": "_run_ghost_motor_test" in content,
    "Fingerprint Inject button": "_run_fingerprint_inject" in content,
    "Run All Shields button": "_run_all_shields" in content,
    # Existing features
    "Font Purge": "_run_font_purge" in content,
    "Audio Harden": "_run_audio_harden" in content,
    "Timezone Sync": "_run_tz_enforce" in content,
    "Kill Switch": "_arm_kill_switch" in content,
    "Preflight Validator": "preflight" in content.lower(),
    "Browser Launch": "launch_browser" in content,
    "Proxy Config": "proxy" in content.lower(),
    "Dark Theme": "QPalette" in content or "palette" in content.lower(),
    "Status Bar": "statusBar" in content,
    "Real-time Logs": "QTextEdit" in content,
    "3DS Bypass": "3DS Bypass" in content,
    "Non-VBV BINs": "Non-VBV" in content,
    "Target Intelligence": "target_intel" in content.lower(),
    "BIN Scoring": "score_bin" in content or "BINScor" in content,
    "TX Monitor": "_refresh_tx_monitor" in content,
    "Forensic Widget": "forensic_widget" in content,
    "OSINT Verifier": "OSINTVerifier" in content,
    "Card Quality Grader": "CardQualityGrader" in content,
    "Purchase History": "purchase_hist" in content.lower() or "Purchase Hist" in content,
}

present = sum(1 for v in checks.values() if v)
total = len(checks)
pct = present / total * 100

print(f"  Score: {present}/{total} ({pct:.0f}%)")
print()
missing = []
for feature, found in sorted(checks.items()):
    icon = "✅" if found else "❌"
    print(f"  {icon} {feature}")
    if not found:
        missing.append(feature)

if missing:
    print(f"\n  MISSING ({len(missing)}):")
    for m in missing:
        print(f"    ❌ {m}")
else:
    print(f"\n  🎯 100% FEATURE COVERAGE — ALL FEATURES PRESENT")
PYEOF

echo ""
echo "═══ [6] VERSION CONSISTENCY ═══"
for f in apps/app_unified.py apps/app_genesis.py apps/app_cerberus.py apps/app_kyc.py; do
    ver=$(grep -oP "V7\.\d+\.?\d*" "$f" 2>/dev/null | head -1)
    echo "  $(basename $f): $ver"
done
for f in core/ollama_bridge.py core/ai_intelligence_engine.py core/tls_parrot.py core/hardware_shield_v6.c core/network_shield_v6.c; do
    ver=$(grep -oP '7\.\d+\.\d+' "$f" 2>/dev/null | head -1)
    echo "  $(basename $f): V$ver"
done

echo ""
echo "═══ [7] SYNTAX CHECK ═══"
python3 -c "import py_compile; py_compile.compile('apps/app_unified.py', doraise=True)" 2>&1 && echo "  ✅ app_unified.py syntax OK" || echo "  ❌ SYNTAX ERROR"

echo ""
echo "═══ [8] CORE MODULE WIRING ═══"
TOTAL_CORE=$(find core/ -maxdepth 1 -name "*.py" -type f | wc -l)
WIRED=0
UNWIRED=""
for mod in $(find core/ -maxdepth 1 -name "*.py" -type f | sort); do
    modname=$(basename "$mod" .py)
    [[ "$modname" == "__"* ]] && continue
    refs=$(grep -rl "$modname" apps/*.py 2>/dev/null | wc -l)
    if [ "$refs" -gt 0 ]; then
        WIRED=$((WIRED + 1))
    else
        UNWIRED="$UNWIRED $modname"
    fi
done
echo "  Core modules: $TOTAL_CORE"
echo "  Wired to GUI: $WIRED"
echo "  Not in GUI: $(echo $UNWIRED | wc -w) (backend-only modules)"
echo "  Unwired:$UNWIRED"

echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  VERIFICATION COMPLETE                                               ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
