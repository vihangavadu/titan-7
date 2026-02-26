#!/bin/bash
# Full VPS operator-level verification
set -e
cd /opt/titan/core

echo "=== 1. CORE MODULE IMPORT TEST ==="
python3 << 'PYEOF'
import os, importlib, sys
sys.path.insert(0, '.')
py_files = sorted([f[:-3] for f in os.listdir('.') if f.endswith('.py') and f != '__init__.py' and not f.startswith('__')])
ok, fails = 0, []
for m in py_files:
    try:
        importlib.import_module(m)
        ok += 1
    except Exception as e:
        fails.append(f'{m}: {str(e)[:80]}')
print(f'IMPORTABLE: {ok}/{len(py_files)}')
if fails:
    print(f'FAILURES ({len(fails)}):')
    for f in fails:
        print(f'  {f}')
print(f'MODULE_LIST: {",".join(py_files)}')
PYEOF

echo ""
echo "=== 2. APP SYNTAX CHECK ==="
for f in /opt/titan/apps/*.py; do
    python3 -c "import ast; ast.parse(open('$f').read())" 2>/dev/null && echo "  OK: $(basename $f)" || echo "  FAIL: $(basename $f)"
done

echo ""
echo "=== 3. KEY CLASS SPOT CHECK ==="
cd /opt/titan/core
python3 << 'PYEOF'
checks = [
    ("genesis_core", "GenesisEngine"),
    ("cerberus_core", "CerberusValidator"),
    ("fingerprint_injector", "FingerprintInjector"),
    ("ghost_motor_v6", "get_forter_safe_params"),
    ("integration_bridge", "TitanIntegrationBridge"),
    ("kill_switch", "KillSwitch"),
    ("kyc_core", "KYCController"),
    ("titan_onnx_engine", "TitanOnnxEngine"),
    ("ai_intelligence_engine", "AIIntelligenceEngine"),
    ("ollama_bridge", "OllamaBridge"),
    ("three_ds_strategy", "ThreeDSBypassEngine"),
    ("titan_automation_orchestrator", "TitanOrchestrator"),
    ("titan_vector_memory", "TitanVectorMemory"),
    ("titan_agent_chain", "TitanAgent"),
    ("cognitive_core", "TitanCognitiveCore"),
    ("tof_depth_synthesis", "FaceDepthGenerator"),
    ("waydroid_sync", "WaydroidSyncEngine"),
    ("titan_webhook_integrations", "WebhookEvent"),
    ("biometric_mimicry", "BiometricMimicry"),
    ("level9_antidetect", "Level9Antidetect"),
    ("chromium_cookie_engine", "ChromiumCookieEngine"),
    ("leveldb_writer", "LevelDBWriter"),
    ("oblivion_forge", "OblivionForgeEngine"),
    ("profile_isolation", "ProfileIsolation"),
    ("titan_detection_lab", "DetectionLab"),
    ("titan_detection_lab_v2", "DetectionLabV2"),
]
import sys
sys.path.insert(0, '.')
ok, fail = 0, 0
for mod_name, cls_name in checks:
    try:
        mod = __import__(mod_name)
        if hasattr(mod, cls_name):
            print(f'  OK: {mod_name}.{cls_name}')
            ok += 1
        else:
            print(f'  MISSING_CLASS: {mod_name}.{cls_name}')
            fail += 1
    except Exception as e:
        print(f'  IMPORT_FAIL: {mod_name} -> {str(e)[:60]}')
        fail += 1
print(f'CLASSES: {ok} ok, {fail} fail')
PYEOF

echo ""
echo "=== 4. ONNX MODEL ==="
python3 << 'PYEOF'
import os, glob
onnx_dir = "/opt/titan/models/phi4-mini-onnx"
if os.path.isdir(onnx_dir):
    onnx_files = glob.glob(f"{onnx_dir}/**/*.onnx", recursive=True)
    total = sum(os.path.getsize(f) for f in onnx_files) / 1024 / 1024
    print(f"ONNX: {len(onnx_files)} files, {total:.0f}MB")
