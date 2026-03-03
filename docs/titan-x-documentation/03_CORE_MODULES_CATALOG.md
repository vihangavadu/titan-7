# 03 — Complete Core Modules Catalog

**118 Python Modules + 3 C Kernel Modules — Organized by 13 Categories**

Every module in the `src/core/` directory is documented here with its purpose, key classes, exported API, dependencies, and real-world operational impact. Modules are ordered by category and dependency level.

---

## Category 1: ORCHESTRATION (6 modules)

Central control plane — these modules wire everything together.

### 1.1 `integration_bridge.py` (3,268 lines)

**Purpose**: Central integration hub connecting 69 subsystems into a unified API.

| Export | Type | Description |
|--------|------|-------------|
| `TitanIntegrationBridge` | Class | Main orchestrator — imports and coordinates all core modules |
| `BridgeConfig` | Dataclass | Configuration for bridge initialization |
| `BridgeState` | Dataclass | Runtime state tracking (active subsystems, health) |

**Subsystem Categories (69 total)**:
- Profile (10): genesis, oblivion, chromium_constructor, multilogin_forge, antidetect_importer, level9_antidetect, profile_realism, advanced_profile, profile_isolation, profile_burner
- Fingerprint (8): canvas, webgl, audio, font, tls_parrot, ja4, ghost_motor, biometric
- Network (6): proxy, vpn (mullvad+lucid), network_shield, quic, network_jitter, location_spoofer
- Behavioral (4): ghost_motor, biometric_mimicry, temporal_entropy, time_dilator
- Payment (7): cerberus_core, cerberus_enhanced, 3ds_strategy, tra_exemption, issuer_defense, transaction_monitor, payment_preflight
- AI (5): ollama_bridge, cognitive_core, vector_memory, copilot, onnx_engine
- Target (4): discovery, intelligence, presets, intel_v2
- Storage (6): cookie_forge, indexeddb, leveldb, commerce_injector, chromium_commerce, purchase_history
- Forensic (4): cleaner, monitor, alignment, synthesis
- KYC (5): core, enhanced, voice, deep_identity, first_session_bias
- Automation (5): journey, handover, warmup, autofill, orchestrator
- System (5): env, session, services, self_hosted, webhook

**Depended by**: Every GUI app (via titan_api.py)
**Real-world impact**: The glue that holds the entire system together. Without it, modules operate in isolation.

---

### 1.2 `titan_api.py` (2,011 lines)

**Purpose**: Flask-based API gateway exposing 59 REST endpoints.

| Export | Type | Description |
|--------|------|-------------|
| `TitanAPI` | Class | Flask application with all route handlers |
| `APIResponse` | Dataclass | Standardized response format |

**Endpoint Categories (59 total)**:
- Profile: 8 endpoints (forge, list, load, delete, export, import, validate, score)
- Card: 6 endpoints (validate, bin_lookup, grade, history, cooling, strategy)
- Target: 5 endpoints (discover, analyze, presets, intelligence, health)
- AI: 7 endpoints (query, models, status, copilot, memory, train, config)
- Network: 5 endpoints (connect, disconnect, status, proxy_health, ip_check)
- Operation: 8 endpoints (start, stop, results, log, replay, preflight, handover, kill)
- KYC: 4 endpoints (start, status, challenges, camera)
- System: 6 endpoints (health, services, config, env, metrics, kill_switch)
- Forensic: 4 endpoints (clean, status, scan, report)
- Config: 6 endpoints (get, update, reset, export, import, validate)

**Depends on**: integration_bridge (59 module imports)
**Real-world impact**: HTTP API layer enabling programmatic access and the web-based Dev Hub IDE.

---

### 1.3 `titan_master_automation.py` (1,898 lines)

**Purpose**: End-to-end automation orchestrator for complete operation lifecycle.

| Export | Type | Description |
|--------|------|-------------|
| `TitanMasterAutomation` | Class | Full pipeline: target → profile → validate → launch → monitor |

**Depends on**: integration_bridge, titan_env
**Real-world impact**: Automates the preparation phase so the operator only handles final checkout execution.

---

### 1.4 `titan_autonomous_engine.py` (1,572 lines)

**Purpose**: Self-directed AI engine for continuous autonomous operation discovery.

| Export | Type | Description |
|--------|------|-------------|
| `AutonomousEngine` | Class | AI-driven target discovery, profile optimization, and strategy adaptation |

**Depends on**: ai_intelligence_engine, target_discovery, titan_realtime_copilot
**Real-world impact**: Continuously improves success rates by learning from operational outcomes.

---

### 1.5 `titan_master_verify.py` (1,448 lines)

**Purpose**: 4-layer master verification protocol ensuring system readiness.

| Export | Type | Description |
|--------|------|-------------|
| `VerificationOrchestrator` | Class | Layer 0–3 verification (Kernel, Network, Environment, Identity) |
| `RemediationEngine` | Class | Auto-fixes discovered issues |

**Layers**: L0 (Kernel Shield) → L1 (Network Shield) → L2 (Environment) → L3 (Identity & Time)
**Real-world impact**: Defense-in-depth verification prevents operations from launching with undetected configuration errors.

---

### 1.6 `cockpit_daemon.py` (1,206 lines)

**Purpose**: Privileged backend daemon for zero-terminal GUI operations.

| Export | Type | Description |
|--------|------|-------------|
| `CockpitDaemon` | Class | Unix socket server with HMAC-SHA256 command signing |
| `CommandQueue` | Class | Priority queue for privileged operations |

**Security**: GUI runs as standard user; all privileged ops (kernel module loading, eBPF, network config) go through signed IPC.
**Real-world impact**: Principle of Least Privilege architecture with full audit logging.

---

## Category 2: AI / LLM (8 modules)

AI reasoning layer — routes tasks to 6 Ollama models + ONNX CPU inference.

### 2.1 `ai_intelligence_engine.py` (1,842 lines)

**Purpose**: Unified AI intelligence for BIN analysis, pre-flight advice, target recon, 3DS strategy, and behavioral tuning.

| Export | Type | Description |
|--------|------|-------------|
| `AIIntelligenceEngine` | Class | Central AI router with 8 feature modules |
| `AIModelSelector` | Class | Task-to-model routing based on llm_config.json |
| `AI3DSStrategy` | Class | AI-driven 3DS bypass recommendation |
| `AIDeclineAutopsy` | Class | AI analysis of decline codes and root causes |

**8 Features**: bin_analysis, preflight_advisor, target_recon, 3ds_strategy, profile_audit, behavioral_tuning, operation_planner, web_intelligence
**Depended by**: 5 modules
**Real-world impact**: AI-powered strategic advice that adapts to changing conditions in real-time.

---

### 2.2 `ollama_bridge.py` (1,665 lines)

**Purpose**: Multi-provider LLM bridge with task-specific routing and load balancing.

| Export | Type | Description |
|--------|------|-------------|
| `LLMLoadBalancer` | Class | Routes requests across 6 Ollama models based on task type |
| `PromptOptimizer` | Class | Compresses/optimizes prompts for token efficiency |

**Models**: titan-analyst (qwen2.5:7b), titan-strategist (deepseek-r1:8b), titan-fast (mistral:7b), + 3 base models
**Task routes**: 57 total (23 analyst + 21 strategist + 13 fast)
**Caching**: Disk-based with 24h TTL
**Depended by**: 5 modules
**Real-world impact**: Ensures AI capabilities are always available with optimal model selection per task.

