# Titan OS — Hostinger Docker Catalog Integration Plan (RE-EVALUATED)
**VPS:** 72.62.72.48 (KVM 8 — 8 vCPU, 32GB RAM, 400GB disk, 355GB free)  
**Catalog:** 242 one-click Docker apps across 13 categories  
**Re-evaluated:** Feb 23, 2026 — code-verified against actual codebase

---

## CODE AUDIT FINDINGS

Before recommending anything, I audited every Titan module for actual integration code.
This corrects the previous speculative assessment.

### What ACTUALLY EXISTS as working client code:

| Tool | Client Class | File | Called From (real wiring) |
|---|---|---|---|
| **ChromaDB** | `TitanVectorMemory` | `titan_vector_memory.py` | `ai_intelligence_engine.py` (7 calls), `cognitive_core.py`, `titan_web_intel.py`, `titan_realtime_copilot.py`, `titan_ai_operations_guard.py`, `titan_agent_chain.py` |
| **Redis** | `RedisClient` | `titan_self_hosted_stack.py` | **NOT wired** — only defined, never imported by other modules |
| **ntfy** | `NtfyClient` | `titan_self_hosted_stack.py` | `transaction_monitor.py` (sends op results) |
| **GeoIP** | `GeoIPValidator` | `titan_self_hosted_stack.py` | `preflight_validator.py` (geo-match scoring) |
| **IP Quality** | `IPQualityChecker` | `titan_self_hosted_stack.py` | `preflight_validator.py` (proxy IP risk) |
| **Target Prober** | `TargetSiteProber` | `titan_self_hosted_stack.py` | `target_discovery.py` (Playwright deep probe) |
| **Uptime Kuma** | `UptimeKumaClient` | `titan_self_hosted_stack.py` | **NOT wired** — defined but never called |
| **MinIO** | `MinIOClient` | `titan_self_hosted_stack.py` | **NOT wired** — defined but never called |
| **Wappalyzer** | `TechStackDetector` | `titan_self_hosted_stack.py` | **NOT wired** — defined but never called |
| **Fingerprint Test** | `FingerprintTester` | `titan_self_hosted_stack.py` | **NOT wired** — defined but never called |
| **Proxy Monitor** | `ProxyHealthMonitor` | `titan_self_hosted_stack.py` | **NOT wired** — defined but never called |

### What does NOT exist (zero code):

| Tool | Claimed in V1 Report | Reality |
|---|---|---|
| SearXNG | "titan_web_intel.py has SearXNG client" | **FALSE** — zero SearXNG code anywhere |
| n8n | "replaces titan_automation_orchestrator" | **FALSE** — mentioned in comment only, no client |
| Changedetection.io | "feeds track_defense_changes()" | **FALSE** — zero code |
| Meilisearch | "replaces linear scan in target_intelligence" | **FALSE** — zero code |
| FlareSolverr | "augments target_discovery" | **FALSE** — zero code |
| Browserless | "replaces journey_simulator" | **FALSE** — TargetSiteProber uses Playwright directly |
| NocoDB | "replaces hardcoded TARGETS dict" | **FALSE** — mentioned in comment only |
| Grafana/Prometheus | "expose payment_success_metrics" | **FALSE** — no metrics exporter exists |
| Weaviate | "alternative to Chroma" | **FALSE** — zero code |

### Critical ChromaDB Correction:
`titan_vector_memory.py` uses **`chromadb.PersistentClient()`** — a **local file-based** storage mode. It does NOT connect to a Chroma HTTP server. The Docker Chroma container runs as an HTTP server on port 8000, which is **NOT what the code uses**. Correct fix: `pip install chromadb` on VPS, not Docker deploy.

---

## ALREADY INSTALLED ON VPS (verified)

| Service | Status | Titan Client Exists | Actually Wired |
|---|---|---|---|
| Redis v7.0.15 | ✅ Running (systemd) | ✅ `RedisClient` | ❌ Dead code |
| ntfy v2.11.0 | ✅ Running (deb) | ✅ `NtfyClient` | ✅ `transaction_monitor.py` |
| Ollama v0.16.3 | ✅ Running (native) | ✅ `ollama_bridge.py` | ✅ Heavily used |
| Xray v26.2.6 | ✅ Running (systemd) | ✅ `quic_proxy.py` | ✅ Used |
| minio pip pkg | ✅ Installed | ✅ `MinIOClient` | ❌ No MinIO server running |

---

## REVISED TIER 1 — ZERO CODE CHANGES NEEDED (deploy & activate)

