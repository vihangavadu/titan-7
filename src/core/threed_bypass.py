"""
TITAN X — 3DS Bypass Plan Generator
Thin wrapper providing get_3ds_bypass_plan() for Cerberus Bridge API.
Delegates to three_ds_strategy module for actual strategy computation.
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("TITAN-3DS-BYPASS")

try:
    from three_ds_strategy import ThreeDSStrategy
    _STRATEGY_OK = True
except ImportError:
    _STRATEGY_OK = False


def get_3ds_bypass_plan(bin6: str, merchant: str = "", amount: float = 0.0,
                        country: str = "US", card_type: str = "visa") -> Dict[str, Any]:
    """
    Generate a 3DS bypass/minimization plan for a given transaction.

    Args:
        bin6: First 6 digits of card
        merchant: Target merchant domain
        amount: Transaction amount
        country: Card issuing country
        card_type: visa/mastercard/amex

    Returns:
        Dict with strategy, risk level, and recommended approach
    """
    plan = {
        "bin6": bin6,
        "merchant": merchant,
        "amount": amount,
        "country": country,
        "card_type": card_type,
        "strategy": "unknown",
        "risk_level": "medium",
        "recommendations": [],
        "3ds_likely": True,
    }

    if _STRATEGY_OK:
        try:
            strategy = ThreeDSStrategy()
            result = strategy.analyze(bin6=bin6, merchant=merchant,
                                      amount=amount, country=country)
            if result:
                plan.update({
                    "strategy": getattr(result, "strategy", "standard"),
                    "risk_level": getattr(result, "risk_level", "medium"),
                    "3ds_likely": getattr(result, "three_ds_likely", True),
                    "recommendations": getattr(result, "recommendations", []),
                })
                return plan
        except Exception as e:
            logger.warning(f"ThreeDSStrategy.analyze failed: {e}")

    # Fallback: rule-based bypass plan
    # Amount-based 3DS likelihood (SCA/TRA thresholds)
    if amount < 30:
        plan["3ds_likely"] = False
        plan["strategy"] = "low_value_exemption"
        plan["risk_level"] = "low"
        plan["recommendations"] = [
            f"Amount ${amount:.2f} below EUR 30 TRA threshold",
            "Most issuers skip 3DS for low-value transactions",
            "Proceed normally — 3DS unlikely",
        ]
    elif amount < 100:
        plan["strategy"] = "tra_exemption"
        plan["risk_level"] = "medium"
        plan["3ds_likely"] = True
        plan["recommendations"] = [
            f"Amount ${amount:.2f} in TRA exemption range",
            "Some merchants request TRA exemption from acquirer",
            "If 3DS triggers: wait 12s before entering code (natural timing)",
            "Have phone ready for OTP",
        ]
    else:
        plan["strategy"] = "full_3ds_expected"
        plan["risk_level"] = "high"
        plan["3ds_likely"] = True
        plan["recommendations"] = [
            f"Amount ${amount:.2f} above SCA threshold — 3DS very likely",
            "Prepare for full 3DS challenge",
            "Wait 10-15s after redirect (simulates phone unlock + SMS read)",
            "Enter OTP character by character with human timing",
            "Consider splitting into smaller amounts if possible",
        ]

    # Card-type specific advice
    if card_type.lower() == "amex":
        plan["recommendations"].append("AMEX SafeKey often uses email OTP — check inbox")
    elif card_type.lower() == "mastercard":
        plan["recommendations"].append("Mastercard Identity Check may use biometric — prepare device")

    logger.info(f"3DS bypass plan: {bin6} @ {merchant} ${amount} -> {plan['strategy']}")
    return plan
