#!/bin/bash
# TITAN VPS Deep Audit — Cross-reference docs claims vs actual deployment

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  TITAN V7.5 VPS DEEP AUDIT — DOCS vs REALITY                        ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo "Date: $(date)"
echo "Host: $(hostname)"
echo ""

# ─────────────────────────────────────────────────────────────────────────────
echo "═══════════════════════════════════════════════════════════════════════"
echo "SECTION 1: RING 0 — KERNEL HARDWARE SHIELD"
echo "═══════════════════════════════════════════════════════════════════════"

echo "[1.1] Kernel module files:"
ls -lh /opt/titan/core/hardware_shield_v6.c 2>/dev/null && echo "  ✅ hardware_shield_v6.c EXISTS" || echo "  ❌ hardware_shield_v6.c MISSING"
ls -lh /opt/titan/kernel-modules/ 2>/dev/null || echo "  ❌ kernel-modules/ dir missing"
ls /opt/titan/kernel-modules/ 2>/dev/null

echo ""
echo "[1.2] Kernel module loaded:"
lsmod | grep titan 2>/dev/null && echo "  ✅ titan module loaded" || echo "  ⚠️  titan module NOT loaded (known KVM limitation)"

echo ""
echo "[1.3] DMI/SMBIOS values (should be spoofed):"
cat /sys/class/dmi/id/sys_vendor 2>/dev/null && echo "" || echo "  N/A"
cat /sys/class/dmi/id/product_name 2>/dev/null && echo "" || echo "  N/A"
cat /sys/class/dmi/id/board_vendor 2>/dev/null && echo "" || echo "  N/A"

echo ""
echo "[1.4] /proc/cpuinfo model:"
grep "model name" /proc/cpuinfo | head -1

echo ""
echo "[1.5] USB peripheral synth:"
ls -lh /opt/titan/core/usb_peripheral_synth.py 2>/dev/null && echo "  ✅ usb_peripheral_synth.py EXISTS" || echo "  ❌ MISSING"
lsusb 2>/dev/null | head -10

echo ""
echo "[1.6] titan-hw-shield service:"
systemctl is-active titan-hw-shield 2>/dev/null || echo "  inactive/not found"
systemctl is-enabled titan-hw-shield 2>/dev/null || echo "  not enabled"

# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════════════════"
echo "SECTION 2: RING 1 — NETWORK SHIELD / eBPF"
echo "═══════════════════════════════════════════════════════════════════════"

echo "[2.1] Network shield files:"
ls -lh /opt/titan/core/network_shield_loader.py 2>/dev/null && echo "  ✅ network_shield_loader.py" || echo "  ❌ MISSING"
ls -lh /opt/titan/core/network_shield.py 2>/dev/null && echo "  ✅ network_shield.py (symlink)" || echo "  ❌ MISSING"
ls -lh /opt/titan/core/tls_parrot.py 2>/dev/null && echo "  ✅ tls_parrot.py" || echo "  ❌ MISSING"
ls -lh /opt/titan/core/network_jitter.py 2>/dev/null && echo "  ✅ network_jitter.py" || echo "  ❌ MISSING"
ls -lh /opt/titan/core/quic_proxy.py 2>/dev/null && echo "  ✅ quic_proxy.py" || echo "  ❌ MISSING"

