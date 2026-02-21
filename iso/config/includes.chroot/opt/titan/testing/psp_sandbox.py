#!/usr/bin/env python3
"""
TITAN V7.0 PSP Sandbox - Payment Service Provider Emulators

Emulates real PSP APIs for testing without hitting production endpoints.
Implements realistic decline logic, fraud detection, and 3DS challenges.

WARNING: This module is for TESTING ONLY. It uses simulated PSP responses
and test card numbers. Do NOT import this module in production code paths.
"""

import os as _os
if _os.environ.get("TITAN_PRODUCTION") == "1":
    raise ImportError(
        "psp_sandbox.py cannot be imported in production mode. "
        "Set TITAN_PRODUCTION=0 or unset it for testing."
    )

import hashlib
import json
import random
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class DeclineReason(Enum):
    """Standard decline reason codes across PSPs"""
    APPROVED = "approved"
    
    # Card Issues
    INSUFFICIENT_FUNDS = "insufficient_funds"
    CARD_DECLINED = "card_declined"
    EXPIRED_CARD = "expired_card"
    INVALID_CVV = "invalid_cvv"
    INVALID_NUMBER = "invalid_number"
    LOST_STOLEN = "lost_stolen"
    PICKUP_CARD = "pickup_card"
    
    # Fraud Detection
    FRAUD_SUSPECTED = "fraud_suspected"
    HIGH_RISK = "high_risk"
    VELOCITY_EXCEEDED = "velocity_exceeded"
    BLACKLISTED = "blacklisted"
    
    # 3DS Related
    AUTHENTICATION_REQUIRED = "authentication_required"
    AUTHENTICATION_FAILED = "authentication_failed"
    
    # Technical
    PROCESSING_ERROR = "processing_error"
    ISSUER_UNAVAILABLE = "issuer_unavailable"
    
    # Address/Identity
    AVS_MISMATCH = "avs_mismatch"
    CVV_MISMATCH = "cvv_mismatch"
    
    # Fingerprint Detection
    DEVICE_FINGERPRINT_MISMATCH = "device_fingerprint_mismatch"
    BROWSER_ANOMALY = "browser_anomaly"
    BOT_DETECTED = "bot_detected"
    
    # Behavioral
    UNUSUAL_BEHAVIOR = "unusual_behavior"
    SESSION_ANOMALY = "session_anomaly"


@dataclass
class PSPResponse:
    """Standardized PSP response"""
    success: bool
    transaction_id: str
    decline_reason: Optional[DeclineReason] = None
    decline_code: Optional[str] = None
    decline_message: Optional[str] = None
    requires_3ds: bool = False
    risk_score: float = 0.0
    risk_signals: List[str] = field(default_factory=list)
    raw_response: Dict[str, Any] = field(default_factory=dict)
    latency_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "transaction_id": self.transaction_id,
            "decline_reason": self.decline_reason.value if self.decline_reason else None,
            "decline_code": self.decline_code,
            "decline_message": self.decline_message,
            "requires_3ds": self.requires_3ds,
            "risk_score": self.risk_score,
            "risk_signals": self.risk_signals,
            "latency_ms": self.latency_ms,
            "timestamp": self.timestamp,
        }


@dataclass
class CardData:
    """Card data for testing"""
    number: str
    exp_month: str
    exp_year: str
    cvv: str
    holder_name: str = "Test User"
    
    @property
    def bin(self) -> str:
        return self.number[:6]
    
    @property
    def last4(self) -> str:
        return self.number[-4:]
    
    def is_valid_luhn(self) -> bool:
        digits = [int(d) for d in self.number if d.isdigit()]
        checksum = 0
        for i, digit in enumerate(reversed(digits)):
            if i % 2 == 1:
                digit *= 2
                if digit > 9:
                    digit -= 9
            checksum += digit
        return checksum % 10 == 0


@dataclass
class BillingAddress:
    """Billing address for AVS checks"""
    line1: str = ""
    line2: str = ""
    city: str = ""
    state: str = ""
    postal_code: str = ""
    country: str = "US"


