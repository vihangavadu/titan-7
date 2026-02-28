# Multilogin 6 vs Titan OS Genesis Engine — Reverse Engineering Comparison

**Date:** Feb 27, 2026
**ML6 Version:** 6.5.0 (Linux x86_64 .deb)
**Titan Version:** V8.1+ Genesis Core (genesis_core.py, 2757 lines)

---

## 1. Architecture Overview

| Aspect | Multilogin 6 | Titan OS Genesis |
|--------|-------------|-----------------|
| **Language** | TypeScript/JavaScript (Electron + Angular) | Python (PyQt5 GUI + Flask API) |
| **Platform** | Cross-platform desktop app (Win/Mac/Linux) | Linux-native (Titan OS / Debian) |
| **UI Framework** | Angular (renderer), Electron (shell) | PyQt5 (desktop), Flask (web API) |
| **Backend** | Java "Indigo" headless browser engine + Express.js local API | Python core modules + Ollama AI |
| **Browser Engine** | Custom Chromium fork ("Mimic") + Custom Firefox fork ("Stealthfox") | Camoufox (Firefox fork) + standard Chromium |
| **Profile Storage** | Cloud-synced (Multilogin servers) + local cache | Local filesystem (`/opt/titan/profiles/`) |
| **API** | REST API on `localhost:35000` (Express.js) | REST API via `titan_api.py` (Flask) |
| **Package Size** | ~312MB (.deb), 230MB Electron binary + 230MB app.asar | ~60MB total codebase (Python) |
| **Licensing** | SaaS subscription (cloud account required) | Self-hosted, no external dependency |

---

## 2. Multilogin 6 — Internal Architecture (Reverse Engineered)

### 2.1 Process Architecture
```
multilogin (Electron main process)
  ├── bundle.js          — Main process: config, IPC, window management, headless orchestration
  ├── express-server.js  — Local REST API server (Express.js on localhost:35000)
  ├── preload.js         — Renderer bridge (IPC channels, theme, platform detection)
  ├── zombie-killer.js   — Process cleanup daemon (kills orphaned browser/proxy processes)
  └── renderer/          — Angular SPA (profile management UI)
       ├── main.js       — Angular app (components, services, routing)
       ├── vendor.js     — Angular framework + dependencies (2MB)
       └── common.js     — Shared utilities
```

### 2.2 Headless Browser Engine ("Indigo")
- **Binary:** `/opt/Multilogin/headless/multilogin` (230MB) — separate Chromium-based engine
- **Config:** `~/.indigobrowser/app.properties` (Java properties format)
- **Logs:** `~/.indigobrowser/log/multiloginapp_log.log`
- **CLI:** `/opt/Multilogin/headless/cli.sh` — headless profile operations
- **Headless mode:** `/opt/Multilogin/headless/headless.sh` — runs without GUI
- **Watchdog:** Monitors headless health with 10s ping interval, auto-restarts on failure
- **Zombie Killer:** Separate process that kills orphaned browser and proxy PIDs

### 2.3 Browser Types
| Browser | Internal Name | Base Engine | Purpose |
|---------|--------------|-------------|---------|
| Mimic | `mimic` (enum=5) | Chromium fork | Primary anti-detect browser |
| Mimic Mobile | `mimic_mobile` (enum=6) | Chromium mobile | Mobile emulation |
| Stealthfox | `stealthfox` (enum=4) | Firefox fork | Firefox fingerprint |

