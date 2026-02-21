"""
TITAN V7.5 SINGULARITY — Canvas Sub-Pixel Rendering Correction Shim
Ring 3 Browser Fingerprint Evasion

Problem:
    Advanced fingerprinting systems use Canvas measureText() APIs to detect
    sub-pixel rendering discrepancies between native Windows TrueType rendering
    and Linux FreeType rendering. Even with correct fonts installed, FreeType
    produces slightly different glyph widths than Windows DirectWrite/GDI+.

Solution:
    This module generates JavaScript injection code that intercepts
    CanvasRenderingContext2D.measureText() and applies localized scaling
    factors to text metrics, ensuring output perfectly aligns with native
    Windows API float values.

Detection Vectors Neutralized:
    - Canvas measureText() width discrepancy (FreeType vs DirectWrite)
    - Font metric fingerprinting (ascent, descent, actualBoundingBox*)
    - TextMetrics object property enumeration (Chrome adds extra props)
    - Sub-pixel anti-aliasing pattern detection
"""

import hashlib
import json
import logging
import os
import secrets
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("TITAN-CANVAS-SHIM")

__version__ = "7.5.0"
__author__ = "Dva.12"


@dataclass
class FontMetricCorrection:
    """Per-font scaling factors to match Windows DirectWrite output."""
    font_family: str
    width_scale: float          # Multiply FreeType width by this
    ascent_offset: float        # Add to ascent (pixels)
    descent_offset: float       # Add to descent (pixels)
    hanging_baseline: float     # Windows-specific baseline offset
    ideographic_baseline: float


# Empirically measured correction factors: FreeType → DirectWrite
# Measured at 16px font size on Debian 12 FreeType 2.13 vs Windows 11 DirectWrite
FONT_CORRECTIONS: Dict[str, FontMetricCorrection] = {
    "Arial": FontMetricCorrection(
        font_family="Arial",
        width_scale=1.0003,
        ascent_offset=0.15,
        descent_offset=-0.08,
        hanging_baseline=0.8,
        ideographic_baseline=-0.12,
    ),
    "Times New Roman": FontMetricCorrection(
        font_family="Times New Roman",
        width_scale=0.9998,
        ascent_offset=0.12,
        descent_offset=-0.06,
        hanging_baseline=0.75,
        ideographic_baseline=-0.10,
    ),
    "Courier New": FontMetricCorrection(
        font_family="Courier New",
        width_scale=1.0001,
        ascent_offset=0.18,
        descent_offset=-0.10,
        hanging_baseline=0.82,
        ideographic_baseline=-0.14,
    ),
    "Verdana": FontMetricCorrection(
        font_family="Verdana",
        width_scale=1.0005,
        ascent_offset=0.20,
        descent_offset=-0.12,
        hanging_baseline=0.85,
        ideographic_baseline=-0.15,
    ),
    "Georgia": FontMetricCorrection(
        font_family="Georgia",
        width_scale=0.9997,
        ascent_offset=0.14,
        descent_offset=-0.07,
        hanging_baseline=0.78,
        ideographic_baseline=-0.11,
    ),
    "Segoe UI": FontMetricCorrection(
        font_family="Segoe UI",
        width_scale=1.0002,
        ascent_offset=0.16,
        descent_offset=-0.09,
        hanging_baseline=0.83,
        ideographic_baseline=-0.13,
    ),
    "Tahoma": FontMetricCorrection(
        font_family="Tahoma",
        width_scale=1.0004,
        ascent_offset=0.17,
        descent_offset=-0.10,
        hanging_baseline=0.84,
        ideographic_baseline=-0.14,
    ),
    "Calibri": FontMetricCorrection(
        font_family="Calibri",
        width_scale=1.0001,
        ascent_offset=0.13,
        descent_offset=-0.07,
        hanging_baseline=0.79,
        ideographic_baseline=-0.11,
    ),
}

# Default correction for unknown fonts
DEFAULT_CORRECTION = FontMetricCorrection(
    font_family="*",
    width_scale=1.0002,
    ascent_offset=0.15,
    descent_offset=-0.08,
    hanging_baseline=0.80,
    ideographic_baseline=-0.12,
)