echo ""
echo "[2.2] eBPF/XDP programs:"
ls /opt/titan/core/*.c 2>/dev/null || echo "  No .c files in core/"
ls /opt/titan/kernel-modules/*.c 2>/dev/null | head -10

echo ""
echo "[2.3] Current TTL setting:"
sysctl net.ipv4.ip_default_ttl 2>/dev/null

echo ""
echo "[2.4] sysctl titan config:"
cat /etc/sysctl.d/99-titan.conf 2>/dev/null || echo "  ❌ /etc/sysctl.d/99-titan.conf NOT FOUND"

echo ""
echo "[2.5] DNS resolver:"
cat /etc/resolv.conf | head -5
chattr -l /etc/resolv.conf 2>/dev/null | grep -i immutable && echo "  ✅ resolv.conf is immutable" || echo "  ⚠️  resolv.conf NOT immutable"

echo ""
echo "[2.6] eBPF programs loaded:"
bpftool prog list 2>/dev/null | head -20 || echo "  bpftool not available or no programs"

# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════════════════"
echo "SECTION 3: RING 2 — OS HARDENING"
echo "═══════════════════════════════════════════════════════════════════════"

echo "[3.1] Font sanitizer:"
ls -lh /opt/titan/core/font_sanitizer.py 2>/dev/null && echo "  ✅ font_sanitizer.py" || echo "  ❌ MISSING"
cat /etc/fonts/local.conf 2>/dev/null | grep -c "rejectfont" && echo "  rejectfont rules found" || echo "  ⚠️  No fontconfig rejectfont rules"

echo ""
echo "[3.2] Audio hardener:"
ls -lh /opt/titan/core/audio_hardener.py 2>/dev/null && echo "  ✅ audio_hardener.py" || echo "  ❌ MISSING"

echo ""
echo "[3.3] Timezone enforcer:"
ls -lh /opt/titan/core/timezone_enforcer.py 2>/dev/null && echo "  ✅ timezone_enforcer.py" || echo "  ❌ MISSING"
timedatectl | grep "Time zone"

echo ""
echo "[3.4] Immutable OS / OverlayFS:"
ls -lh /opt/titan/core/immutable_os.py 2>/dev/null && echo "  ✅ immutable_os.py" || echo "  ❌ MISSING"
mount | grep overlay | head -5 || echo "  No OverlayFS mounts active"

# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════════════════"
echo "SECTION 4: RING 3 — TRINITY APPLICATIONS"
echo "═══════════════════════════════════════════════════════════════════════"

echo "[4.1] Trinity app files:"
for app in app_unified.py app_genesis.py app_cerberus.py app_kyc.py; do
    f="/opt/titan/apps/$app"
    if [ -f "$f" ]; then
        lines=$(wc -l < "$f")
        size=$(du -h "$f" | cut -f1)
        echo "  ✅ $app — $lines lines, $size"
    else
        echo "  ❌ $app MISSING"
    fi
done

echo ""
echo "[4.2] Core engine files:"
for mod in genesis_core.py cerberus_core.py cerberus_enhanced.py kyc_core.py kyc_enhanced.py ghost_motor_v6.py fingerprint_injector.py; do
    f="/opt/titan/core/$mod"
    if [ -f "$f" ]; then
        lines=$(wc -l < "$f")
        echo "  ✅ $mod — $lines lines"
    else
        echo "  ❌ $mod MISSING"
    fi
done

echo ""
echo "[4.3] Camoufox browser:"
find /opt/titan -name "camoufox*" -o -name "camoufox" 2>/dev/null | head -5
find /usr/local/bin -name "camoufox*" 2>/dev/null | head -5
find /opt -name "camoufox" -type f 2>/dev/null | head -5
which camoufox 2>/dev/null || echo "  camoufox not in PATH"

echo ""
echo "[4.4] Ghost Motor JS extension:"
find /opt/titan -name "ghost_motor*.js" 2>/dev/null | head -5
find /opt/titan -name "*.js" 2>/dev/null | head -10

# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════════════════"
echo "SECTION 5: RING 4 — PROFILE DATA LAYER"
echo "═══════════════════════════════════════════════════════════════════════"

echo "[5.1] Profile generator (profgen/):"
ls -la /opt/titan/profgen/ 2>/dev/null || echo "  ❌ /opt/titan/profgen/ MISSING"
ls /opt/titan/profgen/*.py 2>/dev/null | wc -l && echo "  profgen Python files" || echo "  0 profgen files"

echo ""
echo "[5.2] Profiles directory:"
ls -la /opt/titan/profiles/ 2>/dev/null | head -10 || echo "  ❌ /opt/titan/profiles/ MISSING"
du -sh /opt/titan/profiles/ 2>/dev/null || echo "  Empty or missing"

echo ""
echo "[5.3] Advanced profile generator:"
ls -lh /opt/titan/core/advanced_profile_generator.py 2>/dev/null && echo "  ✅ EXISTS" || echo "  ❌ MISSING"
ls -lh /opt/titan/core/forensic_synthesis_engine.py 2>/dev/null && echo "  ✅ forensic_synthesis_engine.py" || echo "  ❌ MISSING"
ls -lh /opt/titan/core/forensic_cleaner.py 2>/dev/null && echo "  ✅ forensic_cleaner.py" || echo "  ❌ MISSING"

echo ""
echo "[5.4] Purchase history engine:"
ls -lh /opt/titan/core/purchase_history_engine.py 2>/dev/null && echo "  ✅ EXISTS" || echo "  ❌ MISSING"

echo ""
echo "[5.5] Referrer warmup:"
ls -lh /opt/titan/core/referrer_warmup.py 2>/dev/null && echo "  ✅ EXISTS" || echo "  ❌ MISSING"

# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════════════════"
echo "SECTION 6: LUCID VPN / NETWORK"
echo "═══════════════════════════════════════════════════════════════════════"

echo "[6.1] Lucid VPN:"
ls -lh /opt/titan/core/lucid_vpn.py 2>/dev/null && echo "  ✅ lucid_vpn.py" || echo "  ❌ MISSING"
ls -lh /opt/titan/vpn/ 2>/dev/null && ls /opt/titan/vpn/ || echo "  ❌ vpn/ dir missing"

echo ""
echo "[6.2] WireGuard:"
which wg 2>/dev/null && echo "  ✅ WireGuard installed" || echo "  ❌ WireGuard NOT installed"
ls /etc/wireguard/ 2>/dev/null || echo "  No WireGuard configs"

echo ""
echo "[6.3] Proxy manager:"
ls -lh /opt/titan/core/proxy_manager.py 2>/dev/null && echo "  ✅ proxy_manager.py" || echo "  ❌ MISSING"

# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════════════════"
echo "SECTION 7: KILL SWITCH & FORENSICS"
echo "═══════════════════════════════════════════════════════════════════════"

echo "[7.1] Kill switch:"
ls -lh /opt/titan/core/kill_switch.py 2>/dev/null && echo "  ✅ kill_switch.py" || echo "  ❌ MISSING"

echo ""
echo "[7.2] Forensic cleaner:"
ls -lh /opt/titan/core/forensic_cleaner.py 2>/dev/null && echo "  ✅ forensic_cleaner.py" || echo "  ❌ MISSING"
ls -lh /opt/titan/core/forensic_synthesis_engine.py 2>/dev/null && echo "  ✅ forensic_synthesis_engine.py" || echo "  ❌ MISSING"

echo ""
echo "[7.3] Handover protocol:"
ls -lh /opt/titan/core/handover_protocol.py 2>/dev/null && echo "  ✅ handover_protocol.py" || echo "  ❌ MISSING"

# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════════════════"
echo "SECTION 8: BACKEND / SERVICES"
echo "═══════════════════════════════════════════════════════════════════════"

echo "[8.1] Lucid Empire backend:"
ls -la /opt/lucid-empire/ 2>/dev/null | head -10 || echo "  ❌ /opt/lucid-empire/ MISSING"

echo ""
echo "[8.2] Systemd services:"
systemctl list-units --type=service --state=active 2>/dev/null | grep -E "titan|lucid|camoufox|ollama" || echo "  No titan/lucid services active"
systemctl list-unit-files 2>/dev/null | grep -E "titan|lucid" | head -20

echo ""
echo "[8.3] Backend API port 8000:"
ss -tlnp | grep 8000 || echo "  ❌ Nothing listening on port 8000"

echo ""
echo "[8.4] Ollama service:"
systemctl is-active ollama && echo "  ✅ Ollama active" || echo "  ❌ Ollama inactive"
ollama list 2>/dev/null

# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════════════════"
echo "SECTION 9: COGNITIVE CORE / LLM"
echo "═══════════════════════════════════════════════════════════════════════"

echo "[9.1] Cognitive core:"
ls -lh /opt/titan/core/cognitive_core.py 2>/dev/null && echo "  ✅ cognitive_core.py" || echo "  ❌ MISSING"

echo ""
echo "[9.2] LLM bridge (new):"
ls -lh /opt/titan/core/ollama_bridge.py 2>/dev/null && echo "  ✅ ollama_bridge.py" || echo "  ❌ MISSING"
ls -lh /opt/titan/config/llm_config.json 2>/dev/null && echo "  ✅ llm_config.json" || echo "  ❌ MISSING"

echo ""
echo "[9.3] LLM routing test:"
cd /opt/titan && python3 - <<'PYEOF'
import sys
sys.path.insert(0, "core")
from ollama_bridge import resolve_provider_for_task, get_provider_status
status = get_provider_status()
available = [k for k,v in status.items() if v["available"]]
print(f"  Available providers: {available}")
r = resolve_provider_for_task("bin_generation")
print(f"  bin_generation -> {r[0]}/{r[1]}" if r else "  bin_generation -> NO PROVIDER")
PYEOF

# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════════════════"
echo "SECTION 10: RDP / DISPLAY / GUI"
echo "═══════════════════════════════════════════════════════════════════════"

echo "[10.1] XRDP:"
systemctl is-active xrdp 2>/dev/null || echo "  xrdp inactive/not installed"
which xrdp 2>/dev/null || echo "  xrdp not installed"

echo ""
echo "[10.2] Desktop environment:"
which startxfce4 2>/dev/null && echo "  ✅ XFCE installed" || echo "  ❌ XFCE not installed"
which Xvfb 2>/dev/null && echo "  ✅ Xvfb available" || echo "  ❌ Xvfb not available"

echo ""
echo "[10.3] PyQt6:"
python3 -c "import PyQt6; print('  ✅ PyQt6 version:', PyQt6.QtCore.PYQT_VERSION_STR)" 2>/dev/null || echo "  ❌ PyQt6 NOT installed"

# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════════════════"
echo "SECTION 11: COMPLETE FILE INVENTORY"
echo "═══════════════════════════════════════════════════════════════════════"

echo "[11.1] /opt/titan/ full tree:"
find /opt/titan -type f | sort | sed 's|/opt/titan/||' | head -100

echo ""
echo "[11.2] /opt/lucid-empire/ structure:"
find /opt/lucid-empire -type f 2>/dev/null | sort | sed 's|/opt/lucid-empire/||' | head -50 || echo "  ❌ /opt/lucid-empire/ not found"

echo ""
echo "[11.3] Systemd unit files for titan:"
find /etc/systemd /lib/systemd -name "*titan*" 2>/dev/null
find /etc/systemd /lib/systemd -name "*lucid*" 2>/dev/null

# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════════════════"
echo "SECTION 12: DOCS CLAIMS vs REALITY SUMMARY"
echo "═══════════════════════════════════════════════════════════════════════"

python3 - <<'PYEOF'
import os, subprocess

checks = {
    "hardware_shield_v6.c":      ("/opt/titan/core/hardware_shield_v6.c", "Ring 0 kernel module source"),
    "usb_peripheral_synth.py":   ("/opt/titan/core/usb_peripheral_synth.py", "USB device tree synthesis"),
    "network_shield_loader.py":  ("/opt/titan/core/network_shield_loader.py", "eBPF network shield"),
    "tls_parrot.py":             ("/opt/titan/core/tls_parrot.py", "JA3/JA4 TLS parroting"),
    "network_jitter.py":         ("/opt/titan/core/network_jitter.py", "Residential jitter injection"),
    "quic_proxy.py":             ("/opt/titan/core/quic_proxy.py", "QUIC/HTTP3 proxy"),
    "font_sanitizer.py":         ("/opt/titan/core/font_sanitizer.py", "Linux font blocking"),
    "audio_hardener.py":         ("/opt/titan/core/audio_hardener.py", "Windows audio spoofing"),
    "timezone_enforcer.py":      ("/opt/titan/core/timezone_enforcer.py", "Timezone enforcement"),
    "immutable_os.py":           ("/opt/titan/core/immutable_os.py", "OverlayFS immutability"),
    "ghost_motor_v6.py":         ("/opt/titan/core/ghost_motor_v6.py", "Behavioral biometrics DMTG"),
    "fingerprint_injector.py":   ("/opt/titan/core/fingerprint_injector.py", "Canvas/WebGL/Audio injection"),
    "webgl_angle.py":            ("/opt/titan/core/webgl_angle.py", "WebGL ANGLE shim"),
    "genesis_core.py":           ("/opt/titan/core/genesis_core.py", "Profile generation engine"),
    "cerberus_enhanced.py":      ("/opt/titan/core/cerberus_enhanced.py", "Transaction engine"),
    "kyc_enhanced.py":           ("/opt/titan/core/kyc_enhanced.py", "KYC identity mask"),
    "kill_switch.py":            ("/opt/titan/core/kill_switch.py", "Emergency kill switch"),
    "handover_protocol.py":      ("/opt/titan/core/handover_protocol.py", "Human handover protocol"),
    "lucid_vpn.py":              ("/opt/titan/core/lucid_vpn.py", "Lucid VPN VLESS+Reality"),
    "proxy_manager.py":          ("/opt/titan/core/proxy_manager.py", "Residential proxy manager"),
    "purchase_history_engine.py":("/opt/titan/core/purchase_history_engine.py", "Purchase history forging"),
    "referrer_warmup.py":        ("/opt/titan/core/referrer_warmup.py", "Referrer chain warmup"),
    "cognitive_core.py":         ("/opt/titan/core/cognitive_core.py", "AI cognitive engine"),
    "advanced_profile_generator.py":("/opt/titan/core/advanced_profile_generator.py", "400-600MB profile gen"),
    "forensic_synthesis_engine.py":("/opt/titan/core/forensic_synthesis_engine.py", "900-day history synthesis"),
    "forensic_cleaner.py":       ("/opt/titan/core/forensic_cleaner.py", "Forensic artifact cleanup"),
    "ollama_bridge.py":          ("/opt/titan/core/ollama_bridge.py", "Multi-provider LLM bridge"),
    "dynamic_data.py":           ("/opt/titan/core/dynamic_data.py", "LLM task routing"),
    "forensic_monitor.py":       ("/opt/titan/core/forensic_monitor.py", "24/7 forensic detection"),
    "app_unified.py":            ("/opt/titan/apps/app_unified.py", "Unified dashboard"),
    "app_genesis.py":            ("/opt/titan/apps/app_genesis.py", "Genesis GUI"),
    "app_cerberus.py":           ("/opt/titan/apps/app_cerberus.py", "Cerberus GUI"),
    "app_kyc.py":                ("/opt/titan/apps/app_kyc.py", "KYC GUI"),
    "llm_config.json":           ("/opt/titan/config/llm_config.json", "LLM provider config"),
    "lucid-empire backend":      ("/opt/lucid-empire", "Lucid Empire backend"),
    "profgen/":                  ("/opt/titan/profgen", "Profile generator scripts"),
}

present = []
missing = []

for name, (path, desc) in checks.items():
    if os.path.exists(path):
        present.append((name, desc))
    else:
        missing.append((name, desc))

print(f"\n  ✅ PRESENT ({len(present)}/{len(checks)}):")
for name, desc in present:
    print(f"     ✅ {name:40s} — {desc}")

print(f"\n  ❌ MISSING ({len(missing)}/{len(checks)}):")
for name, desc in missing:
    print(f"     ❌ {name:40s} — {desc}")

score = len(present) / len(checks) * 100
print(f"\n  DEPLOYMENT COMPLETENESS: {score:.1f}%")
PYEOF

echo ""
echo "═══════════════════════════════════════════════════════════════════════"
echo "AUDIT COMPLETE"
echo "═══════════════════════════════════════════════════════════════════════"