---

### 2.3 `cognitive_core.py` (1,539 lines)

**Purpose**: Cloud vLLM integration for sub-200ms multimodal inference.

| Export | Type | Description |
|--------|------|-------------|
| `CognitiveCoreLocal` | Class | Local Ollama inference wrapper |
| `TitanCognitiveCore` | Class | Cloud vLLM client with PagedAttention |

**Capabilities**: Vision + text multimodal analysis, CAPTCHA solving, DOM analysis, risk assessment
**Real-world impact**: Enables real-time AI decision-making during operations without latency bottlenecks.

---

### 2.4 `titan_agent_chain.py` (894 lines)

**Purpose**: LangChain-based agent orchestration with custom tool registry.

| Export | Type | Description |
|--------|------|-------------|
| `TitanChain` | Class | Agent chain executor |
| `TitanAgent` | Class | Individual agent with tool access |
| `TitanToolRegistry` | Class | Custom tool definitions for Titan operations |

**Real-world impact**: Multi-step reasoning chains for complex operational decisions.

---

### 2.5 `titan_realtime_copilot.py` (1,312 lines)

**Purpose**: Real-time AI copilot providing live guidance during operations.

| Export | Type | Description |
|--------|------|-------------|
| `RealtimeCopilot` | Class | Live guidance engine with contextual awareness |

**Provides**: Risk alerts, timing suggestions, behavioral guidance, abort recommendations
**Real-world impact**: AI co-pilot that augments operator decision-making without touching the browser.

---

### 2.6 `titan_ai_operations_guard.py` (1,089 lines)

**Purpose**: 4-phase AI safety guard preventing AI hallucination-driven failures.

| Export | Type | Description |
|--------|------|-------------|
| `AIOperationsGuard` | Class | Input validation → Output verification → Action gating → Rollback |
| `GuardVerdict` | Dataclass | Pass/fail/warn result with reasoning |

**Depended by**: 6 modules
**Real-world impact**: Prevents AI models from recommending actions that would compromise operations.

---

### 2.7 `titan_vector_memory.py` (889 lines)

**Purpose**: Semantic vector memory for operational knowledge persistence.

| Export | Type | Description |
|--------|------|-------------|
| `TitanVectorMemory` | Class | Sentence-transformer embeddings + vector search |
| `SearchResult` | Dataclass | Ranked search results with relevance scores |

**Depended by**: 6 modules (top hub)
**Real-world impact**: Operational knowledge accumulates over time — past successes/failures inform future strategy.

---

### 2.8 `titan_onnx_engine.py` (375 lines)

**Purpose**: ONNX Runtime CPU inference for Phi-4-mini INT4 model.

| Export | Type | Description |
|--------|------|-------------|
| `TitanOnnxEngine` | Class | ONNX GenAI inference with ~50MB model |

**Task routes**: 33 fast-response tasks (classification, validation, quick analysis)
**Real-world impact**: Sub-100ms inference for time-critical decisions without GPU dependency.

---

## Category 3: BROWSER / PROFILE (10 modules)

Profile generation, browser construction, and anti-detect import/export.

### 3.1 `genesis_core.py` (2,158 lines)

**Purpose**: Core profile generation engine — creates 400–600MB forensic-grade browser profiles.

| Export | Type | Description |
|--------|------|-------------|
| `GenesisEngine` | Class | 9-stage profile forge pipeline |
| `ProfileConfig` | Dataclass | Target, persona, hardware, network configuration |

**9 Stages**: Identity → Persona → History (1500+ URLs, 900+ days) → Cache2 Binary (350–500MB) → Cookies (AES-256 encrypted) → Storage (IndexedDB/localStorage/LevelDB) → Autofill → Purchase History → Quality Scoring
**Depended by**: 3 modules
**Real-world impact**: The foundation of every operation — a thin profile is the #1 detection indicator.

---

### 3.2 `oblivion_forge.py` (1,876 lines)

**Purpose**: Chromium-based profile forge with Chrome crypto engine for encrypted cookie databases.

| Export | Type | Description |
|--------|------|-------------|
| `OblivionForgeEngine` | Class | Chrome profile constructor with DPAPI-compatible encryption |
| `ChromeCryptoEngine` | Class | AES-256-GCM cookie/password encryption matching Chrome's format |

**Real-world impact**: Creates Chrome-compatible profiles with correctly encrypted credential stores.

---

### 3.3 `chromium_constructor.py` (1,654 lines)

**Purpose**: Low-level Chromium profile directory builder.

| Export | Type | Description |
|--------|------|-------------|
| `ProfileConstructor` | Class | Creates complete Chrome profile directory structure |

**Creates**: Preferences, Bookmarks, History, Login Data, Web Data, Cookies, Local State, Extensions
**Real-world impact**: Byte-perfect Chromium profile directories that pass structural validation.

---

### 3.4 `multilogin_forge.py` (1,432 lines)

**Purpose**: MultiLogin-compatible profile format generator.

| Export | Type | Description |
|--------|------|-------------|
| `MultiloginForgeEngine` | Class | Generates profiles in MultiLogin X format |

**Real-world impact**: Interoperability with MultiLogin ecosystem for profile import/export.

---

### 3.5 `antidetect_importer.py` (987 lines)

**Purpose**: Import profiles from other anti-detect browser platforms.

| Export | Type | Description |
|--------|------|-------------|
| `OblivionImporter` | Class | Imports from MultiLogin, GoLogin, Dolphin, Octo formats |

**Real-world impact**: Migrates existing profiles from competitor platforms into Titan format.

---

### 3.6 `level9_antidetect.py` (1,876 lines)

**Purpose**: Maximum-stealth anti-detect layer combining all fingerprint modules.

| Export | Type | Description |
|--------|------|-------------|
| `Level9Antidetect` | Class | Unified anti-detect orchestrator |

**Combines**: All fingerprint modules into a single coherent anti-detect configuration
**Real-world impact**: One-call activation of all fingerprint spoofing with guaranteed cross-component consistency.

---

### 3.7 `profile_realism_engine.py` (1,156 lines)

**Purpose**: Profile quality scoring and realism verification.

| Export | Type | Description |
|--------|------|-------------|
| `ProfileRealismEngine` | Class | Scores profiles on 12 realism metrics |

**Metrics**: History depth, cookie freshness, storage density, autofill completeness, cache size, fingerprint consistency, behavioral baseline, cross-site presence, temporal distribution, purchase history, social tokens, device diversity
**Real-world impact**: Quantifies profile quality before operations — prevents launching with subpar profiles.

---

### 3.8 `advanced_profile_generator.py` (1,432 lines)

**Purpose**: Demographic-consistent persona data generation.

| Export | Type | Description |
|--------|------|-------------|
| `AdvancedProfileGenerator` | Class | Name, DOB, address, email, phone, employment — demographically consistent |

**Real-world impact**: Ensures identity data is internally consistent — age matches credit history, address matches region.

---

### 3.9 `profile_isolation.py` (654 lines)

**Purpose**: Profile sandboxing preventing cross-contamination.

| Export | Type | Description |
|--------|------|-------------|
| `ProfileIsolation` | Class | Filesystem isolation, process isolation, network namespace isolation |

