# MODULE 2: CERBERUS — Complete Technical Reference

## The Gatekeeper: Card Validation + OSINT + Quality Assessment

**Module:** `cerberus_core.py` | **Lines:** 776 | **Path:** `/opt/titan/core/cerberus_core.py`  
**Version:** 7.0.2 | **Authority:** Dva.12

---

## Table of Contents

1. [Purpose & Philosophy](#1-purpose--philosophy)
2. [Classes & Data Structures](#2-classes--data-structures)
3. [Validation Pipeline](#3-validation-pipeline)
4. [BIN Intelligence Database](#4-bin-intelligence-database)
5. [Risk Scoring System](#5-risk-scoring-system)
6. [Stripe SetupIntent Validation](#6-stripe-setupintent-validation)
7. [Card Input Parsing](#7-card-input-parsing)
8. [Bulk Validation](#8-bulk-validation)
9. [V7.0: OSINT Verification](#9-v70-osint-verification)
10. [V7.0: Card Quality Assessment](#10-v70-card-quality-assessment)
11. [V7.0: Bank Enrollment Guide](#11-v70-bank-enrollment-guide)
12. [Integration Points](#12-integration-points)
13. [API Reference](#13-api-reference)

---

## 1. Purpose & Philosophy

Cerberus is the **Gatekeeper** — it validates payment cards **without burning them**. Traditional card checking charges a small amount (which alerts the cardholder and flags the card). Cerberus uses **zero-charge tokenization APIs** (Stripe SetupIntent, Braintree ClientToken, Adyen zero-auth) to determine if a card is live without triggering any transaction.

**Key Principle:** Validate first, operate second. A dead card wastes a profile, a proxy, and operator time. Cerberus ensures only live, quality cards reach the operator.

**Traffic Light System:**
- 🟢 **GREEN (LIVE)** — Card is valid and active. Proceed with operation.
- 🔴 **RED (DEAD)** — Card declined or invalid. Discard immediately.
- 🟡 **YELLOW (UNKNOWN)** — Could not determine status (rate limit, network error). Retry later.
- 🟠 **ORANGE (RISKY)** — Card is valid but has a high-risk BIN (prepaid, virtual, gift card).

---

## 2. Classes & Data Structures

### 2.1 Enums

#### `CardStatus`
```python
class CardStatus(Enum):
    LIVE = "LIVE"       # Green — valid and active
    DEAD = "DEAD"       # Red — declined or invalid
    UNKNOWN = "UNKNOWN" # Yellow — could not determine
    RISKY = "RISKY"     # Orange — valid but high-risk BIN
```

#### `CardType`
```python
class CardType(Enum):
    VISA = "visa"             # Starts with 4
    MASTERCARD = "mastercard" # Starts with 51-55
    AMEX = "amex"             # Starts with 34, 37
    DISCOVER = "discover"     # Starts with 6011, 65
    UNKNOWN = "unknown"
```

### 2.2 Dataclasses

#### `CardAsset`
```python
@dataclass
class CardAsset:
    number: str              # Full PAN (auto-cleaned of non-digits)
    exp_month: int           # 1-12
    exp_year: int            # 4-digit year
    cvv: str                 # 3-4 digit CVV
    holder_name: Optional[str] = None
```

**Computed Properties:**
| Property | Returns | Description |
|----------|---------|-------------|
| `bin` | `str` | First 6 digits (Bank Identification Number) |
| `last_four` | `str` | Last 4 digits for display |
| `card_type` | `CardType` | Network detection from first digits |
| `is_valid_luhn` | `bool` | Luhn algorithm checksum validation |
| `masked()` | `str` | Display format: `424242******4242` |

**Luhn Algorithm Implementation:**
```
1. Take all digits, reverse order
2. Double every second digit
3. If doubled digit > 9, subtract 9
4. Sum all digits
5. Valid if sum % 10 == 0
```

#### `ValidationResult`
```python
@dataclass
class ValidationResult:
    card: CardAsset                    # The validated card
    status: CardStatus                 # Traffic light status
    message: str                       # Human-readable result
    response_code: Optional[str]       # API response code
    bank_name: Optional[str]           # Issuing bank name
    country: Optional[str]             # Issuing country
    risk_score: Optional[int]          # 0-100 risk score
    validated_at: datetime             # Timestamp
    validation_method: str = "stripe_setup_intent"
```

**Computed Properties:**
| Property | Returns | Description |
|----------|---------|-------------|
| `is_live` | `bool` | `status == CardStatus.LIVE` |
| `traffic_light` | `str` | Emoji for GUI: 🟢🔴🟡🟠 |

#### `MerchantKey`
```python
@dataclass
class MerchantKey:
    provider: str              # "stripe", "braintree", "adyen"
    public_key: str            # Publishable/public key
    secret_key: Optional[str]  # Secret key (required for Stripe)
    merchant_id: Optional[str] # Merchant ID (Braintree/Adyen)
    is_live: bool = True       # Whether key is still active
    last_used: Optional[datetime] = None
    success_count: int = 0     # Successful validations
    fail_count: int = 0        # Failed validations
```

---

## 3. Validation Pipeline

```
CardAsset Input
       │
       ▼
┌──────────────┐
│ Luhn Check   │──── FAIL ──► DEAD ("Invalid card number")
└──────┬───────┘
       │ PASS
       ▼
┌──────────────┐
│ BIN Risk     │──── HIGH RISK ──► RISKY ("High-risk BIN", score=80)
│ Check        │
└──────┬───────┘
       │ OK
       ▼
┌──────────────┐
│ Stripe Key   │──── NO KEY ──► BIN-Only Fallback
│ Available?   │
└──────┬───────┘
       │ YES
       ▼
┌──────────────┐
│ Stripe       │──── ERROR ──► DEAD (with decline code)
│ SetupIntent  │──── NETWORK ERROR ──► UNKNOWN
│ Validation   │──── 3DS REQUIRED ──► LIVE (score=40)
└──────┬───────┘
       │ SUCCEEDED
       ▼
   LIVE (score=20)
```

---

## 4. BIN Intelligence Database

### 4.1 High-Risk BINs (50+ entries)

Cards with these BINs are flagged as RISKY (score=80) before any API validation:

**Virtual/Prepaid Cards:**
`414720`, `424631`, `428837`, `431274`, `438857`, `453245`, `476173`, `485932`, `486208`, `489019`, `511563`, `517805`, `524897`, `530136`, `531993`, `540443`, `542418`, `548760`, `552289`, `558848`

**Gift Card BINs:**
`604646`, `627571`, `636297`, `639463`

**High Chargeback Rate BINs:**
`400115`, `401795`, `403587`, `407120`, `410039`, `414709`, `417500`, `421203`, `423223`, `426684`, `428485`, `430906`, `433610`, `436797`, `440066`

**Known Fraud Pattern BINs:**
`453201`, `476042`, `486505`, `492181`, `498824`, `516732`, `524364`, `533248`, `540735`, `548219`

### 4.2 BIN Database (60+ entries)

Each BIN entry contains: `bank`, `country`, `type` (credit/debit), `level` (classic/gold/platinum/signature/world/centurion).

**Coverage by Network:**

| Network | BINs | Banks Covered |
|---------|------|---------------|
| **Visa** | 25+ | Chase, BofA, Capital One, Citi, Wells Fargo, US Bank, PNC, TD, USAA, Navy Federal, Fifth Third, Regions, Huntington |
| **Mastercard** | 10+ | Chase, BofA, Capital One, Citi, Wells Fargo, US Bank, Barclays |
| **Amex** | 8 | Green, Gold, Platinum, Centurion, Business, Corporate |
| **Discover** | 4 | IT, Cashback, Miles |
| **UK Banks** | 7 | Barclays, HSBC, Lloyds, NatWest, Santander, Monzo, Revolut |
| **Canadian** | 5 | TD Canada, RBC, BMO, Scotiabank, CIBC |
| **Australian** | 4 | Commonwealth, Westpac, ANZ, NAB |
| **European** | 6 | Deutsche Bank, Commerzbank, BNP Paribas, Credit Agricole, ING, Rabobank |

### 4.3 Country Risk Factors

| Country | Risk Factor | Notes |
|---------|-------------|-------|
| US | 1.0 | Baseline |
| CA | 1.0 | Low risk |
| GB | 1.0 | Low risk |
| AU | 1.0 | Low risk |
| DE | 1.1 | Slightly higher |
| FR | 1.1 | Slightly higher |
| NL | 1.0 | Low risk |
| Default | 1.5 | Unknown countries |

### 4.4 Card Level Trust Factors

Higher-level cards are more trusted by fraud engines (lower risk multiplier):

| Level | Trust Factor | Notes |
|-------|-------------|-------|
| Centurion | 0.7 | Very trusted — ultra-premium |
| Platinum | 0.8 | High trust |
| Signature | 0.85 | High trust |
| World Elite | 0.85 | High trust |
| World | 0.9 | Good trust |
| Gold | 0.9 | Good trust |
| Classic | 1.0 | Baseline |
| Standard | 1.0 | Baseline |

---

## 5. Risk Scoring System

Risk scores range from 0 (safest) to 100 (highest risk):

| Score | Category | Meaning |
|-------|----------|---------|
| **20** | `live` | Successfully validated via SetupIntent |
| **40** | `3ds_required` | Valid but requires 3D Secure authentication |
| **50** | `bin_only` | BIN exists in database, live status unknown |
| **60** | — | Unknown BIN, cannot validate without API keys |
| **80** | `high_risk` | High-risk BIN detected (prepaid/virtual/gift) |
| **100** | `dead` | Card declined or invalid |

---

## 6. Stripe SetupIntent Validation

### 6.1 Flow

This is the primary validation method. It creates a PaymentMethod and SetupIntent without charging the card.

```
Step 1: POST /v1/payment_methods
        Body: type=card, card[number], card[exp_month], card[exp_year], card[cvc]
        Auth: Bearer <secret_key>
        
        ├── Error response ──► DEAD (with error code)
        └── Success ──► pm_id
        
Step 2: POST /v1/setup_intents
        Body: payment_method=pm_id, confirm=true, usage=off_session
        Auth: Bearer <secret_key>
        
        ├── Error response ──► DEAD (with error:decline_code)
        ├── status=succeeded ──► LIVE (score=20)
        ├── status=requires_action ──► LIVE (score=40, "3DS required")
        ├── status=requires_confirmation ──► LIVE (score=40, "3DS required")
        └── other status ──► DEAD
```

### 6.2 Key Rotation

Merchant keys are rotated round-robin to avoid rate limiting:

```python
key = provider_keys[self._key_index % len(provider_keys)]
self._key_index += 1
```

Each key tracks `success_count`, `fail_count`, and `last_used` for monitoring.

### 6.3 BIN-Only Fallback

When no Stripe keys are available, Cerberus falls back to BIN lookup only:
- BIN found in database → UNKNOWN (score=50), with bank/country info
- BIN not found → UNKNOWN (score=60), "cannot validate without API keys"

---

## 7. Card Input Parsing

`parse_card_input(raw_input)` accepts multiple formats:

| Format | Example |
|--------|---------|
| Pipe-separated | `4242424242424242\|12\|25\|123` |
| Pipe with slash | `4242424242424242\|12/25\|123` |
| Space-separated | `4242424242424242 12 25 123` |
| Spaced PAN | `4242 4242 4242 4242\|12\|2025\|123` |

**Year normalization:** 2-digit years are converted to 4-digit (`25` → `2025`).

**GUI Display Formatting:**
```python
format_result_for_display(result) → {
    "traffic_light": "🟢",
    "status": "LIVE",
    "card": "424242******4242",
    "card_type": "VISA",
    "message": "Card validated successfully",
    "bank": "Chase",
    "country": "US",
    "risk_score": 20,
    "validated_at": "14:32:07"
}
```

---

## 8. Bulk Validation

### `BulkValidator`

Processes card lists with rate limiting and progress tracking.

```python
bulk = BulkValidator(validator, rate_limit=1.0)  # 1 second between requests
results = await bulk.validate_list(cards, progress_callback=on_progress)
summary = bulk.get_summary()
# → {"total": 50, "live": 32, "dead": 12, "unknown": 4, "risky": 2}
```

**Rate Limiting:** Configurable delay between requests (default 1.0s). Essential to avoid Stripe rate limits and merchant key bans.

**Progress Callback:** `callback(current_index, total_count, latest_result)` — used by the GUI to update progress bars and live results.

---

## 9. V7.0: OSINT Verification

### 9.1 Verification Tools

| Tool | URL | Lookup Capability |
|------|-----|-------------------|
| **TruePeopleSearch** | truepeoplesearch.com | Name + State → Address, Phone, Relatives, Property |
| **FastPeopleSearch** | fastpeoplesearch.com | Name/Phone/Email → Cross-reference all data points |
| **Whitepages** | whitepages.com | Name/Phone → Address verification, background |
| **ThatsThem** | thatsthem.com | Name/IP/Email/Phone → Cross-reference identity |

### 9.2 Seven-Step Verification Process

1. Search cardholder name + state on TruePeopleSearch
2. Verify billing address matches known address
3. Cross-reference phone number on FastPeopleSearch
4. Check if email matches any known profiles on ThatsThem
5. Verify property ownership if available (homeowner = higher trust)
6. Check for relatives at same address (co-signers, family cards)
7. Note phone carrier — landline vs mobile vs VoIP

### 9.3 Why OSINT Verification Matters

- Card data from various sources often has typos or automated errors
- Incorrect data leads to AVS mismatch = instant decline
- Verified data ensures billing address, name, phone all match
- Fresh, verified cards from reliable sources have highest success rate

### 9.4 Access

```python
from cerberus_core import get_osint_checklist
checklist = get_osint_checklist()
# Returns full OSINT_VERIFICATION_CHECKLIST dict
```

---

## 10. V7.0: Card Quality Assessment

### 10.1 Quality Tiers

| Tier | Quality | Success Rate | Key Indicators |
|------|---------|-------------|----------------|
| **PREMIUM** | Fresh first-hand | 85-95% | Not tested on any processor, accurate cardholder data, full data (PAN+EXP+CVV+Name+Address+Phone) |
| **DEGRADED** | Resold | 30-50% | Available on multiple marketplaces, may be flagged on Sift/Forter network, partial data |
| **LOW** | Aged | 10-25% | Cardholder may have reported fraud, bank may have issued replacement, likely in fraud databases |

### 10.2 Card Level Compatibility

Each card level has optimal use cases and maximum recommended transaction amounts:

| Level | Best For | Max Amount |
|-------|----------|------------|
| **Centurion** | High-value luxury, Travel, Premium electronics | $50,000 |
| **Platinum** | Electronics, Jewelry, High-value goods | $15,000 |
| **Signature** | Electronics, Gift cards, General | $10,000 |
| **World Elite** | Electronics, Travel, Premium goods | $15,000 |
| **World** | General purchases, Gift cards | $5,000 |
| **Gold** | General purchases, Moderate value | $5,000 |
| **Classic** | Low-value items, Gift cards under $200 | $2,000 |
| **Standard** | Low-value items, Digital goods | $1,500 |

### 10.3 Access

```python
from cerberus_core import get_card_quality_guide
guide = get_card_quality_guide()
# Returns {"quality_indicators": {...}, "level_compatibility": {...}}
```

---

## 11. V7.0: Bank Enrollment Guide

### 11.1 Purpose

Some merchants (notably Google Ads) use **minicharge verification** — they charge a small random amount (e.g., $0.47) and require the user to confirm the exact amount. This requires access to the cardholder's online banking.

### 11.2 When Needed

- Google Ads minicharge verification
- Any merchant that sends small verification charges
- Services requiring bank statement verification

### 11.3 Requirements

- Cardholder's full name (exact as on bank account)
- Last 4 or full card number
- SSN or date of birth (for bank identity verification)
- Cardholder's billing address

### 11.4 Process

1. Navigate to issuing bank's online enrollment page
2. Enter cardholder identity details (name, SSN/DOB)
3. Verify with card number and billing address
4. Set up online banking access
5. View pending transactions to find minicharge amounts
6. Enter minicharge amounts on merchant verification page

### 11.5 Major Bank Enrollment URLs

| Bank | Enrollment URL |
|------|---------------|
| **Chase** | `https://secure.chase.com/web/auth/enrollment` |
| **Bank of America** | `https://secure.bankofamerica.com/enrollment` |
| **Wells Fargo** | `https://connect.secure.wellsfargo.com/auth/enrollment` |
| **Capital One** | `https://verified.capitalone.com/auth/enrollment` |
| **Citi** | `https://online.citi.com/US/login.do` |

### 11.6 Access

```python
from cerberus_core import get_bank_enrollment_guide
guide = get_bank_enrollment_guide()
```

---

## 12. Integration Points

### 12.1 With Target Intelligence

`target_intelligence.py` provides:
- PSP identification per target (which Stripe key to use)
- 3DS likelihood per target (affects risk score interpretation)
- Antifraud system warnings (some systems flag SetupIntent patterns)

### 12.2 With Pre-Flight Validator

`preflight_validator.py` uses Cerberus results to:
- Verify card is LIVE before allowing operation to proceed
- Check card BIN country matches proxy geo-location
- Warn if card level is insufficient for target amount

### 12.3 With Handover Protocol

`handover_protocol.py` includes:
- Card validation result in handover document
- OSINT verification status
- Card quality tier assessment
- Recommended maximum transaction amount based on card level

### 12.4 With 3DS Strategy

`three_ds_strategy.py` uses Cerberus BIN data to:
- Predict 3DS likelihood for the specific BIN
- Recommend avoidance strategies (amount splitting, BIN selection)
- Provide fallback handling if 3DS is triggered

---

## 13. API Reference

### CerberusValidator

```python
validator = CerberusValidator(keys=[MerchantKey(...)])
async with validator:
    result = await validator.validate(card)
```

| Method | Args | Returns | Description |
|--------|------|---------|-------------|
| `validate(card)` | `CardAsset` | `ValidationResult` | Main validation entry point |
| `add_key(key)` | `MerchantKey` | `None` | Add merchant key to rotation pool |
| `parse_card_input(raw)` | `str` | `Optional[CardAsset]` | Parse various card formats |
| `format_result_for_display(result)` | `ValidationResult` | `Dict` | Format for GUI display |

### BulkValidator

```python
bulk = BulkValidator(validator, rate_limit=1.0)
results = await bulk.validate_list(cards, progress_callback)
summary = bulk.get_summary()
```

| Method | Args | Returns | Description |
|--------|------|---------|-------------|
| `validate_list(cards, callback)` | `List[CardAsset], Callable` | `List[ValidationResult]` | Bulk validate with rate limiting |
| `get_summary()` | — | `Dict[str, int]` | Count by status |

### Module-Level Functions (V7.0)

| Function | Returns | Description |
|----------|---------|-------------|
| `get_osint_checklist()` | `Dict` | OSINT verification tools and steps |
| `get_card_quality_guide()` | `Dict` | Quality tiers and level compatibility |
| `get_bank_enrollment_guide()` | `Dict` | Bank enrollment URLs and process |

---

**End of Cerberus Deep Dive** | **TITAN V7.0 SINGULARITY**
