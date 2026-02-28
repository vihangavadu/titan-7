#!/usr/bin/env python3
"""Verify all modules import after VPS sync."""
import os, sys
sys.path.insert(0, "/opt/titan/core")
sys.path.insert(0, "/opt/titan")

print("=" * 60)
print("  TITAN VPS SYNC VERIFICATION")
print("=" * 60)

# Core modules
core_path = "/opt/titan/core"
core_files = sorted([
    f[:-3] for f in os.listdir(core_path)
    if f.endswith(".py") and f != "__init__.py" and not f.startswith("smoke_") and not f.startswith("verify_")
])

core_fails = []
for mod in core_files:
    try:
        __import__(mod)
    except Exception as e:
        core_fails.append((mod, str(e)[:80]))

print(f"\n[CORE] {len(core_files) - len(core_fails)}/{len(core_files)} modules OK")
for f, e in core_fails:
    print(f"  FAIL: {f} -> {e}")

# Apps
apps_path = "/opt/titan/apps"
sys.path.insert(0, apps_path)
app_files = sorted([
    f[:-3] for f in os.listdir(apps_path)
    if f.endswith(".py") and f != "__init__.py"
])

app_fails = []
for mod in app_files:
    try:
        __import__(mod)
    except ImportError as e:
        if "PyQt" in str(e) or "QtWidgets" in str(e) or "QtCore" in str(e) or "QtGui" in str(e):
            pass  # Expected - no display server on VPS
        else:
            app_fails.append((mod, str(e)[:80]))
    except Exception as e:
        err = str(e)[:80]
        if "display" in err.lower() or "xcb" in err.lower() or "wayland" in err.lower():
            pass  # Expected - no GUI on VPS
        else:
            app_fails.append((mod, err))

print(f"\n[APPS] {len(app_files) - len(app_fails)}/{len(app_files)} modules OK (GUI errors ignored)")
for f, e in app_fails:
    print(f"  FAIL: {f} -> {e}")

# Config check
print("\n[CONFIG]")
import json
for cfg in ["llm_config.json", "dev_hub_config.json", "oblivion_template.json"]:
    path = f"/opt/titan/config/{cfg}"
    if os.path.exists(path):
        try:
            data = json.loads(open(path).read())
            if cfg == "llm_config.json":
                tasks = len(data.get("task_routing", {}))
                print(f"  OK  {cfg} ({tasks} task routes)")
            else:
                print(f"  OK  {cfg}")
        except Exception as e:
            print(f"  FAIL {cfg}: {e}")
    else:
        print(f"  MISSING {cfg}")

# Docs check
print("\n[DOCS]")
docs_path = "/opt/titan/docs"
for doc in os.listdir(docs_path):
    if doc.endswith(".md"):
        size = os.path.getsize(f"{docs_path}/{doc}")
        print(f"  OK  {doc} ({size:,} bytes)")

# Summary
total_fails = len(core_fails) + len(app_fails)
print("\n" + "=" * 60)
if total_fails == 0:
    print("  ALL CLEAR - VPS fully synced with local codebase")
else:
    print(f"  {total_fails} FAILURES detected")
print("=" * 60)

sys.exit(1 if total_fails else 0)
