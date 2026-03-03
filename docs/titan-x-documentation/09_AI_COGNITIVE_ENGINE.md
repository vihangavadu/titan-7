# 09 — AI Cognitive Engine

**4-Model ONNX Architecture — 67 Task Routes — Real-Time Copilot — Cognitive Latency Injection**

Titan X embeds a full AI cognitive layer that provides real-time decision making, risk assessment, persona enrichment, detection analysis, CAPTCHA solving, and operator guidance. The system uses 4 local ONNX INT4 models (4.65GB total RAM) with cloud LLM fallback, routing 67 distinct AI tasks to the optimal model based on task characteristics.

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                    AI COGNITIVE ARCHITECTURE                       │
│                                                                    │
│  ┌─────────────────────────────────────────────────────────┐     │
│  │                   TASK ROUTER (67 tasks)                  │     │
│  │  llm_config.json → maps task → best model + provider     │     │
│  └───────────┬──────────┬──────────┬──────────┬────────────┘     │
│              │          │          │          │                    │
│              ▼          ▼          ▼          ▼                    │
│  ┌──────────┐ ┌────────┐ ┌──────────┐ ┌──────────┐             │
│  │  FLASH   │ │ANALYST │ │STRATEGIST│ │ OPERATOR │             │
│  │ Qwen2.5  │ │Qwen2.5 │ │ Phi-3.5  │ │ SmolLM2  │             │
│  │  0.5B    │ │  1.5B  │ │  3.8B    │ │  1.7B    │             │
│  │  350MB   │ │  1GB   │ │  2.2GB   │ │  1.1GB   │             │
│  │   <1s    │ │  ~2s   │ │   ~4s    │ │   ~2s    │             │
│  └──────────┘ └────────┘ └──────────┘ └──────────┘             │
│       ↑            ↑           ↑            ↑                    │
│       │            │           │            │                    │
│  ┌────┴────────────┴───────────┴────────────┴────┐              │
│  │              ONNX Runtime (CPU-only)            │              │
│  │         Zero Ollama overhead, native inference  │              │
│  └────────────────────────────────────────────────┘              │
│                            │                                      │
│                    ┌───────┴───────┐                              │
│                    │  FALLBACK     │                              │
│                    │ Ollama → vLLM │                              │
│                    │ → OpenAI →    │                              │
│                    │ Anthropic →   │                              │
│                    │ Groq → Rules  │                              │
│                    └───────────────┘                              │
└──────────────────────────────────────────────────────────────────┘
```

---

## The 4 Models

### titan-flash (Qwen2.5-0.5B-Instruct)

| Property | Value |
|----------|-------|
| **Base** | Qwen2.5-0.5B-Instruct |
| **Format** | ONNX INT4 |
| **Size** | 350MB |
| **Context** | 32,768 tokens |
| **Response** | <1 second |
| **Strengths** | Speed, generation, warmup content, cookie values, behavioral tuning |
| **Path** | `/opt/titan/models/flash` |

**Primary tasks** (13 total): `copilot_guidance`, `warmup_searches`, `dork_generation`, `general_query`, `navigation_path`, `form_fill_cadence`, `behavioral_tuning`, `trajectory_tuning`, `biometric_profile_tuning`, `cookie_value_generation`, `purchase_history_generation`, `ga_event_planning`, `detection_prediction`

**Use case**: Any task where sub-second response matters more than deep reasoning. Generates warmup search queries, cookie values, navigation paths, and behavioral parameters in real-time during operations.

### titan-analyst (Qwen2.5-1.5B-Instruct)

| Property | Value |
|----------|-------|
| **Base** | Qwen2.5-1.5B-Instruct |
| **Format** | ONNX INT4 |
| **Size** | 1GB |
| **Context** | 32,768 tokens |
| **Response** | ~2 seconds |
| **Strengths** | Structured output, JSON extraction, BIN analysis, profile validation, coherence checks |
| **Path** | `/opt/titan/models/analyst` |

**Primary tasks** (23 total): `bin_analysis`, `bin_generation`, `target_recon`, `site_discovery`, `profile_audit`, `persona_enrichment`, `coherence_check`, `preset_generation`, `country_profiles`, `fingerprint_coherence`, `identity_graph`, `environment_coherence`, `avs_prevalidation`, `live_target_scoring`, `profile_optimization`, `persona_consistency_check`, `card_target_matching`, `operation_pattern_mining`, `autofill_data_generation`, `tls_profile_selection`, `intel_synthesis`, `storage_pattern_planning`, `hardware_profile_coherence`

**Use case**: Any task requiring structured JSON output, data extraction, or validation scoring. The analyst excels at parsing BIN data, scoring profile quality, and validating cross-signal consistency.

### titan-strategist (Phi-3.5-mini-instruct)

| Property | Value |
|----------|-------|
| **Base** | Phi-3.5-mini-instruct |
| **Format** | ONNX INT4 |
| **Size** | 2.2GB |
| **Context** | 131,072 tokens |
| **Response** | ~4 seconds |
| **Strengths** | Strategy, risk analysis, multi-step planning, detection analysis, deep reasoning |
| **Path** | `/opt/titan/models/strategist` |

**Primary tasks** (21 total): `three_ds_strategy`, `operation_planning`, `detection_analysis`, `decline_analysis`, `preflight_advisor`, `bug_analysis`, `session_rhythm`, `card_rotation`, `velocity_schedule`, `defense_tracking`, `decline_autopsy`, `cross_session`, `copilot_abort_prediction`, `detection_root_cause`, `first_session_warmup_plan`, `issuer_behavior_prediction`, `patch_reasoning`, `intel_prioritization`, `history_pattern_planning`, `kyc_strategy`, `validation_strategy`

**Use case**: Complex multi-factor reasoning. The strategist has 128K context (largest of all 4 models) enabling it to process full operation logs, cross-reference decline patterns, and produce multi-step strategies. Used for 3DS bypass planning, issuer behavior prediction, and detection root cause analysis.

### titan-operator (SmolLM2-1.7B-Instruct)

| Property | Value |
|----------|-------|
| **Base** | SmolLM2-1.7B-Instruct |
| **Format** | ONNX INT4 |
| **Size** | 1.1GB |
| **Context** | 8,192 tokens |
| **Response** | ~2 seconds |
| **Strengths** | Human reasoning, situation assessment, instinct, timing, abort decisions |
| **Path** | `/opt/titan/models/operator` |

**Primary tasks** (12 total): `situation_assessment`, `decline_diagnosis`, `target_selection`, `daily_planning`, `emergency_response`, `session_timing`, `amount_optimization`, `ip_proxy_selection`, `fingerprint_check`, `profile_readiness`, `post_op_analysis`, `operator_intel_priority`

**Use case**: The "gut feel" model. Thinks like a seasoned human operator — cautious, adaptive, instinct-driven. Makes split-second decisions during live operations: "abort now", "lower the amount", "switch proxy", "wait 30 seconds". Also handles daily planning and post-operation analysis.

---

## Task Routing System

### Configuration (`llm_config.json`)

Every AI function maps to the optimal model:

```json
{
  "task_routing": {
    "bin_analysis": [
      {"provider": "ollama", "model": "titan-analyst", "_reason": "Structured BIN data extraction + JSON"}
    ],
    "three_ds_strategy": [
      {"provider": "ollama", "model": "titan-strategist", "_reason": "3DS multi-factor risk reasoning"}
    ],
    "copilot_guidance": [
      {"provider": "ollama", "model": "titan-flash", "_reason": "Fast real-time operator guidance"}
    ],
    "situation_assessment": [
      {"provider": "onnx", "model": "titan-operator", "_reason": "Human-like gut-feel assessment"}
    ]
  }
}
```

### Routing Logic

```python
def route_task(task_name: str) -> Tuple[str, str]:
    """Returns (provider, model) for the given task."""
    routes = config["task_routing"].get(task_name, config["task_routing"]["default"])
    
    for route in routes:
        provider = route["provider"]
        model = route["model"]
        
        if provider == "onnx" and onnx_available(model):
            return ("onnx", model)
        elif provider == "ollama" and ollama_available(model):
            return ("ollama", model)
    
    # Fallback chain
    return fallback_provider()
