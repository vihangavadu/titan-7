# Operator Threat Model — Every Decline Vector from Profile Forge to Final Checkout

Complete analysis of every possible decline/detection vector an operator faces when using a 90-day, 500MB+ forged profile with good CC + proxy + VPN on targets like Eneba, and exactly which Titan module patches each one.

---

## Scenario: Real-World Operation on Eneba

**Setup:** Operator has forged a 90-day, 500MB+ Firefox profile with Genesis. Has a valid Chase Visa Signature (BIN 453201), residential proxy in TX matching billing, Mullvad VPN connected, eBPF shield active. Target: Eneba (gift cards, ~$50).

**Eneba's Stack:** Stripe (PSP) → Stripe Radar (antifraud) → 3DS 2.0 (SCA) → Issuer (Chase ML)

---

## The 23 Decline Vectors — Checkpoint by Checkpoint

### CHECKPOINT 1: IP/Network Layer (Before Page Load)

| # | Vector | Detection Method | Titan Patch | Status |
|---|--------|-----------------|-------------|--------|
| 1 | **Datacenter IP** | IP reputation DB (MaxMind, IPQualityScore). VPN/datacenter IPs flagged. | `mullvad_vpn.py` → residential exit, `network_shield_loader.py` → IP reputation check on connect | ✅ Patched |
| 2 | **IP-Billing Geo Mismatch** | IP geolocation vs billing state/country. TX billing + NY IP = flag. | `location_spoofer_linux.py` + `timezone_enforcer.py` → geo-sync IP/TZ/locale to billing | ✅ Patched |
| 3 | **TCP Fingerprint** | p0f/JA3 passive OS detection. Linux TCP stack ≠ claimed Windows UA. | `network_shield.c` (eBPF) → rewrites TCP window/TTL/options to match Windows | ✅ Patched |
| 4 | **TLS/JA4 Fingerprint** | JA4+ hash doesn't match claimed browser. Camoufox JA4 ≠ real Chrome JA4. | `tls_parrot.py` + `ja4_permutation_engine.py` → match JA4 to target's expected browser | ✅ Patched |
| 5 | **DNS Leak** | DNS queries go to ISP DNS instead of VPN tunnel. Reveals real location. | `095-os-harden.hook.chroot` → sysctl IPv6 disable, VPN kill switch | ⚠️ Partial — no active DNS leak test in UI |
| 6 | **WebRTC Leak** | WebRTC STUN request bypasses VPN, reveals real IP. | Browser config `media.peerconnection.enabled=false` in prefs.js | ⚠️ Partial — not explicitly set in forge |

### CHECKPOINT 2: Browser Fingerprint (Page Load)

| # | Vector | Detection Method | Titan Patch | Status |
|---|--------|-----------------|-------------|--------|
| 7 | **Canvas Fingerprint** | Canvas API returns unique pixel hash per GPU/driver. | `canvas_noise.py` + `canvas_subpixel_shim.py` → noise injection | ✅ Patched |
| 8 | **WebGL Fingerprint** | WebGL renderer/vendor string reveals real GPU. | `webgl_angle.py` → spoof ANGLE renderer string | ✅ Patched |
| 9 | **AudioContext Fingerprint** | AudioContext oscillator output is hardware-specific. | `audio_hardener.py` → deterministic noise per profile | ✅ Patched |
| 10 | **Font Enumeration** | Available fonts reveal OS. macOS fonts on "Windows" = caught. | `font_sanitizer.py` → OS-appropriate font list | ✅ Patched |
| 11 | **Navigator Inconsistency** | UA says Windows but `navigator.platform` says Linux. | `fingerprint_injector.py` → consistent navigator overrides | ✅ Patched |
| 12 | **Screen Resolution Mismatch** | Unusual resolution (e.g., 800x600 on "4K monitor" claim). | `genesis_core.py` → coherent screen/GPU/memory combination | ✅ Patched |
| 13 | **Empty Storage Timing Attack** | Empty IndexedDB/localStorage responds in <0.1ms. Populated = 1-5ms. | `indexeddb_lsng_synthesis.py` → pre-populated per-origin databases | ✅ Patched |
| 14 | **First-Session Indicators** | Browser "first run" flags, onboarding markers, telemetry pings. | `first_session_bias_eliminator.py` → patches all first-run markers | ✅ Patched |

