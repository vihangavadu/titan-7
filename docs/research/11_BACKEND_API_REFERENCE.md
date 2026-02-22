# Backend API Reference — All Endpoints, Request/Response Formats

## Server: FastAPI on port 8000

The TITAN backend API runs as a systemd service (`titan-backend.service`) on port 8000. It provides programmatic access to all TITAN subsystems.

**Base URL**: `http://localhost:8000`

---

## Core Endpoints

### GET `/api/status`

System operational status.

**Response:**
```json
{
  "status": "operational",
  "checks": {
    "kernel_module": true,
    "phase3_hardening": true,
    "camoufox": true
  }
}
```

### GET `/api/health`

Simple health check.

**Response:**
```json
{"status": "ok"}
```

### GET `/api/profiles`

List all available browser profiles.

**Response:**
```json
{
  "profiles": [
    {
      "name": "titan_30de2ac0af15",
      "path": "/opt/titan/profiles/titan_30de2ac0af15",
      "has_metadata": true,
      "persona": "John Davis"
    }
  ],
  "count": 1
}
```

---

## Validation Endpoints (`/api/validation/*`)

### GET `/api/validation/health`

Validation subsystem health check.

**Response:**
```json
{"status": "ok", "service": "validation"}
```

### GET `/api/validation/preflight`

Run all preflight validation checks before an operation. Tests system locale, timezone, DNS, fonts, kernel module, proxy, and browser readiness.

**Response:**
```json
{
  "status": "ok",
  "checks": {
    "passed": true,
    "checks": [
      {"name": "System Locale", "status": "pass", "message": "Locale: en_US.UTF-8"},
      {"name": "Timezone", "status": "pass", "message": "EST matches target"},
      {"name": "DNS", "status": "pass", "message": "No ISP DNS leak"},
      {"name": "Fonts", "status": "pass", "message": "0 Linux fonts visible"},
      {"name": "TTL", "status": "pass", "message": "TTL=128 (Windows)"},
      {"name": "Kernel Module", "status": "pass", "message": "hardware_shield_v6 loaded"},
      {"name": "Camoufox", "status": "pass", "message": "Installed at /usr/local/bin/camoufox"}
    ]
  }
}
```

### GET `/api/validation/deep-verify`

Run deep identity verification across three phases: font hygiene, audio hardening, and timezone synchronization.

**Response:**
```json
{
  "status": "ok",
  "phases": {
    "verify_font_hygiene": true,
    "verify_audio_hardening": false,
    "verify_timezone_sync": true
  }
}
```

- `verify_font_hygiene`: Checks that zero Linux-specific fonts are enumerable
- `verify_audio_hardening`: Checks PulseAudio/PipeWire configuration matches Windows profile
- `verify_timezone_sync`: Checks system TZ, browser TZ, and locale are all synchronized

### POST `/api/validation/forensic-clean`

Trigger forensic trace cleanup. Removes operational artifacts from the system.

**Response:**
```json
{
  "status": "ok",
  "message": "forensic_cleaner loaded",
  "functions": ["clean_profile"]
}
```

### GET `/api/validation/profile-realism`

Score the current profile's realism across multiple dimensions.

**Response:**
```json
{
  "status": "ok",
  "message": "profile_realism_engine loaded"
}
```

---

## Backend Architecture

### Server (`server.py`)

The FastAPI server initializes with:
```python
# Import paths
sys.path.insert(0, "/opt/titan/core")
sys.path.insert(0, "/opt/lucid-empire")

# Mount validation router
app.include_router(validation_router, prefix="/api/validation")
```

### Module Structure

```
/opt/lucid-empire/backend/
├── __init__.py              # Lazy imports (avoids circular dependency)
├── server.py                # FastAPI app, routes, startup
├── lucid_api.py             # Main API class (ProfileFactory, Cortex)
├── lucid_manager.py         # Backend orchestration manager
├── lucid_commander.py       # Command execution engine
├── profile_manager.py       # Profile CRUD operations
├── genesis_engine.py        # Profile generation backend
├── warming_engine.py        # Profile warming/aging backend
├── commerce_injector.py     # Commerce token injection
├── firefox_injector.py      # Firefox profile injection (v1)
├── firefox_injector_v2.py   # Firefox profile injection (v2)
├── handover_protocol.py     # Manual handover backend
├── blacklist_validator.py   # BIN/IP blacklist checking
├── zero_detect.py           # Zero-detection engine
├── validation/
│   ├── __init__.py
│   └── validation_api.py    # Validation endpoints (FastAPI router)
├── core/ → core_legacy/     # Symlink to legacy core
│   ├── __init__.py
│   ├── cortex.py            # Core orchestration brain
│   ├── profile_store.py     # Profile database (ProfileFactory, ProfileStore)
│   ├── genesis_engine.py    # Legacy genesis engine
│   ├── bin_finder.py        # BIN lookup database
│   ├── ebpf_loader.py       # eBPF program loader
│   ├── font_config.py       # Font configuration
│   ├── time_displacement.py # Temporal displacement engine
│   └── time_machine.py      # Time manipulation utilities
├── modules/
│   └── __init__.py
└── network/
    └── __init__.py
```

### Systemd Service

```ini
# /etc/systemd/system/titan-backend.service
[Unit]
Description=TITAN Backend API Server
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/lucid-empire
Environment=PYTHONPATH=/opt/lucid-empire:/opt/titan/core
ExecStart=/usr/bin/python3 -c "from backend.server import app; import uvicorn; uvicorn.run(app, host='0.0.0.0', port=8000)"
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### Import Resolution

The backend uses a **lazy import** pattern in `__init__.py` to avoid circular dependencies:

```python
def __getattr__(name):
    if name == 'core':
        from . import core
        return core
    elif name == 'modules':
        from . import modules
        return modules
    # ...
```

All backend modules use **relative imports** (`from .core import ...`) rather than absolute imports (`from backend.core import ...`) to work correctly within the package structure.

---

## Hostinger API Integration

TITAN can be managed remotely via the Hostinger VPS API:

**API Base**: `https://developers.hostinger.com`
**Auth**: `Authorization: Bearer <token>`

### Key Endpoints Used

| Endpoint | Purpose |
|----------|---------|
| `GET /api/vps/v1/virtual-machines` | List VPS instances |
| `GET /api/vps/v1/virtual-machines/{id}` | VPS details (IP, state, specs) |
| `GET /api/vps/v1/firewall` | Firewall rules |
| `POST /api/vps/v1/virtual-machines/{id}/restart` | Restart VPS |

### VPS Details

```json
{
  "id": 1400969,
  "plan": "KVM 8",
  "cpus": 8,
  "memory": 32768,
  "disk": 409600,
  "state": "running",
  "ipv4": [{"address": "72.62.72.48"}],
  "template": {"name": "Debian 12"}
}
```
