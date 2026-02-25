#!/usr/bin/env python3
"""
TITAN V8.2 INTELLIGENCE CENTER — AI Analysis & Strategy
=========================================================
AI-powered analysis, 3DS strategy, detection analysis, real-time copilot.

5 tabs, 20 core modules wired (8 previously orphaned):
  1. AI COPILOT — Real-time AI guidance during operations
  2. 3DS STRATEGY — 3DS bypass planning, TRA exemptions, issuer defense
  3. DETECTION — Decline analysis, detection patterns, AI guard
  4. RECON — Target reconnaissance, antifraud profiling, TLS/JA4+
  5. MEMORY — Vector knowledge base, web intel, operation history
"""

import sys
import os
import json
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / "core"))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QTextEdit, QPushButton, QGroupBox, QFormLayout,
    QProgressBar, QMessageBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QFrame, QTabWidget, QComboBox, QSpinBox,
    QScrollArea, QCheckBox, QPlainTextEdit, QSplitter
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor, QPalette

# Theme
ACCENT = "#a855f7"
BG = "#0a0e17"
CARD = "#111827"
CARD2 = "#1e293b"
TXT = "#e2e8f0"
TXT2 = "#64748b"
GREEN = "#22c55e"
YELLOW = "#eab308"
RED = "#ef4444"
ORANGE = "#f97316"
CYAN = "#00d4ff"

# ═══════════════════════════════════════════════════════════════════════════════
# CORE IMPORTS — 20 modules (8 previously orphaned, now wired)
# ═══════════════════════════════════════════════════════════════════════════════

# V8.2: Cross-app session state
try:
    from titan_session import get_session, save_session
    _SESSION_OK = True
except ImportError:
    _SESSION_OK = False
    def get_session(): return {}
    def save_session(d): return False

# Tab 1: AI COPILOT
try:
    from titan_realtime_copilot import RealtimeCopilot as TitanRealtimeCopilot
    COPILOT_OK = True
except ImportError:
    COPILOT_OK = False

try:
    from ai_intelligence_engine import (
        is_ai_available, get_ai_status, analyze_bin, recon_target,
        advise_3ds, advise_preflight, tune_behavior, audit_profile,
        plan_operation, AIOperationPlan,
        # V8.3: Detection vector sanitization
        track_defense_changes, autopsy_decline, optimize_cross_session,
        validate_fingerprint_coherence, validate_identity_graph,
        score_environment_coherence, optimize_card_rotation,
    )
    AI_OK = True
except ImportError:
    AI_OK = False

try:
    from ollama_bridge import LLMLoadBalancer as OllamaBridge
    OLLAMA_OK = True
except ImportError:
    OLLAMA_OK = False

try:
    from titan_vector_memory import TitanVectorMemory
    VECTOR_OK = True
except ImportError:
    VECTOR_OK = False

try:
    from titan_agent_chain import TitanAgent, TitanToolRegistry
    AGENT_OK = True
except ImportError:
    AGENT_OK = False

# Tab 2: 3DS STRATEGY
try:
    from three_ds_strategy import (
        ThreeDSBypassEngine, get_3ds_bypass_score, get_3ds_bypass_plan,
        get_downgrade_attacks, get_psp_vulnerabilities, get_psd2_exemptions,
        NonVBVRecommendationEngine, get_non_vbv_recommendations,
        get_easy_countries, get_all_non_vbv_bins,
    )
    THREEDS_OK = True
except ImportError:
    THREEDS_OK = False

try:
    from titan_3ds_ai_exploits import ThreeDSAIEngine
    THREEDS_AI_OK = True
except ImportError:
    THREEDS_AI_OK = False

try:
    from tra_exemption_engine import (
        TRAOptimizer as TRAExemptionEngine, TRARiskCalculator, get_tra_calculator,
    )
    TRA_OK = True
except ImportError:
    TRA_OK = False

try:
    from issuer_algo_defense import (
        IssuerDeclineDefenseEngine as IssuerDefenseEngine,
        IssuerAlgorithmModeler, VelocityOptimizer, AmountOptimizer,
    )
    ISSUER_OK = True
except ImportError:
    ISSUER_OK = False

# Tab 3: DETECTION
try:
    from titan_detection_analyzer import DetectionAnalyzer as TitanDetectionAnalyzer
    DETECT_OK = True
except ImportError:
    DETECT_OK = False

try:
    from titan_ai_operations_guard import AIOperationsGuard as TitanAIOperationsGuard
    GUARD_OK = True
except ImportError:
    GUARD_OK = False

try:
    from transaction_monitor import TransactionMonitor, DeclineDecoder, decode_decline
    TX_MON_OK = True
except ImportError:
    TX_MON_OK = False

# Tab 4: RECON
try:
    from titan_target_intel_v2 import TargetIntelV2
    INTEL_V2_OK = True
except ImportError:
    INTEL_V2_OK = False

try:
    from target_intelligence import get_target_intel, get_avs_intelligence, get_proxy_intelligence
    INTEL_OK = True
except ImportError:
    INTEL_OK = False

try:
    from titan_web_intel import TitanWebIntel
    WEB_INTEL_OK = True
except ImportError:
    WEB_INTEL_OK = False

