"""
TITAN V7.0 SINGULARITY - 3DS Strategy Module
Provides guidance on 3DS avoidance and handling

3DS (3D Secure) is a major friction point that can block transactions.
This module provides:
1. BIN-level 3DS likelihood scoring
2. Merchant-specific 3DS patterns
3. Avoidance strategies
4. Fallback handling guidance
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum


class ThreeDSLikelihood(Enum):
    """Likelihood of 3DS being triggered"""
    NONE = "none"           # 3DS never triggered
    LOW = "low"             # <20% chance
    MEDIUM = "medium"       # 20-50% chance
    HIGH = "high"           # 50-80% chance
    ALWAYS = "always"       # Always triggers 3DS


class ThreeDSType(Enum):
    """Type of 3DS challenge"""
    SMS_OTP = "sms_otp"
    EMAIL_OTP = "email_otp"
    BANK_APP = "bank_app"
    BIOMETRIC = "biometric"
    PASSWORD = "password"
    UNKNOWN = "unknown"


@dataclass
class ThreeDSProfile:
    """3DS profile for a BIN or merchant"""
    likelihood: ThreeDSLikelihood
    challenge_types: List[ThreeDSType]
    notes: str = ""


# BINs known to have low 3DS rates (US-issued, major banks)
LOW_3DS_BINS = {
    # Chase - Generally low 3DS on US merchants
    '401200', '414720', '421783', '424631',
    # Bank of America - Low 3DS domestically
    '421783', '517805', '486208',
    # Capital One - Moderate 3DS
    '426684', '524897',
    # Wells Fargo - Low 3DS
    '433610', '540443',
    # USAA - Very low 3DS (military bank)
    '453245', '459500',
    # Navy Federal - Very low 3DS
    '459500',
    # Discover - Low 3DS on US merchants
    '601100', '601111', '644000', '650000',
}

# BINs known to have high 3DS rates
HIGH_3DS_BINS = {
    # UK Banks - Almost always 3DS
    '454313', '454742', '465859', '475129', '476250',
    # Revolut/Monzo - Always 3DS
    '492181', '535522',
    # European Banks - High 3DS (PSD2)
    '400115', '410039', '420000', '430000', '440000', '450000',
    # Virtual/Prepaid - Often 3DS
    '414720', '424631', '428837', '431274', '438857',
}

# Merchant-specific 3DS patterns
MERCHANT_3DS_PATTERNS = {
    "amazon.com": ThreeDSProfile(
        likelihood=ThreeDSLikelihood.LOW,
        challenge_types=[ThreeDSType.SMS_OTP],
        notes="Amazon rarely triggers 3DS for established accounts"
    ),
    "bestbuy.com": ThreeDSProfile(
        likelihood=ThreeDSLikelihood.MEDIUM,
        challenge_types=[ThreeDSType.SMS_OTP, ThreeDSType.BANK_APP],
        notes="3DS more common on high-value items >$500"
    ),
    "eneba.com": ThreeDSProfile(
        likelihood=ThreeDSLikelihood.HIGH,
        challenge_types=[ThreeDSType.SMS_OTP, ThreeDSType.BANK_APP],
        notes="Adyen PSP - triggers 3DS on EU cards, less on US"
    ),
    "mygiftcardsupply.com": ThreeDSProfile(
        likelihood=ThreeDSLikelihood.LOW,
        challenge_types=[ThreeDSType.SMS_OTP],
        notes="Stripe PSP - low 3DS on US cards"
    ),
    "dundle.com": ThreeDSProfile(
        likelihood=ThreeDSLikelihood.HIGH,
        challenge_types=[ThreeDSType.SMS_OTP, ThreeDSType.BANK_APP],
        notes="Adyen + Forter - high 3DS on all cards"
    ),
    "shop.app": ThreeDSProfile(
        likelihood=ThreeDSLikelihood.MEDIUM,
        challenge_types=[ThreeDSType.SMS_OTP],
        notes="Shopify Payments - varies by merchant"
    ),
    "steam": ThreeDSProfile(
        likelihood=ThreeDSLikelihood.MEDIUM,
        challenge_types=[ThreeDSType.SMS_OTP, ThreeDSType.BANK_APP],
        notes="3DS common on new accounts, less on aged"
    ),
    "newegg.com": ThreeDSProfile(
        likelihood=ThreeDSLikelihood.LOW,
        challenge_types=[ThreeDSType.SMS_OTP],
        notes="Low 3DS on US cards"
    ),
}


class ThreeDSStrategy:
    """
    Provides 3DS avoidance and handling strategies.
    
    Usage:
        strategy = ThreeDSStrategy()
        
        # Check BIN
        likelihood = strategy.get_bin_likelihood("401200")
        
        # Check merchant
        profile = strategy.get_merchant_profile("amazon.com")
        
        # Get recommendations
        recs = strategy.get_recommendations("401200", "amazon.com", 150.00)
    """
    
    def __init__(self):
        self.low_3ds_bins = LOW_3DS_BINS
        self.high_3ds_bins = HIGH_3DS_BINS
        self.merchant_patterns = MERCHANT_3DS_PATTERNS
    
    def get_bin_likelihood(self, bin_prefix: str) -> ThreeDSLikelihood:
        """Get 3DS likelihood for a BIN"""
        if bin_prefix in self.high_3ds_bins:
            return ThreeDSLikelihood.HIGH
        elif bin_prefix in self.low_3ds_bins:
            return ThreeDSLikelihood.LOW
        else:
            return ThreeDSLikelihood.MEDIUM
    
    def get_merchant_profile(self, domain: str) -> Optional[ThreeDSProfile]:
        """Get 3DS profile for a merchant"""
        # Normalize domain
        domain = domain.lower().replace("www.", "")
        return self.merchant_patterns.get(domain)
    
    def get_recommendations(self, 
                            bin_prefix: str, 
                            merchant_domain: str,
                            amount: float) -> Dict:
        """
        Get 3DS avoidance recommendations.
        
        Args:
            bin_prefix: First 6 digits of card
            merchant_domain: Target merchant domain
            amount: Transaction amount in USD
            
        Returns:
            Dict with recommendations
        """
        bin_likelihood = self.get_bin_likelihood(bin_prefix)
        merchant_profile = self.get_merchant_profile(merchant_domain)
        
        recommendations = {
            "bin_likelihood": bin_likelihood.value,
            "merchant_likelihood": merchant_profile.likelihood.value if merchant_profile else "unknown",
            "overall_risk": "low",
            "strategies": [],
            "warnings": [],
        }
        
        # Calculate overall risk
        if bin_likelihood == ThreeDSLikelihood.HIGH:
            recommendations["overall_risk"] = "high"
            recommendations["warnings"].append("BIN has high 3DS trigger rate")
        elif merchant_profile and merchant_profile.likelihood == ThreeDSLikelihood.HIGH:
            recommendations["overall_risk"] = "high"
            recommendations["warnings"].append("Merchant frequently triggers 3DS")
        elif bin_likelihood == ThreeDSLikelihood.MEDIUM or (merchant_profile and merchant_profile.likelihood == ThreeDSLikelihood.MEDIUM):
            recommendations["overall_risk"] = "medium"
        
        # Amount-based warnings
        if amount > 500:
            recommendations["warnings"].append("High amount increases 3DS likelihood")
            if recommendations["overall_risk"] == "low":
                recommendations["overall_risk"] = "medium"
        
        # Strategy recommendations
        if recommendations["overall_risk"] == "high":
            recommendations["strategies"] = [
                "Consider using a different BIN with lower 3DS rate",
                "Split transaction into smaller amounts if possible",
                "Use aged profile with established purchase history",
                "Ensure billing address matches card exactly",
            ]
        elif recommendations["overall_risk"] == "medium":
            recommendations["strategies"] = [
                "Ensure profile is warmed up on target site",
                "Use residential proxy matching billing address",
                "Keep transaction under $300 if possible",
            ]
        else:
            recommendations["strategies"] = [
                "Proceed with standard protocol",
                "Warmup recommended but not critical",
            ]
        
        # Add merchant-specific notes
        if merchant_profile and merchant_profile.notes:
            recommendations["merchant_notes"] = merchant_profile.notes
        
        return recommendations
    
    def get_best_bins_for_merchant(self, merchant_domain: str) -> List[str]:
        """Get list of BINs with lowest 3DS likelihood for a merchant"""
        merchant_profile = self.get_merchant_profile(merchant_domain)
        
        # If merchant has high 3DS, prioritize lowest 3DS BINs
        if merchant_profile and merchant_profile.likelihood in [ThreeDSLikelihood.HIGH, ThreeDSLikelihood.ALWAYS]:
            return list(self.low_3ds_bins)[:10]
        
        # Otherwise return all low 3DS BINs
        return list(self.low_3ds_bins)
    
    @staticmethod
    def get_3ds_handling_guide(challenge_type: ThreeDSType) -> str:
        """Get handling guide for specific 3DS challenge type"""
        guides = {
            ThreeDSType.SMS_OTP: """
SMS OTP Challenge:
1. Requires access to cardholder's phone number
2. Options:
   - Use virtual number service (TextNow, Google Voice)
   - SIM swap (high risk, not recommended)
   - Social engineering (not recommended)
3. Best strategy: Use BINs that don't trigger SMS OTP
""",
            ThreeDSType.EMAIL_OTP: """
Email OTP Challenge:
1. Requires access to cardholder's email
2. Options:
   - If email is compromised, check inbox
   - Some banks send to alternate email
3. Best strategy: Avoid BINs with email OTP
""",
            ThreeDSType.BANK_APP: """
Bank App Challenge:
1. Requires cardholder's banking app with biometric
2. Cannot be bypassed remotely
3. Best strategy: Avoid BINs that trigger app authentication
""",
            ThreeDSType.BIOMETRIC: """
Biometric Challenge:
1. Requires cardholder's fingerprint or face
2. Cannot be bypassed
3. Best strategy: Use BINs without biometric 3DS
""",
            ThreeDSType.PASSWORD: """
