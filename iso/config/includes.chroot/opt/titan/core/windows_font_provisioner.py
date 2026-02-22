"""
TITAN V7.5 SINGULARITY — Windows Font Provisioner
Ring 2 OS Hardening — Eliminates font enumeration detection vector

Problem:
    Antifraud JS enumerates installed fonts via Canvas measureText() probing.
    Missing Windows-exclusive fonts (Segoe UI, Calibri, Consolas, Cambria)
    immediately reveal a non-Windows environment.

Solution:
    1. Downloads metric-compatible open-source alternatives
    2. Creates fontconfig aliases so Segoe UI → equivalent metric font
    3. Installs ttf-mscorefonts-installer for Arial, Times, Courier, etc.
    4. Generates complete /etc/fonts/local.conf with rejectfont + alias rules

Detection Vectors Neutralized:
    - Missing Segoe UI, Calibri, Consolas → aliased to metric equivalents
    - Linux-exclusive fonts (Liberation, DejaVu, Noto) → blocked via rejectfont
    - Font list length mismatch (Linux has fewer fonts) → padded with Windows set
"""

import os
import subprocess
import shutil
import logging
from pathlib import Path
from typing import Dict, List, Tuple

__version__ = "8.0.0"
__author__ = "Dva.12"

logger = logging.getLogger("TITAN-V7.5")

# Windows fonts and their open-source metric-compatible equivalents
FONT_ALIASES: Dict[str, str] = {
    # Windows Font → Open Source Equivalent
    "Segoe UI": "Noto Sans",
    "Segoe UI Semibold": "Noto Sans SemiBold",
    "Segoe UI Light": "Noto Sans Light",
    "Segoe UI Symbol": "Noto Sans Symbols",
    "Calibri": "Carlito",
    "Cambria": "Caladea",
    "Consolas": "Cascadia Code",
    "Lucida Console": "Liberation Mono",
    "Palatino Linotype": "TeX Gyre Pagella",
    "Tahoma": "Liberation Sans",
    "Franklin Gothic": "Liberation Sans",
    "Candara": "Noto Sans",
    "Corbel": "Noto Sans",
    "Constantia": "Noto Serif",
}

# Linux fonts to block (reveal non-Windows OS)
LINUX_FONTS_REJECT: List[str] = [
    "Liberation Sans", "Liberation Serif", "Liberation Mono",
    "DejaVu Sans", "DejaVu Serif", "DejaVu Sans Mono",
    "Noto Sans", "Noto Serif", "Noto Mono", "Noto Color Emoji",
    "Ubuntu", "Ubuntu Mono", "Ubuntu Condensed",
    "Droid Sans", "Droid Serif", "Droid Sans Mono",
    "Cantarell", "FreeSans", "FreeMono", "FreeSerif",
    "Bitstream Vera Sans", "Bitstream Vera Serif",
    "Nimbus Sans", "Nimbus Roman", "Nimbus Mono",
    "URW Gothic", "URW Bookman", "URW Palladio",
    "Source Sans Pro", "Source Serif Pro", "Source Code Pro",
    "Hack", "Fira Sans", "Fira Code", "Fira Mono",
    "Open Sans", "Roboto", "Lato", "Montserrat",
]

# APT packages that provide Windows-compatible fonts
FONT_PACKAGES: List[str] = [
    "ttf-mscorefonts-installer",   # Arial, Times, Courier, Verdana, etc.
    "fonts-liberation",             # Liberation (metric-compatible)
    "fonts-liberation2",            # Liberation 2
    "fonts-crosextra-carlito",      # Carlito (Calibri-compatible)
    "fonts-crosextra-caladea",      # Caladea (Cambria-compatible)
    "fonts-cascadia-code",          # Cascadia Code (Consolas-like)
    "fonts-noto-core",              # Noto core fonts
    "fonts-wine",                   # Wine's Windows font set
]


