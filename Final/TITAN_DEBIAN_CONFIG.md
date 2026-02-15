# TITAN V6.2 SOVEREIGN — Debian 12 Customization Guide

**Purpose:** Technical manual for configuring Debian 12 (Bookworm) to build the Lucid Titan OS ISO.  
**Audience:** Operators performing manual builds or verifying automated script behavior.  
**Prerequisite:** The codebase must pass `bash scripts/verify_iso.sh` before building.

---

## 1. Build Environment Setup

You **must** use a Debian 12 (Bookworm) host or VM. Ubuntu hosts may fail due to `debootstrap` version mismatches with Debian's `bookworm` suite.

```bash
sudo apt-get update
sudo apt-get install live-build debootstrap squashfs-tools xorriso grub-pc-bin grub-efi-amd64-bin mtools
```

**Minimum host requirements:**
- Debian 12 (Bookworm) x86_64
- 20 GB free disk space
- 4 GB RAM (8 GB recommended)
- Root access (sudo)
- Internet connection (for package downloads)

---

## 2. Live-Build Configuration (`lb config`)

The `iso/auto/config` file is the control center. It runs `lb config` with all necessary parameters when executed.

### 2.1 Critical Flags

| Flag | Value | Reason |
|------|-------|--------|
| `--distribution` | `bookworm` | Stable headers for DKMS kernel modules |
| `--archive-areas` | `"main contrib non-free non-free-firmware"` | WiFi/GPU firmware packages |
| `--binary-images` | `iso-hybrid` | Bootable on USB and DVD |
| `--security` | `true` | Include security.debian.org updates |
| `--updates` | `true` | Include bookworm-updates |

### 2.2 Boot Parameters

```bash
--bootappend-live "boot=live components quiet splash persistence \
  username=user locales=en_US.UTF-8 ipv6.disable=1 net.ifnames=0 \
  mitigations=off apparmor=1 security=apparmor"
```

| Parameter | Purpose |
|-----------|---------|
| `mitigations=off` | Disables CPU vulnerability mitigations for sub-200ms cognitive latency |
| `apparmor=1 security=apparmor` | Enables AppArmor mandatory access control |
| `ipv6.disable=1` | Prevents IPv6 address leaks |
| `net.ifnames=0` | Predictable interface names (eth0, wlan0) |
| `persistence` | Enables persistent storage partition |
| `username=user` | Auto-creates the `user` account |

### 2.3 Additional Recommended Parameter

```bash
random.trust_cpu=on
```
Forces use of hardware RNG (RDRAND/RDSEED) for faster entropy generation. Required for crypto operations during early boot.

### 2.4 Configuration Files

The `iso/config/` directory contains 4 critical config files:

| File | Key Settings |
|------|-------------|
| `bootstrap` | All mirrors → `deb.debian.org/debian`, security → `deb.debian.org/debian-security` |
| `common` | `LB_MODE="debian"`, `LB_INITSYSTEM="systemd"`, `LB_APT_RECOMMENDS="false"` |
| `chroot` | `LB_KEYRING_PACKAGES="debian-archive-keyring"` |
| `binary` | `LB_HDD_LABEL="TITAN-V62"`, `LB_FIRMWARE_CHROOT="true"`, `LB_SYSLINUX_THEME="debian-banner"` |

> **WARNING:** Do NOT revert mirrors to Ubuntu. The Debian 12 base is required for `v4l2loopback-dkms` headers used in the KYC module.

---

## 3. Chroot Customization (`includes.chroot`)

The `iso/config/includes.chroot/` directory overlays files directly onto the target OS filesystem. Every file placed here appears at the same path on the live system.

### 3.1 Network Privacy

| File | Purpose |
|------|---------|
| `etc/sysctl.d/99-titan-hardening.conf` | Kernel hardening: ASLR=2, IPv6 disabled, TCP SYN cookies, eBPF enabled |
| `etc/NetworkManager/conf.d/10-titan-privacy.conf` | MAC randomization for WiFi + Ethernet |
| `etc/nftables.conf` | Default-deny firewall (all 3 chains: policy drop) |

**nftables whitelist (output chain):**
- DNS: 53/udp, 53/tcp
- DNS-over-TLS: 853/tcp (Unbound → Cloudflare/Quad9)
- HTTP/HTTPS: 80/tcp, 443/tcp
- QUIC: 443/udp
- SOCKS/Proxy: 1080, 3128, 8080, 8443, 9050
- Xray/VLESS: 8443/tcp
- Tailscale: 41641/udp
- Cloud Brain: 8000-8001/tcp
- NTP: 123/udp
- SSH: 22/tcp

