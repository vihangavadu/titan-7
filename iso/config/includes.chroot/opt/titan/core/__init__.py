"""
TITAN V8.0 SINGULARITY - Core Library
Reality Synthesis Suite - Maximum Level

V8.1 Upgrades (Persona Enrichment + Cognitive Profiling):
- Persona Enrichment Engine — AI-powered demographic profiling from name/email/age/occupation
- Purchase Pattern Prediction — 18 purchase categories with demographic-weighted likelihood scoring
- Coherence Validation — Blocks out-of-pattern purchases before they trigger bank declines
- OSINT Enrichment (optional) — Sherlock, Holehe, Maigret integration for interest inference
- Preflight Coherence Check — Wired into PreFlightValidator for automatic persona-purchase alignment
- Real-Time AI Co-Pilot — Continuous AI guidance during operations with timing intelligence
- HITL Timing Guardrails — Per-phase dwell time enforcement to prevent bot-like behavior
- Referrer Chain Enforcement — Blocks operations with empty document.referrer
- Forensic SQLite PRAGMA coherence, screen dimension binding, OS-coherent download history

V8.0 Upgrades (Maximum Level):
- Ghost Motor seeded RNG (deterministic trajectories per profile)
- DNS-over-HTTPS (DoH mode=3, Cloudflare) prevents DNS leak
- eBPF network shield auto-loaded in full_prepare()
- CPUID/RDTSC shield auto-applied for KVM marker suppression
- Transaction monitor → Operations Guard live feedback loop
- Mid-session IP consistency monitor (30s polling)
- Profile validation before launch (required files check)
- Transaction monitor auto-start on operation
- Handover protocol defaults to camoufox browser
- Proxy pool auto-creation on first run
- Win10 22H2 audio profile added
- Autonomous Self-Improving Engine (24/7 operation loop with self-patching)
- Task queue ingestion, adaptive scheduling, detection analysis
- End-of-day self-patch cycle (analyze failures → adjust params → retry)
- MetricsDB (SQLite) for persistent operation tracking
- 28+ upgrade opportunities identified and patched

V7.6 Upgrades (AI Integration + P0 Critical):
- AI Intelligence Engine with Ollama LLM integration
- DevHub v7.6.0 with AI provider management & system editing
- Transaction Analytics, Alert System, BIN Intelligence, Exporter
- Deep Identity Orchestrator, Leak Detector, Consistency Checker
- Advanced config validation, monitoring, secure config, migration
- Service health watchdog, dependency management, metrics collection
- Verification orchestration, history tracking, remediation, scheduling

V7.5 Upgrades (Singularity Enhancements):
- JA4+ Dynamic Permutation Engine (TLS fingerprint randomization)
- IndexedDB/LSNG Sharding Synthesis (advanced storage)
- TRA Exemption Engine (3DS v2.2 frictionless authentication)
- ToF Depth Map Synthesis (3D biometric depth maps)
- Issuer Algorithmic Decline Defense (decline protection)
- First-Session Bias Elimination (detection removal)
- Target Discovery auto-discovery, competitor analysis, metrics
- Intelligence sync, recommendation engine, change tracker
- Preset version manager, validator, migrator, dynamic builder
- Timezone monitor, anomaly detector, transition manager
- QUIC connection pooling, fingerprint rotation, health monitoring
- Referrer campaign manager, chain validator, adaptive warmup

V7.0 Upgrades (Singularity Foundation):
- Immutable OS with OverlayFS + A/B atomic partition updates
- Cockpit middleware daemon (privileged ops via signed JSON over Unix socket)
- TLS Hello Parroting (JA4+ evasion via Client Hello template injection)
- WebGL ANGLE Shim (GPU fingerprint standardization, not spoofing)
- eBPF-driven network micro-jitter + background noise traffic
- Cross-device sync via Waydroid (mobile-desktop persona binding)
- Seven-Layer Spoofing Model (Kernel, Network, DNS, Browser, Fonts, Audio, Behavior)

V6.2 Foundation (carried forward into V7.0):
- Cloud Cognitive Core (vLLM integration, sub-200ms latency)
- DMTG Diffusion Mouse Trajectories (replaces GAN)
- Transparent QUIC Proxy (no more TCP fallback fingerprint)
- Dynamic Netlink Hardware Injection (runtime profile switching)
- Intelligence Layer (AVS, Visa Alerts, PayPal Defense, 3DS v2, Proxy Intel)
- 32 target profiles, 16 antifraud system profiles, card freshness scoring

This module provides the core logic for the Trinity Apps:
- Genesis (Profile Forge)
- Cerberus (Card Validator)
- KYC (Identity Mask)
"""

