#!/bin/bash
# TITAN OS V9.1 — Deep Detection Vector Audit
# Scans for every anomaly that modern antifraud/PSP systems can detect
set -e

echo "================================================================"
echo "  TITAN OS V9.1 — DEEP DETECTION VECTOR AUDIT"
echo "  $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "================================================================"

###############################################################################
# SECTION 1: OS-LEVEL ANOMALIES (Ring 0-2)
###############################################################################
echo ""
echo "=== SECTION 1: OS-LEVEL ANOMALIES ==="

echo ""
echo "--- 1.1 HYPERVISOR DETECTION ---"
# Forter, ThreatMetrix, Kount check these
echo -n "  systemd-detect-virt: "; systemd-detect-virt 2>/dev/null || echo "none"
echo -n "  /sys/class/dmi/id/product_name: "; cat /sys/class/dmi/id/product_name 2>/dev/null || echo "N/A"
echo -n "  /sys/class/dmi/id/sys_vendor: "; cat /sys/class/dmi/id/sys_vendor 2>/dev/null || echo "N/A"
echo -n "  /sys/class/dmi/id/bios_vendor: "; cat /sys/class/dmi/id/bios_vendor 2>/dev/null || echo "N/A"
echo -n "  /sys/class/dmi/id/board_vendor: "; cat /sys/class/dmi/id/board_vendor 2>/dev/null || echo "N/A"
echo -n "  /sys/class/dmi/id/chassis_vendor: "; cat /sys/class/dmi/id/chassis_vendor 2>/dev/null || echo "N/A"
echo -n "  CPUID hypervisor bit: "; grep -c hypervisor /proc/cpuinfo 2>/dev/null || echo "0"
echo -n "  /proc/scsi/scsi (QEMU/VBOX): "; grep -ci 'qemu\|vbox\|vmware\|xen' /proc/scsi/scsi 2>/dev/null || echo "0"
echo -n "  lspci (virtual devices): "; lspci 2>/dev/null | grep -ci 'virtio\|qemu\|vmware\|vbox\|xen' || echo "0"
echo -n "  MAC address prefix: "; ip link show | grep 'link/ether' | head -1 | awk '{print $2}' | cut -d: -f1-3
echo -n "  dmesg VM hints: "; dmesg 2>/dev/null | grep -ci 'hypervisor\|kvm\|qemu\|vmware\|virtualbox' || echo "0"

echo ""
echo "--- 1.2 TCP/IP STACK FINGERPRINT ---"
# Antifraud correlates OS from TCP/IP behavior
echo -n "  ip_default_ttl: "; sysctl -n net.ipv4.ip_default_ttl 2>/dev/null
echo -n "  tcp_window_scaling: "; sysctl -n net.ipv4.tcp_window_scaling 2>/dev/null
echo -n "  tcp_sack: "; sysctl -n net.ipv4.tcp_sack 2>/dev/null
echo -n "  tcp_timestamps: "; sysctl -n net.ipv4.tcp_timestamps 2>/dev/null
echo -n "  tcp_ecn: "; sysctl -n net.ipv4.tcp_ecn 2>/dev/null
echo -n "  tcp_fin_timeout: "; sysctl -n net.ipv4.tcp_fin_timeout 2>/dev/null
echo -n "  tcp_keepalive_time: "; sysctl -n net.ipv4.tcp_keepalive_time 2>/dev/null
echo -n "  tcp_max_syn_backlog: "; sysctl -n net.ipv4.tcp_max_syn_backlog 2>/dev/null
echo -n "  tcp_rmem default: "; sysctl -n net.ipv4.tcp_rmem 2>/dev/null | awk '{print $2}'
echo -n "  tcp_wmem default: "; sysctl -n net.ipv4.tcp_wmem 2>/dev/null | awk '{print $2}'
echo -n "  tcp_congestion_control: "; sysctl -n net.ipv4.tcp_congestion_control 2>/dev/null
echo "  EXPECTED Windows 11: TTL=128, timestamps=1, sack=1, window_scaling=1, ecn=0"

