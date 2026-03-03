#!/usr/bin/env python3
"""
TITAN X LAUNCHER — Responsive Entry Point
==========================================
11 apps, adaptive grid, 117 core modules — zero orphans.
Scales from mobile (800x480) to 4K (3840x2160).

App Structure (Titan X):
  Row 1: Operations Center | Intelligence Center | Network Center
  Row 2: KYC Studio | Admin Panel | Settings
  Row 3: Profile Forge | Card Validator | Browser Launch
  Row 4: Genesis AppX | Bug Reporter
"""

import sys
import os
import subprocess
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QGridLayout, QScrollArea,
    QMessageBox, QSizePolicy, QToolTip
)
from PyQt6.QtCore import Qt, QTimer, QProcess, QSize
from PyQt6.QtGui import QFont, QColor, QPalette, QPainter, QLinearGradient

# Add core to path for health checks
sys.path.insert(0, str(Path(__file__).parent.parent / "core"))

APPS_DIR = Path(__file__).parent
ACCENT = "#00d4ff"
BG_DARK = "#0a0e17"
BG_CARD = "#111827"
BG_HOVER = "#1a2332"
TEXT_PRIMARY = "#e2e8f0"
TEXT_SECONDARY = "#64748b"
GREEN = "#22c55e"
YELLOW = "#eab308"
RED = "#ef4444"
PURPLE = "#a855f7"

FIRST_RUN_FLAG = Path.home() / ".titan" / "first_run_done"

# ── App definitions (plain English for zero-code users) ──────────────
APP_DEFS = [
    {
        "title": "Operations",
        "plain": "Run a full operation from start to finish",
        "detail": "Pick a target, select a card, generate identity,\nforge profile, and launch browser — all in one place.",
        "accent": "#00d4ff",
        "icon": "\u2699\ufe0f",
        "script": "titan_operations.py",
        "tooltip": "Your main workspace. Start here for any new operation.",
    },
    {
        "title": "Intelligence",
        "plain": "AI-powered analysis and strategy",
        "detail": "Ask the AI copilot questions, view 3DS strategies,\nanalyze detections, and research targets.",
        "accent": "#a855f7",
        "icon": "\U0001f9e0",
        "script": "titan_intelligence.py",
        "tooltip": "Get AI recommendations and analyze past results.",
    },
    {
        "title": "Network",
        "plain": "VPN, proxy, and network protection",
        "detail": "Connect to Mullvad VPN, manage proxies,\nmonitor network forensics, and verify your IP.",
        "accent": "#22c55e",
        "icon": "\U0001f512",
        "script": "titan_network.py",
        "tooltip": "Always connect VPN before starting any operation.",
    },
    {
        "title": "KYC Studio",
        "plain": "Identity document and selfie tools",
        "detail": "Camera bypass, document generation,\nvoice synthesis, and liveness checks.",
        "accent": "#f97316",
        "icon": "\U0001f4f7",
        "script": "app_kyc.py",
        "tooltip": "Use when a target requires identity verification.",
    },
    {
        "title": "Admin",
        "plain": "System management and services",
        "detail": "Control background services, view logs,\nmanage automation rules, and system health.",
        "accent": "#f59e0b",
        "icon": "\U0001f6e0\ufe0f",
        "script": "titan_admin.py",
        "tooltip": "Check service health and manage system settings.",
    },
    {
        "title": "Settings",
        "plain": "Configure all tools and API keys",
        "detail": "Set up Mullvad VPN, Ollama AI, Redis,\nproxy settings, and browser preferences.",
        "accent": "#6366f1",
        "icon": "\U0001f527",
        "script": "app_settings.py",
        "tooltip": "First-time setup: enter your API keys and preferences here.",
    },
    {
        "title": "Profile Forge",
        "plain": "Create realistic browser profiles",
        "detail": "Generate personas, build Chrome profiles\nwith history, cookies, and realistic aging.",
        "accent": "#06b6d4",
        "icon": "\U0001f528",
        "script": "app_profile_forge.py",
        "tooltip": "Create believable browser identities for operations.",
    },
    {
        "title": "Card Validator",
        "plain": "Check and grade payment cards",
        "detail": "Validate BINs, check AVS, grade card quality,\nand decode decline reasons.",
        "accent": "#eab308",
        "icon": "\U0001f4b3",
        "script": "app_card_validator.py",
        "tooltip": "Validate cards before using them in operations.",
    },
    {
        "title": "Browser Launch",
        "plain": "Launch browsers with full protection",
        "detail": "Pre-flight checks, Camoufox launch,\nlive transaction monitor, and auto-handover.",
        "accent": "#22c55e",
        "icon": "\U0001f680",
        "script": "app_browser_launch.py",
        "tooltip": "Launch a protected browser session for checkout.",
    },
    {
        "title": "Genesis AppX",
        "plain": "MultiLogin 6 browser manager",
        "detail": "Manage ML6 profiles, Golden Ticket forge,\ntarget-aware profile creation.",
        "accent": "#10b981",
        "icon": "\U0001f48e",
        "script": "../../../tools/multilogin6/genesis_appx/launch_genesis_appx.sh",
        "tooltip": "Alternative browser engine using MultiLogin 6.",
    },
    {
        "title": "Bug Reporter",
        "plain": "Report issues and track fixes",
        "detail": "Log decline patterns, auto-patch known issues,\nand track bug resolution history.",
        "accent": "#5588ff",
        "icon": "\U0001f41b",
        "script": "app_bug_reporter.py",
        "tooltip": "Report problems so they get fixed automatically.",
    },
]


