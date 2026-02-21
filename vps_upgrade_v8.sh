#!/bin/bash
# TITAN V8.0 MAXIMUM — VPS Upgrade Script
# Applies complete V8.0 rebranding to live VPS
set -e

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  TITAN V8.0 MAXIMUM — VPS Upgrade Script                ║"
echo "║  Rebranding OS identity + syncing V8.0 modules           ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# ── 1. OS Identity ──────────────────────────────────────────────
echo "[1/8] Updating /etc/os-release..."
cat > /etc/os-release << 'OSEOF'
PRETTY_NAME="Titan OS V8.0 Maximum"
NAME="Titan OS"
VERSION_ID="8.0"
VERSION="8.0 (Maximum)"
VERSION_CODENAME=maximum
ID=titanos
HOME_URL="https://titan-os.io"
SUPPORT_URL="https://titan-os.io/support"
BUG_REPORT_URL="https://titan-os.io/bugs"
OSEOF
echo "  ✓ /etc/os-release → Titan OS V8.0 Maximum"

# ── 2. LSB Release ─────────────────────────────────────────────
echo "[2/8] Updating /etc/lsb-release..."
cat > /etc/lsb-release << 'LSBEOF'
DISTRIB_ID=TitanOS
DISTRIB_RELEASE=8.0
DISTRIB_CODENAME=maximum
DISTRIB_DESCRIPTION="Titan OS V8.0 Maximum"
LSBEOF
echo "  ✓ /etc/lsb-release → TitanOS 8.0"

# ── 3. Login Banners ───────────────────────────────────────────
echo "[3/8] Updating login banners..."
cat > /etc/issue << 'ISSUEEOF'
 _____ _ _               ___  ____
