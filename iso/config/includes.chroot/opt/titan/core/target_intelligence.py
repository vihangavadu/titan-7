"""
TITAN V7.0 SINGULARITY - Target Intelligence Database
PSP, Fraud Engine, and Detection System Intelligence for 200+ targets
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum
import logging

logger = logging.getLogger("TITAN-INTEL")


@dataclass
class AntifraudSystemProfile:
    """Deep profile of an antifraud system for operator decision support"""
    name: str
    vendor: str
    algorithm_class: str
    detection_method: str
    key_signals: List[str] = field(default_factory=list)
    evasion_guidance: List[str] = field(default_factory=list)
    cross_merchant_sharing: bool = False
    behavioral_biometrics: bool = False
    invisible_challenges: bool = False
    session_handover_detection: bool = False


@dataclass
class ProcessorProfile:
    """Payment processor intelligence for operator decision support"""
    name: str
    three_ds_behavior: str
    security_level: str
    operator_guidance: List[str] = field(default_factory=list)
    weak_points: List[str] = field(default_factory=list)


class FraudEngine(Enum):
    FORTER = "forter"
    RISKIFIED = "riskified"
    SIFT = "sift"
    KOUNT = "kount"
    SEON = "seon"
    CYBERSOURCE = "cybersource"
    MAXMIND = "maxmind"
    STRIPE_RADAR = "stripe_radar"
    ACCERTIFY = "accertify"
    CHAINALYSIS = "chainalysis"
    INTERNAL = "internal"
    NONE = "none"


class PaymentGateway(Enum):
    ADYEN = "adyen"
    STRIPE = "stripe"
    PAYPAL = "paypal"
    G2A_PAY = "g2a_pay"
    SKRILL = "skrill"
    HIPAY = "hipay"
    BITPAY = "bitpay"
    INTERNAL = "internal"


class FrictionLevel(Enum):
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class DetectionCountermeasures:
    """Countermeasures for a fraud engine"""
    min_profile_age_days: int = 60
    min_storage_mb: int = 300
    require_social_footprint: bool = False
    require_commerce_history: bool = False
    require_warmup: bool = True
    warmup_minutes: int = 5
    require_residential_proxy: bool = True
    evasion_notes: List[str] = field(default_factory=list)


COUNTERMEASURES: Dict[FraudEngine, DetectionCountermeasures] = {
    FraudEngine.FORTER: DetectionCountermeasures(
        min_profile_age_days=90, min_storage_mb=500,
        require_social_footprint=True, require_commerce_history=True,
        warmup_minutes=10,
        evasion_notes=["Cross-merchant identity graph", "Pre-warm on Forter sites: Nordstrom, Sephora"]
    ),
    FraudEngine.RISKIFIED: DetectionCountermeasures(
        min_profile_age_days=60, min_storage_mb=400,
        require_commerce_history=True, warmup_minutes=5,
        evasion_notes=["Chargeback guarantee = aggressive approvals", "Mobile app often softer"]
    ),
    FraudEngine.SEON: DetectionCountermeasures(
        min_profile_age_days=90, min_storage_mb=400,
        require_social_footprint=True,
        evasion_notes=["Checks social footprint: WhatsApp, LinkedIn, Spotify", "Fresh email = HIGH RISK"]
    ),
    FraudEngine.CYBERSOURCE: DetectionCountermeasures(
        min_profile_age_days=60, min_storage_mb=300,
        evasion_notes=["Visa rules engine", "Blocks VPNs aggressively", "Strict 3DS for EU"]
    ),
    FraudEngine.MAXMIND: DetectionCountermeasures(
        min_profile_age_days=30, min_storage_mb=200,
        require_warmup=False,
        evasion_notes=["Legacy IP reputation", "Easier to bypass"]
    ),
    FraudEngine.STRIPE_RADAR: DetectionCountermeasures(
        min_profile_age_days=45, min_storage_mb=300,
        evasion_notes=["ML across Stripe network", "CAPTCHA common"]
    ),
    FraudEngine.KOUNT: DetectionCountermeasures(
        min_profile_age_days=60, min_storage_mb=350,
        evasion_notes=["Equifax Omniscore", "AVS match important"]
    ),
    FraudEngine.INTERNAL: DetectionCountermeasures(
        min_profile_age_days=30, min_storage_mb=200,
        evasion_notes=["Custom system - varies"]
    ),
}


@dataclass
class TargetIntelligence:
    """Intelligence profile for a target"""
    name: str
    domain: str
    fraud_engine: FraudEngine
    payment_gateway: PaymentGateway
    friction: FrictionLevel
    three_ds_rate: float = 0.25
    mobile_softer: bool = False
    warmup_sites: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    operator_playbook: List[str] = field(default_factory=list)
    post_checkout_options: List[str] = field(default_factory=list)
    warming_guide: List[str] = field(default_factory=list)
    pickup_method: Optional[str] = None
    
    def get_countermeasures(self) -> DetectionCountermeasures:
        return COUNTERMEASURES.get(self.fraud_engine, COUNTERMEASURES[FraudEngine.INTERNAL])
    
    def get_antifraud_profile(self) -> Optional['AntifraudSystemProfile']:
        """Get deep antifraud system profile for operator awareness"""
        return ANTIFRAUD_PROFILES.get(self.fraud_engine.value)
    
    def get_processor_profile(self) -> Optional['ProcessorProfile']:
        """Get payment processor intelligence"""
        return PROCESSOR_PROFILES.get(self.payment_gateway.value)


# ═══════════════════════════════════════════════════════════════════════════
# TARGET DATABASE - 50+ KEY MARKETPLACES
# ═══════════════════════════════════════════════════════════════════════════

TARGETS: Dict[str, TargetIntelligence] = {
    # GREY MARKET - GLOBAL
    "g2a": TargetIntelligence(
        name="G2A", domain="g2a.com",
        fraud_engine=FraudEngine.FORTER, payment_gateway=PaymentGateway.G2A_PAY,
        friction=FrictionLevel.LOW, three_ds_rate=0.15,
        warmup_sites=["nordstrom.com", "sephora.com", "priceline.com"],
        notes=["FORTER identity graph", "Pre-warm on other Forter merchants"]
    ),
    "eneba": TargetIntelligence(
        name="Eneba", domain="eneba.com",
        fraud_engine=FraudEngine.RISKIFIED, payment_gateway=PaymentGateway.ADYEN,
        friction=FrictionLevel.LOW, three_ds_rate=0.15, mobile_softer=True,
        warmup_sites=["greenmangaming.com", "humblebundle.com"],
        notes=["RISKIFIED chargeback guarantee", "Mobile app softer than web"]
    ),
    "kinguin": TargetIntelligence(
        name="Kinguin", domain="kinguin.net",
        fraud_engine=FraudEngine.MAXMIND, payment_gateway=PaymentGateway.PAYPAL,
        friction=FrictionLevel.MEDIUM, three_ds_rate=0.25,
        notes=["MAXMIND legacy", "PayPal backup", "Manual holds common"]
    ),
    "cdkeys": TargetIntelligence(
        name="CDKeys", domain="cdkeys.com",
        fraud_engine=FraudEngine.CYBERSOURCE, payment_gateway=PaymentGateway.STRIPE,
        friction=FrictionLevel.HIGH, three_ds_rate=0.60,
        notes=["CYBERSOURCE Visa", "Blocks VPNs", "Strict 3DS EU"]
    ),
    "gamivo": TargetIntelligence(
        name="Gamivo", domain="gamivo.com",
        fraud_engine=FraudEngine.KOUNT, payment_gateway=PaymentGateway.STRIPE,
        friction=FrictionLevel.MEDIUM, three_ds_rate=0.30,
        notes=["KOUNT Equifax", "Subscription lowers friction"]
    ),
    "instant_gaming": TargetIntelligence(
        name="Instant Gaming", domain="instant-gaming.com",
        fraud_engine=FraudEngine.INTERNAL, payment_gateway=PaymentGateway.HIPAY,
        friction=FrictionLevel.LOW, three_ds_rate=0.20,
        notes=["Internal system", "Lower friction"]
    ),
    "driffle": TargetIntelligence(
        name="Driffle", domain="driffle.com",
        fraud_engine=FraudEngine.STRIPE_RADAR, payment_gateway=PaymentGateway.STRIPE,
        friction=FrictionLevel.LOW, three_ds_rate=0.20,
        notes=["STRIPE RADAR ML"]
    ),
    # AUTHORIZED RETAILERS
    "greenmangaming": TargetIntelligence(
        name="Green Man Gaming", domain="greenmangaming.com",
        fraud_engine=FraudEngine.RISKIFIED, payment_gateway=PaymentGateway.ADYEN,
        friction=FrictionLevel.LOW, three_ds_rate=0.20,
        notes=["RISKIFIED", "Geo-locks keys"]
    ),
    "humble": TargetIntelligence(
        name="Humble Bundle", domain="humblebundle.com",
        fraud_engine=FraudEngine.STRIPE_RADAR, payment_gateway=PaymentGateway.STRIPE,
        friction=FrictionLevel.MEDIUM, three_ds_rate=0.25,
        notes=["STRIPE RADAR", "Steam linking = social KYC"]
    ),
    "fanatical": TargetIntelligence(
        name="Fanatical", domain="fanatical.com",
        fraud_engine=FraudEngine.INTERNAL, payment_gateway=PaymentGateway.ADYEN,
        friction=FrictionLevel.MEDIUM, three_ds_rate=0.30,
        notes=["Blocks VPNs", "UK/EU focused"]
    ),
    # GIFT CARD SECONDARY
    "cardcash": TargetIntelligence(
        name="CardCash", domain="cardcash.com",
        fraud_engine=FraudEngine.INTERNAL, payment_gateway=PaymentGateway.INTERNAL,
        friction=FrictionLevel.HIGH, three_ds_rate=0.50,
        notes=["ID scan required", "24-48h payout delay"]
    ),
    "raise": TargetIntelligence(
        name="Raise", domain="raise.com",
        fraud_engine=FraudEngine.ACCERTIFY, payment_gateway=PaymentGateway.INTERNAL,
        friction=FrictionLevel.MEDIUM, three_ds_rate=0.35,
        notes=["ACCERTIFY AmEx", "Escrow model"]
    ),
    # CRYPTO
    "bitrefill": TargetIntelligence(
        name="Bitrefill", domain="bitrefill.com",
        fraud_engine=FraudEngine.CHAINALYSIS, payment_gateway=PaymentGateway.BITPAY,
        friction=FrictionLevel.VERY_LOW, three_ds_rate=0.0,
        notes=["CHAINALYSIS KYT", "No user KYC", "Clean crypto required"]
    ),
    "coinsbee": TargetIntelligence(
        name="Coinsbee", domain="coinsbee.com",
        fraud_engine=FraudEngine.NONE, payment_gateway=PaymentGateway.BITPAY,
        friction=FrictionLevel.VERY_LOW, three_ds_rate=0.0,
        notes=["50+ cryptos", "No KYC"]
    ),
    # REGIONAL - SEA
    "seagm": TargetIntelligence(
        name="SEAGM", domain="seagm.com",
        fraud_engine=FraudEngine.SEON, payment_gateway=PaymentGateway.INTERNAL,
        friction=FrictionLevel.MEDIUM, three_ds_rate=0.25,
        notes=["SEON social footprint", "Checks WhatsApp/LinkedIn presence"]
    ),
    "offgamers": TargetIntelligence(
        name="OffGamers", domain="offgamers.com",
        fraud_engine=FraudEngine.FORTER, payment_gateway=PaymentGateway.PAYPAL,
        friction=FrictionLevel.LOW, three_ds_rate=0.20,
        notes=["FORTER", "SEA focused"]
    ),
    # REGIONAL - CIS
    "plati": TargetIntelligence(
        name="Plati.market", domain="plati.market",
        fraud_engine=FraudEngine.INTERNAL, payment_gateway=PaymentGateway.INTERNAL,
        friction=FrictionLevel.LOW, three_ds_rate=0.10,
        notes=["WebMoney/Qiwi", "Low friction for locals"]
    ),
    # GAMING PLATFORMS
    "steam": TargetIntelligence(
        name="Steam", domain="store.steampowered.com",
        fraud_engine=FraudEngine.INTERNAL, payment_gateway=PaymentGateway.ADYEN,
        friction=FrictionLevel.MEDIUM, three_ds_rate=0.30,
        notes=["Steam Guard 2FA", "Account age matters"]
    ),
    "playstation": TargetIntelligence(
        name="PlayStation Store", domain="store.playstation.com",
        fraud_engine=FraudEngine.INTERNAL, payment_gateway=PaymentGateway.ADYEN,
        friction=FrictionLevel.MEDIUM, three_ds_rate=0.25,
        notes=["PSN account required"]
    ),
    "xbox": TargetIntelligence(
        name="Xbox Store", domain="xbox.com",
        fraud_engine=FraudEngine.INTERNAL, payment_gateway=PaymentGateway.ADYEN,
        friction=FrictionLevel.MEDIUM, three_ds_rate=0.25,
        notes=["Microsoft account required"]
    ),
    # RETAIL
    "amazon_us": TargetIntelligence(
        name="Amazon US", domain="amazon.com",
        fraud_engine=FraudEngine.INTERNAL, payment_gateway=PaymentGateway.INTERNAL,
        friction=FrictionLevel.MEDIUM, three_ds_rate=0.30,
        notes=["Proprietary fraud system", "Account age critical"]
    ),
    "bestbuy": TargetIntelligence(
        name="Best Buy", domain="bestbuy.com",
        fraud_engine=FraudEngine.INTERNAL, payment_gateway=PaymentGateway.INTERNAL,
        friction=FrictionLevel.HIGH, three_ds_rate=0.40,
        notes=["High-value = more scrutiny", "In-store pickup requires matching ID"],
        operator_playbook=[
            "Use aged Best Buy account or create with clean iPhone + residential proxy",
            "NONVBV card required to bypass 3DS",
            "Browse 10 min, add random items, log out, wait 30 min, come back",
            "Select same-day pickup, use cardholder name for pickup person",
            "Start with lower-value items ($100-200) and scale up",
        ],
        post_checkout_options=[
            "Pickup person MUST match cardholder name on order",
            "Move fast - pickup within 4 hours of order confirmation",
        ],
        warming_guide=["Browse electronics 10 min", "Add items to wishlist", "Wait 30 min before purchase"],
        pickup_method="in_store_pickup",
    ),
    # NEW TARGETS (Source: Digital Goods Marketplace Research + b1stash PDFs)
    "gamesplanet": TargetIntelligence(
        name="Gamesplanet", domain="gamesplanet.com",
        fraud_engine=FraudEngine.INTERNAL, payment_gateway=PaymentGateway.PAYPAL,
        friction=FrictionLevel.LOW, three_ds_rate=0.15,
        notes=["Authorized retailer", "Cross-border payment focus"],
    ),
    "indiegala": TargetIntelligence(
        name="IndieGala", domain="indiegala.com",
        fraud_engine=FraudEngine.INTERNAL, payment_gateway=PaymentGateway.PAYPAL,
        friction=FrictionLevel.LOW, three_ds_rate=0.15,
        notes=["Authorized retailer", "Bundle exploitation possible"],
    ),
    "gamersgate": TargetIntelligence(
        name="GamersGate", domain="gamersgate.com",
        fraud_engine=FraudEngine.INTERNAL, payment_gateway=PaymentGateway.PAYPAL,
        friction=FrictionLevel.LOW, three_ds_rate=0.15,
        notes=["Authorized retailer", "Regional arbitrage"],
    ),
    "dlgamer": TargetIntelligence(
        name="DLGamer", domain="dlgamer.com",
        fraud_engine=FraudEngine.INTERNAL, payment_gateway=PaymentGateway.STRIPE,
        friction=FrictionLevel.LOW, three_ds_rate=0.20,
        notes=["Authorized retailer", "Geo-locking bypass possible"],
    ),
    "gameflip": TargetIntelligence(
        name="Gameflip", domain="gameflip.com",
        fraud_engine=FraudEngine.INTERNAL, payment_gateway=PaymentGateway.INTERNAL,
        friction=FrictionLevel.MEDIUM, three_ds_rate=0.30,
        notes=["Gaming marketplace", "ID verification for sellers", "Escrow system"],
    ),
    "google_ads": TargetIntelligence(
        name="Google Ads", domain="ads.google.com",
        fraud_engine=FraudEngine.INTERNAL, payment_gateway=PaymentGateway.INTERNAL,
        friction=FrictionLevel.HIGH, three_ds_rate=0.50,
        notes=["Minicharge verification", "Bank enrollment may be needed"],
        operator_playbook=[
            "Enroll in cardholder's online banking to view minicharges",
            "Need SSN/birthday for bank enrollment",
            "Fresh first-hand cards have highest success rate",
            "Confirm minicharge amounts via online banking access",
        ],
    ),
    "pinterest_ads": TargetIntelligence(
        name="Pinterest Ads", domain="ads.pinterest.com",
        fraud_engine=FraudEngine.INTERNAL, payment_gateway=PaymentGateway.STRIPE,
        friction=FrictionLevel.MEDIUM, three_ds_rate=0.30,
        notes=["Weaker security than Google/Meta", "Domain bans via rotation"],
        operator_playbook=[
            "Use residential proxies for account setup",
            "High-limit cards especially from Middle Eastern countries work well",
            "Rotate domains to manage bans",
            "Warm up campaigns with small budgets ($20-50/day)",
            "Use cloaking for landing pages",
        ],
    ),
    # NEW V7.0 TARGETS (Source: b1stash PDF analysis Feb 2026)
    "paypal_direct": TargetIntelligence(
        name="PayPal Direct", domain="paypal.com",
        fraud_engine=FraudEngine.INTERNAL, payment_gateway=PaymentGateway.PAYPAL,
        friction=FrictionLevel.HIGH, three_ds_rate=0.60,
        notes=[
            "Most complex payment system - analyzes hundreds of data points per transaction",
            "3-pillar defense: Cookies + Fingerprint + Card history",
            "PayPal cookies on 80%+ of websites as third-party tracking",
            "Network includes Braintree, eBay, Venmo - cross-network intelligence",
            "Fresh session with no PayPal cookies = declined 9/10 times",
        ],
        operator_playbook=[
            "MUST warm up by browsing 20+ popular e-commerce sites first",
            "Visit PayPal.com help pages before logging in (accumulate cookies)",
            "Architecture consistency: cookie browser type must match actual fingerprint",
            "Card MUST be firsthand - never used on PayPal/eBay/Braintree/Venmo",
            "First transaction small ($5-20) to build trust, then scale",
            "Wait 30+ min between warmup and actual transaction",
            "See: get_paypal_defense_intel() for full 3-pillar strategy",
        ],
        warming_guide=[
            "Browse amazon.com, ebay.com, walmart.com, target.com (10 min each)",
            "Visit cnn.com, reddit.com, youtube.com for news/social cookies",
            "Visit facebook.com, linkedin.com for social proof cookies",
            "Browse PayPal.com help/about pages (don't log in yet)",
            "Wait 30+ minutes before actual PayPal login",
        ],
    ),
    "facebook_ads": TargetIntelligence(
        name="Facebook/Meta Ads", domain="business.facebook.com",
        fraud_engine=FraudEngine.INTERNAL, payment_gateway=PaymentGateway.INTERNAL,
        friction=FrictionLevel.HIGH, three_ds_rate=0.50,
        notes=[
            "Minicode verification via Visa Alerts",
            "Account age and activity history critical",
            "Strict device fingerprinting",
            "Cross-platform tracking (Facebook, Instagram, WhatsApp)",
        ],
        operator_playbook=[
            "Enroll card in Visa Alerts for minicode retrieval",
            "Use aged Facebook account (30+ days) with normal activity",
            "Residential proxy matching cardholder location",
            "Start with small daily budgets ($10-20) and scale gradually",
            "Use business manager - don't add card directly to personal account",
        ],
    ),
    "roblox": TargetIntelligence(
        name="Roblox", domain="roblox.com",
        fraud_engine=FraudEngine.INTERNAL, payment_gateway=PaymentGateway.STRIPE,
        friction=FrictionLevel.MEDIUM, three_ds_rate=0.30,
        notes=[
            "Minicode verification possible - use Visa Alerts",
            "Stripe Radar ML behind the scenes",
            "Account age helps lower friction",
        ],
        operator_playbook=[
            "Enroll Visa card in Visa Alerts for transaction monitoring",
            "Use account with some play history (not fresh)",
            "Start with small Robux purchases to build trust",
            "Residential proxy required",
        ],
    ),
    "stockx": TargetIntelligence(
        name="StockX", domain="stockx.com",
        fraud_engine=FraudEngine.FORTER, payment_gateway=PaymentGateway.STRIPE,
        friction=FrictionLevel.HIGH, three_ds_rate=0.45,
        notes=[
            "FORTER cross-merchant identity graph",
            "Strict verification on high-value sneakers/electronics",
            "Seller payouts subject to additional verification",
        ],
        operator_playbook=[
            "Pre-warm on other Forter merchants (Nordstrom, Sephora, Priceline)",
            "Fresh untagged cards only - Forter network flags reused cards",
            "Start with lower-value items ($100-200) before high-value",
            "Profile age 90+ days with commerce history required",
            "Residential proxy with ZIP match to billing address",
        ],
        warmup_sites=["nordstrom.com", "sephora.com", "priceline.com"],
    ),
    "nordstrom": TargetIntelligence(
        name="Nordstrom", domain="nordstrom.com",
        fraud_engine=FraudEngine.FORTER, payment_gateway=PaymentGateway.INTERNAL,
        friction=FrictionLevel.MEDIUM, three_ds_rate=0.30,
        notes=[
            "FORTER protected - part of cross-merchant graph",
            "Good warmup target for other Forter merchants",
            "Gift cards available as lower-friction option",
        ],
        operator_playbook=[
            "Useful as WARMUP for other Forter targets (builds trust edge)",
            "Browse for 10+ minutes before any purchase",
            "Lower-value items ($50-150) have highest success",
        ],
        warmup_sites=["sephora.com", "priceline.com"],
    ),
    "sephora": TargetIntelligence(
        name="Sephora", domain="sephora.com",
        fraud_engine=FraudEngine.FORTER, payment_gateway=PaymentGateway.INTERNAL,
        friction=FrictionLevel.MEDIUM, three_ds_rate=0.25,
        notes=[
            "FORTER protected - part of cross-merchant graph",
            "Good warmup target for other Forter merchants",
            "Beauty products have good resale value",
        ],
        operator_playbook=[
            "Useful as WARMUP for other Forter targets (builds trust edge)",
            "Create account and browse before purchasing",
            "Add items to cart, leave, come back - mimics real shopper",
        ],
        warmup_sites=["nordstrom.com", "priceline.com"],
    ),
    "walmart": TargetIntelligence(
        name="Walmart", domain="walmart.com",
        fraud_engine=FraudEngine.INTERNAL, payment_gateway=PaymentGateway.INTERNAL,
        friction=FrictionLevel.HIGH, three_ds_rate=0.40,
        notes=[
            "Proprietary fraud system - strict AVS enforcement",
            "In-store pickup requires matching ID",
            "Account age and purchase history matter",
        ],
        operator_playbook=[
            "Strict AVS - must have correct billing address",
            "Account with purchase history has lower friction",
            "In-store pickup: ID must match cardholder name",
            "Start with lower-value items to build account trust",
            "Shipping to billing address has highest success rate",
        ],
        pickup_method="in_store_pickup",
    ),
}


def get_target_intel(name: str) -> Optional[TargetIntelligence]:
    """Get intelligence for a target by name"""
    key = name.lower().replace(" ", "_").replace("-", "_")
    return TARGETS.get(key)


def list_targets() -> List[Dict]:
    """List all targets for GUI"""
    return [
        {
            "id": k,
            "name": v.name,
            "domain": v.domain,
            "fraud_engine": v.fraud_engine.value,
            "friction": v.friction.value,
            "3ds_rate": v.three_ds_rate,
        }
        for k, v in TARGETS.items()
    ]


def get_profile_requirements(target_name: str) -> Dict:
    """Get profile generation requirements for a target"""
    intel = get_target_intel(target_name)
    if not intel:
        return {"error": f"Target '{target_name}' not found"}
    
    cm = intel.get_countermeasures()
    
    return {
        "target": intel.name,
        "domain": intel.domain,
        "fraud_engine": intel.fraud_engine.value,
        "payment_gateway": intel.payment_gateway.value,
        "friction_level": intel.friction.value,
        "three_ds_rate": intel.three_ds_rate,
        "mobile_softer": intel.mobile_softer,
        "profile_requirements": {
            "min_age_days": cm.min_profile_age_days,
            "min_storage_mb": cm.min_storage_mb,
            "require_social_footprint": cm.require_social_footprint,
            "require_commerce_history": cm.require_commerce_history,
            "require_warmup": cm.require_warmup,
            "warmup_minutes": cm.warmup_minutes,
            "require_residential_proxy": cm.require_residential_proxy,
        },
        "warmup_sites": intel.warmup_sites,
        "evasion_notes": cm.evasion_notes + intel.notes,
    }


# ═══════════════════════════════════════════════════════════════════════════
# ANTIFRAUD SYSTEM DEEP PROFILES (Source: AI Fraud Detection Research 2025)
# ═══════════════════════════════════════════════════════════════════════════

ANTIFRAUD_PROFILES: Dict[str, AntifraudSystemProfile] = {
    "forter": AntifraudSystemProfile(
        name="Forter", vendor="Forter Inc.",
        algorithm_class="Cross-Merchant Identity Graph",
        detection_method="JS snippet: behavior, device, environment, network, identity, payment, velocity",
        key_signals=[
            "Mouse movements and typing speed", "Browser/OS/WebGL fingerprint",
            "Automation/headless browser flags", "VPN/proxy/WebRTC leak detection",
            "Email cross-ref across 1.2B+ identities", "BIN/AVS/CVV analysis",
            "Cross-merchant velocity patterns",
        ],
        evasion_guidance=[
            "Pre-warm on Forter sites (Nordstrom, Sephora, Priceline) to build trust edges",
            "Fresh untagged cards only - cross-merchant network flags reused cards",
            "Residential proxy mandatory", "Profile age 90+ days with commerce history",
        ],
        cross_merchant_sharing=True, behavioral_biometrics=True,
    ),
    "riskified": AntifraudSystemProfile(
        name="Riskified", vendor="Riskified Ltd.",
        algorithm_class="Chargeback Guarantee + Shadow Linking",
        detection_method="Links accounts via clipboard paste behavior, font config, browsing habits",
        key_signals=[
            "Shadow Linking - clipboard paste of card# creates linkable pattern",
            "Adaptive Checkout - dynamic friction routing",
            "NLP analysis of customer support communications",
        ],
        evasion_guidance=[
            "TYPE card digits manually - NEVER paste from clipboard",
            "Mobile app often has softer scoring than web",
            "Different identity per Riskified merchant",
        ],
        cross_merchant_sharing=True, behavioral_biometrics=True,
    ),
    "seon": AntifraudSystemProfile(
        name="SEON", vendor="SEON Technologies",
        algorithm_class="170+ Parameter Point Scoring (Open System)",
        detection_method="Point-based: TOR=95pts, disposable email=80pts, proxy=20pts, emulator=8pts. Pass<50pts",
        key_signals=[
            "TOR: 95pts", "Disposable email: 80pts", "Web proxy: 20pts",
            "Emulator: 8pts", "Browser spoof: 8pts", "Old browser: 8pts",
            "Disposable phone: 10pts", "No social profiles: 10pts/platform",
            "Bot detected: 12pts",
        ],
        evasion_guidance=[
            "Email MUST have social presence (WhatsApp, LinkedIn, Spotify)",
            "Phone must be real carrier (not VoIP) with online profiles",
            "Residential IP only", "Current browser version required",
            "Target score below 50 points to pass",
        ],
    ),
    "feedzai": AntifraudSystemProfile(
        name="Feedzai", vendor="Feedzai Inc.",
        algorithm_class="Whitebox ML (GBDT + RNN)",
        detection_method="Railgun velocity windows (1h/24h/30d) + Pulse behavioral biometrics",
        key_signals=[
            "Velocity aggregates across sliding time windows",
            "Global Link Analysis ties shared device telemetry",
            "GenAI artifact detection in documents",
        ],
        evasion_guidance=[
            "Avoid smurfing - shared device/subnet links different accounts",
            "Spread transactions across time windows",
            "Don't reuse device fingerprints across accounts",
        ],
        cross_merchant_sharing=True, behavioral_biometrics=True,
    ),
    "featurespace": AntifraudSystemProfile(
        name="Featurespace", vendor="Featurespace Ltd.",
        algorithm_class="Adaptive Deep Behavioral Networks (LSTM/RNN)",
        detection_method="Per-user probability distribution with Anchor + Adaptive dual-state model",
        key_signals=[
            "Deep State vector updated with every interaction",
            "Concept Drift detection if adaptive profile drifts from anchor",
        ],
        evasion_guidance=[
            "Match cardholder archetype closely - deviation flagged",
            "Slow Boil countered by Anchor profile - can't retrain system",
            "Behavioral consistency is key",
        ],
        behavioral_biometrics=True,
    ),
    "biocatch": AntifraudSystemProfile(
        name="BioCatch", vendor="BioCatch Ltd.",
        algorithm_class="Behavioral Biometrics (Physics/Cognitive)",
        detection_method="2000+ behavioral params: accelerometer recoil, mouse entropy, INVISIBLE CHALLENGES",
        key_signals=[
            "Gyroscope recoil correlation on mobile taps",
            "INVISIBLE CHALLENGES: cursor lag injection, displaced DOM elements",
            "Cognitive tells: hesitation before typing familiar data",
            "RAT detection via network latency in mouse stream",
        ],
        evasion_guidance=[
            "Ghost Motor MUST respond to invisible cursor lag challenges",
            "Mobile: inject synthetic gyroscope recoil with every touch",
            "Type familiar data without hesitation",
            "Session must be continuous - no handover gap detectable",
        ],
        behavioral_biometrics=True, invisible_challenges=True, session_handover_detection=True,
    ),
    "datavisor": AntifraudSystemProfile(
        name="DataVisor", vendor="DataVisor Inc.",
        algorithm_class="Unsupervised Clustering (DBSCAN/Spectral)",
        detection_method="Detects coordinated activity via clustering + Knowledge Graphs, Sleeper Cell detection",
        key_signals=[
            "Sleeper Cell detection - correlated account creation patterns",
            "Knowledge Graph links entities across 5000+ accounts",
        ],
        evasion_guidance=[
            "Vary account creation timing, devices, network subnets",
            "Don't create accounts in batches",
            "Avoid shared attributes between accounts",
        ],
    ),
    "sift": AntifraudSystemProfile(
        name="Sift", vendor="Sift Science",
        algorithm_class="Ensemble (RF + DL + NLP) + Global Data Network",
        detection_method="700+ brands, 1T events/year - card on ANY Sift merchant burns across ALL",
        key_signals=[
            "Global Data Network - cross-merchant instant card flagging",
            "Card testing velocity detection",
            "Provisional Risk Score for fresh identities",
        ],
        evasion_guidance=[
            "NEVER test cards on ANY Sift-protected site",
            "Use established email domains, not fresh custom domains",
            "Card testing velocity detected instantly",
        ],
        cross_merchant_sharing=True,
    ),
    "threatmetrix": AntifraudSystemProfile(
        name="ThreatMetrix", vendor="LexisNexis Risk Solutions",
        algorithm_class="Device Fingerprinting + Crypto (SmartID)",
        detection_method="SmartID (Canvas/TCP/Clock Skew) + BehavioSec continuous authentication",
        key_signals=[
            "Canvas hash persists beyond cookie clear",
            "TCP/IP stack detects OS masquerading",
            "BehavioSec detects session handover (human to bot)",
            "Consistency checks find fingerprint paradoxes",
        ],
        evasion_guidance=[
            "Hardware consistency CRITICAL - GPU/fonts/TCP must match OS",
            "eBPF shield must align TTL/Window Size with User-Agent",
            "Ghost Motor must run CONTINUOUSLY from login through checkout",
            "Canvas fingerprint must be deterministic per profile",
        ],
        cross_merchant_sharing=True, behavioral_biometrics=True, session_handover_detection=True,
    ),
    "kount": AntifraudSystemProfile(
        name="Kount", vendor="Equifax (Kount)",
        algorithm_class="Hybrid Scoring (Supervised + Unsupervised = Omniscore)",
        detection_method="Dual ML tracks + Persona linking + Equifax data enrichment",
        key_signals=[
            "Omniscore composite metric", "Persona Technology clusters identities",
            "Card testing velocity detection", "AVS match via Equifax data",
        ],
        evasion_guidance=[
            "Exact AVS match critical (Equifax enrichment)",
            "Space card testing attempts widely",
            "Don't use same IP range for multiple attempts",
        ],
        cross_merchant_sharing=True,
    ),
    "signifyd": AntifraudSystemProfile(
        name="Signifyd", vendor="Signifyd Inc.",
        algorithm_class="Chained Models (Sequential Pipeline)",
        detection_method="Address->Proxy->Risk chain. Fuzzy address matching normalizes jigged addresses.",
        key_signals=[
            "Address jigging detected - variants resolve to same geocode",
            "Reseller abuse detection", "Cross-merchant claim velocity",
        ],
        evasion_guidance=[
            "Address jigging DETECTED - all variations resolve to same lat/long",
            "Avoid bulk buying patterns", "Claim history tracked across network",
        ],
        cross_merchant_sharing=True,
    ),
    "clearsale": AntifraudSystemProfile(
        name="ClearSale", vendor="ClearSale S.A.",
        algorithm_class="Hybrid ML + Human Review (100% Guarantee Model)",
        detection_method="ML pre-scoring + manual analyst review for flagged orders. Cross-store intelligence.",
        key_signals=[
            "Cross-store purchase pattern analysis",
            "Address consistency across merchant network",
            "Device fingerprint + behavioral biometrics combo",
            "Manual analyst review for borderline scores",
        ],
        evasion_guidance=[
            "ClearSale uses human reviewers - must pass visual scrutiny",
            "Order details must look natural (realistic quantities, normal items)",
            "Latin American merchants heavily use ClearSale",
            "Guaranteed approval model means merchants trust ClearSale decisions",
            "Avoid patterns detectable by human review (obvious bulk buying)",
        ],
        cross_merchant_sharing=True, behavioral_biometrics=True,
    ),
    "accertify": AntifraudSystemProfile(
        name="Accertify", vendor="American Express (Accertify)",
        algorithm_class="Device Intelligence + Consortium Data",
        detection_method="Device fingerprinting + transaction consortium across Accertify merchants",
        key_signals=["Device fingerprint persistence", "Consortium data sharing"],
        evasion_guidance=["Use compromised accounts with existing trust", "Avoid clean-room profiles"],
        cross_merchant_sharing=True,
    ),
    "stripe_radar": AntifraudSystemProfile(
        name="Stripe Radar", vendor="Stripe Inc.",
        algorithm_class="Network ML (billions of data points across Stripe)",
        detection_method="ML trained on Stripe's entire payment network, dynamic 3DS triggering",
        key_signals=[
            "Card data shared across millions of Stripe businesses",
            "Dynamic risk-based 3DS", "Behavioral signals + CAPTCHA",
        ],
        evasion_guidance=[
            "Fresh cards essential", "Small merchants may have Radar disabled",
            "Test mode keys sometimes left exposed",
        ],
        cross_merchant_sharing=True,
    ),
}


# ═══════════════════════════════════════════════════════════════════════════
# PAYMENT PROCESSOR PROFILES (Source: b1stash PDF 004)
# ═══════════════════════════════════════════════════════════════════════════

PROCESSOR_PROFILES: Dict[str, ProcessorProfile] = {
    "stripe": ProcessorProfile(
        name="Stripe (Radar)",
        three_ds_behavior="Dynamic risk-based, varies per transaction",
        security_level="HIGH",
        operator_guidance=[
            "Fresh cards essential - Stripe network shares across millions of businesses",
            "Vary IP and fingerprint between attempts",
            "Dynamic 3DS - same card may/may not trigger",
        ],
        weak_points=["Small merchants may disable Radar", "Test mode keys sometimes exposed"],
    ),
    "adyen": ProcessorProfile(
        name="Adyen (RevenueProtect)",
        three_ds_behavior="Strong 3DS enforcement, especially EU cards (PSD2)",
        security_level="HIGH",
        operator_guidance=[
            "Target merchants with optional 3DS settings",
            "EU cards almost always trigger 3DS",
            "US cards have lower 3DS rates on Adyen",
        ],
        weak_points=["Some merchants configure optional 3DS", "Mobile API sometimes softer"],
    ),
    "worldpay": ProcessorProfile(
        name="WorldPay",
        three_ds_behavior="Per-merchant config - security varies widely",
        security_level="VARIABLE",
        operator_guidance=[
            "Find merchants with weak configurations",
            "Some merchants have threshold amounts before 3DS",
        ],
        weak_points=["Per-merchant config = inconsistent security", "Threshold amounts exploitable"],
    ),
    "authorize_net": ProcessorProfile(
        name="Authorize.Net",
        three_ds_behavior="Merchant-controlled - some disable CVV entirely",
        security_level="LOW-VARIABLE",
        operator_guidance=[
            "Merchant controls all security settings",
            "Some merchants disable CVV verification",
        ],
        weak_points=["Merchant-controlled = gaps", "Some don't verify CVV"],
    ),
    "paypal": ProcessorProfile(
        name="PayPal",
        three_ds_behavior="Internal fraud system + buyer protection",
        security_level="MEDIUM",
        operator_guidance=["Account age matters", "PayPal has own internal fraud scoring"],
        weak_points=["Aged PayPal accounts with history have lower friction"],
    ),
    "internal": ProcessorProfile(
        name="Internal/Proprietary",
        three_ds_behavior="Varies by merchant implementation",
        security_level="VARIABLE",
        operator_guidance=["Study target-specific behavior", "Check operator playbook per target"],
        weak_points=["Custom implementations may have gaps"],
    ),
}


# ═══════════════════════════════════════════════════════════════════════════
# OSINT VERIFICATION TOOLS (Source: b1stash PDF 011)
# ═══════════════════════════════════════════════════════════════════════════

OSINT_TOOLS: Dict[str, Dict[str, str]] = {
    "truepeoplesearch": {
        "name": "TruePeopleSearch", "url": "https://www.truepeoplesearch.com",
        "checks": "Name, address, phone, relatives, property ownership",
    },
    "fastpeoplesearch": {
        "name": "FastPeopleSearch", "url": "https://www.fastpeoplesearch.com",
        "checks": "Name, address, phone, email, associates",
    },
    "whitepages": {
        "name": "Whitepages", "url": "https://www.whitepages.com",
        "checks": "Name, address, phone, background checks",
    },
    "thatsthem": {
        "name": "ThatsThem", "url": "https://thatsthem.com",
        "checks": "Name, address, phone, email, IP address lookup",
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# SEON SCORING REFERENCE (Source: b1stash PDF 012)
# Operator uses this to estimate if their setup will pass SEON check
# ═══════════════════════════════════════════════════════════════════════════

SEON_SCORING_RULES: Dict[str, int] = {
    "tor_detected": 95,
    "disposable_email": 80,
    "web_proxy_detected": 20,
    "bot_automation_detected": 12,
    "email_no_social_profiles": 10,
    "email_domain_under_1month": 10,
    "disposable_phone": 10,
    "emulator_detected": 8,
    "browser_spoofing": 8,
    "old_browser_version": 8,
    "phone_no_online_profiles": 4,
}
SEON_PASS_THRESHOLD = 50


def estimate_seon_score(flags: Dict[str, bool]) -> Dict[str, any]:
    """Estimate SEON fraud score based on active flags. Operator decision support."""
    total = 0
    breakdown = []
    for flag, active in flags.items():
        if active and flag in SEON_SCORING_RULES:
            pts = SEON_SCORING_RULES[flag]
            total += pts
            breakdown.append({"flag": flag, "points": pts})
    return {
        "total_score": total,
        "threshold": SEON_PASS_THRESHOLD,
        "would_pass": total < SEON_PASS_THRESHOLD,
        "breakdown": breakdown,
        "guidance": "PASS - proceed" if total < SEON_PASS_THRESHOLD else "FAIL - fix flagged items",
    }


def get_antifraud_profile(engine_name: str) -> Optional[AntifraudSystemProfile]:
    """Get deep antifraud profile by engine name for operator awareness"""
    return ANTIFRAUD_PROFILES.get(engine_name.lower())


def get_processor_profile(processor_name: str) -> Optional[ProcessorProfile]:
    """Get processor intelligence by name"""
    return PROCESSOR_PROFILES.get(processor_name.lower())


def get_osint_tools() -> Dict[str, Dict[str, str]]:
    """Get OSINT verification tools for operator"""
    return OSINT_TOOLS


# ═══════════════════════════════════════════════════════════════════════════
# AVS INTELLIGENCE (Source: b1stash "What is AVS?" Oct 2024)
# Address Verification System codes and Non-AVS country intelligence
# ═══════════════════════════════════════════════════════════════════════════

AVS_RESPONSE_CODES: Dict[str, Dict[str, str]] = {
    "Y": {"match": "Full Match", "description": "Street address AND ZIP code match", "risk": "LOW"},
    "A": {"match": "Partial - Address", "description": "Street address matches, ZIP does not", "risk": "MEDIUM"},
    "Z": {"match": "Partial - ZIP", "description": "ZIP matches, street address does not", "risk": "MEDIUM"},
    "N": {"match": "No Match", "description": "Neither street address nor ZIP match", "risk": "HIGH"},
    "U": {"match": "Not Verified", "description": "Issuer could not verify the information", "risk": "MEDIUM"},
    "R": {"match": "Retry", "description": "System unavailable, retry later", "risk": "UNKNOWN"},
    "S": {"match": "Not Supported", "description": "Issuer does not support AVS", "risk": "LOW"},
    "G": {"match": "Global Non-AVS", "description": "Non-US issuer does not support AVS", "risk": "LOW"},
}

AVS_COUNTRIES: Dict[str, Dict] = {
    "supported": {
        "US": {"level": "full", "notes": "Full AVS - street + ZIP required"},
        "CA": {"level": "full", "notes": "Full AVS support"},
        "GB": {"level": "partial", "notes": "Partial AVS - numeric portions only"},
    },
    "non_avs_advantage": [
        "MX", "BR", "AR", "CO", "CL", "PE", "EC", "VE", "UY", "PY", "BO",
        "CR", "PA", "DO", "GT", "HN", "SV", "NI", "CU", "JM", "TT", "BB",
        "BS", "BZ", "GY", "SR", "HT", "AG", "KN", "LC", "VC", "DM", "GD",
        "DE", "FR", "IT", "ES", "NL", "BE", "AT", "CH", "SE", "NO", "DK",
        "FI", "PL", "CZ", "PT", "GR", "RO", "HU", "BG", "HR", "SK", "SI",
        "IE", "LT", "LV", "EE", "MT", "CY", "LU",
        "JP", "KR", "TW", "SG", "MY", "TH", "PH", "ID", "VN", "IN",
        "AU", "NZ", "ZA", "AE", "SA", "QA", "KW", "BH", "OM",
        "NG", "KE", "GH", "EG", "MA", "TN",
        "TR", "IL", "RU", "UA", "KZ",
    ],
}

AVS_OPERATOR_GUIDANCE = {
    "non_avs_cards": [
        "Cards from non-AVS countries are a significant advantage",
        "Use your OWN drop address for both billing and shipping",
        "Same billing+shipping address lowers risk score (consistent behavior)",
        "No AVS check = one less obstacle, higher success rate",
        "Still subject to other checks: velocity, device, behavioral",
    ],
    "avs_cards": [
        "US/CA/UK cards REQUIRE correct billing address from fullz",
        "Partial matches (ZIP only) may pass on some merchants",
        "Some merchants accept partial AVS - test with small orders first",
        "Use Cerberus checker which includes AVS verification for supported cards",
    ],
    "merchant_behavior": {
        "strict_avs": ["Amazon", "Best Buy", "Walmart", "Target", "Apple"],
        "partial_avs_ok": ["Many digital goods sites", "Subscription services", "Some EU merchants"],
        "no_avs": ["Most crypto exchanges", "International merchants", "Some gaming platforms"],
    },
}


def get_avs_intelligence(card_country: str = "US") -> Dict:
    """Get AVS intelligence for operator decision support"""
    country_upper = card_country.upper()
    is_avs = country_upper in AVS_COUNTRIES["supported"]
    is_non_avs = country_upper in AVS_COUNTRIES["non_avs_advantage"]
    return {
        "country": country_upper,
        "avs_supported": is_avs,
        "non_avs_advantage": is_non_avs,
        "guidance": AVS_OPERATOR_GUIDANCE["avs_cards"] if is_avs else AVS_OPERATOR_GUIDANCE["non_avs_cards"],
        "avs_codes": AVS_RESPONSE_CODES if is_avs else {"note": "AVS not applicable for this country"},
        "strict_merchants": AVS_OPERATOR_GUIDANCE["merchant_behavior"]["strict_avs"] if is_avs else [],
    }


# ═══════════════════════════════════════════════════════════════════════════
# VISA ALERTS INTELLIGENCE (Source: b1stash "Visa Alerts" Oct 2024)
# Visa Purchase Alerts for card monitoring and minicode verification
# ═══════════════════════════════════════════════════════════════════════════

VISA_ALERTS_INTEL: Dict = {
    "enrollment_url": "https://purchasealerts.visa.com/vca-web/check",
    "enrollment_steps": [
        "1. Go to purchasealerts.visa.com/vca-web/check",
        "2. Enter first 9 digits of Visa card to check eligibility",
        "3. If eligible, enter email you control for alert delivery",
        "4. Confirm account as instructed",
        "5. Add full card details (error here = card already dead)",
        "6. Set notifications for ALL charges regardless of amount",
        "7. Monitor email for real-time transaction alerts",
    ],
    "use_cases": [
        "Facebook Ads minicode verification",
        "Google Payments minicode verification",
        "Roblox purchase verification",
        "Real-time decline detection (distinguish card decline vs antifraud block)",
        "Geolocation matching (alerts include transaction location)",
        "Transaction timing intelligence (learn cardholder active hours)",
        "Limit testing (gradually increase amounts, monitor alerts)",
    ],
    "strategies": [
        "Timing: Make purchase immediately after a legitimate transaction to blend in",
        "Limit Testing: Gradually increase amounts, monitor for flags",
        "Real Decline Test: Distinguish between card declines and antifraud blocks",
        "Geo Matching: Use IP matching cardholder location from alert data",
        "Transaction Timing: Transact during cardholder's active hours",
        "Merchant Selection: Choose merchants matching card's spending history",
    ],
    "supported_countries": [
        "US", "AG", "AI", "AR", "AW", "BS", "BB", "BZ", "BM", "BO", "BQ",
        "BR", "VG", "KY", "CL", "CO", "CR", "CW", "DM", "DO", "EC", "SV",
        "GD", "GT", "GY", "HT", "HN", "JM", "MQ", "MX", "MS", "NI", "PA",
        "PY", "PE", "PR", "KN", "LC", "VC", "MF", "SX", "SR", "TT", "TC",
        "UY", "VI",
    ],
    "requirements": [
        "Visa cards ONLY (not Mastercard/Amex)",
        "Card must be from a supported country",
        "Firsthand/fresh cards required for effective use",
        "Cards already used on PayPal network may be flagged",
    ],
}


def get_visa_alerts_intel() -> Dict:
    """Get Visa Alerts intelligence for operator"""
    return VISA_ALERTS_INTEL


def check_visa_alerts_eligible(card_country: str) -> Dict:
    """Check if a card's country supports Visa Alerts"""
    country = card_country.upper()
    eligible = country in VISA_ALERTS_INTEL["supported_countries"]
    return {
        "country": country,
        "visa_alerts_eligible": eligible,
        "enrollment_url": VISA_ALERTS_INTEL["enrollment_url"] if eligible else None,
        "guidance": "Card eligible for Visa Alerts - enroll for real-time monitoring" if eligible
                    else "Card country does not support Visa Alerts",
    }


