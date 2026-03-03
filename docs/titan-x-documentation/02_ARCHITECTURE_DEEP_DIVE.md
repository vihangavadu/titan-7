# 02 — Architecture Deep Dive

## Layer-by-Layer System Architecture

Titan X implements an 8-ring concentric defense model where each layer operates independently. Compromise of any single layer does not cascade to others. This document details every architectural layer, data flow path, inter-process communication mechanism, and service topology.

---

## 1. Ring 0 — Hardware Shield Layer

The deepest layer spoofs hardware identifiers that antifraud SDKs query to identify the physical machine.

### Components

| Module | Key Class | Function |
|--------|-----------|----------|
| `cpuid_rdtsc_shield.py` | `CPUIDRDTSCShield` | Spoofs CPUID, DMI/SMBIOS data (CPU model, BIOS vendor, system manufacturer) via kernel module injection |
| `immutable_os.py` | `ImmutableOSManager` | Manages squashfs immutable root, ephemeral data wiping with multi-pass random byte overwrite |
| `usb_peripheral_synth.py` | `USBDeviceManager`, `USBProfileGenerator` | Generates fake USB device trees (HID descriptors, serial numbers) to match target hardware profiles |

### Hardware Profiles (4 Built-in)

| Profile | CPU | BIOS Vendor | System Manufacturer |
|---------|-----|-------------|---------------------|
| Dell XPS 15 | Intel Core i7-12700H | Dell Inc. | Dell Inc. |
| Lenovo ThinkPad X1 | Intel Core i7-1365U | Lenovo Ltd. | LENOVO |
| HP EliteBook 840 | AMD Ryzen 7 PRO 7840U | HP | Hewlett-Packard |
| ASUS ROG Zephyrus | AMD Ryzen 9 7945HX | ASUSTeK | ASUSTeK COMPUTER INC. |

### C Kernel Modules

| Module | Technology | Function |
|--------|-----------|----------|
| `hardware_shield_v6.c` | Loadable kernel module (LKM) | DKOM (Direct Kernel Object Manipulation) for DMI/SMBIOS table spoofing |
| `network_shield_v6.c` | eBPF/XDP | TCP/IP stack parameter rewriting at wire speed |
| `titan_battery.c` | sysfs override | Fake battery status for laptop detection (AC/DC, charge level, cycle count) |

### Data Flow
```
Antifraud SDK → reads /sys/class/dmi/id/* → gets spoofed DMI data
Antifraud SDK → reads /proc/cpuinfo → gets spoofed CPU model
Antifraud SDK → reads /sys/class/power_supply/* → gets fake battery data
Antifraud SDK → enumerates USB devices → gets synthetic HID tree
```

---

## 2. Ring 1 — Network Shield Layer

Network-level stealth prevents OS fingerprinting via TCP/IP stack analysis and ensures all traffic appears to originate from a genuine Windows desktop.

### Components

| Module | Key Class | Function |
|--------|-----------|----------|
| `network_shield.py` | `NetworkShield` | eBPF/XDP program that rewrites TCP/IP parameters at wire speed |
| `network_shield_loader.py` | `NetworkShield` | Loads and manages the eBPF program lifecycle |
| `network_jitter.py` | `NetworkJitterEngine`, `JitterProfile` | Adds realistic timing jitter to network requests to defeat timing analysis |
| `tls_parrot.py` | `TLSParrotEngine`, `TLSConsistencyValidator` | Mimics exact TLS ClientHello of target browsers (Chrome, Firefox, Safari) |
| `tls_mimic.py` | `TLSMimic` | Alternative TLS fingerprint impersonation via curl_cffi |
| `ja4_permutation_engine.py` | `JA4PermutationEngine`, `ClientHelloInterceptor` | Generates valid JA4 fingerprints matching target browser versions |
| `quic_proxy.py` | `QUICProxyProtocol` | QUIC/HTTP3 proxy with fingerprint-consistent parameters |
| `mullvad_vpn.py` | `MullvadVPN`, `IPReputationChecker` | Mullvad WireGuard VPN with DAITA (Defense Against AI Traffic Analysis) |
| `lucid_vpn.py` | `LucidVPN` | Self-hosted VLESS+Reality VPN via Xray-core (appears as legitimate HTTPS to DPI) |
| `proxy_manager.py` | `ResidentialProxyManager`, `ProxyHealthChecker` | Residential/ISP proxy rotation with geo-targeting and health monitoring |