### CHECKPOINT 3: Behavioral (During Browsing)

| # | Vector | Detection Method | Titan Patch | Status |
|---|--------|-----------------|-------------|--------|
| 15 | **Mouse Movement Pattern** | BioCatch/BehaviorSec: bot-like straight lines, no micro-jitter. | `ghost_motor_v6.py` → human-like bezier curves, jitter, hesitation | ✅ Patched (operator manual) |
| 16 | **Session Duration** | Instant checkout (<30s on site) = bot/fraud signal. | `HANDOVER_PROTOCOL.txt` → scripted 2-3min warmup, 15s page dwell | ✅ Patched (operator follows protocol) |
| 17 | **Navigation Path** | Direct URL to checkout = suspicious. Real users browse first. | Genesis forge `HANDOVER_PROTOCOL.txt` → Google search → organic click → browse → checkout | ✅ Patched |
| 18 | **Typing Speed** | Form fill at 300 WPM = autofill bot. Real typing = 60-90 WPM. | `form_autofill_injector.py` → pre-filled via browser autofill (natural trigger) | ✅ Patched |

### CHECKPOINT 4: Payment/Card (At Checkout)

| # | Vector | Detection Method | Titan Patch | Status |
|---|--------|-----------------|-------------|--------|
| 19 | **Stripe Radar Score** | Stripe's ML fraud score >65 = block. Factors: device ID, IP, velocity. | `__stripe_mid` pre-aged cookie (30+ days), residential IP, low velocity | ✅ Patched |
| 20 | **3DS 2.0 Challenge** | PSD2 SCA: amounts >€30 in EU, or Radar risk >50 trigger 3DS OTP. | `three_ds_strategy.py` → TRA exemption if <€100, bypass plan, timing advice | ✅ Patched |
| 21 | **AVS Mismatch** | ZIP/street doesn't match issuer's records. Returns N/no match. | `cerberus_enhanced.py` AVSEngine → ZIP-state validation, address normalization | ✅ Patched |
| 22 | **Issuer ML Decline (do_not_honor)** | Chase/Citi ML model: amount unusual for cardholder pattern, new merchant. | `issuer_algo_defense.py` → amount envelope, velocity spacing, MCC diversification | ✅ Patched |
| 23 | **Cross-Merchant Velocity** | Same BIN used on 3 merchants in 1 hour = consortium flag. | `cerberus_core.py` CardCoolingSystem → persistent cooling with disk-backed heat tracking | ✅ Patched |

---

## The 6 Gaps (Vectors With Incomplete Patches)

### Gap 1: WebRTC IP Leak
**Vector:** WebRTC STUN bypasses VPN, reveals real IP.
**Current:** No explicit `media.peerconnection.enabled=false` in forged prefs.js.
**Fix:** Add to `genesis_core.py` `_write_firefox_profile()` and fallback forge prefs.js:
```
user_pref("media.peerconnection.enabled", false);
user_pref("media.peerconnection.ice.no_host", true);
```

### Gap 2: DNS Leak Active Test
**Vector:** DNS queries leak to ISP resolver outside VPN tunnel.
**Current:** Sysctl disables IPv6, VPN routes all traffic. But no active test.
**Fix:** Add DNS leak test button in Network app that queries `whoami.akamai.net` and compares response to VPN exit IP.

### Gap 3: Stripe `__stripe_mid` Not Verified Post-Forge
**Vector:** `__stripe_mid` cookie present but age doesn't match profile or value format is wrong.
**Current:** Cookie generated in genesis_core with correct age. No post-forge verification.
**Fix:** Add "Verify Stripe Trust Tokens" button in Profile Forge that reads cookies.sqlite and checks `__stripe_mid` age + format.

### Gap 4: GAMP/GA Triangulation
**Vector:** Google Analytics client-side events don't match server-side analytics. Empty `_ga` cookies = new visitor signal.
**Current:** `_ga` cookies generated with aged timestamps. But no GA event sequence.
**Fix:** Already have `ga_triangulation.py` module — wire it into Profile Forge stage pipeline to inject realistic GA event data into localStorage.

