# 02 — Techniques & Methods

## Overview

Titan OS employs a layered defense strategy across six rings to defeat every known antifraud detection vector. This document explains each technique, why it exists, and which modules implement it.

---

## 1. Browser Fingerprint Evasion

### What Antifraud Systems Check
Every website can silently fingerprint a visitor's browser by querying JavaScript APIs. Antifraud systems like Forter, Riskified, Sift, and DataDome build a unique device ID from:
- Canvas rendering (pixel-level differences between GPUs)
- WebGL renderer and vendor strings
- AudioContext frequency response
- Installed fonts and their rendering metrics
- Screen resolution, color depth, device pixel ratio
- Navigator properties (userAgent, platform, hardwareConcurrency)
- Client Hints (Sec-CH-UA headers)
- WebRTC local IP addresses

### How Titan OS Defeats It

**Canvas Subpixel Noise** (`canvas_subpixel_shim.py`)
Intercepts `HTMLCanvasElement.toDataURL()` and `CanvasRenderingContext2D.getImageData()` at the JavaScript level. Adds deterministic subpixel noise seeded from the profile UUID. The same profile always produces the same canvas hash, but different profiles produce different hashes. This prevents both fingerprint tracking (same hash across sessions) and fingerprint uniqueness detection (hash never changes).

**Canvas Noise Generator** (`canvas_noise.py`)
Lower-level canvas manipulation that adds controlled noise to the rendering pipeline. Works alongside the subpixel shim to ensure canvas fingerprints appear natural.

**Audio Hardener** (`audio_hardener.py`)
Intercepts Web Audio API calls (`AudioContext`, `OfflineAudioContext`). Modifies oscillator frequency response and dynamic compressor output to match a specific hardware profile. Includes a Win10 22H2 audio profile: 44100Hz sample rate, 32ms output latency, 3.2ms jitter — matching real Windows audio behavior.

**Font Sanitizer** (`font_sanitizer.py`)
Controls which fonts are visible to JavaScript `document.fonts` enumeration. Ensures the font list matches a typical Windows 11 installation. Removes Linux-specific fonts that would reveal the true OS. Adds Windows-exclusive fonts (Segoe UI, Calibri, etc.) to prevent font-based OS detection.

**WebGL Angle Engine** (`webgl_angle.py`)
Spoofs `WEBGL_debug_renderer_info` extension responses. Instead of reporting the real GPU (often "llvmpipe" on VPS), reports a consumer GPU like "ANGLE (NVIDIA GeForce RTX 3060)". Values are consistent with the hardware profile seed.

**Fingerprint Injector** (`fingerprint_injector.py`)
Master coordinator for all fingerprint spoofing. Generates Client Hints headers (Sec-CH-UA matching Chrome 125–133), spoofs WebRTC with fake local IP addresses seeded from the profile, and generates consistent media device IDs. Injects all shims via `page.add_init_script()` before any page JavaScript executes.

**Windows Font Provisioner** (`windows_font_provisioner.py`)
Actually installs Windows TrueType fonts on the Linux system so they render identically to a Windows machine. Font metrics (advance width, kerning pairs) are critical for fingerprint consistency.

---

## 2. Network Identity Masquerade

### What Antifraud Systems Check
The network layer reveals the operating system through:
- TCP/IP stack behavior (TTL, window size, MSS, TCP options order)
- TLS ClientHello fingerprint (JA3/JA4 hash)
- DNS resolution patterns
- HTTP/3 QUIC fingerprint
- IP address reputation (datacenter vs residential)

### How Titan OS Defeats It

**eBPF Network Shield** (`network_shield.py`, `network_shield_loader.py`, `network_shield_v6.c`)
Attaches eBPF/XDP programs to the network interface that rewrite TCP/IP headers at the kernel level. Transforms every outgoing packet:
- TTL: 64 (Linux) → 128 (Windows)
- TCP Window Size: matches Windows 11 defaults
- TCP Options Order: rearranged to match Windows stack
- IP ID field: sequential (Windows) instead of random (Linux)
- MSS: adjusted to match Windows default

This happens below the application layer — no software on the machine can detect the rewrite.

**TLS Parrot** (`tls_parrot.py`)
Mimics the exact TLS ClientHello of a target browser. Chrome, Firefox, Edge, and Safari each produce a unique JA3/JA4 fingerprint based on their cipher suite order, extensions, and supported groups. TLS Parrot replicates the exact byte sequence so the TLS fingerprint matches the claimed browser. Includes GREASE (Generate Random Extensions And Sustain Extensibility) values that Chrome uses.

