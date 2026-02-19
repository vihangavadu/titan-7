# MISSION: TITAN V6.2 SOVEREIGN — CODEBASE AUDIT & FINALITY PATCH

**Role:** Senior Systems Architect & Security Auditor  
**Context:** You are preparing the source code for "Lucid Titan OS" (Debian 12 Live ISO). The codebase is located in the current workspace.  
**Goal:** Analyze the entire directory structure, identify missing dependencies or logic gaps, patch them, and verify the build readiness.

---

## PHASE 1: RECURSIVE ANALYSIS

### 1.1 Map Structure
Scan `iso/config/includes.chroot/opt/titan/` and verify that all Python core modules imported in `__init__.py` actually exist on the file system.

**Expected result:** 29 modules imported, all present. Additional files (`titan_master_verify.py`, 2x `.c`, `Makefile`) exist but are not imported from `__init__.py`.

### 1.2 Legacy Bridge Check
Audit `opt/titan/core/integration_bridge.py`. Ensure it correctly references the legacy path `/opt/lucid-empire/` and that the legacy files exist in `iso/config/includes.chroot/opt/lucid-empire/`.

**Verification points:**
- `sys.path.insert(0, "/opt/lucid-empire/")` present
- `sys.path.insert(0, "/opt/lucid-empire/backend/")` present
- Legacy directory contains `backend/` with 12+ Python files
- Legacy directory contains `bin/` with 8+ executables
- No circular imports between titan core and legacy bridge

### 1.3 C-Level Audit
Check `opt/titan/core/hardware_shield_v6.c` and `network_shield_v6.c`. Verify that the `Makefile` in that directory references the correct kernel headers path for Debian 12 (bookworm).

**Verification points:**
- `Makefile` uses `KDIR ?= /lib/modules/$(shell uname -r)/build` (standard, works on Debian 12)
- `hardware_shield_v6.c` defines `NETLINK_TITAN = 31`
- `050-hardware-shield.hook.chroot` installs `linux-headers-amd64` before running `make`

---

## PHASE 2: GAP DETECTION & PATCHING

### 2.1 Placeholder Scan
Search for strings like `REPLACE_WITH`, `TODO`, or `FIXME` across all `.py`, `.sh`, and `.c` files.

- **Action:** If found in `titan.env`, ensure `titan_env.py` has logic to handle them without crashing (graceful degradation). The `load_env()` function must skip lines where value starts with `REPLACE_WITH`.
- **Action:** If found in logic code, generate a functional patch based on the context (e.g., generate a default UUID if one is missing).

### 2.2 Permission Repair
Scan `scripts/*.sh` and `opt/titan/bin/*`. Ensure they verify executable permissions. If not, verify that `99-fix-perms.hook.chroot` runs `chmod +x` on all binaries and hooks.

**Required chmod targets:**
- `/opt/titan/bin/*`
- `/opt/lucid-empire/bin/*`
- All build hooks in `/iso/config/hooks/live/*.hook.chroot`

### 2.3 Dependency Alignment
Compare imports in `opt/titan/core/*.py` against `iso/config/package-lists/custom.list.chroot` and pip install commands in build hooks.

**Critical third-party libraries to verify:**

| Library | Imported By | Must Be Installed In |
|---------|-------------|---------------------|
| `numpy` | ghost_motor_v6.py | pip (via scipy) |
| `scipy` | ghost_motor_v6.py | pip in 080-ollama-setup |
| `aiohttp` | proxy_manager.py, cerberus_core.py | pip in 99-fix-perms |
| `onnxruntime` | ghost_motor_v6.py | pip in 080-ollama-setup |
| `openai` | cognitive_core.py | pip in 080-ollama-setup |
| `camoufox` | runtime (bin/titan-browser) | pip in 070-camoufox-fetch |
| `browserforge` | runtime | pip in 070-camoufox-fetch |
| `aioquic` | quic_proxy.py | pip in 99-fix-perms |
| `playwright` | referrer_warmup.py | pip in 070-camoufox-fetch |
| `lz4` | profile generation | pip in 99-fix-perms |
| `cryptography` | QUIC certs | pip in 99-fix-perms |
| `stripe` | cerberus_enhanced.py | pip in 99-fix-perms |
| `fastapi` | server.py | pip in 99-fix-perms |

