#!/bin/bash
export PYTHONPATH=/opt/titan:/opt/titan/core:/opt/titan/apps
cd /opt/titan

echo "=== APPS IMPORT CHECK ==="
ok=0; fail=0
for f in apps/*.py; do
  mod=$(basename "$f" .py)
  [ "$mod" = "__init__" ] && continue
  [ "$mod" = "__pycache__" ] && continue
  result=$(python3 -c "import $mod" 2>&1)
  if [ $? -eq 0 ]; then
    ok=$((ok+1))
  else
    fail=$((fail+1))
    short=$(echo "$result" | tail -1 | cut -c1-120)
    echo "  FAIL: $mod -> $short"
  fi
done
echo "APPS: OK=$ok FAIL=$fail"

echo ""
echo "=== CORE IMPORT CHECK ==="
ok=0; fail=0
for f in core/*.py; do
  mod=$(basename "$f" .py)
  [ "$mod" = "__init__" ] && continue
  [ "$mod" = "__pycache__" ] && continue
  result=$(python3 -c "import $mod" 2>&1)
  if [ $? -eq 0 ]; then
    ok=$((ok+1))
  else
    fail=$((fail+1))
    short=$(echo "$result" | tail -1 | cut -c1-120)
    echo "  FAIL: $mod -> $short"
  fi
done
echo "CORE: OK=$ok FAIL=$fail"

echo ""
echo "=== QUICK SERVICE CHECK ==="
for svc in redis-server ollama xray ntfy; do
  echo "  $svc: $(systemctl is-active $svc 2>/dev/null)"
done

echo ""
echo "=== OLLAMA LIST ==="
ollama list 2>/dev/null

echo ""
echo "=== ALL DONE ==="
