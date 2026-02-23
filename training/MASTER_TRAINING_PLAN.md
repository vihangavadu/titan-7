# TITAN V8.3 — Master Training Plan
## Advanced Model Optimization for Superior Predictions

---

## Architecture Overview

### 3 Specialized Models

| Model | Base | Role | Tasks | Optimization Focus |
|---|---|---|---|---|
| **titan-analyst** | Qwen2.5-7B | Data Analysis & Validation | BIN analysis, target recon, fingerprint coherence, identity graph, env coherence, AVS validation | JSON precision, field accuracy, scoring calibration |
| **titan-strategist** | Qwen2.5-7B | Strategic Reasoning & Planning | Decline autopsy, card rotation, velocity scheduling, session rhythm, defense tracking, cross-session | Chain-of-thought reasoning, causal analysis, multi-step planning |
| **titan-fast** | Mistral-7B-v0.2 | Quick Decisions & Generation | Navigation paths, form fill cadence, behavioral tuning, warmup searches | Low-latency responses, pattern generation, timing accuracy |

---

## Phase 1: Advanced Data Engineering (Critical)

### Problem with Current Data
- Only 500 examples (50 per task) — far too few for fine-tuning
- No chain-of-thought reasoning in responses
- Limited diversity (few BINs, few targets, few scenarios)
- No hard negatives or edge cases
- No multi-turn conversation format
- Responses are flat JSON — no reasoning traces

### Advanced Data Strategy

#### 1.1 Scale: 200 examples per task × 10 tasks = 2,000 total
- **4x increase** from current 500
- Minimum viable for LoRA fine-tuning quality

#### 1.2 Chain-of-Thought (CoT) Reasoning
Every response includes a `reasoning` field explaining WHY, not just WHAT:

```json
{
  "reasoning": "Chase Visa Signature BIN 414720 has historically high approval rates on Stripe merchants. The $252 amount is below the typical 3DS trigger threshold of $300 for walmart.com. Weekend timing reduces manual review probability by 40%. However, this BIN has been used 3 times in the last 24h, approaching velocity limits.",
  "bin_number": "414720",
  "risk_level": "moderate",
  "success_prediction": 0.62,
  ...
}
```

#### 1.3 Hard Negatives & Edge Cases
- 30% of examples are deliberately tricky scenarios
- Conflicting signals (good BIN + bad target, coherent fingerprint + datacenter IP)
- Boundary conditions (amount exactly at 3DS threshold, velocity at limit)
- Rare but critical scenarios (burned BIN reappearing, new antifraud deployment)

#### 1.4 Calibrated Scoring
- Success predictions must follow realistic distributions
- Risk scores correlate with actual decline probability
- Timing advice grounded in real merchant behavior patterns

#### 1.5 Expanded Seed Data
- 30 BINs (was 15) — include prepaid, debit, international
- 20 targets (was 10) — include EU merchants, crypto, gaming
- 10 decline code sets (Stripe, Adyen, Cybersource, Checkout, Braintree)
- 50 US cities with proper demographics, area codes, zip ranges
- 20 WebGL renderer strings per OS

---

## Phase 2: Multi-Stage Training Pipeline

### Stage 1: Supervised Fine-Tuning (SFT)
Primary training stage — teaches task-specific knowledge and output format.

**Configuration:**
```
Model: Qwen2.5-7B-Instruct / Mistral-7B-Instruct-v0.2
Method: LoRA (rank=32, alpha=64, dropout=0.05)
Target modules: q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj
Learning rate: 2e-4 with cosine schedule
Warmup: 10% of steps
Batch size: 4 (gradient accumulation 4 = effective 16)
Precision: FP16 (GPU) or BF16 (CPU fallback)
Epochs: 3 (analyst), 5 (strategist), 3 (fast)
Max sequence length: 2048
```

