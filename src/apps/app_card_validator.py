#!/usr/bin/env python3
"""
TITAN V8.2 CARD VALIDATOR — BIN Check, Card Quality, AVS
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

try:
    from titan_theme import apply_titan_theme, make_tab_style
    THEME_OK = True
except ImportError:
    THEME_OK = False

try:
    from cerberus_core import CerberusValidator, CardAsset
    CERBERUS_OK = True
except ImportError:
    CERBERUS_OK = False

try:
    from cerberus_enhanced import (
        AVSEngine, BINScoringEngine, SilentValidationEngine,
        CardQualityGrader, OSINTVerifier
    )
    ENHANCED_OK = True
except ImportError:
    ENHANCED_OK = False

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
        self.setWindowTitle("TITAN V8.2 — Card Validator")
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
        self.val_target.addItems(["amazon.com", "ebay.com", "walmart.com", "bestbuy.com", "shopify.com"])
        gf.addRow("Target:", self.val_target)
        layout.addWidget(grp)

        # Validate button
        self.validate_btn = QPushButton("VALIDATE CARD")
        self.validate_btn.setStyleSheet(f"background: {ACCENT}; color: black; padding: 14px 32px; border-radius: 8px; font-weight: bold; font-size: 14px;")
        self.validate_btn.clicked.connect(self._validate)
        layout.addWidget(self.validate_btn)

        # Module status
        mgrp = QGroupBox("Module Status")
        mf = QVBoxLayout(mgrp)
        modules = [
            ("Cerberus Validator", CERBERUS_OK),
            ("Enhanced (AVS/BIN/Quality)", ENHANCED_OK),
            ("3DS Strategy", TDS_OK),
            ("Target Intelligence", INTEL_OK),
            ("Preflight Validator", PREFLIGHT_OK),
        ]
        for name, ok in modules:
            row = QHBoxLayout()
            dot = QLabel("●")
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
        self.val_result.setMinimumHeight(250)
        self.val_result.setPlaceholderText("Validation results will appear here...")
        layout.addWidget(self.val_result)

        layout.addStretch()
        self.tabs.addTab(scroll, "VALIDATE")

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
        layout.addStretch()
        self.tabs.addTab(scroll, "INTELLIGENCE")

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

    def _on_validate_done(self, result):
        self.validate_btn.setEnabled(True)
        self.validate_btn.setText("VALIDATE CARD")

        lines = []
        lines.append(f"BIN: {result.get('bin', '?')}")
        lines.append(f"Network: {result.get('network', '?')}")
        lines.append(f"Luhn: {'PASS' if result.get('luhn') else 'FAIL'}")

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

        self.val_result.setPlainText("\n".join(lines))

        # Add to history
        self.validation_history.append(result)
        row = self.history_table.rowCount()
        self.history_table.insertRow(row)
        self.history_table.setItem(row, 0, QTableWidgetItem(result.get("timestamp", "")[:19]))
        self.history_table.setItem(row, 1, QTableWidgetItem(result.get("bin", "")))
        self.history_table.setItem(row, 2, QTableWidgetItem(result.get("network", "")))
        self.history_table.setItem(row, 3, QTableWidgetItem("PASS" if result.get("luhn") else "FAIL"))
        self.history_table.setItem(row, 4, QTableWidgetItem(str(cerb.get("score", ""))))
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

        lines = [f"=== BIN Intelligence: {bin_val} ===\n"]

        if ENHANCED_OK:
            try:
                scorer = BINScoringEngine()
                score = scorer.score(bin_val)
                lines.append(f"BIN Score: {score}")
            except Exception as e:
                lines.append(f"BIN Score: error — {e}")

            try:
                grader = CardQualityGrader()
                grade = grader.grade(bin_val + "0000000000")
                lines.append(f"Quality Grade: {grade}")
            except Exception:
                pass

        if TDS_OK:
            try:
                strategy = get_3ds_strategy(bin_val)
                lines.append(f"\n3DS Strategy:\n{strategy}")
            except Exception as e:
                lines.append(f"\n3DS: {e}")

        if INTEL_OK:
            try:
                intel = get_target_intel(bin_val)
                lines.append(f"\nTarget Intel:\n{json.dumps(intel, indent=2, default=str)[:500]}")
            except Exception:
                pass

        self.intel_output.setPlainText("\n".join(lines))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = TitanCardValidator()
    win.show()
    sys.exit(app.exec())
