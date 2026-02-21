"""
TITAN V7.5 SINGULARITY — TRA Exemption Engine for 3DS v2.2
Transaction Risk Analysis Exemption Forcing for Frictionless Authentication

Problem:
    3DS 2.x challenges cause 20% of transaction failures. The protocol allows
    merchants to request TRA (Transaction Risk Analysis) exemptions for
    low-risk transactions under PSD2. However, issuers can override exemptions
    if their risk scoring flags anomalies.

    Detection vectors:
    - Behavioral biometrics mismatch with cardholder history
    - Device fingerprint inconsistency
    - Transaction velocity anomalies
    - Geographic risk profiling
    - First-session identity bias (15% of failures)

Solution:
    TRA Exemption Engine that:
    1. Pre-calculates transaction risk score before submission
    2. Optimizes transaction parameters to stay below TRA thresholds
    3. Builds progressive cardholder trust through micro-transactions
    4. Aligns device/behavioral signals with cardholder persona
    5. Forces frictionless authentication through SCA exemption logic

Target Outcome:
    Convert 3DS challenges to frictionless flow by satisfying
    EMV 3DS 2.2 TRA exemption criteria automatically.
"""

import hashlib
import json
import math
import os
import random
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any, Set

__version__ = "7.5.0"
__author__ = "Dva.12"


class ExemptionType(Enum):
    """3DS 2.x SCA Exemption Types (PSD2)"""
    TRA = "tra"                          # Transaction Risk Analysis
    LOW_VALUE = "low_value"              # <€30 per transaction
    TRUSTED_BENEFICIARY = "trusted"      # Whitelisted payee
    RECURRING = "recurring"              # Subscription/fixed amount
    CORPORATE = "corporate"              # B2B transactions
    NONE = "none"                        # No exemption requested


class RiskLevel(Enum):
    """Transaction risk assessment levels"""
    MINIMAL = "minimal"      # 0-10: Always frictionless
    LOW = "low"              # 11-25: Usually frictionless
    MODERATE = "moderate"    # 26-50: Possible challenge
    HIGH = "high"            # 51-75: Likely challenge
    CRITICAL = "critical"    # 76-100: Always challenged


class ChallengeOutcome(Enum):
    """3DS challenge flow outcomes"""
    FRICTIONLESS = "frictionless"     # No challenge required
    CHALLENGE = "challenge"            # OTP/biometric required
    DECLINED = "declined"              # Issuer declined
    FALLBACK = "fallback"              # Fell back to 3DS 1.0


@dataclass
class CardholderProfile:
    """Cardholder behavioral profile for risk assessment"""
    card_bin: str                      # First 6-8 digits
    issuer_country: str                # 2-letter ISO code
    historical_avg_amount: float       # Average transaction amount
    historical_frequency: int          # Transactions per month
    device_ids: Set[str] = field(default_factory=set)  # Known devices
    ip_addresses: Set[str] = field(default_factory=set)  # Known IPs
    merchant_ids: Set[str] = field(default_factory=set)  # Known merchants
    trust_score: float = 50.0          # 0-100 trust score
    account_age_days: int = 365


@dataclass
class TransactionContext:
    """Transaction context for risk calculation"""
    amount: Decimal
    currency: str
    merchant_id: str
    merchant_category: str
    merchant_country: str
    device_fingerprint: str
    ip_address: str
    session_time_seconds: int
    page_interactions: int
    is_returning_customer: bool
    cart_item_count: int
    email_domain: str
    shipping_matches_billing: bool


@dataclass
class TRAAssessment:
    """Transaction Risk Analysis assessment result"""
    risk_score: float                   # 0-100
    risk_level: RiskLevel
    recommended_exemption: ExemptionType
    exemption_probability: float        # Chance issuer accepts
    optimization_suggestions: List[str]
    predicted_outcome: ChallengeOutcome
    factors: Dict[str, float]           # Individual risk factors


# ═══════════════════════════════════════════════════════════════════════════════
# PSD2 TRA THRESHOLDS - Per EMVCo 3DS 2.3 Specification
# ═══════════════════════════════════════════════════════════════════════════════

# TRA fraud rate thresholds by amount
TRA_THRESHOLDS = {
    # Amount limit: Required fraud rate (basis points)
    100: 13,    # €100: 0.13% fraud rate required
    250: 6,     # €250: 0.06% fraud rate required
    500: 1,     # €500: 0.01% fraud rate required
}

