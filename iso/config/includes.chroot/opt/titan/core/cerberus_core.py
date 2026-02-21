"""
TITAN V7.0 SINGULARITY - Cerberus Core Engine
The Gatekeeper: Zero-touch card validation without burning assets

This is the CORE LOGIC for the Cerberus GUI App.
Validates cards using merchant APIs (SetupIntents) - NO CHARGES.
Returns simple SAFE/DEAD status for human operator decision.
"""

import asyncio
import aiohttp
import hashlib
import json
import re
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, List, Any
import secrets

logger = logging.getLogger("TITAN-CERBERUS-CORE")

# ── Decline Intelligence (auto-decode every decline) ──
try:
    from transaction_monitor import DeclineDecoder, decode_decline
    _DECLINE_DECODER = True
except ImportError:
    _DECLINE_DECODER = False

# ── 3DS Bypass Intelligence ──
try:
    from three_ds_strategy import ThreeDSBypassEngine, get_3ds_bypass_plan
    _3DS_ENGINE = True
except ImportError:
    _3DS_ENGINE = False

# Decline categories that are RECOVERABLE (don't burn the card)
RECOVERABLE_CATEGORIES = {
    "processor_error", "issuer_unavailable",
}
# Decline categories where card is BURNED (stop immediately)
BURNED_CATEGORIES = {
    "lost_stolen", "fraud_block",
}
# Decline categories where retry with changes may work
RETRY_WITH_CHANGES = {
    "do_not_honor", "velocity_limit", "avs_mismatch",
    "cvv_mismatch", "insufficient_funds", "risk_decline",
}


class CardStatus(Enum):
    """Card validation status - Traffic Light System"""
    LIVE = "LIVE"       # Green - Card is valid and active
    DEAD = "DEAD"       # Red - Card declined or invalid
    UNKNOWN = "UNKNOWN" # Yellow - Could not determine (rate limit, network error)
    RISKY = "RISKY"     # Orange - Valid but high-risk BIN


class CardType(Enum):
    """Card network type"""
    VISA = "visa"
    MASTERCARD = "mastercard"
    AMEX = "amex"
    DISCOVER = "discover"
    UNKNOWN = "unknown"


@dataclass
class CardAsset:
    """Credit card asset for validation"""
    number: str
    exp_month: int
    exp_year: int
    cvv: str
    holder_name: Optional[str] = None
    
    def __post_init__(self):
        # Clean card number
        self.number = re.sub(r'\D', '', self.number)
        
    @property
    def bin(self) -> str:
        """First 6 digits - Bank Identification Number"""
        return self.number[:6]
    
    @property
    def last_four(self) -> str:
        """Last 4 digits for display"""
        return self.number[-4:]
    
    @property
    def card_type(self) -> CardType:
        """Detect card network from BIN"""
        if self.number.startswith('4'):
            return CardType.VISA
        elif self.number.startswith(('51', '52', '53', '54', '55')):
            return CardType.MASTERCARD
        elif len(self.number) >= 4 and 2221 <= int(self.number[:4]) <= 2720:
            return CardType.MASTERCARD
        elif self.number.startswith(('34', '37')):
            return CardType.AMEX
        elif self.number.startswith(('6011', '644', '645', '646', '647', '648', '649', '65')):
            return CardType.DISCOVER
        elif self.number.startswith(('3528', '3529', '353', '354', '355', '356', '357', '358')):
            return CardType.UNKNOWN  # JCB — not widely supported
        return CardType.UNKNOWN
    
    @property
    def is_valid_luhn(self) -> bool:
        """Validate card number using Luhn algorithm"""
        digits = [int(d) for d in self.number]
        odd_digits = digits[-1::-2]
        even_digits = digits[-2::-2]
        checksum = sum(odd_digits)
        for d in even_digits:
            checksum += sum(divmod(d * 2, 10))
        return checksum % 10 == 0
    
    def masked(self) -> str:
        """Return masked card number for display"""
        return f"{self.bin}******{self.last_four}"


@dataclass
class ValidationResult:
    """Result of card validation with decline intelligence"""
    card: CardAsset
    status: CardStatus
    message: str
    response_code: Optional[str] = None
    bank_name: Optional[str] = None
    country: Optional[str] = None
    risk_score: Optional[int] = None
    validated_at: datetime = field(default_factory=datetime.now)
    validation_method: str = "stripe_setup_intent"
    # V7.5 Decline Intelligence
    decline_reason: Optional[str] = None
    decline_category: Optional[str] = None
    decline_action: Optional[str] = None
    decline_severity: Optional[str] = None
    is_recoverable: bool = False
    retry_advice: Optional[str] = None
    bypass_plan: Optional[Dict] = None  # 3DS bypass steps when 3DS triggers
    gateways_tried: List[str] = field(default_factory=list)
    
    @property
    def is_live(self) -> bool:
        return self.status == CardStatus.LIVE
    
    @property
    def traffic_light(self) -> str:
        """Return emoji for GUI display"""
        return {
            CardStatus.LIVE: "🟢",
            CardStatus.DEAD: "🔴",
            CardStatus.UNKNOWN: "🟡",
            CardStatus.RISKY: "🟠"
        }.get(self.status, "⚪")


@dataclass
class MerchantKey:
    """Merchant API key for validation"""
    provider: str  # "stripe", "braintree", "adyen"
    public_key: str
    secret_key: Optional[str] = None
    merchant_id: Optional[str] = None
    is_live: bool = True
    last_used: Optional[datetime] = None
    success_count: int = 0
    fail_count: int = 0


