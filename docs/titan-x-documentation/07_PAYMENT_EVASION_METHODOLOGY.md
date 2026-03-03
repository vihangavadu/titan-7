# 07 — Payment Evasion Methodology

**Cerberus Engine — Card Validation, BIN Intelligence, 3DS Bypass, Issuer Defense, Transaction Monitoring**

The Cerberus transaction layer transforms blind card usage into informed, strategic operations. It pre-screens every card, grades quality, identifies optimal targets, engineers 3DS bypass paths, and monitors transactions in real-time. This document covers every payment-related module and strategy.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                     CERBERUS TRANSACTION LAYER                       │
│                                                                      │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐             │
│  │  VALIDATION  │───→│ INTELLIGENCE│───→│  STRATEGY   │             │
│  │ cerberus_core│    │cerberus_enh │    │ 3ds_strategy│             │
│  └─────────────┘    └─────────────┘    └─────────────┘             │
│         │                  │                   │                     │
│         ▼                  ▼                   ▼                     │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐             │
│  │   ISSUER    │    │   TARGET    │    │  MONITOR    │             │
│  │issuer_algo  │    │target_intel │    │ tx_monitor  │             │
│  └─────────────┘    └─────────────┘    └─────────────┘             │
│         │                  │                   │                     │
│         └──────────────────┼───────────────────┘                    │
│                            ▼                                         │
│                    ┌─────────────┐                                   │
│                    │  PREFLIGHT  │                                   │
│                    │  Go / No-Go │                                   │
│                    └─────────────┘                                   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 1. Card Validation (`cerberus_core.py`)

### Validation Pipeline

Every card passes through a 5-step validation before any operation begins:

```
Step 1: Luhn Check → Step 2: Network Detection → Step 3: BIN Lookup →
Step 4: SetupIntent Probe → Step 5: Status Assignment
```

### Step 1: Luhn Algorithm

Mathematical checksum validation catching invalid card numbers immediately. Eliminates typos and fabricated numbers before any external contact.

### Step 2: Card Network Detection

| Network | BIN Range | Digits | Identifier |
|---------|-----------|--------|-----------|
| Visa | 4xxxxxx | 13-19 | Starts with 4 |
| Mastercard | 51-55xx, 2221-2720 | 16 | 51-55 or 2221-2720 |
| American Express | 34xx, 37xx | 15 | Starts with 34 or 37 |
| Discover | 6011, 644-649, 65 | 16-19 | 6011, 644-649, or 65 |
| JCB | 3528-3589 | 16-19 | 3528-3589 range |
| UnionPay | 62xxxx | 16-19 | Starts with 62 |
| Diners Club | 300-305, 36, 38 | 14-19 | 300-305, 36, or 38 |

### Step 3: BIN Lookup

The first 6-8 digits (Bank Identification Number) reveal:

| Data Point | Source | Example |
|-----------|--------|---------|
| Issuing bank | BIN database | Chase, Citi, Bank of America |
| Card type | BIN database | Credit, Debit, Prepaid |
| Card level | BIN database | Classic, Gold, Platinum, Signature, Infinite |
| Country | BIN database | US, UK, CA, DE |
| Card brand | BIN prefix | Visa, Mastercard, Amex |

### Step 4: SetupIntent Probe

Zero-touch validation using Stripe's SetupIntent API:

```
Card data → Stripe SetupIntent (no charge) → Bank response → LIVE/DEAD/RISKY
```

