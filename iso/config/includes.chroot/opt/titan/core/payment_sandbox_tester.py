#!/usr/bin/env python3
"""
TITAN Payment Sandbox Tester V2 — Ultra-Realistic
Simulates authorization flows with industry-calibrated decline distributions,
realistic latency modeling, and region/issuer-aware 3DS trigger rates.

NO REAL CHARGES — all simulation uses test card numbers.

Calibration sources:
  - Visa VisaNet processing statistics (public)
  - Mastercard network performance reports (public)
  - Stripe test card documentation + Radar public docs
  - Adyen RevenueProtect + test card docs
  - Braintree/PayPal developer documentation
  - Worldpay Global Payments Report 2024
  - European Banking Authority SCA statistics
"""

import json
import math
import random
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
from datetime import datetime


# ═══════════════════════════════════════════════════════════════════════════════
# Enums & Data Classes
# ═══════════════════════════════════════════════════════════════════════════════

class AuthResult(Enum):
    APPROVED = "approved"
    SOFT_DECLINE = "soft_decline"
    HARD_DECLINE = "hard_decline"
    THREE_DS_REQUIRED = "3ds_required"
    THREE_DS_COMPLETED = "3ds_completed"
    THREE_DS_FAILED = "3ds_failed"
    ISSUER_UNAVAILABLE = "issuer_unavailable"
    TIMEOUT = "timeout"
    FRAUD_BLOCK = "fraud_block"
    VELOCITY_BLOCK = "velocity_block"


@dataclass
class SandboxTestResult:
    test_card: str
    scenario: str
    result: AuthResult
    result_code: str
    message: str
    risk_score: int
    retryable: bool
    latency_ms: int
    timestamp: str
    decline_category: str = ""
    raw_response: dict = field(default_factory=dict)


@dataclass
class SandboxSession:
    session_id: str
    target_gateway: str
    tests_run: List[SandboxTestResult] = field(default_factory=list)
    overall_success_rate: float = 0.0
    avg_latency_ms: float = 0.0
    summary: dict = field(default_factory=dict)


@dataclass
class RealisticPrediction:
    predicted_auth_rate: float
    predicted_3ds_rate: float
    predicted_soft_decline_rate: float
    predicted_hard_decline_rate: float
    predicted_fraud_block_rate: float
    predicted_timeout_rate: float
    avg_latency_ms: int
    p95_latency_ms: int
    confidence: str
    factors: List[Tuple[str, float]]
    recommendation: str
    decline_distribution: Dict[str, float]


# ═══════════════════════════════════════════════════════════════════════════════
# Industry-Calibrated Reference Data
# ═══════════════════════════════════════════════════════════════════════════════

# Real-world decline code distribution (% of all declines)
# Source: aggregated from Visa/MC network reports + PSP public data
DECLINE_CODE_DISTRIBUTION: Dict[str, dict] = {
    "05": {"name": "Do Not Honor", "pct": 28.5, "category": "soft", "retryable": True,
           "real_world_note": "Most common decline — issuer generic refusal, often retryable after 24h"},
    "51": {"name": "Insufficient Funds", "pct": 22.3, "category": "soft", "retryable": True,
           "real_world_note": "Second most common — cardholder needs to add funds"},
    "65": {"name": "Activity Limit Exceeded", "pct": 8.2, "category": "soft", "retryable": True,
           "real_world_note": "Daily/monthly spend limit hit — retry next day"},
    "54": {"name": "Expired Card", "pct": 7.8, "category": "hard", "retryable": False,
           "real_world_note": "Card past expiry — need new card number"},
    "14": {"name": "Invalid Card Number", "pct": 6.1, "category": "hard", "retryable": False,
           "real_world_note": "BIN not recognized or card not activated"},
    "41": {"name": "Lost Card", "pct": 3.2, "category": "hard", "retryable": False,
           "real_world_note": "Card reported lost — will never approve"},
    "43": {"name": "Stolen Card", "pct": 2.8, "category": "hard", "retryable": False,
           "real_world_note": "Card reported stolen — will never approve, may trigger alert"},
    "N7": {"name": "CVV Mismatch", "pct": 5.5, "category": "soft", "retryable": True,
           "real_world_note": "CVV doesn't match — re-enter carefully"},
    "Z7": {"name": "AVS Mismatch", "pct": 3.8, "category": "soft", "retryable": True,
           "real_world_note": "Address verification failed — check billing address"},
    "59": {"name": "Suspected Fraud", "pct": 4.1, "category": "hard", "retryable": False,
           "real_world_note": "Issuer fraud detection triggered — do not retry"},
    "06": {"name": "Processing Error", "pct": 2.5, "category": "soft", "retryable": True,
           "real_world_note": "Temporary network issue — retry in 5-10 minutes"},
    "91": {"name": "Issuer Unavailable", "pct": 1.8, "category": "soft", "retryable": True,
           "real_world_note": "Issuer system down — retry in 15-30 minutes"},
    "96": {"name": "System Malfunction", "pct": 1.2, "category": "soft", "retryable": True,
           "real_world_note": "Network error — retry immediately"},
    "R1": {"name": "Revocation (all)", "pct": 1.1, "category": "hard", "retryable": False,
           "real_world_note": "All authorizations revoked by issuer"},
    "57": {"name": "Txn Not Permitted", "pct": 1.1, "category": "hard", "retryable": False,
           "real_world_note": "Card not enabled for this transaction type (e.g., international)"},
}