### Gap 5: Eneba-Specific Detection
**Vector:** Eneba uses Sift Science (not just Stripe Radar). Sift checks device fingerprint + purchase history cross-merchant.
**Current:** No Sift-specific countermeasures.
**Fix:** Add Sift Science device ID pre-generation in `purchase_history_engine.py` — inject `__ssid` cookie and `s.siftscience.com` localStorage data.

### Gap 6: Browser Extension Fingerprint
**Vector:** Eneba's antifraud JS checks for browser extensions (ad blockers, privacy tools). Extensions modify DOM.
**Current:** Ghost Motor and TX Monitor extensions present but no stealth.
**Fix:** Ensure extensions use `manifest.json` with minimal permissions and don't inject visible DOM elements.

---

## Decline Code Quick Reference (What Operator Sees)

| Decline Code | Meaning | Operator Action |
|-------------|---------|-----------------|
| `do_not_honor` | Bank ML flagged it | Try: different amount (-10%), different time (±2h), different merchant |
| `card_velocity_exceeded` | Too many attempts | STOP. Wait 4-6 hours. Card is hot. |
| `fraudulent` | Issuer fraud flag | Card is BURNED. Discard immediately. |
| `authentication_required` | 3DS triggered | Complete OTP (wait 12s to simulate phone), or use TRA bypass |
| `incorrect_zip` | AVS mismatch | Fix billing ZIP. Check with OSINT. |
| `incorrect_cvc` | CVV wrong | Card data incomplete. Discard if CVV unknown. |
| `insufficient_funds` | Balance too low | Lower amount or different card. |
| `lost_card` / `stolen_card` | CRITICAL | Discard IMMEDIATELY. Possible LE alert. |
| `merchant_blacklist` | Stripe Radar block | Profile/fingerprint/IP is on blocklist. Rotate EVERYTHING. |
| `generic_decline` | No specific reason | Try: $20 less, wait 1 hour, different warmup path |

---

## Recommended Patches to Implement

| Priority | Gap | Fix | File | Effort |
|----------|-----|-----|------|--------|
| P0 | WebRTC leak | Add `media.peerconnection.enabled=false` to prefs.js | `genesis_core.py`, `app_profile_forge.py` | 10 min |
| P0 | Stripe verify | Add verify button for `__stripe_mid` age | `app_profile_forge.py` | 30 min |
| P1 | DNS leak test | Add DNS leak test button | `titan_network.py` | 30 min |
| P1 | GA triangulation | Wire `ga_triangulation.py` into forge | `app_profile_forge.py` | 1 hour |
| P2 | Sift Science | Add `__ssid` cookie pre-generation | `purchase_history_engine.py` | 1 hour |
| P2 | Extension stealth | Audit extension manifest permissions | `extensions/ghost_motor/manifest.json` | 30 min |

---

## Operator Decision Tree at Checkout

```
CHECKOUT INITIATED
    │
    ├─→ SUCCESS (order confirmed)
    │     └── Post-Op: check email, wait 45s, close browser, cool card 2h
    │
    ├─→ 3DS CHALLENGE
    │     ├── Amount <€100? → TRA exemption may apply, retry without 3DS
    │     ├── OTP received? → Wait 12s, enter code, submit
    │     └── No OTP? → Card not enrolled in 3DS, should auto-pass
    │
    ├─→ DECLINE: do_not_honor
    │     ├── First attempt? → Try: $20 less, wait 30min, different warmup
    │     ├── Second attempt? → Switch card, keep same profile
    │     └── Third attempt? → Switch target, this merchant is blocking you
    │
    ├─→ DECLINE: velocity
    │     └── STOP. Cool card 4-6 hours. Do NOT retry.
    │
    ├─→ DECLINE: fraud/stolen
    │     └── DISCARD card. Kill session. Rotate everything.
    │
    ├─→ DECLINE: AVS/CVV mismatch
    │     ├── Verify billing data via OSINT
    │     └── Try merchant that doesn't enforce AVS (non-US)
    │
    └─→ DECLINE: insufficient_funds
          └── Lower amount by 30% or switch card
```
