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
    version="7.5.0",
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
