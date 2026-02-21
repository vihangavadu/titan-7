"""
TITAN V7.0 SINGULARITY — Phase 3.1: Font Sanitization Engine
OS-Specific Font Injection, Linux Font Rejection, Metric Spoofing

VULNERABILITY: The host OS includes Linux-exclusive fonts like 'Liberation Sans',
'DejaVu Sans', 'Noto Color Emoji'. If the profile claims Windows 10, font
enumeration via JS `document.fonts` or `measureText()` will reveal the
true OS regardless of User-Agent.

FIX:
1. Generate /etc/fonts/local.conf with <rejectfont> for Linux-specific fonts
2. Install target OS fonts into /usr/share/fonts/truetype/titan-{os}/
3. Rebuild font cache with fc-cache
4. Generate font metric overrides for measureText() spoofing
5. Write Camoufox font config to lock enumeration results

Usage:
    from font_sanitizer import FontSanitizer, TargetOS
    
    sanitizer = FontSanitizer(TargetOS.WINDOWS_11)
    sanitizer.apply()  # Generates local.conf + installs fonts + rebuilds cache
"""

import os
import json
import shutil
import subprocess
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("TITAN-V7-FONTS")


class TargetOS(Enum):
    WINDOWS_10 = "windows_10"
    WINDOWS_11 = "windows_11"
    WINDOWS_11_24H2 = "windows_11_24h2"
    MACOS_14 = "macos_14"
    MACOS_13 = "macos_13"
    MACOS_15 = "macos_15"


# ═══════════════════════════════════════════════════════════════════════════
# FONT DATABASES — Real font sets per OS
# ═══════════════════════════════════════════════════════════════════════════

# Fonts that MUST NOT be visible when spoofing a non-Linux OS
LINUX_EXCLUSIVE_FONTS = [
    "Liberation Sans", "Liberation Serif", "Liberation Mono",
    "DejaVu Sans", "DejaVu Serif", "DejaVu Sans Mono",
    "Noto Color Emoji", "Noto Sans", "Noto Serif",
    "Noto Sans CJK", "Noto Serif CJK",
    "Ubuntu", "Ubuntu Mono", "Ubuntu Condensed",
    "Cantarell", "Droid Sans", "Droid Serif",
    "FreeSans", "FreeSerif", "FreeMono",
    "Nimbus Sans", "Nimbus Roman", "Nimbus Mono",
    "STIX", "Latin Modern",
    "Bitstream Vera Sans", "Bitstream Vera Serif",
    # V7.5 FIX: Additional common Linux distribution fonts
    "Source Code Pro", "Hack", "Cantarell Light",
    "Noto Sans Mono", "Noto Sans Display",
    # V7.6: Additional Linux distribution fonts
    "Noto Sans Symbols", "Noto Sans Symbols2", "Noto Sans Math",
    "Noto Music", "Noto Sans SignWriting",
    "URW Gothic", "URW Bookman", "C059", "P052", "Z003", "D050000L",
    "Lato", "Open Sans", "Roboto",
    "Liberation Sans Narrow", "TeX Gyre Termes", "TeX Gyre Heros",
]

# Fonts that MUST be present for Windows spoofing
WINDOWS_CORE_FONTS = {
    "required": [
        "Segoe UI", "Segoe UI Semibold", "Segoe UI Light",
        "Arial", "Times New Roman", "Courier New",
        "Verdana", "Tahoma", "Georgia",
        "Trebuchet MS", "Comic Sans MS", "Impact",
        "Calibri", "Cambria", "Consolas",
        "Lucida Console", "Palatino Linotype",
    ],
    "windows_11_extras": [
        "Segoe UI Variable", "Segoe Fluent Icons",
        "Cascadia Code", "Cascadia Mono",
    ],
    "ttf_files": {
        "Segoe UI": "segoeui.ttf",
        "Segoe UI Semibold": "seguisb.ttf",
        "Segoe UI Light": "segoeuil.ttf",
        "Arial": "arial.ttf",
        "Times New Roman": "times.ttf",
        "Courier New": "cour.ttf",
        "Verdana": "verdana.ttf",
        "Tahoma": "tahoma.ttf",
        "Georgia": "georgia.ttf",
        "Trebuchet MS": "trebuc.ttf",
        "Calibri": "calibri.ttf",
        "Cambria": "cambria.ttc",
        "Consolas": "consola.ttf",
        "Comic Sans MS": "comic.ttf",
        "Impact": "impact.ttf",
    },
}

# Fonts that MUST be present for macOS spoofing
MACOS_CORE_FONTS = {
    "required": [
        "San Francisco", "SF Pro", "SF Mono",
        "Helvetica Neue", "Helvetica",
        "Arial", "Times New Roman", "Courier New",
        "Menlo", "Monaco",
        "Lucida Grande", "Geneva",
        "Avenir", "Avenir Next",
        "Futura", "Gill Sans",
        "Apple Color Emoji",
    ],
    "ttf_files": {
        "Helvetica Neue": "HelveticaNeue.ttc",
        "Menlo": "Menlo.ttc",
        "Monaco": "Monaco.ttf",
        "Lucida Grande": "LucidaGrande.ttc",
        "Avenir": "Avenir.ttc",
    },
}

