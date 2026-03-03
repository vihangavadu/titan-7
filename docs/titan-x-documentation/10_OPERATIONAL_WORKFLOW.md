# 10 — Operational Workflow

**Human-in-the-Loop — 7-Phase Execution — Handover Protocol — Post-Operation Analysis**

Titan X is not a bot. It is an augmentation system that prepares everything for a human operator to execute manually. The automated system achieves 95% of the preparation; the human operator delivers the final 5% that makes the difference between success and detection. This document covers the complete end-to-end workflow from VPS login to post-operation analysis.

---

## The Human-in-the-Loop Principle

Why human execution is non-negotiable:

| Factor | Automation | Human Operator |
|--------|-----------|----------------|
| `navigator.webdriver` | `true` (detectable) | `undefined` (clean) |
| Cognitive patterns | Deterministic | Non-deterministic |
| Decision making | Scripted | Adaptive |
| Navigation | Direct URL | Search → Browse → Buy |
| Error handling | Crashes on unexpected UI | Adapts naturally |
| CAPTCHA response | AI-solved (fast) | Human-timed (realistic) |
| Session rhythm | Constant pace | Variable (warm-up → peak → fatigue) |

The automated system handles profile forging, card validation, shield activation, and environment preparation. The human handles the actual browsing and checkout — the part antifraud systems scrutinize most heavily.

---

## Phase 1: Pre-Operation Setup (One-Time)

### 1.1 VPS Access

```
RDP: 72.62.72.48:3389
User: root
Desktop: XFCE (dark theme, compositing disabled)
```

Or via SSH:
```bash
ssh root@72.62.72.48
```

### 1.2 System Verification

Launch **Settings** app → Services tab → verify all services running:

| Service | Status | Port |
|---------|--------|------|
| Ollama | ● Active | 11434 |
| Redis | ● Active | 6379 |
| Xray | ● Active | — |
| Mullvad daemon | ● Active | — |
| titan-backend | ● Active | 8000 |
| titan-api | ● Active | 8443 |
| hardware_shield_v6 | ● Loaded | — |

### 1.3 API Key Configuration

**Settings** app → API Keys tab:

| Key | Required | Purpose |
|-----|----------|---------|
| Residential proxy credentials | **Yes** | IP reputation is #1 factor |
| Stripe secret key(s) | **Yes** | Card validation via SetupIntent |
| Mullvad account | Recommended | VPN with DAITA protection |
| Cloud LLM API key | Optional | Improved CAPTCHA solving |
| ntfy topic | Optional | Push notifications |

### 1.4 Preflight Validation

**Operations Center** → VALIDATE tab → Run All Checks:

| Check | What It Verifies | Module |
|-------|-----------------|--------|
| Kernel module | hardware_shield_v6.ko loaded | `hardware_shield_v6.c` |
| TTL | ip_default_ttl = 128 | `99-titan.conf` |
| Timezone | Matches target region | `timezone_enforcer.py` |
| DNS | No ISP DNS leak | `/etc/resolv.conf` |
| Fonts | 0 Linux fonts visible | `font_sanitizer.py` |
| Audio | Windows audio parameters | `audio_hardener.py` |
| Proxy | Connected and healthy | `proxy_manager.py` |
| Camoufox | Installed and executable | Integration bridge |
| VPN | Connected (Mullvad or Xray) | `mullvad_vpn.py` |

**All checks must pass before proceeding.** Any failure blocks the operation.

---

## Phase 2: Profile Forging (Genesis)

### 2.1 Select Target

**Profile Forge** app → IDENTITY tab or **Operations Center** → TARGET tab:

Choose from pre-configured target presets:

| Target | Difficulty | 3DS Likelihood | Browser |
|--------|-----------|---------------|---------|
| Amazon US | Medium | 40-60% | Firefox |
| Steam | Easy | 20-30% | Firefox |
| Nike US | Medium | 30-50% | Chromium |
| Eneba | Easy | 15-25% | Firefox |
| Best Buy | Hard | 50-70% | Chromium |
| Apple Store | Extreme | 80-95% | Chromium |

### 2.2 Enter Persona Details

**Operations Center** → IDENTITY tab:

```
Full Name:     John Michael Davis
Email:         jmdavis1987@gmail.com
Street:        4521 Oak Ridge Drive
City:          Austin
State:         TX
ZIP:           78745
Phone:         (512) 555-0147
Date of Birth: 1987-03-14
```

**Consistency rules** (AI-validated):
- Area code (512) matches Austin, TX
- ZIP (78745) matches city/state
- Age (39) matches Professional archetype
- Email format matches era (born 1987)

### 2.3 Configure Profile Parameters

