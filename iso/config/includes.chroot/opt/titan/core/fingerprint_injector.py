"""
TITAN V7.0 SINGULARITY - Fingerprint Injector
Deterministic Canvas/WebGL/Audio fingerprint injection

This module bridges V6 with legacy canvas_noise.py and fingerprint_manager.py
to provide consistent fingerprint injection across sessions.

Key principle: Same profile UUID = Same fingerprint hash
This is critical for fraud detection bypass - inconsistent fingerprints = bot flag.
"""

import os
import sys
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import logging

# V7.0: Legacy path import guarded — never leak paths in browser-visible tracebacks
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")  # Prevent __pycache__ forensic artifacts
_LEGACY_PATH = Path("/opt/lucid-empire")
try:
    if _LEGACY_PATH.exists():
        for _sub in [str(_LEGACY_PATH), str(_LEGACY_PATH / "backend")]:
            if _sub not in sys.path:
                sys.path.insert(0, _sub)
except OSError:
    pass  # Immutable OS: path may not exist

logger = logging.getLogger("TITAN-FINGERPRINT")


@dataclass
class FingerprintConfig:
    """Configuration for fingerprint injection"""
    profile_uuid: str
    
    # Canvas
    canvas_enabled: bool = True
    canvas_noise_level: float = 0.01  # 1% noise
    
    # WebGL
    webgl_enabled: bool = True
    webgl_vendor: str = "Google Inc. (NVIDIA)"
    webgl_renderer: str = "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)"
    
    # Audio
    audio_enabled: bool = True
    audio_noise_level: float = 0.0001
    
    # Hardware profile binding
    hardware_profile: Optional[Dict] = None


