#!/usr/bin/env python3
"""
TITAN OS — Full Operator-Level Verification
=============================================
Tests EVERY feature, app, module, and capability documented in the playbook.
Reads all core modules, apps, extensions, configs, services, AI models,
and produces a comprehensive gap report.

Run on VPS: python3 /tmp/full_operator_verify.py
"""

import os
import sys
import json
import ast
import importlib
import glob
import subprocess
import time
from pathlib import Path
from datetime import datetime

TITAN_ROOT = "/opt/titan"
CORE_DIR = f"{TITAN_ROOT}/core"
APPS_DIR = f"{TITAN_ROOT}/apps"
EXT_DIR = f"{TITAN_ROOT}/src/extensions"
CONFIG_DIR = f"{TITAN_ROOT}/config"

sys.path.insert(0, CORE_DIR)
sys.path.insert(0, APPS_DIR)
os.environ["TITAN_ROOT"] = TITAN_ROOT

PASS = 0
FAIL = 0
GAPS = []

def ok(category, name, detail=""):
    global PASS
    PASS += 1
    print(f"  OK: [{category}] {name}" + (f" ({detail})" if detail else ""))

def fail(category, name, detail=""):
    global FAIL
    FAIL += 1
    GAPS.append({"category": category, "name": name, "detail": detail})
    print(f"  FAIL: [{category}] {name}" + (f" ({detail})" if detail else ""))

def run(cmd, timeout=10):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.returncode == 0, r.stdout.strip(), r.stderr.strip()
    except Exception as e:
        return False, "", str(e)

print("=" * 70)
print("TITAN OS — FULL OPERATOR-LEVEL VERIFICATION")
print(f"Timestamp: {datetime.now().isoformat()}")
print("=" * 70)

# ═══════════════════════════════════════════════════════════════════════
# SECTION 1: CORE MODULES (documented: 113 = 110 Python + 3 C)
# ═══════════════════════════════════════════════════════════════════════
print("\n[1] CORE MODULES")

# 1a. Count Python files
py_files = [f for f in os.listdir(CORE_DIR) if f.endswith(".py") and f != "__init__.py"]
print(f"  Python modules in core/: {len(py_files)}")

# 1b. Import test every module
importable = 0
import_fails = []
for f in sorted(py_files):
    mod_name = f[:-3]
    try:
        importlib.import_module(mod_name)
        importable += 1
    except Exception as e:
        import_fails.append((mod_name, str(e)[:80]))

if importable >= 100:
    ok("core", f"{importable}/{len(py_files)} modules importable")
else:
    fail("core", f"Only {importable}/{len(py_files)} importable", f"{len(import_fails)} failures")

if import_fails:
    print(f"  Import failures ({len(import_fails)}):")
    for name, err in import_fails[:10]:
        print(f"    - {name}: {err}")

# 1c. Check critical modules exist (from playbook doc 03)
CRITICAL_MODULES = [
    "genesis_core", "advanced_profile_generator", "forensic_synthesis_engine",
    "profile_realism_engine", "persona_enrichment_engine", "purchase_history_engine",
    "indexeddb_lsng_synthesis", "first_session_bias_eliminator",
    "fingerprint_injector", "canvas_subpixel_shim", "canvas_noise",
    "audio_hardener", "font_sanitizer", "ghost_motor_v6",
    "tls_parrot", "ja4_permutation_engine", "timezone_enforcer",
    "integration_bridge", "network_shield", "network_shield_loader",
    "network_jitter", "proxy_manager", "quic_proxy",
    "mullvad_vpn", "lucid_vpn", "cpuid_rdtsc_shield",
    "cerberus_core", "cerberus_enhanced", "transaction_monitor",
    "three_ds_strategy", "tra_exemption_engine", "issuer_algo_defense",
    "payment_preflight", "payment_success_metrics", "dynamic_data",
    "form_autofill_injector",
    "ai_intelligence_engine", "cognitive_core", "ollama_bridge",
    "titan_agent_chain", "titan_vector_memory", "titan_web_intel",
    "titan_ai_operations_guard", "titan_3ds_ai_exploits",
    "titan_realtime_copilot", "titan_detection_analyzer",
    "target_discovery", "target_intelligence", "titan_target_intel_v2",
    "target_presets", "intel_monitor", "referrer_warmup",
    "kyc_core", "kyc_enhanced", "kyc_voice_engine",
    "verify_deep_identity", "tof_depth_synthesis",
    "usb_peripheral_synth", "waydroid_sync",
    "titan_automation_orchestrator", "titan_master_automation",
    "titan_autonomous_engine", "titan_auto_patcher",
    "titan_operation_logger", "handover_protocol", "preflight_validator",
    "kill_switch", "forensic_cleaner", "forensic_monitor",
    "titan_api", "titan_services", "titan_env", "cockpit_daemon",
    "titan_master_verify", "titan_self_hosted_stack",
    "bug_patch_bridge", "immutable_os",
    "chromium_cookie_engine", "leveldb_writer", "level9_antidetect",
    "biometric_mimicry", "titan_webhook_integrations",
    "titan_onnx_engine",
]
missing_critical = []
for mod in CRITICAL_MODULES:
    if not os.path.exists(f"{CORE_DIR}/{mod}.py"):
        missing_critical.append(mod)

