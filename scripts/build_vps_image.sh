#!/bin/bash
# ==============================================================================
# LUCID EMPIRE :: TITAN V7.0 SINGULARITY — VPS DISK IMAGE BUILDER
# ==============================================================================
# AUTHORITY: Dva.12
# PURPOSE:   Build a VPS-ready bootable disk image directly from source tree.
#            No live ISO needed — produces raw/qcow2 ready for VPS upload.
#
# Usage:
#   sudo bash scripts/build_vps_image.sh
#   sudo bash scripts/build_vps_image.sh --size 30G --format qcow2
#
# Output:
#   lucid-titan-v7.0-singularity.raw    (raw disk image)
#   lucid-titan-v7.0-singularity.qcow2  (compressed, for upload)
#   lucid-titan-v7.0-singularity.qcow2.sha256
#
# VPS Providers Tested:
#   Vultr (custom ISO / direct upload), Hetzner (rescue mode dd),
#   DigitalOcean (custom image), Linode (dd), Kamatera (custom ISO),
#   AWS (import-image), OVH (rescue mode dd)
#
# Requirements:
#   - Ubuntu 22.04+ or Debian 12+ build host (x86_64)
#   - Root privileges
#   - 20 GB+ free disk space
#   - Internet connection
# ==============================================================================

set -eo pipefail

# ── ANSI Colors ───────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

log()  { echo -e "${GREEN}[TITAN]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC}  $1"; }
err()  { echo -e "${RED}[ERROR]${NC} $1" >&2; }
hdr()  {
    echo ""
    echo -e "${CYAN}${BOLD}══════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}${BOLD}  $1${NC}"
    echo -e "${CYAN}${BOLD}══════════════════════════════════════════════════════════════${NC}"
}

# ── Parse Arguments ───────────────────────────────────────────────────────────
IMG_SIZE="20G"
OUTPUT_FORMAT="both"   # raw, qcow2, or both
ROOT_PASSWORD="titan"
USER_PASSWORD="titan"
VNC_ENABLED=true
SSH_ENABLED=true

while [[ $# -gt 0 ]]; do
    case $1 in
        --size)      IMG_SIZE="$2"; shift 2 ;;
        --format)    OUTPUT_FORMAT="$2"; shift 2 ;;
        --root-pass) ROOT_PASSWORD="$2"; shift 2 ;;
        --user-pass) USER_PASSWORD="$2"; shift 2 ;;
        --no-vnc)    VNC_ENABLED=false; shift ;;
        --no-ssh)    SSH_ENABLED=false; shift ;;
        *)           err "Unknown option: $1"; exit 1 ;;
    esac
done

# ── Resolve Paths ─────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$REPO_ROOT"

CHROOT_OVERLAY="$REPO_ROOT/iso/config/includes.chroot"
PKG_LIST="$REPO_ROOT/iso/config/package-lists/custom.list.chroot"
HOOKS_DIR="$REPO_ROOT/iso/config/hooks/live"

TITAN_VERSION="7.0.3"
IMG_NAME="lucid-titan-v${TITAN_VERSION}-singularity"
RAW_IMG="$REPO_ROOT/${IMG_NAME}.raw"
QCOW2_IMG="$REPO_ROOT/${IMG_NAME}.qcow2"

MOUNT_ROOT=""
LOOP_DEV=""

# ── Cleanup Trap ──────────────────────────────────────────────────────────────
cleanup() {
    log "Cleaning up..."
    [ -n "$MOUNT_ROOT" ] && {
        umount "$MOUNT_ROOT/run" 2>/dev/null || true
        umount "$MOUNT_ROOT/sys" 2>/dev/null || true
        umount "$MOUNT_ROOT/proc" 2>/dev/null || true
        umount "$MOUNT_ROOT/dev/pts" 2>/dev/null || true
        umount "$MOUNT_ROOT/dev" 2>/dev/null || true
        umount "$MOUNT_ROOT/boot/efi" 2>/dev/null || true
        umount "$MOUNT_ROOT" 2>/dev/null || true
        rmdir "$MOUNT_ROOT" 2>/dev/null || true
    }
    [ -n "$LOOP_DEV" ] && losetup -d "$LOOP_DEV" 2>/dev/null || true
}
trap cleanup EXIT

# ==============================================================================
hdr "TITAN V7.0 SINGULARITY — VPS IMAGE BUILDER"
# ==============================================================================

