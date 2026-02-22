# TITAN OS V8.1 — AI Model Assignment Plan

## Overview

This document maps how AI models are assigned across the Titan OS architecture to maximize operation success rates, reduce failures, and provide real-time assistance to human operators.

**Primary AI Engine:** Ollama (local, `http://127.0.0.1:11434`)  
**Models:** `mistral:7b-instruct-v0.2-q4_0`, `qwen2.5:7b`, `deepseek-r1:7b`  
**Fallback Providers:** OpenAI, Anthropic, Groq, OpenRouter (via `ollama_bridge.py`)

---

## Architecture: How AI Flows Through an Operation

```
Human Operator starts operation
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│  integration_bridge.py :: full_prepare()                │
│  ├── AI Operations Guard (pre-flight)                   │
│  └── Real-Time Co-Pilot (begin_operation)               │
│      ├── MistakeDetector  (geo, velocity, burned cards) │
│      ├── TimingIntelligence (warmup, checkout countdown) │
│      ├── BIN Intelligence (ai_intelligence_engine.py)    │
│      └── OllamaAdvisor (deep reasoning if needed)       │
└─────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│  Browser launches with AI Co-Pilot extension            │
│  (titan_3ds_ai_exploits.py)                             │
│                                                          │
│  Browser sends real-time events via sendBeacon:          │
│    → state_change, checkout_detected, payment_active     │
│    → 3ds_detected, transaction_complete                  │
│    → antifraud_detected, page_visit                      │
│                                                          │
│  Events POST to → 127.0.0.1:8443/api/copilot/event     │
└─────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│  titan_realtime_copilot.py (background daemon)          │
│  Processes events, runs continuous checks every 5s:     │
│                                                          │
│  ├── Checkout countdown (warmup % → GO signal)          │
│  ├── Proxy health monitoring                             │
│  ├── Session duration warnings                           │
│  ├── Antifraud detection response                        │
│  ├── Velocity tracking across cards                      │
│  └── Ollama situational analysis at key moments          │
│                                                          │
│  Pushes guidance → GUI polls /api/v1/copilot/guidance   │
└─────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│  Post-Operation Analysis                                 │
│  ├── Decline code analysis (200+ codes across 6 PSPs)   │
│  ├── Burned card detection + tracking                    │
│  ├── Target failure tracking                             │
│  ├── Ollama deep decline reasoning                       │
│  ├── Next target suggestion (target_intel_v2)            │
│  ├── Vector memory storage (cross-session learning)      │
│  └── Operation result persisted to disk                  │
└─────────────────────────────────────────────────────────┘
```

---

## AI Module Assignment Table

| Module | File | AI Model Used | What It Does | When It Runs |
|--------|------|---------------|--------------|-------------|
| **Real-Time Co-Pilot** | `titan_realtime_copilot.py` | Ollama (mistral/qwen2.5) | Continuous monitoring daemon — timing, mistakes, guidance | Entire operation lifecycle |
| **AI Operations Guard** | `titan_ai_operations_guard.py` | Ollama (llama3:8b) | 4-phase guard: pre-op, session, checkout, post-op | Called by co-pilot at phase transitions |
| **AI Intelligence Engine** | `ai_intelligence_engine.py` | Ollama (mistral/qwen2.5) | BIN analysis, pre-flight advisor, target recon, 3DS strategy, profile audit, behavioral tuning | Pre-flight + on-demand |
| **Cognitive Core** | `cognitive_core.py` | OpenAI/Anthropic (cloud) | Complex reasoning with circuit breaker + hard timeout | On-demand for complex decisions |
| **Browser Co-Pilot** | `titan_3ds_ai_exploits.py` | Rule-based (JS) | 3DS iframe blocking, PSP detection, form monitoring, overlay | In-browser during session |
| **Transaction Monitor** | `transaction_monitor.py` | Rule-based | Captures all payment network requests, decodes 200+ decline codes | 24/7 listener on port 7443 |
| **LLM Bridge** | `ollama_bridge.py` | Multi-provider routing | Routes queries to best available model, caching, load balancing | Infrastructure layer |
| **Vector Memory** | `titan_vector_memory.py` | ChromaDB embeddings | Cross-session learning — stores operation results for semantic retrieval | Post-operation |
| **Target Intel V2** | `titan_target_intel_v2.py` | Rule-based + Ollama | Golden path scoring, PSP 3DS behavior database, geo enforcement | Pre-flight + post-op feedback |
| **Autonomous Engine** | `titan_autonomous_engine.py` | Ollama | 24/7 autonomous operation with self-patching | Autonomous mode only |
| **Agent Chain** | `titan_agent_chain.py` | LangChain + Ollama | Multi-step reasoning chains for complex tasks | On-demand |

