# 03 — Core Modules Reference (Part 1)

All 90 modules in `src/core/` documented with purpose, function, and key APIs. Split into two parts for readability.

- **Part 1** (this file): Identity, Anti-Detection, Network, Transaction
- **Part 2** (`03B_CORE_MODULES_PART2.md`): AI, Target/Recon, KYC, Automation, Security, System

---

## Category 1: Identity & Profile Generation (8 modules)

### genesis_core.py — Browser Profile Forge Engine
**Purpose:** Antifraud flags fresh browsers with zero history. Genesis creates profiles that look like a real person has been browsing for 2+ years.

**Functions:**
- Generates complete Firefox profiles: `places.sqlite` (1500+ history entries over 900 days), `cookies.sqlite`, `formhistory.sqlite`, `favicons.sqlite`, `permissions.sqlite`
- Creates site engagement scores, notification permissions, bookmark folders
- Uses `profgen` library for forensic-grade profiles, falls back to built-in writer

**Key API:** `GenesisEngine.forge_profile(config)` → `GeneratedProfile`

---

### advanced_profile_generator.py — 900-Day History Synthesis
**Purpose:** Basic history is flat and unrealistic. This module adds circadian rhythms, weekday/weekend patterns, and evolving interests.

**Functions:**
- Non-linear history with circadian-weighted timestamps
- Pareto-distributed site popularity
- Cache2 binary mass (70% of profile size)
- LSNG structured clone data for localStorage

**Key API:** `AdvancedProfileGenerator.generate(config)` → enhanced profile

---

### forensic_synthesis_engine.py — Cache2 Binary Mass & LSNG
**Purpose:** Firefox's disk cache uses proprietary binary format. Empty cache = new profile signal.

**Functions:**
- Creates `_CACHE_MAP_` index, `_CACHE_001/002/003_` block files
- HTTP metadata appended to entries
- 350-500 MB of realistic binary data
- QuotaManager `.metadata-v2` files per origin

**Key API:** `Cache2Synthesizer.synthesize(profile_path, target_size_mb)`

---

### profile_realism_engine.py — Quality Scoring
**Purpose:** Scores profile quality on 20+ dimensions before use. Catches weaknesses early.

**Functions:** Checks platform ABI, prefs.js consistency, history distribution, profile size vs age ratio. Returns gap analysis with remediation suggestions.

**Key API:** `ProfileRealismEngine.score(profile_path)` → quality score + gaps

---

### persona_enrichment_engine.py — Persona Backstory Generation
**Purpose:** A persona needs coherent backstory — age-appropriate interests, income-matching patterns, location-consistent timezone.

**Functions:** Generates demographics from minimal seed, enriches with interests/occupation/income, validates internal consistency.

**Key API:** `PersonaEnrichmentEngine.enrich(name, address, dob)` → enriched persona

---

### purchase_history_engine.py — Synthetic Purchase Trail
**Purpose:** Browser with no purchase history is suspicious to e-commerce sites.

**Functions:** Injects localStorage for Amazon orders, eBay purchases, loyalty programs. Timestamps match profile age, amounts match persona income.

**Key API:** `PurchaseHistoryEngine.inject(profile_path, persona, card_data)`

---

### indexeddb_lsng_synthesis.py — IndexedDB & localStorage Deep Content
**Purpose:** Modern web apps store MB of data in IndexedDB. Empty storage = new profile.

**Functions:** Creates IndexedDB for Gmail (offline mail), YouTube (watch history), Google Maps (cached routes). Correct Snappy compression and idb/ directory structure.

**Key API:** `IndexedDBSynthesizer.synthesize(profile_path, sites)`

---

### first_session_bias_eliminator.py — New Profile Signal Removal
**Purpose:** Even with history, new profiles have telltale first-session markers.

**Functions:** Injects site engagement scores, notification permissions, DNS prefetch cache, service worker registrations, last-session timestamps.

