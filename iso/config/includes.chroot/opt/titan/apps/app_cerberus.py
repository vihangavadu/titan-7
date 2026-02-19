#!/usr/bin/env python3
"""
TITAN V7.0.3 SINGULARITY - Cerberus App
The Gatekeeper: Card Validation GUI

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
    QFileDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor, QBrush

import asyncio
from cerberus_core import (
    CerberusValidator, CardAsset, ValidationResult, CardStatus,
    MerchantKey, BulkValidator
)
from cerberus_enhanced import (
    MaxDrainEngine, BINScoringEngine, generate_drain_plan, format_drain_plan
)


class DrainPlanDialog(QDialog):
    """Dialog showing full MaxDrain strategy plan"""
    
    def __init__(self, plan_text: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("MaxDrain Strategy Plan")
        self.setMinimumSize(700, 600)
        
        layout = QVBoxLayout(self)
        
        header = QLabel("MaxDrain Strategy")
        header.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header.setStyleSheet("color: #ff9800;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        self.plan_display = QTextEdit()
        self.plan_display.setReadOnly(True)
        self.plan_display.setFont(QFont("Consolas", 10))
        self.plan_display.setPlainText(plan_text)
        self.plan_display.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a2e;
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
                background-color: #ff9800;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #ffa726; }
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
        self.setWindowTitle("🛡️ CERBERUS - The Gatekeeper | TITAN V7.0.3")
        self.setMinimumSize(550, 650)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header = QLabel("🛡️ CERBERUS - THE GATEKEEPER")
        header.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("color: #00bcd4; margin-bottom: 5px;")
        layout.addWidget(header)
        
        subtitle = QLabel("Zero-Touch Card Validation")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #888; font-size: 12px;")
        layout.addWidget(subtitle)
        
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
        self.traffic_light.setFont(QFont("Segoe UI Emoji", 64))
        self.traffic_light.setAlignment(Qt.AlignmentFlag.AlignCenter)
        traffic_layout.addWidget(self.traffic_light)
        
        self.status_text = QLabel("READY")
        self.status_text.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
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
        self.validate_btn.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.validate_btn.setStyleSheet("""
            QPushButton {
                background-color: #00bcd4;
                color: white;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #26c6da;
            }
            QPushButton:pressed {
                background-color: #0097a7;
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
        self.strategy_btn = QPushButton("MaxDrain Strategy")
        self.strategy_btn.setMinimumHeight(40)
        self.strategy_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.strategy_btn.setVisible(False)
        self.strategy_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff9800;
                color: white;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #ffa726;
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
        export_btn.setStyleSheet("color: #00bcd4; background: transparent; border: 1px solid #00bcd4; border-radius: 4px; padding: 4px 10px;")
        export_btn.clicked.connect(self.export_results)
        stats_layout.addWidget(export_btn)
        
        bulk_btn = QPushButton("Bulk Validate")
        bulk_btn.setStyleSheet("color: #ff9800; background: transparent; border: 1px solid #ff9800; border-radius: 4px; padding: 4px 10px;")
        bulk_btn.clicked.connect(self.bulk_validate)
        stats_layout.addWidget(bulk_btn)
        
        clear_history_btn = QPushButton("Clear History")
        clear_history_btn.setStyleSheet("color: #888; background: transparent; border: none;")
        clear_history_btn.clicked.connect(self.clear_history)
        stats_layout.addWidget(clear_history_btn)
        
        layout.addLayout(stats_layout)
        
        # Footer
        footer = QLabel("TITAN V7.0.3 SINGULARITY | Reality Synthesis Suite")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet("color: #555; font-size: 10px;")
        layout.addWidget(footer)
    
    def apply_dark_theme(self):
        """Apply dark theme"""
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #1e1e1e;
                color: #e0e0e0;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #333;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QLineEdit {
                background-color: #2d2d2d;
                border: 1px solid #444;
                border-radius: 6px;
                padding: 8px;
                color: #e0e0e0;
                selection-background-color: #00bcd4;
            }
            QLineEdit:focus {
                border-color: #00bcd4;
            }
            QTableWidget {
                background-color: #252525;
                border: 1px solid #333;
                border-radius: 4px;
                gridline-color: #333;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QTableWidget::item:selected {
                background-color: #00bcd4;
            }
            QHeaderView::section {
                background-color: #333;
                padding: 5px;
                border: none;
                border-bottom: 1px solid #444;
            }
            QProgressBar {
                background-color: #333;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: #00bcd4;
                border-radius: 3px;
            }
        """)
    
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
                            f"MaxDrain Strategy — ${self._last_drain_plan.total_drain_target:,.0f} "
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
        
        self.worker = ValidationWorker(self.validator, card)
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
    
    window = CerberusApp()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
