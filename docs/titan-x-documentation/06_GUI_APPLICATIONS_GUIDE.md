# 06 — GUI Applications Guide

**11 PyQt6 Desktop Applications — 42 Tabs — 362 Core Module Imports**

The Titan X GUI is a 3×3+2 application grid launched from the Titan Launcher. Each app is a standalone PyQt6 window with dark theme, color-coded accent, cross-app session sharing, and graceful fallback when core modules are unavailable. All apps communicate via `titan_session.py` (JSON + Redis pub/sub).

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                    TITAN X LAUNCHER                               │
│                   (titan_launcher.py)                              │
│                                                                   │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐             │
│  │  Operations   │ │ Intelligence │ │   Network    │  Row 1      │
│  │   #00d4ff     │ │   #a855f7    │ │   #22c55e    │             │
│  └──────────────┘ └──────────────┘ └──────────────┘             │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐             │
│  │  KYC Studio   │ │    Admin     │ │   Settings   │  Row 2      │
│  │   #f97316     │ │   #f59e0b    │ │   #6366f1    │             │
│  └──────────────┘ └──────────────┘ └──────────────┘             │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐             │
│  │ Profile Forge │ │Card Validator│ │Browser Launch│  Row 3      │
│  │   #06b6d4     │ │   #eab308    │ │   #22c55e    │             │
│  └──────────────┘ └──────────────┘ └──────────────┘             │
│  ┌──────────────┐ ┌──────────────┐                               │
│  │ Genesis AppX  │ │ Bug Reporter │                  Row 4       │
│  │   #10b981     │ │   #5588ff    │                               │
│  └──────────────┘ └──────────────┘                               │
└──────────────────────────────────────────────────────────────────┘
```

### Cross-App Session System

All apps share state via `titan_session.py`:
- **Backend**: JSON file + Redis pub/sub (real-time sync)
- **Functions**: `get_session()`, `save_session()`, `update_session()`, `add_operation_result()`
- **Shared data**: Selected target, active card, current profile, proxy status, VPN state, operation results
- **Connected**: 7 of 11 apps (Operations, Intelligence, Network, KYC, Profile Forge, Card Validator, Browser Launch)

### Theme System

All apps use `titan_theme.py` for consistent styling:
- **Primary BG**: `#0a0e17` (near-black)
- **Card BG**: `#111827` (dark gray)
- **Text**: `#e2e8f0` (light gray)
- **Dim text**: `#64748b` (muted)
- **Status colors**: Green `#22c55e`, Yellow `#eab308`, Red `#ef4444`, Orange `#f97316`
- **Font**: Monospace for data displays, sans-serif for labels
- **Responsive**: Scales from 800×480 (mobile) to 3840×2160 (4K)

---

## App 0: Titan Launcher

**File**: `titan_launcher.py` (636 lines)
**Accent**: `#00d4ff` (Cyan)
**Purpose**: Entry point — 3×3+2 app grid with system health indicators

### Features

| Feature | Description |
|---------|-------------|
| **App Grid** | 11 clickable cards with icon, title, description, and status indicator |
| **Health Dots** | Green/Yellow/Red dot per app showing module availability |
| **System Bar** | Kill switch button, Mullvad VPN status, Ollama AI status, service count |
| **First Run Wizard** | Launches `titan_first_run_wizard.py` on first boot |
| **Responsive Layout** | Adaptive grid columns based on window width |

### Core Module Imports (5)

| Module | Used For |
|--------|----------|
| `kill_switch` | Emergency panic button in header |
| `mullvad_vpn` | VPN connection status indicator |
| `ollama_bridge` | AI model status indicator |
| `titan_services` | Background service count |
| `titan_env` | Configuration loading |

### Startup Flow
1. Check `~/.titan/first_run_done` flag
2. If first run → launch `titan_first_run_wizard.py`
3. Load session state from `titan_session.py`
4. Render 11 app cards with health status
5. Start QTimer for periodic health refresh

---

## App 1: Operations Center

**File**: `titan_operations.py` (1,834 lines)
**Accent**: `#00d4ff` (Cyan)
**Purpose**: Primary workflow app — 90% of daily operator tasks

### 5 Tabs

#### Tab 1: TARGET
Select merchant site, configure proxy, and set geographic targeting.

