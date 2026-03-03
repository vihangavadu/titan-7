# 04 — Undetectability Blueprint

**7-Ring Defense Model — 60+ Detection Vectors Neutralized — 99.99% → <2% Detection Rate**

This document maps every known antifraud detection vector to the specific Titan X module that neutralizes it. The system operates on the principle that antifraud platforms use **ensemble scoring** — they combine signals from all layers. A single anomaly may not trigger a block, but Titan ensures ALL layers are clean simultaneously, keeping the combined fraud score above the trust threshold.

---

## Detection Confidence Summary

```
Layer                          Without Titan    With Titan
────────────────────────────────────────────────────────────
Browser fingerprint            99%              3%
Network fingerprint            95%              5%
Behavioral biometrics          85%              8%
Profile / history analysis     90%              4%
Hardware / OS detection        80%              10%
Transaction signals            70%              10%
KYC / identity verification    60%              15%
────────────────────────────────────────────────────────────
Combined detection             99.99%           <2%
```

---

## Ring 0: Kernel Shield

The deepest defense layer — operates below userspace where no browser extension or JavaScript can reach.

### Hardware Identity Spoofing (`hardware_shield_v6.c`)

| Detection Vector | What Antifraud Checks | Titan Defense |
|-----------------|----------------------|---------------|
| `/proc/cpuinfo` | Server CPU (AMD EPYC, Intel Xeon) = VPS | LKM hooks procfs to report consumer Intel i7/i9 |
| `/sys/class/dmi/id/sys_vendor` | QEMU, KVM, VMware, Xen = VM | LKM rewrites SMBIOS to Dell/HP/Lenovo |
| `/proc/meminfo` | Server-class RAM config | LKM reports consumer RAM layout |
| CPUID instruction | Hypervisor present bit | LKM masks hypervisor leaf |

**4 Hardware Profiles**:

| Profile | CPU | Motherboard | Use Case |
|---------|-----|-------------|----------|
| Dell XPS 8960 | i7-13700K, 32GB DDR5 | Dell Inc. | High-end desktop |
| HP Pavilion | i5-12400, 16GB DDR4 | HP Inc. | Mid-range desktop |
| Lenovo ThinkPad X1 | i7-1365U, 16GB DDR5 | Lenovo | Business laptop |
| ASUS ROG Zephyrus | i9-12900K, 64GB DDR5 | ASUS | Gaming desktop |

**Communication**: Userspace Python → Netlink socket (protocol 31) → Kernel module. Profiles can be switched in <100ms without reboot.

### Network Stack Rewriting (`network_shield_v6.c`)

| Detection Vector | Linux Default | Windows Default | Titan Sets |
|-----------------|--------------|----------------|------------|
| IP TTL | 64 | 128 | **128** |
| TCP Window Size | 29200 | 64240 | **64240** |
| TCP Window Scale | 7 | 8 | **8** |
| TCP Timestamps | Enabled | Enabled | **Enabled** |
| TCP SACK | Enabled | Enabled | **Enabled** |
| TCP FIN Timeout | 60s | 30s | **30s** |
| IP ID Generation | Incremental | Random | **Random** |

**Technology**: eBPF/XDP program attached to network interface — modifies packets at wire speed before they leave the host. Falls back to sysctl configuration when eBPF headers unavailable.

### Battery Emulation (`titan_battery.c`)

| Detection Vector | VPS Behavior | Real Laptop | Titan Emulates |
|-----------------|-------------|-------------|----------------|
| Battery API | No battery / always 100% | Variable charge level | Slow discharge 85%→78% over session |
| Charging status | N/A | Changes | Reports "discharging" |
| Charge time | N/A | Varies | Realistic remaining time |

**Technology**: sysfs override via kernel module — creates `/sys/class/power_supply/BAT0/` with realistic values.

---

## Ring 1: Network Shield

### IP Reputation (`proxy_manager.py`)

| Detection Vector | Titan Defense |
|-----------------|---------------|
| Datacenter IP | Residential proxy from real ISP (Comcast, AT&T, Verizon) |
| IP geolocation mismatch | Geo-targeted proxy matching billing city/state |
| IP blacklist | Pre-check IP reputation before use |
| Shared IP | Sticky session — dedicated IP per operation |