# Low value exemption: €30 cumulative, 5 transactions
LOW_VALUE_LIMIT = 30
LOW_VALUE_COUNT_LIMIT = 5

# Acquirer risk scoring factors
RISK_FACTORS = {
    "first_device": 15,             # Unknown device
    "first_ip": 10,                 # Unknown IP address
    "first_merchant": 8,            # First transaction with merchant
    "high_amount": 12,              # Above cardholder average
    "velocity_spike": 20,           # Unusual transaction frequency
    "geo_mismatch": 18,             # IP/billing country mismatch
    "email_disposable": 8,          # Temporary email domain
    "session_too_short": 10,        # Transaction completed too fast
    "session_too_long": 5,          # Possible bot hesitation
    "no_interactions": 15,          # No page interactions before checkout
    "shipping_mismatch": 12,        # Ship/bill address mismatch
    "new_account": 10,              # Account created recently
    "high_risk_mcc": 15,            # Digital goods, crypto, etc.
    "cross_border": 8,              # International transaction
    "odd_hours": 5,                 # Transaction during unusual hours
}

# High-risk Merchant Category Codes
HIGH_RISK_MCCS = {
    "5816": "Digital Goods",
    "5818": "Digital Services",
    "6051": "Crypto/Virtual Currency",
    "7995": "Gambling",
    "5962": "Travel (Prepaid)",
    "5964": "Catalog/Mail Order",
    "5967": "Direct Marketing",
}

# Disposable email domains (expanded for 2025+ detection)
DISPOSABLE_DOMAINS = {
    "tempmail.com", "guerrillamail.com", "10minutemail.com", "mailinator.com",
    "throwaway.email", "temp-mail.org", "fakeinbox.com", "maildrop.cc",
    "yopmail.com", "sharklasers.com", "guerrillamailblock.com", "grr.la",
    "dispostable.com", "trashmail.com", "mohmal.com", "tempail.com",
    "emailondeck.com", "getnada.com", "burnermail.io", "inboxkitten.com",
    "minuteinbox.com", "tempr.email", "discard.email", "mailnesia.com",
}


