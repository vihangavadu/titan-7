# 08 — External APIs & Integrations

**Backend API — REST Endpoints — External Services — Inter-Module Communication**

Titan X exposes a comprehensive REST API for programmatic access to all subsystems, integrates with external services (proxy providers, VPN, AI, messaging), and uses Redis pub/sub + JSON session files for real-time inter-module communication. This document covers every API endpoint, external service integration, and communication protocol.

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                         TITAN X API LAYER                            │
│                                                                       │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐         │
│  │  titan_api.py   │  │   server.py    │  │ cockpit_daemon │         │
│  │  Flask :8443    │  │  FastAPI :8000  │  │  WebSocket     │         │
│  │  27 endpoints   │  │  7 endpoints   │  │  Real-time     │         │
│  └───────┬────────┘  └───────┬────────┘  └───────┬────────┘         │
│          │                   │                    │                   │
│          ▼                   ▼                    ▼                   │
│  ┌─────────────────────────────────────────────────────────┐        │
│  │                    CORE MODULES (118)                     │        │
│  └─────────────────────────────────────────────────────────┘        │
│          │                   │                    │                   │
│          ▼                   ▼                    ▼                   │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌──────────┐     │
│  │   Ollama    │  │   Redis    │  │   Mullvad   │  │  Xray    │     │
│  │  :11434     │  │   :6379    │  │  WireGuard  │  │  VLESS   │     │
│  └────────────┘  └────────────┘  └────────────┘  └──────────┘     │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌──────────┐     │
│  │  Camoufox   │  │   ntfy     │  │ Proxy APIs  │  │ Hostinger│     │
│  │  Playwright │  │  :80/443   │  │ Bright Data │  │  VPS API │     │
│  └────────────┘  └────────────┘  └────────────┘  └──────────┘     │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 1. Titan REST API (`titan_api.py`)

**Server**: Flask on port 8443
**Auth**: Bearer token via `X-API-Secret` header
**Rate limit**: 60 requests/minute per IP

### Authentication

```
GET /api/v1/auth/token
Header: X-API-Secret: <secret>
→ Returns: {"token": "eyJ...", "expires_in": 3600}
```

All authenticated endpoints require `Authorization: Bearer <token>`.

### Health & Status Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/v1/health` | No | System health + loaded module count |
| GET | `/api/v1/modules` | Yes | List all available core modules |
| GET | `/api/v1/bridge/status` | Yes | Integration bridge subsystem flags |

#### GET `/api/v1/health` Response

```json
{
  "status": "operational",
  "modules_loaded": 118,
  "uptime_seconds": 86400,
  "version": "10.0"
}
```

### Profile Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v1/profile/generate` | Yes | Generate forensic-grade browser profile |
| GET | `/api/profiles` | No | List all stored profiles |

#### POST `/api/v1/profile/generate` Request

```json
{
  "target": "amazon_us",
  "persona_name": "John Smith",
  "persona_email": "jsmith1987@gmail.com",
  "age_days": 90,
  "browser_type": "firefox",
  "hardware_profile": "us_windows_desktop"
}
```

### Card Validation Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v1/card/validate` | Yes | Validate card via Cerberus (SetupIntent) |

#### POST `/api/v1/card/validate` Request

```json
{
  "number": "4111111111111111",
  "exp_month": "12",
  "exp_year": "25",
  "cvv": "123"
}
```

#### Response

```json
{
  "status": "live",
  "risk_score": 25,
  "bank_name": "Chase",
  "country": "US",
  "card_type": "credit",
  "card_level": "signature",
  "bin_grade": "A"
}
```

### Intelligence Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v1/ja4/generate` | Yes | Generate JA4+ TLS fingerprint |
| POST | `/api/v1/tra/exemption` | Yes | Get TRA exemption strategy (PSD2) |
| POST | `/api/v1/issuer/risk` | Yes | Calculate issuer decline risk |
| POST | `/api/v1/session/synthesize` | Yes | Synthesize returning session artifacts |
| POST | `/api/v1/storage/synthesize` | Yes | Synthesize IndexedDB/localStorage |

### KYC Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v1/kyc/detect` | Yes | Detect KYC provider from HTML |
| POST | `/api/v1/kyc/strategy` | Yes | Get KYC bypass strategy |
| POST | `/api/v1/depth/generate` | Yes | Generate ToF depth map for liveness |

### Persona Enrichment Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v1/persona/enrich` | Yes | Full persona enrichment + pattern prediction |
| POST | `/api/v1/persona/coherence` | Yes | Purchase coherence validation |

