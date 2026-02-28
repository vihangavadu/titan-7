#!/usr/bin/env python3
"""
Genesis AppX Bridge API
=======================
Flask service that implements Multilogin 6-compatible REST endpoints
backed by Titan OS Genesis Core engine.

This bridge allows the modified ML6 Electron shell to communicate
with the Genesis profile engine, providing:
- Profile CRUD (create/read/update/delete)
- Fingerprint generation & management
- Browser launch orchestration
- Genesis-specific features (archetypes, targets, AI intelligence)

Runs on localhost:36200 (separate from ML6's Express on :35000)
"""

import os
import sys
import json
import uuid
import time
import shutil
import hashlib
import logging
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

# Add Titan paths
TITAN_ROOT = Path(os.environ.get("TITAN_ROOT", "/opt/titan"))
for p in [str(TITAN_ROOT), str(TITAN_ROOT / "core"), str(TITAN_ROOT / "apps")]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from flask import Flask, request, jsonify, send_file
    from flask_cors import CORS
except ImportError:
    print("Installing Flask dependencies...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "flask", "flask-cors", "-q"])
    from flask import Flask, request, jsonify, send_file
    from flask_cors import CORS

# Try to import Genesis engine
try:
    from genesis_core import (
        GenesisEngine, ProfileConfig, TargetPreset, ProfileArchetype,
        TARGET_PRESETS, ARCHETYPE_CONFIGS, GeneratedProfile,
        OSConsistencyValidator, pre_forge_validate, score_profile_quality
    )
    GENESIS_AVAILABLE = True
except ImportError:
    GENESIS_AVAILABLE = False
    print("[WARN] Genesis core not available - running in standalone mode")

# Try to import AI engine
try:
    from ai_intelligence_engine import AIIntelligenceEngine
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO, format="[GenesisAppX] %(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("genesis-bridge")

# ─── Configuration ──────────────────────────────────────────────────────────
BRIDGE_PORT = int(os.environ.get("GENESIS_BRIDGE_PORT", 36200))
PROFILES_DIR = Path(os.environ.get("GENESIS_PROFILES_DIR", os.path.expanduser("~/.genesis_appx/profiles")))
CONFIG_DIR = Path(os.environ.get("GENESIS_CONFIG_DIR", os.path.expanduser("~/.genesis_appx")))
PROFILES_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

# Profile database (JSON file)
DB_PATH = CONFIG_DIR / "profiles_db.json"

# Initialize Genesis engine
genesis_engine = None
if GENESIS_AVAILABLE:
    genesis_engine = GenesisEngine(output_dir=str(PROFILES_DIR))

# ─── Profile Database ───────────────────────────────────────────────────────

def _load_db() -> Dict:
    if DB_PATH.exists():
        with open(DB_PATH, 'r') as f:
            return json.load(f)
    return {"profiles": {}, "groups": {}, "settings": {}}

def _save_db(db: Dict):
    with open(DB_PATH, 'w') as f:
        json.dump(db, f, indent=2)

def _generate_sid() -> str:
    return str(uuid.uuid4())

def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


# ═══════════════════════════════════════════════════════════════════════════
# ML6-COMPATIBLE ENDPOINTS (Bridge API)
# These endpoints match what the ML6 Electron renderer expects
# ═══════════════════════════════════════════════════════════════════════════

# ─── Auth / Session (BYPASSED - always authenticated) ────────────────────

@app.route("/bridge/apiToken", methods=["GET"])
def bridge_api_token():
    """Return a fake auth token - auth is bypassed."""
    return jsonify({
        "status": "OK",
        "value": "genesis-local-token-" + hashlib.md5(str(time.time()).encode()).hexdigest()[:16]
    })

@app.route("/bridge/onToken", methods=["GET"])
def bridge_on_token():
    """Token event - always returns valid."""
    return jsonify({"status": "OK", "value": True})

@app.route("/bridge/signOut", methods=["GET", "POST"])
def bridge_sign_out():
    """Sign out - no-op in local mode."""
    return jsonify({"status": "OK"})

@app.route("/bridge/isShowRegistrationBlock", methods=["GET"])
def bridge_show_registration():
    """Never show registration block."""
    return jsonify({"status": "OK", "value": False})

@app.route("/bridge/startSection", methods=["GET"])
def bridge_start_section():
    """Return the start section - always profile dashboard."""
    return jsonify({"status": "OK", "value": "profile"})

# ─── System Info ─────────────────────────────────────────────────────────

@app.route("/version", methods=["GET"])
def get_version():
    return jsonify({"version": "6.5.0-genesis", "build": "genesis-appx-1.0"})

@app.route("/bridge/os", methods=["GET"])
def bridge_os():
    import platform
    return jsonify({"status": "OK", "value": platform.system().lower()})

@app.route("/bridge/connectionSettings", methods=["GET"])
def bridge_connection_settings():
    return jsonify({
        "status": "OK",
        "value": {"connected": True, "offline": False, "localMode": True}
    })

@app.route("/bridge/availableSystemFonts", methods=["GET"])
def bridge_system_fonts():
    """Return available system fonts for fingerprint configuration."""
    fonts = [
        "Arial", "Arial Black", "Comic Sans MS", "Courier New", "Georgia",
        "Impact", "Times New Roman", "Trebuchet MS", "Verdana", "Helvetica",
        "Lucida Console", "Lucida Sans Unicode", "Palatino Linotype",
        "Tahoma", "Segoe UI", "Microsoft Sans Serif", "Calibri", "Cambria",
        "Consolas", "Candara", "Franklin Gothic Medium", "Garamond",
        "Book Antiqua", "Century Gothic", "Copperplate Gothic Bold",
        "DejaVu Sans", "DejaVu Serif", "DejaVu Sans Mono",
        "Liberation Sans", "Liberation Serif", "Liberation Mono",
        "Noto Sans", "Noto Serif", "Roboto", "Open Sans", "Lato",
        "Source Sans Pro", "Ubuntu", "Fira Sans", "Droid Sans",
    ]
    return jsonify({"status": "OK", "value": fonts})

@app.route("/bridge/persistentFonts", methods=["GET"])
def bridge_persistent_fonts():
    return jsonify({"status": "OK", "value": []})

@app.route("/systemScreenResolution", methods=["GET"])
def system_screen_resolution():
    return jsonify({"status": "OK", "value": {"width": 1920, "height": 1080}})

@app.route("/bridge/browserTypeVersions", methods=["GET"])
def bridge_browser_versions():
    return jsonify({
        "status": "OK",
        "value": {
            "mimic": "133.0",
            "stealthfox": "128.0",
            "mimic_mobile": "133.0"
        }
    })

@app.route("/browser-cores-version", methods=["GET"])
def browser_cores_version():
    return jsonify({
        "mimic": {"version": "133.0", "available": True},
        "stealthfox": {"version": "128.0", "available": True}
    })

@app.route("/bridge/isProfileExperimentalFeaturesEnabled", methods=["GET"])
def bridge_experimental():
    return jsonify({"status": "OK", "value": True})

@app.route("/bridge/error", methods=["POST"])
def bridge_error():
    data = request.get_json(silent=True) or {}
    logger.warning(f"Client error: {data}")
    return jsonify({"status": "OK"})

@app.route("/bridge/log", methods=["POST"])
def bridge_log():
    data = request.get_json(silent=True) or {}
    logger.info(f"Client log: {data}")
    return jsonify({"status": "OK"})

@app.route("/bridge/events", methods=["GET"])
def bridge_events():
    """SSE event stream - return empty for now."""
    return jsonify({"status": "OK", "events": []})

@app.route("/msgs/startup/i18n", methods=["GET"])
def msgs_i18n():
    return jsonify({
        "appName": "Genesis AppX",
        "loading": "Loading Genesis AppX...",
        "version": "Powered by Titan OS Genesis Engine"
    })

# ─── Plan / Subscription (always premium) ────────────────────────────────

@app.route("/rest/v1/plans/current", methods=["GET"])
def plans_current():
    return jsonify({
        "plan": "genesis_unlimited",
        "name": "Genesis AppX Unlimited",
        "profiles_limit": 99999,
        "team_members_limit": 99999,
        "browser_profiles_used": 0,
        "is_active": True,
        "features": {
            "mimic": True, "stealthfox": True, "mimic_mobile": True,
            "cookie_import": True, "api_access": True, "automation": True,
            "custom_dns": True, "profile_sharing": True
        }
    })

@app.route("/uaa/rest/v1/lastNotifiedVersion", methods=["GET"])
def last_notified_version():
    return jsonify({"version": "6.5.0"})

@app.route("/uaa/rest/v1/u/billing-url", methods=["GET"])
def billing_url():
    return jsonify({"url": ""})

@app.route("/rest/ui/v1/global-config", methods=["GET"])
def global_config():
    return jsonify({
        "screenResolutions": [
            "1920x1080", "2560x1440", "1366x768", "1536x864",
            "3840x2160", "2560x1600", "1440x900", "1680x1050",
            "3024x1964", "2560x1664"
        ],
        "browserTypes": ["mimic", "stealthfox", "mimic_mobile"],
        "operatingSystems": [
            {"name": "Windows 11", "value": "win"},
            {"name": "Windows 10", "value": "win"},
            {"name": "macOS Sonoma", "value": "mac"},
            {"name": "macOS Ventura", "value": "mac"},
            {"name": "Linux", "value": "lin"},
            {"name": "Android", "value": "android"}
        ],
        "languages": [
            "en-US", "en-GB", "de-DE", "fr-FR", "es-ES", "it-IT",
            "pt-BR", "ja-JP", "ko-KR", "zh-CN", "ru-RU", "nl-NL"
        ],
        "timezones": [
            "America/New_York", "America/Chicago", "America/Denver",
            "America/Los_Angeles", "America/Phoenix", "Europe/London",
            "Europe/Berlin", "Europe/Paris", "Asia/Tokyo", "Asia/Shanghai",
            "Australia/Sydney", "Pacific/Auckland"
        ]
    })

# ═══════════════════════════════════════════════════════════════════════════
# PROFILE MANAGEMENT (ML6-compatible + Genesis-enhanced)
# ═══════════════════════════════════════════════════════════════════════════

@app.route("/rest/ui/v1/group/profile/list", methods=["POST"])
def list_profiles():
    """List all profiles - ML6 group-based listing."""
    db = _load_db()
    profiles_list = []
    for sid, profile in db.get("profiles", {}).items():
        profiles_list.append({
            "sid": sid,
            "name": profile.get("name", "Unnamed"),
            "browserType": profile.get("browserType", "mimic"),
            "os": profile.get("os", "win"),
            "status": profile.get("status", "ready"),
            "notes": profile.get("notes", ""),
            "group": profile.get("group", "default"),
            "createdAt": profile.get("createdAt", ""),
            "updatedAt": profile.get("updatedAt", ""),
            "lastUsed": profile.get("lastUsed", ""),
            # Genesis-specific fields
            "archetype": profile.get("archetype", ""),
            "target": profile.get("target", ""),
            "ageDays": profile.get("ageDays", 0),
            "qualityScore": profile.get("qualityScore", 0),
            "genesisProfile": profile.get("genesisProfile", False),
        })
    return jsonify({"status": "OK", "profiles": profiles_list})

@app.route("/api/v1/profile/create", methods=["POST"])
def create_profile():
    """Create a new browser profile."""
    data = request.get_json(silent=True) or {}
    sid = _generate_sid()
    now = _now_iso()

    profile = {
        "sid": sid,
        "name": data.get("name", f"Profile {sid[:8]}"),
        "browserType": data.get("browserType", "mimic"),
        "os": data.get("os", "win"),
        "status": "ready",
        "notes": data.get("notes", ""),
        "group": data.get("group", "default"),
        "createdAt": now,
        "updatedAt": now,
        "lastUsed": "",
        # Fingerprint config
        "fingerprint": {
            "navigator": {
                "userAgent": data.get("userAgent", ""),
                "platform": data.get("platform", "Win32"),
                "hardwareConcurrency": data.get("hardwareConcurrency", 8),
                "deviceMemory": data.get("deviceMemory", 8),
                "maxTouchPoints": data.get("maxTouchPoints", 0),
                "language": data.get("language", "en-US"),
                "languages": data.get("languages", ["en-US", "en"]),
            },
            "screen": {
                "resolution": data.get("resolution", "1920x1080"),
                "colorDepth": data.get("colorDepth", 24),
            },
            "webgl": {
                "vendor": data.get("webglVendor", "Google Inc. (NVIDIA)"),
                "renderer": data.get("webglRenderer", "ANGLE (NVIDIA, NVIDIA GeForce RTX 4070 Direct3D11 vs_5_0 ps_5_0, D3D11)"),
            },
            "webrtc": {
                "mode": data.get("webrtcMode", "altered"),
                "publicIp": data.get("webrtcPublicIp", ""),
            },
            "canvas": {"mode": data.get("canvasMode", "noise")},
            "audio": {"mode": data.get("audioMode", "noise")},
            "fonts": data.get("fonts", []),
            "timezone": data.get("timezone", "America/New_York"),
            "geolocation": {
                "mode": data.get("geoMode", "prompt"),
                "latitude": data.get("latitude", ""),
                "longitude": data.get("longitude", ""),
            },
            "doNotTrack": data.get("doNotTrack", False),
        },
        # Proxy config
        "proxy": {
            "type": data.get("proxyType", "none"),
            "host": data.get("proxyHost", ""),
            "port": data.get("proxyPort", ""),
            "username": data.get("proxyUser", ""),
            "password": data.get("proxyPass", ""),
        },
        # Genesis-specific
        "genesisProfile": False,
        "archetype": data.get("archetype", ""),
        "target": data.get("target", ""),
        "ageDays": data.get("ageDays", 0),
        "qualityScore": 0,
        "personaName": data.get("personaName", ""),
        "personaEmail": data.get("personaEmail", ""),
        "billingAddress": data.get("billingAddress", {}),
    }

    db = _load_db()
    db["profiles"][sid] = profile
    _save_db(db)

    logger.info(f"Profile created: {sid} ({profile['name']})")
    return jsonify({"status": "OK", "sid": sid, "profile": profile})

@app.route("/api/v1/profile/<sid>", methods=["GET"])
def get_profile(sid):
    """Get profile details."""
    db = _load_db()
    profile = db.get("profiles", {}).get(sid)
    if not profile:
        return jsonify({"status": "ERROR", "message": "Profile not found"}), 404
    return jsonify({"status": "OK", "profile": profile})

@app.route("/api/v1/profile/<sid>", methods=["PUT"])
def update_profile(sid):
    """Update profile settings."""
    db = _load_db()
    profile = db.get("profiles", {}).get(sid)
    if not profile:
        return jsonify({"status": "ERROR", "message": "Profile not found"}), 404

    data = request.get_json(silent=True) or {}
    # Merge update data
    for key, value in data.items():
        if isinstance(value, dict) and key in profile and isinstance(profile[key], dict):
            profile[key].update(value)
        else:
            profile[key] = value
    profile["updatedAt"] = _now_iso()
    db["profiles"][sid] = profile
    _save_db(db)
    return jsonify({"status": "OK", "profile": profile})

@app.route("/api/v1/profile/<sid>", methods=["DELETE"])
def delete_profile(sid):
    """Delete a profile."""
    db = _load_db()
    if sid in db.get("profiles", {}):
        del db["profiles"][sid]
        _save_db(db)
        # Clean up profile directory
        profile_dir = PROFILES_DIR / f"titan_{sid[:12]}"
        if profile_dir.exists():
            shutil.rmtree(profile_dir, ignore_errors=True)
        logger.info(f"Profile deleted: {sid}")
    return jsonify({"status": "OK"})

@app.route("/api/v1/profile/<sid>/clone", methods=["POST"])
def clone_profile(sid):
    """Clone a profile."""
    db = _load_db()
    source = db.get("profiles", {}).get(sid)
    if not source:
        return jsonify({"status": "ERROR", "message": "Source profile not found"}), 404

    new_sid = _generate_sid()
    clone = json.loads(json.dumps(source))  # Deep copy
    clone["sid"] = new_sid
    clone["name"] = f"{source['name']} (Clone)"
    clone["createdAt"] = _now_iso()
    clone["updatedAt"] = _now_iso()

    db["profiles"][new_sid] = clone
    _save_db(db)
    logger.info(f"Profile cloned: {sid} -> {new_sid}")
    return jsonify({"status": "OK", "sid": new_sid, "profile": clone})

@app.route("/api/v1/profile/<sid>/status", methods=["GET"])
def profile_status(sid):
    """Get profile run status."""
    db = _load_db()
    profile = db.get("profiles", {}).get(sid)
    if not profile:
        return jsonify({"status": "ERROR", "message": "Profile not found"}), 404
    return jsonify({
        "status": "OK",
        "profileStatus": profile.get("status", "ready"),
        "browserPid": profile.get("browserPid", None)
    })

# ─── Profile Status Bulk ─────────────────────────────────────────────────

@app.route("/api/v1/profiles/statuses", methods=["GET"])
def profiles_statuses():
    """Get all profile statuses."""
    db = _load_db()
    statuses = {}
    for sid, profile in db.get("profiles", {}).items():
        statuses[sid] = {
            "status": profile.get("status", "ready"),
            "browserPid": profile.get("browserPid", None)
        }
    return jsonify({"status": "OK", "statuses": statuses})

# ─── Cookie Management ───────────────────────────────────────────────────

@app.route("/api/v1/profile/<sid>/cookies", methods=["GET"])
def get_cookies(sid):
    """Get profile cookies."""
    db = _load_db()
    profile = db.get("profiles", {}).get(sid)
    if not profile:
        return jsonify({"status": "ERROR", "message": "Profile not found"}), 404
    return jsonify({"status": "OK", "cookies": profile.get("cookies", [])})

@app.route("/api/v1/profile/<sid>/cookies", methods=["POST"])
def import_cookies(sid):
    """Import cookies into profile."""
    db = _load_db()
    profile = db.get("profiles", {}).get(sid)
    if not profile:
        return jsonify({"status": "ERROR", "message": "Profile not found"}), 404

    data = request.get_json(silent=True) or {}
    cookies = data.get("cookies", [])
    profile["cookies"] = cookies
    profile["updatedAt"] = _now_iso()
    db["profiles"][sid] = profile
    _save_db(db)
    return jsonify({"status": "OK", "imported": len(cookies)})

# ─── Group Management ────────────────────────────────────────────────────

@app.route("/api/v1/groups", methods=["GET"])
def list_groups():
    db = _load_db()
    groups = db.get("groups", {"default": {"name": "Default", "profiles": []}})
    return jsonify({"status": "OK", "groups": groups})

@app.route("/api/v1/groups", methods=["POST"])
def create_group():
    data = request.get_json(silent=True) or {}
    db = _load_db()
    gid = _generate_sid()
    db.setdefault("groups", {})[gid] = {
        "name": data.get("name", "New Group"),
        "profiles": []
    }
    _save_db(db)
    return jsonify({"status": "OK", "gid": gid})

# ═══════════════════════════════════════════════════════════════════════════
# GENESIS-SPECIFIC ENDPOINTS (Enhanced features beyond ML6)
# ═══════════════════════════════════════════════════════════════════════════

@app.route("/api/v1/genesis/targets", methods=["GET"])
def genesis_targets():
    """Get available target presets."""
    if not GENESIS_AVAILABLE:
        return jsonify({"status": "OK", "targets": []})
    targets = []
    for name, preset in TARGET_PRESETS.items():
        targets.append({
            "id": name,
            "name": preset.display_name,
            "domain": preset.domain,
            "category": preset.category.value,
            "recommendedAgeDays": preset.recommended_age_days,
            "browserPreference": preset.browser_preference,
            "notes": preset.notes,
        })
    return jsonify({"status": "OK", "targets": targets})

@app.route("/api/v1/genesis/archetypes", methods=["GET"])
def genesis_archetypes():
    """Get available profile archetypes."""
    if not GENESIS_AVAILABLE:
        return jsonify({"status": "OK", "archetypes": []})
    archetypes = GenesisEngine.get_available_archetypes()
    return jsonify({"status": "OK", "archetypes": archetypes})

@app.route("/api/v1/genesis/forge", methods=["POST"])
def genesis_forge():
    """Forge a Genesis-powered browser profile with full aged history."""
    if not genesis_engine:
        return jsonify({"status": "ERROR", "message": "Genesis engine not available"}), 503

    data = request.get_json(silent=True) or {}
    target_id = data.get("target", "amazon_us")
    archetype_name = data.get("archetype", "casual_shopper")
    persona_name = data.get("personaName", "Alex Mercer")
    persona_email = data.get("personaEmail", "alex.mercer@proton.me")
    billing_address = data.get("billingAddress", {
        "address": "1234 Oak Street",
        "city": "Austin",
        "state": "TX",
        "zip": "78701",
        "country": "US"
    })
    age_days = data.get("ageDays", 90)

    try:
        target = TARGET_PRESETS.get(target_id)
        if not target:
            target = list(TARGET_PRESETS.values())[0]

        archetype_map = {
            "student_developer": ProfileArchetype.STUDENT_DEVELOPER,
            "professional": ProfileArchetype.PROFESSIONAL,
            "retiree": ProfileArchetype.RETIREE,
            "gamer": ProfileArchetype.GAMER,
            "casual_shopper": ProfileArchetype.CASUAL_SHOPPER,
        }
        archetype = archetype_map.get(archetype_name, ProfileArchetype.CASUAL_SHOPPER)

        # Forge the profile
        profile = genesis_engine.forge_archetype_profile(
            archetype=archetype,
            target=target,
            persona_name=persona_name,
            persona_email=persona_email,
            billing_address=billing_address,
            age_days=age_days
        )

        # Score quality
        quality = score_profile_quality(profile.profile_path)

        # Generate handover doc
        genesis_engine.generate_handover_document(profile.profile_path, target.domain)

        # Create ML6-compatible profile entry
        sid = _generate_sid()
        now = _now_iso()
        hw = profile.hardware_fingerprint or {}

        db_profile = {
            "sid": sid,
            "name": f"{persona_name} - {target.display_name}",
            "browserType": "stealthfox" if target.browser_preference == "firefox" else "mimic",
            "os": "win" if "Win" in hw.get("platform", "Win32") else "mac" if "Mac" in hw.get("platform", "") else "lin",
            "status": "ready",
            "notes": f"Genesis forged | {archetype_name} | {target.display_name} | {age_days}d aged",
            "group": "default",
            "createdAt": now,
            "updatedAt": now,
            "lastUsed": "",
            "genesisProfile": True,
            "archetype": archetype_name,
            "target": target_id,
            "ageDays": age_days,
            "qualityScore": quality.get("score", 0),
            "qualityVerdict": quality.get("verdict", "UNKNOWN"),
            "profilePath": str(profile.profile_path),
            "personaName": persona_name,
            "personaEmail": persona_email,
            "billingAddress": billing_address,
            "fingerprint": {
                "navigator": {
                    "userAgent": hw.get("user_agent", ""),
                    "platform": hw.get("platform", "Win32"),
                    "hardwareConcurrency": int(hw.get("cores", 8)),
                    "deviceMemory": int(hw.get("memory", "8GB").replace("GB", "")),
                    "language": "en-US",
                    "languages": ["en-US", "en"],
                },
                "screen": {
                    "resolution": hw.get("screen", "1920x1080"),
                },
                "webgl": {
                    "vendor": hw.get("gpu_vendor", ""),
                    "renderer": hw.get("gpu_renderer", ""),
                },
                "canvas": {"mode": "noise"},
                "audio": {"mode": "noise"},
                "timezone": billing_address.get("timezone", "America/New_York"),
            },
            "proxy": {"type": "none"},
            "stats": {
                "historyEntries": profile.history_count,
                "cookiesCount": profile.cookies_count,
                "profileSizeMB": quality.get("size_mb", 0),
                "fileCount": quality.get("file_count", 0),
            }
        }

        db = _load_db()
        db["profiles"][sid] = db_profile
        _save_db(db)

        logger.info(f"Genesis profile forged: {sid} ({persona_name}) quality={quality.get('score', 0)}")
        return jsonify({
            "status": "OK",
            "sid": sid,
            "profile": db_profile,
            "quality": quality,
        })

    except Exception as e:
        logger.error(f"Genesis forge failed: {e}", exc_info=True)
        return jsonify({"status": "ERROR", "message": str(e)}), 500

@app.route("/api/v1/genesis/validate", methods=["POST"])
def genesis_validate():
    """Pre-forge validation - check BIN/billing/hardware coherence."""
    if not GENESIS_AVAILABLE:
        return jsonify({"status": "ERROR", "message": "Genesis engine not available"}), 503

    data = request.get_json(silent=True) or {}
    result = pre_forge_validate(
        bin6=data.get("bin6", ""),
        billing_address=data.get("billingAddress", {}),
        hardware_profile=data.get("hardwareProfile", "us_windows_desktop"),
        proxy_region=data.get("proxyRegion", "")
    )
    return jsonify({"status": "OK", "validation": result})

@app.route("/api/v1/genesis/os-validate", methods=["POST"])
def genesis_os_validate():
    """Validate OS consistency of a profile."""
    if not GENESIS_AVAILABLE:
        return jsonify({"status": "ERROR", "message": "Genesis engine not available"}), 503

    data = request.get_json(silent=True) or {}
    validator = OSConsistencyValidator()
    result = validator.validate_profile(data)
    return jsonify({"status": "OK", "validation": result})

@app.route("/api/v1/genesis/ai/status", methods=["GET"])
def genesis_ai_status():
    """Get AI engine status."""
    if AI_AVAILABLE:
        try:
            engine = AIIntelligenceEngine()
            status = engine.get_ai_status() if hasattr(engine, 'get_ai_status') else {"available": True}
            return jsonify({"status": "OK", "ai": status})
        except Exception as e:
            return jsonify({"status": "OK", "ai": {"available": False, "error": str(e)}})
    return jsonify({"status": "OK", "ai": {"available": False}})

@app.route("/api/v1/genesis/fingerprint/generate", methods=["POST"])
def genesis_generate_fingerprint():
    """Generate a real fingerprint using Genesis engine."""
    data = request.get_json(silent=True) or {}
    hw_profile = data.get("hardwareProfile", "us_windows_desktop")

    if genesis_engine:
        config = ProfileConfig(
            target=list(TARGET_PRESETS.values())[0],
            persona_name="Temp",
            persona_email="temp@temp.com",
            persona_address={},
            hardware_profile=hw_profile,
        )
        hw = genesis_engine._generate_hardware_fingerprint(config)
        return jsonify({"status": "OK", "fingerprint": hw})

    return jsonify({"status": "ERROR", "message": "Genesis engine not available"}), 503

@app.route("/api/v1/genesis/hardware-profiles", methods=["GET"])
def genesis_hardware_profiles():
    """List available hardware profiles."""
    profiles = [
        "us_windows_desktop", "us_windows_desktop_amd", "us_windows_desktop_intel",
        "us_macbook_pro", "us_macbook_air_m2", "us_macbook_m1",
        "eu_windows_laptop", "us_windows_laptop_gaming", "us_windows_laptop_budget",
        "linux_desktop"
    ]
    return jsonify({"status": "OK", "profiles": profiles})


# ─── Fingerprint Font Endpoints (ML6-compatible) ─────────────────────────

@app.route("/mimic/random_fonts", methods=["GET"])
def mimic_random_fonts():
    """Generate random font subset for Mimic profiles."""
    import random
    all_fonts = [
        "Arial", "Arial Black", "Comic Sans MS", "Courier New", "Georgia",
        "Impact", "Times New Roman", "Trebuchet MS", "Verdana",
        "Lucida Console", "Tahoma", "Segoe UI", "Calibri", "Cambria",
    ]
    subset = random.sample(all_fonts, min(8, len(all_fonts)))
    return jsonify({"status": "OK", "fonts": subset})

@app.route("/stealth_fox/fonts", methods=["GET"])
def stealthfox_fonts():
    return jsonify({"status": "OK", "fonts": [
        "Arial", "Courier New", "Georgia", "Times New Roman", "Verdana",
        "DejaVu Sans", "DejaVu Serif", "Liberation Sans", "Liberation Serif",
    ]})

@app.route("/stealth_fox/random_fonts", methods=["GET"])
def stealthfox_random_fonts():
    import random
    fonts = ["Arial", "Courier New", "Georgia", "Times New Roman", "Verdana",
             "DejaVu Sans", "DejaVu Serif", "Liberation Sans"]
    return jsonify({"status": "OK", "fonts": random.sample(fonts, 5)})


# ─── Download (stub) ─────────────────────────────────────────────────────

@app.route("/download-browser-core/<browser_type>", methods=["GET"])
def download_browser_core(browser_type):
    return jsonify({
        "status": "OK",
        "message": f"Browser core '{browser_type}' is bundled with Genesis AppX",
        "available": True
    })


# ─── Health Check ────────────────────────────────────────────────────────

@app.route("/health", methods=["GET"])
@app.route("/api/v1/health", methods=["GET"])
def health():
    return jsonify({
        "ok": True,
        "service": "genesis-bridge-api",
        "version": "1.0.0",
        "genesis_engine": GENESIS_AVAILABLE,
        "ai_engine": AI_AVAILABLE,
        "profiles_dir": str(PROFILES_DIR),
        "profile_count": len(_load_db().get("profiles", {})),
    })


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logger.info(f"Genesis AppX Bridge API starting on port {BRIDGE_PORT}")
    logger.info(f"  Genesis Engine: {'READY' if GENESIS_AVAILABLE else 'NOT AVAILABLE'}")
    logger.info(f"  AI Engine: {'READY' if AI_AVAILABLE else 'NOT AVAILABLE'}")
    logger.info(f"  Profiles directory: {PROFILES_DIR}")
    logger.info(f"  Config directory: {CONFIG_DIR}")
    app.run(host="127.0.0.1", port=BRIDGE_PORT, debug=False)