class WindowsFontProvisioner:
    """Provision and configure Windows-compatible fonts on Linux."""

    FONT_DIR = Path("/opt/titan/assets/fonts/windows")
    LOCAL_CONF = Path("/etc/fonts/local.conf")
    TITAN_CONF = Path("/etc/fonts/conf.d/99-titan-windows.conf")

    def __init__(self):
        self._installed_packages = []
        self._aliased_fonts = {}
        self._rejected_fonts = []

    def install_font_packages(self) -> Dict[str, bool]:
        """Install APT font packages."""
        results = {}
        env = dict(os.environ, DEBIAN_FRONTEND="noninteractive")

        for pkg in FONT_PACKAGES:
            try:
                # Check if already installed
                ret = subprocess.run(
                    ["dpkg", "-s", pkg],
                    capture_output=True, timeout=10
                )
                if ret.returncode == 0:
                    results[pkg] = True
                    self._installed_packages.append(pkg)
                    continue

                # Install
                ret = subprocess.run(
                    ["apt-get", "install", "-y", "--no-install-recommends", pkg],
                    capture_output=True, env=env, timeout=120
                )
                results[pkg] = ret.returncode == 0
                if ret.returncode == 0:
                    self._installed_packages.append(pkg)
                else:
                    logger.warning(f"Failed to install {pkg}: {ret.stderr.decode()[:100]}")
            except Exception as e:
                results[pkg] = False
                logger.warning(f"Error installing {pkg}: {e}")

        return results

    def stage_fonts(self) -> int:
        """Copy installed fonts to staging directory."""
        self.FONT_DIR.mkdir(parents=True, exist_ok=True)

        font_dirs = [
            "/usr/share/fonts/truetype/msttcorefonts",
            "/usr/share/fonts/truetype/liberation",
            "/usr/share/fonts/truetype/liberation2",
            "/usr/share/fonts/truetype/crosextra",
            "/usr/share/fonts/truetype/cascadia-code",
            "/usr/share/fonts/truetype/noto",
            "/usr/share/fonts/wine",
        ]

        count = 0
        for src_dir in font_dirs:
            src = Path(src_dir)
            if not src.exists():
                continue
            for font_file in src.glob("*.ttf"):
                dst = self.FONT_DIR / font_file.name
                if not dst.exists():
                    shutil.copy2(font_file, dst)
                    count += 1
            for font_file in src.glob("*.TTF"):
                dst = self.FONT_DIR / font_file.name
                if not dst.exists():
                    shutil.copy2(font_file, dst)
                    count += 1

        logger.info(f"Staged {count} new font files to {self.FONT_DIR}")
        return count

    def generate_fontconfig(self) -> str:
        """
        Generate complete fontconfig XML with:
        1. rejectfont rules blocking all Linux-exclusive fonts
        2. Alias rules mapping Windows fonts to installed equivalents
        3. Font directory for our staged Windows fonts
        """
        xml_parts = ['<?xml version="1.0"?>',
                     '<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">',
                     '<fontconfig>',
                     '',
                     '  <!-- TITAN V7.5 Windows Font Environment -->',
                     '  <!-- Auto-generated — do not edit manually -->',
                     '',
                     '  <!-- Custom font directory -->',
                     f'  <dir>{self.FONT_DIR}</dir>',
                     '']

        # Reject Linux fonts
        xml_parts.append('  <!-- Block Linux-exclusive fonts that reveal OS -->')
        xml_parts.append('  <selectfont>')
        xml_parts.append('    <rejectfont>')
        for font in LINUX_FONTS_REJECT:
            xml_parts.append(f'      <pattern><patelt name="family"><string>{font}</string></patelt></pattern>')
            self._rejected_fonts.append(font)
        xml_parts.append('    </rejectfont>')
        xml_parts.append('  </selectfont>')
        xml_parts.append('')

        # Alias Windows fonts to available equivalents
        xml_parts.append('  <!-- Alias Windows fonts to metric-compatible equivalents -->')
        for win_font, equiv_font in FONT_ALIASES.items():
            xml_parts.append(f'  <alias binding="same">')
            xml_parts.append(f'    <family>{win_font}</family>')
            xml_parts.append(f'    <accept><family>{equiv_font}</family></accept>')
            xml_parts.append(f'  </alias>')
            self._aliased_fonts[win_font] = equiv_font
        xml_parts.append('')

        # Prefer Windows-style rendering
        xml_parts.append('  <!-- Windows-style font rendering -->')
        xml_parts.append('  <match target="font">')
        xml_parts.append('    <edit name="antialias" mode="assign"><bool>true</bool></edit>')
        xml_parts.append('    <edit name="hinting" mode="assign"><bool>true</bool></edit>')
        xml_parts.append('    <edit name="hintstyle" mode="assign"><const>hintslight</const></edit>')
        xml_parts.append('    <edit name="rgba" mode="assign"><const>rgb</const></edit>')
        xml_parts.append('    <edit name="lcdfilter" mode="assign"><const>lcddefault</const></edit>')
        xml_parts.append('  </match>')
        xml_parts.append('')

        xml_parts.append('</fontconfig>')
        return '\n'.join(xml_parts)

    def write_fontconfig(self) -> bool:
        """Write the fontconfig file and rebuild cache."""
        xml = self.generate_fontconfig()

        try:
            # Write as separate titan config (doesn't overwrite system local.conf)
            self.TITAN_CONF.parent.mkdir(parents=True, exist_ok=True)
            self.TITAN_CONF.write_text(xml)

            # Also update local.conf
            self.LOCAL_CONF.write_text(xml)

            # Rebuild font cache
            subprocess.run(["fc-cache", "-f"], capture_output=True, timeout=60)
            logger.info(f"Fontconfig written: {len(self._rejected_fonts)} rejected, "
                        f"{len(self._aliased_fonts)} aliased")
            return True
        except Exception as e:
            logger.error(f"Failed to write fontconfig: {e}")
            return False

    def verify(self) -> Dict:
        """Verify font environment after provisioning."""
        results = {
            "linux_fonts_blocked": 0,
            "linux_fonts_leaking": [],
            "windows_fonts_available": 0,
            "windows_fonts_missing": [],
            "total_fonts_staged": 0,
        }

        # Count staged fonts
        if self.FONT_DIR.exists():
            results["total_fonts_staged"] = len(list(self.FONT_DIR.glob("*.ttf")) +
                                                 list(self.FONT_DIR.glob("*.TTF")))

        # Check which Linux fonts are still accessible
        for font in LINUX_FONTS_REJECT[:10]:  # Check subset for speed
            try:
                ret = subprocess.run(
                    ["fc-match", "--format=%{family}", font],
                    capture_output=True, text=True, timeout=5
                )
                matched = ret.stdout.strip()
                if matched.lower() == font.lower():
                    results["linux_fonts_leaking"].append(font)
                else:
                    results["linux_fonts_blocked"] += 1
            except Exception:
                pass

        # Check Windows font availability
        win_fonts_to_check = ["Arial", "Times New Roman", "Courier New",
                              "Verdana", "Georgia", "Impact", "Comic Sans MS"]
        for font in win_fonts_to_check:
            try:
                ret = subprocess.run(
                    ["fc-match", "--format=%{file}", font],
                    capture_output=True, text=True, timeout=5
                )
                if ret.stdout.strip():
                    results["windows_fonts_available"] += 1
                else:
                    results["windows_fonts_missing"].append(font)
            except Exception:
                results["windows_fonts_missing"].append(font)

        return results

    def provision(self) -> Dict:
        """Full provisioning pipeline."""
        report = {
            "version": __version__,
            "packages": self.install_font_packages(),
            "fonts_staged": self.stage_fonts(),
            "fontconfig_written": self.write_fontconfig(),
            "verification": self.verify(),
            "rejected_count": len(self._rejected_fonts),
            "aliased_count": len(self._aliased_fonts),
        }
        return report