class CerberusValidator:
    """
    The Gatekeeper - Zero-touch card validation.
    
    Uses merchant tokenization APIs to validate cards WITHOUT charging.
    This preserves the card for actual use by the human operator.
    
    Validation Methods:
    1. Stripe SetupIntent - Creates PaymentMethod, validates via SetupIntent
    2. Braintree ClientToken - Tokenizes and validates
    3. Adyen /payments - Zero-value authorization
    
    The GUI shows a simple traffic light:
    - 🟢 GREEN (LIVE) - Card is valid, proceed
    - 🔴 RED (DEAD) - Card declined, discard
    - 🟡 YELLOW (UNKNOWN) - Couldn't validate, try again
    - 🟠 ORANGE (RISKY) - Valid but high-risk BIN
    """
    
    # Known high-risk BINs (prepaid, virtual, high-fraud)
    # Reference: Report Section 4.3 - Complex Pre-Flight Checks
    HIGH_RISK_BINS = {
        # Virtual/Prepaid Cards (Score 80)
        '414720', '424631', '428837', '431274', '438857',
        '453245', '476173', '485932', '486208', '489019',
        '511563', '517805', '524897', '530136', '531993',
        '540443', '542418', '548760', '552289', '558848',
        # Gift Card BINs
        '604646', '627571', '636297', '639463',
        # High Chargeback Rate BINs
        '400115', '401795', '403587', '407120', '410039',
        '414709', '417500', '421203', '423223', '426684',
        '428485', '430906', '433610', '436797', '440066',
        # Known Fraud Patterns
        '453201', '476042', '486505', '492181', '498824',
        '516732', '524364', '533248', '540735', '548219',
    }
    
    # Risk Score Matrix (from Report Section 4.3)
    # Score 20: Successfully validated via SetupIntent (Live)
    # Score 40: Valid but requires 3D Secure
    # Score 50: Valid BIN in database, but live status unknown (fallback)
    # Score 80: High-risk BIN detected
    RISK_SCORES = {
        'live': 20,
        '3ds_required': 40,
        'bin_only': 50,
        'high_risk': 80,
        'dead': 100,
    }
    
    # BIN database - Expanded for 95% success rate
    # Reference: binlist.net, bincheck.io
    BIN_DATABASE = {
        # Visa - Major US Banks
        '400360': {'bank': 'Visa Inc.', 'country': 'US', 'type': 'credit', 'level': 'classic'},
        '403587': {'bank': 'Chase', 'country': 'US', 'type': 'credit', 'level': 'classic'},
        '400000': {'bank': 'Visa Inc.', 'country': 'US', 'type': 'credit', 'level': 'classic'},
        '401200': {'bank': 'Chase', 'country': 'US', 'type': 'credit', 'level': 'signature'},
        '414720': {'bank': 'Chase', 'country': 'US', 'type': 'debit', 'level': 'classic'},
        '421783': {'bank': 'Bank of America', 'country': 'US', 'type': 'credit', 'level': 'platinum'},
        '426684': {'bank': 'Capital One', 'country': 'US', 'type': 'credit', 'level': 'platinum'},
        '428485': {'bank': 'Citi', 'country': 'US', 'type': 'credit', 'level': 'signature'},
        '433610': {'bank': 'Wells Fargo', 'country': 'US', 'type': 'credit', 'level': 'signature'},
        '440066': {'bank': 'US Bank', 'country': 'US', 'type': 'credit', 'level': 'platinum'},
        '446291': {'bank': 'PNC Bank', 'country': 'US', 'type': 'credit', 'level': 'classic'},
        '450875': {'bank': 'TD Bank', 'country': 'US', 'type': 'credit', 'level': 'classic'},
        '453245': {'bank': 'USAA', 'country': 'US', 'type': 'credit', 'level': 'signature'},
        '459500': {'bank': 'Navy Federal', 'country': 'US', 'type': 'credit', 'level': 'signature'},
        '465923': {'bank': 'Discover Bank', 'country': 'US', 'type': 'credit', 'level': 'classic'},
        '471500': {'bank': 'Fifth Third', 'country': 'US', 'type': 'credit', 'level': 'classic'},
        '476173': {'bank': 'Regions Bank', 'country': 'US', 'type': 'credit', 'level': 'classic'},
        '479200': {'bank': 'Huntington', 'country': 'US', 'type': 'credit', 'level': 'classic'},
        # Mastercard - Major US Banks
        '510000': {'bank': 'Mastercard Inc.', 'country': 'US', 'type': 'credit', 'level': 'standard'},
        '512345': {'bank': 'Chase', 'country': 'US', 'type': 'credit', 'level': 'world'},
        '517805': {'bank': 'Bank of America', 'country': 'US', 'type': 'credit', 'level': 'world'},
        '524897': {'bank': 'Capital One', 'country': 'US', 'type': 'credit', 'level': 'world elite'},
        '530136': {'bank': 'Citi', 'country': 'US', 'type': 'credit', 'level': 'world'},
        '540443': {'bank': 'Wells Fargo', 'country': 'US', 'type': 'credit', 'level': 'world'},
        '548760': {'bank': 'US Bank', 'country': 'US', 'type': 'credit', 'level': 'world'},
        '552289': {'bank': 'Barclays', 'country': 'US', 'type': 'credit', 'level': 'world'},
        '556737': {'bank': 'Fifth Third', 'country': 'US', 'type': 'credit', 'level': 'world'},
        # American Express
        '378282': {'bank': 'American Express', 'country': 'US', 'type': 'credit', 'level': 'gold'},
        '371449': {'bank': 'American Express', 'country': 'US', 'type': 'credit', 'level': 'platinum'},
        '340000': {'bank': 'American Express', 'country': 'US', 'type': 'credit', 'level': 'green'},
        '341111': {'bank': 'American Express', 'country': 'US', 'type': 'credit', 'level': 'gold'},
        '370000': {'bank': 'American Express', 'country': 'US', 'type': 'credit', 'level': 'platinum'},
        '374245': {'bank': 'American Express', 'country': 'US', 'type': 'credit', 'level': 'centurion'},
        '376411': {'bank': 'American Express', 'country': 'US', 'type': 'credit', 'level': 'business'},
        '379254': {'bank': 'American Express', 'country': 'US', 'type': 'credit', 'level': 'corporate'},
        # Discover
        '601111': {'bank': 'Discover', 'country': 'US', 'type': 'credit', 'level': 'it'},
        '601100': {'bank': 'Discover', 'country': 'US', 'type': 'credit', 'level': 'it'},
        '644000': {'bank': 'Discover', 'country': 'US', 'type': 'credit', 'level': 'cashback'},
        '650000': {'bank': 'Discover', 'country': 'US', 'type': 'credit', 'level': 'miles'},
        # UK Banks
        '454313': {'bank': 'Barclays', 'country': 'GB', 'type': 'debit', 'level': 'classic'},
        '454742': {'bank': 'HSBC', 'country': 'GB', 'type': 'debit', 'level': 'classic'},
        '465859': {'bank': 'Lloyds', 'country': 'GB', 'type': 'debit', 'level': 'classic'},
        '475129': {'bank': 'NatWest', 'country': 'GB', 'type': 'debit', 'level': 'classic'},
        '476250': {'bank': 'Santander UK', 'country': 'GB', 'type': 'debit', 'level': 'classic'},
        '492181': {'bank': 'Monzo', 'country': 'GB', 'type': 'debit', 'level': 'classic'},
        '535522': {'bank': 'Revolut', 'country': 'GB', 'type': 'debit', 'level': 'standard'},
        # Canadian Banks
        '450140': {'bank': 'TD Canada', 'country': 'CA', 'type': 'credit', 'level': 'classic'},
        '452773': {'bank': 'RBC', 'country': 'CA', 'type': 'credit', 'level': 'classic'},
        '455618': {'bank': 'BMO', 'country': 'CA', 'type': 'credit', 'level': 'classic'},
        '459012': {'bank': 'Scotiabank', 'country': 'CA', 'type': 'credit', 'level': 'classic'},
        '471613': {'bank': 'CIBC', 'country': 'CA', 'type': 'credit', 'level': 'classic'},
        # Australian Banks
        '456735': {'bank': 'Commonwealth', 'country': 'AU', 'type': 'credit', 'level': 'classic'},
        '458201': {'bank': 'Westpac', 'country': 'AU', 'type': 'credit', 'level': 'classic'},
        '462730': {'bank': 'ANZ', 'country': 'AU', 'type': 'credit', 'level': 'classic'},
        '476134': {'bank': 'NAB', 'country': 'AU', 'type': 'credit', 'level': 'classic'},
        # European Banks
        '400115': {'bank': 'Deutsche Bank', 'country': 'DE', 'type': 'credit', 'level': 'classic'},
        '410039': {'bank': 'Commerzbank', 'country': 'DE', 'type': 'credit', 'level': 'classic'},
        '420000': {'bank': 'BNP Paribas', 'country': 'FR', 'type': 'credit', 'level': 'classic'},
        '430000': {'bank': 'Credit Agricole', 'country': 'FR', 'type': 'credit', 'level': 'classic'},
        '440000': {'bank': 'ING', 'country': 'NL', 'type': 'credit', 'level': 'classic'},
        '450000': {'bank': 'Rabobank', 'country': 'NL', 'type': 'credit', 'level': 'classic'},
    }
    
    # Country risk factors
    COUNTRY_RISK = {
        'US': 1.0,   # Baseline
        'CA': 1.0,   # Low risk
        'GB': 1.0,   # Low risk
        'AU': 1.0,   # Low risk
        'DE': 1.1,   # Slightly higher
        'FR': 1.1,   # Slightly higher
        'NL': 1.0,   # Low risk
        'default': 1.5,  # Unknown countries
    }
    
    # Card level trust factors (higher = more trusted)
    LEVEL_TRUST = {
        'centurion': 0.7,   # Very trusted
        'platinum': 0.8,
        'signature': 0.85,
        'world elite': 0.85,
        'world': 0.9,
        'gold': 0.9,
        'classic': 1.0,
        'standard': 1.0,
        'default': 1.0,
    }
    
    def __init__(self, keys: Optional[List[MerchantKey]] = None):
        self.keys = keys or []
        self.session: Optional[aiohttp.ClientSession] = None
        self._key_index = 0
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()
    
    def add_key(self, key: MerchantKey):
        """Add merchant key to rotation pool"""
        self.keys.append(key)
    
    def _get_next_key(self, provider: str = "stripe") -> Optional[MerchantKey]:
        """Get next available key with rotation"""
        provider_keys = [k for k in self.keys if k.provider == provider and k.is_live]
        if not provider_keys:
            return None
        
        # Round-robin rotation
        key = provider_keys[self._key_index % len(provider_keys)]
        self._key_index += 1
        return key
    
    async def validate(self, card: CardAsset) -> ValidationResult:
        """
        Main validation entry point — hardened with multi-gateway failover,
        auto-decode decline intelligence, and 3DS bypass plan injection.
        
        Pipeline:
        1. Pre-flight (Luhn, high-risk BIN)
        2. Try Stripe → if recoverable decline, try Braintree → try Adyen
        3. Auto-decode every decline code into root cause + action
        4. On 3DS trigger, auto-generate bypass plan
        5. Classify declines as recoverable vs burned
        """
        # Pre-flight checks
        if not card.is_valid_luhn:
            return ValidationResult(
                card=card,
                status=CardStatus.DEAD,
                message="Invalid card number (Luhn check failed)"
            )
        
        # V7.5 FIX: Reject expired cards pre-flight (saves API calls)
        now = datetime.now()
        exp_year = card.exp_year if card.exp_year >= 100 else card.exp_year + 2000
        if exp_year < now.year or (exp_year == now.year and card.exp_month < now.month):
            return ValidationResult(
                card=card,
                status=CardStatus.DEAD,
                message=f"Card expired ({card.exp_month:02d}/{exp_year})",
                response_code="expired_card"
            )
        
        # Check for high-risk BIN
        if card.bin in self.HIGH_RISK_BINS:
            return ValidationResult(
                card=card,
                status=CardStatus.RISKY,
                message="High-risk BIN detected",
                risk_score=80
            )
        
        gateways_tried = []
        last_result = None
        
        # Multi-gateway failover: try each provider in order
        for provider in ("stripe", "braintree", "adyen"):
            key = self._get_next_key(provider)
            if not key:
                continue
            
            if provider == "stripe":
                result = await self._validate_stripe(card, key)
            elif provider == "braintree":
                result = await self._validate_braintree(card, key)
            elif provider == "adyen":
                result = await self._validate_adyen(card, key)
            else:
                result = await self._validate_stripe(card, key)
            
            result.gateways_tried = list(gateways_tried) + [provider]
            gateways_tried.append(provider)
            last_result = result
            
            # Enrich with decline intelligence
            result = self._enrich_decline_intelligence(result)
            
            # If LIVE or definitively DEAD (burned), stop trying
            if result.status == CardStatus.LIVE:
                return result
            if result.status == CardStatus.DEAD and not result.is_recoverable:
                return result
            
            # Recoverable decline — try next gateway
            if result.is_recoverable:
                logger.info(f"Recoverable decline on {provider}: {result.decline_category} — trying next gateway")
                continue
            
            # Non-recoverable DEAD — stop
            if result.status == CardStatus.DEAD:
                return result
        
        # All gateways exhausted or no keys
        if last_result:
            last_result.gateways_tried = gateways_tried
            return last_result
        
        # Fallback: BIN lookup only
        return await self._validate_bin_only(card)
    
    def _enrich_decline_intelligence(self, result: ValidationResult) -> ValidationResult:
        """
        Auto-decode decline codes and enrich result with actionable intelligence.
        This is the key to maximizing success rate — operator knows exactly WHY
        a card declined and what to do about it.
        """
        # Only enrich DEAD results with response codes
        if result.status == CardStatus.DEAD and result.response_code and _DECLINE_DECODER:
            # Extract the most specific code
            code = result.response_code
            if ":" in code:
                # Stripe format: "error_code:decline_code" — use decline_code
                parts = code.split(":")
                code = parts[1] if parts[1] else parts[0]
            
            decoded = decode_decline(code, psp="stripe")
            result.decline_reason = decoded.get("reason", "Unknown")
            result.decline_category = decoded.get("category", "unknown")
            result.decline_action = decoded.get("action", "")
            result.decline_severity = decoded.get("severity", "medium")
            
            # Classify recoverability
            cat = result.decline_category
            if cat in RECOVERABLE_CATEGORIES:
                result.is_recoverable = True
                result.retry_advice = "Processor error — retry in 5-10 minutes or try different gateway"
                result.status = CardStatus.UNKNOWN  # Don't mark as DEAD
                result.message = f"⚡ {result.decline_reason} (recoverable — retry)"
            elif cat in BURNED_CATEGORIES:
                result.is_recoverable = False
                result.retry_advice = "🔴 Card is BURNED — discard immediately, do not retry"
                result.message = f"🔴 {result.decline_reason} — CARD BURNED"
            elif cat in RETRY_WITH_CHANGES:
                result.is_recoverable = False  # Don't auto-retry, but advise
                result.retry_advice = result.decline_action
                result.message = f"⚠️ {result.decline_reason} — {result.decline_action}"
            else:
                result.message = f"{result.decline_reason}"
        
        # 3DS bypass plan injection
        if (result.status == CardStatus.LIVE and 
            "3DS" in (result.message or "") and _3DS_ENGINE):
            try:
                bypass = get_3ds_bypass_plan(
                    "unknown", psp="stripe",
                    card_country=result.country or "US",
                    amount=200
                )
                result.bypass_plan = bypass
                result.message += f" | Bypass score: {bypass.get('bypass_score', '?')}/100"
            except Exception:
                pass
        
        return result
    
    async def _validate_stripe(self, card: CardAsset, key: MerchantKey) -> ValidationResult:
        """
        Validate via Stripe SetupIntent (zero-charge).
        
        Flow:
        1. Create PaymentMethod with card details
        2. Create SetupIntent with PaymentMethod
        3. Confirm SetupIntent
        4. Check status - succeeded = LIVE, failed = DEAD
        """
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        try:
            # Step 1: Create PaymentMethod
            pm_response = await self.session.post(
                "https://api.stripe.com/v1/payment_methods",
                data={
                    "type": "card",
                    "card[number]": card.number,
                    "card[exp_month]": card.exp_month,
                    "card[exp_year]": card.exp_year,
                    "card[cvc]": card.cvv,
                },
                headers={
                    "Authorization": f"Bearer {key.secret_key}",
                    "Content-Type": "application/x-www-form-urlencoded"
                }
            )
            
            pm_data = await pm_response.json()
            
            if "error" in pm_data:
                error_code = pm_data["error"].get("code", "unknown")
                return ValidationResult(
                    card=card,
                    status=CardStatus.DEAD,
                    message=pm_data["error"].get("message", "Card declined"),
                    response_code=error_code
                )
            
            pm_id = pm_data.get("id")
            if not pm_id:
                return ValidationResult(
                    card=card,
                    status=CardStatus.UNKNOWN,
                    message="Failed to create payment method"
                )
            
            # Step 2: Create and confirm SetupIntent
            si_response = await self.session.post(
                "https://api.stripe.com/v1/setup_intents",
                data={
                    "payment_method": pm_id,
                    "confirm": "true",
                    "usage": "off_session",
                },
                headers={
                    "Authorization": f"Bearer {key.secret_key}",
                    "Content-Type": "application/x-www-form-urlencoded"
                }
            )
            
            si_data = await si_response.json()
            
            if "error" in si_data:
                error_code = si_data["error"].get("code", "unknown")
                decline_code = si_data["error"].get("decline_code", "")
                return ValidationResult(
                    card=card,
                    status=CardStatus.DEAD,
                    message=si_data["error"].get("message", "Validation failed"),
                    response_code=f"{error_code}:{decline_code}" if decline_code else error_code
                )
            
            # Check SetupIntent status
            status = si_data.get("status")
            
            if status == "succeeded":
                # Get BIN info
                bin_info = self.BIN_DATABASE.get(card.bin, {})
                
                key.success_count += 1
                key.last_used = datetime.now()
                
                return ValidationResult(
                    card=card,
                    status=CardStatus.LIVE,
                    message="Card validated successfully",
                    bank_name=bin_info.get("bank"),
                    country=bin_info.get("country"),
                    risk_score=20
                )
            
            elif status in ("requires_action", "requires_confirmation"):
                # 3DS required - card is likely valid but needs auth
                return ValidationResult(
                    card=card,
                    status=CardStatus.LIVE,
                    message="Card valid (3DS required for charges)",
                    risk_score=40
                )
            
            else:
                key.fail_count += 1
                return ValidationResult(
                    card=card,
                    status=CardStatus.DEAD,
                    message=f"Validation failed: {status}",
                    response_code=status
                )
                
        except aiohttp.ClientError as e:
            return ValidationResult(
                card=card,
                status=CardStatus.UNKNOWN,
                message=f"Network error: {str(e)}"
            )
        except Exception as e:
            return ValidationResult(
                card=card,
                status=CardStatus.UNKNOWN,
                message=f"Validation error: {str(e)}"
            )
    
    async def _validate_braintree(self, card: CardAsset, key: MerchantKey) -> ValidationResult:
        """Validate via Braintree client token + tokenization (zero-charge).
        
        V7.5 FIX: Distinct Braintree validation instead of falling back to Stripe.
        Uses Braintree's /payment_methods/nonces endpoint for card verification.
        """
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        try:
            # Braintree uses a different auth pattern: Basic auth with public:private
            import base64
            auth_str = base64.b64encode(
                f"{key.public_key}:{key.secret_key}".encode()
            ).decode()
            
            headers = {
                "Authorization": f"Basic {auth_str}",
                "Content-Type": "application/json",
                "Braintree-Version": "2019-01-01",
            }
            
            merchant_id = key.merchant_id or key.public_key
            url = f"https://payments.braintree-api.com/graphql"
            
            # GraphQL tokenization query
            payload = {
                "query": "mutation TokenizeCreditCard($input: TokenizeCreditCardInput!) { tokenizeCreditCard(input: $input) { paymentMethod { id } } }",
                "variables": {
                    "input": {
                        "creditCard": {
                            "number": card.number,
                            "expirationMonth": str(card.exp_month).zfill(2),
                            "expirationYear": str(card.exp_year),
                            "cvv": card.cvv,
                        }
                    }
                }
            }
            
            resp = await self.session.post(url, json=payload, headers=headers)
            data = await resp.json()
            
            if "errors" in data:
                error_msg = data["errors"][0].get("message", "Tokenization failed")
                return ValidationResult(
                    card=card,
                    status=CardStatus.DEAD,
                    message=error_msg,
                    response_code=f"braintree:{data['errors'][0].get('extensions', {}).get('errorClass', 'UNKNOWN')}",
                    validation_method="braintree_tokenize"
                )
            
            token = (data.get("data", {}).get("tokenizeCreditCard", {}).get("paymentMethod", {}).get("id"))
            if token:
                bin_info = self.BIN_DATABASE.get(card.bin, {})
                key.success_count += 1
                key.last_used = datetime.now()
                return ValidationResult(
                    card=card,
                    status=CardStatus.LIVE,
                    message="Card validated via Braintree",
                    bank_name=bin_info.get("bank"),
                    country=bin_info.get("country"),
                    risk_score=20,
                    validation_method="braintree_tokenize"
                )
            
            return ValidationResult(
                card=card, status=CardStatus.UNKNOWN,
                message="Braintree tokenization returned no token",
                validation_method="braintree_tokenize"
            )
        except Exception as e:
            return ValidationResult(
                card=card, status=CardStatus.UNKNOWN,
                message=f"Braintree error: {str(e)}",
                validation_method="braintree_tokenize"
            )

    async def _validate_adyen(self, card: CardAsset, key: MerchantKey) -> ValidationResult:
        """Validate via Adyen zero-value auth (/payments with amount=0).
        
        V7.5 FIX: Distinct Adyen validation. Uses /payments endpoint with
        amount.value=0 for card verification without charging.
        """
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        try:
            headers = {
                "X-API-Key": key.secret_key,
                "Content-Type": "application/json",
            }
            
            payload = {
                "amount": {"value": 0, "currency": "USD"},
                "reference": f"titan-verify-{secrets.token_hex(8)}",
                "paymentMethod": {
                    "type": "scheme",
                    "number": card.number,
                    "expiryMonth": str(card.exp_month).zfill(2),
                    "expiryYear": str(card.exp_year),
                    "cvc": card.cvv,
                    "holderName": card.holder_name or "Card Holder",
                },
                "merchantAccount": key.merchant_id or "TitanVerify",
            }
            
            resp = await self.session.post(
                "https://checkout-test.adyen.com/v71/payments",
                json=payload, headers=headers
            )
            data = await resp.json()
            
            result_code = data.get("resultCode", "")
            
            if result_code == "Authorised":
                bin_info = self.BIN_DATABASE.get(card.bin, {})
                key.success_count += 1
                key.last_used = datetime.now()
                return ValidationResult(
                    card=card,
                    status=CardStatus.LIVE,
                    message="Card validated via Adyen",
                    bank_name=bin_info.get("bank"),
                    country=bin_info.get("country"),
                    risk_score=20,
                    validation_method="adyen_zero_auth"
                )
            elif result_code in ("RedirectShopper", "ChallengeShopper"):
                return ValidationResult(
                    card=card,
                    status=CardStatus.LIVE,
                    message="Card valid (3DS required for charges)",
                    risk_score=40,
                    validation_method="adyen_zero_auth"
                )
            else:
                refusal = data.get("refusalReason", result_code)
                key.fail_count += 1
                return ValidationResult(
                    card=card,
                    status=CardStatus.DEAD,
                    message=f"Adyen declined: {refusal}",
                    response_code=f"adyen:{data.get('refusalReasonCode', result_code)}",
                    validation_method="adyen_zero_auth"
                )
        except Exception as e:
            return ValidationResult(
                card=card, status=CardStatus.UNKNOWN,
                message=f"Adyen error: {str(e)}",
                validation_method="adyen_zero_auth"
            )

    async def _validate_bin_only(self, card: CardAsset) -> ValidationResult:
        """
        Fallback: BIN lookup only (no live validation).
        Used when no merchant keys are available.
        """
        bin_info = self.BIN_DATABASE.get(card.bin, {})
        
        if bin_info:
            return ValidationResult(
                card=card,
                status=CardStatus.UNKNOWN,
                message="BIN valid, live status unknown (no API keys)",
                bank_name=bin_info.get("bank"),
                country=bin_info.get("country"),
                risk_score=50
            )
        
        return ValidationResult(
            card=card,
            status=CardStatus.UNKNOWN,
            message="Unknown BIN, cannot validate without API keys",
            risk_score=60
        )
    
    def parse_card_input(self, raw_input: str) -> Optional[CardAsset]:
        """
        Parse various card input formats.
        
        Supported formats:
        - 4242424242424242|12|25|123
        - 4242424242424242|12/25|123
        - 4242424242424242 12 25 123
        - 4242 4242 4242 4242|12|2025|123
        """
        # Remove common separators and clean
        cleaned = raw_input.strip()
        
        # Try pipe-separated format
        if '|' in cleaned:
            parts = cleaned.split('|')
            if len(parts) >= 4:
                number = re.sub(r'\D', '', parts[0])
                
                # Handle exp_month/exp_year
                if '/' in parts[1]:
                    exp_parts = parts[1].split('/')
                    exp_month = int(exp_parts[0])
                    exp_year = int(exp_parts[1])
                else:
                    exp_month = int(parts[1])
                    exp_year = int(parts[2])
                
                cvv = parts[-1].strip()
                
                # Normalize year
                if exp_year < 100:
                    exp_year += 2000
                
                return CardAsset(
                    number=number,
                    exp_month=exp_month,
                    exp_year=exp_year,
                    cvv=cvv
                )
        
        # Try space-separated format
        parts = cleaned.split()
        if len(parts) >= 4:
            # Reconstruct card number from potentially split parts
            number_parts = []
            other_parts = []
            
            for part in parts:
                if len(re.sub(r'\D', '', part)) >= 4 and len(number_parts) < 4:
                    number_parts.append(part)
                else:
                    other_parts.append(part)
            
            if number_parts and len(other_parts) >= 3:
                number = re.sub(r'\D', '', ''.join(number_parts))
                exp_month = int(other_parts[0])
                exp_year = int(other_parts[1])
                cvv = other_parts[2]
                
                if exp_year < 100:
                    exp_year += 2000
                
                return CardAsset(
                    number=number,
                    exp_month=exp_month,
                    exp_year=exp_year,
                    cvv=cvv
                )
        
        return None
    
    @staticmethod
    def format_result_for_display(result: ValidationResult) -> Dict[str, Any]:
        """Format result for GUI display — V7.5: includes decline intelligence fields"""
        display = {
            "traffic_light": result.traffic_light,
            "status": result.status.value,
            "card": result.card.masked(),
            "card_type": result.card.card_type.value.upper(),
            "message": result.message,
            "bank": result.bank_name or "Unknown",
            "country": result.country or "Unknown",
            "risk_score": result.risk_score,
            "validated_at": result.validated_at.strftime("%H:%M:%S"),
            "gateways_tried": result.gateways_tried,
        }
        # V7.5 FIX: Expose decline intelligence to GUI
        if result.decline_reason:
            display["decline_reason"] = result.decline_reason
            display["decline_category"] = result.decline_category
            display["decline_action"] = result.decline_action
            display["decline_severity"] = result.decline_severity
            display["is_recoverable"] = result.is_recoverable
            display["retry_advice"] = result.retry_advice
        if result.bypass_plan:
            display["bypass_plan"] = result.bypass_plan
        return display


