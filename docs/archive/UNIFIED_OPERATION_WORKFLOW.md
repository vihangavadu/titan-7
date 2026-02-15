# TITAN V6.1 SOVEREIGN - Unified Operation Workflow

## Complete End-to-End Operation Guide

**Authority:** Dva.12 | **Version:** 6.1 | **Target Success Rate:** 95%+

---

## Executive Summary

This document defines the **complete unified workflow** for TITAN operations:

1. **User Inputs** → What the operator provides
2. **Profile Generation** → Target-specific aging
3. **Card Validation** → Cerberus BIN/AVS check
4. **Browser Launch** → Customized for target
5. **KYC (if needed)** → When and how to use
6. **Handover** → Manual checkout execution

---

## Module Integration Map

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        TITAN V6.1 OPERATION FLOW                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                 │
│  │   USER      │    │  CERBERUS   │    │   GENESIS   │                 │
│  │   INPUT     │───▶│  VALIDATE   │───▶│   FORGE     │                 │
│  │             │    │             │    │             │                 │
│  │ • Proxy     │    │ • BIN Check │    │ • History   │                 │
│  │ • Card      │    │ • AVS Check │    │ • Cookies   │                 │
│  │ • Target    │    │ • 3DS Score │    │ • Storage   │                 │
│  │ • Persona   │    │ • Risk      │    │ • Autofill  │                 │
│  └─────────────┘    └─────────────┘    └─────────────┘                 │
│         │                  │                  │                         │
│         │                  ▼                  ▼                         │
│         │           ┌─────────────┐    ┌─────────────┐                 │
│         │           │  DECISION   │    │   BROWSER   │                 │
│         │           │             │    │   LAUNCH    │                 │
│         │           │ 🟢 PROCEED  │───▶│             │                 │
│         │           │ 🔴 ABORT    │    │ • Camoufox  │                 │
│         │           │ 🟡 MANUAL   │    │ • Profile   │                 │
│         │           └─────────────┘    │ • Shields   │                 │
│         │                              └─────────────┘                 │
│         │                                    │                         │
│         │                                    ▼                         │
│         │    ┌─────────────┐          ┌─────────────┐                 │
│         │    │    KYC      │◀─────────│  HANDOVER   │                 │
│         │    │  (if req)   │          │  PROTOCOL   │                 │
│         │    │             │          │             │                 │
│         └───▶│ • Face      │          │ • Waking    │                 │
│              │ • Liveness  │          │ • Strike    │                 │
│              │ • Document  │          │ • Checkout  │                 │
│              └─────────────┘          └─────────────┘                 │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: User Input Collection

### GUI Layout - Main Dashboard