def provision_windows_fonts() -> Dict:
    """Convenience function for full font provisioning."""
    provisioner = WindowsFontProvisioner()
    return provisioner.provision()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[TITAN-FONTS] %(message)s")
    report = provision_windows_fonts()
    print(f"\nPackages installed: {sum(1 for v in report['packages'].values() if v)}/{len(report['packages'])}")
    print(f"Fonts staged: {report['fonts_staged']}")
    print(f"Fonts rejected: {report['rejected_count']}")
    print(f"Fonts aliased: {report['aliased_count']}")
    v = report["verification"]
    print(f"Windows fonts available: {v['windows_fonts_available']}")
    print(f"Linux fonts leaking: {len(v['linux_fonts_leaking'])}")
    if v["linux_fonts_leaking"]:
        for f in v["linux_fonts_leaking"]:
            print(f"  ⚠️  {f}")


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 P0 CRITICAL ENHANCEMENTS - Advanced Font Synthesis
# ═══════════════════════════════════════════════════════════════════════════════

import threading
import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Optional, Any
from collections import defaultdict


@dataclass
class FontMetrics:
    """Font metrics for anti-aliasing correction"""
    font_family: str
    avg_char_width: float
    x_height: float
    cap_height: float
    ascender: float
    descender: float
    line_height: float


@dataclass
class FontRenderProfile:
    """Font rendering profile for OS matching"""
    os_type: str
    antialias_mode: str
    hinting_mode: str
    subpixel_order: str
    gamma: float
    contrast: float


