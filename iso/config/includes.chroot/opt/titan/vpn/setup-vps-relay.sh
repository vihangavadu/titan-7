#!/bin/bash
# TITAN V7.0 SINGULARITY — VPS Relay Setup Script
# Run this on your VPS to configure the Xray relay server
#
# Usage: bash setup-vps-relay.sh
#
# Prerequisites:
#   - Fresh Linux VPS (Njalla, FlokiNET, BitHost, or Rootlayer)
#   - Root access
#   - Internet connectivity

set -e

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║    TITAN V7.0 — VPS RELAY SETUP                         ║"
echo "║    VLESS + Reality + TCP/IP Spoofing + Tailscale         ║"
echo "╚═══════════════════════════════════════════════════════════╝"

# ═══════════════════════════════════════════════════════════════════
# STEP 1: System Hardening
# ═══════════════════════════════════════════════════════════════════
echo ""
echo "[1/7] System hardening..."

apt-get update -qq
apt-get install -y -qq curl wget unzip jq nftables fail2ban unbound > /dev/null 2>&1

# Disable unnecessary services
systemctl disable --now postfix 2>/dev/null || true
systemctl disable --now exim4 2>/dev/null || true

# Enable nftables
systemctl enable nftables

echo "  ✓ System packages installed"

# ═══════════════════════════════════════════════════════════════════
# STEP 2: TCP/IP Stack Spoofing (Windows 11 mimesis)
# ═══════════════════════════════════════════════════════════════════
echo ""
echo "[2/7] Applying TCP/IP stack spoofing (Windows 11 profile)..."

cat > /etc/sysctl.d/99-titan-vpn.conf << 'SYSCTL'
# TITAN Lucid VPN — TCP/IP Stack Spoofing
# Target: Windows 10/11 residential desktop

# TTL: Linux=64, Windows=128
net.ipv4.ip_default_ttl = 128

# Timestamps: Linux=on, Windows=off
net.ipv4.tcp_timestamps = 0

# Window scaling (both use it)
net.ipv4.tcp_window_scaling = 1

# BBR congestion control (residential quality)
net.core.default_qdisc = fq
net.ipv4.tcp_congestion_control = bbr

# IP forwarding for VPN routing
net.ipv4.ip_forward = 1

# Disable ICMP redirects
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0
SYSCTL

sysctl --system > /dev/null 2>&1
echo "  ✓ TCP/IP: TTL=128, Timestamps=off, BBR=on, Forward=on"

# Nftables MSS clamping
cat > /etc/nftables.d/titan-vpn.nft << 'NFT'
table ip titan_vpn {
    chain forward {
        type filter hook forward priority 0; policy accept;
        tcp flags syn tcp option maxseg size set 1380
    }
    chain postrouting {
        type nat hook postrouting priority 100; policy accept;
        oifname != "lo" masquerade
    }
}
NFT

nft -f /etc/nftables.d/titan-vpn.nft 2>/dev/null || true
echo "  ✓ Nftables: MSS clamped to 1380, NAT masquerade active"

# ═══════════════════════════════════════════════════════════════════
# STEP 3: Install Xray-core
# ═══════════════════════════════════════════════════════════════════
echo ""
echo "[3/7] Installing Xray-core..."

if ! command -v xray &> /dev/null; then
    bash -c "$(curl -sL https://github.com/XTLS/Xray-install/raw/main/install-release.sh)" @ install
fi

# Generate keys
XRAY_KEYS=$(xray x25519)
PRIVATE_KEY=$(echo "$XRAY_KEYS" | grep "Private" | awk '{print $3}')
PUBLIC_KEY=$(echo "$XRAY_KEYS" | grep "Public" | awk '{print $3}')
UUID=$(xray uuid)
SHORT_ID=$(openssl rand -hex 4)

echo "  ✓ Xray installed"
echo ""
echo "  ╔═══════════════════════════════════════════════════════╗"
echo "  ║  SAVE THESE CREDENTIALS (needed on TITAN ISO)        ║"
echo "  ╠═══════════════════════════════════════════════════════╣"
echo "  ║  UUID:        $UUID"
echo "  ║  Public Key:  $PUBLIC_KEY"
echo "  ║  Short ID:    $SHORT_ID"
echo "  ║  VPS IP:      $(curl -s4 api.ipify.org)"
echo "  ║  VPS Port:    443"
echo "  ╚═══════════════════════════════════════════════════════╝"

# ═══════════════════════════════════════════════════════════════════
# STEP 4: Configure Xray Server (VLESS + Reality)
# ═══════════════════════════════════════════════════════════════════
echo ""
echo "[4/7] Configuring Xray server (VLESS + Reality)..."

