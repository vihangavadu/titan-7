# TITAN V8.1 — Persona Enrichment Engine

## Problem Statement

**Generic bank declines** occur when a persona's purchase history doesn't match the target item being purchased. For example:

- A "kitchen shopping" persona suddenly buying **gaming gift cards** → ❌ DECLINE
- A 65-year-old retiree buying **gaming peripherals** → ❌ DECLINE  
- A tech professional buying **baby products** with no prior history → ❌ DECLINE

Antifraud systems (Forter, Riskified, Stripe Radar) analyze **purchase pattern coherence** and flag out-of-pattern transactions as high-risk.

## Solution: AI-Powered Demographic Profiling

The **Persona Enrichment Engine** predicts realistic purchase patterns from demographic data and validates purchase coherence **BEFORE** the operation.

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  PERSONA ENRICHMENT ENGINE                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. DemographicProfiler                                         │
│     ├─ Extract signals from name/email/address/age             │
│     ├─ Infer occupation from email domain                      │
│     ├─ Classify age group (Gen Z, Millennial, Gen X, Boomer)   │
│     └─ Calculate income level & tech savviness                 │
│                                                                  │
│  2. PurchasePatternPredictor                                    │
│     ├─ Predict likely purchases from demographics              │
│     ├─ 18 purchase categories with likelihood scores           │
│     └─ Weighted by age (60%) + occupation (40%)                │
│                                                                  │
│  3. CoherenceValidator                                          │
│     ├─ Validate target purchase against predicted patterns     │
│     ├─ Block incoherent purchases (likelihood <25%)            │
│     └─ Recommend alternative merchants/categories              │
│                                                                  │
│  4. OSINTEnricher (OPTIONAL)                                    │
│     ├─ Sherlock: username → social profiles                    │
│     ├─ Holehe: email → registered accounts                     │
│     └─ Infer interests from discovered accounts                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Demographic Signals

### Age Groups
- **Gen Z** (18-27): Gaming 75%, Streaming 80%, Food Delivery 75%
- **Millennial** (28-43): Tech Gadgets 70%, Home Goods 60%, Fitness 55%
- **Gen X** (44-59): Home Goods 75%, Automotive 60%, Health 65%
- **Boomer** (60-78): Health 80%, Pharmacy 75%, Garden 65%

### Occupation Categories
- **Tech**: Gaming 70%, Tech Gadgets 85%, Software 80%
- **Healthcare**: Health 75%, Fitness 65%, Pharmacy 70%
- **Student**: Gaming 70%, Food Delivery 80%, Streaming 85%
- **Retired**: Health 85%, Pharmacy 80%, Garden 70%

### Email Domain Signals
- `@google.com`, `@microsoft.com` → Tech occupation, high tech savvy
- `.edu`, `university`, `college` → Student, books + gaming
- `@aol.com` → Older demographic, health + garden
- Generic (`@gmail.com`) → No signal, use age/name only

---

## Purchase Categories (18 total)

| Category | Typical Merchants | Avg Amount |
|----------|------------------|------------|
| Gaming | Steam, G2A, Eneba, GameStop | $15-$80 |
| Tech Gadgets | Amazon, Best Buy, Newegg | $20-$150 |
| Home Goods | Amazon, Target, Wayfair | $25-$120 |
| Fashion | Amazon, Target, Macy's | $30-$150 |
| Food Delivery | UberEats, DoorDash, Grubhub | $15-$60 |
| Streaming | Netflix, Spotify, Hulu | $10-$25 |
| Health & Wellness | CVS, Walgreens, Amazon | $15-$80 |
| Pharmacy | CVS, Walgreens, Walmart | $10-$100 |
| Books & Media | Amazon, Barnes & Noble | $10-$40 |
| Automotive | AutoZone, Advance Auto | $15-$100 |
| Garden & Outdoor | Home Depot, Lowe's | $20-$90 |
| Fitness & Sports | Amazon, Dick's Sporting | $25-$120 |
| Baby & Kids | Amazon, Target, BuyBuyBaby | $20-$100 |
| Travel | Expedia, Booking, Airbnb | $50-$500 |
| Software & Apps | Microsoft, Adobe, Steam | $10-$150 |
| Beauty & Cosmetics | Sephora, Ulta, Amazon | $20-$100 |
| Tools & Hardware | Home Depot, Harbor Freight | $25-$200 |
| Home Decor | Wayfair, Target, IKEA | $20-$150 |

---

## Coherence Thresholds

- **≥60% likelihood** → ✅ **COHERENT** (Pass)
- **40-60% likelihood** → ✅ **COHERENT** (Pass with info)
- **25-40% likelihood** → ⚠️ **CAUTION** (Warning)
- **<25% likelihood** → 🚫 **INCOHERENT** (Block/Warn)

---

## Usage

### CLI Testing

```bash
cd /opt/titan/core
python3 persona_enrichment_engine.py \
  --name "John Smith" \
  --email "john.smith@gmail.com" \
  --age 35 \
  --state "TX" \
  --merchant "g2a.com" \
  --item "Steam Gift Card" \
  --amount 50.00
```

