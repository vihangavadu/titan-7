"""
TITAN V7.5 SINGULARITY — KYC Voice Engine
Text-to-Speech synthesis for video+voice KYC challenges.

Handles the "Record a video saying X" KYC challenge type where the
operator must speak a phrase on camera. This module generates realistic
speech audio that is mixed with the reenacted face video and piped to
the virtual camera + virtual microphone.

Supported TTS backends (in priority order):
1. Coqui TTS (XTTS-v2) — best quality, voice cloning capable
2. Piper TTS — fast, lightweight, good quality
3. espeak-ng + ffmpeg — fallback, robotic but functional
4. gTTS (Google TTS) — online fallback, requires internet

Architecture:
  Text prompt → TTS Engine → WAV audio
  Face photo  → LivePortrait → Video frames
  WAV + Video → FFmpeg mux → v4l2loopback (video) + PulseAudio (audio)
"""

import os
import subprocess
import tempfile
import shutil
import logging
import json
import time
import threading
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any, Tuple, Callable
from enum import Enum

logger = logging.getLogger("TITAN-V7-KYC-VOICE")


class TTSBackend(Enum):
    """Available TTS backends"""
    COQUI_XTTS = "coqui_xtts"       # Best quality, voice cloning
    PIPER = "piper"                   # Fast, good quality
    ESPEAK = "espeak"                 # Fallback, robotic
    GTTS = "gtts"                     # Online Google TTS


class VoiceGender(Enum):
    MALE = "male"
    FEMALE = "female"


@dataclass
class VoiceProfile:
    """Voice configuration for TTS"""
    gender: VoiceGender = VoiceGender.MALE
    language: str = "en"
    accent: str = "us"               # us, gb, au, in, ca, ie, za, nz
    speed: float = 1.0               # 0.5-2.0
    pitch: float = 1.0               # 0.5-2.0
    age_range: str = "adult"         # young, adult, senior
    # For voice cloning (Coqui XTTS)
    reference_audio: Optional[str] = None  # Path to reference voice sample
    # Piper voice model name
    piper_model: str = "en_US-lessac-medium"


@dataclass
class SpeechVideoConfig:
    """Configuration for generating speech+video KYC response"""
    text: str                         # What to say
    face_image: str                   # Source face photo
    voice: VoiceProfile = field(default_factory=VoiceProfile)
    output_resolution: Tuple[int, int] = (1280, 720)
    output_fps: int = 30
    camera_device: str = "/dev/video2"
    # Lip sync
    enable_lip_sync: bool = True      # Sync mouth movement to audio
    # Audio output
    audio_device: str = "default"     # PulseAudio sink
    # Realism
    add_noise: bool = True
    noise_level: float = 0.02
    add_breathing_pauses: bool = True  # Natural pauses between sentences


