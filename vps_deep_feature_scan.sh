#!/bin/bash
# TITAN V7.5 — Deep Feature Gap Scan: docs/core vs GUI
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  TITAN V7.5 — DEEP FEATURE GAP SCAN                                 ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"

cd /opt/titan

# ─── 1. Core modules vs GUI wiring ───────────────────────────────────────
echo ""
echo "═══ [1] CORE MODULES → GUI WIRING CHECK ═══"
echo "  Checking if each core module is imported/used in any app..."
echo ""

for mod in $(find core/ -maxdepth 1 -name "*.py" -type f | sort); do
    modname=$(basename "$mod" .py)
    # Skip __init__, __pycache__, test files
    [[ "$modname" == "__"* ]] && continue
    [[ "$modname" == "test_"* ]] && continue
    
    # Check if referenced in any app
    refs=$(grep -rl "$modname" apps/*.py 2>/dev/null | wc -l)
    if [ "$refs" -gt 0 ]; then
        echo "  ✅ $modname → used in $refs app(s)"
    else
        echo "  ❌ $modname → NOT used in any app"
    fi
done

# ─── 2. Ghost Motor specific check ───────────────────────────────────────
echo ""
echo "═══ [2] GHOST MOTOR INTEGRATION ═══"
echo "  ghost_motor_v6.py exists: $([ -f core/ghost_motor_v6.py ] && echo YES || echo NO)"
echo "  Lines: $(wc -l < core/ghost_motor_v6.py 2>/dev/null)"
echo "  Referenced in app_unified: $(grep -ci 'ghost.motor\|GhostMotor\|ghost_motor' apps/app_unified.py)"
echo "  Referenced in app_cerberus: $(grep -ci 'ghost.motor\|GhostMotor\|ghost_motor' apps/app_cerberus.py)"
echo ""
echo "  ghost_motor_v6.py exports:"
grep "^class \|^def " core/ghost_motor_v6.py 2>/dev/null | head -15

# ─── 3. Fingerprint Injector check ───────────────────────────────────────
echo ""
echo "═══ [3] FINGERPRINT INJECTOR ═══"
echo "  fingerprint_injector.py exists: $([ -f core/fingerprint_injector.py ] && echo YES || echo NO)"
echo "  Lines: $(wc -l < core/fingerprint_injector.py 2>/dev/null)"
echo "  Referenced in app_unified: $(grep -ci 'fingerprint_injector\|FingerprintInjector' apps/app_unified.py)"
echo ""
echo "  Exports:"
grep "^class \|^def " core/fingerprint_injector.py 2>/dev/null | head -10

# ─── 4. Canvas/Audio/Font hardening in GUI ────────────────────────────────
echo ""
echo "═══ [4] HARDENING MODULES IN GUI ═══"
for mod in font_sanitizer audio_hardener timezone_enforcer kill_switch immutable_os canvas_subpixel_shim cpuid_rdtsc_shield windows_font_provisioner; do
    exists=$([ -f "core/${mod}.py" ] && echo "✅" || echo "❌")
    gui_refs=$(grep -ci "$mod" apps/app_unified.py 2>/dev/null)
    echo "  $exists $mod: exists=$([ -f core/${mod}.py ] && echo Y || echo N), GUI refs=$gui_refs"
done

# ─── 5. app_unified method coverage ──────────────────────────────────────
echo ""
echo "═══ [5] APP_UNIFIED METHOD COVERAGE ═══"
echo "  Total methods: $(grep -c 'def ' apps/app_unified.py)"
echo ""
echo "  Methods by category:"
echo "    Genesis/Profile: $(grep 'def ' apps/app_unified.py | grep -ci 'genesis\|profile\|forge')"
echo "    Cerberus/Card:   $(grep 'def ' apps/app_unified.py | grep -ci 'cerberus\|card\|bin\|avs')"
echo "    KYC:             $(grep 'def ' apps/app_unified.py | grep -ci 'kyc')"
echo "    Browser/Launch:  $(grep 'def ' apps/app_unified.py | grep -ci 'browser\|launch\|camoufox')"
echo "    AI:              $(grep 'def ' apps/app_unified.py | grep -ci '_ai_')"
echo "    Forensic:        $(grep 'def ' apps/app_unified.py | grep -ci 'forensic')"
echo "    3DS:             $(grep 'def ' apps/app_unified.py | grep -ci '3ds\|bypass')"
echo "    Discovery:       $(grep 'def ' apps/app_unified.py | grep -ci 'discover\|disc')"
echo "    Services:        $(grep 'def ' apps/app_unified.py | grep -ci 'service')"
echo "    Ghost Motor:     $(grep 'def ' apps/app_unified.py | grep -ci 'ghost\|motor\|behavior')"
echo "    Network/Proxy:   $(grep 'def ' apps/app_unified.py | grep -ci 'proxy\|network\|dns')"
echo "    Kill Switch:     $(grep 'def ' apps/app_unified.py | grep -ci 'kill\|shred\|wipe')"
echo "    TX Monitor:      $(grep 'def ' apps/app_unified.py | grep -ci 'tx_\|transaction\|decline')"
echo "    TLS:             $(grep 'def ' apps/app_unified.py | grep -ci 'tls\|parrot')"
echo "    Health:          $(grep 'def ' apps/app_unified.py | grep -ci 'health\|hud\|status')"

# ─── 6. Cross-check: what cerberus_enhanced offers vs what GUI uses ──────
echo ""
echo "═══ [6] CERBERUS_ENHANCED → GUI COVERAGE ═══"
echo "  cerberus_enhanced exports:"
grep "^class \|^def " core/cerberus_enhanced.py | head -20
echo ""
echo "  Used in app_unified:"
grep -o "OSINTVerifier\|CardQualityGrader\|BINScoringEngine\|AVSEngine\|SilentValidation\|score_bin\|check_avs\|get_silent_strategy" apps/app_unified.py | sort | uniq -c | sort -rn

# ─── 7. Cross-check: what three_ds_strategy offers vs what GUI uses ──────
echo ""
echo "═══ [7] THREE_DS_STRATEGY → GUI COVERAGE ═══"
echo "  three_ds_strategy exports:"
grep "^class \|^def " core/three_ds_strategy.py | head -20
echo ""
echo "  Used in app_unified:"
grep -o "ThreeDSBypassEngine\|get_3ds_bypass_score\|get_3ds_bypass_plan\|get_downgrade_attacks\|get_psp_vulnerabilities\|get_psd2_exemptions\|NonVBVRecommendation\|get_non_vbv_recommendations\|get_easy_countries\|get_all_non_vbv_bins\|get_3ds_v2_intelligence\|get_3ds_detection_guide" apps/app_unified.py | sort | uniq -c | sort -rn

# ─── 8. Missing buttons/actions check ────────────────────────────────────
echo ""
echo "═══ [8] CONNECTED vs DISCONNECTED BUTTONS ═══"
echo "  Buttons with .clicked.connect:"
CONNECTED=$(grep -c "clicked.connect" apps/app_unified.py)
echo "    Connected: $CONNECTED"
echo ""
echo "  QPushButton without connect (potential dead buttons):"
python3 - <<'PYEOF'
import re
with open("apps/app_unified.py") as f:
    lines = f.readlines()

buttons = {}
for i, line in enumerate(lines):
    # Find button creation
    m = re.search(r'(\w+)\s*=\s*QPushButton\(', line)
    if m:
        buttons[m.group(1)] = i + 1
    # Find button connect
    m = re.search(r'(\w+)\.clicked\.connect', line)
    if m and m.group(1) in buttons:
        del buttons[m.group(1)]

if buttons:
    for name, line_no in sorted(buttons.items(), key=lambda x: x[1]):
        print(f"    ⚠️  Line {line_no}: {name} — no .clicked.connect found")
else:
    print("    ✅ All buttons connected")
PYEOF

# ─── 9. Version consistency ──────────────────────────────────────────────
echo ""
echo "═══ [9] VERSION CONSISTENCY ═══"
for f in apps/app_unified.py apps/app_genesis.py apps/app_cerberus.py apps/app_kyc.py; do
    ver=$(grep -oP "V7\.\d+\.?\d*" "$f" 2>/dev/null | head -1)
    echo "  $(basename $f): $ver"
done
for f in core/hardware_shield_v6.c core/network_shield_v6.c core/tls_parrot.py core/ai_intelligence_engine.py core/ollama_bridge.py; do
    ver=$(grep -oP '7\.\d+\.\d+' "$f" 2>/dev/null | head -1)
    echo "  $(basename $f): V$ver"
done

# ─── 10. Lucid Empire backend modules in GUI ─────────────────────────────
echo ""
echo "═══ [10] LUCID EMPIRE BACKEND → GUI ═══"
echo "  Backend modules:"
ls /opt/lucid-empire/backend/modules/*.py 2>/dev/null | while read f; do
    mod=$(basename "$f" .py)
    refs=$(grep -rci "$mod" apps/ 2>/dev/null | awk -F: '{s+=$2}END{print s}')
    echo "    $([ "$refs" -gt 0 ] && echo '✅' || echo '❌') $mod: $refs GUI refs"
done

echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  GAP SCAN COMPLETE                                                   ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