**Key API:** `FirstSessionEliminator.eliminate(profile_path)`

---

## Category 2: Anti-Detection & Fingerprint (10 modules)

### fingerprint_injector.py — Master Fingerprint Coordinator
**Purpose:** Coordinates all fingerprint shims with consistent seeding from profile UUID.

**Functions:** Client Hints headers, WebRTC spoofing, media device IDs, injects all JS shims via `page.add_init_script()`.

**Key API:** `FingerprintInjector.inject(page, profile_config)`

---

### canvas_subpixel_shim.py — Canvas Fingerprint Noise
**Purpose:** Canvas fingerprinting is the most effective tracking technique. Must produce deterministic per-profile hashes.

**Functions:** Intercepts `toDataURL()` and `getImageData()`, adds deterministic noise seeded from profile UUID. Same profile = same hash, different profiles = different hashes.

**Key API:** `CanvasSubpixelShim.get_init_script(seed)` → JavaScript

---

### canvas_noise.py — Canvas Hash Randomization
**Purpose:** Companion to subpixel shim for lower-level canvas manipulation.

**Functions:** Modifies RGBA pixel data with controlled noise below perception threshold.

**Key API:** `CanvasNoiseGenerator.apply(canvas_context, seed)`

---

### audio_hardener.py — AudioContext Fingerprint Spoofing
**Purpose:** Web Audio API produces device-specific output used for fingerprinting.

**Functions:** Intercepts AudioContext, modifies oscillator frequency response. Includes Win10 22H2 profile: 44100Hz, 32ms latency, 3.2ms jitter.

**Key API:** `AudioHardener.get_init_script(profile)` → JavaScript

---

### font_sanitizer.py — Font Enumeration Control
**Purpose:** Linux fonts visible to JS reveal true OS.

**Functions:** Hides Linux fonts (Liberation, DejaVu), exposes Windows fonts (Segoe UI, Calibri). Works with `windows_font_provisioner.py`.

**Key API:** `FontSanitizer.get_init_script()` → JavaScript font filter

---

### webgl_angle.py — WebGL Renderer Spoofing
**Purpose:** WebGL reveals GPU. VPS shows "llvmpipe" — dead giveaway.

**Functions:** Spoofs to consumer GPUs: "ANGLE (NVIDIA GeForce RTX 3060)". Matches WebGL parameters to claimed GPU.

**Key API:** `WebGLAngleEngine.get_init_script(gpu_profile)` → JavaScript

---

### ghost_motor_v6.py — Human Behavioral Engine
**Purpose:** Behavioral biometric systems analyze mouse/keyboard patterns. Bot movements trigger detection.

**Functions:** Bézier curve mouse movements, natural typing with inter-key timing, scroll behavior, click timing with positional variance. Profile-seeded for consistency.

**Key API:** `GhostMotorEngine.move_to(x,y)`, `.type_text(text)`, `get_forter_safe_params()`

Also: browser extension `extensions/ghost_motor/ghost_motor.js`

---

### tls_parrot.py — TLS ClientHello Mimicry
**Purpose:** Python's TLS looks nothing like Chrome. Antifraud fingerprints TLS connections.

**Functions:** Replicates exact ClientHello byte sequences including GREASE values. Supports Chrome 120-133, Firefox 121-132, Edge, Safari.

**Key API:** `TLSParrotEngine.get_client_hello(browser, version)`

---

### ja4_permutation_engine.py — JA4+ Fingerprint Generation
**Purpose:** JA4 is next-gen TLS fingerprinting combining TCP + TLS + HTTP/2.

**Functions:** Generates valid JA4+ permutations matching specific browser versions.

**Key API:** `generate_ja4_fingerprint(browser)` → JA4 fingerprint

---

### timezone_enforcer.py — Timezone Consistency
**Purpose:** Billing address in NY but browser reports UTC+0 = instant flag.

**Functions:** Sets system + browser timezone, validates consistency with IP geolocation.