**JA4 Permutation Engine** (`ja4_permutation_engine.py`)
Generates valid JA4+ fingerprint permutations that match specific browser versions. JA4 is the next-generation TLS fingerprinting standard that includes TCP fingerprint, TLS fingerprint, and HTTP/2 fingerprint components.

**QUIC Proxy** (`quic_proxy.py`)
Proxies HTTP/3 QUIC traffic with correct fingerprinting. Without this, QUIC connections would reveal the true TLS implementation (Python's ssl module vs Chrome's BoringSSL).

**Network Jitter Engine** (`network_jitter.py`)
Adds realistic latency variance to network requests. A datacenter connection has unnaturally low and consistent latency. The jitter engine introduces patterns matching a residential DSL/cable/fiber connection, complete with occasional micro-delays.

**Mullvad VPN** (`mullvad_vpn.py`)
Integrates Mullvad WireGuard VPN for IP reputation. Mullvad provides shared residential-looking IPs that are not flagged as datacenter. Supports DAITA (Defence Against AI-guided Traffic Analysis) and QUIC obfuscation. The module manages connection, disconnection, server selection by country/city, and IP reputation checking.

**Lucid VPN** (`lucid_vpn.py`)
Self-hosted VPN using VLESS+Reality protocol through Xray-core. Provides residential exit nodes via Tailscale mesh. The Reality protocol makes VPN traffic indistinguishable from legitimate HTTPS to deep packet inspection.

**Proxy Manager** (`proxy_manager.py`)
Manages residential proxy pools from providers (BrightData, Oxylabs, SmartProxy, IPRoyal). Includes health checking, dead proxy detection, automatic rotation, and session IP monitoring (checks exit IP every 30 seconds to detect silent proxy rotation).

---

## 3. Browser Profile Forensics

### What Antifraud Systems Check
Sophisticated systems examine browser profile age and authenticity:
- How many entries in browsing history (places.sqlite)
- Cookie age and diversity
- localStorage/IndexedDB content depth
- Cache file timestamps and sizes
- First-visit vs returning visitor signals
- Site engagement scores
- Notification permission history

### How Titan OS Creates Authentic Profiles

**Genesis Core** (`genesis_core.py`)
The primary profile generation engine. Creates complete Firefox profiles with:
- **places.sqlite**: 1500+ browsing history entries spanning 900 days, with circadian-weighted timestamps (more visits during waking hours), Pareto-distributed site popularity, and Mozilla's DJB2 URL hashing
- **cookies.sqlite**: Hundreds of cookies from major sites (Google, Facebook, Amazon, news sites) with realistic expiration dates
- **formhistory.sqlite**: Autofill data matching the persona
- **favicons.sqlite**: Favicon data for visited sites
- **permissions.sqlite**: Notification permissions for popular sites
- **prefs.js**: Browser preferences matching the target configuration
- **compatibility.ini**: Correct ABI strings for the platform

**Advanced Profile Generator** (`advanced_profile_generator.py`)
Extends Genesis with 900-day non-linear history synthesis. Uses forensic-grade techniques:
- Cache2 binary mass (70% of profile size) with valid `nsDiskCacheEntry` headers
- LSNG (localStorage Next Generation) with UTF-16LE encoding and Snappy compression
- QuotaManager `.metadata-v2` files for every origin directory
- Atomic temporal synchronization (PRTime microseconds, POSIX seconds, and formatted strings all aligned)

**Forensic Synthesis Engine** (`forensic_synthesis_engine.py`)
Creates the binary cache structure that Firefox uses internally:
- `_CACHE_MAP_` index with 12-byte `CacheIndexHeader`
- `_CACHE_001/002/003_` block files (512/1024/4096 byte blocks)
- HTTP metadata appended to each cache entry
- Symmetrical ratio: 70% binary cache, 30% text/state data

**Profile Realism Engine** (`profile_realism_engine.py`)
Scores profile quality on 20+ dimensions and identifies gaps. Checks that:
- `compatibility.ini` matches the target platform ABI
- `prefs.js` contains no conflicting OS indicators
- History distribution follows natural browsing patterns
- Profile size matches expected range for its claimed age

**IndexedDB/LSNG Synthesis** (`indexeddb_lsng_synthesis.py`)
Creates realistic IndexedDB and localStorage data for common sites. Gmail stores offline mail data, Google Maps caches location data, YouTube stores watch history — all synthesized to match a real user's profile.

**First Session Bias Eliminator** (`first_session_bias_eliminator.py`)
New browser profiles have telltale "first session" signals: empty site engagement scores, no notification permissions, no cached DNS. This module injects all these artifacts to make the profile appear as if the browser has been used for months.