Password Challenge:
1. Requires 3DS password set by cardholder
2. Sometimes can be reset via email
3. Best strategy: Avoid or use cards without 3DS password
""",
        }
        return guides.get(challenge_type, "Unknown challenge type")


# ═══════════════════════════════════════════════════════════════════════════
# VBV TEST BINs (Source: b1stash PDF 013)
# Operator uses these to test if a site enforces 3DS before real attempt
# ═══════════════════════════════════════════════════════════════════════════

VBV_TEST_BINS = {
    "443044": "Known VBV-enrolled test BIN - use to probe site 3DS behavior",
    "510972": "Known VBV-enrolled test BIN - triggers 3DS on compliant sites",
}

# ═══════════════════════════════════════════════════════════════════════════
# 3DS NETWORK SIGNATURES (Source: b1stash PDF 013)
# Operator checks browser DevTools for these indicators
# ═══════════════════════════════════════════════════════════════════════════

THREE_DS_NETWORK_SIGNATURES = {
    "endpoints": [
        "/3ds/authenticate",
        "/3ds2/challenge",
        "/threedsecure",
        "/v1/three-d-secure",
    ],
    "service_domains": [
        "cardinalcommerce.com",
        "arcot.com",
        "3dsecure.io",
        "centinelapistag.cardinalcommerce.com",
        "acs.3dsecure.io",
    ],
    "response_patterns": [
        "enrolled=Y",
        "threeDSMethodURL",
        "acsURL",
        "pareq",
        "creq",
    ],
    "detection_guide": [
        "Open browser DevTools (F12) -> Network tab",
        "Filter by XHR/Fetch requests",
        "Look for requests to endpoints/domains listed above",
        "Check response body for enrolled=Y or threeDSMethodURL",
        "If present, site enforces 3DS for this BIN/amount combo",
    ],
}

# ═══════════════════════════════════════════════════════════════════════════
# AMOUNT THRESHOLDS (Source: b1stash PDFs 004, 009, 013)
# Many sites only trigger 3DS above certain amounts
# ═══════════════════════════════════════════════════════════════════════════

AMOUNT_THRESHOLDS = {
    "bestbuy.com": {"threshold": 500, "notes": "3DS more common above $500"},
    "amazon.com": {"threshold": 1000, "notes": "High-value orders may trigger review"},
    "newegg.com": {"threshold": 750, "notes": "Computer parts above $750 may trigger"},
    "stockx.com": {"threshold": 300, "notes": "Sneakers above $300 more scrutiny"},
    "default": {"threshold": 500, "notes": "General rule: keep under $500 to reduce 3DS"},
}

# ═══════════════════════════════════════════════════════════════════════════
# 3DS TIMEOUT TRICK (Source: b1stash PDF 009)
# ═══════════════════════════════════════════════════════════════════════════

THREE_DS_TIMEOUT_TRICK = {
    "description": "Let the 3DS popup/iframe expire without entering code",
    "mechanism": "Some merchants process payment even if 3DS times out (liability shift back to merchant)",
    "success_rate": "Works on ~15-20% of merchants with optional 3DS",
    "steps": [
        "Proceed to checkout normally",
        "When 3DS popup appears, DO NOT close it",
        "Wait for it to expire/timeout (usually 5-10 minutes)",
        "Check if order was placed anyway",
        "If declined, the card is still clean - try different merchant",
    ],
    "works_best_on": ["Merchants with optional 3DS", "WorldPay merchants", "Low-value transactions"],
}

# ═══════════════════════════════════════════════════════════════════════════
# PROCESSOR-SPECIFIC 3DS BEHAVIOR (Source: b1stash PDF 004)
# ═══════════════════════════════════════════════════════════════════════════

PROCESSOR_3DS_BEHAVIOR = {
    "stripe": {
        "behavior": "Dynamic risk-based 3DS",
        "notes": "Same card may trigger 3DS on one purchase but not another",
        "guidance": "Radar ML decides per-transaction. Low amounts + aged profile = less 3DS",
    },
    "adyen": {
        "behavior": "Strong enforcement, especially EU cards",
        "notes": "RevenueProtect aggressive on EU (PSD2). Look for merchants with optional 3DS",
        "guidance": "US cards have significantly lower 3DS rates on Adyen",
    },
    "worldpay": {
        "behavior": "Per-merchant configuration",
        "notes": "Security varies widely. Some merchants have threshold amounts",
        "guidance": "Find weak configs. 3DS timeout trick works on some WorldPay merchants",
    },
    "authorize_net": {
        "behavior": "Merchant-controlled",
        "notes": "Some merchants disable CVV entirely, rarely enforce 3DS",
        "guidance": "Generally lowest 3DS friction of major processors",
    },
}


def get_3ds_detection_guide() -> Dict:
    """Get complete 3DS detection guide for operator"""
    return {
        "test_bins": VBV_TEST_BINS,
        "network_signatures": THREE_DS_NETWORK_SIGNATURES,
        "amount_thresholds": AMOUNT_THRESHOLDS,
        "timeout_trick": THREE_DS_TIMEOUT_TRICK,
        "processor_behavior": PROCESSOR_3DS_BEHAVIOR,
    }


# ═══════════════════════════════════════════════════════════════════════════
# 3DS 2.0 INTELLIGENCE (Source: b1stash "VBV/MSC/3DS" Oct 2024)
# Who initiates 3DS and what 3DS 2.0 adds
# ═══════════════════════════════════════════════════════════════════════════

THREE_DS_INITIATORS = {
    "bank": {
        "entity": "The Issuing Bank",
        "description": "Bank detects something suspicious and forces 3DS, even if merchant doesn't request it",
        "trigger": "Transaction pattern deviation, geographic anomaly, velocity rules",
        "evasion": "Match cardholder spending patterns. Use residential IP in cardholder's area.",
    },
    "3ds_institution": {
        "entity": "3DS Secure Institution (Cardinal Commerce / Arcot)",
        "description": "Cardinal Commerce can request 3DS on ANY transaction they process",
        "trigger": "Risk scoring by Cardinal's own ML models, independent of merchant/bank",
        "evasion": "Cardinal Commerce is hardest to evade - uses independent risk scoring. Low amounts help.",
    },
    "payment_processor": {
        "entity": "The Payment Processor",
        "description": "Processor auto-requests 3DS if their AI flags suspicious activity",
        "trigger": "Stripe Radar, Adyen RevenueProtect, CyberSource Decision Manager",
        "evasion": "Processor-specific: see PROCESSOR_3DS_BEHAVIOR for per-processor guidance.",
    },
}

THREE_DS_2_INTELLIGENCE = {
    "version": "3DS 2.0 (EMV 3-D Secure)",
    "key_changes": [
        "Uses 150+ data points vs 15 in 3DS 1.0",
        "Frictionless flow: bank can approve without challenge if data looks clean",
        "Risk-based authentication: low-risk = no challenge, high-risk = full challenge",
        "Biometric authentication now possible (fingerprint, facial recognition)",
        "Mobile SDK integration for in-app 3DS",
    ],
    "biometric_threats": {
        "fingerprint_auth": {
            "description": "Some banks now use device biometric (Touch ID / fingerprint) for 3DS",
            "bypass": "Cannot bypass remotely. Avoid BINs from banks that use biometric 3DS.",
            "banks_known": ["Chase (US)", "Barclays (UK)", "HSBC (UK)", "ING (EU)"],
        },
        "facial_recognition": {
            "description": "Emerging: banks using selfie match for 3DS challenge",
            "bypass": "Cannot bypass without KYC module. Avoid these banks entirely.",
            "banks_known": ["Revolut", "N26", "Some Asian banks"],
        },
        "device_biometric": {
            "description": "Bank app requests device biometric (passcode/face/fingerprint) to approve",
            "bypass": "Requires physical access to enrolled device. Not viable for remote operations.",
            "banks_known": ["Most major US/EU banks with mobile banking apps"],
        },
    },
    "frictionless_flow_tips": [
        "3DS 2.0 frictionless flow = bank approves silently based on risk data",
        "To trigger frictionless: match cardholder device, location, spending pattern",
        "Low-value transactions much more likely to get frictionless approval",
        "Aged profiles with consistent behavior data help pass frictionless check",
        "Keep total session data consistent: IP, timezone, locale, browser fingerprint",
    ],
    "non_vbv_strategy": [
        "Focus on cards NOT enrolled in VBV/MSC/3DS programs",
        "Older cards from smaller issuers less likely to be enrolled",
        "Non-US/non-EU cards often have lower 3DS enrollment rates",
        "Test enrollment with VBV test BINs before committing real card",
        "Some merchants allow transactions even if 3DS times out (see timeout trick)",
    ],
}


def get_3ds_v2_intelligence() -> Dict:
    """Get 3DS 2.0 intelligence including biometric threats and initiators"""
    return {
        "initiators": THREE_DS_INITIATORS,
        "v2_intelligence": THREE_DS_2_INTELLIGENCE,
    }


# Export for use in other modules
def get_3ds_strategy() -> ThreeDSStrategy:
    """Get singleton 3DS strategy instance"""
    return ThreeDSStrategy()


# ═══════════════════════════════════════════════════════════════════════════
# V7.0.3: 3DS BYPASS & DOWNGRADE ENGINE
# Comprehensive 3DS attack surface: downgrade, timeout, frictionless abuse,
# amount manipulation, PSP-specific vulnerabilities
# ═══════════════════════════════════════════════════════════════════════════

class ThreeDSBypassType(Enum):
    """Types of 3DS bypass techniques"""
    DOWNGRADE_2_TO_1 = "downgrade_2_to_1"       # Force 3DS 2.0 → 1.0 fallback
    DOWNGRADE_1_TO_NONE = "downgrade_1_to_none"  # Force 3DS 1.0 → no 3DS
    TIMEOUT_EXPLOIT = "timeout_exploit"           # Let 3DS challenge expire
    AMOUNT_SPLIT = "amount_split"                 # Split below threshold
    FRICTIONLESS_ABUSE = "frictionless_abuse"     # Exploit frictionless flow
    BIN_SWITCH = "bin_switch"                     # Use non-enrolled BIN
    RECURRING_FLAG = "recurring_flag"             # Exploit recurring/MIT exemption
    LOW_VALUE_EXEMPT = "low_value_exempt"         # PSD2 low-value exemption (<30 EUR)
    TRA_EXEMPT = "tra_exempt"                     # Transaction Risk Analysis exemption
    MERCHANT_WHITELIST = "merchant_whitelist"     # Trusted beneficiary exemption
    PROTOCOL_MISMATCH = "protocol_mismatch"       # Exploit 3DS version mismatch


@dataclass
class ThreeDSBypassTechnique:
    """A specific 3DS bypass technique with implementation details"""
    bypass_type: ThreeDSBypassType
    name: str
    description: str
    success_rate: float          # 0-1 estimated success rate
    risk_level: str              # low, medium, high
    applicable_psps: List[str]   # Which PSPs this works on
    applicable_versions: List[str]  # 3ds1, 3ds2, both
    implementation: List[str]    # Step-by-step implementation
    detection_risk: str          # How likely to be flagged
    notes: str = ""


# ═══════════════════════════════════════════════════════════════════════════
# 3DS 2.0 → 1.0 DOWNGRADE ATTACK DATABASE
# When a merchant supports both 3DS 2.0 and 1.0, forcing a downgrade to
# 1.0 removes the 150+ data points that 2.0 collects, making bypass easier.
# ═══════════════════════════════════════════════════════════════════════════

THREE_DS_DOWNGRADE_ATTACKS: List[ThreeDSBypassTechnique] = [
    ThreeDSBypassTechnique(
        ThreeDSBypassType.DOWNGRADE_2_TO_1,
        "3DS 2.0 → 1.0 Protocol Downgrade",
        "Many merchants maintain 3DS 1.0 fallback for compatibility. By manipulating "
        "the browser environment to appear incompatible with 3DS 2.0 (blocking the "
        "3DS Method URL iframe, or corrupting the threeDSMethodData), the ACS falls "
        "back to 3DS 1.0 which uses only ~15 data points instead of 150+. "
        "The 1.0 challenge is a simple redirect to bank page — much easier to handle.",
        0.65, "medium",
        ["stripe", "adyen", "worldpay", "checkout_com", "cybersource"],
        ["3ds2"],
        [
            "1. Intercept the /3ds2/init or /v2/authenticate request in DevTools",
            "2. Look for threeDSMethodURL in the response — this is the 3DS 2.0 fingerprint iframe",
            "3. Block the threeDSMethodURL domain in browser (uBlock or nftables rule)",
            "4. The ACS will timeout on 3DS Method collection (10s timeout per spec)",
            "5. Merchant/PSP falls back to 3DS 1.0 challenge (if configured)",
            "6. 3DS 1.0 is a simple redirect — only checks: card enrolled?, OTP correct?",
            "7. If cardholder phone is accessible, OTP can be entered. If not, use timeout trick.",
        ],
        "Low — downgrade looks like a browser compatibility issue",
        notes="Works best on merchants using Cardinal Commerce as 3DS provider. "
              "Cardinal has known fallback behavior when 3DS Method fails."
    ),
    ThreeDSBypassTechnique(
        ThreeDSBypassType.DOWNGRADE_2_TO_1,
        "3DS Method Iframe Corruption",
        "The 3DS 2.0 spec requires the merchant to load a hidden iframe from the ACS "
        "to collect device fingerprint data (threeDSMethodURL). If this iframe returns "
        "an error or the response is corrupted, many ACS implementations fall back to 1.0.",
        0.55, "medium",
        ["stripe", "adyen", "worldpay", "braintree"],
        ["3ds2"],
        [
            "1. When checkout initiates, monitor Network tab for 3DS Method iframe",
            "2. Identify the threeDSMethodURL (e.g., acs.cardinalcommerce.com/...)",
            "3. Use browser extension to inject a Content-Security-Policy header that blocks the ACS domain",
            "4. The iframe fails to load → threeDSCompInd = 'U' (unavailable)",
            "5. ACS receives 'U' and must decide: challenge via 2.0 or fallback to 1.0",
            "6. Many ACS providers fall back to 1.0 when Method data is unavailable",
            "7. Result: simpler authentication with fewer data points analyzed",
        ],
        "Low — CSP blocks are common in corporate environments",
        notes="EMV spec Section 5.3.4: 'If the 3DS Method is not available, "
              "the 3DS Server should set threeDSCompInd to U.'"
    ),
    ThreeDSBypassTechnique(
        ThreeDSBypassType.DOWNGRADE_1_TO_NONE,
        "3DS 1.0 Timeout → No Authentication",
        "When 3DS 1.0 challenge page loads but times out (operator waits without "
        "entering OTP), some merchants process the payment with liability shift "
        "back to themselves rather than declining outright.",
        0.20, "low",
        ["worldpay", "authorize_net", "cybersource"],
        ["3ds1"],
        [
            "1. Proceed through checkout until 3DS 1.0 redirect appears",
            "2. DO NOT close the window — let it sit open",
            "3. Wait for the challenge to timeout (typically 5-15 minutes)",
            "4. The ACS returns AUTHENTICATION_TIMEOUT to the merchant",
            "5. Some merchants have fallback logic: attempt authorization anyway",
            "6. If merchant processes anyway → transaction goes through without 3DS",
            "7. If declined → card is still clean (timeout is not a failed auth)",
        ],
        "Very low — timeout is a normal event",
        notes="~15-20% of merchants with optional 3DS will process on timeout. "
              "WorldPay merchants are most likely to have this behavior."
    ),
    ThreeDSBypassTechnique(
        ThreeDSBypassType.PROTOCOL_MISMATCH,
        "3DS Version Mismatch Exploit",
        "When the card issuer only supports 3DS 1.0 but the merchant only requests "
        "3DS 2.0 (no fallback configured), the authentication cannot complete. "
        "Many merchants will skip 3DS entirely rather than lose the sale.",
        0.40, "low",
        ["stripe", "adyen", "checkout_com"],
        ["both"],
        [
            "1. Use BINs from issuers that only support 3DS 1.0 (older/smaller banks)",
            "2. Target merchants known to ONLY request 3DS 2.0 (no 1.0 fallback)",
            "3. The ACS reports version mismatch — cannot authenticate",
            "4. Merchant receives 'A' (Attempted) or 'U' (Unavailable) status",
            "5. With liability shift ambiguous, many merchants proceed without 3DS",
            "6. Transaction goes through as a standard (non-3DS) transaction",
        ],
        "Very low — version mismatch is a legitimate scenario",
        notes="Stripe Radar: if 3DS is 'attempted' but not completed, Stripe may "
              "still approve based on overall risk score."
    ),
]


# ═══════════════════════════════════════════════════════════════════════════
# PSP-SPECIFIC 3DS VULNERABILITIES
# How each PSP handles 3DS failures, timeouts, and edge cases
# ═══════════════════════════════════════════════════════════════════════════

PSP_3DS_VULNERABILITIES = {
    "stripe": {
        "3ds_version": "2.0 primary, 1.0 fallback",
        "downgrade_possible": True,
        "downgrade_method": "Block threeDSMethodURL → falls back to 1.0 → Radar risk-based decision",
        "timeout_behavior": "Radar decides: if overall risk is low, may approve without 3DS completion",
        "frictionless_exploitable": True,
        "frictionless_method": "Aged profile + low amount + matching geo = high frictionless approval rate",
        "amount_threshold": "Dynamic — Radar ML decides per-transaction. No fixed threshold.",
        "recurring_exempt": True,
        "recurring_method": "First transaction authenticated → subsequent MIT flagged as recurring → no 3DS",
        "weak_points": [
            "Radar trusts aged sessions with consistent fingerprints",
            "Low amounts ($5-20) almost never trigger 3DS on Stripe",
            "If 3DS Method iframe fails, falls back to 1.0 silently",
            "Merchant can set payment_intent.setup_future_usage = 'off_session' to skip 3DS on repeats",
        ],
    },
    "adyen": {
        "3ds_version": "2.0 enforced (EU PSD2), 1.0 fallback for non-EU",
        "downgrade_possible": True,
        "downgrade_method": "Non-EU cards: corrupt threeDSMethodData → 1.0 fallback. EU cards: PSD2 exemption route.",
        "timeout_behavior": "Strict — usually declines on timeout. Some merchants have soft decline → retry without 3DS.",
        "frictionless_exploitable": True,
        "frictionless_method": "Adyen RevenueProtect risk score: low risk → frictionless. Match cardholder profile exactly.",
        "amount_threshold": "EU: mandatory >30 EUR (PSD2). Non-EU: merchant config. US cards rarely trigger.",
        "recurring_exempt": True,
        "recurring_method": "storedPaymentMethodId + shopperInteraction=ContAuth → MIT exemption",
        "weak_points": [
            "US/CA/AU cards on EU Adyen merchants: much lower 3DS rate than EU cards",
            "PSD2 exemptions: TRA (Transaction Risk Analysis) for low-risk under 500 EUR",
            "Adyen's 'soft decline' feature: some merchants retry without 3DS after decline",
            "Amount splitting below 30 EUR triggers low-value exemption in EU",
        ],
    },
    "worldpay": {
        "3ds_version": "Mixed — many merchants still on 1.0",
        "downgrade_possible": True,
        "downgrade_method": "Many WorldPay merchants haven't upgraded to 2.0 — already on 1.0 or no 3DS.",
        "timeout_behavior": "MOST EXPLOITABLE: ~25% of WorldPay merchants process on timeout",
        "frictionless_exploitable": False,
        "frictionless_method": "WorldPay 3DS 2.0 adoption is low — most still use 1.0 or none.",
        "amount_threshold": "Per-merchant config. Many have no threshold (3DS on all or none).",
        "recurring_exempt": True,
        "recurring_method": "Standard MIT exemption supported.",
        "weak_points": [
            "Highest timeout success rate among major PSPs (~25%)",
            "Many merchants still on 3DS 1.0 — simple OTP or none",
            "Per-merchant configuration means wide variance in security",
            "Some merchants disable 3DS entirely for certain card types",
        ],
    },
    "authorize_net": {
        "3ds_version": "1.0 primarily, 2.0 optional",
        "downgrade_possible": False,
        "downgrade_method": "Already on 1.0 — no downgrade needed.",
        "timeout_behavior": "Permissive — many merchants process without completed 3DS",
        "frictionless_exploitable": False,
        "frictionless_method": "No native frictionless flow in 1.0.",
        "amount_threshold": "Merchant-controlled. Many don't enforce any 3DS.",
        "recurring_exempt": True,
        "recurring_method": "CIM (Customer Information Manager) stored cards skip 3DS.",
        "weak_points": [
            "LOWEST 3DS FRICTION of all major PSPs",
            "Many Auth.net merchants don't enforce 3DS at all",
            "1.0 only — no advanced device fingerprinting",
            "CVV-only validation on many merchants (no AVS, no 3DS)",
        ],
    },
    "braintree": {
        "3ds_version": "2.0 primary, 1.0 fallback",
        "downgrade_possible": True,
        "downgrade_method": "Drop connection to braintree-api during 3DS handshake → merchant retry without 3DS",
        "timeout_behavior": "Moderate — PayPal backend may retry as non-3DS if initial attempt times out",
        "frictionless_exploitable": True,
        "frictionless_method": "Kount risk scoring (Braintree default) — low score = frictionless",
        "amount_threshold": "Dynamic via Kount. Generally more permissive than Stripe/Adyen.",
        "recurring_exempt": True,
        "recurring_method": "Vault stored payment methods get MIT exemption.",
        "weak_points": [
            "Braintree → PayPal backend: PayPal's fraud scoring is separate from bank 3DS",
            "Fallback from 2.0 to 1.0 is automatic on many Braintree integrations",
            "Low amounts on food delivery (Uber, Grubhub) almost never trigger 3DS",
            "Vaulted cards (stored) skip 3DS on repeat transactions",
        ],
    },
    "shopify_payments": {
        "3ds_version": "2.0 (Stripe-powered)",
        "downgrade_possible": True,
        "downgrade_method": "Same as Stripe — block threeDSMethodURL → 1.0 fallback via Stripe Radar.",
        "timeout_behavior": "Stripe Radar-dependent — low-risk may approve on timeout",
        "frictionless_exploitable": True,
        "frictionless_method": "Shopify stores inherit Stripe's frictionless flow. Aged profile + low amount = frictionless.",
        "amount_threshold": "Most Shopify stores: no 3DS under $50. Stripe Radar makes per-transaction decision.",
        "recurring_exempt": False,
        "recurring_method": "Shopify subscriptions use Stripe recurring — MIT exemption on renewals.",
        "weak_points": [
            "MOST SHOPIFY STORES HAVE NO CUSTOM FRAUD RULES — default Stripe Radar only",
            "No Forter/Riskified/Sift on most Shopify stores (only Shopify Plus merchants add these)",
            "US cards on Shopify stores: <10% 3DS trigger rate",
            "Small stores (<$1M revenue) almost never see 3DS challenges",
            "Shopify's built-in fraud analysis is basic compared to enterprise antifraud",
        ],
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# PSD2 EXEMPTION EXPLOITATION (EU-specific)
# ═══════════════════════════════════════════════════════════════════════════

PSD2_EXEMPTIONS = {
    "low_value": {
        "threshold": 30.00,     # EUR
        "description": "Transactions under 30 EUR are exempt from SCA (Strong Customer Authentication)",
        "limitation": "Cumulative limit: 5 consecutive exempt transactions OR 100 EUR total, then SCA required",
        "exploit": [
            "Keep individual transactions under 30 EUR",
            "Use different merchants to avoid cumulative tracking",
            "After 5 exempt transactions, switch to non-EU BIN or different card",
            "Digital goods under 30 EUR almost always skip 3DS in EU",
        ],
        "best_targets": ["Spotify (9.99 EUR)", "Netflix (7.99 EUR)", "Game keys <30 EUR"],
    },
    "tra_exemption": {
        "threshold": 500.00,    # EUR (PSP must have <0.13% fraud rate)
        "description": "Transaction Risk Analysis — PSP can exempt if their fraud rate is below threshold",
        "limitation": "PSP fraud rate requirements: <0.13% for up to 100 EUR, <0.06% for up to 250 EUR, <0.01% for up to 500 EUR",
        "exploit": [
            "Target merchants using Stripe/Adyen — they qualify for TRA exemptions",
            "Low-risk profile (aged, consistent behavior) = PSP more likely to request TRA exemption",
            "Transactions 30-100 EUR: most PSPs with good fraud rates will exempt",
            "Transactions 100-250 EUR: Stripe and Adyen qualify but may not always request",
        ],
        "best_targets": ["Stripe merchants under 100 EUR", "Adyen merchants under 250 EUR"],
    },
    "recurring_mit": {
        "threshold": None,      # No amount limit
        "description": "Merchant Initiated Transactions (recurring payments) are exempt from SCA after first authenticated payment",
        "limitation": "First transaction MUST be authenticated. Subsequent recurring charges skip SCA.",
        "exploit": [
            "Subscribe to a service with authenticated first payment",
            "Change subscription amount/plan after enrollment",
            "Merchant charges recurring amount without SCA",
            "Works on: subscription boxes, streaming, SaaS, recurring donations",
        ],
        "best_targets": ["Subscription services", "SaaS platforms", "Streaming services"],
    },
    "trusted_beneficiary": {
        "threshold": None,
        "description": "Cardholder can whitelist a merchant as 'trusted' — future transactions skip SCA",
        "limitation": "Requires initial SCA-authenticated transaction. Cardholder must explicitly whitelist.",
        "exploit": [
            "If cardholder's bank app is accessible: whitelist target merchant",
            "Future transactions to that merchant skip 3DS entirely",
            "Works with most EU banks that support PSD2 whitelisting",
        ],
        "best_targets": ["Any merchant — once whitelisted, unlimited SCA-free transactions"],
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# 3DS BYPASS SCORING ENGINE
# Scores a site for 3DS bypass potential based on PSP, config, behavior
# ═══════════════════════════════════════════════════════════════════════════

class ThreeDSBypassEngine:
    """
    Analyzes a merchant site's 3DS configuration and returns:
    - Overall bypass score (0-100)
    - Applicable bypass techniques with success rates
    - Recommended approach for maximum success
    
    Usage:
        engine = ThreeDSBypassEngine()
        
        # Score a site
        result = engine.score_site("g2a.com", psp="adyen", three_ds="conditional")
        
        # Get bypass plan
        plan = engine.get_bypass_plan("shopify-store.com", psp="shopify_payments",
                                       card_country="US", amount=150)
        
        # Get all downgradeable sites
        downgradeable = engine.get_downgradeable_sites(sites_list)
    """
    
    def score_site(self, domain: str, psp: str = "unknown",
                   three_ds: str = "unknown", fraud_engine: str = "none",
                   is_shopify: bool = False, amount: float = 200,
                   card_country: str = "US") -> Dict:
        """
        Score a site's 3DS bypass potential (0-100).
        
        Higher score = easier to bypass 3DS.
        """
        score = 50  # Base score
        techniques = []
        warnings = []
        
        # ─── PSP-based scoring ───
        psp_lower = psp.lower() if psp else "unknown"
        psp_info = PSP_3DS_VULNERABILITIES.get(psp_lower, {})
        
        if psp_lower == "authorize_net":
            score += 30
            techniques.append("Auth.net: lowest 3DS friction, many merchants skip 3DS entirely")
        elif psp_lower == "worldpay":
            score += 20
            techniques.append("WorldPay: 25% timeout success rate, many on 3DS 1.0 only")
        elif psp_lower == "shopify_payments":
            score += 20
            techniques.append("Shopify: default Stripe Radar only, no custom fraud rules on most stores")
        elif psp_lower == "stripe":
            score += 15
            techniques.append("Stripe: Radar risk-based, low amounts rarely trigger, downgrade possible")
        elif psp_lower == "braintree":
            score += 15
            techniques.append("Braintree: PayPal backend, auto-fallback 2.0→1.0, permissive on low amounts")
        elif psp_lower == "adyen":
            score += 5
            techniques.append("Adyen: strict on EU cards, but US/CA/AU cards rarely trigger 3DS")
        elif psp_lower == "cybersource":
            score -= 5
            techniques.append("CyberSource: Decision Manager is aggressive, higher friction")
        
        # ─── 3DS status scoring ───
        if three_ds == "none":
            score += 25
            techniques.append("NO 3DS: Site does not enforce 3DS → pure 2D transaction")
        elif three_ds == "conditional":
            score += 10
            techniques.append("Conditional 3DS: amount/BIN/risk dependent — bypass via threshold manipulation")
        elif three_ds == "always":
            score -= 20
            techniques.append("Always 3DS: must use downgrade or timeout technique")
        
        # ─── Fraud engine scoring ───
        if fraud_engine in ("none", "basic", "unknown"):
            score += 15
            techniques.append("No advanced antifraud — basic checks only")
        elif fraud_engine == "seon":
            score += 5
            techniques.append("SEON: moderate antifraud, bypassable with clean fingerprint")
        elif fraud_engine in ("forter", "riskified"):
            score -= 15
            techniques.append(f"{fraud_engine.title()}: enterprise antifraud — profile warmup critical")
            warnings.append(f"⚠ {fraud_engine.title()} detected — high friction")
        elif fraud_engine == "sift":
            score -= 10
            techniques.append("Sift: behavioral analysis — Ghost Motor augmentation critical")
        
        # ─── Shopify bonus ───
        if is_shopify:
            score += 10
            techniques.append("Shopify store: typically no custom fraud rules, default Radar only")
        
        # ─── Card country scoring ───
        if card_country == "US":
            score += 10
            techniques.append("US card: lowest global 3DS trigger rate (~15%)")
        elif card_country in ("CA", "AU"):
            score += 5
            techniques.append(f"{card_country} card: low 3DS rate (~20%)")
        elif card_country in ("GB", "DE", "FR"):
            score -= 5
            techniques.append(f"{card_country} card: PSD2 enforced — use low-value exemption <30 EUR")
        
        # ─── Amount scoring ───
        if amount <= 30:
            score += 15
            techniques.append("Under $30: PSD2 exempt (EU) + Stripe Radar almost never triggers")
        elif amount <= 100:
            score += 5
            techniques.append("Under $100: TRA exemption likely (EU) + low Radar risk")
        elif amount > 500:
            score -= 10
            warnings.append("⚠ High amount increases 3DS probability")
        
        # ─── Downgrade possible? ───
        if psp_info.get("downgrade_possible"):
            score += 5
            techniques.append(f"3DS 2.0→1.0 downgrade possible on {psp_lower}")
        
        # ─── Frictionless exploitable? ───
        if psp_info.get("frictionless_exploitable"):
            score += 5
            techniques.append(f"Frictionless flow exploitable on {psp_lower} — aged profile helps")
        
        # Clamp score
        score = max(0, min(100, score))
        
        # Determine bypass level
        if score >= 80:
            bypass_level = "EASY"
            bypass_color = "green"
        elif score >= 60:
            bypass_level = "MODERATE"
            bypass_color = "yellow"
        elif score >= 40:
            bypass_level = "HARD"
            bypass_color = "orange"
        else:
            bypass_level = "VERY HARD"
            bypass_color = "red"
        
        return {
            "domain": domain,
            "bypass_score": score,
            "bypass_level": bypass_level,
            "bypass_color": bypass_color,
            "techniques": techniques,
            "warnings": warnings,
            "psp": psp_lower,
            "psp_vulnerabilities": psp_info.get("weak_points", []),
            "downgrade_possible": psp_info.get("downgrade_possible", False),
            "frictionless_exploitable": psp_info.get("frictionless_exploitable", False),
            "timeout_behavior": psp_info.get("timeout_behavior", "unknown"),
        }
    
    def get_bypass_plan(self, domain: str, psp: str, three_ds: str = "conditional",
                        card_country: str = "US", amount: float = 200,
                        fraud_engine: str = "none") -> Dict:
        """
        Generate a step-by-step 3DS bypass plan for a specific site + card.
        """
        score_result = self.score_site(domain, psp, three_ds, fraud_engine,
                                        False, amount, card_country)
        psp_lower = psp.lower()
        psp_info = PSP_3DS_VULNERABILITIES.get(psp_lower, {})
        
        steps = []
        
        # Step 1: Pre-check
        steps.append({
            "step": 1,
            "action": "PRE-CHECK",
            "detail": f"Verify card BIN is in LOW_3DS_BINS. Check if {domain} currently enforces 3DS "
                      f"by attempting a $1 test charge or checking DevTools for 3DS endpoints.",
        })
        
        # Step 2: Amount optimization
        if three_ds == "conditional":
            threshold = AMOUNT_THRESHOLDS.get(domain, AMOUNT_THRESHOLDS["default"])
            steps.append({
                "step": 2,
                "action": "AMOUNT OPTIMIZATION",
                "detail": f"Stay under ${threshold['threshold']} to reduce 3DS probability. "
                          f"({threshold['notes']}). If total needed is higher, split into multiple orders.",
            })
        
        # Step 3: Frictionless flow preparation
        if psp_info.get("frictionless_exploitable"):
            steps.append({
                "step": 3,
                "action": "FRICTIONLESS FLOW PREP",
                "detail": f"Maximize frictionless approval chance: "
                          f"{psp_info.get('frictionless_method', 'Use aged profile with matching geo.')} "
                          f"Ensure IP geo matches billing address. Use aged profile (>30 days).",
            })
        
        # Step 4: Downgrade attempt
        if psp_info.get("downgrade_possible") and three_ds != "none":
            steps.append({
                "step": 4,
                "action": "3DS DOWNGRADE (2.0 → 1.0)",
                "detail": f"Method: {psp_info.get('downgrade_method', 'Block threeDSMethodURL to force 1.0 fallback.')} "
                          f"In browser DevTools, block requests to cardinalcommerce.com or acs.*.com domains.",
            })
        
        # Step 5: Timeout exploitation
        if three_ds != "none":
            steps.append({
                "step": 5,
                "action": "TIMEOUT FALLBACK",
                "detail": f"If 3DS challenge appears: {psp_info.get('timeout_behavior', 'let it timeout and check if order processes.')} "
                          f"Wait 5-15 minutes without entering OTP. Card remains clean if timeout.",
            })
        
        # Step 6: EU-specific exemptions
        if card_country in ("GB", "DE", "FR", "ES", "IT", "NL", "BE", "AT", "IE", "PT"):
            if amount <= 30:
                steps.append({
                    "step": 6,
                    "action": "PSD2 LOW-VALUE EXEMPTION",
                    "detail": "Transaction under 30 EUR — qualifies for automatic low-value exemption. "
                              "3DS should be skipped automatically. Max 5 consecutive or 100 EUR cumulative.",
                })
            elif amount <= 500:
                steps.append({
                    "step": 6,
                    "action": "PSD2 TRA EXEMPTION",
                    "detail": f"Under 500 EUR — PSP ({psp_lower}) may request TRA exemption if their fraud rate qualifies. "
                              "Low-risk profile increases TRA approval probability.",
                })
        
        return {
            "domain": domain,
            "bypass_score": score_result["bypass_score"],
            "bypass_level": score_result["bypass_level"],
            "card_country": card_country,
            "amount": amount,
            "psp": psp_lower,
            "steps": steps,
            "applicable_techniques": [
                t.name for t in THREE_DS_DOWNGRADE_ATTACKS
                if psp_lower in t.applicable_psps
            ],
            "psp_weak_points": psp_info.get("weak_points", []),
            "warnings": score_result["warnings"],
        }
    
    def get_downgradeable_sites(self, sites: List[Dict]) -> List[Dict]:
        """
        From a list of site dicts, return only those where 3DS 2.0→1.0 
        downgrade is possible, sorted by bypass score.
        """
        results = []
        for site in sites:
            psp = site.get("psp", "unknown")
            psp_info = PSP_3DS_VULNERABILITIES.get(psp, {})
            if psp_info.get("downgrade_possible") and site.get("three_ds") != "none":
                score = self.score_site(
                    site["domain"], psp, site.get("three_ds", "conditional"),
                    site.get("fraud_engine", "none"), site.get("is_shopify", False)
                )
                site_copy = dict(site)
                site_copy["bypass_score"] = score["bypass_score"]
                site_copy["bypass_level"] = score["bypass_level"]
                site_copy["downgrade_method"] = psp_info.get("downgrade_method", "")
                results.append(site_copy)
        
        results.sort(key=lambda x: x["bypass_score"], reverse=True)
        return results


# Convenience exports
def get_3ds_bypass_score(domain, psp="unknown", three_ds="unknown", **kwargs):
    """Quick: score a site's 3DS bypass potential"""
    return ThreeDSBypassEngine().score_site(domain, psp, three_ds, **kwargs)