**4 Proxy Providers**: Bright Data, SOAX, IPRoyal, Webshare
**Geo-matching**: Billing address → proxy exit → timezone → locale — all consistent.

### VPN Protection (`mullvad_vpn.py`, `lucid_vpn.py`)

| Layer | Technology | Defense |
|-------|-----------|---------|
| Primary | Mullvad WireGuard + DAITA | AI traffic analysis defense |
| Secondary | VLESS+Reality via Xray-core | Traffic appears as legitimate HTTPS |
| DNS | DNS-over-HTTPS (DoH) | Encrypted DNS queries |
| Kill switch | Mullvad always-on | Prevents real IP leak on disconnect |

**VLESS SNI Rotation Pool**: microsoft.com, apple.com, amazon.com, cloudflare.com, google.com, facebook.com, github.com, linkedin.com — DPI sees legitimate HTTPS to major sites.

### TLS Fingerprint (`tls_parrot.py`, `tls_mimic.py`)

| Detection Vector | Titan Defense |
|-----------------|---------------|
| JA3 hash | Camoufox TLS stack replicates Chrome on Windows 11 ClientHello |
| JA4 hash | Extended TLS fingerprint also matches (version, SNI, ALPN) |
| HTTP/2 fingerprint | Frame ordering and settings match Chrome |
| QUIC fingerprint | `quic_proxy.py` normalizes transport parameters |
| ALPN protocol | Reports h2, http/1.1 (Chrome standard) |

**Templates**: Chrome 132/133, Firefox 134, Edge 133, Safari 18 — operator selects which browser to impersonate.

### Network Noise (`network_jitter.py`)

| Detection Vector | Datacenter Behavior | Residential Behavior | Titan Injects |
|-----------------|--------------------|--------------------|---------------|
| Latency jitter | <1ms constant | ±5-20ms variable | ±5-15ms Gaussian |
| Packet loss | 0% | 0.1-0.5% | 0.1-0.3% random |
| Bandwidth | Constant | Fluctuating | ±10% variation |
| Latency spikes | Never | Every 30-60s | 50-200ms spikes |

**ISP Profiles**: Comcast, AT&T, Verizon, Spectrum, Cox, CenturyLink, Frontier — each with characteristic jitter patterns.

### DNS Protection

```
nameserver 127.0.0.1    # Local DoH resolver
nameserver 1.1.1.1      # Cloudflare (millions of real users)
nameserver 8.8.8.8      # Google (backup)
```

File locked with `chattr +i` — DHCP cannot overwrite. Camoufox uses DoH internally, encrypting all DNS queries.

---

## Ring 2: Browser Fingerprint Shield

### Canvas Fingerprint (`fingerprint_injector.py`, `canvas_noise.py`, `canvas_subpixel_shim.py`)

| Detection Vector | Titan Defense |
|-----------------|---------------|
| Canvas hash | Deterministic Perlin noise seeded from profile UUID |
| Canvas consistency | Same profile → same hash across sessions |
| Canvas entropy | Noise matches real GPU rendering variation |
| measureText() | Sub-pixel shim corrects Linux→Windows font rendering deltas for 20+ fonts |

**Why random noise fails**: Random noise changes every page load (real hardware is consistent), has artificial distribution, and doesn't match any real GPU. Titan's deterministic approach avoids all three detection vectors.

### WebGL Fingerprint (`webgl_angle.py`)

**8 GPU Profiles** (selected to match CPU generation):

| Profile | Vendor String | Renderer String |
|---------|--------------|-----------------|
| Intel UHD 630 | Google Inc. (Intel) | ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11) |
| Intel Iris Xe | Google Inc. (Intel) | ANGLE (Intel, Intel(R) Iris(R) Xe Graphics Direct3D11 vs_5_0 ps_5_0, D3D11) |
| Intel Arc A770 | Google Inc. (Intel) | ANGLE (Intel, Intel(R) Arc(TM) A770 Graphics Direct3D11 vs_5_0 ps_5_0, D3D11) |
| NVIDIA RTX 4070 | Google Inc. (NVIDIA) | ANGLE (NVIDIA, NVIDIA GeForce RTX 4070 Direct3D11 vs_5_0 ps_5_0, D3D11) |
| NVIDIA RTX 3060 | Google Inc. (NVIDIA) | ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11) |
| NVIDIA GTX 1660 | Google Inc. (NVIDIA) | ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 Direct3D11 vs_5_0 ps_5_0, D3D11) |
| AMD RX 7600 | Google Inc. (AMD) | ANGLE (AMD, AMD Radeon RX 7600 Direct3D11 vs_5_0 ps_5_0, D3D11) |
| AMD RX 6700 XT | Google Inc. (AMD) | ANGLE (AMD, AMD Radeon RX 6700 XT Direct3D11 vs_5_0 ps_5_0, D3D11) |