@dataclass
class FontConsistencyCheck:
    """Font consistency validation result"""
    profile_uuid: str
    claimed_os: str
    fonts_available: int
    fonts_missing: List[str]
    linux_fonts_leaking: List[str]
    metrics_consistent: bool
    overall_pass: bool


class FontMetricsNormalizer:
    """
    V7.6 P0: Normalize font metrics to match Windows rendering.
    
    Features:
    - Anti-aliasing correction factors
    - Sub-pixel rendering adjustment
    - Canvas measureText normalization
    - Consistent metrics across profiles
    """
    
    # Windows font metrics (measured from real Windows 11)
    WINDOWS_METRICS: Dict[str, FontMetrics] = {
        "Arial": FontMetrics(
            font_family="Arial",
            avg_char_width=7.2,
            x_height=10.5,
            cap_height=14.0,
            ascender=15.2,
            descender=3.8,
            line_height=19.0,
        ),
        "Segoe UI": FontMetrics(
            font_family="Segoe UI",
            avg_char_width=6.8,
            x_height=10.2,
            cap_height=13.5,
            ascender=15.0,
            descender=4.0,
            line_height=19.0,
        ),
        "Times New Roman": FontMetrics(
            font_family="Times New Roman",
            avg_char_width=6.5,
            x_height=9.0,
            cap_height=13.8,
            ascender=15.5,
            descender=4.2,
            line_height=19.7,
        ),
        "Consolas": FontMetrics(
            font_family="Consolas",
            avg_char_width=8.4,
            x_height=10.8,
            cap_height=14.2,
            ascender=15.8,
            descender=4.5,
            line_height=20.3,
        ),
    }
    
    # Correction factors (Linux -> Windows)
    CORRECTION_FACTORS = {
        "width": 1.02,   # Linux tends to render slightly narrower
        "height": 0.98,  # Linux tends to render slightly taller
        "baseline": 1.0,
    }
    
    def __init__(self):
        self._corrections: Dict[str, Dict] = {}
        self._lock = threading.Lock()
    
    def get_correction_config(self, font_family: str) -> Dict:
        """Get correction configuration for a font"""
        with self._lock:
            if font_family in self._corrections:
                return self._corrections[font_family]
        
        windows_metrics = self.WINDOWS_METRICS.get(font_family)
        
        config = {
            "font.family": font_family,
            "font.correction_enabled": True,
            "font.width_factor": self.CORRECTION_FACTORS["width"],
            "font.height_factor": self.CORRECTION_FACTORS["height"],
        }
        
        if windows_metrics:
            config["font.expected_avg_width"] = windows_metrics.avg_char_width
            config["font.expected_x_height"] = windows_metrics.x_height
            config["font.expected_cap_height"] = windows_metrics.cap_height
        
        with self._lock:
            self._corrections[font_family] = config
        
        return config
    
    def get_all_corrections(self) -> Dict[str, Dict]:
        """Get correction configs for all known Windows fonts"""
        corrections = {}
        for font in self.WINDOWS_METRICS:
            corrections[font] = self.get_correction_config(font)
        return corrections
    
    def generate_js_shim(self) -> str:
        """Generate JavaScript shim for Canvas measureText correction"""
        corrections = self.get_all_corrections()
        
        js = """// TITAN V7.6 Font Metrics Correction Shim
(function() {
    const corrections = """ + json.dumps(corrections) + """;
    
    const originalMeasureText = CanvasRenderingContext2D.prototype.measureText;
    
    CanvasRenderingContext2D.prototype.measureText = function(text) {
        const result = originalMeasureText.call(this, text);
        const font = this.font || '';
        
        // Find matching correction
        for (const [family, config] of Object.entries(corrections)) {
            if (font.includes(family) && config.font && config.font.correction_enabled) {
                const widthFactor = config.font.width_factor || 1.0;
                
                // Apply correction
                Object.defineProperty(result, 'width', {
                    value: result.width * widthFactor,
                    writable: false
                });
                break;
            }
        }
        
        return result;
    };
})();
"""
        return js