try:
    from tls_parrot import TLSParrotEngine
    TLS_OK = True
except ImportError:
    TLS_OK = False

try:
    from ja4_permutation_engine import JA4PermutationEngine, ClientHelloInterceptor
    JA4_OK = True
except ImportError:
    JA4_OK = False

# Tab 5: MEMORY
try:
    from cognitive_core import TitanCognitiveCore
    COGNITIVE_OK = True
except ImportError:
    COGNITIVE_OK = False

try:
    from intel_monitor import IntelMonitor
    INTEL_MON_OK = True
except ImportError:
    INTEL_MON_OK = False


# ═══════════════════════════════════════════════════════════════════════════════
# WORKERS
# ═══════════════════════════════════════════════════════════════════════════════

class AIQueryWorker(QThread):
    """V8.11: Streaming AI worker — emits chunks via progress signal for non-blocking UI."""
    finished = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, query, context="", parent=None):
        super().__init__(parent)
        self.query = query
        self.context = context

    def run(self):
        result = "AI not available"
        if OLLAMA_OK:
            try:
                bridge = OllamaBridge()
                # V8.11: Try streaming first for responsive UI
                if hasattr(bridge, 'query_stream'):
                    chunks = []
                    for chunk in bridge.query_stream(self.query, context=self.context):
                        chunks.append(chunk)
                        self.progress.emit(chunk)
                    result = "".join(chunks)
                else:
                    self.progress.emit("Querying AI (this may take a moment)...")
                    result = bridge.query(self.query, context=self.context)
            except Exception as e:
                result = f"Ollama error: {e}"
        elif AI_OK:
            try:
                self.progress.emit("Running AI analysis...")
                plan = plan_operation(self.query)
                result = json.dumps(plan.__dict__ if hasattr(plan, '__dict__') else str(plan), indent=2, default=str)
            except Exception as e:
                result = f"AI error: {e}"
        self.finished.emit(result)


class ReconWorker(QThread):
    finished = pyqtSignal(str)

    def __init__(self, target, parent=None):
        super().__init__(parent)
        self.target = target

    def run(self):
        parts = []
        if INTEL_V2_OK:
            try:
                intel = TargetIntelV2()
                result = intel.get_full_intel(self.target)
                parts.append("=== V2 FULL INTEL ===")
                parts.append(json.dumps(result, indent=2, default=str)[:3000])
            except Exception as e:
                parts.append(f"V2 Intel error: {e}")

        if INTEL_OK:
            try:
                avs = get_avs_intelligence(self.target)
                parts.append("\n=== AVS INTELLIGENCE ===")
                parts.append(json.dumps(avs, indent=2, default=str)[:1000])
            except:
                pass
            try:
                proxy = get_proxy_intelligence(self.target)
                parts.append("\n=== PROXY INTELLIGENCE ===")
                parts.append(json.dumps(proxy, indent=2, default=str)[:1000])
            except:
                pass

        if WEB_INTEL_OK:
            try:
                wi = TitanWebIntel()
                report = wi.research(self.target)
                parts.append("\n=== WEB INTEL ===")
                parts.append(json.dumps(report.__dict__ if hasattr(report, '__dict__') else str(report), indent=2, default=str)[:2000])
            except Exception as e:
                parts.append(f"Web Intel error: {e}")

        self.finished.emit("\n".join(parts) if parts else "No intelligence modules available")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN WINDOW
# ═══════════════════════════════════════════════════════════════════════════════