if [ "$EUID" -ne 0 ]; then
    err "This script must be run as root."
    echo "    Usage: sudo bash scripts/build_vps_image.sh"
    exit 1
fi

log "Repo root:    $REPO_ROOT"
log "Image size:   $IMG_SIZE"
log "Output:       $OUTPUT_FORMAT"
log "SSH:          $SSH_ENABLED"
log "VNC:          $VNC_ENABLED"

# Disk space check
AVAIL_GB=$(df --output=avail / | tail -1 | awk '{print int($1/1048576)}')
if [ "$AVAIL_GB" -lt 15 ]; then
    err "Need at least 15 GB free. Only ${AVAIL_GB} GB available."
    exit 1
fi

# ==============================================================================
hdr "PHASE 1 — INSTALL BUILD DEPENDENCIES"
# ==============================================================================

log "Installing build tools..."
apt-get update -qq
apt-get install -y --no-install-recommends \
    debootstrap \
    parted \
    dosfstools \
    e2fsprogs \
    grub-efi-amd64-bin \
    grub-pc-bin \
    grub-common \
    grub2-common \
    qemu-utils \
    squashfs-tools \
    gcc clang llvm make bc \
    libbpf-dev libelf-dev zlib1g-dev \
    dkms \
    python3 python3-pip \
    curl wget git \
    kpartx

log "Build dependencies installed."

# ==============================================================================
hdr "PHASE 2 — CREATE RAW DISK IMAGE"
# ==============================================================================

log "Creating ${IMG_SIZE} raw disk image..."
rm -f "$RAW_IMG"
truncate -s "$IMG_SIZE" "$RAW_IMG"

# Setup loop device
LOOP_DEV=$(losetup --show -fP "$RAW_IMG")
log "Loop device: $LOOP_DEV"

# Create GPT partition table
log "Partitioning (GPT: 512M EFI + rest root)..."
parted -s "$LOOP_DEV" mklabel gpt
parted -s "$LOOP_DEV" mkpart ESP fat32 1MiB 513MiB
parted -s "$LOOP_DEV" set 1 esp on
parted -s "$LOOP_DEV" set 1 boot on
parted -s "$LOOP_DEV" mkpart root ext4 513MiB 100%

# Re-read partition table
partprobe "$LOOP_DEV" 2>/dev/null || true
sleep 2

EFI_PART="${LOOP_DEV}p1"
ROOT_PART="${LOOP_DEV}p2"

# Verify partitions exist
if [ ! -b "$EFI_PART" ] || [ ! -b "$ROOT_PART" ]; then
    # Try kpartx
    kpartx -a "$LOOP_DEV" 2>/dev/null || true
    sleep 1
    LOOP_BASE=$(basename "$LOOP_DEV")
    EFI_PART="/dev/mapper/${LOOP_BASE}p1"
    ROOT_PART="/dev/mapper/${LOOP_BASE}p2"
fi

log "Formatting EFI: $EFI_PART..."
mkfs.vfat -F 32 -n "TITAN-EFI" "$EFI_PART"

log "Formatting root: $ROOT_PART..."
mkfs.ext4 -F -L "TITAN-ROOT" "$ROOT_PART"

# Mount
MOUNT_ROOT=$(mktemp -d)
mount "$ROOT_PART" "$MOUNT_ROOT"
mkdir -p "$MOUNT_ROOT/boot/efi"
mount "$EFI_PART" "$MOUNT_ROOT/boot/efi"

log "Disk image partitioned and mounted at $MOUNT_ROOT"

# ==============================================================================
hdr "PHASE 3 — DEBOOTSTRAP BASE SYSTEM"
# ==============================================================================

log "Running debootstrap (Debian 12 Bookworm amd64)..."
debootstrap \
    --arch=amd64 \
    --variant=minbase \
    --components=main,contrib,non-free,non-free-firmware \
    bookworm \
    "$MOUNT_ROOT" \
    http://deb.debian.org/debian

log "Base system installed."

# Configure apt sources
cat > "$MOUNT_ROOT/etc/apt/sources.list" << 'EOF'
deb http://deb.debian.org/debian bookworm main contrib non-free non-free-firmware
deb http://deb.debian.org/debian bookworm-updates main contrib non-free non-free-firmware
deb http://deb.debian.org/debian-security bookworm-security main contrib non-free non-free-firmware
EOF