```

### Fallback Chain

```
1. ONNX local (titan-flash/analyst/strategist/operator)
2. Ollama local (same models via Ollama serving)
3. vLLM cloud (self-hosted Llama-3-70B AWQ)
4. OpenAI (gpt-4o-mini)
5. Anthropic (claude-3.5-sonnet)
6. Groq (llama-3.1-70b-versatile)
7. Rule-based engine (keyword matching heuristics)
```

Success rate degrades at each fallback level: ONNX/Ollama ~95% → Cloud ~90% → Rules ~70%.

---

## Per-App AI Assignment

Each GUI app uses specific models for its functions:

### Operations Center (`titan_operations.py`)

| Primary Model | Tasks |
|--------------|-------|
| titan-analyst | `persona_enrichment`, `coherence_check`, `profile_audit`, `bin_analysis`, `fingerprint_coherence`, `identity_graph`, `form_fill_cadence`, `persona_consistency_check`, `profile_optimization` |

**Why analyst**: Operations needs structured validation — JSON scoring of personas, profiles, BINs, and cross-signal consistency.

### Intelligence Center (`titan_intelligence.py`)

| Primary Model | Secondary | Tasks |
|--------------|-----------|-------|
| titan-strategist | titan-fast | `operation_planning`, `three_ds_strategy`, `detection_analysis`, `decline_analysis`, `copilot_guidance`, `defense_tracking`, `decline_autopsy`, `cross_session`, `copilot_abort_prediction`, `detection_root_cause`, `live_target_scoring`, `intel_prioritization`, `intel_synthesis`, `operation_pattern_mining` |

**Why strategist**: Intelligence is the brain — deep reasoning for strategy, predictions, and pattern mining. Flash handles fast copilot guidance.

### Profile Forge (`app_profile_forge.py`)

| Primary Model | Secondary | Tasks |
|--------------|-----------|-------|
| titan-analyst | titan-strategist | `profile_audit`, `fingerprint_coherence`, `identity_graph`, `session_rhythm`, `navigation_path`, `profile_optimization`, `persona_consistency_check`, `history_pattern_planning`, `autofill_data_generation`, `cookie_value_generation`, `storage_pattern_planning`, `purchase_history_generation`, `ga_event_planning` |

**Why analyst**: Profile Forge is the most AI-intensive app — generates, validates, and optimizes every aspect of identity. 13 AI tasks, more than any other app.

### Card Validator (`app_card_validator.py`)

| Primary Model | Secondary | Tasks |
|--------------|-----------|-------|
| titan-analyst | titan-strategist | `bin_analysis`, `card_rotation`, `velocity_schedule`, `avs_prevalidation`, `three_ds_strategy`, `card_target_matching`, `validation_strategy`, `issuer_behavior_prediction` |

**Why analyst+strategist**: Card lifecycle needs both structured analysis (BIN scoring) and strategic reasoning (issuer prediction, rotation planning).

### Browser Launch (`app_browser_launch.py`)

| Primary Model | Secondary | Tasks |
|--------------|-----------|-------|
| titan-strategist | titan-fast | `preflight_advisor`, `environment_coherence`, `behavioral_tuning`, `session_rhythm`, `form_fill_cadence`, `trajectory_tuning`, `biometric_profile_tuning`, `first_session_warmup_plan`, `copilot_abort_prediction`, `detection_prediction`, `tls_profile_selection`, `hardware_profile_coherence` |

**Why strategist**: Browser Launch is mission-critical — preflight checks, warmup planning, real-time detection prediction. Flash handles fast behavioral parameter generation.

### KYC Studio (`app_kyc.py`)

| Primary Model | Tasks |
|--------------|-------|
| titan-strategist | `persona_enrichment`, `identity_graph`, `kyc_strategy` |

**Why strategist**: KYC bypass requires strategic planning per provider and challenge type.

### Admin Console (`titan_admin.py`)

| Primary Model | Tasks |
|--------------|-------|
| titan-strategist | `bug_analysis`, `detection_analysis`, `cross_session`, `patch_reasoning`, `operation_pattern_mining` |

**Why strategist**: Admin powers the self-healing loop — detection analysis, patch reasoning, pattern mining across sessions.

### Network Manager (`titan_network.py`)

| Primary Model | Tasks |
|--------------|-------|
| titan-fast | `general_query`, `environment_coherence`, `tls_profile_selection` |

**Why flash**: Network uses AI minimally — fast TLS profile selection per CDN/WAF and environment coherence checks.

### Settings (`app_settings.py`)

| Primary Model | Tasks |
|--------------|-------|
| titan-fast | `general_query` |

**Why flash**: Settings only uses AI for diagnostics queries.

---

## Cognitive Modes

### 1. ANALYSIS Mode (`cognitive_core.py`)

Analyzes page DOM and screenshots to identify form fields, security measures, trust signals, and risk indicators:

```python
response = await brain.analyze_context(
    dom_snippet="<form id='checkout'>...",
    screenshot_b64=screenshot_data
)
# Returns: {elements, security, trust_score, risks, recommendations}
```

### 2. DECISION Mode

Determines optimal next action based on page state:

```python
response = await brain.decide_action(
    page_state="Checkout page with shipping form visible",
    available_actions=["fill_address", "select_shipping", "go_back", "wait"]
)
# Returns: {action: "fill_address", confidence: 0.85, reasoning: "..."}
```

### 3. CAPTCHA Mode (Multimodal)

Solves CAPTCHAs using vision + text analysis:

| CAPTCHA Type | Method | Confidence |
|-------------|--------|-----------|
| Text CAPTCHA | OCR-style character recognition | 85-92% |
| Image selection | Multi-class image classification | 80-88% |
| Slider CAPTCHA | Edge detection for slider position | 90-95% |
| Puzzle CAPTCHA | Template matching for missing piece | 85-90% |

### 4. RISK Mode

Real-time transaction risk assessment:

```python
response = await brain.assess_risk(
    bin_data={"bin": "414720", "type": "credit", "level": "signature"},
    merchant_info={"name": "Amazon", "country": "US"},
    transaction_history=[{"amount": 49.99, "days_ago": 30}]
)
# Returns: {risk_score: 25, risk_factors: [...], recommendation: "proceed"}
```

### 5. CONVERSATION Mode

Natural language generation for customer service interactions, verification questions, and account recovery:

```python
response = await brain.generate_response(
    conversation_context="Agent: Can you verify your billing address?\n",
    persona="casual_user"
)
# Returns natural response matching persona style and demographic
```

---

## Human Cognitive Latency Injection

One of Titan's most critical anti-detection mechanisms. AI inference is too fast — 150ms response looks like a bot.

```python
# LLM responds in ~150ms
inference_latency = 147  # ms

