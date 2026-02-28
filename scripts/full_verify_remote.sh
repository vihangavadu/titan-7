#!/bin/bash
echo '=== DIRS ==='
for d in /opt/titan/core /opt/titan/apps /opt/titan/src/core /opt/titan/src/apps /opt/titan/scripts /opt/titan/training /opt/titan/docs /opt/titan/android; do
  if [ -d "$d" ]; then
    c=$(ls "$d" 2>/dev/null | wc -l)
    echo "FOUND:$d count:$c"
  else
    echo "MISSING:$d"
  fi
done

echo '=== ANDROID/MOBILE ==='
for f in /opt/titan/src/core/waydroid_sync.py /opt/titan/scripts/setup_waydroid_android.sh /opt/titan/scripts/deploy_android_vm.sh; do
  [ -e "$f" ] && echo "FOUND:$f" || echo "MISSING:$f"
done
waydroid status 2>/dev/null || echo "waydroid:not-running"

echo '=== DEV HUB SERVICE ==='
systemctl is-active titan-dev-hub 2>/dev/null || true
systemctl status titan-dev-hub --no-pager 2>&1 | tail -8

echo '=== LISTENING PORTS ==='
ss -tlnp 2>/dev/null | grep LISTEN | head -20

echo '=== DEV HUB HTTP ==='
curl -s --max-time 5 http://localhost:5000/ 2>&1 | head -5 || echo "no-response-5000"
curl -s --max-time 5 http://localhost:5000/api/health 2>&1 | head -5 || echo "no-response-api-health"

echo '=== CORE IMPORTS ==='
cd /opt/titan
export PYTHONPATH=/opt/titan:/opt/titan/src/core:/opt/titan/core:/opt/titan/apps
python3 -c "import integration_bridge; print('integration_bridge: OK')" 2>&1
python3 -c "import titan_session; print('titan_session: OK')" 2>&1
python3 -c "import titan_api; print('titan_api: OK')" 2>&1

echo '=== VERIFY_ALL ==='
cd /opt/titan
export PYTHONPATH=/opt/titan:/opt/titan/src/core:/opt/titan/core:/opt/titan/apps
python3 verify_all.py 2>&1

echo '=== DEV HUB IMPORT ==='
cd /opt/titan/apps
python3 -c "import py_compile; py_compile.compile('titan_dev_hub.py'); print('titan_dev_hub.py syntax: OK')" 2>&1

echo '=== DONE ==='
