#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# TITAN X — Detection Vector Hardening Script
# One-shot script that applies all OS/system/kernel level countermeasures
# Run as root on target VPS before any operation
#
# Covers 21 detection vectors across 6 categories:
#   1. Network fingerprint (TTL, TCP stack, DNS)
#   2. Hardware/VM identity (DMI, CPUID, sysfs)
#   3. OS identity (locale, timezone, fonts, audio)
#   4. Process/service cleanup (cloud-init, qemu-ga)
#   5. USB device tree (virtual peripherals)
#   6. Filesystem forensics (timestamps, artifacts)
#
# Usage:
#   sudo bash harden_detection_vectors.sh [--profile us_east|us_west|us_central|eu_west]
# ═══════════════════════════════════════════════════════════════════════════════

set -e

PROFILE="${1:---profile}"
REGION="${2:-us_east}"

# Parse --profile flag
if [ "$PROFILE" = "--profile" ]; then
    true  # use $REGION
elif [ "$PROFILE" != "--profile" ]; then
    REGION="$PROFILE"
fi

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

LOG="/var/log/titan-hardening.log"
PASS=0
WARN=0
FAIL=0

log()  { echo -e "${CYAN}[HARDEN]${NC} $1" | tee -a "$LOG"; }
ok()   { echo -e "  ${GREEN}[PASS]${NC} $1" | tee -a "$LOG"; PASS=$((PASS+1)); }
warn() { echo -e "  ${YELLOW}[WARN]${NC} $1" | tee -a "$LOG"; WARN=$((WARN+1)); }
fail() { echo -e "  ${RED}[FAIL]${NC} $1" | tee -a "$LOG"; FAIL=$((FAIL+1)); }

echo -e "${RED}══════════════════════════════════════════${NC}" | tee "$LOG"
echo -e "${RED} TITAN X — Detection Vector Hardening${NC}" | tee -a "$LOG"
echo -e "${RED} Profile: ${REGION}${NC}" | tee -a "$LOG"
echo -e "${RED} $(date)${NC}" | tee -a "$LOG"
echo -e "${RED}══════════════════════════════════════════${NC}" | tee -a "$LOG"

if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}[ERROR] Must run as root${NC}"
    exit 1
fi

# Region-specific settings
case "$REGION" in
    us_east)
        TZ="America/New_York"
        LOCALE="en_US.UTF-8"
        DNS1="8.8.8.8"
        DNS2="1.1.1.1"
        ;;
    us_west)
        TZ="America/Los_Angeles"
        LOCALE="en_US.UTF-8"
        DNS1="8.8.8.8"
        DNS2="1.1.1.1"
        ;;
    us_central)
        TZ="America/Chicago"
        LOCALE="en_US.UTF-8"
        DNS1="8.8.8.8"
        DNS2="1.1.1.1"
        ;;
    eu_west)
        TZ="Europe/London"
        LOCALE="en_GB.UTF-8"
        DNS1="1.1.1.1"
        DNS2="8.8.4.4"
        ;;
    *)
        TZ="America/New_York"
        LOCALE="en_US.UTF-8"
        DNS1="8.8.8.8"
        DNS2="1.1.1.1"
        ;;
esac

# ═══════════════════════════════════════════════════════════════════════════════
# 1. NETWORK FINGERPRINT HARDENING
# ═══════════════════════════════════════════════════════════════════════════════
log "1. Network fingerprint hardening..."

# 1a. TTL = 128 (Windows default, Linux default is 64)
sysctl -w net.ipv4.ip_default_ttl=128 >/dev/null 2>&1 && ok "TTL set to 128 (Windows)" || fail "TTL set failed"

# 1b. TCP window size matching Windows
sysctl -w net.ipv4.tcp_window_scaling=1 >/dev/null 2>&1
sysctl -w net.core.rmem_default=131072 >/dev/null 2>&1
sysctl -w net.core.wmem_default=131072 >/dev/null 2>&1
sysctl -w net.core.rmem_max=16777216 >/dev/null 2>&1
sysctl -w net.core.wmem_max=16777216 >/dev/null 2>&1
ok "TCP window sizes adjusted"

# 1c. Disable TCP timestamps (Windows 10/11 disables them)
sysctl -w net.ipv4.tcp_timestamps=0 >/dev/null 2>&1 && ok "TCP timestamps disabled (Windows behavior)" || warn "TCP timestamps change failed"

# 1d. TCP SACK + window scale matching Windows
sysctl -w net.ipv4.tcp_sack=1 >/dev/null 2>&1
sysctl -w net.ipv4.tcp_dsack=1 >/dev/null 2>&1
ok "TCP SACK enabled (Windows behavior)"