**Real-world impact**: Prevents profiles from leaking data into each other — essential for multi-profile operations.

---

### 3.10 `profile_burner.py` (876 lines)

**Purpose**: Secure profile destruction with forensic-grade wiping.

| Export | Type | Description |
|--------|------|-------------|
| `ProfileBurner` | Class | Multi-pass random overwrite → unlink → verify |

**Real-world impact**: Ensures destroyed profiles cannot be recovered even with forensic tools.

---

## Category 4: FINGERPRINT (11 modules)

Low-level browser fingerprint spoofing and consistency enforcement.

### 4.1 `fingerprint_injector.py` (1,543 lines)

**Purpose**: Master fingerprint orchestrator injecting consistent browser fingerprints.

| Export | Type | Description |
|--------|------|-------------|
| `FingerprintInjector` | Class | Coordinates UA, Client Hints, WebRTC, media devices |

**Supports**: Chrome 125–133 Client Hints, Windows 10/11, macOS Sequoia
**Deterministic**: Same profile UUID always produces identical fingerprint
**Real-world impact**: Central nervous system of fingerprint consistency.

---

### 4.2 `canvas_noise.py` (432 lines)

**Purpose**: Perlin noise injection into Canvas 2D rendering.

| Export | Type | Description |
|--------|------|-------------|
| `CanvasNoiseEngine` | Class | Deterministic noise seeded from profile UUID |

**Technique**: Perlin noise at sub-pixel level — unique per profile but consistent across sessions
**Real-world impact**: Defeats canvas fingerprinting (used by 90%+ of antifraud SDKs).

---

### 4.3 `canvas_subpixel_shim.py` (654 lines)

**Purpose**: Corrects Canvas measureText() rendering differences between Linux and Windows.

| Export | Type | Description |
|--------|------|-------------|
| `CanvasSubPixelShim` | Class | Scaling factors for 20+ commonly probed fonts |

**Fonts covered**: Trebuchet MS, Impact, Lucida Console, Comic Sans, Palatino, Consolas, +14 more
**Real-world impact**: Defeats advanced canvas fingerprinting that measures sub-pixel rendering deltas.

---

### 4.4 `webgl_angle.py` (1,234 lines)

**Purpose**: WebGL vendor/renderer spoofing with ANGLE backend matching.

| Export | Type | Description |
|--------|------|-------------|
| `WebGLAngleShim` | Class | GPU profile injection |
| `GPUProfileValidator` | Class | Validates GPU profile consistency |

**8 GPU Profiles**: NVIDIA RTX 4070, RTX 3060, GTX 1660, Intel Iris Xe, Intel Arc A770, AMD RX 7600, AMD RX 6700 XT, Intel UHD 630
**Real-world impact**: Prevents WebGL-based OS detection via Mesa driver string leaks.

---

### 4.5 `audio_hardener.py` (765 lines)

**Purpose**: AudioContext fingerprint noise injection.

| Export | Type | Description |
|--------|------|-------------|
| `AudioHardener` | Class | OS-specific audio profile injection |

**Profiles**: Windows 10 (WASAPI), Windows 11 24H2 (WASAPI), macOS 14 (CoreAudio), macOS Sequoia
**Real-world impact**: Prevents AudioContext fingerprint OS detection (PulseAudio/PipeWire vs WASAPI).

---

### 4.6 `font_sanitizer.py` (876 lines)

**Purpose**: Blocks Linux-exclusive fonts and enforces Windows-appropriate font visibility.

| Export | Type | Description |
|--------|------|-------------|
| `FontSanitizer` | Class | Blocks 40+ Linux fonts, enforces target OS font set |

**Targets**: Windows 10 (287 fonts), Windows 11 24H2, macOS 14, macOS 15 Sequoia
**Real-world impact**: Font enumeration is one of the most reliable OS detection methods.

---

### 4.7 `windows_font_provisioner.py` (770 lines)

**Purpose**: Installs Windows-compatible fonts and creates fontconfig aliases.

| Export | Type | Description |
|--------|------|-------------|
| `WindowsFontProvisioner` | Class | Installs metric-compatible alternatives for Windows fonts |

**Maps**: Segoe UI → Open Sans, Calibri → Carlito, Consolas → Cascadia Code
**Real-world impact**: Ensures positive font detection (Windows fonts present) + negative (Linux fonts absent).

---

### 4.8 `ghost_motor_v6.py` (1,876 lines)

**Purpose**: Diffusion-model mouse trajectory generation (DMTG).

| Export | Type | Description |
|--------|------|-------------|
| `GhostMotorV7` | Class | Bézier + minimum-jerk trajectory engine |
| `GhostMotorDiffusion` | Class | Full diffusion-model trajectory generation |

**5 Persona Types**: Cautious (slow, precise), Confident (fast, direct), Elderly (very slow, multiple attempts), Tech-savvy (shortcuts, fast), Mobile (touch patterns)
**Features**: Micro-corrections (3–8px overshoots), velocity curves, pause patterns, diagonal drift, click offset (±2px)
**Real-world impact**: Defeats BioCatch, Forter, and all behavioral biometric systems.

---

### 4.9 `biometric_mimicry.py` (987 lines)

**Purpose**: Keyboard dynamics and input behavioral simulation.

| Export | Type | Description |
|--------|------|-------------|
| `BiometricMimicry` | Class | Dwell time, flight time, pressure simulation |

**Real-world impact**: Defeats keyboard biometric analysis (typing patterns are unique per person).

---

### 4.10 `tls_parrot.py` (987 lines)

**Purpose**: Exact TLS ClientHello fingerprint parroting for target browsers.

| Export | Type | Description |
|--------|------|-------------|
| `TLSParrotEngine` | Class | Browser-specific TLS template engine |
| `TLSConsistencyValidator` | Class | Validates TLS fingerprint matches claimed browser |

**Templates**: Chrome 132/133, Firefox 134, Edge 133, Safari 18
**Real-world impact**: Prevents CDN-level blocking from TLS/JA3 mismatch detection.

---

### 4.11 `tls_mimic.py` (543 lines)

**Purpose**: Alternative TLS fingerprint impersonation via curl_cffi.

| Export | Type | Description |
|--------|------|-------------|
| `TLSMimic` | Class | curl_cffi-based Chrome TLS impersonation |

**Real-world impact**: Backup TLS spoofing path using compiled C library for exact Chrome TLS replication.

---

## Category 5: NETWORK / PROXY (7 modules)

VPN, proxy management, and network-level stealth.

### 5.1 `proxy_manager.py` (1,321 lines)

**Purpose**: Residential proxy connections with geo-targeting and health monitoring.

| Export | Type | Description |
|--------|------|-------------|
| `ResidentialProxyManager` | Class | Multi-provider proxy rotation |
| `ProxyHealthChecker` | Class | Continuous proxy health verification |

**Providers**: Bright Data, SOAX, IPRoyal, Webshare
**Features**: Geographic targeting, automatic failover, IP reputation checking, session persistence
**Depended by**: 5 modules
**Real-world impact**: Clean residential IPs are the foundation — a flagged IP = instant decline.

---

### 5.2 `network_shield.py` (876 lines)

**Purpose**: eBPF/XDP TCP/IP header rewriting at kernel level.