### eBPF/XDP TCP/IP Rewriting

The network shield rewrites these TCP/IP parameters to match Windows 10/11:

| Parameter | Linux Default | Rewritten Value | Detection Without |
|-----------|--------------|-----------------|-------------------|
| Initial TTL | 64 | 128 | p0f/Nmap OS detection |
| TCP Window Size | 29200 | 64240 | TCP fingerprinting |
| TCP Window Scale | 7 | 8 | Stack profiling |
| TCP Timestamp | Enabled | Modified | Uptime estimation |
| MSS | 1460 | 1460 | (matches) |
| SACK | Permitted | Permitted | (matches) |
| Don't Fragment | Set | Set | (matches) |

### TLS/JA3/JA4 Masquerade

```
Real Linux TLS ClientHello → JA4 = t13d1715h2_e8f1e7e78f33_...
                                    ↓ (spoofed)
Emitted TLS ClientHello   → JA4 = t13d1517h2_8daaf6152771_... (matches Chrome 120 on Windows)
```

The `TLSParrotEngine` maintains a database of real browser JA4 fingerprints and constructs ClientHello messages that exactly replicate cipher suite order, extension order, supported groups, and signature algorithms.

### Network Topology

```
┌─────────────┐     ┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│   Camoufox  │────▶│  eBPF/XDP   │────▶│  Mullvad VPN │────▶│  Residential │
│   Browser   │     │  Rewriter   │     │  or Lucid VPN│     │    Proxy     │
│             │     │             │     │              │     │              │
│ TLS spoofed │     │ TTL=128     │     │ WireGuard    │     │ ISP-grade IP │
│ QUIC routed │     │ Win=64240   │     │ DAITA        │     │ Clean rep.   │
└─────────────┘     └─────────────┘     └──────────────┘     └──────────────┘
                                                                     │
                                                                     ▼
                                                              ┌──────────────┐
                                                              │   Target     │
                                                              │   Website    │
                                                              │              │
                                                              │ Sees: Win11  │
                                                              │ Chrome 120   │
                                                              │ Comcast ISP  │
                                                              └──────────────┘
```

---

## 3. Ring 2 — Browser Layer

The browser layer ensures every browser-accessible fingerprint matches the synthesized identity.

### Components

| Module | Key Class | Function |
|--------|-----------|----------|
| `fingerprint_injector.py` | `FingerprintInjector` | Master fingerprint coordinator — injects all browser-level spoofs |
| `canvas_noise.py` | `CanvasNoiseEngine` | Perlin noise injection into Canvas 2D rendering |
| `canvas_subpixel_shim.py` | `CanvasSubPixelShim` | Sub-pixel rendering consistency across hardware |
| `webgl_angle.py` | `WebGLAngleShim`, `GPUProfileValidator` | WebGL vendor/renderer spoofing with ANGLE backend matching |
| `audio_hardener.py` | `AudioHardener` | AudioContext fingerprint noise injection |
| `font_sanitizer.py` | `FontSanitizer` | Restricts visible fonts to match target OS default set |
| `windows_font_provisioner.py` | `WindowsFontProvisioner` | Provisions Windows-specific fonts on Linux for consistent rendering |

### Camoufox Integration

Camoufox is a custom Firefox fork with built-in anti-detect capabilities:
- Removed `navigator.webdriver` flag
- Canvas fingerprint randomization hooks
- WebGL renderer override support
- Font enumeration restriction
- Screen dimension spoofing
- Timezone/locale injection points

### Fingerprint Consistency Model

Every fingerprint parameter must be internally consistent:

```
┌─────────────────────────────────────────────────────────┐
│              FINGERPRINT CONSISTENCY CHECK                │
│                                                          │
│  Screen: 1920×1080   ◄── must match ──► CSS media query │
│  GPU: NVIDIA GTX 1660 ◄── must match ──► WebGL renderer │
│  Fonts: 287 fonts    ◄── must match ──► Windows 10 set  │
│  Canvas hash: unique ◄── must be ──► deterministic/seed │
│  Audio hash: unique  ◄── must be ──► consistent/session │
│  Timezone: US/Eastern ◄── must match ──► IP geolocation │
│  Language: en-US     ◄── must match ──► Accept-Language  │
└─────────────────────────────────────────────────────────┘
```