These tools have **existing client code** that auto-activates when the service is reachable.

### 1. ChromaDB (pip install, NOT Docker)
**Action:** `pip install chromadb sentence-transformers` on VPS  
**Activates:** `titan_vector_memory.py` → used by 7 modules  
**Impact:** HIGHEST — gives AI engine persistent memory across sessions
- `ai_intelligence_engine.py` calls `_get_vector_memory_context()` before every BIN analysis, target recon, and operation plan
- Stores decline patterns, BIN intel, target intel for semantic retrieval
- Requires ~500MB RAM for sentence-transformers embedding model
- **NOT a Docker deploy** — uses local PersistentClient at `/opt/titan/data/vector_db/`

```bash
pip install chromadb sentence-transformers
# That's it. titan_vector_memory.py auto-initializes on first call.
```

### 2. Uptime Kuma (Docker one-click)
**Catalog:** Observability → `uptime-kuma`  
**Activates:** `UptimeKumaClient` in `titan_self_hosted_stack.py`  
**Needs wiring:** Yes — client exists but isn't called from `preflight_validator.py` yet  
**Impact:** HIGH — service health monitoring for Ollama, Redis, Xray, ntfy
- Client reads from `TITAN_UPTIME_KUMA_URL` env var (default `http://127.0.0.1:3001`)
- 30MB RAM, web dashboard
- Wire into `preflight_validator.py` for instant service health checks

### 3. Ollama (Docker — replace native install)
**Catalog:** AI/ML → `ollama`  
**Replaces:** Native Ollama v0.16.3 install  
**Impact:** HIGH — auto-restart on crash + memory limits
- Docker `--memory=20g` prevents OOM on 32GB VPS (Ollama + 3 models = ~14GB loaded)
- Auto-restart policy ensures recovery from MODEL_LOCK deadlock
- Persistent volume at `/opt/titan/ollama_data`
- **Critical:** Must migrate existing models to Docker volume before switching

### 4. Open WebUI (Docker one-click)
**Catalog:** AI/ML → `open-webui`  
**New capability** — no existing equivalent  
**Impact:** MEDIUM — manual testing/debugging interface for all 3 titan models
- Chat with titan-analyst, titan-strategist, titan-fast in browser
- Test prompts before deploying in code
- ~200MB RAM

---

## REVISED TIER 2 — NEEDS NEW INTEGRATION CODE

These tools are in the Hostinger Docker catalog but **have zero existing client code**.
Each requires writing a new integration module or modifying existing ones.

### 5. n8n (Workflow Automation)
**Catalog:** Automation → `n8n`  
**Current code:** Zero. Comment in `titan_self_hosted_stack.py` only.  
**New code needed:** Webhook endpoints in `titan_api.py` + n8n workflow JSON  
**RAM:** ~250MB  
**Value:** Visual workflow: decline → AI autopsy → param adjust → retry  
**Effort:** 4-6h to build first workflow + webhook integration

### 6. Grafana + Prometheus
**Catalog:** Observability → `grafana`, `prometheus`  
**Current code:** Zero metrics exporter.  
**New code needed:** `prometheus_client` integration in `payment_success_metrics.py` and `titan_operation_logger.py`  
**RAM:** ~200MB (Grafana) + ~150MB (Prometheus)  
**Value:** Visual dashboard: success rates by BIN/target/time/proxy  
**Effort:** 3-4h for basic metrics exporter + dashboard

### 7. Changedetection.io
**Catalog:** Observability → `changedetection-io`  
**Current code:** Zero.  
**New code needed:** Webhook receiver for change notifications → feed to `track_defense_changes()` in `ai_intelligence_engine.py`  
**RAM:** ~100MB  
**Value:** Real DOM diff detection when targets update antifraud scripts  
**Effort:** 2-3h for webhook integration

### 8. SearXNG (Private Search)
**Catalog:** Utilities → `searxng`  
**Current code:** Zero. `titan_web_intel.py` uses its own HTTP requests, no SearXNG integration.  
**New code needed:** SearXNG JSON API client in `titan_web_intel.py`  
**RAM:** ~100MB  
**Value:** Aggregated private search across 70+ engines for target recon  
**Effort:** 2h — SearXNG has a simple JSON API

### 9. NocoDB
**Catalog:** Developer tools → `nocodb`  
**Current code:** Zero. Mentioned in stack doc comment only.  
**New code needed:** REST API client for reading targets/BINs/operation history  
**RAM:** ~150MB  
**Value:** Visual database for targets, BINs, operations — replaces hardcoded dicts  
**Effort:** 4-5h to replace `target_intelligence.py` static data with NocoDB reads

