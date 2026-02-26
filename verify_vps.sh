#!/bin/bash
export PYTHONPATH=/opt/titan:/opt/titan/core:/opt/titan/apps
cd /opt/titan

echo "=== CORE SYNTAX ==="
ok=0; fail=0; fails=""
for f in core/*.py; do
  python3 -c "import py_compile; py_compile.compile('$f', doraise=True)" 2>/dev/null && ok=$((ok+1)) || { fail=$((fail+1)); fails="$fails $f"; }
done
echo "OK:$ok FAIL:$fail"
[ -n "$fails" ] && echo "FAILED:$fails"

echo "=== APPS SYNTAX ==="
ok=0; fail=0; fails=""
for f in apps/*.py; do
  python3 -c "import py_compile; py_compile.compile('$f', doraise=True)" 2>/dev/null && ok=$((ok+1)) || { fail=$((fail+1)); fails="$fails $f"; }
done
echo "OK:$ok FAIL:$fail"
[ -n "$fails" ] && echo "FAILED:$fails"

echo "=== CORE IMPORTS ==="
ok=0; fail=0; fails=""
for f in core/*.py; do
  mod=$(basename "$f" .py)
  # skip __init__ and __pycache__
  [ "$mod" = "__init__" ] && continue
  [ "$mod" = "__pycache__" ] && continue
  python3 -c "import $mod" 2>/dev/null && ok=$((ok+1)) || { fail=$((fail+1)); fails="$fails $mod"; }
done
echo "OK:$ok FAIL:$fail"
[ -n "$fails" ] && echo "FAILED:$fails"

echo "=== SERVICES ==="
for svc in redis-server ollama xray ntfy; do
  status=$(systemctl is-active $svc 2>/dev/null)
  echo "$svc: $status"
done

echo "=== OLLAMA MODELS ==="
ollama list 2>/dev/null

echo "=== REDIS PING ==="
redis-cli ping 2>/dev/null

echo "=== DISK ==="
df -h / | tail -1

echo "=== HOSTNAME ==="
hostname

echo "=== PYTHON VERSION ==="
python3 --version

echo "=== FILE COUNTS ==="
echo "Core .py: $(ls core/*.py 2>/dev/null | wc -l)"
echo "Apps .py: $(ls apps/*.py 2>/dev/null | wc -l)"
echo "Config: $(ls config/ 2>/dev/null | wc -l)"
echo "Scripts: $(find scripts/ -name '*.py' -o -name '*.sh' 2>/dev/null | wc -l)"
echo "Training: $(find training/ -type f 2>/dev/null | wc -l)"
echo "Docs: $(find docs/ -name '*.md' 2>/dev/null | wc -l)"

echo "=== DONE ==="