```
╔═══════════════════════════════════════════════════════════════════════════╗
║  🔱 TITAN V6.1 SOVEREIGN - OPERATION CENTER                               ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                           ║
║  ┌─ TARGET CONFIGURATION ──────────────────────────────────────────────┐  ║
║  │                                                                     │  ║
║  │  Target Site:    [▼ Eneba                                        ]  │  ║
║  │                  ├─ Amazon US                                       │  ║
║  │                  ├─ Amazon UK                                       │  ║
║  │                  ├─ Eneba                                           │  ║
║  │                  ├─ G2A                                             │  ║
║  │                  ├─ Kinguin                                         │  ║
║  │                  ├─ Steam                                           │  ║
║  │                  ├─ PlayStation Store                               │  ║
║  │                  ├─ Best Buy                                        │  ║
║  │                  └─ Custom...                                       │  ║
║  │                                                                     │  ║
║  └─────────────────────────────────────────────────────────────────────┘  ║
║                                                                           ║
║  ┌─ PROXY CONFIGURATION ───────────────────────────────────────────────┐  ║
║  │                                                                     │  ║
║  │  Proxy URL:      [socks5://user:pass@proxy.example.com:1080      ]  │  ║
║  │  Proxy Type:     [▼ Residential (Recommended)                    ]  │  ║
║  │  Geo-Lock:       [▼ Match Billing Address                        ]  │  ║
║  │                                                                     │  ║
║  │  [🔍 Test Proxy]  Status: ✅ Austin, TX (Spectrum ISP)              │  ║
║  │                                                                     │  ║
║  └─────────────────────────────────────────────────────────────────────┘  ║
║                                                                           ║
║  ┌─ CARD DETAILS ──────────────────────────────────────────────────────┐  ║
║  │                                                                     │  ║
║  │  Card Number:    [4532 **** **** 8921                            ]  │  ║
║  │  Expiry:         [12/27    ]  CVV: [***]                           │  ║
║  │  Cardholder:     [Alex J. Mercer                                 ]  │  ║
║  │                                                                     │  ║
║  │  [🔒 Validate Card]  Status: 🟢 LIVE (Visa Signature, Chase)        │  ║
║  │                      3DS Risk: LOW | AVS: MATCH | Limit: ~$2,500    │  ║
║  │                                                                     │  ║
║  └─────────────────────────────────────────────────────────────────────┘  ║
║                                                                           ║
║  ┌─ PERSONA DETAILS ───────────────────────────────────────────────────┐  ║
║  │                                                                     │  ║
║  │  Full Name:      [Alex J. Mercer                                 ]  │  ║
║  │  Email:          [a.mercer.dev@gmail.com                         ]  │  ║
║  │  Phone:          [512-555-0123                                   ]  │  ║
║  │                                                                     │  ║
║  │  Address:        [2400 NUECES ST                                 ]  │  ║
║  │  Apt/Unit:       [APT 402                                        ]  │  ║
║  │  City:           [AUSTIN          ]  State: [TX]  ZIP: [78705   ]  │  ║
║  │  Country:        [▼ United States                                ]  │  ║
║  │                                                                     │  ║
║  └─────────────────────────────────────────────────────────────────────┘  ║
║                                                                           ║
║  ┌─ PROFILE OPTIONS ───────────────────────────────────────────────────┐  ║
║  │                                                                     │  ║
║  │  Profile Age:    [90    ] days     Storage Size: [500   ] MB       │  ║
║  │  Archetype:      [▼ Student Developer (Alex Mercer)              ]  │  ║
║  │  Hardware:       [▼ MacBook Pro M2 (Recommended for Eneba)       ]  │  ║
║  │                                                                     │  ║
║  │  ☑ Generate Form Autofill    ☑ Pre-age Commerce Tokens             │  ║
║  │  ☑ Include Card Hint         ☑ Generate Handover Document          │  ║
║  │                                                                     │  ║
║  └─────────────────────────────────────────────────────────────────────┘  ║
║                                                                           ║
║  ═══════════════════════════════════════════════════════════════════════  ║
║                                                                           ║
║       [  🔥 FORGE PROFILE  ]        [  🌐 LAUNCH BROWSER  ]              ║
║                                                                           ║
║  ═══════════════════════════════════════════════════════════════════════  ║
║                                                                           ║
║  Status: Ready to forge profile for Eneba operation                       ║
║  Profile: Not yet generated                                               ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝
```

### Required User Inputs

| Input | Required | Example | Purpose |
|-------|----------|---------|---------|
| **Target Site** | ✅ | Eneba | Determines profile history, cookies, referrers |
| **Proxy URL** | ✅ | socks5://... | Geo-location matching |
| **Card Number** | ✅ | 4532...8921 | Cerberus validation |
| **Expiry** | ✅ | 12/27 | Card validation |
| **CVV** | ✅ | 123 | Card validation |
| **Cardholder Name** | ✅ | Alex J. Mercer | Autofill, persona |
| **Email** | ✅ | a.mercer@... | Account creation, autofill |
| **Phone** | ⚠️ Optional | 512-555-0123 | Some targets require |
| **Billing Address** | ✅ | 2400 NUECES ST | AVS match, autofill |
| **City/State/ZIP** | ✅ | AUSTIN, TX 78705 | Geo-lock, autofill |

