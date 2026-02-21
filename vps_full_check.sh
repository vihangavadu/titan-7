#!/bin/bash
echo "=== DISK / MEMORY ==="
df -h /
free -h

echo ""
echo "=== OLLAMA STATUS ==="
systemctl is-active ollama 2>/dev/null || echo "inactive"
ollama list 2>/dev/null || echo "no-ollama-cli"

echo ""
echo "=== CORE MODULE COUNT ==="
ls /opt/titan/core/*.py | wc -l

echo ""
echo "=== CORE MODULE IMPORTS ==="
cd /opt/titan

python3 - <<'PYEOF'
import sys
sys.path.insert(0, "core")

tests = [
    ("target_discovery", "SITE_DATABASE"),
    ("three_ds_strategy", "NON_VBV_BINS"),
    ("genesis_core", "GenesisCore"),
    ("target_presets", "TARGET_PRESETS"),
    ("ollama_bridge", "generate_with_cache"),
    ("dynamic_data", "LLM_AVAILABLE"),
    ("forensic_monitor", "ForensicMonitor"),
]

passed = 0
failed = 0
for mod, attr in tests:
    try:
        m = __import__(mod)
        val = getattr(m, attr, "ATTR_MISSING")
        if val == "ATTR_MISSING":
            print(f"  WARN  {mod}.{attr} not found")
        else:
            if isinstance(val, bool):
                print(f"  OK    {mod} ({attr}={val})")
            elif isinstance(val, dict):
                print(f"  OK    {mod} ({attr}: {len(val)} entries)")
            elif isinstance(val, list):
                print(f"  OK    {mod} ({attr}: {len(val)} entries)")
            else:
                print(f"  OK    {mod} ({attr}: {type(val).__name__})")
        passed += 1
    except Exception as e:
        print(f"  FAIL  {mod}: {e}")
        failed += 1

print(f"\n  Result: {passed} passed, {failed} failed")
PYEOF

echo ""
echo "=== LLM ROUTING CHECK ==="
cd /opt/titan
python3 - <<'PYEOF'
import sys
sys.path.insert(0, "core")
from ollama_bridge import resolve_provider_for_task, get_provider_status

print("Provider status:")
for name, info in get_provider_status().items():
    avail = "AVAILABLE" if info["available"] else "unavailable"
    key = "has_key" if info["has_api_key"] else "no_key"
    print(f"  {name:12s}: {avail}, {key}")

print("\nTask routing:")
for task in ["bin_generation", "site_discovery", "preset_generation", "country_profiles", "dork_generation", "default"]:
    r = resolve_provider_for_task(task)
    if r:
        print(f"  {task:20s} -> {r[0]}/{r[1]}")
    else:
        print(f"  {task:20s} -> NO PROVIDER")
PYEOF

echo ""
echo "=== APP UNIFIED FORENSIC TAB ==="
grep -c "FORENSIC\|forensic" /opt/titan/apps/app_unified.py
grep -n "addTab.*FORENSIC\|_launch_forensic_monitor\|forensic_tab" /opt/titan/apps/app_unified.py | head -5

echo ""
echo "=== DATA CACHE DIRS ==="
ls -la /opt/titan/data/llm_cache/ /opt/titan/data/forensic_cache/

echo ""
echo "=== RECENT MODIFIED FILES ==="
find /opt/titan -name "*.py" -newer /opt/titan/core/genesis_core.py 2>/dev/null | sort

echo ""
echo "=== ALL CHECKS COMPLETE ==="