if not missing_critical:
    ok("core", f"All {len(CRITICAL_MODULES)} critical modules present")
else:
    fail("core", f"{len(missing_critical)} critical modules missing", str(missing_critical[:5]))

# ═══════════════════════════════════════════════════════════════════════
# SECTION 2: GUI APPS (documented: 9 apps in V8.2.2)
# ═══════════════════════════════════════════════════════════════════════
print("\n[2] GUI APPS")

EXPECTED_APPS = {
    "titan_operations.py": {"tabs": 5, "desc": "Operations Center"},
    "titan_intelligence.py": {"tabs": 8, "desc": "Intelligence Center"},
    "titan_network.py": {"tabs": 5, "desc": "Network Center"},
    "app_kyc.py": {"tabs": 5, "desc": "KYC Studio"},
    "titan_admin.py": {"tabs": 6, "desc": "Admin Panel"},
    "app_settings.py": {"tabs": 6, "desc": "Settings"},
    "app_profile_forge.py": {"tabs": 4, "desc": "Profile Forge"},
    "app_card_validator.py": {"tabs": 3, "desc": "Card Validator"},
    "app_browser_launch.py": {"tabs": 3, "desc": "Browser Launch"},
    "titan_launcher.py": {"tabs": 0, "desc": "Launcher"},
    "app_bug_reporter.py": {"tabs": 7, "desc": "Bug Reporter"},
    "titan_dev_hub.py": {"tabs": 0, "desc": "Dev Hub"},
}

for app_file, info in EXPECTED_APPS.items():
    path = f"{APPS_DIR}/{app_file}"
    if os.path.exists(path):
        try:
            content = open(path).read()
            compile(content, path, "exec")
            tabs = content.count("addTab")
            ok("app", f"{info['desc']} ({app_file})", f"syntax OK, {tabs} tabs")
        except SyntaxError as e:
            fail("app", f"{info['desc']} ({app_file})", f"SYNTAX ERROR: {e}")
    else:
        fail("app", f"{info['desc']} ({app_file})", "FILE MISSING")

# ═══════════════════════════════════════════════════════════════════════
# SECTION 3: BROWSER EXTENSIONS
# ═══════════════════════════════════════════════════════════════════════
print("\n[3] BROWSER EXTENSIONS")

extensions = {
    "ghost_motor": ["ghost_motor.js", "manifest.json"],
    "tx_monitor": ["tx_monitor.js", "manifest.json", "background.js"],
}
for ext_name, files in extensions.items():
    for f in files:
        path = f"{TITAN_ROOT}/src/extensions/{ext_name}/{f}"
        if os.path.exists(path):
            ok("ext", f"{ext_name}/{f}")
        else:
            fail("ext", f"{ext_name}/{f}", "MISSING")

# ═══════════════════════════════════════════════════════════════════════
# SECTION 4: CONFIG FILES
# ═══════════════════════════════════════════════════════════════════════
print("\n[4] CONFIG FILES")

configs = {
    "llm_config.json": CONFIG_DIR,
    "oblivion_template.json": CONFIG_DIR,
    "titan.env": CONFIG_DIR,
}
for cfg, dir_path in configs.items():
    path = f"{dir_path}/{cfg}"
    if os.path.exists(path):
        size = os.path.getsize(path)
        ok("config", cfg, f"{size} bytes")
    else:
        fail("config", cfg, "MISSING")

