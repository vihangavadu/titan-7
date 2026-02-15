# TITAN V6 Testing Environment

## Virtualized PSP & Detection System Testing

**Version:** 6.1.0 | **Authority:** Dva.12

---

## Overview

The TITAN V6 Testing Environment provides a complete virtualized testing framework for validating profiles, cards, and configurations against realistic PSP and fraud detection systems **without hitting production endpoints**.

### Key Features

- **PSP Sandboxes** - Emulate Stripe, Adyen, Braintree, PayPal, Square
- **Detection Emulators** - Fingerprint, Behavioral, Network, Device, Velocity
- **Automated Test Runner** - Run comprehensive test suites
- **Failure Analysis** - Root cause identification with remediation steps
- **Report Generation** - JSON, Markdown, and HTML reports

### Why Use This?

| Without Testing Environment | With Testing Environment |
|----------------------------|--------------------------|
| Trial and error on live sites | Pre-validate before operation |
| Unknown failure reasons | Detailed failure analysis |
| No success rate metrics | Track success rate trends |
| Manual debugging | Automated recommendations |

---

## Quick Start

### Command Line

```bash
# Run default test suite
titan-test run

# Test a specific profile
titan-test profile /path/to/profile.json

# Quick card test
titan-test card 4111111111111111|12|25|123

# Test fingerprint configuration
titan-test fingerprint

# Test behavioral data
titan-test behavioral

# Test network configuration
titan-test network

# View latest report
titan-test report
```

### Python API

```python
from titan.testing import create_test_environment, TestEnvironment

# Create and initialize environment
env = create_test_environment()

# Run default test suite
report = env.run_tests()
print(f"Success Rate: {report.success_rate:.1f}%")

# Test a specific profile
result = env.test_profile({
    "fingerprint": {
        "canvas_hash": "abc123",
        "webgl_vendor": "Google Inc. (NVIDIA)",
        "webgl_renderer": "ANGLE (NVIDIA, GeForce RTX 3060)",
    },
    "behavioral": {
        "mouse_entropy": 0.75,
        "time_on_page_seconds": 120,
    },
    "network": {
        "ip_address": "203.0.113.50",
        "ip_type": "residential",
    },
    "card": {
        "number": "4111111111111111",
        "exp_month": "12",
        "exp_year": "25",
        "cvv": "123",
    },
})

if result["overall_passed"]:
    print("Profile is ready for operation!")
else:
    print("Issues found:")
    for reason in result["failure_reasons"]:
        print(f"  - {reason}")
```

---

## Components

### 1. PSP Sandboxes

Emulate real Payment Service Provider APIs with realistic decline logic.

#### Available PSPs

| PSP | Features |
|-----|----------|
| **Stripe** | Radar rules, velocity checks, 3DS simulation |
| **Adyen** | RevenueProtect, device fingerprint required |
| **Braintree** | Risk scoring, BIN validation |
| **PayPal** | Account-based risk, behavioral focus |
| **Square** | Basic validation, BIN checks |

#### Test Cards

| Card Number | Behavior |
|-------------|----------|
| `4111111111111111` | Always approved |
| `4000000000000002` | Always declined |
| `4000000000009995` | Insufficient funds |
| `4000000000000069` | Expired card |
| `4000000000000127` | Invalid CVV |
| `4000000000003220` | Requires 3DS |
| `4000000000003063` | 3DS fails |
| `4100000000000019` | Fraud suspected |

#### Usage

```python
from titan.testing import StripeSandbox, TransactionRequest, CardData

stripe = StripeSandbox(config={"risk_threshold": 75})

request = TransactionRequest(
    card=CardData(number="4111111111111111", exp_month="12", exp_year="25", cvv="123"),
    amount=99.99,
)

response = stripe.process_payment(request)
print(f"Success: {response.success}")
print(f"Risk Score: {response.risk_score}")
```

### 2. Detection Emulators

Emulate real-world fraud detection systems.

#### Available Detectors

| Detector | What It Checks |
|----------|----------------|
| **Fingerprint** | Canvas, WebGL, Audio, Screen, User-Agent, Automation |
| **Behavioral** | Mouse entropy, Keystroke timing, Navigation, Timing |
| **Network** | IP reputation, Datacenter detection, Geo mismatch, TLS |
| **Device** | Platform consistency, Hardware concurrency |
| **Velocity** | Transaction frequency, Amount patterns |

#### Risk Signals

Each detector produces risk signals with:
- **Name** - Signal identifier
- **Category** - fingerprint, behavioral, network, etc.
- **Severity** - low, medium, high, critical
- **Score** - Numeric risk contribution
- **Description** - Human-readable explanation
- **Remediation** - How to fix the issue

#### Usage

