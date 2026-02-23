#!/usr/bin/env python3
"""TITAN V8.2 — Full Re-Verification Suite (8 Tests)"""
import os, sys, py_compile
sys.path.insert(0, "/opt/titan/core")
sys.path.insert(0, "/opt/titan/apps")

print("=" * 60)
print("TITAN V8.2 — FULL RE-VERIFICATION SUITE")
print("=" * 60)

# TEST 1: 110-Module Import Smoke Test
print("\n[TEST 1] 110-Module Import Smoke Test")
files = sorted([f[:-3] for f in os.listdir("/opt/titan/core") if f.endswith(".py") and f != "__init__.py"])
t1_ok = 0
t1_fail = []
for m in files:
    try:
        __import__(m)
        t1_ok += 1
    except Exception as e:
        t1_fail.append(m + ": " + str(e)[:80])
print("  TOTAL:", len(files))
print("  OK:", t1_ok)
print("  FAIL:", len(t1_fail))
for f in t1_fail:
    print("   ", f)

# TEST 2: Integration Bridge Subsystem Flags
print("\n[TEST 2] Integration Bridge Subsystem Flags")
import integration_bridge as ib
flags = [
    ("JA4_AVAILABLE", ib.JA4_AVAILABLE),
    ("FSB_AVAILABLE", ib.FSB_AVAILABLE),
    ("TRA_AVAILABLE", ib.TRA_AVAILABLE),
    ("LSNG_AVAILABLE", ib.LSNG_AVAILABLE),
    ("ISSUER_DEFENSE_AVAILABLE", ib.ISSUER_DEFENSE_AVAILABLE),
    ("TOF_AVAILABLE", ib.TOF_AVAILABLE),
    ("GHOST_MOTOR_AVAILABLE", ib.GHOST_MOTOR_AVAILABLE),
    ("OLLAMA_AVAILABLE", ib.OLLAMA_AVAILABLE),
    ("WEBGL_ANGLE_AVAILABLE", ib.WEBGL_ANGLE_AVAILABLE),
    ("FORENSIC_AVAILABLE", ib.FORENSIC_AVAILABLE),
]
t2_ok = sum(1 for _, v in flags if v)
for name, val in flags:
    print("  " + ("OK" if val else "MISSING") + ": " + name)

# TEST 3: GUI App Syntax Check
print("\n[TEST 3] GUI App Syntax Check")
apps = ["titan_operations", "titan_admin", "titan_intelligence", "titan_network", "titan_launcher", "app_kyc"]
t3_ok = 0
for a in apps:
    path = "/opt/titan/apps/" + a + ".py"
    try:
        py_compile.compile(path, doraise=True)
        print("  SYNTAX OK:", a)
        t3_ok += 1
    except py_compile.PyCompileError as e:
        print("  SYNTAX FAIL:", a, str(e)[:80])

# TEST 4: __init__.py Orphan Imports
print("\n[TEST 4] V8.2 Orphan Module Imports (13)")
orphans = [
    ("chromium_commerce_injector", "inject_golden_chain"),
    ("leveldb_writer", "LevelDBWriter"),
    ("titan_master_verify", "VerificationOrchestrator"),
    ("mcp_interface", "MCPClient"),
    ("ntp_isolation", "IsolationManager"),
    ("time_safety_validator", "SafetyValidator"),
    ("forensic_alignment", "ForensicAlignment"),
    ("tls_mimic", "TLSMimic"),
    ("canvas_noise", "CanvasNoiseGenerator"),
    ("profile_realism_engine", "ProfileRealismEngine"),
    ("forensic_synthesis_engine", "Cache2Synthesizer"),
    ("gamp_triangulation_v2", "GAMPTriangulation"),
    ("oblivion_setup", "check_python_version"),
]
t4_ok = 0
for mod, cls in orphans:
    try:
        m = __import__(mod, fromlist=[cls])
        getattr(m, cls)
        print("  OK:", mod + "." + cls)
        t4_ok += 1
    except Exception as e:
        print("  FAIL:", mod + "." + cls, str(e)[:60])