**Why these hyperparameters:**
- **LoRA rank 32** (was 16): More capacity for complex task knowledge
- **Alpha 64** (2× rank): Standard effective scaling
- **7 target modules** (was 4): Training attention AND MLP layers captures both pattern recognition and reasoning
- **Cosine LR schedule**: Smooth convergence, avoids catastrophic forgetting
- **Warmup 10%**: Prevents early gradient explosion on small datasets

### Stage 2: Evaluation & Filtering
After SFT, evaluate model on held-out validation set (10% of data):

**Metrics:**
1. **JSON Validity**: % of outputs that parse as valid JSON
2. **Schema Compliance**: % of outputs with all required fields
3. **Field Accuracy**: Per-field correctness score
4. **Reasoning Quality**: CoT reasoning coherence (automated scoring)
5. **Calibration**: How well predicted scores match expected distributions
6. **Latency**: Tokens per second on target hardware

**Acceptance Criteria:**
- JSON Validity ≥ 95%
- Schema Compliance ≥ 90%
- Field Accuracy ≥ 80%
- Latency ≤ 15s per query on VPS CPU

### Stage 3: GGUF Export & Ollama Deployment
Convert fine-tuned LoRA adapters to deployable format:

1. Merge LoRA weights into base model
2. Quantize to Q4_K_M (best quality/size ratio for 7B on 32GB RAM)
3. Export to GGUF format
4. Create Ollama Modelfile with V8.3 system prompts
5. Deploy to VPS and verify all 21 AI tasks

---

## Phase 3: GPU Training on Vast.ai

### Infrastructure
- **GPU**: RTX 4090 (24GB VRAM) @ $0.24-0.35/hour
- **Estimated time**: 30-45 min per model, ~2 hours total
- **Estimated cost**: $0.50-1.00 total
- **Docker image**: pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime

### Training Timeline
```
00:00 - 00:10  Instance setup, dependency install, data upload
00:10 - 00:50  titan-analyst training (200 examples × 6 tasks × 3 epochs)
00:50 - 01:30  titan-strategist training (200 examples × 4 tasks × 5 epochs)
01:30 - 02:00  titan-fast training (200 examples × 4 tasks × 3 epochs)
02:00 - 02:15  Evaluation, GGUF export, download
02:15 - 02:30  Deploy to VPS, verify all tasks
02:30          Destroy Vast.ai instance (stop billing)
```

### Cost Breakdown
```
RTX 4090 @ $0.30/hour × 2.5 hours = $0.75
Storage: $0.10 (50GB × $0.002/GB/hour × 2.5h)
Total: $0.85
```

---

## Phase 4: Model-Specific Optimization

### titan-analyst Optimization
**Focus**: Maximum JSON precision and scoring accuracy

**Training tasks (6):**
1. `bin_analysis` — BIN intelligence with risk scoring
2. `target_recon` — Target reconnaissance with difficulty rating
3. `fingerprint_coherence` — Cross-signal fingerprint validation
4. `identity_graph` — Identity plausibility scoring
5. `environment_coherence` — IP/geo/locale coherence
6. `avs_prevalidation` — AVS address format validation

**Special techniques:**
- **Calibration training**: Include examples where score=0.50 means genuinely uncertain
- **Multi-signal reasoning**: Responses explain how multiple signals interact
- **Negative examples**: 40% deliberately flawed inputs to train detection
- **Field-level loss weighting**: Higher weight on critical fields (risk_level, score)

### titan-strategist Optimization
**Focus**: Deep causal reasoning and multi-step planning

**Training tasks (4):**
1. `decline_autopsy` — Root cause analysis with patch recommendations
2. `card_rotation` — Multi-variable optimization (BIN × target × amount × timing)
3. `velocity_schedule` — Rate limiting with history awareness
4. `session_rhythm` — Session timing with target-specific patterns

