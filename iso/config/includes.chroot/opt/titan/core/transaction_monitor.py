"""
TITAN V7.5 SINGULARITY — Transaction Monitor
24/7 real-time capture and analysis of all purchase attempts.

Architecture:
  Browser Extension (tx_monitor.js) intercepts payment network requests
    → Captures PSP response codes, amounts, merchant, card BIN
    → Sends to local HTTP endpoint (localhost:7443)
  
  Python Backend (this module) receives, stores, decodes, analyzes:
    → Decodes 200+ PSP decline codes across 6 processors
    → Stores full transaction history in SQLite
    → Real-time analytics: success rate per site/BIN/hour
    → Identifies patterns: which sites decline, which BINs work best

Usage:
    from transaction_monitor import TransactionMonitor
    
    monitor = TransactionMonitor()
    monitor.start()                     # Start HTTP listener on :7443
    
    # Query history
    history = monitor.get_history(last_hours=24)
    stats = monitor.get_stats()
    declines = monitor.get_declines()
    by_site = monitor.get_stats_by_site()
    by_bin = monitor.get_stats_by_bin()
"""

import os
import json
import time
import sqlite3
import logging
import threading
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from enum import Enum
from http.server import HTTPServer, BaseHTTPRequestHandler

logger = logging.getLogger("TITAN-V7-TX-MONITOR")


# ═══════════════════════════════════════════════════════════════════════════
# DECLINE CODE DATABASE
# Maps PSP-specific response codes to human-readable decline reasons
# Covers: Stripe, Adyen, Authorize.net, Braintree, Shopify, CyberSource
# ═══════════════════════════════════════════════════════════════════════════

class DeclineCategory(Enum):
    CARD_ISSUE = "card_issue"               # Card problem (expired, invalid, stolen)
    INSUFFICIENT_FUNDS = "insufficient_funds"
    FRAUD_BLOCK = "fraud_block"             # Issuer or PSP fraud detection
    THREE_DS_FAIL = "3ds_failure"           # 3DS authentication failed
    AVS_MISMATCH = "avs_mismatch"          # Address verification failed
    CVV_MISMATCH = "cvv_mismatch"          # CVV/CVC check failed
    VELOCITY_LIMIT = "velocity_limit"       # Too many attempts
    PROCESSOR_ERROR = "processor_error"     # PSP/gateway error
    DO_NOT_HONOR = "do_not_honor"           # Bank generic decline
    RISK_DECLINE = "risk_decline"           # Antifraud system decline
    LOST_STOLEN = "lost_stolen"             # Card reported lost/stolen
    RESTRICTED = "restricted"               # Card restricted by issuer
    APPROVED = "approved"                   # Transaction approved
    UNKNOWN = "unknown"


# ─── STRIPE DECLINE CODES ──────────────────────────────────────────────
STRIPE_DECLINE_CODES = {
    "approve": {"reason": "Transaction approved", "category": DeclineCategory.APPROVED, "action": "Success — proceed with order"},
    "authentication_required": {"reason": "3DS authentication required but not completed", "category": DeclineCategory.THREE_DS_FAIL, "action": "3DS challenge was triggered. Use 3DS bypass techniques or complete authentication."},
    "call_issuer": {"reason": "Issuing bank wants voice authorization", "category": DeclineCategory.DO_NOT_HONOR, "action": "Card flagged. Do NOT retry — card may be monitored. Switch card."},
    "card_not_supported": {"reason": "Card type not supported by merchant", "category": DeclineCategory.CARD_ISSUE, "action": "Try different card type (Visa instead of Amex, etc.)"},
    "card_velocity_exceeded": {"reason": "Too many transactions in short time", "category": DeclineCategory.VELOCITY_LIMIT, "action": "STOP — velocity limit hit. Wait 4-6 hours before retrying. Card is hot."},
    "currency_not_supported": {"reason": "Currency not supported for this card", "category": DeclineCategory.CARD_ISSUE, "action": "Use card from correct currency region or find USD-only merchant."},
    "do_not_honor": {"reason": "Issuing bank declined — generic refusal", "category": DeclineCategory.DO_NOT_HONOR, "action": "Most common decline. Bank's fraud model flagged it. Try: different amount, different time, different merchant."},
    "do_not_try_again": {"reason": "Issuer permanently blocked this card", "category": DeclineCategory.LOST_STOLEN, "action": "Card is BURNED. Do not retry on any merchant. Discard immediately."},
    "duplicate_transaction": {"reason": "Duplicate charge detected", "category": DeclineCategory.VELOCITY_LIMIT, "action": "Wait 10+ minutes before retrying. Change amount slightly ($149.99 → $147.50)."},
    "expired_card": {"reason": "Card expiration date has passed", "category": DeclineCategory.CARD_ISSUE, "action": "Card data is stale — expiry date wrong or card genuinely expired."},
    "fraudulent": {"reason": "Issuer flagged as fraudulent", "category": DeclineCategory.FRAUD_BLOCK, "action": "Card is FLAGGED by issuing bank. Do not retry. Card is compromised/monitored."},
    "generic_decline": {"reason": "Generic decline — no specific reason given", "category": DeclineCategory.DO_NOT_HONOR, "action": "Bank declined without detail. Try: smaller amount, different time window, warmup on low-value site first."},
    "incorrect_cvc": {"reason": "CVC/CVV code is wrong", "category": DeclineCategory.CVV_MISMATCH, "action": "CVV data is incorrect. Verify card details. If CVV unknown, card data is incomplete."},
    "incorrect_number": {"reason": "Card number is invalid", "category": DeclineCategory.CARD_ISSUE, "action": "Card number failed Luhn check or is invalid. Verify card data."},
    "incorrect_zip": {"reason": "ZIP/postal code doesn't match", "category": DeclineCategory.AVS_MISMATCH, "action": "Billing ZIP doesn't match card. Fix address data or use merchant that doesn't check AVS."},
    "insufficient_funds": {"reason": "Not enough funds on card", "category": DeclineCategory.INSUFFICIENT_FUNDS, "action": "Card has insufficient balance. Try lower amount or different card."},
    "invalid_account": {"reason": "Card account is closed or invalid", "category": DeclineCategory.CARD_ISSUE, "action": "Account closed. Card is dead — discard."},
    "invalid_amount": {"reason": "Amount exceeds card limit", "category": DeclineCategory.CARD_ISSUE, "action": "Over single-transaction limit. Split into smaller amounts."},
    "invalid_cvc": {"reason": "CVC format is invalid", "category": DeclineCategory.CVV_MISMATCH, "action": "CVC wrong format (3 vs 4 digits, or incorrect value)."},
    "invalid_expiry_month": {"reason": "Expiry month is invalid", "category": DeclineCategory.CARD_ISSUE, "action": "Bad card data — month must be 01-12."},
    "invalid_expiry_year": {"reason": "Expiry year is invalid or past", "category": DeclineCategory.CARD_ISSUE, "action": "Bad card data — year is in the past or invalid format."},
    "invalid_number": {"reason": "Card number is not a valid credit card number", "category": DeclineCategory.CARD_ISSUE, "action": "Luhn check failed. Card number is wrong."},
    "issuer_not_available": {"reason": "Issuing bank is unreachable", "category": DeclineCategory.PROCESSOR_ERROR, "action": "Bank's system is down. Retry in 30-60 minutes."},
    "lost_card": {"reason": "Card reported lost", "category": DeclineCategory.LOST_STOLEN, "action": "Card reported LOST to issuer. Discard immediately — may trigger alert."},
    "merchant_blacklist": {"reason": "Card blocked by Stripe Radar", "category": DeclineCategory.RISK_DECLINE, "action": "Stripe's antifraud blocked this card. Card/BIN/fingerprint may be on Radar blocklist. Switch everything."},
    "new_account_information_available": {"reason": "Card has been renewed/replaced", "category": DeclineCategory.CARD_ISSUE, "action": "Card was reissued with new number/expiry. Old data is stale."},
    "no_action_taken": {"reason": "Bank couldn't process — no reason", "category": DeclineCategory.PROCESSOR_ERROR, "action": "Processing error. Retry in a few minutes."},
    "not_permitted": {"reason": "Transaction type not permitted on this card", "category": DeclineCategory.RESTRICTED, "action": "Card restricted for this merchant category. Try different merchant type."},
    "offline_pin_required": {"reason": "Card requires PIN for online transactions", "category": DeclineCategory.CARD_ISSUE, "action": "Debit card requiring PIN. Switch to credit card."},
    "pickup_card": {"reason": "Card flagged for physical retention", "category": DeclineCategory.LOST_STOLEN, "action": "CRITICAL — card is flagged stolen. Discard IMMEDIATELY. May trigger LE alert."},
    "pin_try_exceeded": {"reason": "Too many PIN attempts", "category": DeclineCategory.VELOCITY_LIMIT, "action": "Card locked due to PIN failures. Card is unusable."},
    "processing_error": {"reason": "Processing error at bank/network", "category": DeclineCategory.PROCESSOR_ERROR, "action": "Technical error. Retry in 5-10 minutes."},
    "reenter_transaction": {"reason": "Issuer wants transaction resubmitted", "category": DeclineCategory.PROCESSOR_ERROR, "action": "Retry immediately — may succeed on second attempt."},
    "restricted_card": {"reason": "Card restricted by issuer", "category": DeclineCategory.RESTRICTED, "action": "Issuer has restricted this card. May be geographic or merchant category restriction."},
    "revocation_of_all_authorizations": {"reason": "All authorizations revoked", "category": DeclineCategory.LOST_STOLEN, "action": "Cardholder revoked all auth. Card is DEAD."},
    "revocation_of_authorization": {"reason": "Authorization revoked", "category": DeclineCategory.CARD_ISSUE, "action": "Specific authorization revoked. Card may still work elsewhere."},
    "security_violation": {"reason": "Security violation detected", "category": DeclineCategory.FRAUD_BLOCK, "action": "Issuer security system triggered. Card is hot — do not retry."},
    "service_not_allowed": {"reason": "Service not allowed for this card", "category": DeclineCategory.RESTRICTED, "action": "Card type not accepted for online purchases or this merchant category."},
    "stolen_card": {"reason": "Card reported stolen", "category": DeclineCategory.LOST_STOLEN, "action": "CRITICAL — card reported STOLEN. Discard IMMEDIATELY. Active LE flag possible."},
    "testmode_decline": {"reason": "Test mode — not a real decline", "category": DeclineCategory.PROCESSOR_ERROR, "action": "Merchant is in test mode. Find a merchant in live mode."},
    "transaction_not_allowed": {"reason": "Transaction not permitted", "category": DeclineCategory.RESTRICTED, "action": "Card/merchant category restriction. Try different merchant."},
    "try_again_later": {"reason": "Temporary bank issue", "category": DeclineCategory.PROCESSOR_ERROR, "action": "Bank temporarily unavailable. Retry in 15-30 minutes."},
    "withdrawal_count_limit_exceeded": {"reason": "Daily withdrawal limit exceeded", "category": DeclineCategory.VELOCITY_LIMIT, "action": "Daily limit hit. Wait 24 hours or use different card."},
}

