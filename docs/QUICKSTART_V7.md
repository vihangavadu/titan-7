# TITAN V7.0 SINGULARITY - Quick Start Guide

## Get Started in 5 Minutes

**Version:** 7.0.2 | **Codename:** SINGULARITY | **Authority:** Dva.12

---

## CRITICAL: Human-in-the-Loop Architecture

**TITAN is NOT an automated checkout bot.** It is an operator-assisted preparation system that hands control to a real human for all checkout execution.

### What TITAN Automates (Pre-Checkout Preparation Only)

| Component | What It Does | Touches Live Browser? |
|-----------|-------------|----------------------|
| **Genesis Engine** | Forges aged browser profile (history, cookies, localStorage) | NO — writes files to disk |
| **Fingerprint Injector** | Seeds deterministic Canvas/WebGL/Audio fingerprints | NO — writes profile configs |
| **Form Autofill Injector** | Pre-populates Firefox's `formhistory.sqlite` with persona data | NO — writes to profile DB |
| **Purchase History Engine** | Generates historical purchase records and commerce tokens | NO — writes to profile DB |
| **Hardware Shield / eBPF** | Spoofs TCP/IP stack, TTL, window size at kernel level | NO — kernel-level, transparent |
| **TLS Parrot** | Matches browser TLS fingerprint to real Chrome/Firefox | NO — kernel-level intercept |
| **Network Jitter** | Simulates residential latency patterns via tc-netem | NO — network-level, transparent |
| **Ghost Motor DMTG** | Generates human-like mouse trajectory **coordinates** (math library) | NO — returns (x,y) arrays only |
| **Referrer Warmup** | Navigates Google → organic search result → target site | YES — pre-checkout navigation only |
| **Pre-flight Validator** | Checks IP, TLS, DNS, timezone, fingerprint consistency | NO — read-only diagnostics |

### What the Human Operator Does (Manual Checkout)

| Step | Human Action | Why It Can't Be Automated |
|------|-------------|--------------------------|
| **Product browsing** | Navigate, search, view products organically | Cognitive Non-Determinism defeats behavioral biometrics |
| **Cart management** | Add to cart, review, modify quantities | Natural decision-making patterns |
| **Form filling** | Type billing/shipping details (autofill assists) | Typing rhythm is biometrically unique |
| **Payment entry** | Enter or select saved card | BioCatch monitors hesitation patterns on familiar data |
| **3DS challenges** | Handle SMS/app verification | Requires real-time human judgment |
| **CAPTCHA** | Solve any challenges | Requires human cognition |
| **Post-checkout** | Download keys, track shipping, handle issues | Requires situational awareness |

### The Handover Protocol (3 Phases)

```
Phase 1: GENESIS (Automated)
  └─ Forge profile, inject history, cookies, fingerprints
  └─ Run pre-flight validation checks
  └─ Establish referrer chain via warmup navigation

Phase 2: FREEZE (Transition)
  └─ Kill ALL automation processes (geckodriver, playwright, selenium)
  └─ Kill automated browser instances (marionette flag = bot detection)
  └─ Verify navigator.webdriver flag is CLEARED
  └─ Verify HandoverChecklist: 7/7 checks must PASS

Phase 3: HANDOVER (Manual — Human Takes Control)
  └─ Launch CLEAN browser with forged profile
  └─ Console prints: "BROWSER ACTIVE - MANUAL CONTROL ENABLED"
  └─ Human operator navigates, browses, checks out MANUALLY
  └─ System provides intelligence (target playbook, post-checkout guide)
  └─ Human handles all payment, 3DS, CAPTCHA, and decisions
```

> **Key code evidence:**
> - `handover_protocol.py` line 14: *"The 'Final 5%' of success probability requires Human-in-the-Loop execution."*
> - `integration_bridge.py` line 668: `"BROWSER ACTIVE - MANUAL CONTROL ENABLED"` then `input()` — waits for human
> - `titan-browser` line 523: `"BROWSER ACTIVE - MANUAL CONTROL ENABLED"` then `input()` — waits for human
> - `app_unified.py` line 1579: `"HANDOVER TO OPERATOR"` — GUI explicitly hands off
> - `app_genesis.py` line 114: subtitle = `"Profile Generation for Human Operations"`
> - **ZERO** instances of `page.click()` on any checkout button, payment form, or submit element exist in the entire codebase

---

## Prerequisites

- TITAN V7.0 ISO booted (USB/VM) — `titan-first-boot` runs automatically on first boot
- Camoufox installed (auto-installed by first boot, or `pip install camoufox[geoip]`)
- Operator config set: edit `/opt/titan/config/titan.env` (proxy, VPN, API keys)
- Residential proxy or Lucid VPN configured (recommended)
- Persona config prepared: `/opt/titan/state/active_profile.json` (see below)

> **Recommended:** Use the **Unified GUI** (`python3 /opt/titan/apps/app_unified.py`) for all operations. The steps below show both GUI and CLI/Python approaches.

---

## Step 0: Configure Your Persona (NEW in V7)

