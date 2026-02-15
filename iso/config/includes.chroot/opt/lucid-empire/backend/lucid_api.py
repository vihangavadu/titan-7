# LUCID EMPIRE :: BACKEND API
# Purpose: Main API interface for backend operations
# V7.0: Bridges to /opt/titan/core for Phase 2-3 hardening modules

import sys
import logging
from typing import Dict, Optional
from backend.core import ProfileFactory, ProfileStore, CoreOrchestrator
from backend.modules import CommerceInjector, BiometricMimicry, HumanizationEngine

# V7.0: Bridge to Titan core
sys.path.insert(0, "/opt/titan/core")
TITAN_V7_AVAILABLE = False
try:
    from font_sanitizer import check_fonts
    from audio_hardener import AudioHardener, AudioTargetOS
    from timezone_enforcer import get_timezone_for_state, get_timezone_for_country
    from preflight_validator import PreFlightValidator
    TITAN_V7_AVAILABLE = True
except ImportError:
    pass


class LucidAPI:
    """Main API for Lucid Empire backend.
    
    V7.0: Extended with environment hardening and preflight validation.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.profile_store = ProfileStore()
        self.orchestrator = CoreOrchestrator()
        self.setup_modules()
    
    def setup_modules(self) -> None:
        """Register operational modules"""
        self.orchestrator.register_module('commerce', CommerceInjector())
        self.orchestrator.register_module('biometric', BiometricMimicry())
        self.orchestrator.register_module('humanizer', HumanizationEngine())
    
    def create_profile(self, seed: Dict) -> Dict:
        """Create new profile"""
        return self.profile_store.create_profile(seed)
    
    def get_profile(self, profile_id: str) -> Optional[Dict]:
        """Retrieve profile"""
        return self.profile_store.get_profile(profile_id)
    
    def list_profiles(self) -> list:
        """List all profiles"""
        return self.profile_store.get_all()
    
    def delete_profile(self, profile_id: str) -> None:
        """Delete profile"""
        self.profile_store.delete_profile(profile_id)
    
    # V7.0: Environment hardening endpoints
    
    def check_font_hygiene(self, target_os: str = "windows_11") -> Dict:
        """V7.0: Check font environment for Linux leaks."""
        if not TITAN_V7_AVAILABLE:
            return {"available": False, "error": "Titan V7.0 modules not loaded"}
        return check_fonts(target_os)
    
    def get_timezone(self, state: str = "", country: str = "US") -> str:
        """V7.0: Get timezone for state/country."""
        if not TITAN_V7_AVAILABLE:
            return "America/New_York"
        if state:
            return get_timezone_for_state(state)
        return get_timezone_for_country(country)
    
    def run_preflight(self, profile_path: str = "", proxy_url: str = "") -> Dict:
        """V7.0: Run preflight validation on profile."""
        if not TITAN_V7_AVAILABLE:
            return {"available": False, "error": "Titan V7.0 modules not loaded"}
        try:
            validator = PreFlightValidator()
            result = validator.validate(profile_path=profile_path, proxy_url=proxy_url)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_system_status(self) -> Dict:
        """V7.0: Get overall system readiness status."""
        return {
            "titan_v7_available": TITAN_V7_AVAILABLE,
            "profile_count": len(self.profile_store.get_all()),
            "modules_loaded": list(self.orchestrator.modules.keys()) if hasattr(self.orchestrator, 'modules') else [],
        }