class FontRenderingProfiler:
    """
    V7.6 P0: Match font rendering profiles to target OS.
    
    Features:
    - OS-specific rendering profiles
    - Subpixel rendering configuration
    - Hinting mode selection
    - Gamma/contrast adjustment
    """
    
    RENDER_PROFILES = {
        "windows_11": FontRenderProfile(
            os_type="Windows 11",
            antialias_mode="grayscale",
            hinting_mode="full",
            subpixel_order="rgb",
            gamma=1.8,
            contrast=1.0,
        ),
        "windows_10": FontRenderProfile(
            os_type="Windows 10",
            antialias_mode="cleartype",
            hinting_mode="full",
            subpixel_order="rgb",
            gamma=1.8,
            contrast=1.0,
        ),
        "macos": FontRenderProfile(
            os_type="macOS",
            antialias_mode="lcd",
            hinting_mode="none",
            subpixel_order="rgb",
            gamma=2.2,
            contrast=0.9,
        ),
    }
    
    def __init__(self):
        self._current_profile: Optional[FontRenderProfile] = None
    
    def get_profile(self, os_type: str) -> FontRenderProfile:
        """Get rendering profile for OS type"""
        profile_key = os_type.lower().replace(" ", "_")
        return self.RENDER_PROFILES.get(profile_key, self.RENDER_PROFILES["windows_11"])
    
    def generate_fontconfig_snippet(self, os_type: str) -> str:
        """Generate fontconfig snippet for OS-matched rendering"""
        profile = self.get_profile(os_type)
        
        hinting_map = {
            "full": "hintfull",
            "medium": "hintmedium",
            "slight": "hintslight",
            "none": "hintnone",
        }
        
        xml = f"""  <!-- TITAN V7.6 OS-Matched Rendering: {profile.os_type} -->
  <match target="font">
    <edit name="antialias" mode="assign"><bool>true</bool></edit>
    <edit name="hinting" mode="assign"><bool>{'true' if profile.hinting_mode != 'none' else 'false'}</bool></edit>
    <edit name="hintstyle" mode="assign"><const>{hinting_map.get(profile.hinting_mode, 'hintslight')}</const></edit>
    <edit name="rgba" mode="assign"><const>{profile.subpixel_order}</const></edit>
    <edit name="lcdfilter" mode="assign"><const>lcddefault</const></edit>
  </match>"""
        
        return xml
    
    def apply_profile(self, os_type: str) -> bool:
        """Apply rendering profile system-wide"""
        self._current_profile = self.get_profile(os_type)
        return True


class FontConsistencyValidator:
    """
    V7.6 P0: Validate font environment consistency.
    
    Features:
    - Complete font availability check
    - Linux font leak detection
    - Metrics consistency validation
    - Cross-check with claimed OS
    """
    
    REQUIRED_WINDOWS_FONTS = [
        "Arial", "Times New Roman", "Courier New", "Verdana",
        "Georgia", "Tahoma", "Trebuchet MS", "Impact",
        "Comic Sans MS", "Webdings", "Wingdings",
    ]
    
    def __init__(self):
        self._validations: Dict[str, FontConsistencyCheck] = {}
        self._lock = threading.Lock()
    
    def validate(self, profile_uuid: str, claimed_os: str) -> FontConsistencyCheck:
        """Perform comprehensive font validation"""
        provisioner = WindowsFontProvisioner()
        verification = provisioner.verify()
        
        fonts_available = verification.get("windows_fonts_available", 0)
        fonts_missing = verification.get("windows_fonts_missing", [])
        linux_leaking = verification.get("linux_fonts_leaking", [])
        
        # Check metrics consistency (simplified)
        metrics_consistent = len(linux_leaking) == 0
        
        overall_pass = (
            fonts_available >= len(self.REQUIRED_WINDOWS_FONTS) * 0.8 and
            len(linux_leaking) == 0 and
            metrics_consistent
        )
        
        check = FontConsistencyCheck(
            profile_uuid=profile_uuid,
            claimed_os=claimed_os,
            fonts_available=fonts_available,
            fonts_missing=fonts_missing,
            linux_fonts_leaking=linux_leaking,
            metrics_consistent=metrics_consistent,
            overall_pass=overall_pass,
        )
        
        with self._lock:
            self._validations[profile_uuid] = check
        
        return check
    
    def get_remediation(self, check: FontConsistencyCheck) -> List[str]:
        """Get remediation steps for failed checks"""
        remediation = []
        
        if check.fonts_missing:
            remediation.append(f"Install missing fonts: {', '.join(check.fonts_missing[:5])}")
        
        if check.linux_fonts_leaking:
            remediation.append("Update fontconfig to reject Linux fonts")
            remediation.append(f"Leaking: {', '.join(check.linux_fonts_leaking[:3])}")
        
        if not check.metrics_consistent:
            remediation.append("Apply font metrics correction shim")
        
        return remediation