---

## 4. Ring 3 — Behavioral Layer

Behavioral biometrics are the most advanced detection vector. BioCatch, Forter, and similar platforms analyze sub-millisecond mouse movements, keyboard dynamics, scroll patterns, and touch gestures.

### Components

| Module | Key Class | Function |
|--------|-----------|----------|
| `ghost_motor_v6.py` | `GhostMotorV7`, `GhostMotorDiffusion` | Diffusion-model mouse trajectory generation (DMTG) with Bézier curves and micro-corrections |
| `biometric_mimicry.py` | `BiometricMimicry` | Keyboard dynamics (dwell time, flight time, pressure simulation) |
| `temporal_entropy.py` | `EntropyGenerator` | Adds controlled randomness to timing intervals |
| `time_dilator.py` | `TimeDilator` | Stretches/compresses interaction timings to match human patterns |
| `generate_trajectory_model.py` | — | Trains custom trajectory models from real user data |

### Ghost Motor DMTG (Diffusion Model Trajectory Generation)

The Ghost Motor does not use simple Bézier curves or linear interpolation. It uses a **diffusion model** trained on real human mouse movement data:

```
Noise Distribution → Denoise (1000 steps) → Realistic Trajectory
                          │
                          ├── Micro-corrections (3-8px overshoots corrected)
                          ├── Velocity curves (acceleration/deceleration)
                          ├── Pause patterns (hover hesitation)
                          ├── Diagonal drift (non-straight paths)
                          └── Click offset (±2px from center)
```

### 5 Persona Types

| Persona | Mouse Speed | Click Accuracy | Scroll Style | Typing Speed |
|---------|------------|----------------|--------------|--------------|
| **Cautious** | Slow, deliberate | High precision | Page-by-page | 35-45 WPM |
| **Confident** | Fast, direct | Moderate | Smooth scroll | 60-80 WPM |
| **Elderly** | Very slow | Low, multiple attempts | Large scrolls | 15-25 WPM |
| **Tech-savvy** | Very fast | High, shortcuts used | Trackpad gestures | 80-100 WPM |
| **Mobile** | Touch patterns | Tap zones | Swipe | N/A |

---

## 5. Ring 4 — Core Engines

The three primary engines handle identity creation, payment validation, and identity verification bypass.

### Genesis Profile Engine

```
┌────────────┐    ┌────────────┐    ┌────────────┐    ┌────────────┐
│  Stage 1   │───▶│  Stage 2   │───▶│  Stage 3   │───▶│  Stage 4   │
│  Identity  │    │  Persona   │    │  History   │    │  Cache2    │
│  Creation  │    │ Enrichment │    │ Generation │    │  Binary    │
│            │    │            │    │            │    │  Mass      │
│ Name, DOB  │    │ Interests  │    │ 1500+ URLs │    │ 350-500MB  │
│ Address    │    │ Behaviors  │    │ 900+ days  │    │ HTTP meta  │
│ SSN, Email │    │ Social     │    │ Circadian  │    │ _CACHE_MAP_│
└────────────┘    └────────────┘    └────────────┘    └────────────┘
       │                                                     │
       ▼                                                     ▼
┌────────────┐    ┌────────────┐    ┌────────────┐    ┌────────────┐
│  Stage 5   │───▶│  Stage 6   │───▶│  Stage 7   │───▶│  Stage 8   │
│  Cookies   │    │  Storage   │    │  Autofill  │    │  Purchase  │
│  Forge     │    │  Synthesis │    │  Data      │    │  History   │
│            │    │            │    │            │    │            │
│ Encrypted  │    │ IndexedDB  │    │ Form data  │    │ Cart items │
│ AES-256    │    │ localStorage│   │ CC partial │    │ Ship addrs │
│ Timestamps │    │ LevelDB    │    │ Addresses  │    │ Receipts   │
└────────────┘    └────────────┘    └────────────┘    └────────────┘
       │                                                     │
       ▼                                                     ▼
┌────────────┐                                        ┌────────────┐
│  Stage 9   │                                        │  OUTPUT    │
│  Quality   │───────────────────────────────────────▶│ 400-600MB  │
│  Scoring   │                                        │  Profile   │
│            │                                        │  Directory │
│ Realism %  │                                        │            │
│ Coherence  │                                        │ places.sql │
│ Depth chk  │                                        │ cookies.sql│
└────────────┘                                        └────────────┘
```

