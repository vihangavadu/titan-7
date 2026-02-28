#!/usr/bin/env python3
"""
TITAN V9.1 CARD VALIDATOR — BIN Check, Card Quality, AVS
=========================================================
Focused app for card validation and intelligence.

3 tabs:
  1. VALIDATE — Card number input, BIN lookup, Luhn check
  2. INTELLIGENCE — BIN scoring, card quality grading, issuer intel
  3. HISTORY — Validation history log
"""

import sys
import os
import json
import random
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / "core"))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QGroupBox, QFormLayout,
    QTabWidget, QComboBox, QMessageBox, QScrollArea, QPlainTextEdit,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

ACCENT = "#eab308"
BG = "#0a0e17"
BG_CARD = "#111827"
TEXT = "#e2e8f0"
TEXT2 = "#64748b"
GREEN = "#22c55e"
YELLOW = "#eab308"
RED = "#ef4444"
ORANGE = "#f97316"

try:
    from titan_theme import apply_titan_theme, make_tab_style
    THEME_OK = True
except ImportError:
    THEME_OK = False

# ═══════════════════════════════════════════════════════════════════════════════
# BUILT-IN BIN DATABASE (works without core modules)
# ═══════════════════════════════════════════════════════════════════════════════
_BIN_DB = {
    # ── Chase (largest US card issuer) ────────────────────────────────
    "453201": {"bank": "Chase", "type": "Credit", "level": "Signature", "country": "US", "network": "VISA", "risk": "low"},
    "453211": {"bank": "Chase", "type": "Credit", "level": "Signature Preferred", "country": "US", "network": "VISA", "risk": "low"},
    "414709": {"bank": "Chase", "type": "Credit", "level": "Amazon Prime", "country": "US", "network": "VISA", "risk": "low"},
    "423464": {"bank": "Chase", "type": "Credit", "level": "Freedom Unlimited", "country": "US", "network": "VISA", "risk": "low"},
    "402400": {"bank": "Chase", "type": "Credit", "level": "Sapphire Reserve", "country": "US", "network": "VISA", "risk": "low"},
    "491656": {"bank": "Chase", "type": "Debit", "level": "Classic", "country": "US", "network": "VISA", "risk": "medium"},
    "448490": {"bank": "Chase", "type": "Debit", "level": "Checking", "country": "US", "network": "VISA", "risk": "medium"},
    "542598": {"bank": "Chase", "type": "Credit", "level": "World Elite", "country": "US", "network": "MASTERCARD", "risk": "low"},
    "525893": {"bank": "Chase", "type": "Credit", "level": "Ink Business", "country": "US", "network": "MASTERCARD", "risk": "low"},
    # ── Bank of America ──────────────────────────────────────────────
    "455600": {"bank": "Bank of America", "type": "Credit", "level": "Platinum", "country": "US", "network": "VISA", "risk": "low"},
    "455602": {"bank": "Bank of America", "type": "Credit", "level": "Customized Cash", "country": "US", "network": "VISA", "risk": "low"},
    "428800": {"bank": "Bank of America", "type": "Credit", "level": "Premium Rewards", "country": "US", "network": "VISA", "risk": "low"},
    "481514": {"bank": "Bank of America", "type": "Credit", "level": "Travel Rewards", "country": "US", "network": "VISA", "risk": "low"},
    "439225": {"bank": "Bank of America", "type": "Debit", "level": "Checking", "country": "US", "network": "VISA", "risk": "medium"},
    "549580": {"bank": "Bank of America", "type": "Credit", "level": "World", "country": "US", "network": "MASTERCARD", "risk": "low"},
    # ── Citi ─────────────────────────────────────────────────────────
    "400011": {"bank": "Citi", "type": "Credit", "level": "World Elite", "country": "US", "network": "VISA", "risk": "low"},
    "400025": {"bank": "Citi", "type": "Credit", "level": "Double Cash", "country": "US", "network": "VISA", "risk": "low"},
    "479236": {"bank": "Citi", "type": "Credit", "level": "Custom Cash", "country": "US", "network": "VISA", "risk": "low"},
    "417494": {"bank": "Citi", "type": "Credit", "level": "Premier", "country": "US", "network": "VISA", "risk": "low"},
    "466898": {"bank": "Citi", "type": "Credit", "level": "Rewards+", "country": "US", "network": "VISA", "risk": "low"},
    "539900": {"bank": "Citi", "type": "Credit", "level": "World", "country": "US", "network": "MASTERCARD", "risk": "low"},
    "546616": {"bank": "Citi", "type": "Credit", "level": "Costco Anywhere", "country": "US", "network": "MASTERCARD", "risk": "low"},
    # ── Capital One ──────────────────────────────────────────────────
    "471600": {"bank": "Capital One", "type": "Credit", "level": "World", "country": "US", "network": "VISA", "risk": "low"},
    "471610": {"bank": "Capital One", "type": "Credit", "level": "Venture X", "country": "US", "network": "VISA", "risk": "low"},
    "421738": {"bank": "Capital One", "type": "Credit", "level": "Quicksilver", "country": "US", "network": "VISA", "risk": "low"},
    "425432": {"bank": "Capital One", "type": "Credit", "level": "SavorOne", "country": "US", "network": "VISA", "risk": "low"},
    "414734": {"bank": "Capital One", "type": "Credit", "level": "Venture One", "country": "US", "network": "VISA", "risk": "low"},
    "516805": {"bank": "Capital One", "type": "Credit", "level": "Platinum", "country": "US", "network": "MASTERCARD", "risk": "low"},
    "530060": {"bank": "Capital One", "type": "Credit", "level": "Walmart Rewards", "country": "US", "network": "MASTERCARD", "risk": "low"},
    # ── Wells Fargo ──────────────────────────────────────────────────
    "492910": {"bank": "Wells Fargo", "type": "Credit", "level": "Signature", "country": "US", "network": "VISA", "risk": "low"},
    "485953": {"bank": "Wells Fargo", "type": "Credit", "level": "Active Cash", "country": "US", "network": "VISA", "risk": "low"},
    "480261": {"bank": "Wells Fargo", "type": "Credit", "level": "Autograph", "country": "US", "network": "VISA", "risk": "low"},
    "404841": {"bank": "Wells Fargo", "type": "Debit", "level": "Checking", "country": "US", "network": "VISA", "risk": "medium"},
    "521468": {"bank": "Wells Fargo", "type": "Credit", "level": "Platinum", "country": "US", "network": "MASTERCARD", "risk": "medium"},
    # ── American Express ─────────────────────────────────────────────
    "378282": {"bank": "Amex", "type": "Credit", "level": "Gold", "country": "US", "network": "AMEX", "risk": "low"},
    "371449": {"bank": "Amex", "type": "Credit", "level": "Platinum", "country": "US", "network": "AMEX", "risk": "low"},
    "371414": {"bank": "Amex", "type": "Credit", "level": "Hilton Honors", "country": "US", "network": "AMEX", "risk": "low"},
    "379254": {"bank": "Amex", "type": "Credit", "level": "Blue Cash Preferred", "country": "US", "network": "AMEX", "risk": "low"},
    "340000": {"bank": "Amex", "type": "Credit", "level": "Green", "country": "US", "network": "AMEX", "risk": "medium"},
    "347000": {"bank": "Amex", "type": "Credit", "level": "Delta SkyMiles", "country": "US", "network": "AMEX", "risk": "low"},
    "373953": {"bank": "Amex", "type": "Credit", "level": "Business Gold", "country": "US", "network": "AMEX", "risk": "low"},
    "376655": {"bank": "Amex", "type": "Charge", "level": "Centurion (Black)", "country": "US", "network": "AMEX", "risk": "low"},
    # ── Discover ─────────────────────────────────────────────────────
    "601100": {"bank": "Discover", "type": "Credit", "level": "Standard", "country": "US", "network": "DISCOVER", "risk": "medium"},
    "601101": {"bank": "Discover", "type": "Credit", "level": "it Cash Back", "country": "US", "network": "DISCOVER", "risk": "medium"},
    "644500": {"bank": "Discover", "type": "Credit", "level": "Premium", "country": "US", "network": "DISCOVER", "risk": "medium"},
    "650032": {"bank": "Discover", "type": "Credit", "level": "Miles", "country": "US", "network": "DISCOVER", "risk": "medium"},
    # ── USAA ─────────────────────────────────────────────────────────
    "414720": {"bank": "USAA", "type": "Credit", "level": "Signature", "country": "US", "network": "VISA", "risk": "low"},
    "414724": {"bank": "USAA", "type": "Credit", "level": "Preferred Cash Rewards", "country": "US", "network": "VISA", "risk": "low"},
    "414729": {"bank": "USAA", "type": "Credit", "level": "Rate Advantage", "country": "US", "network": "VISA", "risk": "low"},
    "530750": {"bank": "USAA", "type": "Credit", "level": "World Elite", "country": "US", "network": "MASTERCARD", "risk": "low"},
    # ── Navy Federal ─────────────────────────────────────────────────
    "459236": {"bank": "Navy Federal", "type": "Credit", "level": "Visa Signature", "country": "US", "network": "VISA", "risk": "low"},
    "459237": {"bank": "Navy Federal", "type": "Credit", "level": "cashRewards", "country": "US", "network": "VISA", "risk": "low"},
    "489626": {"bank": "Navy Federal", "type": "Credit", "level": "More Rewards", "country": "US", "network": "VISA", "risk": "low"},
    # ── TD Bank ──────────────────────────────────────────────────────
    "476173": {"bank": "TD Bank", "type": "Debit", "level": "Classic", "country": "US", "network": "VISA", "risk": "high"},
    "476171": {"bank": "TD Bank", "type": "Credit", "level": "Cash Credit Card", "country": "US", "network": "VISA", "risk": "medium"},
    # ── PNC / US Bank / Regions / SunTrust ───────────────────────────
    "431940": {"bank": "PNC Bank", "type": "Credit", "level": "Signature", "country": "US", "network": "VISA", "risk": "medium"},
    "431943": {"bank": "PNC Bank", "type": "Credit", "level": "Cash Rewards", "country": "US", "network": "VISA", "risk": "medium"},
    "405266": {"bank": "US Bank", "type": "Credit", "level": "Altitude Connect", "country": "US", "network": "VISA", "risk": "low"},
    "488893": {"bank": "US Bank", "type": "Credit", "level": "Altitude Go", "country": "US", "network": "VISA", "risk": "low"},
    "447261": {"bank": "US Bank", "type": "Credit", "level": "Cash+", "country": "US", "network": "VISA", "risk": "low"},
    "419773": {"bank": "Regions Bank", "type": "Credit", "level": "Visa Signature", "country": "US", "network": "VISA", "risk": "medium"},
    "490824": {"bank": "Truist", "type": "Credit", "level": "Enjoy Cash", "country": "US", "network": "VISA", "risk": "medium"},
    # ── Synchrony / Store Cards ──────────────────────────────────────
    "606462": {"bank": "Synchrony", "type": "Credit", "level": "Amazon Store", "country": "US", "network": "VISA", "risk": "medium"},
    "493696": {"bank": "Synchrony", "type": "Credit", "level": "PayPal Cashback", "country": "US", "network": "VISA", "risk": "medium"},
    "410165": {"bank": "Synchrony", "type": "Credit", "level": "Verizon Visa", "country": "US", "network": "VISA", "risk": "medium"},
    "403460": {"bank": "Barclays US", "type": "Credit", "level": "AAdvantage", "country": "US", "network": "VISA", "risk": "low"},
    "417484": {"bank": "Barclays US", "type": "Credit", "level": "JetBlue", "country": "US", "network": "VISA", "risk": "low"},
    # ── Goldman Sachs (Apple Card) ───────────────────────────────────
    "518791": {"bank": "Goldman Sachs", "type": "Credit", "level": "Apple Card", "country": "US", "network": "MASTERCARD", "risk": "low"},
    "528187": {"bank": "Goldman Sachs", "type": "Credit", "level": "Apple Card", "country": "US", "network": "MASTERCARD", "risk": "low"},
    # ── Credit Unions ────────────────────────────────────────────────
    "426684": {"bank": "Pentagon FCU", "type": "Credit", "level": "Pathfinder", "country": "US", "network": "VISA", "risk": "low"},
    "406397": {"bank": "Alliant CU", "type": "Credit", "level": "Visa Platinum", "country": "US", "network": "VISA", "risk": "low"},
    "480088": {"bank": "SchoolsFirst FCU", "type": "Credit", "level": "Visa Platinum", "country": "US", "network": "VISA", "risk": "low"},
    # ── UK Banks ─────────────────────────────────────────────────────
    "475129": {"bank": "Barclays UK", "type": "Debit", "level": "Classic", "country": "GB", "network": "VISA", "risk": "low"},
    "454313": {"bank": "Lloyds Bank", "type": "Debit", "level": "Classic", "country": "GB", "network": "VISA", "risk": "low"},
    "465942": {"bank": "HSBC UK", "type": "Debit", "level": "Classic", "country": "GB", "network": "VISA", "risk": "low"},
    "492181": {"bank": "NatWest", "type": "Debit", "level": "Classic", "country": "GB", "network": "VISA", "risk": "low"},
    "454742": {"bank": "Santander UK", "type": "Debit", "level": "Classic", "country": "GB", "network": "VISA", "risk": "low"},
    "539140": {"bank": "Barclays UK", "type": "Credit", "level": "Barclaycard", "country": "GB", "network": "MASTERCARD", "risk": "low"},
    "541275": {"bank": "HSBC UK", "type": "Credit", "level": "World Elite", "country": "GB", "network": "MASTERCARD", "risk": "low"},
    "535522": {"bank": "Lloyds Bank", "type": "Credit", "level": "Platinum", "country": "GB", "network": "MASTERCARD", "risk": "low"},
    # ── Canadian Banks ───────────────────────────────────────────────
    "450140": {"bank": "Royal Bank CA", "type": "Credit", "level": "Visa Infinite", "country": "CA", "network": "VISA", "risk": "low"},
    "455950": {"bank": "TD Canada", "type": "Credit", "level": "Visa Infinite", "country": "CA", "network": "VISA", "risk": "low"},
    "454617": {"bank": "CIBC", "type": "Credit", "level": "Visa Infinite", "country": "CA", "network": "VISA", "risk": "low"},
    "549186": {"bank": "BMO", "type": "Credit", "level": "World Elite", "country": "CA", "network": "MASTERCARD", "risk": "low"},
    "520468": {"bank": "Scotiabank", "type": "Credit", "level": "World", "country": "CA", "network": "MASTERCARD", "risk": "low"},
    # ── European Banks ───────────────────────────────────────────────
    "492923": {"bank": "N26", "type": "Debit", "level": "Standard", "country": "DE", "network": "VISA", "risk": "medium"},
    "427238": {"bank": "Revolut", "type": "Debit", "level": "Standard", "country": "GB", "network": "VISA", "risk": "high"},
    "535301": {"bank": "Revolut", "type": "Prepaid", "level": "Metal", "country": "GB", "network": "MASTERCARD", "risk": "high"},
    "516732": {"bank": "Wise", "type": "Debit", "level": "Standard", "country": "GB", "network": "MASTERCARD", "risk": "high"},
    "459010": {"bank": "ING", "type": "Debit", "level": "Classic", "country": "NL", "network": "VISA", "risk": "low"},
    "542418": {"bank": "BNP Paribas", "type": "Credit", "level": "World", "country": "FR", "network": "MASTERCARD", "risk": "low"},
    "512345": {"bank": "Deutsche Bank", "type": "Credit", "level": "Gold", "country": "DE", "network": "MASTERCARD", "risk": "low"},
    # ── Australian Banks ─────────────────────────────────────────────
    "456420": {"bank": "Commonwealth Bank", "type": "Debit", "level": "Debit Mastercard", "country": "AU", "network": "VISA", "risk": "low"},
    "455703": {"bank": "Westpac", "type": "Credit", "level": "Altitude Platinum", "country": "AU", "network": "VISA", "risk": "low"},
    "530089": {"bank": "ANZ", "type": "Credit", "level": "Frequent Flyer", "country": "AU", "network": "MASTERCARD", "risk": "low"},
    # ── Fintech / Neobanks (HIGH RISK — often flagged) ───────────────
    "448591": {"bank": "Chime", "type": "Debit", "level": "Spending", "country": "US", "network": "VISA", "risk": "high"},
    "423223": {"bank": "Cash App", "type": "Debit", "level": "Cash Card", "country": "US", "network": "VISA", "risk": "high"},
    "440393": {"bank": "Venmo", "type": "Debit", "level": "Venmo Debit", "country": "US", "network": "VISA", "risk": "high"},
    "512604": {"bank": "Current", "type": "Debit", "level": "Current Card", "country": "US", "network": "MASTERCARD", "risk": "high"},
    "420236": {"bank": "Green Dot", "type": "Prepaid", "level": "Prepaid", "country": "US", "network": "VISA", "risk": "high"},
    "476194": {"bank": "NetSpend", "type": "Prepaid", "level": "Prepaid", "country": "US", "network": "VISA", "risk": "high"},
    # ── Test / Generic ───────────────────────────────────────────────
    "411111": {"bank": "Test/Generic", "type": "Credit", "level": "Classic", "country": "US", "network": "VISA", "risk": "high"},
    "555555": {"bank": "Test/Generic", "type": "Credit", "level": "Standard", "country": "US", "network": "MASTERCARD", "risk": "high"},
    "400000": {"bank": "Test/Generic", "type": "Credit", "level": "Classic", "country": "US", "network": "VISA", "risk": "high"},
}
# Load cached BINs from disk if available
_BIN_CACHE_PATH = Path(os.path.expanduser("~/.titan/bin_cache.json"))
if _BIN_CACHE_PATH.exists():
    try:
        _cached = json.loads(_BIN_CACHE_PATH.read_text())
        _BIN_DB.update(_cached)
    except Exception:
        pass

