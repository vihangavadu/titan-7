#!/usr/bin/env python3
"""
TITAN V8.0 MAXIMUM — Asset Validation & Risk Assessment
Card Validation GUI

╔═══════════════════════════════════════════════════════════════════╗
║  DEPRECATED in V8.1 — Use Operations Center (app_unified.py)    ║
║  All card validation features are in the OPERATION tab.          ║
║  Launch via: titan_launcher.py → Operations Center               ║
╚═══════════════════════════════════════════════════════════════════╝

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

# V7.5 AI Intelligence Engine
try:
    from ai_intelligence_engine import (
        analyze_bin, recon_target, advise_3ds, tune_behavior, get_ai_status, is_ai_available,
        record_decline, get_bin_decline_pattern, get_enriched_bin_context
    )
    from tls_parrot import TLSParrotEngine
    from ghost_motor_v6 import get_forter_safe_params, get_warmup_pattern
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False

# V7.5 Hardened Operation Engines
try:
    from transaction_monitor import DeclineDecoder, decode_decline
    DECLINE_DECODER_AVAILABLE = True
except ImportError:
    DECLINE_DECODER_AVAILABLE = False

try:
    from three_ds_strategy import (
        ThreeDSBypassEngine, get_3ds_bypass_score, get_3ds_bypass_plan,
        get_downgrade_attacks, get_psd2_exemptions, get_psp_vulnerabilities
    )
    BYPASS_ENGINE_AVAILABLE = True
except ImportError:
    BYPASS_ENGINE_AVAILABLE = False

try:
    from preflight_validator import PreFlightValidator, PreFlightReport
    PREFLIGHT_AVAILABLE = True
except ImportError:
    PREFLIGHT_AVAILABLE = False

try:
    from target_intelligence import (
        get_target_intel, get_antifraud_profile, get_processor_profile,
        estimate_card_freshness
    )
    from target_discovery import TargetDiscovery, recommend_sites
    from cerberus_enhanced import SilentValidationEngine
    INTEL_AVAILABLE = True
except ImportError:
    INTEL_AVAILABLE = False

# Velocity Guard — per-BIN attempt tracker
_velocity_tracker: dict = {}  # bin6 -> {attempts, last_attempt, declines}
VELOCITY_WARN  = 3
VELOCITY_BLOCK = 6


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
        self._success_tracker: dict = {}  # bin6 -> {attempts, successes}
        
        self.init_ui()
        self.apply_dark_theme()
    
    def init_ui(self):
        self.setWindowTitle("TITAN V8.0 — Asset Validation & Risk Assessment")
        try:
            from titan_icon import set_titan_icon
            set_titan_icon(self, "#00bcd4")
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
        header.setStyleSheet("color: #00bcd4; margin-bottom: 2px;")
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
        
        # Tab 5: AI Intelligence
        self._build_ai_tab()

        # Tab 6: Success Tracker
        self._build_tracker_tab()

        # Tab 7: Hardened Operations Planner
        self._build_ops_tab()

        # Tab 8: BIN → Target Matcher
        self._build_target_matcher_tab()
        
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
        footer = QLabel("TITAN V8.0 MAXIMUM | Asset Validation Engine")
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

    # ─── TAB 5: AI INTELLIGENCE ─────────────────────────────────────

    def _build_ai_tab(self):
        """AI-powered operation optimizer — BIN, target, pre-flight, amount, behavior."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)
        self.tabs.addTab(tab, "🧠 AI Intel")

        header = QLabel("🧠 AI OPERATION OPTIMIZER")
        header.setFont(QFont("JetBrains Mono", 13, QFont.Weight.Bold))
        header.setStyleSheet("color: #E6A817;")
        layout.addWidget(header)

        # Input group
        bin_group = QGroupBox("Operation Parameters")
        bin_form = QFormLayout(bin_group)
        self.ai_bin_input = QLineEdit()
        self.ai_bin_input.setPlaceholderText("BIN first 6 digits, e.g. 476173")
        bin_form.addRow("BIN:", self.ai_bin_input)
        self.ai_bin_target = QLineEdit()
        self.ai_bin_target.setPlaceholderText("Target domain, e.g. nike.com")
        bin_form.addRow("Target:", self.ai_bin_target)
        self.ai_bin_amount = QSpinBox()
        self.ai_bin_amount.setRange(1, 50000)
        self.ai_bin_amount.setValue(150)
        self.ai_bin_amount.setPrefix("$")
        bin_form.addRow("Amount:", self.ai_bin_amount)
        layout.addWidget(bin_group)

        # Row 1: Core analysis
        row1 = QHBoxLayout()
        for label, slot, bg, fg in [
            ("🔍 BIN ANALYSIS",  self._ai_analyze_bin,  "#E6A817", "#000"),
            ("🎯 TARGET RECON",  self._ai_recon_target, "#3A75C4", "#fff"),
            ("🛡️ 3DS STRATEGY", self._ai_3ds_advise,   "#9c27b0", "#fff"),
        ]:
            btn = QPushButton(label)
            btn.setMinimumHeight(36)
            btn.setStyleSheet(f"QPushButton{{background:{bg};color:{fg};font-weight:bold;border:none;border-radius:6px;padding:0 10px;}}QPushButton:hover{{opacity:0.85;}}")
            btn.clicked.connect(slot)
            row1.addWidget(btn)
        layout.addLayout(row1)

        # Row 2: NEW high-success features
        row2 = QHBoxLayout()
        preflight_btn = QPushButton("✅ PRE-FLIGHT GO/NO-GO")
        preflight_btn.setMinimumHeight(36)
        preflight_btn.setStyleSheet("QPushButton{background:#1b5e20;color:#00ff88;font-weight:bold;border:1px solid #00ff88;border-radius:6px;padding:0 10px;}QPushButton:hover{background:#2e7d32;}")
        preflight_btn.clicked.connect(self._ai_preflight)
        row2.addWidget(preflight_btn)

        amount_btn = QPushButton("� AMOUNT OPTIMIZER")
        amount_btn.setMinimumHeight(36)
        amount_btn.setStyleSheet("QPushButton{background:#1a237e;color:#82b1ff;font-weight:bold;border:1px solid #3949ab;border-radius:6px;padding:0 10px;}QPushButton:hover{background:#283593;}")
        amount_btn.clicked.connect(self._ai_optimize_amount)
        row2.addWidget(amount_btn)

        behavior_btn = QPushButton("🤖 BEHAVIORAL TUNING")
        behavior_btn.setMinimumHeight(36)
        behavior_btn.setStyleSheet("QPushButton{background:#4a148c;color:#ea80fc;font-weight:bold;border:1px solid #7b1fa2;border-radius:6px;padding:0 10px;}QPushButton:hover{background:#6a1b9a;}")
        behavior_btn.clicked.connect(self._ai_tune_behavior)
        row2.addWidget(behavior_btn)
        layout.addLayout(row2)

        # Row 3: Ghost Motor + utility
        row3 = QHBoxLayout()
        for label, slot in [
            ("👻 Forter Params",  self._show_forter_params),
            ("🔥 Warmup Pattern", self._show_warmup_pattern),
            ("🚦 Velocity Check", self._check_velocity),
            ("⚡ AI Status",      self._show_ai_status),
        ]:
            btn = QPushButton(label)
            btn.setMinimumHeight(32)
            btn.setStyleSheet("QPushButton{background:#1C2330;color:#aaa;border:1px solid #333;border-radius:6px;padding:0 8px;}QPushButton:hover{color:#fff;border-color:#555;}")
            btn.clicked.connect(slot)
            row3.addWidget(btn)
        layout.addLayout(row3)

        self.ai_result = QTextEdit()
        self.ai_result.setReadOnly(True)
        self.ai_result.setFont(QFont("JetBrains Mono", 10))
        self.ai_result.setPlaceholderText(
            "AI Operation Optimizer — Powered by titan-mistral\n\n"
            "  ✅ Pre-Flight Go/No-Go  — combined BIN+target+amount pass/fail\n"
            "  💰 Amount Optimizer     — finds the sweet spot amount for max success\n"
            "  🤖 Behavioral Tuning   — per-target Ghost Motor evasion params\n"
            "  🔍 BIN Analysis        — AI risk score, success prediction\n"
            "  🎯 Target Recon        — fraud engine, PSP, friction level\n"
            "  🛡️ 3DS Strategy        — bypass approach and timing\n"
            "  � Velocity Check      — per-BIN attempt tracking and warnings\n\n"
            "Enter BIN + Target + Amount, then click any button."
        )
        layout.addWidget(self.ai_result)

    def _ai_analyze_bin(self):
        """AI BIN analysis."""
        if not AI_AVAILABLE:
            self.ai_result.setPlainText("AI Intelligence Engine not available.")
            return
        bin_num = self.ai_bin_input.text().strip()
        if not bin_num:
            self.ai_result.setPlainText("Enter a BIN number.")
            return
        self.ai_result.setPlainText(f"🔍 Analyzing BIN {bin_num}...")
        QApplication.processEvents()
        try:
            b = analyze_bin(bin_num, self.ai_bin_target.text().strip(), self.ai_bin_amount.value())
            text = f"AI BIN ANALYSIS: {b.bin_number}\n{'='*50}\n"
            text += f"  Bank: {b.bank_name} | Country: {b.country}\n"
            text += f"  Type: {b.card_type} {b.card_level} ({b.network})\n"
            text += f"  AI Score: {b.ai_score}/100 | Success: {b.success_prediction:.0%}\n"
            text += f"  Risk: {b.risk_level.value}\n"
            text += f"  Optimal: ${b.optimal_amount_range[0]:.0f}-${b.optimal_amount_range[1]:.0f}\n"
            text += f"  Timing: {b.timing_advice}\n"
            text += f"  Best targets: {', '.join(b.best_targets[:5])}\n"
            text += f"  Avoid: {', '.join(b.avoid_targets[:3])}\n"
            if b.risk_factors:
                text += f"\n  Risk factors:\n" + "\n".join(f"    • {r}" for r in b.risk_factors)
            text += f"\n\n  {b.strategic_notes}\n"
            text += f"\n  AI Powered: {b.ai_powered}"
            self.ai_result.setPlainText(text)
        except Exception as e:
            self.ai_result.setPlainText(f"Error: {e}")

    def _ai_recon_target(self):
        """AI target recon."""
        if not AI_AVAILABLE:
            self.ai_result.setPlainText("AI not available")
            return
        target = self.ai_bin_target.text().strip()
        if not target:
            self.ai_result.setPlainText("Enter a target domain.")
            return
        self.ai_result.setPlainText(f"🎯 Recon on {target}...")
        QApplication.processEvents()
        try:
            t = recon_target(target)
            text = f"AI TARGET RECON: {t.domain}\n{'='*50}\n"
            text += f"  Name: {t.name}\n"
            text += f"  Fraud Engine: {t.fraud_engine_guess}\n"
            text += f"  Payment PSP: {t.payment_processor_guess}\n"
            text += f"  Friction: {t.estimated_friction}\n"
            text += f"  3DS Probability: {t.three_ds_probability:.0%}\n"
            text += f"  Best cards: {', '.join(t.optimal_card_types)}\n"
            text += f"  Best countries: {', '.join(t.optimal_countries)}\n"
            if t.warmup_strategy:
                text += f"\n  Warmup:\n" + "\n".join(f"    {i+1}. {s}" for i, s in enumerate(t.warmup_strategy[:5]))
            if t.checkout_tips:
                text += f"\n\n  Tips:\n" + "\n".join(f"    • {tip}" for tip in t.checkout_tips[:5])
            text += f"\n\n  AI Powered: {t.ai_powered}"
            self.ai_result.setPlainText(text)
        except Exception as e:
            self.ai_result.setPlainText(f"Error: {e}")

    def _ai_3ds_advise(self):
        """AI 3DS bypass strategy."""
        if not AI_AVAILABLE:
            self.ai_result.setPlainText("AI not available")
            return
        self.ai_result.setPlainText("🛡️ Generating 3DS strategy...")
        QApplication.processEvents()
        try:
            s = advise_3ds(
                self.ai_bin_input.text().strip(),
                self.ai_bin_target.text().strip() or "unknown",
                self.ai_bin_amount.value()
            )
            text = f"AI 3DS BYPASS STRATEGY\n{'='*50}\n"
            text += f"  Approach: {s.recommended_approach}\n"
            text += f"  Success: {s.success_probability:.0%}\n"
            text += f"  Timing: {s.timing_window}\n"
            text += f"  Amount Strategy: {s.amount_strategy}\n"
            text += f"  Card Preference: {s.card_type_preference}\n"
            if s.checkout_flow:
                text += f"\n  Flow:\n" + "\n".join(f"    {i+1}. {step}" for i, step in enumerate(s.checkout_flow))
            text += f"\n\n  Fallback: {s.fallback_plan}\n"
            text += f"\n  AI Powered: {s.ai_powered}"
            self.ai_result.setPlainText(text)
        except Exception as e:
            self.ai_result.setPlainText(f"Error: {e}")

    def _show_forter_params(self):
        """Show Forter-safe Ghost Motor parameters."""
        if not AI_AVAILABLE:
            self.ai_result.setPlainText("Ghost Motor not available")
            return
        try:
            params = get_forter_safe_params()
            text = f"FORTER-SAFE GHOST MOTOR PARAMS\n{'='*50}\n\n"
            for k, v in params.items():
                text += f"  {k}: {v}\n"
            self.ai_result.setPlainText(text)
        except Exception as e:
            self.ai_result.setPlainText(f"Error: {e}")

    def _show_warmup_pattern(self):
        """Show pre-checkout warmup pattern."""
        if not AI_AVAILABLE:
            self.ai_result.setPlainText("Ghost Motor not available")
            return
        try:
            target = self.ai_bin_target.text().strip() or "general_ecommerce"
            pattern = get_warmup_pattern(target)
            text = f"WARMUP PATTERN: {target}\n{'='*50}\n\n"
            for k, v in pattern.items():
                text += f"  {k}: {v}\n"
            self.ai_result.setPlainText(text)
        except Exception as e:
            self.ai_result.setPlainText(f"Error: {e}")

    def _show_ai_status(self):
        """Show AI engine status."""
        if not AI_AVAILABLE:
            self.ai_result.setPlainText("AI Intelligence Engine not imported.")
            return
        try:
            status = get_ai_status()
            text = f"AI ENGINE STATUS\n{'='*50}\n\n"
            text += f"  Available: {'✅ ONLINE' if status['available'] else '❌ OFFLINE'}\n"
            text += f"  Provider: {status['provider']}\n"
            text += f"  Version: {status['version']}\n\n"
            if status['features']:
                text += f"  Features ({len(status['features'])}):\n"
                for f in status['features']:
                    text += f"    ✅ {f}\n"
            self.ai_result.setPlainText(text)
        except Exception as e:
            self.ai_result.setPlainText(f"Error: {e}")

    # ─── NEW: Pre-Flight Go/No-Go ────────────────────────────────────

    def _ai_preflight(self):
        """Combined BIN + target + amount go/no-go decision."""
        if not AI_AVAILABLE:
            self.ai_result.setPlainText("AI not available")
            return
        bin_num = self.ai_bin_input.text().strip()
        target  = self.ai_bin_target.text().strip() or "unknown"
        amount  = self.ai_bin_amount.value()
        if not bin_num:
            self.ai_result.setPlainText("Enter a BIN number.")
            return
        self.ai_result.setPlainText(f"✅ Running pre-flight: BIN {bin_num} → {target} ${amount}...")
        QApplication.processEvents()

        import threading, concurrent.futures
        def _worker():
            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
                    f_bin    = ex.submit(analyze_bin, bin_num, target, amount)
                    f_target = ex.submit(recon_target, target)
                    b = f_bin.result(timeout=90)
                    t = f_target.result(timeout=90)

                bin_score    = b.ai_score or 50
                success_pred = b.success_prediction or 0.5
                friction     = {"low": 0.9, "medium": 0.65, "high": 0.35}.get(t.estimated_friction, 0.5)
                three_ds_ok  = 1.0 - t.three_ds_probability

                bin6 = bin_num[:6]
                vel  = _velocity_tracker.get(bin6, {})
                vel_penalty = min(vel.get("declines", 0) * 0.08, 0.4)

                composite = (bin_score / 100 * 0.35
                             + success_pred * 0.30
                             + friction * 0.20
                             + three_ds_ok * 0.15
                             - vel_penalty)
                composite = max(0.0, min(1.0, composite))

                if composite >= 0.70:
                    verdict = "🟢 GO — HIGH CONFIDENCE"
                elif composite >= 0.50:
                    verdict = "🟡 PROCEED WITH CAUTION"
                else:
                    verdict = "🔴 NO-GO — HIGH RISK"

                text  = f"PRE-FLIGHT: {bin_num} → {target} ${amount}\n{'='*55}\n\n"
                text += f"  VERDICT: {verdict}\n"
                text += f"  Composite Score: {composite*100:.0f}/100\n\n"
                text += f"  ── BIN Intelligence ──\n"
                text += f"    Bank:           {b.bank_name}\n"
                text += f"    Risk Level:     {b.risk_level.value}\n"
                text += f"    AI Score:       {b.ai_score}/100\n"
                text += f"    Success Pred:   {b.success_prediction:.0%}\n"
                text += f"    Optimal Range:  ${b.optimal_amount_range[0]:.0f}–${b.optimal_amount_range[1]:.0f}\n"
                text += f"    Timing:         {b.timing_advice}\n\n"
                text += f"  ── Target Intelligence ──\n"
                text += f"    Fraud Engine:   {t.fraud_engine_guess}\n"
                text += f"    PSP:            {t.payment_processor_guess}\n"
                text += f"    Friction:       {t.estimated_friction}\n"
                text += f"    3DS Prob:       {t.three_ds_probability:.0%}\n"
                text += f"    Best Cards:     {', '.join(t.optimal_card_types)}\n"
                text += f"    Best Countries: {', '.join(t.optimal_countries)}\n"
                if t.warmup_strategy:
                    text += f"\n  ── Warmup Steps ──\n"
                    for i, s in enumerate(t.warmup_strategy[:4], 1):
                        text += f"    {i}. {s}\n"
                if vel.get("attempts", 0) > 0:
                    text += f"\n  ── Velocity Guard ──\n"
                    text += f"    Attempts:  {vel.get('attempts',0)}\n"
                    text += f"    Declines:  {vel.get('declines',0)}\n"
                    text += f"    Penalty:   -{vel_penalty*100:.0f}pts\n"
                if b.risk_factors:
                    text += f"\n  ── Risk Factors ──\n"
                    for rf in b.risk_factors[:4]:
                        text += f"    • {rf}\n"
                text += f"\n  AI Powered: {b.ai_powered}"

                from PyQt6.QtCore import QMetaObject, Qt, Q_ARG
                QMetaObject.invokeMethod(self.ai_result, "setPlainText",
                    Qt.ConnectionType.QueuedConnection, Q_ARG(str, text))
            except Exception as e:
                from PyQt6.QtCore import QMetaObject, Qt, Q_ARG
                QMetaObject.invokeMethod(self.ai_result, "setPlainText",
                    Qt.ConnectionType.QueuedConnection, Q_ARG(str, f"Pre-flight error: {e}"))

        threading.Thread(target=_worker, daemon=True).start()

    # ─── NEW: Amount Optimizer ───────────────────────────────────────

    def _ai_optimize_amount(self):
        """Find the sweet spot amount for maximum success rate."""
        if not AI_AVAILABLE:
            self.ai_result.setPlainText("AI not available")
            return
        bin_num = self.ai_bin_input.text().strip()
        target  = self.ai_bin_target.text().strip() or "unknown"
        if not bin_num:
            self.ai_result.setPlainText("Enter a BIN number.")
            return
        self.ai_result.setPlainText(f"💰 Optimizing amount for BIN {bin_num} → {target}...")
        QApplication.processEvents()

        import threading
        def _worker():
            try:
                from ai_intelligence_engine import _query_ollama_json
                prompt = (
                    f"You are a payment fraud analyst. Find the optimal transaction amount for maximum success.\n"
                    f"BIN: {bin_num}\nTarget: {target}\n\n"
                    f"Score each tier 0-100 for success probability:\n"
                    f"- micro ($1-$25): tests validity, minimal friction\n"
                    f"- low ($26-$75): below velocity triggers\n"
                    f"- medium ($76-$200): typical purchase range\n"
                    f"- high ($201-$500): may trigger 3DS\n"
                    f"- premium ($501-$1500): high scrutiny\n\n"
                    f"Respond ONLY with JSON:\n"
                    f'{{\"sweet_spot_amount\":0,\"sweet_spot_range\":[min,max],\"reasoning\":\"...\","'
                    f'"tiers\":{{\"micro\":0,\"low\":0,\"medium\":0,\"high\":0,\"premium\":0}},'
                    f'"avoid_amounts\":[],\"split_strategy\":\"...\"}}'
                )
                r = _query_ollama_json(prompt, task_type="bin_generation", timeout=60)
                if r and isinstance(r, dict):
                    sweet = r.get("sweet_spot_amount", 0)
                    rng   = r.get("sweet_spot_range", [0, 0])
                    tiers = r.get("tiers", {})
                    text  = f"AMOUNT OPTIMIZER: {bin_num} → {target}\n{'='*55}\n\n"
                    text += f"  💰 SWEET SPOT:    ${sweet}\n"
                    text += f"  📊 OPTIMAL RANGE: ${rng[0]}–${rng[1]}\n\n"
                    text += f"  ── Tier Scores ──\n"
                    for tier, score in tiers.items():
                        bar = "█" * int(score / 10) + "░" * (10 - int(score / 10))
                        text += f"    {tier:<10} {bar} {score}/100\n"
                    text += f"\n  Reasoning:      {r.get('reasoning','')}\n"
                    text += f"  Split Strategy: {r.get('split_strategy','')}\n"
                    avoid = r.get("avoid_amounts", [])
                    if avoid:
                        text += f"  Avoid:          {', '.join(f'${a}' for a in avoid[:5])}\n"
                    text += f"\n  → Amount set to ${sweet}"
                    if sweet > 0:
                        from PyQt6.QtCore import QMetaObject, Qt, Q_ARG
                        QMetaObject.invokeMethod(self.ai_bin_amount, "setValue",
                            Qt.ConnectionType.QueuedConnection, Q_ARG(int, int(sweet)))
                else:
                    text = "Amount optimizer: no AI response — try again."

                from PyQt6.QtCore import QMetaObject, Qt, Q_ARG
                QMetaObject.invokeMethod(self.ai_result, "setPlainText",
                    Qt.ConnectionType.QueuedConnection, Q_ARG(str, text))
            except Exception as e:
                from PyQt6.QtCore import QMetaObject, Qt, Q_ARG
                QMetaObject.invokeMethod(self.ai_result, "setPlainText",
                    Qt.ConnectionType.QueuedConnection, Q_ARG(str, f"Amount optimizer error: {e}"))

        threading.Thread(target=_worker, daemon=True).start()

    # ─── NEW: Behavioral Tuning ──────────────────────────────────────

    def _ai_tune_behavior(self):
        """Per-target Ghost Motor behavioral evasion params."""
        if not AI_AVAILABLE:
            self.ai_result.setPlainText("AI not available")
            return
        target = self.ai_bin_target.text().strip() or "general_ecommerce"
        self.ai_result.setPlainText(f"🤖 Tuning behavioral params for {target}...")
        QApplication.processEvents()

        import threading
        def _worker():
            try:
                result = tune_behavior(target)
                text  = f"BEHAVIORAL TUNING: {target}\n{'='*55}\n\n"
                text += f"  Fraud Engine:    {result.target_engine}\n"
                text += f"  Confidence:      {result.confidence:.0%}\n\n"
                text += f"  ── Mouse & Click ──\n"
                text += f"    Speed Range:   {result.mouse_speed_range}\n"
                text += f"    Click Delay:   {result.click_delay_ms}ms\n\n"
                text += f"  ── Typing ──\n"
                text += f"    WPM Range:     {result.typing_wpm_range}\n"
                text += f"    Error Rate:    {result.typing_error_rate:.1%}\n\n"
                text += f"  ── Navigation ──\n"
                text += f"    Scroll:        {result.scroll_behavior}\n"
                text += f"    Form Fill:     {result.form_fill_strategy}\n"
                text += f"    Session:       {result.session_length_seconds}s\n"
                text += f"    Page Views:    {result.page_views_before_checkout}\n"
                if result.warmup_actions:
                    text += f"\n  ── Warmup Sequence ──\n"
                    for i, action in enumerate(result.warmup_actions[:6], 1):
                        text += f"    {i}. {action}\n"
                text += f"\n  AI Powered: {result.ai_powered}"

                from PyQt6.QtCore import QMetaObject, Qt, Q_ARG
                QMetaObject.invokeMethod(self.ai_result, "setPlainText",
                    Qt.ConnectionType.QueuedConnection, Q_ARG(str, text))
            except Exception as e:
                from PyQt6.QtCore import QMetaObject, Qt, Q_ARG
                QMetaObject.invokeMethod(self.ai_result, "setPlainText",
                    Qt.ConnectionType.QueuedConnection, Q_ARG(str, f"Behavioral tuning error: {e}"))

        threading.Thread(target=_worker, daemon=True).start()

    # ─── NEW: Velocity Check ─────────────────────────────────────────

    def _check_velocity(self):
        """Show per-BIN velocity guard status."""
        bin_num = self.ai_bin_input.text().strip()
        if not bin_num:
            self.ai_result.setPlainText("Enter a BIN to check velocity.")
            return
        bin6     = bin_num[:6]
        vel      = _velocity_tracker.get(bin6, {})
        attempts = vel.get("attempts", 0)
        declines = vel.get("declines", 0)
        last     = vel.get("last_attempt", "never")

        if attempts == 0:
            status = "🟢 CLEAN — No attempts recorded"
        elif attempts < VELOCITY_WARN:
            status = f"🟢 LOW — {attempts} attempt(s), safe to proceed"
        elif attempts < VELOCITY_BLOCK:
            status = f"🟡 WARNING — {attempts} attempts, {declines} declines — slow down"
        else:
            status = f"🔴 BLOCKED — {attempts} attempts, {declines} declines — BIN likely flagged"

        text  = f"VELOCITY GUARD: BIN {bin6}\n{'='*50}\n\n"
        text += f"  Status:       {status}\n"
        text += f"  Attempts:     {attempts}\n"
        text += f"  Declines:     {declines}\n"
        text += f"  Last attempt: {last}\n\n"

        all_bins = list(_velocity_tracker.items())
        if all_bins:
            text += f"  ── All Tracked BINs ──\n"
            for b6, v in sorted(all_bins, key=lambda x: x[1].get("attempts", 0), reverse=True)[:10]:
                a = v.get("attempts", 0)
                d = v.get("declines", 0)
                icon = "🔴" if a >= VELOCITY_BLOCK else "🟡" if a >= VELOCITY_WARN else "🟢"
                text += f"    {icon} {b6}  attempts={a}  declines={d}\n"
        self.ai_result.setPlainText(text)

    # ─── NEW: Success Rate Tracker Tab ──────────────────────────────

    def _build_tracker_tab(self):
        """Tab 6: Live success rate tracker per BIN and target."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)
        self.tabs.addTab(tab, "📊 Tracker")

        header = QLabel("📊 OPERATION SUCCESS TRACKER")
        header.setFont(QFont("JetBrains Mono", 13, QFont.Weight.Bold))
        header.setStyleSheet("color: #00bcd4;")
        layout.addWidget(header)

        # Summary stats bar
        self.tracker_stats = QLabel("Attempts: 0 | Successes: 0 | Rate: —")
        self.tracker_stats.setStyleSheet("color: #aaa; font-size: 11px; padding: 4px;")
        layout.addWidget(self.tracker_stats)

        # BIN performance table
        bin_group = QGroupBox("BIN Performance")
        bin_layout = QVBoxLayout(bin_group)
        self.tracker_bin_table = QTableWidget()
        self.tracker_bin_table.setColumnCount(5)
        self.tracker_bin_table.setHorizontalHeaderLabels(["BIN", "Attempts", "Successes", "Rate", "Velocity"])
        self.tracker_bin_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tracker_bin_table.setAlternatingRowColors(True)
        self.tracker_bin_table.setMinimumHeight(180)
        bin_layout.addWidget(self.tracker_bin_table)
        layout.addWidget(bin_group)

        # Manual record buttons
        record_row = QHBoxLayout()
        rec_success_btn = QPushButton("✅ Record Success")
        rec_success_btn.setStyleSheet("QPushButton{background:#1b5e20;color:#00ff88;border:none;border-radius:6px;padding:8px 16px;font-weight:bold;}QPushButton:hover{background:#2e7d32;}")
        rec_success_btn.clicked.connect(lambda: self._record_attempt(success=True))
        record_row.addWidget(rec_success_btn)

        rec_fail_btn = QPushButton("❌ Record Decline")
        rec_fail_btn.setStyleSheet("QPushButton{background:#b71c1c;color:#ff8a80;border:none;border-radius:6px;padding:8px 16px;font-weight:bold;}QPushButton:hover{background:#c62828;}")
        rec_fail_btn.clicked.connect(lambda: self._record_attempt(success=False))
        record_row.addWidget(rec_fail_btn)

        reset_btn = QPushButton("🗑️ Reset Tracker")
        reset_btn.setStyleSheet("QPushButton{background:#333;color:#888;border:none;border-radius:6px;padding:8px 16px;}QPushButton:hover{color:#fff;}")
        reset_btn.clicked.connect(self._reset_tracker)
        record_row.addWidget(reset_btn)
        layout.addLayout(record_row)

        hint = QLabel("BIN is taken from the AI Intel tab. Record results after each attempt to track performance.")
        hint.setStyleSheet("color: #556; font-size: 10px;")
        hint.setWordWrap(True)
        layout.addWidget(hint)

    def _record_attempt(self, success: bool):
        """Record a success or decline for the current BIN."""
        bin_num = self.ai_bin_input.text().strip()
        if not bin_num:
            return
        bin6 = bin_num[:6]
        import datetime

        # Update success tracker
        if bin6 not in self._success_tracker:
            self._success_tracker[bin6] = {"attempts": 0, "successes": 0}
        self._success_tracker[bin6]["attempts"] += 1
        if success:
            self._success_tracker[bin6]["successes"] += 1

        # Update velocity tracker
        if bin6 not in _velocity_tracker:
            _velocity_tracker[bin6] = {"attempts": 0, "declines": 0, "last_attempt": ""}
        _velocity_tracker[bin6]["attempts"] += 1
        if not success:
            _velocity_tracker[bin6]["declines"] += 1
        _velocity_tracker[bin6]["last_attempt"] = datetime.datetime.now().strftime("%H:%M:%S")

        self._update_tracker_table()

    def _reset_tracker(self):
        """Reset all tracking data."""
        self._success_tracker.clear()
        _velocity_tracker.clear()
        self.tracker_bin_table.setRowCount(0)
        self.tracker_stats.setText("Attempts: 0 | Successes: 0 | Rate: —")

    def _update_tracker_table(self):
        """Refresh the tracker table with current data."""
        total_attempts  = sum(v["attempts"]  for v in self._success_tracker.values())
        total_successes = sum(v["successes"] for v in self._success_tracker.values())
        rate = f"{total_successes/total_attempts:.0%}" if total_attempts else "—"
        self.tracker_stats.setText(
            f"<span style='color:#aaa'>Attempts: <b>{total_attempts}</b> | "
            f"Successes: <b style='color:#00ff88'>{total_successes}</b> | "
            f"Rate: <b style='color:#E6A817'>{rate}</b></span>"
        )

        self.tracker_bin_table.setRowCount(len(self._success_tracker))
        for row, (bin6, data) in enumerate(
            sorted(self._success_tracker.items(),
                   key=lambda x: x[1]["attempts"], reverse=True)
        ):
            attempts  = data["attempts"]
            successes = data["successes"]
            bin_rate  = successes / attempts if attempts else 0
            vel       = _velocity_tracker.get(bin6, {})
            vel_atts  = vel.get("attempts", 0)

            if vel_atts >= VELOCITY_BLOCK:
                vel_status = "🔴 BLOCKED"
            elif vel_atts >= VELOCITY_WARN:
                vel_status = "🟡 WARNING"
            else:
                vel_status = "🟢 OK"

            self.tracker_bin_table.setItem(row, 0, QTableWidgetItem(bin6))
            self.tracker_bin_table.setItem(row, 1, QTableWidgetItem(str(attempts)))
            self.tracker_bin_table.setItem(row, 2, QTableWidgetItem(str(successes)))

            rate_item = QTableWidgetItem(f"{bin_rate:.0%}")
            rate_item.setForeground(QBrush(
                QColor("#00ff88") if bin_rate >= 0.7
                else QColor("#ffaa00") if bin_rate >= 0.4
                else QColor("#ff4444")
            ))
            self.tracker_bin_table.setItem(row, 3, rate_item)
            self.tracker_bin_table.setItem(row, 4, QTableWidgetItem(vel_status))

    # ─── TAB 7: HARDENED OPERATIONS PLANNER ─────────────────────────

    def _build_ops_tab(self):
        """Unified operation planner — chains all engines into one-click plan."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)
        self.tabs.addTab(tab, "⚔️ Operations")

        header = QLabel("⚔️ HARDENED OPERATION PLANNER")
        header.setFont(QFont("JetBrains Mono", 13, QFont.Weight.Bold))
        header.setStyleSheet("color: #ff6b35;")
        layout.addWidget(header)

        hint = QLabel("Uses BIN + Target from AI Intel tab. Fill those first.")
        hint.setStyleSheet("color: #556; font-size: 10px;")
        layout.addWidget(hint)

        # Row 1: Primary action
        row1 = QHBoxLayout()
        plan_btn = QPushButton("⚔️ PLAN FULL OPERATION")
        plan_btn.setMinimumHeight(44)
        plan_btn.setStyleSheet("QPushButton{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #ff6b35,stop:1 #e65100);color:#fff;font-weight:bold;font-size:13px;border:none;border-radius:8px;padding:0 20px;}QPushButton:hover{background:#ff8a50;}")
        plan_btn.clicked.connect(self._plan_full_operation)
        row1.addWidget(plan_btn)
        layout.addLayout(row1)

        # Row 2: Individual hardened engines
        row2 = QHBoxLayout()
        for label, slot, bg, fg in [
            ("🛡️ 3DS BYPASS ENGINE", self._run_3ds_bypass,    "#1a237e", "#82b1ff"),
            ("🔍 DECLINE DECODER",    self._run_decline_decoder, "#b71c1c", "#ff8a80"),
            ("🎯 BIN↔TARGET MATCH",   self._run_bin_target_match, "#1b5e20", "#00ff88"),
        ]:
            btn = QPushButton(label)
            btn.setMinimumHeight(36)
            btn.setStyleSheet(f"QPushButton{{background:{bg};color:{fg};font-weight:bold;border:1px solid {fg};border-radius:6px;padding:0 10px;}}QPushButton:hover{{background:{bg.replace('1a','28').replace('b7','c6').replace('1b','2e')}}}")
            btn.clicked.connect(slot)
            row2.addWidget(btn)
        layout.addLayout(row2)

        # Row 3: Utility
        row3 = QHBoxLayout()
        for label, slot in [
            ("📋 Pre-Flight Checks",  self._run_preflight_checks),
            ("💳 Card Freshness",      self._check_card_freshness),
            ("🔇 Silent Validation",   self._show_silent_strategy),
            ("📖 PSP Vulnerabilities", self._show_psp_vulns),
        ]:
            btn = QPushButton(label)
            btn.setMinimumHeight(32)
            btn.setStyleSheet("QPushButton{background:#1C2330;color:#aaa;border:1px solid #333;border-radius:6px;padding:0 8px;}QPushButton:hover{color:#fff;border-color:#555;}")
            btn.clicked.connect(slot)
            row3.addWidget(btn)
        layout.addLayout(row3)

        self.ops_result = QTextEdit()
        self.ops_result.setReadOnly(True)
        self.ops_result.setFont(QFont("JetBrains Mono", 10))
        self.ops_result.setPlaceholderText(
            "Hardened Operation Planner\n\n"
            "  ⚔️ PLAN FULL OPERATION — chains ALL engines into one-click plan:\n"
            "     BIN score → Target match → 3DS bypass → Behavioral tuning\n"
            "     → Pre-flight checks → Step-by-step execution plan\n\n"
            "  🛡️ 3DS Bypass Engine — real PSP vulnerabilities + downgrade attacks\n"
            "  🔍 Decline Decoder — decode any PSP response code into root cause\n"
            "  🎯 BIN↔Target Match — cross-reference BIN with best targets\n"
            "  📋 Pre-Flight Checks — proxy, profile, geo, TLS validation\n"
            "  💳 Card Freshness — estimate card age and viability\n"
            "  🔇 Silent Validation — validate without triggering fraud alerts\n\n"
            "Fill BIN + Target in AI Intel tab, then click PLAN FULL OPERATION."
        )
        layout.addWidget(self.ops_result)

    # ─── PLAN FULL OPERATION (chains all engines) ────────────────────

    def _plan_full_operation(self):
        """One-click operation planner — chains every engine together."""
        bin_num = self.ai_bin_input.text().strip()
        target  = self.ai_bin_target.text().strip()
        amount  = self.ai_bin_amount.value()
        if not bin_num or not target:
            self.ops_result.setPlainText("⚠️ Enter BIN + Target in the AI Intel tab first.")
            return
        self.ops_result.setPlainText(f"⚔️ Planning operation: BIN {bin_num} → {target} ${amount}...\n   Running all engines in parallel. Please wait ~15-20s.")
        QApplication.processEvents()

        import threading
        def _worker():
            try:
                import concurrent.futures, time
                t0 = time.time()
                results = {}

                with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
                    if AI_AVAILABLE:
                        results["f_bin"]    = ex.submit(analyze_bin, bin_num, target, amount)
                        results["f_target"] = ex.submit(recon_target, target)
                        results["f_3ds"]    = ex.submit(advise_3ds, bin_num, target, amount)
                        results["f_behav"]  = ex.submit(tune_behavior, target)

                b = results.get("f_bin")
                b = b.result(timeout=90) if b else None
                t = results.get("f_target")
                t = t.result(timeout=90) if t else None
                s = results.get("f_3ds")
                s = s.result(timeout=90) if s else None
                bh = results.get("f_behav")
                bh = bh.result(timeout=90) if bh else None

                # 3DS Bypass Engine (real)
                bypass = None
                if BYPASS_ENGINE_AVAILABLE and t:
                    bypass = get_3ds_bypass_score(
                        target, psp=t.payment_processor_guess,
                        three_ds="conditional", fraud_engine=t.fraud_engine_guess,
                        amount=amount, card_country=b.country if b else "US"
                    )

                # BIN↔Target match
                matched_targets = []
                if INTEL_AVAILABLE and b:
                    try:
                        td = TargetDiscovery()
                        matched_targets = td.recommend_for_card(
                            country=b.country, amount=amount
                        )[:5]
                    except Exception:
                        pass

                # Card freshness
                freshness = None
                if INTEL_AVAILABLE:
                    try:
                        freshness = estimate_card_freshness(bin_num[:6])
                    except Exception:
                        pass

                elapsed = time.time() - t0

                # ── Build the plan ──
                text  = f"{'='*60}\n"
                text += f"  ⚔️  FULL OPERATION PLAN\n"
                text += f"  BIN {bin_num} → {target} ${amount}\n"
                text += f"{'='*60}\n\n"

                # Verdict
                if b and t and bypass:
                    composite = (
                        (b.ai_score or 50) / 100 * 0.25
                        + (b.success_prediction or 0.5) * 0.25
                        + (bypass.get("bypass_score", 50)) / 100 * 0.25
                        + (1.0 - t.three_ds_probability) * 0.25
                    )
                    vel = _velocity_tracker.get(bin_num[:6], {})
                    composite -= min(vel.get("declines", 0) * 0.05, 0.3)
                    composite = max(0, min(1, composite))
                    if composite >= 0.70:
                        verdict = "🟢 GO — HIGH CONFIDENCE"
                    elif composite >= 0.50:
                        verdict = "🟡 PROCEED WITH CAUTION"
                    else:
                        verdict = "🔴 NO-GO — ABORT"
                    text += f"  VERDICT: {verdict}  ({composite*100:.0f}/100)\n\n"

                # Phase 1: BIN Intelligence
                if b:
                    text += f"  ── PHASE 1: BIN INTELLIGENCE ──\n"
                    text += f"    Bank:          {b.bank_name} ({b.country})\n"
                    text += f"    Type:          {b.card_type} {b.card_level} ({b.network})\n"
                    text += f"    AI Score:      {b.ai_score}/100\n"
                    text += f"    Success Pred:  {b.success_prediction:.0%}\n"
                    text += f"    Risk:          {b.risk_level.value}\n"
                    text += f"    Optimal $:     ${b.optimal_amount_range[0]:.0f}–${b.optimal_amount_range[1]:.0f}\n"
                    text += f"    Timing:        {b.timing_advice}\n"
                    if freshness:
                        text += f"    Freshness:     {freshness}\n"
                    text += "\n"

                # Phase 2: Target Intelligence
                if t:
                    text += f"  ── PHASE 2: TARGET INTELLIGENCE ──\n"
                    text += f"    Fraud Engine:  {t.fraud_engine_guess}\n"
                    text += f"    PSP:           {t.payment_processor_guess}\n"
                    text += f"    Friction:      {t.estimated_friction}\n"
                    text += f"    3DS Prob:      {t.three_ds_probability:.0%}\n"
                    text += f"    Best Cards:    {', '.join(t.optimal_card_types)}\n"
                    text += f"    Best Countries:{', '.join(t.optimal_countries)}\n\n"

                # Phase 3: 3DS Bypass
                if bypass:
                    text += f"  ── PHASE 3: 3DS BYPASS ANALYSIS ──\n"
                    text += f"    Bypass Score:  {bypass['bypass_score']}/100 ({bypass['bypass_level']})\n"
                    text += f"    Downgrade:     {'✅ Possible' if bypass.get('downgrade_possible') else '❌ Not available'}\n"
                    for tech in bypass.get("techniques", [])[:4]:
                        text += f"    • {tech}\n"
                    for w in bypass.get("warnings", [])[:2]:
                        text += f"    {w}\n"
                    text += "\n"

                # Phase 4: 3DS Strategy
                if s:
                    text += f"  ── PHASE 4: 3DS STRATEGY ──\n"
                    text += f"    Approach:      {s.recommended_approach}\n"
                    text += f"    Success:       {s.success_probability:.0%}\n"
                    text += f"    Timing:        {s.timing_window}\n"
                    text += f"    Amount:        {s.amount_strategy}\n"
                    text += f"    Card Pref:     {s.card_type_preference}\n\n"

                # Phase 5: Behavioral Tuning
                if bh:
                    text += f"  ── PHASE 5: BEHAVIORAL EVASION ──\n"
                    text += f"    Engine:        {bh.target_engine}\n"
                    text += f"    Mouse Speed:   {bh.mouse_speed_range}\n"
                    text += f"    Click Delay:   {bh.click_delay_ms}ms\n"
                    text += f"    Typing WPM:    {bh.typing_wpm_range}\n"
                    text += f"    Session:       {bh.session_length_seconds}s\n"
                    text += f"    Page Views:    {bh.page_views_before_checkout}\n\n"

                # Phase 6: Execution Steps
                text += f"  ── PHASE 6: EXECUTION PLAN ──\n"
                step = 1
                if bh and bh.warmup_actions:
                    for action in bh.warmup_actions[:4]:
                        text += f"    {step}. {action}\n"
                        step += 1
                if t and t.warmup_strategy:
                    for ws in t.warmup_strategy[:3]:
                        text += f"    {step}. {ws}\n"
                        step += 1
                if s and s.checkout_flow:
                    for cf in s.checkout_flow:
                        text += f"    {step}. {cf}\n"
                        step += 1
                text += f"    {step}. Monitor for 3DS challenge — if triggered: {s.fallback_plan if s else 'try different card'}\n"

                # Phase 7: Best alternative targets
                if matched_targets:
                    text += f"\n  ── ALTERNATIVE TARGETS (BIN-matched) ──\n"
                    for mt in matched_targets[:5]:
                        name = mt.get("name", mt.get("domain", "?"))
                        rate = mt.get("success_rate", 0)
                        text += f"    • {name} ({mt.get('domain','')}) — {rate*100:.0f}% success\n"

                # Risk factors
                if b and b.risk_factors:
                    text += f"\n  ── RISK FACTORS ──\n"
                    for rf in b.risk_factors[:4]:
                        text += f"    ⚠ {rf}\n"

                text += f"\n{'='*60}\n"
                text += f"  Engines used: {sum(1 for x in [b,t,s,bh,bypass] if x)}/5\n"
                text += f"  Planning time: {elapsed:.1f}s\n"
                text += f"  AI Powered: {b.ai_powered if b else False}\n"

                from PyQt6.QtCore import QMetaObject, Qt, Q_ARG
                QMetaObject.invokeMethod(self.ops_result, "setPlainText",
                    Qt.ConnectionType.QueuedConnection, Q_ARG(str, text))
            except Exception as e:
                from PyQt6.QtCore import QMetaObject, Qt, Q_ARG
                QMetaObject.invokeMethod(self.ops_result, "setPlainText",
                    Qt.ConnectionType.QueuedConnection, Q_ARG(str, f"Operation planning error: {e}"))

        threading.Thread(target=_worker, daemon=True).start()

    # ─── 3DS BYPASS ENGINE ───────────────────────────────────────────

    def _run_3ds_bypass(self):
        """Real 3DS bypass scoring with PSP vulnerabilities."""
        if not BYPASS_ENGINE_AVAILABLE:
            self.ops_result.setPlainText("⚠️ three_ds_strategy module not available")
            return
        target = self.ai_bin_target.text().strip()
        amount = self.ai_bin_amount.value()
        bin_num = self.ai_bin_input.text().strip()
        if not target:
            self.ops_result.setPlainText("Enter a target domain in AI Intel tab.")
            return

        # Get target intel for PSP
        psp = "unknown"
        fraud_eng = "unknown"
        if AI_AVAILABLE:
            try:
                t = recon_target(target)
                psp = t.payment_processor_guess
                fraud_eng = t.fraud_engine_guess
            except Exception:
                pass

        result = get_3ds_bypass_score(
            target, psp=psp, fraud_engine=fraud_eng,
            amount=amount, card_country="US"
        )
        text  = f"3DS BYPASS ENGINE: {target}\n{'='*55}\n\n"
        text += f"  Bypass Score:  {result['bypass_score']}/100 ({result['bypass_level']})\n"
        text += f"  PSP:           {result['psp']}\n"
        text += f"  Downgrade:     {'✅ Yes' if result.get('downgrade_possible') else '❌ No'}\n\n"
        text += f"  ── Techniques ──\n"
        for tech in result.get("techniques", []):
            text += f"    • {tech}\n"
        if result.get("warnings"):
            text += f"\n  ── Warnings ──\n"
            for w in result["warnings"]:
                text += f"    {w}\n"
        vulns = result.get("psp_vulnerabilities", [])
        if vulns:
            text += f"\n  ── PSP Weak Points ──\n"
            for v in vulns[:5]:
                text += f"    • {v}\n"

        # PSD2 exemptions
        exemptions = get_psd2_exemptions()
        if exemptions:
            text += f"\n  ── PSD2 Exemptions ──\n"
            for name, info in list(exemptions.items())[:4]:
                text += f"    {name}: {info.get('description', info) if isinstance(info, dict) else info}\n"

        self.ops_result.setPlainText(text)

    # ─── DECLINE DECODER ─────────────────────────────────────────────

    def _run_decline_decoder(self):
        """Decode a PSP decline code into root cause + action."""
        if not DECLINE_DECODER_AVAILABLE:
            self.ops_result.setPlainText("⚠️ transaction_monitor module not available")
            return
        from PyQt6.QtWidgets import QInputDialog
        code, ok = QInputDialog.getText(
            self, "Decline Decoder",
            "Enter the PSP response/decline code:\n(e.g. 'card_declined', '05', 'do_not_honor', '2004')"
        )
        if not ok or not code.strip():
            return
        result = decode_decline(code.strip())
        sev_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(result["severity"], "⚪")
        text  = f"DECLINE DECODER\n{'='*55}\n\n"
        text += f"  Code:      {result['code']}\n"
        text += f"  PSP:       {result['psp']}\n"
        text += f"  Reason:    {result['reason']}\n"
        text += f"  Category:  {result['category']}\n"
        text += f"  Severity:  {sev_icon} {result['severity'].upper()}\n\n"
        text += f"  ── Action ──\n"
        text += f"  {result['action']}\n"
        self.ops_result.setPlainText(text)

    # ─── BIN ↔ TARGET MATCHER ────────────────────────────────────────

    def _run_bin_target_match(self):
        """Cross-reference BIN with best-matching targets."""
        bin_num = self.ai_bin_input.text().strip()
        if not bin_num:
            self.ops_result.setPlainText("Enter a BIN in AI Intel tab.")
            return
        self.ops_result.setPlainText(f"🎯 Matching BIN {bin_num} to best targets...")
        QApplication.processEvents()

        import threading
        def _worker():
            try:
                text  = f"BIN↔TARGET MATCHER: {bin_num[:6]}\n{'='*55}\n\n"

                # Get BIN info
                country = "US"
                amount = self.ai_bin_amount.value()
                if AI_AVAILABLE:
                    b = analyze_bin(bin_num, "", amount)
                    country = b.country
                    text += f"  Card: {b.bank_name} ({b.country}) {b.card_type} {b.card_level}\n"
                    text += f"  AI Score: {b.ai_score}/100 | Success: {b.success_prediction:.0%}\n\n"

                    if b.best_targets:
                        text += f"  ── AI Recommended Targets ──\n"
                        for tgt in b.best_targets[:5]:
                            text += f"    ✅ {tgt}\n"
                    if b.avoid_targets:
                        text += f"\n  ── Avoid ──\n"
                        for tgt in b.avoid_targets[:3]:
                            text += f"    ❌ {tgt}\n"
                    text += "\n"

                # Target Discovery match
                if INTEL_AVAILABLE:
                    td = TargetDiscovery()
                    matched = td.recommend_for_card(country=country, amount=amount)
                    if matched:
                        text += f"  ── Database Matches ({len(matched)} sites) ──\n"
                        for m in matched[:10]:
                            name = m.get("name", m.get("domain", "?"))
                            domain = m.get("domain", "?")
                            rate = m.get("success_rate", 0)
                            psp = m.get("psp", "?")
                            diff = m.get("difficulty", "?")
                            icon = "🟢" if rate >= 0.8 else "🟡" if rate >= 0.5 else "🔴"
                            text += f"    {icon} {name:25s} {domain:25s} {rate*100:3.0f}% {psp:15s} {diff}\n"

                    # 3DS bypass scoring for top matches
                    if BYPASS_ENGINE_AVAILABLE and matched:
                        text += f"\n  ── 3DS Bypass Scores (top 5) ──\n"
                        for m in matched[:5]:
                            bs = get_3ds_bypass_score(
                                m.get("domain", ""), psp=m.get("psp", "unknown"),
                                three_ds=m.get("three_ds", "unknown"),
                                fraud_engine=m.get("fraud_engine", "unknown"),
                                amount=amount, card_country=country
                            )
                            text += f"    {m.get('domain',''):25s} bypass={bs['bypass_score']}/100 ({bs['bypass_level']})\n"
                else:
                    text += "  target_discovery module not available\n"

                from PyQt6.QtCore import QMetaObject, Qt, Q_ARG
                QMetaObject.invokeMethod(self.ops_result, "setPlainText",
                    Qt.ConnectionType.QueuedConnection, Q_ARG(str, text))
            except Exception as e:
                from PyQt6.QtCore import QMetaObject, Qt, Q_ARG
                QMetaObject.invokeMethod(self.ops_result, "setPlainText",
                    Qt.ConnectionType.QueuedConnection, Q_ARG(str, f"BIN↔Target match error: {e}"))

        threading.Thread(target=_worker, daemon=True).start()

    # ─── PRE-FLIGHT CHECKS ───────────────────────────────────────────

    def _run_preflight_checks(self):
        """Run actual PreFlightValidator checks."""
        if not PREFLIGHT_AVAILABLE:
            self.ops_result.setPlainText("⚠️ preflight_validator module not available")
            return
        self.ops_result.setPlainText("📋 Running pre-flight validation checks...")
        QApplication.processEvents()

        import threading
        def _worker():
            try:
                validator = PreFlightValidator()
                report = validator.validate()
                text  = f"PRE-FLIGHT VALIDATION REPORT\n{'='*55}\n\n"
                text += f"  Overall: {'✅ PASSED' if report.passed else '❌ FAILED'}\n"
                text += f"  Score:   {report.score:.0f}/100\n\n"
                for check in report.checks:
                    icon = "✅" if check.passed else "❌" if check.critical else "⚠️"
                    text += f"  {icon} {check.name}: {check.message}\n"
                if hasattr(report, 'recommendations') and report.recommendations:
                    text += f"\n  ── Recommendations ──\n"
                    for rec in report.recommendations[:5]:
                        text += f"    • {rec}\n"

                from PyQt6.QtCore import QMetaObject, Qt, Q_ARG
                QMetaObject.invokeMethod(self.ops_result, "setPlainText",
                    Qt.ConnectionType.QueuedConnection, Q_ARG(str, text))
            except Exception as e:
                from PyQt6.QtCore import QMetaObject, Qt, Q_ARG
                QMetaObject.invokeMethod(self.ops_result, "setPlainText",
                    Qt.ConnectionType.QueuedConnection, Q_ARG(str, f"Pre-flight error: {e}"))

        threading.Thread(target=_worker, daemon=True).start()

    # ─── CARD FRESHNESS ──────────────────────────────────────────────

    def _check_card_freshness(self):
        """Estimate card freshness/age."""
        if not INTEL_AVAILABLE:
            self.ops_result.setPlainText("⚠️ target_intelligence module not available")
            return
        bin_num = self.ai_bin_input.text().strip()
        if not bin_num:
            self.ops_result.setPlainText("Enter a BIN in AI Intel tab.")
            return
        try:
            result = estimate_card_freshness(bin_num[:6])
            text  = f"CARD FRESHNESS: BIN {bin_num[:6]}\n{'='*55}\n\n"
            if isinstance(result, dict):
                for k, v in result.items():
                    text += f"  {k}: {v}\n"
            else:
                text += f"  {result}\n"
            self.ops_result.setPlainText(text)
        except Exception as e:
            self.ops_result.setPlainText(f"Freshness check error: {e}")

    # ─── SILENT VALIDATION ───────────────────────────────────────────

    def _show_silent_strategy(self):
        """Show silent validation strategy for current BIN."""
        if not INTEL_AVAILABLE:
            self.ops_result.setPlainText("⚠️ cerberus_enhanced module not available")
            return
        bin_num = self.ai_bin_input.text().strip()
        if not bin_num:
            self.ops_result.setPlainText("Enter a BIN in AI Intel tab.")
            return
        try:
            engine = SilentValidationEngine()
            strategy = engine.get_validation_strategy(bin_num[:6], "Unknown")
            text  = f"SILENT VALIDATION STRATEGY: {bin_num[:6]}\n{'='*55}\n\n"
            if isinstance(strategy, dict):
                for k, v in strategy.items():
                    text += f"  {k}: {v}\n"
            else:
                text += f"  {strategy}\n"
            self.ops_result.setPlainText(text)
        except Exception as e:
            self.ops_result.setPlainText(f"Silent validation error: {e}")

    # ─── PSP VULNERABILITIES ─────────────────────────────────────────

    def _show_psp_vulns(self):
        """Show PSP-specific 3DS vulnerabilities."""
        if not BYPASS_ENGINE_AVAILABLE:
            self.ops_result.setPlainText("⚠️ three_ds_strategy module not available")
            return
        target = self.ai_bin_target.text().strip()
        psp = "unknown"
        if AI_AVAILABLE and target:
            try:
                t = recon_target(target)
                psp = t.payment_processor_guess
            except Exception:
                pass

        text  = f"PSP VULNERABILITIES\n{'='*55}\n"
        if psp != "unknown":
            text += f"\n  Target PSP: {psp}\n\n"
            vulns = get_psp_vulnerabilities(psp)
            if vulns:
                for k, v in vulns.items():
                    text += f"  {k}: {v}\n"
            else:
                text += f"  No known vulnerabilities for {psp}\n"

        # Show all downgrade attacks
        attacks = get_downgrade_attacks()
        if attacks:
            text += f"\n  ── 3DS Downgrade Attacks ({len(attacks)}) ──\n"
            for atk in attacks[:6]:
                text += f"    [{atk['success_rate']*100:.0f}%] {atk['name']} ({atk['type']})\n"
                text += f"         PSPs: {', '.join(atk['psps'][:3])}\n"
                for step in atk.get("steps", [])[:2]:
                    text += f"         → {step}\n"
                text += "\n"
        self.ops_result.setPlainText(text)

    # ─── TAB 8: BIN → TARGET MATCHER ─────────────────────────────────

    def _build_target_matcher_tab(self):
        """Tab that takes a BIN and shows best matching targets with safe limits."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        self.tabs.addTab(tab, "🎯 BIN → Targets")

        header = QLabel("BIN → Best Targets & Safe Limits")
        header.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        header.setStyleSheet("color: #00e676;")
        layout.addWidget(header)

        hint = QLabel("Enter a 6-digit BIN to find the best matching targets, safe spending limits, and compatibility scores.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(hint)

        # Input row
        input_row = QHBoxLayout()

        bin_label = QLabel("BIN:")
        bin_label.setStyleSheet("color: #ccc; font-weight: bold;")
        input_row.addWidget(bin_label)

        self.tm_bin_input = QLineEdit()
        self.tm_bin_input.setPlaceholderText("e.g. 421783")
        self.tm_bin_input.setMaxLength(6)
        self.tm_bin_input.setFixedWidth(120)
        self.tm_bin_input.setStyleSheet("QLineEdit{background:#1e1e1e;color:#fff;border:1px solid #444;border-radius:6px;padding:6px;font-family:Consolas;font-size:13px;}QLineEdit:focus{border-color:#00e676;}")
        input_row.addWidget(self.tm_bin_input)

        match_btn = QPushButton("🎯 FIND BEST TARGETS")
        match_btn.setMinimumHeight(38)
        match_btn.setStyleSheet("QPushButton{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #00c853,stop:1 #00e676);color:#000;font-weight:bold;font-size:12px;border:none;border-radius:8px;padding:0 24px;}QPushButton:hover{background:#69f0ae;}")
        match_btn.clicked.connect(self._run_target_match_lookup)
        input_row.addWidget(match_btn)

        input_row.addStretch()
        layout.addLayout(input_row)

        # BIN summary card
        self.tm_bin_summary = QLabel("")
        self.tm_bin_summary.setWordWrap(True)
        self.tm_bin_summary.setStyleSheet("background:#1a1a2e;color:#ccc;border:1px solid #333;border-radius:8px;padding:10px;font-size:11px;")
        self.tm_bin_summary.setMinimumHeight(60)
        layout.addWidget(self.tm_bin_summary)

        # Results table
        self.tm_table = QTableWidget()
        self.tm_table.setColumnCount(7)
        self.tm_table.setHorizontalHeaderLabels([
            "Target", "Compatibility", "Safe Limit", "AVS", "3DS Risk", "Verdict", "Notes"
        ])
        self.tm_table.horizontalHeader().setStretchLastSection(True)
        self.tm_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.tm_table.setAlternatingRowColors(True)
        self.tm_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tm_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tm_table.verticalHeader().setVisible(False)
        self.tm_table.setStyleSheet("""
            QTableWidget { background: #1a1a2e; color: #ddd; gridline-color: #333; border: 1px solid #333; border-radius: 6px; }
            QTableWidget::item { padding: 4px 8px; }
            QTableWidget::item:selected { background: #1b5e20; }
            QHeaderView::section { background: #0d0d1a; color: #00e676; font-weight: bold; border: 1px solid #333; padding: 6px; }
        """)
        layout.addWidget(self.tm_table)

        # Risk factors + recommendations
        self.tm_details = QPlainTextEdit()
        self.tm_details.setReadOnly(True)
        self.tm_details.setMaximumHeight(160)
        self.tm_details.setStyleSheet("QPlainTextEdit{background:#0d0d1a;color:#aaa;border:1px solid #333;border-radius:6px;font-family:Consolas;font-size:11px;}")
        self.tm_details.setPlaceholderText("Risk factors and recommendations will appear here...")
        layout.addWidget(self.tm_details)

    def _run_target_match_lookup(self):
        """Score BIN and display best matching targets with safe limits."""
        bin6 = self.tm_bin_input.text().strip().replace(" ", "")[:6]
        if len(bin6) < 6 or not bin6.isdigit():
            self.tm_bin_summary.setText("⚠️ Enter a valid 6-digit BIN")
            return

        try:
            scorer = BINScoringEngine()
            score = scorer.score_bin(bin6)

            # BIN summary card
            quality_icon = "🟢" if score.overall_score >= 80 else "🟡" if score.overall_score >= 60 else "🔴"
            avs_icon = {"relaxed": "🟢", "moderate": "🟡", "strict": "🔴"}.get(score.avs_strictness, "⚪")
            summary = (
                f"{quality_icon} <b>{score.bank}</b> — {score.card_level.replace('_', ' ').title()} "
                f"{score.network.upper()} ({score.card_type.title()}) | "
                f"<b>Score: {score.overall_score:.0f}/100</b> | "
                f"Country: {score.country} | "
                f"AVS: {avs_icon} {score.avs_strictness.title()} | "
                f"3DS Rate: {score.estimated_3ds_rate:.0%} | "
                f"Max Single: <b>${score.max_single_amount:,.0f}</b> | "
                f"Daily Limit: ${score.velocity_limit_daily:,.0f}"
            )
            self.tm_bin_summary.setText(summary)

            # Build table — sort by compatibility descending
            targets = sorted(score.target_compatibility.items(), key=lambda x: x[1], reverse=True)
            self.tm_table.setRowCount(0)

            for target, compat in targets:
                row = self.tm_table.rowCount()
                self.tm_table.insertRow(row)

                profile = scorer.TARGET_COMPATIBILITY.get(target, {})
                max_amt = profile.get('max_amount', 1000)
                avs_req = profile.get('avs_requirement', 'full')

                # Safe limit = min(card max, target max) with 20% safety margin
                safe_limit = min(score.max_single_amount, max_amt) * 0.8

                # Compatibility color
                if compat >= 0.80:
                    compat_color = "#00e676"
                    verdict = "✅ RECOMMENDED"
                    verdict_color = "#00e676"
                elif compat >= 0.65:
                    compat_color = "#ffeb3b"
                    verdict = "⚠️ POSSIBLE"
                    verdict_color = "#ffeb3b"
                elif compat >= 0.50:
                    compat_color = "#ff9800"
                    verdict = "🟠 RISKY"
                    verdict_color = "#ff9800"
                else:
                    compat_color = "#f44336"
                    verdict = "🔴 AVOID"
                    verdict_color = "#f44336"

                # 3DS risk for this target
                tds_risk = score.estimated_3ds_rate
                if avs_req == 'full':
                    tds_risk = min(tds_risk + 0.10, 1.0)
                tds_icon = "🟢" if tds_risk < 0.25 else "🟡" if tds_risk < 0.40 else "🔴"

                # Notes
                notes = []
                if score.card_type == 'debit':
                    notes.append("Debit — lower limits")
                if score.avs_strictness == 'strict' and avs_req == 'full':
                    notes.append("Strict AVS — verify address")
                if compat >= 0.80:
                    notes.append("High match")
                if safe_limit < 100:
                    notes.append("Low safe limit")

                # Target name
                item_target = QTableWidgetItem(target)
                item_target.setFont(QFont("Consolas", 10))
                self.tm_table.setItem(row, 0, item_target)

                # Compatibility %
                item_compat = QTableWidgetItem(f"{compat:.0%}")
                item_compat.setForeground(QBrush(QColor(compat_color)))
                item_compat.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
                self.tm_table.setItem(row, 1, item_compat)

                # Safe limit
                item_limit = QTableWidgetItem(f"${safe_limit:,.0f}")
                item_limit.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
                item_limit.setForeground(QBrush(QColor("#00e676" if safe_limit >= 500 else "#ffeb3b" if safe_limit >= 200 else "#ff9800")))
                self.tm_table.setItem(row, 2, item_limit)

                # AVS requirement
                avs_display = {"zip_only": "ZIP only", "full": "Full (Street+ZIP)", "none": "None"}.get(avs_req, avs_req)
                item_avs = QTableWidgetItem(avs_display)
                self.tm_table.setItem(row, 3, item_avs)

                # 3DS risk
                item_3ds = QTableWidgetItem(f"{tds_icon} {tds_risk:.0%}")
                self.tm_table.setItem(row, 4, item_3ds)

                # Verdict
                item_verdict = QTableWidgetItem(verdict)
                item_verdict.setForeground(QBrush(QColor(verdict_color)))
                item_verdict.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
                self.tm_table.setItem(row, 5, item_verdict)

                # Notes
                item_notes = QTableWidgetItem(" | ".join(notes) if notes else "—")
                item_notes.setStyleSheet("color: #888;")
                self.tm_table.setItem(row, 6, item_notes)

            # Risk factors + recommendations
            details = f"═══ RISK FACTORS ═══\n"
            for rf in score.risk_factors:
                details += f"  ⚠️ {rf}\n"
            if not score.risk_factors:
                details += "  ✅ No major risk factors detected\n"
            details += f"\n═══ RECOMMENDATIONS ═══\n"
            for rec in score.recommendations:
                details += f"  → {rec}\n"

            # Add decline history if available
            if AI_AVAILABLE:
                try:
                    pattern = get_bin_decline_pattern(bin6)
                    if pattern.get("total_declines", 0) > 0:
                        details += f"\n═══ DECLINE HISTORY ═══\n"
                        details += f"  Total declines: {pattern['total_declines']}\n"
                        details += f"  Recent (1h): {pattern['recent_declines']}\n"
                        details += f"  Pattern: {pattern['pattern']}\n"
                        details += f"  {pattern['recommendation']}\n"
                except Exception:
                    pass

            self.tm_details.setPlainText(details)

        except Exception as e:
            self.tm_bin_summary.setText(f"❌ Error: {e}")
            self.tm_details.setPlainText(str(e))

    def apply_dark_theme(self):
        """Apply Enterprise HRUX theme from centralized theme module."""
        try:
            from titan_enterprise_theme import apply_enterprise_theme
            apply_enterprise_theme(self, "#00bcd4")
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
        """Handle validation result with decline intelligence + velocity tracking"""
        self.validate_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        if isinstance(result, Exception):
            self.show_result_error(str(result))
            self.strategy_btn.setVisible(False)
        else:
            self.show_result(result)
            self.add_to_history(result)
            
            # Feed into velocity tracker + success tracker (decline-aware)
            if hasattr(result, 'card') and result.card:
                is_success = result.status == CardStatus.LIVE
                # Don't count processor errors as real declines
                decline_cat = getattr(result, 'decline_category', '') or ''
                is_real_decline = (result.status == CardStatus.DEAD and
                    decline_cat not in ('processor_error', 'issuer_unavailable', ''))
                if is_success or is_real_decline:
                    self._record_attempt(is_success)
                
                # Feed decline into AI feedback loop for per-BIN learning
                if is_real_decline and AI_AVAILABLE:
                    try:
                        bin6 = result.card.number[:6] if hasattr(result.card, 'number') else ''
                        target = self.ai_bin_target.text().strip() if hasattr(self, 'ai_bin_target') else ''
                        record_decline(
                            bin_number=bin6,
                            target=target or 'unknown',
                            decline_code=getattr(result, 'response_code', '') or '',
                            decline_category=decline_cat,
                            amount=self.ai_bin_amount.value() if hasattr(self, 'ai_bin_amount') else 0,
                        )
                    except Exception:
                        pass
            
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
        """Display validation result with decline intelligence"""
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
        
        # Build enriched detail text with decline intelligence
        detail_parts = [result.message]
        
        # Show gateways tried
        gateways = getattr(result, 'gateways_tried', [])
        if gateways and len(gateways) > 1:
            detail_parts.append(f"Gateways tried: {' → '.join(gateways)}")
        
        # Show decline intelligence
        decline_reason = getattr(result, 'decline_reason', None)
        decline_action = getattr(result, 'decline_action', None)
        decline_severity = getattr(result, 'decline_severity', None)
        retry_advice = getattr(result, 'retry_advice', None)
        
        if decline_severity:
            sev_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(decline_severity, "⚪")
            detail_parts.append(f"Severity: {sev_icon} {decline_severity.upper()}")
        if decline_action and decline_action != decline_reason:
            detail_parts.append(f"Action: {decline_action}")
        if retry_advice and retry_advice != decline_action:
            detail_parts.append(f"Advice: {retry_advice}")
        
        # Show 3DS bypass plan summary
        bypass = getattr(result, 'bypass_plan', None)
        if bypass:
            detail_parts.append(f"3DS Bypass: {bypass.get('bypass_level', '?')} ({bypass.get('bypass_score', '?')}/100)")
        
        self.detail_text.setText("\n".join(detail_parts))
        
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
        apply_enterprise_theme_to_app(app, "#00bcd4")
    except ImportError:
        pass

    splash = None
    try:
        from titan_splash import show_titan_splash
        splash = show_titan_splash(app, "ASSET VALIDATION ENGINE", "#00bcd4")
    except Exception:
        pass
    
    window = CerberusApp()
    window.show()
    if splash:
        splash.finish(window)
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