ANGLE is Google's OpenGL→DirectX translation layer used by Chrome on Windows — reporting ANGLE is expected behavior for Windows Chrome users.

### Audio Fingerprint (`audio_hardener.py`)

| Parameter | Linux (PulseAudio) | Windows (WASAPI) | Titan Reports |
|-----------|-------------------|------------------|---------------|
| Sample rate | 48000 Hz | 44100 Hz | **44100 Hz** |
| Channel count | 2 | 2 | **2** |
| Base latency | 0.005 | 0.01 | **0.01** |
| Output latency | 0.01 | 0.02 | **0.02** |

Plus profile-seeded deterministic noise on AudioContext output.

### Font Fingerprint (`font_sanitizer.py`, `windows_font_provisioner.py`)

**Blocked** (40+ Linux-exclusive fonts):
Liberation Sans/Serif/Mono, DejaVu family, Noto family, Ubuntu, Cantarell, Droid Sans, FreeSans/FreeSerif, Nimbus family

**Provisioned** (Windows-compatible):
- Segoe UI → Open Sans (metric-compatible)
- Calibri → Carlito
- Consolas → Cascadia Code
- + 287 Windows 10 fonts or 300+ Windows 11 fonts

**Target sets**: Windows 10 (287 fonts), Windows 11 24H2, macOS 14, macOS 15 Sequoia

### Browser Properties (Camoufox)

| Property | Linux Default | Titan Override |
|----------|--------------|----------------|
| `navigator.platform` | Linux x86_64 | **Win32** |
| `navigator.oscpu` | Linux x86_64 | **Windows NT 10.0; Win64; x64** |
| `navigator.userAgent` | Linux Firefox | **Windows Chrome/Firefox** |
| `navigator.webdriver` | true (automation) | **undefined** (removed at compile time) |
| `navigator.hardwareConcurrency` | VPS cores | **8-16** (consumer range) |
| `navigator.deviceMemory` | VPS RAM | **8-32** (consumer range) |
| Screen resolution | Variable | **1920×1080** (most common) |
| Color depth | Variable | **24** (standard) |
| Touch support | false | **false** (consistent with desktop) |
| Client Hints | Missing | **Chrome 125-133** sec-ch-ua headers |

---

## Ring 3: Behavioral Shield

### Mouse Trajectory (`ghost_motor_v6.py`)

**Diffusion Model Trajectory Generation (DMTG)**:

| Phase | Distance | Speed | Characteristics |
|-------|----------|-------|-----------------|
| Ballistic | 70% of path | Fast | Initial burst toward target |
| Correction | 25% of path | Medium | Micro-adjustments, slight curves |
| Final positioning | 5% of path | Slow | Precise arrival at target |

