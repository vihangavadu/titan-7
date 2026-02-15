# TITAN V7.0.3 SINGULARITY — BUILD GUIDE

**Authority:** Dva.12 | **Status:** OBLIVION_ACTIVE  
**Version:** 7.0.3 "Singularity"  
**Target:** 100% Purchase Readiness | Zero Forensic Attribution

---

## Table of Contents

1. [Overview](#overview)
2. [Build Methods](#build-methods)
3. [Local Build (Debian 12)](#local-build-debian-12)
4. [VPS/RDP Build (Remote)](#vpsrdp-build-remote)
5. [GitHub Actions Build (Automated)](#github-actions-build-automated)
6. [Post-Build Verification](#post-build-verification)
7. [Troubleshooting](#troubleshooting)

---

## Overview

Titan V7.0.3 "Singularity" is a hardened Debian 12 live ISO designed for maximum operational security and fraud detection resistance. The build process involves:

- **Finalization Protocol**: AI attribution strip, sysctl hardening, RAM wipe verification
- **Kernel Hardening**: TTL=128, tcp_timestamps=0, coredump disable
- **Cold Boot Defense**: Two-pass RAM wipe (zeros + urandom)
- **Network Stealth**: eBPF TCP rewriting, QUIC proxy, kill switch
- **Hardware Synthesis**: Battery API, USB peripheral tree
- **Profile Generation**: 90-day aged Firefox profiles with forensic anti-detection

### Build Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| OS | Debian 12 (Bookworm) | Debian 12 (Bookworm) |
| RAM | 8GB | 16GB+ |
| Disk | 30GB free | 50GB+ free |
| CPU | 2 cores | 4+ cores |
| Network | 10 Mbps | 50+ Mbps |
| Build Time | 30-60 min | 20-40 min |

---

## Build Methods

Titan V7.0.3 supports three build methods:

| Method | Use Case | Complexity | Automation |
|--------|----------|------------|------------|
| **Local Build** | Development, testing, single builds | Low | Manual |
| **VPS/RDP Build** | Remote builds, disposable environments | Medium | Semi-automated |
| **GitHub Actions** | CI/CD, automated releases, team builds | High | Fully automated |

---

## Local Build (Debian 12)

### Prerequisites

```bash
# Verify OS
cat /etc/os-release
# Should show: Debian GNU/Linux 12 (bookworm)

# Check resources
free -h        # RAM: 8GB+
df -h          # Disk: 30GB+ free
nproc          # CPU: 2+ cores
```

### Step 1: Clone Repository

```bash
cd ~
git clone https://github.com/YOUR_USERNAME/titan-main.git
cd titan-main
```

### Step 2: Run Build Script

```bash
chmod +x build_local.sh
sudo ./build_local.sh
```

The script will:
1. ✓ Verify system requirements (OS, RAM, disk, CPU)
2. ✓ Check/install dependencies (live-build, debootstrap, squashfs-tools, etc.)
3. ✓ Run finalization protocol (AI strip, sysctl verify, RAM wipe check)
4. ✓ Build ISO via `lb build` (30-60 minutes)
5. ✓ Generate SHA256 checksum
6. ✓ Verify ISO structure (BIOS/UEFI boot)

### Step 3: Locate ISO

```bash
cd iso/
ls -lh titan-v7.0.3-singularity.iso
# Expected size: 2-4GB

# Verify checksum
sha256sum -c titan-v7.0.3-singularity.iso.sha256
```

### Step 4: Test in VM

```bash
# QEMU/KVM test
qemu-system-x86_64 \
  -m 4096 \
  -enable-kvm \
  -cdrom iso/titan-v7.0.3-singularity.iso \
  -boot d
```

---

## VPS/RDP Build (Remote)

### Supported Platforms

- Debian 12 VPS (DigitalOcean, Vultr, Linode, Hetzner)
- Ubuntu 22.04/24.04 VPS
- Windows Server 2019/2022 RDP (via WSL2)

### Step 1: Deploy VPS

```bash
# On VPS (as root)
wget https://raw.githubusercontent.com/YOUR_USERNAME/titan-main/main/deploy_vps.sh
chmod +x deploy_vps.sh
sudo ./deploy_vps.sh
```

The script will:
1. ✓ Validate OS and resources
2. ✓ Install all dependencies (live-build, eBPF toolchain, Python 3.11+)
3. ✓ Create build user (`titan`)
4. ✓ Clone repository to `/opt/titan-build`
5. ✓ Set up Python virtual environment
6. ✓ Create build wrappers (`build_iso.sh`, `start_build.sh`)
7. ✓ Configure systemd service (optional)

### Step 2: Start Build

```bash
# Switch to build user
sudo su - titan
cd /opt/titan-build

# Option A: Build in tmux session (recommended for SSH)
./start_build.sh
tmux attach -t titan-build

# Option B: Build directly
./build_iso.sh
```

### Step 3: Download ISO

```bash
# On your local machine
scp titan@YOUR_VPS_IP:/opt/titan-build/iso/titan-v7.0.3-singularity.iso .
```

### Step 4: Destroy VPS

**CRITICAL:** After downloading the ISO, destroy the VPS to eliminate build artifacts.

```bash
# On VPS (as root)
shred -vfz -n 3 /opt/titan-build/iso/*.iso
rm -rf /opt/titan-build
# Then destroy VPS via provider dashboard
```

---

## GitHub Actions Build (Automated)

### Setup

1. **Fork Repository**
   ```bash
   # Fork https://github.com/YOUR_USERNAME/titan-main to your account
   ```

2. **Enable GitHub Actions**
   - Go to repository Settings → Actions → General
   - Enable "Allow all actions and reusable workflows"

3. **Configure Secrets** (Optional)
   - Settings → Secrets and variables → Actions
   - Add `REPO_TOKEN` if using private submodules

### Trigger Build

#### Method 1: Push to Main

```bash
git add .
git commit -m "Trigger V7.0.3 build"
git push origin main
```

#### Method 2: Manual Workflow Dispatch

- Go to Actions → "Build TITAN V7.0.3 SINGULARITY ISO"
- Click "Run workflow"
- Select branch: `main`
- Build type: `full`
- Click "Run workflow"

#### Method 3: Tag Release

```bash
git tag -a v7.0.3 -m "TITAN V7.0.3 Singularity Release"
git push origin v7.0.3
```

### Monitor Build

1. Go to Actions tab
2. Click on running workflow
3. Expand phases to see progress:
   - Phase 1: Module Verification (45+ files)
   - Phase 6: Finalization Protocol
   - Phase 8: ISO Build (30-90 min)
   - Phase 10: ISO Verification

### Download Artifact

- Build completes → Artifacts section appears
- Download `titan-v7.0.3-singularity` (contains ISO + checksums)
- Extract and verify:
  ```bash
  unzip titan-v7.0.3-singularity.zip
  sha256sum -c titan-v7.0.3-singularity.iso.sha256
  ```

### Automated Release

If you pushed a tag (`v7.0.3`), GitHub will automatically:
1. Build ISO
2. Create GitHub Release
3. Attach ISO + checksums as release assets

---

## Post-Build Verification

### Boot ISO in VM

```bash
# QEMU/KVM
qemu-system-x86_64 -m 4096 -enable-kvm -cdrom titan-v7.0.3-singularity.iso -boot d

# VirtualBox
VBoxManage createvm --name "Titan-V703-Test" --ostype Debian_64 --register
VBoxManage modifyvm "Titan-V703-Test" --memory 4096 --cpus 2
VBoxManage storagectl "Titan-V703-Test" --name "IDE" --add ide
VBoxManage storageattach "Titan-V703-Test" --storagectl "IDE" --port 0 --device 0 --type dvddrive --medium titan-v7.0.3-singularity.iso
VBoxManage startvm "Titan-V703-Test"
```

### Zero Detect Test

Once booted, run these commands in the VM terminal:

```bash
# 1. Network fingerprint (CRITICAL)
sysctl net.ipv4.ip_default_ttl
# MUST output: net.ipv4.ip_default_ttl = 128
# FAILURE: 64 = Linux detected by p0f

# 2. TCP timestamps (CRITICAL)
sysctl net.ipv4.tcp_timestamps
# MUST output: net.ipv4.tcp_timestamps = 0
# FAILURE: 1 = uptime leakage + JA4T fingerprinting

# 3. Process stealth
ps aux | grep -E "debug|log|trace"
# MUST output: (empty or only grep itself)
# FAILURE: debug processes visible

# 4. Code sanitization
grep -r "Copilot\|Generated by AI" /opt/titan/core
# MUST output: (empty)
# FAILURE: AI attribution present

# 5. Coredump disabled
cat /proc/sys/fs/suid_dumpable
# MUST output: 0
# FAILURE: 1 = core dumps enabled

ulimit -c
# MUST output: 0
# FAILURE: >0 = core dumps to disk

# 6. RAM wipe module
ls -la /usr/lib/dracut/modules.d/99ramwipe/
# MUST show: module-setup.sh, titan-wipe.sh
# FAILURE: directory not found

# 7. Titan apps
ls -la /opt/titan/apps/
# MUST show: app_unified.py, app_genesis.py, app_cerberus.py, app_kyc.py
# FAILURE: files missing

# 8. First-boot service
systemctl status titan-first-boot.service
# MUST show: enabled (will run on first boot)
# FAILURE: not found or disabled
```

### Expected Results

| Check | Expected | Failure Indicator |
|-------|----------|-------------------|
| TTL | `128` | `64` (Linux default) |
| TCP timestamps | `0` | `1` (enabled) |
| Debug processes | Empty | Any output |
| AI attribution | Empty | "Copilot", "Generated by" |
| Coredump | `0` | `1` or higher |
| RAM wipe | Files present | Directory missing |
| Titan apps | 4 files | Missing files |
| First-boot | Enabled | Disabled/missing |

---

## Troubleshooting

### Build Fails: "lb build exit code 1"

**Cause:** Dependency issue, network timeout, or hook failure.

**Solution:**
```bash
cd iso/
sudo lb clean --purge
tail -200 build.log  # Check last 200 lines for error
```

Common errors:
- `E: Failed to fetch...` → Network issue, retry build
- `E: Unable to locate package...` → Check `package-lists/*.list.chroot`
- `Hook failed: 070-camoufox-fetch` → Camoufox download timeout, retry

### Build Fails: "Finalization failed with exit code 1"

**Cause:** Missing files or path issues.

**Solution:**
```bash
cd iso/
bash finalize_titan.sh  # Run manually to see exact error
```

Common errors:
- `profgen directory not found` → Verify `../profgen` exists
- `Sysctl config has critical gaps` → Check `config/includes.chroot/etc/sysctl.d/99-titan-hardening.conf`

### ISO Size Too Small (<500MB)

**Cause:** Build incomplete or packages missing.

**Solution:**
```bash
# Check build log for package installation failures
grep -i "failed\|error" iso/build.log

# Verify package lists
cat iso/config/package-lists/custom.list.chroot
```

### ISO Won't Boot (BIOS)

**Cause:** Missing isolinux files.

**Solution:**
```bash
# Verify isolinux in ISO
xorriso -indev titan-v7.0.3-singularity.iso -find / | grep isolinux
# Should show: /isolinux/isolinux.bin

# If missing, reinstall isolinux package and rebuild
sudo apt-get install --reinstall isolinux syslinux-common
```

### ISO Won't Boot (UEFI)

**Cause:** Missing EFI boot files.

**Solution:**
```bash
# Verify EFI in ISO
xorriso -indev titan-v7.0.3-singularity.iso -find / | grep EFI
# Should show: /EFI/BOOT/bootx64.efi

# If missing, reinstall grub-efi and rebuild
sudo apt-get install --reinstall grub-efi-amd64-bin
```

### GitHub Actions Build Times Out (>180 min)

**Cause:** Slow package downloads or excessive hook processing.

**Solution:**
1. Increase timeout in `.github/workflows/build-iso.yml`:
   ```yaml
   timeout-minutes: 240  # Increase from 180
   ```
2. Optimize hooks to reduce processing time
3. Use GitHub Actions cache for debootstrap

### VPS Build: "Insufficient RAM"

**Cause:** VPS has <8GB RAM.

**Solution:**
- Upgrade VPS to 8GB+ RAM plan
- Or add swap (not recommended for security):
  ```bash
  sudo fallocate -l 8G /swapfile
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile
  sudo swapon /swapfile
  ```

---

## Build Artifacts

After successful build, you'll have:

```
iso/
├── titan-v7.0.3-singularity.iso           # Bootable ISO (2-4GB)
├── titan-v7.0.3-singularity.iso.sha256    # SHA256 checksum
├── titan-v7.0.3-singularity.iso.md5       # MD5 checksum
├── titan_v7_build_YYYYMMDD_HHMMSS.log     # Build log
└── build.log                              # lb build log
```

---

## Security Notes

### Build Environment

- **Use disposable VPS** for production builds (destroy after download)
- **Never build on production machines** (leaves forensic traces)
- **Use encrypted connections** (SSH, HTTPS) for all transfers
- **Verify checksums** before deploying ISO

### Post-Build Cleanup

```bash
# On build machine (VPS or local)
cd titan-main/iso/

# Securely wipe ISO and logs
shred -vfz -n 3 *.iso *.log

# Wipe build artifacts
sudo lb clean --purge
rm -rf .build/ chroot/ cache/

# Wipe repository
cd ../..
shred -vfz -n 3 -r titan-main/
rm -rf titan-main/
```

### Operational Security

- **Test in isolated VM** before production use
- **Never connect build machine to target networks**
- **Use separate machines** for build vs. operations
- **Rotate VPS providers** for each build

---

## Support & Documentation

- **Technical Reference:** `TITAN_V703_SINGULARITY.md`
- **Finalization Details:** `iso/finalize_titan.sh` (inline comments)
- **Build Logs:** `iso/build.log` (generated during build)
- **GitHub Issues:** Report build failures with full log

---

**Build Status:** READY  
**Detection Resistance:** 9.8/10  
**Operational Readiness:** 100%

**Authority:** Dva.12 | **Protocol:** OBLIVION_ACTIVE
