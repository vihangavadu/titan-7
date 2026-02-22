#!/usr/bin/env python3
"""
LUCID EMPIRE :: Backend API Server
TITAN V7.5 SINGULARITY

Starts the FastAPI backend that serves:
  - /api/validation/* — Forensic validation endpoints
  - /api/profiles/*   — Profile management
  - /api/health       — Health check
  - /api/status       — System status

Started by titan-backend-init.sh at boot.
Listens on 0.0.0.0:8000
"""

import sys
import os
import logging
from pathlib import Path

# Ensure import paths
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "/opt/titan/core")
sys.path.insert(0, "/opt/lucid-empire")

logging.basicConfig(
    level=logging.INFO,
    format="[TITAN-API] %(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

try:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
except ImportError:
    logger.error("FastAPI not installed. Run: pip3 install fastapi uvicorn")
    sys.exit(1)

app = FastAPI(
    title="TITAN V7.5 SINGULARITY API",
    description="Backend API for Lucid Empire Titan operations",
    version="8.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health + Status ──────────────────────────────────────────────────────────
@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "7.5.0", "service": "titan-backend"}


@app.get("/api/status")
async def status():
    import subprocess

    checks = {}

    # Kernel module
    try:
        result = subprocess.run(
            ["lsmod"], capture_output=True, text=True, timeout=5
        )
        checks["kernel_module"] = "titan_hw" in result.stdout
    except Exception:
        checks["kernel_module"] = False

    # V7.0 core
    try:
        from font_sanitizer import check_fonts
        checks["phase3_hardening"] = True
    except ImportError:
        checks["phase3_hardening"] = False

    # Camoufox
    try:
        from camoufox.sync_api import Camoufox
        checks["camoufox"] = True
    except ImportError:
        checks["camoufox"] = False

    return {"status": "operational", "checks": checks}


# ── Module Status Endpoints (v7.5) ──────────────────────────────────────────
@app.get("/api/genesis/status")
async def genesis_status():
    """Genesis identity synthesis engine status."""
    try:
        from genesis_core import GenesisEngine
        targets = GenesisEngine.get_available_targets()
        return {"status": "operational", "module": "genesis_core", "version": "7.5", "targets_loaded": len(targets)}
    except Exception as e:
        return {"status": "degraded", "module": "genesis_core", "error": str(e)}


@app.get("/api/cerberus/status")
async def cerberus_status():
    """Cerberus Enhanced asset validation intelligence status."""
    try:
        from cerberus_enhanced import AVSEngine, BINScoringEngine, AVSPreCheckEngine
        return {
            "status": "operational", "module": "cerberus_enhanced", "version": "7.5",
            "engines": ["AVSEngine", "BINScoringEngine", "SilentValidationEngine",
                        "GeoMatchChecker", "IssuingBankPatternPredictor", "MaxDrainEngine",
                        "AVSPreCheckEngine"]
        }
    except Exception as e:
        return {"status": "degraded", "module": "cerberus_enhanced", "error": str(e)}


@app.get("/api/kyc/status")
async def kyc_status():
    """KYC Enhanced verification compliance status."""
    try:
        from kyc_enhanced import KYCEnhancedController, AmbientLightingNormalizer
        return {
            "status": "operational", "module": "kyc_enhanced", "version": "7.5",
            "components": ["KYCEnhancedController", "AmbientLightingNormalizer"]
        }
    except Exception as e:
        return {"status": "degraded", "module": "kyc_enhanced", "error": str(e)}


@app.get("/api/ghost-motor/status")
async def ghost_motor_status():
    """Ghost Motor V7 behavioral biometrics status."""
    try:
        from ghost_motor_v6 import GhostMotorV7
        return {"status": "operational", "module": "ghost_motor_v7", "version": "7.5"}
    except Exception as e:
        return {"status": "degraded", "module": "ghost_motor_v7", "error": str(e)}


@app.get("/api/kill-switch/status")
async def kill_switch_status():
    """Kill Switch forensic wipe status."""
    try:
        from kill_switch import KillSwitch
        return {"status": "armed", "module": "kill_switch", "version": "7.5"}
    except Exception as e:
        return {"status": "degraded", "module": "kill_switch", "error": str(e)}


@app.get("/api/hardware/status")
async def hardware_status():
    """Hardware Shield kernel module status."""
    import subprocess
    hw_info = {"kernel_module": False, "spoofed_devices": 0}
    try:
        result = subprocess.run(["lsmod"], capture_output=True, text=True, timeout=5)
        hw_info["kernel_module"] = "titan_hw" in result.stdout
    except Exception:
        pass
    try:
        devs = Path("/opt/titan/state/spoofed_devices.json")
        if devs.exists():
            import json as _json
            hw_info["spoofed_devices"] = len(_json.loads(devs.read_text()))
    except Exception:
        pass
    return {"status": "operational" if hw_info["kernel_module"] else "degraded", "module": "hardware_shield", "info": hw_info}


@app.get("/api/tls/status")
async def tls_status():
    """TLS Parrot Engine status."""
    try:
        from tls_parrot import TLSParrotEngine, JA4PermutationEngine, DynamicGREASEShuffler
        return {
            "status": "operational", "module": "tls_parrot", "version": "7.5",
            "components": ["TLSParrotEngine", "JA4PermutationEngine", "DynamicGREASEShuffler"]
        }
    except Exception as e:
        return {"status": "degraded", "module": "tls_parrot", "error": str(e)}


# ── Profile endpoints ────────────────────────────────────────────────────────
@app.get("/api/profiles")
async def list_profiles():
    """List available identity profiles."""
    profiles_dir = "/opt/titan/profiles"
    profiles = []
    if os.path.isdir(profiles_dir):
        for name in sorted(os.listdir(profiles_dir)):
            full = os.path.join(profiles_dir, name)
            if os.path.isdir(full) and not name.startswith("."):
                meta_file = os.path.join(full, "profile_metadata.json")
                meta = {}
                if os.path.isfile(meta_file):
                    try:
                        import json
                        with open(meta_file) as f:
                            meta = json.load(f)
                    except Exception:
                        pass
                profiles.append({
                    "name": name,
                    "path": full,
                    "has_metadata": os.path.isfile(meta_file),
                    "persona": meta.get("config", {}).get("persona_name", "Unknown"),
                })
    return {"profiles": profiles, "count": len(profiles)}


# ── Genesis API: Profile Forge ──────────────────────────────────────────────
@app.post("/api/genesis/forge")
async def genesis_forge(
    nationality: str = "us",
    age: int = 35,
    history_density: float = 1.5,
    archetype: str = "professional"
):
    """
    Forge a new identity using Genesis engine.
    
    Args:
        nationality: US, UK, CA, AU, DE
        age: 18-75
        history_density: 0.5-3.0
        archetype: student, professional, retiree, gamer, casual
    
    Returns:
        Forged profile with metadata
    """
    try:
        from genesis_core import GenesisEngine, ProfileConfig, ProfileArchetype
        
        # Map archetype string to enum
        archetype_map = {
            "student": ProfileArchetype.STUDENT_DEVELOPER,
            "professional": ProfileArchetype.PROFESSIONAL,
            "retiree": ProfileArchetype.RETIREE,
            "gamer": ProfileArchetype.GAMER,
            "casual": ProfileArchetype.CASUAL_SHOPPER,
        }
        arch = archetype_map.get(archetype.lower(), ProfileArchetype.PROFESSIONAL)
        
        # Create config
        config = ProfileConfig(
            persona_name=f"Genesis-{nationality.upper()}-{age}",
            nationality=nationality.upper(),
            age_days=age * 365,
            profile_dir="/tmp",
            archetype=arch,
            history_density_multiplier=history_density
        )
        
        # Forge profile
        engine = GenesisEngine(config)
        profile = engine.forge_profile()
        
        return {
            "status": "success",
            "profile": {
                "name": profile.get("full_name", "Unknown"),
                "email": profile.get("email", ""),
                "nationality": nationality,
                "age": age,
                "archetype": archetype,
                "history_size_mb": profile.get("history_size_mb", 0),
                "trust_score": profile.get("trust_score", 0),
            },
            "timestamp": str(Path("/tmp").stat().st_mtime)
        }
    except Exception as e:
        logger.error(f"Genesis forge failed: {e}")
        return {"status": "error", "error": str(e)}, 500


# ── Cerberus API: Card Validation ─────────────────────────────────────────────
@app.post("/api/cerberus/validate")
async def cerberus_validate(
    card_number: str,
    expiry: str,
    cvv: str,
    cardholder_name: str,
    country: str = "us"
):
    """
    Validate card asset using Cerberus engine.
    
    Args:
        card_number: 16-digit card number (spaces allowed)
        expiry: MM/YY format
        cvv: 3-4 digit security code
        cardholder_name: Name on card
        country: Card BIN country (us, uk, ca, au, de, fr, etc.)
    
    Returns:
        Validation result with risk assessment
    """
    try:
        from cerberus_core import CerberusValidator, CardAsset, CardStatus
        from cerberus_enhanced import CardQualityGrader
        
        # Clean card number
        card_clean = card_number.replace(" ", "").replace("-", "")
        
        # Create CardAsset
        card = CardAsset(
            number=card_clean,
            expiry_month=int(expiry.split("/")[0]),
            expiry_year=2000 + int(expiry.split("/")[1]),
            cvv=cvv,
            cardholder_name=cardholder_name,
            country=country.upper()
        )
        
        # Validate using Cerberus
        validator = CerberusValidator()
        result = validator.validate_card(card)
        
        # Grade quality
        grader = CardQualityGrader()
        quality = grader.grade_card(card)
        
        return {
            "status": "success",
            "validation": {
                "card_masked": f"•••• •••• •••• {card_clean[-4:]}",
                "luhn_valid": result.luhn_valid,
                "bin_country": result.bin_country,
                "card_status": result.status.value,
                "quality_grade": quality.get("grade", "F"),
                "success_probability": quality.get("expected_success_rate", 0),
                "risk_score": result.risk_score,
                "notes": result.notes if hasattr(result, 'notes') else ""
            },
            "timestamp": str(Path("/tmp").stat().st_mtime)
        }
    except Exception as e:
        logger.error(f"Cerberus validation failed: {e}")
        return {"status": "error", "error": str(e)}, 500


# ── KYC API: Start Verification Session ───────────────────────────────────────
@app.post("/api/kyc/start-session")
async def kyc_start_session(
    provider: str = "iproov",
    challenge_type: str = "liveness",
    age_threshold: int = 18
):
    """
    Start a KYC verification session.
    
    Args:
        provider: iproov, jumio, id.me, au10tix, intellinetics, trulioo
        challenge_type: liveness, document, video_call
        age_threshold: Minimum age required
    
    Returns:
        Session token and flow instructions
    """
    try:
        from kyc_core import KYCController
        from kyc_enhanced import KYCProvider
        
        # Map provider string to enum
        provider_map = {
            "iproov": KYCProvider.IPROOV,
            "jumio": KYCProvider.JUMIO,
            "id.me": KYCProvider.IDME,
            "au10tix": KYCProvider.AU10TIX,
            "intellinetics": KYCProvider.INTELLINETICS,
            "trulioo": KYCProvider.TRULIOO,
        }
        prov = provider_map.get(provider.lower(), KYCProvider.IPROOV)
        
        # Create KYC session
        controller = KYCController()
        session = controller.start_session(
            provider=prov,
            challenge_type=challenge_type,
            age_threshold=age_threshold
        )
        
        import uuid
        session_id = str(uuid.uuid4())
        
        return {
            "status": "success",
            "session": {
                "session_id": session_id,
                "provider": provider,
                "challenge_type": challenge_type,
                "challenges": [
                    "hold_still", "blink", "smile", "turn_left", "turn_right",
                    "nod", "look_up", "look_down", "raise_eyebrows"
                ],
                "timeout_seconds": 300,
            },
            "instructions": f"Initiate {challenge_type} challenge with {provider}",
            "timestamp": str(Path("/tmp").stat().st_mtime)
        }
    except Exception as e:
        logger.error(f"KYC session start failed: {e}")
        return {"status": "error", "error": str(e)}, 500


# ── Ghost Motor API: Behavioral Trajectory Generation ───────────────────────────
@app.post("/api/ghost-motor/generate")
async def ghost_motor_generate(
    persona_type: str = "professional",
    interaction_type: str = "checkout",
    duration_seconds: int = 30
):
    """
    Generate behavioral biometric trajectory using Ghost Motor.
    
    Args:
        persona_type: gamer, casual, elderly, professional
        interaction_type: browsing, form_fill, checkout, login
        duration_seconds: Expected interaction duration
    
    Returns:
        Trajectory data and metadata
    """
    try:
        from ghost_motor_v6 import GhostMotorDiffusion, PersonaType, TrajectoryConfig
        
        # Map persona string to enum
        persona_map = {
            "gamer": PersonaType.GAMER,
            "casual": PersonaType.CASUAL,
            "elderly": PersonaType.ELDERLY,
            "professional": PersonaType.PROFESSIONAL,
        }
        persona = persona_map.get(persona_type.lower(), PersonaType.PROFESSIONAL)
        
        # Create trajectory config
        config = TrajectoryConfig(
            persona_type=persona,
            duration_sec=duration_seconds,
            width=1920,
            height=1080,
            use_diffusion=False  # Use analytical mode if ONNX not available
        )
        
        # Generate trajectory
        motor = GhostMotorDiffusion(config)
        trajectory = motor.generate_trajectory()
        
        return {
            "status": "success",
            "trajectory": {
                "persona": persona_type,
                "interaction_type": interaction_type,
                "duration_seconds": duration_seconds,
                "point_count": len(trajectory) if isinstance(trajectory, list) else 0,
                "features": {
                    "involves_overshoot": True,
                    "has_corrections": True,
                    "natural_pauses": True,
                    "acceleration_variance": "realistic"
                }
            },
            "timestamp": str(Path("/tmp").stat().st_mtime)
        }
    except Exception as e:
        logger.error(f"Ghost Motor generation failed: {e}")
        return {"status": "error", "error": str(e)}, 500


# ── Get Targets List ──────────────────────────────────────────────────────────
@app.get("/api/targets")
async def get_targets(category: str = None):
    """
    Get available target presets.
    
    Args:
        category: Optional filter (ecommerce, fintech, crypto, gaming, etc.)
    
    Returns:
        Target list with metadata
    """
    try:
        from target_discovery import list_targets
        targets = list_targets()
        
        if category:
            targets = [t for t in targets if t.get("category", "").lower() == category.lower()]
        
        return {
            "status": "success",
            "targets": targets,
            "count": len(targets),
            "timestamp": str(Path("/tmp").stat().st_mtime)
        }
    except Exception as e:
        logger.error(f"Target list failed: {e}")
        return {"status": "error", "error": str(e)}, 500


# ── Validation router ────────────────────────────────────────────────────────
try:
    from validation.validation_api import router as validation_router
    app.include_router(validation_router)
    logger.info("Validation API router mounted at /api/validation")
except ImportError as e:
    logger.warning(f"Validation API not available: {e}")


# ── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        import uvicorn
    except ImportError:
        logger.error("uvicorn not installed. Run: pip3 install uvicorn")
        sys.exit(1)

    logger.info("Starting TITAN V7.5 Backend API on 0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