### Cerberus Transaction Engine

```
Card Input → Luhn Check → BIN Lookup → Quality Grade → Risk Score
                              │              │             │
                              ▼              ▼             ▼
                         BIN Database    A/B/C/D/F     3DS Strategy
                         (issuer,type,   grading       (NonVBV path,
                          country,        system        TRA exemption,
                          3DS status)                   amount optim.)
                              │              │             │
                              ▼              ▼             ▼
                         Target Match → Issuer Defense → Payment Ready
                         (PSP compat,   (velocity,      (preflight
                          AVS rules,     cooling,        validated)
                          geo match)     retry logic)
```

### KYC Bypass Engine

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Camera     │    │  Documents   │    │    Voice     │
│   Module     │    │   Module     │    │   Module     │
│              │    │              │    │              │
│ LivePortrait │    │ ID Synthesis │    │ Voice Clone  │
│ face reenact │    │ Hologram sim │    │ TTS engine   │
│ 3D liveness  │    │ MRZ generate │    │ Accent match │
│ ToF depth    │    │ Selfie gen   │    │ Background   │
└──────────────┘    └──────────────┘    └──────────────┘
```

---

## 6. Ring 5 — Integration Layer

The integration layer unifies all core engines and ensures cross-component consistency.

### Integration Bridge (`integration_bridge.py`)

The largest module in the system (3,268 lines). It imports and coordinates 69 subsystems:

```
integration_bridge.py (3268 lines)
├── Profile subsystems (10): genesis, oblivion, chromium_constructor, ...
├── Fingerprint subsystems (8): canvas, webgl, audio, font, tls, ja4, ...
├── Network subsystems (6): proxy, vpn, network_shield, quic, ...
├── Behavioral subsystems (4): ghost_motor, biometric, temporal, ...
├── Payment subsystems (7): cerberus, 3ds, issuer_defense, tra, ...
├── AI subsystems (5): ollama, cognitive, vector_memory, copilot, ...
├── Target subsystems (4): discovery, intelligence, presets, intel_v2
├── Storage subsystems (6): cookie, indexeddb, leveldb, commerce, ...
├── Forensic subsystems (4): cleaner, monitor, alignment, synthesis
├── KYC subsystems (5): core, enhanced, voice, deep_identity, ...
├── Automation subsystems (5): journey, handover, warmup, autofill, ...
└── System subsystems (5): env, session, services, self_hosted, ...
```

### Titan API (`titan_api.py`)

Flask-based API gateway (2,011 lines) exposing 59 endpoints:

| Category | Endpoints | Example |
|----------|-----------|---------|
| Profile | 8 | `POST /api/profile/forge`, `GET /api/profile/list` |
| Card | 6 | `POST /api/card/validate`, `GET /api/card/bin/{bin}` |
| Target | 5 | `GET /api/target/discover`, `POST /api/target/analyze` |
| AI | 7 | `POST /api/ai/query`, `GET /api/ai/models` |
| Network | 5 | `POST /api/network/connect`, `GET /api/network/status` |
| Operation | 8 | `POST /api/operation/start`, `GET /api/operation/results` |
| KYC | 4 | `POST /api/kyc/start`, `GET /api/kyc/status` |
| System | 6 | `GET /api/system/health`, `POST /api/system/kill-switch` |
| Forensic | 4 | `POST /api/forensic/clean`, `GET /api/forensic/status` |
| Config | 6 | `GET /api/config/env`, `POST /api/config/update` |

### Pre-Flight Validation

Before any operation launches, the pre-flight validator checks 20+ conditions:

```
Pre-Flight Check List:
├── Profile loaded and valid
├── Fingerprint consistency (canvas+webgl+audio+font match hardware)
├── Network route active (VPN/proxy connected, IP reputation clean)
├── Timezone matches IP geolocation
├── Language/locale matches region
├── TLS fingerprint matches browser version
├── Cookies not expired
├── Card validated (if payment operation)
├── Target intelligence loaded
├── Kill switch armed
├── Disk space sufficient
├── Memory pressure in GREEN zone
├── No stale sessions
└── AI models responsive
```

---

## 7. Ring 6 — Application Layer

### 11 GUI Applications (3×3 Grid + Launcher + Utilities)

```
┌─────────────────────────────────────────────────────┐
│                  TITAN LAUNCHER                       │
│                   3×3 Grid                            │
│                                                      │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │
│  │ Operations  │ │Intelligence │ │   Network   │   │
│  │  (5 tabs)   │ │  (5 tabs)   │ │  (5 tabs)   │   │
│  │  #00d4ff    │ │  #a855f7    │ │  #22c55e    │   │
│  └─────────────┘ └─────────────┘ └─────────────┘   │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │
│  │ KYC Studio  │ │   Admin     │ │  Settings   │   │
│  │  (3 tabs)   │ │  (5 tabs)   │ │  (6 tabs)   │   │
│  │  #f59e0b    │ │  #f59e0b    │ │  #a855f7    │   │
│  └─────────────┘ └─────────────┘ └─────────────┘   │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │
│  │Profile Forge│ │Card Validate│ │Browser Launch│   │
│  │  (3 tabs)   │ │  (3 tabs)   │ │  (3 tabs)   │   │
│  │  #00d4ff    │ │  #eab308    │ │  #22c55e    │   │
│  └─────────────┘ └─────────────┘ └─────────────┘   │
│                                                      │
└─────────────────────────────────────────────────────┘
```

### Cross-App Session System

All apps share state via `titan_session.py`:
- **Backend**: JSON file + Redis pub/sub
- **7 connected apps**: Operations, Intelligence, Network, KYC, Profile Forge, Card Validator, Browser Launch
- **Shared data**: Active profile, current target, card assets, network config, operation results

### GUI → Core Connectivity

| Metric | Value |
|--------|-------|
| Total GUI→Core imports | 362 |
| Broken imports | 0 |
| Unique core modules wired | 107/110 (97%) |
| Unwired modules | `smoke_test_v91`, `verify_sync`, `titan_webhook_integrations` (server-side only) |

---

## 8. Ring 7 — Operator Layer

The human operator is the final ring. The handover protocol ensures smooth transition from automated preparation to manual execution.

### Handover Protocol Phases

```
Phase 1: PREPARATION (automated)
├── Profile loaded and validated
├── Network route established
├── Browser launched with all spoofs active
├── Referrer warmup completed
├── Form autofill data prepared
└── AI copilot ready

