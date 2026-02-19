#!/bin/bash
# TITAN V7.0 SINGULARITY — Residential Exit Node Setup Script
# Run this on your residential device (Raspberry Pi, spare PC, phone via Termux)
#
# This creates the final hop of the Lucid VPN split-horizon topology:
#   TITAN ISO → VPS Relay (Xray VLESS+Reality) → [Tailscale mesh] → THIS DEVICE → Internet
#
# The target website sees traffic from your residential ISP IP address,
# making it indistinguishable from a real home user.
#
# Usage: bash setup-exit-node.sh
#
# Prerequisites:
#   - Device on a residential network (home broadband, not datacenter)
#   - Internet connectivity
#   - Tailscale account (free tier works)

set -e

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║    TITAN V7.0 — RESIDENTIAL EXIT NODE SETUP              ║"
echo "║    Tailscale Exit Node for Lucid VPN                     ║"
echo "╚═══════════════════════════════════════════════════════════╝"

# ═══════════════════════════════════════════════════════════════════
# STEP 1: Install Tailscale
# ═══════════════════════════════════════════════════════════════════
echo ""
echo "[1/4] Installing Tailscale..."

if ! command -v tailscale &> /dev/null; then
    curl -fsSL https://tailscale.com/install.sh | sh
else
    echo "  Tailscale already installed: $(tailscale version 2>/dev/null || echo 'unknown')"
fi

systemctl enable tailscaled
systemctl start tailscaled

echo "  ✓ Tailscale installed and running"

# ═══════════════════════════════════════════════════════════════════
# STEP 2: Enable IP Forwarding
# ═══════════════════════════════════════════════════════════════════
echo ""
echo "[2/4] Enabling IP forwarding..."

cat > /etc/sysctl.d/99-tailscale-exit.conf << 'SYSCTL'
# TITAN Lucid VPN — Residential Exit Node
# Required for Tailscale exit node functionality

# IPv4 forwarding (required)
net.ipv4.ip_forward = 1

# IPv6 forwarding (optional, enable if your ISP supports it)
net.ipv6.conf.all.forwarding = 1
SYSCTL

sysctl -p /etc/sysctl.d/99-tailscale-exit.conf > /dev/null 2>&1
echo "  ✓ IP forwarding: IPv4=on, IPv6=on"

# ═══════════════════════════════════════════════════════════════════
# STEP 3: Advertise as Exit Node
# ═══════════════════════════════════════════════════════════════════
echo ""
echo "[3/4] Advertising as Tailscale exit node..."

# Check if already authenticated
if tailscale status &>/dev/null; then
    echo "  Already authenticated to Tailscale network"
    tailscale up --advertise-exit-node --reset
else
    echo "  Please authenticate when prompted..."
    tailscale up --advertise-exit-node
fi

echo "  ✓ Exit node advertised"

# ═══════════════════════════════════════════════════════════════════
# STEP 4: Verify and Display Status
# ═══════════════════════════════════════════════════════════════════
echo ""
echo "[4/4] Verifying setup..."

# Get Tailscale IP
TS_IP=$(tailscale ip -4 2>/dev/null || echo "unknown")
PUBLIC_IP=$(curl -s4 --max-time 5 api.ipify.org 2>/dev/null || echo "unknown")
ISP=$(curl -s --max-time 5 "http://ip-api.com/json/${PUBLIC_IP}?fields=isp" 2>/dev/null | grep -o '"isp":"[^"]*"' | cut -d'"' -f4 || echo "unknown")

echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║    EXIT NODE SETUP COMPLETE                               ║"
echo "╠═══════════════════════════════════════════════════════════╣"
echo "║                                                           ║"
echo "║  Tailscale IP:  $TS_IP"
echo "║  Public IP:     $PUBLIC_IP"
echo "║  ISP:           $ISP"
echo "║                                                           ║"
echo "║  IMPORTANT — APPROVE THIS NODE IN TAILSCALE ADMIN:       ║"
echo "║                                                           ║"
echo "║  1. Go to: https://login.tailscale.com/admin/machines    ║"
echo "║  2. Find this device                                     ║"
echo "║  3. Click ⋮ → Edit route settings                        ║"
echo "║  4. Enable 'Use as exit node'                            ║"
echo "║                                                           ║"
echo "║  THEN on your VPS relay, run:                            ║"
echo "║    tailscale up --exit-node=$TS_IP                       ║"
echo "║                                                           ║"
echo "║  This routes VPS outbound traffic through this device.   ║"
echo "║  Target websites will see: $PUBLIC_IP ($ISP)"
echo "║                                                           ║"
echo "╚═══════════════════════════════════════════════════════════╝"

# Persistence: Ensure Tailscale starts on boot
systemctl enable tailscaled 2>/dev/null || true

echo ""
echo "  Exit node is running. Keep this device powered on and connected."
echo "  Tailscale will auto-reconnect after reboots."