# ==============================================================================
hdr "PHASE 4 — INSTALL PACKAGES"
# ==============================================================================

# Bind mount for chroot
mount --bind /dev "$MOUNT_ROOT/dev"
mount --bind /dev/pts "$MOUNT_ROOT/dev/pts"
mount --bind /proc "$MOUNT_ROOT/proc"
mount --bind /sys "$MOUNT_ROOT/sys"
mount --bind /run "$MOUNT_ROOT/run" 2>/dev/null || true

# Build package install list from custom.list.chroot (skip comments and blanks)
# Also exclude live-boot/live-config packages (not needed for VPS)
PKGS=""
if [ -f "$PKG_LIST" ]; then
    while IFS= read -r line; do
        line=$(echo "$line" | sed 's/#.*//' | tr -d '[:space:]')
        [ -z "$line" ] && continue
        # Skip live-boot packages — not needed for persistent disk
        case "$line" in
            live-boot|live-config|live-config-systemd) continue ;;
        esac
        PKGS="$PKGS $line"
    done < "$PKG_LIST"
fi

# Add VPS-specific packages not in the live list
VPS_PKGS="openssh-server cloud-guest-utils acpid qemu-guest-agent"
VPS_PKGS="$VPS_PKGS grub-efi-amd64 grub-pc-bin linux-image-amd64 linux-headers-amd64"
VPS_PKGS="$VPS_PKGS ifupdown net-tools"

if [ "$VNC_ENABLED" = true ]; then
    VPS_PKGS="$VPS_PKGS tigervnc-standalone-server tigervnc-common"
fi

log "Installing $(echo $PKGS $VPS_PKGS | wc -w) packages..."
chroot "$MOUNT_ROOT" /bin/bash -c "
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq
    apt-get install -y --no-install-recommends $PKGS $VPS_PKGS 2>&1 | tail -5
" || {
    warn "Some packages may have failed — continuing"
}

log "Package installation complete."

# ==============================================================================
hdr "PHASE 5 — DEPLOY TITAN SOURCE TREE"
# ==============================================================================

log "Copying /opt/titan overlay..."
if [ -d "$CHROOT_OVERLAY/opt/titan" ]; then
    cp -a "$CHROOT_OVERLAY/opt/titan" "$MOUNT_ROOT/opt/"
    log "  /opt/titan deployed"
fi

log "Copying /opt/lucid-empire overlay..."
if [ -d "$CHROOT_OVERLAY/opt/lucid-empire" ]; then
    cp -a "$CHROOT_OVERLAY/opt/lucid-empire" "$MOUNT_ROOT/opt/"
    log "  /opt/lucid-empire deployed"
fi

log "Copying /etc overlays..."
for etc_item in "$CHROOT_OVERLAY/etc/"*; do
    [ -e "$etc_item" ] || continue
    item_name=$(basename "$etc_item")
    cp -a "$etc_item" "$MOUNT_ROOT/etc/" 2>/dev/null || true
    log "  etc/$item_name"
done

log "Copying /usr overlays..."
if [ -d "$CHROOT_OVERLAY/usr" ]; then
    cp -a "$CHROOT_OVERLAY/usr/"* "$MOUNT_ROOT/usr/" 2>/dev/null || true
    log "  /usr overlay deployed"
fi

# Set permissions
find "$MOUNT_ROOT/opt/titan" -name "*.py" -exec chmod +x {} \; 2>/dev/null || true
find "$MOUNT_ROOT/opt/titan" -name "*.sh" -exec chmod +x {} \; 2>/dev/null || true
chmod +x "$MOUNT_ROOT/opt/titan/bin/"* 2>/dev/null || true
chmod +x "$MOUNT_ROOT/opt/titan/apps/"* 2>/dev/null || true
find "$MOUNT_ROOT/opt/lucid-empire" -name "*.py" -exec chmod +x {} \; 2>/dev/null || true
find "$MOUNT_ROOT/opt/lucid-empire" -name "*.sh" -exec chmod +x {} \; 2>/dev/null || true
chmod +x "$MOUNT_ROOT/opt/lucid-empire/bin/"* 2>/dev/null || true
chmod +x "$MOUNT_ROOT/opt/lucid-empire/launch-titan.sh" 2>/dev/null || true

log "Source tree deployed."

# ==============================================================================
hdr "PHASE 6 — RUN BUILD HOOKS"
# ==============================================================================