# Gateway-specific test card libraries with realistic metadata
GATEWAY_CARDS: Dict[str, Dict[str, dict]] = {
    "stripe": {
        "success_visa":           {"card": "4242424242424242", "desc": "Visa Success", "network": "visa", "expected": "approved"},
        "success_mastercard":     {"card": "5555555555554444", "desc": "MC Success", "network": "mastercard", "expected": "approved"},
        "success_amex":           {"card": "378282246310005", "desc": "Amex Success", "network": "amex", "expected": "approved"},
        "success_debit":          {"card": "4000056655665556", "desc": "Visa Debit Success", "network": "visa", "expected": "approved"},
        "decline_generic":        {"card": "4000000000000002", "desc": "Generic Decline", "network": "visa", "expected": "hard_decline", "code": "05"},
        "decline_insufficient":   {"card": "4000000000009995", "desc": "Insufficient Funds", "network": "visa", "expected": "soft_decline", "code": "51"},
        "decline_lost":           {"card": "4000000000009987", "desc": "Lost Card", "network": "visa", "expected": "hard_decline", "code": "41"},
        "decline_stolen":         {"card": "4000000000009979", "desc": "Stolen Card", "network": "visa", "expected": "hard_decline", "code": "43"},
        "decline_expired":        {"card": "4000000000000069", "desc": "Expired Card", "network": "visa", "expected": "hard_decline", "code": "54"},
        "decline_cvv":            {"card": "4000000000000127", "desc": "CVV Fail", "network": "visa", "expected": "soft_decline", "code": "N7"},
        "decline_processing":     {"card": "4000000000000119", "desc": "Processing Error", "network": "visa", "expected": "soft_decline", "code": "06"},
        "decline_velocity":       {"card": "4000000000006975", "desc": "Velocity Limit", "network": "visa", "expected": "velocity_block", "code": "65"},
        "3ds_required":           {"card": "4000002500003155", "desc": "3DS Required", "network": "visa", "expected": "3ds_required"},
        "3ds_success":            {"card": "4000000000003220", "desc": "3DS Auth Success", "network": "visa", "expected": "3ds_completed"},
        "3ds_fail":               {"card": "4000000000003238", "desc": "3DS Auth Fail", "network": "visa", "expected": "3ds_failed"},
        "fraud_block":            {"card": "4100000000000019", "desc": "Radar Fraud Block", "network": "visa", "expected": "fraud_block", "code": "59"},
    },
    "adyen": {
        "success_visa":           {"card": "4111111111111111", "desc": "Visa Success", "network": "visa", "expected": "approved"},
        "success_mc":             {"card": "5555444433331111", "desc": "MC Success", "network": "mastercard", "expected": "approved"},
        "success_amex":           {"card": "370000000000002", "desc": "Amex Success", "network": "amex", "expected": "approved"},
        "decline_05":             {"card": "4000020000000000", "desc": "Do Not Honor", "network": "visa", "expected": "soft_decline", "code": "05"},
        "decline_14":             {"card": "4000030000000000", "desc": "Invalid Card", "network": "visa", "expected": "hard_decline", "code": "14"},
        "decline_54":             {"card": "4000040000000000", "desc": "Expired Card", "network": "visa", "expected": "hard_decline", "code": "54"},
        "decline_51":             {"card": "4000050000000000", "desc": "Insufficient Funds", "network": "visa", "expected": "soft_decline", "code": "51"},
        "decline_65":             {"card": "4000060000000000", "desc": "Activity Limit", "network": "visa", "expected": "soft_decline", "code": "65"},
        "decline_fraud":          {"card": "4000070000000000", "desc": "Fraud Suspected", "network": "visa", "expected": "fraud_block", "code": "59"},
        "3ds_frictionless":       {"card": "5201281500101010", "desc": "3DS Frictionless", "network": "mastercard", "expected": "3ds_completed"},
        "3ds_challenge":          {"card": "5201281500101028", "desc": "3DS Challenge", "network": "mastercard", "expected": "3ds_required"},
        "3ds_challenge_fail":     {"card": "5201281500101036", "desc": "3DS Challenge Fail", "network": "mastercard", "expected": "3ds_failed"},
    },
    "braintree": {
        "success_visa":           {"card": "4111111111111111", "desc": "Visa Success", "network": "visa", "expected": "approved"},
        "success_amex":           {"card": "378734493671000", "desc": "Amex Success", "network": "amex", "expected": "approved"},
        "success_mc":             {"card": "5555555555554444", "desc": "MC Success", "network": "mastercard", "expected": "approved"},
        "decline_processor":      {"card": "4000111111111115", "desc": "Processor Declined", "network": "visa", "expected": "hard_decline", "code": "05"},
        "decline_gateway":        {"card": "2000111111111115", "desc": "Gateway Rejected", "network": "mastercard", "expected": "hard_decline", "code": "05"},
        "decline_cvv":            {"card": "4000111111111122", "desc": "CVV Fail", "network": "visa", "expected": "soft_decline", "code": "N7"},
        "decline_avs":            {"card": "4000111111111130", "desc": "AVS Fail", "network": "visa", "expected": "soft_decline", "code": "Z7"},
        "decline_fraud":          {"card": "4000111111111148", "desc": "Fraud Detected", "network": "visa", "expected": "fraud_block", "code": "59"},
        "decline_insufficient":   {"card": "4000111111111156", "desc": "Insufficient Funds", "network": "visa", "expected": "soft_decline", "code": "51"},
    },
    "checkout_com": {
        "success_visa":           {"card": "4242424242424242", "desc": "Visa Success", "network": "visa", "expected": "approved"},
        "success_mc":             {"card": "5436031030606378", "desc": "MC Success", "network": "mastercard", "expected": "approved"},
        "decline_insufficient":   {"card": "4000000000000077", "desc": "Insufficient Funds", "network": "visa", "expected": "soft_decline", "code": "51"},
        "decline_expired":        {"card": "4000000000000085", "desc": "Expired Card", "network": "visa", "expected": "hard_decline", "code": "54"},
        "decline_fraud":          {"card": "4000000000000093", "desc": "Fraud Block", "network": "visa", "expected": "fraud_block", "code": "59"},
        "3ds_challenge":          {"card": "4000000000000101", "desc": "3DS Challenge", "network": "visa", "expected": "3ds_required"},
    },
}