| User Input | Widget | Core Module |
|------------|--------|-------------|
| Target Site | QComboBox (50+ presets) | `target_presets`, `target_discovery` |
| Category | QComboBox (electronics, gaming, fashion, etc.) | `target_intelligence` |
| Proxy Provider | QComboBox (Bright Data, SOAX, IPRoyal, Webshare) | `proxy_manager` |
| Country | QComboBox (US, UK, DE, FR, CA, AU, +) | `location_spoofer_linux` |
| City | QComboBox (dynamic based on country) | `location_spoofer_linux` |
| Custom Target URL | QLineEdit | `target_discovery` (auto-probe) |

**Actions**: "Analyze Target" (runs target_intelligence), "Auto-Discover" (scans for new low-friction sites)

#### Tab 2: IDENTITY
Build synthetic persona with demographic consistency.

| User Input | Widget | Core Module |
|------------|--------|-------------|
| First Name | QLineEdit (auto-generated or manual) | `advanced_profile_generator` |
| Last Name | QLineEdit | `advanced_profile_generator` |
| Date of Birth | QLineEdit (MM/DD/YYYY) | `advanced_profile_generator` |
| Address | QLineEdit (street, city, state, zip) | `advanced_profile_generator` |
| Email | QLineEdit | `advanced_profile_generator` |
| Phone | QLineEdit | `advanced_profile_generator` |
| SSN (last 4) | QLineEdit | `advanced_profile_generator` |
| Card Number | QLineEdit | Auto-fills to VALIDATE tab |
| Card Expiry | QLineEdit (MM/YY) | — |
| Card CVV | QLineEdit | — |

**Actions**: "Generate Identity" (creates full persona), "Import from Clipboard", "Save to Session"

#### Tab 3: VALIDATE
Card validation, BIN intelligence, and preflight system check.

| User Input | Widget | Core Module |
|------------|--------|-------------|
| Card Number | QLineEdit (auto-filled from IDENTITY) | `cerberus_core` |
| BIN Lookup | QPushButton | `cerberus_enhanced` (BIN scoring) |
| AVS Check | QPushButton | `cerberus_enhanced` (local AVS pre-check) |
| Preflight Check | QPushButton | `preflight_validator`, `verify_deep_identity` |

**Outputs**: LIVE/DEAD/RISKY status, BIN grade (A–F), issuer name, card type, 3DS requirement, AVS support, target compatibility score

#### Tab 4: FORGE & LAUNCH
Generate browser profile and launch Camoufox.

| User Input | Widget | Core Module |
|------------|--------|-------------|
| Profile Type | QComboBox (Firefox/Chromium/Anti-detect Export) | `genesis_core`, `oblivion_forge`, `chromium_constructor` |
| Browser Target | QComboBox (Chrome 133, Firefox 134, Edge 133, Safari 18) | `fingerprint_injector` |
| OS Target | QComboBox (Windows 10, Windows 11, macOS Sequoia) | `fingerprint_injector` |
| GPU Profile | QComboBox (8 GPU options) | `webgl_angle` |
| Hardware Profile | QComboBox (Dell, Lenovo, HP, ASUS) | `cpuid_rdtsc_shield` |
| Warmup Sites | QSpinBox (0–20) | `referrer_warmup` |

**Progress**: 9-stage progress bar (Identity → Persona → History → Cache → Cookies → Storage → Autofill → Purchase → Score)
**Actions**: "Forge Profile" (starts genesis pipeline), "Launch Browser" (opens Camoufox with profile)

#### Tab 5: RESULTS
Operation history, success metrics, and decline analysis.

| Display | Widget | Core Module |
|---------|--------|-------------|
| Operation History | QTableWidget | `titan_operation_logger` |
| Success Rate | QLabel (%) | `payment_success_metrics` |
| Decline Decoder | QTextEdit | `transaction_monitor` |
| GAMP Verification | QPushButton | `gamp_triangulation_v2` |

### Core Module Count: 51

---

## App 2: Intelligence Center

**File**: `titan_intelligence.py` (1,925 lines)
**Accent**: `#a855f7` (Purple)
**Purpose**: AI-powered analysis, strategy planning, and operational intelligence

### 5 Tabs

#### Tab 1: AI COPILOT
Real-time AI guidance during operations.

| User Input | Widget | Core Module |
|------------|--------|-------------|
| Question | QTextEdit (free-form) | `titan_realtime_copilot` |
| Context | QComboBox (operation, card, target, detection) | `ai_intelligence_engine` |
| Model | QComboBox (titan-analyst, titan-strategist, titan-fast) | `ollama_bridge` |