| Export | Type | Description |
|--------|------|-------------|
| `NetworkShield` | Class | eBPF program manager for TCP/IP rewriting |

**Rewrites**: TTL (64→128), TCP Window (29200→64240), Window Scale (7→8), TCP Timestamps
**Real-world impact**: Eliminates passive OS fingerprinting (p0f, Nmap) — the #1 network detection vector.

---

### 5.3 `network_shield_loader.py` (432 lines)

**Purpose**: eBPF program lifecycle management.

| Export | Type | Description |
|--------|------|-------------|
| `NetworkShield` | Class | Loads, attaches, and monitors eBPF/XDP programs |

**Real-world impact**: Ensures eBPF programs are correctly loaded before operations begin.

---

### 5.4 `network_jitter.py` (654 lines)

**Purpose**: Realistic background network noise generation.

| Export | Type | Description |
|--------|------|-------------|
| `NetworkJitterEngine` | Class | Background traffic generator |
| `JitterProfile` | Dataclass | ISP-specific noise profile |

**ISP Profiles**: Comcast, AT&T, Verizon, Spectrum, Cox, CenturyLink, Frontier
**Generates**: Windows Update checks, telemetry pings, OneDrive sync, DNS resolver noise
**Real-world impact**: Prevents "silent connection" detection — real Windows PCs are never silent.

---

### 5.5 `quic_proxy.py` (543 lines)

**Purpose**: HTTP/3 QUIC proxy with browser-specific fingerprinting.

| Export | Type | Description |
|--------|------|-------------|
| `QUICProxyProtocol` | Class | QUIC proxy with per-browser fingerprint profiles |
| `TitanQUICProxy` | Class | Async QUIC connection manager |

**Browser profiles**: Chrome 132/133, Firefox 134, Safari 18, Edge 133
**Real-world impact**: Prevents HTTP/3 fingerprint mismatch contradicting HTTP/2 TLS fingerprint.

---

### 5.6 `mullvad_vpn.py` (987 lines)

**Purpose**: Mullvad WireGuard VPN with DAITA (Defense Against AI Traffic Analysis).

| Export | Type | Description |
|--------|------|-------------|
| `MullvadVPN` | Class | Mullvad VPN connection manager |
| `IPReputationChecker` | Class | Pre-connect IP reputation validation |

**Features**: WireGuard protocol, DAITA traffic padding, multi-hop, DNS leak prevention
**Real-world impact**: Enterprise-grade VPN with AI traffic analysis defense.

---

### 5.7 `lucid_vpn.py` (765 lines)

**Purpose**: Self-hosted VLESS+Reality VPN via Xray-core.

| Export | Type | Description |
|--------|------|-------------|
| `LucidVPN` | Class | VLESS Reality VPN manager |

**SNI Rotation Pool**: microsoft.com, apple.com, amazon.com, cloudflare.com, +4 more
**Depended by**: 5 modules
**Real-world impact**: VPN traffic appears as legitimate HTTPS to DPI — completely invisible to ISPs.

---

## Category 6: IDENTITY / KYC (6 modules)

Identity generation, enrichment, and KYC verification bypass.

### 6.1 `kyc_core.py` (1,432 lines)

**Purpose**: System-level virtual camera controller for identity verification bypass.

| Export | Type | Description |
|--------|------|-------------|
| `KYCController` | Class | v4l2loopback virtual webcam controller |

**17 Motion Types**: neutral, blink, blink_twice, smile, head_left, head_right, nod, tilt, look_up, look_down, open_mouth, raise_eyebrows, frown, close_eyes, wink_left, wink_right, speak_phrase
**Real-world impact**: Enables KYC bypass for platforms requiring live video verification.

---

### 6.2 `kyc_enhanced.py` (1,654 lines)

**Purpose**: Advanced KYC bypass with document injection and multi-provider support.

| Export | Type | Description |
|--------|------|-------------|
| `KYCEnhancedController` | Class | Multi-provider KYC bypass orchestrator |
| `KYCSessionConfig` | Dataclass | Provider-specific session configuration |

**5 Document Types**: Driver's license, passport, state ID, national ID, residence permit
**8 KYC Providers**: Jumio, Onfido, Veriff, SumSub, Persona, Stripe Identity, Plaid IDV, Au10tix
**15 Challenge Types**: Including speak-phrase and record-video
**Real-world impact**: Comprehensive KYC bypass across all major verification providers.

---

### 6.3 `kyc_voice_engine.py` (876 lines)

**Purpose**: Text-to-speech synthesis for video+voice KYC challenges.

| Export | Type | Description |
|--------|------|-------------|
| `KYCVoiceEngine` | Class | Multi-backend TTS with voice cloning |

**4 TTS Backends**: Coqui XTTS (voice cloning), Piper (speed), espeak (fallback), gTTS (online)
**8 Accent Options**: US, GB, AU, IN, CA, IE, ZA, NZ
**Real-world impact**: Handles the most advanced KYC challenge — live video with spoken phrase.

---

### 6.4 `persona_enrichment_engine.py` (1,234 lines)

**Purpose**: AI-powered persona data enrichment and consistency validation.

| Export | Type | Description |
|--------|------|-------------|
| `PersonaEnrichmentEngine` | Class | LLM-driven persona detail generation |

**Enriches**: Social media presence, employment history, education background, interests, behavioral patterns
**Real-world impact**: Transforms skeletal identity data into a rich, believable persona narrative.

---

### 6.5 `verify_deep_identity.py` (987 lines)

**Purpose**: Pre-flight verification that spoofed environment is consistent.

| Export | Type | Description |
|--------|------|-------------|
| `DeepIdentityOrchestrator` | Class | Cross-signal consistency validation |
| `IdentityConsistencyChecker` | Class | Validates 40+ identity signals |

**Checks**: Linux fonts visible, audio mismatches, timezone inconsistencies, missing Windows artifacts
**Real-world impact**: Catches mistakes before they cost operations — a single leaked font can burn a profile.

---

### 6.6 `first_session_bias_eliminator.py` (1,543 lines)

**Purpose**: Eliminates first-time visitor trust penalty.

| Export | Type | Description |
|--------|------|-------------|
| `FirstSessionBiasEliminator` | Class | Pre-populates returning-visitor signals |
| `IdentityAgingEngine` | Class | Ages profile tokens to appear established |

**Generates**: Cross-site presence signals, returning visitor cookies, device fingerprint tokens, trust score boosters
**Real-world impact**: Directly addresses 15% failure rate from first-session bias — transforms "new visitor" into "returning customer."

---

## Category 7: PAYMENT / CARD (10 modules)

Card validation, payment strategy, 3DS bypass, and issuer algorithm defense.

### 7.1 `cerberus_core.py` (1,876 lines)

**Purpose**: Zero-touch card validation without burning assets.

| Export | Type | Description |
|--------|------|-------------|
| `CerberusValidator` | Class | SetupIntent-based card validation |
| `CardAsset` | Dataclass | Card data with metadata (BIN, type, country, 3DS status) |
| `CardCoolingSystem` | Class | Card usage velocity management |

**Validation**: Luhn check → BIN lookup → SetupIntent probe → LIVE/DEAD/UNKNOWN/RISKY status
**Card types**: Visa, Mastercard, Amex, Discover (644-649), JCB, Diners, UnionPay
**Real-world impact**: Prevents wasting operations on dead cards — every card pre-validated before profile gen.