class KYCVoiceEngine:
    """
    Voice synthesis engine for KYC video+speech challenges.
    
    Handles the full pipeline:
    1. Generate speech audio from text (TTS)
    2. Generate lip-synced face video (LivePortrait + audio-driven motion)
    3. Mix audio + video
    4. Stream to virtual camera + virtual microphone
    
    Usage:
        engine = KYCVoiceEngine()
        engine.speak_to_camera(
            text="My name is John Davis and today is February twentieth",
            face_image="/path/to/face.jpg",
            camera_device="/dev/video2"
        )
    """
    
    MODELS_PATH = Path("/opt/titan/models")
    PIPER_PATH = Path("/opt/titan/bin/piper")
    TEMP_PATH = Path("/tmp/titan_kyc_voice")
    MOTION_ASSETS = Path("/opt/titan/assets/motions")
    
    def __init__(self):
        self._backend: Optional[TTSBackend] = None
        self._ffmpeg_proc: Optional[subprocess.Popen] = None
        self._audio_proc: Optional[subprocess.Popen] = None
        self._stop_event = threading.Event()
        
        self.on_log: Optional[Callable[[str, str], None]] = None
        self.on_progress: Optional[Callable[[str, float], None]] = None
        
        self.TEMP_PATH.mkdir(parents=True, exist_ok=True)
        self._detect_backend()
    
    def _log(self, msg: str, level: str = "info"):
        logger.info(msg) if level == "info" else logger.warning(msg)
        if self.on_log:
            self.on_log(msg, level)
    
    def _detect_backend(self):
        """Detect best available TTS backend"""
        # 1. Check Coqui TTS (XTTS)
        try:
            import TTS
            self._backend = TTSBackend.COQUI_XTTS
            self._log("TTS backend: Coqui XTTS (best quality, voice cloning)")
            return
        except ImportError:
            pass
        
        # 2. Check Piper
        if self.PIPER_PATH.exists() or shutil.which("piper"):
            self._backend = TTSBackend.PIPER
            self._log("TTS backend: Piper (fast, good quality)")
            return
        
        # 3. Check espeak-ng
        if shutil.which("espeak-ng") or shutil.which("espeak"):
            self._backend = TTSBackend.ESPEAK
            self._log("TTS backend: espeak-ng (fallback)")
            return
        
        # 4. Check gTTS (requires internet)
        try:
            import gtts
            self._backend = TTSBackend.GTTS
            self._log("TTS backend: Google TTS (online)")
            return
        except ImportError:
            pass
        
        self._log("No TTS backend available! Install piper or espeak-ng", "error")
    
    @property
    def is_available(self) -> bool:
        return self._backend is not None
    
    @property
    def backend_name(self) -> str:
        return self._backend.value if self._backend else "none"
    
    # ═══════════════════════════════════════════════════════════════════
    # TEXT-TO-SPEECH GENERATION
    # ═══════════════════════════════════════════════════════════════════
    
    def generate_speech(self, text: str, voice: VoiceProfile,
                        output_path: Optional[str] = None) -> Optional[str]:
        """
        Generate speech audio from text.
        Returns path to WAV file.
        """
        if not self.is_available:
            self._log("No TTS backend available", "error")
            return None
        
        if not output_path:
            output_path = str(self.TEMP_PATH / "speech.wav")
        
        self._log(f"Generating speech: '{text[:60]}...' via {self.backend_name}")
        
        if self._backend == TTSBackend.COQUI_XTTS:
            return self._generate_coqui(text, voice, output_path)
        elif self._backend == TTSBackend.PIPER:
            return self._generate_piper(text, voice, output_path)
        elif self._backend == TTSBackend.ESPEAK:
            return self._generate_espeak(text, voice, output_path)
        elif self._backend == TTSBackend.GTTS:
            return self._generate_gtts(text, voice, output_path)
        
        return None
    
    def _generate_coqui(self, text: str, voice: VoiceProfile,
                         output_path: str) -> Optional[str]:
        """Generate speech using Coqui TTS (XTTS-v2)"""
        try:
            from TTS.api import TTS as CoquiTTS
            
            model_name = "tts_models/multilingual/multi-dataset/xtts_v2"
            tts = CoquiTTS(model_name)
            
            if voice.reference_audio and os.path.exists(voice.reference_audio):
                # Voice cloning mode
                tts.tts_to_file(
                    text=text,
                    speaker_wav=voice.reference_audio,
                    language=voice.language,
                    file_path=output_path
                )
            else:
                tts.tts_to_file(
                    text=text,
                    language=voice.language,
                    file_path=output_path
                )
            
            self._log(f"Coqui TTS generated: {output_path}")
            return output_path
        except Exception as e:
            self._log(f"Coqui TTS failed: {e}", "error")
            return self._generate_espeak(text, voice, output_path)
    
    def _generate_piper(self, text: str, voice: VoiceProfile,
                         output_path: str) -> Optional[str]:
        """Generate speech using Piper TTS"""
        try:
            piper_bin = str(self.PIPER_PATH) if self.PIPER_PATH.exists() else "piper"
            model = voice.piper_model
            
            # Check if model exists locally
            model_path = self.MODELS_PATH / "piper" / f"{model}.onnx"
            if model_path.exists():
                model_arg = str(model_path)
            else:
                model_arg = model
            
            cmd = f'echo "{text}" | {piper_bin} --model {model_arg} --output_file {output_path}'
            
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=30
            )
            
            if os.path.exists(output_path) and os.path.getsize(output_path) > 100:
                # Apply speed/pitch adjustments
                if voice.speed != 1.0 or voice.pitch != 1.0:
                    self._adjust_audio(output_path, voice.speed, voice.pitch)
                self._log(f"Piper TTS generated: {output_path}")
                return output_path
            else:
                self._log(f"Piper output empty, falling back to espeak", "warn")
                return self._generate_espeak(text, voice, output_path)
                
        except Exception as e:
            self._log(f"Piper TTS failed: {e}, falling back to espeak", "warn")
            return self._generate_espeak(text, voice, output_path)
    
    def _generate_espeak(self, text: str, voice: VoiceProfile,
                          output_path: str) -> Optional[str]:
        """Generate speech using espeak-ng (always available fallback)"""
        try:
            espeak = "espeak-ng" if shutil.which("espeak-ng") else "espeak"
            
            # Build voice string
            voice_str = f"{voice.language}"
            if voice.gender == VoiceGender.FEMALE:
                voice_str += "+f3"
            else:
                voice_str += "+m3"
            
            speed = int(150 * voice.speed)  # Default 150 wpm
            pitch = int(50 * voice.pitch)   # Default 50
            
            cmd = [
                espeak, "-v", voice_str,
                "-s", str(speed),
                "-p", str(pitch),
                "-w", output_path,
                text
            ]
            
            subprocess.run(cmd, capture_output=True, timeout=15)
            
            if os.path.exists(output_path) and os.path.getsize(output_path) > 100:
                self._log(f"espeak TTS generated: {output_path}")
                return output_path
            
            self._log("espeak output empty", "error")
            return None
            
        except Exception as e:
            self._log(f"espeak failed: {e}", "error")
            return None
    
    def _generate_gtts(self, text: str, voice: VoiceProfile,
                        output_path: str) -> Optional[str]:
        """Generate speech using Google TTS (requires internet)"""
        try:
            from gtts import gTTS
            
            tld_map = {"us": "com", "gb": "co.uk", "au": "com.au", "in": "co.in"}
            tld = tld_map.get(voice.accent, "com")
            
            mp3_path = output_path.replace(".wav", ".mp3")
            tts = gTTS(text=text, lang=voice.language, tld=tld, slow=False)
            tts.save(mp3_path)
            
            # Convert MP3 to WAV
            subprocess.run([
                "ffmpeg", "-y", "-i", mp3_path,
                "-ar", "22050", "-ac", "1",
                output_path
            ], capture_output=True, timeout=15)
            
            os.remove(mp3_path)
            
            if os.path.exists(output_path):
                self._log(f"Google TTS generated: {output_path}")
                return output_path
            
            return None
        except Exception as e:
            self._log(f"Google TTS failed: {e}", "error")
            return self._generate_espeak(text, voice, output_path)
    
    def _adjust_audio(self, audio_path: str, speed: float, pitch: float):
        """Adjust audio speed and pitch using ffmpeg"""
        temp = audio_path + ".tmp.wav"
        atempo = max(0.5, min(2.0, speed))
        
        # Pitch shift via asetrate + aresample
        sample_rate = int(22050 * pitch)
        
        cmd = [
            "ffmpeg", "-y", "-i", audio_path,
            "-filter:a", f"atempo={atempo},asetrate={sample_rate},aresample=22050",
            temp
        ]
        subprocess.run(cmd, capture_output=True, timeout=15)
        
        if os.path.exists(temp):
            os.replace(temp, audio_path)
    
    # ═══════════════════════════════════════════════════════════════════
    # SPEECH + VIDEO PIPELINE
    # ═══════════════════════════════════════════════════════════════════
    
    def speak_to_camera(self, config: SpeechVideoConfig) -> bool:
        """
        Full pipeline: generate speech, create lip-synced video, stream to camera.
        
        This handles the "Record a video saying X" KYC challenge.
        
        Pipeline:
        1. Generate speech WAV from text
        2. Get audio duration
        3. Generate talking-head video (LivePortrait with speech motion)
        4. Mux audio + video
        5. Stream to virtual camera + play audio to virtual mic
        """
        if not self.is_available:
            self._log("No TTS backend available", "error")
            return False
        
        if not os.path.exists(config.face_image):
            self._log(f"Face image not found: {config.face_image}", "error")
            return False
        
        self._stop_event.clear()
        
        # Step 1: Generate speech audio
        if self.on_progress:
            self.on_progress("Generating speech...", 0.1)
        
        audio_path = str(self.TEMP_PATH / "speech.wav")
        audio_result = self.generate_speech(config.text, config.voice, audio_path)
        if not audio_result:
            self._log("Speech generation failed", "error")
            return False
        
        # Step 2: Get audio duration
        duration = self._get_audio_duration(audio_path)
        if duration <= 0:
            duration = len(config.text.split()) * 0.4  # Estimate ~0.4s per word
        
        self._log(f"Speech duration: {duration:.1f}s")
        
        if self.on_progress:
            self.on_progress("Creating talking video...", 0.3)
        
        # Step 3: Generate talking-head video
        video_path = str(self.TEMP_PATH / "talking.mp4")
        video_ok = self._generate_talking_video(
            config.face_image, audio_path, video_path, config, duration
        )
        
        if not video_ok:
            self._log("Talking video generation failed, using static face + audio", "warn")
            video_path = None
        
        if self.on_progress:
            self.on_progress("Streaming to camera...", 0.7)
        
        # Step 4: Stream to virtual camera + play audio
        return self._stream_speech_video(
            video_path, audio_path, config
        )
    
    def _generate_talking_video(self, face_image: str, audio_path: str,
                                  output_path: str, config: SpeechVideoConfig,
                                  duration: float) -> bool:
        """
        Generate a talking-head video using LivePortrait audio-driven mode
        or fallback to face + mouth motion overlay.
        """
        model_path = self.MODELS_PATH / "liveportrait"
        w, h = config.output_resolution
        
        # Try LivePortrait audio-driven reenactment
        if model_path.exists():
            try:
                # Use the smile motion as a talking base (mouth movement)
                talk_motion = self.MOTION_ASSETS / "smile.mp4"
                if not talk_motion.exists():
                    talk_motion = self.MOTION_ASSETS / "neutral.mp4"
                
                cmd = [
                    "python3", "-m", "liveportrait.inference",
                    "--source", face_image,
                    "--driving", str(talk_motion),
                    "--output", output_path,
                    "--head_rotation", str(config.head_rotation_intensity if hasattr(config, 'head_rotation_intensity') else 0.3),
                    "--expression", "1.2",  # Slightly exaggerated for speech
                    "--fps", str(config.output_fps),
                ]
                
                result = subprocess.run(
                    cmd, cwd=str(model_path),
                    capture_output=True, text=True, timeout=60
                )
                
                if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                    # Trim/loop video to match audio duration
                    self._match_video_duration(output_path, duration, config.output_fps)
                    self._log("LivePortrait talking video generated")
                    return True
                    
            except Exception as e:
                self._log(f"LivePortrait talking video failed: {e}", "warn")
        
        # Fallback: static face with subtle motion via ffmpeg
        try:
            cmd = [
                "ffmpeg", "-y",
                "-loop", "1",
                "-i", face_image,
                "-t", str(duration + 0.5),
                "-vf", (
                    f"scale={w}:{h},"
                    "noise=alls=3:allf=t,"
                    "curves=lighter"
                ),
                "-r", str(config.output_fps),
                "-pix_fmt", "yuv420p",
                output_path
            ]
            subprocess.run(cmd, capture_output=True, timeout=30)
            
            if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                self._log("Fallback talking video generated (static + noise)")
                return True
        except Exception as e:
            self._log(f"Fallback video failed: {e}", "error")
        
        return False
    
    def _stream_speech_video(self, video_path: Optional[str],
                               audio_path: str,
                               config: SpeechVideoConfig) -> bool:
        """
        Stream video to virtual camera and audio to virtual microphone simultaneously.
        """
        w, h = config.output_resolution
        
        try:
            # Build video source
            if video_path and os.path.exists(video_path):
                video_input = ["-i", video_path]
                video_filter = f"scale={w}:{h}"
            else:
                # Static face image as video
                video_input = ["-loop", "1", "-i", config.face_image]
                video_filter = f"scale={w}:{h},noise=alls=3:allf=t"
            
            if config.add_noise:
                video_filter += f",noise=alls={int(config.noise_level * 100)}:allf=t"
            
            # Stream video to v4l2loopback
            video_cmd = [
                "ffmpeg", "-y", "-re",
                *video_input,
                "-vf", video_filter,
                "-f", "v4l2",
                "-pix_fmt", "yuyv422",
                "-r", str(config.output_fps),
                config.camera_device
            ]
            
            self._ffmpeg_proc = subprocess.Popen(
                video_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # Play audio through PulseAudio (virtual mic or speakers)
            # Use paplay for PulseAudio or aplay for ALSA
            audio_player = "paplay" if shutil.which("paplay") else "aplay"
            audio_cmd = [audio_player, audio_path]
            
            # Small delay to sync video start with audio
            time.sleep(0.3)
            
            self._audio_proc = subprocess.Popen(
                audio_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            self._log("Speech+video streaming to camera")
            
            if self.on_progress:
                self.on_progress("Speaking...", 0.9)
            
            # Wait for audio to finish
            self._audio_proc.wait(timeout=60)
            
            # Stop video after audio ends (+ small buffer)
            time.sleep(0.5)
            self.stop()
            
            if self.on_progress:
                self.on_progress("Complete", 1.0)
            
            self._log("Speech+video complete")
            return True
            
        except Exception as e:
            self._log(f"Stream failed: {e}", "error")
            self.stop()
            return False
    
    def stop(self):
        """Stop all streaming"""
        self._stop_event.set()
        
        for proc in (self._ffmpeg_proc, self._audio_proc):
            if proc:
                proc.terminate()
                try:
                    proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    proc.kill()
        
        self._ffmpeg_proc = None
        self._audio_proc = None
    
    # ═══════════════════════════════════════════════════════════════════
    # HELPERS
    # ═══════════════════════════════════════════════════════════════════
    
    def _get_audio_duration(self, audio_path: str) -> float:
        """Get audio duration in seconds"""
        try:
            result = subprocess.run([
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                audio_path
            ], capture_output=True, text=True, timeout=5)
            return float(result.stdout.strip())
        except Exception:
            return 0
    
    def _match_video_duration(self, video_path: str, target_duration: float,
                                fps: int):
        """Trim or loop video to match target duration"""
        current = self._get_video_duration(video_path)
        if abs(current - target_duration) < 0.5:
            return  # Close enough
        
        temp = video_path + ".tmp.mp4"
        if current < target_duration:
            # Loop video
            loops = int(target_duration / max(current, 0.1)) + 1
            cmd = [
                "ffmpeg", "-y",
                "-stream_loop", str(loops),
                "-i", video_path,
                "-t", str(target_duration),
                "-c", "copy",
                temp
            ]
        else:
            # Trim video
            cmd = [
                "ffmpeg", "-y",
                "-i", video_path,
                "-t", str(target_duration),
                "-c", "copy",
                temp
            ]
        
        subprocess.run(cmd, capture_output=True, timeout=30)
        if os.path.exists(temp):
            os.replace(temp, video_path)
    
    def _get_video_duration(self, video_path: str) -> float:
        return self._get_audio_duration(video_path)  # Same ffprobe method
    
    def get_status(self) -> Dict[str, Any]:
        """Get engine status for GUI display"""
        return {
            "available": self.is_available,
            "backend": self.backend_name,
            "backends_checked": {
                "coqui_xtts": self._check_coqui(),
                "piper": self.PIPER_PATH.exists() or bool(shutil.which("piper")),
                "espeak": bool(shutil.which("espeak-ng") or shutil.which("espeak")),
                "gtts": self._check_gtts(),
            }
        }
    
    def _check_coqui(self) -> bool:
        try:
            import TTS
            return True
        except ImportError:
            return False
    
    def _check_gtts(self) -> bool:
        try:
            import gtts
            return True
        except ImportError:
            return False
    
    @staticmethod
    def get_available_voices() -> List[Dict[str, str]]:
        """Get list of available voice presets for GUI dropdown"""
        return [
            {"id": "us_male", "name": "US Male", "gender": "male", "accent": "us"},
            {"id": "us_female", "name": "US Female", "gender": "female", "accent": "us"},
            {"id": "gb_male", "name": "British Male", "gender": "male", "accent": "gb"},
            {"id": "gb_female", "name": "British Female", "gender": "female", "accent": "gb"},
            {"id": "au_male", "name": "Australian Male", "gender": "male", "accent": "au"},
        ]


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 VOICE CLONE ENGINE — Clone voices from reference audio samples
# ═══════════════════════════════════════════════════════════════════════════════

import hashlib
from collections import defaultdict


@dataclass
class VoiceClone:
    """A cloned voice profile."""
    clone_id: str
    name: str
    reference_audio: str
    duration_seconds: float
    quality_score: float
    language: str
    gender: VoiceGender
    created_at: float
    sample_count: int


class VoiceCloneEngine:
    """
    V7.6 Voice Clone Engine - Clones voices from reference audio
    samples for highly realistic TTS.
    """
    
    CLONES_DIR = Path("/opt/titan/data/voice_clones")
    MIN_SAMPLE_DURATION = 5.0  # Minimum 5 seconds of reference audio
    
    def __init__(self):
        self._clones: Dict[str, VoiceClone] = {}
        self._load_clones()
    
    def _load_clones(self):
        """Load saved voice clones."""
        if not self.CLONES_DIR.exists():
            return
        
        index_file = self.CLONES_DIR / "clones.json"
        if index_file.exists():
            try:
                data = json.loads(index_file.read_text())
                for clone_data in data.get("clones", []):
                    clone = VoiceClone(
                        clone_id=clone_data["clone_id"],
                        name=clone_data["name"],
                        reference_audio=clone_data["reference_audio"],
                        duration_seconds=clone_data["duration_seconds"],
                        quality_score=clone_data["quality_score"],
                        language=clone_data["language"],
                        gender=VoiceGender(clone_data["gender"]),
                        created_at=clone_data["created_at"],
                        sample_count=clone_data.get("sample_count", 1)
                    )
                    self._clones[clone.clone_id] = clone
            except Exception as e:
                logger.warning(f"Could not load voice clones: {e}")
    
    def _save_clones(self):
        """Save voice clones index."""
        self.CLONES_DIR.mkdir(parents=True, exist_ok=True)
        index_file = self.CLONES_DIR / "clones.json"
        
        data = {
            "clones": [
                {
                    "clone_id": c.clone_id,
                    "name": c.name,
                    "reference_audio": c.reference_audio,
                    "duration_seconds": c.duration_seconds,
                    "quality_score": c.quality_score,
                    "language": c.language,
                    "gender": c.gender.value,
                    "created_at": c.created_at,
                    "sample_count": c.sample_count
                }
                for c in self._clones.values()
            ]
        }
        index_file.write_text(json.dumps(data, indent=2))
    
    def _get_audio_duration(self, audio_path: str) -> float:
        """Get audio duration in seconds."""
        try:
            result = subprocess.run([
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                audio_path
            ], capture_output=True, text=True, timeout=5)
            return float(result.stdout.strip())
        except Exception:
            return 0
    
    def create_clone(self, name: str, reference_audio: str,
                    language: str = "en",
                    gender: VoiceGender = VoiceGender.MALE) -> Optional[VoiceClone]:
        """
        Create a voice clone from reference audio.
        
        Args:
            name: Human-readable name for the clone
            reference_audio: Path to reference audio file
            language: Language code
            gender: Voice gender
        
        Returns:
            Created VoiceClone or None on failure
        """
        if not os.path.exists(reference_audio):
            logger.error(f"Reference audio not found: {reference_audio}")
            return None
        
        duration = self._get_audio_duration(reference_audio)
        if duration < self.MIN_SAMPLE_DURATION:
            logger.warning(f"Reference audio too short ({duration}s), need at least {self.MIN_SAMPLE_DURATION}s")
        
        # Generate clone ID
        clone_id = hashlib.md5(
            f"{name}{reference_audio}{time.time()}".encode()
        ).hexdigest()[:12]
        
        # Copy reference audio to clones directory
        self.CLONES_DIR.mkdir(parents=True, exist_ok=True)
        dest_audio = self.CLONES_DIR / f"{clone_id}.wav"
        
        # Convert to WAV 22050 Hz mono
        try:
            subprocess.run([
                "ffmpeg", "-y", "-i", reference_audio,
                "-ar", "22050", "-ac", "1",
                str(dest_audio)
            ], capture_output=True, timeout=30)
        except Exception as e:
            logger.error(f"Could not process reference audio: {e}")
            return None
        
        # Analyze audio quality
        quality_score = self._analyze_quality(str(dest_audio))
        
        clone = VoiceClone(
            clone_id=clone_id,
            name=name,
            reference_audio=str(dest_audio),
            duration_seconds=duration,
            quality_score=quality_score,
            language=language,
            gender=gender,
            created_at=time.time(),
            sample_count=1
        )
        
        self._clones[clone_id] = clone
        self._save_clones()
        
        logger.info(f"Voice clone created: {name} (quality: {quality_score:.2f})")
        return clone
    
    def _analyze_quality(self, audio_path: str) -> float:
        """Analyze audio quality for voice cloning."""
        # Basic quality score based on duration and file size
        duration = self._get_audio_duration(audio_path)
        file_size = os.path.getsize(audio_path) if os.path.exists(audio_path) else 0
        
        # Score factors
        duration_score = min(duration / 30.0, 1.0)  # Max at 30 seconds
        size_score = min(file_size / (100 * 1024), 1.0)  # Expect ~100KB for 10s
        
        return (duration_score * 0.6 + size_score * 0.4)
    
    def add_sample(self, clone_id: str, additional_audio: str) -> bool:
        """Add additional sample to improve clone quality."""
        clone = self._clones.get(clone_id)
        if not clone:
            return False
        
        # Merge additional audio with existing reference
        # For simplicity, just concatenate
        merged_path = self.CLONES_DIR / f"{clone_id}_merged.wav"
        
        try:
            subprocess.run([
                "ffmpeg", "-y",
                "-i", clone.reference_audio,
                "-i", additional_audio,
                "-filter_complex", "[0:a][1:a]concat=n=2:v=0:a=1",
                str(merged_path)
            ], capture_output=True, timeout=30)
            
            if merged_path.exists():
                os.replace(str(merged_path), clone.reference_audio)
                clone.sample_count += 1
                clone.duration_seconds = self._get_audio_duration(clone.reference_audio)
                clone.quality_score = self._analyze_quality(clone.reference_audio)
                self._save_clones()
                return True
        except Exception as e:
            logger.warning(f"Could not add sample: {e}")
        
        return False
    
    def get_clone(self, clone_id: str) -> Optional[VoiceClone]:
        """Get a voice clone by ID."""
        return self._clones.get(clone_id)
    
    def list_clones(self) -> List[Dict]:
        """List all voice clones."""
        return [
            {
                "id": c.clone_id,
                "name": c.name,
                "duration": c.duration_seconds,
                "quality": round(c.quality_score, 2),
                "language": c.language,
                "gender": c.gender.value,
                "samples": c.sample_count
            }
            for c in self._clones.values()
        ]
    
    def delete_clone(self, clone_id: str) -> bool:
        """Delete a voice clone."""
        clone = self._clones.pop(clone_id, None)
        if clone:
            try:
                if os.path.exists(clone.reference_audio):
                    os.remove(clone.reference_audio)
            except Exception:
                pass
            self._save_clones()
            return True
        return False
    
    def get_voice_profile(self, clone_id: str) -> Optional[VoiceProfile]:
        """Get VoiceProfile for a clone to use with KYCVoiceEngine."""
        clone = self._clones.get(clone_id)
        if not clone:
            return None
        
        return VoiceProfile(
            gender=clone.gender,
            language=clone.language,
            reference_audio=clone.reference_audio
        )


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 SPEECH QUALITY ANALYZER — Analyze speech quality and naturalness
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class QualityMetrics:
    """Speech quality metrics."""
    overall_score: float
    clarity_score: float
    naturalness_score: float
    pacing_score: float
    volume_score: float
    issues: List[str]


class SpeechQualityAnalyzer:
    """
    V7.6 Speech Quality Analyzer - Analyzes generated speech
    for quality and naturalness.
    """
    
    # Target metrics for natural speech
    TARGET_METRICS = {
        "duration_per_word": (0.3, 0.6),  # seconds
        "silence_ratio": (0.1, 0.3),       # pause time ratio
        "volume_variance": (0.1, 0.4),     # volume consistency
        "sample_rate": 22050,
    }
    
    def __init__(self):
        self._analysis_cache: Dict[str, QualityMetrics] = {}
    
    def analyze(self, audio_path: str, text: str) -> QualityMetrics:
        """
        Analyze speech quality.
        
        Args:
            audio_path: Path to speech audio file
            text: Original text that was spoken
        
        Returns:
            QualityMetrics with scores and issues
        """
        issues = []
        scores = {}
        
        # Get audio info
        duration = self._get_duration(audio_path)
        word_count = len(text.split())
        
        # Analyze pacing
        if word_count > 0:
            pace = duration / word_count
            min_pace, max_pace = self.TARGET_METRICS["duration_per_word"]
            
            if pace < min_pace:
                issues.append("Speech too fast")
                scores["pacing"] = max(0, 1 - (min_pace - pace) * 2)
            elif pace > max_pace:
                issues.append("Speech too slow")
                scores["pacing"] = max(0, 1 - (pace - max_pace) * 2)
            else:
                scores["pacing"] = 1.0
        else:
            scores["pacing"] = 0.5
        
        # Analyze volume (using ffmpeg loudnorm stats)
        volume_info = self._analyze_volume(audio_path)
        if volume_info:
            input_i = volume_info.get("input_i", -20)
            if input_i < -30:
                issues.append("Volume too low")
                scores["volume"] = 0.5
            elif input_i > -10:
                issues.append("Volume too high")
                scores["volume"] = 0.7
            else:
                scores["volume"] = 1.0
        else:
            scores["volume"] = 0.7
        
        # Clarity score (based on no obvious issues)
        clarity_issues = [i for i in issues if "Volume" not in i]
        scores["clarity"] = 1.0 - len(clarity_issues) * 0.2
        
        # Naturalness (harder to measure without ML)
        scores["naturalness"] = min(
            scores.get("pacing", 0.5),
            scores.get("volume", 0.5)
        )
        
        # Overall score
        overall = (
            scores.get("clarity", 0.5) * 0.3 +
            scores.get("naturalness", 0.5) * 0.3 +
            scores.get("pacing", 0.5) * 0.25 +
            scores.get("volume", 0.5) * 0.15
        )
        
        metrics = QualityMetrics(
            overall_score=round(overall, 2),
            clarity_score=round(scores.get("clarity", 0.5), 2),
            naturalness_score=round(scores.get("naturalness", 0.5), 2),
            pacing_score=round(scores.get("pacing", 0.5), 2),
            volume_score=round(scores.get("volume", 0.5), 2),
            issues=issues
        )
        
        self._analysis_cache[audio_path] = metrics
        return metrics
    
    def _get_duration(self, audio_path: str) -> float:
        """Get audio duration."""
        try:
            result = subprocess.run([
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                audio_path
            ], capture_output=True, text=True, timeout=5)
            return float(result.stdout.strip())
        except Exception:
            return 0
    
    def _analyze_volume(self, audio_path: str) -> Optional[Dict]:
        """Analyze volume using ffmpeg loudnorm."""
        try:
            result = subprocess.run([
                "ffmpeg", "-i", audio_path,
                "-af", "loudnorm=I=-16:print_format=json",
                "-f", "null", "-"
            ], capture_output=True, text=True, timeout=10)
            
            # Parse loudnorm output
            output = result.stderr
            json_match = output[output.rfind("{"):output.rfind("}") + 1]
            if json_match:
                return json.loads(json_match)
        except Exception:
            pass
        return None
    
    def suggest_improvements(self, metrics: QualityMetrics) -> List[str]:
        """Suggest improvements based on quality analysis."""
        suggestions = []
        
        if metrics.pacing_score < 0.7:
            if "too fast" in str(metrics.issues):
                suggestions.append("Decrease speech speed to 0.85x")
            else:
                suggestions.append("Increase speech speed to 1.15x")
        
        if metrics.volume_score < 0.7:
            suggestions.append("Normalize audio volume")
        
        if metrics.naturalness_score < 0.7:
            suggestions.append("Use a higher quality TTS backend (Coqui XTTS)")
        
        if not suggestions:
            suggestions.append("Quality is acceptable for KYC")
        
        return suggestions


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 LIP SYNC OPTIMIZER — Optimize lip sync for different PSPs
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class LipSyncConfig:
    """Lip sync configuration."""
    mouth_amplitude: float = 1.0
    jaw_movement: float = 0.8
    expression_intensity: float = 1.0
    head_motion: float = 0.3
    blink_frequency: float = 0.2
    sync_offset_ms: float = 0


class LipSyncOptimizer:
    """
    V7.6 Lip Sync Optimizer - Optimizes lip sync parameters
    for different KYC providers and detection systems.
    """
    
    # Pre-tuned profiles for different KYC providers
    PROVIDER_PROFILES = {
        "stripe_identity": LipSyncConfig(
            mouth_amplitude=1.1,
            jaw_movement=0.9,
            expression_intensity=1.0,
            head_motion=0.2,
            blink_frequency=0.25,
            sync_offset_ms=-50
        ),
        "onfido": LipSyncConfig(
            mouth_amplitude=1.0,
            jaw_movement=0.85,
            expression_intensity=0.9,
            head_motion=0.35,
            blink_frequency=0.2,
            sync_offset_ms=0
        ),
        "jumio": LipSyncConfig(
            mouth_amplitude=0.95,
            jaw_movement=0.8,
            expression_intensity=1.1,
            head_motion=0.25,
            blink_frequency=0.18,
            sync_offset_ms=-30
        ),
        "veriff": LipSyncConfig(
            mouth_amplitude=1.05,
            jaw_movement=0.9,
            expression_intensity=1.0,
            head_motion=0.3,
            blink_frequency=0.22,
            sync_offset_ms=0
        ),
        "default": LipSyncConfig()
    }
    
    def __init__(self):
        self._optimization_history: Dict[str, List[Dict]] = defaultdict(list)
    
    def get_config_for_provider(self, provider: str) -> LipSyncConfig:
        """Get optimized lip sync config for a provider."""
        return self.PROVIDER_PROFILES.get(
            provider.lower().replace(" ", "_"),
            self.PROVIDER_PROFILES["default"]
        )
    
    def optimize_for_success(self, provider: str,
                            base_config: Optional[LipSyncConfig] = None) -> LipSyncConfig:
        """
        Get optimized config based on past success history.
        
        Args:
            provider: KYC provider name
            base_config: Starting config to modify
        
        Returns:
            Optimized LipSyncConfig
        """
        config = base_config or self.get_config_for_provider(provider)
        history = self._optimization_history.get(provider, [])
        
        if not history:
            return config
        
        # Find best performing config from history
        successful = [h for h in history if h.get("success")]
        if not successful:
            return config
        
        # Average the successful configs
        avg_amplitude = sum(h["config"]["mouth_amplitude"] for h in successful) / len(successful)
        avg_jaw = sum(h["config"]["jaw_movement"] for h in successful) / len(successful)
        avg_expression = sum(h["config"]["expression_intensity"] for h in successful) / len(successful)
        
        return LipSyncConfig(
            mouth_amplitude=avg_amplitude,
            jaw_movement=avg_jaw,
            expression_intensity=avg_expression,
            head_motion=config.head_motion,
            blink_frequency=config.blink_frequency,
            sync_offset_ms=config.sync_offset_ms
        )
    
    def record_result(self, provider: str, config: LipSyncConfig, success: bool):
        """Record a KYC attempt result for optimization."""
        self._optimization_history[provider].append({
            "config": {
                "mouth_amplitude": config.mouth_amplitude,
                "jaw_movement": config.jaw_movement,
                "expression_intensity": config.expression_intensity
            },
            "success": success,
            "timestamp": time.time()
        })
        
        # Keep only last 50 attempts
        if len(self._optimization_history[provider]) > 50:
            self._optimization_history[provider] = self._optimization_history[provider][-50:]
    
    def get_success_rate(self, provider: str) -> float:
        """Get success rate for a provider."""
        history = self._optimization_history.get(provider, [])
        if not history:
            return 0
        
        successful = sum(1 for h in history if h.get("success"))
        return successful / len(history)
    
    def apply_to_video(self, video_path: str, config: LipSyncConfig,
                      output_path: str) -> bool:
        """
        Apply lip sync adjustments to video.
        
        Note: This is a simplified implementation. Full lip sync
        optimization requires integration with LivePortrait or
        similar tools.
        """
        try:
            # Apply sync offset and expression adjustments via ffmpeg
            filters = []
            
            # Sync offset
            if config.sync_offset_ms != 0:
                offset = config.sync_offset_ms / 1000
                if offset > 0:
                    filters.append(f"adelay={abs(int(config.sync_offset_ms))}|{abs(int(config.sync_offset_ms))}")
                else:
                    filters.append(f"atrim=start={abs(offset)}")
            
            # Expression intensity via contrast/saturation
            if config.expression_intensity != 1.0:
                contrast = config.expression_intensity
                filters.append(f"eq=contrast={contrast}")
            
            filter_str = ",".join(filters) if filters else "copy"
            
            cmd = [
                "ffmpeg", "-y", "-i", video_path,
                "-vf", filter_str if "eq=" in filter_str else "copy",
                "-af", filter_str if "adelay" in filter_str or "atrim" in filter_str else "acopy",
                "-c:v", "libx264", "-c:a", "aac",
                output_path
            ]
            
            subprocess.run(cmd, capture_output=True, timeout=60)
            return os.path.exists(output_path)
            
        except Exception as e:
            logger.warning(f"Lip sync optimization failed: {e}")
            return False


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 MULTI-LANGUAGE VOICE ENGINE — Handle multiple languages and accents
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class LanguageSupport:
    """Language support information."""
    code: str
    name: str
    accents: List[str]
    piper_models: List[str]
    espeak_voice: str
    default_gender: VoiceGender


class MultiLanguageVoiceEngine:
    """
    V7.6 Multi-Language Voice Engine - Handles TTS across
    multiple languages with appropriate accent matching.
    """
    
    # Supported languages with configuration
    LANGUAGES = {
        "en": LanguageSupport(
            code="en",
            name="English",
            accents=["us", "gb", "au", "in"],
            piper_models=["en_US-lessac-medium", "en_GB-alan-medium"],
            espeak_voice="en",
            default_gender=VoiceGender.MALE
        ),
        "es": LanguageSupport(
            code="es",
            name="Spanish",
            accents=["es", "mx", "ar"],
            piper_models=["es_ES-davefx-medium", "es_MX-arlette-medium"],
            espeak_voice="es",
            default_gender=VoiceGender.MALE
        ),
        "fr": LanguageSupport(
            code="fr",
            name="French",
            accents=["fr", "ca"],
            piper_models=["fr_FR-siwis-medium"],
            espeak_voice="fr",
            default_gender=VoiceGender.FEMALE
        ),
        "de": LanguageSupport(
            code="de",
            name="German",
            accents=["de", "at", "ch"],
            piper_models=["de_DE-thorsten-medium"],
            espeak_voice="de",
            default_gender=VoiceGender.MALE
        ),
        "it": LanguageSupport(
            code="it",
            name="Italian",
            accents=["it"],
            piper_models=["it_IT-riccardo-medium"],
            espeak_voice="it",
            default_gender=VoiceGender.MALE
        ),
        "pt": LanguageSupport(
            code="pt",
            name="Portuguese",
            accents=["br", "pt"],
            piper_models=["pt_BR-faber-medium"],
            espeak_voice="pt-br",
            default_gender=VoiceGender.MALE
        ),
    }
    
    def __init__(self, base_engine: Optional[KYCVoiceEngine] = None):
        """
        Initialize multi-language engine.
        
        Args:
            base_engine: KYCVoiceEngine instance to use
        """
        self.base_engine = base_engine or KYCVoiceEngine()
        self._download_status: Dict[str, bool] = {}
    
    def get_supported_languages(self) -> List[Dict]:
        """Get list of supported languages."""
        return [
            {
                "code": lang.code,
                "name": lang.name,
                "accents": lang.accents,
                "default_gender": lang.default_gender.value
            }
            for lang in self.LANGUAGES.values()
        ]
    
    def get_voice_profile(self, language: str, accent: Optional[str] = None,
                         gender: Optional[VoiceGender] = None) -> VoiceProfile:
        """
        Get voice profile for a language.
        
        Args:
            language: Language code (e.g., "en", "es")
            accent: Optional accent (e.g., "us", "gb")
            gender: Optional gender preference
        
        Returns:
            VoiceProfile for the language
        """
        lang_support = self.LANGUAGES.get(language, self.LANGUAGES["en"])
        
        actual_accent = accent if accent in lang_support.accents else lang_support.accents[0]
        actual_gender = gender or lang_support.default_gender
        
        # Select appropriate Piper model
        piper_model = lang_support.piper_models[0]
        for model in lang_support.piper_models:
            if actual_accent.upper() in model or actual_accent.lower() in model:
                piper_model = model
                break
        
        return VoiceProfile(
            gender=actual_gender,
            language=language,
            accent=actual_accent,
            piper_model=piper_model
        )
    
    def detect_language(self, text: str) -> str:
        """
        Detect language of text.
        
        Simple heuristic based on character frequency.
        For production, use langdetect or similar.
        """
        # Common language indicators
        indicators = {
            "es": ["ñ", "¿", "¡"],
            "fr": ["ç", "œ", "ê", "é"],
            "de": ["ß", "ü", "ö", "ä"],
            "pt": ["ã", "ç", "õ"],
            "it": ["è", "ò", "ù"],
        }
        
        text_lower = text.lower()
        for lang, chars in indicators.items():
            if any(c in text_lower for c in chars):
                return lang
        
        return "en"
    
    def generate_speech(self, text: str, language: Optional[str] = None,
                       accent: Optional[str] = None,
                       gender: Optional[VoiceGender] = None,
                       output_path: Optional[str] = None) -> Optional[str]:
        """
        Generate speech in specified language.
        
        Auto-detects language if not specified.
        """
        if language is None:
            language = self.detect_language(text)
        
        voice = self.get_voice_profile(language, accent, gender)
        return self.base_engine.generate_speech(text, voice, output_path)
    
    def get_accent_for_country(self, country_code: str) -> Tuple[str, str]:
        """
        Get language and accent for a country code.
        
        Args:
            country_code: ISO country code (e.g., "US", "GB", "MX")
        
        Returns:
            Tuple of (language, accent)
        """
        # Country to language/accent mapping
        mapping = {
            "US": ("en", "us"),
            "GB": ("en", "gb"),
            "CA": ("en", "us"),
            "AU": ("en", "au"),
            "IN": ("en", "in"),
            "ES": ("es", "es"),
            "MX": ("es", "mx"),
            "AR": ("es", "ar"),
            "FR": ("fr", "fr"),
            "DE": ("de", "de"),
            "AT": ("de", "at"),
            "CH": ("de", "ch"),
            "IT": ("it", "it"),
            "BR": ("pt", "br"),
            "PT": ("pt", "pt"),
        }
        
        return mapping.get(country_code.upper(), ("en", "us"))


# Global instances
_voice_clone_engine: Optional[VoiceCloneEngine] = None
_speech_quality_analyzer: Optional[SpeechQualityAnalyzer] = None
_lip_sync_optimizer: Optional[LipSyncOptimizer] = None
_multi_language_engine: Optional[MultiLanguageVoiceEngine] = None


def get_voice_clone_engine() -> VoiceCloneEngine:
    """Get global voice clone engine."""
    global _voice_clone_engine
    if _voice_clone_engine is None:
        _voice_clone_engine = VoiceCloneEngine()
    return _voice_clone_engine


def get_speech_quality_analyzer() -> SpeechQualityAnalyzer:
    """Get global speech quality analyzer."""
    global _speech_quality_analyzer
    if _speech_quality_analyzer is None:
        _speech_quality_analyzer = SpeechQualityAnalyzer()
    return _speech_quality_analyzer


def get_lip_sync_optimizer() -> LipSyncOptimizer:
    """Get global lip sync optimizer."""
    global _lip_sync_optimizer
    if _lip_sync_optimizer is None:
        _lip_sync_optimizer = LipSyncOptimizer()
    return _lip_sync_optimizer


def get_multi_language_engine() -> MultiLanguageVoiceEngine:
    """Get global multi-language voice engine."""
    global _multi_language_engine
    if _multi_language_engine is None:
        _multi_language_engine = MultiLanguageVoiceEngine()
    return _multi_language_engine
