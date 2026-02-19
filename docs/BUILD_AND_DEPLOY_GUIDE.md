# TITAN V7.0 SINGULARITY — Build & Deploy Guide

**For Windows operators without WSL/Docker. Build on a cloud VPS, deploy on a separate VPS.**

---

## Overview

| Phase | What | Where | Time |
|-------|------|-------|------|
| **Phase A** | Build the ISO | Debian 12 VPS (temporary, destroy after) | 30–90 min |
| **Phase B** | Deploy the ISO | KVM VPS with ISO boot support | 5–15 min |
| **Phase C** | Set up Lucid VPN relay | Separate privacy VPS | 10 min |
| **Phase D** | Configure residential exit | Home PC or mobile hotspot | 5 min |
| **Phase E** | Clone & Configure (C&C) | Existing Debian 12 VPS | 10 min |

---

## Phase A: Build the ISO

### A.1 — VPS Recommendation for Building

You need a **temporary** Debian 12 VPS to compile the ISO. Destroy it after downloading your ISO.

| Provider | Plan | Specs | Price | Why |
|----------|------|-------|-------|-----|
| **Kamatera** (recommended) | Cloud Server | 4 vCPU, 8 GB RAM, 40 GB SSD | ~$0.05/hr (~$1.50 for build) | Hourly billing, Debian 12 image, fast provisioning |
| **Hetzner** | CX31 | 4 vCPU, 8 GB RAM, 80 GB SSD | €8.50/mo (prorate hourly) | EU-based, excellent peering, Debian 12 |
| **Vultr** | Cloud Compute | 4 vCPU, 8 GB RAM, 160 GB SSD | $48/mo ($0.07/hr) | Instant deploy, global regions |
| **DigitalOcean** | Droplet | 4 vCPU, 8 GB RAM, 160 GB SSD | $48/mo ($0.07/hr) | Simple UI, Debian 12 one-click |

> **Minimum specs:** 4 CPU, 8 GB RAM, 30 GB free disk.  
> **OS:** Debian 12 (Bookworm) x86_64 — do NOT use Ubuntu for building.

### A.2 — Provision the Build VPS