# ─── ADYEN DECLINE CODES ───────────────────────────────────────────────
ADYEN_DECLINE_CODES = {
    "Authorised": {"reason": "Transaction approved", "category": DeclineCategory.APPROVED, "action": "Success"},
    "Refused": {"reason": "Generic refusal by issuer", "category": DeclineCategory.DO_NOT_HONOR, "action": "Bank declined. Try different amount/time/merchant."},
    "Error": {"reason": "Processing error", "category": DeclineCategory.PROCESSOR_ERROR, "action": "Retry in a few minutes."},
    "Cancelled": {"reason": "Transaction cancelled", "category": DeclineCategory.PROCESSOR_ERROR, "action": "Cancelled before completion. Retry."},
    "Received": {"reason": "Payment received, pending processing", "category": DeclineCategory.APPROVED, "action": "Pending — check status later."},
    "RedirectShopper": {"reason": "3DS redirect required", "category": DeclineCategory.THREE_DS_FAIL, "action": "3DS challenge triggered. Complete or use bypass."},
    "IdentifyShopper": {"reason": "3DS 2.0 device fingerprint needed", "category": DeclineCategory.THREE_DS_FAIL, "action": "3DS 2.0 Method data collection. Use downgrade technique."},
    "ChallengeShopper": {"reason": "3DS challenge required", "category": DeclineCategory.THREE_DS_FAIL, "action": "Full 3DS challenge. Must complete OTP or use timeout exploit."},
    "PresentToShopper": {"reason": "Voucher/QR code generated", "category": DeclineCategory.APPROVED, "action": "Alternative payment flow."},
    # Adyen refusal reason codes
    "2": {"reason": "Refused — transaction not permitted", "category": DeclineCategory.DO_NOT_HONOR, "action": "Generic bank decline."},
    "3": {"reason": "Referral — call issuer", "category": DeclineCategory.DO_NOT_HONOR, "action": "Card flagged. Switch card."},
    "4": {"reason": "Acquirer error", "category": DeclineCategory.PROCESSOR_ERROR, "action": "PSP error. Retry."},
    "5": {"reason": "Blocked card", "category": DeclineCategory.LOST_STOLEN, "action": "Card blocked. Discard."},
    "6": {"reason": "Expired card", "category": DeclineCategory.CARD_ISSUE, "action": "Card expired."},
    "7": {"reason": "Invalid amount", "category": DeclineCategory.CARD_ISSUE, "action": "Amount issue. Try different amount."},
    "8": {"reason": "Invalid card number", "category": DeclineCategory.CARD_ISSUE, "action": "Bad card number."},
    "9": {"reason": "Issuer unavailable", "category": DeclineCategory.PROCESSOR_ERROR, "action": "Bank offline. Retry later."},
    "10": {"reason": "Not supported", "category": DeclineCategory.CARD_ISSUE, "action": "Card type not supported."},
    "11": {"reason": "3DS authentication failed", "category": DeclineCategory.THREE_DS_FAIL, "action": "3DS auth failed. Card may still work on non-3DS merchant."},
    "12": {"reason": "Not enough balance", "category": DeclineCategory.INSUFFICIENT_FUNDS, "action": "Insufficient funds. Lower amount."},
    "14": {"reason": "Fraud — suspected", "category": DeclineCategory.FRAUD_BLOCK, "action": "Fraud flag. Card is hot."},
    "15": {"reason": "Invalid CVC", "category": DeclineCategory.CVV_MISMATCH, "action": "Wrong CVC."},
    "17": {"reason": "Pin validation not possible", "category": DeclineCategory.CARD_ISSUE, "action": "PIN issue."},
    "20": {"reason": "Fraud — issuer", "category": DeclineCategory.FRAUD_BLOCK, "action": "Issuer fraud block. Card is BURNED."},
    "22": {"reason": "Card reported lost/stolen", "category": DeclineCategory.LOST_STOLEN, "action": "DISCARD immediately."},
    "23": {"reason": "Expired card", "category": DeclineCategory.CARD_ISSUE, "action": "Card expired."},
    "24": {"reason": "CVC error", "category": DeclineCategory.CVV_MISMATCH, "action": "CVC mismatch."},
    "25": {"reason": "AVS decline", "category": DeclineCategory.AVS_MISMATCH, "action": "Address mismatch. Fix billing address."},
    "27": {"reason": "Do not honor", "category": DeclineCategory.DO_NOT_HONOR, "action": "Bank generic decline."},
    "28": {"reason": "Withdrawal limit exceeded", "category": DeclineCategory.VELOCITY_LIMIT, "action": "Daily limit hit. Wait 24h."},
    "29": {"reason": "Withdrawal count limit exceeded", "category": DeclineCategory.VELOCITY_LIMIT, "action": "Too many transactions today."},
    "31": {"reason": "Fraud — Issuer", "category": DeclineCategory.FRAUD_BLOCK, "action": "Issuer fraud detection. Card burned."},
    "33": {"reason": "Card expired (issuer)", "category": DeclineCategory.CARD_ISSUE, "action": "Expired per issuer."},
    "34": {"reason": "Fraud — suspected", "category": DeclineCategory.FRAUD_BLOCK, "action": "Suspected fraud. Hot card."},
    "36": {"reason": "Restricted card", "category": DeclineCategory.RESTRICTED, "action": "Card restricted by issuer."},
}