def _save_bin_cache(bin6, info):
    _BIN_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        cache = json.loads(_BIN_CACHE_PATH.read_text()) if _BIN_CACHE_PATH.exists() else {}
        cache[bin6] = info
        _BIN_CACHE_PATH.write_text(json.dumps(cache, indent=2))
    except Exception:
        pass

def _luhn_check(card_number):
    digits = [int(d) for d in card_number if d.isdigit()]
    if not digits:
        return False
    checksum = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0

def _detect_network(card):
    if not card:
        return "UNKNOWN"
    if card[0] == "4":
        return "VISA"
    elif card[0] == "5" and len(card) > 1 and card[1] in "12345":
        return "MASTERCARD"
    elif card[:2] in ("34", "37"):
        return "AMEX"
    elif card[:4] == "6011" or card[:3] == "644" or card[:3] == "645" or card[:2] == "65":
        return "DISCOVER"
    elif card[:4] in ("2221", "2720") or (len(card) >= 4 and 2221 <= int(card[:4]) <= 2720):
        return "MASTERCARD"
    return "UNKNOWN"

def _lookup_bin(bin6):
    if bin6 in _BIN_DB:
        return _BIN_DB[bin6]
    for prefix_len in (5, 4):
        prefix = bin6[:prefix_len]
        for k, v in _BIN_DB.items():
            if k.startswith(prefix):
                return {**v, "approximate": True}
    return None

