#!/bin/bash
# LUCID EMPIRE :: XDP DEPLOYMENT SCRIPT
# Bash script for deploying XDP programs

set -e

INTERFACE="${1:-eth0}"
XDP_PROGRAM="${2:-./xdp_outbound.o}"

echo "[XDP] Deploying XDP program to interface: $INTERFACE"
echo "[XDP] Program path: $XDP_PROGRAM"

if [ ! -f "$XDP_PROGRAM" ]; then
    echo "[ERROR] XDP program not found at $XDP_PROGRAM"
    exit 1
fi

echo "[XDP] Loading XDP program..."
ip link set dev "$INTERFACE" xdp obj "$XDP_PROGRAM" sec xdp

echo "[XDP] Verifying XDP program loaded..."
ip link show "$INTERFACE" | grep -q "xdp" && echo "[SUCCESS] XDP program loaded" || echo "[FAILED] XDP program not loaded"

exit 0
