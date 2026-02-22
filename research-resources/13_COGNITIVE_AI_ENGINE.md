# Cognitive AI Engine — Cloud Brain, CAPTCHA Solving & Decision Making

## Core Module: `cognitive_core.py` (613 lines)

The Cognitive Core is TITAN's AI brain — a cloud-hosted LLM that provides real-time decision making, CAPTCHA solving, risk assessment, and natural language generation during operations.

---

## Architecture: Cloud vLLM vs Local Ollama

### Cloud Mode (Primary)
- **Backend**: Self-hosted vLLM cluster with OpenAI-compatible API
- **Model**: AWQ-quantized Llama-3-70B or Qwen-2.5-72B
- **Latency**: ~150ms inference (sub-200ms with network)
- **Concurrency**: 50+ simultaneous agents via PagedAttention
- **Context window**: 32k tokens

### Local Fallback (Degraded)
- **Backend**: Ollama running locally
- **Model**: Llama-3-8B (smaller, faster, less capable)
- **Latency**: 1500-3000ms
- **Concurrency**: 1 (resource locked)
- **Context window**: 4k tokens

### Rule-Based Fallback (Minimal)
- **No LLM**: Pure keyword matching and heuristic rules
- **Success rate**: ~70% (vs 95% with cloud LLM)
- **Used when**: No cloud configured AND no local Ollama

---

## Cognitive Modes

### 1. ANALYSIS Mode
Analyzes page DOM/screenshots to identify:
- Form fields and their purposes
- Security measures (CAPTCHA, 2FA, 3DS indicators)
- Trust signals (SSL badges, reviews, security logos)
- Risk indicators (velocity warnings, fraud alerts)

```python
response = await brain.analyze_context(
    dom_snippet="<form id='checkout'>...",
    screenshot_b64=screenshot_data
)
# Returns: {elements, security, trust_score, risks, recommendations}
```

### 2. DECISION Mode
Determines the optimal next action based on page state:

```python
response = await brain.decide_action(
    page_state="Checkout page with shipping form visible",
    available_actions=["fill_address", "select_shipping", "go_back", "wait"]
)
# Returns: {action: "fill_address", confidence: 0.85, reasoning: "..."}
```

### 3. CAPTCHA Mode (Multimodal)
Solves CAPTCHAs using vision + text analysis:

```python
response = await brain.solve_captcha(
    captcha_image_b64=captcha_screenshot,
    captcha_type="text"  # or "image_selection", "slider", "puzzle"
)
# Returns: {captcha_type: "text", solution: "xK7m2P", confidence: 0.92}
```

Supported CAPTCHA types:
- **Text CAPTCHA**: OCR-style character recognition
- **Image selection**: "Select all images with traffic lights"
- **Slider CAPTCHA**: Identify correct slider position
- **Puzzle CAPTCHA**: Identify missing piece location

### 4. RISK Mode
Assesses transaction risk before proceeding:

```python
response = await brain.assess_risk(
    bin_data={"bin": "414720", "type": "credit", "level": "signature", "country": "US"},
    merchant_info={"name": "Amazon", "country": "US", "category": "electronics"},
    transaction_history=[{"amount": 49.99, "days_ago": 30}, ...]
)
# Returns: {risk_score: 25, risk_factors: [...], recommendation: "proceed", proceed: true}
```

### 5. CONVERSATION Mode
Generates natural human-like responses for:
- Customer service chat interactions
- Verification question answers
- Account recovery flows
- Phone verification scripts

```python
response = await brain.generate_response(
    conversation_context="Agent: Can you verify your billing address?\n",
    persona="casual_user"
)
# Returns natural response matching persona style
```

---

## Critical Feature: Human Cognitive Latency Injection

This is one of TITAN's most important anti-detection mechanisms. The problem:

- vLLM responds in ~150ms
- A human thinks for 200-450ms before acting
- If the system acts faster than 150ms, it's flagged as a bot

The solution:

```python
# After receiving LLM response:
inference_latency = (now - start_time).total_seconds() * 1000  # e.g., 147ms

# Calculate required delay to match human timing
required_delay = random.uniform(
    HUMAN_LATENCY_MIN,   # 200ms
    HUMAN_LATENCY_MAX    # 450ms
) - inference_latency    # e.g., 320ms - 147ms = 173ms additional delay

if required_delay > 0:
    await asyncio.sleep(required_delay / 1000)

# Total visible latency: 147ms + 173ms = 320ms (human-like)
```

This ensures every action taken by the system has a response time that falls within the human cognitive range, defeating timing-based bot detection.

---

## Local Fallback: Rule-Based Engine (`CognitiveCoreLocal`)

When no LLM is available, the system falls back to keyword-based heuristics:

### DOM Analysis Rules
```python
# Security detection
if "captcha" in dom: → "captcha_detected"
if "3d secure" in dom: → "3ds_challenge"
if "declined" in dom: → "error_state_detected"
if "suspicious" in dom: → "fraud_detection_triggered"

# Trust signals
if "ssl" or "secure checkout" in dom: trust_score += 10
if "mcafee" or "norton" in dom: trust_score += 5

# Page state
if "order confirm" or "thank you" in dom: → "order_likely_successful"
if "cart" and "empty" in dom: → "cart_emptied"
```

### Action Decision Rules
```python
priority_map = [
    ("captcha", "solve_captcha", 0.9),
    ("3d secure", "wait_3ds", 0.85),
    ("declined", "abort", 0.95),
    ("confirm", "confirm_order", 0.8),
    ("checkout", "proceed_checkout", 0.8),
    ("payment", "fill_payment", 0.8),
    ("address", "fill_address", 0.8),
]
```

### Risk Assessment Rules
```python
# Card type scoring
if card_type == "prepaid": risk += 30
if card_type == "debit": risk += 10

# Card level
if card_level in ("platinum", "signature"): risk -= 10

# Network
if bin_prefix[:2] in ("34", "37"): risk += 10  # Amex higher scrutiny

# Geography
if card_country != merchant_country: risk += 15

# Velocity
if len(history) > 3: risk += 10
```

---

## Configuration

Set in `/opt/titan/config/titan.env`:

```bash
# Cloud Brain (vLLM)
TITAN_CLOUD_URL=https://your-vllm-server.com/v1
TITAN_API_KEY=your-api-key
TITAN_MODEL=meta-llama/Meta-Llama-3-70B-Instruct

# Local Ollama (fallback)
OLLAMA_URL=http://127.0.0.1:11434/v1
OLLAMA_MODEL=llama3:8b
```

The system automatically detects which backend is available:
1. Try cloud vLLM → if configured and reachable, use it
2. Try local Ollama → if running, use it
3. Fall back to rule-based engine

---

## Statistics Tracking

```python
brain.get_stats()
# Returns:
{
    "connected": true,
    "endpoint": "https://vllm.example.com/v1",
    "model": "meta-llama/Meta-Llama-3-70B-Instruct",
    "total_requests": 47,
    "average_latency_ms": 312.5,
    "errors": 2,
    "error_rate": 4.26
}
```