**Output:**
```
═══════════════════════════════════════════════════════════════
DEMOGRAPHIC PROFILE
═══════════════════════════════════════════════════════════════
Name: John Smith
Age: 35 (millennial)
Occupation: unemployed
Income: middle
Tech Savvy: 50%
Online Shopper: 65%

═══════════════════════════════════════════════════════════════
PREDICTED PURCHASE PATTERNS (Top 5)
═══════════════════════════════════════════════════════════════
1. Tech Gadgets: 70% likelihood
   Merchants: amazon.com, bestbuy.com, newegg.com
   Items: USB Cable, Phone Case, Wireless Charger
   Amount: $20-$150

2. Streaming Services: 75% likelihood
   Merchants: netflix.com, spotify.com, hulu.com
   Items: Monthly Subscription, Premium Upgrade
   Amount: $10-$25

3. Gaming: 55% likelihood
   Merchants: steampowered.com, g2a.com, eneba.com
   Items: Game Key, Gift Card, Gaming Mouse
   Amount: $15-$80

═══════════════════════════════════════════════════════════════
COHERENCE VALIDATION
═══════════════════════════════════════════════════════════════
Target: g2a.com (Steam Gift Card)
Coherent: ✅ YES
Confidence: 55%
Category: gaming
Likelihood: 55%

✅ COHERENT: John Smith buying 'gaming' is consistent with profile (likelihood=55%).
═══════════════════════════════════════════════════════════════
```

### Integration with Preflight Validator

The enrichment engine is **automatically wired** into the preflight validator. To use it:

```python
from preflight_validator import PreFlightValidator

validator = PreFlightValidator(
    profile_path=profile_path,
    proxy_url=proxy_url,
    billing_region=billing_region
)

# Set persona data for coherence check
validator._persona_data = {
    'name': 'John Smith',
    'email': 'john.smith@gmail.com',
    'age': 35,
    'city': 'Austin',
    'state': 'TX',
    'country': 'US',
    'zip': '78705',
}
validator._target_merchant = 'g2a.com'
validator._target_item = 'Steam Gift Card'
validator._target_amount = 50.00

# Run all checks (includes coherence validation)
report = validator.run_all_checks()

# Check coherence result
coherence_check = next((c for c in report.checks if c.name == "Purchase Coherence"), None)
if coherence_check:
    print(f"Coherence: {coherence_check.status.value}")
    print(f"Message: {coherence_check.message}")
    print(f"Recommended: {coherence_check.details.get('recommended_merchants', [])}")
```

---

## OSINT Tools (Optional)

Self-hosted OSINT tools enhance profiling accuracy by discovering real online accounts and interests.

### Installation

```bash
cd /opt/titan/scripts
sudo chmod +x install_osint_tools.sh

# Install all tools (recommended)
sudo ./install_osint_tools.sh all

# Install minimal (Sherlock + Holehe only)
sudo ./install_osint_tools.sh minimal

# Custom selection
sudo ./install_osint_tools.sh custom
```

### Supported Tools

1. **Sherlock** — GitHub username → social profiles (2500+ sites)
2. **Holehe** — Email → registered accounts (120+ services)
3. **Maigret** — Username → 2500+ sites (advanced Sherlock)
4. **theHarvester** — Email → public data sources (OSINT aggregator)
5. **Photon** — Web scraper for person data

### Enabling OSINT

```python
from persona_enrichment_engine import PersonaEnrichmentEngine

# Enable OSINT enrichment
engine = PersonaEnrichmentEngine(enable_osint=True)

profile, patterns, coherence = engine.enrich_and_validate(
    name="John Smith",
    email="john.smith@gmail.com",
    age=35,
    address={'state': 'TX', 'country': 'US'},
    target_merchant="g2a.com"
)

# OSINT will discover registered accounts and infer interests
# e.g., if email is registered on Steam → gaming interest boosted
```

---

## Example Scenarios

### ✅ PASS: Coherent Purchase

**Persona:**
- Name: Sarah Johnson
- Email: sarah.johnson@google.com
- Age: 28
- Occupation: Tech (inferred from @google.com)

**Target:** `bestbuy.com` — "Wireless Mouse" ($45)

**Result:**
- Category: `tech_gadgets`
- Likelihood: **85%** (Tech occupation + Millennial age)
- Verdict: ✅ **COHERENT** — Tech professional buying tech gadgets is highly consistent

---

### ⚠️ CAUTION: Slightly Out of Pattern

**Persona:**
- Name: Robert Williams
- Email: robert.w@aol.com
- Age: 68
- Occupation: Retired (inferred from @aol.com)

**Target:** `amazon.com` — "Gaming Headset" ($80)

**Result:**
- Category: `gaming`
- Likelihood: **10%** (Boomer age group has 10% gaming likelihood)
- Verdict: ⚠️ **CAUTION** — Retiree buying gaming gear is unusual but not impossible

---

### 🚫 BLOCK: Incoherent Purchase