cat > /usr/local/etc/xray/config.json << XRAY_CONFIG
{
    "log": {
        "loglevel": "warning"
    },
    "inbounds": [
        {
            "tag": "vless-reality",
            "port": 443,
            "protocol": "vless",
            "settings": {
                "clients": [
                    {
                        "id": "${UUID}",
                        "flow": "xtls-rprx-vision"
                    }
                ],
                "decryption": "none"
            },
            "streamSettings": {
                "network": "tcp",
                "security": "reality",
                "realitySettings": {
                    "show": false,
                    "dest": "learn.microsoft.com:443",
                    "serverNames": [
                        "learn.microsoft.com",
                        "www.microsoft.com"
                    ],
                    "privateKey": "${PRIVATE_KEY}",
                    "shortIds": ["${SHORT_ID}"]
                }
            }
        }
    ],
    "outbounds": [
        {
            "tag": "direct",
            "protocol": "freedom",
            "settings": {}
        },
        {
            "tag": "block",
            "protocol": "blackhole",
            "settings": {}
        }
    ],
    "routing": {
        "rules": [
            {
                "type": "field",
                "outboundTag": "block",
                "protocol": ["bittorrent"]
            }
        ]
    }
}
XRAY_CONFIG

systemctl enable xray
systemctl restart xray
echo "  ✓ Xray server running on port 443 (VLESS + Reality)"

# ═══════════════════════════════════════════════════════════════════
# STEP 5: Install Tailscale
# ═══════════════════════════════════════════════════════════════════
echo ""
echo "[5/7] Installing Tailscale..."

if ! command -v tailscale &> /dev/null; then
    curl -fsSL https://tailscale.com/install.sh | sh
fi

systemctl enable tailscaled
systemctl start tailscaled

echo "  ✓ Tailscale installed"
echo "  Run: tailscale up --advertise-routes=0.0.0.0/0"
echo "  Then on your residential exit device: tailscale up --advertise-exit-node"

# ═══════════════════════════════════════════════════════════════════
# STEP 6: Configure Unbound DNS
# ═══════════════════════════════════════════════════════════════════
echo ""
echo "[6/7] Configuring secure DNS (Unbound)..."

cat > /etc/unbound/unbound.conf.d/titan-dns.conf << 'DNS'
server:
    interface: 127.0.0.1
    port: 53
    do-not-query-localhost: no
    hide-identity: yes
    hide-version: yes
    qname-minimisation: yes
    
forward-zone:
    name: "."
    forward-addr: 9.9.9.9@853
    forward-addr: 1.1.1.1@853
    forward-tls-upstream: yes
DNS

systemctl enable unbound
systemctl restart unbound
echo "  ✓ Unbound DNS resolver active (DoT to Quad9 + Cloudflare)"

# ═══════════════════════════════════════════════════════════════════
# STEP 7: Firewall + Fail2Ban
# ═══════════════════════════════════════════════════════════════════
echo ""
echo "[7/7] Configuring firewall..."

# UFW or nftables rules
if command -v ufw &> /dev/null; then
    ufw default deny incoming
    ufw default allow outgoing
    ufw allow 443/tcp    # Xray (VLESS+Reality)
    ufw allow 22/tcp     # SSH (change to custom port later)
    ufw allow 41641/udp  # Tailscale
    ufw --force enable
    echo "  ✓ UFW firewall active"
fi

systemctl enable fail2ban
systemctl restart fail2ban
echo "  ✓ Fail2Ban active"

# ═══════════════════════════════════════════════════════════════════
# DONE
# ═══════════════════════════════════════════════════════════════════
echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║    VPS RELAY SETUP COMPLETE                              ║"
echo "╠═══════════════════════════════════════════════════════════╣"
echo "║                                                         ║"
echo "║  On your TITAN ISO, run: titan-vpn-setup                ║"
echo "║  Enter these values:                                    ║"
echo "║                                                         ║"
echo "║    VPS IP:      $(curl -s4 api.ipify.org)"
echo "║    UUID:        $UUID"
echo "║    Public Key:  $PUBLIC_KEY"
echo "║    Short ID:    $SHORT_ID"
echo "║    SNI:         learn.microsoft.com                     ║"
echo "║                                                         ║"
echo "║  NEXT: Set up residential exit device with Tailscale    ║"
echo "║    1. Install Tailscale on Raspberry Pi / phone / PC    ║"
echo "║    2. Run: tailscale up --advertise-exit-node           ║"
echo "║    3. Approve exit node in Tailscale admin console      ║"
echo "║    4. On this VPS: tailscale up --exit-node=<IP>        ║"
echo "║                                                         ║"
echo "╚═══════════════════════════════════════════════════════════╝"

# Save credentials to file
cat > /root/titan-vpn-credentials.txt << CREDS
TITAN Lucid VPN — Server Credentials
Generated: $(date)

VPS IP:      $(curl -s4 api.ipify.org)
VPS Port:    443
UUID:        $UUID
Public Key:  $PUBLIC_KEY
Private Key: $PRIVATE_KEY
Short ID:    $SHORT_ID
SNI Target:  learn.microsoft.com

KEEP THIS FILE SECURE. DELETE AFTER CONFIGURING TITAN ISO.
CREDS

chmod 600 /root/titan-vpn-credentials.txt
echo ""
echo "  Credentials saved to: /root/titan-vpn-credentials.txt"
echo "  DELETE this file after configuring your TITAN ISO!"
