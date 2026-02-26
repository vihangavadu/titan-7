#!/bin/bash
# =============================================================================
# TITAN OS V9.1 — Full ISO Build Script (VPS Edition)
# Run on VPS: bash /opt/titan/iso/build_iso_vps.sh
# =============================================================================
set -e
ISO_DIR="/opt/titan/iso"
TITAN_SRC="/opt/titan"
INCLUDES_DIR="$ISO_DIR/config/includes.chroot"
LOG="/tmp/titan_iso_build.log"
date +%s > /tmp/titan_build_start

exec > >(tee -a "$LOG") 2>&1
echo "============================================================"
echo "  TITAN OS V9.1 — ISO BUILD STARTED $(date)"
echo "============================================================"

# ── Phase 0: Pre-flight ───────────────────────────────────────────────────────
echo "[0/8] Pre-flight checks..."
FREE_GB=$(df -BG / | awk 'NR==2{print $4}' | tr -d 'G')
[ "$FREE_GB" -lt 20 ] && { echo "ERROR: Need 20GB free (have ${FREE_GB}GB)"; exit 1; }
echo "  Disk: ${FREE_GB}GB free | RAM: $(free -h | awk '/^Mem:/{print $2}') | CPU: $(nproc) cores"

# ── Phase 1: Install live-build ───────────────────────────────────────────────
echo "[1/8] Installing live-build..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y --no-install-recommends \
    live-build debootstrap squashfs-tools xorriso \
    isolinux syslinux-common grub-efi-amd64-bin grub-pc-bin \
    mtools dosfstools rsync curl wget ca-certificates 2>&1 | tail -3
echo "  live-build: $(lb --version 2>/dev/null || echo 'installed')"

# ── Phase 2: Sync codebase into ISO includes ─────────────────────────────────
echo "[2/8] Syncing Titan OS codebase into ISO includes..."

for d in core apps profgen config lib bin tools extensions patches \
          training/phase1 training/phase2 training/phase3 \
          vpn assets branding docs models modelfiles profiles state data \
          scripts src tests; do
    mkdir -p "$INCLUDES_DIR/opt/titan/$d"
done

rsync -a --exclude="__pycache__" --exclude="*.pyc" --exclude="*.bin" \
    --exclude="*.safetensors" --exclude="*.gguf" \
    "$TITAN_SRC/core/"       "$INCLUDES_DIR/opt/titan/core/"
rsync -a --exclude="__pycache__" --exclude="*.pyc" --exclude="*.bat" \
    "$TITAN_SRC/apps/"       "$INCLUDES_DIR/opt/titan/apps/"
rsync -a --exclude="__pycache__" --exclude="*.pyc" \
    "$TITAN_SRC/profgen/"    "$INCLUDES_DIR/opt/titan/profgen/"
rsync -a "$TITAN_SRC/config/"    "$INCLUDES_DIR/opt/titan/config/"
rsync -a "$TITAN_SRC/lib/"       "$INCLUDES_DIR/opt/titan/lib/"       2>/dev/null || true
rsync -a "$TITAN_SRC/bin/"       "$INCLUDES_DIR/opt/titan/bin/"       2>/dev/null || true
rsync -a --exclude="__pycache__" --exclude="*.pyc" \
    "$TITAN_SRC/tools/"      "$INCLUDES_DIR/opt/titan/tools/"         2>/dev/null || true
rsync -a --exclude="__pycache__" --exclude="*.pyc" \
    "$TITAN_SRC/extensions/" "$INCLUDES_DIR/opt/titan/extensions/"    2>/dev/null || true
rsync -a --exclude="__pycache__" --exclude="*.pyc" \
    "$TITAN_SRC/patches/"    "$INCLUDES_DIR/opt/titan/patches/"       2>/dev/null || true
rsync -a --include="*.modelfile" --include="*.py" --include="*.sh" \
    --exclude="*" \
    "$TITAN_SRC/training/phase1/" "$INCLUDES_DIR/opt/titan/training/phase1/" 2>/dev/null || true
