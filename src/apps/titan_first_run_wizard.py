#!/usr/bin/env python3
"""
TITAN X FIRST-RUN WIZARD
=========================
Guided setup for new users — plain English, zero code knowledge required.
Steps: Welcome → VPN Setup → API Keys → AI Check → Done
"""

import sys
import os
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QStackedWidget, QLineEdit,
    QMessageBox, QSizePolicy, QComboBox, QCheckBox, QTextEdit
)
from PyQt6.QtCore import Qt, QTimer, QProcess
from PyQt6.QtGui import QFont, QColor, QPalette

sys.path.insert(0, str(Path(__file__).parent.parent / "core"))

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
TITAN_ENV = Path("/opt/titan/titan.env")


class WizardPage(QFrame):
    """A single wizard page with title, content area, and navigation."""

    def __init__(self, title: str, subtitle: str = "", parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: transparent;")

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(40, 30, 40, 20)
        self._layout.setSpacing(16)

        # Step title
        title_lbl = QLabel(title)
        title_lbl.setFont(QFont("Noto Sans", 22, QFont.Weight.Bold))
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_lbl.setStyleSheet(f"color: {ACCENT};")
        title_lbl.setWordWrap(True)
        self._layout.addWidget(title_lbl)

        if subtitle:
            sub_lbl = QLabel(subtitle)
            sub_lbl.setFont(QFont("Noto Sans", 11))
            sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            sub_lbl.setStyleSheet(f"color: {TEXT_SECONDARY};")
            sub_lbl.setWordWrap(True)
            self._layout.addWidget(sub_lbl)

        # Content area for subclass to populate
        self.content = QVBoxLayout()
        self.content.setSpacing(12)
        self._layout.addLayout(self.content)
        self._layout.addStretch()

    def add_info_card(self, icon: str, text: str):
        """Add an info card with icon and text."""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: {BG_CARD};
                border: 1px solid #1e293b;
                border-radius: 10px;
                padding: 12px;
            }}
        """)
        h = QHBoxLayout(card)
        h.setContentsMargins(16, 12, 16, 12)
        h.setSpacing(12)

        icon_lbl = QLabel(icon)
        icon_lbl.setFont(QFont("Noto Color Emoji", 20))
        icon_lbl.setFixedWidth(40)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h.addWidget(icon_lbl)

        text_lbl = QLabel(text)
        text_lbl.setFont(QFont("Noto Sans", 11))
        text_lbl.setStyleSheet(f"color: {TEXT_PRIMARY};")
        text_lbl.setWordWrap(True)
        h.addWidget(text_lbl, 1)

        self.content.addWidget(card)

    def add_input(self, label: str, placeholder: str = "", password: bool = False) -> QLineEdit:
        """Add a labeled input field."""
        lbl = QLabel(label)
        lbl.setFont(QFont("Noto Sans", 10, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: {TEXT_SECONDARY};")
        self.content.addWidget(lbl)

        inp = QLineEdit()
        inp.setPlaceholderText(placeholder)
        inp.setFont(QFont("DejaVu Sans Mono", 11))
        inp.setMinimumHeight(44)
        if password:
            inp.setEchoMode(QLineEdit.EchoMode.Password)
        inp.setStyleSheet(f"""
            QLineEdit {{
                background: {BG_CARD};
                color: {TEXT_PRIMARY};
                border: 1px solid #1e293b;
                border-radius: 8px;
                padding: 8px 12px;
            }}
            QLineEdit:focus {{
                border: 1px solid {ACCENT};
            }}
        """)
        self.content.addWidget(inp)
        return inp


class FirstRunWizard(QMainWindow):
    """Guided first-run wizard for Titan X."""

    def __init__(self):
        super().__init__()
        self.current_page = 0
        self.pages = []
        self.init_ui()
        self.apply_theme()

    def init_ui(self):
        self.setWindowTitle("Titan X — Setup Wizard")
        self.setMinimumSize(700, 500)
        self.resize(800, 600)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Progress bar
        self.progress_frame = QFrame()
        self.progress_frame.setFixedHeight(4)
        self.progress_frame.setStyleSheet(f"background: #1e293b;")
        layout.addWidget(self.progress_frame)

        self.progress_bar = QFrame(self.progress_frame)
        self.progress_bar.setStyleSheet(f"background: {ACCENT}; border-radius: 2px;")
        self.progress_bar.setGeometry(0, 0, 0, 4)

        # Stacked pages
        self.stack = QStackedWidget()
        layout.addWidget(self.stack, 1)

        # Navigation buttons
        nav = QFrame()
        nav.setStyleSheet(f"background: {BG_CARD}; border-top: 1px solid #1e293b;")
        nav_layout = QHBoxLayout(nav)
        nav_layout.setContentsMargins(20, 12, 20, 12)

        self.btn_back = QPushButton("Back")
        self.btn_back.setFont(QFont("Noto Sans", 11))
        self.btn_back.setMinimumHeight(44)
        self.btn_back.setMinimumWidth(100)
        self.btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_back.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {TEXT_SECONDARY};
                border: 1px solid #1e293b;
                border-radius: 8px;
                padding: 8px 20px;
            }}
            QPushButton:hover {{
                border: 1px solid {ACCENT};
                color: {TEXT_PRIMARY};
            }}
        """)
        self.btn_back.clicked.connect(self._back)
        nav_layout.addWidget(self.btn_back)

        nav_layout.addStretch()

        # Step indicator
        self.step_label = QLabel("Step 1 of 5")
        self.step_label.setFont(QFont("Noto Sans", 10))
        self.step_label.setStyleSheet(f"color: {TEXT_SECONDARY};")
        nav_layout.addWidget(self.step_label)

        nav_layout.addStretch()

        self.btn_next = QPushButton("Next")
        self.btn_next.setFont(QFont("Noto Sans", 11, QFont.Weight.Bold))
        self.btn_next.setMinimumHeight(44)
        self.btn_next.setMinimumWidth(100)
        self.btn_next.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_next.setStyleSheet(f"""
            QPushButton {{
                background: {ACCENT};
                color: #0a0e17;
                border: none;
                border-radius: 8px;
                font-weight: bold;
                padding: 8px 20px;
            }}
            QPushButton:hover {{
                background: {ACCENT}cc;
            }}
        """)
        self.btn_next.clicked.connect(self._next)
        nav_layout.addWidget(self.btn_next)

        layout.addWidget(nav)

        # Build pages
        self._build_pages()
        self._update_nav()

    def _build_pages(self):
        # Page 1: Welcome
        p1 = WizardPage(
            "Welcome to Titan X",
            "Let's get you set up in a few minutes. No coding required."
        )
        p1.add_info_card("\U0001f512", "Step 1: We'll help you connect your VPN for safety")
        p1.add_info_card("\U0001f511", "Step 2: Enter your API keys (if you have them)")
        p1.add_info_card("\U0001f916", "Step 3: Check that the AI engine is ready")
        p1.add_info_card("\u2705", "Step 4: You're all set — start your first operation!")
        self._add_page(p1)

        # Page 2: VPN
        p2 = WizardPage(
            "VPN Connection",
            "A VPN protects your real IP address. We recommend Mullvad VPN."
        )
        p2.add_info_card("\U0001f30d", "Mullvad VPN is pre-configured. Just enter your account number.")
        self.vpn_input = p2.add_input("Mullvad Account Number", "e.g. 1234567890123456")
        p2.add_info_card("\U0001f4a1", "Don't have Mullvad? You can skip this and set it up later in Settings.")
        self._add_page(p2)

        # Page 3: API Keys
        p3 = WizardPage(
            "API Keys (Optional)",
            "These make the AI features smarter. You can skip and add them later."
        )
        self.openai_input = p3.add_input("OpenAI API Key", "sk-...", password=True)
        self.anthropic_input = p3.add_input("Anthropic API Key (optional)", "sk-ant-...", password=True)
        p3.add_info_card("\U0001f4a1", "No API keys? Titan X will use the local Ollama AI model instead. It's free!")
        self._add_page(p3)

        # Page 4: System Check
        p4 = WizardPage(
            "System Check",
            "Checking that everything is working..."
        )
        self.check_results = QTextEdit()
        self.check_results.setReadOnly(True)
        self.check_results.setFont(QFont("DejaVu Sans Mono", 10))
        self.check_results.setMinimumHeight(200)
        self.check_results.setStyleSheet(f"""
            QTextEdit {{
                background: {BG_CARD};
                color: {TEXT_PRIMARY};
                border: 1px solid #1e293b;
                border-radius: 8px;
                padding: 12px;
            }}
        """)
        p4.content.addWidget(self.check_results)
        self._add_page(p4)

        # Page 5: Done
        p5 = WizardPage(
            "\u2705  You're All Set!",
            "Titan X is ready to use."
        )
        p5.add_info_card("\U0001f3af", "Open OPERATIONS to start your first run")
        p5.add_info_card("\U0001f9e0", "Use INTELLIGENCE for AI-powered advice")
        p5.add_info_card("\U0001f527", "Go to SETTINGS anytime to change your configuration")
        p5.add_info_card("\U0001f41b", "Having problems? Open BUG REPORTER to get auto-fixes")
        self._add_page(p5)

    def _add_page(self, page):
        self.pages.append(page)
        self.stack.addWidget(page)

    def _update_nav(self):
        total = len(self.pages)
        self.step_label.setText(f"Step {self.current_page + 1} of {total}")
        self.btn_back.setVisible(self.current_page > 0)

        if self.current_page == total - 1:
            self.btn_next.setText("Finish")
        elif self.current_page == 1 or self.current_page == 2:
            self.btn_next.setText("Skip / Next")
        else:
            self.btn_next.setText("Next")

        # Progress bar
        pct = (self.current_page + 1) / total
        bar_width = int(self.progress_frame.width() * pct)
        self.progress_bar.setGeometry(0, 0, max(bar_width, 20), 4)

    def _next(self):
        # Save data from current page before advancing
        if self.current_page == 1:
            self._save_vpn()
        elif self.current_page == 2:
            self._save_api_keys()
        elif self.current_page == 3:
            self._run_system_check()

        if self.current_page >= len(self.pages) - 1:
            self._finish()
            return

        self.current_page += 1
        self.stack.setCurrentIndex(self.current_page)
        self._update_nav()

        # Auto-run system check when reaching page 4
        if self.current_page == 3:
            QTimer.singleShot(500, self._run_system_check)

    def _back(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.stack.setCurrentIndex(self.current_page)
            self._update_nav()

    def _save_vpn(self):
        """Save VPN account number to titan.env."""
        account = self.vpn_input.text().strip()
        if account:
            self._update_env("MULLVAD_ACCOUNT", account)

    def _save_api_keys(self):
        """Save API keys to titan.env."""
        openai_key = self.openai_input.text().strip()
        anthropic_key = self.anthropic_input.text().strip()
        if openai_key:
            self._update_env("OPENAI_API_KEY", openai_key)
        if anthropic_key:
            self._update_env("ANTHROPIC_API_KEY", anthropic_key)

    def _update_env(self, key: str, value: str):
        """Update or add a key in titan.env."""
        try:
            env_path = TITAN_ENV
            if not env_path.exists():
                env_path.parent.mkdir(parents=True, exist_ok=True)
                env_path.write_text(f"{key}={value}\n")
                return

            lines = env_path.read_text().splitlines()
            found = False
            for i, line in enumerate(lines):
                if line.startswith(f"{key}="):
                    lines[i] = f"{key}={value}"
                    found = True
                    break
            if not found:
                lines.append(f"{key}={value}")
            env_path.write_text("\n".join(lines) + "\n")
        except Exception:
            pass  # Non-fatal: user can set it manually in Settings

    def _run_system_check(self):
        """Run automated system checks."""
        self.check_results.clear()
        results = []

        def log(icon, text):
            results.append(f"  {icon}  {text}")
            self.check_results.setPlainText("\n".join(results))

        log("\U0001f50d", "Checking core modules...")
        core_dir = Path(__file__).parent.parent / "core"
        if core_dir.exists():
            count = len(list(core_dir.glob("*.py"))) - 1
            log("\u2705", f"Found {count} core modules")
        else:
            log("\u274c", "Core modules directory not found")

        log("\U0001f50d", "Checking app scripts...")
        apps_dir = Path(__file__).parent
        app_count = len(list(apps_dir.glob("*.py")))
        log("\u2705", f"Found {app_count} app scripts")

        log("\U0001f50d", "Checking VPN...")
        try:
            from mullvad_vpn import get_mullvad_status
            status = get_mullvad_status()
            state = status.get("state", "Unknown")
            if state == "Connected":
                log("\u2705", f"VPN connected: {status.get('city', 'Unknown')}")
            else:
                log("\u26a0\ufe0f", f"VPN: {state} — connect via Network app")
        except Exception:
            log("\u26a0\ufe0f", "VPN module not loaded — configure in Settings")

        log("\U0001f50d", "Checking AI engine...")
        try:
            from ollama_bridge import LLMLoadBalancer
            bridge = LLMLoadBalancer()
            if bridge.is_available():
                log("\u2705", "Ollama AI engine is online")
            else:
                log("\u26a0\ufe0f", "Ollama AI is offline — start via Admin app")
        except Exception:
            log("\u26a0\ufe0f", "AI engine not available — optional feature")

        log("\U0001f50d", "Checking branding...")
        wp = Path("/opt/titan/branding/wallpapers/titan_wallpaper_1080.png")
        if wp.exists():
            log("\u2705", "Branding assets installed")
        else:
            log("\u26a0\ufe0f", "Branding assets not found — cosmetic only")

        log("", "")
        log("\u2705", "System check complete!")

    def _finish(self):
        """Mark first run as done and close."""
        try:
            FIRST_RUN_FLAG.parent.mkdir(parents=True, exist_ok=True)
            FIRST_RUN_FLAG.write_text("done\n")
        except Exception:
            pass
        self.close()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_nav()

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
    window = FirstRunWizard()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