# Human thinks for 200-450ms
required_total = random.uniform(200, 450)  # e.g., 320ms

# Add delay to match human timing
additional_delay = required_total - inference_latency  # 173ms
await asyncio.sleep(additional_delay / 1000)

# Total visible latency: 147 + 173 = 320ms (human-like)
```

Every AI-driven action in the browser (click, type, scroll, navigate) has this latency injection applied. Timing-based bot detection sees human-speed responses.

---

## Real-Time Copilot (`titan_realtime_copilot.py`)

### Event Pipeline

```
Browser Extension → sendBeacon('/api/copilot/event') →
Flask API → Event Parser → AI Task Router →
titan-flash (guidance) / titan-operator (decisions) →
Guidance Queue → GUI Dashboard / ntfy Push
```

### Event Types

| Event | Source | AI Task |
|-------|--------|---------|
| `page_load` | TX Monitor extension | `situation_assessment` |
| `form_detected` | TX Monitor extension | `form_fill_cadence` |
| `captcha_detected` | TX Monitor extension | CAPTCHA solving mode |
| `3ds_challenge` | TX Monitor extension | `emergency_response` |
| `fraud_score_change` | TX Monitor extension | `detection_prediction` |
| `decline` | TX Monitor extension | `decline_diagnosis` |
| `checkout_start` | TX Monitor extension | `session_timing` |
| `order_success` | TX Monitor extension | `post_op_analysis` |

### Guidance Output Format

```json
{
  "timestamp": "2026-03-15T14:32:15Z",
  "type": "guidance",
  "priority": "high",
  "message": "Fraud score dropped to 82. Slow down form filling. Add 3-second pause before payment submission.",
  "action": "adjust_pace",
  "confidence": 0.88,
  "model": "titan-operator"
}
```

---

## Detection Gap Analysis

The AI layer closes 8 critical detection gaps that static rules cannot address:

| # | Detection Gap | AI Solution | Model | Impact |
|---|--------------|------------|-------|--------|
| 1 | Behavioral biometrics | `trajectory_tuning` + `biometric_profile_tuning` | flash | Adapts Ghost Motor per antifraud engine |
| 2 | First-session bias (15% of failures) | `first_session_warmup_plan` | strategist | Plans targeted warmup to eliminate bias |
| 3 | Issuer ML scoring (35% of declines) | `issuer_behavior_prediction` | strategist | Predicts bank scoring response |
| 4 | Profile inconsistency | `persona_consistency_check` | analyst | Cross-validates 40+ identity signals |
| 5 | Wrong card+target combo | `card_target_matching` | analyst | Scores compatibility from history |
| 6 | TLS fingerprint mismatch | `tls_profile_selection` | analyst | Selects JA4 profile per CDN/WAF |
| 7 | Unrealistic browser history | `history_pattern_planning` | strategist | Plans 900-day history per persona |
| 8 | Late detection response | `detection_prediction` | flash | Predicts detection 30s before trigger |

---

## Vector Memory (`titan_vector_memory.py`)

Long-term operational knowledge storage using vector embeddings:

| Feature | Detail |
|---------|--------|
| **Storage** | ChromaDB or FAISS local vector database |
| **Embedding** | Sentence-transformers (all-MiniLM-L6-v2) |
| **Capacity** | 100K+ entries |
| **Query** | Semantic similarity search |

**Stored knowledge types**:
- Decline patterns (BIN + target + time → outcome)
- Target intelligence (antifraud changes, threshold updates)
- Successful strategies (what worked, when, why)
- Detection events (what triggered detection, how to avoid)
- Operator notes (manual observations and tips)

**Retrieval**: Before every operation, the AI queries vector memory for relevant past experience:

```python
similar = memory.search("Amazon US Visa signature 3DS", top_k=5)
# Returns 5 most relevant past operations for context
```

This gives the AI "experience" — it learns from past operations and adapts strategy accordingly.

---

## Rule-Based Fallback (`CognitiveCoreLocal`)

When no LLM is available, pure keyword matching and heuristic rules:

### DOM Analysis Rules

```python
if "captcha" in dom → "captcha_detected"
if "3d secure" in dom → "3ds_challenge"
if "declined" in dom → "error_state_detected"
if "suspicious" in dom → "fraud_detection_triggered"
if "order confirm" in dom → "order_likely_successful"
```

### Risk Assessment Rules

```python
if card_type == "prepaid": risk += 30
if card_type == "debit": risk += 10
if card_level in ("platinum", "signature"): risk -= 10
if bin_prefix in ("34", "37"): risk += 10  # Amex
if card_country != merchant_country: risk += 15
if len(history) > 3: risk += 10
```

**Success rate**: ~70% with rules vs ~95% with full AI models.

---

## Training & Fine-Tuning

### Training Data

| Model | Training Examples | Task Coverage |
|-------|------------------|---------------|
| titan-analyst | 6,900 examples | 23 tasks × 300 |
| titan-strategist | 6,300 examples | 21 tasks × 300 |
| titan-flash | 3,900 examples | 13 tasks × 300 |
| titan-operator | 3,600 examples | 12 tasks × 300 |
| **Total** | **20,700 examples** | **67 tasks** |

### Training Method

- **Technique**: QLoRA fine-tuning (4-bit quantized LoRA)
- **Hardware**: NVIDIA RTX 3090 Ti (24GB VRAM) via Vast.ai
- **LoRA config**: r=16, alpha=32, 4 epochs
- **Output**: ONNX INT4 quantized models for CPU-only inference

### Model Update Cycle

1. Collect operation logs and outcomes
2. Generate new training examples from successful/failed operations
3. Fine-tune on Vast.ai GPU ($0.064/hr)
4. Quantize to ONNX INT4
5. Deploy to `/opt/titan/models/`
6. Validate with benchmark suite
7. Update `llm_config.json` if task routing changes

---

## Performance Budget

| Resource | Allocation | Notes |
|----------|-----------|-------|
| Total AI RAM | 4.65GB | Down from 9GB in V9.0 |
| Flash inference | <1s | Real-time tasks |
| Analyst inference | ~2s | Acceptable for pre-operation |
| Strategist inference | ~4s | Background planning tasks |
| Operator inference | ~2s | Quick decisions during ops |
| LLM cache TTL | 24 hours | Repeated queries cached |
| Cache directory | `/opt/titan/data/llm_cache` | Disk-based caching |

### Global Settings

```json
{
  "global": {
    "default_temperature": 0.3,
    "default_max_tokens": 8192,
    "log_prompts": false,
    "log_responses": false
  }
}
```

Low temperature (0.3) ensures consistent, deterministic outputs. Prompt/response logging disabled by default for forensic safety — can be enabled for debugging.

---

*Document 09 of 11 — Titan X Documentation Suite — V10.0 — March 2026*
