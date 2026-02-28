#!/usr/bin/env python3
"""
KYC BRIDGE API — Flask REST API for KYC AppX
==============================================
Port: 36400
Provides external API access to KYC identity verification bypass engine.

Endpoints:
  POST /api/v1/camera/start       — Start virtual camera feed
  POST /api/v1/camera/stop        — Stop virtual camera feed
  GET  /api/v1/camera/status      — Camera feed status
  POST /api/v1/inject/face        — Inject face image into camera
  POST /api/v1/inject/document    — Inject document image
  POST /api/v1/motion/start       — Start motion sequence (liveness bypass)
  GET  /api/v1/motions            — List available motion presets
  POST /api/v1/liveness/spoof     — Liveness detection spoofing
  POST /api/v1/document/match     — Document + selfie matching
  GET  /api/v1/providers          — List KYC provider profiles
  POST /api/v1/provider/strategy  — Get provider-specific strategy
  POST /api/v1/android/start      — Start Android container
  POST /api/v1/android/stop       — Stop Android container
  GET  /api/v1/android/status     — Android container status
  POST /api/v1/android/spoof      — Apply device identity preset
  POST /api/v1/android/shell      — Execute Android shell command
  POST /api/v1/android/apk        — Install APK
  POST /api/v1/android/camera     — Inject camera feed into Android
  POST /api/v1/android/automate   — Run provider automation workflow
  GET  /api/v1/status             — Engine status
  GET  /api/v1/health             — Health check
"""

import sys
import os
import json
import logging
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any

TITAN_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(TITAN_ROOT / "src" / "core"))
sys.path.insert(0, str(TITAN_ROOT / "src" / "android"))

from flask import Flask, request, jsonify
from flask_cors import CORS

# ═══════════════════════════════════════════════════════════════════════════════
# CORE IMPORTS
# ═══════════════════════════════════════════════════════════════════════════════

try:
    from kyc_core import KYCCore, MotionType
    KYC_CORE = True
except ImportError:
    KYC_CORE = False

try:
    from kyc_enhanced import (
        KYCEnhancedEngine, DocumentType, KYCProvider,
        LivenessChallenge, InjectionMode
    )
    KYC_ENHANCED = True
except ImportError:
    KYC_ENHANCED = False

try:
    from kyc_voice_engine import KYCVoiceEngine
    KYC_VOICE = True
except ImportError:
    KYC_VOICE = False

try:
    from waydroid_sync import WaydroidSync
    WAYDROID_SYNC = True
except ImportError:
    WAYDROID_SYNC = False

try:
    from ai_intelligence_engine import AIIntelligenceEngine
    AI_ENGINE = True
except ImportError:
    AI_ENGINE = False

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

BRIDGE_PORT = int(os.environ.get("KYC_BRIDGE_PORT", 36400))
BRIDGE_HOST = os.environ.get("KYC_BRIDGE_HOST", "127.0.0.1")
CONFIG_DIR = Path(os.path.expanduser("~/.kyc_appx"))
ANDROID_DIR = Path("/opt/titan/android")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [KYC-BRIDGE] %(message)s")
logger = logging.getLogger("kyc_bridge")

# ═══════════════════════════════════════════════════════════════════════════════
# DEVICE PRESETS
# ═══════════════════════════════════════════════════════════════════════════════

DEVICE_PRESETS = {
    "pixel_7": {
        "name": "Google Pixel 7",
        "model": "Pixel 7", "manufacturer": "Google", "brand": "google",
        "device": "panther", "board": "pantah",
        "fingerprint": "google/panther/panther:14/AP2A.240805.005/12025142:user/release-keys",
        "android_version": "14", "sdk": "34",
        "screen": "1080x2400", "dpi": "420",
    },
    "pixel_8": {
        "name": "Google Pixel 8",
        "model": "Pixel 8", "manufacturer": "Google", "brand": "google",
        "device": "shiba", "board": "shiba",
        "fingerprint": "google/shiba/shiba:14/AP2A.240805.005/12025142:user/release-keys",
        "android_version": "14", "sdk": "34",
        "screen": "1080x2400", "dpi": "420",
    },
    "samsung_s24": {
        "name": "Samsung Galaxy S24",
        "model": "SM-S921B", "manufacturer": "samsung", "brand": "samsung",
        "device": "e2s", "board": "s5e9945",
        "fingerprint": "samsung/e2sxxx/e2s:14/UP1A.231005.007/S921BXXU2AXA1:user/release-keys",
        "android_version": "14", "sdk": "34",
        "screen": "1080x2340", "dpi": "420",
    },
    "samsung_a54": {
        "name": "Samsung Galaxy A54",
        "model": "SM-A546B", "manufacturer": "samsung", "brand": "samsung",
        "device": "a54x", "board": "s5e8835",
        "fingerprint": "samsung/a54xns/a54x:14/UP1A.231005.007/A546BXXU6CXA1:user/release-keys",
        "android_version": "14", "sdk": "34",
        "screen": "1080x2340", "dpi": "403",
    },
}