echo ""
echo "--- 1.3 TIMEZONE & LOCALE ---"
echo -n "  System TZ: "; timedatectl 2>/dev/null | grep 'Time zone' | awk '{print $3}'
echo -n "  Hardware clock: "; timedatectl 2>/dev/null | grep 'RTC in local TZ' | awk '{print $NF}'
echo -n "  NTP sync: "; timedatectl 2>/dev/null | grep 'synchronized' | awk '{print $NF}'
echo -n "  LANG: "; echo "${LANG:-not set}"
echo -n "  LC_ALL: "; echo "${LC_ALL:-not set}"

echo ""
echo "--- 1.4 KERNEL & PROCESS LEAKS ---"
echo -n "  Kernel version: "; uname -r
echo -n "  Kernel flavor: "; uname -v
echo "  RISK: Kernel string contains 'Debian' — detectable if JS reads navigator.oscpu"
echo -n "  /proc/version: "; head -c 120 /proc/version
echo ""
echo -n "  Uptime: "; uptime -p
echo -n "  Boot time: "; who -b 2>/dev/null | awk '{print $3, $4}'
echo -n "  Process count: "; ps aux | wc -l
echo -n "  Linux-specific procs: "; ps aux | grep -c 'systemd\|cron\|sshd\|dbus' || echo "0"

echo ""
echo "--- 1.5 NETWORK INTERFACES ---"
echo -n "  Interface count: "; ip link show | grep -c '^[0-9]'
ip link show | grep '^[0-9]' | while read line; do
    iface=$(echo "$line" | awk -F: '{print $2}' | tr -d ' ')
    mac=$(ip link show "$iface" 2>/dev/null | grep 'link/ether' | awk '{print $2}')
    if [ -n "$mac" ]; then
        prefix=$(echo "$mac" | cut -d: -f1-3 | tr '[:lower:]' '[:upper:]')
        # Known VM MAC prefixes
        case "$prefix" in
            52:54:00|08:00:27|00:0C:29|00:50:56|00:16:3E|00:1A:4A)
                echo "  RISK: $iface MAC=$mac (VM prefix $prefix)";;
            *)
                echo "  OK: $iface MAC=$mac (non-VM prefix)";;
        esac
    fi
done

echo ""
echo "--- 1.6 DISK & STORAGE FINGERPRINT ---"
echo -n "  Disk model: "; cat /sys/block/*/device/model 2>/dev/null | head -1 || echo "N/A"
echo -n "  Disk vendor: "; cat /sys/block/*/device/vendor 2>/dev/null | head -1 || echo "N/A"
echo -n "  /sys/block devices: "; ls /sys/block/ 2>/dev/null | tr '\n' ' '
echo ""
echo -n "  SCSI disk strings: "; lsblk -o NAME,MODEL 2>/dev/null | grep -v NAME || echo "none"

echo ""
echo "--- 1.7 GPU & DISPLAY ---"
echo -n "  GPU devices: "; lspci 2>/dev/null | grep -i 'vga\|display\|3d' || echo "none"
echo -n "  DISPLAY var: "; echo "${DISPLAY:-not set}"
echo -n "  Xorg running: "; pgrep -c Xorg 2>/dev/null || echo "0"

###############################################################################
# SECTION 2: BROWSER-LEVEL DETECTION VECTORS (Ring 3-4)
###############################################################################
echo ""
echo "=== SECTION 2: BROWSER-LEVEL DETECTION VECTORS ==="

echo ""
echo "--- 2.1 CAMOUFOX STATUS ---"
echo -n "  Camoufox binary: "; which camoufox 2>/dev/null || find /opt/titan -name 'camoufox' -type f 2>/dev/null | head -1 || echo "NOT FOUND"
echo -n "  Camoufox version: "; camoufox --version 2>/dev/null || echo "N/A"