rsync -a --exclude="__pycache__" --exclude="*.pyc" --exclude="data/" \
    "$TITAN_SRC/training/phase2/" "$INCLUDES_DIR/opt/titan/training/phase2/" 2>/dev/null || true
rsync -a --exclude="__pycache__" --exclude="*.pyc" \
    "$TITAN_SRC/training/phase3/" "$INCLUDES_DIR/opt/titan/training/phase3/" 2>/dev/null || true
rsync -a "$TITAN_SRC/vpn/"       "$INCLUDES_DIR/opt/titan/vpn/"       2>/dev/null || true
rsync -a "$TITAN_SRC/assets/"    "$INCLUDES_DIR/opt/titan/assets/"    2>/dev/null || true
rsync -a "$TITAN_SRC/branding/"  "$INCLUDES_DIR/opt/titan/branding/"  2>/dev/null || true

rsync -a --exclude="__pycache__" --exclude="*.pyc" \
    "$TITAN_SRC/scripts/"    "$INCLUDES_DIR/opt/titan/scripts/"    2>/dev/null || true
rsync -a --exclude="__pycache__" --exclude="*.pyc" \
    "$TITAN_SRC/src/"        "$INCLUDES_DIR/opt/titan/src/"        2>/dev/null || true
rsync -a --exclude="__pycache__" --exclude="*.pyc" \
    "$TITAN_SRC/tests/"      "$INCLUDES_DIR/opt/titan/tests/"      2>/dev/null || true

# Ship top-level docs (plans, audits, manuals) into /opt/titan
rsync -a --include="*.md" --include="*.txt" --exclude="*" \
    "$TITAN_SRC/" "$INCLUDES_DIR/opt/titan/" 2>/dev/null || true

for f in build.sh smoke_test.py smoke_test_v2.py verify_all.py; do
    [ -f "$TITAN_SRC/$f" ] && cp "$TITAN_SRC/$f" "$INCLUDES_DIR/opt/titan/" || true
done

echo "  Core: $(ls $INCLUDES_DIR/opt/titan/core/*.py 2>/dev/null | wc -l) modules | Apps: $(ls $INCLUDES_DIR/opt/titan/apps/*.py 2>/dev/null | wc -l) files"

# ── Phase 3: /etc includes ────────────────────────────────────────────────────
echo "[3/8] Writing /etc includes..."
mkdir -p "$INCLUDES_DIR/etc/profile.d" "$INCLUDES_DIR/etc/sysctl.d"

cat > "$INCLUDES_DIR/etc/profile.d/titan.sh" << 'EOF'
#!/bin/bash
export PYTHONPATH="/opt/titan:/opt/titan/core:/opt/titan/apps:$PYTHONPATH"
export TITAN_ROOT="/opt/titan"
export TITAN_VERSION="9.1"
export HISTSIZE=0
export HISTFILESIZE=0
unset HISTFILE
EOF
chmod +x "$INCLUDES_DIR/etc/profile.d/titan.sh"

cat > "$INCLUDES_DIR/etc/os-release" << 'EOF'
PRETTY_NAME="Titan OS V9.1"
NAME="TitanOS"
VERSION_ID="9.1"
VERSION="9.1"
ID=titanos
ID_LIKE=debian
HOME_URL="https://titan-os.io"
EOF

printf "Titan OS V9.1 \\n \\l\n" > "$INCLUDES_DIR/etc/issue"
echo "titan" > "$INCLUDES_DIR/etc/hostname"

cat > "$INCLUDES_DIR/etc/sysctl.d/99-titan.conf" << 'EOF'
net.ipv6.conf.all.disable_ipv6 = 1
net.ipv6.conf.default.disable_ipv6 = 1
net.ipv6.conf.lo.disable_ipv6 = 1
net.ipv4.tcp_timestamps = 0
kernel.dmesg_restrict = 1
kernel.kptr_restrict = 2
EOF