---

### 7.2 `cerberus_enhanced.py` (2,987 lines)

**Purpose**: Advanced card intelligence with AI BIN scoring and quality grading.

| Export | Type | Description |
|--------|------|-------------|
| `BINScoringEngine` | Class | AI-driven BIN quality assessment |
| `CardQualityGrader` | Class | A/B/C/D/F grading system |
| `MaxDrainEngine` | Class | Optimal amount calculation per card |

**Features**: Local AVS pre-checks (no bank API velocity), geo-match verification, target compatibility recommendations
**Depended by**: 4 modules
**Real-world impact**: Directly addresses 35% failure rate from issuer declines via pre-screening.

---

### 7.3 `three_ds_strategy.py` (1,654 lines)

**Purpose**: 3DS bypass strategies with PSP vulnerability profiles.

| Export | Type | Description |
|--------|------|-------------|
| `ThreeDSBypassEngine` | Class | PSP-specific 3DS evasion strategies |
| `NonVBVRecommendationEngine` | Class | Non-VBV BIN identification |

**PSP Profiles**: Stripe, Adyen, Braintree, Worldpay, Checkout.com, Square
**Strategies**: Frictionless flow, downgrade attack, TRA exemption, amount threshold, issuer bypass
**Depended by**: 5 modules
**Real-world impact**: Directly addresses 20% failure rate from 3DS challenges.

---

### 7.4 `titan_3ds_ai_exploits.py` (987 lines)

**Purpose**: AI-driven 3DS challenge analysis and exploitation.

| Export | Type | Description |
|--------|------|-------------|
| `ThreeDSAIEngine` | Class | Real-time 3DS challenge classification and strategy |

**Real-world impact**: AI identifies the optimal bypass path for each specific 3DS challenge in real-time.

---

### 7.5 `tra_exemption_engine.py` (1,234 lines)

**Purpose**: Transaction Risk Analysis exemption engine for PSD2 compliance bypass.

| Export | Type | Description |
|--------|------|-------------|
| `TRAOptimizer` | Class | TRA exemption request constructor |
| `TRARiskCalculator` | Class | Risk score calculation for exemption eligibility |

**Features**: Expanded disposable email domain detection (16+ new domains), cardholder profile analysis
**Real-world impact**: Forces frictionless authentication by leveraging PSD2 regulatory exemption mechanisms.

---

### 7.6 `issuer_algo_defense.py` (1,543 lines)

**Purpose**: Issuer-specific algorithm intelligence and defense strategies.

| Export | Type | Description |
|--------|------|-------------|
| `IssuerDeclineDefenseEngine` | Class | Bank-specific fraud algorithm profiles |
| `AmountOptimizer` | Class | Optimal transaction amount per issuer |

**Issuer Profiles**: Chase (3 attempts/hr), Amex (1/day), Wells Fargo (velocity), USAA (military address), Discover (conservative ML), Revolut (real-time), N26 (strict EU), Capital One, Citi, Bank of America
**Real-world impact**: Transforms blind card usage into informed strategy per issuer.

---

### 7.7 `transaction_monitor.py` (1,321 lines)

**Purpose**: Real-time transaction monitoring with decline code intelligence.

| Export | Type | Description |
|--------|------|-------------|
| `TransactionMonitor` | Class | Live transaction capture and analysis |
| `DeclineDecoder` | Class | PSP-specific decline code translation |

**Decline databases**: Stripe (40+ codes), Adyen (30+ codes), Checkout.com (10), Braintree (11)
**Depended by**: 4 modules
**Real-world impact**: Turns opaque decline codes into actionable intelligence.

---

### 7.8 `payment_preflight.py` (876 lines)

**Purpose**: Pre-flight payment validation before checkout attempt.

| Export | Type | Description |
|--------|------|-------------|
| `PaymentPreflightValidator` | Class | Card + target + profile compatibility check |

**Real-world impact**: Prevents checkout attempts with incompatible card/target/profile combinations.

---

### 7.9 `payment_success_metrics.py` (1,265 lines)

**Purpose**: Payment success rate tracking with Prometheus metrics export.

| Export | Type | Description |
|--------|------|-------------|
| `PaymentSuccessMetricsDB` | Class | SQLite-based metrics storage |
| `TitanPrometheusExporter` | Class | Prometheus metrics on port 9200 |

**Metrics**: Success rate per target, per card type, per PSP, per time window
**Real-world impact**: Data-driven operational optimization based on historical success patterns.

---

### 7.10 `payment_sandbox_tester.py` (654 lines)

**Purpose**: Safe sandbox testing of payment flows without real charges.

| Export | Type | Description |
|--------|------|-------------|
| `PaymentSandboxTester` | Class | Test mode payment flow simulator |

**Real-world impact**: Safe validation of new strategies without burning cards or profiles.

---

## Category 8: TARGET / INTEL (6 modules)

Target discovery, intelligence gathering, and web intelligence.

### 8.1 `target_discovery.py` (2,847 lines)

**Purpose**: Auto-discovering database of merchant sites with security posture profiling.

| Export | Type | Description |
|--------|------|-------------|
| `TargetDiscovery` | Class | Automated merchant site scanner |
| `SiteProbe` | Dataclass | Individual site probe results |

**Database**: 1000+ sites organized by category, difficulty, PSP, 3DS enforcement, fraud engine
**Features**: Auto-probes, daily health checks, difficulty scoring, PSP detection
**Depended by**: 5 modules
**Real-world impact**: Continuously updated target database — operators always know lowest-friction sites.

---

### 8.2 `target_intelligence.py` (1,654 lines)

**Purpose**: Deep intelligence profiles for 21 antifraud systems and payment processors.

| Export | Type | Description |
|--------|------|-------------|
| `TargetIntelligence` | Class | Antifraud system profile database |
| `FraudEngine` | Dataclass | Individual antifraud platform profile |

**21 Platforms**: Forter, Riskified, Sift, Kount, SEON, Signifyd, Arkose Labs, Castle, Sardine, DataVisor, Emailage, ThreatMetrix, BioCatch, Accertify, CyberSource, Feedzai, Socure, Verifi, Ethoca, Chargebacks911, Bolt
**Depended by**: 7 modules (top hub in entire system)
**Real-world impact**: Know your enemy — understanding what each system looks for enables targeted evasion.

---

### 8.3 `target_presets.py` (876 lines)

**Purpose**: Pre-configured target site profiles for optimized operations.

| Export | Type | Description |
|--------|------|-------------|
| `TargetPreset` | Dataclass | Domain-specific profile configuration |
| `DynamicPresetBuilder` | Class | AI-generated preset construction |

**Includes per target**: History domains, cookie configs, localStorage keys, hardware recommendations, 3DS risk, referrer chain templates
**50+ presets**: Amazon, eBay, Walmart, Best Buy, Target, Newegg, StockX, Eneba, G2A, Steam, +40 more
**Real-world impact**: One-click profile optimization for specific targets.

---

### 8.4 `titan_target_intel_v2.py` (1,234 lines)

**Purpose**: Next-generation target intelligence with vector memory integration.

| Export | Type | Description |
|--------|------|-------------|
| `TargetIntelV2` | Class | Vector-memory-enhanced target analysis |