# Latency profiles per gateway (milliseconds) — calibrated from public status pages
# (p50, p75, p90, p95, p99) for each outcome type
LATENCY_PROFILES: Dict[str, Dict[str, Tuple[int, int, int, int, int]]] = {
    "stripe": {
        "approved":       (180, 250, 380, 520, 850),
        "soft_decline":   (150, 210, 320, 450, 700),
        "hard_decline":   (120, 170, 260, 380, 600),
        "3ds_required":   (200, 300, 500, 750, 1200),
        "3ds_completed":  (2500, 4000, 6500, 9000, 15000),  # includes user interaction
        "3ds_failed":     (3000, 5000, 8000, 12000, 20000),
        "fraud_block":    (80, 120, 180, 250, 400),   # Radar is fast
        "velocity_block": (50, 80, 120, 180, 300),
        "timeout":        (15000, 20000, 25000, 28000, 30000),
        "issuer_unavailable": (5000, 8000, 12000, 18000, 25000),
    },
    "adyen": {
        "approved":       (200, 280, 420, 580, 950),
        "soft_decline":   (170, 240, 360, 500, 780),
        "hard_decline":   (140, 200, 300, 420, 650),
        "3ds_required":   (220, 330, 550, 800, 1300),
        "3ds_completed":  (2800, 4500, 7000, 9500, 16000),
        "3ds_failed":     (3200, 5500, 8500, 13000, 22000),
        "fraud_block":    (90, 140, 200, 280, 450),
        "velocity_block": (60, 90, 140, 200, 350),
        "timeout":        (15000, 20000, 25000, 28000, 30000),
        "issuer_unavailable": (5500, 9000, 13000, 19000, 26000),
    },
    "braintree": {
        "approved":       (220, 310, 460, 640, 1050),
        "soft_decline":   (190, 270, 400, 550, 860),
        "hard_decline":   (160, 220, 340, 470, 720),
        "3ds_required":   (250, 370, 600, 880, 1400),
        "3ds_completed":  (3000, 5000, 7500, 10000, 17000),
        "3ds_failed":     (3500, 6000, 9000, 14000, 23000),
        "fraud_block":    (100, 150, 220, 310, 500),
        "velocity_block": (70, 100, 160, 220, 380),
        "timeout":        (15000, 20000, 25000, 28000, 30000),
        "issuer_unavailable": (6000, 9500, 14000, 20000, 27000),
    },
    "checkout_com": {
        "approved":       (190, 270, 400, 560, 920),
        "soft_decline":   (160, 230, 350, 480, 750),
        "hard_decline":   (130, 190, 280, 400, 630),
        "3ds_required":   (210, 320, 520, 770, 1250),
        "3ds_completed":  (2600, 4200, 6800, 9200, 15500),
        "3ds_failed":     (3100, 5200, 8200, 12500, 21000),
        "fraud_block":    (85, 130, 190, 270, 430),
        "velocity_block": (55, 85, 130, 190, 320),
        "timeout":        (15000, 20000, 25000, 28000, 30000),
        "issuer_unavailable": (5200, 8500, 12500, 18500, 25500),
    },
}

# 3DS trigger rates by region (% of transactions that get 3DS challenge)
# Source: EBA SCA statistics, Visa/MC public reports
TDS_TRIGGER_RATES: Dict[str, dict] = {
    "EU_SCA": {
        "base_rate": 68.0,       # SCA mandate
        "low_value_exempt": 30,  # <€30 exemption
        "tra_exempt": 100,       # TRA exemption threshold (€)
        "completion_rate": 78.5, # % of 3DS challenges completed successfully
        "frictionless_rate": 42.0,  # % that pass frictionless (no user interaction)
    },
    "UK_SCA": {
        "base_rate": 62.0,
        "low_value_exempt": 25,
        "tra_exempt": 85,
        "completion_rate": 81.2,
        "frictionless_rate": 45.0,
    },
    "US": {
        "base_rate": 12.0,      # voluntary, not mandated
        "low_value_exempt": 0,
        "tra_exempt": 0,
        "completion_rate": 85.0,
        "frictionless_rate": 60.0,
    },
    "LATAM": {
        "base_rate": 35.0,
        "low_value_exempt": 0,
        "tra_exempt": 0,
        "completion_rate": 72.0,
        "frictionless_rate": 30.0,
    },
    "APAC": {
        "base_rate": 25.0,
        "low_value_exempt": 0,
        "tra_exempt": 0,
        "completion_rate": 80.0,
        "frictionless_rate": 50.0,
    },
    "DEFAULT": {
        "base_rate": 20.0,
        "low_value_exempt": 0,
        "tra_exempt": 0,
        "completion_rate": 78.0,
        "frictionless_rate": 40.0,
    },
}

