# Detection Evasion Matrix — Every Antifraud System vs TITAN Countermeasure

## Comprehensive mapping of detection techniques used by major antifraud platforms and how TITAN neutralizes each one.

---

## Antifraud Platform Coverage

| Platform | Type | Detection Focus | TITAN Evasion Confidence |
|----------|------|----------------|-------------------------|
| **Forter** | Real-time decisioning | Behavioral + device + identity | 95% |
| **Sift** | ML fraud scoring | Velocity + device + behavioral | 93% |
| **ThreatMetrix (LexisNexis)** | Device fingerprinting | Hardware + network + browser | 96% |
| **BioCatch** | Behavioral biometrics | Mouse/keyboard/cognitive | 92% |
| **Riskified** | Chargeback guarantee | Identity + device + history | 94% |
| **Kount (Equifax)** | Device intelligence | Device ID + IP + velocity | 95% |
| **Stripe Radar** | Payment fraud | Card testing + velocity + device | 90% |
| **Signifyd** | Commerce protection | Identity + device + behavioral | 93% |
| **Arkose Labs** | Bot detection | Challenge-response + behavioral | 88% |
| **PerimeterX (HUMAN)** | Bot mitigation | JS challenges + behavioral | 90% |
| **Sardine** | Behavioral intelligence | Device + behavioral + identity | 91% |
| **FingerprintJS** | Browser fingerprinting | Canvas + WebGL + Audio + Fonts | 97% |

---

## Detection Vector Matrix

### 1. Device Fingerprinting

| Detection Vector | What They Check | TITAN Countermeasure | Module |
|-----------------|----------------|---------------------|--------|
| Canvas hash | GPU rendering differences | Deterministic noise injection seeded from profile UUID | `fingerprint_injector.py` |
| WebGL renderer | GPU vendor/model string | ANGLE shim reports consumer GPU (Intel UHD 630) | `webgl_angle.py` |
| WebGL hash | 3D scene rendering differences | Consistent rendering via ANGLE translation layer | `webgl_angle.py` |
| Audio fingerprint | AudioContext oscillator output | Profile-seeded noise + Windows audio parameters | `audio_hardener.py` |
| Font enumeration | Installed font list reveals OS | fontconfig rejectfont blocks all Linux fonts | `font_sanitizer.py` |
| Screen resolution | Unusual resolutions = VM | Standard 1920x1080 configured | Camoufox config |
| Color depth | Non-standard depth = VM | 24-bit color depth (standard) | Camoufox config |
| Hardware concurrency | CPU core count | Reports consumer core count (8-16) | Camoufox config |
| Device memory | RAM amount | Reports 8-32GB (consumer range) | Camoufox config |
| Platform string | "Linux x86_64" reveals OS | Reports "Win32" | Camoufox config |
| User-Agent | Linux UA reveals OS | Windows Chrome/Firefox UA | Camoufox config |
| navigator.webdriver | Automation flag | Cleared at compile time in Camoufox | Camoufox build |
| Battery API | VMs report no battery | API disabled or reports laptop battery | Camoufox config |
| Touch support | Desktops have no touch | Reports no touch (consistent with desktop) | Camoufox config |

### 2. Network Fingerprinting

| Detection Vector | What They Check | TITAN Countermeasure | Module |
|-----------------|----------------|---------------------|--------|
| IP reputation | Datacenter IP = instant flag | Residential proxy (real ISP IP) | `proxy_manager.py` |
| IP geolocation | IP location vs billing address | Geo-targeted proxy matching billing city/state | `proxy_manager.py` |
| TTL value | Linux=64, Windows=128 | sysctl `ip_default_ttl=128` | `99-titan.conf` |
| TCP fingerprint | Window size, options order | sysctl TCP parameters match Windows | `99-titan.conf` |
| TLS JA3/JA4 | ClientHello fingerprint | Camoufox TLS stack matches Chrome on Windows | `tls_parrot.py` |
| DNS resolver | Datacenter DNS reveals hosting | Local DoH resolver + Cloudflare/Google DNS | `/etc/resolv.conf` |
| WebRTC leak | Real IP exposed via STUN | WebRTC disabled or proxied in Camoufox | Camoufox config |
| HTTP/2 fingerprint | Frame ordering, settings | Camoufox matches Chrome HTTP/2 behavior | Camoufox build |
| QUIC fingerprint | Transport parameters | QUIC proxy normalizes parameters | `quic_proxy.py` |
| Network jitter | Datacenter = zero jitter | tc-netem adds residential-like jitter | `network_jitter.py` |

### 3. Behavioral Analysis

| Detection Vector | What They Check | TITAN Countermeasure | Module |
|-----------------|----------------|---------------------|--------|
| Mouse velocity | Constant speed = bot | Bell-curve velocity profile with variation | `ghost_motor_v6.py` |
| Mouse curvature | Straight lines = bot | Bézier curves with micro-corrections | `ghost_motor_v6.py` |
| Click precision | Pixel-perfect = bot | Intentional overshoot + correction (15-30%) | `ghost_motor_v6.py` |
| Typing speed | Constant interval = bot | Per-key timing distributions with variation | `ghost_motor_v6.py` |
| Typing errors | Zero errors = bot | 2-8% typo rate with backspace corrections | `ghost_motor_v6.py` |
| Scroll behavior | Fixed increments = bot | Momentum scrolling with reading pauses | `ghost_motor_v6.py` |
| Cognitive delays | No thinking time = bot | Persona-appropriate delays (200-1200ms) | `ghost_motor_v6.py` |
| Session rhythm | Constant pace = bot | Warm-up → peak → fatigue modeling | `ghost_motor_v6.py` |
| Copy-paste detection | Pasted card numbers | Always typed character-by-character | `form_autofill_injector.py` |
| Form fill speed | Instant fill = autofill/bot | Character-by-character with human timing | `form_autofill_injector.py` |
| Navigation pattern | Direct to checkout = fraud | Google search → browse → cart → checkout | `referrer_warmup.py` |
| Time on page | Too fast = didn't read | Natural reading time per page type | `ghost_motor_v6.py` |