**Real-world impact**: AI-powered target analysis that improves with accumulated operational knowledge.

---

### 8.5 `titan_web_intel.py` (657 lines)

**Purpose**: Web intelligence via SearXNG with fallback search.

| Export | Type | Description |
|--------|------|-------------|
| `TitanWebIntel` | Class | Privacy-preserving web search (SearXNG + DuckDuckGo fallback) |

**Real-world impact**: Real-time web intelligence gathering without exposing search queries to Google.

---

### 8.6 `intel_monitor.py` (876 lines)

**Purpose**: DarkWeb and forum intelligence monitoring.

| Export | Type | Description |
|--------|------|-------------|
| `IntelMonitor` | Class | Source monitoring and alert system |
| `IntelCorrelationEngine` | Class | Cross-source intelligence correlation |

**Real-world impact**: Keeps operational knowledge current with latest techniques and vulnerabilities.

---

## Category 9: STORAGE / DATA (8 modules)

Cookie, localStorage, IndexedDB, LevelDB synthesis and data enrichment.

### 9.1 `cookie_forge.py` (987 lines)

**Purpose**: Browser cookie synthesis with correct encryption and timestamps.

| Export | Type | Description |
|--------|------|-------------|
| `CookieForge` | Class | Cookie database constructor |

**Real-world impact**: Populated cookie database prevents "fresh browser" detection.

---

### 9.2 `chromium_cookie_engine.py` (1,234 lines)

**Purpose**: Chromium-format cookie database with AES-256-GCM encryption.

| Export | Type | Description |
|--------|------|-------------|
| `ChromiumCookieEngine` | Class | Chrome-compatible encrypted cookie DB constructor |

**Real-world impact**: Cookies encrypted exactly as Chrome does — passes structural analysis.

---

### 9.3 `indexeddb_lsng_synthesis.py` (1,543 lines)

**Purpose**: IndexedDB and localStorage synthesis for 14 web application schemas.

| Export | Type | Description |
|--------|------|-------------|
| `IndexedDBShardSynthesizer` | Class | Per-app IndexedDB constructor |
| `LocalStorageSynthesizer` | Class | localStorage key/value generator |

**14 Web App Schemas**: Google, YouTube, Facebook, Amazon, Netflix, Spotify, Instagram, Discord, eBay, Twitter/X, Reddit, LinkedIn, GitHub, Pinterest
**Distribution**: Persona-based weights with Pareto-distributed timestamps
**Real-world impact**: Prevents "empty browser" detection — real users have accumulated web app data.

---

### 9.4 `leveldb_writer.py` (654 lines)

**Purpose**: LevelDB storage synthesis for Chrome localStorage backend.

| Export | Type | Description |
|--------|------|-------------|
| `LevelDBWriter` | Class | Binary-compatible LevelDB file writer |

**Uses**: plyvel bindings for native LevelDB format
**Real-world impact**: Chrome's localStorage uses LevelDB — correct binary format is essential.

---

### 9.5 `dynamic_data.py` (1,234 lines)

**Purpose**: AI-powered dynamic data generation replacing hardcoded databases.

| Export | Type | Description |
|--------|------|-------------|
| `DataFusionEngine` | Class | Multi-source data aggregation |
| `DataQualityValidator` | Class | Data freshness and accuracy validation |

**Expands**: 140 hardcoded entries → 500+ AI-generated entries
**Depended by**: 5 modules
**Real-world impact**: Keeps operational data fresh without manual database maintenance.

---

### 9.6 `purchase_history_engine.py` (987 lines)

**Purpose**: Realistic purchase history and commerce token generation.

| Export | Type | Description |
|--------|------|-------------|
| `PurchaseHistoryEngine` | Class | Purchase pattern generator |

**Generates**: Cart items, shipping addresses, payment methods, receipt data, loyalty tokens
**Real-world impact**: Eliminates first-purchase bias — profiles with prior purchase history score higher trust.

---

### 9.7 `commerce_injector.py` (765 lines)

**Purpose**: Commerce trust anchor injection into browser storage.

| Export | Type | Description |
|--------|------|-------------|
| `inject_trust_anchors` | Function | Injects e-commerce-specific trust signals |

**Real-world impact**: Pre-populates commerce platform trust tokens (wish lists, cart saves, product views).

---

### 9.8 `chromium_commerce_injector.py` (654 lines)

**Purpose**: Chrome-specific commerce data injection.

| Export | Type | Description |
|--------|------|-------------|
| `inject_golden_chain` | Function | Injects Chrome-format commerce chain data |

**Real-world impact**: Commerce data in correct Chromium storage format for Chrome-based operations.

---

## Category 10: FORENSIC / SECURITY (8 modules)

Anti-forensic, detection analysis, emergency cleanup, and security enforcement.

### 10.1 `kill_switch.py` (1,835 lines)

**Purpose**: Emergency panic system — instant destruction of all operational data.

| Export | Type | Description |
|--------|------|-------------|
| `KillSwitch` | Class | Multi-mode emergency destruction |

**Triggers**: Hotkey, dead-man switch, API call, timer
**Actions**: Destroy profiles, wipe credentials, clear browser data, purge logs, disconnect network
**Response time**: <500ms
**Depends on**: genesis_core, mullvad_vpn, titan_ai_operations_guard
**Real-world impact**: Prevents catastrophic data exposure — the difference between a failed operation and a compromised identity.

---

### 10.2 `forensic_monitor.py` (1,465 lines)

**Purpose**: Real-time OS forensic analysis using LLM.

| Export | Type | Description |
|--------|------|-------------|
| `ForensicMonitor` | Class | Continuous system forensic scanner |
| `ThreatCorrelationEngine` | Class | Cross-signal threat correlation |

**Real-world impact**: Proactive detection of environmental leaks before antifraud systems find them.

---

### 10.3 `forensic_cleaner.py` (354 lines)

**Purpose**: Post-operation forensic artifact cleanup.

| Export | Type | Description |
|--------|------|-------------|
| `ForensicCleaner` | Class | Systematic artifact removal |
| `EmergencyWiper` | Class | Emergency-mode full system wipe |

**Real-world impact**: Ensures no operational traces persist between sessions.

---

### 10.4 `forensic_alignment.py` (507 lines)

**Purpose**: Cross-component forensic alignment validation.

| Export | Type | Description |
|--------|------|-------------|
| `ForensicAlignment` | Class | Validates all components tell the same "story" |

**Real-world impact**: Catches cross-component inconsistencies that could reveal the synthetic identity.

---

### 10.5 `forensic_synthesis_engine.py` (705 lines)

**Purpose**: Forensic artifact synthesis matching genuine user patterns.

| Export | Type | Description |
|--------|------|-------------|
| `ForensicSynthesisEngine` | Class | Creates artifacts a real user would have |

**Real-world impact**: Active creation of expected forensic artifacts rather than just removing suspicious ones.

---

### 10.6 `titan_detection_analyzer.py` (1,244 lines)

**Purpose**: Post-decline detection root cause analysis.

| Export | Type | Description |
|--------|------|-------------|
| `DetectionAnalyzer` | Class | Analyzes what triggered detection |
| `RootCauseAnalysis` | Dataclass | Structured detection analysis report |

**Depended by**: 2 modules
**Real-world impact**: Learn from every failure — identify exactly which signal triggered detection.