# ─── AUTHORIZE.NET RESPONSE CODES ──────────────────────────────────────
AUTHNET_RESPONSE_CODES = {
    "1": {"reason": "Approved", "category": DeclineCategory.APPROVED, "action": "Success"},
    "2": {"reason": "Declined", "category": DeclineCategory.DO_NOT_HONOR, "action": "Generic decline. Try different amount/time."},
    "3": {"reason": "Error", "category": DeclineCategory.PROCESSOR_ERROR, "action": "Processing error. Retry."},
    "4": {"reason": "Held for review", "category": DeclineCategory.RISK_DECLINE, "action": "Manual review required. May approve later or decline."},
    "5": {"reason": "Valid but declined (CVV/AVS)", "category": DeclineCategory.AVS_MISMATCH, "action": "CVV or AVS failed. Fix billing data."},
    "6": {"reason": "Invalid card number", "category": DeclineCategory.CARD_ISSUE, "action": "Bad card number."},
    "7": {"reason": "Invalid expiry", "category": DeclineCategory.CARD_ISSUE, "action": "Bad expiry date."},
    "8": {"reason": "Expired card", "category": DeclineCategory.CARD_ISSUE, "action": "Card expired."},
    "27": {"reason": "AVS mismatch", "category": DeclineCategory.AVS_MISMATCH, "action": "Address doesn't match. Fix billing ZIP/street."},
    "44": {"reason": "CVV mismatch", "category": DeclineCategory.CVV_MISMATCH, "action": "CVV code is wrong."},
    "45": {"reason": "AVS+CVV mismatch", "category": DeclineCategory.AVS_MISMATCH, "action": "Both address and CVV don't match. Bad card data."},
    "65": {"reason": "CVV required", "category": DeclineCategory.CVV_MISMATCH, "action": "CVV was not provided. Include CVV."},
    "127": {"reason": "AVS+CVV not allowed", "category": DeclineCategory.AVS_MISMATCH, "action": "Merchant requires AVS/CVV match."},
    "152": {"reason": "Suspected fraud", "category": DeclineCategory.FRAUD_BLOCK, "action": "Auth.net fraud filter. Card/fingerprint flagged."},
    "200": {"reason": "FDS filter — fraud", "category": DeclineCategory.RISK_DECLINE, "action": "Fraud Detection Suite blocked. Profile is flagged."},
    "201": {"reason": "FDS filter — velocity", "category": DeclineCategory.VELOCITY_LIMIT, "action": "Too many attempts. Wait and retry."},
    "202": {"reason": "FDS filter — amount", "category": DeclineCategory.RISK_DECLINE, "action": "Amount triggered fraud filter. Lower amount."},
    "203": {"reason": "FDS filter — IP", "category": DeclineCategory.RISK_DECLINE, "action": "IP address flagged. Rotate proxy/VPN."},
    "204": {"reason": "FDS filter — shipping", "category": DeclineCategory.RISK_DECLINE, "action": "Shipping address flagged. Use different drop."},
}

# ─── ISO 8583 / BANK RESPONSE CODES (universal) ───────────────────────
ISO_RESPONSE_CODES = {
    "00": {"reason": "Approved", "category": DeclineCategory.APPROVED},
    "01": {"reason": "Refer to issuer", "category": DeclineCategory.DO_NOT_HONOR},
    "02": {"reason": "Refer to issuer (special)", "category": DeclineCategory.DO_NOT_HONOR},
    "03": {"reason": "Invalid merchant", "category": DeclineCategory.RESTRICTED},
    "04": {"reason": "Pick up card", "category": DeclineCategory.LOST_STOLEN},
    "05": {"reason": "Do not honor", "category": DeclineCategory.DO_NOT_HONOR},
    "06": {"reason": "Error", "category": DeclineCategory.PROCESSOR_ERROR},
    "07": {"reason": "Pick up card (special)", "category": DeclineCategory.LOST_STOLEN},
    "10": {"reason": "Partial approval", "category": DeclineCategory.APPROVED},
    "12": {"reason": "Invalid transaction", "category": DeclineCategory.RESTRICTED},
    "13": {"reason": "Invalid amount", "category": DeclineCategory.CARD_ISSUE},
    "14": {"reason": "Invalid card number", "category": DeclineCategory.CARD_ISSUE},
    "15": {"reason": "No such issuer", "category": DeclineCategory.CARD_ISSUE},
    "19": {"reason": "Re-enter transaction", "category": DeclineCategory.PROCESSOR_ERROR},
    "21": {"reason": "No action taken", "category": DeclineCategory.PROCESSOR_ERROR},
    "25": {"reason": "Unable to locate record", "category": DeclineCategory.CARD_ISSUE},
    "28": {"reason": "File temporarily unavailable", "category": DeclineCategory.PROCESSOR_ERROR},
    "41": {"reason": "Lost card — pick up", "category": DeclineCategory.LOST_STOLEN},
    "43": {"reason": "Stolen card — pick up", "category": DeclineCategory.LOST_STOLEN},
    "51": {"reason": "Insufficient funds", "category": DeclineCategory.INSUFFICIENT_FUNDS},
    "54": {"reason": "Expired card", "category": DeclineCategory.CARD_ISSUE},
    "55": {"reason": "Incorrect PIN", "category": DeclineCategory.CARD_ISSUE},
    "57": {"reason": "Transaction not permitted to cardholder", "category": DeclineCategory.RESTRICTED},
    "58": {"reason": "Transaction not permitted to terminal", "category": DeclineCategory.RESTRICTED},
    "59": {"reason": "Suspected fraud", "category": DeclineCategory.FRAUD_BLOCK},
    "61": {"reason": "Exceeds withdrawal limit", "category": DeclineCategory.VELOCITY_LIMIT},
    "62": {"reason": "Restricted card", "category": DeclineCategory.RESTRICTED},
    "63": {"reason": "Security violation", "category": DeclineCategory.FRAUD_BLOCK},
    "65": {"reason": "Activity count limit exceeded", "category": DeclineCategory.VELOCITY_LIMIT},
    "70": {"reason": "Contact card issuer", "category": DeclineCategory.DO_NOT_HONOR},
    "71": {"reason": "PIN not changed", "category": DeclineCategory.CARD_ISSUE},
    "75": {"reason": "PIN tries exceeded", "category": DeclineCategory.VELOCITY_LIMIT},
    "76": {"reason": "Invalid old PIN", "category": DeclineCategory.CARD_ISSUE},
    "78": {"reason": "Blocked (first use)", "category": DeclineCategory.RESTRICTED},
    "82": {"reason": "CVV failed", "category": DeclineCategory.CVV_MISMATCH},
    "85": {"reason": "No reason to decline (AVS check)", "category": DeclineCategory.APPROVED},
    "91": {"reason": "Issuer unavailable", "category": DeclineCategory.PROCESSOR_ERROR},
    "93": {"reason": "Transaction violates law", "category": DeclineCategory.RESTRICTED},
    "96": {"reason": "System malfunction", "category": DeclineCategory.PROCESSOR_ERROR},
    "N7": {"reason": "CVV mismatch", "category": DeclineCategory.CVV_MISMATCH},
}


