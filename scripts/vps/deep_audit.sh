#!/bin/bash
export PYTHONPATH="/opt/titan:/opt/titan/core:/opt/titan/apps"

echo "=========================================="
echo "TITAN OS DEEP AUDIT — $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "=========================================="

# ── 1. CORE MODULE IMPORT CHECK ──
echo ""
echo "=== [1] CORE MODULE IMPORT CHECK ==="
cd /opt/titan
core_total=0; core_ok=0; core_fail=""
for f in /opt/titan/core/*.py; do
  mod=$(basename "$f" .py)
  [ "$mod" = "__init__" ] && continue
  core_total=$((core_total+1))
  python3 -c "import $mod" 2>/dev/null && core_ok=$((core_ok+1)) || core_fail="$core_fail $mod"
done
echo "  Core: $core_ok/$core_total importable"
[ -n "$core_fail" ] && echo "  FAILED:$core_fail"

# ── 2. AI MODELS CHECK ──
echo ""
echo "=== [2] OLLAMA AI MODELS ==="
echo "-- Installed models --"
ollama list 2>/dev/null || echo "  ollama not running"
echo ""
echo "-- Model response test --"
for model in titan-analyst titan-strategist titan-fast; do
  echo -n "  $model: "
  start=$(date +%s%N)
  resp=$(curl -s --max-time 30 http://127.0.0.1:11434/api/generate -d "{\"model\":\"$model\",\"prompt\":\"What is your primary role? Answer in one sentence.\",\"stream\":false}" 2>/dev/null)
  end=$(date +%s%N)
  ms=$(( (end - start) / 1000000 ))
  answer=$(echo "$resp" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('response','NO RESPONSE')[:120])" 2>/dev/null || echo "PARSE_ERROR")
  echo "${ms}ms | $answer"
done

# ── 3. AI TASK ROUTING (llm_config.json) ──
echo ""
echo "=== [3] AI TASK ROUTING CONFIG ==="
if [ -f /opt/titan/config/llm_config.json ]; then
  python3 -c "
import json
cfg = json.load(open('/opt/titan/config/llm_config.json'))
if isinstance(cfg, dict):
    routes = cfg.get('task_routing', cfg.get('routes', cfg))
    if isinstance(routes, dict):
        for task, model in sorted(routes.items()):
            m = model if isinstance(model, str) else model.get('model', str(model))
            print(f'  {task:40s} → {m}')
    elif isinstance(routes, list):
        for r in routes[:25]:
            print(f'  {r}')
    else:
        print(json.dumps(cfg, indent=2)[:800])
else:
    print(json.dumps(cfg, indent=2)[:800])
"
else
  echo "  llm_config.json NOT FOUND"
  # Check alternative locations
  for p in /opt/titan/llm_config.json /opt/titan/config/ai_config.json /opt/titan/config/models.json; do
    [ -f "$p" ] && echo "  Found: $p" && head -20 "$p"
  done
fi

# ── 4. LOCAL vs VPS FILE TREE DIFF ──
echo ""
echo "=== [4] VPS FILE TREE INVENTORY ==="

echo "-- /opt/titan/core/ (.py count) --"
core_count=$(ls /opt/titan/core/*.py 2>/dev/null | wc -l)
echo "  $core_count .py files"

echo "-- /opt/titan/apps/ (.py count) --"
apps_count=$(ls /opt/titan/apps/*.py 2>/dev/null | wc -l)
echo "  $apps_count .py files"

echo "-- /opt/titan/scripts/ --"
scripts_count=$(ls /opt/titan/scripts/ 2>/dev/null | wc -l)
echo "  $scripts_count files"
ls -1 /opt/titan/scripts/ 2>/dev/null || echo "  MISSING"

echo "-- /opt/titan/docs/ --"
docs_count=$(find /opt/titan/docs/ -type f 2>/dev/null | wc -l)
echo "  $docs_count files"

echo "-- /opt/titan/training/ --"
training_count=$(find /opt/titan/training/ -type f 2>/dev/null | wc -l)
echo "  $training_count files"

echo "-- /opt/titan/tests/ --"
tests_count=$(find /opt/titan/tests/ -type f 2>/dev/null | wc -l)
echo "  $tests_count files"

echo "-- /opt/titan/config/ --"
ls -la /opt/titan/config/ 2>/dev/null || echo "  MISSING"

echo "-- /opt/titan/src/core/ --"
src_core=$(ls /opt/titan/src/core/*.py 2>/dev/null | wc -l)
echo "  $src_core .py files"

echo "-- /opt/titan/src/apps/ --"
src_apps=$(ls /opt/titan/src/apps/*.py 2>/dev/null | wc -l)
echo "  $src_apps .py files"

echo "-- /opt/titan/bin/ --"
ls -1 /opt/titan/bin/ 2>/dev/null || echo "  MISSING"

echo "-- /opt/titan/branding/ --"
ls -1 /opt/titan/branding/ 2>/dev/null || echo "  MISSING"

echo "-- /opt/titan/modelfiles/ --"
ls -1 /opt/titan/modelfiles/ 2>/dev/null || echo "  MISSING"

# ── 5. MISSING FILES CHECK ──
echo ""
echo "=== [5] MISSING CRITICAL FILES ==="
critical_files=(
  "/opt/titan/core/__init__.py"
  "/opt/titan/core/titan_api.py"
  "/opt/titan/core/integration_bridge.py"
  "/opt/titan/core/titan_session.py"
  "/opt/titan/core/titan_env.py"
  "/opt/titan/apps/titan_launcher.py"
  "/opt/titan/apps/titan_operations.py"
  "/opt/titan/apps/titan_intelligence.py"
  "/opt/titan/apps/titan_network.py"
  "/opt/titan/apps/titan_admin.py"
  "/opt/titan/apps/titan_dev_hub.py"
  "/opt/titan/apps/app_profile_forge.py"
  "/opt/titan/apps/app_card_validator.py"
  "/opt/titan/apps/app_kyc.py"
  "/opt/titan/apps/app_browser_launch.py"
  "/opt/titan/apps/app_settings.py"
  "/opt/titan/apps/app_bug_reporter.py"
  "/opt/titan/config/llm_config.json"
  "/opt/titan/config/titan.env"
  "/opt/titan/config/dev_hub_config.json"
  "/opt/titan/bin/titan-browser"
  "/opt/titan/bin/titan-first-boot"
)
missing=0
for f in "${critical_files[@]}"; do
  if [ ! -f "$f" ]; then
    echo "  MISSING: $f"
    missing=$((missing+1))
  fi
done
[ $missing -eq 0 ] && echo "  All critical files present"

# ── 6. SERVICES + PORTS ──
echo ""
echo "=== [6] SERVICES & PORTS ==="
for svc in redis-server ollama xray ntfy titan-dev-hub; do
  st=$(systemctl is-active $svc 2>/dev/null || echo "not-found")
  echo "  $svc: $st"
done
echo ""
echo "-- Open ports --"
ss -tlnp 2>/dev/null | grep -E "LISTEN" | awk '{print "  " $4 " " $6}' | head -20

# ── 7. DISK + MEMORY ──
echo ""
echo "=== [7] RESOURCES ==="
df -h / | tail -1 | awk '{print "  Disk: " $3 " used / " $2 " total (" $5 " used)"}'
free -h | head -2 | tail -1 | awk '{print "  RAM: " $3 " used / " $2 " total"}'

echo ""
echo "=== DEEP AUDIT COMPLETE ==="
