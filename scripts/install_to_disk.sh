#!/bin/bash
# ==============================================================================
# LUCID EMPIRE :: TITAN V7.0 SINGULARITY — VPS DISK INSTALLER
# ==============================================================================
# AUTHORITY: Dva.12
# PURPOSE:   Install TITAN V7.0 from live ISO to a persistent disk.
#            Works on VPS (Vultr, Hetzner, DO, Linode, Kamatera) or bare metal.
#
# Usage:
#   # From within the booted live ISO:
#   sudo bash /opt/titan/bin/install-to-disk /dev/vda
#
#   # Or from the repo after building the ISO:
#   sudo bash scripts/install_to_disk.sh /dev/vda
#
# What it does:
#   1. Partitions the target disk (GPT: EFI + root)
#   2. Extracts the live filesystem to the root partition
#   3. Installs GRUB bootloader (EFI + BIOS fallback)
#   4. Configures fstab, networking, hostname, SSH
#   5. Enables all TITAN V7.0 systemd services
#   6. Sets root password and creates 'user' account
#
# After install:
#   - Reboot removes the live media
#   - System boots directly into TITAN V7.0 with GUI
#   - All modules persist across reboots
#   - VNC/RDP available for headless VPS access
# ==============================================================================

set -eo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

log()  { echo -e "${GREEN}[INSTALL]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC}    $1"; }
err()  { echo -e "${RED}[ERROR]${NC}   $1" >&2; }
hdr()  {
    echo ""
    echo -e "${CYAN}${BOLD}══════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}${BOLD}  $1${NC}"
    echo -e "${CYAN}${BOLD}══════════════════════════════════════════════════════════════${NC}"
}

# ==============================================================================
hdr "TITAN V7.0 SINGULARITY — VPS DISK INSTALLER"
# ==============================================================================

if [ "$EUID" -ne 0 ]; then
    err "Must run as root: sudo bash $0 /dev/sdX"
    exit 1
fi

TARGET_DISK="${1:-}"
if [ -z "$TARGET_DISK" ]; then
    err "Usage: sudo bash $0 /dev/sdX"
    echo ""
    echo "Available disks:"
    lsblk -d -o NAME,SIZE,TYPE,MODEL | grep disk
    echo ""
    err "Example: sudo bash $0 /dev/vda"
    exit 1
fi

if [ ! -b "$TARGET_DISK" ]; then
    err "$TARGET_DISK is not a block device"
    exit 1
fi

DISK_SIZE=$(lsblk -b -d -o SIZE "$TARGET_DISK" | tail -1 | tr -d ' ')
DISK_SIZE_GB=$((DISK_SIZE / 1073741824))
log "Target: $TARGET_DISK (${DISK_SIZE_GB} GB)"

if [ "$DISK_SIZE_GB" -lt 8 ]; then
    err "Disk too small. Minimum 8 GB required (found ${DISK_SIZE_GB} GB)."
    exit 1
fi

# Safety check
echo ""
echo -e "${RED}${BOLD}WARNING: This will ERASE ALL DATA on $TARGET_DISK${NC}"
echo ""
lsblk "$TARGET_DISK"
echo ""
read -p "Type 'YES' to continue: " CONFIRM
if [ "$CONFIRM" != "YES" ]; then
    err "Aborted."
    exit 1
fi

# ==============================================================================
hdr "PHASE 1 — PARTITION DISK"
# ==============================================================================

# Install required tools
apt-get update -qq 2>/dev/null
apt-get install -y --no-install-recommends \
    parted dosfstools e2fsprogs grub-efi-amd64-bin grub-pc-bin \
    grub-common grub2-common dracut 2>/dev/null || true

log "Unmounting any existing partitions on $TARGET_DISK..."
umount "${TARGET_DISK}"* 2>/dev/null || true
swapoff "${TARGET_DISK}"* 2>/dev/null || true

log "Creating GPT partition table..."
parted -s "$TARGET_DISK" mklabel gpt

log "Creating EFI partition (512 MB)..."
parted -s "$TARGET_DISK" mkpart ESP fat32 1MiB 513MiB
parted -s "$TARGET_DISK" set 1 esp on
parted -s "$TARGET_DISK" set 1 boot on

