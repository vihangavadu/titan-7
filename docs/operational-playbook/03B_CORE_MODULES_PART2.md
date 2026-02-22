# 03B — Core Modules Reference (Part 2)

Continuation from [Part 1](03_CORE_MODULES.md). Covers: AI, Target/Recon, KYC, Automation, Security, System.

---

## Category 5: AI & Intelligence (11 modules)

### ai_intelligence_engine.py — Central AI Analysis
**Purpose:** LLM reasoning for BIN analysis, target recon, strategy recommendations.

**Functions:** BIN analysis with vector memory context, target reconnaissance with web search, 3DS strategy, preflight assessment, behavioral tuning, profile auditing.

**Key API:** `analyze_bin(bin)`, `recon_target(url)`, `advise_3ds(card, merchant)`, `advise_preflight(op)`, `tune_behavior(target)`, `audit_profile(profile)`, `plan_operation(query)` → `AIOperationPlan`, `is_ai_available()`, `get_ai_status()`

---

### cognitive_core.py — Central AI Coordination Hub
**Purpose:** Manages context, memory, and multi-model orchestration across AI components.

**Functions:** Coordinates between Ollama models (mistral/qwen/deepseek), manages conversation context, routes queries to best model, behavioral profile modeling.

**Key API:** `TitanCognitiveCore.process(input)`, `CognitiveEngine`, `BehaviorProfile`

---

### ollama_bridge.py — Local LLM Interface
**Purpose:** Local inference via Ollama — no data sent to external APIs.

**Functions:** Interface to Ollama REST API (localhost:11434). Supports mistral:7b, qwen2.5:7b, deepseek-r1:8b. Streaming responses.

**Key API:** `OllamaBridge.query(prompt, context, model)` → response

---

### titan_agent_chain.py — LangChain ReAct Agent
**Purpose:** Complex multi-step reasoning with tool access (vector memory, web search, BIN analysis).

**Functions:** ReAct pattern: Reason → Act → Observe → Repeat. Self-correcting on failed tool calls.

**Key API:** `TitanAgent.run(query)` → response with reasoning chain, `TitanToolRegistry`

---

### titan_vector_memory.py — ChromaDB Knowledge Base
**Purpose:** Semantic search over past operations, decline patterns, target intelligence.

**Functions:** Stores operation outcomes, BIN intel, target analysis as vector embeddings. Semantic similarity: "similar operations that succeeded on Shopify."

**Key API:** `TitanVectorMemory.store(data, metadata)`, `.search(query, n)` → top-N results

---

### titan_web_intel.py — Multi-Provider Web Search
**Purpose:** Real-time web intelligence about targets, BINs, merchants.

**Functions:** DuckDuckGo/Google/Bing search, structured extraction, PSP identification, BIN research.

**Key API:** `TitanWebIntel.research(query)` → structured report

---

### titan_ai_operations_guard.py — 4-Phase AI Advisor
**Purpose:** Real-time AI guidance during all operation phases. Never blocks — only advises.

**4 Phases:**
1. **Pre-Op:** Geo-mismatch detection, BIN velocity check, golden path scoring
2. **Active Session:** Session duration, page count, proxy latency monitoring
3. **Checkout:** PSP-specific 3DS prediction, amount threshold advice
4. **Post-Op:** Decline analysis, vector memory storage, next target recommendation

**Key API:** `TitanAIOperationsGuard.advise(phase, context)` → advisory

---

### titan_3ds_ai_exploits.py — AI Checkout Co-Pilot
**Purpose:** During checkout, antifraud decisions happen in milliseconds. AI intervenes where humans can't react fast enough.

**Functions:** Auto-detects checkout pages, blocks hidden 3DS fingerprint iframes in <10ms, scans 30-80 API responses for decline signals, identifies PSP from page source, non-blocking alerts.

**Key API:** `ThreeDSAIEngine.monitor(page)` — delivered as browser extension

---

### titan_realtime_copilot.py — Real-Time Operation Guidance
**Purpose:** Guides operator on timing, next steps, and alternative approaches during operations.

**Key API:** `TitanRealtimeCopilot.advise(operation_state)` → guidance

---

### titan_detection_analyzer.py — Detection Pattern Analysis
**Purpose:** Post-operation analysis reveals which defenses worked and which failed.

**Functions:** Identifies triggering antifraud vector, correlation analysis across operations, defense improvement recommendations.

