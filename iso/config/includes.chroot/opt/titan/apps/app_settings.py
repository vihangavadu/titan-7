#!/usr/bin/env python3
"""
TITAN V9.1 SETTINGS — External Tool Configuration & System Setup
================================================================
Lets the operator configure all external services, API keys, and
system dependencies from a single unified GUI.

6 tabs:
  1. VPN — Mullvad account, relay selection, WireGuard status
  2. AI — Ollama models, endpoints, LLM routing config
  3. SERVICES — Redis, MinIO, ntfy, Xray, Uptime Kuma
  4. BROWSER — Camoufox path, profile directory, extensions
  5. API KEYS — Proxy providers, OSINT tools, payment sandbox
  6. SYSTEM — titan.env editor, paths, versioning, diagnostics
"""

import sys
import os
import json
import subprocess
import shutil
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / "core"))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QGroupBox, QFormLayout,
    QTabWidget, QFrame, QComboBox, QCheckBox, QMessageBox,
    QScrollArea, QPlainTextEdit, QFileDialog, QSpinBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

try:
    from titan_theme import THEME, apply_titan_theme, make_tab_style, make_btn, make_mono_display
    THEME_OK = True
except ImportError:
    THEME_OK = False

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════
ACCENT = "#a855f7"  # Purple for Settings
BG_DARK = "#0a0e17"
BG_CARD = "#111827"
BG_CARD2 = "#1e293b"
TEXT = "#e2e8f0"
TEXT2 = "#64748b"
GREEN = "#22c55e"
YELLOW = "#eab308"
RED = "#ef4444"

TITAN_ROOT = Path("/opt/titan")
TITAN_ENV = TITAN_ROOT / "config" / "titan.env"
LLM_CONFIG = TITAN_ROOT / "config" / "llm_config.json"

# ═══════════════════════════════════════════════════════════════════════════════
# HELPER: Run shell command and return output
# ═══════════════════════════════════════════════════════════════════════════════
def _run(cmd, timeout=10):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip() + r.stderr.strip()
    except Exception as e:
        return str(e)

def _check_service(name):
    try:
        r = subprocess.run(["systemctl", "is-active", name], capture_output=True, text=True, timeout=5)
        return r.stdout.strip() == "active"
    except Exception:
        return False

def _read_env():
    env = {}
    if TITAN_ENV.exists():
        for line in TITAN_ENV.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    return env

def _save_env(env_dict):
    lines = []
    lines.append("# TITAN V9.1 Environment Configuration")
    lines.append(f"# Last updated: {datetime.now().isoformat()}")
    lines.append("")
    for k, v in sorted(env_dict.items()):
        lines.append(f"{k}={v}")
    TITAN_ENV.parent.mkdir(parents=True, exist_ok=True)
    TITAN_ENV.write_text("\n".join(lines) + "\n")


# ═══════════════════════════════════════════════════════════════════════════════
# STATUS CHECK WORKER
# ═══════════════════════════════════════════════════════════════════════════════
class StatusWorker(QThread):
    finished = pyqtSignal(dict)

    def run(self):
        status = {}
        # Mullvad
        try:
            r = subprocess.run(["mullvad", "status"], capture_output=True, text=True, timeout=5)
            status["mullvad"] = r.stdout.strip()
            status["mullvad_ok"] = "Connected" in r.stdout
        except Exception:
            status["mullvad"] = "Not installed"
            status["mullvad_ok"] = False

        # Ollama
        try:
            import requests
            r = requests.get("http://127.0.0.1:11434/api/tags", timeout=3)
            models = r.json().get("models", [])
            status["ollama"] = f"Running — {len(models)} models"
            status["ollama_ok"] = True
            status["ollama_models"] = [m.get("name", "?") for m in models]
        except Exception:
            status["ollama"] = "Not running"
            status["ollama_ok"] = False
            status["ollama_models"] = []

        # Redis
        try:
            r = subprocess.run(["redis-cli", "ping"], capture_output=True, text=True, timeout=3)
            status["redis_ok"] = "PONG" in r.stdout
            status["redis"] = "Running" if status["redis_ok"] else "Not running"
        except Exception:
            status["redis"] = "Not installed"
            status["redis_ok"] = False

        # Xray
        try:
            r = subprocess.run(["xray", "version"], capture_output=True, text=True, timeout=3)
            status["xray"] = r.stdout.split("\n")[0] if r.returncode == 0 else "Not running"
            status["xray_ok"] = r.returncode == 0
        except Exception:
            status["xray"] = "Not installed"
            status["xray_ok"] = False

        # ntfy
        try:
            status["ntfy_ok"] = _check_service("ntfy")
            status["ntfy"] = "Running" if status["ntfy_ok"] else "Stopped"
        except Exception:
            status["ntfy"] = "Not installed"
            status["ntfy_ok"] = False

        # Camoufox
        try:
            r = subprocess.run(["camoufox", "--version"], capture_output=True, text=True, timeout=5)
            status["camoufox"] = r.stdout.strip() or "Installed"
            status["camoufox_ok"] = True
        except Exception:
            # Check pip
            try:
                import camoufox
                status["camoufox"] = f"v{camoufox.__version__}"
                status["camoufox_ok"] = True
            except Exception:
                status["camoufox"] = "Not installed"
                status["camoufox_ok"] = False

        # Disk
        try:
            total, used, free = shutil.disk_usage("/")
            status["disk_free"] = f"{free // (1024**3)} GB free of {total // (1024**3)} GB"
        except Exception:
            status["disk_free"] = "Unknown"

        self.finished.emit(status)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN WINDOW