class TRARiskCalculator:
    """
    Calculates transaction risk score using EMV 3DS 2.x methodology.
    
    Implements acquirer-side TRA scoring to predict issuer behavior
    and optimize transaction parameters for exemption eligibility.
    """
    
    def __init__(self):
        self._lock = threading.Lock()
        self._assessment_cache: Dict[str, TRAAssessment] = {}
    
    def assess(
        self,
        cardholder: CardholderProfile,
        transaction: TransactionContext,
    ) -> TRAAssessment:
        """
        Calculate comprehensive TRA risk assessment.
        
        Returns risk score and optimization recommendations.
        """
        factors = {}
        
        # Device fingerprint check
        if transaction.device_fingerprint not in cardholder.device_ids:
            factors["first_device"] = RISK_FACTORS["first_device"]
        
        # IP address check
        if transaction.ip_address not in cardholder.ip_addresses:
            factors["first_ip"] = RISK_FACTORS["first_ip"]
        
        # Merchant history
        if transaction.merchant_id not in cardholder.merchant_ids:
            factors["first_merchant"] = RISK_FACTORS["first_merchant"]
        
        # Amount analysis
        if float(transaction.amount) > cardholder.historical_avg_amount * 2:
            factors["high_amount"] = RISK_FACTORS["high_amount"]
        
        # Geographic analysis
        if transaction.ip_address:
            # Simplified geo check - in reality would use IP geolocation
            if transaction.merchant_country != cardholder.issuer_country:
                factors["cross_border"] = RISK_FACTORS["cross_border"]
        
        # Email domain check
        email_domain = transaction.email_domain.lower()
        if email_domain in DISPOSABLE_DOMAINS:
            factors["email_disposable"] = RISK_FACTORS["email_disposable"]
        
        # Session timing analysis
        if transaction.session_time_seconds < 30:
            factors["session_too_short"] = RISK_FACTORS["session_too_short"]
        elif transaction.session_time_seconds > 1800:
            factors["session_too_long"] = RISK_FACTORS["session_too_long"]
        
        # Interaction analysis
        if transaction.page_interactions < 3:
            factors["no_interactions"] = RISK_FACTORS["no_interactions"]
        
        # Shipping check
        if not transaction.shipping_matches_billing:
            factors["shipping_mismatch"] = RISK_FACTORS["shipping_mismatch"]
        
        # Account age
        if cardholder.account_age_days < 30:
            factors["new_account"] = RISK_FACTORS["new_account"]
        
        # MCC risk
        if transaction.merchant_category in HIGH_RISK_MCCS:
            factors["high_risk_mcc"] = RISK_FACTORS["high_risk_mcc"]
        
        # Calculate raw score
        raw_score = sum(factors.values())
        
        # Apply trust score modifier
        trust_modifier = (100 - cardholder.trust_score) / 100
        final_score = raw_score * (0.5 + 0.5 * trust_modifier)
        
        # Cap at 100
        final_score = min(100, final_score)
        
        # Determine risk level
        if final_score <= 10:
            risk_level = RiskLevel.MINIMAL
        elif final_score <= 25:
            risk_level = RiskLevel.LOW
        elif final_score <= 50:
            risk_level = RiskLevel.MODERATE
        elif final_score <= 75:
            risk_level = RiskLevel.HIGH
        else:
            risk_level = RiskLevel.CRITICAL
        
        # Determine best exemption strategy
        exemption, probability = self._select_exemption(
            transaction, final_score, risk_level
        )
        
        # Generate optimization suggestions
        suggestions = self._generate_suggestions(factors, transaction, cardholder)
        
        # Predict outcome
        outcome = self._predict_outcome(final_score, exemption, probability)
        
        return TRAAssessment(
            risk_score=round(final_score, 2),
            risk_level=risk_level,
            recommended_exemption=exemption,
            exemption_probability=round(probability * 100, 1),
            optimization_suggestions=suggestions,
            predicted_outcome=outcome,
            factors=factors,
        )
    
    def _select_exemption(
        self,
        transaction: TransactionContext,
        risk_score: float,
        risk_level: RiskLevel,
    ) -> Tuple[ExemptionType, float]:
        """Select optimal exemption type"""
        amount = float(transaction.amount)
        
        # Low value exemption
        if amount <= LOW_VALUE_LIMIT:
            return ExemptionType.LOW_VALUE, 0.95
        
        # TRA exemption thresholds
        if amount <= 100 and risk_score <= 20:
            return ExemptionType.TRA, 0.85
        elif amount <= 250 and risk_score <= 15:
            return ExemptionType.TRA, 0.75
        elif amount <= 500 and risk_score <= 10:
            return ExemptionType.TRA, 0.60
        
        # Returning customer might qualify for trusted
        if transaction.is_returning_customer and risk_score <= 25:
            return ExemptionType.TRUSTED_BENEFICIARY, 0.70
        
        # No exemption recommended
        if risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            return ExemptionType.NONE, 0.0
        
        # Try TRA anyway for moderate risk
        return ExemptionType.TRA, 0.40
    
    def _generate_suggestions(
        self,
        factors: Dict[str, float],
        transaction: TransactionContext,
        cardholder: CardholderProfile,
    ) -> List[str]:
        """Generate optimization suggestions to reduce risk score"""
        suggestions = []
        
        if "first_device" in factors:
            suggestions.append("Use a device fingerprint from cardholder's known devices")
        
        if "first_ip" in factors:
            suggestions.append("Route through IP address in cardholder's history")
        
        if "session_too_short" in factors:
            suggestions.append("Extend session time to at least 60 seconds")
        
        if "no_interactions" in factors:
            suggestions.append("Simulate page scrolls and product clicks before checkout")
        
        if "high_amount" in factors:
            suggestions.append(f"Split transaction into amounts < €{cardholder.historical_avg_amount:.0f}")
        
        if "email_disposable" in factors:
            suggestions.append("Use established email domain (gmail, outlook, etc.)")
        
        if "shipping_mismatch" in factors:
            suggestions.append("Set shipping address to match billing address")
        
        if "new_account" in factors:
            suggestions.append("Use aged merchant account or build trust score first")
        
        return suggestions
    
    def _predict_outcome(
        self,
        risk_score: float,
        exemption: ExemptionType,
        probability: float,
    ) -> ChallengeOutcome:
        """Predict 3DS flow outcome"""
        if exemption == ExemptionType.LOW_VALUE and probability > 0.8:
            return ChallengeOutcome.FRICTIONLESS
        
        if exemption == ExemptionType.TRA and probability > 0.7:
            return ChallengeOutcome.FRICTIONLESS
        
        if risk_score > 75:
            return ChallengeOutcome.DECLINED
        
        if risk_score > 50:
            return ChallengeOutcome.CHALLENGE
        
        if probability > 0.5:
            return ChallengeOutcome.FRICTIONLESS
        
        return ChallengeOutcome.CHALLENGE


