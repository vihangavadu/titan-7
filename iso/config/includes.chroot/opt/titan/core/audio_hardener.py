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
import secrets
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
        "context_sample_rate": 44100,
        "destination_channels": 2,
    },
    "windows_11_24h2": {
        "default_sample_rate": 48000,     # Win11 24H2 defaults to 48kHz
        "channel_count": 2,
        "channel_layout": "stereo",
        "base_latency": 0.01,
        "output_latency": 0.025,          # Slightly lower on 24H2
        "max_channel_count": 2,
        "state": "running",
        "noise_floor_db": -92,
        "timing_jitter_ms": 2.5,
        "oscillator_detune_range": 153600,
        "context_sample_rate": 48000,
        "destination_channels": 2,
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
        "context_sample_rate": 44100,
        "destination_channels": 2,
    },
    "macos_sequoia": {
        "default_sample_rate": 48000,     # macOS 15 Sequoia defaults to 48kHz
        "channel_count": 2,
        "channel_layout": "stereo",
        "base_latency": 0.004,
        "output_latency": 0.011,
        "max_channel_count": 2,
        "state": "running",
        "noise_floor_db": -98,
        "timing_jitter_ms": 1.5,
        "oscillator_detune_range": 153600,
        "context_sample_rate": 48000,
        "destination_channels": 2,
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
    
    # V7.5 FIX: Use correct Camoufox install path on Titan OS
    CAMOUFOX_PREFS_PATH = Path("/opt/camoufox/defaults/pref/local-settings.js")
    
    def __init__(self, target_os: AudioTargetOS = AudioTargetOS.WINDOWS, profile_uuid: Optional[str] = None):
        self.target_os = target_os
        self.os_profile = AUDIO_OS_PROFILES[target_os.value]
        self.profile_uuid = profile_uuid
        # V7.5 FIX: Generate random seed when no profile_uuid to avoid zero-noise
        self.jitter_seed = self._derive_jitter_seed(profile_uuid) if profile_uuid else secrets.randbits(64)
    
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
            # V7.5 FIX: Check for existing audio prefs to avoid duplicates
            existing = ""
            if user_js.exists():
                existing = user_js.read_text()
            if "Phase 3.2: Audio Stack Nullification" in existing:
                logger.debug("[PHASE 3.2] Audio prefs already present in user.js, skipping")
                return True
            
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
        
        # V7.5 FIX: Check for existing audio prefs to avoid duplicates
        existing = self.CAMOUFOX_PREFS_PATH.read_text()
        if "Phase 3.2: Audio Stack Nullification" in existing:
            logger.debug("[PHASE 3.2] Audio prefs already present in Camoufox prefs, skipping")
            return True
        
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


# ═══════════════════════════════════════════════════════════════════════════
# V7.6 P0 UPGRADE: SPEECH SYNTHESIS PROTECTION
# Prevent fingerprinting via Web Speech API
# ═══════════════════════════════════════════════════════════════════════════

class SpeechSynthesisProtection:
    """
    V7.6: Protects against Web Speech API fingerprinting.
    
    SpeechSynthesis can fingerprint via:
    - Available voices (varies by OS, locale, installed TTS)
    - Voice properties (voiceURI, name, lang, localService)
    - Voice ordering (unique per system)
    
    This engine provides consistent spoofed voice lists.
    """
    
    # Standardized voice sets by platform
    VOICE_SETS = {
        'windows': [
            {'voiceURI': 'Microsoft Zira - English (United States)', 'name': 'Microsoft Zira', 'lang': 'en-US', 'localService': True, 'default': True},
            {'voiceURI': 'Microsoft David - English (United States)', 'name': 'Microsoft David', 'lang': 'en-US', 'localService': True, 'default': False},
            {'voiceURI': 'Microsoft Mark - English (United States)', 'name': 'Microsoft Mark', 'lang': 'en-US', 'localService': True, 'default': False},
            {'voiceURI': 'Google US English', 'name': 'Google US English', 'lang': 'en-US', 'localService': False, 'default': False},
        ],
        'macos': [
            {'voiceURI': 'Samantha', 'name': 'Samantha', 'lang': 'en-US', 'localService': True, 'default': True},
            {'voiceURI': 'Alex', 'name': 'Alex', 'lang': 'en-US', 'localService': True, 'default': False},
            {'voiceURI': 'Victoria', 'name': 'Victoria', 'lang': 'en-US', 'localService': True, 'default': False},
            {'voiceURI': 'Google US English', 'name': 'Google US English', 'lang': 'en-US', 'localService': False, 'default': False},
        ],
        'linux': [
            {'voiceURI': 'espeak en-us', 'name': 'eSpeak English (US)', 'lang': 'en-US', 'localService': True, 'default': True},
            {'voiceURI': 'Google US English', 'name': 'Google US English', 'lang': 'en-US', 'localService': False, 'default': False},
        ],
    }
    
    def __init__(self, platform: str = 'windows'):
        self.platform = platform
        self.voices = self.VOICE_SETS.get(platform, self.VOICE_SETS['windows'])
    
    def generate_speech_shim(self) -> str:
        """Generate JavaScript to spoof speechSynthesis.getVoices()."""
        import json as _json
        voices_json = _json.dumps(self.voices)
        
        return f"""
(function() {{
    'use strict';
    const _titanVoices = {voices_json};
    
    // Create fake SpeechSynthesisVoice objects
    const _fakeVoices = _titanVoices.map(v => {{
        const voice = Object.create(SpeechSynthesisVoice.prototype);
        Object.defineProperties(voice, {{
            voiceURI: {{ value: v.voiceURI, enumerable: true }},
            name: {{ value: v.name, enumerable: true }},
            lang: {{ value: v.lang, enumerable: true }},
            localService: {{ value: v.localService, enumerable: true }},
            default: {{ value: v.default, enumerable: true }},
        }});
        return voice;
    }});
    
    // Override getVoices
    if (window.speechSynthesis) {{
        Object.defineProperty(window.speechSynthesis, 'getVoices', {{
            value: function() {{ return _fakeVoices; }},
            writable: false,
            configurable: false
        }});
        
        // Fire voiceschanged event once
        setTimeout(() => {{
            window.speechSynthesis.dispatchEvent(new Event('voiceschanged'));
        }}, 100);
    }}
}})();
"""
    
    def get_voice_list(self) -> list:
        """Get the spoofed voice list."""
        return self.voices.copy()


# ═══════════════════════════════════════════════════════════════════════════
# V7.6 P0 UPGRADE: MEDIA DEVICES SPOOFER
# Spoof navigator.mediaDevices.enumerateDevices() for audio
# ═══════════════════════════════════════════════════════════════════════════

class MediaDevicesSpoofer:
    """
    V7.6: Spoofs audio device enumeration.
    
    MediaDevices.enumerateDevices() reveals:
    - Number of audio inputs/outputs
    - Device labels (after permission granted)
    - Device IDs (persistent across sessions)
    
    This creates consistent fake device profile.
    """
    
    # Standard device configurations by platform
    DEVICE_CONFIGS = {
        'windows_desktop': {
            'audio_inputs': [
                {'label': 'Microphone (Realtek High Definition Audio)', 'deviceId': 'default'},
                {'label': 'Stereo Mix (Realtek High Definition Audio)', 'deviceId': 'communications'},
            ],
            'audio_outputs': [
                {'label': 'Speakers (Realtek High Definition Audio)', 'deviceId': 'default'},
                {'label': 'Digital Audio (S/PDIF) (Realtek High Definition Audio)', 'deviceId': 'spdif'},
            ],
        },
        'windows_laptop': {
            'audio_inputs': [
                {'label': 'Internal Microphone (Realtek(R) Audio)', 'deviceId': 'default'},
            ],
            'audio_outputs': [
                {'label': 'Speakers (Realtek(R) Audio)', 'deviceId': 'default'},
            ],
        },
        'macos': {
            'audio_inputs': [
                {'label': 'Built-in Microphone', 'deviceId': 'default'},
            ],
            'audio_outputs': [
                {'label': 'Built-in Speakers', 'deviceId': 'default'},
            ],
        },
    }
    
    def __init__(self, profile: str = 'windows_laptop', seed: str = None):
        import hashlib
        
        self.profile = profile
        self.config = self.DEVICE_CONFIGS.get(profile, self.DEVICE_CONFIGS['windows_laptop'])
        
        # Generate deterministic device IDs from seed
        self._seed = seed or 'titan_default'
        self._device_ids = self._generate_device_ids()
    
    def _generate_device_ids(self) -> dict:
        """Generate deterministic device IDs."""
        import hashlib
        ids = {}
        
        for i, device in enumerate(self.config['audio_inputs']):
            key = f"input_{i}"
            ids[key] = hashlib.sha256(f"{self._seed}_audioinput_{i}".encode()).hexdigest()[:64]
        
        for i, device in enumerate(self.config['audio_outputs']):
            key = f"output_{i}"
            ids[key] = hashlib.sha256(f"{self._seed}_audiooutput_{i}".encode()).hexdigest()[:64]
        
        return ids
    
    def generate_devices(self) -> list:
        """Generate complete device list."""
        devices = []
        
        # Audio inputs
        for i, device in enumerate(self.config['audio_inputs']):
            devices.append({
                'deviceId': self._device_ids[f'input_{i}'],
                'kind': 'audioinput',
                'label': device['label'],
                'groupId': self._device_ids[f'input_{i}'][:32],
            })
        
        # Audio outputs
        for i, device in enumerate(self.config['audio_outputs']):
            devices.append({
                'deviceId': self._device_ids[f'output_{i}'],
                'kind': 'audiooutput',
                'label': device['label'],
                'groupId': self._device_ids[f'output_{i}'][:32],
            })
        
        return devices
    
    def generate_media_devices_shim(self) -> str:
        """Generate JavaScript to spoof enumerateDevices()."""
        import json as _json
        devices = self.generate_devices()
        devices_json = _json.dumps(devices)
        
        return f"""
(function() {{
    'use strict';
    const _titanDevices = {devices_json};
    
    if (navigator.mediaDevices) {{
        const _origEnumerate = navigator.mediaDevices.enumerateDevices;
        
        navigator.mediaDevices.enumerateDevices = function() {{
            return Promise.resolve(_titanDevices.map(d => {{
                const device = Object.create(MediaDeviceInfo.prototype);
                Object.defineProperties(device, {{
                    deviceId: {{ value: d.deviceId, enumerable: true }},
                    kind: {{ value: d.kind, enumerable: true }},
                    label: {{ value: d.label, enumerable: true }},
                    groupId: {{ value: d.groupId, enumerable: true }},
                    toJSON: {{ value: function() {{ return d; }} }}
                }});
                return device;
            }}));
        }};
    }}
}})();
"""
    
    def get_device_summary(self) -> dict:
        """Get summary of spoofed devices."""
        return {
            'profile': self.profile,
            'audio_inputs': len(self.config['audio_inputs']),
            'audio_outputs': len(self.config['audio_outputs']),
            'devices': self.generate_devices(),
        }


# ═══════════════════════════════════════════════════════════════════════════
# V7.6 P0 UPGRADE: WEB AUDIO CONTEXT SHIM
# Intercept AudioContext for consistent fingerprint
# ═══════════════════════════════════════════════════════════════════════════

class WebAudioContextShim:
    """
    V7.6: Provides consistent AudioContext fingerprint.
    
    AudioContext fingerprinting targets:
    - Sample rate (varies by hardware)
    - Destination channel count
    - BaseLatency / outputLatency
    - createOscillator + analyser output
    
    This shim normalizes all these values.
    """
    
    # Standard audio parameters by platform
    AUDIO_PARAMS = {
        'windows': {
            'sampleRate': 48000,
            'channelCount': 2,
            'baseLatency': 0.005333333333333333,
            'outputLatency': 0.016,
            'maxChannelCount': 2,
        },
        'macos': {
            'sampleRate': 44100,
            'channelCount': 2,
            'baseLatency': 0.005804988662131519,
            'outputLatency': 0.013,
            'maxChannelCount': 2,
        },
        'linux': {
            'sampleRate': 48000,
            'channelCount': 2,
            'baseLatency': 0.01,
            'outputLatency': 0.02,
            'maxChannelCount': 2,
        },
    }
    
    def __init__(self, platform: str = 'windows', noise_seed: str = None):
        import hashlib
        
        self.platform = platform
        self.params = self.AUDIO_PARAMS.get(platform, self.AUDIO_PARAMS['windows'])
        
        # Generate deterministic noise seed
        self._noise_seed = noise_seed or 'titan_audio_default'
        self._noise_hash = int(hashlib.sha256(self._noise_seed.encode()).hexdigest()[:8], 16)
    
    def generate_audio_context_shim(self) -> str:
        """Generate JavaScript to shim AudioContext."""
        params = self.params
        noise_seed = self._noise_hash
        
        return f"""
(function() {{
    'use strict';
    const _titanAudioParams = {{
        sampleRate: {params['sampleRate']},
        channelCount: {params['channelCount']},
        baseLatency: {params['baseLatency']},
        outputLatency: {params['outputLatency']},
        maxChannelCount: {params['maxChannelCount']},
    }};
    const _noiseSeed = {noise_seed};
    
    // Seeded random for consistent noise
    function _titanSeededRandom(seed) {{
        seed = (seed * 9301 + 49297) % 233280;
        return seed / 233280;
    }}
    
    // Wrap AudioContext
    const _OrigAudioContext = window.AudioContext || window.webkitAudioContext;
    if (_OrigAudioContext) {{
        window.AudioContext = function(options) {{
            const ctx = new _OrigAudioContext(options);
            
            // Override sampleRate
            Object.defineProperty(ctx, 'sampleRate', {{
                value: _titanAudioParams.sampleRate,
                writable: false
            }});
            
            // Override baseLatency
            Object.defineProperty(ctx, 'baseLatency', {{
                value: _titanAudioParams.baseLatency,
                writable: false
            }});
            
            // Override outputLatency (if exists)
            if ('outputLatency' in ctx) {{
                Object.defineProperty(ctx, 'outputLatency', {{
                    value: _titanAudioParams.outputLatency,
                    writable: false
                }});
            }}
            
            // Override destination properties
            Object.defineProperty(ctx.destination, 'channelCount', {{
                value: _titanAudioParams.channelCount,
                writable: true
            }});
            Object.defineProperty(ctx.destination, 'maxChannelCount', {{
                value: _titanAudioParams.maxChannelCount,
                writable: false
            }});
            
            // Wrap getFloatFrequencyData for noise injection
            const _origCreateAnalyser = ctx.createAnalyser.bind(ctx);
            ctx.createAnalyser = function() {{
                const analyser = _origCreateAnalyser();
                const _origGetFloat = analyser.getFloatFrequencyData.bind(analyser);
                
                analyser.getFloatFrequencyData = function(array) {{
                    _origGetFloat(array);
                    // Add deterministic noise
                    let seed = _noiseSeed;
                    for (let i = 0; i < array.length; i++) {{
                        seed = (seed * 9301 + 49297) % 233280;
                        array[i] += (seed / 233280 - 0.5) * 0.0001;
                    }}
                }};
                
                return analyser;
            }};
            
            return ctx;
        }};
        window.webkitAudioContext = window.AudioContext;
    }}
}})();
"""
    
    def get_audio_params(self) -> dict:
        """Get the spoofed audio parameters."""
        return self.params.copy()


# ═══════════════════════════════════════════════════════════════════════════
# V7.6 UNIFIED AUDIO PROTECTION
# ═══════════════════════════════════════════════════════════════════════════

class UnifiedAudioProtection:
    """
    V7.6: Combines all audio protection mechanisms.
    """
    
    def __init__(self, platform: str = 'windows', profile_uuid: str = None):
        self.platform = platform
        self.profile_uuid = profile_uuid
        
        self.speech_protection = SpeechSynthesisProtection(platform)
        self.media_spoofer = MediaDevicesSpoofer(
            f'{platform}_laptop' if platform in ('windows', 'macos') else platform,
            seed=profile_uuid
        )
        self.audio_shim = WebAudioContextShim(platform, noise_seed=profile_uuid)
        self.hardener = AudioHardener(
            AudioTargetOS.WINDOWS if platform == 'windows' else AudioTargetOS.MACOS,
            profile_uuid=profile_uuid
        )
    
    def generate_combined_shim(self) -> str:
        """Generate all audio protection JavaScript."""
        return '\n\n'.join([
            "// TITAN V7.6 Unified Audio Protection",
            self.speech_protection.generate_speech_shim(),
            self.media_spoofer.generate_media_devices_shim(),
            self.audio_shim.generate_audio_context_shim(),
        ])
    
    def apply_to_profile(self, profile_path: str) -> dict:
        """Apply all audio protections to profile."""
        result = {
            'hardening': self.hardener.apply_to_profile(profile_path),
            'shim_generated': True,
        }
        
        # Write combined shim to profile
        from pathlib import Path
        shim_path = Path(profile_path) / 'audio_protection_shim.js'
        try:
            shim_path.write_text(self.generate_combined_shim())
            result['shim_path'] = str(shim_path)
        except Exception as e:
            result['shim_error'] = str(e)
        
        return result


# V7.6 Convenience exports
def create_speech_protection(platform: str = 'windows') -> SpeechSynthesisProtection:
    """V7.6: Create speech synthesis protection"""
    return SpeechSynthesisProtection(platform)

def create_media_spoofer(profile: str = 'windows_laptop', seed: str = None) -> MediaDevicesSpoofer:
    """V7.6: Create media devices spoofer"""
    return MediaDevicesSpoofer(profile, seed)

def create_audio_protection(platform: str = 'windows', profile_uuid: str = None) -> UnifiedAudioProtection:
    """V7.6: Create unified audio protection"""
    return UnifiedAudioProtection(platform, profile_uuid)
