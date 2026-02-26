#!/bin/bash
echo "=== VPS APPS ==="
for f in /opt/titan/apps/*.py; do
  name=$(basename "$f")
  lines=$(wc -l < "$f")
  size=$(wc -c < "$f")
  echo "$name | lines=$lines | bytes=$size"
done

echo ""
echo "=== VPS APPS NOT IN LOCAL SRC ==="
echo "app_cerberus.py app_genesis.py app_unified.py titan_mission_control.py"

echo ""
echo "=== VPS CORE MODULE COUNT ==="
ls /opt/titan/core/*.py 2>/dev/null | wc -l

echo ""
echo "=== VPS APP IMPORT CHECK ==="
cd /opt/titan
for f in apps/*.py; do
  python3 -c "import ast; ast.parse(open('$f').read())" 2>&1 && echo "SYNTAX OK: $f" || echo "SYNTAX FAIL: $f"
done

echo ""
echo "=== VPS vs LOCAL APP SIZES ==="
for f in /opt/titan/apps/*.py; do
  name=$(basename "$f")
  echo "$name $(wc -c < $f)"
done

echo ""
echo "=== FEATURE SCAN: tabs/workers/routes in each app ==="
for f in /opt/titan/apps/titan_*.py /opt/titan/apps/app_*.py; do
  name=$(basename "$f")
  tabs=$(grep -c "addTab\|_build_.*_tab\|QTabWidget\|tab(" "$f" 2>/dev/null || echo 0)
  workers=$(grep -c "QThread\|Worker\|threading.Thread" "$f" 2>/dev/null || echo 0)
  imports=$(grep -c "^from \|^import " "$f" 2>/dev/null || echo 0)
  buttons=$(grep -c "QPushButton\|button\|btn" "$f" 2>/dev/null || echo 0)
  echo "$name | tabs=$tabs | workers=$workers | imports=$imports | buttons=$buttons"
done

echo ""
echo "=== EXTRA APPS ON VPS NOT IN LOCAL ==="
for extra in app_cerberus.py app_genesis.py app_unified.py titan_mission_control.py; do
  if [ -f "/opt/titan/apps/$extra" ]; then
    lines=$(wc -l < "/opt/titan/apps/$extra")
    head -5 "/opt/titan/apps/$extra"
    echo "--- ($extra: $lines lines) ---"
    echo ""
  fi
done

echo ""
echo "=== CORE MODULES WIRED TO GUI (grep from apps) ==="
grep -roh "from [a-z_]* import\|import [a-z_]*" /opt/titan/apps/*.py 2>/dev/null | sort -u | head -80

echo ""
echo "=== CORE MODULES NOT IMPORTED BY ANY APP ==="
for core in /opt/titan/core/*.py; do
  mod=$(basename "$core" .py)
  if [ "$mod" = "__init__" ]; then continue; fi
  found=$(grep -rl "$mod" /opt/titan/apps/*.py 2>/dev/null | wc -l)
  if [ "$found" -eq 0 ]; then
    echo "UNWIRED: $mod"
  fi
done