# Font metrics for measureText() spoofing (width ratios relative to Arial at 16px)
FONT_METRICS_DATABASE = {
    "windows": {
        "Segoe UI": {"avg_width_ratio": 0.528, "ascent": 1.079, "descent": 0.283, "line_gap": 0.0},
        "Arial": {"avg_width_ratio": 0.552, "ascent": 1.055, "descent": 0.244, "line_gap": 0.0},
        "Calibri": {"avg_width_ratio": 0.508, "ascent": 1.060, "descent": 0.293, "line_gap": 0.0},
        "Verdana": {"avg_width_ratio": 0.602, "ascent": 1.100, "descent": 0.267, "line_gap": 0.0},
        "Tahoma": {"avg_width_ratio": 0.554, "ascent": 1.063, "descent": 0.249, "line_gap": 0.0},
        "Times New Roman": {"avg_width_ratio": 0.467, "ascent": 1.067, "descent": 0.270, "line_gap": 0.0},
        "Consolas": {"avg_width_ratio": 0.550, "ascent": 1.068, "descent": 0.282, "line_gap": 0.0},
    },
    "macos": {
        "Helvetica Neue": {"avg_width_ratio": 0.532, "ascent": 1.052, "descent": 0.259, "line_gap": 0.0},
        "San Francisco": {"avg_width_ratio": 0.528, "ascent": 1.068, "descent": 0.276, "line_gap": 0.0},
        "Menlo": {"avg_width_ratio": 0.602, "ascent": 1.125, "descent": 0.295, "line_gap": 0.0},
        "Monaco": {"avg_width_ratio": 0.602, "ascent": 1.065, "descent": 0.280, "line_gap": 0.0},
    },
}


@dataclass
class FontSanitizationResult:
    """Result of font sanitization"""
    target_os: str
    fonts_rejected: int
    fonts_installed: int
    fonts_missing: List[str]
    local_conf_written: bool
    cache_rebuilt: bool
    metric_overrides_written: bool
    clean: bool