### 3.2 DNS Privacy

| File | Purpose |
|------|---------|
| `etc/unbound/unbound.conf.d/titan-dns.conf` | Local DNS resolver, DNS-over-TLS to 1.1.1.1 + 9.9.9.9 |
| `etc/systemd/system/titan-dns.service` | Activates local resolver, rewrites resolv.conf |

DNS flow: `Application → 127.0.0.1:53 (Unbound) → TLS → 1.1.1.1:853`

### 3.3 Fingerprint Hardening

| File | Purpose |
|------|---------|
| `etc/fonts/local.conf` | **CRITICAL** — Blocks Linux fonts (DejaVu, Liberation, Noto, Droid, Ubuntu). Substitutes with Windows equivalents (Arial, Times New Roman, Courier New). Without this, any font enumeration reveals Linux. |
| `etc/pulse/daemon.conf` | PulseAudio tuned to 44100Hz/5ms fragments to match Windows CoreAudio signature |
| `usr/lib/firefox-esr/defaults/pref/titan-hardening.js` | Firefox ESR fallback: WebRTC disabled, DNS-over-HTTPS, telemetry off, battery/sensors/gamepad APIs disabled |

### 3.4 System Security

| File | Purpose |
|------|---------|
| `etc/sudoers.d/titan-ops` | Passwordless sudo for `modprobe`, `insmod`, `ffmpeg`, `nft`, `xray`, `tailscale` |
| `etc/polkit-1/localauthority/50-local.d/10-titan-nopasswd.pkla` | PolicyKit rules for passwordless hardware operations |
| `etc/systemd/journald.conf.d/titan-privacy.conf` | Volatile logging only (RAM, no disk) |
| `etc/systemd/coredump.conf.d/titan-no-coredump.conf` | Core dumps disabled |
| `etc/udev/rules.d/99-titan-usb.rules` | USB device access control |

### 3.5 Desktop Environment

| File | Purpose |
|------|---------|
| `etc/lightdm/lightdm.conf` | Auto-login as `user`, XFCE session |
| `etc/lightdm/lightdm-gtk-greeter.conf` | Arc-Dark theme, Papirus-Dark icons |
| `etc/xdg/openbox/menu.xml` | Right-click menu with Titan tools |
| `etc/xdg/openbox/rc.xml` | Keyboard shortcuts (Super+T=terminal, Super+B=browser) |
| `etc/skel/.bashrc` | PATH, aliases, MOTD, colored prompt |
| `etc/issue`, `etc/issue.net` | TITAN V6.2 SOVEREIGN branding |
| `usr/share/applications/titan-*.desktop` | Desktop entries for Titan tools |

---

## 4. Kernel Module Injection (DKMS)

Titan relies on `titan_hw.ko` (Ring 0 hardware shield). Standard `live-build` doesn't compile custom kernel modules. A **build hook** handles this.

### 4.1 Build Hook: `050-hardware-shield.hook.chroot`

This script runs **inside the chroot** during the build process:

1. Installs `linux-headers-amd64` and `build-essential`
2. Copies `hardware_shield_v6.c` + `Makefile` to `/usr/src/titan-hw-6.2.0/`
3. Runs `make` to compile `hardware_shield_v6.ko`
4. Runs `make install` to copy module to `/opt/lucid-empire/hardware_shield/`
5. Runs `depmod -a` to update module dependency database

### 4.2 DKMS Registration: `060-kernel-module.hook.chroot`

Registers the module with DKMS so it survives kernel upgrades:
- Module name: `titan_hw`
- Version: `6.2.0`
- Protocol: `NETLINK_TITAN = 31`

### 4.3 Ring 0 ↔ Ring 3 Communication

The kernel module (`hardware_shield_v6.c`) communicates with userspace (`fingerprint_injector.py`) via Netlink sockets:

```
Browser (Ring 3)                    Kernel (Ring 0)
   │                                     │
   ├─ FingerprintInjector                 │
   │   └─ WebGL vendor/renderer           │
   │                                      │
   ├─ NetlinkHWBridge ──── NETLINK_TITAN=31 ──── hardware_shield_v6.c
   │   └─ send_profile()                  │   └─ Spoof /proc/cpuinfo
   │                                      │   └─ Spoof /sys/class/dmi
   │                                      │
   └─ AudioHardener                       │
       └─ Seeded jitter (SHA-256)         │
```