### 2.4 Local API (Express Server)
Discovered endpoints from renderer code:
- `GET /version` — App version
- `GET /browser-cores-version` — Browser engine versions
- `GET /bridge/apiToken` — Auth token
- `GET /bridge/os` — OS detection
- `GET /bridge/events` — Event stream (SSE)
- `GET /bridge/error` — Error reporting
- `GET /bridge/log` — Logging
- `GET /bridge/connectionSettings` — Network config
- `GET /bridge/availableSystemFonts` — Font enumeration
- `GET /bridge/persistentFonts` — Persistent font list
- `GET /bridge/onToken` — Token events
- `GET /bridge/signOut` — Sign out
- `GET /bridge/startSection` — Section navigation
- `GET /bridge/browserTypeVersions` — Available browser versions
- `GET /bridge/isProfileExperimentalFeaturesEnabled` — Feature flags
- `GET /bridge/isShowRegistrationBlock` — Registration gate
- `GET /systemScreenResolution` — Screen resolution detection
- `GET /download-browser-core/{type}` — Download browser engine
- `GET /clb/p/{id}/migrate` — Profile migration
- `GET /msgs/startup/i18n` — Localization messages
- `POST /rest/ui/v1/group/profile/list` — List profiles in group

### 2.5 Cloud API Endpoints
- `GET /rest/ui/v1/global-config?osType={os}` — Global configuration
- `GET /rest/v1/plans/current` — Current subscription plan
- `GET /uaa/rest/v1/lastNotifiedVersion` — Version check
- `GET /uaa/rest/v1/u/billing-url` — Billing portal URL
- Migration API for account transfers

### 2.6 Fingerprint Spoofing Categories
From renderer analysis, ML6 manages these fingerprint vectors:
- **NAVIGATOR** — User-Agent, platform, vendor, languages, plugins
- **SCREEN** — Resolution, color depth
- **WEBGL** — WebGL vendor/renderer strings
- **WEBGL2** — WebGL2 parameters
- **WEBRTC** — WebRTC leak protection
- **FONTS** — System font list spoofing + random font generation
- **LANGUAGES** — Accept-Language header
- **Geolocation** — GPS coordinate spoofing
- **Timezone** — Timezone spoofing
- **Canvas** — Canvas fingerprint noise
- **Audio** — AudioContext fingerprint
- **Plugins** — Browser plugin list

### 2.7 Profile Management Features
- Create/Edit/Clone/Delete profiles
- Group/Folder organization with team sharing
- Profile transfer between accounts
- Cookie import/export
- Proxy configuration per profile (HTTP/SOCKS)
- Profile status monitoring (active sessions)
- Pinned groups / favorites
- Legacy profile migration
- Profile fingerprint generation (`generateRealProfileFingerprint`)

### 2.8 IPC Channels (Electron)
- `app-ready` — App initialization complete
- `config-change` — Configuration updates
- `proxy-authorization` — Proxy auth flow
- `set-cookie` — Cookie injection
- `update-title` — Window title updates

### 2.9 UI Routes (Angular)
- `/login` — Authentication
- `/signup` — Registration
- `/forgot` / `/reset` — Password recovery
- `/profile` — Profile list/dashboard
- `/profile/:sid` — Individual profile editing
- `/migration` — Account migration
- `/confirm` — Email confirmation
- `/lang-switch` — Language switching
- `/not-found` — 404 page

---

## 3. Titan OS Genesis Engine — Architecture

### 3.1 Core Components
```
genesis_core.py (2757 lines)
  ├── GenesisEngine              — Main profile forge engine
  ├── OSConsistencyValidator     — Cross-signal consistency enforcement
  ├── TargetPreset               — Pre-configured target site profiles (14 targets)
  ├── ProfileArchetype           — Behavioral archetypes (5 types)
  ├── ProfileConfig              — Profile generation configuration
  ├── GeneratedProfile           — Output profile data structure
  ├── pre_forge_validate()       — BIN-aware pre-validation
  └── score_profile_quality()    — Profile readiness scoring

Supporting modules:
  ├── fingerprint_injector.py    — Browser fingerprint injection
  ├── canvas_noise.py            — Canvas fingerprint noise generation
  ├── canvas_subpixel_shim.py    — Subpixel rendering shimming
  ├── oblivion_setup.py          — Oblivion anti-detect template setup
  ├── oblivion_forge.py          — Oblivion profile forging
  ├── form_autofill_injector.py  — Form autofill data injection
  ├── advanced_profile_generator.py — "Golden Ticket" 500MB+ profile generator
  ├── target_intelligence.py     — Target site intelligence database
  └── ai_intelligence_engine.py  — AI-powered validation (21 functions)
```

