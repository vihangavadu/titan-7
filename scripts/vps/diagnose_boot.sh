#!/bin/bash
# Run in recovery mode - diagnose why SSH fails on normal boot
ROOT="/mnt/sdb1"

echo "=== CLOUD-INIT USER DATA ==="
cat ${ROOT}/var/lib/cloud/instance/user-data.txt 2>/dev/null || echo "no user-data"

echo ""
echo "=== CLOUD-INIT VENDOR DATA ==="
cat ${ROOT}/var/lib/cloud/instance/vendor-data.txt 2>/dev/null | head -80 || echo "no vendor-data"

echo ""
echo "=== CLOUD-INIT CFG.D FILES ==="
for f in ${ROOT}/etc/cloud/cloud.cfg.d/*.cfg; do
    echo "--- $(basename $f) ---"
    cat "$f" 2>/dev/null
    echo ""
done

echo ""
echo "=== CLOUD-INIT PER-BOOT SCRIPTS ==="
ls -la ${ROOT}/var/lib/cloud/scripts/per-boot/ 2>/dev/null || echo "none"

echo ""
echo "=== CLOUD-INIT PER-INSTANCE SCRIPTS ==="
ls -la ${ROOT}/var/lib/cloud/scripts/per-instance/ 2>/dev/null || echo "none"

echo ""
echo "=== JOURNAL FROM LAST NORMAL BOOT ==="
# Try to read the journal from the mounted filesystem
MACHINE_ID=$(cat ${ROOT}/etc/machine-id 2>/dev/null)
if [ -n "$MACHINE_ID" ]; then
    JOURNAL_DIR="${ROOT}/var/log/journal/${MACHINE_ID}"
    if [ -d "$JOURNAL_DIR" ]; then
        # Use journalctl to read from the mounted journal
        journalctl --directory="${JOURNAL_DIR}" -b -1 --no-pager -p err --lines=30 2>/dev/null || echo "cant read journal"
    else
        echo "no journal dir for machine $MACHINE_ID"
    fi
else
    echo "no machine-id"
fi

echo ""
echo "=== DMESG FROM LAST BOOT (if available) ==="
tail -50 ${ROOT}/var/log/kern.log 2>/dev/null | grep -i "error\|fail\|eth0\|network" | tail -20 || echo "no kern.log"

echo ""
echo "=== AUTH LOG (SSH attempts) ==="
tail -30 ${ROOT}/var/log/auth.log 2>/dev/null | grep -i "ssh\|sshd" | tail -10 || echo "no auth.log"

echo ""
echo "=== NETWORK CONFIG FILES ==="
echo "--- interfaces ---"
cat ${ROOT}/etc/network/interfaces 2>/dev/null || echo "none"
echo ""
echo "--- NetworkManager conf ---"
cat ${ROOT}/etc/NetworkManager/NetworkManager.conf 2>/dev/null | head -20 || echo "none"

echo ""
echo "=== FINAL MASKED/DISABLED CHECK ==="
echo "Masked services:"
find ${ROOT}/etc/systemd/system/ -maxdepth 1 -type l -lname '/dev/null' -exec basename {} \; 2>/dev/null | sort
echo ""
echo "Enabled in multi-user:"
ls ${ROOT}/etc/systemd/system/multi-user.target.wants/ 2>/dev/null | sort