class AppCard(QFrame):
    """Clickable app launcher card — responsive sizing."""

    def __init__(self, app_def: dict, parent=None):
        super().__init__(parent)
        self.script = app_def["script"]
        self.accent = app_def["accent"]

        self.setMinimumSize(260, 220)
        self.setMaximumSize(400, 320)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(app_def.get("tooltip", ""))
        self.setStyleSheet(f"""
            AppCard {{
                background: {BG_CARD};
                border: 1px solid #1e293b;
                border-radius: 14px;
            }}
            AppCard:hover {{
                background: {BG_HOVER};
                border: 1px solid {self.accent};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)

        # Top row: icon + title + status dot
        top = QHBoxLayout()
        top.setSpacing(10)

        icon = QLabel(app_def["icon"])
        icon.setFont(QFont("Noto Color Emoji", 28))
        icon.setFixedSize(48, 48)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top.addWidget(icon)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_lbl = QLabel(app_def["title"])
        title_lbl.setFont(QFont("Noto Sans", 14, QFont.Weight.Bold))
        title_lbl.setStyleSheet(f"color: {self.accent};")
        title_col.addWidget(title_lbl)

        plain_lbl = QLabel(app_def["plain"])
        plain_lbl.setFont(QFont("Noto Sans", 9))
        plain_lbl.setStyleSheet(f"color: {TEXT_SECONDARY};")
        plain_lbl.setWordWrap(True)
        title_col.addWidget(plain_lbl)
        top.addLayout(title_col, 1)

        # Status badge
        self.status_dot = QLabel("\u25cf")
        self.status_dot.setFont(QFont("Noto Sans", 12))
        self.status_dot.setStyleSheet(f"color: {TEXT_SECONDARY};")
        self.status_dot.setToolTip("Checking...")
        self.status_dot.setFixedSize(20, 20)
        self.status_dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top.addWidget(self.status_dot)

        layout.addLayout(top)

        # Description
        desc_lbl = QLabel(app_def["detail"])
        desc_lbl.setFont(QFont("Noto Sans", 9))
        desc_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft)
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; padding: 4px 0;")
        layout.addWidget(desc_lbl)

        layout.addStretch()

        # Launch button — large touch target (48px min)
        btn = QPushButton("OPEN")
        btn.setFont(QFont("Noto Sans", 11, QFont.Weight.Bold))
        btn.setMinimumHeight(48)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setToolTip(f"Open {app_def['title']}")
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {self.accent};
                color: #0a0e17;
                border: none;
                border-radius: 10px;
                font-weight: bold;
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                background: {self.accent}cc;
            }}
            QPushButton:pressed {{
                background: {self.accent}88;
            }}
        """)
        btn.clicked.connect(self._launch)
        layout.addWidget(btn)

    def set_ready(self, ready: bool):
        """Set the status badge color."""
        if ready:
            self.status_dot.setStyleSheet(f"color: {GREEN};")
            self.status_dot.setToolTip("Ready")
        else:
            self.status_dot.setStyleSheet(f"color: {YELLOW};")
            self.status_dot.setToolTip("Module available")

    def _launch(self):
        script_path = str(APPS_DIR / self.script)

        # V9.2 FIX: Pass DISPLAY + XAUTHORITY so child processes can connect to X
        env = QProcess.systemEnvironment()
        display = os.environ.get("DISPLAY", ":10")
        xauth = os.environ.get("XAUTHORITY", os.path.expanduser("~/.Xauthority"))
        pythonpath = ":".join([
            str(APPS_DIR.parent / "core"),
            str(APPS_DIR),
            str(APPS_DIR.parent),
            "/opt/titan",
        ])
        # Update or insert env vars
        env_dict = {}
        for item in env:
            if "=" in item:
                k, v = item.split("=", 1)
                env_dict[k] = v
        env_dict["DISPLAY"] = display
        env_dict["XAUTHORITY"] = xauth
        env_dict["PYTHONPATH"] = pythonpath
        env_dict["QT_QPA_PLATFORM"] = "xcb"
        env_list = [f"{k}={v}" for k, v in env_dict.items()]

        proc = QProcess()
        proc.setEnvironment(env_list)

        if self.script.endswith(".sh"):
            proc.startDetached("bash", [script_path])
        elif os.path.exists(script_path):
            proc.startDetached("python3", [script_path])
        else:
            proc.startDetached(sys.executable, [script_path])

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._launch()