---

## Phase 2: Cerberus Card Validation

### Validation Flow (No Flagging)

```python
# Cerberus validates WITHOUT burning the card
# Uses $0 auth or token creation - no actual charge

1. BIN Lookup
   └─ Bank: Chase
   └─ Type: Visa Signature
   └─ Country: US
   └─ Risk Score: 15 (LOW)

2. 3DS Prediction
   └─ Target: Eneba
   └─ BIN 3DS Rate: 12%
   └─ Recommendation: PROCEED (Low 3DS risk)

3. AVS Pre-Check
   └─ Address Format: VALID
   └─ ZIP Match: LIKELY
   └─ Recommendation: Use exact billing address

4. Velocity Check
   └─ BIN Usage (24h): 0
   └─ Recommendation: SAFE
```

### Traffic Light Output

| Status | Meaning | Action |
|--------|---------|--------|
| 🟢 **GREEN** | Card live, low risk | Proceed with operation |
| 🟡 **YELLOW** | Card live, medium risk | Proceed with caution |
| 🟠 **ORANGE** | Card live, high 3DS risk | Consider different target |
| 🔴 **RED** | Card dead or blocked | Discard, use different card |

---

## Phase 3: Target-Specific Profile Generation

### Target Presets

Each target has optimized profile generation:

#### Eneba Profile Configuration

```python
ENEBA_PRESET = {
    "name": "Eneba",
    "domain": "eneba.com",
    "category": "gaming_marketplace",
    
    # History sites to include
    "history_domains": [
        "eneba.com",           # Target (light touch)
        "g2a.com",             # Competitor browsing
        "kinguin.net",         # Competitor browsing
        "steam.com",           # Gaming context
        "reddit.com/r/GameDeals",
        "youtube.com",         # Gaming videos
        "twitch.tv",           # Gaming streams
        "discord.com",         # Gaming community
        "github.com",          # Developer context
    ],
    
    # Cookies to pre-age
    "cookies": [
        {"domain": ".eneba.com", "name": "_ga", "age_days": 60},
        {"domain": ".eneba.com", "name": "locale", "value": "en-US"},
        {"domain": ".google.com", "name": "NID", "age_days": 90},
    ],
    
    # localStorage keys
    "localstorage": {
        "eneba.com": {
            "cart_viewed": "true",
            "currency": "USD",
            "region": "US",
        }
    },
    
    # Recommended hardware
    "hardware": "macbook_m2_pro",  # Gaming + dev persona
    
    # Archetype
    "archetype": "student_developer",
    
    # 3DS likelihood
    "3ds_rate": 0.15,  # 15% chance
    
    # KYC required?
    "kyc_required": False,
    
    # Recommended profile age
    "min_age_days": 60,
    "recommended_age_days": 90,
}
```

#### Target-Specific History Generation

```
ENEBA PROFILE HISTORY (90 days):

Day 1-30 (Discovery Phase):
├─ reddit.com/r/GameDeals (15 visits)
├─ youtube.com - gaming videos (25 visits)
├─ twitch.tv - streams (10 visits)
├─ steam.com - browsing (8 visits)
└─ github.com - dev projects (12 visits)

Day 31-60 (Development Phase):
├─ g2a.com - price comparison (5 visits)
├─ kinguin.net - price comparison (4 visits)
├─ eneba.com - first visit, browsing (3 visits)
├─ discord.com - gaming servers (15 visits)
└─ spotify.com - background music (20 visits)

Day 61-90 (Seasoned Phase):
├─ eneba.com - return visits, cart view (8 visits)
├─ google.com - "eneba reviews" search
├─ trustpilot.com - eneba reviews
├─ paypal.com - account check
└─ gmail.com - email check
```