**Key API:** `TitanDetectionAnalyzer.analyze(operation_log)` → detection report

---

### generate_trajectory_model.py — Behavioral Trajectory Training
**Purpose:** Trains models on successful operation trajectories to improve Ghost Motor patterns.

**Key API:** `TrajectoryModelGenerator.train(data)` → trained model

---

## Category 6: Target & Reconnaissance (6 modules)

### target_discovery.py — Automated Target Discovery
**Purpose:** Systematic discovery of suitable merchant websites.

**Functions:** Google dorking by PSP/MCC/geography, site probing for PSP identification, checkout flow analysis, success probability scoring.

**Key API:** `TargetDiscovery.discover(criteria)` → scored target list, `AutoDiscovery`, `auto_discover()`

---

### target_intelligence.py — Target Site Analysis
**Purpose:** Each merchant has different antifraud, checkout flows, and 3DS requirements.

**Functions:** PSP identification, antifraud mapping (Forter/Riskified/Sift/DataDome), AVS intelligence, proxy recommendations, checkout flow mapping.

**Key API:** `get_target_intel(url)`, `get_avs_intelligence(target)`, `get_proxy_intelligence(target)`

---

### titan_target_intel_v2.py — 8-Vector Golden Path Scoring
**Purpose:** Rigorous target scoring with 8 weighted vectors (100 points total).

**Vectors:**
1. PSP 3DS config (25 pts)
2. MCC intelligence (10 pts) — restaurants/rideshare = lowest 3DS
3. Acquirer level (5 pts)
4. Geographic enforcement (15 pts)
5. Transaction exemptions (10 pts)
6. Amount thresholds (15 pts) — below €30 often exempt
7. Antifraud gaps (10 pts)
8. Checkout flow (10 pts)

**Key API:** `TargetIntelV2.get_full_intel(target)` → comprehensive score

---

### target_presets.py — Pre-Configured Target Profiles
**Purpose:** Known-good target configurations for quick loading.

**Key API:** `TARGET_PRESETS`, `get_target_preset(name)`, `list_targets()`

---

### intel_monitor.py — Continuous Intelligence Monitoring
**Purpose:** Detects PSP changes, new antifraud deployments at known targets.

**Key API:** `IntelMonitor.start()` — begins periodic re-scanning

---

### referrer_warmup.py — Referrer Chain Engine
**Purpose:** Direct navigation to checkout is suspicious. Builds natural referrer trails.

**Functions:** Google search → organic result → target. Social media → target. Email link → target. Unique per session.

**Key API:** `ReferrerWarmupEngine.warmup(target_url)`

---

## Category 7: KYC & Identity Verification (7 modules)

### kyc_core.py — Virtual Camera Controller
**Purpose:** KYC requires live camera. Virtual camera streams animated face to any app.

**Functions:** LivePortrait face reenactment from single image, `/dev/video` output via v4l2loopback, motions: blink/smile/head-turn/nod/eyebrow-raise, works with any app (browser, Zoom, Telegram).

**Key API:** `KYCController.setup_virtual_camera()`, `.start_reenactment(config)`, `.stop_stream()`, `.get_available_motions()`

Config classes: `ReenactmentConfig` (motion, rotation, intensity, blink rate), `VirtualCameraConfig` (device, resolution, FPS), `IntegrityShield`

---

### kyc_enhanced.py — Provider-Specific KYC Intelligence
**Purpose:** Each KYC provider has different challenges, timing, and detection.

**Supported providers:** Onfido, Jumio, Veriff, Sumsub, Persona, Stripe Identity, Plaid IDV, Au10tix

**Functions:** Liveness challenge prediction, document type requirements, timing templates, session configuration per provider.

**Key API:** `create_kyc_session(provider, config)`, `KYC_PROVIDER_PROFILES`, `LivenessChallenge`

---

### kyc_voice_engine.py — Voice Verification
**Purpose:** Some providers require spoken phrases.

**Functions:** TTS with natural voice, gender-specific profiles, lip-sync video generation, accent/cadence matching.

**Key API:** `KYCVoiceEngine.synthesize(text, voice_profile)`, `VoiceProfile`, `SpeechVideoConfig`

---

### verify_deep_identity.py — Deep Identity Verification
**Purpose:** Advanced KYC beyond face matching — document authenticity, database cross-referencing.

**Key API:** `DeepIdentityVerifier.verify(config)`, `IdentityConfig`