**Profile Forge** → FORGE tab:

| Parameter | Recommended | Range |
|-----------|------------|-------|
| Profile age | 120 days | 30-900 days |
| Persona archetype | Professional | Student/Professional/Gamer/Parent/Elderly |
| Hardware profile | Dell XPS 8960 | 4 profiles available |
| Browser type | Firefox | Firefox or Chromium |
| History density | 1.0x | 0.5x-2.0x multiplier |

### 2.4 Execute Forge

Click **"Forge Profile"** → 9-stage pipeline executes (~90-180 seconds):

```
Stage 1: Identity generation          ✅ 2s
Stage 2: Persona enrichment (AI)      ✅ 4s
Stage 3: Browsing history (5,000+)    ✅ 25s
Stage 4: Cache generation (350MB+)    ✅ 40s
Stage 5: Cookie synthesis (800+)      ✅ 15s
Stage 6: Storage synthesis (IDB+LS)   ✅ 20s
Stage 7: Autofill injection           ✅ 3s
Stage 8: Purchase history             ✅ 10s
Stage 9: Quality scoring              ✅ 2s

Profile Quality: 94/100 (Excellent)
Profile Size: 687MB
Profile ID: titan_30de2ac0af15
```

### 2.5 Quality Gate

| Score | Grade | Action |
|-------|-------|--------|
| 90-100 | Excellent | Proceed immediately |
| 70-89 | Good | Proceed with minor warnings reviewed |
| 50-69 | Fair | Review flagged dimensions before proceeding |
| Below 50 | Poor | **Auto-rejected** — regenerate |

---

## Phase 3: Card Validation (Cerberus)

### 3.1 Enter Card Data

**Card Validator** → VALIDATE tab:

```
Card Number: 4147 2012 3456 7890
Exp Month:   12
Exp Year:    26
CVV:         789
Holder:      John M Davis
```

### 3.2 Validation Pipeline

```
Step 1: Luhn check              ✅ VALID
Step 2: Network detection       Visa
Step 3: BIN lookup              Chase, Credit, Signature, US
Step 4: SetupIntent probe       ✅ LIVE
Step 5: BIN scoring             Grade A (87/100)
```

### 3.3 Intelligence Output

**Card Validator** → INTELLIGENCE tab:

| Data Point | Value | Impact |
|-----------|-------|--------|
| Card type | Credit | +20 score |
| Card level | Signature | +15 score |
| Issuing bank | Chase | Tier-1, tolerant |
| Country | US | Domestic match |
| AVS support | Full | Street + ZIP |
| 3DS likelihood | Medium (45%) | Profile aging helps |
| Max safe amount | $299.99 | Based on issuer + level |
| Recommended cooldown | 2 hours | Between operations |

### 3.4 Strategy Selection

Based on card grade + target difficulty:

| Combination | Strategy | Warmup Time |
|------------|---------|-------------|
| Grade A + Easy target | Direct checkout | 2-3 minutes |
| Grade A + Medium target | Brief warmup → checkout | 3-5 minutes |
| Grade B + Medium target | Extended warmup → checkout | 5-8 minutes |
| Grade B + Hard target | Small purchase first → target | 10-15 minutes |
| Grade C/D + Any | Consider different card | — |

---

## Phase 4: Shield Activation

### 4.1 Automatic Shield Activation

When the operator clicks **"Launch Browser"**, all shields activate automatically:

| Shield | Activation | Module |
|--------|-----------|--------|
| Hardware identity | Netlink profile → kernel module | `hardware_shield_v6.c` |
| Network stack | sysctl + eBPF applied | `network_shield_v6.c` |
| VPN tunnel | Mullvad WireGuard connected | `mullvad_vpn.py` |
| Proxy | Residential proxy geo-matched | `proxy_manager.py` |
| Network jitter | tc-netem rules applied | `network_jitter.py` |
| Browser fingerprint | Canvas/WebGL/Audio configured | `fingerprint_injector.py` |
| Font sanitization | Linux fonts blocked | `font_sanitizer.py` |
| Timezone sync | Matches billing address | `timezone_enforcer.py` |
| Locale | en_US.UTF-8 | `location_spoofer_linux.py` |
| Ghost Motor | Extension loaded | `ghost_motor_v6.py` |
| TX Monitor | Extension loaded | TX Monitor extension |
| Kill switch | Armed and monitoring | `kill_switch.py` |

### 4.2 Deep Identity Verification

40+ cross-signal consistency checks run automatically:

```
Timezone (America/Chicago) matches proxy (Austin, TX)     ✅
Locale (en_US) matches country (US)                       ✅
GPU (Intel UHD 630) matches CPU (i7-13700K)               ✅
Font set (287 fonts) matches OS (Windows 10)              ✅
Audio profile (44100Hz WASAPI) matches OS (Windows)       ✅
Battery status (none) matches hardware (desktop)          ✅
Screen (1920x1080) matches hardware profile               ✅
Client hints match user-agent                             ✅

Deep Identity Score: 98/100 — READY
```

---

## Phase 5: The Handover Protocol

### 5.1 GENESIS Phase (Complete)

All automated preparation is done:
- ✅ Profile forged (687MB, quality 94)
- ✅ Card validated (Grade A, LIVE)
- ✅ Proxy geo-matched (Austin, TX residential)
- ✅ All shields active
- ✅ Kill switch armed

### 5.2 FREEZE Phase

```
[HANDOVER] Terminating all automation...
[HANDOVER] Closing headless browser instances...
[HANDOVER] Flushing automation artifacts...
[HANDOVER] Profile ready for manual operation
[HANDOVER] *** FREEZE COMPLETE — AWAITING OPERATOR ***
```

All automation stops. No scripts running. No headless browsers. Clean state.

### 5.3 HANDOVER Phase — Manual Browser Launch

Camoufox launches with the forged profile:

```bash
/opt/titan/bin/titan-browser --profile /opt/titan/profiles/titan_30de2ac0af15
```

Browser opens with:
- All 800+ cookies pre-loaded (returning visitor)
- Hardware fingerprint reporting Dell XPS desktop
- Residential proxy in Austin, TX
- Ghost Motor extension active
- TX Monitor extension active

### 5.4 Operator Browsing Workflow

The operator follows a natural browsing pattern:

```
Step 1: Google Search                              ~10 seconds
  → Type "amazon electronics deals" in Google
  → Click organic Amazon result
  → Establishes referrer chain (google.com → amazon.com)

Step 2: Browse Target Site                          ~20 seconds
  → Land on Amazon homepage
  → Scroll through deals naturally
  → Ghost Motor humanizes all interactions

Step 3: Product Search                              ~45 seconds
  → Use site search bar
  → Type product name naturally
  → Browse 2-3 results
  → Read reviews on one product

Step 4: Product Selection                           ~40 seconds
  → Select size/color/options
  → Read product details
  → Scroll through reviews
  → Add to cart

Step 5: Cart Review                                 ~15 seconds
  → Review cart
  → Maybe continue shopping briefly
  → Proceed to checkout

Step 6: Checkout                                    ~90 seconds
  → Shipping address (pre-filled or typed naturally)
  → Payment method (type card details with Ghost Motor)
  → Review order total
  → Place order

Total natural session: 3-5 minutes
```

### Why This Defeats Antifraud

The antifraud system sees:

| Signal | What It Sees | Result |
|--------|-------------|--------|
| Visitor type | Returning customer (purchase history) | ✅ Trusted |
| Profile age | 120-day browser profile, 687MB | ✅ Established |
| Referrer chain | Google → Amazon (organic) | ✅ Natural |
| Behavioral patterns | Human mouse/keyboard/scroll | ✅ Human |
| Device fingerprint | Consistent with previous visits | ✅ Known device |
| Geography | IP + timezone + billing all match | ✅ Consistent |
| Session duration | 3-5 minutes of browsing | ✅ Natural |
| Platform | Windows 10 desktop | ✅ Consumer device |
| IP type | Residential ISP | ✅ Home connection |

---

## Phase 6: Real-Time Monitoring

### 6.1 TX Monitor Dashboard

During the operation, the **Intelligence Center** → DETECTION tab shows real-time data:

```
Fraud Score:    92 ████████████████████░░░░ GREEN
Threat Level:   GREEN — No detection signals
Session Time:   2m 34s
Page:           amazon.com/checkout
Antifraud SDKs: Sift (detected), Internal (detected)
```

### 6.2 Copilot Guidance

The AI copilot provides real-time advice:

```
[14:32:15] ℹ️ Sift SDK detected on checkout page. Score: 92. Proceed normally.
[14:32:45] ℹ️ Form fill rate looks natural. Ghost Motor active.
[14:33:10] ⚠️ Fraud score dipped to 88. YELLOW zone. Slow down slightly.
[14:33:30] ℹ️ Score recovered to 91. GREEN. Proceed with payment.
[14:34:00] ✅ Order submitted. Monitoring for confirmation...
[14:34:15] ✅ Order confirmed. Operation successful.
```

### 6.3 Kill Switch Status