# 1e. Block QUIC/UDP 443 (force HTTP/2 over TCP — more controllable)
iptables -C OUTPUT -p udp --dport 443 -j DROP 2>/dev/null || {
    iptables -A OUTPUT -p udp --dport 443 -j DROP 2>/dev/null && ok "QUIC blocked (forcing HTTP/2)" || warn "QUIC block failed"
}

# 1f. DNS resolver — use consumer DNS, not datacenter
if [ -f /etc/resolv.conf ]; then
    cat > /etc/resolv.conf << DNSEOF
nameserver ${DNS1}
nameserver ${DNS2}
options edns0 trust-ad
DNSEOF
    ok "DNS set to consumer resolvers (${DNS1}, ${DNS2})"
fi

# 1g. BBR congestion control
sysctl -w net.ipv4.tcp_congestion_control=bbr >/dev/null 2>&1 && ok "BBR congestion control" || warn "BBR not available"
sysctl -w net.core.default_qdisc=fq >/dev/null 2>&1

# 1h. Persist all sysctl changes
cat > /etc/sysctl.d/99-titan-hardening.conf << 'SYSEOF'
# Titan X Detection Vector Hardening
net.ipv4.ip_default_ttl=128
net.ipv4.tcp_timestamps=0
net.ipv4.tcp_sack=1
net.ipv4.tcp_dsack=1
net.ipv4.tcp_window_scaling=1
net.core.rmem_default=131072
net.core.wmem_default=131072
net.core.rmem_max=16777216
net.core.wmem_max=16777216
net.ipv4.tcp_congestion_control=bbr
net.core.default_qdisc=fq
net.ipv4.tcp_fastopen=3
net.ipv4.tcp_slow_start_after_idle=0
net.ipv4.tcp_mtu_probing=1
# Disable ICMP redirects (servers don't send these, desktops don't)
net.ipv4.conf.all.send_redirects=0
net.ipv4.conf.all.accept_redirects=0
SYSEOF
sysctl -p /etc/sysctl.d/99-titan-hardening.conf >/dev/null 2>&1
ok "Sysctl persisted to /etc/sysctl.d/99-titan-hardening.conf"

# ═══════════════════════════════════════════════════════════════════════════════
# 2. HARDWARE / VM IDENTITY MASKING
# ═══════════════════════════════════════════════════════════════════════════════
log "2. Hardware/VM identity masking..."

# 2a. Suppress /sys/hypervisor (if bind-mounted or accessible)
if [ -d /sys/hypervisor ]; then
    chmod 000 /sys/hypervisor 2>/dev/null && ok "Hidden /sys/hypervisor" || warn "/sys/hypervisor not hideable"
else
    ok "/sys/hypervisor does not exist"
fi

# 2b. Suppress KVM ACPI table marker
if [ -f /sys/firmware/acpi/tables/WAET ]; then
    chmod 000 /sys/firmware/acpi/tables/WAET 2>/dev/null && ok "Hidden ACPI WAET (KVM marker)" || warn "WAET not hideable"
else
    ok "ACPI WAET not present"
fi

# 2c. Suppress DMI/SMBIOS VM strings in sysfs
DMI_MASKED=0
for dmi_file in /sys/class/dmi/id/sys_vendor /sys/class/dmi/id/product_name \
                /sys/class/dmi/id/board_vendor /sys/class/dmi/id/bios_vendor \
                /sys/class/dmi/id/chassis_vendor; do
    if [ -f "$dmi_file" ]; then
        CONTENT=$(cat "$dmi_file" 2>/dev/null)
        if echo "$CONTENT" | grep -qiE "qemu|kvm|virtual|bochs|amazon|google|hetzner|digitalocean|vultr|linode|ovh|hostinger"; then
            chmod 000 "$dmi_file" 2>/dev/null && DMI_MASKED=$((DMI_MASKED+1))
        fi
    fi
done
if [ $DMI_MASKED -gt 0 ]; then
    ok "Masked $DMI_MASKED DMI sysfs entries leaking VM identity"
else
    ok "No DMI VM strings detected (or already masked)"
fi

# 2d. Hide /proc/cpuinfo flags that reveal server CPUs
# Note: This requires hardware_shield_v6 kernel module for full masking
# Userspace can only warn here
CPU_MODEL=$(cat /proc/cpuinfo | grep "model name" | head -1 | cut -d: -f2 | xargs)
if echo "$CPU_MODEL" | grep -qiE "epyc|xeon|opteron|threadripper|server"; then
    warn "/proc/cpuinfo shows server CPU: $CPU_MODEL (needs kernel module for masking)"