# ═══════════════════════════════════════════════════════════════════════════
# FINGERPRINT VERIFICATION TOOLS (Source: b1stash "Where to Check" Oct 2024)
# 10 tools for operators to verify their antidetect profile quality
# ═══════════════════════════════════════════════════════════════════════════

FINGERPRINT_CHECK_TOOLS: Dict[str, Dict] = {
    "browserleaks": {
        "name": "BrowserLeaks", "url": "https://browserleaks.com",
        "category": "comprehensive",
        "checks": "WebRTC, Canvas, WebGL, Fonts, JS, CSS, Geolocation, Audio",
        "pros": "Free, tests multiple fingerprinting methods, updated regularly",
        "cons": "Not enough for advanced analysis, lacks specialized antidetect tests",
        "priority": "START_HERE",
    },
    "creepjs": {
        "name": "CreepJS", "url": "https://abrahamjuliot.github.io/creepjs/",
        "category": "advanced",
        "checks": "Deep fingerprint analysis, subtle inconsistencies, lies detection",
        "pros": "Most complete fingerprint analysis available, detects subtle inconsistencies other tools miss",
        "cons": "Complex for beginners, takes longer to analyze",
        "priority": "CRITICAL",
    },
    "fvpro": {
        "name": "Fake Vision Pro", "url": "https://fv.pro",
        "category": "antidetect_specialist",
        "checks": "Antidetect browser profile detection, detailed reports, commercial-grade",
        "pros": "Very accurate, specialized in antidetect profiles, detailed reports",
        "cons": "Paid subscription for full features",
        "priority": "RECOMMENDED",
    },
    "pixelscan": {
        "name": "PixelScan", "url": "https://pixelscan.net",
        "category": "canvas_specialist",
        "checks": "Canvas fingerprinting, browser rendering analysis",
        "pros": "Specializes in canvas fingerprinting, key technique in modern detection",
        "cons": "Narrow focus on canvas only",
        "priority": "RECOMMENDED",
    },
    "amiunique": {
        "name": "AmIUnique", "url": "https://amiunique.org",
        "category": "uniqueness",
        "checks": "Browser uniqueness score, comparison against database",
        "pros": "Easy to use, uniqueness score, user friendly",
        "cons": "Only uniqueness, no antidetect leak detection",
        "priority": "QUICK_CHECK",
    },
    "proxydetect": {
        "name": "Proxydetect.live", "url": "https://proxydetect.live",
        "category": "proxy",
        "checks": "Proxy/VPN/SOCKS detection, real-time analysis",
        "pros": "Real-time proxy detection of HTTP/SOCKS/VPN, detects residential proxies",
        "cons": "Limited to proxy detection only, too sensitive (false positives)",
        "priority": "PROXY_CHECK",
    },
    "dnscheck": {
        "name": "DNSCheck Tools", "url": "https://www.dnscheck.tools/",
        "category": "dns",
        "checks": "DNS fingerprinting, DNS leak detection",
        "pros": "Focused on DNS fingerprinting, detects leaks other tools miss",
        "cons": "Limited scope, DNS only",
        "priority": "DNS_CHECK",
    },
    "panopticlick": {
        "name": "Panopticlick", "url": "https://panopticlick.eff.org/",
        "category": "privacy",
        "checks": "Browser uniqueness, privacy risk assessment",
        "pros": "EFF maintained, privacy focused, clear risk assessment",
        "cons": "Not updated as often, doesn't detect latest techniques",
        "priority": "OPTIONAL",
    },
    "fingerprintjs": {
        "name": "FingerprintJS", "url": "https://fingerprintjs.com/demo/",
        "category": "commercial",
        "checks": "Commercial fingerprinting demo, shows how real antifraud sees you",
        "pros": "Shows how commercial antifraud systems fingerprint you",
        "cons": "Demo version limited, enterprise features require subscription",
        "priority": "AWARENESS",
    },
    "deviceinfo": {
        "name": "DeviceInfo", "url": "https://www.deviceinfo.me/",
        "category": "device",
        "checks": "Hardware, network, browser characteristics",
        "pros": "Shows device and browser info including hardware details",
        "cons": "More informative than analytical, needs interpretation",
        "priority": "OPTIONAL",
    },
}