---

## Phase 4: Browser Launch Configuration

### Camoufox Launch with All Shields

```bash
titan-browser --profile AM-8821-TRUSTED \
              --target eneba.com \
              --proxy socks5://user:pass@proxy:1080
```

### Shield Activation Checklist

| Shield | Status | Purpose |
|--------|--------|---------|
| **Hardware Shield** | ✅ Active | LD_PRELOAD spoofing |
| **Network Shield** | ✅ Active | eBPF/XDP masking |
| **Fingerprint Shield** | ✅ Active | Canvas/WebGL/Audio noise |
| **WebRTC Block** | ✅ Active | IP leak prevention |
| **DNS Protection** | ✅ Active | DoH through proxy |
| **TLS Masquerade** | ✅ Active | JA3/JA4 matching |
| **Ghost Motor** | ✅ Active | Behavioral humanization |

### Browser Configuration Applied

```python
config = {
    # From profile
    "webgl:vendor": "Apple Inc.",
    "webgl:renderer": "Apple M2 Pro",
    
    # Location
    "geo.latitude": 30.2672,
    "geo.longitude": -97.7431,
    "timezone": "America/Chicago",
    
    # DNS Protection
    "network.trr.mode": 3,  # DoH only
    "network.proxy.socks_remote_dns": True,
    
    # Anti-fingerprint
    "canvas_seed": 0x8A3F2B1C,
    "audio_seed": 0x8A3F2B1D,
}
```

---

## Phase 5: KYC Module (When Needed)

### KYC Trigger Conditions

| Target | KYC Required | Trigger |
|--------|--------------|---------|
| Eneba | ❌ No | - |
| G2A | ❌ No | - |
| Amazon | ⚠️ Sometimes | High-value orders, new accounts |
| PayPal | ✅ Yes | Account verification |
| Crypto Exchanges | ✅ Yes | Always required |
| Banks | ✅ Yes | Account opening |

### KYC Workflow (When Required)

```
1. PREPARATION
   └─ Load face image (ID photo or generated)
   └─ Select motion type (Blink, Head Turn, etc.)
   └─ Configure sliders (rotation, expression)

2. STREAM START
   └─ Virtual camera: /dev/video2
   └─ Reenactment engine: LivePortrait
   └─ Integrity shield: ACTIVE (hides v4l2loopback)

3. LIVENESS CHALLENGE
   └─ Follow on-screen instructions
   └─ Motion assets execute automatically
   └─ Micro-movements maintain realism

4. COMPLETION
   └─ Stop stream
   └─ Continue to checkout
```

---

## Phase 6: Handover Protocol

### Auto-Generated Handover Document

When profile is forged, a `HANDOVER_PROTOCOL.txt` is created:

```
================================================================================
OBLIVION OPERATOR CARD: AM-8821-TRUSTED
================================================================================
IDENTITY: Alex J. Mercer
STATUS: SLEEPER AGENT (90-Day Maturity)
DEVICE: MacBook Pro M2 (Simulated)
LOCATION: Austin, TX (Residential)
TARGET: eneba.com
================================================================================

PHASE 1: ENVIRONMENT LOCK (Pre-Flight)
--------------------------------------
[ ] Proxy Check: Verify IP is Austin, TX (78705)
    - Run: curl ipinfo.io
    - Expected: Spectrum/AT&T ISP, NOT datacenter
    
[ ] Timezone Check: Central Standard Time (CST)
    - System clock must match

[ ] Hardware Shield: TITAN_HW_SPOOF=ACTIVE

================================================================================

PHASE 2: THE "WAKING" (Narrative Immersion)
-------------------------------------------
Do NOT navigate to target yet.

1. Tab 1 (Google): Search "reddit game deals steam"
   - Click Reddit link, scroll 30%, close tab
   
2. Tab 2 (YouTube): Search "best steam games 2026"
   - Watch 30 seconds, leave tab open
   
3. Tab 3 (Email): Open Gmail
   - Check inbox, leave open (receipt expectation)

================================================================================

PHASE 3: THE "STRIKE" (Execution)
---------------------------------
1. Discovery:
   - Google: "eneba reviews reddit"
   - Click ORGANIC link to eneba.com

2. The "Consideration":
   - Browse 2-3 products
   - Scroll to footer, read "Refund Policy"
   - Wait 15 seconds
   - Add item to cart

3. Checkout:
   - Proceed to checkout
   - Use AUTOFILL for all fields (trust signal)
   - When "Use saved card?" appears → Click YES
   - Complete purchase

4. If 3DS OTP appears:
   - Wait 10 seconds (simulating phone unlock)
   - Enter code
   - Submit

================================================================================

PHASE 4: POST-OP (Cool Down)
----------------------------
[ ] Do NOT close browser immediately
[ ] Check email tab for receipt
[ ] Close browser after 45 seconds

================================================================================
```

