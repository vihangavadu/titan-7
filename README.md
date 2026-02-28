# TITAN X (V10.0) — HYPERSWITCH SINGULARITY

[![Version](https://img.shields.io/badge/version-10.0.0-blue.svg)]()
[![Core](https://img.shields.io/badge/core_modules-115-purple.svg)]()
[![Apps](https://img.shields.io/badge/GUI_apps-5-cyan.svg)]()
[![Platform](https://img.shields.io/badge/platform-Debian_12_%7C_Python_3.11-orange.svg)]()
[![Payment](https://img.shields.io/badge/payment-Hyperswitch_Orchestrator-green.svg)]()

> **Codename:** HYPERSWITCH SINGULARITY | **Version:** Titan X (10.0)  
> **Platform:** Debian 12 | Python 3.11 | Camoufox Browser | Ollama LLM | Hyperswitch Payment Orchestrator  
> **Major Upgrade:** Integrated Juspay Hyperswitch for intelligent payment routing, revenue recovery, and 50+ PSP connectors

---

## 🚀 What's New in Titan X

### Hyperswitch Payment Orchestration
- **Intelligent Routing**: Multi-Armed Bandit (MAB), least-cost, elimination, and contracts-based routing
- **Revenue Recovery**: Automated retry logic with smart fallback strategies
- **Unified API**: Single integration for 50+ payment processors (Stripe, Adyen, Braintree, PayPal, etc.)
- **PCI-Compliant Vault**: Secure card tokenization and storage
- **Cost Observability**: Real-time payment analytics and cost tracking
- **Cerberus AppX V2**: Rebuilt 7-tab GUI with Hyperswitch integration

### New Modules (115 Total)
- `cerberus_hyperswitch.py` — Hyperswitch REST API client with routing, vault, retry, and analytics
- `cerberus_bridge_api.py` — Enhanced with 10 new v2 endpoints for Hyperswitch operations

### Enhanced Applications
- **Cerberus AppX V2**: 7 tabs (VALIDATE, BATCH, ROUTING, VAULT, ANALYTICS, INTELLIGENCE, CONNECTORS)
- **Genesis AppX**: Enhanced profile forge with Hyperswitch payment validation
- **Titan Operations**: Integrated Hyperswitch payment orchestration

---

## Repository Structure

```
titan-x/
├── src/                         # All Titan source code
│   ├── core/                    # 115 core modules (112 Python + 3 C)
│   ├── apps/                    # 5 PyQt6 GUI applications + launcher
│   ├── extensions/              # Browser extensions (Ghost Motor, TX Monitor)
│   ├── profgen/                 # Firefox profile generator library
│   ├── testing/                 # Testing framework & adversary simulator
│   ├── bin/                     # System launch scripts
│   ├── lib/                     # C libraries (integrity shield, HW shield)
│   ├── vpn/                     # VPN relay & exit node configs
│   ├── branding/                # Desktop theme, logos, GRUB branding
│   ├── assets/                  # Motion data for liveness detection
│   ├── models/                  # ML model storage (LivePortrait, etc.)
│   ├── config/                  # titan.env, LLM config
│   └── build.sh                 # Titan build script
│
├── docs/                        # Documentation
│   ├── ARCHITECTURE.md          # System architecture (Six Rings)
│   ├── APP_ARCHITECTURE.md      # 5-app GUI structure
│   ├── MODULE_REFERENCE.md      # All 113 modules documented
│   ├── API_REFERENCE.md         # REST API (47 endpoints)
│   ├── OPERATOR_GUIDE.md        # How to operate Titan
│   ├── AUTOMATION_SYSTEM.md     # Autonomous engine docs
│   ├── BUILD_AND_DEPLOY_GUIDE.md
│   ├── MANUAL_DEPLOYMENT.md
│   ├── TROUBLESHOOTING.md
│   ├── CHANGELOG.md
│   └── research/                # 17 R&D papers
│
├── iso/                         # Debian live-build system
│   ├── auto/                    # lb auto scripts
│   ├── config/                  # Live-build config
│   │   ├── includes.chroot/     # System overlay (etc/, usr/)
│   │   ├── hooks/               # Build hooks
│   │   └── package-lists/       # APT package lists
│   ├── finalize_titan.sh        # Post-build finalization
│   └── templates/               # DKMS templates
│
├── scripts/                     # Build & deployment
│   ├── install/                 # Installation scripts
│   ├── vps/                     # VPS deployment & upgrade
│   ├── build_iso.sh             # ISO builder
│   ├── build_vps_image.sh       # VPS image builder
│   └── ...
│
├── tests/                       # Unit tests (pytest)
├── Dockerfile.build             # Docker build environment
├── pytest.ini                   # Test configuration
└── .github/workflows/           # CI/CD pipelines
```

---

## Core Modules (115)

### Payment Orchestration (NEW in Titan X)
| Module | Description |
|--------|-------------|
| `cerberus_hyperswitch.py` | Hyperswitch payment orchestrator integration (800 lines, 5 classes) |
| `cerberus_core.py` | Enhanced with Hyperswitch as primary validation backend |
| `cerberus_enhanced.py` | Integrated Hyperswitch analytics for data enrichment |
| `cerberus_bridge_api.py` | 10 new v2 REST endpoints for Hyperswitch operations |

**Hyperswitch Features:**
- **HyperswitchClient**: Payment creation, retrieval, confirmation, cancellation
- **HyperswitchRouter**: Intelligent routing strategies (MAB, least-cost, elimination, contracts)
- **HyperswitchVault**: PCI-compliant card tokenization and customer management
- **HyperswitchRetry**: Automated retry logic with smart fallback
- **HyperswitchAnalytics**: Real-time payment metrics and cost observability

---

## Legacy Core Modules (113)

### Identity & Profile Generation
| Module | Description |
|--------|-------------|
| `genesis_core.py` | Browser profile forge engine (aged Firefox profiles) |
| `advanced_profile_generator.py` | 900-day history synthesis with forensic accuracy |
| `forensic_synthesis_engine.py` | Cache2 binary mass, LSNG structured clone, DJB2 hashing |
| `profile_realism_engine.py` | Profile quality scoring & gap analysis |
| `persona_enrichment_engine.py` | Persona backstory generation |
| `purchase_history_engine.py` | Synthetic purchase trail injection |
| `indexeddb_lsng_synthesis.py` | IndexedDB & localStorage synthesis |
| `first_session_bias_eliminator.py` | Eliminates new-profile detection signals |

### Anti-Detection & Fingerprint
| Module | Description |
|--------|-------------|
| `fingerprint_injector.py` | Client Hints, WebRTC, media device spoofing |
| `canvas_subpixel_shim.py` | Canvas subpixel noise injection |
| `canvas_noise.py` | Canvas hash randomization |
| `audio_hardener.py` | AudioContext fingerprint spoofing |
| `font_sanitizer.py` | Font enumeration control |
| `webgl_angle.py` | WebGL renderer/vendor spoofing |
| `ghost_motor_v6.py` | Human-like mouse/keyboard behavioral engine |
| `tls_parrot.py` | TLS ClientHello mimicry (JA3/JA4) |
| `ja4_permutation_engine.py` | JA4 fingerprint permutation |
| `timezone_enforcer.py` | Timezone consistency enforcement |
| `location_spoofer_linux.py` | GPS coordinate spoofing with jitter |

### Network & Infrastructure
| Module | Description |
|--------|-------------|
| `integration_bridge.py` | Master orchestration bridge (all modules wired) |
| `network_shield.py` | eBPF TCP/IP fingerprint masquerade |
| `network_shield_loader.py` | Network shield kernel loader |
| `network_jitter.py` | Realistic network latency patterns |
| `proxy_manager.py` | Residential proxy pool management |
| `quic_proxy.py` | HTTP/3 QUIC proxy with TLS fingerprint |
| `lucid_vpn.py` | VLESS+Reality VPN with WireGuard |
| `mullvad_vpn.py` | Mullvad WireGuard integration |
| `cpuid_rdtsc_shield.py` | CPUID/RDTSC hypervisor concealment |
| `immutable_os.py` | Immutable filesystem protection |

### Transaction & Payment
| Module | Description |
|--------|-------------|
| `cerberus_core.py` | Card validation engine (BIN analysis, Luhn) |
| `cerberus_enhanced.py` | Enhanced card intelligence |
| `transaction_monitor.py` | Real-time TX capture & decline decoder |
| `three_ds_strategy.py` | 3DS bypass strategies per PSP |
| `tra_exemption_engine.py` | TRA exemption calculation |
| `issuer_algo_defense.py` | Issuer algorithm countermeasures |
| `payment_preflight.py` | Pre-checkout validation |
| `payment_sandbox_tester.py` | PSP sandbox testing |
| `payment_success_metrics.py` | Success rate analytics |
| `dynamic_data.py` | Dynamic checkout data generation |
| `form_autofill_injector.py` | Form field injection |

### AI & Intelligence
| Module | Description |
|--------|-------------|
| `ai_intelligence_engine.py` | Ollama-powered BIN & risk analysis |
| `cognitive_core.py` | Central AI coordination hub |
| `ollama_bridge.py` | Local LLM interface (Ollama) |
| `titan_agent_chain.py` | LangChain ReAct agent with tools |
| `titan_vector_memory.py` | ChromaDB persistent vector store |
| `titan_web_intel.py` | Multi-provider web search intelligence |
| `titan_ai_operations_guard.py` | 4-phase AI operations advisor |
| `titan_3ds_ai_exploits.py` | AI checkout co-pilot (browser extension) |
| `titan_realtime_copilot.py` | Real-time operation guidance |
| `titan_detection_analyzer.py` | Detection pattern analysis |
| `generate_trajectory_model.py` | Behavioral trajectory model training |

### Target & Recon
| Module | Description |
|--------|-------------|
| `target_discovery.py` | Automated target site discovery & probing |
| `target_intelligence.py` | Target site analysis & scoring |
| `titan_target_intel_v2.py` | 8-vector golden path scoring |
| `target_presets.py` | Pre-configured target profiles |
| `intel_monitor.py` | Continuous intelligence monitoring |
| `referrer_warmup.py` | Referrer chain warmup engine |

### KYC & Identity Verification
| Module | Description |
|--------|-------------|
| `kyc_core.py` | KYC bypass core engine |
| `kyc_enhanced.py` | Enhanced document synthesis |
| `kyc_voice_engine.py` | Voice verification engine |
| `verify_deep_identity.py` | Deep identity verification |
| `tof_depth_synthesis.py` | ToF depth map synthesis |
| `usb_peripheral_synth.py` | USB peripheral emulation |
| `waydroid_sync.py` | Android emulation sync |

### Automation & Orchestration
| Module | Description |
|--------|-------------|
| `titan_automation_orchestrator.py` | 12-phase E2E operation orchestrator |
| `titan_master_automation.py` | Master automation controller |
| `titan_autonomous_engine.py` | 24/7 self-improving operation loop |
| `titan_auto_patcher.py` | Automated parameter tuning |
| `titan_operation_logger.py` | Operation analytics & logging |
| `handover_protocol.py` | Session handover between modules |
| `preflight_validator.py` | Pre-launch environment validation |

### Security & Forensics
| Module | Description |
|--------|-------------|
| `kill_switch.py` | Emergency wipe & panic protocol |
| `forensic_cleaner.py` | Artifact removal |
| `forensic_monitor.py` | Real-time forensic monitoring |

### System & Services
| Module | Description |
|--------|-------------|
| `titan_api.py` | Flask REST API (47 endpoints) |
| `titan_services.py` | Service management daemon |
| `titan_env.py` | Configuration loader |
| `cockpit_daemon.py` | System health monitoring |
| `titan_master_verify.py` | System integrity verification |
| `titan_self_hosted_stack.py` | Self-hosted tool integrations |
| `bug_patch_bridge.py` | Bug reporting & patching bridge |
| `windows_font_provisioner.py` | Windows font installation |

---

## 6 GUI Applications

| App | File | Tabs | Purpose |
|-----|------|------|---------|
| **Cerberus AppX V2** | `app_cerberus.py` | 7 | VALIDATE, BATCH, ROUTING, VAULT, ANALYTICS, INTELLIGENCE, CONNECTORS |
| **Genesis AppX** | `app_genesis.py` | 4 | Profile Forge, Browser Launch, History, Settings |
| **Operations** | `titan_operations.py` | 5 | Target → Identity → Validate → Launch → Results |
| **Intelligence** | `titan_intelligence.py` | 5 | AI Copilot, 3DS Strategy, Detection, Recon, Memory |
| **Network** | `titan_network.py` | 4 | VPN, Network Shield, Forensic, Proxy/DNS |
| **KYC Studio** | `app_kyc.py` | 4 | Camera, Documents, Mobile Sync, Voice |
| **Admin** | `titan_admin.py` | 5 | Services, Tools, System, Automation, Config |
| **Launcher** | `titan_launcher.py` | — | Dashboard with health status & app cards |

### Cerberus AppX V2 — Payment Orchestration Hub
**7 Tabs:**
1. **VALIDATE** — Single card validation with Hyperswitch/Stripe/Braintree/Adyen
2. **BATCH** — Bulk card validation with rate limiting and export
3. **ROUTING** — Configure intelligent routing strategies (MAB, least-cost, elimination)
4. **VAULT** — Manage tokenized cards and customer profiles
5. **ANALYTICS** — Real-time payment metrics, success rates, cost analysis
6. **INTELLIGENCE** — BIN lookup, decline analytics, validation history
7. **CONNECTORS** — Manage PSP API keys and connector status (50+ supported)

---

## Quick Start

### Standard Deployment
```bash
# Clone
git clone https://github.com/malithwishwa02-dot/titan-7.git
cd titan-7

# Configure
cp src/config/titan.env.example src/config/titan.env
# Edit titan.env with your proxy credentials and API keys

# Deploy to VPS
bash scripts/vps/deploy_vps.sh

# Or build ISO
bash scripts/build_iso.sh
```

### Hyperswitch Deployment (Titan X Feature)
```bash
# Deploy Hyperswitch payment orchestrator
bash scripts/deploy_hyperswitch.sh

# This will:
# 1. Install Docker & Docker Compose
# 2. Deploy Hyperswitch stack (App Server, Control Center, PostgreSQL, Redis)
# 3. Configure environment variables in titan.env
# 4. Run health checks
# 5. Display Control Center URL (default: http://127.0.0.1:9000)

# Enable Hyperswitch in Titan
# Edit src/config/titan.env:
HYPERSWITCH_ENABLED=1
HYPERSWITCH_URL=http://127.0.0.1:8080
HYPERSWITCH_API_KEY=your_api_key_here
HYPERSWITCH_PUBLISHABLE_KEY=your_pk_here
HYPERSWITCH_ADMIN_KEY=your_admin_key_here

# Launch Cerberus AppX V2
python src/apps/app_cerberus.py
```

### Cerberus Bridge API (REST Endpoints)
```bash
# Start Cerberus Bridge API
python tools/cerberus_appx/cerberus_bridge_api.py

# API runs on http://127.0.0.1:36300
# V2 Endpoints (Hyperswitch):
# POST /api/v2/validate          - Validate card via Hyperswitch
# GET  /api/v2/connectors         - List available PSP connectors
# POST /api/v2/routing/create     - Create routing algorithm
# GET  /api/v2/routing/list       - List routing algorithms
# POST /api/v2/vault/tokenize     - Tokenize card in vault
# GET  /api/v2/vault/customers    - List vault customers
# GET  /api/v2/analytics/metrics  - Get payment analytics
# POST /api/v2/retry/configure    - Configure retry logic
# GET  /api/v2/retry/status       - Get retry status
# GET  /api/v2/health             - Hyperswitch health check
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [Architecture](docs/ARCHITECTURE.md) | Six-ring system architecture |
| [Module Reference](docs/MODULE_REFERENCE.md) | All 113 modules with API details |
| [API Reference](docs/API_REFERENCE.md) | REST API endpoints |
| [Operator Guide](docs/OPERATOR_GUIDE.md) | How to run operations |
| [Automation](docs/AUTOMATION_SYSTEM.md) | Autonomous engine & orchestrator |
| [Build & Deploy](docs/BUILD_AND_DEPLOY_GUIDE.md) | ISO build & VPS deployment |
| [Troubleshooting](docs/TROUBLESHOOTING.md) | Common issues & fixes |
| [Changelog](docs/CHANGELOG.md) | Version history |
| [Technical Report](docs/TITAN_OS_TECHNICAL_REPORT.md) | Deep technical analysis |

---

## Tech Stack

- **OS:** Debian 12 (custom live-build ISO)
- **Runtime:** Python 3.11
- **Browser:** Camoufox (anti-detection Firefox fork)
- **GUI:** PyQt6
- **Payment:** Hyperswitch (open-source payment orchestrator)
- **AI:** Ollama (mistral:7b, qwen2.5:7b, deepseek-r1:8b)
- **Vector DB:** ChromaDB
- **Network:** eBPF/XDP, WireGuard, VLESS+Reality
- **Kernel:** Custom modules (titan_hw.ko, network_shield)
- **Infrastructure:** Docker, PostgreSQL, Redis

### Hyperswitch Stack
- **App Server:** Rust-based payment orchestrator (port 8080)
- **Control Center:** React dashboard (port 9000)
- **Database:** PostgreSQL 14
- **Cache:** Redis 7
- **Connectors:** 50+ PSPs (Stripe, Adyen, Braintree, PayPal, Checkout.com, etc.)

---

## Environment Variables (Hyperswitch)

Add to `src/config/titan.env`:

```bash
# Hyperswitch Configuration
HYPERSWITCH_ENABLED=1                                    # Enable Hyperswitch (0=disabled, 1=enabled)
HYPERSWITCH_URL=http://127.0.0.1:8080                   # Hyperswitch API URL
HYPERSWITCH_API_KEY=your_api_key_here                   # Merchant API key
HYPERSWITCH_PUBLISHABLE_KEY=your_pk_here                # Publishable key for client-side
HYPERSWITCH_ADMIN_KEY=your_admin_key_here               # Admin API key
HYPERSWITCH_CONTROL_CENTER_URL=http://127.0.0.1:9000    # Control Center dashboard
```

---

## Architecture: Hyperswitch Integration

```
┌─────────────────────────────────────────────────────────────────┐
│                     Cerberus AppX V2 (PyQt6)                    │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────────┐   │
│  │ VALIDATE │  BATCH   │ ROUTING  │  VAULT   │  ANALYTICS   │   │
│  └──────────┴──────────┴──────────┴──────────┴──────────────┘   │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              cerberus_hyperswitch.py (Core Module)              │
│  ┌──────────────┬──────────────┬──────────────┬──────────────┐  │
│  │ Client       │ Router       │ Vault        │ Analytics    │  │
│  │ (Payments)   │ (Strategies) │ (Tokens)     │ (Metrics)    │  │
│  └──────────────┴──────────────┴──────────────┴──────────────┘  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Hyperswitch App Server (Rust)                  │
│                         Port 8080                               │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Intelligent Routing Engine (MAB, Least-Cost, etc.)     │   │
│  │  Retry Logic & Revenue Recovery                         │   │
│  │  PCI-Compliant Vault                                    │   │
│  │  Cost Observability & Analytics                         │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┬──────────────┐
         ▼               ▼               ▼              ▼
    ┌────────┐      ┌────────┐      ┌────────┐    ┌────────┐
    │ Stripe │      │ Adyen  │      │Braintree│    │ +47    │
    │        │      │        │      │        │    │ more   │
    └────────┘      └────────┘      └────────┘    └────────┘
```

### Payment Flow (Hyperswitch Mode)
1. **User Input** → Cerberus AppX V2 (VALIDATE tab)
2. **Validation** → `cerberus_hyperswitch.py` creates payment
3. **Routing** → Hyperswitch applies intelligent routing algorithm
4. **PSP Selection** → Routes to optimal PSP (Stripe/Adyen/Braintree)
5. **Retry Logic** → Auto-retry on failure with different PSP
6. **Response** → Return validation result to GUI
7. **Analytics** → Track success rate, cost, latency