1. Sign up at [Kamatera](https://www.kamatera.com/) (or your choice)
2. Create server:
   - **OS:** Debian 12 (Bookworm) 64-bit
   - **CPU:** 4 cores
   - **RAM:** 8 GB
   - **Disk:** 40 GB SSD
   - **Region:** Any (closest to you for faster SCP)
3. Note the **IP address** and **root password** from the dashboard

### A.3 — Install Git for Windows (on your Windows machine)

You need an SSH/SCP client. Install **Git for Windows** which includes Git Bash with SSH and SCP:

1. Download from: https://gitforwindows.org/
2. Install with default options
3. Open **Git Bash** (from Start menu)

### A.4 — Upload Repo to Build VPS

In **Git Bash** on your Windows machine:

```bash
# Upload the entire repo to the VPS
scp -r "/c/Users/Administrator/Desktop/final lucid/titan-main" root@<VPS_IP>:/root/titan-main
```

Replace `<VPS_IP>` with your build VPS IP address. Enter the root password when prompted.

> **Alternative:** If your repo is on GitHub/GitLab, SSH into the VPS and clone directly:
> ```bash
> ssh root@<VPS_IP>
> apt-get update && apt-get install -y git
> git clone <YOUR_REPO_URL> /root/titan-main
> ```

### A.5 — Run the Build

SSH into the build VPS and run the cloud build script:

```bash
# SSH into the VPS
ssh root@<VPS_IP>

# Run the one-shot builder
cd /root/titan-main
bash scripts/cloud_build.sh
```

This will:
1. Install all build dependencies (live-build, debootstrap, etc.)
2. Run `build_iso.sh` through all 9 phases
3. Output: `/root/titan-main/lucid-titan-v7.0-singularity.iso`

**Build time:** 30–90 minutes depending on VPS speed and network.

### A.6 — Download the ISO

After the build completes, download the ISO to your Windows machine. In **Git Bash**:

```bash
# Download ISO
scp root@<VPS_IP>:/root/titan-main/lucid-titan-v7.0-singularity.iso "/c/Users/Administrator/Desktop/"

# Download checksum
scp root@<VPS_IP>:/root/titan-main/lucid-titan-v7.0-singularity.iso.sha256 "/c/Users/Administrator/Desktop/"
```

### A.7 — Destroy the Build VPS

Once you have the ISO, **delete the build VPS** from your provider dashboard to stop billing and leave no traces.

---

## Phase E: Clone & Configure (C&C) Migration

The Clone & Configure (C&C) method is the fastest way to transform a standard Debian 12 VPS into a Titan Singularity Node. This method is 100% automated and includes stealth acquisition and kernel mutation.

### E.1 — Deploy to Fresh Debian 12
On your target VPS (Debian 12 recommended):

```bash
# Download and run the deployment script
wget https://raw.githubusercontent.com/YOUR_REPO/titan-main/deploy_vps.sh
chmod +x deploy_vps.sh
sudo ./deploy_vps.sh
```

### E.2 — Execute 100% Automated Migration
After the deployment script completes, run the migration command:

```bash
sudo titan-migrate
```

**This command performs the following:**
1. **Hardens the Network Stack:** Injects TTL=128 and disables TCP timestamps.
2. **Syncs Configuration:** Applies forensic hardening to the host OS.
3. **Finalizes Source:** Runs the Singularity Compiler to sanitize the build tree.
4. **Launches Build Engine:** Starts the ISO build process in a detached `tmux` session.

### E.3 — Monitor Progress
Attach to the build session:
```bash
tmux attach -t titan-build
```

---

## Phase B: Deploy the ISO (Run TITAN OS)

### B.1 — VPS Recommendation for Deployment

The deployment VPS is where TITAN OS actually **runs**. This is a long-term server.

**Critical requirements:**
- **KVM virtualization** (not OpenVZ/LXC — TITAN needs kernel access for eBPF, DKMS modules, nftables)
- **Custom ISO boot** support (mount your own ISO)
- **Privacy-friendly** jurisdiction (outside Five Eyes if possible)
- **Dedicated IP** (not shared)

| Provider | Plan | Specs | Price | ISO Boot | Privacy |
|----------|------|-------|-------|----------|---------|
| **Kamatera** (recommended) | Cloud Server | 4 vCPU, 8 GB RAM, 100 GB SSD | ~$36/mo | ✅ Custom ISO upload | Israel (neutral) |
| **Hetzner** | CX31 | 4 vCPU, 8 GB RAM, 80 GB SSD | €8.50/mo | ✅ ISO mount via rescue | Germany (14-Eyes but cheap) |
| **Vultr** | Bare Metal / Cloud | 4 vCPU, 8 GB RAM, 160 GB SSD | $48/mo | ✅ Custom ISO upload | US (not ideal, many regions) |
| **FlokiNET** | VPS-3 | 4 vCPU, 8 GB RAM, 80 GB SSD | €29/mo | ✅ Custom ISO | Iceland/Romania (privacy haven) |
| **Njalla** | VPS | 4 vCPU, 4 GB RAM, 80 GB | €15/mo | ✅ Custom ISO | Sweden (activist-run) |
| **BuyVM** | KVM Slice | 4 vCPU, 4 GB RAM, 80 GB SSD | $15/mo | ✅ Custom ISO | Luxembourg |
| **1984 Hosting** | VPS | 4 vCPU, 4 GB RAM, 40 GB | €9.95/mo | ✅ ISO mount | Iceland (privacy-first) |

> **Best privacy tier:** FlokiNET (Iceland) or 1984 Hosting (Iceland) — both accept crypto, minimal logging.  
> **Best value:** Kamatera or Hetzner — easiest ISO upload workflow.  
> **Minimum specs:** 4 vCPU, 4 GB RAM (8 GB recommended), 40 GB SSD, KVM.

### B.2 — Upload and Boot the ISO

The exact steps vary by provider. Here are the most common:

#### Kamatera
1. Go to **My Cloud → Servers → Create New Server**
2. Choose **"My ISO"** under OS selection
3. Upload `lucid-titan-v7.0-singularity.iso` via the dashboard
4. Select your specs (4 vCPU, 8 GB RAM, 100 GB SSD)
5. Create — the server boots from your ISO

#### Hetzner
1. Create a server with any OS (Debian placeholder)
2. Go to **Rescue** tab → Enable rescue mode
3. Mount ISO via `dd` or the ISO mount tool in Robot panel
4. Reboot into your ISO

#### Vultr
1. Go to **Products → ISOs → Add ISO**
2. Upload `lucid-titan-v7.0-singularity.iso` (direct upload or URL)
3. Create new server → Choose **"Upload ISO"** as OS
4. Select your plan and deploy

#### FlokiNET / Njalla
1. Open a support ticket requesting custom ISO mount
2. Upload ISO via SFTP/SCP to their staging area
3. They mount it and reboot your VPS

### B.3 — First Boot

Once TITAN OS boots:

1. **`titan-first-boot`** runs automatically — installs all packages, DKMS modules, Python deps, Camoufox
2. Wait for all 11 steps to complete (5–15 minutes)
3. Login with default credentials (set during live-build)
4. Configure `/opt/titan/config/titan.env` with your API keys and proxy settings

### B.4 — Verify Installation

```bash
# Run the verification script
bash /opt/titan/scripts/verify_titan.sh

# Expected: All 11 modules GREEN
# Genesis Engine .............. ✅
# Fingerprint Injector ........ ✅
# TLS Parrot .................. ✅
# Hardware Shield ............. ✅
# Lucid VPN ................... ✅
# Ghost Motor ................. ✅
# Cerberus Validator .......... ✅
# Network Jitter .............. ✅
# Pre-flight Validator ........ ✅
# Timezone Enforcer ........... ✅
# Font Sanitizer .............. ✅
```

---

## Phase C: Set Up Lucid VPN Relay (Optional but Recommended)

The Lucid VPN relay is a **separate VPS** that acts as the Xray VLESS+Reality server. This is NOT the same VPS running TITAN OS.

### C.1 — VPS Recommendation for Relay

| Provider | Why | Price |
|----------|-----|-------|
| **FlokiNET Iceland** | Privacy haven, no logs, crypto payments | €12/mo |
| **Njalla** | Activist-run, anonymous registration | €15/mo |
| **1984 Hosting Iceland** | Strong privacy laws | €6/mo |
| **BuyVM Luxembourg** | Cheap, KVM, good peering | $3.50/mo |

> **Specs needed:** 1 vCPU, 1 GB RAM, 10 GB SSD — relay is lightweight.  
> **OS:** Debian 12 minimal.

### C.2 — Deploy the Relay

```bash
# SSH into the relay VPS
ssh root@<RELAY_VPS_IP>

# Upload and run the setup script
scp vpn/setup-vps-relay.sh root@<RELAY_VPS_IP>:/root/
ssh root@<RELAY_VPS_IP> "bash /root/setup-vps-relay.sh"
```

The script automatically:
1. Installs Xray-core with VLESS+Reality
2. Generates x25519 keypair
3. Configures Unbound DNS resolver
4. Installs Tailscale and joins your tailnet
5. Hardens firewall (UFW + fail2ban)
6. Outputs connection credentials

**Save the output!** You'll need:
- `LUCID_VPN_VPS_ADDRESS` (relay IP)
- `LUCID_VPN_XRAY_UUID`
- `LUCID_VPN_XRAY_PUBLIC_KEY`
- `LUCID_VPN_XRAY_SHORT_ID`
- `LUCID_VPN_TAILSCALE_AUTH_KEY`

### C.3 — Configure TITAN to Use the Relay

On your TITAN OS VPS, edit `/opt/titan/config/titan.env`:

```bash
# Lucid VPN Configuration
LUCID_VPN_ENABLED=true
LUCID_VPN_MODE=lucid_vpn
LUCID_VPN_VPS_ADDRESS=<RELAY_IP>
LUCID_VPN_VPS_PORT=443
LUCID_VPN_XRAY_UUID=<from relay output>
LUCID_VPN_XRAY_PUBLIC_KEY=<from relay output>
LUCID_VPN_XRAY_SHORT_ID=<from relay output>
LUCID_VPN_SNI=www.microsoft.com
LUCID_VPN_TAILSCALE_AUTH_KEY=<from Tailscale admin console>
LUCID_VPN_EXIT_NODE_IP=<residential exit IP>
LUCID_VPN_EXIT_NODE_TYPE=residential
```

---

## Phase D: Set Up Residential Exit Node (Optional)

For maximum trust score, route traffic through a residential IP. This runs on a **home PC or mobile hotspot**.

### D.1 — On a Home PC (Windows/Linux/Mac)

```bash
# Install Tailscale: https://tailscale.com/download
# Login to the same tailnet as the relay

# Enable as exit node (Linux)
sudo tailscale up --advertise-exit-node --auth-key=<TAILSCALE_AUTH_KEY>

# Enable as exit node (Windows)
# Right-click Tailscale tray icon → "Exit Node" → "Run as exit node"
```

### D.2 — On a Mobile Hotspot (Highest Trust)

1. Install Tailscale on an Android phone
2. Connect phone to 4G/5G (NOT WiFi)
3. Enable "Run as exit node" in Tailscale app
4. Traffic now exits through a mobile carrier CGNAT IP — **highest trust tier**

### D.3 — Approve Exit Node

In the [Tailscale Admin Console](https://login.tailscale.com/admin/machines):
1. Find the exit node machine
2. Click **"..."** → **"Edit route settings"**
3. Enable **"Use as exit node"**

---

## Quick Reference: Complete Network Path

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        COMPLETE DATA FLOW                              │
│                                                                        │
│  TITAN OS (KVM VPS)                                                    │
│    │                                                                   │
│    ├─ Xray Client (VLESS+Reality, TLS 1.3 masquerade)                 │
│    │   └─ Looks like HTTPS to www.microsoft.com                       │
│    │                                                                   │
│    ▼                                                                   │
│  VPS Relay (Iceland/Romania)                                           │
│    │                                                                   │
│    ├─ Xray Server decrypts → Tailscale mesh                           │
│    │                                                                   │
│    ▼                                                                   │
│  Residential Exit (Home PC / Mobile Hotspot)                           │
│    │                                                                   │
│    ├─ TCP/IP spoofed to Windows 10 signature                          │
│    ├─ IP = Comcast/AT&T/T-Mobile (trusted residential/mobile)         │
│    │                                                                   │
│    ▼                                                                   │
│  Target Website (Amazon, etc.)                                         │
│    └─ Sees: Windows 10, Chrome 131, residential IP, clean fingerprint │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Cost Summary

| Component | Provider | Monthly Cost |
|-----------|----------|-------------|
| **Build VPS** (temporary) | Kamatera | ~$1.50 one-time |
| **TITAN OS VPS** (deployment) | Kamatera / FlokiNET | $15–36/mo |
| **Lucid VPN Relay** | BuyVM / 1984 Hosting | $3.50–12/mo |
| **Residential Exit** | Your home PC / phone | Free |
| **Tailscale** | Free tier (up to 100 devices) | Free |
| **Total ongoing** | | **$18.50–48/mo** |

---

## Checklist

- [ ] Git for Windows installed on your Windows machine
- [ ] Build VPS provisioned (Debian 12, 4 vCPU, 8 GB RAM)
- [ ] Repo uploaded to build VPS
- [ ] `cloud_build.sh` completed successfully
- [ ] ISO downloaded to your Windows machine
- [ ] Build VPS destroyed
- [ ] Deployment VPS provisioned (KVM, custom ISO support)
- [ ] ISO uploaded and booted on deployment VPS
- [ ] `titan-first-boot` completed (11/11 steps)
- [ ] `/opt/titan/config/titan.env` configured with API keys
- [ ] Lucid VPN relay deployed (optional)
- [ ] Residential exit node connected (optional)
- [ ] Pre-flight validator passes all checks

---

*TITAN V7.0 SINGULARITY — Build & Deploy Guide*  
*Authority: Dva.12*