#### POST `/api/v1/persona/enrich` Request

```json
{
  "name": "John Smith",
  "email": "john@gmail.com",
  "age": 35,
  "address": {"state": "TX", "country": "US"},
  "target_merchant": "g2a.com",
  "target_item": "Steam Gift Card",
  "amount": 50.00
}
```

#### Response

```json
{
  "success": true,
  "data": {
    "demographic": {
      "age_group": "millennial",
      "occupation": "unemployed",
      "income_level": "middle",
      "tech_savvy": 0.5,
      "online_shopper": 0.65
    },
    "top_categories": [
      {"name": "Streaming Services", "likelihood": 0.75},
      {"name": "Tech Gadgets", "likelihood": 0.70}
    ],
    "coherence": {
      "coherent": true,
      "likelihood": 0.55,
      "category": "gaming"
    }
  }
}
```

### Real-Time Co-Pilot Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/copilot/event` | No | Ingest browser event (sendBeacon) |
| GET | `/api/v1/copilot/guidance` | Yes | Get latest AI guidance messages |
| GET | `/api/v1/copilot/dashboard` | Yes | Full co-pilot dashboard status |
| POST | `/api/v1/copilot/begin` | Yes | Begin operation (pre-flight) |
| POST | `/api/v1/copilot/end` | Yes | End operation (post-analysis) |
| GET | `/api/v1/copilot/timing` | Yes | Real-time timing intelligence |
| GET | `/api/v1/copilot/history` | Yes | Operation history |

### Autonomous Engine Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/v1/autonomous/status` | Yes | Engine status |
| POST | `/api/v1/autonomous/start` | Yes | Start autonomous engine |
| POST | `/api/v1/autonomous/stop` | Yes | Stop autonomous engine |
| GET | `/api/v1/autonomous/report` | Yes | Daily report |

### Android/Waydroid Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/v1/android/status` | Yes | Waydroid container status |
| POST | `/api/v1/android/start` | Yes | Start Android session |
| POST | `/api/v1/android/stop` | Yes | Stop Android session |
| POST | `/api/v1/android/shell` | Yes | Execute Android shell command |
| POST | `/api/v1/android/spoof` | Yes | Apply device identity preset |
| POST | `/api/v1/android/sync` | Yes | Cross-device sync |

---

## 2. Backend API (`server.py`)

**Server**: FastAPI/Uvicorn on port 8000
**Service**: `titan-backend.service` (systemd)

### Validation Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/status` | System operational status |
| GET | `/api/health` | Simple health check |
| GET | `/api/profiles` | List all browser profiles |
| GET | `/api/validation/health` | Validation subsystem health |
| GET | `/api/validation/preflight` | Run all preflight checks |
| GET | `/api/validation/deep-verify` | Deep identity verification (3 phases) |
| POST | `/api/validation/forensic-clean` | Trigger forensic cleanup |
| GET | `/api/validation/profile-realism` | Score profile realism |

#### GET `/api/validation/preflight` Response

```json
{
  "status": "ok",
  "checks": {
    "passed": true,
    "checks": [
      {"name": "System Locale", "status": "pass", "message": "en_US.UTF-8"},
      {"name": "Timezone", "status": "pass", "message": "EST matches target"},
      {"name": "DNS", "status": "pass", "message": "No ISP DNS leak"},
      {"name": "Fonts", "status": "pass", "message": "0 Linux fonts visible"},
      {"name": "TTL", "status": "pass", "message": "TTL=128 (Windows)"},
      {"name": "Kernel Module", "status": "pass", "message": "hardware_shield_v6 loaded"},
      {"name": "Camoufox", "status": "pass", "message": "Installed"}
    ]
  }
}
```

#### GET `/api/validation/deep-verify` Response

```json
{
  "phases": {
    "verify_font_hygiene": true,
    "verify_audio_hardening": false,
    "verify_timezone_sync": true
  }
}
```

### Backend Module Structure

