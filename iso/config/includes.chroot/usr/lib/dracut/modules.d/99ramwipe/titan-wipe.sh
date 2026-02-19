#!/bin/bash
# TITAN SECURE WIPE
echo "[!] INITIATING SECURE MEMORY WIPE..."
# Drop caches to ensure data is in free memory
echo 3 > /proc/sys/vm/drop_caches
# Fill RAM with zeros then urandom until OOM
mount -t tmpfs -o size=100% tmpfs /mnt
echo "  [1/2] Zeroing memory..."
dd if=/dev/zero of=/mnt/wipe bs=1M status=none || true
rm /mnt/wipe
echo "  [2/2] Scrambling memory..."
dd if=/dev/urandom of=/mnt/wipe bs=1M status=none || true
umount /mnt
echo "[+] MEMORY SANITIZED."
