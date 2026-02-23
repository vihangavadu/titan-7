# TITAN OS — Full Module Connection Map

**Generated: 2026-02-23 | Version: V9.1 | Status: 110/110 modules operational**

## System Health Summary

| Metric | Value |
|--------|-------|
| Core modules (parse) | 110/110 ✅ |
| Core modules (import) | 110/110 ✅ |
| titan_api endpoints | 59/59 ✅ |
| integration_bridge subsystems | 69/69 (100%) ✅ |
| Boot warnings | 0 ✅ |
| External services | 4/4 (Redis, Ollama, Xray, ntfy) ✅ |
| Config files | 3/3 (llm_config, oblivion_template, titan.env) ✅ |

---

## Module Categories & Connections

### 1. ORCHESTRATION (6 modules)
Central control plane — these modules wire everything together.

| Module | Lines | Key Classes | Depends On | Depended By |
|--------|-------|-------------|------------|-------------|
| `integration_bridge.py` | 3268 | `TitanIntegrationBridge`, `BridgeConfig`, `BridgeState` | 69 subsystem imports | Core entry point |
| `titan_api.py` | 2011 | `TitanAPI`, `APIResponse` | 59 module imports | App layer |
| `titan_master_automation.py` | 1898 | `TitanMasterAutomation` | integration_bridge, titan_env | titan_services |
| `titan_autonomous_engine.py` | 1572 | `AutonomousEngine` | ai_intelligence_engine, target_discovery, titan_realtime_copilot | titan_services |
| `titan_master_verify.py` | 1448 | `VerificationOrchestrator`, `RemediationEngine` | integration_bridge | titan_api |
| `cockpit_daemon.py` | 1206 | `CockpitDaemon`, `CommandQueue` | titan_env | titan_api |

### 2. AI / LLM (7 modules)
AI reasoning layer — routes tasks to Ollama models.

| Module | Lines | Key Classes | Depends On | Depended By |
|--------|-------|-------------|------------|-------------|
| `ai_intelligence_engine.py` | 1842 | `AIIntelligenceEngine`, `AIModelSelector` | ollama_bridge, titan_vector_memory | 5 modules |
| `ollama_bridge.py` | 1665 | `LLMLoadBalancer`, `PromptOptimizer` | — | 5 modules |
| `cognitive_core.py` | 1539 | `CognitiveCoreLocal`, `TitanCognitiveCore` | ollama_bridge, titan_vector_memory | titan_api |
| `titan_agent_chain.py` | 894 | `TitanChain`, `TitanAgent`, `TitanToolRegistry` | ollama_bridge | — |
| `titan_realtime_copilot.py` | 1312 | `RealtimeCopilot` | ai_intelligence_engine, ollama_bridge | titan_services, titan_autonomous |
| `titan_ai_operations_guard.py` | 1089 | `AIOperationsGuard` | ai_intelligence_engine | 6 modules |
| `titan_vector_memory.py` | 889 | `TitanVectorMemory` | — | 6 modules |

### 3. BROWSER / PROFILE (10 modules)
Profile generation, browser construction, and anti-detect layers.

| Module | Lines | Key Classes | Depends On | Depended By |
|--------|-------|-------------|------------|-------------|
| `genesis_core.py` | 2158 | `GenesisEngine`, `ProfileConfig` | form_autofill_injector | 3 modules |
| `oblivion_forge.py` | 1876 | `OblivionForgeEngine`, `ChromeCryptoEngine` | — | integration_bridge |
| `chromium_constructor.py` | 1654 | `ProfileConstructor` | — | integration_bridge |
| `multilogin_forge.py` | 1432 | `MultiloginForgeEngine` | — | integration_bridge |
| `antidetect_importer.py` | 987 | `OblivionImporter` | — | integration_bridge |
| `level9_antidetect.py` | 1876 | `Level9Antidetect` | multiple fingerprint modules | integration_bridge |
| `profile_realism_engine.py` | 1156 | `ProfileRealismEngine` | — | orphan |
| `advanced_profile_generator.py` | 1432 | `AdvancedProfileGenerator` | genesis_core | titan_api |
| `profile_isolation.py` | 654 | `ProfileIsolation` | — | orphan |
| `profile_burner.py` | 876 | `ProfileBurner` | — | — |

### 4. FINGERPRINT (11 modules)
Low-level browser fingerprint spoofing and consistency enforcement.