echo ""
echo "--- 2.2 FINGERPRINT MODULE STATUS ---"
cd /opt/titan/core
python3 << 'PYEOF'
import sys
sys.path.insert(0, '.')

fp_modules = [
    ("fingerprint_injector", "FingerprintInjector", "Master fingerprint orchestrator"),
    ("canvas_noise", "CanvasNoiseEngine", "Canvas fingerprint randomization"),
    ("canvas_subpixel_shim", "CanvasSubPixelShim", "Subpixel rendering consistency"),
    ("webgl_angle", "WebGLAngleShim", "WebGL GPU spoofing"),
    ("font_sanitizer", "FontSanitizer", "Font enumeration control"),
    ("audio_hardener", "AudioHardener", "AudioContext fingerprint"),
    ("tls_parrot", "TLSParrotEngine", "TLS fingerprint mimicry"),
    ("tls_mimic", "TLSMimic", "TLS ClientHello spoofing"),
    ("ja4_permutation_engine", "JA4PermutationEngine", "JA4/JA3 hash control"),
    ("ghost_motor_v6", "get_forter_safe_params", "Behavioral mouse/keyboard"),
    ("biometric_mimicry", "BiometricMimicry", "BioCatch/BehavioSec defeat"),
    ("level9_antidetect", "Level9Antidetect", "Multi-layer antidetect"),
    ("timezone_enforcer", None, "TZ/locale matching"),
    ("location_spoofer", None, "Geo-IP consistency"),
    ("sensor_fingerprint", None, "Device sensor spoofing"),
    ("usb_peripheral_synth", None, "USB device emulation"),
    ("ntp_clock_sync", None, "NTP clock alignment"),
    ("client_hints_shim", None, "UA-CH header spoofing"),
    ("webrtc_leak_preventer", None, "WebRTC IP leak block"),
]

ok, warn = 0, 0
for mod_name, cls_name, desc in fp_modules:
    try:
        mod = __import__(mod_name)
        if cls_name and not hasattr(mod, cls_name):
            print(f"  WARN: {mod_name} loaded but {cls_name} missing — {desc}")
            warn += 1
        else:
            print(f"  OK: {mod_name} — {desc}")
            ok += 1
    except Exception as e:
        print(f"  FAIL: {mod_name} — {desc} — {str(e)[:60]}")
        warn += 1
print(f"\nFINGERPRINT MODULES: {ok} ok, {warn} warnings")
PYEOF

echo ""
echo "--- 2.3 TLS/JA3/JA4 FINGERPRINT CHECK ---"
python3 << 'PYEOF'
import sys
sys.path.insert(0, '/opt/titan/core')
try:
    from tls_parrot import TLSParrotEngine
    engine = TLSParrotEngine()
    profiles = engine.get_available_profiles() if hasattr(engine, 'get_available_profiles') else []
    print(f"  TLS Parrot profiles: {len(profiles)}")
    if profiles:
        for p in profiles[:5]:
            print(f"    - {p}")
except Exception as e:
    print(f"  TLS Parrot: {e}")

try:
    from ja4_permutation_engine import JA4PermutationEngine
    eng = JA4PermutationEngine()
    status = eng.get_status() if hasattr(eng, 'get_status') else "loaded"
    print(f"  JA4 Engine: {status}")
except Exception as e:
    print(f"  JA4 Engine: {e}")
PYEOF

###############################################################################
# SECTION 3: NETWORK DETECTION VECTORS
###############################################################################
echo ""
echo "=== SECTION 3: NETWORK DETECTION VECTORS ==="

echo ""
echo "--- 3.1 IP REPUTATION ---"
PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || curl -s icanhazip.com 2>/dev/null)
echo "  Public IP: $PUBLIC_IP"
echo -n "  IP type: "; curl -s "https://ipinfo.io/$PUBLIC_IP/json" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'org={d.get(\"org\",\"?\")}, hosting={d.get(\"hosting\",\"?\")}')" 2>/dev/null || echo "check failed"
echo "  RISK: Datacenter/VPS IPs have high fraud scores in IPQS/MaxMind/Spur"