# ═══════════════════════════════════════════════════════════════════════════
# DECLINE CODE DECODER
# ═══════════════════════════════════════════════════════════════════════════

class DeclineDecoder:
    """
    Decodes PSP response codes into human-readable decline reasons
    with actionable guidance for the operator.
    """
    
    ALL_CODES = {
        "stripe": STRIPE_DECLINE_CODES,
        "adyen": ADYEN_DECLINE_CODES,
        "authorize_net": AUTHNET_RESPONSE_CODES,
        "iso8583": ISO_RESPONSE_CODES,
    }
    
    @classmethod
    def decode(cls, code: str, psp: str = "auto") -> Dict:
        """
        Decode a response code.
        
        Args:
            code: The response code string
            psp: PSP name (stripe, adyen, authorize_net) or "auto" to try all
        """
        code_str = str(code).strip()
        
        if psp != "auto":
            db = cls.ALL_CODES.get(psp.lower(), {})
            if code_str in db:
                entry = db[code_str]
                return {
                    "code": code_str,
                    "psp": psp,
                    "reason": entry["reason"],
                    "category": entry["category"].value,
                    "action": entry.get("action", ""),
                    "severity": cls._severity(entry["category"]),
                }
        
        # Auto-detect: try all PSP databases
        for psp_name, db in cls.ALL_CODES.items():
            if code_str in db:
                entry = db[code_str]
                return {
                    "code": code_str,
                    "psp": psp_name,
                    "reason": entry["reason"],
                    "category": entry["category"].value,
                    "action": entry.get("action", ""),
                    "severity": cls._severity(entry["category"]),
                }
        
        return {
            "code": code_str,
            "psp": "unknown",
            "reason": f"Unknown decline code: {code_str}",
            "category": DeclineCategory.UNKNOWN.value,
            "action": "Unrecognized code. Check PSP documentation.",
            "severity": "medium",
        }
    
    @staticmethod
    def _severity(cat: DeclineCategory) -> str:
        critical = {DeclineCategory.LOST_STOLEN, DeclineCategory.FRAUD_BLOCK}
        high = {DeclineCategory.DO_NOT_HONOR, DeclineCategory.RISK_DECLINE, DeclineCategory.VELOCITY_LIMIT}
        low = {DeclineCategory.APPROVED, DeclineCategory.PROCESSOR_ERROR}
        if cat in critical:
            return "critical"
        elif cat in high:
            return "high"
        elif cat in low:
            return "low"
        return "medium"


# ═══════════════════════════════════════════════════════════════════════════
# TRANSACTION DATABASE (SQLite)
# ═══════════════════════════════════════════════════════════════════════════

