# LUCID TITAN V7.0.3 SINGULARITY — Complete User Manual

**Version:** 7.0.3 | **Last Updated:** 2026-02-14 | **Platform:** Debian 12 Live ISO  
**Purpose:** Step-by-step operational guide for every feature in the system.

---

## TABLE OF CONTENTS

1. [System Requirements](#1-system-requirements)
2. [Deployment Methods](#2-deployment-methods)
3. [First Boot Configuration](#3-first-boot-configuration)
4. [GUI Overview — 7 Tabs](#4-gui-overview)
5. [Tab 1: OPERATION — Profile Forge & Launch](#5-operation-tab)
6. [Tab 2: INTELLIGENCE — Target & AVS Intel](#6-intelligence-tab)
7. [Tab 3: SHIELDS — Hardening & Kill Switch](#7-shields-tab)
8. [Tab 4: KYC — Virtual Camera](#8-kyc-tab)
9. [Tab 5: HEALTH — System Monitor](#9-health-tab)
10. [Tab 6: TX MONITOR — Transaction Capture](#10-tx-monitor-tab)
11. [Tab 7: DISCOVERY — Targets, 3DS Bypass, Non-VBV BINs](#11-discovery-tab)
12. [Background Services](#12-background-services)
13. [titan.env Configuration Reference](#13-titanenv-reference)
14. [API Reference](#14-api-reference)
15. [Operational Workflow — Step by Step](#15-operational-workflow)
16. [Troubleshooting](#16-troubleshooting)
17. [Appendix A: Non-VBV BIN Countries](#appendix-a)
18. [Appendix B: Decline Code Reference](#appendix-b)
19. [Appendix C: 3DS Bypass Techniques](#appendix-c)

---

## 1. System Requirements

### Hardware (Minimum)
| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **CPU** | 64-bit x86_64, 2 cores | 4+ cores |
| **RAM** | 4 GB | 8+ GB |
| **Storage** | 8 GB USB / 15 GB disk | 32+ GB |
| **Network** | Ethernet or WiFi | Ethernet (lower latency) |
| **GPU** | Not required | Any (for KYC neural reenactment) |

### Software (Pre-installed in ISO)
- Debian 12 Bookworm (kernel 6.1+)
- Python 3.11+ with PyQt6
- Camoufox browser (Firefox-based)
- Xray-core (VLESS+Reality VPN)
- v4l2loopback (virtual camera)
- eBPF/XDP (network stack)

### Network Requirements
| Service | Port | Direction | Purpose |
|---------|------|-----------|---------|
| HTTPS | 443 | Outbound | All browsing + VPN |
| DNS-over-TLS | 853 | Outbound | Encrypted DNS |
| SOCKS5 | 1080-9050 | Localhost | Proxy tunnel |
| TX Monitor | 7443 | Localhost | Transaction capture |
| Tailscale | 41641 | Outbound | VPN mesh (optional) |

---

## 2. Deployment Methods

### Method A: Live USB Boot (Recommended)

No installation required. System runs entirely from USB in RAM.

```bash
# On any Linux/Mac/Windows machine:

# 1. Download the ISO
# File: lucid-titan-v7.0.3-singularity.iso

# 2. Write to USB (Linux/Mac)
sudo dd if=lucid-titan-v7.0.3-singularity.iso of=/dev/sdX bs=4M status=progress
sync

# 3. Write to USB (Windows)
# Use Rufus (rufus.ie) or balenaEtcher:
#   - Select ISO file
#   - Select USB drive
#   - Click Write
#   - Boot from USB in BIOS

# 4. Boot
# Insert USB → Restart → Enter BIOS (F2/F12/DEL) → Boot from USB
# System boots to desktop in ~30 seconds
```

**Advantages:** Zero trace on host machine. All data in RAM. Pull USB = everything gone.

### Method B: Install to Disk (VPS/Dedicated)

For persistent installations on VPS or dedicated hardware.

```bash
# After booting from Live USB:
sudo /opt/titan/bin/install-to-disk

# Follow prompts:
#   1. Select target disk (WARNING: will format)
#   2. Set hostname
#   3. Configure user password
#   4. Wait for installation (~5 minutes)
#   5. Reboot and remove USB
```

### Method C: Virtual Machine

```bash
# Create VM with:
#   - 4+ GB RAM
#   - 20+ GB disk
#   - EFI boot enabled
#   - Network: NAT or Bridged
# Mount ISO as CD/DVD → Boot
```

---

## 3. First Boot Configuration

On first boot, `titan-first-boot` runs automatically and performs 11 checks:

| # | Check | What It Does |
|---|-------|-------------|
| 1 | Kernel module | Loads titan_hw.ko (hardware fingerprint spoof) |
| 2 | eBPF shield | Attaches XDP to network interface (TCP stack rewrite) |
| 3 | DNS resolver | Configures Unbound (DNS-over-TLS via Cloudflare + Quad9) |
| 4 | Firewall | Loads nftables default-deny rules |
| 5 | Font shield | Verifies Linux fonts are rejected, Windows fonts available |
| 6 | Audio config | Sets PulseAudio to 44100Hz (Windows CoreAudio match) |
| 7 | MAC randomization | Randomizes network MAC address |
| 8 | Journal privacy | Confirms volatile-only logging (no disk writes) |
| 9 | Coredump disabled | Confirms core dumps are suppressed |
| 10 | Timezone | Sets to UTC (will be overridden per-operation) |
| 11 | Directory structure | Creates all required data directories |

### Post-Boot Setup

After first boot, configure your operator settings:

```bash
# 1. Open the configuration file
nano /opt/titan/config/titan.env

# 2. Set your proxy (REQUIRED — Section 2 in the file)
# Option A: Provider credentials
TITAN_PROXY_PROVIDER=brightdata
TITAN_PROXY_USERNAME=your_username
TITAN_PROXY_PASSWORD=your_password

# Option B: Custom proxy pool
# Edit /opt/titan/state/proxies.json with your proxy list

# 3. (Optional) Set up VPN
# Run the VPN setup wizard:
/opt/titan/bin/titan-vpn-setup

# 4. Launch the GUI
python3 /opt/titan/apps/app_unified.py
# Or use the launcher:
/opt/titan/bin/titan-launcher
```

---

## 4. GUI Overview

The Unified Operation Center has **7 tabs**:

| Tab | Purpose | Key Actions |
|-----|---------|-------------|
| **OPERATION** | Main workflow: target → proxy → card → persona → forge → launch | Profile creation + browser launch |
| **INTELLIGENCE** | AVS intel, Visa Alerts, card freshness, fingerprint tools, PayPal defense, 3DS v2, proxy intel, target database | Intelligence lookup |
| **SHIELDS** | Pre-flight verification, environment hardening (fonts/audio/timezone), kill switch, OSINT verification, purchase history injection | System hardening |
| **KYC** | Virtual camera controller for identity verification bypass | Document + liveness feed |
| **HEALTH** | System resource monitor, privacy service status, network connectivity | Real-time HUD |
| **TX MONITOR** | 24/7 transaction capture, decline code decoder, per-site/BIN analytics | Transaction analysis |
| **DISCOVERY** | Auto-discovery, 3DS bypass scoring, Non-VBV BIN recommendations, background services | Target finding |

---

## 5. OPERATION Tab

This is the main workflow tab. Follow steps top to bottom.

### Step 1: Target Configuration
- Select target from dropdown (14+ presets: Eneba, G2A, Amazon, Steam, etc.)
- System auto-loads recommended profile age, archetype, and hardware settings

### Step 2: Network Configuration
- **Proxy mode:** Enter SOCKS5 proxy URL → click "Test Proxy"
- **VPN mode:** Click "Connect VPN" (requires prior VPN setup)
- Status shows: IP, geolocation, latency

### Step 3: Card Details
- Enter card number, expiry (MM/YY), CVV, cardholder name
- Click "Validate Card" → Cerberus validates (BIN lookup + AVS + 3DS risk)
- Result: GREEN (live) / YELLOW (risky) / RED (dead)

### Step 4: Persona Details
- Full name, email, phone, address, city, state, ZIP
- Must match card billing address for AVS pass

### Step 5: Profile Options
- **Profile Age:** 30-365 days (default: 90)
- **Storage Size:** 100-1000 MB (default: 500)
- **Archetype:** Student Developer / Professional / Gamer / Casual / Retiree
- **Hardware:** MacBook Pro M2 / Windows Desktop / Gaming / Laptop / Linux

### Step 6: Forge & Launch
1. Click **FORGE PROFILE** → generates 400MB+ aged browser profile
2. Click **LAUNCH BROWSER** → opens Camoufox with all shields active

---

## 6. INTELLIGENCE Tab

Sub-tabs (left sidebar):

### AVS
- Enter card country code → Check AVS → shows enforcement rules per country

### Visa Alerts
- Check if card is enrolled in Visa Purchase Alerts (push notification risk)

### Card Fresh
- Score card freshness: has it been checked before? declined? used elsewhere?

### Fingerprint
- Verification tools and workflow to confirm fingerprint consistency

### PayPal
- PayPal 3-pillar defense analysis and evasion strategies

### 3DS v2
- 3DS 2.0 intelligence: who triggers 3DS, biometric threats, frictionless flow tips

### Proxy/DNS
- Proxy type recommendations, DNS leak prevention, IP reputation check URLs

### Targets
- Browse 29-target intelligence database with fraud engine, PSP, 3DS rate per target

---

## 7. SHIELDS Tab

### Pre-Flight
- **Run Master Verify:** 4-layer check (Kernel → Network → Environment → Identity)
- **Deep Identity Check:** Detects font/audio/timezone leaks

### Environment
- **Font Purge:** Rejects Linux fonts, injects Windows equivalents
- **Audio Harden:** Sets 44100Hz, injects noise profile
- **Timezone Sync:** Kills browsers → sets timezone → NTP sync

### Kill Switch
- **ARM:** Monitors fraud_score.json every 500ms
- **PANIC:** Kills browsers, flushes hardware ID, clears session, rotates proxy, randomizes MAC
- **Threshold:** Configurable (default: 85)

### OSINT / Quality
- **OSINT Verify:** 7-step verification of cardholder identity
- **Grade Card:** BIN quality grading (PREMIUM / DEGRADED / LOW)

### Purchase History
- Inject 1-24 months of realistic purchase records into browser profile

---

## 8. KYC Tab

Virtual camera controller for identity verification bypass.

### Usage
1. Click **Load Image** → select face photo (JPG/PNG)
2. Select motion type: Natural Blink, Gentle Smile, Head Turn, Nod, etc.
3. Adjust parameters: Head Rotation, Expression Intensity, Blink Frequency
4. Enable **Integrity Shield** (hides virtual camera from detection)
5. Click **START STREAM** → virtual camera begins streaming
6. Open target KYC flow in browser → camera shows your stream
7. Click **STOP** when done

### Supported Providers
Jumio, Onfido, Veriff, Sumsub, Persona, Stripe Identity, Plaid IDV, Au10tix

---

## 9. HEALTH Tab

Real-time system monitor (auto-refreshes every 5 seconds):

- **CPU Load:** Usage percentage with bar graph
- **Memory:** Used / Total MB
- **Overlay (tmpfs):** Disk usage for live system

### Privacy Services Status
| Service | What It Checks |
|---------|---------------|
| Kernel Hardware Shield | `/sys/module/titan_hw` exists |
| eBPF Network Shield | `/sys/fs/bpf/titan_xdp` exists |
| DNS Resolver (Unbound) | systemctl is-active unbound |
| Tor Service | systemctl is-active tor |
| Lucid VPN | xray process running |
| PulseAudio | pactl info succeeds |

---

## 10. TX MONITOR Tab

24/7 transaction capture — records every purchase attempt.

### Live Statistics
- **Total / Approved / Declined / Rate** — auto-refreshes every 10 seconds

### Decline Code Decoder
1. Enter any decline code (e.g., `do_not_honor`, `51`, `fraudulent`)
2. Select PSP or leave Auto-detect
3. Click **DECODE** → shows:
   - Severity (CRITICAL / HIGH / MEDIUM / LOW)
   - Human-readable reason
   - Recommended action

### Transaction Feed
Click **REFRESH** to load recent transactions (last 24h, max 50)

### Analytics
- **SITE STATS:** Per-site success rates with visual bars
- **BIN STATS:** Per-BIN success rates with visual bars

### How It Works
The TX Monitor browser extension (installed in Camoufox) hooks into `fetch()` and `XMLHttpRequest` to capture payment API responses from Stripe, Adyen, Braintree, Shopify, Authorize.net, and 5 other PSPs. Data is sent to `localhost:7443` where the Python backend decodes, stores, and analyzes.

---

## 11. DISCOVERY Tab

### Discovery Sub-Tab
- **RUN DISCOVERY NOW:** Immediate Google dorking scan for new easy targets
- **DB STATS:** View target database statistics (total sites, by category, by PSP)
- **EASY 2D SITES:** Browse all sites with no 3DS enforcement
- **SHOPIFY STORES:** Browse Shopify stores (usually easiest targets)

Auto-discovery runs daily at 3 AM UTC (configurable in titan.env).

### 3DS Bypass Sub-Tab
Score any site's 3DS bypass potential:

1. Enter domain, select PSP, card country, amount
2. **SCORE SITE** → bypass score 0-100 (EASY / MODERATE / HARD / VERY HARD)
3. **BYPASS PLAN** → step-by-step plan (pre-check → amount optimization → frictionless → downgrade → timeout → PSD2)
4. **DOWNGRADE ATTACKS** → view all 3DS 2.0→1.0 downgrade techniques
5. **PSD2 EXPLOITS** → EU-specific exemption exploitation guide

### Non-VBV BINs Sub-Tab
Browse and get recommendations from the Non-VBV BIN database:

1. Select country (28 available)
2. Optionally enter target merchant
3. **GET RECOMMENDATIONS** → BINs sorted by lowest 3DS rate
4. **ALL BINs** → browse entire database (100+ BINs)
5. **EASY COUNTRIES** → country difficulty ranking

### Services Sub-Tab
Manage background services:
- **START ALL SERVICES** — TX Monitor + Daily Discovery + Feedback Loop
- **CHECK STATUS** — JSON status of all services
- **UPDATE FEEDBACK** — Force feedback loop to update site/BIN scores from TX data
- **BEST SITES** — Sites with highest real success rates from your TX history

---

## 12. Background Services

Three services run automatically in the background:

| Service | What It Does | Interval |
|---------|-------------|----------|
| **TX Monitor** | Captures payment responses via browser extension → SQLite DB | Real-time (port 7443) |
| **Daily Discovery** | Google dorking → probe → classify → add to DB | Once per day (3 AM UTC) |
| **Feedback Loop** | TX decline data → update site/BIN scores | Every 30 minutes |

All services auto-start when GUI launches. Configure in titan.env:
```
TITAN_TX_MONITOR_AUTOSTART=1
TITAN_DISCOVERY_AUTOSTART=1
TITAN_FEEDBACK_AUTOSTART=1
```

---

## 13. titan.env Configuration Reference

Location: `/opt/titan/config/titan.env`

| Section | Status | Variables | Purpose |
|---------|--------|-----------|---------|
| Cloud Brain | [OPTIONAL] | TITAN_CLOUD_URL, TITAN_API_KEY | vLLM AI server |
| Proxy | [REQUIRED] | TITAN_PROXY_PROVIDER, _USERNAME, _PASSWORD | Residential proxy |
| VPN | [OPTIONAL] | TITAN_VPN_SERVER_IP, _UUID, _PUBLIC_KEY, etc. | VLESS+Reality VPN |
| Payment PSPs | [OPTIONAL] | TITAN_STRIPE_SECRET_KEY, TITAN_PAYPAL_*, etc. | Silent card validation |
| eBPF | [AUTO] | TITAN_EBPF_ENABLED | Network shield |
| Hardware | [AUTO] | TITAN_HW_SHIELD_ENABLED | Hardware fingerprint |
| TX Monitor | [AUTO] | TITAN_TX_MONITOR_PORT (7443) | Transaction capture |
| Discovery | [AUTO] | TITAN_DISCOVERY_RUN_HOUR (3) | Daily target finding |
| Feedback | [AUTO] | TITAN_FEEDBACK_AUTOSTART (1) | TX data → scoring |

**[AUTO]** = Works without configuration  
**[REQUIRED]** = Must set before operating  
**[OPTIONAL]** = Enhanced functionality when configured

---

## 14. API Reference

### Quick Import Examples

```python
# Genesis — Profile Creation
from genesis_core import GenesisEngine, ProfileConfig
from advanced_profile_generator import AdvancedProfileGenerator

# Cerberus — Card Validation
from cerberus_core import CerberusValidator, CardAsset
from cerberus_enhanced import MaxDrainStrategy, generate_drain_plan

# Target Discovery
from target_discovery import TargetDiscovery, auto_discover, get_bypass_targets

# 3DS Bypass
from three_ds_strategy import get_3ds_bypass_score, get_3ds_bypass_plan, get_downgrade_attacks

# Non-VBV BINs
from three_ds_strategy import get_non_vbv_recommendations, get_easy_countries

# Transaction Monitor
from transaction_monitor import TransactionMonitor, decode_decline

# Services
from titan_services import start_all_services, get_services_status

# Intel Monitor
from intel_monitor import IntelMonitor, get_intel_feed
```

---

## 15. Operational Workflow — Step by Step

### Pre-Operation (Once)
1. Boot TITAN from USB
2. Edit `/opt/titan/config/titan.env` — set proxy credentials
3. Launch GUI: `python3 /opt/titan/apps/app_unified.py`
4. Go to DISCOVERY → Services → START ALL SERVICES

### Per-Operation Flow
1. **OPERATION tab** → Select target
2. Enter proxy URL → Test Proxy → confirm residential IP in correct geo
3. Enter card details → Validate Card → confirm GREEN
4. Enter persona (matching card billing address exactly)
5. FORGE PROFILE → wait for 400MB+ profile generation
6. SHIELDS tab → Run Master Verify → confirm all GREEN
7. OPERATION tab → LAUNCH BROWSER
8. In browser: navigate via warmup chain (Google → target)
9. Complete checkout manually (Ghost Motor augments your input)
10. After checkout → check TX MONITOR for result

### Post-Operation
1. TX MONITOR → verify captured response code
2. If declined → DECODE the decline code → follow recommended action
3. DISCOVERY → BEST SITES → check which sites have highest success rates
4. Kill Switch → DISARM when done

---

## 16. Troubleshooting

### Boot Issues
| Problem | Solution |
|---------|----------|
| USB won't boot | Enable EFI in BIOS, disable Secure Boot |
| Black screen after boot | Add `nomodeset` to GRUB kernel params |
| No network after boot | Check ethernet cable or WiFi driver |

### Proxy Issues
| Problem | Solution |
|---------|----------|
| Proxy test fails | Verify URL format: `socks5://user:pass@host:port` |
| Datacenter IP detected | Switch to residential proxy provider |
| Geo mismatch | Use proxy in same state as card billing address |

### Card Validation Issues
| Problem | Solution |
|---------|----------|
| Card shows DEAD | Card is expired, cancelled, or number is wrong |
| 3DS triggered | Use card from Non-VBV BINs list or lower amount |
| AVS mismatch | Match billing address exactly (use OSINT to verify) |

### Browser Issues
| Problem | Solution |
|---------|----------|
| Browser won't launch | Run `titan-first-boot` again to reload kernel modules |
| Fingerprint leak detected | Run Master Verify in SHIELDS tab |
| Ghost Motor not working | Check extension is loaded in about:addons |

### TX Monitor Issues
| Problem | Solution |
|---------|----------|
| No transactions captured | Verify TX Monitor extension is installed in Camoufox |
| Backend not responding | Check port 7443: `curl http://127.0.0.1:7443/api/heartbeat` |

### Service Issues
| Problem | Solution |
|---------|----------|
| Discovery returns no results | Check internet connection, Google may rate-limit |
| Feedback shows 0 updates | TX Monitor needs captured transactions first |
| Services won't start | Check logs: set TITAN_LOG_LEVEL=DEBUG in titan.env |

---

## Appendix A: Non-VBV BIN Countries

28 countries/regions with 100+ BINs:

| Country | Code | Difficulty | 3DS Rate | AVS | Best For |
|---------|------|-----------|----------|-----|----------|
| United States | US | Easy | 15% | Yes | Amazon, BestBuy, G2A |
| Japan | JP | Easy | 5% | No | G2A, Steam |
| Brazil | BR | Easy | 5% | No | G2A, Steam |
| Mexico | MX | Easy | 5-8% | No | G2A, Eneba |
| Canada | CA | Easy | 15-20% | Yes | Amazon.ca, G2A |
| Australia | AU | Easy | 10-12% | Yes | G2A, Steam |
| South Korea | KR | Easy | 5-6% | No | G2A, Steam |
| Singapore | SG | Easy | 8-10% | No | G2A, Steam |
| UAE | AE | Easy | 8-10% | No | G2A, Amazon.ae |
| South Africa | ZA | Easy | 8-10% | No | G2A, Steam |
| Germany | DE | Moderate | 20-30% | No | Amazon.de, G2A |
| France | FR | Moderate | 22-35% | No | Amazon.fr, G2A |
| United Kingdom | GB | Moderate | 30-40% | Yes | Amazon.co.uk |
| Netherlands | NL | Moderate | 30% | No | G2A, Bol.com |
| Poland | PL | Moderate | 25-28% | No | G2A, Allegro |

---

## Appendix B: Decline Code Quick Reference

### Critical (Card is burned — discard immediately)
| Code | PSP | Meaning |
|------|-----|---------|
| `stolen_card` | Stripe | Card reported stolen |
| `lost_card` | Stripe | Card reported lost |
| `pickup_card` | Stripe | Card flagged for retention |
| `fraudulent` | Stripe | Issuer flagged as fraud |
| `do_not_try_again` | Stripe | Permanently blocked |
| `22` | Adyen | Card reported lost/stolen |
| `41` / `43` | ISO | Lost / Stolen card |

### High (Switch card or wait)
| Code | PSP | Meaning |
|------|-----|---------|
| `do_not_honor` | Stripe | Generic bank decline |
| `card_velocity_exceeded` | Stripe | Too many attempts — wait 4-6h |
| `generic_decline` | Stripe | Try different amount/time |
| `merchant_blacklist` | Stripe | Stripe Radar blocked |
| `27` / `28` | Adyen | Do not honor / withdrawal limit |

### Medium (Fixable)
| Code | PSP | Meaning |
|------|-----|---------|
| `incorrect_cvc` | Stripe | Wrong CVV |
| `incorrect_zip` | Stripe | Wrong billing ZIP |
| `insufficient_funds` | Stripe | Lower the amount |
| `authentication_required` | Stripe | 3DS triggered |

---

## Appendix C: 3DS Bypass Techniques

| Technique | Success Rate | Risk | Works On |
|-----------|-------------|------|----------|
| 3DS 2.0→1.0 Protocol Downgrade | 65% | Medium | Stripe, Adyen, WorldPay |
| 3DS Method Iframe Corruption | 55% | Medium | Stripe, Adyen, Braintree |
| 3DS 1.0 Timeout → No Auth | 20% | Low | WorldPay, Auth.net |
| 3DS Version Mismatch | 40% | Low | Stripe, Adyen |
| PSD2 Low-Value (<30 EUR) | 90% | None | All EU merchants |
| PSD2 TRA Exemption (<500 EUR) | 70% | Low | Stripe, Adyen |
| Recurring/MIT Exemption | 85% | Low | Subscription services |

---

*End of TITAN V7.0.3 User Manual*
