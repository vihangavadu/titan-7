#!/usr/bin/env python3
"""
TITAN V7.5 SINGULARITY — Unified Operations Dashboard
Complete GUI for end-to-end operations

Integrates:
- Infrastructure assessment with presets + V7.5 target intelligence
- Network configuration with DNS leak prevention
- Asset validation (Cerberus) + AVS intelligence + freshness scoring
- Identity synthesis (Genesis)
- Browser launch with fingerprint verification checklist
- Verification compliance module (when needed)
- Operational handover
- V7.5 Intelligence Panel (AVS, Visa Alerts, PayPal Defense, 3DS v2, Proxy Intel)

Flow:
1. User inputs: Target, Proxy, Card, Persona
2. Cerberus validates card (BIN, 3DS, AVS) + freshness check
3. Genesis synthesizes profile (500MB+, 90-day history)
4. Browser launches with all shields
5. Handover document generated for operator
"""

import sys
import os
import asyncio
from pathlib import Path
from datetime import datetime

# Add core library to path
sys.path.insert(0, str(Path(__file__).parent.parent / "core"))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QComboBox, QPushButton, QSpinBox, QTextEdit,
    QGroupBox, QFormLayout, QProgressBar, QMessageBox, QFileDialog,
    QTabWidget, QCheckBox, QFrame, QSplitter, QStackedWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QIcon, QPalette, QColor

# Core imports
try:
    from genesis_core import GenesisEngine, ProfileConfig, GeneratedProfile
    from cerberus_core import CerberusValidator, CardAsset, ValidationResult, CardStatus
    from target_presets import TARGET_PRESETS, get_target_preset, list_targets, TargetPreset
    from advanced_profile_generator import AdvancedProfileGenerator, AdvancedProfileConfig
    CORE_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Core modules not fully available: {e}")
    CORE_AVAILABLE = False

# V7.5 Intelligence imports
try:
    from target_intelligence import (
        get_avs_intelligence, get_visa_alerts_intel, check_visa_alerts_eligible,
        get_fingerprint_tools, get_card_prechecking_intel, estimate_card_freshness,
        get_proxy_intelligence, get_paypal_defense_intel,
        TARGETS as INTEL_TARGETS, get_target_intel, list_targets as intel_list_targets,
    )
    from three_ds_strategy import get_3ds_v2_intelligence, get_3ds_detection_guide
    INTEL_AVAILABLE = True
except ImportError as e:
    print(f"Warning: V7.5 Intelligence modules not available: {e}")
    INTEL_AVAILABLE = False

# V7.5 KYC imports
try:
    from kyc_core import KYCController, ReenactmentConfig, CameraState
    KYC_AVAILABLE = True
except ImportError as e:
    print(f"Warning: KYC module not available: {e}")
    KYC_AVAILABLE = False

# V7.5 Feature imports
try:
    from transaction_monitor import TransactionMonitor, DeclineDecoder, decode_decline
    from target_discovery import TargetDiscovery, AutoDiscovery, get_site_stats, auto_discover
    from three_ds_strategy import (
        ThreeDSBypassEngine, get_3ds_bypass_score, get_3ds_bypass_plan,
        get_downgrade_attacks, get_psp_vulnerabilities, get_psd2_exemptions,
        NonVBVRecommendationEngine, get_non_vbv_recommendations,
        get_easy_countries, get_all_non_vbv_bins,
    )
    from titan_services import TitanServiceManager, get_service_manager, start_all_services
    V703_AVAILABLE = True
except ImportError as e:
    print(f"Warning: V7.5 modules not available: {e}")
    V703_AVAILABLE = False

# V7.5 Hardening imports (Phase 2-3)
try:
    from font_sanitizer import FontSanitizer, TargetOS as FontTargetOS, check_fonts
    from audio_hardener import AudioHardener, AudioTargetOS
    from timezone_enforcer import TimezoneEnforcer, TimezoneConfig, get_timezone_for_state
    from kill_switch import KillSwitch, KillSwitchConfig
    from cerberus_enhanced import OSINTVerifier, CardQualityGrader, CardQualityGrade, score_bin, BINScoringEngine
    from purchase_history_engine import PurchaseHistoryEngine, CardHolderData
    from preflight_validator import PreFlightValidator
    HARDENING_AVAILABLE = True
except ImportError as e:
    print(f"Warning: V7.5 Hardening modules not available: {e}")
    HARDENING_AVAILABLE = False

# V7.5 AI Intelligence Engine
try:
    from ai_intelligence_engine import (
        is_ai_available, get_ai_status, analyze_bin, recon_target,
        advise_3ds, advise_preflight, tune_behavior, audit_profile,
        plan_operation, AIOperationPlan, RiskLevel,
    )
    from tls_parrot import TLSParrotEngine, ParrotTarget
    AI_AVAILABLE = True
except ImportError as e:
    print(f"Warning: AI Intelligence Engine not available: {e}")
    AI_AVAILABLE = False