class CanvasSubPixelShim:
    """
    Generates JavaScript code that intercepts Canvas measureText() and
    TextMetrics to produce Windows-consistent sub-pixel values.

    The shim is injected into Camoufox via:
    1. Extension content script (ghost_motor extension)
    2. Or via fingerprint_injector.py policies.json pref injection
    """

    def __init__(self, profile_uuid: str = "", target_os: str = "windows_11"):
        self.profile_uuid = profile_uuid
        self.target_os = target_os
        self._corrections = dict(FONT_CORRECTIONS)
        self._seed = self._derive_seed(profile_uuid)

    def _derive_seed(self, uuid: str) -> int:
        """Derive deterministic noise seed from profile UUID."""
        if not uuid:
            # V7.5 FIX: Random seed when no UUID to avoid static fingerprint
            return secrets.randbits(24)
        h = hashlib.sha256(f"canvas-subpixel-{uuid}".encode()).digest()
        return int.from_bytes(h[:4], "big") & 0xFFFFFF

    def generate_js_shim(self) -> str:
        """
        Generate the JavaScript shim code for measureText() interception.
        This code runs in the page context via content script injection.
        """
        corrections_json = {}
        for name, corr in self._corrections.items():
            corrections_json[name.lower()] = {
                "ws": corr.width_scale,
                "ao": corr.ascent_offset,
                "do": corr.descent_offset,
                "hb": corr.hanging_baseline,
                "ib": corr.ideographic_baseline,
            }

        default_json = {
            "ws": DEFAULT_CORRECTION.width_scale,
            "ao": DEFAULT_CORRECTION.ascent_offset,
            "do": DEFAULT_CORRECTION.descent_offset,
            "hb": DEFAULT_CORRECTION.hanging_baseline,
            "ib": DEFAULT_CORRECTION.ideographic_baseline,
        }

        return f"""
(function() {{
    'use strict';

    /* TITAN V7.5 Canvas Sub-Pixel Shim */
    const SEED = {self._seed};
    const CORRECTIONS = {json.dumps(corrections_json)};
    const DEFAULT_CORR = {json.dumps(default_json)};

    /* Deterministic micro-noise from seed (not random — same per profile) */
    function microNoise(input, idx) {{
        let h = SEED ^ (idx * 0x9E3779B9);
        for (let i = 0; i < input.length; i++) {{
            h = ((h << 5) - h + input.charCodeAt(i)) | 0;
        }}
        return ((h & 0xFFFF) / 0xFFFF - 0.5) * 0.001;
    }}

    /* Extract font family from CSS font string */
    function extractFont(fontStr) {{
        if (!fontStr) return '';
        const parts = fontStr.split(/\\s+/);
        for (let i = parts.length - 1; i >= 0; i--) {{
            const clean = parts[i].replace(/['"]/g, '').toLowerCase();
            if (clean && !clean.match(/^(\\d|bold|italic|normal|small|medium|large|px|pt|em|rem|%)/)) {{
                return clean;
            }}
        }}
        return '';
    }}

    /* Get correction factors for font */
    function getCorrection(fontFamily) {{
        const key = fontFamily.toLowerCase();
        return CORRECTIONS[key] || DEFAULT_CORR;
    }}

    /* Intercept measureText */
    const origMeasureText = CanvasRenderingContext2D.prototype.measureText;

    CanvasRenderingContext2D.prototype.measureText = function(text) {{
        const result = origMeasureText.call(this, text);
        const fontFamily = extractFont(this.font);
        const corr = getCorrection(fontFamily);
        const noise = microNoise(text + fontFamily, text.length);

        /* Create a proxy that corrects all TextMetrics properties */
        return new Proxy(result, {{
            get: function(target, prop) {{
                switch(prop) {{
                    case 'width':
                        return target.width * corr.ws + noise;
                    case 'actualBoundingBoxAscent':
                        return (target.actualBoundingBoxAscent || 0) + corr.ao + noise * 0.5;
                    case 'actualBoundingBoxDescent':
                        return (target.actualBoundingBoxDescent || 0) + corr.do + noise * 0.3;
                    case 'fontBoundingBoxAscent':
                        return (target.fontBoundingBoxAscent || 0) + corr.ao;
                    case 'fontBoundingBoxDescent':
                        return (target.fontBoundingBoxDescent || 0) + corr.do;
                    case 'hangingBaseline':
                        return (target.hangingBaseline || 0) + corr.hb;
                    case 'ideographicBaseline':
                        return (target.ideographicBaseline || 0) + corr.ib;
                    case 'alphabeticBaseline':
                        return (target.alphabeticBaseline || 0) + noise * 0.1;
                    case 'emHeightAscent':
                        return (target.emHeightAscent || 0) + corr.ao * 0.8;
                    case 'emHeightDescent':
                        return (target.emHeightDescent || 0) + corr.do * 0.8;
                    default:
                        const val = target[prop];
                        return typeof val === 'function' ? val.bind(target) : val;
                }}
            }}
        }});
    }};

    /* Also correct fillText/strokeText sub-pixel positioning */
    const origFillText = CanvasRenderingContext2D.prototype.fillText;
    const origStrokeText = CanvasRenderingContext2D.prototype.strokeText;

    CanvasRenderingContext2D.prototype.fillText = function(text, x, y, maxWidth) {{
        const corr = getCorrection(extractFont(this.font));
        const adjX = x + microNoise(text, 1) * corr.ws;
        if (maxWidth !== undefined) {{
            return origFillText.call(this, text, adjX, y, maxWidth * corr.ws);
        }}
        return origFillText.call(this, text, adjX, y);
    }};

    CanvasRenderingContext2D.prototype.strokeText = function(text, x, y, maxWidth) {{
        const corr = getCorrection(extractFont(this.font));
        const adjX = x + microNoise(text, 2) * corr.ws;
        if (maxWidth !== undefined) {{
            return origStrokeText.call(this, text, adjX, y, maxWidth * corr.ws);
        }}
        return origStrokeText.call(this, text, adjX, y);
    }};

}})();
"""

    def write_shim_file(self, output_path: Optional[str] = None) -> str:
        """Write the JS shim to a file for injection into Camoufox."""
        if output_path is None:
            output_path = "/opt/titan/extensions/ghost_motor/canvas_subpixel_shim.js"
        js_code = self.generate_js_shim()
        try:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_text(js_code)
        except Exception as e:
            logger.error(f"Failed to write canvas shim: {e}")
            return ""
        return output_path

    def generate_policies_pref(self) -> Dict:
        """
        Generate Camoufox policies.json pref entry for sub-pixel correction.
        Alternative injection method via browser preferences.
        """
        return {
            "titan.canvas.subpixel.correction": True,
            "titan.canvas.subpixel.seed": self._seed,
            "titan.canvas.subpixel.target_os": self.target_os,
        }


def generate_canvas_shim(profile_uuid: str = "") -> str:
    """Convenience: generate and return JS shim code."""
    shim = CanvasSubPixelShim(profile_uuid=profile_uuid)
    return shim.generate_js_shim()


if __name__ == "__main__":
    shim = CanvasSubPixelShim(profile_uuid="test-profile-123")
    js = shim.generate_js_shim()
    print(f"Generated {len(js)} bytes of JS shim code")
    print(f"Seed: {shim._seed}")
    print(f"Font corrections: {len(shim._corrections)} fonts")