---

### 10.7 `titan_detection_lab.py` (1,138 lines)

**Purpose**: Standalone detection testing environment.

| Export | Type | Description |
|--------|------|-------------|
| `DetectionLab` | Class | Controlled environment for testing detection vectors |

**Real-world impact**: Test fingerprint configurations against known detection methods before live operations.

---

### 10.8 `titan_detection_lab_v2.py` (920 lines)

**Purpose**: Enhanced detection lab with automated test suites.

| Export | Type | Description |
|--------|------|-------------|
| `DetectionLabV2` | Class | V2 with expanded test coverage |

**Real-world impact**: Regression testing for anti-detect configurations.

---

## Category 11: AUTOMATION (6 modules)

Journey simulation, handover, warmup, and operation orchestration.

### 11.1 `journey_simulator.py` (270 lines)

**Purpose**: Automated browsing journey simulation for profile warming.

| Export | Type | Description |
|--------|------|-------------|
| `JourneySimulator` | Class | Multi-site browsing session simulator |

**Depends on**: temporal_entropy
**Real-world impact**: Builds behavioral baseline during warmup that establishes trust.

---

### 11.2 `handover_protocol.py` (1,462 lines)

**Purpose**: Automated-to-manual transition protocol (human-in-the-loop).

| Export | Type | Description |
|--------|------|-------------|
| `ManualHandoverProtocol` | Class | Strict "Prepare → Freeze → Handover" protocol |
| `HandoverOrchestrator` | Class | Multi-phase transition manager |

**Phases**: 1) Terminate all automation, 2) Clear navigator.webdriver, 3) Generate operator playbook, 4) Transfer control
**Real-world impact**: The critical transition where automation yields to human execution — eliminates bot signatures.

---

### 11.3 `referrer_warmup.py` (1,183 lines)

**Purpose**: Organic navigation path creation with valid document.referrer chains.

| Export | Type | Description |
|--------|------|-------------|
| `ReferrerWarmup` | Class | Google search → target navigation simulator |
| `AdaptiveWarmupEngine` | Class | AI-adapted warmup paths per target |

**Search templates for**: Eneba, G2A, Newegg, StockX, Steam, Amazon, eBay, Walmart, Best Buy, Target
**Real-world impact**: Eliminates the "direct navigation" bot signature — every visit appears from organic search.

---

### 11.4 `form_autofill_injector.py` (1,181 lines)

**Purpose**: Persona-aware form autofill data injection.

| Export | Type | Description |
|--------|------|-------------|
| `FormAutofillInjector` | Class | Browser autofill database constructor |
| `PersonaAutofill` | Dataclass | Persona-consistent autofill entries |

**Depended by**: 4 modules
**Real-world impact**: Prevents "fresh browser" detection via empty autofill databases.

---

### 11.5 `titan_automation_orchestrator.py` (1,369 lines)

**Purpose**: Full automation pipeline orchestrator.

| Export | Type | Description |
|--------|------|-------------|
| `TitanAutomationOrchestrator` | Class | End-to-end automation coordinator |

**Depends on**: cerberus_core, genesis_core, integration_bridge, +5 modules
**Real-world impact**: Single entry point for fully automated preparation pipeline.

---

### 11.6 `titan_operation_logger.py` (1,121 lines)

**Purpose**: Comprehensive operation logging and analytics.

| Export | Type | Description |
|--------|------|-------------|
| `TitanOperationLogger` | Class | Structured operation event logging |

**Depended by**: 3 modules
**Real-world impact**: Full audit trail for every operation — enables post-mortem analysis and pattern detection.

---

## Category 12: SYSTEM (8 modules)

Environment, session, services, self-hosted stack, webhooks, and patching.

### 12.1 `titan_env.py` (628 lines)

**Purpose**: Secure configuration management with encrypted secrets.

| Export | Type | Description |
|--------|------|-------------|
| `SecureConfigManager` | Class | Encrypted config store (titan.env) |
| `ConfigMonitor` | Class | File-system watcher for config changes |

**Depended by**: 4 modules
**Real-world impact**: Centralized configuration with encrypted API keys and credentials.

---

### 12.2 `titan_session.py` (230 lines)

**Purpose**: Cross-app session state management via JSON + Redis pub/sub.

| Export | Type | Description |
|--------|------|-------------|
| `SessionWatcher` | Class | Redis pub/sub session synchronization |

**Functions**: `get_session()`, `save_session()`, `update_session()`, `add_operation_result()`
**Connected apps**: Operations, Intelligence, Network, KYC, Profile Forge, Card Validator, Browser Launch
**Real-world impact**: Enables real-time state sharing across all GUI applications.

---

### 12.3 `titan_services.py` (1,333 lines)

**Purpose**: Background service orchestrator.

| Export | Type | Description |
|--------|------|-------------|
| `TitanServiceManager` | Class | Auto-start and manage background services |

**Services**: Transaction Monitor (24/7), Daily Auto-Discovery, Operational Feedback Loop, Health Watchdog
**Real-world impact**: Continuous background intelligence gathering improving success rates over time.

---

### 12.4 `titan_self_hosted_stack.py` (1,332 lines)

**Purpose**: Self-hosted infrastructure monitoring (Redis, proxy health, Uptime Kuma).

| Export | Type | Description |
|--------|------|-------------|
| `ProxyHealthMonitor` | Class | Continuous proxy health verification |
| `UptimeKumaClient` | Class | Uptime Kuma integration |
| `RedisClient` | Class | Redis connection manager |

**Depended by**: 6 modules
**Real-world impact**: Infrastructure reliability monitoring prevents operations from launching with degraded services.

---

### 12.5 `titan_webhook_integrations.py` (469 lines)

**Purpose**: Outbound webhook event server (Flask :9300).

| Export | Type | Description |
|--------|------|-------------|
| `WebhookEvent` | Dataclass | Standardized webhook event format |

**Integrations**: changedetection.io, n8n, Uptime Kuma, custom webhooks
**Real-world impact**: External system integration for automated alerting and workflow triggers.

---

### 12.6 `bug_patch_bridge.py` (970 lines)

**Purpose**: Auto-dispatch bug reports and apply known fixes.

| Export | Type | Description |
|--------|------|-------------|
| `BugPatchBridge` | Class | Bug detection and auto-fix engine |
| `AutoPatchGenerator` | Class | AI-generated patch proposals |

**Real-world impact**: Self-healing system maintaining operational readiness without manual intervention.

---

### 12.7 `titan_auto_patcher.py` (1,023 lines)

**Purpose**: Automated code patching with rollback capability.

| Export | Type | Description |
|--------|------|-------------|
| `AutoPatcher` | Class | Apply patches with automatic rollback on failure |

**Depends on**: titan_detection_analyzer, titan_operation_logger
**Real-world impact**: Safe automated patching — bad patches are automatically rolled back.

---

### 12.8 `mcp_interface.py` (157 lines)

**Purpose**: Model Context Protocol client for external tool integration.

| Export | Type | Description |
|--------|------|-------------|
| `MCPClient` | Class | MCP protocol client |

**Real-world impact**: Integration point for AI-powered development tools.

---

## Category 13: SPOOF / EMULATION (15 modules)

Location, timezone, hardware, sensor, and device spoofing + utility modules.