FINGERPRINT_CHECK_WORKFLOW = [
    "1. Set FvPro or CreepJS as your antidetect browser homepage for automatic checking",
    "2. Start with BrowserLeaks for general overview and fingerprint uniqueness",
    "3. Use Proxydetect.live to verify your proxy isn't flagged",
    "4. Use DNSCheck Tools to verify no DNS leaks",
    "5. Use CreepJS for in-depth analysis of browser resistance to fingerprinting",
    "6. Use PixelScan to verify canvas fingerprint consistency",
    "7. Check profile EVERY TIME you open a new session",
    "8. A unique fingerprint is as bad as a dirty IP - both will get you caught",
]


def get_fingerprint_tools() -> Dict:
    """Get fingerprint verification tools and workflow for operator"""
    return {
        "tools": FINGERPRINT_CHECK_TOOLS,
        "workflow": FINGERPRINT_CHECK_WORKFLOW,
        "critical_tools": ["creepjs", "fvpro", "browserleaks"],
        "proxy_tools": ["proxydetect", "dnscheck"],
    }


# ═══════════════════════════════════════════════════════════════════════════
# CARD PRECHECKING INTELLIGENCE (Source: b1stash "Why Transactions Declined")
# The prechecking paradox and card freshness scoring
# ═══════════════════════════════════════════════════════════════════════════

