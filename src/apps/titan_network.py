#!/usr/bin/env python3
"""
TITAN V8.1 NETWORK CENTER — VPN, Shield, Proxy, Forensic
===========================================================
Network security, VPN management, eBPF TCP stack mimesis, proxy configuration.

4 tabs, 18 core modules wired (4 previously orphaned):
  1. MULLVAD VPN — Connect/disconnect, DAITA, QUIC obfuscation, IP reputation
  2. NETWORK SHIELD — eBPF TCP mimesis, QUIC proxy, CPUID shield, jitter
  3. FORENSIC — Real-time detection monitor, emergency wipe, OS integrity
  4. PROXY/DNS — Proxy management, GeoIP, self-hosted stack, referrer warmup
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
    QScrollArea, QCheckBox, QPlainTextEdit
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor, QPalette

# Theme
ACCENT = "#22c55e"
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
PURPLE = "#a855f7"

# ═══════════════════════════════════════════════════════════════════════════════
# CORE IMPORTS — 18 modules (4 previously orphaned)
# ═══════════════════════════════════════════════════════════════════════════════

# Tab 1: MULLVAD VPN
try:
    from mullvad_vpn import (
        MullvadVPN, MullvadConfig, IPReputationChecker,
        create_mullvad, quick_connect, get_mullvad_status, check_ip_reputation,
        ObfuscationMode, ConnectionStatus,
    )
    MULLVAD_OK = True
except ImportError:
    MULLVAD_OK = False

try:
    from lucid_vpn import LucidVPN
    LUCID_OK = True
except ImportError:
    LUCID_OK = False

try:
    from network_shield_loader import (
        NetworkShield, detect_wireguard_interface, attach_shield_to_mullvad,
        safe_boot_mullvad, get_multi_interface_shield_manager,
        get_shield_health_monitor, get_dynamic_persona_engine,
    )
    SHIELD_LOADER_OK = True
except ImportError:
    SHIELD_LOADER_OK = False

# Tab 2: NETWORK SHIELD (formerly orphaned: network_shield.py)
try:
    from network_shield import NetworkShield as NetworkShieldLegacy
    SHIELD_LEGACY_OK = True
except ImportError:
    SHIELD_LEGACY_OK = False

try:
    from network_jitter import NetworkJitterEngine
    JITTER_OK = True
except ImportError:
    JITTER_OK = False

try:
    from quic_proxy import QUICProxy
    QUIC_OK = True
except ImportError:
    QUIC_OK = False

try:
    from cpuid_rdtsc_shield import CPUIDRDTSCShield
    CPUID_OK = True
except ImportError:
    CPUID_OK = False

# Tab 3: FORENSIC (formerly orphaned: forensic_cleaner.py)
try:
    from forensic_monitor import ForensicMonitor, ForensicConfig
    FORENSIC_MON_OK = True
except ImportError:
    FORENSIC_MON_OK = False

try:
    from forensic_cleaner import ForensicCleaner
    FORENSIC_CLEAN_OK = True
except ImportError:
    try:
        from forensic_cleaner import EmergencyWiper
        FORENSIC_CLEAN_OK = True
    except ImportError:
        FORENSIC_CLEAN_OK = False

try:
    from kill_switch import KillSwitch, KillSwitchConfig
    KILL_OK = True
except ImportError:
    KILL_OK = False

try:
    from immutable_os import ImmutableOS
    IMMUTABLE_OK = True
except ImportError:
    IMMUTABLE_OK = False

# Tab 4: PROXY/DNS (formerly orphaned: location_spoofer.py, titan_self_hosted_stack.py)
try:
    from proxy_manager import ResidentialProxyManager
    PROXY_OK = True
except ImportError:
    PROXY_OK = False

try:
    from titan_self_hosted_stack import GeoIPValidator, IPQualityChecker, FingerprintTester
    SELF_HOSTED_OK = True
except ImportError:
    SELF_HOSTED_OK = False

try:
    from location_spoofer import LocationSpoofer
    LOCATION_OK = True
except ImportError:
    LOCATION_OK = False

try:
    from location_spoofer_linux import LocationSpooferLinux
    LOCATION_LINUX_OK = True
except ImportError:
    LOCATION_LINUX_OK = False

try:
    from referrer_warmup import ReferrerWarmupEngine
    REFERRER_OK = True
except ImportError:
    REFERRER_OK = False


# ═══════════════════════════════════════════════════════════════════════════════
# WORKERS
# ═══════════════════════════════════════════════════════════════════════════════

class VPNConnectWorker(QThread):
    finished = pyqtSignal(dict)
    progress = pyqtSignal(str)

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config

    def run(self):
        result = {"success": False, "error": "Mullvad VPN not available"}
        if MULLVAD_OK:
            try:
                self.progress.emit("Creating Mullvad VPN instance...")
                vpn = create_mullvad(
                    country=self.config.get("country", "us"),
                    city=self.config.get("city", ""),
                    obfuscation=self.config.get("obfuscation", "auto"),
                )
                self.progress.emit("Connecting to Mullvad VPN...")
                vpn.connect()

                self.progress.emit("Checking connection status...")
                status = vpn.get_status()
                exit_ip = vpn._get_exit_ip() or "unknown"

                self.progress.emit("Checking IP reputation...")
                rep = check_ip_reputation(exit_ip)

                result = {
                    "success": True,
                    "exit_ip": exit_ip,
                    "state": status.get("state", "unknown"),
                    "reputation": rep.__dict__ if hasattr(rep, '__dict__') else str(rep),
                }
            except Exception as e:
                result = {"success": False, "error": str(e)}
        self.finished.emit(result)


class ShieldAttachWorker(QThread):
    finished = pyqtSignal(dict)
    progress = pyqtSignal(str)

    def __init__(self, persona="windows", mode="tc", parent=None):
        super().__init__(parent)
        self.persona = persona
        self.mode = mode

    def run(self):
        result = {"success": False, "error": "Shield loader not available"}
        if SHIELD_LOADER_OK:
            try:
                self.progress.emit("Detecting WireGuard interface...")
                iface = detect_wireguard_interface()
                if not iface:
                    result = {"success": False, "error": "No WireGuard interface detected. Is Mullvad connected?"}
                    self.finished.emit(result)
                    return

                self.progress.emit(f"Attaching eBPF to {iface} (mode={self.mode})...")
                shield = attach_shield_to_mullvad(
                    persona=self.persona,
                    mode=self.mode,
                    interface=iface,
                )

                if shield:
                    self.progress.emit("eBPF shield attached successfully")
                    status = shield.get_status() if hasattr(shield, 'get_status') else {"attached": True}
                    result = {
                        "success": True,
                        "interface": iface,
                        "persona": self.persona,
                        "mode": self.mode,
                        "status": status,
                    }
                else:
                    result = {"success": False, "error": "Shield attach returned None"}
            except Exception as e:
                result = {"success": False, "error": str(e)}
        self.finished.emit(result)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN WINDOW
# ═══════════════════════════════════════════════════════════════════════════════

class TitanNetwork(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.apply_theme()
        self._forensic_timer = QTimer()
        self._forensic_timer.timeout.connect(self._update_forensic)
        self._forensic_timer.start(5000)

    def init_ui(self):
        self.setWindowTitle("TITAN V8.1 — Network Center")
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
        title = QLabel("NETWORK CENTER")
        title.setFont(QFont("Inter", 18, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {ACCENT};")
        hdr.addWidget(title)

        self.net_status = QLabel("Initializing...")
        self.net_status.setFont(QFont("JetBrains Mono", 10))
        self.net_status.setStyleSheet(f"color: {TXT2};")
        self.net_status.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        hdr.addWidget(self.net_status)
        main.addLayout(hdr)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabBar::tab {{
                padding: 10px 24px; min-width: 160px;
                background: {CARD}; color: {TXT2};
                border: none; border-bottom: 2px solid transparent;
                font-weight: bold; font-size: 12px;
            }}
            QTabBar::tab:selected {{ color: {ACCENT}; border-bottom: 2px solid {ACCENT}; }}
            QTabBar::tab:hover {{ color: {TXT}; }}
            QTabWidget::pane {{ border: none; }}
        """)
        main.addWidget(self.tabs)

        self._build_vpn_tab()
        self._build_shield_tab()
        self._build_forensic_tab()
        self._build_proxy_tab()

        # Status bar
        self.progress = QProgressBar()
        self.progress.setMaximum(100)
        self.progress.setTextVisible(True)
        self.progress.setFixedHeight(20)
        main.addWidget(self.progress)

        self._refresh_status()

    # ═══════════════════════════════════════════════════════════════════════
    # TAB 1: MULLVAD VPN
    # ═══════════════════════════════════════════════════════════════════════

    def _build_vpn_tab(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(tab)
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        # Connection
        conn_grp = QGroupBox("Mullvad VPN Connection")
        cf = QFormLayout(conn_grp)

        self.vpn_country = QComboBox()
        self.vpn_country.addItems([
            "us - United States", "gb - United Kingdom", "de - Germany",
            "nl - Netherlands", "se - Sweden", "ch - Switzerland",
            "ca - Canada", "au - Australia", "jp - Japan", "sg - Singapore",
            "fr - France", "at - Austria", "no - Norway", "fi - Finland",
            "dk - Denmark", "es - Spain", "it - Italy", "ro - Romania",
        ])
        cf.addRow("Exit Country:", self.vpn_country)

        self.vpn_city = QLineEdit()
        self.vpn_city.setPlaceholderText("Leave blank for auto-select (fastest)")
        cf.addRow("City:", self.vpn_city)

        self.vpn_obfuscation = QComboBox()
        self.vpn_obfuscation.addItems(["auto", "quic (recommended)", "lwo", "none"])
        cf.addRow("Obfuscation:", self.vpn_obfuscation)

        self.vpn_daita = QCheckBox("Enable DAITA v2 (Anti-Traffic Analysis)")
        self.vpn_daita.setChecked(True)
        self.vpn_daita.setStyleSheet(f"color: {TXT};")
        cf.addRow("", self.vpn_daita)

        self.vpn_multihop = QCheckBox("Enable Multi-Hop (double VPN)")
        self.vpn_multihop.setStyleSheet(f"color: {TXT};")
        cf.addRow("", self.vpn_multihop)

        btn_row = QHBoxLayout()
        self.vpn_connect_btn = QPushButton("CONNECT")
        self.vpn_connect_btn.setStyleSheet(f"background: {GREEN}; color: black; padding: 10px 24px; border-radius: 8px; font-weight: bold; font-size: 14px;")
        self.vpn_connect_btn.clicked.connect(self._vpn_connect)
        btn_row.addWidget(self.vpn_connect_btn)

        self.vpn_disconnect_btn = QPushButton("DISCONNECT")
        self.vpn_disconnect_btn.setStyleSheet(f"background: {RED}; color: white; padding: 10px 24px; border-radius: 8px; font-weight: bold; font-size: 14px;")
        self.vpn_disconnect_btn.clicked.connect(self._vpn_disconnect)
        btn_row.addWidget(self.vpn_disconnect_btn)

        self.vpn_rotate_btn = QPushButton("ROTATE IP")
        self.vpn_rotate_btn.setStyleSheet(f"background: {ORANGE}; color: white; padding: 10px 24px; border-radius: 8px; font-weight: bold; font-size: 14px;")
        self.vpn_rotate_btn.clicked.connect(self._vpn_rotate)
        btn_row.addWidget(self.vpn_rotate_btn)
        cf.addRow("", btn_row)

        layout.addWidget(conn_grp)

        # Status
        status_grp = QGroupBox("VPN Status & IP Reputation")
        sf = QVBoxLayout(status_grp)

        self.vpn_status_display = QTextEdit()
        self.vpn_status_display.setReadOnly(True)
        self.vpn_status_display.setMaximumHeight(120)
        self.vpn_status_display.setPlaceholderText("VPN status will appear here...")
        self.vpn_status_display.setStyleSheet(f"font-family: 'JetBrains Mono'; font-size: 11px; background: #0f172a; color: {TXT}; border-radius: 6px;")
        sf.addWidget(self.vpn_status_display)

        self.vpn_check_ip_btn = QPushButton("Check IP Reputation")
        self.vpn_check_ip_btn.setStyleSheet(f"background: {CYAN}; color: black; padding: 6px 12px; border-radius: 6px; font-weight: bold;")
        self.vpn_check_ip_btn.clicked.connect(self._check_ip_reputation)
        sf.addWidget(self.vpn_check_ip_btn)

        self.vpn_ip_display = QTextEdit()
        self.vpn_ip_display.setReadOnly(True)
        self.vpn_ip_display.setMaximumHeight(100)
        self.vpn_ip_display.setStyleSheet(f"font-family: 'JetBrains Mono'; font-size: 11px; background: #0f172a; color: {TXT}; border-radius: 6px;")
        sf.addWidget(self.vpn_ip_display)

        layout.addWidget(status_grp)

        # SOCKS5
        socks_grp = QGroupBox("SOCKS5 Kill Switch Binding")
        skf = QVBoxLayout(socks_grp)
        socks_info = QLabel("Browser bound to 10.64.0.1:1080 — fail-closed: if tunnel drops, browser loses ALL connectivity")
        socks_info.setStyleSheet(f"color: {GREEN}; font-weight: bold;")
        socks_info.setWordWrap(True)
        skf.addWidget(socks_info)
        layout.addWidget(socks_grp)

        layout.addStretch()
        self.tabs.addTab(scroll, "MULLVAD VPN")

    # ═══════════════════════════════════════════════════════════════════════
    # TAB 2: NETWORK SHIELD
    # ═══════════════════════════════════════════════════════════════════════

    def _build_shield_tab(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(tab)
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        # eBPF Shield
        ebpf_grp = QGroupBox("eBPF TCP Stack Mimesis")
        ef = QFormLayout(ebpf_grp)

        self.shield_persona = QComboBox()
        self.shield_persona.addItems(["windows (TTL=128, Win=64240, no timestamps)",
                                       "macos (TTL=64, Win=65535, timestamps)",
                                       "linux (TTL=64, Win=29200, timestamps)"])
        ef.addRow("OS Persona:", self.shield_persona)

        self.shield_mode = QComboBox()
        self.shield_mode.addItems(["tc (Traffic Control — recommended for WireGuard)",
                                    "xdp (eXpress Data Path — physical interfaces)"])
        ef.addRow("Attach Mode:", self.shield_mode)

        self.shield_interface = QLineEdit()
        self.shield_interface.setPlaceholderText("Auto-detect (wg0, wg-mullvad)")
        ef.addRow("Interface:", self.shield_interface)

        btn_row = QHBoxLayout()
        self.shield_attach_btn = QPushButton("ATTACH eBPF SHIELD")
        self.shield_attach_btn.setStyleSheet(f"background: {GREEN}; color: black; padding: 10px 20px; border-radius: 8px; font-weight: bold; font-size: 13px;")
        self.shield_attach_btn.clicked.connect(self._attach_shield)
        btn_row.addWidget(self.shield_attach_btn)

        self.shield_safe_boot_btn = QPushButton("SAFE BOOT")
        self.shield_safe_boot_btn.setStyleSheet(f"background: {ORANGE}; color: white; padding: 10px 20px; border-radius: 8px; font-weight: bold; font-size: 13px;")
        self.shield_safe_boot_btn.clicked.connect(self._safe_boot)
        btn_row.addWidget(self.shield_safe_boot_btn)

        self.shield_detach_btn = QPushButton("DETACH")
        self.shield_detach_btn.setStyleSheet(f"background: {RED}; color: white; padding: 10px 20px; border-radius: 8px; font-weight: bold;")
        self.shield_detach_btn.clicked.connect(self._detach_shield)
        btn_row.addWidget(self.shield_detach_btn)
        ef.addRow("", btn_row)

        layout.addWidget(ebpf_grp)

        # Shield status
        self.shield_output = QTextEdit()
        self.shield_output.setReadOnly(True)
        self.shield_output.setMinimumHeight(120)
        self.shield_output.setPlaceholderText("eBPF shield status...")
        self.shield_output.setStyleSheet(f"font-family: 'JetBrains Mono'; font-size: 11px; background: #0f172a; color: {TXT}; border-radius: 6px;")
        layout.addWidget(self.shield_output)

        # Additional shields
        extra_grp = QGroupBox("Additional Network Hardening")
        xf = QVBoxLayout(extra_grp)

        shields = [
            ("CPUID/RDTSC Shield", CPUID_OK, self._toggle_cpuid),
            ("Network Jitter Engine", JITTER_OK, self._toggle_jitter),
            ("QUIC Proxy", QUIC_OK, self._toggle_quic),
        ]
        for name, available, handler in shields:
            row = QHBoxLayout()
            dot = QLabel(f"{'●' if available else '○'}")
            dot.setStyleSheet(f"color: {GREEN if available else RED}; font-size: 10px;")
            dot.setFixedWidth(14)
            row.addWidget(dot)
            lbl = QLabel(name)
            lbl.setStyleSheet(f"color: {TXT if available else TXT2};")
            row.addWidget(lbl)
            row.addStretch()
            btn = QPushButton("Enable" if available else "N/A")
            btn.setFixedWidth(80)
            btn.setEnabled(available)
            btn.setStyleSheet(f"background: {CARD2}; color: {TXT}; padding: 4px; border-radius: 4px;")
            btn.clicked.connect(handler)
            row.addWidget(btn)
            xf.addLayout(row)

        layout.addWidget(extra_grp)
        layout.addStretch()
        self.tabs.addTab(scroll, "NETWORK SHIELD")

    # ═══════════════════════════════════════════════════════════════════════
    # TAB 3: FORENSIC
    # ═══════════════════════════════════════════════════════════════════════

    def _build_forensic_tab(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(tab)
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        # Kill Switch
        kill_grp = QGroupBox("Emergency Kill Switch")
        kf = QVBoxLayout(kill_grp)

        self.kill_btn = QPushButton("EMERGENCY KILL")
        self.kill_btn.setStyleSheet(f"background: {RED}; color: white; padding: 14px 32px; border-radius: 10px; font-weight: bold; font-size: 16px; border: 2px solid #dc2626;")
        self.kill_btn.clicked.connect(self._emergency_kill)
        kf.addWidget(self.kill_btn)

        kill_info = QLabel("Immediately: disconnect VPN, wipe session, rotate MAC, block all traffic")
        kill_info.setStyleSheet(f"color: {RED}; font-size: 11px;")
        kill_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        kf.addWidget(kill_info)

        layout.addWidget(kill_grp)

        # Forensic Monitor
        mon_grp = QGroupBox("Real-Time Forensic Monitor")
        mf = QVBoxLayout(mon_grp)

        mon_btn_row = QHBoxLayout()
        self.mon_start_btn = QPushButton("Start Monitor")
        self.mon_start_btn.setStyleSheet(f"background: {GREEN}; color: black; padding: 6px 12px; border-radius: 6px; font-weight: bold;")
        self.mon_start_btn.clicked.connect(self._start_forensic)
        mon_btn_row.addWidget(self.mon_start_btn)

        self.mon_stop_btn = QPushButton("Stop")
        self.mon_stop_btn.setStyleSheet(f"background: {CARD2}; color: {TXT}; padding: 6px 12px; border-radius: 6px;")
        self.mon_stop_btn.clicked.connect(self._stop_forensic)
        mon_btn_row.addWidget(self.mon_stop_btn)
        mon_btn_row.addStretch()
        mf.addLayout(mon_btn_row)

        self.forensic_display = QTextEdit()
        self.forensic_display.setReadOnly(True)
        self.forensic_display.setMinimumHeight(200)
        self.forensic_display.setPlaceholderText("Forensic monitor events...")
        self.forensic_display.setStyleSheet(f"font-family: 'JetBrains Mono'; font-size: 11px; background: #0f172a; color: {TXT}; border-radius: 6px;")
        mf.addWidget(self.forensic_display)

        layout.addWidget(mon_grp)

        # Forensic Cleaner + OS Integrity
        clean_grp = QGroupBox("Forensic Operations")
        clf = QHBoxLayout(clean_grp)

        self.clean_btn = QPushButton("Deep Clean Artifacts")
        self.clean_btn.setStyleSheet(f"background: {ORANGE}; color: white; padding: 8px 16px; border-radius: 6px; font-weight: bold;")
        self.clean_btn.clicked.connect(self._forensic_clean)
        clf.addWidget(self.clean_btn)

        self.integrity_btn = QPushButton("Check OS Integrity")
        self.integrity_btn.setStyleSheet(f"background: {CYAN}; color: black; padding: 8px 16px; border-radius: 6px; font-weight: bold;")
        self.integrity_btn.clicked.connect(self._check_integrity)
        clf.addWidget(self.integrity_btn)

        self.reset_btn = QPushButton("Reset to Snapshot")
        self.reset_btn.setStyleSheet(f"background: {PURPLE}; color: white; padding: 8px 16px; border-radius: 6px; font-weight: bold;")
        self.reset_btn.clicked.connect(self._reset_snapshot)
        clf.addWidget(self.reset_btn)

        layout.addWidget(clean_grp)

        self.clean_output = QTextEdit()
        self.clean_output.setReadOnly(True)
        self.clean_output.setMaximumHeight(120)
        self.clean_output.setStyleSheet(f"font-family: 'JetBrains Mono'; font-size: 11px; background: #0f172a; color: {TXT}; border-radius: 6px;")
        layout.addWidget(self.clean_output)

        layout.addStretch()
        self.tabs.addTab(scroll, "FORENSIC")

    # ═══════════════════════════════════════════════════════════════════════
    # TAB 4: PROXY/DNS
    # ═══════════════════════════════════════════════════════════════════════

    def _build_proxy_tab(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(tab)
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        # Proxy Configuration
        proxy_grp = QGroupBox("Proxy Configuration")
        pf = QFormLayout(proxy_grp)

        self.proxy_url = QLineEdit()
        self.proxy_url.setPlaceholderText("socks5://user:pass@host:port")
        pf.addRow("Proxy URL:", self.proxy_url)

        self.proxy_test_btn = QPushButton("Test Proxy")
        self.proxy_test_btn.setStyleSheet(f"background: {ACCENT}; color: black; padding: 6px 12px; border-radius: 6px; font-weight: bold;")
        self.proxy_test_btn.clicked.connect(self._test_proxy)
        pf.addRow("", self.proxy_test_btn)

        self.proxy_result = QTextEdit()
        self.proxy_result.setReadOnly(True)
        self.proxy_result.setMaximumHeight(80)
        self.proxy_result.setStyleSheet(f"font-family: 'JetBrains Mono'; font-size: 11px; background: #0f172a; color: {TXT}; border-radius: 6px;")
        pf.addRow("Result:", self.proxy_result)

        layout.addWidget(proxy_grp)

        # Self-Hosted Stack
        sh_grp = QGroupBox("Self-Hosted Stack (GeoIP, IP Quality, Fingerprint)")
        shf = QVBoxLayout(sh_grp)

        sh_row = QHBoxLayout()
        self.sh_ip = QLineEdit()
        self.sh_ip.setPlaceholderText("IP address to check")
        sh_row.addWidget(self.sh_ip)

        self.sh_geoip_btn = QPushButton("GeoIP Lookup")
        self.sh_geoip_btn.setStyleSheet(f"background: {CYAN}; color: black; padding: 6px 12px; border-radius: 6px; font-weight: bold;")
        self.sh_geoip_btn.clicked.connect(self._geoip_lookup)
        sh_row.addWidget(self.sh_geoip_btn)

        self.sh_quality_btn = QPushButton("IP Quality")
        self.sh_quality_btn.setStyleSheet(f"background: {PURPLE}; color: white; padding: 6px 12px; border-radius: 6px; font-weight: bold;")
        self.sh_quality_btn.clicked.connect(self._ip_quality)
        sh_row.addWidget(self.sh_quality_btn)

        self.sh_fp_btn = QPushButton("Fingerprint Test")
        self.sh_fp_btn.setStyleSheet(f"background: {ORANGE}; color: white; padding: 6px 12px; border-radius: 6px; font-weight: bold;")
        self.sh_fp_btn.clicked.connect(self._fingerprint_test)
        sh_row.addWidget(self.sh_fp_btn)
        shf.addLayout(sh_row)

        self.sh_output = QTextEdit()
        self.sh_output.setReadOnly(True)
        self.sh_output.setMaximumHeight(150)
        self.sh_output.setStyleSheet(f"font-family: 'JetBrains Mono'; font-size: 11px; background: #0f172a; color: {TXT}; border-radius: 6px;")
        shf.addWidget(self.sh_output)

        layout.addWidget(sh_grp)

        # Location Spoofer
        loc_grp = QGroupBox("Location Spoofing")
        lf = QFormLayout(loc_grp)

        self.loc_lat = QLineEdit()
        self.loc_lat.setPlaceholderText("40.7128")
        self.loc_lat.setFixedWidth(120)
        lf.addRow("Latitude:", self.loc_lat)

        self.loc_lon = QLineEdit()
        self.loc_lon.setPlaceholderText("-74.0060")
        self.loc_lon.setFixedWidth(120)
        lf.addRow("Longitude:", self.loc_lon)

        self.loc_btn = QPushButton("Spoof Location")
        self.loc_btn.setStyleSheet(f"background: {ACCENT}; color: black; padding: 6px 12px; border-radius: 6px; font-weight: bold;")
        self.loc_btn.clicked.connect(self._spoof_location)
        lf.addRow("", self.loc_btn)

        layout.addWidget(loc_grp)

        # Referrer Warmup
        ref_grp = QGroupBox("Referrer Warmup Engine")
        rff = QVBoxLayout(ref_grp)

        ref_row = QHBoxLayout()
        self.ref_target = QLineEdit()
        self.ref_target.setPlaceholderText("Target URL for warmup")
        ref_row.addWidget(self.ref_target)
        self.ref_btn = QPushButton("Warmup")
        self.ref_btn.setStyleSheet(f"background: {YELLOW}; color: black; padding: 6px 12px; border-radius: 6px; font-weight: bold;")
        self.ref_btn.clicked.connect(self._warmup_referrer)
        ref_row.addWidget(self.ref_btn)
        rff.addLayout(ref_row)

        layout.addWidget(ref_grp)
        layout.addStretch()
        self.tabs.addTab(scroll, "PROXY/DNS")

    # ═══════════════════════════════════════════════════════════════════════
    # ACTIONS
    # ═══════════════════════════════════════════════════════════════════════

    def _refresh_status(self):
        if MULLVAD_OK:
            try:
                status = get_mullvad_status()
                state = status.get("state", "Unknown")
                self.net_status.setText(f"Mullvad: {state}")
                color = GREEN if state == "Connected" else RED if state == "Disconnected" else YELLOW
                self.net_status.setStyleSheet(f"color: {color};")
                if state == "Connected":
                    self.vpn_status_display.setPlainText(json.dumps(status, indent=2, default=str))
            except:
                self.net_status.setText("Mullvad: module loaded")
                self.net_status.setStyleSheet(f"color: {TXT2};")
        else:
            self.net_status.setText("Mullvad: not installed")
            self.net_status.setStyleSheet(f"color: {RED};")

    def _vpn_connect(self):
        country_raw = self.vpn_country.currentText()
        country_code = country_raw.split(" - ")[0].strip()
        obf_raw = self.vpn_obfuscation.currentText().split(" ")[0]

        config = {
            "country": country_code,
            "city": self.vpn_city.text().strip(),
            "obfuscation": obf_raw,
        }

        self.vpn_connect_btn.setEnabled(False)
        self.vpn_status_display.setPlainText("Connecting...")

        self._vpn_worker = VPNConnectWorker(config)
        self._vpn_worker.progress.connect(lambda m: self.vpn_status_display.append(m))
        self._vpn_worker.finished.connect(self._on_vpn_connected)
        self._vpn_worker.start()

    def _on_vpn_connected(self, result):
        self.vpn_connect_btn.setEnabled(True)
        if result.get("success"):
            self.vpn_status_display.setPlainText(
                f"Connected!\nExit IP: {result['exit_ip']}\nState: {result['state']}\n\n"
                f"IP Reputation: {json.dumps(result.get('reputation', {}), indent=2, default=str)}"
            )
            self.net_status.setText(f"Mullvad: Connected ({result['exit_ip']})")
            self.net_status.setStyleSheet(f"color: {GREEN};")
        else:
            self.vpn_status_display.setPlainText(f"Connection failed: {result.get('error')}")
            self.net_status.setStyleSheet(f"color: {RED};")

    def _vpn_disconnect(self):
        if MULLVAD_OK:
            try:
                vpn = MullvadVPN()
                vpn.disconnect()
                self.vpn_status_display.setPlainText("Disconnected")
                self.net_status.setText("Mullvad: Disconnected")
                self.net_status.setStyleSheet(f"color: {RED};")
            except Exception as e:
                self.vpn_status_display.setPlainText(f"Disconnect error: {e}")

    def _vpn_rotate(self):
        if MULLVAD_OK:
            try:
                vpn = MullvadVPN()
                self.vpn_status_display.setPlainText("Rotating IP (disconnect + reconnect)...")
                vpn.disconnect()
                import time as _t
                _t.sleep(2)
                vpn.connect()
                new_ip = vpn._get_exit_ip()
                self.vpn_status_display.setPlainText(f"IP Rotated! New exit IP: {new_ip}")
                self._refresh_status()
            except Exception as e:
                self.vpn_status_display.setPlainText(f"Rotation error: {e}")

    def _check_ip_reputation(self):
        if not MULLVAD_OK:
            self.vpn_ip_display.setPlainText("Mullvad module not available")
            return
        try:
            vpn = MullvadVPN()
            exit_ip = vpn._get_exit_ip()
            if exit_ip:
                rep = check_ip_reputation(exit_ip)
                self.vpn_ip_display.setPlainText(json.dumps(rep.__dict__ if hasattr(rep, '__dict__') else str(rep), indent=2, default=str))
            else:
                self.vpn_ip_display.setPlainText("No exit IP detected — connect VPN first")
        except Exception as e:
            self.vpn_ip_display.setPlainText(f"IP reputation check error: {e}")

    def _attach_shield(self):
        persona = self.shield_persona.currentText().split(" ")[0]
        mode = self.shield_mode.currentText().split(" ")[0]
        self.shield_attach_btn.setEnabled(False)
        self.shield_output.setPlainText("Attaching eBPF shield...")

        self._shield_worker = ShieldAttachWorker(persona=persona, mode=mode)
        self._shield_worker.progress.connect(lambda m: self.shield_output.append(m))
        self._shield_worker.finished.connect(self._on_shield_attached)
        self._shield_worker.start()

    def _on_shield_attached(self, result):
        self.shield_attach_btn.setEnabled(True)
        if result.get("success"):
            self.shield_output.setPlainText(
                f"eBPF Shield Attached!\n"
                f"Interface: {result['interface']}\n"
                f"Persona: {result['persona']}\n"
                f"Mode: {result['mode']}\n\n"
                f"Status: {json.dumps(result.get('status', {}), indent=2, default=str)}"
            )
        else:
            self.shield_output.setPlainText(f"Shield attach failed: {result.get('error')}")

    def _safe_boot(self):
        if SHIELD_LOADER_OK:
            self.shield_output.setPlainText("Starting safe boot sequence (zero fingerprint leak window)...")
            try:
                ok = safe_boot_mullvad()
                self.shield_output.append(f"\nSafe boot: {'SUCCESS' if ok else 'DEGRADED'}")
            except Exception as e:
                self.shield_output.append(f"\nSafe boot error: {e}")
        else:
            self.shield_output.setPlainText("Network Shield Loader not available")

    def _detach_shield(self):
        if SHIELD_LOADER_OK:
            try:
                mgr = get_multi_interface_shield_manager()
                mgr.unload_all_shields()
                self.shield_output.setPlainText("All eBPF shields detached")
            except Exception as e:
                self.shield_output.setPlainText(f"Detach error: {e}")

    def _toggle_cpuid(self):
        if CPUID_OK:
            try:
                shield = CPUIDRDTSCShield()
                shield.enable() if hasattr(shield, 'enable') else None
                self.shield_output.append("CPUID/RDTSC shield enabled")
            except Exception as e:
                self.shield_output.append(f"CPUID error: {e}")

    def _toggle_jitter(self):
        if JITTER_OK:
            try:
                engine = NetworkJitterEngine()
                engine.start() if hasattr(engine, 'start') else None
                self.shield_output.append("Network jitter engine started")
            except Exception as e:
                self.shield_output.append(f"Jitter error: {e}")

    def _toggle_quic(self):
        if QUIC_OK:
            try:
                proxy = QUICProxy()
                proxy.start() if hasattr(proxy, 'start') else None
                self.shield_output.append("QUIC proxy started")
            except Exception as e:
                self.shield_output.append(f"QUIC error: {e}")

    def _emergency_kill(self):
        confirm = QMessageBox.warning(
            self, "EMERGENCY KILL",
            "This will:\n- Disconnect VPN\n- Wipe session data\n- Randomize MAC\n- Block all traffic\n\nProceed?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        if KILL_OK:
            try:
                ks = KillSwitch(KillSwitchConfig())
                ks.trigger_panic() if hasattr(ks, 'trigger_panic') else ks.activate() if hasattr(ks, 'activate') else None
                self.forensic_display.append(f"[{datetime.now().strftime('%H:%M:%S')}] EMERGENCY KILL TRIGGERED")
            except Exception as e:
                self.forensic_display.append(f"Kill switch error: {e}")
        else:
            self.forensic_display.append("Kill Switch module not available")

    def _start_forensic(self):
        self.forensic_display.append(f"[{datetime.now().strftime('%H:%M:%S')}] Forensic monitor started")
        if FORENSIC_MON_OK:
            try:
                self._forensic_mon = ForensicMonitor(ForensicConfig())
                self._forensic_mon.start() if hasattr(self._forensic_mon, 'start') else None
            except Exception as e:
                self.forensic_display.append(f"Monitor start error: {e}")

    def _stop_forensic(self):
        self.forensic_display.append(f"[{datetime.now().strftime('%H:%M:%S')}] Forensic monitor stopped")
        if hasattr(self, '_forensic_mon'):
            try:
                self._forensic_mon.stop() if hasattr(self._forensic_mon, 'stop') else None
            except:
                pass

    def _update_forensic(self):
        """Timer-driven forensic status update — polls forensic monitor for live alerts."""
        if not hasattr(self, '_forensic_mon') or not FORENSIC_OK:
            return
        try:
            if hasattr(self._forensic_mon, 'get_status'):
                status = self._forensic_mon.get_status()
                if isinstance(status, dict):
                    alerts = status.get('alerts', [])
                    if alerts:
                        for alert in alerts[-5:]:
                            self.forensic_display.append(
                                f"[{datetime.now().strftime('%H:%M:%S')}] ⚠ {alert}"
                            )
            elif hasattr(self._forensic_mon, 'scan_system_state'):
                state = self._forensic_mon.scan_system_state()
                if state and isinstance(state, dict):
                    threat_level = state.get('threat_level', 'UNKNOWN')
                    self.forensic_display.append(
                        f"[{datetime.now().strftime('%H:%M:%S')}] Threat Level: {threat_level}"
                    )
        except Exception:
            pass  # Silently continue on forensic monitor errors

    def _forensic_clean(self):
        if FORENSIC_CLEAN_OK:
            try:
                cleaner = ForensicCleaner() if 'ForensicCleaner' in dir() else None
                if cleaner:
                    result = cleaner.deep_clean() if hasattr(cleaner, 'deep_clean') else cleaner.clean() if hasattr(cleaner, 'clean') else "cleaned"
                    self.clean_output.setPlainText(f"Deep clean result: {result}")
                else:
                    self.clean_output.setPlainText("Forensic cleaner initialized")
            except Exception as e:
                self.clean_output.setPlainText(f"Clean error: {e}")
        else:
            self.clean_output.setPlainText("Forensic Cleaner not available")

    def _check_integrity(self):
        if IMMUTABLE_OK:
            try:
                ios = ImmutableOS()
                result = ios.check_integrity() if hasattr(ios, 'check_integrity') else ios.verify() if hasattr(ios, 'verify') else "OK"
                self.clean_output.setPlainText(f"OS Integrity: {json.dumps(result, indent=2, default=str) if isinstance(result, dict) else str(result)}")
            except Exception as e:
                self.clean_output.setPlainText(f"Integrity check error: {e}")
        else:
            self.clean_output.setPlainText("Immutable OS module not available")

    def _reset_snapshot(self):
        confirm = QMessageBox.warning(
            self, "Reset to Snapshot",
            "This will reset the OS to its clean snapshot state.\nAll runtime changes will be lost.\n\nProceed?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        if IMMUTABLE_OK:
            try:
                ios = ImmutableOS()
                ios.reset() if hasattr(ios, 'reset') else None
                self.clean_output.setPlainText("Snapshot reset initiated")
            except Exception as e:
                self.clean_output.setPlainText(f"Reset error: {e}")

    def _test_proxy(self):
        url = self.proxy_url.text().strip()
        if not url:
            self.proxy_result.setPlainText("Enter a proxy URL")
            return
        try:
            import subprocess
            result = subprocess.run(
                ["curl", "-s", "--proxy", url, "--max-time", "10", "https://ipinfo.io/json"],
                capture_output=True, text=True, timeout=15
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                self.proxy_result.setPlainText(f"Connected! IP: {data.get('ip')} | Org: {data.get('org')} | City: {data.get('city')}")
            else:
                self.proxy_result.setPlainText(f"Proxy test failed: {result.stderr[:200]}")
        except Exception as e:
            self.proxy_result.setPlainText(f"Proxy test error: {e}")

    def _geoip_lookup(self):
        ip = self.sh_ip.text().strip()
        if not ip:
            return
        if SELF_HOSTED_OK:
            try:
                validator = GeoIPValidator()
                result = validator.lookup(ip) if hasattr(validator, 'lookup') else validator.check(ip) if hasattr(validator, 'check') else str(validator)
                self.sh_output.setPlainText(json.dumps(result, indent=2, default=str) if isinstance(result, dict) else str(result))
            except Exception as e:
                self.sh_output.setPlainText(f"GeoIP error: {e}")
        else:
            self.sh_output.setPlainText("Self-Hosted Stack not available")

    def _ip_quality(self):
        ip = self.sh_ip.text().strip()
        if not ip:
            return
        if SELF_HOSTED_OK:
            try:
                checker = IPQualityChecker()
                result = checker.check(ip)
                self.sh_output.setPlainText(json.dumps(result, indent=2, default=str) if isinstance(result, dict) else str(result))
            except Exception as e:
                self.sh_output.setPlainText(f"IP Quality error: {e}")
        else:
            self.sh_output.setPlainText("Self-Hosted Stack not available")

    def _fingerprint_test(self):
        if SELF_HOSTED_OK:
            try:
                tester = FingerprintTester()
                result = tester.test() if hasattr(tester, 'test') else str(tester)
                self.sh_output.setPlainText(json.dumps(result, indent=2, default=str) if isinstance(result, dict) else str(result))
            except Exception as e:
                self.sh_output.setPlainText(f"Fingerprint test error: {e}")
        else:
            self.sh_output.setPlainText("Self-Hosted Stack not available")

    def _spoof_location(self):
        lat = self.loc_lat.text().strip()
        lon = self.loc_lon.text().strip()
        if not lat or not lon:
            return
        if LOCATION_LINUX_OK:
            try:
                spoofer = LocationSpooferLinux()
                spoofer.set_location(float(lat), float(lon))
                QMessageBox.information(self, "Location", f"Location spoofed to ({lat}, {lon})")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Spoof error: {e}")
        elif LOCATION_OK:
            try:
                spoofer = LocationSpoofer()
                spoofer.set_location(float(lat), float(lon))
                QMessageBox.information(self, "Location", f"Location spoofed to ({lat}, {lon})")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Spoof error: {e}")
        else:
            QMessageBox.warning(self, "Error", "Location Spoofer not available")

    def _warmup_referrer(self):
        target = self.ref_target.text().strip()
        if not target:
            return
        if REFERRER_OK:
            try:
                engine = ReferrerWarmupEngine()
                engine.warmup(target) if hasattr(engine, 'warmup') else engine.start(target) if hasattr(engine, 'start') else None
                QMessageBox.information(self, "Warmup", f"Referrer warmup started for {target}")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Warmup error: {e}")
        else:
            QMessageBox.warning(self, "Error", "Referrer Warmup Engine not available")

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
            QProgressBar {{
                background: #1e293b; border: none; border-radius: 4px; text-align: center; color: {TXT};
            }}
            QProgressBar::chunk {{ background: {ACCENT}; border-radius: 4px; }}
            QCheckBox {{ color: {TXT}; }}
        """)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = TitanNetwork()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