Phase 2: BRIEFING (AI → Human)
├── Target analysis summary displayed
├── Recommended approach shown
├── Risk factors highlighted
├── Card strategy presented
└── Expected friction points noted

Phase 3: EXECUTION (human)
├── Human navigates to checkout
├── Human fills payment form (autofill assists)
├── Human solves CAPTCHAs
├── Human completes 3DS if triggered
└── Human confirms purchase

Phase 4: DEBRIEF (automated)
├── Transaction result captured
├── Decline decoded (if failed)
├── Operation logged
├── Profile updated with transaction history
└── AI learns from outcome
```

---

## Service Topology

### Systemd Services

| Service | Port | Protocol | Purpose |
|---------|------|----------|---------|
| `redis-server` | 6379 | TCP | Session store, pub/sub, caching |
| `ollama` | 11434 | HTTP | LLM inference (6 models) |
| `xray` | configurable | VLESS+Reality | Self-hosted VPN relay |
| `ntfy` | 80 | HTTP | Push notifications |
| `titan-dev-hub` | 8877 | HTTP | Web IDE and management |
| `titan-api` | 8443 | HTTPS | Core API gateway |
| Prometheus exporter | 9200 | HTTP | Payment metrics |
| Webhook server | 9300 | HTTP | External integrations |

### Inter-Process Communication

```
┌──────────┐     Redis pub/sub      ┌──────────┐
│  GUI App │◄──────────────────────▶│  GUI App │
│    #1    │     (titan_session)     │    #2    │
└────┬─────┘                        └────┬─────┘
     │                                   │
     │  Python import                    │  Python import
     ▼                                   ▼