__version__ = "8.1.0"
__author__ = "Dva.12"
__status__ = "SINGULARITY_V8"
__codename__ = "MAXIMUM_LEVEL"

from .genesis_core import GenesisEngine, ProfileConfig, TargetPreset
from .cerberus_core import CerberusValidator, CardAsset, ValidationResult
try:
    from .kyc_core import KYCController, ReenactmentConfig, CameraState
except ImportError:
    KYCController = ReenactmentConfig = CameraState = None
from .cognitive_core import TitanCognitiveCore, CognitiveRequest, CognitiveResponse
from .ghost_motor_v6 import GhostMotorDiffusion, TrajectoryConfig, PersonaType
from .quic_proxy import TitanQUICProxy, ProxyConfig, BrowserProfile
from .handover_protocol import ManualHandoverProtocol, HandoverPhase, HandoverStatus
from .integration_bridge import TitanIntegrationBridge, BridgeConfig, create_bridge
from .proxy_manager import ResidentialProxyManager, ProxyEndpoint, GeoTarget, get_active_connection, SessionIPMonitor, create_session_ip_monitor
from .lucid_vpn import LucidVPN, VPNConfig, VPNMode, VPNStatus
from .purchase_history_engine import PurchaseHistoryEngine, CardHolderData, PurchaseHistoryConfig, inject_purchase_history
from .cerberus_enhanced import AVSEngine, BINScoringEngine, SilentValidationEngine, GeoMatchChecker, check_avs, score_bin, get_silent_strategy, check_geo
from .cerberus_enhanced import OSINTVerifier, OSINTReport, OSINTVerificationResult
from .cerberus_enhanced import CardQualityGrader, CardQualityGrade, CardQualityReport
from .generate_trajectory_model import TrajectoryPlanner, WarmupTrajectoryPlan, generate_warmup_trajectory
from .kill_switch import KillSwitch, KillSwitchConfig, ThreatLevel, arm_kill_switch, send_panic_signal
from .font_sanitizer import FontSanitizer, TargetOS as FontTargetOS, sanitize_fonts, check_fonts
from .audio_hardener import AudioHardener, AudioTargetOS, harden_audio
from .timezone_enforcer import TimezoneEnforcer, TimezoneConfig, enforce_timezone, get_timezone_for_state
try:
    from .kyc_enhanced import KYCEnhancedController, KYCSessionConfig, DocumentAsset, FaceAsset, LivenessChallenge, KYCProvider, DocumentType, create_kyc_session
except ImportError:
    KYCEnhancedController = KYCSessionConfig = DocumentAsset = FaceAsset = LivenessChallenge = KYCProvider = DocumentType = create_kyc_session = None
from .fingerprint_injector import FingerprintInjector, FingerprintConfig, create_injector, NetlinkHWBridge
from .referrer_warmup import ReferrerWarmup, WarmupPlan, create_warmup_plan, get_warmup_instructions
from .advanced_profile_generator import AdvancedProfileGenerator, AdvancedProfileConfig
from .target_presets import TARGET_PRESETS, get_target_preset, list_targets as list_target_presets, TargetPreset as SiteTargetPreset
from .target_presets import get_target_preset_auto, list_all_targets, generate_preset_from_intel
from .form_autofill_injector import FormAutofillInjector
from .verify_deep_identity import verify_font_hygiene, verify_audio_hardening, verify_timezone_sync
from .location_spoofer_linux import LinuxLocationSpoofer, LocationProfile, GeoCoordinates
from .titan_env import load_env, get_config, is_configured, get_config_status

# V7.0 Singularity Modules
from .tls_parrot import TLSParrotEngine, TLSTemplate, ParrotTarget, get_parrot_config
from .webgl_angle import WebGLAngleShim, WebGLParams, GPUProfile, get_webgl_config
from .network_jitter import NetworkJitterEngine, ConnectionType, JitterProfile, apply_network_jitter
from .immutable_os import ImmutableOSManager, ImmutableConfig, verify_system_integrity, get_boot_status
from .cockpit_daemon import CockpitClient, CockpitDaemon, CommandAction
try:
    from .waydroid_sync import WaydroidSyncEngine, SyncConfig, MobilePersona, start_cross_device_sync
except ImportError:
    WaydroidSyncEngine = SyncConfig = MobilePersona = start_cross_device_sync = None

