#!/bin/bash
# Deploy etc config files + deep_verify.py from zip
set -e

echo "[*] Extracting etc config package..."
python3 << 'PYEOF'
import zipfile, os, shutil
zf = zipfile.ZipFile('/tmp/titan_v8_etc.zip', 'r')
d = '/tmp/titan_v8_etc'
if os.path.exists(d):
    shutil.rmtree(d)
os.makedirs(d)
count = 0
for info in zf.infolist():
    info.filename = info.filename.replace('\\', '/')
    zf.extract(info, d)
    count += 1
zf.close()
print(f"  Extracted {count} files")
PYEOF

echo "[*] Finding extracted files..."
find /tmp/titan_v8_etc -type f | head -30

# Deploy conky config
CONKY_SRC=$(find /tmp/titan_v8_etc -path "*/conky/titan.conf" | head -1)
if [ -n "$CONKY_SRC" ]; then
    mkdir -p /etc/conky
    cp -f "$CONKY_SRC" /etc/conky/titan.conf
    echo "  ✓ conky/titan.conf deployed"
fi

# Deploy neofetch config
NEO_SRC=$(find /tmp/titan_v8_etc -path "*/neofetch/config.conf" | head -1)
if [ -n "$NEO_SRC" ]; then
    mkdir -p /etc/neofetch
    cp -f "$NEO_SRC" /etc/neofetch/config.conf
    echo "  ✓ neofetch/config.conf deployed"
fi

# Deploy lightdm greeter
LDM_SRC=$(find /tmp/titan_v8_etc -path "*/lightdm-gtk-greeter.conf" | head -1)
if [ -n "$LDM_SRC" ]; then
    mkdir -p /etc/lightdm
    cp -f "$LDM_SRC" /etc/lightdm/lightdm-gtk-greeter.conf
    echo "  ✓ lightdm-gtk-greeter.conf deployed"
fi

# Deploy APT pin
APT_SRC=$(find /tmp/titan_v8_etc -path "*/00-titan-pin-stable" | head -1)
if [ -n "$APT_SRC" ]; then
    mkdir -p /etc/apt/preferences.d
    cp -f "$APT_SRC" /etc/apt/preferences.d/00-titan-pin-stable
    echo "  ✓ APT pin config deployed"
fi

# Deploy deep_verify.py
DV_SRC=$(find /tmp/titan_v8_etc -name "deep_verify.py" | head -1)
if [ -n "$DV_SRC" ]; then
    cp -f "$DV_SRC" /opt/titan/deep_verify.py
    chmod +x /opt/titan/deep_verify.py
    echo "  ✓ deep_verify.py deployed"
fi

# Cleanup
rm -rf /tmp/titan_v8_etc /tmp/titan_v8_etc.zip

echo ""
echo "  Config sync complete!"
