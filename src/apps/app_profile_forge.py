#!/usr/bin/env python3
"""
TITAN V8.2 PROFILE FORGE — Identity + Chrome Profile Building
==============================================================
Focused app for persona creation and browser profile forging.

3 tabs:
  1. IDENTITY — Name, email, phone, address, card details
  2. FORGE — Genesis engine, purchase history, IndexedDB, realism scoring
  3. PROFILES — Browse/manage generated profiles
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
    QTabWidget, QFrame, QComboBox, QProgressBar, QMessageBox,
    QScrollArea, QPlainTextEdit, QSpinBox, QTableWidget,
    QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

ACCENT = "#00d4ff"
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

# Core imports (graceful)
try:
    from genesis_core import GenesisEngine, ProfileConfig
    GENESIS_OK = True
except ImportError:
    GENESIS_OK = False

try:
    from purchase_history_engine import PurchaseHistoryEngine, CardHolderData
    PURCHASE_OK = True
except ImportError:
    PURCHASE_OK = False

try:
    from advanced_profile_generator import AdvancedProfileGenerator
    APG_OK = True
except ImportError:
    APG_OK = False

try:
    from persona_enrichment_engine import PersonaEnrichmentEngine
    PERSONA_OK = True
except ImportError:
    PERSONA_OK = False

try:
    from indexeddb_lsng_synthesis import IndexedDBShardSynthesizer
    IDB_OK = True
except ImportError:
    IDB_OK = False

try:
    from first_session_bias_eliminator import FirstSessionBiasEliminator
    FSB_OK = True
except ImportError:
    FSB_OK = False

try:
    from forensic_synthesis_engine import Cache2Synthesizer
    CACHE_OK = True
except ImportError:
    CACHE_OK = False

try:
    from font_sanitizer import FontSanitizer
    FONT_OK = True
except ImportError:
    FONT_OK = False

try:
    from audio_hardener import AudioHardener
    AUDIO_OK = True
except ImportError:
    AUDIO_OK = False

try:
    from profile_realism_engine import ProfileRealismEngine
    REALISM_OK = True
except ImportError:
    REALISM_OK = False

try:
    from chromium_commerce_injector import inject_golden_chain
    CHROME_COMMERCE_OK = True
except ImportError:
    CHROME_COMMERCE_OK = False

try:
    from titan_session import get_session, update_session
    SESSION_OK = True
except ImportError:
    SESSION_OK = False

# V8.3: AI detection vector sanitization
try:
    from ai_intelligence_engine import (
        validate_fingerprint_coherence, validate_identity_graph,
        plan_session_rhythm, generate_navigation_path, audit_profile,
    )
    AI_V83_OK = True
except ImportError:
    AI_V83_OK = False


class ForgeWorker(QThread):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(dict)

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self._stop_flag = __import__('threading').Event()

    def stop(self):
        """V8.3 FIX #2: Signal worker to stop cleanly."""
        self._stop_flag.set()

    def run(self):
        result = {"success": False, "error": "Genesis not available"}
        if not GENESIS_OK:
            self.finished.emit(result)
            return
        try:
            self.progress.emit(5, "Initializing Genesis Engine...")
            engine = GenesisEngine()

            self.progress.emit(10, "Building profile config...")
            pc = ProfileConfig(
                target=self.config.get("target", "amazon.com"),
                persona_name=self.config.get("name", ""),
                persona_email=self.config.get("email", ""),
                age_days=self.config.get("age_days", 90),
            )

            self.progress.emit(20, "Forging browser profile...")
            profile = engine.generate(pc)
            profile_path = str(getattr(profile, 'path', ''))

            self.progress.emit(35, "Injecting purchase history...")
            if PURCHASE_OK and self.config.get("name"):
                try:
                    name_parts = self.config["name"].split()
                    ch = CardHolderData(
                        full_name=self.config.get("name", ""),
                        first_name=name_parts[0] if name_parts else "",
                        last_name=name_parts[-1] if len(name_parts) > 1 else "",
                        card_last_four=self.config.get("card_last4", "0000"),
                        card_network=self.config.get("card_network", "visa"),
                        card_exp_display=self.config.get("card_exp", "12/27"),
                        billing_address=self.config.get("street", ""),
                        billing_city=self.config.get("city", ""),
                        billing_state=self.config.get("state", ""),
                        billing_zip=self.config.get("zip", ""),
                        email=self.config.get("email", ""),
                        phone=self.config.get("phone", ""),
                    )
                    phe = PurchaseHistoryEngine()
                    phe.inject(profile_path, ch, num_purchases=random.randint(5, 12),
                               age_days=self.config.get("age_days", 90))
                except Exception as e:
                    self.progress.emit(37, f"Purchase history: {e}")

            if self._stop_flag.is_set():
                self.finished.emit({"success": False, "error": "Cancelled"})
                return

            self.progress.emit(45, "Synthesizing IndexedDB shards...")
            if IDB_OK:
                try:
                    idb = IndexedDBShardSynthesizer()
                    idb.synthesize(profile_path, target=self.config.get("target", ""), age_days=self.config.get("age_days", 90))
                except Exception as e:
                    import logging; logging.getLogger("TITAN-FORGE").error(f"IDB synthesis failed: {e}", exc_info=True)

            if self._stop_flag.is_set():
                self.finished.emit({"success": False, "error": "Cancelled"})
                return

            self.progress.emit(55, "Eliminating first-session bias...")
            if FSB_OK:
                try:
                    FirstSessionBiasEliminator().eliminate(profile_path)
                except Exception as e:
                    import logging; logging.getLogger("TITAN-FORGE").error(f"FSB elimination failed: {e}", exc_info=True)

            self.progress.emit(60, "Injecting Chrome commerce funnel...")
            if CHROME_COMMERCE_OK and profile_path:
                try:
                    history_db = os.path.join(profile_path, "Default", "History")
                    if os.path.exists(history_db):
                        target = self.config.get("target", "amazon.com")
                        inject_golden_chain(history_db, f"https://{target}", f"ORD-{random.randint(10000, 99999)}")
                except Exception as e:
                    import logging; logging.getLogger("TITAN-FORGE").error(f"Commerce injection failed: {e}", exc_info=True)

            self.progress.emit(68, "Generating forensic cache mass...")
            if CACHE_OK:
                try:
                    Cache2Synthesizer().synthesize(profile_path, target_mb=self.config.get("storage_mb", 500))
                except Exception as e:
                    import logging; logging.getLogger("TITAN-FORGE").error(f"Cache synthesis failed: {e}", exc_info=True)

            self.progress.emit(78, "Applying fingerprint hardening...")
            if FONT_OK:
                try:
                    FontSanitizer().sanitize(profile_path)
                except Exception as e:
                    import logging; logging.getLogger("TITAN-FORGE").error(f"Font sanitizer failed: {e}", exc_info=True)
            if AUDIO_OK:
                try:
                    AudioHardener().harden(profile_path)
                except Exception as e:
                    import logging; logging.getLogger("TITAN-FORGE").error(f"Audio hardener failed: {e}", exc_info=True)

            self.progress.emit(88, "Running realism analysis...")
            quality_score = 0
            if REALISM_OK:
                try:
                    score_result = ProfileRealismEngine().score(profile_path)
                    quality_score = getattr(score_result, 'score', 0) if hasattr(score_result, 'score') else 75
                except Exception as e:
                    import logging; logging.getLogger("TITAN-FORGE").error(f"Realism scoring failed: {e}", exc_info=True)
                    quality_score = 70

            # V8.3: AI fingerprint coherence + identity graph validation
            fp_coherence = None
            id_graph = None
            if AI_V83_OK:
                try:
                    self.progress.emit(90, "V8.3: Validating fingerprint coherence...")
                    fp_config = {
                        "user_agent": self.config.get("user_agent", ""),
                        "webgl_renderer": self.config.get("webgl_renderer", ""),
                        "hardware_concurrency": self.config.get("hw_concurrency", 16),
                        "screen_resolution": self.config.get("screen_res", "1920x1080"),
                        "timezone": self.config.get("timezone", ""),
                        "locale": self.config.get("locale", "en-US"),
                        "platform": self.config.get("platform", "Win32"),
                    }
                    fp_coherence = validate_fingerprint_coherence(fp_config)
                    if fp_coherence and fp_coherence.ai_powered:
                        quality_score = int(quality_score * 0.6 + fp_coherence.score * 0.4)
                except Exception as e:
                    import logging; logging.getLogger("TITAN-FORGE").error(f"FP coherence check failed: {e}", exc_info=True)

                try:
                    self.progress.emit(93, "V8.3: Validating identity graph...")
                    persona = {
                        "name": self.config.get("name", ""),
                        "email": self.config.get("email", ""),
                        "phone": self.config.get("phone", ""),
                        "street": self.config.get("street", ""),
                        "city": self.config.get("city", ""),
                        "state": self.config.get("state", ""),
                        "zip": self.config.get("zip", ""),
                        "card_bin": self.config.get("card_bin", ""),
                        "card_network": self.config.get("card_network", ""),
                    }
                    id_graph = validate_identity_graph(persona)
                except Exception as e:
                    import logging; logging.getLogger("TITAN-FORGE").error(f"Identity graph check failed: {e}", exc_info=True)

            self.progress.emit(97, "Finalizing...")
            result = {
                "success": True,
                "profile_path": profile_path,
                "profile_id": str(getattr(profile, 'uuid', '')),
                "quality_score": quality_score,
                "layers_applied": sum([PURCHASE_OK, IDB_OK, FSB_OK, CHROME_COMMERCE_OK, CACHE_OK, FONT_OK, AUDIO_OK, REALISM_OK]),
                "v83_fp_coherence": fp_coherence.score if fp_coherence and fp_coherence.ai_powered else None,
                "v83_fp_issues": fp_coherence.mismatches if fp_coherence and fp_coherence.ai_powered else [],
                "v83_id_plausible": id_graph.plausible if id_graph and id_graph.ai_powered else None,
                "v83_id_anomalies": id_graph.anomalies if id_graph and id_graph.ai_powered else [],
            }
            self.progress.emit(100, f"Profile forged — Quality: {quality_score}/100")
        except Exception as e:
            result = {"success": False, "error": str(e)}
        self.finished.emit(result)