This ensures that `navigator.hardwareConcurrency` in the browser matches `cat /proc/cpuinfo` at the kernel level.

---

## 5. Kernel Module Blacklist

The `095-os-harden.hook.chroot` writes `/etc/modprobe.d/titan-blacklist.conf`:

| Module | Reason |
|--------|--------|
| `bluetooth`, `btusb`, `btrtl`, `btbcm`, `btintel` | Not needed, reduces fingerprint |
| `uvcvideo` | Real webcam disabled (v4l2loopback used instead) |
| `firewire-core`, `firewire-ohci`, `firewire-sbp2` | DMA attack vector |
| `thunderbolt` | DMA attack vector |
| `nfc`, `near` | Unused wireless |
| `cramfs`, `freevxfs`, `jffs2`, `hfs`, `hfsplus`, `udf` | Rarely needed, attack surface |
| `dccp`, `sctp`, `rds`, `tipc` | Unused network protocols |

---

## 6. Build Hook Sequence

Hooks execute in **alphabetical/numerical order** inside the chroot:

```
050-hardware-shield.hook.chroot  → Compile titan_hw.ko kernel module
060-kernel-module.hook.chroot    → Register with DKMS
070-camoufox-fetch.hook.chroot   → Download hardened browser + pip packages
080-ollama-setup.hook.chroot     → Install AI/ML dependencies (Ollama, scipy, onnxruntime)
090-kyc-setup.hook.chroot        → Configure KYC virtual camera module
095-os-harden.hook.chroot        → Firewall, DNS, kernel blacklist, locale, hostname
 99-fix-perms.hook.chroot        → Final chmod +x, pip fallback installs, cleanup
```

> **IMPORTANT:** `050` must run before `095`. If `hardware_shield_v6.ko` is not compiled before the hardening hook, the DKMS registration will fail.

---

## 7. Package List

The file `iso/config/package-lists/custom.list.chroot` contains all Debian packages. Key categories:

| Category | Packages |
|----------|----------|
| Desktop | xfce4, xfce4-terminal, lightdm, thunar |
| Browser | firefox-esr |
| Network | curl, wget, dnsutils, nftables, unbound, proxychains4, torsocks |
| Security | apparmor, apparmor-utils, firejail, rng-tools5, haveged |
| Video | ffmpeg, v4l2loopback-dkms, mesa-utils |
| Build | build-essential, dkms, linux-headers-amd64, git |
| Python | python3, python3-pip, python3-venv, python3-pyqt6, python3-numpy |
| Audio | pulseaudio, policykit-1 |

**Pip-only packages** (installed by hooks, not in Debian repos):
- `openai`, `onnxruntime`, `aiohttp`, `aioquic`, `camoufox[geoip]`, `browserforge`
- `playwright`, `lz4`, `cryptography`, `stripe`, `httpx`, `fastapi`, `uvicorn`

---

## 8. Systemd Services

| Service | Type | Purpose |
|---------|------|---------|
| `lucid-titan.service` | Simple | Main Titan backend daemon |
| `lucid-ebpf.service` | Simple | eBPF network shield loader |
| `lucid-console.service` | Simple | GUI console auto-start |
| `titan-first-boot.service` | Oneshot | 11-point operational readiness check |
| `titan-dns.service` | Oneshot | DNS privacy activation (resolv.conf rewrite) |

---

## 9. Pre-Build Verification

Run from the `titan-main/` directory:

```bash
bash scripts/verify_iso.sh
```

This checks 105+ items across 9 categories:
- ISO configuration files (mirrors, keyring, bootappend)
- Core modules (31 .py + 2 .c)
- Legacy bridge (`/opt/lucid-empire/`)
- Build hook ordering
- OS hardening configs (20 files)
- Systemd services (5 units)
- Package list (12 critical packages)
- Security (nftables, fonts, Netlink, audio, kernel blacklist)
- Python syntax (when python3 available)

**Expected output:** `STATUS: READY FOR BUILD` with 0 failures.

---

## 10. Build Execution

```bash
cd iso
sudo lb clean        # Purge any previous build artifacts
lb config            # Initialize Debian 12 Sovereign configuration
sudo lb build        # Build the ISO (takes 15-45 minutes)
```