if [ -d "$HOOKS_DIR" ]; then
    for hook in $(ls "$HOOKS_DIR/"*.hook.chroot 2>/dev/null | sort); do
        HOOK_NAME=$(basename "$hook")
        log "Running hook: $HOOK_NAME"
        cp "$hook" "$MOUNT_ROOT/tmp/_hook.sh"
        chmod +x "$MOUNT_ROOT/tmp/_hook.sh"
        chroot "$MOUNT_ROOT" /bin/bash /tmp/_hook.sh 2>&1 | tail -5 || {
            warn "Hook $HOOK_NAME had issues — continuing"
        }
        rm -f "$MOUNT_ROOT/tmp/_hook.sh"
    done
fi

log "Build hooks complete."

# ==============================================================================
hdr "PHASE 7 — CONFIGURE SYSTEM FOR VPS"
# ==============================================================================

ROOT_UUID=$(blkid -s UUID -o value "$ROOT_PART")
EFI_UUID=$(blkid -s UUID -o value "$EFI_PART")

log "Root UUID: $ROOT_UUID"
log "EFI  UUID: $EFI_UUID"

# fstab
cat > "$MOUNT_ROOT/etc/fstab" << EOF
# TITAN V7.0 SINGULARITY — /etc/fstab (VPS Persistent Disk)
UUID=$ROOT_UUID  /          ext4  errors=remount-ro,noatime,discard  0 1
UUID=$EFI_UUID   /boot/efi  vfat  umask=0077                        0 1
tmpfs            /tmp       tmpfs defaults,noatime,size=2G           0 0
EOF

# hostname
echo "titan-singularity" > "$MOUNT_ROOT/etc/hostname"
cat > "$MOUNT_ROOT/etc/hosts" << EOF
127.0.0.1   localhost
127.0.1.1   titan-singularity
::1         localhost ip6-localhost ip6-loopback
EOF

# Networking — auto DHCP (works on all VPS providers)
mkdir -p "$MOUNT_ROOT/etc/network"
cat > "$MOUNT_ROOT/etc/network/interfaces" << EOF
auto lo
iface lo inet loopback

# Primary interface — DHCP (covers eth0, ens3, enp0s3, enp1s0)
allow-hotplug eth0
iface eth0 inet dhcp

allow-hotplug ens3
iface ens3 inet dhcp

allow-hotplug enp0s3
iface enp0s3 inet dhcp

allow-hotplug enp1s0
iface enp1s0 inet dhcp
EOF

# Locale
chroot "$MOUNT_ROOT" /bin/bash -c "
    echo 'en_US.UTF-8 UTF-8' > /etc/locale.gen
    locale-gen 2>/dev/null || true
    echo 'LANG=en_US.UTF-8' > /etc/default/locale
" 2>/dev/null || true

# Timezone (UTC — operator changes per-session via timezone_enforcer.py)
chroot "$MOUNT_ROOT" /bin/bash -c "ln -sf /usr/share/zoneinfo/UTC /etc/localtime" 2>/dev/null || true

# SSH configuration
if [ "$SSH_ENABLED" = true ]; then
    mkdir -p "$MOUNT_ROOT/etc/ssh"
    if [ -f "$MOUNT_ROOT/etc/ssh/sshd_config" ]; then
        sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin yes/' "$MOUNT_ROOT/etc/ssh/sshd_config"
        sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication yes/' "$MOUNT_ROOT/etc/ssh/sshd_config"
    fi
    log "SSH: Root login enabled (change password after first login!)"
fi

# User accounts
chroot "$MOUNT_ROOT" /bin/bash -c "echo 'root:${ROOT_PASSWORD}' | chpasswd" 2>/dev/null || true
chroot "$MOUNT_ROOT" /bin/bash -c "
    id user &>/dev/null || useradd -m -s /bin/bash -G sudo,audio,video,plugdev,netdev user
    echo 'user:${USER_PASSWORD}' | chpasswd
" 2>/dev/null || true

# Sudoers
cat > "$MOUNT_ROOT/etc/sudoers.d/titan-user" << 'EOF'
# TITAN V7.0 — VPS user permissions
user ALL=(ALL) NOPASSWD: ALL
EOF
chmod 440 "$MOUNT_ROOT/etc/sudoers.d/titan-user"

log "Users: root/${ROOT_PASSWORD}, user/${USER_PASSWORD}"