def get_3ds_bypass_plan(domain, psp, card_country="US", amount=200, **kwargs):
    """Quick: generate 3DS bypass plan for a site"""
    return ThreeDSBypassEngine().get_bypass_plan(domain, psp, card_country=card_country, amount=amount, **kwargs)

def get_downgrade_attacks():
    """Quick: get all 3DS downgrade attack techniques"""
    return [{"name": t.name, "type": t.bypass_type.value, "success_rate": t.success_rate,
             "risk": t.risk_level, "psps": t.applicable_psps, "steps": t.implementation,
             "description": t.description} for t in THREE_DS_DOWNGRADE_ATTACKS]

def get_psd2_exemptions():
    """Quick: get PSD2 exemption exploitation guide"""
    return PSD2_EXEMPTIONS

def get_psp_vulnerabilities(psp=None):
    """Quick: get PSP-specific 3DS vulnerabilities"""
    if psp:
        return PSP_3DS_VULNERABILITIES.get(psp.lower(), {})
    return PSP_3DS_VULNERABILITIES


# ═══════════════════════════════════════════════════════════════════════════
# V7.0.2: NON-VBV CARD RECOMMENDATION ENGINE
# Multi-country BIN intelligence for 3DS avoidance
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class NonVBVBin:
    """A BIN known or likely to be non-VBV enrolled"""
    bin: str
    bank: str
    country: str
    network: str                # visa, mastercard, amex, discover
    card_type: str              # credit, debit
    level: str                  # classic, gold, platinum, signature, world, etc.
    vbv_status: str             # non_vbv, low_vbv, conditional_vbv
    three_ds_rate: float        # 0.0-1.0 estimated 3DS trigger rate
    avs_required: bool          # Whether AVS is enforced by issuer
    notes: str = ""
    best_for: List[str] = field(default_factory=list)  # Best merchant categories


