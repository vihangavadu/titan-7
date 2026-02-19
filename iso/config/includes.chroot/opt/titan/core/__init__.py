"""
TITAN V7.0 SINGULARITY - Core Library
Reality Synthesis Suite - Shared Components

V7.0 Upgrades (Singularity):
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

__version__ = "7.0.3"
__author__ = "Dva.12"
__status__ = "SINGULARITY"
__codename__ = "REALITY_SYNTHESIS"

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
from .proxy_manager import ResidentialProxyManager, ProxyEndpoint, GeoTarget, get_active_connection
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
    get_service_manager, start_all_services, stop_all_services, get_services_status,
)

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
    # V7.0.3 3DS Bypass & Downgrade Engine
    'ThreeDSBypassEngine', 'get_3ds_bypass_score', 'get_3ds_bypass_plan',
    'get_downgrade_attacks', 'get_psd2_exemptions', 'get_psp_vulnerabilities',
    'PSP_3DS_VULNERABILITIES', 'PSD2_EXEMPTIONS', 'THREE_DS_DOWNGRADE_ATTACKS',
    # V7.0.2 Non-VBV Card Recommendation Engine
    'NonVBVRecommendationEngine', 'get_non_vbv_recommendations',
    'get_non_vbv_country_profile', 'get_easy_countries', 'get_all_non_vbv_bins',
    'COUNTRY_PROFILES', 'NON_VBV_BINS', 'COUNTRY_DIFFICULTY_RANKING',
    # V7.0.3 Target Discovery + Auto-Discovery + Bypass Scoring
    'TargetDiscovery', 'SiteProbe', 'AutoDiscovery',
    'get_easy_sites', 'get_2d_sites', 'get_shopify_sites',
    'recommend_sites', 'probe_site', 'get_site_stats', 'search_sites',
    'auto_discover', 'get_bypass_targets', 'get_downgradeable',
    'SITE_DATABASE',
    # V7.0.2 DarkWeb & Forum Intel Monitor
    'IntelMonitor', 'get_intel_sources', 'get_intel_feed',
    'get_intel_alerts', 'get_intel_settings',
    # V7.0.3 Transaction Monitor (24/7 capture + decline decoder)
    'TransactionMonitor', 'DeclineDecoder', 'decode_decline',
    'get_tx_stats', 'start_tx_monitor',
    # V7.0.3 Service Orchestrator (auto-start, daily discovery, feedback loop)
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
]