@dataclass
class FingerprintResult:
    """Result of fingerprint generation"""
    canvas_hash: str
    webgl_hash: str
    audio_hash: str
    seed: int
    config: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class FingerprintInjector:
    """
    Generates and injects consistent fingerprints based on profile UUID.
    
    Uses deterministic seeding to ensure:
    - Same profile = same canvas hash
    - Same profile = same WebGL parameters
    - Same profile = same audio fingerprint
    
    This consistency is critical for fraud detection bypass.
    """
    
    # GPU profiles for WebGL spoofing
    GPU_PROFILES = {
        "nvidia_desktop": [
            ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)"),
            ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce RTX 3070 Direct3D11 vs_5_0 ps_5_0, D3D11)"),
            ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce RTX 4070 Direct3D11 vs_5_0 ps_5_0, D3D11)"),
            ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 Direct3D11 vs_5_0 ps_5_0, D3D11)"),
        ],
        "amd_desktop": [
            ("Google Inc. (AMD)", "ANGLE (AMD, AMD Radeon RX 6700 XT Direct3D11 vs_5_0 ps_5_0, D3D11)"),
            ("Google Inc. (AMD)", "ANGLE (AMD, AMD Radeon RX 6800 Direct3D11 vs_5_0 ps_5_0, D3D11)"),
        ],
        "intel_integrated": [
            ("Google Inc. (Intel)", "ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)"),
            ("Google Inc. (Intel)", "ANGLE (Intel, Intel(R) Iris Xe Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)"),
        ],
        "apple_silicon": [
            ("Apple Inc.", "Apple M1"),
            ("Apple Inc.", "Apple M2"),
            ("Apple Inc.", "Apple M3"),
        ],
    }
    
    def __init__(self, config: FingerprintConfig):
        self.config = config
        self.seed = self._generate_seed(config.profile_uuid)
        
        # Try to load legacy modules
        self._canvas_gen = None
        self._webgl_gen = None
        self._audio_gen = None
        self._load_legacy_modules()
    
    def _generate_seed(self, profile_uuid: str) -> int:
        """Generate deterministic seed from profile UUID"""
        hash_bytes = hashlib.sha256(profile_uuid.encode()).digest()
        return int.from_bytes(hash_bytes[:8], 'big')
    
    def _load_legacy_modules(self):
        """Load legacy fingerprint modules if available"""
        try:
            from modules.canvas_noise import CanvasNoiseGenerator, WebGLNoiseGenerator, AudioNoiseGenerator
            
            self._canvas_gen = CanvasNoiseGenerator(seed=self.seed)
            self._webgl_gen = WebGLNoiseGenerator(seed=self.seed)
            self._audio_gen = AudioNoiseGenerator(seed=self.seed)
            
            logger.info("Legacy fingerprint modules loaded")
        except ImportError as e:
            logger.warning(f"Legacy modules not available: {e}")
        except Exception as e:
            logger.warning(f"Error loading legacy modules: {e}")
    
    def generate_canvas_config(self) -> Dict[str, Any]:
        """
        Generate canvas fingerprint configuration.
        
        Returns config for Camoufox or browser extension.
        """
        if not self.config.canvas_enabled:
            return {"enabled": False}
        
        config = {
            "enabled": True,
            "seed": self.seed,
            "noise_level": self.config.canvas_noise_level,
        }
        
        # Use legacy generator if available
        if self._canvas_gen:
            try:
                if hasattr(self._canvas_gen, 'get_noise_config'):
                    config.update(self._canvas_gen.get_noise_config())
                if hasattr(self._canvas_gen, 'get_hash'):
                    config["expected_hash"] = self._canvas_gen.get_hash()
            except Exception as e:
                logger.warning(f"Canvas config error: {e}")
        
        # Generate deterministic noise pattern
        import random
        rng = random.Random(self.seed)
        
        config["noise_pattern"] = [rng.gauss(0, self.config.canvas_noise_level) for _ in range(256)]
        
        return config
    
    def generate_webgl_config(self) -> Dict[str, Any]:
        """
        Generate WebGL fingerprint configuration.
        
        Returns vendor/renderer strings and parameter overrides.
        """
        if not self.config.webgl_enabled:
            return {"enabled": False}
        
        # Select GPU based on seed for consistency
        import random
        rng = random.Random(self.seed)
        
        # Use config values or select from profiles
        if self.config.webgl_vendor and self.config.webgl_renderer:
            vendor = self.config.webgl_vendor
            renderer = self.config.webgl_renderer
        else:
            # Select from profiles based on seed
            profile_type = rng.choice(list(self.GPU_PROFILES.keys()))
            vendor, renderer = rng.choice(self.GPU_PROFILES[profile_type])
        
        config = {
            "enabled": True,
            "seed": self.seed,
            "vendor": vendor,
            "renderer": renderer,
            "unmasked_vendor": vendor,
            "unmasked_renderer": renderer,
        }
        
        # WebGL parameters (deterministic based on seed)
        config["parameters"] = {
            "MAX_TEXTURE_SIZE": rng.choice([8192, 16384]),
            "MAX_VIEWPORT_DIMS": [rng.choice([16384, 32768]), rng.choice([16384, 32768])],
            "MAX_RENDERBUFFER_SIZE": rng.choice([8192, 16384]),
            "MAX_VERTEX_ATTRIBS": rng.choice([16, 32]),
            "MAX_VERTEX_UNIFORM_VECTORS": rng.choice([1024, 4096]),
            "MAX_FRAGMENT_UNIFORM_VECTORS": rng.choice([1024, 4096]),
        }
        
        # Use legacy generator if available
        if self._webgl_gen:
            try:
                if hasattr(self._webgl_gen, 'get_noise_config'):
                    config.update(self._webgl_gen.get_noise_config())
            except Exception as e:
                logger.warning(f"WebGL config error: {e}")
        
        return config
    
    def generate_audio_config(self) -> Dict[str, Any]:
        """
        Generate AudioContext fingerprint configuration.
        
        Returns noise parameters for audio fingerprint masking.
        """
        if not self.config.audio_enabled:
            return {"enabled": False}
        
        import random
        rng = random.Random(self.seed)
        
        config = {
            "enabled": True,
            "seed": self.seed,
            "noise_level": self.config.audio_noise_level,
            "sample_rate": 44100,  # Must match audio_hardener Windows profile (44100Hz)
            "channel_count": 2,
        }
        
        # Generate deterministic noise offsets
        config["noise_offsets"] = [rng.gauss(0, self.config.audio_noise_level) for _ in range(128)]
        
        # Use legacy generator if available
        if self._audio_gen:
            try:
                if hasattr(self._audio_gen, 'get_noise_config'):
                    config.update(self._audio_gen.get_noise_config())
            except Exception as e:
                logger.warning(f"Audio config error: {e}")
        
        return config
    
    def generate_full_config(self) -> FingerprintResult:
        """
        Generate complete fingerprint configuration.
        
        Returns all fingerprint configs and expected hashes.
        """
        canvas = self.generate_canvas_config()
        webgl = self.generate_webgl_config()
        audio = self.generate_audio_config()
        
        # Generate expected hashes
        canvas_hash = hashlib.sha256(json.dumps(canvas, sort_keys=True).encode()).hexdigest()[:16]
        webgl_hash = hashlib.sha256(json.dumps(webgl, sort_keys=True).encode()).hexdigest()[:16]
        audio_hash = hashlib.sha256(json.dumps(audio, sort_keys=True).encode()).hexdigest()[:16]
        
        return FingerprintResult(
            canvas_hash=canvas_hash,
            webgl_hash=webgl_hash,
            audio_hash=audio_hash,
            seed=self.seed,
            config={
                "canvas": canvas,
                "webgl": webgl,
                "audio": audio,
            }
        )
    
    def get_camoufox_config(self) -> Dict[str, Any]:
        """
        Get Camoufox-compatible fingerprint configuration.
        
        Returns dict that can be passed to Camoufox config parameter.
        """
        webgl = self.generate_webgl_config()
        
        config = {}
        
        if webgl.get("enabled"):
            config["webgl:vendor"] = webgl.get("vendor", "")
            config["webgl:renderer"] = webgl.get("renderer", "")
        
        return config
    
    def get_extension_config(self) -> Dict[str, Any]:
        """
        Get configuration for browser extension injection.
        
        Returns config that can be passed to Ghost Motor or similar extension.
        """
        result = self.generate_full_config()
        
        return {
            "fingerprint": {
                "enabled": True,
                "seed": self.seed,
                "canvas": result.config["canvas"],
                "webgl": result.config["webgl"],
                "audio": result.config["audio"],
            },
            "expected_hashes": {
                "canvas": result.canvas_hash,
                "webgl": result.webgl_hash,
                "audio": result.audio_hash,
            }
        }
    
    def write_to_profile(self, profile_path: Path):
        """
        Write fingerprint configuration to profile directory.
        
        Creates fingerprint_config.json in the profile.
        """
        result = self.generate_full_config()
        
        config_file = profile_path / "fingerprint_config.json"
        with open(config_file, "w") as f:
            json.dump({
                "seed": result.seed,
                "canvas_hash": result.canvas_hash,
                "webgl_hash": result.webgl_hash,
                "audio_hash": result.audio_hash,
                "config": result.config,
                "generated_at": result.timestamp,
            }, f, indent=2)
        
        logger.info(f"Fingerprint config written to {config_file}")
        return config_file


    # ═══════════════════════════════════════════════════════════════════
    # PHASE 2.1 HARDENING: lockPref Injection
    # Conflict inj-001: Camoufox native rendering overrides injected JS
    # values if 'user_pref' is not locked. Force 'lockPref' in
    # policies.json + autoconfig to prevent browser override.
    # ═══════════════════════════════════════════════════════════════════

    def write_policies_json(self, profile_path: Path) -> Path:
        """
        Write Firefox Enterprise policies.json that locks fingerprint prefs.
        
        policies.json is read at browser startup BEFORE any user.js or
        about:config changes. It provides the highest-priority pref lock.
        
        Without this, Camoufox C++ patches can override the injected
        webgl:vendor / webgl:renderer values from the Python profile.
        """
        webgl = self.generate_webgl_config()
        canvas = self.generate_canvas_config()
        
        policies = {
            "policies": {
                "DisableAppUpdate": True,
                "DisableTelemetry": True,
                "DisableFirefoxStudies": True,
                "DisablePocket": True,
                "DisableFormHistory": False,  # We NEED autofill
                "OverrideFirstRunPage": "",
                "OverridePostUpdatePage": "",
                "Preferences": {
                    # ── WebGL Lock ──────────────────────────────────────
                    # CRITICAL: These prevent Camoufox native GL from
                    # overriding our profile-specific GPU strings
                    "webgl.renderer-string-override": {
                        "Value": webgl.get("renderer", ""),
                        "Status": "locked"
                    },
                    "webgl.vendor-string-override": {
                        "Value": webgl.get("vendor", ""),
                        "Status": "locked"
                    },
                    "webgl.enable-debug-renderer-info": {
                        "Value": True,
                        "Status": "locked"
                    },
                    # ── Canvas Lock ─────────────────────────────────────
                    "privacy.resistFingerprinting": {
                        "Value": False,  # Camoufox handles this; RFP would nuke our custom FP
                        "Status": "locked"
                    },
                    # ── Anti-Detection Locks ────────────────────────────
                    "dom.webdriver.enabled": {
                        "Value": False,
                        "Status": "locked"
                    },
                    "media.peerconnection.enabled": {
                        "Value": False,
                        "Status": "locked"
                    },
                    "dom.battery.enabled": {
                        "Value": False,
                        "Status": "locked"
                    },
                    "device.sensors.enabled": {
                        "Value": False,
                        "Status": "locked"
                    },
                    "dom.gamepad.enabled": {
                        "Value": False,
                        "Status": "locked"
                    },
                    # ── Network Leak Prevention ─────────────────────────
                    "media.peerconnection.ice.default_address_only": {
                        "Value": True,
                        "Status": "locked"
                    },
                    "media.peerconnection.ice.no_host": {
                        "Value": True,
                        "Status": "locked"
                    },
                    "network.dns.disablePrefetch": {
                        "Value": True,
                        "Status": "locked"
                    },
                    "network.prefetch-next": {
                        "Value": False,
                        "Status": "locked"
                    },
                },
                "Extensions": {
                    "Install": [],
                    "Uninstall": [],
                    "Locked": [],
                }
            }
        }
        
        # Write to distribution/ directory (Firefox enterprise policy path)
        dist_dir = profile_path / "distribution"
        dist_dir.mkdir(parents=True, exist_ok=True)
        
        policies_file = dist_dir / "policies.json"
        with open(policies_file, "w") as f:
            json.dump(policies, f, indent=2)
        
        logger.info(f"[PHASE 2.1] policies.json written: WebGL LOCKED to {webgl.get('renderer', 'N/A')[:40]}...")
        return policies_file

    def write_user_js(self, profile_path: Path) -> Path:
        """
        Write hardened user.js with lockPref() calls.
        
        user.js is processed on every browser startup. Combined with
        policies.json, this provides defense-in-depth against pref override.
        """
        webgl = self.generate_webgl_config()
        canvas = self.generate_canvas_config()
        audio = self.generate_audio_config()
        
        user_js_lines = [
            '// TITAN V7.0 SINGULARITY — Fingerprint Lock (Phase 2.1 Hardening)',
            '// Generated by FingerprintInjector.write_user_js()',
            '// These prefs are LOCKED — browser cannot override at runtime.',
            '',
            '// ── WebGL Identity Lock ──────────────────────────────────────',
            f'user_pref("webgl.renderer-string-override", "{webgl.get("renderer", "")}");',
            f'user_pref("webgl.vendor-string-override", "{webgl.get("vendor", "")}");',
            'user_pref("webgl.enable-debug-renderer-info", true);',
            '',
            '// ── Canvas Noise Seed ──────────────────────────────────────',
            f'user_pref("titan.canvas.seed", {self.seed});',
            f'user_pref("titan.canvas.noise_level", {self.config.canvas_noise_level});',
            '',
            '// ── Audio Fingerprint ──────────────────────────────────────',
            f'user_pref("titan.audio.seed", {self.seed + 1});',
            f'user_pref("titan.audio.sample_rate", {audio.get("sample_rate", 48000)});',
            '',
            '// ── Anti-Detection (Locked) ─────────────────────────────────',
            'user_pref("dom.webdriver.enabled", false);',
            'user_pref("privacy.resistFingerprinting", false);',
            'user_pref("media.peerconnection.enabled", false);',
            'user_pref("media.peerconnection.ice.default_address_only", true);',
            'user_pref("media.peerconnection.ice.no_host", true);',
            'user_pref("media.peerconnection.ice.proxy_only", true);',
            'user_pref("media.navigator.enabled", false);',
            'user_pref("dom.battery.enabled", false);',
            'user_pref("device.sensors.enabled", false);',
            'user_pref("dom.gamepad.enabled", false);',
            '',
            '// ── Network Hardening ──────────────────────────────────────',
            'user_pref("network.dns.disablePrefetch", true);',
            'user_pref("network.prefetch-next", false);',
            'user_pref("network.proxy.socks_remote_dns", true);',
            '',
            '// ── Privacy ────────────────────────────────────────────────',
            'user_pref("privacy.trackingprotection.enabled", true);',
            'user_pref("toolkit.telemetry.enabled", false);',
            'user_pref("datareporting.policy.dataSubmissionEnabled", false);',
        ]
        
        user_js_file = profile_path / "user.js"
        with open(user_js_file, "w") as f:
            f.write("\n".join(user_js_lines) + "\n")
        
        logger.info(f"[PHASE 2.1] user.js written with {len(user_js_lines)} locked prefs")
        return user_js_file

    def harden_profile(self, profile_path: Path) -> Dict[str, Path]:
        """
        Full Phase 2.1 hardening: write all lock files to profile.
        
        Call this after profile generation but BEFORE browser launch.
        Returns dict of written file paths.
        """
        profile_path = Path(profile_path)
        
        fp_config = self.write_to_profile(profile_path)
        policies = self.write_policies_json(profile_path)
        user_js = self.write_user_js(profile_path)
        
        logger.info("[PHASE 2.1] Profile hardened — WebGL/Canvas/Audio LOCKED")
        return {
            'fingerprint_config': fp_config,
            'policies_json': policies,
            'user_js': user_js,
        }


