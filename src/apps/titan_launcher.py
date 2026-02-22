#!/usr/bin/env python3
"""
TITAN V8.1 LAUNCHER — Clean Entry Point
========================================
5 apps, 23 tabs total, 85 core modules — zero orphans.

App Structure (V8.1 Final):
  1. Operations Center — Daily workflow (target → card → persona → forge → launch)
  2. Intelligence Center — AI copilot, 3DS strategy, detection analysis, recon
  3. Network Center — Mullvad VPN, eBPF shield, proxy, forensic monitor
  4. KYC Studio — Camera, documents, voice, mobile sync
  5. Admin Panel — Services, tools, system, automation, config
"""

import sys
import os
import subprocess
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QGridLayout, QGroupBox
)
from PyQt6.QtCore import Qt, QTimer, QProcess
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


class AppCard(QFrame):
    """Clickable app launcher card."""

    def __init__(self, title: str, subtitle: str, description: str,
                 accent: str, icon_char: str, script: str, parent=None):
        super().__init__(parent)
        self.script = script
        self.accent = accent
        self._hovered = False

        self.setFixedSize(320, 280)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            AppCard {{
                background: {BG_CARD};
                border: 1px solid #1e293b;
                border-radius: 16px;
            }}
            AppCard:hover {{
                background: {BG_HOVER};
                border: 1px solid {accent};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        # Icon
        icon = QLabel(icon_char)
        icon.setFont(QFont("Segoe UI Emoji", 36))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon)

        # Title
        title_lbl = QLabel(title)
        title_lbl.setFont(QFont("Inter", 16, QFont.Weight.Bold))
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_lbl.setStyleSheet(f"color: {accent};")
        layout.addWidget(title_lbl)

        # Subtitle
        sub_lbl = QLabel(subtitle)
        sub_lbl.setFont(QFont("JetBrains Mono", 9))
        sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub_lbl.setStyleSheet(f"color: {TEXT_SECONDARY};")
        layout.addWidget(sub_lbl)

        # Description
        desc_lbl = QLabel(description)
        desc_lbl.setFont(QFont("Inter", 10))
        desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet(f"color: {TEXT_PRIMARY};")
        layout.addWidget(desc_lbl)

        layout.addStretch()

        # Launch button
        btn = QPushButton("LAUNCH")
        btn.setFont(QFont("Inter", 11, QFont.Weight.Bold))
        btn.setFixedHeight(40)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {accent};
                color: #0a0e17;
                border: none;
                border-radius: 8px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {accent}dd;
            }}
        """)
        btn.clicked.connect(self._launch)
        layout.addWidget(btn)

    def _launch(self):
        script_path = str(APPS_DIR / self.script)
        if os.path.exists(script_path):
            QProcess.startDetached("python3", [script_path])
        else:
            # Fallback for Windows
            QProcess.startDetached(sys.executable, [script_path])

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._launch()


class HealthIndicator(QFrame):
    """Small health status indicator."""

    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        self.dot = QLabel("\u2b24")
        self.dot.setFont(QFont("Inter", 8))
        self.dot.setStyleSheet(f"color: {TEXT_SECONDARY};")
        layout.addWidget(self.dot)

        self.label = QLabel(label)
        self.label.setFont(QFont("Inter", 10))
        self.label.setStyleSheet(f"color: {TEXT_SECONDARY};")
        layout.addWidget(self.label)

        self.value = QLabel("...")
        self.value.setFont(QFont("JetBrains Mono", 10))
        self.value.setStyleSheet(f"color: {TEXT_PRIMARY};")
        layout.addWidget(self.value)
        layout.addStretch()

    def set_status(self, text: str, color: str = GREEN):
        self.value.setText(text)
        self.value.setStyleSheet(f"color: {color};")
        self.dot.setStyleSheet(f"color: {color};")


class TitanLauncher(QMainWindow):
    """
    TITAN V8.1 Launcher — 5 apps, 23 tabs, 85 modules, zero orphans.

    - Operations Center: Daily workflow (38 modules)
    - Intelligence Center: AI analysis & strategy (20 modules)
    - Network Center: VPN, shield, proxy, forensic (18 modules)
    - KYC Studio: Identity verification (8 modules)
    - Admin Panel: System management (14 modules)
    """

    def __init__(self):
        super().__init__()
        self.init_ui()
        self.apply_theme()
        QTimer.singleShot(500, self._check_health)

    def init_ui(self):
        self.setWindowTitle("TITAN V8.1 \u2014 Launcher")
        try:
            from titan_icon import set_titan_icon
            set_titan_icon(self, ACCENT)
        except Exception:
            pass
        self.setFixedSize(1180, 700)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(16)

        # Header
        header = QLabel("TITAN V8.1")
        header.setFont(QFont("Inter", 28, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet(f"color: {ACCENT};")
        layout.addWidget(header)

        subtitle = QLabel("SINGULARITY \u2014 MAXIMUM LEVEL")
        subtitle.setFont(QFont("JetBrains Mono", 11))
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet(f"color: {TEXT_SECONDARY}; letter-spacing: 4px;")
        layout.addWidget(subtitle)

        # App Cards — top row (3) + bottom row (2)
        top_row = QHBoxLayout()
        top_row.setSpacing(16)

        # Card 1: Operations Center (38 modules)
        top_row.addWidget(AppCard(
            title="Operations",
            subtitle="DAILY WORKFLOW \u2022 38 MODULES",
            description="Target \u2192 Identity \u2192 Validate \u2192 Forge \u2192 Launch\n5 tabs \u2022 Card BIN intel \u2022 Preflight",
            accent="#00d4ff",
            icon_char="\ud83c\udfaf",
            script="titan_operations.py",
        ))

        # Card 2: Intelligence Center (20 modules)
        top_row.addWidget(AppCard(
            title="Intelligence",
            subtitle="AI ANALYSIS \u2022 20 MODULES",
            description="AI Copilot \u2022 3DS Strategy \u2022 Detection\nRecon \u2022 Vector Memory \u2022 Web Intel",
            accent="#a855f7",
            icon_char="\ud83e\udde0",
            script="titan_intelligence.py",
        ))

        # Card 3: Network Center (18 modules)
        top_row.addWidget(AppCard(
            title="Network",
            subtitle="VPN & SHIELD \u2022 18 MODULES",
            description="Mullvad VPN \u2022 eBPF TCP Mimesis\nForensic Monitor \u2022 Proxy \u2022 GeoIP",
            accent="#22c55e",
            icon_char="\ud83d\udd12",
            script="titan_network.py",
        ))

        layout.addLayout(top_row)

        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(16)
        bottom_row.addStretch()

        # Card 4: KYC Studio (8 modules)
        bottom_row.addWidget(AppCard(
            title="KYC Studio",
            subtitle="IDENTITY VERIFY \u2022 8 MODULES",
            description="Camera \u2022 Documents \u2022 Voice\nToF Depth \u2022 Deep Identity \u2022 Mobile",
            accent="#f97316",
            icon_char="\ud83d\udcf7",
            script="app_kyc.py",
        ))

        # Card 5: Admin Panel (14 modules)
        bottom_row.addWidget(AppCard(
            title="Admin",
            subtitle="SYSTEM MGMT \u2022 14 MODULES",
            description="Services \u2022 Automation \u2022 Config\nDetection Lab \u2022 AI Setup \u2022 Kill Switch",
            accent="#f59e0b",
            icon_char="\u2699\ufe0f",
            script="titan_admin.py",
        ))

        # Card 6: Bug Reporter (recovered V8.0)
        bottom_row.addWidget(AppCard(
            title="Bug Reporter",
            subtitle="DIAGNOSTICS \u2022 AUTO-PATCH",
            description="Issue Reporting \u2022 Decline Intel\nWindsurf Patching \u2022 Log Analysis",
            accent="#ef4444",
            icon_char="\ud83d\udc1b",
            script="app_bug_reporter.py",
        ))

        bottom_row.addStretch()
        layout.addLayout(bottom_row)

        # Health Status Bar
        health_frame = QFrame()
        health_frame.setStyleSheet(f"""
            QFrame {{
                background: {BG_CARD};
                border: 1px solid #1e293b;
                border-radius: 10px;
            }}
        """)
        health_layout = QHBoxLayout(health_frame)
        health_layout.setContentsMargins(16, 8, 16, 8)

        self.h_version = HealthIndicator("Version")
        self.h_modules = HealthIndicator("Modules")
        self.h_services = HealthIndicator("Services")
        self.h_vpn = HealthIndicator("VPN")
        self.h_ai = HealthIndicator("AI Engine")

        health_layout.addWidget(self.h_version)
        health_layout.addWidget(self.h_modules)
        health_layout.addWidget(self.h_services)
        health_layout.addWidget(self.h_vpn)
        health_layout.addWidget(self.h_ai)

        layout.addWidget(health_frame)

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
                self.h_version.set_status(mod.__version__, GREEN)
        except Exception:
            self.h_version.set_status("8.1.0", ACCENT)

        # Module count
        core_dir = Path(__file__).parent.parent / "core"
        if core_dir.exists():
            py_count = len(list(core_dir.glob("*.py"))) - 1  # minus __init__
            color = GREEN if py_count >= 70 else YELLOW if py_count >= 50 else RED
            self.h_modules.set_status(f"{py_count} core", color)
        else:
            self.h_modules.set_status("N/A", RED)

        # Services
        try:
            from titan_services import get_services_status
            status = get_services_status()
            running = sum(1 for s in status.values() if s.get("running"))
            self.h_services.set_status(f"{running} running", GREEN if running > 0 else YELLOW)
        except Exception:
            self.h_services.set_status("ready", YELLOW)

        # VPN
        try:
            from mullvad_vpn import get_mullvad_status
            status = get_mullvad_status()
            state = status.get("state", "Unknown")
            if state == "Connected":
                self.h_vpn.set_status("Mullvad OK", GREEN)
            elif state == "Blocked":
                self.h_vpn.set_status("kill switch", YELLOW)
            else:
                self.h_vpn.set_status("disconnected", RED)
        except ImportError:
            self.h_vpn.set_status("not loaded", TEXT_SECONDARY)
        except Exception:
            self.h_vpn.set_status("error", RED)

        # AI
        try:
            from ollama_bridge import OllamaBridge
            bridge = OllamaBridge()
            if bridge.is_available():
                self.h_ai.set_status("Ollama OK", GREEN)
            else:
                self.h_ai.set_status("offline", YELLOW)
        except Exception:
            self.h_ai.set_status("offline", YELLOW)

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
        """)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = TitanLauncher()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