log "Creating root partition (rest of disk)..."
parted -s "$TARGET_DISK" mkpart root ext4 513MiB 100%

# Detect partition names (handles /dev/vda1 vs /dev/sda1 vs /dev/nvme0n1p1)
sleep 2
partprobe "$TARGET_DISK" 2>/dev/null || true
sleep 1

if [ -b "${TARGET_DISK}p1" ]; then
    EFI_PART="${TARGET_DISK}p1"
    ROOT_PART="${TARGET_DISK}p2"
elif [ -b "${TARGET_DISK}1" ]; then
    EFI_PART="${TARGET_DISK}1"
    ROOT_PART="${TARGET_DISK}2"
else
    err "Cannot detect partitions. Check: lsblk $TARGET_DISK"
    exit 1
fi

log "Formatting EFI: $EFI_PART (FAT32)..."
mkfs.vfat -F 32 -n "TITAN-EFI" "$EFI_PART"

log "Formatting root: $ROOT_PART (ext4)..."
mkfs.ext4 -F -L "TITAN-ROOT" "$ROOT_PART"

log "Partitioning complete."

# ==============================================================================
hdr "PHASE 2 — EXTRACT FILESYSTEM"
# ==============================================================================

MOUNT_ROOT=$(mktemp -d)
mount "$ROOT_PART" "$MOUNT_ROOT"
mkdir -p "$MOUNT_ROOT/boot/efi"
mount "$EFI_PART" "$MOUNT_ROOT/boot/efi"

# Find squashfs — either from mounted ISO or live filesystem
SQUASHFS=""
for sq in /run/live/medium/live/filesystem.squashfs \
          /lib/live/mount/medium/live/filesystem.squashfs \
          /cdrom/live/filesystem.squashfs; do
    if [ -f "$sq" ]; then
        SQUASHFS="$sq"
        break
    fi
done

if [ -n "$SQUASHFS" ]; then
    log "Extracting squashfs: $SQUASHFS ..."
    unsquashfs -f -d "$MOUNT_ROOT" "$SQUASHFS"
else
    # Running from live system — copy the live filesystem
    log "No squashfs found — copying live filesystem..."
    for dir in bin boot etc home lib lib64 opt root run sbin srv tmp usr var; do
        if [ -d "/$dir" ]; then
            log "  Copying /$dir ..."
            cp -a "/$dir" "$MOUNT_ROOT/" 2>/dev/null || true
        fi
    done
    mkdir -p "$MOUNT_ROOT"/{dev,proc,sys,run,mnt,media}
fi

log "Filesystem extraction complete."
log "Disk usage: $(du -sh "$MOUNT_ROOT" 2>/dev/null | awk '{print $1}')"

# ==============================================================================
hdr "PHASE 3 — CONFIGURE SYSTEM"
# ==============================================================================

ROOT_UUID=$(blkid -s UUID -o value "$ROOT_PART")
EFI_UUID=$(blkid -s UUID -o value "$EFI_PART")

log "Root UUID: $ROOT_UUID"
log "EFI  UUID: $EFI_UUID"

# fstab
cat > "$MOUNT_ROOT/etc/fstab" << EOF
# TITAN V7.0 SINGULARITY — /etc/fstab
UUID=$ROOT_UUID  /          ext4  errors=remount-ro,noatime  0 1
UUID=$EFI_UUID   /boot/efi  vfat  umask=0077                0 1
tmpfs            /tmp       tmpfs defaults,noatime,size=2G   0 0
EOF
log "fstab written."

# hostname
echo "titan-singularity" > "$MOUNT_ROOT/etc/hostname"
cat > "$MOUNT_ROOT/etc/hosts" << EOF
127.0.0.1   localhost
127.0.1.1   titan-singularity
::1         localhost ip6-localhost ip6-loopback
EOF
log "Hostname: titan-singularity"

# Networking — auto DHCP on all interfaces
mkdir -p "$MOUNT_ROOT/etc/network"
cat > "$MOUNT_ROOT/etc/network/interfaces" << EOF
auto lo
iface lo inet loopback

# Primary interface — DHCP (works on all VPS providers)
auto eth0
iface eth0 inet dhcp

auto ens3
iface ens3 inet dhcp

auto enp0s3
iface enp0s3 inet dhcp
EOF
log "Network: DHCP on eth0/ens3/enp0s3"