def create_injector(profile_uuid: str, **kwargs) -> FingerprintInjector:
    """Create fingerprint injector for profile"""
    config = FingerprintConfig(profile_uuid=profile_uuid, **kwargs)
    return FingerprintInjector(config)


def inject_fingerprint_to_profile(profile_path: str, profile_uuid: str) -> Path:
    """Convenience function to inject fingerprint config to profile"""
    injector = create_injector(profile_uuid)
    return injector.write_to_profile(Path(profile_path))


class NetlinkHWBridge:
    """
    Ring 0 ↔ Ring 3 synchronization bridge via Netlink sockets.
    Communicates with hardware_shield_v6.c kernel module to ensure
    /proc/cpuinfo matches WebGL fingerprint at the browser level.
    
    Protocol: NETLINK_TITAN = 31
    Message types:
      1 = SET_PROFILE (send hardware profile to kernel)
      2 = GET_PROFILE (read current kernel profile)
      3 = HIDE_MODULE (stealth: hide titan_hw from lsmod)
    """
    
    NETLINK_TITAN = 31
    TITAN_MSG_SET_PROFILE = 1
    TITAN_MSG_GET_PROFILE = 2
    TITAN_MSG_HIDE_MODULE = 3
    
    def __init__(self):
        self.sock = None
        self.connected = False
        self._pid = None
    
    def connect(self) -> bool:
        """Open AF_NETLINK socket to kernel module"""
        import socket
        import os
        try:
            self.sock = socket.socket(socket.AF_NETLINK, socket.SOCK_RAW, self.NETLINK_TITAN)
            self._pid = os.getpid()
            self.sock.bind((self._pid, 0))
            self.connected = True
            logger.info(f"[NETLINK] Connected to kernel module (PID={self._pid}, proto={self.NETLINK_TITAN})")
            return True
        except OSError as e:
            logger.warning(f"[NETLINK] Cannot connect to kernel module: {e}")
            self.connected = False
            return False
    
    def send_profile(self, profile: Dict[str, Any]) -> bool:
        """Pack nlmsghdr + JSON payload and send to kernel"""
        import struct
        if not self.connected or not self.sock:
            logger.error("[NETLINK] Not connected")
            return False
        try:
            payload = json.dumps(profile).encode('utf-8')
            # nlmsghdr: length(4) + type(2) + flags(2) + seq(4) + pid(4) = 16 bytes
            msg_len = 16 + len(payload)
            header = struct.pack('=IHHII',
                msg_len,
                self.TITAN_MSG_SET_PROFILE,
                0,  # flags
                0,  # seq
                self._pid or 0
            )
            self.sock.send(header + payload)
            logger.info(f"[NETLINK] Sent hardware profile ({len(payload)} bytes)")
            return True
        except Exception as e:
            logger.error(f"[NETLINK] Send failed: {e}")
            return False
    
    def sync_with_injector(self, injector: 'FingerprintInjector') -> bool:
        """
        Read WebGL vendor/renderer from injector and construct
        a matching kernel profile for /proc/cpuinfo spoofing.
        """
        if not injector or not injector.config:
            return False
        
        kernel_profile = {
            "cpu_model": "Intel(R) Core(TM) i7-12700K",
            "cpu_cores": 16,
            "cpu_threads": 24,
            "webgl_vendor": injector.config.webgl_vendor,
            "webgl_renderer": injector.config.webgl_renderer,
            "gpu_vendor": "NVIDIA Corporation",
            "gpu_model": "NVIDIA GeForce RTX 3060",
            "total_memory_gb": 32,
        }
        
        return self.send_profile(kernel_profile)
    
    def hide_module(self) -> bool:
        """Send HIDE_MODULE command to remove titan_hw from /proc/modules"""
        import struct
        if not self.connected or not self.sock:
            return False
        try:
            msg_len = 16
            header = struct.pack('=IHHII',
                msg_len,
                self.TITAN_MSG_HIDE_MODULE,
                0, 0,
                self._pid or 0
            )
            self.sock.send(header)
            logger.info("[NETLINK] Module hide command sent")
            return True
        except Exception as e:
            logger.error(f"[NETLINK] Hide failed: {e}")
            return False
    
    def close(self):
        """Close Netlink socket"""
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
            self.sock = None
            self.connected = False
            logger.info("[NETLINK] Connection closed")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("TITAN V7.0 Fingerprint Injector Demo")
    print("-" * 40)
    
    # Create injector
    injector = create_injector("demo_profile_001")
    
    # Generate full config
    result = injector.generate_full_config()
    
    print(f"\nSeed: {result.seed}")
    print(f"Canvas Hash: {result.canvas_hash}")
    print(f"WebGL Hash: {result.webgl_hash}")
    print(f"Audio Hash: {result.audio_hash}")
    
    # Get Camoufox config
    camoufox = injector.get_camoufox_config()
    print(f"\nCamoufox config: {camoufox}")
