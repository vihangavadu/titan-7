# TITAN V7.0.3 — Model Assets

This directory contains ML model files required by TITAN subsystems.

## Required Models

### Ghost Motor DMTG (Optional)
- **File:** `dmtg_denoiser.onnx`
- **Used by:** `core/ghost_motor_v6.py`
- **Purpose:** Learned denoising for diffusion mouse trajectory generation
- **Fallback:** Analytical Bezier + minimum-jerk engine (built-in, no model needed)
- **Generate:** `python3 scripts/generate_trajectory_model.py`

### LivePortrait (Required for KYC)
- **Directory:** `liveportrait/`
- **Used by:** `core/kyc_core.py`, `core/kyc_enhanced.py`
- **Purpose:** Neural facial reenactment for KYC liveness bypass
- **Install:** `pip3 install liveportrait && python3 -m liveportrait.download`
- **Fallback:** Pre-recorded motion videos in `/opt/titan/assets/motions/`

## Auto-Download

On first boot, `titan-first-boot` will attempt to download missing models
if network is available. Models can also be pre-staged here before ISO build.