# Check llm_config task routing
llm_cfg_path = f"{CONFIG_DIR}/llm_config.json"
if os.path.exists(llm_cfg_path):
    try:
        cfg = json.load(open(llm_cfg_path))
        routes = cfg.get("task_routing", {})
        ok("config", f"llm_config task_routing", f"{len(routes)} routes")
    except Exception as e:
        fail("config", "llm_config parse", str(e))

# ═══════════════════════════════════════════════════════════════════════
# SECTION 5: EXTERNAL SERVICES (documented in playbook 18)
# ═══════════════════════════════════════════════════════════════════════
print("\n[5] EXTERNAL SERVICES")

services = {
    "ollama": {"check": "curl -s http://127.0.0.1:11434/api/tags", "port": 11434},
    "redis": {"check": "redis-cli ping", "port": 6379},
    "xray": {"check": "systemctl is-active xray", "port": None},
    "ntfy": {"check": "systemctl is-active ntfy", "port": 8090},
    "waydroid": {"check": "which waydroid", "port": None},
}
for svc, info in services.items():
    success, stdout, stderr = run(info["check"])
    if success and stdout:
        ok("service", svc, stdout[:50])
    else:
        fail("service", svc, stderr[:50] if stderr else "not responding")

# ═══════════════════════════════════════════════════════════════════════
# SECTION 6: AI MODELS
# ═══════════════════════════════════════════════════════════════════════
print("\n[6] AI MODELS")

# Ollama models
success, stdout, stderr = run("ollama list")
if success:
    lines = [l for l in stdout.splitlines() if l.strip() and not l.startswith("NAME")]
    models = [l.split()[0] for l in lines if l.split()]
    titan_models = [m for m in models if "titan" in m.lower()]
    ok("ai", f"Ollama models: {len(models)} total, {len(titan_models)} titan")
    for m in titan_models:
        ok("ai", f"  {m}")
    
    expected_titan = ["titan-analyst", "titan-strategist", "titan-fast"]
    for exp in expected_titan:
        found = any(exp in m for m in models)
        if not found:
            fail("ai", f"Missing titan model: {exp}")
else:
    fail("ai", "Ollama not responding")

# ONNX model
onnx_files = glob.glob(f"{TITAN_ROOT}/models/phi4-mini-onnx/**/*.onnx", recursive=True)
if onnx_files:
    total_size = sum(os.path.getsize(f) for f in onnx_files) / 1024 / 1024
    ok("ai", f"Phi-4-mini ONNX: {len(onnx_files)} files, {total_size:.0f}MB")
else:
    fail("ai", "Phi-4-mini ONNX model not found")

# ONNX engine
try:
    from titan_onnx_engine import get_status
    status = get_status()
    ok("ai", f"ONNX engine: backend={status.get('backend')}, tasks={status.get('tasks_mapped')}")
except Exception as e:
    fail("ai", f"ONNX engine import", str(e)[:60])

# ═══════════════════════════════════════════════════════════════════════
# SECTION 7: KYC + ANDROID MODULE
# ═══════════════════════════════════════════════════════════════════════
print("\n[7] KYC + ANDROID")

kyc_modules = ["kyc_core", "kyc_enhanced", "kyc_voice_engine", "tof_depth_synthesis", "waydroid_sync"]
for mod in kyc_modules:
    try:
        importlib.import_module(mod)
        ok("kyc", mod)
    except Exception as e:
        fail("kyc", mod, str(e)[:60])

# Android/Waydroid
android_checks = {
    "waydroid binary": "which waydroid",
    "system.img": "test -f /var/lib/waydroid/images/system.img",
    "vendor.img": "test -f /var/lib/waydroid/images/vendor.img",
    "device props": "test -f /var/lib/waydroid/waydroid_base.prop",
    "kyc_android_console": f"test -f {TITAN_ROOT}/android/kyc_android_console.py",
    "titan-android CLI": "test -x /usr/local/bin/titan-android",
}
for name, cmd in android_checks.items():
    success, _, _ = run(cmd)
    if success:
        ok("android", name)
    else:
        fail("android", name)

# ═══════════════════════════════════════════════════════════════════════
# SECTION 8: TRAINING DATA
# ═══════════════════════════════════════════════════════════════════════
print("\n[8] TRAINING DATA")

