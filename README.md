# LUCID EMPIRE — TITAN V8.1 SINGULARITY

### Full System Analysis & Developer Reference

[![Version](https://img.shields.io/badge/version-8.1--SINGULARITY-blue.svg)]()
[![License](https://img.shields.io/badge/license-GPL--3.0-green.svg)]()
[![Platform](https://img.shields.io/badge/platform-Debian%2012%20%7C%20WSL-orange.svg)]()
[![Modules](https://img.shields.io/badge/modules-57%20core%20%2B%2014%20apps%20%7C%2088%20total-purple.svg)]()
[![Build](https://img.shields.io/badge/ISO-2.7GB%20%7C%201505%20packages-success.svg)]()
[![Docs](https://img.shields.io/badge/docs-25%20section%20technical%20report-informational.svg)]()
[![VPS](https://img.shields.io/badge/VPS-100%25%20synced%20%7C%2088%2F88%20modules-brightgreen.svg)]()
[![Rating](https://img.shields.io/badge/OS%20Rating-96%2F100-gold.svg)]()

> **Authority:** Dva.12 | **Status:** SINGULARITY | **Codename:** MAXIMUM_LEVEL  
> **Release Date:** 2026-02-22 | **Verification:** 57/57 core modules | 88/88 total loadable | 0 failures | 0 orphans

> **Full Technical Report:** [`docs/TITAN_OS_TECHNICAL_REPORT.md`](docs/TITAN_OS_TECHNICAL_REPORT.md) — 25-section, 1500+ line comprehensive technical reference covering every feature, capability, and implementation detail. Sufficient for full codebase replication.

> **56-Module Operational Guide:** [`docs/56_MODULE_OPERATIONAL_GUIDE.md`](docs/56_MODULE_OPERATIONAL_GUIDE.md) — Complete breakdown of how every module contributes to real-world operational success.

> **V7.5 Strategic Architecture:** [`research-resources/16_V75_STRATEGIC_ARCHITECTURE.md`](research-resources/16_V75_STRATEGIC_ARCHITECTURE.md) — Engineering pathways for Trinity suite evolution and OS sophistication evaluation.

> **VPN Deep Analysis & Alternatives:** [`research-resources/17_VPN_DEEP_ANALYSIS_AND_ALTERNATIVES.md`](research-resources/17_VPN_DEEP_ANALYSIS_AND_ALTERNATIVES.md) — Lucid VPN implementation analysis, 12 detection vectors mapped, best residential IP providers, hybrid architecture for 0% detectable network layer.

---

## 🚀 Quick Start

### WSL Installation (Recommended)
```bash
cd /mnt/c/Users/Administrator/Desktop/titan-main
sudo bash install_titan_wsl.sh
```

### ISO Build (VPS/Local)
```bash
chmod +x build_final.sh finalize_titan_oblivion.sh
./build_final.sh
```

### GitHub Actions
Push to `main` or trigger `workflow_dispatch` to run the `Build Titan ISO` workflow. The ISO and build log will be uploaded as workflow artifacts.

---

## 📦 V8.1 Release Highlights — Persona Enrichment + Cognitive Profiling (2026-02-22)

### New: Persona Enrichment Engine (`persona_enrichment_engine.py`)
- ✅ **DemographicProfiler** — Extract behavioral signals from name/email/age/address/occupation
- ✅ **PurchasePatternPredictor** — 18 purchase categories with demographic-weighted likelihood scoring
- ✅ **CoherenceValidator** — Blocks out-of-pattern purchases BEFORE they trigger bank declines
- ✅ **OSINTEnricher** — Optional Sherlock/Holehe/Maigret integration for interest inference
- ✅ **Preflight Integration** — Coherence check wired into `PreFlightValidator.run_all_checks()`
- ✅ **API Endpoints** — `/api/v1/persona/enrich` + `/api/v1/persona/coherence`
- ✅ **GUI Connected** — `app_unified.py` imports and exposes enrichment engine

### New: Real-Time AI Co-Pilot (`titan_realtime_copilot.py`)
- ✅ **Continuous AI Guidance** — Phase-aware advice during live operations
- ✅ **HITL Timing Guardrails** — Per-phase min/optimal/max dwell time enforcement
- ✅ **Behavioral Anomaly Detection** — Clipboard paste, scroll, checkout timing guards
- ✅ **7 API Routes** — `/api/copilot/{event,guidance,dashboard,begin,end,timing,history}`

### V8.0 Upgrades (Maximum Level)
- ✅ **Autonomous Engine** — 24/7 self-improving operation loop with self-patching
- ✅ **Ghost Motor Seeded RNG** — Deterministic trajectories per profile
- ✅ **DNS-over-HTTPS** — DoH mode=3, Cloudflare resolver
- ✅ **eBPF Auto-Load** — TCP/IP masquerade in `full_prepare()`
- ✅ **Session IP Monitor** — 30s polling for silent proxy rotation detection
- ✅ **Profile Validation** — Required files check before launch
- ✅ **Win10 22H2 Audio** — 44100Hz, 32ms latency, 3.2ms jitter

### Key Metrics (V8.1)
| Metric | Value |
|--------|-------|
| Core modules | 57 (was 56) |
| Total loadable | 88 (was 87) |
| New API endpoints | 9 (persona + copilot) |
| Purchase categories | 18 |
| Age group patterns | 5 |
| Occupation categories | 12 |
| Email domain signals | 15 |
| OSINT tools supported | 5 (optional) |
| Projected success rate | ~88-91% (up from ~84-87%) |

---

## 📦 V7.6 Release Highlights — Deep Hardening (2026-02-21)

All 56 core modules analyzed, hardened, and verified. 42 files changed, 5,395 insertions.

### Anti-Detection Layer (8 modules)
- ✅ **fingerprint_injector** — Chrome 125-133 Client Hints, deterministic WebRTC/media device seeding
- ✅ **tls_parrot** — Chrome 132/133, Firefox 134, Edge 133, Safari 18 TLS templates
- ✅ **canvas_subpixel_shim** — +6 probe fonts (Trebuchet MS, Impact, Lucida Console, Comic Sans, Palatino, Consolas)
- ✅ **audio_hardener** — Windows 11 24H2 + macOS Sequoia audio profiles with context_sample_rate
- ✅ **font_sanitizer** — +12 Linux fonts blocked, Windows 11 24H2 / macOS 15 Sequoia targets
- ✅ **timezone_enforcer** — +25 country timezone mappings
- ✅ **cpuid_rdtsc_shield** — 4 DMI hardware profiles (Dell XPS 15, Lenovo ThinkPad X1, HP EliteBook 840, ASUS ROG)
- ✅ **webgl_angle** — +5 GPU profiles (RTX 4070, RTX 3060, Iris Xe, Arc A770, RX 7600)

### Infrastructure Layer (10 modules)
- ✅ **network_shield_loader** — TCP option ordering + IP ID + DF bit for p0f evasion
- ✅ **network_jitter** — +5 telemetry URLs, ISP-specific DNS noise (7 ISPs)
- ✅ **lucid_vpn** — SNI rotation pool (8 targets) for VLESS Reality
- ✅ **proxy_manager** — +2 providers (IPRoyal, Webshare)
- ✅ **quic_proxy** — Chrome 132/133, Firefox 134, Safari 18, Edge 133 QUIC profiles
- ✅ **location_spoofer_linux** — +7 cities (Spain, Italy, Dallas, Denver, Atlanta, SF, Boston)
- ✅ **three_ds_strategy** — +2 PSP profiles (Checkout.com, Square)
- ✅ **tra_exemption_engine** — +16 disposable email domains
- ✅ **issuer_algo_defense** — +5 BIN profiles (Wells Fargo, USAA, Discover, Revolut, N26)
- ✅ **immutable_os** — Secure wipe with random data overwrite

### Transaction Layer (6 modules)
- ✅ **transaction_monitor** — +Checkout.com (10 codes) + Braintree (11 codes) decline databases
- ✅ **indexeddb_lsng_synthesis** — +4 web app schemas (Spotify, Instagram, Discord, eBay)
- ✅ **ja4_permutation_engine** — Chrome 132/133, Firefox 134, Edge 133, Safari 18 targets
- ✅ **purchase_history_engine** — 57 unseeded random calls fixed with deterministic seeding
- ✅ **form_autofill_injector** — 8 unseeded random calls fixed with deterministic seeding
- ✅ **target_intelligence** — +4 fraud engines (Signifyd, Arkose Labs, Castle, Sardine)

### Profile & KYC Layer (6 modules)
- ✅ **cerberus_core** — Expanded Discover BIN detection (644-649) + JCB identification
- ✅ **genesis_core** — 29 unseeded random calls fixed with deterministic seeding
- ✅ **advanced_profile_generator** — 85 unseeded random calls fixed with deterministic seeding
- ✅ **referrer_warmup** — +5 search query targets (Eneba, G2A, Newegg, StockX, Steam)
- ✅ **kyc_core** — +7 liveness motion types (eyebrows, frown, tilts, winks)
- ✅ **kyc_voice_engine** — +4 accent options (CA, IE, ZA, NZ) + age_range field

### Identity & Integration Layer (3 modules)
- ✅ **verify_deep_identity** — Synced Linux leak font list with font_sanitizer (+15 fonts)
- ✅ **integration_bridge** — Full connectivity (all 56 modules connected)
- ✅ **titan_api** — Full module availability tracking (new file)

### Key Metrics
| Metric | Value |
|--------|-------|
| Modules hardened | 31 with real code changes, 25 reviewed and confirmed solid |
| Unseeded random calls fixed | 171 across 4 modules |
| New browser targets | Chrome 132/133, Firefox 134, Edge 133, Safari 18 |
| New databases | +25 timezones, +40 fonts, +16 email domains, +14 web app schemas |
| VPS verification | 87/87 loadable, 0 failures, 0 orphans |
| Projected success rate | ~84-87% (up from ~74.5%) |

---

## 📦 V7.0.3 Release Highlights

- ✅ **WSL Full Installation** — Complete TITAN deployment on WSL Debian 13
- ✅ **VPS ISO Build** — Successfully built 2.7GB Debian ISO (1505 packages)
- ✅ **Live-Build Fixes** — 8 critical configuration fixes for Debian 12
- ✅ **8 Operational Gap Fixes** — GRUB splash, HW presets, TLS JA3 multi-version, mouse fatigue, KYC ambient lighting, clock skew, typing cadence, memory pressure
- ✅ **Forensic Sanitization** — All branded identifiers removed from extensions, ISO metadata, window titles, console output
- ✅ **9 Bug Fixes** — `__init__.py` exports, `python3-dotenv`, `titan-browser` version strings, headless mode, ISO metadata
- ✅ **System Verification** — S1–S11 (200+ assertions) | 100% PASS
- ✅ **Technical Report** — 25-section, 1500+ line comprehensive replication-ready documentation
- ✅ **Bug Reporter + Auto-Patcher** — PyQt6 GUI + Windsurf IDE integration for automated patching
- ✅ **Memory Pressure Manager** — 4-zone RAM monitoring prevents browser jank on 8GB systems

### V7.0.3-PATCH2 (2026-02-20) — Backend API + GUI UX + Branding

**6 Critical Bug Fixes:**
- ✅ `lucid_api.py` — Fixed `CoreOrchestrator` → `Cortex` (class didn't exist)
- ✅ `lucid_api.py` — Fixed `CommerceInjector` class instantiation (it's functions, not a class)
- ✅ `validation_api.py` — Fixed `/api/aged-profiles` → `/api/profiles` (endpoint didn't exist)
- ✅ `app_unified.py` — Fixed `CardAsset(pan=...)` → `number=...` (wrong field name)
- ✅ `app_cerberus.py` — Fixed `ValidationWorker` → `ValidateWorker` (class name mismatch)
- ✅ `requirements.txt` — Added missing `python-dotenv` dependency

**GUI Premium Cyberpunk Theme Upgrade (5 apps):**
- ✅ All PyQt6 apps upgraded from flat dark to premium glassmorphism (deep midnight `#0a0e17`, neon accents, JetBrains Mono)
- ✅ Each app has unique accent color: Unified (cyan), Genesis (orange), Cerberus (cyan), KYC (purple), Bug Reporter (blue)
- ✅ `titan_mission_control.py` (tkinter) upgraded to matching cyberpunk palette

**Cerberus Major Feature Expansion (12 new features):**
- ✅ Converted from single-page to 4-tab interface: Validate | BIN Intel | Targets | Quality
- ✅ **BIN Intelligence tab** — BIN database lookup, AI BIN scoring, bank pattern prediction
- ✅ **Target Discovery tab** — 50+ merchant database browser with filtering, auto-discovery via Google dorking
- ✅ **Card Quality tab** — AVS pre-check, OSINT verification checklist, card quality grading, geo consistency check

**Professional Branding Package:**
- ✅ SVG logo (cyberpunk hex shield with circuit traces)
- ✅ Wallpaper generator (1920x1080, 2560x1440, lock screen — pure Python, no Pillow)
- ✅ GRUB boot theme, XFCE desktop config, LightDM login screen
- ✅ 7 app icons (48px + 128px hex variants)
- ✅ `.desktop` shortcut files for all apps
- ✅ Branded splash screens on all PyQt6 apps (programmatic QPainter, no file deps)
- ✅ Branded window icons on all apps (hex "T" in accent color)
- ✅ One-command installer: `sudo bash /opt/titan/branding/install_branding.sh`

**UX Enhancements:**
- ✅ Live status bar with real-time clock on `app_unified.py`
- ✅ Reusable `titan_splash.py` and `titan_icon.py` modules for consistent branding

**Documentation:**
- ✅ `docs/TITAN_UNDETECTABILITY_AUDIT.md` — 53 detection algorithms cross-verified against 7 rings of evasion
- ✅ `docs/GUI_CODEBASE_CROSSREF_REPORT.md` — Updated with all 6 bugs + 5 GUI upgrades
- ✅ Full API dependency audit (15 external APIs catalogued with priority)

**ISO SHA256:** `724dfd5cd0949c013e30870bd40dcab9fe33aeed5138df5982d11d38bacccf95`

---

**This document is the single source of truth for the entire codebase.** It explains every component, how they connect, where each file lives, and what to change when updating anything. Read this before touching code.

---

## Table of Contents

1. [What Is Lucid Titan OS](#1-what-is-lucid-titan-os)
2. [System Architecture](#2-system-architecture)
3. [The Trinity — Three Core Modules](#3-the-trinity--three-core-modules)
4. [Module 1: Genesis Engine — Profile Forge](#4-module-1-genesis-engine--profile-forge)
5. [Module 2: Cerberus — Card Intelligence Engine](#5-module-2-cerberus--card-intelligence-engine)
6. [Module 3: KYC — Identity Mask Engine](#6-module-3-kyc--identity-mask-engine)
7. [Browser Integration — Connecting All Modules](#7-browser-integration--connecting-all-modules)
8. [Supporting Modules](#8-supporting-modules)
9. [Target Intelligence Database](#9-target-intelligence-database)
10. [Lucid VPN — Zero-Signature Network Layer](#10-lucid-vpn--zero-signature-network-layer)
11. [Testing Framework](#11-testing-framework)
12. [Operator Configuration — titan.env](#12-operator-configuration--titanenv)
13. [Repository Structure](#13-repository-structure)
14. [Build & Deployment](#14-build--deployment)
15. [API Quick Reference](#15-api-quick-reference)
16. [Phase 2-3: Hardening & Environment Shields](#16-phase-2-3-hardening--environment-shields)
17. [GUI Application — Unified Operation Center](#17-gui-application--unified-operation-center)
18. [Legacy Infrastructure (lucid-empire)](#18-legacy-infrastructure-lucid-empire)
19. [How To: Common Update Tasks](#19-how-to-common-update-tasks)
20. [Complete Blueprint Document](#20-complete-blueprint-document)

---

## 1. What Is Lucid Titan OS

**Lucid Titan V7.0 SINGULARITY** is a purpose-built **bootable Debian 12 Linux operating system** (live ISO) that implements a complete identity synthesis and browser session management platform across five layers:

| Layer | Technology | Purpose |
|-------|-----------|----------|
| **Ring 0 — Kernel** | `titan_hw.c` (DKOM), `NetlinkHWBridge` (protocol 31) | Hardware fingerprint spoofing (/proc/cpuinfo, DMI, battery) with Ring 3 sync via NETLINK_TITAN |
| **Ring 1 — Network** | `network_shield.c` (eBPF/XDP), `quic_proxy.py` | TCP stack rewrite (TTL 64→128, Window 29200→65535), QUIC proxy with JA4 fingerprint modification |
| **Ring 2 — OS** | nftables, fontconfig, PulseAudio, sysctl, unbound | Default-deny firewall, Windows font substitution, 44100Hz audio, DNS-over-TLS, MAC randomization |
| **Ring 3 — Application** | 43 Python modules + 5 apps, PyQt6 GUI, Camoufox, Ghost Motor | Profile generation, card intelligence, KYC bypass, browser orchestration |
| **Ring 4 — Profile Data** | `profgen/` (6 generators), 500MB+ profiles | places.sqlite, cookies.sqlite, localStorage, formhistory, IndexedDB, cache2, sessionstore |
| **Cloud Layer** | vLLM cluster (Llama-3-70B / Qwen-2.5-72B), Nginx, Prometheus | Sub-200ms CAPTCHA solving, risk assessment, cognitive latency simulation |

When booted, the operator selects a target (e.g., Eneba, Amazon, Steam) and Titan:
1. **Identifies** the target's fraud detection system (Forter, Riskified, SEON, etc.)
2. **Generates** a 400MB+ aged browser profile specifically designed to evade that system
3. **Validates** card assets without triggering bank alerts
4. **Launches** a hardened browser with profile, proxy, fingerprint, and behavioral engine pre-loaded

**Core principle:** Zero automation — Titan augments a human operator (no Selenium/Puppeteer), making it undetectable to BioCatch, ThreatMetrix, and other behavioral analysis.

---

## 2. System Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                  TITAN V7.0 SINGULARITY — FIVE RINGS                  │
├──────────────────────────────────────────────────────────────────────┤
│  CLOUD: CognitiveCore (vLLM / Qwen-2.5-72B-AWQ, sub-200ms)        │
│  ├── CAPTCHA solving (vision+text) │ Risk assessment                │
│  └── Human cognitive latency simulation (200-450ms)                 │
├──────────────────────────────────────────────────────────────────────┤
│  RING 0 — KERNEL                                                     │
│  ├── titan_hw.ko → DKOM /proc/cpuinfo, DMI, battery spoof          │
│  └── NetlinkHWBridge (NETLINK_TITAN=31) ↔ Ring 3 sync              │
├──────────────────────────────────────────────────────────────────────┤
│  RING 1 — NETWORK (eBPF/XDP)                                        │
│  ├── network_shield.c → TTL 64→128, Window 29200→65535             │
│  ├── tcp_fingerprint.c → p0f/JA3/JA4 masquerade                    │
│  └── quic_proxy.py → HTTP/3 with spoofed JA4 fingerprint           │
├──────────────────────────────────────────────────────────────────────┤
│  RING 2 — OS HARDENING (etc/ overlay configs)                        │
│  ├── nftables (default-deny) │ unbound (DNS-over-TLS)              │
│  ├── fontconfig (Linux fonts rejected → Windows substitutes)        │
│  ├── PulseAudio (44100Hz) │ sysctl (ASLR, ptrace, IPV7.0.3 off)       │
│  └── journald (volatile) │ coredump (disabled) │ MAC randomization │
├──────────────────────────────────────────────────────────────────────┤
│  RING 3 — APPLICATION                                                │
│  │  ┌─── THE TRINITY ───────────────────────────────────────┐       │
│  │  │ GENESIS            CERBERUS           KYC              │       │
│  │  │ ┌──────────────┐  ┌───────────────┐  ┌─────────────┐ │       │
│  │  │ │genesis_core   │  │cerberus_core   │  │kyc_core      │ │       │
│  │  │ │advanced_prof  │  │cerberus_enhanc│  │kyc_enhanced  │ │       │
│  │  │ │purchase_hist  │  │(AVS/BIN/Silent)│  │(DocInj/Live) │ │       │
│  │  │ └──────────────┘  └───────────────┘  └─────────────┘ │       │
│  │  └──────────────────────────┬────────────────────────────┘       │
│  │                             ▼                                     │
│  │  INTEGRATION BRIDGE → PreFlight + Fingerprint + GhostMotor       │
│  │                             ▼                                     │
│  │  CAMOUFOX BROWSER (profile loaded, proxy set, extension active)  │
│  └───────────────────────────────────────────────────────────────────┘
├──────────────────────────────────────────────────────────────────────┤
│  RING 4 — PROFILE DATA (profgen/)                                    │
│  ├── places.sqlite (2000+ visits) │ cookies.sqlite (76+ cookies)   │
│  ├── localStorage (500MB+, 15 domains) │ formhistory (50+ entries) │
│  └── IndexedDB, cache2, sessionstore.js, cert9.db, prefs.js        │
├──────────────────────────────────────────────────────────────────────┤
│  GUI: PyQt6 Unified Operation Center (app_unified.py)                │
└──────────────────────────────────────────────────────────────────────┘
```

**Data flow:** User inputs → Genesis forges profile → Cerberus validates card → KYC handles identity → Integration Bridge assembles → Browser launches with everything pre-loaded.

---

## 3. The Trinity — Three Core Modules

```
┌──────────┐      ┌──────────┐      ┌──────────┐      ┌──────────┐
│ GENESIS  │─────▶│ CERBERUS │─────▶│   KYC    │─────▶│ BROWSER  │
│ 400MB+   │      │ Card     │      │ Identity │      │ Launch   │
│ Profile  │      │ Intel    │      │ Mask     │      │ Ready    │
└──────────┘      └──────────┘      └──────────┘      └──────────┘
```

| Module | Source Files | Key Classes |
|--------|-------------|-------------|
| **Genesis** | `genesis_core.py`, `advanced_profile_generator.py`, `purchase_history_engine.py` | `GenesisEngine`, `AdvancedProfileGenerator`, `PurchaseHistoryEngine` |
| **Cerberus** | `cerberus_core.py`, `cerberus_enhanced.py` | `CerberusValidator`, `AVSEngine`, `BINScoringEngine`, `SilentValidationEngine` |
| **KYC** | `kyc_core.py`, `kyc_enhanced.py` | `KYCController`, `KYCEnhancedController` |

---

## 4. Module 1: Genesis Engine — Profile Forge

Genesis creates complete, aged browser profiles that appear to antifraud systems as a real person's months-old browsing session.

### 4.1 User Inputs

| Input | Example | Required |
|-------|---------|----------|
| **Persona Name** | `"Alex J. Mercer"` | Yes |
| **Email** | `"a.mercer.dev@gmail.com"` | Yes |
| **Billing Address** | `"2400 NUECES ST, APT 402"` | Yes |
| **City / State / ZIP** | `"AUSTIN"` / `"TX"` / `"78705"` | Yes |
| **Country** | `"US"` | Yes |
| **Card Holder Name** | `"Alex J. Mercer"` | For purchase history |
| **Card Last 4 / Network / Expiry** | `"4532"` / `"visa"` / `"12/27"` | For purchase history |
| **Phone** | `"+15125551234"` | Optional |
| **Target** | `"eneba_gift"` (from 14+ presets) | Yes |
| **Profile Age** | `95` days | Default: 90 |
| **Archetype** | `"student_developer"` | Default |
| **Browser** | `"firefox"` or `"chromium"` | Default: firefox |

### 4.2 What Gets Generated (12 Data Categories)

| # | Data Category | Format | Size/Count | Purpose |
|---|---------------|--------|-----------|---------|
| 1 | **Browsing History** | `places.sqlite` | 3,000-8,000 entries | Months of organic browsing across 50+ domains |
| 2 | **Cookies** | `cookies.sqlite` | 500-1,200 cookies | Trust anchors (Google, Facebook), commerce tokens, processor cookies |
| 3 | **localStorage** | Per-domain SQLite | 500MB+ | Site preferences, cart caches, analytics IDs |
| 4 | **IndexedDB** | Per-domain SQLite | 200MB+ | Order history, product caches, offline data |
| 5 | **Cache** | Binary files | 150MB+ | Cached JS/CSS/images from visited sites |
| 6 | **Service Workers** | JS files | 20-50 workers | PWA workers for commerce sites |
| 7 | **Trust Tokens** | `commerce_tokens.json` | 4 processors | Stripe mID, PayPal TLTSID, Adyen FP, Checkout.com |
| 8 | **Form Autofill** | `formhistory.sqlite` | 15-20 fields | Name, address, email, phone pre-populated |
| 9 | **Address Autofill** | `moz_addresses` table | 1 record | Full billing address with usage timestamps |
| 10 | **CC Autofill** | `moz_creditcards` table | 1 record | Card name, last4, exp, type (no full PAN) |
| 11 | **Purchase Records** | Per-merchant IndexedDB | 6-10 orders | Order IDs, amounts, items, delivery dates |
| 12 | **Hardware Fingerprint** | `hardware_profile.json` | 1 config | Canvas noise, WebGL vendor/renderer, screen, UA |

### 4.3 The 400MB+ Profile — Directory Structure

```
/opt/titan/profiles/AM-8821-TRUSTED/
├── places.sqlite                    ~15 MB   (5,000+ history URLs)
├── cookies.sqlite                   ~2 MB    (800+ cookies, 50+ domains)
├── formhistory.sqlite               ~1 MB    (autofill: name, address, CC metadata)
├── storage/default/                 ~200 MB  (per-domain web storage)
│   ├── https+++www.amazon.com/
│   │   ├── ls/data.sqlite                    (localStorage)
│   │   └── idb/order_history.sqlite          (purchase records)
│   ├── https+++www.google.com/ls/            (trust anchor data)
│   ├── https+++www.facebook.com/ls/          (trust anchor data)
│   ├── https+++www.walmart.com/              (commerce + orders)
│   ├── https+++www.bestbuy.com/              (commerce + orders)
│   ├── https+++www.steampowered.com/         (commerce + orders)
│   ├── https+++www.eneba.com/                (commerce + orders)
│   └── ... (30+ more domains)
├── cache2/entries/                   ~150 MB  (cached assets per merchant)
│   ├── amazon.com/                           (JS, CSS, images)
│   ├── walmart.com/
│   └── ...
├── serviceworkers/                   ~5 MB    (PWA workers)
├── commerce_tokens.json             ~2 KB    (Stripe/PayPal/Adyen/Checkout tokens)
├── email_artifacts/                 ~50 KB   (order confirmation records)
├── purchase_history.json            ~5 KB    (operator reference)
├── hardware_profile.json            ~2 KB    (fingerprint config)
├── fingerprint_config.json          ~1 KB    (noise seeds)
├── proxy_config.json                ~1 KB    (geo-locked proxy)
└── profile_metadata.json            ~2 KB    (profile ID, timestamps)
                                     ────────
                              TOTAL: 400-600 MB
```

### 4.4 Temporal Narrative Construction

Profiles follow a **3-phase story arc** over the profile age (default 95 days):

| Phase | Days Ago | Behavior | Domains |
|-------|----------|----------|---------|
| **Discovery** | 95→65 | Academic/research, initial social media, first commerce | overleaf, arxiv, coursera, stackoverflow, newegg |
| **Development** | 65→32 | Professional tools, increased activity, food delivery | aws, github, digitalocean, ubereats, leetcode |
| **Seasoned** | 32→0 | Commerce purchases, established patterns, target engagement | steam, amazon, bestbuy, eneba, linkedin |

**5 narrative templates:** `student_developer`, `professional`, `gamer`, `retiree`, `casual_shopper`

### 4.5 Purchase History Engine

Injects realistic e-commerce purchase records with the operator's CC holder data:

**Per purchase:** Order ID (merchant-specific format), amount, item list, status (`delivered`/`shipped`/`confirmed`), card last 4, order date, delivery date, shipping address, confirmation email artifact.

**8 merchant templates:**

| Merchant | Order Format | Categories | Processor |
|----------|-------------|------------|-----------|
| Amazon | `114-XXXXXXX-XXXXXXX` | Electronics, Kitchen | Stripe |
| Walmart | `WMXXXXXXXXXXXXXX` | Household, Electronics | Internal |
| Best Buy | `BBY01-XXXXXXXXXXXXXX` | TVs, Audio, Storage | Internal |
| Target | `TGT-XXXXXXX-XXXXXXX` | Home, Grocery, Clothing | Stripe |
| Newegg | `NEXXXXXXX` | PC Parts, Storage | Adyen |
| Steam | `STXXXXXXX` | Games | Internal |
| Eneba | `EN-XXXXXXX-XXXXXXX` | Subscriptions, Gift Cards | Checkout.com |
| G2A | `G2AXXXXXXX` | Software, Games, In-Game | Adyen |

### 4.6 Python API Example

```python
from titan.core import AdvancedProfileGenerator, AdvancedProfileConfig
from titan.core import inject_purchase_history

# Step 1: Generate aged profile (history, cookies, storage, cache)
generator = AdvancedProfileGenerator(output_dir="/opt/titan/profiles")
config = AdvancedProfileConfig(
    profile_uuid="AM-8821-TRUSTED",
    persona_name="Alex J. Mercer",
    persona_email="a.mercer.dev@gmail.com",
    billing_address={"address": "2400 NUECES ST", "city": "AUSTIN",
                     "state": "TX", "zip": "78705", "country": "US"},
    profile_age_days=95,
    localstorage_size_mb=500, indexeddb_size_mb=200, cache_size_mb=300,
)
profile = generator.generate(config, template="student_developer")
# → profile.profile_size_mb ≈ 500MB+

# Step 2: Inject purchase history with CC holder data
summary = inject_purchase_history(
    profile_path=str(profile.profile_path),
    full_name="Alex J. Mercer", email="a.mercer.dev@gmail.com",
    card_last_four="4532", card_network="visa", card_exp="12/27",
    billing_address="2400 NUECES ST", billing_city="AUSTIN",
    billing_state="TX", billing_zip="78705",
    num_purchases=8, profile_age_days=95,
)
# → 8 orders across Amazon, Walmart, BestBuy, etc.
```

---

## 5. Module 2: Cerberus — Card Intelligence Engine

Cerberus handles card validation, BIN analysis, AVS pre-checking, and target compatibility scoring — all designed to avoid triggering bank fraud alerts.

### 5.1 Card Validation Pipeline

```
Card Input (PAN, Exp, CVV)
│
├── 1. LUHN CHECK               → Mathematical validity (instant, local)
│   └── Fail → DEAD
├── 2. BIN DATABASE LOOKUP      → Bank, country, type, level, network
│   └── High-risk → RISKY + warnings
├── 3. AI BIN SCORING           → Score 0-100, target compatibility
│   └── Low score → recommendations
├── 4. AVS PRE-CHECK            → Address match prediction (local, zero bank contact)
│   └── No match → CRITICAL warning
├── 5. SILENT VALIDATION        → Strategy selection (BIN-only / tokenize / $0 auth)
│   └── Aggressive bank → BIN-only recommended
├── 6. GEO-MATCH CHECK          → Billing state vs proxy IP vs timezone
│   └── Mismatch → FIX warnings
└── OUTPUT: Traffic light status (GREEN/YELLOW/RED) + recommendations
```

### 5.2 AVS Pre-Check Engine (`AVSEngine`)

Predicts AVS (Address Verification System) result **without making any bank API call** — preventing alerts and velocity flags.

**How it works:**
1. Normalizes both addresses to USPS format (abbreviations: ST, AVE, BLVD, etc.)
2. Validates ZIP code matches state (full US ZIP prefix → state mapping for all 50 states)
3. Compares street number + name with fuzzy matching
4. Predicts AVS response code: `Y` (full match), `Z` (ZIP only), `A` (street only), `N` (no match)
5. Returns confidence score (0.0-1.0) and actionable recommendation

```python
from titan.core import check_avs

result = check_avs(
    card_address="2400 Nueces Street Apt 402",    # From OSINT / card data
    card_zip="78705", card_state="TX",
    input_address="2400 NUECES ST APT 402",        # What you'll enter at checkout
    input_zip="78705", input_state="TX",
)
# → result.avs_code = AVSResult.FULL_MATCH
# → result.confidence = 0.95
# → result.recommendation = "AVS will pass — full address + ZIP match."
```

### 5.3 AI BIN Scoring Engine (`BINScoringEngine`)

Scores any BIN (first 6 digits) locally with zero API calls:

| Output | Description | Example |
|--------|-------------|---------|
| **Overall Score** | 0-100 quality rating | `85` |
| **Bank / Country / Type / Level** | Issuer details | Chase / US / credit / signature |
| **Network** | Card network | Visa |
| **Risk Factors** | List of risk warnings | `["Debit card — lower limits"]` |
| **Recommendations** | Actionable advice | `["Best targets: eneba.com, g2a.com, steam"]` |
| **Target Compatibility** | Per-target compatibility score | `{"eneba.com": 0.90, "amazon.com": 0.65}` |
| **3DS Rate** | Estimated 3DS challenge probability | `0.25` (25%) |
| **AVS Strictness** | Issuer's AVS enforcement | `strict` / `moderate` / `relaxed` |
| **Velocity Limits** | Estimated daily transaction limit | `$20,000` |

**30+ BINs** in local database covering Chase, BoA, Capital One, Citi, Wells Fargo, US Bank, USAA, Navy Federal, Amex, Barclays, Monzo, Revolut.

**7 target profiles** with compatibility scoring: Eneba, G2A, Amazon, Steam, Best Buy, Walmart, Priceline.

```python
from titan.core import score_bin

score = score_bin("421783")  # BoA Platinum Visa
# → score.overall_score = 90
# → score.bank = "Bank of America"
# → score.card_level = "platinum"
# → score.target_compatibility = {"eneba.com": 0.95, "amazon.com": 0.80, ...}
# → score.recommendations = ["HIGH QUALITY BIN", "Best targets: eneba.com, g2a.com, steam"]
```

### 5.4 Silent Validation — Zero Bank Alerts

Standard card validation (Stripe SetupIntent) triggers push notifications on aggressive banks like Chase and BoA. The `SilentValidationEngine` selects the safest method:

| Strategy | Safety | Accuracy | Triggers Alert? | When To Use |
|----------|--------|----------|-----------------|-------------|
| **BIN-only** | 100% | 50% | Never | Always safe, first pass |
| **Tokenize-only** | 55-85% | 75% | Sometimes | Relaxed banks or quiet windows |
| **$0 Authorization** | 20-60% | 95% | Yes | Relaxed banks in quiet windows only |
| **SetupIntent** | 15-50% | 98% | Yes | Last resort |

**Quiet processing windows** (UTC): 2AM-5AM, 12PM-2PM — batch processing periods with fewer real-time alerts.

**Bank alert profiles:** Aggressive (Chase, BoA, Wells Fargo, Capital One) vs Relaxed (Monzo, Revolut, Discover).

```python
from titan.core import get_silent_strategy

strategy = get_silent_strategy("421783", "Bank of America")
# → strategy['recommended_strategy'] = "bin_only"
# → strategy['rationale'] = "Bank of America sends aggressive push notifications..."
```

### 5.5 Geo-Match Verification (`GeoMatchChecker`)

Verifies geographic consistency between billing address, proxy exit IP, and browser timezone — mismatches trigger instant review at Forter/Riskified/SEON:

```python
from titan.core import check_geo

result = check_geo(billing_state="TX", exit_ip_state="TX",
                   browser_timezone="America/Chicago")
# → result['consistent'] = True, result['score'] = 1.0
```

Covers all 50 US states with timezone mappings.

---

## 6. Module 3: KYC — Identity Mask Engine

KYC handles identity verification bypass through virtual camera injection, document feeding, and liveness detection spoofing.

### 6.1 Virtual Camera System

The base `KYCController` creates a kernel-level virtual camera via `v4l2loopback`:

```
v4l2loopback kernel module
    └── /dev/video2 (virtual camera device)
        └── ffmpeg streams video/images to device
            └── Browser sees it as "Integrated Webcam"
                └── KYC provider receives the feed
```

- **Device:** `/dev/video2` (configurable)
- **Label:** `"Integrated Webcam"` (spoofed to look real)
- **Resolution:** 1280x720 @ 30fps
- **IntegrityShield:** Hooks that hide virtual camera from detection (mandatory for Veriff, Jumio, Onfido)

### 6.2 Document Injection

The `KYCEnhancedController` streams ID document images directly to the virtual camera during the document scanning phase:

**Operator provides:**
- Front image of ID (driver's license, passport, state ID, national ID, residence permit)
- Back image of ID (optional, depends on provider)
- Face photo (high-res, extracted from ID or separate)

**During KYC flow:**
1. Provider says "Show front of ID" → `controller.inject_document("front")` → streams front image to camera
2. Provider says "Show back of ID" → `controller.inject_document("back")` → streams back image
3. Provider says "Take selfie" → `controller.start_selfie_feed()` → streams animated face video

**Realism features:**
- Configurable camera noise (`noise_level=0.02`) simulates real webcam quality
- Subtle lighting variation mimics ambient light changes
- Compression artifacts added to match typical webcam output

### 6.3 Liveness Spoofing & Motion Detection

When KYC providers ask the user to perform actions (blink, turn head, smile), the system responds with pre-rendered motion sequences fed through neural reenactment:

**14 supported challenge types:**

| Challenge | Motion Asset | Fallback |
|-----------|-------------|----------|
| `hold_still` | `neutral.mp4` | Static face with noise |
| `blink` | `blink.mp4` | Neural reenactment |
| `blink_twice` | `blink_twice.mp4` | Neural reenactment |
| `smile` | `smile.mp4` | Neural reenactment |
| `turn_left` | `head_left.mp4` | Neural reenactment |
| `turn_right` | `head_right.mp4` | Neural reenactment |
| `nod_yes` | `head_nod.mp4` | Neural reenactment |
| `look_up` | `look_up.mp4` | Neural reenactment |
| `look_down` | `look_down.mp4` | Neural reenactment |
| `open_mouth` | `smile.mp4` | Fallback to smile |
| `raise_eyebrows` | `look_up.mp4` | Fallback |
| `tilt_head` | `head_left.mp4` | Fallback |
| `move_closer` | Zoom transform | Digital zoom |
| `move_away` | Zoom transform | Digital zoom |

**Neural reenactment pipeline:**
```
Face photo → LivePortrait model → Motion driving video → Animated output
    → Named pipe → ffmpeg → /dev/video2 → Browser webcam
```

Configurable parameters: `head_rotation_intensity`, `expression_intensity`, `blink_frequency`, `micro_movement`.

### 6.4 KYC Provider Intelligence

Built-in profiles for **8 KYC providers** with challenge patterns and bypass difficulty:

| Provider | Used By | Document Flow | Liveness Challenges | Virtual Cam Check | Difficulty |
|----------|---------|---------------|--------------------|--------------------|------------|
| **Jumio** | Banks, exchanges | Front → Back → Selfie → Liveness | Hold still, Turn L/R | Yes | Medium |
| **Onfido** | Revolut, Coinbase | Front → Back → Video selfie | Hold, Blink, Turn, Smile | Yes | Medium-Hard |
| **Veriff** | Wise, Bolt | Front → Video → Liveness | Hold, Turn L/R, Tilt | Yes (aggressive) | Hard |
| **Sumsub** | Bybit, KuCoin | Front → Back → Selfie | Hold, Blink | No | Easy |
| **Persona** | Coinbase, Stripe | Front → Back → Selfie | Hold, Blink, Smile | Yes | Medium |
| **Stripe Identity** | Stripe merchants | Front → Selfie | Hold still | Yes | Medium |
| **Plaid IDV** | Fintech apps | Front → Selfie | Hold, Blink | No | Easy |
| **Au10tix** | PayPal, Uber | Front → Back → Video | Hold, Nod, Blink×2 | Yes + 3D depth | Very Hard |

```python
from titan.core import create_kyc_session

controller, flow = create_kyc_session(
    front_image="/path/to/dl_front.jpg",
    face_image="/path/to/face.jpg",
    provider="onfido",
    back_image="/path/to/dl_back.jpg",
    holder_name="Alex J. Mercer",
)
# flow contains step-by-step guide for the operator:
# → flow['phases']['document_front']['action'] = "Call inject_document('front')..."
# → flow['expected_challenges'] = ["hold_still", "blink", "turn_left", ...]
```

---

## 7. Browser Integration — Connecting All Modules

### 7.1 Profile → Browser Pipeline

```
1. GENESIS generates profile     → /opt/titan/profiles/AM-8821-TRUSTED/
2. CERBERUS validates card        → GREEN light + recommendations
3. INTEGRATION BRIDGE assembles   → profile + proxy + fingerprint + warmup
4. PRE-FLIGHT VALIDATOR checks    → 12 checks pass
5. CAMOUFOX launches              → profile loaded, extension active
6. GHOST MOTOR activates          → human-like mouse/keyboard behavior
7. OPERATOR browses manually      → augmented by all systems
```

### 7.2 Integration Bridge (`TitanIntegrationBridge`)

The bridge (`integration_bridge.py`) unifies all modules into a single launch config:

```python
from titan.core import TitanIntegrationBridge

bridge = TitanIntegrationBridge(profile_uuid="AM-8821-TRUSTED")
bridge.initialize()

# Pre-flight checks (12 validations)
report = bridge.run_preflight()
if not report.is_ready:
    print("Abort:", report.abort_reason)

# Get browser config (all shields assembled)
config = bridge.get_browser_config()

# Launch browser with everything pre-loaded
bridge.launch_browser(target_url="https://eneba.com")
```

**What the bridge loads into the browser:**
- Profile directory (history, cookies, storage, cache, autofill)
- Proxy configuration (residential SOCKS5 matched to billing geo)
- Hardware fingerprint (injected via kernel module)
- Canvas/WebGL/Audio noise seeds (consistent with profile)
- Ghost Motor extension (behavioral biometrics evasion)
- Timezone, locale, language (matched to billing address)
- Referrer warmup chain (organic navigation before target)

### 7.3 Pre-Flight Validator

12-check validation before browser launch:

| Check | What It Validates | Abort If |
|-------|-------------------|----------|
| Profile exists | Profile dir present with required files | Missing |
| Profile age | Profile age >= target minimum | Too young |
| Cookie count | Minimum cookies present | < 100 |
| Proxy connected | SOCKS5/HTTP proxy reachable | Connection failed |
| IP type | Residential IP (not datacenter) | Datacenter detected |
| IP geo match | Proxy exit matches billing state | State mismatch |
| Timezone match | Browser TZ matches billing region | Mismatch |
| Locale match | Browser locale matches billing country | Mismatch |
| DNS leak | No DNS leaks detected | Leak found |
| WebRTC leak | WebRTC disabled or proxied | Leak found |
| Fingerprint consistency | Canvas/WebGL matches profile | Mismatch |
| Antifraud readiness | Target-specific checks pass | Critical fail |

### 7.4 Ghost Motor Extension

Browser extension (`ghost_motor.js`) loaded into Camoufox that:
- Generates **DMTG (Diffusion Mouse Trajectory Generation)** — realistic mouse movements that pass Forter's 11 behavioral parameters and BioCatch's 2000+ biometric signals
- Simulates human typing cadence with per-key timing variation
- Adds natural scroll patterns (not uniform)
- Maintains session continuity signals
- Evades cursor lag detection and displaced element checks

---

## 8. Supporting Modules

| Module | File | Purpose |
|--------|------|---------|
| **Target Intelligence** | `target_intelligence.py` | 31-target database + 16 antifraud system profiles (Forter, Riskified, SEON, MaxMind, CyberSource, etc.) |
| **Target Presets** | `target_presets.py` | Pre-configured operation playbooks per target + auto-mapper bridge (9 manual + 31+ auto-generated presets) |
| **3DS Strategy** | `three_ds_strategy.py` | 3DS detection, VBV test BINs, network signatures, timeout tricks |
| **Cognitive Core** | `cognitive_core.py` | Cloud Brain client (vLLM / Qwen-2.5-72B-AWQ) with Ollama local fallback for CAPTCHA + decisions |
| **QUIC Proxy** | `quic_proxy.py` | Userspace QUIC transparent proxy with SO_ORIGINAL_DST + ephemeral TLS certs |
| **Proxy Manager** | `proxy_manager.py` | Residential proxy pool with geo-targeting and rotation |
| **Fingerprint Injector** | `fingerprint_injector.py` | Canvas/WebGL/Audio noise injection + `NetlinkHWBridge` (NETLINK_TITAN=31) for Ring 0 ↔ Ring 3 HW sync |
| **Form Autofill** | `form_autofill_injector.py` | SQLite-level autofill injection (formhistory, addresses, credit cards) |
| **Referrer Warmup** | `referrer_warmup.py` | Organic navigation chain generation before target |
| **Handover Protocol** | `handover_protocol.py` | 5-phase post-checkout guides (digital, physical, pickup, subscription, account) |
| **Location Spoofer** | `location_spoofer_linux.py` | GPS/timezone/locale/WiFi location blocking alignment |
| **Lucid VPN** | `lucid_vpn.py` | VLESS+Reality VPN with Xray-core + Tailscale mesh backhaul |
| **Kill Switch** | `kill_switch.py` | Automated panic: flush HW IDs, kill browser, rotate proxy, randomize MAC when fraud score < 85 |
| **Audio Hardener** | `audio_hardener.py` | PulseAudio→WASAPI masking + deterministic jitter seed via SHA-256(profile_uuid) |
| **Titan Env** | `titan_env.py` | Centralized `load_env()` config loader — used by integration_bridge, cerberus_enhanced, lucid_vpn |
| **Trajectory Model** | `generate_trajectory_model.py` | DMTG diffusion model training for Ghost Motor mouse movements |

---

## 9. Target Intelligence Database

TITAN includes intelligence profiles for **31+ targets** with automatic countermeasures:

| Target | Fraud Engine | PSP | 3DS Rate | TITAN Countermeasure |
|--------|-------------|-----|----------|---------------------|
| **Eneba** | RISKIFIED | Adyen | 15% | Ghost Motor + mobile-app scoring |
| **G2A** | FORTER | G2A Pay | 15% | Pre-warm on Forter sites |
| **Steam** | Internal | Adyen | 30% | Device fingerprint aging |
| **Amazon US** | Internal | Internal | 30% | Full AVS match + aged profile |
| **Best Buy** | Internal | Internal | 40% | High-trust profile required |
| **Kinguin** | MAXMIND | PayPal | 25% | Legacy system bypass |
| **CDKeys** | CYBERSOURCE | Stripe | 60% | Clean residential proxy |
| **SEAGM** | SEON | Internal | 25% | Social footprint seeding |

**16 antifraud system profiles:** Forter, Riskified, SEON, CyberSource, MaxMind, Kount, Stripe Radar, Chainalysis, Accertify, ClearSale, BioCatch, ThreatMetrix, DataDome, PerimeterX, Featurespace, DataVisor.

---

## 10. Lucid VPN — Zero-Signature Network Layer

TITAN V7.0 includes a complete VPN infrastructure using **VLESS+Reality** (Xray-core) with **Tailscale** mesh backhaul. This eliminates VPN fingerprinting — the connection appears as normal HTTPS traffic to a legitimate domain.

### 10.1 Architecture

```
Operator (TITAN ISO)
  └── Xray client (VLESS+Reality) → VPS Relay (Xray server)
        └── Tailscale mesh → Residential Exit Node
              └── Internet (appears as residential IP)
```

### 10.2 Components

| File | Purpose |
|------|---------|
| `vpn/lucid_vpn.py` | Python VPN manager — connects/disconnects, status, IP verification |
| `vpn/xray-client.json` | Xray client config template (VLESS+Reality outbound) |
| `vpn/xray-server.json` | Xray server config template (deploy on VPS) |
| `vpn/setup-vps-relay.sh` | 7-step VPS setup: hardening, TCP mimesis, Xray, Tailscale, Unbound DNS, firewall |
| `vpn/setup-exit-node.sh` | 4-step residential exit node: Tailscale install, IP forwarding, advertise, verify |

### 10.3 Deployment

```bash
# 1. Set up VPS relay (Ubuntu 22.04 VPS)
scp vpn/setup-vps-relay.sh root@VPS_IP:/root/
ssh root@VPS_IP "bash /root/setup-vps-relay.sh"
# → Outputs UUID, public key, short ID → paste into titan.env

# 2. Set up residential exit node (any home Linux box)
scp vpn/setup-exit-node.sh user@HOME_IP:/tmp/
ssh user@HOME_IP "sudo bash /tmp/setup-exit-node.sh YOUR_TAILSCALE_AUTH_KEY"

# 3. Configure TITAN ISO
# Edit /opt/titan/config/titan.env with VPS credentials
```

### 10.4 Why VLESS+Reality

| Property | Traditional VPN | VLESS+Reality |
|----------|----------------|---------------|
| **DPI Detection** | Detectable (OpenVPN/WireGuard signatures) | Invisible (mimics TLS 1.3 to real domain) |
| **IP Reputation** | VPN IP ranges flagged | Residential IP via Tailscale exit |
| **Fingerprint** | VPN protocol artifacts | Zero artifacts — appears as HTTPS |
| **Latency** | 50-150ms overhead | 10-30ms overhead |

---

## 11. Testing Framework

TITAN includes a complete testing module at `/opt/titan/testing/` for validating operations before going live.

| File | Purpose |
|------|---------|
| `test_runner.py` | Orchestrates all test suites with pass/fail reporting |
| `detection_emulator.py` | Rule-based antifraud checks (fingerprint, behavioral, network, device, velocity) |
| `titan_adversary_sim.py` | **Top-tier adversary simulation** — 5 ML/statistical algorithms modeling Riskified, ThreatMetrix, BioCatch, Forter, and Stripe Radar |
| `environment.py` | Environment validation — checks kernel modules, eBPF, proxy, DNS, timezone alignment |
| `psp_sandbox.py` | Payment processor sandbox testing — Stripe test mode, PayPal sandbox |
| `report_generator.py` | Generates HTML/JSON reports of test results |

---

## 12. Operator Configuration — `titan.env`

All operator-specific configuration lives in `/opt/titan/config/titan.env`. This file is loaded by `titan_env.py` at startup.

### 12.1 Configuration Sections

| Section | Variables | Purpose |
|---------|-----------|---------|
| **Cloud Brain** | `TITAN_CLOUD_URL`, `TITAN_CLOUD_API_KEY`, `TITAN_CLOUD_MODEL` | vLLM endpoint for cognitive core |
| **Proxy** | `TITAN_PROXY_PROVIDER`, `TITAN_PROXY_API_KEY`, `TITAN_PROXY_DEFAULT_COUNTRY` | Residential proxy pool |
| **Lucid VPN** | `TITAN_VPN_SERVER_IP`, `TITAN_VPN_UUID`, `TITAN_VPN_REALITY_*`, `TITAN_VPN_TAILSCALE_*` | VLESS+Reality+Tailscale config |
| **Stripe** | `TITAN_STRIPE_API_KEY` | Silent card validation |
| **PayPal** | `TITAN_PAYPAL_CLIENT_ID`, `TITAN_PAYPAL_CLIENT_SECRET` | PayPal validation |
| **Braintree** | `TITAN_BRAINTREE_MERCHANT_ID`, `TITAN_BRAINTREE_*_KEY` | Braintree validation |
| **eBPF** | `TITAN_EBPF_INTERFACE`, `TITAN_EBPF_MODE` | Network shield config |
| **Hardware** | `TITAN_HW_SHIELD_ENABLED`, `TITAN_HW_VENDOR`, `TITAN_HW_MODEL` | Hardware fingerprint overrides |

All values default to `REPLACE_WITH_*` placeholders. The `titan_env.py` module reports which services are configured vs pending.

---

## 13. Repository Structure

```
lucid-titan/
├── iso/                                     # Debian Live ISO build tree
│   ├── auto/config                          # lb config — persistence, grub-efi, bookworm
│   ├── config/
│   │   ├── includes.chroot/opt/titan/       # ═══ V7.0 PRIMARY TREE ═══
│   │   │   ├── core/                        # 43 core modules (43 .py)
│   │   │   │   ├── genesis_core.py          #   Profile forge engine
│   │   │   │   ├── advanced_profile_generator.py  #   500MB+ profile synthesis
│   │   │   │   ├── purchase_history_engine.py     #   Commerce history injection
│   │   │   │   ├── cerberus_core.py         #   Card validation + OSINT
│   │   │   │   ├── cerberus_enhanced.py     #   AVS/BIN/Silent validation
│   │   │   │   ├── kyc_core.py              #   Virtual camera controller
│   │   │   │   ├── kyc_enhanced.py          #   Doc injection + liveness
│   │   │   │   ├── integration_bridge.py    #   Module unification
│   │   │   │   ├── preflight_validator.py   #   12-check pre-op validation
│   │   │   │   ├── target_intelligence.py   #   29 targets + 16 antifraud
│   │   │   │   ├── target_presets.py        #   Operation playbooks per target
│   │   │   │   ├── ghost_motor_v6.py        #   DMTG trajectories
│   │   │   │   ├── cognitive_core.py        #   Cloud Brain client (vLLM)
│   │   │   │   ├── quic_proxy.py            #   QUIC transparent proxy
│   │   │   │   ├── proxy_manager.py         #   Residential proxy pool
│   │   │   │   ├── fingerprint_injector.py  #   Canvas/WebGL/Audio + NetlinkHWBridge
│   │   │   │   ├── form_autofill_injector.py #  SQLite autofill injection
│   │   │   │   ├── referrer_warmup.py       #   Navigation chain gen
│   │   │   │   ├── handover_protocol.py     #   5-phase post-checkout
│   │   │   │   ├── three_ds_strategy.py     #   3DS handling
│   │   │   │   ├── lucid_vpn.py             #   VLESS+Reality VPN manager
│   │   │   │   ├── location_spoofer_linux.py #  GPS/TZ/WiFi alignment
│   │   │   │   ├── kill_switch.py           #   Panic + evidence wipe
│   │   │   │   ├── font_sanitizer.py        #   Phase 3: font shield
│   │   │   │   ├── audio_hardener.py        #   Phase 3: AudioContext + jitter seed
│   │   │   │   ├── timezone_enforcer.py     #   Phase 3: timezone atomicity
│   │   │   │   ├── verify_deep_identity.py  #   Deep identity leak check
│   │   │   │   ├── titan_master_verify.py   #   4-layer MVP gate
│   │   │   │   ├── generate_trajectory_model.py  #  DMTG model training
│   │   │   │   ├── titan_env.py             #   Config loader (titan.env)
│   │   │   │   ├── hardware_shield_v6.c     #   Kernel HW injection (Netlink)
│   │   │   │   ├── network_shield_v6.c      #   eBPF XDP + QUIC proxy
│   │   │   │   ├── build_ebpf.sh            #   eBPF compile + load script
│   │   │   │   ├── Makefile                 #   Kernel module build
│   │   │   │   └── __init__.py              #   80+ exports
│   │   │   ├── apps/                        # PyQt6 GUI apps
│   │   │   │   ├── app_unified.py           #   MAIN: 4-tab Operation Center
│   │   │   │   ├── app_genesis.py           #   Standalone Genesis
│   │   │   │   ├── app_cerberus.py          #   Standalone Cerberus
│   │   │   │   └── app_kyc.py               #   Standalone KYC
│   │   │   ├── bin/                         # Launchers + tools
│   │   │   │   ├── titan-browser            #   Camoufox launcher (552 lines)
│   │   │   │   ├── titan-launcher           #   dmenu/rofi launcher
│   │   │   │   ├── titan-first-boot         #   First boot setup (11 checks)
│   │   │   │   ├── titan-vpn-setup          #   VPN configuration wizard
│   │   │   │   ├── titan-test               #   CLI test runner
│   │   │   │   └── install-to-disk          #   VPS disk installer
│   │   │   ├── vpn/                         # Lucid VPN infrastructure
│   │   │   │   ├── xray-client.json         #   VLESS+Reality client config
│   │   │   │   ├── xray-server.json         #   VLESS+Reality server template
│   │   │   │   ├── setup-vps-relay.sh       #   VPS relay setup (7-step)
│   │   │   │   └── setup-exit-node.sh       #   Residential exit node setup
│   │   │   ├── testing/                     # Test framework
│   │   │   │   ├── test_runner.py           #   Test orchestrator
│   │   │   │   ├── detection_emulator.py    #   Antifraud simulation
│   │   │   │   ├── environment.py           #   Environment validation
│   │   │   │   ├── psp_sandbox.py           #   PSP sandbox testing
│   │   │   │   └── report_generator.py      #   HTML/JSON reports
│   │   │   ├── config/titan.env             # Operator configuration
│   │   │   ├── extensions/ghost_motor/      # Browser extension
│   │   │   │   ├── ghost_motor.js           #   Behavioral biometrics
│   │   │   │   └── manifest.json
│   │   │   ├── assets/motions/              # KYC motion videos
│   │   │   ├── state/                       # Runtime state (profiles, certs)
│   │   │   └── build.sh                     # In-chroot build helper
│   │   ├── includes.chroot/opt/lucid-empire/  # ═══ LEGACY INFRA ═══
│   │   │   ├── backend/                     #   FastAPI backend + modules
│   │   │   │   ├── server.py                #   API server (:8000)
│   │   │   │   ├── validation/              #   Forensic validators
│   │   │   │   ├── modules/                 #   Commerce, fingerprint, etc.
│   │   │   │   ├── network/                 #   eBPF loader, XDP, TLS
│   │   │   │   └── core/                    #   Profile store, genesis, fonts
│   │   │   ├── bin/                         #   Systemd service scripts
│   │   │   │   ├── titan-backend-init.sh    #   Boot init (kernel + backend)
│   │   │   │   └── load-ebpf.sh             #   eBPF network shield loader
│   │   │   ├── ebpf/                        #   eBPF source (network_shield.c)
│   │   │   ├── hardware_shield/             #   DKMS kernel module source
│   │   │   └── camoufox/                    #   Browser settings
│   │   ├── includes.chroot/etc/             # ═══ RING 2 OS HARDENING CONFIGS ═══
│   │   │   ├── nftables.conf                #   Default-deny firewall (TCP 80/443/853, UDP 443/51820)
│   │   │   ├── fonts/local.conf             #   Reject Linux fonts, substitute Windows equivalents
│   │   │   ├── pulse/daemon.conf            #   44100Hz sample rate (Windows CoreAudio match)
│   │   │   ├── sysctl.d/99-titan-hardening.conf  # ASLR, ptrace, IPV7.0.3 off, BBR congestion
│   │   │   ├── NetworkManager/conf.d/10-titan-privacy.conf  # MAC randomization
│   │   │   ├── systemd/journald.conf.d/titan-privacy.conf   # Volatile-only logging
│   │   │   ├── systemd/coredump.conf.d/titan-no-coredump.conf  # No core dumps
│   │   │   ├── unbound/unbound.conf         #   DNS-over-TLS (Cloudflare + Quad9)
│   │   │   ├── sudoers.d/titan-ops          #   Passwordless sudo for modprobe, nft, ip
│   │   │   ├── polkit-1/.../10-titan-nopasswd.pkla  # No password for systemd/NM
│   │   │   ├── lightdm/lightdm.conf         #   Auto-login as 'user'
│   │   │   ├── udev/rules.d/99-titan-usb.rules  # USB device filtering
│   │   │   └── systemd/system/              #   Systemd services
│   │   │       ├── lucid-titan.service      #     Backend + kernel modules
│   │   │       ├── lucid-ebpf.service       #     eBPF network shield
│   │   │       ├── lucid-console.service    #     GUI autostart
│   │   │       ├── titan-dns.service        #     DNS resolver lock
│   │   │       └── titan-first-boot.service #     One-time first boot
│   │   ├── includes.chroot/usr/lib/firefox-esr/defaults/pref/
│   │   │   └── titan-hardening.js           #   WebRTC off, telemetry off, battery off
│   │   ├── hooks/live/                      # 7 ISO build hooks
│   │   │   ├── 050-hardware-shield.hook.chroot  # Compile titan_hw.ko
│   │   │   ├── 060-kernel-module.hook.chroot    # DKMS register + install
│   │   │   ├── 070-camoufox-fetch.hook.chroot   # Download Camoufox browser
│   │   │   ├── 080-ollama-setup.hook.chroot     # ML/AI pip dependencies
│   │   │   ├── 090-kyc-setup.hook.chroot        # v4l2loopback + deepfake
│   │   │   ├── 095-os-harden.hook.chroot        # Service disable, module blacklist, crash suppress
│   │   │   └── 99-fix-perms.hook.chroot         # Final perms, pip, symlinks, systemd enable
│   │   └── package-lists/custom.list.chroot #   234-line APT package list
├── scripts/                                 # Build & utility scripts
│   ├── build_iso.sh                         #   V7.0 ISO builder (9 phases, 680 lines)
│   ├── deploy_titan_v6.sh                   #   Deployment automation
│   └── install_to_disk.sh                   #   VPS installer (standalone)
├── titan/                                   # Standalone kernel/eBPF source
│   ├── hardware_shield/                     #   titan_hw.c, titan_battery.c, Makefile, dkms.conf
│   ├── ebpf/                                #   network_shield.c, tcp_fingerprint.c, loader
│   └── mobile/                              #   waydroid_hardener.py
├── titan_v6_cloud_brain/                    # Cloud Brain infrastructure
│   └── docker-compose.yml                   #   vLLM + nginx + Redis + Prometheus + Grafana
├── .github/workflows/                       # CI/CD pipelines
│   ├── build-iso.yml
│   ├── test-modules.yml
│   └── v6_iso_build.yml
├── docs/                                    # 23 documentation files
│   ├── Operationalizing Titan V7.0 System.txt  # Master operational spec
│   ├── ARCHITECTURE.md                      #   System architecture reference
│   ├── QUICKSTART_V6.md                     #   Quick start guide
│   └── archive/                             #   Historical audit reports
├── profgen/                                 # V7.0 profile generator (6 modules)
│   ├── config.py                            #   Persona, domains, fingerprint seeds, anti-detect funcs
│   ├── gen_places.py                        #   places.sqlite (2000+ visits, from_visit chains)
│   ├── gen_cookies.py                       #   cookies.sqlite (76+ cookies, 17 sites)
│   ├── gen_storage.py                       #   localStorage (500MB+, 15 domains)
│   ├── gen_formhistory.py                   #   formhistory.sqlite (50+ entries)
│   └── gen_firefox_files.py                 #   17 additional profile files
├── simulation/                              # Interactive HTML GUI demo
│   ├── index.html                           #   Demo dashboard
│   ├── js/titan-app.js, titan-modules.js
│   └── css/titan.css
├── TITAN_COMPLETE_BLUEPRINT.md              # 1600+ line complete system blueprint
└── README.md                                # ← This file
```

---

## 14. Build & Deployment

### Prerequisites
- Debian 12 Bookworm or Ubuntu 22.04+ (x86_64), 15GB+ disk, root privileges

### Build ISO (Live USB)
```bash
git clone https://github.com/codybrady96-netizen/lucid-titan.git
cd lucid-titan
sudo bash scripts/build_iso.sh
# 9-phase build: deps → verify → eBPF → HW shield → DKMS → layout → capability → lb build → collect
# Output: lucid-titan-v7.0.3-singularity.iso + .sha256

# Write to USB:
sudo bash scripts/write_usb.sh /dev/sdX
```

### Clone & Configure (C&C) Migration (NEW - Recommended for VPS)
The C&C method transforms a standard Debian 12 VPS into a Titan Singularity Node via a 100% automated, stealthy migration.

```bash
# 1. Download and run deployment script
wget https://raw.githubusercontent.com/YOUR_REPO/titan-main/deploy_vps.sh
chmod +x deploy_vps.sh
sudo ./deploy_vps.sh

# 2. Run automated migration
sudo titan-migrate
```
*See `docs/BUILD_AND_DEPLOY_GUIDE.md` (Phase E) for full details.*

### Build VPS/RDP Image (Persistent Install)
```bash
sudo bash scripts/build_vps_image.sh
# Options: --size 30G --format qcow2 --root-pass YOUR_PASSWORD
# Output: lucid-titan-v7.0.3-singularity.qcow2 + .sha256
#
# Deploy to VPS:
#   Vultr/Kamatera: Upload as custom image
#   Hetzner/OVH:    Rescue mode → dd if=image.raw of=/dev/sda bs=4M
#   DigitalOcean:   Custom Images → Upload qcow2
#   AWS:            aws ec2 import-image
```

### Boot & Configure
```bash
# After booting from USB/VM/VPS:
# titan-first-boot runs automatically (11-step readiness check)
# Then edit operator config:
nano /opt/titan/config/titan.env              # Set proxy (REQUIRED), VPN, API keys
python3 /opt/titan/apps/app_unified.py        # Launch 7-tab Unified GUI
```

### VPN Setup (Optional but Recommended)
```bash
# On VPS (Ubuntu 22.04):
bash setup-vps-relay.sh                       # Installs Xray, Tailscale, hardens
# Copy credentials from /root/titan-vpn-credentials.txt → titan.env

# On residential box (exit node):
sudo bash setup-exit-node.sh YOUR_TAILSCALE_AUTH_KEY
```

### Cloud Brain Setup
```bash
cd titan_v6_cloud_brain/
export HF_TOKEN=your_huggingface_token
docker-compose up -d
# Services: vLLM (70B + 7B lite), nginx gateway, Redis, Prometheus, Grafana
```

---

## 15. API Quick Reference

```python
# ─── GENESIS ────────────────────────────────────────
from titan.core import GenesisEngine, ProfileConfig
from titan.core import AdvancedProfileGenerator, AdvancedProfileConfig
from titan.core import inject_purchase_history

# ─── CERBERUS ───────────────────────────────────────
from titan.core import CerberusValidator, CardAsset
from titan.core import check_avs, score_bin, get_silent_strategy, check_geo

# ─── KYC ────────────────────────────────────────────
from titan.core import KYCController, KYCEnhancedController
from titan.core import create_kyc_session, LivenessChallenge

# ─── INTEGRATION ────────────────────────────────────
from titan.core import TitanIntegrationBridge, create_bridge
from titan.core import PreFlightValidator
from titan.core import FingerprintInjector, create_injector
from titan.core import NetlinkHWBridge                       # Ring 0 ↔ Ring 3 sync
from titan.core import ReferrerWarmup, create_warmup_plan
from titan.core import GhostMotorDiffusion
from titan.core import KillSwitch                            # Automated panic sequence
from titan.core import LucidVPN, VPNConfig
```

---

## 16. Phase 2-3: Hardening & Environment Shields

V7.0 added three layers of environmental hardening that run **before** browser launch. These eliminate fingerprint leaks that older versions missed.

### 16.1 Where The Code Lives

| Module | File | What It Does |
|--------|------|-------------|
| **Font Sanitizer** | `core/font_sanitizer.py` | Phase 3.1 — Rejects Linux-only fonts via `/etc/fonts/local.conf`, installs target OS fonts, spoofs `measureText()` metrics via Ghost Motor |
| **Audio Hardener** | `core/audio_hardener.py` | Phase 3.2 — Deterministic jitter seed via SHA-256(profile_uuid), seeded Gaussian noise injection, PulseAudio 44100Hz masking, RFP enforcement |
| **Timezone Enforcer** | `core/timezone_enforcer.py` | Phase 3.3 — Atomic sequence: kill switch → VPN connect → NTP sync → verify → set TZ env vars → launch |
| **Kill Switch** | `core/kill_switch.py` | Phase 2 — Emergency connection kill, ARM/DISARM/PANIC modes |
| **Deep Identity Verifier** | `core/verify_deep_identity.py` | Post-hardening leak check — returns GHOST (clean) or FLAGGED (leak detected) |
| **Master Verification** | `core/titan_master_verify.py` | 4-layer MVP: Kernel → Network → Environment → Identity, mandatory pre-launch gate |

### 16.2 How They Wire Into The Launch

The `titan-browser` script (`bin/titan-browser`) runs this sequence:

```
1. titan_master_verify.py  → 4-layer Go/No-Go check
2. verify_deep_identity.py → Font/Audio/TZ leak detection
3. If FLAGGED → operator gets override prompt
4. If GHOST → browser launches with all shields active
```

### 16.3 ISO Build Hook Integration

File: `iso/config/hooks/live/99-fix-perms.hook.chroot`

This hook runs at ISO build time to:
- Install `aioquic` + `pytz` pip deps
- Run `font_sanitizer.py` to generate `/etc/fonts/local.conf` with Linux font rejection rules
- `chmod +x` all Phase 2-3 module scripts

**To update:** If you add a new hardening module, add its `chmod +x` line to this hook and export it in `core/__init__.py`.

---

## 17. GUI Application — Unified Operation Center

V7.0.3 consolidates all capabilities into **one app** with 8 tabs. No separate apps needed.

### 17.1 `app_unified.py` — 8 Tabs

| Tab | What It Does |
|-----|-------------|
| **OPERATION** | Target selection (35 presets), proxy config, card validation (Cerberus), profile generation (Genesis), browser launch, handover protocol |
| **INTELLIGENCE** | 8 sub-tabs: AVS, Visa Alerts, Card Freshness, Fingerprint Tools, PayPal Defense, 3DS v2, Proxy/DNS, Target Intel |
| **SHIELDS** | Pre-flight validator, Environment hardening (font/audio/timezone), Kill switch, OSINT/Card quality grading, Purchase history injection |
| **KYC** | Virtual camera controller — load face image, select motion, start/stop stream to `/dev/video` |
| **HEALTH** | Real-time system monitor (CPU/RAM/tmpfs), privacy service status (kernel module, eBPF, DNS, VPN, PulseAudio) |
| **FORENSIC** | Real-time system forensic analysis, suspicious activity detection, privacy service deep checks |
| **TX MONITOR** | 24/7 transaction capture via browser extension, decline code decoder, per-site/BIN analytics, live success rate stats |
| **DISCOVERY** | 4 sub-tabs: Auto-Discovery (Google dorking + site classification), 3DS Bypass scoring, Non-VBV BIN recommendations (100+ BINs, 28 countries), Background Services management |

### 17.2 Desktop Entries (3 Icons)

| File | Desktop Icon | Launches |
|------|-------------|----------|
| `titan-unified.desktop` | **TITAN V7.0 — Operation Center** | `python3 /opt/titan/apps/app_unified.py` |
| `titan-browser.desktop` | **Titan Browser** | `bash /opt/titan/bin/titan-browser` |
| `titan-install.desktop` | **Install to Disk** | VPS/bare metal disk installer |

### 17.3 Services & Autostart

| File | What It Does |
|------|-------------|
| `etc/xdg/autostart/lucid-titan-console.desktop` | Auto-launches `app_unified.py` on desktop login |
| `etc/systemd/system/lucid-console.service` | Runs `app_unified.py` as systemd service (user session) |
| `etc/systemd/system/lucid-titan.service` | Runs `titan-backend-init.sh` (kernel modules + backend API) |
| `etc/systemd/system/lucid-ebpf.service` | Loads eBPF network shield |
| `etc/systemd/system/titan-first-boot.service` | One-time first boot setup (11 verification checks) |

**To update:** If you rename the GUI file or change its path, update `titan-unified.desktop`, `lucid-titan-console.desktop` (autostart), and `lucid-console.service`.

---

## 18. Legacy Infrastructure (lucid-empire)

The `/opt/lucid-empire` tree retains **infrastructure only** — all user-facing code has been removed and consolidated into `/opt/titan/`. The legacy tree exists because systemd services and boot scripts reference it.

### 18.1 What Remains (Infrastructure Only)

| Path | Purpose |
|------|---------|
| `backend/server.py` | FastAPI backend API on `:8000` (health, profiles, validation) |
| `backend/lucid_api.py` | Backend API bridge (imports V7.0 core modules) |
| `backend/validation/` | Forensic validation endpoints |
| `backend/modules/` | Commerce, fingerprint, ghost motor, location modules |
| `backend/core/` | Profile store, genesis engine, cortex, temporal control |
| `bin/titan-backend-init.sh` | Boot-time init (kernel modules, dirs, FastAPI start) |
| `bin/load-ebpf.sh` | eBPF network shield loader |
| `ebpf/` | eBPF source + compiled bytecode |
| `hardware_shield/` | DKMS kernel module source |
| `camoufox/` | Browser settings |
| `launch-titan.sh` | Backward-compat shim → redirects to `app_unified.py` |

### 18.2 What Was Removed (V7.0 Cleanup)

These files were superseded by V7.0 `/opt/titan/` modules and deleted:

- `TITAN_CONSOLE.py` → superseded by `app_unified.py`
- `lucid_unified_panel.py` → superseded by `app_unified.py`
- `lucid_genesis_engine.py` → superseded by `genesis_core.py`
- `lucid_firefox_injector.py` → superseded by `fingerprint_injector.py`
- `browser_verify_profile.py` → superseded by `verify_deep_identity.py`
- `launch_lucid_browser.py` → superseded by `titan-browser`
- `verify_*.py` (4 files) → superseded by `titan_master_verify.py`
- `titan_core.py` → superseded by `core/__init__.py`
- `tests/` + `scripts/` → superseded by V7.0 testing module

---

## 19. How To: Common Update Tasks

### Add a new core module

1. Create `iso/config/includes.chroot/opt/titan/core/your_module.py`
2. Export it in `core/__init__.py` (add to imports and `__all__`)
3. Add `chmod +x` in `iso/config/hooks/live/99-fix-perms.hook.chroot`
4. If it has a GUI panel, add it to `app_unified.py` SHIELDS tab

### Add a new target to the intelligence database

1. Edit `core/target_intelligence.py` — add entry to `TARGET_DB`
2. Add purchase history template in `core/purchase_history_engine.py` if the target is a merchant
3. Update the target dropdown in `apps/app_unified.py`

### Change version strings

All version strings are `V7.0` / `7.0.0` across the entire codebase. If you bump versions, update:
- `core/__init__.py` (`__version__`)
- `titan-browser` (`TITAN_VERSION` export + banner)
- `titan-launcher` (zenity title)
- All `.desktop` files in `usr/share/applications/`
- All `.service` files in `etc/systemd/system/`
- `titan-backend-init.sh` banner
- `.github/workflows/build-iso.yml` (ISO_NAME, DKMS version, release notes)
- `README.md` badges + header

### Add a pip dependency

1. Add to `iso/config/hooks/live/99-fix-perms.hook.chroot` in the pip install section
2. If it's a system package, add to `iso/config/package-lists/custom.list.chroot`

### Add a new capability

Prefer adding a new **tab** or **sub-tab** in `app_unified.py` instead of creating a separate app. This keeps the zero-terminal UX with one consolidated GUI.

### Build & Deploy to VPS (Primary — No Live ISO Needed)

```bash
# Build a VPS-ready disk image directly from the repo:
sudo bash scripts/build_vps_image.sh
# Options:
#   --size 30G          (default: 20G)
#   --format qcow2      (default: both raw+qcow2)
#   --root-pass MyPass   (default: titan)
#   --no-vnc             (skip VNC server)

# Output:
#   lucid-titan-v7.0-singularity.raw     (for dd to VPS disk)
#   lucid-titan-v7.0-singularity.qcow2   (for DigitalOcean/Vultr upload)

# Deploy Option A: dd (Hetzner/OVH rescue mode)
scp lucid-titan-v7.0-singularity.raw root@VPS:/tmp/
ssh root@VPS 'dd if=/tmp/lucid-titan-v7.0-singularity.raw of=/dev/sda bs=4M status=progress'

# Deploy Option B: Custom Image Upload (DigitalOcean/Vultr)
# Upload .qcow2 via provider dashboard → Create droplet from image

# Deploy Option C: Test locally with QEMU
qemu-system-x86_64 -m 4096 -enable-kvm \
    -drive file=lucid-titan-v7.0-singularity.qcow2,format=qcow2 \
    -net nic -net user,hostfwd=tcp::2222-:22,hostfwd=tcp::5901-:5901

# After boot:
#   SSH:  ssh root@<VPS_IP>    (password: titan — CHANGE IMMEDIATELY)
#   VNC:  <VPS_IP>:5901        (password: titan)
#   GUI:  Auto-launches via VNC desktop session
```

### Build Live ISO (Legacy — USB boot only)

```bash
# Only if you need a USB-bootable live ISO:
sudo bash scripts/build_iso.sh
```

### Update Cloud Brain

1. Edit `titan_v6_cloud_brain/docker-compose.yml`
2. Update `titan_v6_cloud_brain/prometheus.yml` if adding monitoring targets
3. Update `core/cognitive_core.py` client if API changes

---

## 20. v7.0.3 Intelligence & Operational Modules

These modules were added in v7.0.3 to maximize real-world operational success rates:

| Module | File | Purpose |
|--------|------|---------|
| **MaxDrain Engine** | `cerberus_enhanced.py` | Auto-generates optimal multi-step extraction plans after CC validation (4 phases, 5 categories, 13 bank velocity profiles) |
| **Non-VBV Recommendations** | `three_ds_strategy.py` | 60+ BINs across 13 countries ranked by 3DS avoidance probability |
| **Bank Pattern Predictor** | `cerberus_enhanced.py` | Predicts issuing bank approve/decline before attempting transaction |
| **Target Discovery** | `target_discovery.py` | 150+ curated merchant sites across 12 categories with auto-probe PSP/fraud/3DS detection + daily health check |
| **Intel Monitor** | `intel_monitor.py` | Monitors 16 forums/shops/channels for new vectors (manual login + auto-engagement) |
| **Cognitive Timing** | `ghost_motor.js` | Field familiarity typing, page attention, scroll reading, idle injection |
| **IP Reputation** | `preflight_validator.py` | 3-tier IP scoring (Scamalytics + IPQS + ip-api) before session starts |

**Full feature reference with every technique explained:** `Final/V7_COMPLETE_FEATURE_REFERENCE.md`

---

## 21. Executive Whitepaper & Complete Blueprint

For the strategic intelligence assessment, see **`Final/V7_EXECUTIVE_WHITEPAPER.md`** — covers the doctrine of Synthetic Sovereignty, Seven-Layer Defense Model, success rate formula, and operational dynamics.

For a deep-dive into every component, technique, and data structure, see **`TITAN_COMPLETE_BLUEPRINT.md`** (1,600+ lines). It covers:

| Section | Content |
|---------|---------|
| **Full Repo Tree** | Every file and directory in the repository |
| **Five Rings Architecture** | How Ring 0 (kernel) through Ring 4 (profile data) interconnect |
| **Profile Generation** | All 6 profgen modules: config seeds, places.sqlite schema, 76+ cookies, 500MB+ localStorage, formhistory, 17 Firefox files |
| **Core Modules** | All 43 modules with technique details: NetlinkHWBridge, DMTG diffusion, cloud vLLM + Ollama fallback, kill switch panic sequence |
| **Zero-Detection Techniques** | 35+ detection vectors across 6 layers with specific countermeasures |
| **Kernel Spoofing** | DKOM procfs, Netlink protocol 31, DKMS build, module hiding |
| **eBPF Network Stack** | XDP packet rewriting, p0f/JA3/JA4 masquerade, QUIC proxy pipeline |
| **OS Hardening** | All etc/ overlay configs: nftables, fontconfig, PulseAudio, sysctl, journald, coredump |
| **ISO Build System** | 5-stage build chain, 7 hooks, 280 packages, systemd services, verify_iso.sh |
| **Operational Workflow** | 4-phase operation from profile creation to post-op cleanup |
| **Rebuild Guide** | 10-step instructions to reconstruct the entire system from scratch |

```bash
# View the blueprint:
cat TITAN_COMPLETE_BLUEPRINT.md
```

---

## License

GNU General Public License v3.0

## Disclaimer

This software is provided for **educational and research purposes only**. The authors do not condone or support any illegal activities. Users are responsible for ensuring compliance with all applicable laws and terms of service.

---

**Authority:** Dva.12 | **Version:** 8.1 SINGULARITY | **Codename:** MAXIMUM_LEVEL


