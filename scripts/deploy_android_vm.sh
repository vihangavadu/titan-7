#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# TITAN OS — Deploy Android VM to VPS
# Quick deployment script: syncs KYC files + runs Waydroid setup on VPS
#
# Usage (from local machine):
#   bash scripts/deploy_android_vm.sh
#
# Or via plink:
#   plink.exe -ssh root@72.62.72.48 -pw "Chilaw@123@llm" -batch "bash /tmp/deploy_android_vm.sh"
# ═══════════════════════════════════════════════════════════════════════════

set -euo pipefail

VPS_IP="72.62.72.48"
VPS_USER="root"
VPS_PASS="Chilaw@123@llm"
TITAN_ROOT="/opt/titan"

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

log() { echo -e "${CYAN}[DEPLOY]${NC} $1"; }
ok()  { echo -e "${GREEN}[✓]${NC} $1"; }

# ─── PHASE 1: Sync KYC files to VPS ──────────────────────────────────────
log "Phase 1: Syncing KYC + Android files to VPS..."

# Detect if we're running on the VPS itself or locally
if [ "$(hostname -I 2>/dev/null | grep -c '72.62.72.48')" -gt 0 ] || [ -d "${TITAN_ROOT}/core" ]; then
    log "Running on VPS — skipping file sync, using local files"
    ON_VPS=1
else
    ON_VPS=0
    log "Running locally — will use plink/scp for file transfer"
fi

if [ "$ON_VPS" = "1" ]; then
    # ─── PHASE 2: Install Waydroid on VPS ─────────────────────────────────
    log "Phase 2: Installing Waydroid..."

    # Check if already installed
    if command -v waydroid &>/dev/null; then
        ok "Waydroid already installed: $(waydroid --version 2>&1 | head -1)"
    else
        log "Adding Waydroid repository..."
        apt-get install -y curl ca-certificates gnupg 2>&1 | tail -1

        if [ ! -f /usr/share/keyrings/waydroid.gpg ]; then
            curl -fsSL https://repo.waydro.id/waydroid.gpg | gpg --dearmor -o /usr/share/keyrings/waydroid.gpg
            echo "deb [signed-by=/usr/share/keyrings/waydroid.gpg] https://repo.waydro.id/ bookworm main" > /etc/apt/sources.list.d/waydroid.list
        fi

        apt-get update -qq 2>&1 | tail -1
        apt-get install -y waydroid python3-gbinder lxc dnsmasq-base iptables 2>&1 | tail -5
        ok "Waydroid installed"
    fi

    # ─── PHASE 3: Check kernel binder support ─────────────────────────────
    log "Phase 3: Checking kernel binder support..."

    BINDER_OK=0
    if [ -e /dev/binderfs/binder ] || [ -e /dev/binder ]; then
        ok "Binder device found"
        BINDER_OK=1
    elif modprobe binder_linux 2>/dev/null; then
        ok "binder_linux module loaded"
        BINDER_OK=1
    elif grep -q "CONFIG_ANDROID_BINDER" /boot/config-$(uname -r) 2>/dev/null; then
        ok "Binder support in kernel config"
        BINDER_OK=1
    fi

    if [ "$BINDER_OK" = "0" ]; then
        log "Binder not available — installing DKMS modules..."
        apt-get install -y linux-headers-$(uname -r) dkms 2>&1 | tail -3

        # Try anbox-modules for binder/ashmem
        if [ ! -d /usr/src/anbox-modules ]; then
            git clone https://github.com/AsteroidOS/anbox-modules.git /usr/src/anbox-modules 2>&1 | tail -2 || true
            if [ -f /usr/src/anbox-modules/INSTALL.sh ]; then
                cd /usr/src/anbox-modules && bash INSTALL.sh 2>&1 | tail -3 || true
                cd -
            fi
        fi
        modprobe binder_linux 2>/dev/null || true
        modprobe ashmem_linux 2>/dev/null || true
    fi

    # ─── PHASE 4: Initialize Waydroid with Android image ──────────────────
    log "Phase 4: Initializing Android image..."

    if [ -f /var/lib/waydroid/images/system.img ]; then
        ok "Android system image already exists"
    else
        log "Downloading LineageOS 18.1 GAPPS image (Android 11)..."
        log "This downloads ~1GB from https://ota.waydro.id/ — may take a few minutes"
        waydroid init -s GAPPS -f 2>&1 | tail -10 || {
            log "GAPPS failed, trying VANILLA..."
            waydroid init -s VANILLA -f 2>&1 | tail -10
        }

        if [ -f /var/lib/waydroid/images/system.img ]; then
            ok "Android image downloaded successfully"
        else
            echo -e "${RED}[!] Android image download failed${NC}"
            echo "    Try manually: waydroid init -s GAPPS -f"
            echo "    Or download from: https://ota.waydro.id/system"
        fi
    fi

    # ─── PHASE 5: Configure device properties ─────────────────────────────
    log "Phase 5: Configuring device properties..."

    PROP_FILE="/var/lib/waydroid/waydroid_base.prop"
    if [ ! -f "$PROP_FILE" ] || ! grep -q "ro.product.model=Pixel 7" "$PROP_FILE" 2>/dev/null; then
        cat > "$PROP_FILE" << 'PROPS'
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
PROPS
        ok "Device properties set (Pixel 7)"
    else
        ok "Device properties already configured"
    fi

    # ─── PHASE 6: Deploy KYC Android console ──────────────────────────────
    log "Phase 6: Deploying KYC Android console..."

    mkdir -p "${TITAN_ROOT}/android"

    # Copy the setup script's embedded console if it exists
    if [ -f "${TITAN_ROOT}/scripts/setup_waydroid_android.sh" ]; then
        # Extract and run just the deploy_kyc_app function
        bash "${TITAN_ROOT}/scripts/setup_waydroid_android.sh" 2>/dev/null || true
    fi

    # Ensure titan-android CLI wrapper exists
    cat > /usr/local/bin/titan-android << 'WRAPPER'