- **Action:** If a Python library is imported but missing from both the package list and pip install hooks, add it to `iso/config/hooks/live/99-fix-perms.hook.chroot` as a `pip install` command.

---

## PHASE 3: FINAL VERIFICATION (PRE-BUILD)

### 3.1 Syntax Check
Run a syntax check (`python3 -m py_compile`) on all `.py` files to catch syntax errors that would break the GUI on boot. If Python is not available on the build host, create a verification script that performs this check on the Debian target.

### 3.2 Hook Ordering
Verify `iso/config/hooks/live/` contains hooks numbered `050` through `099`. Ensure `050-hardware-shield.hook.chroot` comes *before* `095-os-harden.hook.chroot`.

**Required hook sequence:**
```
050-hardware-shield.hook.chroot  ← Kernel module compilation
060-kernel-module.hook.chroot    ← DKMS registration
070-camoufox-fetch.hook.chroot   ← Browser binary + pip packages
080-ollama-setup.hook.chroot     ← AI/ML dependencies
090-kyc-setup.hook.chroot        ← KYC module setup
095-os-harden.hook.chroot        ← Firewall, DNS, blacklist, locale
 99-fix-perms.hook.chroot        ← Final permissions + pip fallback
```

### 3.3 Kernel Config
Verify `iso/auto/config` contains `bootappend live` parameters including:

| Parameter | Required | Purpose |
|-----------|----------|---------|
| `mitigations=off` | **YES** | Sub-200ms cognitive latency |
| `apparmor=1` | **YES** | Mandatory access control |
| `security=apparmor` | **YES** | AppArmor as Linux Security Module |
| `ipv6.disable=1` | **YES** | Prevent IPv6 leaks |
| `persistence` | **YES** | Persistent storage support |
| `net.ifnames=0` | **YES** | Predictable interface names |

---

## PHASE 4: HARDENING VERIFICATION

### 4.1 Firewall
Ensure `etc/nftables.conf` is set to **default-deny on all 3 chains** (input, forward, output) with whitelist for xray, local DNS, SOCKS, TLS.

### 4.2 Kernel Blacklist
Verify `095-os-harden.hook.chroot` blacklists:
- `uvcvideo` (real webcam — replaced by v4l2loopback)
- `bluetooth` (btusb, btrtl, btbcm, btintel)
- `firewire-core`, `thunderbolt` (DMA attack vectors)
- Unused network protocols (dccp, sctp, rds, tipc)

### 4.3 Font Masking
Verify `etc/fonts/local.conf` exists and rejects Linux discovery fonts:
- DejaVu, Liberation, Noto, Droid, Ubuntu
- Substitutes with Windows equivalents (Arial, Times New Roman, Courier New)

### 4.4 Audio Masking
Verify `etc/pulse/daemon.conf` sets 44100Hz sample rate and 5ms fragment size to match Windows CoreAudio signature.

### 4.5 Ring 0 ↔ Ring 3 Synchronization
Verify `core/fingerprint_injector.py` contains `NetlinkHWBridge` class using `NETLINK_TITAN = 31` to communicate with `hardware_shield_v6.c`.

### 4.6 Audio Jitter Seed
Verify `core/audio_hardener.py` derives a deterministic jitter seed from `profile_uuid` via SHA-256.

### 4.7 Entropy
Confirm `rng-tools5` and `haveged` are in the package list to prevent GPG/TLS entropy depletion.

---

## OUTPUT DELIVERABLE

Generate a report file `FINAL_PREFLIGHT_CHECK.md` summarizing:
- Files analyzed and their status
- Files fixed (with before/after description)
- Dependencies added
- Security verification results
- Confirmation of **"Ready for Build"** status

---

## EXECUTION NOTES

- **Do NOT revert Debian mirrors** — `deb.debian.org` is required for `v4l2loopback-dkms` headers
- **Do NOT replace XFCE4 with GNOME** — XFCE has smaller fingerprint surface
- **Do NOT set `LB_MODE` to `ubuntu`** — must remain `debian`
- All `etc/` paths are relative to `iso/config/includes.chroot/`
- The `auto/config` script runs `lb config` with all parameters
