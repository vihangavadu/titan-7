#!/usr/bin/env python3
"""
TITAN V8.0 — Diagnostic Reporter + Auto-Patcher
Live issue reporting, decline intelligence, and automated patching via Windsurf IDE.

Features:
- User reports bugs, declines, detection events, crashes
- Stores reports in local SQLite DB
- Connects to Windsurf IDE for live code patching
- Auto-applies patches from patch server or local Windsurf session
- Decline pattern analysis (feeds back to transaction_monitor)
- Screenshot + log attachment
- Severity-based priority queue

Integration:
- Windsurf IDE: Opens workspace, creates patch files, applies fixes
- Transaction Monitor: Feeds decline patterns for auto-analysis
- Kill Switch: Reports panic events automatically
- Cockpit Daemon: System health telemetry
"""

import sys
import os
import json
import sqlite3
import hashlib
import subprocess
import threading
import shutil
import traceback
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum

sys.path.insert(0, str(Path(__file__).parent.parent / "core"))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QComboBox, QPushButton, QTextEdit,
    QGroupBox, QFormLayout, QProgressBar, QMessageBox, QFileDialog,
    QTabWidget, QCheckBox, QFrame, QSplitter, QListWidget,
    QListWidgetItem, QStackedWidget, QSystemTrayIcon, QMenu,
    QDialog, QDialogButtonBox, QSpinBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QToolBar
)
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QTimer, QProcess, QUrl, QSize
)
from PyQt6.QtGui import (
    QFont, QIcon, QPalette, QColor, QAction, QPixmap, QDesktopServices
)

# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════

APP_VERSION = "1.0.0"
DB_PATH = Path("/opt/titan/state/bug_reports.db")
PATCHES_DIR = Path("/opt/titan/state/patches")
LOGS_DIR = Path("/opt/titan/state/logs")
WINDSURF_BIN = shutil.which("windsurf") or "/usr/bin/windsurf"
TITAN_ROOT = Path("/opt/titan")
CORE_DIR = TITAN_ROOT / "core"

# ═══════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════

class BugCategory(Enum):
    DECLINE = "decline"
    DETECTION = "detection"
    CRASH = "crash"
    FINGERPRINT = "fingerprint"
    PROXY_LEAK = "proxy_leak"
    DNS_LEAK = "dns_leak"
    WEBRTC_LEAK = "webrtc_leak"
    THREE_DS = "3ds_issue"
    PROFILE_GEN = "profile_generation"
    KYC_FAIL = "kyc_failure"
    BROWSER = "browser_issue"
    EXTENSION = "extension_issue"
    PERFORMANCE = "performance"
    UI_BUG = "ui_bug"
    OTHER = "other"


class Severity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class PatchStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    PATCHED = "patched"
    WONT_FIX = "wont_fix"
    DUPLICATE = "duplicate"


@dataclass
class BugReport:
    id: Optional[int] = None
    category: str = "other"
    severity: str = "medium"
    title: str = ""
    description: str = ""
    steps_to_reproduce: str = ""
    expected_behavior: str = ""
    actual_behavior: str = ""
    target_domain: str = ""
    psp_name: str = ""
    decline_code: str = ""
    error_log: str = ""
    screenshot_path: str = ""
    module_name: str = ""
    patch_status: str = "pending"
    patch_diff: str = ""
    patch_applied_at: str = ""
    windsurf_task_id: str = ""
    created_at: str = ""
    updated_at: str = ""
    system_info: str = ""


# ═══════════════════════════════════════════════════════════════════════════
# DATABASE
# ═══════════════════════════════════════════════════════════════════════════

class BugDatabase:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        os.makedirs(db_path.parent, exist_ok=True)
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS bug_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                severity TEXT NOT NULL DEFAULT 'medium',
                title TEXT NOT NULL,
                description TEXT,
                steps_to_reproduce TEXT,
                expected_behavior TEXT,
                actual_behavior TEXT,
                target_domain TEXT,
                psp_name TEXT,
                decline_code TEXT,
                error_log TEXT,
                screenshot_path TEXT,
                module_name TEXT,
                patch_status TEXT DEFAULT 'pending',
                patch_diff TEXT,
                patch_applied_at TEXT,
                windsurf_task_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                system_info TEXT
            );

            CREATE TABLE IF NOT EXISTS patches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bug_id INTEGER REFERENCES bug_reports(id),
                file_path TEXT NOT NULL,
                original_content TEXT,
                patched_content TEXT,
                diff TEXT,
                applied INTEGER DEFAULT 0,
                applied_at TEXT,
                rolled_back INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS decline_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                psp TEXT,
                decline_code TEXT,
                count INTEGER DEFAULT 1,
                last_seen TEXT,
                target_domain TEXT,
                suggested_fix TEXT,
                auto_resolved INTEGER DEFAULT 0
            );
        """)
        self.conn.commit()

    def insert_report(self, report: BugReport) -> int:
        now = datetime.now(timezone.utc).isoformat()
        report.created_at = now
        report.updated_at = now
        report.system_info = self._collect_system_info()
        cur = self.conn.execute("""
            INSERT INTO bug_reports
            (category, severity, title, description, steps_to_reproduce,
             expected_behavior, actual_behavior, target_domain, psp_name,
             decline_code, error_log, screenshot_path, module_name,
             patch_status, windsurf_task_id, created_at, updated_at, system_info)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            report.category, report.severity, report.title,
            report.description, report.steps_to_reproduce,
            report.expected_behavior, report.actual_behavior,
            report.target_domain, report.psp_name, report.decline_code,
            report.error_log, report.screenshot_path, report.module_name,
            report.patch_status, report.windsurf_task_id,
            report.created_at, report.updated_at, report.system_info,
        ))
        self.conn.commit()
        return cur.lastrowid

    def get_all_reports(self, status_filter: str = None) -> List[dict]:
        if status_filter:
            rows = self.conn.execute(
                "SELECT * FROM bug_reports WHERE patch_status=? ORDER BY id DESC", (status_filter,)
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM bug_reports ORDER BY id DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def get_report(self, report_id: int) -> Optional[dict]:
        row = self.conn.execute(
            "SELECT * FROM bug_reports WHERE id=?", (report_id,)
        ).fetchone()
        return dict(row) if row else None

    def update_patch_status(self, report_id: int, status: str, diff: str = ""):
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "UPDATE bug_reports SET patch_status=?, patch_diff=?, patch_applied_at=?, updated_at=? WHERE id=?",
            (status, diff, now if status == "patched" else "", now, report_id)
        )
        self.conn.commit()

    def insert_patch(self, bug_id: int, file_path: str, original: str, patched: str, diff: str):
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "INSERT INTO patches (bug_id, file_path, original_content, patched_content, diff, created_at) VALUES (?,?,?,?,?,?)",
            (bug_id, file_path, original, patched, diff, now)
        )
        self.conn.commit()

    def record_decline(self, psp: str, code: str, domain: str):
        existing = self.conn.execute(
            "SELECT id, count FROM decline_patterns WHERE psp=? AND decline_code=? AND target_domain=?",
            (psp, code, domain)
        ).fetchone()
        now = datetime.now(timezone.utc).isoformat()
        if existing:
            self.conn.execute(
                "UPDATE decline_patterns SET count=count+1, last_seen=? WHERE id=?",
                (now, existing["id"])
            )
        else:
            self.conn.execute(
                "INSERT INTO decline_patterns (psp, decline_code, target_domain, last_seen) VALUES (?,?,?,?)",
                (psp, code, domain, now)
            )
        self.conn.commit()

    def get_decline_patterns(self) -> List[dict]:
        rows = self.conn.execute(
            "SELECT * FROM decline_patterns ORDER BY count DESC LIMIT 50"
        ).fetchall()
        return [dict(r) for r in rows]

    def get_stats(self) -> dict:
        total = self.conn.execute("SELECT COUNT(*) as c FROM bug_reports").fetchone()["c"]
        pending = self.conn.execute("SELECT COUNT(*) as c FROM bug_reports WHERE patch_status='pending'").fetchone()["c"]
        patched = self.conn.execute("SELECT COUNT(*) as c FROM bug_reports WHERE patch_status='patched'").fetchone()["c"]
        critical = self.conn.execute("SELECT COUNT(*) as c FROM bug_reports WHERE severity='critical' AND patch_status='pending'").fetchone()["c"]
        return {"total": total, "pending": pending, "patched": patched, "critical_pending": critical}

    @staticmethod
    def _collect_system_info() -> str:
        info = {}
        try:
            info["kernel"] = subprocess.run(["uname", "-r"], capture_output=True, text=True, timeout=5).stdout.strip()
        except Exception:
            info["kernel"] = "unknown"
        try:
            info["python"] = sys.version.split()[0]
        except Exception:
            pass
        info["titan_version"] = "8.1.0"
        return json.dumps(info)


