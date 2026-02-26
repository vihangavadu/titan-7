#!/bin/bash
# Deep diagnosis: Why is port 22 blocked on normal boot?
# Run in recovery mode with VPS filesystem at /mnt/sdb1
ROOT="/mnt/sdb1"

echo "=== PORT 22 BLOCK DIAGNOSIS ==="

echo ""
echo "--- 1. IPTABLES SAVED RULES ---"
cat ${ROOT}/etc/iptables/rules.v4 2>/dev/null || echo "no iptables rules.v4"
cat ${ROOT}/etc/iptables/rules.v6 2>/dev/null || echo "no iptables rules.v6"
cat ${ROOT}/etc/iptables.up.rules 2>/dev/null || echo "no iptables.up.rules"

echo ""
echo "--- 2. IPTABLES-PERSISTENT / NETFILTER-PERSISTENT ---"
ls ${ROOT}/etc/systemd/system/multi-user.target.wants/ 2>/dev/null | grep -i 'iptables\|netfilter'
ls ${ROOT}/lib/systemd/system/netfilter-persistent.service 2>/dev/null
ls ${ROOT}/lib/systemd/system/iptables-persistent.service 2>/dev/null
dpkg --root=${ROOT} -l 2>/dev/null | grep -i 'iptables-persistent\|netfilter-persistent\|nftables' || chroot ${ROOT} dpkg -l 2>/dev/null | grep -i 'iptables-persistent\|netfilter-persistent\|nftables' | head -5

echo ""
echo "--- 3. FAIL2BAN ---"
ls ${ROOT}/etc/systemd/system/multi-user.target.wants/fail2ban* 2>/dev/null || echo "fail2ban not enabled"
cat ${ROOT}/etc/fail2ban/jail.local 2>/dev/null | head -20 || echo "no fail2ban jail.local"

echo ""
echo "--- 4. MONARX AGENT ---"
cat ${ROOT}/etc/systemd/system/monarx-agent.service 2>/dev/null || cat ${ROOT}/lib/systemd/system/monarx-agent.service 2>/dev/null || echo "no monarx service file"

echo ""
echo "--- 5. FILEBROWSER SERVICE ---"
cat ${ROOT}/etc/systemd/system/filebrowser.service 2>/dev/null || cat ${ROOT}/lib/systemd/system/filebrowser.service 2>/dev/null || echo "no filebrowser service"

echo ""
echo "--- 6. ANY FIREWALL-RELATED SCRIPTS ---"
grep -rl 'iptables\|nft \|nftables\|ufw' ${ROOT}/etc/init.d/ 2>/dev/null | head -5
grep -rl 'iptables\|nft \|nftables\|ufw' ${ROOT}/etc/network/if-up.d/ 2>/dev/null | head -5
grep -rl 'iptables\|nft \|nftables\|ufw' ${ROOT}/etc/network/if-pre-up.d/ 2>/dev/null | head -5

echo ""
echo "--- 7. CLOUD-INIT LOG (last boot) ---"
tail -100 ${ROOT}/var/log/cloud-init-output.log 2>/dev/null | grep -i 'error\|fail\|ssh\|firewall\|iptables\|nft\|ufw' | tail -20 || echo "no cloud-init-output.log"

echo ""
echo "--- 8. SSHD CONFIG (full check) ---"
grep -v '^#' ${ROOT}/etc/ssh/sshd_config 2>/dev/null | grep -v '^$' | head -30

echo ""
echo "--- 9. SSH SOCKET ACTIVATION ---"
ls ${ROOT}/lib/systemd/system/ssh.socket 2>/dev/null
cat ${ROOT}/lib/systemd/system/ssh.socket 2>/dev/null
ls ${ROOT}/etc/systemd/system/multi-user.target.wants/ssh.socket 2>/dev/null
ls ${ROOT}/etc/systemd/system/sockets.target.wants/ssh.socket 2>/dev/null

echo ""
echo "--- 10. UFW RULES (even though masked) ---"
cat ${ROOT}/etc/ufw/user.rules 2>/dev/null | head -30 || echo "no user.rules"
cat ${ROOT}/lib/ufw/user.rules 2>/dev/null | head -30 || echo "no lib user.rules"

echo ""
echo "--- 11. PROFTPD (could conflict with ports) ---"
cat ${ROOT}/etc/proftpd/proftpd.conf 2>/dev/null | grep -i 'port\|listen' | head -5

echo ""
echo "--- 12. SSH SOCKET vs SERVICE ---"
# Ubuntu 24.04 uses ssh.socket by default instead of ssh.service!
cat ${ROOT}/lib/systemd/system/ssh.service 2>/dev/null | head -10
echo "---"
cat ${ROOT}/lib/systemd/system/ssh.socket 2>/dev/null

echo ""
echo "--- 13. CHECK IF ssh.socket IS THE DEFAULT ---"
ls -la ${ROOT}/etc/systemd/system/sockets.target.wants/ 2>/dev/null

echo ""
echo "=== DIAGNOSIS COMPLETE ==="