```
/opt/lucid-empire/backend/
├── server.py                # FastAPI app, startup, routes
├── lucid_api.py             # ProfileFactory, Cortex orchestrator
├── lucid_manager.py         # Backend orchestration manager
├── lucid_commander.py       # Command execution engine
├── profile_manager.py       # Profile CRUD operations
├── genesis_engine.py        # Profile generation backend
├── warming_engine.py        # Profile warming/aging
├── commerce_injector.py     # Commerce token injection
├── firefox_injector.py      # Firefox profile injection (v1)
├── firefox_injector_v2.py   # Firefox profile injection (v2)
├── handover_protocol.py     # Manual handover backend
├── blacklist_validator.py   # BIN/IP blacklist checking
├── zero_detect.py           # Zero-detection engine
├── validation/
│   └── validation_api.py    # Validation endpoints (FastAPI router)
└── core/
    ├── cortex.py             # Core orchestration brain
    ├── profile_store.py      # ProfileFactory, ProfileStore
    ├── bin_finder.py         # BIN lookup database
    ├── ebpf_loader.py        # eBPF program loader
    ├── font_config.py        # Font configuration
    ├── time_displacement.py  # Temporal displacement engine
    └── time_machine.py       # Time manipulation utilities
```

---

## 3. External Service Integrations

### Ollama (Local LLM)

| Property | Value |
|----------|-------|
| **Service** | `ollama.service` (systemd) |
| **Port** | 11434 |
| **API** | OpenAI-compatible (`/api/generate`, `/api/chat`) |
| **Models** | 4 ONNX INT4 + 6 Ollama models |

**Integration module**: `ollama_bridge.py`

```python
class OllamaBridge:
    base_url = "http://127.0.0.1:11434"
    
    async def generate(self, model, prompt, **kwargs) -> str
    async def chat(self, model, messages, **kwargs) -> str
    async def list_models(self) -> List[Dict]
    async def pull_model(self, model_name) -> bool
    def is_available(self) -> bool
```

**Task routing**: 67 AI tasks routed to optimal model via `llm_config.json`:

| Model | Base | Size | Avg Response | Primary Tasks |
|-------|------|------|-------------|---------------|
| titan-flash | Qwen2.5-0.5B | 350MB | <1s | Generation, warmup, cookies, behavioral tuning |
| titan-analyst | Qwen2.5-1.5B | 1GB | ~2s | JSON extraction, BIN analysis, profile validation |
| titan-strategist | Phi-3.5-mini | 2.2GB | ~4s | Strategy, risk analysis, detection reasoning |
| titan-operator | SmolLM2-1.7B | 1.1GB | ~2s | Situation assessment, timing, abort decisions |

### Redis

| Property | Value |
|----------|-------|
| **Service** | `redis-server.service` |
| **Port** | 6379 |
| **Version** | 7.0.15 |

**Integration module**: `titan_session.py`

```python
class TitanSession:
    # Pub/sub channels for real-time inter-app communication
    CHANNELS = {
        "titan:operations": "Operation state changes",
        "titan:intelligence": "AI guidance messages",
        "titan:detection": "Detection alerts",
        "titan:kill": "Kill switch signals",
        "titan:profile": "Profile status updates",
        "titan:copilot": "Co-pilot events"
    }
    
    def publish(self, channel, data: dict) -> None
    def subscribe(self, channel, callback) -> None
    def get_session(self, session_id) -> dict
    def set_session(self, session_id, data: dict, ttl=3600) -> None
```

**Session file format** (`/opt/titan/state/session.json`):

```json
{
  "session_id": "op_2026_03_15_001",
  "profile_uuid": "titan_30de2ac0af15",
  "target": "amazon_us",
  "card_bin": "414720",
  "proxy_ip": "73.162.45.123",
  "proxy_geo": {"city": "Austin", "state": "TX"},
  "fraud_score": 92,
  "threat_level": "GREEN",
  "started_at": "2026-03-15T14:30:00Z",
  "phase": "checkout"
}
```

### Mullvad VPN

| Property | Value |
|----------|-------|
| **Service** | `mullvad-daemon.service` |
| **Protocol** | WireGuard |
| **Version** | 2025.14 |
| **Features** | DAITA (AI traffic analysis defense), multihop, DNS leak protection |

**Integration module**: `mullvad_vpn.py`

```python
class MullvadVPN:
    def connect(self, server: str = "auto") -> bool
    def disconnect(self) -> bool
    def set_country(self, country_code: str) -> bool
    def set_city(self, city: str) -> bool
    def enable_daita(self) -> bool       # Defense Against AI-Guided Traffic Analysis
    def enable_multihop(self, entry: str, exit: str) -> bool
    def get_status(self) -> Dict
    def check_leak(self) -> bool          # DNS/WebRTC leak test
    def get_relay_list(self) -> List[Dict]
```

### Xray-core (VLESS+Reality)

| Property | Value |
|----------|-------|
| **Service** | `xray.service` |
| **Version** | 26.2.6 |
| **Protocol** | VLESS + Reality |