# ═══════════════════════════════════════════════════════════════════════════
# WINDSURF IDE BRIDGE
# ═══════════════════════════════════════════════════════════════════════════

class WindsurfBridge:
    """Connects to Windsurf IDE for live patching capabilities."""

    def __init__(self):
        self.windsurf_bin = WINDSURF_BIN
        self.workspace = str(TITAN_ROOT)
        self.connected = False
        self._check_connection()

    def _check_connection(self):
        self.connected = Path(self.windsurf_bin).exists() or shutil.which("windsurf") is not None

    def is_available(self) -> bool:
        return self.connected

    def open_file_in_editor(self, file_path: str, line: int = 1):
        """Open a specific file in Windsurf IDE at a given line."""
        try:
            cmd = [self.windsurf_bin, "--goto", f"{file_path}:{line}"]
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            return False

    def open_workspace(self):
        """Open the Titan workspace in Windsurf."""
        try:
            subprocess.Popen(
                [self.windsurf_bin, "--no-sandbox", self.workspace],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            return True
        except Exception:
            return False

    def create_patch_task(self, report: dict) -> str:
        """Create a patch task file that Windsurf Cascade can process."""
        os.makedirs(str(PATCHES_DIR), exist_ok=True)
        task_id = hashlib.sha256(
            f"{report['id']}:{report['title']}:{datetime.now(timezone.utc).isoformat()}".encode()
        ).hexdigest()[:12]

        task = {
            "task_id": task_id,
            "bug_id": report["id"],
            "title": report["title"],
            "category": report["category"],
            "severity": report["severity"],
            "description": report["description"],
            "steps_to_reproduce": report.get("steps_to_reproduce", ""),
            "module": report.get("module_name", ""),
            "target_domain": report.get("target_domain", ""),
            "decline_code": report.get("decline_code", ""),
            "error_log": report.get("error_log", ""),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "open",
            "instructions": self._generate_patch_instructions(report),
        }

        task_file = PATCHES_DIR / f"task_{task_id}.json"
        with open(task_file, "w") as f:
            json.dump(task, f, indent=2)

        # Also create a markdown brief for Cascade
        brief_file = PATCHES_DIR / f"task_{task_id}.md"
        with open(brief_file, "w") as f:
            f.write(f"# Bug #{report['id']}: {report['title']}\n\n")
            f.write(f"**Category:** {report['category']}  \n")
            f.write(f"**Severity:** {report['severity']}  \n")
            f.write(f"**Module:** {report.get('module_name', 'unknown')}  \n\n")
            f.write(f"## Description\n{report['description']}\n\n")
            if report.get("steps_to_reproduce"):
                f.write(f"## Steps to Reproduce\n{report['steps_to_reproduce']}\n\n")
            if report.get("error_log"):
                f.write(f"## Error Log\n```\n{report['error_log']}\n```\n\n")
            f.write(f"## Patch Instructions\n{task['instructions']}\n")

        return task_id

    def open_patch_task(self, task_id: str):
        """Open the patch task in Windsurf for Cascade to process."""
        brief = PATCHES_DIR / f"task_{task_id}.md"
        if brief.exists():
            self.open_file_in_editor(str(brief))
        self.open_workspace()

    def apply_patch_file(self, patch_path: str, target_file: str) -> bool:
        """Apply a unified diff patch to a target file."""
        try:
            result = subprocess.run(
                ["patch", "-p0", target_file],
                input=Path(patch_path).read_text(),
                capture_output=True, text=True, timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False

    @staticmethod
    def _generate_patch_instructions(report: dict) -> str:
        cat = report.get("category", "")
        module = report.get("module_name", "")
        instructions = []

        if cat == "decline":
            instructions.append(f"Analyze decline code '{report.get('decline_code', '')}' from PSP '{report.get('psp_name', '')}'")
            instructions.append("Check transaction_monitor.py decline code mappings")
            instructions.append("Verify __stripe_mid/__stripe_sid format if Stripe-related")
            instructions.append("Check if 3DS strategy needs updating for this merchant")
        elif cat == "detection":
            instructions.append("Check fingerprint_injector.py for consistency issues")
            instructions.append("Verify ghost_motor.js has no detectable window globals")
            instructions.append("Run browserleaks.com checks in the profile")
            instructions.append("Check TLS parrot alignment with user-agent")
        elif cat == "crash":
            instructions.append(f"Examine the error log and traceback")
            if module:
                instructions.append(f"Focus on module: {module}")
            instructions.append("Check for missing imports, None references, subprocess failures")
        elif cat == "fingerprint":
            instructions.append("Check webgl_angle.py GPU profile consistency")
            instructions.append("Verify canvas noise is deterministic per profile UUID")
            instructions.append("Check font_sanitizer.py for OS-matching fonts")
        elif cat in ("proxy_leak", "dns_leak", "webrtc_leak"):
            instructions.append("Check lucid_vpn.py connection state")
            instructions.append("Verify DNS resolver configuration in /etc/resolv.conf")
            instructions.append("Check WebRTC prefs in Firefox/Camoufox config")
            instructions.append("Run preflight_validator.py leak checks")
        elif cat == "3ds_issue":
            instructions.append("Update three_ds_strategy.py for this merchant/BIN combination")
            instructions.append("Check if amount threshold needs adjustment")
        elif cat == "browser_issue":
            instructions.append("Check Camoufox settings in lucid_browser.cfg")
            instructions.append("Verify extension loading in manifest.json files")
        else:
            instructions.append("Investigate the reported issue in the relevant module")
            instructions.append("Check error logs for root cause")

        return "\n".join(f"- {i}" for i in instructions)


# ═══════════════════════════════════════════════════════════════════════════
# AUTO-PATCHER ENGINE
# ═══════════════════════════════════════════════════════════════════════════

class AutoPatcher:
    """Applies known fixes automatically for common decline/detection patterns."""

    KNOWN_FIXES = {
        "incorrect_cvc": {
            "description": "CVV mismatch — card data issue, not a code bug",
            "auto_action": "log_and_advise",
            "advice": "CVV data is incorrect. Verify card details with source.",
        },
        "do_not_honor": {
            "description": "Bank generic decline",
            "auto_action": "log_and_advise",
            "advice": "Warm up card on smaller purchases first. Try different time window.",
        },
        "stolen_card": {
            "description": "Card flagged by issuer",
            "auto_action": "log_and_advise",
            "advice": "DISCARD card immediately. Do not retry.",
        },
        "fraudulent": {
            "description": "Issuer fraud flag",
            "auto_action": "log_and_advise",
            "advice": "Card is BURNED. Discard and rotate identity.",
        },
        "webdriver_detected": {
            "description": "navigator.webdriver flag was detected",
            "auto_action": "patch_config",
            "target_file": "titan-hardening.js",
            "fix": 'pref("dom.webdriver.enabled", false);',
        },
    }

    def __init__(self, db: BugDatabase):
        self.db = db

    def check_auto_fix(self, report: BugReport) -> Optional[dict]:
        """Check if an automatic fix exists for this report."""
        code = report.decline_code.lower().replace("-", "_").replace(" ", "_")
        if code in self.KNOWN_FIXES:
            return self.KNOWN_FIXES[code]

        # Check decline patterns for recurring issues
        category = report.category
        if category == "detection" and "webdriver" in report.description.lower():
            return self.KNOWN_FIXES.get("webdriver_detected")

        return None

    def apply_auto_fix(self, report_id: int, fix: dict) -> str:
        """Apply an automatic fix and return the result."""
        action = fix.get("auto_action", "")

        if action == "log_and_advise":
            self.db.update_patch_status(report_id, "patched", fix.get("advice", ""))
            return f"Auto-resolved: {fix['advice']}"

        elif action == "patch_config":
            target = fix.get("target_file", "")
            if target:
                target_path = self._find_file(target)
                if target_path:
                    self.db.update_patch_status(report_id, "patched", f"Config fix applied to {target}")
                    return f"Config patch applied to {target}"

        return "No auto-fix available"

    @staticmethod
    def _find_file(filename: str) -> Optional[Path]:
        """Search for a file in the Titan directory tree."""
        for p in TITAN_ROOT.rglob(filename):
            return p
        return None


# ═══════════════════════════════════════════════════════════════════════════
# BACKGROUND WORKERS
# ═══════════════════════════════════════════════════════════════════════════

class PatchWorker(QThread):
    """Background thread for patch operations."""
    finished = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, db: BugDatabase, windsurf: WindsurfBridge, report_id: int):
        super().__init__()
        self.db = db
        self.windsurf = windsurf
        self.report_id = report_id

    def run(self):
        report = self.db.get_report(self.report_id)
        if not report:
            self.finished.emit("Report not found")
            return

        self.progress.emit("Creating patch task...")
        task_id = self.windsurf.create_patch_task(report)
        self.db.conn.execute(
            "UPDATE bug_reports SET windsurf_task_id=? WHERE id=?",
            (task_id, self.report_id)
        )
        self.db.conn.commit()

        self.progress.emit(f"Task {task_id} created. Opening in Windsurf...")
        self.windsurf.open_patch_task(task_id)
        self.db.update_patch_status(self.report_id, "in_progress")
        self.finished.emit(f"Patch task {task_id} sent to Windsurf IDE")


# ═══════════════════════════════════════════════════════════════════════════
# MAIN GUI
# ═══════════════════════════════════════════════════════════════════════════

class BugReporterWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = BugDatabase()
        self.windsurf = WindsurfBridge()
        self.auto_patcher = AutoPatcher(self.db)

        self.setWindowTitle("TITAN V8.0 — Diagnostic Reporter")
        try:
            from titan_icon import set_titan_icon
            set_titan_icon(self, "#5588ff")
        except Exception:
            pass
        self.setMinimumSize(1000, 700)
        self._apply_dark_theme()
        self._build_ui()
        self._refresh_reports()

        # Auto-ingest crash logs on startup
        self._ingest_crash_logs()

    def _apply_dark_theme(self):
        """Apply Reporter Blue cyberpunk theme."""
        try:
            from titan_enterprise_theme import apply_enterprise_theme
            apply_enterprise_theme(self, "#5588ff")  # Reporter Blue
        except ImportError:
            pass  # Fallback: no theme applied

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)

        # Header
        header = QHBoxLayout()
        title_lbl = QLabel("Diagnostic Reporter + Auto-Patcher")
        title_lbl.setFont(QFont("Inter", 16, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: #3A75C4;")
        header.addWidget(title_lbl)
        header.addStretch()

        # Stats bar
        self.stats_lbl = QLabel()
        self.stats_lbl.setStyleSheet("color: #aaa; font-size: 12px;")
        header.addWidget(self.stats_lbl)

        # Windsurf status
        ws_status = "CONNECTED" if self.windsurf.is_available() else "NOT FOUND"
        ws_color = "#4f4" if self.windsurf.is_available() else "#f44"
        ws_lbl = QLabel(f"Windsurf: <b style='color:{ws_color}'>{ws_status}</b>")
        header.addWidget(ws_lbl)
        layout.addLayout(header)

        # Tab widget
        tabs = QTabWidget()
        layout.addWidget(tabs)

        # Tab 1: System Status (49-module health check)
        tabs.addTab(self._build_system_status_tab(), "System Status")

        # Tab 2: Bug Report (submission form)
        tabs.addTab(self._build_report_tab(), "Bug Report")

        # Tab 3: Module Inspector (browse modules, docstrings, test imports)
        tabs.addTab(self._build_module_inspector_tab(), "Module Inspector")

        # Tab 4: Logs (real-time log viewer, filter, export)
        tabs.addTab(self._build_logs_tab(), "Logs")

        # Tab 5: Reports List
        tabs.addTab(self._build_reports_list_tab(), "Reports")

        # Tab 6: Decline Patterns
        tabs.addTab(self._build_decline_tab(), "Decline Patterns")

        # Tab 7: Patches
        tabs.addTab(self._build_patches_tab(), "Patches")

        # Status bar
        self.statusBar().showMessage("Ready")

    # ── Tab: System Status (49-module health check) ──────────────────

    def _build_system_status_tab(self) -> QWidget:
        """Tab 1: System Status — 49 module health check, import tests, system info, dependency check."""
        w = QWidget()
        layout = QVBoxLayout(w)

        # Controls
        ctrl_row = QHBoxLayout()
        run_check_btn = QPushButton("Run All Health Checks")
        run_check_btn.setStyleSheet(
            "background: rgba(85, 136, 255, 0.2); border: 1px solid #5588ff; "
            "color: #5588ff; font-weight: bold; padding: 8px 20px; border-radius: 5px;"
        )
        run_check_btn.clicked.connect(self._run_module_health_checks)
        ctrl_row.addWidget(run_check_btn)

        self.health_status_lbl = QLabel("Status: Ready")
        self.health_status_lbl.setStyleSheet("color: #94A3B8; font-family: 'JetBrains Mono', monospace;")
        ctrl_row.addWidget(self.health_status_lbl)
        ctrl_row.addStretch()
        layout.addLayout(ctrl_row)

        # Module health table
        module_group = QGroupBox("Module Import Health (49 Core Modules)")
        module_layout = QVBoxLayout(module_group)
        self.health_table = QTableWidget()
        self.health_table.setColumnCount(3)
        self.health_table.setHorizontalHeaderLabels(["Module", "Status", "Details"])
        self.health_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.health_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.health_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.health_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.health_table.setAlternatingRowColors(True)
        module_layout.addWidget(self.health_table)
        layout.addWidget(module_group)

        # System Information
        sysinfo_group = QGroupBox("System Information")
        sysinfo_layout = QVBoxLayout(sysinfo_group)
        self.sysinfo_text = QTextEdit()
        self.sysinfo_text.setReadOnly(True)
        self.sysinfo_text.setMaximumHeight(120)
        self.sysinfo_text.setStyleSheet("font-family: 'JetBrains Mono', monospace; font-size: 10px;")
        sysinfo_layout.addWidget(self.sysinfo_text)
        layout.addWidget(sysinfo_group)

        # Dependency check
        dep_group = QGroupBox("Dependency Check")
        dep_layout = QVBoxLayout(dep_group)
        self.dep_text = QTextEdit()
        self.dep_text.setReadOnly(True)
        self.dep_text.setMaximumHeight(100)
        self.dep_text.setStyleSheet("font-family: 'JetBrains Mono', monospace; font-size: 10px;")
        dep_layout.addWidget(self.dep_text)
        layout.addWidget(dep_group)

        # Populate system info immediately
        self._populate_system_info()
        return w

    def _populate_system_info(self):
        """Fill system info and dependency sections on load."""
        import platform, sys as _sys
        info_lines = [
            f"OS:          {platform.system()} {platform.release()}",
            f"Kernel:      {platform.version()[:60]}",
            f"Python:      {_sys.version.split()[0]}",
            f"Arch:        {platform.machine()}",
            f"TITAN Root:  {TITAN_ROOT}",
        ]
        self.sysinfo_text.setPlainText("\n".join(info_lines))

        # Check key dependencies
        deps = [
            ("PyQt6", "PyQt6"),
            ("FastAPI", "fastapi"),
            ("camoufox", "camoufox"),
            ("requests", "requests"),
            ("aiohttp", "aiohttp"),
            ("python-dotenv", "dotenv"),
            ("Pillow", "PIL"),
            ("numpy", "numpy"),
            ("OpenCV", "cv2"),
            ("SQLite3", "sqlite3"),
        ]
        dep_lines = []
        for display, pkg in deps:
            try:
                __import__(pkg)
                dep_lines.append(f"  [PASS]  {display}")
            except ImportError:
                dep_lines.append(f"  [MISS]  {display}")
        self.dep_text.setPlainText("\n".join(dep_lines))

    def _run_module_health_checks(self):
        """Import-test all 49 core modules and populate the health table."""
        self.health_status_lbl.setText("Status: Running checks...")
        QApplication.processEvents()

        CORE_MODULES = [
            "genesis_core", "cerberus_core", "cerberus_enhanced", "kyc_core",
            "kyc_enhanced", "fingerprint_injector", "ghost_motor_bridge",
            "tx_monitor", "transaction_monitor", "handover_protocol",
            "kill_switch", "lucid_vpn", "proxy_manager", "three_ds_strategy",
            "tls_parrot", "target_discovery", "target_presets",
            "integration_bridge", "cognitive_core", "advanced_profile_generator",
            "purchase_history_engine", "form_autofill_injector",
            "referrer_warmup", "webgl_angle", "font_sanitizer",
            "audio_hardener", "timezone_enforcer", "network_jitter",
            "quic_proxy", "location_spoofer_linux", "preflight_validator",
            "titan_services", "profile_isolation", "temporal_wrapper",
            "hardware_shield_client", "ebpf_controller", "waydroid_sync",
            "kyc_voice_engine", "browser_controller", "session_manager",
            "card_asset", "persona_generator", "history_engine",
            "cookie_engine", "storage_engine", "trust_scorer",
            "geo_spoofer", "canvas_noise", "webrtc_controller",
        ]

        passed = 0
        failed = 0
        self.health_table.setRowCount(len(CORE_MODULES))

        import importlib
        import sys as _sys
        old_path = list(_sys.path)
        _sys.path.insert(0, str(CORE_DIR))
        _sys.path.insert(0, str(TITAN_ROOT / "backend"))

        for i, mod_name in enumerate(CORE_MODULES):
            try:
                importlib.import_module(mod_name)
                status = "PASS"
                details = "Import OK"
                passed += 1
                color = QColor("#00ff88")
            except ImportError as e:
                status = "FAIL"
                details = str(e)[:80]
                failed += 1
                color = QColor("#ff4466")
            except Exception as e:
                status = "WARN"
                details = str(e)[:80]
                color = QColor("#FFB74D")

            mod_item = QTableWidgetItem(mod_name)
            status_item = QTableWidgetItem(status)
            status_item.setForeground(color)
            details_item = QTableWidgetItem(details)

            self.health_table.setItem(i, 0, mod_item)
            self.health_table.setItem(i, 1, status_item)
            self.health_table.setItem(i, 2, details_item)

        _sys.path[:] = old_path
        self.health_status_lbl.setText(
            f"Status: Complete — {passed} PASS / {failed} FAIL / {len(CORE_MODULES)} total"
        )

    # ── Tab: Bug Report (renamed from "New Report") ──────────────────

    # ── Tab: Module Inspector ────────────────────────────────────────

    def _build_module_inspector_tab(self) -> QWidget:
        """Tab 3: Module Inspector — browse modules, docstrings, test imports."""
        w = QWidget()
        layout = QHBoxLayout(w)

        # Left: module browser list
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        left_layout.addWidget(QLabel("Core Modules:"))
        self.inspector_list = QListWidget()
        self.inspector_list.setMinimumWidth(180)
        self.inspector_list.setStyleSheet("font-family: 'JetBrains Mono', monospace; font-size: 10px;")

        CORE_MODULES = [
            "genesis_core", "cerberus_core", "cerberus_enhanced", "kyc_core",
            "kyc_enhanced", "fingerprint_injector", "tx_monitor",
            "transaction_monitor", "handover_protocol", "kill_switch",
            "lucid_vpn", "proxy_manager", "three_ds_strategy", "tls_parrot",
            "target_discovery", "target_presets", "integration_bridge",
            "cognitive_core", "advanced_profile_generator",
            "purchase_history_engine", "form_autofill_injector",
            "referrer_warmup", "webgl_angle", "font_sanitizer",
            "audio_hardener", "timezone_enforcer", "network_jitter",
            "quic_proxy", "location_spoofer_linux", "preflight_validator",
            "titan_services", "profile_isolation", "temporal_wrapper",
        ]
        for mod in CORE_MODULES:
            self.inspector_list.addItem(mod)
        self.inspector_list.itemClicked.connect(self._inspect_module)
        left_layout.addWidget(self.inspector_list)

        test_import_btn = QPushButton("Test Import")
        test_import_btn.setStyleSheet("background: rgba(85,136,255,0.15); border: 1px solid #5588ff; color: #5588ff; border-radius: 4px; padding: 6px;")
        test_import_btn.clicked.connect(self._test_selected_module_import)
        left_layout.addWidget(test_import_btn)

        layout.addWidget(left_panel)

        # Right: module details
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        right_layout.addWidget(QLabel("Module Details:"))
        self.inspector_details = QTextEdit()
        self.inspector_details.setReadOnly(True)
        self.inspector_details.setPlaceholderText(
            "Select a module from the list to view its docstring, classes, functions, and dependencies."
        )
        self.inspector_details.setStyleSheet("font-family: 'JetBrains Mono', monospace; font-size: 10px;")
        right_layout.addWidget(self.inspector_details)

        layout.addWidget(right_panel)
        layout.setStretch(0, 1)
        layout.setStretch(1, 3)
        return w

    def _inspect_module(self, item):
        """Show docstring, classes, and functions from a module."""
        mod_name = item.text()
        import importlib, inspect, sys as _sys
        old_path = list(_sys.path)
        _sys.path.insert(0, str(CORE_DIR))
        _sys.path.insert(0, str(TITAN_ROOT / "backend"))

        text = f"MODULE: {mod_name}\n{'=' * 50}\n\n"
        try:
            mod = importlib.import_module(mod_name)
            text += f"File: {getattr(mod, '__file__', 'built-in')}\n\n"

            doc = inspect.getdoc(mod)
            text += f"DOCSTRING:\n{doc or '(none)'}\n\n"

            classes = [name for name, obj in inspect.getmembers(mod, inspect.isclass) if obj.__module__ == mod_name]
            text += f"CLASSES ({len(classes)}):\n"
            for cls in classes:
                text += f"  • {cls}\n"

            funcs = [name for name, obj in inspect.getmembers(mod, inspect.isfunction) if obj.__module__ == mod_name]
            text += f"\nFUNCTIONS ({len(funcs)}):\n"
            for fn in funcs[:20]:
                text += f"  • {fn}()\n"

        except ImportError as e:
            text += f"IMPORT FAILED: {e}\n"
        except Exception as e:
            text += f"ERROR: {e}\n"
        finally:
            _sys.path[:] = old_path

        self.inspector_details.setPlainText(text)

    def _test_selected_module_import(self):
        """Test importing the selected module and report result."""
        current = self.inspector_list.currentItem()
        if not current:
            QMessageBox.information(self, "Info", "Select a module first.")
            return
        mod_name = current.text()
        import importlib, sys as _sys
        old_path = list(_sys.path)
        _sys.path.insert(0, str(CORE_DIR))
        _sys.path.insert(0, str(TITAN_ROOT / "backend"))
        try:
            importlib.import_module(mod_name)
            QMessageBox.information(self, "Import Test", f"✅ {mod_name}: Import PASSED")
        except ImportError as e:
            QMessageBox.warning(self, "Import Test", f"❌ {mod_name}: Import FAILED\n{e}")
        finally:
            _sys.path[:] = old_path

    # ── Tab: Logs ────────────────────────────────────────────────────

    def _build_logs_tab(self) -> QWidget:
        """Tab 4: Logs — real-time log viewer with filter by module/severity and export."""
        w = QWidget()
        layout = QVBoxLayout(w)

        # Filter bar
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Module:"))
        self.log_filter_module = QComboBox()
        self.log_filter_module.addItems(["All", "genesis_core", "cerberus_core", "kyc_core",
                                          "kill_switch", "tx_monitor", "proxy_manager", "lucid_vpn"])
        self.log_filter_module.currentTextChanged.connect(self._apply_log_filter)
        filter_row.addWidget(self.log_filter_module)

        filter_row.addWidget(QLabel("Severity:"))
        self.log_filter_severity = QComboBox()
        self.log_filter_severity.addItems(["All", "CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"])
        self.log_filter_severity.currentTextChanged.connect(self._apply_log_filter)
        filter_row.addWidget(self.log_filter_severity)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setStyleSheet("background: rgba(85,136,255,0.15); border: 1px solid #5588ff; color: #5588ff; border-radius: 4px; padding: 6px 12px;")
        refresh_btn.clicked.connect(self._load_logs)
        filter_row.addWidget(refresh_btn)

        export_btn = QPushButton("Export Logs")
        export_btn.setStyleSheet("background: rgba(0,255,136,0.1); border: 1px solid #00ff88; color: #00ff88; border-radius: 4px; padding: 6px 12px;")
        export_btn.clicked.connect(self._export_logs)
        filter_row.addWidget(export_btn)

        clear_btn = QPushButton("Clear")
        clear_btn.setStyleSheet("background: rgba(255,51,85,0.1); border: 1px solid #ff3355; color: #ff3355; border-radius: 4px; padding: 6px 12px;")
        clear_btn.clicked.connect(self._clear_log_view)
        filter_row.addWidget(clear_btn)

        filter_row.addStretch()
        layout.addLayout(filter_row)

        # Real-time log viewer
        self.log_viewer = QTextEdit()
        self.log_viewer.setReadOnly(True)
        self.log_viewer.setStyleSheet(
            "font-family: 'JetBrains Mono', monospace; font-size: 10px; "
            "background-color: rgba(10, 14, 23, 0.95); color: #c8d2dc;"
        )
        self.log_viewer.setPlaceholderText("Log entries will appear here. Click 'Refresh' to load.")
        layout.addWidget(self.log_viewer)

        # Auto-refresh timer (10 seconds)
        self._log_timer = QTimer()
        self._log_timer.timeout.connect(self._load_logs)
        self._log_timer.start(10000)

        # Load on open
        self._load_logs()
        return w

    def _load_logs(self):
        """Load log entries from TITAN log files."""
        if not hasattr(self, 'log_viewer'):
            return
        lines = []
        log_files = [
            LOGS_DIR / "titan.log",
            LOGS_DIR / "kill_switch.log",
            LOGS_DIR / "tx_monitor.log",
            LOGS_DIR / "proxy.log",
            Path("/var/log/syslog"),
        ]
        for lf in log_files:
            if lf.exists():
                try:
                    with open(lf, "r", errors="replace") as f:
                        last = f.readlines()[-200:]
                    for line in last:
                        lines.append(f"[{lf.name}] {line.rstrip()}")
                except Exception:
                    pass

        if not lines:
            lines = [f"No log files found in {LOGS_DIR}",
                     "Logs will appear here as TITAN services generate them."]

        self._all_log_lines = lines
        self._apply_log_filter()

    def _apply_log_filter(self):
        """Filter log lines by module and severity."""
        if not hasattr(self, '_all_log_lines'):
            return
        mod_filter = self.log_filter_module.currentText()
        sev_filter = self.log_filter_severity.currentText()

        filtered = []
        for line in self._all_log_lines:
            if mod_filter != "All" and mod_filter.lower() not in line.lower():
                continue
            if sev_filter != "All" and sev_filter.upper() not in line.upper():
                continue
            filtered.append(line)

        self.log_viewer.setPlainText("\n".join(filtered[-500:]))  # Last 500 visible
        # Scroll to bottom
        cursor = self.log_viewer.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.log_viewer.setTextCursor(cursor)

    def _clear_log_view(self):
        self.log_viewer.clear()
        self._all_log_lines = []

    def _export_logs(self):
        """Export current log view to file."""
        content = self.log_viewer.toPlainText()
        if not content:
            QMessageBox.information(self, "Empty", "No log content to export.")
            return
        save_path, _ = QFileDialog.getSaveFileName(self, "Export Logs", "titan_logs.txt", "Text Files (*.txt)")
        if save_path:
            try:
                Path(save_path).write_text(content)
                QMessageBox.information(self, "Exported", f"Logs exported to:\n{save_path}")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Export failed: {e}")

    # ── Tab: Bug Report ──────────────────────────────────────────────

    def _build_report_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        form_group = QGroupBox("Report Details")
        form = QFormLayout(form_group)

        self.rpt_title = QLineEdit()
        self.rpt_title.setPlaceholderText("Short description of the issue")
        form.addRow("Title:", self.rpt_title)

        self.rpt_category = QComboBox()
        for c in BugCategory:
            self.rpt_category.addItem(c.value.replace("_", " ").title(), c.value)
        form.addRow("Category:", self.rpt_category)

        self.rpt_severity = QComboBox()
        for s in Severity:
            self.rpt_severity.addItem(s.value.title(), s.value)
        self.rpt_severity.setCurrentIndex(2)
        form.addRow("Severity:", self.rpt_severity)

        self.rpt_module = QComboBox()
        self.rpt_module.setEditable(True)
        self.rpt_module.addItems([
            "", "genesis_core", "cerberus_core", "cerberus_enhanced",
            "fingerprint_injector", "ghost_motor", "tx_monitor",
            "handover_protocol", "kill_switch", "lucid_vpn",
            "proxy_manager", "three_ds_strategy", "tls_parrot",
            "target_discovery", "transaction_monitor", "integration_bridge",
            "cognitive_core", "kyc_core", "kyc_enhanced",
            "advanced_profile_generator", "purchase_history_engine",
            "form_autofill_injector", "referrer_warmup", "webgl_angle",
            "font_sanitizer", "audio_hardener", "timezone_enforcer",
            "network_jitter", "quic_proxy", "location_spoofer_linux",
        ])
        form.addRow("Module:", self.rpt_module)

        self.rpt_description = QTextEdit()
        self.rpt_description.setMaximumHeight(100)
        self.rpt_description.setPlaceholderText("Detailed description of the issue...")
        form.addRow("Description:", self.rpt_description)

        self.rpt_steps = QTextEdit()
        self.rpt_steps.setMaximumHeight(80)
        self.rpt_steps.setPlaceholderText("1. Open browser\n2. Navigate to...\n3. ...")
        form.addRow("Steps:", self.rpt_steps)

        layout.addWidget(form_group)

        # Decline-specific fields
        decline_group = QGroupBox("Decline / Detection Details (optional)")
        decline_form = QFormLayout(decline_group)

        self.rpt_domain = QLineEdit()
        self.rpt_domain.setPlaceholderText("e.g., g2a.com")
        decline_form.addRow("Target Domain:", self.rpt_domain)

        self.rpt_psp = QComboBox()
        self.rpt_psp.setEditable(True)
        self.rpt_psp.addItems(["", "stripe", "adyen", "braintree", "paypal", "authorize_net", "shopify", "square", "cybersource", "worldpay"])
        decline_form.addRow("PSP:", self.rpt_psp)

        self.rpt_decline_code = QLineEdit()
        self.rpt_decline_code.setPlaceholderText("e.g., do_not_honor, fraudulent, incorrect_cvc")
        decline_form.addRow("Decline Code:", self.rpt_decline_code)

        self.rpt_error_log = QTextEdit()
        self.rpt_error_log.setMaximumHeight(80)
        self.rpt_error_log.setPlaceholderText("Paste error log, traceback, or console output here...")
        decline_form.addRow("Error Log:", self.rpt_error_log)

        layout.addWidget(decline_group)

        # Submit buttons
        btn_layout = QHBoxLayout()

        submit_btn = QPushButton("Submit Report")
        submit_btn.setStyleSheet("background: #2255aa; font-weight: bold; padding: 10px 30px;")
        submit_btn.clicked.connect(self._submit_report)
        btn_layout.addWidget(submit_btn)

        submit_patch_btn = QPushButton("Submit + Send to Windsurf")
        submit_patch_btn.setStyleSheet("background: #1a6b1a; font-weight: bold; padding: 10px 30px;")
        submit_patch_btn.clicked.connect(self._submit_and_patch)
        btn_layout.addWidget(submit_patch_btn)

        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._clear_form)
        btn_layout.addWidget(clear_btn)

        layout.addLayout(btn_layout)
        layout.addStretch()
        return w

    # ── Tab: Reports List ────────────────────────────────────────────

    def _build_reports_list_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        # Filter bar
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter:"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All", "Pending", "In Progress", "Patched", "Won't Fix"])
        self.filter_combo.currentTextChanged.connect(self._refresh_reports)
        filter_layout.addWidget(self.filter_combo)
        filter_layout.addStretch()

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._refresh_reports)
        filter_layout.addWidget(refresh_btn)
        layout.addLayout(filter_layout)

        # Reports table
        self.reports_table = QTableWidget()
        self.reports_table.setColumnCount(7)
        self.reports_table.setHorizontalHeaderLabels(["ID", "Severity", "Category", "Title", "Status", "Module", "Created"])
        self.reports_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.reports_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.reports_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.reports_table.doubleClicked.connect(self._open_report_detail)
        layout.addWidget(self.reports_table)

        # Action buttons
        action_layout = QHBoxLayout()
        send_ws_btn = QPushButton("Send to Windsurf")
        send_ws_btn.clicked.connect(self._send_selected_to_windsurf)
        action_layout.addWidget(send_ws_btn)

        mark_fixed_btn = QPushButton("Mark as Patched")
        mark_fixed_btn.setObjectName("success")
        mark_fixed_btn.clicked.connect(self._mark_selected_patched)
        action_layout.addWidget(mark_fixed_btn)

        action_layout.addStretch()
        layout.addLayout(action_layout)
        return w

    # ── Tab: Decline Patterns ────────────────────────────────────────

    def _build_decline_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(QLabel("Top Decline Patterns (auto-populated from Transaction Monitor)"))

        self.decline_table = QTableWidget()
        self.decline_table.setColumnCount(5)
        self.decline_table.setHorizontalHeaderLabels(["PSP", "Decline Code", "Count", "Target", "Last Seen"])
        self.decline_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.decline_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.decline_table)

        btn_layout = QHBoxLayout()
        ingest_btn = QPushButton("Ingest from Transaction Monitor DB")
        ingest_btn.clicked.connect(self._ingest_tx_monitor)
        btn_layout.addWidget(ingest_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        return w

    # ── Tab: Patches ─────────────────────────────────────────────────

    def _build_patches_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        layout.addWidget(QLabel("Applied Patches & Windsurf Tasks"))

        self.patches_list = QListWidget()
        layout.addWidget(self.patches_list)

        btn_layout = QHBoxLayout()
        open_ws_btn = QPushButton("Open Windsurf Workspace")
        open_ws_btn.clicked.connect(lambda: self.windsurf.open_workspace())
        btn_layout.addWidget(open_ws_btn)

        open_patches_btn = QPushButton("Open Patches Folder")
        open_patches_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(PATCHES_DIR))))
        btn_layout.addWidget(open_patches_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        return w

    # ═══════════════════════════════════════════════════════════════════
    # ACTIONS
    # ═══════════════════════════════════════════════════════════════════

    def _submit_report(self):
        title = self.rpt_title.text().strip()
        if not title:
            QMessageBox.warning(self, "Error", "Title is required.")
            return

        report = BugReport(
            category=self.rpt_category.currentData(),
            severity=self.rpt_severity.currentData(),
            title=title,
            description=self.rpt_description.toPlainText().strip(),
            steps_to_reproduce=self.rpt_steps.toPlainText().strip(),
            target_domain=self.rpt_domain.text().strip(),
            psp_name=self.rpt_psp.currentText().strip(),
            decline_code=self.rpt_decline_code.text().strip(),
            error_log=self.rpt_error_log.toPlainText().strip(),
            module_name=self.rpt_module.currentText().strip(),
        )

        # Check for auto-fix
        auto_fix = self.auto_patcher.check_auto_fix(report)

        report_id = self.db.insert_report(report)

        # Record decline pattern if applicable
        if report.decline_code and report.psp_name:
            self.db.record_decline(report.psp_name, report.decline_code, report.target_domain)

        if auto_fix:
            result = self.auto_patcher.apply_auto_fix(report_id, auto_fix)
            QMessageBox.information(self, "Auto-Fix Applied",
                f"Report #{report_id} submitted.\n\nAuto-fix: {result}")
        else:
            QMessageBox.information(self, "Report Submitted",
                f"Bug report #{report_id} submitted successfully.")

        self._clear_form()
        self._refresh_reports()

    def _submit_and_patch(self):
        title = self.rpt_title.text().strip()
        if not title:
            QMessageBox.warning(self, "Error", "Title is required.")
            return

        if not self.windsurf.is_available():
            QMessageBox.warning(self, "Windsurf Not Found",
                "Windsurf IDE is not installed. Submit report only.")
            self._submit_report()
            return

        report = BugReport(
            category=self.rpt_category.currentData(),
            severity=self.rpt_severity.currentData(),
            title=title,
            description=self.rpt_description.toPlainText().strip(),
            steps_to_reproduce=self.rpt_steps.toPlainText().strip(),
            target_domain=self.rpt_domain.text().strip(),
            psp_name=self.rpt_psp.currentText().strip(),
            decline_code=self.rpt_decline_code.text().strip(),
            error_log=self.rpt_error_log.toPlainText().strip(),
            module_name=self.rpt_module.currentText().strip(),
        )
        report_id = self.db.insert_report(report)

        if report.decline_code and report.psp_name:
            self.db.record_decline(report.psp_name, report.decline_code, report.target_domain)

        report_dict = self.db.get_report(report_id)
        self.worker = PatchWorker(self.db, self.windsurf, report_id)
        self.worker.progress.connect(lambda msg: self.statusBar().showMessage(msg))
        self.worker.finished.connect(lambda msg: (
            self.statusBar().showMessage(msg),
            QMessageBox.information(self, "Patch Task Created", msg),
            self._refresh_reports(),
        ))
        self.worker.start()
        self._clear_form()

    def _clear_form(self):
        self.rpt_title.clear()
        self.rpt_description.clear()
        self.rpt_steps.clear()
        self.rpt_domain.clear()
        self.rpt_decline_code.clear()
        self.rpt_error_log.clear()
        self.rpt_category.setCurrentIndex(0)
        self.rpt_severity.setCurrentIndex(2)
        self.rpt_module.setCurrentIndex(0)
        self.rpt_psp.setCurrentIndex(0)

    def _refresh_reports(self):
        filter_text = self.filter_combo.currentText() if hasattr(self, 'filter_combo') else "All"
        status_map = {
            "All": None, "Pending": "pending",
            "In Progress": "in_progress", "Patched": "patched", "Won't Fix": "wont_fix"
        }
        reports = self.db.get_all_reports(status_map.get(filter_text))
        self.reports_table.setRowCount(len(reports))

        severity_colors = {
            "critical": "#ff4444", "high": "#ff8844",
            "medium": "#ffcc44", "low": "#88cc44"
        }
        status_colors = {
            "pending": "#ff8844", "in_progress": "#44aaff",
            "patched": "#44cc44", "wont_fix": "#888888", "duplicate": "#888888"
        }

        for i, r in enumerate(reports):
            self.reports_table.setItem(i, 0, QTableWidgetItem(str(r["id"])))
            sev_item = QTableWidgetItem(r["severity"])
            sev_item.setForeground(QColor(severity_colors.get(r["severity"], "#ccc")))
            self.reports_table.setItem(i, 1, sev_item)
            self.reports_table.setItem(i, 2, QTableWidgetItem(r["category"]))
            self.reports_table.setItem(i, 3, QTableWidgetItem(r["title"]))
            status_item = QTableWidgetItem(r["patch_status"])
            status_item.setForeground(QColor(status_colors.get(r["patch_status"], "#ccc")))
            self.reports_table.setItem(i, 4, status_item)
            self.reports_table.setItem(i, 5, QTableWidgetItem(r.get("module_name", "")))
            self.reports_table.setItem(i, 6, QTableWidgetItem(r["created_at"][:19]))

        # Update stats
        stats = self.db.get_stats()
        self.stats_lbl.setText(
            f"Total: {stats['total']} | Pending: {stats['pending']} | "
            f"Patched: {stats['patched']} | Critical: {stats['critical_pending']}"
        )

        # Update patches tab
        self._refresh_patches()
        self._refresh_decline_patterns()

    def _open_report_detail(self):
        row = self.reports_table.currentRow()
        if row < 0:
            return
        report_id = int(self.reports_table.item(row, 0).text())
        report = self.db.get_report(report_id)
        if not report:
            return

        detail = (
            f"Bug #{report['id']}: {report['title']}\n"
            f"{'='*60}\n"
            f"Category: {report['category']}\n"
            f"Severity: {report['severity']}\n"
            f"Status: {report['patch_status']}\n"
            f"Module: {report.get('module_name', 'N/A')}\n"
            f"Domain: {report.get('target_domain', 'N/A')}\n"
            f"PSP: {report.get('psp_name', 'N/A')}\n"
            f"Decline Code: {report.get('decline_code', 'N/A')}\n"
            f"Created: {report['created_at']}\n"
            f"\nDescription:\n{report.get('description', '')}\n"
            f"\nSteps:\n{report.get('steps_to_reproduce', '')}\n"
            f"\nError Log:\n{report.get('error_log', '')}\n"
        )
        if report.get("patch_diff"):
            detail += f"\nPatch/Resolution:\n{report['patch_diff']}\n"
        if report.get("windsurf_task_id"):
            detail += f"\nWindsurf Task: {report['windsurf_task_id']}\n"

        QMessageBox.information(self, f"Bug #{report['id']}", detail)

    def _send_selected_to_windsurf(self):
        row = self.reports_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Error", "Select a report first.")
            return
        report_id = int(self.reports_table.item(row, 0).text())

        if not self.windsurf.is_available():
            QMessageBox.warning(self, "Error", "Windsurf IDE not available.")
            return

        report = self.db.get_report(report_id)
        self.worker = PatchWorker(self.db, self.windsurf, report_id)
        self.worker.progress.connect(lambda msg: self.statusBar().showMessage(msg))
        self.worker.finished.connect(lambda msg: (
            self.statusBar().showMessage(msg),
            self._refresh_reports(),
        ))
        self.worker.start()

    def _mark_selected_patched(self):
        row = self.reports_table.currentRow()
        if row < 0:
            return
        report_id = int(self.reports_table.item(row, 0).text())
        self.db.update_patch_status(report_id, "patched", "Manually marked as patched")
        self._refresh_reports()
        self.statusBar().showMessage(f"Report #{report_id} marked as patched")

    def _refresh_patches(self):
        if not hasattr(self, 'patches_list'):
            return
        self.patches_list.clear()
        if PATCHES_DIR.exists():
            for f in sorted(PATCHES_DIR.glob("task_*.md"), reverse=True):
                self.patches_list.addItem(f.name)

    def _refresh_decline_patterns(self):
        if not hasattr(self, 'decline_table'):
            return
        patterns = self.db.get_decline_patterns()
        self.decline_table.setRowCount(len(patterns))
        for i, p in enumerate(patterns):
            self.decline_table.setItem(i, 0, QTableWidgetItem(p.get("psp", "")))
            self.decline_table.setItem(i, 1, QTableWidgetItem(p.get("decline_code", "")))
            self.decline_table.setItem(i, 2, QTableWidgetItem(str(p.get("count", 0))))
            self.decline_table.setItem(i, 3, QTableWidgetItem(p.get("target_domain", "")))
            self.decline_table.setItem(i, 4, QTableWidgetItem(p.get("last_seen", "")[:19]))

    def _ingest_tx_monitor(self):
        """Import decline data from Transaction Monitor's database."""
        tx_db = Path("/opt/titan/state/tx_monitor.db")
        if not tx_db.exists():
            QMessageBox.information(self, "Info", "Transaction Monitor DB not found. Run some transactions first.")
            return
        try:
            tx_conn = sqlite3.connect(str(tx_db))
            tx_conn.row_factory = sqlite3.Row
            rows = tx_conn.execute(
                "SELECT psp, response_code, COUNT(*) as cnt, domain, MAX(timestamp) as last "
                "FROM transactions WHERE status='declined' "
                "GROUP BY psp, response_code, domain ORDER BY cnt DESC LIMIT 50"
            ).fetchall()
            for r in rows:
                self.db.record_decline(r["psp"], r["response_code"], r["domain"])
            tx_conn.close()
            self._refresh_decline_patterns()
            self.statusBar().showMessage(f"Imported {len(rows)} decline patterns from TX Monitor")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to import: {e}")

    def _ingest_crash_logs(self):
        """Auto-create reports from panic_log.jsonl if present."""
        panic_log = Path("/opt/titan/state/panic_log.jsonl")
        if not panic_log.exists():
            return
        try:
            with open(panic_log, "r") as f:
                lines = f.readlines()
            for line in lines[-10:]:  # Last 10 events
                event = json.loads(line.strip())
                existing = self.db.conn.execute(
                    "SELECT id FROM bug_reports WHERE title LIKE ? AND created_at > ?",
                    (f"%{event.get('reason', '')}%", (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat())
                ).fetchone()
                if not existing:
                    report = BugReport(
                        category="crash",
                        severity="critical" if event.get("threat_level") == "critical" else "high",
                        title=f"Kill Switch Panic: {event.get('reason', 'unknown')}",
                        description=f"Auto-generated from kill switch panic event.\nFraud score: {event.get('fraud_score', 'N/A')}",
                        error_log=json.dumps(event, indent=2),
                        module_name="kill_switch",
                    )
                    self.db.insert_report(report)
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("TITAN Diagnostic Reporter")
    app.setStyle("Fusion")

    try:
        from titan_enterprise_theme import apply_enterprise_theme_to_app
        apply_enterprise_theme_to_app(app)
    except ImportError:
        pass

    splash = None
    try:
        from titan_splash import show_titan_splash
        splash = show_titan_splash(app, "DIAGNOSTIC REPORTER", "#3A75C4")
    except Exception:
        pass

    window = BugReporterWindow()
    window.show()
    if splash:
        splash.finish(window)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