# VNC Server
if [ "$VNC_ENABLED" = true ]; then
    mkdir -p "$MOUNT_ROOT/home/user/.vnc"
    cat > "$MOUNT_ROOT/home/user/.vnc/xstartup" << 'EOF'
#!/bin/bash
unset SESSION_MANAGER
unset DBUS_SESSION_BUS_ADDRESS
export DISPLAY=:1
export PYTHONPATH=/opt/titan/core:/opt/titan/apps:/opt/lucid-empire:/opt/lucid-empire/backend
exec startxfce4 &
EOF
    chmod +x "$MOUNT_ROOT/home/user/.vnc/xstartup"
    chroot "$MOUNT_ROOT" /bin/bash -c "chown -R user:user /home/user/.vnc" 2>/dev/null || true

    # VNC password
    chroot "$MOUNT_ROOT" /bin/bash -c "
        printf '${USER_PASSWORD}\n${USER_PASSWORD}\nn\n' | su - user -c 'vncpasswd' 2>/dev/null || true
    " 2>/dev/null || true

    # VNC systemd service
    cat > "$MOUNT_ROOT/etc/systemd/system/titan-vnc.service" << 'EOF'
[Unit]
Description=TITAN V7.0 VNC Server (Display :1)
After=network.target

[Service]
Type=simple
User=user
Group=user
WorkingDirectory=/home/user
ExecStart=/usr/bin/vncserver :1 -geometry 1920x1080 -depth 24 -localhost no
ExecStop=/usr/bin/vncserver -kill :1
Restart=on-failure
RestartSec=5
Environment=HOME=/home/user

[Install]
WantedBy=multi-user.target
EOF
    log "VNC server configured on :1 (port 5901)"
fi

# Install pip dependencies
if [ -f "$MOUNT_ROOT/opt/lucid-empire/requirements.txt" ]; then
    log "Installing Python dependencies..."
    chroot "$MOUNT_ROOT" /bin/bash -c "
        pip3 install --break-system-packages -r /opt/lucid-empire/requirements.txt 2>&1 | tail -3
    " 2>/dev/null || warn "Some pip packages may have failed"
fi

log "VPS configuration complete."

# ==============================================================================
hdr "PHASE 8 — INSTALL GRUB & ENABLE SERVICES"
# ==============================================================================

log "Installing GRUB bootloader..."
chroot "$MOUNT_ROOT" /bin/bash << 'CHROOTEOF'
set -e

# Install GRUB for EFI
grub-install --target=x86_64-efi --efi-directory=/boot/efi --removable --recheck 2>/dev/null || {
    echo "[WARN] EFI GRUB install had issues"
}

# Update GRUB config
cat > /etc/default/grub << 'GRUBCFG'
GRUB_DEFAULT=0
GRUB_TIMEOUT=3
GRUB_DISTRIBUTOR="TITAN V7.0 SINGULARITY"
GRUB_CMDLINE_LINUX_DEFAULT="quiet ipv6.disable=1 net.ifnames=0"
GRUB_CMDLINE_LINUX=""
GRUB_TERMINAL="console serial"
GRUB_SERIAL_COMMAND="serial --speed=115200 --unit=0 --word=8 --parity=no --stop=1"
GRUBCFG

update-grub 2>/dev/null || grub-mkconfig -o /boot/grub/grub.cfg 2>/dev/null || true

# Enable services
systemctl enable ssh 2>/dev/null || true
systemctl enable networking 2>/dev/null || true
systemctl enable nftables 2>/dev/null || true
systemctl enable unbound 2>/dev/null || true
systemctl enable lucid-titan.service 2>/dev/null || true
systemctl enable lucid-ebpf.service 2>/dev/null || true
systemctl enable lucid-console.service 2>/dev/null || true
systemctl enable titan-first-boot.service 2>/dev/null || true
systemctl enable titan-dns.service 2>/dev/null || true
systemctl enable titan-vnc.service 2>/dev/null || true
systemctl enable qemu-guest-agent 2>/dev/null || true

echo "[+] GRUB and services configured."
CHROOTEOF

log "GRUB and services installed."

# ==============================================================================
hdr "PHASE 9 — CLEANUP & CONVERT"
# ==============================================================================