```python
from titan.testing import FingerprintDetector

detector = FingerprintDetector(config={"threshold": 70})

result = detector.analyze({
    "canvas": {"hash": "abc123def456"},
    "webgl": {"vendor": "Google Inc. (NVIDIA)", "renderer": "ANGLE (NVIDIA, RTX 3060)"},
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
})

print(f"Passed: {result.passed}")
print(f"Risk Score: {result.risk_score}")
for signal in result.signals:
    print(f"  - {signal.name}: {signal.description}")
```

### 3. Test Runner

Automated test execution with comprehensive coverage.

#### Default Test Suite

The default suite includes tests for:
- Valid profiles (should pass)
- Missing fingerprints (should fail)
- Headless browser detection (should fail)
- Bot-like mouse movement (should fail)
- Datacenter IP detection (should fail)
- Country mismatch (should fail)
- Declined cards (should fail)
- 3DS required cards (should fail)

#### Custom Test Suites

```python
from titan.testing import TestRunner, TestSuite, TestCase

suite = TestSuite(
    name="Custom Test Suite",
    description="My custom tests",
)

suite.add_test(TestCase(
    name="my_test",
    description="Test my specific scenario",
    category="custom",
    expected_result="pass",
    test_data={
        "card": {"number": "4111111111111111", "exp_month": "12", "exp_year": "25", "cvv": "123"},
        "fingerprint": {"canvas_hash": "abc123"},
        "behavioral": {"mouse_entropy": 0.8},
    },
))

runner = TestRunner()
summary = runner.run_suite(suite)
print(f"Passed: {summary.passed}/{summary.total_tests}")
```

### 4. Report Generator

Comprehensive failure analysis with remediation recommendations.

#### Report Contents

- **Executive Summary** - Pass/fail counts, success rate
- **Component Health** - Status of each detection component
- **Failure Analysis** - Root cause for each failure
- **Remediation Steps** - How to fix each issue
- **Recommendations** - Prioritized action items
- **Projected Success Rate** - Expected rate after fixes

#### Report Formats

| Format | Use Case |
|--------|----------|
| JSON | Programmatic processing |
| Markdown | Human-readable, version control |
| HTML | Visual dashboard, sharing |

#### Usage

```python
from titan.testing import generate_report

# After running tests
report = generate_report(test_summary, output_dir=Path("/opt/titan/testing/reports"))

# Access report data
print(f"Success Rate: {report.success_rate:.1f}%")
print(f"Projected Rate: {report.projected_success_rate:.1f}%")

# Get markdown
print(report.to_markdown())

# Save all formats
report.save(Path("/opt/titan/testing/reports"), formats=["json", "md", "html"])
```

---

## Test Environment API

### TestEnvironment Class

```python
class TestEnvironment:
    def initialize(self) -> bool
    def run_tests(self, suite: Optional[TestSuite] = None) -> TestReport
    def test_profile(self, profile_data: Dict) -> Dict
    def test_card(self, card_data: Dict, psp: str = "stripe") -> Dict
    def test_fingerprint(self, fingerprint_data: Dict) -> Dict
    def test_behavioral(self, behavioral_data: Dict) -> Dict
    def test_network(self, network_data: Dict) -> Dict
    def get_test_history(self) -> List[Dict]
    def get_success_rate_trend(self) -> List[Dict]
```

### EnvironmentConfig

```python
@dataclass
class EnvironmentConfig:
    enabled_psps: List[str]           # ["stripe", "adyen", "braintree"]
    psp_risk_threshold: int           # 75
    enabled_detectors: List[str]      # ["fingerprint", "behavioral", ...]
    detection_threshold: int          # 70
    output_dir: Path                  # /opt/titan/testing/reports
    report_formats: List[str]         # ["json", "md", "html"]
```

---

## Detection Thresholds

### Risk Score Interpretation

| Score | Level | Action |
|-------|-------|--------|
| 0-29 | LOW | ✅ Safe to proceed |
| 30-59 | MEDIUM | ⚠️ Proceed with caution |
| 60-84 | HIGH | ❌ Likely to fail |
| 85-100 | CRITICAL | ❌ Will definitely fail |

### Component Thresholds

| Component | Default Threshold | Recommended |
|-----------|-------------------|-------------|
| Fingerprint | 70 | 60-75 |
| Behavioral | 70 | 65-80 |
| Network | 70 | 60-75 |
| Device | 70 | 70-80 |
| Velocity | 70 | 75-85 |
| PSP | 75 | 70-80 |

---

## Common Failure Patterns

### Fingerprint Failures

| Signal | Cause | Fix |
|--------|-------|-----|
| `missing_canvas` | No canvas hash | Enable FingerprintInjector |
| `missing_webgl` | No WebGL data | Configure GPU spoofing |
| `headless_browser` | HeadlessChrome detected | Use Camoufox |
| `webdriver_detected` | Automation detected | Use manual operation |
| `vm_detected` | VM GPU detected | Use GPU passthrough |

### Behavioral Failures