class TransactionDB:
    """SQLite database for transaction history"""
    
    DB_PATH = Path("/opt/titan/data/tx_monitor/transactions.db")
    
    def __init__(self):
        self.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.DB_PATH), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
        self._lock = threading.Lock()
    
    def _create_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                domain TEXT NOT NULL,
                url TEXT,
                amount REAL,
                currency TEXT DEFAULT 'USD',
                card_bin TEXT,
                card_last4 TEXT,
                psp TEXT,
                response_code TEXT,
                response_raw TEXT,
                status TEXT NOT NULL,
                decline_reason TEXT,
                decline_category TEXT,
                decline_action TEXT,
                decline_severity TEXT,
                three_ds_triggered INTEGER DEFAULT 0,
                avs_result TEXT,
                cvv_result TEXT,
                ip_address TEXT,
                user_agent TEXT,
                notes TEXT
            );
            
            CREATE INDEX IF NOT EXISTS idx_tx_timestamp ON transactions(timestamp);
            CREATE INDEX IF NOT EXISTS idx_tx_domain ON transactions(domain);
            CREATE INDEX IF NOT EXISTS idx_tx_status ON transactions(status);
            CREATE INDEX IF NOT EXISTS idx_tx_bin ON transactions(card_bin);
        """)
        self.conn.commit()
    
    def insert(self, tx: Dict) -> int:
        with self._lock:
            cursor = self.conn.execute("""
                INSERT INTO transactions 
                (timestamp, domain, url, amount, currency, card_bin, card_last4,
                 psp, response_code, response_raw, status, decline_reason,
                 decline_category, decline_action, decline_severity,
                 three_ds_triggered, avs_result, cvv_result, ip_address,
                 user_agent, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                tx.get("timestamp", datetime.now(timezone.utc).isoformat()),
                tx.get("domain", "unknown"),
                tx.get("url", ""),
                tx.get("amount"),
                tx.get("currency", "USD"),
                tx.get("card_bin", ""),
                tx.get("card_last4", ""),
                tx.get("psp", "unknown"),
                tx.get("response_code", ""),
                tx.get("response_raw", ""),
                tx.get("status", "unknown"),
                tx.get("decline_reason", ""),
                tx.get("decline_category", ""),
                tx.get("decline_action", ""),
                tx.get("decline_severity", ""),
                tx.get("three_ds_triggered", 0),
                tx.get("avs_result", ""),
                tx.get("cvv_result", ""),
                tx.get("ip_address", ""),
                tx.get("user_agent", ""),
                tx.get("notes", ""),
            ))
            self.conn.commit()
            return cursor.lastrowid
    
    def query(self, where: str = "1=1", params: tuple = (), limit: int = 100) -> List[Dict]:
        with self._lock:
            cursor = self.conn.execute(
                f"SELECT * FROM transactions WHERE {where} ORDER BY timestamp DESC LIMIT ?",
                params + (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def get_stats(self, hours: int = 24) -> Dict:
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        with self._lock:
            total = self.conn.execute(
                "SELECT COUNT(*) FROM transactions WHERE timestamp > ?", (cutoff,)
            ).fetchone()[0]
            approved = self.conn.execute(
                "SELECT COUNT(*) FROM transactions WHERE timestamp > ? AND status = 'approved'", (cutoff,)
            ).fetchone()[0]
            declined = self.conn.execute(
                "SELECT COUNT(*) FROM transactions WHERE timestamp > ? AND status = 'declined'", (cutoff,)
            ).fetchone()[0]
            
            by_category = {}
            for row in self.conn.execute(
                "SELECT decline_category, COUNT(*) as cnt FROM transactions "
                "WHERE timestamp > ? AND status = 'declined' GROUP BY decline_category ORDER BY cnt DESC",
                (cutoff,)
            ).fetchall():
                by_category[row[0]] = row[1]
            
            by_site = {}
            for row in self.conn.execute(
                "SELECT domain, COUNT(*) as total, "
                "SUM(CASE WHEN status='approved' THEN 1 ELSE 0 END) as ok "
                "FROM transactions WHERE timestamp > ? GROUP BY domain ORDER BY total DESC LIMIT 20",
                (cutoff,)
            ).fetchall():
                by_site[row[0]] = {"total": row[1], "approved": row[2],
                                    "rate": round(row[2] / max(row[1], 1) * 100, 1)}
            
            by_bin = {}
            for row in self.conn.execute(
                "SELECT card_bin, COUNT(*) as total, "
                "SUM(CASE WHEN status='approved' THEN 1 ELSE 0 END) as ok "
                "FROM transactions WHERE timestamp > ? AND card_bin != '' "
                "GROUP BY card_bin ORDER BY total DESC LIMIT 20",
                (cutoff,)
            ).fetchall():
                by_bin[row[0]] = {"total": row[1], "approved": row[2],
                                   "rate": round(row[2] / max(row[1], 1) * 100, 1)}
        
        return {
            "period_hours": hours,
            "total_transactions": total,
            "approved": approved,
            "declined": declined,
            "success_rate": round(approved / max(total, 1) * 100, 1),
            "decline_breakdown": by_category,
            "by_site": by_site,
            "by_bin": by_bin,
        }


# ═══════════════════════════════════════════════════════════════════════════
# HTTP LISTENER — Receives transaction data from browser extension
# ═══════════════════════════════════════════════════════════════════════════

class TxMonitorHandler(BaseHTTPRequestHandler):
    """HTTP handler that receives transaction events from the browser extension"""
    
    monitor = None  # Set by TransactionMonitor
    
    def do_POST(self):
        if self.path == "/api/tx":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                data = json.loads(body)
                result = self.monitor.process_transaction(data)
                self._respond(200, result)
            except Exception as e:
                self._respond(400, {"error": str(e)})
        elif self.path == "/api/heartbeat":
            self._respond(200, {"status": "alive", "timestamp": datetime.now(timezone.utc).isoformat()})
        else:
            self._respond(404, {"error": "not found"})
    
    def do_GET(self):
        if self.path == "/api/stats":
            stats = self.monitor.get_stats()
            self._respond(200, stats)
        elif self.path == "/api/history":
            history = self.monitor.get_history()
            self._respond(200, {"transactions": history})
        elif self.path == "/api/declines":
            declines = self.monitor.get_declines()
            self._respond(200, {"declines": declines})
        elif self.path.startswith("/api/decode/"):
            code = self.path.split("/api/decode/")[1]
            result = DeclineDecoder.decode(code)
            self._respond(200, result)
        else:
            self._respond(404, {"error": "not found"})
    
    def _respond(self, code: int, data: Any):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
    
    def log_message(self, format, *args):
        pass  # Suppress default logging


# ═══════════════════════════════════════════════════════════════════════════
# MAIN TRANSACTION MONITOR
# ═══════════════════════════════════════════════════════════════════════════

class TransactionMonitor:
    """
    24/7 Transaction Monitor — captures, decodes, and analyzes all purchases.
    
    Usage:
        monitor = TransactionMonitor()
        monitor.start()                     # Start HTTP listener
        
        stats = monitor.get_stats()         # Get analytics
        history = monitor.get_history()     # Get transaction history
        declines = monitor.get_declines()   # Get declined transactions
        
        # Decode a specific code
        info = monitor.decode("do_not_honor", psp="stripe")
        
        # Manually log a transaction
        monitor.log_transaction({
            "domain": "g2a.com",
            "amount": 49.99,
            "card_bin": "401200",
            "response_code": "do_not_honor",
            "psp": "stripe",
            "status": "declined",
        })
    """
    
    PORT = 7443
    
    def __init__(self):
        self.db = TransactionDB()
        self.decoder = DeclineDecoder()
        self._server = None
        self._server_thread = None
    
    def start(self, port: int = None):
        """Start the HTTP listener for browser extension events"""
        port = port or self.PORT
        TxMonitorHandler.monitor = self
        self._server = HTTPServer(("127.0.0.1", port), TxMonitorHandler)
        self._server_thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._server_thread.start()
        logger.info(f"Transaction Monitor listening on http://127.0.0.1:{port}")
        return {"status": "started", "port": port}
    
    def stop(self):
        """Stop the HTTP listener"""
        if self._server:
            self._server.shutdown()
            logger.info("Transaction Monitor stopped")
    
    def process_transaction(self, data: Dict) -> Dict:
        """
        Process an incoming transaction event from the browser extension.
        Decodes the response code and stores in database.
        """
        code = data.get("response_code", data.get("code", ""))
        psp = data.get("psp", "auto")
        status = data.get("status", "unknown")
        
        # Decode the response code
        decoded = self.decoder.decode(code, psp) if code else {
            "reason": "", "category": "", "action": "", "severity": "low"
        }
        
        # Determine status from decode if not provided
        if status == "unknown" and decoded.get("category"):
            if decoded["category"] == "approved":
                status = "approved"
            elif decoded["category"] != "unknown":
                status = "declined"
        
        # Build transaction record
        tx = {
            "timestamp": data.get("timestamp", datetime.now(timezone.utc).isoformat()),
            "domain": data.get("domain", "unknown"),
            "url": data.get("url", ""),
            "amount": data.get("amount"),
            "currency": data.get("currency", "USD"),
            "card_bin": data.get("card_bin", data.get("bin", "")),
            "card_last4": data.get("card_last4", data.get("last4", "")),
            "psp": decoded.get("psp", psp),
            "response_code": code,
            "response_raw": json.dumps(data.get("raw_response", {}))[:500],
            "status": status,
            "decline_reason": decoded.get("reason", ""),
            "decline_category": decoded.get("category", ""),
            "decline_action": decoded.get("action", ""),
            "decline_severity": decoded.get("severity", ""),
            "three_ds_triggered": 1 if data.get("three_ds") else 0,
            "avs_result": data.get("avs_result", ""),
            "cvv_result": data.get("cvv_result", ""),
            "ip_address": data.get("ip", ""),
            "user_agent": data.get("user_agent", ""),
            "notes": data.get("notes", ""),
        }
        
        tx_id = self.db.insert(tx)
        
        severity_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(
            decoded.get("severity", "low"), "⚪"
        )
        
        logger.info(
            f"{severity_icon} TX #{tx_id}: {status.upper()} on {tx['domain']} "
            f"— ${tx.get('amount', '?')} — {decoded.get('reason', code)}"
        )
        
        return {
            "tx_id": tx_id,
            "status": status,
            "domain": tx["domain"],
            "amount": tx["amount"],
            "response_code": code,
            "decline_reason": decoded.get("reason", ""),
            "decline_category": decoded.get("category", ""),
            "decline_action": decoded.get("action", ""),
            "severity": decoded.get("severity", ""),
        }
    
    def log_transaction(self, data: Dict) -> Dict:
        """Manually log a transaction"""
        return self.process_transaction(data)
    
    def decode(self, code: str, psp: str = "auto") -> Dict:
        """Decode a decline code"""
        return self.decoder.decode(code, psp)
    
    def get_history(self, last_hours: int = 24, limit: int = 100) -> List[Dict]:
        """Get recent transaction history"""
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=last_hours)).isoformat()
        return self.db.query("timestamp > ?", (cutoff,), limit)
    
    def get_declines(self, last_hours: int = 24, limit: int = 50) -> List[Dict]:
        """Get recent declined transactions"""
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=last_hours)).isoformat()
        return self.db.query("timestamp > ? AND status = 'declined'", (cutoff,), limit)
    
    def get_stats(self, hours: int = 24) -> Dict:
        """Get transaction statistics"""
        return self.db.get_stats(hours)
    
    def get_stats_by_site(self, hours: int = 24) -> Dict:
        """Get success rate per site"""
        stats = self.db.get_stats(hours)
        return stats.get("by_site", {})
    
    def get_stats_by_bin(self, hours: int = 24) -> Dict:
        """Get success rate per BIN"""
        stats = self.db.get_stats(hours)
        return stats.get("by_bin", {})


