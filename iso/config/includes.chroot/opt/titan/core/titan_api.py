#!/usr/bin/env python3
"""
TITAN V8.1 SINGULARITY — Unified REST API
═══════════════════════════════════════════════════════════════════════════════

Provides RESTful API access to all TITAN modules for programmatic integration.

ENDPOINTS:
    /api/v1/health              - System health check
    /api/v1/modules             - List available modules
    /api/v1/bridge/status       - Integration bridge status
    
    /api/v1/profile/generate    - Generate browser profile
    /api/v1/profile/validate    - Validate profile integrity
    
    /api/v1/card/validate       - Validate card with Cerberus
    /api/v1/card/score          - Score card freshness
    
    /api/v1/ja4/generate        - Generate JA4+ fingerprint
    /api/v1/tra/exemption       - Get TRA exemption strategy
    /api/v1/issuer/risk         - Calculate issuer decline risk
    /api/v1/session/synthesize  - Synthesize returning session
    /api/v1/storage/synthesize  - Synthesize IndexedDB storage
    
    /api/v1/kyc/detect          - Detect KYC provider
    /api/v1/kyc/strategy        - Get KYC bypass strategy
    /api/v1/depth/generate      - Generate ToF depth map

Usage:
    # Start server
    python titan_api.py --port 8443
    
    # Or import in your code
    from titan_api import TitanAPI
    api = TitanAPI()
    result = api.generate_ja4_fingerprint("chrome_131", "windows_11")

Author: Dva.12
Version: 8.1.0
"""

import os
import sys
import json
import logging
import asyncio
import time
import hmac
import hashlib
import secrets
import threading
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
from functools import wraps
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

# Add core to path
sys.path.insert(0, str(Path(__file__).parent))

logger = logging.getLogger("TITAN-API")


# ═══════════════════════════════════════════════════════════════════════════════
# R2-FIX: JWT-like Token Authentication + Rate Limiting + Thread Pool
# ═══════════════════════════════════════════════════════════════════════════════

# Load API secret from environment or generate ephemeral one
_API_SECRET = os.environ.get("TITAN_API_SECRET", "")
if not _API_SECRET:
    _API_SECRET = secrets.token_hex(32)
    _secret_path = Path("/opt/titan/config/.api_secret")
    try:
        _secret_path.parent.mkdir(parents=True, exist_ok=True)
        _secret_path.write_text(_API_SECRET)
        _secret_path.chmod(0o600)
        logger.info(f"[API-AUTH] Generated ephemeral API secret → {_secret_path}")
    except Exception:
        logger.warning("[API-AUTH] Could not persist API secret — using in-memory only")


def _generate_api_token(secret: str = _API_SECRET, ttl_hours: int = 24) -> str:
    """Generate a time-limited HMAC token for API authentication."""
    import base64
    expires = int(time.time()) + (ttl_hours * 3600)
    payload = f"{expires}"
    sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    token = base64.urlsafe_b64encode(f"{payload}.{sig}".encode()).decode()
    return token


def _verify_api_token(token: str, secret: str = _API_SECRET) -> bool:
    """Verify an HMAC token — checks signature and expiry."""
    import base64
    try:
        decoded = base64.urlsafe_b64decode(token.encode()).decode()
        payload, sig = decoded.rsplit(".", 1)
        expected_sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            return False
        expires = int(payload)
        return time.time() < expires
    except Exception:
        return False


class RateLimiter:
    """R2-FIX: Sliding-window rate limiter per client IP."""
    
    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: Dict[str, list] = defaultdict(list)
        self._lock = threading.Lock()
    
    def is_allowed(self, client_ip: str) -> bool:
        """Check if request is within rate limit."""
        now = time.time()
        cutoff = now - self.window_seconds
        with self._lock:
            # Prune old entries
            self._requests[client_ip] = [
                t for t in self._requests[client_ip] if t > cutoff
            ]
            if len(self._requests[client_ip]) >= self.max_requests:
                return False
            self._requests[client_ip].append(now)
            return True
    
    def get_remaining(self, client_ip: str) -> int:
        """Get remaining requests in current window."""
        now = time.time()
        cutoff = now - self.window_seconds
        with self._lock:
            active = [t for t in self._requests[client_ip] if t > cutoff]
            return max(0, self.max_requests - len(active))


# Global rate limiter and thread pool
_rate_limiter = RateLimiter(max_requests=60, window_seconds=60)
_thread_pool = ThreadPoolExecutor(max_workers=8, thread_name_prefix="titan-api")


def _get_client_ip(request_obj) -> str:
    """Extract client IP from Flask request, respecting X-Forwarded-For."""
    forwarded = request_obj.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request_obj.remote_addr or "127.0.0.1"

# Module availability flags
MODULES_AVAILABLE = {
    # Core Modules
    "integration_bridge": False,
    "genesis_core": False,
    "cerberus_core": False,
    "kyc_core": False,
    # V7.6 Architectural Modules
    "ja4_permutation": False,
    "first_session_bias": False,
    "tra_exemption": False,
    "indexeddb_lsng": False,
    "issuer_defense": False,
    "tof_depth": False,
    # Extended Modules
    "ghost_motor": False,
    "webgl_angle": False,
    "forensic_monitor": False,
    "form_autofill": False,
    "network_jitter": False,
    "referrer_warmup": False,
    "kyc_enhanced": False,
    "kyc_voice": False,
    "usb_synth": False,
    "deep_identity": False,
    "dynamic_data": False,
    "intel_monitor": False,
    "master_verify": False,
    "handover": False,
    "preflight": False,
    "three_ds_strategy": False,
    "target_intelligence": False,
    "ai_engine": False,
    # Full Codebase Connectivity
    "advanced_profile_gen": False,
    "audio_hardener": False,
    "bug_patch_bridge": False,
    "canvas_subpixel_shim": False,
    "cerberus_enhanced": False,
    "cockpit_daemon": False,
    "cognitive_core": False,
    "cpuid_rdtsc_shield": False,
    "fingerprint_injector": False,
    "font_sanitizer": False,
    "trajectory_model": False,
    "immutable_os": False,
    "kill_switch": False,
    "location_spoofer": False,
    "lucid_vpn": False,
    "network_shield": False,
    "ollama_bridge": False,
    "proxy_manager": False,
    "purchase_history": False,
    "quic_proxy": False,
    "target_discovery": False,
    "target_presets": False,
    "timezone_enforcer": False,
    "titan_services": False,
    "tls_parrot": False,
    "transaction_monitor": False,
    "waydroid_sync": False,
    "windows_font_prov": False,
    # V8.0 Autonomous Engine
    "autonomous_engine": False,
    # V8.1 Persona Enrichment
    "persona_enrichment": False,
}

# Import modules with availability tracking
try:
    from integration_bridge import (
        TitanIntegrationBridge, BridgeConfig, create_bridge,
        get_bridge_health_monitor, get_module_discovery,
        get_integration_analytics, get_cross_module_sync,
    )
    MODULES_AVAILABLE["integration_bridge"] = True
except ImportError as e:
    logger.warning(f"Integration bridge not available: {e}")

try:
    from genesis_core import GenesisEngine, ProfileConfig, GeneratedProfile
    MODULES_AVAILABLE["genesis_core"] = True
except ImportError as e:
    logger.warning(f"Genesis core not available: {e}")

try:
    from cerberus_core import CerberusValidator, CardAsset, ValidationResult
    MODULES_AVAILABLE["cerberus_core"] = True
except ImportError as e:
    logger.warning(f"Cerberus core not available: {e}")

