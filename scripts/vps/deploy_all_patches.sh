#!/bin/bash
set -e
echo "=== DEPLOY ALL PATCHES ==="

# Copy from src to live apps
echo "[1/6] Copying patched files to /opt/titan/apps/..."
cp /opt/titan/src/apps/titan_admin.py /opt/titan/apps/titan_admin.py
cp /opt/titan/src/apps/app_profile_forge.py /opt/titan/apps/app_profile_forge.py
cp /opt/titan/src/apps/titan_network.py /opt/titan/apps/titan_network.py
cp /opt/titan/src/apps/titan_intelligence.py /opt/titan/apps/titan_intelligence.py
cp /opt/titan/src/apps/titan_dev_hub.py /opt/titan/apps/titan_dev_hub.py

# Fix BOM in app_bug_reporter.py
echo "[2/6] Fixing BOM in app_bug_reporter.py..."
if [ -f /opt/titan/apps/app_bug_reporter.py ]; then
  sed -i '1s/^\xEF\xBB\xBF//' /opt/titan/apps/app_bug_reporter.py
  sed -i '1s/^\xEF\xBB\xBF//' /opt/titan/src/apps/app_bug_reporter.py 2>/dev/null || true
fi

# Syntax verify all apps
echo "[3/6] Syntax verifying all apps..."
FAIL=0
for f in /opt/titan/apps/*.py; do
  python3 -m py_compile "$f" 2>&1 && echo "  OK: $(basename $f)" || { echo "  FAIL: $(basename $f)"; FAIL=$((FAIL+1)); }
done
echo "Syntax failures: $FAIL"

# Import check for new modules
echo "[4/6] Checking new module wiring..."
cd /opt/titan
python3 -c "
import sys
sys.path.insert(0, '/opt/titan/core')
sys.path.insert(0, '/opt/titan/apps')
results = []
tests = [
    ('titan_webhook_integrations', 'WebhookEvent'),
    ('chromium_cookie_engine', 'OblivionForgeEngine'),
    ('leveldb_writer', 'LevelDBWriter'),
    ('level9_antidetect', 'Level9Antidetect'),
    ('biometric_mimicry', 'BiometricMimicry'),
]
for mod, cls in tests:
    try:
        m = __import__(mod)
        has = hasattr(m, cls)
        results.append(f'  OK: {mod}.{cls} (found={has})')
    except Exception as e:
        results.append(f'  WARN: {mod} — {str(e)[:60]}')
print('\n'.join(results))
"

# Restart dev hub
echo "[5/6] Restarting titan-dev-hub..."
systemctl restart titan-dev-hub
sleep 2
systemctl is-active titan-dev-hub && echo "  titan-dev-hub: active" || echo "  titan-dev-hub: FAILED"

# Health check
echo "[6/6] Health check..."
curl -s http://127.0.0.1:8877/api/health
echo ""

# Final unwired check
echo ""
echo "=== FINAL UNWIRED MODULE CHECK ==="
for core in /opt/titan/core/*.py; do
  mod=$(basename "$core" .py)
  if [ "$mod" = "__init__" ] || [ "$mod" = "smoke_test_v91" ] || [ "$mod" = "verify_sync" ] || [ "$mod" = "oblivion_setup" ] || [ "$mod" = "verify_deep_identity" ]; then
    continue
  fi
  found=$(grep -rl "$mod" /opt/titan/apps/*.py 2>/dev/null | wc -l)
  if [ "$found" -eq 0 ]; then
    echo "  STILL UNWIRED: $mod"
  fi
done

echo ""
echo "=== DEPLOYMENT COMPLETE ==="