---

## What AI Handles That Humans Cannot

### 1. TIMING PRECISION
- **Module:** `TimingIntelligence` (in `titan_realtime_copilot.py`)
- **What:** Precise warmup countdowns (60s–300s depending on target/antifraud), velocity spacing between cards, time-of-day optimization
- **Why humans fail:** Humans rush under pressure, can't count 127 seconds precisely, forget velocity cooldowns

### 2. PATTERN MEMORY
- **Module:** `titan_vector_memory.py` + `transaction_monitor.py`
- **What:** Remembers every operation result across sessions — which BINs work on which targets, which PSPs decline which card types
- **Why humans fail:** Humans forget which combinations failed, retry burned cards, repeat mistakes

### 3. MULTI-CHANNEL MONITORING
- **Module:** `RealtimeCopilot._run_continuous_checks()`
- **What:** Simultaneously monitors proxy health, fingerprint consistency, session timing, antifraud signals, card velocity — all in parallel
- **Why humans fail:** Humans can only focus on one thing at a time during checkout

### 4. DECLINE ANALYSIS
- **Module:** `OllamaRealtimeAdvisor.analyze_decline()` + `transaction_monitor.py`
- **What:** Instantly decodes decline codes, determines if card is burned vs. retriable, recommends next action
- **Why humans fail:** 200+ decline codes across 6 PSPs — impossible to memorize

### 5. ANTIFRAUD DETECTION RESPONSE
- **Module:** `MistakeDetector` + `TimingIntelligence`
- **What:** When Forter/Riskified/Sift detected, instantly adjusts warmup requirements (300s+ for enterprise antifraud)
- **Why humans fail:** Humans don't know which antifraud system requires what warmup duration

### 6. GEO MISMATCH DETECTION
- **Module:** `MistakeDetector.check_all()`
- **What:** Catches proxy country ≠ card country, proxy state ≠ billing state before checkout
- **Why humans fail:** Easy to overlook when managing multiple cards and proxies

---

## API Endpoints (Co-Pilot)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/copilot/event` | POST | No (sendBeacon) | Browser event ingestion |
| `/api/v1/copilot/guidance` | GET | Yes | Latest guidance messages |
| `/api/v1/copilot/dashboard` | GET | Yes | Full copilot status |
| `/api/v1/copilot/begin` | POST | Yes | Start operation + pre-flight |
| `/api/v1/copilot/end` | POST | Yes | End operation + post-analysis |
| `/api/v1/copilot/timing` | GET | Yes | Checkout countdown + velocity |
| `/api/v1/copilot/history` | GET | Yes | Session operation history |

---

## Auto-Start Configuration

The co-pilot auto-starts with all other services via `titan_services.py`:

```bash
# titan.env
TITAN_COPILOT_AUTOSTART=1    # Default: ON (always monitor operations)
```

Or manually:
```python
from titan_realtime_copilot import start_copilot, begin_op, get_guidance

copilot = start_copilot()
guidance = begin_op(target="cdkeys.com", card_bin="401200", card_country="US", amount=49.99)
# ... operation runs, browser events flow in automatically ...
latest = get_guidance()
```

---

## Ollama Model Routing (via ollama_bridge.py)

| Task Type | Preferred Model | Fallback | Temperature |
|-----------|----------------|----------|-------------|
| `situational_analysis` | mistral:7b | llama3:8b | 0.3 |
| `decline_analysis` | mistral:7b | qwen2.5:7b | 0.3 |
| `bin_analysis` | qwen2.5:7b | mistral:7b | 0.2 |
| `target_recon` | mistral:7b | deepseek-r1:7b | 0.3 |
| `3ds_strategy` | mistral:7b | llama3:8b | 0.2 |
| `profile_audit` | qwen2.5:7b | mistral:7b | 0.2 |
| `behavioral_tuning` | mistral:7b | qwen2.5:7b | 0.4 |

---

## Files Modified/Created

| File | Change |
|------|--------|
| `titan_realtime_copilot.py` | **NEW** — Real-time AI co-pilot daemon |
| `titan_api.py` | Added 7 copilot API routes + public endpoint for sendBeacon |
| `titan_3ds_ai_exploits.py` | Fixed sendBeacon URL from port 7700 → 8443 |
| `integration_bridge.py` | Wired co-pilot into `full_prepare()` operation flow |
| `__init__.py` | Registered co-pilot exports |
| `titan_services.py` | Added co-pilot to auto-start service manager |