# Enable SSH for VPS access
mkdir -p "$MOUNT_ROOT/etc/ssh"
if [ -f "$MOUNT_ROOT/etc/ssh/sshd_config" ]; then
    sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin yes/' "$MOUNT_ROOT/etc/ssh/sshd_config"
    sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication yes/' "$MOUNT_ROOT/etc/ssh/sshd_config"
fi
log "SSH: Root login enabled"

# Set root password
chroot "$MOUNT_ROOT" /bin/bash -c "echo 'root:titan' | chpasswd" 2>/dev/null || {
    warn "Could not set root password in chroot"
}
log "Root password: titan (CHANGE THIS AFTER FIRST LOGIN)"

# Create user account (same as live session)
chroot "$MOUNT_ROOT" /bin/bash -c "
    id user &>/dev/null || useradd -m -s /bin/bash -G sudo,audio,video,plugdev user
    echo 'user:titan' | chpasswd
" 2>/dev/null || {
    warn "Could not create user account"
}
log "User account: user / titan"

# ==============================================================================
hdr "PHASE 4 — INSTALL GRUB BOOTLOADER"
# ==============================================================================

# Bind mount system directories
mount --bind /dev "$MOUNT_ROOT/dev"
mount --bind /dev/pts "$MOUNT_ROOT/dev/pts"
mount --bind /proc "$MOUNT_ROOT/proc"
mount --bind /sys "$MOUNT_ROOT/sys"
mount --bind /run "$MOUNT_ROOT/run" 2>/dev/null || true

# Install GRUB in chroot
log "Installing GRUB bootloader..."
chroot "$MOUNT_ROOT" /bin/bash << 'CHROOTEOF'
set -e

# Ensure grub and dracut packages are installed
apt-get update -qq 2>/dev/null || true
apt-get install -y --no-install-recommends \
    grub-efi-amd64 grub-pc-bin grub-common \
    linux-image-amd64 linux-headers-amd64 \
    dracut openssh-server 2>/dev/null || true

# Regenerate initramfs with 99ramwipe module
echo "[*] Regenerating initramfs with dracut (embedding 99ramwipe)..."
dracut -f --add 99ramwipe 2>/dev/null || {
    echo "[WARN] Dracut failed — initramfs may not include RAM wipe"
}

# Install GRUB for EFI
grub-install --target=x86_64-efi --efi-directory=/boot/efi --removable --recheck 2>/dev/null || {
    echo "[WARN] EFI GRUB install had issues — trying BIOS fallback"
}

# Install GRUB for BIOS (MBR fallback for some VPS providers)
DISK_DEV=$(mount | grep ' / ' | awk '{print $1}' | sed 's/[0-9]*$//')
grub-install --target=i386-pc "$DISK_DEV" 2>/dev/null || {
    echo "[WARN] BIOS GRUB install skipped (EFI-only system)"
}

# Update GRUB config
update-grub 2>/dev/null || {
    echo "[WARN] update-grub failed — generating manually"
    grub-mkconfig -o /boot/grub/grub.cfg 2>/dev/null || true
}

# Sync Titan Hardening configs
echo "[*] Applying kernel and network hardening to persistent disk..."
mkdir -p /etc/sysctl.d
cp /opt/titan/config/99-titan-hardening.conf /etc/sysctl.d/ 2>/dev/null || \
cp /opt/titan-build/iso/config/includes.chroot/etc/sysctl.d/99-titan-hardening.conf /etc/sysctl.d/ 2>/dev/null || true

# Enable critical services
systemctl enable ssh 2>/dev/null || true
systemctl enable lucid-titan.service 2>/dev/null || true
systemctl enable lucid-ebpf.service 2>/dev/null || true
systemctl enable lucid-console.service 2>/dev/null || true
systemctl enable titan-first-boot.service 2>/dev/null || true
systemctl enable NetworkManager 2>/dev/null || systemctl enable networking 2>/dev/null || true

echo "[+] GRUB and services configured."
CHROOTEOF

log "GRUB installation complete."

# ==============================================================================
hdr "PHASE 5 — VPS-SPECIFIC OPTIMIZATIONS"
# ==============================================================================