# ── Phase 4: Write build hooks ────────────────────────────────────────────────
echo "[4/8] Writing V9.1 build hooks..."
HOOKS_DIR="$ISO_DIR/config/hooks/live"
mkdir -p "$HOOKS_DIR"

# 010 — Python deps
cat > "$HOOKS_DIR/010-titan-pip-deps.hook.chroot" << 'EOF'
#!/bin/bash
echo "I: [010] Installing Python deps..."
pip3 install --no-cache-dir --break-system-packages \
    flask aiohttp requests numpy scipy cryptography PyQt6 \
    python-dotenv psutil pyyaml langchain langchain-core \
    langchain-community duckduckgo-search sentence-transformers \
    curl_cffi openai onnxruntime lz4 zstandard 2>/dev/null || \
pip3 install --no-cache-dir \
    flask aiohttp requests numpy scipy cryptography PyQt6 \
    python-dotenv psutil pyyaml curl_cffi openai onnxruntime lz4 2>/dev/null || true
echo "I: [010] Python deps done"
EOF
chmod +x "$HOOKS_DIR/010-titan-pip-deps.hook.chroot"

# 020 — Ollama
cat > "$HOOKS_DIR/020-titan-ollama.hook.chroot" << 'EOF'
#!/bin/bash
echo "I: [020] Setting up Ollama..."
OLLAMA_VERSION="0.16.3"
if ! command -v ollama >/dev/null 2>&1; then
    for URL in \
        "https://github.com/ollama/ollama/releases/download/v${OLLAMA_VERSION}/ollama-linux-amd64" \
        "https://ollama.com/download/ollama-linux-amd64"; do
        if curl -fsSL --retry 3 --max-time 120 "$URL" -o /usr/local/bin/ollama 2>/dev/null; then
            chmod +x /usr/local/bin/ollama && break
        fi
    done
fi
useradd -r -s /bin/false -d /usr/share/ollama ollama 2>/dev/null || true
mkdir -p /usr/share/ollama/.ollama/models
chown -R ollama:ollama /usr/share/ollama 2>/dev/null || true
cat > /etc/systemd/system/ollama.service << 'SEOF'
[Unit]
Description=Ollama AI Service
After=network-online.target
[Service]
Type=exec
User=ollama
Group=ollama
Restart=always
RestartSec=3
Environment="OLLAMA_HOST=127.0.0.1:11434"
Environment="OLLAMA_MODELS=/usr/share/ollama/.ollama/models"
ExecStart=/usr/local/bin/ollama serve
[Install]
WantedBy=multi-user.target
SEOF
systemctl enable ollama.service 2>/dev/null || true
echo "I: [020] Ollama configured (models download on first boot)"
EOF
chmod +x "$HOOKS_DIR/020-titan-ollama.hook.chroot"

# 030 — Camoufox
cat > "$HOOKS_DIR/030-titan-camoufox.hook.chroot" << 'EOF'
#!/bin/bash
echo "I: [030] Setting up Camoufox..."
pip3 install --no-cache-dir --break-system-packages camoufox 2>/dev/null || true
python3 -c "import camoufox; camoufox.install()" 2>/dev/null || true
CF_DIR="/opt/camoufox"
mkdir -p "$CF_DIR"
if [ ! -f "$CF_DIR/camoufox" ]; then
    CF_URL="https://github.com/daijro/camoufox/releases/latest/download/camoufox-linux-x86_64.tar.gz"
    curl -fsSL --retry 3 --max-time 180 "$CF_URL" -o /tmp/cf.tar.gz 2>/dev/null && \
        tar -xzf /tmp/cf.tar.gz -C "$CF_DIR" --strip-components=1 2>/dev/null || \
        tar -xzf /tmp/cf.tar.gz -C "$CF_DIR" 2>/dev/null || true
    rm -f /tmp/cf.tar.gz
    chmod +x "$CF_DIR/camoufox" 2>/dev/null || true