else:
    print("ONNX: NOT FOUND")

# Test ONNX engine import
try:
    import sys
    sys.path.insert(0, '/opt/titan/core')
    from titan_onnx_engine import get_status
    s = get_status()
    print(f"ONNX_ENGINE: backend={s.get('backend')}, tasks={s.get('tasks_mapped')}")
except Exception as e:
    print(f"ONNX_ENGINE: FAIL - {e}")
PYEOF

echo ""
echo "=== 5. EXTERNAL SERVICES ==="
echo -n "  Ollama: "; systemctl is-active ollama 2>/dev/null || echo "inactive"
echo -n "  Redis: "; systemctl is-active redis-server 2>/dev/null || echo "inactive"
echo -n "  Xray: "; systemctl is-active xray 2>/dev/null || echo "inactive"
echo -n "  ntfy: "; systemctl is-active ntfy 2>/dev/null || echo "inactive"
echo -n "  Mullvad: "; systemctl is-active mullvad-daemon 2>/dev/null || echo "inactive"
echo -n "  Waydroid: "; which waydroid >/dev/null 2>&1 && echo "installed" || echo "not installed"

echo ""
echo "=== 6. EXTENSIONS ==="
for ext in ghost_motor tx_monitor; do
    if [ -d "/opt/titan/src/extensions/$ext" ]; then
        echo "  OK: $ext ($(ls /opt/titan/src/extensions/$ext/ | wc -l) files)"
    else
        echo "  MISSING: $ext"
    fi
done
test -f /opt/titan/src/extensions/golden_trap.js && echo "  OK: golden_trap.js" || echo "  MISSING: golden_trap.js"

echo ""
echo "=== 7. CONFIG FILES ==="
for f in llm_config.json oblivion_template.json titan.env; do
    if [ -f "/opt/titan/config/$f" ]; then
        echo "  OK: $f ($(wc -c < /opt/titan/config/$f) bytes)"
    else
        echo "  MISSING: $f"
    fi
done

echo ""
echo "=== 8. TRAINING DATA ==="
echo -n "  JSONL files: "; ls /opt/titan/training/data_v10_operator/*.jsonl 2>/dev/null | wc -l
echo -n "  Total examples: "; cat /opt/titan/training/data_v10_operator/*.jsonl 2>/dev/null | wc -l

echo ""
echo "=== 9. ANDROID/KYC ==="
test -f /opt/titan/android/kyc_android_console.py && echo "  OK: kyc_android_console.py" || echo "  MISSING: kyc_android_console.py"
test -x /usr/local/bin/titan-android && echo "  OK: titan-android CLI" || echo "  MISSING: titan-android CLI"

echo ""
echo "=== 10. SYSTEM ==="
echo "  Disk: $(df -h / | tail -1 | awk '{print $3"/"$2" ("$5" used)"}')"
echo "  RAM: $(free -h | awk '/Mem:/{print $3"/"$2}')"
echo "  Kernel: $(uname -r)"
echo "  Python: $(python3 --version 2>&1)"

echo ""
echo "=== 11. API ENDPOINTS ==="
cd /opt/titan/core
python3 << 'PYEOF'
import sys
sys.path.insert(0, '.')
try:
    import ast
    tree = ast.parse(open('titan_api.py').read())
    routes = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and hasattr(n, 'func') and hasattr(getattr(n, 'func', None), 'attr', None) and getattr(n.func, 'attr', '') == 'route']
    # Count @app.route decorators
    count = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for dec in node.decorator_list:
                if isinstance(dec, ast.Call) and hasattr(dec.func, 'attr') and dec.func.attr == 'route':
                    count += 1
    print(f"API_ENDPOINTS: {count}")
except Exception as e:
    print(f"API_ENDPOINTS: error - {e}")
PYEOF

echo ""
echo "=== VERIFICATION COMPLETE ==="