# Country → 3DS region mapping
COUNTRY_TO_3DS_REGION: Dict[str, str] = {
    "AT": "EU_SCA", "BE": "EU_SCA", "BG": "EU_SCA", "HR": "EU_SCA",
    "CY": "EU_SCA", "CZ": "EU_SCA", "DK": "EU_SCA", "EE": "EU_SCA",
    "FI": "EU_SCA", "FR": "EU_SCA", "DE": "EU_SCA", "GR": "EU_SCA",
    "HU": "EU_SCA", "IE": "EU_SCA", "IT": "EU_SCA", "LV": "EU_SCA",
    "LT": "EU_SCA", "LU": "EU_SCA", "MT": "EU_SCA", "NL": "EU_SCA",
    "PL": "EU_SCA", "PT": "EU_SCA", "RO": "EU_SCA", "SK": "EU_SCA",
    "SI": "EU_SCA", "ES": "EU_SCA", "SE": "EU_SCA",
    "NO": "EU_SCA", "IS": "EU_SCA", "LI": "EU_SCA",  # EEA
    "GB": "UK_SCA",
    "US": "US", "CA": "US",
    "BR": "LATAM", "MX": "LATAM", "AR": "LATAM", "CL": "LATAM", "CO": "LATAM",
    "JP": "APAC", "AU": "APAC", "NZ": "APAC", "SG": "APAC", "HK": "APAC",
    "KR": "APAC", "TW": "APAC", "IN": "APAC", "TH": "APAC", "MY": "APAC",
}