class TRAOptimizer:
    """
    Optimizes transaction parameters to maximize TRA exemption success.
    
    Implements progressive trust-building and transaction shaping
    to achieve frictionless authentication.
    """
    
    def __init__(self, calculator: TRARiskCalculator):
        self.calculator = calculator
        self._trust_history: Dict[str, List[Dict]] = {}
        self._lock = threading.Lock()
    
    def optimize_transaction(
        self,
        cardholder: CardholderProfile,
        transaction: TransactionContext,
    ) -> Dict[str, Any]:
        """
        Optimize transaction parameters for TRA exemption.
        
        Returns optimized transaction context and recommendations.
        """
        # Get baseline assessment
        baseline = self.calculator.assess(cardholder, transaction)
        
        optimizations = []
        
        # Optimize session behavior if needed
        if transaction.session_time_seconds < 60:
            optimizations.append({
                "action": "extend_session",
                "current": transaction.session_time_seconds,
                "target": 90,
                "impact": "-10 risk points",
            })
        
        # Optimize interactions if needed
        if transaction.page_interactions < 5:
            optimizations.append({
                "action": "simulate_interactions",
                "current": transaction.page_interactions,
                "target": 8,
                "impact": "-15 risk points",
            })
        
        # Amount optimization for high-value transactions
        amount = float(transaction.amount)
        if amount > 100 and baseline.risk_score > 25:
            # Suggest amount splitting
            optimal_amounts = self._calculate_split(amount, cardholder)
            optimizations.append({
                "action": "split_transaction",
                "current": amount,
                "suggested_splits": optimal_amounts,
                "impact": "Multiple frictionless transactions",
            })
        
        # Device binding recommendation
        if "first_device" in baseline.factors:
            optimizations.append({
                "action": "bind_device",
                "impact": "Add device to cardholder profile for future use",
            })
        
        return {
            "baseline_assessment": {
                "risk_score": baseline.risk_score,
                "risk_level": baseline.risk_level.value,
                "predicted_outcome": baseline.predicted_outcome.value,
                "exemption": baseline.recommended_exemption.value,
                "exemption_probability": baseline.exemption_probability,
            },
            "optimizations": optimizations,
            "optimal_exemption_type": self._determine_optimal_exemption(
                amount, baseline.risk_score
            ),
            "3ds_request_config": self._generate_3ds_config(baseline),
        }
    
    def _calculate_split(
        self,
        amount: float,
        cardholder: CardholderProfile,
    ) -> List[float]:
        """Calculate optimal transaction splits"""
        # Target amount per transaction
        target = min(
            cardholder.historical_avg_amount * 0.8,  # Below avg
            100.0,  # Below TRA threshold
            LOW_VALUE_LIMIT,  # Low value exemption
        )
        
        if target < 10:
            target = 30  # Minimum practical amount
        
        splits = []
        remaining = amount
        
        while remaining > 0:
            if remaining <= target * 1.5:
                splits.append(round(remaining, 2))
                remaining = 0
            else:
                # Add some variance
                split_amount = target * (0.9 + random.random() * 0.2)
                splits.append(round(split_amount, 2))
                remaining -= split_amount
        
        return splits
    
    def _determine_optimal_exemption(
        self,
        amount: float,
        risk_score: float,
    ) -> str:
        """Determine optimal exemption type for 3DS request"""
        if amount <= LOW_VALUE_LIMIT:
            return "lowValue"
        
        if risk_score <= 15 and amount <= 250:
            return "transactionRiskAnalysis"
        
        if risk_score <= 10 and amount <= 500:
            return "transactionRiskAnalysis"
        
        return "noExemption"
    
    def _generate_3ds_config(self, assessment: TRAAssessment) -> Dict:
        """Generate 3DS v2.2 request configuration"""
        return {
            "threeDSRequestorChallengeInd": "01" if assessment.risk_score <= 30 else "02",
            "scaExemptionReason": assessment.recommended_exemption.value,
            "threeDSRequestorAuthenticationInd": "01",  # Payment transaction
            "acquirerBinCountry": "826",  # ISO numeric country
            "acquirerFraudRate": max(1, int(assessment.risk_score / 10)),
            "deviceChannel": "02",  # Browser
            "messageCategory": "01",  # Payment authentication
        }
    
    def build_trust_incrementally(
        self,
        card_hash: str,
        initial_amount: float = 5.0,
        target_amount: float = 500.0,
        days: int = 30,
    ) -> List[Dict]:
        """
        Generate progressive trust-building transaction schedule.
        
        Small successful transactions build cardholder trust score
        before attempting high-value transactions.
        """
        schedule = []
        current_amount = initial_amount
        current_day = 0
        
        # Exponential growth with variance
        while current_amount < target_amount and current_day < days:
            # Add some randomness
            variance = random.uniform(0.8, 1.2)
            tx_amount = min(current_amount * variance, target_amount)
            
            schedule.append({
                "day": current_day,
                "amount": round(tx_amount, 2),
                "currency": "EUR",
                "purpose": "trust_building",
                "expected_outcome": "frictionless" if tx_amount < LOW_VALUE_LIMIT else "likely_frictionless",
            })
            
            # Grow amount for next transaction
            growth_factor = 1.5 + random.random() * 0.5
            current_amount = tx_amount * growth_factor
            
            # Space transactions
            current_day += random.randint(1, 5)
        
        # Final target transaction
        if current_day < days:
            schedule.append({
                "day": min(current_day + 3, days),
                "amount": target_amount,
                "currency": "EUR",
                "purpose": "target_transaction",
                "expected_outcome": "frictionless_with_tra",
            })
        
        return schedule
    
    def record_transaction_outcome(
        self,
        card_hash: str,
        amount: float,
        outcome: ChallengeOutcome,
        exemption_used: ExemptionType,
    ) -> None:
        """Record transaction outcome for learning"""
        with self._lock:
            if card_hash not in self._trust_history:
                self._trust_history[card_hash] = []
            
            self._trust_history[card_hash].append({
                "timestamp": time.time(),
                "amount": amount,
                "outcome": outcome.value,
                "exemption": exemption_used.value,
                "success": outcome == ChallengeOutcome.FRICTIONLESS,
            })


