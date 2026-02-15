"""
TITAN V7.0 SINGULARITY — Phase 3.2: Audio Stack Nullification
AudioContext Fingerprint Protection & PulseAudio Latency Masking

VULNERABILITY: Linux PulseAudio/PipeWire has a distinct latency curve
compared to Windows CoreAudio. The AudioContext API exposes:
1. Sample rate (PulseAudio defaults to 48000, Windows CoreAudio to 44100)
2. Channel count and layout
3. AudioBuffer timing jitter (PulseAudio ~5.3ms, CoreAudio ~2.9ms)
4. OscillatorNode frequency response (unique per audio stack)

Hardware Shield masks CPU/memory but does NOT hook ioctl calls for
the sound card. Browser-level mitigation is required.

FIX:
1. Write Camoufox prefs to force RFP (resistFingerprinting) for audio
2. Override AudioContext sample rate to match target OS
3. Inject noise into AudioBuffer to mask PulseAudio timing signature
4. Generate audio fingerprint config for Ghost Motor extension

Usage:
    from audio_hardener import AudioHardener, AudioTargetOS
    
    hardener = AudioHardener(AudioTargetOS.WINDOWS)
    hardener.apply_to_profile("/opt/titan/profiles/AM-8821")
"""

import json
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("TITAN-V7-AUDIO")


class AudioTargetOS(Enum):
    WINDOWS = "windows"
    MACOS = "macos"


# ═══════════════════════════════════════════════════════════════════════════
# AUDIO SIGNATURE DATABASE — Real OS audio stack characteristics
# ═══════════════════════════════════════════════════════════════════════════

AUDIO_OS_PROFILES = {
    "windows": {
        "default_sample_rate": 44100,     # CoreAudio default
        "channel_count": 2,
        "channel_layout": "stereo",
        "base_latency": 0.01,             # ~10ms
        "output_latency": 0.029,          # ~29ms (typical Windows)
        "max_channel_count": 2,
        "state": "running",
        "noise_floor_db": -90,
        "timing_jitter_ms": 2.9,          # CoreAudio timing jitter
        "oscillator_detune_range": 153600, # cents
    },
    "macos": {
        "default_sample_rate": 44100,
        "channel_count": 2,
        "channel_layout": "stereo",
        "base_latency": 0.005,            # ~5ms (CoreAudio lower)
        "output_latency": 0.013,          # ~13ms
        "max_channel_count": 2,
        "state": "running",
        "noise_floor_db": -96,
        "timing_jitter_ms": 1.8,
        "oscillator_detune_range": 153600,
    },
}

# Firefox prefs that control AudioContext behavior
AUDIO_FIREFOX_PREFS = {
    "core": {
        # RFP forces sample rate to 44100 and reduces timer precision
        "privacy.resistFingerprinting": True,
        # FPP with overrides — protect audio without breaking CSS
        "privacy.fingerprintingProtection": True,
        "privacy.fingerprintingProtection.overrides": "+AllTargets,-CSSPrefersColorScheme",
        # Disable audio channel promiscuous mode
        "dom.audiochannel.audioCompeting": False,
    },
    "hardening": {
        # Force consistent sample rate
        "media.default_audio_sample_rate": 44100,
        # Reduce timer precision to mask timing jitter
        "privacy.reduceTimerPrecision": True,
        "privacy.resistFingerprinting.reduceTimerPrecision.microseconds": 1000,
        "privacy.resistFingerprinting.reduceTimerPrecision.jitter": True,
        # Disable Web Audio API features that leak signatures
        "dom.webaudio.enabled": True,  # Must stay true or sites break
        "media.webaudio.AudioBuffer.speex_resampler.maxChannels": 2,
    },
    "noise_injection": {
        # Titan-specific prefs read by Ghost Motor for audio noise
        "titan.audio.noise_injection": True,
        "titan.audio.noise_amplitude": 0.0000001,
        "titan.audio.target_sample_rate": 44100,
        "titan.audio.target_latency": 0.01,
    },
}


@dataclass
class AudioHardeningResult:
    target_os: str
    prefs_written: int
    user_js_updated: bool
    camoufox_prefs_updated: bool
    audio_config_written: bool
    ghost_motor_config_written: bool