**Output:** `live-image-amd64.hybrid.iso` in the `iso/` directory.

Rename to: `lucid-titan-v6.2-sovereign.iso`

---

## 11. Post-Build Gate Checks

After booting the ISO (VM or bare metal):

| # | Check | Command | Expected |
|---|-------|---------|----------|
| 1 | First boot | Automatic | titan-first-boot passes 11/11 |
| 2 | Identity | `python3 /opt/titan/core/verify_deep_identity.py --os windows_11` | Status = **GHOST** |
| 3 | WebRTC | `titan-browser --debug https://browserleaks.com` | No WebRTC leak |
| 4 | Fonts | `fc-list` | No DejaVu, Liberation, Noto |
| 5 | Audio | Check AudioContext sample rate | 44100 Hz |
| 6 | Firewall | `sudo nft list ruleset` | All 3 chains: policy drop |
| 7 | Webcam | `lsmod \| grep uvcvideo` | Empty (blacklisted) |
| 8 | DNS | `cat /etc/resolv.conf` | nameserver 127.0.0.1 |
| 9 | MAC | `ip link show` | Random MAC on each boot |
| 10 | Kernel | `cat /proc/cmdline` | mitigations=off, apparmor=1 |
| 11 | Entropy | `cat /proc/sys/kernel/random/entropy_avail` | > 256 |

---

## 12. Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `debootstrap` fails | Ubuntu host | Use Debian 12 host |
| Mirrors unreachable | Wrong URLs in `bootstrap` | Verify `deb.debian.org/debian` |
| `titan_hw.ko` not found | 050 hook failed | Check `linux-headers-amd64` installed |
| Fonts visible in browser | Missing `local.conf` | Verify `etc/fonts/local.conf` in chroot |
| WebRTC leaks | Missing Firefox prefs | Verify `titan-hardening.js` in chroot |
| No internet after boot | nftables too strict | Check whitelist in `etc/nftables.conf` |
| Slow boot entropy | Missing haveged | Verify in package list |
| Audio fingerprint mismatch | Random jitter | Verify `_derive_jitter_seed()` in audio_hardener.py |

---

## Appendix: Directory Structure

```
titan-main/
├── iso/
│   ├── auto/
│   │   └── config                      ← lb config parameters
│   └── config/
│       ├── bootstrap                   ← Debian mirror URLs
│       ├── common                      ← LB_MODE, LB_INITSYSTEM
│       ├── chroot                      ← Keyring packages
│       ├── binary                      ← ISO label, firmware
│       ├── package-lists/
│       │   └── custom.list.chroot      ← All Debian packages
│       ├── hooks/live/
│       │   ├── 050-hardware-shield.hook.chroot
│       │   ├── 060-kernel-module.hook.chroot
│       │   ├── 070-camoufox-fetch.hook.chroot
│       │   ├── 080-ollama-setup.hook.chroot
│       │   ├── 090-kyc-setup.hook.chroot
│       │   ├── 095-os-harden.hook.chroot
│       │   └── 99-fix-perms.hook.chroot
│       └── includes.chroot/
│           ├── etc/                    ← OS configuration overlay
│           │   ├── fonts/local.conf
│           │   ├── nftables.conf
│           │   ├── pulse/daemon.conf
│           │   ├── sysctl.d/99-titan-hardening.conf
│           │   ├── NetworkManager/conf.d/10-titan-privacy.conf
│           │   ├── sudoers.d/titan-ops
│           │   ├── systemd/system/*.service
│           │   ├── unbound/unbound.conf.d/titan-dns.conf
│           │   └── lightdm/*.conf
│           ├── opt/titan/
│           │   ├── core/               ← 31 .py + 2 .c + Makefile
│           │   ├── bin/                ← Shell scripts
│           │   ├── config/             ← titan.env
│           │   └── extensions/         ← Ghost Motor browser extension
│           ├── opt/lucid-empire/       ← Legacy backend (12+ .py files)
│           └── usr/lib/firefox-esr/    ← Firefox chroot prefs
├── scripts/
│   ├── verify_iso.sh                   ← Pre-build verification
│   ├── build_iso.sh                    ← Build automation
│   └── *.py                            ← Utility scripts
├── FINAL_PREFLIGHT_CHECK.md            ← Audit report
├── WINDSURF_MISSION_SCOPE.md           ← Agent prompt
└── TITAN_DEBIAN_CONFIG.md              ← This file
```