echo ""
echo "--- 3.2 DNS LEAK CHECK ---"
echo -n "  Resolv.conf nameservers: "; grep nameserver /etc/resolv.conf | awk '{print $2}' | tr '\n' ' '
echo ""
echo -n "  DNS over HTTPS: "; curl -s "https://cloudflare-dns.com/dns-query?name=example.com&type=A" -H "accept: application/dns-json" 2>/dev/null | python3 -c "import sys,json; print('OK' if json.load(sys.stdin).get('Status')==0 else 'FAIL')" 2>/dev/null || echo "N/A"

echo ""
echo "--- 3.3 VPN/PROXY STATUS ---"
echo -n "  Mullvad: "; systemctl is-active mullvad-daemon 2>/dev/null || echo "inactive"
echo -n "  Xray: "; systemctl is-active xray 2>/dev/null || echo "inactive"
echo -n "  WireGuard interfaces: "; ip link show type wireguard 2>/dev/null | grep -c '^[0-9]' || echo "0"
echo -n "  SOCKS proxies listening: "; ss -tlnp 2>/dev/null | grep -c ':108[0-9]' || echo "0"

echo ""
echo "--- 3.4 eBPF NETWORK SHIELD ---"
echo -n "  eBPF programs loaded: "; bpftool prog list 2>/dev/null | grep -c 'type' || echo "0 (bpftool not found or no progs)"
echo -n "  network_shield.py importable: "
cd /opt/titan/core && python3 -c "import network_shield; print('OK')" 2>/dev/null || echo "FAIL"

###############################################################################
# SECTION 4: PROFILE & IDENTITY CONSISTENCY
###############################################################################
echo ""
echo "=== SECTION 4: PROFILE & IDENTITY CONSISTENCY ==="

cd /opt/titan/core
python3 << 'PYEOF'
import sys, os, json, glob
sys.path.insert(0, '.')

# Check profile directories
profiles_dir = "/opt/titan/profiles"
if os.path.isdir(profiles_dir):
    profiles = [d for d in os.listdir(profiles_dir) if os.path.isdir(os.path.join(profiles_dir, d))]
    print(f"  Profiles directory: {len(profiles)} profiles found")
    for p in profiles[:3]:
        pdir = os.path.join(profiles_dir, p)
        files = os.listdir(pdir)
        has_places = 'places.sqlite' in files
        has_cookies = 'cookies.sqlite' in files
        has_prefs = 'prefs.js' in files
        size = sum(os.path.getsize(os.path.join(pdir, f)) for f in files if os.path.isfile(os.path.join(pdir, f)))
        print(f"    {p}: {len(files)} files, {size/1024/1024:.1f}MB, places={has_places}, cookies={has_cookies}, prefs={has_prefs}")
else:
    print("  Profiles directory: NOT FOUND")

# Check llm_config.json task routing
config_path = "/opt/titan/config/llm_config.json"
if os.path.isfile(config_path):
    with open(config_path) as f:
        cfg = json.load(f)
    tasks = cfg.get("task_routing", cfg.get("tasks", {}))
    print(f"  LLM task routes: {len(tasks)}")
    # Check critical tasks
    critical = ["decline_analysis", "three_ds_strategy", "profile_generation", "target_analysis", "identity_forge"]
    for t in critical:
        found = t in tasks or any(t in k for k in tasks.keys())
        print(f"    {'OK' if found else 'MISSING'}: {t}")
else:
    print("  llm_config.json: NOT FOUND")

# Check oblivion template
tmpl_path = "/opt/titan/config/oblivion_template.json"
if os.path.isfile(tmpl_path):
    with open(tmpl_path) as f:
        tmpl = json.load(f)
    print(f"  Oblivion template: {len(tmpl)} keys")
    # Check critical fingerprint fields
    fp_keys = ["navigator", "screen", "webgl", "canvas", "audio", "fonts", "plugins"]
    for k in fp_keys:
        found = k in tmpl or any(k in str(v).lower() for v in tmpl.values() if isinstance(v, (str, dict)))
        print(f"    {'OK' if found else 'WARN'}: {k} config")
