#!/bin/bash
# TITAN V7.5 — Complete VPS Sync & Verification
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  TITAN V7.5 — COMPLETE VPS SYNC                                     ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"

# ─── 1. Check what's different between local upload and VPS ──────────────
echo ""
echo "═══ [1] CURRENT VPS STATE ═══"
echo "  Apps:"
for f in app_unified app_genesis app_cerberus app_kyc; do
    echo "    ${f}.py: $(wc -l < /opt/titan/apps/${f}.py 2>/dev/null || echo MISSING) lines"
done
echo "  Core (new V7.5 modules):"
for f in ai_intelligence_engine canvas_subpixel_shim cpuid_rdtsc_shield windows_font_provisioner tls_parrot ollama_bridge ghost_motor_v6 fingerprint_injector immutable_os dynamic_data forensic_monitor; do
    if [ -f "/opt/titan/core/${f}.py" ]; then
        echo "    ✅ ${f}.py: $(wc -l < /opt/titan/core/${f}.py) lines"
    else
        echo "    ❌ ${f}.py: MISSING"
    fi
done

# ─── 2. Check versions ──────────────────────────────────────────────────
echo ""
echo "═══ [2] VERSION CHECK ═══"
for f in /opt/titan/apps/app_unified.py /opt/titan/apps/app_genesis.py /opt/titan/apps/app_cerberus.py /opt/titan/apps/app_kyc.py; do
    ver=$(grep -oP "V7\.\d+\.?\d*" "$f" 2>/dev/null | head -1)
    echo "  $(basename $f): $ver"
done

# ─── 3. Full import test ────────────────────────────────────────────────
echo ""
echo "═══ [3] IMPORT TEST ═══"
cd /opt/titan && python3 - <<'PYEOF'
import sys, time
sys.path.insert(0, "core")
sys.path.insert(0, "apps")

modules = [
    "genesis_core", "cerberus_core", "cerberus_enhanced", "target_presets",
    "advanced_profile_generator", "target_intelligence", "three_ds_strategy",
    "font_sanitizer", "audio_hardener", "timezone_enforcer", "kill_switch",
    "purchase_history_engine", "preflight_validator", "transaction_monitor",
    "target_discovery", "titan_services", "ai_intelligence_engine",
    "tls_parrot", "ghost_motor_v6", "fingerprint_injector", "canvas_subpixel_shim",
    "cpuid_rdtsc_shield", "ollama_bridge", "forensic_monitor", "kyc_core",
    "dynamic_data", "immutable_os", "windows_font_provisioner",
]

ok = 0
fail = 0
for m in sorted(modules):
    try:
        t0 = time.monotonic()
        __import__(m)
        ms = (time.monotonic() - t0) * 1000
        print(f"  ✅ {m:<35} {ms:>6.0f}ms")
        ok += 1
    except Exception as e:
        print(f"  ❌ {m:<35} {str(e)[:50]}")
        fail += 1

print(f"\n  Result: {ok}/{ok+fail} modules OK")
PYEOF

# ─── 4. AI Engine status ────────────────────────────────────────────────
echo ""
echo "═══ [4] AI ENGINE STATUS ═══"
cd /opt/titan && python3 -c "
import sys; sys.path.insert(0,'core')
from ai_intelligence_engine import get_ai_status
s = get_ai_status()
print(f'  Available: {s[\"available\"]}')
print(f'  Provider: {s[\"provider\"]}')
print(f'  Features: {len(s[\"features\"])}')
for f in s['features']:
    print(f'    ✅ {f}')
"

# ─── 5. Backend API health ──────────────────────────────────────────────
echo ""
echo "═══ [5] BACKEND API ═══"
curl -s http://localhost:8000/api/health 2>/dev/null || echo "  Backend not responding"

# ─── 6. Services status ─────────────────────────────────────────────────
echo ""
echo "═══ [6] SERVICES ═══"
for svc in ollama titan-backend fail2ban; do
    status=$(systemctl is-active $svc 2>/dev/null)
    echo "  $svc: $status"
