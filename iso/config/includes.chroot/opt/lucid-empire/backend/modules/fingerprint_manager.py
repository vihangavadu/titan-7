"""
LUCID EMPIRE v7.0-TITAN - Fingerprint Manager
==============================================
Unified fingerprint management for all browser fingerprinting vectors.
"""

import hashlib
import json
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .canvas_noise import CanvasNoiseGenerator, WebGLNoiseGenerator, AudioNoiseGenerator


@dataclass
class BrowserFingerprint:
    """Complete browser fingerprint configuration."""
    
    # Navigator
    user_agent: str = ""
    platform: str = "Win32"
    language: str = "en-US"
    languages: List[str] = field(default_factory=lambda: ["en-US", "en"])
    hardware_concurrency: int = 8
    device_memory: int = 8
    max_touch_points: int = 0
    
    # Screen
    screen_width: int = 1920
    screen_height: int = 1080
    screen_avail_width: int = 1920
    screen_avail_height: int = 1040
    color_depth: int = 24
    pixel_ratio: float = 1.0
    
    # WebGL
    webgl_vendor: str = "Google Inc. (NVIDIA)"
    webgl_renderer: str = "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)"
    webgl_version: str = "WebGL 2.0 (OpenGL ES 3.0 Chromium)"
    
    # Audio
    audio_sample_rate: int = 48000
    audio_channels: int = 2
    
    # Canvas/WebGL/Audio seeds
    canvas_seed: str = ""
    webgl_seed: str = ""
    audio_seed: str = ""
    
    # Timezone
    timezone: str = "America/New_York"
    timezone_offset: int = -300  # minutes
    
    # Plugins (modern browsers report empty)
    plugins: List[str] = field(default_factory=list)
    
    # Client hints
    ch_ua: str = '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"'
    ch_ua_mobile: str = "?0"
    ch_ua_platform: str = '"Windows"'
    ch_ua_arch: str = '"x86"'
    ch_ua_bitness: str = '"64"'
    ch_ua_model: str = '""'
    ch_ua_full_version: str = '"120.0.6099.109"'