CARD_PRECHECKING_INTEL: Dict = {
    "the_paradox": (
        "Prechecking cards is counterproductive. Banks detect unusual small transactions "
        "especially ones that don't fit the cardholder's typical buying pattern. "
        "Two unusual transactions in quick succession (precheck + actual purchase) "
        "is a surefire way to get flagged. Less activity before first use = better results."
    ),
    "when_to_check": [
        "Only check cards from secondary/untrusted sellers",
        "NEVER precheck first-party (fresh) cards - trust the source",
        "If you must check, wait at least 24 hours before using the card",
        "Use Cerberus SetupIntent (zero-charge) which is less detectable than $1 auth",
    ],
    "card_tier_intelligence": {
        "platinum_world_business": {
            "tiers": ["Visa Signature", "Visa Infinite", "Mastercard World", "Mastercard World Elite",
                      "Amex Platinum", "Amex Gold", "Chase Sapphire", "Corporate/Business"],
            "advantage": "Higher limits, more flexible with larger transactions, less likely to decline",
            "typical_limit": "$5,000-$50,000+",
            "best_for": "High-value purchases ($500+), electronics, ad platforms",
        },
        "standard_credit": {
            "tiers": ["Visa Classic", "Mastercard Standard", "Discover", "Basic Credit"],
            "advantage": "Common card type, blends in with normal purchases",
            "typical_limit": "$1,000-$5,000",
            "best_for": "Mid-range purchases ($100-$500), digital goods",
        },
        "debit_prepaid": {
            "tiers": ["Visa Debit", "Mastercard Debit", "Prepaid", "Gift Cards"],
            "advantage": "None - highest risk of decline",
            "typical_limit": "$500-$2,000",
            "best_for": "Low-value only, avoid for anything over $100",
            "warning": "Prepaid/gift cards are HIGH RISK BINs in most antifraud systems",
        },
    },
    "freshness_scoring": {
        "pristine": {"description": "First-party, never used, never checked", "score": 100, "guidance": "Best possible card - use immediately"},
        "checked_once": {"description": "Validated via SetupIntent only", "score": 85, "guidance": "Good - minimal footprint from zero-charge check"},
        "multi_checked": {"description": "Checked on multiple services", "score": 40, "guidance": "Risky - multiple auth attempts create pattern"},
        "previously_used": {"description": "Used on another site before", "score": 20, "guidance": "Avoid - transaction history may be flagged"},
        "burned": {"description": "Declined or flagged on any site", "score": 0, "guidance": "DISCARD - card is in fraud databases"},
    },
}