def _score_card(card, bin_info):
    score = 50
    reasons = []
    if _luhn_check(card):
        score += 10
        reasons.append("Luhn PASS")
    else:
        score -= 30
        reasons.append("Luhn FAIL")
    if bin_info:
        risk = bin_info.get("risk", "medium")
        if risk == "low":
            score += 20
            reasons.append(f"Low-risk issuer ({bin_info['bank']})")
        elif risk == "high":
            score -= 15
            reasons.append(f"High-risk issuer ({bin_info['bank']})")
        level = bin_info.get("level", "")
        if any(k in level.lower() for k in ["world elite", "signature", "platinum", "infinite"]):
            score += 10
            reasons.append(f"Premium tier: {level}")
        if bin_info.get("type") == "Credit":
            score += 5
            reasons.append("Credit card (preferred)")
        elif bin_info.get("type") == "Debit":
            score -= 5
            reasons.append("Debit card (less preferred)")
    else:
        reasons.append("BIN not in database")
    return max(0, min(100, score)), reasons

def _generate_test_card(network="visa"):
    bins = {"visa": ["4532","4556","4916"], "mastercard": ["5425","5399","5168"],
            "amex": ["3782","3714"], "discover": ["6011","6445"]}
    prefix = random.choice(bins.get(network, bins["visa"]))
    length = 15 if network == "amex" else 16
    body = prefix + "".join(str(random.randint(0, 9)) for _ in range(length - len(prefix) - 1))
    digits = [int(d) for d in body]
    odd = sum(digits[-1::-2])
    even = sum(sum(divmod(2 * d, 10)) for d in digits[-2::-2])
    check = (10 - (odd + even) % 10) % 10
    return body + str(check)