### 3.2 Profile Generation Pipeline
1. **Pre-forge validation** — BIN/card level vs hardware consistency check
2. **Profile ID generation** — SHA256-based deterministic IDs
3. **Browser history generation** — Pareto distribution + circadian rhythm weighting
4. **Cookie generation** — Trust anchor cookies (Google, Facebook, Stripe, PSPs)
5. **LocalStorage generation** — Multi-PSP trust tokens (Stripe, PayPal, Adyen, Braintree, Shopify, Klarna, Amazon, Square)
6. **Hardware fingerprint** — 10 hardware profiles (Windows/Mac/Linux, multiple tiers)
7. **Firefox profile writing** — places.sqlite, cookies.sqlite, prefs.js with forensic-grade schemas
8. **Chromium profile writing** — History, Cookies, Web Data databases with Chrome epoch timestamps
9. **V7.6 P0 components** — Site Engagement scores, Notification permissions, Bookmarks, Favicons, Download history, Web Data/Autofill
10. **Autofill injection** — FormAutofillInjector for "Use saved card?" prompt
11. **Integration** — Location spoofing, Commerce vault tokens, Canvas noise seeds
12. **Handover document** — Human operator execution instructions
13. **Profile quality scoring** — Go/No-Go readiness assessment

### 3.3 Target Presets (14 built-in)
| Target | Domain | Category | Age (days) | Browser |
|--------|--------|----------|-----------|---------|
| Amazon US | amazon.com | ecommerce | 90 | Firefox |
| Amazon UK | amazon.co.uk | ecommerce | 90 | Firefox |
| Eneba Gift | eneba.com | gift_cards | 60 | Chromium |
| G2A Gift | g2a.com | gift_cards | 45 | Chromium |
| Steam Wallet | steampowered.com | gaming | 120 | Firefox |
| Coinbase | coinbase.com | crypto | 180 | Chromium |
| Best Buy | bestbuy.com | ecommerce | 60 | Chromium |
| Newegg | newegg.com | ecommerce | 45 | Firefox |
| StockX | stockx.com | ecommerce | 90 | Chromium |
| Netflix | netflix.com | streaming | 30 | Firefox |
| MyGiftCardSupply | mygiftcardsupply.com | gift_cards | 60 | Firefox |
| Dundle | dundle.com | gift_cards | 60 | Firefox |
| Shop.app | shop.app | ecommerce | 45 | Chromium |
| Eneba Keys | eneba.com | gaming | 60 | Firefox |

### 3.4 Profile Archetypes (5 types)
| Archetype | Age Range | Hardware | Key Domains |
|-----------|-----------|----------|-------------|
| Student Developer | 20-28 | MacBook Pro | GitHub, Stack Overflow, Coursera |
| Professional | 28-50 | Windows Desktop | LinkedIn, Slack, Salesforce |
| Retiree | 55-75 | Windows Desktop | AARP, WebMD, Medicare |
| Gamer | 18-35 | Windows Desktop | Steam, Twitch, Discord |
| Casual Shopper | 25-55 | Windows Desktop | Amazon, Target, Walmart |

### 3.5 AI-Powered Features (Not in ML6)
Titan integrates 21 AI functions via Ollama models:
- `validate_fingerprint_coherence()` — Cross-signal validation
- `validate_identity_graph()` — Identity plausibility check
- `plan_session_rhythm()` — Realistic session timing
- `score_environment_coherence()` — IP+geo+locale+TZ coherence
- `generate_navigation_path()` — Realistic browse-to-purchase
- `optimize_card_rotation()` — Card-target-amount optimization
- `tune_form_fill_cadence()` — Per-field typing speed
- `schedule_velocity()` — Velocity rate-limit prevention
- `pre_validate_avs()` — AVS format validation
- `track_defense_changes()` — Anti-fraud upgrade detection
- `autopsy_decline()` — Root cause analysis
- `optimize_cross_session()` — Cross-session pattern learning

