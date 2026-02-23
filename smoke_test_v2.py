#!/usr/bin/env python3
"""TITAN V8.11 — Smoke Test V2 (Auto-Discovery)
Dynamically discovers all classes in all modules, tries to instantiate them,
and reports results. No hardcoded class names.
"""
import os, sys, importlib, inspect, traceback, json, tempfile, shutil
sys.path.insert(0, "/opt/titan/core")
sys.path.insert(0, "/opt/titan")

PASS = 0
FAIL = 0
WARN = 0
SKIP = 0
results = []

def record(status, name, detail=""):
    global PASS, FAIL, WARN, SKIP
    if status == "PASS":
        PASS += 1
    elif status == "FAIL":
        FAIL += 1
    elif status == "WARN":
        WARN += 1
    elif status == "SKIP":
        SKIP += 1
    results.append((status, name, detail))

# ══════════════════════════════════════════════════════════════════
# PHASE 1: Auto-discover and instantiate every class in every module
# ══════════════════════════════════════════════════════════════════
core_dir = "/opt/titan/core"
files = sorted([f[:-3] for f in os.listdir(core_dir) if f.endswith(".py") and f != "__init__.py"])

total_classes = 0
instantiated = 0

for mod_name in files:
    try:
        mod = importlib.import_module(mod_name)
    except Exception as e:
        record("FAIL", f"{mod_name}: import", str(e)[:100])
        continue

    # Get classes defined in this module (not imported)
    classes = [(n, o) for n, o in inspect.getmembers(mod, inspect.isclass)
               if o.__module__ == mod_name and not n.startswith("_")]

    if not classes:
        # Module has no classes — check for functions
        funcs = [(n, o) for n, o in inspect.getmembers(mod, inspect.isfunction)
                 if o.__module__ == mod_name and not n.startswith("_")]
        if funcs:
            record("PASS", f"{mod_name}: {len(funcs)} functions (no classes)")
        else:
            record("PASS", f"{mod_name}: constants/config module")
        continue

    total_classes += len(classes)

    for cls_name, cls_obj in classes:
        # Skip Enum subclasses, dataclasses used as types, NamedTuples, Exceptions
        if issubclass(cls_obj, Exception):
            record("SKIP", f"{mod_name}.{cls_name}", "exception class")
            continue
        try:
            from enum import Enum
            if issubclass(cls_obj, Enum):
                members = list(cls_obj)
                record("PASS", f"{mod_name}.{cls_name}", f"Enum with {len(members)} members")
                instantiated += 1
                continue
        except TypeError:
            pass

        # Check if it's a dataclass
        import dataclasses
        if dataclasses.is_dataclass(cls_obj) and not isinstance(cls_obj, type):
            record("SKIP", f"{mod_name}.{cls_name}", "dataclass instance")
            continue
        if dataclasses.is_dataclass(cls_obj):
            # Try with no args — might have defaults
            try:
                obj = cls_obj()
                record("PASS", f"{mod_name}.{cls_name}", "dataclass (defaults)")
                instantiated += 1
                continue
            except TypeError:
                record("SKIP", f"{mod_name}.{cls_name}", "dataclass (needs args)")
                continue

        # Try to instantiate with no args
        try:
            obj = cls_obj()
            record("PASS", f"{mod_name}.{cls_name}", "instantiated OK")
            instantiated += 1
            continue
        except TypeError as te:
            # Needs arguments — try with common patterns
            te_str = str(te)
            if "missing" in te_str and "required positional argument" in te_str:
                # Count required args
                sig = inspect.signature(cls_obj.__init__)
                params = [(n, p) for n, p in sig.parameters.items()
                          if n != "self" and p.default is inspect.Parameter.empty]
                # Try to supply dummy args
                dummy_args = {}
                for pname, param in params:
                    ann = param.annotation
                    if ann == str or "str" in str(ann).lower() or "path" in pname.lower():
                        dummy_args[pname] = "/tmp/titan_smoke_test"
                    elif ann == dict or "config" in pname.lower() or "dict" in str(ann).lower():
                        dummy_args[pname] = {}
                    elif ann == int or "port" in pname.lower():
                        dummy_args[pname] = 0
                    elif ann == bool:
                        dummy_args[pname] = False
                    elif ann == list:
                        dummy_args[pname] = []
                    elif "page" in pname.lower():
                        dummy_args[pname] = None
                    elif "logger" in pname.lower():
                        import logging
                        dummy_args[pname] = logging.getLogger("smoke")
                    else:
                        dummy_args[pname] = None

                try:
                    obj = cls_obj(**dummy_args)
                    record("PASS", f"{mod_name}.{cls_name}", f"instantiated with {len(dummy_args)} dummy args")
                    instantiated += 1
                    continue
                except Exception as e2:
                    record("WARN", f"{mod_name}.{cls_name}", f"needs specific args: {str(e2)[:80]}")
                    continue
            else:
                record("WARN", f"{mod_name}.{cls_name}", f"TypeError: {te_str[:80]}")
                continue
        except Exception as e:
            tb = traceback.format_exc().strip().split("\n")[-1]
            record("WARN", f"{mod_name}.{cls_name}", f"{tb[:100]}")
            continue