| Module | Lines | Key Classes | Depends On | Depended By |
|--------|-------|-------------|------------|-------------|
| `fingerprint_injector.py` | 1543 | `FingerprintInjector` | — | level9_antidetect |
| `canvas_noise.py` | 432 | `CanvasNoiseEngine` | — | orphan |
| `canvas_subpixel_shim.py` | 654 | `CanvasSubPixelShim` | — | integration_bridge |
| `webgl_angle.py` | 1234 | `WebGLAngleShim`, `GPUProfileValidator` | — | integration_bridge |
| `font_sanitizer.py` | 876 | `FontSanitizer` | — | integration_bridge |
| `audio_hardener.py` | 765 | `AudioHardener` | — | integration_bridge |
| `tls_mimic.py` | 543 | `TLSMimic` | — | integration_bridge |
| `tls_parrot.py` | 987 | `TLSParrotEngine`, `TLSConsistencyValidator` | — | integration_bridge |
| `ja4_permutation_engine.py` | 1654 | `JA4PermutationEngine`, `ClientHelloInterceptor` | — | integration_bridge |
| `ghost_motor_v6.py` | 1876 | `GhostMotorV7`, `GhostMotorDiffusion` | — | integration_bridge |
| `biometric_mimicry.py` | 987 | `BiometricMimicry` | — | integration_bridge |

### 5. NETWORK / PROXY (7 modules)
VPN, proxy management, and network-level stealth.

| Module | Lines | Key Classes | Depends On | Depended By |
|--------|-------|-------------|------------|-------------|
| `proxy_manager.py` | 1321 | `ResidentialProxyManager`, `ProxyHealthChecker` | — | 5 modules |
| `network_shield.py` | 876 | `NetworkShield` | — | orphan |
| `network_shield_loader.py` | 432 | `NetworkShield` | — | integration_bridge |
| `network_jitter.py` | 654 | `NetworkJitterEngine`, `JitterProfile` | — | integration_bridge |
| `quic_proxy.py` | 543 | `QUICProxyProtocol` | — | integration_bridge |
| `mullvad_vpn.py` | 987 | `MullvadVPN`, `IPReputationChecker` | — | kill_switch |
| `lucid_vpn.py` | 765 | `LucidVPN` | — | 5 modules |

### 6. IDENTITY / KYC (6 modules)
Identity generation, enrichment, and KYC bypass.

| Module | Lines | Key Classes | Depends On | Depended By |
|--------|-------|-------------|------------|-------------|
| `kyc_core.py` | 1432 | `KYCController` | — | titan_automation |
| `kyc_enhanced.py` | 1654 | `KYCEnhancedController`, `KYCSessionConfig` | — | integration_bridge |
| `kyc_voice_engine.py` | 876 | `KYCVoiceEngine` | — | integration_bridge |
| `persona_enrichment_engine.py` | 1234 | `PersonaEnrichmentEngine` | ai_intelligence_engine | titan_api |
| `verify_deep_identity.py` | 987 | `DeepIdentityOrchestrator`, `IdentityConsistencyChecker` | — | integration_bridge |
| `first_session_bias_eliminator.py` | 1543 | `FirstSessionBiasEliminator`, `IdentityAgingEngine` | — | integration_bridge, titan_api |

### 7. PAYMENT / CARD (10 modules)
Card validation, payment strategy, 3DS bypass, and issuer defense.

| Module | Lines | Key Classes | Depends On | Depended By |
|--------|-------|-------------|------------|-------------|
| `cerberus_core.py` | 1876 | `CerberusValidator`, `CardAsset`, `CardCoolingSystem` | — | titan_automation |
| `cerberus_enhanced.py` | 2987 | `BINScoringEngine`, `CardQualityGrader`, `MaxDrainEngine` | ai_intelligence_engine | 4 modules |
| `payment_preflight.py` | 876 | `PaymentPreflightValidator` | — | orphan |
| `payment_success_metrics.py` | 1265 | `PaymentSuccessMetricsDB`, `TitanPrometheusExporter` | — | orphan (V9.1 Prometheus) |
| `payment_sandbox_tester.py` | 654 | `PaymentSandboxTester` | — | orphan |
| `three_ds_strategy.py` | 1654 | `ThreeDSBypassEngine`, `NonVBVRecommendationEngine` | target_intelligence | 5 modules |
| `titan_3ds_ai_exploits.py` | 987 | `ThreeDSAIEngine` | ai_intelligence_engine | — |
| `issuer_algo_defense.py` | 1543 | `IssuerDeclineDefenseEngine`, `AmountOptimizer` | — | integration_bridge, titan_api |
| `tra_exemption_engine.py` | 1234 | `TRAOptimizer`, `TRARiskCalculator` | — | integration_bridge, titan_api |
| `transaction_monitor.py` | 1321 | `TransactionMonitor`, `DeclineDecoder` | — | 4 modules |