class FingerprintManager:
    """
    Manages browser fingerprint generation and modification.
    
    Creates consistent fingerprint profiles based on profile seeds,
    ensuring all fingerprinting vectors match the target persona.
    """
    
    # Common GPU vendors and renderers
    GPU_PROFILES = {
        "nvidia_desktop": [
            ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)"),
            ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce RTX 3070 Direct3D11 vs_5_0 ps_5_0, D3D11)"),
            ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce RTX 4060 Direct3D11 vs_5_0 ps_5_0, D3D11)"),
            ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 Super Direct3D11 vs_5_0 ps_5_0, D3D11)"),
        ],
        "amd_desktop": [
            ("Google Inc. (AMD)", "ANGLE (AMD, AMD Radeon RX 6700 XT Direct3D11 vs_5_0 ps_5_0, D3D11)"),
            ("Google Inc. (AMD)", "ANGLE (AMD, AMD Radeon RX 6600 Direct3D11 vs_5_0 ps_5_0, D3D11)"),
        ],
        "intel_integrated": [
            ("Google Inc. (Intel)", "ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)"),
            ("Google Inc. (Intel)", "ANGLE (Intel, Intel(R) UHD Graphics 770 Direct3D11 vs_5_0 ps_5_0, D3D11)"),
            ("Google Inc. (Intel)", "ANGLE (Intel, Intel(R) Iris Xe Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)"),
        ],
        "apple_silicon": [
            ("Apple Inc.", "Apple M1"),
            ("Apple Inc.", "Apple M1 Pro"),
            ("Apple Inc.", "Apple M2"),
            ("Apple Inc.", "Apple M2 Pro"),
        ],
        "mobile_qualcomm": [
            ("Qualcomm", "Adreno (TM) 740"),
            ("Qualcomm", "Adreno (TM) 730"),
            ("Qualcomm", "Adreno (TM) 650"),
        ],
    }
    
    # Screen resolution profiles by device type
    SCREEN_PROFILES = {
        "desktop_1080p": {"width": 1920, "height": 1080, "avail_height": 1040, "ratio": 1.0},
        "desktop_1440p": {"width": 2560, "height": 1440, "avail_height": 1400, "ratio": 1.0},
        "desktop_4k": {"width": 3840, "height": 2160, "avail_height": 2120, "ratio": 1.5},
        "laptop_1366": {"width": 1366, "height": 768, "avail_height": 728, "ratio": 1.0},
        "laptop_1536": {"width": 1536, "height": 864, "avail_height": 824, "ratio": 1.25},
        "macbook_retina": {"width": 2560, "height": 1440, "avail_height": 1415, "ratio": 2.0},
        "mobile_standard": {"width": 412, "height": 915, "avail_height": 857, "ratio": 2.625},
        "mobile_large": {"width": 428, "height": 926, "avail_height": 868, "ratio": 3.0},
    }
    
    def __init__(self, profile_seed: str):
        """
        Initialize with profile-specific seed.
        
        Args:
            profile_seed: Unique identifier (typically profile UUID)
        """
        self.seed = profile_seed
        self.seed_int = int(hashlib.sha256(profile_seed.encode()).hexdigest()[:8], 16)
        
        # Initialize noise generators
        self.canvas_noise = CanvasNoiseGenerator(profile_seed)
        self.webgl_noise = WebGLNoiseGenerator(profile_seed)
        self.audio_noise = AudioNoiseGenerator(profile_seed)
        
        # Seed random for consistent generation
        random.seed(self.seed_int)
    
    def generate_fingerprint(
        self,
        os_type: str = "windows",
        browser_type: str = "chrome",
        device_type: str = "desktop",
        gpu_type: Optional[str] = None
    ) -> BrowserFingerprint:
        """
        Generate a complete browser fingerprint.
        
        Args:
            os_type: windows, macos, linux, android, ios
            browser_type: chrome, firefox, safari, edge
            device_type: desktop, laptop, mobile
            gpu_type: nvidia_desktop, amd_desktop, intel_integrated, apple_silicon, mobile_qualcomm
        
        Returns:
            Complete BrowserFingerprint configuration
        """
        # Determine platform
        platforms = {
            "windows": "Win32",
            "macos": "MacIntel",
            "linux": "Linux x86_64",
            "android": "Linux armv81",
            "ios": "iPhone",
        }
        platform = platforms.get(os_type, "Win32")
        
        # Select GPU profile
        if gpu_type is None:
            if os_type == "windows":
                gpu_type = random.choice(["nvidia_desktop", "amd_desktop", "intel_integrated"])
            elif os_type == "macos":
                gpu_type = "apple_silicon"
            elif os_type == "android":
                gpu_type = "mobile_qualcomm"
            else:
                gpu_type = "intel_integrated"
        
        gpu_options = self.GPU_PROFILES.get(gpu_type, self.GPU_PROFILES["intel_integrated"])
        webgl_vendor, webgl_renderer = random.choice(gpu_options)
        
        # Select screen profile
        if device_type == "mobile":
            screen_key = random.choice(["mobile_standard", "mobile_large"])
        elif os_type == "macos":
            screen_key = "macbook_retina"
        else:
            screen_key = random.choice(["desktop_1080p", "desktop_1440p", "laptop_1536"])
        
        screen = self.SCREEN_PROFILES[screen_key]
        
        # Hardware specs
        if device_type == "mobile":
            hw_concurrency = random.choice([4, 6, 8])
            device_memory = random.choice([4, 6, 8])
            touch_points = 5
        else:
            hw_concurrency = random.choice([4, 6, 8, 12, 16])
            device_memory = random.choice([8, 16, 32])
            touch_points = 0
        
        # Generate seeds
        canvas_seed = hashlib.sha256(f"{self.seed}:canvas".encode()).hexdigest()[:16]
        webgl_seed = hashlib.sha256(f"{self.seed}:webgl".encode()).hexdigest()[:16]
        audio_seed = hashlib.sha256(f"{self.seed}:audio".encode()).hexdigest()[:16]
        
        # Client hints
        if browser_type == "chrome":
            ch_ua = f'"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"'
        elif browser_type == "edge":
            ch_ua = f'"Not_A Brand";v="8", "Chromium";v="120", "Microsoft Edge";v="120"'
        else:
            ch_ua = ""
        
        ch_ua_platform = {
            "windows": '"Windows"',
            "macos": '"macOS"',
            "linux": '"Linux"',
            "android": '"Android"',
            "ios": '"iOS"',
        }.get(os_type, '"Windows"')
        
        return BrowserFingerprint(
            platform=platform,
            hardware_concurrency=hw_concurrency,
            device_memory=device_memory,
            max_touch_points=touch_points,
            screen_width=screen["width"],
            screen_height=screen["height"],
            screen_avail_width=screen["width"],
            screen_avail_height=screen["avail_height"],
            pixel_ratio=screen["ratio"],
            webgl_vendor=webgl_vendor,
            webgl_renderer=webgl_renderer,
            canvas_seed=canvas_seed,
            webgl_seed=webgl_seed,
            audio_seed=audio_seed,
            ch_ua=ch_ua,
            ch_ua_platform=ch_ua_platform,
            ch_ua_mobile="?1" if device_type == "mobile" else "?0",
        )
    
    def get_injection_script(self, fingerprint: BrowserFingerprint) -> str:
        """
        Generate JavaScript code to inject fingerprint overrides.
        
        Args:
            fingerprint: Fingerprint configuration
        
        Returns:
            JavaScript code as string
        """
        canvas_params = self.canvas_noise.get_fingerprint_modifier()
        webgl_params = self.webgl_noise.get_webgl_noise_params()
        audio_params = self.audio_noise.get_audio_noise_params()
        
        script = f"""
// TITAN Fingerprint Injection
(function() {{
    'use strict';
    
    const FINGERPRINT = {{
        navigator: {{
            platform: "{fingerprint.platform}",
            hardwareConcurrency: {fingerprint.hardware_concurrency},
            deviceMemory: {fingerprint.device_memory},
            maxTouchPoints: {fingerprint.max_touch_points},
            language: "{fingerprint.language}",
            languages: {json.dumps(fingerprint.languages)},
        }},
        screen: {{
            width: {fingerprint.screen_width},
            height: {fingerprint.screen_height},
            availWidth: {fingerprint.screen_avail_width},
            availHeight: {fingerprint.screen_avail_height},
            colorDepth: {fingerprint.color_depth},
            pixelDepth: {fingerprint.color_depth},
        }},
        webgl: {{
            vendor: "{fingerprint.webgl_vendor}",
            renderer: "{fingerprint.webgl_renderer}",
        }},
        canvas: {json.dumps(canvas_params)},
        audio: {json.dumps(audio_params)},
    }};
    
    // Override navigator properties
    for (const [key, value] of Object.entries(FINGERPRINT.navigator)) {{
        Object.defineProperty(navigator, key, {{ get: () => value }});
    }}
    
    // Override screen properties
    for (const [key, value] of Object.entries(FINGERPRINT.screen)) {{
        Object.defineProperty(screen, key, {{ get: () => value }});
    }}
    
    // Override WebGL
    const getParameterOrig = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(param) {{
        if (param === 37445) return FINGERPRINT.webgl.vendor;
        if (param === 37446) return FINGERPRINT.webgl.renderer;
        return getParameterOrig.call(this, param);
    }};
    
    // Canvas noise injection
    const toDataURLOrig = HTMLCanvasElement.prototype.toDataURL;
    HTMLCanvasElement.prototype.toDataURL = function() {{
        const ctx = this.getContext('2d');
        if (ctx) {{
            const imageData = ctx.getImageData(0, 0, this.width, this.height);
            const seed = FINGERPRINT.canvas.seed;
            // Apply subtle noise
            for (let i = 0; i < imageData.data.length; i += 4) {{
                const noise = ((seed + i) % 5) - 2;
                imageData.data[i] = Math.max(0, Math.min(255, imageData.data[i] + noise));
            }}
            ctx.putImageData(imageData, 0, 0);
        }}
        return toDataURLOrig.apply(this, arguments);
    }};
    
    console.log('[TITAN] Fingerprint injection active');
}})();
"""
        return script
    
    def to_dict(self, fingerprint: BrowserFingerprint) -> Dict[str, Any]:
        """Convert fingerprint to dictionary."""
        return {
            "navigator": {
                "user_agent": fingerprint.user_agent,
                "platform": fingerprint.platform,
                "language": fingerprint.language,
                "languages": fingerprint.languages,
                "hardware_concurrency": fingerprint.hardware_concurrency,
                "device_memory": fingerprint.device_memory,
                "max_touch_points": fingerprint.max_touch_points,
            },
            "screen": {
                "width": fingerprint.screen_width,
                "height": fingerprint.screen_height,
                "avail_width": fingerprint.screen_avail_width,
                "avail_height": fingerprint.screen_avail_height,
                "color_depth": fingerprint.color_depth,
                "pixel_ratio": fingerprint.pixel_ratio,
            },
            "webgl": {
                "vendor": fingerprint.webgl_vendor,
                "renderer": fingerprint.webgl_renderer,
                "version": fingerprint.webgl_version,
            },
            "audio": {
                "sample_rate": fingerprint.audio_sample_rate,
                "channels": fingerprint.audio_channels,
            },
            "seeds": {
                "canvas": fingerprint.canvas_seed,
                "webgl": fingerprint.webgl_seed,
                "audio": fingerprint.audio_seed,
            },
            "timezone": {
                "name": fingerprint.timezone,
                "offset": fingerprint.timezone_offset,
            },
            "client_hints": {
                "ua": fingerprint.ch_ua,
                "mobile": fingerprint.ch_ua_mobile,
                "platform": fingerprint.ch_ua_platform,
            },
        }