log "Cleaning build artifacts..."
chroot "$MOUNT_ROOT" /bin/bash -c "
    apt-get clean
    rm -rf /var/cache/apt/archives/*.deb
    rm -rf /tmp/*
    rm -rf /var/tmp/*
    find / -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
    find / -name '*.pyc' -delete 2>/dev/null || true
" 2>/dev/null || true

# Unmount everything
log "Unmounting..."
umount "$MOUNT_ROOT/run" 2>/dev/null || true
umount "$MOUNT_ROOT/sys" 2>/dev/null || true
umount "$MOUNT_ROOT/proc" 2>/dev/null || true
umount "$MOUNT_ROOT/dev/pts" 2>/dev/null || true
umount "$MOUNT_ROOT/dev" 2>/dev/null || true
umount "$MOUNT_ROOT/boot/efi" 2>/dev/null || true
umount "$MOUNT_ROOT" 2>/dev/null || true
MOUNT_ROOT=""

sync

# Detach loop
losetup -d "$LOOP_DEV" 2>/dev/null || true
LOOP_DEV=""

log "Raw image ready: $RAW_IMG"
RAW_SIZE=$(ls -lh "$RAW_IMG" | awk '{print $5}')

# Convert to qcow2
if [ "$OUTPUT_FORMAT" = "qcow2" ] || [ "$OUTPUT_FORMAT" = "both" ]; then
    log "Converting to qcow2 (compressed)..."
    qemu-img convert -c -f raw -O qcow2 "$RAW_IMG" "$QCOW2_IMG"
    QCOW2_SIZE=$(ls -lh "$QCOW2_IMG" | awk '{print $5}')
    sha256sum "$QCOW2_IMG" > "${QCOW2_IMG}.sha256"
    log "qcow2 ready: $QCOW2_IMG ($QCOW2_SIZE)"
fi

# Remove raw if only qcow2 requested
if [ "$OUTPUT_FORMAT" = "qcow2" ]; then
    rm -f "$RAW_IMG"
fi

# Generate SHA256 for raw
if [ -f "$RAW_IMG" ]; then
    sha256sum "$RAW_IMG" > "${RAW_IMG}.sha256"
fi

# ==============================================================================
hdr "BUILD COMPLETE — TITAN V7.0 SINGULARITY (VPS IMAGE)"
# ==============================================================================
echo ""
if [ -f "$RAW_IMG" ]; then
    echo -e "  ${GREEN}${BOLD}RAW:${NC}      $RAW_IMG ($RAW_SIZE)"
fi
if [ -f "$QCOW2_IMG" ]; then
    echo -e "  ${GREEN}${BOLD}QCOW2:${NC}    $QCOW2_IMG ($QCOW2_SIZE)"
    echo -e "  ${GREEN}${BOLD}SHA256:${NC}    $(cat "${QCOW2_IMG}.sha256" | awk '{print $1}')"
fi
echo ""
echo -e "  ${CYAN}${BOLD}Deploy to VPS:${NC}"
echo ""
echo -e "  ${CYAN}Option A: Direct dd (Hetzner/OVH rescue mode):${NC}"
echo -e "    scp ${IMG_NAME}.raw root@VPS_IP:/tmp/"
echo -e "    ssh root@VPS_IP 'dd if=/tmp/${IMG_NAME}.raw of=/dev/sda bs=4M status=progress'"
echo ""
echo -e "  ${CYAN}Option B: Custom Image Upload (DigitalOcean/Vultr):${NC}"
echo -e "    Upload ${IMG_NAME}.qcow2 via provider dashboard → Create droplet from image"
echo ""
echo -e "  ${CYAN}Option C: QEMU test locally:${NC}"
echo -e "    qemu-system-x86_64 -m 4096 -enable-kvm -drive file=${IMG_NAME}.qcow2,format=qcow2 -net nic -net user,hostfwd=tcp::2222-:22,hostfwd=tcp::5901-:5901"
echo ""
echo -e "  ${CYAN}After boot:${NC}"
echo -e "    SSH:  ssh root@<VPS_IP>         (password: ${ROOT_PASSWORD})"
echo -e "    VNC:  <VPS_IP>:5901             (password: ${USER_PASSWORD})"
echo -e "    GUI:  Via VNC → app_unified.py auto-launches on desktop"
echo ""
echo -e "  ${RED}${BOLD}⚠ CHANGE PASSWORDS IMMEDIATELY AFTER FIRST LOGIN:${NC}"
echo -e "    passwd root && passwd user"
echo -e "    vncpasswd (as user)"
echo ""
