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
            "Let's get you set up in 5 minutes. No coding required."
        )
        p1.add_info_card("\U0001f512", "Step 1: Connect your VPN (Mullvad is pre-installed)")
        p1.add_info_card("\U0001f310", "Step 2: Add your proxy credentials for residential IPs")
        p1.add_info_card("\U0001f511", "Step 3: Enter your API keys (Groq is free and fast)")
        p1.add_info_card("\U0001f916", "Step 4: System readiness check — verify everything works")
        p1.add_info_card("\u2705", "Step 5: You're ready — start your first operation!")
        self._add_page(p1)

        # Page 2: VPN
        p2 = WizardPage(
            "VPN Connection",
            "Mullvad VPN is pre-installed. Enter your account number to connect."
        )
        p2.add_info_card("\U0001f30d", "Mullvad is the safest VPN for operations. No logs, no leak.")
        self.vpn_input = p2.add_input("Mullvad Account Number (16 digits)", "e.g. 1234567890123456")

        self.vpn_test_btn = QPushButton("Test VPN Connection")
        self.vpn_test_btn.setFont(QFont("Noto Sans", 10))
        self.vpn_test_btn.setMinimumHeight(40)
        self.vpn_test_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.vpn_test_btn.setStyleSheet(f"""
            QPushButton {{ background: {GREEN}; color: #0a0e17; border: none;
                border-radius: 8px; font-weight: bold; padding: 8px 16px; }}
            QPushButton:hover {{ background: {GREEN}cc; }}
        """)
        self.vpn_test_btn.clicked.connect(self._test_vpn)
        p2.content.addWidget(self.vpn_test_btn)

        self.vpn_status_lbl = QLabel("Status: Not tested")
        self.vpn_status_lbl.setFont(QFont("DejaVu Sans Mono", 10))
        self.vpn_status_lbl.setStyleSheet(f"color: {TEXT_SECONDARY};")
        p2.content.addWidget(self.vpn_status_lbl)

        p2.add_info_card("\U0001f4a1", "No Mullvad? Get one at mullvad.net — from $5/month. Skip and set up later in Settings.")
        self._add_page(p2)

        # Page 3: Proxy Setup
        p3 = WizardPage(
            "Residential Proxy",
            "A residential proxy makes you look like a real home user to target sites."
        )
        p3.add_info_card("\U0001f3e0", "Residential proxies are REQUIRED for checkout. Datacenter IPs are blocked.")
        self.proxy_provider_combo = QComboBox()
        self.proxy_provider_combo.addItems(["brightdata", "oxylabs", "smartproxy", "iproyal", "custom"])
        self.proxy_provider_combo.setFont(QFont("Noto Sans", 11))
        self.proxy_provider_combo.setMinimumHeight(44)
        self.proxy_provider_combo.setStyleSheet(f"""
            QComboBox {{ background: {BG_CARD}; color: {TEXT_PRIMARY};
                border: 1px solid #1e293b; border-radius: 8px; padding: 8px 12px; }}
            QComboBox::drop-down {{ border: none; }}
            QComboBox QAbstractItemView {{ background: {BG_CARD}; color: {TEXT_PRIMARY}; }}
        """)
        p3.content.addWidget(QLabel("Provider:"))
        p3.content.addWidget(self.proxy_provider_combo)

        self.proxy_user_input = p3.add_input("Proxy Username", "user_abc123")
        self.proxy_pass_input = p3.add_input("Proxy Password", "••••••••", password=True)
        p3.add_info_card("\U0001f4a1", "Don't have a proxy? You can skip and add one later in Settings → Proxy tab.")
        self._add_page(p3)

        # Page 4: API Keys
        p4 = WizardPage(
            "API Keys",
            "These power the AI features. Groq is FREE and gives fast inference."
        )
        p4.add_info_card("\u26a1", "Groq is FREE (6,000 req/day) — get key at console.groq.com in 30 seconds")
        self.groq_input = p4.add_input("Groq API Key (FREE — recommended)", "gsk_...", password=True)
        self.openai_input = p4.add_input("OpenAI API Key (optional)", "sk-...", password=True)
        self.anthropic_input = p4.add_input("Anthropic API Key (optional)", "sk-ant-...", password=True)
        self.serpapi_input = p4.add_input("SerpAPI Key (optional — free tier available at serpapi.com)", "", password=True)
        p4.add_info_card("\U0001f916", "No keys? Titan X uses local Ollama AI (4 models, free, no internet needed)")
        self._add_page(p4)

        # Page 5: System Check
        p5 = WizardPage(
            "System Readiness Check",
            "Verifying all services are running correctly..."
        )
        self.check_results = QTextEdit()
        self.check_results.setReadOnly(True)
        self.check_results.setFont(QFont("DejaVu Sans Mono", 10))
        self.check_results.setMinimumHeight(260)
        self.check_results.setStyleSheet(f"""
            QTextEdit {{ background: {BG_CARD}; color: {TEXT_PRIMARY};
                border: 1px solid #1e293b; border-radius: 8px; padding: 12px; }}
        """)
        p5.content.addWidget(self.check_results)

        recheck_btn = QPushButton("Re-run Check")
        recheck_btn.setFont(QFont("Noto Sans", 10))
        recheck_btn.setMinimumHeight(40)
        recheck_btn.setStyleSheet(f"""
            QPushButton {{ background: {ACCENT}44; color: {ACCENT}; border: 1px solid {ACCENT}44;
                border-radius: 8px; font-weight: bold; padding: 8px 16px; }}
            QPushButton:hover {{ background: {ACCENT}88; }}
        """)
        recheck_btn.clicked.connect(self._run_system_check)
        p5.content.addWidget(recheck_btn)

        self.readiness_lbl = QLabel("Readiness: checking...")
        self.readiness_lbl.setFont(QFont("Noto Sans", 14, QFont.Weight.Bold))
        self.readiness_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.readiness_lbl.setStyleSheet(f"color: {YELLOW};")
        p5.content.addWidget(self.readiness_lbl)
        self._add_page(p5)

        # Page 6: Done
        p6 = WizardPage(
            "\u2705  Titan X is Ready!",
            "Your system is configured. Here's how to begin."
        )
        p6.add_info_card("\u0031\ufe0f\u20e3", "Open OPERATIONS — pick a target, fill card, click RUN FULL OP")
        p6.add_info_card("\u0032\ufe0f\u20e3", "Connect VPN in NETWORK before every operation")
        p6.add_info_card("\u0033\ufe0f\u20e3", "Use PROFILE FORGE to create aged browser identities")
        p6.add_info_card("\u0034\ufe0f\u20e3", "Use CARD VALIDATOR to grade your cards before use")
        p6.add_info_card("\U0001f41b", "Problems? Open BUG REPORTER for auto-diagnosis and fixes")
        self._add_page(p6)

    def _add_page(self, page):
        self.pages.append(page)
        self.stack.addWidget(page)

    def _update_nav(self):
        total = len(self.pages)
        self.step_label.setText(f"Step {self.current_page + 1} of {total}")
        self.btn_back.setVisible(self.current_page > 0)

        # Pages 2,3,4 (proxy, API keys) are skippable
        skippable = {2, 3, 4}
        if self.current_page == total - 1:
            self.btn_next.setText("Start Titan X")
        elif self.current_page in skippable:
            self.btn_next.setText("Skip / Next")
        else:
            self.btn_next.setText("Next")

        pct = (self.current_page + 1) / total
        bar_width = int(self.progress_frame.width() * pct)
        self.progress_bar.setGeometry(0, 0, max(bar_width, 20), 4)

    def _next(self):
        if self.current_page == 1:
            self._save_vpn()
        elif self.current_page == 2:
            self._save_proxy()
        elif self.current_page == 3:
            self._save_api_keys()

        if self.current_page >= len(self.pages) - 1:
            self._finish()
            return

        self.current_page += 1
        self.stack.setCurrentIndex(self.current_page)
        self._update_nav()

        # Auto-run system check when reaching page 5
        if self.current_page == 4:
            QTimer.singleShot(400, self._run_system_check)

    def _back(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.stack.setCurrentIndex(self.current_page)
            self._update_nav()

    def _save_vpn(self):
        account = self.vpn_input.text().strip()
        if account and account.isdigit():
            self._update_env("TITAN_MULLVAD_ACCOUNT", account)

    def _save_proxy(self):
        provider = self.proxy_provider_combo.currentText()
        user = self.proxy_user_input.text().strip()
        passwd = self.proxy_pass_input.text().strip()
        if user and passwd:
            self._update_env("TITAN_PROXY_PROVIDER", provider)
            self._update_env("TITAN_PROXY_USERNAME", user)
            self._update_env("TITAN_PROXY_PASSWORD", passwd)

    def _save_api_keys(self):
        keys = {
            "TITAN_GROQ_API_KEY": self.groq_input.text().strip(),
            "TITAN_OPENAI_API_KEY": self.openai_input.text().strip(),
            "TITAN_ANTHROPIC_API_KEY": self.anthropic_input.text().strip(),
            "SERPAPI_KEY": self.serpapi_input.text().strip(),
        }
        for k, v in keys.items():
            if v:
                self._update_env(k, v)

    def _test_vpn(self):
        account = self.vpn_input.text().strip()
        if account:
            self._save_vpn()
            self.vpn_status_lbl.setText("Status: Connecting...")
            self.vpn_status_lbl.setStyleSheet(f"color: {YELLOW};")
            try:
                import subprocess
                result = subprocess.run(
                    ["mullvad", "account", "set", account],
                    capture_output=True, text=True, timeout=10
                )
                result2 = subprocess.run(
                    ["mullvad", "connect"],
                    capture_output=True, text=True, timeout=15
                )
                import time; time.sleep(3)
                result3 = subprocess.run(
                    ["mullvad", "status"],
                    capture_output=True, text=True, timeout=5
                )
                out = result3.stdout.strip()
                if "Connected" in out:
                    self.vpn_status_lbl.setText(f"Status: Connected — {out}")
                    self.vpn_status_lbl.setStyleSheet(f"color: {GREEN};")
                else:
                    self.vpn_status_lbl.setText(f"Status: {out or 'Connecting...'}")
                    self.vpn_status_lbl.setStyleSheet(f"color: {YELLOW};")
            except Exception as e:
                self.vpn_status_lbl.setText(f"Status: Error — {e}")
                self.vpn_status_lbl.setStyleSheet(f"color: {RED};")
        else:
            self.vpn_status_lbl.setText("Status: Enter account number first")
            self.vpn_status_lbl.setStyleSheet(f"color: {RED};")

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
        """Comprehensive system readiness check with scoring."""
        import subprocess
        self.check_results.clear()
        lines = []
        score = 0
        max_score = 0

        def chk(icon, label, ok, points=10, note=""):
            nonlocal score, max_score
            max_score += points
            if ok:
                score += points
            sym = "\u2705" if ok else "\u26a0\ufe0f"
            suffix = f"  ({note})" if note else ""
            lines.append(f"  {sym}  {label}{suffix}")
            self.check_results.setPlainText("\n".join(lines))
            QApplication.processEvents()

        lines.append("  ══ TITAN X READINESS CHECK ══\n")
        self.check_results.setPlainText("\n".join(lines))
        QApplication.processEvents()

        # Core modules
        core_dir = Path(__file__).parent.parent / "core"
        count = len(list(core_dir.glob("*.py"))) - 1 if core_dir.exists() else 0
        chk("", f"Core modules: {count}/119", count >= 100, 15)

        # App scripts
        apps_dir = Path(__file__).parent
        app_count = len(list(apps_dir.glob("*.py")))
        chk("", f"App scripts: {app_count}", app_count >= 15, 10)

        # Kernel module
        ko_ok = Path("/opt/titan/hardware_shield/titan_hw.ko").exists() or \
                Path("/opt/titan/kernel-modules/titan_hw.ko").exists()
        chk("", "Hardware shield (kernel module)", ko_ok, 10, "optional but recommended")

        # Ollama AI service
        try:
            r = subprocess.run(["curl", "-s", "--max-time", "3", "http://127.0.0.1:11434/api/tags"],
                               capture_output=True, text=True)
            ai_ok = r.returncode == 0 and "models" in r.stdout
            model_count = r.stdout.count('"name"') if ai_ok else 0
            chk("", f"Ollama AI: {model_count} models loaded", ai_ok, 15)
        except Exception:
            chk("", "Ollama AI service", False, 15, "start via: systemctl start ollama")

        # Bridge APIs
        for bridge_name, port in [("Genesis AppX", 36200), ("Cerberus AppX", 36300), ("KYC AppX", 36400)]:
            try:
                r = subprocess.run(["curl", "-s", "--max-time", "2", f"http://127.0.0.1:{port}/health"],
                                   capture_output=True, text=True)
                ok = r.returncode == 0 and len(r.stdout) > 2
                chk("", f"{bridge_name} bridge :{port}", ok, 10)
            except Exception:
                chk("", f"{bridge_name} bridge :{port}", False, 10, "auto-starts with titan-services")

        # VPN
        try:
            r = subprocess.run(["mullvad", "status"], capture_output=True, text=True, timeout=5)
            connected = "Connected" in r.stdout
            chk("", f"VPN: {r.stdout.strip()[:60]}", connected, 15,
                "" if connected else "connect via Network app or Settings")
        except Exception:
            chk("", "Mullvad VPN", False, 15, "configure in Settings")

        # Proxy config
        env_path = TITAN_ENV
        proxy_set = False
        if env_path.exists():
            content = env_path.read_text()
            proxy_set = "TITAN_PROXY_USERNAME=" in content and "demo-user" not in content
        chk("", "Residential proxy configured", proxy_set, 15,
            "" if proxy_set else "add in Settings → Proxy or re-run wizard")

        # Redis
        try:
            r = subprocess.run(["redis-cli", "ping"], capture_output=True, text=True, timeout=3)
            chk("", "Redis cache", r.stdout.strip() == "PONG", 5)
        except Exception:
            chk("", "Redis cache", False, 5, "start: systemctl start redis-server")

        # Waydroid
        try:
            r = subprocess.run(["waydroid", "status"], capture_output=True, text=True, timeout=5)
            wd_ok = "RUNNING" in r.stdout or "running" in r.stdout or "active" in r.stdout
            chk("", "Waydroid (Android VM)", wd_ok, 5, "needed for KYC mobile flow")
        except Exception:
            chk("", "Waydroid", False, 5, "optional — needed for KYC")

        # Camoufox
        try:
            from camoufox.sync_api import Camoufox
            chk("", "Camoufox browser engine", True, 10)
        except Exception:
            chk("", "Camoufox browser engine", False, 10, "pip install camoufox")

        pct = int(score / max_score * 100) if max_score > 0 else 0
        lines.append("")
        lines.append(f"  ══════════════════════════════")
        lines.append(f"  READINESS SCORE: {pct}%  ({score}/{max_score} pts)")
        if pct >= 80:
            lines.append("  STATUS: OPERATIONAL — ready for live operations")
            color = GREEN
        elif pct >= 60:
            lines.append("  STATUS: DEGRADED — configure optional services for best results")
            color = YELLOW
        else:
            lines.append("  STATUS: NOT READY — fix critical items above first")
            color = RED
        self.check_results.setPlainText("\n".join(lines))

        self.readiness_lbl.setText(f"Readiness: {pct}%")
        self.readiness_lbl.setStyleSheet(f"color: {color};")

    def _finish(self):
        """Mark first run as done and close."""
        try:
            FIRST_RUN_FLAG.parent.mkdir(parents=True, exist_ok=True)
            FIRST_RUN_FLAG.write_text("done\n")
        except Exception:
            pass
        # Write system health state file
        try:
            import json as _json
            health_dir = Path("/opt/titan/state")
            health_dir.mkdir(parents=True, exist_ok=True)
            (health_dir / "wizard_complete.json").write_text(
                _json.dumps({"wizard_version": "10.0", "completed": True}, indent=2)
            )
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
