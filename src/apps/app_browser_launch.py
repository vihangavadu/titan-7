#!/usr/bin/env python3
"""
TITAN V8.2 BROWSER LAUNCH — Profile Launch, TX Monitor, Handover
================================================================
Focused app for launching forged profiles in Camoufox and monitoring
live transactions.

3 tabs:
  1. LAUNCH — Select profile, preflight checks, launch browser
  2. MONITOR — Live transaction monitoring, decline decoder
  3. HANDOVER — Manual handover protocol, post-checkout guide
"""

import sys
import os
import json
import subprocess
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / "core"))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QGroupBox, QFormLayout,
    QTabWidget, QComboBox, QProgressBar, QMessageBox, QScrollArea,
    QPlainTextEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QCheckBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

ACCENT = "#22c55e"
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

# Core imports
try:
    from integration_bridge import TitanIntegrationBridge, BridgeConfig, create_bridge
    BRIDGE_OK = True
except ImportError:
    BRIDGE_OK = False

try:
    from preflight_validator import PreFlightValidator, PreFlightReport
    PREFLIGHT_OK = True
except ImportError:
    PREFLIGHT_OK = False

try:
    from handover_protocol import ManualHandoverProtocol, HandoverPhase
    HANDOVER_OK = True
except ImportError:
    HANDOVER_OK = False

try:
    from transaction_monitor import TransactionMonitor, DeclineDecoder, decode_decline
    TX_MON_OK = True
except ImportError:
    TX_MON_OK = False

try:
    from ghost_motor_v6 import GhostMotorDiffusion
    GHOST_OK = True
except ImportError:
    GHOST_OK = False

try:
    from titan_ai_operations_guard import AIOperationsGuard, get_operations_guard
    AI_GUARD_OK = True
except ImportError:
    AI_GUARD_OK = False

try:
    from titan_realtime_copilot import RealtimeCopilot, get_realtime_copilot
    COPILOT_OK = True
except ImportError:
    COPILOT_OK = False

try:
    from titan_session import get_session, update_session
    SESSION_OK = True
except ImportError:
    SESSION_OK = False

try:
    from payment_success_metrics import PaymentSuccessMetricsDB
    METRICS_OK = True
except ImportError:
    METRICS_OK = False

# V8.3: AI detection vector sanitization
try:
    from ai_intelligence_engine import (
        score_environment_coherence, plan_session_rhythm,
        tune_form_fill_cadence, autopsy_decline, tune_behavior,
    )
    AI_V83_OK = True
except ImportError:
    AI_V83_OK = False


class PreflightWorker(QThread):
    finished = pyqtSignal(dict)

    def __init__(self, profile_path, target, parent=None):
        super().__init__(parent)
        self.profile_path = profile_path
        self.target = target
        self._stop_flag = __import__('threading').Event()

    def stop(self):
        """V8.3 FIX #2: Signal worker to stop cleanly."""
        self._stop_flag.set()

    def run(self):
        result = {"checks": [], "ready": False}
        checks = []

        # Profile exists
        exists = os.path.isdir(self.profile_path) if self.profile_path else False
        checks.append(("Profile exists", exists, self.profile_path or "No path"))

        # Preflight validator
        if PREFLIGHT_OK and exists:
            try:
                pf = PreFlightValidator()
                report = pf.run_all_checks(profile_path=self.profile_path, target=self.target)
                ready = getattr(report, 'is_ready', False) if report else False
                checks.append(("Preflight checks", ready, str(report)[:200] if report else "No report"))
            except Exception as e:
                checks.append(("Preflight checks", False, str(e)[:100]))
        else:
            checks.append(("Preflight checks", False, "Module not available" if not PREFLIGHT_OK else "No profile"))

        # Bridge available
        checks.append(("Integration Bridge", BRIDGE_OK, ""))
        checks.append(("Ghost Motor", GHOST_OK, ""))
        checks.append(("Handover Protocol", HANDOVER_OK, ""))
        checks.append(("TX Monitor", TX_MON_OK, ""))
        checks.append(("AI Operations Guard", AI_GUARD_OK, ""))

        # V8.3: AI environment coherence check
        if AI_V83_OK:
            try:
                env_config = {
                    "target": self.target,
                    "profile_path": self.profile_path,
                }
                env_result = score_environment_coherence(env_config)
                env_ok = env_result.coherent if env_result.ai_powered else True
                env_msg = f"Score: {env_result.score}/100" if env_result.ai_powered else "AI unavailable"
                if not env_ok and env_result.mismatches:
                    env_msg += f" | Issues: {', '.join(env_result.mismatches[:3])}"
                checks.append(("V8.3 Environment Coherence", env_ok, env_msg))
                result["v83_env_coherence"] = {
                    "score": env_result.score,
                    "coherent": env_result.coherent,
                    "mismatches": env_result.mismatches,
                    "fixes": env_result.fixes,
                    "ai_powered": env_result.ai_powered,
                }
            except Exception as e:
                checks.append(("V8.3 Environment Coherence", True, f"Check skipped: {str(e)[:60]}"))

            # V8.3: AI session rhythm planning
            try:
                rhythm = plan_session_rhythm(self.target)
                result["v83_session_rhythm"] = {
                    "total_session_s": rhythm.total_session_s,
                    "warmup_pages": len(rhythm.warmup_pages),
                    "browse_pages": len(rhythm.browse_pages),
                    "timing_notes": rhythm.timing_notes,
                    "ai_powered": rhythm.ai_powered,
                }
            except Exception:
                pass

        result["checks"] = checks
        result["ready"] = all(ok for _, ok, _ in checks[:3])
        self.finished.emit(result)


