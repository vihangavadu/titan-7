# 09 — Operator Workflow

## Complete Step-by-Step: What the Human Operator Does

This document describes the exact workflow a human operator follows from startup to operation completion. Every input, every button click, every decision point is covered.

---

## Phase 0: System Startup

### Step 0.1 — Boot Titan OS
The operator boots the Titan OS machine (VPS or local workstation). On boot:
- Hardware shield loads automatically (DMI/SMBIOS spoofing active)
- eBPF network shield loads automatically (TTL=128, Windows TCP stack)
- CPUID/RDTSC shield activates (hypervisor hidden)
- Immutable OS verifies core file integrity
- All AUTO services start: TX Monitor, Intel Monitor, Forensic Monitor, Cockpit

**Operator action:** Power on machine, log into XFCE desktop.

### Step 0.2 — Launch Titan Launcher
The operator clicks the Titan Launcher icon on the desktop (or runs `python3 src/apps/titan_launcher.py`).

The Launcher displays:
- System health dashboard (RAM, disk, CPU)
- Module availability count (e.g., "87/90 modules active")
- AI status (Ollama models loaded)
- VPN status (disconnected)
- 5 app cards with launch buttons

**Operator action:** Review health dashboard. All indicators should be green.

### Step 0.3 — Open Admin Panel → Verify System
Before any operation, the operator opens the Admin Panel and checks:
1. **Tab 1 (Services):** All services running? RAM usage acceptable?
2. **Tab 3 (System):** Module health — any failed imports? System integrity OK?
3. **Tab 5 (Config):** titan.env configured? Proxy credentials set? API keys present?

**Operator action:** Fix any red indicators before proceeding.

---

## Phase 1: Network Setup

### Step 1.1 — Open Network Center
The operator launches the Network Center app.

### Step 1.2 — Connect VPN
In **Tab 1 (Mullvad VPN)**:
1. Select country matching the billing address (e.g., "United States")
2. Select city for closer match (e.g., "Miami")
3. Select obfuscation mode (recommended: "DAITA" for residential ISPs)
4. Click **Connect**

**Wait for:** Green "Connected" status + exit IP display.

### Step 1.3 — Check IP Reputation
After connection, the system automatically checks IP reputation.
- **Clean:** Proceed
- **Suspicious:** Try a different server (disconnect, select different city, reconnect)
- **Blacklisted:** Do NOT proceed. Select a different country/city.

### Step 1.4 — Attach Network Shield
Still in Tab 1, click **Attach Shield**:
- System auto-detects WireGuard interface (e.g., `wg0`)
- Applies Windows TCP persona to the VPN tunnel
- Confirm: "eBPF shield attached to wg0"

### Step 1.5 — Configure Proxy (Optional)
If using residential proxy instead of/alongside VPN, go to **Tab 4 (Proxy/DNS)**:
1. Select proxy provider
2. Set country/city matching billing address
3. Click **Connect Proxy**
4. Verify GeoIP match with billing address

### Step 1.6 — Verify Network Stack
In **Tab 2 (Network Shield)**:
- Confirm TTL shows 128 (not 64)
- Confirm TCP window size matches Windows 11
- Confirm CPUID hypervisor bit is masked
- Optionally enable Network Jitter (Cable/DSL/Fiber profile)

**Decision point:** Network ready? All green → proceed to Phase 2.

---

## Phase 2: Target Selection & Intelligence

### Step 2.1 — Open Operations Center
The operator launches the Operations Center app.

### Step 2.2 — Select Target
In **Tab 1 (Target)**:

**Option A — Use Preset:**
1. Open target preset dropdown
2. Select a known target (e.g., "Amazon US")
3. Preset auto-fills PSP, 3DS requirements, and optimal settings

**Option B — Custom Target:**
1. Enter target URL in the URL field
2. Click **Analyze** to run target intelligence
3. Review: PSP identified, antifraud systems, 3DS requirements, golden path score

**Option C — Discover New Targets:**
1. Click **Discover** to find new merchant sites
2. Review discovered targets sorted by success probability
3. Select the highest-scoring target

### Step 2.3 — Review Target Intelligence
For any selected target, review:
- **Golden Path Score:** 80+/100 = good, 60-80 = acceptable, <60 = risky
- **PSP:** Which payment processor (Stripe, Adyen, etc.)
- **3DS:** Required? Can it be bypassed? Which exemptions apply?
- **Antifraud:** Which systems detected (Forter, Riskified, DataDome)?
- **AVS:** What address verification is required?

### Step 2.4 — Deep Recon (Optional)
Switch to **Intelligence Center → Tab 4 (Recon)**:
1. Enter target URL
2. Click **Run Recon**
3. Review V2 Full Intel, AVS Intelligence, Proxy Intelligence, Web Intel
4. Check TLS/JA4 requirements