class IssuerBehaviorPredictor:
    """
    Predicts issuer-specific 3DS behavior patterns.
    
    Different issuers have different risk thresholds and
    exemption acceptance rates.
    """
    
    def __init__(self):
        # BIN prefix -> issuer behavior
        self._issuer_profiles: Dict[str, Dict] = {
            # Major US issuers
            "4": {"name": "Visa", "tra_acceptance": 0.75, "challenge_threshold": 60},
            "5": {"name": "Mastercard", "tra_acceptance": 0.70, "challenge_threshold": 55},
            "34": {"name": "Amex", "tra_acceptance": 0.65, "challenge_threshold": 45},
            "37": {"name": "Amex", "tra_acceptance": 0.65, "challenge_threshold": 45},
            "6011": {"name": "Discover", "tra_acceptance": 0.72, "challenge_threshold": 58},
            
            # European issuers (stricter PSD2)
            "4148": {"name": "Barclays UK", "tra_acceptance": 0.60, "challenge_threshold": 40},
            "4659": {"name": "Deutsche Bank", "tra_acceptance": 0.55, "challenge_threshold": 35},
            "5178": {"name": "BNP Paribas", "tra_acceptance": 0.58, "challenge_threshold": 38},
        }
    
    def predict_behavior(self, bin_prefix: str) -> Dict:
        """Predict issuer behavior for BIN prefix"""
        # Try longest prefix match
        for prefix_len in range(len(bin_prefix), 0, -1):
            prefix = bin_prefix[:prefix_len]
            if prefix in self._issuer_profiles:
                profile = self._issuer_profiles[prefix]
                return {
                    "issuer": profile["name"],
                    "tra_acceptance_rate": profile["tra_acceptance"],
                    "challenge_threshold": profile["challenge_threshold"],
                    "recommendation": self._get_recommendation(profile),
                }
        
        # Default behavior
        return {
            "issuer": "Unknown",
            "tra_acceptance_rate": 0.50,
            "challenge_threshold": 50,
            "recommendation": "Use conservative amount splitting",
        }
    
    def _get_recommendation(self, profile: Dict) -> str:
        """Get issuer-specific recommendation"""
        if profile["tra_acceptance"] >= 0.70:
            return "TRA exemptions likely accepted; proceed normally"
        elif profile["tra_acceptance"] >= 0.55:
            return "Moderate TRA acceptance; consider trust-building first"
        else:
            return "Strict issuer; use low-value exemptions or progressive trust"