class HealthBar(QFrame):
    """Compact health status bar that wraps on small screens."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            HealthBar {{
                background: {BG_CARD};
                border: 1px solid #1e293b;
                border-radius: 10px;
            }}
        """)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(12, 6, 12, 6)
        self._layout.setSpacing(4)
        self.indicators = {}

    def add_indicator(self, key: str, label: str):
        frame = QFrame()
        h = QHBoxLayout(frame)
        h.setContentsMargins(6, 2, 6, 2)
        h.setSpacing(4)

        dot = QLabel("\u25cf")
        dot.setFont(QFont("Noto Sans", 7))
        dot.setStyleSheet(f"color: {TEXT_SECONDARY};")
        h.addWidget(dot)

        lbl = QLabel(label)
        lbl.setFont(QFont("Noto Sans", 9))
        lbl.setStyleSheet(f"color: {TEXT_SECONDARY};")
        h.addWidget(lbl)

        val = QLabel("...")
        val.setFont(QFont("DejaVu Sans Mono", 9))
        val.setStyleSheet(f"color: {TEXT_PRIMARY};")
        h.addWidget(val)

        self.indicators[key] = {"dot": dot, "value": val}
        self._layout.addWidget(frame)

    def set_status(self, key: str, text: str, color: str = GREEN):
        if key in self.indicators:
            self.indicators[key]["value"].setText(text)
            self.indicators[key]["value"].setStyleSheet(f"color: {color};")
            self.indicators[key]["dot"].setStyleSheet(f"color: {color};")


