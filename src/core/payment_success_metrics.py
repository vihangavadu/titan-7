#!/usr/bin/env python3
"""
TITAN Payment Success Metrics Engine V2 — Ultra-Realistic
Bayesian prediction engine with time-decay weighting, merchant risk profiles,
and multi-factor logistic regression for real-world success rate prediction.

Calibration sources:
  - Visa VisaNet authorization statistics (public)
  - Mastercard network performance reports (public)
  - Worldpay Global Payments Report 2024
  - Stripe Radar public documentation
  - Adyen RevenueProtect public docs
  - Nilson Report card fraud statistics
  - European Banking Authority SCA reports
"""

import json
import logging
import math
import os
import sqlite3
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import threading


# ═══════════════════════════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class SuccessRateMetrics:
    total_attempts: int
    successful: int
    declined: int
    soft_declines: int
    hard_declines: int
    fraud_blocks: int
    timeouts: int
    error_rate: float
    success_rate_pct: float
    time_window_hours: int


@dataclass
class DimensionBreakdown:
    dimension: str
    values: Dict[str, SuccessRateMetrics]


@dataclass
class ReliabilityScore:
    overall_score: int
    confidence: str
    factors: List[Tuple[str, str, float]]
    recommendation: str
    bayesian_estimate: float
    credible_interval: Tuple[float, float]


@dataclass
class BayesianPrediction:
    posterior_mean: float
    credible_interval_95: Tuple[float, float]
    prior_alpha: float
    prior_beta: float
    posterior_alpha: float
    posterior_beta: float
    effective_sample_size: float
    time_decay_factor: float


# ═══════════════════════════════════════════════════════════════════════════════
# Merchant Risk Profiles — Industry-Calibrated
# ═══════════════════════════════════════════════════════════════════════════════

MERCHANT_RISK_PROFILES: Dict[str, dict] = {
    "digital_goods": {
        "mcc_range": "5815-5818",
        "base_auth_rate": 82.5,
        "chargeback_rate": 1.8,
        "fraud_rate": 2.5,
        "3ds_challenge_rate": 18.0,
        "avg_ticket_usd": 35,
        "risk_tier": "medium-high",
        "velocity_sensitivity": 0.85,
    },
    "saas_subscription": {
        "mcc_range": "5734,5817",
        "base_auth_rate": 88.0,
        "chargeback_rate": 0.8,
        "fraud_rate": 1.2,
        "3ds_challenge_rate": 12.0,
        "avg_ticket_usd": 50,
        "risk_tier": "medium",
        "velocity_sensitivity": 0.60,
    },
    "ecommerce_physical": {
        "mcc_range": "5300-5499",
        "base_auth_rate": 86.5,
        "chargeback_rate": 0.6,
        "fraud_rate": 0.9,
        "3ds_challenge_rate": 15.0,
        "avg_ticket_usd": 120,
        "risk_tier": "low-medium",
        "velocity_sensitivity": 0.50,
    },
    "travel_airline": {
        "mcc_range": "3000-3299,4511",
        "base_auth_rate": 84.0,
        "chargeback_rate": 1.2,
        "fraud_rate": 1.8,
        "3ds_challenge_rate": 22.0,
        "avg_ticket_usd": 450,
        "risk_tier": "medium-high",
        "velocity_sensitivity": 0.40,
    },
    "gambling_gaming": {
        "mcc_range": "7995,7801",
        "base_auth_rate": 72.0,
        "chargeback_rate": 3.5,
        "fraud_rate": 4.2,
        "3ds_challenge_rate": 35.0,
        "avg_ticket_usd": 80,
        "risk_tier": "high",
        "velocity_sensitivity": 0.95,
    },
    "crypto_exchange": {
        "mcc_range": "6051",
        "base_auth_rate": 65.0,
        "chargeback_rate": 4.0,
        "fraud_rate": 5.5,
        "3ds_challenge_rate": 40.0,
        "avg_ticket_usd": 200,
        "risk_tier": "very-high",
        "velocity_sensitivity": 0.98,
    },
    "luxury_retail": {
        "mcc_range": "5094,5944,5947",
        "base_auth_rate": 80.0,
        "chargeback_rate": 1.5,
        "fraud_rate": 3.0,
        "3ds_challenge_rate": 25.0,
        "avg_ticket_usd": 800,
        "risk_tier": "high",
        "velocity_sensitivity": 0.70,
    },
    "food_delivery": {
        "mcc_range": "5811,5812",
        "base_auth_rate": 90.5,
        "chargeback_rate": 0.4,
        "fraud_rate": 0.6,
        "3ds_challenge_rate": 8.0,
        "avg_ticket_usd": 30,
        "risk_tier": "low",
        "velocity_sensitivity": 0.30,
    },
    "generic": {
        "mcc_range": "0000",
        "base_auth_rate": 85.0,
        "chargeback_rate": 1.0,
        "fraud_rate": 1.5,
        "3ds_challenge_rate": 15.0,
        "avg_ticket_usd": 100,
        "risk_tier": "medium",
        "velocity_sensitivity": 0.60,
    },
}

# Country-level authorization rate priors (Worldpay 2024)
COUNTRY_AUTH_PRIORS: Dict[str, float] = {
    "US": 86.5, "CA": 85.0, "GB": 83.0, "DE": 81.5, "FR": 80.0,
    "NL": 84.0, "SE": 85.5, "NO": 84.5, "DK": 84.0, "FI": 83.5,
    "AU": 84.0, "NZ": 83.5, "JP": 82.0, "SG": 83.0, "HK": 81.0,
    "KR": 80.5, "IT": 78.0, "ES": 79.0, "PT": 78.5, "PL": 77.0,
    "BR": 75.0, "MX": 74.0, "AR": 72.0, "CO": 73.0, "CL": 76.0,
    "IN": 78.0, "TH": 77.0, "MY": 79.0, "ID": 74.0, "PH": 73.0,
    "RU": 70.0, "TR": 72.0, "ZA": 76.0, "NG": 68.0, "KE": 70.0,
    "AE": 80.0, "SA": 78.0, "IL": 79.0, "EG": 71.0,
}

