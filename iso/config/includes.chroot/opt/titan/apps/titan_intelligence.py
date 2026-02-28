#!/usr/bin/env python3
"""
TITAN V9.1 INTELLIGENCE CENTER — AI Analysis & Strategy
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
    from titan_onnx_engine import TitanOnnxEngine, get_engine as get_onnx_engine
    ONNX_OK = True
except ImportError:
    ONNX_OK = False

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

# Tab 6: OSINT
try:
    from titan_web_intel import TitanWebIntel as _TitanWebIntel, get_web_intel, is_web_intel_available
    OSINT_WEB_OK = True
except ImportError:
    OSINT_WEB_OK = False

try:
    from intel_monitor import (
        IntelMonitor, INTEL_SOURCES, classify_post, AutoEngagement,
        SessionManager as IntelSessionManager, AlertPriority, SourceType,
    )
    OSINT_MONITOR_OK = True
except ImportError:
    OSINT_MONITOR_OK = False

try:
    from target_intelligence import (
        get_target_intel, list_targets, get_profile_requirements,
        ANTIFRAUD_PROFILES, TARGETS,
    )
    TARGET_INTEL_OK = True
except ImportError:
    TARGET_INTEL_OK = False

# Tab 7: TARGET DISCOVERY
try:
    from target_discovery import (
        TargetDiscovery, SITE_DATABASE, SiteDifficulty, SiteCategory, PSP,
    )
    DISCOVERY_OK = True
except ImportError:
    DISCOVERY_OK = False

try:
    from titan_target_intel_v2 import (
        TargetIntelV2, PSP_3DS_BEHAVIOR, MCC_3DS_INTELLIGENCE,
        GEO_3DS_ENFORCEMENT, TRANSACTION_TYPE_EXEMPTIONS, ANTIFRAUD_GAPS,
        CHECKOUT_FLOW_INTELLIGENCE,
    )
    INTEL_V2_FULL_OK = True
except ImportError:
    INTEL_V2_FULL_OK = False

try:
    from target_presets import get_preset_targets
    PRESETS_OK = True
except ImportError:
    PRESETS_OK = False


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


class OSINTWorker(QThread):
    finished = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, query, search_type="web", parent=None):
        super().__init__(parent)
        self.query = query
        self.search_type = search_type

    def run(self):
        parts = []
        try:
            if self.search_type == "web" and OSINT_WEB_OK:
                self.progress.emit("Searching web intelligence...")
                wi = get_web_intel()
                results = wi.search(self.query, num_results=8)
                parts.append(f"=== WEB INTEL: {self.query} ===\n")
                for r in results:
                    parts.append(f"[{r.get('position', '?')}] {r.get('title', '')}")
                    parts.append(f"    URL: {r.get('url', '')}")
                    parts.append(f"    {r.get('snippet', '')}\n")
            elif self.search_type == "merchant" and OSINT_WEB_OK:
                self.progress.emit("Running merchant recon...")
                wi = get_web_intel()
                report = wi.recon_merchant(self.query)
                parts.append(f"=== MERCHANT RECON: {self.query} ===\n")
                for r in (report.results if hasattr(report, 'results') else []):
                    parts.append(f"• {r.title}")
                    parts.append(f"  {r.url}")
                    parts.append(f"  {r.snippet}\n")
            elif self.search_type == "bin" and OSINT_WEB_OK:
                self.progress.emit("Searching BIN intelligence...")
                wi = get_web_intel()
                report = wi.search_bin_intel(self.query)
                parts.append(f"=== BIN INTEL: {self.query} ===\n")
                for r in (report.results if hasattr(report, 'results') else []):
                    parts.append(f"• {r.title} — {r.snippet}")
            elif self.search_type == "threat" and OSINT_WEB_OK:
                self.progress.emit("Monitoring threat intelligence...")
                wi = get_web_intel()
                report = wi.monitor_threats(self.query)
                parts.append(f"=== THREAT MONITOR: {self.query} ===\n")
                for r in (report.results if hasattr(report, 'results') else []):
                    parts.append(f"• {r.title}")
                    parts.append(f"  {r.snippet}\n")
            elif self.search_type == "antifraud" and OSINT_WEB_OK:
                self.progress.emit("Researching antifraud bypass intel...")
                wi = get_web_intel()
                report = wi.search_antifraud_bypass(self.query)
                parts.append(f"=== ANTIFRAUD BYPASS INTEL: {self.query} ===\n")
                for r in (report.results if hasattr(report, 'results') else []):
                    parts.append(f"• {r.title}")
                    parts.append(f"  {r.url}")
                    parts.append(f"  {r.snippet}\n")
            if not parts:
                parts.append("No OSINT results found. Check web intel module or API keys.")
        except Exception as e:
            parts.append(f"OSINT error: {e}")
        self.finished.emit("\n".join(parts))


class TargetDiscoveryWorker(QThread):
    finished = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, action, params=None, parent=None):
        super().__init__(parent)
        self.action = action
        self.params = params or {}

    def run(self):
        parts = []
        try:
            if self.action == "list_sites" and DISCOVERY_OK:
                self.progress.emit("Loading site database...")
                difficulty = self.params.get("difficulty", "easy")
                category = self.params.get("category", "all")
                td = TargetDiscovery()
                if category != "all":
                    sites = td.get_sites(difficulty=difficulty, category=category)
                else:
                    sites = td.get_sites(difficulty=difficulty)
                parts.append(f"=== SITE DATABASE: {difficulty.upper()} | {category} ===\n{len(sites)} sites found\n")
                for s in sites[:50]:
                    parts.append(f"{'✓' if hasattr(s,'status') and str(getattr(s,'status',''))=='SiteStatus.VERIFIED' else '○'} {s.name} ({s.domain})")
                    parts.append(f"  PSP: {s.psp.value if hasattr(s.psp,'value') else s.psp} | 3DS: {s.three_ds} | Fraud: {s.fraud_engine}")
                    parts.append(f"  Countries: {', '.join(s.country_focus[:4])} | Max: ${s.max_amount} | Cashout: {int(s.cashout_rate*100)}%")
                    if s.notes:
                        parts.append(f"  Note: {s.notes[:100]}")
                    parts.append("")
            elif self.action == "recommend" and DISCOVERY_OK:
                self.progress.emit("Finding best sites for card...")
                td = TargetDiscovery()
                country = self.params.get("country", "US")
                amount = float(self.params.get("amount", 200))
                sites = td.recommend_for_card(country=country, amount=amount)
                parts.append(f"=== RECOMMENDATIONS: {country} card, ${amount} ===\n")
                for s in sites[:20]:
                    parts.append(f"★ {s.name} ({s.domain})")
                    parts.append(f"  PSP: {s.psp.value if hasattr(s.psp,'value') else s.psp} | 3DS: {s.three_ds} | Rate: {int(getattr(s,'success_rate',0)*100)}%")
                    parts.append(f"  Cashout: {int(s.cashout_rate*100)}% | {s.products}\n")
            elif self.action == "probe" and DISCOVERY_OK:
                self.progress.emit("Probing target site...")
                td = TargetDiscovery()
                domain = self.params.get("domain", "")
                result = td.probe_site(domain)
                parts.append(f"=== SITE PROBE: {domain} ===\n")
                parts.append(json.dumps(result.__dict__ if hasattr(result, '__dict__') else result, indent=2, default=str))
            elif self.action == "psp_intel" and INTEL_V2_FULL_OK:
                self.progress.emit("Loading PSP intelligence...")
                psp = self.params.get("psp", "stripe")
                data = PSP_3DS_BEHAVIOR.get(psp.lower(), {})
                parts.append(f"=== PSP INTEL: {psp.upper()} ===\n")
                parts.append(json.dumps(data, indent=2))
            elif self.action == "geo_intel" and INTEL_V2_FULL_OK:
                self.progress.emit("Loading geo enforcement map...")
                parts.append("=== GEOGRAPHIC 3DS ENFORCEMENT ===\n")
                for zone, data in GEO_3DS_ENFORCEMENT.items():
                    parts.append(f"[{zone.upper()}]")
                    if isinstance(data, dict):
                        countries = data.get("countries", [])
                        rate = data.get("3ds_rate_range", "?")
                        parts.append(f"  Countries: {', '.join(countries[:10])}{'...' if len(countries)>10 else ''}")
                        parts.append(f"  3DS Rate: {rate}")
                    parts.append("")
            elif self.action == "mcc_intel" and INTEL_V2_FULL_OK:
                self.progress.emit("Loading MCC intelligence...")
                parts.append("=== MCC 3DS INTELLIGENCE ===\n")
                for mcc, data in MCC_3DS_INTELLIGENCE.items():
                    parts.append(f"MCC {mcc}: {data.get('name', '?')}")
                    parts.append(f"  3DS Rate: {int(data.get('3ds_rate', 0)*100)}% | {data.get('reason', '')[:80]}")
                    parts.append(f"  Examples: {', '.join(data.get('examples', [])[:4])}\n")
            elif self.action == "exemptions" and INTEL_V2_FULL_OK:
                self.progress.emit("Loading transaction exemptions...")
                parts.append("=== TRANSACTION TYPE EXEMPTIONS ===\n")
                for key, data in TRANSACTION_TYPE_EXEMPTIONS.items():
                    parts.append(f"[{data.get('name', key)}]")
                    parts.append(f"  3DS Required: {data.get('3ds_required', '?')}")
                    parts.append(f"  {data.get('description', '')[:120]}")
                    how = data.get('how_to_exploit', [])
                    if how:
                        parts.append(f"  HOW: {how[0][:100]}")
                    parts.append("")
            if not parts:
                parts.append("No discovery results. Ensure target_discovery / titan_target_intel_v2 modules are available.")
        except Exception as e:
            parts.append(f"Discovery error: {e}")
        self.finished.emit("\n".join(parts))


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
        self.setWindowTitle("TITAN X — Intelligence Center")
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
                        INTEL_V2_OK, INTEL_OK, WEB_INTEL_OK, TLS_OK, JA4_OK, COGNITIVE_OK,
                        INTEL_MON_OK, OSINT_WEB_OK, OSINT_MONITOR_OK, TARGET_INTEL_OK,
                        DISCOVERY_OK, INTEL_V2_FULL_OK])
        mod_lbl = QLabel(f"{available}/24 modules active")
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
        self._build_osint_tab()
        self._build_target_discovery_tab()

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

        # AI Model Health + Engine Toggle
        status_grp = QGroupBox("AI Engine Status & Model Selection")
        sf = QVBoxLayout(status_grp)

        # Engine status dots
        dot_row = QHBoxLayout()
        engines = [
            ("AI Intelligence", AI_OK),
            ("Ollama Bridge", OLLAMA_OK),
            ("ONNX Engine", ONNX_OK),
            ("Realtime Copilot", COPILOT_OK),
            ("Vector Memory", VECTOR_OK),
        ]
        for name, ok in engines:
            dot = QLabel(f"{'●' if ok else '○'} {name}")
            dot.setStyleSheet(f"color: {GREEN if ok else RED}; font-size: 11px;")
            dot_row.addWidget(dot)
        dot_row.addStretch()
        sf.addLayout(dot_row)

        # Model selector + ONNX toggle
        model_row = QHBoxLayout()
        model_row.addWidget(QLabel("Engine:"))
        self.ai_engine_selector = QComboBox()
        self.ai_engine_selector.addItems(["Auto (Ollama + ONNX)", "Ollama Only", "ONNX Only"])
        self.ai_engine_selector.setMaximumWidth(220)
        model_row.addWidget(self.ai_engine_selector)

        model_row.addWidget(QLabel("Fast Model:"))
        self.fast_model = QLabel("qwen2.5:3b" if OLLAMA_OK else "N/A")
        self.fast_model.setStyleSheet(f"color: {GREEN if OLLAMA_OK else RED}; font-weight: bold;")
        model_row.addWidget(self.fast_model)

        model_row.addWidget(QLabel("Analyst:"))
        self.analyst_model = QLabel("qwen2.5:7b" if OLLAMA_OK else "N/A")
        self.analyst_model.setStyleSheet(f"color: {GREEN if OLLAMA_OK else RED}; font-weight: bold;")
        model_row.addWidget(self.analyst_model)

        model_row.addWidget(QLabel("ONNX:"))
        self.onnx_model = QLabel("phi-4-mini" if ONNX_OK else "N/A")
        self.onnx_model.setStyleSheet(f"color: {GREEN if ONNX_OK else RED}; font-weight: bold;")
        model_row.addWidget(self.onnx_model)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setStyleSheet(f"background: {CARD2}; color: {TXT}; padding: 4px 10px; border-radius: 4px; font-size: 10px;")
        refresh_btn.clicked.connect(self._refresh_ai_health)
        model_row.addWidget(refresh_btn)

        model_row.addStretch()
        sf.addLayout(model_row)
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
            ("Pre-Op Checklist", lambda: self._generate_preop_checklist()),
            ("Plan Operation", lambda: self._quick_ask("Plan a full operation for the current target")),
            ("Analyze BIN", lambda: self._quick_ask("Analyze BIN intelligence for the card I'm using")),
            ("3DS Advice", lambda: self._quick_ask("What 3DS strategy should I use for this target?")),
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

        # Non-VBV BIN Finder
        nvbv_row = QHBoxLayout()
        nvbv_btn = QPushButton("Find Non-VBV BINs")
        nvbv_btn.setStyleSheet(f"background: {GREEN}; color: black; padding: 8px 16px; border-radius: 6px; font-weight: bold;")
        nvbv_btn.clicked.connect(self._find_non_vbv)
        nvbv_row.addWidget(nvbv_btn)
        self.nvbv_country = QComboBox()
        self.nvbv_country.addItems(["US", "UK", "CA", "AU", "DE", "FR", "NL", "SE", "JP", "ALL"])
        self.nvbv_country.setFixedWidth(80)
        nvbv_row.addWidget(self.nvbv_country)
        nvbv_row.addStretch()
        bf.addRow("", nvbv_row)

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

    def _refresh_ai_health(self):
        """Check which AI models are loaded and available."""
        # Ollama models
        if OLLAMA_OK:
            try:
                from ollama_bridge import LLMLoadBalancer
                bridge = LLMLoadBalancer()
                if bridge.is_available():
                    self.fast_model.setText("qwen2.5:3b ✓")
                    self.fast_model.setStyleSheet(f"color: {GREEN}; font-weight: bold;")
                    self.analyst_model.setText("qwen2.5:7b ✓")
                    self.analyst_model.setStyleSheet(f"color: {GREEN}; font-weight: bold;")
                else:
                    self.fast_model.setText("offline")
                    self.fast_model.setStyleSheet(f"color: {RED}; font-weight: bold;")
                    self.analyst_model.setText("offline")
                    self.analyst_model.setStyleSheet(f"color: {RED}; font-weight: bold;")
            except Exception:
                self.fast_model.setText("error")
                self.fast_model.setStyleSheet(f"color: {RED};")
        # ONNX
        if ONNX_OK:
            try:
                from titan_onnx_engine import get_engine
                engine = get_engine()
                if engine and engine.is_available():
                    self.onnx_model.setText("phi-4-mini ✓")
                    self.onnx_model.setStyleSheet(f"color: {GREEN}; font-weight: bold;")
                else:
                    self.onnx_model.setText("not loaded")
                    self.onnx_model.setStyleSheet(f"color: {YELLOW}; font-weight: bold;")
            except Exception:
                self.onnx_model.setText("error")
                self.onnx_model.setStyleSheet(f"color: {RED};")

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

    def _generate_preop_checklist(self):
        session = get_session() if _SESSION_OK else {}
        target = session.get("target", "unknown")
        bin6 = session.get("last_bin", "")
        profile_path = session.get("last_profile_path", "")
        quality = session.get("last_forge_quality", 0)
        lines = [
            "╔══════════════════════════════════════════════════════════╗",
            "║            PRE-OPERATION CHECKLIST                      ║",
            "╚══════════════════════════════════════════════════════════╝",
            "",
            f"Target: {target}",
            f"BIN: {bin6 or 'NOT SET — validate a card first'}",
            f"Profile: {profile_path or 'NOT SET — forge a profile first'}",
            f"Quality: {quality}/100" if quality else "Quality: NOT SCORED",
            "",
            "═══ ENVIRONMENT ═══",
            "[ ] VPN connected to billing region",
            "[ ] IP reputation checked (not datacenter/VPN flagged)",
            "[ ] Timezone matches billing state",
            "[ ] DNS leak test passed",
            "[ ] Hardware shield active (TITAN_HW_SPOOF=ACTIVE)",
            "",
            "═══ PROFILE ═══",
            f"[ ] Profile forged with {'✅ ' + str(quality) + '/100' if quality >= 80 else '⚠️ LOW QUALITY — re-forge'}",
            "[ ] Autofill data pre-populated (name, address, card)",
            "[ ] Stripe __stripe_mid cookie present (pre-aged 30+ days)",
            "[ ] Cache size ≥ 100MB",
            "[ ] History entries ≥ 100",
            "",
            "═══ CARD ═══",
            f"[ ] BIN validated: {bin6 or 'PENDING'}",
            "[ ] Luhn check passed",
            "[ ] AVS pre-check (ZIP matches state)",
            "[ ] Card not in cooling period",
            "[ ] Issuer velocity limit not reached",
            "",
            "═══ EXECUTION TIMING ═══",
            "[ ] Time: weekday 10am-8pm local (billing timezone)",
            "[ ] Session warm-up: 2-3 mins browsing before target",
            "[ ] Page dwell: 15-30s per page (not instant)",
            "[ ] Checkout typing: ~85 WPM (not instant)",
            "[ ] 3DS delay: 10-15s (simulate phone unlock)",
            "",
            "═══ POST-OP ═══",
            "[ ] Check email tab for receipt (45s wait)",
            "[ ] Do NOT close browser immediately",
            "[ ] Log result in Operations Center",
            "[ ] Cool card BIN for minimum 2 hours",
        ]
        self.copilot_output.setPlainText("\n".join(lines))

    def _quick_ask(self, query):
        self.copilot_input.setText(query)
        self._ask_copilot()

    def _on_copilot_response(self, response):
        self.copilot_send.setEnabled(True)
        self.copilot_history.append(f"\n{response}\n{'─' * 60}")

    def _find_non_vbv(self):
        country = self.nvbv_country.currentText()
        lines = ["═══ NON-VBV / LOW-3DS BIN INTELLIGENCE ═══", ""]
        if THREEDS_OK:
            try:
                if country == "ALL":
                    bins = get_all_non_vbv_bins() if hasattr(get_all_non_vbv_bins, '__call__') else []
                else:
                    easy = get_easy_countries() if hasattr(get_easy_countries, '__call__') else {}
                    bins = get_all_non_vbv_bins() if hasattr(get_all_non_vbv_bins, '__call__') else []
                    if isinstance(bins, dict):
                        bins = bins.get(country, [])
                    elif isinstance(bins, list):
                        bins = [b for b in bins if isinstance(b, dict) and b.get("country", "") == country]
                if bins:
                    lines.append(f"Found {len(bins) if isinstance(bins, list) else 'N/A'} non-VBV BINs for {country}:")
                    lines.append(json.dumps(bins, indent=2, default=str)[:3000])
                else:
                    lines.append(f"No non-VBV BINs found for {country} in database")
            except Exception as e:
                lines.append(f"Error: {e}")
        else:
            lines.append("three_ds_strategy module not loaded")

        lines.append("\n═══ EASY COUNTRIES (Low 3DS Enforcement) ═══")
        if THREEDS_OK:
            try:
                easy = get_easy_countries() if hasattr(get_easy_countries, '__call__') else {}
                if easy:
                    lines.append(json.dumps(easy, indent=2, default=str)[:1500])
                else:
                    lines.append("No easy country data available")
            except Exception as e:
                lines.append(f"Error: {e}")

        if INTEL_V2_FULL_OK:
            try:
                lines.append("\n═══ PSP 3DS BEHAVIOR ═══")
                lines.append(json.dumps(dict(list(PSP_3DS_BEHAVIOR.items())[:5]), indent=2, default=str)[:1000])
            except Exception:
                pass

        self.tds_output.setPlainText("\n".join(lines))

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
    # TAB 6: OSINT
    # ═══════════════════════════════════════════════════════════════════════

    def _build_osint_tab(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(tab)
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        status_grp = QGroupBox("OSINT Module Status")
        sf = QHBoxLayout(status_grp)
        for name, ok in [("Web Intel", OSINT_WEB_OK), ("Intel Monitor", OSINT_MONITOR_OK),
                          ("Target Intel DB", TARGET_INTEL_OK), ("Discovery Engine", DISCOVERY_OK)]:
            dot = QLabel(f"{'●' if ok else '○'} {name}")
            dot.setStyleSheet(f"color: {GREEN if ok else RED}; font-size: 11px;")
            sf.addWidget(dot)
        sf.addStretch()
        if OSINT_WEB_OK:
            try:
                wi = get_web_intel()
                stats = wi.get_stats()
                pl = QLabel(f"Providers: {', '.join(stats.get('providers', ['none'])[:3])}")
                pl.setStyleSheet(f"color: {CYAN}; font-size: 10px;")
                sf.addWidget(pl)
            except Exception:
                pass
        layout.addWidget(status_grp)

        search_grp = QGroupBox("Web Intelligence Search")
        sg = QVBoxLayout(search_grp)
        sr = QHBoxLayout()
        self.osint_query = QLineEdit()
        self.osint_query.setPlaceholderText("Query, domain, BIN number, or antifraud vendor name...")
        self.osint_query.returnPressed.connect(self._run_osint_web)
        sr.addWidget(self.osint_query)
        self.osint_type = QComboBox()
        self.osint_type.addItems(["web", "merchant", "bin", "threat", "antifraud"])
        self.osint_type.setFixedWidth(120)
        sr.addWidget(self.osint_type)
        ob = QPushButton("SEARCH OSINT")
        ob.setStyleSheet(f"background: {ACCENT}; color: white; padding: 8px 16px; border-radius: 6px; font-weight: bold;")
        ob.clicked.connect(self._run_osint_web)
        sr.addWidget(ob)
        sg.addLayout(sr)

        qr = QHBoxLayout()
        for label, stype in [("Merchant Recon","merchant"),("BIN Intel","bin"),("Threat Monitor","threat"),("AF Bypass","antifraud"),("Security News","news")]:
            btn = QPushButton(label)
            btn.setStyleSheet(f"background: {CARD2}; color: {TXT}; padding: 5px 10px; border-radius: 4px; font-size: 11px;")
            btn.clicked.connect(lambda c, st=stype: self._osint_quick(st))
            qr.addWidget(btn)
        qr.addStretch()
        sg.addLayout(qr)
        self.osint_status = QLabel("Ready")
        self.osint_status.setStyleSheet(f"color: {TXT2}; font-size: 10px;")
        sg.addWidget(self.osint_status)
        self.osint_output = QPlainTextEdit()
        self.osint_output.setReadOnly(True)
        self.osint_output.setMinimumHeight(250)
        self.osint_output.setStyleSheet(f"font-family: 'JetBrains Mono'; font-size: 11px; background: #0f172a; color: {TXT};")
        self.osint_output.setPlainText("OSINT Engine ready.\n\nTypes: web | merchant | bin | threat | antifraud\nPowered by: SearXNG → SerpAPI → Serper → DuckDuckGo")
        sg.addWidget(self.osint_output)
        layout.addWidget(search_grp)

        monitor_grp = QGroupBox("Intelligence Monitor — Forums / Channels / RSS")
        mg = QVBoxLayout(monitor_grp)
        mt = QHBoxLayout()
        self.monitor_source = QComboBox()
        if OSINT_MONITOR_OK:
            for src in INTEL_SOURCES:
                icon = {"forum": "🔴", "cc_shop": "💳", "telegram": "📱", "rss": "📰"}.get(src.source_type.value, "○")
                self.monitor_source.addItem(f"{icon} {src.name} ({src.access.value})", src.source_id)
        else:
            self.monitor_source.addItem("Intel Monitor not available")
        mt.addWidget(QLabel("Source:"))
        mt.addWidget(self.monitor_source)
        for lbl, fn in [("Source Info", self._show_source_info), ("List All Sources", self._list_all_sources)]:
            b = QPushButton(lbl)
            b.setStyleSheet(f"background: {CARD2}; color: {TXT}; padding: 6px 12px; border-radius: 4px;")
            b.clicked.connect(fn)
            mt.addWidget(b)
        mt.addStretch()
        mg.addLayout(mt)
        self.monitor_output = QPlainTextEdit()
        self.monitor_output.setReadOnly(True)
        self.monitor_output.setMaximumHeight(180)
        self.monitor_output.setStyleSheet(f"font-family: 'JetBrains Mono'; font-size: 11px; background: #0f172a; color: {TXT};")
        self.monitor_output.setPlainText("Select a source and click 'Source Info' or 'List All Sources'.")
        mg.addWidget(self.monitor_output)
        layout.addWidget(monitor_grp)

        af_grp = QGroupBox("Antifraud Intelligence Database")
        af = QVBoxLayout(af_grp)
        at = QHBoxLayout()
        self.af_vendor = QComboBox()
        self.af_vendor.addItems(["forter","riskified","seon","stripe_radar","kount","signifyd",
                                  "cybersource","maxmind","biocatch","threatmetrix","datadome",
                                  "perimeter_x","feedzai","featurespace","accertify","chainalysis"])
        at.addWidget(QLabel("Vendor:"))
        at.addWidget(self.af_vendor)
        gi = QPushButton("Get Intel")
        gi.setStyleSheet(f"background: {CYAN}; color: black; padding: 6px 14px; border-radius: 4px; font-weight: bold;")
        gi.clicked.connect(self._get_antifraud_intel)
        at.addWidget(gi)
        lt = QPushButton("List Targets DB")
        lt.setStyleSheet(f"background: {CARD2}; color: {TXT}; padding: 6px 12px; border-radius: 4px;")
        lt.clicked.connect(self._list_targets_db)
        at.addWidget(lt)
        at.addStretch()
        af.addLayout(at)
        self.af_output = QPlainTextEdit()
        self.af_output.setReadOnly(True)
        self.af_output.setMaximumHeight(180)
        self.af_output.setStyleSheet(f"font-family: 'JetBrains Mono'; font-size: 11px; background: #0f172a; color: {TXT};")
        self.af_output.setPlainText("Select antifraud vendor → Get Intel.\nContains detection methods, key signals, and evasion guidance for 17 fraud engines.")
        af.addWidget(self.af_output)
        layout.addWidget(af_grp)
        layout.addStretch()
        self.tabs.addTab(scroll, "OSINT")

    def _run_osint_web(self):
        query = self.osint_query.text().strip()
        if not query:
            return
        st = self.osint_type.currentText()
        self.osint_status.setText(f"Searching [{st}]...")
        self.osint_output.setPlainText("Searching...")
        self._osint_worker = OSINTWorker(query, st)
        self._osint_worker.progress.connect(lambda msg: self.osint_status.setText(msg))
        self._osint_worker.finished.connect(self._on_osint_done)
        self._osint_worker.start()

    def _osint_quick(self, st):
        query = self.osint_query.text().strip()
        if not query:
            if st == "news":
                query = "payment fraud antifraud 2026"
                st = "threat"
            else:
                self.osint_status.setText("Enter a query first")
                return
        self.osint_type.setCurrentText(st if st in ["web","merchant","bin","threat","antifraud"] else "web")
        self.osint_output.setPlainText("Searching...")
        self._osint_worker = OSINTWorker(query, st)
        self._osint_worker.progress.connect(lambda msg: self.osint_status.setText(msg))
        self._osint_worker.finished.connect(self._on_osint_done)
        self._osint_worker.start()

    def _on_osint_done(self, result):
        self.osint_status.setText("Done")
        self.osint_output.setPlainText(result)

    def _show_source_info(self):
        if not OSINT_MONITOR_OK:
            self.monitor_output.setPlainText("Intel Monitor not available")
            return
        source_id = self.monitor_source.currentData()
        src = next((s for s in INTEL_SOURCES if s.source_id == source_id), None)
        if not src:
            self.monitor_output.setPlainText("Source not found")
            return
        lines = [f"=== {src.name} ===",
                 f"Type: {src.source_type.value.upper()} | Access: {src.access.value.upper()}",
                 f"URL: {src.url}",
                 f"Rating: {'★'*int(src.rating)}{'☆'*(5-int(src.rating))} ({src.rating})",
                 f"Login Required: {'Yes' if src.login_required else 'No'}",
                 f"Post Visibility: {src.post_visibility.value}",
                 f"Auto-Engage: {'Yes' if src.auto_engage else 'No'}",
                 f"", f"Description: {src.description}",
                 f"", f"Sections: {', '.join(src.sections[:6])}",
                 f"Specialties: {', '.join(src.specialties)}",
                 f"Country Focus: {', '.join(src.country_focus)}",
                 f"Refresh: every {src.refresh_minutes} min",
                 f"Notes: {src.notes}"]
        self.monitor_output.setPlainText("\n".join(lines))

    def _list_all_sources(self):
        if not OSINT_MONITOR_OK:
            self.monitor_output.setPlainText("Intel Monitor not available")
            return
        lines = [f"=== ALL INTEL SOURCES ({len(INTEL_SOURCES)}) ===\n"]
        type_icons = {"forum":"🔴 FORUM","cc_shop":"💳 SHOP","telegram":"📱 TELEGRAM","rss":"📰 RSS"}
        for src in INTEL_SOURCES:
            icon = type_icons.get(src.source_type.value, "○")
            login_flag = "[LOGIN]" if src.login_required else "[PUBLIC]"
            tor_flag = " [TOR]" if src.access.value == "tor" else ""
            lines.append(f"{icon} {src.name} {login_flag}{tor_flag}")
            lines.append(f"  {'★'*int(src.rating)} | {src.url}")
            lines.append(f"  {src.description[:80]}")
            lines.append("")
        self.monitor_output.setPlainText("\n".join(lines))

    def _get_antifraud_intel(self):
        vendor = self.af_vendor.currentText()
        lines = [f"=== ANTIFRAUD INTEL: {vendor.upper()} ===\n"]
        found = False
        if TARGET_INTEL_OK:
            try:
                profile = ANTIFRAUD_PROFILES.get(vendor.lower())
                if profile:
                    found = True
                    lines += [f"Vendor: {profile.name} ({profile.vendor})",
                               f"Algorithm: {profile.algorithm_class}",
                               f"Detection: {profile.detection_method}",
                               f"Cross-Merchant: {'YES' if profile.cross_merchant_sharing else 'no'}",
                               f"Behavioral Biometrics: {'YES' if profile.behavioral_biometrics else 'no'}",
                               f"Invisible Challenges: {'YES ⚠' if profile.invisible_challenges else 'no'}",
                               f"Session Handover Detect: {'YES ⚠' if profile.session_handover_detection else 'no'}",
                               f"", "Key Signals:"]
                    for sig in profile.key_signals:
                        lines.append(f"  • {sig}")
                    lines.append("\nEvasion Guidance:")
                    for eg in profile.evasion_guidance:
                        lines.append(f"  ✓ {eg}")
            except Exception as e:
                lines.append(f"DB error: {e}")
        if not found:
            lines.append(f"Not in local DB. Use OSINT search for live intel.")
        self.af_output.setPlainText("\n".join(lines))

    def _list_targets_db(self):
        if not TARGET_INTEL_OK:
            self.af_output.setPlainText("Target Intelligence DB not available")
            return
        try:
            targets = list_targets()
            icons = {"very_low":"🟢","low":"🟡","medium":"🟠","high":"🔴"}
            lines = [f"=== TARGET DATABASE ({len(targets)} targets) ===\n"]
            for t in targets:
                icon = icons.get(t.get("friction",""), "○")
                lines.append(f"{icon} {t['name']} ({t['domain']})")
                lines.append(f"   Fraud: {t['fraud_engine']} | 3DS: {int(t['3ds_rate']*100)}% | Friction: {t['friction']}")
            self.af_output.setPlainText("\n".join(lines))
        except Exception as e:
            self.af_output.setPlainText(f"Error: {e}")

    # ═══════════════════════════════════════════════════════════════════════
    # TAB 7: TARGET DISCOVERY
    # ═══════════════════════════════════════════════════════════════════════

    def _build_target_discovery_tab(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(tab)
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        status_grp = QGroupBox("Target Discovery Module Status")
        sf = QHBoxLayout(status_grp)
        for name, ok in [("Site DB (1000+)", DISCOVERY_OK), ("PSP Intel V2", INTEL_V2_FULL_OK),
                          ("MCC Intel", INTEL_V2_FULL_OK), ("Geo 3DS Map", INTEL_V2_FULL_OK), ("TX Exemptions", INTEL_V2_FULL_OK)]:
            dot = QLabel(f"{'●' if ok else '○'} {name}")
            dot.setStyleSheet(f"color: {GREEN if ok else RED}; font-size: 11px;")
            sf.addWidget(dot)
        if DISCOVERY_OK:
            cl = QLabel(f"  |  {len(SITE_DATABASE)} sites loaded")
            cl.setStyleSheet(f"color: {CYAN}; font-size: 11px;")
            sf.addWidget(cl)
        sf.addStretch()
        layout.addWidget(status_grp)

        site_grp = QGroupBox("Site Database Browser")
        sg = QVBoxLayout(site_grp)
        fr = QHBoxLayout()
        fr.addWidget(QLabel("Difficulty:"))
        self.site_difficulty = QComboBox()
        self.site_difficulty.addItems(["easy","moderate","hard","all"])
        fr.addWidget(self.site_difficulty)
        fr.addWidget(QLabel("Category:"))
        self.site_category = QComboBox()
        self.site_category.addItems(["all","gaming","gift_cards","crypto","shopify","subscriptions",
                                      "digital","electronics","fashion","health","sports","travel","food_delivery"])
        fr.addWidget(self.site_category)
        fr.addWidget(QLabel("Country:"))
        self.card_country = QLineEdit()
        self.card_country.setPlaceholderText("US")
        self.card_country.setFixedWidth(55)
        fr.addWidget(self.card_country)
        fr.addWidget(QLabel("Amount $:"))
        self.site_amount = QLineEdit()
        self.site_amount.setText("200")
        self.site_amount.setFixedWidth(75)
        fr.addWidget(self.site_amount)
        for lbl, fn, col in [("BROWSE", self._list_discovery_sites, ACCENT),
                               ("RECOMMEND", self._recommend_sites, GREEN),
                               ("PROBE DOMAIN", self._probe_domain, ORANGE)]:
            b = QPushButton(lbl)
            b.setStyleSheet(f"background: {col}; color: {'black' if col==GREEN else 'white'}; padding: 7px 12px; border-radius: 6px; font-weight: bold;")
            b.clicked.connect(fn)
            fr.addWidget(b)
        fr.addStretch()
        sg.addLayout(fr)
        self.discovery_status = QLabel("Ready")
        self.discovery_status.setStyleSheet(f"color: {TXT2}; font-size: 10px;")
        sg.addWidget(self.discovery_status)
        self.discovery_output = QPlainTextEdit()
        self.discovery_output.setReadOnly(True)
        self.discovery_output.setMinimumHeight(240)
        self.discovery_output.setStyleSheet(f"font-family: 'JetBrains Mono'; font-size: 11px; background: #0f172a; color: {TXT};")
        self.discovery_output.setPlainText(f"Site Database ready. {len(SITE_DATABASE) if DISCOVERY_OK else 'N/A'} sites.\nBROWSE=filter list | RECOMMEND=best for card+amount | PROBE=auto-detect PSP/3DS/fraud")
        sg.addWidget(self.discovery_output)
        layout.addWidget(site_grp)

        vector_grp = QGroupBox("8-Vector Intelligence Engine")
        vg = QVBoxLayout(vector_grp)
        vtabs = QTabWidget()
        vtabs.setStyleSheet(f"QTabBar::tab{{padding:5px 12px;background:{CARD2};color:{TXT2};border:none;font-size:11px;font-weight:bold;}}QTabBar::tab:selected{{color:{CYAN};border-bottom:2px solid {CYAN};}}QTabWidget::pane{{border:1px solid #1e293b;}}")

        psp_w = QWidget(); psp_l = QVBoxLayout(psp_w)
        pr = QHBoxLayout()
        pr.addWidget(QLabel("PSP:"))
        self.psp_selector = QComboBox()
        self.psp_selector.addItems(["stripe","shopify_payments","adyen","authorize_net","braintree",
                                     "cybersource","square","worldpay","nmi","checkout_com","payflow_pro","eway","bambora","moneris"])
        pr.addWidget(self.psp_selector)
        pb = QPushButton("Get PSP Intel")
        pb.setStyleSheet(f"background: {CYAN}; color: black; padding: 6px 12px; border-radius: 4px; font-weight: bold;")
        pb.clicked.connect(self._get_psp_intel)
        pr.addWidget(pb)
        ca = QPushButton("Compare All")
        ca.setStyleSheet(f"background: {CARD2}; color: {TXT}; padding: 6px 10px; border-radius: 4px;")
        ca.clicked.connect(self._compare_all_psps)
        pr.addWidget(ca)
        pr.addStretch()
        psp_l.addLayout(pr)
        self.psp_output = QPlainTextEdit()
        self.psp_output.setReadOnly(True)
        self.psp_output.setStyleSheet(f"font-family: 'JetBrains Mono'; font-size: 11px; background: #0f172a; color: {TXT};")
        self.psp_output.setMinimumHeight(150)
        psp_l.addWidget(self.psp_output)
        vtabs.addTab(psp_w, "PSP Intel")

        for title, attr, btn_lbl, btn_fn, hint in [
            ("MCC Intel", "mcc_output", "Load MCC 3DS Intelligence", self._get_mcc_intel, "MCC categories with lowest 3DS enforcement rates — digital goods, restaurants, rideshare..."),
            ("Geo 3DS Map", "geo_output", "Load Geographic Enforcement Map", self._get_geo_intel, "Which card countries have NO 3DS mandate vs MANDATORY. One-Leg-Out exemption explained."),
            ("TX Exemptions", "exempt_output", "Load Transaction Exemptions", self._get_exemptions, "MIT, MOTO, Network Tokens, Card-on-File — transactions that skip 3DS entirely."),
            ("AF Gaps", "gaps_output", "Load Antifraud System Gaps", self._get_af_gaps, "Merchants with NO antifraud vs basic rules vs enterprise ML — and how to identify them."),
        ]:
            w = QWidget(); wl = QVBoxLayout(w)
            b = QPushButton(btn_lbl)
            b.setStyleSheet(f"background: {CYAN}; color: black; padding: 6px 14px; border-radius: 4px; font-weight: bold;")
            b.clicked.connect(btn_fn)
            wl.addWidget(b)
            out = QPlainTextEdit()
            out.setReadOnly(True)
            out.setStyleSheet(f"font-family: 'JetBrains Mono'; font-size: 11px; background: #0f172a; color: {TXT};")
            out.setMinimumHeight(150)
            out.setPlainText(hint)
            setattr(self, attr, out)
            wl.addWidget(out)
            vtabs.addTab(w, title)

        vg.addWidget(vtabs)
        layout.addWidget(vector_grp)
        layout.addStretch()
        self.tabs.addTab(scroll, "TARGET DISCOVERY")

    def _list_discovery_sites(self):
        diff = self.site_difficulty.currentText()
        cat = self.site_category.currentText()
        self.discovery_status.setText(f"Loading {diff}/{cat}...")
        self.discovery_output.setPlainText("Loading site database...")
        self._disc_worker = TargetDiscoveryWorker("list_sites", {"difficulty": diff, "category": cat})
        self._disc_worker.progress.connect(lambda m: self.discovery_status.setText(m))
        self._disc_worker.finished.connect(self._on_discovery_done)
        self._disc_worker.start()

    def _recommend_sites(self):
        country = self.card_country.text().strip() or "US"
        amount = self.site_amount.text().strip() or "200"
        self.discovery_status.setText(f"Recommending for {country} ${amount}...")
        self.discovery_output.setPlainText("Finding best sites...")
        self._disc_worker = TargetDiscoveryWorker("recommend", {"country": country, "amount": amount})
        self._disc_worker.progress.connect(lambda m: self.discovery_status.setText(m))
        self._disc_worker.finished.connect(self._on_discovery_done)
        self._disc_worker.start()

    def _probe_domain(self):
        from PyQt6.QtWidgets import QInputDialog
        prefill = self.osint_query.text().strip() or ""
        domain, ok = QInputDialog.getText(self, "Probe Domain", "Enter domain to probe (e.g. amazon.com):", text=prefill)
        if not ok or not domain:
            return
        self.discovery_status.setText(f"Probing {domain}...")
        self.discovery_output.setPlainText(f"Probing {domain}...")
        self._disc_worker = TargetDiscoveryWorker("probe", {"domain": domain})
        self._disc_worker.progress.connect(lambda m: self.discovery_status.setText(m))
        self._disc_worker.finished.connect(self._on_discovery_done)
        self._disc_worker.start()

    def _on_discovery_done(self, result):
        self.discovery_status.setText("Done")
        self.discovery_output.setPlainText(result)

    def _get_psp_intel(self):
        psp = self.psp_selector.currentText()
        self._disc_worker2 = TargetDiscoveryWorker("psp_intel", {"psp": psp})
        self._disc_worker2.finished.connect(lambda r: self.psp_output.setPlainText(r))
        self._disc_worker2.start()

    def _compare_all_psps(self):
        if not INTEL_V2_FULL_OK:
            self.psp_output.setPlainText("PSP Intel V2 module not available")
            return
        lines = ["=== ALL PSP 3DS BEHAVIOR COMPARISON ===\n"]
        rate_icons = {"OFF": "🟢 OFF", "RISK_BASED": "🟡 RISK", "ENFORCED_EU": "🔴 EU-ENFORCED",
                      "STRICT": "🔴 STRICT", "MERCHANT_CONFIG": "🟠 MERCHANT-CONFIG"}
        for psp, data in PSP_3DS_BEHAVIOR.items():
            default = data.get("default_3ds", "?")
            adoption = data.get("3ds_adoption_rate", 0)
            icon = rate_icons.get(default, f"○ {default}")
            lines.append(f"{icon:30s} {psp.upper():20s} adoption: {int(adoption*100)}%")
            lines.append(f"  {data.get('notes','')[:90]}")
            lines.append("")
        self.psp_output.setPlainText("\n".join(lines))

    def _get_mcc_intel(self):
        self._disc_worker3 = TargetDiscoveryWorker("mcc_intel", {})
        self._disc_worker3.finished.connect(lambda r: self.mcc_output.setPlainText(r))
        self._disc_worker3.start()

    def _get_geo_intel(self):
        self._disc_worker4 = TargetDiscoveryWorker("geo_intel", {})
        self._disc_worker4.finished.connect(lambda r: self.geo_output.setPlainText(r))
        self._disc_worker4.start()

    def _get_exemptions(self):
        self._disc_worker5 = TargetDiscoveryWorker("exemptions", {})
        self._disc_worker5.finished.connect(lambda r: self.exempt_output.setPlainText(r))
        self._disc_worker5.start()

    def _get_af_gaps(self):
        if not INTEL_V2_FULL_OK:
            self.gaps_output.setPlainText("Intel V2 module not available")
            return
        lines = ["=== ANTIFRAUD SYSTEM GAPS DATABASE ===\n"]
        for key, data in ANTIFRAUD_GAPS.items():
            lines.append(f"[{key.upper()}]")
            lines.append(f"Prevalence: {data.get('prevalence','?')}")
            lines.append(f"{data.get('description','')[:150]}")
            how = data.get("how_to_identify") or data.get("how_to_satisfy") or data.get("known_gaps", [])
            for item in how[:4]:
                lines.append(f"  • {item[:100]}")
            lines.append("")
        self.gaps_output.setPlainText("\n".join(lines))

    def _probe_domain_input(self):
        from PyQt6.QtWidgets import QInputDialog
        domain, ok = QInputDialog.getText(self, "Probe Domain", "Enter domain:")
        if ok and domain:
            self.discovery_status.setText(f"Probing {domain}...")
            self.discovery_output.setPlainText(f"Probing {domain}...")
            self._disc_worker = TargetDiscoveryWorker("probe", {"domain": domain})
            self._disc_worker.progress.connect(lambda m: self.discovery_status.setText(m))
            self._disc_worker.finished.connect(self._on_discovery_done)
            self._disc_worker.start()

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
