# Changelog

All notable changes to Titan OS will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [10.0.0] - Titan X (HYPERSWITCH SINGULARITY) - 2025-02-26

### 🚀 Major Features

#### Hyperswitch Payment Orchestration Integration
- **NEW:** Integrated Juspay Hyperswitch open-source payment orchestrator
- **NEW:** `cerberus_hyperswitch.py` — 800-line core module with 5 classes
  - `HyperswitchClient` — Payment creation, retrieval, confirmation, cancellation
  - `HyperswitchRouter` — Intelligent routing (MAB, least-cost, elimination, contracts)
  - `HyperswitchVault` — PCI-compliant card tokenization and customer management
  - `HyperswitchRetry` — Automated retry logic with smart fallback
  - `HyperswitchAnalytics` — Real-time payment metrics and cost observability
- **NEW:** Support for 50+ payment processors via unified API
- **NEW:** Multi-Armed Bandit (MAB) routing for optimal PSP selection
- **NEW:** Revenue recovery with automated retry strategies
- **NEW:** PCI-compliant vault for secure card tokenization

#### Cerberus AppX V2 — Complete Rebuild
- **REBUILT:** `app_cerberus.py` — Upgraded from 4 tabs to 7 tabs
  1. **VALIDATE** — Single card validation with Hyperswitch/Stripe/Braintree/Adyen
  2. **BATCH** — Bulk card validation with rate limiting and export
  3. **ROUTING** — Configure intelligent routing strategies
  4. **VAULT** — Manage tokenized cards and customer profiles
  5. **ANALYTICS** — Real-time payment metrics and cost analysis
  6. **INTELLIGENCE** — BIN lookup, decline analytics, validation history
  7. **CONNECTORS** — Manage PSP API keys (50+ supported)
- **ENHANCED:** Real-time Hyperswitch status indicator in header
- **ENHANCED:** Gateway selector now includes Hyperswitch routing options

#### Cerberus Core Enhancements
- **ENHANCED:** `cerberus_core.py` — Hyperswitch as primary validation backend
  - New `_validate_hyperswitch()` method for Hyperswitch payment validation
  - Updated failover logic: Hyperswitch → Stripe → Braintree → Adyen
  - Integrated intelligent routing and retry mechanisms
- **ENHANCED:** `cerberus_enhanced.py` — Added Hyperswitch analytics import for data enrichment

#### Cerberus Bridge API V2
- **NEW:** 10 new REST API v2 endpoints in `cerberus_bridge_api.py`
  - `POST /api/v2/validate` — Validate card via Hyperswitch
  - `GET /api/v2/connectors` — List available PSP connectors
  - `POST /api/v2/routing/create` — Create routing algorithm
  - `GET /api/v2/routing/list` — List routing algorithms
  - `POST /api/v2/vault/tokenize` — Tokenize card in vault
  - `GET /api/v2/vault/customers` — List vault customers
  - `GET /api/v2/analytics/metrics` — Get payment analytics
  - `POST /api/v2/retry/configure` — Configure retry logic
  - `GET /api/v2/retry/status` — Get retry status
  - `GET /api/v2/health` — Hyperswitch health check
- **ENHANCED:** Status endpoint now includes Hyperswitch availability

#### Deployment & Infrastructure
- **NEW:** `scripts/deploy_hyperswitch.sh` — Automated Hyperswitch deployment script
  - Docker Compose orchestration for Hyperswitch stack
  - PostgreSQL 14 database setup
  - Redis 7 cache configuration
  - Environment variable generation
  - Health checks and validation
  - Control Center dashboard setup (port 9000)