training_dirs = {
    "phase1": f"{TITAN_ROOT}/training/phase1",
    "phase2": f"{TITAN_ROOT}/training/phase2",
    "phase3": f"{TITAN_ROOT}/training/phase3",
}
for name, path in training_dirs.items():
    if os.path.isdir(path):
        files = os.listdir(path)
        ok("training", name, f"{len(files)} files")
    else:
        fail("training", name, "MISSING")

# Operator training data
op_data = glob.glob(f"{TITAN_ROOT}/training/data_v10_operator/*.jsonl")
if op_data:
    total = sum(1 for f in op_data for _ in open(f))
    ok("training", f"Operator training data: {total} examples in {len(op_data)} files")
else:
    fail("training", "No operator training data (.jsonl)")

# ═══════════════════════════════════════════════════════════════════════
# SECTION 9: DIRECTORY STRUCTURE
# ═══════════════════════════════════════════════════════════════════════
print("\n[9] DIRECTORY STRUCTURE")

expected_dirs = [
    "core", "apps", "src", "config", "scripts", "docs", "training",
    "tests", "bin", "branding", "modelfiles", "iso", "android",
    "models", "profiles", "state", "data",
    "src/extensions", "src/lib", "src/patches", "src/tools", "src/vpn",
]
for d in expected_dirs:
    path = f"{TITAN_ROOT}/{d}"
    if os.path.isdir(path):
        ok("dir", d)
    else:
        fail("dir", d, "MISSING")

# ═══════════════════════════════════════════════════════════════════════
# SECTION 10: KEY CLASS/FUNCTION EXISTENCE (from playbook docs)
# ═══════════════════════════════════════════════════════════════════════
print("\n[10] KEY CLASSES (spot check from playbook)")

spot_checks = [
    ("genesis_core", "GenesisEngine"),
    ("cerberus_core", "CerberusValidator"),
    ("fingerprint_injector", "FingerprintInjector"),
    ("ghost_motor_v6", "get_forter_safe_params"),
    ("integration_bridge", "TitanIntegrationBridge"),
    ("kill_switch", "KillSwitch"),
    ("kyc_core", "KYCController"),
    ("kyc_enhanced", "KYCEnhancedController"),
    ("tof_depth_synthesis", "FaceDepthGenerator"),
    ("waydroid_sync", "WaydroidSyncEngine"),
    ("titan_onnx_engine", "TitanOnnxEngine"),
    ("ai_intelligence_engine", "get_ai_status"),
    ("ollama_bridge", "OllamaBridge"),
    ("three_ds_strategy", "get_3ds_bypass_score"),
    ("titan_automation_orchestrator", "TitanOrchestrator"),
]

for mod_name, class_name in spot_checks:
    try:
        mod = importlib.import_module(mod_name)
        if hasattr(mod, class_name):
            ok("class", f"{mod_name}.{class_name}")
        else:
            fail("class", f"{mod_name}.{class_name}", "class/func not found in module")
    except Exception as e:
        fail("class", f"{mod_name}.{class_name}", f"import failed: {str(e)[:50]}")

# ═══════════════════════════════════════════════════════════════════════
# SECTION 11: DISK SPACE + SYSTEM
# ═══════════════════════════════════════════════════════════════════════
print("\n[11] SYSTEM")
success, stdout, _ = run("df -h / | tail -1")
if success:
    ok("system", f"Disk: {stdout}")
success, stdout, _ = run("free -h | head -2 | tail -1")
if success:
    ok("system", f"RAM: {stdout[:60]}")
success, stdout, _ = run("uname -r")
if success:
    ok("system", f"Kernel: {stdout}")
success, stdout, _ = run("python3 --version")
if success:
    ok("system", f"Python: {stdout}")

# ═══════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print(f"VERIFICATION COMPLETE")
print(f"  PASSED: {PASS}")
print(f"  FAILED: {FAIL}")
print(f"  GAPS: {len(GAPS)}")
print("=" * 70)

if GAPS:
    print("\nGAP REPORT:")
    for i, gap in enumerate(GAPS, 1):
        print(f"  {i}. [{gap['category']}] {gap['name']}: {gap['detail']}")

# Save report
report = {
    "timestamp": datetime.now().isoformat(),
    "passed": PASS,
    "failed": FAIL,
    "gaps": GAPS,
    "import_failures": import_fails,
    "missing_critical": missing_critical,
}
report_path = f"{TITAN_ROOT}/verification_report.json"
with open(report_path, "w") as f:
    json.dump(report, f, indent=2, default=str)
print(f"\nReport saved: {report_path}")
