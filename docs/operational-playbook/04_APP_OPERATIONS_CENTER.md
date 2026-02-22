# 04 — App: Operations Center

## Overview

**File:** `src/apps/titan_operations.py`
**Color Theme:** Cyan (#00d4ff)
**Tabs:** 5
**Modules Wired:** 38
**Purpose:** The primary app for daily operations. 90% of operator tasks happen here.

The Operations Center follows the natural workflow: select a target → build an identity → validate the card → generate profile and launch browser → review results.

---

## Tab 1: TARGET — Select Site, Proxy, Geo

### What This Tab Does
The operator selects which merchant website to target, configures the proxy/VPN connection, and sets the geographic identity (timezone, location).

### Features

**Target Preset Selector**
- Dropdown of pre-configured targets from `target_presets.py`
- Each preset includes: PSP, 3DS requirements, optimal proxy type, checkout flow details
- Operator selects a preset or enters a custom URL

**Target Discovery**
- "Discover" button triggers `TargetDiscovery` to find new merchant sites
- `AutoDiscovery` runs Google dorking to find sites by PSP, MCC, and geography
- Results displayed in a table with success probability scores

**Target Intelligence**
- "Analyze" button runs `get_target_intel()` on the selected target
- Shows: PSP identification, antifraud systems detected, AVS requirements
- `TargetIntelV2` provides 8-vector golden path scoring (0-100 points)
- Displays breakdown per vector (3DS config, MCC, geography, amount thresholds, etc.)

**Proxy Configuration**
- `ResidentialProxyManager` integration for proxy pool selection
- Country/state/city dropdown for geographic targeting
- Health check button shows proxy pool status
- Exit IP display with reputation score

**Timezone & Location**
- `TimezoneEnforcer` auto-sets timezone based on selected state
- `LocationSpooferLinux` configures GPS coordinates matching billing address
- Visual indicator showing timezone consistency status

### What the Operator Inputs
| Input | Description | Example |
|-------|-------------|---------|
| Target URL | Merchant website URL | `https://store.example.com` |
| Target Preset | Pre-configured target name | "Amazon US" |
| Proxy Country | Geographic proxy selection | "US" |
| Proxy City | City-level targeting (optional) | "Miami" |

### What the Operator Gets
| Output | Description |
|--------|-------------|
| Target Intel Report | PSP, antifraud, 3DS requirements, golden path score |
| Proxy Status | Connected proxy IP + reputation score |
| Timezone Status | Green/red indicator of timezone consistency |
| Discovery Results | Table of discovered targets with success scores |

---

## Tab 2: IDENTITY — Build Persona + Profile

### What This Tab Does
The operator defines the persona (name, address, demographics) that will be used to generate the browser profile and fill checkout forms.

### Features

**Persona Builder**
- Form fields for: first name, last name, DOB, gender, occupation, income range, interests
- `PersonaEnrichmentEngine` auto-fills demographics from minimal data
- `CoherenceValidator` checks internal consistency (age vs credit history, income vs interests)

**Profile Configuration**
- Profile age slider (30-900 days)
- Browser type selector (Firefox/Chrome profile format)
- Interest categories for history generation
- Profile output directory configuration

**Genesis Engine Integration**
- "Generate Profile" button triggers `GenesisEngine.forge_profile()`
- Progress bar shows generation stages
- Profile quality score displayed after generation
- `ProfileRealismEngine` runs automatic quality audit

**Advanced Profile Options**
- `AdvancedProfileGenerator` toggle for 900-day non-linear synthesis
- `PurchaseHistoryEngine` toggle for e-commerce purchase trail injection
- `FormAutofillInjector` pre-configuration with persona data
- `DynamicDataEngine` for checkout-ready data formatting

**Profile Realism Audit**
- Displays 20+ quality dimensions with per-dimension scores
- Gap analysis with specific remediation suggestions
- Re-generate button for low-scoring profiles

### What the Operator Inputs
| Input | Description | Example |
|-------|-------------|---------|
| First Name | Persona first name | "Michael" |
| Last Name | Persona last name | "Thompson" |
| Street Address | Billing address | "1234 Oak Street" |
| City/State/ZIP | Billing location | "Miami, FL, 33101" |
| DOB | Date of birth | "1985-03-15" |
| Profile Age | Days of history to generate | 450 |

### What the Operator Gets
| Output | Description |
|--------|-------------|
| Generated Profile | Complete Firefox profile at specified path |
| Quality Score | 0-100% profile quality rating |
| Gap Report | List of weaknesses with fixes |
| Persona Summary | Enriched persona with demographics |

---

## Tab 3: VALIDATE — Card Check, BIN Intel, Preflight

### What This Tab Does
The operator enters card details and the system validates the card, provides BIN intelligence, and runs preflight checks before launching the browser.

### Features

**Card Validation (Cerberus)**
- Input fields: Card number, expiration (MM/YY), CVV
- "Validate" button triggers `CerberusValidator.validate()`
- Background thread (`ValidateWorker`) prevents UI freeze
- Results show: card status (LIVE/DEAD/RESTRICTED), BIN info, issuer, country, card type/level

**Enhanced BIN Intelligence**
- `BINScoringEngine` provides 10+ quality dimensions
- `OSINTVerifier` cross-references cardholder data
- `CardQualityGrader` assigns A-F quality grade
- AI BIN analysis if Ollama is available

**Preflight Validation**
- `PreFlightValidator` checks all environment conditions
- `PaymentPreflightValidator` checks payment-specific readiness
- Results displayed as checklist: IP reputation ✓, TLS fingerprint ✓, canvas consistency ✓, timezone match ✓, proxy health ✓
- Go/No-Go recommendation with specific issues listed

**Sandbox Testing**
- `PaymentSandboxTester` option to test checkout flow with test cards
- Validates form filling logic before real attempt

### What the Operator Inputs
| Input | Description | Example |
|-------|-------------|---------|
| Card Number | Full card number | 4532XXXXXXXX1234 |
| Expiration | MM/YY format | "03/27" |
| CVV | Security code | "456" |

### What the Operator Gets
| Output | Description |
|--------|-------------|
| Card Status | LIVE / DEAD / RESTRICTED / UNKNOWN |
| BIN Intelligence | Issuer, country, type, level, quality grade |
| Preflight Report | Checklist of all validation checks |
| Go/No-Go | Green (proceed) or Red (issues to fix) |

---

## Tab 4: FORGE & LAUNCH — Generate Profile, Launch Browser

### What This Tab Does
This tab configures and launches the Camoufox browser with all fingerprint shims, behavioral engine, and extensions loaded.

### Features

**Fingerprint Configuration**
- `FingerprintInjector` settings: platform, GPU profile, screen resolution
- `CanvasSubpixelShim` + `CanvasNoiseGenerator` configuration
- `AudioHardener` profile selection (Win10/Win11)
- `FontSanitizer` font whitelist configuration
- `WebGLAngleEngine` GPU selection (RTX 3060, RTX 4060, Intel UHD, etc.)

**Profile Enhancement**
- `IndexedDBSynthesizer` — populate deep app data
- `FirstSessionEliminator` — remove new-profile signals
- `Cache2Synthesizer` — add binary cache mass (target MB)
- `USBPeripheralSynth` — create virtual USB devices
- `WindowsFontProvisioner` — install Windows fonts

**Browser Launch Controls**
- "Launch" button starts Camoufox with full configuration
- Headless/headed mode toggle
- Ghost Motor enable/disable
- Browser extension loading (Ghost Motor JS, TX Monitor JS)
- `HandoverProtocol` manages transition to human operator

**Live Status**
- Fingerprint summary panel showing all active shims
- Module status indicators (green = loaded, yellow = fallback, red = unavailable)
- Browser process health monitor

### What the Operator Inputs
| Input | Description | Example |
|-------|-------------|---------|
| GPU Profile | Claimed GPU for WebGL | "NVIDIA GeForce RTX 3060" |
| Screen Resolution | Claimed screen size | "1920x1080" |
| Cache Size | Target cache mass in MB | 400 |
| Headless Mode | Run without visible window | Off (for manual operation) |

### What the Operator Gets
| Output | Description |
|--------|-------------|
| Running Browser | Camoufox with all shims loaded |
| Fingerprint Summary | All active spoofing values |
| Module Status | Green/yellow/red for each loaded module |
| Handover Signal | "Ready for manual operation" |

---

## Tab 5: RESULTS — Success Tracker, Decline Decoder, History

### What This Tab Does
After operations complete, this tab shows results, decodes decline codes, and provides historical analytics.

### Features

**Transaction Results**
- Real-time results from the current/last operation
- Success/failure status with timestamp
- Phase-by-phase breakdown (which phase failed and why)

**Decline Decoder**
- `DeclineDecoder` translates PSP-specific codes to human-readable reasons
- Supported PSPs: Stripe, Adyen, Authorize.net, ISO 8583, Checkout.com, Braintree
- Each decode shows: reason, category, severity, actionable guidance
- Example: Stripe `card_declined` → "Generic decline — try different card or lower amount"

**Operation History**
- `OperationLog` table showing all past operations
- Filterable by: target, BIN, status, date range
- Sortable by: success rate, amount, date

**Success Metrics**
- `PaymentSuccessMetricsDB` analytics dashboard
- Success rate by: BIN, PSP, target, profile age, time of day
- Trend charts showing improvement over time
- Best-performing combinations highlighted

**Transaction Monitor**
- Live feed from `TransactionMonitor` browser extension
- Captures payment events during checkout
- Displays PSP responses in real-time

### What the Operator Gets
| Output | Description |
|--------|-------------|
| Result Status | Success/failure with full details |
| Decline Decode | Human-readable explanation + guidance |
| History Table | All past operations with filtering |
| Analytics | Success rates and trends |

---

## Module Wiring Summary

| Tab | Modules Used |
|-----|-------------|
| TARGET | target_presets, target_discovery, target_intelligence, titan_target_intel_v2, proxy_manager, timezone_enforcer, location_spoofer_linux |
| IDENTITY | genesis_core, advanced_profile_generator, persona_enrichment_engine, purchase_history_engine, form_autofill_injector, dynamic_data, profile_realism_engine |
| VALIDATE | cerberus_core, cerberus_enhanced, preflight_validator, payment_preflight, payment_sandbox_tester |
| FORGE & LAUNCH | fingerprint_injector, canvas_noise, canvas_subpixel_shim, font_sanitizer, audio_hardener, webgl_angle, indexeddb_lsng_synthesis, first_session_bias_eliminator, forensic_synthesis_engine, usb_peripheral_synth, windows_font_provisioner, ghost_motor_v6, handover_protocol |
| RESULTS | payment_success_metrics, transaction_monitor, titan_operation_logger |

**Total: 38 modules wired into Operations Center**

---

*Next: [05 — App: Intelligence Center](05_APP_INTELLIGENCE_CENTER.md)*