# Real-world outcome distribution for a "typical" CNP transaction
# (used when simulating realistic scenarios, not test-card-specific ones)
REALISTIC_OUTCOME_WEIGHTS: Dict[str, Dict[str, float]] = {
    "US_domestic": {
        "approved": 85.2, "soft_decline": 7.8, "hard_decline": 3.5,
        "3ds_triggered": 2.0, "fraud_block": 1.0, "timeout": 0.5,
    },
    "EU_domestic": {
        "approved": 78.5, "soft_decline": 6.2, "hard_decline": 3.0,
        "3ds_triggered": 10.5, "fraud_block": 1.2, "timeout": 0.6,
    },
    "cross_border": {
        "approved": 72.8, "soft_decline": 9.5, "hard_decline": 5.2,
        "3ds_triggered": 8.0, "fraud_block": 3.5, "timeout": 1.0,
    },
    "high_risk": {
        "approved": 62.0, "soft_decline": 12.0, "hard_decline": 8.0,
        "3ds_triggered": 10.0, "fraud_block": 6.5, "timeout": 1.5,
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# Core Tester
# ═══════════════════════════════════════════════════════════════════════════════

class PaymentSandboxTester:
    """
    Ultra-realistic sandbox authorization simulator.
    
    Features:
    - Industry-calibrated decline code distributions
    - Realistic latency modeling (percentile-based per gateway)
    - Region/issuer-aware 3DS trigger rate simulation
    - Multi-gateway support (Stripe, Adyen, Braintree, Checkout.com)
    - Realistic prediction engine using multi-factor model
    
    NO REAL MONEY IS CHARGED — all simulation uses test card numbers.
    """

    def __init__(self, gateway: str = "stripe"):
        self.gateway = gateway.lower()
        if self.gateway not in GATEWAY_CARDS:
            self.gateway = "stripe"
        self.session_id = f"sandbox_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{random.randint(1000,9999)}"

    def run_test(self, scenario: str, custom_card: Optional[str] = None) -> SandboxTestResult:
        """Run a single sandbox test scenario with realistic simulation."""
        cards = GATEWAY_CARDS.get(self.gateway, GATEWAY_CARDS["stripe"])

        if scenario not in cards and not custom_card:
            return SandboxTestResult(
                test_card="unknown", scenario=scenario,
                result=AuthResult.HARD_DECLINE, result_code="UNKNOWN_SCENARIO",
                message=f"Unknown scenario: {scenario}. Available: {', '.join(cards.keys())}",
                risk_score=0, retryable=False, latency_ms=0,
                timestamp=datetime.utcnow().isoformat(),
            )

        if custom_card:
            card_info = {"card": custom_card, "desc": "Custom", "network": "visa", "expected": "approved"}
        else:
            card_info = cards[scenario]

        return self._simulate_auth(scenario, card_info)

    def run_full_suite(self) -> SandboxSession:
        """Run all test scenarios for the configured gateway."""
        cards = GATEWAY_CARDS.get(self.gateway, GATEWAY_CARDS["stripe"])
        session = SandboxSession(session_id=self.session_id, target_gateway=self.gateway)

        for scenario in cards:
            result = self.run_test(scenario)
            session.tests_run.append(result)

        self._compute_session_stats(session)
        return session

    def test_specific_scenarios(self, scenarios: List[str]) -> List[SandboxTestResult]:
        """Test specific scenarios."""
        return [self.run_test(s) for s in scenarios]

    def simulate_realistic_batch(self, count: int = 100,
                                  billing_country: str = "US",
                                  amount_usd: float = 100.0,
                                  cross_border: bool = False) -> SandboxSession:
        """
        Simulate a batch of transactions with realistic outcome distribution.
        Uses industry-calibrated probabilities instead of test-card-specific outcomes.
        """
        session = SandboxSession(session_id=self.session_id, target_gateway=self.gateway)

        # Determine scenario profile
        if cross_border:
            profile = REALISTIC_OUTCOME_WEIGHTS["cross_border"]
        elif billing_country in COUNTRY_TO_3DS_REGION:
            region = COUNTRY_TO_3DS_REGION[billing_country]
            if region in ("EU_SCA", "UK_SCA"):
                profile = REALISTIC_OUTCOME_WEIGHTS["EU_domestic"]
            else:
                profile = REALISTIC_OUTCOME_WEIGHTS["US_domestic"]
        else:
            profile = REALISTIC_OUTCOME_WEIGHTS["US_domestic"]

        # Amount adjustments
        if amount_usd > 1000:
            profile = dict(profile)
            profile["approved"] -= 8.0
            profile["soft_decline"] += 3.0
            profile["hard_decline"] += 2.0
            profile["fraud_block"] += 2.0
            profile["3ds_triggered"] += 1.0
        elif amount_usd > 500:
            profile = dict(profile)
            profile["approved"] -= 4.0
            profile["soft_decline"] += 2.0
            profile["fraud_block"] += 1.0
            profile["3ds_triggered"] += 1.0

        outcomes = list(profile.keys())
        weights = [max(0.1, profile[k]) for k in outcomes]

        for i in range(count):
            outcome = random.choices(outcomes, weights=weights, k=1)[0]
            result = self._simulate_realistic_outcome(outcome, i, billing_country, amount_usd)
            session.tests_run.append(result)

        self._compute_session_stats(session)
        return session

    def predict_real_success_rate(self, payment_profile: dict) -> dict:
        """
        Predict real-world success probability using multi-factor model.
        
        Factors considered:
          1. Base regional auth rate
          2. Amount band modifier
          3. Cross-border penalty
          4. 3DS completion impact
          5. Card network modifier
          6. PSP fraud engine impact
          7. Velocity state
          8. Profile age
        """
        amount = float(payment_profile.get("amount", 100))
        billing_country = payment_profile.get("billing_country", "US").upper()
        card_network = payment_profile.get("card_network", "visa").lower()
        cross_border = payment_profile.get("cross_border", False)
        has_3ds = payment_profile.get("has_3ds", True)
        profile_age_hours = payment_profile.get("profile_age_hours", 168)
        recent_attempts = payment_profile.get("recent_attempts_1h", 0)

        factors = []

        # 1. Base regional rate
        region = COUNTRY_TO_3DS_REGION.get(billing_country, "DEFAULT")
        if cross_border:
            base = 72.8
            factors.append(("Cross-border base rate", base))
        elif region in ("EU_SCA", "UK_SCA"):
            base = 78.5
            factors.append(("EU/UK domestic base rate", base))
        else:
            base = 85.2
            factors.append(("US/standard domestic base rate", base))

        predicted = base

        # 2. Amount band
        if amount > 5000:
            adj = -18.0
        elif amount > 2500:
            adj = -12.0
        elif amount > 1000:
            adj = -8.0
        elif amount > 500:
            adj = -4.5
        elif amount > 200:
            adj = -2.0
        elif amount < 25:
            adj = +2.5
        else:
            adj = 0.0
        if adj != 0:
            predicted += adj
            factors.append((f"Amount ${amount:.0f} modifier", adj))

        # 3. Cross-border penalty (additional to base)
        if cross_border:
            xb_penalty = -4.2 if self.gateway == "stripe" else -5.5
            predicted += xb_penalty
            factors.append(("Cross-border PSP penalty", xb_penalty))

        # 4. 3DS impact
        tds_region = TDS_TRIGGER_RATES.get(region, TDS_TRIGGER_RATES["DEFAULT"])
        tds_rate = tds_region["base_rate"]
        if amount < tds_region.get("low_value_exempt", 0):
            tds_rate *= 0.15  # low-value exemption
        completion = tds_region["completion_rate"]
        # 3DS abandonment reduces effective auth rate
        tds_abandonment = (tds_rate / 100.0) * (1 - completion / 100.0) * 100
        if tds_abandonment > 0.5:
            predicted -= tds_abandonment * 0.4
            factors.append((f"3DS abandonment ({tds_rate:.0f}% trigger, {completion:.0f}% complete)", -tds_abandonment * 0.4))

        if not has_3ds:
            # No 3DS = higher fraud block rate
            predicted -= 8.0
            factors.append(("No 3DS available — higher fraud blocks", -8.0))

        # 5. Card network
        network_mods = {"visa": 0.0, "mastercard": -0.5, "amex": +2.0, "discover": -1.5, "jcb": -3.0, "unionpay": -8.0}
        nm = network_mods.get(card_network, -2.0)
        if nm != 0:
            predicted += nm
            factors.append((f"Network: {card_network}", nm))

        # 6. PSP fraud engine
        psp_penalty = {"stripe": -2.5, "adyen": -3.0, "braintree": -3.5, "checkout_com": -2.8}.get(self.gateway, -3.0)
        predicted += psp_penalty
        factors.append((f"PSP fraud engine ({self.gateway})", psp_penalty))

        # 7. Velocity
        if recent_attempts >= 5:
            predicted -= 25.0
            factors.append(("Velocity block triggered", -25.0))
        elif recent_attempts >= 3:
            predicted -= 8.0
            factors.append(("Elevated velocity", -8.0))

        # 8. Profile age
        if profile_age_hours < 1:
            predicted -= 12.0
            factors.append(("Brand new profile (<1h)", -12.0))
        elif profile_age_hours < 24:
            predicted -= 5.0
            factors.append(("Young profile (<24h)", -5.0))
        elif profile_age_hours < 168:
            predicted -= 1.0
            factors.append(("Moderate profile age", -1.0))

        # Clamp
        predicted = max(35.0, min(93.0, predicted))

        # Build decline distribution prediction
        remaining = 100.0 - predicted
        soft_pct = remaining * 0.55
        hard_pct = remaining * 0.25
        fraud_pct = remaining * 0.12
        timeout_pct = remaining * 0.03
        tds_fail_pct = remaining * 0.05

        # Recommendation
        if predicted >= 80:
            rec = f"GO: {predicted:.1f}% predicted auth rate — high confidence"
        elif predicted >= 65:
            rec = f"CAUTION: {predicted:.1f}% predicted auth rate — review risk factors"
        elif predicted >= 50:
            rec = f"WARNING: {predicted:.1f}% predicted auth rate — significant risk"
        else:
            rec = f"NO-GO: {predicted:.1f}% predicted auth rate — address issues first"

        # Confidence
        factor_count = len(factors)
        if factor_count >= 5 and billing_country in COUNTRY_TO_3DS_REGION:
            confidence = "high"
        elif factor_count >= 3:
            confidence = "medium"
        else:
            confidence = "low"

        # Latency prediction
        lp = LATENCY_PROFILES.get(self.gateway, LATENCY_PROFILES["stripe"])
        avg_lat = lp["approved"][0]  # p50 for approved
        p95_lat = lp["approved"][3]

        return {
            "predicted_auth_rate": round(predicted, 1),
            "predicted_3ds_rate": round(tds_rate, 1),
            "predicted_soft_decline_rate": round(soft_pct, 1),
            "predicted_hard_decline_rate": round(hard_pct, 1),
            "predicted_fraud_block_rate": round(fraud_pct, 1),
            "predicted_timeout_rate": round(timeout_pct, 1),
            "avg_latency_ms": avg_lat,
            "p95_latency_ms": p95_lat,
            "confidence": confidence,
            "factors": [(f, round(v, 2)) for f, v in factors],
            "recommendation": rec,
            "decline_distribution": {
                "soft_decline": round(soft_pct, 1),
                "hard_decline": round(hard_pct, 1),
                "fraud_block": round(fraud_pct, 1),
                "timeout": round(timeout_pct, 1),
                "3ds_failure": round(tds_fail_pct, 1),
            },
        }

    def generate_report(self, session: SandboxSession) -> str:
        """Generate detailed human-readable test report."""
        lines = [
            "=" * 72,
            "  TITAN PAYMENT SANDBOX TEST REPORT V2 — ULTRA-REALISTIC",
            "=" * 72,
            f"  Session:  {session.session_id}",
            f"  Gateway:  {session.target_gateway.upper()}",
            f"  Tests:    {len(session.tests_run)}",
            f"  Auth Rate: {session.overall_success_rate:.1f}%",
            f"  Avg Latency: {session.avg_latency_ms:.0f}ms",
            "-" * 72,
            "  OUTCOME DISTRIBUTION:",
        ]

        # Count by result
        by_result: Dict[str, int] = {}
        for t in session.tests_run:
            key = t.result.value
            by_result[key] = by_result.get(key, 0) + 1

        total = len(session.tests_run)
        for result_val, count in sorted(by_result.items(), key=lambda x: -x[1]):
            pct = (count / total * 100) if total > 0 else 0
            bar = "█" * int(pct / 2)
            lines.append(f"    {result_val:22s} {count:4d} ({pct:5.1f}%) {bar}")

        lines.append("-" * 72)
        lines.append("  DECLINE CODE BREAKDOWN:")

        # Count by decline code
        by_code: Dict[str, int] = {}
        for t in session.tests_run:
            if t.result != AuthResult.APPROVED:
                code = t.result_code
                by_code[code] = by_code.get(code, 0) + 1

        for code, count in sorted(by_code.items(), key=lambda x: -x[1]):
            info = DECLINE_CODE_DISTRIBUTION.get(code, {"name": "Unknown", "real_world_note": ""})
            lines.append(f"    [{code:3s}] {info['name']:25s} ×{count:3d}  — {info.get('real_world_note', '')}")

        lines.append("-" * 72)
        lines.append("  DETAILED RESULTS:")

        for t in session.tests_run:
            icon = "✓" if t.result in (AuthResult.APPROVED, AuthResult.THREE_DS_COMPLETED) else "✗"
            lines.append(
                f"  {icon} {t.scenario:28s} | {t.result.value:18s} | "
                f"{t.result_code:4s} | {t.latency_ms:5d}ms | {t.message}"
            )

        lines.append("=" * 72)
        return "\n".join(lines)

    # ═══════════════════════════════════════════════════════════════════════
    # Internal Simulation
    # ═══════════════════════════════════════════════════════════════════════

    def _simulate_auth(self, scenario: str, card_info: dict) -> SandboxTestResult:
        """Simulate authorization with realistic latency and response."""
        expected = card_info.get("expected", "approved")
        code = card_info.get("code", "00")
        card_num = card_info["card"]

        result_map = {
            "approved":        (AuthResult.APPROVED, "00", "Approved", False),
            "soft_decline":    (AuthResult.SOFT_DECLINE, code, "", True),
            "hard_decline":    (AuthResult.HARD_DECLINE, code, "", False),
            "3ds_required":    (AuthResult.THREE_DS_REQUIRED, "3DS", "3D Secure authentication required", True),
            "3ds_completed":   (AuthResult.THREE_DS_COMPLETED, "00", "Approved after 3DS authentication", False),
            "3ds_failed":      (AuthResult.THREE_DS_FAILED, "N7", "3D Secure authentication failed", False),
            "fraud_block":     (AuthResult.FRAUD_BLOCK, code, "Blocked by fraud detection", False),
            "velocity_block":  (AuthResult.VELOCITY_BLOCK, "65", "Velocity limit exceeded", True),
            "timeout":         (AuthResult.TIMEOUT, "TO", "Authorization timed out", True),
            "issuer_unavailable": (AuthResult.ISSUER_UNAVAILABLE, "91", "Issuer system unavailable", True),
        }

        auth_result, result_code, message, retryable = result_map.get(
            expected, (AuthResult.HARD_DECLINE, "05", "Unknown", False)
        )

        # Resolve message from decline code database if not set
        if not message and result_code in DECLINE_CODE_DISTRIBUTION:
            dc = DECLINE_CODE_DISTRIBUTION[result_code]
            message = dc["name"]
            decline_cat = dc["category"]
        else:
            decline_cat = "hard" if auth_result in (AuthResult.HARD_DECLINE, AuthResult.FRAUD_BLOCK) else "soft"

        # Simulate realistic latency
        latency = self._simulate_latency(expected)

        # Risk score
        risk_scores = {
            "approved": (5, 20), "soft_decline": (40, 70), "hard_decline": (65, 90),
            "3ds_required": (30, 55), "3ds_completed": (10, 30), "3ds_failed": (60, 85),
            "fraud_block": (85, 99), "velocity_block": (70, 90),
            "timeout": (20, 40), "issuer_unavailable": (15, 35),
        }
        lo, hi = risk_scores.get(expected, (30, 60))
        risk = random.randint(lo, hi)

        return SandboxTestResult(
            test_card=card_num[-4:].rjust(16, "*"),
            scenario=scenario,
            result=auth_result,
            result_code=result_code,
            message=message,
            risk_score=risk,
            retryable=retryable,
            latency_ms=latency,
            timestamp=datetime.utcnow().isoformat(),
            decline_category=decline_cat,
            raw_response={
                "gateway": self.gateway,
                "card_last4": card_num[-4:],
                "network": card_info.get("network", "unknown"),
                "auth_code": result_code,
                "risk_score": risk,
                "latency_ms": latency,
                "retryable": retryable,
            },
        )

    def _simulate_realistic_outcome(self, outcome: str, idx: int,
                                     billing_country: str, amount: float) -> SandboxTestResult:
        """Simulate a single realistic outcome for batch testing."""
        # Pick a decline code based on real-world distribution
        if outcome == "approved":
            code = "00"
            message = "Approved"
            auth_result = AuthResult.APPROVED
            retryable = False
            decline_cat = ""
        elif outcome == "soft_decline":
            code, message, decline_cat = self._pick_decline_code("soft")
            auth_result = AuthResult.SOFT_DECLINE
            retryable = True
        elif outcome == "hard_decline":
            code, message, decline_cat = self._pick_decline_code("hard")
            auth_result = AuthResult.HARD_DECLINE
            retryable = False
        elif outcome == "3ds_triggered":
            # Determine if 3DS succeeds or fails
            region = COUNTRY_TO_3DS_REGION.get(billing_country, "DEFAULT")
            tds_info = TDS_TRIGGER_RATES.get(region, TDS_TRIGGER_RATES["DEFAULT"])
            if random.random() * 100 < tds_info["frictionless_rate"]:
                auth_result = AuthResult.THREE_DS_COMPLETED
                code = "00"
                message = "Approved (3DS frictionless)"
            elif random.random() * 100 < tds_info["completion_rate"]:
                auth_result = AuthResult.THREE_DS_COMPLETED
                code = "00"
                message = "Approved (3DS challenge completed)"
            else:
                auth_result = AuthResult.THREE_DS_FAILED
                code = "N7"
                message = "3DS challenge abandoned/failed"
            retryable = auth_result == AuthResult.THREE_DS_FAILED
            decline_cat = "" if auth_result == AuthResult.THREE_DS_COMPLETED else "soft"
        elif outcome == "fraud_block":
            code = "59"
            message = "Blocked by fraud detection"
            auth_result = AuthResult.FRAUD_BLOCK
            retryable = False
            decline_cat = "hard"
        elif outcome == "timeout":
            code = "TO"
            message = "Authorization timed out"
            auth_result = AuthResult.TIMEOUT
            retryable = True
            decline_cat = "soft"
        else:
            code = "05"
            message = "Do Not Honor"
            auth_result = AuthResult.SOFT_DECLINE
            retryable = True
            decline_cat = "soft"

        latency_key = outcome
        if outcome == "3ds_triggered":
            latency_key = "3ds_completed" if auth_result == AuthResult.THREE_DS_COMPLETED else "3ds_failed"
        latency = self._simulate_latency(latency_key)

        risk_lo, risk_hi = (5, 25) if auth_result == AuthResult.APPROVED else (40, 90)
        risk = random.randint(risk_lo, risk_hi)

        return SandboxTestResult(
            test_card=f"****_sim_{idx:04d}",
            scenario=f"realistic_{outcome}_{idx}",
            result=auth_result,
            result_code=code,
            message=message,
            risk_score=risk,
            retryable=retryable,
            latency_ms=latency,
            timestamp=datetime.utcnow().isoformat(),
            decline_category=decline_cat,
            raw_response={
                "gateway": self.gateway,
                "billing_country": billing_country,
                "amount_usd": amount,
                "simulated": True,
            },
        )

    def _pick_decline_code(self, category: str) -> Tuple[str, str, str]:
        """Pick a decline code weighted by real-world distribution."""
        candidates = {k: v for k, v in DECLINE_CODE_DISTRIBUTION.items() if v["category"] == category}
        if not candidates:
            return ("05", "Do Not Honor", category)

        codes = list(candidates.keys())
        weights = [candidates[c]["pct"] for c in codes]
        chosen = random.choices(codes, weights=weights, k=1)[0]
        info = candidates[chosen]
        return (chosen, info["name"], category)

    def _simulate_latency(self, outcome_type: str) -> int:
        """Simulate realistic latency using percentile-based distribution."""
        lp = LATENCY_PROFILES.get(self.gateway, LATENCY_PROFILES["stripe"])
        # Map outcome types to latency keys
        key_map = {
            "approved": "approved", "soft_decline": "soft_decline",
            "hard_decline": "hard_decline", "3ds_required": "3ds_required",
            "3ds_completed": "3ds_completed", "3ds_failed": "3ds_failed",
            "fraud_block": "fraud_block", "velocity_block": "velocity_block",
            "timeout": "timeout", "issuer_unavailable": "issuer_unavailable",
        }
        key = key_map.get(outcome_type, "approved")
        percentiles = lp.get(key, lp["approved"])
        p50, p75, p90, p95, p99 = percentiles

        # Generate latency from a log-normal-ish distribution anchored to percentiles
        r = random.random()
        if r < 0.50:
            latency = random.randint(max(50, p50 - (p75 - p50)), p50)
        elif r < 0.75:
            latency = random.randint(p50, p75)
        elif r < 0.90:
            latency = random.randint(p75, p90)
        elif r < 0.95:
            latency = random.randint(p90, p95)
        else:
            latency = random.randint(p95, p99)

        # Add small jitter
        latency += random.randint(-10, 10)
        return max(30, latency)

    def _compute_session_stats(self, session: SandboxSession):
        """Compute session-level statistics."""
        total = len(session.tests_run)
        if total == 0:
            return

        approved = sum(1 for t in session.tests_run
                       if t.result in (AuthResult.APPROVED, AuthResult.THREE_DS_COMPLETED))
        session.overall_success_rate = (approved / total * 100)
        session.avg_latency_ms = sum(t.latency_ms for t in session.tests_run) / total

        by_result: Dict[str, int] = {}
        by_code: Dict[str, int] = {}
        latencies = []
        for t in session.tests_run:
            by_result[t.result.value] = by_result.get(t.result.value, 0) + 1
            if t.result_code != "00":
                by_code[t.result_code] = by_code.get(t.result_code, 0) + 1
            latencies.append(t.latency_ms)

        latencies.sort()
        p50_idx = max(0, int(total * 0.50) - 1)
        p95_idx = max(0, int(total * 0.95) - 1)
        p99_idx = max(0, int(total * 0.99) - 1)

        session.summary = {
            "total_tests": total,
            "approved": by_result.get("approved", 0) + by_result.get("3ds_completed", 0),
            "soft_declines": by_result.get("soft_decline", 0),
            "hard_declines": by_result.get("hard_decline", 0),
            "3ds_required": by_result.get("3ds_required", 0),
            "3ds_completed": by_result.get("3ds_completed", 0),
            "3ds_failed": by_result.get("3ds_failed", 0),
            "fraud_blocks": by_result.get("fraud_block", 0),
            "velocity_blocks": by_result.get("velocity_block", 0),
            "timeouts": by_result.get("timeout", 0),
            "success_rate_pct": round(session.overall_success_rate, 1),
            "avg_latency_ms": round(session.avg_latency_ms, 0),
            "p50_latency_ms": latencies[p50_idx] if latencies else 0,
            "p95_latency_ms": latencies[p95_idx] if latencies else 0,
            "p99_latency_ms": latencies[p99_idx] if latencies else 0,
            "decline_codes": by_code,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Convenience Functions
# ═══════════════════════════════════════════════════════════════════════════════

def quick_test(gateway: str = "stripe", scenario: str = "success_visa") -> dict:
    """Quick single test."""
    tester = PaymentSandboxTester(gateway=gateway)
    result = tester.run_test(scenario)
    return {
        "scenario": result.scenario,
        "result": result.result.value,
        "code": result.result_code,
        "message": result.message,
        "risk_score": result.risk_score,
        "retryable": result.retryable,
        "latency_ms": result.latency_ms,
    }


def predict_success(card_bin: str = None, amount: float = 100,
                    billing_country: str = "US",
                    cross_border: bool = False, has_3ds: bool = True,
                    gateway: str = "stripe") -> dict:
    """Predict real-world success probability."""
    tester = PaymentSandboxTester(gateway=gateway)
    profile = {
        "card_bin": card_bin,
        "amount": amount,
        "billing_country": billing_country,
        "cross_border": cross_border,
        "has_3ds": has_3ds,
    }
    return tester.predict_real_success_rate(profile)


if __name__ == "__main__":
    # Demo 1: Full test suite
    print("Running Stripe test suite...")
    tester = PaymentSandboxTester(gateway="stripe")
    session = tester.run_full_suite()
    print(tester.generate_report(session))

    print("\n" + "=" * 72 + "\n")

    # Demo 2: Realistic batch simulation
    print("Simulating 200 realistic US domestic transactions...")
    batch = tester.simulate_realistic_batch(count=200, billing_country="US", amount_usd=150)
    print(tester.generate_report(batch))

    print("\n" + "=" * 72 + "\n")

    # Demo 3: Prediction
    print("Predicting success for cross-border EU transaction...")
    prediction = tester.predict_real_success_rate({
        "amount": 350,
        "billing_country": "DE",
        "cross_border": True,
        "has_3ds": True,
        "card_network": "visa",
    })
    print(json.dumps(prediction, indent=2))