# ═══════════════════════════════════════════════════════════════════════════════
class TitanSettings(QMainWindow):
    """
    TITAN V9.1 Settings — Configure all external tools and services.
    """

    def __init__(self):
        super().__init__()
        self.status_data = {}
        self.env_data = _read_env()
        self.init_ui()
        self.apply_theme()
        QTimer.singleShot(300, self._refresh_status)

    def apply_theme(self):
        if THEME_OK:
            apply_titan_theme(self, ACCENT)
            self.tabs.setStyleSheet(make_tab_style(ACCENT))
        else:
            self.setStyleSheet(f"background: {BG_DARK}; color: {TEXT};")

    def init_ui(self):
        self.setWindowTitle("TITAN V9.1 — Settings")
        try:
            from titan_icon import set_titan_icon
            set_titan_icon(self, ACCENT)
        except Exception:
            pass
        self.setMinimumSize(1100, 800)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)

        # Header
        hdr = QHBoxLayout()
        title = QLabel("SETTINGS")
        title.setFont(QFont("Inter", 20, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {ACCENT};")
        hdr.addWidget(title)
        hdr.addStretch()

        self.refresh_btn = QPushButton("Refresh Status")
        self.refresh_btn.setStyleSheet(f"background: {ACCENT}; color: white; padding: 8px 16px; border-radius: 6px; font-weight: bold;")
        self.refresh_btn.clicked.connect(self._refresh_status)
        hdr.addWidget(self.refresh_btn)
        layout.addLayout(hdr)

        # Tabs
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self._build_vpn_tab()
        self._build_ai_tab()
        self._build_services_tab()
        self._build_browser_tab()
        self._build_apikeys_tab()
        self._build_system_tab()

    # ═══════════════════════════════════════════════════════════════════════
    # TAB 1: VPN (Mullvad)
    # ═══════════════════════════════════════════════════════════════════════

    def _build_vpn_tab(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(tab)
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        # Mullvad Status
        grp = QGroupBox("Mullvad VPN")
        gf = QVBoxLayout(grp)

        status_row = QHBoxLayout()
        self.mullvad_dot = QLabel("●")
        self.mullvad_dot.setStyleSheet(f"color: {RED};")
        status_row.addWidget(self.mullvad_dot)
        self.mullvad_status = QLabel("Checking...")
        self.mullvad_status.setStyleSheet(f"color: {TEXT};")
        status_row.addWidget(self.mullvad_status)
        status_row.addStretch()
        gf.addLayout(status_row)

        # Account
        form = QFormLayout()
        self.mullvad_account = QLineEdit()
        self.mullvad_account.setPlaceholderText("Enter Mullvad account number (e.g., 1234567890123456)")
        self.mullvad_account.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Account:", self.mullvad_account)

        self.mullvad_relay = QComboBox()
        self.mullvad_relay.addItems(["Auto", "us-nyc", "us-lax", "us-chi", "us-mia", "uk-lon", "de-fra", "nl-ams", "se-sto", "ch-zrh", "jp-tky", "sg-sin", "au-syd"])
        form.addRow("Relay:", self.mullvad_relay)
        gf.addLayout(form)

        # Buttons
        btn_row = QHBoxLayout()
        self.vpn_connect_btn = QPushButton("Connect VPN")
        self.vpn_connect_btn.setStyleSheet(f"background: {GREEN}; color: black; padding: 8px 16px; border-radius: 6px; font-weight: bold;")
        self.vpn_connect_btn.clicked.connect(self._vpn_connect)
        btn_row.addWidget(self.vpn_connect_btn)

        self.vpn_disconnect_btn = QPushButton("Disconnect")
        self.vpn_disconnect_btn.setStyleSheet(f"background: {RED}; color: white; padding: 8px 16px; border-radius: 6px; font-weight: bold;")
        self.vpn_disconnect_btn.clicked.connect(self._vpn_disconnect)
        btn_row.addWidget(self.vpn_disconnect_btn)

        self.vpn_save_btn = QPushButton("Save Account")
        self.vpn_save_btn.setStyleSheet(f"background: {BG_CARD}; color: {TEXT}; padding: 8px 16px; border: 1px solid #334155; border-radius: 6px;")
        self.vpn_save_btn.clicked.connect(self._vpn_save_account)
        btn_row.addWidget(self.vpn_save_btn)
        btn_row.addStretch()
        gf.addLayout(btn_row)

        self.vpn_log = QPlainTextEdit()
        self.vpn_log.setReadOnly(True)
        self.vpn_log.setMaximumHeight(150)
        self.vpn_log.setPlaceholderText("VPN connection log...")
        gf.addWidget(self.vpn_log)

        layout.addWidget(grp)

        # Xray Relay
        xgrp = QGroupBox("Xray Relay (Lucid VPN Fallback)")
        xf = QVBoxLayout(xgrp)
        xform = QFormLayout()
        self.xray_server = QLineEdit()
        self.xray_server.setPlaceholderText("VPS relay address (e.g., relay.yourdomain.com)")
        self.xray_server.setText(self.env_data.get("XRAY_SERVER", ""))
        xform.addRow("Server:", self.xray_server)
        self.xray_port = QSpinBox()
        self.xray_port.setRange(1, 65535)
        self.xray_port.setValue(int(self.env_data.get("XRAY_PORT", "443")))
        xform.addRow("Port:", self.xray_port)
        self.xray_uuid = QLineEdit()
        self.xray_uuid.setPlaceholderText("Xray UUID")
        self.xray_uuid.setText(self.env_data.get("XRAY_UUID", ""))
        xform.addRow("UUID:", self.xray_uuid)
        xf.addLayout(xform)

        xsave = QPushButton("Save Xray Config")
        xsave.setStyleSheet(f"background: {ACCENT}; color: white; padding: 8px 16px; border-radius: 6px; font-weight: bold;")
        xsave.clicked.connect(self._save_xray)
        xf.addWidget(xsave)
        layout.addWidget(xgrp)

        layout.addStretch()
        self.tabs.addTab(scroll, "VPN")

    # ═══════════════════════════════════════════════════════════════════════
    # TAB 2: AI (Ollama)
    # ═══════════════════════════════════════════════════════════════════════

    def _build_ai_tab(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(tab)
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        # Ollama Status
        grp = QGroupBox("Ollama LLM Server")
        gf = QVBoxLayout(grp)

        status_row = QHBoxLayout()
        self.ollama_dot = QLabel("●")
        self.ollama_dot.setStyleSheet(f"color: {RED};")
        status_row.addWidget(self.ollama_dot)
        self.ollama_status = QLabel("Checking...")
        status_row.addWidget(self.ollama_status)
        status_row.addStretch()
        gf.addLayout(status_row)

        form = QFormLayout()
        self.ollama_host = QLineEdit()
        self.ollama_host.setText(self.env_data.get("OLLAMA_HOST", "http://127.0.0.1:11434"))
        form.addRow("Endpoint:", self.ollama_host)
        gf.addLayout(form)

        # Model list
        self.model_list = QPlainTextEdit()
        self.model_list.setReadOnly(True)
        self.model_list.setMaximumHeight(120)
        self.model_list.setPlaceholderText("Loaded models will appear here...")
        gf.addWidget(QLabel("Loaded Models:"))
        gf.addWidget(self.model_list)

        # Pull model
        pull_row = QHBoxLayout()
        self.pull_model_input = QLineEdit()
        self.pull_model_input.setPlaceholderText("Model to pull (e.g., mistral:7b, qwen2.5:7b)")
        pull_row.addWidget(self.pull_model_input)
        pull_btn = QPushButton("Pull Model")
        pull_btn.setStyleSheet(f"background: {GREEN}; color: black; padding: 8px 16px; border-radius: 6px; font-weight: bold;")
        pull_btn.clicked.connect(self._pull_model)
        pull_row.addWidget(pull_btn)
        gf.addLayout(pull_row)

        save_btn = QPushButton("Save Ollama Config")
        save_btn.setStyleSheet(f"background: {ACCENT}; color: white; padding: 8px 16px; border-radius: 6px; font-weight: bold;")
        save_btn.clicked.connect(self._save_ollama)
        gf.addWidget(save_btn)

        layout.addWidget(grp)

        # LLM Routing Config
        rgrp = QGroupBox("LLM Task Routing (llm_config.json)")
        rf = QVBoxLayout(rgrp)
        self.llm_config_edit = QPlainTextEdit()
        self.llm_config_edit.setMinimumHeight(200)
        try:
            if LLM_CONFIG.exists():
                self.llm_config_edit.setPlainText(LLM_CONFIG.read_text())
            else:
                self.llm_config_edit.setPlaceholderText("llm_config.json not found — will be created on save")
        except Exception:
            self.llm_config_edit.setPlaceholderText("Could not read llm_config.json")
        rf.addWidget(self.llm_config_edit)

        llm_save = QPushButton("Save LLM Config")
        llm_save.setStyleSheet(f"background: {ACCENT}; color: white; padding: 8px 16px; border-radius: 6px; font-weight: bold;")
        llm_save.clicked.connect(self._save_llm_config)
        rf.addWidget(llm_save)
        layout.addWidget(rgrp)

        layout.addStretch()
        self.tabs.addTab(scroll, "AI")

    # ═══════════════════════════════════════════════════════════════════════
    # TAB 3: SERVICES (Redis, MinIO, ntfy, Uptime Kuma)
    # ═══════════════════════════════════════════════════════════════════════

    def _build_services_tab(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(tab)
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        # Service status panel
        grp = QGroupBox("Service Status")
        gf = QVBoxLayout(grp)

        self.svc_indicators = {}
        services = [
            ("redis-server", "Redis", "Cache & session store"),
            ("xray", "Xray", "VPN relay protocol"),
            ("ntfy", "ntfy", "Push notifications"),
            ("ollama", "Ollama", "LLM inference server"),
            ("mullvad-daemon", "Mullvad", "VPN daemon"),
        ]
        for svc_name, label, desc in services:
            row = QHBoxLayout()
            dot = QLabel("●")
            dot.setFixedWidth(14)
            dot.setStyleSheet(f"color: {RED};")
            row.addWidget(dot)
            lbl = QLabel(f"{label} — {desc}")
            lbl.setStyleSheet(f"color: {TEXT};")
            row.addWidget(lbl)
            row.addStretch()

            start_btn = QPushButton("Start")
            start_btn.setFixedWidth(60)
            start_btn.setStyleSheet(f"background: {GREEN}; color: black; padding: 4px; border-radius: 4px; font-size: 11px;")
            start_btn.clicked.connect(lambda checked, s=svc_name: self._start_service(s))
            row.addWidget(start_btn)

            stop_btn = QPushButton("Stop")
            stop_btn.setFixedWidth(60)
            stop_btn.setStyleSheet(f"background: {RED}; color: white; padding: 4px; border-radius: 4px; font-size: 11px;")
            stop_btn.clicked.connect(lambda checked, s=svc_name: self._stop_service(s))
            row.addWidget(stop_btn)

            gf.addLayout(row)
            self.svc_indicators[svc_name] = dot

        layout.addWidget(grp)

        # Redis config
        rgrp = QGroupBox("Redis Configuration")
        rf = QFormLayout(rgrp)
        self.redis_url = QLineEdit()
        self.redis_url.setText(self.env_data.get("TITAN_REDIS_URL", "redis://127.0.0.1:6379/0"))
        rf.addRow("Redis URL:", self.redis_url)
        layout.addWidget(rgrp)

        # MinIO config
        mgrp = QGroupBox("MinIO Object Storage")
        mf = QFormLayout(mgrp)
        self.minio_endpoint = QLineEdit()
        self.minio_endpoint.setText(self.env_data.get("TITAN_MINIO_ENDPOINT", "127.0.0.1:9000"))
        mf.addRow("Endpoint:", self.minio_endpoint)
        self.minio_key = QLineEdit()
        self.minio_key.setText(self.env_data.get("TITAN_MINIO_ACCESS_KEY", "titan"))
        mf.addRow("Access Key:", self.minio_key)
        self.minio_secret = QLineEdit()
        self.minio_secret.setEchoMode(QLineEdit.EchoMode.Password)
        self.minio_secret.setText(self.env_data.get("TITAN_MINIO_SECRET_KEY", ""))
        mf.addRow("Secret Key:", self.minio_secret)
        layout.addWidget(mgrp)

        # ntfy config
        ngrp = QGroupBox("ntfy Push Notifications")
        nf = QFormLayout(ngrp)
        self.ntfy_url = QLineEdit()
        self.ntfy_url.setText(self.env_data.get("TITAN_NTFY_URL", "http://127.0.0.1:8090"))
        nf.addRow("Server URL:", self.ntfy_url)
        self.ntfy_topic = QLineEdit()
        self.ntfy_topic.setText(self.env_data.get("TITAN_NTFY_TOPIC", "titan-ops"))
        nf.addRow("Topic:", self.ntfy_topic)
        layout.addWidget(ngrp)

        # Save all services config
        save = QPushButton("Save All Service Config")
        save.setStyleSheet(f"background: {ACCENT}; color: white; padding: 10px 24px; border-radius: 6px; font-weight: bold;")
        save.clicked.connect(self._save_services)
        layout.addWidget(save)

        layout.addStretch()
        self.tabs.addTab(scroll, "SERVICES")

    # ═══════════════════════════════════════════════════════════════════════
    # TAB 4: BROWSER (Camoufox)
    # ═══════════════════════════════════════════════════════════════════════

    def _build_browser_tab(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(tab)
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        grp = QGroupBox("Camoufox Anti-Detect Browser")
        gf = QVBoxLayout(grp)

        status_row = QHBoxLayout()
        self.camofox_dot = QLabel("●")
        self.camofox_dot.setStyleSheet(f"color: {RED};")
        status_row.addWidget(self.camofox_dot)
        self.camofox_status = QLabel("Checking...")
        status_row.addWidget(self.camofox_status)
        status_row.addStretch()
        gf.addLayout(status_row)

        form = QFormLayout()
        self.browser_profiles_dir = QLineEdit()
        self.browser_profiles_dir.setText(self.env_data.get("TITAN_PROFILES_DIR", "/opt/titan/profiles"))
        form.addRow("Profiles Dir:", self.browser_profiles_dir)

        self.browser_extensions_dir = QLineEdit()
        self.browser_extensions_dir.setText(self.env_data.get("TITAN_EXTENSIONS_DIR", "/opt/titan/extensions"))
        form.addRow("Extensions Dir:", self.browser_extensions_dir)

        self.browser_handover = QComboBox()
        self.browser_handover.addItems(["camoufox", "firefox", "chromium"])
        current = self.env_data.get("TITAN_BROWSER", "camoufox")
        idx = self.browser_handover.findText(current)
        if idx >= 0:
            self.browser_handover.setCurrentIndex(idx)
        form.addRow("Default Browser:", self.browser_handover)
        gf.addLayout(form)

        save = QPushButton("Save Browser Config")
        save.setStyleSheet(f"background: {ACCENT}; color: white; padding: 8px 16px; border-radius: 6px; font-weight: bold;")
        save.clicked.connect(self._save_browser)
        gf.addWidget(save)

        layout.addWidget(grp)

        # Ghost Motor config
        gmgrp = QGroupBox("Ghost Motor (Behavioral Engine)")
        gmf = QFormLayout(gmgrp)
        self.gm_model_path = QLineEdit()
        self.gm_model_path.setText(self.env_data.get("GHOST_MOTOR_MODEL", "/opt/titan/models/ghost_motor_v6.onnx"))
        gmf.addRow("ONNX Model:", self.gm_model_path)
        layout.addWidget(gmgrp)

        layout.addStretch()
        self.tabs.addTab(scroll, "BROWSER")

    # ═══════════════════════════════════════════════════════════════════════
    # TAB 5: API KEYS
    # ═══════════════════════════════════════════════════════════════════════

    def _build_apikeys_tab(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(tab)
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        # Proxy providers
        pgrp = QGroupBox("Proxy Providers")
        pf = QFormLayout(pgrp)
        self.proxy_key_fields = {}
        providers = [
            ("PROXY_BRIGHTDATA_KEY", "Bright Data API Key"),
            ("PROXY_OXYLABS_KEY", "Oxylabs API Key"),
            ("PROXY_SMARTPROXY_KEY", "Smartproxy API Key"),
            ("PROXY_IPROYAL_KEY", "IPRoyal API Key"),
        ]
        for env_key, label in providers:
            field = QLineEdit()
            field.setEchoMode(QLineEdit.EchoMode.Password)
            field.setText(self.env_data.get(env_key, ""))
            field.setPlaceholderText(f"Enter {label}")
            pf.addRow(label + ":", field)
            self.proxy_key_fields[env_key] = field
        layout.addWidget(pgrp)

        # Payment sandbox
        sgrp = QGroupBox("Payment Sandbox")
        sf = QFormLayout(sgrp)
        self.sandbox_fields = {}
        sandbox_keys = [
            ("STRIPE_TEST_KEY", "Stripe Test Key (sk_test_...)"),
            ("STRIPE_PUB_KEY", "Stripe Publishable Key (pk_test_...)"),
        ]
        for env_key, label in sandbox_keys:
            field = QLineEdit()
            field.setEchoMode(QLineEdit.EchoMode.Password)
            field.setText(self.env_data.get(env_key, ""))
            field.setPlaceholderText(label)
            sf.addRow(label.split("(")[0].strip() + ":", field)
            self.sandbox_fields[env_key] = field
        layout.addWidget(sgrp)

        # OSINT tools
        ogrp = QGroupBox("OSINT / Intel Tools")
        of = QFormLayout(ogrp)
        self.osint_fields = {}
        osint_keys = [
            ("IPQS_API_KEY", "IPQualityScore API Key"),
            ("SEON_API_KEY", "SEON API Key"),
            ("SHODAN_API_KEY", "Shodan API Key"),
        ]
        for env_key, label in osint_keys:
            field = QLineEdit()
            field.setEchoMode(QLineEdit.EchoMode.Password)
            field.setText(self.env_data.get(env_key, ""))
            field.setPlaceholderText(f"Enter {label}")
            of.addRow(label + ":", field)
            self.osint_fields[env_key] = field
        layout.addWidget(ogrp)

        # Save
        save = QPushButton("Save All API Keys")
        save.setStyleSheet(f"background: {ACCENT}; color: white; padding: 10px 24px; border-radius: 6px; font-weight: bold;")
        save.clicked.connect(self._save_apikeys)
        layout.addWidget(save)

        layout.addStretch()
        self.tabs.addTab(scroll, "API KEYS")

    # ═══════════════════════════════════════════════════════════════════════
    # TAB 6: SYSTEM (titan.env editor, diagnostics)
    # ═══════════════════════════════════════════════════════════════════════

    def _build_system_tab(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(tab)
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        # titan.env raw editor
        grp = QGroupBox("titan.env — Raw Editor")
        gf = QVBoxLayout(grp)
        self.env_editor = QPlainTextEdit()
        self.env_editor.setMinimumHeight(300)
        try:
            if TITAN_ENV.exists():
                self.env_editor.setPlainText(TITAN_ENV.read_text())
            else:
                self.env_editor.setPlaceholderText("titan.env not found — will be created on save")
        except Exception:
            self.env_editor.setPlaceholderText("Could not read titan.env")

        gf.addWidget(self.env_editor)

        btn_row = QHBoxLayout()
        save_env = QPushButton("Save titan.env")
        save_env.setStyleSheet(f"background: {ACCENT}; color: white; padding: 8px 16px; border-radius: 6px; font-weight: bold;")
        save_env.clicked.connect(self._save_raw_env)
        btn_row.addWidget(save_env)

        reload_env = QPushButton("Reload")
        reload_env.setStyleSheet(f"background: {BG_CARD}; color: {TEXT}; padding: 8px 16px; border: 1px solid #334155; border-radius: 6px;")
        reload_env.clicked.connect(self._reload_env)
        btn_row.addWidget(reload_env)
        btn_row.addStretch()
        gf.addLayout(btn_row)
        layout.addWidget(grp)

        # Diagnostics
        dgrp = QGroupBox("System Diagnostics")
        df = QVBoxLayout(dgrp)
        self.diag_output = QPlainTextEdit()
        self.diag_output.setReadOnly(True)
        self.diag_output.setMaximumHeight(150)
        df.addWidget(self.diag_output)

        diag_btn = QPushButton("Run Diagnostics")
        diag_btn.setStyleSheet(f"background: {YELLOW}; color: black; padding: 8px 16px; border-radius: 6px; font-weight: bold;")
        diag_btn.clicked.connect(self._run_diagnostics)
        df.addWidget(diag_btn)
        layout.addWidget(dgrp)

        # Version info
        vgrp = QGroupBox("Version Info")
        vf = QFormLayout(vgrp)
        vf.addRow("Titan OS:", QLabel("V9.1 SINGULARITY"))
        vf.addRow("Core Modules:", QLabel("115"))
        vf.addRow("GUI Apps:", QLabel("9 apps + Launcher"))
        vf.addRow("Author:", QLabel("Dva.12"))
        layout.addWidget(vgrp)

        layout.addStretch()
        self.tabs.addTab(scroll, "SYSTEM")

    # ═══════════════════════════════════════════════════════════════════════
    # ACTIONS
    # ═══════════════════════════════════════════════════════════════════════

    def _refresh_status(self):
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("Checking...")
        self.worker = StatusWorker()
        self.worker.finished.connect(self._on_status)
        self.worker.start()

    def _on_status(self, data):
        self.status_data = data
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("Refresh Status")

        # VPN
        ok = data.get("mullvad_ok", False)
        self.mullvad_dot.setStyleSheet(f"color: {GREEN if ok else RED};")
        self.mullvad_status.setText(data.get("mullvad", "Unknown"))

        # Ollama
        ok = data.get("ollama_ok", False)
        self.ollama_dot.setStyleSheet(f"color: {GREEN if ok else RED};")
        self.ollama_status.setText(data.get("ollama", "Unknown"))
        models = data.get("ollama_models", [])
        self.model_list.setPlainText("\n".join(models) if models else "No models loaded")

        # Camoufox
        ok = data.get("camoufox_ok", False)
        self.camofox_dot.setStyleSheet(f"color: {GREEN if ok else RED};")
        self.camofox_status.setText(data.get("camoufox", "Unknown"))

        # Service indicators
        for svc, dot in self.svc_indicators.items():
            active = _check_service(svc)
            dot.setStyleSheet(f"color: {GREEN if active else RED};")

    def _vpn_connect(self):
        relay = self.mullvad_relay.currentText()
        if relay != "Auto":
            self.vpn_log.appendPlainText(f"Setting relay to {relay}...")
            _run(f"mullvad relay set location {relay}")
        self.vpn_log.appendPlainText("Connecting...")
        out = _run("mullvad connect", timeout=15)
        self.vpn_log.appendPlainText(out or "Connect command sent")
        QTimer.singleShot(3000, self._refresh_status)

    def _vpn_disconnect(self):
        out = _run("mullvad disconnect")
        self.vpn_log.appendPlainText(out or "Disconnected")
        QTimer.singleShot(1000, self._refresh_status)

    def _vpn_save_account(self):
        acct = self.mullvad_account.text().strip()
        if acct:
            out = _run(f"mullvad account login {acct}")
            self.vpn_log.appendPlainText(out or "Account set")
            self.env_data["MULLVAD_ACCOUNT"] = acct
        else:
            self.vpn_log.appendPlainText("No account number entered")

    def _save_xray(self):
        self.env_data["XRAY_SERVER"] = self.xray_server.text().strip()
        self.env_data["XRAY_PORT"] = str(self.xray_port.value())
        self.env_data["XRAY_UUID"] = self.xray_uuid.text().strip()
        _save_env(self.env_data)
        QMessageBox.information(self, "Saved", "Xray config saved to titan.env")

    def _save_ollama(self):
        self.env_data["OLLAMA_HOST"] = self.ollama_host.text().strip()
        _save_env(self.env_data)
        QMessageBox.information(self, "Saved", "Ollama config saved")

    def _pull_model(self):
        model = self.pull_model_input.text().strip()
        if model:
            self.model_list.appendPlainText(f"Pulling {model}... (this may take a while)")
            out = _run(f"ollama pull {model}", timeout=300)
            self.model_list.appendPlainText(out)
            QTimer.singleShot(1000, self._refresh_status)

    def _save_llm_config(self):
        text = self.llm_config_edit.toPlainText()
        try:
            json.loads(text)
            LLM_CONFIG.parent.mkdir(parents=True, exist_ok=True)
            LLM_CONFIG.write_text(text)
            QMessageBox.information(self, "Saved", "LLM config saved")
        except json.JSONDecodeError as e:
            QMessageBox.warning(self, "Invalid JSON", f"Cannot save — invalid JSON:\n{e}")

    def _start_service(self, name):
        _run(f"systemctl start {name}")
        QTimer.singleShot(1000, self._refresh_status)

    def _stop_service(self, name):
        _run(f"systemctl stop {name}")
        QTimer.singleShot(1000, self._refresh_status)

    def _save_services(self):
        self.env_data["TITAN_REDIS_URL"] = self.redis_url.text().strip()
        self.env_data["TITAN_MINIO_ENDPOINT"] = self.minio_endpoint.text().strip()
        self.env_data["TITAN_MINIO_ACCESS_KEY"] = self.minio_key.text().strip()
        self.env_data["TITAN_MINIO_SECRET_KEY"] = self.minio_secret.text().strip()
        self.env_data["TITAN_NTFY_URL"] = self.ntfy_url.text().strip()
        self.env_data["TITAN_NTFY_TOPIC"] = self.ntfy_topic.text().strip()
        _save_env(self.env_data)
        QMessageBox.information(self, "Saved", "All service config saved to titan.env")

    def _save_browser(self):
        self.env_data["TITAN_PROFILES_DIR"] = self.browser_profiles_dir.text().strip()
        self.env_data["TITAN_EXTENSIONS_DIR"] = self.browser_extensions_dir.text().strip()
        self.env_data["TITAN_BROWSER"] = self.browser_handover.currentText()
        self.env_data["GHOST_MOTOR_MODEL"] = self.gm_model_path.text().strip()
        _save_env(self.env_data)
        QMessageBox.information(self, "Saved", "Browser config saved")

    def _save_apikeys(self):
        for key, field in self.proxy_key_fields.items():
            val = field.text().strip()
            if val:
                self.env_data[key] = val
        for key, field in self.sandbox_fields.items():
            val = field.text().strip()
            if val:
                self.env_data[key] = val
        for key, field in self.osint_fields.items():
            val = field.text().strip()
            if val:
                self.env_data[key] = val
        _save_env(self.env_data)
        QMessageBox.information(self, "Saved", "All API keys saved to titan.env")

    def _save_raw_env(self):
        text = self.env_editor.toPlainText()
        try:
            TITAN_ENV.parent.mkdir(parents=True, exist_ok=True)
            TITAN_ENV.write_text(text)
            self.env_data = _read_env()
            QMessageBox.information(self, "Saved", "titan.env saved")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save: {e}")

    def _reload_env(self):
        try:
            if TITAN_ENV.exists():
                self.env_editor.setPlainText(TITAN_ENV.read_text())
                self.env_data = _read_env()
        except Exception as e:
            self.env_editor.setPlainText(f"Error: {e}")

    def _run_diagnostics(self):
        lines = []
        lines.append(f"=== TITAN V9.1 DIAGNOSTICS === {datetime.now().isoformat()}")
        lines.append(f"Disk: {self.status_data.get('disk_free', 'unknown')}")
        lines.append(f"Mullvad: {self.status_data.get('mullvad', 'unknown')}")
        lines.append(f"Ollama: {self.status_data.get('ollama', 'unknown')}")
        lines.append(f"Redis: {self.status_data.get('redis', 'unknown')}")
        lines.append(f"Xray: {self.status_data.get('xray', 'unknown')}")
        lines.append(f"Camoufox: {self.status_data.get('camoufox', 'unknown')}")
        lines.append(f"Core modules: 110")
        lines.append(f"titan.env keys: {len(self.env_data)}")

        # Python package check
        pkgs = ["plyvel", "aioquic", "minio", "curl_cffi", "camoufox", "numpy", "scipy", "flask"]
        for p in pkgs:
            try:
                __import__(p)
                lines.append(f"  pip: {p} OK")
            except ImportError:
                lines.append(f"  pip: {p} MISSING")

        self.diag_output.setPlainText("\n".join(lines))


# ═══════════════════════════════════════════════════════════════════════════════
# STANDALONE LAUNCH
# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = TitanSettings()
    win.show()
    sys.exit(app.exec())