class ProxyTestWorker(QThread):
    """Background worker for proxy connectivity test"""
    finished = pyqtSignal(dict)
    
    def __init__(self, proxy_url: str):
        super().__init__()
        self.proxy_url = proxy_url
    
    def run(self):
        import time
        try:
            import requests
            start = time.time()
            proxies = {"http": self.proxy_url, "https": self.proxy_url}
            resp = requests.get(
                "https://ipinfo.io/json",
                proxies=proxies,
                timeout=15,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            latency = (time.time() - start) * 1000
            if resp.status_code == 200:
                data = resp.json()
                ip = data.get("ip", "?")
                city = data.get("city", "")
                region = data.get("region", "")
                org = data.get("org", "")
                geo = f"{city}, {region}" if city else org
                self.finished.emit({
                    "success": True, "ip": ip, "geo": geo,
                    "latency_ms": latency, "org": org,
                    "city": city, "region": region,
                })
            else:
                self.finished.emit({"success": False, "error": f"HTTP {resp.status_code}"})
        except requests.exceptions.ProxyError as e:
            self.finished.emit({"success": False, "error": f"Proxy refused: {e}"})
        except requests.exceptions.ConnectTimeout:
            self.finished.emit({"success": False, "error": "Connection timed out (15s)"})
        except Exception as e:
            self.finished.emit({"success": False, "error": str(e)[:120]})


class CardValidationWorker(QThread):
    """Background worker for card validation"""
    finished = pyqtSignal(object)
    status = pyqtSignal(str)
    
    def __init__(self, card_data: dict):
        super().__init__()
        self.card_data = card_data
    
    def run(self):
        try:
            self.status.emit("Validating card...")
            
            # Create card asset
            card = CardAsset(
                number=self.card_data["pan"],
                exp_month=self.card_data["exp_month"],
                exp_year=self.card_data["exp_year"],
                cvv=self.card_data["cvv"],
                holder_name=self.card_data.get("holder_name", "")
            )
            
            # Validate
            validator = CerberusValidator()
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(validator.validate(card))
            loop.close()
            
            self.finished.emit(result)
            
        except Exception as e:
            self.finished.emit({"error": str(e)})


class ProfileForgeWorker(QThread):
    """Background worker for profile generation"""
    finished = pyqtSignal(object)
    progress = pyqtSignal(str)
    
    def __init__(self, config: dict, target_preset: TargetPreset):
        super().__init__()
        self.config = config
        self.target_preset = target_preset
    
    def run(self):
        try:
            self.progress.emit("Initializing Genesis Engine...")
            
            # Create advanced profile config
            profile_config = AdvancedProfileConfig(
                profile_uuid=f"TITAN-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                persona_name=self.config["persona_name"],
                persona_email=self.config["persona_email"],
                billing_address={
                    "address": self.config["address"],
                    "city": self.config["city"],
                    "state": self.config["state"],
                    "zip": self.config["zip"],
                    "country": self.config.get("country", "US"),
                    "phone": self.config.get("phone", ""),
                },
                profile_age_days=self.config.get("age_days", 90),
                localstorage_size_mb=self.config.get("storage_mb", 500),
            )
            
            self.progress.emit("Generating browsing history...")
            self.progress.emit("Creating aged cookies...")
            self.progress.emit("Injecting localStorage (500MB+)...")
            self.progress.emit("Adding commerce trust tokens...")
            self.progress.emit("Generating form autofill...")
            
            # Generate profile
            generator = AdvancedProfileGenerator()
            
            # Use target-specific template
            template = self.target_preset.recommended_archetype
            profile = generator.generate(profile_config, template)
            
            self.progress.emit("Writing handover protocol...")
            
            # Generate handover document
            engine = GenesisEngine()
            engine.generate_handover_document(
                profile.profile_path,
                self.target_preset.domain
            )
            
            self.progress.emit("Profile forged successfully!")
            self.finished.emit(profile)
            
        except Exception as e:
            self.finished.emit({"error": str(e)})


class UnifiedOperationCenter(QMainWindow):
    """
    TITAN V7.5 Unified Operations Dashboard
    
    Complete GUI for end-to-end operations with V7.5 Intelligence Dashboard.
    """
    
    def __init__(self):
        super().__init__()
        
        self.current_target: TargetPreset = None
        self.card_validation_result = None
        self.generated_profile = None
        self.validation_worker = None
        self.forge_worker = None
        
        self.init_ui()
        self.apply_dark_theme()
        self.load_targets()
        self._start_status_bar_timer()
    
    def init_ui(self):
        self.setWindowTitle("TITAN V7.5 — Unified Operations Dashboard")
        try:
            from titan_icon import set_titan_icon
            set_titan_icon(self, "#00d4ff")
        except Exception:
            pass
        self.setMinimumSize(1100, 950)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(6)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Header
        header = QLabel("TITAN V7.5 SINGULARITY")
        header.setFont(QFont("Inter", 22, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("color: #00d4ff; padding: 6px;")
        layout.addWidget(header)
        
        subtitle = QLabel("UNIFIED OPERATIONS DASHBOARD")
        subtitle.setFont(QFont("JetBrains Mono", 11))
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #556; margin-bottom: 4px; font-family: 'JetBrains Mono', 'Consolas', monospace;")
        layout.addWidget(subtitle)
        
        # === TABBED INTERFACE ===
        self.main_tabs = QTabWidget()
        layout.addWidget(self.main_tabs)
        
        # Tab 1: Operation Panel
        op_tab = QWidget()
        op_scroll = QVBoxLayout(op_tab)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(6)
        
        # ═══════════════════════════════════════════════════════════════════
        # TARGET CONFIGURATION
        # ═══════════════════════════════════════════════════════════════════
        target_group = QGroupBox("🎯 TARGET CONFIGURATION")
        target_layout = QFormLayout(target_group)
        
        self.target_combo = QComboBox()
        self.target_combo.currentIndexChanged.connect(self.on_target_changed)
        target_layout.addRow("Target Site:", self.target_combo)
        
        self.target_info = QLabel("Select a target to see details")
        self.target_info.setStyleSheet("color: #888; font-size: 11px;")
        target_layout.addRow("", self.target_info)
        
        content_layout.addWidget(target_group)
        
        # ═══════════════════════════════════════════════════════════════════
        # NETWORK CONFIGURATION (Proxy OR Lucid VPN)
        # ═══════════════════════════════════════════════════════════════════
        net_group = QGroupBox("🌐 NETWORK CONFIGURATION")
        net_layout = QFormLayout(net_group)
        
        # Network mode selector
        mode_layout = QHBoxLayout()
        self.net_mode = QComboBox()
        self.net_mode.addItems(["Residential Proxy", "Lucid VPN (Residential Exit)", "Lucid VPN (Mobile 4G/5G)"])
        self.net_mode.currentIndexChanged.connect(self._on_net_mode_changed)
        mode_layout.addWidget(self.net_mode)
        net_layout.addRow("Mode:", mode_layout)
        
        # Proxy fields (shown in proxy mode)
        self.proxy_url = QLineEdit()
        self.proxy_url.setPlaceholderText("socks5://user:pass@proxy.example.com:1080")
        net_layout.addRow("Proxy URL:", self.proxy_url)
        self.proxy_url_label = net_layout.labelForField(self.proxy_url)
        
        proxy_type_layout = QHBoxLayout()
        self.proxy_type = QComboBox()
        self.proxy_type.addItems(["Residential (Recommended)", "Mobile", "Datacenter"])
        proxy_type_layout.addWidget(self.proxy_type)
        
        self.test_proxy_btn = QPushButton("🔍 Test Proxy")
        self.test_proxy_btn.clicked.connect(self.test_proxy)
        proxy_type_layout.addWidget(self.test_proxy_btn)
        net_layout.addRow("Proxy Type:", proxy_type_layout)
        self.proxy_type_label = net_layout.labelForField(proxy_type_layout)
        self.proxy_type_widget = proxy_type_layout
        
        # VPN fields (shown in VPN mode)
        vpn_btn_layout = QHBoxLayout()
        self.vpn_connect_btn = QPushButton("🔗 Connect VPN")
        self.vpn_connect_btn.clicked.connect(self._vpn_connect)
        vpn_btn_layout.addWidget(self.vpn_connect_btn)
        self.vpn_disconnect_btn = QPushButton("🔌 Disconnect")
        self.vpn_disconnect_btn.clicked.connect(self._vpn_disconnect)
        vpn_btn_layout.addWidget(self.vpn_disconnect_btn)
        self.vpn_setup_btn = QPushButton("⚙ Setup")
        self.vpn_setup_btn.setToolTip("Run titan-vpn-setup wizard in terminal")
        self.vpn_setup_btn.clicked.connect(self._vpn_open_setup)
        vpn_btn_layout.addWidget(self.vpn_setup_btn)
        net_layout.addRow("VPN Control:", vpn_btn_layout)
        self.vpn_control_label = net_layout.labelForField(vpn_btn_layout)
        
        # Status (shared)
        self.proxy_status = QLabel("Not tested")
        self.proxy_status.setStyleSheet("color: #888;")
        net_layout.addRow("Status:", self.proxy_status)
        
        # Hide VPN controls by default (proxy mode is default)
        self.vpn_connect_btn.setVisible(False)
        self.vpn_disconnect_btn.setVisible(False)
        self.vpn_setup_btn.setVisible(False)
        self.vpn_control_label.setVisible(False)
        
        content_layout.addWidget(net_group)
        
        # ═══════════════════════════════════════════════════════════════════
        # CARD DETAILS
        # ═══════════════════════════════════════════════════════════════════
        card_group = QGroupBox("💳 CARD DETAILS")
        card_layout = QFormLayout(card_group)
        
        self.card_pan = QLineEdit()
        self.card_pan.setPlaceholderText("4532 XXXX XXXX 8921")
        self.card_pan.setMaxLength(19)
        card_layout.addRow("Card Number:", self.card_pan)
        
        exp_cvv_layout = QHBoxLayout()
        self.card_exp = QLineEdit()
        self.card_exp.setPlaceholderText("MM/YY")
        self.card_exp.setMaxLength(5)
        self.card_exp.setMaximumWidth(80)
        exp_cvv_layout.addWidget(self.card_exp)
        
        exp_cvv_layout.addWidget(QLabel("CVV:"))
        self.card_cvv = QLineEdit()
        self.card_cvv.setPlaceholderText("XXX")
        self.card_cvv.setMaxLength(4)
        self.card_cvv.setMaximumWidth(60)
        self.card_cvv.setEchoMode(QLineEdit.EchoMode.Password)
        exp_cvv_layout.addWidget(self.card_cvv)
        exp_cvv_layout.addStretch()
        
        self.validate_card_btn = QPushButton("🔒 Validate Card")
        self.validate_card_btn.clicked.connect(self.validate_card)
        exp_cvv_layout.addWidget(self.validate_card_btn)
        
        card_layout.addRow("Expiry:", exp_cvv_layout)
        
        self.card_holder = QLineEdit()
        self.card_holder.setPlaceholderText("ALEX J MERCER")
        card_layout.addRow("Cardholder:", self.card_holder)
        
        self.card_status = QLabel("Not validated")
        self.card_status.setStyleSheet("color: #888;")
        card_layout.addRow("Status:", self.card_status)
        
        content_layout.addWidget(card_group)
        
        # ═══════════════════════════════════════════════════════════════════
        # PERSONA DETAILS
        # ═══════════════════════════════════════════════════════════════════
        persona_group = QGroupBox("👤 PERSONA DETAILS")
        persona_layout = QFormLayout(persona_group)
        
        self.persona_name = QLineEdit()
        self.persona_name.setPlaceholderText("Alex J. Mercer")
        persona_layout.addRow("Full Name:", self.persona_name)
        
        self.persona_email = QLineEdit()
        self.persona_email.setPlaceholderText("a.mercer.dev@gmail.com")
        persona_layout.addRow("Email:", self.persona_email)
        
        self.persona_phone = QLineEdit()
        self.persona_phone.setPlaceholderText("512-555-0123")
        persona_layout.addRow("Phone:", self.persona_phone)
        
        self.persona_address = QLineEdit()
        self.persona_address.setPlaceholderText("2400 NUECES ST, APT 402")
        persona_layout.addRow("Address:", self.persona_address)
        
        city_state_layout = QHBoxLayout()
        self.persona_city = QLineEdit()
        self.persona_city.setPlaceholderText("AUSTIN")
        city_state_layout.addWidget(self.persona_city)
        
        self.persona_state = QLineEdit()
        self.persona_state.setPlaceholderText("TX")
        self.persona_state.setMaximumWidth(50)
        city_state_layout.addWidget(self.persona_state)
        
        self.persona_zip = QLineEdit()
        self.persona_zip.setPlaceholderText("78705")
        self.persona_zip.setMaximumWidth(80)
        city_state_layout.addWidget(self.persona_zip)
        
        self.persona_country = QComboBox()
        self.persona_country.addItems(["US", "CA", "GB", "AU", "DE", "FR", "NL", "BR", "MX", "JP"])
        self.persona_country.setMaximumWidth(70)
        city_state_layout.addWidget(self.persona_country)
        
        persona_layout.addRow("City/State/ZIP/Country:", city_state_layout)
        
        content_layout.addWidget(persona_group)
        
        # ═══════════════════════════════════════════════════════════════════
        # PROFILE OPTIONS
        # ═══════════════════════════════════════════════════════════════════
        options_group = QGroupBox("⚙️ PROFILE OPTIONS")
        options_layout = QFormLayout(options_group)
        
        age_storage_layout = QHBoxLayout()
        
        age_storage_layout.addWidget(QLabel("Profile Age:"))
        self.profile_age = QSpinBox()
        self.profile_age.setRange(30, 365)
        self.profile_age.setValue(90)
        self.profile_age.setSuffix(" days")
        age_storage_layout.addWidget(self.profile_age)
        
        age_storage_layout.addWidget(QLabel("Storage:"))
        self.storage_size = QSpinBox()
        self.storage_size.setRange(100, 1000)
        self.storage_size.setValue(500)
        self.storage_size.setSuffix(" MB")
        age_storage_layout.addWidget(self.storage_size)
        
        age_storage_layout.addStretch()
        options_layout.addRow("", age_storage_layout)
        
        self.archetype_combo = QComboBox()
        self.archetype_combo.addItems([
            "Student Developer (Alex Mercer)",
            "Professional",
            "Gamer",
            "Casual Shopper",
            "Retiree"
        ])
        options_layout.addRow("Archetype:", self.archetype_combo)
        
        self.hardware_combo = QComboBox()
        self.hardware_combo.addItems([
            "MacBook Pro M2 (Recommended)",
            "Windows Desktop (NVIDIA)",
            "Windows Gaming (RTX 4080)",
            "Windows Laptop (Intel)",
            "Linux Desktop"
        ])
        options_layout.addRow("Hardware:", self.hardware_combo)
        
        checkboxes_layout = QHBoxLayout()
        self.cb_autofill = QCheckBox("Form Autofill")
        self.cb_autofill.setChecked(True)
        checkboxes_layout.addWidget(self.cb_autofill)
        
        self.cb_tokens = QCheckBox("Commerce Tokens")
        self.cb_tokens.setChecked(True)
        checkboxes_layout.addWidget(self.cb_tokens)
        
        self.cb_card_hint = QCheckBox("Card Hint")
        self.cb_card_hint.setChecked(True)
        checkboxes_layout.addWidget(self.cb_card_hint)
        
        self.cb_handover = QCheckBox("Handover Doc")
        self.cb_handover.setChecked(True)
        checkboxes_layout.addWidget(self.cb_handover)
        
        checkboxes_layout.addStretch()
        options_layout.addRow("Options:", checkboxes_layout)
        
        content_layout.addWidget(options_group)
        
        # ═══════════════════════════════════════════════════════════════════
        # ACTION BUTTONS
        # ═══════════════════════════════════════════════════════════════════
        actions_layout = QHBoxLayout()
        
        self.forge_btn = QPushButton("SYNTHESIZE PROFILE")
        self.forge_btn.setFont(QFont("Inter", 14, QFont.Weight.Bold))
        self.forge_btn.setMinimumHeight(50)
        self.forge_btn.setStyleSheet("""
            QPushButton {
                background-color: #3A75C4;
                color: white;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #4A8AD8;
            }
            QPushButton:disabled {
                background-color: #2A3444;
                color: #64748B;
            }
        """)
        self.forge_btn.clicked.connect(self.forge_profile)
        actions_layout.addWidget(self.forge_btn)
        
        self.launch_btn = QPushButton("INITIATE SESSION")
        self.launch_btn.setFont(QFont("Inter", 14, QFont.Weight.Bold))
        self.launch_btn.setMinimumHeight(50)
        self.launch_btn.setEnabled(False)
        self.launch_btn.setStyleSheet("""
            QPushButton {
                background-color: #2E7D32;
                color: white;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #388E3C;
            }
            QPushButton:disabled {
                background-color: #2A3444;
                color: #64748B;
            }
        """)
        self.launch_btn.clicked.connect(self.launch_browser)
        actions_layout.addWidget(self.launch_btn)
        
        content_layout.addLayout(actions_layout)
        
        # ═══════════════════════════════════════════════════════════════════
        # STATUS
        # ═══════════════════════════════════════════════════════════════════
        status_group = QGroupBox("📊 STATUS")
        status_layout = QVBoxLayout(status_group)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        status_layout.addWidget(self.progress_bar)
        
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMaximumHeight(100)
        self.status_text.setPlaceholderText("Ready to begin operation...")
        status_layout.addWidget(self.status_text)
        
        content_layout.addWidget(status_group)
        
        op_scroll.addWidget(content)
        self.main_tabs.addTab(op_tab, "OPERATION")
        
        # ═══════════════════════════════════════════════════════════════════
        # Tab 2: V7.5 INTELLIGENCE DASHBOARD
        # ═══════════════════════════════════════════════════════════════════
        intel_tab = QWidget()
        intel_layout = QVBoxLayout(intel_tab)
        intel_layout.setSpacing(4)
        
        self.intel_tabs = QTabWidget()
        self.intel_tabs.setTabPosition(QTabWidget.TabPosition.West)
        self.intel_tabs.setStyleSheet("""
            QTabBar::tab { padding: 10px 6px; min-width: 30px; background: #1C2330; color: #64748B; }
            QTabBar::tab:selected { background: #1A2D4A; color: #4A8AD8; font-weight: bold; border-left: 2px solid #3A75C4; }
            QTabBar::tab:hover { background: #232B3A; color: #E2E8F0; }
        """)
        intel_layout.addWidget(self.intel_tabs)
        
        # --- AVS Intelligence Sub-Tab ---
        avs_widget = QWidget()
        avs_layout = QVBoxLayout(avs_widget)
        avs_layout.addWidget(QLabel("AVS INTELLIGENCE"))
        
        avs_form = QFormLayout()
        self.avs_country_input = QLineEdit()
        self.avs_country_input.setPlaceholderText("US, GB, DE, BR, etc.")
        self.avs_country_input.setMaximumWidth(120)
        avs_check_btn = QPushButton("Check AVS")
        avs_check_btn.clicked.connect(self._check_avs)
        avs_row = QHBoxLayout()
        avs_row.addWidget(self.avs_country_input)
        avs_row.addWidget(avs_check_btn)
        avs_row.addStretch()
        avs_form.addRow("Card Country:", avs_row)
        avs_layout.addLayout(avs_form)
        
        self.avs_result_text = QTextEdit()
        self.avs_result_text.setReadOnly(True)
        self.avs_result_text.setPlaceholderText("Enter a country code and click Check AVS...")
        avs_layout.addWidget(self.avs_result_text)
        self.intel_tabs.addTab(avs_widget, "AVS")
        
        # --- Visa Alerts Sub-Tab ---
        visa_widget = QWidget()
        visa_layout = QVBoxLayout(visa_widget)
        visa_layout.addWidget(QLabel("VISA PURCHASE ALERTS"))
        
        visa_form = QFormLayout()
        self.visa_country_input = QLineEdit()
        self.visa_country_input.setPlaceholderText("US, MX, BR, etc.")
        self.visa_country_input.setMaximumWidth(120)
        visa_check_btn = QPushButton("Check Eligibility")
        visa_check_btn.clicked.connect(self._check_visa_alerts)
        visa_row = QHBoxLayout()
        visa_row.addWidget(self.visa_country_input)
        visa_row.addWidget(visa_check_btn)
        visa_row.addStretch()
        visa_form.addRow("Card Country:", visa_row)
        visa_layout.addLayout(visa_form)
        
        self.visa_result_text = QTextEdit()
        self.visa_result_text.setReadOnly(True)
        if INTEL_AVAILABLE:
            intel = get_visa_alerts_intel()
            intro = "VISA ALERTS ENROLLMENT\n"
            intro += f"URL: {intel['enrollment_url']}\n\n"
            intro += "STEPS:\n" + "\n".join(intel["enrollment_steps"]) + "\n\n"
            intro += "USE CASES:\n" + "\n".join(f"  - {u}" for u in intel["use_cases"])
            self.visa_result_text.setPlainText(intro)
        visa_layout.addWidget(self.visa_result_text)
        self.intel_tabs.addTab(visa_widget, "Visa Alerts")
        
        # --- Card Freshness Sub-Tab ---
        fresh_widget = QWidget()
        fresh_layout = QVBoxLayout(fresh_widget)
        fresh_layout.addWidget(QLabel("CARD FRESHNESS & PRECHECKING"))
        
        fresh_form = QFormLayout()
        self.fresh_checked = QCheckBox("Card has been checked before")
        self.fresh_times = QSpinBox()
        self.fresh_times.setRange(0, 20)
        self.fresh_times.setValue(0)
        self.fresh_used = QCheckBox("Previously used on another site")
        self.fresh_declined = QCheckBox("Ever been declined")
        fresh_score_btn = QPushButton("Score Freshness")
        fresh_score_btn.clicked.connect(self._score_freshness)
        
        fresh_form.addRow("", self.fresh_checked)
        fresh_form.addRow("Times Checked:", self.fresh_times)
        fresh_form.addRow("", self.fresh_used)
        fresh_form.addRow("", self.fresh_declined)
        fresh_form.addRow("", fresh_score_btn)
        fresh_layout.addLayout(fresh_form)
        
        self.fresh_result_text = QTextEdit()
        self.fresh_result_text.setReadOnly(True)
        if INTEL_AVAILABLE:
            intel = get_card_prechecking_intel()
            self.fresh_result_text.setPlainText(
                "THE PRECHECKING PARADOX\n" + "=" * 40 + "\n" +
                intel["the_paradox"] + "\n\n" +
                "WHEN TO CHECK:\n" + "\n".join(f"  - {w}" for w in intel["when_to_check"]) + "\n\n" +
                "CARD TIERS:\n" +
                "\n".join(f"  {k}: {v['advantage']}" for k, v in intel["card_tier_intelligence"].items())
            )
        fresh_layout.addWidget(self.fresh_result_text)
        self.intel_tabs.addTab(fresh_widget, "Card Fresh")
        
        # --- Fingerprint Tools Sub-Tab ---
        fp_widget = QWidget()
        fp_layout = QVBoxLayout(fp_widget)
        fp_layout.addWidget(QLabel("FINGERPRINT VERIFICATION TOOLS"))
        
        self.fp_result_text = QTextEdit()
        self.fp_result_text.setReadOnly(True)
        if INTEL_AVAILABLE:
            fp_data = get_fingerprint_tools()
            text = "VERIFICATION WORKFLOW\n" + "=" * 40 + "\n"
            text += "\n".join(fp_data["workflow"]) + "\n\n"
            text += "TOOLS\n" + "=" * 40 + "\n"
            for key, tool in fp_data["tools"].items():
                text += f"\n[{tool['priority']}] {tool['name']}\n"
                text += f"  URL: {tool['url']}\n"
                text += f"  Checks: {tool['checks']}\n"
                text += f"  Pros: {tool['pros']}\n"
                text += f"  Cons: {tool['cons']}\n"
            self.fp_result_text.setPlainText(text)
        fp_layout.addWidget(self.fp_result_text)
        self.intel_tabs.addTab(fp_widget, "Fingerprint")
        
        # --- PayPal Defense Sub-Tab ---
        pp_widget = QWidget()
        pp_layout = QVBoxLayout(pp_widget)
        pp_layout.addWidget(QLabel("PAYPAL 3-PILLAR DEFENSE"))
        
        self.pp_result_text = QTextEdit()
        self.pp_result_text.setReadOnly(True)
        if INTEL_AVAILABLE:
            pp = get_paypal_defense_intel()
            text = "OVERVIEW\n" + "=" * 40 + "\n" + pp["overview"] + "\n\n"
            for pillar_key, pillar in pp["three_pillars"].items():
                text += f"\nPILLAR: {pillar_key.upper()}\n" + "-" * 30 + "\n"
                text += f"{pillar['description']}\n\n"
                if "key_facts" in pillar:
                    text += "Key Facts:\n" + "\n".join(f"  - {f}" for f in pillar["key_facts"]) + "\n"
                if "components" in pillar:
                    text += "Components:\n" + "\n".join(f"  {c}" for c in pillar["components"]) + "\n"
                if "checks" in pillar:
                    text += "Checks:\n" + "\n".join(f"  {c}" for c in pillar["checks"]) + "\n"
                text += "Evasion:\n" + "\n".join(f"  - {e}" for e in pillar["evasion"]) + "\n"
            text += "\n\nWARMING STRATEGY\n" + "=" * 40 + "\n"
            text += "\n".join(pp["warming_strategy"])
            self.pp_result_text.setPlainText(text)
        pp_layout.addWidget(self.pp_result_text)
        self.intel_tabs.addTab(pp_widget, "PayPal")
        
        # --- 3DS v2 Sub-Tab ---
        tds_widget = QWidget()
        tds_layout = QVBoxLayout(tds_widget)
        tds_layout.addWidget(QLabel("3DS 2.0 INTELLIGENCE"))
        
        self.tds_result_text = QTextEdit()
        self.tds_result_text.setReadOnly(True)
        if INTEL_AVAILABLE:
            tds = get_3ds_v2_intelligence()
            text = "3DS INITIATORS (Who can trigger 3DS)\n" + "=" * 40 + "\n"
            for key, init in tds["initiators"].items():
                text += f"\n{init['entity']}\n"
                text += f"  {init['description']}\n"
                text += f"  Trigger: {init['trigger']}\n"
                text += f"  Evasion: {init['evasion']}\n"
            v2 = tds["v2_intelligence"]
            text += f"\n\n3DS 2.0 KEY CHANGES\n" + "=" * 40 + "\n"
            text += "\n".join(f"  - {c}" for c in v2["key_changes"]) + "\n"
            text += f"\nBIOMETRIC THREATS\n" + "-" * 30 + "\n"
            for bk, bv in v2["biometric_threats"].items():
                text += f"\n  {bk}: {bv['description']}\n"
                text += f"    Bypass: {bv['bypass']}\n"
                text += f"    Banks: {', '.join(bv['banks_known'])}\n"
            text += f"\nFRICTIONLESS FLOW TIPS\n" + "-" * 30 + "\n"
            text += "\n".join(f"  - {t}" for t in v2["frictionless_flow_tips"])
            text += f"\n\nNON-VBV STRATEGY\n" + "-" * 30 + "\n"
            text += "\n".join(f"  - {s}" for s in v2["non_vbv_strategy"])
            self.tds_result_text.setPlainText(text)
        tds_layout.addWidget(self.tds_result_text)
        self.intel_tabs.addTab(tds_widget, "3DS v2")
        
        # --- Proxy & DNS Sub-Tab ---
        proxy_intel_widget = QWidget()
        proxy_intel_layout = QVBoxLayout(proxy_intel_widget)
        proxy_intel_layout.addWidget(QLabel("PROXY & DNS INTELLIGENCE"))
        
        self.proxy_intel_text = QTextEdit()
        self.proxy_intel_text.setReadOnly(True)
        if INTEL_AVAILABLE:
            pi = get_proxy_intelligence()
            text = "PROXY TYPE PREFERENCE (Best to Worst)\n" + "=" * 40 + "\n"
            for key, ptype in pi["type_preference"].items():
                text += f"\n  [{ptype['risk']}] {ptype['type']}\n    {ptype['notes']}\n"
            text += f"\n\nDNS LEAK PREVENTION\n" + "=" * 40 + "\n"
            text += "\n".join(f"  - {d}" for d in pi["dns_leak_prevention"])
            text += f"\n\nSHARED POOL WARNING\n" + "-" * 30 + "\n{pi['shared_pool_warning']}\n"
            text += f"\nIP REPUTATION CHECK URLS:\n"
            text += "\n".join(f"  {u}" for u in pi["ip_reputation_check_urls"])
            self.proxy_intel_text.setPlainText(text)
        proxy_intel_layout.addWidget(self.proxy_intel_text)
        self.intel_tabs.addTab(proxy_intel_widget, "Proxy/DNS")
        
        # --- Target Intel Sub-Tab ---
        target_intel_widget = QWidget()
        target_intel_layout = QVBoxLayout(target_intel_widget)
        target_intel_layout.addWidget(QLabel("TARGET INTELLIGENCE DATABASE"))
        
        ti_search_row = QHBoxLayout()
        self.ti_search = QLineEdit()
        self.ti_search.setPlaceholderText("Search target by name (e.g. paypal, stockx, g2a)...")
        ti_search_btn = QPushButton("Lookup")
        ti_search_btn.clicked.connect(self._lookup_target_intel)
        ti_search_row.addWidget(self.ti_search)
        ti_search_row.addWidget(ti_search_btn)
        target_intel_layout.addLayout(ti_search_row)
        
        self.ti_result_text = QTextEdit()
        self.ti_result_text.setReadOnly(True)
        if INTEL_AVAILABLE:
            targets = intel_list_targets()
            text = f"LOADED {len(targets)} TARGETS\n" + "=" * 40 + "\n"
            for t in targets:
                text += f"  {t['name']:25s} | {t['fraud_engine']:15s} | {t['friction']:10s} | 3DS: {t['3ds_rate']*100:.0f}%\n"
            self.ti_result_text.setPlainText(text)
        target_intel_layout.addWidget(self.ti_result_text)
        self.intel_tabs.addTab(target_intel_widget, "Targets")
        
        self.main_tabs.addTab(intel_tab, "INTELLIGENCE")
        
        # ═══════════════════════════════════════════════════════════════════
        # Tab 3: V7.5 SHIELDS & HARDENING
        # ═══════════════════════════════════════════════════════════════════
        shields_tab = QWidget()
        shields_layout = QVBoxLayout(shields_tab)
        shields_layout.setSpacing(4)
        
        self.shields_tabs = QTabWidget()
        self.shields_tabs.setTabPosition(QTabWidget.TabPosition.West)
        self.shields_tabs.setStyleSheet("""
            QTabBar::tab { padding: 10px 6px; min-width: 30px; background: #1C2330; color: #64748B; }
            QTabBar::tab:selected { background: #1A2D4A; color: #4A8AD8; font-weight: bold; border-left: 2px solid #3A75C4; }
            QTabBar::tab:hover { background: #232B3A; color: #E2E8F0; }
        """)
        shields_layout.addWidget(self.shields_tabs)
        
        # --- Pre-Flight / Master Verify Sub-Tab ---
        pf_widget = QWidget()
        pf_layout = QVBoxLayout(pf_widget)
        pf_layout.addWidget(QLabel("MASTER VERIFICATION PROTOCOL (MVP)"))
        
        pf_btn_row = QHBoxLayout()
        self.mvp_run_btn = QPushButton("▶ Run Master Verify")
        self.mvp_run_btn.clicked.connect(self._run_master_verify)
        pf_btn_row.addWidget(self.mvp_run_btn)
        self.deep_id_btn = QPushButton("▶ Deep Identity Check")
        self.deep_id_btn.clicked.connect(self._run_deep_identity)
        pf_btn_row.addWidget(self.deep_id_btn)
        pf_btn_row.addStretch()
        pf_layout.addLayout(pf_btn_row)
        
        self.preflight_text = QTextEdit()
        self.preflight_text.setReadOnly(True)
        self.preflight_text.setPlaceholderText(
            "Run Master Verify to check all 4 layers:\n"
            "  Layer 0: Kernel Shield (titan_hw.ko)\n"
            "  Layer 1: Network Shield (eBPF/XDP)\n"
            "  Layer 2: Environment (Fonts/Audio/Prefs)\n"
            "  Layer 3: Identity & Time (Profile/FP/TZ)"
        )
        pf_layout.addWidget(self.preflight_text)
        self.shields_tabs.addTab(pf_widget, "Pre-Flight")
        
        # --- Phase 3: Environment Hardening Sub-Tab ---
        env_widget = QWidget()
        env_layout = QVBoxLayout(env_widget)
        env_layout.addWidget(QLabel("PHASE 3: ENVIRONMENT HARDENING (Fonts / Audio / Time)"))
        
        env_form = QFormLayout()
        self.env_target_os = QComboBox()
        self.env_target_os.addItems(["Windows 11", "Windows 10", "macOS 14", "macOS 13"])
        env_form.addRow("Target OS:", self.env_target_os)
        
        env_btn_row = QHBoxLayout()
        self.font_purge_btn = QPushButton("🔤 Font Purge")
        self.font_purge_btn.setToolTip("Phase 3.1: Reject Linux fonts, inject target OS fonts")
        self.font_purge_btn.clicked.connect(self._run_font_purge)
        env_btn_row.addWidget(self.font_purge_btn)
        
        self.audio_harden_btn = QPushButton("🔊 Audio Harden")
        self.audio_harden_btn.setToolTip("Phase 3.2: AudioContext noise injection + RFP")
        self.audio_harden_btn.clicked.connect(self._run_audio_harden)
        env_btn_row.addWidget(self.audio_harden_btn)
        
        self.tz_enforce_btn = QPushButton("🕐 Timezone Sync")
        self.tz_enforce_btn.setToolTip("Phase 3.3: Kill browsers → set TZ → NTP sync → verify")
        self.tz_enforce_btn.clicked.connect(self._run_tz_enforce)
        env_btn_row.addWidget(self.tz_enforce_btn)
        env_btn_row.addStretch()
        env_form.addRow("Actions:", env_btn_row)
        
        # V7.5 Extended hardening row
        env_btn_row2 = QHBoxLayout()
        self.canvas_shim_btn = QPushButton("🖼️ Canvas Shim")
        self.canvas_shim_btn.setToolTip("V7.5: Sub-pixel measureText() correction for Windows consistency")
        self.canvas_shim_btn.clicked.connect(self._run_canvas_shim)
        env_btn_row2.addWidget(self.canvas_shim_btn)
        
        self.cpuid_shield_btn = QPushButton("🔒 CPUID Shield")
        self.cpuid_shield_btn.setToolTip("V7.5: DMI bind-mount overrides + hypervisor suppression")
        self.cpuid_shield_btn.clicked.connect(self._run_cpuid_shield)
        env_btn_row2.addWidget(self.cpuid_shield_btn)
        
        self.font_prov_btn = QPushButton("📦 Font Provision")
        self.font_prov_btn.setToolTip("V7.5: Install Windows fonts + block Linux fonts + alias Segoe UI")
        self.font_prov_btn.clicked.connect(self._run_font_provisioner)
        env_btn_row2.addWidget(self.font_prov_btn)
        
        self.immutable_btn = QPushButton("🛡️ Immutable OS")
        self.immutable_btn.setToolTip("Lock down OS: immutable resolv.conf, sysctl hardening")
        self.immutable_btn.clicked.connect(self._run_immutable_os)
        env_btn_row2.addWidget(self.immutable_btn)
        env_btn_row2.addStretch()
        env_form.addRow("V7.5:", env_btn_row2)
        
        # Ghost Motor + Fingerprint row
        env_btn_row3 = QHBoxLayout()
        self.ghost_motor_btn = QPushButton("👻 Ghost Motor")
        self.ghost_motor_btn.setToolTip("Diffusion-based human trajectory generation for Forter/BioCatch evasion")
        self.ghost_motor_btn.clicked.connect(self._run_ghost_motor_test)
        env_btn_row3.addWidget(self.ghost_motor_btn)
        
        self.fp_inject_btn = QPushButton("🧬 Inject Fingerprint")
        self.fp_inject_btn.setToolTip("Inject hardware fingerprint into browser profile via Netlink bridge")
        self.fp_inject_btn.clicked.connect(self._run_fingerprint_inject)
        env_btn_row3.addWidget(self.fp_inject_btn)
        
        self.run_all_shields_btn = QPushButton("⚡ RUN ALL SHIELDS")
        self.run_all_shields_btn.setStyleSheet("QPushButton{background:#E6A817;color:#000;font-weight:bold;}")
        self.run_all_shields_btn.setToolTip("Run all V7.5 hardening in sequence")
        self.run_all_shields_btn.clicked.connect(self._run_all_shields)
        env_btn_row3.addWidget(self.run_all_shields_btn)
        env_btn_row3.addStretch()
        env_form.addRow("Shields:", env_btn_row3)
        
        env_layout.addLayout(env_form)
        
        self.env_result_text = QTextEdit()
        self.env_result_text.setReadOnly(True)
        self.env_result_text.setPlaceholderText(
            "V7.5 Environment Hardening:\n"
            "  Phase 3.1 — Font Purge: Reject Linux fonts, inject Windows core fonts\n"
            "  Phase 3.2 — Audio Harden: 44100Hz + noise injection + PulseAudio mask\n"
            "  Phase 3.3 — Timezone Sync: Kill browsers → set TZ → NTP sync\n"
            "  Phase 3.4 — Canvas Shim: Sub-pixel measureText() correction (8 fonts)\n"
            "  Phase 3.5 — CPUID Shield: DMI overrides + /sys/hypervisor suppression\n"
            "  Phase 3.6 — Font Provision: 352 Windows fonts + 39 Linux fonts blocked\n"
            "  Phase 3.7 — Immutable OS: resolv.conf lock + sysctl hardening\n"
            "  Phase 3.8 — Ghost Motor: Diffusion trajectory generation\n"
            "  Phase 3.9 — Fingerprint Inject: HW fingerprint → browser profile\n\n"
            "Click RUN ALL SHIELDS to execute everything in sequence."
        )
        env_layout.addWidget(self.env_result_text)
        self.shields_tabs.addTab(env_widget, "Environment")
        
        # --- Kill Switch Sub-Tab ---
        ks_widget = QWidget()
        ks_layout = QVBoxLayout(ks_widget)
        ks_layout.addWidget(QLabel("PHASE 2.3: KILL SWITCH"))
        
        ks_form = QFormLayout()
        self.ks_threshold = QSpinBox()
        self.ks_threshold.setRange(50, 100)
        self.ks_threshold.setValue(85)
        self.ks_threshold.setSuffix(" fraud score")
        ks_form.addRow("Panic Threshold:", self.ks_threshold)
        
        ks_btn_row = QHBoxLayout()
        self.ks_arm_btn = QPushButton("🔴 ARM Kill Switch")
        self.ks_arm_btn.setStyleSheet("QPushButton { background-color: #8B0000; color: white; font-weight: bold; }")
        self.ks_arm_btn.clicked.connect(self._arm_kill_switch)
        ks_btn_row.addWidget(self.ks_arm_btn)
        self.ks_disarm_btn = QPushButton("⬛ DISARM")
        self.ks_disarm_btn.clicked.connect(self._disarm_kill_switch)
        self.ks_disarm_btn.setEnabled(False)
        ks_btn_row.addWidget(self.ks_disarm_btn)
        self.ks_panic_btn = QPushButton("⚡ MANUAL PANIC")
        self.ks_panic_btn.setStyleSheet("QPushButton { background-color: #D32F2F; color: white; font-weight: bold; }")
        self.ks_panic_btn.clicked.connect(self._manual_panic)
        self.ks_panic_btn.setEnabled(False)
        ks_btn_row.addWidget(self.ks_panic_btn)
        ks_btn_row.addStretch()
        ks_form.addRow("Controls:", ks_btn_row)
        ks_layout.addLayout(ks_form)
        
        self.ks_status_text = QTextEdit()
        self.ks_status_text.setReadOnly(True)
        self.ks_status_text.setPlaceholderText(
            "Kill Switch monitors fraud_score.json every 500ms.\n"
            "On PANIC (score < threshold):\n"
            "  1. pkill -9 browser processes\n"
            "  2. Flush hardware ID (Netlink → titan_hw.ko)\n"
            "  3. Clear session data\n"
            "  4. Rotate proxy\n"
            "  5. Randomize MAC address\n"
            "  6. Log event to panic_log.jsonl"
        )
        ks_layout.addWidget(self.ks_status_text)
        self.shields_tabs.addTab(ks_widget, "Kill Switch")
        
        # --- OSINT & Card Quality Sub-Tab ---
        osint_widget = QWidget()
        osint_layout = QVBoxLayout(osint_widget)
        osint_layout.addWidget(QLabel("OSINT VERIFICATION & CARD QUALITY GRADING"))
        
        osint_form = QFormLayout()
        self.osint_name = QLineEdit()
        self.osint_name.setPlaceholderText("Cardholder full name")
        osint_form.addRow("Name:", self.osint_name)
        self.osint_state = QLineEdit()
        self.osint_state.setPlaceholderText("TX")
        self.osint_state.setMaximumWidth(60)
        osint_form.addRow("State:", self.osint_state)
        self.osint_bin = QLineEdit()
        self.osint_bin.setPlaceholderText("453201")
        self.osint_bin.setMaximumWidth(100)
        osint_form.addRow("BIN (6 digits):", self.osint_bin)
        
        osint_btn_row = QHBoxLayout()
        osint_verify_btn = QPushButton("🔍 OSINT Verify")
        osint_verify_btn.clicked.connect(self._run_osint)
        osint_btn_row.addWidget(osint_verify_btn)
        grade_btn = QPushButton("📊 Grade Card Quality")
        grade_btn.clicked.connect(self._grade_card)
        osint_btn_row.addWidget(grade_btn)
        osint_btn_row.addStretch()
        osint_form.addRow("", osint_btn_row)
        osint_layout.addLayout(osint_form)
        
        self.osint_result_text = QTextEdit()
        self.osint_result_text.setReadOnly(True)
        self.osint_result_text.setPlaceholderText(
            "7-Step OSINT Protocol:\n"
            "  1. TruePeopleSearch — name + state lookup\n"
            "  2. FastPeopleSearch — phone + carrier validation\n"
            "  3. Whitepages — address history confirmation\n"
            "  4. Spokeo — email + social footprint\n"
            "  5. ThatsThem — IP + email cross-ref\n"
            "  6. Property records — homeowner status\n"
            "  7. Data consistency — cross-check all sources\n\n"
            "Card Quality Grades: PREMIUM (85-95%) | DEGRADED (30-50%) | LOW (10-25%)"
        )
        osint_layout.addWidget(self.osint_result_text)
        self.shields_tabs.addTab(osint_widget, "OSINT / Quality")
        
        # --- Purchase History Sub-Tab ---
        ph_widget = QWidget()
        ph_layout = QVBoxLayout(ph_widget)
        ph_layout.addWidget(QLabel("PURCHASE HISTORY INJECTION"))
        
        ph_form = QFormLayout()
        self.ph_profile_path = QLineEdit()
        self.ph_profile_path.setPlaceholderText("/opt/titan/profiles/titan_XXXXXX")
        ph_form.addRow("Profile Path:", self.ph_profile_path)
        self.ph_months = QSpinBox()
        self.ph_months.setRange(1, 24)
        self.ph_months.setValue(6)
        self.ph_months.setSuffix(" months")
        ph_form.addRow("History Depth:", self.ph_months)
        
        ph_btn = QPushButton("💳 Inject Purchase History")
        ph_btn.clicked.connect(self._inject_purchase_history)
        ph_form.addRow("", ph_btn)
        ph_layout.addLayout(ph_form)
        
        self.ph_result_text = QTextEdit()
        self.ph_result_text.setReadOnly(True)
        self.ph_result_text.setPlaceholderText(
            "Injects realistic aged purchase records into browser profile:\n"
            "  • Order confirmation cookies (Amazon, eBay, Walmart)\n"
            "  • Commerce localStorage (cart data, wish lists)\n"
            "  • Autofill data (CC holder info, shipping address)\n"
            "  • Merchant cache artifacts (session IDs, device tokens)"
        )
        ph_layout.addWidget(self.ph_result_text)
        self.shields_tabs.addTab(ph_widget, "Purchase Hist")
        
        self.main_tabs.addTab(shields_tab, "SHIELDS")
        
        # ═══════════════════════════════════════════════════════════════════
        # Tab 4: KYC — VIRTUAL CAMERA CONTROLLER
        # ═══════════════════════════════════════════════════════════════════
        kyc_tab = QWidget()
        kyc_layout = QVBoxLayout(kyc_tab)
        kyc_layout.setSpacing(10)
        
        kyc_header = QLabel("VERIFICATION COMPLIANCE")
        kyc_header.setFont(QFont("Inter", 16, QFont.Weight.Bold))
        kyc_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        kyc_header.setStyleSheet("color: #3A75C4;")
        kyc_layout.addWidget(kyc_header)
        
        kyc_subtitle = QLabel("System-Level Virtual Camera Controller — Works with ANY app")
        kyc_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        kyc_subtitle.setStyleSheet("color: #94A3B8; font-size: 11px;")
        kyc_layout.addWidget(kyc_subtitle)
        
        # KYC Controls
        kyc_controls = QHBoxLayout()
        
        # Left: Source image
        kyc_src_group = QGroupBox("📷 Source Image")
        kyc_src_layout = QVBoxLayout(kyc_src_group)
        self.kyc_image_label = QLabel("No image loaded\n\nClick 'Load Image'\nto select a face photo")
        self.kyc_image_label.setMinimumSize(220, 260)
        self.kyc_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.kyc_image_label.setStyleSheet("background-color: #1C2330; border: 2px dashed #2A3444; border-radius: 8px;")
        kyc_src_layout.addWidget(self.kyc_image_label)
        self.kyc_load_btn = QPushButton("📁 Load Image")
        self.kyc_load_btn.setMinimumHeight(30)
        self.kyc_load_btn.clicked.connect(self._kyc_load_image)
        kyc_src_layout.addWidget(self.kyc_load_btn)
        kyc_controls.addWidget(kyc_src_group)
        
        # Right: Reenactment controls
        kyc_ctrl_group = QGroupBox("🎛️ Reenactment Controls")
        kyc_ctrl_layout = QVBoxLayout(kyc_ctrl_group)
        
        ctrl_form = QFormLayout()
        self.kyc_motion_combo = QComboBox()
        self.kyc_motion_combo.addItems([
            "Natural Blink", "Gentle Smile", "Head Turn Left",
            "Head Turn Right", "Nod Yes", "Nod No", "Breathing Idle"
        ])
        ctrl_form.addRow("Motion:", self.kyc_motion_combo)
        
        self.kyc_head_spin = QSpinBox()
        self.kyc_head_spin.setRange(0, 200)
        self.kyc_head_spin.setValue(100)
        self.kyc_head_spin.setSuffix("%")
        ctrl_form.addRow("Head Rotation:", self.kyc_head_spin)
        
        self.kyc_expr_spin = QSpinBox()
        self.kyc_expr_spin.setRange(0, 200)
        self.kyc_expr_spin.setValue(100)
        self.kyc_expr_spin.setSuffix("%")
        ctrl_form.addRow("Expression:", self.kyc_expr_spin)
        
        self.kyc_blink_spin = QSpinBox()
        self.kyc_blink_spin.setRange(0, 100)
        self.kyc_blink_spin.setValue(30)
        self.kyc_blink_spin.setSuffix("/s")
        ctrl_form.addRow("Blink Freq:", self.kyc_blink_spin)
        
        kyc_ctrl_layout.addLayout(ctrl_form)
        
        self.kyc_loop_check = QCheckBox("Loop motion continuously")
        self.kyc_loop_check.setChecked(True)
        kyc_ctrl_layout.addWidget(self.kyc_loop_check)
        
        self.kyc_shield_check = QCheckBox("Enable Integrity Shield (hide virtual camera)")
        self.kyc_shield_check.setChecked(True)
        kyc_ctrl_layout.addWidget(self.kyc_shield_check)
        
        kyc_ctrl_layout.addStretch()
        kyc_controls.addWidget(kyc_ctrl_group)
        
        kyc_layout.addLayout(kyc_controls)
        
        # Status
        kyc_status_group = QGroupBox("📡 Camera Status")
        kyc_status_layout = QHBoxLayout(kyc_status_group)
        kyc_status_layout.addWidget(QLabel("Device:"))
        self.kyc_device_label = QLabel("/dev/video10")
        self.kyc_device_label.setStyleSheet("color: #3A75C4; font-family: 'JetBrains Mono', monospace;")
        kyc_status_layout.addWidget(self.kyc_device_label)
        kyc_status_layout.addStretch()
        self.kyc_status_indicator = QLabel("⚪ STOPPED")
        self.kyc_status_indicator.setFont(QFont("Inter", 11, QFont.Weight.Bold))
        kyc_status_layout.addWidget(self.kyc_status_indicator)
        kyc_layout.addWidget(kyc_status_group)
        
        # Buttons
        kyc_btn_layout = QHBoxLayout()
        self.kyc_start_btn = QPushButton("▶️ START STREAM")
        self.kyc_start_btn.setMinimumHeight(45)
        self.kyc_start_btn.setFont(QFont("Inter", 11, QFont.Weight.Bold))
        self.kyc_start_btn.setStyleSheet("QPushButton{background:#2E7D32;color:white;border:none;border-radius:8px;} QPushButton:hover{background:#388E3C;}")
        self.kyc_start_btn.clicked.connect(self._kyc_start)
        kyc_btn_layout.addWidget(self.kyc_start_btn)
        
        self.kyc_stop_btn = QPushButton("⏹️ STOP")
        self.kyc_stop_btn.setMinimumHeight(45)
        self.kyc_stop_btn.setEnabled(False)
        self.kyc_stop_btn.setStyleSheet("QPushButton{background:#D32F2F;color:white;border:none;border-radius:8px;} QPushButton:hover{background:#EF5350;} QPushButton:disabled{background:#2A3444;color:#64748B;}")
        self.kyc_stop_btn.clicked.connect(self._kyc_stop)
        kyc_btn_layout.addWidget(self.kyc_stop_btn)
        kyc_layout.addLayout(kyc_btn_layout)
        
        # Log
        self.kyc_log = QTextEdit()
        self.kyc_log.setReadOnly(True)
        self.kyc_log.setMaximumHeight(100)
        self.kyc_log.setPlaceholderText("KYC operation log...")
        kyc_layout.addWidget(self.kyc_log)
        
        self.main_tabs.addTab(kyc_tab, "KYC")
        
        # ═══════════════════════════════════════════════════════════════════
        # Tab 5: SYSTEM HEALTH HUD (Global Status Dashboard)
        # ═══════════════════════════════════════════════════════════════════
        health_tab = QWidget()
        health_layout = QVBoxLayout(health_tab)
        health_layout.setSpacing(8)
        
        hud_header = QLabel("SYSTEM HEALTH HUD")
        hud_header.setFont(QFont("JetBrains Mono", 16, QFont.Weight.Bold))
        hud_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hud_header.setStyleSheet("color: #3A75C4;")
        health_layout.addWidget(hud_header)
        
        # --- System Resources Row ---
        res_group = QGroupBox("SYSTEM RESOURCES")
        res_layout = QHBoxLayout(res_group)
        
        # CPU
        cpu_panel = QVBoxLayout()
        cpu_panel.addWidget(QLabel("CPU LOAD"))
        self.hud_cpu_bar = QProgressBar()
        self.hud_cpu_bar.setRange(0, 100)
        self.hud_cpu_bar.setValue(0)
        self.hud_cpu_bar.setFormat("%v%")
        self.hud_cpu_bar.setMinimumHeight(28)
        cpu_panel.addWidget(self.hud_cpu_bar)
        self.hud_cpu_label = QLabel("-- %")
        self.hud_cpu_label.setStyleSheet("color: #00ff88; font-family: 'JetBrains Mono', monospace; font-size: 13px;")
        self.hud_cpu_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cpu_panel.addWidget(self.hud_cpu_label)
        res_layout.addLayout(cpu_panel)
        
        # Memory
        mem_panel = QVBoxLayout()
        mem_panel.addWidget(QLabel("MEMORY"))
        self.hud_mem_bar = QProgressBar()
        self.hud_mem_bar.setRange(0, 100)
        self.hud_mem_bar.setValue(0)
        self.hud_mem_bar.setFormat("%v%")
        self.hud_mem_bar.setMinimumHeight(28)
        mem_panel.addWidget(self.hud_mem_bar)
        self.hud_mem_label = QLabel("-- / -- MB")
        self.hud_mem_label.setStyleSheet("color: #00ff88; font-family: 'JetBrains Mono', monospace; font-size: 13px;")
        self.hud_mem_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mem_panel.addWidget(self.hud_mem_label)
        res_layout.addLayout(mem_panel)
        
        # Disk / tmpfs
        disk_panel = QVBoxLayout()
        disk_panel.addWidget(QLabel("OVERLAY (tmpfs)"))
        self.hud_disk_bar = QProgressBar()
        self.hud_disk_bar.setRange(0, 100)
        self.hud_disk_bar.setValue(0)
        self.hud_disk_bar.setFormat("%v%")
        self.hud_disk_bar.setMinimumHeight(28)
        disk_panel.addWidget(self.hud_disk_bar)
        self.hud_disk_label = QLabel("-- / -- MB")
        self.hud_disk_label.setStyleSheet("color: #00ff88; font-family: 'JetBrains Mono', monospace; font-size: 13px;")
        self.hud_disk_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        disk_panel.addWidget(self.hud_disk_label)
        res_layout.addLayout(disk_panel)
        
        health_layout.addWidget(res_group)
        
        # --- Privacy Services Status ---
        svc_group = QGroupBox("PRIVACY SERVICES")
        svc_layout = QFormLayout(svc_group)
        
        self.hud_services = {}
        service_list = [
            ("titan_hw", "Kernel Hardware Shield (titan_hw.ko)"),
            ("ebpf", "eBPF Network Shield (XDP)"),
            ("unbound", "DNS Resolver (Unbound)"),
            ("tor", "Tor Service"),
            ("vpn", "Lucid VPN"),
            ("cockpit", "Cockpit Daemon"),
            ("pulseaudio", "PulseAudio (44100Hz locked)"),
            ("xrdp", "xrdp RDP Server (port 3389)"),
            ("vnc", "VNC Server (port 5901)"),
        ]
        for svc_id, svc_name in service_list:
            badge = QLabel("⚪ UNKNOWN")
            badge.setStyleSheet("color: #556; font-family: 'JetBrains Mono', monospace; font-weight: bold;")
            svc_layout.addRow(svc_name + ":", badge)
            self.hud_services[svc_id] = badge
        
        health_layout.addWidget(svc_group)
        
        # --- Network & Connectivity ---
        net_group = QGroupBox("NETWORK & CONNECTIVITY")
        net_layout_hud = QFormLayout(net_group)
        
        self.hud_exit_ip = QLabel("--")
        self.hud_exit_ip.setStyleSheet("color: #40E0FF; font-family: 'JetBrains Mono', monospace;")
        net_layout_hud.addRow("Exit IP:", self.hud_exit_ip)
        
        self.hud_dns_status = QLabel("--")
        self.hud_dns_status.setStyleSheet("color: #556; font-family: 'JetBrains Mono', monospace;")
        net_layout_hud.addRow("DNS Leak Test:", self.hud_dns_status)
        
        self.hud_latency = QLabel("--")
        self.hud_latency.setStyleSheet("color: #556; font-family: 'JetBrains Mono', monospace;")
        net_layout_hud.addRow("Latency:", self.hud_latency)
        
        health_layout.addWidget(net_group)
        
        # Refresh button
        hud_btn_layout = QHBoxLayout()
        self.hud_refresh_btn = QPushButton("🔄 REFRESH STATUS")
        self.hud_refresh_btn.setMinimumHeight(40)
        self.hud_refresh_btn.setStyleSheet(
            "QPushButton { background-color: #1A2D4A; color: #4A8AD8; "
            "border: 1px solid #3A75C4; font-weight: bold; border-radius: 6px; }"
            "QPushButton:hover { background-color: #3A75C4; color: white; }"
        )
        self.hud_refresh_btn.clicked.connect(self._refresh_health_hud)
        hud_btn_layout.addWidget(self.hud_refresh_btn)
        health_layout.addLayout(hud_btn_layout)
        
        health_layout.addStretch()
        self.main_tabs.addTab(health_tab, "HEALTH")
        
        # ═══════════════════════════════════════════════════════════════════
        # Tab 6: FORENSIC MONITOR — 24/7 System Analysis
        # ═══════════════════════════════════════════════════════════════════
        forensic_tab = QWidget()
        forensic_layout = QVBoxLayout(forensic_tab)
        forensic_layout.setSpacing(6)
        
        forensic_header = QLabel("🔍 24/7 FORENSIC MONITOR")
        forensic_header.setFont(QFont("JetBrains Mono", 16, QFont.Weight.Bold))
        forensic_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        forensic_header.setStyleSheet("color: #3A75C4;")
        forensic_layout.addWidget(forensic_header)
        
        # Instructions
        forensic_info = QLabel(
            "Real-time OS analysis using LLM to detect forensic artifacts, missing components, "
            "and detectable traces. Monitors processes, network, filesystem, logs, and Titan modules."
        )
        forensic_info.setWordWrap(True)
        forensic_info.setStyleSheet("color: #888; padding: 10px; background: #1a1a1a; border-radius: 4px; margin: 5px;")
        forensic_layout.addWidget(forensic_info)
        
        # Launch button
        forensic_btn_layout = QHBoxLayout()
        self.launch_forensic_btn = QPushButton("🔍 LAUNCH FORENSIC MONITOR")
        self.launch_forensic_btn.setFont(QFont("Inter", 12, QFont.Weight.Bold))
        self.launch_forensic_btn.setMinimumHeight(50)
        self.launch_forensic_btn.setStyleSheet("""
            QPushButton {
                background-color: #3A75C4;
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4A8AD8;
            }
            QPushButton:pressed {
                background-color: #2D5F9E;
            }
        """)
        self.launch_forensic_btn.clicked.connect(self._launch_forensic_monitor)
        forensic_btn_layout.addWidget(self.launch_forensic_btn)
        forensic_btn_layout.addStretch()
        forensic_layout.addLayout(forensic_btn_layout)
        
        # Features list
        features_group = QGroupBox("🎯 MONITORING FEATURES")
        features_layout = QVBoxLayout(features_group)
        
        features_text = QLabel(
            "• 🧠 LLM-Powered Analysis: Intelligent threat assessment using multi-provider LLM bridge\n"
            "• ⚡ Real-Time Scanning: Every 5 minutes comprehensive system analysis\n"
            "• 🚨 Threat Classification: Critical/High/Medium/Low risk levels with color-coded alerts\n"
            "• 🕵️ Forensic Detection: Identify suspicious files, processes, network activity\n"
            "• 🛡️ Countermeasures: Automatic artifact cleanup and security recommendations\n"
            "• 📊 Interactive Dashboard: Split-pane view with issues, instructions, and analysis\n"
            "• 🔍 Titan Module Status: Monitor stealth components and anti-forensics capabilities\n"
            "• 📋 Missing Components: Detect gaps in security configuration\n"
            "• 🗑️ Cache Management: 24-hour retention with manual cleanup options\n"
            "• 🔄 Auto-Refresh: Continuous monitoring with manual scan capability"
        )
        features_text.setWordWrap(True)
        features_text.setStyleSheet("color: #ccc; font-family: 'JetBrains Mono', monospace; font-size: 10px; padding: 10px;")
        features_layout.addWidget(features_text)
        
        forensic_layout.addWidget(features_group)
        
        # Status indicator
        self.forensic_status = QLabel("🟢 Ready to launch")
        self.forensic_status.setStyleSheet("color: #00ff88; font-weight: bold; padding: 10px;")
        forensic_layout.addWidget(self.forensic_status)
        
        forensic_layout.addStretch()
        self.main_tabs.addTab(forensic_tab, "FORENSIC")
        
        # ═══════════════════════════════════════════════════════════════════
        # Tab 7: V7.5 TRANSACTION MONITOR
        # ═══════════════════════════════════════════════════════════════════
        tx_tab = QWidget()
        tx_layout = QVBoxLayout(tx_tab)
        tx_layout.setSpacing(6)
        
        tx_header = QLabel("24/7 TRANSACTION MONITOR")
        tx_header.setFont(QFont("JetBrains Mono", 16, QFont.Weight.Bold))
        tx_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tx_header.setStyleSheet("color: #3A75C4;")
        tx_layout.addWidget(tx_header)
        
        # Stats row
        tx_stats_group = QGroupBox("LIVE STATISTICS")
        tx_stats_layout = QHBoxLayout(tx_stats_group)
        self.tx_total_label = QLabel("Total: --")
        self.tx_total_label.setStyleSheet("color: #40E0FF; font-size: 14px; font-weight: bold;")
        tx_stats_layout.addWidget(self.tx_total_label)
        self.tx_approved_label = QLabel("Approved: --")
        self.tx_approved_label.setStyleSheet("color: #00ff88; font-size: 14px; font-weight: bold;")
        tx_stats_layout.addWidget(self.tx_approved_label)
        self.tx_declined_label = QLabel("Declined: --")
        self.tx_declined_label.setStyleSheet("color: #EF5350; font-size: 14px; font-weight: bold;")
        tx_stats_layout.addWidget(self.tx_declined_label)
        self.tx_rate_label = QLabel("Rate: --%")
        self.tx_rate_label.setStyleSheet("color: #E6A817; font-size: 14px; font-weight: bold;")
        tx_stats_layout.addWidget(self.tx_rate_label)
        tx_layout.addWidget(tx_stats_group)
        
        # Decline decoder
        decode_group = QGroupBox("DECLINE CODE DECODER")
        decode_layout = QHBoxLayout(decode_group)
        self.decode_input = QLineEdit()
        self.decode_input.setPlaceholderText("Enter decline code (e.g. do_not_honor, 51, fraudulent)")
        decode_layout.addWidget(self.decode_input)
        self.decode_psp = QComboBox()
        self.decode_psp.addItems(["Auto-detect", "Stripe", "Adyen", "Authorize.net", "ISO 8583"])
        self.decode_psp.setMaximumWidth(140)
        decode_layout.addWidget(self.decode_psp)
        decode_btn = QPushButton("DECODE")
        decode_btn.clicked.connect(self._decode_decline)
        decode_layout.addWidget(decode_btn)
        tx_layout.addWidget(decode_group)
        
        # TX log
        self.tx_log = QTextEdit()
        self.tx_log.setReadOnly(True)
        self.tx_log.setPlaceholderText(
            "Transaction feed will appear here...\n\n"
            "The TX Monitor extension captures every payment attempt:\n"
            "  - PSP response codes (Stripe, Adyen, Braintree, Shopify, Auth.net)\n"
            "  - Approval/decline status with human-readable reasons\n"
            "  - 3DS trigger detection\n"
            "  - Success rate per site and per BIN\n\n"
            "Click REFRESH to load recent transactions."
        )
        tx_layout.addWidget(self.tx_log)
        
        tx_btn_row = QHBoxLayout()
        tx_refresh_btn = QPushButton("REFRESH")
        tx_refresh_btn.clicked.connect(self._refresh_tx_monitor)
        tx_btn_row.addWidget(tx_refresh_btn)
        tx_site_stats_btn = QPushButton("SITE STATS")
        tx_site_stats_btn.clicked.connect(self._show_tx_site_stats)
        tx_btn_row.addWidget(tx_site_stats_btn)
        tx_bin_stats_btn = QPushButton("BIN STATS")
        tx_bin_stats_btn.clicked.connect(self._show_tx_bin_stats)
        tx_btn_row.addWidget(tx_bin_stats_btn)
        tx_btn_row.addStretch()
        tx_layout.addLayout(tx_btn_row)
        
        self.main_tabs.addTab(tx_tab, "TX MONITOR")
        
        # ═══════════════════════════════════════════════════════════════════
        # Tab 7: V7.5 TARGET DISCOVERY + 3DS BYPASS
        # ═══════════════════════════════════════════════════════════════════
        disc_tab = QWidget()
        disc_layout = QVBoxLayout(disc_tab)
        disc_layout.setSpacing(4)
        
        self.disc_tabs = QTabWidget()
        self.disc_tabs.setTabPosition(QTabWidget.TabPosition.West)
        self.disc_tabs.setStyleSheet("""
            QTabBar::tab { padding: 10px 6px; min-width: 30px; background: #1C2330; color: #64748B; }
            QTabBar::tab:selected { background: #1A2D4A; color: #4A8AD8; font-weight: bold; border-left: 2px solid #3A75C4; }
            QTabBar::tab:hover { background: #232B3A; color: #E2E8F0; }
        """)
        disc_layout.addWidget(self.disc_tabs)
        
        # --- Auto-Discovery Sub-Tab ---
        auto_disc_w = QWidget()
        auto_disc_l = QVBoxLayout(auto_disc_w)
        auto_disc_l.addWidget(QLabel("AUTO-DISCOVERY ENGINE"))
        
        disc_btn_row = QHBoxLayout()
        disc_run_btn = QPushButton("RUN DISCOVERY NOW")
        disc_run_btn.setStyleSheet("QPushButton{background:#1A2D4A;color:#4A8AD8;font-weight:bold;border:1px solid #3A75C4;}")
        disc_run_btn.clicked.connect(self._run_auto_discovery)
        disc_btn_row.addWidget(disc_run_btn)
        disc_stats_btn = QPushButton("DB STATS")
        disc_stats_btn.clicked.connect(self._show_discovery_stats)
        disc_btn_row.addWidget(disc_stats_btn)
        disc_easy_btn = QPushButton("EASY 2D SITES")
        disc_easy_btn.clicked.connect(self._show_easy_sites)
        disc_btn_row.addWidget(disc_easy_btn)
        disc_shopify_btn = QPushButton("SHOPIFY STORES")
        disc_shopify_btn.clicked.connect(self._show_shopify_sites)
        disc_btn_row.addWidget(disc_shopify_btn)
        disc_btn_row.addStretch()
        auto_disc_l.addLayout(disc_btn_row)
        
        self.disc_result_text = QTextEdit()
        self.disc_result_text.setReadOnly(True)
        self.disc_result_text.setPlaceholderText(
            "Auto-Discovery finds new easy targets via Google dorking:\n"
            "  - Shopify stores (default Stripe Radar, no custom fraud)\n"
            "  - Stripe merchants (risk-based 3DS, low amounts skip)\n"
            "  - Digital goods (instant delivery, high cashout)\n"
            "  - Auth.net merchants (lowest 3DS friction of all PSPs)\n\n"
            "Runs automatically once per day. Click RUN DISCOVERY NOW for immediate scan."
        )
        auto_disc_l.addWidget(self.disc_result_text)
        self.disc_tabs.addTab(auto_disc_w, "Discovery")
        
        # --- 3DS Bypass Sub-Tab ---
        bypass_w = QWidget()
        bypass_l = QVBoxLayout(bypass_w)
        bypass_l.addWidget(QLabel("3DS BYPASS & DOWNGRADE ENGINE"))
        
        bypass_form = QFormLayout()
        self.bypass_domain = QLineEdit()
        self.bypass_domain.setPlaceholderText("e.g. g2a.com")
        bypass_form.addRow("Domain:", self.bypass_domain)
        self.bypass_psp = QComboBox()
        self.bypass_psp.addItems(["stripe", "adyen", "worldpay", "authorize_net", "braintree", "shopify_payments", "cybersource", "unknown"])
        bypass_form.addRow("PSP:", self.bypass_psp)
        self.bypass_country = QComboBox()
        self.bypass_country.addItems(["US", "CA", "GB", "DE", "FR", "AU", "BR", "MX", "JP", "KR"])
        bypass_form.addRow("Card Country:", self.bypass_country)
        self.bypass_amount = QSpinBox()
        self.bypass_amount.setRange(1, 5000)
        self.bypass_amount.setValue(200)
        self.bypass_amount.setPrefix("$")
        bypass_form.addRow("Amount:", self.bypass_amount)
        
        bypass_btn_row = QHBoxLayout()
        bypass_score_btn = QPushButton("SCORE SITE")
        bypass_score_btn.clicked.connect(self._score_3ds_bypass)
        bypass_btn_row.addWidget(bypass_score_btn)
        bypass_plan_btn = QPushButton("BYPASS PLAN")
        bypass_plan_btn.clicked.connect(self._get_bypass_plan)
        bypass_btn_row.addWidget(bypass_plan_btn)
        bypass_attacks_btn = QPushButton("DOWNGRADE ATTACKS")
        bypass_attacks_btn.clicked.connect(self._show_downgrade_attacks)
        bypass_btn_row.addWidget(bypass_attacks_btn)
        bypass_psd2_btn = QPushButton("PSD2 EXPLOITS")
        bypass_psd2_btn.clicked.connect(self._show_psd2_exploits)
        bypass_btn_row.addWidget(bypass_psd2_btn)
        bypass_btn_row.addStretch()
        bypass_form.addRow("", bypass_btn_row)
        bypass_l.addLayout(bypass_form)
        
        self.bypass_result_text = QTextEdit()
        self.bypass_result_text.setReadOnly(True)
        self.bypass_result_text.setPlaceholderText(
            "Score any site's 3DS bypass potential (0-100):\n"
            "  EASY (80+) | MODERATE (60-79) | HARD (40-59) | VERY HARD (<40)\n\n"
            "Techniques: 3DS 2.0→1.0 downgrade, timeout exploit,\n"
            "frictionless abuse, PSD2 exemptions, protocol mismatch"
        )
        bypass_l.addWidget(self.bypass_result_text)
        self.disc_tabs.addTab(bypass_w, "3DS Bypass")
        
        # --- Non-VBV BINs Sub-Tab ---
        nvbv_w = QWidget()
        nvbv_l = QVBoxLayout(nvbv_w)
        nvbv_l.addWidget(QLabel("NON-VBV BIN RECOMMENDATION ENGINE"))
        
        nvbv_form = QFormLayout()
        self.nvbv_country = QComboBox()
        self.nvbv_country.addItems(["US", "CA", "GB", "FR", "DE", "AU", "JP", "BR", "MX",
                                     "NL", "IT", "ES", "BE", "KR", "TH", "SG", "AE", "ZA",
                                     "IN", "TR", "PL", "SE", "IE", "PT", "CO", "AR", "PH", "CL", "MY"])
        nvbv_form.addRow("Country:", self.nvbv_country)
        self.nvbv_target = QLineEdit()
        self.nvbv_target.setPlaceholderText("e.g. g2a.com (optional)")
        nvbv_form.addRow("Target Site:", self.nvbv_target)
        
        nvbv_btn_row = QHBoxLayout()
        nvbv_rec_btn = QPushButton("GET RECOMMENDATIONS")
        nvbv_rec_btn.clicked.connect(self._get_nvbv_recommendations)
        nvbv_btn_row.addWidget(nvbv_rec_btn)
        nvbv_all_btn = QPushButton("ALL BINs")
        nvbv_all_btn.clicked.connect(self._show_all_nvbv_bins)
        nvbv_btn_row.addWidget(nvbv_all_btn)
        nvbv_easy_btn = QPushButton("EASY COUNTRIES")
        nvbv_easy_btn.clicked.connect(self._show_easy_countries)
        nvbv_btn_row.addWidget(nvbv_easy_btn)
        nvbv_btn_row.addStretch()
        nvbv_form.addRow("", nvbv_btn_row)
        nvbv_l.addLayout(nvbv_form)
        
        self.nvbv_result_text = QTextEdit()
        self.nvbv_result_text.setReadOnly(True)
        self.nvbv_result_text.setPlaceholderText(
            "Non-VBV BIN Database — 100+ BINs across 28 countries\n"
            "  US: Chase, Wells Fargo, Citi, Capital One, BofA, USAA, Navy Federal...\n"
            "  CA: TD, RBC, BMO, Scotiabank, CIBC\n"
            "  EU: HSBC, Lloyds, Credit Mutuel, Sparkasse, ING, UniCredit...\n"
            "  LATAM: Itau, Bradesco, Bancolombia, Banamex, Galicia...\n"
            "  APAC: MUFG, Shinhan, DBS, Bangkok Bank, Maybank...\n\n"
            "Select a country and click GET RECOMMENDATIONS."
        )
        nvbv_l.addWidget(self.nvbv_result_text)
        self.disc_tabs.addTab(nvbv_w, "Non-VBV BINs")
        
        # --- Services Status Sub-Tab ---
        svc_w = QWidget()
        svc_l = QVBoxLayout(svc_w)
        svc_l.addWidget(QLabel("BACKGROUND SERVICES"))
        
        svc_btn_row = QHBoxLayout()
        svc_start_btn = QPushButton("START ALL SERVICES")
        svc_start_btn.setStyleSheet("QPushButton{background:#1A2D4A;color:#4A8AD8;font-weight:bold;}")
        svc_start_btn.clicked.connect(self._start_all_services)
        svc_btn_row.addWidget(svc_start_btn)
        svc_status_btn = QPushButton("CHECK STATUS")
        svc_status_btn.clicked.connect(self._check_services_status)
        svc_btn_row.addWidget(svc_status_btn)
        svc_feedback_btn = QPushButton("UPDATE FEEDBACK")
        svc_feedback_btn.clicked.connect(self._update_feedback)
        svc_btn_row.addWidget(svc_feedback_btn)
        svc_best_btn = QPushButton("BEST SITES (from TX data)")
        svc_best_btn.clicked.connect(self._show_best_sites)
        svc_btn_row.addWidget(svc_best_btn)
        svc_btn_row.addStretch()
        svc_l.addLayout(svc_btn_row)
        
        self.svc_result_text = QTextEdit()
        self.svc_result_text.setReadOnly(True)
        self.svc_result_text.setPlaceholderText(
            "Background Services:\n"
            "  1. TX Monitor — 24/7 capture on port 7443\n"
            "  2. Daily Auto-Discovery — finds new easy targets once/day\n"
            "  3. Operational Feedback — TX data feeds back into site/BIN scoring\n\n"
            "Click START ALL SERVICES to begin."
        )
        svc_l.addWidget(self.svc_result_text)
        self.disc_tabs.addTab(svc_w, "Services")
        
        self.main_tabs.addTab(disc_tab, "DISCOVERY")
        
        # ═══════════════════════════════════════════════════════════════════
        # Tab 9: AI INTELLIGENCE — Ollama-Powered Operations
        # ═══════════════════════════════════════════════════════════════════
        ai_tab = QWidget()
        ai_layout = QVBoxLayout(ai_tab)
        ai_layout.setSpacing(4)
        
        self.ai_tabs = QTabWidget()
        self.ai_tabs.setTabPosition(QTabWidget.TabPosition.West)
        self.ai_tabs.setStyleSheet("""
            QTabBar::tab { padding: 10px 6px; min-width: 30px; background: #1C2330; color: #64748B; }
            QTabBar::tab:selected { background: #1A2D4A; color: #E6A817; font-weight: bold; border-left: 2px solid #E6A817; }
            QTabBar::tab:hover { background: #232B3A; color: #E2E8F0; }
        """)
        ai_layout.addWidget(self.ai_tabs)
        
        # --- AI Operation Planner Sub-Tab ---
        ai_plan_w = QWidget()
        ai_plan_l = QVBoxLayout(ai_plan_w)
        ai_plan_header = QLabel("🧠 AI OPERATION PLANNER")
        ai_plan_header.setFont(QFont("JetBrains Mono", 14, QFont.Weight.Bold))
        ai_plan_header.setStyleSheet("color: #E6A817;")
        ai_plan_l.addWidget(ai_plan_header)
        ai_plan_l.addWidget(QLabel("Full AI analysis: BIN + Target + 3DS + Behavioral tuning in one call"))
        
        ai_plan_form = QFormLayout()
        self.ai_bin_input = QLineEdit()
        self.ai_bin_input.setPlaceholderText("Enter BIN (first 6 digits, e.g. 421783)")
        ai_plan_form.addRow("Card BIN:", self.ai_bin_input)
        self.ai_target_input = QLineEdit()
        self.ai_target_input.setPlaceholderText("Target domain (e.g. eneba.com)")
        ai_plan_form.addRow("Target:", self.ai_target_input)
        self.ai_amount_input = QSpinBox()
        self.ai_amount_input.setRange(1, 50000)
        self.ai_amount_input.setValue(150)
        self.ai_amount_input.setPrefix("$")
        ai_plan_form.addRow("Amount:", self.ai_amount_input)
        ai_plan_l.addLayout(ai_plan_form)
        
        ai_plan_btn_row = QHBoxLayout()
        ai_plan_btn = QPushButton("🧠 RUN FULL AI PLAN")
        ai_plan_btn.setStyleSheet("QPushButton{background:#E6A817;color:#000;font-weight:bold;padding:10px;font-size:14px;}")
        ai_plan_btn.clicked.connect(self._ai_run_plan)
        ai_plan_btn_row.addWidget(ai_plan_btn)
        ai_bin_btn = QPushButton("🔍 BIN ONLY")
        ai_bin_btn.clicked.connect(self._ai_analyze_bin)
        ai_plan_btn_row.addWidget(ai_bin_btn)
        ai_target_btn = QPushButton("🎯 TARGET ONLY")
        ai_target_btn.clicked.connect(self._ai_recon_target)
        ai_plan_btn_row.addWidget(ai_target_btn)
        ai_plan_btn_row.addStretch()
        ai_plan_l.addLayout(ai_plan_btn_row)
        
        self.ai_plan_result = QTextEdit()
        self.ai_plan_result.setReadOnly(True)
        self.ai_plan_result.setPlaceholderText(
            "AI Operation Planner — Powered by local Ollama (qwen2.5:7b + mistral:7b)\n\n"
            "Enter a BIN + Target + Amount and click RUN FULL AI PLAN.\n"
            "The AI will analyze:\n"
            "  • BIN risk scoring & bank intelligence\n"
            "  • Target antifraud engine detection\n"
            "  • 3DS bypass probability & strategy\n"
            "  • Ghost Motor behavioral tuning\n"
            "  • GO/NO-GO decision with confidence score\n\n"
            "All inference runs LOCALLY — zero external API calls."
        )
        ai_plan_l.addWidget(self.ai_plan_result)
        self.ai_tabs.addTab(ai_plan_w, "Op Planner")
        
        # --- AI 3DS Advisor Sub-Tab ---
        ai_3ds_w = QWidget()
        ai_3ds_l = QVBoxLayout(ai_3ds_w)
        ai_3ds_l.addWidget(QLabel("🛡️ AI 3DS BYPASS ADVISOR"))
        ai_3ds_form = QFormLayout()
        self.ai_3ds_bin = QLineEdit()
        self.ai_3ds_bin.setPlaceholderText("BIN (e.g. 421783)")
        ai_3ds_form.addRow("BIN:", self.ai_3ds_bin)
        self.ai_3ds_target = QLineEdit()
        self.ai_3ds_target.setPlaceholderText("Target (e.g. eneba.com)")
        ai_3ds_form.addRow("Target:", self.ai_3ds_target)
        self.ai_3ds_amount = QSpinBox()
        self.ai_3ds_amount.setRange(1, 50000)
        self.ai_3ds_amount.setValue(100)
        self.ai_3ds_amount.setPrefix("$")
        ai_3ds_form.addRow("Amount:", self.ai_3ds_amount)
        ai_3ds_l.addLayout(ai_3ds_form)
        ai_3ds_btn = QPushButton("🛡️ GET 3DS STRATEGY")
        ai_3ds_btn.setStyleSheet("QPushButton{background:#1A2D4A;color:#4A8AD8;font-weight:bold;padding:8px;}")
        ai_3ds_btn.clicked.connect(self._ai_3ds_advise)
        ai_3ds_l.addWidget(ai_3ds_btn)
        self.ai_3ds_result = QTextEdit()
        self.ai_3ds_result.setReadOnly(True)
        self.ai_3ds_result.setPlaceholderText("AI will recommend optimal 3DS bypass strategy for your card+target+amount combination.")
        ai_3ds_l.addWidget(self.ai_3ds_result)
        self.ai_tabs.addTab(ai_3ds_w, "3DS Advisor")
        
        # --- AI Behavioral Tuning Sub-Tab ---
        ai_beh_w = QWidget()
        ai_beh_l = QVBoxLayout(ai_beh_w)
        ai_beh_l.addWidget(QLabel("🎭 AI BEHAVIORAL TUNING (Ghost Motor)"))
        ai_beh_form = QFormLayout()
        self.ai_beh_target = QLineEdit()
        self.ai_beh_target.setPlaceholderText("Target (e.g. amazon.com)")
        ai_beh_form.addRow("Target:", self.ai_beh_target)
        self.ai_beh_engine = QComboBox()
        self.ai_beh_engine.addItems(["auto-detect", "forter", "riskified", "sift", "kount", "seon", "signifyd", "none"])
        ai_beh_form.addRow("Fraud Engine:", self.ai_beh_engine)
        self.ai_beh_persona = QLineEdit()
        self.ai_beh_persona.setPlaceholderText("e.g. US adult 30-45, casual shopper")
        self.ai_beh_persona.setText("US adult, casual online shopper")
        ai_beh_form.addRow("Persona:", self.ai_beh_persona)
        ai_beh_l.addLayout(ai_beh_form)
        ai_beh_btn = QPushButton("🎭 GENERATE BEHAVIORAL PROFILE")
        ai_beh_btn.setStyleSheet("QPushButton{background:#1A2D4A;color:#4A8AD8;font-weight:bold;padding:8px;}")
        ai_beh_btn.clicked.connect(self._ai_tune_behavior)
        ai_beh_l.addWidget(ai_beh_btn)
        self.ai_beh_result = QTextEdit()
        self.ai_beh_result.setReadOnly(True)
        self.ai_beh_result.setPlaceholderText(
            "AI generates per-target Ghost Motor parameters:\n"
            "  • Mouse speed & click delays\n"
            "  • Typing WPM & error rate\n"
            "  • Scroll behavior & page dwell time\n"
            "  • Form fill strategy\n"
            "  • Idle patterns\n\n"
            "Tuned specifically for the target's antifraud engine."
        )
        ai_beh_l.addWidget(self.ai_beh_result)
        self.ai_tabs.addTab(ai_beh_w, "Behavioral")
        
        # --- AI Profile Audit Sub-Tab ---
        ai_prof_w = QWidget()
        ai_prof_l = QVBoxLayout(ai_prof_w)
        ai_prof_l.addWidget(QLabel("🔬 AI PROFILE FORENSIC AUDIT"))
        ai_prof_btn_row = QHBoxLayout()
        ai_prof_btn = QPushButton("🔬 AUDIT CURRENT PROFILE")
        ai_prof_btn.setStyleSheet("QPushButton{background:#1A2D4A;color:#4A8AD8;font-weight:bold;padding:8px;}")
        ai_prof_btn.clicked.connect(self._ai_audit_profile)
        ai_prof_btn_row.addWidget(ai_prof_btn)
        ai_prof_browse = QPushButton("📁 SELECT PROFILE")
        ai_prof_browse.clicked.connect(self._ai_browse_profile)
        ai_prof_btn_row.addWidget(ai_prof_browse)
        ai_prof_btn_row.addStretch()
        ai_prof_l.addLayout(ai_prof_btn_row)
        self.ai_prof_path = QLabel("Profile: (auto-detect from Genesis output)")
        self.ai_prof_path.setStyleSheet("color: #64748B;")
        ai_prof_l.addWidget(self.ai_prof_path)
        self.ai_prof_result = QTextEdit()
        self.ai_prof_result.setReadOnly(True)
        self.ai_prof_result.setPlaceholderText(
            "AI Forensic Profile Audit:\n"
            "  • Checks for timestamp inconsistencies\n"
            "  • Detects OS/UA mismatches\n"
            "  • Validates cookie/history consistency\n"
            "  • Identifies leak vectors antifraud would catch\n"
            "  • Scores profile cleanliness 0-100\n\n"
            "Click AUDIT to scan the generated profile."
        )
        ai_prof_l.addWidget(self.ai_prof_result)
        self.ai_tabs.addTab(ai_prof_w, "Profile Audit")
        
        # --- TLS Parrot Status Sub-Tab ---
        ai_tls_w = QWidget()
        ai_tls_l = QVBoxLayout(ai_tls_w)
        ai_tls_l.addWidget(QLabel("🔒 TLS PARROT ENGINE STATUS"))
        ai_tls_btn = QPushButton("🔒 CHECK TLS STATUS")
        ai_tls_btn.setStyleSheet("QPushButton{background:#1A2D4A;color:#4A8AD8;font-weight:bold;padding:8px;}")
        ai_tls_btn.clicked.connect(self._ai_tls_status)
        ai_tls_l.addWidget(ai_tls_btn)
        self.ai_tls_result = QTextEdit()
        self.ai_tls_result.setReadOnly(True)
        self.ai_tls_result.setPlaceholderText(
            "TLS Parrot Engine V7.5:\n"
            "  • JA4+ fingerprint parroting\n"
            "  • Per-session cipher/extension shuffling\n"
            "  • Dynamic GREASE rotation\n"
            "  • Chrome/Firefox/Edge/Safari templates\n\n"
            "Click CHECK to verify TLS configuration."
        )
        ai_tls_l.addWidget(self.ai_tls_result)
        self.ai_tabs.addTab(ai_tls_w, "TLS Parrot")
        
        # --- AI Status Sub-Tab ---
        ai_status_w = QWidget()
        ai_status_l = QVBoxLayout(ai_status_w)
        ai_status_l.addWidget(QLabel("⚡ AI ENGINE STATUS"))
        ai_status_btn = QPushButton("⚡ REFRESH STATUS")
        ai_status_btn.clicked.connect(self._ai_refresh_status)
        ai_status_l.addWidget(ai_status_btn)
        self.ai_status_result = QTextEdit()
        self.ai_status_result.setReadOnly(True)
        ai_status_l.addWidget(self.ai_status_result)
        self.ai_tabs.addTab(ai_status_w, "AI Status")
        
        self.main_tabs.addTab(ai_tab, "🧠 AI INTEL")
        
        # Start HUD auto-refresh timer (every 5 seconds)
        self._hud_timer = QTimer(self)
        self._hud_timer.timeout.connect(self._refresh_health_hud)
        self._hud_timer.start(5000)
        QTimer.singleShot(500, self._refresh_health_hud)
        
        # Auto-refresh TX monitor every 10 seconds
        self._tx_timer = QTimer(self)
        self._tx_timer.timeout.connect(self._refresh_tx_stats_silent)
        self._tx_timer.start(10000)
        
        # Auto-start background services
        if V703_AVAILABLE:
            QTimer.singleShot(2000, self._auto_start_services)
        
        # Store KYC state
        self._kyc_source_path = None
        self._kyc_controller = None
    
    def _kyc_load_image(self):
        """Load source face image for KYC"""
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Face Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if path:
            self._kyc_source_path = path
            self.kyc_image_label.setText(f"✅ Loaded:\n{os.path.basename(path)}")
            self.kyc_log.append(f"[+] Image loaded: {path}")
    
    def _kyc_start(self):
        """Start KYC virtual camera stream with neural reenactment"""
        if not KYC_AVAILABLE:
            self.kyc_log.append("[!] KYC module not available")
            QMessageBox.warning(self, "KYC", "KYC core module not available.\nCheck v4l2loopback is installed.")
            return
        if not self._kyc_source_path:
            self.kyc_log.append("[!] No source image loaded")
            QMessageBox.warning(self, "KYC", "Load a face image first.")
            return
        try:
            if not self._kyc_controller:
                self._kyc_controller = KYCController()
            self._kyc_controller.setup_virtual_camera()
            
            # Map motion combo index to MotionType
            from kyc_core import MotionType
            motion_map = {
                0: MotionType.BLINK,
                1: MotionType.SMILE,
                2: MotionType.HEAD_LEFT,
                3: MotionType.HEAD_RIGHT,
                4: MotionType.HEAD_NOD,
                5: MotionType.HEAD_NOD,
                6: MotionType.NEUTRAL,
            }
            motion_type = motion_map.get(self.kyc_motion_combo.currentIndex(), MotionType.NEUTRAL)
            
            # Build reenactment config from GUI sliders
            config = ReenactmentConfig(
                source_image=self._kyc_source_path,
                motion_type=motion_type,
                loop=self.kyc_loop_check.isChecked(),
                head_rotation_intensity=self.kyc_head_spin.value() / 100,
                expression_intensity=self.kyc_expr_spin.value() / 100,
                blink_frequency=self.kyc_blink_spin.value() / 100,
            )
            
            # Try neural reenactment first, fall back to plain video
            success = self._kyc_controller.start_reenactment(config)
            if not success:
                self.kyc_log.append("[~] Reenactment unavailable — falling back to plain stream")
                self._kyc_controller.stream_image(self._kyc_source_path)
            
            self.kyc_status_indicator.setText("🟢 STREAMING")
            self.kyc_status_indicator.setStyleSheet("color: #00ff88;")
            self.kyc_start_btn.setEnabled(False)
            self.kyc_stop_btn.setEnabled(True)
            self.kyc_log.append(f"[+] Stream started — {self.kyc_motion_combo.currentText()} "
                                f"(head={self.kyc_head_spin.value()}% expr={self.kyc_expr_spin.value()}% "
                                f"blink={self.kyc_blink_spin.value()}/s)")
        except Exception as e:
            self.kyc_log.append(f"[!] Error: {e}")
            QMessageBox.critical(self, "KYC Error", str(e))
    
    def _kyc_stop(self):
        """Stop KYC virtual camera stream"""
        try:
            if self._kyc_controller:
                self._kyc_controller.stop_stream()
            self.kyc_status_indicator.setText("⚪ STOPPED")
            self.kyc_status_indicator.setStyleSheet("color: #888;")
            self.kyc_start_btn.setEnabled(True)
            self.kyc_stop_btn.setEnabled(False)
            self.kyc_log.append("[+] Stream stopped")
        except Exception as e:
            self.kyc_log.append(f"[!] Error stopping: {e}")
    
    def _refresh_health_hud(self):
        """Refresh System Health HUD — CPU, memory, disk, service status badges"""
        try:
            import psutil
            
            # CPU
            cpu = psutil.cpu_percent(interval=0)
            self.hud_cpu_bar.setValue(int(cpu))
            self.hud_cpu_label.setText(f"{cpu:.1f}%")
            
            # Memory
            mem = psutil.virtual_memory()
            mem_pct = mem.percent
            self.hud_mem_bar.setValue(int(mem_pct))
            self.hud_mem_label.setText(f"{mem.used // (1024*1024)} / {mem.total // (1024*1024)} MB")
            
            # Disk / tmpfs overlay
            try:
                disk = psutil.disk_usage('/run/live/overlay' if os.path.exists('/run/live/overlay') else '/')
                self.hud_disk_bar.setValue(int(disk.percent))
                self.hud_disk_label.setText(f"{disk.used // (1024*1024)} / {disk.total // (1024*1024)} MB")
            except Exception:
                self.hud_disk_bar.setValue(0)
                self.hud_disk_label.setText("N/A")
            
        except ImportError:
            self.hud_cpu_label.setText("psutil not available")
            self.hud_mem_label.setText("psutil not available")
        
        # Service status checks
        svc_checks = {
            "titan_hw": lambda: os.path.exists("/sys/module/titan_hw"),
            "ebpf": lambda: os.path.exists("/sys/fs/bpf/titan_xdp"),
            "unbound": lambda: os.system("systemctl is-active --quiet unbound 2>/dev/null") == 0,
            "tor": lambda: os.system("systemctl is-active --quiet tor 2>/dev/null") == 0,
            "vpn": lambda: os.path.exists("/run/titan-vpn.pid") or os.system("pgrep -f xray >/dev/null 2>&1") == 0,
            "cockpit": lambda: os.path.exists("/run/titan/cockpit.sock"),
            "pulseaudio": lambda: os.system("pactl info >/dev/null 2>&1") == 0,
            "xrdp": lambda: os.system("systemctl is-active --quiet xrdp 2>/dev/null") == 0,
            "vnc": lambda: os.system("systemctl is-active --quiet titan-vnc 2>/dev/null") == 0,
        }
        
        for svc_id, check_fn in svc_checks.items():
            badge = self.hud_services.get(svc_id)
            if badge:
                try:
                    active = check_fn()
                    if active:
                        badge.setText("🟢 ACTIVE")
                        badge.setStyleSheet("color: #00ff88; font-family: 'JetBrains Mono', monospace; font-weight: bold;")
                    else:
                        badge.setText("⚪ INACTIVE")
                        badge.setStyleSheet("color: #556; font-family: 'JetBrains Mono', monospace; font-weight: bold;")
                except Exception:
                    badge.setText("⚠️ ERROR")
                    badge.setStyleSheet("color: #E6A817; font-family: 'JetBrains Mono', monospace; font-weight: bold;")
    
    def apply_dark_theme(self):
        """Apply Enterprise HRUX theme from centralized theme module."""
        try:
            from titan_enterprise_theme import apply_enterprise_theme
            apply_enterprise_theme(self, "#00d4ff")
        except ImportError:
            pass  # Fallback: no theme applied
    
    def load_targets(self):
        """Load target presets into dropdown"""
        self.target_combo.clear()
        
        for target in list_targets():
            self.target_combo.addItem(
                f"{target['name']} ({target['domain']})",
                target['id']
            )
    
    def on_target_changed(self, index):
        """Handle target selection change"""
        if index < 0:
            return
        
        target_id = self.target_combo.currentData()
        self.current_target = get_target_preset(target_id)
        
        if self.current_target:
            info = (
                f"Category: {self.current_target.category.value} | "
                f"3DS Risk: {self.current_target.three_ds_rate*100:.0f}% | "
                f"KYC: {'Required' if self.current_target.kyc_required else 'No'} | "
                f"Min Age: {self.current_target.min_age_days}d"
            )
            self.target_info.setText(info)
            
            # Update recommended settings
            self.profile_age.setValue(self.current_target.recommended_age_days)
            self.storage_size.setValue(self.current_target.recommended_storage_mb)
            
            # Update archetype
            archetype_map = {
                "student_developer": 0,
                "professional": 1,
                "gamer": 2,
                "casual_shopper": 3,
                "retiree": 4,
            }
            arch_idx = archetype_map.get(self.current_target.recommended_archetype, 0)
            self.archetype_combo.setCurrentIndex(arch_idx)
            
            # Update hardware
            hw_map = {
                "macbook_m2_pro": 0,
                "windows_desktop_nvidia": 1,
                "windows_gaming_rtx4080": 2,
                "windows_laptop_intel": 3,
                "linux_desktop": 4,
            }
            hw_idx = hw_map.get(self.current_target.recommended_hardware, 0)
            self.hardware_combo.setCurrentIndex(hw_idx)
    
    def _on_net_mode_changed(self, index):
        """Toggle between Proxy and VPN UI elements"""
        is_proxy = (index == 0)
        is_vpn = (index > 0)
        # Proxy fields
        self.proxy_url.setVisible(is_proxy)
        self.proxy_url_label.setVisible(is_proxy)
        self.proxy_type.setVisible(is_proxy)
        self.test_proxy_btn.setVisible(is_proxy)
        self.proxy_type_label.setVisible(is_proxy)
        # VPN fields
        self.vpn_connect_btn.setVisible(is_vpn)
        self.vpn_disconnect_btn.setVisible(is_vpn)
        self.vpn_setup_btn.setVisible(is_vpn)
        self.vpn_control_label.setVisible(is_vpn)
        # Reset status
        if is_vpn:
            self.proxy_status.setText("VPN mode — click Connect or Setup")
            self.proxy_status.setStyleSheet("color: #00d4ff;")
        else:
            self.proxy_status.setText("Not tested")
            self.proxy_status.setStyleSheet("color: #888;")
    
    def _vpn_connect(self):
        """Connect Lucid VPN"""
        self.proxy_status.setText("🔄 Connecting Lucid VPN...")
        self.proxy_status.setStyleSheet("color: #00d4ff;")
        try:
            from lucid_vpn import LucidVPN, VPNStatus
            vpn = LucidVPN()
            vpn.load_config()
            if not vpn.is_configured():
                self.proxy_status.setText("⚠️ VPN not configured. Click Setup first.")
                self.proxy_status.setStyleSheet("color: #ffaa00;")
                return
            state = vpn.connect()
            if state.status == VPNStatus.CONNECTED:
                self.proxy_status.setText(f"✅ VPN Connected — Exit: {state.exit_ip}")
                self.proxy_status.setStyleSheet("color: #00ff00;")
                self.proxy_url.setText(vpn.get_socks5_url() or "")
            else:
                self.proxy_status.setText(f"❌ VPN Error: {state.error_message}")
                self.proxy_status.setStyleSheet("color: #ff0000;")
        except ImportError:
            self.proxy_status.setText("❌ lucid_vpn module not found")
            self.proxy_status.setStyleSheet("color: #ff0000;")
        except Exception as e:
            self.proxy_status.setText(f"❌ {str(e)[:60]}")
            self.proxy_status.setStyleSheet("color: #ff0000;")
    
    def _vpn_disconnect(self):
        """Disconnect Lucid VPN"""
        try:
            from lucid_vpn import LucidVPN
            vpn = LucidVPN()
            vpn.load_config()
            vpn.disconnect()
            self.proxy_status.setText("VPN Disconnected")
            self.proxy_status.setStyleSheet("color: #888;")
            self.proxy_url.setText("")
        except Exception as e:
            self.proxy_status.setText(f"❌ {str(e)[:60]}")
            self.proxy_status.setStyleSheet("color: #ff0000;")
    
    def _vpn_open_setup(self):
        """Open VPN setup wizard in terminal"""
        import subprocess
        try:
            subprocess.Popen(
                ["x-terminal-emulator", "-e", "python3", "/opt/titan/bin/titan-vpn-setup"],
                start_new_session=True
            )
            self.proxy_status.setText("VPN Setup wizard opened in terminal")
            self.proxy_status.setStyleSheet("color: #00d4ff;")
        except Exception:
            try:
                subprocess.Popen(
                    ["xterm", "-e", "python3 /opt/titan/bin/titan-vpn-setup"],
                    start_new_session=True
                )
            except Exception as e:
                self.proxy_status.setText(f"❌ Could not open terminal: {e}")
                self.proxy_status.setStyleSheet("color: #ff0000;")
    
    def get_active_proxy_url(self) -> str:
        """Get the active proxy URL regardless of mode (proxy or VPN)"""
        mode_idx = self.net_mode.currentIndex()
        if mode_idx == 0:
            return self.proxy_url.text().strip()
        else:
            try:
                from lucid_vpn import LucidVPN, VPNStatus
                vpn = LucidVPN()
                vpn.load_config()
                if vpn.get_state().status == VPNStatus.CONNECTED:
                    return vpn.get_socks5_url() or ""
            except Exception:
                pass
            return self.proxy_url.text().strip()
    
    def test_proxy(self):
        """Test proxy connection with real HTTP request"""
        proxy = self.get_active_proxy_url()
        if not proxy:
            self.proxy_status.setText("⚠️ Enter proxy URL first")
            self.proxy_status.setStyleSheet("color: #ffaa00;")
            return
        
        self.proxy_status.setText("🔄 Testing...")
        self.proxy_status.setStyleSheet("color: #00d4ff;")
        
        self._proxy_test_worker = ProxyTestWorker(proxy)
        self._proxy_test_worker.finished.connect(self._proxy_test_complete)
        self._proxy_test_worker.start()
    
    def _proxy_test_complete(self, result):
        if result.get("success"):
            ip = result.get("ip", "?")
            geo = result.get("geo", "")
            latency = result.get("latency_ms", 0)
            self.proxy_status.setText(f"✅ Connected — IP: {ip} ({geo}) [{latency:.0f}ms]")
            self.proxy_status.setStyleSheet("color: #00ff00;")
        else:
            err = result.get("error", "Unknown error")
            self.proxy_status.setText(f"❌ {err}")
            self.proxy_status.setStyleSheet("color: #ff0000;")
    
    def validate_card(self):
        """Validate card with Cerberus"""
        pan = self.card_pan.text().replace(" ", "").replace("-", "")
        exp = self.card_exp.text()
        cvv = self.card_cvv.text()
        holder = self.card_holder.text()
        
        if not pan or not exp or not cvv:
            self.card_status.setText("⚠️ Enter card details first")
            self.card_status.setStyleSheet("color: #ffaa00;")
            return
        
        # Parse expiry
        try:
            parts = exp.split("/")
            exp_month = int(parts[0])
            exp_year = int(parts[1])
            if exp_year < 100:
                exp_year += 2000
        except:
            self.card_status.setText("⚠️ Invalid expiry format (MM/YY)")
            self.card_status.setStyleSheet("color: #ffaa00;")
            return
        
        self.card_status.setText("🔄 Validating...")
        self.card_status.setStyleSheet("color: #00d4ff;")
        self.validate_card_btn.setEnabled(False)
        
        # Start validation worker
        self.validation_worker = CardValidationWorker({
            "pan": pan,
            "exp_month": exp_month,
            "exp_year": exp_year,
            "cvv": cvv,
            "holder_name": holder,
        })
        self.validation_worker.finished.connect(self._card_validation_complete)
        self.validation_worker.start()
    
    def _card_validation_complete(self, result):
        self.validate_card_btn.setEnabled(True)
        
        if isinstance(result, dict) and "error" in result:
            self.card_status.setText(f"❌ Error: {result['error']}")
            self.card_status.setStyleSheet("color: #ff0000;")
            return
        
        self.card_validation_result = result
        
        if hasattr(result, 'status'):
            if result.status == CardStatus.LIVE:
                self.card_status.setText(
                    f"🟢 LIVE ({result.card_type} {result.card_tier}, {result.issuer})\n"
                    f"3DS Risk: {result.three_ds_likelihood} | AVS: {result.avs_result}"
                )
                self.card_status.setStyleSheet("color: #00ff00;")
            elif result.status == CardStatus.DEAD:
                self.card_status.setText("🔴 DEAD - Card declined")
                self.card_status.setStyleSheet("color: #ff0000;")
            else:
                self.card_status.setText(f"🟡 {result.status.value}")
                self.card_status.setStyleSheet("color: #ffaa00;")
        else:
            # Fallback for simple result
            self.card_status.setText("🟢 Validation complete")
            self.card_status.setStyleSheet("color: #00ff00;")
    
    def forge_profile(self):
        """Forge the browser profile"""
        if not self.current_target:
            QMessageBox.warning(self, "Error", "Please select a target first")
            return
        
        # Validate required fields
        if not self.persona_name.text() or not self.persona_email.text():
            QMessageBox.warning(self, "Error", "Please enter persona name and email")
            return
        
        if not self.persona_address.text() or not self.persona_city.text():
            QMessageBox.warning(self, "Error", "Please enter billing address")
            return
        
        # Prepare config
        config = {
            "persona_name": self.persona_name.text(),
            "persona_email": self.persona_email.text(),
            "phone": self.persona_phone.text(),
            "address": self.persona_address.text(),
            "city": self.persona_city.text(),
            "state": self.persona_state.text(),
            "zip": self.persona_zip.text(),
            "country": self.persona_country.currentText(),
            "age_days": self.profile_age.value(),
            "storage_mb": self.storage_size.value(),
        }
        
        # Start forge
        self.forge_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.status_text.clear()
        
        self.forge_worker = ProfileForgeWorker(config, self.current_target)
        self.forge_worker.progress.connect(self._forge_progress)
        self.forge_worker.finished.connect(self._forge_complete)
        self.forge_worker.start()
    
    def _forge_progress(self, message):
        self.status_text.append(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
    
    def _forge_complete(self, result):
        self.forge_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        if isinstance(result, dict) and "error" in result:
            self.status_text.append(f"\n❌ ERROR: {result['error']}")
            QMessageBox.critical(self, "Forge Failed", result['error'])
            return
        
        self.generated_profile = result
        self.launch_btn.setEnabled(True)
        
        self.status_text.append(f"\n✅ PROFILE FORGED SUCCESSFULLY")
        self.status_text.append(f"   Path: {result.profile_path}")
        self.status_text.append(f"   Size: {result.profile_size_mb:.1f} MB")
        self.status_text.append(f"   History: {result.history_entries} entries")
        self.status_text.append(f"\n📄 Handover document generated")
        self.status_text.append(f"   Ready for browser launch!")
    
    def launch_browser(self):
        """Launch browser with forged profile"""
        if not self.generated_profile:
            QMessageBox.warning(self, "Error", "Please forge a profile first")
            return
        
        proxy = self.get_active_proxy_url()
        
        # Build command
        cmd = [
            "titan-browser",
            "--profile", str(self.generated_profile.profile_path),
            "--target", self.current_target.domain,
        ]
        
        if proxy:
            cmd.extend(["--proxy", proxy])
        
        self.status_text.append(f"\n🌐 Launching browser...")
        self.status_text.append(f"   Command: {' '.join(cmd)}")
        
        # Launch browser
        import subprocess
        try:
            subprocess.Popen(cmd)
            self.status_text.append(f"\n✅ Browser launched - HANDOVER TO OPERATOR")
        except Exception as e:
            self.status_text.append(f"\n❌ Launch failed: {e}")


    # ═══════════════════════════════════════════════════════════════════
    # V7.5 INTELLIGENCE HANDLERS
    # ═══════════════════════════════════════════════════════════════════
    
    def _check_avs(self):
        """Check AVS intelligence for a country"""
        if not INTEL_AVAILABLE:
            self.avs_result_text.setPlainText("Intelligence modules not available")
            return
        country = self.avs_country_input.text().strip().upper()
        if not country:
            self.avs_result_text.setPlainText("Enter a country code (e.g. US, GB, DE, BR)")
            return
        result = get_avs_intelligence(country)
        text = f"AVS INTELLIGENCE FOR: {result['country']}\n" + "=" * 40 + "\n"
        text += f"AVS Supported: {'YES' if result['avs_supported'] else 'NO'}\n"
        text += f"Non-AVS Advantage: {'YES' if result['non_avs_advantage'] else 'NO'}\n\n"
        text += "GUIDANCE:\n" + "\n".join(f"  - {g}" for g in result["guidance"]) + "\n"
        if result["strict_merchants"]:
            text += f"\nSTRICT AVS MERCHANTS:\n" + "\n".join(f"  - {m}" for m in result["strict_merchants"])
        if result["avs_supported"]:
            text += f"\n\nAVS RESPONSE CODES:\n"
            for code, info in result["avs_codes"].items():
                text += f"  {code}: {info['match']} - {info['description']} (Risk: {info['risk']})\n"
        self.avs_result_text.setPlainText(text)
    
    def _check_visa_alerts(self):
        """Check Visa Alerts eligibility"""
        if not INTEL_AVAILABLE:
            self.visa_result_text.setPlainText("Intelligence modules not available")
            return
        country = self.visa_country_input.text().strip().upper()
        if not country:
            self.visa_result_text.setPlainText("Enter a country code (e.g. US, MX, BR)")
            return
        result = check_visa_alerts_eligible(country)
        text = f"VISA ALERTS CHECK: {result['country']}\n" + "=" * 40 + "\n"
        text += f"Eligible: {'YES' if result['visa_alerts_eligible'] else 'NO'}\n"
        text += f"{result['guidance']}\n"
        if result['enrollment_url']:
            text += f"\nEnrollment URL: {result['enrollment_url']}\n"
            intel = get_visa_alerts_intel()
            text += "\nENROLLMENT STEPS:\n" + "\n".join(intel["enrollment_steps"])
            text += "\n\nSTRATEGIES:\n" + "\n".join(f"  - {s}" for s in intel["strategies"])
        self.visa_result_text.setPlainText(text)
    
    def _score_freshness(self):
        """Score card freshness"""
        if not INTEL_AVAILABLE:
            self.fresh_result_text.setPlainText("Intelligence modules not available")
            return
        result = estimate_card_freshness(
            checked=self.fresh_checked.isChecked(),
            times_checked=self.fresh_times.value(),
            previously_used=self.fresh_used.isChecked(),
            ever_declined=self.fresh_declined.isChecked(),
        )
        text = f"CARD FRESHNESS SCORE\n" + "=" * 40 + "\n"
        text += f"Tier: {result['freshness_tier'].upper()}\n"
        text += f"Score: {result['score']}/100\n"
        text += f"Description: {result['description']}\n"
        text += f"Guidance: {result['guidance']}\n"
        color = "#00ff00" if result["score"] >= 80 else "#ffaa00" if result["score"] >= 40 else "#ff0000"
        self.fresh_result_text.setPlainText(text)
    
    def _lookup_target_intel(self):
        """Lookup target intelligence"""
        if not INTEL_AVAILABLE:
            self.ti_result_text.setPlainText("Intelligence modules not available")
            return
        query = self.ti_search.text().strip().lower().replace(" ", "_").replace("-", "_")
        if not query:
            self.ti_result_text.setPlainText("Enter a target name to search")
            return
        intel = get_target_intel(query)
        if not intel:
            matches = [t for t in INTEL_TARGETS if query in t]
            if matches:
                text = f"No exact match for '{query}'. Did you mean:\n"
                for m in matches:
                    text += f"  - {m}\n"
                self.ti_result_text.setPlainText(text)
            else:
                self.ti_result_text.setPlainText(f"No target found for '{query}'")
            return
        text = f"TARGET: {intel.name} ({intel.domain})\n" + "=" * 40 + "\n"
        text += f"Fraud Engine: {intel.fraud_engine.value}\n"
        text += f"Payment Gateway: {intel.payment_gateway.value}\n"
        text += f"Friction: {intel.friction.value}\n"
        text += f"3DS Rate: {intel.three_ds_rate*100:.0f}%\n"
        text += f"Mobile Softer: {'Yes' if intel.mobile_softer else 'No'}\n"
        if intel.notes:
            text += f"\nNOTES:\n" + "\n".join(f"  - {n}" for n in intel.notes) + "\n"
        if intel.operator_playbook:
            text += f"\nOPERATOR PLAYBOOK:\n" + "\n".join(f"  {i+1}. {p}" for i, p in enumerate(intel.operator_playbook)) + "\n"
        if intel.warming_guide:
            text += f"\nWARMING GUIDE:\n" + "\n".join(f"  - {w}" for w in intel.warming_guide) + "\n"
        if intel.warmup_sites:
            text += f"\nWARMUP SITES: {', '.join(intel.warmup_sites)}\n"
        if intel.pickup_method:
            text += f"\nPICKUP METHOD: {intel.pickup_method}\n"
        cm = intel.get_countermeasures()
        text += f"\nCOUNTERMEASURES:\n"
        text += f"  Min Profile Age: {cm.min_profile_age_days} days\n"
        text += f"  Min Storage: {cm.min_storage_mb} MB\n"
        text += f"  Require Social Footprint: {cm.require_social_footprint}\n"
        text += f"  Require Commerce History: {cm.require_commerce_history}\n"
        text += f"  Warmup Minutes: {cm.warmup_minutes}\n"
        if cm.evasion_notes:
            text += f"  Evasion Notes:\n" + "\n".join(f"    - {n}" for n in cm.evasion_notes)
        self.ti_result_text.setPlainText(text)


    # ═══════════════════════════════════════════════════════════════════
    # V7.5 SHIELDS & HARDENING HANDLERS
    # ═══════════════════════════════════════════════════════════════════
    
    def _run_master_verify(self):
        """Run titan_master_verify.py and display results"""
        self.preflight_text.clear()
        self.preflight_text.append("Running Master Verification Protocol...\n")
        import subprocess
        try:
            args = ["python3", "/opt/titan/core/titan_master_verify.py"]
            if self.generated_profile:
                args.extend(["--profile", str(self.generated_profile.profile_path)])
            result = subprocess.run(args, capture_output=True, text=True, timeout=30)
            self.preflight_text.append(result.stdout)
            if result.returncode == 0:
                self.preflight_text.append("\n✅ MASTER VERIFY: ALL GREEN")
            else:
                self.preflight_text.append("\n❌ MASTER VERIFY: FAILURES DETECTED")
                if result.stderr:
                    self.preflight_text.append(result.stderr)
        except Exception as e:
            self.preflight_text.append(f"❌ Error: {e}")
    
    def _run_deep_identity(self):
        """Run verify_deep_identity.py"""
        self.preflight_text.append("\n\nRunning Deep Identity Check...\n")
        import subprocess
        try:
            args = ["python3", "/opt/titan/core/verify_deep_identity.py", "--os", "windows_11"]
            if self.generated_profile:
                args.extend(["--profile", str(self.generated_profile.profile_path)])
            result = subprocess.run(args, capture_output=True, text=True, timeout=30)
            self.preflight_text.append(result.stdout)
            if result.returncode == 0:
                self.preflight_text.append("\n✅ STATUS: GHOST (UNDETECTABLE)")
            else:
                self.preflight_text.append("\n❌ STATUS: FLAGGED — fix environmental leaks")
        except Exception as e:
            self.preflight_text.append(f"❌ Error: {e}")
    
    def _get_target_os_enum(self):
        """Map dropdown index to target OS string"""
        idx = self.env_target_os.currentIndex()
        return ["windows_11", "windows_10", "macos_14", "macos_13"][idx]
    
    def _run_font_purge(self):
        """Phase 3.1: Font sanitization"""
        if not HARDENING_AVAILABLE:
            self.env_result_text.setPlainText("Hardening modules not available")
            return
        self.env_result_text.clear()
        self.env_result_text.append("Phase 3.1: Running Font Purge...\n")
        try:
            os_str = self._get_target_os_enum()
            os_map = {"windows_10": FontTargetOS.WINDOWS_10, "windows_11": FontTargetOS.WINDOWS_11,
                      "macos_14": FontTargetOS.MACOS_14, "macos_13": FontTargetOS.MACOS_13}
            sanitizer = FontSanitizer(os_map[os_str])
            
            hygiene = sanitizer.check_font_hygiene()
            self.env_result_text.append(f"Target OS: {os_str}")
            self.env_result_text.append(f"Linux font leaks: {len(hygiene.get('leaks', []))}")
            for leak in hygiene.get("leaks", [])[:8]:
                self.env_result_text.append(f"  ✗ {leak}")
            self.env_result_text.append(f"Missing target fonts: {len(hygiene.get('missing', []))}")
            for m in hygiene.get("missing", [])[:8]:
                self.env_result_text.append(f"  ✗ {m}")
            
            if hygiene.get("clean"):
                self.env_result_text.append("\n✅ Font environment: CLEAN")
            else:
                self.env_result_text.append("\n⚠ Font environment: DIRTY — run as root to apply")
                self.env_result_text.append("  sudo python3 -c \"from font_sanitizer import *; sanitize_fonts('" + os_str + "')\"")
        except Exception as e:
            self.env_result_text.append(f"❌ Error: {e}")
    
    def _run_audio_harden(self):
        """Phase 3.2: Audio hardening"""
        if not HARDENING_AVAILABLE:
            self.env_result_text.setPlainText("Hardening modules not available")
            return
        self.env_result_text.append("\n\nPhase 3.2: Audio Hardening...\n")
        try:
            os_str = self._get_target_os_enum()
            os_family = "windows" if "windows" in os_str else "macos"
            os_map = {"windows": AudioTargetOS.WINDOWS, "macos": AudioTargetOS.MACOS}
            hardener = AudioHardener(os_map[os_family])
            
            prefs = hardener.generate_user_js_prefs()
            self.env_result_text.append(f"Target audio profile: {os_family}")
            self.env_result_text.append(f"Prefs to write: {len(prefs) - 3}")
            self.env_result_text.append(f"  privacy.resistFingerprinting = true")
            self.env_result_text.append(f"  privacy.fingerprintingProtection = true")
            self.env_result_text.append(f"  media.default_audio_sample_rate = 44100")
            
            if self.generated_profile:
                result = hardener.apply_to_profile(str(self.generated_profile.profile_path))
                if result.user_js_updated:
                    self.env_result_text.append(f"\n✅ Audio prefs written to profile user.js")
                if result.audio_config_written:
                    self.env_result_text.append(f"✅ Audio config written for Ghost Motor")
            else:
                self.env_result_text.append("\n⚠ No profile generated — forge a profile first to apply")
        except Exception as e:
            self.env_result_text.append(f"❌ Error: {e}")
    
    def _run_tz_enforce(self):
        """Phase 3.3: Timezone enforcement"""
        if not HARDENING_AVAILABLE:
            self.env_result_text.setPlainText("Hardening modules not available")
            return
        self.env_result_text.append("\n\nPhase 3.3: Timezone Enforcement...\n")
        try:
            state = self.persona_state.text().strip().upper() or "TX"
            tz = get_timezone_for_state(state)
            self.env_result_text.append(f"Target state: {state} → Timezone: {tz}")
            
            confirm = QMessageBox.question(
                self, "Timezone Enforcement",
                f"This will:\n1. KILL all browser processes\n2. Set timezone to {tz}\n3. Sync NTP\n\nProceed?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if confirm == QMessageBox.StandardButton.Yes:
                config = TimezoneConfig(target_timezone=tz, target_state=state)
                enforcer = TimezoneEnforcer(config)
                result = enforcer.enforce()
                self.env_result_text.append(f"Timezone before: {result.timezone_before}")
                self.env_result_text.append(f"Timezone after:  {result.timezone_after}")
                self.env_result_text.append(f"Browser killed:  {result.browser_killed}")
                self.env_result_text.append(f"NTP synced:      {result.ntp_synced}")
                if result.success:
                    self.env_result_text.append(f"\n✅ Timezone enforced: {result.timezone_after}")
                else:
                    self.env_result_text.append(f"\n❌ Failed steps: {result.steps_failed}")
            else:
                self.env_result_text.append("Cancelled by operator.")
        except Exception as e:
            self.env_result_text.append(f"❌ Error: {e}")
    
    def _arm_kill_switch(self):
        """Arm the kill switch"""
        if not HARDENING_AVAILABLE:
            self.ks_status_text.setPlainText("Kill switch module not available")
            return
        try:
            profile_name = "default"
            if self.generated_profile:
                profile_name = str(Path(self.generated_profile.profile_path).name)
            
            config = KillSwitchConfig(
                profile_uuid=profile_name,
                threshold=self.ks_threshold.value(),
            )
            self._kill_switch = KillSwitch(config)
            self._kill_switch.arm()
            
            self.ks_arm_btn.setEnabled(False)
            self.ks_disarm_btn.setEnabled(True)
            self.ks_panic_btn.setEnabled(True)
            self.ks_status_text.clear()
            self.ks_status_text.append(f"🔴 KILL SWITCH ARMED")
            self.ks_status_text.append(f"   Profile: {profile_name}")
            self.ks_status_text.append(f"   Threshold: {self.ks_threshold.value()}")
            self.ks_status_text.append(f"   Monitoring: fraud_score.json every 500ms")
        except Exception as e:
            self.ks_status_text.append(f"❌ Error: {e}")
    
    def _disarm_kill_switch(self):
        """Disarm the kill switch"""
        try:
            if hasattr(self, '_kill_switch') and self._kill_switch:
                self._kill_switch.disarm()
                self._kill_switch = None
            self.ks_arm_btn.setEnabled(True)
            self.ks_disarm_btn.setEnabled(False)
            self.ks_panic_btn.setEnabled(False)
            self.ks_status_text.append("\n⬛ Kill switch DISARMED")
        except Exception as e:
            self.ks_status_text.append(f"❌ Error: {e}")
    
    def _manual_panic(self):
        """Trigger manual panic"""
        confirm = QMessageBox.warning(
            self, "MANUAL PANIC",
            "This will:\n• Kill all browsers\n• Flush hardware ID\n• Clear session\n• Rotate proxy\n\nPROCEED?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                if hasattr(self, '_kill_switch') and self._kill_switch:
                    self._kill_switch.trigger_manual_panic()
                    self.ks_status_text.append("\n⚡ PANIC EXECUTED — all countermeasures deployed")
                else:
                    self.ks_status_text.append("❌ Kill switch not armed")
            except Exception as e:
                self.ks_status_text.append(f"❌ Panic error: {e}")
    
    def _run_osint(self):
        """Run OSINT verification"""
        if not HARDENING_AVAILABLE:
            self.osint_result_text.setPlainText("OSINT modules not available")
            return
        name = self.osint_name.text().strip()
        state = self.osint_state.text().strip()
        if not name:
            self.osint_result_text.setPlainText("Enter cardholder name to verify")
            return
        self.osint_result_text.clear()
        self.osint_result_text.append(f"Running 7-Step OSINT Protocol for: {name} ({state})...\n")
        try:
            verifier = OSINTVerifier()
            report = verifier.verify(name=name, state=state)
            self.osint_result_text.append(f"Overall confidence: {report.confidence_score}/100")
            self.osint_result_text.append(f"Address verified: {report.address_verified}")
            self.osint_result_text.append(f"Phone verified: {report.phone_verified}")
            self.osint_result_text.append(f"Identity consistent: {report.identity_consistent}")
            if report.warnings:
                self.osint_result_text.append(f"\nWarnings:")
                for w in report.warnings:
                    self.osint_result_text.append(f"  ⚠ {w}")
            if report.recommendations:
                self.osint_result_text.append(f"\nRecommendations:")
                for r in report.recommendations:
                    self.osint_result_text.append(f"  → {r}")
        except Exception as e:
            self.osint_result_text.append(f"❌ Error: {e}")
    
    def _grade_card(self):
        """Grade card quality"""
        if not HARDENING_AVAILABLE:
            self.osint_result_text.setPlainText("Card quality modules not available")
            return
        bin_str = self.osint_bin.text().strip()
        if not bin_str or len(bin_str) < 6:
            self.osint_result_text.append("\n⚠ Enter a 6-digit BIN to grade")
            return
        try:
            grader = CardQualityGrader()
            report = grader.grade(bin_prefix=bin_str)
            self.osint_result_text.append(f"\n{'='*40}")
            self.osint_result_text.append(f"CARD QUALITY GRADE: {report.grade.value}")
            self.osint_result_text.append(f"Success estimate: {report.success_rate_estimate}%")
            self.osint_result_text.append(f"Risk level: {report.risk_level}")
            if report.factors:
                self.osint_result_text.append(f"Factors:")
                for factor in report.factors:
                    self.osint_result_text.append(f"  • {factor}")
        except Exception as e:
            self.osint_result_text.append(f"❌ Error: {e}")
    
    def _inject_purchase_history(self):
        """Inject purchase history into profile"""
        if not HARDENING_AVAILABLE:
            self.ph_result_text.setPlainText("Purchase history module not available")
            return
        profile_path = self.ph_profile_path.text().strip()
        if not profile_path:
            if self.generated_profile:
                profile_path = str(self.generated_profile.profile_path)
                self.ph_profile_path.setText(profile_path)
            else:
                self.ph_result_text.setPlainText("⚠ Enter profile path or forge a profile first")
                return
        self.ph_result_text.clear()
        self.ph_result_text.append(f"Injecting {self.ph_months.value()}-month purchase history...\n")
        try:
            holder = CardHolderData(
                name=self.persona_name.text() or "Alex Mercer",
                email=self.persona_email.text() or "a.mercer@gmail.com",
                address=self.persona_address.text() or "2400 Nueces St",
                city=self.persona_city.text() or "Austin",
                state=self.persona_state.text() or "TX",
                zip_code=self.persona_zip.text() or "78705",
            )
            engine = PurchaseHistoryEngine()
            result = engine.inject(
                profile_path=profile_path,
                cardholder=holder,
                months=self.ph_months.value(),
            )
            self.ph_result_text.append(f"Orders injected: {result.orders_count}")
            self.ph_result_text.append(f"Commerce cookies: {result.cookies_count}")
            self.ph_result_text.append(f"Autofill entries: {result.autofill_count}")
            self.ph_result_text.append(f"Merchant cache: {result.cache_entries}")
            self.ph_result_text.append(f"\n✅ Purchase history injected successfully")
        except Exception as e:
            self.ph_result_text.append(f"❌ Error: {e}")


    # ═══════════════════════════════════════════════════════════════════
    # V7.5 HANDLER METHODS
    # ═══════════════════════════════════════════════════════════════════

    def _auto_start_services(self):
        """Auto-start background services on GUI launch"""
        if not V703_AVAILABLE:
            return
        try:
            mgr = get_service_manager()
            mgr.start_all()
        except Exception as e:
            print(f"Service auto-start warning: {e}")

    # ─── TX MONITOR HANDLERS ──────────────────────────────────────────

    def _refresh_tx_stats_silent(self):
        """Silent TX stats refresh (timer-driven)"""
        if not V703_AVAILABLE:
            return
        try:
            monitor = TransactionMonitor()
            stats = monitor.get_stats(hours=24)
            self.tx_total_label.setText(f"Total: {stats.get('total_transactions', 0)}")
            self.tx_approved_label.setText(f"Approved: {stats.get('approved', 0)}")
            self.tx_declined_label.setText(f"Declined: {stats.get('declined', 0)}")
            self.tx_rate_label.setText(f"Rate: {stats.get('success_rate', 0)}%")
        except Exception:
            pass

    def _refresh_tx_monitor(self):
        """Refresh TX monitor with recent transactions"""
        if not V703_AVAILABLE:
            self.tx_log.setPlainText("V7.5 modules not available")
            return
        try:
            monitor = TransactionMonitor()
            stats = monitor.get_stats(hours=24)
            self.tx_total_label.setText(f"Total: {stats.get('total_transactions', 0)}")
            self.tx_approved_label.setText(f"Approved: {stats.get('approved', 0)}")
            self.tx_declined_label.setText(f"Declined: {stats.get('declined', 0)}")
            self.tx_rate_label.setText(f"Rate: {stats.get('success_rate', 0)}%")

            history = monitor.get_history(last_hours=24, limit=50)
            text = f"LAST 24 HOURS — {len(history)} transactions\n" + "=" * 60 + "\n\n"
            for tx in history:
                icon = {"approved": "✅", "declined": "❌", "pending_3ds": "🔶"}.get(tx.get("status", ""), "⚪")
                text += (f"{icon} {tx.get('timestamp', '')[:19]}  {tx.get('domain', '?'):25s}  "
                         f"${tx.get('amount') or '?':>8}  {tx.get('status', '?'):10s}  "
                         f"{tx.get('decline_reason', '')}\n")
            if not history:
                text += "No transactions recorded yet.\n"
                text += "Install the TX Monitor extension and make a purchase to start capturing."
            self.tx_log.setPlainText(text)
        except Exception as e:
            self.tx_log.setPlainText(f"Error: {e}")

    def _decode_decline(self):
        """Decode a decline code"""
        if not V703_AVAILABLE:
            self.tx_log.setPlainText("V7.5 modules not available")
            return
        code = self.decode_input.text().strip()
        if not code:
            return
        psp_map = {"Auto-detect": "auto", "Stripe": "stripe", "Adyen": "adyen",
                    "Authorize.net": "authorize_net", "ISO 8583": "iso8583"}
        psp = psp_map.get(self.decode_psp.currentText(), "auto")
        result = decode_decline(code, psp)
        severity_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(result.get("severity", ""), "⚪")
        text = f"\n{'='*50}\n"
        text += f"CODE: {result.get('code', code)}\n"
        text += f"PSP: {result.get('psp', 'unknown')}\n"
        text += f"SEVERITY: {severity_icon} {result.get('severity', 'unknown').upper()}\n"
        text += f"CATEGORY: {result.get('category', 'unknown')}\n"
        text += f"REASON: {result.get('reason', 'Unknown')}\n"
        text += f"ACTION: {result.get('action', 'N/A')}\n"
        self.tx_log.append(text)

    def _show_tx_site_stats(self):
        """Show per-site success rates"""
        if not V703_AVAILABLE:
            return
        try:
            monitor = TransactionMonitor()
            stats = monitor.get_stats(hours=168)
            by_site = stats.get("by_site", {})
            text = "SUCCESS RATE BY SITE (Last 7 days)\n" + "=" * 50 + "\n\n"
            for domain, data in sorted(by_site.items(), key=lambda x: x[1].get("rate", 0), reverse=True):
                bar = "█" * int(data["rate"] / 5) + "░" * (20 - int(data["rate"] / 5))
                text += f"  {domain:30s}  {bar}  {data['rate']:5.1f}%  ({data['approved']}/{data['total']})\n"
            if not by_site:
                text += "  No data yet.\n"
            self.tx_log.setPlainText(text)
        except Exception as e:
            self.tx_log.setPlainText(f"Error: {e}")

    def _show_tx_bin_stats(self):
        """Show per-BIN success rates"""
        if not V703_AVAILABLE:
            return
        try:
            monitor = TransactionMonitor()
            stats = monitor.get_stats(hours=168)
            by_bin = stats.get("by_bin", {})
            text = "SUCCESS RATE BY BIN (Last 7 days)\n" + "=" * 50 + "\n\n"
            for bin_prefix, data in sorted(by_bin.items(), key=lambda x: x[1].get("rate", 0), reverse=True):
                bar = "█" * int(data["rate"] / 5) + "░" * (20 - int(data["rate"] / 5))
                text += f"  {bin_prefix:8s}  {bar}  {data['rate']:5.1f}%  ({data['approved']}/{data['total']})\n"
            if not by_bin:
                text += "  No data yet.\n"
            self.tx_log.setPlainText(text)
        except Exception as e:
            self.tx_log.setPlainText(f"Error: {e}")

    # ─── AUTO-DISCOVERY HANDLERS ──────────────────────────────────────

    def _run_auto_discovery(self):
        """Run auto-discovery immediately"""
        if not V703_AVAILABLE:
            self.disc_result_text.setPlainText("V7.5 modules not available")
            return
        self.disc_result_text.setPlainText("Running Auto-Discovery... (this may take 2-5 minutes)\n")
        try:
            mgr = get_service_manager()
            result = mgr.run_discovery_now()
            text = "AUTO-DISCOVERY RESULTS\n" + "=" * 50 + "\n\n"
            text += f"Total searched: {result.get('total_searched', 0)}\n"
            text += f"Easy 2D found: {result.get('easy_2d_found', 0)}\n"
            text += f"2D with antifraud: {result.get('2d_with_antifraud', 0)}\n"
            text += f"3DS bypassable: {result.get('bypassable_found', 0)}\n"
            text += f"3DS downgradeable: {result.get('downgradeable_found', 0)}\n"
            text += f"Hard 3DS: {result.get('hard_3ds', 0)}\n"
            text += f"Auto-added to DB: {result.get('auto_added_to_db', 0)}\n\n"
            for r in result.get("results", [])[:30]:
                icon = {"EASY_2D": "🟢", "2D_WITH_ANTIFRAUD": "🟡", "3DS_BYPASSABLE": "🔵",
                         "3DS_DOWNGRADEABLE": "🟠", "3DS_HARD": "🔴"}.get(r.get("classification", ""), "⚪")
                text += f"  {icon} {r.get('domain', '?'):30s}  {r.get('classification', '?'):20s}  Score: {r.get('bypass_score', '?')}\n"
            self.disc_result_text.setPlainText(text)
        except Exception as e:
            self.disc_result_text.setPlainText(f"Error: {e}")

    def _show_discovery_stats(self):
        """Show target database statistics"""
        if not V703_AVAILABLE:
            return
        try:
            stats = get_site_stats()
            text = "TARGET DATABASE STATISTICS\n" + "=" * 50 + "\n\n"
            text += f"Total sites: {stats.get('total_sites', 0)}\n"
            text += f"Easy sites: {stats.get('easy_sites', 0)}\n"
            text += f"Moderate sites: {stats.get('moderate_sites', 0)}\n"
            text += f"Hard sites: {stats.get('hard_sites', 0)}\n"
            text += f"Shopify stores: {stats.get('shopify_stores', 0)}\n"
            text += f"2D secure (no 3DS): {stats.get('2d_secure_sites', 0)}\n"
            text += f"Avg success rate: {stats.get('avg_success_rate', 0)*100:.0f}%\n\n"
            text += "BY CATEGORY:\n"
            for cat, count in stats.get("by_category", {}).items():
                text += f"  {cat:20s}: {count}\n"
            text += "\nBY PSP:\n"
            for psp, count in stats.get("by_psp", {}).items():
                text += f"  {psp:20s}: {count}\n"
            self.disc_result_text.setPlainText(text)
        except Exception as e:
            self.disc_result_text.setPlainText(f"Error: {e}")

    def _show_easy_sites(self):
        """Show easy 2D sites"""
        if not V703_AVAILABLE:
            return
        try:
            td = TargetDiscovery()
            sites = td.get_easy_sites()
            text = f"EASY 2D SITES ({len(sites)} found)\n" + "=" * 50 + "\n\n"
            for s in sites[:50]:
                text += (f"  {s['domain']:30s}  PSP: {s['psp']:15s}  "
                         f"3DS: {s['three_ds']:12s}  Rate: {s['success_rate_pct']}\n")
            self.disc_result_text.setPlainText(text)
        except Exception as e:
            self.disc_result_text.setPlainText(f"Error: {e}")

    def _show_shopify_sites(self):
        """Show Shopify stores"""
        if not V703_AVAILABLE:
            return
        try:
            td = TargetDiscovery()
            sites = td.get_shopify_sites()
            text = f"SHOPIFY STORES ({len(sites)} found)\n" + "=" * 50 + "\n\n"
            for s in sites[:50]:
                text += (f"  {s['domain']:30s}  PSP: {s['psp']:15s}  "
                         f"Fraud: {s['fraud_engine']:12s}  Rate: {s['success_rate_pct']}\n")
            self.disc_result_text.setPlainText(text)
        except Exception as e:
            self.disc_result_text.setPlainText(f"Error: {e}")

    # ─── 3DS BYPASS HANDLERS ─────────────────────────────────────────

    def _score_3ds_bypass(self):
        """Score a site's 3DS bypass potential"""
        if not V703_AVAILABLE:
            self.bypass_result_text.setPlainText("V7.5 modules not available")
            return
        domain = self.bypass_domain.text().strip()
        if not domain:
            self.bypass_result_text.setPlainText("Enter a domain to score")
            return
        try:
            result = get_3ds_bypass_score(
                domain, psp=self.bypass_psp.currentText(),
                card_country=self.bypass_country.currentText(),
                amount=self.bypass_amount.value()
            )
            color = {"green": "🟢", "yellow": "🟡", "orange": "🟠", "red": "🔴"}.get(result.get("bypass_color", ""), "⚪")
            text = f"3DS BYPASS SCORE: {domain}\n" + "=" * 50 + "\n\n"
            text += f"  SCORE: {color} {result['bypass_score']}/100 ({result['bypass_level']})\n\n"
            text += "  TECHNIQUES:\n"
            for t in result.get("techniques", []):
                text += f"    • {t}\n"
            if result.get("warnings"):
                text += "\n  WARNINGS:\n"
                for w in result["warnings"]:
                    text += f"    {w}\n"
            text += f"\n  PSP: {result.get('psp', 'unknown')}\n"
            text += f"  Downgrade possible: {'Yes' if result.get('downgrade_possible') else 'No'}\n"
            text += f"  Frictionless exploitable: {'Yes' if result.get('frictionless_exploitable') else 'No'}\n"
            text += f"  Timeout behavior: {result.get('timeout_behavior', 'unknown')}\n"
            if result.get("psp_vulnerabilities"):
                text += "\n  PSP WEAK POINTS:\n"
                for wp in result["psp_vulnerabilities"]:
                    text += f"    → {wp}\n"
            self.bypass_result_text.setPlainText(text)
        except Exception as e:
            self.bypass_result_text.setPlainText(f"Error: {e}")

    def _get_bypass_plan(self):
        """Get step-by-step 3DS bypass plan"""
        if not V703_AVAILABLE:
            return
        domain = self.bypass_domain.text().strip()
        if not domain:
            self.bypass_result_text.setPlainText("Enter a domain first")
            return
        try:
            plan = get_3ds_bypass_plan(
                domain, psp=self.bypass_psp.currentText(),
                card_country=self.bypass_country.currentText(),
                amount=self.bypass_amount.value()
            )
            text = f"3DS BYPASS PLAN: {domain}\n" + "=" * 50 + "\n"
            text += f"Score: {plan['bypass_score']}/100 ({plan['bypass_level']})\n\n"
            for step in plan.get("steps", []):
                text += f"  STEP {step['step']}: {step['action']}\n"
                text += f"    {step['detail']}\n\n"
            if plan.get("applicable_techniques"):
                text += "APPLICABLE DOWNGRADE TECHNIQUES:\n"
                for t in plan["applicable_techniques"]:
                    text += f"  • {t}\n"
            self.bypass_result_text.setPlainText(text)
        except Exception as e:
            self.bypass_result_text.setPlainText(f"Error: {e}")

    def _show_downgrade_attacks(self):
        """Show all 3DS downgrade attack techniques"""
        if not V703_AVAILABLE:
            return
        try:
            attacks = get_downgrade_attacks()
            text = "3DS DOWNGRADE ATTACKS\n" + "=" * 50 + "\n\n"
            for a in attacks:
                text += f"[{a['success_rate']*100:.0f}% success] {a['name']}\n"
                text += f"  Type: {a['type']} | Risk: {a['risk']} | PSPs: {', '.join(a['psps'])}\n"
                text += f"  {a['description'][:200]}\n"
                text += "  Steps:\n"
                for s in a["steps"]:
                    text += f"    {s}\n"
                text += "\n"
            self.bypass_result_text.setPlainText(text)
        except Exception as e:
            self.bypass_result_text.setPlainText(f"Error: {e}")

    def _show_psd2_exploits(self):
        """Show PSD2 exemption exploitation guide"""
        if not V703_AVAILABLE:
            return
        try:
            exemptions = get_psd2_exemptions()
            text = "PSD2 EXEMPTION EXPLOITATION (EU)\n" + "=" * 50 + "\n\n"
            for key, ex in exemptions.items():
                text += f"[{key.upper()}]\n"
                text += f"  {ex['description']}\n"
                if ex.get("threshold"):
                    text += f"  Threshold: {ex['threshold']} EUR\n"
                text += f"  Limitation: {ex['limitation']}\n"
                text += "  Exploit:\n"
                for e in ex.get("exploit", []):
                    text += f"    • {e}\n"
                text += f"  Best targets: {', '.join(ex.get('best_targets', []))}\n\n"
            self.bypass_result_text.setPlainText(text)
        except Exception as e:
            self.bypass_result_text.setPlainText(f"Error: {e}")

    # ─── NON-VBV BIN HANDLERS ────────────────────────────────────────

    def _get_nvbv_recommendations(self):
        """Get Non-VBV BIN recommendations"""
        if not V703_AVAILABLE:
            self.nvbv_result_text.setPlainText("V7.5 modules not available")
            return
        try:
            country = self.nvbv_country.currentText()
            target = self.nvbv_target.text().strip() or None
            result = get_non_vbv_recommendations(country=country, target_merchant=target)
            text = f"NON-VBV RECOMMENDATIONS: {country}\n" + "=" * 50 + "\n\n"
            if result.get("country_profile"):
                cp = result["country_profile"]
                text += f"Country: {cp.get('name', country)} | Difficulty: {cp.get('difficulty', '?')}\n"
                text += f"Base 3DS rate: {cp.get('three_ds_base_rate', 0)*100:.0f}% | AVS: {'Yes' if cp.get('avs_common') else 'No'}\n"
                text += f"Notes: {cp.get('notes', '')[:200]}\n\n"
            text += "RECOMMENDED BINs:\n" + "-" * 40 + "\n"
            for bin_data in result.get("recommendations", []):
                text += (f"  {bin_data.get('bin', '?'):8s}  {bin_data.get('bank', '?'):20s}  "
                         f"{bin_data.get('network', '?'):6s}  {bin_data.get('level', '?'):10s}  "
                         f"3DS: {bin_data.get('three_ds_rate', 0)*100:.0f}%  "
                         f"Status: {bin_data.get('vbv_status', '?')}\n")
                text += f"           {bin_data.get('notes', '')[:80]}\n"
            if not result.get("recommendations"):
                text += "  No BINs found for this country.\n"
            self.nvbv_result_text.setPlainText(text)
        except Exception as e:
            self.nvbv_result_text.setPlainText(f"Error: {e}")

    def _show_all_nvbv_bins(self):
        """Show all Non-VBV BINs"""
        if not V703_AVAILABLE:
            return
        try:
            all_bins = get_all_non_vbv_bins()
            text = f"ALL NON-VBV BINs ({sum(len(v) for v in all_bins.values())} total across {len(all_bins)} regions)\n"
            text += "=" * 60 + "\n\n"
            for country, bins in sorted(all_bins.items()):
                text += f"── {country} ({len(bins)} BINs) ──\n"
                for b in bins:
                    text += (f"  {b.bin:8s}  {b.bank:20s}  {b.network:6s}  {b.level:10s}  "
                             f"3DS: {b.three_ds_rate*100:.0f}%  {b.vbv_status}\n")
                text += "\n"
            self.nvbv_result_text.setPlainText(text)
        except Exception as e:
            self.nvbv_result_text.setPlainText(f"Error: {e}")

    def _show_easy_countries(self):
        """Show easy countries ranking"""
        if not V703_AVAILABLE:
            return
        try:
            countries = get_easy_countries()
            text = "COUNTRY DIFFICULTY RANKING\n" + "=" * 50 + "\n\n"
            for c in countries:
                icon = {"easy": "🟢", "moderate": "🟡", "hard": "🟠"}.get(c.get("difficulty", ""), "⚪")
                text += f"  #{c['rank']:2d}  {icon} {c['code']}  {c['name']:20s}  [{c['difficulty']}]\n"
                text += f"       {c['reason']}\n\n"
            self.nvbv_result_text.setPlainText(text)
        except Exception as e:
            self.nvbv_result_text.setPlainText(f"Error: {e}")

    # ─── SERVICES HANDLERS ────────────────────────────────────────────

    def _start_all_services(self):
        """Start all background services"""
        if not V703_AVAILABLE:
            self.svc_result_text.setPlainText("V7.5 modules not available")
            return
        try:
            mgr = get_service_manager()
            result = mgr.start_all()
            text = "SERVICE START RESULTS\n" + "=" * 50 + "\n\n"
            for svc, status in result.items():
                icon = "🟢" if status.get("status") == "started" else "🔴"
                text += f"  {icon} {svc}: {status}\n"
            self.svc_result_text.setPlainText(text)
        except Exception as e:
            self.svc_result_text.setPlainText(f"Error: {e}")

    def _check_services_status(self):
        """Check status of all services"""
        if not V703_AVAILABLE:
            return
        try:
            import json
            mgr = get_service_manager()
            status = mgr.get_status()
            self.svc_result_text.setPlainText(
                "SERVICE STATUS\n" + "=" * 50 + "\n\n" +
                json.dumps(status, indent=2, default=str)
            )
        except Exception as e:
            self.svc_result_text.setPlainText(f"Error: {e}")

    def _update_feedback(self):
        """Force feedback loop update"""
        if not V703_AVAILABLE:
            return
        try:
            mgr = get_service_manager()
            result = mgr.update_feedback_now()
            text = "FEEDBACK UPDATE\n" + "=" * 50 + "\n\n"
            text += f"Updated sites: {result.get('updated_sites', 0)}\n"
            text += f"Updated BINs: {result.get('updated_bins', 0)}\n"
            text += f"Total tracked sites: {result.get('total_site_scores', 0)}\n"
            text += f"Total tracked BINs: {result.get('total_bin_scores', 0)}\n"
            self.svc_result_text.setPlainText(text)
        except Exception as e:
            self.svc_result_text.setPlainText(f"Error: {e}")

    def _show_best_sites(self):
        """Show best sites from real TX data"""
        if not V703_AVAILABLE:
            return
        try:
            mgr = get_service_manager()
            best = mgr.get_best_sites()
            text = "BEST SITES (from real TX data, >70% success, 3+ transactions)\n"
            text += "=" * 60 + "\n\n"
            for s in best[:30]:
                bar = "█" * int(s["success_rate"] * 20) + "░" * (20 - int(s["success_rate"] * 20))
                text += f"  {s['domain']:30s}  {bar}  {s['success_rate']*100:.0f}%  ({s['approved']}/{s['total_tx']})\n"
            if not best:
                text += "  No data yet. TX Monitor needs to capture transactions first.\n"
            self.svc_result_text.setPlainText(text)
        except Exception as e:
            self.svc_result_text.setPlainText(f"Error: {e}")


    # ─── V7.5 EXTENDED SHIELD HANDLERS ───────────────────────────────

    def _run_canvas_shim(self):
        """Generate and deploy Canvas sub-pixel correction shim"""
        try:
            from canvas_subpixel_shim import CanvasSubPixelShim
            shim = CanvasSubPixelShim(profile_uuid=getattr(self, '_last_profile_uuid', 'default'))
            js = shim.generate_js_shim()
            path = shim.write_shim_file()
            self.env_result_text.setPlainText(
                f"CANVAS SUB-PIXEL SHIM\n{'='*50}\n\n"
                f"  JS shim generated: {len(js)} bytes\n"
                f"  Written to: {path}\n"
                f"  Seed: {shim._seed}\n"
                f"  Font corrections: {len(shim._corrections)} fonts\n"
                f"    (Arial, Times New Roman, Courier New, Verdana,\n"
                f"     Georgia, Segoe UI, Tahoma, Calibri)\n\n"
                f"  The shim intercepts measureText() and corrects\n"
                f"  FreeType→DirectWrite sub-pixel discrepancies.\n"
                f"  Injected via Ghost Motor extension on browser launch."
            )
        except Exception as e:
            self.env_result_text.setPlainText(f"Canvas Shim Error: {e}")

    def _run_cpuid_shield(self):
        """Apply CPUID/RDTSC hardening"""
        try:
            from cpuid_rdtsc_shield import CPUIDRDTSCShield
            shield = CPUIDRDTSCShield()
            report = shield.apply_all()
            pre = report['pre_scan']
            post = report['post_scan']
            text = f"CPUID/RDTSC SHIELD\n{'='*50}\n\n"
            text += f"  Pre-scan leaks:  {len(pre['leak_vectors'])}\n"
            text += f"  Post-scan leaks: {len(post['leak_vectors'])}\n"
            text += f"  Leaks fixed:     {report['leaks_fixed']}\n\n"
            text += f"  DMI Overrides:\n"
            for path, ok in report.get('sysfs_overrides', {}).items():
                text += f"    {'✅' if ok else '❌'} {path.split('/')[-1]}\n"
            text += f"\n  Hypervisor suppressed: {'✅' if report['hypervisor_suppressed'] else '❌'}\n"
            text += f"  ACPI suppressed: {'✅' if report['acpi_suppressed'] else '❌'}\n"
            text += f"  RDTSC smoothed: {'✅' if report['rdtsc_smoothed'] else '❌'}\n"
            if post['leak_vectors']:
                text += f"\n  Remaining leaks:\n"
                for v in post['leak_vectors']:
                    text += f"    ⚠️ {v[:80]}\n"
            self.env_result_text.setPlainText(text)
        except Exception as e:
            self.env_result_text.setPlainText(f"CPUID Shield Error: {e}")

    def _run_font_provisioner(self):
        """Run Windows font provisioner"""
        try:
            from windows_font_provisioner import WindowsFontProvisioner
            self.env_result_text.setPlainText("📦 Provisioning Windows fonts... (may take 30s)")
            QApplication.processEvents()
            prov = WindowsFontProvisioner()
            report = prov.provision()
            v = report['verification']
            text = f"WINDOWS FONT PROVISIONER\n{'='*50}\n\n"
            text += f"  Packages: {sum(1 for x in report['packages'].values() if x)}/{len(report['packages'])}\n"
            text += f"  Fonts staged: {report['fonts_staged']}\n"
            text += f"  Fonts rejected: {report['rejected_count']}\n"
            text += f"  Fonts aliased: {report['aliased_count']}\n"
            text += f"  Fontconfig written: {'✅' if report['fontconfig_written'] else '❌'}\n\n"
            text += f"  Windows fonts available: {v['windows_fonts_available']}\n"
            text += f"  Linux fonts leaking: {len(v['linux_fonts_leaking'])}\n"
            if v['linux_fonts_leaking']:
                for f in v['linux_fonts_leaking']:
                    text += f"    ⚠️ {f}\n"
            if v.get('windows_fonts_missing'):
                text += f"\n  Missing Windows fonts:\n"
                for f in v['windows_fonts_missing']:
                    text += f"    ❌ {f}\n"
            self.env_result_text.setPlainText(text)
        except Exception as e:
            self.env_result_text.setPlainText(f"Font Provisioner Error: {e}")

    def _run_immutable_os(self):
        """Apply immutable OS hardening"""
        try:
            from immutable_os import ImmutableOS
            ios = ImmutableOS()
            result = ios.apply()
            text = f"IMMUTABLE OS HARDENING\n{'='*50}\n\n"
            if isinstance(result, dict):
                for k, v in result.items():
                    text += f"  {'✅' if v else '❌'} {k}\n"
            else:
                text += f"  Result: {result}\n"
            self.env_result_text.setPlainText(text)
        except ImportError:
            # Fallback: run sysctl + chattr directly
            import subprocess
            cmds = [
                ("sysctl -w net.ipv4.ip_default_ttl=128", "TTL=128"),
                ("chattr +i /etc/resolv.conf", "resolv.conf immutable"),
            ]
            text = f"IMMUTABLE OS (direct mode)\n{'='*50}\n\n"
            for cmd, desc in cmds:
                try:
                    r = subprocess.run(cmd.split(), capture_output=True, timeout=5)
                    text += f"  {'✅' if r.returncode == 0 else '⚠️'} {desc}\n"
                except Exception as e:
                    text += f"  ❌ {desc}: {e}\n"
            self.env_result_text.setPlainText(text)
        except Exception as e:
            self.env_result_text.setPlainText(f"Immutable OS Error: {e}")

    def _run_ghost_motor_test(self):
        """Test Ghost Motor diffusion trajectory generation"""
        try:
            from ghost_motor_v6 import (
                GhostMotorDiffusion, PersonaType,
                get_forter_safe_params, get_biocatch_evasion_guide, get_warmup_pattern
            )
            motor = GhostMotorDiffusion()
            traj = motor.generate((100, 100), (500, 400), persona=PersonaType.CASUAL_SHOPPER)
            forter = get_forter_safe_params()
            warmup = get_warmup_pattern()
            text = f"GHOST MOTOR V7.5 — DIFFUSION TRAJECTORY\n{'='*50}\n\n"
            text += f"  Trajectory points: {len(traj.points)}\n"
            text += f"  Duration: {traj.total_duration_ms:.0f}ms\n"
            text += f"  Persona: CASUAL_SHOPPER\n"
            text += f"  Start: (100, 100) → End: (500, 400)\n\n"
            text += f"  Forter-Safe Parameters:\n"
            for k, v in forter.items():
                text += f"    {k}: {v}\n"
            text += f"\n  Warmup Pattern:\n"
            for k, v in list(warmup.items())[:8]:
                text += f"    {k}: {v}\n"
            text += f"\n  BioCatch Evasion:\n"
            biocatch = get_biocatch_evasion_guide()
            for k, v in list(biocatch.items())[:5]:
                text += f"    {k}: {v}\n"
            self.env_result_text.setPlainText(text)
        except Exception as e:
            self.env_result_text.setPlainText(f"Ghost Motor Error: {e}")

    def _run_fingerprint_inject(self):
        """Inject hardware fingerprint into current profile"""
        try:
            from fingerprint_injector import FingerprintInjector, create_injector
            profile_uuid = getattr(self, '_last_profile_uuid', 'default-profile')
            injector = create_injector(profile_uuid)
            config = injector.generate_config()
            text = f"FINGERPRINT INJECTOR\n{'='*50}\n\n"
            text += f"  Profile UUID: {profile_uuid}\n"
            text += f"  Config generated: {len(config)} parameters\n\n"
            for k, v in list(config.items())[:15]:
                val_str = str(v)[:60]
                text += f"  {k}: {val_str}\n"
            if len(config) > 15:
                text += f"\n  ... and {len(config) - 15} more parameters\n"
            text += f"\n  Fingerprint will be injected on browser launch."
            self.env_result_text.setPlainText(text)
        except Exception as e:
            self.env_result_text.setPlainText(f"Fingerprint Injector Error: {e}")

    def _run_all_shields(self):
        """Run all V7.5 shields in sequence"""
        self.env_result_text.setPlainText("⚡ RUNNING ALL V7.5 SHIELDS...\n")
        QApplication.processEvents()
        results = []
        steps = [
            ("Font Purge", self._run_font_purge),
            ("Audio Harden", self._run_audio_harden),
            ("Timezone Sync", self._run_tz_enforce),
            ("Canvas Shim", self._run_canvas_shim),
            ("CPUID Shield", self._run_cpuid_shield),
            ("Font Provision", self._run_font_provisioner),
            ("Immutable OS", self._run_immutable_os),
            ("Ghost Motor", self._run_ghost_motor_test),
            ("Fingerprint Inject", self._run_fingerprint_inject),
        ]
        text = f"⚡ ALL V7.5 SHIELDS — SEQUENTIAL RUN\n{'='*50}\n\n"
        for name, func in steps:
            try:
                func()
                # Capture what was written to env_result_text
                result_text = self.env_result_text.toPlainText()
                has_error = "Error" in result_text and "✅" not in result_text[:100]
                results.append((name, not has_error))
                text += f"  {'✅' if not has_error else '⚠️'} {name}\n"
            except Exception as e:
                results.append((name, False))
                text += f"  ❌ {name}: {e}\n"
            QApplication.processEvents()
        
        passed = sum(1 for _, ok in results if ok)
        text += f"\n{'='*50}\n"
        text += f"  Result: {passed}/{len(results)} shields active\n"
        text += f"  Status: {'✅ ALL SHIELDS UP' if passed == len(results) else '⚠️ PARTIAL'}\n"
        self.env_result_text.setPlainText(text)

    # ─── AI INTELLIGENCE HANDLERS ────────────────────────────────────

    def _ai_run_plan(self):
        """Run full AI operation plan"""
        if not AI_AVAILABLE:
            self.ai_plan_result.setPlainText("AI Intelligence Engine not available.\nCheck that ai_intelligence_engine.py is in /opt/titan/core/")
            return
        bin_num = self.ai_bin_input.text().strip()
        target = self.ai_target_input.text().strip()
        amount = self.ai_amount_input.value()
        if not bin_num or not target:
            self.ai_plan_result.setPlainText("Enter BIN and Target to run AI plan.")
            return
        self.ai_plan_result.setPlainText("🧠 Running AI Operation Plan... (15-40s)\nAnalyzing BIN + Target + 3DS + Behavioral...")
        QApplication.processEvents()
        try:
            plan = plan_operation(bin_num, target, amount)
            text = f"{'='*60}\n  AI OPERATION PLAN\n{'='*60}\n\n"
            text += f"  Decision: {'✅ GO' if plan.go_decision else '❌ NO-GO'}\n"
            text += f"  Overall Score: {plan.overall_score}/100\n"
            text += f"  AI Powered: {'Full' if plan.ai_powered else 'Partial (some fallbacks)'}\n\n"
            text += f"{'─'*60}\n  BIN ANALYSIS\n{'─'*60}\n"
            b = plan.bin_analysis
            text += f"  Bank: {b.bank_name} | Country: {b.country}\n"
            text += f"  Type: {b.card_type} {b.card_level} ({b.network})\n"
            text += f"  AI Score: {b.ai_score}/100 | Success: {b.success_prediction:.0%}\n"
            text += f"  Risk: {b.risk_level.value} | Amount: ${b.optimal_amount_range[0]:.0f}-${b.optimal_amount_range[1]:.0f}\n"
            text += f"  Timing: {b.timing_advice}\n"
            text += f"  Best targets: {', '.join(b.best_targets[:3])}\n"
            if b.risk_factors:
                text += f"  Risk factors: {'; '.join(b.risk_factors[:3])}\n"
            text += f"  Strategy: {b.strategic_notes}\n\n"
            text += f"{'─'*60}\n  TARGET RECON\n{'─'*60}\n"
            t = plan.target_recon
            text += f"  Target: {t.name} ({t.domain})\n"
            text += f"  Fraud Engine: {t.fraud_engine_guess}\n"
            text += f"  Payment PSP: {t.payment_processor_guess}\n"
            text += f"  Friction: {t.estimated_friction} | 3DS: {t.three_ds_probability:.0%}\n"
            if t.checkout_tips:
                text += f"  Tips: {'; '.join(t.checkout_tips[:2])}\n"
            text += f"\n{'─'*60}\n  3DS STRATEGY\n{'─'*60}\n"
            s = plan.threeds_strategy
            text += f"  Approach: {s.recommended_approach}\n"
            text += f"  Success: {s.success_probability:.0%}\n"
            text += f"  Timing: {s.timing_window}\n"
            text += f"  Amount: {s.amount_strategy}\n"
            if s.checkout_flow:
                text += f"  Flow: {' → '.join(s.checkout_flow[:4])}\n"
            text += f"  Fallback: {s.fallback_plan}\n"
            text += f"\n{'─'*60}\n  BEHAVIORAL TUNING (Ghost Motor)\n{'─'*60}\n"
            bh = plan.behavioral_tuning
            text += f"  Mouse: {bh.mouse_speed_range[0]:.0f}-{bh.mouse_speed_range[1]:.0f} px/s\n"
            text += f"  Click delay: {bh.click_delay_ms[0]}-{bh.click_delay_ms[1]}ms\n"
            text += f"  Typing: {bh.typing_wpm_range[0]}-{bh.typing_wpm_range[1]} WPM (error: {bh.typing_error_rate:.1%})\n"
            text += f"  Scroll: {bh.scroll_behavior}\n"
            text += f"  Page dwell: {bh.page_dwell_seconds[0]}-{bh.page_dwell_seconds[1]}s\n"
            text += f"  Form fill: {bh.form_fill_strategy}\n"
            text += f"\n{'='*60}\n  {plan.executive_summary}\n{'='*60}\n"
            self.ai_plan_result.setPlainText(text)
        except Exception as e:
            self.ai_plan_result.setPlainText(f"Error: {e}")

    def _ai_analyze_bin(self):
        """AI BIN-only analysis"""
        if not AI_AVAILABLE:
            self.ai_plan_result.setPlainText("AI not available")
            return
        bin_num = self.ai_bin_input.text().strip()
        if not bin_num:
            self.ai_plan_result.setPlainText("Enter a BIN number.")
            return
        self.ai_plan_result.setPlainText(f"🔍 Analyzing BIN {bin_num}...")
        QApplication.processEvents()
        try:
            b = analyze_bin(bin_num, self.ai_target_input.text().strip(), self.ai_amount_input.value())
            text = f"BIN ANALYSIS: {b.bin_number}\n{'='*50}\n"
            text += f"  Bank: {b.bank_name} | Country: {b.country}\n"
            text += f"  Type: {b.card_type} {b.card_level} ({b.network})\n"
            text += f"  AI Score: {b.ai_score}/100 | Success: {b.success_prediction:.0%}\n"
            text += f"  Risk: {b.risk_level.value}\n"
            text += f"  Optimal: ${b.optimal_amount_range[0]:.0f}-${b.optimal_amount_range[1]:.0f}\n"
            text += f"  Timing: {b.timing_advice}\n"
            text += f"  Best: {', '.join(b.best_targets[:5])}\n"
            text += f"  Avoid: {', '.join(b.avoid_targets[:3])}\n"
            if b.risk_factors:
                text += f"\n  Risk factors:\n" + "\n".join(f"    • {r}" for r in b.risk_factors)
            text += f"\n\n  {b.strategic_notes}\n"
            text += f"\n  AI Powered: {b.ai_powered}"
            self.ai_plan_result.setPlainText(text)
        except Exception as e:
            self.ai_plan_result.setPlainText(f"Error: {e}")

    def _ai_recon_target(self):
        """AI target-only recon"""
        if not AI_AVAILABLE:
            self.ai_plan_result.setPlainText("AI not available")
            return
        target = self.ai_target_input.text().strip()
        if not target:
            self.ai_plan_result.setPlainText("Enter a target domain.")
            return
        self.ai_plan_result.setPlainText(f"🎯 Recon on {target}...")
        QApplication.processEvents()
        try:
            t = recon_target(target)
            text = f"TARGET RECON: {t.domain}\n{'='*50}\n"
            text += f"  Name: {t.name}\n"
            text += f"  Fraud Engine: {t.fraud_engine_guess}\n"
            text += f"  Payment PSP: {t.payment_processor_guess}\n"
            text += f"  Friction: {t.estimated_friction}\n"
            text += f"  3DS Probability: {t.three_ds_probability:.0%}\n"
            text += f"  Best cards: {', '.join(t.optimal_card_types)}\n"
            text += f"  Best countries: {', '.join(t.optimal_countries)}\n"
            if t.warmup_strategy:
                text += f"\n  Warmup:\n" + "\n".join(f"    {i+1}. {s}" for i, s in enumerate(t.warmup_strategy[:5]))
            if t.checkout_tips:
                text += f"\n\n  Tips:\n" + "\n".join(f"    • {tip}" for tip in t.checkout_tips[:5])
            if t.risk_factors:
                text += f"\n\n  Risks:\n" + "\n".join(f"    ⚠ {r}" for r in t.risk_factors[:5])
            text += f"\n\n  AI Powered: {t.ai_powered}"
            self.ai_plan_result.setPlainText(text)
        except Exception as e:
            self.ai_plan_result.setPlainText(f"Error: {e}")

    def _ai_3ds_advise(self):
        """AI 3DS bypass strategy"""
        if not AI_AVAILABLE:
            self.ai_3ds_result.setPlainText("AI not available")
            return
        self.ai_3ds_result.setPlainText("🛡️ Generating 3DS strategy...")
        QApplication.processEvents()
        try:
            s = advise_3ds(
                self.ai_3ds_bin.text().strip(),
                self.ai_3ds_target.text().strip() or "unknown",
                self.ai_3ds_amount.value()
            )
            text = f"3DS BYPASS STRATEGY\n{'='*50}\n"
            text += f"  Approach: {s.recommended_approach}\n"
            text += f"  Success Probability: {s.success_probability:.0%}\n"
            text += f"  Timing: {s.timing_window}\n"
            text += f"  Amount Strategy: {s.amount_strategy}\n"
            text += f"  Card Preference: {s.card_type_preference}\n"
            if s.checkout_flow:
                text += f"\n  Checkout Flow:\n" + "\n".join(f"    {i+1}. {step}" for i, step in enumerate(s.checkout_flow))
            text += f"\n\n  Fallback: {s.fallback_plan}\n"
            if s.risk_factors:
                text += f"\n  Risks:\n" + "\n".join(f"    ⚠ {r}" for r in s.risk_factors)
            text += f"\n\n  AI Powered: {s.ai_powered}"
            self.ai_3ds_result.setPlainText(text)
        except Exception as e:
            self.ai_3ds_result.setPlainText(f"Error: {e}")

    def _ai_tune_behavior(self):
        """AI behavioral tuning for Ghost Motor"""
        if not AI_AVAILABLE:
            self.ai_beh_result.setPlainText("AI not available")
            return
        self.ai_beh_result.setPlainText("🎭 Generating behavioral profile...")
        QApplication.processEvents()
        try:
            engine = self.ai_beh_engine.currentText()
            if engine == "auto-detect":
                engine = "unknown"
            bh = tune_behavior(
                self.ai_beh_target.text().strip() or "unknown",
                fraud_engine=engine,
                persona=self.ai_beh_persona.text().strip()
            )
            text = f"GHOST MOTOR BEHAVIORAL PROFILE\n{'='*50}\n"
            text += f"  Target: {bh.target}\n\n"
            text += f"  Mouse Speed:    {bh.mouse_speed_range[0]:.0f} - {bh.mouse_speed_range[1]:.0f} px/s\n"
            text += f"  Click Delay:    {bh.click_delay_ms[0]} - {bh.click_delay_ms[1]} ms\n"
            text += f"  Scroll:         {bh.scroll_behavior}\n"
            text += f"  Typing Speed:   {bh.typing_wpm_range[0]} - {bh.typing_wpm_range[1]} WPM\n"
            text += f"  Typing Errors:  {bh.typing_error_rate:.1%}\n"
            text += f"  Page Dwell:     {bh.page_dwell_seconds[0]} - {bh.page_dwell_seconds[1]} seconds\n"
            text += f"  Idle Pattern:   {bh.idle_pattern}\n"
            text += f"  Form Fill:      {bh.form_fill_strategy}\n"
            text += f"\n  AI Powered: {bh.ai_powered}"
            self.ai_beh_result.setPlainText(text)
        except Exception as e:
            self.ai_beh_result.setPlainText(f"Error: {e}")

    def _ai_audit_profile(self):
        """AI profile forensic audit"""
        if not AI_AVAILABLE:
            self.ai_prof_result.setPlainText("AI not available")
            return
        profile_path = getattr(self, '_ai_selected_profile', None)
        if not profile_path:
            profiles_dir = Path("/opt/titan/profiles")
            if profiles_dir.exists():
                dirs = sorted(profiles_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
                if dirs:
                    profile_path = str(dirs[0])
        if not profile_path:
            self.ai_prof_result.setPlainText("No profile found. Generate one with Genesis first, or click SELECT PROFILE.")
            return
        self.ai_prof_path.setText(f"Profile: {profile_path}")
        self.ai_prof_result.setPlainText(f"🔬 Auditing profile: {profile_path}...")
        QApplication.processEvents()
        try:
            result = audit_profile(profile_path)
            text = f"PROFILE FORENSIC AUDIT\n{'='*50}\n"
            text += f"  Path: {profile_path}\n"
            text += f"  Clean: {'✅ YES' if result.clean else '❌ NO'}\n"
            text += f"  Score: {result.score}/100\n"
            text += f"  AI Powered: {result.ai_powered}\n"
            if result.inconsistencies:
                text += f"\n  Inconsistencies ({len(result.inconsistencies)}):\n"
                text += "\n".join(f"    ⚠ {i}" for i in result.inconsistencies)
            if result.leak_vectors:
                text += f"\n\n  Leak Vectors ({len(result.leak_vectors)}):\n"
                text += "\n".join(f"    🔴 {v}" for v in result.leak_vectors)
            if result.recommendations:
                text += f"\n\n  Recommendations:\n"
                text += "\n".join(f"    → {r}" for r in result.recommendations)
            self.ai_prof_result.setPlainText(text)
        except Exception as e:
            self.ai_prof_result.setPlainText(f"Error: {e}")

    def _ai_browse_profile(self):
        """Browse for profile directory"""
        path = QFileDialog.getExistingDirectory(self, "Select Profile Directory", "/opt/titan/profiles")
        if path:
            self._ai_selected_profile = path
            self.ai_prof_path.setText(f"Profile: {path}")

    def _ai_tls_status(self):
        """Show TLS Parrot engine status"""
        try:
            if not AI_AVAILABLE:
                self.ai_tls_result.setPlainText("TLS Parrot module not available")
                return
            engine = TLSParrotEngine()
            text = f"TLS PARROT ENGINE V7.5\n{'='*50}\n\n"
            text += f"  Templates loaded: {len(engine.templates)}\n\n"
            for target, tmpl in engine.templates.items():
                text += f"  {target.value}:\n"
                text += f"    JA3: {tmpl.ja3_hash[:20]}...\n"
                text += f"    JA4: {tmpl.ja4_hash}\n"
                text += f"    Ciphers: {len(tmpl.cipher_suites)} | Extensions: {len(tmpl.extensions)}\n"
                text += f"    GREASE: {'✅' if tmpl.grease_enabled else '❌'} | ECH: {'✅' if tmpl.encrypted_client_hello else '❌'}\n\n"
            text += f"{'─'*50}\n  JA4+ Permutation Test:\n"
            p1 = engine.ja4_permutation(ParrotTarget.CHROME_131_WIN11, "test.com")
            p2 = engine.ja4_permutation(ParrotTarget.CHROME_131_WIN11, "test.com")
            text += f"    Session 1 ciphers: {p1['cipher_suites'][:3]}...\n"
            text += f"    Session 2 ciphers: {p2['cipher_suites'][:3]}...\n"
            text += f"    Different order: {'✅ YES' if p1['cipher_suites'] != p2['cipher_suites'] else '⚠ SAME'}\n"
            text += f"    JA4 hash stable: {'✅ YES' if p1['ja4_computed'] == p2['ja4_computed'] else '❌ NO'}\n"
            self.ai_tls_result.setPlainText(text)
        except Exception as e:
            self.ai_tls_result.setPlainText(f"Error: {e}")

    def _ai_refresh_status(self):
        """Refresh AI engine status"""
        try:
            if AI_AVAILABLE:
                status = get_ai_status()
                text = f"AI INTELLIGENCE ENGINE STATUS\n{'='*50}\n\n"
                text += f"  Available: {'✅ ONLINE' if status['available'] else '❌ OFFLINE'}\n"
                text += f"  Provider: {status['provider']}\n"
                text += f"  Version: {status['version']}\n\n"
                if status['features']:
                    text += f"  Features ({len(status['features'])}):\n"
                    for f in status['features']:
                        text += f"    ✅ {f}\n"
                else:
                    text += "  No features available (Ollama offline?)\n"
                    text += "\n  To start Ollama: systemctl start ollama\n"
            else:
                text = "AI Intelligence Engine not imported.\n"
                text += "Check /opt/titan/core/ai_intelligence_engine.py exists."
            self.ai_status_result.setPlainText(text)
        except Exception as e:
            self.ai_status_result.setPlainText(f"Error: {e}")

    def _launch_forensic_monitor(self):
        """Launch the forensic monitor widget"""
        try:
            # Import the forensic widget
            from forensic_widget import ForensicWidget
            from PyQt6.QtWidgets import QApplication
            
            # Check if already running
            for widget in QApplication.topLevelWidgets():
                if isinstance(widget, ForensicWidget):
                    self.forensic_status.setText("🟡 Already running")
                    self.forensic_status.setStyleSheet("color: #FFC107;")
                    widget.raise_()
                    widget.activateWindow()
                    return
            
            # Create and show forensic widget
            forensic_widget = ForensicWidget()
            forensic_widget.show()
            
            self.forensic_status.setText("🟢 Forensic monitor launched")
            self.forensic_status.setStyleSheet("color: #4CAF50;")
            
            # Update button text
            self.launch_forensic_btn.setText("🔍 FORENSIC MONITOR ACTIVE")
            self.launch_forensic_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #45A049;
                }
                QPushButton:pressed {
                    background-color: #3D8B40;
                }
            """)
            
        except ImportError as e:
            self.forensic_status.setText(f"❌ Import error: {e}")
            self.forensic_status.setStyleSheet("color: #F44336;")
        except Exception as e:
            self.forensic_status.setText(f"❌ Launch failed: {e}")
            self.forensic_status.setStyleSheet("color: #F44336;")

    def _start_status_bar_timer(self):
        """Add a live status bar with clock and system info"""
        self._statusbar = self.statusBar()
        self._statusbar.setStyleSheet(
            "QStatusBar { background: #151A21; color: #64748B; border-top: 1px solid #2A3444; font-family: 'JetBrains Mono', monospace; font-size: 11px; }"
            "QStatusBar::item { border: none; }"
        )
        self._sb_clock = QLabel()
        self._sb_clock.setStyleSheet("color: #40E0FF; font-family: 'JetBrains Mono', monospace; padding: 0 12px;")
        self._sb_version = QLabel("TITAN V7.5 SINGULARITY")
        self._sb_version.setStyleSheet("color: #64748B; font-family: 'JetBrains Mono', monospace;")
        self._sb_mode = QLabel("MODE: KINETIC")
        self._sb_mode.setStyleSheet("color: #4CAF50; font-family: 'JetBrains Mono', monospace; padding: 0 12px;")
        self._statusbar.addWidget(self._sb_version)
        self._statusbar.addWidget(self._sb_mode)
        self._statusbar.addPermanentWidget(self._sb_clock)
        self._sb_timer = QTimer(self)
        self._sb_timer.timeout.connect(self._update_status_bar)
        self._sb_timer.start(1000)
        self._update_status_bar()

    def _update_status_bar(self):
        from datetime import datetime
        now = datetime.now()
        self._sb_clock.setText(now.strftime("⏱ %H:%M:%S  |  %Y-%m-%d"))


def show_splash(app):
    """Show branded splash screen while app loads."""
    try:
        from PyQt6.QtWidgets import QSplashScreen
        from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont, QLinearGradient
        from PyQt6.QtCore import Qt

        # Create splash pixmap programmatically (no file dependency)
        splash_pix = QPixmap(600, 380)
        painter = QPainter(splash_pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background gradient
        grad = QLinearGradient(0, 0, 600, 380)
        grad.setColorAt(0, QColor(10, 14, 23))
        grad.setColorAt(1, QColor(13, 21, 37))
        painter.fillRect(0, 0, 600, 380, grad)

        # Hex border
        painter.setPen(QColor(0, 212, 255, 40))
        painter.drawRect(2, 2, 596, 376)
        painter.setPen(QColor(0, 212, 255, 15))
        painter.drawRect(8, 8, 584, 364)

        # Corner accents
        painter.setPen(QColor(0, 212, 255, 80))
        for cx, cy, dx, dy in [(0, 0, 1, 1), (599, 0, -1, 1), (0, 379, 1, -1), (599, 379, -1, -1)]:
            painter.drawLine(cx, cy, cx + dx * 50, cy)
            painter.drawLine(cx, cy, cx, cy + dy * 50)

        # Title
        painter.setPen(QColor(58, 117, 196))
        painter.setFont(QFont("Inter", 28, QFont.Weight.Bold))
        painter.drawText(0, 80, 600, 50, Qt.AlignmentFlag.AlignCenter, "TITAN")

        painter.setFont(QFont("Inter", 11))
        painter.setPen(QColor(58, 117, 196, 150))
        painter.drawText(0, 130, 600, 30, Qt.AlignmentFlag.AlignCenter, "V7.5  SINGULARITY")

        # Subtitle
        painter.setFont(QFont("Inter", 9))
        painter.setPen(QColor(148, 163, 184))
        painter.drawText(0, 170, 600, 25, Qt.AlignmentFlag.AlignCenter, "UNIFIED OPERATIONS DASHBOARD")

        # Loading bar background
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(42, 52, 68, 120))
        painter.drawRoundedRect(150, 260, 300, 6, 3, 3)

        # Loading bar fill
        painter.setBrush(QColor(58, 117, 196, 200))
        painter.drawRoundedRect(150, 260, 180, 6, 3, 3)

        # Status text
        painter.setPen(QColor(60, 80, 100))
        painter.setFont(QFont("JetBrains Mono", 8))
        painter.drawText(0, 280, 600, 20, Qt.AlignmentFlag.AlignCenter, "Initializing shields...")

        # Orange accent dot
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 107, 53))
        painter.drawEllipse(293, 60, 14, 14)

        # Version footer
        painter.setPen(QColor(40, 55, 75))
        painter.setFont(QFont("JetBrains Mono", 7))
        painter.drawText(0, 340, 600, 20, Qt.AlignmentFlag.AlignCenter, "AUTHORITY: Dva.12  |  CODENAME: SINGULARITY  |  BUILD: 7.0.3-FINAL")

        # Scan lines
        painter.setPen(QColor(0, 0, 0, 8))
        for y in range(0, 380, 3):
            painter.drawLine(0, y, 600, y)

        painter.end()

        splash = QSplashScreen(splash_pix)
        splash.show()
        app.processEvents()
        return splash
    except Exception:
        return None


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Apply enterprise theme globally at QApplication level
    try:
        from titan_enterprise_theme import apply_enterprise_theme_to_app
        apply_enterprise_theme_to_app(app, "#00d4ff")
    except ImportError:
        pass

    splash = show_splash(app)

    window = UnifiedOperationCenter()
    window.show()

    if splash:
        splash.finish(window)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
