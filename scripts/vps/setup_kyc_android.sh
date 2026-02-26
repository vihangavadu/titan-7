#!/bin/bash
set -e
echo "=== SETUP KYC ANDROID MODULE ==="

# 1. Deploy KYC console + CLI wrapper
echo "[1] Deploying KYC Android console..."
python3 -m py_compile /opt/titan/android/kyc_android_console.py && echo "  Syntax OK" || echo "  SYNTAX FAIL"

cat > /usr/local/bin/titan-android << 'WRAPPER'
#!/bin/bash
export PYTHONPATH="/opt/titan:/opt/titan/core:/opt/titan/apps"
exec python3 /opt/titan/android/kyc_android_console.py "$@"
WRAPPER
chmod +x /usr/local/bin/titan-android
echo "  CLI wrapper: /usr/local/bin/titan-android"

# 2. Configure device properties (Pixel 7 default)
echo ""
echo "[2] Setting device properties..."
mkdir -p /var/lib/waydroid
cat > /var/lib/waydroid/waydroid_base.prop << 'PROPS'
ro.product.model=Pixel 7
ro.product.brand=google
ro.product.name=panther
ro.product.device=panther
ro.product.manufacturer=Google
ro.build.fingerprint=google/panther/panther:14/AP2A.240805.005/12025142:user/release-keys
ro.build.version.release=14
ro.build.version.sdk=34
ro.build.version.security_patch=2024-08-05
ro.sf.lcd_density=420
persist.sys.timezone=America/New_York
persist.sys.locale=en_US
ro.kernel.qemu=0
ro.hardware.virtual=0
ro.debuggable=0
ro.secure=1
ro.hardware.chipname=exynos2400
gsm.version.baseband=1.0
init.svc.adbd=stopped
ro.build.tags=release-keys
ro.build.type=user
persist.sys.usb.config=none
PROPS
echo "  Device: Pixel 7 (panther) Android 14"

# 3. Configure networking
echo ""
echo "[3] Configuring networking..."
sysctl -w net.ipv4.ip_forward=1 > /dev/null 2>&1
echo "net.ipv4.ip_forward=1" > /etc/sysctl.d/99-titan-waydroid.conf 2>/dev/null || true
iptables -t nat -C POSTROUTING -s 192.168.240.0/24 -o eth0 -j MASQUERADE 2>/dev/null || \
    iptables -t nat -A POSTROUTING -s 192.168.240.0/24 -o eth0 -j MASQUERADE 2>/dev/null || true
echo "  IP forwarding + NAT configured"

# 4. Create systemd service
echo ""
echo "[4] Creating systemd service..."
cat > /etc/systemd/system/titan-waydroid.service << 'SVC'
[Unit]
Description=TITAN OS — Waydroid Android Container
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStartPre=/usr/bin/waydroid container start
ExecStart=/usr/bin/waydroid session start
ExecStop=/usr/bin/waydroid session stop
ExecStopPost=/usr/bin/waydroid container stop
TimeoutStartSec=60

[Install]
WantedBy=multi-user.target
SVC
systemctl daemon-reload
systemctl enable titan-waydroid.service 2>/dev/null || true
echo "  Service: titan-waydroid.service (enabled)"

# 5. Create asset directories
echo ""
echo "[5] Creating asset directories..."
mkdir -p /opt/titan/android/assets/faces
mkdir -p /opt/titan/android/assets/documents
mkdir -p /opt/titan/android/assets/motions
mkdir -p /opt/titan/android/screenshots
echo "  Directories created"

# 6. Try starting Android
echo ""
echo "[6] Starting Android container..."
waydroid container start 2>&1 | tail -3 || echo "  Container start had issues"
sleep 2
waydroid session start 2>&1 | tail -3 || echo "  Session start had issues"
sleep 5

# 7. Verification
echo ""
echo "[7] VERIFICATION..."
PASS=0; FAIL=0
check() {
    if eval "$1" 2>/dev/null; then
        echo "  OK: $2"
        PASS=$((PASS+1))
    else
        echo "  FAIL: $2"
        FAIL=$((FAIL+1))
    fi
}

check "command -v waydroid" "waydroid binary"
check "[ -f /var/lib/waydroid/images/system.img ]" "system.img (Android image)"
check "[ -f /var/lib/waydroid/images/vendor.img ]" "vendor.img"
check "[ -f /var/lib/waydroid/waydroid_base.prop ]" "device properties"
check "[ -f /opt/titan/android/kyc_android_console.py ]" "KYC console"
check "[ -x /usr/local/bin/titan-android ]" "titan-android CLI"
check "python3 -m py_compile /opt/titan/android/kyc_android_console.py" "console syntax"
check "systemctl list-unit-files | grep -q titan-waydroid" "systemd service"
check "[ -f /opt/titan/core/kyc_core.py ]" "kyc_core.py"
check "[ -f /opt/titan/core/kyc_enhanced.py ]" "kyc_enhanced.py"
check "[ -f /opt/titan/core/kyc_voice_engine.py ]" "kyc_voice_engine.py"
check "[ -f /opt/titan/core/tof_depth_synthesis.py ]" "tof_depth_synthesis.py"
check "[ -f /opt/titan/core/waydroid_sync.py ]" "waydroid_sync.py"
check "[ -d /opt/titan/android/assets ]" "asset directories"

echo ""
echo "  Results: $PASS passed, $FAIL failed"

# 8. Test console
echo ""
echo "[8] Testing titan-android CLI..."
titan-android status 2>&1 | head -15 || echo "  CLI test had issues"

echo ""
echo "=== KYC ANDROID SETUP COMPLETE ==="
echo ""
echo "Usage:"
echo "  titan-android status       # Check container status"
echo "  titan-android start        # Start Android"
echo "  titan-android stop         # Stop Android"
echo "  titan-android spoof pixel7 # Apply device identity"
echo "  titan-android apps         # List installed apps"
echo "  titan-android camera setup # Setup virtual camera"
echo "  titan-android kyc jumio    # Check KYC capabilities"
echo "  titan-android sync         # Cross-device sync"
