#!/bin/bash
# TITAN Mullvad SSH-Safe Connect Script
# Ensures SSH stays alive when Mullvad VPN connects on a VPS
#
# Problem: Mullvad replaces default route → incoming SSH to VPS public IP dies
# Solution: Policy route forces traffic FROM VPS public IP through real gateway
#
# Usage: bash mullvad_ssh_safe.sh connect
#        bash mullvad_ssh_safe.sh disconnect
#        bash mullvad_ssh_safe.sh status

set -e

VPS_IP="72.62.72.48"
TABLE_ID=100
RULE_PRIO=10

get_gateway() {
    ip route show default | awk '/default/ {print $3; exit}'
}

get_interface() {
    ip route show default | awk '/default/ {print $5; exit}'
}

setup_ssh_route() {
    local GW=$(get_gateway)
    local IFACE=$(get_interface)
    
    if [ -z "$GW" ] || [ -z "$IFACE" ]; then
        echo "ERROR: Cannot determine gateway/interface"
        exit 1
    fi
    
    echo "[*] VPS IP: $VPS_IP"
    echo "[*] Gateway: $GW via $IFACE"
    
    # Add policy routes: traffic FROM VPS_IP uses table 100 (bypasses VPN)
    ip route flush table $TABLE_ID 2>/dev/null || true
    ip route add default via $GW dev $IFACE table $TABLE_ID
    
    # Rule: packets with source VPS_IP use our bypass table
    ip rule del from $VPS_IP table $TABLE_ID priority $RULE_PRIO 2>/dev/null || true
    ip rule add from $VPS_IP table $TABLE_ID priority $RULE_PRIO
    
    echo "[+] SSH bypass route installed (table $TABLE_ID, priority $RULE_PRIO)"
}

remove_ssh_route() {
    ip rule del from $VPS_IP table $TABLE_ID priority $RULE_PRIO 2>/dev/null || true
    ip route flush table $TABLE_ID 2>/dev/null || true
    echo "[+] SSH bypass route removed"
}

do_connect() {
    echo "=== TITAN Mullvad SSH-Safe Connect ==="
    
    # Step 1: Ensure Mullvad is disconnected first
    mullvad disconnect 2>/dev/null || true
    sleep 2
    
    # Step 2: Install SSH bypass route BEFORE connecting
    setup_ssh_route
    
    # Step 3: Configure Mullvad
    mullvad lan set allow
    mullvad auto-connect set off
    mullvad relay set location us nyc
    mullvad dns set default --block-ads --block-trackers
    
    # Step 4: Connect
    echo "[*] Connecting to Mullvad..."
    mullvad connect
    
    # Step 5: Wait for connection
    for i in $(seq 1 15); do
        STATUS=$(mullvad status 2>/dev/null | head -1)
        if echo "$STATUS" | grep -q "Connected"; then
            echo "[+] $STATUS"
            break
        fi
        sleep 1
    done
    
    # Step 6: Show new IP
    echo "[*] VPN Exit IP: $(curl -s --max-time 5 https://api.ipify.org 2>/dev/null || echo 'timeout')"
    echo "[*] VPS Real IP: $VPS_IP (SSH still works on this)"
    
    # Step 7: Verify SSH route is intact
    if ip rule show | grep -q "from $VPS_IP"; then
        echo "[+] SSH bypass route: ACTIVE"
    else
        echo "[!] WARNING: SSH bypass route missing! Re-installing..."
        setup_ssh_route
    fi
    
    echo "=== Done ==="
}

do_disconnect() {
    echo "=== Disconnecting Mullvad ==="
    mullvad disconnect
    remove_ssh_route
    echo "[+] Disconnected. VPS IP: $(curl -s --max-time 5 https://api.ipify.org 2>/dev/null)"
}

do_status() {
    echo "=== Mullvad Status ==="
    mullvad status
    echo ""
    echo "=== SSH Route ==="
    if ip rule show | grep -q "from $VPS_IP"; then
        echo "SSH bypass: ACTIVE"
        ip rule show | grep "from $VPS_IP"
    else
        echo "SSH bypass: NOT ACTIVE"
    fi
    echo ""
    echo "VPN IP: $(curl -s --max-time 5 https://api.ipify.org 2>/dev/null || echo 'timeout')"
}

case "${1:-status}" in
    connect)    do_connect ;;
    disconnect) do_disconnect ;;
    status)     do_status ;;
    *)          echo "Usage: $0 {connect|disconnect|status}" ;;
esac