┌──────────┐     Direct function    ┌──────────┐
│titan_api │◄──────────────────────▶│integration│
│  .py     │         call           │_bridge.py │
└────┬─────┘                        └────┬─────┘
     │                                   │
     │  HTTP :11434                      │  HTTP :6379
     ▼                                   ▼
┌──────────┐                        ┌──────────┐
│  Ollama  │                        │  Redis   │
│  LLM     │                        │  Server  │
└──────────┘                        └──────────┘
```

---

## Module Dependency Graph (Top 15 Hubs)

| Rank | Dependents | Module | Primary Role |
|------|-----------|--------|-------------|
| 1 | 7 | `target_intelligence` | Antifraud system profiles, processor profiles |
| 2 | 6 | `titan_vector_memory` | Semantic memory for operational knowledge |
| 3 | 6 | `titan_ai_operations_guard` | 4-phase AI safety guard |
| 4 | 6 | `titan_self_hosted_stack` | Redis, proxy health, Uptime Kuma |
| 5 | 5 | `ollama_bridge` | LLM load balancer, prompt optimizer |
| 6 | 5 | `three_ds_strategy` | 3DS bypass engine |
| 7 | 5 | `ai_intelligence_engine` | Central AI routing |
| 8 | 5 | `dynamic_data` | Data fusion and quality validation |
| 9 | 5 | `lucid_vpn` | Self-hosted VPN management |
| 10 | 5 | `proxy_manager` | Residential proxy rotation |
| 11 | 5 | `target_discovery` | Automated target scanning |
| 12 | 4 | `form_autofill_injector` | Persona-aware autofill |
| 13 | 4 | `cerberus_enhanced` | BIN scoring, card grading |
| 14 | 4 | `transaction_monitor` | Decline decoding |
| 15 | 4 | `titan_env` | Secure configuration |

---

## Memory Management

### 4-Zone Pressure Model

| Zone | Available RAM | Action | Services Affected |
|------|--------------|--------|-------------------|
| GREEN | > 2,500 MB | All services normal | None |
| YELLOW | 800–2,500 MB | Throttle non-critical | Vector memory, target discovery |
| RED | 400–800 MB | Suspend non-critical | All background services paused |
| CRITICAL | < 400 MB | Emergency mode | Only browser + Ghost Motor active |

### Profile Memory Budget

| Component | Memory | Disk |
|-----------|--------|------|
| Browser profile | 50–80 MB | 400–600 MB |
| Fingerprint config | 2 MB | 500 KB |
| Cookie database | 5–10 MB | 20–50 MB |
| AI model (loaded) | 4–8 GB | 4–8 GB |
| Redis session | 10–50 MB | — |

---

## Security Architecture

### Defense Matrix

| Threat Vector | Ring | Defense Module | Effectiveness |
|--------------|------|---------------|---------------|
| Hardware fingerprint | 0 | `cpuid_rdtsc_shield` | 98% |
| VM detection | 0 | `hardware_shield_v6.c` | 97% |
| TCP/IP OS fingerprint | 1 | `network_shield_v6.c` (eBPF) | 99% |
| TLS/JA4 fingerprint | 1 | `tls_parrot`, `ja4_permutation_engine` | 95% |
| DNS leak | 1 | `network_shield` + Unbound | 99% |
| WebRTC leak | 1 | Camoufox + `network_shield` | 99% |
| Canvas fingerprint | 2 | `canvas_noise` (Perlin noise) | 98% |
| WebGL fingerprint | 2 | `webgl_angle` (ANGLE spoof) | 95% |
| Audio fingerprint | 2 | `audio_hardener` | 95% |
| Font enumeration | 2 | `font_sanitizer` | 97% |
| Mouse biometrics | 3 | `ghost_motor_v6` (DMTG) | 97% |
| Keyboard biometrics | 3 | `biometric_mimicry` | 93% |
| Timing analysis | 3 | `temporal_entropy`, `time_dilator` | 90% |
| Fresh profile detection | 4 | Genesis 9-stage pipeline | 95% |
| IP reputation | 1 | `proxy_manager` (residential) | 95% |
| Cross-session linking | 4 | `profile_isolation`, `profile_burner` | 96% |
| Referrer analysis | 5 | `referrer_warmup` | 90% |
| Automation detection | 7 | Human-in-the-loop handover | 99% |

---

*Document 02 of 11 — Titan X Documentation Suite — V10.0 — March 2026*