class TitanLauncher(QMainWindow):
    """
    TITAN X Launcher — 11 apps, adaptive grid, 117 modules.
    Responsive from 800x480 (mobile) to 4K.
    """

    def __init__(self):
        super().__init__()
        self.cards = []
        self.init_ui()
        self.apply_theme()
        QTimer.singleShot(500, self._check_health)
        QTimer.singleShot(1000, self._check_first_run)

    def init_ui(self):
        self.setWindowTitle("TITAN X")
        try:
            from titan_icon import set_titan_icon
            set_titan_icon(self, ACCENT)
        except Exception:
            pass

        # Responsive: min 800x480, start at 1100x900
        self.setMinimumSize(800, 480)
        self.resize(1100, 900)

        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Scroll area for the entire content (mobile-friendly)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{ background: {BG_DARK}; border: none; }}
            QScrollBar:vertical {{
                background: {BG_DARK}; width: 8px; border: none;
            }}
            QScrollBar::handle:vertical {{
                background: #1e293b; border-radius: 4px; min-height: 40px;
            }}
            QScrollBar::handle:vertical:hover {{ background: {ACCENT}44; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """)

        content = QWidget()
        self.content_layout = QVBoxLayout(content)
        self.content_layout.setContentsMargins(20, 16, 20, 16)
        self.content_layout.setSpacing(14)

        # ── Header ──
        header = QLabel("TITAN X")
        header.setFont(QFont("Noto Sans", 26, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet(f"color: {ACCENT};")
        self.content_layout.addWidget(header)

        subtitle = QLabel("V10.0  \u2014  117 MODULES  \u00b7  11 APPS  \u00b7  3 BRIDGES")
        subtitle.setFont(QFont("DejaVu Sans Mono", 10))
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet(f"color: {TEXT_SECONDARY}; letter-spacing: 2px;")
        subtitle.setWordWrap(True)
        self.content_layout.addWidget(subtitle)

        # ── Quick Start banner (for new users) ──
        self.quick_start = QPushButton("\U0001f680  QUICK START  \u2014  Click here to begin your first operation")
        self.quick_start.setFont(QFont("Noto Sans", 12, QFont.Weight.Bold))
        self.quick_start.setMinimumHeight(52)
        self.quick_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.quick_start.setToolTip("Opens a guided wizard to help you get started")
        self.quick_start.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {ACCENT}, stop:1 {PURPLE});
                color: #0a0e17;
                border: none;
                border-radius: 12px;
                font-weight: bold;
                padding: 12px 24px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {PURPLE}, stop:1 {ACCENT});
            }}
        """)
        self.quick_start.clicked.connect(self._launch_wizard)
        self.content_layout.addWidget(self.quick_start)

        # ── App Grid (adaptive columns via QGridLayout) ──
        self.grid_widget = QWidget()
        self.grid = QGridLayout(self.grid_widget)
        self.grid.setSpacing(12)
        self.grid.setContentsMargins(0, 0, 0, 0)

        for i, app_def in enumerate(APP_DEFS):
            card = AppCard(app_def)
            self.cards.append(card)
            # Default: 3 columns. resizeEvent will re-layout
            row, col = divmod(i, 3)
            self.grid.addWidget(card, row, col)

        self.content_layout.addWidget(self.grid_widget)

        # ── Health Bar ──
        self.health = HealthBar()
        self.health.add_indicator("version", "Version")
        self.health.add_indicator("modules", "Modules")
        self.health.add_indicator("services", "Services")
        self.health.add_indicator("vpn", "VPN")
        self.health.add_indicator("ai", "AI")
        self.content_layout.addWidget(self.health)

        # ── Emergency Wipe ──
        panic_btn = QPushButton("\u26a0  EMERGENCY WIPE")
        panic_btn.setFont(QFont("Noto Sans", 12, QFont.Weight.Bold))
        panic_btn.setMinimumHeight(50)
        panic_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        panic_btn.setToolTip("Kill all browsers, flush hardware IDs, clear all data. IRREVERSIBLE.")
        panic_btn.setStyleSheet(f"""
            QPushButton {{
                background: {RED};
                color: white;
                border: 2px solid #991b1b;
                border-radius: 10px;
                font-weight: bold;
                letter-spacing: 1px;
            }}
            QPushButton:hover {{
                background: #991b1b;
                border: 2px solid {RED};
            }}
        """)
        panic_btn.clicked.connect(self._trigger_panic)
        self.content_layout.addWidget(panic_btn)

        self.content_layout.addStretch()

        scroll.setWidget(content)
        outer.addWidget(scroll)

    def resizeEvent(self, event):
        """Adapt grid columns based on window width."""
        super().resizeEvent(event)
        w = self.width()
        if w < 900:
            cols = 1
        elif w < 1200:
            cols = 2
        else:
            cols = 3

        # Re-layout cards only if column count changed
        current_cols = self.grid.columnCount()
        if current_cols == cols and self.grid.count() > 0:
            return

        # Remove all widgets from grid (without deleting)
        while self.grid.count():
            item = self.grid.takeAt(0)
            # Don't delete the widget, just remove from layout

        # Re-add with new column count
        for i, card in enumerate(self.cards):
            row, col = divmod(i, cols)
            self.grid.addWidget(card, row, col)

    def _check_first_run(self):
        """Show wizard if first run."""
        if FIRST_RUN_FLAG.exists():
            self.quick_start.hide()
        else:
            self.quick_start.show()

    def _launch_wizard(self):
        """Launch the first-run wizard."""
        wizard_path = str(APPS_DIR / "titan_first_run_wizard.py")
        if os.path.exists(wizard_path):
            QProcess.startDetached("python3", [wizard_path])
        else:
            QMessageBox.information(
                self, "Quick Start",
                "Welcome to Titan X!\n\n"
                "1. Open SETTINGS to configure your VPN and API keys\n"
                "2. Open NETWORK to connect your VPN\n"
                "3. Open OPERATIONS to start your first run\n\n"
                "That's it! Everything else is automatic.",
            )

    def _check_health(self):
        """Run quick health checks."""
        # Version
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent / "core"))
            import importlib
            spec = importlib.util.spec_from_file_location(
                "core_init",
                str(Path(__file__).parent.parent / "core" / "__init__.py")
            )
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                self.health.set_status("version", mod.__version__, GREEN)
        except Exception:
            self.health.set_status("version", "10.0.0", ACCENT)

        # Module count
        core_dir = Path(__file__).parent.parent / "core"
        if core_dir.exists():
            py_count = len(list(core_dir.glob("*.py"))) - 1  # minus __init__
            color = GREEN if py_count >= 70 else YELLOW if py_count >= 50 else RED
            self.health.set_status("modules", f"{py_count} core", color)
        else:
            self.health.set_status("modules", "N/A", RED)

        # Services
        try:
            from titan_services import get_services_status
            status = get_services_status()
            running = sum(1 for s in status.values() if s.get("running"))
            self.health.set_status("services", f"{running} running", GREEN if running > 0 else YELLOW)
        except Exception:
            self.health.set_status("services", "ready", YELLOW)

        # VPN
        try:
            from mullvad_vpn import get_mullvad_status
            status = get_mullvad_status()
            state = status.get("state", "Unknown")
            if state == "Connected":
                self.health.set_status("vpn", "Connected", GREEN)
            elif state == "Blocked":
                self.health.set_status("vpn", "Kill Switch", YELLOW)
            else:
                self.health.set_status("vpn", "Disconnected", RED)
        except ImportError:
            self.health.set_status("vpn", "Not loaded", TEXT_SECONDARY)
        except Exception:
            self.health.set_status("vpn", "Error", RED)

        # AI
        try:
            from ollama_bridge import LLMLoadBalancer as OllamaBridge
            bridge = OllamaBridge()
            if bridge.is_available():
                self.health.set_status("ai", "Online", GREEN)
            else:
                self.health.set_status("ai", "Offline", YELLOW)
        except Exception:
            self.health.set_status("ai", "Offline", YELLOW)

        # Set card status badges (all green if script exists)
        for card in self.cards:
            script_path = APPS_DIR / card.script
            card.set_ready(script_path.exists())

    def _trigger_panic(self):
        """Emergency panic — confirm then trigger kill switch."""
        reply = QMessageBox.critical(
            self, "EMERGENCY WIPE",
            "This will:\n\n"
            "  1. Kill all browser processes\n"
            "  2. Flush hardware IDs\n"
            "  3. Clear all profiles and session data\n"
            "  4. Randomize MAC address\n\n"
            "THIS CANNOT BE UNDONE. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                sys.path.insert(0, str(Path(__file__).parent.parent / "core"))
                from kill_switch import send_panic_signal
                send_panic_signal()
                QMessageBox.information(self, "Done", "Emergency wipe complete. All data cleared.")
            except ImportError:
                QMessageBox.warning(self, "Error", "Kill switch module not available.\nGo to Admin > Kill Switch for manual wipe.")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Kill switch error: {e}")

    def apply_theme(self):
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(BG_DARK))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(TEXT_PRIMARY))
        palette.setColor(QPalette.ColorRole.Base, QColor(BG_CARD))
        palette.setColor(QPalette.ColorRole.Text, QColor(TEXT_PRIMARY))
        self.setPalette(palette)
        self.setStyleSheet(f"""
            QMainWindow {{ background: {BG_DARK}; }}
            QLabel {{ background: transparent; }}
            QToolTip {{
                background: {BG_CARD};
                color: {TEXT_PRIMARY};
                border: 1px solid {ACCENT}44;
                border-radius: 6px;
                padding: 8px;
                font-size: 11px;
            }}
        """)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Global tooltip styling
    QToolTip.setFont(QFont("Noto Sans", 10))

    window = TitanLauncher()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
