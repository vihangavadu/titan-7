# VPS Cross-Reference Analysis — Titan OS V8.1

**Date:** Feb 23, 2026
**VPS ID:** 1400969
**VPS IP:** 72.62.72.48 (IPv4) / 2a02:4780:5e:2caf::1 (IPv6)
**Plan:** KVM 8 (8 CPU, 32GB RAM, 400GB SSD, 32TB bandwidth)
**OS:** Debian 12
**State:** Running
**Datacenter:** ID 21
**Created:** Feb 19, 2026

---

## VPS Action Timeline

| Date | Actions | Notes |
|------|---------|-------|
| Feb 19 | VPS created, initial setup | Debian 12, Titan deployed |
| Feb 20 06:16-09:09 | **7 recovery cycles** | eBPF XDP lockout — tcp_fingerprint.c rewrote ALL packets including SSH |
| Feb 20 10:25 | Restart | Post-recovery stabilization |
| Feb 20 10:53-19:16 | **3 snapshots created** | Backup after fixes |
| Feb 21 05:40 | Restart | Applied patches |
| Feb 21 13:03-14:19 | Limits set (2x) | Resource adjustments |
| Feb 21 14:58-15:00 | SSH keys refreshed (2x) | New SSH key deployed |
| Feb 21 23:34 | Root password reset | Security update |

**Total actions:** 40

---

## Module Comparison

### Counts
| Location | Python Modules | Non-Python | Total |
|----------|---------------|------------|-------|
| **VPS** (`/opt/titan/core/`) | 86 | 7 (.c, .sh, Makefile) | 93 |
| **Local** (`src/core/`) | 94 | 7 (.c, .sh, Makefile) | 101 |
| **Diff** | **+8 local-only** | 0 | +8 |

### 8 Modules LOCAL-ONLY (need deployment to VPS)

| Module | Size | Origin | Function |
|--------|------|--------|----------|
| `chromium_cookie_engine.py` | 49KB | Cookie-main | Chrome V10/V11 cookie encryption (DPAPI, AES-GCM) |
| `cookie_forge.py` | 26KB | Cookie-main | Multi-browser cookie/history/localStorage injection |
| `ga_triangulation.py` | 18KB | vehicle-main | Google Analytics GAMP server-side event triangulation |
| `journey_simulator.py` | 10KB | vehicle-main | Playwright-driven multi-site browsing journeys |
| `profile_burner.py` | 8KB | vehicle-main | Browser-driven profile aging (real Camoufox visits) |
| `profile_isolation.py` | 17KB | titan/ (V5) | Linux namespace/cgroup process isolation |
| `temporal_entropy.py` | 8KB | vehicle-main | Poisson-distribution temporal entropy generator |
| `time_dilator.py` | 7KB | vehicle-main | Firefox places.sqlite backdated history injection |

### 0 Modules VPS-ONLY
All VPS modules are present in the local codebase.

---

## VPS Security Status

| Check | Status | Action Needed |
|-------|--------|---------------|
| Firewall | **NONE configured** | Create via hPanel with SSH/RDP/7700/51820 rules |
| SSH Keys | Configured (refreshed Feb 21) | OK |
| Root Password | Reset Feb 21 | OK |
| Snapshot | Feb 20, expires Mar 12 | Create fresh snapshot after sync |
| Backups | **None** | Enable automatic backups in hPanel |
| PTR Record | Default (srv1400969.hstgr.cloud) | OK for now |
| Recovery | Available | Used 7x during eBPF incident, working |

---

## Sync Plan

To bring the VPS up to date with the local V8.1 codebase:

```bash
# SSH into VPS
ssh root@72.62.72.48

# Backup current state
cd /opt/titan
tar czf /root/titan-backup-$(date +%Y%m%d).tar.gz core/ apps/

# Pull latest from GitHub
cd /opt/titan
git pull origin main

# Or if not a git repo on VPS, sync from local:
# Option A: rsync from local machine
# rsync -avz --delete src/core/ root@72.62.72.48:/opt/titan/core/
# rsync -avz --delete src/apps/ root@72.62.72.48:/opt/titan/apps/

# Option B: Clone fresh
# cd /opt && rm -rf titan && git clone https://github.com/malithwishwa02-dot/titan-7.git titan
# cd titan && ln -s src/core core  # Maintain /opt/titan/core/ path compatibility

# Verify sync
ls /opt/titan/core/*.py | wc -l  # Should be 94
python3 -c "import sys; sys.path.insert(0,'/opt/titan/core'); from __init__ import *; print('OK')"

# Restart services
python3 /opt/titan/core/titan_services.py restart
```

---

## Files Changed Since Last VPS Sync

### New Modules (8)
All rewritten for V8.1 compatibility (Playwright, Camoufox, Firefox, optional deps):
- `temporal_entropy.py` — numpy/scipy optional, pure-Python Poisson fallback
- `time_dilator.py` — targets Firefox places.sqlite (not Chrome History)
- `profile_burner.py` — uses Playwright + Camoufox (not Selenium + Chrome)
- `journey_simulator.py` — 5 journey templates, Playwright-driven
- `ga_triangulation.py` — requests optional, curl_cffi for TLS mimicking
- `chromium_cookie_engine.py` — win32crypt optional (works on Linux)
- `cookie_forge.py` — Chrome + Firefox dual-browser support
- `profile_isolation.py` — Linux namespace/cgroup isolation

### Modified Files
- `src/core/__init__.py` — 8 new module imports + __all__ exports
- `src/apps/titan_operations.py` — 6 new module imports in FORGE tab
- `src/apps/titan_admin.py` — Detection Lab + Profile Isolation imports
- `src/apps/titan_launcher.py` — Bug Reporter added as 6th app card
- `.gitignore` — Added .windsurf/ (MCP token protection)

### New Supporting Files
- `hostinger-dev/` — 6 files (API reference, MCP setup, VPS client, workflow)
- `docs/operational-playbook/13_VERSION_COMPARISON.md`
- `docs/MODULE_CERBERUS_DEEP_DIVE.md`
- `docs/MODULE_GENESIS_DEEP_DIVE.md`
- `scripts/OPERATION_EXECUTION.py`
- `scripts/OPERATION_EXECUTION_SIMPLIFIED.py`
- `src/apps/validation_dashboard.html`
- `src/apps/app_bug_reporter.py`
- `src/lib/tcp_fingerprint.c`
- `src/lib/network_shield_original.c`
- `src/lib/xdp_loader.c`