# V6.1 Intelligence & Evasion Enhancements
from .target_intelligence import (
    AntifraudSystemProfile, ProcessorProfile,
    ANTIFRAUD_PROFILES, PROCESSOR_PROFILES, OSINT_TOOLS,
    SEON_SCORING_RULES, estimate_seon_score,
    get_target_intel, get_antifraud_profile, get_processor_profile,
    get_osint_tools, get_profile_requirements,
)
# Intelligence Modules
from .target_intelligence import (
    get_avs_intelligence, get_visa_alerts_intel, check_visa_alerts_eligible,
    get_fingerprint_tools, get_card_prechecking_intel, estimate_card_freshness,
    get_proxy_intelligence, get_paypal_defense_intel,
    AVS_RESPONSE_CODES, AVS_COUNTRIES, VISA_ALERTS_INTEL,
    FINGERPRINT_CHECK_TOOLS, CARD_PRECHECKING_INTEL, PROXY_INTELLIGENCE,
    PAYPAL_DEFENSE_INTEL,
)
from .preflight_validator import PreFlightValidator, PreFlightReport
from .three_ds_strategy import (
    ThreeDSStrategy, get_3ds_strategy, get_3ds_detection_guide,
    VBV_TEST_BINS, THREE_DS_NETWORK_SIGNATURES, AMOUNT_THRESHOLDS,
    get_3ds_v2_intelligence, THREE_DS_INITIATORS, THREE_DS_2_INTELLIGENCE,
    NonVBVRecommendationEngine, get_non_vbv_recommendations,
    get_non_vbv_country_profile, get_easy_countries, get_all_non_vbv_bins,
    COUNTRY_PROFILES, NON_VBV_BINS, COUNTRY_DIFFICULTY_RANKING,
    ThreeDSBypassEngine, get_3ds_bypass_score, get_3ds_bypass_plan,
    get_downgrade_attacks, get_psd2_exemptions, get_psp_vulnerabilities,
    PSP_3DS_VULNERABILITIES, PSD2_EXEMPTIONS, THREE_DS_DOWNGRADE_ATTACKS,
)
from .cerberus_core import (
    get_osint_checklist, get_card_quality_guide, get_bank_enrollment_guide,
)
from .ghost_motor_v6 import (
    get_forter_safe_params, get_biocatch_evasion_guide, get_warmup_pattern,
    FORTER_SAFE_PARAMS, BIOCATCH_EVASION, WARMUP_BROWSING_PATTERNS,
)
from .handover_protocol import (
    get_post_checkout_guide, get_handover_osint_checklist,
    intel_aware_handover, POST_CHECKOUT_GUIDES,
)
from .target_discovery import (
    TargetDiscovery, SiteProbe, AutoDiscovery, get_easy_sites, get_2d_sites,
    get_shopify_sites, recommend_sites, probe_site, get_site_stats,
    search_sites, auto_discover, get_bypass_targets, get_downgradeable,
    SITE_DATABASE,
)
from .intel_monitor import (
    IntelMonitor, get_intel_sources, get_intel_feed,
    get_intel_alerts, get_intel_settings,
)
from .transaction_monitor import (
    TransactionMonitor, DeclineDecoder, decode_decline,
    get_tx_stats, start_tx_monitor,
)
from .titan_services import (
    TitanServiceManager, DailyDiscoveryScheduler, OperationalFeedbackLoop,
    MemoryPressureManager,
    get_service_manager, start_all_services, stop_all_services, get_services_status,
)
from .bug_patch_bridge import BugPatchBridge

# V7.6 Self-Hosted Tool Stack
try:
    from .titan_self_hosted_stack import (
        TitanSelfHostedStack, get_self_hosted_stack,
        GeoIPValidator, get_geoip_validator,
        IPQualityChecker, get_ip_quality_checker,
        ProxyHealthMonitor, get_proxy_health_monitor,
        RedisClient, get_redis_client,
        NtfyClient, get_ntfy_client,
        TargetSiteProber, get_target_prober,
        TechStackDetector, get_tech_detector,
        MinIOClient, get_minio_client,
    )
except ImportError:
    TitanSelfHostedStack = get_self_hosted_stack = None
    GeoIPValidator = get_geoip_validator = None
    IPQualityChecker = get_ip_quality_checker = None
    ProxyHealthMonitor = get_proxy_health_monitor = None
    RedisClient = get_redis_client = None
    NtfyClient = get_ntfy_client = None
    TargetSiteProber = get_target_prober = None
    TechStackDetector = get_tech_detector = None
    MinIOClient = get_minio_client = None