try:
    from cerberus_core import CerberusValidator, CardAsset
    CERBERUS_OK = True
except ImportError:
    CERBERUS_OK = False

try:
    from cerberus_enhanced import (
        AVSEngine, BINScoringEngine, SilentValidationEngine,
        CardQualityGrader, OSINTVerifier, GeoMatchChecker
    )
    ENHANCED_OK = True
except ImportError:
    ENHANCED_OK = False

try:
    from cerberus_core import CardCoolingSystem, IssuerVelocityTracker
    COOLING_OK = True
except ImportError:
    COOLING_OK = False

try:
    from three_ds_strategy import ThreeDSStrategy, get_3ds_strategy
    TDS_OK = True
except ImportError:
    TDS_OK = False

try:
    from target_intelligence import get_target_intel
    INTEL_OK = True
except ImportError:
    INTEL_OK = False

try:
    from preflight_validator import PreFlightValidator
    PREFLIGHT_OK = True
except ImportError:
    PREFLIGHT_OK = False

try:
    from titan_session import get_session, update_session
    SESSION_OK = True
except ImportError:
    SESSION_OK = False

# V8.3: AI detection vector sanitization
try:
    from ai_intelligence_engine import (
        analyze_bin, optimize_card_rotation, schedule_velocity,
        pre_validate_avs, autopsy_decline,
    )
    AI_V83_OK = True
except ImportError:
    AI_V83_OK = False


class ValidateWorker(QThread):
    finished = pyqtSignal(dict)

    def __init__(self, card_number, exp="", cvv="", target="", parent=None):
        super().__init__(parent)
        self.card_number = card_number
        self.exp = exp
        self.cvv = cvv
        self.target = target
        self._stop_flag = __import__('threading').Event()

    def stop(self):
        """V8.3 FIX #2: Signal worker to stop cleanly."""
        self._stop_flag.set()

    def run(self):
        result = {"card": self.card_number[:6] + "..." if len(self.card_number) > 6 else self.card_number}

        # Luhn check
        digits = [int(d) for d in self.card_number if d.isdigit()]
        if digits:
            checksum = 0
            for i, d in enumerate(reversed(digits)):
                if i % 2 == 1:
                    d *= 2
                    if d > 9:
                        d -= 9
                checksum += d
            result["luhn"] = checksum % 10 == 0
        else:
            result["luhn"] = False

        # BIN info
        bin6 = self.card_number[:6] if len(self.card_number) >= 6 else ""
        result["bin"] = bin6

        # Network detection
        first = self.card_number[0] if self.card_number else ""
        if first == "4":
            result["network"] = "VISA"
        elif first == "5":
            result["network"] = "MASTERCARD"
        elif first == "3":
            result["network"] = "AMEX"
        elif first == "6":
            result["network"] = "DISCOVER"
        else:
            result["network"] = "UNKNOWN"

        # Cerberus validation
        if CERBERUS_OK:
            try:
                cv = CerberusValidator()
                card = CardAsset(
                    number=self.card_number,
                    exp_month=self.exp[:2] if self.exp else "",
                    exp_year=self.exp[2:] if len(self.exp) >= 4 else self.exp[3:] if len(self.exp) >= 5 else "",
                    cvv=self.cvv,
                )
                vr = cv.validate(card, target=self.target)
                result["cerberus"] = {
                    "status": getattr(vr, 'status', 'unknown'),
                    "score": getattr(vr, 'score', 0),
                    "details": str(vr),
                }
            except Exception as e:
                result["cerberus"] = {"status": "error", "error": str(e)[:100]}

        # BIN scoring
        if ENHANCED_OK and bin6:
            try:
                scorer = BINScoringEngine()
                score = scorer.score(bin6)
                result["bin_score"] = score
            except Exception:
                pass

            try:
                grader = CardQualityGrader()
                grade = grader.grade(self.card_number)
                result["quality_grade"] = str(grade)
            except Exception:
                pass

        # 3DS strategy
        if TDS_OK and bin6:
            try:
                strategy = get_3ds_strategy(bin6, target=self.target)
                result["tds_strategy"] = str(strategy)
            except Exception:
                pass

        # V8.3: AI-powered BIN deep analysis
        if AI_V83_OK and bin6:
            try:
                ai_bin = analyze_bin(bin6, target=self.target)
                result["v83_ai_bin"] = {
                    "ai_score": ai_bin.ai_score,
                    "success_prediction": ai_bin.success_prediction,
                    "risk_level": ai_bin.risk_level.value if hasattr(ai_bin.risk_level, 'value') else str(ai_bin.risk_level),
                    "best_targets": ai_bin.best_targets,
                    "timing_advice": ai_bin.timing_advice,
                    "strategic_notes": ai_bin.strategic_notes,
                    "ai_powered": ai_bin.ai_powered,
                }
            except Exception:
                pass

            # V8.3: AVS pre-validation
            try:
                address = {
                    "street": self.target,  # placeholder — real address from session
                    "zip": "",
                }
                avs = pre_validate_avs(address, card_country="US", target=self.target)
                result["v83_avs"] = {
                    "likely_pass": avs.avs_likely_pass,
                    "confidence": avs.confidence,
                    "issues": avs.issues,
                    "ai_powered": avs.ai_powered,
                }
            except Exception:
                pass

        result["timestamp"] = datetime.now().isoformat()
        self.finished.emit(result)