#!/bin/bash
exec python3 /opt/titan/android/kyc_android_console.py "$@"
WRAPPER
    chmod +x /usr/local/bin/titan-android 2>/dev/null || true

    ok "KYC Android console ready"

    # ─── PHASE 7: Configure networking ────────────────────────────────────
    log "Phase 7: Configuring networking..."
    sysctl -w net.ipv4.ip_forward=1 > /dev/null 2>&1
    echo "net.ipv4.ip_forward=1" > /etc/sysctl.d/99-titan-waydroid.conf 2>/dev/null || true
    iptables -t nat -C POSTROUTING -s 192.168.240.0/24 -o eth0 -j MASQUERADE 2>/dev/null || \
        iptables -t nat -A POSTROUTING -s 192.168.240.0/24 -o eth0 -j MASQUERADE 2>/dev/null || true
    ok "Networking configured"

    # ─── PHASE 8: Create systemd service ──────────────────────────────────
    log "Phase 8: Creating systemd service..."

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
    ok "Service created: titan-waydroid.service"

    # ─── PHASE 9: Verification ────────────────────────────────────────────
    log "Phase 9: Running verification..."
    echo ""
    echo "═══════════════════════════════════════════════════════"

    PASS=0; FAIL=0
    check() {
        if eval "$1" 2>/dev/null; then
            echo -e "  ${GREEN}✓${NC} $2"
            ((PASS++))
        else
            echo -e "  ${RED}✗${NC} $2"
            ((FAIL++))
        fi
    }

    check "command -v waydroid" "waydroid binary installed"
    check "[ -f /var/lib/waydroid/images/system.img ]" "Android system.img exists"
    check "[ -f /var/lib/waydroid/images/vendor.img ]" "Android vendor.img exists"
    check "[ -f /var/lib/waydroid/waydroid_base.prop ]" "Device properties configured"
    check "[ -f ${TITAN_ROOT}/android/kyc_android_console.py ]" "KYC console deployed"
    check "[ -f /usr/local/bin/titan-android ]" "titan-android CLI wrapper"
    check "systemctl list-unit-files | grep -q titan-waydroid" "systemd service registered"
    check "[ -f ${TITAN_ROOT}/core/waydroid_sync.py ]" "waydroid_sync.py in core"
    check "[ -f ${TITAN_ROOT}/core/kyc_core.py ]" "kyc_core.py in core"
    check "[ -f ${TITAN_ROOT}/core/kyc_enhanced.py ]" "kyc_enhanced.py in core"
    check "[ -f ${TITAN_ROOT}/core/kyc_voice_engine.py ]" "kyc_voice_engine.py in core"
    check "python3 -c \"import sys; sys.path.insert(0,'${TITAN_ROOT}/core'); from waydroid_sync import WaydroidSyncEngine\"" "waydroid_sync importable"

    echo ""
    echo "  Results: ${PASS} passed, ${FAIL} failed"
    echo "═══════════════════════════════════════════════════════"
    echo ""

    if [ "$FAIL" -eq 0 ]; then
        echo -e "${GREEN}Android VM deployment complete!${NC}"
    else
        echo -e "${RED}Some checks failed — review output above${NC}"
    fi

    echo ""
    echo "  Next steps:"
    echo "    titan-android start      # Start Android container"
    echo "    titan-android status     # Check status"
    echo "    titan-android spoof pixel7  # Apply device identity"
    echo "    titan-android apps       # List installed apps"
    echo "    titan-android sync       # Start cross-device sync"

else
    # Running locally — deploy via plink
    PLINK="./plink.exe"
    if [ ! -f "$PLINK" ]; then
        echo "plink.exe not found in current directory"
        echo "Upload this script to VPS and run there instead:"
        echo "  scp scripts/deploy_android_vm.sh root@${VPS_IP}:/tmp/"
        echo "  ssh root@${VPS_IP} 'bash /tmp/deploy_android_vm.sh'"
        exit 1
    fi

    log "Uploading files to VPS via plink..."
    # This would need pscp or similar — just print instructions
    echo ""
    echo "To deploy on VPS, run:"
    echo "  1. Upload: pscp -pw \"${VPS_PASS}\" scripts/deploy_android_vm.sh ${VPS_USER}@${VPS_IP}:/tmp/"
    echo "  2. Execute: plink.exe -ssh ${VPS_USER}@${VPS_IP} -pw \"${VPS_PASS}\" -batch \"bash /tmp/deploy_android_vm.sh\""
fi