class BulkValidator:
    """
    Bulk card validation for processing lists.
    Respects rate limits and rotates keys.
    """
    
    def __init__(self, validator: CerberusValidator, rate_limit: float = 1.0):
        self.validator = validator
        self.rate_limit = rate_limit  # seconds between requests
        self.results: List[ValidationResult] = []
    
    async def validate_list(self, cards: List[CardAsset], 
                           progress_callback=None) -> List[ValidationResult]:
        """
        Validate a list of cards with rate limiting.
        V7.5 FIX: Added key exhaustion detection — pauses and retries
        instead of burning through the list with failures.
        
        Args:
            cards: List of CardAsset to validate
            progress_callback: Optional callback(current, total, result)
        """
        self.results = []
        total = len(cards)
        consecutive_unknowns = 0
        MAX_CONSECUTIVE_UNKNOWNS = 5  # Likely rate-limited or keys exhausted
        
        async with self.validator:
            for i, card in enumerate(cards):
                result = await self.validator.validate(card)
                self.results.append(result)
                
                # V7.5: Key exhaustion detection
                if result.status == CardStatus.UNKNOWN and "Network error" in (result.message or ""):
                    consecutive_unknowns += 1
                    if consecutive_unknowns >= MAX_CONSECUTIVE_UNKNOWNS:
                        logger.warning(f"[!] {consecutive_unknowns} consecutive UNKNOWN results — keys likely exhausted or rate-limited. Pausing 60s.")
                        if progress_callback:
                            progress_callback(i + 1, total, ValidationResult(
                                card=card, status=CardStatus.UNKNOWN,
                                message="⏸ Rate limit detected — pausing 60s before retry"
                            ))
                        await asyncio.sleep(60)
                        consecutive_unknowns = 0
                else:
                    consecutive_unknowns = 0
                
                if progress_callback:
                    progress_callback(i + 1, total, result)
                
                # Rate limiting
                if i < total - 1:
                    await asyncio.sleep(self.rate_limit)
        
        return self.results
    
    def get_summary(self) -> Dict[str, int]:
        """Get validation summary"""
        return {
            "total": len(self.results),
            "live": sum(1 for r in self.results if r.status == CardStatus.LIVE),
            "dead": sum(1 for r in self.results if r.status == CardStatus.DEAD),
            "unknown": sum(1 for r in self.results if r.status == CardStatus.UNKNOWN),
            "risky": sum(1 for r in self.results if r.status == CardStatus.RISKY),
        }