@dataclass
class CountryProfile:
    """3DS enforcement profile for a country"""
    code: str                   # ISO 3166-1 alpha-2
    name: str
    difficulty: str             # easy, moderate, hard, very_hard
    psd2_enforced: bool         # EU PSD2 Strong Customer Authentication
    three_ds_base_rate: float   # Base 3DS rate for cards from this country
    avs_common: bool            # Whether AVS is commonly enforced
    best_card_types: List[str]  # credit, debit
    best_networks: List[str]    # visa, mastercard, etc.
    notes: str = ""
    recommended_targets: List[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# COUNTRY PROFILES — 3DS enforcement by country
# ═══════════════════════════════════════════════════════════════════════════

COUNTRY_PROFILES: Dict[str, CountryProfile] = {
    "US": CountryProfile(
        code="US", name="United States",
        difficulty="easy",
        psd2_enforced=False,
        three_ds_base_rate=0.15,
        avs_common=True,
        best_card_types=["credit"],
        best_networks=["visa", "mastercard"],
        notes="No PSD2. 3DS is optional and risk-based. Many banks don't enroll cards in VBV. "
              "AVS is strictly enforced — must match billing address exactly. "
              "Best country for non-VBV operations. Focus on credit over debit.",
        recommended_targets=["amazon.com", "walmart.com", "bestbuy.com", "newegg.com",
                             "g2a.com", "eneba.com", "steam", "priceline.com"],
    ),
    "CA": CountryProfile(
        code="CA", name="Canada",
        difficulty="easy",
        psd2_enforced=False,
        three_ds_base_rate=0.20,
        avs_common=True,
        best_card_types=["credit"],
        best_networks=["visa", "mastercard"],
        notes="Similar to US. No PSD2. 3DS adoption growing but still optional for most banks. "
              "TD, RBC, BMO cards often non-VBV. AVS enforced on domestic merchants.",
        recommended_targets=["amazon.ca", "bestbuy.ca", "g2a.com", "eneba.com", "steam"],
    ),
    "GB": CountryProfile(
        code="GB", name="United Kingdom",
        difficulty="moderate",
        psd2_enforced=True,
        three_ds_base_rate=0.55,
        avs_common=True,
        best_card_types=["credit"],
        best_networks=["visa", "mastercard"],
        notes="PSD2 enforced since 2021 but with exemptions. Transactions under £30 often exempt. "
              "Older cards from smaller building societies may not be enrolled. "
              "Credit cards have lower 3DS rates than debit. Monzo/Revolut always trigger 3DS.",
        recommended_targets=["amazon.co.uk", "g2a.com", "eneba.com", "steam"],
    ),
    "FR": CountryProfile(
        code="FR", name="France",
        difficulty="moderate",
        psd2_enforced=True,
        three_ds_base_rate=0.50,
        avs_common=False,
        best_card_types=["credit"],
        best_networks=["visa", "mastercard"],
        notes="PSD2 enforced but French banks have high exemption rates for low-value transactions. "
              "Transactions under 30 EUR often skip 3DS. Carte Bancaire (CB) network widely used — "
              "CB co-branded Visa/MC often have lower 3DS rates. AVS rarely enforced. "
              "Credit Mutuel, Banque Postale cards good candidates.",
        recommended_targets=["amazon.fr", "cdiscount.com", "g2a.com", "eneba.com", "instant-gaming.com"],
    ),
    "DE": CountryProfile(
        code="DE", name="Germany",
        difficulty="moderate",
        psd2_enforced=True,
        three_ds_base_rate=0.45,
        avs_common=False,
        best_card_types=["credit"],
        best_networks=["visa", "mastercard"],
        notes="PSD2 enforced but German banks are slower to adopt full 3DS 2.0. "
              "Many Sparkasse and Volksbank cards still use older auth methods. "
              "AVS almost never enforced in Germany. SEPA direct debit preferred by locals — "
              "credit card 3DS enrollment is lower than UK. Under 30 EUR often exempt.",
        recommended_targets=["amazon.de", "otto.de", "g2a.com", "eneba.com", "instant-gaming.com"],
    ),
    "NL": CountryProfile(
        code="NL", name="Netherlands",
        difficulty="moderate",
        psd2_enforced=True,
        three_ds_base_rate=0.50,
        avs_common=False,
        best_card_types=["credit"],
        best_networks=["visa", "mastercard"],
        notes="iDEAL is dominant payment method — credit card usage is lower, meaning bank 3DS "
              "infrastructure for cards is less mature. ING and ABN AMRO credit cards have "
              "moderate 3DS rates. Under 30 EUR often exempt. AVS not enforced.",
        recommended_targets=["bol.com", "g2a.com", "eneba.com", "instant-gaming.com"],
    ),
    "AU": CountryProfile(
        code="AU", name="Australia",
        difficulty="easy",
        psd2_enforced=False,
        three_ds_base_rate=0.20,
        avs_common=True,
        best_card_types=["credit"],
        best_networks=["visa", "mastercard"],
        notes="No PSD2. 3DS adoption is voluntary. Many AU banks haven't enrolled all cards. "
              "Commonwealth Bank, Westpac, ANZ cards often non-VBV for credit. "
              "AVS enforced on some merchants. Good country for operations.",
        recommended_targets=["amazon.com.au", "g2a.com", "eneba.com", "steam"],
    ),
    "IT": CountryProfile(
        code="IT", name="Italy",
        difficulty="moderate",
        psd2_enforced=True,
        three_ds_base_rate=0.50,
        avs_common=False,
        best_card_types=["credit"],
        best_networks=["visa", "mastercard"],
        notes="PSD2 enforced. PostePay prepaid cards widely used but high 3DS. "
              "UniCredit and Intesa Sanpaolo credit cards have moderate 3DS rates. "
              "Under 30 EUR often exempt. AVS not enforced.",
        recommended_targets=["amazon.it", "g2a.com", "eneba.com", "instant-gaming.com"],
    ),
    "ES": CountryProfile(
        code="ES", name="Spain",
        difficulty="moderate",
        psd2_enforced=True,
        three_ds_base_rate=0.50,
        avs_common=False,
        best_card_types=["credit"],
        best_networks=["visa", "mastercard"],
        notes="PSD2 enforced. CaixaBank and BBVA credit cards have moderate 3DS rates. "
              "Under 30 EUR often exempt. AVS not enforced in Spain.",
        recommended_targets=["amazon.es", "g2a.com", "eneba.com", "instant-gaming.com"],
    ),
    "BE": CountryProfile(
        code="BE", name="Belgium",
        difficulty="moderate",
        psd2_enforced=True,
        three_ds_base_rate=0.45,
        avs_common=False,
        best_card_types=["credit"],
        best_networks=["visa", "mastercard"],
        notes="PSD2 enforced. KBC and BNP Paribas Fortis cards have moderate 3DS rates. "
              "Bancontact is dominant locally but international credit cards have lower 3DS. "
              "Under 30 EUR often exempt. AVS not enforced.",
        recommended_targets=["amazon.de", "bol.com", "g2a.com", "eneba.com"],
    ),
    "JP": CountryProfile(
        code="JP", name="Japan",
        difficulty="easy",
        psd2_enforced=False,
        three_ds_base_rate=0.15,
        avs_common=False,
        best_card_types=["credit"],
        best_networks=["visa", "mastercard"],
        notes="No PSD2. 3DS adoption is very low in Japan. Most Japanese cards are non-VBV. "
              "JCB network dominant but Visa/MC also issued. AVS rarely enforced. "
              "Rakuten, MUFG, SMBC cards almost never trigger 3DS on international sites.",
        recommended_targets=["amazon.co.jp", "g2a.com", "steam"],
    ),
    "BR": CountryProfile(
        code="BR", name="Brazil",
        difficulty="easy",
        psd2_enforced=False,
        three_ds_base_rate=0.10,
        avs_common=False,
        best_card_types=["credit"],
        best_networks=["visa", "mastercard"],
        notes="No PSD2. Very low 3DS adoption. Most Brazilian cards are non-VBV. "
              "Itau, Bradesco, Banco do Brasil cards rarely trigger 3DS internationally. "
              "AVS not enforced. CPF (tax ID) sometimes required on local merchants. "
              "Cross-border transactions may have higher decline rates from issuing banks.",
        recommended_targets=["g2a.com", "eneba.com", "steam"],
    ),
    "MX": CountryProfile(
        code="MX", name="Mexico",
        difficulty="easy",
        psd2_enforced=False,
        three_ds_base_rate=0.10,
        avs_common=False,
        best_card_types=["credit"],
        best_networks=["visa", "mastercard"],
        notes="No PSD2. Very low 3DS adoption. Banamex, Banorte, BBVA Mexico cards "
              "rarely trigger 3DS. AVS not enforced. Cross-border may decline more often.",
        recommended_targets=["g2a.com", "eneba.com", "steam", "amazon.com.mx"],
    ),
}


# ═══════════════════════════════════════════════════════════════════════════
# NON-VBV BIN DATABASE — Organized by country
# BINs known or highly likely to NOT trigger 3DS/VBV
# ═══════════════════════════════════════════════════════════════════════════

NON_VBV_BINS: Dict[str, List[NonVBVBin]] = {
    # ─── UNITED STATES ──────────────────────────────────────────────────
    "US": [
        NonVBVBin("401200", "Chase", "US", "visa", "credit", "signature",
                  "non_vbv", 0.10, True,
                  "Chase Sapphire — low 3DS domestically. Strong on US merchants.",
                  ["amazon.com", "bestbuy.com", "walmart.com"]),
        NonVBVBin("403587", "Chase", "US", "visa", "credit", "classic",
                  "non_vbv", 0.12, True,
                  "Chase Freedom — widely issued, rarely triggers 3DS.",
                  ["g2a.com", "eneba.com", "steam"]),
        NonVBVBin("433610", "Wells Fargo", "US", "visa", "credit", "signature",
                  "non_vbv", 0.08, True,
                  "Wells Fargo Visa Signature — very low 3DS rate.",
                  ["amazon.com", "walmart.com", "g2a.com"]),
        NonVBVBin("540443", "Wells Fargo", "US", "mastercard", "credit", "world",
                  "non_vbv", 0.10, True,
                  "Wells Fargo World MC — low 3DS, good for mid-value.",
                  ["bestbuy.com", "newegg.com"]),
        NonVBVBin("440066", "US Bank", "US", "visa", "credit", "platinum",
                  "non_vbv", 0.12, True,
                  "US Bank Platinum — moderate limits, low 3DS.",
                  ["g2a.com", "eneba.com", "steam"]),
        NonVBVBin("548760", "US Bank", "US", "mastercard", "credit", "world",
                  "non_vbv", 0.10, True,
                  "US Bank Cash+ World MC — low 3DS.",
                  ["amazon.com", "walmart.com"]),
        NonVBVBin("453245", "USAA", "US", "visa", "credit", "signature",
                  "non_vbv", 0.05, True,
                  "USAA Visa Signature — military bank, very low 3DS. Relaxed fraud model.",
                  ["amazon.com", "bestbuy.com", "g2a.com", "eneba.com"]),
        NonVBVBin("459500", "Navy Federal", "US", "visa", "credit", "signature",
                  "non_vbv", 0.05, True,
                  "Navy Federal Visa Sig — military bank, very low 3DS.",
                  ["amazon.com", "bestbuy.com", "g2a.com", "steam"]),
        NonVBVBin("556737", "Fifth Third", "US", "mastercard", "credit", "world",
                  "non_vbv", 0.08, True,
                  "Fifth Third Bank — regional bank, low 3DS adoption.",
                  ["g2a.com", "eneba.com", "amazon.com"]),
        NonVBVBin("400360", "Visa Inc.", "US", "visa", "credit", "classic",
                  "low_vbv", 0.15, True,
                  "Generic Visa Classic — low 3DS on most US merchants.",
                  ["g2a.com", "eneba.com", "steam"]),
        NonVBVBin("601100", "Discover", "US", "discover", "credit", "classic",
                  "non_vbv", 0.08, False,
                  "Discover it — no VBV (Discover uses ProtectBuy, lower adoption). AVS relaxed.",
                  ["amazon.com", "walmart.com"]),
        NonVBVBin("650000", "Discover", "US", "discover", "credit", "classic",
                  "non_vbv", 0.08, False,
                  "Discover Cashback — ProtectBuy rarely triggers. Good for US merchants.",
                  ["amazon.com", "g2a.com"]),
    ],

    # ─── CANADA ─────────────────────────────────────────────────────────
    "CA": [
        NonVBVBin("450140", "TD Bank", "CA", "visa", "credit", "platinum",
                  "non_vbv", 0.15, True,
                  "TD Visa Platinum — Canadian bank, low 3DS on domestic/US merchants.",
                  ["amazon.ca", "bestbuy.ca", "g2a.com"]),
        NonVBVBin("455618", "RBC Royal Bank", "CA", "visa", "credit", "gold",
                  "non_vbv", 0.12, True,
                  "RBC Visa Gold — large issuer, low 3DS domestically.",
                  ["amazon.ca", "g2a.com", "eneba.com"]),
        NonVBVBin("459022", "BMO", "CA", "visa", "credit", "platinum",
                  "non_vbv", 0.15, True,
                  "BMO Visa Platinum — moderate limits, low 3DS.",
                  ["amazon.ca", "steam"]),
        NonVBVBin("525893", "Scotiabank", "CA", "mastercard", "credit", "world",
                  "non_vbv", 0.12, True,
                  "Scotiabank MC World — low 3DS on US/CA merchants.",
                  ["amazon.ca", "amazon.com", "g2a.com"]),
        NonVBVBin("549184", "CIBC", "CA", "mastercard", "credit", "world",
                  "low_vbv", 0.18, True,
                  "CIBC MC World — moderate 3DS, good for low-value.",
                  ["g2a.com", "eneba.com"]),
    ],

    # ─── UNITED KINGDOM ─────────────────────────────────────────────────
    "GB": [
        NonVBVBin("475129", "HSBC", "GB", "visa", "credit", "gold",
                  "conditional_vbv", 0.35, True,
                  "HSBC Visa Gold — 3DS often skipped under £30 (PSD2 exemption). Credit only.",
                  ["amazon.co.uk", "g2a.com"]),
        NonVBVBin("465859", "Lloyds", "GB", "visa", "credit", "classic",
                  "conditional_vbv", 0.40, True,
                  "Lloyds Visa — PSD2 exemption under £30. Older cards sometimes non-VBV.",
                  ["g2a.com", "eneba.com"]),
        NonVBVBin("476250", "NatWest", "GB", "visa", "credit", "gold",
                  "conditional_vbv", 0.35, True,
                  "NatWest Visa Gold — exemption under £30. Credit has lower 3DS than debit.",
                  ["g2a.com", "amazon.co.uk"]),
        NonVBVBin("518791", "Santander UK", "GB", "mastercard", "credit", "world",
                  "conditional_vbv", 0.38, True,
                  "Santander UK MC — PSD2 exemptions apply. Keep under £30 for best results.",
                  ["g2a.com", "eneba.com", "instant-gaming.com"]),
        NonVBVBin("543458", "Tesco Bank", "GB", "mastercard", "credit", "classic",
                  "low_vbv", 0.30, True,
                  "Tesco Bank MC — smaller issuer, less aggressive 3DS. PSD2 exemptions apply.",
                  ["g2a.com", "eneba.com"]),
    ],

    # ─── FRANCE ─────────────────────────────────────────────────────────
    "FR": [
        NonVBVBin("497010", "Credit Mutuel", "FR", "visa", "credit", "classic",
                  "low_vbv", 0.25, False,
                  "Credit Mutuel CB/Visa — co-branded Carte Bancaire. Lower 3DS on international.",
                  ["amazon.fr", "g2a.com", "instant-gaming.com"]),
        NonVBVBin("497011", "Banque Postale", "FR", "visa", "credit", "classic",
                  "low_vbv", 0.22, False,
                  "La Banque Postale — postal bank, less aggressive fraud detection.",
                  ["amazon.fr", "g2a.com", "cdiscount.com"]),
        NonVBVBin("533110", "Credit Agricole", "FR", "mastercard", "credit", "gold",
                  "low_vbv", 0.28, False,
                  "Credit Agricole MC Gold — large bank but moderate 3DS on international.",
                  ["g2a.com", "eneba.com", "instant-gaming.com"]),
        NonVBVBin("513500", "BNP Paribas", "FR", "mastercard", "credit", "world",
                  "conditional_vbv", 0.35, False,
                  "BNP Paribas MC World — PSD2 exempt under 30 EUR. No AVS enforcement.",
                  ["amazon.fr", "g2a.com"]),
        NonVBVBin("497040", "Caisse d'Epargne", "FR", "visa", "credit", "classic",
                  "low_vbv", 0.22, False,
                  "Caisse d'Epargne CB/Visa — savings bank, low 3DS on international.",
                  ["g2a.com", "instant-gaming.com", "eneba.com"]),
    ],

    # ─── GERMANY ────────────────────────────────────────────────────────
    "DE": [
        NonVBVBin("400606", "Sparkasse", "DE", "visa", "credit", "classic",
                  "low_vbv", 0.20, False,
                  "Sparkasse Visa — network of savings banks, slower 3DS adoption. No AVS.",
                  ["amazon.de", "g2a.com", "eneba.com", "instant-gaming.com"]),
        NonVBVBin("415344", "Volksbank", "DE", "visa", "credit", "classic",
                  "low_vbv", 0.22, False,
                  "Volksbank Visa — cooperative bank, moderate 3DS. No AVS.",
                  ["amazon.de", "g2a.com"]),
        NonVBVBin("521396", "Commerzbank", "DE", "mastercard", "credit", "gold",
                  "conditional_vbv", 0.30, False,
                  "Commerzbank MC Gold — 3DS exempt under 30 EUR. No AVS.",
                  ["amazon.de", "g2a.com", "eneba.com"]),
        NonVBVBin("516952", "DKB", "DE", "mastercard", "credit", "classic",
                  "low_vbv", 0.25, False,
                  "DKB Visa — online bank, moderate 3DS. Free Visa debit popular.",
                  ["g2a.com", "eneba.com", "instant-gaming.com"]),
        NonVBVBin("490680", "ING-DiBa", "DE", "visa", "credit", "classic",
                  "low_vbv", 0.25, False,
                  "ING Germany Visa — online bank, moderate 3DS adoption.",
                  ["amazon.de", "g2a.com"]),
    ],

    # ─── NETHERLANDS ────────────────────────────────────────────────────
    "NL": [
        NonVBVBin("412894", "ING", "NL", "visa", "credit", "gold",
                  "conditional_vbv", 0.30, False,
                  "ING Visa Gold — PSD2 exempt under 30 EUR. No AVS.",
                  ["bol.com", "g2a.com", "eneba.com"]),
        NonVBVBin("524804", "ABN AMRO", "NL", "mastercard", "credit", "gold",
                  "conditional_vbv", 0.32, False,
                  "ABN AMRO MC Gold — moderate 3DS. No AVS enforced.",
                  ["g2a.com", "eneba.com"]),
        NonVBVBin("542606", "Rabobank", "NL", "mastercard", "credit", "classic",
                  "conditional_vbv", 0.30, False,
                  "Rabobank MC — cooperative bank. PSD2 exemptions apply.",
                  ["g2a.com", "eneba.com", "instant-gaming.com"]),
    ],

    # ─── AUSTRALIA ──────────────────────────────────────────────────────
    "AU": [
        NonVBVBin("453904", "Commonwealth Bank", "AU", "visa", "credit", "platinum",
                  "non_vbv", 0.12, True,
                  "CommBank Visa Platinum — large issuer, low 3DS. AVS on some merchants.",
                  ["amazon.com.au", "g2a.com", "eneba.com"]),
        NonVBVBin("463524", "Westpac", "AU", "visa", "credit", "gold",
                  "non_vbv", 0.10, True,
                  "Westpac Visa Gold — very low 3DS rate.",
                  ["g2a.com", "eneba.com", "steam"]),
        NonVBVBin("528735", "ANZ", "AU", "mastercard", "credit", "platinum",
                  "non_vbv", 0.12, True,
                  "ANZ MC Platinum — low 3DS, good for gaming/digital.",
                  ["g2a.com", "steam", "eneba.com"]),
        NonVBVBin("455708", "NAB", "AU", "visa", "credit", "gold",
                  "non_vbv", 0.10, True,
                  "NAB Visa Gold — low 3DS. Good for international merchants.",
                  ["amazon.com.au", "g2a.com"]),
    ],

    # ─── ITALY ──────────────────────────────────────────────────────────
    "IT": [
        NonVBVBin("401795", "UniCredit", "IT", "visa", "credit", "gold",
                  "conditional_vbv", 0.30, False,
                  "UniCredit Visa Gold — PSD2 exempt under 30 EUR. No AVS.",
                  ["amazon.it", "g2a.com"]),
        NonVBVBin("540500", "Intesa Sanpaolo", "IT", "mastercard", "credit", "gold",
                  "conditional_vbv", 0.32, False,
                  "Intesa MC Gold — moderate 3DS. No AVS.",
                  ["g2a.com", "eneba.com"]),
    ],

    # ─── SPAIN ──────────────────────────────────────────────────────────
    "ES": [
        NonVBVBin("454618", "CaixaBank", "ES", "visa", "credit", "gold",
                  "conditional_vbv", 0.30, False,
                  "CaixaBank Visa Gold — PSD2 exempt under 30 EUR.",
                  ["amazon.es", "g2a.com"]),
        NonVBVBin("540616", "BBVA Spain", "ES", "mastercard", "credit", "gold",
                  "conditional_vbv", 0.32, False,
                  "BBVA MC Gold — moderate 3DS.",
                  ["g2a.com", "eneba.com"]),
    ],

    # ─── BELGIUM ────────────────────────────────────────────────────────
    "BE": [
        NonVBVBin("475116", "KBC", "BE", "visa", "credit", "gold",
                  "conditional_vbv", 0.28, False,
                  "KBC Visa Gold — PSD2 exempt under 30 EUR. No AVS.",
                  ["g2a.com", "eneba.com", "amazon.de"]),
        NonVBVBin("518594", "BNP Paribas Fortis", "BE", "mastercard", "credit", "gold",
                  "conditional_vbv", 0.30, False,
                  "Fortis MC Gold — moderate 3DS.",
                  ["g2a.com", "eneba.com"]),
    ],

    # ─── JAPAN ──────────────────────────────────────────────────────────
    "JP": [
        NonVBVBin("401170", "MUFG", "JP", "visa", "credit", "gold",
                  "non_vbv", 0.05, False,
                  "MUFG Visa Gold — very low 3DS. Japan has minimal 3DS adoption.",
                  ["amazon.co.jp", "g2a.com", "steam"]),
        NonVBVBin("453235", "SMBC", "JP", "visa", "credit", "classic",
                  "non_vbv", 0.05, False,
                  "SMBC Visa — very low 3DS. No AVS.",
                  ["g2a.com", "steam"]),
        NonVBVBin("524050", "Rakuten Card", "JP", "mastercard", "credit", "classic",
                  "non_vbv", 0.08, False,
                  "Rakuten MC — popular issuer, very low 3DS internationally.",
                  ["g2a.com", "eneba.com", "steam"]),
    ],

    # ─── BRAZIL ─────────────────────────────────────────────────────────
    "BR": [
        NonVBVBin("418310", "Itau", "BR", "visa", "credit", "gold",
                  "non_vbv", 0.05, False,
                  "Itau Visa Gold — very low 3DS. Cross-border may decline from issuing bank.",
                  ["g2a.com", "eneba.com", "steam"]),
        NonVBVBin("546554", "Bradesco", "BR", "mastercard", "credit", "gold",
                  "non_vbv", 0.05, False,
                  "Bradesco MC Gold — very low 3DS. CPF may be needed on BR merchants.",
                  ["g2a.com", "steam"]),
        NonVBVBin("405680", "Banco do Brasil", "BR", "visa", "credit", "classic",
                  "non_vbv", 0.05, False,
                  "BB Visa — government bank, very low 3DS internationally.",
                  ["g2a.com", "eneba.com"]),
    ],

    # ─── MEXICO ─────────────────────────────────────────────────────────
    "MX": [
        NonVBVBin("406243", "Banamex", "MX", "visa", "credit", "gold",
                  "non_vbv", 0.05, False,
                  "Banamex Visa Gold — very low 3DS. Cross-border may decline.",
                  ["g2a.com", "eneba.com"]),
        NonVBVBin("537437", "BBVA Mexico", "MX", "mastercard", "credit", "gold",
                  "non_vbv", 0.08, False,
                  "BBVA Mexico MC Gold — very low 3DS.",
                  ["g2a.com", "steam"]),
        NonVBVBin("450906", "Banorte", "MX", "visa", "credit", "classic",
                  "non_vbv", 0.05, False,
                  "Banorte Visa — low 3DS, good for gaming targets.",
                  ["g2a.com", "eneba.com", "steam"]),
        NonVBVBin("431460", "Santander MX", "MX", "visa", "credit", "gold",
                  "non_vbv", 0.06, False,
                  "Santander Mexico Visa Gold — very low 3DS.",
                  ["g2a.com", "eneba.com"]),
    ],

    # ─── ADDITIONAL US BINs ──────────────────────────────────────────
    # Extended US coverage — more banks, more card types
    "US_EXT": [
        NonVBVBin("414720", "Citi", "US", "visa", "credit", "signature",
                  "non_vbv", 0.12, True,
                  "Citi Double Cash Visa Sig — widely issued, low 3DS domestic.",
                  ["amazon.com", "walmart.com", "bestbuy.com"]),
        NonVBVBin("438857", "Citi", "US", "visa", "credit", "platinum",
                  "non_vbv", 0.10, True,
                  "Citi Costco Visa — low 3DS, high limits.",
                  ["costco.com", "amazon.com", "bestbuy.com"]),
        NonVBVBin("479300", "Capital One", "US", "visa", "credit", "signature",
                  "non_vbv", 0.14, True,
                  "Capital One Venture — risk-based 3DS, low trigger domestic.",
                  ["amazon.com", "g2a.com", "hotels.com"]),
        NonVBVBin("428600", "Capital One", "US", "visa", "credit", "platinum",
                  "non_vbv", 0.12, True,
                  "Capital One Quicksilver — widely issued, low 3DS.",
                  ["amazon.com", "walmart.com", "g2a.com"]),
        NonVBVBin("522490", "Capital One", "US", "mastercard", "credit", "world",
                  "non_vbv", 0.12, True,
                  "Capital One Savor MC World — low 3DS.",
                  ["amazon.com", "g2a.com", "doordash.com"]),
        NonVBVBin("426684", "Bank of America", "US", "visa", "credit", "signature",
                  "non_vbv", 0.10, True,
                  "BofA Cash Rewards Visa Sig — large issuer, low 3DS.",
                  ["amazon.com", "walmart.com", "bestbuy.com"]),
        NonVBVBin("481075", "Bank of America", "US", "visa", "credit", "platinum",
                  "non_vbv", 0.08, True,
                  "BofA Travel Rewards — low 3DS, good on travel merchants.",
                  ["priceline.com", "hotels.com", "amazon.com"]),
        NonVBVBin("517805", "PNC Bank", "US", "mastercard", "credit", "world",
                  "non_vbv", 0.08, True,
                  "PNC Cash Rewards MC World — regional bank, very low 3DS.",
                  ["amazon.com", "g2a.com", "eneba.com"]),
        NonVBVBin("424604", "SunTrust", "US", "visa", "credit", "signature",
                  "non_vbv", 0.07, True,
                  "SunTrust/Truist Visa Sig — regional, relaxed fraud model.",
                  ["amazon.com", "g2a.com"]),
        NonVBVBin("431940", "TD Bank US", "US", "visa", "credit", "platinum",
                  "non_vbv", 0.10, True,
                  "TD Bank US Visa Platinum — lower 3DS than Canadian counterpart.",
                  ["amazon.com", "bestbuy.com"]),
        NonVBVBin("480091", "Regions Bank", "US", "visa", "credit", "signature",
                  "non_vbv", 0.06, True,
                  "Regions Visa Sig — small regional, very low 3DS adoption.",
                  ["amazon.com", "g2a.com", "eneba.com"]),
        NonVBVBin("527347", "KeyBank", "US", "mastercard", "credit", "world",
                  "non_vbv", 0.07, True,
                  "KeyBank MC World — regional, low 3DS.",
                  ["g2a.com", "eneba.com", "steam"]),
        NonVBVBin("486500", "Huntington", "US", "visa", "credit", "platinum",
                  "non_vbv", 0.06, True,
                  "Huntington Voice Visa — very low 3DS, relaxed.",
                  ["amazon.com", "g2a.com"]),
        NonVBVBin("414740", "Synchrony", "US", "visa", "credit", "classic",
                  "non_vbv", 0.15, True,
                  "Synchrony store cards — many merchants, moderate 3DS.",
                  ["amazon.com"]),
        NonVBVBin("476173", "M&T Bank", "US", "visa", "credit", "gold",
                  "non_vbv", 0.06, True,
                  "M&T Bank Visa Gold — East Coast regional, very low 3DS.",
                  ["amazon.com", "g2a.com"]),
        NonVBVBin("544616", "Ally Bank", "US", "mastercard", "credit", "world",
                  "non_vbv", 0.09, True,
                  "Ally MC World — online bank, low 3DS.",
                  ["g2a.com", "eneba.com"]),
        NonVBVBin("414734", "Pentagon FCU", "US", "visa", "credit", "platinum",
                  "non_vbv", 0.04, True,
                  "PenFed Visa Platinum — credit union, very relaxed fraud model.",
                  ["amazon.com", "g2a.com", "bestbuy.com"]),
        NonVBVBin("469266", "BECU", "US", "visa", "credit", "signature",
                  "non_vbv", 0.05, True,
                  "BECU Visa Sig — credit union, very low 3DS.",
                  ["amazon.com", "g2a.com", "steam"]),
        NonVBVBin("486596", "Citizen Bank", "US", "visa", "credit", "platinum",
                  "non_vbv", 0.07, True,
                  "Citizens Bank Visa — regional, relaxed model.",
                  ["amazon.com", "walmart.com"]),
    ],

    # ─── COLOMBIA ──────────────────────────────────────────────────────
    "CO": [
        NonVBVBin("457554", "Bancolombia", "CO", "visa", "credit", "gold",
                  "non_vbv", 0.04, False,
                  "Bancolombia Visa Gold — virtually no 3DS. Cross-border risk from issuer.",
                  ["g2a.com", "eneba.com", "steam"]),
        NonVBVBin("540663", "Davivienda", "CO", "mastercard", "credit", "gold",
                  "non_vbv", 0.05, False,
                  "Davivienda MC Gold — very low 3DS.",
                  ["g2a.com", "steam"]),
        NonVBVBin("479266", "BBVA Colombia", "CO", "visa", "credit", "classic",
                  "non_vbv", 0.04, False,
                  "BBVA Colombia Visa — minimal 3DS, no AVS.",
                  ["g2a.com", "eneba.com"]),
    ],

    # ─── ARGENTINA ─────────────────────────────────────────────────────
    "AR": [
        NonVBVBin("450799", "Banco Galicia", "AR", "visa", "credit", "gold",
                  "non_vbv", 0.03, False,
                  "Galicia Visa Gold — virtually no 3DS. Currency controls may limit cross-border.",
                  ["g2a.com", "steam"]),
        NonVBVBin("522135", "Banco Macro", "AR", "mastercard", "credit", "gold",
                  "non_vbv", 0.03, False,
                  "Macro MC Gold — no 3DS. ARS currency restrictions apply.",
                  ["g2a.com", "eneba.com"]),
        NonVBVBin("425860", "HSBC Argentina", "AR", "visa", "credit", "platinum",
                  "non_vbv", 0.04, False,
                  "HSBC AR Visa Platinum — very low 3DS internationally.",
                  ["g2a.com", "steam"]),
    ],

    # ─── INDIA ─────────────────────────────────────────────────────────
    "IN": [
        NonVBVBin("436077", "HDFC Bank", "IN", "visa", "credit", "gold",
                  "low_vbv", 0.20, False,
                  "HDFC Visa Gold — India has OTP-based 3DS but international tx often bypass. No AVS.",
                  ["g2a.com", "steam"]),
        NonVBVBin("524289", "ICICI Bank", "IN", "mastercard", "credit", "platinum",
                  "low_vbv", 0.22, False,
                  "ICICI MC Platinum — international 3DS lower than domestic. Forex markup applies.",
                  ["g2a.com", "eneba.com"]),
        NonVBVBin("460523", "SBI", "IN", "visa", "credit", "gold",
                  "low_vbv", 0.25, False,
                  "SBI Visa Gold — government bank, moderate 3DS on international.",
                  ["g2a.com", "steam"]),
        NonVBVBin("512419", "Axis Bank", "IN", "mastercard", "credit", "world",
                  "low_vbv", 0.18, False,
                  "Axis MC World — lower 3DS on international transactions.",
                  ["g2a.com", "eneba.com", "steam"]),
    ],

    # ─── TURKEY ────────────────────────────────────────────────────────
    "TR": [
        NonVBVBin("454671", "Garanti BBVA", "TR", "visa", "credit", "gold",
                  "low_vbv", 0.15, False,
                  "Garanti Visa Gold — Turkey has growing 3DS but many BINs not enrolled. No AVS.",
                  ["g2a.com", "eneba.com"]),
        NonVBVBin("540667", "Isbank", "TR", "mastercard", "credit", "gold",
                  "low_vbv", 0.15, False,
                  "Isbank MC Gold — moderate 3DS, TRY currency issues on cross-border.",
                  ["g2a.com", "steam"]),
        NonVBVBin("413226", "Akbank", "TR", "visa", "credit", "platinum",
                  "low_vbv", 0.12, False,
                  "Akbank Visa Platinum — lower 3DS than average Turkish bank.",
                  ["g2a.com", "eneba.com"]),
    ],

    # ─── UAE ───────────────────────────────────────────────────────────
    "AE": [
        NonVBVBin("457617", "Emirates NBD", "AE", "visa", "credit", "signature",
                  "non_vbv", 0.08, False,
                  "Emirates NBD Visa Sig — low 3DS, no PSD2, no AVS. High limits.",
                  ["g2a.com", "eneba.com", "amazon.ae"]),
        NonVBVBin("530060", "Mashreq Bank", "AE", "mastercard", "credit", "world",
                  "non_vbv", 0.10, False,
                  "Mashreq MC World — moderate 3DS, good limits.",
                  ["g2a.com", "amazon.ae"]),
        NonVBVBin("422817", "ADCB", "AE", "visa", "credit", "platinum",
                  "non_vbv", 0.08, False,
                  "ADCB Visa Platinum — low 3DS, Gulf region bank.",
                  ["g2a.com", "eneba.com"]),
    ],

    # ─── SOUTH KOREA ───────────────────────────────────────────────────
    "KR": [
        NonVBVBin("404825", "Shinhan Card", "KR", "visa", "credit", "gold",
                  "non_vbv", 0.05, False,
                  "Shinhan Visa Gold — Korea has very low international 3DS. No AVS.",
                  ["g2a.com", "steam", "eneba.com"]),
        NonVBVBin("515831", "Samsung Card", "KR", "mastercard", "credit", "platinum",
                  "non_vbv", 0.05, False,
                  "Samsung MC Platinum — very low 3DS internationally.",
                  ["g2a.com", "steam"]),
        NonVBVBin("465275", "KB Card", "KR", "visa", "credit", "classic",
                  "non_vbv", 0.06, False,
                  "KB Kookmin Visa — large issuer, minimal 3DS on cross-border.",
                  ["g2a.com", "eneba.com"]),
    ],

    # ─── THAILAND ──────────────────────────────────────────────────────
    "TH": [
        NonVBVBin("418052", "Bangkok Bank", "TH", "visa", "credit", "gold",
                  "non_vbv", 0.04, False,
                  "Bangkok Bank Visa Gold — minimal 3DS. No AVS. THB currency.",
                  ["g2a.com", "steam"]),
        NonVBVBin("552234", "Kasikorn Bank", "TH", "mastercard", "credit", "platinum",
                  "non_vbv", 0.05, False,
                  "KBank MC Platinum — very low 3DS internationally.",
                  ["g2a.com", "eneba.com"]),
    ],

    # ─── POLAND ────────────────────────────────────────────────────────
    "PL": [
        NonVBVBin("431286", "PKO Bank", "PL", "visa", "credit", "gold",
                  "conditional_vbv", 0.28, False,
                  "PKO Visa Gold — PSD2 exempt under 15 PLN (~3.50 EUR). No AVS.",
                  ["g2a.com", "eneba.com", "allegro.pl"]),
        NonVBVBin("516907", "mBank", "PL", "mastercard", "credit", "world",
                  "conditional_vbv", 0.25, False,
                  "mBank MC World — online bank, moderate 3DS. PLN transactions often exempt.",
                  ["g2a.com", "eneba.com"]),
        NonVBVBin("427604", "ING Poland", "PL", "visa", "credit", "gold",
                  "conditional_vbv", 0.25, False,
                  "ING PL Visa Gold — moderate 3DS, low-value exempt.",
                  ["g2a.com", "eneba.com"]),
    ],

    # ─── SWEDEN ────────────────────────────────────────────────────────
    "SE": [
        NonVBVBin("455000", "SEB", "SE", "visa", "credit", "gold",
                  "conditional_vbv", 0.30, False,
                  "SEB Visa Gold — PSD2 exempt under 300 SEK (~28 EUR). No AVS.",
                  ["g2a.com", "eneba.com"]),
        NonVBVBin("519651", "Nordea Sweden", "SE", "mastercard", "credit", "gold",
                  "conditional_vbv", 0.28, False,
                  "Nordea MC Gold — moderate 3DS, exempt on low-value.",
                  ["g2a.com", "eneba.com"]),
    ],

    # ─── IRELAND ───────────────────────────────────────────────────────
    "IE": [
        NonVBVBin("428903", "AIB", "IE", "visa", "credit", "gold",
                  "conditional_vbv", 0.32, True,
                  "AIB Visa Gold — PSD2 exempt under 30 EUR. AVS on some UK merchants.",
                  ["g2a.com", "amazon.co.uk"]),
        NonVBVBin("539930", "Bank of Ireland", "IE", "mastercard", "credit", "world",
                  "conditional_vbv", 0.30, True,
                  "BOI MC World — moderate 3DS, exempt on low-value.",
                  ["g2a.com", "eneba.com"]),
    ],

    # ─── PORTUGAL ──────────────────────────────────────────────────────
    "PT": [
        NonVBVBin("490720", "Millennium BCP", "PT", "visa", "credit", "gold",
                  "conditional_vbv", 0.28, False,
                  "BCP Visa Gold — PSD2 exempt under 30 EUR. No AVS.",
                  ["g2a.com", "eneba.com"]),
        NonVBVBin("533248", "Novo Banco", "PT", "mastercard", "credit", "gold",
                  "conditional_vbv", 0.25, False,
                  "Novo Banco MC Gold — moderate 3DS.",
                  ["g2a.com", "eneba.com"]),
    ],

    # ─── SOUTH AFRICA ──────────────────────────────────────────────────
    "ZA": [
        NonVBVBin("462742", "FNB", "ZA", "visa", "credit", "gold",
                  "non_vbv", 0.08, False,
                  "FNB Visa Gold — SA has low 3DS adoption. No PSD2. ZAR currency.",
                  ["g2a.com", "steam", "eneba.com"]),
        NonVBVBin("521442", "Standard Bank", "ZA", "mastercard", "credit", "gold",
                  "non_vbv", 0.10, False,
                  "Standard Bank MC Gold — low 3DS, good for international.",
                  ["g2a.com", "eneba.com"]),
        NonVBVBin("410120", "Nedbank", "ZA", "visa", "credit", "platinum",
                  "non_vbv", 0.08, False,
                  "Nedbank Visa Platinum — low 3DS, SA banking system lenient.",
                  ["g2a.com", "steam"]),
    ],

    # ─── SINGAPORE ─────────────────────────────────────────────────────
    "SG": [
        NonVBVBin("426101", "DBS Bank", "SG", "visa", "credit", "signature",
                  "non_vbv", 0.10, False,
                  "DBS Visa Signature — Singapore has low 3DS. No AVS. High limits.",
                  ["g2a.com", "amazon.sg", "steam"]),
        NonVBVBin("548814", "OCBC", "SG", "mastercard", "credit", "platinum",
                  "non_vbv", 0.10, False,
                  "OCBC MC Platinum — low 3DS, good for international.",
                  ["g2a.com", "eneba.com"]),
        NonVBVBin("411726", "UOB", "SG", "visa", "credit", "gold",
                  "non_vbv", 0.08, False,
                  "UOB Visa Gold — very low 3DS internationally.",
                  ["g2a.com", "steam"]),
    ],

    # ─── MALAYSIA ──────────────────────────────────────────────────────
    "MY": [
        NonVBVBin("421150", "Maybank", "MY", "visa", "credit", "gold",
                  "low_vbv", 0.15, False,
                  "Maybank Visa Gold — moderate 3DS. MYR currency. No AVS.",
                  ["g2a.com", "steam"]),
        NonVBVBin("526233", "CIMB", "MY", "mastercard", "credit", "platinum",
                  "low_vbv", 0.12, False,
                  "CIMB MC Platinum — lower 3DS than Maybank.",
                  ["g2a.com", "eneba.com"]),
    ],

    # ─── PHILIPPINES ───────────────────────────────────────────────────
    "PH": [
        NonVBVBin("448438", "BDO", "PH", "visa", "credit", "gold",
                  "non_vbv", 0.05, False,
                  "BDO Visa Gold — very low 3DS. PHP currency. Cross-border may limit.",
                  ["g2a.com", "steam"]),
        NonVBVBin("537522", "BPI", "PH", "mastercard", "credit", "gold",
                  "non_vbv", 0.05, False,
                  "BPI MC Gold — minimal 3DS on international.",
                  ["g2a.com", "eneba.com"]),
    ],

    # ─── CHILE ─────────────────────────────────────────────────────────
    "CL": [
        NonVBVBin("405612", "Banco de Chile", "CL", "visa", "credit", "gold",
                  "non_vbv", 0.04, False,
                  "Banco de Chile Visa Gold — virtually no 3DS. CLP currency.",
                  ["g2a.com", "steam"]),
        NonVBVBin("549009", "Banco Estado", "CL", "mastercard", "credit", "classic",
                  "non_vbv", 0.04, False,
                  "Banco Estado MC — government bank, no 3DS.",
                  ["g2a.com", "eneba.com"]),
    ],
}


# ═══════════════════════════════════════════════════════════════════════════
# COUNTRY DIFFICULTY RANKING
# ═══════════════════════════════════════════════════════════════════════════

COUNTRY_DIFFICULTY_RANKING = [
    {"rank": 1, "code": "US", "name": "United States", "difficulty": "easy",
     "reason": "No PSD2, optional 3DS, many non-VBV BINs, high merchant coverage"},
    {"rank": 2, "code": "JP", "name": "Japan", "difficulty": "easy",
     "reason": "Minimal 3DS adoption, no AVS, large issuers rarely enroll in VBV"},
    {"rank": 3, "code": "BR", "name": "Brazil", "difficulty": "easy",
     "reason": "Very low 3DS, no AVS, but cross-border decline risk from issuers"},
    {"rank": 4, "code": "MX", "name": "Mexico", "difficulty": "easy",
     "reason": "Very low 3DS, no AVS, but cross-border decline risk from issuers"},
    {"rank": 5, "code": "CA", "name": "Canada", "difficulty": "easy",
     "reason": "No PSD2, growing 3DS but still optional for most banks"},
    {"rank": 6, "code": "AU", "name": "Australia", "difficulty": "easy",
     "reason": "No PSD2, voluntary 3DS, good merchant coverage"},
    {"rank": 7, "code": "DE", "name": "Germany", "difficulty": "moderate",
     "reason": "PSD2 but slower adoption, no AVS, exempt under 30 EUR"},
    {"rank": 8, "code": "FR", "name": "France", "difficulty": "moderate",
     "reason": "PSD2 but high exemption rates, no AVS, CB co-branding helps"},
    {"rank": 9, "code": "BE", "name": "Belgium", "difficulty": "moderate",
     "reason": "PSD2 but exempt under 30 EUR, no AVS"},
    {"rank": 10, "code": "NL", "name": "Netherlands", "difficulty": "moderate",
     "reason": "PSD2, moderate 3DS, no AVS, credit card usage is lower"},
    {"rank": 11, "code": "IT", "name": "Italy", "difficulty": "moderate",
     "reason": "PSD2, moderate 3DS, no AVS, PostePay prepaid has high 3DS"},
    {"rank": 12, "code": "ES", "name": "Spain", "difficulty": "moderate",
     "reason": "PSD2, moderate 3DS, no AVS"},
    {"rank": 13, "code": "GB", "name": "United Kingdom", "difficulty": "moderate",
     "reason": "PSD2 enforced, but exemptions under £30. Credit < debit for 3DS"},
]


# ═══════════════════════════════════════════════════════════════════════════
# NON-VBV RECOMMENDATION ENGINE
# ═══════════════════════════════════════════════════════════════════════════

class NonVBVRecommendationEngine:
    """
    V7.0.2: Recommends optimal non-VBV BINs based on country, target merchant,
    amount, and card preferences.
    
    Usage:
        engine = NonVBVRecommendationEngine()
        
        # Get recommendations for a country
        recs = engine.recommend(country="US", target="g2a.com", amount=150)
        
        # Get all easy countries
        easy = engine.get_easy_countries()
        
        # Get country profile
        profile = engine.get_country_profile("FR")
    """
    
    def recommend(self,
                  country: str = None,
                  target: str = None,
                  amount: float = None,
                  card_type: str = "credit",
                  network: str = None,
                  max_3ds_rate: float = 0.30) -> Dict:
        """
        Get non-VBV BIN recommendations.
        
        Args:
            country: ISO country code (US, GB, FR, DE, etc.) or None for all
            target: Target merchant domain or None for general
            amount: Transaction amount in USD/EUR or None
            card_type: Preferred card type (credit, debit)
            network: Preferred network (visa, mastercard) or None for any
            max_3ds_rate: Maximum acceptable 3DS rate (default 0.30 = 30%)
            
        Returns:
            Dict with ranked recommendations, country profile, and strategy tips
        """
        results = {
            "country": country,
            "target": target,
            "amount": amount,
            "recommendations": [],
            "country_profile": None,
            "strategy_tips": [],
            "psd2_warning": False,
        }
        
        # Get country profile
        if country:
            country = country.upper()
            profile = COUNTRY_PROFILES.get(country)
            if profile:
                results["country_profile"] = {
                    "code": profile.code,
                    "name": profile.name,
                    "difficulty": profile.difficulty,
                    "psd2_enforced": profile.psd2_enforced,
                    "three_ds_base_rate": profile.three_ds_base_rate,
                    "avs_common": profile.avs_common,
                    "notes": profile.notes,
                    "recommended_targets": profile.recommended_targets,
                }
                if profile.psd2_enforced:
                    results["psd2_warning"] = True
                    results["strategy_tips"].append(
                        f"PSD2 ACTIVE in {profile.name} — keep transactions under "
                        f"30 EUR/GBP for SCA exemption"
                    )
        
        # Collect candidate BINs
        candidates = []
        if country and country in NON_VBV_BINS:
            candidates = NON_VBV_BINS[country]
        elif not country:
            # All countries
            for bins in NON_VBV_BINS.values():
                candidates.extend(bins)
        
        # Filter candidates
        filtered = []
        for b in candidates:
            # Filter by 3DS rate
            if b.three_ds_rate > max_3ds_rate:
                continue
            # Filter by card type
            if card_type and b.card_type != card_type:
                continue
            # Filter by network
            if network and b.network != network:
                continue
            
            # Score this BIN for the specific request
            score = 100.0
            match_reasons = []
            
            # 3DS rate scoring (lower = better)
            score -= b.three_ds_rate * 100  # e.g., 0.10 = -10 points
            
            # Target compatibility bonus
            if target:
                target_clean = target.lower().replace("www.", "")
                if target_clean in b.best_for:
                    score += 20
                    match_reasons.append(f"Recommended for {target_clean}")
            
            # Amount-based scoring
            if amount:
                # EU PSD2 exemption
                profile = COUNTRY_PROFILES.get(b.country)
                if profile and profile.psd2_enforced and amount <= 30:
                    score += 15
                    match_reasons.append("Under 30 EUR — PSD2 SCA exemption likely")
                elif profile and profile.psd2_enforced and amount > 30:
                    score -= 15
                    match_reasons.append("Over 30 EUR — PSD2 may trigger 3DS")
                
                # US amount scoring
                if not profile or not profile.psd2_enforced:
                    if amount <= 200:
                        score += 10
                        match_reasons.append("Low amount — reduced 3DS risk")
                    elif amount > 500:
                        score -= 10
                        match_reasons.append("High amount — increased 3DS risk")
            
            # Non-VBV bonus
            if b.vbv_status == "non_vbv":
                score += 15
                match_reasons.append("Confirmed non-VBV")
            elif b.vbv_status == "low_vbv":
                score += 8
                match_reasons.append("Low VBV enrollment rate")
            elif b.vbv_status == "conditional_vbv":
                score += 3
                match_reasons.append("VBV conditional on amount/merchant")
            
            # AVS factor
            if not b.avs_required:
                score += 5
                match_reasons.append("No AVS — billing address less critical")
            
            filtered.append({
                "bin": b.bin,
                "bank": b.bank,
                "country": b.country,
                "network": b.network,
                "card_type": b.card_type,
                "level": b.level,
                "vbv_status": b.vbv_status,
                "three_ds_rate": f"{b.three_ds_rate*100:.0f}%",
                "avs_required": b.avs_required,
                "notes": b.notes,
                "score": round(score, 1),
                "match_reasons": match_reasons,
            })
        
        # Sort by score descending
        filtered.sort(key=lambda x: x["score"], reverse=True)
        results["recommendations"] = filtered[:20]  # Top 20
        
        # Strategy tips
        if not results["strategy_tips"]:
            if country in ("US", "CA", "AU", "JP", "BR", "MX"):
                results["strategy_tips"].append(
                    "Non-PSD2 country — 3DS is optional and risk-based. Focus on credit cards."
                )
        
        if target:
            merchant_profile = MERCHANT_3DS_PATTERNS.get(target.lower().replace("www.", ""))
            if merchant_profile:
                results["strategy_tips"].append(
                    f"Merchant {target}: 3DS likelihood = {merchant_profile.likelihood.value}. "
                    f"{merchant_profile.notes}"
                )
        
        if amount and amount > 300:
            results["strategy_tips"].append(
                "Amount >$300 increases 3DS risk on most merchants. Split if possible."
            )
        
        results["total_bins_found"] = len(filtered)
        
        return results
    
    def get_easy_countries(self) -> List[Dict]:
        """Get countries ranked by ease of operation (lowest 3DS rates)"""
        return COUNTRY_DIFFICULTY_RANKING
    
    def get_country_profile(self, country_code: str) -> Optional[Dict]:
        """Get detailed profile for a specific country"""
        profile = COUNTRY_PROFILES.get(country_code.upper())
        if not profile:
            return None
        
        bins = NON_VBV_BINS.get(country_code.upper(), [])
        
        return {
            "code": profile.code,
            "name": profile.name,
            "difficulty": profile.difficulty,
            "psd2_enforced": profile.psd2_enforced,
            "three_ds_base_rate": f"{profile.three_ds_base_rate*100:.0f}%",
            "avs_common": profile.avs_common,
            "best_card_types": profile.best_card_types,
            "best_networks": profile.best_networks,
            "notes": profile.notes,
            "recommended_targets": profile.recommended_targets,
            "non_vbv_bins_count": len(bins),
            "non_vbv_bins": [
                {
                    "bin": b.bin,
                    "bank": b.bank,
                    "network": b.network,
                    "level": b.level,
                    "vbv_status": b.vbv_status,
                    "three_ds_rate": f"{b.three_ds_rate*100:.0f}%",
                    "notes": b.notes,
                }
                for b in bins
            ],
        }
    
    def get_bins_for_target(self, target: str, max_3ds_rate: float = 0.25) -> List[Dict]:
        """Get best non-VBV BINs for a specific target across all countries"""
        return self.recommend(
            target=target,
            max_3ds_rate=max_3ds_rate
        )["recommendations"]
    
    def get_all_non_vbv_bins(self, country: str = None) -> List[Dict]:
        """Get all non-VBV BINs, optionally filtered by country"""
        if country:
            bins = NON_VBV_BINS.get(country.upper(), [])
        else:
            bins = []
            for b_list in NON_VBV_BINS.values():
                bins.extend(b_list)
        
        return [
            {
                "bin": b.bin,
                "bank": b.bank,
                "country": b.country,
                "network": b.network,
                "card_type": b.card_type,
                "level": b.level,
                "vbv_status": b.vbv_status,
                "three_ds_rate": f"{b.three_ds_rate*100:.0f}%",
                "avs_required": b.avs_required,
                "notes": b.notes,
                "best_for": b.best_for,
            }
            for b in sorted(bins, key=lambda x: x.three_ds_rate)
        ]


# ═══════════════════════════════════════════════════════════════════════════
# CONVENIENCE EXPORTS
# ═══════════════════════════════════════════════════════════════════════════

def get_non_vbv_recommendations(country=None, target=None, amount=None,
                                 card_type="credit", network=None) -> Dict:
    """Quick non-VBV recommendations"""
    return NonVBVRecommendationEngine().recommend(
        country=country, target=target, amount=amount,
        card_type=card_type, network=network
    )

def get_non_vbv_country_profile(country_code: str) -> Optional[Dict]:
    """Get non-VBV country profile"""
    return NonVBVRecommendationEngine().get_country_profile(country_code)

def get_easy_countries() -> List[Dict]:
    """Get countries ranked by ease of operation"""
    return COUNTRY_DIFFICULTY_RANKING

def get_all_non_vbv_bins(country: str = None) -> List[Dict]:
    """Get all non-VBV BINs"""
    return NonVBVRecommendationEngine().get_all_non_vbv_bins(country)