### 4. Identity & History

| Detection Vector | What They Check | TITAN Countermeasure | Module |
|-----------------|----------------|---------------------|--------|
| Cookie age | Fresh cookies = new device | 90-900 day old cookies pre-generated | `genesis_core.py` |
| Browsing history | Empty = fresh install | 5,000+ entries with circadian rhythm | `genesis_core.py` |
| Trust anchors | No Google/FB cookies = suspicious | Trust anchor cookies from major platforms | `genesis_core.py` |
| Purchase history | First-time buyer = high risk | Synthetic past purchases on target merchant | `purchase_history_engine.py` |
| Account age | New account = high risk | Profile includes account creation artifacts | `genesis_core.py` |
| localStorage | Empty = never visited | Pre-populated with realistic web app state | `genesis_core.py` |
| Profile size | Tiny profile = new/bot | ~700MB profile matching real usage | `genesis_core.py` |
| Referrer chain | No referrer = direct/bot | Google → review site → merchant chain | `referrer_warmup.py` |

### 5. Hardware & OS Detection

| Detection Vector | What They Check | TITAN Countermeasure | Module |
|-----------------|----------------|---------------------|--------|
| /proc/cpuinfo | Server CPU = VPS | Kernel module reports consumer Intel CPU | `hardware_shield_v6.c` |
| DMI/SMBIOS | QEMU/KVM = VM | Kernel module reports Dell/HP/Lenovo | `hardware_shield_v6.c` |
| USB device tree | Empty = VM | Virtual USB devices via configfs | `usb_peripheral_synth.py` |
| Audio stack | PulseAudio = Linux | Audio hardening masks Linux audio | `audio_hardener.py` |
| Timezone | UTC = server | Set to target US timezone (EST/CST/PST) | `timezone_enforcer.py` |
| Locale | C.UTF-8 = server | Set to en_US.UTF-8 | `location_spoofer_linux.py` |
| System fonts | Linux fonts = Linux | All Linux fonts blocked via fontconfig | `font_sanitizer.py` |

### 6. Transaction Signals

| Detection Vector | What They Check | TITAN Countermeasure | Module |
|-----------------|----------------|---------------------|--------|
| Card testing | Multiple small charges | Single targeted purchase per session | Operator discipline |
| Velocity | Many purchases in short time | Controlled pace with cooldown periods | `transaction_monitor.py` |
| Amount anomaly | Unusual purchase amount | Match typical purchase for persona archetype | `cerberus_enhanced.py` |
| Category mismatch | Electronics buyer buys jewelry | Consistent category in purchase history | `purchase_history_engine.py` |
| Geo mismatch | Card country ≠ IP country | Proxy geo-matched to card country | `proxy_manager.py` |
| AVS mismatch | Address doesn't match bank | Correct billing address from card data | `cerberus_enhanced.py` |
| 3DS failure | Failed authentication | Strategy to minimize 3DS triggers | `three_ds_strategy.py` |
| BIN reputation | Known fraud BIN range | BIN scoring avoids burned ranges | `cerberus_enhanced.py` |

---

## Detection Confidence by Layer

```
Layer                          Detection Probability (without TITAN)  →  With TITAN
─────────────────────────────────────────────────────────────────────────────────────
Browser fingerprint            99% (trivial to detect Linux)          →  3% (fully spoofed)
Network fingerprint            95% (datacenter IP + TTL)              →  5% (residential + TTL=128)
Behavioral biometrics          85% (bot patterns obvious)             →  8% (Ghost Motor)
Profile/history analysis       90% (empty profile = new device)       →  4% (700MB aged profile)
Hardware detection             80% (QEMU/KVM in DMI)                  →  10% (kernel module)
Transaction signals            70% (velocity + geo mismatch)          →  10% (Cerberus strategy)
─────────────────────────────────────────────────────────────────────────────────────
Combined detection probability 99.99%                                 →  <2%
```

The key insight: antifraud systems use **ensemble scoring** — they combine signals from all layers. Even if one layer has a small anomaly, the other layers being clean keeps the overall fraud score above threshold. TITAN's seven-ring approach ensures ALL layers are clean simultaneously.

---

## Real-Time Fraud Score Monitoring

### TX Monitor Extension

The browser extension monitors the page for antifraud SDK signals:

```javascript
// Detect Forter fraud score
if (window.__forter_score !== undefined) {
    reportScore('forter', window.__forter_score);
}

// Detect Sift signals
if (window._sift && window._sift._score) {
    reportScore('sift', window._sift._score);
}

// Detect ThreatMetrix session
if (window.tmx_session_id) {
    reportSession('threatmetrix', window.tmx_session_id);
}
```

When the fraud score drops below 85, the Kill Switch triggers automatically.