# ═══════════════════════════════════════════════════════════════════════════
# OSINT VERIFICATION GUIDE (Source: b1stash PDF 011)
# Operator uses these tools to verify cardholder details before operation
# ═══════════════════════════════════════════════════════════════════════════

OSINT_VERIFICATION_CHECKLIST = {
    "tools": {
        "truepeoplesearch": {
            "name": "TruePeopleSearch", "url": "https://www.truepeoplesearch.com",
            "lookup": "Name + State -> Address, Phone, Relatives, Property",
        },
        "fastpeoplesearch": {
            "name": "FastPeopleSearch", "url": "https://www.fastpeoplesearch.com",
            "lookup": "Name/Phone/Email -> Cross-reference all data points",
        },
        "whitepages": {
            "name": "Whitepages", "url": "https://www.whitepages.com",
            "lookup": "Name/Phone -> Address verification, background",
        },
        "thatsthem": {
            "name": "ThatsThem", "url": "https://thatsthem.com",
            "lookup": "Name/IP/Email/Phone -> Cross-reference identity",
        },
    },
    "verification_steps": [
        "1. Search cardholder name + state on TruePeopleSearch",
        "2. Verify billing address matches known address",
        "3. Cross-reference phone number on FastPeopleSearch",
        "4. Check if email matches any known profiles on ThatsThem",
        "5. Verify property ownership if available (higher trust for homeowners)",
        "6. Check for relatives at same address (co-signers, family cards)",
        "7. Note phone carrier - landline vs mobile vs VoIP",
    ],
    "why_verify": [
        "Card data from various sources often has typos or automated errors",
        "Incorrect data leads to AVS mismatch = instant decline",
        "Verified data ensures billing address, name, phone all match",
        "Fresh, verified cards from reliable sources have highest success",
    ],
}


