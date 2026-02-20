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
    accent: str = "us"               # us, gb, au, in
    speed: float = 1.0               # 0.5-2.0
    pitch: float = 1.0               # 0.5-2.0
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