else:
    print("  oblivion_template.json: NOT FOUND")
PYEOF

###############################################################################
# SECTION 5: MODERN ANTIFRAUD DETECTION MATRIX
###############################################################################
echo ""
echo "=== SECTION 5: MODERN ANTIFRAUD DETECTION MATRIX ==="

echo ""
echo "--- 5.1 DETECTION SYSTEMS WE MUST DEFEAT ---"
cat << 'EOF'
  | System | Detection Method | Titan Defense | Risk Level |
  |--------|-----------------|---------------|------------|
  | Forter | Device fingerprint + behavioral | Ghost Motor + HW Shield | MEDIUM |
  | ThreatMetrix | Device DNA + location intel | Full 6-ring | MEDIUM |
  | Kount | Device trust scoring | Profile age + history | LOW |
  | SEON | Email/phone/IP intelligence | Persona enrichment | MEDIUM |
  | Stripe Radar | ML on payment patterns | 3DS strategy | MEDIUM |
  | Adyen RevenueProtect | Risk scoring + 3DS2 | TRA exemption engine | MEDIUM |
  | Riskified | Behavioral biometrics | Ghost Motor + biometric mimicry | HIGH |
  | Signifyd | Identity graph linking | Profile isolation | HIGH |
  | BioCatch | Behavioral biometrics | Biometric mimicry module | HIGH |
  | PerimeterX/HUMAN | Bot detection + JS challenge | Ghost Motor + Camoufox | HIGH |
  | Cloudflare Turnstile | JS challenge + fingerprint | Camoufox + FP injector | MEDIUM |
  | DataDome | Bot/fraud detection | Full stack required | HIGH |
  | Arkose Labs | Challenge-based auth | Manual solve + Ghost Motor | HIGH |
EOF

echo ""
echo "--- 5.2 SPECIFIC DETECTION VECTORS ANALYSIS ---"
cd /opt/titan/core
python3 << 'PYEOF'
import sys
sys.path.insert(0, '.')

vectors = []

# Vector 1: Canvas fingerprint consistency
try:
    import canvas_noise
    vectors.append(("Canvas Noise", "OK", "Deterministic subpixel noise seeded from profile UUID"))
except:
    vectors.append(("Canvas Noise", "FAIL", "Canvas fingerprint will be default/detectable"))

# Vector 2: WebGL consistency
try:
    import webgl_angle
    vectors.append(("WebGL ANGLE", "OK", "GPU vendor/renderer spoofed per profile"))
except:
    vectors.append(("WebGL ANGLE", "FAIL", "WebGL will expose real GPU info"))

# Vector 3: Audio fingerprint
try:
    import audio_hardener
    vectors.append(("Audio Hardener", "OK", "AudioContext fingerprint altered"))
except:
    vectors.append(("Audio Hardener", "FAIL", "AudioContext will expose real audio stack"))

# Vector 4: Font enumeration
try:
    import font_sanitizer
    vectors.append(("Font Sanitizer", "OK", "Font list matches Windows 11 default set"))
except:
    vectors.append(("Font Sanitizer", "FAIL", "Linux fonts exposed — instant detection"))

# Vector 5: Client Hints
try:
    import client_hints_shim
    vectors.append(("Client Hints", "OK", "UA-CH headers spoofed to Windows Chrome"))
except:
    vectors.append(("Client Hints", "FAIL", "Client Hints will expose Linux/Firefox"))

# Vector 6: WebRTC
try:
    import webrtc_leak_preventer
    vectors.append(("WebRTC Leak", "OK", "Local IP leak prevented"))
except:
    vectors.append(("WebRTC Leak", "FAIL", "WebRTC may expose local/VPS IP"))

# Vector 7: Timezone consistency
try:
    import timezone_enforcer
    vectors.append(("Timezone", "OK", "TZ enforced to match billing address"))