@dataclass
class DeviceFingerprint:
    """Device fingerprint data"""
    canvas_hash: str = ""
    webgl_hash: str = ""
    audio_hash: str = ""
    screen_resolution: str = "1920x1080"
    timezone: str = "America/New_York"
    language: str = "en-US"
    platform: str = "Win32"
    user_agent: str = ""
    ip_address: str = ""
    session_id: str = ""


@dataclass
class BehavioralData:
    """Behavioral analytics data"""
    mouse_entropy: float = 0.0
    keystroke_timing: List[float] = field(default_factory=list)
    scroll_patterns: List[Dict] = field(default_factory=list)
    time_on_page_seconds: float = 0.0
    form_fill_time_seconds: float = 0.0
    navigation_path: List[str] = field(default_factory=list)
    referrer: str = ""


@dataclass
class TransactionRequest:
    """Complete transaction request for testing"""
    card: CardData
    amount: float
    currency: str = "USD"
    billing: Optional[BillingAddress] = None
    shipping: Optional[BillingAddress] = None
    fingerprint: Optional[DeviceFingerprint] = None
    behavioral: Optional[BehavioralData] = None
    merchant_id: str = "test_merchant"
    order_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class PSPSandbox(ABC):
    """Base class for PSP sandbox emulators"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.name = "base"
        self.transactions: List[Dict] = []
        self.velocity_tracker: Dict[str, List[datetime]] = {}
        
        # Detection thresholds
        self.risk_threshold = self.config.get("risk_threshold", 75)
        self.velocity_limit = self.config.get("velocity_limit", 5)
        self.velocity_window_minutes = self.config.get("velocity_window_minutes", 60)
        
        # BIN risk database
        self.high_risk_bins = {
            '414720', '424631', '428837', '431274', '438857',
            '453245', '476173', '485932', '486208', '489019',
        }
        
        # Test card behaviors
        self.test_cards = {
            '4111111111111111': {'action': 'approve'},
            '4000000000000002': {'action': 'decline', 'reason': DeclineReason.CARD_DECLINED},
            '4000000000009995': {'action': 'decline', 'reason': DeclineReason.INSUFFICIENT_FUNDS},
            '4000000000000069': {'action': 'decline', 'reason': DeclineReason.EXPIRED_CARD},
            '4000000000000127': {'action': 'decline', 'reason': DeclineReason.INVALID_CVV},
            '4000000000000119': {'action': 'decline', 'reason': DeclineReason.PROCESSING_ERROR},
            '4000000000003220': {'action': '3ds', 'reason': DeclineReason.AUTHENTICATION_REQUIRED},
            '4000000000003063': {'action': '3ds_fail', 'reason': DeclineReason.AUTHENTICATION_FAILED},
            '4100000000000019': {'action': 'fraud', 'reason': DeclineReason.FRAUD_SUSPECTED},
        }
    
    @abstractmethod
    def process_payment(self, request: TransactionRequest) -> PSPResponse:
        """Process a payment request"""
        pass
    
    @abstractmethod
    def get_risk_signals(self, request: TransactionRequest) -> Tuple[float, List[str]]:
        """Calculate risk score and signals"""
        pass
    
    def _generate_transaction_id(self) -> str:
        """Generate unique transaction ID"""
        return f"{self.name}_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
    
    def _check_velocity(self, identifier: str) -> bool:
        """Check if velocity limit exceeded"""
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(minutes=self.velocity_window_minutes)
        
        if identifier not in self.velocity_tracker:
            self.velocity_tracker[identifier] = []
        
        # Clean old entries
        self.velocity_tracker[identifier] = [
            t for t in self.velocity_tracker[identifier] if t > window_start
        ]
        
        # Check limit
        if len(self.velocity_tracker[identifier]) >= self.velocity_limit:
            return True
        
        # Add current transaction
        self.velocity_tracker[identifier].append(now)
        return False
    
    def _check_avs(self, billing: BillingAddress, expected: Optional[Dict] = None) -> str:
        """Check Address Verification System"""
        if not billing or not billing.postal_code:
            return "N"  # No match
        
        # Simulate AVS check
        if billing.postal_code.startswith("0"):
            return "N"  # No match
        elif billing.postal_code.startswith("9"):
            return "A"  # Address match only
        elif billing.postal_code.startswith("1"):
            return "Z"  # Zip match only
        else:
            return "Y"  # Full match
    
    def _check_cvv(self, cvv: str) -> str:
        """Check CVV"""
        if not cvv:
            return "N"
        if cvv == "000":
            return "N"
        if len(cvv) < 3:
            return "N"
        return "M"  # Match
    
    def _simulate_latency(self) -> float:
        """Simulate realistic API latency"""
        base_latency = random.uniform(150, 400)
        jitter = random.uniform(-50, 100)
        return max(100, base_latency + jitter)


class StripeSandbox(PSPSandbox):
    """Stripe PSP Sandbox Emulator"""
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.name = "stripe"
        
        # Stripe-specific Radar rules
        self.radar_rules = {
            "block_high_risk_countries": True,
            "block_prepaid": self.config.get("block_prepaid", False),
            "require_3ds_above": self.config.get("require_3ds_above", 100),
            "velocity_check": True,
            "device_fingerprint_check": True,
        }
        
        self.high_risk_countries = {'RU', 'NG', 'GH', 'PK', 'BD'}
    
    def process_payment(self, request: TransactionRequest) -> PSPResponse:
        start_time = time.time()
        tx_id = self._generate_transaction_id()
        
        # Check test cards first
        if request.card.number in self.test_cards:
            behavior = self.test_cards[request.card.number]
            latency = self._simulate_latency()
            
            if behavior['action'] == 'approve':
                return PSPResponse(
                    success=True,
                    transaction_id=tx_id,
                    latency_ms=latency,
                )
            elif behavior['action'] == '3ds':
                return PSPResponse(
                    success=False,
                    transaction_id=tx_id,
                    decline_reason=behavior['reason'],
                    requires_3ds=True,
                    decline_code="authentication_required",
                    decline_message="This card requires 3D Secure authentication",
                    latency_ms=latency,
                )
            else:
                return PSPResponse(
                    success=False,
                    transaction_id=tx_id,
                    decline_reason=behavior['reason'],
                    decline_code=behavior['reason'].value,
                    decline_message=f"Card declined: {behavior['reason'].value}",
                    latency_ms=latency,
                )
        
        # Run full risk analysis
        risk_score, risk_signals = self.get_risk_signals(request)
        
        # Check velocity
        velocity_key = f"{request.card.bin}_{request.fingerprint.ip_address if request.fingerprint else 'unknown'}"
        if self._check_velocity(velocity_key):
            return PSPResponse(
                success=False,
                transaction_id=tx_id,
                decline_reason=DeclineReason.VELOCITY_EXCEEDED,
                decline_code="velocity_exceeded",
                decline_message="Too many transactions in short period",
                risk_score=risk_score,
                risk_signals=risk_signals,
                latency_ms=self._simulate_latency(),
            )
        
        # Check Luhn
        if not request.card.is_valid_luhn():
            return PSPResponse(
                success=False,
                transaction_id=tx_id,
                decline_reason=DeclineReason.INVALID_NUMBER,
                decline_code="invalid_number",
                decline_message="Card number failed validation",
                latency_ms=self._simulate_latency(),
            )
        
        # Check CVV
        cvv_result = self._check_cvv(request.card.cvv)
        if cvv_result == "N":
            return PSPResponse(
                success=False,
                transaction_id=tx_id,
                decline_reason=DeclineReason.INVALID_CVV,
                decline_code="incorrect_cvc",
                decline_message="Your card's security code is incorrect",
                latency_ms=self._simulate_latency(),
            )
        
        # Check AVS
        if request.billing:
            avs_result = self._check_avs(request.billing)
            if avs_result == "N":
                risk_signals.append("avs_mismatch")
                risk_score += 20
        
        # Check 3DS requirement
        if request.amount >= self.radar_rules["require_3ds_above"]:
            return PSPResponse(
                success=False,
                transaction_id=tx_id,
                decline_reason=DeclineReason.AUTHENTICATION_REQUIRED,
                requires_3ds=True,
                decline_code="authentication_required",
                decline_message="3D Secure authentication required for this amount",
                risk_score=risk_score,
                risk_signals=risk_signals,
                latency_ms=self._simulate_latency(),
            )
        
        # Final risk decision
        if risk_score >= self.risk_threshold:
            return PSPResponse(
                success=False,
                transaction_id=tx_id,
                decline_reason=DeclineReason.HIGH_RISK,
                decline_code="high_risk",
                decline_message="Transaction blocked by Radar",
                risk_score=risk_score,
                risk_signals=risk_signals,
                latency_ms=self._simulate_latency(),
            )
        
        # Approved
        return PSPResponse(
            success=True,
            transaction_id=tx_id,
            risk_score=risk_score,
            risk_signals=risk_signals,
            latency_ms=self._simulate_latency(),
        )
    
    def get_risk_signals(self, request: TransactionRequest) -> Tuple[float, List[str]]:
        risk_score = 0.0
        signals = []
        
        # BIN check
        if request.card.bin in self.high_risk_bins:
            risk_score += 30
            signals.append("high_risk_bin")
        
        # Country check
        if request.billing and request.billing.country in self.high_risk_countries:
            risk_score += 40
            signals.append("high_risk_country")
        
        # Fingerprint checks
        if request.fingerprint:
            # Empty fingerprint
            if not request.fingerprint.canvas_hash:
                risk_score += 25
                signals.append("missing_canvas_fingerprint")
            
            # Datacenter IP detection (simplified)
            ip = request.fingerprint.ip_address
            if ip.startswith("10.") or ip.startswith("192.168.") or ip.startswith("172."):
                risk_score += 15
                signals.append("private_ip_detected")
            
            # Timezone mismatch (simplified)
            if request.fingerprint.timezone == "UTC":
                risk_score += 10
                signals.append("generic_timezone")
        else:
            risk_score += 35
            signals.append("no_device_fingerprint")
        
        # Behavioral checks
        if request.behavioral:
            # Too fast form fill
            if request.behavioral.form_fill_time_seconds < 5:
                risk_score += 30
                signals.append("form_fill_too_fast")
            
            # Low mouse entropy
            if request.behavioral.mouse_entropy < 0.3:
                risk_score += 25
                signals.append("low_mouse_entropy")
            
            # No referrer
            if not request.behavioral.referrer:
                risk_score += 15
                signals.append("no_referrer")
            
            # Short session
            if request.behavioral.time_on_page_seconds < 10:
                risk_score += 20
                signals.append("short_session")
        else:
            risk_score += 20
            signals.append("no_behavioral_data")
        
        # Amount-based risk
        if request.amount > 500:
            risk_score += 10
            signals.append("high_amount")
        if request.amount > 1000:
            risk_score += 15
            signals.append("very_high_amount")
        
        return min(100, risk_score), signals


class AdyenSandbox(PSPSandbox):
    """Adyen PSP Sandbox Emulator"""
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.name = "adyen"
        
        # Adyen RevenueProtect rules
        self.revenue_protect = {
            "device_fingerprint_required": True,
            "3ds2_preferred": True,
            "velocity_check": True,
            "referral_check": True,
        }
    
    def process_payment(self, request: TransactionRequest) -> PSPResponse:
        tx_id = self._generate_transaction_id()
        
        # Test cards
        if request.card.number in self.test_cards:
            behavior = self.test_cards[request.card.number]
            latency = self._simulate_latency()
            
            if behavior['action'] == 'approve':
                return PSPResponse(
                    success=True,
                    transaction_id=tx_id,
                    latency_ms=latency,
                    raw_response={"resultCode": "Authorised"},
                )
            elif behavior['action'] == '3ds':
                return PSPResponse(
                    success=False,
                    transaction_id=tx_id,
                    decline_reason=behavior['reason'],
                    requires_3ds=True,
                    decline_code="RedirectShopper",
                    decline_message="3D Secure 2 authentication required",
                    latency_ms=latency,
                    raw_response={"resultCode": "RedirectShopper"},
                )
            else:
                return PSPResponse(
                    success=False,
                    transaction_id=tx_id,
                    decline_reason=behavior['reason'],
                    decline_code="Refused",
                    decline_message=f"Refused: {behavior['reason'].value}",
                    latency_ms=latency,
                    raw_response={"resultCode": "Refused"},
                )
        
        risk_score, risk_signals = self.get_risk_signals(request)
        
        # Adyen requires device fingerprint
        if self.revenue_protect["device_fingerprint_required"]:
            if not request.fingerprint or not request.fingerprint.session_id:
                return PSPResponse(
                    success=False,
                    transaction_id=tx_id,
                    decline_reason=DeclineReason.DEVICE_FINGERPRINT_MISMATCH,
                    decline_code="Refused",
                    decline_message="Device fingerprint required",
                    risk_score=risk_score,
                    risk_signals=risk_signals + ["missing_device_fingerprint"],
                    latency_ms=self._simulate_latency(),
                )
        
        # Risk decision
        if risk_score >= self.risk_threshold:
            return PSPResponse(
                success=False,
                transaction_id=tx_id,
                decline_reason=DeclineReason.FRAUD_SUSPECTED,
                decline_code="Refused",
                decline_message="Transaction blocked by RevenueProtect",
                risk_score=risk_score,
                risk_signals=risk_signals,
                latency_ms=self._simulate_latency(),
            )
        
        return PSPResponse(
            success=True,
            transaction_id=tx_id,
            risk_score=risk_score,
            risk_signals=risk_signals,
            latency_ms=self._simulate_latency(),
            raw_response={"resultCode": "Authorised"},
        )
    
    def get_risk_signals(self, request: TransactionRequest) -> Tuple[float, List[str]]:
        risk_score = 0.0
        signals = []
        
        # Similar to Stripe but with Adyen-specific checks
        if request.card.bin in self.high_risk_bins:
            risk_score += 25
            signals.append("high_risk_bin")
        
        if request.fingerprint:
            if not request.fingerprint.webgl_hash:
                risk_score += 20
                signals.append("missing_webgl")
            
            # Check for headless browser indicators
            if "HeadlessChrome" in request.fingerprint.user_agent:
                risk_score += 50
                signals.append("headless_browser_detected")
        else:
            risk_score += 40
            signals.append("no_fingerprint")
        
        if request.behavioral:
            if request.behavioral.mouse_entropy < 0.2:
                risk_score += 35
                signals.append("bot_like_mouse_movement")
        
        return min(100, risk_score), signals


class BraintreeSandbox(PSPSandbox):
    """Braintree PSP Sandbox Emulator"""
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.name = "braintree"
    
    def process_payment(self, request: TransactionRequest) -> PSPResponse:
        tx_id = self._generate_transaction_id()
        risk_score, risk_signals = self.get_risk_signals(request)
        
        if request.card.number in self.test_cards:
            behavior = self.test_cards[request.card.number]
            if behavior['action'] == 'approve':
                return PSPResponse(success=True, transaction_id=tx_id, latency_ms=self._simulate_latency())
            else:
                return PSPResponse(
                    success=False,
                    transaction_id=tx_id,
                    decline_reason=behavior['reason'],
                    latency_ms=self._simulate_latency(),
                )
        
        if risk_score >= self.risk_threshold:
            return PSPResponse(
                success=False,
                transaction_id=tx_id,
                decline_reason=DeclineReason.HIGH_RISK,
                risk_score=risk_score,
                risk_signals=risk_signals,
                latency_ms=self._simulate_latency(),
            )
        
        return PSPResponse(success=True, transaction_id=tx_id, risk_score=risk_score, latency_ms=self._simulate_latency())
    
    def get_risk_signals(self, request: TransactionRequest) -> Tuple[float, List[str]]:
        risk_score = 0.0
        signals = []
        
        if request.card.bin in self.high_risk_bins:
            risk_score += 30
            signals.append("high_risk_bin")
        
        if request.fingerprint and not request.fingerprint.canvas_hash:
            risk_score += 25
            signals.append("missing_fingerprint")
        
        return min(100, risk_score), signals


class PayPalSandbox(PSPSandbox):
    """PayPal PSP Sandbox Emulator"""
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.name = "paypal"
    
    def process_payment(self, request: TransactionRequest) -> PSPResponse:
        tx_id = self._generate_transaction_id()
        risk_score, risk_signals = self.get_risk_signals(request)
        
        if risk_score >= self.risk_threshold:
            return PSPResponse(
                success=False,
                transaction_id=tx_id,
                decline_reason=DeclineReason.FRAUD_SUSPECTED,
                risk_score=risk_score,
                risk_signals=risk_signals,
                latency_ms=self._simulate_latency(),
            )
        
        return PSPResponse(success=True, transaction_id=tx_id, risk_score=risk_score, latency_ms=self._simulate_latency())
    
    def get_risk_signals(self, request: TransactionRequest) -> Tuple[float, List[str]]:
        risk_score = 0.0
        signals = []
        
        # PayPal focuses heavily on account history and behavioral
        if request.behavioral:
            if request.behavioral.time_on_page_seconds < 15:
                risk_score += 30
                signals.append("rushed_checkout")
        
        return min(100, risk_score), signals


class SquareSandbox(PSPSandbox):
    """Square PSP Sandbox Emulator"""
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.name = "square"
    
    def process_payment(self, request: TransactionRequest) -> PSPResponse:
        tx_id = self._generate_transaction_id()
        risk_score, risk_signals = self.get_risk_signals(request)
        
        if risk_score >= self.risk_threshold:
            return PSPResponse(
                success=False,
                transaction_id=tx_id,
                decline_reason=DeclineReason.HIGH_RISK,
                risk_score=risk_score,
                risk_signals=risk_signals,
                latency_ms=self._simulate_latency(),
            )
        
        return PSPResponse(success=True, transaction_id=tx_id, risk_score=risk_score, latency_ms=self._simulate_latency())
    
    def get_risk_signals(self, request: TransactionRequest) -> Tuple[float, List[str]]:
        risk_score = 0.0
        signals = []
        
        if request.card.bin in self.high_risk_bins:
            risk_score += 25
            signals.append("high_risk_bin")
        
        return min(100, risk_score), signals


# Factory function
def create_psp_sandbox(psp_name: str, config: Optional[Dict] = None) -> PSPSandbox:
    """Create a PSP sandbox by name"""
    sandboxes = {
        "stripe": StripeSandbox,
        "adyen": AdyenSandbox,
        "braintree": BraintreeSandbox,
        "paypal": PayPalSandbox,
        "square": SquareSandbox,
    }
    
    if psp_name.lower() not in sandboxes:
        raise ValueError(f"Unknown PSP: {psp_name}. Available: {list(sandboxes.keys())}")
    
    return sandboxes[psp_name.lower()](config)


if __name__ == "__main__":
    # Demo usage
    stripe = StripeSandbox()
    
    request = TransactionRequest(
        card=CardData(
            number="4111111111111111",
            exp_month="12",
            exp_year="25",
            cvv="123",
        ),
        amount=99.99,
        fingerprint=DeviceFingerprint(
            canvas_hash="abc123",
            ip_address="203.0.113.50",
        ),
        behavioral=BehavioralData(
            mouse_entropy=0.75,
            form_fill_time_seconds=45,
            time_on_page_seconds=120,
        ),
    )
    
    response = stripe.process_payment(request)
    print(f"Result: {'APPROVED' if response.success else 'DECLINED'}")
    print(f"Risk Score: {response.risk_score}")
    print(f"Signals: {response.risk_signals}")
