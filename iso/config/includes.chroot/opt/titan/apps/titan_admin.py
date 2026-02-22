#!/usr/bin/env python3
"""
TITAN V8.1 ADMIN PANEL — System Administration & Diagnostics
=============================================================
Consolidates: titan_mission_control.py + titan_dev_hub.py + app_bug_reporter.py

3 tabs:
  1. SERVICES — Start/stop services, health monitoring, memory pressure
  2. TOOLS — Bug reporter, auto-patcher status, AI config
  3. SYSTEM — Module health, kill switch, VPN status, forensic monitor
"""

import sys
import os
import subprocess
import json
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / "core"))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QGroupBox, QFormLayout,
    QTabWidget, QFrame, QProgressBar, QComboBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QCheckBox, QSpinBox, QMessageBox,
    QScrollArea, QPlainTextEdit
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor, QPalette

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════
ACCENT = "#f59e0b"
BG_DARK = "#0a0e17"
BG_CARD = "#111827"
TEXT_PRIMARY = "#e2e8f0"
TEXT_SECONDARY = "#64748b"
GREEN = "#22c55e"
YELLOW = "#eab308"
RED = "#ef4444"

# ═══════════════════════════════════════════════════════════════════════════════
# CORE IMPORTS (graceful)
# ═══════════════════════════════════════════════════════════════════════════════
try:
    from titan_services import (
        TitanServiceManager, get_service_manager,
        start_all_services, stop_all_services, get_services_status,
        MemoryPressureManager,
    )
    SERVICES_AVAILABLE = True
except ImportError:
    SERVICES_AVAILABLE = False

try:
    from kill_switch import KillSwitch, KillSwitchConfig, arm_kill_switch, send_panic_signal
    KILL_SWITCH_AVAILABLE = True
except ImportError:
    KILL_SWITCH_AVAILABLE = False

try:
    from bug_patch_bridge import BugPatchBridge
    BUG_BRIDGE_AVAILABLE = True
except ImportError:
    BUG_BRIDGE_AVAILABLE = False

try:
    from titan_auto_patcher import TitanAutoPatcher
    PATCHER_AVAILABLE = True
except ImportError:
    PATCHER_AVAILABLE = False

try:
    from ollama_bridge import OllamaBridge
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

try:
    from ai_intelligence_engine import get_ai_status, is_ai_available
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False

try:
    from lucid_vpn import LucidVPN, VPNStatus
    VPN_AVAILABLE = True
except ImportError:
    VPN_AVAILABLE = False

try:
    from forensic_monitor import ForensicMonitor
    FORENSIC_AVAILABLE = True
except ImportError:
    FORENSIC_AVAILABLE = False

try:
    from immutable_os import verify_system_integrity, get_boot_status
    IMMUTABLE_AVAILABLE = True
except ImportError:
    IMMUTABLE_AVAILABLE = False


# ═══════════════════════════════════════════════════════════════════════════════
# WORKERS
# ═══════════════════════════════════════════════════════════════════════════════

class HealthCheckWorker(QThread):
    """Background worker for health checks."""
    finished = pyqtSignal(dict)

    def run(self):
        results = {}
        core_dir = Path(__file__).parent.parent / "core"

        # Count modules
        py_files = list(core_dir.glob("*.py"))
        results["core_count"] = len(py_files) - 1  # minus __init__

        # Check importability
        importable = 0
        failed = []
        for f in py_files:
            if f.name == "__init__.py":
                continue
            mod_name = f.stem
            try:
                __import__(mod_name)
                importable += 1
            except Exception as e:
                failed.append(f"{mod_name}: {str(e)[:60]}")

        results["importable"] = importable
        results["failed"] = failed

        # Memory
        try:
            import psutil
            mem = psutil.virtual_memory()
            results["ram_used_gb"] = round(mem.used / (1024**3), 1)
            results["ram_total_gb"] = round(mem.total / (1024**3), 1)
            results["ram_pct"] = mem.percent
        except ImportError:
            results["ram_pct"] = -1

        # Disk
        try:
            import shutil
            total, used, free = shutil.disk_usage("/")
            results["disk_free_gb"] = round(free / (1024**3), 1)
        except Exception:
            results["disk_free_gb"] = -1

        # Services
        if SERVICES_AVAILABLE:
            try:
                results["services"] = get_services_status()
            except Exception:
                results["services"] = {}
        else:
            results["services"] = {}

        # AI status
        if AI_AVAILABLE:
            try:
                results["ai_status"] = get_ai_status()
            except Exception:
                results["ai_status"] = {"available": False}
        else:
            results["ai_status"] = {"available": False}

        self.finished.emit(results)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN WINDOW