# ═══════════════════════════════════════════════════════════════════════════
# CONVENIENCE EXPORTS
# ═══════════════════════════════════════════════════════════════════════════

def decode_decline(code, psp="auto"):
    """Quick: decode a decline code"""
    return DeclineDecoder.decode(code, psp)

def get_tx_stats(hours=24):
    """Quick: get transaction stats"""
    return TransactionMonitor().get_stats(hours)

def start_tx_monitor(port=7443):
    """Quick: start the transaction monitor"""
    m = TransactionMonitor()
    return m.start(port)


# ═══════════════════════════════════════════════════════════════════════════
# V7.6 P0 CRITICAL ENHANCEMENTS
# ═══════════════════════════════════════════════════════════════════════════

class TransactionAnalytics:
    """
    V7.6 P0: Advanced analytics and pattern detection for transactions.
    
    Provides deep analytics, trend detection, anomaly identification,
    and predictive insights for transaction patterns.
    """
    
    _instance = None
    
    def __init__(self, db: TransactionDB = None):
        self.db = db or TransactionDB()
        self.analytics_cache: Dict[str, Dict] = {}
        self.cache_ttl = 300  # 5 minutes
        self.logger = logging.getLogger("TITAN-TX.Analytics")
    
    def get_hourly_pattern(self, days: int = 7) -> Dict:
        """Analyze success rate by hour of day."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        
        with self.db._lock:
            rows = self.db.conn.execute("""
                SELECT 
                    CAST(strftime('%H', timestamp) AS INTEGER) as hour,
                    COUNT(*) as total,
                    SUM(CASE WHEN status='approved' THEN 1 ELSE 0 END) as approved
                FROM transactions
                WHERE timestamp > ?
                GROUP BY hour
                ORDER BY hour
            """, (cutoff,)).fetchall()
        
        hourly = {}
        for row in rows:
            hour = row[0]
            total = row[1]
            approved = row[2]
            hourly[hour] = {
                "total": total,
                "approved": approved,
                "rate": round(approved / max(total, 1) * 100, 1)
            }
        
        # Find best hours
        best_hours = sorted(hourly.items(), key=lambda x: x[1]["rate"], reverse=True)[:5]
        
        return {
            "period_days": days,
            "hourly_breakdown": hourly,
            "best_hours": [{"hour": h, **d} for h, d in best_hours],
            "recommendation": f"Best hours for transactions: {', '.join(f'{h}:00' for h, _ in best_hours[:3])}"
        }
    
    def get_site_analysis(self, min_transactions: int = 3) -> Dict:
        """Deep analysis of site performance."""
        stats = self.db.get_stats(hours=168)  # 7 days
        by_site = stats.get("by_site", {})
        
        analysis = {
            "sites_analyzed": len(by_site),
            "high_success": [],
            "low_success": [],
            "velocity_limited": [],
            "fraud_blocked": []
        }
        
        for domain, data in by_site.items():
            if data["total"] < min_transactions:
                continue
            
            rate = data["rate"]
            if rate >= 70:
                analysis["high_success"].append({"domain": domain, **data})
            elif rate < 30:
                analysis["low_success"].append({"domain": domain, **data})
        
        # Check for velocity-limited sites
        with self.db._lock:
            velocity_rows = self.db.conn.execute("""
                SELECT domain, COUNT(*) as cnt
                FROM transactions
                WHERE decline_category = 'velocity_limit'
                AND timestamp > datetime('now', '-7 days')
                GROUP BY domain
                HAVING cnt >= 2
                ORDER BY cnt DESC
            """).fetchall()
        
        for row in velocity_rows:
            analysis["velocity_limited"].append({"domain": row[0], "velocity_declines": row[1]})
        
        # Check for fraud-blocked sites
        with self.db._lock:
            fraud_rows = self.db.conn.execute("""
                SELECT domain, COUNT(*) as cnt
                FROM transactions
                WHERE decline_category IN ('fraud_block', 'risk_decline')
                AND timestamp > datetime('now', '-7 days')
                GROUP BY domain
                HAVING cnt >= 2
                ORDER BY cnt DESC
            """).fetchall()
        
        for row in fraud_rows:
            analysis["fraud_blocked"].append({"domain": row[0], "fraud_declines": row[1]})
        
        return analysis
    
    def get_bin_intelligence(self, min_transactions: int = 2) -> Dict:
        """Analyze BIN performance and scoring."""
        stats = self.db.get_stats(hours=168)
        by_bin = stats.get("by_bin", {})
        
        intelligence = {
            "bins_analyzed": len(by_bin),
            "top_performers": [],
            "poor_performers": [],
            "burned_bins": []
        }
        
        for bin_prefix, data in by_bin.items():
            if data["total"] < min_transactions:
                continue
            
            rate = data["rate"]
            entry = {"bin": bin_prefix, **data}
            
            if rate >= 80:
                intelligence["top_performers"].append(entry)
            elif rate == 0 and data["total"] >= 3:
                intelligence["burned_bins"].append(entry)
            elif rate < 30:
                intelligence["poor_performers"].append(entry)
        
        # Sort by rate
        intelligence["top_performers"].sort(key=lambda x: x["rate"], reverse=True)
        intelligence["poor_performers"].sort(key=lambda x: x["rate"])
        
        return intelligence
    
    def get_decline_analysis(self, hours: int = 168) -> Dict:
        """Analyze decline patterns and categories."""
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        
        with self.db._lock:
            category_rows = self.db.conn.execute("""
                SELECT 
                    decline_category,
                    COUNT(*) as cnt,
                    AVG(amount) as avg_amount
                FROM transactions
                WHERE timestamp > ? AND status = 'declined'
                GROUP BY decline_category
                ORDER BY cnt DESC
            """, (cutoff,)).fetchall()
        
        categories = []
        for row in category_rows:
            categories.append({
                "category": row[0],
                "count": row[1],
                "avg_amount": round(row[2], 2) if row[2] else 0,
                "percentage": 0  # Will calculate below
            })
        
        total_declines = sum(c["count"] for c in categories)
        for c in categories:
            c["percentage"] = round(c["count"] / max(total_declines, 1) * 100, 1)
        
        # Most common reasons
        with self.db._lock:
            reason_rows = self.db.conn.execute("""
                SELECT decline_reason, COUNT(*) as cnt
                FROM transactions
                WHERE timestamp > ? AND status = 'declined' AND decline_reason != ''
                GROUP BY decline_reason
                ORDER BY cnt DESC
                LIMIT 10
            """, (cutoff,)).fetchall()
        
        top_reasons = [{"reason": row[0], "count": row[1]} for row in reason_rows]
        
        return {
            "period_hours": hours,
            "total_declines": total_declines,
            "category_breakdown": categories,
            "top_decline_reasons": top_reasons,
            "actionable_insights": self._generate_insights(categories, top_reasons)
        }
    
    def _generate_insights(self, categories: List[Dict], reasons: List[Dict]) -> List[str]:
        """Generate actionable insights from decline data."""
        insights = []
        
        category_map = {c["category"]: c["percentage"] for c in categories}
        
        if category_map.get("fraud_block", 0) > 20:
            insights.append("High fraud block rate - consider profile rotation or infrastructure change")
        
        if category_map.get("velocity_limit", 0) > 15:
            insights.append("Velocity limits being hit frequently - slow down transaction pace")
        
        if category_map.get("avs_mismatch", 0) > 10:
            insights.append("AVS mismatch common - verify billing address data quality")
        
        if category_map.get("cvv_mismatch", 0) > 10:
            insights.append("CVV mismatch common - verify card data quality")
        
        if category_map.get("three_ds_fail", 0) > 20:
            insights.append("3DS failures high - focus on non-3DS merchants or improve bypass")
        
        return insights
    
    def get_trend_analysis(self, days: int = 30) -> Dict:
        """Analyze trends over time."""
        daily_stats = []
        
        for i in range(days):
            day_start = datetime.now(timezone.utc) - timedelta(days=i+1)
            day_end = datetime.now(timezone.utc) - timedelta(days=i)
            
            with self.db._lock:
                row = self.db.conn.execute("""
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN status='approved' THEN 1 ELSE 0 END) as approved
                    FROM transactions
                    WHERE timestamp >= ? AND timestamp < ?
                """, (day_start.isoformat(), day_end.isoformat())).fetchone()
            
            total = row[0]
            approved = row[1]
            daily_stats.append({
                "date": day_start.strftime("%Y-%m-%d"),
                "total": total,
                "approved": approved,
                "rate": round(approved / max(total, 1) * 100, 1)
            })
        
        # Calculate trend
        if len(daily_stats) >= 7:
            recent_avg = sum(d["rate"] for d in daily_stats[:7]) / 7
            earlier_avg = sum(d["rate"] for d in daily_stats[-7:]) / 7
            trend = "improving" if recent_avg > earlier_avg else "declining" if recent_avg < earlier_avg else "stable"
        else:
            trend = "insufficient_data"
        
        return {
            "period_days": days,
            "daily_breakdown": daily_stats,
            "trend": trend,
            "recent_7d_avg": round(sum(d["rate"] for d in daily_stats[:7]) / max(len(daily_stats[:7]), 1), 1),
            "overall_avg": round(sum(d["rate"] for d in daily_stats) / max(len(daily_stats), 1), 1)
        }


class TransactionAlertSystem:
    """
    V7.6 P0: Real-time alerting on transaction anomalies.
    
    Monitors transactions and generates alerts for important events
    like critical declines, velocity limits, and pattern changes.
    """
    
    _instance = None
    
    def __init__(self):
        self.alert_rules: List[Dict] = []
        self.alert_history: List[Dict] = []
        self.max_history = 500
        self.alert_callbacks: List[callable] = []
        self.logger = logging.getLogger("TITAN-TX.Alerts")
        
        self._register_default_rules()
    
    def _register_default_rules(self):
        """Register default alert rules."""
        self.alert_rules = [
            {
                "name": "lost_stolen_card",
                "condition": lambda tx: tx.get("decline_category") in ["lost_stolen"],
                "severity": "critical",
                "message": "Card reported lost/stolen - DISCARD IMMEDIATELY"
            },
            {
                "name": "fraud_block",
                "condition": lambda tx: tx.get("decline_category") == "fraud_block",
                "severity": "high",
                "message": "Issuer fraud block detected - card may be monitored"
            },
            {
                "name": "velocity_limit",
                "condition": lambda tx: tx.get("decline_category") == "velocity_limit",
                "severity": "high",
                "message": "Velocity limit hit - slow down transaction pace"
            },
            {
                "name": "consecutive_declines",
                "condition": self._check_consecutive_declines,
                "severity": "high",
                "message": "Multiple consecutive declines detected"
            },
            {
                "name": "large_amount_decline",
                "condition": lambda tx: tx.get("status") == "declined" and tx.get("amount", 0) >= 500,
                "severity": "medium",
                "message": "High-value transaction declined"
            }
        ]
    
    def _check_consecutive_declines(self, tx: Dict) -> bool:
        """Check for consecutive declines on same domain."""
        # This is a simplified check - in production would track history
        return False  # Handled by separate monitoring
    
    def add_rule(self, name: str, condition: callable, severity: str, message: str):
        """Add a custom alert rule."""
        self.alert_rules.append({
            "name": name,
            "condition": condition,
            "severity": severity,
            "message": message
        })
    
    def register_callback(self, callback: callable):
        """Register a callback for alerts."""
        self.alert_callbacks.append(callback)
    
    def process_transaction(self, tx: Dict) -> List[Dict]:
        """Process transaction and generate any applicable alerts."""
        alerts = []
        
        for rule in self.alert_rules:
            try:
                if rule["condition"](tx):
                    alert = {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "rule": rule["name"],
                        "severity": rule["severity"],
                        "message": rule["message"],
                        "transaction": {
                            "domain": tx.get("domain"),
                            "amount": tx.get("amount"),
                            "status": tx.get("status"),
                            "decline_category": tx.get("decline_category")
                        }
                    }
                    
                    self.alert_history.append(alert)
                    alerts.append(alert)
                    
                    self.logger.warning(
                        f"[{rule['severity'].upper()}] {rule['message']} - {tx.get('domain')}"
                    )
                    
                    # Notify callbacks
                    for callback in self.alert_callbacks:
                        try:
                            callback(alert)
                        except Exception:
                            pass
            except Exception as e:
                self.logger.error(f"Alert rule {rule['name']} error: {e}")
        
        # Trim history
        if len(self.alert_history) > self.max_history:
            self.alert_history = self.alert_history[-self.max_history:]
        
        return alerts
    
    def get_recent_alerts(self, hours: int = 24, severity: str = None) -> List[Dict]:
        """Get recent alerts."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        alerts = []
        for alert in reversed(self.alert_history):
            try:
                ts = datetime.fromisoformat(alert["timestamp"].replace('Z', '+00:00'))
                if ts < cutoff:
                    break
                if severity and alert["severity"] != severity:
                    continue
                alerts.append(alert)
            except Exception:
                continue
        
        return alerts
    
    def get_alert_summary(self, hours: int = 24) -> Dict:
        """Get summary of recent alerts."""
        alerts = self.get_recent_alerts(hours)
        
        by_severity = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        by_rule = {}
        
        for alert in alerts:
            by_severity[alert["severity"]] = by_severity.get(alert["severity"], 0) + 1
            by_rule[alert["rule"]] = by_rule.get(alert["rule"], 0) + 1
        
        return {
            "period_hours": hours,
            "total_alerts": len(alerts),
            "by_severity": by_severity,
            "by_rule": by_rule,
            "recent": alerts[:10]
        }


