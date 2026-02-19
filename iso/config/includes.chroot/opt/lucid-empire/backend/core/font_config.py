# LUCID EMPIRE :: FONT FINGERPRINTING CONFIGURATION
# Purpose: Manage font-based fingerprinting mitigation
# V7.0: Bridges to /opt/titan/core/font_sanitizer.py for OS-level font purging

import json
import os
import sys
from typing import Dict, List, Optional

# V7.0: Bridge to Titan font sanitizer
sys.path.insert(0, "/opt/titan/core")
try:
    from font_sanitizer import FontSanitizer, TargetOS, FONT_METRICS_DATABASE, check_fonts
    TITAN_V6_AVAILABLE = True
except ImportError:
    TITAN_V6_AVAILABLE = False


class FontConfig:
    """Configure and manage font fingerprinting signatures.
    
    V7.0: Now bridges to FontSanitizer for:
    - Linux font rejection via /etc/fonts/local.conf
    - Target OS font installation
    - measureText() metric spoofing via Ghost Motor
    """
    
    def __init__(self):
        self.fonts = {}
        self.load_config()
    
    def load_config(self) -> None:
        """Load font configuration from assets"""
        config_path = os.path.join("assets", "fonts_config.json")
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                self.fonts = json.load(f)
    
    def get_common_fonts(self, os_type: str) -> List[str]:
        """Get list of common fonts for OS.
        
        V7.0: Extended with complete font lists from FontSanitizer.
        """
        if TITAN_V6_AVAILABLE:
            os_map = {
                "windows": TargetOS.WINDOWS_11,
                "windows_10": TargetOS.WINDOWS_10,
                "windows_11": TargetOS.WINDOWS_11,
                "macos": TargetOS.MACOS_14,
                "macos_14": TargetOS.MACOS_14,
                "macos_13": TargetOS.MACOS_13,
            }
            target = os_map.get(os_type.lower(), TargetOS.WINDOWS_11)
            sanitizer = FontSanitizer(target)
            return sanitizer.TARGET_FONTS.get(target.value, [])
        
        common_fonts = {
            'windows': [
                'Arial', 'Times New Roman', 'Courier New', 'Verdana',
                'Georgia', 'Trebuchet MS', 'Comic Sans MS', 'Segoe UI',
                'Tahoma', 'Calibri', 'Consolas', 'Cambria',
            ],
            'macos': [
                'Helvetica Neue', 'Helvetica', 'Times New Roman', 'Monaco',
                'Menlo', 'Courier New', 'Georgia', 'SF Pro', 'SF Mono',
            ],
            'linux': [
                'DejaVu Sans', 'DejaVu Serif', 'Courier',
                'Times', 'Liberation Sans', 'Liberation Serif'
            ]
        }
        return common_fonts.get(os_type.lower(), common_fonts['windows'])
    
    def get_font_metrics(self, font_name: str) -> Optional[Dict]:
        """Get font metrics if available.
        
        V7.0: Falls through to FontSanitizer FONT_METRICS_DATABASE
        for measureText() spoofing data.
        """
        result = self.fonts.get(font_name, None)
        if result is None and TITAN_V6_AVAILABLE:
            return FONT_METRICS_DATABASE.get(font_name, None)
        return result
    
    def inject_font_signature(self, profile: Dict, fonts: List[str]) -> None:
        """Inject font signature into profile"""
        profile['fonts'] = fonts
    
    def check_hygiene(self, target_os: str = "windows_11") -> Dict:
        """V7.0: Check font environment hygiene via FontSanitizer."""
        if TITAN_V6_AVAILABLE:
            return check_fonts(target_os)
        return {"clean": False, "error": "FontSanitizer not available"}
    
    def sanitize(self, target_os: str = "windows_11") -> bool:
        """V7.0: Run full font sanitization (requires root)."""
        if TITAN_V6_AVAILABLE:
            os_map = {
                "windows_10": TargetOS.WINDOWS_10, "windows_11": TargetOS.WINDOWS_11,
                "macos_14": TargetOS.MACOS_14, "macos_13": TargetOS.MACOS_13,
            }
            target = os_map.get(target_os, TargetOS.WINDOWS_11)
            sanitizer = FontSanitizer(target)
            result = sanitizer.apply()
            return result.get("success", False) if isinstance(result, dict) else False
        return False