# ═══════════════════════════════════════════════════════════════════════════════

class TitanAdmin(QMainWindow):
    """
    TITAN V8.1 Admin Panel

    Consolidated system administration:
    - Tab 1: SERVICES — health monitoring, start/stop, memory pressure
    - Tab 2: TOOLS — bug reporter, auto-patcher, AI configuration
    - Tab 3: SYSTEM — module health, kill switch, VPN, forensics
    """

    def __init__(self):
        super().__init__()
        self.health_data = {}
        self.init_ui()
        self.apply_theme()
        QTimer.singleShot(300, self._run_health_check)

    def init_ui(self):
        self.setWindowTitle("TITAN V8.1 \u2014 Admin Panel")
        try:
            from titan_icon import set_titan_icon
            set_titan_icon(self, ACCENT)
        except Exception:
            pass
        self.setMinimumSize(1100, 800)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Header
        header = QLabel("TITAN V8.1 ADMIN")
        header.setFont(QFont("Inter", 20, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet(f"color: {ACCENT};")
        layout.addWidget(header)

        # Main tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabBar::tab {{
                padding: 10px 20px;
                min-width: 120px;
                background: {BG_CARD};
                color: {TEXT_SECONDARY};
                border: none;
                border-bottom: 2px solid transparent;
            }}
            QTabBar::tab:selected {{
                color: {ACCENT};
                border-bottom: 2px solid {ACCENT};
                font-weight: bold;
            }}
            QTabBar::tab:hover {{ color: {TEXT_PRIMARY}; }}
            QTabWidget::pane {{ border: none; }}
        """)
        layout.addWidget(self.tabs)

        self._build_services_tab()
        self._build_tools_tab()
        self._build_system_tab()

        # Status bar
        self.status_bar = QLabel("Ready")
        self.status_bar.setFont(QFont("JetBrains Mono", 9))
        self.status_bar.setStyleSheet(f"color: {TEXT_SECONDARY}; padding: 4px;")
        layout.addWidget(self.status_bar)

    # ═══════════════════════════════════════════════════════════════════════════
    # TAB 1: SERVICES
    # ═══════════════════════════════════════════════════════════════════════════

    def _build_services_tab(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(tab)
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        # Service controls
        ctrl_layout = QHBoxLayout()

        self.start_all_btn = QPushButton("Start All Services")
        self.start_all_btn.setStyleSheet(f"background: {GREEN}; color: black; padding: 8px 16px; border-radius: 6px; font-weight: bold;")
        self.start_all_btn.clicked.connect(self._start_services)
        ctrl_layout.addWidget(self.start_all_btn)

        self.stop_all_btn = QPushButton("Stop All Services")
        self.stop_all_btn.setStyleSheet(f"background: {RED}; color: white; padding: 8px 16px; border-radius: 6px; font-weight: bold;")
        self.stop_all_btn.clicked.connect(self._stop_services)
        ctrl_layout.addWidget(self.stop_all_btn)

        self.refresh_btn = QPushButton("Refresh Health")
        self.refresh_btn.setStyleSheet(f"background: {ACCENT}; color: black; padding: 8px 16px; border-radius: 6px; font-weight: bold;")
        self.refresh_btn.clicked.connect(self._run_health_check)
        ctrl_layout.addWidget(self.refresh_btn)

        ctrl_layout.addStretch()
        layout.addLayout(ctrl_layout)

        # Health overview
        health_group = QGroupBox("System Health")
        health_layout = QFormLayout(health_group)

        self.lbl_modules = QLabel("...")
        self.lbl_ram = QLabel("...")
        self.lbl_disk = QLabel("...")
        self.lbl_ai = QLabel("...")
        self.lbl_services_count = QLabel("...")

        health_layout.addRow("Core Modules:", self.lbl_modules)
        health_layout.addRow("RAM Usage:", self.lbl_ram)
        health_layout.addRow("Disk Free:", self.lbl_disk)
        health_layout.addRow("AI Engine:", self.lbl_ai)
        health_layout.addRow("Services:", self.lbl_services_count)

        layout.addWidget(health_group)

        # Service table
        svc_group = QGroupBox("Service Status")
        svc_layout = QVBoxLayout(svc_group)

        self.svc_table = QTableWidget()
        self.svc_table.setColumnCount(4)
        self.svc_table.setHorizontalHeaderLabels(["Service", "Status", "Uptime", "Actions"])
        self.svc_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.svc_table.setMinimumHeight(200)
        svc_layout.addWidget(self.svc_table)

        layout.addWidget(svc_group)

        # Memory pressure
        mem_group = QGroupBox("Memory Pressure Monitor")
        mem_layout = QVBoxLayout(mem_group)

        self.mem_bar = QProgressBar()
        self.mem_bar.setMinimum(0)
        self.mem_bar.setMaximum(100)
        self.mem_bar.setTextVisible(True)
        self.mem_bar.setFormat("%p% RAM")
        mem_layout.addWidget(self.mem_bar)

        self.mem_status = QLabel("Checking...")
        self.mem_status.setFont(QFont("JetBrains Mono", 10))
        mem_layout.addWidget(self.mem_status)

        layout.addWidget(mem_group)
        layout.addStretch()

        self.tabs.addTab(scroll, "SERVICES")

    # ═══════════════════════════════════════════════════════════════════════════
    # TAB 2: TOOLS
    # ═══════════════════════════════════════════════════════════════════════════

    def _build_tools_tab(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(tab)
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        # Bug Reporter
        bug_group = QGroupBox("Bug Reporter")
        bug_layout = QVBoxLayout(bug_group)

        bug_form = QFormLayout()
        self.bug_title = QLineEdit()
        self.bug_title.setPlaceholderText("Brief bug description")
        bug_form.addRow("Title:", self.bug_title)

        self.bug_severity = QComboBox()
        self.bug_severity.addItems(["P0 - Critical", "P1 - High", "P2 - Medium", "P3 - Low"])
        bug_form.addRow("Severity:", self.bug_severity)

        self.bug_module = QComboBox()
        self.bug_module.addItems([
            "genesis_core", "cerberus_core", "kyc_core", "integration_bridge",
            "ghost_motor_v6", "fingerprint_injector", "tls_parrot", "titan_api",
            "preflight_validator", "transaction_monitor", "target_discovery",
            "persona_enrichment_engine", "titan_realtime_copilot", "other"
        ])
        bug_form.addRow("Module:", self.bug_module)

        bug_layout.addLayout(bug_form)

        self.bug_desc = QPlainTextEdit()
        self.bug_desc.setPlaceholderText("Steps to reproduce, expected vs actual behavior...")
        self.bug_desc.setMaximumHeight(120)
        bug_layout.addWidget(self.bug_desc)

        bug_btn_layout = QHBoxLayout()
        self.submit_bug_btn = QPushButton("Submit Bug Report")
        self.submit_bug_btn.setStyleSheet(f"background: {ACCENT}; color: black; padding: 8px 16px; border-radius: 6px; font-weight: bold;")
        self.submit_bug_btn.clicked.connect(self._submit_bug)
        bug_btn_layout.addWidget(self.submit_bug_btn)

        self.auto_patch_btn = QPushButton("Auto-Patch (Windsurf)")
        self.auto_patch_btn.setStyleSheet(f"background: #6366f1; color: white; padding: 8px 16px; border-radius: 6px; font-weight: bold;")
        self.auto_patch_btn.clicked.connect(self._auto_patch)
        bug_btn_layout.addWidget(self.auto_patch_btn)
        bug_btn_layout.addStretch()

        bug_layout.addLayout(bug_btn_layout)
        layout.addWidget(bug_group)

        # AI Configuration
        ai_group = QGroupBox("AI Engine Configuration")
        ai_layout = QFormLayout(ai_group)

        self.ai_provider = QComboBox()
        self.ai_provider.addItems(["Ollama (Local)", "vLLM (Cloud)", "OpenAI API", "Anthropic API"])
        ai_layout.addRow("Provider:", self.ai_provider)

        self.ai_model = QComboBox()
        self.ai_model.addItems(["qwen2.5:7b", "llama3:8b", "mixtral:8x7b", "codellama:13b"])
        ai_layout.addRow("Model:", self.ai_model)

        self.ai_endpoint = QLineEdit()
        self.ai_endpoint.setPlaceholderText("http://127.0.0.1:11434")
        self.ai_endpoint.setText("http://127.0.0.1:11434")
        ai_layout.addRow("Endpoint:", self.ai_endpoint)

        ai_test_btn = QPushButton("Test Connection")
        ai_test_btn.setStyleSheet(f"background: {GREEN}; color: black; padding: 6px 12px; border-radius: 6px;")
        ai_test_btn.clicked.connect(self._test_ai)
        ai_layout.addRow("", ai_test_btn)

        self.ai_status_text = QLabel("Not tested")
        self.ai_status_text.setStyleSheet(f"color: {TEXT_SECONDARY};")
        ai_layout.addRow("Status:", self.ai_status_text)

        layout.addWidget(ai_group)

        # Auto-Patcher Status
        patch_group = QGroupBox("Auto-Patcher Status")
        patch_layout = QVBoxLayout(patch_group)
        self.patch_log = QTextEdit()
        self.patch_log.setReadOnly(True)
        self.patch_log.setMaximumHeight(150)
        self.patch_log.setPlaceholderText("No patches applied yet...")
        self.patch_log.setStyleSheet("font-family: 'JetBrains Mono', monospace; font-size: 11px;")
        patch_layout.addWidget(self.patch_log)
        layout.addWidget(patch_group)

        layout.addStretch()
        self.tabs.addTab(scroll, "TOOLS")

    # ═══════════════════════════════════════════════════════════════════════════
    # TAB 3: SYSTEM
    # ═══════════════════════════════════════════════════════════════════════════

    def _build_system_tab(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(tab)
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        # Module Health Table
        mod_group = QGroupBox("Core Module Health")
        mod_layout = QVBoxLayout(mod_group)

        mod_ctrl = QHBoxLayout()
        self.scan_modules_btn = QPushButton("Scan All Modules")
        self.scan_modules_btn.setStyleSheet(f"background: {ACCENT}; color: black; padding: 6px 12px; border-radius: 6px; font-weight: bold;")
        self.scan_modules_btn.clicked.connect(self._scan_modules)
        mod_ctrl.addWidget(self.scan_modules_btn)
        mod_ctrl.addStretch()
        mod_layout.addLayout(mod_ctrl)

        self.mod_table = QTableWidget()
        self.mod_table.setColumnCount(3)
        self.mod_table.setHorizontalHeaderLabels(["Module", "Status", "Classes"])
        self.mod_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.mod_table.setMinimumHeight(250)
        mod_layout.addWidget(self.mod_table)

        layout.addWidget(mod_group)

        # Kill Switch
        ks_group = QGroupBox("Kill Switch (Emergency)")
        ks_layout = QHBoxLayout(ks_group)

        self.ks_arm_btn = QPushButton("ARM Kill Switch")
        self.ks_arm_btn.setStyleSheet(f"background: {YELLOW}; color: black; padding: 8px 16px; border-radius: 6px; font-weight: bold;")
        self.ks_arm_btn.clicked.connect(self._arm_kill_switch)
        ks_layout.addWidget(self.ks_arm_btn)

        self.ks_panic_btn = QPushButton("PANIC")
        self.ks_panic_btn.setStyleSheet(f"background: {RED}; color: white; padding: 8px 24px; border-radius: 6px; font-weight: bold; font-size: 14px;")
        self.ks_panic_btn.clicked.connect(self._panic)
        self.ks_panic_btn.setEnabled(False)
        ks_layout.addWidget(self.ks_panic_btn)

        self.ks_status = QLabel("DISARMED")
        self.ks_status.setFont(QFont("JetBrains Mono", 12, QFont.Weight.Bold))
        self.ks_status.setStyleSheet(f"color: {GREEN};")
        ks_layout.addWidget(self.ks_status)
        ks_layout.addStretch()

        layout.addWidget(ks_group)

        # VPN Status
        vpn_group = QGroupBox("VPN Status")
        vpn_layout = QFormLayout(vpn_group)

        self.vpn_status = QLabel("Not connected")
        self.vpn_status.setStyleSheet(f"color: {TEXT_SECONDARY};")
        vpn_layout.addRow("Status:", self.vpn_status)

        vpn_btn = QPushButton("Check VPN")
        vpn_btn.setStyleSheet(f"background: {BG_CARD}; color: {TEXT_PRIMARY}; padding: 6px 12px; border: 1px solid #334155; border-radius: 6px;")
        vpn_btn.clicked.connect(self._check_vpn)
        vpn_layout.addRow("", vpn_btn)

        layout.addWidget(vpn_group)

        # System integrity
        integrity_group = QGroupBox("System Integrity")
        integrity_layout = QVBoxLayout(integrity_group)
        self.integrity_log = QTextEdit()
        self.integrity_log.setReadOnly(True)
        self.integrity_log.setMaximumHeight(120)
        self.integrity_log.setPlaceholderText("Run integrity check to verify system...")
        self.integrity_log.setStyleSheet("font-family: 'JetBrains Mono', monospace; font-size: 11px;")
        integrity_layout.addWidget(self.integrity_log)

        int_btn = QPushButton("Run Integrity Check")
        int_btn.setStyleSheet(f"background: {BG_CARD}; color: {TEXT_PRIMARY}; padding: 6px 12px; border: 1px solid #334155; border-radius: 6px;")
        int_btn.clicked.connect(self._check_integrity)
        integrity_layout.addWidget(int_btn)

        layout.addWidget(integrity_group)

        layout.addStretch()
        self.tabs.addTab(scroll, "SYSTEM")

    # ═══════════════════════════════════════════════════════════════════════════
    # ACTIONS
    # ═══════════════════════════════════════════════════════════════════════════

    def _run_health_check(self):
        self.status_bar.setText("Running health check...")
        self.worker = HealthCheckWorker()
        self.worker.finished.connect(self._on_health_result)
        self.worker.start()

    def _on_health_result(self, data: dict):
        self.health_data = data

        # Modules
        core = data.get("core_count", 0)
        imp = data.get("importable", 0)
        failed = data.get("failed", [])
        color = GREEN if len(failed) == 0 else YELLOW if len(failed) < 5 else RED
        self.lbl_modules.setText(f"{imp}/{core} importable ({len(failed)} failed)")
        self.lbl_modules.setStyleSheet(f"color: {color}; font-weight: bold;")

        # RAM
        pct = data.get("ram_pct", -1)
        if pct >= 0:
            used = data.get("ram_used_gb", 0)
            total = data.get("ram_total_gb", 0)
            color = GREEN if pct < 70 else YELLOW if pct < 85 else RED
            self.lbl_ram.setText(f"{used}/{total} GB ({pct}%)")
            self.lbl_ram.setStyleSheet(f"color: {color};")
            self.mem_bar.setValue(int(pct))
            zone = "GREEN" if pct < 60 else "YELLOW" if pct < 75 else "RED" if pct < 90 else "CRITICAL"
            self.mem_status.setText(f"Zone: {zone} | {used:.1f}/{total:.1f} GB")
        else:
            self.lbl_ram.setText("psutil not available")
            self.lbl_ram.setStyleSheet(f"color: {TEXT_SECONDARY};")

        # Disk
        disk = data.get("disk_free_gb", -1)
        if disk >= 0:
            color = GREEN if disk > 10 else YELLOW if disk > 2 else RED
            self.lbl_disk.setText(f"{disk} GB free")
            self.lbl_disk.setStyleSheet(f"color: {color};")
        else:
            self.lbl_disk.setText("N/A")

        # AI
        ai = data.get("ai_status", {})
        if ai.get("available"):
            self.lbl_ai.setText(f"Online ({ai.get('model', 'unknown')})")
            self.lbl_ai.setStyleSheet(f"color: {GREEN};")
        else:
            self.lbl_ai.setText("Offline")
            self.lbl_ai.setStyleSheet(f"color: {YELLOW};")

        # Services
        svcs = data.get("services", {})
        running = sum(1 for s in svcs.values() if isinstance(s, dict) and s.get("running"))
        self.lbl_services_count.setText(f"{running}/{len(svcs)} running")
        self.lbl_services_count.setStyleSheet(f"color: {GREEN if running > 0 else YELLOW};")

        self.status_bar.setText(f"Health check complete \u2014 {imp}/{core} modules, {pct}% RAM")

    def _start_services(self):
        if SERVICES_AVAILABLE:
            try:
                start_all_services()
                self.status_bar.setText("All services started")
                QTimer.singleShot(1000, self._run_health_check)
            except Exception as e:
                self.status_bar.setText(f"Error: {e}")
        else:
            self.status_bar.setText("Service manager not available")

    def _stop_services(self):
        if SERVICES_AVAILABLE:
            try:
                stop_all_services()
                self.status_bar.setText("All services stopped")
                QTimer.singleShot(1000, self._run_health_check)
            except Exception as e:
                self.status_bar.setText(f"Error: {e}")

    def _submit_bug(self):
        title = self.bug_title.text().strip()
        if not title:
            QMessageBox.warning(self, "Missing Info", "Bug title is required")
            return

        bug = {
            "title": title,
            "severity": self.bug_severity.currentText().split(" - ")[0],
            "module": self.bug_module.currentText(),
            "description": self.bug_desc.toPlainText(),
            "timestamp": datetime.now().isoformat(),
        }

        # Save to bugs directory
        bugs_dir = Path(__file__).parent.parent / "state" / "bugs"
        bugs_dir.mkdir(parents=True, exist_ok=True)
        bug_file = bugs_dir / f"bug_{int(time.time())}.json"
        bug_file.write_text(json.dumps(bug, indent=2))

        self.bug_title.clear()
        self.bug_desc.clear()
        self.status_bar.setText(f"Bug submitted: {bug_file.name}")
        QMessageBox.information(self, "Bug Submitted", f"Bug report saved to {bug_file.name}")

    def _auto_patch(self):
        if BUG_BRIDGE_AVAILABLE:
            try:
                bridge = BugPatchBridge()
                self.patch_log.append(f"[{datetime.now().strftime('%H:%M:%S')}] Auto-patch dispatched to Windsurf IDE")
                self.status_bar.setText("Auto-patch dispatched")
            except Exception as e:
                self.patch_log.append(f"[ERROR] {e}")
        else:
            self.patch_log.append("[WARN] Bug Patch Bridge not available")

    def _test_ai(self):
        endpoint = self.ai_endpoint.text().strip()
        self.ai_status_text.setText("Testing...")
        self.ai_status_text.setStyleSheet(f"color: {YELLOW};")

        try:
            import urllib.request
            req = urllib.request.Request(f"{endpoint}/api/tags", method="GET")
            req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
                models = data.get("models", [])
                names = [m.get("name", "?") for m in models[:5]]
                self.ai_status_text.setText(f"Connected \u2014 {len(models)} models: {', '.join(names)}")
                self.ai_status_text.setStyleSheet(f"color: {GREEN}; font-weight: bold;")
        except Exception as e:
            self.ai_status_text.setText(f"Failed: {str(e)[:80]}")
            self.ai_status_text.setStyleSheet(f"color: {RED};")

    def _scan_modules(self):
        core_dir = Path(__file__).parent.parent / "core"
        py_files = sorted(core_dir.glob("*.py"))

        self.mod_table.setRowCount(0)
        for f in py_files:
            if f.name == "__init__.py":
                continue
            row = self.mod_table.rowCount()
            self.mod_table.insertRow(row)
            self.mod_table.setItem(row, 0, QTableWidgetItem(f.stem))

            try:
                mod = __import__(f.stem)
                classes = [name for name in dir(mod) if isinstance(getattr(mod, name, None), type)]
                self.mod_table.setItem(row, 1, QTableWidgetItem("OK"))
                self.mod_table.item(row, 1).setForeground(QColor(GREEN))
                self.mod_table.setItem(row, 2, QTableWidgetItem(str(len(classes))))
            except Exception as e:
                self.mod_table.setItem(row, 1, QTableWidgetItem(f"FAIL: {str(e)[:40]}"))
                self.mod_table.item(row, 1).setForeground(QColor(RED))
                self.mod_table.setItem(row, 2, QTableWidgetItem("-"))

        self.status_bar.setText(f"Scanned {self.mod_table.rowCount()} modules")

    def _arm_kill_switch(self):
        reply = QMessageBox.question(
            self, "Arm Kill Switch",
            "This will arm the kill switch for emergency data wipe.\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.ks_status.setText("ARMED")
            self.ks_status.setStyleSheet(f"color: {RED}; font-weight: bold;")
            self.ks_panic_btn.setEnabled(True)
            self.ks_arm_btn.setEnabled(False)
            if KILL_SWITCH_AVAILABLE:
                try:
                    arm_kill_switch()
                except Exception:
                    pass

    def _panic(self):
        reply = QMessageBox.critical(
            self, "CONFIRM PANIC",
            "THIS WILL WIPE ALL PROFILES AND SESSIONS.\n\nThis action CANNOT be undone.\n\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            if KILL_SWITCH_AVAILABLE:
                try:
                    send_panic_signal()
                except Exception:
                    pass
            self.ks_status.setText("PANIC SENT")
            self.ks_status.setStyleSheet(f"color: {RED}; font-weight: bold;")

    def _check_vpn(self):
        if VPN_AVAILABLE:
            try:
                vpn = LucidVPN()
                status = vpn.get_status()
                if status and hasattr(status, 'connected') and status.connected:
                    self.vpn_status.setText(f"Connected \u2014 {status.exit_ip}")
                    self.vpn_status.setStyleSheet(f"color: {GREEN}; font-weight: bold;")
                else:
                    self.vpn_status.setText("Disconnected")
                    self.vpn_status.setStyleSheet(f"color: {YELLOW};")
            except Exception as e:
                self.vpn_status.setText(f"Error: {str(e)[:60]}")
                self.vpn_status.setStyleSheet(f"color: {RED};")
        else:
            self.vpn_status.setText("VPN module not available")

    def _check_integrity(self):
        self.integrity_log.clear()
        self.integrity_log.append(f"[{datetime.now().strftime('%H:%M:%S')}] Running integrity check...")

        if IMMUTABLE_AVAILABLE:
            try:
                result = verify_system_integrity()
                self.integrity_log.append(f"System integrity: {result}")
                boot = get_boot_status()
                self.integrity_log.append(f"Boot status: {boot}")
            except Exception as e:
                self.integrity_log.append(f"[ERROR] {e}")
        else:
            self.integrity_log.append("[INFO] Immutable OS module not available (normal on dev machines)")

        # Check core files
        core_dir = Path(__file__).parent.parent / "core"
        py_count = len(list(core_dir.glob("*.py")))
        self.integrity_log.append(f"Core modules: {py_count} files")
        self.integrity_log.append(f"Apps: {len(list(Path(__file__).parent.glob('*.py')))} files")
        self.integrity_log.append("Integrity check complete")

    def apply_theme(self):
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(BG_DARK))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(TEXT_PRIMARY))
        palette.setColor(QPalette.ColorRole.Base, QColor(BG_CARD))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#1e293b"))
        palette.setColor(QPalette.ColorRole.Text, QColor(TEXT_PRIMARY))
        palette.setColor(QPalette.ColorRole.Button, QColor(BG_CARD))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(TEXT_PRIMARY))
        self.setPalette(palette)
        self.setStyleSheet(f"""
            QMainWindow {{ background: {BG_DARK}; }}
            QGroupBox {{
                background: {BG_CARD};
                border: 1px solid #1e293b;
                border-radius: 10px;
                margin-top: 16px;
                padding-top: 20px;
                color: {TEXT_PRIMARY};
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
                color: {ACCENT};
            }}
            QLineEdit, QComboBox, QSpinBox, QPlainTextEdit {{
                background: #1e293b;
                color: {TEXT_PRIMARY};
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px;
            }}
            QTextEdit {{
                background: #0f172a;
                color: {TEXT_PRIMARY};
                border: 1px solid #1e293b;
                border-radius: 6px;
            }}
            QTableWidget {{
                background: #0f172a;
                color: {TEXT_PRIMARY};
                gridline-color: #1e293b;
                border: none;
            }}
            QHeaderView::section {{
                background: {BG_CARD};
                color: {ACCENT};
                padding: 6px;
                border: none;
                font-weight: bold;
            }}
            QLabel {{ background: transparent; }}
            QProgressBar {{
                background: #1e293b;
                border: none;
                border-radius: 6px;
                text-align: center;
                color: {TEXT_PRIMARY};
            }}
            QProgressBar::chunk {{
                background: {ACCENT};
                border-radius: 6px;
            }}
        """)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = TitanAdmin()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
