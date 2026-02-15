# Lucid Empire Backend Modules
# Operational modules for behavioral simulation and injection

# Legacy modules - import functions, not classes (for backward compatibility)
try:
    from .commerce_injector import inject_trust_anchors, inject_commerce_vector, inject_commerce_signals
except ImportError:
    pass

try:
    from .biometric_mimicry import BiometricMimicry
except ImportError:
    BiometricMimicry = None

try:
    from .humanization import HumanizationEngine
except ImportError:
    HumanizationEngine = None

# Zero Detect modules (v7.0.0)
from .canvas_noise import (
    CanvasNoiseConfig,
    CanvasNoiseInjector,
    CanvasHashValidator,
    WebGLNoiseConfig,
    WebGLNoiseInjector,
    AudioNoiseConfig,
    AudioNoiseInjector,
    FingerprintNoiseManager
)

from .ghost_motor import (
    TrajectoryConfig,
    GhostMotorGAN,
    GhostMotor,
    KeyboardGenerator,
    ScrollGenerator
)

from .commerce_vault import (
    CommerceVault,
    StripeTokenGenerator,
    AdyenTokenGenerator,
    PayPalTokenGenerator
)

# Firefox Profile Injection (v7.0.0)
from .firefox_injector import (
    FirefoxProfileInjector,
    CookieEntry,
    HistoryEntry,
    FormEntry,
    LocalStorageEntry,
    create_stripe_cookies,
    create_adyen_cookies,
    create_paypal_cookies
)

# Firefox Profile Injector v2.0 - LSNG Edition (Research Guide Implementation)
from .firefox_injector_v2 import (
    FirefoxProfileInjectorV2,
    CookieEntry as CookieEntryV2,
    HistoryEntry as HistoryEntryV2,
    LocalStorageEntry as LocalStorageEntryV2,
    VisitTypeDistribution,
    # Core algorithms
    mozilla_url_hash,
    generate_firefox_guid,
    generate_rev_host,
    to_prtime,
    from_prtime,
    sanitize_origin,
    desanitize_origin,
    compress_value_snappy,
    create_metadata_v2,
    create_commerce_cookies_v2
)

# Location Spoofing Module - Proxy-less geolocation spoofing (v7.0.0-TITAN)
from .location_spoofer import (
    LocationSpoofingEngine,
    BrowserGeolocationSpoofer,
    WindowsLocationSpoofer,
    WiFiBSSIDNullifier,
    TimezoneLocaleAligner,
    LocationProfile,
    GeoCoordinates,
    LOCATION_DATABASE
)

__all__ = [
    # Legacy Commerce
    'inject_trust_anchors', 'inject_commerce_vector', 'inject_commerce_signals',
    'BiometricMimicry',
    'HumanizationEngine',
    
    # Zero Detect - Canvas/WebGL/Audio
    'CanvasNoiseConfig',
    'CanvasNoiseInjector',
    'CanvasHashValidator',
    'WebGLNoiseConfig',
    'WebGLNoiseInjector',
    'AudioNoiseConfig',
    'AudioNoiseInjector',
    'FingerprintNoiseManager',
    
    # Zero Detect - Ghost Motor
    'TrajectoryConfig',
    'GhostMotorGAN',
    'GhostMotor',
    'KeyboardGenerator',
    'ScrollGenerator',
    
    # Zero Detect - Commerce
    'CommerceVault',
    'StripeTokenGenerator',
    'AdyenTokenGenerator',
    'PayPalTokenGenerator',
    
    # Firefox Profile Injection
    'FirefoxProfileInjector',
    'CookieEntry',
    'HistoryEntry',
    'FormEntry',
    'LocalStorageEntry',
    'create_stripe_cookies',
    'create_adyen_cookies',
    'create_paypal_cookies',
    
    # Firefox Profile Injector v2.0 - LSNG
    'FirefoxProfileInjectorV2',
    'CookieEntryV2',
    'HistoryEntryV2',
    'LocalStorageEntryV2',
    'VisitTypeDistribution',
    'mozilla_url_hash',
    'generate_firefox_guid',
    'generate_rev_host',
    'to_prtime',
    'from_prtime',
    'sanitize_origin',
    'desanitize_origin',
    'compress_value_snappy',
    'create_metadata_v2',
    'create_commerce_cookies_v2',
    
    # Location Spoofing Module (Proxy-less)
    'LocationSpoofingEngine',
    'BrowserGeolocationSpoofer',
    'WindowsLocationSpoofer',
    'WiFiBSSIDNullifier',
    'TimezoneLocaleAligner',
    'LocationProfile',
    'GeoCoordinates',
    'LOCATION_DATABASE'
]