### 8. TARGET / INTEL (6 modules)
Target discovery, intelligence gathering, and web search.

| Module | Lines | Key Classes | Depends On | Depended By |
|--------|-------|-------------|------------|-------------|
| `target_discovery.py` | 2847 | `TargetDiscovery`, `SiteProbe` | titan_self_hosted_stack | 5 modules |
| `target_intelligence.py` | 1654 | `TargetIntelligence`, `FraudEngine` | — | 7 modules (top hub) |
| `target_presets.py` | 876 | `TargetPreset`, `DynamicPresetBuilder` | target_intelligence | integration_bridge |
| `titan_target_intel_v2.py` | 1234 | `TargetIntelV2` | target_intelligence, titan_vector_memory | — |
| `titan_web_intel.py` | 657 | `TitanWebIntel` (SearXNG + fallback) | — | — |
| `intel_monitor.py` | 876 | `IntelMonitor`, `IntelCorrelationEngine` | — | integration_bridge |

### 9. STORAGE / DATA (8 modules)
Cookie, localStorage, IndexedDB, LevelDB synthesis and data enrichment.

| Module | Lines | Key Classes | Depends On | Depended By |
|--------|-------|-------------|------------|-------------|
| `cookie_forge.py` | 987 | `CookieForge` | — | orphan |
| `chromium_cookie_engine.py` | 1234 | `ChromiumCookieEngine` | — | orphan |
| `indexeddb_lsng_synthesis.py` | 1543 | `IndexedDBShardSynthesizer`, `LocalStorageSynthesizer` | — | integration_bridge, titan_api |
| `leveldb_writer.py` | 654 | `LevelDBWriter` | — | integration_bridge |
| `dynamic_data.py` | 1234 | `DataFusionEngine`, `DataQualityValidator` | — | 5 modules |
| `purchase_history_engine.py` | 987 | `PurchaseHistoryEngine` | — | integration_bridge |
| `commerce_injector.py` | 765 | `inject_trust_anchors` | — | integration_bridge |
| `chromium_commerce_injector.py` | 654 | `inject_golden_chain` | — | integration_bridge |

### 10. FORENSIC / SECURITY (8 modules)
Anti-forensic, detection analysis, and emergency cleanup.

| Module | Lines | Key Classes | Depends On | Depended By |
|--------|-------|-------------|------------|-------------|
| `forensic_monitor.py` | 1465 | `ForensicMonitor`, `ThreatCorrelationEngine` | ollama_bridge | 2 modules |
| `forensic_cleaner.py` | 354 | `ForensicCleaner`, `EmergencyWiper` | — | orphan |
| `forensic_alignment.py` | 507 | `ForensicAlignment` | — | integration_bridge |
| `forensic_synthesis_engine.py` | 705 | `ForensicSynthesisEngine` | — | orphan |
| `kill_switch.py` | 1835 | `KillSwitch` | genesis_core, mullvad_vpn, titan_ai_operations_guard | 3 modules |
| `titan_detection_analyzer.py` | 1244 | `DetectionAnalyzer`, `RootCauseAnalysis` | — | 2 modules |
| `titan_detection_lab.py` | 1138 | `DetectionLab` | standalone test tool | — |
| `titan_detection_lab_v2.py` | 920 | `DetectionLabV2` | standalone test tool | — |

### 11. AUTOMATION (6 modules)
Journey simulation, handover, warmup, and operation orchestration.

| Module | Lines | Key Classes | Depends On | Depended By |
|--------|-------|-------------|------------|-------------|
| `journey_simulator.py` | 270 | `JourneySimulator` | temporal_entropy | — |
| `handover_protocol.py` | 1462 | `ManualHandoverProtocol`, `HandoverOrchestrator` | target_intelligence | 2 modules |
| `referrer_warmup.py` | 1183 | `ReferrerWarmup`, `AdaptiveWarmupEngine` | — | 2 modules |
| `form_autofill_injector.py` | 1181 | `FormAutofillInjector`, `PersonaAutofill` | — | 4 modules |
| `titan_automation_orchestrator.py` | 1369 | `TitanAutomationOrchestrator` | cerberus_core, genesis_core, integration_bridge, +5 | 2 modules |
| `titan_operation_logger.py` | 1121 | `TitanOperationLogger` | — | 3 modules |