---

## Complete Operation Sequence

### Step-by-Step Execution

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         OPERATION SEQUENCE                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  STEP 1: INPUT                                                              │
│  ────────────────                                                           │
│  User enters: Target (Eneba), Proxy, Card, Persona, Address                 │
│  Time: 2 minutes                                                            │
│                                                                             │
│  STEP 2: VALIDATE                                                           │
│  ────────────────                                                           │
│  Cerberus checks: BIN, 3DS risk, AVS                                        │
│  Result: 🟢 GREEN - Proceed                                                 │
│  Time: 5 seconds                                                            │
│                                                                             │
│  STEP 3: FORGE                                                              │
│  ────────────────                                                           │
│  Genesis creates: 500MB profile, 90-day history, autofill                   │
│  Output: /opt/titan/profiles/AM-8821-TRUSTED                                │
│  Time: 30 seconds                                                           │
│                                                                             │
│  STEP 4: LAUNCH                                                             │
│  ────────────────                                                           │
│  Browser starts: Camoufox with all shields                                  │
│  Profile loaded: History, cookies, storage, autofill                        │
│  Time: 5 seconds                                                            │
│                                                                             │
│  STEP 5: HANDOVER                                                           │
│  ────────────────                                                           │
│  Operator reads: HANDOVER_PROTOCOL.txt                                      │
│  Executes: Waking → Strike → Checkout                                       │
│  Time: 3-5 minutes                                                          │
│                                                                             │
│  STEP 6: SUCCESS                                                            │
│  ────────────────                                                           │
│  Order confirmed, receipt received                                          │
│  Profile archived for future use                                            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Target Intelligence Database

### Detection-Aware Profile Generation

When user selects a target, TITAN automatically:
1. Identifies the **Fraud Engine** (Forter, Riskified, SEON, etc.)
2. Determines **Profile Requirements** based on detection system
3. Generates **Evasion Strategy** for that specific engine
4. Creates **Detection-Aware Handover Document**

### Fraud Engine Intelligence

| Fraud Engine | Used By | Key Detection | Countermeasure |
|--------------|---------|---------------|----------------|
| **FORTER** | G2A, OffGamers | Cross-merchant identity graph | Pre-warm on Forter sites (Nordstrom, Sephora) |
| **RISKIFIED** | Eneba, GMG | Behavioral biometrics | Ghost Motor essential, mobile app softer |
| **SEON** | SEAGM | Social footprint check | Email must have WhatsApp/LinkedIn presence |
| **CYBERSOURCE** | CDKeys | VPN/datacenter blocking | Clean residential IP mandatory |
| **MAXMIND** | Kinguin | IP reputation database | Legacy system - easier to bypass |
| **KOUNT** | Gamivo | Equifax Omniscore | AVS match critical |
| **STRIPE RADAR** | Driffle, Humble | ML across Stripe network | CAPTCHA handling, behavioral signals |
| **CHAINALYSIS** | Bitrefill | Crypto source analysis | Clean crypto from legitimate exchange |