# ══════════════════════════════════════════════════════════════════
# PHASE 2: Targeted functional tests for key modules
# ══════════════════════════════════════════════════════════════════

# Test 1: WebGL — all GPU profiles populated
try:
    from webgl_angle import WebGLAngleShim, GPUProfile, GPU_PROFILES, WebGLParams
    missing = [p.name for p in GPUProfile if p not in GPU_PROFILES]
    if missing:
        record("FAIL", "FUNC: webgl GPU profiles", f"Missing: {missing}")
    else:
        config = WebGLAngleShim().generate_webgl_config(gpu_profile=GPUProfile.ANGLE_D3D11)
        record("PASS", "FUNC: webgl GPU profiles", f"{len(GPU_PROFILES)} profiles, config={type(config).__name__}")
except Exception as e:
    record("FAIL", "FUNC: webgl GPU profiles", str(e)[:100])

# Test 2: LevelDB — full write cycle
try:
    from leveldb_writer import LevelDBWriter
    tmpdir = tempfile.mkdtemp(prefix="titan_ldb_")
    try:
        with LevelDBWriter(tmpdir) as w:
            ok1 = w.write_origin_data("https://test.com", {"k1": "v1", "k2": "v2"})
            ok2 = w.write_commerce_anchors("https://shop.com", "shopify")
            snap = os.path.join(tmpdir, "local_storage_simulated.json")
            data = json.load(open(snap))
            assert "https://test.com" in data and "https://shop.com" in data
            record("PASS", "FUNC: leveldb write+commerce", f"wrote {w.stats['write_count']} keys")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
except Exception as e:
    record("FAIL", "FUNC: leveldb write+commerce", str(e)[:100])

# Test 3: Session — read/write/update
try:
    from titan_session import get_session, update_session
    s = get_session()
    assert s.get("version") == "8.11.0"
    update_session(current_target="__smoke_v2__")
    s2 = get_session()
    assert s2["current_target"] == "__smoke_v2__"
    update_session(current_target="")
    record("PASS", "FUNC: session read/write", f"v{s['version']}, {len(s)} keys")
except Exception as e:
    record("FAIL", "FUNC: session read/write", str(e)[:100])

# Test 4: Integration bridge — subsystem count
try:
    from integration_bridge import TitanIntegrationBridge
    bridge = TitanIntegrationBridge(config={})
    init_methods = [m for m in dir(bridge) if m.startswith("_init_") and callable(getattr(bridge, m))]
    api_methods = [m for m in dir(bridge) if not m.startswith("_") and callable(getattr(bridge, m))]
    record("PASS", "FUNC: integration bridge", f"{len(init_methods)} subsystems, {len(api_methods)} API methods")
except Exception as e:
    record("FAIL", "FUNC: integration bridge", str(e)[:100])