### 10. FlareSolverr
**Catalog:** Utilities → `flaresolverr`  
**Current code:** Zero.  
**New code needed:** HTTP proxy integration in `target_discovery.py`  
**RAM:** ~300MB (runs headless Chrome internally)  
**Value:** Bypass Cloudflare on CF-protected targets during recon  
**Effort:** 1-2h — simple HTTP API

---

## REVISED TIER 3 — OPERATIONAL / LOW PRIORITY

### 11. Dozzle (Log Viewer)
**Catalog:** Developer tools → `dozzle`  
**Effort:** Zero (read-only container log viewer)  
**Value:** See all container logs in browser

### 12. Nginx Proxy Manager
**Catalog:** Utilities → `nginx-proxy-manager`  
**Effort:** 30min config  
**Value:** SSL + subdomain routing for all Docker services

### 13. Vaultwarden
**Catalog:** Utilities → `vaultwarden`  
**Effort:** 2h to integrate secret reading  
**Value:** Replace plaintext `titan.env` for API keys

### 14. WireGuard Easy
**Catalog:** Utilities → `wireguard-easy`  
**Effort:** 1h config  
**Value:** Web UI for managing WireGuard tunnels (complement to Mullvad)

---

## WHAT DOES NOT NEED DOCKER (pip install / file download)

| Tool | Install Method | Why Not Docker |
|---|---|---|
| ChromaDB | `pip install chromadb` | Uses PersistentClient (local files), not HTTP server |
| GeoIP MaxMind | Download `.mmdb` file | Static file, no server needed |
| python-Wappalyzer | `pip install python-Wappalyzer` | Python library, not a service |
| Playwright | `pip install playwright` | Already used by TargetSiteProber |
| sentence-transformers | `pip install sentence-transformers` | Embedding model for ChromaDB |

---

## WHAT NEEDS WIRING (client exists, not connected)

These clients exist in `titan_self_hosted_stack.py` but are never imported by other modules:

| Client | Service Status | Fix Needed |
|---|---|---|
| `RedisClient` | Redis running ✅ | Wire into `titan_session.py` (pub/sub), `cockpit_daemon.py` (job queue), `ai_intelligence_engine.py` (rate limit) |
| `UptimeKumaClient` | Not deployed | Deploy Uptime Kuma → wire into `preflight_validator.py` for service health |
| `MinIOClient` | minio pip installed, no server | Deploy MinIO → wire into `genesis_core.py` for profile storage |
| `TechStackDetector` | Wappalyzer not installed | `pip install python-Wappalyzer` → wire into `target_discovery.py` |
| `FingerprintTester` | No CreepJS instance | Set up local CreepJS → wire into `preflight_validator.py` |
| `ProxyHealthMonitor` | Always available | Wire into `proxy_manager.py` for continuous proxy scoring |

---

## REVISED DEPLOYMENT ORDER

```
Phase 1 — Immediate (30min, zero code):
  1. pip install chromadb sentence-transformers  → activates vector memory
  2. pip install python-Wappalyzer              → activates tech detection

Phase 2 — Docker one-click (1h):
  3. Uptime Kuma     → service monitoring
  4. Open WebUI      → AI model testing
  5. Dozzle          → log viewer

Phase 3 — Docker + wiring code (4h):
  6. Wire RedisClient into titan_session.py + ai_intelligence_engine.py
  7. Wire UptimeKumaClient into preflight_validator.py
  8. Wire ProxyHealthMonitor into proxy_manager.py
  9. Wire TechStackDetector into target_discovery.py

Phase 4 — New integrations (8-12h):
  10. n8n + webhook endpoints in titan_api.py
  11. Grafana + Prometheus + metrics exporter
  12. Changedetection.io + webhook receiver
  13. SearXNG + client in titan_web_intel.py
```

---

## RAM BUDGET (32GB VPS)

| Service | RAM | Status |
|---|---|---|
| Debian 12 OS | ~1GB | Running |
| Ollama (3 models loaded) | ~14GB | Running |
| Redis | ~50MB | Running |
| ntfy | ~30MB | Running |
| Xray | ~20MB | Running |
| ChromaDB (PersistentClient) | ~500MB | After pip install |
| sentence-transformers | ~500MB | After pip install |
| **Subtotal (current)** | **~16GB** | |
| Uptime Kuma (Docker) | ~30MB | Phase 2 |
| Open WebUI (Docker) | ~200MB | Phase 2 |
| Dozzle (Docker) | ~20MB | Phase 2 |
| n8n (Docker) | ~250MB | Phase 4 |
| Grafana + Prometheus (Docker) | ~350MB | Phase 4 |
| Changedetection.io (Docker) | ~100MB | Phase 4 |
| SearXNG (Docker) | ~100MB | Phase 4 |
| **Total projected** | **~17.5GB** | Leaves ~14GB headroom |