# TEST 5: ForgeWorker Pipeline Stages
print("\n[TEST 5] ForgeWorker Pipeline (9 stages)")
forge = [
    ("genesis_core", "GenesisEngine"),
    ("purchase_history_engine", "PurchaseHistoryEngine"),
    ("indexeddb_lsng_synthesis", "IndexedDBShardSynthesizer"),
    ("first_session_bias_eliminator", "FirstSessionBiasEliminator"),
    ("chromium_commerce_injector", "inject_golden_chain"),
    ("forensic_synthesis_engine", "Cache2Synthesizer"),
    ("font_sanitizer", "FontSanitizer"),
    ("audio_hardener", "AudioHardener"),
    ("profile_realism_engine", "ProfileRealismEngine"),
]
t5_ok = 0
for i, (mod, cls) in enumerate(forge, 1):
    try:
        m = __import__(mod, fromlist=[cls])
        getattr(m, cls)
        print("  OK: Stage", i, mod + "." + cls)
        t5_ok += 1
    except Exception as e:
        print("  FAIL: Stage", i, mod + "." + cls, str(e)[:60])

# TEST 6: API Server Import
print("\n[TEST 6] API Server Import")
try:
    import titan_api
    print("  OK: titan_api version=" + str(getattr(titan_api, "__version__", "?")))
    t6_pass = True
except Exception as e:
    print("  FAIL:", str(e)[:80])
    t6_pass = False

# TEST 7: Ollama LLM Connectivity
print("\n[TEST 7] Ollama LLM Connectivity")
t7_pass = False
try:
    import requests
    r = requests.get("http://127.0.0.1:11434/api/tags", timeout=5)
    models = r.json().get("models", [])
    print("  OK: Ollama running,", len(models), "models")
    for m in models:
        print("    -", m.get("name", "?"), "(" + str(round(m.get("size", 0)/1e9, 1)) + " GB)")
    t7_pass = True
except Exception as e:
    print("  FAIL:", str(e)[:80])

# TEST 8: Session System
print("\n[TEST 8] Session System")
t8_pass = False
try:
    from titan_session import get_session, update_session
    s = get_session()
    print("  OK: version=" + s.get("version", "?"))
    update_session(current_target="__verify__")
    s2 = get_session()
    if s2.get("current_target") == "__verify__":
        print("  OK: read/write works")
        update_session(current_target="")
        t8_pass = True
    else:
        print("  FAIL: write not persisted")
except Exception as e:
    print("  FAIL:", str(e)[:80])

# VERDICT
print("\n" + "=" * 60)
print("VERDICT")
print("=" * 60)
tests = [
    ("110-Module Import", len(t1_fail) == 0, str(t1_ok) + "/" + str(len(files))),
    ("Bridge Subsystems", t2_ok == len(flags), str(t2_ok) + "/" + str(len(flags))),
    ("GUI Syntax", t3_ok == len(apps), str(t3_ok) + "/" + str(len(apps))),
    ("Orphan Imports", t4_ok == len(orphans), str(t4_ok) + "/" + str(len(orphans))),
    ("Forge Pipeline", t5_ok == len(forge), str(t5_ok) + "/" + str(len(forge))),
    ("API Server", t6_pass, "OK" if t6_pass else "FAIL"),
    ("Ollama LLM", t7_pass, "connected" if t7_pass else "down"),
    ("Session System", t8_pass, "OK" if t8_pass else "FAIL"),
]
all_pass = True
for name, passed, detail in tests:
    tag = "PASS" if passed else "FAIL"
    if not passed:
        all_pass = False
    print("  [" + tag + "] " + name + ": " + detail)

print()
if all_pass:
    print("  >>> ALL 8 TESTS PASSED — SYSTEM OPERATIONAL <<<")
else:
    fails = sum(1 for _, p, _ in tests if not p)
    print("  >>> " + str(fails) + " TEST(S) FAILED <<<")
print()