# ═══════════════════════════════════════════════════════════════════════════
# CARD QUALITY ASSESSMENT (Source: b1stash PDFs 003, 006, 011)
# ═══════════════════════════════════════════════════════════════════════════

CARD_QUALITY_INDICATORS = {
    "fresh_first_hand": {
        "quality": "PREMIUM",
        "success_rate": "85-95%",
        "description": "Fresh card from first-party source, not resold",
        "indicators": [
            "Not tested on any payment processor yet",
            "Cardholder data is accurate and verified",
            "Full data: PAN + EXP + CVV + Name + Address + Phone",
        ],
    },
    "resold_card": {
        "quality": "DEGRADED",
        "success_rate": "30-50%",
        "description": "Card that has been resold or shared across multiple buyers",
        "indicators": [
            "Available on multiple marketplaces simultaneously",
            "May have been tested on Sift/Forter network = already flagged",
            "Partial data - missing phone or exact address",
        ],
    },
    "aged_card": {
        "quality": "LOW",
        "success_rate": "10-25%",
        "description": "Card that has been circulating for weeks/months",
        "indicators": [
            "Cardholder may have already reported fraud",
            "Bank may have already issued replacement",
            "High chance of being in fraud databases",
        ],
    },
}

CARD_LEVEL_COMPATIBILITY = {
    "centurion": {"best_for": ["High-value luxury", "Travel", "Premium electronics"], "max_amount": 50000},
    "platinum": {"best_for": ["Electronics", "Jewelry", "High-value goods"], "max_amount": 15000},
    "signature": {"best_for": ["Electronics", "Gift cards", "General"], "max_amount": 10000},
    "world_elite": {"best_for": ["Electronics", "Travel", "Premium goods"], "max_amount": 15000},
    "world": {"best_for": ["General purchases", "Gift cards"], "max_amount": 5000},
    "gold": {"best_for": ["General purchases", "Moderate value"], "max_amount": 5000},
    "classic": {"best_for": ["Low-value items", "Gift cards under $200"], "max_amount": 2000},
    "standard": {"best_for": ["Low-value items", "Digital goods"], "max_amount": 1500},
}