class TitanProfileForge(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.apply_theme()

    def apply_theme(self):
        if THEME_OK:
            apply_titan_theme(self, ACCENT)
            self.tabs.setStyleSheet(make_tab_style(ACCENT))
        else:
            self.setStyleSheet(f"background: {BG}; color: {TEXT};")

    def init_ui(self):
        self.setWindowTitle("TITAN V8.2 — Profile Forge")
        self.setMinimumSize(1000, 750)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)

        hdr = QLabel("PROFILE FORGE")
        hdr.setFont(QFont("Inter", 18, QFont.Weight.Bold))
        hdr.setStyleSheet(f"color: {ACCENT};")
        layout.addWidget(hdr)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self._build_identity_tab()
        self._build_forge_tab()
        self._build_profiles_tab()

    def _build_identity_tab(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(tab)
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        # Persona
        pgrp = QGroupBox("Persona Identity")
        pf = QFormLayout(pgrp)
        self.id_name = QLineEdit()
        self.id_name.setPlaceholderText("Full name")
        pf.addRow("Name:", self.id_name)
        self.id_email = QLineEdit()
        self.id_email.setPlaceholderText("email@provider.com")
        pf.addRow("Email:", self.id_email)
        self.id_phone = QLineEdit()
        self.id_phone.setPlaceholderText("+1-555-000-0000")
        pf.addRow("Phone:", self.id_phone)
        layout.addWidget(pgrp)

        # Address
        agrp = QGroupBox("Billing Address")
        af = QFormLayout(agrp)
        self.id_street = QLineEdit()
        self.id_street.setPlaceholderText("123 Main St")
        af.addRow("Street:", self.id_street)
        self.id_city = QLineEdit()
        af.addRow("City:", self.id_city)
        self.id_state = QLineEdit()
        self.id_state.setPlaceholderText("e.g., NY, CA, TX")
        af.addRow("State:", self.id_state)
        self.id_zip = QLineEdit()
        af.addRow("ZIP:", self.id_zip)
        layout.addWidget(agrp)

        # Card
        cgrp = QGroupBox("Card Details")
        cf = QFormLayout(cgrp)
        self.id_card_last4 = QLineEdit()
        self.id_card_last4.setPlaceholderText("Last 4 digits")
        self.id_card_last4.setMaxLength(4)
        cf.addRow("Last 4:", self.id_card_last4)
        self.id_card_network = QComboBox()
        self.id_card_network.addItems(["visa", "mastercard", "amex", "discover"])
        cf.addRow("Network:", self.id_card_network)
        self.id_card_exp = QLineEdit()
        self.id_card_exp.setPlaceholderText("MM/YY")
        self.id_card_exp.setMaxLength(5)
        cf.addRow("Expiry:", self.id_card_exp)
        layout.addWidget(cgrp)

        # Target
        tgrp = QGroupBox("Target Configuration")
        tf = QFormLayout(tgrp)
        self.id_target = QComboBox()
        self.id_target.setEditable(True)
        self.id_target.addItems(["amazon.com", "ebay.com", "walmart.com", "bestbuy.com", "target.com", "shopify.com", "stripe.com"])
        tf.addRow("Target:", self.id_target)
        self.id_age = QSpinBox()
        self.id_age.setRange(7, 365)
        self.id_age.setValue(90)
        self.id_age.setSuffix(" days")
        tf.addRow("Profile Age:", self.id_age)
        self.id_storage = QSpinBox()
        self.id_storage.setRange(50, 5000)
        self.id_storage.setValue(500)
        self.id_storage.setSuffix(" MB")
        tf.addRow("Cache Size:", self.id_storage)
        layout.addWidget(tgrp)

        layout.addStretch()
        self.tabs.addTab(scroll, "IDENTITY")

    def _build_forge_tab(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(tab)
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        # Pipeline status
        grp = QGroupBox("Forge Pipeline (9 Stages)")
        gf = QVBoxLayout(grp)
        layers = [
            ("Genesis Engine", GENESIS_OK),
            ("Purchase History", PURCHASE_OK),
            ("IndexedDB/LSNG", IDB_OK),
            ("First-Session Bias", FSB_OK),
            ("Chrome Commerce", CHROME_COMMERCE_OK),
            ("Forensic Cache", CACHE_OK),
            ("Font Sanitizer", FONT_OK),
            ("Audio Hardener", AUDIO_OK),
            ("Realism Scoring", REALISM_OK),
        ]
        for name, ok in layers:
            row = QHBoxLayout()
            dot = QLabel("●")
            dot.setStyleSheet(f"color: {GREEN if ok else RED}; font-size: 10px;")
            dot.setFixedWidth(14)
            row.addWidget(dot)
            row.addWidget(QLabel(name))
            row.addStretch()
            gf.addLayout(row)
        layout.addWidget(grp)

        # Progress
        self.forge_progress = QProgressBar()
        self.forge_progress.setValue(0)
        layout.addWidget(self.forge_progress)

        self.forge_status = QLabel("Ready to forge")
        self.forge_status.setStyleSheet(f"color: {TEXT2};")
        layout.addWidget(self.forge_status)

        # Forge button
        self.forge_btn = QPushButton("FORGE PROFILE")
        self.forge_btn.setStyleSheet(f"background: {ACCENT}; color: white; padding: 14px 32px; border-radius: 8px; font-weight: bold; font-size: 14px;")
        self.forge_btn.clicked.connect(self._start_forge)
        layout.addWidget(self.forge_btn)

        # Output
        self.forge_output = QPlainTextEdit()
        self.forge_output.setReadOnly(True)
        self.forge_output.setMinimumHeight(200)
        self.forge_output.setPlaceholderText("Forge output will appear here...")
        layout.addWidget(self.forge_output)

        layout.addStretch()
        self.tabs.addTab(scroll, "FORGE")

    def _build_profiles_tab(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(tab)
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        grp = QGroupBox("Generated Profiles")
        gf = QVBoxLayout(grp)

        self.profiles_table = QTableWidget()
        self.profiles_table.setColumnCount(5)
        self.profiles_table.setHorizontalHeaderLabels(["ID", "Target", "Age", "Quality", "Created"])
        self.profiles_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.profiles_table.setMinimumHeight(400)
        gf.addWidget(self.profiles_table)

        btn_row = QHBoxLayout()
        refresh = QPushButton("Refresh")
        refresh.setStyleSheet(f"background: {BG_CARD}; color: {TEXT}; padding: 8px 16px; border: 1px solid #334155; border-radius: 6px;")
        refresh.clicked.connect(self._refresh_profiles)
        btn_row.addWidget(refresh)
        btn_row.addStretch()
        gf.addLayout(btn_row)

        layout.addWidget(grp)
        layout.addStretch()
        self.tabs.addTab(scroll, "PROFILES")

    def _start_forge(self):
        config = {
            "target": self.id_target.currentText(),
            "name": self.id_name.text().strip(),
            "email": self.id_email.text().strip(),
            "phone": self.id_phone.text().strip(),
            "street": self.id_street.text().strip(),
            "city": self.id_city.text().strip(),
            "state": self.id_state.text().strip(),
            "zip": self.id_zip.text().strip(),
            "card_last4": self.id_card_last4.text().strip(),
            "card_network": self.id_card_network.currentText(),
            "card_exp": self.id_card_exp.text().strip(),
            "age_days": self.id_age.value(),
            "storage_mb": self.id_storage.value(),
        }
        self.forge_btn.setEnabled(False)
        self.forge_progress.setValue(0)
        self.forge_output.clear()
        self.worker = ForgeWorker(config)
        self.worker.progress.connect(self._on_forge_progress)
        self.worker.finished.connect(self._on_forge_done)
        self.worker.start()

    def _on_forge_progress(self, pct, msg):
        self.forge_progress.setValue(pct)
        self.forge_status.setText(msg)
        self.forge_output.appendPlainText(f"[{pct}%] {msg}")

    def _on_forge_done(self, result):
        self.forge_btn.setEnabled(True)
        if result.get("success"):
            self.forge_output.appendPlainText(f"\nSUCCESS — Quality: {result.get('quality_score', 0)}/100")
            self.forge_output.appendPlainText(f"Path: {result.get('profile_path', 'N/A')}")
            self.forge_output.appendPlainText(f"Layers: {result.get('layers_applied', 0)}")
            if SESSION_OK:
                try:
                    update_session(
                        last_profile_path=result.get("profile_path", ""),
                        last_profile_id=result.get("profile_id", ""),
                        last_forge_quality=result.get("quality_score", 0),
                    )
                except Exception:
                    pass
        else:
            self.forge_output.appendPlainText(f"\nFAILED: {result.get('error', 'Unknown')}")

    def _refresh_profiles(self):
        profiles_dir = Path("/opt/titan/profiles")
        if not profiles_dir.exists():
            return
        self.profiles_table.setRowCount(0)
        for d in sorted(profiles_dir.iterdir(), reverse=True):
            if d.is_dir():
                row = self.profiles_table.rowCount()
                self.profiles_table.insertRow(row)
                self.profiles_table.setItem(row, 0, QTableWidgetItem(d.name[:16]))
                meta_file = d / "titan_meta.json"
                if meta_file.exists():
                    try:
                        meta = json.loads(meta_file.read_text())
                        self.profiles_table.setItem(row, 1, QTableWidgetItem(meta.get("target", "")))
                        self.profiles_table.setItem(row, 2, QTableWidgetItem(f"{meta.get('age_days', '?')}d"))
                        self.profiles_table.setItem(row, 3, QTableWidgetItem(str(meta.get("quality_score", "?"))))
                        self.profiles_table.setItem(row, 4, QTableWidgetItem(meta.get("created", "")))
                    except Exception:
                        pass


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = TitanProfileForge()
    win.show()
    sys.exit(app.exec())
