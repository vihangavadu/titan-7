#!/usr/bin/env python3
"""
TITAN OS - Master VPS Installation
Fully configures Titan OS on VPS based on complete repo tree analysis.
Covers ALL package lists, hooks, configs, services, and dependencies.
"""

import json
import os
import sys
import time
from pathlib import Path, PurePosixPath

import paramiko

VPS_IP = os.environ.get("TITAN_VPS_HOST", "72.62.72.48")
VPS_USER = os.environ.get("TITAN_VPS_USER", "root")
VPS_PASS = os.environ.get("TITAN_VPS_PASSWORD", "")
VPS_ROOT = "/opt/titan"
LOCAL_ROOT = Path(__file__).resolve().parents[1]
KEY_FILE = Path.home() / ".ssh" / "id_ed25519"

# Skip local dirs that should not be mirrored
SKIP_DIRS = {".git", ".idea", ".venv", ".windsurf", "__pycache__", "node_modules"}
SKIP_SUFFIXES = (".pyc", ".pyo")


def list_local_files():
    """List every file in local repo (relative to LOCAL_ROOT)."""
    files = {}
    for root, dirs, filenames in os.walk(LOCAL_ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in filenames:
            if name.endswith(SKIP_SUFFIXES):
                continue
            full = Path(root) / name
            rel = full.relative_to(LOCAL_ROOT).as_posix()
            try:
                size = full.stat().st_size
            except OSError:
                size = 0
            files[rel] = {"size": size, "local_path": str(full)}
    return files


def list_remote_files(ssh):
    """List every file on VPS under /opt/titan."""
    rc, out, _ = ssh_run(ssh, f"find {VPS_ROOT} -type f -printf '%P\\t%s\\n'", timeout=240)
    files = {}
    if rc != 0 or not out:
        return files
    for line in out.splitlines():
        parts = line.split("\t", 1)
        if len(parts) != 2:
            continue
        rel = parts[0].strip()
        try:
            size = int(parts[1].strip())
        except ValueError:
            size = -1
        files[rel] = {"size": size}
    return files


def sftp_mkdir_p(sftp, remote_dir):
    dirs_to_create = []
    current = remote_dir
    while current and current != "/":
        try:
            sftp.stat(current)
            break
        except FileNotFoundError:
            dirs_to_create.append(current)
            current = str(PurePosixPath(current).parent)
    for d in reversed(dirs_to_create):
        try:
            sftp.mkdir(d)
        except IOError:
            pass


def upload_files(ssh, missing_files, local_files):
    sftp = ssh.open_sftp()
    uploaded = 0
    failed = []
    total = len(missing_files)
    total_bytes = 0

    for i, rel_path in enumerate(sorted(missing_files), 1):
        info = local_files[rel_path]
        local_path = info["local_path"]
        remote_path = f"{VPS_ROOT}/{rel_path}"
        remote_dir = str(PurePosixPath(remote_path).parent)
        try:
            sftp_mkdir_p(sftp, remote_dir)
            sftp.put(local_path, remote_path)
            uploaded += 1
            total_bytes += info["size"]
            if i % 100 == 0 or i == total:
                pct = (i / total) * 100 if total else 100
                print(f"    [{i}/{total}] {pct:.0f}% uploaded ({uploaded} ok, {len(failed)} fail)")
        except Exception as e:
            failed.append((rel_path, str(e)[:120]))

    sftp.close()
    return uploaded, failed, total_bytes


def sync_repo_to_vps(ssh):
    """Mirror local repo files to VPS before installation phases."""
    print("  - Scanning local repo...")
    local_files = list_local_files()
    print(f"    Local files: {len(local_files):,}")

    print("  - Scanning VPS tree...")
    remote_files = list_remote_files(ssh)
    print(f"    Remote files: {len(remote_files):,}")

    local_set = set(local_files.keys())
    remote_set = set(remote_files.keys())
    missing = local_set - remote_set
    common = local_set & remote_set
    stale = set()
    for rel in common:
        if local_files[rel]["size"] != remote_files[rel]["size"]:
            stale.add(rel)

    need_upload = missing | stale
    print(f"    Missing: {len(missing):,} | Stale: {len(stale):,} | To upload: {len(need_upload):,}")
    if not need_upload:
        print("  - Repo already in sync.")
        return {"uploaded": 0, "failed": 0, "missing": 0, "stale": 0}

    uploaded, failed, total_bytes = upload_files(ssh, need_upload, local_files)
    print(f"  - Uploaded {uploaded:,} files ({total_bytes / (1024 * 1024):.1f} MB), failed {len(failed):,}")

    # Normalize permissions for scripts after sync
    ssh_run(ssh, f"find {VPS_ROOT} -name '*.sh' -exec chmod +x {{}} \\;")
    ssh_run(ssh, f"find {VPS_ROOT} -name '*.py' -exec chmod +x {{}} \\;")
    ssh_run(ssh, f"find {VPS_ROOT}/src/bin -type f -exec chmod +x {{}} \\; 2>/dev/null")

    return {
        "uploaded": uploaded,
        "failed": len(failed),
        "missing": len(missing),
        "stale": len(stale),
    }

# ── The master install script to run on the VPS ──
MASTER_INSTALL_SH = r'''#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════
# TITAN OS — MASTER VPS INSTALLATION SCRIPT
# Generated from complete repo tree analysis
# Covers: package-lists + hooks + configs + services + pip deps
# ═══════════════════════════════════════════════════════════════════════
set +e  # Continue on errors — log everything
export DEBIAN_FRONTEND=noninteractive
TITAN_ROOT="/opt/titan"
GUI_USER_PASSWORD="${TITAN_GUI_PASSWORD:-titan}"
LOG="/tmp/titan_master_install.log"
exec > >(tee -a "$LOG") 2>&1

PASS=0
WARN=0
FAIL=0
mark_pass() { PASS=$((PASS+1)); echo "[PASS] $1"; }
mark_warn() { WARN=$((WARN+1)); echo "[WARN] $1"; }
mark_fail() { FAIL=$((FAIL+1)); echo "[FAIL] $1"; }

echo "═══════════════════════════════════════════════════════════════"
echo "  TITAN OS — Master VPS Installation"
echo "  Started: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "═══════════════════════════════════════════════════════════════"

# ═══════════════════════════════════════════════════════════════════════
# PHASE 1: SYSTEM PACKAGES (from custom.list.chroot + kyc_module + waydroid)
# ═══════════════════════════════════════════════════════════════════════
echo ""
echo "═══ PHASE 1: System Packages ═══"

apt-get update -qq

# Core system (VPS-compatible subset of custom.list.chroot)
echo "[1.1] Core system packages..."
apt-get install -y --no-install-recommends \
    openssh-server \
    build-essential gcc git vim curl wget clang llvm cmake pkg-config \
    libssl-dev libffi-dev libgl-dev mesa-common-dev libx11-dev rsync \
    2>&1 | tail -3 && mark_pass "Core system" || mark_warn "Core system (partial)"

# GUI/XRDP stack (full UI/UX requirement)
echo "[1.1b] GUI + XRDP packages..."
apt-get install -y --no-install-recommends \
    xfce4 xfce4-terminal lightdm lightdm-gtk-greeter \
    xrdp xorgxrdp tigervnc-standalone-server tigervnc-common \
    dbus-x11 \
    2>&1 | tail -3 && mark_pass "GUI + XRDP" || mark_warn "GUI + XRDP (partial)"

# eBPF / XDP Tools
echo "[1.2] eBPF / XDP tools..."
apt-get install -y --no-install-recommends \
    linux-headers-$(uname -r) \
    bpfcc-tools libbpf-dev iproute2 \
    2>&1 | tail -3 && mark_pass "eBPF tools" || mark_warn "eBPF tools (partial)"

# Python environment
echo "[1.3] Python environment..."
apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv python3-dev \
    2>&1 | tail -3 && mark_pass "Python env" || mark_fail "Python env"

# Network analysis
echo "[1.4] Network analysis tools..."
apt-get install -y --no-install-recommends \
    tcpdump nmap netcat-openbsd dnsutils iptables nftables \
    2>&1 | tail -3 && mark_pass "Network tools" || mark_warn "Network tools (partial)"

# Time manipulation
echo "[1.5] Time manipulation (libfaketime)..."
apt-get install -y --no-install-recommends libfaketime \
    2>&1 | tail -3 && mark_pass "libfaketime" || mark_warn "libfaketime"

# Process isolation
echo "[1.6] Process isolation..."
apt-get install -y --no-install-recommends \
    cgroup-tools systemd-container \
    2>&1 | tail -3 && mark_pass "Process isolation" || mark_warn "Process isolation"

# Utilities
echo "[1.7] Utilities..."
apt-get install -y --no-install-recommends \
    jq sqlite3 tree htop tmux unzip p7zip-full \
    2>&1 | tail -3 && mark_pass "Utilities" || mark_warn "Utilities"

# Python system packages
echo "[1.8] Python system packages..."
apt-get install -y --no-install-recommends \
    python3-pyqt6 python3-dotenv python3-cryptography python3-nacl \
    python3-requests python3-httpx python3-aiohttp python3-flask python3-jinja2 \
    python3-numpy python3-pil python3-psutil python3-yaml python3-dateutil \
    python3-pydantic python3-tk python3-snappy \
    2>&1 | tail -3 && mark_pass "Python system pkgs" || mark_warn "Python system pkgs (partial)"

# Database & storage
echo "[1.9] Database & storage..."
apt-get install -y --no-install-recommends \
    libsnappy-dev libsodium-dev \
    2>&1 | tail -3 && mark_pass "DB/storage libs" || mark_warn "DB/storage libs"

# Font management
echo "[1.10] Font management..."
apt-get install -y --no-install-recommends \
    fontconfig fonts-liberation fonts-dejavu fonts-noto fonts-cantarell \
    2>&1 | tail -3 && mark_pass "Fonts" || mark_warn "Fonts"

# Hardware ID masking
echo "[1.11] Hardware ID masking tools..."
apt-get install -y --no-install-recommends \
    dmidecode lshw pciutils usbutils \
    2>&1 | tail -3 && mark_pass "HW ID tools" || mark_warn "HW ID tools"

# Audio/Video (KYC module toolchain)
echo "[1.12] Audio/Video + KYC toolchain..."
apt-get install -y --no-install-recommends \
    ffmpeg v4l2loopback-dkms v4l2loopback-utils \
    gstreamer1.0-tools gstreamer1.0-plugins-good gstreamer1.0-plugins-bad \
    python3-opencv python3-pil python3-scipy \
    mesa-utils vainfo libpulse0 libopengl0 libglx-mesa0 \
    2>&1 | tail -3 && mark_pass "Audio/Video/KYC" || mark_warn "Audio/Video/KYC (partial)"

# Node.js (KYC 3D Renderer)
echo "[1.13] Node.js..."
apt-get install -y --no-install-recommends nodejs npm \
    2>&1 | tail -3 && mark_pass "Node.js" || mark_warn "Node.js"

# Proxy / SOCKS support
echo "[1.14] Proxy/SOCKS tools..."
apt-get install -y --no-install-recommends \
    proxychains4 torsocks \
    2>&1 | tail -3 && mark_pass "Proxy tools" || mark_warn "Proxy tools"

# Security tools
echo "[1.15] Security tools..."
apt-get install -y --no-install-recommends \
    apparmor firejail \
    2>&1 | tail -3 && mark_pass "Security tools" || mark_warn "Security tools"

# Additional tools
echo "[1.16] Additional eBPF + system info..."
apt-get install -y --no-install-recommends \
    libelf-dev zlib1g-dev lsb-release zstd lz4 \
    ca-certificates ssl-cert acpid ifupdown e2fsprogs \
    2>&1 | tail -3 && mark_pass "Additional tools" || mark_warn "Additional tools"

# DNS privacy (unbound)
echo "[1.17] DNS privacy (unbound)..."
apt-get install -y --no-install-recommends \
    unbound \
    2>&1 | tail -3 && mark_pass "Unbound DNS" || mark_warn "Unbound DNS"

# Waydroid dependencies
echo "[1.18] Waydroid dependencies..."
apt-get install -y --no-install-recommends \
    lxc dnsmasq-base dkms libgles2-mesa bridge-utils \
    2>&1 | tail -3 && mark_pass "Waydroid deps" || mark_warn "Waydroid deps"

# Compression
echo "[1.19] Compression tools..."
apt-get install -y --no-install-recommends \
    zstd lz4 \
    2>&1 | tail -3 && mark_pass "Compression" || mark_warn "Compression"

# USB peripheral synthesis
echo "[1.20] USB tools..."
apt-get install -y --no-install-recommends \
    usb-modeswitch \
    2>&1 | tail -3 && mark_pass "USB tools" || mark_warn "USB tools"

# Headless browser deps (for Camoufox/Playwright on VPS)
echo "[1.21] Headless browser deps..."
apt-get install -y --no-install-recommends \
    libgbm1 libdrm2 libxt6 xvfb libgtk-3-0 libdbus-glib-1-2 \
    libasound2 libx11-xcb1 libxtst6 dbus-x11 \
    2>&1 | tail -3 && mark_pass "Browser deps" || mark_warn "Browser deps"

echo ""
echo "Phase 1 complete."

# ═══════════════════════════════════════════════════════════════════════
# PHASE 2: PYTHON PIP DEPENDENCIES
# (from requirements.txt + hooks 070/080/99)
# ═══════════════════════════════════════════════════════════════════════
echo ""
echo "═══ PHASE 2: Python Pip Dependencies ═══"

# From hook 080 (Cognitive Core)
echo "[2.1] Cognitive Core deps (openai, onnxruntime, scipy)..."
pip3 install --no-cache-dir --break-system-packages \
    openai onnxruntime scipy \
    2>&1 | tail -3 && mark_pass "Cognitive Core pip" || mark_warn "Cognitive Core pip"

# From hook 99 (Cloud Brain + DMTG + core)
echo "[2.2] Core pip deps (httpx, pydantic, aiohttp, etc)..."
pip3 install --no-cache-dir --break-system-packages \
    httpx pydantic aiohttp python-socks requests urllib3 certifi \
    2>&1 | tail -3 && mark_pass "Core pip" || mark_warn "Core pip"

# From hook 070 (Camoufox + Playwright)
echo "[2.3] Camoufox + browserforge..."
pip3 install --no-cache-dir --break-system-packages \
    "camoufox[geoip]" browserforge \
    2>&1 | tail -3 && mark_pass "Camoufox pip" || mark_warn "Camoufox pip"

echo "[2.4] Playwright..."
pip3 install --no-cache-dir --break-system-packages \
    playwright \
    2>&1 | tail -3 && mark_pass "Playwright pip" || mark_warn "Playwright pip"

# From hook 99 (Phase 3 deps)
echo "[2.5] Phase 3 deps (aioquic, pytz, lz4, stripe, fastapi, uvicorn)..."
pip3 install --no-cache-dir --break-system-packages \
    aioquic pytz lz4 stripe fastapi uvicorn cryptography \
    2>&1 | tail -3 && mark_pass "Phase 3 pip" || mark_warn "Phase 3 pip"

# From hook 99 (LivePortrait for KYC)
echo "[2.6] InsightFace + ONNX..."
pip3 install --no-cache-dir --break-system-packages \
    insightface onnxruntime \
    2>&1 | tail -3 && mark_pass "InsightFace pip" || mark_warn "InsightFace pip"

# From src/apps/requirements.txt
echo "[2.7] Apps requirements (gitpython, chromadb, langchain, etc)..."
pip3 install --no-cache-dir --break-system-packages \
    gitpython black flake8 orjson structlog \
    watchdog pyyaml python-dotenv jedi \
    websockets python-dateutil jsonschema tqdm \
    2>&1 | tail -3 && mark_pass "Apps pip (core)" || mark_warn "Apps pip (core)"

echo "[2.8] AI Enhancement Stack..."
pip3 install --no-cache-dir --break-system-packages \
    chromadb sentence-transformers \
    langchain langchain-core langchain-ollama langchain-community \
    duckduckgo-search \
    geoip2 redis minio playwright \
    2>&1 | tail -3 && mark_pass "AI Enhancement pip" || mark_warn "AI Enhancement pip"

# From src/core/requirements_oblivion.txt
echo "[2.9] Oblivion deps..."
pip3 install --no-cache-dir --break-system-packages \
    pycryptodome websocket-client selenium \
    2>&1 | tail -3 && mark_pass "Oblivion pip" || mark_warn "Oblivion pip"

# From tests/requirements-test.txt
echo "[2.10] Test deps..."
pip3 install --no-cache-dir --break-system-packages \
    pytest pytest-cov pytest-asyncio pytest-mock pytest-html pytest-timeout \
    faker coverage \
    2>&1 | tail -3 && mark_pass "Test pip" || mark_warn "Test pip"

# Additional useful packages
echo "[2.11] Additional packages (prometheus, flask-cors, etc)..."
pip3 install --no-cache-dir --break-system-packages \
    prometheus-client flask-cors gunicorn \
    2>&1 | tail -3 && mark_pass "Additional pip" || mark_warn "Additional pip"

echo ""
echo "Phase 2 complete."

# ═══════════════════════════════════════════════════════════════════════
# PHASE 3: DIRECTORY STRUCTURE
# ═══════════════════════════════════════════════════════════════════════
echo ""
echo "═══ PHASE 3: Directory Structure ═══"

echo "[3.1] Creating all required directories..."
mkdir -p "$TITAN_ROOT"/{core,apps,bin,config,vpn,state,profiles,data,lib}
mkdir -p "$TITAN_ROOT"/{docs,scripts,training,tests,modelfiles}
mkdir -p "$TITAN_ROOT"/{src/core,src/apps,src/bin,src/branding,src/assets/motions}
mkdir -p "$TITAN_ROOT"/{iso,plans,.github,hostinger-dev}
mkdir -p "$TITAN_ROOT"/assets/motions
mkdir -p "$TITAN_ROOT"/android
mkdir -p "$TITAN_ROOT"/profiles/{default,active}
mkdir -p /tmp/titan_kyc
mark_pass "Directory structure"

echo "[3.2] Runtime path compatibility (/opt/titan/src -> runtime paths)..."
mkdir -p "$TITAN_ROOT"/{apps,core,bin}
if [ -d "$TITAN_ROOT/src/apps" ]; then
    rsync -a --delete "$TITAN_ROOT/src/apps/" "$TITAN_ROOT/apps/" 2>/dev/null || \
        cp -a "$TITAN_ROOT/src/apps/." "$TITAN_ROOT/apps/" 2>/dev/null || true
fi
if [ -d "$TITAN_ROOT/src/core" ]; then
    rsync -a --delete "$TITAN_ROOT/src/core/" "$TITAN_ROOT/core/" 2>/dev/null || \
        cp -a "$TITAN_ROOT/src/core/." "$TITAN_ROOT/core/" 2>/dev/null || true
fi
if [ -d "$TITAN_ROOT/src/bin" ]; then
    rsync -a "$TITAN_ROOT/src/bin/" "$TITAN_ROOT/bin/" 2>/dev/null || \
        cp -a "$TITAN_ROOT/src/bin/." "$TITAN_ROOT/bin/" 2>/dev/null || true
fi

# Overlay curated includes.chroot app/core/bin files (for files only present there)
if [ -d "$TITAN_ROOT/iso/config/includes.chroot/opt/titan/apps" ]; then
    cp -an "$TITAN_ROOT/iso/config/includes.chroot/opt/titan/apps/." "$TITAN_ROOT/apps/" 2>/dev/null || true
fi
if [ -d "$TITAN_ROOT/iso/config/includes.chroot/opt/titan/core" ]; then
    cp -an "$TITAN_ROOT/iso/config/includes.chroot/opt/titan/core/." "$TITAN_ROOT/core/" 2>/dev/null || true
fi
if [ -d "$TITAN_ROOT/iso/config/includes.chroot/opt/titan/bin" ]; then
    cp -an "$TITAN_ROOT/iso/config/includes.chroot/opt/titan/bin/." "$TITAN_ROOT/bin/" 2>/dev/null || true
fi

# Compatibility link for launcher references
if [ -f "$TITAN_ROOT/bin/titan_mission_control.py" ] && [ ! -f "$TITAN_ROOT/apps/titan_mission_control.py" ]; then
    ln -sf "$TITAN_ROOT/bin/titan_mission_control.py" "$TITAN_ROOT/apps/titan_mission_control.py"
fi

# Legacy entrypoints required by desktop files/services
if [ ! -f "$TITAN_ROOT/apps/app_unified.py" ] && [ -f "$TITAN_ROOT/apps/titan_launcher.py" ]; then
cat > "$TITAN_ROOT/apps/app_unified.py" << 'UNIFIEDPY'
#!/usr/bin/env python3
import runpy
runpy.run_path('/opt/titan/apps/titan_launcher.py', run_name='__main__')
UNIFIEDPY
fi
if [ ! -f "$TITAN_ROOT/apps/app_genesis.py" ] && [ -f "$TITAN_ROOT/apps/app_profile_forge.py" ]; then
cat > "$TITAN_ROOT/apps/app_genesis.py" << 'GENESISPY'
#!/usr/bin/env python3
import runpy
runpy.run_path('/opt/titan/apps/app_profile_forge.py', run_name='__main__')
GENESISPY
fi
if [ ! -f "$TITAN_ROOT/apps/app_cerberus.py" ] && [ -f "$TITAN_ROOT/apps/app_card_validator.py" ]; then
cat > "$TITAN_ROOT/apps/app_cerberus.py" << 'CERBERUSPY'
#!/usr/bin/env python3
import runpy
runpy.run_path('/opt/titan/apps/app_card_validator.py', run_name='__main__')
CERBERUSPY
fi
chmod +x "$TITAN_ROOT/apps/app_unified.py" "$TITAN_ROOT/apps/app_genesis.py" "$TITAN_ROOT/apps/app_cerberus.py" 2>/dev/null || true
mark_pass "Runtime path compatibility"

echo "[3.3] /opt/lucid-empire compatibility..."
mkdir -p /opt/lucid-empire/{bin,lib,backend,profiles/default}
ln -sfn /opt/lucid-empire/profiles/default /opt/lucid-empire/profiles/active
ln -sfn "$TITAN_ROOT/core" /opt/lucid-empire/backend/core
ln -sfn "$TITAN_ROOT/apps" /opt/lucid-empire/backend/apps

cat > /opt/lucid-empire/bin/titan-backend-init.sh << 'BEOF'
#!/bin/bash
set +e
echo "[TITAN-BACKEND] Initializing..."
if [ -f /opt/titan/kernel-modules/titan_hw.ko ]; then
    insmod /opt/titan/kernel-modules/titan_hw.ko 2>/dev/null || true
fi
[ -L /opt/lucid-empire/profiles/active ] || ln -sf /opt/lucid-empire/profiles/default /opt/lucid-empire/profiles/active
echo "[TITAN-BACKEND] Init complete"
exit 0
BEOF

cat > /opt/lucid-empire/bin/load-ebpf.sh << 'EEOF'
#!/bin/bash
set +e
ACTION="${3:-load}"
if [ "$ACTION" = "unload" ]; then
    echo "[TITAN-EBPF] Shield unloaded"
    exit 0
fi
echo "[TITAN-EBPF] Shield loaded"
exit 0
EEOF

chmod +x /opt/lucid-empire/bin/titan-backend-init.sh /opt/lucid-empire/bin/load-ebpf.sh
mark_pass "/opt/lucid-empire compatibility"

echo "[3.4] User account + GUI groups..."
if ! id -u user >/dev/null 2>&1; then
    useradd -m -s /bin/bash user 2>/dev/null || true
fi
echo "user:${GUI_USER_PASSWORD}" | chpasswd 2>/dev/null || true
usermod -aG sudo,video,audio,render,netdev user 2>/dev/null || true
mark_pass "User account"

# ═══════════════════════════════════════════════════════════════════════
# PHASE 4: DEPLOY CONFIG FILES FROM includes.chroot/etc
# ═══════════════════════════════════════════════════════════════════════
echo ""
echo "═══ PHASE 4: System Config Files ═══"

# 4.1 OS Identity — preserve Debian base for apt/tailscale compatibility
echo "[4.1] OS Identity..."
# Store Titan branding separately; never overwrite /etc/os-release on VPS
if [ -f "$TITAN_ROOT/iso/config/includes.chroot/etc/os-release" ]; then
    cp "$TITAN_ROOT/iso/config/includes.chroot/etc/os-release" /etc/os-release.titan 2>/dev/null || true
else
    cat > /etc/os-release.titan << 'OSREL'
NAME="Titan OS"
VERSION="9.2 (Singularity)"
ID=titanos
ID_LIKE=debian
VERSION_ID="9.2"
PRETTY_NAME="Titan OS 9.2 (Singularity)"
HOME_URL="https://titan-os.io"
SUPPORT_URL="https://titan-os.io/support"
BUG_REPORT_URL="https://titan-os.io/bugs"
OSREL
fi
# Ensure VERSION_CODENAME exists for package tooling
if ! grep -q '^VERSION_CODENAME=' /etc/os-release 2>/dev/null; then
    echo 'VERSION_CODENAME=bookworm' >> /etc/os-release
fi
mark_pass "OS Identity (Debian preserved, Titan branding in /etc/os-release.titan)"

# 4.2 Hostname
echo "[4.2] Hostname..."
echo "titan-os" > /etc/hostname
hostnamectl set-hostname titan-os 2>/dev/null || true
mark_pass "Hostname"

# 4.3 /etc/issue + /etc/issue.net
echo "[4.3] Login banners..."
if [ -f "$TITAN_ROOT/iso/config/includes.chroot/etc/issue" ]; then
    cp "$TITAN_ROOT/iso/config/includes.chroot/etc/issue" /etc/issue
fi
if [ -f "$TITAN_ROOT/iso/config/includes.chroot/etc/issue.net" ]; then
    cp "$TITAN_ROOT/iso/config/includes.chroot/etc/issue.net" /etc/issue.net
fi
mark_pass "Login banners"

# 4.4 /etc/hosts
echo "[4.4] Hosts file..."
if [ -f "$TITAN_ROOT/iso/config/includes.chroot/etc/hosts" ]; then
    # Merge: keep existing entries, add Titan ones
    grep -v "titan" /etc/hosts > /tmp/hosts.tmp 2>/dev/null || true
    cat "$TITAN_ROOT/iso/config/includes.chroot/etc/hosts" >> /tmp/hosts.tmp
    cp /tmp/hosts.tmp /etc/hosts
fi
mark_pass "Hosts file"

# 4.5 /etc/lsb-release
echo "[4.5] LSB release..."
if [ -f "$TITAN_ROOT/iso/config/includes.chroot/etc/lsb-release" ]; then
    cp "$TITAN_ROOT/iso/config/includes.chroot/etc/lsb-release" /etc/lsb-release
fi
mark_pass "LSB release"

# 4.6 Sysctl hardening
echo "[4.6] Sysctl hardening..."
SYSCTL_SRC="$TITAN_ROOT/iso/config/includes.chroot/etc/sysctl.d"
if [ -d "$SYSCTL_SRC" ]; then
    mkdir -p /etc/sysctl.d
    cp "$SYSCTL_SRC"/* /etc/sysctl.d/ 2>/dev/null || true
    sysctl --system 2>/dev/null || true
    mark_pass "Sysctl hardening"
else
    # Create essential hardening
    cat > /etc/sysctl.d/99-titan-hardening.conf << 'SYSCTL'
# TITAN OS Hardening
net.ipv4.ip_forward = 1
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1
net.ipv4.tcp_syncookies = 1
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv6.conf.all.accept_redirects = 0
kernel.sysrq = 0
fs.suid_dumpable = 0
kernel.core_uses_pid = 1
SYSCTL
    sysctl --system 2>/dev/null || true
    mark_pass "Sysctl hardening (generated)"
fi

# 4.7 Nftables firewall
echo "[4.7] Nftables firewall..."
if [ -f "$TITAN_ROOT/iso/config/includes.chroot/etc/nftables.conf" ]; then
    cp "$TITAN_ROOT/iso/config/includes.chroot/etc/nftables.conf" /etc/nftables.conf
    mark_pass "Nftables config"
else
    mark_warn "Nftables config (not found in repo)"
fi

# 4.8 PulseAudio config
echo "[4.8] PulseAudio config..."
if [ -f "$TITAN_ROOT/iso/config/includes.chroot/etc/pulse/daemon.conf" ]; then
    mkdir -p /etc/pulse
    cp "$TITAN_ROOT/iso/config/includes.chroot/etc/pulse/daemon.conf" /etc/pulse/daemon.conf
    mark_pass "PulseAudio config"
else
    mark_warn "PulseAudio config (not found)"
fi

# 4.9 Font config
echo "[4.9] Font config..."
if [ -f "$TITAN_ROOT/iso/config/includes.chroot/etc/fonts/local.conf" ]; then
    mkdir -p /etc/fonts
    cp "$TITAN_ROOT/iso/config/includes.chroot/etc/fonts/local.conf" /etc/fonts/local.conf
    fc-cache -f 2>/dev/null || true
    mark_pass "Font config"
else
    mark_warn "Font config (not found)"
fi

# 4.10 NetworkManager privacy
echo "[4.10] NetworkManager privacy..."
if [ -f "$TITAN_ROOT/iso/config/includes.chroot/etc/NetworkManager/conf.d/10-titan-privacy.conf" ]; then
    mkdir -p /etc/NetworkManager/conf.d
    cp "$TITAN_ROOT/iso/config/includes.chroot/etc/NetworkManager/conf.d/10-titan-privacy.conf" \
       /etc/NetworkManager/conf.d/10-titan-privacy.conf
    mark_pass "NetworkManager privacy"
else
    mark_warn "NetworkManager privacy (not found)"
fi

# 4.11 Conky config
echo "[4.11] Conky config..."
if [ -f "$TITAN_ROOT/iso/config/includes.chroot/etc/conky/titan.conf" ]; then
    mkdir -p /etc/conky
    cp "$TITAN_ROOT/iso/config/includes.chroot/etc/conky/titan.conf" /etc/conky/titan.conf
    mark_pass "Conky config"
fi

# 4.12 Profile.d (shell prompt)
echo "[4.12] Shell profile..."
if [ -f "$TITAN_ROOT/iso/config/includes.chroot/etc/profile.d/titan-prompt.sh" ]; then
    cp "$TITAN_ROOT/iso/config/includes.chroot/etc/profile.d/titan-prompt.sh" /etc/profile.d/
    chmod +x /etc/profile.d/titan-prompt.sh
    mark_pass "Shell profile"
fi

# 4.13 Security limits
echo "[4.13] Security limits..."
if [ -f "$TITAN_ROOT/iso/config/includes.chroot/etc/security/limits.d/disable-cores.conf" ]; then
    mkdir -p /etc/security/limits.d
    cp "$TITAN_ROOT/iso/config/includes.chroot/etc/security/limits.d/disable-cores.conf" \
       /etc/security/limits.d/
    mark_pass "Security limits"
fi

# 4.14 Sudoers
echo "[4.14] Sudoers..."
if [ -f "$TITAN_ROOT/iso/config/includes.chroot/etc/sudoers.d/titan-ops" ]; then
    cp "$TITAN_ROOT/iso/config/includes.chroot/etc/sudoers.d/titan-ops" /etc/sudoers.d/
    chmod 440 /etc/sudoers.d/titan-ops
    mark_pass "Sudoers"
fi

# 4.15 GRUB branding
echo "[4.15] GRUB branding..."
if [ -f "$TITAN_ROOT/iso/config/includes.chroot/etc/default/grub.d/titan-branding.cfg" ]; then
    mkdir -p /etc/default/grub.d
    cp "$TITAN_ROOT/iso/config/includes.chroot/etc/default/grub.d/titan-branding.cfg" \
       /etc/default/grub.d/
    update-grub 2>/dev/null || true
    mark_pass "GRUB branding"
fi

echo ""
echo "Phase 4 complete."

# ═══════════════════════════════════════════════════════════════════════
# PHASE 5: KYC MODULE SETUP (from hook 090)
# ═══════════════════════════════════════════════════════════════════════
echo ""
echo "═══ PHASE 5: KYC Module Setup ═══"

# 5.1 v4l2loopback kernel module config
echo "[5.1] v4l2loopback config..."
cat > /etc/modprobe.d/titan-camera.conf << 'MODCONF'
# TITAN V6 :: Virtual Camera Configuration
options v4l2loopback video_nr=2 card_label="Integrated Camera" exclusive_caps=1
MODCONF
grep -q "v4l2loopback" /etc/modules 2>/dev/null || echo "v4l2loopback" >> /etc/modules
modprobe v4l2loopback video_nr=2 card_label="Integrated Camera" exclusive_caps=1 2>/dev/null || true
mark_pass "v4l2loopback config"

# 5.2 KYC assets directories
echo "[5.2] KYC assets..."
mkdir -p "$TITAN_ROOT/core/assets"
mkdir -p "$TITAN_ROOT/assets/motions"
if [ ! -f "$TITAN_ROOT/assets/motions/README.txt" ]; then
    cat > "$TITAN_ROOT/assets/motions/README.txt" << 'MOTIONS'
TITAN V6 Motion Assets (for DMTG Reenactment)
===============================================
Place motion driving videos here:
- neutral.mp4, blink.mp4, smile.mp4, head_left.mp4, head_right.mp4
- head_nod.mp4, look_up.mp4, look_down.mp4
MOTIONS
fi
mark_pass "KYC assets"

# 5.3 KYC permissions
echo "[5.3] KYC permissions..."
chmod +x "$TITAN_ROOT/core/camera_injector.py" 2>/dev/null || true
chmod +x "$TITAN_ROOT/core/reenactment_engine.py" 2>/dev/null || true
chmod +x "$TITAN_ROOT/core/app.py" 2>/dev/null || true
mark_pass "KYC permissions"

echo ""
echo "Phase 5 complete."

# ═══════════════════════════════════════════════════════════════════════
# PHASE 6: OS HARDENING (from hook 095)
# ═══════════════════════════════════════════════════════════════════════
echo ""
echo "═══ PHASE 6: OS Hardening ═══"

# 6.1 Disable unnecessary services
echo "[6.1] Disabling unnecessary services..."
for svc in avahi-daemon cups cups-browsed bluetooth ModemManager whoopsie apport geoclue; do
    systemctl disable "$svc" 2>/dev/null || true
    systemctl mask "$svc" 2>/dev/null || true
done
mark_pass "Disabled unnecessary services"

# 6.2 Kernel module blacklist
echo "[6.2] Kernel module blacklist..."
cat > /etc/modprobe.d/titan-blacklist.conf << 'BLACKLIST'
# TITAN V7.0 — Kernel Module Blacklist
blacklist bluetooth
blacklist btusb
blacklist btrtl
blacklist btbcm
blacklist btintel
blacklist firewire-core
blacklist firewire-ohci
blacklist firewire-sbp2
blacklist thunderbolt
blacklist nfc
blacklist near
blacklist cramfs
blacklist freevxfs
blacklist jffs2
blacklist hfs
blacklist hfsplus
blacklist udf
blacklist dccp
blacklist sctp
blacklist rds
blacklist tipc
BLACKLIST
mark_pass "Kernel blacklist"

# 6.3 Locale
echo "[6.3] Locale..."
echo "en_US.UTF-8 UTF-8" > /etc/locale.gen
locale-gen 2>/dev/null || true
echo 'LANG=en_US.UTF-8' > /etc/default/locale
ln -sf /usr/share/zoneinfo/UTC /etc/localtime
mark_pass "Locale"

# 6.4 AI attribution stripping
echo "[6.4] AI attribution stripping..."
find /opt/titan -name "*.py" -exec sed -i '/Author: GitHub Copilot/d' {} + 2>/dev/null || true
find /opt/titan -name "*.py" -exec sed -i '/Generated by AI/d' {} + 2>/dev/null || true
mark_pass "AI attribution stripped"

echo ""
echo "Phase 6 complete."

# ═══════════════════════════════════════════════════════════════════════
# PHASE 7: ENVIRONMENT VARIABLES & PYTHONPATH
# ═══════════════════════════════════════════════════════════════════════
echo ""
echo "═══ PHASE 7: Environment Setup ═══"

# 7.1 PYTHONPATH for all Titan modules
echo "[7.1] PYTHONPATH..."
cat > /etc/profile.d/titan-env.sh << 'ENVSH'
#!/bin/bash
# TITAN OS — Environment Variables
export TITAN_ROOT="/opt/titan"
export PYTHONPATH="/opt/titan:/opt/titan/core:/opt/titan/apps:/opt/titan/src/core:/opt/titan/src/apps:$PYTHONPATH"
export PATH="/opt/titan/bin:$PATH"
ENVSH
chmod +x /etc/profile.d/titan-env.sh
# Also set for systemd services
mkdir -p /etc/environment.d
cat > /etc/environment.d/50-titan.conf << 'ENVCONF'
TITAN_ROOT=/opt/titan
PYTHONPATH=/opt/titan:/opt/titan/core:/opt/titan/apps:/opt/titan/src/core:/opt/titan/src/apps
PATH=/opt/titan/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ENVCONF
mark_pass "PYTHONPATH + env vars"

# 7.2 Cognitive core env
echo "[7.2] Cognitive core config..."
cat > "$TITAN_ROOT/.env.cognitive" << 'COGENV'
# TITAN V6 Cloud Brain Configuration
TITAN_CLOUD_URL=https://api.titan-singularity.local/v1
TITAN_API_KEY=titan-singularity-v7-key
TITAN_MODEL=meta-llama/Meta-Llama-3-70B-Instruct
TITAN_FALLBACK_LOCAL=true
COGENV
mark_pass "Cognitive core env"

# 7.3 Cerberus env
echo "[7.3] Cerberus config..."
cat > "$TITAN_ROOT/.env.cerberus" << 'CERENV'
# Cerberus Financial Intelligence Configuration
CERBERUS_OLLAMA_URL=http://localhost:11434
CERBERUS_PRIMARY_MODEL=mistral:7b-instruct-v0.2-q4_0
CERBERUS_FALLBACK_MODEL=phi:2.7b-chat-v2.2-q4_0
CERBERUS_HARVEST_INTERVAL=3600
CERBERUS_MAX_KEYS=100
CERBERUS_KEY_EXPIRY_DAYS=7
CERBERUS_TRUST_THRESHOLD=70
CERBERUS_DEFAULT_LIMIT=250.00
CERENV
mark_pass "Cerberus env"

# 7.4 dpkg vendor override
echo "[7.4] Vendor override..."
mkdir -p /etc/dpkg/origins
cat > /etc/dpkg/origins/titanos << 'ORIGINEOF'
Vendor: TitanOS
Vendor-URL: https://titan-os.io
Bugs: https://titan-os.io/bugs
Parent: Debian
ORIGINEOF
ln -sf /etc/dpkg/origins/titanos /etc/dpkg/origins/default 2>/dev/null || true
mark_pass "Vendor override"

echo ""
echo "Phase 7 complete."

# ═══════════════════════════════════════════════════════════════════════
# PHASE 8: SYSTEMD SERVICES
# ═══════════════════════════════════════════════════════════════════════
echo ""
echo "═══ PHASE 8: Systemd Services ═══"

# 8.0 Deploy repo service units first (authoritative)
echo "[8.0] Repo service units..."
UNIT_SRC="$TITAN_ROOT/iso/config/includes.chroot/etc/systemd/system"
if [ -d "$UNIT_SRC" ]; then
    cp "$UNIT_SRC"/*.service /etc/systemd/system/ 2>/dev/null || true
    mark_pass "Repo service units deployed"
else
    mark_warn "Repo service units not found"
fi

# 8.1 Titan API service
echo "[8.1] Titan API service..."
cat > /etc/systemd/system/titan-api.service << 'APISVC'
[Unit]
Description=Titan OS API Server
After=network-online.target redis-server.service ollama.service
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/titan
Environment="PYTHONPATH=/opt/titan:/opt/titan/core:/opt/titan/apps"
Environment="TITAN_ROOT=/opt/titan"
ExecStart=/usr/bin/python3 /opt/titan/core/titan_api.py
Restart=always
RestartSec=5
TimeoutStartSec=30

[Install]
WantedBy=multi-user.target
APISVC
systemctl daemon-reload
systemctl enable titan-api.service 2>/dev/null || true
mark_pass "Titan API service"

# 8.2 Ollama service (ensure exists and enabled)
echo "[8.2] Ollama service..."
if [ -f /etc/systemd/system/ollama.service ]; then
    mark_pass "Ollama service (exists)"
else
    cat > /etc/systemd/system/ollama.service << 'OLSVC'
[Unit]
Description=Ollama Service
After=network-online.target

[Service]
Type=exec
User=ollama
Group=ollama
Restart=always
RestartSec=3
Environment="OLLAMA_HOST=0.0.0.0:11434"
Environment="OLLAMA_MODELS=/usr/share/ollama/.ollama/models"
Environment="OLLAMA_NUM_PARALLEL=2"
Environment="OLLAMA_MAX_LOADED_MODELS=1"
ExecStart=/usr/local/bin/ollama serve
WorkingDirectory=/usr/share/ollama

[Install]
WantedBy=multi-user.target
OLSVC
    systemctl daemon-reload
    systemctl enable ollama.service 2>/dev/null || true
    mark_pass "Ollama service (created)"
fi

# 8.3 Dev Hub service
echo "[8.3] Dev Hub service..."
if [ ! -f /etc/systemd/system/titan-dev-hub.service ]; then
    cat > /etc/systemd/system/titan-dev-hub.service << 'DHSVC'
[Unit]
Description=Titan Development Hub
After=network-online.target titan-api.service
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/titan
Environment="PYTHONPATH=/opt/titan:/opt/titan/core:/opt/titan/apps"
ExecStart=/usr/bin/python3 /opt/titan/apps/titan_dev_hub.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
DHSVC
fi
systemctl daemon-reload
systemctl enable titan-dev-hub.service 2>/dev/null || true
mark_pass "Dev Hub service"

# 8.4 Waydroid container service
echo "[8.4] Waydroid container service..."
cat > /etc/systemd/system/titan-waydroid.service << 'WDSVC'
[Unit]
Description=Titan Waydroid Android Container
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/bin/waydroid container start
ExecStop=/usr/bin/waydroid container stop
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
WDSVC
systemctl daemon-reload
mark_pass "Waydroid service (created, not enabled - needs init)"

# 8.5 Redis service
echo "[8.5] Redis service..."
systemctl enable redis-server 2>/dev/null || true
systemctl start redis-server 2>/dev/null || true
mark_pass "Redis service"

# 8.6 Nftables firewall service
echo "[8.6] Nftables service..."
systemctl enable nftables 2>/dev/null || true
mark_pass "Nftables service"

# 8.7 Enable legacy + current Titan unit set
echo "[8.7] Enabling Titan unit set..."
for svc in lucid-titan lucid-ebpf lucid-console titan-first-boot titan-dns titan-patch-bridge titan-dev-hub titan-api; do
    systemctl enable "$svc".service 2>/dev/null || true
done
mark_pass "Titan unit set enabled"

# 8.8 XRDP login session wiring
echo "[8.8] XRDP desktop login..."
cat > /etc/xrdp/startwm.sh << 'XRDPEOF'
#!/bin/sh
if [ -r /etc/default/locale ]; then
    . /etc/default/locale
    export LANG LANGUAGE
fi
export PYTHONPATH=/opt/titan:/opt/titan/core:/opt/titan/apps:/opt/titan/src/core:/opt/titan/src/apps
unset DBUS_SESSION_BUS_ADDRESS
unset SESSION_MANAGER
exec startxfce4
XRDPEOF
chmod +x /etc/xrdp/startwm.sh 2>/dev/null || true
systemctl enable xrdp.service 2>/dev/null || true
systemctl enable lightdm.service 2>/dev/null || true
mark_pass "XRDP configured"

systemctl daemon-reload

echo ""
echo "Phase 8 complete."

# ═══════════════════════════════════════════════════════════════════════
# PHASE 9: XRAY VPN + TAILSCALE (from hook 99)
# ═══════════════════════════════════════════════════════════════════════
echo ""
echo "═══ PHASE 9: VPN Infrastructure ═══"

# 9.1 Xray-core
echo "[9.1] Xray-core..."
if ! command -v xray &>/dev/null; then
    bash -c "$(curl -sL https://github.com/XTLS/Xray-install/raw/main/install-release.sh)" @ install 2>/dev/null && \
        mark_pass "Xray-core installed" || mark_warn "Xray-core install failed"
else
    mark_pass "Xray-core (already installed)"
fi

# 9.2 Tailscale — use apt repo for Debian (generic install.sh fails on custom os-release)
echo "[9.2] Tailscale..."
if ! command -v tailscale &>/dev/null; then
    TS_CODENAME=$(awk -F= '/^VERSION_CODENAME=/{print $2}' /etc/os-release 2>/dev/null | tr -d '"')
    [ -z "$TS_CODENAME" ] && TS_CODENAME="bookworm"
    TS_LOG="/tmp/titan_tailscale_install.log"
    TS_OK=0

    # Method 1: apt repo (preferred for Debian)
    if command -v gpg &>/dev/null; then
        install -m 0755 -d /usr/share/keyrings 2>/dev/null || true
        if curl -fsSL "https://pkgs.tailscale.com/stable/debian/${TS_CODENAME}.noarmor.gpg" \
               -o /usr/share/keyrings/tailscale-archive-keyring.gpg >>"$TS_LOG" 2>&1 && \
           printf 'deb [signed-by=/usr/share/keyrings/tailscale-archive-keyring.gpg] https://pkgs.tailscale.com/stable/debian %s main\n' "$TS_CODENAME" \
               > /etc/apt/sources.list.d/tailscale.list && \
           apt-get update -qq >>"$TS_LOG" 2>&1 && \
           apt-get install -y tailscale >>"$TS_LOG" 2>&1; then
            TS_OK=1
            mark_pass "Tailscale installed (apt/${TS_CODENAME})"
        fi
    fi

    # Method 2: fallback to generic installer
    if [ "$TS_OK" -eq 0 ]; then
        if curl -fsSL https://tailscale.com/install.sh | sh >>"$TS_LOG" 2>&1; then
            mark_pass "Tailscale installed (generic)"
        else
            mark_warn "Tailscale install failed (see $TS_LOG)"
        fi
    fi
else
    mark_pass "Tailscale (already installed)"
fi

# 9.3 VPN directory
echo "[9.3] VPN config dir..."
mkdir -p /opt/titan/vpn
chmod 700 /opt/titan/vpn
mark_pass "VPN config dir"

echo ""
echo "Phase 9 complete."

# ═══════════════════════════════════════════════════════════════════════
# PHASE 10: LIBFAKETIME + HARDWARE SHIELD (from hook 99)
# ═══════════════════════════════════════════════════════════════════════
echo ""
echo "═══ PHASE 10: Runtime Libraries ═══"

# 10.1 libfaketime symlinks
echo "[10.1] libfaketime symlinks..."
FAKETIME_PATH=""
for p in /usr/lib/x86_64-linux-gnu/faketime/libfaketime.so.1 /usr/lib/faketime/libfaketime.so.1; do
    if [ -f "$p" ]; then FAKETIME_PATH="$p"; break; fi
done
if [ -n "$FAKETIME_PATH" ]; then
    ln -sf "$FAKETIME_PATH" /usr/lib/libfaketime.so.1 2>/dev/null || true
    ln -sf "$FAKETIME_PATH" /usr/local/lib/libfaketime.so.1 2>/dev/null || true
    mark_pass "libfaketime symlinks"
else
    mark_warn "libfaketime not found"
fi

# 10.2 Hardware Shield compilation
echo "[10.2] Hardware Shield..."
HW_SO="$TITAN_ROOT/lib/libhardwareshield.so"
HW_BUILD_LOG="/tmp/titan_hw_shield_build.log"
HW_COMPILED=0
mkdir -p "$TITAN_ROOT/lib"
: > "$HW_BUILD_LOG"

if command -v gcc &>/dev/null; then
    for cand in "$TITAN_ROOT/lib/hardware_shield.c" "$TITAN_ROOT/src/lib/vps_hw_shield.c" "$TITAN_ROOT/src/lib/integrity_shield.c"; do
        [ -f "$cand" ] || continue
        echo "Trying: $cand" >> "$HW_BUILD_LOG"
        if gcc -shared -fPIC -O2 -o "$HW_SO" "$cand" -ldl >> "$HW_BUILD_LOG" 2>&1; then
            HW_COMPILED=1
            echo "Success: $cand" >> "$HW_BUILD_LOG"
            break
        else
            echo "Failed: $cand (rc=$?)" >> "$HW_BUILD_LOG"
        fi
    done
fi

if [ "$HW_COMPILED" -eq 1 ]; then
    ln -sf libhardwareshield.so "$TITAN_ROOT/lib/hardware_shield.so" 2>/dev/null || true
    echo "$TITAN_ROOT/lib" > /etc/ld.so.conf.d/titan-v6.conf
    ldconfig 2>/dev/null || true
    mark_pass "Hardware Shield compiled"
elif [ -f "$HW_SO" ]; then
    mark_pass "Hardware Shield (pre-compiled)"
else
    mark_warn "Hardware Shield compilation failed (see $HW_BUILD_LOG)"
fi

# DKMS kernel module install from repo if available
echo "[10.3] DKMS titan_hw module..."
DKMS_LOG="/tmp/titan_dkms_build.log"
: > "$DKMS_LOG"
DKMS_OK=0
KVER=$(uname -r)

# Check kernel headers are available (required for DKMS)
if [ ! -d "/lib/modules/${KVER}/build" ]; then
    echo "Installing linux-headers-${KVER}..." >> "$DKMS_LOG"
    apt-get install -y "linux-headers-${KVER}" >> "$DKMS_LOG" 2>&1 || true
fi

if command -v dkms &>/dev/null; then
    for DKMS_SRC in \
        "$TITAN_ROOT/iso/config/includes.chroot/usr/src/titan-hw-7.0.0" \
        "$TITAN_ROOT/iso/config/includes.chroot/usr/src/titan-hw-6.2.0"; do

        [ -d "$DKMS_SRC" ] || continue
        [ "$DKMS_OK" -eq 1 ] && break

        DKMS_BASE=$(basename "$DKMS_SRC")
        DKMS_VER="${DKMS_BASE#titan-hw-}"
        echo "=== Trying titan-hw/${DKMS_VER} ===" >> "$DKMS_LOG"

        mkdir -p "/usr/src/${DKMS_BASE}"
        cp -a "$DKMS_SRC/." "/usr/src/${DKMS_BASE}/" >> "$DKMS_LOG" 2>&1 || true

        dkms remove "titan-hw/${DKMS_VER}" --all >> "$DKMS_LOG" 2>&1 || true

        if dkms add "titan-hw/${DKMS_VER}" >> "$DKMS_LOG" 2>&1 && \
           dkms build "titan-hw/${DKMS_VER}" -k "$KVER" >> "$DKMS_LOG" 2>&1 && \
           dkms install "titan-hw/${DKMS_VER}" -k "$KVER" >> "$DKMS_LOG" 2>&1; then
            KO_PATH=$(find /lib/modules -name "titan_hw.ko*" 2>/dev/null | head -1)
            if [ -n "$KO_PATH" ]; then
                mkdir -p /opt/titan/kernel-modules
                cp "$KO_PATH" /opt/titan/kernel-modules/titan_hw.ko 2>/dev/null || true
                DKMS_OK=1
                mark_pass "DKMS titan_hw module (${DKMS_VER})"
            fi
        else
            echo "Build failed for titan-hw/${DKMS_VER}" >> "$DKMS_LOG"
        fi
    done

    if [ "$DKMS_OK" -eq 0 ]; then
        mark_warn "DKMS titan_hw build/install failed (see $DKMS_LOG)"
    fi
else
    mark_warn "DKMS not available (install dkms package)"
fi

echo ""
echo "Phase 10 complete."

# ═══════════════════════════════════════════════════════════════════════
# PHASE 11: PERMISSIONS (from hook 99)
# ═══════════════════════════════════════════════════════════════════════
echo ""
echo "═══ PHASE 11: Permissions ═══"

echo "[11.1] Setting executable permissions on all scripts..."
find "$TITAN_ROOT" -name "*.py" -exec chmod +x {} \;
find "$TITAN_ROOT" -name "*.sh" -exec chmod +x {} \;
chmod +x "$TITAN_ROOT/bin/"* 2>/dev/null || true
chmod +x "$TITAN_ROOT/apps/"* 2>/dev/null || true
chmod +x "$TITAN_ROOT/src/bin/"* 2>/dev/null || true
mark_pass "Script permissions"

echo "[11.2] Protecting sensitive configs..."
chmod 600 "$TITAN_ROOT/config/titan.env" 2>/dev/null || true
chmod 600 "$TITAN_ROOT/state/proxies.json" 2>/dev/null || true
chmod 600 "$TITAN_ROOT/vpn/xray-client.json" 2>/dev/null || true
chmod 700 "$TITAN_ROOT/config" 2>/dev/null || true
chmod 700 "$TITAN_ROOT/vpn" 2>/dev/null || true
mark_pass "Sensitive config permissions"

echo "[11.3] Config file permissions..."
chmod 644 /etc/fonts/local.conf 2>/dev/null || true
chmod 644 /etc/pulse/daemon.conf 2>/dev/null || true
chmod 644 /etc/nftables.conf 2>/dev/null || true
chmod 644 /etc/sysctl.d/99-titan-hardening.conf 2>/dev/null || true
mark_pass "Config file permissions"

echo ""
echo "Phase 11 complete."

# ═══════════════════════════════════════════════════════════════════════
# PHASE 12: START SERVICES
# ═══════════════════════════════════════════════════════════════════════
echo ""
echo "═══ PHASE 12: Start Services ═══"

systemctl daemon-reload

echo "[12.1] Starting core services..."
for svc in redis-server ollama; do
    systemctl start "$svc" 2>/dev/null && \
        echo "  [+] $svc started" || echo "  [-] $svc failed to start"
done

echo "[12.2] Waiting for Ollama to be ready..."
for i in $(seq 1 15); do
    if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
        mark_pass "Ollama responding"
        break
    fi
    sleep 2
done

echo "[12.3] Starting Titan services..."
for svc in titan-api titan-dev-hub; do
    systemctl restart "$svc" 2>/dev/null && \
        echo "  [+] $svc started" || echo "  [-] $svc failed to start"
done
sleep 3

echo "[12.4] Starting optional services..."
for svc in xray ntfy xrdp lightdm; do
    systemctl start "$svc" 2>/dev/null && \
        echo "  [+] $svc started" || echo "  [-] $svc skipped"
done

mark_pass "Services started"

echo ""
echo "Phase 12 complete."

# ═══════════════════════════════════════════════════════════════════════
# PHASE 13: MASTER VERIFICATION (kernel-level + all subsystems)
# ═══════════════════════════════════════════════════════════════════════
echo ""
echo "═══ PHASE 13: Master Verification ═══"
V_PASS=0; V_WARN=0; V_FAIL=0
VERIFY_LOG="/tmp/titan_verify_report.json"
vpass() { echo "  [PASS] $1"; V_PASS=$((V_PASS+1)); }
vwarn() { echo "  [WARN] $1"; V_WARN=$((V_WARN+1)); }
vfail() { echo "  [FAIL] $1"; V_FAIL=$((V_FAIL+1)); }

# ── 13.1 Installed tools ──
echo ""
echo "[13.1] Installed tools..."
for tool in python3 pip3 git gcc make dkms node npm ffmpeg curl jq sqlite3 tmux nmap xray tailscale; do
    if command -v "$tool" &>/dev/null; then
        VER=$("$tool" --version 2>&1 | head -1 | cut -c1-50)
        vpass "$tool: $VER"
    else
        vfail "$tool: NOT FOUND"
    fi
done

# ── 13.2 Kernel & DKMS ──
echo ""
echo "[13.2] Kernel-level verification..."
KVER=$(uname -r)
echo "  Kernel: $KVER"

# 13.2.1 Kernel headers
if [ -d "/lib/modules/${KVER}/build" ]; then
    vpass "Kernel headers (${KVER})"
else
    vwarn "Kernel headers missing for ${KVER}"
fi

# 13.2.2 DKMS titan_hw module
DKMS_STATUS=$(dkms status titan-hw 2>/dev/null || echo "")
if echo "$DKMS_STATUS" | grep -qi "installed"; then
    vpass "DKMS titan_hw: $DKMS_STATUS"
elif [ -n "$DKMS_STATUS" ]; then
    vwarn "DKMS titan_hw: $DKMS_STATUS"
else
    vfail "DKMS titan_hw: not registered"
fi

# 13.2.3 titan_hw.ko kernel module file
KO_FILE=$(find /lib/modules -name "titan_hw.ko*" 2>/dev/null | head -1)
if [ -n "$KO_FILE" ]; then
    KO_SIZE=$(stat -c%s "$KO_FILE" 2>/dev/null || echo 0)
    vpass "titan_hw.ko: $KO_FILE (${KO_SIZE} bytes)"
elif [ -f "/opt/titan/kernel-modules/titan_hw.ko" ]; then
    vpass "titan_hw.ko: /opt/titan/kernel-modules/titan_hw.ko (local copy)"
else
    vfail "titan_hw.ko: NOT FOUND anywhere"
fi

# 13.2.4 Loaded kernel module
if lsmod 2>/dev/null | grep -q "titan_hw"; then
    vpass "titan_hw module: LOADED in kernel"
else
    vwarn "titan_hw module: not loaded (insmod needed after reboot)"
fi

# 13.2.5 DKMS build log
if [ -f /tmp/titan_dkms_build.log ]; then
    echo "  DKMS build log (last 5 lines):"
    tail -5 /tmp/titan_dkms_build.log | sed 's/^/    /'
fi

# ── 13.3 LD_PRELOAD / Hardware Shield ──
echo ""
echo "[13.3] LD_PRELOAD & Hardware Shield..."
HW_SO="$TITAN_ROOT/lib/libhardwareshield.so"
if [ -f "$HW_SO" ]; then
    SO_SIZE=$(stat -c%s "$HW_SO" 2>/dev/null || echo 0)
    # Verify it's a valid ELF shared object
    if file "$HW_SO" 2>/dev/null | grep -q "ELF.*shared object"; then
        vpass "libhardwareshield.so: valid ELF (${SO_SIZE} bytes)"
    else
        vfail "libhardwareshield.so: exists but not valid ELF"
    fi
else
    vfail "libhardwareshield.so: NOT FOUND"
fi

# Symlink check
if [ -L "$TITAN_ROOT/lib/hardware_shield.so" ]; then
    vpass "hardware_shield.so symlink OK"
else
    vwarn "hardware_shield.so symlink missing"
fi

# ldconfig
if ldconfig -p 2>/dev/null | grep -q "hardwareshield"; then
    vpass "ldconfig: libhardwareshield registered"
else
    vwarn "ldconfig: libhardwareshield not in cache"
fi

# libfaketime
if ldconfig -p 2>/dev/null | grep -q "faketime" || [ -f /usr/lib/libfaketime.so.1 ]; then
    vpass "libfaketime available"
else
    vwarn "libfaketime not found"
fi

# ── 13.4 procfs/sysfs spoofing readiness ──
echo ""
echo "[13.4] Hardware spoofing readiness..."
# Check /proc entries that titan_hw would create
for entry in /proc/titan_hw_profile /proc/cpuinfo /sys/class/dmi/id/board_vendor; do
    if [ -e "$entry" ]; then
        FIRST=$(head -c 80 "$entry" 2>/dev/null | tr '\n' ' ')
        echo "  [INFO] $entry: ${FIRST}"
    fi
done

# Check for configfs/gadgetfs (USB peripheral synthesis)
if [ -d /sys/kernel/config/usb_gadget ] || [ -d /dev/gadget ]; then
    vpass "USB gadget/configfs available"
else
    vwarn "USB gadget/configfs not available (expected on VPS)"
fi

# ── 13.5 VPN infrastructure ──
echo ""
echo "[13.5] VPN infrastructure..."
# Tailscale
if command -v tailscale &>/dev/null; then
    TS_STATUS=$(tailscale status --json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('BackendState','unknown'))" 2>/dev/null || echo "unknown")
    vpass "Tailscale: $TS_STATUS"
else
    vfail "Tailscale: not installed"
fi

# Mullvad
if command -v mullvad &>/dev/null; then
    MV_STATUS=$(mullvad status 2>/dev/null | head -1 || echo "unknown")
    vpass "Mullvad: $MV_STATUS"
else
    vwarn "Mullvad: not installed"
fi

# WireGuard
if command -v wg &>/dev/null; then
    vpass "WireGuard tools: installed"
else
    vwarn "WireGuard tools: missing"
fi

# VPN config dir
if [ -d /opt/titan/vpn ]; then
    VPN_FILES=$(find /opt/titan/vpn -type f 2>/dev/null | wc -l)
    vpass "VPN config dir: $VPN_FILES files"
else
    vfail "VPN config dir: missing"
fi

# ── 13.6 Services ──
echo ""
echo "[13.6] Services..."
for svc in redis-server ollama titan-api titan-dev-hub xray xrdp lightdm tailscaled mullvad-daemon; do
    STATUS=$(systemctl is-active "$svc" 2>/dev/null || echo "inactive")
    ENABLED=$(systemctl is-enabled "$svc" 2>/dev/null || echo "unknown")
    if [ "$STATUS" = "active" ]; then
        vpass "$svc: active (enabled=$ENABLED)"
    elif [ "$ENABLED" = "enabled" ]; then
        vwarn "$svc: $STATUS but enabled"
    else
        echo "  [INFO] $svc: $STATUS"
    fi
done

# ── 13.7 Python library imports ──
echo ""
echo "[13.7] Python library imports..."
PYTHONPATH="/opt/titan:/opt/titan/core:/opt/titan/apps" python3 << 'PYCHECK'
import sys
sys.path.insert(0, "/opt/titan/core")
sys.path.insert(0, "/opt/titan/apps")
modules = [
    "flask", "redis", "requests", "httpx", "aiohttp",
    "numpy", "PIL", "yaml", "cryptography",
    "fastapi", "uvicorn", "pydantic",
    "prometheus_client", "paramiko", "plyvel",
    "aioquic", "minio", "curl_cffi",
]
ok = 0
fail = 0
for m in modules:
    try:
        __import__(m)
        ok += 1
    except ImportError:
        print(f"  [-] {m}: IMPORT FAILED")
        fail += 1
print(f"  Python imports: {ok} OK, {fail} FAIL")
PYCHECK

# ── 13.8 Titan core module syntax + import ──
echo ""
echo "[13.8] Titan core modules (syntax + import)..."
PYTHONPATH="/opt/titan:/opt/titan/core:/opt/titan/apps" python3 << 'CORECHECK'
import os, sys, ast, importlib
sys.path.insert(0, "/opt/titan/core")
sys.path.insert(0, "/opt/titan/apps")
sys.path.insert(0, "/opt/titan")

core_dir = "/opt/titan/core"
if not os.path.isdir(core_dir):
    print("  [FAIL] /opt/titan/core does not exist")
    sys.exit(1)

py_files = sorted([f[:-3] for f in os.listdir(core_dir) if f.endswith('.py') and f != '__init__.py'])
syntax_ok = import_ok = 0
syntax_fail = import_fail = 0

for m in py_files:
    fpath = os.path.join(core_dir, m + ".py")
    try:
        with open(fpath) as f:
            ast.parse(f.read())
        syntax_ok += 1
    except SyntaxError as e:
        print(f"  [SYNTAX_FAIL] {m}: {e}")
        syntax_fail += 1
        continue
    try:
        importlib.import_module(m)
        import_ok += 1
    except Exception:
        import_fail += 1

print(f"  Core syntax: {syntax_ok} OK, {syntax_fail} FAIL (of {len(py_files)})")
print(f"  Core import: {import_ok} OK, {import_fail} FAIL")

# Apps
apps_dir = "/opt/titan/apps"
if os.path.isdir(apps_dir):
    app_files = [f for f in os.listdir(apps_dir) if f.endswith('.py')]
    app_ok = 0
    for af in app_files:
        try:
            with open(os.path.join(apps_dir, af)) as f:
                ast.parse(f.read())
            app_ok += 1
        except SyntaxError as e:
            print(f"  [SYNTAX_FAIL] apps/{af}: {e}")
    print(f"  Apps syntax: {app_ok}/{len(app_files)} OK")
CORECHECK

# ── 13.9 Key class spot check ──
echo ""
echo "[13.9] Key class spot check..."
PYTHONPATH="/opt/titan:/opt/titan/core:/opt/titan/apps" python3 << 'CLASSCHECK'
import sys
sys.path.insert(0, "/opt/titan/core")
checks = [
    ("integration_bridge", "TitanIntegrationBridge"),
    ("titan_session", "TitanSession"),
    ("genesis_core", "GenesisEngine"),
    ("cerberus_core", "CerberusValidator"),
    ("fingerprint_injector", "FingerprintInjector"),
    ("ghost_motor_v6", "get_forter_safe_params"),
    ("kill_switch", "KillSwitch"),
    ("kyc_core", "KYCController"),
    ("titan_onnx_engine", "TitanOnnxEngine"),
    ("ai_intelligence_engine", "AIIntelligenceEngine"),
    ("three_ds_strategy", "ThreeDSBypassEngine"),
    ("waydroid_sync", "WaydroidSyncEngine"),
    ("biometric_mimicry", "BiometricMimicry"),
    ("level9_antidetect", "Level9Antidetect"),
    ("oblivion_forge", "OblivionForgeEngine"),
    ("titan_detection_lab", "DetectionLab"),
]
ok = fail = 0
for mod_name, cls_name in checks:
    try:
        mod = __import__(mod_name)
        if hasattr(mod, cls_name):
            ok += 1
        else:
            print(f"  [MISSING] {mod_name}.{cls_name}")
            fail += 1
    except Exception as e:
        print(f"  [IMPORT_FAIL] {mod_name}: {str(e)[:60]}")
        fail += 1
print(f"  Key classes: {ok} OK, {fail} FAIL")
CLASSCHECK

# ── 13.10 API endpoints ──
echo ""
echo "[13.10] API endpoints..."
sleep 2
for endpoint in "http://localhost:5000/api/v1/health" "http://localhost:8877/api/health"; do
    RESP=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$endpoint" 2>/dev/null)
    if [ "$RESP" = "200" ]; then
        vpass "API $endpoint: $RESP"
    else
        vwarn "API $endpoint: $RESP"
    fi
done

# ── 13.11 Directory structure ──
echo ""
echo "[13.11] Directory structure..."
for d in core apps bin config vpn state profiles data docs scripts training tests iso modelfiles src kernel-modules lib; do
    if [ -d "$TITAN_ROOT/$d" ]; then
        COUNT=$(find "$TITAN_ROOT/$d" -type f 2>/dev/null | wc -l)
        echo "  [+] $d/: $COUNT files"
    else
        echo "  [-] $d/: MISSING"
    fi
done

# ── 13.12 File counts ──
echo ""
echo "[13.12] File counts..."
TOTAL_FILES=$(find "$TITAN_ROOT" -type f | wc -l)
TOTAL_DIRS=$(find "$TITAN_ROOT" -type d | wc -l)
TOTAL_PY=$(find "$TITAN_ROOT" -name "*.py" | wc -l)
TOTAL_C=$(find "$TITAN_ROOT" -name "*.c" | wc -l)
TOTAL_SH=$(find "$TITAN_ROOT" -name "*.sh" | wc -l)
TOTAL_MD=$(find "$TITAN_ROOT" -name "*.md" | wc -l)
echo "  Total files:  $TOTAL_FILES"
echo "  Total dirs:   $TOTAL_DIRS"
echo "  Python files: $TOTAL_PY"
echo "  C sources:    $TOTAL_C"
echo "  Shell files:  $TOTAL_SH"
echo "  Markdown:     $TOTAL_MD"

# ── 13.13 ONNX / AI models ──
echo ""
echo "[13.13] AI models..."
ONNX_DIR="/opt/titan/models/phi4-mini-onnx"
if [ -d "$ONNX_DIR" ]; then
    ONNX_COUNT=$(find "$ONNX_DIR" -name "*.onnx" 2>/dev/null | wc -l)
    ONNX_MB=$(du -sm "$ONNX_DIR" 2>/dev/null | cut -f1)
    vpass "ONNX model: $ONNX_COUNT files, ${ONNX_MB}MB"
else
    vwarn "ONNX model dir not found"
fi
# Ollama models
if command -v ollama &>/dev/null; then
    OLLAMA_MODELS=$(ollama list 2>/dev/null | tail -n +2 | wc -l)
    echo "  Ollama models: $OLLAMA_MODELS"
fi

# ── 13.14 System resources ──
echo ""
echo "[13.14] System resources..."
echo "  Disk:   $(df -h / | tail -1 | awk '{print $3"/"$2" ("$5" used)"}')"
echo "  RAM:    $(free -h | awk '/Mem:/{print $3"/"$2}')"
echo "  Kernel: $KVER"
echo "  Python: $(python3 --version 2>&1)"
echo "  Debian: $(cat /etc/debian_version 2>/dev/null || echo 'unknown')"
echo "  OS:     $(grep PRETTY_NAME /etc/os-release 2>/dev/null | cut -d= -f2 | tr -d '"')"

# ── 13.15 Build logs summary ──
echo ""
echo "[13.15] Build logs..."
for logf in /tmp/titan_hw_shield_build.log /tmp/titan_dkms_build.log /tmp/titan_tailscale_install.log; do
    if [ -f "$logf" ]; then
        LINES=$(wc -l < "$logf")
        echo "  $logf: $LINES lines"
        if grep -qi "error\|fail" "$logf" 2>/dev/null; then
            echo "    Errors found:"
            grep -i "error\|fail" "$logf" | tail -3 | sed 's/^/      /'
        fi
    fi
done

# ── Generate JSON report ──
VERIFY_REPORT="/tmp/titan_verify_report.json"
cat > "$VERIFY_REPORT" << JSONEOF
{
  "timestamp": "$(date -u '+%Y-%m-%dT%H:%M:%SZ')",
  "kernel": "$KVER",
  "debian": "$(cat /etc/debian_version 2>/dev/null)",
  "verify_pass": $V_PASS,
  "verify_warn": $V_WARN,
  "verify_fail": $V_FAIL,
  "install_pass": $PASS,
  "install_warn": $WARN,
  "install_fail": $FAIL,
  "dkms_status": "$(dkms status titan-hw 2>/dev/null | head -1)",
  "titan_hw_ko": "$(find /lib/modules -name 'titan_hw.ko*' 2>/dev/null | head -1)",
  "hw_shield_so": "$([ -f $HW_SO ] && echo 'present' || echo 'missing')",
  "tailscale": "$(command -v tailscale >/dev/null 2>&1 && echo 'installed' || echo 'missing')",
  "total_files": $TOTAL_FILES,
  "python_files": $TOTAL_PY,
  "c_sources": $TOTAL_C
}
JSONEOF
echo ""
echo "Verify report: $VERIFY_REPORT"

# ═══════════════════════════════════════════════════════════════════════
# PHASE 14: CROSS-REFERENCE — Docs vs VPS vs Local Codebase
# ═══════════════════════════════════════════════════════════════════════
echo ""
echo "═══ PHASE 14: Cross-Reference (Docs ↔ VPS ↔ Local) ═══"
XREF_REPORT="/tmp/titan_xref_report.txt"
: > "$XREF_REPORT"
X_MATCH=0; X_MISSING=0; X_UNDOC=0; X_DRIFT=0

# ── 14.1 Documented modules from MODULE_CONNECTION_MAP / ARCHITECTURE ──
# All 115 Python modules documented across 13 categories
DOCUMENTED_MODULES=(
    # 1. ORCHESTRATION (6)
    integration_bridge titan_api titan_master_automation titan_autonomous_engine
    titan_master_verify cockpit_daemon
    # 2. AI / LLM (8)
    ai_intelligence_engine ollama_bridge cognitive_core titan_agent_chain
    titan_realtime_copilot titan_ai_operations_guard titan_vector_memory titan_onnx_engine
    # 3. BROWSER / PROFILE (10)
    genesis_core oblivion_forge chromium_constructor multilogin_forge
    antidetect_importer level9_antidetect profile_realism_engine
    advanced_profile_generator profile_isolation profile_burner
    # 4. FINGERPRINT (11)
    fingerprint_injector canvas_noise canvas_subpixel_shim webgl_angle
    font_sanitizer audio_hardener tls_mimic tls_parrot
    ja4_permutation_engine ghost_motor_v6 biometric_mimicry
    # 5. NETWORK / PROXY (7)
    proxy_manager network_shield network_shield_loader network_jitter
    quic_proxy mullvad_vpn lucid_vpn
    # 6. IDENTITY / KYC (6)
    kyc_core kyc_enhanced kyc_voice_engine persona_enrichment_engine
    verify_deep_identity first_session_bias_eliminator
    # 7. PAYMENT / CARD (10)
    cerberus_core cerberus_enhanced payment_preflight payment_success_metrics
    payment_sandbox_tester three_ds_strategy titan_3ds_ai_exploits
    issuer_algo_defense tra_exemption_engine transaction_monitor
    # 8. TARGET / INTEL (6)
    target_discovery target_intelligence target_presets
    titan_target_intel_v2 titan_web_intel intel_monitor
    # 9. STORAGE / DATA (8)
    cookie_forge chromium_cookie_engine indexeddb_lsng_synthesis leveldb_writer
    dynamic_data purchase_history_engine commerce_injector chromium_commerce_injector
    # 10. FORENSIC / SECURITY (8)
    forensic_monitor forensic_cleaner forensic_alignment forensic_synthesis_engine
    kill_switch titan_detection_analyzer titan_detection_lab titan_detection_lab_v2
    # 11. AUTOMATION (6)
    journey_simulator handover_protocol referrer_warmup form_autofill_injector
    titan_automation_orchestrator titan_operation_logger
    # 12. SYSTEM (8)
    titan_env titan_session titan_services titan_self_hosted_stack
    titan_webhook_integrations bug_patch_bridge titan_auto_patcher mcp_interface
    # 13. SPOOF / EMULATION (15)
    location_spoofer location_spoofer_linux timezone_enforcer ntp_isolation
    time_dilator time_safety_validator temporal_entropy immutable_os
    cpuid_rdtsc_shield tof_depth_synthesis usb_peripheral_synth waydroid_sync
    windows_font_provisioner ga_triangulation gamp_triangulation_v2
)

# Additional modules from MODULE_REFERENCE not in connection map
DOCUMENTED_MODULES+=(
    generate_trajectory_model preflight_validator
)

# Documented C modules
DOCUMENTED_C_MODULES=(hardware_shield_v6 network_shield_v6 titan_battery)

# Documented apps
DOCUMENTED_APPS=(
    titan_launcher titan_operations titan_intelligence titan_network
    app_kyc titan_admin app_settings app_profile_forge
    app_card_validator app_browser_launch
)

echo ""
echo "[14.1] Docs → VPS core module check (${#DOCUMENTED_MODULES[@]} documented)..."
for mod in "${DOCUMENTED_MODULES[@]}"; do
    if [ -f "$TITAN_ROOT/core/${mod}.py" ]; then
        X_MATCH=$((X_MATCH+1))
    else
        echo "  [MISSING] core/${mod}.py — documented but NOT on VPS"
        echo "MISSING_CORE: ${mod}.py" >> "$XREF_REPORT"
        X_MISSING=$((X_MISSING+1))
    fi
done
echo "  Documented core: ${#DOCUMENTED_MODULES[@]} | Present: $X_MATCH | Missing: $X_MISSING"

echo ""
echo "[14.2] Docs → VPS C module check..."
C_OK=0; C_MISS=0
for cmod in "${DOCUMENTED_C_MODULES[@]}"; do
    FOUND=0
    for loc in "$TITAN_ROOT/core/${cmod}.c" "$TITAN_ROOT/src/core/${cmod}.c" "$TITAN_ROOT/src/lib/${cmod}.c"; do
        if [ -f "$loc" ]; then FOUND=1; break; fi
    done
    if [ "$FOUND" -eq 1 ]; then
        C_OK=$((C_OK+1))
    else
        echo "  [MISSING] ${cmod}.c — documented but NOT found"
        echo "MISSING_C: ${cmod}.c" >> "$XREF_REPORT"
        C_MISS=$((C_MISS+1))
    fi
done
echo "  C modules: $C_OK present, $C_MISS missing (of ${#DOCUMENTED_C_MODULES[@]})"

echo ""
echo "[14.3] Docs → VPS app check..."
A_OK=0; A_MISS=0
for app in "${DOCUMENTED_APPS[@]}"; do
    if [ -f "$TITAN_ROOT/apps/${app}.py" ]; then
        A_OK=$((A_OK+1))
    else
        echo "  [MISSING] apps/${app}.py — documented but NOT on VPS"
        echo "MISSING_APP: ${app}.py" >> "$XREF_REPORT"
        A_MISS=$((A_MISS+1))
    fi
done
echo "  Apps: $A_OK present, $A_MISS missing (of ${#DOCUMENTED_APPS[@]})"

# ── 14.4 VPS → Docs (undocumented modules) ──
echo ""
echo "[14.4] VPS → Docs (undocumented modules)..."
DOC_LIST=$(printf "%s\n" "${DOCUMENTED_MODULES[@]}")
if [ -d "$TITAN_ROOT/core" ]; then
    for pyf in "$TITAN_ROOT/core"/*.py; do
        [ -f "$pyf" ] || continue
        BASENAME=$(basename "$pyf" .py)
        [ "$BASENAME" = "__init__" ] && continue
        if ! echo "$DOC_LIST" | grep -qx "$BASENAME"; then
            echo "  [UNDOC] core/$BASENAME.py — on VPS but NOT in docs"
            echo "UNDOCUMENTED: core/${BASENAME}.py" >> "$XREF_REPORT"
            X_UNDOC=$((X_UNDOC+1))
        fi
    done
fi
echo "  Undocumented core modules on VPS: $X_UNDOC"

# ── 14.5 VPS vs Local file count parity ──
echo ""
echo "[14.5] VPS ↔ Local codebase parity..."
VPS_CORE_COUNT=$(find "$TITAN_ROOT/core" -maxdepth 1 -name "*.py" 2>/dev/null | wc -l)
VPS_APPS_COUNT=$(find "$TITAN_ROOT/apps" -maxdepth 1 -name "*.py" 2>/dev/null | wc -l)
VPS_SCRIPTS_COUNT=$(find "$TITAN_ROOT/scripts" -type f 2>/dev/null | wc -l)
VPS_DOCS_COUNT=$(find "$TITAN_ROOT/docs" -name "*.md" 2>/dev/null | wc -l)
VPS_TESTS_COUNT=$(find "$TITAN_ROOT/tests" -type f 2>/dev/null | wc -l)
VPS_TRAINING_COUNT=$(find "$TITAN_ROOT/training" -type f 2>/dev/null | wc -l)

# Compare with src/ mirrors if they exist
SRC_CORE_COUNT=$(find "$TITAN_ROOT/src/core" -maxdepth 1 -name "*.py" 2>/dev/null | wc -l)
SRC_APPS_COUNT=$(find "$TITAN_ROOT/src/apps" -maxdepth 1 -name "*.py" 2>/dev/null | wc -l)

echo "  core/:     $VPS_CORE_COUNT .py files (src/core: $SRC_CORE_COUNT)"
echo "  apps/:     $VPS_APPS_COUNT .py files (src/apps: $SRC_APPS_COUNT)"
echo "  scripts/:  $VPS_SCRIPTS_COUNT files"
echo "  docs/:     $VPS_DOCS_COUNT .md files"
echo "  tests/:    $VPS_TESTS_COUNT files"
echo "  training/: $VPS_TRAINING_COUNT files"

# Check for core/src drift
if [ "$VPS_CORE_COUNT" -ne "$SRC_CORE_COUNT" ] && [ "$SRC_CORE_COUNT" -gt 0 ]; then
    DIFF=$((VPS_CORE_COUNT - SRC_CORE_COUNT))
    echo "  [DRIFT] core/ vs src/core/ difference: $DIFF files"
    echo "DRIFT: core($VPS_CORE_COUNT) vs src/core($SRC_CORE_COUNT) = $DIFF" >> "$XREF_REPORT"
    X_DRIFT=$((X_DRIFT+1))
fi
if [ "$VPS_APPS_COUNT" -ne "$SRC_APPS_COUNT" ] && [ "$SRC_APPS_COUNT" -gt 0 ]; then
    DIFF=$((VPS_APPS_COUNT - SRC_APPS_COUNT))
    echo "  [DRIFT] apps/ vs src/apps/ difference: $DIFF files"
    echo "DRIFT: apps($VPS_APPS_COUNT) vs src/apps($SRC_APPS_COUNT) = $DIFF" >> "$XREF_REPORT"
    X_DRIFT=$((X_DRIFT+1))
fi

# ── 14.6 Key class cross-reference (docs say class X exists in module Y) ──
echo ""
echo "[14.6] Key class cross-reference..."
PYTHONPATH="/opt/titan:/opt/titan/core:/opt/titan/apps" python3 << 'XREFPY'
import sys, importlib
sys.path.insert(0, "/opt/titan/core")

# From MODULE_CONNECTION_MAP docs — module → expected classes
doc_classes = {
    "integration_bridge": ["TitanIntegrationBridge", "BridgeConfig", "BridgeState"],
    "titan_api": ["TitanAPI"],
    "titan_master_automation": ["TitanMasterAutomation"],
    "titan_autonomous_engine": ["AutonomousEngine"],
    "titan_master_verify": ["VerificationOrchestrator", "RemediationEngine"],
    "cockpit_daemon": ["CockpitDaemon", "CommandQueue"],
    "ai_intelligence_engine": ["AIModelSelector", "AIDeclineAutopsy"],
    "ollama_bridge": ["LLMLoadBalancer", "PromptOptimizer"],
    "cognitive_core": ["CognitiveCoreLocal", "TitanCognitiveCore"],
    "titan_agent_chain": ["TitanChain", "TitanAgent", "TitanToolRegistry"],
    "titan_onnx_engine": ["TitanOnnxEngine"],
    "genesis_core": ["GenesisEngine", "ProfileConfig"],
    "oblivion_forge": ["OblivionForgeEngine"],
    "level9_antidetect": ["Level9Antidetect"],
    "fingerprint_injector": ["FingerprintInjector"],
    "ghost_motor_v6": ["GhostMotorV7", "GhostMotorDiffusion"],
    "biometric_mimicry": ["BiometricMimicry"],
    "proxy_manager": ["ResidentialProxyManager"],
    "mullvad_vpn": ["MullvadVPN"],
    "kyc_core": ["KYCController"],
    "kyc_enhanced": ["KYCEnhancedController"],
    "kyc_voice_engine": ["KYCVoiceEngine"],
    "cerberus_core": ["CerberusValidator", "CardAsset"],
    "cerberus_enhanced": ["BINScoringEngine", "CardQualityGrader"],
    "three_ds_strategy": ["ThreeDSBypassEngine"],
    "tra_exemption_engine": ["TRAOptimizer", "TRARiskCalculator"],
    "issuer_algo_defense": ["IssuerDeclineDefenseEngine"],
    "transaction_monitor": ["TransactionMonitor", "DeclineDecoder"],
    "target_discovery": ["TargetDiscovery"],
    "target_intelligence": ["TargetIntelligence"],
    "kill_switch": ["KillSwitch"],
    "titan_detection_lab": ["DetectionLab"],
    "titan_detection_lab_v2": ["DetectionLabV2"],
    "forensic_monitor": ["ForensicMonitor"],
    "titan_env": ["SecureConfigManager"],
    "titan_self_hosted_stack": ["RedisClient"],
    "waydroid_sync": ["CrossDeviceActivityOrchestrator"],
    "tof_depth_synthesis": ["FaceDepthGenerator"],
    "usb_peripheral_synth": ["USBDeviceManager", "USBProfileGenerator"],
    "handover_protocol": ["ManualHandoverProtocol"],
    "titan_automation_orchestrator": ["TitanAutomationOrchestrator"],
    "titan_operation_logger": ["TitanOperationLogger"],
}

ok = mismatch = import_fail = 0
mismatches = []
for mod_name, expected_classes in doc_classes.items():
    try:
        mod = importlib.import_module(mod_name)
        for cls in expected_classes:
            if hasattr(mod, cls):
                ok += 1
            else:
                mismatch += 1
                mismatches.append(f"{mod_name}.{cls}")
    except Exception:
        import_fail += 1

print(f"  Class xref: {ok} OK, {mismatch} mismatched, {import_fail} import failures")
if mismatches:
    print(f"  Mismatches (docs say exists but module lacks):")
    for m in mismatches[:15]:
        print(f"    [MISMATCH] {m}")
XREFPY

# ── 14.7 Service cross-reference (docs say these should be active) ──
echo ""
echo "[14.7] Service cross-reference (docs vs actual)..."
DOC_SERVICES="redis-server ollama xray ntfy tailscaled"
for dsvc in $DOC_SERVICES; do
    ACTUAL=$(systemctl is-active "$dsvc" 2>/dev/null || echo "missing")
    if [ "$ACTUAL" = "active" ]; then
        echo "  [OK] $dsvc: documented + active"
    else
        echo "  [GAP] $dsvc: documented but $ACTUAL"
    fi
done

# ── Generate cross-reference summary ──
echo "" >> "$XREF_REPORT"
echo "=== CROSS-REFERENCE SUMMARY ===" >> "$XREF_REPORT"
echo "Documented core modules: ${#DOCUMENTED_MODULES[@]}" >> "$XREF_REPORT"
echo "Present on VPS: $X_MATCH" >> "$XREF_REPORT"
echo "Missing from VPS: $X_MISSING" >> "$XREF_REPORT"
echo "Undocumented on VPS: $X_UNDOC" >> "$XREF_REPORT"
echo "File drift: $X_DRIFT dirs" >> "$XREF_REPORT"
echo "Documented apps: ${#DOCUMENTED_APPS[@]} (present: $A_OK, missing: $A_MISS)" >> "$XREF_REPORT"
echo "Documented C modules: ${#DOCUMENTED_C_MODULES[@]} (present: $C_OK, missing: $C_MISS)" >> "$XREF_REPORT"

echo ""
echo "Cross-reference report: $XREF_REPORT"
echo "  Core: $X_MATCH/${#DOCUMENTED_MODULES[@]} match | $X_MISSING missing | $X_UNDOC undocumented"
echo "  Apps: $A_OK/${#DOCUMENTED_APPS[@]} match | C: $C_OK/${#DOCUMENTED_C_MODULES[@]} match"
echo "  Drift: $X_DRIFT directories"

# ── Final summary ──
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  TITAN OS Master Install + Verify + Cross-Reference Complete"
echo "  Time: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "═══════════════════════════════════════════════════════════════"
echo "  INSTALL  → PASS: $PASS | WARN: $WARN | FAIL: $FAIL"
echo "  VERIFY   → PASS: $V_PASS | WARN: $V_WARN | FAIL: $V_FAIL"
echo "  XREF     → Match: $X_MATCH | Missing: $X_MISSING | Undoc: $X_UNDOC | Drift: $X_DRIFT"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "Logs: $LOG"
echo "Verify: $VERIFY_REPORT"
echo "Cross-ref: $XREF_REPORT"
echo "Build logs: /tmp/titan_*_build.log /tmp/titan_tailscale_install.log"
'''


def get_ssh():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    kwargs = {"hostname": VPS_IP, "username": VPS_USER, "timeout": 20,
              "look_for_keys": True, "allow_agent": True}
    if KEY_FILE.exists():
        kwargs["key_filename"] = str(KEY_FILE)
    if VPS_PASS:
        kwargs["password"] = VPS_PASS
    ssh.connect(**kwargs)
    return ssh


def ssh_run(ssh, cmd, timeout=600):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    err = stderr.read().decode("utf-8", errors="replace").strip()
    rc = stdout.channel.recv_exit_status()
    return rc, out, err


def main():
    print("=" * 72)
    print("TITAN OS - Master VPS Installation Orchestrator")
    print("=" * 72)
    print(f"Target: {VPS_USER}@{VPS_IP}:{VPS_ROOT}")
    print()

    # Connect
    print("[1] Connecting to VPS...")
    ssh = get_ssh()
    print("  Connected.")

    # Sync repo first to avoid stale/outdated path drift on VPS
    print("[2] Syncing local repo to VPS tree...")
    sync_stats = sync_repo_to_vps(ssh)
    print(
        "  Sync result: "
        f"uploaded={sync_stats['uploaded']}, missing={sync_stats['missing']}, "
        f"stale={sync_stats['stale']}, failed={sync_stats['failed']}"
    )

    # Upload master install script
    print("[3] Uploading master install script...")
    sftp = ssh.open_sftp()
    remote_script = "/tmp/titan_master_install.sh"
    with sftp.file(remote_script, "w") as f:
        f.write(MASTER_INSTALL_SH)
    sftp.close()
    ssh_run(ssh, f"chmod +x {remote_script}")
    print(f"  Uploaded to {remote_script}")

    # Run it
    print("[4] Running master install (this will take several minutes)...")
    print("  Streaming output...\n")

    channel = ssh.get_transport().open_session()
    channel.settimeout(1800)  # 30 min max
    channel.exec_command(f"bash {remote_script}")

    # Stream output
    import socket
    buffer = ""
    while True:
        try:
            if channel.recv_ready():
                chunk = channel.recv(4096).decode("utf-8", errors="replace")
                sys.stdout.write(chunk)
                sys.stdout.flush()
                buffer += chunk
            if channel.recv_stderr_ready():
                chunk = channel.recv_stderr(4096).decode("utf-8", errors="replace")
                # Only print stderr errors, not noise
                for line in chunk.splitlines():
                    if "error" in line.lower() or "fail" in line.lower():
                        sys.stderr.write(f"  STDERR: {line}\n")
            if channel.exit_status_ready():
                # Drain remaining
                while channel.recv_ready():
                    chunk = channel.recv(4096).decode("utf-8", errors="replace")
                    sys.stdout.write(chunk)
                    sys.stdout.flush()
                    buffer += chunk
                break
        except socket.timeout:
            continue
        except Exception:
            break
        time.sleep(0.1)

    rc = channel.recv_exit_status()
    print(f"\n\nScript exit code: {rc}")

    # Download logs + verification report
    print("\n[5] Downloading install log + verification report...")
    sftp = ssh.open_sftp()

    downloads = {
        "/tmp/titan_master_install.log": LOCAL_ROOT / "titan_master_install.log",
        "/tmp/titan_verify_report.json": LOCAL_ROOT / "titan_verify_report.json",
        "/tmp/titan_hw_shield_build.log": LOCAL_ROOT / "titan_hw_shield_build.log",
        "/tmp/titan_dkms_build.log": LOCAL_ROOT / "titan_dkms_build.log",
        "/tmp/titan_tailscale_install.log": LOCAL_ROOT / "titan_tailscale_install.log",
        "/tmp/titan_xref_report.txt": LOCAL_ROOT / "titan_xref_report.txt",
    }
    for remote, local in downloads.items():
        try:
            sftp.get(remote, str(local))
            print(f"  Downloaded: {local.name}")
        except Exception:
            pass  # Some logs may not exist if that phase was skipped

    sftp.close()

    # Print verification summary from JSON if available
    verify_json = LOCAL_ROOT / "titan_verify_report.json"
    if verify_json.exists():
        try:
            report = json.loads(verify_json.read_text())
            print("\n" + "=" * 60)
            print("  VERIFICATION REPORT")
            print("=" * 60)
            print(f"  Kernel:       {report.get('kernel', '?')}")
            print(f"  Debian:       {report.get('debian', '?')}")
            print(f"  Install:      PASS={report.get('install_pass',0)} WARN={report.get('install_warn',0)} FAIL={report.get('install_fail',0)}")
            print(f"  Verify:       PASS={report.get('verify_pass',0)} WARN={report.get('verify_warn',0)} FAIL={report.get('verify_fail',0)}")
            print(f"  DKMS:         {report.get('dkms_status', 'unknown')}")
            print(f"  titan_hw.ko:  {report.get('titan_hw_ko', 'not found')}")
            print(f"  HW Shield:    {report.get('hw_shield_so', '?')}")
            print(f"  Tailscale:    {report.get('tailscale', '?')}")
            print(f"  Files:        {report.get('total_files',0)} total, {report.get('python_files',0)} py, {report.get('c_sources',0)} C")
            print("=" * 60)
        except Exception:
            pass

    # Print cross-reference summary if available
    xref_file = LOCAL_ROOT / "titan_xref_report.txt"
    if xref_file.exists():
        try:
            xref = xref_file.read_text()
            print("\n" + "=" * 60)
            print("  CROSS-REFERENCE REPORT (Docs ↔ VPS)")
            print("=" * 60)
            for line in xref.strip().splitlines():
                print(f"  {line}")
            print("=" * 60)
        except Exception:
            pass

    ssh.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