**Actions**: "Ask AI", "Analyze BIN", "Profile Audit", "Suggest Strategy"

#### Tab 2: 3DS STRATEGY
3DS bypass planning and TRA exemption engineering.

| User Input | Widget | Core Module |
|------------|--------|-------------|
| Target PSP | QComboBox (Stripe, Adyen, Braintree, etc.) | `three_ds_strategy` |
| Card BIN | QLineEdit (first 6–8 digits) | `cerberus_enhanced` |
| Amount | QDoubleSpinBox | `tra_exemption_engine` |
| Issuer | QComboBox (auto-detected from BIN) | `issuer_algo_defense` |

**Outputs**: Recommended bypass path, TRA exemption eligibility, amount optimization, issuer behavior profile

#### Tab 3: DETECTION
Decline analysis, root cause identification, and AI operations guard.

| Feature | Core Module |
|---------|-------------|
| Decline Root Cause | `titan_detection_analyzer` |
| Detection Pattern Analysis | `titan_detection_lab` |
| AI Operations Guard | `titan_ai_operations_guard` |
| Fingerprint Coherence | `ai_intelligence_engine` |

#### Tab 4: RECON
Target reconnaissance and antifraud system profiling.

| User Input | Widget | Core Module |
|------------|--------|-------------|
| Target URL | QLineEdit | `target_intelligence` |
| TLS Analysis | QPushButton | `ja4_permutation_engine`, `tls_parrot` |
| Antifraud Detection | QComboBox (21 platforms) | `target_intelligence` |

#### Tab 5: MEMORY
Vector knowledge base and web intelligence.

| Feature | Core Module |
|---------|-------------|
| Semantic Search | `titan_vector_memory` |
| Web Intelligence | `titan_web_intel` |
| Operation History | `titan_operation_logger` |
| ONNX Fast Query | `titan_onnx_engine` |

### Core Module Count: 21

---

## App 3: Network Center

**File**: `titan_network.py` (lines vary)
**Accent**: `#22c55e` (Green)
**Purpose**: VPN, proxy, network forensics, and IP verification

### 5 Tabs

#### Tab 1: MULLVAD VPN
WireGuard VPN connection management.

| User Input | Widget | Core Module |
|------------|--------|-------------|
| Server Location | QComboBox (country/city) | `mullvad_vpn` |
| Protocol | QComboBox (WireGuard, OpenVPN) | `mullvad_vpn` |
| Multi-hop | QCheckBox | `mullvad_vpn` |
| DAITA | QCheckBox (AI traffic analysis defense) | `mullvad_vpn` |

**Actions**: "Connect", "Disconnect", "Check IP", "Rotate Server"

#### Tab 2: NETWORK SHIELD
eBPF/XDP TCP/IP header rewriting control.

| Feature | Core Module |
|---------|-------------|
| Shield Status | `network_shield_loader` |
| TCP Parameter Override | `network_shield` |
| OS Fingerprint Test | `network_shield` |

#### Tab 3: FORENSIC
Real-time system forensic monitoring.

| Feature | Core Module |
|---------|-------------|
| Forensic Scan | `forensic_monitor` |
| Artifact Cleanup | `forensic_cleaner` |
| Forensic Dashboard | `forensic_alignment` |

#### Tab 4: PROXY / DNS
Residential proxy and DNS management.

| User Input | Widget | Core Module |
|------------|--------|-------------|
| Proxy Provider | QComboBox | `proxy_manager` |
| QUIC Proxy | QCheckBox | `quic_proxy` |
| Location Spoof | QComboBox (city) | `location_spoofer_linux` |
| DNS Config | QComboBox | `network_jitter` |

#### Tab 5: VLESS / LUCID
Self-hosted VLESS Reality VPN management.

| User Input | Widget | Core Module |
|------------|--------|-------------|
| Server | QLineEdit | `lucid_vpn` |
| SNI | QComboBox (8 rotation targets) | `lucid_vpn` |
| Protocol | QComboBox (VLESS, Trojan) | `lucid_vpn` |

### Core Module Count: 22

---

## App 4: KYC Studio

**File**: `app_kyc.py` (1,896 lines)
**Accent**: `#f97316` (Orange)
**Purpose**: Identity verification bypass — camera, documents, voice