def get_card_prechecking_intel() -> Dict:
    """Get card prechecking intelligence for operator"""
    return CARD_PRECHECKING_INTEL


def estimate_card_freshness(checked: bool = False, times_checked: int = 0,
                            previously_used: bool = False, ever_declined: bool = False) -> Dict:
    """Estimate card freshness score for operator decision support"""
    if ever_declined:
        tier = "burned"
    elif previously_used:
        tier = "previously_used"
    elif times_checked > 1:
        tier = "multi_checked"
    elif checked:
        tier = "checked_once"
    else:
        tier = "pristine"
    info = CARD_PRECHECKING_INTEL["freshness_scoring"][tier]
    return {"freshness_tier": tier, **info}


# ═══════════════════════════════════════════════════════════════════════════
# PROXY & DNS INTELLIGENCE (Source: b1stash "Proxies Explained" Oct 2024)
# ═══════════════════════════════════════════════════════════════════════════

PROXY_INTELLIGENCE: Dict = {
    "type_preference": {
        "1_residential_socks5": {
            "type": "Residential SOCKS5",
            "risk": "LOWEST",
            "notes": "Best option. Real ISP IP + SOCKS handles DNS through proxy (no DNS leak)",
        },
        "2_residential_http": {
            "type": "Residential HTTP/HTTPS",
            "risk": "LOW",
            "notes": "Good but HTTP proxies don't handle DNS - use with VPN layer for DNS protection",
        },
        "3_isp_static": {
            "type": "ISP/Static Residential",
            "risk": "LOW",
            "notes": "Static IPs from ISPs. Consistent for multi-session operations",
        },
        "4_mobile": {
            "type": "Mobile (4G/5G)",
            "risk": "LOW-MEDIUM",
            "notes": "Shared CGNAT IPs - many users per IP. Good for mobile-targeted sites",
        },
        "5_datacenter": {
            "type": "Datacenter",
            "risk": "HIGH",
            "notes": "AVOID for carding. Detected by all modern antifraud systems",
        },
    },
    "dns_leak_prevention": [
        "SOCKS5 proxies handle DNS through the proxy tunnel - preferred over HTTP",
        "HTTP proxies: your DNS queries may leak to your ISP, revealing real location",
        "Always use VPN layer BEFORE connecting to proxy for DNS protection",
        "Set DNS to privacy-respecting server: 9.9.9.9 (Quad9) or 1.1.1.1 (Cloudflare)",
        "Check for DNS leaks at dnscheck.tools or dnsleaktest.com EVERY session",
        "WebRTC leaks can expose real IP even through proxy - must be blocked",
    ],
    "shared_pool_warning": (
        "Some proxy providers have limited IP pools shared by all customers. "
        "The proxy IP you get might already be flagged from other users' activities. "
        "Use premium providers with larger, less-used IP pools. "
        "Check IP reputation at ipqualityscore.com before using."
    ),
    "ip_reputation_check_urls": [
        "https://ipqualityscore.com/",
        "https://scamalytics.com/",
        "https://proxydetect.live/",
        "https://whatismyipaddress.com/blacklist-check",
    ],
}