# VNC server for headless VPS GUI access
log "Installing VNC server for remote GUI access..."
chroot "$MOUNT_ROOT" /bin/bash -c "
    apt-get install -y --no-install-recommends \
        tigervnc-standalone-server tigervnc-common \
        xfce4 xfce4-terminal dbus-x11 2>/dev/null || true
" 2>/dev/null || warn "VNC/XFCE install had issues (may need manual setup)"

# Create VNC startup for user
mkdir -p "$MOUNT_ROOT/home/user/.vnc"
cat > "$MOUNT_ROOT/home/user/.vnc/xstartup" << 'EOF'
#!/bin/bash
unset SESSION_MANAGER
unset DBUS_SESSION_BUS_ADDRESS
export DISPLAY=:1
export PYTHONPATH=/opt/titan/core:/opt/titan/apps

# Start desktop environment
exec startxfce4 &
EOF
chmod +x "$MOUNT_ROOT/home/user/.vnc/xstartup"

# VNC password (default: titan)
chroot "$MOUNT_ROOT" /bin/bash -c "
    printf 'titan\ntitan\nn\n' | su - user -c 'vncpasswd' 2>/dev/null || true
" 2>/dev/null || true

# Create VNC systemd service
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

chroot "$MOUNT_ROOT" /bin/bash -c "systemctl enable titan-vnc.service" 2>/dev/null || true
log "VNC server configured on :1 (port 5901)"
log "VNC password: titan"

# Sudoers for user
cat > "$MOUNT_ROOT/etc/sudoers.d/titan-user" << 'EOF'
# TITAN V7.0 — VPS user permissions
user ALL=(ALL) NOPASSWD: ALL
EOF
chmod 440 "$MOUNT_ROOT/etc/sudoers.d/titan-user"

# ==============================================================================
hdr "PHASE 6 — CLEANUP & UNMOUNT"
# ==============================================================================

log "Cleaning up..."

# Unmount bind mounts
umount "$MOUNT_ROOT/run" 2>/dev/null || true
umount "$MOUNT_ROOT/sys" 2>/dev/null || true
umount "$MOUNT_ROOT/proc" 2>/dev/null || true
umount "$MOUNT_ROOT/dev/pts" 2>/dev/null || true
umount "$MOUNT_ROOT/dev" 2>/dev/null || true
umount "$MOUNT_ROOT/boot/efi" 2>/dev/null || true
umount "$MOUNT_ROOT" 2>/dev/null || true

rmdir "$MOUNT_ROOT" 2>/dev/null || true

sync

# ==============================================================================
hdr "INSTALLATION COMPLETE — TITAN V7.0 SINGULARITY"
# ==============================================================================
echo ""
echo -e "  ${GREEN}${BOLD}Disk:${NC}       $TARGET_DISK"
echo -e "  ${GREEN}${BOLD}Root:${NC}       $ROOT_PART (ext4, UUID=$ROOT_UUID)"
echo -e "  ${GREEN}${BOLD}EFI:${NC}        $EFI_PART (FAT32)"
echo -e "  ${GREEN}${BOLD}Hostname:${NC}   titan-singularity"
echo ""
echo -e "  ${CYAN}Credentials:${NC}"
echo -e "    root / titan"
echo -e "    user / titan"
echo -e "    ${RED}${BOLD}⚠ CHANGE THESE IMMEDIATELY AFTER FIRST LOGIN${NC}"
echo ""
echo -e "  ${CYAN}Access after reboot:${NC}"
echo -e "    SSH:  ssh root@<VPS_IP>"
echo -e "    VNC:  <VPS_IP>:5901 (password: titan)"
echo ""
echo -e "  ${CYAN}Services enabled:${NC}"
echo -e "    lucid-titan.service    — Kernel shields + backend API"
echo -e "    lucid-console.service  — GUI auto-launch"
echo -e "    titan-first-boot.service — Browser + dependency check"
echo -e "    titan-vnc.service      — VNC server on :5901"
echo -e "    ssh                    — SSH access"
echo ""
echo -e "  ${CYAN}Next steps:${NC}"
echo -e "    1. Remove live media / reboot"
echo -e "    2. Connect via SSH or VNC"
echo -e "    3. Change passwords: passwd root && passwd user"
echo -e "    4. Run: python3 /opt/titan/apps/app_unified.py"
echo ""