except:
    vectors.append(("Timezone", "FAIL", "Timezone mismatch detectable"))

# Vector 8: Battery API
try:
    # Check if navigator.getBattery is handled
    vectors.append(("Battery API", "WARN", "Must return realistic battery level, not 100% always"))
except:
    vectors.append(("Battery API", "WARN", "Battery API needs verification"))

# Vector 9: Navigator.connection
vectors.append(("Network Info API", "WARN", "navigator.connection must show wifi/4g, not ethernet"))

# Vector 10: Screen resolution
vectors.append(("Screen Resolution", "WARN", "Must match common consumer resolutions, not VPS default"))

# Vector 11: Memory/CPU core count
vectors.append(("Hardware Concurrency", "WARN", "navigator.hardwareConcurrency must match spoofed device"))

# Vector 12: Device memory
vectors.append(("Device Memory", "WARN", "navigator.deviceMemory must be 4/8GB, not VPS 32GB"))

# Vector 13: Installed plugins
vectors.append(("Plugin List", "WARN", "navigator.plugins must show Chrome/Firefox default set"))

# Vector 14: Touch support
vectors.append(("Touch Events", "WARN", "ontouchstart should be absent for desktop profile"))

# Vector 15: Headless detection
vectors.append(("Headless Detection", "WARN", "window.chrome, Notification.permission, etc must pass"))

print("\n  DETECTION VECTOR ANALYSIS:")
ok_count = sum(1 for _, s, _ in vectors if s == "OK")
warn_count = sum(1 for _, s, _ in vectors if s == "WARN")
fail_count = sum(1 for _, s, _ in vectors if s == "FAIL")
for name, status, note in vectors:
    icon = "✅" if status == "OK" else "⚠️" if status == "WARN" else "❌"
    print(f"  {icon} {name}: {note}")
print(f"\n  SCORE: {ok_count} OK, {warn_count} WARN, {fail_count} FAIL / {len(vectors)} total")
PYEOF

###############################################################################
# SECTION 6: TITAN.ENV & CONFIG AUDIT
###############################################################################
echo ""
echo "=== SECTION 6: CONFIG AUDIT ==="
echo ""
echo "--- 6.1 titan.env critical keys ---"
if [ -f /opt/titan/config/titan.env ]; then
    # Check critical env vars
    for key in TITAN_VPN_PROVIDER TITAN_PROXY_TYPE TITAN_AI_MODEL TITAN_BROWSER_PATH TITAN_PROFILES_DIR TITAN_TTL TITAN_TCP_WINDOW TITAN_SEARXNG_URL TITAN_FLARESOLVERR_URL; do
        val=$(grep "^${key}=" /opt/titan/config/titan.env 2>/dev/null | head -1 | cut -d= -f2-)
        if [ -n "$val" ]; then
            echo "  OK: $key=$val"
        else
            echo "  MISSING: $key"
        fi
    done
else
    echo "  titan.env NOT FOUND"
fi

echo ""
echo "--- 6.2 eBPF shield sysctl check ---"
# These must be set for Windows TCP/IP mimicry
declare -A EXPECTED
EXPECTED[net.ipv4.ip_default_ttl]=128
EXPECTED[net.ipv4.tcp_timestamps]=1
EXPECTED[net.ipv4.tcp_sack]=1
EXPECTED[net.ipv4.tcp_window_scaling]=1
EXPECTED[net.ipv4.tcp_ecn]=0
EXPECTED[net.ipv4.tcp_fin_timeout]=120
for key in "${!EXPECTED[@]}"; do
    actual=$(sysctl -n "$key" 2>/dev/null)
    expected="${EXPECTED[$key]}"
    if [ "$actual" = "$expected" ]; then
        echo "  OK: $key=$actual (expected=$expected)"
    else
        echo "  MISMATCH: $key=$actual (expected=$expected)"
    fi
done

echo ""
echo "================================================================"
echo "  AUDIT COMPLETE — $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "================================================================"