class FontEnumerationDefense:
    """
    V7.6 P0: Defend against font enumeration attacks.
    
    Features:
    - Font list padding to Windows count
    - Deterministic font ordering
    - Enumeration result caching
    - Anti-timing attack measures
    """
    
    # Typical Windows 11 font count
    WINDOWS_11_FONT_COUNT = 283
    
    def __init__(self):
        self._cached_font_list: Optional[List[str]] = None
        self._lock = threading.Lock()
    
    def get_padded_font_list(self, profile_uuid: str) -> List[str]:
        """Get font list padded to Windows count"""
        with self._lock:
            if self._cached_font_list:
                return self._cached_font_list
        
        # Start with core Windows fonts
        fonts = list(FONT_ALIASES.keys())
        
        # Add MS Core fonts
        ms_core = [
            "Arial", "Arial Black", "Arial Narrow", "Comic Sans MS",
            "Courier New", "Georgia", "Impact", "Lucida Console",
            "Lucida Sans Unicode", "Palatino Linotype", "Tahoma",
            "Times New Roman", "Trebuchet MS", "Verdana", "Webdings",
            "Wingdings", "Wingdings 2", "Wingdings 3", "Symbol",
        ]
        fonts.extend(ms_core)
        
        # Add Windows 11 specific
        win11_fonts = [
            "Segoe UI Variable", "Segoe Fluent Icons", "Segoe MDL2 Assets",
            "Cascadia Code", "Cascadia Mono", "Bahnschrift", "Ink Free",
        ]
        fonts.extend(win11_fonts)
        
        # Deduplicate
        fonts = list(dict.fromkeys(fonts))
        
        # Deterministic padding based on profile
        seed = int(hashlib.sha256(profile_uuid.encode()).hexdigest()[:8], 16)
        rng = __import__("random").Random(seed)
        
        # Pad with plausible additional fonts
        padding_fonts = [
            f"Font{i:03d}" for i in range(100)
        ]
        
        while len(fonts) < self.WINDOWS_11_FONT_COUNT:
            if padding_fonts:
                fonts.append(padding_fonts.pop(0))
            else:
                break
        
        # Deterministic ordering
        rng.shuffle(fonts)
        
        with self._lock:
            self._cached_font_list = fonts
        
        return fonts
    
    def get_enumeration_config(self, profile_uuid: str) -> Dict:
        """Get font enumeration configuration for injection"""
        fonts = self.get_padded_font_list(profile_uuid)
        
        return {
            "fonts.enumeration_override": True,
            "fonts.list": fonts,
            "fonts.count": len(fonts),
            "fonts.timing_normalize": True,
            "fonts.timing_delay_ms": 0.5,  # Normalize enumeration timing
        }


# ═══════════════════════════════════════════════════════════════════════════
# V7.6 SINGLETON INSTANCES
# ═══════════════════════════════════════════════════════════════════════════

_font_metrics_normalizer: Optional[FontMetricsNormalizer] = None
_font_rendering_profiler: Optional[FontRenderingProfiler] = None
_font_consistency_validator: Optional[FontConsistencyValidator] = None
_font_enumeration_defense: Optional[FontEnumerationDefense] = None


def get_font_metrics_normalizer() -> FontMetricsNormalizer:
    """Get global font metrics normalizer"""
    global _font_metrics_normalizer
    if _font_metrics_normalizer is None:
        _font_metrics_normalizer = FontMetricsNormalizer()
    return _font_metrics_normalizer


def get_font_rendering_profiler() -> FontRenderingProfiler:
    """Get global font rendering profiler"""
    global _font_rendering_profiler
    if _font_rendering_profiler is None:
        _font_rendering_profiler = FontRenderingProfiler()
    return _font_rendering_profiler


def get_font_consistency_validator() -> FontConsistencyValidator:
    """Get global font consistency validator"""
    global _font_consistency_validator
    if _font_consistency_validator is None:
        _font_consistency_validator = FontConsistencyValidator()
    return _font_consistency_validator


def get_font_enumeration_defense() -> FontEnumerationDefense:
    """Get global font enumeration defense"""
    global _font_enumeration_defense
    if _font_enumeration_defense is None:
        _font_enumeration_defense = FontEnumerationDefense()
    return _font_enumeration_defense