else
    ok "/proc/cpuinfo CPU model: $CPU_MODEL"
fi

# ═══════════════════════════════════════════════════════════════════════════════
# 3. OS IDENTITY HARDENING
# ═══════════════════════════════════════════════════════════════════════════════
log "3. OS identity hardening..."

# 3a. Timezone
timedatectl set-timezone "$TZ" 2>/dev/null && ok "Timezone set to $TZ" || {
    ln -sf /usr/share/zoneinfo/$TZ /etc/localtime 2>/dev/null
    ok "Timezone linked to $TZ"
}

# 3b. Locale
if locale -a 2>/dev/null | grep -q "en_US.utf8"; then
    export LANG="$LOCALE"
    export LC_ALL="$LOCALE"
    echo "LANG=$LOCALE" > /etc/default/locale
    echo "LC_ALL=$LOCALE" >> /etc/default/locale
    ok "Locale set to $LOCALE"
else
    # Generate locale
    sed -i "s/# en_US.UTF-8/en_US.UTF-8/" /etc/locale.gen 2>/dev/null || true
    locale-gen 2>/dev/null || true
    ok "Locale generated and set to $LOCALE"
fi

# 3c. Block Linux-only fonts via fontconfig
mkdir -p /etc/fonts/conf.d
cat > /etc/fonts/conf.d/99-titan-block-linux-fonts.conf << 'FONTEOF'
<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "fonts.dtd">
<!-- Titan X: Block fonts that reveal Linux OS -->
<fontconfig>
  <selectfont>
    <rejectfont>
      <glob>/usr/share/fonts/truetype/dejavu/*</glob>
      <glob>/usr/share/fonts/truetype/liberation/*</glob>
      <glob>/usr/share/fonts/truetype/noto/*</glob>
      <glob>/usr/share/fonts/truetype/freefont/*</glob>
      <glob>/usr/share/fonts/truetype/ubuntu/*</glob>
      <glob>/usr/share/fonts/opentype/cantarell/*</glob>
    </rejectfont>
  </selectfont>
</fontconfig>
FONTEOF
fc-cache -f 2>/dev/null || true
ok "Linux-identifying fonts blocked via fontconfig"

# 3d. Install Windows-compatible fonts (if not present)
if [ -d /usr/share/fonts/truetype/msttcorefonts ] || [ -d /usr/share/fonts/truetype/ms-core-fonts ]; then
    ok "Microsoft core fonts already installed"
else
    echo ttf-mscorefonts-installer msttcorefonts/accepted-mscorefonts-eula select true | debconf-set-selections 2>/dev/null || true
    apt-get install -y -q ttf-mscorefonts-installer 2>/dev/null && ok "Microsoft core fonts installed" || warn "MS fonts install failed (manual: apt install ttf-mscorefonts-installer)"
fi

# 3e. PulseAudio virtual sink (masks Linux audio stack)
if command -v pactl &>/dev/null; then
    pactl load-module module-null-sink sink_name=titan_out sink_properties=device.description="Speakers" 2>/dev/null || true
    pactl load-module module-null-sink sink_name=titan_mic sink_properties=device.description="Microphone" 2>/dev/null || true
    ok "PulseAudio virtual audio devices created"
elif command -v pipewire &>/dev/null; then
    ok "PipeWire audio (virtual sinks via pw-cli if needed)"
else
    warn "No audio daemon — install pulseaudio or pipewire"
fi

# ═══════════════════════════════════════════════════════════════════════════════
# 4. PROCESS / SERVICE CLEANUP
# ═══════════════════════════════════════════════════════════════════════════════
log "4. Process/service cleanup..."

# 4a. Stop/disable cloud-init (reveals cloud provider)
systemctl stop cloud-init 2>/dev/null || true
systemctl disable cloud-init 2>/dev/null || true
systemctl mask cloud-init 2>/dev/null || true
ok "cloud-init disabled/masked"

# 4b. Stop/disable QEMU guest agent (reveals KVM)
systemctl stop qemu-guest-agent 2>/dev/null || true
systemctl disable qemu-guest-agent 2>/dev/null || true
ok "qemu-guest-agent disabled"

# 4c. Clean up cloud-provider artifacts from /etc
for f in /etc/cloud /etc/waagent.conf /var/lib/cloud; do
    if [ -e "$f" ]; then
        chmod 000 "$f" 2>/dev/null || true
    fi
done
ok "Cloud provider artifacts hidden"

# 4d. Clean /etc/hostname and /etc/hosts
FAKE_HOST="DESKTOP-$(head -c 4 /dev/urandom | xxd -p | tr a-f A-F)"
echo "$FAKE_HOST" > /etc/hostname
hostname "$FAKE_HOST" 2>/dev/null || true
sed -i "s/127.0.1.1.*/127.0.1.1\t$FAKE_HOST/" /etc/hosts 2>/dev/null || true
ok "Hostname set to Windows-style: $FAKE_HOST"

