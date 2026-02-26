# 12 — Codebase Gap Analysis & Fixes

## Cross-Reference: Playbook Docs vs Actual Code

This document records all gaps found by cross-referencing the operational playbook documentation against the actual codebase, and the fixes applied.

---

## GAP 1: UTF-16 Encoded Files (CRITICAL)

**Impact:** 6 Python files were saved in UTF-16 encoding. Python's default import mechanism expects UTF-8. These files would fail to import on the Linux VPS with `SyntaxError` or `UnicodeDecodeError`.

| File | Size (UTF-16) | Size (UTF-8) |
|------|--------------|--------------|
| `canvas_noise.py` | 4,896 B | 2,447 chars |
| `forensic_cleaner.py` | 34,826 B | 17,412 chars |
| `forensic_synthesis_engine.py` | 65,224 B | 32,611 chars |
| `location_spoofer.py` | 6,716 B | 3,357 chars |
| `network_shield.py` | 90,110 B | 45,054 chars |
| `profile_realism_engine.py` | 84,318 B | 42,158 chars |

**Fix:** All 6 files converted from UTF-16 to UTF-8.

---

## GAP 2: Missing Wrapper Classes (HIGH)

### forensic_cleaner.py
- **Problem:** Network Center imports `ForensicCleaner` and `EmergencyWiper` classes, but the file only had a bare `clean_profile()` function.
- **Fix:** Added `ForensicCleaner` class (wraps `clean_profile()`) and `EmergencyWiper` class (secure directory wiping).

### profile_realism_engine.py
- **Problem:** Operations Center imports `ProfileRealismEngine` class, but the file only had bare functions (`enhance_profile()`, etc.).
- **Fix:** Added `ProfileRealismEngine` wrapper class that delegates to `enhance_profile()`.

---

## GAP 3: Import Name Mismatches — GUI Apps (HIGH)

Every GUI app uses `try/except ImportError` guards, so mismatches don't crash the app — but the module silently becomes unavailable, reducing functionality.

### titan_admin.py (6 fixes)
| Import Name | Actual Class | Module |
|-------------|-------------|--------|
| `AutomationOrchestrator` | `TitanOrchestrator` | `titan_automation_orchestrator.py` |
| `TitanAutonomousEngine` | `AutonomousEngine` | `titan_autonomous_engine.py` |
| `MasterVerifier` | `VerificationOrchestrator` | `titan_master_verify.py` |
| `TitanAutoPatcher` | `AutoPatcher` | `titan_auto_patcher.py` |
| `TitanEnvManager` | `SecureConfigManager` | `titan_env.py` |
| `ImmutableOS` (also added `ImmutableOSManager`) | `ImmutableOSManager` | `immutable_os.py` |

### titan_intelligence.py (4 fixes)
| Import Name | Actual Class | Module |
|-------------|-------------|--------|
| `TitanRealtimeCopilot` | `RealtimeCopilot` | `titan_realtime_copilot.py` |
| `TitanDetectionAnalyzer` | `DetectionAnalyzer` | `titan_detection_analyzer.py` |
| `TitanAIOperationsGuard` | `AIOperationsGuard` | `titan_ai_operations_guard.py` |
| `IssuerDefenseEngine` | `IssuerDeclineDefenseEngine` | `issuer_algo_defense.py` |

### titan_operations.py (4 fixes)
| Import Name | Actual Class | Module |
|-------------|-------------|--------|
| `DynamicDataEngine` | `DataFusionEngine` | `dynamic_data.py` |
| `CanvasSubpixelShim` | `CanvasSubPixelShim` | `canvas_subpixel_shim.py` |
| `IndexedDBSynthesizer` | `IndexedDBShardSynthesizer` | `indexeddb_lsng_synthesis.py` |
| `FirstSessionEliminator` | `FirstSessionBiasEliminator` | `first_session_bias_eliminator.py` |
| `WebGLAngleEngine` | `WebGLAngleShim` | `webgl_angle.py` |

### titan_network.py (2 fixes)
| Import Name | Actual Class | Module |
|-------------|-------------|--------|
| `ImmutableOS` | `ImmutableOSManager` | `immutable_os.py` |
| `ReferrerWarmupEngine` | `ReferrerWarmup` | `referrer_warmup.py` |

### app_kyc.py (1 fix)
| Import Name | Actual Class | Module |
|-------------|-------------|--------|
| `CognitiveEngine` | `TitanCognitiveCore` | `cognitive_core.py` |

---

## GAP 4: __init__.py Export Mismatches (MEDIUM)

The central `__init__.py` had 12 wrong class names in its import statements. All fixed with `as` aliases:

| Export Name | Actual Class | Module |
|-------------|-------------|--------|
| `PaymentPreflightV2` | `PaymentPreflightValidator` | `payment_preflight.py` |
| `PreflightResult` | `PreflightReport` | `payment_preflight.py` |
| `PaymentSuccessMetrics` | `PaymentSuccessMetricsDB` | `payment_success_metrics.py` |
| `OperationLogger` | `TitanOperationLogger` | `titan_operation_logger.py` |
| `AutomationOrchestrator` | `TitanOrchestrator` | `titan_automation_orchestrator.py` |
| `TitanAutoPatcher` | `AutoPatcher` | `titan_auto_patcher.py` |
| `VectorMemory` | `TitanVectorMemory` | `titan_vector_memory.py` |
| `WebIntelCollector` | `TitanWebIntel` | `titan_web_intel.py` |
| `MasterAutomation` | `TitanMasterAutomation` | `titan_master_automation.py` |
| `NetworkShieldLoader` | `NetworkShield` | `network_shield_loader.py` |
| `CPUIDShield` | `CPUIDRDTSCShield` | `cpuid_rdtsc_shield.py` |
| `DynamicDataGenerator` | `DataFusionEngine` | `dynamic_data.py` |
| `AgentChain` | `TitanAgent` | `titan_agent_chain.py` |
| `TitanDetectionAnalyzer` | `DetectionAnalyzer` | `titan_detection_analyzer.py` |
| `CanvasSubpixelShim` | `CanvasSubPixelShim` | `canvas_subpixel_shim.py` |

---

## GAP 5: Module Count Reconciliation

### V8.1 Documented: 90 modules → V9.1 Actual: 115 Python modules

**VPS-verified (2026-02-26):**
- **115 Python files** in `/opt/titan/core/` (excluding `__init__.py`, `__pycache__`)
- **3 C source files**: `hardware_shield_v6.c`, `network_shield_v6.c`, `titan_battery.c`
- **2 Shell scripts**: `build_ebpf.sh`, `initramfs_dmi_hook.sh`
- **Total: 120 files** (115 + 3 + 2)

All 115 Python modules are importable on VPS (verified by automated import test).

---

## GAP 6: V9.1 Class Name Mismatches (MEDIUM)

Found during VPS operator-level verification (2026-02-26). These are documentation-only gaps — the classes exist under different names.

| Documented Class | Actual Class(es) | Module |
|-----------------|------------------|--------|
| `AIIntelligenceEngine` | `AIModelSelector`, `AI3DSStrategy` | `ai_intelligence_engine.py` |
| `OllamaBridge` | `LLMLoadBalancer`, `PromptOptimizer` | `ollama_bridge.py` |
| `ChromiumCookieEngine` | `ChromeCryptoEngine`, `HybridInjector` | `chromium_cookie_engine.py` |
| `ProfileIsolation` | `ProfileIsolator`, `CgroupManager` | `profile_isolation.py` |

**Fix:** Documentation updated to use actual class names. No code changes needed.

---

## GAP 7: V9.1 Service Gaps (LOW)

| Service | Status | Note |
|---------|--------|------|
| Ollama | ✅ active | 6 models loaded |
| Redis | ✅ active | Session pub/sub working |
| Xray | ✅ active | Proxy tunneling |
| ntfy | ✅ active | Push notifications |
| Mullvad | ❌ inactive | VPN daemon not running (expected on VPS) |
| SearXNG | ⚠️ not set | `TITAN_SEARXNG_URL` env var not configured |
| FlareSolverr | ⚠️ not set | `TITAN_FLARESOLVERR_URL` env var not configured |

**Fix:** SearXNG and FlareSolverr are optional self-hosted tools. Documented as "configure if available" in `titan.env`.

---

## Summary of All Changes

| Category | Count | Severity |
|----------|-------|----------|
| UTF-16 → UTF-8 encoding fixes | 6 files | CRITICAL |
| Missing wrapper classes added | 2 files | HIGH |
| GUI app import name fixes | 17 imports across 5 apps | HIGH |
| `__init__.py` export fixes | 15 aliases | MEDIUM |
| V9.1 doc class name corrections | 4 entries | MEDIUM |
| V9.1 service env var gaps | 2 entries | LOW |
| **Total fixes** | **46** | |

### Files Modified (V8.1 → V8.2.2)
1. `src/core/canvas_noise.py` — encoding fix
2. `src/core/forensic_cleaner.py` — encoding fix + added classes
3. `src/core/forensic_synthesis_engine.py` — encoding fix
4. `src/core/location_spoofer.py` — encoding fix
5. `src/core/network_shield.py` — encoding fix
6. `src/core/profile_realism_engine.py` — encoding fix + added class
7. `src/core/__init__.py` — 15 export name fixes
8. `src/apps/titan_admin.py` — 6 import fixes + webhook tab
9. `src/apps/titan_intelligence.py` — 4 import fixes
10. `src/apps/titan_operations.py` — 5 import fixes
11. `src/apps/titan_network.py` — 2 import fixes + antidetect tab
12. `src/apps/app_kyc.py` — 1 import fix

### Files Added/Modified (V8.2.2 → V9.1)
13. `src/core/titan_onnx_engine.py` — ONNX inference engine (new)
14. `src/core/titan_webhook_integrations.py` — webhook server (new)
15. `src/apps/app_profile_forge.py` — advanced cookie/LevelDB tab
16. `training/phase2/generate_operator_training_data.py` — training data generator (new)
17. `scripts/vps/` — 8 deployment/verification scripts (new)