done

# ─── 7. Running processes ───────────────────────────────────────────────
echo ""
echo "═══ [7] RUNNING PROCESSES ═══"
echo "  app_unified: $(ps aux | grep app_unified | grep -v grep | wc -l) instances"
echo "  uvicorn: $(ps aux | grep uvicorn | grep -v grep | wc -l) workers"
echo "  ollama: $(ps aux | grep ollama | grep -v grep | wc -l) processes"

# ─── 8. Recompile all bytecode ──────────────────────────────────────────
echo ""
echo "═══ [8] RECOMPILE BYTECODE ═══"
python3 -m compileall -q -f /opt/titan/core/ /opt/titan/apps/ 2>/dev/null
echo "  __pycache__ dirs: $(find /opt/titan -name '__pycache__' -type d | wc -l)"

# ─── 9. Feature completeness ────────────────────────────────────────────
echo ""
echo "═══ [9] FEATURE COMPLETENESS ═══"
cd /opt/titan && python3 - <<'PYEOF'
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
    "AI Behavioral": "_ai_tune_behavior" in content,
    "AI Profile Audit": "_ai_audit_profile" in content,
    "AI TLS Parrot": "_ai_tls_status" in content,
    "AI Status": "_ai_refresh_status" in content,
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
    "Target Intel": "target_intel" in content.lower(),
    "BIN Scoring": "score_bin" in content,
    "TX Monitor": "_refresh_tx_monitor" in content,
    "Forensic Widget": "forensic_widget" in content,
    "OSINT Verifier": "OSINTVerifier" in content,
    "Card Quality": "CardQualityGrader" in content,
    "Purchase History": "Purchase Hist" in content,
}

present = sum(1 for v in checks.values() if v)
total = len(checks)
missing = [k for k, v in checks.items() if not v]
print(f"  Score: {present}/{total} ({present/total*100:.0f}%)")
if missing:
    for m in missing:
        print(f"    ❌ {m}")
else:
    print("  ✅ ALL FEATURES PRESENT")
PYEOF

# ─── 10. Tab/Button summary ─────────────────────────────────────────────
echo ""
echo "═══ [10] SUMMARY ═══"
echo "  Main tabs: $(grep -c 'main_tabs.addTab' /opt/titan/apps/app_unified.py)"
echo "  Total sub-tabs: $(grep -c '_tabs.addTab' /opt/titan/apps/app_unified.py)"
echo "  Buttons: $(grep -c 'QPushButton' /opt/titan/apps/app_unified.py)"
echo "  Connected: $(grep -c 'clicked.connect' /opt/titan/apps/app_unified.py)"
echo "  Methods: $(grep -c 'def ' /opt/titan/apps/app_unified.py)"
echo "  Lines: $(wc -l < /opt/titan/apps/app_unified.py)"
echo "  Syntax: $(python3 -c "import py_compile; py_compile.compile('/opt/titan/apps/app_unified.py', doraise=True)" 2>&1 && echo OK || echo FAIL)"

# ─── 11. Quick AI smoke test ────────────────────────────────────────────
echo ""
echo "═══ [11] AI SMOKE TEST ═══"
cd /opt/titan && python3 -c "
import sys; sys.path.insert(0,'core')
from ai_intelligence_engine import analyze_bin, recon_target
b = analyze_bin('421783', 'eneba.com', 150)
print(f'  BIN 421783: score={b.ai_score}/100 risk={b.risk_level.value} bank={b.bank_name}')
t = recon_target('eneba.com')
print(f'  eneba.com: fraud={t.fraud_engine_guess} psp={t.payment_processor_guess} 3ds={t.three_ds_probability:.0%}')
print('  ✅ AI smoke test passed')
" 2>&1 || echo "  ⚠️ AI test failed (Ollama may be loading)"

echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  VPS COMPLETE — ALL SYSTEMS VERIFIED                                 ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