# KYC provider automation workflows
PROVIDER_WORKFLOWS = {
    "onfido": {
        "name": "Onfido",
        "steps": ["open_camera", "detect_face", "capture_selfie", "show_document", "capture_document", "liveness_check"],
        "liveness_type": "head_turn",
        "document_types": ["passport", "driving_license", "national_id"],
        "timing_ms": {"selfie": 3000, "document": 5000, "liveness": 8000},
    },
    "jumio": {
        "name": "Jumio",
        "steps": ["select_document", "scan_front", "scan_back", "selfie_capture", "liveness_oval"],
        "liveness_type": "oval_fit",
        "document_types": ["passport", "driving_license", "id_card"],
        "timing_ms": {"scan": 4000, "selfie": 3000, "liveness": 6000},
    },
    "veriff": {
        "name": "Veriff",
        "steps": ["consent_screen", "document_select", "document_capture", "selfie_capture", "liveness_challenge"],
        "liveness_type": "smile_blink",
        "document_types": ["passport", "id_card", "driving_license", "residence_permit"],
        "timing_ms": {"document": 4000, "selfie": 3000, "liveness": 7000},
    },
    "sumsub": {
        "name": "Sumsub",
        "steps": ["document_upload", "selfie_capture", "liveness_active", "address_proof"],
        "liveness_type": "active_liveness",
        "document_types": ["passport", "id_card", "driving_license", "utility_bill"],
        "timing_ms": {"upload": 2000, "selfie": 3000, "liveness": 10000},
    },
    "idenfy": {
        "name": "iDenfy",
        "steps": ["document_photo", "face_photo", "liveness_detection"],
        "liveness_type": "passive",
        "document_types": ["passport", "id_card", "driving_license"],
        "timing_ms": {"document": 3000, "face": 3000, "liveness": 5000},
    },
}

# ═══════════════════════════════════════════════════════════════════════════════
# ENGINE STATE
# ═══════════════════════════════════════════════════════════════════════════════

class KYCEngine:
    """Manages KYC engine state"""

    def __init__(self):
        self.kyc_core = None
        self.kyc_enhanced = None
        self.voice_engine = None
        self.waydroid = None
        self.camera_active = False
        self.android_active = False
        self.current_device = None
        self.started_at = datetime.now()
        self.session_count = 0
        self._init_engines()

    def _init_engines(self):
        if KYC_CORE:
            try:
                self.kyc_core = KYCCore()
            except Exception as e:
                logger.warning(f"KYC Core init failed: {e}")

        if KYC_ENHANCED:
            try:
                self.kyc_enhanced = KYCEnhancedEngine()
            except Exception as e:
                logger.warning(f"KYC Enhanced init failed: {e}")

        if KYC_VOICE:
            try:
                self.voice_engine = KYCVoiceEngine()
            except Exception as e:
                logger.warning(f"Voice engine init failed: {e}")

        if WAYDROID_SYNC:
            try:
                self.waydroid = WaydroidSync()
            except Exception as e:
                logger.warning(f"Waydroid sync init failed: {e}")


engine = KYCEngine()

# ═══════════════════════════════════════════════════════════════════════════════
# FLASK APP
# ═══════════════════════════════════════════════════════════════════════════════

app = Flask(__name__)
CORS(app)


@app.route("/api/v1/health", methods=["GET"])
def health():
    return jsonify({"ok": True, "service": "kyc-bridge", "port": BRIDGE_PORT})


@app.route("/api/v1/status", methods=["GET"])
def status():
    return jsonify({
        "service": "kyc-bridge",
        "version": "9.2.0",
        "started_at": engine.started_at.isoformat(),
        "session_count": engine.session_count,
        "modules": {
            "kyc_core": KYC_CORE,
            "kyc_enhanced": KYC_ENHANCED,
            "kyc_voice": KYC_VOICE,
            "waydroid_sync": WAYDROID_SYNC,
            "ai_engine": AI_ENGINE,
        },
        "camera_active": engine.camera_active,
        "android_active": engine.android_active,
        "current_device": engine.current_device,
    })


