# TITAN V6.1 SOVEREIGN - User Experience Guide

## First Boot & Complete OS Walkthrough

**Version:** 6.1.0 | **Authority:** Dva.12

---

## First Boot Experience

### Boot Sequence

On first boot, you'll see the TITAN splash screen with module initialization:

```
TITAN V6.1 SOVEREIGN - Loading...
✓ Hardware Shield Active
✓ Network Sovereignty Enabled  
✓ Ghost Motor Initialized
✓ Fingerprint Engine Ready
```

### Desktop Layout

After boot, the XFCE desktop displays:

| Location | Content |
|----------|---------|
| **Top Taskbar** | Genesis, Cerberus, KYC, Test, Browser quick-launch |
| **Desktop Icons** | 4 main modules + Browser + Terminal + Files + Settings |
| **Bottom Status** | CPU, RAM, Proxy status, Shield status |

---

## Home Dashboard (4 Main Modules)

Press `Super` key or click TITAN menu to open:

```
┌─────────────────────────────────────────────────────┐
│              TITAN V6.1 HOME DASHBOARD              │
├─────────────────────────────────────────────────────┤
│  Profiles: 12  │  Cards: 47  │  Success Rate: 94%  │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │ GENESIS  │  │ CERBERUS │  │   KYC    │          │
│  │ Profile  │  │  Card    │  │ Identity │          │
│  │ Forging  │  │ Validate │  │  Verify  │          │
│  └──────────┘  └──────────┘  └──────────┘          │
│                                                     │
│  ┌──────────┐  ┌──────────┐                        │
│  │   TEST   │  │  TITAN   │                        │
│  │ENVIRONMT │  │ BROWSER  │                        │
│  └──────────┘  └──────────┘                        │
│                                                     │
│  RECENT: Profile forged, Card validated, Test pass │
└─────────────────────────────────────────────────────┘
```

---

## 1. Genesis Module (`Ctrl+Alt+G`)

**Purpose:** Forge aged browser profiles with complete fingerprints

### Interface

- **Target Site:** Amazon, BestBuy, Walmart, etc.
- **Persona Name:** Identity for this profile
- **Profile Age:** 60-120 days recommended
- **Browser:** Firefox (recommended) or Chromium
- **Billing Address:** For geo-alignment
- **Integrations:** Bridge, Proxy, Fingerprint

### Workflow

1. Select target site
2. Enter persona details
3. Set age (90 days recommended)
4. Enable integrations
5. Click **FORGE PROFILE**
6. Wait for completion (~15 seconds)
7. Profile appears in list

### Profile List

Shows all profiles with: ID, Target, Age, Status, Actions (Launch/Edit/Delete)

---

## 2. Cerberus Module (`Ctrl+Alt+C`)

**Purpose:** Validate cards and assess risk before operations

### Interface

- **Card Input:** Number, Expiry, CVV, Holder
- **Validation Mode:** Zero-Touch / Micro-Auth / BIN Only
- **Results:** Status, Risk Score, BIN Info, Recommendations

### Validation Modes

| Mode | Description |
|------|-------------|
| Zero-Touch | No charge, pre-screening |
| Micro-Auth | $0.01 auth test |
| BIN Check | Info only |

### Risk Scores

| Score | Level | Action |
|-------|-------|--------|
| 0-30 | LOW | ✅ Good to use |
| 31-50 | MEDIUM | ⚠️ Caution |
| 51+ | HIGH | ❌ Avoid |

---

## 3. KYC Module (`Ctrl+Alt+K`)

**Purpose:** Generate consistent personas and validate addresses

### Features

- **Persona Generator:** Name, DOB, Address, Phone, Email
- **Address Validator:** Verify real addresses
- **Phone Validator:** Check number validity

### Workflow

1. Select country/state
2. Set age range and gender
3. Click **GENERATE PERSONA**
4. Copy or save to profile

---

## 4. Test Environment (`Ctrl+Alt+T`)

**Purpose:** Validate config against PSP and detection systems

### Quick Tests

- **Run Full Suite:** All 24 default tests
- **Test Profile:** Validate specific profile
- **Test Card:** Quick card check
- **Test Network:** Proxy/IP validation

### Results Display

```
SUMMARY: 22/24 passed (92%)
Projected Rate: 95% after fixes

COMPONENT HEALTH:
✓ Fingerprint: 100%
✓ Behavioral: 95%
⚠ Network: 80%
✓ PSP: 90%

FAILED TESTS:
❌ network_geo_mismatch
   Fix: Use proxy matching billing country
```

### Report Formats

- JSON (programmatic)
- Markdown (readable)
- HTML (visual dashboard)

---

## 5. TITAN Browser (`Ctrl+Alt+B`)

**Purpose:** Hardened browser with all shields active

### Launch Options

1. **From Genesis:** Click "Launch" on profile
2. **From Dashboard:** Click TITAN Browser
3. **Terminal:** `titan-browser -p PROFILE_ID URL`

### Active Shields

- Hardware fingerprint masking
- Network sovereignty (TCP/IP)
- Ghost Motor (mouse/keyboard)
- Fingerprint injection
- Proxy routing

### Browser Interface

Standard Firefox with status indicator showing active shields.

---

## Terminal & CLI Tools

### Available Commands

| Command | Purpose |
|---------|---------|
| `titan-genesis` | Profile forging CLI |
| `titan-cerberus` | Card validation CLI |
| `titan-browser` | Browser launcher |
| `titan-test` | Test environment CLI |
| `titan-bridge` | Integration bridge |

### Example Session

```bash
# Forge profile
titan-genesis --target amazon_us --persona "John Smith" --age 90

# Validate card
titan-cerberus --card 4111111111111111 --exp 12/25 --cvv 123

# Test profile
titan-test profile /opt/titan/profiles/titan_abc123/profile.json

# Launch browser
titan-browser -p titan_abc123 https://amazon.com
```

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Super` | Open Dashboard |
| `Ctrl+Alt+G` | Genesis Module |
| `Ctrl+Alt+C` | Cerberus Module |
| `Ctrl+Alt+K` | KYC Module |
| `Ctrl+Alt+T` | Test Environment |
| `Ctrl+Alt+B` | TITAN Browser |
| `Ctrl+Alt+Term` | Terminal |

---

## Daily Workflow

### Recommended Operation Flow

1. **Start:** Open Test Environment, run quick validation
2. **Prepare:** Forge or select profile in Genesis
3. **Validate:** Check card in Cerberus
4. **Test:** Run profile through Test Environment
5. **Operate:** Launch TITAN Browser with profile
6. **Complete:** Follow timing guidelines (45-90s per page)

### Pre-Operation Checklist

- [ ] Proxy connected and matching billing country
- [ ] Profile age > 60 days
- [ ] Card validated (LOW risk)
- [ ] Test suite passing > 90%
- [ ] Shields all active

---

## System Tray Indicators

| Icon | Meaning |
|------|---------|
| 🟢 | All systems operational |
| 🟡 | Warning - check status |
| 🔴 | Critical - fix before operation |
| 🔒 | Shields active |
| 🌐 | Proxy connected |

---

*TITAN V6.1 SOVEREIGN - User Experience Guide*
*Authority: Dva.12 | Version: 6.1.0*
