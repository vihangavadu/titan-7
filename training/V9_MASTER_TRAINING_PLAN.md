# TITAN V9.0 — MASTER TRAINING PLAN
## 57 AI Tasks | 17,100 Training Examples | 3 Fine-Tuned Models

---

## OVERVIEW

| Metric | Value |
|--------|-------|
| Total AI tasks | 57 |
| Examples per task | 300 |
| Total training examples | 17,100 |
| Models fine-tuned | 3 (titan-analyst, titan-strategist, titan-fast) |
| Training method | Ollama Modelfile (few-shot) + CPU LoRA fine-tuning |
| Hardware | AMD EPYC 9354P, 8 vCPU, 32GB DDR5, AVX-512 BF16 |
| Estimated total time | ~72-96 hours (all 3 models sequential) |

---

## EXECUTION PIPELINE

```
Phase 1: Generate Training Data          (~5 min)
    └→ 17,100 examples across 57 tasks → JSONL files

Phase 2: Build V9 Modelfiles             (~2 min)
    └→ 3 Modelfiles with comprehensive few-shot examples
    └→ ollama create titan-analyst/strategist/fast

Phase 3: LoRA Fine-Tuning                (~72-96h)
    └→ titan-analyst (23 tasks, ~6,900 examples, ~30h)
    └→ titan-strategist (21 tasks, ~6,300 examples, ~28h)
    └→ titan-fast (13 tasks, ~3,900 examples, ~16h)

Phase 4: Merge + Deploy                  (~30 min)
    └→ Merge LoRA → base model
    └→ Convert to GGUF
    └→ ollama create with V9 Modelfile
    └→ Verify all 57 tasks

Phase 5: Evaluate                        (~15 min)
    └→ Run evaluation suite on held-out test set
    └→ Compare V8.3 vs V9.0 accuracy per task
```

---

## ONE-COMMAND EXECUTION

```bash
# On VPS (72.62.72.48):
cd /opt/titan/training
bash run_v9_training.sh
```

This script:
1. Generates all training data
2. Rebuilds Ollama models with V9 Modelfiles
3. Launches LoRA fine-tuning for each model sequentially
4. Monitors progress with live logging

---

## TASK-TO-MODEL MAPPING (57 tasks)

### titan-analyst (23 tasks → qwen2.5:7b base)
| # | Task | Examples | Description |
|---|------|----------|-------------|
| 1 | bin_analysis | 300 | BIN intelligence with risk scoring |
| 2 | bin_generation | 300 | Generate BIN data for unknown BINs |
| 3 | target_recon | 300 | Merchant antifraud analysis |
| 4 | site_discovery | 300 | Find new viable targets |
| 5 | profile_audit | 300 | Browser profile quality scoring |
| 6 | persona_enrichment | 300 | Demographics generation |
| 7 | coherence_check | 300 | General coherence validation |
| 8 | preset_generation | 300 | Target preset JSON generation |
| 9 | country_profiles | 300 | Country payment landscape |
| 10 | fingerprint_coherence | 300 | Cross-signal fingerprint validation |
| 11 | identity_graph | 300 | Identity plausibility scoring |
| 12 | environment_coherence | 300 | IP/geo/locale/TZ validation |
| 13 | avs_prevalidation | 300 | Address format pre-check |
| 14 | live_target_scoring | 300 | Real-time target vulnerability |
| 15 | profile_optimization | 300 | Optimize profile per target |
| 16 | persona_consistency_check | 300 | Cross-validate persona fields |
| 17 | card_target_matching | 300 | Card-to-target compatibility |
| 18 | operation_pattern_mining | 300 | Hidden pattern discovery |
| 19 | autofill_data_generation | 300 | Realistic form data |
| 20 | tls_profile_selection | 300 | JA4 TLS profile per CDN |
| 21 | intel_synthesis | 300 | Web intel synthesis |
| 22 | storage_pattern_planning | 300 | IndexedDB pattern planning |
| 23 | hardware_profile_coherence | 300 | USB/HW tree validation |

