#!/usr/bin/env python3
"""
TITAN V9.2 SINGULARITY — Cerberus AppX V2
============================================
Desktop application for payment validation & orchestration.
7 tabs:
  1. VALIDATE — Single card validation with Hyperswitch + direct PSP fallback
  2. BATCH — Bulk card processing with live streaming results
  3. ROUTING — Hyperswitch intelligent routing dashboard
  4. VAULT — PCI-compliant card vault management
  5. ANALYTICS — Per-connector performance, decline heatmap, revenue recovery
  6. INTELLIGENCE — BIN scoring, OSINT, AVS, pattern predictor, drain planner
  7. CONNECTORS — Manage PSP connectors, API keys, test connectivity

Architecture:
  PyQt6 GUI → Hyperswitch (50+ connectors) → Stripe/Braintree/Adyen/+47 more
  Fallback: Direct PSP validation when Hyperswitch is offline
  API: Cerberus Bridge API on port 36300
"""

import sys
import os
import re
import json
import asyncio
import csv
import io
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any

sys.path.insert(0, str(Path(__file__).parent.parent / "core"))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QGroupBox, QFormLayout,
    QTabWidget, QComboBox, QMessageBox, QScrollArea, QPlainTextEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar,
    QFileDialog, QSpinBox, QCheckBox, QFrame, QSplitter, QDoubleSpinBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor

# ═══════════════════════════════════════════════════════════════════════════════
# THEME
# ═══════════════════════════════════════════════════════════════════════════════

ACCENT = "#ef4444"      # Cerberus red
ACCENT2 = "#f97316"     # Orange accent
BG = "#0a0e17"
BG_CARD = "#111827"
BG_INPUT = "#1e293b"
TEXT = "#e2e8f0"
TEXT2 = "#64748b"
GREEN = "#22c55e"
YELLOW = "#eab308"
RED = "#ef4444"
ORANGE = "#f97316"
BORDER = "#1e293b"

try:
    from titan_theme import apply_titan_theme, make_tab_style
    THEME_OK = True
except ImportError:
    THEME_OK = False

# ═══════════════════════════════════════════════════════════════════════════════
# CORE IMPORTS (graceful degradation)
# ═══════════════════════════════════════════════════════════════════════════════

try:
    from cerberus_core import (
        CerberusValidator, BulkValidator, CardAsset, CardStatus,
        CardType, MerchantKey, ValidationResult,
        CardCoolingSystem, IssuerVelocityTracker, CrossPSPCorrelator,
        get_osint_checklist, get_card_quality_guide, get_bank_enrollment_guide,
        CARD_QUALITY_INDICATORS, CARD_LEVEL_COMPATIBILITY
    )
    CERBERUS_CORE = True
except ImportError:
    CERBERUS_CORE = False

try:
    from cerberus_enhanced import (
        AVSEngine, BINScoringEngine, BINScore,
        AVSResult, AVSCheckResult
    )
    CERBERUS_ENHANCED = True
except ImportError:
    CERBERUS_ENHANCED = False

try:
    from ai_intelligence_engine import AIIntelligenceEngine
    AI_ENGINE = True
except ImportError:
    AI_ENGINE = False

try:
    from cerberus_hyperswitch import (
        HyperswitchClient, HyperswitchRouter, HyperswitchVault,
        HyperswitchRetry, HyperswitchAnalytics,
        get_hyperswitch_client, get_hyperswitch_router,
        get_hyperswitch_vault, get_hyperswitch_retry,
        get_hyperswitch_analytics, is_hyperswitch_available,
        PaymentStatus, RoutingAlgorithm, ConnectorStatus,
    )
    HYPERSWITCH_OK = is_hyperswitch_available()
except ImportError:
    HYPERSWITCH_OK = False

# ═══════════════════════════════════════════════════════════════════════════════
# BUILT-IN BIN DATABASE (works without core modules)
# ═══════════════════════════════════════════════════════════════════════════════

_BUILTIN_BIN_DB = {
    "453201": {"bank": "Chase", "type": "Credit", "level": "Signature", "country": "US", "network": "VISA", "risk": "low"},
    "455600": {"bank": "Bank of America", "type": "Credit", "level": "Platinum", "country": "US", "network": "VISA", "risk": "low"},
    "491656": {"bank": "Chase", "type": "Debit", "level": "Classic", "country": "US", "network": "VISA", "risk": "medium"},
    "471600": {"bank": "Capital One", "type": "Credit", "level": "World", "country": "US", "network": "VISA", "risk": "low"},
    "492910": {"bank": "Wells Fargo", "type": "Credit", "level": "Signature", "country": "US", "network": "VISA", "risk": "low"},
    "400011": {"bank": "Citi", "type": "Credit", "level": "World Elite", "country": "US", "network": "VISA", "risk": "low"},
    "414720": {"bank": "USAA", "type": "Credit", "level": "Signature", "country": "US", "network": "VISA", "risk": "low"},
    "542598": {"bank": "Chase", "type": "Credit", "level": "World Elite", "country": "US", "network": "MASTERCARD", "risk": "low"},
    "539900": {"bank": "Citi", "type": "Credit", "level": "World", "country": "US", "network": "MASTERCARD", "risk": "low"},
    "516805": {"bank": "Capital One", "type": "Credit", "level": "Platinum", "country": "US", "network": "MASTERCARD", "risk": "low"},
    "549580": {"bank": "Bank of America", "type": "Credit", "level": "World", "country": "US", "network": "MASTERCARD", "risk": "low"},
    "378282": {"bank": "Amex", "type": "Credit", "level": "Gold", "country": "US", "network": "AMEX", "risk": "low"},
    "371449": {"bank": "Amex", "type": "Credit", "level": "Platinum", "country": "US", "network": "AMEX", "risk": "low"},
    "601100": {"bank": "Discover", "type": "Credit", "level": "Standard", "country": "US", "network": "DISCOVER", "risk": "medium"},
    "476173": {"bank": "TD Bank", "type": "Debit", "level": "Classic", "country": "US", "network": "VISA", "risk": "high"},
    "411111": {"bank": "Test/Generic", "type": "Credit", "level": "Classic", "country": "US", "network": "VISA", "risk": "high"},
    "555555": {"bank": "Test/Generic", "type": "Credit", "level": "Standard", "country": "US", "network": "MASTERCARD", "risk": "high"},
}


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
    elif card[:4] == "6011" or card[:3] in ("644", "645") or card[:2] == "65":
        return "DISCOVER"
    return "UNKNOWN"


# ═══════════════════════════════════════════════════════════════════════════════
# MERCHANT KEY STORAGE
# ═══════════════════════════════════════════════════════════════════════════════

CERBERUS_CONFIG_DIR = Path(os.path.expanduser("~/.cerberus_appx"))
KEYS_FILE = CERBERUS_CONFIG_DIR / "keys.json"
HISTORY_FILE = CERBERUS_CONFIG_DIR / "history.json"
INTELLIGENCE_FILE = CERBERUS_CONFIG_DIR / "intelligence.json"


def _load_keys() -> Dict[str, List[Dict]]:
    if KEYS_FILE.exists():
        try:
            return json.loads(KEYS_FILE.read_text())
        except Exception:
            pass
    return {"stripe": [], "braintree": [], "adyen": []}


def _save_keys(keys: Dict):
    CERBERUS_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    KEYS_FILE.write_text(json.dumps(keys, indent=2))


def _load_history() -> List[Dict]:
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text())
        except Exception:
            pass
    return []


def _save_history(history: List[Dict]):
    CERBERUS_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    # Keep last 10000 entries
    HISTORY_FILE.write_text(json.dumps(history[-10000:], indent=2))


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATE WORKER (async card validation in background thread)
# ═══════════════════════════════════════════════════════════════════════════════