def get_proxy_intelligence() -> Dict:
    """Get proxy and DNS intelligence for operator"""
    return PROXY_INTELLIGENCE


# ═══════════════════════════════════════════════════════════════════════════
# PAYPAL DEEP DEFENSE INTELLIGENCE (Source: b1stash "PayPal Security" Oct 2024)
# PayPal's 3-pillar defense: Cookies + Fingerprint + Card
# ═══════════════════════════════════════════════════════════════════════════

PAYPAL_DEFENSE_INTEL: Dict = {
    "overview": (
        "PayPal is the most complex payment system. It analyzes hundreds of data points "
        "per transaction in milliseconds. PayPal's third-party cookies exist on 80%+ of all "
        "websites. Every site you visit with PayPal integration builds a behavioral profile."
    ),
    "three_pillars": {
        "cookies": {
            "description": "PayPal's cookie is the cornerstone of its risk assessment",
            "key_facts": [
                "PayPal cookies exist on 80%+ of all websites as third-party tracking",
                "Even legit users get 2FA if they clear cookies despite same device",
                "Fresh browser session with no PayPal cookies = declined 9/10 times",
                "Cookie builds profile of your entire digital behavior before checkout",
            ],
            "evasion": [
                "MUST warm up by browsing 20+ popular e-commerce sites before PayPal login",
                "Visit news portals, social media, shopping sites to accumulate PayPal third-party cookies",
                "Never go directly to checkout with fresh session",
                "Genesis profile should include PayPal cookie accumulation from warmup sites",
            ],
        },
        "fingerprint": {
            "description": "8-point digital fingerprint used to track across sessions",
            "components": [
                "1. User agent string",
                "2. Screen resolution",
                "3. Installed plugins and versions",
                "4. Time zone settings",
                "5. Language preferences",
                "6. Hardware configuration",
                "7. Canvas fingerprinting",
                "8. WebGL fingerprinting",
            ],
            "evasion": [
                "Antidetect browser is mandatory - not optional",
                "Architecture consistency: don't import Brave cookies into Chrome-based antidetect",
                "Browser type in cookies must match actual browser fingerprint",
                "Canvas/WebGL must be deterministic per profile (same seed = same output)",
            ],
        },
        "card": {
            "description": "PayPal checks card history across its entire network",
            "checks": [
                "1. Transaction history on PayPal network",
                "2. Associated identities linked to card",
                "3. Previous sessions linked to card",
                "PayPal network includes: Braintree, eBay, Venmo, and more",
            ],
            "evasion": [
                "Card MUST be fresh/firsthand - never used on PayPal's network before",
                "Cards previously used on eBay, Braintree, or Venmo are likely flagged",
                "Fresh cards with no PayPal network history have highest success",
                "Avoid cards from other sellers - they may have been tested on PayPal",
            ],
        },
    },
    "warming_strategy": [
        "1. Create profile with Genesis (90+ day age, PROFESSIONAL archetype)",
        "2. Browse 20+ popular sites to accumulate PayPal third-party cookies:",
        "   - amazon.com, ebay.com, walmart.com, target.com, bestbuy.com",
        "   - cnn.com, bbc.com, nytimes.com, reddit.com, youtube.com",
        "   - facebook.com, instagram.com, linkedin.com, twitter.com",
        "3. Visit PayPal.com and browse help pages (don't log in yet)",
        "4. Wait 30+ minutes between warming and actual PayPal login",
        "5. Log in and browse account settings before attempting any transaction",
        "6. First transaction should be small ($5-$20) to build trust",
    ],
}


def get_paypal_defense_intel() -> Dict:
    """Get PayPal's 3-pillar defense intelligence for operator"""
    return PAYPAL_DEFENSE_INTEL


if __name__ == "__main__":
    print("TITAN V7.0 Target Intelligence Database")
    print("=" * 60)
    
    for target in list_targets():
        print(f"\n{target['name']} ({target['domain']})")
        print(f"  Fraud Engine: {target['fraud_engine']}")
        print(f"  Friction: {target['friction']}")
        print(f"  3DS Rate: {target['3ds_rate']*100:.0f}%")
    
    print(f"\n\nAntifraud Profiles: {len(ANTIFRAUD_PROFILES)}")
    print(f"Processor Profiles: {len(PROCESSOR_PROFILES)}")
    print(f"OSINT Tools: {len(OSINT_TOOLS)}")
    print(f"Total Targets: {len(TARGETS)}")