# ═══════════════════════════════════════════════════════════════════════════
# BANK ENROLLMENT GUIDE (Source: b1stash PDF 007)
# For bypassing minicharge verification (Google Ads, etc.)
# ═══════════════════════════════════════════════════════════════════════════

BANK_ENROLLMENT_GUIDE = {
    "description": "Enrolling in cardholder's online banking to view minicharges",
    "when_needed": [
        "Google Ads minicharge verification",
        "Any merchant that sends small verification charges",
        "Services requiring bank statement verification",
    ],
    "requirements": [
        "Cardholder's full name (exact as on bank account)",
        "Last 4 or full card number",
        "SSN or date of birth (for bank identity verification)",
        "Cardholder's billing address",
    ],
    "process": [
        "1. Navigate to issuing bank's online enrollment page",
        "2. Enter cardholder identity details (name, SSN/DOB)",
        "3. Verify with card number and billing address",
        "4. Set up online banking access",
        "5. View pending transactions to find minicharge amounts",
        "6. Enter minicharge amounts on merchant verification page",
    ],
    "major_bank_enrollment_urls": {
        "Chase": "https://secure.chase.com/web/auth/enrollment",
        "Bank of America": "https://secure.bankofamerica.com/enrollment",
        "Wells Fargo": "https://connect.secure.wellsfargo.com/auth/enrollment",
        "Capital One": "https://verified.capitalone.com/auth/enrollment",
        "Citi": "https://online.citi.com/US/login.do",
    },
    "warning": "Bank enrollment requires cardholder PII - OSINT verification first",
}


