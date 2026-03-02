#!/bin/bash
# TITAN X — OS Identity Branding
set -e

echo "[TITAN X] Applying OS identity branding..."

# 1. os-release
cat > /etc/os-release << 'OSEOF'
PRETTY_NAME="Titan X V10.0 Singularity"
NAME="Titan X"
VERSION_ID="10.0"
VERSION="10.0 (Singularity)"
VERSION_CODENAME=singularity
ID=titan-x
ID_LIKE=debian
HOME_URL="https://titan-x.local"
SUPPORT_URL="https://titan-x.local/support"
BUG_REPORT_URL="https://titan-x.local/bugs"
OSEOF
echo "  [+] /etc/os-release updated"

# 2. lsb-release
cat > /etc/lsb-release << 'LSBEOF'
DISTRIB_ID=TitanX
DISTRIB_RELEASE=10.0
DISTRIB_CODENAME=singularity
DISTRIB_DESCRIPTION="Titan X V10.0 Singularity"
LSBEOF
echo "  [+] /etc/lsb-release updated"

# 3. hostname
echo "titan-x" > /etc/hostname
hostnamectl set-hostname titan-x 2>/dev/null || true
echo "  [+] hostname set to titan-x"

# 4. MOTD
cat > /etc/motd << 'MOTDEOF'

  ████████╗██╗████████╗ █████╗ ███╗   ██╗    ██╗  ██╗
  ╚══██╔══╝██║╚══██╔══╝██╔══██╗████╗  ██║    ╚██╗██╔╝
     ██║   ██║   ██║   ███████║██╔██╗ ██║     ╚███╔╝
     ██║   ██║   ██║   ██╔══██║██║╚██╗██║     ██╔██╗
     ██║   ██║   ██║   ██║  ██║██║ ╚████║    ██╔╝ ██╗
     ╚═╝   ╚═╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═══╝    ╚═╝  ╚═╝

  V10.0 SINGULARITY  |  117 Modules  |  11 Apps  |  3 Bridges
  ───────────────────────────────────────────────────────────

MOTDEOF
echo "  [+] /etc/motd updated"

# 5. issue (pre-login banner)
cat > /etc/issue << 'ISSEOF'
  TITAN X V10.0 — Secure Terminal
  ─────────────────────────────────

ISSEOF
cp /etc/issue /etc/issue.net
echo "  [+] /etc/issue + /etc/issue.net updated"

# 6. Dynamic MOTD script
mkdir -p /etc/update-motd.d
cat > /etc/update-motd.d/10-titan-status << 'DYNEOF'
#!/bin/bash
CORE_COUNT=$(find /opt/titan/src/core -name "*.py" 2>/dev/null | wc -l)
SERVICES_UP=$(systemctl is-active genesis-appx-bridge cerberus-bridge kyc-bridge redis-server ollama xrdp nginx 2>/dev/null | grep -c "^active$")
echo ""
echo "  System: Titan X V10.0  |  Modules: ${CORE_COUNT}  |  Services: ${SERVICES_UP}/7 active"
echo ""
DYNEOF
chmod +x /etc/update-motd.d/10-titan-status
echo "  [+] Dynamic MOTD script installed"

echo "[DONE] OS identity branding applied."