try:
    from kyc_core import (
        KYCController, KYCProviderDetector, LivenessDetectionBypass,
        detect_kyc_provider, get_kyc_bypass_strategy,
    )
    MODULES_AVAILABLE["kyc_core"] = True
except ImportError as e:
    logger.warning(f"KYC core not available: {e}")

try:
    from ja4_permutation_engine import (
        JA4PermutationEngine, BrowserTarget, OSTarget,
        PermutationConfig, TLSFingerprint,
    )
    MODULES_AVAILABLE["ja4_permutation"] = True
except ImportError as e:
    logger.warning(f"JA4 permutation not available: {e}")

try:
    from first_session_bias_eliminator import (
        FirstSessionEliminator, IdentityMaturity, SessionType,
    )
    MODULES_AVAILABLE["first_session_bias"] = True
except ImportError as e:
    logger.warning(f"First session bias not available: {e}")

try:
    from tra_exemption_engine import (
        TRAExemptionEngine, ExemptionType, CardholderProfile,
    )
    MODULES_AVAILABLE["tra_exemption"] = True
except ImportError as e:
    logger.warning(f"TRA exemption not available: {e}")

try:
    from indexeddb_lsng_synthesis import (
        IndexedDBSynthesizer, StoragePersona, LSNGProfile,
    )
    MODULES_AVAILABLE["indexeddb_lsng"] = True
except ImportError as e:
    logger.warning(f"IndexedDB LSNG not available: {e}")

try:
    from issuer_algo_defense import (
        IssuerDefenseEngine, DeclineReason, RiskMitigation,
    )
    MODULES_AVAILABLE["issuer_defense"] = True
except ImportError as e:
    logger.warning(f"Issuer defense not available: {e}")

try:
    from tof_depth_synthesis import (
        ToFDepthSynthesizer, SensorType, DepthQuality,
    )
    MODULES_AVAILABLE["tof_depth"] = True
except ImportError as e:
    logger.warning(f"ToF depth not available: {e}")

# Extended Module Imports
try:
    from ghost_motor_v6 import GhostMotorEngine, HumanBehaviorProfile
    MODULES_AVAILABLE["ghost_motor"] = True
except ImportError:
    pass

try:
    from webgl_angle import WebGLAngleEngine, AngleConfig
    MODULES_AVAILABLE["webgl_angle"] = True
except ImportError:
    pass

try:
    from forensic_monitor import ForensicMonitor, ForensicConfig
    MODULES_AVAILABLE["forensic_monitor"] = True
except ImportError:
    pass

try:
    from form_autofill_injector import FormAutofillInjector, AutofillProfile
    MODULES_AVAILABLE["form_autofill"] = True
except ImportError:
    pass

try:
    from network_jitter import NetworkJitterEngine, JitterProfile
    MODULES_AVAILABLE["network_jitter"] = True
except ImportError:
    pass

try:
    from referrer_warmup import ReferrerWarmupEngine, WarmupConfig
    MODULES_AVAILABLE["referrer_warmup"] = True
except ImportError:
    pass

try:
    from kyc_enhanced import KYCEnhancedEngine, EnhancedKYCConfig
    MODULES_AVAILABLE["kyc_enhanced"] = True
except ImportError:
    pass

try:
    from kyc_voice_engine import KYCVoiceEngine, VoiceProfile
    MODULES_AVAILABLE["kyc_voice"] = True
except ImportError:
    pass

try:
    from usb_peripheral_synth import USBPeripheralSynth, PeripheralConfig
    MODULES_AVAILABLE["usb_synth"] = True
except ImportError:
    pass

try:
    from verify_deep_identity import DeepIdentityVerifier, IdentityConfig
    MODULES_AVAILABLE["deep_identity"] = True
except ImportError:
    pass

try:
    from dynamic_data import DynamicDataEngine, DataConfig
    MODULES_AVAILABLE["dynamic_data"] = True
except ImportError:
    pass

try:
    from intel_monitor import IntelMonitor, IntelConfig
    MODULES_AVAILABLE["intel_monitor"] = True
except ImportError:
    pass

try:
    from titan_master_verify import MasterVerifier, VerifyConfig
    MODULES_AVAILABLE["master_verify"] = True
except ImportError:
    pass

try:
    from handover_protocol import HandoverProtocol, HandoverDocument
    MODULES_AVAILABLE["handover"] = True
except ImportError:
    pass

try:
    from preflight_validator import PreFlightValidator, ValidationReport
    MODULES_AVAILABLE["preflight"] = True
except ImportError:
    pass

try:
    from three_ds_strategy import ThreeDSBypassEngine, get_3ds_bypass_score
    MODULES_AVAILABLE["three_ds_strategy"] = True
except ImportError:
    pass

try:
    from target_intelligence import get_avs_intelligence, get_proxy_intelligence
    MODULES_AVAILABLE["target_intelligence"] = True
except ImportError:
    pass

try:
    from ai_intelligence_engine import analyze_bin, recon_target, plan_operation
    MODULES_AVAILABLE["ai_engine"] = True
except ImportError:
    pass

# ═══════════════════════════════════════════════════════════════════════════
# FULL CODEBASE CONNECTIVITY — Remaining 28 Core Modules
# ═══════════════════════════════════════════════════════════════════════════

try:
    from advanced_profile_generator import AdvancedProfileGenerator
    MODULES_AVAILABLE["advanced_profile_gen"] = True
except ImportError:
    pass

try:
    from audio_hardener import AudioHardener
    MODULES_AVAILABLE["audio_hardener"] = True
except ImportError:
    pass

try:
    from bug_patch_bridge import BugPatchBridge
    MODULES_AVAILABLE["bug_patch_bridge"] = True
except ImportError:
    pass

try:
    from canvas_subpixel_shim import CanvasSubpixelShim
    MODULES_AVAILABLE["canvas_subpixel_shim"] = True
except ImportError:
    pass

try:
    from cerberus_enhanced import CerberusEnhancedEngine
    MODULES_AVAILABLE["cerberus_enhanced"] = True
except ImportError:
    pass

try:
    from cockpit_daemon import CockpitDaemon
    MODULES_AVAILABLE["cockpit_daemon"] = True
except ImportError:
    pass

try:
    from cognitive_core import TitanCognitiveCore
    MODULES_AVAILABLE["cognitive_core"] = True
except ImportError:
    pass

try:
    from cpuid_rdtsc_shield import CPUIDRDTSCShield
    MODULES_AVAILABLE["cpuid_rdtsc_shield"] = True
except ImportError:
    pass

try:
    from fingerprint_injector import FingerprintInjector
    MODULES_AVAILABLE["fingerprint_injector"] = True
except ImportError:
    pass

try:
    from font_sanitizer import FontSanitizer
    MODULES_AVAILABLE["font_sanitizer"] = True
except ImportError:
    pass

try:
    from generate_trajectory_model import TrajectoryModelGenerator
    MODULES_AVAILABLE["trajectory_model"] = True
except ImportError:
    pass

try:
    from immutable_os import ImmutableOS
    MODULES_AVAILABLE["immutable_os"] = True
except ImportError:
    pass

try:
    from kill_switch import KillSwitch
    MODULES_AVAILABLE["kill_switch"] = True
except ImportError:
    pass

try:
    from location_spoofer_linux import LocationSpoofer
    MODULES_AVAILABLE["location_spoofer"] = True
except ImportError:
    pass

try:
    from lucid_vpn import LucidVPN
    MODULES_AVAILABLE["lucid_vpn"] = True
