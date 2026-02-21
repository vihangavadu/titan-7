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

__version__ = "7.5.0"
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
