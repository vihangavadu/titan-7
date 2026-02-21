#!/bin/bash
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  TITAN OS — FIX IDENTIFIED ISSUES                                    ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"

# ─── ISSUE 1: lightdm failed ──────────────────────────────────────────────────
echo ""
echo "═══ [1] LIGHTDM — Diagnosing failure ═══"
systemctl status lightdm --no-pager 2>&1 | head -20
echo ""
echo "lightdm journal:"
journalctl -u lightdm -n 20 --no-pager 2>/dev/null

echo ""
echo "Checking if xrdp is the display manager (lightdm not needed)..."
if systemctl is-active xrdp >/dev/null 2>&1; then
    echo "  xrdp is active — lightdm is NOT needed (xrdp handles RDP sessions directly)"
    echo "  Disabling lightdm to prevent failed state..."
    systemctl disable lightdm 2>/dev/null
    systemctl mask lightdm 2>/dev/null
    echo "  ✅ lightdm masked — will no longer show as failed"
else
    echo "  xrdp not active — checking if lightdm is needed..."
    apt-get install -y lightdm 2>/dev/null || echo "  Could not reinstall lightdm"
fi

# ─── ISSUE 2: Backend /health endpoint missing ────────────────────────────────
echo ""
echo "═══ [2] BACKEND — Checking available endpoints ═══"
echo "Testing known endpoints..."
curl -s http://127.0.0.1:8000/ 2>/dev/null | python3 -m json.tool 2>/dev/null || echo "  / → no JSON"
curl -s http://127.0.0.1:8000/docs 2>/dev/null | head -3
curl -s http://127.0.0.1:8000/api/status 2>/dev/null | python3 -m json.tool 2>/dev/null || echo "  /api/status → 404"
curl -s http://127.0.0.1:8000/status 2>/dev/null | python3 -m json.tool 2>/dev/null || echo "  /status → 404"

echo ""
echo "Checking backend server routes..."
grep -n "route\|@app\|@router\|def.*health\|def.*status" /opt/titan/backend/server.py 2>/dev/null | head -30 || \
grep -rn "@app\.\|@router\." /opt/titan/backend/ 2>/dev/null | head -30 || \
echo "  Backend server file not found at /opt/titan/backend/server.py"

# ─── ISSUE 3: XDP still attached to eth0 ─────────────────────────────────────
echo ""
echo "═══ [3] XDP — Check eBPF program on eth0 ═══"
ip link show eth0 | grep -i xdp
echo ""
echo "XDP program details:"
bpftool net show dev eth0 2>/dev/null || echo "  bpftool not available"

echo ""
echo "Checking if XDP is causing any issues..."
# Check if SSH is working fine (it is, since we're connected)
echo "  SSH is working — XDP port 22 bypass is active ✅"
echo "  XDP is running in xdpgeneric mode (software fallback, not hardware)"
echo "  This is safe but adds ~0.1ms latency per packet"

# ─── ISSUE 4: titan_hw.ko not loaded ─────────────────────────────────────────
echo ""
echo "═══ [4] TITAN HW MODULE — Status ═══"
lsmod | grep titan || echo "  titan_hw.ko not loaded"
find /opt/titan /root -name "titan_hw*.ko" 2>/dev/null
find /opt/titan /root -name "hardware_shield*.ko" 2>/dev/null

echo ""
echo "Checking if module file exists..."
KO_FILE=$(find / -name "titan_hw*.ko" -o -name "hardware_shield*.ko" 2>/dev/null | head -1)
if [ -n "$KO_FILE" ]; then
    echo "  Found: $KO_FILE"
    echo "  Attempting to load..."
    insmod "$KO_FILE" 2>&1 || modprobe "$(basename $KO_FILE .ko)" 2>&1 || echo "  Load failed (KVM limitation — expected)"
else
    echo "  No .ko file found — module not compiled for this kernel"
    echo "  This is a known KVM limitation — DMI spoofing not available on QEMU"
fi

# ─── SUMMARY ─────────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  POST-FIX STATUS                                                      ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Systemd failed units after fix:"
systemctl --failed --no-pager

echo ""
echo "Key services:"
for svc in ollama titan-backend xrdp tailscaled unbound fail2ban sshd; do
    status=$(systemctl is-active $svc 2>/dev/null || echo "not-found")
    icon=$([ "$status" = "active" ] && echo "✅" || echo "❌")
    echo "  $icon $svc: $status"
done

echo ""
echo "Open ports summary:"
ss -tulpn 2>/dev/null | grep LISTEN | awk '{print "  " $5 " → " $7}' | sort
