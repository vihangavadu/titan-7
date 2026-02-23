# TITAN OS — Pre-Operation Readiness Plan

## Overview
This document defines the complete verification pipeline that must pass before any real-world operation. It covers 10 verification phases across OS-level forensics, browser profile integrity, network anonymity, AI model readiness, and end-to-end dry runs.

---

## Phase 1: AI Model Deployment & Validation
**Goal**: Confirm all 3 V9 LoRA-tuned models are loaded, responding correctly, and routed properly.

| Check | Tool | Pass Criteria |
|-------|------|---------------|
| Ollama service running | `systemctl status ollama` | active (running) |
| 3 base models loaded | `ollama list` | qwen2.5:7b, deepseek-r1:8b, mistral:7b |
| LoRA adapters applied | Check `/opt/titan/training/models_v9/` | 3 adapter dirs present |
| Task routing config | `llm_config.json` | 57 task routes, 9 apps mapped |
| AI response quality | Query each model with sample task | Valid JSON, CoT reasoning, <10s latency |
| Model assignment accuracy | Test 5 tasks per model | Correct model handles correct task type |

**Script**: `titan_preflight.py --phase ai`

---

## Phase 2: OS-Level Forensic Sweep
**Goal**: Ensure the OS leaves zero forensic traces that identify it as Titan or a VM.

| Check | What It Detects | Pass Criteria |
|-------|-----------------|---------------|
| Hostname | Generic VM/Titan hostname | Looks like real consumer PC |
| DMI/SMBIOS | VirtualBox/QEMU/VMware strings | Real hardware vendor strings |
| CPUID/RDTSC | Hypervisor bit, timing anomalies | No hypervisor detected |
| MAC address | VM vendor OUI (08:00:27, 52:54:00) | Real NIC vendor OUI |
| Kernel modules | vboxguest, vmw_balloon, virtio | No VM kernel modules loaded |
| Process list | VBoxService, vmtoolsd, qemu-ga | No VM management processes |
| Filesystem artifacts | /opt/titan visible, .titan files | Titan dirs hidden/encrypted |
| /proc leaks | /proc/scsi/scsi shows VBOX HARDDISK | Real disk vendor |
| Systemd services | titan-*.service visible | Services disguised or hidden |
| Installed packages | dpkg -l shows titan-* | No titan packages in dpkg |
| Log files | /var/log contains titan references | Logs sanitized |
| Bash history | Commands reveal titan usage | History cleaned |
| Cron jobs | Titan scheduled tasks visible | Cron sanitized |
| DNS leaks | resolv.conf points to real DNS | VPN DNS only |
| Timezone consistency | System TZ matches profile TZ | Aligned |

**Script**: `titan_preflight.py --phase os`

---

## Phase 3: Network & VPN Verification
**Goal**: Confirm network anonymity with zero leaks.

| Check | What It Detects | Pass Criteria |
|-------|-----------------|---------------|
| VPN connected | Mullvad/WireGuard active | Connected, IP changed |
| IP geolocation | IP matches target region | Correct country/city |
| DNS leak test | DNS queries bypass VPN | All DNS through VPN tunnel |
| WebRTC leak | Local IP exposed via WebRTC | WebRTC disabled or proxied |
| IPv6 leak | IPv6 bypasses VPN tunnel | IPv6 disabled |
| Xray/proxy chain | SOCKS5/HTTP proxy working | Proxy responds, IP matches |
| MTU/TTL | TTL=64 (Linux) vs TTL=128 (Windows) | Matches spoofed OS |
| ASN reputation | IP on known VPN/datacenter ASN | Residential or clean ASN |
| Tor detection | IP flagged as Tor exit node | Not a Tor exit |
| Port scan exposure | Open ports reveal services | No unexpected open ports |

**Script**: `titan_preflight.py --phase network`

---

## Phase 4: Browser Profile Forensics
**Goal**: Profile passes all antifraud forensic analysis (Riskified, SEON, Forter, Adyen).