**Integration module**: `lucid_vpn.py`

```python
class LucidVPN:
    # VLESS+Reality makes VPN traffic appear as legitimate HTTPS
    # DPI sees connections to microsoft.com, apple.com, etc.
    
    SNI_ROTATION_POOL = [
        "microsoft.com", "apple.com", "amazon.com",
        "cloudflare.com", "google.com", "facebook.com",
        "github.com", "linkedin.com"
    ]
    
    def connect(self, config_path: str) -> bool
    def disconnect(self) -> bool
    def rotate_sni(self) -> str
    def get_status(self) -> Dict
```

### ntfy (Push Notifications)

| Property | Value |
|----------|-------|
| **Service** | Self-hosted or ntfy.sh |
| **Port** | 80/443 |
| **Version** | 2.11.0 |

**Integration module**: `titan_notifications.py`

```python
class TitanNotifications:
    def send(self, topic: str, title: str, message: str, priority: int = 3) -> bool
    
    # Notification topics
    TOPICS = {
        "titan-ops": "Operation success/failure alerts",
        "titan-detection": "Detection warnings",
        "titan-system": "System health alerts",
        "titan-panic": "Kill switch activation alerts"
    }
```

**Example alert**:
```
POST https://ntfy.sh/titan-ops
Title: Operation Success
Message: Amazon US — $149.99 — Profile titan_30de — 42s checkout
Priority: 4 (high)
```

### Camoufox (Antidetect Browser)

| Property | Value |
|----------|-------|
| **Version** | 0.4.11 |
| **Engine** | Modified Firefox (Playwright-compatible) |
| **Install** | pip + Playwright |

**Integration module**: `integration_bridge.py`

```python
class TitanIntegrationBridge:
    def launch_browser(self, target_url: str = None) -> bool
    def get_browser_config(self) -> BrowserLaunchConfig
    
    # Camoufox launch with all shields
    # 1. Load fingerprint config (canvas, WebGL, audio)
    # 2. Set proxy (residential or Mullvad)
    # 3. Load profile (cookies, history, localStorage)
    # 4. Inject Ghost Motor extension
    # 5. Inject TX Monitor extension
    # 6. Set user-agent, platform, locale
    # 7. Launch with Playwright
```

### Proxy Provider APIs

| Provider | Type | API Style | Module |
|----------|------|-----------|--------|
| Bright Data | Residential | HTTP endpoint | `proxy_manager.py` |
| SOAX | Residential | HTTP endpoint | `proxy_manager.py` |
| IPRoyal | Residential | HTTP endpoint | `proxy_manager.py` |
| Webshare | Residential | HTTP endpoint | `proxy_manager.py` |
| Custom pool | Mixed | JSON file | `proxy_manager.py` |

**Proxy selection flow**:
```
Billing address → GeoTarget → proxy_manager.get_proxy_for_geo(target) →
  Filter by country → Filter by state → Filter by city →
  Health check → Sticky session → ProxyEndpoint
```

### Hostinger VPS API

| Property | Value |
|----------|-------|
| **Base URL** | `https://developers.hostinger.com` |
| **Auth** | Bearer token |

**Key endpoints**:

| Endpoint | Purpose |
|----------|---------|
| `GET /api/vps/v1/virtual-machines` | List VPS instances |
| `GET /api/vps/v1/virtual-machines/{id}` | VPS details (IP, state, specs) |
| `GET /api/vps/v1/firewall` | Firewall rules |
| `POST /api/vps/v1/virtual-machines/{id}/restart` | Restart VPS |

**VPS specs** (ID: 1400969):
- Plan: KVM 8 (8 CPUs, 32GB RAM, 400GB disk)
- OS: Debian 12 (bookworm)
- IP: 72.62.72.48

### Cloud LLM Providers (Fallback)

| Provider | Model | Module | Use Case |
|----------|-------|--------|----------|
| OpenAI | gpt-4o-mini | `cognitive_core.py` | Cloud fallback for complex tasks |
| Anthropic | claude-3.5-sonnet | `cognitive_core.py` | Cloud fallback for reasoning |
| Groq | llama-3.1-70b | `cognitive_core.py` | Fast cloud inference |
| vLLM (self-hosted) | Llama-3-70B AWQ | `cognitive_core.py` | Primary cloud brain |

**Failover chain**: ONNX local → Ollama local → vLLM cloud → OpenAI → Anthropic → Groq → Rule-based engine

### Stripe API (Card Validation)

