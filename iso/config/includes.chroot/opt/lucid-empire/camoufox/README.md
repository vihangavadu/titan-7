# Lucid Empire: Sovereign Identity Integration

## Overview
This repository has been transformed into the **Lucid Empire** platform, a weaponized identity infrastructure designed to defeat Generation 5 Fraud Detection Systems.

## Core Components

### 1. The Python Lobotomy (`pythonlib/lucid_browser/sync_api.py`)
- **Status**: ACTIVE
- **Function**: Enforces "Fail-Closed" logic. The browser refuses to launch without a valid `Golden Template` JSON.
- **Dependency**: `browserforge` has been excised to prevent probabilistic entropy leakage.

### 2. Engine Hardening (C++ Layer)
- **Status**: PATCHED
- **Patches**:
  - `patches/lucid-navigator.patch`: Overrides `Navigator` properties via environment variables.
  - `patches/webgl-spoofing.patch`: Overrides WebGL Vendor/Renderer via `LUCID_WEBGL_VENDOR`.
  - `patches/font-hijacker.patch`: Overrides system fonts via `LUCID_FONT_LIST`.
- **Mechanism**: All overrides utilize `std::getenv` for binary-level interception, bypassing JS detection.

### 3. Genesis Ecosystem (`core/genesis_engine.py`)
- **Status**: INSTALLED
- **Function**: Orchestrates "Temporal Displacement" (Time Travel) using `libfaketime`.
- **Usage**:
  ```bash
  python -m core.genesis_engine
  ```
- **Phases**: Inception (T-90d), Warming (T-60d), Engagement (T-30d).

### 4. Forensic Injection (`modules/commerce_injector.py`)
- **Status**: INSTALLED
- **Function**: Injects "Trust Anchors" (e.g., Stripe cookies, Shopify tokens) using the "Double-Tap Protocol" (Write + Event Dispatch).

### 5. Sovereignty Layer (`docker-compose.yml`)
- **Status**: CONFIGURED
- **Services**:
  - `vtpm_emulator`: Virtual TPM 2.0 cluster for DBSC bypass.
  - `genesis_engine`: Containerized environment with `NET_ADMIN` caps for eBPF/XDP.

### 6. Orchestration (`lucid_launcher.py`)
- **Status**: INSTALLED
- **Usage**:
  ```bash
  python dashboard/main.py list
  python dashboard/main.py warmup --profile "profile_001"
  python dashboard/main.py proxy --profile "profile_001" --url "socks5://user:pass@host:port"

Note: Prefer using `python start_empire.py` to launch the dashboard (it will ensure environment dependencies and provide a verified entry point).  ```

### 7. Biometric Humanization (`modules/biometric_mimicry.py`)
- **Status**: ACTIVE
- **Features**:
  - **GAN Trajectories**: Generates mouse paths using `ghost_motor_v5.onnx`.
  - **Keystroke Dynamics**: Simulates "Flight Time," "Key Overlap," and error correction (typos).

### 8. Verification & Transit
- **Grand Verification**:
  ```bash
  python scripts/LUCID_GRAND_VERIFICATION.py
  ```
  Verifies WebGL spoofing, Navigator integrity, and Font blindness.
- **State Transit**:
  ```bash
  python scripts/package_ghost.py
  ```
  Packages the full profile (browsing history + vTPM state) into a portable `.lxc` container.

### 9. Commercial Dashboard (GUI)
- **Status**: ACTIVE
- **Components**:
  - `lucid_manager.py`: Main GUI control panel.
  - `core/profile_store.py`: Identity persistence layer.
- **Usage**:
  ```bash
  ./start_lucid.sh
  ```
  Launches the "Ops Commander" interface to create profiles, set proxies, and manage the Genesis lifecycle.

## Build Instructions
The project uses a Hybrid Build Pipeline.
1. **Linux**: Manages orchestration, Genesis Engine, and source patching.
2. **Windows**: Compiles the final `lucid.exe` binary via GitHub Actions (`.github/workflows/lucid-build.yml`).

## Operational Directives
*   **Always** use a Golden Template.
*   **Never** launch without the Genesis Engine warmup for high-value targets.
*   **Maintain** the `lucid_profile_data` directory structure.

**AUTHORITY**: PROMETHEUS-CORE | **STATUS**: OBLIVION_ACTIVE