except ImportError:
    pass

try:
    from network_shield_loader import NetworkShieldLoader
    MODULES_AVAILABLE["network_shield"] = True
except ImportError:
    pass

try:
    from ollama_bridge import OllamaBridge
    MODULES_AVAILABLE["ollama_bridge"] = True
except ImportError:
    pass

try:
    from proxy_manager import ProxyManager
    MODULES_AVAILABLE["proxy_manager"] = True
except ImportError:
    pass

try:
    from purchase_history_engine import PurchaseHistoryEngine
    MODULES_AVAILABLE["purchase_history"] = True
except ImportError:
    pass

try:
    from quic_proxy import QUICProxyEngine
    MODULES_AVAILABLE["quic_proxy"] = True
except ImportError:
    pass

try:
    from target_discovery import TargetDiscovery
    MODULES_AVAILABLE["target_discovery"] = True
except ImportError:
    pass

try:
    from target_presets import TargetPresets
    MODULES_AVAILABLE["target_presets"] = True
except ImportError:
    pass

try:
    from timezone_enforcer import TimezoneEnforcer
    MODULES_AVAILABLE["timezone_enforcer"] = True
except ImportError:
    pass

try:
    from titan_services import TitanServiceManager
    MODULES_AVAILABLE["titan_services"] = True
except ImportError:
    pass

try:
    from tls_parrot import TLSParrot
    MODULES_AVAILABLE["tls_parrot"] = True
except ImportError:
    pass

try:
    from transaction_monitor import TransactionMonitor
    MODULES_AVAILABLE["transaction_monitor"] = True
except ImportError:
    pass

try:
    from waydroid_sync import WaydroidSync
    MODULES_AVAILABLE["waydroid_sync"] = True
except ImportError:
    pass

try:
    from windows_font_provisioner import WindowsFontProvisioner
    MODULES_AVAILABLE["windows_font_prov"] = True
except ImportError:
    pass

# V8.0 Autonomous Engine
try:
    from titan_autonomous_engine import (
        AutonomousEngine, get_autonomous_engine, start_autonomous,
        stop_autonomous, get_autonomous_status
    )
    MODULES_AVAILABLE["autonomous_engine"] = True
except ImportError:
    pass

# V8.1 Persona Enrichment Engine
try:
    from persona_enrichment_engine import (
        PersonaEnrichmentEngine, DemographicProfiler, PurchasePatternPredictor,
        CoherenceValidator, DemographicProfile, CoherenceResult,
    )
    MODULES_AVAILABLE["persona_enrichment"] = True
except ImportError:
    pass