| Check | What It Detects | Pass Criteria |
|-------|-----------------|---------------|
| Profile structure | Missing/extra Firefox files | All standard files present, no artifacts |
| Profile age | Created <60 days ago | Age ≥60 days |
| Profile size | <400MB total | Size ≥400MB |
| History count | <1000 URLs | ≥1000 URLs with diverse domains |
| Visit type distribution | 100% link visits (type=1) | Mix of link/typed/bookmark visits |
| Temporal coverage | All visits same day | Visits spread across 60+ days |
| Circadian pattern | Visits at 3AM | <15% night visits (midnight-5AM) |
| Cookie count & age | <50 cookies, all same timestamp | ≥50 cookies, spread across 30+ days |
| Trust anchor cookies | No Google/YouTube/GitHub cookies | Major platform cookies present |
| Commerce cookies | No Stripe/PayPal/Adyen cookies | Commerce cookies pre-seeded |
| LocalStorage keys | Synthetic padding patterns (_c_*, pad_*) | Real-looking key names |
| IndexedDB | Empty | ≥1 IDB database |
| Form history | Only persona fields | Mix of persona + search + misc fields |
| Session store | 1 tab, no closed tabs | Multiple tabs, closed tabs present |
| URL diversity | All root-only URLs (domain.com/) | Deep paths (domain.com/path/page) |
| GUID format | Hex-only GUIDs | Base64url GUIDs (Firefox native) |
| url_hash values | All zeros | Computed hashes |
| frecency scores | All -1 | Computed frecency |
| from_visit chains | No referral chains | ≥10% visits have referrers |
| Bookmark count | Zero bookmarks | ≥1 bookmark |

**Script**: `titan_preflight.py --phase profile`

---

## Phase 5: Fingerprint Coherence
**Goal**: All browser fingerprint signals are internally consistent and match the spoofed identity.

| Check | What It Detects | Pass Criteria |
|-------|-----------------|---------------|
| Canvas hash | Unique per-session, not blocklisted | Stable, realistic hash |
| WebGL renderer | Mismatched GPU string | Matches spoofed hardware |
| Audio fingerprint | Default/missing audio context | Realistic audio hash |
| Font enumeration | Missing system fonts for claimed OS | Fonts match claimed OS |
| Screen resolution | Uncommon resolution | Common resolution for claimed device |
| User-Agent | UA doesn't match navigator properties | UA ↔ navigator ↔ platform aligned |
| Platform string | navigator.platform mismatch | Matches claimed OS |
| Language/locale | Accept-Language doesn't match timezone | Language ↔ TZ ↔ geo aligned |
| Hardware concurrency | Unusual core count | Realistic for claimed device |
| Device memory | Missing or unusual value | 4/8/16 GB (common values) |
| Touch support | Touch on desktop or no-touch on mobile | Matches device type |
| JA4 fingerprint | Known bot/automation JA4 hash | Looks like real browser |
| TLS cipher suites | Non-browser cipher order | Matches target browser version |

**Script**: `titan_preflight.py --phase fingerprint`

---

## Phase 6: Identity & Persona Consistency
**Goal**: All persona fields are internally consistent and pass cross-validation.

| Check | What It Detects | Pass Criteria |
|-------|-----------------|---------------|
| Name ↔ Email | Email doesn't match name | Plausible correlation |
| Phone ↔ Region | Phone country code ≠ billing country | Aligned |
| Address ↔ ZIP | ZIP doesn't match city/state | Valid ZIP for city |
| Card BIN ↔ Country | BIN country ≠ billing country | Aligned or plausible |
| Card BIN ↔ Bank | Bank name doesn't match BIN | Correct issuer |
| Email age | Email created today | Email appears established |
| Email provider | Disposable email domain | Major provider (Gmail, Outlook) |
| Social presence | No social profiles linked to email | At least 1 social signal |
| IP ↔ Billing | IP country ≠ billing country | Same country or plausible travel |
| Timezone ↔ IP | TZ offset doesn't match IP geo | Aligned |

**Script**: `titan_preflight.py --phase identity`

---

## Phase 7: Service Health
**Goal**: All backend services are running and responsive.

| Service | Check | Pass Criteria |
|---------|-------|---------------|
| Redis | `redis-cli ping` | PONG |
| Ollama | `curl localhost:11434/api/tags` | 200 OK, 3 models |
| Xray | `systemctl status xray` | active |
| Mullvad | `mullvad status` | Connected |
| ntfy | `curl localhost:8090/health` | 200 OK |
| Camoufox | Binary exists, launches | `/opt/camoufox/camoufox` executable |
| titan_api | `curl localhost:5000/health` | 200 OK, all endpoints |
| Ghost Motor | Import test | Module loads without error |
| Kill Switch | Import test | Module loads, armed |

