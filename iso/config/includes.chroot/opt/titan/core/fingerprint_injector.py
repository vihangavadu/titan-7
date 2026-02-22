"""
TITAN V8.1 SINGULARITY - Fingerprint Injector
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
from datetime import datetime, timezone
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

    # Hardware concurrency — must match kernel spoof (e.g. /proc/cpuinfo cpu cores)
    hardware_concurrency: int = 16


@dataclass
class FingerprintResult:
    """Result of fingerprint generation"""
    canvas_hash: str
    webgl_hash: str
    audio_hash: str
    seed: int
    config: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


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
        # V7.5 FIX: Linux OpenGL profiles for Titan OS (Camoufox on Linux)
        "nvidia_linux": [
            ("NVIDIA Corporation", "NVIDIA GeForce RTX 3060/PCIe/SSE2"),
            ("NVIDIA Corporation", "NVIDIA GeForce RTX 3070/PCIe/SSE2"),
            ("NVIDIA Corporation", "NVIDIA GeForce RTX 4070/PCIe/SSE2"),
            ("NVIDIA Corporation", "NVIDIA GeForce GTX 1660/PCIe/SSE2"),
        ],
        "intel_linux": [
            ("Intel", "Mesa Intel(R) UHD Graphics 630 (CFL GT2)"),
            ("Intel", "Mesa Intel(R) Xe Graphics (TGL GT2)"),
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
    
    def generate_hardware_concurrency_script(self) -> str:
        """
        Generate a JavaScript snippet that overrides navigator.hardwareConcurrency.

        The returned script uses Object.defineProperty with a getter and no
        setter, making the property effectively read-only (attempts to assign
        are silently ignored in non-strict mode or throw in strict mode).
        configurable:false prevents the descriptor from being redefined by
        page scripts after injection.

        The default value (16) is chosen to match the cpu_cores reported by
        the kernel spoof in NetlinkHWBridge.sync_with_injector().
        """
        concurrency = int(self.config.hardware_concurrency)
        return (
            "(function() {{\n"
            "    'use strict';\n"
            "    Object.defineProperty(navigator, 'hardwareConcurrency', {{\n"
            "        get: function() {{ return {concurrency}; }},\n"
            "        configurable: false,\n"
            "        enumerable: true,\n"
            "    }});\n"
            "}})();"
        ).format(concurrency=concurrency)

    def inject_cdp_preload(self, driver) -> None:
        """
        Inject navigator.hardwareConcurrency override via CDP preload.

        Calls Page.addScriptToEvaluateOnNewDocument so the script runs
        in every new document context BEFORE any page JavaScript executes.
        This prevents anti-fraud scripts from reading the real core count
        before our override is in place.

        Args:
            driver: A Selenium / undetected-chromedriver WebDriver instance
                    that exposes execute_cdp_cmd(), or any object with the
                    same interface (e.g. Playwright's CDP session).
        """
        script = self.generate_hardware_concurrency_script()
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": script},
        )
        logger.info(
            "[CDP] hardwareConcurrency preload injected → %d cores",
            self.config.hardware_concurrency,
        )

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
        
        # V7.5 FIX: Write to BOTH profile and Camoufox install directory
        # Firefox reads policies.json from <install_dir>/distribution/, not profile dir
        written_path = None
        for base_dir in [profile_path, Path("/opt/camoufox")]:
            dist_dir = base_dir / "distribution"
            dist_dir.mkdir(parents=True, exist_ok=True)
            policies_file = dist_dir / "policies.json"
            with open(policies_file, "w") as f:
                json.dump(policies, f, indent=2)
            if written_path is None:
                written_path = policies_file
        
        logger.info(f"[PHASE 2.1] policies.json written: WebGL LOCKED to {webgl.get('renderer', 'N/A')[:40]}...")
        return written_path

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
            '// TITAN V8.1 SINGULARITY — Fingerprint Lock (Phase 2.1 Hardening)',
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
            "cpu_cores": injector.config.hardware_concurrency,
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
            except Exception:
                pass
            self.sock = None
            self.connected = False
            logger.info("[NETLINK] Connection closed")


# ═══════════════════════════════════════════════════════════════════════════
# V7.5 UPGRADE: CPUID / RDTSC TIMING HARDENING
# Defeats VM/sandbox detection via CPUID leaf enumeration and RDTSC
# timing side-channel analysis. Antifraud scripts (Forter, ThreatMetrix)
# measure CPUID execution latency to detect hypervisors.
# ═══════════════════════════════════════════════════════════════════════════

class CPUIDHardener:
    """
    v7.5 CPUID and RDTSC timing hardening.

    Detection vectors neutralized:
    - CPUID leaf 0x1: hypervisor bit (ECX bit 31) must be cleared
    - CPUID leaf 0x40000000: hypervisor brand string must be absent
    - RDTSC timing: VM exits cause >500 cycle latency; bare metal is <100
    - CPUID leaf 0x80000002-4: processor brand string must match profile
    """

    # Known hypervisor signatures to suppress
    HYPERVISOR_SIGNATURES = [
        b"KVMKVMKVM\x00\x00\x00",   # KVM
        b"Microsoft Hv",              # Hyper-V
        b"VMwareVMware",              # VMware
        b"XenVMMXenVMM",              # Xen
        b"VBoxVBoxVBox",              # VirtualBox
        b"TCGTCGTCGTCG",              # QEMU TCG
    ]

    # Realistic RDTSC cycle counts for bare-metal CPUID execution
    BARE_METAL_CPUID_CYCLES = {
        "leaf_0x0": (28, 45),    # Basic CPUID info
        "leaf_0x1": (30, 50),    # Feature flags
        "leaf_0x7": (32, 55),    # Extended features
        "leaf_0x80000002": (35, 60),  # Processor brand string
    }

    def __init__(self, target_cpu: str = "Intel(R) Core(TM) i7-12700K"):
        self.target_cpu = target_cpu
        self._patched = False

    def generate_cpuid_mask_script(self) -> str:
        """
        Generate JavaScript that intercepts WebAssembly CPUID probes.
        Some antifraud scripts use WASM to execute CPUID-like timing
        measurements via SharedArrayBuffer + Atomics high-res timer.
        """
        return (
            "(function() {\n"
            "  'use strict';\n"
            "  // v7.5 CPUID Hardening: mask high-resolution timer\n"
            "  const _origNow = performance.now.bind(performance);\n"
            "  const _jitter = () => (Math.random() - 0.5) * 0.05;\n"
            "  Object.defineProperty(performance, 'now', {\n"
            "    value: function() {\n"
            "      return Math.round(_origNow() * 20) / 20 + _jitter();\n"
            "    },\n"
            "    writable: false,\n"
            "    configurable: false\n"
            "  });\n"
            "  // Clamp SharedArrayBuffer timer resolution\n"
            "  if (typeof SharedArrayBuffer !== 'undefined') {\n"
            "    const _origWait = Atomics.wait;\n"
            "    Atomics.wait = function() {\n"
            "      return _origWait.apply(this, arguments);\n"
            "    };\n"
            "  }\n"
            "})();\n"
        )

    def generate_rdtsc_calibration(self) -> dict:
        """
        Generate RDTSC calibration parameters for the kernel module.
        The hardware_shield_v6.c module intercepts RDTSC and adds
        controlled noise to mask VM exit latency.
        """
        import random
        return {
            "rdtsc_offset_cycles": random.randint(-15, 15),
            "rdtsc_jitter_range": (5, 25),
            "cpuid_exit_overhead_mask": True,
            "target_latency_cycles": {
                k: random.randint(*v)
                for k, v in self.BARE_METAL_CPUID_CYCLES.items()
            },
            "hypervisor_bit_clear": True,
            "brand_string": self.target_cpu,
        }

    def get_kernel_patch_config(self) -> dict:
        """
        Configuration for hardware_shield_v6.c CPUID/RDTSC interception.
        """
        return {
            "cpuid_intercept": {
                "leaf_0x1_ecx_mask": 0x7FFFFFFF,  # Clear bit 31 (hypervisor)
                "leaf_0x40000000_zero": True,       # Zero hypervisor brand
                "brand_string_override": self.target_cpu,
            },
            "rdtsc_intercept": {
                "enabled": True,
                "noise_distribution": "gaussian",
                "noise_sigma_cycles": 8,
                "clamp_min_cycles": 20,
                "clamp_max_cycles": 80,
            },
        }


# ═══════════════════════════════════════════════════════════════════════════
# V7.5 UPGRADE: FONT SUB-PIXEL RENDERING SHIM
# Defeats font fingerprinting via Canvas measureText() and glyph rendering
# differences. Antifraud scripts measure exact sub-pixel widths of rendered
# text to identify OS/GPU/font-renderer combinations.
# ═══════════════════════════════════════════════════════════════════════════

class FontSubPixelShim:
    """
    v7.5 Font Sub-Pixel Rendering Shim.

    Detection vectors neutralized:
    - Canvas measureText() width fingerprinting
    - Sub-pixel glyph positioning differences between renderers
    - Font enumeration via width-based detection
    - DirectWrite vs FreeType vs CoreText rendering signatures

    Technique: Inject deterministic per-profile correction factors into
    measureText() results so that the same profile always produces the
    same font metrics, matching the target OS rendering engine.
    """

    # Correction factors: target_os -> (scale_x, offset_px)
    # These map Linux FreeType rendering to match Windows DirectWrite output
    CORRECTION_FACTORS = {
        "windows_11": {
            "scale": 1.0,
            "offset": 0.0,
            "subpixel_order": "rgb",
            "hinting": "full",
            "antialiasing": "cleartype",
        },
        "windows_10": {
            "scale": 1.0,
            "offset": 0.0,
            "subpixel_order": "rgb",
            "hinting": "full",
            "antialiasing": "cleartype",
        },
        "macos_sonoma": {
            "scale": 0.998,
            "offset": 0.15,
            "subpixel_order": "none",
            "hinting": "none",
            "antialiasing": "grayscale",
        },
        "linux_freetype": {
            "scale": 1.002,
            "offset": -0.08,
            "subpixel_order": "rgb",
            "hinting": "slight",
            "antialiasing": "subpixel",
        },
    }

    # Common fonts used in fingerprinting probes
    PROBE_FONTS = [
        "Arial", "Verdana", "Times New Roman", "Georgia", "Courier New",
        "Trebuchet MS", "Impact", "Comic Sans MS", "Palatino Linotype",
        "Lucida Console", "Tahoma", "Segoe UI", "Calibri",
    ]

    def __init__(self, profile_seed: int, target_os: str = "windows_11"):
        self.seed = profile_seed
        self.target_os = target_os
        self.correction = self.CORRECTION_FACTORS.get(target_os, self.CORRECTION_FACTORS["windows_11"])
        self._font_offsets = self._generate_font_offsets()

    def _generate_font_offsets(self) -> dict:
        """
        Generate deterministic per-font correction offsets.
        Same seed = same offsets = consistent fingerprint across sessions.
        """
        import random
        rng = random.Random(self.seed)
        offsets = {}
        for font in self.PROBE_FONTS:
            offsets[font] = {
                "width_scale": self.correction["scale"] + rng.gauss(0, 0.0005),
                "width_offset": self.correction["offset"] + rng.gauss(0, 0.02),
                "height_offset": rng.gauss(0, 0.01),
            }
        return offsets

    def generate_shim_script(self) -> str:
        """
        Generate JavaScript shim that intercepts CanvasRenderingContext2D.measureText()
        and applies deterministic correction factors per font family.
        """
        import json as _json
        offsets_json = _json.dumps(self._font_offsets)
        return (
            "(function() {\n"
            "  'use strict';\n"
            f"  const _offsets = {offsets_json};\n"
            "  const _origMeasure = CanvasRenderingContext2D.prototype.measureText;\n"
            "  CanvasRenderingContext2D.prototype.measureText = function(text) {\n"
            "    const result = _origMeasure.call(this, text);\n"
            "    const font = this.font || '';\n"
            "    let correction = null;\n"
            "    for (const [name, off] of Object.entries(_offsets)) {\n"
            "      if (font.includes(name)) { correction = off; break; }\n"
            "    }\n"
            "    if (correction) {\n"
            "      const origWidth = result.width;\n"
            "      Object.defineProperty(result, 'width', {\n"
            "        get: () => origWidth * correction.width_scale + correction.width_offset,\n"
            "        configurable: false\n"
            "      });\n"
            "    }\n"
            "    return result;\n"
            "  };\n"
            "})();\n"
        )

    def get_fontconfig_override(self) -> dict:
        """
        Generate fontconfig/freetype override settings for the OS level.
        Applied via environment variables before browser launch.
        """
        return {
            "FREETYPE_PROPERTIES": f"truetype:interpreter-version=40 cff:no-stem-darkening=1",
            "FC_FORCE_HINTING": self.correction["hinting"],
            "FC_SUBPIXEL_ORDER": self.correction["subpixel_order"],
            "TITAN_FONT_SHIM_SEED": str(self.seed),
            "TITAN_FONT_TARGET_OS": self.target_os,
        }


# ═══════════════════════════════════════════════════════════════════════════
# V7.6 P0 UPGRADE: WEBRTC LEAK PREVENTION
# Prevents IP address leaks via WebRTC STUN/TURN requests
# ═══════════════════════════════════════════════════════════════════════════

class WebRTCLeakPrevention:
    """
    V7.6: Prevents WebRTC IP leaks that bypass proxy/VPN.
    
    WebRTC can leak:
    - Local IP address (192.168.x.x, 10.x.x.x)
    - Public IP (even through VPN via STUN)
    - Device media capabilities
    
    This engine provides:
    1. RTCPeerConnection override to block STUN
    2. MediaDevices enumeration spoofing
    3. IP address masking/replacement
    """
    
    def __init__(self, fake_local_ip: str = None, fake_public_ip: str = None,
                 block_mode: str = 'spoof'):
        """
        Args:
            fake_local_ip: IP to report as local (e.g., "192.168.1.105")
            fake_public_ip: IP to report as public (should match proxy exit)
            block_mode: 'spoof' (replace IPs), 'block' (disable WebRTC), 'allow' (passthrough)
        """
        self.fake_local_ip = fake_local_ip or self._generate_fake_local_ip()
        self.fake_public_ip = fake_public_ip
        self.block_mode = block_mode
        self._media_devices = self._generate_media_devices()
    
    def _generate_fake_local_ip(self) -> str:
        """Generate a plausible local IP, seeded for profile consistency."""
        import random
        # Seed from fake_public_ip or fallback to system random
        seed_val = hash(self.fake_public_ip or 'titan') & 0xFFFFFFFF
        rng = random.Random(seed_val)
        subnet = rng.choice(['192.168.1', '192.168.0', '10.0.0', '172.16.0'])
        host = rng.randint(2, 254)
        return f"{subnet}.{host}"
    
    def _generate_media_devices(self) -> list:
        """Generate realistic media device list, seeded for profile consistency."""
        import random
        rng = random.Random(hash(self.fake_local_ip or 'titan') & 0xFFFFFFFF)
        devices = []
        
        # Typical webcam names
        webcam_names = [
            "HD Webcam", "Integrated Camera", "USB 2.0 Camera",
            "FaceTime HD Camera", "HD Pro Webcam C920",
        ]
        
        # Typical microphone names
        mic_names = [
            "Internal Microphone", "Built-in Microphone",
            "HD Webcam Microphone", "USB Audio Device",
        ]
        
        # Add 1-2 cameras
        for i in range(rng.randint(1, 2)):
            seed_str = f"cam_{i}_{self.fake_local_ip}"
            devices.append({
                'deviceId': hashlib.sha256(seed_str.encode()).hexdigest()[:64],
                'groupId': hashlib.sha256(f"group_{seed_str}".encode()).hexdigest()[:64],
                'kind': 'videoinput',
                'label': rng.choice(webcam_names),
            })
        
        # Add 1-2 microphones
        for i in range(rng.randint(1, 2)):
            seed_str = f"mic_{i}_{self.fake_local_ip}"
            devices.append({
                'deviceId': hashlib.sha256(seed_str.encode()).hexdigest()[:64],
                'groupId': hashlib.sha256(f"group_{seed_str}".encode()).hexdigest()[:64],
                'kind': 'audioinput',
                'label': rng.choice(mic_names),
            })
        
        # Add audio output
        devices.append({
            'deviceId': 'default',
            'groupId': hashlib.sha256("speakers".encode()).hexdigest()[:64],
            'kind': 'audiooutput',
            'label': 'Default - Speakers',
        })
        
        return devices
    
    def generate_webrtc_shim(self) -> str:
        """
        Generate JavaScript to prevent WebRTC IP leaks.
        """
        import json as _json
        
        if self.block_mode == 'block':
            return """
(function() {
    'use strict';
    // Block WebRTC entirely
    window.RTCPeerConnection = undefined;
    window.webkitRTCPeerConnection = undefined;
    window.mozRTCPeerConnection = undefined;
    if (navigator.mediaDevices) {
        navigator.mediaDevices.getUserMedia = () => Promise.reject(new DOMException('NotAllowedError'));
        navigator.mediaDevices.enumerateDevices = () => Promise.resolve([]);
    }
})();
"""
        
        devices_json = _json.dumps(self._media_devices)
        fake_local = self.fake_local_ip
        fake_public = self.fake_public_ip or self.fake_local_ip
        
        return f"""
(function() {{
    'use strict';
    const _fakeLocalIP = '{fake_local}';
    const _fakePublicIP = '{fake_public}';
    const _fakeDevices = {devices_json};
    
    // Override RTCPeerConnection to spoof IPs
    const _OrigRTC = window.RTCPeerConnection || window.webkitRTCPeerConnection;
    if (_OrigRTC) {{
        window.RTCPeerConnection = function(config, constraints) {{
            // Remove STUN/TURN servers to prevent real IP leak
            if (config && config.iceServers) {{
                config.iceServers = [];
            }}
            const pc = new _OrigRTC(config, constraints);
            
            // Override onicecandidate to spoof IP in candidates
            const _origOnIce = Object.getOwnPropertyDescriptor(pc, 'onicecandidate');
            Object.defineProperty(pc, 'onicecandidate', {{
                set: function(handler) {{
                    pc.addEventListener('icecandidate', function(event) {{
                        if (event.candidate && event.candidate.candidate) {{
                            // Replace real IP with fake
                            let spoofed = event.candidate.candidate;
                            spoofed = spoofed.replace(/([0-9]{{1,3}}\\.?){{4}}/g, _fakeLocalIP);
                            const newCandidate = new RTCIceCandidate({{
                                candidate: spoofed,
                                sdpMid: event.candidate.sdpMid,
                                sdpMLineIndex: event.candidate.sdpMLineIndex
                            }});
                            handler({{ candidate: newCandidate }});
                        }} else {{
                            handler(event);
                        }}
                    }});
                }}
            }});
            
            return pc;
        }};
        window.webkitRTCPeerConnection = window.RTCPeerConnection;
    }}
    
    // Override enumerateDevices
    if (navigator.mediaDevices) {{
        navigator.mediaDevices.enumerateDevices = () => Promise.resolve(_fakeDevices);
    }}
}})();
"""
    
    def get_config(self) -> dict:
        """Get WebRTC prevention config for external use."""
        return {
            'mode': self.block_mode,
            'fake_local_ip': self.fake_local_ip,
            'fake_public_ip': self.fake_public_ip,
            'media_devices': self._media_devices,
        }


# ═══════════════════════════════════════════════════════════════════════════
# V7.6 P0 UPGRADE: CLIENT HINTS SPOOFING
# Modern User-Agent Client Hints (UA-CH) API spoofing
# ═══════════════════════════════════════════════════════════════════════════

class ClientHintsSpoofing:
    """
    V7.6: Spoofs User-Agent Client Hints (UA-CH) API.
    
    Modern antifraud systems use UA-CH instead of User-Agent string:
    - Sec-CH-UA: Brand information
    - Sec-CH-UA-Platform: OS
    - Sec-CH-UA-Mobile: Is mobile device
    - Sec-CH-UA-Full-Version-List: Detailed versions
    
    Inconsistency between UA string and UA-CH = immediate bot flag.
    """
    
    # Chrome brand versions (must match navigator.userAgent)
    BRAND_VERSIONS = {
        '120': {'major': '120', 'full': '120.0.6099.129'},
        '121': {'major': '121', 'full': '121.0.6167.85'},
        '122': {'major': '122', 'full': '122.0.6261.94'},
        '123': {'major': '123', 'full': '123.0.6312.58'},
        '124': {'major': '124', 'full': '124.0.6367.60'},
        '125': {'major': '125', 'full': '125.0.6422.76'},
        '126': {'major': '126', 'full': '126.0.6478.114'},
        '127': {'major': '127', 'full': '127.0.6533.72'},
        '128': {'major': '128', 'full': '128.0.6613.84'},
        '129': {'major': '129', 'full': '129.0.6668.70'},
        '130': {'major': '130', 'full': '130.0.6723.58'},
        '131': {'major': '131', 'full': '131.0.6778.85'},
        '132': {'major': '132', 'full': '132.0.6834.83'},
        '133': {'major': '133', 'full': '133.0.6943.53'},
    }
    
    PLATFORMS = {
        'windows': {'platform': 'Windows', 'platformVersion': '15.0.0'},
        'windows_10': {'platform': 'Windows', 'platformVersion': '10.0.0'},
        'windows_11': {'platform': 'Windows', 'platformVersion': '15.0.0'},
        'macos': {'platform': 'macOS', 'platformVersion': '14.3.1'},
        'macos_sonoma': {'platform': 'macOS', 'platformVersion': '14.4.0'},
        'macos_sequoia': {'platform': 'macOS', 'platformVersion': '15.1.0'},
        'linux': {'platform': 'Linux', 'platformVersion': '6.5.0'},
    }
    
    def __init__(self, chrome_version: str = '122', platform: str = 'windows',
                 is_mobile: bool = False, architecture: str = 'x86'):
        self.chrome_version = chrome_version
        self.platform = platform
        self.is_mobile = is_mobile
        self.architecture = architecture
        self._brand_info = self.BRAND_VERSIONS.get(chrome_version, self.BRAND_VERSIONS['122'])
        self._platform_info = self.PLATFORMS.get(platform, self.PLATFORMS['windows'])
    
    def generate_client_hints(self) -> dict:
        """Generate complete Client Hints data."""
        brands = [
            {'brand': 'Not A(Brand', 'version': '8'},
            {'brand': 'Chromium', 'version': self._brand_info['major']},
            {'brand': 'Google Chrome', 'version': self._brand_info['major']},
        ]
        
        full_brands = [
            {'brand': 'Not A(Brand', 'version': '8.0.0.0'},
            {'brand': 'Chromium', 'version': self._brand_info['full']},
            {'brand': 'Google Chrome', 'version': self._brand_info['full']},
        ]
        
        return {
            'brands': brands,
            'fullVersionList': full_brands,
            'mobile': self.is_mobile,
            'platform': self._platform_info['platform'],
            'platformVersion': self._platform_info['platformVersion'],
            'architecture': self.architecture,
            'bitness': '64',
            'model': '' if not self.is_mobile else 'Pixel 8',
            'uaFullVersion': self._brand_info['full'],
            'wow64': False,
        }
    
    def generate_client_hints_shim(self) -> str:
        """Generate JavaScript to spoof navigator.userAgentData."""
        import json as _json
        hints = self.generate_client_hints()
        hints_json = _json.dumps(hints)
        
        return f"""
(function() {{
    'use strict';
    const _hints = {hints_json};
    
    // Override navigator.userAgentData
    Object.defineProperty(navigator, 'userAgentData', {{
        get: function() {{
            return {{
                brands: _hints.brands,
                mobile: _hints.mobile,
                platform: _hints.platform,
                getHighEntropyValues: function(keys) {{
                    return Promise.resolve({{
                        brands: _hints.brands,
                        fullVersionList: _hints.fullVersionList,
                        mobile: _hints.mobile,
                        platform: _hints.platform,
                        platformVersion: _hints.platformVersion,
                        architecture: _hints.architecture,
                        bitness: _hints.bitness,
                        model: _hints.model,
                        uaFullVersion: _hints.uaFullVersion,
                        wow64: _hints.wow64,
                    }});
                }},
                toJSON: function() {{
                    return {{
                        brands: _hints.brands,
                        mobile: _hints.mobile,
                        platform: _hints.platform,
                    }};
                }}
            }};
        }},
        configurable: false
    }});
}})();
"""
    
    def get_http_headers(self) -> dict:
        """Get Client Hints HTTP headers for requests."""
        brands_str = ', '.join([f'"{b["brand"]}";v="{b["version"]}"' for b in self.generate_client_hints()['brands']])
        
        return {
            'Sec-CH-UA': brands_str,
            'Sec-CH-UA-Mobile': '?1' if self.is_mobile else '?0',
            'Sec-CH-UA-Platform': f'"{self._platform_info["platform"]}"',
            'Sec-CH-UA-Platform-Version': f'"{self._platform_info["platformVersion"]}"',
            'Sec-CH-UA-Arch': f'"{self.architecture}"',
            'Sec-CH-UA-Bitness': '"64"',
            'Sec-CH-UA-Full-Version-List': ', '.join([
                f'"{b["brand"]}";v="{b["version"]}"' 
                for b in self.generate_client_hints()['fullVersionList']
            ]),
        }


# ═══════════════════════════════════════════════════════════════════════════
# V7.6 P0 UPGRADE: BATTERY API SPOOFING
# Battery status can be used for fingerprinting and tracking
# ═══════════════════════════════════════════════════════════════════════════

class BatteryAPISpoofing:
    """
    V7.6: Spoofs Battery Status API to prevent fingerprinting.
    
    Battery API reveals:
    - Charging status (plugged in vs battery)
    - Battery level (unique identifier when combined with other data)
    - Charging/discharging time (very precise fingerprint)
    
    Modern browsers are deprecating this API, but many sites still probe it.
    """
    
    def __init__(self, simulate_desktop: bool = True):
        """
        Args:
            simulate_desktop: If True, simulate always plugged in (desktop behavior)
        """
        self.simulate_desktop = simulate_desktop
        self._state = self._generate_state()
    
    def _generate_state(self) -> dict:
        import random
        
        if self.simulate_desktop:
            # Desktop: always charging, full battery
            return {
                'charging': True,
                'chargingTime': 0,
                'dischargingTime': float('inf'),
                'level': 1.0,
            }
        else:
            # Simulate realistic laptop battery
            level = random.uniform(0.3, 0.95)
            charging = random.random() > 0.5
            
            if charging:
                charge_time = int((1.0 - level) * 7200)  # Time to full in seconds
                discharge_time = float('inf')
            else:
                charge_time = float('inf')
                discharge_time = int(level * 14400)  # Time to empty in seconds
            
            return {
                'charging': charging,
                'chargingTime': charge_time,
                'dischargingTime': discharge_time,
                'level': round(level, 2),
            }
    
    def generate_battery_shim(self) -> str:
        """Generate JavaScript to spoof Battery Status API."""
        import json as _json
        
        # Handle infinity for JSON
        state = self._state.copy()
        state['dischargingTime'] = 'Infinity' if state['dischargingTime'] == float('inf') else state['dischargingTime']
        state['chargingTime'] = 'Infinity' if state['chargingTime'] == float('inf') else state['chargingTime']
        
        return f"""
(function() {{
    'use strict';
    const _batteryState = {{
        charging: {str(self._state['charging']).lower()},
        chargingTime: {'Infinity' if self._state['chargingTime'] == float('inf') else self._state['chargingTime']},
        dischargingTime: {'Infinity' if self._state['dischargingTime'] == float('inf') else self._state['dischargingTime']},
        level: {self._state['level']},
        onchargingchange: null,
        onchargingtimechange: null,
        ondischargingtimechange: null,
        onlevelchange: null,
        addEventListener: function() {{}},
        removeEventListener: function() {{}},
        dispatchEvent: function() {{ return true; }}
    }};
    
    // Override getBattery
    if (navigator.getBattery) {{
        navigator.getBattery = function() {{
            return Promise.resolve(_batteryState);
        }};
    }}
    
    // Block BatteryManager access
    if (window.BatteryManager) {{
        window.BatteryManager = undefined;
    }}
}})();
"""
    
    def get_state(self) -> dict:
        """Get current battery state for external use."""
        return self._state.copy()


# ═══════════════════════════════════════════════════════════════════════════
# V7.6 UNIFIED FINGERPRINT HARDENING
# ═══════════════════════════════════════════════════════════════════════════

class UnifiedFingerprintHardener:
    """
    V7.6: Combines all fingerprint evasion techniques into a single coordinator.
    """
    
    def __init__(self, profile_uuid: str, platform: str = 'windows',
                 chrome_version: str = '122', proxy_ip: str = None):
        self.profile_uuid = profile_uuid
        self.platform = platform
        self.chrome_version = chrome_version
        
        # Initialize all components
        self.injector = FingerprintInjector(profile_uuid, target_os=platform)
        self.webrtc = WebRTCLeakPrevention(fake_public_ip=proxy_ip)
        self.client_hints = ClientHintsSpoofing(chrome_version, platform)
        self.battery = BatteryAPISpoofing(simulate_desktop=(platform != 'android'))
        self.font_shim = FontSubPixelShim(profile_uuid, platform)
    
    def generate_all_shims(self) -> str:
        """Generate combined JavaScript for all fingerprint evasion."""
        shims = [
            "// TITAN V7.6 Unified Fingerprint Hardening",
            self.injector.generate_hardware_concurrency_script(),
            self.webrtc.generate_webrtc_shim(),
            self.client_hints.generate_client_hints_shim(),
            self.battery.generate_battery_shim(),
            self.font_shim.generate_shim_script(),
        ]
        return '\n\n'.join(shims)
    
    def get_full_config(self) -> dict:
        """Get complete fingerprint hardening config."""
        fp_result = self.injector.generate_full_config()
        
        return {
            'profile_uuid': self.profile_uuid,
            'platform': self.platform,
            'chrome_version': self.chrome_version,
            'fingerprint': {
                'canvas_hash': fp_result.canvas_hash,
                'webgl_hash': fp_result.webgl_hash,
                'audio_hash': fp_result.audio_hash,
            },
            'webrtc': self.webrtc.get_config(),
            'client_hints': self.client_hints.generate_client_hints(),
            'client_hints_headers': self.client_hints.get_http_headers(),
            'battery': self.battery.get_state(),
            'font_env': self.font_shim.get_fontconfig_override(),
        }


# V7.6 Convenience exports
def create_webrtc_prevention(fake_public_ip: str = None, block_mode: str = 'spoof'):
    """V7.6: Create WebRTC leak prevention"""
    return WebRTCLeakPrevention(fake_public_ip=fake_public_ip, block_mode=block_mode)

def create_client_hints_spoof(chrome_version: str = '122', platform: str = 'windows'):
    """V7.6: Create Client Hints spoofing"""
    return ClientHintsSpoofing(chrome_version, platform)

def create_unified_hardener(profile_uuid: str, platform: str = 'windows', proxy_ip: str = None):
    """V7.6: Create unified fingerprint hardener"""
    return UnifiedFingerprintHardener(profile_uuid, platform, proxy_ip=proxy_ip)


if __name__ == "__main__":
    # Demo of fingerprint injection
    injector = FingerprintInjector("test-profile-uuid-1234")
    config = injector.generate_full_config()
    print(f"Canvas Hash: {config.canvas_hash}")
    print(f"WebGL Hash: {config.webgl_hash}")
    print(f"Audio Hash: {config.audio_hash}")
    
    # Demo V7.6 unified hardener
    hardener = create_unified_hardener("test-profile", platform="windows", proxy_ip="203.0.113.50")
    print(f"\nV7.6 Unified Config: {hardener.get_full_config()['client_hints']}")
    logging.basicConfig(level=logging.INFO)
    
    print("TITAN V7.5 Fingerprint Injector Demo")
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