### 4 Tabs

#### Tab 1: CAMERA
Virtual camera control with liveness motion support.

| User Input | Widget | Core Module |
|------------|--------|-------------|
| Source Image | QFileDialog (face photo) | `kyc_core` |
| Motion Type | QComboBox (17 motions) | `kyc_core` |
| Head Rotation | QSlider (-45° to +45°) | `kyc_core` |
| Expression Intensity | QSlider (0–100%) | `kyc_core` |
| Blink Frequency | QSpinBox (0–30 per min) | `kyc_core` |
| Camera Device | QComboBox (/dev/video0–9) | `kyc_core` |

**17 Motions**: neutral, blink, blink_twice, smile, head_left, head_right, nod, tilt, look_up, look_down, open_mouth, raise_eyebrows, frown, close_eyes, wink_left, wink_right, speak_phrase

**Actions**: "Start Stream", "Stop Stream", "Preview", "Record"

#### Tab 2: DOCUMENTS
Identity document generation and injection.

| User Input | Widget | Core Module |
|------------|--------|-------------|
| Document Type | QComboBox (5 types) | `kyc_enhanced` |
| KYC Provider | QComboBox (8 providers) | `kyc_enhanced` |
| Country | QComboBox | `kyc_enhanced` |
| Personal Info | QFormLayout (name, DOB, address) | `kyc_enhanced` |

**5 Document Types**: Driver's license, passport, state ID, national ID, residence permit
**8 Providers**: Jumio, Onfido, Veriff, SumSub, Persona, Stripe Identity, Plaid IDV, Au10tix

#### Tab 3: VOICE
Text-to-speech for video+voice KYC challenges.

| User Input | Widget | Core Module |
|------------|--------|-------------|
| Text Phrase | QLineEdit (spoken phrase) | `kyc_voice_engine` |
| TTS Backend | QComboBox (Coqui, Piper, espeak, gTTS) | `kyc_voice_engine` |
| Accent | QComboBox (8 options) | `kyc_voice_engine` |
| Age Range | QComboBox (young, middle, senior) | `kyc_voice_engine` |

**Actions**: "Generate Audio", "Play Preview", "Export WAV"

#### Tab 4: MOBILE SYNC
Cross-device Waydroid Android synchronization.

| Feature | Core Module |
|---------|-------------|
| Android Container | `waydroid_sync` |
| Device Identity | `waydroid_sync` (Pixel 7 preset) |
| Cross-device Sync | `waydroid_sync` |
| Deep Identity | `verify_deep_identity` |
| 3D Depth | `tof_depth_synthesis` |

### Core Module Count: 13

---

## App 5: Admin Panel

**File**: `titan_admin.py` (lines vary)
**Accent**: `#f59e0b` (Amber)
**Purpose**: System management, service health, automation rules

### 5 Tabs

#### Tab 1: SERVICES
Background service monitoring and control.

| Feature | Core Module |
|---------|-------------|
| Service Status Table | `titan_services` |
| Redis Status | `titan_self_hosted_stack` |
| Ollama Status | `ollama_bridge` |
| Xray Status | `titan_self_hosted_stack` |
| ntfy Status | `titan_self_hosted_stack` |

**Actions**: "Start All", "Stop All", "Restart Service", "Health Check"

#### Tab 2: TOOLS
Utility tools and diagnostics.

| Feature | Core Module |
|---------|-------------|
| Module Status | `integration_bridge` (69 subsystems) |
| Profile Isolation | `profile_isolation` |
| Detection Lab | `titan_detection_lab` |
| Forensic Monitor | `forensic_monitor` |

#### Tab 3: SYSTEM
System health and resource monitoring.

| Feature | Core Module |
|---------|-------------|
| CPU/RAM/Disk | System metrics |
| Kill Switch | `kill_switch` |
| Immutable OS | `immutable_os` |
| Bug Patch Bridge | `bug_patch_bridge` |

#### Tab 4: AUTOMATION
Automated workflow rules and scheduling.

| Feature | Core Module |
|---------|-------------|
| Auto-Discovery Schedule | `titan_services` |
| Auto-Patcher | `titan_auto_patcher` |
| Feedback Loop Config | `titan_services` |
| Orchestrator Config | `titan_automation_orchestrator` |

#### Tab 5: CONFIG
Configuration editor for titan.env and llm_config.json.