---

## 4. Feature-by-Feature Comparison

### 4.1 Profile Generation

| Feature | Multilogin 6 | Titan Genesis | Winner |
|---------|-------------|---------------|--------|
| **Browser history** | Basic (via Indigo engine) | Pareto distribution + circadian rhythms, 90+ days | **Titan** |
| **Cookie aging** | Cloud-managed profiles | Forensic-grade SQLite with Firefox PRAGMA, SameSite, schemeMap | **Titan** |
| **Trust anchors** | Not profile-level | Google, Facebook, Stripe, PayPal, Adyen, Braintree, Shopify, Klarna, Amazon, Square tokens | **Titan** |
| **Site Engagement** | Not generated | Chrome Site Engagement DB with logarithmic scoring | **Titan** |
| **Bookmarks** | Manual user creation | Auto-generated archetype-specific bookmark folders | **Titan** |
| **Favicons** | Browser handles | Synthetic favicon database matching history | **Titan** |
| **Download history** | Manual | Auto-generated archetype-specific downloads | **Titan** |
| **Autofill/Web Data** | Manual entry | Auto-injected from persona (name, email, phone, address) | **Titan** |
| **Notification permissions** | Not managed | Pre-configured allow/deny decisions for common sites | **Titan** |
| **Profile quality scoring** | None | Automated Go/No-Go scoring (100-point scale) | **Titan** |

### 4.2 Fingerprint Spoofing

| Feature | Multilogin 6 | Titan Genesis | Winner |
|---------|-------------|---------------|--------|
| **Canvas noise** | Built into Mimic/Stealthfox engine | `canvas_noise.py` + `canvas_subpixel_shim.py` | **ML6** (kernel-level) |
| **WebGL spoofing** | Engine-level (Mimic modifies Chromium) | Hardware profile JSON (applied by Camoufox) | **ML6** (deeper integration) |
| **WebRTC protection** | Built-in leak prevention | Managed via browser config | **ML6** |
| **Font spoofing** | `availableSystemFonts` + `persistentFonts` + random fonts | Via Camoufox configuration | **ML6** (random font generation) |
| **Screen resolution** | Spoofed at engine level | Hardware profile presets (10 profiles) | **Tie** |
| **Navigator properties** | Full browser-level spoofing | Config-based + OSConsistencyValidator | **ML6** (native engine) |
| **Audio fingerprint** | Engine-level noise | Configuration-based | **ML6** |
| **Timezone** | Profile-level spoofing | Locale-aware with billing country sync | **Titan** (geo-coherent) |
| **OS consistency** | Implicit (browser handles) | Explicit `OSConsistencyValidator` with cross-signal checks | **Titan** (documented validation) |

### 4.3 Browser & Runtime

| Feature | Multilogin 6 | Titan Genesis | Winner |
|---------|-------------|---------------|--------|
| **Custom browser engines** | Mimic (Chromium) + Stealthfox (Firefox) | Camoufox (Firefox fork) | **ML6** (two engines) |
| **Mobile emulation** | Mimic Mobile (enum=6) | Via Waydroid Android VM | **Titan** (real Android) |
| **Headless mode** | Full headless with CLI + watchdog | API-driven, no dedicated headless | **ML6** |
| **Automation API** | Selenium/Puppeteer compatible | Python scripting + API | **ML6** (wider ecosystem) |
| **Browser auto-update** | `/download-browser-core/{type}` | Manual Camoufox updates | **ML6** |

### 4.4 Profile Management

| Feature | Multilogin 6 | Titan Genesis | Winner |
|---------|-------------|---------------|--------|
| **Cloud sync** | Yes (Multilogin servers) | No (local only) | **ML6** (if you want cloud) |
| **Team sharing** | Groups, rights, team members | Single-user | **ML6** |
| **Profile cloning** | Built-in | Not explicit | **ML6** |
| **Cookie import/export** | GUI-based import/export | Cookie generation from config | **Titan** (auto-generation) |
| **Target-specific profiles** | Generic profiles | 14 pre-built target presets with detection-aware settings | **Titan** |
| **Archetype narratives** | None | 5 behavioral archetypes with coherent history | **Titan** |
| **BIN-aware optimization** | None | Card-level → hardware mapping, pre-forge validation | **Titan** |