V7 requires a persona configuration file. All downstream generators (cookies, localStorage, history, timezone, locale) derive from this config automatically.

### Create `/opt/titan/state/active_profile.json`

```json
{
  "first_name": "John",
  "last_name": "Smith",
  "email": "j.smith.dev@gmail.com",
  "phone": "+12125550147",
  "billing": {
    "street": "350 Fifth Avenue",
    "city": "New York",
    "state": "NY",
    "zip": "10001",
    "country": "US"
  },
  "card_last4": "4829",
  "age_days": 95,
  "storage_mb": 500,
  "screen_w": 1920,
  "screen_h": 1080
}
```

**What V7 derives automatically from this config:**
- **Timezone:** `America/New_York` (from state `NY`)
- **Locale:** `en-US`
- **Search region:** `US` (from billing country)
- **Commerce cookies:** US store settings
- **Screen dimensions:** Consistent across Facebook `wd` cookie, `xulstore.json`, `sessionstore.js`

Alternatively, set environment variables: `TITAN_FIRST_NAME`, `TITAN_BILLING_CITY`, `TITAN_TIMEZONE`, etc.

---

## Step 1: Forge a Profile (2 minutes)

### Option A: Command Line

```bash
# Forge a 95-day aged profile for Amazon US
titan-genesis --target amazon_us --persona "John Smith" --age 95

# Output: Profile created: titan_abc123
```

### Option B: Python

```python
from titan.core import GenesisEngine, ProfileConfig

genesis = GenesisEngine()
profile = genesis.forge_profile(ProfileConfig(
    target="amazon_us",
    persona_name="John Smith",
    age_days=95
))

print(f"Profile: {profile.profile_id}")
print(f"Path: {profile.profile_path}")
```

### Option C: GUI

```bash
# Launch Genesis GUI
python3 /opt/titan/apps/app_genesis.py
```

---

## Step 2: Validate Your Card (1 minute)

### Command Line

```bash
# Validate a card
titan-cerberus --card "4111111111111111|12|25|123"

# Output:
# Status: LIVE
# Risk Score: 20
# Bank: Test Bank
```

### Python

```python
from titan.core import CerberusValidator, CardAsset

async def validate():
    async with CerberusValidator() as validator:
        result = await validator.validate(CardAsset(
            number="4111111111111111",
            exp_month="12",
            exp_year="25",
            cvv="123"
        ))
        print(f"Status: {result.status}")
        print(f"Risk: {result.risk_score}")

import asyncio
asyncio.run(validate())
```

---

## Step 3: Configure Proxy (1 minute)

### Add to Pool

```python
from titan.core import ResidentialProxyManager, ProxyEndpoint

manager = ResidentialProxyManager()
manager.add_proxy(ProxyEndpoint(
    host="proxy.example.com",
    port=8080,
    username="user",
    password="pass",
    country="US",
    state="NY",
    city="New York"
))
```

### Or Use Provider

```python
manager = ResidentialProxyManager(
    provider="brightdata",
    username="your_user",
    password="your_pass"
)
```

### Or Use Lucid VPN (Recommended)

```bash
# Connect Lucid VPN with residential exit
titan-vpn-setup --connect --mode residential
```

---

## Step 4: Launch Browser (1 minute)

### Command Line

```bash
# Launch with profile
titan-browser -p titan_abc123 https://amazon.com

# With proxy
titan-browser -p titan_abc123 --proxy socks5://user:pass@proxy:1080 https://amazon.com
```

### Python (Full Integration)

```python
from titan.core import create_bridge

# Create bridge with all integrations
bridge = create_bridge(
    profile_uuid="titan_abc123",
    billing_address={
        "city": "New York",
        "state": "NY",
        "zip": "10001",
        "country": "US"
    },
    proxy_config={
        "url": "socks5://user:pass@proxy:1080"
    }
)

# Run pre-flight checks
report = bridge.run_preflight()
if not report.is_ready:
    print(f"Not ready: {report.abort_reason}")
    exit(1)

# Launch browser
bridge.launch_browser("https://amazon.com")
```

---

## Step 5: Manual Operation

Once the browser launches:

1. **Follow timing guide** - Don't rush
2. **Navigate organically** - Use search, don't direct URL
3. **Complete checkout** - Fill forms naturally
4. **Handle 3DS if needed** - Have SMS/app ready

### Timing Reference

| Action | Wait Time |
|--------|-----------|
| Product view | 45-90 seconds |
| Add to cart | 8-15 seconds |
| Checkout form | 60-180 seconds |
| Payment entry | 45-90 seconds |

---

## Complete Example Script