# Test 5: Realtime copilot — all phases
try:
    from titan_realtime_copilot import OperatorPhase
    expected = ["IDLE", "CONFIGURING", "PRE_FLIGHT", "BROWSING", "WARMING_UP",
                "APPROACHING_CHECKOUT", "CHECKOUT", "ENTERING_SHIPPING",
                "ENTERING_PAYMENT", "REVIEWING_ORDER", "PROCESSING",
                "THREE_DS", "ORDER_COMPLETE", "COMPLETED"]
    missing = [p for p in expected if not hasattr(OperatorPhase, p)]
    if missing:
        record("FAIL", "FUNC: copilot phases", f"Missing: {missing}")
    else:
        record("PASS", "FUNC: copilot phases", f"{len(expected)} phases verified")
except Exception as e:
    record("FAIL", "FUNC: copilot phases", str(e)[:100])

# Test 6: Time safety validator report
try:
    from time_safety_validator import SafetyValidator
    sv = SafetyValidator()
    report = sv.get_validation_report()
    assert isinstance(report, dict) and "status" in report
    record("PASS", "FUNC: time safety report", f"status={report['status']}")
except Exception as e:
    record("FAIL", "FUNC: time safety report", str(e)[:100])

# Test 7: NTP isolation state
try:
    from ntp_isolation import IsolationManager
    im = IsolationManager()
    assert isinstance(im.isolation_state, dict)
    assert "w32time_original" in im.isolation_state
    record("PASS", "FUNC: ntp isolation state", f"{len(im.isolation_state)} state keys")
except Exception as e:
    record("FAIL", "FUNC: ntp isolation state", str(e)[:100])

# Test 8: App syntax compilation
try:
    import py_compile
    apps_dir = "/opt/titan/apps"
    app_files = sorted([f for f in os.listdir(apps_dir) if f.endswith(".py")])
    for af in app_files:
        py_compile.compile(os.path.join(apps_dir, af), doraise=True)
    record("PASS", "FUNC: all apps compile", f"{len(app_files)} app files")
except Exception as e:
    record("FAIL", "FUNC: app compilation", str(e)[:100])

# ══════════════════════════════════════════════════════════════════
# RESULTS
# ══════════════════════════════════════════════════════════════════
print("=" * 72)
print("TITAN V8.11 SMOKE TEST V2 RESULTS")
print("=" * 72)

# Print failures and warnings first
fails = [(s, n, d) for s, n, d in results if s == "FAIL"]
warns = [(s, n, d) for s, n, d in results if s == "WARN"]
passes = [(s, n, d) for s, n, d in results if s == "PASS"]
skips = [(s, n, d) for s, n, d in results if s == "SKIP"]

if fails:
    print(f"\n--- FAILURES ({len(fails)}) ---")
    for s, n, d in fails:
        print(f"  [!] {n}: {d}")

if warns:
    print(f"\n--- WARNINGS ({len(warns)}) ---")
    for s, n, d in warns:
        print(f"  [~] {n}: {d}")

print(f"\n--- PASSES ({len(passes)}) ---")
for s, n, d in passes:
    detail = f" -> {d}" if d else ""
    print(f"  [+] {n}{detail}")

print(f"\n--- SKIPPED ({len(skips)}) ---")
for s, n, d in skips:
    print(f"  [-] {n}: {d}")

print()
print("=" * 72)
print(f"MODULES: {len(files)} | CLASSES FOUND: {total_classes} | INSTANTIATED: {instantiated}")
print(f"TESTS: {PASS + FAIL + WARN + SKIP} | PASS: {PASS} | WARN: {WARN} | FAIL: {FAIL} | SKIP: {SKIP}")
if FAIL == 0:
    pct = round(PASS / max(PASS + WARN, 1) * 100, 1)
    print(f"VERDICT: ALL CRITICAL TESTS PASSED ({pct}% clean)")
else:
    print(f"VERDICT: {FAIL} CRITICAL FAILURES")
print("=" * 72)
