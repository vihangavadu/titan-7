# TITAN V6.2 SOVEREIGN - Quick Start Guide

## Get Started in 5 Minutes

**Version:** 6.2.0 | **Authority:** Dva.12

---

## Prerequisites

- TITAN V6.2 ISO booted (USB/VM) — `titan-first-boot` runs automatically on first boot
- Camoufox installed (auto-installed by first boot, or `pip install camoufox[geoip]`)
- Operator config set: edit `/opt/titan/config/titan.env` (proxy, VPN, API keys)
- Residential proxy or Lucid VPN configured (recommended)

> **Recommended:** Use the **Unified GUI** (`python3 /opt/titan/apps/app_unified.py`) for all operations. The steps below show both GUI and CLI/Python approaches.

---

## Step 1: Forge a Profile (2 minutes)

### Option A: Command Line

```bash
# Forge a 90-day aged profile for Amazon US
titan-genesis --target amazon_us --persona "John Smith" --age 90

# Output: Profile created: titan_abc123
```

### Option B: Python

```python
from titan.core import GenesisEngine, ProfileConfig

genesis = GenesisEngine()
profile = genesis.forge_profile(ProfileConfig(
    target="amazon_us",
    persona_name="John Smith",
    age_days=90
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
TITAN V6.2 Complete Operation Script
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
            age_days=90
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

### "Card declined"

- Verify card details are correct
- Check Cerberus risk score
- Try different card

---

## Next Steps

1. Read the [V6.2 Master Documentation](TITAN_V6.2_MASTER_DOCUMENTATION.md)
2. Set up [Lucid VPN](../README.md#10-lucid-vpn--zero-signature-network-layer) for zero-signature networking
3. Read module deep-dives: [Genesis](MODULE_GENESIS_DEEP_DIVE.md) | [Cerberus](MODULE_CERBERUS_DEEP_DIVE.md) | [KYC](MODULE_KYC_DEEP_DIVE.md)
4. Check the [Developer Update Guide](DEVELOPER_UPDATE_GUIDE.md) before making changes
5. Review the [Operationalizing Titan V6.2 System](Operationalizing%20Titan%20V6.2%20System.txt) for infrastructure deployment

---

*TITAN V6.2 SOVEREIGN - Quick Start Guide*
*Authority: Dva.12 | Get to 95%+ success rate*