class ValidateWorker(QThread):
    """Background worker for single card validation"""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, card_data: str, provider: str, keys: Dict):
        super().__init__()
        self.card_data = card_data
        self.provider = provider
        self.keys = keys

    def run(self):
        try:
            if CERBERUS_CORE:
                result = self._validate_with_core()
            else:
                result = self._validate_builtin()
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))

    def _validate_with_core(self) -> Dict:
        """Validate using cerberus_core.py engine"""
        validator = CerberusValidator()

        # Add merchant keys
        for provider, key_list in self.keys.items():
            for k in key_list:
                if k.get("public_key") and k.get("secret_key"):
                    validator.add_key(MerchantKey(
                        provider=provider,
                        public_key=k["public_key"],
                        secret_key=k["secret_key"],
                        merchant_id=k.get("merchant_id"),
                        is_live=k.get("is_live", True)
                    ))

        card = validator.parse_card_input(self.card_data)
        if not card:
            return {
                "status": "ERROR",
                "message": "Could not parse card input",
                "traffic_light": "⚪"
            }

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(validator.validate(card))
            display = CerberusValidator.format_result_for_display(result)
            return display
        finally:
            loop.close()

    def _validate_builtin(self) -> Dict:
        """Validate using built-in checks (no core module)"""
        cleaned = re.sub(r'\D', '', self.card_data.split('|')[0] if '|' in self.card_data else self.card_data.split()[0])

        if not cleaned or len(cleaned) < 13:
            return {"status": "ERROR", "message": "Invalid card number", "traffic_light": "⚪"}

        luhn_ok = _luhn_check(cleaned)
        network = _detect_network(cleaned)
        bin6 = cleaned[:6]
        bin_info = _BUILTIN_BIN_DB.get(bin6, {})

        if not luhn_ok:
            return {
                "status": "DEAD", "traffic_light": "🔴",
                "message": "Invalid card number (Luhn check failed)",
                "card": f"{bin6}******{cleaned[-4:]}",
                "card_type": network, "bank": "Unknown", "country": "Unknown"
            }

        status = "UNKNOWN"
        light = "🟡"
        msg = "BIN lookup only — add merchant API keys for live validation"

        if bin_info:
            if bin_info.get("risk") == "high":
                status = "RISKY"
                light = "🟠"
                msg = f"High-risk BIN detected ({bin_info.get('bank', 'Unknown')})"
            else:
                msg = f"BIN valid: {bin_info.get('bank', '?')} {bin_info.get('level', '?')} ({bin_info.get('country', '?')})"

        return {
            "status": status, "traffic_light": light, "message": msg,
            "card": f"{bin6}******{cleaned[-4:]}", "card_type": network,
            "bank": bin_info.get("bank", "Unknown"),
            "country": bin_info.get("country", "Unknown"),
            "risk_score": {"low": 20, "medium": 50, "high": 80}.get(bin_info.get("risk", "medium"), 50),
            "bin_info": bin_info
        }


# ═══════════════════════════════════════════════════════════════════════════════
# BATCH WORKER (validates list of cards)
# ═══════════════════════════════════════════════════════════════════════════════

class BatchWorker(QThread):
    """Background worker for batch card validation"""
    progress = pyqtSignal(int, int, dict)   # current, total, result
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, card_lines: List[str], provider: str, keys: Dict,
                 rate_limit: float = 1.0):
        super().__init__()
        self.card_lines = card_lines
        self.provider = provider
        self.keys = keys
        self.rate_limit = rate_limit
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        try:
            results = []
            total = len(self.card_lines)

            if CERBERUS_CORE:
                validator = CerberusValidator()
                for provider, key_list in self.keys.items():
                    for k in key_list:
                        if k.get("public_key") and k.get("secret_key"):
                            validator.add_key(MerchantKey(
                                provider=provider,
                                public_key=k["public_key"],
                                secret_key=k["secret_key"],
                                merchant_id=k.get("merchant_id"),
                                is_live=k.get("is_live", True)
                            ))

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    for i, line in enumerate(self.card_lines):
                        if self._stop:
                            break
                        line = line.strip()
                        if not line:
                            continue
                        card = validator.parse_card_input(line)
                        if card:
                            result = loop.run_until_complete(validator.validate(card))
                            display = CerberusValidator.format_result_for_display(result)
                        else:
                            display = {"status": "ERROR", "message": "Parse failed", "traffic_light": "⚪", "card": line[:20]}
                        results.append(display)
                        self.progress.emit(i + 1, total, display)
                        if i < total - 1:
                            import time
                            time.sleep(self.rate_limit)
                finally:
                    loop.close()
            else:
                # Built-in validation (BIN check only)
                for i, line in enumerate(self.card_lines):
                    if self._stop:
                        break
                    line = line.strip()
                    if not line:
                        continue
                    worker = ValidateWorker(line, self.provider, self.keys)
                    display = worker._validate_builtin()
                    results.append(display)
                    self.progress.emit(i + 1, total, display)

            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN WINDOW
# ═══════════════════════════════════════════════════════════════════════════════

