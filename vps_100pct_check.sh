#!/bin/bash
cd /opt/titan

# Fix ollama_bridge version
sed -i 's/"7.0.0"/"7.5.0"/g' core/ollama_bridge.py 2>/dev/null

# Recompile
python3 -m compileall -q -f apps/ core/ 2>/dev/null

# Syntax check
python3 -c "import py_compile; py_compile.compile('apps/app_unified.py', doraise=True)" 2>&1 && echo "SYNTAX: OK" || echo "SYNTAX: FAIL"

# Feature check
python3 - <<'PYEOF'
with open("apps/app_unified.py") as f:
    content = f.read()

checks = {
    "OPERATION tab": '"OPERATION"' in content,
    "INTELLIGENCE tab": '"INTELLIGENCE"' in content,
    "SHIELDS tab": '"SHIELDS"' in content,
    "KYC tab": '"KYC"' in content,
    "HEALTH tab": '"HEALTH"' in content,
    "FORENSIC tab": '"FORENSIC"' in content,
    "TX MONITOR tab": '"TX MONITOR"' in content,
    "DISCOVERY tab": '"DISCOVERY"' in content,
    "AI INTEL tab": "AI INTEL" in content,
    "AI Op Planner": "_ai_run_plan" in content,
    "AI BIN Analysis": "_ai_analyze_bin" in content,
    "AI Target Recon": "_ai_recon_target" in content,
    "AI 3DS Advisor": "_ai_3ds_advise" in content,
    "AI Behavioral Tuning": "_ai_tune_behavior" in content,
    "AI Profile Audit": "_ai_audit_profile" in content,
    "AI TLS Parrot": "_ai_tls_status" in content,
    "AI Status Panel": "_ai_refresh_status" in content,
    "Canvas Shim": "_run_canvas_shim" in content,
    "CPUID Shield": "_run_cpuid_shield" in content,
    "Font Provisioner": "_run_font_provisioner" in content,
    "Immutable OS": "_run_immutable_os" in content,
    "Ghost Motor": "_run_ghost_motor_test" in content,
    "Fingerprint Inject": "_run_fingerprint_inject" in content,
    "Run All Shields": "_run_all_shields" in content,
    "Font Purge": "_run_font_purge" in content,
    "Audio Harden": "_run_audio_harden" in content,
    "Timezone Sync": "_run_tz_enforce" in content,
    "Kill Switch": "_arm_kill_switch" in content,
    "Preflight": "preflight" in content.lower(),
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
    "Purchase History": "Purchase Hist" in content,
}

present = sum(1 for v in checks.values() if v)
total = len(checks)
missing = [k for k, v in checks.items() if not v]

print(f"FEATURES: {present}/{total} ({present/total*100:.0f}%)")
if missing:
    for m in missing:
        print(f"  MISSING: {m}")
else:
    print("  ALL FEATURES PRESENT")

# Version check
import subprocess
print()
for f in ["core/ollama_bridge.py", "core/ai_intelligence_engine.py", "core/tls_parrot.py"]:
    import re
    with open(f) as fh:
        ver = re.search(r'7\.\d+\.\d+', fh.read())
        print(f"  {f.split('/')[-1]}: V{ver.group() if ver else '?'}")
PYEOF

echo ""
echo "TABS: $(grep -c 'main_tabs.addTab' apps/app_unified.py) main + $(grep -c 'ai_tabs.addTab' apps/app_unified.py) AI + $(grep -c 'intel_tabs.addTab' apps/app_unified.py) intel + $(grep -c 'shields_tabs.addTab' apps/app_unified.py) shields + $(grep -c 'disc_tabs.addTab' apps/app_unified.py) discovery"
echo "BUTTONS: $(grep -c 'QPushButton' apps/app_unified.py) total, $(grep -c 'clicked.connect' apps/app_unified.py) connected"
echo "LINES: $(wc -l < apps/app_unified.py)"
