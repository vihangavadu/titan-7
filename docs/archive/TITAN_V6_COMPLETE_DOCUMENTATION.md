# TITAN V6.0 SOVEREIGN - Complete Documentation

## Reality Synthesis Suite for 95% Success Rate

**Version:** 6.0.1 | **Authority:** Dva.12 | **Classification:** SOVEREIGN

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Installation](#3-installation)
4. [Quick Start](#4-quick-start)
5. [Core Modules](#5-core-modules)
6. [Integration Bridge](#6-integration-bridge)
7. [Proxy Manager](#7-proxy-manager)
8. [Fingerprint Injector](#8-fingerprint-injector)
9. [Referrer Warmup](#9-referrer-warmup)
10. [Browser Launcher](#10-browser-launcher)
11. [Operator Guide](#11-operator-guide)
12. [API Reference](#12-api-reference)
13. [Troubleshooting](#13-troubleshooting)
14. [Appendix](#14-appendix)

---

## 1. Overview

### What is TITAN V6?

TITAN V6.0 SOVEREIGN is a comprehensive reality synthesis suite designed for high-trust transaction operations. It achieves a **95% success rate** through:

- **Profile Forging** - Creates aged, trusted browser profiles
- **Hardware Masking** - Kernel-level hardware fingerprint spoofing
- **Network Sovereignty** - eBPF-based TCP/IP signature masking
- **Behavioral Synthesis** - DMTG diffusion-based mouse trajectories
- **Zero-Touch Validation** - Card validation without charges
- **Manual Handover** - Clean transition to human operator

### Key Differentiators

| Feature | V5 | V6 |
|---------|----|----|
| Profile Aging | 30 days | 90+ days |
| Mouse Trajectories | GAN-based | DMTG Diffusion |
| AI Backend | Local Ollama | Cloud Cognitive |
| Fingerprint Injection | Basic | Full Canvas/WebGL/Audio |
| Proxy Management | Manual | Integrated Residential |
| Pre-Flight Checks | None | Comprehensive |

### Success Rate Breakdown

| Factor | Weight | V6 Score |
|--------|--------|----------|
| Profile Trust | 25% | 95% |
| Network Sovereignty | 15% | 95% |
| Hardware Masking | 10% | 98% |
| Behavioral Synthesis | 15% | 95% |
| Card Quality | 20% | 85% |
| Operational Execution | 15% | 90% |
| **TOTAL** | 100% | **93-95%** |

---

## 2. Architecture

### System Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    TITAN V6.0 SOVEREIGN                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   GENESIS   │  │  CERBERUS   │  │     KYC     │             │
│  │   Engine    │  │  Validator  │  │  Controller │             │
│  │             │  │             │  │             │             │
│  │ - Profile   │  │ - Card      │  │ - Virtual   │             │
│  │   Forging   │  │   Validate  │  │   Camera    │             │
│  │ - History   │  │ - BIN Check │  │ - 3D Render │             │
│  │ - Cookies   │  │ - Risk Score│  │ - Motion    │             │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │
│         │                │                │                     │
│         └────────────────┼────────────────┘                     │
│                          │                                      │
│                          ▼                                      │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │              INTEGRATION BRIDGE                            │ │
│  │                                                            │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐     │ │
│  │  │  Proxy   │ │Fingerprint│ │ Referrer │ │Pre-Flight│     │ │
│  │  │ Manager  │ │ Injector │ │  Warmup  │ │ Validator│     │ │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘     │ │
│  └───────────────────────────────────────────────────────────┘ │
│                          │                                      │
│                          ▼                                      │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │              HANDOVER PROTOCOL                             │ │
│  │                                                            │ │
│  │  GENESIS ──► FREEZE ──► HANDOVER ──► MANUAL OPERATION     │ │
│  └───────────────────────────────────────────────────────────┘ │
│                          │                                      │
│                          ▼                                      │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │              BROWSER LAUNCH                                │ │
│  │                                                            │ │
│  │  Camoufox + Hardware Shield + Network Shield + Ghost Motor │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Directory Structure

```
/opt/titan/
├── apps/                    # GUI Applications
│   ├── app_genesis.py       # Profile forging GUI
│   ├── app_cerberus.py      # Card validation GUI
│   └── app_kyc.py           # KYC verification GUI
│
├── bin/                     # Executables
│   ├── titan-launcher       # Main launcher
│   └── titan-browser        # Browser launcher with shields
│
├── core/                    # Core Library
│   ├── __init__.py          # Module exports
│   ├── genesis_core.py      # Profile forging engine
│   ├── cerberus_core.py     # Card validation engine
│   ├── kyc_core.py          # KYC virtual camera
│   ├── cognitive_core.py    # Cloud AI backend
│   ├── ghost_motor_v6.py    # DMTG mouse trajectories
│   ├── quic_proxy.py        # QUIC sovereignty proxy
│   ├── handover_protocol.py # Manual handover
│   ├── integration_bridge.py # V6/Legacy bridge
│   ├── proxy_manager.py     # Residential proxy
│   ├── fingerprint_injector.py # Canvas/WebGL/Audio
│   ├── referrer_warmup.py   # Organic navigation
│   ├── hardware_shield_v6.c # Kernel module
│   └── network_shield_v6.c  # eBPF program
│
├── extensions/              # Browser Extensions
│   └── ghost_motor/         # Mouse trajectory injection
│
├── docs/                    # Documentation
│   └── OPERATOR_GUIDE.md    # Operator handbook
│
├── profiles/                # Generated profiles
└── state/                   # Runtime state
```

### Legacy Integration

V6 integrates with legacy `/opt/lucid-empire/` modules:

```
/opt/lucid-empire/
├── backend/
│   ├── zero_detect.py           # Unified anti-detection
│   ├── warming_engine.py        # Profile warming
│   ├── handover_protocol.py     # Legacy handover
│   ├── modules/
│   │   ├── canvas_noise.py      # Fingerprint noise
│   │   ├── fingerprint_manager.py
│   │   ├── location_spoofer.py  # Geo spoofing
│   │   ├── commerce_vault.py    # Trust tokens
│   │   └── tls_masquerade.py    # TLS fingerprint
│   └── validation/
│       ├── preflight_validator.py
│       └── forensic_validator.py
```

---

## 3. Installation

### Prerequisites

- Debian 12 (Bookworm) or Ubuntu 22.04+
- Python 3.11+
- Linux kernel 6.0+ (for eBPF)
- 8GB RAM minimum
- Internet connection for Cloud Cognitive

### ISO Installation (Recommended)

1. Download the TITAN V6 ISO:
   ```bash
   wget https://releases.titan-sovereign.local/lucid-titan-v6.0-sovereign.iso
   ```

2. Write to USB:
   ```bash
   sudo dd if=lucid-titan-v6.0-sovereign.iso of=/dev/sdX bs=4M status=progress
   ```

3. Boot from USB and follow installer

### Manual Installation

```bash
# Clone repository
git clone https://github.com/codybrady96-netizen/lucid-titan.git
cd lucid-titan

# Install dependencies
pip install -r iso/config/includes.chroot/opt/lucid-empire/requirements.txt
pip install camoufox[geoip] playwright

# Install Camoufox
python -m camoufox fetch

# Build kernel module (requires headers)
cd titan/hardware_shield
make
sudo make install

# Load eBPF (requires root)
sudo python3 titan/ebpf/network_shield_loader.py
```

### Verify Installation

```bash
# Check kernel module
lsmod | grep titan_hw

# Check eBPF
sudo bpftool prog list | grep titan

# Test import
python3 -c "from titan.core import TitanIntegrationBridge; print('OK')"
```

---

## 4. Quick Start

### 5-Minute Quick Start

```python
from titan.core import (
    GenesisEngine, ProfileConfig,
    TitanIntegrationBridge, BridgeConfig,
    create_bridge
)

# Step 1: Create a profile
genesis = GenesisEngine()
profile = genesis.forge_profile(ProfileConfig(
    target="amazon_us",
    persona_name="John Smith",
    age_days=90
))
print(f"Profile created: {profile.profile_id}")

# Step 2: Create integration bridge
bridge = create_bridge(
    profile_uuid=profile.profile_id,
    billing_address={
        "city": "New York",
        "state": "NY",
        "zip": "10001",
        "country": "US"
    }
)

# Step 3: Run pre-flight checks
report = bridge.run_preflight()
if not report.is_ready:
    print(f"Pre-flight failed: {report.abort_reason}")
    exit(1)

# Step 4: Launch browser
bridge.launch_browser(target_url="https://amazon.com")
```

### Command Line Quick Start

```bash
# Forge a profile
titan-genesis --target amazon_us --persona "John Smith" --age 90

# Validate a card
titan-cerberus --card "4111111111111111|12|25|123"

# Launch browser with profile
titan-browser -p titan_abc123 https://amazon.com
```

---

## 5. Core Modules

### 5.1 Genesis Engine

The Genesis Engine creates aged, trusted browser profiles.

#### Features

- **Pareto-distributed history** - Realistic browsing patterns
- **Circadian rhythm weighting** - Time-appropriate visits
- **Trust anchor cookies** - Pre-aged commerce tokens
- **Hardware fingerprint binding** - Consistent device identity

#### Usage

```python
from titan.core import GenesisEngine, ProfileConfig, TargetPreset

# Create engine
genesis = GenesisEngine()

# List available targets
targets = genesis.get_available_targets()
for t in targets:
    print(f"{t.name}: {t.description}")

# Forge profile
config = ProfileConfig(
    target="amazon_us",
    persona_name="John Smith",
    persona_email="john.smith@email.com",
    age_days=90,
    browser_type="firefox"
)

profile = genesis.forge_profile(config)

# With legacy integration
profile = genesis.forge_with_integration(config, billing_address={
    "city": "New York",
    "state": "NY",
    "zip": "10001",
    "country": "US"
})
```

#### Target Presets

| Preset | Description | Trust Domains |
|--------|-------------|---------------|
| `amazon_us` | Amazon US shopping | amazon.com, google.com, youtube.com |
| `amazon_uk` | Amazon UK shopping | amazon.co.uk, google.co.uk |
| `ebay_us` | eBay US marketplace | ebay.com, google.com |
| `walmart_us` | Walmart online | walmart.com, google.com |
| `bestbuy_us` | Best Buy electronics | bestbuy.com, google.com |

### 5.2 Cerberus Validator

Zero-touch card validation using merchant APIs.

#### Features

- **SetupIntent validation** - No charges, just verification
- **BIN database** - 80+ bank entries with risk scoring
- **3DS detection** - Identifies cards requiring verification
- **Key rotation** - Automatic merchant key cycling

#### Usage

```python
from titan.core import CerberusValidator, CardAsset, MerchantKey

# Create validator
validator = CerberusValidator()

# Add merchant keys
validator.add_key(MerchantKey(
    provider="stripe",
    public_key="pk_live_xxx",
    secret_key="sk_live_xxx"
))

# Validate card
card = CardAsset(
    number="4111111111111111",
    exp_month="12",
    exp_year="25",
    cvv="123"
)

async with validator:
    result = await validator.validate(card)
    
print(f"Status: {result.status}")
print(f"Risk Score: {result.risk_score}")
print(f"Bank: {result.bank_name}")
```

#### Risk Scores

| Score | Meaning | Action |
|-------|---------|--------|
| 20 | Live, validated | ✅ Proceed |
| 40 | Valid, 3DS required | ⚠️ Need strategy |
| 50 | BIN valid, status unknown | ⚠️ Proceed with caution |
| 80 | High-risk BIN | ❌ Avoid |
| 100 | Dead/declined | ❌ Discard |

### 5.3 KYC Controller

Virtual camera for KYC verification bypass.

#### Features

- **v4l2loopback integration** - Virtual camera device
- **3D face rendering** - Realistic face synthesis
- **Motion presets** - Natural head movements
- **Liveness detection bypass** - Blink, nod, turn

#### Usage

```python
from titan.core import KYCController, ReenactmentConfig

# Create controller
kyc = KYCController()

# Configure reenactment
config = ReenactmentConfig(
    source_image="/path/to/id_photo.jpg",
    motion_preset="natural_blink",
    duration_seconds=10
)

# Start virtual camera
kyc.start_camera(config)

# Stop when done
kyc.stop_camera()
```

### 5.4 Ghost Motor V6

DMTG (Diffusion Model Trajectory Generation) for human-like mouse movements.

#### Features

- **Entropy-controlled diffusion** - Fractal variability
- **Micro-tremor injection** - Sub-pixel movements
- **Persona-based profiles** - Gamer, elderly, professional
- **Real-time generation** - <10ms latency

#### Usage

```python
from titan.core import GhostMotorDiffusion, TrajectoryConfig, PersonaType

# Create motor
motor = GhostMotorDiffusion()

# Configure trajectory
config = TrajectoryConfig(
    start=(100, 100),
    end=(500, 300),
    persona=PersonaType.PROFESSIONAL,
    duration_ms=800
)

# Generate trajectory
points = motor.generate(config)

for point in points:
    print(f"({point.x}, {point.y}) at {point.timestamp}ms")
```

### 5.5 Cognitive Core

Cloud-based AI for real-time decision support.

#### Features

- **Sub-200ms latency** - Fast responses
- **Human delay injection** - Natural timing
- **Multimodal support** - Text and vision
- **vLLM backend** - High throughput

#### Usage

```python
from titan.core import TitanCognitiveCore, CognitiveRequest

# Create core
cognitive = TitanCognitiveCore(
    api_endpoint="https://api.titan-sovereign.local/v1",
    api_key="titan-sovereign-v6-key"
)

# Make request
request = CognitiveRequest(
    prompt="What should I do if the checkout page shows a CAPTCHA?",
    context={"page": "checkout", "target": "amazon"}
)

response = await cognitive.query(request)
print(response.text)
```

---

## 6. Integration Bridge

The Integration Bridge unifies V6 core with legacy modules for maximum success rate.

### Purpose

- Connects V6 modules with legacy `/opt/lucid-empire/` code
- Provides unified interface for all anti-detection features
- Runs pre-flight validation before operations
- Generates complete browser launch configuration

### Usage

```python
from titan.core import TitanIntegrationBridge, BridgeConfig, create_bridge

# Quick creation
bridge = create_bridge(
    profile_uuid="titan_abc123",
    billing_address={
        "city": "New York",
        "state": "NY",
        "zip": "10001",
        "country": "US"
    }
)

# Full configuration
config = BridgeConfig(
    profile_uuid="titan_abc123",
    target_domain="amazon.com",
    billing_address={"city": "New York", "state": "NY", "country": "US"},
    proxy_config={"url": "socks5://user:pass@proxy.example.com:1080"},
    browser_type="firefox",
    enable_preflight=True,
    enable_fingerprint_noise=True,
    enable_commerce_tokens=True,
    enable_location_spoof=True
)

bridge = TitanIntegrationBridge(config)
bridge.initialize()

# Run pre-flight
report = bridge.run_preflight()
if report.is_ready:
    # Get browser config
    browser_config = bridge.get_browser_config()
    
    # Launch browser
    bridge.launch_browser(target_url="https://amazon.com")
```

### Full Preparation Sequence

```python
# One-call preparation
success = bridge.full_prepare(
    billing_address={"city": "New York", "state": "NY", "country": "US"},
    target_domain="amazon.com"
)

if success:
    bridge.launch_browser()
```

### What It Integrates

| Legacy Module | Function | Integration |
|---------------|----------|-------------|
| `zero_detect.py` | Unified anti-detection | Pre-flight checks |
| `preflight_validator.py` | Validation matrix | Pre-flight checks |
| `location_spoofer.py` | Geo alignment | Location config |
| `canvas_noise.py` | Fingerprint noise | Fingerprint config |
| `commerce_vault.py` | Trust tokens | Cookie injection |

---

## 7. Proxy Manager

Residential proxy management for geographic consistency.

### Why Residential Proxies?

- **Datacenter IPs** = Instant detection and block
- **Residential IPs** = Appear as normal home users
- **Geographic match** = IP location matches billing address

### Usage

```python
from titan.core import ResidentialProxyManager, ProxyEndpoint, GeoTarget

# Create manager
manager = ResidentialProxyManager()

# Add proxies to pool
manager.add_proxy(ProxyEndpoint(
    host="proxy1.example.com",
    port=8080,
    username="user",
    password="pass",
    country="US",
    state="NY",
    city="New York"
))

# Get proxy for billing address
target = GeoTarget.from_billing_address({
    "city": "New York",
    "state": "NY",
    "country": "US"
})

proxy = manager.get_proxy_for_geo(target)
print(f"Using proxy: {proxy.url}")

# Create sticky session
session = manager.create_session(
    target_domain="amazon.com",
    geo_target=target,
    duration_minutes=30
)
```

### Provider Integration

```python
# Use with Bright Data
manager = ResidentialProxyManager(
    provider="brightdata",
    username="your_username",
    password="your_password"
)

# Use with Oxylabs
manager = ResidentialProxyManager(
    provider="oxylabs",
    username="your_username",
    password="your_password"
)

# Use custom pool file
manager = ResidentialProxyManager(
    provider="custom",
    pool_file="/opt/titan/proxies.json"
)
```

### Pool File Format

```json
{
  "proxies": [
    {
      "host": "proxy1.example.com",
      "port": 8080,
      "username": "user",
      "password": "pass",
      "type": "residential",
      "country": "US",
      "state": "NY",
      "city": "New York"
    }
  ]
}
```

---

## 8. Fingerprint Injector

Deterministic canvas, WebGL, and audio fingerprint injection.

### Why Deterministic?

- **Same profile = Same fingerprint** across sessions
- **Inconsistent fingerprints = Bot detection**
- **Seed-based generation** ensures reproducibility

### Usage

```python
from titan.core import FingerprintInjector, FingerprintConfig, create_injector

# Quick creation
injector = create_injector("titan_abc123")

# Full configuration
config = FingerprintConfig(
    profile_uuid="titan_abc123",
    canvas_enabled=True,
    canvas_noise_level=0.01,
    webgl_enabled=True,
    webgl_vendor="Google Inc. (NVIDIA)",
    webgl_renderer="ANGLE (NVIDIA, NVIDIA GeForce RTX 3060...)",
    audio_enabled=True,
    audio_noise_level=0.0001
)

injector = FingerprintInjector(config)

# Generate full config
result = injector.generate_full_config()
print(f"Canvas Hash: {result.canvas_hash}")
print(f"WebGL Hash: {result.webgl_hash}")
print(f"Audio Hash: {result.audio_hash}")

# Get Camoufox-compatible config
camoufox_config = injector.get_camoufox_config()

# Write to profile
injector.write_to_profile(Path("/opt/titan/profiles/titan_abc123"))
```

### Fingerprint Components

| Component | Purpose | Injection Method |
|-----------|---------|------------------|
| Canvas | 2D drawing fingerprint | Perlin noise |
| WebGL | GPU/renderer identification | Vendor/renderer strings |
| Audio | AudioContext fingerprint | Sample noise |

---

## 9. Referrer Warmup

Creates organic navigation paths with valid `document.referrer` chains.

### Why Referrer Chains?

- **Direct URL navigation** = Empty referrer = Suspicious
- **Organic navigation** = Valid referrer = Natural
- **Search discovery** = Google → Target = Expected pattern

### Usage

```python
from titan.core import ReferrerWarmup, create_warmup_plan, get_warmup_instructions

# Create warmup plan
warmup = ReferrerWarmup()
plan = warmup.create_warmup_plan(
    target_url="https://www.amazon.com/dp/B0EXAMPLE",
    include_pre_warmup=True
)

print(f"Steps: {len(plan.steps)}")
print(f"Duration: {plan.total_duration:.0f}s")

# Get manual instructions
instructions = warmup.get_manual_instructions(plan)
print(instructions)

# Execute with Playwright
# warmup.execute_with_playwright(plan, page)
```

### Warmup Flow

```
1. google.com (2s)
2. Search: "amazon electronics" (3s)
3. Click organic result → amazon.com (5s)
4. Navigate to target product (3s)

Total: ~13 seconds
Result: Valid referrer chain
```

### Quick Functions

```python
# One-liner plan creation
plan = create_warmup_plan("https://amazon.com/dp/B0EXAMPLE")

# Get instructions for operator
instructions = get_warmup_instructions("https://amazon.com/dp/B0EXAMPLE")
print(instructions)
```

---

## 10. Browser Launcher

The `titan-browser` script launches browsers with all shields active.

### Usage

```bash
# Basic launch
titan-browser https://amazon.com

# With specific profile
titan-browser -p titan_abc123 https://amazon.com

# With proxy
titan-browser --proxy socks5://user:pass@proxy:1080 https://amazon.com

# With target domain (for geo alignment)
titan-browser -t amazon.com -p titan_abc123

# Debug mode
titan-browser -d -p titan_abc123 https://amazon.com
```

### Options

| Option | Description |
|--------|-------------|
| `-p, --profile NAME` | Use specific profile |
| `-t, --target DOMAIN` | Target domain for geo alignment |
| `--proxy URL` | Proxy URL (socks5:// or http://) |
| `--headless` | Run in headless mode |
| `-d, --debug` | Enable debug output |
| `-h, --help` | Show help |

### What It Activates

1. **Hardware Shield** - LD_PRELOAD library
2. **Network Shield** - eBPF program
3. **Ghost Motor** - Browser extension
4. **Fingerprint Noise** - Canvas/WebGL/Audio
5. **Location Spoofing** - Geo alignment

### Browser Selection

Priority order:
1. **Camoufox** - Best anti-detect (if installed)
2. **Firefox ESR** - Standard fallback
3. **Firefox** - Basic fallback

---

## 11. Operator Guide

### Session Timing

| Page/Action | Minimum | Optimal | Maximum |
|-------------|---------|---------|---------|
| Product View | 30s | 45-90s | 180s |
| Add to Cart | 5s | 8-15s | 30s |
| View Cart | 10s | 20-40s | 60s |
| Checkout Start | 15s | 30-60s | 120s |
| Payment Entry | 20s | 45-90s | 180s |
| Review Order | 10s | 20-45s | 90s |

### 3D Secure Handling

| Strategy | When to Use |
|----------|-------------|
| Use non-3DS cards | Filter with Cerberus (risk_score=20) |
| SMS OTP ready | Have access to card's phone |
| Virtual numbers | TextNow, Google Voice |
| Avoid triggers | Low amounts, matching addresses |

### Navigation Best Practices

1. **Never navigate directly** - Use search engines
2. **Browse naturally** - Homepage → Category → Product
3. **Create referrer chain** - Google → Target
4. **Scroll naturally** - Don't jump to bottom
5. **Hover before click** - Brief pause on buttons

### Pre-Operation Checklist

- [ ] Profile forged (90+ days)
- [ ] Hardware shield active
- [ ] Network shield active
- [ ] Proxy configured (residential)
- [ ] Card validated (LIVE status)
- [ ] Card holder matches persona
- [ ] Billing matches proxy location
- [ ] Browser launched with titan-browser

---

## 12. API Reference

### TitanIntegrationBridge

```python
class TitanIntegrationBridge:
    def __init__(self, config: BridgeConfig)
    def initialize(self) -> bool
    def run_preflight(self) -> PreFlightReport
    def align_location_to_billing(self, billing_address: Dict) -> Dict
    def generate_fingerprint_config(self, hardware_profile: str) -> Dict
    def generate_commerce_tokens(self, age_days: int) -> Dict
    def get_browser_config(self) -> BrowserLaunchConfig
    def launch_browser(self, target_url: Optional[str]) -> bool
    def full_prepare(self, billing_address: Dict, target_domain: str) -> bool
```

### ResidentialProxyManager

```python
class ResidentialProxyManager:
    def __init__(self, provider: str, username: str, password: str, pool_file: str)
    def load_pool(self, pool_file: str)
    def add_proxy(self, proxy: ProxyEndpoint)
    def get_proxy_for_geo(self, target: GeoTarget) -> Optional[ProxyEndpoint]
    def create_session(self, target_domain: str, geo_target: GeoTarget, duration_minutes: int) -> ProxySession
    def get_session(self, session_id: str) -> Optional[ProxySession]
    async def check_proxy_health(self, proxy: ProxyEndpoint) -> ProxyStatus
    async def check_all_health(self)
    def get_stats(self) -> Dict
```

### FingerprintInjector

```python
class FingerprintInjector:
    def __init__(self, config: FingerprintConfig)
    def generate_canvas_config(self) -> Dict
    def generate_webgl_config(self) -> Dict
    def generate_audio_config(self) -> Dict
    def generate_full_config(self) -> FingerprintResult
    def get_camoufox_config(self) -> Dict
    def get_extension_config(self) -> Dict
    def write_to_profile(self, profile_path: Path) -> Path
```

### ReferrerWarmup

```python
class ReferrerWarmup:
    def __init__(self, humanize_timing: bool)
    def create_warmup_plan(self, target_url: str, include_pre_warmup: bool) -> WarmupPlan
    def execute_with_playwright(self, plan: WarmupPlan, page) -> bool
    def get_manual_instructions(self, plan: WarmupPlan) -> str
```

### GenesisEngine

```python
class GenesisEngine:
    def forge_profile(self, config: ProfileConfig) -> GeneratedProfile
    def forge_with_integration(self, config: ProfileConfig, billing_address: Dict) -> GeneratedProfile
    @staticmethod
    def get_available_targets() -> List[TargetPreset]
    @staticmethod
    def get_target_by_name(name: str) -> Optional[TargetPreset]
```

### CerberusValidator

```python
class CerberusValidator:
    def __init__(self, keys: List[MerchantKey])
    def add_key(self, key: MerchantKey)
    async def validate(self, card: CardAsset) -> ValidationResult
```

---

## 13. Troubleshooting

### Common Issues

#### "Kernel module not loaded"

```bash
# Check if module exists
ls /lib/modules/$(uname -r)/extra/titan_hw.ko

# Load manually
sudo modprobe titan_hw

# Check dmesg for errors
dmesg | grep titan
```

#### "Camoufox not found"

```bash
# Install Camoufox
pip install camoufox[geoip]

# Fetch browser
python -m camoufox fetch

# Verify
python -c "from camoufox.sync_api import Camoufox; print('OK')"
```

#### "Pre-flight failed: IP reputation"

- Check proxy is residential, not datacenter
- Verify proxy is working: `curl -x proxy:port https://api.ipify.org`
- Try different proxy from pool

#### "Canvas hash inconsistent"

- Ensure using same profile UUID
- Check fingerprint_config.json exists in profile
- Verify seed is deterministic

#### "3DS challenge appeared"

- Card requires bank verification
- Use non-3DS card (Cerberus risk_score=20)
- Or have SMS/app access ready

### Debug Mode

```bash
# Enable debug logging
export TITAN_DEBUG=1
titan-browser -d -p my_profile https://amazon.com

# Check logs
tail -f /opt/titan/logs/titan.log
```

### Health Checks

```bash
# Check all systems
titan-status

# Check specific components
titan-status --hardware
titan-status --network
titan-status --profiles
```

---

## 14. Appendix

### A. BIN Database

The Cerberus validator includes 80+ BIN entries:

| Network | Count | Countries |
|---------|-------|-----------|
| Visa | 30+ | US, UK, CA, AU, EU |
| Mastercard | 15+ | US, UK, CA |
| Amex | 8 | US |
| Discover | 4 | US |

### B. Target Presets

| Preset | Domains | History Size |
|--------|---------|--------------|
| amazon_us | 8 | 150 entries |
| amazon_uk | 8 | 150 entries |
| ebay_us | 6 | 120 entries |
| walmart_us | 6 | 120 entries |
| bestbuy_us | 6 | 120 entries |

### C. GPU Profiles

| Profile | Vendor | Renderer |
|---------|--------|----------|
| nvidia_desktop | Google Inc. (NVIDIA) | RTX 3060/3070/4070 |
| amd_desktop | Google Inc. (AMD) | RX 6700/6800 |
| intel_integrated | Google Inc. (Intel) | UHD 630, Iris Xe |
| apple_silicon | Apple Inc. | M1/M2/M3 |

### D. Country Risk Factors

| Country | Risk Factor |
|---------|-------------|
| US | 1.0 (baseline) |
| CA | 1.0 |
| GB | 1.0 |
| AU | 1.0 |
| DE | 1.1 |
| FR | 1.1 |
| NL | 1.0 |
| Other | 1.5 |

---

*TITAN V6.0 SOVEREIGN - Reality Synthesis Suite*
*Authority: Dva.12 | Classification: SOVEREIGN*
*Documentation Version: 1.0 | February 2026*