### 4.5 Intelligence & AI

| Feature | Multilogin 6 | Titan Genesis | Winner |
|---------|-------------|---------------|--------|
| **AI integration** | None | 21 AI functions via 3 Ollama models | **Titan** |
| **Target intelligence** | None | Detection-aware profiles per fraud engine | **Titan** |
| **Decline analysis** | None | `autopsy_decline()` AI root cause analysis | **Titan** |
| **Defense tracking** | None | `track_defense_changes()` anti-fraud monitoring | **Titan** |
| **Pre-validation** | None | BIN/billing/hardware/proxy coherence checks | **Titan** |
| **Handover protocol** | None | Detailed human operator execution docs | **Titan** |

### 4.6 Infrastructure

| Feature | Multilogin 6 | Titan Genesis | Winner |
|---------|-------------|---------------|--------|
| **Proxy management** | Per-profile proxy (HTTP/SOCKS) | Per-profile + Mullvad VPN + Xray-core | **Titan** |
| **Process management** | Zombie killer + watchdog | systemd services | **Tie** |
| **Multi-language** | 11 languages (en, de, fr, es, pt, ru, zh, ja, ko, vi, ...) | English only | **ML6** |
| **Self-hosted** | No (requires ML account) | Yes (fully offline capable) | **Titan** |
| **Cost** | $99-399/month subscription | Free (self-hosted) | **Titan** |

---

## 5. Key Insights for Titan Development

### 5.1 What Titan Does Better Than ML6
1. **Forensic-grade profile generation** — Titan generates SQLite databases matching real Firefox/Chrome schemas at the byte level (PRAGMA settings, SameSite cookies, Chrome epoch timestamps). ML6 relies on its browser engine to handle this.
2. **Behavioral coherence** — Archetype-based profiles with circadian-rhythmic history, Pareto-distributed visit patterns, and archetype-specific bookmarks/downloads/engagement scores.
3. **AI intelligence layer** — 21 AI functions for fingerprint validation, session planning, decline analysis, and cross-session learning. ML6 has zero AI.
4. **Target-aware generation** — Pre-built profiles optimized for specific fraud engines (Forter, SEON, ThreatMetrix) with detection-aware handover docs.
5. **BIN coherence** — Card level → hardware profile mapping ensures premium cards match premium devices.
6. **Multi-PSP trust tokens** — Pre-aged tokens for Stripe, PayPal, Adyen, Braintree, Shopify, Klarna, Amazon, Square.
7. **OS consistency validation** — Explicit cross-signal validation (UA ↔ platform ↔ GPU ↔ timezone ↔ locale).

### 5.2 What ML6 Does Better Than Titan
1. **Custom browser engines** — Mimic (Chromium) and Stealthfox (Firefox) are full browser forks with kernel-level fingerprint spoofing. Titan relies on Camoufox (community Firefox fork).
2. **Canvas/WebGL/Audio noise** — Injected at the browser engine level (C++ modifications to Chromium/Firefox rendering pipeline). Titan applies noise via JavaScript shims.
3. **Font enumeration spoofing** — ML6 has `availableSystemFonts`, `persistentFonts`, and random font generation. More sophisticated than config-based approaches.
4. **Headless automation** — Full Selenium/Puppeteer-compatible headless mode with CLI, watchdog, and zombie process cleanup. Good for automation at scale.
5. **Team collaboration** — Profile groups, sharing, rights management, account transfers. Titan is single-user.
6. **Cloud sync** — Profiles synced across devices via Multilogin cloud servers.
7. **Multi-platform GUI** — Polished Electron + Angular UI with dark/light themes, splash screen, and 11 locales.