**Decision point:** Target viable? Score acceptable? → proceed to Phase 3.

---

## Phase 3: Identity Building

### Step 3.1 — Build Persona
In **Operations Center → Tab 2 (Identity)**:

1. Enter persona details:
   - First Name, Last Name
   - Street Address, City, State, ZIP
   - Date of Birth
   - (Optional: gender, occupation, income, interests)

2. Click **Enrich** to auto-fill demographics
3. Review coherence validation results (any inconsistencies flagged)

**Critical:** Billing address must match the VPN exit country/state. Timezone will be auto-set.

### Step 3.2 — Configure Profile
1. Set Profile Age (recommended: 180-450 days)
2. Enable Advanced Profile Generation (900-day non-linear)
3. Enable Purchase History Injection
4. Set target cache size (300-500 MB)

### Step 3.3 — Generate Profile
1. Click **Generate Profile**
2. Watch progress bar through stages:
   - History generation (places.sqlite)
   - Cookie synthesis
   - Cache2 binary mass generation
   - IndexedDB population
   - First-session bias elimination
   - Purchase history injection
3. Review quality score (target: 80%+)
4. If score < 70%, click **Regenerate** with different parameters

**Output:** Complete Firefox profile at the configured path, ready for browser loading.

---

## Phase 4: Card Validation

### Step 4.1 — Validate Card
In **Operations Center → Tab 3 (Validate)**:

1. Enter card details:
   - Card Number (full 16 digits)
   - Expiration (MM/YY)
   - CVV (3-4 digits)

2. Click **Validate**
3. Wait for Cerberus validation result:
   - **LIVE:** Card is active, proceed
   - **DEAD:** Card is not working, use a different card
   - **RESTRICTED:** Card has limitations, review BIN intelligence

### Step 4.2 — Review BIN Intelligence
After validation, review:
- Issuer bank name
- Card country
- Card type (credit/debit)
- Card level (classic/gold/platinum/infinite)
- Quality grade (A-F)

### Step 4.3 — Check 3DS Strategy
Switch to **Intelligence Center → Tab 2 (3DS Strategy)**:
1. Enter card BIN + merchant PSP + amount
2. Review:
   - 3DS bypass probability
   - Applicable exemptions (TRA, low-value, one-leg-out)
   - Issuer-specific risk score
   - Non-VBV status
3. If 3DS bypass probability is low, consider:
   - Lower transaction amount (below €30 for low-value exemption)
   - Different card (non-VBV BIN)
   - Different target (lower 3DS enforcement)

### Step 4.4 — Run Preflight
Back in **Operations Center → Tab 3**:
1. Click **Run Preflight**
2. Review checklist:
   - ✅ Card is live
   - ✅ IP matches billing geography
   - ✅ Proxy not blacklisted at target
   - ✅ TLS fingerprint consistent
   - ✅ Canvas fingerprint unique
   - ✅ Timezone matches billing state
   - ✅ No WebRTC leaks
3. All green → **GO**. Any red → fix the issue first.

**Decision point:** Preflight passed? → proceed to Phase 5.

---

## Phase 5: Browser Launch & Operation

### Step 5.1 — Configure Fingerprint
In **Operations Center → Tab 4 (Forge & Launch)**:

1. Select GPU profile (e.g., "NVIDIA GeForce RTX 3060")
2. Confirm screen resolution (1920x1080 recommended)
3. Verify Windows font installation
4. Check USB peripheral synthesis
5. Enable Ghost Motor behavioral engine
6. Set browser mode to **Headed** (for manual operation)

### Step 5.2 — Launch Browser
1. Click **Launch**
2. System executes in sequence:
   - Loads generated profile into Camoufox
   - Injects all fingerprint shims (canvas, audio, WebGL, fonts, Client Hints)
   - Loads Ghost Motor extension
   - Loads TX Monitor extension
   - Loads AI Co-Pilot extension
   - Sets timezone and location
   - Executes referrer warmup chain (Google → intermediate sites → target)
   - Handover protocol signals: "Ready for manual operation"

3. **Camoufox browser window opens**

### Step 5.3 — Manual Browsing
The operator now browses **manually** in the Camoufox window:

1. Browser is already on the target site (from referrer warmup)
2. Browse the site naturally:
   - Look at products
   - Read reviews
   - Add item to cart
   - Proceed to checkout

**Background (invisible to operator):**
- Ghost Motor humanizes mouse movements and typing
- AI Co-Pilot monitors for checkout page detection
- TX Monitor captures payment events
- Forensic Monitor watches for detection signals
- All fingerprint shims active on every page