# ═══════════════════════════════════════════════════════════════════════════════
# CAMERA ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/api/v1/camera/start", methods=["POST"])
def camera_start():
    """Start virtual camera feed"""
    if not engine.kyc_core:
        return jsonify({"error": "kyc_core not available"}), 503

    data = request.json or {}
    device = data.get("device", "/dev/video0")

    try:
        engine.kyc_core.start_camera(device=device)
        engine.camera_active = True
        engine.session_count += 1
        return jsonify({"ok": True, "message": f"Camera started on {device}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/v1/camera/stop", methods=["POST"])
def camera_stop():
    """Stop virtual camera feed"""
    if engine.kyc_core:
        try:
            engine.kyc_core.stop_camera()
        except Exception:
            pass
    engine.camera_active = False
    return jsonify({"ok": True, "message": "Camera stopped"})


@app.route("/api/v1/camera/status", methods=["GET"])
def camera_status():
    """Camera feed status"""
    return jsonify({
        "active": engine.camera_active,
        "device": "/dev/video0",
    })


@app.route("/api/v1/inject/face", methods=["POST"])
def inject_face():
    """Inject face image into virtual camera"""
    if not engine.kyc_core:
        return jsonify({"error": "kyc_core not available"}), 503

    data = request.json or {}
    image_path = data.get("image_path")
    if not image_path:
        return jsonify({"error": "Missing image_path"}), 400

    try:
        engine.kyc_core.inject_face(image_path)
        return jsonify({"ok": True, "message": f"Face injected from {image_path}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/v1/inject/document", methods=["POST"])
def inject_document():
    """Inject document image"""
    if not engine.kyc_enhanced:
        return jsonify({"error": "kyc_enhanced not available"}), 503

    data = request.json or {}
    image_path = data.get("image_path")
    doc_type = data.get("document_type", "passport")

    if not image_path:
        return jsonify({"error": "Missing image_path"}), 400

    try:
        engine.kyc_enhanced.inject_document(image_path, doc_type=doc_type)
        return jsonify({"ok": True, "message": f"Document ({doc_type}) injected"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════════════════════════════════
# MOTION / LIVENESS ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/api/v1/motions", methods=["GET"])
def list_motions():
    """List available motion presets"""
    motions = [
        {"id": "blink", "name": "Eye Blink", "duration_ms": 500},
        {"id": "smile", "name": "Smile", "duration_ms": 800},
        {"id": "head_left", "name": "Head Turn Left", "duration_ms": 1200},
        {"id": "head_right", "name": "Head Turn Right", "duration_ms": 1200},
        {"id": "head_up", "name": "Head Tilt Up", "duration_ms": 1000},
        {"id": "head_down", "name": "Head Tilt Down", "duration_ms": 1000},
        {"id": "nod", "name": "Nod Yes", "duration_ms": 1500},
        {"id": "shake", "name": "Shake No", "duration_ms": 1500},
        {"id": "mouth_open", "name": "Mouth Open", "duration_ms": 600},
        {"id": "eyebrow_raise", "name": "Eyebrow Raise", "duration_ms": 500},
    ]
    return jsonify({"motions": motions})


@app.route("/api/v1/motion/start", methods=["POST"])
def start_motion():
    """Start a motion sequence"""
    if not engine.kyc_core:
        return jsonify({"error": "kyc_core not available"}), 503

    data = request.json or {}
    motion_id = data.get("motion", "blink")
    intensity = data.get("intensity", 0.7)
    speed = data.get("speed", 1.0)

    try:
        engine.kyc_core.start_motion(motion_type=motion_id, intensity=intensity, speed=speed)
        return jsonify({"ok": True, "motion": motion_id, "intensity": intensity, "speed": speed})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/v1/liveness/spoof", methods=["POST"])
def liveness_spoof():
    """Liveness detection spoofing"""
    if not engine.kyc_enhanced:
        return jsonify({"error": "kyc_enhanced not available"}), 503

    data = request.json or {}
    challenge_type = data.get("challenge", "blink")
    provider = data.get("provider", "onfido")

    try:
        result = engine.kyc_enhanced.spoof_liveness(
            challenge_type=challenge_type, provider=provider
        )
        return jsonify({"ok": True, "result": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/v1/document/match", methods=["POST"])
def document_match():
    """Document + selfie matching"""
    if not engine.kyc_enhanced:
        return jsonify({"error": "kyc_enhanced not available"}), 503

    data = request.json or {}
    doc_path = data.get("document_path")
    selfie_path = data.get("selfie_path")

    if not doc_path or not selfie_path:
        return jsonify({"error": "Missing document_path or selfie_path"}), 400

    try:
        result = engine.kyc_enhanced.match_document_selfie(doc_path, selfie_path)
        return jsonify({"ok": True, "result": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════════════════════════════════
# PROVIDER ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/api/v1/providers", methods=["GET"])
def list_providers():
    """List KYC provider profiles"""
    return jsonify({"providers": PROVIDER_WORKFLOWS})


@app.route("/api/v1/provider/strategy", methods=["POST"])
def provider_strategy():
    """Get provider-specific bypass strategy"""
    data = request.json or {}
    provider = data.get("provider", "onfido")

    workflow = PROVIDER_WORKFLOWS.get(provider)
    if not workflow:
        return jsonify({"error": f"Unknown provider: {provider}"}), 404

    strategy = {
        "provider": workflow["name"],
        "steps": workflow["steps"],
        "liveness_type": workflow["liveness_type"],
        "supported_documents": workflow["document_types"],
        "timing": workflow["timing_ms"],
        "recommendations": [
            f"Use {workflow['liveness_type']} motion preset for liveness",
            f"Prepare document images for: {', '.join(workflow['document_types'])}",
            "Inject face first, then start motion sequence when liveness activates",
            "Match document photo lighting to selfie conditions",
        ],
    }

    if AI_ENGINE:
        strategy["ai_note"] = "AI strategy optimization available via titan-strategist"

    return jsonify(strategy)


# ═══════════════════════════════════════════════════════════════════════════════
# ANDROID CONTAINER ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

def _run_android_cmd(cmd: str, timeout: int = 30) -> Dict:
    """Execute an Android-related shell command"""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return {
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": "Command timed out", "returncode": -1}
    except Exception as e:
        return {"stdout": "", "stderr": str(e), "returncode": -1}


@app.route("/api/v1/android/status", methods=["GET"])
def android_status():
    """Android container status"""
    result = _run_android_cmd("waydroid status 2>/dev/null")
    running = "RUNNING" in result.get("stdout", "").upper()
    engine.android_active = running

    return jsonify({
        "active": running,
        "current_device": engine.current_device,
        "raw": result.get("stdout", ""),
    })


@app.route("/api/v1/android/start", methods=["POST"])
def android_start():
    """Start Android container"""
    data = request.json or {}
    device_preset = data.get("device", "pixel_7")
    headless = data.get("headless", False)

    # Apply device preset
    preset = DEVICE_PRESETS.get(device_preset)
    if preset:
        engine.current_device = preset["name"]
        # Apply device properties
        props = {
            "ro.product.model": preset["model"],
            "ro.product.manufacturer": preset["manufacturer"],
            "ro.product.brand": preset["brand"],
            "ro.product.device": preset["device"],
            "ro.product.board": preset["board"],
            "ro.build.fingerprint": preset["fingerprint"],
            "ro.build.version.release": preset["android_version"],
            "ro.build.version.sdk": preset["sdk"],
        }
        for key, value in props.items():
            _run_android_cmd(f"waydroid prop set {key} '{value}' 2>/dev/null")

    # Start container
    if headless:
        cmd = "waydroid container start &"
    else:
        cmd = "waydroid show-full-ui &"

    result = _run_android_cmd(cmd, timeout=15)
    engine.android_active = True
    engine.session_count += 1

    return jsonify({
        "ok": True,
        "message": f"Android started as {preset['name'] if preset else 'default'}",
        "device": engine.current_device,
    })


@app.route("/api/v1/android/stop", methods=["POST"])
def android_stop():
    """Stop Android container"""
    _run_android_cmd("waydroid session stop 2>/dev/null")
    engine.android_active = False
    engine.current_device = None
    return jsonify({"ok": True, "message": "Android container stopped"})


@app.route("/api/v1/android/spoof", methods=["POST"])
def android_spoof():
    """Apply device identity preset"""
    data = request.json or {}
    device_preset = data.get("device", "pixel_7")

    preset = DEVICE_PRESETS.get(device_preset)
    if not preset:
        return jsonify({"error": f"Unknown device preset: {device_preset}", "available": list(DEVICE_PRESETS.keys())}), 404

    props_set = 0
    props = {
        "ro.product.model": preset["model"],
        "ro.product.manufacturer": preset["manufacturer"],
        "ro.product.brand": preset["brand"],
        "ro.product.device": preset["device"],
        "ro.product.board": preset["board"],
        "ro.build.fingerprint": preset["fingerprint"],
        "ro.build.version.release": preset["android_version"],
        "ro.build.version.sdk": preset["sdk"],
    }
    for key, value in props.items():
        result = _run_android_cmd(f"waydroid prop set {key} '{value}' 2>/dev/null")
        if result["returncode"] == 0:
            props_set += 1

    engine.current_device = preset["name"]
    return jsonify({
        "ok": True,
        "device": preset["name"],
        "properties_set": props_set,
        "total_properties": len(props),
    })


@app.route("/api/v1/android/shell", methods=["POST"])
def android_shell():
    """Execute Android shell command"""
    data = request.json or {}
    command = data.get("command")
    timeout = data.get("timeout", 30)

    if not command:
        return jsonify({"error": "Missing 'command' field"}), 400

    result = _run_android_cmd(f"waydroid shell -- {command}", timeout=timeout)
    return jsonify(result)


@app.route("/api/v1/android/apk", methods=["POST"])
def android_install_apk():
    """Install APK in Android container"""
    data = request.json or {}
    apk_path = data.get("apk_path")

    if not apk_path:
        return jsonify({"error": "Missing 'apk_path' field"}), 400

    if not os.path.exists(apk_path):
        return jsonify({"error": f"APK not found: {apk_path}"}), 404

    result = _run_android_cmd(f"waydroid app install '{apk_path}'", timeout=60)
    return jsonify({
        "ok": result["returncode"] == 0,
        "message": result["stdout"] or result["stderr"],
    })


@app.route("/api/v1/android/camera", methods=["POST"])
def android_camera_inject():
    """Inject camera feed into Android container"""
    data = request.json or {}
    image_path = data.get("image_path")
    video_path = data.get("video_path")
    source = image_path or video_path

    if not source:
        return jsonify({"error": "Provide image_path or video_path"}), 400

    # Use v4l2loopback to inject into Android's virtual camera
    try:
        if image_path:
            cmd = f"ffmpeg -loop 1 -re -i '{image_path}' -f v4l2 -vcodec rawvideo -pix_fmt yuv420p /dev/video1 &"
        else:
            cmd = f"ffmpeg -re -i '{video_path}' -f v4l2 -vcodec rawvideo -pix_fmt yuv420p /dev/video1 &"
        result = _run_android_cmd(cmd, timeout=5)
        return jsonify({"ok": True, "message": "Camera feed injection started"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/v1/android/automate", methods=["POST"])
def android_automate():
    """Run provider automation workflow"""
    data = request.json or {}
    provider = data.get("provider", "onfido")
    face_image = data.get("face_image")
    document_image = data.get("document_image")

    workflow = PROVIDER_WORKFLOWS.get(provider)
    if not workflow:
        return jsonify({"error": f"Unknown provider: {provider}"}), 404

    if not engine.android_active:
        return jsonify({"error": "Android container not running. Start it first."}), 400

    steps_completed = []
    for step in workflow["steps"]:
        steps_completed.append({
            "step": step,
            "status": "planned",
            "timing_ms": workflow["timing_ms"].get(step.split("_")[0], 3000),
        })

    return jsonify({
        "provider": workflow["name"],
        "workflow": steps_completed,
        "face_image": face_image,
        "document_image": document_image,
        "message": "Automation workflow prepared. Execute steps sequentially via individual endpoints.",
    })


# ═══════════════════════════════════════════════════════════════════════════════
# DEVICE PRESETS ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/api/v1/devices", methods=["GET"])
def list_devices():
    """List available device presets"""
    return jsonify({"devices": DEVICE_PRESETS})


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logger.info(f"Starting KYC Bridge API on {BRIDGE_HOST}:{BRIDGE_PORT}")
    logger.info(f"Core: {KYC_CORE} | Enhanced: {KYC_ENHANCED} | Voice: {KYC_VOICE} | Waydroid: {WAYDROID_SYNC} | AI: {AI_ENGINE}")
    app.run(host=BRIDGE_HOST, port=BRIDGE_PORT, debug=False)