**Persona:**
- Name: Margaret Davis
- Email: margaret.davis@aol.com
- Age: 72
- Occupation: Retired

**Target:** `g2a.com` — "Steam Gift Card $100"

**Result:**
- Category: `gaming`
- Likelihood: **10%**
- Verdict: 🚫 **INCOHERENT** — 72-year-old retiree buying gaming gift cards is highly suspicious
- **Recommended alternatives:**
  - `cvs.com` (pharmacy)
  - `amazon.com` (home goods)
  - `homedepot.com` (garden)

---

## Integration Points

### 1. Profile Generation (`genesis_core.py`)

When generating profiles, use archetype-based purchase history:

```python
from genesis_core import GenesisCore, ProfileArchetype

core = GenesisCore()

# Generate profile with GAMER archetype
profile = core.forge_archetype_profile(
    archetype=ProfileArchetype.GAMER,
    target=target_preset,
    persona_name="Alex Chen",
    persona_email="alex.chen@gmail.com",
    billing_address=address,
    age_days=90
)

# Profile will have gaming-heavy purchase history:
# - Steam, G2A, Eneba merchants
# - Gaming peripherals, gift cards
# - Discord, Twitch cookies
```

### 2. Preflight Validation (`preflight_validator.py`)

Automatically validates coherence before operations:

```python
# Coherence check runs automatically if persona data is set
validator._persona_data = {...}
validator._target_merchant = "g2a.com"
report = validator.run_all_checks()

# Check will appear in report.checks as "Purchase Coherence"
```

### 3. Purchase History Engine (`purchase_history_engine.py`)

Generate purchase history matching predicted patterns:

```python
from persona_enrichment_engine import PersonaEnrichmentEngine, DemographicProfiler

profiler = DemographicProfiler()
profile = profiler.profile(name, email, age, address)

predictor = PurchasePatternPredictor()
patterns = predictor.predict(profile)

# Use top 3 categories for purchase history
top_categories = list(patterns.keys())[:3]
merchants = []
for cat in top_categories:
    merchants.extend(patterns[cat].typical_merchants[:2])

# Generate purchase history with these merchants
config = PurchaseHistoryConfig(
    cardholder=cardholder_data,
    target_merchants=merchants  # Use predicted merchants
)
```

---

## Configuration

### Adjusting Thresholds

Edit `persona_enrichment_engine.py`:

```python
class CoherenceValidator:
    # Coherence thresholds
    COHERENT_THRESHOLD = 0.40  # Default: 40%
    CAUTION_THRESHOLD = 0.25   # Default: 25%
    INCOHERENT_THRESHOLD = 0.25  # Default: 25%
```

### Adding Custom Categories

Add to `PURCHASE_CATEGORY_DEFINITIONS`:

```python
"crypto": PurchaseCategory(
    name="Cryptocurrency",
    likelihood=0.0,
    typical_merchants=["coinbase.com", "binance.com", "kraken.com"],
    typical_items=["Bitcoin", "Ethereum", "Trading Fee"],
    avg_amount_range=(50.0, 500.0),
)
```

Add to demographic patterns:

```python
AgeGroup.MILLENNIAL: {
    # ... existing categories ...
    "crypto": 0.45,  # 45% likelihood for millennials
}
```

---

## Troubleshooting

### Issue: All purchases marked as SKIP

**Cause:** Persona data not set in preflight validator

**Fix:**
```python
validator._persona_data = {
    'name': 'John Smith',
    'email': 'john@example.com',
    'age': 35,
    # ... other fields
}
validator._target_merchant = 'target.com'
```

### Issue: OSINT tools not working

**Cause:** Tools not installed or incorrect path

**Fix:**
```bash
# Verify installation
ls -la /opt/titan/osint_tools/

# Reinstall if needed
sudo /opt/titan/scripts/install_osint_tools.sh all
```

### Issue: Coherence always passes

**Cause:** Thresholds too low or category mapping missing

**Fix:**
1. Check `MERCHANT_CATEGORY_MAP` includes your target merchant
2. Adjust `COHERENT_THRESHOLD` if needed
3. Verify demographic patterns include the category

---

## Performance

- **Profiling**: <1ms (pure Python heuristics)
- **Pattern Prediction**: <5ms (dictionary lookups + weighted math)
- **Coherence Validation**: <10ms (category matching + scoring)
- **OSINT Enrichment**: 5-30 seconds (network-dependent, optional)

**Recommendation:** Disable OSINT for real-time operations, use for profile generation only.

---

## Version History

- **V8.1.0** (Feb 2026) — Initial release
  - 18 purchase categories
  - 5 age groups, 12 occupation categories
  - Email domain inference
  - OSINT integration (optional)
  - Preflight validator integration

---

## Credits

- Demographic purchase patterns based on consumer behavior research
- Email domain signals from common corporate/educational domains
- OSINT tools: Sherlock, Holehe, Maigret, theHarvester, Photon (all open-source)

---

## License

TITAN Internal Use Only — Proprietary