class TitanBrowserLaunch(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.apply_theme()
        self._load_session()

    def apply_theme(self):
        if THEME_OK:
            apply_titan_theme(self, ACCENT)
            self.tabs.setStyleSheet(make_tab_style(ACCENT))
        else:
            self.setStyleSheet(f"background: {BG}; color: {TEXT};")

    def _load_session(self):
        if SESSION_OK:
            try:
                s = get_session()
                path = s.get("last_profile_path", "")
                if path:
                    self.profile_path.setText(path)
                target = s.get("current_target", "")
                if target:
                    idx = self.target_combo.findText(target)
                    if idx >= 0:
                        self.target_combo.setCurrentIndex(idx)
                    else:
                        self.target_combo.setEditText(target)
            except Exception:
                pass

    def init_ui(self):
        self.setWindowTitle("TITAN V8.2 — Browser Launch")
        self.setMinimumSize(1000, 750)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)

        hdr = QLabel("BROWSER LAUNCH")
        hdr.setFont(QFont("Inter", 18, QFont.Weight.Bold))
        hdr.setStyleSheet(f"color: {ACCENT};")
        layout.addWidget(hdr)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self._build_launch_tab()
        self._build_monitor_tab()
        self._build_handover_tab()

    # ═══════════════════════════════════════════════════════════════════════
    # TAB 1: LAUNCH
    # ═══════════════════════════════════════════════════════════════════════

    def _build_launch_tab(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(tab)
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        # Profile selection
        grp = QGroupBox("Profile Selection")
        gf = QFormLayout(grp)
        self.profile_path = QLineEdit()
        self.profile_path.setPlaceholderText("/opt/titan/profiles/<profile-uuid>")
        gf.addRow("Profile:", self.profile_path)
        self.target_combo = QComboBox()
        self.target_combo.setEditable(True)
        self.target_combo.addItems(["amazon.com", "ebay.com", "walmart.com", "bestbuy.com", "shopify.com"])
        gf.addRow("Target:", self.target_combo)
        layout.addWidget(grp)

        # Launch options
        ogrp = QGroupBox("Launch Options")
        of = QVBoxLayout(ogrp)
        self.opt_ghost_motor = QCheckBox("Enable Ghost Motor (behavioral evasion)")
        self.opt_ghost_motor.setChecked(True)
        self.opt_ghost_motor.setEnabled(GHOST_OK)
        of.addWidget(self.opt_ghost_motor)

        self.opt_ai_guard = QCheckBox("Enable AI Operations Guard (real-time monitoring)")
        self.opt_ai_guard.setChecked(True)
        self.opt_ai_guard.setEnabled(AI_GUARD_OK)
        of.addWidget(self.opt_ai_guard)

        self.opt_copilot = QCheckBox("Enable Real-Time AI Copilot")
        self.opt_copilot.setChecked(True)
        self.opt_copilot.setEnabled(COPILOT_OK)
        of.addWidget(self.opt_copilot)

        self.opt_tx_monitor = QCheckBox("Enable Transaction Monitor")
        self.opt_tx_monitor.setChecked(True)
        self.opt_tx_monitor.setEnabled(TX_MON_OK)
        of.addWidget(self.opt_tx_monitor)
        layout.addWidget(ogrp)

        # Preflight
        btn_row = QHBoxLayout()
        self.preflight_btn = QPushButton("RUN PREFLIGHT")
        self.preflight_btn.setStyleSheet(f"background: {YELLOW}; color: black; padding: 12px 24px; border-radius: 8px; font-weight: bold; font-size: 13px;")
        self.preflight_btn.clicked.connect(self._run_preflight)
        btn_row.addWidget(self.preflight_btn)

        self.launch_btn = QPushButton("LAUNCH BROWSER")
        self.launch_btn.setStyleSheet(f"background: {GREEN}; color: black; padding: 12px 24px; border-radius: 8px; font-weight: bold; font-size: 13px;")
        self.launch_btn.clicked.connect(self._launch_browser)
        self.launch_btn.setEnabled(False)
        btn_row.addWidget(self.launch_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # Preflight results
        self.preflight_output = QPlainTextEdit()
        self.preflight_output.setReadOnly(True)
        self.preflight_output.setMinimumHeight(200)
        self.preflight_output.setPlaceholderText("Preflight check results will appear here...")
        layout.addWidget(self.preflight_output)

        # Module status
        mgrp = QGroupBox("Launch Subsystems")
        mf = QVBoxLayout(mgrp)
        modules = [
            ("Integration Bridge", BRIDGE_OK),
            ("Preflight Validator", PREFLIGHT_OK),
            ("Ghost Motor V6", GHOST_OK),
            ("Handover Protocol", HANDOVER_OK),
            ("TX Monitor", TX_MON_OK),
            ("AI Operations Guard", AI_GUARD_OK),
            ("Realtime Copilot", COPILOT_OK),
            ("Success Metrics", METRICS_OK),
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

        layout.addStretch()
        self.tabs.addTab(scroll, "LAUNCH")

    # ═══════════════════════════════════════════════════════════════════════
    # TAB 2: MONITOR
    # ═══════════════════════════════════════════════════════════════════════

    def _build_monitor_tab(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(tab)
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        # Live TX monitor
        grp = QGroupBox("Transaction Monitor")
        gf = QVBoxLayout(grp)

        self.tx_log = QPlainTextEdit()
        self.tx_log.setReadOnly(True)
        self.tx_log.setMinimumHeight(200)
        self.tx_log.setPlaceholderText("Transaction events will appear during live operations...")
        gf.addWidget(self.tx_log)
        layout.addWidget(grp)

        # Decline decoder
        dgrp = QGroupBox("Decline Decoder")
        df = QVBoxLayout(dgrp)
        row = QHBoxLayout()
        self.decline_input = QLineEdit()
        self.decline_input.setPlaceholderText("Enter decline code or message (e.g., 05, insufficient_funds, do_not_honor)")
        row.addWidget(self.decline_input)
        decode_btn = QPushButton("Decode")
        decode_btn.setStyleSheet(f"background: {ACCENT}; color: black; padding: 8px 16px; border-radius: 6px; font-weight: bold;")
        decode_btn.clicked.connect(self._decode_decline)
        row.addWidget(decode_btn)
        df.addLayout(row)

        self.decline_output = QPlainTextEdit()
        self.decline_output.setReadOnly(True)
        self.decline_output.setMinimumHeight(150)
        df.addWidget(self.decline_output)
        layout.addWidget(dgrp)

        # TX History table
        hgrp = QGroupBox("Transaction History")
        hf = QVBoxLayout(hgrp)
        self.tx_table = QTableWidget()
        self.tx_table.setColumnCount(5)
        self.tx_table.setHorizontalHeaderLabels(["Time", "Target", "Amount", "Status", "Code"])
        self.tx_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tx_table.setMinimumHeight(200)
        hf.addWidget(self.tx_table)
        layout.addWidget(hgrp)

        layout.addStretch()
        self.tabs.addTab(scroll, "MONITOR")

    # ═══════════════════════════════════════════════════════════════════════
    # TAB 3: HANDOVER
    # ═══════════════════════════════════════════════════════════════════════

    def _build_handover_tab(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(tab)
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        # Handover protocol guide
        grp = QGroupBox("Manual Handover Protocol")
        gf = QVBoxLayout(grp)

        self.handover_output = QPlainTextEdit()
        self.handover_output.setReadOnly(True)
        self.handover_output.setMinimumHeight(300)

        if HANDOVER_OK:
            try:
                from handover_protocol import get_post_checkout_guide, POST_CHECKOUT_GUIDES
                guides = []
                for target, guide in POST_CHECKOUT_GUIDES.items():
                    guides.append(f"=== {target} ===")
                    if isinstance(guide, dict):
                        for k, v in guide.items():
                            guides.append(f"  {k}: {v}")
                    else:
                        guides.append(f"  {guide}")
                    guides.append("")
                self.handover_output.setPlainText("\n".join(guides) if guides else "Handover protocol loaded — use during live operations")
            except Exception:
                self.handover_output.setPlainText("Handover protocol loaded — guides available during operations")
        else:
            self.handover_output.setPlainText("Handover protocol module not available")

        gf.addWidget(self.handover_output)

        # Quick actions
        btn_row = QHBoxLayout()
        self.handover_start_btn = QPushButton("Start Handover")
        self.handover_start_btn.setStyleSheet(f"background: {GREEN}; color: black; padding: 8px 16px; border-radius: 6px; font-weight: bold;")
        self.handover_start_btn.setEnabled(HANDOVER_OK)
        self.handover_start_btn.clicked.connect(self._start_handover)
        btn_row.addWidget(self.handover_start_btn)

        self.handover_abort_btn = QPushButton("Abort")
        self.handover_abort_btn.setStyleSheet(f"background: {RED}; color: white; padding: 8px 16px; border-radius: 6px; font-weight: bold;")
        self.handover_abort_btn.clicked.connect(self._abort_handover)
        btn_row.addWidget(self.handover_abort_btn)
        btn_row.addStretch()
        gf.addLayout(btn_row)

        layout.addWidget(grp)

        # Post-op analysis
        pgrp = QGroupBox("Post-Operation Analysis")
        pf = QVBoxLayout(pgrp)
        self.postop_output = QPlainTextEdit()
        self.postop_output.setReadOnly(True)
        self.postop_output.setMinimumHeight(150)
        self.postop_output.setPlaceholderText("Post-operation analysis will appear after browser session ends...")
        pf.addWidget(self.postop_output)

        analyze_btn = QPushButton("Run Post-Op Analysis")
        analyze_btn.setStyleSheet(f"background: {BG_CARD}; color: {TEXT}; padding: 8px 16px; border: 1px solid #334155; border-radius: 6px;")
        analyze_btn.clicked.connect(self._run_postop)
        pf.addWidget(analyze_btn)
        layout.addWidget(pgrp)

        layout.addStretch()
        self.tabs.addTab(scroll, "HANDOVER")

    # ═══════════════════════════════════════════════════════════════════════
    # ACTIONS
    # ═══════════════════════════════════════════════════════════════════════

    def _run_preflight(self):
        profile = self.profile_path.text().strip()
        target = self.target_combo.currentText()
        self.preflight_btn.setEnabled(False)
        self.preflight_btn.setText("Checking...")
        self.preflight_output.setPlainText("Running preflight checks...\n")

        self.pf_worker = PreflightWorker(profile, target)
        self.pf_worker.finished.connect(self._on_preflight_done)
        self.pf_worker.start()

    def _on_preflight_done(self, result):
        self.preflight_btn.setEnabled(True)
        self.preflight_btn.setText("RUN PREFLIGHT")

        lines = ["=== PREFLIGHT REPORT ===\n"]
        for name, ok, detail in result.get("checks", []):
            status = "PASS" if ok else "FAIL"
            line = f"  [{status}] {name}"
            if detail:
                line += f" — {detail[:100]}"
            lines.append(line)

        ready = result.get("ready", False)
        lines.append(f"\n{'GO FOR LAUNCH' if ready else 'NOT READY — fix failed checks'}")
        self.preflight_output.setPlainText("\n".join(lines))
        self.launch_btn.setEnabled(ready)

        if ready:
            self.launch_btn.setStyleSheet(f"background: {GREEN}; color: black; padding: 12px 24px; border-radius: 8px; font-weight: bold; font-size: 13px;")
        else:
            self.launch_btn.setStyleSheet(f"background: {RED}; color: white; padding: 12px 24px; border-radius: 8px; font-weight: bold; font-size: 13px;")

    def _launch_browser(self):
        profile = self.profile_path.text().strip()
        target = self.target_combo.currentText()

        if not profile:
            QMessageBox.warning(self, "No Profile", "Select a profile path first")
            return

        reply = QMessageBox.question(
            self, "Launch Browser",
            f"Launch Camoufox with:\n\nProfile: {profile}\nTarget: {target}\n\nGhost Motor: {'ON' if self.opt_ghost_motor.isChecked() else 'OFF'}\nAI Guard: {'ON' if self.opt_ai_guard.isChecked() else 'OFF'}\n\nProceed?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.preflight_output.appendPlainText("\nLaunching browser...")
            if SESSION_OK:
                try:
                    update_session(
                        current_target=target,
                        active_profile_path=profile,
                        browser_launched=datetime.now().isoformat(),
                    )
                except Exception:
                    pass

            if BRIDGE_OK:
                try:
                    bridge = create_bridge(profile_uuid=os.path.basename(profile))
                    bridge.initialize()
                    self.preflight_output.appendPlainText("Bridge initialized — launching browser...")
                except Exception as e:
                    self.preflight_output.appendPlainText(f"Bridge error: {e}")
            else:
                self.preflight_output.appendPlainText("Bridge not available — manual launch required")

    def _decode_decline(self):
        code = self.decline_input.text().strip()
        if not code:
            return

        lines = [f"=== Decline Decoder: {code} ===\n"]
        if TX_MON_OK:
            try:
                result = decode_decline(code)
                lines.append(json.dumps(result, indent=2, default=str) if isinstance(result, dict) else str(result))
            except Exception as e:
                lines.append(f"Decoder error: {e}")
        else:
            # Basic built-in decoder
            codes = {
                "05": "DO NOT HONOR — Bank refused. Try different card or lower amount.",
                "14": "INVALID CARD — Number doesn't match BIN. Check card data.",
                "51": "INSUFFICIENT FUNDS — Card has no balance.",
                "54": "EXPIRED CARD — Card past expiry date.",
                "57": "NOT PERMITTED — Transaction type not allowed on this card.",
                "61": "EXCEEDS WITHDRAWAL — Amount too high for card limits.",
                "65": "EXCEEDS FREQUENCY — Too many transactions in short time.",
                "91": "ISSUER UNAVAILABLE — Bank system down. Retry later.",
                "N7": "CVV2 MISMATCH — Wrong CVV entered.",
                "insufficient_funds": "Card balance too low for amount.",
                "do_not_honor": "Generic bank refusal — try smaller amount, different time, or different card.",
                "stolen_card": "Card flagged as stolen. Do NOT retry.",
                "lost_card": "Card flagged as lost. Do NOT retry.",
            }
            decoded = codes.get(code, codes.get(code.lower(), f"Unknown code: {code}"))
            lines.append(decoded)

        self.decline_output.setPlainText("\n".join(lines))

    def _start_handover(self):
        self.handover_output.appendPlainText(f"\n[{datetime.now().strftime('%H:%M:%S')}] Handover initiated...")
        if HANDOVER_OK:
            try:
                protocol = ManualHandoverProtocol()
                target = self.target_combo.currentText()
                self.handover_output.appendPlainText(f"Target: {target}")
                self.handover_output.appendPlainText("Phase: CHECKOUT → Follow on-screen guide")
            except Exception as e:
                self.handover_output.appendPlainText(f"Handover error: {e}")

    def _abort_handover(self):
        self.handover_output.appendPlainText(f"\n[{datetime.now().strftime('%H:%M:%S')}] HANDOVER ABORTED")

    def _run_postop(self):
        lines = [f"=== Post-Operation Analysis === {datetime.now().isoformat()}\n"]
        if AI_GUARD_OK:
            try:
                guard = get_operations_guard()
                from titan_ai_operations_guard import post_op_analysis
                analysis = post_op_analysis()
                lines.append(json.dumps(analysis, indent=2, default=str) if isinstance(analysis, dict) else str(analysis))
            except Exception as e:
                lines.append(f"AI Guard analysis: {e}")
        else:
            lines.append("AI Operations Guard not available — manual review required")

        if METRICS_OK:
            try:
                db = PaymentSuccessMetricsDB()
                stats = db.get_stats() if hasattr(db, 'get_stats') else {}
                lines.append(f"\nMetrics: {json.dumps(stats, indent=2, default=str)[:300]}")
            except Exception:
                pass

        self.postop_output.setPlainText("\n".join(lines))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = TitanBrowserLaunch()
    win.show()
    sys.exit(app.exec())