@dataclass
class APIResponse:
    """Standard API response structure"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)


class TitanAPI:
    """
    TITAN V8.0 Unified API
    
    Provides programmatic access to all TITAN modules.
    Can be used standalone or integrated with Flask/FastAPI.
    """
    
    VERSION = "8.1.0"
    
    def __init__(self, profile_uuid: str = None):
        """
        Initialize TITAN API.
        
        Args:
            profile_uuid: Optional profile UUID for session context
        """
        self.profile_uuid = profile_uuid or f"api-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self._bridge = None
        self._engines = {}
        self._initialize_engines()
    
    def _initialize_engines(self):
        """Initialize available engines."""
        # Integration Bridge
        if MODULES_AVAILABLE["integration_bridge"]:
            try:
                config = BridgeConfig(profile_uuid=self.profile_uuid)
                self._bridge = TitanIntegrationBridge(config)
                self._bridge.initialize()
            except Exception as e:
                logger.warning(f"Bridge initialization failed: {e}")
        
        # JA4 Engine
        if MODULES_AVAILABLE["ja4_permutation"]:
            try:
                self._engines["ja4"] = JA4PermutationEngine()
            except Exception:
                pass
        
        # First Session Bias Eliminator
        if MODULES_AVAILABLE["first_session_bias"]:
            try:
                self._engines["fsb"] = FirstSessionEliminator()
            except Exception:
                pass
        
        # TRA Exemption Engine
        if MODULES_AVAILABLE["tra_exemption"]:
            try:
                self._engines["tra"] = TRAExemptionEngine()
            except Exception:
                pass
        
        # IndexedDB Synthesizer
        if MODULES_AVAILABLE["indexeddb_lsng"]:
            try:
                self._engines["lsng"] = IndexedDBSynthesizer()
            except Exception:
                pass
        
        # Issuer Defense Engine
        if MODULES_AVAILABLE["issuer_defense"]:
            try:
                self._engines["issuer"] = IssuerDefenseEngine()
            except Exception:
                pass
        
        # ToF Depth Synthesizer
        if MODULES_AVAILABLE["tof_depth"]:
            try:
                self._engines["tof"] = ToFDepthSynthesizer()
            except Exception:
                pass
    
    # ═══════════════════════════════════════════════════════════════════════════
    # HEALTH & STATUS ENDPOINTS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def health(self) -> APIResponse:
        """Get system health status."""
        active_modules = sum(1 for v in MODULES_AVAILABLE.values() if v)
        total_modules = len(MODULES_AVAILABLE)
        
        return APIResponse(
            success=True,
            data={
                "status": "healthy" if active_modules > 5 else "degraded",
                "version": self.VERSION,
                "profile_uuid": self.profile_uuid,
                "modules_active": active_modules,
                "modules_total": total_modules,
                "bridge_initialized": self._bridge is not None and self._bridge.initialized,
            }
        )
    
    def list_modules(self) -> APIResponse:
        """List all available modules."""
        return APIResponse(
            success=True,
            data={
                "modules": MODULES_AVAILABLE,
                "engines_loaded": list(self._engines.keys()),
            }
        )
    
    def bridge_status(self) -> APIResponse:
        """Get integration bridge status."""
        if not self._bridge:
            return APIResponse(success=False, error="Bridge not initialized")
        
        try:
            v76_status = self._bridge.get_v76_module_status()
            return APIResponse(
                success=True,
                data={
                    "initialized": self._bridge.initialized,
                    "v76_modules": v76_status,
                    "profile_uuid": self.profile_uuid,
                }
            )
        except Exception as e:
            return APIResponse(success=False, error=str(e))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # JA4+ PERMUTATION ENDPOINTS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def generate_ja4_fingerprint(
        self,
        browser: str = "chrome_131",
        os_target: str = "windows_11",
        enable_grease: bool = True,
        shuffle_extensions: bool = True,
    ) -> APIResponse:
        """
        Generate JA4+ TLS fingerprint.
        
        Args:
            browser: Target browser (chrome_131, firefox_133, edge_131, safari_17)
            os_target: Target OS (windows_11, windows_10, macos_14, macos_13)
            enable_grease: Enable GREASE value injection
            shuffle_extensions: Shuffle TLS extension order
        """
        if not MODULES_AVAILABLE["ja4_permutation"]:
            return APIResponse(success=False, error="JA4 permutation module not available")
        
        try:
            browser_enum = BrowserTarget(browser)
            os_enum = OSTarget(os_target)
            config = PermutationConfig(
                enable_grease=enable_grease,
                shuffle_extensions=shuffle_extensions,
            )
            
            engine = self._engines.get("ja4")
            if not engine:
                engine = JA4PermutationEngine()
            
            fingerprint = engine.generate(browser_enum, os_enum, config)
            
            return APIResponse(
                success=True,
                data={
                    "ja3_hash": fingerprint.ja3_hash,
                    "ja4_hash": fingerprint.ja4_hash,
                    "ja4h_hash": fingerprint.ja4h_hash,
                    "tls_version": fingerprint.tls_version,
                    "cipher_count": len(fingerprint.cipher_suites),
                    "extension_count": len(fingerprint.extensions),
                    "grease_count": len(fingerprint.grease_values),
                    "alpn": fingerprint.alpn_protocols,
                }
            )
        except Exception as e:
            return APIResponse(success=False, error=str(e))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # TRA EXEMPTION ENDPOINTS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_tra_exemption(
        self,
        amount: float,
        currency: str = "EUR",
        issuer_country: str = "US",
        merchant_country: str = "US",
    ) -> APIResponse:
        """
        Get optimal TRA exemption strategy.
        
        Args:
            amount: Transaction amount
            currency: Currency code
            issuer_country: Card issuer country
            merchant_country: Merchant country
        """
        if not MODULES_AVAILABLE["tra_exemption"]:
            return APIResponse(success=False, error="TRA exemption module not available")
        
        try:
            engine = self._engines.get("tra")
            if not engine:
                engine = TRAExemptionEngine()
            
            result = engine.get_optimal_exemption(amount, currency, issuer_country, merchant_country)
            
            return APIResponse(
                success=True,
                data={
                    "exemption_type": result.type.value,
                    "success_probability": result.success_rate,
                    "rationale": result.rationale,
                    "steps": result.steps,
                    "risk_score": result.risk_score,
                }
            )
        except Exception as e:
            return APIResponse(success=False, error=str(e))
    
    def calculate_tra_score(
        self,
        amount: float,
        issuer_country: str = "US",
    ) -> APIResponse:
        """Calculate TRA risk score for transaction."""
        if not MODULES_AVAILABLE["tra_exemption"]:
            return APIResponse(success=False, error="TRA exemption module not available")
        
        try:
            engine = self._engines.get("tra")
            if not engine:
                engine = TRAExemptionEngine()
            
            score = engine.calculate_score(amount, issuer_country)
            
            return APIResponse(
                success=True,
                data={
                    "score": score,
                    "risk_level": "low" if score < 30 else "medium" if score < 60 else "high",
                    "frictionless_likely": score < 40,
                }
            )
        except Exception as e:
            return APIResponse(success=False, error=str(e))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ISSUER DEFENSE ENDPOINTS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def calculate_issuer_risk(
        self,
        bin_value: str,
        amount: float,
        mcc: str = "5411",
    ) -> APIResponse:
        """
        Calculate issuer decline risk.
        
        Args:
            bin_value: Card BIN (6-8 digits)
            amount: Transaction amount
            mcc: Merchant Category Code
        """
        if not MODULES_AVAILABLE["issuer_defense"]:
            return APIResponse(success=False, error="Issuer defense module not available")
        
        try:
            engine = self._engines.get("issuer")
            if not engine:
                engine = IssuerDefenseEngine()
            
            risk = engine.calculate_risk(bin_value, amount, mcc)
            
            return APIResponse(
                success=True,
                data={
                    "risk_score": risk.score,
                    "decline_probability": risk.decline_probability,
                    "risk_factors": risk.factors,
                    "recommended_mitigation": risk.mitigation.value if risk.mitigation else None,
                }
            )
        except Exception as e:
            return APIResponse(success=False, error=str(e))
    
    def get_mitigation_strategy(
        self,
        bin_value: str,
        amount: float,
    ) -> APIResponse:
        """Get mitigation strategy for issuer declines."""
        if not MODULES_AVAILABLE["issuer_defense"]:
            return APIResponse(success=False, error="Issuer defense module not available")
        
        try:
            engine = self._engines.get("issuer")
            if not engine:
                engine = IssuerDefenseEngine()
            
            strategy = engine.get_mitigation(bin_value, amount)
            
            return APIResponse(
                success=True,
                data={
                    "primary_strategy": strategy.primary.value,
                    "risk_reduction": strategy.risk_reduction,
                    "actions": strategy.actions,
                    "best_timing": {
                        "days": strategy.best_days,
                        "hours": strategy.best_hours,
                    },
                }
            )
        except Exception as e:
            return APIResponse(success=False, error=str(e))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SESSION BIAS ENDPOINTS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def synthesize_session(
        self,
        profile_path: str,
        maturity: str = "mature",
        session_type: str = "returning",
    ) -> APIResponse:
        """
        Synthesize returning user session signals.
        
        Args:
            profile_path: Path to browser profile
            maturity: Identity maturity (mature, established, young, new, fresh)
            session_type: Session type (returning, frequent, power_user, first_visit)
        """
        if not MODULES_AVAILABLE["first_session_bias"]:
            return APIResponse(success=False, error="First session bias module not available")
        
        try:
            engine = self._engines.get("fsb")
            if not engine:
                engine = FirstSessionEliminator()
            
            maturity_enum = IdentityMaturity(maturity)
            session_enum = SessionType(session_type)
            
            result = engine.synthesize(profile_path, maturity_enum, session_enum)
            
            return APIResponse(
                success=True,
                data={
                    "profile_path": profile_path,
                    "maturity": maturity,
                    "session_type": session_type,
                    "components_synthesized": result.components,
                    "bias_reduction": result.bias_reduction,
                }
            )
        except Exception as e:
            return APIResponse(success=False, error=str(e))
    
    def calculate_identity_age_score(
        self,
        maturity: str = "mature",
    ) -> APIResponse:
        """Calculate identity age score."""
        if not MODULES_AVAILABLE["first_session_bias"]:
            return APIResponse(success=False, error="First session bias module not available")
        
        try:
            engine = self._engines.get("fsb")
            if not engine:
                engine = FirstSessionEliminator()
            
            maturity_enum = IdentityMaturity(maturity)
            score = engine.calculate_age_score(maturity_enum)
            
            risk_level = "low" if score >= 80 else "medium" if score >= 50 else "high"
            
            return APIResponse(
                success=True,
                data={
                    "maturity": maturity,
                    "score": score,
                    "risk_level": risk_level,
                }
            )
        except Exception as e:
            return APIResponse(success=False, error=str(e))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # STORAGE SYNTHESIS ENDPOINTS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def synthesize_storage(
        self,
        profile_path: str,
        persona: str = "power",
        age_days: int = 90,
        size_mb: int = 500,
    ) -> APIResponse:
        """
        Synthesize IndexedDB storage for profile.
        
        Args:
            profile_path: Path to browser profile
            persona: Storage persona (power, casual, developer, business, gamer, trader)
            age_days: Simulated storage age in days
            size_mb: Target storage size in MB
        """
        if not MODULES_AVAILABLE["indexeddb_lsng"]:
            return APIResponse(success=False, error="IndexedDB LSNG module not available")
        
        try:
            engine = self._engines.get("lsng")
            if not engine:
                engine = IndexedDBSynthesizer()
            
            persona_enum = StoragePersona(persona)
            result = engine.synthesize(profile_path, persona_enum, age_days, size_mb)
            
            return APIResponse(
                success=True,
                data={
                    "profile_path": profile_path,
                    "persona": persona,
                    "age_days": age_days,
                    "target_size_mb": size_mb,
                    "actual_size_mb": result.total_size_mb,
                    "origins_created": result.total_origins,
                    "shards_created": len(result.shards),
                }
            )
        except Exception as e:
            return APIResponse(success=False, error=str(e))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # KYC ENDPOINTS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def detect_kyc_provider(
        self,
        html_content: str,
    ) -> APIResponse:
        """
        Detect KYC provider from page HTML.
        
        Args:
            html_content: Page HTML content
        """
        if not MODULES_AVAILABLE["kyc_core"]:
            return APIResponse(success=False, error="KYC core module not available")
        
        try:
            provider, confidence = detect_kyc_provider(html_content)
            
            return APIResponse(
                success=True,
                data={
                    "provider": provider,
                    "confidence": confidence,
                }
            )
        except Exception as e:
            return APIResponse(success=False, error=str(e))
    
    def get_kyc_bypass_strategy(
        self,
        provider: str,
    ) -> APIResponse:
        """
        Get KYC bypass strategy for provider.
        
        Args:
            provider: KYC provider name (onfido, jumio, veriff, sumsub, etc.)
        """
        if not MODULES_AVAILABLE["kyc_core"]:
            return APIResponse(success=False, error="KYC core module not available")
        
        try:
            strategy = get_kyc_bypass_strategy(provider)
            
            return APIResponse(
                success=True,
                data=strategy,
            )
        except Exception as e:
            return APIResponse(success=False, error=str(e))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # TOF DEPTH ENDPOINTS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def generate_depth_map(
        self,
        image_path: str,
        sensor: str = "truedepth",
        quality: str = "high",
    ) -> APIResponse:
        """
        Generate 3D depth map for KYC liveness.
        
        Args:
            image_path: Path to face image
            sensor: Target sensor (truedepth, tof, stereo, lidar, ir_dot)
            quality: Depth quality (ultra, high, medium, low)
        """
        if not MODULES_AVAILABLE["tof_depth"]:
            return APIResponse(success=False, error="ToF depth module not available")
        
        try:
            engine = self._engines.get("tof")
            if not engine:
                engine = ToFDepthSynthesizer()
            
            sensor_enum = SensorType(sensor)
            quality_enum = DepthQuality(quality)
            
            result = engine.generate(image_path, sensor_enum, quality_enum)
            
            return APIResponse(
                success=True,
                data={
                    "source_image": image_path,
                    "sensor": sensor,
                    "quality": quality,
                    "output_path": result.output_path,
                    "resolution": result.resolution,
                }
            )
        except Exception as e:
            return APIResponse(success=False, error=str(e))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CARD VALIDATION ENDPOINTS
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def validate_card(
        self,
        pan: str,
        exp_month: str,
        exp_year: str,
        cvv: str,
        holder_name: str = "",
    ) -> APIResponse:
        """
        Validate card using Cerberus engine.
        
        Args:
            pan: Card number
            exp_month: Expiry month (MM)
            exp_year: Expiry year (YY or YYYY)
            cvv: CVV/CVC
            holder_name: Cardholder name
        """
        if not MODULES_AVAILABLE["cerberus_core"]:
            return APIResponse(success=False, error="Cerberus core module not available")
        
        try:
            card = CardAsset(
                number=pan,
                exp_month=exp_month,
                exp_year=exp_year,
                cvv=cvv,
                holder_name=holder_name,
            )
            
            validator = CerberusValidator()
            result = await validator.validate(card)
            
            return APIResponse(
                success=True,
                data={
                    "valid": result.is_valid,
                    "status": result.status.value,
                    "bin_info": result.bin_info,
                    "3ds_likelihood": result.three_ds_likelihood,
                    "avs_required": result.avs_required,
                    "risk_score": result.risk_score,
                }
            )
        except Exception as e:
            return APIResponse(success=False, error=str(e))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PROFILE GENERATION ENDPOINTS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def generate_profile(
        self,
        persona_name: str,
        persona_email: str,
        billing_address: Dict,
        age_days: int = 90,
        storage_mb: int = 500,
    ) -> APIResponse:
        """
        Generate browser profile using Genesis engine.
        
        Args:
            persona_name: Full name
            persona_email: Email address
            billing_address: Address dict with address, city, state, zip, country
            age_days: Profile age in days
            storage_mb: Storage size in MB
        """
        if not MODULES_AVAILABLE["genesis_core"]:
            return APIResponse(success=False, error="Genesis core module not available")
        
        try:
            config = ProfileConfig(
                persona_name=persona_name,
                persona_email=persona_email,
                billing_address=billing_address,
                profile_age_days=age_days,
                localstorage_size_mb=storage_mb,
            )
            
            engine = GenesisEngine()
            profile = engine.generate(config)
            
            return APIResponse(
                success=True,
                data={
                    "profile_uuid": profile.profile_uuid,
                    "profile_path": str(profile.profile_path),
                    "created_at": profile.created_at,
                    "age_days": age_days,
                    "storage_mb": storage_mb,
                }
            )
        except Exception as e:
            return APIResponse(success=False, error=str(e))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # EXTENDED MODULE ENDPOINTS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def generate_human_trajectory(
        self,
        start_x: int = 0,
        start_y: int = 0,
        end_x: int = 500,
        end_y: int = 300,
        duration_ms: int = 800,
    ) -> APIResponse:
        """Generate human-like mouse trajectory using Ghost Motor."""
        if not MODULES_AVAILABLE["ghost_motor"]:
            return APIResponse(success=False, error="Ghost Motor module not available")
        try:
            engine = GhostMotorEngine()
            trajectory = engine.generate_trajectory(start_x, start_y, end_x, end_y, duration_ms)
            return APIResponse(success=True, data={"points": trajectory.points, "duration_ms": duration_ms})
        except Exception as e:
            return APIResponse(success=False, error=str(e))
    
    def inject_webgl_fingerprint(
        self,
        profile_path: str,
        vendor: str = "Intel Inc.",
        renderer: str = "Intel Iris OpenGL Engine",
    ) -> APIResponse:
        """Inject WebGL fingerprint into profile."""
        if not MODULES_AVAILABLE["webgl_angle"]:
            return APIResponse(success=False, error="WebGL ANGLE module not available")
        try:
            engine = WebGLAngleEngine()
            result = engine.inject(profile_path, vendor, renderer)
            return APIResponse(success=True, data={"injected": result, "vendor": vendor, "renderer": renderer})
        except Exception as e:
            return APIResponse(success=False, error=str(e))
    
    def run_preflight_check(
        self,
        profile_path: str,
        target_domain: str = "",
    ) -> APIResponse:
        """Run preflight validation checks."""
        if not MODULES_AVAILABLE["preflight"]:
            return APIResponse(success=False, error="Preflight validator not available")
        try:
            validator = PreFlightValidator()
            report = validator.validate(profile_path, target_domain)
            return APIResponse(success=True, data={
                "passed": report.passed,
                "checks": report.checks,
                "warnings": report.warnings,
                "errors": report.errors,
            })
        except Exception as e:
            return APIResponse(success=False, error=str(e))
    
    def get_3ds_bypass_score(
        self,
        bin_value: str,
        amount: float,
        merchant: str = "",
    ) -> APIResponse:
        """Calculate 3DS bypass likelihood score."""
        if not MODULES_AVAILABLE["three_ds_strategy"]:
            return APIResponse(success=False, error="3DS strategy module not available")
        try:
            score = get_3ds_bypass_score(bin_value, amount, merchant)
            return APIResponse(success=True, data={
                "bypass_score": score.score,
                "likelihood": score.likelihood,
                "strategy": score.recommended_strategy,
            })
        except Exception as e:
            return APIResponse(success=False, error=str(e))
    
    def get_avs_intelligence(
        self,
        target: str,
    ) -> APIResponse:
        """Get AVS intelligence for target."""
        if not MODULES_AVAILABLE["target_intelligence"]:
            return APIResponse(success=False, error="Target intelligence module not available")
        try:
            intel = get_avs_intelligence(target)
            return APIResponse(success=True, data=intel)
        except Exception as e:
            return APIResponse(success=False, error=str(e))
    
    def analyze_bin_ai(
        self,
        bin_value: str,
    ) -> APIResponse:
        """AI-powered BIN analysis."""
        if not MODULES_AVAILABLE["ai_engine"]:
            return APIResponse(success=False, error="AI engine not available")
        try:
            analysis = analyze_bin(bin_value)
            return APIResponse(success=True, data=analysis)
        except Exception as e:
            return APIResponse(success=False, error=str(e))
    
    def plan_operation_ai(
        self,
        target: str,
        card_bin: str,
        amount: float,
    ) -> APIResponse:
        """AI-powered operation planning."""
        if not MODULES_AVAILABLE["ai_engine"]:
            return APIResponse(success=False, error="AI engine not available")
        try:
            plan = plan_operation(target, card_bin, amount)
            return APIResponse(success=True, data={
                "target": target,
                "risk_level": plan.risk_level.value if hasattr(plan.risk_level, 'value') else str(plan.risk_level),
                "steps": plan.steps,
                "recommendations": plan.recommendations,
            })
        except Exception as e:
            return APIResponse(success=False, error=str(e))
    
    def run_master_verify(
        self,
        profile_path: str = "",
    ) -> APIResponse:
        """Run master verification on system/profile."""
        if not MODULES_AVAILABLE["master_verify"]:
            return APIResponse(success=False, error="Master verifier not available")
        try:
            verifier = MasterVerifier()
            result = verifier.verify(profile_path)
            return APIResponse(success=True, data={
                "verified": result.verified,
                "score": result.score,
                "issues": result.issues,
            })
        except Exception as e:
            return APIResponse(success=False, error=str(e))
    
    def generate_handover(
        self,
        profile_uuid: str,
        target: str,
        card_last4: str,
    ) -> APIResponse:
        """Generate operator handover document."""
        if not MODULES_AVAILABLE["handover"]:
            return APIResponse(success=False, error="Handover protocol not available")
        try:
            protocol = HandoverProtocol()
            doc = protocol.generate(profile_uuid, target, card_last4)
            return APIResponse(success=True, data={
                "document_path": str(doc.path),
                "checksum": doc.checksum,
            })
        except Exception as e:
            return APIResponse(success=False, error=str(e))
    
    def start_forensic_monitoring(
        self,
        profile_path: str,
    ) -> APIResponse:
        """Start forensic monitoring for profile."""
        if not MODULES_AVAILABLE["forensic_monitor"]:
            return APIResponse(success=False, error="Forensic monitor not available")
        try:
            monitor = ForensicMonitor()
            session_id = monitor.start(profile_path)
            return APIResponse(success=True, data={"session_id": session_id, "status": "monitoring"})
        except Exception as e:
            return APIResponse(success=False, error=str(e))
    
    def apply_network_jitter(
        self,
        min_delay_ms: int = 10,
        max_delay_ms: int = 50,
        variance: float = 0.3,
    ) -> APIResponse:
        """Apply network jitter for realism."""
        if not MODULES_AVAILABLE["network_jitter"]:
            return APIResponse(success=False, error="Network jitter not available")
        try:
            engine = NetworkJitterEngine()
            result = engine.apply(min_delay_ms, max_delay_ms, variance)
            return APIResponse(success=True, data={"applied": result, "config": {"min": min_delay_ms, "max": max_delay_ms}})
        except Exception as e:
            return APIResponse(success=False, error=str(e))
    
    def inject_autofill(
        self,
        profile_path: str,
        name: str,
        email: str,
        address: Dict,
        phone: str = "",
    ) -> APIResponse:
        """Inject form autofill data into profile."""
        if not MODULES_AVAILABLE["form_autofill"]:
            return APIResponse(success=False, error="Form autofill not available")
        try:
            injector = FormAutofillInjector()
            result = injector.inject(profile_path, name, email, address, phone)
            return APIResponse(success=True, data={"injected": result, "profile": profile_path})
        except Exception as e:
            return APIResponse(success=False, error=str(e))
    
    def run_referrer_warmup(
        self,
        profile_path: str,
        target_domain: str,
        warmup_sites: int = 10,
    ) -> APIResponse:
        """Run referrer warmup for target domain."""
        if not MODULES_AVAILABLE["referrer_warmup"]:
            return APIResponse(success=False, error="Referrer warmup not available")
        try:
            engine = ReferrerWarmupEngine()
            result = engine.run(profile_path, target_domain, warmup_sites)
            return APIResponse(success=True, data={"warmed": result, "sites_visited": warmup_sites})
        except Exception as e:
            return APIResponse(success=False, error=str(e))
    
    def generate_dynamic_identity(
        self,
        country: str = "US",
        gender: str = "random",
        age_range: str = "25-45",
    ) -> APIResponse:
        """Generate dynamic identity data."""
        if not MODULES_AVAILABLE["dynamic_data"]:
            return APIResponse(success=False, error="Dynamic data not available")
        try:
            engine = DynamicDataEngine()
            identity = engine.generate(country, gender, age_range)
            return APIResponse(success=True, data=identity)
        except Exception as e:
            return APIResponse(success=False, error=str(e))
    
    def synthesize_voice(
        self,
        text: str,
        gender: str = "male",
        accent: str = "american",
    ) -> APIResponse:
        """Synthesize voice response for KYC."""
        if not MODULES_AVAILABLE["kyc_voice"]:
            return APIResponse(success=False, error="KYC voice engine not available")
        try:
            engine = KYCVoiceEngine()
            audio_path = engine.synthesize(text, gender, accent)
            return APIResponse(success=True, data={"audio_path": str(audio_path)})
        except Exception as e:
            return APIResponse(success=False, error=str(e))

    # ═══════════════════════════════════════════════════════════════════════════
    # V8.0 AUTONOMOUS ENGINE ENDPOINTS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def autonomous_status(self) -> APIResponse:
        """Get autonomous engine status."""
        if not MODULES_AVAILABLE["autonomous_engine"]:
            return APIResponse(success=False, error="Autonomous engine not available")
        try:
            status = get_autonomous_status()
            return APIResponse(success=True, data=status)
        except Exception as e:
            return APIResponse(success=False, error=str(e))
    
    def autonomous_start(self, task_dir: str = "/opt/titan/tasks") -> APIResponse:
        """Start the autonomous engine."""
        if not MODULES_AVAILABLE["autonomous_engine"]:
            return APIResponse(success=False, error="Autonomous engine not available")
        try:
            engine = start_autonomous(task_dir)
            return APIResponse(success=True, data={
                "status": "started",
                "tasks_queued": engine.task_queue.pending_count(),
            })
        except Exception as e:
            return APIResponse(success=False, error=str(e))
    
    def autonomous_stop(self) -> APIResponse:
        """Stop the autonomous engine."""
        if not MODULES_AVAILABLE["autonomous_engine"]:
            return APIResponse(success=False, error="Autonomous engine not available")
        try:
            stop_autonomous()
            return APIResponse(success=True, data={"status": "stopped"})
        except Exception as e:
            return APIResponse(success=False, error=str(e))
    
    def autonomous_report(self) -> APIResponse:
        """Get autonomous engine daily report."""
        if not MODULES_AVAILABLE["autonomous_engine"]:
            return APIResponse(success=False, error="Autonomous engine not available")
        try:
            engine = get_autonomous_engine()
            report = engine.get_daily_report()
            return APIResponse(success=True, data=report)
        except Exception as e:
            return APIResponse(success=False, error=str(e))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # V8.1 PERSONA ENRICHMENT ENDPOINTS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def enrich_persona(
        self,
        name: str,
        email: str,
        age: int,
        address: Dict,
        target_merchant: str = "",
        target_item: str = "",
        amount: float = 0.0,
    ) -> APIResponse:
        """
        Enrich persona with demographic profiling and purchase pattern prediction.
        Optionally validates coherence against a target purchase.
        """
        if not MODULES_AVAILABLE["persona_enrichment"]:
            return APIResponse(success=False, error="Persona enrichment module not available")
        try:
            engine = PersonaEnrichmentEngine(enable_osint=False)
            profile, patterns, coherence = engine.enrich_and_validate(
                name=name, email=email, age=age, address=address,
                target_merchant=target_merchant, target_item=target_item, amount=amount,
            )
            return APIResponse(success=True, data={
                "demographic": {
                    "age_group": profile.age_group.value,
                    "occupation": profile.occupation_category.value,
                    "income_level": profile.income_level.value,
                    "tech_savvy": profile.tech_savvy,
                    "online_shopper": profile.online_shopper,
                    "gender": profile.gender,
                },
                "top_categories": [
                    {"name": cat.name, "likelihood": cat.likelihood,
                     "merchants": cat.typical_merchants[:3]}
                    for cat in list(patterns.values())[:5]
                ],
                "coherence": {
                    "coherent": coherence.coherent,
                    "likelihood": coherence.likelihood_score,
                    "category": coherence.category_match,
                    "message": coherence.warning_message,
                    "alternatives": coherence.recommended_alternatives,
                } if target_merchant else None,
            })
        except Exception as e:
            return APIResponse(success=False, error=str(e))
    
    def validate_purchase_coherence(
        self,
        name: str,
        email: str,
        age: int,
        target_merchant: str,
        target_item: str = "",
        amount: float = 0.0,
    ) -> APIResponse:
        """Quick coherence check — is this purchase consistent with this persona?"""
        if not MODULES_AVAILABLE["persona_enrichment"]:
            return APIResponse(success=False, error="Persona enrichment module not available")
        try:
            engine = PersonaEnrichmentEngine(enable_osint=False)
            _, _, coherence = engine.enrich_and_validate(
                name=name, email=email, age=age, address={},
                target_merchant=target_merchant, target_item=target_item, amount=amount,
            )
            return APIResponse(success=True, data={
                "coherent": coherence.coherent,
                "likelihood": coherence.likelihood_score,
                "category": coherence.category_match,
                "message": coherence.warning_message,
                "alternatives": coherence.recommended_alternatives,
            })
        except Exception as e:
            return APIResponse(success=False, error=str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# FLASK/FASTAPI INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════

def create_flask_app():
    """Create Flask app with TITAN API routes."""
    try:
        from flask import Flask, request, jsonify
    except ImportError:
        logger.warning("Flask not available. Install with: pip install flask")
        return None
    
    app = Flask(__name__)
    api = TitanAPI()
    
    # R2-FIX: Public endpoints that don't require auth
    PUBLIC_ENDPOINTS = {"/api/v1/health", "/api/v1/auth/token", "/api/copilot/event"}
    
    @app.before_request
    def _enforce_auth_and_rate_limit():
        """R2-FIX: Enforce JWT auth + rate limiting on all non-public endpoints."""
        # Rate limiting on ALL endpoints
        client_ip = _get_client_ip(request)
        if not _rate_limiter.is_allowed(client_ip):
            return jsonify({
                "success": False,
                "error": "Rate limit exceeded (60 req/min)",
                "retry_after_seconds": 60,
            }), 429
        
        # Skip auth for public endpoints and localhost
        if request.path in PUBLIC_ENDPOINTS:
            return None
        if client_ip in ("127.0.0.1", "::1"):
            return None
        
        # Require Bearer token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({
                "success": False,
                "error": "Missing Authorization header. Use: Bearer <token>",
                "hint": "GET /api/v1/auth/token with X-API-Secret header to obtain token",
            }), 401
        
        token = auth_header[7:]
        if not _verify_api_token(token):
            return jsonify({
                "success": False,
                "error": "Invalid or expired token",
            }), 403
    
    @app.after_request
    def _add_security_headers(response):
        """R2-FIX: Add security headers to all responses."""
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-RateLimit-Remaining"] = str(
            _rate_limiter.get_remaining(_get_client_ip(request))
        )
        return response
    
    @app.teardown_appcontext
    def _shutdown_thread_pool(exception=None):
        """R2-FIX: Ensure thread pool shuts down cleanly."""
        pass  # ThreadPoolExecutor cleanup happens at process exit
    
    # R2-FIX: Token generation endpoint
    @app.route("/api/v1/auth/token", methods=["GET"])
    def auth_token():
        """Generate API token. Requires X-API-Secret header."""
        provided_secret = request.headers.get("X-API-Secret", "")
        if not hmac.compare_digest(provided_secret, _API_SECRET):
            return jsonify({"success": False, "error": "Invalid API secret"}), 403
        ttl = int(request.args.get("ttl_hours", 24))
        ttl = min(ttl, 720)  # Max 30 days
        token = _generate_api_token(ttl_hours=ttl)
        return jsonify({
            "success": True,
            "data": {
                "token": token,
                "ttl_hours": ttl,
                "usage": "Authorization: Bearer <token>",
            }
        })
    
    @app.route("/api/v1/health", methods=["GET"])
    def health():
        return jsonify(api.health().to_dict())
    
    @app.route("/api/v1/modules", methods=["GET"])
    def modules():
        return jsonify(api.list_modules().to_dict())
    
    @app.route("/api/v1/bridge/status", methods=["GET"])
    def bridge_status():
        return jsonify(api.bridge_status().to_dict())
    
    @app.route("/api/v1/ja4/generate", methods=["POST"])
    def ja4_generate():
        data = request.get_json() or {}
        return jsonify(api.generate_ja4_fingerprint(
            browser=data.get("browser", "chrome_131"),
            os_target=data.get("os", "windows_11"),
            enable_grease=data.get("enable_grease", True),
            shuffle_extensions=data.get("shuffle_extensions", True),
        ).to_dict())
    
    @app.route("/api/v1/tra/exemption", methods=["POST"])
    def tra_exemption():
        data = request.get_json() or {}
        return jsonify(api.get_tra_exemption(
            amount=data.get("amount", 100),
            currency=data.get("currency", "EUR"),
            issuer_country=data.get("issuer_country", "US"),
        ).to_dict())
    
    @app.route("/api/v1/issuer/risk", methods=["POST"])
    def issuer_risk():
        data = request.get_json() or {}
        return jsonify(api.calculate_issuer_risk(
            bin_value=data.get("bin", "421783"),
            amount=data.get("amount", 100),
            mcc=data.get("mcc", "5411"),
        ).to_dict())
    
    @app.route("/api/v1/session/synthesize", methods=["POST"])
    def session_synthesize():
        data = request.get_json() or {}
        return jsonify(api.synthesize_session(
            profile_path=data.get("profile_path", "/opt/titan/profiles/default"),
            maturity=data.get("maturity", "mature"),
            session_type=data.get("session_type", "returning"),
        ).to_dict())
    
    @app.route("/api/v1/storage/synthesize", methods=["POST"])
    def storage_synthesize():
        data = request.get_json() or {}
        return jsonify(api.synthesize_storage(
            profile_path=data.get("profile_path", "/opt/titan/profiles/default"),
            persona=data.get("persona", "power"),
            age_days=data.get("age_days", 90),
            size_mb=data.get("size_mb", 500),
        ).to_dict())
    
    @app.route("/api/v1/kyc/detect", methods=["POST"])
    def kyc_detect():
        data = request.get_json() or {}
        return jsonify(api.detect_kyc_provider(
            html_content=data.get("html", ""),
        ).to_dict())
    
    @app.route("/api/v1/kyc/strategy", methods=["POST"])
    def kyc_strategy():
        data = request.get_json() or {}
        return jsonify(api.get_kyc_bypass_strategy(
            provider=data.get("provider", "onfido"),
        ).to_dict())
    
    @app.route("/api/v1/depth/generate", methods=["POST"])
    def depth_generate():
        data = request.get_json() or {}
        return jsonify(api.generate_depth_map(
            image_path=data.get("image_path", ""),
            sensor=data.get("sensor", "truedepth"),
            quality=data.get("quality", "high"),
        ).to_dict())
    
    # V8.1 Persona Enrichment Routes
    @app.route("/api/v1/persona/enrich", methods=["POST"])
    def persona_enrich():
        data = request.get_json() or {}
        return jsonify(api.enrich_persona(
            name=data.get("name", ""),
            email=data.get("email", ""),
            age=data.get("age", 30),
            address=data.get("address", {}),
            target_merchant=data.get("target_merchant", ""),
            target_item=data.get("target_item", ""),
            amount=data.get("amount", 0.0),
        ).to_dict())
    
    @app.route("/api/v1/persona/coherence", methods=["POST"])
    def persona_coherence():
        data = request.get_json() or {}
        return jsonify(api.validate_purchase_coherence(
            name=data.get("name", ""),
            email=data.get("email", ""),
            age=data.get("age", 30),
            target_merchant=data.get("target_merchant", ""),
            target_item=data.get("target_item", ""),
            amount=data.get("amount", 0.0),
        ).to_dict())
    
    # V8.0 Autonomous Engine Routes
    @app.route("/api/v1/autonomous/status", methods=["GET"])
    def autonomous_status():
        return jsonify(api.autonomous_status().to_dict())
    
    @app.route("/api/v1/autonomous/start", methods=["POST"])
    def autonomous_start():
        data = request.get_json() or {}
        return jsonify(api.autonomous_start(
            task_dir=data.get("task_dir", "/opt/titan/tasks"),
        ).to_dict())
    
    @app.route("/api/v1/autonomous/stop", methods=["POST"])
    def autonomous_stop():
        return jsonify(api.autonomous_stop().to_dict())
    
    @app.route("/api/v1/autonomous/report", methods=["GET"])
    def autonomous_report():
        return jsonify(api.autonomous_report().to_dict())
    
    # ═══════════════════════════════════════════════════════════════════════
    # V8.1 REAL-TIME AI CO-PILOT ROUTES
    # ═══════════════════════════════════════════════════════════════════════
    # Browser co-pilot (titan_3ds_ai_exploits.py) sends events here via
    # navigator.sendBeacon. GUI polls guidance and dashboard endpoints.
    
    @app.route("/api/copilot/event", methods=["POST"])
    def copilot_event():
        """Ingest real-time browser event from co-pilot content script."""
        try:
            from titan_realtime_copilot import get_realtime_copilot
            copilot = get_realtime_copilot()
            data = request.get_json(silent=True) or {}
            copilot.ingest_browser_event(data)
            return "", 204
        except Exception as e:
            logger.debug(f"Copilot event error: {e}")
            return "", 204  # Always 204 — sendBeacon is fire-and-forget
    
    @app.route("/api/v1/copilot/guidance", methods=["GET"])
    def copilot_guidance():
        """Get latest AI guidance messages (GUI polls this)."""
        try:
            from titan_realtime_copilot import get_realtime_copilot
            copilot = get_realtime_copilot()
            limit = request.args.get("limit", 10, type=int)
            return jsonify({"success": True, "guidance": copilot.get_latest_guidance(limit)})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})
    
    @app.route("/api/v1/copilot/dashboard", methods=["GET"])
    def copilot_dashboard():
        """Get full co-pilot dashboard status."""
        try:
            from titan_realtime_copilot import get_realtime_copilot
            return jsonify({"success": True, "dashboard": get_realtime_copilot().get_dashboard()})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})
    
    @app.route("/api/v1/copilot/begin", methods=["POST"])
    def copilot_begin():
        """Begin a new operation — runs pre-flight checks."""
        try:
            from titan_realtime_copilot import get_realtime_copilot
            copilot = get_realtime_copilot()
            data = request.get_json() or {}
            msgs = copilot.begin_operation(
                target=data.get("target", ""),
                card_bin=data.get("card_bin", ""),
                card_country=data.get("card_country", "US"),
                proxy_ip=data.get("proxy_ip", ""),
                proxy_country=data.get("proxy_country", ""),
                proxy_state=data.get("proxy_state", ""),
                billing_state=data.get("billing_state", ""),
                billing_zip=data.get("billing_zip", ""),
                amount=data.get("amount", 0.0),
                psp=data.get("psp", "unknown"),
                profile_id=data.get("profile_id", ""),
            )
            return jsonify({
                "success": True,
                "guidance": [{"level": m.level.value, "category": m.category,
                              "message": m.message, "action": m.action} for m in msgs],
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})
    
    @app.route("/api/v1/copilot/end", methods=["POST"])
    def copilot_end():
        """End current operation — runs post-analysis."""
        try:
            from titan_realtime_copilot import get_realtime_copilot
            copilot = get_realtime_copilot()
            data = request.get_json() or {}
            msgs = copilot.end_operation(
                result=data.get("result", "unknown"),
                decline_code=data.get("decline_code", ""),
            )
            return jsonify({
                "success": True,
                "analysis": [{"level": m.level.value, "category": m.category,
                              "message": m.message, "action": m.action} for m in msgs],
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})
    
    @app.route("/api/v1/copilot/timing", methods=["GET"])
    def copilot_timing():
        """Get real-time timing intelligence (checkout countdown, velocity)."""
        try:
            from titan_realtime_copilot import get_realtime_copilot
            return jsonify({"success": True, "timing": get_realtime_copilot().get_timing_status()})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})
    
    @app.route("/api/v1/copilot/history", methods=["GET"])
    def copilot_history():
        """Get operation history from this session."""
        try:
            from titan_realtime_copilot import get_realtime_copilot
            limit = request.args.get("limit", 20, type=int)
            return jsonify({
                "success": True,
                "history": get_realtime_copilot().get_operation_history(limit),
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})
    
    return app


# ═══════════════════════════════════════════════════════════════════════════════
# CLI ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Main CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="TITAN V8.1 API Server")
    parser.add_argument("--port", type=int, default=8443, help="Server port")
    parser.add_argument("--host", default="0.0.0.0", help="Server host")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()
    
    print("=" * 70)
    print("  TITAN V8.1 MAXIMUM LEVEL — Unified REST API")
    print("=" * 70)
    
    app = create_flask_app()
    if app:
        print(f"  Starting server on {args.host}:{args.port}")
        print(f"  API Endpoints: /api/v1/health, /api/v1/modules, ...")
        print("=" * 70)
        app.run(host=args.host, port=args.port, debug=args.debug)
    else:
        # Fallback: print API status directly
        api = TitanAPI()
        print("\n  Flask not available. Direct API test:")
        print(f"  Health: {api.health().to_json()}")
        print(f"  Modules: {api.list_modules().to_json()}")


if __name__ == "__main__":
    main()