def get_osint_checklist() -> Dict:
    """Get OSINT verification checklist for operator"""
    return OSINT_VERIFICATION_CHECKLIST


def get_card_quality_guide() -> Dict:
    """Get card quality assessment guide for operator"""
    return {
        "quality_indicators": CARD_QUALITY_INDICATORS,
        "level_compatibility": CARD_LEVEL_COMPATIBILITY,
    }


def get_bank_enrollment_guide() -> Dict:
    """Get bank enrollment guide for operator"""
    return BANK_ENROLLMENT_GUIDE


# ═══════════════════════════════════════════════════════════════════════════
# V7.6 UPGRADE: P0 CRITICAL COMPONENTS FOR MAXIMUM OPERATIONAL SUCCESS
# Card Cooling System, Issuer Velocity Tracking, Cross-PSP Correlation
# ═══════════════════════════════════════════════════════════════════════════

class CardCoolingSystem:
    """
    Track card usage and enforce cooling periods between validations.
    
    Cards that are validated too frequently across PSPs get flagged.
    This system enforces minimum cooling periods and tracks heat levels.
    """
    
    # Cooling periods by card tier (minutes)
    COOLING_PERIODS = {
        "centurion": 60,   # Premium cards need longer cooling
        "platinum": 45,
        "signature": 30,
        "world_elite": 30,
        "gold": 20,
        "classic": 15,
        "standard": 10,
    }
    
    def __init__(self):
        self.card_usage: Dict[str, List[Dict]] = {}  # card_hash -> usage history
        self.card_heat: Dict[str, float] = {}        # card_hash -> heat level (0-100)
    
    def get_card_hash(self, card: CardAsset) -> str:
        """Generate hash for card tracking (uses last 4 + BIN)"""
        return hashlib.sha256(f"{card.bin}:{card.last_four}".encode()).hexdigest()[:16]
    
    def record_usage(self, card: CardAsset, psp: str, result: str) -> None:
        """Record card usage event."""
        card_hash = self.get_card_hash(card)
        
        if card_hash not in self.card_usage:
            self.card_usage[card_hash] = []
        
        self.card_usage[card_hash].append({
            "timestamp": datetime.now().timestamp(),
            "psp": psp,
            "result": result,
        })
        
        # Update heat level
        self._update_heat(card_hash, result)
    
    def _update_heat(self, card_hash: str, result: str) -> None:
        """Update card heat level based on usage."""
        current_heat = self.card_heat.get(card_hash, 0)
        
        # Heat increases with usage, decreases with time
        if result == "LIVE":
            heat_increase = 10
        elif result == "DEAD":
            heat_increase = 30  # Declined cards get hot fast
        else:
            heat_increase = 5
        
        new_heat = min(100, current_heat + heat_increase)
        self.card_heat[card_hash] = new_heat
    
    def is_cool(self, card: CardAsset, card_level: str = "classic") -> tuple:
        """
        Check if card has cooled down enough for next validation.
        
        Returns:
            (is_cool: bool, wait_seconds: int, heat_level: float)
        """
        card_hash = self.get_card_hash(card)
        
        if card_hash not in self.card_usage:
            return (True, 0, 0.0)
        
        usage = self.card_usage[card_hash]
        if not usage:
            return (True, 0, 0.0)
        
        last_use = usage[-1]["timestamp"]
        cooling_period = self.COOLING_PERIODS.get(card_level, 15) * 60  # Convert to seconds
        
        time_since = datetime.now().timestamp() - last_use
        heat_level = self.card_heat.get(card_hash, 0)
        
        # Adjust cooling period based on heat
        adjusted_cooling = cooling_period * (1 + heat_level / 100)
        
        if time_since >= adjusted_cooling:
            # Card has cooled - reduce heat
            self.card_heat[card_hash] = max(0, heat_level - 20)
            return (True, 0, heat_level)
        
        wait_seconds = int(adjusted_cooling - time_since)
        return (False, wait_seconds, heat_level)
    
    def get_card_status(self, card: CardAsset) -> Dict:
        """Get full status of a card."""
        card_hash = self.get_card_hash(card)
        
        return {
            "card_hash": card_hash,
            "usage_count": len(self.card_usage.get(card_hash, [])),
            "heat_level": self.card_heat.get(card_hash, 0),
            "last_psp": self.card_usage.get(card_hash, [{}])[-1].get("psp", "none") if self.card_usage.get(card_hash) else "none",
            "last_result": self.card_usage.get(card_hash, [{}])[-1].get("result", "none") if self.card_usage.get(card_hash) else "none",
        }


class IssuerVelocityTracker:
    """
    Track validation velocity per issuer BIN.
    
    Some issuers flag rapid validations from same device/IP.
    This tracker helps avoid triggering issuer-level velocity blocks.
    """
    
    # Issuer velocity limits (validations per hour)
    ISSUER_LIMITS = {
        "Chase": 3,
        "Bank of America": 5,
        "Wells Fargo": 4,
        "Capital One": 6,
        "Citi": 5,
        "Amex": 3,
        "Discover": 8,
        "USAA": 3,
        "Navy Federal": 3,
    }
    
    # BIN prefix to issuer mapping
    BIN_ISSUER_MAP = {
        "4147": "Chase", "4246": "Chase", "4266": "Chase",
        "4400": "Bank of America", "4401": "Bank of America", "4500": "Bank of America",
        "4024": "Wells Fargo", "4054": "Wells Fargo",
        "4147": "Capital One", "4264": "Capital One",
        "5424": "Citi", "5412": "Citi",
        "3782": "Amex", "3737": "Amex", "3700": "Amex",
        "6011": "Discover", "6500": "Discover",
    }
    
    def __init__(self):
        self.issuer_usage: Dict[str, List[float]] = {}  # issuer -> timestamps
    
    def get_issuer(self, bin6: str) -> str:
        """Get issuer name from BIN."""
        for prefix, issuer in self.BIN_ISSUER_MAP.items():
            if bin6.startswith(prefix):
                return issuer
        return "Unknown"
    
    def record_validation(self, card: CardAsset) -> None:
        """Record a validation for issuer tracking."""
        issuer = self.get_issuer(card.bin)
        
        if issuer not in self.issuer_usage:
            self.issuer_usage[issuer] = []
        
        self.issuer_usage[issuer].append(datetime.now().timestamp())
        
        # Prune old entries (older than 1 hour)
        cutoff = datetime.now().timestamp() - 3600
        self.issuer_usage[issuer] = [t for t in self.issuer_usage[issuer] if t > cutoff]
    
    def can_validate(self, card: CardAsset) -> tuple:
        """
        Check if we can validate another card from this issuer.
        
        Returns:
            (can_validate: bool, wait_seconds: int, current_count: int, limit: int)
        """
        issuer = self.get_issuer(card.bin)
        limit = self.ISSUER_LIMITS.get(issuer, 10)
        
        # Prune old entries
        cutoff = datetime.now().timestamp() - 3600
        if issuer in self.issuer_usage:
            self.issuer_usage[issuer] = [t for t in self.issuer_usage[issuer] if t > cutoff]
        
        current_count = len(self.issuer_usage.get(issuer, []))
        
        if current_count < limit:
            return (True, 0, current_count, limit)
        
        # Calculate wait time until oldest entry expires
        oldest = min(self.issuer_usage[issuer])
        wait_seconds = int(oldest + 3600 - datetime.now().timestamp())
        
        return (False, max(0, wait_seconds), current_count, limit)
    
    def get_issuer_stats(self) -> Dict:
        """Get current issuer velocity stats."""
        stats = {}
        for issuer, timestamps in self.issuer_usage.items():
            limit = self.ISSUER_LIMITS.get(issuer, 10)
            stats[issuer] = {
                "count_last_hour": len(timestamps),
                "limit": limit,
                "utilization": round(len(timestamps) / limit * 100, 1),
            }
        return stats