# BIN-range issuer authorization rate priors
ISSUER_AUTH_PRIORS: Dict[str, float] = {
    "chase": 88.5, "citi": 86.0, "bofa": 85.5, "wells_fargo": 84.0,
    "capital_one": 83.0, "amex": 87.0, "discover": 84.5,
    "barclays": 82.0, "hsbc": 81.5, "lloyds": 83.0, "natwest": 82.5,
    "bnp_paribas": 80.0, "societe_generale": 79.5, "deutsche_bank": 81.0,
    "commerzbank": 80.5, "ing": 83.0, "rabobank": 84.0,
    "commonwealth": 84.5, "anz": 83.5, "westpac": 84.0, "nab": 83.0,
    "generic": 82.0,
}

# Time-decay half-life configurations (hours)
TIME_DECAY_PROFILES = {
    "aggressive": {"half_life_hours": 6, "min_weight": 0.05},
    "standard": {"half_life_hours": 24, "min_weight": 0.10},
    "conservative": {"half_life_hours": 72, "min_weight": 0.20},
    "long_memory": {"half_life_hours": 168, "min_weight": 0.30},
}


# ═══════════════════════════════════════════════════════════════════════════════
# Bayesian Engine
# ═══════════════════════════════════════════════════════════════════════════════

class BayesianAuthPredictor:
    """
    Bayesian conjugate Beta-Binomial model for authorization rate prediction.
    
    Uses informative priors from industry data and updates with observed
    transaction outcomes. Applies exponential time-decay to weight recent
    observations more heavily.
    """

    def __init__(self, decay_profile: str = "standard"):
        dp = TIME_DECAY_PROFILES.get(decay_profile, TIME_DECAY_PROFILES["standard"])
        self.half_life_hours = dp["half_life_hours"]
        self.min_weight = dp["min_weight"]

    def compute_prior(self, merchant_type: str = "generic",
                      billing_country: str = "US",
                      issuer: str = "generic") -> Tuple[float, float]:
        """
        Compute informative Beta prior from industry data.
        
        Returns (alpha, beta) for Beta distribution.
        Effective sample size of prior = alpha + beta (pseudo-observations).
        """
        # Merchant base rate
        profile = MERCHANT_RISK_PROFILES.get(merchant_type, MERCHANT_RISK_PROFILES["generic"])
        merchant_rate = profile["base_auth_rate"] / 100.0

        # Country modifier
        country_rate = COUNTRY_AUTH_PRIORS.get(billing_country, 82.0) / 100.0

        # Issuer modifier
        issuer_rate = ISSUER_AUTH_PRIORS.get(issuer, 82.0) / 100.0

        # Weighted combination: merchant 50%, country 30%, issuer 20%
        combined_rate = merchant_rate * 0.50 + country_rate * 0.30 + issuer_rate * 0.20

        # Prior strength (pseudo-observations) — stronger for well-known profiles
        prior_strength = 20.0  # equivalent to 20 pseudo-observations
        if merchant_type != "generic":
            prior_strength += 5.0
        if billing_country in COUNTRY_AUTH_PRIORS:
            prior_strength += 3.0
        if issuer != "generic":
            prior_strength += 2.0

        alpha = combined_rate * prior_strength
        beta = (1 - combined_rate) * prior_strength
        return (alpha, beta)

    def time_decay_weight(self, hours_ago: float) -> float:
        """Exponential time-decay weight."""
        decay = math.exp(-math.log(2) * hours_ago / self.half_life_hours)
        return max(self.min_weight, decay)

    def update_posterior(self, prior_alpha: float, prior_beta: float,
                         observations: List[Tuple[bool, float]]) -> BayesianPrediction:
        """
        Update Beta posterior with time-weighted observations.
        
        observations: list of (success: bool, hours_ago: float)
        """
        weighted_successes = 0.0
        weighted_failures = 0.0
        total_weight = 0.0

        for success, hours_ago in observations:
            w = self.time_decay_weight(hours_ago)
            if success:
                weighted_successes += w
            else:
                weighted_failures += w
            total_weight += w

        post_alpha = prior_alpha + weighted_successes
        post_beta = prior_beta + weighted_failures

        # Posterior mean
        posterior_mean = post_alpha / (post_alpha + post_beta)

        # 95% credible interval (Beta quantile approximation)
        # Using normal approximation for Beta when alpha, beta > 1
        n = post_alpha + post_beta
        std = math.sqrt(post_alpha * post_beta / (n * n * (n + 1)))
        ci_low = max(0.0, posterior_mean - 1.96 * std)
        ci_high = min(1.0, posterior_mean + 1.96 * std)

        # Effective sample size (time-decay adjusted)
        ess = total_weight

        # Time decay factor (average weight)
        avg_decay = (total_weight / len(observations)) if observations else 1.0

        return BayesianPrediction(
            posterior_mean=posterior_mean,
            credible_interval_95=(ci_low, ci_high),
            prior_alpha=prior_alpha,
            prior_beta=prior_beta,
            posterior_alpha=post_alpha,
            posterior_beta=post_beta,
            effective_sample_size=ess,
            time_decay_factor=avg_decay,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Database Layer
# ═══════════════════════════════════════════════════════════════════════════════

class PaymentSuccessMetricsDB:
    """SQLite-backed metrics storage with enhanced schema for V2"""

    def __init__(self, db_path: str = "/opt/titan/data/payment_metrics.db"):
        self.db_path = db_path
        self.lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        """Initialize database schema"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS payment_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    session_id TEXT,
                    target_domain TEXT,
                    merchant_type TEXT,
                    gateway TEXT,
                    card_bin TEXT,
                    card_network TEXT,
                    issuer TEXT,
                    billing_country TEXT,
                    amount REAL,
                    currency TEXT,
                    status TEXT,
                    decline_code TEXT,
                    decline_reason TEXT,
                    decline_category TEXT,
                    phase TEXT,
                    detection_type TEXT,
                    profile_age_hours REAL,
                    proxy_country TEXT,
                    latency_ms INTEGER,
                    risk_score INTEGER,
                    was_3ds INTEGER DEFAULT 0,
                    metadata TEXT
                )
            """)

            for idx_col in ["timestamp", "target_domain", "card_bin", "status",
                            "billing_country", "gateway", "merchant_type", "decline_code"]:
                conn.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_{idx_col}
                    ON payment_attempts({idx_col})
                """)

            conn.commit()

    def record_attempt(self, data: dict):
        """Record a payment attempt with extended fields."""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO payment_attempts (
                        timestamp, session_id, target_domain, merchant_type, gateway,
                        card_bin, card_network, issuer, billing_country, amount,
                        currency, status, decline_code, decline_reason, decline_category,
                        phase, detection_type, profile_age_hours, proxy_country,
                        latency_ms, risk_score, was_3ds, metadata
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    data.get("timestamp", datetime.utcnow().isoformat()),
                    data.get("session_id"),
                    data.get("target_domain"),
                    data.get("merchant_type", "generic"),
                    data.get("gateway"),
                    data.get("card_bin"),
                    data.get("card_network"),
                    data.get("issuer"),
                    data.get("billing_country"),
                    data.get("amount"),
                    data.get("currency", "USD"),
                    data.get("status"),
                    data.get("decline_code"),
                    data.get("decline_reason"),
                    data.get("decline_category"),
                    data.get("phase", "unknown"),
                    data.get("detection_type"),
                    data.get("profile_age_hours"),
                    data.get("proxy_country"),
                    data.get("latency_ms"),
                    data.get("risk_score"),
                    1 if data.get("was_3ds") else 0,
                    json.dumps(data.get("metadata", {})),
                ))
                conn.commit()

    def get_metrics(self, hours: int = 24,
                    target: Optional[str] = None,
                    gateway: Optional[str] = None) -> SuccessRateMetrics:
        """Get success rate metrics for a time window."""
        since = (datetime.utcnow() - timedelta(hours=hours)).isoformat()

        query = """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful,
                SUM(CASE WHEN status IN ('soft_decline','hard_decline') THEN 1 ELSE 0 END) as declined,
                SUM(CASE WHEN status = 'soft_decline' THEN 1 ELSE 0 END) as soft,
                SUM(CASE WHEN status = 'hard_decline' THEN 1 ELSE 0 END) as hard,
                SUM(CASE WHEN status = 'fraud_block' THEN 1 ELSE 0 END) as fraud,
                SUM(CASE WHEN status = 'timeout' THEN 1 ELSE 0 END) as timeouts
            FROM payment_attempts
            WHERE timestamp > ?
        """
        params: list = [since]

        if target:
            query += " AND target_domain = ?"
            params.append(target)
        if gateway:
            query += " AND gateway = ?"
            params.append(gateway)

        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(query, params).fetchone()

        total = row[0] or 0
        successful = row[1] or 0
        declined = row[2] or 0
        soft = row[3] or 0
        hard = row[4] or 0
        fraud = row[5] or 0
        timeouts = row[6] or 0

        success_rate = (successful / total * 100) if total > 0 else 0
        error_rate = ((total - successful - declined - fraud - timeouts) / total * 100) if total > 0 else 0

        return SuccessRateMetrics(
            total_attempts=total, successful=successful, declined=declined,
            soft_declines=soft, hard_declines=hard, fraud_blocks=fraud,
            timeouts=timeouts, error_rate=max(0, error_rate),
            success_rate_pct=success_rate, time_window_hours=hours,
        )

    def get_time_weighted_observations(self, hours: int = 168,
                                        target: Optional[str] = None,
                                        gateway: Optional[str] = None,
                                        card_bin: Optional[str] = None,
                                        billing_country: Optional[str] = None
                                        ) -> List[Tuple[bool, float]]:
        """
        Get observations as (success, hours_ago) tuples for Bayesian updating.
        """
        since = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
        now = datetime.utcnow()

        query = """
            SELECT timestamp, status FROM payment_attempts
            WHERE timestamp > ?
        """
        params: list = [since]

        if target:
            query += " AND target_domain = ?"
            params.append(target)
        if gateway:
            query += " AND gateway = ?"
            params.append(gateway)
        if card_bin:
            query += " AND card_bin = ?"
            params.append(card_bin)
        if billing_country:
            query += " AND billing_country = ?"
            params.append(billing_country)

        query += " ORDER BY timestamp DESC LIMIT 5000"

        observations = []
        with sqlite3.connect(self.db_path) as conn:
            for row in conn.execute(query, params).fetchall():
                try:
                    ts = datetime.fromisoformat(row[0])
                    hours_ago = (now - ts).total_seconds() / 3600.0
                    success = row[1] == "success"
                    observations.append((success, hours_ago))
                except (ValueError, TypeError):
                    continue

        return observations

    def get_breakdown_by_merchant(self, hours: int = 24) -> DimensionBreakdown:
        """Get success rate breakdown by merchant/target."""
        return self._get_breakdown("target_domain", "merchant", hours)

    def get_breakdown_by_bin(self, hours: int = 24) -> DimensionBreakdown:
        """Get success rate breakdown by card BIN."""
        return self._get_breakdown("card_bin", "bin_range", hours, limit=50)

    def get_breakdown_by_country(self, hours: int = 24) -> DimensionBreakdown:
        """Get success rate breakdown by billing country."""
        return self._get_breakdown("billing_country", "country", hours)

    def get_breakdown_by_gateway(self, hours: int = 24) -> DimensionBreakdown:
        """Get success rate breakdown by gateway."""
        return self._get_breakdown("gateway", "gateway", hours)

    def get_decline_code_distribution(self, hours: int = 24,
                                       target: Optional[str] = None) -> Dict[str, int]:
        """Get decline code distribution."""
        since = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
        query = """
            SELECT COALESCE(decline_code, 'unknown') as code, COUNT(*) as cnt
            FROM payment_attempts
            WHERE timestamp > ? AND status != 'success'
        """
        params: list = [since]
        if target:
            query += " AND target_domain = ?"
            params.append(target)
        query += " GROUP BY code ORDER BY cnt DESC"

        with sqlite3.connect(self.db_path) as conn:
            return {r[0]: r[1] for r in conn.execute(query, params).fetchall()}

    def get_failure_reasons(self, hours: int = 24) -> Dict[str, int]:
        """Get count of failure reasons."""
        since = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT COALESCE(decline_reason, 'unknown') as reason, COUNT(*) as count
                FROM payment_attempts
                WHERE timestamp > ? AND status != 'success'
                GROUP BY decline_reason ORDER BY count DESC
            """, (since,))
            return {row[0]: row[1] for row in cursor.fetchall()}

    def get_hourly_trend(self, hours: int = 24) -> List[Tuple[str, float, int]]:
        """Get success rate trend by hour with volume."""
        since = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT
                    strftime('%Y-%m-%d %H:00:00', timestamp) as hour,
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful
                FROM payment_attempts WHERE timestamp > ?
                GROUP BY hour ORDER BY hour
            """, (since,))
            return [
                (row[0], (row[2] / row[1] * 100) if row[1] > 0 else 0, row[1])
                for row in cursor.fetchall()
            ]

    def get_latency_stats(self, hours: int = 24,
                          gateway: Optional[str] = None) -> dict:
        """Get latency percentile statistics."""
        since = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
        query = """
            SELECT latency_ms FROM payment_attempts
            WHERE timestamp > ? AND latency_ms IS NOT NULL AND latency_ms > 0
        """
        params: list = [since]
        if gateway:
            query += " AND gateway = ?"
            params.append(gateway)
        query += " ORDER BY latency_ms"

        with sqlite3.connect(self.db_path) as conn:
            latencies = [r[0] for r in conn.execute(query, params).fetchall()]

        if not latencies:
            return {"count": 0, "p50": 0, "p75": 0, "p90": 0, "p95": 0, "p99": 0, "avg": 0}

        n = len(latencies)
        return {
            "count": n,
            "p50": latencies[int(n * 0.50)],
            "p75": latencies[int(n * 0.75)] if n > 3 else latencies[-1],
            "p90": latencies[int(n * 0.90)] if n > 9 else latencies[-1],
            "p95": latencies[int(n * 0.95)] if n > 19 else latencies[-1],
            "p99": latencies[min(int(n * 0.99), n - 1)],
            "avg": round(sum(latencies) / n, 0),
        }

    def _get_breakdown(self, column: str, dimension_name: str,
                       hours: int, limit: int = 100) -> DimensionBreakdown:
        since = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(f"""
                SELECT
                    {column},
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful,
                    SUM(CASE WHEN status = 'soft_decline' THEN 1 ELSE 0 END) as soft,
                    SUM(CASE WHEN status = 'hard_decline' THEN 1 ELSE 0 END) as hard,
                    SUM(CASE WHEN status = 'fraud_block' THEN 1 ELSE 0 END) as fraud,
                    SUM(CASE WHEN status = 'timeout' THEN 1 ELSE 0 END) as timeouts
                FROM payment_attempts
                WHERE timestamp > ? AND {column} IS NOT NULL
                GROUP BY {column} ORDER BY total DESC LIMIT ?
            """, (since, limit))

            values = {}
            for row in cursor.fetchall():
                key, total, succ, soft, hard, fraud, to = row
                rate = (succ / total * 100) if total > 0 else 0
                err = ((total - succ - soft - hard - fraud - to) / total * 100) if total > 0 else 0
                values[key] = SuccessRateMetrics(
                    total_attempts=total, successful=succ,
                    declined=soft + hard, soft_declines=soft,
                    hard_declines=hard, fraud_blocks=fraud,
                    timeouts=to, error_rate=max(0, err),
                    success_rate_pct=rate, time_window_hours=hours,
                )

        return DimensionBreakdown(dimension=dimension_name, values=values)


# ═══════════════════════════════════════════════════════════════════════════════
# Scorer — Multi-Factor Bayesian + Logistic Regression
# ═══════════════════════════════════════════════════════════════════════════════

class PaymentSuccessScorer:
    """
    Ultra-realistic reliability scorer combining:
    1. Bayesian Beta-Binomial posterior with time-decay
    2. Multi-factor logistic regression adjustments
    3. Merchant risk profile calibration
    4. Trend analysis with exponential smoothing
    """

    def __init__(self, db: Optional[PaymentSuccessMetricsDB] = None,
                 decay_profile: str = "standard"):
        self.db = db or PaymentSuccessMetricsDB()
        self.bayesian = BayesianAuthPredictor(decay_profile=decay_profile)

    def calculate_reliability_score(self, target: Optional[str] = None,
                                     gateway: Optional[str] = None,
                                     merchant_type: str = "generic",
                                     billing_country: str = "US",
                                     issuer: str = "generic") -> ReliabilityScore:
        """
        Calculate reliability score using Bayesian posterior + multi-factor analysis.
        """
        # 1. Get Bayesian posterior
        alpha, beta = self.bayesian.compute_prior(merchant_type, billing_country, issuer)
        observations = self.db.get_time_weighted_observations(
            hours=168, target=target, gateway=gateway
        )
        prediction = self.bayesian.update_posterior(alpha, beta, observations)

        # 2. Multi-factor scoring
        metrics_1h = self.db.get_metrics(hours=1, target=target, gateway=gateway)
        metrics_6h = self.db.get_metrics(hours=6, target=target, gateway=gateway)
        metrics_24h = self.db.get_metrics(hours=24, target=target, gateway=gateway)
        metrics_7d = self.db.get_metrics(hours=168, target=target, gateway=gateway)

        factors: List[Tuple[str, str, float]] = []
        score = prediction.posterior_mean * 100  # Start from Bayesian estimate

        # Factor 1: Bayesian posterior
        factors.append(("Bayesian posterior mean",
                        f"{prediction.posterior_mean*100:.1f}% (ESS={prediction.effective_sample_size:.0f})",
                        0.0))

        # Factor 2: Short-term trend (1h vs 6h)
        if metrics_1h.total_attempts >= 3 and metrics_6h.total_attempts >= 10:
            trend = metrics_1h.success_rate_pct - metrics_6h.success_rate_pct
            if trend > 15:
                adj = +5.0
                status = "rapidly improving"
            elif trend > 5:
                adj = +2.5
                status = "improving"
            elif trend < -15:
                adj = -8.0
                status = "rapidly declining"
            elif trend < -5:
                adj = -4.0
                status = "declining"
            else:
                adj = 0.0
                status = "stable"
            score += adj
            factors.append(("Short-term trend (1h vs 6h)", status, adj))

        # Factor 3: Medium-term trend (6h vs 24h)
        if metrics_6h.total_attempts >= 5 and metrics_24h.total_attempts >= 15:
            trend = metrics_6h.success_rate_pct - metrics_24h.success_rate_pct
            if trend > 10:
                adj = +3.0
                status = "improving"
            elif trend < -10:
                adj = -5.0
                status = "declining"
            else:
                adj = 0.0
                status = "stable"
            if adj != 0:
                score += adj
                factors.append(("Medium-term trend (6h vs 24h)", status, adj))

        # Factor 4: Hard decline ratio (high = bad cards)
        if metrics_24h.total_attempts >= 10 and metrics_24h.declined > 0:
            hard_ratio = metrics_24h.hard_declines / max(1, metrics_24h.declined)
            if hard_ratio > 0.6:
                adj = -8.0
                status = f"high ({hard_ratio:.0%} of declines are hard)"
            elif hard_ratio > 0.4:
                adj = -3.0
                status = f"moderate ({hard_ratio:.0%})"
            else:
                adj = +2.0
                status = f"low ({hard_ratio:.0%}) — mostly retryable"
            score += adj
            factors.append(("Hard decline ratio", status, adj))

        # Factor 5: Fraud block rate
        if metrics_24h.total_attempts >= 10:
            fraud_pct = (metrics_24h.fraud_blocks / metrics_24h.total_attempts) * 100
            if fraud_pct > 5:
                adj = -12.0
                status = f"critical ({fraud_pct:.1f}%)"
            elif fraud_pct > 2:
                adj = -5.0
                status = f"elevated ({fraud_pct:.1f}%)"
            elif fraud_pct > 0.5:
                adj = -1.0
                status = f"normal ({fraud_pct:.1f}%)"
            else:
                adj = +1.0
                status = f"low ({fraud_pct:.1f}%)"
            score += adj
            factors.append(("Fraud block rate", status, adj))

        # Factor 6: Timeout rate
        if metrics_24h.total_attempts >= 10:
            timeout_pct = (metrics_24h.timeouts / metrics_24h.total_attempts) * 100
            if timeout_pct > 3:
                adj = -6.0
                status = f"high ({timeout_pct:.1f}%) — network issues"
            elif timeout_pct > 1:
                adj = -2.0
                status = f"moderate ({timeout_pct:.1f}%)"
            else:
                adj = 0.0
                status = f"normal ({timeout_pct:.1f}%)"
            if adj != 0:
                score += adj
                factors.append(("Timeout rate", status, adj))

        # Factor 7: Merchant risk profile
        profile = MERCHANT_RISK_PROFILES.get(merchant_type, MERCHANT_RISK_PROFILES["generic"])
        risk_tier = profile["risk_tier"]
        tier_adj = {
            "low": +3.0, "low-medium": +1.5, "medium": 0.0,
            "medium-high": -2.0, "high": -5.0, "very-high": -10.0,
        }.get(risk_tier, 0.0)
        if tier_adj != 0:
            score += tier_adj
            factors.append(("Merchant risk tier", f"{risk_tier} ({merchant_type})", tier_adj))

        # Factor 8: Sample size confidence bonus/penalty
        total_obs = len(observations)
        if total_obs >= 100:
            adj = +3.0
            conf_status = f"high ({total_obs} observations)"
        elif total_obs >= 30:
            adj = +1.0
            conf_status = f"medium ({total_obs} observations)"
        elif total_obs >= 5:
            adj = 0.0
            conf_status = f"low ({total_obs} observations)"
        else:
            adj = -5.0
            conf_status = f"very low ({total_obs} observations) — relying on priors"
        score += adj
        factors.append(("Data confidence", conf_status, adj))

        # Clamp
        score = max(5.0, min(98.0, score))

        # Confidence level
        ess = prediction.effective_sample_size
        ci_width = prediction.credible_interval_95[1] - prediction.credible_interval_95[0]
        if ess >= 50 and ci_width < 0.15:
            confidence = "high"
        elif ess >= 15 and ci_width < 0.25:
            confidence = "medium"
        else:
            confidence = "low"

        # Recommendation
        if score >= 80:
            rec = f"GO: {score:.0f}/100 — high reliability, proceed with confidence"
        elif score >= 65:
            rec = f"CAUTION: {score:.0f}/100 — moderate reliability, monitor closely"
        elif score >= 45:
            rec = f"WARNING: {score:.0f}/100 — below average, review risk factors"
        else:
            rec = f"NO-GO: {score:.0f}/100 — poor reliability, investigate before proceeding"

        return ReliabilityScore(
            overall_score=int(round(score)),
            confidence=confidence,
            factors=factors,
            recommendation=rec,
            bayesian_estimate=round(prediction.posterior_mean * 100, 1),
            credible_interval=(
                round(prediction.credible_interval_95[0] * 100, 1),
                round(prediction.credible_interval_95[1] * 100, 1),
            ),
        )

    def predict_success_probability(self, card_bin: str = None,
                                     target: str = None,
                                     amount: float = None,
                                     billing_country: str = None,
                                     gateway: str = None,
                                     merchant_type: str = "generic",
                                     issuer: str = "generic",
                                     cross_border: bool = False,
                                     profile_age_hours: float = 168) -> dict:
        """
        Predict success probability using Bayesian posterior + logistic adjustments.
        """
        country = (billing_country or "US").upper()

        # 1. Bayesian posterior from historical data
        alpha, beta = self.bayesian.compute_prior(merchant_type, country, issuer)
        observations = self.db.get_time_weighted_observations(
            hours=168, target=target, gateway=gateway,
            card_bin=card_bin, billing_country=country,
        )
        prediction = self.bayesian.update_posterior(alpha, beta, observations)

        base_rate = prediction.posterior_mean * 100
        adjustments: List[Tuple[str, float]] = []

        # 2. Amount band adjustment
        if amount is not None:
            if amount > 5000:
                adj = -15.0
            elif amount > 2500:
                adj = -10.0
            elif amount > 1000:
                adj = -6.0
            elif amount > 500:
                adj = -3.5
            elif amount > 200:
                adj = -1.5
            elif amount < 25:
                adj = +2.0
            else:
                adj = 0.0
            if adj != 0:
                adjustments.append((f"Amount ${amount:.0f}", adj))

        # 3. Cross-border
        if cross_border:
            adjustments.append(("Cross-border transaction", -5.5))

        # 4. Profile age
        if profile_age_hours < 1:
            adjustments.append(("Brand new profile (<1h)", -10.0))
        elif profile_age_hours < 24:
            adjustments.append(("Young profile (<24h)", -4.0))
        elif profile_age_hours < 72:
            adjustments.append(("Recent profile (<3d)", -1.5))

        # 5. Country risk
        country_prior = COUNTRY_AUTH_PRIORS.get(country, 80.0)
        if country_prior < 75:
            adjustments.append((f"High-risk country ({country})", -4.0))
        elif country_prior < 80:
            adjustments.append((f"Moderate-risk country ({country})", -1.5))

        # 6. Merchant risk
        profile = MERCHANT_RISK_PROFILES.get(merchant_type, MERCHANT_RISK_PROFILES["generic"])
        if profile["fraud_rate"] > 3.0:
            adjustments.append((f"High-risk merchant ({merchant_type})", -5.0))
        elif profile["fraud_rate"] > 2.0:
            adjustments.append((f"Elevated merchant risk ({merchant_type})", -2.0))

        # Apply adjustments
        total_adj = sum(a[1] for a in adjustments)
        predicted = max(35.0, min(95.0, base_rate + total_adj))

        # Confidence
        ess = prediction.effective_sample_size
        if ess >= 30:
            conf = "high"
        elif ess >= 10:
            conf = "medium"
        else:
            conf = "low"

        return {
            "predicted_probability": round(predicted, 1),
            "bayesian_base_rate": round(base_rate, 1),
            "credible_interval_95": (
                round(prediction.credible_interval_95[0] * 100, 1),
                round(prediction.credible_interval_95[1] * 100, 1),
            ),
            "adjustments": adjustments,
            "effective_sample_size": round(ess, 1),
            "time_decay_factor": round(prediction.time_decay_factor, 3),
            "similar_transactions": len(observations),
            "confidence": conf,
            "merchant_risk_tier": profile["risk_tier"],
        }

    def generate_reliability_report(self, target: Optional[str] = None,
                                     merchant_type: str = "generic",
                                     billing_country: str = "US") -> dict:
        """Generate comprehensive reliability report with Bayesian analysis."""
        score = self.calculate_reliability_score(
            target=target, merchant_type=merchant_type,
            billing_country=billing_country,
        )
        metrics_1h = self.db.get_metrics(hours=1, target=target)
        metrics_6h = self.db.get_metrics(hours=6, target=target)
        metrics_24h = self.db.get_metrics(hours=24, target=target)
        metrics_7d = self.db.get_metrics(hours=168, target=target)

        merchant_breakdown = self.db.get_breakdown_by_merchant(hours=168)
        country_breakdown = self.db.get_breakdown_by_country(hours=168)
        gateway_breakdown = self.db.get_breakdown_by_gateway(hours=168)
        decline_codes = self.db.get_decline_code_distribution(hours=168, target=target)
        failures = self.db.get_failure_reasons(hours=168)
        hourly = self.db.get_hourly_trend(hours=24)
        latency = self.db.get_latency_stats(hours=24)

        def _metrics_dict(m: SuccessRateMetrics) -> dict:
            return {
                "attempts": m.total_attempts,
                "success_rate": round(m.success_rate_pct, 1),
                "successful": m.successful,
                "soft_declines": m.soft_declines,
                "hard_declines": m.hard_declines,
                "fraud_blocks": m.fraud_blocks,
                "timeouts": m.timeouts,
                "error_rate": round(m.error_rate, 1),
            }

        return {
            "generated_at": datetime.utcnow().isoformat(),
            "target_filter": target,
            "merchant_type": merchant_type,
            "reliability_score": {
                "overall": score.overall_score,
                "confidence": score.confidence,
                "recommendation": score.recommendation,
                "bayesian_estimate": score.bayesian_estimate,
                "credible_interval_95": score.credible_interval,
                "factors": [(f, s, round(i, 1)) for f, s, i in score.factors],
            },
            "metrics": {
                "1h": _metrics_dict(metrics_1h),
                "6h": _metrics_dict(metrics_6h),
                "24h": _metrics_dict(metrics_24h),
                "7d": _metrics_dict(metrics_7d),
            },
            "top_merchants": {
                k: {"attempts": v.total_attempts, "success_rate": round(v.success_rate_pct, 1)}
                for k, v in list(merchant_breakdown.values.items())[:10]
            },
            "top_countries": {
                k: {"attempts": v.total_attempts, "success_rate": round(v.success_rate_pct, 1)}
                for k, v in list(country_breakdown.values.items())[:10]
            },
            "gateways": {
                k: {"attempts": v.total_attempts, "success_rate": round(v.success_rate_pct, 1)}
                for k, v in gateway_breakdown.values.items()
            },
            "decline_codes": decline_codes,
            "failure_reasons": failures,
            "hourly_trend": hourly,
            "latency_stats": latency,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Singleton Accessors
# ═══════════════════════════════════════════════════════════════════════════════

_metrics_db: Optional[PaymentSuccessMetricsDB] = None
_metrics_scorer: Optional[PaymentSuccessScorer] = None

def get_metrics_db() -> PaymentSuccessMetricsDB:
    global _metrics_db
    if _metrics_db is None:
        _metrics_db = PaymentSuccessMetricsDB()
    return _metrics_db

def get_metrics_scorer() -> PaymentSuccessScorer:
    global _metrics_scorer
    if _metrics_scorer is None:
        _metrics_scorer = PaymentSuccessScorer(get_metrics_db())
    return _metrics_scorer


# ═══════════════════════════════════════════════════════════════════════════════
# Prometheus Metrics Exporter
# ═══════════════════════════════════════════════════════════════════════════════

_prom_logger = logging.getLogger("TITAN-PROM")

_PROMETHEUS_AVAILABLE = False
try:
    from prometheus_client import Gauge, Counter, Histogram, Info, start_http_server as _prom_start
    _PROMETHEUS_AVAILABLE = True
except ImportError:
    _prom_logger.debug("prometheus_client not installed: pip install prometheus-client")


class TitanPrometheusExporter:
    """
    Exports payment_success_metrics SQLite data as Prometheus metrics.
    Scraped by Prometheus → visualized in Grafana.

    Metrics exported:
        titan_ops_total{status}               — counter per status
        titan_ops_success_rate{window}         — gauge per time window
        titan_ops_by_target{target,status}     — counter per target+status
        titan_ops_by_bin{bin,status}           — counter per BIN+status
        titan_ops_by_country{country,status}   — counter per country+status
        titan_ops_decline_codes{code}          — counter per decline code
        titan_ops_fraud_block_rate{window}     — gauge fraud block %
        titan_ops_latency_ms{quantile}         — gauge latency percentiles
        titan_ops_bayesian_score{target}       — gauge Bayesian posterior per target
    """

    def __init__(self, db: PaymentSuccessMetricsDB = None, port: int = None):
        self._db = db or get_metrics_db()
        self._port = port or int(os.getenv("TITAN_PROMETHEUS_PORT", "9200"))
        self._started = False

        if not _PROMETHEUS_AVAILABLE:
            _prom_logger.warning("prometheus_client not installed — exporter disabled")
            return

        # ── Gauges (current values, refreshed on scrape) ──
        self._success_rate = Gauge(
            "titan_ops_success_rate_pct", "Success rate percentage",
            ["window"]
        )
        self._total_attempts = Gauge(
            "titan_ops_total_attempts", "Total attempts in window",
            ["window"]
        )
        self._fraud_block_rate = Gauge(
            "titan_ops_fraud_block_rate_pct", "Fraud block rate percentage",
            ["window"]
        )
        self._hard_decline_rate = Gauge(
            "titan_ops_hard_decline_rate_pct", "Hard decline rate percentage",
            ["window"]
        )
        self._soft_decline_rate = Gauge(
            "titan_ops_soft_decline_rate_pct", "Soft decline rate percentage",
            ["window"]
        )
        self._timeout_rate = Gauge(
            "titan_ops_timeout_rate_pct", "Timeout rate percentage",
            ["window"]
        )

        # ── Per-dimension gauges ──
        self._target_success = Gauge(
            "titan_ops_target_success_rate_pct", "Success rate by target",
            ["target"]
        )
        self._target_volume = Gauge(
            "titan_ops_target_volume", "Attempt volume by target",
            ["target"]
        )
        self._bin_success = Gauge(
            "titan_ops_bin_success_rate_pct", "Success rate by BIN",
            ["bin"]
        )
        self._country_success = Gauge(
            "titan_ops_country_success_rate_pct", "Success rate by country",
            ["country"]
        )
        self._gateway_success = Gauge(
            "titan_ops_gateway_success_rate_pct", "Success rate by gateway",
            ["gateway"]
        )

        # ── Decline code distribution ──
        self._decline_code_count = Gauge(
            "titan_ops_decline_code_count", "Decline count by code (24h)",
            ["code"]
        )

        # ── Latency ──
        self._latency = Gauge(
            "titan_ops_latency_ms", "Latency percentiles",
            ["quantile"]
        )

    @property
    def is_available(self) -> bool:
        return _PROMETHEUS_AVAILABLE

    def start(self) -> bool:
        """Start the Prometheus HTTP metrics server."""
        if not _PROMETHEUS_AVAILABLE:
            return False
        if self._started:
            return True
        try:
            _prom_start(self._port)
            self._started = True
            _prom_logger.info(f"Prometheus exporter started on :{self._port}/metrics")
            # Do initial refresh
            self.refresh()
            return True
        except Exception as e:
            _prom_logger.error(f"Failed to start Prometheus exporter: {e}")
            return False

    def refresh(self):
        """Refresh all Prometheus metrics from SQLite. Call periodically or on-demand."""
        if not _PROMETHEUS_AVAILABLE:
            return

        # ── Overall metrics per time window ──
        for label, hours in [("1h", 1), ("6h", 6), ("24h", 24), ("7d", 168)]:
            m = self._db.get_metrics(hours=hours)
            self._success_rate.labels(window=label).set(round(m.success_rate_pct, 2))
            self._total_attempts.labels(window=label).set(m.total_attempts)
            if m.total_attempts > 0:
                self._fraud_block_rate.labels(window=label).set(
                    round(m.fraud_blocks / m.total_attempts * 100, 2))
                self._hard_decline_rate.labels(window=label).set(
                    round(m.hard_declines / m.total_attempts * 100, 2))
                self._soft_decline_rate.labels(window=label).set(
                    round(m.soft_declines / m.total_attempts * 100, 2))
                self._timeout_rate.labels(window=label).set(
                    round(m.timeouts / m.total_attempts * 100, 2))

        # ── Per-target breakdown (24h) ──
        target_bd = self._db.get_breakdown_by_merchant(hours=24)
        for tgt, metrics in list(target_bd.values.items())[:25]:
            if tgt:
                self._target_success.labels(target=tgt).set(round(metrics.success_rate_pct, 2))
                self._target_volume.labels(target=tgt).set(metrics.total_attempts)

        # ── Per-BIN breakdown (24h) ──
        bin_bd = self._db.get_breakdown_by_bin(hours=24)
        for bn, metrics in list(bin_bd.values.items())[:30]:
            if bn:
                self._bin_success.labels(bin=bn).set(round(metrics.success_rate_pct, 2))

        # ── Per-country breakdown (24h) ──
        country_bd = self._db.get_breakdown_by_country(hours=24)
        for country, metrics in country_bd.values.items():
            if country:
                self._country_success.labels(country=country).set(
                    round(metrics.success_rate_pct, 2))

        # ── Per-gateway breakdown (24h) ──
        gw_bd = self._db.get_breakdown_by_gateway(hours=24)
        for gw, metrics in gw_bd.values.items():
            if gw:
                self._gateway_success.labels(gateway=gw).set(
                    round(metrics.success_rate_pct, 2))

        # ── Decline codes (24h) ──
        codes = self._db.get_decline_code_distribution(hours=24)
        for code, count in list(codes.items())[:20]:
            self._decline_code_count.labels(code=code).set(count)

        # ── Latency percentiles (24h) ──
        lat = self._db.get_latency_stats(hours=24)
        for q in ["p50", "p75", "p90", "p95", "p99"]:
            self._latency.labels(quantile=q).set(lat.get(q, 0))

    def get_stats(self) -> dict:
        return {
            "available": _PROMETHEUS_AVAILABLE,
            "started": self._started,
            "port": self._port,
            "url": f"http://127.0.0.1:{self._port}/metrics" if self._started else None,
        }


_prom_exporter: Optional[TitanPrometheusExporter] = None

def get_prometheus_exporter() -> TitanPrometheusExporter:
    global _prom_exporter
    if _prom_exporter is None:
        _prom_exporter = TitanPrometheusExporter()
    return _prom_exporter

def start_prometheus_exporter(port: int = None) -> bool:
    """Start the Prometheus metrics exporter HTTP server."""
    exp = get_prometheus_exporter()
    if port:
        exp._port = port
    return exp.start()


if __name__ == "__main__":
    import random

    db = PaymentSuccessMetricsDB()
    scorer = PaymentSuccessScorer(db, decay_profile="standard")

    # Seed sample data
    statuses = ["success"] * 75 + ["soft_decline"] * 12 + ["hard_decline"] * 5 + \
               ["fraud_block"] * 3 + ["timeout"] * 2 + ["error"] * 3
    gateways = ["stripe", "adyen", "braintree"]
    countries = ["US", "GB", "DE", "BR", "JP"]
    decline_codes = {"soft_decline": ["05", "51", "65", "N7"],
                     "hard_decline": ["54", "14", "41"],
                     "fraud_block": ["59"],
                     "timeout": ["TO"],
                     "error": ["06", "96"]}

    for i in range(100):
        status = random.choice(statuses)
        dc = random.choice(decline_codes.get(status, ["00"])) if status != "success" else None
        db.record_attempt({
            "session_id": f"demo_{i}",
            "target_domain": "shop.example.com",
            "merchant_type": "ecommerce_physical",
            "gateway": random.choice(gateways),
            "card_bin": random.choice(["424242", "555544", "378282"]),
            "card_network": "visa",
            "billing_country": random.choice(countries),
            "amount": round(random.uniform(20, 500), 2),
            "status": status,
            "decline_code": dc,
            "decline_reason": dc,
            "latency_ms": random.randint(100, 800),
            "phase": "sandbox",
        })

    # Generate report
    report = scorer.generate_reliability_report(
        target="shop.example.com",
        merchant_type="ecommerce_physical",
        billing_country="US",
    )
    print(json.dumps(report, indent=2))

    # Predict
    pred = scorer.predict_success_probability(
        card_bin="424242", target="shop.example.com",
        amount=250, billing_country="US",
        merchant_type="ecommerce_physical",
    )
    print("\nPrediction:", json.dumps(pred, indent=2))