class FontSanitizer:
    """
    Phase 3.1: Full font environment sanitization.
    
    Generates /etc/fonts/local.conf with rejectfont directives,
    manages target OS font installation, rebuilds font cache,
    and generates metric override configs for Ghost Motor.
    """
    
    FONT_INSTALL_DIR = Path("/usr/share/fonts/truetype")
    LOCAL_CONF_PATH = Path("/etc/fonts/local.conf")
    TITAN_FONT_SOURCE = Path("/opt/titan/assets/fonts")
    
    def __init__(self, target_os: TargetOS):
        self.target_os = target_os
        self.os_family = "windows" if "windows" in target_os.value else "macos"
    
    def generate_local_conf(self) -> str:
        """
        Generate /etc/fonts/local.conf with rejectfont directives
        that hide all Linux-exclusive fonts from enumeration.
        """
        reject_patterns = []
        for font in LINUX_EXCLUSIVE_FONTS:
            reject_patterns.append(f'      <pattern><patelt name="family"><string>{font}</string></patelt></pattern>')
        
        # Also add substitution rules so Linux fonts map to target OS equivalents
        if self.os_family == "windows":
            substitutions = [
                ("Liberation Sans", "Arial"),
                ("Liberation Serif", "Times New Roman"),
                ("Liberation Mono", "Courier New"),
                ("DejaVu Sans", "Segoe UI"),
                ("DejaVu Serif", "Georgia"),
                ("DejaVu Sans Mono", "Consolas"),
                ("Noto Color Emoji", "Segoe UI Emoji"),
                ("Ubuntu", "Segoe UI"),
            ]
        else:  # macOS
            substitutions = [
                ("Liberation Sans", "Helvetica Neue"),
                ("Liberation Serif", "Times New Roman"),
                ("Liberation Mono", "Menlo"),
                ("DejaVu Sans", "Helvetica Neue"),
                ("DejaVu Serif", "Georgia"),
                ("DejaVu Sans Mono", "Monaco"),
                ("Noto Color Emoji", "Apple Color Emoji"),
                ("Ubuntu", "San Francisco"),
            ]
        
        alias_entries = []
        for linux_font, target_font in substitutions:
            alias_entries.append(f"""  <alias>
    <family>{linux_font}</family>
    <prefer><family>{target_font}</family></prefer>
  </alias>""")
        
        conf = f"""<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">
<!--
  TITAN V7.0 SINGULARITY — Font Sanitization (Phase 3.1)
  Target OS: {self.target_os.value}
  Generated: {datetime.now(timezone.utc).isoformat()}
  
  Purpose: Hide Linux-exclusive fonts and substitute with target OS equivalents.
  This prevents font enumeration attacks from revealing the true OS.
-->
<fontconfig>

  <!-- ═══ PHASE 3.1: REJECT LINUX-EXCLUSIVE FONTS ═══ -->
  <selectfont>
    <rejectfont>
{chr(10).join(reject_patterns)}
    </rejectfont>
  </selectfont>

  <!-- ═══ FONT SUBSTITUTION (fallback mapping) ═══ -->
{chr(10).join(alias_entries)}

  <!-- ═══ DEFAULT FONT for {self.os_family.upper()} ═══ -->
  <alias>
    <family>sans-serif</family>
    <prefer><family>{"Segoe UI" if self.os_family == "windows" else "Helvetica Neue"}</family></prefer>
  </alias>
  <alias>
    <family>serif</family>
    <prefer><family>{"Georgia" if self.os_family == "windows" else "Times New Roman"}</family></prefer>
  </alias>
  <alias>
    <family>monospace</family>
    <prefer><family>{"Consolas" if self.os_family == "windows" else "Menlo"}</family></prefer>
  </alias>

</fontconfig>
"""
        return conf
    
    def write_local_conf(self) -> bool:
        """Write the generated local.conf to /etc/fonts/"""
        conf = self.generate_local_conf()
        try:
            self.LOCAL_CONF_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(self.LOCAL_CONF_PATH, 'w') as f:
                f.write(conf)
            logger.info(f"[PHASE 3.1] local.conf written: {len(LINUX_EXCLUSIVE_FONTS)} fonts rejected")
            return True
        except PermissionError:
            logger.error("[PHASE 3.1] Permission denied writing local.conf — run as root")
            return False
        except Exception as e:
            logger.error(f"[PHASE 3.1] local.conf write error: {e}")
            return False
    
    def install_target_fonts(self) -> int:
        """
        Install target OS fonts from the Titan font asset directory.
        Fonts must be pre-staged in /opt/titan/assets/fonts/{os}/
        """
        if self.os_family == "windows":
            font_db = WINDOWS_CORE_FONTS
            os_dir = "windows"
        else:
            font_db = MACOS_CORE_FONTS
            os_dir = "macos"
        
        source_dir = self.TITAN_FONT_SOURCE / os_dir
        target_dir = self.FONT_INSTALL_DIR / f"titan-{self.target_os.value.replace('_', '')}"
        
        installed = 0
        
        if not source_dir.exists():
            logger.warning(f"[PHASE 3.1] Font source directory not found: {source_dir}")
            logger.warning(f"[PHASE 3.1] Stage fonts manually: copy .ttf files to {source_dir}/")
            return 0
        
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            
            for ttf_file in source_dir.glob("*.tt[fc]"):
                dest = target_dir / ttf_file.name
                shutil.copy2(ttf_file, dest)
                installed += 1
            
            logger.info(f"[PHASE 3.1] Installed {installed} fonts to {target_dir}")
        except PermissionError:
            logger.error("[PHASE 3.1] Permission denied installing fonts — run as root")
        except Exception as e:
            logger.error(f"[PHASE 3.1] Font install error: {e}")
        
        return installed
    
    def rebuild_font_cache(self) -> bool:
        """Run fc-cache -f -v to rebuild the system font cache"""
        try:
            result = subprocess.run(
                ["fc-cache", "-f", "-v"],
                capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0:
                logger.info("[PHASE 3.1] Font cache rebuilt successfully")
                return True
            else:
                logger.error(f"[PHASE 3.1] fc-cache failed: {result.stderr[:200]}")
                return False
        except FileNotFoundError:
            logger.error("[PHASE 3.1] fc-cache not found — install fontconfig")
            return False
        except Exception as e:
            logger.error(f"[PHASE 3.1] fc-cache error: {e}")
            return False
    
    def check_font_hygiene(self) -> Dict[str, Any]:
        """
        Verify current font environment against target OS expectations.
        Returns detailed report of leaks and missing fonts.
        """
        result = {
            "target_os": self.target_os.value,
            "leaks": [],
            "missing": [],
            "clean": True,
        }
        
        try:
            output = subprocess.check_output(
                "fc-list : family", shell=True, timeout=10
            ).decode()
            installed_flat = output
        except Exception as e:
            result["error"] = str(e)
            result["clean"] = False
            return result
        
        # Check for Linux font leaks
        for font in LINUX_EXCLUSIVE_FONTS:
            if font in installed_flat:
                result["leaks"].append(font)
                result["clean"] = False
        
        # Check for required target OS fonts
        if self.os_family == "windows":
            required = WINDOWS_CORE_FONTS["required"]
        else:
            required = MACOS_CORE_FONTS["required"]
        
        for font in required:
            if font not in installed_flat:
                result["missing"].append(font)
        
        # Missing fonts are a warning, not a hard fail (Camoufox can handle some)
        if result["leaks"]:
            result["clean"] = False
        
        return result
    
    def generate_metric_overrides(self, profile_path: Optional[Path] = None) -> Dict[str, Any]:
        """
        Generate font metric override config for Ghost Motor extension.
        
        This handles the measureText() attack: even if fonts are rejected,
        the fallback font metrics can differ between OSes. We provide
        exact metric values that Ghost Motor injects via canvas override.
        """
        metrics = FONT_METRICS_DATABASE.get(self.os_family, {})
        
        config = {
            "font_metric_spoofing": True,
            "target_os": self.target_os.value,
            "metrics": metrics,
            "default_font": "Segoe UI" if self.os_family == "windows" else "Helvetica Neue",
        }
        
        if profile_path:
            out = Path(profile_path) / "font_metrics.json"
            try:
                with open(out, 'w') as f:
                    json.dump(config, f, indent=2)
                logger.info(f"[PHASE 3.1] Font metrics written to {out}")
            except Exception as e:
                logger.error(f"[PHASE 3.1] Failed to write font metrics: {e}")
        
        return config
    
    def apply(self, profile_path: Optional[str] = None) -> FontSanitizationResult:
        """
        Full Phase 3.1 application:
        1. Write local.conf with rejectfont
        2. Install target OS fonts
        3. Rebuild font cache
        4. Generate metric overrides
        """
        logger.info(f"[PHASE 3.1] Sanitizing fonts for {self.target_os.value}...")
        
        conf_ok = self.write_local_conf()
        installed = self.install_target_fonts()
        cache_ok = self.rebuild_font_cache() if conf_ok else False
        
        metrics_ok = False
        if profile_path:
            self.generate_metric_overrides(Path(profile_path))
            metrics_ok = True
        
        hygiene = self.check_font_hygiene()
        
        result = FontSanitizationResult(
            target_os=self.target_os.value,
            fonts_rejected=len(LINUX_EXCLUSIVE_FONTS),
            fonts_installed=installed,
            fonts_missing=hygiene.get("missing", []),
            local_conf_written=conf_ok,
            cache_rebuilt=cache_ok,
            metric_overrides_written=metrics_ok,
            clean=hygiene.get("clean", False),
        )
        
        if result.clean:
            logger.info("[PHASE 3.1] Font environment: CLEAN")
        else:
            leaks = hygiene.get("leaks", [])
            logger.warning(f"[PHASE 3.1] Font environment: {len(leaks)} leaks detected")
        
        return result


# ═══════════════════════════════════════════════════════════════════════════
# CONVENIENCE EXPORTS
# ═══════════════════════════════════════════════════════════════════════════

def sanitize_fonts(target_os: str = "windows_11", profile_path: Optional[str] = None) -> FontSanitizationResult:
    """Quick font sanitization"""
    os_map = {
        "windows_10": TargetOS.WINDOWS_10, "windows_11": TargetOS.WINDOWS_11,
        "macos_14": TargetOS.MACOS_14, "macos_13": TargetOS.MACOS_13,
    }
    sanitizer = FontSanitizer(os_map.get(target_os, TargetOS.WINDOWS_11))
    return sanitizer.apply(profile_path)

def check_fonts(target_os: str = "windows_11") -> Dict[str, Any]:
    """Quick font hygiene check"""
    os_map = {
        "windows_10": TargetOS.WINDOWS_10, "windows_11": TargetOS.WINDOWS_11,
        "macos_14": TargetOS.MACOS_14, "macos_13": TargetOS.MACOS_13,
    }
    sanitizer = FontSanitizer(os_map.get(target_os, TargetOS.WINDOWS_11))
    return sanitizer.check_font_hygiene()


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 FONT FINGERPRINT DETECTOR — Detect font-based fingerprinting attempts
# ═══════════════════════════════════════════════════════════════════════════════

import time
import hashlib
import random


@dataclass
class FingerprintAttempt:
    """Record of a fingerprinting attempt."""
    timestamp: float
    method: str  # "enumerate", "measureText", "canvas"
    fonts_probed: List[str]
    source_url: str
    risk_score: float


class FontFingerprintDetector:
    """
    V7.6 Font Fingerprint Detector - Detects and logs font-based
    fingerprinting attempts from websites.
    """
    
    # Known fingerprinting probe patterns
    FINGERPRINT_PROBE_FONTS = {
        # Common fingerprinting libraries probe these obscure fonts
        "Wingdings", "Wingdings 2", "Wingdings 3", "Webdings",
        "Symbol", "Marlett", "MS Reference Sans Serif",
        "MS Reference Specialty", "MT Extra", "Bookshelf Symbol 7",
        "Agency FB", "Algerian", "Baskerville Old Face",
        "Bauhaus 93", "Bell MT", "Berlin Sans FB",
        "Bernard MT Condensed", "Blackadder ITC", "Bodoni MT",
        "Bradley Hand ITC", "Britannic Bold", "Broadway",
    }
    
    # Suspicious rapid enumeration threshold
    RAPID_ENUM_THRESHOLD = 50  # fonts in 1 second
    RAPID_MEASURE_THRESHOLD = 20  # measureText calls in 100ms
    
    def __init__(self):
        self._attempts: List[FingerprintAttempt] = []
        self._font_probes: Dict[str, List[float]] = {}  # font -> timestamps
        self._measure_calls: List[float] = []
        self._detection_count = 0
    
    def record_font_probe(self, font_name: str, source_url: str = ""):
        """Record a font enumeration probe."""
        now = time.time()
        
        if font_name not in self._font_probes:
            self._font_probes[font_name] = []
        self._font_probes[font_name].append(now)
        
        # Check for fingerprinting indicators
        risk_score = 0.0
        
        # Probe of known fingerprint fonts
        if font_name in self.FINGERPRINT_PROBE_FONTS:
            risk_score += 0.4
        
        # Rapid enumeration pattern
        recent_probes = [t for f, times in self._font_probes.items() 
                        for t in times if now - t < 1.0]
        if len(recent_probes) > self.RAPID_ENUM_THRESHOLD:
            risk_score += 0.5
        
        if risk_score >= 0.4:
            self._detection_count += 1
            attempt = FingerprintAttempt(
                timestamp=now,
                method="enumerate",
                fonts_probed=[font_name],
                source_url=source_url,
                risk_score=min(1.0, risk_score)
            )
            self._attempts.append(attempt)
            logger.warning(f"[V7.6] Font fingerprint attempt detected: {font_name} (risk: {risk_score:.1%})")
    
    def record_measure_text_call(self, font_family: str, test_string: str, source_url: str = ""):
        """Record a measureText() call for fingerprint detection."""
        now = time.time()
        self._measure_calls.append(now)
        
        risk_score = 0.0
        
        # Rapid measureText calls
        recent = [t for t in self._measure_calls if now - t < 0.1]
        if len(recent) > self.RAPID_MEASURE_THRESHOLD:
            risk_score += 0.6
        
        # Common fingerprint test strings
        fingerprint_strings = [
            "mmmmmmmmmmlli", "wwwwwwwwwww", "WWWWWWWWWWW",
            "iiiiiiiiiiiiiiiiiiii", "0123456789", "The quick brown fox"
        ]
        if test_string in fingerprint_strings:
            risk_score += 0.3
        
        if risk_score >= 0.3:
            self._detection_count += 1
            attempt = FingerprintAttempt(
                timestamp=now,
                method="measureText",
                fonts_probed=[font_family],
                source_url=source_url,
                risk_score=min(1.0, risk_score)
            )
            self._attempts.append(attempt)
    
    def get_recent_attempts(self, seconds: int = 300) -> List[FingerprintAttempt]:
        """Get fingerprinting attempts from the last N seconds."""
        cutoff = time.time() - seconds
        return [a for a in self._attempts if a.timestamp > cutoff]
    
    def get_risk_assessment(self) -> Dict[str, Any]:
        """Get overall fingerprinting risk assessment."""
        recent = self.get_recent_attempts(60)
        
        if not recent:
            return {"risk": "none", "attempts": 0, "recommendation": "No action needed"}
        
        max_risk = max(a.risk_score for a in recent)
        
        if max_risk >= 0.7:
            return {
                "risk": "high",
                "attempts": len(recent),
                "recommendation": "Consider rotating profile or applying additional font masking"
            }
        elif max_risk >= 0.4:
            return {
                "risk": "medium",
                "attempts": len(recent),
                "recommendation": "Monitor for continued fingerprinting"
            }
        else:
            return {
                "risk": "low",
                "attempts": len(recent),
                "recommendation": "Normal font probing detected"
            }
    
    def get_stats(self) -> Dict[str, int]:
        """Get detection statistics."""
        return {
            "total_detections": self._detection_count,
            "recent_attempts": len(self.get_recent_attempts(300)),
            "fonts_probed": len(self._font_probes)
        }


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 DYNAMIC FONT INJECTOR — Runtime font injection/removal
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class InjectionResult:
    """Result of font injection operation."""
    success: bool
    fonts_injected: int
    fonts_removed: int
    errors: List[str]


class DynamicFontInjector:
    """
    V7.6 Dynamic Font Injector - Enables runtime font injection
    and removal without requiring system restart or cache rebuild.
    """
    
    def __init__(self, target_os: TargetOS = TargetOS.WINDOWS_11):
        self.target_os = target_os
        self._injected_fonts: Set[str] = set()
        self._removed_fonts: Set[str] = set()
        self._injection_history: List[Dict] = []
    
    def inject_font(self, font_name: str, font_path: str) -> bool:
        """
        Inject a font into the system temporarily.
        
        Args:
            font_name: Display name for the font
            font_path: Path to the .ttf/.otf file
        
        Returns:
            True if successful
        """
        font_file = Path(font_path)
        if not font_file.exists():
            logger.error(f"[V7.6] Font file not found: {font_path}")
            return False
        
        # Create user font directory if needed
        user_font_dir = Path.home() / ".local/share/fonts/titan-injected"
        user_font_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Copy font to user directory
            dest = user_font_dir / font_file.name
            shutil.copy2(font_file, dest)
            
            # Update font cache for user directory only (faster)
            subprocess.run(
                ["fc-cache", "-f", str(user_font_dir)],
                capture_output=True, timeout=30
            )
            
            self._injected_fonts.add(font_name)
            self._injection_history.append({
                "action": "inject",
                "font": font_name,
                "path": str(dest),
                "timestamp": time.time()
            })
            
            logger.info(f"[V7.6] Font injected: {font_name}")
            return True
            
        except Exception as e:
            logger.error(f"[V7.6] Font injection failed: {e}")
            return False
    
    def remove_font(self, font_name: str) -> bool:
        """
        Remove a previously injected font.
        
        Args:
            font_name: Name of the font to remove
        
        Returns:
            True if successful
        """
        user_font_dir = Path.home() / ".local/share/fonts/titan-injected"
        
        try:
            # Find and remove matching font files
            removed = False
            for font_file in user_font_dir.glob("*"):
                # Simple check - in production would parse font metadata
                if font_name.lower().replace(" ", "") in font_file.stem.lower().replace(" ", ""):
                    font_file.unlink()
                    removed = True
            
            if removed:
                # Refresh cache
                subprocess.run(
                    ["fc-cache", "-f", str(user_font_dir)],
                    capture_output=True, timeout=30
                )
                
                self._removed_fonts.add(font_name)
                if font_name in self._injected_fonts:
                    self._injected_fonts.remove(font_name)
                
                self._injection_history.append({
                    "action": "remove",
                    "font": font_name,
                    "timestamp": time.time()
                })
                
                logger.info(f"[V7.6] Font removed: {font_name}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"[V7.6] Font removal failed: {e}")
            return False
    
    def inject_os_font_set(self, font_source_dir: str) -> InjectionResult:
        """
        Inject a complete OS font set from a directory.
        
        Args:
            font_source_dir: Directory containing font files
        
        Returns:
            InjectionResult with summary
        """
        source = Path(font_source_dir)
        if not source.exists():
            return InjectionResult(
                success=False,
                fonts_injected=0,
                fonts_removed=0,
                errors=[f"Source directory not found: {font_source_dir}"]
            )
        
        injected = 0
        errors = []
        
        for font_file in source.glob("*.tt[fc]"):
            font_name = font_file.stem.replace("-", " ").replace("_", " ")
            if self.inject_font(font_name, str(font_file)):
                injected += 1
            else:
                errors.append(f"Failed to inject: {font_file.name}")
        
        for font_file in source.glob("*.otf"):
            font_name = font_file.stem.replace("-", " ").replace("_", " ")
            if self.inject_font(font_name, str(font_file)):
                injected += 1
            else:
                errors.append(f"Failed to inject: {font_file.name}")
        
        return InjectionResult(
            success=injected > 0,
            fonts_injected=injected,
            fonts_removed=0,
            errors=errors
        )
    
    def clear_injected_fonts(self) -> int:
        """Remove all injected fonts."""
        user_font_dir = Path.home() / ".local/share/fonts/titan-injected"
        cleared = 0
        
        if user_font_dir.exists():
            for font_file in user_font_dir.glob("*"):
                try:
                    font_file.unlink()
                    cleared += 1
                except Exception:
                    pass
            
            # Refresh cache
            subprocess.run(
                ["fc-cache", "-f"],
                capture_output=True, timeout=60
            )
        
        self._injected_fonts.clear()
        logger.info(f"[V7.6] Cleared {cleared} injected fonts")
        return cleared
    
    def get_injected_fonts(self) -> List[str]:
        """Get list of currently injected fonts."""
        return list(self._injected_fonts)


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 FONT METRIC FUZZER — Add controlled noise to font metrics
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class FuzzedMetrics:
    """Fuzzed font metrics."""
    original: Dict[str, float]
    fuzzed: Dict[str, float]
    noise_added: Dict[str, float]
    seed: str


class FontMetricFuzzer:
    """
    V7.6 Font Metric Fuzzer - Adds controlled noise to font metrics
    to prevent exact matching against known metric databases.
    """
    
    # Noise ranges by metric type (percentage)
    NOISE_RANGES = {
        "avg_width_ratio": 0.005,  # 0.5% max variance
        "ascent": 0.003,           # 0.3% max variance
        "descent": 0.005,          # 0.5% max variance
        "line_gap": 0.010,         # 1.0% max variance (can be 0)
    }
    
    def __init__(self, seed: Optional[str] = None):
        """
        Initialize fuzzer with optional seed for reproducibility.
        
        Args:
            seed: Seed string (e.g., profile ID) for reproducible fuzzing
        """
        self.seed = seed or hashlib.md5(str(time.time()).encode()).hexdigest()[:8]
        self._rng = random.Random(self.seed)
        self._fuzzed_cache: Dict[str, FuzzedMetrics] = {}
    
    def fuzz_metrics(self, font_name: str, metrics: Dict[str, float]) -> FuzzedMetrics:
        """
        Add controlled noise to font metrics.
        
        Args:
            font_name: Font name for caching
            metrics: Original metrics dict
        
        Returns:
            FuzzedMetrics with original and fuzzed values
        """
        # Return cached result for consistency
        cache_key = f"{font_name}_{self.seed}"
        if cache_key in self._fuzzed_cache:
            return self._fuzzed_cache[cache_key]
        
        fuzzed = {}
        noise = {}
        
        for key, value in metrics.items():
            if key in self.NOISE_RANGES:
                max_noise = self.NOISE_RANGES[key]
                noise_pct = self._rng.uniform(-max_noise, max_noise)
                fuzzed_value = value * (1 + noise_pct)
                
                # Round to realistic precision
                fuzzed[key] = round(fuzzed_value, 4)
                noise[key] = round(noise_pct * 100, 3)  # Store as percentage
            else:
                fuzzed[key] = value
                noise[key] = 0
        
        result = FuzzedMetrics(
            original=metrics,
            fuzzed=fuzzed,
            noise_added=noise,
            seed=self.seed
        )
        
        self._fuzzed_cache[cache_key] = result
        return result
    
    def fuzz_font_database(self, os_family: str) -> Dict[str, Dict[str, float]]:
        """
        Fuzz all metrics in a font database.
        
        Args:
            os_family: "windows" or "macos"
        
        Returns:
            Dict of font_name -> fuzzed_metrics
        """
        source = FONT_METRICS_DATABASE.get(os_family, {})
        fuzzed_db = {}
        
        for font_name, metrics in source.items():
            fuzzed = self.fuzz_metrics(font_name, metrics)
            fuzzed_db[font_name] = fuzzed.fuzzed
        
        return fuzzed_db
    
    def generate_config(self, os_family: str, output_path: Optional[str] = None) -> Dict:
        """
        Generate fuzzed font metrics config for profile.
        
        Args:
            os_family: "windows" or "macos"
            output_path: Optional path to write config
        
        Returns:
            Config dict
        """
        config = {
            "font_metric_fuzzing": True,
            "fuzzer_seed": self.seed,
            "os_family": os_family,
            "metrics": self.fuzz_font_database(os_family)
        }
        
        if output_path:
            try:
                with open(output_path, 'w') as f:
                    json.dump(config, f, indent=2)
                logger.info(f"[V7.6] Fuzzed font metrics written to {output_path}")
            except Exception as e:
                logger.error(f"[V7.6] Failed to write fuzzed metrics: {e}")
        
        return config
    
    def reset_seed(self, new_seed: str):
        """Reset fuzzer with new seed."""
        self.seed = new_seed
        self._rng = random.Random(new_seed)
        self._fuzzed_cache.clear()


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 CROSS-OS FONT RESOLVER — Resolve fonts across OS emulations
# ═══════════════════════════════════════════════════════════════════════════════

class CrossOSFontResolver:
    """
    V7.6 Cross-OS Font Resolver - Resolves font requests across
    different OS emulations, providing appropriate substitutions.
    """
    
    # Comprehensive font mappings between OSes
    FONT_MAPPINGS = {
        # Windows -> macOS
        "windows_to_macos": {
            "Segoe UI": "San Francisco",
            "Segoe UI Light": "SF Pro Light",
            "Segoe UI Semibold": "SF Pro Semibold",
            "Arial": "Helvetica",
            "Calibri": "Helvetica Neue",
            "Cambria": "Times New Roman",
            "Consolas": "Menlo",
            "Courier New": "Courier",
            "Tahoma": "Geneva",
            "Verdana": "Helvetica Neue",
            "Georgia": "Georgia",
            "Impact": "Helvetica Bold",
            "Comic Sans MS": "Chalkboard SE",
            "Trebuchet MS": "Trebuchet MS",
            "Lucida Console": "Monaco",
            "Palatino Linotype": "Palatino",
        },
        # macOS -> Windows
        "macos_to_windows": {
            "San Francisco": "Segoe UI",
            "SF Pro": "Segoe UI",
            "SF Pro Light": "Segoe UI Light",
            "SF Pro Semibold": "Segoe UI Semibold",
            "SF Mono": "Consolas",
            "Helvetica Neue": "Arial",
            "Helvetica": "Arial",
            "Menlo": "Consolas",
            "Monaco": "Lucida Console",
            "Lucida Grande": "Tahoma",
            "Geneva": "Tahoma",
            "Avenir": "Century Gothic",
            "Avenir Next": "Calibri",
            "Apple Color Emoji": "Segoe UI Emoji",
        },
        # Linux -> Windows
        "linux_to_windows": {
            "Liberation Sans": "Arial",
            "Liberation Serif": "Times New Roman",
            "Liberation Mono": "Courier New",
            "DejaVu Sans": "Segoe UI",
            "DejaVu Serif": "Georgia",
            "DejaVu Sans Mono": "Consolas",
            "Ubuntu": "Segoe UI",
            "Ubuntu Mono": "Consolas",
            "Noto Sans": "Arial",
            "Noto Serif": "Times New Roman",
            "Noto Mono": "Courier New",
            "Noto Color Emoji": "Segoe UI Emoji",
            "Cantarell": "Segoe UI",
            "Source Code Pro": "Consolas",
            "Hack": "Consolas",
        },
        # Linux -> macOS
        "linux_to_macos": {
            "Liberation Sans": "Helvetica Neue",
            "Liberation Serif": "Times New Roman",
            "Liberation Mono": "Menlo",
            "DejaVu Sans": "Helvetica Neue",
            "DejaVu Serif": "Georgia",
            "DejaVu Sans Mono": "Monaco",
            "Ubuntu": "San Francisco",
            "Ubuntu Mono": "SF Mono",
            "Noto Sans": "Helvetica",
            "Noto Serif": "Times New Roman",
            "Noto Color Emoji": "Apple Color Emoji",
        },
    }
    
    # Generic fallbacks by category
    CATEGORY_FALLBACKS = {
        "sans-serif": {"windows": "Segoe UI", "macos": "Helvetica Neue"},
        "serif": {"windows": "Georgia", "macos": "Times New Roman"},
        "monospace": {"windows": "Consolas", "macos": "Menlo"},
        "emoji": {"windows": "Segoe UI Emoji", "macos": "Apple Color Emoji"},
    }
    
    def __init__(self, target_os: TargetOS):
        self.target_os = target_os
        self.os_family = "windows" if "windows" in target_os.value else "macos"
        self._resolution_cache: Dict[str, str] = {}
        self._resolution_count = 0
    
    def resolve(self, requested_font: str, source_os: str = "linux") -> str:
        """
        Resolve a font request to appropriate target OS font.
        
        Args:
            requested_font: Font name requested
            source_os: Source OS ("linux", "windows", "macos")
        
        Returns:
            Resolved font name for target OS
        """
        cache_key = f"{requested_font}_{source_os}"
        if cache_key in self._resolution_cache:
            return self._resolution_cache[cache_key]
        
        self._resolution_count += 1
        resolved = self._do_resolve(requested_font, source_os)
        self._resolution_cache[cache_key] = resolved
        
        return resolved
    
    def _do_resolve(self, font: str, source_os: str) -> str:
        """Internal resolution logic."""
        # Direct mapping
        mapping_key = f"{source_os}_to_{self.os_family}"
        mapping = self.FONT_MAPPINGS.get(mapping_key, {})
        
        if font in mapping:
            return mapping[font]
        
        # Try case-insensitive match
        font_lower = font.lower()
        for src, dst in mapping.items():
            if src.lower() == font_lower:
                return dst
        
        # If font is already valid for target OS, return as-is
        if self.os_family == "windows":
            valid_fonts = set(WINDOWS_CORE_FONTS["required"])
        else:
            valid_fonts = set(MACOS_CORE_FONTS["required"])
        
        if font in valid_fonts:
            return font
        
        # Category-based fallback
        font_lower = font.lower()
        if any(mono in font_lower for mono in ["mono", "console", "code", "courier"]):
            return self.CATEGORY_FALLBACKS["monospace"][self.os_family]
        elif any(serif in font_lower for serif in ["serif", "times", "georgia"]):
            return self.CATEGORY_FALLBACKS["serif"][self.os_family]
        elif "emoji" in font_lower:
            return self.CATEGORY_FALLBACKS["emoji"][self.os_family]
        else:
            return self.CATEGORY_FALLBACKS["sans-serif"][self.os_family]
    
    def resolve_font_stack(self, font_stack: List[str], source_os: str = "linux") -> List[str]:
        """
        Resolve an entire font stack.
        
        Args:
            font_stack: List of font names in priority order
            source_os: Source OS
        
        Returns:
            Resolved font stack
        """
        resolved = []
        seen = set()
        
        for font in font_stack:
            r = self.resolve(font, source_os)
            if r not in seen:
                resolved.append(r)
                seen.add(r)
        
        return resolved
    
    def generate_css_override(self, css_rules: Dict[str, str], source_os: str = "linux") -> Dict[str, str]:
        """
        Generate CSS font-family overrides.
        
        Args:
            css_rules: Dict of selector -> font-family value
            source_os: Source OS
        
        Returns:
            Dict with resolved font-family values
        """
        overrides = {}
        
        for selector, font_family in css_rules.items():
            # Parse font-family (comma-separated)
            fonts = [f.strip().strip("'\"") for f in font_family.split(",")]
            resolved = self.resolve_font_stack(fonts, source_os)
            overrides[selector] = ", ".join(f'"{f}"' if " " in f else f for f in resolved)
        
        return overrides
    
    def get_stats(self) -> Dict[str, Any]:
        """Get resolution statistics."""
        return {
            "target_os": self.target_os.value,
            "resolutions_performed": self._resolution_count,
            "cached_resolutions": len(self._resolution_cache)
        }


# Global instances
_fingerprint_detector: Optional[FontFingerprintDetector] = None
_dynamic_injector: Optional[DynamicFontInjector] = None
_metric_fuzzer: Optional[FontMetricFuzzer] = None
_font_resolver: Optional[CrossOSFontResolver] = None


def get_fingerprint_detector() -> FontFingerprintDetector:
    """Get global font fingerprint detector."""
    global _fingerprint_detector
    if _fingerprint_detector is None:
        _fingerprint_detector = FontFingerprintDetector()
    return _fingerprint_detector


def get_dynamic_injector(target_os: TargetOS = TargetOS.WINDOWS_11) -> DynamicFontInjector:
    """Get global dynamic font injector."""
    global _dynamic_injector
    if _dynamic_injector is None:
        _dynamic_injector = DynamicFontInjector(target_os)
    return _dynamic_injector


def get_metric_fuzzer(seed: Optional[str] = None) -> FontMetricFuzzer:
    """Get global font metric fuzzer."""
    global _metric_fuzzer
    if _metric_fuzzer is None:
        _metric_fuzzer = FontMetricFuzzer(seed)
    return _metric_fuzzer


def get_font_resolver(target_os: TargetOS = TargetOS.WINDOWS_11) -> CrossOSFontResolver:
    """Get global cross-OS font resolver."""
    global _font_resolver
    if _font_resolver is None:
        _font_resolver = CrossOSFontResolver(target_os)
    return _font_resolver