### titan-strategist (21 tasks → deepseek-r1:8b base)
| # | Task | Examples | Description |
|---|------|----------|-------------|
| 1 | three_ds_strategy | 300 | 3DS bypass planning |
| 2 | operation_planning | 300 | End-to-end operation plan |
| 3 | detection_analysis | 300 | Detection pattern analysis |
| 4 | decline_analysis | 300 | Decline pattern correlation |
| 5 | preflight_advisor | 300 | Go/no-go decision |
| 6 | bug_analysis | 300 | Code reasoning + patches |
| 7 | session_rhythm | 300 | Per-target session timing |
| 8 | card_rotation | 300 | Card-target-timing optimization |
| 9 | velocity_schedule | 300 | Velocity limit scheduling |
| 10 | defense_tracking | 300 | Antifraud upgrade detection |
| 11 | decline_autopsy | 300 | Decline root cause + patches |
| 12 | cross_session | 300 | Cross-session pattern learning |
| 13 | copilot_abort_prediction | 300 | Predict failure 30-60s early |
| 14 | detection_root_cause | 300 | Deep detection log reasoning |
| 15 | first_session_warmup_plan | 300 | Targeted warmup planning |
| 16 | issuer_behavior_prediction | 300 | Predict issuer ML scoring |
| 17 | patch_reasoning | 300 | Auto-patch decision making |
| 18 | intel_prioritization | 300 | Intel feed prioritization |
| 19 | history_pattern_planning | 300 | 900-day browsing history |
| 20 | kyc_strategy | 300 | KYC bypass per provider |
| 21 | validation_strategy | 300 | Card validation approach |

### titan-fast (13 tasks → mistral:7b base)
| # | Task | Examples | Description |
|---|------|----------|-------------|
| 1 | behavioral_tuning | 300 | Ghost Motor param tuning |
| 2 | copilot_guidance | 300 | Real-time operator help |
| 3 | warmup_searches | 300 | Search query generation |
| 4 | dork_generation | 300 | Google dork generation |
| 5 | general_query | 300 | Fast Titan OS guidance |
| 6 | navigation_path | 300 | Browse-to-purchase journey |
| 7 | form_fill_cadence | 300 | Per-field typing timing |
| 8 | trajectory_tuning | 300 | Mouse dynamics per antifraud |
| 9 | biometric_profile_tuning | 300 | Biometric params per persona |
| 10 | cookie_value_generation | 300 | Realistic cookie values |
| 11 | detection_prediction | 300 | Real-time detection prediction |
| 12 | purchase_history_generation | 300 | Past purchase artifacts |
| 13 | ga_event_planning | 300 | GA event sequence planning |

---

## TRAINING HYPERPARAMETERS

### LoRA Configuration (all models)
| Parameter | Value | Rationale |
|-----------|-------|-----------|
| LoRA rank (r) | 16 | Higher rank for 57-task coverage |
| LoRA alpha | 32 | Scaling factor 2x |
| LoRA dropout | 0.05 | Light regularization |
| Target modules | q,k,v,o_proj | All attention projections |
| Learning rate | 1.5e-4 | Slightly lower for stability |
| LR scheduler | cosine | Smooth decay |
| Warmup ratio | 0.05 | 5% warmup steps |
| Epochs | 4 | 4 epochs for convergence |
| Effective batch | 8 | micro=1, grad_accum=8 |
| Max seq length | 1536 | Longer for complex JSON |
| Compute dtype | BFloat16 | Native AVX-512 BF16 |
| Weight decay | 0.01 | Standard regularization |
| Max grad norm | 1.0 | Gradient clipping |

### Training Data Quality
| Feature | Value |
|---------|-------|
| Chain-of-thought | Every response has `reasoning` field |
| Hard negatives | 30% adversarial examples per task |
| Edge cases | 10% extreme/boundary examples |
| Score distribution | Full range (0-100), not clustered |
| JSON validation | 100% valid JSON responses |
| Multi-signal | Responses correlate multiple inputs |