- **NEW:** 6 environment variables in `titan.env.example`
  - `HYPERSWITCH_ENABLED` — Enable/disable Hyperswitch (default: 0)
  - `HYPERSWITCH_URL` — Hyperswitch API URL (default: http://127.0.0.1:8080)
  - `HYPERSWITCH_API_KEY` — Merchant API key
  - `HYPERSWITCH_PUBLISHABLE_KEY` — Publishable key for client-side
  - `HYPERSWITCH_ADMIN_KEY` — Admin API key
  - `HYPERSWITCH_CONTROL_CENTER_URL` — Control Center URL (default: http://127.0.0.1:9000)

#### Integration & Wiring
- **ENHANCED:** `integration_bridge.py` — Added `cerberus_hyperswitch` import and subsystem registration
- **ENHANCED:** `titan_api.py` — Added `cerberus_hyperswitch` to `MODULES_AVAILABLE` dictionary

### 📊 Statistics
- **Total Core Modules:** 115 (up from 113)
- **New Modules:** 2 (`cerberus_hyperswitch.py`, enhanced `cerberus_bridge_api.py`)
- **GUI Applications:** 6 (Cerberus AppX V2 now standalone)
- **REST API Endpoints:** 57 (47 legacy + 10 new v2 endpoints)
- **Supported PSPs:** 50+ (via Hyperswitch)
- **Lines of Code Added:** ~1,500

### 🔧 Technical Improvements
- Async/await support for Hyperswitch API calls
- Singleton pattern for Hyperswitch component factories
- Graceful degradation when Hyperswitch is disabled
- Enhanced error handling and logging
- Real-time analytics and metrics tracking

### 📚 Documentation
- **UPDATED:** `README.md` — Complete rewrite for Titan X
  - New "What's New in Titan X" section
  - Hyperswitch deployment instructions
  - Cerberus Bridge API v2 endpoint documentation
  - Architecture diagrams for Hyperswitch integration
  - Updated tech stack with Hyperswitch components
- **NEW:** `CHANGELOG.md` — Version history and release notes

### 🐛 Bug Fixes
- Fixed encoding issues in syntax validation (UTF-8 enforcement)
- Resolved import conflicts between legacy and Hyperswitch modules
- Fixed async event loop handling in Flask endpoints

---

## [9.2.0] - 2025-02-25

### Added
- Full codebase audit and integration
- Cross-module verification and dependency mapping

### Changed
- Improved module import handling
- Enhanced error reporting

---

## [9.1.0] - 2025-02-24

### Added
- Updated all documentation to current VPS-verified state
- 115 modules cataloged
- ONNX engine integration
- Android KYC support
- Operator training system

### Changed
- Synchronized documentation with deployed VPS state

---

## [8.3.0] - 2025-02-23

### Fixed
- Genesis AppX: Added fallback forge for profile generation
- Cerberus AppX: BIN database + traffic light status indicator
- KYC AppX: Android Image tab for Waydroid sync
- Operations AppX: Fallback handling for missing modules
- Intelligence AppX: Fixed broken API calls

---

## [8.2.0] - 2025-02-22

### Added
- V8.2 SINGULARITY release
- 113 core modules
- 5 GUI applications
- Comprehensive documentation suite

### Changed
- Repository restructure: flattened src/ directory
- Consolidated documentation in docs/
- Removed deprecated files and clutter

---

## [8.1.0] - 2025-02-21

### Added
- Operational Playbook: 12 comprehensive docs
- Deep integration of recovered modules
- Firefox/Camoufox/Playwright compatibility layer
- 6 VPS-only modules synced to local

### Fixed
- 40 gaps: UTF-16 encoding, missing classes, import mismatches
- 15 `__init__.py` export fixes

---

## [8.0.0] - 2025-02-20

### Added
- V8.0 SINGULARITY release
- Restructured GUI into 5 apps (23 tabs, 85 modules)
- Persona Enrichment Engine
- Cognitive Profiling system
- Full documentation update

### Changed
- 7 apps → 5 apps + launcher
- Fixed 17 orphan modules

---

## [7.6.0] - 2025-02-19

### Added
- 56-Module Operational Guide
- V7.5 Strategic Architecture documentation
- Deep hardening of all 56 modules

### Changed
- Canvas & Graphics Fingerprint Protection upgrade
- Enhanced forensic and functional gap fixes

---

## [7.5.0] - 2025-02-18

### Added
- Enterprise HRUX theme enforcement
- Trinity apps rebrand
- RDP optimization
- Ollama LLM bridge with dynamic data generation
- Multi-provider LLM routing

### Changed
- Complete UI/UX architecture overhaul
- Fixed all broken imports
- Updated all version references

---

## [7.0.3] - 2025-02-17

### Added
- KYC Enhanced expansion
- Document Injection engine
- Provider Intelligence system
- Liveness Bypass module
- Waydroid Mobile Sync

### Fixed
- Premium GUI themes
- Cerberus 4-tab expansion
- Branding package
- Splash screens
- Undetectability audit

---

## [7.0.0] - 2025-02-16

### Added
- Initial TITAN OS V7.0 release
- 100+ core modules
- 7 GUI applications
- Debian 12 live-build ISO
- VPS deployment scripts
- Comprehensive documentation

### Changed
- Complete system architecture
- Six-ring security model
- Anti-detection framework
- Payment validation engine

---

## Version Naming Convention

- **Major.Minor.Patch** (Semantic Versioning)
- **Codenames:**
  - V10.0 = Titan X (HYPERSWITCH SINGULARITY)
  - V9.x = Titan 9
  - V8.x = Titan 8 (SINGULARITY)
  - V7.x = Titan 7 (SINGULARITY)

---

## Links

- [GitHub Repository](https://github.com/malithwishwa02-dot/titan-7)
- [Documentation](docs/)
- [API Reference](docs/API_REFERENCE.md)
- [Operator Guide](docs/OPERATOR_GUIDE.md)