|_   _(_) |_ __ _ _ __  / _ \/ ___|
  | | | | __/ _` | '_ \| | | \___ \
  | | | | || (_| | | | | |_| |___) |
  |_| |_|\__\__,_|_| |_|\___/|____/
             V8.0 MAXIMUM

System ready. Auto-login enabled.

ISSUEEOF

echo "Titan OS V8.0 Maximum" > /etc/issue.net
echo "  ✓ /etc/issue + /etc/issue.net updated"

# ── 4. Hostname ─────────────────────────────────────────────────
echo "[4/8] Updating hostname..."
echo "titan-maximum" > /etc/hostname
hostname titan-maximum 2>/dev/null || true

# Update /etc/hosts
if grep -q "titan-singularity" /etc/hosts 2>/dev/null; then
    sed -i 's/titan-singularity/titan-maximum/g' /etc/hosts
fi
# Ensure 127.0.1.1 entry exists
if ! grep -q "127.0.1.1" /etc/hosts; then
    echo "127.0.1.1 titan-maximum" >> /etc/hosts
else
    sed -i 's/127\.0\.1\.1.*/127.0.1.1 titan-maximum/' /etc/hosts
fi
echo "  ✓ hostname → titan-maximum"

# ── 5. MOTD / Profile ──────────────────────────────────────────
echo "[5/8] Updating terminal prompt & MOTD..."
mkdir -p /etc/profile.d
cat > /etc/profile.d/titan-prompt.sh << 'PROMPTEOF'
#!/bin/bash
# Titan OS V8.0 — Custom Terminal Prompt & Environment

# Custom PS1 Prompt
if [ "$EUID" -eq 0 ]; then
    PS1='\[\e[38;5;196m\]\u\[\e[38;5;240m\]@\[\e[38;5;39m\]\h \[\e[38;5;245m\]\w \[\e[38;5;196m\]#\[\e[0m\] '
else
    PS1='\[\e[38;5;39m\]\u\[\e[38;5;240m\]@\[\e[38;5;45m\]titan \[\e[38;5;245m\]\w \[\e[38;5;39m\]>\[\e[0m\] '
fi

export TITAN_ROOT="/opt/titan"
export EDITOR=nano
export VISUAL=nano
export TERM=xterm-256color

# MOTD on first terminal open
if [ -z "$TITAN_MOTD_SHOWN" ] && [ -t 1 ]; then
    export TITAN_MOTD_SHOWN=1
    echo ""
    echo -e "  \e[38;5;39m╔══════════════════════════════════════╗\e[0m"
    echo -e "  \e[38;5;39m║\e[0m   \e[1;38;5;39mTitan OS\e[0m V8.0 Maximum            \e[38;5;39m║\e[0m"
    echo -e "  \e[38;5;39m║\e[0m   Type \e[38;5;45mops\e[0m to launch Operation Center \e[38;5;39m║\e[0m"
    echo -e "  \e[38;5;39m╚══════════════════════════════════════╝\e[0m"
    echo ""
fi
PROMPTEOF
chmod +x /etc/profile.d/titan-prompt.sh
echo "  ✓ Terminal prompt + MOTD → V8.0 Maximum"

# ── 6. Remove Debian Branding Leftovers ─────────────────────────
echo "[6/8] Removing base distro branding..."

# Clear motd if it has Debian text
if grep -qi "debian\|bookworm\|GNU/Linux" /etc/motd 2>/dev/null; then
    echo "" > /etc/motd
fi

# Remove Debian pixmaps and desktop-base branding
rm -f /usr/share/desktop-base/active-theme 2>/dev/null || true
rm -rf /usr/share/pixmaps/debian* 2>/dev/null || true
rm -rf /usr/share/images/desktop-base/desktop-background* 2>/dev/null || true

# Override dpkg vendor
mkdir -p /etc/dpkg/origins
cat > /etc/dpkg/origins/titanos << 'ORIGINEOF'
Vendor: TitanOS
Vendor-URL: https://titan-os.io
Bugs: https://titan-os.io/bugs
Parent: Debian
ORIGINEOF
ln -sf /etc/dpkg/origins/titanos /etc/dpkg/origins/default 2>/dev/null || true

# Strip ID_LIKE from os-release (prevent neofetch/screenfetch leak)
sed -i '/^ID_LIKE=/d' /etc/os-release 2>/dev/null || true

echo "  ✓ Base distro branding removed"

# ── 7. GRUB Branding ───────────────────────────────────────────
echo "[7/8] Updating GRUB branding..."
mkdir -p /etc/default/grub.d
cat > /etc/default/grub.d/titan-branding.cfg << 'GRUBEOF'
# TITAN OS V8.0 — GRUB Configuration
# Custom bootloader branding
GRUB_TIMEOUT=3
GRUB_CMDLINE_LINUX_DEFAULT="quiet splash vt.handoff=7 loglevel=0 rd.systemd.show_status=false rd.udev.log_level=3 udev.log_priority=3"
GRUB_CMDLINE_LINUX=""
GRUB_DISTRIBUTOR="Titan OS"
GRUB_GFXMODE="1920x1080x32,1280x720x32,auto"
GRUB_GFXPAYLOAD_LINUX="keep"
GRUB_DISABLE_OS_PROBER=true
GRUB_BACKGROUND=""
GRUBEOF

# Update GRUB distributor in main config too
if [ -f /etc/default/grub ]; then
    sed -i 's/GRUB_DISTRIBUTOR=.*/GRUB_DISTRIBUTOR="Titan OS"/' /etc/default/grub 2>/dev/null || true
fi
# Rebuild GRUB config
update-grub 2>/dev/null || true
echo "  ✓ GRUB branding → Titan OS"

# ── 8. Final Verification ──────────────────────────────────────
echo "[8/8] Verifying V8.0 branding..."
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  VERIFICATION RESULTS"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Check os-release
if grep -q "titanos" /etc/os-release; then
    echo "  ✓ os-release: $(grep PRETTY_NAME /etc/os-release)"
else
    echo "  ✗ os-release: FAILED"
fi

# Check lsb-release
if grep -q "TitanOS" /etc/lsb-release 2>/dev/null; then
    echo "  ✓ lsb-release: $(grep DISTRIB_DESCRIPTION /etc/lsb-release)"
else
    echo "  ✗ lsb-release: FAILED"
fi

# Check hostname
echo "  ✓ hostname: $(hostname)"

# Check issue
if grep -q "V8.0" /etc/issue; then
    echo "  ✓ issue: V8.0 MAXIMUM banner present"
else
    echo "  ✗ issue: FAILED"
fi

# Check issue.net
if grep -q "V8.0" /etc/issue.net; then
    echo "  ✓ issue.net: $(cat /etc/issue.net)"
else
    echo "  ✗ issue.net: FAILED"
fi

# Check dpkg vendor
if [ -f /etc/dpkg/origins/titanos ]; then
    echo "  ✓ dpkg vendor: TitanOS"
else
    echo "  ✗ dpkg vendor: FAILED"
fi

# Check no ID_LIKE leak
if ! grep -q "ID_LIKE" /etc/os-release; then
    echo "  ✓ ID_LIKE: not present (no base distro leak)"
else
    echo "  ✗ ID_LIKE: LEAKED — $(grep ID_LIKE /etc/os-release)"
fi

# Check no Debian in os-release
if ! grep -qi "debian\|bookworm" /etc/os-release; then
    echo "  ✓ Debian refs: CLEAN (no debian/bookworm in os-release)"
else
    echo "  ✗ Debian refs: FOUND in os-release"
fi

# Check GRUB
if grep -q "Titan OS" /etc/default/grub.d/titan-branding.cfg 2>/dev/null; then
    echo "  ✓ GRUB: Titan OS distributor"
else
    echo "  ✗ GRUB: FAILED"
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  TITAN OS V8.0 MAXIMUM — VPS UPGRADE COMPLETE"
echo "═══════════════════════════════════════════════════════════"
