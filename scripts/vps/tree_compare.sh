#!/bin/bash
export PYTHONPATH="/opt/titan:/opt/titan/core:/opt/titan/apps"

echo "=========================================="
echo "LOCAL REPO vs VPS DEEP COMPARISON"
echo "=========================================="

# 1. Core modules: compare filenames
echo ""
echo "=== [1] CORE MODULES: local src/core vs VPS /opt/titan/core ==="
echo "VPS core .py files:"
ls -1 /opt/titan/core/*.py 2>/dev/null | xargs -I{} basename {} | sort > /tmp/vps_core.txt
wc -l < /tmp/vps_core.txt
echo "VPS src/core .py files:"
ls -1 /opt/titan/src/core/*.py 2>/dev/null | xargs -I{} basename {} | sort > /tmp/src_core.txt
wc -l < /tmp/src_core.txt

echo ""
echo "In VPS core but NOT in src/core:"
comm -23 /tmp/vps_core.txt /tmp/src_core.txt

echo ""
echo "In src/core but NOT in VPS core:"
comm -13 /tmp/vps_core.txt /tmp/src_core.txt

# 2. Apps: compare
echo ""
echo "=== [2] APPS: src/apps vs VPS /opt/titan/apps ==="
ls -1 /opt/titan/apps/*.py 2>/dev/null | xargs -I{} basename {} | sort > /tmp/vps_apps.txt
ls -1 /opt/titan/src/apps/*.py 2>/dev/null | xargs -I{} basename {} | sort > /tmp/src_apps.txt

echo "In VPS apps but NOT in src/apps:"
comm -23 /tmp/vps_apps.txt /tmp/src_apps.txt

echo ""
echo "In src/apps but NOT in VPS apps:"
comm -13 /tmp/vps_apps.txt /tmp/src_apps.txt

# 3. Scripts
echo ""
echo "=== [3] SCRIPTS ==="
ls -1 /opt/titan/scripts/*.py /opt/titan/scripts/*.sh 2>/dev/null | xargs -I{} basename {} | sort
echo "---"
echo "Total scripts: $(ls -1 /opt/titan/scripts/*.py /opt/titan/scripts/*.sh 2>/dev/null | wc -l)"

# 4. Config files
echo ""
echo "=== [4] CONFIG FILES ==="
find /opt/titan/config -maxdepth 1 -type f | sort

# 5. Bin scripts
echo ""
echo "=== [5] BIN SCRIPTS ==="
ls -1 /opt/titan/bin/ 2>/dev/null

# 6. Key directories presence
echo ""
echo "=== [6] KEY DIRECTORIES ==="
for d in core apps src src/core src/apps config scripts docs training tests bin branding modelfiles iso state profiles data android; do
  if [ -d "/opt/titan/$d" ]; then
    count=$(find "/opt/titan/$d" -maxdepth 1 -type f 2>/dev/null | wc -l)
    echo "  OK: /opt/titan/$d ($count top-level files)"
  else
    echo "  MISSING: /opt/titan/$d"
  fi
done

# 7. Size comparison between src/apps and live apps
echo ""
echo "=== [7] SIZE DIFF: src/apps vs apps (stale copies?) ==="
for f in /opt/titan/src/apps/*.py; do
  name=$(basename "$f")
  if [ -f "/opt/titan/apps/$name" ]; then
    s1=$(wc -c < "$f")
    s2=$(wc -c < "/opt/titan/apps/$name")
    if [ "$s1" != "$s2" ]; then
      echo "  STALE: $name (src=${s1}B live=${s2}B)"
    fi
  fi
done
echo "  (empty = all in sync)"

# 8. Module import test (quick, with PYTHONPATH)
echo ""
echo "=== [8] CORE IMPORT QUICK TEST ==="
cd /opt/titan
fail_count=0
fail_list=""
for f in /opt/titan/core/*.py; do
  mod=$(basename "$f" .py)
  [ "$mod" = "__init__" ] && continue
  python3 -c "import $mod" 2>/dev/null || { fail_count=$((fail_count+1)); fail_list="$fail_list $mod"; }
done
total=$(ls /opt/titan/core/*.py | wc -l)
total=$((total-1))
ok=$((total-fail_count))
echo "  $ok/$total importable"
[ -n "$fail_list" ] && echo "  Failed:$fail_list"

# 9. App syntax check
echo ""
echo "=== [9] APP SYNTAX CHECK ==="
app_fail=0
for f in /opt/titan/apps/*.py; do
  python3 -m py_compile "$f" 2>/dev/null || { echo "  FAIL: $(basename $f)"; app_fail=$((app_fail+1)); }
done
app_total=$(ls /opt/titan/apps/*.py | wc -l)
echo "  $((app_total-app_fail))/$app_total syntax OK"

# 10. AI model operational check
echo ""
echo "=== [10] AI MODELS OPERATIONAL ==="
for model in titan-analyst titan-strategist titan-fast; do
  echo -n "  $model: "
  resp=$(curl -s --max-time 30 http://127.0.0.1:11434/api/generate \
    -d "{\"model\":\"$model\",\"prompt\":\"What are your top 3 task domains?\",\"stream\":false,\"options\":{\"num_predict\":50,\"temperature\":0}}" 2>/dev/null)
  if [ -z "$resp" ]; then
    echo "TIMEOUT"
  else
    answer=$(echo "$resp" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('response','NO_RESP')[:150])" 2>/dev/null || echo "PARSE_ERR")
    eval_s=$(echo "$resp" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'{d.get(\"eval_duration\",0)/1e9:.1f}s')" 2>/dev/null || echo "?")
    echo "($eval_s) $answer"
  fi
done

echo ""
echo "=========================================="
echo "COMPARISON COMPLETE"
echo "=========================================="