# V7.6 Target Intelligence V2 — Golden Path Scoring
try:
    from .titan_target_intel_v2 import (
        TargetIntelV2, get_target_intel_v2,
        score_target as score_target_v2,
        find_golden_targets, get_no_3ds_psps,
        full_target_analysis,
        PSP_3DS_BEHAVIOR, MCC_3DS_INTELLIGENCE,
        GEO_3DS_ENFORCEMENT, TRANSACTION_TYPE_EXEMPTIONS,
        CONFIRMED_NO_3DS_PATTERNS, ANTIFRAUD_GAPS,
        GoldenPathScore,
    )
except ImportError:
    TargetIntelV2 = get_target_intel_v2 = None
    score_target_v2 = find_golden_targets = get_no_3ds_psps = full_target_analysis = None
    PSP_3DS_BEHAVIOR = MCC_3DS_INTELLIGENCE = GEO_3DS_ENFORCEMENT = None
    TRANSACTION_TYPE_EXEMPTIONS = CONFIRMED_NO_3DS_PATTERNS = ANTIFRAUD_GAPS = None
    GoldenPathScore = None

# V7.6 3DS AI-Speed Exploit Engine
try:
    from .titan_3ds_ai_exploits import (
        ThreeDSAIEngine, get_3ds_ai_engine,
        get_ai_techniques, get_optimal_exploit_stack,
        generate_exploit_script,
    )
except ImportError:
    ThreeDSAIEngine = get_3ds_ai_engine = None
    get_ai_techniques = get_optimal_exploit_stack = generate_exploit_script = None

# V7.6 AI Operations Guard — Silent Ollama-powered operation lifecycle monitor
try:
    from .titan_ai_operations_guard import (
        AIOperationsGuard, get_operations_guard,
        pre_op_check, session_health, checkout_assist, post_op_analysis,
        GuardVerdict, OperationPhase, RiskLevel,
    )
except ImportError:
    AIOperationsGuard = get_operations_guard = None
    pre_op_check = session_health = checkout_assist = post_op_analysis = None
    GuardVerdict = OperationPhase = RiskLevel = None

# V7.5 Singularity Enhancement Modules
from .ja4_permutation_engine import JA4PermutationEngine
from .indexeddb_lsng_synthesis import IndexedDBShardSynthesizer, LocalStorageSynthesizer, StoragePersona, StorageShard
from .tra_exemption_engine import ExemptionType, CardholderProfile, IssuerBehaviorPredictor
from .tof_depth_synthesis import FaceDepthGenerator, DepthQuality, FacialLandmarks, DepthMapConfig
from .issuer_algo_defense import IssuerDeclineDefenseEngine, DeclineReason, AmountOptimizer
from .first_session_bias_eliminator import FirstSessionBiasEliminator

# P1-10 FIX: Missing module exports
try:
    from .payment_preflight import PaymentPreflightV2, PreflightResult
except ImportError:
    PaymentPreflightV2 = PreflightResult = None

try:
    from .payment_sandbox_tester import PaymentSandboxTester
except ImportError:
    PaymentSandboxTester = None

try:
    from .payment_success_metrics import PaymentSuccessMetrics
except ImportError:
    PaymentSuccessMetrics = None

try:
    from .titan_operation_logger import OperationLogger
except ImportError:
    OperationLogger = None

try:
    from .cognitive_core import get_module_health
except ImportError:
    get_module_health = None

# V8.0 Autonomous Self-Improving Engine
try:
    from .titan_autonomous_engine import (
        AutonomousEngine, get_autonomous_engine, start_autonomous, stop_autonomous,
        get_autonomous_status, TaskQueue, TaskInput, MetricsDB, DetectionAnalyzer,
        SelfPatcher, AdaptiveScheduler, CycleMetrics
    )
except ImportError:
    AutonomousEngine = get_autonomous_engine = start_autonomous = stop_autonomous = None
    get_autonomous_status = TaskQueue = TaskInput = MetricsDB = None
    DetectionAnalyzer = SelfPatcher = AdaptiveScheduler = CycleMetrics = None

# V8.1 Real-Time AI Co-Pilot — continuous AI assistant during operations
try:
    from .titan_realtime_copilot import (
        RealtimeCopilot, get_realtime_copilot, start_copilot, stop_copilot,
        begin_op, end_op, get_guidance, get_dashboard,
        OperatorPhase, GuidanceLevel, GuidanceMessage,
        TimingIntelligence, MistakeDetector, OllamaRealtimeAdvisor,
    )
except ImportError:
    RealtimeCopilot = get_realtime_copilot = start_copilot = stop_copilot = None
    begin_op = end_op = get_guidance = get_dashboard = None
    OperatorPhase = GuidanceLevel = GuidanceMessage = None
    TimingIntelligence = MistakeDetector = OllamaRealtimeAdvisor = None