**Key API:** `TimezoneEnforcer.set_timezone(state)`, `get_timezone_for_state(code)`

---

### location_spoofer_linux.py — GPS Coordinate Spoofing
**Purpose:** HTML5 Geolocation revealing server location = detection.

**Functions:** Intercepts `navigator.geolocation`, returns coordinates matching billing address with ±50m jitter.

**Key API:** `LocationSpooferLinux.spoof(lat, lng, accuracy)`

---

## Category 3: Network & Infrastructure (11 modules)

### integration_bridge.py — Master Orchestration Bridge
**Purpose:** 90 modules need coordination. The bridge is the central nervous system.

**Functions:** Auto-discovers modules, unified preflight checks, browser profile loading, VPN/proxy + timezone coordination, session handover, health monitoring.

**Key API:** `TitanIntegrationBridge.initialize()`, `.run_preflight()` → `PreFlightReport`, `get_bridge_health_monitor()`, `get_module_discovery()`

---

### network_shield.py + network_shield_loader.py — eBPF TCP/IP Masquerade
**Purpose:** Linux TCP/IP stack is identifiable from a single SYN packet (TTL=64, unique window sizes).

**Functions:** eBPF programs rewrite TCP/IP headers at kernel level: TTL 64→128, Windows TCP window sizes, Windows options order, sequential IP ID field. Multi-interface management, WireGuard detection, dynamic persona switching.

**Key API:** `attach_shield_to_mullvad(persona, mode, interface)`, `safe_boot_mullvad()`, `detect_wireguard_interface()`

---

### network_jitter.py — Realistic Latency Patterns
**Purpose:** Datacenter latency (1-3ms, ±0.1ms) is unnaturally consistent.

**Functions:** Adds residential latency patterns — DSL: 15-40ms, Cable: 8-20ms, Fiber: 3-10ms, with occasional 100-200ms spikes.

**Key API:** `NetworkJitterEngine.apply(connection_type)`

---

### proxy_manager.py — Residential Proxy Pool
**Purpose:** Datacenter IPs are flagged. Residential proxies appear legitimate.

**Functions:** Manages pools from BrightData/Oxylabs/SmartProxy/IPRoyal. Health checks, dead detection, auto-rotation, exit IP monitoring every 30s, geo-targeting.

**Key API:** `ResidentialProxyManager.get_proxy(country, city)`, `.health_check()`

---

### quic_proxy.py — HTTP/3 QUIC Proxy
**Purpose:** HTTP/3 QUIC has its own fingerprint that must match TLS fingerprint.

**Key API:** `QUICProxy.start(port)`

---

### mullvad_vpn.py — Mullvad WireGuard Integration
**Purpose:** Shared residential-looking IPs not flagged as datacenter.

**Functions:** Connect/disconnect, server selection by country/city, DAITA support, QUIC obfuscation, IP reputation checking.

**Key API:** `create_mullvad(country, city, obfuscation)`, `quick_connect()`, `check_ip_reputation(ip)`

---

### lucid_vpn.py — Self-Hosted VLESS+Reality VPN
**Purpose:** Dedicated residential IP via Xray-core. Reality protocol indistinguishable from HTTPS.

**Key API:** `LucidVPN.connect()` / `.disconnect()`

---

### cpuid_rdtsc_shield.py — Hypervisor Concealment
**Purpose:** performance.now() timing and CPUID detect VMs.

**Functions:** Masks CPUID hypervisor bit, calibrates RDTSC to eliminate VM-exit latency.

**Key API:** `CPUIDRDTSCShield.apply()`

---

### immutable_os.py — Filesystem Integrity
**Purpose:** Prevents modification of core system files.

**Functions:** Checksums core files, monitors modifications, auto-restores from known-good copies.

**Key API:** `verify_system_integrity()`, `get_boot_status()`

---

### location_spoofer.py — Generic Location Spoofing
**Purpose:** Cross-platform location spoofing fallback.

