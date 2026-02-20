#!/usr/bin/env python3
"""
TITAN V7.5 SINGULARITY — Asset Validation & Risk Assessment
Card Validation GUI

PyQt6 Desktop Application for zero-touch card validation.
User pastes card -> App shows Traffic Light (Green/Yellow/Red).
Simple, fast, no-burn validation using merchant APIs.

Traffic Light System:
🟢 GREEN (LIVE) - Card is valid, proceed with operation
🔴 RED (DEAD) - Card declined, discard
🟡 YELLOW (UNKNOWN) - Couldn't validate, try again
🟠 ORANGE (RISKY) - Valid but high-risk BIN
"""

import sys
import os
from pathlib import Path

# Add core library to path
sys.path.insert(0, str(Path(__file__).parent.parent / "core"))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QTextEdit, QPushButton, QGroupBox, QFormLayout,
    QProgressBar, QMessageBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QFrame, QSplitter, QDialog, QDialogButtonBox,
    QFileDialog, QTabWidget, QComboBox, QSpinBox, QPlainTextEdit,
    QScrollArea
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor, QBrush, QPalette

import asyncio
from cerberus_core import (
    CerberusValidator, CardAsset, ValidationResult, CardStatus,
    MerchantKey, BulkValidator
)
from cerberus_enhanced import (
    MaxDrainEngine, BINScoringEngine, generate_drain_plan, format_drain_plan
)

# Import enhanced modules (graceful fallback)
try:
    from cerberus_enhanced import (
        AVSEngine, SilentValidationEngine, GeoMatchChecker,
        OSINTVerifier, CardQualityGrader, IssuingBankPatternPredictor
    )
    ENHANCED_AVAILABLE = True
except ImportError:
    ENHANCED_AVAILABLE = False

try:
    from target_discovery import (
        AutoDiscovery, MERCHANT_DATABASE, SiteCategory, SiteDifficulty,
        DISCOVERY_DORKS
    )
    DISCOVERY_AVAILABLE = True
except ImportError:
    DISCOVERY_AVAILABLE = False


class DrainPlanDialog(QDialog):
    """Dialog showing full MaxDrain strategy plan"""
    
    def __init__(self, plan_text: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Extraction Strategy Plan")
        self.setMinimumSize(700, 600)
        
        layout = QVBoxLayout(self)
        
        header = QLabel("Extraction Strategy")
        header.setFont(QFont("Inter", 16, QFont.Weight.Bold))
        header.setStyleSheet("color: #E6A817;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        self.plan_display = QTextEdit()
        self.plan_display.setReadOnly(True)
        self.plan_display.setFont(QFont("Consolas", 10))
        self.plan_display.setPlainText(plan_text)
        self.plan_display.setStyleSheet("""
            QTextEdit {
                background-color: #1C2330;
                color: #e0e0e0;
                border: 1px solid #333;
                border-radius: 6px;
                padding: 10px;
            }
        """)
        layout.addWidget(self.plan_display)
        
        btn_layout = QHBoxLayout()
        
        copy_btn = QPushButton("Copy to Clipboard")
        copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #E6A817;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #F0BD3E; }
        """)
        copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(plan_text))
        btn_layout.addWidget(copy_btn)
        
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #444;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
            }
            QPushButton:hover { background-color: #555; }
        """)
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)


class ValidateWorker(QThread):
    """Background worker for card validation"""
    finished = pyqtSignal(object)  # ValidationResult or Exception
    
    def __init__(self, validator: CerberusValidator, card: CardAsset):
        super().__init__()
        self.validator = validator
        self.card = card
    
    def run(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.validator.validate(self.card))
            loop.close()
            self.finished.emit(result)
        except Exception as e:
            self.finished.emit(e)