# V8.1 Persona Enrichment Engine — AI-powered demographic profiling + coherence validation
try:
    from .persona_enrichment_engine import (
        PersonaEnrichmentEngine, DemographicProfiler, PurchasePatternPredictor,
        CoherenceValidator, OSINTEnricher, DemographicProfile, PurchaseCategory,
        CoherenceResult, AgeGroup, OccupationCategory, IncomeLevel,
    )
except ImportError:
    PersonaEnrichmentEngine = DemographicProfiler = PurchasePatternPredictor = None
    CoherenceValidator = OSINTEnricher = DemographicProfile = PurchaseCategory = None
    CoherenceResult = AgeGroup = OccupationCategory = IncomeLevel = None

# ═══════════════════════════════════════════════════════════════════════════════
# ORPHAN FIX: Previously unregistered core modules (17 modules)
# ═══════════════════════════════════════════════════════════════════════════════

# AI Intelligence Engine (Ollama LLM integration, model selection, prompt optimization)
try:
    from .ai_intelligence_engine import (
        UnifiedAIOrchestrator, AIModelSelector, AIPromptOptimizer,
        AIResponseValidator, AIBINAnalysis, AIPreFlightAdvice,
        AITargetRecon, AI3DSStrategy, AIProfileAudit, AIBehavioralTuning,
    )
except ImportError:
    UnifiedAIOrchestrator = AIModelSelector = AIPromptOptimizer = AIResponseValidator = None
    AIBINAnalysis = AIPreFlightAdvice = AITargetRecon = AI3DSStrategy = None
    AIProfileAudit = AIBehavioralTuning = None

# Canvas Subpixel Shim (anti-fingerprint canvas noise injection)
try:
    from .canvas_subpixel_shim import CanvasSubpixelShim
except ImportError:
    CanvasSubpixelShim = None

# CPUID/RDTSC Shield (KVM marker suppression)
try:
    from .cpuid_rdtsc_shield import CPUIDShield
except ImportError:
    CPUIDShield = None

# Dynamic Data Generation
try:
    from .dynamic_data import DynamicDataGenerator
except ImportError:
    DynamicDataGenerator = None

# Forensic Monitor (real-time detection monitoring)
try:
    from .forensic_monitor import ForensicMonitor
except ImportError:
    ForensicMonitor = None

# KYC Voice Engine (voice synthesis for liveness)
try:
    from .kyc_voice_engine import KYCVoiceEngine
except ImportError:
    KYCVoiceEngine = None

# Network Shield Loader (eBPF/XDP TCP stack rewrite)
try:
    from .network_shield_loader import NetworkShieldLoader
except ImportError:
    NetworkShieldLoader = None

# Ollama Bridge (local LLM integration)
try:
    from .ollama_bridge import OllamaBridge
except ImportError:
    OllamaBridge = None

# USB Peripheral Synthesis (fake USB device tree)
try:
    from .usb_peripheral_synth import USBPeripheralSynth
except ImportError:
    USBPeripheralSynth = None

# Windows Font Provisioner (font substitution for Linux)
try:
    from .windows_font_provisioner import WindowsFontProvisioner
except ImportError:
    WindowsFontProvisioner = None

# Titan Agent Chain (multi-step AI agent orchestration)
try:
    from .titan_agent_chain import AgentChain
except ImportError:
    AgentChain = None

# Titan Auto Patcher (automated bug fixing)
try:
    from .titan_auto_patcher import TitanAutoPatcher
except ImportError:
    TitanAutoPatcher = None

# Titan Automation Orchestrator (workflow automation)
try:
    from .titan_automation_orchestrator import AutomationOrchestrator
except ImportError:
    AutomationOrchestrator = None

# Titan Detection Analyzer (antifraud detection analysis)
try:
    from .titan_detection_analyzer import TitanDetectionAnalyzer
except ImportError:
    TitanDetectionAnalyzer = None

# Titan Vector Memory (embedding-based context memory)
try:
    from .titan_vector_memory import VectorMemory
except ImportError:
    VectorMemory = None

# Titan Web Intel (web scraping intelligence)
try:
    from .titan_web_intel import WebIntelCollector
except ImportError:
    WebIntelCollector = None

# Titan Master Automation (high-level automation coordinator)
try:
    from .titan_master_automation import MasterAutomation
except ImportError:
    MasterAutomation = None