### 5.3 Gaps to Close (Titan Priorities)
1. **Browser engine depth** — Camoufox is good but Titan would benefit from deeper Chromium-level integration (canvas/WebGL noise at C++ level, not JS shims).
2. **Font fingerprint sophistication** — Add real font enumeration spoofing with random subset generation.
3. **Headless/automation mode** — Add a proper headless browser launch with Selenium/Playwright compatibility for batch operations.
4. **Profile portability** — Add profile export/import in a standard format for backup and migration.
5. **WebRTC leak prevention** — Ensure Camoufox config fully prevents WebRTC IP leaks in all modes.

### 5.4 ML6 Weaknesses Titan Already Exploits
1. **No AI** — ML6 has zero intelligence. Titan's 21 AI functions provide massive operational advantage.
2. **Generic profiles** — ML6 creates blank profiles. Titan creates fully aged, narratively coherent profiles.
3. **No target awareness** — ML6 doesn't know which fraud engine the target uses. Titan optimizes per-target.
4. **No BIN coherence** — ML6 doesn't validate card-to-hardware consistency. Titan catches mismatches pre-forge.
5. **Subscription dependency** — ML6 requires active subscription and cloud account. Titan runs fully offline.
6. **No handover protocol** — ML6 assumes automation. Titan provides detailed human operator execution docs.

---

## 6. File Structure Summary

### Multilogin 6 (from .deb)
```
/opt/Multilogin/
├── multilogin              (176MB - Electron binary)
├── headless/
│   ├── multilogin          (230MB - Headless Chromium engine "Indigo")
│   ├── cli.sh              (CLI wrapper)
│   └── headless.sh         (Headless launcher)
├── resources/
│   └── app.asar            (230MB - Electron app bundle)
│       ├── dist/
│       │   ├── bundle.js       (2MB - Main process)
│       │   ├── express-server.js (1.7MB - Local API)
│       │   ├── preload.js      (400KB - Renderer bridge)
│       │   └── zombie-killer.js (136KB - Process cleanup)
│       └── renderer/multilogin/{en,de,fr,...}/
│           ├── main.js         (193KB - Angular app)
│           ├── vendor.js       (2MB - Angular framework)
│           └── [46 lazy-loaded chunks]
├── chrome-sandbox           (SUID sandbox)
├── libEGL.so, libGLESv2.so, libffmpeg.so, libvulkan.so.1
├── icudtl.dat              (ICU data - 10MB)
├── locales/*.pak           (65 locale packs)
└── resources.pak, chrome_*.pak, v8_context_snapshot.bin
```

### Titan Genesis (from src/core/)
```
/opt/titan/core/
├── genesis_core.py          (2757 lines - Main forge engine)
├── fingerprint_injector.py  (Fingerprint injection)
├── canvas_noise.py          (Canvas noise generation)
├── canvas_subpixel_shim.py  (Subpixel rendering)
├── oblivion_setup.py        (Anti-detect setup)
├── oblivion_forge.py        (Profile forging)
├── form_autofill_injector.py (Autofill injection)
├── ai_intelligence_engine.py (21 AI functions)
├── target_intelligence.py   (Target site database)
└── [100+ other core modules]
```

---

## 7. Conclusion

**Multilogin 6** is a mature commercial anti-detect browser with polished UX, custom browser engines (Mimic/Stealthfox), and team collaboration features. Its strength is **kernel-level fingerprint spoofing** through custom Chromium/Firefox forks.

**Titan OS Genesis** surpasses ML6 in **profile intelligence** — forensic-grade browser profile generation, AI-powered validation, target-specific optimization, behavioral archetypes, and BIN-coherent profiles. Titan's profiles are significantly more realistic and detection-resistant than ML6's blank-slate approach.

**Bottom line:** ML6 is a better *browser*, Titan is a better *brain*. The ideal architecture combines Titan's intelligent profile generation with a deep browser engine like ML6's Mimic for kernel-level spoofing.