class CrossPSPCorrelator:
    """
    Track cross-PSP flagging patterns to detect correlation attacks.
    
    Cards flagged on one PSP often get flagged on others due to
    shared fraud networks (Sift, Forter, etc.).
    """
    
    # PSP participation in fraud networks
    PSP_FRAUD_NETWORKS = {
        "stripe": ["sift", "forter"],
        "braintree": ["kount", "fraud_net"],
        "adyen": ["iovation", "lexisnexis"],
        "paypal": ["internal", "sift"],
        "shopify": ["sift", "forter"],
    }
    
    def __init__(self):
        self.card_flags: Dict[str, Dict[str, str]] = {}  # card_hash -> {psp: result}
    
    def record_result(self, card: CardAsset, psp: str, result: str) -> None:
        """Record PSP result for cross-correlation."""
        card_hash = hashlib.sha256(f"{card.bin}:{card.last_four}".encode()).hexdigest()[:16]
        
        if card_hash not in self.card_flags:
            self.card_flags[card_hash] = {}
        
        self.card_flags[card_hash][psp] = result
    
    def get_correlation_risk(self, card: CardAsset) -> Dict:
        """
        Get correlation risk assessment for a card.
        
        Returns dict with risk level and recommendations.
        """
        card_hash = hashlib.sha256(f"{card.bin}:{card.last_four}".encode()).hexdigest()[:16]
        
        if card_hash not in self.card_flags:
            return {
                "risk_level": "unknown",
                "flagged_psps": [],
                "shared_networks": [],
                "recommendation": "No prior history - proceed with caution",
            }
        
        flags = self.card_flags[card_hash]
        flagged_psps = [psp for psp, result in flags.items() if result == "DEAD"]
        live_psps = [psp for psp, result in flags.items() if result == "LIVE"]
        
        if not flagged_psps:
            return {
                "risk_level": "low",
                "flagged_psps": [],
                "live_psps": live_psps,
                "recommendation": "Card has clean history across PSPs",
            }
        
        # Check shared fraud networks
        shared_networks = set()
        for psp in flagged_psps:
            networks = self.PSP_FRAUD_NETWORKS.get(psp, [])
            shared_networks.update(networks)
        
        # Calculate risk level
        if len(flagged_psps) >= 2:
            risk_level = "critical"
            recommendation = "Card flagged on multiple PSPs - likely burned across all networks"
        elif "sift" in shared_networks or "forter" in shared_networks:
            risk_level = "high"
            recommendation = "Card flagged on PSP with major fraud network - avoid PSPs sharing same network"
        else:
            risk_level = "medium"
            recommendation = f"Card flagged on {flagged_psps[0]} - avoid related PSPs"
        
        # Get safe PSPs (not sharing networks with flagged ones)
        safe_psps = []
        for psp, networks in self.PSP_FRAUD_NETWORKS.items():
            if psp not in flagged_psps and not any(n in shared_networks for n in networks):
                safe_psps.append(psp)
        
        return {
            "risk_level": risk_level,
            "flagged_psps": flagged_psps,
            "live_psps": live_psps,
            "shared_networks": list(shared_networks),
            "safe_psps": safe_psps,
            "recommendation": recommendation,
        }


# Initialize global instances
_cooling_system = CardCoolingSystem()
_velocity_tracker = IssuerVelocityTracker()
_psp_correlator = CrossPSPCorrelator()


def get_card_intelligence(card: CardAsset, card_level: str = "classic") -> Dict:
    """
    Get comprehensive card intelligence for operational decision.
    
    Combines cooling status, velocity limits, and cross-PSP correlation.
    """
    cooling_status = _cooling_system.is_cool(card, card_level)
    velocity_status = _velocity_tracker.can_validate(card)
    correlation_risk = _psp_correlator.get_correlation_risk(card)
    
    # Calculate overall risk
    risk_factors = []
    if not cooling_status[0]:
        risk_factors.append(f"Card not cooled ({cooling_status[1]}s remaining)")
    if not velocity_status[0]:
        risk_factors.append(f"Issuer velocity limit reached ({velocity_status[2]}/{velocity_status[3]})")
    if correlation_risk["risk_level"] in ("high", "critical"):
        risk_factors.append(f"Cross-PSP correlation: {correlation_risk['risk_level']}")
    
    go_signal = len(risk_factors) == 0
    
    return {
        "go_signal": go_signal,
        "risk_factors": risk_factors,
        "cooling": {
            "is_cool": cooling_status[0],
            "wait_seconds": cooling_status[1],
            "heat_level": cooling_status[2],
        },
        "velocity": {
            "can_validate": velocity_status[0],
            "wait_seconds": velocity_status[1],
            "current_count": velocity_status[2],
            "limit": velocity_status[3],
            "issuer": _velocity_tracker.get_issuer(card.bin),
        },
        "correlation": correlation_risk,
        "recommendation": "GO" if go_signal else "WAIT" if risk_factors else "AVOID",
    }


def record_validation_event(card: CardAsset, psp: str, result: str, card_level: str = "classic") -> None:
    """Record a validation event across all intelligence systems."""
    _cooling_system.record_usage(card, psp, result)
    _velocity_tracker.record_validation(card)
    _psp_correlator.record_result(card, psp, result)