__all__ = [
    # Trinity Apps Core
    'GenesisEngine', 'ProfileConfig', 'TargetPreset',
    'CerberusValidator', 'CardAsset', 'ValidationResult',
    'KYCController', 'ReenactmentConfig', 'CameraState',
    # V6 Cloud Cognitive
    'TitanCognitiveCore', 'CognitiveRequest', 'CognitiveResponse',
    # V6 DMTG Ghost Motor
    'GhostMotorDiffusion', 'TrajectoryConfig', 'PersonaType',
    # V6 QUIC Proxy
    'TitanQUICProxy', 'ProxyConfig', 'BrowserProfile',
    # V6 Manual Handover Protocol (Report Section 7.2)
    'ManualHandoverProtocol', 'HandoverPhase', 'HandoverStatus',
    # V6 Integration Bridge (95% Success Rate)
    'TitanIntegrationBridge', 'BridgeConfig', 'create_bridge',
    # V6 Residential Proxy Manager
    'ResidentialProxyManager', 'ProxyEndpoint', 'GeoTarget',
    # V6 Fingerprint Injector
    'FingerprintInjector', 'FingerprintConfig', 'create_injector',
    # V6 Referrer Chain Warmup
    'ReferrerWarmup', 'WarmupPlan', 'create_warmup_plan', 'get_warmup_instructions',
    # V6.1 Target Intelligence & Antifraud Profiles
    'AntifraudSystemProfile', 'ProcessorProfile',
    'ANTIFRAUD_PROFILES', 'PROCESSOR_PROFILES', 'OSINT_TOOLS',
    'SEON_SCORING_RULES', 'estimate_seon_score',
    'get_target_intel', 'get_antifraud_profile', 'get_processor_profile',
    'get_osint_tools', 'get_profile_requirements',
    # V6.1 Enhanced Pre-Flight Validator
    'PreFlightValidator', 'PreFlightReport',
    # V6.1 3DS Strategy & Detection
    'ThreeDSStrategy', 'get_3ds_strategy', 'get_3ds_detection_guide',
    'VBV_TEST_BINS', 'THREE_DS_NETWORK_SIGNATURES', 'AMOUNT_THRESHOLDS',
    # V7.5 3DS Bypass & Downgrade Engine
    'ThreeDSBypassEngine', 'get_3ds_bypass_score', 'get_3ds_bypass_plan',
    'get_downgrade_attacks', 'get_psd2_exemptions', 'get_psp_vulnerabilities',
    'PSP_3DS_VULNERABILITIES', 'PSD2_EXEMPTIONS', 'THREE_DS_DOWNGRADE_ATTACKS',
    # V7.0.2 Non-VBV Card Recommendation Engine
    'NonVBVRecommendationEngine', 'get_non_vbv_recommendations',
    'get_non_vbv_country_profile', 'get_easy_countries', 'get_all_non_vbv_bins',
    'COUNTRY_PROFILES', 'NON_VBV_BINS', 'COUNTRY_DIFFICULTY_RANKING',
    # V7.5 Target Discovery + Auto-Discovery + Bypass Scoring
    'TargetDiscovery', 'SiteProbe', 'AutoDiscovery',
    'get_easy_sites', 'get_2d_sites', 'get_shopify_sites',
    'recommend_sites', 'probe_site', 'get_site_stats', 'search_sites',
    'auto_discover', 'get_bypass_targets', 'get_downgradeable',
    'SITE_DATABASE',
    # V7.0.2 DarkWeb & Forum Intel Monitor
    'IntelMonitor', 'get_intel_sources', 'get_intel_feed',
    'get_intel_alerts', 'get_intel_settings',
    # V7.5 Transaction Monitor (24/7 capture + decline decoder)
    'TransactionMonitor', 'DeclineDecoder', 'decode_decline',
    'get_tx_stats', 'start_tx_monitor',
    # V7.5 Service Orchestrator (auto-start, daily discovery, feedback loop)
    'TitanServiceManager', 'DailyDiscoveryScheduler', 'OperationalFeedbackLoop',
    'get_service_manager', 'start_all_services', 'stop_all_services', 'get_services_status',
    # V6.1 OSINT & Card Quality
    'get_osint_checklist', 'get_card_quality_guide', 'get_bank_enrollment_guide',
    # V6.1 Ghost Motor Evasion Profiles
    'get_forter_safe_params', 'get_biocatch_evasion_guide', 'get_warmup_pattern',
    'FORTER_SAFE_PARAMS', 'BIOCATCH_EVASION', 'WARMUP_BROWSING_PATTERNS',
    # V6.1 Enhanced Handover Protocol
    'get_post_checkout_guide', 'get_handover_osint_checklist',
    'intel_aware_handover', 'POST_CHECKOUT_GUIDES',
    # AVS Intelligence
    'get_avs_intelligence', 'AVS_RESPONSE_CODES', 'AVS_COUNTRIES',
    # Visa Alerts Intelligence
    'get_visa_alerts_intel', 'check_visa_alerts_eligible', 'VISA_ALERTS_INTEL',
    # Fingerprint Verification Tools
    'get_fingerprint_tools', 'FINGERPRINT_CHECK_TOOLS',
    # Card Prechecking & Freshness
    'get_card_prechecking_intel', 'estimate_card_freshness', 'CARD_PRECHECKING_INTEL',
    # Proxy & DNS Intelligence
    'get_proxy_intelligence', 'PROXY_INTELLIGENCE',
    # PayPal Defense Intelligence
    'get_paypal_defense_intel', 'PAYPAL_DEFENSE_INTEL',
    # 3DS 2.0 Intelligence
    'get_3ds_v2_intelligence', 'THREE_DS_INITIATORS', 'THREE_DS_2_INTELLIGENCE',
    # Lucid VPN (Zero-Signature Network)
    'LucidVPN', 'VPNConfig', 'VPNMode', 'VPNStatus',
    'get_active_connection',
    # Purchase History Engine
    'PurchaseHistoryEngine', 'CardHolderData', 'PurchaseHistoryConfig', 'inject_purchase_history',
    # Cerberus Enhanced (AVS, BIN Scoring, Silent Validation)
    'AVSEngine', 'BINScoringEngine', 'SilentValidationEngine', 'GeoMatchChecker',
    'check_avs', 'score_bin', 'get_silent_strategy', 'check_geo',
    # OSINT Verification Framework
    'OSINTVerifier', 'OSINTReport', 'OSINTVerificationResult',
    # Card Quality Grading (PREMIUM/DEGRADED/LOW)
    'CardQualityGrader', 'CardQualityGrade', 'CardQualityReport',
    # KYC Enhanced (Document Injection, Liveness Bypass)
    'KYCEnhancedController', 'KYCSessionConfig', 'DocumentAsset', 'FaceAsset',
    'LivenessChallenge', 'KYCProvider', 'DocumentType', 'create_kyc_session',
    # Trajectory Modeling (Cognitive Warm-up)
    'TrajectoryPlanner', 'WarmupTrajectoryPlan', 'generate_warmup_trajectory',
    # Kill Switch (Panic Sequence)
    'KillSwitch', 'KillSwitchConfig', 'ThreatLevel', 'arm_kill_switch', 'send_panic_signal',
    # Font Sanitization
    'FontSanitizer', 'FontTargetOS', 'sanitize_fonts', 'check_fonts',
    # Audio Stack Nullification
    'AudioHardener', 'AudioTargetOS', 'harden_audio',
    # Timezone Atomicity
    'TimezoneEnforcer', 'TimezoneConfig', 'enforce_timezone', 'get_timezone_for_state',
    # Advanced Profile Generator
    'AdvancedProfileGenerator', 'AdvancedProfileConfig',
    # Target Presets (site-specific configs)
    'TARGET_PRESETS', 'get_target_preset', 'list_target_presets', 'SiteTargetPreset',
    # Form Autofill Injector
    'FormAutofillInjector',
    # Ring 0 <-> Ring 3 Netlink Bridge
    'NetlinkHWBridge',
    # Deep Identity Verification
    'verify_font_hygiene', 'verify_audio_hardening', 'verify_timezone_sync',
    # Linux Location Spoofer
    'LinuxLocationSpoofer', 'LocationProfile', 'GeoCoordinates',
    # Configuration Management
    'load_env', 'get_config', 'is_configured', 'get_config_status',
    # V7.0 TLS Hello Parroting (JA4+ Evasion)
    'TLSParrotEngine', 'TLSTemplate', 'ParrotTarget', 'get_parrot_config',
    # V7.0 WebGL ANGLE Shim (GPU Fingerprint Standardization)
    'WebGLAngleShim', 'WebGLParams', 'GPUProfile', 'get_webgl_config',
    # V7.0 Network Micro-Jitter & Background Noise
    'NetworkJitterEngine', 'ConnectionType', 'JitterProfile', 'apply_network_jitter',
    # V7.0 Immutable OS Manager (OverlayFS + A/B Partitions)
    'ImmutableOSManager', 'ImmutableConfig', 'verify_system_integrity', 'get_boot_status',
    # V7.0 Cockpit Middleware Daemon
    'CockpitClient', 'CockpitDaemon', 'CommandAction',
    # V7.0 Cross-Device Sync (Waydroid)
    'WaydroidSyncEngine', 'SyncConfig', 'MobilePersona', 'start_cross_device_sync',
    # V7.5 Bug Reporter + Auto-Patcher Bridge
    'BugPatchBridge',
    # V7.5 Memory Pressure Manager
    'MemoryPressureManager',
    # V7.5 Singularity Enhancement Modules
    'JA4PermutationEngine',
    'IndexedDBShardSynthesizer', 'LocalStorageSynthesizer', 'StoragePersona', 'StorageShard',
    'ExemptionType', 'CardholderProfile', 'IssuerBehaviorPredictor',
    'FaceDepthGenerator', 'DepthQuality', 'FacialLandmarks', 'DepthMapConfig',
    'IssuerDeclineDefenseEngine', 'DeclineReason', 'AmountOptimizer',
    'FirstSessionBiasEliminator',
    # V7.6 Self-Hosted Tool Stack
    'TitanSelfHostedStack', 'get_self_hosted_stack',
    'GeoIPValidator', 'get_geoip_validator',
    'IPQualityChecker', 'get_ip_quality_checker',
    'ProxyHealthMonitor', 'get_proxy_health_monitor',
    'RedisClient', 'get_redis_client',
    'NtfyClient', 'get_ntfy_client',
    'TargetSiteProber', 'get_target_prober',
    'TechStackDetector', 'get_tech_detector',
    'MinIOClient', 'get_minio_client',
    # V7.6 Target Intelligence V2 — Golden Path Scoring
    'TargetIntelV2', 'get_target_intel_v2',
    'score_target_v2', 'find_golden_targets', 'get_no_3ds_psps', 'full_target_analysis',
    'PSP_3DS_BEHAVIOR', 'MCC_3DS_INTELLIGENCE', 'GEO_3DS_ENFORCEMENT',
    'TRANSACTION_TYPE_EXEMPTIONS', 'CONFIRMED_NO_3DS_PATTERNS', 'ANTIFRAUD_GAPS',
    'GoldenPathScore',
    # V7.6 3DS AI-Speed Exploit Engine
    'ThreeDSAIEngine', 'get_3ds_ai_engine',
    'get_ai_techniques', 'get_optimal_exploit_stack', 'generate_exploit_script',
    # V7.6 AI Operations Guard
    'AIOperationsGuard', 'get_operations_guard',
    'pre_op_check', 'session_health', 'checkout_assist', 'post_op_analysis',
    'GuardVerdict', 'OperationPhase', 'RiskLevel',
    # V8.0 Maximum Level Upgrades
    'SessionIPMonitor', 'create_session_ip_monitor',
    # V8.0 Autonomous Self-Improving Engine (24/7)
    'AutonomousEngine', 'get_autonomous_engine', 'start_autonomous', 'stop_autonomous',
    'get_autonomous_status', 'TaskQueue', 'TaskInput', 'MetricsDB',
    'DetectionAnalyzer', 'SelfPatcher', 'AdaptiveScheduler', 'CycleMetrics',
    # V8.1 Real-Time AI Co-Pilot
    'RealtimeCopilot', 'get_realtime_copilot', 'start_copilot', 'stop_copilot',
    'begin_op', 'end_op', 'get_guidance', 'get_dashboard',
    'OperatorPhase', 'GuidanceLevel', 'GuidanceMessage',
    'TimingIntelligence', 'MistakeDetector', 'OllamaRealtimeAdvisor',
    # P1-10 FIX: Previously missing exports
    'PaymentPreflightV2', 'PreflightResult',
    'PaymentSandboxTester', 'PaymentSuccessMetrics',
    'OperationLogger', 'get_module_health',
    # V8.1 Persona Enrichment Engine
    'PersonaEnrichmentEngine', 'DemographicProfiler', 'PurchasePatternPredictor',
    'CoherenceValidator', 'OSINTEnricher', 'DemographicProfile', 'PurchaseCategory',
    'CoherenceResult', 'AgeGroup', 'OccupationCategory', 'IncomeLevel',
    # Orphan Fix: 17 previously unregistered modules
    'UnifiedAIOrchestrator', 'AIModelSelector', 'AIPromptOptimizer', 'AIResponseValidator',
    'AIBINAnalysis', 'AIPreFlightAdvice', 'AITargetRecon', 'AI3DSStrategy',
    'AIProfileAudit', 'AIBehavioralTuning',
    'CanvasSubpixelShim', 'CPUIDShield', 'DynamicDataGenerator',
    'ForensicMonitor', 'KYCVoiceEngine', 'NetworkShieldLoader',
    'OllamaBridge', 'USBPeripheralSynth', 'WindowsFontProvisioner',
    'AgentChain', 'TitanAutoPatcher', 'AutomationOrchestrator',
    'TitanDetectionAnalyzer', 'VectorMemory', 'WebIntelCollector', 'MasterAutomation',
]
