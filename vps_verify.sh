#!/bin/bash
echo "=== FILE VERIFICATION ==="
ls -lh /opt/titan/core/ollama_bridge.py \
        /opt/titan/core/dynamic_data.py \
        /opt/titan/core/forensic_monitor.py \
        /opt/titan/config/llm_config.json \
        /opt/titan/apps/forensic_widget.py \
        /opt/titan/apps/launch_forensic_monitor.py \
        /opt/titan/apps/app_unified.py 2>&1

echo ""
echo "=== IMPORT TEST: ollama_bridge ==="
cd /opt/titan && python3 - <<'PYEOF'
import sys
sys.path.insert(0, "core")
from ollama_bridge import is_ollama_available, get_provider_status, resolve_provider_for_task
print("ollama_bridge: OK")
print("LLM available:", is_ollama_available())
status = get_provider_status()
for k, v in status.items():
    print(f"  {k}: enabled={v['enabled']}, has_key={v['has_api_key']}, available={v['available']}")
print()
for task in ["bin_generation", "site_discovery", "preset_generation", "default"]:
    r = resolve_provider_for_task(task)
    print(f"  routing {task} -> {r[0]}/{r[1]}" if r else f"  routing {task} -> no provider")
PYEOF

echo ""
echo "=== IMPORT TEST: dynamic_data ==="
cd /opt/titan && python3 - <<'PYEOF'
import sys
sys.path.insert(0, "core")
from dynamic_data import LLM_AVAILABLE, OLLAMA_AVAILABLE
print("dynamic_data: OK")
print("LLM_AVAILABLE:", LLM_AVAILABLE)
print("OLLAMA_AVAILABLE (compat):", OLLAMA_AVAILABLE)
PYEOF

echo ""
echo "=== IMPORT TEST: forensic_monitor ==="
cd /opt/titan && python3 - <<'PYEOF'
import sys
sys.path.insert(0, "core")
from forensic_monitor import ForensicMonitor
m = ForensicMonitor()
print("forensic_monitor: OK")
print("cache_dir:", m.cache_dir)
print("scan_interval:", m.scan_interval, "seconds")
PYEOF

echo ""
echo "=== APP UNIFIED LINE COUNT ==="
wc -l /opt/titan/apps/app_unified.py

echo ""
echo "=== FORENSIC TAB CHECK ==="
grep -n "FORENSIC\|forensic_monitor\|_launch_forensic" /opt/titan/apps/app_unified.py | head -10

echo ""
echo "=== LLM CONFIG CHECK ==="
python3 -c "import json; cfg=json.load(open('/opt/titan/config/llm_config.json')); print('providers:', list(cfg['providers'].keys())); print('task_routing:', list(cfg['task_routing'].keys()))"

echo ""
echo "=== DATA DIRS ==="
mkdir -p /opt/titan/data/llm_cache /opt/titan/data/forensic_cache
ls -la /opt/titan/data/

echo ""
echo "=== ALL CHECKS COMPLETE ==="