**Key API:** `LocationSpoofer.spoof(lat, lng)`

---

## Category 4: Transaction & Payment (11 modules)

### cerberus_core.py — Card Validation Engine
**Purpose:** Pre-validates cards to avoid wasting operations on dead cards.

**Functions:** Luhn verification, BIN lookup (issuer/country/type/level), card status assessment, $0 auth validation, decline code capture.

**Key API:** `CerberusValidator.validate(card_asset)` → `ValidationResult`

---

### cerberus_enhanced.py — Enhanced Card Intelligence
**Purpose:** Deep BIN scoring, OSINT verification, quality grading.

**Key API:** `BINScoringEngine.score(bin)`, `OSINTVerifier.verify(cardholder)`, `CardQualityGrader.grade(card)`

---

### transaction_monitor.py — TX Capture & Decline Decoder
**Purpose:** Understanding why transactions fail improves success rates.

**Functions:** Captures payment events from browser extension, SQLite storage, decodes PSP-specific codes (Stripe/Adyen/Authorize.net/ISO8583/Checkout.com/Braintree) to reasons + categories + guidance.

**Key API:** `DeclineDecoder.decode(psp, code)`, `decode_decline(code)`

Also: browser extension `extensions/tx_monitor/`

---

### three_ds_strategy.py — 3DS Bypass Planning
**Purpose:** 3DS is the primary transaction barrier. Different PSPs have different vulnerabilities.

**Functions:** PSP vulnerability profiles, PSD2 exemptions (TRA/low-value/recurring/MOTO), one-leg-out rule, downgrade attacks, non-VBV BIN database.

**Key API:** `get_3ds_bypass_score(card, merchant)`, `get_non_vbv_recommendations(country)`, `get_easy_countries()`

---

### tra_exemption_engine.py — TRA Exemption Calculation
**Purpose:** PSD2 TRA exemptions can skip SCA for qualifying transactions.

**Functions:** Thresholds: €100 (fraud <0.13%), €250 (<0.06%), €500 (<0.01%). PSP-specific adoption data.

**Key API:** `get_optimal_exemption(amount)`, `calculate_tra_score(params)`

---

### issuer_algo_defense.py — Issuer Algorithm Countermeasures
**Purpose:** Each bank uses different risk scoring. Chase ≠ Citi ≠ Amex.

**Functions:** Issuer-specific risk profiles, decline risk calculation, mitigation strategies.

**Key API:** `calculate_decline_risk(issuer, params)`, `get_mitigation_strategy(issuer, code)`

---

### payment_preflight.py — Pre-Checkout Validation
**Purpose:** Multi-condition validation before checkout attempt.

**Functions:** Card liveness, IP-billing geo consistency, proxy blacklist check, 3DS readiness, velocity limits.

**Key API:** `PaymentPreflightValidator.validate(operation)` → go/no-go

---

### payment_sandbox_tester.py — PSP Sandbox Testing
**Purpose:** Test checkout flows with PSP sandbox before real transactions.

**Key API:** `PaymentSandboxTester.test(psp, flow)`

---

### payment_success_metrics.py — Success Rate Analytics
**Purpose:** Track success rates across BINs, PSPs, targets, profiles.

**Key API:** `PaymentSuccessMetricsDB.record(result)`, `get_metrics_db()`

---

### dynamic_data.py — Checkout Data Generation
**Purpose:** Generates correctly formatted checkout data matching persona.

**Key API:** `DynamicDataEngine.generate(persona, card)`

---

### form_autofill_injector.py — Form Field Injection
**Purpose:** Auto-fills checkout forms with human-like timing.

**Functions:** Detects fields by name/id/label, handles dropdowns/checkboxes, adapts to different layouts.

**Key API:** `FormAutofillInjector.fill(page, data)`

---

*Continued in [Part 2](03B_CORE_MODULES_PART2.md) — AI, Target/Recon, KYC, Automation, Security, System*