---

### tof_depth_synthesis.py — Time-of-Flight Depth Maps
**Purpose:** 3D liveness detection uses depth cameras. Flat images fail.

**Functions:** Generates ToF depth maps from 2D face images, IR dot patterns matching real sensors, supports structured light/ToF/stereo sensor types, anatomically correct facial landmarks.

**Key API:** `generate_depth_map(face_image, sensor)`, `synthesize_ir_pattern()`, `ToFDepthSynthesizer`, `DepthQuality`, `SensorType`, `FacialLandmarks`

---

### usb_peripheral_synth.py — USB Device Emulation
**Purpose:** Real desktops have USB keyboard/mouse/webcam. VPS has none.

**Functions:** Creates synthetic USB device descriptors matching consumer peripherals in `lsusb` output.

**Key API:** `USBPeripheralSynth.create_devices()`

---

### waydroid_sync.py — Android Emulation Sync
**Purpose:** Some KYC flows require mobile device. Waydroid runs Android on Linux.

**Functions:** Syncs KYC session between desktop and emulated mobile, mobile persona management.

**Key API:** `WaydroidSyncEngine.sync(config)`, `SyncConfig`, `MobilePersona`

---

## Category 8: Automation & Orchestration (7 modules)

### titan_automation_orchestrator.py — 12-Phase E2E Orchestrator
**Purpose:** Automates the complete operation lifecycle from initialization to cleanup.

**12 Phases:**
1. **INIT** — Initialize bridge, Cerberus, Genesis
2. **CARD_VALIDATION** — Validate card via Cerberus or Luhn fallback
3. **PROFILE_GENERATION** — Generate browser profile via Genesis
4. **NETWORK_SETUP** — Connect VPN/proxy, generate JA4 fingerprint
5. **PREFLIGHT** — Run ZeroDetect + PreFlight validation
6. **BROWSER_LAUNCH** — Configure browser with profile + fingerprints
7. **NAVIGATION** — Referrer warmup + target navigation
8. **CHECKOUT** — TRA exemption + issuer risk + form filling
9. **THREE_DS** — 3DS bypass execution
10. **KYC** — KYC handling if required
11. **COMPLETION** — Transaction finalization
12. **CLEANUP** — VPN disconnect, card cooling, artifact removal

**Key API:** `TitanOrchestrator.run_operation(config)` → `OperationResult`

Config: `OperationConfig` (card details, billing, persona, target URL, options)
Output: `OperationResult` (phase results, status, duration, risk level)

---

### titan_master_automation.py — Master Automation Controller
**Purpose:** High-level controller for running single, batch, and test operations.

**Functions:** Test operations with sample data, single operations from config, batch operations with delays.

**Key API:** `TitanMasterAutomation.run_test_operation()`, `.run_single(config)`, `.run_batch(configs)`

---

### titan_autonomous_engine.py — 24/7 Self-Improving Loop
**Purpose:** Continuous automated operation cycle with self-improvement.

**Functions:** Automated target selection, operation execution, result analysis, parameter tuning, sleep/wake cycles matching human patterns.

**Key API:** `TitanAutonomousEngine.start()`, `.stop()`, `.get_status()`

---

### titan_auto_patcher.py — Automated Parameter Tuning
**Purpose:** Auto-adjusts parameters based on operation outcomes.

**Functions:** Analyzes decline patterns, tunes timing/amount/proxy parameters, A/B testing configurations.

**Key API:** `TitanAutoPatcher.patch(analysis)` → tuned parameters

---

### titan_operation_logger.py — Operation Analytics & Logging
**Purpose:** Comprehensive logging for feedback loop and performance analysis.

**Functions:** SQLite database of operation steps, phase results, metrics, detection signals. Log retention and compression.

**Key API:** `OperationLog.record(step)`, `.get_history()`, `.get_analytics()`

---

### handover_protocol.py — Session Handover
**Purpose:** Clean transition from automated warmup to human operator control.

**Functions:** Verifies browser state is clean, pauses automated systems, transfers control to human.

**Key API:** `HandoverProtocol.handover(session)` → ready state

---

### preflight_validator.py — Pre-Launch Environment Validation
**Purpose:** Verifies all systems are correctly configured before launching an operation.

**Functions:** Checks IP reputation, TLS fingerprint, canvas consistency, WebRTC leaks, timezone match, proxy health.

**Key API:** `PreFlightValidator.validate()` → pass/fail with details