class CardBINIntelligence:
    """
    V7.6 P0: BIN intelligence and scoring system.
    
    Maintains intelligence on card BINs including success rates,
    issuer patterns, and scoring for card selection.
    """
    
    _instance = None
    BIN_DATA_FILE = Path("/opt/titan/data/tx_monitor/bin_intelligence.json")
    
    def __init__(self, db: TransactionDB = None):
        self.db = db or TransactionDB()
        self.bin_data: Dict[str, Dict] = {}
        self.logger = logging.getLogger("TITAN-TX.BIN")
        
        self._load_bin_data()
    
    def _load_bin_data(self):
        """Load BIN intelligence data."""
        if self.BIN_DATA_FILE.exists():
            try:
                with open(self.BIN_DATA_FILE) as f:
                    self.bin_data = json.load(f)
            except Exception as e:
                self.logger.warning(f"Failed to load BIN data: {e}")
    
    def _save_bin_data(self):
        """Save BIN intelligence data."""
        try:
            self.BIN_DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(self.BIN_DATA_FILE, 'w') as f:
                json.dump(self.bin_data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save BIN data: {e}")
    
    def update_from_transactions(self) -> int:
        """Update BIN intelligence from transaction history."""
        stats = self.db.get_stats(hours=168)  # 7 days
        by_bin = stats.get("by_bin", {})
        
        updated = 0
        for bin_prefix, data in by_bin.items():
            if bin_prefix not in self.bin_data:
                self.bin_data[bin_prefix] = {
                    "first_seen": datetime.now(timezone.utc).isoformat(),
                    "total_transactions": 0,
                    "total_approved": 0,
                    "decline_categories": {},
                    "sites_used": []
                }
            
            entry = self.bin_data[bin_prefix]
            entry["total_transactions"] = data["total"]
            entry["total_approved"] = data["approved"]
            entry["success_rate"] = data["rate"]
            entry["last_updated"] = datetime.now(timezone.utc).isoformat()
            entry["score"] = self._calculate_score(entry)
            updated += 1
        
        self._save_bin_data()
        return updated
    
    def _calculate_score(self, entry: Dict) -> int:
        """Calculate BIN score (0-100)."""
        score = 50  # Base score
        
        # Success rate impact (-30 to +30)
        rate = entry.get("success_rate", 50)
        score += (rate - 50) * 0.6
        
        # Transaction volume impact (+0 to +10)
        total = entry.get("total_transactions", 0)
        if total >= 10:
            score += 10
        elif total >= 5:
            score += 5
        elif total >= 2:
            score += 2
        
        # Penalty for fraud blocks
        categories = entry.get("decline_categories", {})
        if categories.get("fraud_block", 0) > 0:
            score -= 20
        if categories.get("lost_stolen", 0) > 0:
            score -= 50  # Heavily penalize
        
        return max(0, min(100, int(score)))
    
    def get_bin_score(self, bin_prefix: str) -> Dict:
        """Get score and intelligence for a BIN."""
        if bin_prefix in self.bin_data:
            return self.bin_data[bin_prefix]
        return {"bin": bin_prefix, "score": 50, "status": "unknown"}
    
    def get_top_bins(self, limit: int = 20) -> List[Dict]:
        """Get top performing BINs by score."""
        bins = []
        for bin_prefix, data in self.bin_data.items():
            if data.get("total_transactions", 0) >= 2:
                bins.append({"bin": bin_prefix, **data})
        
        bins.sort(key=lambda x: x.get("score", 0), reverse=True)
        return bins[:limit]
    
    def get_burned_bins(self) -> List[str]:
        """Get list of burned/blocked BINs."""
        burned = []
        for bin_prefix, data in self.bin_data.items():
            categories = data.get("decline_categories", {})
            if categories.get("lost_stolen", 0) > 0:
                burned.append(bin_prefix)
            elif data.get("success_rate", 100) == 0 and data.get("total_transactions", 0) >= 3:
                burned.append(bin_prefix)
        return burned
    
    def record_decline(self, bin_prefix: str, category: str):
        """Record a decline category for a BIN."""
        if bin_prefix not in self.bin_data:
            self.bin_data[bin_prefix] = {
                "first_seen": datetime.now(timezone.utc).isoformat(),
                "total_transactions": 0,
                "total_approved": 0,
                "decline_categories": {},
                "sites_used": []
            }
        
        entry = self.bin_data[bin_prefix]
        if "decline_categories" not in entry:
            entry["decline_categories"] = {}
        
        entry["decline_categories"][category] = entry["decline_categories"].get(category, 0) + 1
        entry["score"] = self._calculate_score(entry)
        self._save_bin_data()


class TransactionExporter:
    """
    V7.6 P0: Export transactions in various formats.
    
    Supports exporting transaction data to CSV, JSON, and
    other formats for analysis and reporting.
    """
    
    _instance = None
    
    def __init__(self, db: TransactionDB = None):
        self.db = db or TransactionDB()
        self.export_dir = Path("/opt/titan/data/tx_exports")
        self.logger = logging.getLogger("TITAN-TX.Exporter")
    
    def export_csv(self, filename: str = None, hours: int = 168) -> Path:
        """Export transactions to CSV."""
        import csv
        
        self.export_dir.mkdir(parents=True, exist_ok=True)
        filename = filename or f"transactions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = self.export_dir / filename
        
        transactions = self.db.query(
            f"timestamp > datetime('now', '-{hours} hours')",
            limit=10000
        )
        
        if not transactions:
            return None
        
        with open(filepath, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=transactions[0].keys())
            writer.writeheader()
            writer.writerows(transactions)
        
        self.logger.info(f"Exported {len(transactions)} transactions to {filepath}")
        return filepath
    
    def export_json(self, filename: str = None, hours: int = 168) -> Path:
        """Export transactions to JSON."""
        self.export_dir.mkdir(parents=True, exist_ok=True)
        filename = filename or f"transactions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.export_dir / filename
        
        transactions = self.db.query(
            f"timestamp > datetime('now', '-{hours} hours')",
            limit=10000
        )
        
        with open(filepath, 'w') as f:
            json.dump({
                "exported": datetime.now(timezone.utc).isoformat(),
                "period_hours": hours,
                "count": len(transactions),
                "transactions": transactions
            }, f, indent=2)
        
        self.logger.info(f"Exported {len(transactions)} transactions to {filepath}")
        return filepath
    
    def export_summary_report(self, filename: str = None, hours: int = 168) -> Path:
        """Export summary report."""
        self.export_dir.mkdir(parents=True, exist_ok=True)
        filename = filename or f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.export_dir / filename
        
        stats = self.db.get_stats(hours)
        analytics = TransactionAnalytics(self.db)
        
        report = {
            "generated": datetime.now(timezone.utc).isoformat(),
            "period_hours": hours,
            "summary": stats,
            "hourly_pattern": analytics.get_hourly_pattern(days=hours//24),
            "site_analysis": analytics.get_site_analysis(),
            "bin_intelligence": analytics.get_bin_intelligence(),
            "decline_analysis": analytics.get_decline_analysis(hours)
        }
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.logger.info(f"Exported summary report to {filepath}")
        return filepath
    
    def list_exports(self) -> List[Dict]:
        """List available exports."""
        if not self.export_dir.exists():
            return []
        
        exports = []
        for f in self.export_dir.glob("*"):
            if f.is_file():
                exports.append({
                    "filename": f.name,
                    "size_bytes": f.stat().st_size,
                    "created": datetime.fromtimestamp(f.stat().st_ctime).isoformat()
                })
        
        exports.sort(key=lambda x: x["created"], reverse=True)
        return exports


# ═══════════════════════════════════════════════════════════════════════════
# V7.6 SINGLETON GETTERS
# ═══════════════════════════════════════════════════════════════════════════

def get_transaction_analytics() -> TransactionAnalytics:
    """Get singleton TransactionAnalytics instance."""
    if TransactionAnalytics._instance is None:
        TransactionAnalytics._instance = TransactionAnalytics()
    return TransactionAnalytics._instance


def get_transaction_alert_system() -> TransactionAlertSystem:
    """Get singleton TransactionAlertSystem instance."""
    if TransactionAlertSystem._instance is None:
        TransactionAlertSystem._instance = TransactionAlertSystem()
    return TransactionAlertSystem._instance


def get_card_bin_intelligence() -> CardBINIntelligence:
    """Get singleton CardBINIntelligence instance."""
    if CardBINIntelligence._instance is None:
        CardBINIntelligence._instance = CardBINIntelligence()
    return CardBINIntelligence._instance


def get_transaction_exporter() -> TransactionExporter:
    """Get singleton TransactionExporter instance."""
    if TransactionExporter._instance is None:
        TransactionExporter._instance = TransactionExporter()
    return TransactionExporter._instance