**Key principle**: SetupIntent performs address verification and card existence check without creating a charge. This means:
- No velocity hit on the card (doesn't count as a declined transaction)
- No fraud signal generated (SetupIntent is a legitimate merchant action)
- Instant response (<2 seconds)

### Step 5: Status Assignment

| Status | Meaning | Action |
|--------|---------|--------|
| **LIVE** ✅ | Card exists, bank approves setup | Proceed to operation |
| **DEAD** ❌ | Card invalid, canceled, or stolen-flagged | Discard immediately |
| **RISKY** ⚠️ | Card exists but shows risk indicators | Review before use |
| **UNKNOWN** ❓ | Bank did not respond or ambiguous response | Retry or manual check |

### Card Cooling System

Enforces velocity limits to prevent card burning:

| Cooldown Rule | Duration | Purpose |
|--------------|----------|---------|
| Between validation attempts | 30 minutes | Prevent BIN velocity detection |
| Between operations (same card) | 2-6 hours | Match natural purchase pacing |
| After decline | 24 hours minimum | Allow fraud score reset |
| After 3DS failure | 48 hours | Extended cooling for challenged cards |

---

## 2. BIN Intelligence (`cerberus_enhanced.py`)

### BIN Scoring Algorithm

Each BIN is scored 0-100 based on weighted factors:

| Factor | Weight | Scoring Logic |
|--------|--------|--------------|
| Card type | 25% | Credit: 80-100, Debit: 50-70, Prepaid: 10-30 |
| Card level | 20% | Infinite/Centurion: 95-100, Platinum: 80-90, Gold: 70-80, Classic: 50-65 |
| Issuing bank | 15% | Tier-1 (Chase, Citi): 80-95, Tier-2: 60-75, Tier-3: 40-55 |
| Country match | 15% | Domestic: 85-100, Same continent: 60-75, Cross-continent: 20-40 |
| Known decline rate | 15% | Historical data per BIN range (0-100 inverse) |
| AVS support | 10% | Full AVS: 90-100, ZIP only: 60-75, None: 20-40 |

### Card Quality Grades

| Grade | Score | Description | Expected Success |
|-------|-------|-------------|-----------------|
| **A+** | 90-100 | Premium credit, Tier-1 bank, domestic | 85-95% |
| **A** | 80-89 | Standard credit, good bank, domestic | 75-85% |
| **B** | 70-79 | Credit card, decent bank | 60-75% |
| **C** | 60-69 | Debit card or international credit | 40-60% |
| **D** | 40-59 | Prepaid or high-risk BIN | 20-40% |
| **F** | 0-39 | Known burned BIN, virtual card | <20% |

### AVS (Address Verification System) Intelligence

AVS checks if the billing address matches the bank's records:

| AVS Result | Match Level | Risk | Strategy |
|-----------|------------|------|----------|
| Y (Full match) | Street + ZIP | Lowest | Use for high-security merchants |
| Z (ZIP match) | ZIP only | Low | Sufficient for most merchants |
| A (Address match) | Street only | Medium | Use when ZIP unknown |
| N (No match) | Neither | High | Avoid unless merchant ignores AVS |
| U (Unavailable) | Bank doesn't support | Variable | Depends on merchant policy |

The engine determines optimal AVS strategy per target:

| Target Type | Recommended AVS |
|------------|----------------|
| Electronics (Amazon, Best Buy) | Full match (Y) required |
| Digital goods (Steam, Eneba) | ZIP match (Z) sufficient |
| Fashion (Nike, Adidas) | ZIP match (Z) sufficient |
| Gift cards | Full match (Y) required |
| Subscriptions (Netflix, Spotify) | Minimal — often no AVS check |

### OSINT Verification

Cross-references cardholder data against public records:

| Check | Source | Purpose |
|-------|--------|---------|
| Name + address | Public records | Verify identity consistency |
| Phone area code | Phone databases | Must match billing ZIP region |
| Email domain age | WHOIS | Domain must predate profile |
| Social presence | LinkedIn, Facebook | Establishes identity legitimacy |

### Max Drain Calculation

The `MaxDrainEngine` calculates optimal transaction amount:

| Factor | Impact |
|--------|--------|
| Card level | Higher level → higher safe amount |
| Issuer velocity limits | Some banks flag amounts > $500 |
| Target merchant | Each merchant has typical purchase ranges |
| Time of day | Nighttime transactions flagged more often |
| Day of week | Weekend purchases slightly lower risk |
| Geographic match | Domestic → higher safe amount |

---

## 3. Target Intelligence (`target_discovery.py`, `target_intelligence.py`, `target_presets.py`)

### Target Database Structure

Each target includes a comprehensive profile:

```python
@dataclass
class TargetPreset:
    name: str                    # "Amazon US"
    domain: str                  # "amazon.com"
    category: str                # "electronics"
    difficulty: str              # "easy" | "medium" | "hard" | "extreme"
    antifraud_systems: List[str] # ["Sift", "internal"]
    avs_requirement: str         # "full" | "zip_only" | "none"
    three_ds_likelihood: float   # 0.0-1.0
    velocity_limits: Dict        # {"per_hour": 3, "per_day": 10}
    browser_preference: str      # "firefox" | "chromium"
    requires_account: bool       # Must create account first?
    guest_checkout: bool         # Supports guest checkout?
    digital_goods: bool          # Instant delivery (no shipping)
    notes: str                   # Operator tips
```

### Target Categories

| Category | Examples | Difficulty | 3DS Likelihood |
|----------|---------|-----------|---------------|
| Gaming/Digital | Steam, Eneba, G2A, Kinguin | Easy-Medium | Low (20-40%) |
| Electronics | Amazon, Best Buy, Newegg | Medium-Hard | Medium (40-60%) |
| Fashion | Nike, Adidas, SSENSE, Farfetch | Medium | Medium (30-50%) |
| Digital Services | Spotify, Netflix, Adobe | Easy | Low (10-30%) |
| General Retail | Walmart, Target | Medium | Medium (40-60%) |
| Gift Cards | Amazon GC, Apple GC | Hard | High (60-80%) |
| Luxury | Louis Vuitton, Gucci | Extreme | Very High (80-95%) |
| Crypto | Coinbase, Binance | Extreme | Very High (90-99%) |

### Antifraud System Intelligence

21 antifraud platforms profiled with detection methods and evasion strategies:

| Platform | Detection Focus | Primary Weakness |
|----------|----------------|-----------------|
| **Forter** | Behavioral + device + identity | Behavioral analysis can be defeated with Ghost Motor |
| **Sift** | Velocity + device + ML scoring | Velocity rules are predictable |
| **ThreatMetrix** | Device fingerprint + network | Hardware Shield defeats device detection |
| **BioCatch** | Behavioral biometrics (2000+ params) | Persona-specific Ghost Motor profiles |
| **Riskified** | Identity + purchase history | Genesis profile provides purchase history |
| **Kount** | Device ID + IP reputation | Residential proxy + fresh device fingerprint |
| **Stripe Radar** | Card testing + velocity | Single-attempt strategy with cooling |
| **Signifyd** | Identity + device graph | Isolated profiles prevent graph linking |
| **Arkose Labs** | Challenge-response + behavioral | Challenge solutions + human-like interaction |
| **HUMAN (PerimeterX)** | JS challenges + behavioral | Camoufox passes JS challenges natively |
| **FingerprintJS** | Canvas + WebGL + Audio + Fonts | All vectors spoofed by Ring 2 modules |
| **Sardine** | Device + behavioral intelligence | Combined Ring 2 + Ring 3 defense |
| **Accertify** | Device + behavioral + rules | Rule-based systems have predictable triggers |
| **CyberSource** | Decision Manager rules | Configurable thresholds are discoverable |
| **Feedzai** | ML-based anomaly detection | Profile depth defeats anomaly scoring |
| **DataVisor** | Unsupervised ML clustering | Profile isolation prevents clustering |
| **Emailage** | Email risk scoring | Aged email addresses with social presence |
| **Socure** | Identity verification | Full persona with public records presence |
| **Verifi/Ethoca** | Chargeback prevention | Post-operation concern, not detection |
| **Chargebacks911** | Chargeback management | Post-operation concern |
| **Bolt** | One-click checkout optimization | Minimal fraud detection focus |

### Auto-Discovery Engine

`target_discovery.py` continuously scans and profiles new merchants:

| Probe | What It Detects |
|-------|----------------|
| Checkout flow analysis | Guest vs account required, step count |
| PSP detection | Payment processor (Stripe, Braintree, Adyen, PayPal) |
| Antifraud SDK scan | Script tags for ThreatMetrix, Forter, Sift, etc. |
| 3DS implementation | Challenge vs frictionless, threshold detection |
| Velocity testing | How many attempts before lockout |
| Health checks | Daily availability and configuration change monitoring |

---

## 4. 3DS Strategy (`three_ds_strategy.py`, `titan_3ds_ai_exploits.py`, `tra_exemption_engine.py`)

### 3DS Challenge Types

| Type | Mechanism | Bypass Possibility |
|------|-----------|-------------------|
| Frictionless | Bank approves silently | No bypass needed — proceeds automatically |
| OTP (SMS) | SMS code to cardholder phone | Requires cardholder cooperation |
| OTP (Email) | Email code to cardholder | Requires email access |
| App Push | Bank app push notification | Requires cardholder cooperation |
| Biometric | Fingerprint/face on bank app | Cannot bypass |
| Risk-based | Challenge only if suspicious | Reduce risk signals → no challenge |

### PSP-Specific Strategies

| PSP | 3DS Implementation | Optimal Strategy |
|-----|-------------------|-----------------|
| **Stripe** | Risk-based, merchant-configurable | Low amounts + strong profile = frictionless |
| **Adyen** | Sophisticated risk engine | TRA exemption for PSD2 regions |
| **Braintree** | PayPal-backed risk scoring | Domestic cards + returning customer signals |
| **Worldpay** | Traditional rules-based | Amount threshold exploitation |
| **Checkout.com** | ML-based risk assessment | Profile depth + behavioral consistency |
| **Square** | Conservative 3DS | Domestic only, small amounts |

### TRA Exemption Engine

**Transaction Risk Analysis (TRA)** exemption under PSD2 allows merchants to request frictionless authentication for low-risk transactions:

| Amount Threshold | Required Fraud Rate | Strategy |
|-----------------|-------------------|---------|
| Up to €30 | <0.13% | Almost always exempt |
| Up to €100 | <0.06% | Exempt with clean merchant history |
| Up to €250 | <0.01% | Rarely exempt, requires perfect signals |
| Up to €500 | <0.005% | Very rarely exempt |

The `TRAOptimizer` constructs exemption requests with:
- Transaction amount justification
- Merchant fraud rate evidence
- Cardholder risk assessment
- Device trust score

### Strategies to Minimize 3DS Triggers

| Strategy | Effectiveness | How It Works |
|----------|-------------|-------------|
| Profile aging | ★★★★★ | Older profiles with purchase history trigger fewer challenges |
| Low-value first | ★★★★☆ | Small purchases build trust, larger purchases follow |
| Domestic matching | ★★★★☆ | Card country = merchant country = proxy country |
| Business hours | ★★★☆☆ | Weekday 9-5 transactions trigger fewer challenges |
| Device consistency | ★★★★★ | Same device fingerprint across sessions |
| Merchant familiarity | ★★★★★ | Previous purchases on same merchant |
| Amount normalization | ★★★☆☆ | Purchase amount typical for category |
| TRA exemption | ★★★★☆ | Exploit PSD2 regulatory exemption (EU only) |

### AI-Driven 3DS Analysis (`titan_3ds_ai_exploits.py`)

Real-time AI classification of 3DS challenges:
- Identifies challenge type from iframe/popup analysis
- Recommends optimal response strategy
- Predicts frictionless probability based on card + merchant + profile signals
- Suggests amount adjustments to avoid 3DS threshold

---

## 5. Issuer Algorithm Defense (`issuer_algo_defense.py`)

### Bank-Specific Intelligence

| Issuer | Fraud Algorithm | Velocity Rules | Titan Strategy |
|--------|----------------|---------------|---------------|
| **Chase** | ML + rules hybrid | 3 attempts/hr, $2K daily limit | Single attempt, moderate amount, domestic |
| **American Express** | Strict ML, manual review triggers | 1 attempt/day for new merchants | Premium persona, high-value profile, patience |
| **Wells Fargo** | Velocity-focused | Rapid decline after 2nd attempt | Extended cooldown, single-shot approach |
| **Capital One** | ML-heavy, device fingerprint | Device graph analysis | Perfect device consistency, no graph links |
| **Citi** | Rules + ML hybrid | Moderate velocity tolerance | Standard approach, domestic matching |
| **Bank of America** | Conservative rules | Low velocity tolerance | Conservative amounts, domestic only |
| **USAA** | Military-specific patterns | Address verification strict | Military-area address matching |
| **Discover** | Conservative ML | Very low tolerance | Small amounts, established relationship |
| **Revolut** | Real-time ML, instant blocks | Zero tolerance for anomalies | Conservative, domestic, small amounts |
| **N26** | Strict EU compliance | PSD2 enforcement | Full TRA exemption path |

### Amount Optimization

The `AmountOptimizer` calculates the ideal transaction amount per issuer:

| Factor | Logic |
|--------|-------|
| Card level | Platinum → higher safe amount than Classic |
| Issuer tolerance | Chase tolerates more than Discover |
| Time since last use | Longer gap → slightly higher safe amount |
| Merchant category | Electronics → higher typical amounts |
| Geographic match | Domestic → 20% higher safe amount |
| Day of week | Weekend → slightly lower threshold |

---

## 6. Transaction Monitoring (`transaction_monitor.py`)

### Real-Time Monitoring

The TX Monitor watches for:

| Signal | Detection Method | Response |
|--------|-----------------|----------|
| Fraud score drop | Read antifraud SDK variables from page | Alert if <85, Kill Switch if <70 |
| Decline message | DOM text analysis for "declined", "error", "failed" | Capture decline code, log for analysis |
| 3DS popup | iframe/popup detection | Alert operator, suggest strategy |
| Velocity warning | Count transactions per time window | Enforce cooldown |
| Session anomaly | Cookie deletion, fingerprint check | Alert operator |

### Antifraud SDK Detection

```javascript
// Forter fraud score
window.__forter_score → reportScore('forter', score)

// Sift signals
window._sift._score → reportScore('sift', score)

// ThreatMetrix session
window.tmx_session_id → reportSession('threatmetrix', id)

// Riskified session
window.RISKX → reportSession('riskified', window.RISKX.sessionId)
```

### Decline Code Intelligence

PSP-specific decline code databases:

#### Stripe (40+ codes)

| Code | Meaning | Action |
|------|---------|--------|
| `card_declined` | Generic decline | Check BIN grade, try different target |
| `insufficient_funds` | Balance too low | Lower amount or different card |
| `lost_card` | Reported lost | Discard card immediately |
| `stolen_card` | Reported stolen | Discard card immediately |
| `fraud_detected` | Bank fraud system triggered | 48hr cooldown, review profile |
| `do_not_honor` | Bank refuses (generic) | Try different PSP or target |
| `incorrect_cvc` | CVV mismatch | Verify card data |
| `expired_card` | Past expiry date | Verify expiry |

#### Adyen (30+ codes)

| Code | Meaning | Action |
|------|---------|--------|
| `Refused` | Generic refusal | Analyze sub-code |
| `Acquirer Fraud` | Acquirer fraud detection | Different PSP needed |
| `Blocked Card` | Card blocked by issuer | Discard |
| `Not Enough Balance` | Insufficient funds | Lower amount |
| `3D Not Authenticated` | 3DS failure | Review 3DS strategy |

#### Checkout.com (10+ codes)

| Code | Meaning | Action |
|------|---------|--------|
| `20005` | Do not honor | Different PSP |
| `20051` | Insufficient funds | Lower amount |
| `20054` | Expired card | Verify expiry |
| `20065` | Exceeds withdrawal limit | Lower amount, wait 24hrs |

### Kill Switch Integration

When TX Monitor detects fraud score <70:
1. Write alert to `/opt/titan/state/fraud_score.json`
2. Kill Switch daemon reads file every 500ms
3. If score <70 → automatic panic sequence (<500ms)
4. All profiles destroyed, network disconnected, session wiped

---

## 7. Payment Preflight (`payment_preflight.py`)

### Go/No-Go Checklist

Before any checkout attempt, all signals are validated:

| Check | Required | Module |
|-------|----------|--------|
| Card LIVE status | ✅ | `cerberus_core` |
| BIN grade ≥ C | ✅ | `cerberus_enhanced` |
| Target compatible | ✅ | `target_intelligence` |
| Proxy geo-matched | ✅ | `proxy_manager` |
| Profile quality ≥ 70 | ✅ | `profile_realism_engine` |
| VPN connected | ✅ | `mullvad_vpn` or `lucid_vpn` |
| Network shield active | ✅ | `network_shield` |
| Hardware shield active | ✅ | `hardware_shield_v6.c` |
| Deep identity verified | ✅ | `verify_deep_identity` |
| Forensic scan clean | ✅ | `forensic_monitor` |
| Ghost Motor configured | ✅ | `ghost_motor_v6` |
| Kill switch armed | ✅ | `kill_switch` |

**Any failed check = operation blocked**. No overrides — the system enforces discipline.

---

## 8. Payment Metrics (`payment_success_metrics.py`)

### Metrics Tracked

| Metric | Granularity | Storage |
|--------|------------|---------|
| Success rate | Per target, per BIN, per PSP | SQLite database |
| Decline reasons | Per decline code | SQLite database |
| 3DS challenge rate | Per PSP, per issuer | SQLite database |
| Average amount | Per successful operation | SQLite database |
| Time-to-checkout | Per target | SQLite database |
| Profile quality correlation | Score vs success rate | SQLite database |

### Prometheus Export

Metrics exported on port 9200 for monitoring:

```
titan_payment_success_total{target="amazon",psp="stripe"} 47
titan_payment_decline_total{target="amazon",reason="card_declined"} 12
titan_3ds_challenge_total{psp="adyen",result="frictionless"} 23
titan_avg_checkout_seconds{target="eneba"} 142
```

### Data-Driven Optimization

Historical metrics inform future strategy:
- BIN ranges with >70% success rate are prioritized
- Targets with <30% success rate are de-prioritized
- PSPs with highest frictionless 3DS rate are preferred
- Time-of-day success patterns inform scheduling
- Amount ranges with highest approval rate are targeted

---

## 9. Sandbox Testing (`payment_sandbox_tester.py`)

Safe validation of payment flows without real charges:

| Feature | Description |
|---------|-------------|
| Test card numbers | Stripe/Adyen test cards for flow validation |
| Mock 3DS challenges | Simulate 3DS flows with predictable outcomes |
| PSP response simulation | Test decline handling and retry logic |
| Strategy validation | Verify strategy changes before live deployment |

---

## Operational Payment Flow

```
1. CARD ARRIVES → Luhn check → Network detection → BIN lookup
2. VALIDATION → SetupIntent probe → LIVE/DEAD/RISKY
3. INTELLIGENCE → BIN scoring (A-F) → Issuer profile → AVS check
4. TARGET MATCH → Card + target compatibility → 3DS likelihood
5. STRATEGY → 3DS bypass path → Amount optimization → Timing
6. PREFLIGHT → 12-point Go/No-Go checklist
7. OPERATION → Profile loaded → Browser launched → Warmup
8. CHECKOUT → Ghost Motor form fill → Payment submission
9. MONITORING → Real-time TX watch → Decline decoder → Kill switch ready
10. POST-OP → Metrics logged → Profile burndown → Card cooling
```

---

*Document 07 of 11 — Titan X Documentation Suite — V10.0 — March 2026*