**Script**: `titan_preflight.py --phase services`

---

## Phase 8: Behavioral Simulation Dry Run
**Goal**: End-to-end simulation without real payment to verify all systems work together.

| Step | What It Tests | Pass Criteria |
|------|---------------|---------------|
| Profile load | Camoufox launches with profile | Browser opens, no errors |
| Ghost Motor activation | Mouse/keyboard simulation starts | Realistic movement patterns |
| Navigation warmup | Browse 3-5 sites before target | History/cookies accumulate |
| Target navigation | Navigate to target site | Page loads, no blocks |
| Form fill simulation | Autofill persona data | Fields populated correctly |
| 3DS readiness | 3DS strategy module responds | Strategy generated |
| Session rhythm | Timing between actions | Realistic delays (not instant) |
| Detection check mid-session | Run forensic monitor during browse | No new anomalies |
| Abort test | Trigger kill switch | Clean shutdown, traces wiped |

**Script**: `titan_preflight.py --phase dryrun`

---

## Phase 9: AI-Powered Deep Analysis
**Goal**: Use the trained AI models themselves to analyze the entire setup and find issues humans miss.

| AI Task | Model | What It Does |
|---------|-------|--------------|
| `profile_optimization` | titan-analyst | Analyze profile and suggest improvements |
| `persona_consistency_check` | titan-analyst | Cross-validate all persona fields |
| `detection_prediction` | titan-fast | Predict which antifraud systems will flag us |
| `first_session_warmup_plan` | titan-strategist | Generate optimal warmup sequence |
| `card_target_matching` | titan-analyst | Score card-target compatibility |
| `issuer_behavior_prediction` | titan-strategist | Predict issuer response |
| `tls_profile_selection` | titan-analyst | Verify TLS profile matches browser |

**Script**: `titan_preflight.py --phase ai-analysis`

---

## Phase 10: Final GO/NO-GO Scorecard
**Goal**: Aggregate all results into a single pass/fail decision.

| Category | Weight | Threshold |
|----------|--------|-----------|
| OS Forensics | 20% | 0 FAIL, ≤2 WARN |
| Network/VPN | 15% | 0 FAIL, 0 WARN |
| Browser Profile | 25% | 0 FAIL, ≤3 ANOM |
| Fingerprint | 15% | 0 FAIL, 0 ANOM |
| Identity | 10% | 0 FAIL, ≤1 WARN |
| Services | 10% | All running |
| AI Analysis | 5% | No critical flags |

**Verdict**:
- **GREEN (GO)**: All categories pass → proceed with operation
- **YELLOW (CAUTION)**: Minor warnings → proceed with extra monitoring
- **RED (NO-GO)**: Any FAIL or >threshold → fix before proceeding

---

## Execution Order

```
# Full preflight (runs all 10 phases)
python3 /opt/titan/core/titan_preflight.py --full

# Individual phases
python3 /opt/titan/core/titan_preflight.py --phase ai
python3 /opt/titan/core/titan_preflight.py --phase os
python3 /opt/titan/core/titan_preflight.py --phase network
python3 /opt/titan/core/titan_preflight.py --phase profile
python3 /opt/titan/core/titan_preflight.py --phase fingerprint
python3 /opt/titan/core/titan_preflight.py --phase identity
python3 /opt/titan/core/titan_preflight.py --phase services
python3 /opt/titan/core/titan_preflight.py --phase dryrun
python3 /opt/titan/core/titan_preflight.py --phase ai-analysis
python3 /opt/titan/core/titan_preflight.py --phase scorecard

# Quick check (phases 2,3,7 only — 30 seconds)
python3 /opt/titan/core/titan_preflight.py --quick
```

---

## Post-Training Deployment Steps

1. Download LoRA models from Vast.ai instances
2. Merge LoRA adapters into base Ollama models
3. Deploy merged models to VPS Ollama
4. Run `--phase ai` to validate model quality
5. Run `--full` preflight
6. Fix any FAIL/ANOM items
7. Re-run until GREEN
8. Begin operation
