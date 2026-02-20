# Cerberus Transaction Engine — Card Validation, BIN Intelligence & Target Discovery

## Core Modules: `cerberus_core.py`, `cerberus_enhanced.py`, `target_discovery.py`, `target_intelligence.py`, `three_ds_strategy.py`, `transaction_monitor.py`

Cerberus is the transaction intelligence layer. It validates card assets, scores BIN quality, discovers optimal targets, strategizes 3D Secure challenges, and monitors transactions in real-time.

---

## 1. Card Validation (`cerberus_core.py`)

### Luhn Algorithm Validation
Every card number is validated against the Luhn checksum algorithm before any operation begins. This catches typos and invalid card data immediately.

### Card Network Detection
```
Visa:        4xxxxx (13-19 digits)
Mastercard:  51-55xx, 2221-2720 (16 digits)
Amex:        34xx, 37xx (15 digits)
Discover:    6011, 644-649, 65 (16-19 digits)
JCB:         3528-3589 (16-19 digits)
UnionPay:    62xxxx (16-19 digits)
```

### BIN (Bank Identification Number) Lookup
The first 6-8 digits of a card number identify:
- **Issuing bank** (Chase, Citi, BoA, etc.)
- **Card type** (Credit, Debit, Prepaid)
- **Card level** (Classic, Gold, Platinum, Signature, Infinite, Centurion)
- **Country of issuance**
- **Card brand** (Visa, MC, Amex)

### Validation Result Structure
```python
@dataclass
class ValidationResult:
    card_number: str
    is_valid: bool           # Luhn check
    network: str             # visa, mastercard, amex
    bin_data: Dict           # Bank, type, level, country
    risk_score: int          # 0-100 (lower = better)
    avs_recommendation: str  # full, partial, zip_only
    recommended_targets: List[str]  # Best merchants for this card
```

---

## 2. BIN Intelligence (`cerberus_enhanced.py` — BINScoringEngine)

### BIN Scoring Algorithm

Each BIN is scored on a 0-100 scale based on multiple factors:

| Factor | Weight | Description |
|--------|--------|-------------|
| Card type | 25% | Credit > Debit > Prepaid |
| Card level | 20% | Platinum/Signature score highest |
| Issuing bank | 15% | Tier-1 banks (Chase, Citi) score higher |
| Country match | 15% | Domestic cards score higher than international |
| Known decline rate | 15% | Historical decline data per BIN range |
| AVS support | 10% | Full AVS support scores higher |

### Card Quality Grading (`CardQualityGrader`)

Cards are graded A through F:

| Grade | Score | Description | Expected Success Rate |
|-------|-------|-------------|----------------------|
| **A+** | 90-100 | Premium credit, Tier-1 bank, domestic | 85-95% |
| **A** | 80-89 | Standard credit, good bank, domestic | 75-85% |
| **B** | 70-79 | Credit card, decent bank | 60-75% |
| **C** | 60-69 | Debit card or international credit | 40-60% |
| **D** | 40-59 | Prepaid or high-risk BIN | 20-40% |
| **F** | 0-39 | Known burned BIN, virtual card | <20% |

### AVS (Address Verification System) Engine

AVS checks if the billing address matches what the bank has on file. The engine determines the optimal AVS strategy:

- **Full match**: Street + ZIP both match (best for high-security merchants)
- **Partial match**: ZIP only matches (sufficient for most merchants)
- **No match**: Neither matches (high decline risk)

The engine recommends which address fields to provide based on the target merchant's known AVS requirements.

### OSINT Verification (`OSINTVerifier`)

Cross-references cardholder data against public records:
- Name + address consistency check
- Phone number area code matches billing ZIP
- Email domain age verification
- Social media presence check (LinkedIn, Facebook)

---

## 3. Target Discovery (`target_discovery.py`, `target_presets.py`)

### Pre-Configured Merchant Profiles (9 built-in, extensible)

The `target_presets.py` module ships with 9 built-in merchant profiles (Eneba, G2A, Kinguin, Steam, PlayStation, etc.) with the `generate_preset_from_intel()` function allowing operators to auto-generate new presets from target intelligence. Each target preset contains:

```python
@dataclass
class TargetPreset:
    name: str                    # "Amazon US"
    domain: str                  # "amazon.com"
    category: str                # "electronics", "gaming", "fashion"
    difficulty: str              # "easy", "medium", "hard", "extreme"
    antifraud_systems: List[str] # ["Sift", "internal"]
    avs_requirement: str         # "full", "zip_only", "none"
    three_ds_likelihood: float   # 0.0-1.0
    velocity_limits: Dict        # {"per_hour": 3, "per_day": 10}
    browser_preference: str      # "firefox" or "chromium"
    requires_account: bool       # Must create account first?
    guest_checkout: bool         # Supports guest checkout?
    digital_goods: bool          # Instant delivery (no shipping)
    notes: str                   # Operator tips
```

### Target Categories

| Category | Examples | Typical Difficulty |
|----------|----------|-------------------|
| **Electronics** | Amazon, BestBuy, Newegg | Medium-Hard |
| **Gaming** | Steam, PlayStation Store, Xbox, Eneba | Easy-Medium |
| **Fashion** | Nike, Adidas, SSENSE, Farfetch | Medium |
| **Gift Cards** | Amazon GC, Apple GC, Google Play | Hard |
| **Digital Services** | Spotify, Netflix, Adobe | Easy |
| **Luxury** | Louis Vuitton, Gucci, Rolex | Extreme |
| **Crypto** | Coinbase, Binance | Extreme |

### Auto-Discovery (`target_intelligence.py`)

Automatically profiles new merchants by analyzing:
- Checkout flow (guest vs account required)
- Payment processors used (Stripe, Braintree, Adyen, PayPal)
- Antifraud SDK presence (ThreatMetrix, Forter, Sift scripts)
- 3DS implementation (challenge vs frictionless)
- Velocity limit detection (how many attempts before lockout)

---

## 4. 3D Secure Strategy (`three_ds_strategy.py`)

### What is 3DS?

3D Secure (Verified by Visa, Mastercard SecureCode) is an additional authentication layer where the bank sends an OTP or challenge to the cardholder. It's the #1 reason transactions fail.

### TITAN's 3DS Strategy Engine

The engine classifies 3DS implementations:

| Type | Description | Strategy |
|------|-------------|----------|
| **Frictionless** | Bank approves silently (no challenge) | Proceed normally |
| **Challenge (OTP)** | SMS/email code required | Requires cardholder cooperation |
| **Challenge (App)** | Bank app push notification | Requires cardholder cooperation |
| **Biometric** | Fingerprint/face on bank app | Cannot bypass |
| **Risk-based** | Challenge only for suspicious transactions | Lower risk = no challenge |

### Strategies to Minimize 3DS Challenges

1. **Profile aging**: Older profiles with purchase history trigger fewer challenges
2. **Low-value first**: Start with small purchases to build trust
3. **Domestic matching**: Card country matches merchant country
4. **Time-of-day**: Transactions during business hours trigger fewer challenges
5. **Device consistency**: Same device fingerprint across sessions
6. **Merchant familiarity**: Previous purchases on same merchant reduce challenges

---

## 5. Transaction Monitoring (`transaction_monitor.py`)

### Real-Time Monitoring

The TX Monitor browser extension (`/opt/titan/extensions/tx_monitor/`) watches for:

- **Fraud score changes**: Reads antifraud SDK signals from page
- **Decline indicators**: Detects "declined", "error", "failed" in DOM
- **3DS iframe appearance**: Detects 3DS challenge popup
- **Velocity warnings**: Tracks transaction count per time window
- **Session anomalies**: Detects if session is being flagged

### Integration with Kill Switch

When the TX Monitor detects a fraud score drop below threshold (default: 85), it writes to `/opt/titan/state/fraud_score.json`. The Kill Switch daemon reads this file every 500ms and triggers the panic sequence if the score is too low.

---

## GUI: Cerberus App (`app_cerberus.py` — 1441 lines, 4 tabs)

### Tab 1: Validate
- Card number input with Luhn validation
- BIN lookup with bank/type/level display
- Network detection (Visa/MC/Amex)
- Risk score calculation

### Tab 2: BIN Intelligence
- BIN database search
- Card quality grading (A+ through F)
- AVS recommendation engine
- Bank tier classification

### Tab 3: Target Discovery
- 50+ merchant database browser
- Difficulty rating per target
- Antifraud system identification
- Velocity limit information
- Recommended approach per target

### Tab 4: Card Quality
- Comprehensive card scoring
- OSINT verification results
- Geo-match analysis
- Success probability estimation