VPS has plenty of headroom for all services.

---

## V9.1 IMPLEMENTATION STATUS (code written)

All modules below have been implemented. Every integration is **optional** —
falls back gracefully if the Docker service is not deployed.

### New Env Vars (add to `/opt/titan/config/titan.env`):

```bash
# SearXNG (Docker one-click)
TITAN_SEARXNG_URL=http://127.0.0.1:8888

# FlareSolverr (Docker one-click)
TITAN_FLARESOLVERR_URL=http://127.0.0.1:8191

# Prometheus exporter port (auto-started)
TITAN_PROMETHEUS_PORT=9200

# Webhook server port (receives from Changedetection/n8n/Kuma)
TITAN_WEBHOOK_PORT=9300
```

### Files Modified:

| File | Change |
|---|---|
| `payment_success_metrics.py` | +`TitanPrometheusExporter` class, `start_prometheus_exporter()`, serves `:9200/metrics` |
| `titan_web_intel.py` | +`_search_searxng()` provider (priority 0), auto-fallback to existing providers |
| `target_discovery.py` | +FlareSolverr CF bypass in `probe_site()`, +Wappalyzer `TechStackDetector` wiring |
| `titan_session.py` | +Redis pub/sub in `save_session()` via existing `RedisClient` |
| `preflight_validator.py` | +`_check_service_health()` via `UptimeKumaClient`, +`ProxyHealthMonitor` scoring |
| `__init__.py` | +exports for webhook integrations + Prometheus exporter |

### New File:

| File | Purpose |
|---|---|
| `titan_webhook_integrations.py` | Flask webhook server receiving from Changedetection.io, n8n, Uptime Kuma |

### Webhook Endpoints (`:9300`):

| Endpoint | Source | Action |
|---|---|---|
| `POST /webhook/changedetection` | Changedetection.io | Routes to `track_defense_changes()` AI, sends ntfy alert |
| `POST /webhook/n8n/decline-retry` | n8n workflow | Runs `autopsy_decline()` AI, returns recommendation |
| `POST /webhook/n8n/target-recon` | n8n workflow | Runs `analyze_target()` AI, returns recon |
| `POST /webhook/n8n` | n8n generic | Logs and acknowledges |
| `POST /webhook/uptime-kuma` | Uptime Kuma | Forwards service up/down alerts to ntfy |
| `GET /webhook/events` | Debug | Lists recent webhook events |
| `GET /health` | Health check | Returns `{"status": "ok"}` |

### Previously Dead Code Now Wired:

| Client | Was Dead | Now Called From |
|---|---|---|
| `RedisClient` | ✅ | `titan_session.py` — pub/sub on every `save_session()` |
| `UptimeKumaClient` | ✅ | `preflight_validator.py` — `_check_service_health()` |
| `TechStackDetector` | ✅ | `target_discovery.py` — `probe_site()` Wappalyzer detection |
| `ProxyHealthMonitor` | ✅ | `preflight_validator.py` — `_check_proxy_connection()` enrichment |

### To Deploy:

```bash
# Phase 1: pip installs (VPS, no Docker needed)
pip install chromadb sentence-transformers python-Wappalyzer prometheus-client

# Phase 2: Docker one-click via Hostinger
#   - Uptime Kuma (:3001)
#   - Open WebUI (:3000)
#   - Dozzle (log viewer)

# Phase 3: Docker + configure webhook URLs
#   - SearXNG (:8888) → set TITAN_SEARXNG_URL
#   - FlareSolverr (:8191) → set TITAN_FLARESOLVERR_URL
#   - Changedetection.io → webhook URL: http://127.0.0.1:9300/webhook/changedetection
#   - n8n → webhook URLs: http://127.0.0.1:9300/webhook/n8n/*
#   - Uptime Kuma → notification webhook: http://127.0.0.1:9300/webhook/uptime-kuma

# Phase 4: Grafana + Prometheus
#   - Prometheus scrape target: http://127.0.0.1:9200/metrics
#   - Grafana data source: Prometheus at http://127.0.0.1:9090
```
