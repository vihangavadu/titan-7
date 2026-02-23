# TITAN V8.2.2 — Operational Playbook

**Version:** 8.2.2 | **Author:** Dva.12 | **Updated:** 2026-02-23

---

## Quick Start — Complete Operation Flow

This is the step-by-step guide for running a full operation using Titan OS V8.2.2's 9-app architecture.

---

### Phase 0: System Setup (One-Time)

1. **Open Settings** (indigo card, row 2 center-right)
2. **VPN tab** — Enter Mullvad account number, select relay country/city, connect
3. **AI tab** — Verify Ollama endpoint, pull models if needed (mistral:7b, qwen2.5:7b, deepseek-r1:8b)
4. **SERVICES tab** — Start Redis, Ollama, Xray (green dots = running)
5. **BROWSER tab** — Verify Camoufox path and extensions
6. **API KEYS tab** — Enter proxy provider credentials, OSINT API keys

---

### Phase 1: Intelligence Gathering

1. **Open Intelligence Center** (purple card, row 1 center)
2. **RECON tab** — Enter target URL, run target reconnaissance
3. **3DS STRATEGY tab** — Enter BIN prefix, review 3DS likelihood and strategy
4. **AI COPILOT tab** — Ask for operation plan based on target + card combo
5. **DETECTION tab** — Review antifraud platform profile for the target

---

### Phase 2: Card Validation

1. **Open Card Validator** (yellow card, row 3 center)
2. **VALIDATE tab** — Enter full card details, run Luhn + BIN + Cerberus check
3. **INTELLIGENCE tab** — Review card grade (aim for S or A)
4. Review 3DS strategy preview — confirm approach
5. If card fails, try another; check **HISTORY tab** for patterns

---

### Phase 3: Profile Forging

1. **Open Profile Forge** (cyan card, row 3 left)
2. **IDENTITY tab** — Fill in persona: name, email, phone, address, card details
3. Select target site and profile age (90+ days recommended)
4. **FORGE tab** — Click **Start Forge**, watch 9-stage pipeline:
   - Genesis → Purchase History → IndexedDB → First-Session Bias → Chrome Commerce → Forensic Cache → Font → Audio → Realism Score
5. Review quality score — aim for **75+**
6. **PROFILES tab** — Verify profile appears in list

---

### Phase 4: Network Preparation

1. **Open Network Center** (green card, row 1 right)
2. **MULLVAD VPN tab** — Confirm VPN connected to correct geo
3. **NETWORK SHIELD tab** — Enable eBPF TCP mimesis if needed
4. **TLS tab** — Verify JA3/JA4 fingerprint matches Chrome
5. **PROXY/DNS tab** — Configure proxy if using residential IP instead of VPN

---

### Phase 5: Browser Launch

1. **Open Browser Launch** (green card, row 3 right)
2. **LAUNCH tab** — Select forged profile from dropdown
3. Review preflight checklist — all items must be green:
   - Profile exists, VPN active, IP clean, DNS secure, TZ match, fingerprint ready, Ghost Motor loaded, TX Monitor loaded
4. Click **Launch** — Camoufox opens with profile loaded
5. **MONITOR tab** — Watch live TX events as you browse

---

### Phase 6: Operation Execution

1. Browse target site naturally (follow timing guide below)
2. Add items to cart, proceed to checkout
3. Fill shipping info using form autofill
4. When **handover signal** appears — take manual control
5. Type card details with human-like timing (pauses, corrections)
6. Submit payment
7. Monitor for success/decline in **MONITOR tab**

---

### Phase 7: Post-Operation

1. **HANDOVER tab** — Review post-op analysis
2. If declined — check decline decoder for code meaning and next steps
3. **Open Intelligence Center** → **DETECTION tab** — Analyze what triggered decline
4. **Open Admin** → **LOGS tab** — Review operation log
5. Clean up: close browser, disconnect VPN if done

---

## Timing Guide

| Page/Action | Minimum | Optimal | Maximum |
|-------------|---------|---------|---------|
| Product View | 30s | 45-90s | 180s |
| Add to Cart | 5s | 8-15s | 30s |
| View Cart | 10s | 20-40s | 60s |
| Checkout Start | 15s | 30-60s | 120s |
| Payment Entry | 20s | 45-90s | 180s |
| Review Order | 10s | 20-45s | 90s |

---

## 9-App Quick Reference

| App | Accent | When to Use |
|-----|--------|-------------|
| **Operations** | Cyan | Full workflow in one window (power users) |
| **Intelligence** | Purple | Before ops: recon, 3DS strategy, AI guidance |
| **Network** | Green | VPN/proxy setup, network shield |
| **KYC Studio** | Orange | Identity verification bypass |
| **Admin** | Amber | System health, logs, automation |
| **Settings** | Indigo | First-time setup, external tool config |
| **Profile Forge** | Cyan | Focused profile building |
| **Card Validator** | Yellow | Focused card checking |
| **Browser Launch** | Green | Focused launch + TX monitoring |

---

## Detailed Playbook Chapters

For in-depth documentation of each app, module, and technique, see the full playbook:

→ [**operational-playbook/00_INDEX.md**](operational-playbook/00_INDEX.md) — 18 chapters covering every aspect of Titan OS

---

*V8.2.2 — 9 apps, 110 modules, 10 external tools, 6 AI models, 36 tabs.*
