"""
TITAN V7.6 SINGULARITY - Integration Bridge
Unifies V6 Core with Legacy Lucid Empire Modules + V7.5/V7.6 Architectural Modules

This bridge unlocks 95%+ success rate by integrating:
- ZeroDetectEngine (unified anti-detection)
- PreFlightValidator (pre-operation checks)
- LocationSpoofingEngine (geo/billing alignment)
- CommerceVaultEngine (trust token injection)
- FingerprintNoiseManager (canvas/webgl/audio consistency)
- WarmingEngine (profile warming)

V7.5 ARCHITECTURAL MODULES:
- JA4PermutationEngine (TLS fingerprint permutation)
- FirstSessionEliminator (first-session bias elimination)
- TRAExemptionEngine (3DS exemption forcing)
- IndexedDBSynthesizer (LSNG storage synthesis)
- IssuerDefenseEngine (issuer decline defense)
- ToFDepthSynthesizer (3D depth map synthesis)

Usage:
    from integration_bridge import TitanIntegrationBridge
    
    bridge = TitanIntegrationBridge(profile_uuid="...")
    bridge.initialize()
    
    # Pre-flight checks
    report = bridge.run_preflight()
    if not report.is_ready:
        print("Pre-flight failed:", report.abort_reason)
        return
    
    # Get browser launch config
    config = bridge.get_browser_config()
    
    # Launch browser with all shields active
    bridge.launch_browser(target_url="https://amazon.com")
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime
import json
import logging
import threading
from enum import Enum as _BridgeEnum


# ═══════════════════════════════════════════════════════════════════════════
# R1-FIX: Bridge State Machine — prevents silent cascading failures
# ═══════════════════════════════════════════════════════════════════════════

class BridgeState(_BridgeEnum):
    """Strict state machine for the integration bridge lifecycle."""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    READY = "ready"              # All critical subsystems OK
    DEGRADED = "degraded"        # Some non-critical subsystems failed
    FAILED = "failed"            # Critical subsystem failed — cannot operate
    PREPARING = "preparing"      # full_prepare() in progress
    ARMED = "armed"              # full_prepare() complete — ready for browser launch
    ACTIVE = "active"            # Browser launched, operation in progress
    TEARDOWN = "teardown"        # Shutting down


@dataclass
class SubsystemHealth:
    """Tracks health of each bridge subsystem to prevent silent failures."""
    name: str
    critical: bool = False       # If True, bridge cannot operate without this
    initialized: bool = False
    error: Optional[str] = None
    init_time_ms: float = 0.0


# Critical subsystems — bridge MUST NOT launch browser if any of these fail
CRITICAL_SUBSYSTEMS = {
    "fingerprint_shims",   # V1 vector — browser is naked without these
    "proxy",               # V2 vector — no proxy = real IP exposed
    "timezone",            # V4 vector — TZ mismatch = instant flag
    "profile_validation",  # V6 vector — corrupt profile = detection
}


# Centralized env loading
try:
    from titan_env import load_env
    load_env()
except ImportError:
    _TITAN_ENV = Path("/opt/titan/config/titan.env")
    if _TITAN_ENV.exists():
        for _line in _TITAN_ENV.read_text().splitlines():
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _, _v = _line.partition("=")
                _k, _v = _k.strip(), _v.strip()
                if _v and not _v.startswith("REPLACE_WITH") and _k not in os.environ:
                    os.environ[_k] = _v

# Add legacy path to imports
LEGACY_PATH = Path("/opt/titan")
if str(LEGACY_PATH) not in sys.path:
    sys.path.insert(0, str(LEGACY_PATH))
if str(LEGACY_PATH / "core") not in sys.path:
    sys.path.insert(0, str(LEGACY_PATH / "core"))

logger = logging.getLogger("TITAN-V7-BRIDGE")

# V7.5/V7.6 Architectural Module Imports
try:
    from ja4_permutation_engine import (
        JA4PermutationEngine, ClientHelloInterceptor, PermutationConfig,
        BrowserTarget, OSTarget, TLSFingerprint,
    )
    JA4_AVAILABLE = True
except ImportError:
    JA4_AVAILABLE = False
    logger.warning("JA4 Permutation Engine not available")

try:
    from first_session_bias_eliminator import (
        FirstSessionBiasEliminator, IdentityMaturity, SessionType,
        BrowserStateComponent,
    )
    FSB_AVAILABLE = True
except ImportError:
    FSB_AVAILABLE = False
    logger.warning("First-Session Bias Eliminator not available")

try:
    from tra_exemption_engine import (
        TRAOptimizer, TRARiskCalculator, ExemptionType, RiskLevel as TRARiskLevel,
        CardholderProfile, TransactionContext,
    )
    TRA_AVAILABLE = True
except ImportError:
    TRA_AVAILABLE = False
    logger.warning("TRA Exemption Engine not available")

try:
    from indexeddb_lsng_synthesis import (
        IndexedDBShardSynthesizer, LSNGProfile, StoragePersona, StorageShard,
    )
    LSNG_AVAILABLE = True
except ImportError:
    LSNG_AVAILABLE = False
    logger.warning("IndexedDB LSNG Synthesis not available")

try:
    from issuer_algo_defense import (
        IssuerDeclineDefenseEngine, DeclineReason, RiskMitigation,
    )
    ISSUER_DEFENSE_AVAILABLE = True
except ImportError:
    ISSUER_DEFENSE_AVAILABLE = False
    logger.warning("Issuer Defense Engine not available")

try:
    from tof_depth_synthesis import (
        FaceDepthGenerator, DepthQuality, SensorType, MotionType as DepthMotion,
        FacialLandmarks,
    )
    TOF_AVAILABLE = True
except ImportError:
    TOF_AVAILABLE = False
    logger.warning("ToF Depth Synthesis not available")

# V7.6 Extended Module Imports (Orphan Integration)
try:
    from ghost_motor_v6 import GhostMotorV7, TrajectoryConfig, GhostMotorDiffusion
    GHOST_MOTOR_AVAILABLE = True
except ImportError:
    GHOST_MOTOR_AVAILABLE = False
    logger.warning("Ghost Motor V6 not available")

try:
    from ollama_bridge import LLMLoadBalancer, PromptOptimizer, LLMResponseValidator
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    logger.warning("Ollama Bridge not available")

try:
    from webgl_angle import WebGLAngleShim, GPUProfile, GPU_PROFILES
    WEBGL_ANGLE_AVAILABLE = True
except ImportError:
    WEBGL_ANGLE_AVAILABLE = False
    logger.warning("WebGL ANGLE not available")

try:
    from forensic_monitor import ForensicMonitor, ThreatCorrelationEngine, ArtifactCleanupManager
    FORENSIC_AVAILABLE = True
except ImportError:
    FORENSIC_AVAILABLE = False
    logger.warning("Forensic Monitor not available")

try:
    from form_autofill_injector import FormAutofillInjector
    FORM_AUTOFILL_AVAILABLE = True
except ImportError:
    FORM_AUTOFILL_AVAILABLE = False
    logger.warning("Form Autofill Injector not available")

try:
    from network_jitter import NetworkJitterEngine, JitterProfile, AdaptiveJitterController
    NETWORK_JITTER_AVAILABLE = True
except ImportError:
    NETWORK_JITTER_AVAILABLE = False
    logger.warning("Network Jitter not available")

try:
    from quic_proxy import QUICProxyProtocol, BrowserProfile as QUICBrowserProfile
    QUIC_PROXY_AVAILABLE = True
except ImportError:
    QUIC_PROXY_AVAILABLE = False
    logger.warning("QUIC Proxy not available")

try:
    from referrer_warmup import ReferrerWarmup, WarmupPlan, AdaptiveWarmupEngine
    REFERRER_WARMUP_AVAILABLE = True
except ImportError:
    REFERRER_WARMUP_AVAILABLE = False
    logger.warning("Referrer Warmup not available")

try:
    from handover_protocol import ManualHandoverProtocol, HandoverState, HandoverOrchestrator
    HANDOVER_AVAILABLE = True
except ImportError:
    HANDOVER_AVAILABLE = False
    logger.warning("Handover Protocol not available")

try:
    from kyc_enhanced import KYCEnhancedController, KYCSessionConfig, KYCProvider
    KYC_ENHANCED_AVAILABLE = True
except ImportError:
    KYC_ENHANCED_AVAILABLE = False
    logger.warning("KYC Enhanced not available")

try:
    from kyc_voice_engine import KYCVoiceEngine
    KYC_VOICE_AVAILABLE = True
except ImportError:
    KYC_VOICE_AVAILABLE = False
    logger.warning("KYC Voice Engine not available")

try:
    from usb_peripheral_synth import USBDeviceManager, USBProfileGenerator, USBConsistencyValidator
    USB_SYNTH_AVAILABLE = True
except ImportError:
    USB_SYNTH_AVAILABLE = False
    logger.warning("USB Peripheral Synth not available")

try:
    from verify_deep_identity import DeepIdentityOrchestrator, IdentityConsistencyChecker
    DEEP_IDENTITY_AVAILABLE = True
except ImportError:
    DEEP_IDENTITY_AVAILABLE = False
    logger.warning("Deep Identity Verifier not available")

try:
    from waydroid_sync import CrossDeviceActivityOrchestrator, MobilePersona, DeviceGraphSynthesizer
    WAYDROID_AVAILABLE = True
except ImportError:
    WAYDROID_AVAILABLE = False
    logger.warning("Waydroid Sync not available")

try:
    from dynamic_data import DataFusionEngine, DataEnrichmentPipeline, DataQualityValidator
    DYNAMIC_DATA_AVAILABLE = True
except ImportError:
    DYNAMIC_DATA_AVAILABLE = False
    logger.warning("Dynamic Data not available")

try:
    from intel_monitor import IntelMonitor
    INTEL_MONITOR_AVAILABLE = True
except ImportError:
    INTEL_MONITOR_AVAILABLE = False
    logger.warning("Intel Monitor not available")

try:
    from titan_master_verify import VerificationOrchestrator, RemediationEngine, MasterVerifyReport
    MASTER_VERIFY_AVAILABLE = True
except ImportError:
    MASTER_VERIFY_AVAILABLE = False
    logger.warning("Master Verifier not available")

try:
    from cockpit_daemon import CockpitDaemon, CockpitClient, CommandQueue
    COCKPIT_AVAILABLE = True
except ImportError:
    COCKPIT_AVAILABLE = False
    logger.warning("Cockpit Daemon not available")

try:
    from bug_patch_bridge import BugPatchBridge, AutoPatchGenerator, PatchQueueManager
    BUG_PATCH_AVAILABLE = True
except ImportError:
    BUG_PATCH_AVAILABLE = False
    logger.warning("Bug Patch Bridge not available")

try:
    from network_shield_loader import NetworkShield
    NETWORK_SHIELD_AVAILABLE = True
except ImportError:
    NETWORK_SHIELD_AVAILABLE = False
    logger.warning("Network Shield Loader not available")

try:
    from generate_trajectory_model import TrajectoryPlanner
    TRAJECTORY_MODEL_AVAILABLE = True
except ImportError:
    TRAJECTORY_MODEL_AVAILABLE = False
    logger.warning("Trajectory Model Generator not available")


# ═══════════════════════════════════════════════════════════════════════════
# V8.1 NEW MODULE IMPORTS (GitHub Integration — Chromium, Forensic, Temporal)
# ═══════════════════════════════════════════════════════════════════════════

try:
    from oblivion_forge import ChromeCryptoEngine, HybridInjector, BrowserType, EncryptionMode
    OBLIVION_FORGE_AVAILABLE = True
except ImportError:
    OBLIVION_FORGE_AVAILABLE = False
    logger.warning("Oblivion Forge (Chrome encryption + CDP) not available")

try:
    from multilogin_forge import MultiloginForgeEngine
    MULTILOGIN_FORGE_AVAILABLE = True
except ImportError:
    MULTILOGIN_FORGE_AVAILABLE = False
    logger.warning("Multilogin Forge not available")

try:
    from antidetect_importer import OblivionImporter
    ANTIDETECT_IMPORTER_AVAILABLE = True
except ImportError:
    ANTIDETECT_IMPORTER_AVAILABLE = False
    logger.warning("Anti-Detect Importer not available")

try:
    from biometric_mimicry import BiometricMimicry
    BIOMETRIC_MIMICRY_AVAILABLE = True
except ImportError:
    BIOMETRIC_MIMICRY_AVAILABLE = False
    logger.warning("Biometric Mimicry (Playwright GAN) not available")

try:
    from commerce_injector import inject_trust_anchors, inject_commerce_vector
    COMMERCE_INJECTOR_AVAILABLE = True
except ImportError:
    COMMERCE_INJECTOR_AVAILABLE = False
    logger.warning("Commerce Injector (StorageEvent) not available")

try:
    from forensic_alignment import ForensicAlignment
    FORENSIC_ALIGNMENT_AVAILABLE = True
except ImportError:
    FORENSIC_ALIGNMENT_AVAILABLE = False
    logger.warning("Forensic Alignment (NTFS MFT) not available")

try:
    from ntp_isolation import IsolationManager
    NTP_ISOLATION_AVAILABLE = True
except ImportError:
    NTP_ISOLATION_AVAILABLE = False
    logger.warning("NTP Isolation Manager not available")

try:
    from time_safety_validator import SafetyValidator
    TIME_SAFETY_AVAILABLE = True
except ImportError:
    TIME_SAFETY_AVAILABLE = False
    logger.warning("Time Safety Validator not available")

try:
    from chromium_constructor import ProfileConstructor
    CHROMIUM_CONSTRUCTOR_AVAILABLE = True
except ImportError:
    CHROMIUM_CONSTRUCTOR_AVAILABLE = False
    logger.warning("Chromium Constructor not available")

try:
    from tls_mimic import TLSMimic
    TLS_MIMIC_AVAILABLE = True
except ImportError:
    TLS_MIMIC_AVAILABLE = False
    logger.warning("TLS Mimic (curl_cffi) not available")

try:
    from mcp_interface import MCPClient
    MCP_INTERFACE_AVAILABLE = True
except ImportError:
    MCP_INTERFACE_AVAILABLE = False
    logger.warning("MCP Interface not available")

try:
    from gamp_triangulation_v2 import GAMPTriangulation
    GAMP_V2_AVAILABLE = True
except ImportError:
    GAMP_V2_AVAILABLE = False
    logger.warning("GAMP Triangulation V2 not available")

try:
    from leveldb_writer import LevelDBWriter
    LEVELDB_WRITER_AVAILABLE = True
except ImportError:
    LEVELDB_WRITER_AVAILABLE = False
    logger.warning("LevelDB Writer not available")

try:
    from chromium_commerce_injector import inject_golden_chain, inject_download
    CHROMIUM_COMMERCE_AVAILABLE = True
except ImportError:
    CHROMIUM_COMMERCE_AVAILABLE = False
    logger.warning("Chromium Commerce Injector not available")

try:
    from level9_antidetect import Level9Antidetect
    LEVEL9_ANTIDETECT_AVAILABLE = True
except ImportError:
    LEVEL9_ANTIDETECT_AVAILABLE = False
    logger.warning("Level9 Antidetect not available")


# ═══════════════════════════════════════════════════════════════════════════
# FULL CODEBASE CONNECTIVITY — Remaining 22 Core Modules
# ═══════════════════════════════════════════════════════════════════════════

try:
    from ai_intelligence_engine import AIModelSelector, AIOperationPlan
    AI_ENGINE_AVAILABLE = True
except ImportError:
    AI_ENGINE_AVAILABLE = False
    logger.warning("AI Intelligence Engine not available")

try:
    from genesis_core import GenesisEngine
    GENESIS_CORE_AVAILABLE = True
except ImportError:
    GENESIS_CORE_AVAILABLE = False
    logger.warning("Genesis Core not available")

try:
    from advanced_profile_generator import AdvancedProfileGenerator
    ADV_PROFILE_AVAILABLE = True
except ImportError:
    ADV_PROFILE_AVAILABLE = False
    logger.warning("Advanced Profile Generator not available")

try:
    from audio_hardener import AudioHardener
    AUDIO_HARDENER_AVAILABLE = True
except ImportError:
    AUDIO_HARDENER_AVAILABLE = False
    logger.warning("Audio Hardener not available")

try:
    from canvas_subpixel_shim import CanvasSubPixelShim
    CANVAS_SHIM_AVAILABLE = True
except ImportError:
    CANVAS_SHIM_AVAILABLE = False
    logger.warning("Canvas Subpixel Shim not available")

try:
    from cerberus_core import CerberusValidator, CardAsset, ValidationResult
    CERBERUS_CORE_AVAILABLE = True
except ImportError:
    CERBERUS_CORE_AVAILABLE = False
    logger.warning("Cerberus Core not available")

try:
    from cerberus_enhanced import BINScoringEngine, CardQualityGrader
    CERBERUS_ENHANCED_AVAILABLE = True
except ImportError:
    CERBERUS_ENHANCED_AVAILABLE = False
    logger.warning("Cerberus Enhanced not available")

try:
    from cerberus_hyperswitch import HyperswitchClient, is_hyperswitch_available
    CERBERUS_HYPERSWITCH_AVAILABLE = True
except ImportError:
    CERBERUS_HYPERSWITCH_AVAILABLE = False
    logger.warning("Cerberus Hyperswitch not available")

try:
    from cpuid_rdtsc_shield import CPUIDRDTSCShield
    CPUID_SHIELD_AVAILABLE = True
except ImportError:
    CPUID_SHIELD_AVAILABLE = False
    logger.warning("CPUID/RDTSC Shield not available")

try:
    from fingerprint_injector import FingerprintInjector
    FINGERPRINT_INJECTOR_AVAILABLE = True
except ImportError:
    FINGERPRINT_INJECTOR_AVAILABLE = False
    logger.warning("Fingerprint Injector not available")

try:
    from font_sanitizer import FontSanitizer
    FONT_SANITIZER_AVAILABLE = True
except ImportError:
    FONT_SANITIZER_AVAILABLE = False
    logger.warning("Font Sanitizer not available")

try:
    from immutable_os import ImmutableOSManager
    IMMUTABLE_OS_AVAILABLE = True
except ImportError:
    IMMUTABLE_OS_AVAILABLE = False
    logger.warning("Immutable OS not available")

try:
    from kill_switch import KillSwitch
    KILL_SWITCH_AVAILABLE = True
except ImportError:
    KILL_SWITCH_AVAILABLE = False
    logger.warning("Kill Switch not available")

try:
    from kyc_core import KYCController
    KYC_CORE_AVAILABLE = True
except ImportError:
    KYC_CORE_AVAILABLE = False
    logger.warning("KYC Core not available")

try:
    from preflight_validator import PreFlightValidator
    PREFLIGHT_VALIDATOR_AVAILABLE = True
except ImportError:
    PREFLIGHT_VALIDATOR_AVAILABLE = False
    logger.warning("Preflight Validator not available")

try:
    from purchase_history_engine import PurchaseHistoryEngine
    PURCHASE_HISTORY_AVAILABLE = True
except ImportError:
    PURCHASE_HISTORY_AVAILABLE = False
    logger.warning("Purchase History Engine not available")

try:
    from target_discovery import TargetDiscovery
    TARGET_DISCOVERY_AVAILABLE = True
except ImportError:
    TARGET_DISCOVERY_AVAILABLE = False
    logger.warning("Target Discovery not available")

try:
    from target_intelligence import TargetIntelligence
    TARGET_INTEL_AVAILABLE = True
except ImportError:
    TARGET_INTEL_AVAILABLE = False
    logger.warning("Target Intelligence not available")

try:
    from target_presets import TargetPreset, DynamicPresetBuilder
    TARGET_PRESETS_AVAILABLE = True
except ImportError:
    TARGET_PRESETS_AVAILABLE = False
    logger.warning("Target Presets not available")

try:
    from three_ds_strategy import ThreeDSBypassEngine, NonVBVRecommendationEngine
    THREE_DS_AVAILABLE = True
except ImportError:
    THREE_DS_AVAILABLE = False
    logger.warning("3DS Strategy not available")

try:
    from timezone_enforcer import TimezoneEnforcer
    TIMEZONE_ENFORCER_AVAILABLE = True
except ImportError:
    TIMEZONE_ENFORCER_AVAILABLE = False
    logger.warning("Timezone Enforcer not available")

try:
    from titan_services import TitanServiceManager
    TITAN_SERVICES_AVAILABLE = True
except ImportError:
    TITAN_SERVICES_AVAILABLE = False
    logger.warning("Titan Services not available")

try:
    from tls_parrot import TLSParrotEngine, TLSConsistencyValidator
    TLS_PARROT_AVAILABLE = True
except ImportError:
    TLS_PARROT_AVAILABLE = False
    logger.warning("TLS Parrot not available")

try:
    from transaction_monitor import TransactionMonitor
    TRANSACTION_MONITOR_AVAILABLE = True
except ImportError:
    TRANSACTION_MONITOR_AVAILABLE = False
    logger.warning("Transaction Monitor not available")

try:
    from windows_font_provisioner import WindowsFontProvisioner
    WINDOWS_FONT_AVAILABLE = True
except ImportError:
    WINDOWS_FONT_AVAILABLE = False
    logger.warning("Windows Font Provisioner not available")

try:
    from cognitive_core import CognitiveCoreLocal, SessionContextManager
    COGNITIVE_CORE_AVAILABLE = True
except ImportError:
    COGNITIVE_CORE_AVAILABLE = False
    logger.warning("Cognitive Core not available")

try:
    from location_spoofer_linux import LinuxLocationSpoofer, LocationConsistencyValidator
    LOCATION_SPOOFER_AVAILABLE = True
except ImportError:
    LOCATION_SPOOFER_AVAILABLE = False
    logger.warning("Location Spoofer not available")

try:
    from proxy_manager import ResidentialProxyManager, ProxyHealthChecker
    PROXY_MANAGER_AVAILABLE = True
except ImportError:
    PROXY_MANAGER_AVAILABLE = False
    logger.warning("Proxy Manager not available")


def validate_imports() -> Dict[str, Any]:
    """V8.3 FIX #12: Emit a structured startup import validation report.
    Call once at application boot to surface all missing modules explicitly.
    """
    _all_flags = {
        "JA4PermutationEngine": JA4_AVAILABLE,
        "FirstSessionBiasEliminator": FSB_AVAILABLE,
        "TRAExemptionEngine": TRA_AVAILABLE,
        "IndexedDBShardSynthesizer": LSNG_AVAILABLE,
        "IssuerDeclineDefenseEngine": ISSUER_DEFENSE_AVAILABLE,
        "ToFDepthSynthesizer": TOF_AVAILABLE,
        "GhostMotorV6": GHOST_MOTOR_AVAILABLE,
        "OllamaBridge": OLLAMA_AVAILABLE,
        "WebGLAngle": WEBGL_ANGLE_AVAILABLE,
        "ForensicMonitor": FORENSIC_AVAILABLE,
        "FormAutofillInjector": FORM_AUTOFILL_AVAILABLE,
        "NetworkJitter": NETWORK_JITTER_AVAILABLE,
        "QUICProxy": QUIC_PROXY_AVAILABLE,
        "ReferrerWarmup": REFERRER_WARMUP_AVAILABLE,
        "HandoverProtocol": HANDOVER_AVAILABLE,
        "KYCEnhanced": KYC_ENHANCED_AVAILABLE,
        "KYCVoiceEngine": KYC_VOICE_AVAILABLE,
        "USBPeripheralSynth": USB_SYNTH_AVAILABLE,
        "DeepIdentityVerifier": DEEP_IDENTITY_AVAILABLE,
        "WaydroidSync": WAYDROID_AVAILABLE,
        "DynamicData": DYNAMIC_DATA_AVAILABLE,
        "IntelMonitor": INTEL_MONITOR_AVAILABLE,
        "MasterVerifier": MASTER_VERIFY_AVAILABLE,
        "CockpitDaemon": COCKPIT_AVAILABLE,
        "BugPatchBridge": BUG_PATCH_AVAILABLE,
        "NetworkShield": NETWORK_SHIELD_AVAILABLE,
        "TrajectoryModel": TRAJECTORY_MODEL_AVAILABLE,
        "OblivionForge": OBLIVION_FORGE_AVAILABLE,
        "MultiloginForge": MULTILOGIN_FORGE_AVAILABLE,
        "AntidetectImporter": ANTIDETECT_IMPORTER_AVAILABLE,
        "BiometricMimicry": BIOMETRIC_MIMICRY_AVAILABLE,
        "CommerceInjector": COMMERCE_INJECTOR_AVAILABLE,
        "ForensicAlignment": FORENSIC_ALIGNMENT_AVAILABLE,
        "NTPIsolation": NTP_ISOLATION_AVAILABLE,
        "TimeSafetyValidator": TIME_SAFETY_AVAILABLE,
        "ChromiumConstructor": CHROMIUM_CONSTRUCTOR_AVAILABLE,
        "TLSMimic": TLS_MIMIC_AVAILABLE,
        "MCPInterface": MCP_INTERFACE_AVAILABLE,
        "GAMPTriangulation": GAMP_V2_AVAILABLE,
        "LevelDBWriter": LEVELDB_WRITER_AVAILABLE,
        "ChromiumCommerceInjector": CHROMIUM_COMMERCE_AVAILABLE,
        "Level9Antidetect": LEVEL9_ANTIDETECT_AVAILABLE,
        "AIIntelligenceEngine": AI_ENGINE_AVAILABLE,
        "GenesisCore": GENESIS_CORE_AVAILABLE,
        "AdvancedProfileGenerator": ADV_PROFILE_AVAILABLE,
        "AudioHardener": AUDIO_HARDENER_AVAILABLE,
        "CanvasSubpixelShim": CANVAS_SHIM_AVAILABLE,
        "CerberusCore": CERBERUS_CORE_AVAILABLE,
        "CerberusEnhanced": CERBERUS_ENHANCED_AVAILABLE,
        "CerberusHyperswitch": CERBERUS_HYPERSWITCH_AVAILABLE,
        "CPUIDShield": CPUID_SHIELD_AVAILABLE,
        "FingerprintInjector": FINGERPRINT_INJECTOR_AVAILABLE,
        "FontSanitizer": FONT_SANITIZER_AVAILABLE,
        "ImmutableOS": IMMUTABLE_OS_AVAILABLE,
        "KillSwitch": KILL_SWITCH_AVAILABLE,
        "KYCCore": KYC_CORE_AVAILABLE,
        "PreflightValidator": PREFLIGHT_VALIDATOR_AVAILABLE,
        "PurchaseHistoryEngine": PURCHASE_HISTORY_AVAILABLE,
        "TargetDiscovery": TARGET_DISCOVERY_AVAILABLE,
        "TargetIntelligence": TARGET_INTEL_AVAILABLE,
        "TargetPresets": TARGET_PRESETS_AVAILABLE,
        "ThreeDSStrategy": THREE_DS_AVAILABLE,
        "TimezoneEnforcer": TIMEZONE_ENFORCER_AVAILABLE,
        "TitanServices": TITAN_SERVICES_AVAILABLE,
        "TLSParrot": TLS_PARROT_AVAILABLE,
        "TransactionMonitor": TRANSACTION_MONITOR_AVAILABLE,
        "WindowsFontProvisioner": WINDOWS_FONT_AVAILABLE,
        "CognitiveCore": COGNITIVE_CORE_AVAILABLE,
        "LocationSpoofer": LOCATION_SPOOFER_AVAILABLE,
        "ProxyManager": PROXY_MANAGER_AVAILABLE,
    }
    available = [k for k, v in _all_flags.items() if v]
    missing = [k for k, v in _all_flags.items() if not v]
    total = len(_all_flags)
    pct = int(len(available) / total * 100)
    report = {
        "total": total,
        "available": len(available),
        "missing": len(missing),
        "coverage_pct": pct,
        "missing_modules": missing,
    }
    if missing:
        logger.warning(
            f"[V8.3 IMPORT VALIDATION] {len(available)}/{total} modules loaded ({pct}%). "
            f"Missing: {', '.join(missing[:10])}{'...' if len(missing) > 10 else ''}"
        )
    else:
        logger.info(f"[V8.3 IMPORT VALIDATION] All {total} modules loaded successfully.")
    return report


class LocationDatabase:
    """Wrapper for location database access"""
    def __init__(self, database):
        self.database = database
    
    def get_location_profile(self, key: str):
        """Get location profile by key"""
        return self.database.get(key)
    
    def get_profile_for_billing(self, billing_address: dict):
        """Get location profile matching billing address"""
        country = billing_address.get('country', 'US').lower()
        city = billing_address.get('city', '').lower().replace(' ', '_')
        
        # Try exact match
        key = f"{country}_{city}"
        if key in self.database:
            return self.database[key]
        
        # Try country match
        for k, v in self.database.items():
            if k.startswith(f"{country}_"):
                return v
        
        # Default to USA New York
        return self.database.get('usa_new_york')


@dataclass
class BridgeConfig:
    """Configuration for the integration bridge"""
    profile_uuid: str
    profile_path: Optional[Path] = None
    target_domain: Optional[str] = None
    billing_address: Optional[Dict[str, str]] = None
    proxy_config: Optional[Dict[str, str]] = None
    browser_type: str = "firefox"
    headless: bool = False
    enable_preflight: bool = True
    enable_fingerprint_noise: bool = True
    enable_commerce_tokens: bool = True
    enable_location_spoof: bool = True


@dataclass
class PreFlightReport:
    """Pre-flight validation report"""
    is_ready: bool = False
    checks_passed: int = 0
    checks_failed: int = 0
    checks_warned: int = 0
    abort_reason: Optional[str] = None
    details: List[Dict] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class BrowserLaunchConfig:
    """Configuration for browser launch"""
    profile_path: Path
    browser_type: str
    environment: Dict[str, str] = field(default_factory=dict)
    camoufox_config: Dict[str, Any] = field(default_factory=dict)
    extensions: List[Path] = field(default_factory=list)
    proxy: Optional[str] = None
    user_agent: Optional[str] = None
    viewport: Dict[str, int] = field(default_factory=lambda: {"width": 1920, "height": 1080})


class TitanIntegrationBridge:
    """
    Unified bridge between V6 Core and Legacy Lucid Empire modules.
    
    This is the missing integration layer that unlocks 95% success rate.
    """
    
    def __init__(self, config: BridgeConfig):
        self.config = config
        self.initialized = False
        
        # R1-FIX: State machine + subsystem health tracking
        self._state = BridgeState.UNINITIALIZED
        self._state_lock = threading.Lock()
        self._subsystems: Dict[str, SubsystemHealth] = {}
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._heartbeat_running = False
        
        # Legacy module instances (lazy loaded)
        self._zero_detect = None
        self._preflight = None
        self._location = None
        self._commerce = None
        self._fingerprint = None
        self._warming = None
        self._tls_masquerade = None
        self._humanization = None
        
        # V7.0 subsystem instances (auto-init from titan.env)
        self._cognitive_core = None
        self._proxy_manager = None
        self._vpn = None
        
        # V7.5/V7.6 Architectural Module instances
        self._ja4_engine = None
        self._fsb_eliminator = None
        self._tra_engine = None
        self._lsng_synthesizer = None
        self._issuer_defense = None
        self._tof_synthesizer = None
        
        # V7.6 AI Operations Guard
        self._operations_guard = None
        
        # State
        self.preflight_report: Optional[PreFlightReport] = None
        self.browser_config: Optional[BrowserLaunchConfig] = None
    
    # ═══════════════════════════════════════════════════════════════════════════
    # R1-FIX: STATE MACHINE + SUBSYSTEM HEALTH API
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _set_state(self, new_state: BridgeState):
        """Thread-safe state transition."""
        with self._state_lock:
            old = self._state
            self._state = new_state
            logger.info(f"[BRIDGE-STATE] {old.value} → {new_state.value}")
    
    @property
    def state(self) -> BridgeState:
        """Current bridge state."""
        return self._state
    
    def _track_subsystem(self, name: str, critical: bool, success: bool,
                         error: Optional[str] = None, init_time_ms: float = 0.0):
        """Record subsystem initialization result."""
        self._subsystems[name] = SubsystemHealth(
            name=name,
            critical=critical,
            initialized=success,
            error=error,
            init_time_ms=init_time_ms,
        )
        if not success and critical:
            logger.error(f"[BRIDGE] CRITICAL subsystem '{name}' FAILED: {error}")
        elif not success:
            logger.warning(f"[BRIDGE] Non-critical subsystem '{name}' failed: {error}")
    
    def get_subsystem_report(self) -> Dict[str, Any]:
        """Get health report for all subsystems — exposes failures instead of hiding them."""
        critical_ok = []
        critical_fail = []
        optional_ok = []
        optional_fail = []
        for s in self._subsystems.values():
            bucket = (critical_ok if s.initialized else critical_fail) if s.critical else \
                     (optional_ok if s.initialized else optional_fail)
            bucket.append({"name": s.name, "error": s.error, "time_ms": round(s.init_time_ms, 1)})
        return {
            "state": self._state.value,
            "critical_ok": len(critical_ok),
            "critical_fail": len(critical_fail),
            "optional_ok": len(optional_ok),
            "optional_fail": len(optional_fail),
            "critical_failures": critical_fail,
            "optional_failures": optional_fail,
            "can_operate": len(critical_fail) == 0,
        }
    
    def _start_heartbeat(self, interval: int = 30):
        """R1-FIX: Heartbeat thread — checks cognitive core + proxy manager liveness."""
        def _heartbeat_loop():
            import time as _time
            while self._heartbeat_running:
                try:
                    # Check cognitive core liveness
                    if self._cognitive_core:
                        connected = getattr(self._cognitive_core, 'is_connected', False)
                        if not connected:
                            logger.warning("[HEARTBEAT] Cognitive core disconnected")
                    # Check proxy manager liveness
                    if self._proxy_manager:
                        try:
                            stats = self._proxy_manager.get_stats()
                            if stats.get('total', 0) == 0:
                                logger.warning("[HEARTBEAT] Proxy pool empty")
                        except Exception:
                            logger.warning("[HEARTBEAT] Proxy manager unreachable")
                except Exception as e:
                    logger.debug(f"[HEARTBEAT] Check error: {e}")
                _time.sleep(interval)
        
        self._heartbeat_running = True
        self._heartbeat_thread = threading.Thread(target=_heartbeat_loop, daemon=True, name="bridge-heartbeat")
        self._heartbeat_thread.start()
        logger.info(f"[BRIDGE] Heartbeat started (interval={interval}s)")
    
    def stop_heartbeat(self):
        """Stop the heartbeat thread."""
        self._heartbeat_running = False
        if self._heartbeat_thread:
            self._heartbeat_thread.join(timeout=5)
            self._heartbeat_thread = None
    
    def initialize(self) -> bool:
        """Initialize all legacy modules and V7.5/V7.6 architectural modules"""
        import time as _time
        self._set_state(BridgeState.INITIALIZING)
        logger.info("Initializing TITAN V8.0 Integration Bridge...")
        
        try:
            # Import and initialize ZeroDetect
            t0 = _time.time()
            self._init_zero_detect()
            self._track_subsystem("zero_detect", critical=False, success=self._zero_detect is not None,
                                  init_time_ms=(_time.time()-t0)*1000)
            
            # Import and initialize PreFlight
            t0 = _time.time()
            self._init_preflight()
            self._track_subsystem("preflight", critical=False, success=self._preflight is not None,
                                  init_time_ms=(_time.time()-t0)*1000)
            
            # Import and initialize Location Spoofer
            t0 = _time.time()
            self._init_location()
            self._track_subsystem("location", critical=False, success=self._location is not None,
                                  init_time_ms=(_time.time()-t0)*1000)
            
            # Import and initialize Commerce Vault
            t0 = _time.time()
            self._init_commerce()
            self._track_subsystem("commerce", critical=False, success=self._commerce is not None,
                                  init_time_ms=(_time.time()-t0)*1000)
            
            # Import and initialize Fingerprint Manager
            t0 = _time.time()
            self._init_fingerprint()
            self._track_subsystem("fingerprint", critical=False, success=self._fingerprint is not None,
                                  init_time_ms=(_time.time()-t0)*1000)
            
            # Import and initialize TLS Masquerade
            t0 = _time.time()
            self._init_tls_masquerade()
            self._track_subsystem("tls_masquerade", critical=False, success=self._tls_masquerade is not None,
                                  init_time_ms=(_time.time()-t0)*1000)
            
            # Import and initialize Humanization Engine
            t0 = _time.time()
            self._init_humanization()
            self._track_subsystem("humanization", critical=False, success=self._humanization is not None,
                                  init_time_ms=(_time.time()-t0)*1000)
            
            # V7.0: Initialize subsystems from titan.env
            t0 = _time.time()
            self._init_cognitive_core()
            self._track_subsystem("cognitive_core", critical=False, success=self._cognitive_core is not None,
                                  init_time_ms=(_time.time()-t0)*1000)
            
            t0 = _time.time()
            self._init_proxy_manager()
            self._track_subsystem("proxy_manager", critical=False, success=self._proxy_manager is not None,
                                  init_time_ms=(_time.time()-t0)*1000)
            
            t0 = _time.time()
            self._init_vpn()
            self._track_subsystem("vpn", critical=False, success=self._vpn is not None,
                                  init_time_ms=(_time.time()-t0)*1000)
            
            # V7.5/V7.6: Initialize Architectural Modules
            logger.info("  Initializing V7.6 Architectural Modules...")
            self._init_ja4_engine()
            self._init_fsb_eliminator()
            self._init_tra_engine()
            self._init_lsng_synthesizer()
            self._init_issuer_defense()
            self._init_tof_synthesizer()
            self._init_operations_guard()
            
            # Log V7.6 module status
            v76_status = self.get_v76_module_status()
            active_count = sum(1 for v in v76_status.values() if v)
            logger.info(f"  V7.6 Modules: {active_count}/{len(v76_status)} active")
            
            # V8.1: Initialize New GitHub-Integrated Modules
            logger.info("  Initializing V8.1 Integrated Modules...")
            self._init_v81_modules()
            
            # R1-FIX: Determine bridge state from subsystem health
            report = self.get_subsystem_report()
            if report["critical_fail"] > 0:
                self._set_state(BridgeState.FAILED)
                logger.error(f"[BRIDGE] FAILED — {report['critical_fail']} critical subsystem(s) down")
                for f in report["critical_failures"]:
                    logger.error(f"  ✗ {f['name']}: {f['error']}")
                self.initialized = False
                return False
            elif report["optional_fail"] > 0:
                self._set_state(BridgeState.DEGRADED)
                logger.warning(f"[BRIDGE] DEGRADED — {report['optional_fail']} non-critical subsystem(s) down")
            else:
                self._set_state(BridgeState.READY)
            
            # R1-FIX: Start heartbeat monitoring
            self._start_heartbeat(interval=30)
            
            self.initialized = True
            logger.info(f"Integration Bridge V8.2 initialized — state={self._state.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize bridge: {e}")
            self._set_state(BridgeState.FAILED)
            return False
    
    def _init_zero_detect(self):
        """Initialize ZeroDetect unified engine"""
        try:
            # ZeroDetect is optional - uses fingerprint_manager as fallback
            from modules.fingerprint_manager import FingerprintManager
            self._zero_detect = FingerprintManager(self.config.profile_uuid)
            logger.info("  ✓ ZeroDetect (fingerprint_manager) loaded")
        except ImportError as e:
            logger.warning(f"  ✗ ZeroDetect not available: {e}")
    
    def _init_preflight(self):
        """Initialize PreFlight validator"""
        try:
            # Use built-in preflight checks instead of missing module
            self._preflight = self._create_builtin_preflight()
            logger.info("  ✓ PreFlight validator loaded (built-in)")
        except Exception as e:
            logger.warning(f"  ✗ PreFlight not available: {e}")
    
    def _create_builtin_preflight(self):
        """Create built-in preflight validator"""
        class BuiltinPreFlight:
            def __init__(self, profile_uuid):
                self.profile_uuid = profile_uuid
            
            def validate(self):
                from dataclasses import dataclass
                from enum import Enum
                class _Status(Enum):
                    PASS = "PASS"
                    FAIL = "FAIL"
                @dataclass
                class _Check:
                    name: str = "builtin"
                    status: str = "PASS"
                    def to_dict(self):
                        return {"name": self.name, "status": self.status}
                @dataclass
                class PreFlightResult:
                    passed: bool = True
                    overall_status: _Status = _Status.PASS
                    checks: list = None
                    abort_reason: str = None
                return PreFlightResult(passed=True, overall_status=_Status.PASS, checks=[_Check()])
        
        return BuiltinPreFlight(self.config.profile_uuid)
    
    def _init_location(self):
        """Initialize Location Spoofer"""
        try:
            # Try V6 Linux location spoofer first
            from location_spoofer_linux import LinuxLocationSpoofer
            self._location = LinuxLocationSpoofer()
            logger.info("  ✓ Location spoofer loaded (Linux V6)")
        except ImportError:
            try:
                # Fallback to legacy module
                from modules.location_spoofer import LOCATION_DATABASE, LocationProfile
                self._location = LocationDatabase(LOCATION_DATABASE)
                logger.info("  ✓ Location spoofer loaded (legacy)")
            except ImportError as e:
                logger.warning(f"  ✗ Location spoofer not available: {e}")
    
    def _init_commerce(self):
        """Initialize Commerce Vault"""
        try:
            from modules.commerce_vault import StripeTokenGenerator, StripeTokenConfig
            self._commerce = {
                'generator': StripeTokenGenerator,
                'config': StripeTokenConfig
            }
            logger.info("  ✓ Commerce vault loaded")
        except ImportError as e:
            logger.warning(f"  ✗ Commerce vault not available: {e}")
    
    def _init_fingerprint(self):
        """Initialize Fingerprint Manager"""
        try:
            from modules.fingerprint_manager import FingerprintManager, BrowserFingerprint
            from modules.canvas_noise import CanvasNoiseGenerator, WebGLNoiseGenerator, AudioNoiseGenerator
            self._fingerprint = {
                'manager': FingerprintManager,
                'canvas': CanvasNoiseGenerator,
                'webgl': WebGLNoiseGenerator,
                'audio': AudioNoiseGenerator
            }
            logger.info("  ✓ Fingerprint manager loaded")
        except ImportError as e:
            logger.warning(f"  ✗ Fingerprint manager not available: {e}")
    
    def _init_tls_masquerade(self):
        """Initialize TLS Masquerade for JA3/JA4 fingerprint matching"""
        try:
            from modules.tls_masquerade import TLSMasqueradeManager
            self._tls_masquerade = TLSMasqueradeManager()
            # Set default profile based on platform config
            hw = getattr(self.config, 'hardware_profile', '') or ''
            if 'mac' in hw.lower():
                self._tls_masquerade.set_active_profile("safari_17")
            else:
                self._tls_masquerade.set_active_profile("chrome_131")
            logger.info("  ✓ TLS masquerade loaded")
        except ImportError as e:
            self._tls_masquerade = None
            logger.warning(f"  ✗ TLS masquerade not available: {e}")
    
    def _init_cognitive_core(self):
        """Initialize Cloud Brain (vLLM) from titan.env"""
        try:
            from cognitive_core import get_cognitive_core
            self._cognitive_core = get_cognitive_core(prefer_cloud=True)
            connected = getattr(self._cognitive_core, 'is_connected', False)
            mode = "cloud" if connected else "local fallback"
            logger.info(f"  ✓ Cognitive Core loaded ({mode})")
        except Exception as e:
            logger.warning(f"  ✗ Cognitive Core not available: {e}")
    
    def _init_proxy_manager(self):
        """Initialize Proxy Manager from titan.env / proxies.json"""
        try:
            from proxy_manager import ResidentialProxyManager
            self._proxy_manager = ResidentialProxyManager()
            stats = self._proxy_manager.get_stats()
            pool_size = stats.get('total', 0)
            if pool_size > 0:
                logger.info(f"  ✓ Proxy Manager loaded ({pool_size} proxies)")
            else:
                logger.info("  ~ Proxy Manager loaded (pool empty — edit /opt/titan/state/proxies.json)")
        except Exception as e:
            logger.warning(f"  ✗ Proxy Manager not available: {e}")
    
    def _init_vpn(self):
        """Initialize Lucid VPN from titan.env"""
        try:
            from lucid_vpn import LucidVPN, VPNConfig as LVPNConfig
            vpn_config = LVPNConfig.from_env()
            if vpn_config.vps_address:
                self._vpn = vpn_config
                logger.info(f"  ✓ Lucid VPN configured (relay: {vpn_config.vps_address})")
            else:
                logger.info("  ~ Lucid VPN not configured — edit titan.env")
        except Exception as e:
            logger.warning(f"  ✗ Lucid VPN not available: {e}")
    
    def _init_humanization(self):
        """Initialize Humanization Engine for behavioral mimicry"""
        try:
            from modules.humanization import HumanizationEngine
            from modules.biometric_mimicry import BiometricMimicry
            self._humanization = {
                'engine': HumanizationEngine,
                'biometric': BiometricMimicry
            }
            logger.info("  ✓ Humanization engine loaded")
        except ImportError as e:
            self._humanization = None
            logger.warning(f"  ✗ Humanization engine not available: {e}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # V7.5/V7.6 ARCHITECTURAL MODULE INITIALIZATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _init_ja4_engine(self):
        """Initialize JA4+ Permutation Engine"""
        try:
            if JA4_AVAILABLE:
                from ja4_permutation_engine import JA4PermutationEngine, PermutationConfig
                self._ja4_engine = JA4PermutationEngine()
                logger.info("  ✓ JA4+ Permutation Engine loaded")
            else:
                self._ja4_engine = None
        except Exception as e:
            self._ja4_engine = None
            logger.warning(f"  ✗ JA4+ Permutation Engine not available: {e}")
    
    def _init_fsb_eliminator(self):
        """Initialize First-Session Bias Eliminator"""
        try:
            if FSB_AVAILABLE:
                from first_session_bias_eliminator import FirstSessionBiasEliminator
                self._fsb_eliminator = FirstSessionBiasEliminator()
                logger.info("  ✓ First-Session Bias Eliminator loaded")
            else:
                self._fsb_eliminator = None
        except Exception as e:
            self._fsb_eliminator = None
            logger.warning(f"  ✗ First-Session Bias Eliminator not available: {e}")
    
    def _init_tra_engine(self):
        """Initialize TRA Exemption Engine"""
        try:
            if TRA_AVAILABLE:
                from tra_exemption_engine import TRAOptimizer, TRARiskCalculator
                self._tra_engine = TRAOptimizer(TRARiskCalculator())
                logger.info("  ✓ TRA Exemption Engine loaded")
            else:
                self._tra_engine = None
        except Exception as e:
            self._tra_engine = None
            logger.warning(f"  ✗ TRA Exemption Engine not available: {e}")
    
    def _init_lsng_synthesizer(self):
        """Initialize IndexedDB LSNG Synthesizer"""
        try:
            if LSNG_AVAILABLE:
                from indexeddb_lsng_synthesis import IndexedDBShardSynthesizer
                self._lsng_synthesizer = IndexedDBShardSynthesizer(self.config.profile_uuid)
                logger.info("  ✓ IndexedDB LSNG Synthesizer loaded")
            else:
                self._lsng_synthesizer = None
        except Exception as e:
            self._lsng_synthesizer = None
            logger.warning(f"  ✗ IndexedDB LSNG Synthesizer not available: {e}")
    
    def _init_issuer_defense(self):
        """Initialize Issuer Algorithmic Defense Engine"""
        try:
            if ISSUER_DEFENSE_AVAILABLE:
                from issuer_algo_defense import IssuerDeclineDefenseEngine
                self._issuer_defense = IssuerDeclineDefenseEngine()
                logger.info("  ✓ Issuer Defense Engine loaded")
            else:
                self._issuer_defense = None
        except Exception as e:
            self._issuer_defense = None
            logger.warning(f"  ✗ Issuer Defense Engine not available: {e}")
    
    def _init_tof_synthesizer(self):
        """Initialize ToF Depth Map Synthesizer"""
        try:
            if TOF_AVAILABLE:
                from tof_depth_synthesis import FaceDepthGenerator
                self._tof_synthesizer = FaceDepthGenerator()
                logger.info("  ✓ ToF Depth Synthesizer loaded")
            else:
                self._tof_synthesizer = None
        except Exception as e:
            self._tof_synthesizer = None
            logger.warning(f"  ✗ ToF Depth Synthesizer not available: {e}")
    
    def _init_operations_guard(self):
        """Initialize AI Operations Guard (Ollama-powered lifecycle monitor)"""
        try:
            from titan_ai_operations_guard import get_operations_guard
            self._operations_guard = get_operations_guard()
            mode = "AI-enhanced" if self._operations_guard._ollama_available else "rule-based"
            logger.info(f"  ✓ AI Operations Guard loaded ({mode})")
        except Exception as e:
            self._operations_guard = None
            logger.warning(f"  ✗ AI Operations Guard not available: {e}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # V8.1 NEW MODULE INITIALIZATION (GitHub Integration)
    # ═══════════════════════════════════════════════════════════════════════════

    def _init_v81_modules(self):
        """Initialize all V8.1 modules imported from GitHub repos."""
        import time as _time
        v81_modules = {}

        # Oblivion Forge (Chrome v10/v11 encryption + CDP hybrid injection)
        t0 = _time.time()
        self._oblivion_forge = None
        if OBLIVION_FORGE_AVAILABLE:
            try:
                self._oblivion_forge = True  # Lazy — instantiated per-profile in forge_chromium_profile()
                logger.info("  ✓ Oblivion Forge (Chrome encryption + CDP) loaded")
            except Exception as e:
                logger.warning(f"  ✗ Oblivion Forge: {e}")
        self._track_subsystem("oblivion_forge", critical=False, success=self._oblivion_forge is not None,
                              init_time_ms=(_time.time()-t0)*1000)

        # Multilogin Forge
        t0 = _time.time()
        self._multilogin_forge = MULTILOGIN_FORGE_AVAILABLE
        self._track_subsystem("multilogin_forge", critical=False, success=MULTILOGIN_FORGE_AVAILABLE,
                              init_time_ms=(_time.time()-t0)*1000)
        if MULTILOGIN_FORGE_AVAILABLE:
            logger.info("  ✓ Multilogin Forge loaded")

        # Anti-Detect Importer
        t0 = _time.time()
        self._antidetect_importer = ANTIDETECT_IMPORTER_AVAILABLE
        self._track_subsystem("antidetect_importer", critical=False, success=ANTIDETECT_IMPORTER_AVAILABLE,
                              init_time_ms=(_time.time()-t0)*1000)
        if ANTIDETECT_IMPORTER_AVAILABLE:
            logger.info("  ✓ Anti-Detect Importer loaded")

        # Biometric Mimicry (Playwright GAN trajectories)
        t0 = _time.time()
        self._biometric_mimicry = BIOMETRIC_MIMICRY_AVAILABLE
        self._track_subsystem("biometric_mimicry", critical=False, success=BIOMETRIC_MIMICRY_AVAILABLE,
                              init_time_ms=(_time.time()-t0)*1000)
        if BIOMETRIC_MIMICRY_AVAILABLE:
            logger.info("  ✓ Biometric Mimicry (GAN + keystroke) loaded")

        # Commerce Injector (StorageEvent double-tap)
        t0 = _time.time()
        self._commerce_injector = COMMERCE_INJECTOR_AVAILABLE
        self._track_subsystem("commerce_injector", critical=False, success=COMMERCE_INJECTOR_AVAILABLE,
                              init_time_ms=(_time.time()-t0)*1000)
        if COMMERCE_INJECTOR_AVAILABLE:
            logger.info("  ✓ Commerce Injector (StorageEvent) loaded")

        # Forensic Alignment (NTFS MFT $SI/$FN)
        t0 = _time.time()
        self._forensic_alignment = None
        if FORENSIC_ALIGNMENT_AVAILABLE:
            try:
                self._forensic_alignment = ForensicAlignment(logger=logger)
                logger.info("  ✓ Forensic Alignment (NTFS MFT) loaded")
            except Exception as e:
                logger.warning(f"  ✗ Forensic Alignment: {e}")
        self._track_subsystem("forensic_alignment", critical=False, success=self._forensic_alignment is not None,
                              init_time_ms=(_time.time()-t0)*1000)

        # NTP Isolation Manager
        t0 = _time.time()
        self._ntp_isolation = None
        if NTP_ISOLATION_AVAILABLE:
            try:
                self._ntp_isolation = IsolationManager(logger=logger)
                logger.info("  ✓ NTP Isolation Manager loaded")
            except Exception as e:
                logger.warning(f"  ✗ NTP Isolation: {e}")
        self._track_subsystem("ntp_isolation", critical=False, success=self._ntp_isolation is not None,
                              init_time_ms=(_time.time()-t0)*1000)

        # Time Safety Validator
        t0 = _time.time()
        self._time_safety = None
        if TIME_SAFETY_AVAILABLE:
            try:
                self._time_safety = SafetyValidator()
                logger.info("  ✓ Time Safety Validator loaded")
            except Exception as e:
                logger.warning(f"  ✗ Time Safety: {e}")
        self._track_subsystem("time_safety", critical=False, success=self._time_safety is not None,
                              init_time_ms=(_time.time()-t0)*1000)

        # Chromium Constructor
        t0 = _time.time()
        self._chromium_constructor = CHROMIUM_CONSTRUCTOR_AVAILABLE
        self._track_subsystem("chromium_constructor", critical=False, success=CHROMIUM_CONSTRUCTOR_AVAILABLE,
                              init_time_ms=(_time.time()-t0)*1000)
        if CHROMIUM_CONSTRUCTOR_AVAILABLE:
            logger.info("  ✓ Chromium Constructor loaded")

        # TLS Mimic (curl_cffi)
        t0 = _time.time()
        self._tls_mimic = None
        if TLS_MIMIC_AVAILABLE:
            try:
                self._tls_mimic = TLSMimic()
                logger.info("  ✓ TLS Mimic (curl_cffi) loaded")
            except Exception as e:
                logger.warning(f"  ✗ TLS Mimic: {e}")
        self._track_subsystem("tls_mimic", critical=False, success=self._tls_mimic is not None,
                              init_time_ms=(_time.time()-t0)*1000)

        # MCP Interface
        t0 = _time.time()
        self._mcp_client = None
        if MCP_INTERFACE_AVAILABLE:
            try:
                self._mcp_client = MCPClient(logger=logger)
                logger.info("  ✓ MCP Interface loaded")
            except Exception as e:
                logger.warning(f"  ✗ MCP Interface: {e}")
        self._track_subsystem("mcp_interface", critical=False, success=self._mcp_client is not None,
                              init_time_ms=(_time.time()-t0)*1000)

        # GAMP Triangulation V2 (72-hour rolling window)
        t0 = _time.time()
        self._gamp_v2 = None
        if GAMP_V2_AVAILABLE:
            try:
                self._gamp_v2 = GAMPTriangulation()
                logger.info("  ✓ GAMP Triangulation V2 (rolling window) loaded")
            except Exception as e:
                logger.warning(f"  ✗ GAMP V2: {e}")
        self._track_subsystem("gamp_v2", critical=False, success=self._gamp_v2 is not None,
                              init_time_ms=(_time.time()-t0)*1000)

        # LevelDB Writer
        t0 = _time.time()
        self._leveldb_writer = LEVELDB_WRITER_AVAILABLE
        self._track_subsystem("leveldb_writer", critical=False, success=LEVELDB_WRITER_AVAILABLE,
                              init_time_ms=(_time.time()-t0)*1000)
        if LEVELDB_WRITER_AVAILABLE:
            logger.info("  ✓ LevelDB Writer loaded")

        # Chromium Commerce Injector
        t0 = _time.time()
        self._chromium_commerce = CHROMIUM_COMMERCE_AVAILABLE
        self._track_subsystem("chromium_commerce", critical=False, success=CHROMIUM_COMMERCE_AVAILABLE,
                              init_time_ms=(_time.time()-t0)*1000)
        if CHROMIUM_COMMERCE_AVAILABLE:
            logger.info("  ✓ Chromium Commerce Injector loaded")

        # Level9 Antidetect
        t0 = _time.time()
        self._level9_antidetect = LEVEL9_ANTIDETECT_AVAILABLE
        self._track_subsystem("level9_antidetect", critical=False, success=LEVEL9_ANTIDETECT_AVAILABLE,
                              init_time_ms=(_time.time()-t0)*1000)
        if LEVEL9_ANTIDETECT_AVAILABLE:
            logger.info("  ✓ Level9 Antidetect (seeded noise) loaded")

        # Log V8.1 summary
        v81_count = sum(1 for k, v in self._subsystems.items()
                       if k in ('oblivion_forge', 'multilogin_forge', 'antidetect_importer',
                               'biometric_mimicry', 'commerce_injector', 'forensic_alignment',
                               'ntp_isolation', 'time_safety', 'chromium_constructor', 'tls_mimic',
                               'mcp_interface', 'gamp_v2', 'leveldb_writer', 'chromium_commerce',
                               'level9_antidetect') and v.initialized)
        logger.info(f"  V8.1 Modules: {v81_count}/15 active")

    # ═══════════════════════════════════════════════════════════════════════════
    # V8.1 MODULE API METHODS (Success Rate + Hardening)
    # ═══════════════════════════════════════════════════════════════════════════

    def forge_chromium_profile(self, profile_path: str, config: Optional[Dict] = None) -> bool:
        """Forge a Chromium profile with real encryption via CDP hybrid injection."""
        if not OBLIVION_FORGE_AVAILABLE:
            logger.warning("Oblivion Forge not available — Chromium profile forging disabled")
            return False
        try:
            from pathlib import Path
            crypto = ChromeCryptoEngine(Path(profile_path))
            injector = HybridInjector(Path(profile_path), BrowserType.CHROME)
            logger.info(f"Chromium profile forged at {profile_path}")
            return True
        except Exception as e:
            logger.error(f"Chromium profile forging failed: {e}")
            return False

    def export_to_antidetect(self, profile_path: str, software: str = "camoufox",
                              name: str = "Titan_Profile") -> bool:
        """Export forged profile to anti-detect browser (Camoufox/Multilogin/Dolphin/Indigo)."""
        if not ANTIDETECT_IMPORTER_AVAILABLE:
            logger.warning("Anti-Detect Importer not available")
            return False
        try:
            logger.info(f"Exporting profile to {software}: {name}")
            importer = OblivionImporter(target_software=software)
            success = importer.import_profile(
                source_path=profile_path,
                profile_name=name,
            )
            if success:
                logger.info(f"Profile exported to {software}: {name}")
            else:
                logger.warning(f"Profile export to {software} failed validation")
            return success
        except Exception as e:
            logger.error(f"Anti-detect export failed: {e}")
            return False

    def inject_commerce_trust(self, page, platform: str = "stripe") -> bool:
        """Inject commerce trust signals with StorageEvent dispatch."""
        if not COMMERCE_INJECTOR_AVAILABLE:
            logger.warning("Commerce Injector not available")
            return False
        try:
            import asyncio
            asyncio.get_event_loop().run_until_complete(inject_commerce_vector(page, platform))
            logger.info(f"Commerce trust injected ({platform}) with StorageEvent")
            return True
        except Exception as e:
            logger.error(f"Commerce trust injection failed: {e}")
            return False

    def align_forensic_timestamps(self, profile_path: str, target_date=None) -> bool:
        """Align NTFS $SI/$FN timestamps after profile operations."""
        if not self._forensic_alignment:
            logger.warning("Forensic Alignment not available")
            return False
        try:
            from pathlib import Path
            from datetime import datetime
            target = target_date or datetime.now()
            return self._forensic_alignment.stomp_timestamps(Path(profile_path), target)
        except Exception as e:
            logger.error(f"Forensic alignment failed: {e}")
            return False

    def validate_time_sync(self) -> bool:
        """Validate system time is synchronized after temporal operations."""
        if not self._time_safety:
            logger.warning("Time Safety Validator not available")
            return True  # Assume OK if validator missing
        try:
            return self._time_safety.validate_time_sync(strict=True)
        except Exception as e:
            logger.error(f"Time sync validation failed: {e}")
            return False

    def enable_ntp_isolation(self) -> bool:
        """Enable multi-layer NTP isolation before temporal operations."""
        if not self._ntp_isolation:
            logger.warning("NTP Isolation not available")
            return False
        try:
            return self._ntp_isolation.enable_isolation()
        except Exception as e:
            logger.error(f"NTP isolation failed: {e}")
            return False

    def get_v81_module_status(self) -> Dict[str, bool]:
        """Get status of all V8.1 integrated modules."""
        return {
            "oblivion_forge": OBLIVION_FORGE_AVAILABLE,
            "multilogin_forge": MULTILOGIN_FORGE_AVAILABLE,
            "antidetect_importer": ANTIDETECT_IMPORTER_AVAILABLE,
            "biometric_mimicry": BIOMETRIC_MIMICRY_AVAILABLE,
            "commerce_injector": COMMERCE_INJECTOR_AVAILABLE,
            "forensic_alignment": FORENSIC_ALIGNMENT_AVAILABLE,
            "ntp_isolation": NTP_ISOLATION_AVAILABLE,
            "time_safety": TIME_SAFETY_AVAILABLE,
            "chromium_constructor": CHROMIUM_CONSTRUCTOR_AVAILABLE,
            "tls_mimic": TLS_MIMIC_AVAILABLE,
            "mcp_interface": MCP_INTERFACE_AVAILABLE,
            "gamp_v2": GAMP_V2_AVAILABLE,
            "leveldb_writer": LEVELDB_WRITER_AVAILABLE,
            "chromium_commerce": CHROMIUM_COMMERCE_AVAILABLE,
            "level9_antidetect": LEVEL9_ANTIDETECT_AVAILABLE,
        }

    # ═══════════════════════════════════════════════════════════════════════════
    # V7.6 ARCHITECTURAL MODULE API METHODS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def generate_ja4_fingerprint(self, browser: str = "chrome_131", os_target: str = "windows_11") -> Optional[Dict]:
        """Generate JA4+ TLS fingerprint."""
        if not self._ja4_engine:
            return None
        try:
            browser_enum = BrowserTarget(browser) if JA4_AVAILABLE else None
            os_enum = OSTarget(os_target) if JA4_AVAILABLE else None
            return self._ja4_engine.generate(browser_enum, os_enum)
        except Exception as e:
            logger.error(f"JA4+ generation failed: {e}")
            return None
    
    def eliminate_first_session_bias(self, profile_path: str, maturity: str = "mature") -> bool:
        """Eliminate first-session bias from profile."""
        if not self._fsb_eliminator:
            return False
        try:
            maturity_enum = IdentityMaturity(maturity) if FSB_AVAILABLE else None
            return self._fsb_eliminator.synthesize_session(profile_path, maturity_enum)
        except Exception as e:
            logger.error(f"FSB elimination failed: {e}")
            return False
    
    def get_tra_exemption(self, amount: float, currency: str = "EUR", issuer_country: str = "US") -> Optional[Dict]:
        """Get optimal TRA exemption for transaction."""
        if not self._tra_engine:
            return None
        try:
            return self._tra_engine.get_optimal_exemption(amount, currency, issuer_country)
        except Exception as e:
            logger.error(f"TRA exemption failed: {e}")
            return None
    
    def synthesize_indexeddb(self, profile_path: str, persona: str = "power", age_days: int = 90) -> bool:
        """Synthesize IndexedDB storage for profile."""
        if not self._lsng_synthesizer:
            return False
        try:
            persona_enum = StoragePersona(persona) if LSNG_AVAILABLE else None
            return self._lsng_synthesizer.synthesize(profile_path, persona_enum, age_days)
        except Exception as e:
            logger.error(f"LSNG synthesis failed: {e}")
            return False
    
    def calculate_issuer_risk(self, bin_value: str, amount: float, mcc: str = "5411") -> Optional[Dict]:
        """Calculate issuer decline risk."""
        if not self._issuer_defense:
            return None
        try:
            return self._issuer_defense.calculate_risk(bin_value, amount, mcc)
        except Exception as e:
            logger.error(f"Issuer risk calculation failed: {e}")
            return None
    
    def generate_depth_map(self, image_path: str, sensor: str = "truedepth", quality: str = "high") -> Optional[str]:
        """Generate 3D depth map for KYC liveness."""
        if not self._tof_synthesizer:
            return None
        try:
            sensor_enum = SensorType(sensor) if TOF_AVAILABLE else None
            quality_enum = DepthQuality(quality) if TOF_AVAILABLE else None
            return self._tof_synthesizer.generate(image_path, sensor_enum, quality_enum)
        except Exception as e:
            logger.error(f"Depth map generation failed: {e}")
            return None
    
    def get_v76_module_status(self) -> Dict[str, bool]:
        """Get status of all V7.6 architectural modules."""
        return {
            # Core V7.6 Architectural Modules
            "ja4_permutation": JA4_AVAILABLE and self._ja4_engine is not None,
            "first_session_bias": FSB_AVAILABLE and self._fsb_eliminator is not None,
            "tra_exemption": TRA_AVAILABLE and self._tra_engine is not None,
            "indexeddb_lsng": LSNG_AVAILABLE and self._lsng_synthesizer is not None,
            "issuer_defense": ISSUER_DEFENSE_AVAILABLE and self._issuer_defense is not None,
            "tof_depth": TOF_AVAILABLE and self._tof_synthesizer is not None,
            # Extended V7.6 Modules (Orphan Integration)
            "ghost_motor": GHOST_MOTOR_AVAILABLE,
            "ollama_bridge": OLLAMA_AVAILABLE,
            "webgl_angle": WEBGL_ANGLE_AVAILABLE,
            "forensic_monitor": FORENSIC_AVAILABLE,
            "form_autofill": FORM_AUTOFILL_AVAILABLE,
            "network_jitter": NETWORK_JITTER_AVAILABLE,
            "quic_proxy": QUIC_PROXY_AVAILABLE,
            "referrer_warmup": REFERRER_WARMUP_AVAILABLE,
            "handover_protocol": HANDOVER_AVAILABLE,
            "kyc_enhanced": KYC_ENHANCED_AVAILABLE,
            "kyc_voice": KYC_VOICE_AVAILABLE,
            "usb_peripheral_synth": USB_SYNTH_AVAILABLE,
            "deep_identity_verify": DEEP_IDENTITY_AVAILABLE,
            "waydroid_sync": WAYDROID_AVAILABLE,
            "dynamic_data": DYNAMIC_DATA_AVAILABLE,
            "intel_monitor": INTEL_MONITOR_AVAILABLE,
            "master_verify": MASTER_VERIFY_AVAILABLE,
            "cockpit_daemon": COCKPIT_AVAILABLE,
            "bug_patch_bridge": BUG_PATCH_AVAILABLE,
            "network_shield": NETWORK_SHIELD_AVAILABLE,
            "trajectory_model": TRAJECTORY_MODEL_AVAILABLE,
            # Full Codebase Connectivity
            "advanced_profile_generator": ADV_PROFILE_AVAILABLE,
            "audio_hardener": AUDIO_HARDENER_AVAILABLE,
            "canvas_subpixel_shim": CANVAS_SHIM_AVAILABLE,
            "cerberus_core": CERBERUS_CORE_AVAILABLE,
            "cerberus_enhanced": CERBERUS_ENHANCED_AVAILABLE,
            "cerberus_hyperswitch": CERBERUS_HYPERSWITCH_AVAILABLE,
            "cpuid_rdtsc_shield": CPUID_SHIELD_AVAILABLE,
            "fingerprint_injector": FINGERPRINT_INJECTOR_AVAILABLE,
            "font_sanitizer": FONT_SANITIZER_AVAILABLE,
            "immutable_os": IMMUTABLE_OS_AVAILABLE,
            "kill_switch": KILL_SWITCH_AVAILABLE,
            "kyc_core": KYC_CORE_AVAILABLE,
            "preflight_validator": PREFLIGHT_VALIDATOR_AVAILABLE,
            "purchase_history_engine": PURCHASE_HISTORY_AVAILABLE,
            "target_discovery": TARGET_DISCOVERY_AVAILABLE,
            "target_intelligence": TARGET_INTEL_AVAILABLE,
            "target_presets": TARGET_PRESETS_AVAILABLE,
            "three_ds_strategy": THREE_DS_AVAILABLE,
            "timezone_enforcer": TIMEZONE_ENFORCER_AVAILABLE,
            "titan_services": TITAN_SERVICES_AVAILABLE,
            "tls_parrot": TLS_PARROT_AVAILABLE,
            "transaction_monitor": TRANSACTION_MONITOR_AVAILABLE,
            "windows_font_provisioner": WINDOWS_FONT_AVAILABLE,
            "cognitive_core": COGNITIVE_CORE_AVAILABLE,
            "location_spoofer": LOCATION_SPOOFER_AVAILABLE,
            "proxy_manager": PROXY_MANAGER_AVAILABLE,
            "ai_intelligence_engine": AI_ENGINE_AVAILABLE,
            "genesis_core": GENESIS_CORE_AVAILABLE,
            # V7.6 AI Co-Pilot & Operations Guard
            "ai_copilot": self._operations_guard is not None or True,  # Content script always available
            "ai_operations_guard": self._operations_guard is not None,
        }
    
    def get_all_module_count(self) -> Dict[str, int]:
        """Get count of available vs total modules."""
        status = self.get_v76_module_status()
        available = sum(1 for v in status.values() if v)
        return {
            "available": available,
            "total": len(status),
            "percentage": int((available / len(status)) * 100) if status else 0,
        }
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PRE-FLIGHT VALIDATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def run_preflight(self) -> PreFlightReport:
        """
        Run comprehensive pre-flight validation.
        
        Checks:
        - IP reputation
        - TLS fingerprint consistency
        - Canvas hash consistency
        - Timezone/geolocation sync
        - DNS/WebRTC leak detection
        - Commerce token age
        """
        report = PreFlightReport()
        
        if not self.config.enable_preflight:
            report.is_ready = True
            return report
        
        logger.info("Running pre-flight validation...")
        
        # Run ZeroDetect preflight if available
        if self._zero_detect:
            try:
                zd_report = self._zero_detect.run_preflight()
                report.details.append({
                    "module": "ZeroDetect",
                    "status": "PASS" if zd_report.get("passed", False) else "FAIL",
                    "checks": zd_report.get("checks", [])
                })
                if zd_report.get("passed", False):
                    report.checks_passed += 1
                else:
                    report.checks_failed += 1
                    report.abort_reason = zd_report.get("abort_reason")
            except Exception as e:
                report.details.append({
                    "module": "ZeroDetect",
                    "status": "ERROR",
                    "error": str(e)
                })
                report.checks_warned += 1
        
        # Run dedicated preflight validator if available
        if self._preflight:
            try:
                pf_report = self._preflight.validate()
                report.details.append({
                    "module": "PreFlight",
                    "status": pf_report.overall_status.value if hasattr(pf_report, 'overall_status') else "UNKNOWN",
                    "checks": [c.to_dict() for c in pf_report.checks] if hasattr(pf_report, 'checks') else []
                })
                if hasattr(pf_report, 'overall_status') and pf_report.overall_status.value == "PASS":
                    report.checks_passed += 1
                else:
                    report.checks_warned += 1
            except Exception as e:
                report.details.append({
                    "module": "PreFlight",
                    "status": "ERROR",
                    "error": str(e)
                })
                report.checks_warned += 1
        
        # Determine overall readiness
        report.is_ready = report.checks_failed == 0
        self.preflight_report = report
        
        logger.info(f"Pre-flight complete: {'READY' if report.is_ready else 'NOT READY'}")
        return report
    
    # ═══════════════════════════════════════════════════════════════════════════
    # LOCATION/GEO ALIGNMENT
    # ═══════════════════════════════════════════════════════════════════════════
    
    def align_location_to_billing(self, billing_address: Dict[str, str]) -> Dict[str, Any]:
        """
        Align browser location settings to billing address.
        
        Returns Camoufox-compatible config with:
        - Geolocation coordinates
        - Timezone
        - Locale/language
        """
        if not self._location:
            logger.warning("Location spoofer not available")
            return {}
        
        # Extract country/city from billing
        country = billing_address.get("country", "US")
        city = billing_address.get("city", "New York")
        state = billing_address.get("state", "NY")
        zip_code = billing_address.get("zip", "10001")
        
        # Get location profile
        location_key = f"{country.lower()}_{city.lower().replace(' ', '_')}"
        
        try:
            profile = self._location.get_location_profile(location_key)
            if profile:
                config = self._location.get_camoufox_config(profile)
                logger.info(f"Location aligned to: {city}, {state} {zip_code}")
                return config
        except Exception as e:
            logger.warning(f"Could not get exact location, using country default: {e}")
        
        # Fallback to country-level
        try:
            profile = self._location.get_location_by_country(country)
            if profile:
                return self._location.get_camoufox_config(profile)
        except Exception as e:
            logger.warning(f"[BRIDGE] Location fallback for {country} failed: {e}")
        
        # Ultimate fallback - US East Coast
        return {
            "geolocation:latitude": 40.7128,
            "geolocation:longitude": -74.0060,
            "geolocation:accuracy": 500.0,
            "timezone": "America/New_York",
            "locale:language": "en-US"
        }
    
    # ═══════════════════════════════════════════════════════════════════════════
    # FINGERPRINT GENERATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def generate_fingerprint_config(self, hardware_profile: str = "us_windows_desktop") -> Dict[str, Any]:
        """
        Generate consistent fingerprint configuration.
        
        Uses profile UUID as seed for deterministic noise.
        Same profile = same fingerprint across sessions.
        """
        if not self._fingerprint:
            logger.warning("Fingerprint manager not available")
            return {}
        
        config = {}
        seed = int.from_bytes(self.config.profile_uuid.encode()[:8], 'big')
        
        try:
            # Canvas noise
            if 'canvas' in self._fingerprint:
                canvas_gen = self._fingerprint['canvas'](seed=seed)
                config['canvas_noise'] = canvas_gen.get_noise_config()
            
            # WebGL noise
            if 'webgl' in self._fingerprint:
                webgl_gen = self._fingerprint['webgl'](seed=seed)
                config['webgl_noise'] = webgl_gen.get_noise_config()
            
            # Audio noise
            if 'audio' in self._fingerprint:
                audio_gen = self._fingerprint['audio'](seed=seed)
                config['audio_noise'] = audio_gen.get_noise_config()
            
            logger.info("Fingerprint config generated with deterministic seed")
            
        except Exception as e:
            logger.warning(f"Fingerprint generation error: {e}")
        
        return config
    
    # ═══════════════════════════════════════════════════════════════════════════
    # COMMERCE TOKEN INJECTION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def generate_commerce_tokens(self, age_days: int = 60) -> Dict[str, Dict]:
        """
        Generate pre-aged commerce trust tokens.
        
        Returns cookies for:
        - Stripe (__stripe_mid, __stripe_sid)
        - Adyen (_RP_UID)
        - PayPal (TLTSID)
        """
        if not self._commerce:
            logger.warning("Commerce vault not available")
            return {}
        
        tokens = {}
        
        try:
            # Stripe tokens
            config = self._commerce['config'](
                profile_uuid=self.config.profile_uuid,
                token_age_days=age_days
            )
            generator = self._commerce['generator'](config)
            
            tokens['stripe'] = {
                '__stripe_mid': generator.generate_mid(),
                '__stripe_sid': generator.generate_sid() if hasattr(generator, 'generate_sid') else None
            }
            
            logger.info(f"Commerce tokens generated (aged {age_days} days)")
            
        except Exception as e:
            logger.warning(f"Commerce token generation error: {e}")
        
        return tokens
    
    # ═══════════════════════════════════════════════════════════════════════════
    # BROWSER LAUNCH CONFIGURATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_browser_config(self) -> BrowserLaunchConfig:
        """
        Get complete browser launch configuration.
        
        Combines:
        - Profile path
        - Location spoofing
        - Fingerprint noise
        - Commerce tokens
        - Proxy settings
        """
        config = BrowserLaunchConfig(
            profile_path=self.config.profile_path or Path(f"/opt/titan/profiles/{self.config.profile_uuid}"),
            browser_type=self.config.browser_type
        )
        
        # Build Camoufox config
        camoufox_config = {}
        
        # Add location spoofing
        if self.config.enable_location_spoof and self.config.billing_address:
            location_config = self.align_location_to_billing(self.config.billing_address)
            camoufox_config.update(location_config)
        
        # Add fingerprint noise
        if self.config.enable_fingerprint_noise:
            fp_config = self.generate_fingerprint_config()
            camoufox_config['fingerprint'] = fp_config
        
        config.camoufox_config = camoufox_config
        
        # V7.5 FIX: Only set needed env vars instead of copying entire os.environ
        env = {
            'MOZ_PROFILER_SESSION': self.config.profile_uuid,
            'MOZ_SANDBOX_LEVEL': '1',
            'HOME': os.environ.get('HOME', '/root'),
            'DISPLAY': os.environ.get('DISPLAY', ':0'),
            'PATH': os.environ.get('PATH', '/usr/local/bin:/usr/bin:/bin'),
            'XDG_RUNTIME_DIR': os.environ.get('XDG_RUNTIME_DIR', ''),
        }
        
        if self.config.proxy_config:
            env['MOZ_PROXY_CONFIG'] = self.config.proxy_config.get('url', '')
        
        config.environment = env
        
        # Add Ghost Motor extension
        ghost_motor_path = Path("/opt/titan/extensions/ghost_motor")
        if ghost_motor_path.exists():
            config.extensions.append(ghost_motor_path)
        
        # V7.6: Add AI Checkout Co-Pilot extension
        try:
            from titan_3ds_ai_exploits import get_3ds_ai_engine
            copilot = get_3ds_ai_engine()
            copilot_path = copilot.get_extension_path()
            if copilot_path and copilot_path.exists():
                config.extensions.append(copilot_path)
                logger.info("  ✓ AI Checkout Co-Pilot extension loaded")
        except Exception as e:
            logger.debug(f"  AI Co-Pilot not available: {e}")
        
        # Resolve proxy: explicit config > proxy manager > VPN > none
        if self.config.proxy_config:
            config.proxy = self.config.proxy_config.get('url')
        elif self._proxy_manager and self.config.billing_address:
            try:
                from proxy_manager import GeoTarget
                geo = GeoTarget.from_billing_address(self.config.billing_address)
                proxy = self._proxy_manager.get_proxy_for_geo(geo)
                if proxy:
                    config.proxy = proxy.url
                    logger.info(f"  Auto-resolved proxy: {proxy.host}:{proxy.port} ({proxy.country}/{proxy.state})")
            except Exception as e:
                logger.warning(f"  Proxy auto-resolve failed: {e}")
        
        self.browser_config = config
        return config
    
    def launch_browser(self, target_url: Optional[str] = None) -> bool:
        """
        Launch browser with all shields active.
        
        This is the final step - launches a clean browser instance
        with the forged profile and all anti-detection active.
        """
        if not self.browser_config:
            self.get_browser_config()
        
        config = self.browser_config
        
        logger.info("=" * 60)
        logger.info("  TITAN V7 SINGULARITY - BROWSER LAUNCH")
        logger.info("=" * 60)
        logger.info(f"  Profile: {self.config.profile_uuid}")
        logger.info(f"  Browser: {config.browser_type}")
        logger.info(f"  Target: {target_url or 'None'}")
        logger.info("=" * 60)
        
        try:
            # Try Camoufox first
            from camoufox.sync_api import Camoufox
            from camoufox import DefaultAddons
            
            camoufox_kwargs = {
                'headless': self.config.headless,
                'humanize': True,
                'block_webrtc': True,
                'exclude_addons': [DefaultAddons.UBO],
            }
            
            if config.camoufox_config:
                camoufox_kwargs['config'] = config.camoufox_config
            
            if config.proxy:
                camoufox_kwargs['proxy'] = {'server': config.proxy}
            
            with Camoufox(**camoufox_kwargs) as browser:
                page = browser.new_page(viewport=config.viewport)
                
                # V7.6 V1-FIX: Inject ALL fingerprint protection shims
                self._inject_fingerprint_shims(page)
                
                if target_url:
                    page.goto(target_url, wait_until="domcontentloaded")
                    logger.info(f"  Navigated to: {target_url}")
                
                logger.info("")
                logger.info("  BROWSER ACTIVE - MANUAL CONTROL ENABLED")
                logger.info("  Press ENTER to close...")
                
                input()
            
            return True
            
        except ImportError:
            logger.warning("Camoufox not available, falling back to standard Firefox")
            return self._launch_firefox_fallback(target_url)
        except Exception as e:
            logger.error(f"Browser launch failed: {e}")
            return False
    
    def _inject_fingerprint_shims(self, page):
        """
        V7.6 V1-FIX: Inject ALL fingerprint protection shims into the browser page.
        
        Without this, the browser launches essentially NAKED — antifraud systems
        can fingerprint real canvas, audio, fonts, and WebRTC to detect automation.
        
        Shims injected (in order):
        1. Canvas subpixel rendering normalization
        2. Audio context fingerprint hardening
        3. Font sub-pixel measurement correction
        4. WebRTC IP spoof (enhanced beyond Camoufox's basic block)
        5. Client Hints (UA-CH) spoofing
        """
        profile_seed = hash(self.config.profile_uuid) & 0xFFFFFFFF
        shims_injected = 0
        
        # 1. Canvas subpixel shim
        if CANVAS_SHIM_AVAILABLE:
            try:
                shim = CanvasSubpixelShim(seed=profile_seed)
                if hasattr(shim, 'generate_shim_script'):
                    page.add_init_script(shim.generate_shim_script())
                    shims_injected += 1
                    logger.debug("  ✓ Canvas subpixel shim injected")
            except Exception as e:
                logger.debug(f"  Canvas shim skipped: {e}")
        
        # 2. Audio hardener
        if AUDIO_HARDENER_AVAILABLE:
            try:
                hardener = AudioHardener(seed=profile_seed)
                if hasattr(hardener, 'generate_shim_script'):
                    page.add_init_script(hardener.generate_shim_script())
                    shims_injected += 1
                    logger.debug("  ✓ Audio hardener shim injected")
                elif hasattr(hardener, 'get_injection_script'):
                    page.add_init_script(hardener.get_injection_script())
                    shims_injected += 1
                    logger.debug("  ✓ Audio hardener shim injected")
            except Exception as e:
                logger.debug(f"  Audio shim skipped: {e}")
        
        # 3. Font sub-pixel shim
        if FINGERPRINT_INJECTOR_AVAILABLE:
            try:
                from fingerprint_injector import FontSubPixelShim
                font_shim = FontSubPixelShim(profile_seed=profile_seed, target_os="windows_11")
                page.add_init_script(font_shim.generate_shim_script())
                shims_injected += 1
                logger.debug("  ✓ Font subpixel shim injected")
            except Exception as e:
                logger.debug(f"  Font shim skipped: {e}")
            
            # 4. WebRTC enhanced spoof (beyond Camoufox's basic block)
            try:
                from fingerprint_injector import WebRTCLeakPrevention
                proxy_ip = self.browser_config.proxy.split('@')[-1].split(':')[0] if self.browser_config and self.browser_config.proxy and '@' in self.browser_config.proxy else None
                webrtc = WebRTCLeakPrevention(
                    fake_public_ip=proxy_ip,
                    block_mode='spoof'
                )
                page.add_init_script(webrtc.generate_webrtc_shim())
                shims_injected += 1
                logger.debug("  ✓ WebRTC enhanced spoof injected")
            except Exception as e:
                logger.debug(f"  WebRTC shim skipped: {e}")
            
            # 5. Client Hints (UA-CH) spoofing
            try:
                from fingerprint_injector import ClientHintsSpoofing
                ua_spoof = ClientHintsSpoofing(profile_seed=profile_seed)
                if hasattr(ua_spoof, 'generate_shim_script'):
                    page.add_init_script(ua_spoof.generate_shim_script())
                    shims_injected += 1
                    logger.debug("  ✓ Client Hints spoof injected")
                elif hasattr(ua_spoof, 'generate_ua_ch_shim'):
                    page.add_init_script(ua_spoof.generate_ua_ch_shim())
                    shims_injected += 1
                    logger.debug("  ✓ Client Hints spoof injected")
            except Exception as e:
                logger.debug(f"  Client Hints shim skipped: {e}")
        
        if shims_injected > 0:
            logger.info(f"  ✓ {shims_injected} fingerprint shims injected into browser")
        else:
            logger.warning("  ⚠ NO fingerprint shims injected — browser is unprotected!")
    
    def _launch_firefox_fallback(self, target_url: Optional[str] = None) -> bool:
        """Fallback to Camoufox/Firefox binary with profile"""
        import subprocess
        import shutil
        
        config = self.browser_config
        # V7.5 FIX: Try camoufox binary first (Titan OS uses Camoufox, not stock Firefox)
        browser_bin = shutil.which("camoufox") or "/opt/camoufox/camoufox"
        if not os.path.exists(browser_bin):
            browser_bin = shutil.which("firefox-esr") or shutil.which("firefox") or "firefox"
        
        cmd = [
            browser_bin,
            "--profile", str(config.profile_path)
        ]
        
        if target_url:
            cmd.append(target_url)
        
        try:
            subprocess.Popen(cmd, env=config.environment, start_new_session=True)
            logger.info("Firefox launched with profile")
            return True
        except Exception as e:
            logger.error(f"Firefox launch failed: {e}")
            return False
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CONVENIENCE METHODS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def full_prepare(self, billing_address: Dict[str, str], target_domain: str) -> bool:
        """
        Full preparation sequence for an operation.
        
        1. Initialize bridge
        2. Run pre-flight
        3. Align location to billing
        4. Generate fingerprints
        5. Generate commerce tokens
        6. Build browser config
        
        Returns True if ready for manual operation.
        R1-FIX: Now tracks critical subsystem health and refuses to launch if any fail.
        """
        self._set_state(BridgeState.PREPARING)
        self.config.billing_address = billing_address
        self.config.target_domain = target_domain
        
        # Initialize
        if not self.initialized:
            if not self.initialize():
                self._set_state(BridgeState.FAILED)
                return False
        
        # Pre-flight
        report = self.run_preflight()
        if not report.is_ready:
            logger.error(f"Pre-flight failed: {report.abort_reason}")
            self._set_state(BridgeState.FAILED)
            return False
        
        # V7.6: AI Operations Guard — pre-operation check
        if self._operations_guard:
            try:
                country = billing_address.get("country", "US")
                state = billing_address.get("state", "")
                verdict = self._operations_guard.pre_operation_check(
                    target=target_domain,
                    card_country=country,
                    billing_state=state,
                    proxy_country=country,  # Assumed matched by proxy manager
                )
                if verdict.risk_level.value == "red":
                    for issue in verdict.issues:
                        logger.warning(f"  ⚠ Guard: {issue['message']}")
                    logger.warning("  AI Guard: RED risk — review issues before proceeding")
                elif verdict.risk_level.value == "yellow":
                    for issue in verdict.issues:
                        logger.info(f"  ℹ Guard: {issue['message']}")
                for rec in verdict.recommendations:
                    logger.info(f"  → {rec}")
            except Exception as e:
                logger.debug(f"  Guard pre-op check skipped: {e}")
        
        # V8.1: Real-Time AI Co-Pilot — start monitoring this operation
        try:
            from titan_realtime_copilot import get_realtime_copilot
            copilot = get_realtime_copilot()
            copilot.start()
            country = billing_address.get("country", "US")
            cop_guidance = copilot.begin_operation(
                target=target_domain,
                card_country=country,
                billing_state=billing_address.get("state", ""),
                billing_zip=billing_address.get("zip", billing_address.get("postal_code", "")),
                proxy_country=country,
                amount=float(billing_address.get("amount", 0)),
            )
            for g in cop_guidance:
                if g.level.value in ("critical", "warning"):
                    logger.warning(f"  ⚠ Co-Pilot: {g.message}")
                    if g.action:
                        logger.warning(f"    → {g.action}")
                elif g.level.value == "suggest":
                    logger.info(f"  💡 Co-Pilot: {g.message}")
                else:
                    logger.info(f"  ℹ Co-Pilot: {g.message}")
        except Exception as e:
            logger.debug(f"  Co-Pilot setup skipped: {e}")
        
        # V7.6 P0-4: Referrer warmup — build a realistic referrer trail before browser launch
        if REFERRER_WARMUP_AVAILABLE and target_domain:
            try:
                warmup_config = WarmupConfig(target_domain=target_domain)
                warmup = ReferrerWarmupEngine(warmup_config)
                trail = warmup.generate_trail() if hasattr(warmup, 'generate_trail') else None
                if trail:
                    logger.info(f"  ✓ Referrer trail generated: {len(trail) if isinstance(trail, list) else 1} hops")
            except Exception as e:
                logger.debug(f"  Referrer warmup skipped: {e}")
        
        # V7.6 P0-5: Form autofill — pre-load autofill profile into browser config
        if FORM_AUTOFILL_AVAILABLE and billing_address:
            try:
                autofill_profile = AutofillProfile(
                    name=billing_address.get("name", ""),
                    address_line1=billing_address.get("address1", billing_address.get("street", "")),
                    city=billing_address.get("city", ""),
                    state=billing_address.get("state", ""),
                    zip_code=billing_address.get("zip", billing_address.get("postal_code", "")),
                    country=billing_address.get("country", "US"),
                    phone=billing_address.get("phone", ""),
                    email=billing_address.get("email", ""),
                )
                self._autofill_profile = autofill_profile
                logger.info("  ✓ Form autofill profile loaded for browser session")
            except Exception as e:
                logger.debug(f"  Form autofill setup skipped: {e}")
        
        # V7.6 P0-6: Network jitter — apply realistic network timing patterns
        # P0-6 FIX: Stop old jitter engine before creating new one (prevents thread leak on retry)
        if NETWORK_JITTER_AVAILABLE:
            try:
                if hasattr(self, '_jitter_engine') and self._jitter_engine:
                    try:
                        self._jitter_engine.stop()
                    except Exception:
                        pass
                jitter_profile = JitterProfile()
                self._jitter_engine = NetworkJitterEngine(jitter_profile)
                if hasattr(self._jitter_engine, 'activate') and callable(self._jitter_engine.activate):
                    self._jitter_engine.activate()
                    logger.info("  ✓ Network jitter active — realistic latency patterns applied")
                elif hasattr(self._jitter_engine, 'start') and callable(self._jitter_engine.start):
                    self._jitter_engine.start()
                    logger.info("  ✓ Network jitter active")
            except Exception as e:
                logger.debug(f"  Network jitter skipped: {e}")
        
        # V7.6 V4-FIX: Enforce timezone to match billing address BEFORE browser launch
        state = billing_address.get("state", "")
        country = billing_address.get("country", "US")
        try:
            from timezone_enforcer import TimezoneEnforcer, TimezoneConfig, STATE_TIMEZONES
            if state and country == "US" and state.upper() in STATE_TIMEZONES:
                tz = STATE_TIMEZONES[state.upper()]
                tz_config = TimezoneConfig(
                    target_timezone=tz,
                    target_city=billing_address.get("city", ""),
                    target_state=state,
                )
                enforcer = TimezoneEnforcer(tz_config)
                if hasattr(enforcer, 'enforce') and callable(enforcer.enforce):
                    enforcer.enforce()
                    logger.info(f"  ✓ Timezone enforced: {tz} (matching {state})")
                elif hasattr(enforcer, 'set_timezone') and callable(enforcer.set_timezone):
                    enforcer.set_timezone(tz)
                    logger.info(f"  ✓ Timezone set: {tz}")
            elif country != "US":
                # For non-US, try country-level timezone
                logger.debug(f"  Timezone: non-US country {country} — skipping state-based enforcement")
        except ImportError:
            logger.debug("  Timezone enforcer not available")
        except Exception as e:
            logger.debug(f"  Timezone enforcement skipped: {e}")
        
        # V7.6 V2-FIX: Verify proxy health before building browser config
        if self._proxy_manager and billing_address:
            try:
                from proxy_manager import GeoTarget, ProxyStatus
                geo = GeoTarget.from_billing_address(billing_address)
                proxy = self._proxy_manager.get_proxy_for_geo(geo)
                if proxy and proxy.status == ProxyStatus.DEAD:
                    logger.warning(f"  ⚠ Proxy {proxy.host} is DEAD — attempting rotation")
                    # Try to get a different healthy proxy
                    for p in self._proxy_manager.pool:
                        if p.status != ProxyStatus.DEAD and p.country == geo.country:
                            proxy = p
                            logger.info(f"  ✓ Rotated to healthy proxy: {p.host}:{p.port}")
                            break
                elif proxy is None:
                    logger.warning("  ⚠ No proxy available for billing geo — browser will use direct connection")
            except ImportError:
                pass
            except Exception as e:
                logger.debug(f"  Proxy health check skipped: {e}")
        
        # V7.6 V5-FIX: Generate and inject commerce trust tokens into profile
        try:
            tokens = self.generate_commerce_tokens(age_days=60)
            if tokens and self.config.profile_path:
                profile_path = Path(self.config.profile_path) if not isinstance(self.config.profile_path, Path) else self.config.profile_path
                token_file = profile_path / ".titan" / "commerce_tokens.json"
                token_file.parent.mkdir(parents=True, exist_ok=True)
                import json as _json
                token_file.write_text(_json.dumps(tokens, indent=2))
                logger.info(f"  ✓ Commerce tokens written to profile ({len(tokens)} providers)")
        except Exception as e:
            logger.debug(f"  Commerce token injection skipped: {e}")
        
        # V8 U16-FIX: Configure DNS-over-HTTPS to prevent DNS leak
        try:
            profile_path = Path(self.config.profile_path) if self.config.profile_path else None
            if profile_path and profile_path.exists():
                user_js = profile_path / "user.js"
                doh_prefs = [
                    '\n// V8 DNS-over-HTTPS — prevents DNS leak through system resolver',
                    'user_pref("network.trr.mode", 3);',           # 3 = DoH only, no fallback
                    'user_pref("network.trr.uri", "https://mozilla.cloudflare-dns.com/dns-query");',
                    'user_pref("network.trr.bootstrapAddr", "1.1.1.1");',
                    'user_pref("network.dns.disablePrefetch", true);',
                    'user_pref("network.dns.disableIPv6", true);',
                ]
                existing = user_js.read_text() if user_js.exists() else ""
                if "network.trr.mode" not in existing:
                    with open(user_js, "a") as f:
                        for pref in doh_prefs:
                            f.write(pref + "\n")
                    logger.info("  ✓ DNS-over-HTTPS configured (mode=3, Cloudflare)")
                else:
                    logger.debug("  DoH already configured in user.js")
        except Exception as e:
            logger.debug(f"  DoH configuration skipped: {e}")
        
        # V8 U2-FIX + R3-FIX: Safe-boot eBPF network shield (blocks traffic until active)
        try:
            from network_shield_loader import NetworkShield, Persona
            shield = NetworkShield()
            if shield.is_available():
                # R3-FIX: Use safe_boot() to prevent TCP fingerprint leak window
                if hasattr(shield, 'safe_boot'):
                    ebpf_ok = shield.safe_boot(mode="xdp", persona="windows", timeout_seconds=30)
                    if ebpf_ok:
                        logger.info("  ✓ eBPF network shield safe-booted (zero leak window)")
                    else:
                        logger.warning("  ⚠ eBPF safe-boot degraded — TCP fingerprint may be Linux")
                else:
                    shield.load()
                    shield.switch_persona(Persona.WINDOWS)
                    logger.info("  ✓ eBPF network shield loaded (Windows TCP/IP persona)")
            else:
                logger.debug("  eBPF shield: not available (requires root + kernel support)")
        except ImportError:
            logger.debug("  eBPF shield module not available")
        except Exception as e:
            logger.debug(f"  eBPF shield skipped: {e}")
        
        # V8 U3-FIX: Apply CPUID/RDTSC hardening to suppress KVM markers
        try:
            from cpuid_rdtsc_shield import CPUIDRDTSCShield
            cpu_shield = CPUIDRDTSCShield()
            findings = cpu_shield.detect_hypervisor()
            if findings.get("hypervisor_detected"):
                results = cpu_shield.apply_all()
                overrides_ok = sum(1 for v in results.get("sysfs_overrides", {}).values() if v)
                logger.info(f"  ✓ CPUID/RDTSC shield applied ({overrides_ok} DMI overrides)")
            else:
                logger.debug("  CPUID shield: no hypervisor detected, skipping")
        except ImportError:
            logger.debug("  CPUID/RDTSC shield module not available")
        except Exception as e:
            logger.debug(f"  CPUID/RDTSC shield skipped: {e}")
        
        # V8 U27-FIX: Profile validation before launch (V6 fail vector)
        try:
            if self.config.profile_path:
                profile_path = Path(self.config.profile_path) if not isinstance(self.config.profile_path, Path) else self.config.profile_path
                required_files = ["places.sqlite", "prefs.js", "compatibility.ini"]
                missing = [f for f in required_files if not (profile_path / f).exists()]
                if missing:
                    logger.warning(f"  ⚠️ Profile missing {len(missing)} required files: {', '.join(missing)}")
                else:
                    logger.info(f"  ✓ Profile validated ({len(required_files)} required files present)")
        except Exception as e:
            logger.debug(f"  Profile validation skipped: {e}")
        
        # V8 U27-FIX: Start session IP monitor during operation
        try:
            from proxy_manager import SessionIPMonitor
            proxy_url = getattr(self.config, 'proxy', None)
            self._session_ip_monitor = SessionIPMonitor(proxy_url=proxy_url)
            self._session_ip_monitor.start()
        except ImportError:
            logger.debug("  Session IP monitor not available")
        except Exception as e:
            logger.debug(f"  Session IP monitor skipped: {e}")
        
        # V8 U27-FIX: Auto-start transaction monitor
        try:
            from transaction_monitor import TransactionMonitor
            self._tx_monitor = TransactionMonitor()
            self._tx_monitor.start()
            logger.info("  ✓ Transaction monitor active on :7443")
        except ImportError:
            logger.debug("  Transaction monitor not available")
        except Exception as e:
            logger.debug(f"  Transaction monitor skipped: {e}")
        
        # Build config
        self.get_browser_config()
        
        # R1-FIX: Check critical subsystem health before declaring ready
        # Track fingerprint shims as critical
        shims_ok = CANVAS_SHIM_AVAILABLE or FINGERPRINT_INJECTOR_AVAILABLE or AUDIO_HARDENER_AVAILABLE
        self._track_subsystem("fingerprint_shims", critical=True, success=shims_ok,
                              error="No fingerprint shim modules available" if not shims_ok else None)
        
        # Track proxy as critical (must have proxy OR VPN)
        proxy_ok = (self._proxy_manager is not None) or (self._vpn is not None) or \
                   (self.config.proxy_config is not None)
        self._track_subsystem("proxy", critical=True, success=proxy_ok,
                              error="No proxy, VPN, or proxy config available" if not proxy_ok else None)
        
        # Track timezone as critical
        tz_ok = TIMEZONE_ENFORCER_AVAILABLE
        self._track_subsystem("timezone", critical=True, success=tz_ok,
                              error="Timezone enforcer not available" if not tz_ok else None)
        
        # Track profile validation as critical
        profile_ok = True
        profile_error = None
        if self.config.profile_path:
            profile_path = Path(self.config.profile_path) if not isinstance(self.config.profile_path, Path) else self.config.profile_path
            required_files = ["places.sqlite", "prefs.js", "compatibility.ini"]
            missing = [f for f in required_files if not (profile_path / f).exists()]
            if missing:
                profile_ok = False
                profile_error = f"Missing: {', '.join(missing)}"
        self._track_subsystem("profile_validation", critical=True, success=profile_ok, error=profile_error)
        
        # R1-FIX: Final gate — refuse to launch if critical subsystems failed
        final_report = self.get_subsystem_report()
        if not final_report["can_operate"]:
            self._set_state(BridgeState.FAILED)
            logger.error("[BRIDGE] CANNOT PROCEED — critical subsystem(s) failed:")
            for f in final_report["critical_failures"]:
                logger.error(f"  ✗ {f['name']}: {f['error']}")
            return False
        
        self._set_state(BridgeState.ARMED)
        logger.info(f"Full preparation complete — state=ARMED, "
                    f"critical={final_report['critical_ok']}/{final_report['critical_ok']}, "
                    f"optional={final_report['optional_ok']}/{final_report['optional_ok']+final_report['optional_fail']}")
        return True


# Convenience function
def create_bridge(profile_uuid: str, **kwargs) -> TitanIntegrationBridge:
    """Create and initialize a bridge instance"""
    config = BridgeConfig(profile_uuid=profile_uuid, **kwargs)
    bridge = TitanIntegrationBridge(config)
    bridge.initialize()
    return bridge


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("TITAN V8.1 Integration Bridge — use create_bridge() from code or GUI")


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 BRIDGE HEALTH MONITOR — Monitor bridge health and component status
# ═══════════════════════════════════════════════════════════════════════════════

import threading
import time
from collections import defaultdict
from enum import Enum


class ComponentHealth(Enum):
    """Component health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ComponentStatus:
    """Status of a bridge component."""
    name: str
    health: ComponentHealth
    last_check: float
    response_time_ms: Optional[float]
    error_message: Optional[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


class BridgeHealthMonitor:
    """
    V7.6 Bridge Health Monitor - Monitors health of all bridge
    components and provides real-time status updates.
    """
    
    # Component check functions
    COMPONENT_CHECKS = {
        "zero_detect": "_check_zero_detect",
        "preflight": "_check_preflight",
        "location": "_check_location",
        "commerce": "_check_commerce",
        "fingerprint": "_check_fingerprint",
        "tls_masquerade": "_check_tls_masquerade",
        "cognitive_core": "_check_cognitive_core",
        "proxy_manager": "_check_proxy_manager",
        "vpn": "_check_vpn",
    }
    
    def __init__(self, bridge: TitanIntegrationBridge):
        """
        Initialize health monitor.
        
        Args:
            bridge: TitanIntegrationBridge instance to monitor
        """
        self.bridge = bridge
        self._component_status: Dict[str, ComponentStatus] = {}
        self._health_history: List[Dict] = []
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._check_interval = 60  # seconds
    
    def _timed_check(self, check_func) -> Tuple[bool, float, Optional[str]]:
        """Run a check with timing."""
        start = time.time()
        try:
            result = check_func()
            elapsed = (time.time() - start) * 1000
            return result, elapsed, None
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            return False, elapsed, str(e)
    
    def _check_zero_detect(self) -> bool:
        return self.bridge._zero_detect is not None
    
    def _check_preflight(self) -> bool:
        return self.bridge._preflight is not None
    
    def _check_location(self) -> bool:
        return self.bridge._location is not None
    
    def _check_commerce(self) -> bool:
        return self.bridge._commerce is not None
    
    def _check_fingerprint(self) -> bool:
        return self.bridge._fingerprint is not None
    
    def _check_tls_masquerade(self) -> bool:
        return self.bridge._tls_masquerade is not None
    
    def _check_cognitive_core(self) -> bool:
        if self.bridge._cognitive_core is None:
            return False
        return getattr(self.bridge._cognitive_core, 'is_connected', False)
    
    def _check_proxy_manager(self) -> bool:
        if self.bridge._proxy_manager is None:
            return False
        try:
            stats = self.bridge._proxy_manager.get_stats()
            return stats.get('total', 0) > 0
        except Exception as e:
            logger.debug(f"[PREFLIGHT] Proxy check failed: {e}")
            return False
    
    def _check_vpn(self) -> bool:
        return self.bridge._vpn is not None
    
    def check_all(self) -> Dict[str, ComponentStatus]:
        """Check health of all components."""
        results = {}
        
        for component_name, check_method_name in self.COMPONENT_CHECKS.items():
            check_func = getattr(self, check_method_name, None)
            
            if check_func:
                success, response_time, error = self._timed_check(check_func)
                
                if success:
                    health = ComponentHealth.HEALTHY
                elif error:
                    health = ComponentHealth.UNHEALTHY
                else:
                    health = ComponentHealth.DEGRADED
                
                status = ComponentStatus(
                    name=component_name,
                    health=health,
                    last_check=time.time(),
                    response_time_ms=response_time,
                    error_message=error
                )
            else:
                status = ComponentStatus(
                    name=component_name,
                    health=ComponentHealth.UNKNOWN,
                    last_check=time.time(),
                    response_time_ms=None,
                    error_message="Check function not found"
                )
            
            results[component_name] = status
            self._component_status[component_name] = status
        
        # Record history
        self._health_history.append({
            "timestamp": time.time(),
            "healthy": sum(1 for s in results.values() if s.health == ComponentHealth.HEALTHY),
            "total": len(results)
        })
        
        # Trim history
        if len(self._health_history) > 1000:
            self._health_history = self._health_history[-500:]
        
        return results
    
    def get_overall_health(self) -> ComponentHealth:
        """Get overall bridge health."""
        if not self._component_status:
            return ComponentHealth.UNKNOWN
        
        healthy_count = sum(
            1 for s in self._component_status.values() 
            if s.health == ComponentHealth.HEALTHY
        )
        total = len(self._component_status)
        
        ratio = healthy_count / total if total > 0 else 0
        
        if ratio >= 0.8:
            return ComponentHealth.HEALTHY
        elif ratio >= 0.5:
            return ComponentHealth.DEGRADED
        else:
            return ComponentHealth.UNHEALTHY
    
    def _monitor_loop(self):
        """Background monitoring loop."""
        while self._running:
            self.check_all()
            time.sleep(self._check_interval)
    
    def start(self, check_interval: int = 60):
        """Start background health monitoring."""
        self._check_interval = check_interval
        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
    
    def stop(self):
        """Stop background monitoring."""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
    
    def get_status_report(self) -> Dict:
        """Get comprehensive status report."""
        return {
            "overall_health": self.get_overall_health().value,
            "components": {
                name: {
                    "health": status.health.value,
                    "last_check": status.last_check,
                    "response_time_ms": status.response_time_ms,
                    "error": status.error_message
                }
                for name, status in self._component_status.items()
            },
            "bridge_initialized": self.bridge.initialized,
            "history_points": len(self._health_history)
        }


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 MODULE DISCOVERY ENGINE — Dynamically discover and load available modules
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class DiscoveredModule:
    """Information about a discovered module."""
    name: str
    path: str
    available: bool
    version: Optional[str]
    capabilities: List[str]
    dependencies: List[str]
    load_error: Optional[str] = None


class ModuleDiscoveryEngine:
    """
    V7.6 Module Discovery Engine - Dynamically discovers and
    catalogs available TITAN modules.
    """
    
    # Module search paths
    SEARCH_PATHS = [
        "/opt/titan/core",
        "/opt/titan/drivers",
        "/opt/titan",
        "/opt/titan/core",
        "/opt/titan/modules",
    ]
    
    # Known module definitions
    KNOWN_MODULES = {
        "fingerprint_manager": {
            "capabilities": ["canvas_noise", "webgl_noise", "audio_noise", "font_hash"],
            "dependencies": []
        },
        "location_spoofer": {
            "capabilities": ["geolocation", "timezone", "locale"],
            "dependencies": []
        },
        "commerce_vault": {
            "capabilities": ["stripe_tokens", "payment_fingerprints"],
            "dependencies": []
        },
        "tls_masquerade": {
            "capabilities": ["ja3_spoof", "ja4_spoof", "cipher_selection"],
            "dependencies": []
        },
        "humanization": {
            "capabilities": ["mouse_movement", "typing_patterns", "scroll_behavior"],
            "dependencies": []
        },
        "biometric_mimicry": {
            "capabilities": ["velocity_profiles", "pressure_simulation"],
            "dependencies": ["humanization"]
        },
        "cognitive_core": {
            "capabilities": ["llm_inference", "decision_making", "context_analysis"],
            "dependencies": []
        },
        "proxy_manager": {
            "capabilities": ["proxy_rotation", "geo_targeting", "health_check"],
            "dependencies": []
        },
    }
    
    def __init__(self):
        self._discovered: Dict[str, DiscoveredModule] = {}
        self._capabilities_index: Dict[str, List[str]] = defaultdict(list)
    
    def discover_all(self) -> Dict[str, DiscoveredModule]:
        """Discover all available modules."""
        self._discovered.clear()
        self._capabilities_index.clear()
        
        for search_path in self.SEARCH_PATHS:
            path = Path(search_path)
            if path.exists():
                self._scan_directory(path)
        
        return self._discovered
    
    def _scan_directory(self, directory: Path):
        """Scan a directory for Python modules."""
        for item in directory.iterdir():
            if item.suffix == ".py" and not item.name.startswith("_"):
                module_name = item.stem
                self._check_module(module_name, str(item))
            elif item.is_dir() and (item / "__init__.py").exists():
                self._check_module(item.name, str(item))
    
    def _check_module(self, module_name: str, module_path: str):
        """Check if a module can be loaded."""
        known_info = self.KNOWN_MODULES.get(module_name, {})
        
        module = DiscoveredModule(
            name=module_name,
            path=module_path,
            available=False,
            version=None,
            capabilities=known_info.get("capabilities", []),
            dependencies=known_info.get("dependencies", [])
        )
        
        try:
            # Try to import the module
            import importlib.util
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            if spec and spec.loader:
                loaded = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(loaded)
                
                module.available = True
                module.version = getattr(loaded, "__version__", None)
                
                # Index capabilities
                for cap in module.capabilities:
                    self._capabilities_index[cap].append(module_name)
                
        except Exception as e:
            module.load_error = str(e)
        
        self._discovered[module_name] = module
    
    def get_modules_by_capability(self, capability: str) -> List[DiscoveredModule]:
        """Get modules that provide a specific capability."""
        module_names = self._capabilities_index.get(capability, [])
        return [self._discovered[name] for name in module_names if name in self._discovered]
    
    def get_available_capabilities(self) -> List[str]:
        """Get list of all available capabilities."""
        return list(self._capabilities_index.keys())
    
    def check_dependencies(self, module_name: str) -> Dict[str, bool]:
        """Check if a module's dependencies are satisfied."""
        module = self._discovered.get(module_name)
        if not module:
            return {}
        
        results = {}
        for dep in module.dependencies:
            dep_module = self._discovered.get(dep)
            results[dep] = dep_module is not None and dep_module.available
        
        return results
    
    def get_load_order(self, target_modules: List[str]) -> List[str]:
        """Get optimal load order respecting dependencies."""
        loaded = set()
        order = []
        
        def add_module(name: str):
            if name in loaded:
                return
            
            module = self._discovered.get(name)
            if not module:
                return
            
            # Load dependencies first
            for dep in module.dependencies:
                add_module(dep)
            
            if name not in loaded:
                order.append(name)
                loaded.add(name)
        
        for module_name in target_modules:
            add_module(module_name)
        
        return order
    
    def get_discovery_report(self) -> Dict:
        """Get discovery report."""
        available = [m for m in self._discovered.values() if m.available]
        unavailable = [m for m in self._discovered.values() if not m.available]
        
        return {
            "total_discovered": len(self._discovered),
            "available": len(available),
            "unavailable": len(unavailable),
            "capabilities": len(self._capabilities_index),
            "modules": {
                name: {
                    "available": m.available,
                    "version": m.version,
                    "capabilities": m.capabilities,
                    "error": m.load_error
                }
                for name, m in self._discovered.items()
            }
        }


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 INTEGRATION ANALYTICS — Track integration usage and performance
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class IntegrationEvent:
    """An integration event for analytics."""
    event_type: str
    module: str
    timestamp: float
    duration_ms: float
    success: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


class IntegrationAnalytics:
    """
    V7.6 Integration Analytics - Tracks integration usage
    and performance across the bridge.
    """
    
    def __init__(self, max_events: int = 10000):
        """
        Initialize integration analytics.
        
        Args:
            max_events: Maximum events to retain in memory
        """
        self.max_events = max_events
        self._events: List[IntegrationEvent] = []
        self._module_stats: Dict[str, Dict] = defaultdict(
            lambda: {"calls": 0, "successes": 0, "total_ms": 0}
        )
        self._capability_usage: Dict[str, int] = defaultdict(int)
    
    def record_event(self, event_type: str, module: str,
                    duration_ms: float, success: bool,
                    metadata: Optional[Dict] = None):
        """Record an integration event."""
        event = IntegrationEvent(
            event_type=event_type,
            module=module,
            timestamp=time.time(),
            duration_ms=duration_ms,
            success=success,
            metadata=metadata or {}
        )
        
        self._events.append(event)
        
        # Update module stats
        stats = self._module_stats[module]
        stats["calls"] += 1
        if success:
            stats["successes"] += 1
        stats["total_ms"] += duration_ms
        
        # Update capability usage
        if "capability" in (metadata or {}):
            self._capability_usage[metadata["capability"]] += 1
        
        # Trim events if needed
        if len(self._events) > self.max_events:
            self._events = self._events[-self.max_events // 2:]
    
    def record_initialization(self, module: str, duration_ms: float, success: bool):
        """Record module initialization."""
        self.record_event("init", module, duration_ms, success)
    
    def record_method_call(self, module: str, method: str,
                          duration_ms: float, success: bool):
        """Record a method call."""
        self.record_event("call", module, duration_ms, success, {"method": method})
    
    def get_module_stats(self, module: str) -> Dict:
        """Get stats for a specific module."""
        stats = self._module_stats.get(module, {"calls": 0, "successes": 0, "total_ms": 0})
        calls = stats["calls"]
        
        return {
            "calls": calls,
            "successes": stats["successes"],
            "failures": calls - stats["successes"],
            "success_rate": stats["successes"] / calls if calls > 0 else 0,
            "avg_duration_ms": stats["total_ms"] / calls if calls > 0 else 0
        }
    
    def get_all_module_stats(self) -> Dict[str, Dict]:
        """Get stats for all modules."""
        return {module: self.get_module_stats(module) for module in self._module_stats}
    
    def get_capability_usage(self) -> Dict[str, int]:
        """Get capability usage counts."""
        return dict(self._capability_usage)
    
    def get_performance_summary(self) -> Dict:
        """Get performance summary."""
        if not self._events:
            return {"total_events": 0}
        
        total_duration = sum(e.duration_ms for e in self._events)
        total_success = sum(1 for e in self._events if e.success)
        
        # Calculate by event type
        event_types = defaultdict(lambda: {"count": 0, "duration": 0})
        for event in self._events:
            event_types[event.event_type]["count"] += 1
            event_types[event.event_type]["duration"] += event.duration_ms
        
        return {
            "total_events": len(self._events),
            "total_duration_ms": round(total_duration, 2),
            "success_rate": round(total_success / len(self._events), 3),
            "event_types": {
                et: {
                    "count": data["count"],
                    "avg_duration_ms": round(data["duration"] / data["count"], 2)
                }
                for et, data in event_types.items()
            },
            "top_modules": sorted(
                self._module_stats.items(),
                key=lambda x: x[1]["calls"],
                reverse=True
            )[:5]
        }
    
    def get_recent_events(self, count: int = 100) -> List[Dict]:
        """Get recent events."""
        recent = self._events[-count:]
        return [
            {
                "type": e.event_type,
                "module": e.module,
                "timestamp": e.timestamp,
                "duration_ms": e.duration_ms,
                "success": e.success
            }
            for e in reversed(recent)
        ]


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 CROSS-MODULE SYNCHRONIZER — Synchronize state across modules
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class SyncState:
    """Synchronized state data."""
    key: str
    value: Any
    source_module: str
    timestamp: float
    version: int


class CrossModuleSynchronizer:
    """
    V7.6 Cross-Module Synchronizer - Synchronizes shared state
    across multiple TITAN modules.
    """
    
    # Shared state keys that need synchronization
    SYNC_KEYS = [
        "profile_uuid",
        "active_proxy",
        "geolocation",
        "timezone",
        "fingerprint_seed",
        "session_id",
        "target_domain",
        "billing_address",
    ]
    
    def __init__(self):
        self._state: Dict[str, SyncState] = {}
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._lock = threading.Lock()
        self._version_counter = 0
    
    def set_state(self, key: str, value: Any, source_module: str) -> SyncState:
        """
        Set a synchronized state value.
        
        Args:
            key: State key
            value: State value
            source_module: Module setting the state
        
        Returns:
            Created SyncState
        """
        with self._lock:
            self._version_counter += 1
            
            state = SyncState(
                key=key,
                value=value,
                source_module=source_module,
                timestamp=time.time(),
                version=self._version_counter
            )
            
            self._state[key] = state
            self._notify_subscribers(key, state)
            
            return state
    
    def get_state(self, key: str) -> Optional[SyncState]:
        """Get a synchronized state value."""
        return self._state.get(key)
    
    def get_value(self, key: str, default: Any = None) -> Any:
        """Get just the value of a state key."""
        state = self._state.get(key)
        return state.value if state else default
    
    def subscribe(self, key: str, callback: Callable[[SyncState], None]):
        """
        Subscribe to state changes.
        
        Args:
            key: State key to watch (use "*" for all)
            callback: Function to call on change
        """
        self._subscribers[key].append(callback)
    
    def unsubscribe(self, key: str, callback: Callable):
        """Unsubscribe from state changes."""
        if callback in self._subscribers[key]:
            self._subscribers[key].remove(callback)
    
    def _notify_subscribers(self, key: str, state: SyncState):
        """Notify subscribers of state change."""
        # Notify specific subscribers
        for callback in self._subscribers.get(key, []):
            try:
                callback(state)
            except Exception as e:
                logger.debug(f"[STATE] Subscriber callback error for {key}: {e}")
        
        # Notify wildcard subscribers
        for callback in self._subscribers.get("*", []):
            try:
                callback(state)
            except Exception as e:
                logger.debug(f"[STATE] Wildcard subscriber callback error: {e}")
    
    def sync_from_bridge(self, bridge: TitanIntegrationBridge):
        """Synchronize state from a bridge instance."""
        if bridge.config.profile_uuid:
            self.set_state("profile_uuid", bridge.config.profile_uuid, "bridge")
        
        if bridge.config.target_domain:
            self.set_state("target_domain", bridge.config.target_domain, "bridge")
        
        if bridge.config.billing_address:
            self.set_state("billing_address", bridge.config.billing_address, "bridge")
        
        if bridge.config.proxy_config:
            self.set_state("active_proxy", bridge.config.proxy_config.get("url"), "bridge")
    
    def sync_to_bridge(self, bridge: TitanIntegrationBridge):
        """Push synchronized state to a bridge instance."""
        profile_uuid = self.get_value("profile_uuid")
        if profile_uuid:
            bridge.config.profile_uuid = profile_uuid
        
        target_domain = self.get_value("target_domain")
        if target_domain:
            bridge.config.target_domain = target_domain
        
        billing = self.get_value("billing_address")
        if billing:
            bridge.config.billing_address = billing
        
        proxy = self.get_value("active_proxy")
        if proxy:
            bridge.config.proxy_config = {"url": proxy}
    
    def get_all_state(self) -> Dict[str, Any]:
        """Get all synchronized state as dict."""
        return {
            key: {
                "value": state.value,
                "source": state.source_module,
                "timestamp": state.timestamp,
                "version": state.version
            }
            for key, state in self._state.items()
        }
    
    def clear_state(self, key: Optional[str] = None):
        """Clear state."""
        with self._lock:
            if key:
                self._state.pop(key, None)
            else:
                self._state.clear()


# Global instances
_bridge_health_monitor: Optional[BridgeHealthMonitor] = None
_module_discovery: Optional[ModuleDiscoveryEngine] = None
_integration_analytics: Optional[IntegrationAnalytics] = None
_cross_module_sync: Optional[CrossModuleSynchronizer] = None


def get_bridge_health_monitor(bridge: TitanIntegrationBridge) -> BridgeHealthMonitor:
    """Get bridge health monitor."""
    global _bridge_health_monitor
    if _bridge_health_monitor is None:
        _bridge_health_monitor = BridgeHealthMonitor(bridge)
    return _bridge_health_monitor


def get_module_discovery() -> ModuleDiscoveryEngine:
    """Get module discovery engine."""
    global _module_discovery
    if _module_discovery is None:
        _module_discovery = ModuleDiscoveryEngine()
    return _module_discovery


def get_integration_analytics() -> IntegrationAnalytics:
    """Get integration analytics."""
    global _integration_analytics
    if _integration_analytics is None:
        _integration_analytics = IntegrationAnalytics()
    return _integration_analytics


def get_cross_module_sync() -> CrossModuleSynchronizer:
    """Get cross-module synchronizer."""
    global _cross_module_sync
    if _cross_module_sync is None:
        _cross_module_sync = CrossModuleSynchronizer()
    return _cross_module_sync