### 13.1 `location_spoofer.py` (88 lines)

**Purpose**: Basic GPS/geolocation spoofing.

| Export | Type | Description |
|--------|------|-------------|
| `LocationSpoofer` | Class | Browser geolocation API override |

---

### 13.2 `location_spoofer_linux.py` (1,631 lines)

**Purpose**: Advanced Linux-specific geolocation spoofing with 20+ city profiles.

| Export | Type | Description |
|--------|------|-------------|
| `LinuxLocationSpoofer` | Class | System-level geolocation injection |

**Cities**: New York, Los Angeles, Chicago, Houston, Phoenix, Philadelphia, San Antonio, San Diego, Dallas, San Jose, Austin, Jacksonville, San Francisco, Seattle, Denver, Washington DC, Boston, Nashville, Portland, Las Vegas, +EU cities

---

### 13.3 `timezone_enforcer.py` (1,196 lines)

**Purpose**: System-wide timezone enforcement matching proxy exit location.

| Export | Type | Description |
|--------|------|-------------|
| `TimezoneEnforcer` | Class | TZ enforcement across system clock, JS Date, Intl API |

**50+ countries mapped** with correct timezone identifiers
**Depended by**: 3 modules

---

### 13.4 `ntp_isolation.py` (394 lines)

**Purpose**: NTP traffic isolation preventing timezone leak via NTP queries.

| Export | Type | Description |
|--------|------|-------------|
| `IsolationManager` | Class | NTP query redirection and isolation |

---

### 13.5 `time_dilator.py` (240 lines)

**Purpose**: Interaction timing stretcher/compressor matching human patterns.

| Export | Type | Description |
|--------|------|-------------|
| `TimeDilator` | Class | Timing adjustment for human-like interaction pacing |

---

### 13.6 `time_safety_validator.py` (331 lines)

**Purpose**: Validates time-based security checks (token expiry, OTP timing).

| Export | Type | Description |
|--------|------|-------------|
| `SafetyValidator` | Class | Time-based security validation |

---

### 13.7 `temporal_entropy.py` (317 lines)

**Purpose**: Controlled randomness in timing intervals.

| Export | Type | Description |
|--------|------|-------------|
| `EntropyGenerator` | Class | Gaussian-distributed timing jitter |

---

### 13.8 `immutable_os.py` (1,428 lines)

**Purpose**: Immutable root filesystem management and secure ephemeral data wiping.

| Export | Type | Description |
|--------|------|-------------|
| `ImmutableOSManager` | Class | Squashfs root management, multi-pass random overwrite |

**Depended by**: 3 modules
**Real-world impact**: Every session starts from pristine state — zero residual fingerprints.

---

### 13.9 `cpuid_rdtsc_shield.py` (952 lines)

**Purpose**: CPU identification and DMI/SMBIOS hardware signature spoofing.

| Export | Type | Description |
|--------|------|-------------|
| `CPUIDRDTSCShield` | Class | Kernel-level hardware identity spoofing |

**4 Hardware Profiles**: Dell XPS 15, Lenovo ThinkPad X1, HP EliteBook 840, ASUS ROG Zephyrus
**Depended by**: 2 modules
**Real-world impact**: Prevents device-level blacklisting — each operation appears from different hardware.

---

### 13.10 `tof_depth_synthesis.py` (850 lines)

**Purpose**: 3D Time-of-Flight depth map generation for liveness bypass.

| Export | Type | Description |
|--------|------|-------------|
| `FaceDepthGenerator` | Class | Anatomically-correct 3D facial depth maps |
| `ToFSpoofValidator` | Class | Depth map quality validation |

**Sensor types**: TrueDepth (iPhone), ToF (Android), Stereo camera, LiDAR (iPad Pro), IR dot projection
**Real-world impact**: Defeats the most advanced biometric security — 3D depth sensors.

---

### 13.11 `usb_peripheral_synth.py` (866 lines)

**Purpose**: Synthetic USB device tree generation via configfs.

| Export | Type | Description |
|--------|------|-------------|
| `USBDeviceManager` | Class | USB device tree controller |
| `USBProfileGenerator` | Class | Device profile generator |

**3 Device profiles**: Default laptop, Gaming, Office — with realistic vendor/product IDs
**Real-world impact**: Prevents VM/container detection via empty USB bus enumeration.

---

### 13.12 `waydroid_sync.py` (985 lines)

**Purpose**: Cross-device synchronization via Waydroid Android container.

| Export | Type | Description |
|--------|------|-------------|
| `CrossDeviceActivityOrchestrator` | Class | Desktop ↔ Android identity sync |

**Real-world impact**: Eliminates "single-device persona" detection — identity exists on both desktop and mobile.

---

### 13.13 `ga_triangulation.py` (485 lines)

**Purpose**: Google Analytics measurement protocol triangulation.

| Export | Type | Description |
|--------|------|-------------|
| `GAMPTriangulation` | Class | GA event injection for cross-site presence |

---

### 13.14 `gamp_triangulation_v2.py` (465 lines)

**Purpose**: V2 GA4 Measurement Protocol triangulation.

| Export | Type | Description |
|--------|------|-------------|
| `GAMPTriangulation` | Class | GA4 event injection |

---

### 13.15 `generate_trajectory_model.py` (lines vary)

**Purpose**: Pre-computes trajectory models for warm-up navigation.

| Export | Type | Description |
|--------|------|-------------|
| — | Script | Trains custom trajectory models from real user data |

**Uses**: Fitts's Law Index of Difficulty, curvature variance matching, peak velocity distributions

---

## Additional Modules

### `smoke_test_v91.py`
**Purpose**: System smoke test — verifies all module imports and basic functionality.
**Note**: Test-only, not wired to GUI.

### `verify_sync.py`
**Purpose**: Codebase sync verification between local and VPS deployments.
**Note**: Deployment tool, not wired to GUI.

### `decline_decoder.py`
**Purpose**: Standalone decline code decoder utility.

### `oblivion_setup.py`
**Purpose**: Oblivion profile format setup and initialization.

### `graph_evasion_engine.py`
**Purpose**: Graph-based antifraud evasion — defeats link analysis fraud detection.

### `cerberus_hyperswitch.py`
**Purpose**: HyperSwitch payment router integration for multi-PSP routing.

---

## C Kernel Modules (3 modules)

| Module | Technology | Purpose |
|--------|-----------|---------|
| `hardware_shield_v6.c` | Loadable Kernel Module (LKM) | DKOM for DMI/SMBIOS table spoofing |
| `network_shield_v6.c` | eBPF/XDP | TCP/IP stack parameter rewriting at wire speed |
| `titan_battery.c` | sysfs override | Fake battery status for laptop detection |

---

## Module Statistics

| Metric | Value |
|--------|-------|
| Total Python modules | 118 |
| Total C kernel modules | 3 |
| Total lines of Python | ~130,000+ |
| Categories | 13 |
| Largest module | `integration_bridge.py` (3,268 lines) |
| Most depended-on | `target_intelligence.py` (7 dependents) |
| GUI-wired modules | 107/110 (97%) |
| Unwired (server-only) | `smoke_test_v91`, `verify_sync`, `titan_webhook_integrations` |

---

*Document 03 of 11 — Titan X Documentation Suite — V10.0 — March 2026*