| Feature | Core Module |
|---------|-------------|
| Config Editor | `titan_env` |
| LLM Config | `ollama_bridge` |
| MCP Interface | `mcp_interface` |

### Core Module Count: 24

---

## App 6: Settings

**File**: `app_settings.py` (lines vary)
**Accent**: `#6366f1` (Indigo)
**Purpose**: First-time setup and ongoing configuration

### 6 Tabs

#### Tab 1: VPN
Mullvad VPN account and connection settings.

| User Input | Widget |
|------------|--------|
| Account Number | QLineEdit (masked) |
| Default Server | QComboBox |
| Auto-connect | QCheckBox |
| Kill Switch on Disconnect | QCheckBox |

#### Tab 2: AI
Ollama model configuration and ONNX engine settings.

| User Input | Widget |
|------------|--------|
| Ollama URL | QLineEdit (default: http://localhost:11434) |
| Default Model | QComboBox (6 models) |
| ONNX Model Path | QLineEdit |
| Temperature | QDoubleSpinBox (0.0–2.0) |

#### Tab 3: SERVICES
Redis, Xray, ntfy service configuration.

| User Input | Widget |
|------------|--------|
| Redis URL | QLineEdit (default: localhost:6379) |
| Xray Config Path | QLineEdit |
| ntfy Server URL | QLineEdit |
| ntfy Topic | QLineEdit |

#### Tab 4: BROWSER
Camoufox and browser engine settings.

| User Input | Widget |
|------------|--------|
| Camoufox Path | QLineEdit |
| Default Profile Type | QComboBox |
| User Agent Override | QLineEdit |
| Launch Flags | QTextEdit |

#### Tab 5: API KEYS
External service API key management.

| User Input | Widget |
|------------|--------|
| Bright Data API | QLineEdit (masked) |
| SOAX API | QLineEdit (masked) |
| IPRoyal API | QLineEdit (masked) |
| OpenAI API | QLineEdit (masked) |
| Groq API | QLineEdit (masked) |
| OpenRouter API | QLineEdit (masked) |

#### Tab 6: SYSTEM
Global system preferences.

| User Input | Widget |
|------------|--------|
| Theme | QComboBox (Dark/Light) |
| Default Country | QComboBox |
| Log Level | QComboBox (DEBUG/INFO/WARNING/ERROR) |
| Export Config | QPushButton |

### Core Module Count: 2

---

## App 7: Profile Forge

**File**: `app_profile_forge.py` (lines vary)
**Accent**: `#06b6d4` (Cyan)
**Purpose**: Focused profile generation with 9-stage pipeline visualization

### 3 Tabs

#### Tab 1: IDENTITY
Persona creation with demographic consistency.

| User Input | Widget | Core Module |
|------------|--------|-------------|
| Full Name | QLineEdit | `advanced_profile_generator` |
| DOB | QLineEdit | `advanced_profile_generator` |
| Address | QFormLayout | `advanced_profile_generator` |
| Email | QLineEdit | `advanced_profile_generator` |
| Persona Archetype | QComboBox (Casual, Gamer, Professional, Student) | `persona_enrichment_engine` |

#### Tab 2: FORGE
9-stage profile forge pipeline with real-time progress.

| Stage | Description | Core Module |
|-------|-------------|-------------|
| 1. Identity | Generate persona data | `advanced_profile_generator` |
| 2. Persona | Enrich with demographics | `persona_enrichment_engine` |
| 3. History | 1500+ URLs, 900+ days | `genesis_core` |
| 4. Cache | 350–500MB binary cache | `genesis_core` |
| 5. Cookies | AES-256 encrypted DB | `chromium_cookie_engine`, `cookie_forge` |
| 6. Storage | IndexedDB + localStorage | `indexeddb_lsng_synthesis`, `leveldb_writer` |
| 7. Autofill | Form autofill data | `form_autofill_injector` |
| 8. Purchase | Commerce history | `purchase_history_engine` |
| 9. Score | Quality validation | `profile_realism_engine` |

#### Tab 3: PROFILES
Profile library with import/export.

| Feature | Core Module |
|---------|-------------|
| Profile List | `genesis_core` |
| Quality Score | `profile_realism_engine` |
| Export (ML6/GoLogin/Dolphin) | `antidetect_importer` |
| Import | `antidetect_importer` |
| Delete (secure wipe) | `profile_burner` |
| Forensic Synthesis | `forensic_synthesis_engine` |

### Core Module Count: 14

---

## App 8: Card Validator

**File**: `app_card_validator.py` (lines vary)
**Accent**: `#eab308` (Yellow)
**Purpose**: Card validation, BIN intelligence, and quality grading

### 3 Tabs

#### Tab 1: VALIDATE
Card validation with zero-touch SetupIntent checks.

| User Input | Widget | Core Module |
|------------|--------|-------------|
| Card Number | QLineEdit | `cerberus_core` |
| Expiry | QLineEdit (MM/YY) | `cerberus_core` |
| CVV | QLineEdit | `cerberus_core` |
| Billing Zip | QLineEdit | `cerberus_enhanced` (AVS) |

**Output**: LIVE ✅ / DEAD ❌ / RISKY ⚠️ / UNKNOWN ❓ with decline intelligence

#### Tab 2: INTELLIGENCE
BIN scoring and issuer behavior profiles.

| Feature | Core Module |
|---------|-------------|
| BIN Scoring (A–F) | `cerberus_enhanced` |
| Issuer Profile | `issuer_algo_defense` |
| Target Compatibility | `cerberus_enhanced` |
| Amount Optimization | `issuer_algo_defense` |
| Card Cooling Timer | `cerberus_core` |

#### Tab 3: HISTORY
Validation history and success analytics.

| Feature | Core Module |
|---------|-------------|
| Validation Log | `titan_operation_logger` |
| Success Rate by BIN | `payment_success_metrics` |
| Decline Patterns | `transaction_monitor` |

### Core Module Count: 8

---

## App 9: Browser Launch

**File**: `app_browser_launch.py` (647 lines)
**Accent**: `#22c55e` (Green)
**Purpose**: Profile launch, live transaction monitoring, manual handover

### 3 Tabs

#### Tab 1: LAUNCH
Select profile and run preflight before launching browser.

| User Input | Widget | Core Module |
|------------|--------|-------------|
| Profile | QComboBox (generated profiles) | `genesis_core` |
| Browser | QComboBox (Camoufox, Chrome) | `integration_bridge` |
| Target | QComboBox (from session) | `target_presets` |
| Preflight Check | QPushButton | `preflight_validator`, `titan_master_verify` |

**Preflight**: L0 Kernel → L1 Network → L2 Environment → L3 Identity (all must pass)
**Actions**: "Run Preflight", "Launch Browser"

#### Tab 2: MONITOR
Live transaction monitoring and decline decoding.

| Feature | Core Module |
|---------|-------------|
| Live TX Feed | `transaction_monitor` |
| Decline Decoder | `transaction_monitor` |
| Payment Metrics | `payment_success_metrics` |
| AI Copilot Alerts | `titan_realtime_copilot` |

#### Tab 3: HANDOVER
Automated-to-manual transition protocol.

| Feature | Core Module |
|---------|-------------|
| Handover Protocol | `handover_protocol` |
| Operator Playbook | Generated per-operation |
| Post-Checkout Guide | Checklist UI |
| Kill Switch | `kill_switch` |

### Core Module Count: 11

---

## App 10: Genesis AppX

**File**: `tools/multilogin6/genesis_appx/launch_genesis_appx.sh`
**Accent**: `#10b981` (Emerald)
**Purpose**: MultiLogin 6 browser manager with Genesis Engine backend

### Architecture

Genesis AppX is a patched MultiLogin 6 Electron shell where:
- **Auth** is bypassed (always authenticated)
- **API calls** are redirected to local Genesis Bridge API (port 36200)
- **Branding** is changed from MultiLogin to Genesis AppX
- **Color scheme** is changed from blue to emerald green

### Components

| Component | File | Purpose |
|-----------|------|---------|
| Bridge API | `genesis_bridge_api.py` | Flask REST API on :36200 backing ML6 endpoints |
| Launcher | `launch_genesis_appx.sh` | Starts bridge + Electron app |
| Patcher | `patch_selective.py` | ASAR extraction and patching (13 files) |
| Deployer | `deploy_genesis_appx.sh` | Full installation from ML6 .deb |

### Bridge API Endpoints

| Endpoint | Description |
|----------|-------------|
| `/api/v2/profile` | Profile CRUD (backed by genesis_core) |
| `/api/v2/profile/start` | Launch browser with profile |
| `/api/v2/cookie/import` | Import cookies from external source |
| `/genesis/forge` | Titan-specific: Forge profile for target |
| `/genesis/targets` | List available target presets |
| `/genesis/archetypes` | Persona archetype library |
| `/genesis/validate` | Card validation via cerberus_core |

---

## App 11: Bug Reporter

**File**: `app_bug_reporter.py` (lines vary)
**Accent**: `#5588ff` (Blue)
**Purpose**: Issue reporting, auto-patching, and fix tracking

### Features

| Feature | Core Module |
|---------|-------------|
| Report Bug | `bug_patch_bridge` |
| Auto-Patch | `titan_auto_patcher` |
| Known Issues DB | `bug_patch_bridge` |
| Fix History | `titan_operation_logger` |
| Decline Pattern Logger | `transaction_monitor` |

---

## Supporting GUI Components

### `titan_theme.py`
Centralized theme constants and helper functions:
- `THEME` dataclass with all color constants
- `apply_titan_theme(app)` — applies dark palette to QApplication
- `make_tab_style(accent)` — generates QTabWidget stylesheet
- `make_btn(text, accent)` — styled QPushButton factory
- `make_mono_display()` — monospace QTextEdit factory
- `status_dot(color)` — colored status indicator widget

### `titan_splash.py`
Animated splash screen with progress bar shown during app startup.

### `titan_first_run_wizard.py`
Step-by-step setup wizard for new installations:
1. Welcome and system requirements check
2. VPN configuration (Mullvad account)
3. AI model download (Ollama models)
4. Proxy provider API keys
5. Browser engine selection
6. System verification and first preflight

### `titan_icon.py`
SVG icon generator for app launcher cards.

### `titan_enterprise_theme.py`
Alternative enterprise theme (lighter colors, corporate branding).

### `forensic_widget.py`
Reusable forensic monitoring widget embedded in Network Center.

### `launch_forensic_monitor.py`
Standalone forensic monitor launcher (for headless/terminal use).

### `app_cerberus.py`
Cerberus payment terminal standalone app (legacy).

---

## Import Statistics

| Metric | Value |
|--------|-------|
| Total GUI apps | 11 (9 PyQt6 + 1 Electron + 1 hybrid) |
| Total tabs | 42 |
| Total core imports | 362 |
| Broken imports | 0 |
| Core modules wired to GUI | 107/110 (97%) |
| Unwired (server-only) | `smoke_test_v91`, `verify_sync`, `titan_webhook_integrations` |
| Session-connected apps | 7 |

### Module Wiring by App

| App | Core Modules | Workers |
|-----|-------------|---------|
| Launcher | 5 | — |
| Operations | 51 | ValidateWorker, ForgeWorker |
| Intelligence | 21 | AIQueryWorker, ReconWorker |
| Network | 22 | VPNConnectWorker, ShieldAttachWorker |
| KYC Studio | 13 | StreamWorker |
| Admin | 24 | HealthCheckWorker |
| Settings | 2 | StatusWorker |
| Profile Forge | 14 | ForgeWorker |
| Card Validator | 8 | ValidateWorker |
| Browser Launch | 11 | PreflightWorker |
| Genesis AppX | N/A (bridge) | — |
| Bug Reporter | 4 | — |

---

## Typical Operator Workflow (GUI)

```
1. LAUNCHER → Click "Operations"
2. OPERATIONS/TARGET → Select target site + proxy + geo
3. OPERATIONS/IDENTITY → Generate or enter persona + card data
4. OPERATIONS/VALIDATE → Validate card → check BIN → run preflight
5. OPERATIONS/FORGE → Forge profile (9-stage pipeline, ~2 min)
6. BROWSER LAUNCH/LAUNCH → Run preflight checks → launch Camoufox
7. BROWSER LAUNCH/MONITOR → Watch live transactions
8. BROWSER LAUNCH/HANDOVER → Automation freezes → operator takes control
9. [MANUAL CHECKOUT] → Operator completes purchase
10. OPERATIONS/RESULTS → Review outcome → decline decoder if failed
```

**Alternative flows**:
- Use **Intelligence Center** to analyze a new target before adding it
- Use **KYC Studio** when target requires identity verification
- Use **Card Validator** for bulk card checking
- Use **Profile Forge** to pre-build profiles in batches
- Use **Network Center** to verify VPN/proxy before operations

---

*Document 06 of 11 — Titan X Documentation Suite — V10.0 — March 2026*