class KeyConfigDialog(QDialog):
    """Dialog for configuring merchant API keys"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configure API Keys")
        self.setMinimumSize(500, 300)
        
        layout = QVBoxLayout(self)
        
        # Stripe keys
        stripe_group = QGroupBox("Stripe API Keys")
        stripe_layout = QFormLayout(stripe_group)
        
        self.stripe_pk = QLineEdit()
        self.stripe_pk.setPlaceholderText("pk_live_...")
        stripe_layout.addRow("Public Key:", self.stripe_pk)
        
        self.stripe_sk = QLineEdit()
        self.stripe_sk.setPlaceholderText("sk_live_...")
        self.stripe_sk.setEchoMode(QLineEdit.EchoMode.Password)
        stripe_layout.addRow("Secret Key:", self.stripe_sk)
        
        layout.addWidget(stripe_group)
        
        # Info
        info = QLabel(
            "⚠️ Keys are stored in memory only and cleared on app close.\n"
            "Use harvested keys from Cerberus Key Harvester or your own test keys."
        )
        info.setStyleSheet("color: #888; font-size: 11px;")
        info.setWordWrap(True)
        layout.addWidget(info)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def get_keys(self):
        """Return configured keys"""
        keys = []
        if self.stripe_sk.text().strip():
            keys.append(MerchantKey(
                provider="stripe",
                public_key=self.stripe_pk.text().strip(),
                secret_key=self.stripe_sk.text().strip()
            ))
        return keys


class CerberusApp(QMainWindow):
    """
    Cerberus - The Gatekeeper
    
    Main GUI for card validation.
    
    Layout:
    ┌─────────────────────────────────────────────────┐
    │  🛡️ CERBERUS - THE GATEKEEPER                   │
    ├─────────────────────────────────────────────────┤
    │  ┌─────────────────────────────────────────┐    │
    │  │                                         │    │
    │  │              🟢 LIVE                    │    │
    │  │                                         │    │
    │  │         Card validated OK               │    │
    │  └─────────────────────────────────────────┘    │
    │                                                 │
    │  Card: [4242424242424242|12|25|123______]      │
    │                                                 │
    │  [  🔍 VALIDATE  ]  [  ⚙️ Keys  ]              │
    │                                                 │
    │  ─────────────────────────────────────────────  │
    │  History:                                       │
    │  | Card        | Status | Bank    | Time     | │
    │  |-------------|--------|---------|----------| │
    │  | 4242***4242 | 🟢 LIVE| Chase   | 14:32:01 | │
    │  | 5555***4444 | 🔴 DEAD| Unknown | 14:31:45 | │
    └─────────────────────────────────────────────────┘
    """
    
    def __init__(self):
        super().__init__()
        self.validator = CerberusValidator()
        self.worker = None
        self.history: list[ValidationResult] = []
        
        self.init_ui()
        self.apply_dark_theme()
    
    def init_ui(self):
        self.setWindowTitle("TITAN V7.5 — Asset Validation & Risk Assessment")
        try:
            from titan_icon import set_titan_icon
            set_titan_icon(self, "#3A75C4")
        except Exception:
            pass
        self.setMinimumSize(850, 750)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(12, 12, 12, 12)
        
        # Header
        header = QLabel("ASSET VALIDATION & RISK ASSESSMENT")
        header.setFont(QFont("Inter", 20, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("color: #3A75C4; margin-bottom: 2px;")
        main_layout.addWidget(header)
        
        subtitle = QLabel("Card Validation + BIN Intelligence + Target Discovery")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #556; font-size: 11px;")
        main_layout.addWidget(subtitle)
        
        # ═══ TABBED INTERFACE ═══
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # Tab 1: Validate (existing UI)
        validate_tab = QWidget()
        layout = QVBoxLayout(validate_tab)
        layout.setSpacing(12)
        layout.setContentsMargins(10, 10, 10, 10)
        self.tabs.addTab(validate_tab, "🔍 Validate")
        
        # Tab 2: BIN Intelligence
        self._build_bin_tab()
        
        # Tab 3: Target Discovery
        self._build_target_tab()
        
        # Tab 4: Card Quality
        self._build_quality_tab()
        
        # ═══ VALIDATION TAB CONTENT (existing) ═══
        
        # Traffic Light Display
        self.traffic_frame = QFrame()
        self.traffic_frame.setMinimumHeight(150)
        self.traffic_frame.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border: 2px solid #444;
                border-radius: 12px;
            }
        """)
        traffic_layout = QVBoxLayout(self.traffic_frame)
        traffic_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.traffic_light = QLabel("⚪")
        self.traffic_light.setFont(QFont("Inter Emoji", 64))
        self.traffic_light.setAlignment(Qt.AlignmentFlag.AlignCenter)
        traffic_layout.addWidget(self.traffic_light)
        
        self.status_text = QLabel("READY")
        self.status_text.setFont(QFont("Inter", 18, QFont.Weight.Bold))
        self.status_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_text.setStyleSheet("color: #888;")
        traffic_layout.addWidget(self.status_text)
        
        self.detail_text = QLabel("Paste card and click Validate")
        self.detail_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.detail_text.setStyleSheet("color: #666; font-size: 12px;")
        traffic_layout.addWidget(self.detail_text)
        
        layout.addWidget(self.traffic_frame)
        
        # Card Input
        input_group = QGroupBox("💳 Card Input")
        input_layout = QVBoxLayout(input_group)
        
        self.card_input = QLineEdit()
        self.card_input.setPlaceholderText("4242424242424242|12|25|123 or paste any format")
        self.card_input.setMinimumHeight(40)
        self.card_input.setFont(QFont("Consolas", 12))
        self.card_input.returnPressed.connect(self.validate_card)
        input_layout.addWidget(self.card_input)
        
        format_hint = QLabel("Formats: NUM|MM|YY|CVV or NUM|MM/YY|CVV or space-separated")
        format_hint.setStyleSheet("color: #666; font-size: 10px;")
        input_layout.addWidget(format_hint)
        
        layout.addWidget(input_group)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.validate_btn = QPushButton("🔍 VALIDATE")
        self.validate_btn.setMinimumHeight(45)
        self.validate_btn.setFont(QFont("Inter", 12, QFont.Weight.Bold))
        self.validate_btn.setStyleSheet("""
            QPushButton {
                background-color: #3A75C4;
                color: white;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #4A8AD8;
            }
            QPushButton:pressed {
                background-color: #2D5F9E;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #888;
            }
        """)
        self.validate_btn.clicked.connect(self.validate_card)
        btn_layout.addWidget(self.validate_btn, stretch=3)
        
        self.keys_btn = QPushButton("⚙️ Keys")
        self.keys_btn.setMinimumHeight(45)
        self.keys_btn.setStyleSheet("""
            QPushButton {
                background-color: #444;
                color: white;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #555;
            }
        """)
        self.keys_btn.clicked.connect(self.configure_keys)
        btn_layout.addWidget(self.keys_btn, stretch=1)
        
        self.clear_btn = QPushButton("🗑️")
        self.clear_btn.setMinimumHeight(45)
        self.clear_btn.setMinimumWidth(45)
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #444;
                color: white;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #555;
            }
        """)
        self.clear_btn.clicked.connect(self.clear_input)
        btn_layout.addWidget(self.clear_btn)
        
        layout.addLayout(btn_layout)
        
        # Strategy button (shown after LIVE validation)
        self.strategy_btn = QPushButton("Extraction Strategy")
        self.strategy_btn.setMinimumHeight(40)
        self.strategy_btn.setFont(QFont("Inter", 11, QFont.Weight.Bold))
        self.strategy_btn.setVisible(False)
        self.strategy_btn.setStyleSheet("""
            QPushButton {
                background-color: #E6A817;
                color: white;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #F0BD3E;
            }
            QPushButton:pressed {
                background-color: #e65100;
            }
        """)
        self.strategy_btn.clicked.connect(self.show_drain_strategy)
        layout.addWidget(self.strategy_btn)
        
        # Store last validated card BIN for strategy generation
        self._last_live_bin = None
        self._last_drain_plan = None
        
        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMinimumHeight(6)
        layout.addWidget(self.progress_bar)
        
        # History Table
        history_group = QGroupBox("📜 Validation History")
        history_layout = QVBoxLayout(history_group)
        
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(7)
        self.history_table.setHorizontalHeaderLabels(["Card", "Status", "Type", "Tier", "Bank", "Country", "Time"])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.history_table.setMinimumHeight(150)
        history_layout.addWidget(self.history_table)
        
        layout.addWidget(history_group)
        
        # Stats + action buttons
        stats_layout = QHBoxLayout()
        self.stats_label = QLabel("Live: 0 | Dead: 0 | Unknown: 0")
        self.stats_label.setStyleSheet("color: #888;")
        stats_layout.addWidget(self.stats_label)
        stats_layout.addStretch()
        
        export_btn = QPushButton("Export Results")
        export_btn.setStyleSheet("color: #3A75C4; background: transparent; border: 1px solid #3A75C4; border-radius: 4px; padding: 4px 10px;")
        export_btn.clicked.connect(self.export_results)
        stats_layout.addWidget(export_btn)
        
        bulk_btn = QPushButton("Bulk Validate")
        bulk_btn.setStyleSheet("color: #E6A817; background: transparent; border: 1px solid #E6A817; border-radius: 4px; padding: 4px 10px;")
        bulk_btn.clicked.connect(self.bulk_validate)
        stats_layout.addWidget(bulk_btn)
        
        clear_history_btn = QPushButton("Clear History")
        clear_history_btn.setStyleSheet("color: #888; background: transparent; border: none;")
        clear_history_btn.clicked.connect(self.clear_history)
        stats_layout.addWidget(clear_history_btn)
        
        layout.addLayout(stats_layout)
        
        # Footer
        footer = QLabel("TITAN V7.5 SINGULARITY | Asset Validation Engine")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet("color: #64748B; font-size: 10px;")
        layout.addWidget(footer)
    
    # ═══════════════════════════════════════════════════════════════════
    # TAB 2: BIN INTELLIGENCE
    # ═══════════════════════════════════════════════════════════════════

    def _build_bin_tab(self):
        """BIN lookup, scoring, and bank pattern analysis."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        self.tabs.addTab(tab, "🏦 BIN Intel")

        # BIN Input
        input_row = QHBoxLayout()
        input_row.addWidget(QLabel("BIN (first 6):"))
        self.bin_input = QLineEdit()
        self.bin_input.setPlaceholderText("e.g. 421783")
        self.bin_input.setMaxLength(8)
        self.bin_input.setFont(QFont("JetBrains Mono", 12))
        self.bin_input.setMinimumHeight(36)
        input_row.addWidget(self.bin_input, stretch=2)

        bin_lookup_btn = QPushButton("🔍 Lookup BIN")
        bin_lookup_btn.setMinimumHeight(36)
        bin_lookup_btn.setStyleSheet("background: #3A75C4; color: white; border: none; border-radius: 6px; padding: 0 16px; font-weight: bold;")
        bin_lookup_btn.clicked.connect(self._lookup_bin)
        input_row.addWidget(bin_lookup_btn)

        bin_score_btn = QPushButton("📊 Score BIN")
        bin_score_btn.setMinimumHeight(36)
        bin_score_btn.setStyleSheet("background: #E6A817; color: white; border: none; border-radius: 6px; padding: 0 16px; font-weight: bold;")
        bin_score_btn.clicked.connect(self._score_bin)
        input_row.addWidget(bin_score_btn)
        layout.addLayout(input_row)

        # BIN Result display
        self.bin_result = QPlainTextEdit()
        self.bin_result.setReadOnly(True)
        self.bin_result.setFont(QFont("JetBrains Mono", 10))
        self.bin_result.setPlaceholderText("Enter a BIN and click Lookup or Score...")
        self.bin_result.setMinimumHeight(200)
        layout.addWidget(self.bin_result)

        # Bank Pattern Predictor
        pattern_group = QGroupBox("🧠 Issuing Bank Pattern Predictor")
        pattern_layout = QVBoxLayout(pattern_group)
        pattern_row = QHBoxLayout()
        pattern_row.addWidget(QLabel("Amount $:"))
        self.pattern_amount = QSpinBox()
        self.pattern_amount.setRange(1, 10000)
        self.pattern_amount.setValue(150)
        self.pattern_amount.setMinimumHeight(32)
        pattern_row.addWidget(self.pattern_amount)
        pattern_row.addWidget(QLabel("MCC:"))
        self.pattern_mcc = QComboBox()
        self.pattern_mcc.addItems(["5411 - Grocery", "5912 - Pharmacy", "5999 - Retail", "5944 - Jewelry", "4812 - Telecom", "5732 - Electronics"])
        self.pattern_mcc.setMinimumHeight(32)
        pattern_row.addWidget(self.pattern_mcc)
        predict_btn = QPushButton("Predict")
        predict_btn.setMinimumHeight(32)
        predict_btn.setStyleSheet("background: #9c27b0; color: white; border: none; border-radius: 6px; padding: 0 14px;")
        predict_btn.clicked.connect(self._predict_pattern)
        pattern_row.addWidget(predict_btn)
        pattern_layout.addLayout(pattern_row)
        self.pattern_result = QLabel("Enter BIN above, set amount + MCC, then click Predict")
        self.pattern_result.setWordWrap(True)
        self.pattern_result.setStyleSheet("color: #889; padding: 6px;")
        pattern_layout.addWidget(self.pattern_result)
        layout.addWidget(pattern_group)

    def _lookup_bin(self):
        """Look up BIN in local database."""
        bin6 = self.bin_input.text().strip()[:6]
        if len(bin6) < 6:
            self.bin_result.setPlainText("⚠️ Enter at least 6 digits")
            return
        try:
            info = self.validator.lookup_bin(bin6)
            if info:
                text = f"═══ BIN LOOKUP: {bin6} ═══\n\n"
                text += f"  Bank:      {info.get('bank', 'Unknown')}\n"
                text += f"  Country:   {info.get('country', 'Unknown')}\n"
                text += f"  Type:      {info.get('type', 'Unknown')}\n"
                text += f"  Level:     {info.get('level', 'Unknown')}\n"
                text += f"  Network:   {'Visa' if bin6[0] == '4' else 'Mastercard' if bin6[0] == '5' else 'Amex' if bin6[:2] in ('34','37') else 'Other'}\n"
                text += f"\n  Luhn Prefix Valid: ✅\n"
            else:
                text = f"BIN {bin6} not found in local database.\n"
                text += f"Network: {'Visa' if bin6[0] == '4' else 'Mastercard' if bin6[0] == '5' else 'Amex' if bin6[:2] in ('34','37') else 'Discover' if bin6[:4] == '6011' else 'Unknown'}\n"
            self.bin_result.setPlainText(text)
        except Exception as e:
            self.bin_result.setPlainText(f"Error: {e}")

    def _score_bin(self):
        """Score BIN using BINScoringEngine."""
        bin6 = self.bin_input.text().strip()[:6]
        if len(bin6) < 6:
            self.bin_result.setPlainText("⚠️ Enter at least 6 digits")
            return
        try:
            scorer = BINScoringEngine()
            score = scorer.score_bin(bin6)
            text = f"═══ BIN INTELLIGENCE SCORE: {bin6} ═══\n\n"
            text += f"  Overall Score:     {score.overall_score:.0f}/100\n"
            text += f"  Success Rate:      {score.success_rate_estimate}\n"
            text += f"  Velocity Limit:    {score.velocity_limit}\n"
            text += f"  3DS Likelihood:    {score.three_ds_likelihood}\n"
            text += f"  AVS Strictness:    {score.avs_strictness}\n"
            text += f"  Fraud Score Risk:  {score.fraud_score_risk}\n"
            text += f"  Best Targets:      {', '.join(score.best_targets[:5])}\n"
            text += f"  Avoid Targets:     {', '.join(score.avoid_targets[:3])}\n"
            text += f"  Max Single Amount: ${score.max_single_amount:.0f}\n"
            text += f"\n{'─'*50}\n"
            rec = scorer.get_target_recommendation(bin6, self.pattern_amount.value())
            text += f"\n  Target Rec for ${self.pattern_amount.value()}:\n"
            text += f"    Recommended: {rec.get('recommended_target', 'N/A')}\n"
            text += f"    Strategy:    {rec.get('strategy', 'N/A')}\n"
            text += f"    Risk Level:  {rec.get('risk_level', 'N/A')}\n"
            self.bin_result.setPlainText(text)
        except Exception as e:
            self.bin_result.setPlainText(f"Error scoring BIN: {e}")

    def _predict_pattern(self):
        """Predict if transaction matches bank's fraud model."""
        bin6 = self.bin_input.text().strip()[:6]
        if len(bin6) < 6:
            self.pattern_result.setText("⚠️ Enter BIN first")
            return
        try:
            if ENHANCED_AVAILABLE:
                predictor = IssuingBankPatternPredictor()
                mcc = self.pattern_mcc.currentText().split(" - ")[0].strip()
                amount = self.pattern_amount.value()
                prediction = predictor.predict(bin6, amount=amount, mcc=mcc)
                color = "#00ff88" if prediction.in_pattern else "#ff4444"
                conf = f"{prediction.confidence*100:.0f}%"
                self.pattern_result.setText(
                    f"<b style='color:{color}'>{'✅ IN PATTERN' if prediction.in_pattern else '⚠️ OUT OF PATTERN'}</b> "
                    f"(confidence: {conf}) — {prediction.recommendation}"
                )
            else:
                self.pattern_result.setText("⚠️ cerberus_enhanced module not available")
        except Exception as e:
            self.pattern_result.setText(f"Error: {e}")

    # ═══════════════════════════════════════════════════════════════════
    # TAB 3: TARGET DISCOVERY
    # ═══════════════════════════════════════════════════════════════════

    def _build_target_tab(self):
        """Target discovery — merchant database + auto-discovery."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        self.tabs.addTab(tab, "🎯 Targets")

        # Filter controls
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Category:"))
        self.target_category = QComboBox()
        self.target_category.addItems(["All", "Gift Cards", "Digital Goods", "Electronics", "Fashion", "Crypto", "Services", "Subscriptions"])
        self.target_category.setMinimumHeight(32)
        self.target_category.currentTextChanged.connect(self._filter_targets)
        filter_row.addWidget(self.target_category)

        filter_row.addWidget(QLabel("Difficulty:"))
        self.target_difficulty = QComboBox()
        self.target_difficulty.addItems(["All", "Easy", "Medium", "Hard"])
        self.target_difficulty.setMinimumHeight(32)
        self.target_difficulty.currentTextChanged.connect(self._filter_targets)
        filter_row.addWidget(self.target_difficulty)

        filter_row.addWidget(QLabel("Max Amount $:"))
        self.target_max_amount = QSpinBox()
        self.target_max_amount.setRange(0, 50000)
        self.target_max_amount.setValue(5000)
        self.target_max_amount.setMinimumHeight(32)
        filter_row.addWidget(self.target_max_amount)

        load_btn = QPushButton("📋 Load Database")
        load_btn.setMinimumHeight(32)
        load_btn.setStyleSheet("background: #3A75C4; color: white; border: none; border-radius: 6px; padding: 0 14px; font-weight: bold;")
        load_btn.clicked.connect(self._load_target_database)
        filter_row.addWidget(load_btn)
        layout.addLayout(filter_row)

        # Target table
        self.target_table = QTableWidget()
        self.target_table.setColumnCount(8)
        self.target_table.setHorizontalHeaderLabels(["Domain", "Name", "Category", "Difficulty", "PSP", "3DS", "Max $", "Success %"])
        self.target_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.target_table.setAlternatingRowColors(True)
        self.target_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.target_table.setMinimumHeight(250)
        layout.addWidget(self.target_table)

        # Auto-discovery section
        disco_group = QGroupBox("🔎 Auto-Discovery (Google Dorking)")
        disco_layout = QVBoxLayout(disco_group)
        disco_row = QHBoxLayout()
        self.disco_engine = QComboBox()
        self.disco_engine.addItems(["google", "bing", "duckduckgo"])
        self.disco_engine.setMinimumHeight(32)
        disco_row.addWidget(QLabel("Engine:"))
        disco_row.addWidget(self.disco_engine)
        self.disco_max = QSpinBox()
        self.disco_max.setRange(10, 500)
        self.disco_max.setValue(100)
        self.disco_max.setMinimumHeight(32)
        disco_row.addWidget(QLabel("Max sites:"))
        disco_row.addWidget(self.disco_max)
        disco_btn = QPushButton("🚀 Discover New Targets")
        disco_btn.setMinimumHeight(32)
        disco_btn.setStyleSheet("background: #E6A817; color: white; border: none; border-radius: 6px; padding: 0 14px; font-weight: bold;")
        disco_btn.clicked.connect(self._run_discovery)
        disco_row.addWidget(disco_btn)
        disco_layout.addLayout(disco_row)
        self.disco_result = QPlainTextEdit()
        self.disco_result.setReadOnly(True)
        self.disco_result.setFont(QFont("JetBrains Mono", 9))
        self.disco_result.setMinimumHeight(200)
        self.disco_result.setPlaceholderText("Discovery results will appear here...")
        disco_layout.addWidget(self.disco_result)
        layout.addWidget(disco_group)

        # Auto-load on tab creation
        QTimer.singleShot(100, self._load_target_database)

    def _load_target_database(self):
        """Load merchant database into table."""
        try:
            if not DISCOVERY_AVAILABLE:
                self.target_table.setRowCount(1)
                self.target_table.setItem(0, 0, QTableWidgetItem("target_discovery module not available"))
                return
            sites = MERCHANT_DATABASE
            self._all_targets = sites
            self._filter_targets()
        except Exception as e:
            self.disco_result.setPlainText(f"Error loading database: {e}")

    def _filter_targets(self):
        """Filter target table by category and difficulty."""
        if not hasattr(self, '_all_targets'):
            return
        cat = self.target_category.currentText()
        diff = self.target_difficulty.currentText()
        filtered = []
        for site in self._all_targets:
            if cat != "All" and cat.lower().replace(" ", "_") not in str(getattr(site, 'category', '')).lower():
                continue
            if diff != "All" and diff.lower() not in str(getattr(site, 'difficulty', '')).lower():
                continue
            filtered.append(site)

        self.target_table.setRowCount(len(filtered))
        for i, site in enumerate(filtered):
            self.target_table.setItem(i, 0, QTableWidgetItem(getattr(site, 'domain', str(site))))
            self.target_table.setItem(i, 1, QTableWidgetItem(getattr(site, 'name', '')))
            self.target_table.setItem(i, 2, QTableWidgetItem(str(getattr(site, 'category', '')).split('.')[-1]))
            self.target_table.setItem(i, 3, QTableWidgetItem(str(getattr(site, 'difficulty', '')).split('.')[-1]))
            self.target_table.setItem(i, 4, QTableWidgetItem(str(getattr(site, 'psp', '')).split('.')[-1]))
            self.target_table.setItem(i, 5, QTableWidgetItem(getattr(site, 'three_ds', 'unknown')))
            self.target_table.setItem(i, 6, QTableWidgetItem(f"${getattr(site, 'max_amount', 0):,.0f}"))
            rate = getattr(site, 'success_rate', 0)
            rate_item = QTableWidgetItem(f"{rate*100:.0f}%" if isinstance(rate, float) else str(rate))
            if isinstance(rate, float) and rate >= 0.8:
                rate_item.setForeground(QBrush(QColor("#00ff88")))
            elif isinstance(rate, float) and rate >= 0.5:
                rate_item.setForeground(QBrush(QColor("#ffaa00")))
            else:
                rate_item.setForeground(QBrush(QColor("#ff4444")))
            self.target_table.setItem(i, 7, rate_item)

    def _run_discovery(self):
        """Run auto-discovery via Google dorking in a background thread."""
        if not DISCOVERY_AVAILABLE:
            self.disco_result.setPlainText("⚠️ target_discovery module not available")
            return
        
        # Prevent double-click
        if hasattr(self, '_disco_running') and self._disco_running:
            return
        self._disco_running = True
        
        engine = self.disco_engine.currentText()
        max_sites = self.disco_max.value()
        self.disco_result.setPlainText(
            f"🔍 Running auto-discovery ({len(DISCOVERY_DORKS)} dork queries, engine={engine})...\n"
            f"   Target: {max_sites} sites. This may take 2-5 minutes.\n"
            f"   Do NOT close this tab."
        )
        
        import threading
        thread = threading.Thread(
            target=self._do_discovery_worker,
            args=(engine, max_sites),
            daemon=True
        )
        thread.start()

    def _do_discovery_worker(self, engine, max_sites):
        """Background worker for discovery — runs off the main thread."""
        try:
            disco = AutoDiscovery()
            results = disco.discover_sites(
                engine=engine,
                max_per_query=max_sites,
                auto_probe=False
            )
            # Build result text
            text = f"═══ DISCOVERED {len(results)} NEW TARGETS ═══\n\n"
            # Group by category
            by_cat = {}
            for r in results:
                cat = r.get('expected_category', 'misc')
                by_cat.setdefault(cat, []).append(r)
            
            for cat, sites in sorted(by_cat.items()):
                text += f"── {cat.upper()} ({len(sites)} sites) ──\n"
                for r in sites:
                    domain = r.get('domain', '?')
                    classification = r.get('classification', 'unprobed')
                    psp = r.get('expected_psp', '?')
                    text += f"  {domain:40s}  [{classification:20s}]  PSP: {psp}\n"
                text += "\n"
            
            text += f"\n{'═'*60}\nTotal: {len(results)} sites across {len(by_cat)} categories"
            
            # Update GUI from main thread via QTimer
            from PyQt6.QtCore import QMetaObject, Qt, Q_ARG
            QMetaObject.invokeMethod(
                self.disco_result, "setPlainText",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(str, text)
            )
        except Exception as e:
            try:
                from PyQt6.QtCore import QMetaObject, Qt, Q_ARG
                QMetaObject.invokeMethod(
                    self.disco_result, "setPlainText",
                    Qt.ConnectionType.QueuedConnection,
                    Q_ARG(str, f"Discovery error: {e}\n\nThis may be caused by:\n"
                          f"  - No internet connection\n"
                          f"  - curl not installed\n"
                          f"  - Search engine blocking requests\n\n"
                          f"Try a different engine (bing/duckduckgo) or check connectivity.")
                )
            except Exception:
                pass
        finally:
            self._disco_running = False

    # ═══════════════════════════════════════════════════════════════════
    # TAB 4: CARD QUALITY GRADER
    # ═══════════════════════════════════════════════════════════════════

    def _build_quality_tab(self):
        """Card quality grading — combines BIN + AVS + OSINT + Geo."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        self.tabs.addTab(tab, "⭐ Quality")

        # Card info input
        card_group = QGroupBox("💳 Card + Billing Info")
        card_layout = QFormLayout(card_group)
        self.q_bin = QLineEdit()
        self.q_bin.setPlaceholderText("First 6 digits")
        self.q_bin.setMaxLength(8)
        card_layout.addRow("BIN:", self.q_bin)
        self.q_name = QLineEdit()
        self.q_name.setPlaceholderText("John Smith")
        card_layout.addRow("Cardholder:", self.q_name)
        self.q_address = QLineEdit()
        self.q_address.setPlaceholderText("123 Main St")
        card_layout.addRow("Address:", self.q_address)
        self.q_city = QLineEdit()
        self.q_city.setPlaceholderText("New York")
        card_layout.addRow("City:", self.q_city)
        self.q_state = QLineEdit()
        self.q_state.setPlaceholderText("NY")
        self.q_state.setMaxLength(2)
        card_layout.addRow("State:", self.q_state)
        self.q_zip = QLineEdit()
        self.q_zip.setPlaceholderText("10001")
        self.q_zip.setMaxLength(10)
        card_layout.addRow("ZIP:", self.q_zip)
        self.q_phone = QLineEdit()
        self.q_phone.setPlaceholderText("(212) 555-1234")
        card_layout.addRow("Phone:", self.q_phone)
        layout.addWidget(card_group)

        # Action buttons
        btn_row = QHBoxLayout()
        avs_btn = QPushButton("🏠 Check AVS")
        avs_btn.setMinimumHeight(36)
        avs_btn.setStyleSheet("background: #3A75C4; color: white; border: none; border-radius: 6px; padding: 0 14px; font-weight: bold;")
        avs_btn.clicked.connect(self._check_avs)
        btn_row.addWidget(avs_btn)

        osint_btn = QPushButton("🔎 OSINT Checklist")
        osint_btn.setMinimumHeight(36)
        osint_btn.setStyleSheet("background: #9c27b0; color: white; border: none; border-radius: 6px; padding: 0 14px; font-weight: bold;")
        osint_btn.clicked.connect(self._generate_osint)
        btn_row.addWidget(osint_btn)

        grade_btn = QPushButton("⭐ Grade Card")
        grade_btn.setMinimumHeight(36)
        grade_btn.setStyleSheet("background: #E6A817; color: white; border: none; border-radius: 6px; padding: 0 14px; font-weight: bold;")
        grade_btn.clicked.connect(self._grade_card)
        btn_row.addWidget(grade_btn)

        geo_btn = QPushButton("🌍 Geo Check")
        geo_btn.setMinimumHeight(36)
        geo_btn.setStyleSheet("background: #4caf50; color: white; border: none; border-radius: 6px; padding: 0 14px; font-weight: bold;")
        geo_btn.clicked.connect(self._check_geo)
        btn_row.addWidget(geo_btn)
        layout.addLayout(btn_row)

        # Result display
        self.quality_result = QPlainTextEdit()
        self.quality_result.setReadOnly(True)
        self.quality_result.setFont(QFont("JetBrains Mono", 10))
        self.quality_result.setPlaceholderText("Fill in card + billing info above, then use the analysis tools...")
        layout.addWidget(self.quality_result)

    def _check_avs(self):
        """Run AVS pre-verification."""
        if not ENHANCED_AVAILABLE:
            self.quality_result.setPlainText("⚠️ cerberus_enhanced module not available")
            return
        try:
            avs = AVSEngine()
            result = avs.check_avs(
                card_billing_address=self.q_address.text(),
                card_billing_zip=self.q_zip.text(),
                card_billing_state=self.q_state.text(),
                target_address=self.q_address.text(),
                target_zip=self.q_zip.text()
            )
            text = f"═══ AVS PRE-CHECK ═══\n\n"
            text += f"  AVS Code:      {result.avs_code.value} ({result.avs_code.name})\n"
            text += f"  Street Match:  {'✅' if result.street_match else '❌'}\n"
            text += f"  ZIP Match:     {'✅' if result.zip_match else '❌'}\n"
            text += f"  State Valid:   {'✅' if result.state_valid else '❌'}\n"
            text += f"  Confidence:    {result.confidence*100:.0f}%\n"
            self.quality_result.setPlainText(text)
        except Exception as e:
            self.quality_result.setPlainText(f"AVS Error: {e}")

    def _generate_osint(self):
        """Generate OSINT verification checklist."""
        if not ENHANCED_AVAILABLE:
            self.quality_result.setPlainText("⚠️ cerberus_enhanced module not available")
            return
        try:
            osint = OSINTVerifier()
            checklist = osint.generate_verification_checklist(
                name=self.q_name.text(),
                address=self.q_address.text(),
                city=self.q_city.text(),
                state=self.q_state.text(),
                zip_code=self.q_zip.text(),
                phone=self.q_phone.text()
            )
            text = f"═══ OSINT VERIFICATION CHECKLIST ═══\n\n"
            for source, info in checklist.get('sources', {}).items():
                text += f"  [{source.upper()}]\n"
                text += f"    URL:   {info.get('url', 'N/A')}\n"
                text += f"    Query: {info.get('query', 'N/A')}\n"
                text += f"    Check: {', '.join(info.get('checks', []))}\n\n"
            text += f"{'─'*50}\n"
            text += f"  Total Sources: {checklist.get('total_sources', 0)}\n"
            text += f"  Priority: {checklist.get('priority_order', 'N/A')}\n"
            self.quality_result.setPlainText(text)
        except Exception as e:
            self.quality_result.setPlainText(f"OSINT Error: {e}")

    def _grade_card(self):
        """Grade card quality using CardQualityGrader."""
        if not ENHANCED_AVAILABLE:
            self.quality_result.setPlainText("⚠️ cerberus_enhanced module not available")
            return
        try:
            grader = CardQualityGrader()
            bin6 = self.q_bin.text().strip()[:6]
            if len(bin6) < 6:
                self.quality_result.setPlainText("⚠️ Enter BIN first")
                return
            report = grader.grade_card(
                bin_number=bin6,
                billing_address=self.q_address.text(),
                billing_zip=self.q_zip.text(),
                billing_state=self.q_state.text(),
                cardholder_name=self.q_name.text()
            )
            grade_colors = {"PREMIUM": "🟢", "DEGRADED": "🟡", "LOW": "🔴"}
            text = f"═══ CARD QUALITY GRADE ═══\n\n"
            text += f"  Grade:           {grade_colors.get(report.grade.value, '⚪')} {report.grade.value}\n"
            text += f"  Success Rate:    {report.success_rate_estimate}\n"
            text += f"  BIN Score:       {report.bin_score:.0f}/100\n"
            text += f"  AVS Score:       {report.avs_score:.0f}/100\n"
            text += f"  Geo Score:       {report.geo_score:.0f}/100\n"
            text += f"  OSINT Score:     {report.osint_score:.0f}/100\n"
            text += f"\n  Recommendation:\n    {report.recommendation}\n"
            self.quality_result.setPlainText(text)
        except Exception as e:
            self.quality_result.setPlainText(f"Grading Error: {e}")

    def _check_geo(self):
        """Check geographic consistency."""
        if not ENHANCED_AVAILABLE:
            self.quality_result.setPlainText("⚠️ cerberus_enhanced module not available")
            return
        try:
            geo = GeoMatchChecker()
            state = self.q_state.text().strip().upper()
            result = geo.check_geo_consistency(
                billing_state=state,
                exit_ip_state=None,
                browser_timezone=""
            )
            text = f"═══ GEO CONSISTENCY CHECK ═══\n\n"
            text += f"  Billing State:    {state}\n"
            text += f"  Expected TZ:      {result.get('expected_timezone', 'N/A')}\n"
            text += f"  Geo Match:        {'✅' if result.get('geo_match') else '⚠️ Check proxy'}\n"
            text += f"  Recommendation:   {result.get('recommendation', 'N/A')}\n"
            self.quality_result.setPlainText(text)
        except Exception as e:
            self.quality_result.setPlainText(f"Geo Error: {e}")

    def apply_dark_theme(self):
        """Apply Enterprise HRUX theme from centralized theme module."""
        try:
            from titan_enterprise_theme import apply_enterprise_theme
            apply_enterprise_theme(self)
        except ImportError:
            pass  # Fallback: no theme applied
    
    def validate_card(self):
        """Start card validation"""
        raw_input = self.card_input.text().strip()
        
        if not raw_input:
            QMessageBox.warning(self, "Input Required", "Please enter card details")
            return
        
        # Parse card
        card = self.validator.parse_card_input(raw_input)
        
        if not card:
            self.show_result_error("Invalid card format")
            return
        
        # Pre-flight Luhn check
        if not card.is_valid_luhn:
            self.show_result(ValidationResult(
                card=card,
                status=CardStatus.DEAD,
                message="Invalid card number (Luhn check failed)"
            ))
            return
        
        # Disable UI
        self.validate_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.status_text.setText("VALIDATING...")
        self.status_text.setStyleSheet("color: #FFC107;")
        self.traffic_light.setText("⏳")
        
        # Start worker
        self.worker = ValidateWorker(self.validator, card)
        self.worker.finished.connect(self.on_validation_complete)
        self.worker.start()
    
    def on_validation_complete(self, result):
        """Handle validation result"""
        self.validate_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        if isinstance(result, Exception):
            self.show_result_error(str(result))
            self.strategy_btn.setVisible(False)
        else:
            self.show_result(result)
            self.add_to_history(result)
            
            # If card is LIVE, auto-generate drain strategy
            if result.status == CardStatus.LIVE and result.card:
                card_num = result.card.number if hasattr(result.card, 'number') else ''
                if card_num and len(card_num) >= 6:
                    self._last_live_bin = card_num[:6]
                    try:
                        self._last_drain_plan = generate_drain_plan(self._last_live_bin)
                        plan_text = format_drain_plan(self._last_drain_plan)
                        self.strategy_btn.setVisible(True)
                        self.strategy_btn.setText(
                            f"Extraction Strategy — ${self._last_drain_plan.total_drain_target:,.0f} "
                            f"({self._last_drain_plan.cashout_efficiency*100:.0f}% cashout)"
                        )
                    except Exception as e:
                        self.strategy_btn.setVisible(False)
                        self._last_drain_plan = None
                else:
                    self.strategy_btn.setVisible(False)
            else:
                self.strategy_btn.setVisible(False)
    
    def show_result(self, result: ValidationResult):
        """Display validation result with traffic light"""
        status_config = {
            CardStatus.LIVE: ("🟢", "LIVE", "#4CAF50", "#1b5e20"),
            CardStatus.DEAD: ("🔴", "DEAD", "#f44336", "#b71c1c"),
            CardStatus.UNKNOWN: ("🟡", "UNKNOWN", "#FFC107", "#ff8f00"),
            CardStatus.RISKY: ("🟠", "RISKY", "#FF9800", "#e65100"),
        }
        
        emoji, text, color, border_color = status_config.get(
            result.status, 
            ("⚪", "ERROR", "#888", "#444")
        )
        
        self.traffic_light.setText(emoji)
        self.status_text.setText(text)
        self.status_text.setStyleSheet(f"color: {color};")
        self.detail_text.setText(result.message)
        
        self.traffic_frame.setStyleSheet(f"""
            QFrame {{
                background-color: #2d2d2d;
                border: 2px solid {border_color};
                border-radius: 12px;
            }}
        """)
    
    def show_result_error(self, message: str):
        """Show error state"""
        self.traffic_light.setText("❌")
        self.status_text.setText("ERROR")
        self.status_text.setStyleSheet("color: #f44336;")
        self.detail_text.setText(message)
        
        self.traffic_frame.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border: 2px solid #b71c1c;
                border-radius: 12px;
            }
        """)
    
    def add_to_history(self, result: ValidationResult):
        """Add result to history table"""
        self.history.append(result)
        
        row = self.history_table.rowCount()
        self.history_table.insertRow(row)
        
        # Card (masked)
        card_item = QTableWidgetItem(result.card.masked())
        card_item.setFont(QFont("Consolas", 10))
        self.history_table.setItem(row, 0, card_item)
        
        # Status with color
        status_item = QTableWidgetItem(f"{result.traffic_light} {result.status.value}")
        status_colors = {
            CardStatus.LIVE: QColor("#4CAF50"),
            CardStatus.DEAD: QColor("#f44336"),
            CardStatus.UNKNOWN: QColor("#FFC107"),
            CardStatus.RISKY: QColor("#FF9800"),
        }
        status_item.setForeground(QBrush(status_colors.get(result.status, QColor("#888"))))
        self.history_table.setItem(row, 1, status_item)
        
        # Card Type (Visa/MC/Amex/Discover)
        card_type_str = result.card.card_type.value.upper() if hasattr(result.card, 'card_type') else "?"
        self.history_table.setItem(row, 2, QTableWidgetItem(card_type_str))
        
        # Card Tier (from BIN database)
        bin_info = CerberusValidator.BIN_DATABASE.get(result.card.bin, {})
        tier_str = bin_info.get("level", "—").title()
        self.history_table.setItem(row, 3, QTableWidgetItem(tier_str))
        
        # Bank
        self.history_table.setItem(row, 4, QTableWidgetItem(result.bank_name or "Unknown"))
        
        # Country
        self.history_table.setItem(row, 5, QTableWidgetItem(result.country or "Unknown"))
        
        # Time
        self.history_table.setItem(row, 6, QTableWidgetItem(
            result.validated_at.strftime("%H:%M:%S")
        ))
        
        # Update stats
        self.update_stats()
        
        # Scroll to bottom
        self.history_table.scrollToBottom()
    
    def update_stats(self):
        """Update statistics label"""
        live = sum(1 for r in self.history if r.status == CardStatus.LIVE)
        dead = sum(1 for r in self.history if r.status == CardStatus.DEAD)
        unknown = sum(1 for r in self.history if r.status in (CardStatus.UNKNOWN, CardStatus.RISKY))
        
        self.stats_label.setText(
            f"<span style='color: #4CAF50;'>Live: {live}</span> | "
            f"<span style='color: #f44336;'>Dead: {dead}</span> | "
            f"<span style='color: #FFC107;'>Unknown: {unknown}</span>"
        )
    
    def show_drain_strategy(self):
        """Show full drain strategy in dialog"""
        if not self._last_drain_plan:
            return
        
        plan_text = format_drain_plan(self._last_drain_plan)
        dialog = DrainPlanDialog(plan_text, self)
        dialog.setStyleSheet(self.styleSheet())
        dialog.exec()
    
    def clear_input(self):
        """Clear card input and reset display"""
        self.card_input.clear()
        self.traffic_light.setText("⚪")
        self.status_text.setText("READY")
        self.status_text.setStyleSheet("color: #888;")
        self.detail_text.setText("Paste card and click Validate")
        self.traffic_frame.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border: 2px solid #444;
                border-radius: 12px;
            }
        """)
        self.strategy_btn.setVisible(False)
        self._last_live_bin = None
        self._last_drain_plan = None
        self.card_input.setFocus()
    
    def clear_history(self):
        """Clear validation history"""
        self.history.clear()
        self.history_table.setRowCount(0)
        self.update_stats()
    
    def configure_keys(self):
        """Open key configuration dialog"""
        dialog = KeyConfigDialog(self)
        dialog.setStyleSheet(self.styleSheet())
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            keys = dialog.get_keys()
            for key in keys:
                self.validator.add_key(key)
            
            if keys:
                QMessageBox.information(
                    self, 
                    "Keys Configured",
                    f"Added {len(keys)} API key(s) for live validation."
                )
    
    def export_results(self):
        """Export validation history to file"""
        if not self.history:
            QMessageBox.information(self, "Export", "No results to export.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Results", "cerberus_results.txt",
            "Text Files (*.txt);;CSV Files (*.csv)"
        )
        if not path:
            return
        try:
            with open(path, "w") as f:
                if path.endswith(".csv"):
                    f.write("Card,Status,Type,Tier,Bank,Country,Time,Message\n")
                    for r in self.history:
                        bin_info = CerberusValidator.BIN_DATABASE.get(r.card.bin, {})
                        tier = bin_info.get("level", "unknown")
                        f.write(f"{r.card.masked()},{r.status.value},{r.card.card_type.value},{tier},{r.bank_name or ''},{r.country or ''},{r.validated_at.strftime('%H:%M:%S')},{r.message}\n")
                else:
                    for r in self.history:
                        bin_info = CerberusValidator.BIN_DATABASE.get(r.card.bin, {})
                        tier = bin_info.get("level", "unknown")
                        f.write(f"{r.traffic_light} {r.card.masked()} | {r.status.value} | {r.card.card_type.value.upper()} {tier} | {r.bank_name or '?'} ({r.country or '?'}) | {r.message}\n")
            QMessageBox.information(self, "Export", f"Exported {len(self.history)} results to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))
    
    def bulk_validate(self):
        """Bulk validate cards from a text input dialog"""
        from PyQt6.QtWidgets import QInputDialog
        text, ok = QInputDialog.getMultiLineText(
            self, "Bulk Validate",
            "Paste cards (one per line):\nFormats: PAN|MM|YY|CVV or PAN MM YY CVV",
            ""
        )
        if not ok or not text.strip():
            return
        lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
        parsed = []
        for line in lines:
            card = self.validator.parse_card_input(line)
            if card:
                parsed.append(card)
        if not parsed:
            QMessageBox.warning(self, "Bulk Validate", "No valid cards could be parsed from input.")
            return
        
        QMessageBox.information(
            self, "Bulk Validate",
            f"Parsed {len(parsed)} cards from {len(lines)} lines.\n"
            f"Validation will run sequentially with rate limiting.\n"
            f"Results will appear in the history table."
        )
        
        # Validate each card sequentially via the existing worker
        self._bulk_queue = list(parsed)
        self._bulk_validate_next()
    
    def _bulk_validate_next(self):
        """Process next card in bulk queue"""
        if not hasattr(self, '_bulk_queue') or not self._bulk_queue:
            return
        card = self._bulk_queue.pop(0)
        # Populate input field for visual feedback
        self.card_input.setText(card.masked())
        self.validate_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        
        self.worker = ValidateWorker(self.validator, card)
        self.worker.finished.connect(self._on_bulk_result)
        self.worker.start()
    
    def _on_bulk_result(self, result):
        """Handle bulk validation result"""
        self.validate_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        if isinstance(result, Exception):
            self.show_result_error(str(result))
        else:
            self.show_result(result)
            self.add_to_history(result)
        # Continue with next card after a short delay
        if hasattr(self, '_bulk_queue') and self._bulk_queue:
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(1200, self._bulk_validate_next)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    try:
        from titan_enterprise_theme import apply_enterprise_theme_to_app
        apply_enterprise_theme_to_app(app)
    except ImportError:
        pass

    splash = None
    try:
        from titan_splash import show_titan_splash
        splash = show_titan_splash(app, "ASSET VALIDATION ENGINE", "#3A75C4")
    except Exception:
        pass
    
    window = CerberusApp()
    window.show()
    if splash:
        splash.finish(window)
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