```python
#!/usr/bin/env python3
"""
TITAN V7.0 SINGULARITY — Complete Operation Script
"""

from titan.core import (
    GenesisEngine, ProfileConfig,
    CerberusValidator, CardAsset,
    create_bridge
)
import asyncio

async def main():
    # 1. Forge profile
    print("[1/4] Forging profile...")
    genesis = GenesisEngine()
    profile = genesis.forge_with_integration(
        ProfileConfig(
            target="amazon_us",
            persona_name="John Smith",
            age_days=95
        ),
        billing_address={
            "city": "New York",
            "state": "NY",
            "zip": "10001",
            "country": "US"
        }
    )
    print(f"      Profile: {profile.profile_id}")
    
    # 2. Validate card
    print("[2/4] Validating card...")
    async with CerberusValidator() as validator:
        result = await validator.validate(CardAsset(
            number="4111111111111111",
            exp_month="12",
            exp_year="25",
            cvv="123"
        ))
        print(f"      Status: {result.status}, Risk: {result.risk_score}")
        
        if result.risk_score > 50:
            print("      Card too risky, aborting")
            return
    
    # 3. Create bridge and run pre-flight
    print("[3/4] Running pre-flight checks...")
    bridge = create_bridge(
        profile_uuid=profile.profile_id,
        billing_address={
            "city": "New York",
            "state": "NY",
            "zip": "10001",
            "country": "US"
        }
    )
    
    report = bridge.run_preflight()
    print(f"      Checks passed: {report.checks_passed}")
    print(f"      Ready: {report.is_ready}")
    
    if not report.is_ready:
        print(f"      Abort: {report.abort_reason}")
        return
    
    # 4. Launch browser
    print("[4/4] Launching browser...")
    print("      Manual control enabled. Complete the operation.")
    bridge.launch_browser("https://amazon.com")
    
    print("\nOperation complete.")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## V7.0 Key Differences from V6.2

| Feature | V6.2 | V7.0 |
|---------|------|------|
| **Persona Config** | Hardcoded in profgen | Dynamic via JSON/env vars |
| **Timezone** | Hardcoded `Asia/Colombo` | Auto-derived from billing state |
| **Locale/Geo** | Hardcoded | Auto-derived from billing country |
| **Screen Dims** | Random per layer | Centralized `SCREEN_W`/`SCREEN_H` |
| **Downloads** | macOS artifacts | Windows-correct `.exe`/`.zip` |
| **Audio Fingerprint** | Random 44100/48000 | Locked 44100Hz (matches hardener) |
| **Logger Names** | TITAN-V6-* | TITAN-V7-* |
| **Codename** | SOVEREIGN | SINGULARITY |

---

## Troubleshooting

### "Camoufox not found"

```bash
pip install camoufox[geoip]
python -m camoufox fetch
```

### "Kernel module not loaded"

```bash
sudo modprobe titan_hw
```

### "Pre-flight failed"

- Check proxy is residential (not datacenter)
- Verify profile exists
- Check network connectivity
- Ensure persona config matches billing address

### "Card declined"

- Verify card details are correct
- Check Cerberus risk score
- Ensure billing address matches cardholder data
- Try different card

---

## V7.0.2 New Capabilities

### MaxDrain Strategy (Auto after CC validation)
Card validates LIVE → orange **"MaxDrain Strategy"** button appears → click for full extraction plan.
```python
from cerberus_enhanced import generate_drain_plan, format_drain_plan
plan = generate_drain_plan("401200")  # Auto from BIN
print(format_drain_plan(plan))        # Full step-by-step plan
```

### Non-VBV Card Recommendations
```python
from three_ds_strategy import get_non_vbv_recommendations, get_easy_countries
recs = get_non_vbv_recommendations(country="US", target="g2a.com", amount=150)
easy = get_easy_countries()  # 13 countries ranked by difficulty
```

### Target Discovery (70+ sites, auto-verified)
```python
from target_discovery import get_easy_sites, get_shopify_sites, probe_site
easy = get_easy_sites(country="US")      # All easy 2D sites
shops = get_shopify_sites()              # 19 easy Shopify stores
probe_site("new-store.com")             # Auto-detect PSP/fraud/3DS
```

### Intel Monitor (Forums & DarkWeb)
```python
from intel_monitor import IntelMonitor
monitor = IntelMonitor()
sources = monitor.get_sources()          # 16 curated sources
alerts = monitor.get_alerts()            # High-priority intel
# Configure source after manual login:
monitor.configure_source("nulled", cookies={...}, auto_engage=True)
```

### IP Reputation Pre-Check
Now runs automatically during pre-flight. Catches bad IPs before they burn cards.
Score >25 = rotate recommended. Score >50 = abort.

---

## Next Steps

1. Read the [Architecture Documentation](ARCHITECTURE.md)
2. Read **`Final/V7_COMPLETE_FEATURE_REFERENCE.md`** — exhaustive feature doc with every technique
3. Set up [Lucid VPN](../README.md#10-lucid-vpn--zero-signature-network-layer) for zero-signature networking
4. Read module deep-dives: [Genesis](MODULE_GENESIS_DEEP_DIVE.md) | [Cerberus](MODULE_CERBERUS_DEEP_DIVE.md) | [KYC](MODULE_KYC_DEEP_DIVE.md)
5. Check the [Developer Update Guide](DEVELOPER_UPDATE_GUIDE.md) before making changes

---

*TITAN V7.0.2 SINGULARITY - Quick Start Guide*
*Authority: Dva.12 | Estimated success rate: 76-83% with good CC*