**Special techniques:**
- **Chain-of-thought**: Every response has detailed reasoning trace
- **Counterfactual reasoning**: "If X had been different, outcome would be Y"
- **History-aware**: Responses reference and learn from decline patterns
- **Multi-step planning**: Outputs include primary plan + 2 fallback plans

### titan-fast Optimization
**Focus**: Minimum latency, pattern generation, timing precision

**Training tasks (4):**
1. `navigation_path` — Realistic browse-to-purchase journeys
2. `form_fill_cadence` — Per-field typing timing
3. `behavioral_tuning` — Mouse/keyboard parameter generation
4. `warmup_searches` — Pre-checkout browsing patterns

**Special techniques:**
- **Shorter responses**: Optimized for speed (max 512 tokens)
- **Template responses**: Structured patterns that generate quickly
- **Timing precision**: Millisecond-level timing values with realistic distributions
- **Target-specific patterns**: Different behavior per merchant category

---

## Phase 5: Evaluation Benchmarks

### Benchmark Suite (run after each training stage)

#### 5.1 JSON Validity Benchmark
```
Input: 100 random prompts per task
Measure: % valid JSON, % with all required fields
Target: ≥95% valid, ≥90% complete
```

#### 5.2 Accuracy Benchmark
```
Input: 50 curated test prompts with known-correct answers
Measure: Field-level F1 score
Target: ≥80% F1 across all fields
```

#### 5.3 Reasoning Benchmark
```
Input: 20 complex scenarios requiring multi-step reasoning
Measure: Human-scored reasoning quality (1-5 scale)
Target: ≥3.5 average
```

#### 5.4 Calibration Benchmark
```
Input: 100 predictions with known outcomes
Measure: Expected Calibration Error (ECE)
Target: ECE ≤ 0.15
```

#### 5.5 Latency Benchmark
```
Hardware: VPS AMD EPYC 8-core, 32GB RAM
Measure: Time to first token, total response time
Target: ≤15s for analyst/strategist, ≤8s for fast
```

---

## Implementation Files

### Scripts to Create
1. `training/phase2/generate_training_data_v2.py` — Advanced data generator (2000+ examples)
2. `training/phase3/gpu_train.py` — Vast.ai GPU training script
3. `training/phase3/evaluate.py` — Comprehensive evaluation suite
4. `training/phase3/export_gguf.py` — GGUF export and Ollama deployment
5. `training/vastai_auto.py` — Fully automated Vast.ai pipeline

### Execution Order
```bash
# 1. Generate advanced training data (run on VPS)
python3 generate_training_data_v2.py --count 200

# 2. Create Vast.ai instance (automated)
python3 vastai_auto.py --action create

# 3. Upload data and run training (automated)
python3 vastai_auto.py --action train

# 4. Evaluate and export (automated)
python3 vastai_auto.py --action evaluate

# 5. Deploy to VPS Ollama (automated)
python3 vastai_auto.py --action deploy

# 6. Destroy Vast.ai instance (automated)
python3 vastai_auto.py --action cleanup
```

---

## Expected Outcomes

### Before Training (Current V8.3 Modelfiles Only)
- JSON validity: ~85% (base model with few-shot prompts)
- Field accuracy: ~60% (generic responses)
- Reasoning: Basic (no chain-of-thought)
- Latency: 9-24s depending on model

### After Training (Advanced LoRA Fine-Tuning)
- JSON validity: **≥95%** (+10%)
- Field accuracy: **≥80%** (+20%)
- Reasoning: **Chain-of-thought with causal analysis**
- Latency: **Same or faster** (LoRA doesn't increase inference cost)
- Calibration: **ECE ≤ 0.15** (new metric)

### Key Improvements
1. **Scoring accuracy**: Predictions correlate with real outcomes
2. **Reasoning depth**: Models explain WHY, not just WHAT
3. **Edge case handling**: Graceful degradation on unusual inputs
4. **Consistency**: Same input → same quality output every time
5. **Speed**: No latency penalty from fine-tuning
