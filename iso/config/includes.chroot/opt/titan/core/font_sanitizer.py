"""
TITAN V7.0 SINGULARITY — Phase 3.1: Font Sanitization Engine
OS-Specific Font Injection, Linux Font Rejection, Metric Spoofing

VULNERABILITY: Titan is Debian-based. Fonts like 'Liberation Sans',
'DejaVu Sans', 'Noto Color Emoji' are Linux-exclusive. If the profile
claims Windows 10, font enumeration via JS `document.fonts` or
`measureText()` will reveal the true OS regardless of User-Agent.

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
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("TITAN-V7-FONTS")


class TargetOS(Enum):
    WINDOWS_10 = "windows_10"
    WINDOWS_11 = "windows_11"
    MACOS_14 = "macos_14"
    MACOS_13 = "macos_13"


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
  Generated: {__import__('datetime').datetime.now().isoformat()}
  
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
            installed_fonts = set(output.strip().split("\n"))
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
            with open(out, 'w') as f:
                json.dump(config, f, indent=2)
            logger.info(f"[PHASE 3.1] Font metrics written to {out}")
        
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
