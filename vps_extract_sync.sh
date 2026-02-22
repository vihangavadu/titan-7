#!/bin/bash
# Extract V8.0 sync zip and deploy to /opt/titan
set -e

echo "[*] Extracting V8.0 sync package..."

# Use Python to handle Windows backslash paths in zip
python3 << 'PYEOF'
import zipfile, os, shutil

zf = zipfile.ZipFile('/tmp/titan_v8_sync.zip', 'r')
extract_dir = '/tmp/titan_v8_extract'
if os.path.exists(extract_dir):
    shutil.rmtree(extract_dir)
os.makedirs(extract_dir)

count = 0
for info in zf.infolist():
    fixed = info.filename.replace('\\', '/')
    info.filename = fixed
    zf.extract(info, extract_dir)
    count += 1
zf.close()
print(f"  Extracted {count} files")
PYEOF

echo "[*] Finding core and apps directories..."

# Find the core and apps dirs (they may be nested)
CORE_DIR=$(find /tmp/titan_v8_extract -type d -name "core" | head -1)
APPS_DIR=$(find /tmp/titan_v8_extract -type d -name "apps" | head -1)

echo "  Core: $CORE_DIR"
echo "  Apps: $APPS_DIR"

# Backup current
echo "[*] Backing up current modules..."
BACKUP="/opt/titan/backups/pre_v8_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP"
cp -r /opt/titan/core "$BACKUP/" 2>/dev/null || true
cp -r /opt/titan/apps "$BACKUP/" 2>/dev/null || true
echo "  Backup: $BACKUP"

# Deploy core modules
if [ -n "$CORE_DIR" ] && [ -d "$CORE_DIR" ]; then
    echo "[*] Deploying core modules..."
    CORE_COUNT=$(find "$CORE_DIR" -name "*.py" | wc -l)
    cp -f "$CORE_DIR"/*.py /opt/titan/core/ 2>/dev/null || true
    echo "  Deployed $CORE_COUNT core Python files"
else
    echo "[!] Core directory not found in archive"
fi

# Deploy apps
if [ -n "$APPS_DIR" ] && [ -d "$APPS_DIR" ]; then
    echo "[*] Deploying apps..."
    APPS_COUNT=$(find "$APPS_DIR" -name "*.py" | wc -l)
    cp -f "$APPS_DIR"/*.py /opt/titan/apps/ 2>/dev/null || true
    echo "  Deployed $APPS_COUNT app Python files"
else
    echo "[!] Apps directory not found in archive"
fi

# Set permissions
echo "[*] Setting permissions..."
chmod +x /opt/titan/core/*.py 2>/dev/null || true
chmod +x /opt/titan/apps/*.py 2>/dev/null || true
chown -R root:root /opt/titan/core /opt/titan/apps 2>/dev/null || true

# Verify key files
echo ""
echo "═══════════════════════════════════════════════════"
echo "  V8.0 MODULE SYNC VERIFICATION"
echo "═══════════════════════════════════════════════════"
echo ""

# Check version in __init__.py
if grep -q "8.0" /opt/titan/core/__init__.py 2>/dev/null; then
    echo "  ✓ core/__init__.py: V8.0 present"
else
    echo "  ✗ core/__init__.py: V8.0 NOT found"
fi

# Check app_unified.py
if grep -q "V8.0" /opt/titan/apps/app_unified.py 2>/dev/null; then
    echo "  ✓ apps/app_unified.py: V8.0 present"
else
    echo "  ✗ apps/app_unified.py: V8.0 NOT found"
fi

# Check app_genesis.py
if grep -q "V8.0" /opt/titan/apps/app_genesis.py 2>/dev/null; then
    echo "  ✓ apps/app_genesis.py: V8.0 present"
else
    echo "  ✗ apps/app_genesis.py: V8.0 NOT found"
fi

# Check app_cerberus.py
if grep -q "V8.0" /opt/titan/apps/app_cerberus.py 2>/dev/null; then
    echo "  ✓ apps/app_cerberus.py: V8.0 present"
else
    echo "  ✗ apps/app_cerberus.py: V8.0 NOT found"
fi

# Check app_kyc.py
if grep -q "V8.0" /opt/titan/apps/app_kyc.py 2>/dev/null; then
    echo "  ✓ apps/app_kyc.py: V8.0 present"
else
    echo "  ✗ apps/app_kyc.py: V8.0 NOT found"
fi

# Check enterprise theme
if grep -q "V8.0" /opt/titan/apps/titan_enterprise_theme.py 2>/dev/null; then
    echo "  ✓ apps/titan_enterprise_theme.py: V8.0 present"
else
    echo "  ✗ apps/titan_enterprise_theme.py: V8.0 NOT found"
fi

# Check titan_api.py
if grep -q "8.0" /opt/titan/core/titan_api.py 2>/dev/null; then
    echo "  ✓ core/titan_api.py: V8.0 present"
else
    echo "  ✗ core/titan_api.py: V8.0 NOT found"
fi

# Check no Debian in key files
DEBIAN_HITS=$(grep -rli "debian\|bookworm" /opt/titan/core/font_sanitizer.py /opt/titan/core/canvas_subpixel_shim.py /opt/titan/core/immutable_os.py /opt/titan/core/kill_switch.py /opt/titan/core/verify_deep_identity.py 2>/dev/null | wc -l)
if [ "$DEBIAN_HITS" -eq 0 ]; then
    echo "  ✓ Core modules: No debian/bookworm references"
else
    echo "  ✗ Core modules: $DEBIAN_HITS files still have debian refs"
fi

# Module counts
CORE_FINAL=$(ls /opt/titan/core/*.py 2>/dev/null | wc -l)
APPS_FINAL=$(ls /opt/titan/apps/*.py 2>/dev/null | wc -l)
echo ""
echo "  Total: $CORE_FINAL core modules, $APPS_FINAL app modules"

# Cleanup
rm -rf /tmp/titan_v8_extract /tmp/titan_v8_sync.zip

echo ""
echo "═══════════════════════════════════════════════════"
echo "  V8.0 MODULE SYNC COMPLETE"
echo "═══════════════════════════════════════════════════"