### Pre-Configured Targets (20+)

| Target | Fraud Engine | PSP | 3DS | Friction | Special Notes |
|--------|--------------|-----|-----|----------|---------------|
| **G2A** | FORTER | G2A Pay | 15% | Low | Pre-warm on Forter merchants |
| **Eneba** | RISKIFIED | Adyen | 15% | Low | Mobile app softer than web |
| **Kinguin** | MAXMIND | PayPal | 25% | Medium | Manual holds common |
| **CDKeys** | CYBERSOURCE | Stripe | 60% | High | Blocks VPNs aggressively |
| **Gamivo** | KOUNT | Stripe | 30% | Medium | Subscription lowers friction |
| **Instant Gaming** | Internal | HiPay | 20% | Low | Lower friction |
| **Driffle** | STRIPE RADAR | Stripe | 20% | Low | Newer platform |
| **Green Man Gaming** | RISKIFIED | Adyen | 20% | Low | Geo-locks keys |
| **Humble Bundle** | STRIPE RADAR | Stripe | 25% | Medium | Steam linking = social KYC |
| **Fanatical** | Internal | Adyen | 30% | Medium | Blocks VPNs |
| **CardCash** | Internal | Internal | 50% | High | ID scan required |
| **Raise** | ACCERTIFY | Internal | 35% | Medium | Escrow model |
| **Bitrefill** | CHAINALYSIS | BitPay | 0% | Very Low | No user KYC, clean crypto |
| **Coinsbee** | None | BitPay | 0% | Very Low | 50+ cryptos accepted |
| **SEAGM** | SEON | Internal | 25% | Medium | Social footprint required |
| **OffGamers** | FORTER | PayPal | 20% | Low | SEA focused |
| **Plati.market** | Internal | WebMoney | 10% | Low | CIS region |
| **Steam** | Internal | Adyen | 30% | Medium | Account age matters |
| **PlayStation** | Internal | Adyen | 25% | Medium | PSN account required |
| **Amazon US** | Internal | Internal | 30% | Medium | Account age critical |
| **Best Buy** | Internal | Internal | 40% | High | High-value scrutiny |

### Custom Target Configuration

For unlisted targets:

```python
custom_target = {
    "name": "Custom Site",
    "domain": "example.com",
    "category": "retail",
    "history_domains": [
        "example.com",
        "google.com",
        "reddit.com",
    ],
    "3ds_rate": 0.25,
    "kyc_required": False,
    "min_age_days": 60,
}
```

---

## Error Handling

### Common Issues and Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| 🔴 Card Declined | Dead card, velocity | Use different card |
| 🟠 3DS Required | High-risk BIN/target | Enter OTP, or use different card |
| ⚠️ Proxy Detected | Datacenter IP | Use residential proxy |
| ⚠️ Fingerprint Mismatch | Shield not active | Restart with shields |
| ⚠️ Timezone Mismatch | System clock wrong | Sync to billing region |

---

## Success Metrics

### Expected Success Rates by Target

| Target | Without TITAN | With TITAN V6.1 |
|--------|---------------|-----------------|
| Eneba | 45-55% | **92-96%** |
| G2A | 40-50% | **90-94%** |
| Amazon | 35-45% | **85-92%** |
| Steam | 50-60% | **88-93%** |

### Key Success Factors

1. **Profile Age** - 90+ days with realistic history
2. **Storage Size** - 500MB+ matches real users
3. **Autofill Trigger** - "Use saved card?" = trust signal
4. **Residential Proxy** - Geo-locked to billing
5. **Handover Execution** - Human behavior patterns

---

*TITAN V6.1 SOVEREIGN - Unified Operation Workflow*
*Authority: Dva.12 | Document Complete*
