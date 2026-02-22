# 05 — App: Intelligence Center

## Overview

**File:** `src/apps/titan_intelligence.py`
**Color Theme:** Purple (#a855f7)
**Tabs:** 5
**Modules Wired:** 20 (8 previously orphaned, now connected)
**Purpose:** AI-powered analysis, strategy planning, detection research, and knowledge management.

The Intelligence Center is where the operator thinks before acting. It provides AI analysis, 3DS bypass strategy, detection pattern research, target reconnaissance, and persistent memory of past operations.

---

## Tab 1: AI COPILOT — Real-Time AI Guidance

### What This Tab Does
Interactive AI assistant that answers operational questions using local LLM models (Ollama). The operator asks questions in natural language and gets strategy recommendations.

### Features

**AI Query Interface**
- Text input for natural language questions
- Context field for providing additional operation details
- "Ask AI" button triggers `AIQueryWorker` background thread
- Response displayed in scrollable output panel

**AI Engine Integration**
- Primary: `ai_intelligence_engine.py` — `plan_operation(query)` returns structured `AIOperationPlan`
- Fallback: `ollama_bridge.py` — `OllamaBridge.query()` for general questions
- `TitanRealtimeCopilot` for operation-state-aware guidance

**LangChain Agent**
- `TitanAgent` (ReAct pattern) with tool access
- Can query vector memory, search web, analyze BINs mid-conversation
- Multi-step reasoning with intermediate tool calls
- Self-correcting on failed tool invocations

**AI Status Panel**
- Model availability (mistral:7b, qwen2.5:7b, deepseek-r1:8b)
- Ollama server status
- Context window usage
- Response latency

### What the Operator Inputs
| Input | Description | Example |
|-------|-------------|---------|
| Query | Natural language question | "What's the best approach for a Shopify store using Stripe with a UK Visa?" |
| Context | Additional operation context | "Card is platinum, billing is London, using Mullvad UK exit" |

### What the Operator Gets
| Output | Description |
|--------|-------------|
| AI Plan | Structured operation plan with steps |
| Strategy | Recommended approach with reasoning |
| Risk Assessment | Predicted success probability |
| Alternative Approaches | Fallback strategies if primary fails |

---

## Tab 2: 3DS STRATEGY — Bypass Planning & Exemptions

### What This Tab Does
Comprehensive 3D Secure analysis and bypass strategy planning. The operator enters card and merchant details to get a bypass plan.

### Features

**3DS Bypass Engine**
- `ThreeDSBypassEngine` calculates bypass probability per PSP
- `get_3ds_bypass_score(card, merchant)` → numerical score
- `get_3ds_bypass_plan(card, merchant)` → detailed strategy
- `get_downgrade_attacks()` — force 3DS1 instead of 3DS2
- `get_psp_vulnerabilities()` — known PSP weaknesses

**PSD2 Exemption Analysis**
- `get_psd2_exemptions()` — all applicable exemptions:
  - **TRA (Transaction Risk Analysis):** Thresholds at €100/€250/€500 based on acquirer fraud rate
  - **Low-Value:** Transactions below €30 (cumulative limit €100)
  - **Recurring:** Subsequent payments on established mandates
  - **MOTO:** Mail Order / Telephone Order (no SCA)
  - **One-Leg-Out:** Non-EU card on EU merchant = no SCA
- `TRAExemptionEngine.calculate()` — real-time TRA scoring

**Non-VBV Intelligence**
- `NonVBVRecommendationEngine` — finds cards not enrolled in 3DS
- `get_non_vbv_recommendations(country)` — country-specific non-VBV BINs
- `get_easy_countries()` — countries with weakest 3DS enforcement
- `get_all_non_vbv_bins()` — full database of non-VBV BINs

**Issuer Defense Analysis**
- `IssuerDefenseEngine` profiles per-issuer risk models
- `calculate_decline_risk(issuer, params)` — risk score per issuer
- `get_mitigation_strategy(issuer, decline_code)` — countermeasures
- Issuer comparison table showing risk thresholds

**AI 3DS Engine**
- `ThreeDSAIEngine` — AI-powered checkout co-pilot
- Real-time 3DS challenge prediction
- PSP auto-detection from page source

### What the Operator Inputs
| Input | Description | Example |
|-------|-------------|---------|
| Card BIN | First 6-8 digits | "453201" |
| Merchant PSP | Payment processor | "Stripe" |
| Amount | Transaction amount | "€85.00" |
| Card Country | Issuing country | "UK" |
| Merchant Country | Merchant location | "Germany" |

### What the Operator Gets
| Output | Description |
|--------|-------------|
| Bypass Score | 0-100 probability of bypassing 3DS |
| Bypass Plan | Step-by-step strategy |
| Exemptions | Applicable PSD2 exemptions |
| Issuer Risk | Per-issuer decline probability |
| Non-VBV Status | Whether card is enrolled in 3DS |

---

## Tab 3: DETECTION — Decline Analysis & Pattern Research

### What This Tab Does
Post-operation analysis of detection signals. Understanding what caused a decline or detection helps improve future operations.

### Features

**Detection Analyzer**
- `TitanDetectionAnalyzer.analyze(operation_log)` — full detection report
- Identifies which antifraud vector triggered detection
- Categories: fingerprint, behavioral, network, velocity, geo-mismatch, 3DS failure

**AI Operations Guard Review**
- `TitanAIOperationsGuard` 4-phase analysis review
- Phase 1 (Pre-Op): Were there geo-mismatches? BIN velocity issues?
- Phase 2 (Active): Session too short? Too few pages? Proxy latency spike?
- Phase 3 (Checkout): 3DS triggered unexpectedly? Amount over threshold?
- Phase 4 (Post-Op): What should change for next operation?

**Decline Code Research**
- `TransactionMonitor` + `DeclineDecoder` integration
- Enter any PSP decline code to get: reason, category, severity, guidance
- Cross-PSP code mapping (same decline across different PSPs)
- Historical decline frequency chart

**Correlation Analysis**
- Cross-operation pattern detection
- "BIN X always fails at merchant Y with code Z"
- Time-of-day correlation with decline rates
- Profile age vs success rate correlation

### What the Operator Inputs
| Input | Description | Example |
|-------|-------------|---------|
| Operation ID | Past operation to analyze | "op_2024_001" |
| Decline Code | PSP-specific code | "card_declined" (Stripe) |
| PSP | Payment processor | "Adyen" |

### What the Operator Gets
| Output | Description |
|--------|-------------|
| Detection Report | Which vector triggered, root cause |
| Decline Decode | Human-readable explanation + fix |
| Pattern Analysis | Correlations across operations |
| Improvement Plan | Specific changes to try next |

---

## Tab 4: RECON — Target Reconnaissance

### What This Tab Does
Deep intelligence gathering on target websites before operations. The operator enters a URL and gets comprehensive analysis.

### Features

**V2 Full Intel**
- `TargetIntelV2.get_full_intel(target)` — 8-vector golden path scoring
- Detailed breakdown of all 8 scoring vectors
- Overall score out of 100 with confidence level

**Target Intelligence**
- `get_target_intel(url)` — PSP identification, antifraud detection
- `get_avs_intelligence(target)` — AVS requirements per target
- `get_proxy_intelligence(target)` — which proxy types work best

**Web Intelligence**
- `TitanWebIntel.research(target)` — multi-provider web search
- Extracts: PSP switches, antifraud changes, checkout flow updates
- Real-time web data supplements local knowledge base

**TLS/JA4+ Analysis**
- `TLSParrotEngine` — analyze target's TLS requirements
- `JA4PermutationEngine` — generate matching JA4 fingerprints
- Shows which browser/version fingerprint matches the target

**Recon Worker**
- Background thread (`ReconWorker`) runs all intelligence gathering in parallel
- Results combined into single comprehensive report
- Truncated at 3000 chars per section to prevent UI overflow

### What the Operator Inputs
| Input | Description | Example |
|-------|-------------|---------|
| Target URL | Website to analyze | "https://shop.example.com" |

### What the Operator Gets
| Output | Description |
|--------|-------------|
| Golden Path Score | 0-100 with per-vector breakdown |
| PSP Identification | Which payment processor the target uses |
| Antifraud Map | Detected antifraud systems |
| AVS Requirements | What address verification is needed |
| TLS Profile | Required browser TLS fingerprint |
| Web Intel | Recent news/changes about target |

---

## Tab 5: MEMORY — Vector Knowledge Base

### What This Tab Does
Manages the persistent vector knowledge base that stores all operational intelligence for semantic search.

### Features

**Vector Memory Search**
- `TitanVectorMemory.search(query, n)` — semantic similarity search
- Natural language queries: "What worked on Shopify last month?"
- Returns top-N most similar past experiences with relevance scores

**Knowledge Storage**
- All operation results automatically stored as vectors
- BIN intelligence, target analysis, decline patterns archived
- Manual knowledge entry for operator notes

**Cognitive Core**
- `TitanCognitiveCore` — coordinates memory across AI components
- Behavioral profile modeling from accumulated data
- Pattern recognition across hundreds of operations

**Intel Monitor**
- `IntelMonitor` — continuous background monitoring of known targets
- Alerts when targets change PSP or upgrade antifraud
- Historical intelligence timeline per target

**Memory Statistics**
- Total vectors stored
- Collection sizes by category
- Last update timestamps
- Storage usage

### What the Operator Inputs
| Input | Description | Example |
|-------|-------------|---------|
| Search Query | Semantic search | "successful Visa operations on Stripe merchants" |
| Manual Note | Knowledge to store | "BIN 453201 works best with Mullvad UK exit" |

### What the Operator Gets
| Output | Description |
|--------|-------------|
| Search Results | Ranked past experiences |
| Pattern Insights | Detected patterns from data |
| Target Alerts | Changes at monitored targets |
| Memory Stats | Knowledge base health |

---

## Module Wiring Summary

| Tab | Modules Used |
|-----|-------------|
| AI COPILOT | titan_realtime_copilot, ai_intelligence_engine, ollama_bridge, titan_agent_chain, titan_vector_memory |
| 3DS STRATEGY | three_ds_strategy, titan_3ds_ai_exploits, tra_exemption_engine, issuer_algo_defense |
| DETECTION | titan_detection_analyzer, titan_ai_operations_guard, transaction_monitor |
| RECON | titan_target_intel_v2, target_intelligence, titan_web_intel, tls_parrot, ja4_permutation_engine |
| MEMORY | cognitive_core, titan_vector_memory, intel_monitor |

**Total: 20 modules wired into Intelligence Center**

---

*Next: [06 — App: Network Center](06_APP_NETWORK_CENTER.md)*