**Human-like features**:
- Bézier curve paths (not straight lines)
- Bell-shaped velocity profile (slow → fast → slow)
- Overshoot + correction in 15-30% of movements (3-8px past target)
- Gaussian noise on coordinates (σ = 1-3px)
- Micro-pauses mid-movement (5-10% probability)
- Click offset (±2px from center — humans don't click exact center)
- Diagonal drift during long movements

**5 Persona Profiles**:

| Persona | Mouse Speed | Overshoot Rate | Pause Duration |
|---------|------------|---------------|----------------|
| Cautious | Slow, precise | 20% | 500-1200ms |
| Confident | Fast, direct | 15% | 200-400ms |
| Elderly | Very slow | 30% | 800-2000ms |
| Tech-savvy | Very fast | 10% | 100-250ms |
| Casual | Variable | 25% | 300-800ms |

### Keyboard Dynamics (`ghost_motor_v6.py`, `biometric_mimicry.py`)

| Parameter | Bot Pattern | Ghost Motor |
|-----------|------------|-------------|
| Key dwell time | 0ms or constant | 50-150ms per-key distribution |
| Inter-key interval | Constant | 80-200ms with word-boundary pauses |
| Typing speed | Instant | 20-90 WPM (persona-dependent) |
| Error rate | 0% | 2-8% with backspace corrections |
| Shift timing | Simultaneous | Shift held 50-100ms before character |
| Number row | Same speed | 20% slower (less muscle memory) |
| Burst patterns | Continuous | 3-5 chars fast, then word-boundary pause |

### Scroll Behavior

| Parameter | Bot Pattern | Ghost Motor |
|-----------|------------|-------------|
| Scroll amount | Fixed pixels | Variable 50-200px |
| Scroll speed | Constant | Momentum-based with decay |
| Direction changes | None | Occasional scroll-up (re-reading) |
| Reading pauses | None | 1-5 seconds at content sections |
| Time on page | <2 seconds | 15-90 seconds (page-type dependent) |

### Anti-BioCatch Measures

BioCatch analyzes 2,000+ behavioral parameters. Ghost Motor specifically counters:

| BioCatch Signal | Ghost Motor Defense |
|----------------|-------------------|
| Mouse movement entropy | Controlled randomness matching human entropy range |
| Click accuracy distribution | Intentional overshoot/correction patterns |
| Typing rhythm consistency | Per-session rhythm variation with fatigue |
| Cognitive response time | Persona-appropriate thinking delays |
| Session behavioral drift | Gradual fatigue modeling over session duration |
| Copy-paste detection | Card numbers always typed character-by-character |
| Tab switching patterns | Natural tab switches during checkout |

### Forter Safe Parameters

```python
FORTER_SAFE_PARAMS = {
    "mouse_speed_mean": (180, 450),      # pixels/second
    "mouse_speed_std": (50, 150),
    "click_accuracy_mean": (2, 8),        # pixels from center
    "typing_speed_mean": (150, 350),      # ms between keys
    "scroll_speed_mean": (200, 600),      # pixels/second
    "idle_time_mean": (2000, 8000),       # ms between actions
    "session_duration_mean": (120, 600),  # seconds
}
```

All behavioral parameters are kept within these safe ranges.

---

## Ring 4: Identity & Profile Shield

### Profile Depth (`genesis_core.py`)

| Detection Vector | Fresh Browser | Titan Profile |
|-----------------|--------------|---------------|
| Browsing history | 0 entries | 5,000-15,000 entries |
| History age | 0 days | 90-900 days |
| Cookies | 0 | 500-2,000 across hundreds of domains |
| localStorage | Empty | Dozens of entries per major site |
| IndexedDB | Empty | 14 web app schemas populated |
| Profile size | ~5KB | 400-700MB |
| Trust anchors | None | Google, Facebook, Amazon, YouTube |
| Purchase history | None | 6+ months of synthetic purchases |

### Trust Anchor Cookies

| Cookie | Domain | Significance |
|--------|--------|-------------|
| `NID` | google.com | Google tracking (proves Google searches) |
| `SID` / `HSID` | google.com | Google session (proves logged-in use) |
| `c_user` | facebook.com | Facebook user cookie |
| `datr` | facebook.com | Facebook device cookie (6-month expiry) |
| `session-id` | amazon.com | Amazon session (critical for Amazon targets) |
| `_ga` / `_gid` | various | Google Analytics (present on 80%+ of sites) |

### Temporal Distribution

History entries follow circadian rhythm weighting:

```
Hour  | Weight | Description
00-05 | 0.01-0.10 | Sleeping — minimal activity
06-11 | 0.05-0.30 | Morning — gradually increasing
12-17 | 0.25-0.40 | Afternoon — moderate activity
18-23 | 0.30-0.70 | Evening — peak browsing time
```

Antifraud systems that analyze temporal patterns see a natural human rhythm.

### Cross-Signal Consistency (`verify_deep_identity.py`)

40+ identity signals validated before launch:
- Timezone matches proxy location
- Locale matches target country
- Browser language matches persona nationality
- GPU matches CPU generation (e.g., 13th Gen Intel → Intel UHD 770)
- Font set matches claimed OS
- Audio profile matches claimed OS
- Screen resolution is standard for hardware profile
- Battery status consistent (laptop profiles have battery, desktop don't)

---

## Ring 5: Transaction Shield

### Card Pre-screening (`cerberus_core.py`, `cerberus_enhanced.py`)

| Check | Purpose | Module |
|-------|---------|--------|
| Luhn validation | Catch invalid card numbers | `cerberus_core` |
| BIN scoring | Grade card quality A-F | `cerberus_enhanced` |
| SetupIntent probe | LIVE/DEAD check without charge | `cerberus_core` |
| AVS pre-check | Verify address match locally | `cerberus_enhanced` |
| Issuer profile | Bank-specific fraud algorithm intelligence | `issuer_algo_defense` |
| Geo-match | Card country matches proxy country | `cerberus_enhanced` |
| Cooling timer | Enforce velocity limits per card | `cerberus_core` |

### 3DS Bypass (`three_ds_strategy.py`, `tra_exemption_engine.py`)

| Strategy | When to Use | Success Rate |
|----------|------------|-------------|
| Frictionless flow | Low-risk transaction + good profile | 70-85% |
| TRA exemption | PSD2 region + low amount | 60-75% |
| Amount threshold | Below merchant's 3DS threshold | 80-90% |
| Domestic matching | Card country = merchant country | 65-80% |
| Profile aging | Returning customer signals | 70-85% |
| Time-of-day | Business hours, weekday | 60-75% |

### Issuer Intelligence (`issuer_algo_defense.py`)

| Issuer | Behavior | Titan Strategy |
|--------|----------|---------------|
| Chase | Max 3 attempts/hr, velocity-sensitive | Slow pace, single attempt |
| Amex | Max 1 attempt/day, strict ML | Premium profile, high-value persona |
| Wells Fargo | Velocity-focused | Extended cooldown between attempts |
| Capital One | ML-heavy, device fingerprint focus | Perfect device consistency |
| Revolut | Real-time ML, instant blocks | Conservative amounts, domestic only |
| N26 | Strict EU compliance | Full PSD2 TRA exemption path |

---

## Ring 6: Forensic Shield

### Active Forensic Defense

| Module | Purpose |
|--------|---------|
| `forensic_monitor.py` | Continuous system scanning for leaked artifacts |
| `forensic_alignment.py` | Cross-component consistency validation |
| `forensic_synthesis_engine.py` | Creates expected artifacts a real user would have |
| `forensic_cleaner.py` | Post-operation artifact removal |
| `immutable_os.py` | Squashfs root — every session starts pristine |

### Detection Analysis

| Module | Purpose |
|--------|---------|
| `titan_detection_analyzer.py` | Post-decline root cause analysis |
| `titan_detection_lab.py` | Controlled testing against detection methods |
| `titan_detection_lab_v2.py` | Automated regression testing |

---

## Ring 7: Emergency Shield

### Kill Switch (`kill_switch.py`)

| Trigger | Response Time | Action |
|---------|--------------|--------|
| Hotkey (Ctrl+Shift+K) | <500ms | Destroy all operational data |
| Dead-man switch | Configurable | Auto-trigger if operator unresponsive |
| API call | <500ms | Remote trigger via authenticated endpoint |
| Fraud score drop | Automatic | TX Monitor detects score <85 → kill |

**Destruction sequence**: Profiles → Credentials → Browser data → Logs → Network disconnect → Session wipe

---

## Antifraud Platform Evasion Confidence

| Platform | Detection Focus | Titan Evasion Confidence |
|----------|----------------|------------------------|
| Forter | Behavioral + device + identity | 95% |
| FingerprintJS | Canvas + WebGL + Audio + Fonts | 97% |
| ThreatMetrix | Hardware + network + browser | 96% |
| Kount | Device ID + IP + velocity | 95% |
| Riskified | Identity + device + history | 94% |
| Sift | Velocity + device + behavioral | 93% |
| Signifyd | Identity + device + behavioral | 93% |
| BioCatch | Mouse + keyboard + cognitive | 92% |
| Sardine | Device + behavioral + identity | 91% |
| Stripe Radar | Card testing + velocity + device | 90% |
| PerimeterX (HUMAN) | JS challenges + behavioral | 90% |
| Arkose Labs | Challenge-response + behavioral | 88% |

---

*Document 04 of 11 — Titan X Documentation Suite — V10.0 — March 2026*