class AudioHardener:
    """
    Phase 3.2: AudioContext fingerprint nullification.
    
    Writes browser prefs and extension configs to mask the
    Linux PulseAudio/PipeWire audio stack signature.
    """
    
    CAMOUFOX_PREFS_PATH = Path("/opt/lucid-empire/camoufox/settings/defaults/pref/local-settings.js")
    
    def __init__(self, target_os: AudioTargetOS = AudioTargetOS.WINDOWS, profile_uuid: Optional[str] = None):
        self.target_os = target_os
        self.os_profile = AUDIO_OS_PROFILES[target_os.value]
        self.profile_uuid = profile_uuid
        self.jitter_seed = self._derive_jitter_seed(profile_uuid) if profile_uuid else 0
    
    @staticmethod
    def _derive_jitter_seed(profile_uuid: str) -> int:
        """Derive deterministic 8-byte jitter seed from profile UUID via SHA-256.
        Same profile UUID always produces same audio fingerprint."""
        h = hashlib.sha256(f"audio-jitter-{profile_uuid}".encode()).digest()
        return int.from_bytes(h[:8], 'big')
    
    def generate_user_js_prefs(self) -> List[str]:
        """Generate user.js lines for audio hardening"""
        lines = [
            "",
            "// ── TITAN Phase 3.2: Audio Stack Nullification ──────────────",
            f"// Target OS audio profile: {self.target_os.value}",
        ]
        
        all_prefs = {}
        all_prefs.update(AUDIO_FIREFOX_PREFS["core"])
        all_prefs.update(AUDIO_FIREFOX_PREFS["hardening"])
        all_prefs.update(AUDIO_FIREFOX_PREFS["noise_injection"])
        
        # Override target-specific values
        all_prefs["titan.audio.target_latency"] = self.os_profile["base_latency"]
        all_prefs["titan.audio.target_sample_rate"] = self.os_profile["default_sample_rate"]
        
        for key, value in all_prefs.items():
            if isinstance(value, bool):
                val_str = "true" if value else "false"
            elif isinstance(value, (int, float)):
                val_str = str(value)
            else:
                val_str = f'"{value}"'
            lines.append(f'user_pref("{key}", {val_str});')
        
        return lines
    
    def apply_to_user_js(self, profile_path: Path) -> bool:
        """Append audio hardening prefs to profile user.js"""
        user_js = Path(profile_path) / "user.js"
        lines = self.generate_user_js_prefs()
        
        try:
            with open(user_js, "a") as f:
                f.write("\n".join(lines) + "\n")
            logger.info(f"[PHASE 3.2] {len(lines)-3} audio prefs appended to user.js")
            return True
        except Exception as e:
            logger.error(f"[PHASE 3.2] user.js write error: {e}")
            return False
    
    def apply_to_camoufox_prefs(self) -> bool:
        """
        Write audio hardening to Camoufox default prefs.
        This affects ALL Camoufox sessions globally.
        """
        if not self.CAMOUFOX_PREFS_PATH.exists():
            logger.warning(f"[PHASE 3.2] Camoufox prefs not found at {self.CAMOUFOX_PREFS_PATH}")
            return False
        
        lines = [
            "",
            "// TITAN Phase 3.2: Audio Stack Nullification",
        ]
        
        for key, value in AUDIO_FIREFOX_PREFS["core"].items():
            if isinstance(value, bool):
                val_str = "true" if value else "false"
            elif isinstance(value, str):
                val_str = f'"{value}"'
            else:
                val_str = str(value)
            lines.append(f'pref("{key}", {val_str});')
        
        try:
            with open(self.CAMOUFOX_PREFS_PATH, "a") as f:
                f.write("\n".join(lines) + "\n")
            logger.info("[PHASE 3.2] Camoufox global prefs updated")
            return True
        except Exception as e:
            logger.error(f"[PHASE 3.2] Camoufox prefs write error: {e}")
            return False
    
    def generate_audio_config(self, profile_path: Path) -> bool:
        """Write audio fingerprint config for Ghost Motor extension"""
        config = {
            "audio_hardening": True,
            "target_os": self.target_os.value,
            "profile": self.os_profile,
            "noise_injection": {
                "enabled": True,
                "amplitude": 0.0000001,
                "method": "seeded_gaussian",
                "seed": self.jitter_seed,
                "apply_to": ["AudioBuffer", "AnalyserNode", "OscillatorNode"],
            },
            "timing_mask": {
                "enabled": True,
                "target_jitter_ms": self.os_profile["timing_jitter_ms"],
                "timer_precision_us": 1000,
                "jitter_seed": self.jitter_seed,
            },
        }
        
        try:
            out = Path(profile_path) / "audio_config.json"
            with open(out, 'w') as f:
                json.dump(config, f, indent=2)
            logger.info(f"[PHASE 3.2] Audio config written to {out}")
            return True
        except Exception as e:
            logger.error(f"[PHASE 3.2] Audio config write error: {e}")
            return False
    
    def apply_to_profile(self, profile_path: str) -> AudioHardeningResult:
        """Full Phase 3.2 application to a profile"""
        pp = Path(profile_path)
        
        user_js_ok = self.apply_to_user_js(pp)
        camoufox_ok = self.apply_to_camoufox_prefs()
        audio_cfg_ok = self.generate_audio_config(pp)
        
        prefs_count = (len(AUDIO_FIREFOX_PREFS["core"]) +
                      len(AUDIO_FIREFOX_PREFS["hardening"]) +
                      len(AUDIO_FIREFOX_PREFS["noise_injection"]))
        
        return AudioHardeningResult(
            target_os=self.target_os.value,
            prefs_written=prefs_count,
            user_js_updated=user_js_ok,
            camoufox_prefs_updated=camoufox_ok,
            audio_config_written=audio_cfg_ok,
            ghost_motor_config_written=audio_cfg_ok,
        )


def harden_audio(target_os: str = "windows", profile_path: Optional[str] = None, profile_uuid: Optional[str] = None) -> AudioHardeningResult:
    """Quick audio hardening with optional deterministic seed"""
    os_map = {"windows": AudioTargetOS.WINDOWS, "macos": AudioTargetOS.MACOS}
    hardener = AudioHardener(os_map.get(target_os, AudioTargetOS.WINDOWS), profile_uuid=profile_uuid)
    if profile_path:
        return hardener.apply_to_profile(profile_path)
    return AudioHardeningResult(target_os, 0, False, False, False, False)
