#!/bin/bash
# TITAN V8.1 SINGULARITY — Root Partition Installer
# WARNING: This script overwrites the root filesystem. Use with extreme caution.
set -e
echo "[TITAN V8.1] Starting installation to root partition..."
echo "[TITAN V8.1] Syncing TITAN system to root..."
rsync -aAX --delete \
  --exclude=/mnt \
  --exclude=/proc \
  --exclude=/sys \
  --exclude=/dev \
  --exclude=/run \
  --exclude=/tmp \
  --exclude=/home \
  /mnt/titan-root/ /

mkdir -p /proc /sys /dev /run /tmp /mnt
cp -f /mnt/titan-root/boot/vmlinuz-* /boot/
cp -f /mnt/titan-root/boot/initrd.img-* /boot/
update-grub
echo "[TITAN] Installation complete. Rebooting in 5 seconds..."
sleep 5
reboot