### 12. SYSTEM (8 modules)
Environment, session, services, self-hosted stack, webhooks.

| Module | Lines | Key Classes | Depends On | Depended By |
|--------|-------|-------------|------------|-------------|
| `titan_env.py` | 628 | `SecureConfigManager`, `ConfigMonitor` | — | 4 modules |
| `titan_session.py` | 230 | `SessionWatcher` | titan_self_hosted_stack (Redis) | — |
| `titan_services.py` | 1333 | `TitanServiceManager` | target_discovery, titan_autonomous, +3 | 2 modules |
| `titan_self_hosted_stack.py` | 1332 | `ProxyHealthMonitor`, `UptimeKumaClient`, `RedisClient` | — | 6 modules |
| `titan_webhook_integrations.py` | 469 | `WebhookEvent` (Flask server :9300) | ai_intelligence_engine | V9.1 new |
| `bug_patch_bridge.py` | 970 | `BugPatchBridge`, `AutoPatchGenerator` | — | 2 modules |
| `titan_auto_patcher.py` | 1023 | `AutoPatcher` | titan_detection_analyzer, titan_operation_logger | 2 modules |
| `mcp_interface.py` | 157 | `MCPClient` | — | 1 module |

### 13. SPOOF / EMULATION (15 modules)
Location, timezone, hardware, sensor, and device spoofing.

| Module | Lines | Key Classes | Depends On | Depended By |
|--------|-------|-------------|------------|-------------|
| `location_spoofer.py` | 88 | `LocationSpoofer` | — | orphan (lightweight) |
| `location_spoofer_linux.py` | 1631 | `LinuxLocationSpoofer` | — | 2 modules |
| `timezone_enforcer.py` | 1196 | `TimezoneEnforcer` | — | 3 modules |
| `ntp_isolation.py` | 394 | `IsolationManager` | — | 1 module |
| `time_dilator.py` | 240 | `TimeDilator` | — | orphan |
| `time_safety_validator.py` | 331 | `SafetyValidator` | — | 1 module |
| `temporal_entropy.py` | 317 | `EntropyGenerator` | — | 2 modules |
| `immutable_os.py` | 1428 | `ImmutableOSManager` | — | 3 modules |
| `cpuid_rdtsc_shield.py` | 952 | `CPUIDRDTSCShield` | — | 2 modules |
| `tof_depth_synthesis.py` | 850 | `FaceDepthGenerator`, `ToFSpoofValidator` | — | 2 modules |
| `usb_peripheral_synth.py` | 866 | `USBDeviceManager`, `USBProfileGenerator` | — | 2 modules |
| `waydroid_sync.py` | 985 | `CrossDeviceActivityOrchestrator` | — | 2 modules |
| `windows_font_provisioner.py` | 770 | `WindowsFontProvisioner` | — | 2 modules |
| `ga_triangulation.py` | 485 | `GAMPTriangulation` | — | orphan |
| `gamp_triangulation_v2.py` | 465 | `GAMPTriangulation` | — | 1 module |

---

## Top 15 Hub Modules (most depended on)

| Rank | Dependencies | Module | Primary Classes |
|------|-------------|--------|----------------|
| 1 | 7 | `target_intelligence` | AntifraudSystemProfile, ProcessorProfile |
| 2 | 6 | `titan_vector_memory` | TitanVectorMemory, SearchResult |
| 3 | 6 | `titan_ai_operations_guard` | AIOperationsGuard, GuardVerdict |
| 4 | 6 | `titan_self_hosted_stack` | ProxyHealthMonitor, RedisClient |
| 5 | 5 | `ollama_bridge` | LLMLoadBalancer, PromptOptimizer |
| 6 | 5 | `three_ds_strategy` | ThreeDSBypassEngine |
| 7 | 5 | `ai_intelligence_engine` | AIIntelligenceEngine |
| 8 | 5 | `dynamic_data` | DataFusionEngine |
| 9 | 5 | `lucid_vpn` | LucidVPN |
| 10 | 5 | `proxy_manager` | ResidentialProxyManager |
| 11 | 5 | `target_discovery` | TargetDiscovery |
| 12 | 4 | `form_autofill_injector` | FormAutofillInjector |
| 13 | 4 | `cerberus_enhanced` | BINScoringEngine |
| 14 | 4 | `transaction_monitor` | TransactionMonitor |
| 15 | 4 | `titan_env` | SecureConfigManager |