### Step 5.4 — Fill Checkout Form
At the checkout page:

1. Form fields auto-fill with persona data (billing address, name, email, phone)
   - Auto-fill uses human-like timing (not instant)
   - Ghost Motor adds natural pauses between fields
2. Enter card details when prompted:
   - Card number, expiration, CVV
   - These are typed with human-like cadence
3. Review order summary

**AI Co-Pilot (background):**
- Detects PSP from page source
- Blocks hidden 3DS fingerprint iframes in <10ms
- Scans API responses for pre-authorization signals
- Alerts operator if something looks wrong (non-blocking notification)

### Step 5.5 — Submit Payment
1. Click **Place Order** / **Pay Now**
2. TX Monitor captures the payment event
3. Wait for response:

**If 3DS Challenge appears:**
- AI Co-Pilot has already attempted bypass strategies
- If challenge persists, operator may need to:
  - Enter OTP from bank SMS (if available)
  - Complete challenge manually

**If KYC Verification triggered:**
- Switch to KYC Studio app
- Tab 1: Start virtual camera with face image
- Complete liveness challenge (blink, head turn)
- Tab 2: Upload document if requested

### Step 5.6 — Capture Result
After payment attempt:
- TX Monitor displays result (success/decline)
- If declined: Decline Decoder shows reason + guidance

---

## Phase 6: Post-Operation

### Step 6.1 — Review Results
In **Operations Center → Tab 5 (Results)**:
1. Check transaction status
2. If declined, review decline code analysis
3. Note which phase failed (if any)

### Step 6.2 — Store Intelligence
In **Intelligence Center → Tab 5 (Memory)**:
- Operation result automatically stored in vector memory
- Add manual notes if needed ("BIN works well with this target")

### Step 6.3 — Analyze Detection (if declined)
In **Intelligence Center → Tab 3 (Detection)**:
1. Enter operation ID
2. Review detection analysis:
   - Which antifraud vector triggered?
   - What should change for next attempt?
3. AI Guard provides post-operation recommendations

### Step 6.4 — Cleanup
1. Close Camoufox browser
2. In **Network Center → Tab 3 (Forensic)**:
   - Click **Clean** to remove session artifacts
3. If done for the day:
   - Disconnect VPN
   - Stop services via Admin Panel

---

## Workflow Summary Diagram

```
STARTUP
  │
  ├── Boot → Auto: HW shield, eBPF, CPUID mask, services
  ├── Launcher → Health check
  └── Admin Panel → Verify config
  │
NETWORK (Network Center)
  │
  ├── Connect VPN → Check IP reputation
  ├── Attach eBPF shield → Verify TTL=128
  └── (Optional) Configure proxy
  │
TARGET (Operations Center Tab 1 + Intelligence Center Tab 4)
  │
  ├── Select/discover target
  ├── Review golden path score
  └── Verify PSP + 3DS + antifraud
  │
IDENTITY (Operations Center Tab 2)
  │
  ├── Build persona → Enrich → Validate coherence
  ├── Configure profile (age, cache, history)
  └── Generate → Quality audit (80%+ target)
  │
VALIDATE (Operations Center Tab 3 + Intelligence Center Tab 2)
  │
  ├── Validate card → BIN intelligence
  ├── 3DS strategy analysis
  └── Run preflight → All green = GO
  │
LAUNCH (Operations Center Tab 4)
  │
  ├── Configure fingerprints
  ├── Launch Camoufox → Shims + Extensions loaded
  ├── Referrer warmup → Handover to human
  └── MANUAL BROWSING → checkout → payment
  │
RESULT (Operations Center Tab 5 + Intelligence Center Tab 3)
  │
  ├── Capture result
  ├── Decode decline (if any)
  ├── Store in vector memory
  └── Cleanup
```

---

## Timing Guide

| Phase | Expected Duration | Notes |
|-------|------------------|-------|
| System startup | 30-60 seconds | Auto services boot in parallel |
| VPN connection | 5-15 seconds | Including IP reputation check |
| Target analysis | 10-30 seconds | Depends on recon depth |
| Profile generation | 15-45 seconds | Depends on profile age and cache size |
| Card validation | 3-10 seconds | Network-dependent |
| Preflight | 5-15 seconds | All checks run in parallel |
| Browser launch | 10-20 seconds | Including referrer warmup |
| Manual browsing | 3-10 minutes | Natural browsing pace |
| Checkout | 1-3 minutes | Form filling + payment |
| **Total per operation** | **5-15 minutes** | Varies by target complexity |

---

*Next: [10 — Real-World Operations](10_REAL_WORLD_OPERATIONS.md)*