```
[KILLSWITCH] *** ARMED ***
[KILLSWITCH] Monitoring fraud score every 500ms
[KILLSWITCH] Threshold: score < 75 → AUTO PANIC
[KILLSWITCH] Hotkey: Ctrl+Shift+K → MANUAL PANIC
```

### 6.4 Threat Level Escalation

| Level | Score | Operator Action |
|-------|-------|----------------|
| GREEN | 90-100 | Continue normally |
| YELLOW | 85-89 | Slow down, add pauses |
| ORANGE | 75-84 | Finish quickly or abort |
| RED | <75 | **AUTO PANIC** — system takes over |

---

## Phase 7: Post-Operation

### 7.1 Success Path

```
✅ Order confirmed
  → Screenshot captured for records
  → Disarm kill switch
  → Log success metrics (target, BIN, amount, time)
  → Profile saved for future use on same merchant
  → Card enters cooldown (2-6 hours)
  → Optional: forensic clean
```

**Profile Reuse**: For future purchases on the same merchant, the same profile can be reused — it now has an additional real purchase in its history, making it even more trusted.

### 7.2 Decline Path

```
❌ Card declined
  → TX Monitor captures decline code
  → Cerberus analyzes decline reason
  → AI runs decline_diagnosis task
  
Possible actions:
  → "insufficient_funds" → Lower amount or different card
  → "card_declined" → Check BIN grade, try different target
  → "fraud_detected" → 48hr cooldown, review profile quality
  → "do_not_honor" → Try different PSP/target
  → "lost_card" / "stolen_card" → Discard card immediately
```

### 7.3 3DS Challenge Path

```
⚠️ 3DS challenge detected
  → TX Monitor identifies challenge type
  → AI recommends response strategy
  
  OTP (SMS/Email): Enter code if available
  App Push: Requires cardholder's phone
  Biometric: Cannot bypass — abort
  
  No access to OTP → Abort → Try different card
```

### 7.4 Panic Recovery

```
🔴 Kill switch activated
  → Network severed (<50ms)
  → Browser killed (<30ms)
  → Hardware ID flushed (<100ms)
  → Session data cleared (<80ms)
  → Proxy rotated (<150ms)
  → Total: ~470ms
  
Recovery:
  → Wait 5 minutes
  → Re-run preflight checks
  → Forge fresh profile (different persona)
  → Use different card
  → Resume operations
```

### 7.5 Metrics Logging

Every operation is logged for data-driven optimization:

| Metric | Storage | Used By |
|--------|---------|---------|
| Target + outcome | SQLite | Success rate per target |
| BIN + outcome | SQLite | BIN quality tracking |
| Profile quality + outcome | SQLite | Quality/success correlation |
| Time-to-checkout | SQLite | Efficiency tracking |
| Decline codes | SQLite | Pattern analysis |
| 3DS challenge rate | SQLite | PSP strategy tuning |
| AI guidance accuracy | SQLite | Model improvement |

---

## Daily Operation Cadence

### Recommended Daily Workflow

```
09:00  System check, run preflight
09:15  AI daily_planning task → plan targets and order
09:30  Forge 2-3 profiles for today's targets
10:00  Validate cards, select best Grade A/B cards
10:30  Operation 1 (easiest target first)
11:00  Cool down (30 min minimum between ops)
11:30  Operation 2
12:00  Lunch break (natural gap)
13:30  Operation 3
14:00  Cool down
14:30  Operation 4 (if cards available)
15:00  Post-operation analysis
15:30  Review metrics, adjust strategy for tomorrow
16:00  Forensic clean, rotate proxies
```

### Key Timing Rules

| Rule | Reason |
|------|--------|
| No operations 1-5 AM local time | Nighttime purchases flagged more |
| 30+ minute gap between operations | Velocity detection prevention |
| 2-6 hour cooldown per card | Card-level velocity limits |
| 48 hour cooldown after decline | Allow fraud score reset |
| Different persona per operation | Prevent identity linking |
| Rotate proxy between operations | Prevent IP linking |

---

## Emergency Procedures

### Manual Panic

**Hotkey**: `Ctrl+Shift+K` — triggers full panic sequence immediately.

### SSH Remote Kill

```bash
ssh root@72.62.72.48 "touch /opt/titan/state/kill_signal"
```

The kill switch daemon detects the signal file within 500ms.

### Full System Reset

```bash
ssh root@72.62.72.48 "systemctl restart titan-backend titan-api"
```

### Network Emergency

If proxy fails mid-operation:
1. Kill switch auto-triggers (IP change detected)
2. Or manual: disconnect VPN → reconnect with new exit node
3. Forge new profile (old profile is compromised)

---

*Document 10 of 11 — Titan X Documentation Suite — V10.0 — March 2026*