fi
printf '#!/bin/bash\nexec /opt/camoufox/camoufox "$@"\n' > /usr/local/bin/camoufox
chmod +x /usr/local/bin/camoufox 2>/dev/null || true
echo "I: [030] Camoufox done"
EOF
chmod +x "$HOOKS_DIR/030-titan-camoufox.hook.chroot"

# 040 — Xray
cat > "$HOOKS_DIR/040-titan-xray.hook.chroot" << 'EOF'
#!/bin/bash
echo "I: [040] Setting up Xray-core..."
XRAY_DIR="/opt/xray"; mkdir -p "$XRAY_DIR"
if [ ! -f "$XRAY_DIR/xray" ]; then
    URL="https://github.com/XTLS/Xray-core/releases/download/v1.8.11/Xray-linux-64.zip"
    curl -fsSL --retry 3 --max-time 120 "$URL" -o /tmp/xray.zip 2>/dev/null && \
        unzip -o /tmp/xray.zip -d "$XRAY_DIR" 2>/dev/null || true
    rm -f /tmp/xray.zip
    chmod +x "$XRAY_DIR/xray" 2>/dev/null || true
    ln -sf "$XRAY_DIR/xray" /usr/local/bin/xray 2>/dev/null || true
fi
cat > /etc/systemd/system/xray.service << 'SEOF'
[Unit]
Description=Xray Service
After=network.target
[Service]
Type=simple
ExecStart=/opt/xray/xray run -config /opt/titan/vpn/xray_config.json
Restart=on-failure
[Install]
WantedBy=multi-user.target
SEOF
echo "I: [040] Xray done"
EOF
chmod +x "$HOOKS_DIR/040-titan-xray.hook.chroot"

# 050 — Redis
cat > "$HOOKS_DIR/050-titan-redis.hook.chroot" << 'EOF'
#!/bin/bash
echo "I: [050] Setting up Redis..."
apt-get install -y --no-install-recommends redis-server 2>/dev/null || true
cat > /etc/redis/redis.conf << 'REOF'
bind 127.0.0.1
port 6379
daemonize no
loglevel warning
maxmemory 256mb
maxmemory-policy allkeys-lru
save ""
REOF
systemctl enable redis-server 2>/dev/null || true
echo "I: [050] Redis done"
EOF
chmod +x "$HOOKS_DIR/050-titan-redis.hook.chroot"

# 070 — Services & desktop shortcuts
cat > "$HOOKS_DIR/070-titan-services.hook.chroot" << 'EOF'
#!/bin/bash
echo "I: [070] Configuring services and autostart..."
mkdir -p /etc/xdg/autostart /home/user/Desktop

cat > /etc/xdg/autostart/titan-launcher.desktop << 'DEOF'
[Desktop Entry]
Type=Application
Name=Titan OS Launcher
Exec=/usr/bin/python3 /opt/titan/apps/titan_launcher.py
Hidden=false
X-GNOME-Autostart-enabled=true
DEOF

cat > /home/user/Desktop/titan-launcher.desktop << 'DEOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=Titan OS V9.1
Exec=/usr/bin/python3 /opt/titan/apps/titan_launcher.py
Icon=/opt/titan/assets/titan_icon.png
Terminal=false
Categories=Application;
DEOF
chmod +x /home/user/Desktop/titan-launcher.desktop 2>/dev/null || true

cat > /home/user/Desktop/titan-preflight.desktop << 'DEOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=Titan Preflight Check
Exec=bash -c "python3 /opt/titan/core/titan_preflight.py 2>&1 | tee /tmp/preflight.log"
Icon=utilities-system-monitor
Terminal=true
Categories=Application;
DEOF
chmod +x /home/user/Desktop/titan-preflight.desktop 2>/dev/null || true
chown -R user:user /home/user/Desktop 2>/dev/null || true
chmod -R 755 /opt/titan 2>/dev/null || true
echo "I: [070] Services done"
EOF
chmod +x "$HOOKS_DIR/070-titan-services.hook.chroot"