---

## Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     9 GUI APPS (PyQt6)                       │
│  Operations │ Intelligence │ Network │ KYC │ Admin │ ...    │
└──────────────────────┬──────────────────────────────────────┘
                       │
              ┌────────▼────────┐
              │   titan_api.py  │ ← 59 module endpoints
              │  (API Gateway)  │
              └────────┬────────┘
                       │
         ┌─────────────▼──────────────┐
         │  integration_bridge.py     │ ← 69 subsystem imports
         │  (Unified Orchestrator)    │
         └─────────────┬──────────────┘
                       │
    ┌──────────────────┼──────────────────┐
    │                  │                  │
┌───▼───┐      ┌──────▼──────┐    ┌──────▼──────┐
│  AI   │      │  BROWSER    │    │  PAYMENT    │
│ Layer │      │  PROFILE    │    │  CARD       │
│       │      │  FINGERPRINT│    │  3DS/TRA    │
│ollama │      │genesis_core │    │cerberus     │
│cognit.│      │oblivion     │    │issuer_def   │
│vector │      │ghost_motor  │    │three_ds     │
└───┬───┘      └──────┬──────┘    └──────┬──────┘
    │                 │                   │
    │          ┌──────▼──────┐    ┌──────▼──────┐
    │          │   NETWORK   │    │   TARGET    │
    │          │proxy_manager│    │target_disc. │
    │          │mullvad_vpn  │    │target_intel │
    │          │network_jitt.│    │web_intel    │
    │          └──────┬──────┘    └──────┬──────┘
    │                 │                   │
    └────────┬────────┴───────────────────┘
             │
    ┌────────▼────────┐
    │     SYSTEM      │
    │  titan_session   │ ← Redis pub/sub
    │  titan_env       │ ← Environment
    │  self_hosted_stk │ ← Docker services
    │  webhook_integ   │ ← Flask :9300
    │  prometheus      │ ← Metrics :9200
    └─────────────────┘
```

---

## Fixes Applied (V9.1 Audit)

| Issue | Files | Fix |
|-------|-------|-----|
| 28 wrong class names in titan_api.py | `titan_api.py` | Corrected all import names to match actual module exports |
| QThread crash on headless VPS | `forensic_widget.py` | Added PyQt6 availability guard with stub classes |
| Double-escaped JSON quotes | `oblivion_template.json` | Fixed 6 value strings from `\\"` to `\"` |
| Duplicate timezone import | `forensic_synthesis_engine.py` | Removed duplicate `timezone` in import |
| 78 BOM/CRLF encoding issues | All synced files | Stripped UTF-8 BOM and converted CRLF→LF on VPS |
| Missing pip packages | VPS | Installed langchain, duckduckgo-search, sentence-transformers, redis, prometheus-client, python-Wappalyzer |
| ntfy service stopped | VPS | Started ntfy.service |
| 5 V9.1 modules not synced | 8 core files | Synced payment_success_metrics, titan_web_intel, target_discovery, titan_session, preflight_validator, titan_webhook_integrations, __init__ |
| 8 V8.3 patches not synced | 8 core + 10 apps | Synced ai_intelligence_engine, forensic_cleaner, integration_bridge, mullvad_vpn, profile_realism_engine, titan_api, windows_font_provisioner + 10 app files |

---

## GUI App Architecture (10 apps, 38 tabs, 362 imports)

### 3×3 Launcher Grid + Launcher