class CerberusApp(QMainWindow):
    """Cerberus AppX V2 — Payment Validation & Orchestration Platform"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cerberus AppX V2 — Payment Orchestration Intelligence")
        self.setMinimumSize(1200, 800)
        self.merchant_keys = _load_keys()
        self.validation_history = _load_history()
        self.cooling_system = CardCoolingSystem() if CERBERUS_CORE else None
        self.velocity_tracker = IssuerVelocityTracker() if CERBERUS_CORE else None
        self.psp_correlator = CrossPSPCorrelator() if CERBERUS_CORE else None
        self.avs_engine = AVSEngine() if CERBERUS_ENHANCED else None
        self.bin_scorer = BINScoringEngine() if CERBERUS_ENHANCED else None
        # V2: Hyperswitch components
        self.hs_client = None
        self.hs_router = None
        self.hs_vault = None
        self.hs_retry = None
        self.hs_analytics = None
        if HYPERSWITCH_OK:
            try:
                self.hs_client = get_hyperswitch_client()
                self.hs_router = get_hyperswitch_router()
                self.hs_vault = get_hyperswitch_vault()
                self.hs_retry = get_hyperswitch_retry()
                self.hs_analytics = get_hyperswitch_analytics()
            except Exception:
                pass
        self._worker = None
        self._batch_worker = None
        self._init_ui()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QWidget()
        header.setFixedHeight(56)
        header.setStyleSheet(f"background: {BG_CARD}; border-bottom: 1px solid {BORDER};")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(16, 0, 16, 0)

        title = QLabel("CERBERUS AppX V2")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {ACCENT}; background: transparent;")
        hl.addWidget(title)

        subtitle = QLabel("Payment Orchestration Intelligence")
        subtitle.setStyleSheet(f"color: {TEXT2}; background: transparent; font-size: 12px;")
        hl.addWidget(subtitle)
        hl.addStretch()

        # Status indicators
        hs_label = QLabel(f"Hyperswitch: {'✓' if HYPERSWITCH_OK else '✗'}")
        hs_label.setStyleSheet(f"color: {GREEN if HYPERSWITCH_OK else ORANGE}; background: transparent; font-size: 11px; font-weight: bold;")
        hl.addWidget(hs_label)

        core_label = QLabel(f"Core: {'✓' if CERBERUS_CORE else '✗'}")
        core_label.setStyleSheet(f"color: {GREEN if CERBERUS_CORE else RED}; background: transparent; font-size: 11px;")
        hl.addWidget(core_label)

        enhanced_label = QLabel(f"Enhanced: {'✓' if CERBERUS_ENHANCED else '✗'}")
        enhanced_label.setStyleSheet(f"color: {GREEN if CERBERUS_ENHANCED else RED}; background: transparent; font-size: 11px;")
        hl.addWidget(enhanced_label)

        ai_label = QLabel(f"AI: {'✓' if AI_ENGINE else '✗'}")
        ai_label.setStyleSheet(f"color: {GREEN if AI_ENGINE else RED}; background: transparent; font-size: 11px;")
        hl.addWidget(ai_label)

        layout.addWidget(header)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: none; background: {BG}; }}
            QTabBar::tab {{
                background: {BG_CARD}; color: {TEXT2}; padding: 10px 24px;
                border: none; border-bottom: 2px solid transparent;
                font-size: 12px; font-weight: bold;
            }}
            QTabBar::tab:selected {{
                color: {ACCENT}; border-bottom: 2px solid {ACCENT};
            }}
            QTabBar::tab:hover {{ color: {TEXT}; }}
        """)

        self.tabs.addTab(self._build_validate_tab(), "VALIDATE")
        self.tabs.addTab(self._build_batch_tab(), "BATCH")
        self.tabs.addTab(self._build_routing_tab(), "ROUTING")
        self.tabs.addTab(self._build_vault_tab(), "VAULT")
        self.tabs.addTab(self._build_analytics_tab(), "ANALYTICS")
        self.tabs.addTab(self._build_intelligence_tab(), "INTELLIGENCE")
        self.tabs.addTab(self._build_connectors_tab(), "CONNECTORS")

        layout.addWidget(self.tabs)

        # Apply global stylesheet
        self.setStyleSheet(f"""
            QMainWindow {{ background: {BG}; }}
            QWidget {{ background: {BG}; color: {TEXT}; }}
            QGroupBox {{
                background: {BG_CARD}; border: 1px solid {BORDER};
                border-radius: 8px; margin-top: 12px; padding: 16px; padding-top: 28px;
                font-weight: bold; color: {TEXT};
            }}
            QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 6px; color: {ACCENT}; }}
            QLineEdit, QPlainTextEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
                background: {BG_INPUT}; border: 1px solid {BORDER}; border-radius: 4px;
                padding: 6px 10px; color: {TEXT}; font-size: 13px;
            }}
            QLineEdit:focus, QPlainTextEdit:focus {{
                border: 1px solid {ACCENT};
            }}
            QPushButton {{
                background: {ACCENT}; color: white; border: none; border-radius: 4px;
                padding: 8px 20px; font-weight: bold; font-size: 12px;
            }}
            QPushButton:hover {{ background: #dc2626; }}
            QPushButton:disabled {{ background: {BG_INPUT}; color: {TEXT2}; }}
            QTableWidget {{
                background: {BG_CARD}; gridline-color: {BORDER};
                border: 1px solid {BORDER}; border-radius: 4px;
            }}
            QTableWidget::item {{ padding: 4px 8px; }}
            QHeaderView::section {{
                background: {BG_INPUT}; color: {TEXT2}; border: none;
                padding: 6px 8px; font-weight: bold; font-size: 11px;
            }}
            QProgressBar {{
                background: {BG_INPUT}; border: 1px solid {BORDER}; border-radius: 4px;
                text-align: center; color: {TEXT}; height: 20px;
            }}
            QProgressBar::chunk {{ background: {ACCENT}; border-radius: 3px; }}
            QScrollBar:vertical {{
                background: {BG}; width: 8px; margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {BORDER}; border-radius: 4px; min-height: 20px;
            }}
        """)

    # ───────────────────────────────────────────────────────────────────────
    # TAB 1: VALIDATE
    # ───────────────────────────────────────────────────────────────────────

    def _build_validate_tab(self) -> QWidget:
        w = QWidget()
        layout = QHBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Left panel: Card input
        left = QVBoxLayout()

        # Card input group
        card_grp = QGroupBox("Card Input")
        card_layout = QVBoxLayout(card_grp)

        lbl = QLabel("Enter card data (formats: PAN|MM|YY|CVV or PAN MM YY CVV):")
        lbl.setStyleSheet(f"color: {TEXT2}; font-size: 11px; background: transparent;")
        card_layout.addWidget(lbl)

        self.card_input = QLineEdit()
        self.card_input.setPlaceholderText("4242424242424242|12|25|123")
        self.card_input.setFont(QFont("Consolas", 14))
        self.card_input.setFixedHeight(44)
        self.card_input.returnPressed.connect(self._on_validate)
        card_layout.addWidget(self.card_input)

        # Provider selector
        prov_layout = QHBoxLayout()
        prov_layout.addWidget(QLabel("Gateway:"))
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["Auto (Hyperswitch + PSP)", "Hyperswitch Only", "Stripe", "Braintree", "Adyen"])
        prov_layout.addWidget(self.provider_combo)
        prov_layout.addStretch()
        card_layout.addLayout(prov_layout)

        # Validate button
        btn_layout = QHBoxLayout()
        self.validate_btn = QPushButton("VALIDATE CARD")
        self.validate_btn.setFixedHeight(44)
        self.validate_btn.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.validate_btn.clicked.connect(self._on_validate)
        btn_layout.addWidget(self.validate_btn)

        self.clear_btn = QPushButton("CLEAR")
        self.clear_btn.setFixedHeight(44)
        self.clear_btn.setStyleSheet(f"background: {BG_INPUT}; color: {TEXT};")
        self.clear_btn.clicked.connect(self._on_clear)
        btn_layout.addWidget(self.clear_btn)
        card_layout.addLayout(btn_layout)

        left.addWidget(card_grp)

        # Result panel
        result_grp = QGroupBox("Result")
        result_layout = QVBoxLayout(result_grp)

        # Traffic light display
        self.traffic_light = QLabel("⚪")
        self.traffic_light.setFont(QFont("Segoe UI", 64))
        self.traffic_light.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.traffic_light.setStyleSheet("background: transparent;")
        result_layout.addWidget(self.traffic_light)

        self.status_label = QLabel("Ready")
        self.status_label.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet(f"color: {TEXT2}; background: transparent;")
        result_layout.addWidget(self.status_label)

        self.message_label = QLabel("Enter a card number to validate")
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message_label.setWordWrap(True)
        self.message_label.setStyleSheet(f"color: {TEXT2}; background: transparent; font-size: 12px;")
        result_layout.addWidget(self.message_label)

        left.addWidget(result_grp)
        left.addStretch()

        # Right panel: Details
        right = QVBoxLayout()

        detail_grp = QGroupBox("Validation Details")
        detail_layout = QFormLayout(detail_grp)
        detail_layout.setSpacing(8)

        self.det_card = QLabel("—")
        self.det_network = QLabel("—")
        self.det_bank = QLabel("—")
        self.det_country = QLabel("—")
        self.det_risk = QLabel("—")
        self.det_gateways = QLabel("—")
        self.det_decline = QLabel("—")
        self.det_action = QLabel("—")
        self.det_bypass = QLabel("—")

        for lbl_obj in [self.det_card, self.det_network, self.det_bank, self.det_country,
                        self.det_risk, self.det_gateways, self.det_decline, self.det_action, self.det_bypass]:
            lbl_obj.setStyleSheet(f"color: {TEXT}; background: transparent; font-size: 12px;")
            lbl_obj.setWordWrap(True)

        detail_layout.addRow(self._form_label("Card:"), self.det_card)
        detail_layout.addRow(self._form_label("Network:"), self.det_network)
        detail_layout.addRow(self._form_label("Bank:"), self.det_bank)
        detail_layout.addRow(self._form_label("Country:"), self.det_country)
        detail_layout.addRow(self._form_label("Risk Score:"), self.det_risk)
        detail_layout.addRow(self._form_label("Gateways:"), self.det_gateways)
        detail_layout.addRow(self._form_label("Decline:"), self.det_decline)
        detail_layout.addRow(self._form_label("Action:"), self.det_action)
        detail_layout.addRow(self._form_label("3DS Bypass:"), self.det_bypass)

        right.addWidget(detail_grp)

        # Cooling / velocity info
        intel_grp = QGroupBox("Card Intelligence")
        intel_layout = QVBoxLayout(intel_grp)
        self.intel_text = QPlainTextEdit()
        self.intel_text.setReadOnly(True)
        self.intel_text.setMaximumHeight(200)
        self.intel_text.setStyleSheet(f"font-family: Consolas; font-size: 11px; background: {BG_INPUT};")
        intel_layout.addWidget(self.intel_text)
        right.addWidget(intel_grp)

        right.addStretch()

        layout.addLayout(left, 1)
        layout.addLayout(right, 1)
        return w

    def _form_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {TEXT2}; background: transparent; font-size: 12px; font-weight: bold;")
        return lbl

    def _on_validate(self):
        card_data = self.card_input.text().strip()
        if not card_data:
            return

        self.validate_btn.setEnabled(False)
        self.validate_btn.setText("Validating...")
        self.traffic_light.setText("⏳")
        self.status_label.setText("Validating...")
        self.status_label.setStyleSheet(f"color: {YELLOW}; background: transparent;")
        self.message_label.setText("Checking card against payment gateways...")

        provider = self.provider_combo.currentText().split()[0].lower()
        if provider == "auto":
            provider = "stripe"

        self._worker = ValidateWorker(card_data, provider, self.merchant_keys)
        self._worker.finished.connect(self._on_validate_result)
        self._worker.error.connect(self._on_validate_error)
        self._worker.start()

    def _on_validate_result(self, result: Dict):
        self.validate_btn.setEnabled(True)
        self.validate_btn.setText("VALIDATE CARD")

        status = result.get("status", "UNKNOWN")
        light = result.get("traffic_light", "⚪")

        self.traffic_light.setText(light)
        self.status_label.setText(status)

        color_map = {"LIVE": GREEN, "DEAD": RED, "UNKNOWN": YELLOW, "RISKY": ORANGE}
        self.status_label.setStyleSheet(f"color: {color_map.get(status, TEXT2)}; background: transparent;")
        self.message_label.setText(result.get("message", ""))

        # Populate details
        self.det_card.setText(result.get("card", "—"))
        self.det_network.setText(result.get("card_type", "—"))
        self.det_bank.setText(result.get("bank", "—"))
        self.det_country.setText(result.get("country", "—"))

        risk = result.get("risk_score")
        if risk is not None:
            risk_color = GREEN if risk <= 30 else (YELLOW if risk <= 60 else RED)
            self.det_risk.setText(f"{risk}/100")
            self.det_risk.setStyleSheet(f"color: {risk_color}; background: transparent; font-size: 12px;")
        else:
            self.det_risk.setText("—")

        gateways = result.get("gateways_tried", [])
        self.det_gateways.setText(", ".join(gateways) if gateways else "BIN lookup only")

        self.det_decline.setText(result.get("decline_reason", "—"))
        self.det_action.setText(result.get("retry_advice", result.get("decline_action", "—")))

        bypass = result.get("bypass_plan")
        if bypass:
            self.det_bypass.setText(f"Score: {bypass.get('bypass_score', '?')}/100")
        else:
            self.det_bypass.setText("—")

        # Intelligence panel
        intel_lines = []
        if result.get("bin_info"):
            bi = result["bin_info"]
            intel_lines.append(f"BIN: {bi.get('bank', '?')} | {bi.get('type', '?')} | {bi.get('level', '?')}")
            intel_lines.append(f"Country: {bi.get('country', '?')} | Network: {bi.get('network', '?')}")
            intel_lines.append(f"Risk: {bi.get('risk', '?')}")
        if result.get("decline_category"):
            intel_lines.append(f"\nDecline Category: {result['decline_category']}")
            intel_lines.append(f"Severity: {result.get('decline_severity', '?')}")
            intel_lines.append(f"Recoverable: {'Yes' if result.get('is_recoverable') else 'No'}")
        self.intel_text.setPlainText("\n".join(intel_lines) if intel_lines else "No additional intelligence")

        # Save to history
        result["timestamp"] = datetime.now().isoformat()
        self.validation_history.append(result)
        _save_history(self.validation_history)

    def _on_validate_error(self, err: str):
        self.validate_btn.setEnabled(True)
        self.validate_btn.setText("VALIDATE CARD")
        self.traffic_light.setText("⚪")
        self.status_label.setText("ERROR")
        self.status_label.setStyleSheet(f"color: {RED}; background: transparent;")
        self.message_label.setText(f"Validation error: {err}")

    def _on_clear(self):
        self.card_input.clear()
        self.traffic_light.setText("⚪")
        self.status_label.setText("Ready")
        self.status_label.setStyleSheet(f"color: {TEXT2}; background: transparent;")
        self.message_label.setText("Enter a card number to validate")
        for lbl in [self.det_card, self.det_network, self.det_bank, self.det_country,
                    self.det_risk, self.det_gateways, self.det_decline, self.det_action, self.det_bypass]:
            lbl.setText("—")
        self.intel_text.clear()

    # ───────────────────────────────────────────────────────────────────────
    # TAB 2: BATCH
    # ───────────────────────────────────────────────────────────────────────

    def _build_batch_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Controls
        ctrl_layout = QHBoxLayout()

        self.batch_import_btn = QPushButton("Import Cards (TXT/CSV)")
        self.batch_import_btn.clicked.connect(self._on_batch_import)
        ctrl_layout.addWidget(self.batch_import_btn)

        ctrl_layout.addWidget(QLabel("Rate Limit (sec):"))
        self.rate_limit_spin = QDoubleSpinBox()
        self.rate_limit_spin.setRange(0.1, 60.0)
        self.rate_limit_spin.setValue(1.0)
        self.rate_limit_spin.setSingleStep(0.5)
        ctrl_layout.addWidget(self.rate_limit_spin)

        self.batch_start_btn = QPushButton("START BATCH")
        self.batch_start_btn.setStyleSheet(f"background: {GREEN};")
        self.batch_start_btn.clicked.connect(self._on_batch_start)
        ctrl_layout.addWidget(self.batch_start_btn)

        self.batch_stop_btn = QPushButton("STOP")
        self.batch_stop_btn.setStyleSheet(f"background: {RED};")
        self.batch_stop_btn.setEnabled(False)
        self.batch_stop_btn.clicked.connect(self._on_batch_stop)
        ctrl_layout.addWidget(self.batch_stop_btn)

        self.batch_export_btn = QPushButton("Export Results")
        self.batch_export_btn.clicked.connect(self._on_batch_export)
        ctrl_layout.addWidget(self.batch_export_btn)

        ctrl_layout.addStretch()
        layout.addLayout(ctrl_layout)

        # Card list input
        input_grp = QGroupBox("Card List (one per line — PAN|MM|YY|CVV)")
        input_layout = QVBoxLayout(input_grp)
        self.batch_input = QPlainTextEdit()
        self.batch_input.setPlaceholderText("4242424242424242|12|25|123\n5555555555554444|10|26|456\n371449635398431|08|27|1234")
        self.batch_input.setMaximumHeight(150)
        self.batch_input.setStyleSheet(f"font-family: Consolas; font-size: 12px; background: {BG_INPUT};")
        input_layout.addWidget(self.batch_input)
        layout.addWidget(input_grp)

        # Progress
        prog_layout = QHBoxLayout()
        self.batch_progress = QProgressBar()
        self.batch_progress.setValue(0)
        prog_layout.addWidget(self.batch_progress)

        self.batch_stats = QLabel("0/0 — Live: 0 | Dead: 0 | Unknown: 0")
        self.batch_stats.setStyleSheet(f"color: {TEXT2}; background: transparent; font-size: 11px;")
        prog_layout.addWidget(self.batch_stats)
        layout.addLayout(prog_layout)

        # Results table
        self.batch_table = QTableWidget(0, 7)
        self.batch_table.setHorizontalHeaderLabels(["#", "Status", "Card", "Network", "Bank", "Country", "Message"])
        self.batch_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.batch_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.batch_table.setColumnWidth(0, 40)
        self.batch_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.batch_table.setColumnWidth(1, 80)
        self.batch_table.verticalHeader().setVisible(False)
        self.batch_table.setAlternatingRowColors(True)
        self.batch_table.setStyleSheet(f"""
            QTableWidget {{ alternate-background-color: {BG_INPUT}; }}
        """)
        layout.addWidget(self.batch_table)

        self._batch_results = []
        self._batch_live = 0
        self._batch_dead = 0
        self._batch_unknown = 0

        return w

    def _on_batch_import(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import Card List", "", "Text Files (*.txt *.csv);;All Files (*)")
        if path:
            try:
                with open(path, "r") as f:
                    content = f.read()
                self.batch_input.setPlainText(content)
            except Exception as e:
                QMessageBox.warning(self, "Import Error", str(e))

    def _on_batch_start(self):
        text = self.batch_input.toPlainText().strip()
        if not text:
            return

        lines = [l for l in text.splitlines() if l.strip()]
        if not lines:
            return

        self.batch_table.setRowCount(0)
        self._batch_results = []
        self._batch_live = 0
        self._batch_dead = 0
        self._batch_unknown = 0
        self.batch_progress.setMaximum(len(lines))
        self.batch_progress.setValue(0)

        self.batch_start_btn.setEnabled(False)
        self.batch_stop_btn.setEnabled(True)

        provider = self.provider_combo.currentText().split()[0].lower()
        self._batch_worker = BatchWorker(
            lines, provider, self.merchant_keys,
            rate_limit=self.rate_limit_spin.value()
        )
        self._batch_worker.progress.connect(self._on_batch_progress)
        self._batch_worker.finished.connect(self._on_batch_finished)
        self._batch_worker.error.connect(self._on_batch_error)
        self._batch_worker.start()

    def _on_batch_stop(self):
        if self._batch_worker:
            self._batch_worker.stop()
        self.batch_start_btn.setEnabled(True)
        self.batch_stop_btn.setEnabled(False)

    def _on_batch_progress(self, current: int, total: int, result: Dict):
        self.batch_progress.setValue(current)
        self._batch_results.append(result)

        status = result.get("status", "UNKNOWN")
        if status == "LIVE":
            self._batch_live += 1
        elif status == "DEAD":
            self._batch_dead += 1
        else:
            self._batch_unknown += 1

        self.batch_stats.setText(
            f"{current}/{total} — "
            f"Live: {self._batch_live} | Dead: {self._batch_dead} | Unknown: {self._batch_unknown}"
        )

        # Add row to table
        row = self.batch_table.rowCount()
        self.batch_table.insertRow(row)

        self.batch_table.setItem(row, 0, QTableWidgetItem(str(current)))

        status_item = QTableWidgetItem(result.get("traffic_light", "⚪") + " " + status)
        color = {
            "LIVE": QColor(GREEN), "DEAD": QColor(RED),
            "UNKNOWN": QColor(YELLOW), "RISKY": QColor(ORANGE)
        }.get(status, QColor(TEXT2))
        status_item.setForeground(color)
        self.batch_table.setItem(row, 1, status_item)

        self.batch_table.setItem(row, 2, QTableWidgetItem(result.get("card", "—")))
        self.batch_table.setItem(row, 3, QTableWidgetItem(result.get("card_type", "—")))
        self.batch_table.setItem(row, 4, QTableWidgetItem(result.get("bank", "—")))
        self.batch_table.setItem(row, 5, QTableWidgetItem(result.get("country", "—")))
        self.batch_table.setItem(row, 6, QTableWidgetItem(result.get("message", "—")))

        self.batch_table.scrollToBottom()

    def _on_batch_finished(self, results: List[Dict]):
        self.batch_start_btn.setEnabled(True)
        self.batch_stop_btn.setEnabled(False)

        total = len(results)
        live_pct = (self._batch_live / total * 100) if total else 0
        self.batch_stats.setText(
            f"COMPLETE: {total} cards — "
            f"Live: {self._batch_live} ({live_pct:.0f}%) | "
            f"Dead: {self._batch_dead} | Unknown: {self._batch_unknown}"
        )

    def _on_batch_error(self, err: str):
        self.batch_start_btn.setEnabled(True)
        self.batch_stop_btn.setEnabled(False)
        QMessageBox.warning(self, "Batch Error", err)

    def _on_batch_export(self):
        if not self._batch_results:
            QMessageBox.information(self, "Export", "No results to export")
            return

        path, _ = QFileDialog.getSaveFileName(self, "Export Results", "cerberus_results.csv", "CSV (*.csv);;JSON (*.json)")
        if not path:
            return

        try:
            if path.endswith(".json"):
                with open(path, "w") as f:
                    json.dump(self._batch_results, f, indent=2)
            else:
                with open(path, "w", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(["Status", "Card", "Network", "Bank", "Country", "Message", "Risk"])
                    for r in self._batch_results:
                        writer.writerow([
                            r.get("status", ""), r.get("card", ""), r.get("card_type", ""),
                            r.get("bank", ""), r.get("country", ""), r.get("message", ""),
                            r.get("risk_score", "")
                        ])
            QMessageBox.information(self, "Export", f"Results exported to {path}")
        except Exception as e:
            QMessageBox.warning(self, "Export Error", str(e))

    # ───────────────────────────────────────────────────────────────────────
    # TAB 3: INTELLIGENCE
    # ───────────────────────────────────────────────────────────────────────

    def _build_intelligence_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # BIN Lookup
        bin_grp = QGroupBox("BIN Intelligence Lookup")
        bin_layout = QHBoxLayout(bin_grp)

        bin_layout.addWidget(QLabel("BIN (6 digits):"))
        self.bin_input = QLineEdit()
        self.bin_input.setPlaceholderText("453201")
        self.bin_input.setMaxLength(8)
        self.bin_input.setFixedWidth(120)
        bin_layout.addWidget(self.bin_input)

        self.bin_lookup_btn = QPushButton("Lookup BIN")
        self.bin_lookup_btn.clicked.connect(self._on_bin_lookup)
        bin_layout.addWidget(self.bin_lookup_btn)
        bin_layout.addStretch()
        layout.addWidget(bin_grp)

        # BIN result
        self.bin_result = QPlainTextEdit()
        self.bin_result.setReadOnly(True)
        self.bin_result.setMaximumHeight(200)
        self.bin_result.setStyleSheet(f"font-family: Consolas; font-size: 12px; background: {BG_INPUT};")
        layout.addWidget(self.bin_result)

        # Validation History
        hist_grp = QGroupBox(f"Validation History (last {min(len(self.validation_history), 100)} entries)")
        hist_layout = QVBoxLayout(hist_grp)

        self.hist_table = QTableWidget(0, 6)
        self.hist_table.setHorizontalHeaderLabels(["Time", "Status", "Card", "Bank", "Message", "Risk"])
        self.hist_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.hist_table.verticalHeader().setVisible(False)
        self.hist_table.setAlternatingRowColors(True)
        self.hist_table.setStyleSheet(f"QTableWidget {{ alternate-background-color: {BG_INPUT}; }}")

        # Populate history
        for entry in reversed(self.validation_history[-100:]):
            row = self.hist_table.rowCount()
            self.hist_table.insertRow(row)
            self.hist_table.setItem(row, 0, QTableWidgetItem(entry.get("timestamp", "—")[:19]))
            status = entry.get("status", "—")
            si = QTableWidgetItem(entry.get("traffic_light", "") + " " + status)
            color = {"LIVE": QColor(GREEN), "DEAD": QColor(RED), "UNKNOWN": QColor(YELLOW), "RISKY": QColor(ORANGE)}.get(status, QColor(TEXT2))
            si.setForeground(color)
            self.hist_table.setItem(row, 1, si)
            self.hist_table.setItem(row, 2, QTableWidgetItem(entry.get("card", "—")))
            self.hist_table.setItem(row, 3, QTableWidgetItem(entry.get("bank", "—")))
            self.hist_table.setItem(row, 4, QTableWidgetItem(entry.get("message", "—")))
            self.hist_table.setItem(row, 5, QTableWidgetItem(str(entry.get("risk_score", "—"))))

        hist_layout.addWidget(self.hist_table)
        layout.addWidget(hist_grp)

        # Decline analytics summary
        analytics_grp = QGroupBox("Decline Analytics")
        analytics_layout = QVBoxLayout(analytics_grp)
        self.analytics_text = QPlainTextEdit()
        self.analytics_text.setReadOnly(True)
        self.analytics_text.setMaximumHeight(150)
        self.analytics_text.setStyleSheet(f"font-family: Consolas; font-size: 11px; background: {BG_INPUT};")
        self._refresh_analytics()
        analytics_layout.addWidget(self.analytics_text)
        layout.addWidget(analytics_grp)

        return w

    def _on_bin_lookup(self):
        bin6 = re.sub(r'\D', '', self.bin_input.text())[:6]
        if len(bin6) < 6:
            self.bin_result.setPlainText("Enter a valid 6-digit BIN")
            return

        lines = [f"BIN: {bin6}", "=" * 40]

        # Built-in lookup
        info = _BUILTIN_BIN_DB.get(bin6, {})
        if info:
            lines.append(f"Bank: {info.get('bank', '?')}")
            lines.append(f"Type: {info.get('type', '?')}")
            lines.append(f"Level: {info.get('level', '?')}")
            lines.append(f"Country: {info.get('country', '?')}")
            lines.append(f"Network: {info.get('network', '?')}")
            lines.append(f"Risk: {info.get('risk', '?')}")
        else:
            lines.append("BIN not in local database")

        # Enhanced BIN scoring
        if CERBERUS_ENHANCED and self.bin_scorer:
            lines.append("")
            lines.append("═══ AI BIN SCORE ═══")
            try:
                score = self.bin_scorer.score_bin(bin6)
                lines.append(f"Overall Score: {score.overall_score}/100")
                lines.append(f"Est. Success Rate: {score.estimated_success_rate:.0%}")
                lines.append(f"Est. 3DS Rate: {score.estimated_3ds_rate:.0%}")
                lines.append(f"AVS Strictness: {score.avs_strictness}")
                lines.append(f"Max Single Amount: ${score.max_single_amount:,.0f}")
                lines.append(f"Daily Limit: ${score.velocity_limit_daily:,.0f}")
                if score.risk_factors:
                    lines.append(f"\nRisk Factors:")
                    for rf in score.risk_factors:
                        lines.append(f"  - {rf}")
                if score.recommendations:
                    lines.append(f"\nRecommendations:")
                    for rec in score.recommendations:
                        lines.append(f"  - {rec}")
                if score.target_compatibility:
                    lines.append(f"\nTarget Compatibility:")
                    for target, compat in sorted(score.target_compatibility.items(), key=lambda x: -x[1]):
                        lines.append(f"  {target}: {compat:.0%}")
            except Exception as e:
                lines.append(f"Scoring error: {e}")

        # Core BIN database
        if CERBERUS_CORE:
            core_info = CerberusValidator.BIN_DATABASE.get(bin6, {})
            if core_info:
                lines.append("")
                lines.append("═══ CORE DB ═══")
                for k, v in core_info.items():
                    lines.append(f"  {k}: {v}")

        self.bin_result.setPlainText("\n".join(lines))

    def _refresh_analytics(self):
        if not self.validation_history:
            self.analytics_text.setPlainText("No validation history yet")
            return

        total = len(self.validation_history)
        live = sum(1 for h in self.validation_history if h.get("status") == "LIVE")
        dead = sum(1 for h in self.validation_history if h.get("status") == "DEAD")
        unknown = sum(1 for h in self.validation_history if h.get("status") == "UNKNOWN")
        risky = sum(1 for h in self.validation_history if h.get("status") == "RISKY")

        # Decline reason breakdown
        decline_reasons = {}
        for h in self.validation_history:
            reason = h.get("decline_reason") or h.get("decline_category")
            if reason:
                decline_reasons[reason] = decline_reasons.get(reason, 0) + 1

        lines = [
            f"Total Validations: {total}",
            f"Live: {live} ({live/total*100:.0f}%)" if total else "Live: 0",
            f"Dead: {dead} ({dead/total*100:.0f}%)" if total else "Dead: 0",
            f"Unknown: {unknown} ({unknown/total*100:.0f}%)" if total else "Unknown: 0",
            f"Risky: {risky} ({risky/total*100:.0f}%)" if total else "Risky: 0",
            "",
            "Top Decline Reasons:"
        ]
        for reason, count in sorted(decline_reasons.items(), key=lambda x: -x[1])[:10]:
            lines.append(f"  {reason}: {count}")

        self.analytics_text.setPlainText("\n".join(lines))

    # ───────────────────────────────────────────────────────────────────────
    # TAB 3: ROUTING (Hyperswitch Intelligent Routing Dashboard)
    # ───────────────────────────────────────────────────────────────────────

    def _build_routing_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Routing algorithm selector
        algo_grp = QGroupBox("Routing Algorithm")
        algo_layout = QHBoxLayout(algo_grp)

        algo_layout.addWidget(QLabel("Active Algorithm:"))
        self.routing_algo_combo = QComboBox()
        self.routing_algo_combo.addItems([
            "Auth Rate (MAB)", "Least Cost", "Priority-Based", "Elimination"
        ])
        self.routing_algo_combo.setFixedWidth(200)
        algo_layout.addWidget(self.routing_algo_combo)

        self.routing_refresh_btn = QPushButton("Refresh")
        self.routing_refresh_btn.clicked.connect(self._on_routing_refresh)
        algo_layout.addWidget(self.routing_refresh_btn)

        algo_layout.addStretch()

        algo_info = QLabel(
            "Auth Rate: ML-driven Multi-Armed Bandit optimizes for highest approval rate\n"
            "Least Cost: Routes to cheapest connector per transaction\n"
            "Priority: Fixed priority ordering with failover\n"
            "Elimination: Detects downtime and de-prioritizes failing connectors"
        )
        algo_info.setStyleSheet(f"color: {TEXT2}; background: transparent; font-size: 10px;")
        algo_info.setWordWrap(True)
        algo_layout.addWidget(algo_info)
        layout.addWidget(algo_grp)

        # Connector health dashboard
        health_grp = QGroupBox("Connector Health")
        health_layout = QVBoxLayout(health_grp)

        self.routing_health_table = QTableWidget(0, 6)
        self.routing_health_table.setHorizontalHeaderLabels([
            "Connector", "Status", "Auth Rate", "Latency (ms)", "Volume (7d)", "Priority"
        ])
        self.routing_health_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.routing_health_table.verticalHeader().setVisible(False)
        self.routing_health_table.setAlternatingRowColors(True)
        self.routing_health_table.setStyleSheet(f"QTableWidget {{ alternate-background-color: {BG_INPUT}; }}")

        # Populate with default connectors
        default_connectors = [
            ("Stripe", "Active" if HYPERSWITCH_OK else "Standby", "94.2%", "230", "1,247", "1"),
            ("Braintree", "Active" if HYPERSWITCH_OK else "Standby", "91.8%", "310", "892", "2"),
            ("Adyen", "Active" if HYPERSWITCH_OK else "Standby", "93.1%", "280", "1,034", "3"),
            ("Checkout.com", "Available", "—", "—", "0", "4"),
            ("PayPal", "Available", "—", "—", "0", "5"),
        ]
        for i, (name, status, auth, lat, vol, pri) in enumerate(default_connectors):
            self.routing_health_table.insertRow(i)
            self.routing_health_table.setItem(i, 0, QTableWidgetItem(name))
            status_item = QTableWidgetItem(status)
            status_color = GREEN if status == "Active" else (YELLOW if status == "Standby" else TEXT2)
            status_item.setForeground(QColor(status_color))
            self.routing_health_table.setItem(i, 1, status_item)
            self.routing_health_table.setItem(i, 2, QTableWidgetItem(auth))
            self.routing_health_table.setItem(i, 3, QTableWidgetItem(lat))
            self.routing_health_table.setItem(i, 4, QTableWidgetItem(vol))
            self.routing_health_table.setItem(i, 5, QTableWidgetItem(pri))

        health_layout.addWidget(self.routing_health_table)
        layout.addWidget(health_grp)

        # Routing log
        log_grp = QGroupBox("Routing Decisions (Live)")
        log_layout = QVBoxLayout(log_grp)
        self.routing_log = QPlainTextEdit()
        self.routing_log.setReadOnly(True)
        self.routing_log.setMaximumHeight(200)
        self.routing_log.setStyleSheet(f"font-family: Consolas; font-size: 11px; background: {BG_INPUT};")
        self.routing_log.setPlainText(
            "Routing engine initialized\n"
            f"Algorithm: Auth Rate (MAB)\n"
            f"Hyperswitch: {'Connected' if HYPERSWITCH_OK else 'Not configured — using direct PSP routing'}\n"
            f"Active connectors: {'3+ via Hyperswitch' if HYPERSWITCH_OK else 'Stripe, Braintree, Adyen (direct)'}\n"
            "Awaiting transactions..."
        )
        log_layout.addWidget(self.routing_log)
        layout.addWidget(log_grp)

        return w

    def _on_routing_refresh(self):
        """Refresh routing dashboard with live data"""
        if self.hs_analytics:
            try:
                loop = asyncio.new_event_loop()
                summary = loop.run_until_complete(self.hs_analytics.get_summary())
                loop.close()

                lines = [f"Active Connectors: {summary.get('active_connectors', 0)}"]
                lines.append(f"Overall Auth Rate: {summary.get('overall_auth_rate', 0)}%")
                lines.append(f"Total Volume: ${summary.get('total_volume_usd', 0):,.2f}")
                if summary.get('best_connector'):
                    lines.append(f"Best Connector: {summary['best_connector']} ({summary['best_auth_rate']}%)")
                self.routing_log.appendPlainText("\n" + "\n".join(lines))
            except Exception as e:
                self.routing_log.appendPlainText(f"\nRefresh error: {e}")
        else:
            self.routing_log.appendPlainText("\nHyperswitch not available — showing cached data")

    # ───────────────────────────────────────────────────────────────────────
    # TAB 4: VAULT (PCI-Compliant Card Storage)
    # ───────────────────────────────────────────────────────────────────────

    def _build_vault_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Vault status
        vault_status = QGroupBox("Vault Status")
        vs_layout = QHBoxLayout(vault_status)
        vault_ok = HYPERSWITCH_OK and self.hs_vault is not None
        vs_lbl = QLabel(f"PCI Vault: {'ACTIVE' if vault_ok else 'OFFLINE'}")
        vs_lbl.setStyleSheet(f"color: {GREEN if vault_ok else ORANGE}; font-weight: bold; font-size: 13px; background: transparent;")
        vs_layout.addWidget(vs_lbl)
        vs_info = QLabel("Cards tokenized via Hyperswitch Vault — PCI DSS compliant" if vault_ok else "Enable Hyperswitch to activate PCI-compliant card vault")
        vs_info.setStyleSheet(f"color: {TEXT2}; font-size: 11px; background: transparent;")
        vs_layout.addWidget(vs_info)
        vs_layout.addStretch()
        layout.addWidget(vault_status)

        # Store card form
        store_grp = QGroupBox("Store Card in Vault")
        store_layout = QFormLayout(store_grp)

        self.vault_card_input = QLineEdit()
        self.vault_card_input.setPlaceholderText("4242424242424242|12|25|123")
        self.vault_card_input.setFont(QFont("Consolas", 12))
        store_layout.addRow("Card Data:", self.vault_card_input)

        self.vault_nickname = QLineEdit()
        self.vault_nickname.setPlaceholderText("My Chase Visa")
        store_layout.addRow("Nickname:", self.vault_nickname)

        vault_btn_layout = QHBoxLayout()
        self.vault_store_btn = QPushButton("STORE IN VAULT")
        self.vault_store_btn.clicked.connect(self._on_vault_store)
        vault_btn_layout.addWidget(self.vault_store_btn)

        self.vault_refresh_btn = QPushButton("Refresh")
        self.vault_refresh_btn.setStyleSheet(f"background: {BG_INPUT}; color: {TEXT};")
        self.vault_refresh_btn.clicked.connect(self._on_vault_refresh)
        vault_btn_layout.addWidget(self.vault_refresh_btn)
        vault_btn_layout.addStretch()
        store_layout.addRow("", vault_btn_layout)
        layout.addWidget(store_grp)

        # Vaulted cards table
        cards_grp = QGroupBox("Vaulted Cards")
        cards_layout = QVBoxLayout(cards_grp)

        self.vault_table = QTableWidget(0, 7)
        self.vault_table.setHorizontalHeaderLabels([
            "ID", "Last 4", "Network", "Exp", "Issuer", "Nickname", "Actions"
        ])
        self.vault_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.vault_table.verticalHeader().setVisible(False)
        self.vault_table.setAlternatingRowColors(True)
        self.vault_table.setStyleSheet(f"QTableWidget {{ alternate-background-color: {BG_INPUT}; }}")
        cards_layout.addWidget(self.vault_table)
        layout.addWidget(cards_grp)

        # Vault log
        self.vault_log = QPlainTextEdit()
        self.vault_log.setReadOnly(True)
        self.vault_log.setMaximumHeight(120)
        self.vault_log.setStyleSheet(f"font-family: Consolas; font-size: 11px; background: {BG_INPUT};")
        self.vault_log.setPlainText("Vault ready. Cards are tokenized and stored securely.")
        layout.addWidget(self.vault_log)

        return w

    def _on_vault_store(self):
        """Store a card in the Hyperswitch vault"""
        card_data = self.vault_card_input.text().strip()
        nickname = self.vault_nickname.text().strip()

        if not card_data:
            self.vault_log.appendPlainText("Enter card data to store")
            return

        if not self.hs_vault:
            self.vault_log.appendPlainText("Vault not available — Hyperswitch not configured")
            return

        # Parse card data
        parts = card_data.split("|")
        if len(parts) < 4:
            self.vault_log.appendPlainText("Invalid format. Use: PAN|MM|YY|CVV")
            return

        try:
            loop = asyncio.new_event_loop()
            vaulted = loop.run_until_complete(self.hs_vault.store_card(
                card_number=parts[0].strip(),
                card_exp_month=parts[1].strip(),
                card_exp_year=parts[2].strip(),
                card_cvc=parts[3].strip() if len(parts) > 3 else None,
                nickname=nickname or None,
            ))
            loop.close()

            self.vault_log.appendPlainText(
                f"Stored: {vaulted.card_network.upper()} ****{vaulted.card_last4} "
                f"(ID: {vaulted.payment_method_id[:12]}...)"
            )
            self.vault_card_input.clear()
            self.vault_nickname.clear()
            self._on_vault_refresh()
        except Exception as e:
            self.vault_log.appendPlainText(f"Vault error: {e}")

    def _on_vault_refresh(self):
        """Refresh the vaulted cards table"""
        if not self.hs_vault:
            return

        try:
            loop = asyncio.new_event_loop()
            cards = loop.run_until_complete(self.hs_vault.list_cards())
            loop.close()

            self.vault_table.setRowCount(0)
            for card in cards:
                row = self.vault_table.rowCount()
                self.vault_table.insertRow(row)
                self.vault_table.setItem(row, 0, QTableWidgetItem(card.payment_method_id[:12] + "..."))
                self.vault_table.setItem(row, 1, QTableWidgetItem(f"****{card.card_last4}"))
                self.vault_table.setItem(row, 2, QTableWidgetItem(card.card_network.upper()))
                self.vault_table.setItem(row, 3, QTableWidgetItem(f"{card.card_exp_month}/{card.card_exp_year}"))
                self.vault_table.setItem(row, 4, QTableWidgetItem(card.card_issuer or "—"))
                self.vault_table.setItem(row, 5, QTableWidgetItem(card.nickname or "—"))

                rm_btn = QPushButton("Delete")
                rm_btn.setStyleSheet(f"background: {RED}; padding: 3px 8px; font-size: 10px;")
                rm_btn.clicked.connect(lambda _, pid=card.payment_method_id: self._on_vault_delete(pid))
                self.vault_table.setCellWidget(row, 6, rm_btn)
        except Exception as e:
            self.vault_log.appendPlainText(f"Refresh error: {e}")

    def _on_vault_delete(self, payment_method_id: str):
        """Delete a card from the vault"""
        if self.hs_vault:
            try:
                loop = asyncio.new_event_loop()
                loop.run_until_complete(self.hs_vault.delete_card(payment_method_id))
                loop.close()
                self.vault_log.appendPlainText(f"Deleted: {payment_method_id[:12]}...")
                self._on_vault_refresh()
            except Exception as e:
                self.vault_log.appendPlainText(f"Delete error: {e}")

    # ───────────────────────────────────────────────────────────────────────
    # TAB 5: ANALYTICS (Per-Connector Performance)
    # ───────────────────────────────────────────────────────────────────────

    def _build_analytics_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Summary cards
        summary_grp = QGroupBox("Performance Summary")
        summary_layout = QHBoxLayout(summary_grp)

        self.analytics_total_txn = self._make_stat_card("Total Txns", "0")
        self.analytics_auth_rate = self._make_stat_card("Auth Rate", "0%")
        self.analytics_volume = self._make_stat_card("Volume (USD)", "$0")
        self.analytics_connectors = self._make_stat_card("Active Connectors", "0")
        self.analytics_best = self._make_stat_card("Best Connector", "—")

        for card_widget in [self.analytics_total_txn, self.analytics_auth_rate,
                            self.analytics_volume, self.analytics_connectors, self.analytics_best]:
            summary_layout.addWidget(card_widget)
        layout.addWidget(summary_grp)

        # Refresh button
        ctrl = QHBoxLayout()
        self.analytics_refresh_btn = QPushButton("Refresh Analytics")
        self.analytics_refresh_btn.clicked.connect(self._on_analytics_refresh)
        ctrl.addWidget(self.analytics_refresh_btn)

        self.analytics_period_combo = QComboBox()
        self.analytics_period_combo.addItems(["Last 24h", "Last 7d", "Last 30d"])
        self.analytics_period_combo.setCurrentIndex(1)
        ctrl.addWidget(self.analytics_period_combo)
        ctrl.addStretch()
        layout.addLayout(ctrl)

        # Per-connector table
        conn_grp = QGroupBox("Per-Connector Breakdown")
        conn_layout = QVBoxLayout(conn_grp)

        self.analytics_conn_table = QTableWidget(0, 7)
        self.analytics_conn_table.setHorizontalHeaderLabels([
            "Connector", "Transactions", "Success", "Failed", "Auth Rate", "Volume (USD)", "Top Decline"
        ])
        self.analytics_conn_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.analytics_conn_table.verticalHeader().setVisible(False)
        self.analytics_conn_table.setAlternatingRowColors(True)
        self.analytics_conn_table.setStyleSheet(f"QTableWidget {{ alternate-background-color: {BG_INPUT}; }}")
        conn_layout.addWidget(self.analytics_conn_table)
        layout.addWidget(conn_grp)

        # Decline heatmap (text-based)
        decline_grp = QGroupBox("Decline Code Distribution")
        decline_layout = QVBoxLayout(decline_grp)
        self.analytics_decline_text = QPlainTextEdit()
        self.analytics_decline_text.setReadOnly(True)
        self.analytics_decline_text.setMaximumHeight(180)
        self.analytics_decline_text.setStyleSheet(f"font-family: Consolas; font-size: 11px; background: {BG_INPUT};")
        self._refresh_analytics_decline()
        decline_layout.addWidget(self.analytics_decline_text)
        layout.addWidget(decline_grp)

        return w

    def _make_stat_card(self, title: str, value: str) -> QWidget:
        """Create a stat card widget for analytics summary"""
        card = QFrame()
        card.setFixedHeight(80)
        card.setStyleSheet(f"background: {BG_CARD}; border: 1px solid {BORDER}; border-radius: 8px;")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(12, 8, 12, 8)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"color: {TEXT2}; font-size: 10px; background: transparent; border: none;")
        cl.addWidget(title_lbl)

        value_lbl = QLabel(value)
        value_lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        value_lbl.setStyleSheet(f"color: {ACCENT}; background: transparent; border: none;")
        value_lbl.setObjectName("stat_value")
        cl.addWidget(value_lbl)

        return card

    def _on_analytics_refresh(self):
        """Refresh analytics with live Hyperswitch data"""
        if self.hs_analytics:
            try:
                loop = asyncio.new_event_loop()
                summary = loop.run_until_complete(self.hs_analytics.get_summary())
                analytics = loop.run_until_complete(self.hs_analytics.get_connector_analytics())
                loop.close()

                # Update summary cards
                self.analytics_total_txn.findChild(QLabel, "stat_value").setText(str(summary.get("total_transactions", 0)))
                self.analytics_auth_rate.findChild(QLabel, "stat_value").setText(f"{summary.get('overall_auth_rate', 0)}%")
                self.analytics_volume.findChild(QLabel, "stat_value").setText(f"${summary.get('total_volume_usd', 0):,.0f}")
                self.analytics_connectors.findChild(QLabel, "stat_value").setText(str(summary.get("active_connectors", 0)))
                self.analytics_best.findChild(QLabel, "stat_value").setText(summary.get("best_connector", "—") or "—")

                # Update connector table
                self.analytics_conn_table.setRowCount(0)
                for a in analytics:
                    row = self.analytics_conn_table.rowCount()
                    self.analytics_conn_table.insertRow(row)
                    self.analytics_conn_table.setItem(row, 0, QTableWidgetItem(a.connector_name))
                    self.analytics_conn_table.setItem(row, 1, QTableWidgetItem(str(a.total_transactions)))
                    self.analytics_conn_table.setItem(row, 2, QTableWidgetItem(str(a.successful)))
                    self.analytics_conn_table.setItem(row, 3, QTableWidgetItem(str(a.failed)))

                    rate_item = QTableWidgetItem(f"{a.auth_rate}%")
                    rate_color = GREEN if a.auth_rate >= 90 else (YELLOW if a.auth_rate >= 70 else RED)
                    rate_item.setForeground(QColor(rate_color))
                    self.analytics_conn_table.setItem(row, 4, rate_item)

                    self.analytics_conn_table.setItem(row, 5, QTableWidgetItem(f"${a.total_amount:,.2f}"))

                    top_decline = a.top_decline_codes[0]["code"] if a.top_decline_codes else "—"
                    self.analytics_conn_table.setItem(row, 6, QTableWidgetItem(top_decline))

            except Exception as e:
                pass  # Silently handle — analytics is non-critical

        # Also refresh local decline analytics
        self._refresh_analytics_decline()

    def _refresh_analytics_decline(self):
        """Refresh decline code distribution from local history"""
        if not self.validation_history:
            self.analytics_decline_text.setPlainText("No validation data yet")
            return

        total = len(self.validation_history)
        live = sum(1 for h in self.validation_history if h.get("status") == "LIVE")
        dead = sum(1 for h in self.validation_history if h.get("status") == "DEAD")

        decline_reasons = {}
        for h in self.validation_history:
            reason = h.get("decline_reason") or h.get("decline_category")
            if reason:
                decline_reasons[reason] = decline_reasons.get(reason, 0) + 1

        gateway_stats = {}
        for h in self.validation_history:
            for gw in h.get("gateways_tried", []):
                if gw not in gateway_stats:
                    gateway_stats[gw] = {"total": 0, "live": 0, "dead": 0}
                gateway_stats[gw]["total"] += 1
                if h.get("status") == "LIVE":
                    gateway_stats[gw]["live"] += 1
                elif h.get("status") == "DEAD":
                    gateway_stats[gw]["dead"] += 1

        lines = [
            f"Total: {total} | Live: {live} ({live/total*100:.0f}%) | Dead: {dead} ({dead/total*100:.0f}%)" if total else "No data",
            "",
            "Per-Gateway Success:"
        ]
        for gw, stats in sorted(gateway_stats.items(), key=lambda x: -x[1]["total"]):
            rate = (stats["live"] / stats["total"] * 100) if stats["total"] > 0 else 0
            lines.append(f"  {gw}: {stats['total']} txns, {rate:.0f}% auth rate")

        lines.append("")
        lines.append("Top Decline Reasons:")
        for reason, count in sorted(decline_reasons.items(), key=lambda x: -x[1])[:10]:
            pct = count / dead * 100 if dead > 0 else 0
            lines.append(f"  {reason}: {count} ({pct:.0f}%)")

        self.analytics_decline_text.setPlainText("\n".join(lines))

    # ───────────────────────────────────────────────────────────────────────
    # TAB 7: CONNECTORS (formerly API KEYS)
    # ───────────────────────────────────────────────────────────────────────

    def _build_connectors_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Hyperswitch status banner
        hs_banner = QGroupBox("Hyperswitch Status")
        hs_bl = QHBoxLayout(hs_banner)
        hs_status = "CONNECTED" if HYPERSWITCH_OK else "NOT CONFIGURED"
        hs_color = GREEN if HYPERSWITCH_OK else ORANGE
        hs_lbl = QLabel(f"Hyperswitch: {hs_status}")
        hs_lbl.setStyleSheet(f"color: {hs_color}; font-weight: bold; font-size: 13px; background: transparent;")
        hs_bl.addWidget(hs_lbl)
        hs_info = QLabel("50+ connectors via intelligent routing" if HYPERSWITCH_OK else "Configure Hyperswitch for intelligent routing across 50+ PSPs")
        hs_info.setStyleSheet(f"color: {TEXT2}; font-size: 11px; background: transparent;")
        hs_bl.addWidget(hs_info)
        hs_bl.addStretch()
        layout.addWidget(hs_banner)

        info = QLabel(
            "Add merchant API keys for direct PSP validation (fallback when Hyperswitch is offline).\n"
            "Keys are stored locally in ~/.cerberus_appx/keys.json.\n"
            "When Hyperswitch is active, connectors are managed through the Hyperswitch admin API."
        )
        info.setStyleSheet(f"color: {TEXT2}; background: transparent; font-size: 12px;")
        info.setWordWrap(True)
        layout.addWidget(info)

        # Add key form
        add_grp = QGroupBox("Add Merchant Key")
        add_layout = QFormLayout(add_grp)

        self.key_provider = QComboBox()
        self.key_provider.addItems(["stripe", "braintree", "adyen"])
        add_layout.addRow("Provider:", self.key_provider)

        self.key_public = QLineEdit()
        self.key_public.setPlaceholderText("pk_test_... or pk_live_...")
        add_layout.addRow("Public Key:", self.key_public)

        self.key_secret = QLineEdit()
        self.key_secret.setPlaceholderText("sk_test_... or sk_live_...")
        self.key_secret.setEchoMode(QLineEdit.EchoMode.Password)
        add_layout.addRow("Secret Key:", self.key_secret)

        self.key_merchant_id = QLineEdit()
        self.key_merchant_id.setPlaceholderText("Optional — required for Braintree/Adyen")
        add_layout.addRow("Merchant ID:", self.key_merchant_id)

        self.key_is_live = QCheckBox("Live key (not test)")
        add_layout.addRow("", self.key_is_live)

        add_btn = QPushButton("Add Key")
        add_btn.clicked.connect(self._on_add_key)
        add_layout.addRow("", add_btn)

        layout.addWidget(add_grp)

        # Current keys table
        keys_grp = QGroupBox("Configured Keys")
        keys_layout = QVBoxLayout(keys_grp)

        self.keys_table = QTableWidget(0, 5)
        self.keys_table.setHorizontalHeaderLabels(["Provider", "Public Key", "Live?", "Success", "Remove"])
        self.keys_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.keys_table.verticalHeader().setVisible(False)
        keys_layout.addWidget(self.keys_table)
        self._refresh_keys_table()

        layout.addWidget(keys_grp)
        layout.addStretch()

        return w

    def _on_add_key(self):
        provider = self.key_provider.currentText()
        public_key = self.key_public.text().strip()
        secret_key = self.key_secret.text().strip()
        merchant_id = self.key_merchant_id.text().strip()
        is_live = self.key_is_live.isChecked()

        if not public_key or not secret_key:
            QMessageBox.warning(self, "Missing Keys", "Both public and secret keys are required")
            return

        if provider not in self.merchant_keys:
            self.merchant_keys[provider] = []

        self.merchant_keys[provider].append({
            "public_key": public_key,
            "secret_key": secret_key,
            "merchant_id": merchant_id or None,
            "is_live": is_live,
            "added_at": datetime.now().isoformat(),
            "success_count": 0,
            "fail_count": 0,
        })

        _save_keys(self.merchant_keys)
        self._refresh_keys_table()

        self.key_public.clear()
        self.key_secret.clear()
        self.key_merchant_id.clear()
        QMessageBox.information(self, "Key Added", f"{provider} key added successfully")

    def _refresh_keys_table(self):
        self.keys_table.setRowCount(0)
        for provider, key_list in self.merchant_keys.items():
            for i, k in enumerate(key_list):
                row = self.keys_table.rowCount()
                self.keys_table.insertRow(row)
                self.keys_table.setItem(row, 0, QTableWidgetItem(provider.upper()))
                pk = k.get("public_key", "")
                self.keys_table.setItem(row, 1, QTableWidgetItem(f"{pk[:12]}...{pk[-4:]}" if len(pk) > 16 else pk))
                self.keys_table.setItem(row, 2, QTableWidgetItem("LIVE" if k.get("is_live") else "TEST"))
                self.keys_table.setItem(row, 3, QTableWidgetItem(f"{k.get('success_count', 0)}/{k.get('fail_count', 0)}"))

                rm_btn = QPushButton("Remove")
                rm_btn.setStyleSheet(f"background: {RED}; padding: 4px 8px; font-size: 10px;")
                rm_btn.clicked.connect(lambda _, p=provider, idx=i: self._remove_key(p, idx))
                self.keys_table.setCellWidget(row, 4, rm_btn)

    def _remove_key(self, provider: str, index: int):
        if provider in self.merchant_keys and index < len(self.merchant_keys[provider]):
            self.merchant_keys[provider].pop(index)
            _save_keys(self.merchant_keys)
            self._refresh_keys_table()


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    app = QApplication(sys.argv)
    if THEME_OK:
        apply_titan_theme(app)
    window = CerberusApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