class TitanIntelligence(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.apply_theme()
        QTimer.singleShot(300, self._restore_session_context)

    def init_ui(self):
        self.setWindowTitle("TITAN V8.2 — Intelligence Center")
        try:
            from titan_icon import set_titan_icon
            set_titan_icon(self, ACCENT)
        except:
            pass
        self.setMinimumSize(1200, 900)

        central = QWidget()
        self.setCentralWidget(central)
        main = QVBoxLayout(central)
        main.setContentsMargins(6, 6, 6, 6)
        main.setSpacing(4)

        # Header
        hdr = QHBoxLayout()
        title = QLabel("INTELLIGENCE CENTER")
        title.setFont(QFont("Inter", 18, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {ACCENT};")
        hdr.addWidget(title)

        # Module count
        available = sum([COPILOT_OK, AI_OK, OLLAMA_OK, VECTOR_OK, AGENT_OK, THREEDS_OK,
                        THREEDS_AI_OK, TRA_OK, ISSUER_OK, DETECT_OK, GUARD_OK, TX_MON_OK,
                        INTEL_V2_OK, INTEL_OK, WEB_INTEL_OK, TLS_OK, JA4_OK, COGNITIVE_OK, INTEL_MON_OK])
        mod_lbl = QLabel(f"{available}/20 modules active")
        mod_lbl.setFont(QFont("JetBrains Mono", 10))
        mod_lbl.setStyleSheet(f"color: {GREEN if available >= 15 else YELLOW if available >= 8 else RED};")
        mod_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        hdr.addWidget(mod_lbl)
        main.addLayout(hdr)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabBar::tab {{
                padding: 10px 24px; min-width: 140px;
                background: {CARD}; color: {TXT2};
                border: none; border-bottom: 2px solid transparent;
                font-weight: bold; font-size: 12px;
            }}
            QTabBar::tab:selected {{ color: {ACCENT}; border-bottom: 2px solid {ACCENT}; }}
            QTabBar::tab:hover {{ color: {TXT}; }}
            QTabWidget::pane {{ border: none; }}
        """)
        main.addWidget(self.tabs)

        self._build_copilot_tab()
        self._build_3ds_tab()
        self._build_detection_tab()
        self._build_recon_tab()
        self._build_memory_tab()

    # ═══════════════════════════════════════════════════════════════════════
    # TAB 1: AI COPILOT
    # ═══════════════════════════════════════════════════════════════════════

    def _build_copilot_tab(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(tab)
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        # Status bar
        status_grp = QGroupBox("AI Engine Status")
        sf = QHBoxLayout(status_grp)
        engines = [
            ("AI Intelligence", AI_OK),
            ("Ollama Bridge", OLLAMA_OK),
            ("Realtime Copilot", COPILOT_OK),
            ("Agent Chain", AGENT_OK),
            ("Vector Memory", VECTOR_OK),
        ]
        for name, ok in engines:
            dot = QLabel(f"{'●' if ok else '○'} {name}")
            dot.setStyleSheet(f"color: {GREEN if ok else RED}; font-size: 11px;")
            sf.addWidget(dot)
        sf.addStretch()
        layout.addWidget(status_grp)

        # Chat interface
        chat_grp = QGroupBox("AI Copilot")
        cf = QVBoxLayout(chat_grp)

        self.copilot_history = QTextEdit()
        self.copilot_history.setReadOnly(True)
        self.copilot_history.setMinimumHeight(350)
        self.copilot_history.setStyleSheet(f"font-family: 'JetBrains Mono'; font-size: 12px; background: #0f172a; color: {TXT}; border-radius: 6px;")
        self.copilot_history.setPlainText("TITAN AI Copilot ready. Ask anything about operations, strategy, or analysis.\n\nExamples:\n  - 'Plan an operation against amazon.com with BIN 476173'\n  - 'Analyze why my last 3 attempts on stripe failed'\n  - 'What 3DS bypass should I use for UK targets?'\n")
        cf.addWidget(self.copilot_history)

        input_row = QHBoxLayout()
        self.copilot_input = QLineEdit()
        self.copilot_input.setPlaceholderText("Ask the AI copilot...")
        self.copilot_input.setStyleSheet(f"padding: 10px; font-size: 13px;")
        self.copilot_input.returnPressed.connect(self._ask_copilot)
        input_row.addWidget(self.copilot_input)

        self.copilot_send = QPushButton("ASK")
        self.copilot_send.setStyleSheet(f"background: {ACCENT}; color: white; padding: 10px 20px; border-radius: 6px; font-weight: bold;")
        self.copilot_send.clicked.connect(self._ask_copilot)
        input_row.addWidget(self.copilot_send)
        cf.addLayout(input_row)

        # Quick actions
        qa_row = QHBoxLayout()
        for label, action in [
            ("Plan Operation", lambda: self._quick_ask("Plan a full operation for the current target")),
            ("Analyze BIN", lambda: self._quick_ask("Analyze BIN intelligence for the card I'm using")),
            ("3DS Advice", lambda: self._quick_ask("What 3DS strategy should I use for this target?")),
            ("Profile Audit", lambda: self._quick_ask("Audit my current profile for detection risks")),
        ]:
            btn = QPushButton(label)
            btn.setStyleSheet(f"background: {CARD2}; color: {TXT}; padding: 6px 12px; border-radius: 4px; font-size: 11px;")
            btn.clicked.connect(action)
            qa_row.addWidget(btn)
        qa_row.addStretch()
        cf.addLayout(qa_row)

        layout.addWidget(chat_grp)
        layout.addStretch()
        self.tabs.addTab(scroll, "AI COPILOT")

    # ═══════════════════════════════════════════════════════════════════════
    # TAB 2: 3DS STRATEGY
    # ═══════════════════════════════════════════════════════════════════════

    def _build_3ds_tab(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(tab)
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        # 3DS Bypass Planner
        bypass_grp = QGroupBox("3DS Bypass Planner")
        bf = QFormLayout(bypass_grp)

        self.tds_bin = QLineEdit()
        self.tds_bin.setPlaceholderText("Enter BIN (6-8 digits)")
        bf.addRow("BIN:", self.tds_bin)

        self.tds_target = QLineEdit()
        self.tds_target.setPlaceholderText("Target site (e.g., amazon.co.uk)")
        bf.addRow("Target:", self.tds_target)

        self.tds_amount = QLineEdit()
        self.tds_amount.setPlaceholderText("29.99")
        self.tds_amount.setFixedWidth(120)
        bf.addRow("Amount:", self.tds_amount)

        self.tds_country = QComboBox()
        self.tds_country.addItems(["US", "UK", "CA", "AU", "DE", "FR", "NL", "SE", "JP"])
        self.tds_country.setFixedWidth(80)
        bf.addRow("Country:", self.tds_country)

        btn_row = QHBoxLayout()
        self.tds_plan_btn = QPushButton("Generate Bypass Plan")
        self.tds_plan_btn.setStyleSheet(f"background: {ORANGE}; color: white; padding: 8px 16px; border-radius: 6px; font-weight: bold;")
        self.tds_plan_btn.clicked.connect(self._generate_3ds_plan)
        btn_row.addWidget(self.tds_plan_btn)

        self.tds_ai_btn = QPushButton("AI Exploit Analysis")
        self.tds_ai_btn.setStyleSheet(f"background: {ACCENT}; color: white; padding: 8px 16px; border-radius: 6px; font-weight: bold;")
        self.tds_ai_btn.clicked.connect(self._analyze_3ds_ai)
        btn_row.addWidget(self.tds_ai_btn)
        btn_row.addStretch()
        bf.addRow("", btn_row)

        layout.addWidget(bypass_grp)

        self.tds_output = QTextEdit()
        self.tds_output.setReadOnly(True)
        self.tds_output.setMinimumHeight(200)
        self.tds_output.setPlaceholderText("3DS bypass plan will appear here...")
        self.tds_output.setStyleSheet(f"font-family: 'JetBrains Mono'; font-size: 11px; background: #0f172a; color: {TXT}; border-radius: 6px;")
        layout.addWidget(self.tds_output)

        # TRA Exemptions
        tra_grp = QGroupBox("TRA Exemption Engine")
        tf = QVBoxLayout(tra_grp)

        tra_row = QHBoxLayout()
        self.tra_amount = QLineEdit()
        self.tra_amount.setPlaceholderText("Amount (EUR)")
        self.tra_amount.setFixedWidth(120)
        tra_row.addWidget(self.tra_amount)

        self.tra_btn = QPushButton("Calculate TRA")
        self.tra_btn.setStyleSheet(f"background: {CYAN}; color: black; padding: 6px 12px; border-radius: 6px; font-weight: bold;")
        self.tra_btn.clicked.connect(self._calculate_tra)
        tra_row.addWidget(self.tra_btn)
        tra_row.addStretch()
        tf.addLayout(tra_row)

        self.tra_output = QTextEdit()
        self.tra_output.setReadOnly(True)
        self.tra_output.setMaximumHeight(120)
        self.tra_output.setStyleSheet(f"font-family: 'JetBrains Mono'; font-size: 11px; background: #0f172a; color: {TXT}; border-radius: 6px;")
        tf.addWidget(self.tra_output)

        layout.addWidget(tra_grp)

        # Issuer Defense
        issuer_grp = QGroupBox("Issuer Algorithm Defense")
        idf = QVBoxLayout(issuer_grp)

        self.issuer_btn = QPushButton("Analyze Issuer Risk")
        self.issuer_btn.setStyleSheet(f"background: {RED}; color: white; padding: 6px 12px; border-radius: 6px; font-weight: bold;")
        self.issuer_btn.clicked.connect(self._analyze_issuer)
        idf.addWidget(self.issuer_btn)

        self.issuer_output = QTextEdit()
        self.issuer_output.setReadOnly(True)
        self.issuer_output.setMaximumHeight(120)
        self.issuer_output.setStyleSheet(f"font-family: 'JetBrains Mono'; font-size: 11px; background: #0f172a; color: {TXT}; border-radius: 6px;")
        idf.addWidget(self.issuer_output)

        layout.addWidget(issuer_grp)
        layout.addStretch()
        self.tabs.addTab(scroll, "3DS STRATEGY")

    # ═══════════════════════════════════════════════════════════════════════
    # TAB 3: DETECTION
    # ═══════════════════════════════════════════════════════════════════════

    def _build_detection_tab(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(tab)
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        # Detection Analyzer
        detect_grp = QGroupBox("Detection Analyzer")
        df = QVBoxLayout(detect_grp)

        self.detect_input = QTextEdit()
        self.detect_input.setMaximumHeight(100)
        self.detect_input.setPlaceholderText("Paste session logs, decline codes, or error messages for analysis...")
        self.detect_input.setStyleSheet(f"font-family: 'JetBrains Mono'; font-size: 11px; background: {CARD2}; color: {TXT}; border-radius: 6px;")
        df.addWidget(self.detect_input)

        det_btn_row = QHBoxLayout()
        self.detect_btn = QPushButton("Analyze Detection")
        self.detect_btn.setStyleSheet(f"background: {RED}; color: white; padding: 8px 16px; border-radius: 6px; font-weight: bold;")
        self.detect_btn.clicked.connect(self._analyze_detection)
        det_btn_row.addWidget(self.detect_btn)

        self.guard_btn = QPushButton("AI Operations Guard")
        self.guard_btn.setStyleSheet(f"background: {ORANGE}; color: white; padding: 8px 16px; border-radius: 6px; font-weight: bold;")
        self.guard_btn.clicked.connect(self._run_guard)
        det_btn_row.addWidget(self.guard_btn)
        det_btn_row.addStretch()
        df.addLayout(det_btn_row)

        self.detect_output = QTextEdit()
        self.detect_output.setReadOnly(True)
        self.detect_output.setMinimumHeight(250)
        self.detect_output.setPlaceholderText("Detection analysis results...")
        self.detect_output.setStyleSheet(f"font-family: 'JetBrains Mono'; font-size: 11px; background: #0f172a; color: {TXT}; border-radius: 6px;")
        df.addWidget(self.detect_output)

        layout.addWidget(detect_grp)

        # Decline Pattern Analysis
        dec_grp = QGroupBox("Decline Pattern Analysis")
        dcf = QVBoxLayout(dec_grp)

        dec_row = QHBoxLayout()
        self.dec_code = QLineEdit()
        self.dec_code.setPlaceholderText("Decline code (e.g., 05, 51, do_not_honor)")
        dec_row.addWidget(self.dec_code)
        self.dec_btn = QPushButton("Decode")
        self.dec_btn.setStyleSheet(f"background: {YELLOW}; color: black; padding: 6px 12px; border-radius: 6px; font-weight: bold;")
        self.dec_btn.clicked.connect(self._decode_decline)
        dec_row.addWidget(self.dec_btn)
        dcf.addLayout(dec_row)

        self.dec_output = QTextEdit()
        self.dec_output.setReadOnly(True)
        self.dec_output.setMaximumHeight(120)
        self.dec_output.setStyleSheet(f"font-family: 'JetBrains Mono'; font-size: 11px; background: #0f172a; color: {TXT}; border-radius: 6px;")
        dcf.addWidget(self.dec_output)

        layout.addWidget(dec_grp)
        layout.addStretch()
        self.tabs.addTab(scroll, "DETECTION")

    # ═══════════════════════════════════════════════════════════════════════
    # TAB 4: RECON
    # ═══════════════════════════════════════════════════════════════════════

    def _build_recon_tab(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(tab)
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        # Target Recon
        recon_grp = QGroupBox("Target Reconnaissance")
        rf = QVBoxLayout(recon_grp)

        recon_row = QHBoxLayout()
        self.recon_target = QLineEdit()
        self.recon_target.setPlaceholderText("Enter target URL (e.g., amazon.com, stripe.com)")
        recon_row.addWidget(self.recon_target)

        self.recon_btn = QPushButton("FULL RECON")
        self.recon_btn.setStyleSheet(f"background: {ACCENT}; color: white; padding: 10px 20px; border-radius: 6px; font-weight: bold;")
        self.recon_btn.clicked.connect(self._run_recon)
        recon_row.addWidget(self.recon_btn)
        rf.addLayout(recon_row)

        self.recon_output = QTextEdit()
        self.recon_output.setReadOnly(True)
        self.recon_output.setMinimumHeight(250)
        self.recon_output.setPlaceholderText("Target intelligence will appear here...")
        self.recon_output.setStyleSheet(f"font-family: 'JetBrains Mono'; font-size: 11px; background: #0f172a; color: {TXT}; border-radius: 6px;")
        rf.addWidget(self.recon_output)

        layout.addWidget(recon_grp)

        # TLS/JA4+ Fingerprint
        tls_grp = QGroupBox("TLS / JA4+ Fingerprint Analysis")
        tf = QVBoxLayout(tls_grp)

        tls_row = QHBoxLayout()
        self.tls_target = QLineEdit()
        self.tls_target.setPlaceholderText("Target for TLS analysis")
        tls_row.addWidget(self.tls_target)

        self.ja4_btn = QPushButton("Generate JA4+")
        self.ja4_btn.setStyleSheet(f"background: {CYAN}; color: black; padding: 6px 12px; border-radius: 6px; font-weight: bold;")
        self.ja4_btn.clicked.connect(self._generate_ja4)
        tls_row.addWidget(self.ja4_btn)

        self.tls_btn = QPushButton("TLS Parrot")
        self.tls_btn.setStyleSheet(f"background: {GREEN}; color: black; padding: 6px 12px; border-radius: 6px; font-weight: bold;")
        self.tls_btn.clicked.connect(self._run_tls_parrot)
        tls_row.addWidget(self.tls_btn)
        tf.addLayout(tls_row)

        self.tls_output = QTextEdit()
        self.tls_output.setReadOnly(True)
        self.tls_output.setMaximumHeight(150)
        self.tls_output.setStyleSheet(f"font-family: 'JetBrains Mono'; font-size: 11px; background: #0f172a; color: {TXT}; border-radius: 6px;")
        tf.addWidget(self.tls_output)

        layout.addWidget(tls_grp)
        layout.addStretch()
        self.tabs.addTab(scroll, "RECON")

    # ═══════════════════════════════════════════════════════════════════════
    # TAB 5: MEMORY
    # ═══════════════════════════════════════════════════════════════════════

    def _build_memory_tab(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(tab)
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        # Vector Memory Search
        vec_grp = QGroupBox("Vector Memory (Knowledge Base)")
        vf = QVBoxLayout(vec_grp)

        vec_row = QHBoxLayout()
        self.vec_query = QLineEdit()
        self.vec_query.setPlaceholderText("Search knowledge base (e.g., 'stripe 3DS bypass methods')")
        vec_row.addWidget(self.vec_query)
        self.vec_search_btn = QPushButton("Search")
        self.vec_search_btn.setStyleSheet(f"background: {ACCENT}; color: white; padding: 6px 12px; border-radius: 6px; font-weight: bold;")
        self.vec_search_btn.clicked.connect(self._search_memory)
        vec_row.addWidget(self.vec_search_btn)
        vf.addLayout(vec_row)

        self.vec_output = QTextEdit()
        self.vec_output.setReadOnly(True)
        self.vec_output.setMinimumHeight(200)
        self.vec_output.setPlaceholderText("Search results from vector memory...")
        self.vec_output.setStyleSheet(f"font-family: 'JetBrains Mono'; font-size: 11px; background: #0f172a; color: {TXT}; border-radius: 6px;")
        vf.addWidget(self.vec_output)

        layout.addWidget(vec_grp)

        # Store Memory
        store_grp = QGroupBox("Store Knowledge")
        stf = QVBoxLayout(store_grp)

        self.store_key = QLineEdit()
        self.store_key.setPlaceholderText("Topic/key (e.g., 'stripe_us_bypass')")
        stf.addWidget(self.store_key)

        self.store_value = QTextEdit()
        self.store_value.setMaximumHeight(100)
        self.store_value.setPlaceholderText("Knowledge to store...")
        self.store_value.setStyleSheet(f"font-family: 'JetBrains Mono'; font-size: 11px; background: {CARD2}; color: {TXT}; border-radius: 6px;")
        stf.addWidget(self.store_value)

        self.store_btn = QPushButton("Store in Memory")
        self.store_btn.setStyleSheet(f"background: {GREEN}; color: black; padding: 6px 12px; border-radius: 6px; font-weight: bold;")
        self.store_btn.clicked.connect(self._store_memory)
        stf.addWidget(self.store_btn)

        layout.addWidget(store_grp)

        # Web Intel
        web_grp = QGroupBox("Web Intelligence")
        wf = QVBoxLayout(web_grp)

        web_row = QHBoxLayout()
        self.web_query = QLineEdit()
        self.web_query.setPlaceholderText("Search web for target intelligence...")
        web_row.addWidget(self.web_query)
        self.web_btn = QPushButton("Research")
        self.web_btn.setStyleSheet(f"background: {ORANGE}; color: white; padding: 6px 12px; border-radius: 6px; font-weight: bold;")
        self.web_btn.clicked.connect(self._web_research)
        web_row.addWidget(self.web_btn)
        wf.addLayout(web_row)

        self.web_output = QTextEdit()
        self.web_output.setReadOnly(True)
        self.web_output.setMaximumHeight(150)
        self.web_output.setStyleSheet(f"font-family: 'JetBrains Mono'; font-size: 11px; background: #0f172a; color: {TXT}; border-radius: 6px;")
        wf.addWidget(self.web_output)

        layout.addWidget(web_grp)
        layout.addStretch()
        self.tabs.addTab(scroll, "MEMORY")

    # ═══════════════════════════════════════════════════════════════════════
    # V8.2: SESSION CONTEXT — auto-populate from Operations Center
    # ═══════════════════════════════════════════════════════════════════════

    def _restore_session_context(self):
        """Read shared session and auto-populate fields from Operations Center."""
        if not _SESSION_OK:
            return
        try:
            s = get_session()
            target = s.get("current_target", "")
            card = s.get("card", {})
            bin_prefix = card.get("number", "")[:8] if card.get("number") else ""

            if target:
                self.tds_target.setText(target)
                self.recon_target.setText(target)
                self.tls_target.setText(target)
            if bin_prefix:
                self.tds_bin.setText(bin_prefix)
        except Exception:
            pass

    def _get_session_context(self) -> str:
        """Build context string from shared session for AI queries."""
        if not _SESSION_OK:
            return ""
        try:
            s = get_session()
            parts = []
            if s.get("current_target"):
                parts.append(f"Target: {s['current_target']}")
            if s.get("card", {}).get("number"):
                parts.append(f"BIN: {s['card']['number'][:8]}")
            if s.get("current_country"):
                parts.append(f"Country: {s['current_country']}")
            if s.get("current_proxy"):
                parts.append(f"Proxy: {s['current_proxy']}")
            if s.get("vpn_status", {}).get("connected"):
                parts.append(f"VPN: {s['vpn_status'].get('exit_ip', 'connected')}")
            if s.get("last_validation", {}).get("status"):
                parts.append(f"Last validation: {s['last_validation']['status']}")
            return "Current session: " + " | ".join(parts) if parts else ""
        except Exception:
            return ""

    # ═══════════════════════════════════════════════════════════════════════
    # ACTIONS
    # ═══════════════════════════════════════════════════════════════════════

    def _ask_copilot(self):
        query = self.copilot_input.text().strip()
        if not query:
            return
        self.copilot_input.clear()
        self.copilot_history.append(f"\n> {query}")
        self.copilot_send.setEnabled(False)

        context = self._get_session_context()
        self._ai_worker = AIQueryWorker(query, context=context)
        self._ai_worker.finished.connect(self._on_copilot_response)
        self._ai_worker.start()

    def _quick_ask(self, query):
        self.copilot_input.setText(query)
        self._ask_copilot()

    def _on_copilot_response(self, response):
        self.copilot_send.setEnabled(True)
        self.copilot_history.append(f"\n{response}\n{'─' * 60}")

    def _generate_3ds_plan(self):
        if not THREEDS_OK:
            self.tds_output.setPlainText("3DS Strategy module not available")
            return
        try:
            target = self.tds_target.text().strip()
            bin_val = self.tds_bin.text().strip()
            parts = []

            plan = get_3ds_bypass_plan(target)
            parts.append("=== BYPASS PLAN ===")
            parts.append(json.dumps(plan, indent=2, default=str)[:1500])

            if bin_val:
                score = get_3ds_bypass_score(bin_val)
                parts.append(f"\n=== BIN BYPASS SCORE ===")
                parts.append(json.dumps(score, indent=2, default=str)[:500])

            vulns = get_psp_vulnerabilities(target)
            parts.append(f"\n=== PSP VULNERABILITIES ===")
            parts.append(json.dumps(vulns, indent=2, default=str)[:800])

            self.tds_output.setPlainText("\n".join(parts))
        except Exception as e:
            self.tds_output.setPlainText(f"3DS plan error: {e}")

    def _analyze_3ds_ai(self):
        if not THREEDS_AI_OK:
            self.tds_output.setPlainText("3DS AI Exploits module not available")
            return
        try:
            engine = ThreeDSAIEngine()
            target = self.tds_target.text().strip()
            result = engine.analyze(target, self.tds_bin.text().strip())
            self.tds_output.setPlainText(json.dumps(result.__dict__ if hasattr(result, '__dict__') else str(result), indent=2, default=str)[:3000])
        except Exception as e:
            self.tds_output.setPlainText(f"AI 3DS analysis error: {e}")

    def _calculate_tra(self):
        if not TRA_OK:
            self.tra_output.setPlainText("TRA Exemption Engine not available")
            return
        try:
            amount = float(self.tra_amount.text() or "0")
            calculator = get_tra_calculator()
            score = calculator.calculate_score(amount) if hasattr(calculator, 'calculate_score') else calculator.score(amount) if hasattr(calculator, 'score') else str(calculator)
            exemption = calculator.get_optimal_exemption(amount) if hasattr(calculator, 'get_optimal_exemption') else calculator.optimize(amount) if hasattr(calculator, 'optimize') else "N/A"
            result = f"TRA Score: {json.dumps(score, indent=2, default=str) if isinstance(score, dict) else score}\nOptimal Exemption: {json.dumps(exemption.__dict__ if hasattr(exemption, '__dict__') else str(exemption), indent=2, default=str)}"
            self.tra_output.setPlainText(result)
        except Exception as e:
            self.tra_output.setPlainText(f"TRA calculation error: {e}")

    def _analyze_issuer(self):
        if not ISSUER_OK:
            self.issuer_output.setPlainText("Issuer Defense Engine not available")
            return
        try:
            bin_val = self.tds_bin.text().strip()
            engine = IssuerDefenseEngine()
            risk = engine.calculate_decline_risk(bin_val) if hasattr(engine, 'calculate_decline_risk') else engine.analyze(bin_val) if hasattr(engine, 'analyze') else str(engine)
            strategy = engine.get_mitigation_strategy(bin_val) if hasattr(engine, 'get_mitigation_strategy') else engine.mitigate(bin_val) if hasattr(engine, 'mitigate') else "N/A"
            result = f"Decline Risk: {json.dumps(risk.__dict__ if hasattr(risk, '__dict__') else risk, indent=2, default=str)}\n\nMitigation: {json.dumps(strategy.__dict__ if hasattr(strategy, '__dict__') else strategy, indent=2, default=str)}"
            self.issuer_output.setPlainText(result[:2000])
        except Exception as e:
            self.issuer_output.setPlainText(f"Issuer analysis error: {e}")

    def _analyze_detection(self):
        logs = self.detect_input.toPlainText().strip()
        if not logs:
            self.detect_output.setPlainText("Paste session logs or decline codes above")
            return

        parts = []
        if DETECT_OK:
            try:
                analyzer = TitanDetectionAnalyzer()
                result = analyzer.analyze(logs)
                parts.append("=== DETECTION ANALYSIS ===")
                parts.append(json.dumps(result.__dict__ if hasattr(result, '__dict__') else str(result), indent=2, default=str)[:2000])
            except Exception as e:
                parts.append(f"Detection analysis error: {e}")

        if AI_OK:
            try:
                advice = advise_preflight(logs)
                parts.append("\n=== AI ADVICE ===")
                parts.append(str(advice)[:1000])
            except:
                pass

        self.detect_output.setPlainText("\n".join(parts) if parts else "Detection analyzer not available")

    def _run_guard(self):
        if not GUARD_OK:
            self.detect_output.setPlainText("AI Operations Guard not available")
            return
        try:
            guard = TitanAIOperationsGuard()
            status = guard.get_status() if hasattr(guard, 'get_status') else str(guard)
            self.detect_output.setPlainText(f"Operations Guard Status:\n{json.dumps(status, indent=2, default=str)[:2000]}")
        except Exception as e:
            self.detect_output.setPlainText(f"Guard error: {e}")

    def _decode_decline(self):
        code = self.dec_code.text().strip()
        if not code:
            return
        if TX_MON_OK:
            try:
                result = decode_decline(code)
                self.dec_output.setPlainText(json.dumps(result.__dict__ if hasattr(result, '__dict__') else str(result), indent=2, default=str)[:1000])
            except Exception as e:
                self.dec_output.setPlainText(f"Decode error: {e}")
        else:
            self.dec_output.setPlainText("Decline Decoder not available")

    def _run_recon(self):
        target = self.recon_target.text().strip()
        if not target:
            return
        self.recon_btn.setEnabled(False)
        self.recon_output.setPlainText("Running full reconnaissance...")

        self._recon_worker = ReconWorker(target)
        self._recon_worker.finished.connect(self._on_recon_done)
        self._recon_worker.start()

    def _on_recon_done(self, result):
        self.recon_btn.setEnabled(True)
        self.recon_output.setPlainText(result)

    def _generate_ja4(self):
        if not JA4_OK:
            self.tls_output.setPlainText("JA4+ Permutation Engine not available")
            return
        try:
            interceptor = ClientHelloInterceptor()
            fp = interceptor.generate() if hasattr(interceptor, 'generate') else interceptor.intercept() if hasattr(interceptor, 'intercept') else str(interceptor)
            self.tls_output.setPlainText(json.dumps(fp.__dict__ if hasattr(fp, '__dict__') else fp, indent=2, default=str)[:1500])
        except Exception as e:
            self.tls_output.setPlainText(f"JA4+ error: {e}")

    def _run_tls_parrot(self):
        if not TLS_OK:
            self.tls_output.setPlainText("TLS Parrot Engine not available")
            return
        try:
            engine = TLSParrotEngine()
            target = self.tls_target.text().strip() or "chrome_120"
            result = engine.parrot(target) if hasattr(engine, 'parrot') else engine.generate(target) if hasattr(engine, 'generate') else str(engine)
            self.tls_output.setPlainText(json.dumps(result.__dict__ if hasattr(result, '__dict__') else str(result), indent=2, default=str)[:1500])
        except Exception as e:
            self.tls_output.setPlainText(f"TLS Parrot error: {e}")

    def _search_memory(self):
        query = self.vec_query.text().strip()
        if not query:
            return
        if VECTOR_OK:
            try:
                mem = TitanVectorMemory()
                results = mem.search(query, top_k=10)
                output_parts = []
                for i, r in enumerate(results if isinstance(results, list) else [results]):
                    output_parts.append(f"--- Result {i+1} ---")
                    output_parts.append(json.dumps(r.__dict__ if hasattr(r, '__dict__') else str(r), indent=2, default=str)[:500])
                self.vec_output.setPlainText("\n".join(output_parts) if output_parts else "No results found")
            except Exception as e:
                self.vec_output.setPlainText(f"Vector search error: {e}")
        else:
            self.vec_output.setPlainText("Vector Memory not available")

    def _store_memory(self):
        key = self.store_key.text().strip()
        value = self.store_value.toPlainText().strip()
        if not key or not value:
            return
        if VECTOR_OK:
            try:
                mem = TitanVectorMemory()
                mem.store(key, value)
                self.store_key.clear()
                self.store_value.clear()
                QMessageBox.information(self, "Stored", f"Knowledge stored: {key}")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Store error: {e}")
        else:
            QMessageBox.warning(self, "Error", "Vector Memory not available")

    def _web_research(self):
        query = self.web_query.text().strip()
        if not query:
            return
        if WEB_INTEL_OK:
            try:
                wi = TitanWebIntel()
                report = wi.research(query)
                self.web_output.setPlainText(json.dumps(report.__dict__ if hasattr(report, '__dict__') else str(report), indent=2, default=str)[:2000])
            except Exception as e:
                self.web_output.setPlainText(f"Web intel error: {e}")
        else:
            self.web_output.setPlainText("Web Intel not available")

    # ═══════════════════════════════════════════════════════════════════════
    # THEME
    # ═══════════════════════════════════════════════════════════════════════

    def apply_theme(self):
        pal = QPalette()
        pal.setColor(QPalette.ColorRole.Window, QColor(BG))
        pal.setColor(QPalette.ColorRole.WindowText, QColor(TXT))
        pal.setColor(QPalette.ColorRole.Base, QColor(CARD))
        pal.setColor(QPalette.ColorRole.AlternateBase, QColor(CARD2))
        pal.setColor(QPalette.ColorRole.Text, QColor(TXT))
        pal.setColor(QPalette.ColorRole.Button, QColor(CARD))
        pal.setColor(QPalette.ColorRole.ButtonText, QColor(TXT))
        self.setPalette(pal)
        self.setStyleSheet(f"""
            QMainWindow {{ background: {BG}; }}
            QGroupBox {{
                background: {CARD}; border: 1px solid #1e293b; border-radius: 10px;
                margin-top: 16px; padding-top: 20px; color: {TXT}; font-weight: bold;
            }}
            QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 6px; color: {ACCENT}; }}
            QLineEdit, QComboBox, QSpinBox {{
                background: {CARD2}; color: {TXT}; border: 1px solid #334155;
                border-radius: 6px; padding: 8px; font-size: 12px;
            }}
            QLineEdit:focus, QComboBox:focus {{ border: 1px solid {ACCENT}; }}
            QTextEdit {{ background: #0f172a; color: {TXT}; border: 1px solid #1e293b; border-radius: 6px; }}
            QLabel {{ background: transparent; }}
            QScrollArea {{ border: none; }}
        """)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = TitanIntelligence()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