class TitanCardValidator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.validation_history = []
        self.init_ui()
        self.apply_theme()

    def apply_theme(self):
        if THEME_OK:
            apply_titan_theme(self, ACCENT)
            self.tabs.setStyleSheet(make_tab_style(ACCENT))
        else:
            self.setStyleSheet(f"background: {BG}; color: {TEXT};")

    def init_ui(self):
        self.setWindowTitle("TITAN V9.1 — Card Validator")
        self.setMinimumSize(900, 700)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)

        hdr = QLabel("CARD VALIDATOR")
        hdr.setFont(QFont("Inter", 18, QFont.Weight.Bold))
        hdr.setStyleSheet(f"color: {ACCENT};")
        layout.addWidget(hdr)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self._build_validate_tab()
        self._build_intel_tab()
        self._build_history_tab()

    def _build_validate_tab(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(tab)
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        # Traffic Light Display
        tl_grp = QGroupBox("Traffic Light")
        tl_layout = QHBoxLayout(tl_grp)
        tl_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.traffic_light = QLabel("\u25cf")
        self.traffic_light.setFont(QFont("Inter", 64))
        self.traffic_light.setStyleSheet("color: #334155;")
        self.traffic_light.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tl_layout.addWidget(self.traffic_light)
        self.traffic_label = QLabel("AWAITING INPUT")
        self.traffic_label.setFont(QFont("Inter", 16, QFont.Weight.Bold))
        self.traffic_label.setStyleSheet(f"color: {TEXT2};")
        self.traffic_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tl_layout.addWidget(self.traffic_label)
        self.traffic_score = QLabel("")
        self.traffic_score.setFont(QFont("Inter", 20, QFont.Weight.Bold))
        self.traffic_score.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tl_layout.addWidget(self.traffic_score)
        layout.addWidget(tl_grp)

        # Input
        grp = QGroupBox("Card Input")
        gf = QFormLayout(grp)
        self.val_card = QLineEdit()
        self.val_card.setPlaceholderText("Card number (16 digits)")
        self.val_card.setMaxLength(19)
        gf.addRow("Card:", self.val_card)
        self.val_exp = QLineEdit()
        self.val_exp.setPlaceholderText("MMYY or MM/YY")
        self.val_exp.setMaxLength(5)
        gf.addRow("Expiry:", self.val_exp)
        self.val_cvv = QLineEdit()
        self.val_cvv.setPlaceholderText("CVV")
        self.val_cvv.setMaxLength(4)
        gf.addRow("CVV:", self.val_cvv)
        self.val_target = QComboBox()
        self.val_target.setEditable(True)
        self.val_target.addItems(["amazon.com", "ebay.com", "walmart.com", "bestbuy.com", "shopify.com", "target.com", "stripe.com"])
        gf.addRow("Target:", self.val_target)
        layout.addWidget(grp)

        # Button row
        btn_row = QHBoxLayout()
        self.validate_btn = QPushButton("VALIDATE CARD")
        self.validate_btn.setStyleSheet(f"background: {ACCENT}; color: black; padding: 14px 32px; border-radius: 8px; font-weight: bold; font-size: 14px;")
        self.validate_btn.clicked.connect(self._validate)
        btn_row.addWidget(self.validate_btn)

        gen_btn = QPushButton("Generate Test Card")
        gen_btn.setStyleSheet(f"background: {BG_CARD}; color: {TEXT}; padding: 14px 18px; border: 1px solid #334155; border-radius: 8px;")
        gen_btn.clicked.connect(self._generate_test_card)
        btn_row.addWidget(gen_btn)

        batch_btn = QPushButton("Batch Validate (Clipboard)")
        batch_btn.setStyleSheet(f"background: {BG_CARD}; color: {TEXT}; padding: 14px 18px; border: 1px solid #334155; border-radius: 8px;")
        batch_btn.clicked.connect(self._batch_validate)
        btn_row.addWidget(batch_btn)
        layout.addLayout(btn_row)

        # Module status
        mgrp = QGroupBox("Module Status")
        mf = QVBoxLayout(mgrp)
        modules = [
            ("Cerberus Validator", CERBERUS_OK),
            ("Enhanced (AVS/BIN/Quality)", ENHANCED_OK),
            ("3DS Strategy", TDS_OK),
            ("Target Intelligence", INTEL_OK),
            ("Preflight Validator", PREFLIGHT_OK),
            ("Built-in BIN Database", True),
            ("Built-in Luhn Validator", True),
            ("Built-in Card Scoring", True),
        ]
        for name, ok in modules:
            row = QHBoxLayout()
            dot = QLabel("\u25cf")
            dot.setStyleSheet(f"color: {GREEN if ok else RED}; font-size: 10px;")
            dot.setFixedWidth(14)
            row.addWidget(dot)
            row.addWidget(QLabel(name))
            row.addStretch()
            mf.addLayout(row)
        layout.addWidget(mgrp)

        # Result
        self.val_result = QPlainTextEdit()
        self.val_result.setReadOnly(True)
        self.val_result.setMinimumHeight(200)
        self.val_result.setPlaceholderText("Validation results will appear here...")
        layout.addWidget(self.val_result)

        layout.addStretch()
        self.tabs.addTab(scroll, "VALIDATE")

    def _generate_test_card(self):
        network = random.choice(["visa", "mastercard", "amex"])
        card = _generate_test_card(network)
        self.val_card.setText(card)
        exp_m = random.randint(1, 12)
        exp_y = random.randint(26, 29)
        self.val_exp.setText(f"{exp_m:02d}/{exp_y}")
        self.val_cvv.setText(str(random.randint(100, 9999 if network == "amex" else 999)))

    def _batch_validate(self):
        clipboard = QApplication.clipboard()
        text = clipboard.text().strip()
        if not text:
            QMessageBox.warning(self, "Batch", "Clipboard is empty. Copy card numbers (one per line) first.")
            return
        cards = [line.strip().replace(" ", "").replace("-", "") for line in text.splitlines() if line.strip()]
        cards = [c for c in cards if len(c) >= 13 and c.isdigit()]
        if not cards:
            QMessageBox.warning(self, "Batch", "No valid card numbers found in clipboard.")
            return
        results = []
        for card in cards[:50]:
            luhn = _luhn_check(card)
            network = _detect_network(card)
            bin6 = card[:6]
            bin_info = _lookup_bin(bin6)
            score, reasons = _score_card(card, bin_info)
            light = "GREEN" if score >= 70 else "YELLOW" if score >= 45 else "RED"
            bank = bin_info["bank"] if bin_info else "Unknown"
            results.append(f"{card[:6]}...{card[-4:]}  {network:10s}  Luhn:{'PASS' if luhn else 'FAIL'}  Score:{score:3d}  {light:6s}  {bank}")
            self.validation_history.append({
                "card": card[:6] + "...", "bin": bin6, "network": network,
                "luhn": luhn, "score": score, "timestamp": datetime.now().isoformat(),
            })
            row = self.history_table.rowCount()
            self.history_table.insertRow(row)
            self.history_table.setItem(row, 0, QTableWidgetItem(datetime.now().strftime("%H:%M:%S")))
            self.history_table.setItem(row, 1, QTableWidgetItem(bin6))
            self.history_table.setItem(row, 2, QTableWidgetItem(network))
            self.history_table.setItem(row, 3, QTableWidgetItem("PASS" if luhn else "FAIL"))
            self.history_table.setItem(row, 4, QTableWidgetItem(str(score)))
            self.history_table.setItem(row, 5, QTableWidgetItem(self.val_target.currentText()))
        self.val_result.setPlainText(f"=== Batch Validation: {len(results)} cards ===\n\n" + "\n".join(results))
        greens = sum(1 for r in results if "GREEN" in r)
        yellows = sum(1 for r in results if "YELLOW" in r)
        reds = sum(1 for r in results if "RED" in r)
        self.traffic_label.setText(f"BATCH: {greens}G / {yellows}Y / {reds}R")
        if greens > reds:
            self.traffic_light.setStyleSheet(f"color: {GREEN};")
        elif reds > greens:
            self.traffic_light.setStyleSheet(f"color: {RED};")
        else:
            self.traffic_light.setStyleSheet(f"color: {YELLOW};")

    def _build_intel_tab(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(tab)
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        grp = QGroupBox("BIN Intelligence Lookup")
        gf = QVBoxLayout(grp)

        row = QHBoxLayout()
        self.intel_bin = QLineEdit()
        self.intel_bin.setPlaceholderText("Enter BIN (first 6-8 digits)")
        self.intel_bin.setMaxLength(8)
        row.addWidget(self.intel_bin)
        lookup_btn = QPushButton("Lookup")
        lookup_btn.setStyleSheet(f"background: {ACCENT}; color: black; padding: 8px 16px; border-radius: 6px; font-weight: bold;")
        lookup_btn.clicked.connect(self._lookup_bin)
        row.addWidget(lookup_btn)
        gf.addLayout(row)

        self.intel_output = QPlainTextEdit()
        self.intel_output.setReadOnly(True)
        self.intel_output.setMinimumHeight(400)
        self.intel_output.setPlaceholderText("BIN intelligence will appear here...")
        gf.addWidget(self.intel_output)

        layout.addWidget(grp)

        # AVS Pre-Check Panel
        avs_grp = QGroupBox("AVS Pre-Check (Address Verification)")
        avs_layout = QFormLayout(avs_grp)
        self.avs_street = QLineEdit()
        self.avs_street.setPlaceholderText("1234 Oak Street")
        avs_layout.addRow("Billing Street:", self.avs_street)
        self.avs_zip = QLineEdit()
        self.avs_zip.setPlaceholderText("78701")
        self.avs_zip.setMaxLength(10)
        avs_layout.addRow("Billing ZIP:", self.avs_zip)
        self.avs_state = QLineEdit()
        self.avs_state.setPlaceholderText("TX")
        self.avs_state.setMaxLength(2)
        avs_layout.addRow("State:", self.avs_state)
        avs_btn = QPushButton("Check AVS")
        avs_btn.setStyleSheet(f"background: {ACCENT}; color: black; padding: 8px 16px; border-radius: 6px; font-weight: bold;")
        avs_btn.clicked.connect(self._check_avs)
        avs_layout.addRow(avs_btn)
        self.avs_result = QPlainTextEdit()
        self.avs_result.setReadOnly(True)
        self.avs_result.setMaximumHeight(120)
        self.avs_result.setPlaceholderText("AVS result will appear here...")
        avs_layout.addRow(self.avs_result)
        layout.addWidget(avs_grp)

        # Geo Consistency Checker
        geo_grp = QGroupBox("Geo Consistency Check")
        geo_layout = QFormLayout(geo_grp)
        self.geo_state = QLineEdit()
        self.geo_state.setPlaceholderText("TX")
        self.geo_state.setMaxLength(2)
        geo_layout.addRow("Billing State:", self.geo_state)
        self.geo_proxy_state = QLineEdit()
        self.geo_proxy_state.setPlaceholderText("TX (from proxy IP)")
        self.geo_proxy_state.setMaxLength(2)
        geo_layout.addRow("Proxy Exit State:", self.geo_proxy_state)
        self.geo_timezone = QLineEdit()
        self.geo_timezone.setPlaceholderText("America/Chicago")
        geo_layout.addRow("Browser Timezone:", self.geo_timezone)
        geo_btn = QPushButton("Check Geo Consistency")
        geo_btn.setStyleSheet(f"background: {GREEN}; color: black; padding: 8px 16px; border-radius: 6px; font-weight: bold;")
        geo_btn.clicked.connect(self._check_geo)
        geo_layout.addRow(geo_btn)
        self.geo_result = QPlainTextEdit()
        self.geo_result.setReadOnly(True)
        self.geo_result.setMaximumHeight(100)
        self.geo_result.setPlaceholderText("Geo consistency result...")
        geo_layout.addRow(self.geo_result)
        layout.addWidget(geo_grp)

        # Card Cooling Status
        cool_grp = QGroupBox("Card Cooling Status")
        cool_layout = QFormLayout(cool_grp)
        self.cool_bin = QLineEdit()
        self.cool_bin.setPlaceholderText("Enter BIN (first 6 digits)")
        self.cool_bin.setMaxLength(6)
        cool_layout.addRow("Card BIN:", self.cool_bin)
        cool_btn = QPushButton("Check Cooling")
        cool_btn.setStyleSheet(f"background: {ORANGE}; color: black; padding: 8px 16px; border-radius: 6px; font-weight: bold;")
        cool_btn.clicked.connect(self._check_cooling)
        cool_layout.addRow(cool_btn)
        self.cool_result = QPlainTextEdit()
        self.cool_result.setReadOnly(True)
        self.cool_result.setMaximumHeight(100)
        self.cool_result.setPlaceholderText("Card cooling and issuer velocity status...")
        cool_layout.addRow(self.cool_result)
        layout.addWidget(cool_grp)

        # OSINT Cardholder Verification
        osint_grp = QGroupBox("OSINT Cardholder Verification")
        osint_layout = QFormLayout(osint_grp)
        self.osint_name = QLineEdit()
        self.osint_name.setPlaceholderText("John Smith")
        osint_layout.addRow("Cardholder Name:", self.osint_name)
        self.osint_address = QLineEdit()
        self.osint_address.setPlaceholderText("1234 Oak Street")
        osint_layout.addRow("Address:", self.osint_address)
        self.osint_city = QLineEdit()
        self.osint_city.setPlaceholderText("Austin")
        osint_layout.addRow("City:", self.osint_city)
        self.osint_state = QLineEdit()
        self.osint_state.setPlaceholderText("TX")
        self.osint_state.setMaxLength(2)
        osint_layout.addRow("State:", self.osint_state)
        self.osint_zip = QLineEdit()
        self.osint_zip.setPlaceholderText("78701")
        self.osint_zip.setMaxLength(10)
        osint_layout.addRow("ZIP:", self.osint_zip)
        self.osint_phone = QLineEdit()
        self.osint_phone.setPlaceholderText("(555) 123-4567")
        osint_layout.addRow("Phone:", self.osint_phone)
        osint_btn = QPushButton("Generate OSINT Checklist")
        osint_btn.setStyleSheet(f"background: #a855f7; color: white; padding: 8px 16px; border-radius: 6px; font-weight: bold;")
        osint_btn.clicked.connect(self._generate_osint_checklist)
        osint_layout.addRow(osint_btn)
        self.osint_result = QPlainTextEdit()
        self.osint_result.setReadOnly(True)
        self.osint_result.setMaximumHeight(200)
        self.osint_result.setPlaceholderText("OSINT verification checklist will appear here...")
        osint_layout.addRow(self.osint_result)
        layout.addWidget(osint_grp)

        layout.addStretch()
        self.tabs.addTab(scroll, "INTELLIGENCE")

    def _check_avs(self):
        if not ENHANCED_OK:
            self.avs_result.setPlainText("AVS Engine not available (cerberus_enhanced not loaded)")
            return
        try:
            engine = AVSEngine()
            street = self.avs_street.text().strip()
            zip_code = self.avs_zip.text().strip()
            state = self.avs_state.text().strip().upper()
            if not zip_code or not state:
                self.avs_result.setPlainText("Enter ZIP and State to check AVS")
                return
            # Check ZIP-State match
            zip_ok = engine.verify_zip_state(zip_code, state)
            # Normalize address
            normalized = engine.normalize_address(street) if street else "N/A"
            lines = [
                f"ZIP-State Match: {'PASS' if zip_ok else 'FAIL — ZIP does not match state'}",
                f"Normalized Address: {normalized}",
                f"State: {state} | ZIP: {zip_code}",
            ]
            if not zip_ok:
                lines.append("WARNING: Billing ZIP does not match the state — AVS will return N (no match)")
            self.avs_result.setPlainText("\n".join(lines))
        except Exception as e:
            self.avs_result.setPlainText(f"AVS error: {e}")

    def _check_geo(self):
        if not ENHANCED_OK:
            self.geo_result.setPlainText("GeoMatchChecker not available")
            return
        try:
            checker = GeoMatchChecker()
            result = checker.check_geo_consistency(
                billing_state=self.geo_state.text().strip().upper(),
                exit_ip_state=self.geo_proxy_state.text().strip().upper() or None,
                browser_timezone=self.geo_timezone.text().strip() or "America/New_York"
            )
            lines = [f"Geo Score: {result.get('score', 0)}/100"]
            for check, status in result.get("checks", {}).items():
                lines.append(f"  {check}: {'PASS' if status else 'FAIL'}")
            if result.get("recommendation"):
                lines.append(f"\nRecommendation: {result['recommendation']}")
            self.geo_result.setPlainText("\n".join(lines))
        except Exception as e:
            self.geo_result.setPlainText(f"Geo check error: {e}")

    def _check_cooling(self):
        if not COOLING_OK:
            self.cool_result.setPlainText("Card Cooling System not available")
            return
        try:
            cooling = CardCoolingSystem()
            velocity = IssuerVelocityTracker()
            bin6 = self.cool_bin.text().strip()
            if not bin6 or len(bin6) < 6:
                self.cool_result.setPlainText("Enter at least 6 BIN digits")
                return
            # Create a temp card asset for checking
            card = CardAsset(number=bin6 + "0000000000", exp_month=12, exp_year=2027, cvv="000") if CERBERUS_OK else None
            if card:
                cool_ok, wait, heat = cooling.is_cool(card)
                issuer = velocity.get_issuer(bin6)
                can_val, msg = velocity.can_validate(card)
                lines = [
                    f"Card Heat: {heat:.0f}/100 {'(COOL)' if cool_ok else f'(HOT — wait {wait}s)'}",
                    f"Issuer: {issuer}",
                    f"Velocity OK: {can_val} — {msg}",
                ]
                self.cool_result.setPlainText("\n".join(lines))
            else:
                self.cool_result.setPlainText("CerberusValidator not loaded — cannot create card asset")
        except Exception as e:
            self.cool_result.setPlainText(f"Cooling check error: {e}")

    def _generate_osint_checklist(self):
        if not ENHANCED_OK:
            self.osint_result.setPlainText("OSINTVerifier not available (cerberus_enhanced not loaded)")
            return
        try:
            verifier = OSINTVerifier()
            checklist = verifier.generate_verification_checklist(
                name=self.osint_name.text().strip(),
                address=self.osint_address.text().strip(),
                city=self.osint_city.text().strip(),
                state=self.osint_state.text().strip().upper(),
                zip_code=self.osint_zip.text().strip(),
                phone=self.osint_phone.text().strip(),
            )
            lines = ["=== OSINT CARDHOLDER VERIFICATION CHECKLIST ===\n"]
            for source, info in checklist.get("sources", {}).items():
                lines.append(f"[{source.upper()}]")
                if isinstance(info, dict):
                    for k, v in info.items():
                        lines.append(f"  {k}: {v}")
                else:
                    lines.append(f"  {info}")
                lines.append("")
            if checklist.get("checks"):
                lines.append("MANUAL CHECKS:")
                for check in checklist["checks"]:
                    lines.append(f"  [ ] {check}")
            if checklist.get("risk_factors"):
                lines.append("\nRISK FACTORS:")
                for rf in checklist["risk_factors"]:
                    lines.append(f"  ! {rf}")
            self.osint_result.setPlainText("\n".join(lines))
        except Exception as e:
            self.osint_result.setPlainText(f"OSINT error: {e}")

    def _build_history_tab(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(tab)
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        grp = QGroupBox("Validation History")
        gf = QVBoxLayout(grp)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(6)
        self.history_table.setHorizontalHeaderLabels(["Time", "BIN", "Network", "Luhn", "Score", "Target"])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.history_table.setMinimumHeight(400)
        gf.addWidget(self.history_table)

        clear_btn = QPushButton("Clear History")
        clear_btn.setStyleSheet(f"background: {RED}; color: white; padding: 8px 16px; border-radius: 6px;")
        clear_btn.clicked.connect(lambda: (self.validation_history.clear(), self.history_table.setRowCount(0)))
        gf.addWidget(clear_btn)

        layout.addWidget(grp)
        layout.addStretch()
        self.tabs.addTab(scroll, "HISTORY")

    def _validate(self):
        card = self.val_card.text().strip().replace(" ", "").replace("-", "")
        if not card or len(card) < 13:
            self.val_result.setPlainText("Enter a valid card number (13-19 digits)")
            return

        self.validate_btn.setEnabled(False)
        self.validate_btn.setText("Validating...")
        self.val_result.setPlainText("Running validation...")

        exp = self.val_exp.text().strip().replace("/", "")
        cvv = self.val_cvv.text().strip()
        target = self.val_target.currentText()

        self.worker = ValidateWorker(card, exp, cvv, target)
        self.worker.finished.connect(self._on_validate_done)
        self.worker.start()

    def _update_traffic_light(self, score, label_text=None):
        if score >= 70:
            self.traffic_light.setStyleSheet(f"color: {GREEN};")
            self.traffic_label.setText(label_text or "GREEN — GO")
            self.traffic_label.setStyleSheet(f"color: {GREEN}; font-weight: bold;")
        elif score >= 45:
            self.traffic_light.setStyleSheet(f"color: {YELLOW};")
            self.traffic_label.setText(label_text or "YELLOW — CAUTION")
            self.traffic_label.setStyleSheet(f"color: {YELLOW}; font-weight: bold;")
        else:
            self.traffic_light.setStyleSheet(f"color: {RED};")
            self.traffic_label.setText(label_text or "RED — STOP")
            self.traffic_label.setStyleSheet(f"color: {RED}; font-weight: bold;")
        self.traffic_score.setText(f"{score}/100")
        self.traffic_score.setStyleSheet(f"color: {GREEN if score >= 70 else YELLOW if score >= 45 else RED};")

    def _on_validate_done(self, result):
        self.validate_btn.setEnabled(True)
        self.validate_btn.setText("VALIDATE CARD")

        # Built-in scoring
        bin6 = result.get("bin", "")
        bin_info = _lookup_bin(bin6) if bin6 else None
        card_raw = self.val_card.text().strip().replace(" ", "").replace("-", "")
        builtin_score, score_reasons = _score_card(card_raw, bin_info)

        lines = []
        lines.append(f"BIN: {result.get('bin', '?')}")
        lines.append(f"Network: {result.get('network', '?')}")
        lines.append(f"Luhn: {'PASS' if result.get('luhn') else 'FAIL'}")

        if bin_info:
            lines.append(f"\n=== BIN Intelligence ===")
            lines.append(f"Bank: {bin_info.get('bank', '?')}")
            lines.append(f"Type: {bin_info.get('type', '?')}")
            lines.append(f"Level: {bin_info.get('level', '?')}")
            lines.append(f"Country: {bin_info.get('country', '?')}")
            lines.append(f"Risk: {bin_info.get('risk', '?').upper()}")
            if bin_info.get('approximate'):
                lines.append("(approximate match)")
        else:
            lines.append(f"\nBIN not in local database")

        lines.append(f"\n=== Quality Score: {builtin_score}/100 ===")
        for r in score_reasons:
            lines.append(f"  - {r}")

        cerb = result.get("cerberus", {})
        if cerb:
            lines.append(f"\nCerberus: {cerb.get('status', '?')} (score: {cerb.get('score', '?')})")
            if cerb.get("details"):
                lines.append(f"Details: {cerb['details'][:200]}")

        if result.get("bin_score"):
            lines.append(f"\nBIN Score: {result['bin_score']}")
        if result.get("quality_grade"):
            lines.append(f"Quality Grade: {result['quality_grade']}")
        if result.get("tds_strategy"):
            lines.append(f"\n3DS Strategy: {result['tds_strategy'][:200]}")

        if result.get("v83_ai_bin"):
            ai = result["v83_ai_bin"]
            lines.append(f"\n=== AI Analysis ===")
            lines.append(f"AI Score: {ai.get('ai_score', '?')}")
            lines.append(f"Success Prediction: {ai.get('success_prediction', '?')}")
            lines.append(f"Risk Level: {ai.get('risk_level', '?')}")

        self.val_result.setPlainText("\n".join(lines))

        # Update traffic light
        final_score = cerb.get("score", builtin_score) if cerb else builtin_score
        self._update_traffic_light(final_score)

        # Add to history
        self.validation_history.append(result)
        row = self.history_table.rowCount()
        self.history_table.insertRow(row)
        self.history_table.setItem(row, 0, QTableWidgetItem(result.get("timestamp", "")[:19]))
        self.history_table.setItem(row, 1, QTableWidgetItem(result.get("bin", "")))
        self.history_table.setItem(row, 2, QTableWidgetItem(result.get("network", "")))
        self.history_table.setItem(row, 3, QTableWidgetItem("PASS" if result.get("luhn") else "FAIL"))
        self.history_table.setItem(row, 4, QTableWidgetItem(str(final_score)))
        self.history_table.setItem(row, 5, QTableWidgetItem(self.val_target.currentText()))

        # Update session
        if SESSION_OK:
            try:
                update_session(
                    last_bin=result.get("bin", ""),
                    last_validation=result.get("timestamp", ""),
                    last_validation_result=cerb.get("status", ""),
                )
            except Exception:
                pass

    def _lookup_bin(self):
        bin_val = self.intel_bin.text().strip()
        if not bin_val or len(bin_val) < 6:
            self.intel_output.setPlainText("Enter at least 6 digits")
            return

        bin6 = bin_val[:6]
        lines = [f"=== BIN Intelligence: {bin6} ===\n"]

        # Built-in lookup (always available)
        builtin = _lookup_bin(bin6)
        if builtin:
            lines.append("--- Built-in Database ---")
            lines.append(f"  Bank:    {builtin.get('bank', '?')}")
            lines.append(f"  Network: {builtin.get('network', '?')}")
            lines.append(f"  Type:    {builtin.get('type', '?')}")
            lines.append(f"  Level:   {builtin.get('level', '?')}")
            lines.append(f"  Country: {builtin.get('country', '?')}")
            lines.append(f"  Risk:    {builtin.get('risk', '?').upper()}")
            if builtin.get('approximate'):
                lines.append("  (approximate match)")

            # Generate a test card for this BIN and score it
            test_card = bin6 + "".join(str(random.randint(0, 9)) for _ in range(9))
            digits = [int(d) for d in test_card]
            odd = sum(digits[-1::-2])
            even = sum(sum(divmod(2 * d, 10)) for d in digits[-2::-2])
            check = (10 - (odd + even) % 10) % 10
            test_card += str(check)
            score, reasons = _score_card(test_card, builtin)
            lines.append(f"\n--- Quality Assessment ---")
            lines.append(f"  Score: {score}/100")
            for r in reasons:
                lines.append(f"    - {r}")

            # Traffic light recommendation
            if score >= 70:
                lines.append(f"\n  RECOMMENDATION: GREEN — Good for operations")
            elif score >= 45:
                lines.append(f"\n  RECOMMENDATION: YELLOW — Use with caution")
            else:
                lines.append(f"\n  RECOMMENDATION: RED — Avoid")
        else:
            network = _detect_network(bin6)
            lines.append(f"  Network: {network}")
            lines.append(f"  BIN {bin6} not in local database ({len(_BIN_DB)} entries)")
            lines.append(f"  Try enhanced modules for online BIN lookup")

        # Enhanced modules (if available)
        if ENHANCED_OK:
            lines.append("\n--- Enhanced Module ---")
            try:
                scorer = BINScoringEngine()
                score = scorer.score(bin_val)
                lines.append(f"  BIN Score: {score}")
            except Exception as e:
                lines.append(f"  BIN Score: error — {e}")

            try:
                grader = CardQualityGrader()
                grade = grader.grade(bin_val + "0000000000")
                lines.append(f"  Quality Grade: {grade}")
            except Exception:
                pass

        if TDS_OK:
            lines.append("\n--- 3DS Strategy ---")
            try:
                strategy = get_3ds_strategy(bin_val)
                lines.append(f"  {strategy}")
            except Exception as e:
                lines.append(f"  3DS: {e}")

        if INTEL_OK:
            try:
                intel = get_target_intel(bin_val)
                lines.append(f"\n--- Target Intel ---\n{json.dumps(intel, indent=2, default=str)[:500]}")
            except Exception:
                pass

        if AI_V83_OK:
            lines.append("\n--- AI Deep Analysis ---")
            try:
                ai_bin = analyze_bin(bin6)
                lines.append(f"  AI Score: {ai_bin.ai_score}")
                lines.append(f"  Prediction: {ai_bin.success_prediction}")
                lines.append(f"  Best Targets: {', '.join(ai_bin.best_targets[:3])}")
            except Exception:
                lines.append("  AI analysis unavailable")

        self.intel_output.setPlainText("\n".join(lines))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = TitanCardValidator()
    win.show()
    sys.exit(app.exec())