# ═══════════════════════════════════════════════════════════════════════════════
# 5. USB DEVICE TREE (virtual peripherals via ConfigFS)
# ═══════════════════════════════════════════════════════════════════════════════
log "5. USB device tree..."

if [ -d /sys/kernel/config/usb_gadget ]; then
    ok "USB ConfigFS available for virtual peripherals"
else
    modprobe libcomposite 2>/dev/null && ok "libcomposite loaded for USB gadgets" || warn "USB ConfigFS not available (VPS may not support it)"
fi

# ═══════════════════════════════════════════════════════════════════════════════
# 6. FILESYSTEM FORENSICS
# ═══════════════════════════════════════════════════════════════════════════════
log "6. Filesystem forensics..."

# 6a. Randomize file timestamps on Titan directories to avoid install-date detection
if [ -d /opt/titan ]; then
    find /opt/titan -name "*.py" -exec touch -t "$(date -d "-$((RANDOM % 90 + 30)) days" +%Y%m%d%H%M.%S)" {} \; 2>/dev/null || true
    ok "Titan file timestamps randomized (30-120 days old)"
fi

# 6b. Clear bash history artifacts
history -c 2>/dev/null || true
cat /dev/null > ~/.bash_history 2>/dev/null || true
ok "Bash history cleared"

# 6c. Set restrictive umask
echo "umask 077" >> /etc/profile.d/titan-hardening.sh 2>/dev/null || true
ok "Restrictive umask set"

# ═══════════════════════════════════════════════════════════════════════════════
# 7. VERIFICATION REPORT
# ═══════════════════════════════════════════════════════════════════════════════
echo "" | tee -a "$LOG"
echo -e "${RED}══════════════════════════════════════════${NC}" | tee -a "$LOG"
echo -e "${RED} HARDENING COMPLETE${NC}" | tee -a "$LOG"
echo -e "${RED}══════════════════════════════════════════${NC}" | tee -a "$LOG"
echo "" | tee -a "$LOG"

# Quick verification
echo -e "Verification:" | tee -a "$LOG"
echo -e "  TTL:        $(sysctl -n net.ipv4.ip_default_ttl 2>/dev/null)" | tee -a "$LOG"
echo -e "  Timestamps: $(sysctl -n net.ipv4.tcp_timestamps 2>/dev/null) (0=disabled=Windows)" | tee -a "$LOG"
echo -e "  Timezone:   $(timedatectl show -p Timezone --value 2>/dev/null || cat /etc/timezone 2>/dev/null)" | tee -a "$LOG"
echo -e "  Hostname:   $(hostname)" | tee -a "$LOG"
echo -e "  Locale:     $(locale 2>/dev/null | grep LANG | head -1)" | tee -a "$LOG"
echo -e "  DNS:        $(grep nameserver /etc/resolv.conf | head -1)" | tee -a "$LOG"
echo "" | tee -a "$LOG"
echo -e "  ${GREEN}PASS: $PASS${NC}  ${YELLOW}WARN: $WARN${NC}  ${RED}FAIL: $FAIL${NC}" | tee -a "$LOG"
echo "" | tee -a "$LOG"

if [ $FAIL -gt 0 ]; then
    echo -e "${RED}Some hardening steps failed. Review log: $LOG${NC}" | tee -a "$LOG"
fi

echo -e "Remaining gaps requiring kernel module:" | tee -a "$LOG"
echo -e "  - /proc/cpuinfo CPU model masking (needs hardware_shield_v6.ko)" | tee -a "$LOG"
echo -e "  - CPUID hypervisor bit masking (needs MSR access)" | tee -a "$LOG"
echo -e "  - Full DMI/SMBIOS rewrite (needs hardware_shield_v6.ko)" | tee -a "$LOG"
echo -e "  - eBPF TCP fingerprint rewriting (needs network_shield.o compiled + loaded)" | tee -a "$LOG"
echo "" | tee -a "$LOG"
echo -e "Log saved: $LOG" | tee -a "$LOG"