# 080 — Compile C/eBPF
cat > "$HOOKS_DIR/080-titan-build-c.hook.chroot" << 'EOF'
#!/bin/bash
echo "I: [080] Compiling C/eBPF components..."
apt-get install -y --no-install-recommends \
    linux-headers-amd64 libbpf-dev libelf-dev clang llvm 2>/dev/null || true
TITAN_LIB="/opt/titan/lib"
for src in tcp_fingerprint xdp_loader network_shield_original; do
    [ -f "$TITAN_LIB/${src}.c" ] && \
        clang -O2 -target bpf -c "$TITAN_LIB/${src}.c" \
            -o "$TITAN_LIB/${src}.o" 2>/dev/null && \
        echo "I: [080] ${src}.o compiled" || \
        echo "W: [080] ${src}.c compile skipped"
done
[ -f "/opt/titan/core/Makefile" ] && \
    make -C /opt/titan/core 2>/dev/null && echo "I: [080] kernel module built" || true
echo "I: [080] C/eBPF done"
EOF
chmod +x "$HOOKS_DIR/080-titan-build-c.hook.chroot"

# 090 — Harden
cat > "$HOOKS_DIR/090-titan-harden.hook.chroot" << 'EOF'
#!/bin/bash
echo "I: [090] Hardening OS..."
echo "net.ipv6.conf.all.disable_ipv6 = 1" >> /etc/sysctl.conf
echo "net.ipv6.conf.default.disable_ipv6 = 1" >> /etc/sysctl.conf
echo "unset HISTFILE" >> /etc/profile
echo "export HISTSIZE=0" >> /etc/profile
rm -f /root/.bash_history /home/user/.bash_history 2>/dev/null || true
ln -sf /dev/null /root/.bash_history 2>/dev/null || true
echo "* hard core 0" >> /etc/security/limits.conf
find /opt/titan -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find /opt/titan -name "*.pyc" -delete 2>/dev/null || true
find /var/log -type f -exec truncate -s 0 {} \; 2>/dev/null || true
echo "I: [090] Hardening done"
EOF
chmod +x "$HOOKS_DIR/090-titan-harden.hook.chroot"

