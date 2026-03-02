"""
TITAN X — Decline Decoder
Thin wrapper providing decode_decline() for Cerberus Bridge API.
Extracts decline intelligence from transaction_monitor if available,
otherwise provides standalone decline code interpretation.
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("TITAN-DECLINE-DECODER")

# Standard decline code database
DECLINE_CODES = {
    "01": {"reason": "Refer to card issuer", "category": "soft", "action": "Retry with different amount or wait 24h"},
    "02": {"reason": "Refer to card issuer (special)", "category": "soft", "action": "Contact issuer or try different card"},
    "03": {"reason": "Invalid merchant", "category": "hard", "action": "Check merchant configuration"},
    "04": {"reason": "Pick up card", "category": "hard", "action": "Card is flagged — do not retry"},
    "05": {"reason": "Do not honor", "category": "soft", "action": "Most common generic decline — retry after cooldown"},
    "06": {"reason": "Error", "category": "soft", "action": "Retry transaction"},
    "07": {"reason": "Pick up card (special)", "category": "hard", "action": "Card flagged for fraud — burn card"},
    "12": {"reason": "Invalid transaction", "category": "hard", "action": "Transaction type not supported"},
    "13": {"reason": "Invalid amount", "category": "soft", "action": "Try different amount"},
    "14": {"reason": "Invalid card number", "category": "hard", "action": "Check card number — possible typo"},
    "15": {"reason": "No such issuer", "category": "hard", "action": "BIN not recognized — check card data"},
    "19": {"reason": "Re-enter transaction", "category": "soft", "action": "Retry immediately"},
    "41": {"reason": "Lost card", "category": "hard", "action": "Card reported lost — do not retry"},
    "43": {"reason": "Stolen card", "category": "hard", "action": "Card reported stolen — burn immediately"},
    "51": {"reason": "Insufficient funds", "category": "soft", "action": "Try smaller amount or different card"},
    "54": {"reason": "Expired card", "category": "hard", "action": "Card expired — need new card data"},
    "55": {"reason": "Incorrect PIN", "category": "soft", "action": "PIN required — use correct PIN"},
    "57": {"reason": "Transaction not permitted", "category": "hard", "action": "Card restricted for this merchant type"},
    "59": {"reason": "Suspected fraud", "category": "hard", "action": "Issuer flagged as fraud — burn card + proxy"},
    "61": {"reason": "Exceeds withdrawal limit", "category": "soft", "action": "Try smaller amount"},
    "62": {"reason": "Restricted card", "category": "hard", "action": "Card restricted by issuer"},
    "63": {"reason": "Security violation", "category": "hard", "action": "Issuer security flag — burn card"},
    "65": {"reason": "Activity limit exceeded", "category": "soft", "action": "Velocity limit hit — wait 24-48h"},
    "70": {"reason": "Contact card issuer", "category": "soft", "action": "Generic — retry after cooldown"},
    "75": {"reason": "PIN tries exceeded", "category": "hard", "action": "Too many PIN attempts — card locked"},
    "78": {"reason": "Blocked first use", "category": "soft", "action": "Card not yet activated"},
    "82": {"reason": "CVV incorrect", "category": "soft", "action": "Check CVV — possible data error"},
    "85": {"reason": "No reason to decline", "category": "soft", "action": "Issuer approved but PSP declined — try different PSP"},
    "91": {"reason": "Issuer unavailable", "category": "soft", "action": "Issuer system down — retry in 1h"},
    "96": {"reason": "System malfunction", "category": "soft", "action": "PSP error — retry immediately"},
    "N7": {"reason": "CVV2 mismatch", "category": "soft", "action": "CVV wrong — verify card data"},
    "R1": {"reason": "Stop payment order", "category": "hard", "action": "Cardholder requested stop — do not retry"},
}

# PSP-specific decline mappings
PSP_DECLINES = {
    "stripe": {
        "card_declined": "05", "expired_card": "54", "incorrect_cvc": "N7",
        "insufficient_funds": "51", "lost_card": "41", "stolen_card": "43",
        "fraudulent": "59", "processing_error": "96",
    },
    "adyen": {
        "Refused": "05", "CVC Declined": "N7", "Expired Card": "54",
        "Not enough balance": "51", "Acquirer Fraud": "59",
    },
    "braintree": {
        "2000": "05", "2001": "51", "2002": "13", "2003": "41",
        "2004": "54", "2010": "N7", "2046": "05",
    },
}


def decode_decline(code: str, psp: str = "generic", raw_message: str = "") -> Dict[str, Any]:
    """
    Decode a transaction decline code into actionable intelligence.

    Args:
        code: Decline code (ISO 8583 or PSP-specific)
        psp: Payment processor name (stripe, adyen, braintree, generic)
        raw_message: Raw decline message from PSP

    Returns:
        Dict with reason, category, action, and intelligence
    """
    # Try PSP-specific mapping first
    iso_code = code
    if psp.lower() in PSP_DECLINES:
        psp_map = PSP_DECLINES[psp.lower()]
        if code in psp_map:
            iso_code = psp_map[code]

    # Look up in decline database
    info = DECLINE_CODES.get(iso_code, {
        "reason": f"Unknown decline code: {code}",
        "category": "unknown",
        "action": "Review manually — unrecognized code",
    })

    result = {
        "code": code,
        "iso_code": iso_code,
        "psp": psp,
        "reason": info["reason"],
        "category": info["category"],
        "action": info["action"],
        "raw_message": raw_message,
        "retryable": info["category"] == "soft",
        "burn_card": info["category"] == "hard" and iso_code in ("04", "07", "41", "43", "59", "63"),
        "burn_proxy": iso_code in ("59", "63"),
    }

    logger.info(f"Decline decoded: {code} ({psp}) -> {info['reason']} [{info['category']}]")
    return result
