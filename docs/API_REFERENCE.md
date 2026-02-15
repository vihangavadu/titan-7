# TITAN V7.0 SINGULARITY - API Reference

## Complete Module API Documentation

**Version:** 7.0.2 | **Authority:** Dva.12

---

## Table of Contents

1. [Core Module Exports](#core-module-exports)
2. [GenesisEngine](#genesisengine)
3. [CerberusValidator](#cerberusvalidator)
4. [KYCController](#kyccontroller)
5. [TitanCognitiveCore](#titancognitivecore)
6. [GhostMotorDiffusion](#ghostmotordiffusion)
7. [TitanQUICProxy](#titanquicproxy)
8. [ManualHandoverProtocol](#manualhandoverprotocol)
9. [TitanIntegrationBridge](#titanintegrationbridge)
10. [ResidentialProxyManager](#residentialproxymanager)
11. [FingerprintInjector](#fingerprintinjector)
12. [ReferrerWarmup](#referrerwarmup)
13. [Data Classes](#data-classes)
14. [Enums](#enums)
15. [Convenience Functions](#convenience-functions)

---

## Core Module Exports

```python
from titan.core import (
    # Genesis Engine
    GenesisEngine, ProfileConfig, TargetPreset,
    
    # Cerberus Validator
    CerberusValidator, CardAsset, ValidationResult,
    
    # KYC Controller
    KYCController, ReenactmentConfig, CameraState,
    
    # Cognitive Core
    TitanCognitiveCore, CognitiveRequest, CognitiveResponse,
    
    # Ghost Motor
    GhostMotorDiffusion, TrajectoryConfig, PersonaType,
    
    # QUIC Proxy
    TitanQUICProxy, ProxyConfig, BrowserProfile,
    
    # Handover Protocol
    ManualHandoverProtocol, HandoverPhase, HandoverStatus,
    
    # Integration Bridge
    TitanIntegrationBridge, BridgeConfig, create_bridge,
    
    # Proxy Manager
    ResidentialProxyManager, ProxyEndpoint, GeoTarget,
    
    # Fingerprint Injector
    FingerprintInjector, FingerprintConfig, create_injector,
    
    # Referrer Warmup
    ReferrerWarmup, WarmupPlan, create_warmup_plan, get_warmup_instructions,
)
```

---

## GenesisEngine

Profile forging engine with Pareto-distributed history and trust anchors.

### Class Definition

```python
class GenesisEngine:
    """
    Genesis Engine - Profile Forging with Temporal Displacement
    
    Creates aged browser profiles with:
    - Pareto-distributed browsing history
    - Circadian rhythm weighted visits
    - Pre-aged commerce trust tokens
    - Hardware fingerprint binding
    """
```

### Constructor

```python
GenesisEngine(
    profiles_dir: str = "/opt/titan/profiles"
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `profiles_dir` | `str` | `/opt/titan/profiles` | Directory for profile storage |

### Methods

#### forge_profile

```python
def forge_profile(self, config: ProfileConfig) -> GeneratedProfile
```

Forge a new browser profile with aged history and cookies.

| Parameter | Type | Description |
|-----------|------|-------------|
| `config` | `ProfileConfig` | Profile configuration |

**Returns:** `GeneratedProfile` with profile_id, profile_path, and metadata.

**Example:**
```python
genesis = GenesisEngine()
profile = genesis.forge_profile(ProfileConfig(
    target="amazon_us",
    persona_name="John Smith",
    age_days=90
))
```

#### forge_with_integration

```python
def forge_with_integration(
    self, 
    config: ProfileConfig, 
    billing_address: Optional[Dict] = None
) -> GeneratedProfile
```

Enhanced forging with legacy module integration (location, commerce tokens, fingerprints).

| Parameter | Type | Description |
|-----------|------|-------------|
| `config` | `ProfileConfig` | Profile configuration |
| `billing_address` | `Dict` | Optional billing address for geo alignment |

**Returns:** `GeneratedProfile` with additional integration files.

#### get_available_targets (static)

```python
@staticmethod
def get_available_targets() -> List[TargetPreset]
```

Returns list of available target presets.

#### get_target_by_name (static)

```python
@staticmethod
def get_target_by_name(name: str) -> Optional[TargetPreset]
```

Get specific target preset by name.

---

## CerberusValidator

Zero-touch card validation using merchant APIs.

### Class Definition

```python
class CerberusValidator:
    """
    Cerberus Card Validator - Zero-Touch Validation
    
    Validates cards using SetupIntents without charges.
    Includes BIN database and risk scoring.
    """
```

### Constructor

```python
CerberusValidator(
    keys: Optional[List[MerchantKey]] = None
)
```

### Methods

#### add_key

```python
def add_key(self, key: MerchantKey) -> None
```

Add merchant key to rotation pool.

#### validate (async)

```python
async def validate(self, card: CardAsset) -> ValidationResult
```

Validate a card using zero-touch methods.

| Parameter | Type | Description |
|-----------|------|-------------|
| `card` | `CardAsset` | Card to validate |

**Returns:** `ValidationResult` with status, risk_score, bank_name.

**Example:**
```python
async with CerberusValidator() as validator:
    validator.add_key(MerchantKey(
        provider="stripe",
        secret_key="sk_live_xxx"
    ))
    
    result = await validator.validate(CardAsset(
        number="4111111111111111",
        exp_month="12",
        exp_year="25",
        cvv="123"
    ))
    
    print(f"Status: {result.status}")
```

### Class Attributes

#### HIGH_RISK_BINS

```python
HIGH_RISK_BINS: Set[str]
```

Set of known high-risk BIN prefixes (prepaid, virtual, high-fraud).

#### BIN_DATABASE

```python
BIN_DATABASE: Dict[str, Dict]
```

Database of 80+ BIN entries with bank, country, type, level.

#### COUNTRY_RISK

```python
COUNTRY_RISK: Dict[str, float]
```

Country risk multipliers (1.0 = baseline).

#### LEVEL_TRUST

```python
LEVEL_TRUST: Dict[str, float]
```

Card level trust factors (lower = more trusted).

---

## TitanIntegrationBridge

Unified bridge between V6 core and legacy modules.

### Class Definition

```python
class TitanIntegrationBridge:
    """
    Integration Bridge - Unified V6/Legacy Interface
    
    Connects V6 core with legacy modules for:
    - Pre-flight validation
    - Location spoofing
    - Fingerprint injection
    - Commerce tokens
    - Browser launch configuration
    """
```

### Constructor

```python
TitanIntegrationBridge(config: BridgeConfig)
```

### Methods

#### initialize

```python
def initialize(self) -> bool
```

Initialize all legacy modules. Returns True if successful.

#### run_preflight

```python
def run_preflight(self) -> PreFlightReport
```

Run comprehensive pre-flight validation checks.

**Returns:** `PreFlightReport` with is_ready, checks, abort_reason.

#### align_location_to_billing

```python
def align_location_to_billing(
    self, 
    billing_address: Dict[str, str]
) -> Dict[str, Any]
```

Get Camoufox-compatible location config matching billing address.

#### generate_fingerprint_config

```python
def generate_fingerprint_config(
    self, 
    hardware_profile: str = "us_windows_desktop"
) -> Dict[str, Any]
```

Generate deterministic fingerprint configuration.

#### generate_commerce_tokens

```python
def generate_commerce_tokens(
    self, 
    age_days: int = 60
) -> Dict[str, Dict]
```

Generate pre-aged commerce trust tokens (Stripe, Adyen, PayPal).

#### get_browser_config

```python
def get_browser_config(self) -> BrowserLaunchConfig
```

Get complete browser launch configuration.

#### launch_browser

```python
def launch_browser(
    self, 
    target_url: Optional[str] = None
) -> bool
```

Launch browser with all shields active.

#### full_prepare

```python
def full_prepare(
    self, 
    billing_address: Dict[str, str], 
    target_domain: str
) -> bool
```

Full preparation sequence. Returns True if ready for operation.

**Example:**
```python
bridge = TitanIntegrationBridge(BridgeConfig(
    profile_uuid="titan_abc123",
    billing_address={"city": "New York", "state": "NY", "country": "US"}
))

bridge.initialize()

if bridge.full_prepare(
    billing_address={"city": "New York", "state": "NY", "country": "US"},
    target_domain="amazon.com"
):
    bridge.launch_browser("https://amazon.com")
```

---

## ResidentialProxyManager

Residential proxy pool management with geographic targeting.

### Class Definition

```python
class ResidentialProxyManager:
    """
    Residential Proxy Manager
    
    Features:
    - Geographic targeting (match billing address)
    - Session stickiness (same IP for checkout)
    - Health monitoring and failover
    - Provider integration (Bright Data, Oxylabs, etc.)
    """
```

### Constructor

```python
ResidentialProxyManager(
    provider: str = "custom",
    username: Optional[str] = None,
    password: Optional[str] = None,
    pool_file: Optional[str] = None
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `provider` | `str` | `"custom"` | Provider name or "custom" |
| `username` | `str` | `None` | Provider username |
| `password` | `str` | `None` | Provider password |
| `pool_file` | `str` | `None` | Path to custom pool JSON |

### Methods

#### load_pool

```python
def load_pool(self, pool_file: str) -> None
```

Load proxy pool from JSON file.

#### add_proxy

```python
def add_proxy(self, proxy: ProxyEndpoint) -> None
```

Add single proxy to pool.

#### get_proxy_for_geo

```python
def get_proxy_for_geo(
    self, 
    target: GeoTarget
) -> Optional[ProxyEndpoint]
```

Get proxy matching geographic target.

#### create_session

```python
def create_session(
    self,
    target_domain: str,
    geo_target: GeoTarget,
    duration_minutes: int = 30
) -> Optional[ProxySession]
```

Create sticky proxy session for operation.

#### get_session

```python
def get_session(self, session_id: str) -> Optional[ProxySession]
```

Get existing session by ID.

#### check_proxy_health (async)

```python
async def check_proxy_health(
    self, 
    proxy: ProxyEndpoint
) -> ProxyStatus
```

Check single proxy health.

#### check_all_health (async)

```python
async def check_all_health(self) -> None
```

Check health of all proxies in pool.

#### get_stats

```python
def get_stats(self) -> Dict[str, Any]
```

Get pool statistics.

---

## FingerprintInjector

Deterministic fingerprint generation for canvas, WebGL, and audio.

### Class Definition

```python
class FingerprintInjector:
    """
    Fingerprint Injector - Deterministic Noise Generation
    
    Same profile UUID = Same fingerprint hash
    Critical for fraud detection bypass.
    """
```

### Constructor

```python
FingerprintInjector(config: FingerprintConfig)
```

### Methods

#### generate_canvas_config

```python
def generate_canvas_config(self) -> Dict[str, Any]
```

Generate canvas fingerprint configuration.

#### generate_webgl_config

```python
def generate_webgl_config(self) -> Dict[str, Any]
```

Generate WebGL fingerprint configuration.

#### generate_audio_config

```python
def generate_audio_config(self) -> Dict[str, Any]
```

Generate audio fingerprint configuration.

#### generate_full_config

```python
def generate_full_config(self) -> FingerprintResult
```

Generate complete fingerprint configuration with hashes.

#### get_camoufox_config

```python
def get_camoufox_config(self) -> Dict[str, Any]
```

Get Camoufox-compatible configuration.

#### get_extension_config

```python
def get_extension_config(self) -> Dict[str, Any]
```

Get configuration for browser extension.

#### write_to_profile

```python
def write_to_profile(self, profile_path: Path) -> Path
```

Write fingerprint config to profile directory.

---

## ReferrerWarmup

Organic navigation path creation for valid referrer chains.

### Class Definition

```python
class ReferrerWarmup:
    """
    Referrer Chain Warmup
    
    Creates organic navigation paths:
    Google → Search → Click → Target
    
    Establishes valid document.referrer chain.
    """
```

### Constructor

```python
ReferrerWarmup(humanize_timing: bool = True)
```

### Methods

#### create_warmup_plan

```python
def create_warmup_plan(
    self,
    target_url: str,
    include_pre_warmup: bool = True
) -> WarmupPlan
```

Create navigation plan for target URL.

#### execute_with_playwright

```python
def execute_with_playwright(
    self, 
    plan: WarmupPlan, 
    page
) -> bool
```

Execute plan using Playwright page object.

#### get_manual_instructions

```python
def get_manual_instructions(self, plan: WarmupPlan) -> str
```

Get human-readable navigation instructions.

---

## Data Classes

### ProfileConfig

```python
@dataclass
class ProfileConfig:
    target: str                          # Target preset name
    persona_name: str = "John Doe"       # Persona full name
    persona_email: str = ""              # Persona email
    age_days: int = 90                   # Profile age in days
    browser_type: str = "firefox"        # Browser type
    history_size: int = 150              # Number of history entries
```

### GeneratedProfile

```python
@dataclass
class GeneratedProfile:
    profile_id: str                      # Unique profile ID
    profile_path: Path                   # Path to profile directory
    browser_type: str                    # Browser type
    persona: Dict                        # Persona data
    created_at: datetime                 # Creation timestamp
    age_days: int                        # Profile age
```

### CardAsset

```python
@dataclass
class CardAsset:
    number: str                          # Card number
    exp_month: str                       # Expiration month (MM)
    exp_year: str                        # Expiration year (YY)
    cvv: str                             # CVV/CVC
    holder_name: Optional[str] = None    # Cardholder name
    
    @property
    def bin(self) -> str                 # First 6 digits
    
    @property
    def is_valid_luhn(self) -> bool      # Luhn check result
```

### ValidationResult

```python
@dataclass
class ValidationResult:
    card: CardAsset                      # Validated card
    status: CardStatus                   # LIVE, DEAD, RISKY, UNKNOWN
    message: str                         # Status message
    risk_score: int = 50                 # 0-100 risk score
    bank_name: Optional[str] = None      # Issuing bank
    country: Optional[str] = None        # Card country
    response_code: Optional[str] = None  # Raw response code
```

### BridgeConfig

```python
@dataclass
class BridgeConfig:
    profile_uuid: str                    # Profile UUID
    profile_path: Optional[Path] = None  # Profile directory
    target_domain: Optional[str] = None  # Target domain
    billing_address: Optional[Dict] = None
    proxy_config: Optional[Dict] = None
    browser_type: str = "firefox"
    headless: bool = False
    enable_preflight: bool = True
    enable_fingerprint_noise: bool = True
    enable_commerce_tokens: bool = True
    enable_location_spoof: bool = True
```

### PreFlightReport

```python
@dataclass
class PreFlightReport:
    is_ready: bool = False               # Ready for operation
    checks_passed: int = 0               # Passed check count
    checks_failed: int = 0               # Failed check count
    checks_warned: int = 0               # Warning count
    abort_reason: Optional[str] = None   # Reason if not ready
    details: List[Dict] = field(...)     # Check details
    timestamp: str                       # Report timestamp
```

### ProxyEndpoint

```python
@dataclass
class ProxyEndpoint:
    host: str                            # Proxy host
    port: int                            # Proxy port
    username: Optional[str] = None       # Auth username
    password: Optional[str] = None       # Auth password
    proxy_type: ProxyType = RESIDENTIAL  # Proxy type
    country: str = "US"                  # Country code
    city: Optional[str] = None           # City
    state: Optional[str] = None          # State/province
    
    @property
    def url(self) -> str                 # HTTP proxy URL
    
    @property
    def socks5_url(self) -> str          # SOCKS5 proxy URL
```

### GeoTarget

```python
@dataclass
class GeoTarget:
    country: str                         # Country code
    state: Optional[str] = None          # State/province
    city: Optional[str] = None           # City
    zip_code: Optional[str] = None       # Postal code
    
    @classmethod
    def from_billing_address(cls, address: Dict) -> GeoTarget
```

### FingerprintConfig

```python
@dataclass
class FingerprintConfig:
    profile_uuid: str                    # Profile UUID (seed)
    canvas_enabled: bool = True          # Enable canvas noise
    canvas_noise_level: float = 0.01     # Noise level (1%)
    webgl_enabled: bool = True           # Enable WebGL spoof
    webgl_vendor: str = "..."            # GPU vendor string
    webgl_renderer: str = "..."          # GPU renderer string
    audio_enabled: bool = True           # Enable audio noise
    audio_noise_level: float = 0.0001    # Audio noise level
```

### FingerprintResult

```python
@dataclass
class FingerprintResult:
    canvas_hash: str                     # Canvas fingerprint hash
    webgl_hash: str                      # WebGL fingerprint hash
    audio_hash: str                      # Audio fingerprint hash
    seed: int                            # Generation seed
    config: Dict[str, Any]               # Full configuration
    timestamp: str                       # Generation timestamp
```

### WarmupPlan

```python
@dataclass
class WarmupPlan:
    target_domain: str                   # Target domain
    target_url: str                      # Final destination
    steps: List[WarmupStep]              # Navigation steps
    total_duration: float                # Estimated duration
```

---

## Enums

### CardStatus

```python
class CardStatus(Enum):
    LIVE = "live"           # Card is valid and active
    DEAD = "dead"           # Card is declined/invalid
    RISKY = "risky"         # High-risk BIN detected
    UNKNOWN = "unknown"     # Status could not be determined
```

### ProxyType

```python
class ProxyType(Enum):
    RESIDENTIAL = "residential"
    MOBILE = "mobile"
    DATACENTER = "datacenter"
    ISP = "isp"
```

### ProxyStatus

```python
class ProxyStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DEAD = "dead"
    UNKNOWN = "unknown"
```

### HandoverPhase

```python
class HandoverPhase(Enum):
    GENESIS = "genesis"     # Profile forging phase
    FREEZE = "freeze"       # Automation termination
    HANDOVER = "handover"   # Human operator control
    COMPLETE = "complete"   # Operation finished
```

### HandoverStatus

```python
class HandoverStatus(Enum):
    NOT_READY = "not_ready"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    FAILED = "failed"
```

### PersonaType

```python
class PersonaType(Enum):
    PROFESSIONAL = "professional"  # Precise, efficient movements
    CASUAL = "casual"              # Relaxed, varied movements
    GAMER = "gamer"                # Fast, accurate movements
    ELDERLY = "elderly"            # Slower, less precise
```

---

## Convenience Functions

### create_bridge

```python
def create_bridge(profile_uuid: str, **kwargs) -> TitanIntegrationBridge
```

Create and initialize an integration bridge.

**Example:**
```python
bridge = create_bridge(
    profile_uuid="titan_abc123",
    billing_address={"city": "New York", "country": "US"}
)
```

### create_injector

```python
def create_injector(profile_uuid: str, **kwargs) -> FingerprintInjector
```

Create fingerprint injector for profile.

### create_warmup_plan

```python
def create_warmup_plan(target_url: str) -> WarmupPlan
```

Create warmup navigation plan for target.

### get_warmup_instructions

```python
def get_warmup_instructions(target_url: str) -> str
```

Get manual warmup instructions for operator.

### run_preflight_checks

```python
def run_preflight_checks(profile_path: str) -> Dict[str, Any]
```

Run pre-flight validation on profile.

### quick_handover

```python
def quick_handover(
    profile_path: str, 
    target: str, 
    browser: str = "firefox"
) -> ManualHandoverProtocol
```

Quick handover setup for simple operations.

---

*TITAN V6.0 SOVEREIGN - API Reference*
*Authority: Dva.12 | Version: 6.0.1*