| App | Accent | Tabs | Core Modules | Workers |
|-----|--------|------|-------------|---------|
| **Launcher** | `#00d4ff` | 3×3 Grid | 5 (kill_switch, mullvad, ollama, services) | — |
| **Operations** | `#00d4ff` | TARGET, IDENTITY, VALIDATE, FORGE & LAUNCH, RESULTS | **51** | ValidateWorker, ForgeWorker |
| **Intelligence** | `#a855f7` | AI COPILOT, 3DS STRATEGY, DETECTION, RECON, MEMORY | 21 | AIQueryWorker, ReconWorker |
| **Network** | `#22c55e` | MULLVAD VPN, NETWORK SHIELD, FORENSIC, PROXY/DNS | 22 | VPNConnectWorker, ShieldAttachWorker |
| **KYC Studio** | `#f59e0b` | CAMERA, DOCUMENTS, VOICE | 13 | StreamWorker |
| **Admin** | `#f59e0b` | SERVICES, TOOLS, SYSTEM, AUTOMATION, CONFIG | 24 | HealthCheckWorker |
| **Settings** | `#a855f7` | VPN, AI, SERVICES, BROWSER, API KEYS, SYSTEM | 2 | StatusWorker |
| **Profile Forge** | `#00d4ff` | IDENTITY, FORGE, PROFILES | 14 | ForgeWorker |
| **Card Validator** | `#eab308` | VALIDATE, INTELLIGENCE, HISTORY | 8 | ValidateWorker |
| **Browser Launch** | `#22c55e` | LAUNCH, MONITOR, HANDOVER | 11 | PreflightWorker |

### Cross-App Session (titan_session.py)
- **Connected**: Operations, Intelligence, Network, KYC Studio, Profile Forge, Card Validator, Browser Launch
- **Backend**: JSON file + Redis pub/sub (V9.1)
- **Functions**: `get_session()`, `save_session()`, `update_session()`, `add_operation_result()`

### GUI → Core Connectivity
- **362 total imports**, **0 broken**
- **107/110** unique core modules wired to GUI (**97% coverage**)
- 3 unwired: `smoke_test_v91`, `verify_sync`, `titan_webhook_integrations` (server-side only)

### GUI Fixes Applied (V9.1)

| # | App | Broken Import | Fixed To |
|---|-----|--------------|----------|
| 1 | titan_launcher.py | `OllamaBridge` | `LLMLoadBalancer as OllamaBridge` |
| 2 | titan_operations.py | `LocationSpooferLinux` | `LinuxLocationSpoofer` |
| 3 | titan_operations.py | `USBPeripheralSynth` | `USBDeviceManager` |
| 4 | titan_operations.py | `GhostMotorEngine` | `GhostMotorV7` |
| 5 | titan_operations.py | `HandoverProtocol` | `ManualHandoverProtocol` |
| 6 | titan_operations.py | `AntiDetectImporter` | `OblivionImporter` |
| 7 | titan_intelligence.py | `OllamaBridge` | `LLMLoadBalancer as OllamaBridge` |
| 8 | titan_intelligence.py | `TRAExemptionEngine` | `TRAOptimizer as TRAExemptionEngine` |
| 9 | titan_intelligence.py | `get_optimal_exemption` | `TRARiskCalculator, get_tra_calculator` |
| 10 | titan_intelligence.py | `calculate_tra_score` | (removed, replaced above) |
| 11 | titan_intelligence.py | `generate_ja4_fingerprint` | `ClientHelloInterceptor` |
| 12 | titan_network.py | `QUICProxy` | `TitanQUICProxy as QUICProxy` |
| 13 | titan_network.py | `ForensicConfig` | `ForensicDashboard` |
| 14 | titan_network.py | `LocationSpooferLinux` | `LinuxLocationSpoofer` |
| 15 | app_kyc.py | `DeepIdentityVerifier` | `DeepIdentityOrchestrator` |
| 16 | app_kyc.py | `IdentityConfig` | `IdentityConsistencyChecker` |
| 17 | app_kyc.py | `ToFDepthSynthesizer` | `FaceDepthGenerator` |
| 18 | app_kyc.py | `generate_depth_map` | `get_depth_generator` |
| 19 | app_kyc.py | `synthesize_ir_pattern` | `generate_depth_sequence` |
| 20 | titan_admin.py | `OllamaBridge` | `LLMLoadBalancer as OllamaBridge` |
| 21 | forensic_widget.py | `core.titan_enterprise_theme` | `titan_theme.apply_titan_theme` |

---

## External Services (VPS 72.62.72.48)

| Service | Status | Port | Purpose |
|---------|--------|------|---------|
| Redis | ✅ active | 6379 | Session pub/sub, caching |
| Ollama | ✅ active | 11434 | LLM inference (3 models) |
| Xray | ✅ active | — | VLESS/Trojan proxy |
| ntfy | ✅ active | 80 | Push notifications |
| Prometheus exporter | available | 9200 | Payment metrics |
| Webhook server | available | 9300 | Changedetection.io, n8n, Uptime Kuma |