---

## Category 9: Security & Forensics (3 modules)

### kill_switch.py — Emergency Wipe Protocol
**Purpose:** Panic button for emergency data destruction.

**Functions:** Shreds all profiles/logs/state, overwrites free disk space, clears RAM (tmpfs), notifies AI Guard.

**Key API:** `arm_kill_switch()`, `send_panic_signal()`, `KillSwitch`, `KillSwitchConfig`

---

### forensic_cleaner.py — Artifact Removal
**Purpose:** Removes all Titan-specific artifacts from filesystem.

**Functions:** Profile directory cleanup, browser cache sanitization, secure deletion of temp files.

**Key API:** `ForensicCleaner.clean()` / `EmergencyWiper`

---

### forensic_monitor.py — Real-Time Forensic Monitoring
**Purpose:** Detects forensic artifacts that could reveal Titan OS presence.

**Functions:** Monitors filesystem, process list, network connections for detectable traces. Real-time alerts.

**Key API:** `ForensicMonitor.start(config)`, `ForensicConfig`

---

## Category 10: System & Services (8 modules)

### titan_api.py — Flask REST API (47 endpoints)
**Purpose:** Remote control and monitoring via HTTP API.

**Functions:** 47 endpoints covering all module operations, status monitoring, configuration management. Used by GUI apps and external tools.

**Key API:** Flask app with `/api/v1/` prefix

---

### titan_services.py — Service Management Daemon
**Purpose:** Manages background services (API server, monitors, schedulers).

**Functions:** Start/stop individual or all services, health monitoring, memory pressure management.

**Key API:** `start_all_services()`, `stop_all_services()`, `get_services_status()`, `MemoryPressureManager`

---

### titan_env.py — Configuration Loader
**Purpose:** Loads and validates `titan.env` configuration.

**Functions:** Parses titan.env, validates required vs optional settings, provides typed access to config values.

**Key API:** `TitanEnvManager.load()`, `ConfigValidator.validate()`

---

### cockpit_daemon.py — System Health Monitoring
**Purpose:** Continuous system health checks (CPU, RAM, disk, services).

**Key API:** `CockpitDaemon.start()`, `.get_health()`

---

### titan_master_verify.py — System Integrity Verification
**Purpose:** Verifies all modules are present, importable, and correctly configured.

**Key API:** `MasterVerifier.verify()` → integrity report

---

### titan_self_hosted_stack.py — Self-Hosted Tool Integrations
**Purpose:** Integrates GeoIP, IP Quality Score, and fingerprint testing tools.

**Key API:** `GeoIPValidator`, `IPQualityChecker`, `FingerprintTester`

---

### bug_patch_bridge.py — Bug Reporting & Patching
**Purpose:** Structured bug reporting with automated patch suggestions.

**Key API:** `BugPatchBridge.report(bug)`, `.suggest_patch(bug)`

---

### windows_font_provisioner.py — Windows Font Installation
**Purpose:** Installs Windows TrueType fonts on Linux for correct rendering metrics.

**Key API:** `WindowsFontProvisioner.install()`

---

## C Source Files (3)

### network_shield_v6.c — eBPF Network Shield
Kernel-level eBPF program for TCP/IP header rewriting. Compiled and loaded by `network_shield_loader.py`.

### hardware_shield_v6.c — Hardware Identity Spoof
Kernel module that spoofs DMI/SMBIOS strings (vendor, product, BIOS). Loaded at boot.

### titan_battery.c — Battery Emulation
Emulates laptop battery status via sysfs. Real desktops have batteries; VPS doesn't. Reports 78% charge, discharging.

---

## Shell Scripts (3)

### initramfs_dmi_hook.sh — Boot-Time DMI Spoof
Early-boot hook that loads hardware shield before userspace starts.

### build.sh — Titan Build Script
Builds the complete Titan OS from source, compiles C modules, installs Python dependencies.

---

## Browser Extensions (2)

### extensions/ghost_motor/ — Ghost Motor Extension
Injects human-like behavioral patterns into every webpage. `ghost_motor.js` + `manifest.json`.

### extensions/tx_monitor/ — Transaction Monitor Extension
Captures payment events during checkout. `background.js` + `tx_monitor.js` + `manifest.json`. Sends events to `transaction_monitor.py` backend.

---

*Next: [04 — App: Operations Center](04_APP_OPERATIONS_CENTER.md)*