# ═══════════════════════════════════════════════════════════════════════════════
# V7.5 SINGLETON INSTANCES
# ═══════════════════════════════════════════════════════════════════════════════

_tra_calculator: Optional[TRARiskCalculator] = None
_tra_optimizer: Optional[TRAOptimizer] = None
_issuer_predictor: Optional[IssuerBehaviorPredictor] = None


def get_tra_calculator() -> TRARiskCalculator:
    """Get TRA risk calculator"""
    global _tra_calculator
    if _tra_calculator is None:
        _tra_calculator = TRARiskCalculator()
    return _tra_calculator


def get_tra_optimizer() -> TRAOptimizer:
    """Get TRA optimizer"""
    global _tra_optimizer
    if _tra_optimizer is None:
        _tra_optimizer = TRAOptimizer(get_tra_calculator())
    return _tra_optimizer


def get_issuer_predictor() -> IssuerBehaviorPredictor:
    """Get issuer behavior predictor"""
    global _issuer_predictor
    if _issuer_predictor is None:
        _issuer_predictor = IssuerBehaviorPredictor()
    return _issuer_predictor


def assess_transaction_risk(
    card_bin: str,
    amount: float,
    currency: str = "EUR",
    merchant_mcc: str = "5999",
    is_returning: bool = False,
    session_seconds: int = 120,
    page_interactions: int = 5,
) -> Dict:
    """Convenience function: assess transaction risk and get recommendations"""
    calculator = get_tra_calculator()
    optimizer = get_tra_optimizer()
    issuer_pred = get_issuer_predictor()
    
    # Build mock profiles
    cardholder = CardholderProfile(
        card_bin=card_bin,
        issuer_country="US",
        historical_avg_amount=150.0,
        historical_frequency=5,
        trust_score=60.0,
    )
    
    transaction = TransactionContext(
        amount=Decimal(str(amount)),
        currency=currency,
        merchant_id="merchant_001",
        merchant_category=merchant_mcc,
        merchant_country="US",
        device_fingerprint="device_001",
        ip_address="1.2.3.4",
        session_time_seconds=session_seconds,
        page_interactions=page_interactions,
        is_returning_customer=is_returning,
        cart_item_count=3,
        email_domain="gmail.com",
        shipping_matches_billing=True,
    )
    
    assessment = calculator.assess(cardholder, transaction)
    optimization = optimizer.optimize_transaction(cardholder, transaction)
    issuer_behavior = issuer_pred.predict_behavior(card_bin)
    
    return {
        "risk_assessment": {
            "score": assessment.risk_score,
            "level": assessment.risk_level.value,
            "factors": assessment.factors,
        },
        "exemption": {
            "recommended": assessment.recommended_exemption.value,
            "probability": assessment.exemption_probability,
        },
        "prediction": {
            "outcome": assessment.predicted_outcome.value,
            "issuer_behavior": issuer_behavior,
        },
        "optimizations": optimization["optimizations"],
        "suggestions": assessment.optimization_suggestions,
        "3ds_config": optimization["3ds_request_config"],
    }


if __name__ == "__main__":
    print("TITAN V7.5 TRA Exemption Engine")
    print("=" * 50)
    
    # Test risk assessment
    result = assess_transaction_risk(
        card_bin="411111",
        amount=150.00,
        is_returning=False,
        session_seconds=45,
        page_interactions=2,
    )
    
    print(f"\nRisk Score: {result['risk_assessment']['score']}")
    print(f"Risk Level: {result['risk_assessment']['level']}")
    print(f"Predicted Outcome: {result['prediction']['outcome']}")
    print(f"Exemption: {result['exemption']['recommended']} ({result['exemption']['probability']}%)")
    print(f"\nSuggestions:")
    for suggestion in result['suggestions']:
        print(f"  - {suggestion}")
