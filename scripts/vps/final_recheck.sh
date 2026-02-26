#!/bin/bash
echo "=== FINAL OPERATOR RECHECK ==="
echo ""

echo "[1] APP COUNT + SYNTAX"
total=0; ok=0
for f in /opt/titan/apps/*.py; do
  total=$((total+1))
  python3 -m py_compile "$f" 2>/dev/null && ok=$((ok+1)) || echo "  SYNTAX FAIL: $(basename $f)"
done
echo "  Apps: $ok/$total syntax OK"

echo ""
echo "[2] CORE MODULE COUNT + IMPORT"
cd /opt/titan
core_total=0; core_ok=0; core_fail=""
for f in /opt/titan/core/*.py; do
  mod=$(basename "$f" .py)
  [ "$mod" = "__init__" ] && continue
  core_total=$((core_total+1))
  python3 -c "import $mod" 2>/dev/null && core_ok=$((core_ok+1)) || core_fail="$core_fail $mod"
done
echo "  Core: $core_ok/$core_total importable"
[ -n "$core_fail" ] && echo "  Failed:$core_fail"

echo ""
echo "[3] TAB + FEATURE COUNT PER APP"
for f in /opt/titan/apps/titan_*.py /opt/titan/apps/app_*.py; do
  name=$(basename "$f")
  tabs=$(grep -c "addTab\|_build_.*_tab" "$f" 2>/dev/null || echo 0)
  workers=$(grep -c "QThread\|Worker" "$f" 2>/dev/null || echo 0)
  imports=$(grep -c "^try:" "$f" 2>/dev/null || echo 0)
  echo "  $name | tabs=$tabs | workers=$workers | module_imports=$imports"
done

echo ""
echo "[4] PREVIOUSLY UNWIRED MODULES — NOW WIRED?"
for mod in biometric_mimicry chromium_cookie_engine level9_antidetect leveldb_writer titan_webhook_integrations; do
  found=$(grep -rl "$mod" /opt/titan/apps/*.py 2>/dev/null | wc -l)
  echo "  $mod: wired_in=$found apps"
done

echo ""
echo "[5] SERVICES"
for svc in redis-server ollama xray ntfy titan-dev-hub; do
  st=$(systemctl is-active $svc 2>/dev/null || echo "not-found")
  echo "  $svc: $st"
done

echo ""
echo "[6] DEV HUB API CONNECTOR ROUTES"
curl -s http://127.0.0.1:8877/api/health | python3 -m json.tool 2>/dev/null || echo "  dev-hub health: FAIL"

echo ""
echo "[7] TOTAL STATS"
echo "  Core modules: $core_total"
echo "  GUI apps (py): $total"
apps_tabs=$(grep -roh "addTab" /opt/titan/apps/*.py 2>/dev/null | wc -l)
echo "  Total tabs across all apps: $apps_tabs"
apps_workers=$(grep -roh "QThread" /opt/titan/apps/*.py 2>/dev/null | wc -l)
echo "  Total QThread workers: $apps_workers"

echo ""
echo "=== RECHECK COMPLETE ==="