# 099 — Final verification
cat > "$HOOKS_DIR/099-titan-final.hook.chroot" << 'EOF'
#!/bin/bash
echo "I: [099] Final verification..."
CORE=$(ls /opt/titan/core/*.py 2>/dev/null | wc -l)
APPS=$(ls /opt/titan/apps/*.py 2>/dev/null | wc -l)
ERRS=0
for f in /opt/titan/core/*.py /opt/titan/apps/*.py; do
    python3 -m py_compile "$f" 2>/dev/null || ERRS=$((ERRS+1))
done
echo 'export PYTHONPATH="/opt/titan:/opt/titan/core:/opt/titan/apps"' >> /etc/bash.bashrc
cat > /opt/titan/VERSION << VEOF
TITAN_VERSION=9.1
BUILD_DATE=$(date +%Y-%m-%d)
CODENAME=TitanOS
CORE_MODULES=$CORE
APP_FILES=$APPS
SYNTAX_ERRORS=$ERRS
VEOF
echo "I: [099] Core=$CORE | Apps=$APPS | SyntaxErrors=$ERRS"
echo "I: [099] Titan OS V9.1 ISO finalized"
EOF
chmod +x "$HOOKS_DIR/099-titan-final.hook.chroot"

echo "  Hooks: $(ls $HOOKS_DIR/*.hook.chroot | wc -l) total"

# ── Phase 5: lb config ────────────────────────────────────────────────────────
echo "[5/8] Running lb config..."
cd "$ISO_DIR"
lb clean --purge 2>/dev/null || true

lb config noauto \
    --mode debian \
    --distribution bookworm \
    --parent-distribution bookworm \
    --parent-mirror-bootstrap http://deb.debian.org/debian \
    --parent-mirror-chroot http://deb.debian.org/debian \
    --parent-mirror-chroot-security http://security.debian.org/debian-security \
    --parent-mirror-binary http://deb.debian.org/debian \
    --parent-mirror-binary-security http://security.debian.org/debian-security \
    --mirror-bootstrap http://deb.debian.org/debian \
    --mirror-chroot http://deb.debian.org/debian \
    --mirror-chroot-security http://security.debian.org/debian-security \
    --mirror-binary http://deb.debian.org/debian \
    --mirror-binary-security http://security.debian.org/debian-security \
    --keyring-packages debian-archive-keyring \
    --archive-areas "main contrib non-free non-free-firmware" \
    --architectures amd64 \
    --binary-images iso-hybrid \
    --bootappend-live "boot=live components quiet splash toram persistence username=user locales=en_US.UTF-8 ipv6.disable=1 net.ifnames=0" \
    --debian-installer none \
    --security true \
    --backports false \
    --linux-flavours amd64 \
    --bootloader grub-efi \
    --system live \
    --initramfs live-boot \
    --initsystem systemd \
    --linux-packages "linux-image linux-headers" \
    --apt-indices false \
    --apt-recommends false \
    --iso-application "Titan OS V9.1" \
    --iso-publisher "Titan" \
    --iso-volume "TITAN-V91" \
    --firmware-chroot true \
    --cache true \
    --cache-packages true
echo "  lb config done"

# ── Phase 6: Add swap ─────────────────────────────────────────────────────────
echo "[6/8] Adding build swap (8GB)..."
SWAP_FILE="/swapfile_titan_build"
if [ ! -f "$SWAP_FILE" ]; then
    fallocate -l 8G "$SWAP_FILE" 2>/dev/null || \
        dd if=/dev/zero of="$SWAP_FILE" bs=1M count=8192 status=none
    chmod 600 "$SWAP_FILE"
    mkswap "$SWAP_FILE" -q
    swapon "$SWAP_FILE"
fi
echo "  Swap: $(free -h | awk '/^Swap:/{print $2}')"

# ── Phase 7: lb build ─────────────────────────────────────────────────────────
echo "[7/8] Running lb build (30-90 min)..."
echo "  Started: $(date)"
lb build 2>&1 | tee -a "$LOG"
BUILD_EXIT=${PIPESTATUS[0]}

# ── Phase 8: Report ───────────────────────────────────────────────────────────
BUILD_END=$(date +%s)
BUILD_START_TS=$(cat /tmp/titan_build_start 2>/dev/null || echo $BUILD_END)
ELAPSED=$(( (BUILD_END - BUILD_START_TS) / 60 ))

swapoff "$SWAP_FILE" 2>/dev/null || true
rm -f "$SWAP_FILE" 2>/dev/null || true

echo ""
echo "[8/8] Build finished (exit=$BUILD_EXIT, ${ELAPSED}min)"

if [ $BUILD_EXIT -eq 0 ]; then
    ISO_FILE=$(ls "$ISO_DIR"/*.iso 2>/dev/null | head -1)
    if [ -n "$ISO_FILE" ]; then
        ISO_SIZE=$(du -h "$ISO_FILE" | cut -f1)
        ISO_SHA=$(sha256sum "$ISO_FILE" | cut -d' ' -f1)
        echo "============================================================"
        echo "  TITAN OS V9.1 ISO BUILD SUCCESSFUL"
        echo "  File:   $ISO_FILE"
        echo "  Size:   $ISO_SIZE"
        echo "  SHA256: $ISO_SHA"
        echo "  Time:   ${ELAPSED} minutes"
        echo "  Download: scp -P 22 root@72.62.72.48:$ISO_FILE ."
        echo "============================================================"
        printf "ISO=%s\nSIZE=%s\nSHA256=%s\nMINUTES=%s\n" \
            "$ISO_FILE" "$ISO_SIZE" "$ISO_SHA" "$ELAPSED" > /tmp/titan_iso_info.txt
    fi
else
    echo "============================================================"
    echo "  BUILD FAILED — last 30 lines:"
    echo "============================================================"
    tail -30 "$LOG"
fi
