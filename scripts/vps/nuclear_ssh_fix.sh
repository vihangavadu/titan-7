#!/bin/bash
# NUCLEAR SSH FIX - Forces SSH to work regardless of any firewall or service issues
# Run in recovery mode with VPS filesystem at /mnt/sdb1
ROOT="/mnt/sdb1"

echo "=== NUCLEAR SSH FIX ==="

# 1. Check sshd_config.d for broken configs
echo "--- 1. Checking sshd_config.d ---"
ls -la ${ROOT}/etc/ssh/sshd_config.d/ 2>/dev/null
for f in ${ROOT}/etc/ssh/sshd_config.d/*.conf; do
    echo "  File: $(basename $f)"
    cat "$f" 2>/dev/null
    echo ""
done

# 2. Check if iptables-nft is installed (can load rules behind the scenes)
echo "--- 2. iptables binary type ---"
file ${ROOT}/usr/sbin/iptables 2>/dev/null
ls -la ${ROOT}/usr/sbin/iptables 2>/dev/null
ls -la ${ROOT}/etc/alternatives/iptables 2>/dev/null

# 3. Check for any saved iptables rules
echo "--- 3. Saved iptables rules ---"
cat ${ROOT}/etc/iptables/rules.v4 2>/dev/null || echo "  none"
cat ${ROOT}/etc/iptables.rules 2>/dev/null || echo "  none"

# 4. NUCLEAR: Create rc.local that forces SSH open
echo "--- 4. Creating NUCLEAR rc.local ---"
cat > ${ROOT}/etc/rc.local << 'RCEOF'
#!/bin/bash
# TITAN NUCLEAR SSH FIX - Runs at boot, forces SSH to work
exec > /var/log/titan-nuclear-boot.log 2>&1
echo "[TITAN-NUCLEAR] Starting at $(date)"

# Flush ALL firewall rules
echo "[TITAN-NUCLEAR] Flushing all firewall rules..."
iptables -F 2>/dev/null
iptables -X 2>/dev/null
iptables -P INPUT ACCEPT 2>/dev/null
iptables -P OUTPUT ACCEPT 2>/dev/null
iptables -P FORWARD ACCEPT 2>/dev/null
ip6tables -F 2>/dev/null
ip6tables -X 2>/dev/null
ip6tables -P INPUT ACCEPT 2>/dev/null
ip6tables -P OUTPUT ACCEPT 2>/dev/null
ip6tables -P FORWARD ACCEPT 2>/dev/null
nft flush ruleset 2>/dev/null
echo "[TITAN-NUCLEAR] Firewall flushed, policy=ACCEPT on all chains"

# Force network interface up
echo "[TITAN-NUCLEAR] Ensuring network..."
ip addr add 72.62.72.48/24 dev eth0 2>/dev/null || true
ip link set eth0 up 2>/dev/null || true
ip route add default via 72.62.72.254 2>/dev/null || true

# Generate SSH host keys if missing
if [ ! -f /etc/ssh/ssh_host_ed25519_key ]; then
    echo "[TITAN-NUCLEAR] Generating SSH host keys..."
    ssh-keygen -A
fi

# Force start SSH
echo "[TITAN-NUCLEAR] Starting SSH..."
/usr/sbin/sshd -D &
echo "[TITAN-NUCLEAR] SSH started (PID: $!)"

echo "[TITAN-NUCLEAR] Complete at $(date)"
exit 0
RCEOF
chmod +x ${ROOT}/etc/rc.local
echo "  rc.local created"

# 5. Enable rc-local service
echo "--- 5. Enabling rc-local service ---"
cat > ${ROOT}/etc/systemd/system/rc-local.service << 'SVCEOF'
[Unit]
Description=TITAN Nuclear SSH Fix (/etc/rc.local)
After=network.target
ConditionFileIsExecutable=/etc/rc.local

[Service]
Type=forking
ExecStart=/etc/rc.local
TimeoutSec=30
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
SVCEOF
ln -sf /etc/systemd/system/rc-local.service ${ROOT}/etc/systemd/system/multi-user.target.wants/rc-local.service 2>/dev/null
echo "  rc-local.service enabled"

# 6. Also create a cron @reboot entry as backup
echo "--- 6. Creating cron backup ---"
mkdir -p ${ROOT}/var/spool/cron/crontabs
echo '@reboot sleep 10 && iptables -F && iptables -P INPUT ACCEPT && iptables -P OUTPUT ACCEPT && nft flush ruleset 2>/dev/null && /usr/sbin/sshd 2>/dev/null' > ${ROOT}/var/spool/cron/crontabs/root
chmod 600 ${ROOT}/var/spool/cron/crontabs/root
chown root:crontab ${ROOT}/var/spool/cron/crontabs/root 2>/dev/null || true
echo "  @reboot cron entry created"

# 7. Also add to /etc/network/if-up.d/ as another backup
echo "--- 7. Creating if-up.d hook ---"
mkdir -p ${ROOT}/etc/network/if-up.d
cat > ${ROOT}/etc/network/if-up.d/99-titan-ssh << 'IFEOF'
#!/bin/bash
# Ensure SSH works when network comes up
iptables -F 2>/dev/null
iptables -P INPUT ACCEPT 2>/dev/null  
iptables -P OUTPUT ACCEPT 2>/dev/null
nft flush ruleset 2>/dev/null
pgrep -x sshd > /dev/null || /usr/sbin/sshd 2>/dev/null
IFEOF
chmod +x ${ROOT}/etc/network/if-up.d/99-titan-ssh
echo "  if-up.d hook created"

echo ""
echo "=== NUCLEAR FIX APPLIED ==="
echo "SSH will now start via 3 independent mechanisms:"
echo "  1. rc.local (systemd rc-local.service)"
echo "  2. @reboot crontab entry"
echo "  3. if-up.d network hook"
echo "All firewall rules will be flushed at boot."
echo ""
echo "Stop recovery mode and test SSH."