| Signal | Cause | Fix |
|--------|-------|-----|
| `low_mouse_entropy` | Bot-like movement | Enable Ghost Motor |
| `fast_form_fill` | Too fast typing | Slow down to 30-60s |
| `no_referrer` | Direct navigation | Use ReferrerWarmup |
| `short_session` | Quick page visit | Spend 45-90s per page |

### Network Failures

| Signal | Cause | Fix |
|--------|-------|-----|
| `datacenter_ip` | Non-residential IP | Use residential proxy |
| `country_mismatch` | IP ≠ billing country | Match proxy to billing |
| `low_ip_reputation` | Blacklisted IP | Use different proxy |
| `vpn_detected` | VPN IP detected | Use residential proxy |

---

## Integration with TITAN Modules

### Testing a Forged Profile

```python
from titan.core import GenesisEngine, ProfileConfig
from titan.testing import create_test_environment

# Forge profile
genesis = GenesisEngine()
profile = genesis.forge_with_integration(
    ProfileConfig(target="amazon_us", persona_name="John Smith", age_days=90),
    billing_address={"city": "New York", "state": "NY", "country": "US"}
)

# Test profile
env = create_test_environment()
result = env.test_profile({
    "profile_id": profile.profile_id,
    "fingerprint": profile.fingerprint_config,
    "behavioral": {"mouse_entropy": 0.75, "time_on_page_seconds": 120},
    "network": {"ip_address": "203.0.113.50", "ip_type": "residential"},
})

if result["overall_passed"]:
    print("Profile ready!")
else:
    print("Fix issues before operation")
```

### Pre-Flight Testing

```python
from titan.core import create_bridge
from titan.testing import create_test_environment

# Create bridge
bridge = create_bridge(
    profile_uuid="titan_abc123",
    billing_address={"city": "New York", "state": "NY", "country": "US"}
)

# Get browser config
config = bridge.get_browser_config()

# Test configuration
env = create_test_environment()
result = env.test_profile({
    "fingerprint": config.fingerprint,
    "network": {"ip_address": config.proxy.ip if config.proxy else ""},
})

# Only proceed if tests pass
if result["overall_passed"]:
    bridge.launch_browser()
```

---

## CLI Reference

### titan-test

```
Usage: titan-test [COMMAND] [OPTIONS]

Commands:
  run              Run the default test suite
  profile FILE     Test a profile from JSON file
  card NUMBER      Quick card validation test
  fingerprint      Test fingerprint configuration
  behavioral       Test behavioral data
  network          Test network configuration
  report           View latest test report
  history          Show test run history

Options:
  --psp NAME       PSP to test against (stripe, adyen, braintree)
  --output DIR     Output directory for reports
  --verbose        Enable verbose output
  --json           Output results as JSON
  -h, --help       Show this help message
```

### Examples

```bash
# Run full test suite
titan-test run

# Test a profile JSON
titan-test profile /opt/titan/profiles/titan_abc123/profile.json

# Test card against Adyen
titan-test card 4111111111111111|12|25|123 --psp adyen

# View latest report
titan-test report

# Show test history
titan-test history
```

---

## Sample Profile JSON

```json
{
  "profile_id": "titan_abc123",
  "fingerprint": {
    "canvas_hash": "a1b2c3d4e5f6789",
    "webgl_vendor": "Google Inc. (NVIDIA)",
    "webgl_renderer": "ANGLE (NVIDIA, GeForce RTX 3060)",
    "audio_hash": "xyz789audio",
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "screen_width": 1920,
    "screen_height": 1080,
    "timezone": "America/New_York",
    "platform": "Win32"
  },
  "behavioral": {
    "mouse_entropy": 0.75,
    "time_on_page_seconds": 120,
    "form_fill_time_seconds": 45,
    "referrer": "https://www.google.com/search?q=amazon",
    "navigation_path": ["google.com", "amazon.com", "product", "cart", "checkout"]
  },
  "network": {
    "ip_address": "203.0.113.50",
    "ip_type": "residential",
    "ip_reputation": 85,
    "ip_country": "US"
  },
  "billing": {
    "city": "New York",
    "state": "NY",
    "postal_code": "10001",
    "country": "US"
  },
  "card": {
    "number": "4111111111111111",
    "exp_month": "12",
    "exp_year": "25",
    "cvv": "123"
  },
  "amount": 99.99
}
```

---

## Troubleshooting

### "Module not found" errors

```bash
# Ensure TITAN is in path
export PYTHONPATH=/opt/titan:$PYTHONPATH

# Or run from TITAN directory
cd /opt/titan
python3 -m testing.environment --run-tests
```

### Reports not generating

```bash
# Create reports directory
mkdir -p /opt/titan/testing/reports
chmod 755 /opt/titan/testing/reports
```

### Tests timing out

```python
# Increase timeout in config
config = EnvironmentConfig(test_timeout_seconds=60.0)
env = TestEnvironment(config)
```

---

*TITAN V6 Testing Environment - Validate Before You Operate*
*Authority: Dva.12 | Version: 6.1.0*