**Purchase History Engine** (`purchase_history_engine.py`)
Injects realistic e-commerce purchase trails into the profile. localStorage entries for Amazon order history, eBay purchase confirmations, and retail site loyalty program data — all timestamped consistently with the profile's age.

---

## 4. Behavioral Mimicry

### What Antifraud Systems Check
Behavioral biometric systems analyze:
- Mouse movement patterns (speed, acceleration, curvature)
- Typing cadence (inter-key timing, error rate)
- Scroll behavior (speed, direction changes)
- Time between page interactions
- Navigation patterns (direct URL vs search vs link)

### How Titan OS Mimics Human Behavior

**Ghost Motor V6** (`ghost_motor_v6.py`)
A behavioral engine that drives mouse and keyboard with human-like patterns:
- **Mouse**: Bézier curve movements with variable speed, overshooting, and micro-corrections. Seeded RNG ensures consistent behavioral patterns per profile.
- **Keyboard**: Natural typing with variable inter-key timing (faster for common bigrams, slower for uncommon ones). Includes realistic typos and corrections.
- **Scroll**: Variable speed scrolling with direction changes and pauses at content boundaries.
- **Click**: Natural click timing with slight positional variance (humans don't click the exact center of buttons).

Delivered as a browser extension (`extensions/ghost_motor/`) that intercepts and humanizes all input events.

**Referrer Warmup** (`referrer_warmup.py`)
Before visiting the target site, builds a realistic referrer chain. Instead of navigating directly to `checkout.example.com`, the system visits Google, clicks a search result, browses related sites, and eventually arrives at the target — creating a natural referrer trail.

**Handover Protocol** (`handover_protocol.py`)
Manages the transition from automated warmup to human control. Ensures the browser state is clean and the human operator can seamlessly take over browsing.

---

## 5. Card Intelligence & Transaction Strategy

### What Payment Systems Check
Payment processors and issuing banks analyze:
- Card BIN (first 6-8 digits) reputation
- AVS (Address Verification System) match
- 3D Secure authentication requirements
- Velocity (number of transactions per card/BIN/IP)
- Geographic consistency (card country vs IP country vs billing address)
- Transaction amount patterns

### How Titan OS Optimizes Transactions

**Cerberus Core** (`cerberus_core.py`)
Card validation engine that performs:
- Luhn algorithm verification
- BIN lookup for issuer, country, card type, level
- Card status assessment (live, dead, restricted)
- Pre-transaction validation via $0 auth or SetupIntent

**Three DS Strategy** (`three_ds_strategy.py`)
Comprehensive 3DS bypass planning per PSP:
- PSP vulnerability profiles (Stripe, Adyen, Braintree, etc.)
- PSD2 exemption detection (TRA, low-value, recurring)
- One-leg-out rule exploitation (non-EU card on EU merchant = no SCA)
- Downgrade attack strategies

**TRA Exemption Engine** (`tra_exemption_engine.py`)
Calculates Transaction Risk Analysis exemptions. Under PSD2, transactions below certain thresholds (€30 for acquirers with <0.13% fraud rate) are exempt from Strong Customer Authentication.

**Issuer Algorithm Defense** (`issuer_algo_defense.py`)
Countermeasures against issuer-side fraud scoring algorithms. Different issuers (Chase, Citi, Amex) use different risk models. This module adjusts transaction parameters to score below each issuer's decline threshold.

**Target Intel V2** (`titan_target_intel_v2.py`)
8-vector golden path scoring system that predicts success probability:
1. PSP 3DS configuration (25 points)
2. MCC intelligence (10 points) — restaurants and rideshare have lowest 3DS rates
3. Acquirer level (5 points)
4. Geographic enforcement (15 points)
5. Transaction type exemptions (10 points)
6. Amount thresholds (15 points)
7. Antifraud gaps (10 points)
8. Checkout flow (10 points)

---

## 6. AI-Powered Decision Making

### The AI Stack

**Ollama Bridge** (`ollama_bridge.py`)
Interface to locally-running Ollama LLM server. Three models available:
- `mistral:7b` — general reasoning and analysis
- `qwen2.5:7b` — multilingual and code understanding
- `deepseek-r1:8b` — deep reasoning for complex scenarios

**AI Intelligence Engine** (`ai_intelligence_engine.py`)
Coordinates AI analysis across all modules:
- BIN analysis with context enrichment
- Target reconnaissance with web search
- 3DS strategy recommendations
- Preflight validation assessment
- Behavioral tuning suggestions
- Profile quality auditing

**AI Operations Guard** (`titan_ai_operations_guard.py`)
Four-phase AI advisor that runs alongside operations:
1. **Pre-Operation**: Geo-mismatch detection, BIN velocity tracking, golden path scoring
2. **Active Session**: Session duration analysis, page count tracking, proxy latency monitoring
3. **Checkout**: PSP-specific 3DS prediction, amount threshold advice
4. **Post-Operation**: Decline code analysis, vector memory storage, next target recommendation

The guard NEVER blocks the operator — it only advises.

**Vector Memory** (`titan_vector_memory.py`)
ChromaDB-based persistent knowledge base. Every operation result, decline code, target analysis, and BIN assessment is stored as a vector embedding. Future operations can semantically search past experience: "What happened last time I used a Chase Visa on Shopify?"

**AI Co-Pilot Extension** (`titan_3ds_ai_exploits.py`)
Browser extension injected into Camoufox that monitors checkout pages:
- Detects checkout/payment pages automatically
- Blocks hidden 3DS fingerprint iframes in <10ms
- Scans 30-80 API responses during checkout for decline signals
- Auto-detects PSP (Stripe/Adyen/Braintree) from page source
- Alerts operator via non-blocking notifications

---

## 7. Hardware Identity Concealment

### Why It Matters
Websites can detect virtual machines through JavaScript APIs (`navigator.hardwareConcurrency`, WebGL renderer) and through OS-level artifacts (DMI vendor strings visible via `/sys/class/dmi/`).

### How Titan OS Hides the VM

**CPUID/RDTSC Shield** (`cpuid_rdtsc_shield.py`)
Masks the hypervisor CPUID leaf (`CPUID.1:ECX[31]`) and calibrates RDTSC timing to eliminate the latency spike caused by VM exits. Makes `performance.now()` timing attacks fail to detect the hypervisor.

**Hardware Shield** (`hardware_shield_v6.c`)
Kernel module that spoofs DMI/SMBIOS strings:
- `sys_vendor`: "QEMU" → "Dell Inc."
- `product_name`: "Standard PC" → "OptiPlex 7090"
- `bios_vendor`: "SeaBIOS" → "Dell Inc."
- Also spoofs CPU model string and MAC address OUI

**USB Peripheral Synthesis** (`usb_peripheral_synth.py`)
Creates virtual USB devices that appear in `lsusb` output. A real desktop has a keyboard, mouse, and maybe a webcam connected via USB. A VPS has none. This module creates synthetic USB device descriptors matching common consumer peripherals.

---

## 8. KYC Verification Bypass

### What KYC Systems Check
Know Your Customer verification requires:
- Live camera feed showing the operator's face
- Document photo matching the face
- Liveness detection (blink, head turn, smile)
- 3D depth verification (prevents flat image attacks)
- Voice verification (speak a phrase)

### How Titan OS Handles It

**KYC Core** (`kyc_core.py`)
Virtual camera controller using LivePortrait face reenactment. Takes a static face image and animates it in real-time, outputting to `/dev/video` virtual camera. Supports motions: blink, smile, head turn, nod, eyebrow raise.

**KYC Enhanced** (`kyc_enhanced.py`)
Provider-specific intelligence for Onfido, Jumio, Veriff, Sumsub, Persona, Stripe Identity, Plaid IDV, and Au10tix. Each provider has different liveness challenge sequences and timing requirements.

**ToF Depth Synthesis** (`tof_depth_synthesis.py`)
Generates Time-of-Flight depth maps to defeat 3D liveness detection. Creates realistic IR dot patterns and depth data matching the face geometry.

**Voice Engine** (`kyc_voice_engine.py`)
Text-to-speech with natural voice synthesis for voice verification challenges. Generates lip-synced video output matching the spoken phrase.

---

## 9. Forensic Protection

**Kill Switch** (`kill_switch.py`)
Emergency wipe protocol triggered by panic signal:
- Shreds all profiles, logs, and state data
- Overwrites free disk space
- Clears RAM (tmpfs)
- Notifies AI Operations Guard for learning

**Forensic Cleaner** (`forensic_cleaner.py`)
Removes all Titan-specific artifacts from the filesystem:
- Profile directories cleaned of `.titan/` metadata
- Browser cache sanitized
- Temporary files securely deleted

**Forensic Monitor** (`forensic_monitor.py`)
Real-time monitoring for forensic artifacts that could reveal Titan OS presence. Alerts if any detectable traces appear in the filesystem, process list, or network connections.

**Immutable OS** (`immutable_os.py`)
Filesystem integrity protection. Core system files are checksummed and monitored. Any modification triggers an alert and automatic restoration.

---

*Next: [03 — Core Modules Reference](03_CORE_MODULES.md)*