| Property | Value |
|----------|-------|
| **Base URL** | `https://api.stripe.com/v1` |
| **Auth** | `sk_live_*` secret key |

**Used endpoints**:

| Endpoint | Purpose |
|----------|---------|
| `POST /v1/setup_intents` | Zero-charge card validation |
| `POST /v1/payment_methods` | Create payment method for validation |
| `POST /v1/tokens` | Tokenize card for validation |

**Key rotation**: Multiple Stripe keys in rotation pool — if one gets rate-limited, switch to next.

---

## 4. Inter-Module Communication

### Session Sharing (`titan_session.py`)

All 11 GUI apps share state via two mechanisms:

**1. JSON Session File** (`/opt/titan/state/session.json`):
- Written by Operations app when operation begins
- Read by all other apps for context
- Updated in real-time as operation progresses
- Contains: profile UUID, target, card BIN, proxy, fraud score, phase

**2. Redis Pub/Sub**:
- Real-time event broadcasting between apps
- Sub-millisecond message delivery
- Used for: detection alerts, kill switch signals, copilot guidance

### Cockpit Daemon (`cockpit_daemon.py`)

WebSocket-based command protocol for remote control:

| Command | Direction | Action |
|---------|-----------|--------|
| `START_OPERATION` | Remote → Titan | Begin operation with params |
| `STOP_OPERATION` | Remote → Titan | Graceful stop |
| `PANIC` | Remote → Titan | Trigger kill switch |
| `GET_STATUS` | Remote → Titan | Current operation status |
| `STATUS_UPDATE` | Titan → Remote | Real-time status broadcast |
| `FRAUD_ALERT` | Titan → Remote | Detection warning |
| `START_WAYDROID` | Remote → Titan | Start Android VM |
| `STOP_WAYDROID` | Remote → Titan | Stop Android VM |

### Prometheus Metrics Export

| Port | Module | Metrics |
|------|--------|---------|
| 9200 | `payment_success_metrics.py` | Payment success/decline rates |
| 9201 | `titan_monitor.py` | System health metrics |

**Example metrics**:
```
titan_payment_success_total{target="amazon",psp="stripe"} 47
titan_payment_decline_total{reason="card_declined"} 12
titan_3ds_challenge_total{psp="adyen",result="frictionless"} 23
titan_profile_quality_score{profile="titan_30de"} 87
titan_kill_switch_activations_total 3
```

---

## 5. Browser Extensions

### TX Monitor Extension

**Location**: `/opt/titan/extensions/tx_monitor/`

Injected into Camoufox via Playwright — monitors antifraud SDK signals:

| SDK Detected | JavaScript Hook | Data Extracted |
|-------------|----------------|----------------|
| Forter | `window.__forter_score` | Fraud score (0-100) |
| Sift | `window._sift._score` | Risk score |
| ThreatMetrix | `window.tmx_session_id` | Session ID |
| Riskified | `window.RISKX.sessionId` | Session ID |
| Kount | `window.ka.sessionId` | Device session |

**Communication**: Extension → `navigator.sendBeacon('/api/copilot/event')` → Flask API → Kill Switch daemon

### Ghost Motor Extension

**Location**: `/opt/titan/extensions/ghost_motor/`

Content script that intercepts and humanizes all browser events:
- Mouse event coordinates: adds micro-noise
- Keyboard event timestamps: adds per-key timing variation
- Scroll events: adds momentum and decay
- Touch events: disabled (desktop persona)

---

## 6. Data Flow Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  GUI Apps    │────→│ titan_session │────→│   Redis      │
│  (PyQt6)    │     │  (JSON+pub)  │     │  (pub/sub)   │
└──────┬───────┘     └──────────────┘     └──────────────┘
       │                                         │
       ▼                                         ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ titan_api.py │────→│ Core Modules │────→│   Ollama     │
│  (Flask)     │     │   (118 py)   │     │  (4 models)  │
└──────┬───────┘     └──────┬───────┘     └──────────────┘
       │                    │
       ▼                    ▼
┌──────────────┐     ┌──────────────┐
│  Camoufox    │     │  Extensions  │
│ (Playwright) │←────│ (TX+Ghost)   │
└──────┬───────┘     └──────────────┘
       │
       ▼
┌──────────────┐     ┌──────────────┐
│ Residential  │     │   Target     │
│   Proxy      │────→│  Merchant    │
└──────────────┘     └──────────────┘
```

---

*Document 08 of 11 — Titan X Documentation Suite — V10.0 — March 2026*
