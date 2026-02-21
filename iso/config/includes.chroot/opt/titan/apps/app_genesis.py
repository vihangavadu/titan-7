#!/usr/bin/env python3
"""
TITAN V7.5 SINGULARITY — Identity Synthesis Engine

PyQt6 Desktop Application for creating aged browser profiles.
User selects target from dropdown, enters persona details, clicks "Synthesize".
Profile is generated for MANUAL use by the human operator.

NO AUTOMATION — This is augmentation, not a bot.
"""

import sys
import os
from pathlib import Path

# Add core library to path
sys.path.insert(0, str(Path(__file__).parent.parent / "core"))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QComboBox, QPushButton, QSpinBox, QTextEdit,
    QGroupBox, QFormLayout, QProgressBar, QMessageBox, QFileDialog,
    QTabWidget, QCheckBox, QFrame, QSplitter, QSlider, QDoubleSpinBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QIcon, QPalette, QColor

from genesis_core import (
    GenesisEngine, ProfileConfig, TargetPreset, GeneratedProfile,
    TARGET_PRESETS, TargetCategory
)
from target_presets import TARGET_PRESETS as TP_PRESETS, get_target_preset, list_targets

# V7.5 BIN-aware forge + quality scoring
try:
    from genesis_core import pre_forge_validate, score_profile_quality
    FORGE_INTEL_AVAILABLE = True
except ImportError:
    FORGE_INTEL_AVAILABLE = False

try:
    from cerberus_enhanced import BINScoringEngine
    BIN_SCORER_AVAILABLE = True
except ImportError:
    BIN_SCORER_AVAILABLE = False

# V7.5 AI Intelligence Engine
try:
    from ai_intelligence_engine import audit_profile, get_ai_status, is_ai_available
    from fingerprint_injector import create_injector
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False


class ForgeWorker(QThread):
    """Background worker for profile generation"""
    finished = pyqtSignal(object)  # GeneratedProfile or Exception
    progress = pyqtSignal(str)
    
    def __init__(self, engine: GenesisEngine, config: ProfileConfig):
        super().__init__()
        self.engine = engine
        self.config = config
    
    def run(self):
        try:
            self.progress.emit("Initializing forge...")
            self.progress.emit("Generating browsing history...")
            self.progress.emit("Creating aged cookies...")
            self.progress.emit("Injecting trust anchors...")
            self.progress.emit("Writing browser profile...")
            
            profile = self.engine.forge_profile(self.config)
            self.finished.emit(profile)
        except Exception as e:
            self.finished.emit(e)


class GenesisApp(QMainWindow):
    """
    Genesis - The Forge
    
    Main GUI for profile generation.
    
    Layout:
    ┌─────────────────────────────────────────────────┐
    │  🔥 GENESIS - THE FORGE                         │
    ├─────────────────────────────────────────────────┤
    │  Target: [Dropdown: Amazon US, Eneba, etc.]     │
    │  ─────────────────────────────────────────────  │
    │  Persona:                                       │
    │    Name: [________________]                     │
    │    Email: [________________]                    │
    │    Address: [________________]                  │
    │  ─────────────────────────────────────────────  │
    │  Profile Age: [90] days                         │
    │  Browser: [Firefox ▼]                           │
    │  Hardware: [US Windows Desktop ▼]               │
    │  ─────────────────────────────────────────────  │
    │  [  🔥 FORGE PROFILE  ]                         │
    │  ─────────────────────────────────────────────  │
    │  Status: Ready                                  │
    │  Output: /opt/titan/profiles/titan_abc123       │
    └─────────────────────────────────────────────────┘
    """
    
    def __init__(self):
        super().__init__()
        self.engine = GenesisEngine()
        self.worker = None
        self.last_profile: GeneratedProfile = None
        
        self.init_ui()
        self._apply_theme()
    
    def init_ui(self):
        self.setWindowTitle("TITAN V7.5 — Genesis Profile Forge")
        try:
            from titan_icon import set_titan_icon
            set_titan_icon(self, "#ff6b35")
        except Exception:
            pass
        self.setMinimumSize(900, 800)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(6)
        main_layout.setContentsMargins(8, 8, 8, 8)
        
        # Header
        header = QLabel("TITAN V7.5 — GENESIS FORGE")
        header.setFont(QFont("JetBrains Mono", 20, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("color: #ff6b35; padding: 4px;")
        main_layout.addWidget(header)
        
        subtitle = QLabel("Profile Generation for Human Operations")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #94A3B8; font-size: 11px; font-family: 'JetBrains Mono', monospace; margin-bottom: 4px;")
        main_layout.addWidget(subtitle)
        
        # === TABBED INTERFACE ===
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # ── Tab 1: SYNTHESIZE ──
        self._build_synthesize_tab()
        
        # ── Tab 2: PROFILE HISTORY ──
        self._build_history_tab()
        
        # ── Tab 3: PROFILE INSPECTOR ──
        self._build_inspector_tab()
        
        # ── Tab 4: BATCH SYNTHESIS ──
        self._build_batch_tab()
        
        # ── Tab 5: AI PROFILE AUDIT ──
        self._build_ai_audit_tab()
        
        # Footer
        footer = QLabel("TITAN V7.5 SINGULARITY | Identity Synthesis Engine")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet("color: #64748B; font-size: 10px;")
        main_layout.addWidget(footer)
        
        # Status bar
        self._statusbar = self.statusBar()
        self._statusbar.setStyleSheet(
            "QStatusBar { background: #151A21; color: #64748B; border-top: 1px solid #2A3444; font-family: 'JetBrains Mono', monospace; font-size: 11px; }"
        )
        self._sb_version = QLabel("GENESIS V7.5")
        self._sb_version.setStyleSheet("color: #ff6b35; padding: 0 8px;")
        self._sb_ai = QLabel("AI: " + ("ONLINE" if AI_AVAILABLE else "OFFLINE"))
        self._sb_ai.setStyleSheet("color: #4CAF50; padding: 0 8px;" if AI_AVAILABLE else "color: #EF5350; padding: 0 8px;")
        self._statusbar.addWidget(self._sb_version)
        self._statusbar.addWidget(self._sb_ai)
    
    # ═══════════════════════════════════════════════════════════════════
    # TAB 1: SYNTHESIZE (original single-panel form)
    # ═══════════════════════════════════════════════════════════════════
    
    def _build_synthesize_tab(self):
        """Main profile synthesis form."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        self.tabs.addTab(tab, "Synthesize")
        
        # Target Selection Group
        target_group = QGroupBox("Infrastructure Assessment")
        target_layout = QFormLayout(target_group)
        
        self.target_combo = QComboBox()
        self.target_combo.setMinimumHeight(35)
        for preset in GenesisEngine.get_available_targets():
            self.target_combo.addItem(
                f"{preset.display_name} ({preset.category.value})",
                preset.name
            )
        self.target_combo.currentIndexChanged.connect(self.on_target_changed)
        target_layout.addRow("Target:", self.target_combo)
        
        self.target_notes = QLabel("")
        self.target_notes.setStyleSheet("color: #94A3B8; font-style: italic;")
        self.target_notes.setWordWrap(True)
        target_layout.addRow("", self.target_notes)
        
        layout.addWidget(target_group)
        
        # Persona Group
        persona_group = QGroupBox("Identity Configuration")
        persona_layout = QFormLayout(persona_group)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("John Smith")
        self.name_input.setMinimumHeight(30)
        persona_layout.addRow("Full Name:", self.name_input)
        
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("john.smith@gmail.com")
        self.email_input.setMinimumHeight(30)
        persona_layout.addRow("Email:", self.email_input)
        
        self.address_input = QLineEdit()
        self.address_input.setPlaceholderText("123 Main St, New York, NY 10001")
        self.address_input.setMinimumHeight(30)
        persona_layout.addRow("Address:", self.address_input)
        
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("+1 555 123 4567")
        self.phone_input.setMinimumHeight(30)
        persona_layout.addRow("Phone:", self.phone_input)
        
        # V7.5: BIN input for card-aware profile optimization
        bin_row = QHBoxLayout()
        self.bin_input = QLineEdit()
        self.bin_input.setPlaceholderText("e.g. 421783 (optional — optimizes profile for card)")
        self.bin_input.setMaxLength(6)
        self.bin_input.setMinimumHeight(30)
        self.bin_input.setStyleSheet("QLineEdit{font-family:Consolas;font-size:13px;}")
        bin_row.addWidget(self.bin_input)
        self.bin_check_btn = QPushButton("Check")
        self.bin_check_btn.setMinimumHeight(30)
        self.bin_check_btn.setFixedWidth(70)
        self.bin_check_btn.setStyleSheet("QPushButton{background:#ff6b35;color:#000;font-weight:bold;border:none;border-radius:4px;}QPushButton:hover{background:#ff8a50;}")
        self.bin_check_btn.clicked.connect(self._run_pre_forge_check)
        bin_row.addWidget(self.bin_check_btn)
        persona_layout.addRow("Card BIN:", bin_row)
        
        # Pre-forge validation result
        self.preflight_label = QLabel("")
        self.preflight_label.setWordWrap(True)
        self.preflight_label.setStyleSheet("color: #888; font-size: 10px; padding: 2px 0;")
        persona_layout.addRow("", self.preflight_label)
        
        layout.addWidget(persona_group)
        
        # Profile Settings Group
        settings_group = QGroupBox("Synthesis Parameters")
        settings_layout = QFormLayout(settings_group)
        
        self.age_spin = QSpinBox()
        self.age_spin.setRange(7, 365)
        self.age_spin.setValue(90)
        self.age_spin.setSuffix(" days")
        self.age_spin.setMinimumHeight(30)
        settings_layout.addRow("Profile Age:", self.age_spin)
        
        # Age slider 30–900 days (synced with age_spin for rapid adjustment)
        self.age_slider = QSlider(Qt.Orientation.Horizontal)
        self.age_slider.setRange(30, 900)
        self.age_slider.setValue(90)
        self.age_slider.setTickInterval(90)
        self.age_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.age_slider.setToolTip("Quick age selection: 30–900 days")
        age_slider_row = QHBoxLayout()
        age_slider_row.addWidget(QLabel("30d"))
        age_slider_row.addWidget(self.age_slider)
        age_slider_row.addWidget(QLabel("900d"))
        self.age_slider.valueChanged.connect(lambda v: self.age_spin.setValue(min(v, 365)))
        self.age_spin.valueChanged.connect(lambda v: self.age_slider.setValue(v))
        settings_layout.addRow("Age Slider:", age_slider_row)
        
        self.browser_combo = QComboBox()
        self.browser_combo.addItems(["Firefox", "Chromium"])
        self.browser_combo.setMinimumHeight(30)
        settings_layout.addRow("Browser:", self.browser_combo)
        
        self.hardware_combo = QComboBox()
        self.hardware_combo.addItems([
            "US Windows Desktop (Dell XPS, RTX 4070)",
            "US Windows Desktop AMD (ROG Strix, RX 7900)",
            "US Windows Desktop Intel (HP Pavilion, UHD 770)",
            "US MacBook Pro (M3 Pro)",
            "US MacBook Air (M2)",
            "US MacBook (M1)",
            "EU Windows Laptop (ThinkPad X1)",
            "US Gaming Laptop (ROG Zephyrus, RTX 3060)",
            "US Budget Laptop (Acer Aspire)",
            "Linux Desktop (Custom, GTX 1660)"
        ])
        self.hardware_combo.setMinimumHeight(30)
        settings_layout.addRow("Hardware Profile:", self.hardware_combo)
        
        self.archetype_combo = QComboBox()
        self.archetype_combo.addItems([
            "Student Developer",
            "Professional",
            "Retiree",
            "Gamer",
            "Casual Shopper"
        ])
        self.archetype_combo.setMinimumHeight(30)
        settings_layout.addRow("Archetype:", self.archetype_combo)
        
        # History density multiplier 0.5x – 3.0x
        density_row = QHBoxLayout()
        self.density_spin = QDoubleSpinBox()
        self.density_spin.setRange(0.5, 3.0)
        self.density_spin.setValue(1.0)
        self.density_spin.setSingleStep(0.1)
        self.density_spin.setDecimals(1)
        self.density_spin.setSuffix("x")
        self.density_spin.setMinimumHeight(30)
        self.density_spin.setToolTip("Multiplier for browsing history density (0.5x sparse → 3.0x ultra-dense)")
        density_row.addWidget(self.density_spin)
        density_lbl = QLabel(" (0.5x sparse → 3.0x ultra-dense)")
        density_lbl.setStyleSheet("color: #64748B; font-size: 10px;")
        density_row.addWidget(density_lbl)
        settings_layout.addRow("History Density:", density_row)
        
        # Checkboxes
        checkbox_layout = QHBoxLayout()
        self.social_check = QCheckBox("Social History")
        self.social_check.setChecked(True)
        self.shopping_check = QCheckBox("Shopping History")
        self.shopping_check.setChecked(True)
        self.purchase_hist_check = QCheckBox("Purchase History")
        self.purchase_hist_check.setChecked(True)
        self.autofill_check = QCheckBox("Form Autofill")
        self.autofill_check.setChecked(True)
        checkbox_layout.addWidget(self.social_check)
        checkbox_layout.addWidget(self.shopping_check)
        checkbox_layout.addWidget(self.purchase_hist_check)
        checkbox_layout.addWidget(self.autofill_check)
        settings_layout.addRow("", checkbox_layout)
        
        layout.addWidget(settings_group)
        
        # Synthesize Button
        self.forge_btn = QPushButton("🔥 Forge Profile")
        self.forge_btn.setMinimumHeight(50)
        self.forge_btn.setFont(QFont("JetBrains Mono", 14, QFont.Weight.Bold))
        self.forge_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 107, 53, 0.2);
                color: #ff6b35;
                border: 1px solid #ff6b35;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #ff6b35;
                color: #000000;
            }
            QPushButton:pressed {
                background-color: #cc5522;
                color: #000000;
            }
            QPushButton:disabled {
                background-color: rgba(26, 32, 53, 0.5);
                border: 1px solid rgba(100, 116, 139, 0.3);
                color: #475569;
            }
        """)
        self.forge_btn.clicked.connect(self.forge_profile)
        layout.addWidget(self.forge_btn)
        
        # Quick Forge + View Profile buttons  
        quick_row = QHBoxLayout()
        
        self.quick_forge_btn = QPushButton("⚡ Quick Forge")
        self.quick_forge_btn.setMinimumHeight(38)
        self.quick_forge_btn.setToolTip("Forge with default values — no persona required")
        self.quick_forge_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 107, 53, 0.1);
                color: #ff6b35;
                border: 1px solid rgba(255, 107, 53, 0.5);
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: rgba(255, 107, 53, 0.6);
                color: #000000;
            }
        """)
        self.quick_forge_btn.clicked.connect(self.quick_forge)
        quick_row.addWidget(self.quick_forge_btn)
        
        self.view_profile_btn = QPushButton("📂 View Profile")
        self.view_profile_btn.setMinimumHeight(38)
        self.view_profile_btn.setVisible(False)
        self.view_profile_btn.setToolTip("Open profile directory in file manager")
        self.view_profile_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 255, 136, 0.1);
                color: #00ff88;
                border: 1px solid rgba(0, 255, 136, 0.5);
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: rgba(0, 255, 136, 0.6);
                color: #000000;
            }
        """)
        self.view_profile_btn.clicked.connect(self.open_profile_directory)
        quick_row.addWidget(self.view_profile_btn)
        
        layout.addLayout(quick_row)
        
        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMinimumHeight(8)
        layout.addWidget(self.progress_bar)
        
        # Status Group
        status_group = QGroupBox("Status")
        status_layout = QVBoxLayout(status_group)
        
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #4CAF50; font-size: 14px;")
        status_layout.addWidget(self.status_label)
        
        self.output_label = QLabel("Output: -")
        self.output_label.setStyleSheet("color: #94A3B8;")
        self.output_label.setWordWrap(True)
        status_layout.addWidget(self.output_label)
        
        # Launch browser button (hidden until profile is ready)
        self.launch_btn = QPushButton("🚀 Launch Browser")
        self.launch_btn.setMinimumHeight(40)
        self.launch_btn.setVisible(False)
        self.launch_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 255, 136, 0.15);
                color: #00ff88;
                border: 1px solid #00ff88;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: rgba(0, 255, 136, 0.7);
                color: #000000;
            }
        """)
        self.launch_btn.clicked.connect(self.launch_browser)
        status_layout.addWidget(self.launch_btn)
        
        layout.addWidget(status_group)
        
        # Initialize target notes
        self.on_target_changed(0)
    
    # ═══════════════════════════════════════════════════════════════════
    # TAB 2: PROFILE HISTORY
    # ═══════════════════════════════════════════════════════════════════
    
    def _build_history_tab(self):
        """Profile history — list all previously generated profiles."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        self.tabs.addTab(tab, "History")
        
        # Controls
        ctrl_row = QHBoxLayout()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setStyleSheet("background-color: #3A75C4; color: white; border: none; border-radius: 4px; padding: 8px 16px;")
        refresh_btn.clicked.connect(self._refresh_history)
        ctrl_row.addWidget(refresh_btn)
        
        delete_btn = QPushButton("Delete Selected")
        delete_btn.setStyleSheet("background-color: #C62828; color: white; border: none; border-radius: 4px; padding: 8px 16px;")
        delete_btn.clicked.connect(self._delete_selected_profile)
        ctrl_row.addWidget(delete_btn)
        
        export_btn = QPushButton("Export Selected")
        export_btn.setStyleSheet("background-color: #2E7D32; color: white; border: none; border-radius: 4px; padding: 8px 16px;")
        export_btn.clicked.connect(self._export_selected_profile)
        ctrl_row.addWidget(export_btn)
        
        ctrl_row.addStretch()
        layout.addLayout(ctrl_row)
        
        # Profile list
        from PyQt6.QtWidgets import QListWidget
        self.history_list = QListWidget()
        self.history_list.setMinimumHeight(200)
        self.history_list.setStyleSheet("font-family: 'JetBrains Mono', monospace; font-size: 11px;")
        self.history_list.itemClicked.connect(self._on_history_item_clicked)
        layout.addWidget(self.history_list)
        
        # Profile details
        details_group = QGroupBox("Profile Details")
        details_layout = QVBoxLayout(details_group)
        self.history_details = QTextEdit()
        self.history_details.setReadOnly(True)
        self.history_details.setPlaceholderText("Select a profile from the list above to view details...")
        self.history_details.setStyleSheet("font-family: 'JetBrains Mono', monospace; font-size: 11px;")
        details_layout.addWidget(self.history_details)
        layout.addWidget(details_group)
        
        # Stats
        self.history_stats = QLabel("Profiles: 0 | Total Size: 0 MB")
        self.history_stats.setStyleSheet("color: #94A3B8; font-size: 11px;")
        layout.addWidget(self.history_stats)
    
    def _refresh_history(self):
        """Scan profile directory and list all generated profiles."""
        self.history_list.clear()
        self.history_details.clear()
        profile_dir = Path("/opt/titan/profiles")
        total_size = 0
        count = 0
        
        if profile_dir.exists():
            for p in sorted(profile_dir.iterdir(), key=lambda x: x.stat().st_mtime if x.exists() else 0, reverse=True):
                if p.is_dir() and p.name.startswith("titan_"):
                    try:
                        size = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
                        total_size += size
                        count += 1
                        age_file = p / ".genesis_meta.json"
                        meta = ""
                        if age_file.exists():
                            import json
                            with open(age_file) as f:
                                data = json.load(f)
                            meta = f" | {data.get('persona_name', '?')} | {data.get('age_days', '?')}d | {data.get('browser', '?')}"
                        self.history_list.addItem(f"{p.name}  ({size / 1024 / 1024:.1f} MB){meta}")
                    except Exception:
                        self.history_list.addItem(f"{p.name}  (error reading)")
        
        if count == 0:
            self.history_list.addItem("No profiles found in /opt/titan/profiles/")
        
        self.history_stats.setText(f"Profiles: {count} | Total Size: {total_size / 1024 / 1024:.1f} MB")
    
    def _on_history_item_clicked(self, item):
        """Show details for selected profile."""
        name = item.text().split("  ")[0].strip()
        profile_path = Path("/opt/titan/profiles") / name
        meta_file = profile_path / ".genesis_meta.json"
        
        text = f"Profile: {name}\nPath: {profile_path}\n\n"
        if meta_file.exists():
            try:
                import json
                with open(meta_file) as f:
                    data = json.load(f)
                text += "METADATA:\n"
                for k, v in data.items():
                    text += f"  {k}: {v}\n"
            except Exception as e:
                text += f"Error reading metadata: {e}\n"
        else:
            text += "No metadata file found (.genesis_meta.json)\n"
        
        # List top-level contents
        if profile_path.exists():
            text += f"\nCONTENTS:\n"
            for item_path in sorted(profile_path.iterdir()):
                if item_path.is_dir():
                    sub_count = sum(1 for _ in item_path.rglob("*") if _.is_file())
                    text += f"  [DIR]  {item_path.name}/  ({sub_count} files)\n"
                else:
                    text += f"  [FILE] {item_path.name}  ({item_path.stat().st_size / 1024:.1f} KB)\n"
        
        self.history_details.setPlainText(text)
    
    def _delete_selected_profile(self):
        """Delete selected profile from disk."""
        current = self.history_list.currentItem()
        if not current:
            QMessageBox.warning(self, "No Selection", "Select a profile to delete.")
            return
        name = current.text().split("  ")[0].strip()
        profile_path = Path("/opt/titan/profiles") / name
        
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Permanently delete profile?\n{profile_path}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            import shutil
            try:
                shutil.rmtree(profile_path)
                self._refresh_history()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete: {e}")
    
    def _export_selected_profile(self):
        """Export selected profile as tar.gz archive."""
        current = self.history_list.currentItem()
        if not current:
            QMessageBox.warning(self, "No Selection", "Select a profile to export.")
            return
        name = current.text().split("  ")[0].strip()
        profile_path = Path("/opt/titan/profiles") / name
        
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Export Profile", f"{name}.tar.gz", "Archives (*.tar.gz)"
        )
        if save_path:
            import tarfile
            try:
                with tarfile.open(save_path, "w:gz") as tar:
                    tar.add(str(profile_path), arcname=name)
                QMessageBox.information(self, "Exported", f"Profile exported to:\n{save_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Export failed: {e}")
    
    # ═══════════════════════════════════════════════════════════════════
    # TAB 3: PROFILE INSPECTOR
    # ═══════════════════════════════════════════════════════════════════
    
    def _build_inspector_tab(self):
        """Inspect a profile — view cookies, history, fingerprint, trust score."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        self.tabs.addTab(tab, "Inspector")
        
        # Path input
        path_row = QHBoxLayout()
        self.inspect_path = QLineEdit()
        self.inspect_path.setPlaceholderText("/opt/titan/profiles/titan_XXXXXX")
        self.inspect_path.setMinimumHeight(30)
        path_row.addWidget(self.inspect_path)
        
        browse_btn = QPushButton("Browse...")
        browse_btn.setStyleSheet("background-color: #334155; color: white; border: none; border-radius: 4px; padding: 8px 12px;")
        browse_btn.clicked.connect(self._browse_profile)
        path_row.addWidget(browse_btn)
        
        inspect_btn = QPushButton("Inspect")
        inspect_btn.setStyleSheet("background-color: #3A75C4; color: white; border: none; border-radius: 4px; padding: 8px 16px;")
        inspect_btn.clicked.connect(self._run_inspect)
        path_row.addWidget(inspect_btn)
        layout.addLayout(path_row)
        
        # Inspection sub-tabs
        self.inspect_tabs = QTabWidget()
        layout.addWidget(self.inspect_tabs)
        
        # -- Summary sub-tab --
        summary_w = QWidget()
        summary_l = QVBoxLayout(summary_w)
        self.inspect_summary = QTextEdit()
        self.inspect_summary.setReadOnly(True)
        self.inspect_summary.setPlaceholderText("Load a profile to see summary: age, browser, persona, trust score...")
        self.inspect_summary.setStyleSheet("font-family: 'JetBrains Mono', monospace; font-size: 11px;")
        summary_l.addWidget(self.inspect_summary)
        self.inspect_tabs.addTab(summary_w, "Summary")
        
        # -- Cookies sub-tab --
        cookies_w = QWidget()
        cookies_l = QVBoxLayout(cookies_w)
        self.inspect_cookies = QTextEdit()
        self.inspect_cookies.setReadOnly(True)
        self.inspect_cookies.setPlaceholderText("Cookie inventory will appear here...")
        self.inspect_cookies.setStyleSheet("font-family: 'JetBrains Mono', monospace; font-size: 11px;")
        cookies_l.addWidget(self.inspect_cookies)
        self.inspect_tabs.addTab(cookies_w, "Cookies")
        
        # -- History sub-tab --
        hist_w = QWidget()
        hist_l = QVBoxLayout(hist_w)
        self.inspect_history = QTextEdit()
        self.inspect_history.setReadOnly(True)
        self.inspect_history.setPlaceholderText("Browsing history entries will appear here...")
        self.inspect_history.setStyleSheet("font-family: 'JetBrains Mono', monospace; font-size: 11px;")
        hist_l.addWidget(self.inspect_history)
        self.inspect_tabs.addTab(hist_w, "History")
        
        # -- Fingerprint sub-tab --
        fp_w = QWidget()
        fp_l = QVBoxLayout(fp_w)
        self.inspect_fingerprint = QTextEdit()
        self.inspect_fingerprint.setReadOnly(True)
        self.inspect_fingerprint.setPlaceholderText("Hardware fingerprint details will appear here...")
        self.inspect_fingerprint.setStyleSheet("font-family: 'JetBrains Mono', monospace; font-size: 11px;")
        fp_l.addWidget(self.inspect_fingerprint)
        self.inspect_tabs.addTab(fp_w, "Fingerprint")
    
    def _browse_profile(self):
        """Open directory picker for profile path."""
        path = QFileDialog.getExistingDirectory(self, "Select Profile Directory", "/opt/titan/profiles")
        if path:
            self.inspect_path.setText(path)
    
    def _run_inspect(self):
        """Inspect the selected profile directory."""
        profile_path = Path(self.inspect_path.text().strip())
        if not profile_path.exists():
            self.inspect_summary.setPlainText(f"Profile path does not exist: {profile_path}")
            return
        
        # Summary
        meta_file = profile_path / ".genesis_meta.json"
        summary = f"PROFILE INSPECTION: {profile_path.name}\n{'=' * 60}\n\n"
        
        if meta_file.exists():
            try:
                import json
                with open(meta_file) as f:
                    data = json.load(f)
                summary += "METADATA:\n"
                for k, v in data.items():
                    summary += f"  {k:25s}: {v}\n"
                summary += "\n"
            except Exception as e:
                summary += f"Metadata error: {e}\n\n"
        
        # Size analysis
        total_files = 0
        total_size = 0
        for f in profile_path.rglob("*"):
            if f.is_file():
                total_files += 1
                total_size += f.stat().st_size
        summary += f"DISK USAGE:\n  Files: {total_files}\n  Size: {total_size / 1024 / 1024:.2f} MB\n\n"
        
        # Trust score estimate
        has_cookies = (profile_path / "cookies.sqlite").exists() or (profile_path / "Cookies").exists()
        has_history = (profile_path / "places.sqlite").exists() or (profile_path / "History").exists()
        has_localstorage = (profile_path / "webappsstore.sqlite").exists() or (profile_path / "Local Storage").exists()
        trust = 0
        if has_cookies: trust += 30
        if has_history: trust += 30
        if has_localstorage: trust += 20
        if total_files > 50: trust += 10
        if total_size > 50 * 1024 * 1024: trust += 10
        summary += f"TRUST SCORE ESTIMATE: {trust}/100\n"
        summary += f"  Cookies: {'PRESENT' if has_cookies else 'MISSING'}\n"
        summary += f"  History: {'PRESENT' if has_history else 'MISSING'}\n"
        summary += f"  LocalStorage: {'PRESENT' if has_localstorage else 'MISSING'}\n"
        
        self.inspect_summary.setPlainText(summary)
        
        # Cookies
        cookie_text = "COOKIE INVENTORY:\n" + "=" * 60 + "\n\n"
        cookie_files = list(profile_path.rglob("cookies*")) + list(profile_path.rglob("Cookies*"))
        if cookie_files:
            for cf in cookie_files:
                cookie_text += f"  {cf.relative_to(profile_path)}  ({cf.stat().st_size / 1024:.1f} KB)\n"
        else:
            cookie_text += "  No cookie files found.\n"
        self.inspect_cookies.setPlainText(cookie_text)
        
        # History
        hist_text = "BROWSING HISTORY:\n" + "=" * 60 + "\n\n"
        hist_files = list(profile_path.rglob("places*")) + list(profile_path.rglob("History*"))
        if hist_files:
            for hf in hist_files:
                hist_text += f"  {hf.relative_to(profile_path)}  ({hf.stat().st_size / 1024:.1f} KB)\n"
        else:
            hist_text += "  No history files found.\n"
        self.inspect_history.setPlainText(hist_text)
        
        # Fingerprint
        fp_text = "FINGERPRINT DATA:\n" + "=" * 60 + "\n\n"
        fp_files = list(profile_path.rglob("*fingerprint*")) + list(profile_path.rglob("*prefs*")) + list(profile_path.rglob("*Preferences*"))
        if fp_files:
            for ff in fp_files:
                fp_text += f"  {ff.relative_to(profile_path)}  ({ff.stat().st_size / 1024:.1f} KB)\n"
        else:
            fp_text += "  No fingerprint/preference files found.\n"
        self.inspect_fingerprint.setPlainText(fp_text)
    
    # ═══════════════════════════════════════════════════════════════════
    # TAB 4: BATCH SYNTHESIS
    # ═══════════════════════════════════════════════════════════════════
    
    def _build_batch_tab(self):
        """Batch profile synthesis — generate multiple profiles at once."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        self.tabs.addTab(tab, "Batch")
        
        # Batch config
        config_group = QGroupBox("Batch Configuration")
        config_layout = QFormLayout(config_group)
        
        self.batch_count = QSpinBox()
        self.batch_count.setRange(2, 50)
        self.batch_count.setValue(5)
        self.batch_count.setMinimumHeight(30)
        config_layout.addRow("Number of Profiles:", self.batch_count)
        
        self.batch_target = QComboBox()
        self.batch_target.setMinimumHeight(30)
        for preset in GenesisEngine.get_available_targets():
            self.batch_target.addItem(
                f"{preset.display_name} ({preset.category.value})",
                preset.name
            )
        config_layout.addRow("Target:", self.batch_target)
        
        self.batch_browser = QComboBox()
        self.batch_browser.addItems(["Firefox", "Chromium", "Random"])
        self.batch_browser.setMinimumHeight(30)
        config_layout.addRow("Browser:", self.batch_browser)
        
        self.batch_age_min = QSpinBox()
        self.batch_age_min.setRange(7, 365)
        self.batch_age_min.setValue(30)
        self.batch_age_min.setSuffix(" days")
        self.batch_age_min.setMinimumHeight(30)
        config_layout.addRow("Min Age:", self.batch_age_min)
        
        self.batch_age_max = QSpinBox()
        self.batch_age_max.setRange(7, 365)
        self.batch_age_max.setValue(180)
        self.batch_age_max.setSuffix(" days")
        self.batch_age_max.setMinimumHeight(30)
        config_layout.addRow("Max Age:", self.batch_age_max)
        
        self.batch_auto_persona = QCheckBox("Auto-generate persona names and emails")
        self.batch_auto_persona.setChecked(True)
        config_layout.addRow("", self.batch_auto_persona)
        
        layout.addWidget(config_group)
        
        # Buttons
        btn_row = QHBoxLayout()
        self.batch_start_btn = QPushButton("Start Batch Synthesis")
        self.batch_start_btn.setMinimumHeight(45)
        self.batch_start_btn.setFont(QFont("Inter", 12, QFont.Weight.Bold))
        self.batch_start_btn.setStyleSheet("""
            QPushButton {
                background-color: #3A75C4;
                color: white;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #4A8AD8; }
            QPushButton:disabled { background-color: #2A3444; color: #64748B; }
        """)
        self.batch_start_btn.clicked.connect(self._start_batch)
        btn_row.addWidget(self.batch_start_btn)
        
        self.batch_stop_btn = QPushButton("Stop")
        self.batch_stop_btn.setMinimumHeight(45)
        self.batch_stop_btn.setEnabled(False)
        self.batch_stop_btn.setStyleSheet("background-color: #C62828; color: white; border: none; border-radius: 6px; padding: 8px 16px;")
        self.batch_stop_btn.clicked.connect(self._stop_batch)
        btn_row.addWidget(self.batch_stop_btn)
        layout.addLayout(btn_row)
        
        # Progress
        self.batch_progress = QProgressBar()
        self.batch_progress.setMinimumHeight(12)
        self.batch_progress.setTextVisible(True)
        layout.addWidget(self.batch_progress)
        
        # Log
        self.batch_log = QTextEdit()
        self.batch_log.setReadOnly(True)
        self.batch_log.setPlaceholderText("Batch synthesis log will appear here...")
        self.batch_log.setStyleSheet("font-family: 'JetBrains Mono', monospace; font-size: 11px;")
        layout.addWidget(self.batch_log)
    
    def _start_batch(self):
        """Start batch profile synthesis."""
        import random
        count = self.batch_count.value()
        self.batch_progress.setRange(0, count)
        self.batch_progress.setValue(0)
        self.batch_log.clear()
        self.batch_start_btn.setEnabled(False)
        self.batch_stop_btn.setEnabled(True)
        self._batch_cancelled = False
        
        target_name = self.batch_target.currentData()
        target = GenesisEngine.get_target_by_name(target_name)
        
        first_names = ["James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda",
                       "David", "Elizabeth", "William", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
                       "Thomas", "Sarah", "Christopher", "Karen", "Daniel", "Lisa", "Matthew", "Nancy"]
        last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
                      "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
                      "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson"]
        
        self.batch_log.append(f"Starting batch synthesis: {count} profiles for {target_name}\n")
        
        for i in range(count):
            if self._batch_cancelled:
                self.batch_log.append(f"\n[CANCELLED] Stopped at profile {i}/{count}")
                break
            
            fname = random.choice(first_names)
            lname = random.choice(last_names)
            age = random.randint(self.batch_age_min.value(), self.batch_age_max.value())
            browser_choice = self.batch_browser.currentText().lower()
            if browser_choice == "random":
                browser_choice = random.choice(["firefox", "chromium"])
            
            self.batch_log.append(f"[{i+1}/{count}] Synthesizing: {fname} {lname} | {age}d | {browser_choice}")
            
            # V7.5: Randomize hardware profiles for batch diversity
            batch_hw_pool = [
                "us_windows_desktop", "us_windows_desktop_amd", "us_windows_desktop_intel",
                "us_macbook_pro", "us_macbook_air_m2", "eu_windows_laptop",
                "us_windows_laptop_gaming", "us_windows_laptop_budget",
            ]
            batch_hw = random.choice(batch_hw_pool)
            
            try:
                config = ProfileConfig(
                    target=target,
                    persona_name=f"{fname} {lname}",
                    persona_email=f"{fname.lower()}.{lname.lower()}{random.randint(10,99)}@gmail.com",
                    persona_address={"full": f"{random.randint(100,9999)} Main St", "phone": ""},
                    age_days=age,
                    browser=browser_choice,
                    include_social_history=True,
                    include_shopping_history=True,
                    hardware_profile=batch_hw
                )
                profile = self.engine.forge_profile(config)
                self.batch_log.append(f"  -> OK: {profile.profile_path}")
            except Exception as e:
                self.batch_log.append(f"  -> ERROR: {e}")
            
            self.batch_progress.setValue(i + 1)
            QApplication.processEvents()
        
        self.batch_start_btn.setEnabled(True)
        self.batch_stop_btn.setEnabled(False)
        if not self._batch_cancelled:
            self.batch_log.append(f"\nBatch complete: {count} profiles generated.")
    
    def _stop_batch(self):
        """Cancel batch synthesis."""
        self._batch_cancelled = True
    
    # ═══════════════════════════════════════════════════════════════════
    # TAB 5: AI PROFILE AUDIT
    # ═══════════════════════════════════════════════════════════════════
    
    def _build_ai_audit_tab(self):
        """AI-powered profile forensic audit."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        self.tabs.addTab(tab, "🧠 AI Audit")
        
        header = QLabel("🧠 AI PROFILE FORENSIC AUDIT")
        header.setFont(QFont("JetBrains Mono", 14, QFont.Weight.Bold))
        header.setStyleSheet("color: #E6A817;")
        layout.addWidget(header)
        layout.addWidget(QLabel("AI analyzes generated profiles for antifraud detection vectors"))
        
        btn_row = QHBoxLayout()
        self.ai_audit_btn = QPushButton("🔬 AUDIT LAST PROFILE")
        self.ai_audit_btn.setMinimumHeight(40)
        self.ai_audit_btn.setStyleSheet("QPushButton{background:#E6A817;color:#000;font-weight:bold;font-size:13px;}")
        self.ai_audit_btn.clicked.connect(self._run_ai_audit)
        btn_row.addWidget(self.ai_audit_btn)
        
        self.ai_audit_browse = QPushButton("📁 Select Profile")
        self.ai_audit_browse.setMinimumHeight(40)
        self.ai_audit_browse.clicked.connect(self._browse_audit_profile)
        btn_row.addWidget(self.ai_audit_browse)
        
        self.ai_inject_fp = QPushButton("🧬 Inject Fingerprint")
        self.ai_inject_fp.setMinimumHeight(40)
        self.ai_inject_fp.clicked.connect(self._inject_fingerprint)
        btn_row.addWidget(self.ai_inject_fp)
        btn_row.addStretch()
        layout.addLayout(btn_row)
        
        self.ai_audit_path_label = QLabel("Profile: (auto-detect from last forge)")
        self.ai_audit_path_label.setStyleSheet("color: #64748B;")
        layout.addWidget(self.ai_audit_path_label)
        
        self.ai_audit_result = QTextEdit()
        self.ai_audit_result.setReadOnly(True)
        self.ai_audit_result.setPlaceholderText(
            "AI Forensic Profile Audit (Ollama-powered):\n\n"
            "  • Timestamp consistency analysis\n"
            "  • OS/UA mismatch detection\n"
            "  • Cookie/history coherence check\n"
            "  • Leak vector identification\n"
            "  • Cleanliness score 0-100\n\n"
            "Forge a profile first, then click AUDIT."
        )
        layout.addWidget(self.ai_audit_result)
    
    def _run_ai_audit(self):
        """Run AI audit on the last generated profile."""
        if not AI_AVAILABLE:
            self.ai_audit_result.setPlainText("AI Intelligence Engine not available.")
            return
        profile_path = getattr(self, '_audit_profile_path', None)
        if not profile_path and self.last_profile:
            profile_path = str(self.last_profile.profile_path)
        if not profile_path:
            profiles_dir = Path("/opt/titan/profiles")
            if profiles_dir.exists():
                dirs = sorted(profiles_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
                if dirs:
                    profile_path = str(dirs[0])
        if not profile_path:
            self.ai_audit_result.setPlainText("No profile found. Forge one first.")
            return
        self.ai_audit_path_label.setText(f"Profile: {profile_path}")
        self.ai_audit_result.setPlainText(f"🔬 Auditing: {profile_path}...")
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
            self.ai_audit_result.setPlainText(text)
        except Exception as e:
            self.ai_audit_result.setPlainText(f"Error: {e}")
    
    def _browse_audit_profile(self):
        """Browse for profile to audit."""
        path = QFileDialog.getExistingDirectory(self, "Select Profile", "/opt/titan/profiles")
        if path:
            self._audit_profile_path = path
            self.ai_audit_path_label.setText(f"Profile: {path}")
    
    def _inject_fingerprint(self):
        """Inject hardware fingerprint into profile."""
        if not AI_AVAILABLE:
            self.ai_audit_result.setPlainText("Fingerprint injector not available.")
            return
        profile_path = getattr(self, '_audit_profile_path', None)
        if not profile_path and self.last_profile:
            profile_path = str(self.last_profile.profile_path)
        if not profile_path:
            self.ai_audit_result.setPlainText("No profile selected.")
            return
        try:
            injector = create_injector(Path(profile_path).name)
            config = injector.generate_config()
            text = f"FINGERPRINT INJECTED\n{'='*50}\n\n"
            text += f"  Profile: {profile_path}\n"
            text += f"  Parameters: {len(config)}\n\n"
            for k, v in list(config.items())[:12]:
                text += f"  {k}: {str(v)[:50]}\n"
            if len(config) > 12:
                text += f"\n  ... and {len(config) - 12} more\n"
            self.ai_audit_result.setPlainText(text)
        except Exception as e:
            self.ai_audit_result.setPlainText(f"Error: {e}")
    
    def _apply_theme(self):
        """Apply Genesis Orange cyberpunk theme."""
        try:
            from titan_enterprise_theme import apply_enterprise_theme
            apply_enterprise_theme(self, "#ff6b35")  # Genesis Orange
        except ImportError:
            pass  # Fallback: no theme applied
    
    def _run_pre_forge_check(self):
        """Run pre-forge validation — check BIN vs hardware/geo/proxy consistency."""
        bin6 = self.bin_input.text().strip().replace(" ", "")[:6]
        if len(bin6) < 6 or not bin6.isdigit():
            self.preflight_label.setText("Enter a valid 6-digit BIN to check")
            self.preflight_label.setStyleSheet("color: #888; font-size: 10px;")
            return

        if not FORGE_INTEL_AVAILABLE:
            self.preflight_label.setText("Pre-forge validation not available (missing genesis_core functions)")
            return

        hardware_map = {
            0: "us_windows_desktop", 1: "us_windows_desktop_amd", 2: "us_windows_desktop_intel",
            3: "us_macbook_pro", 4: "us_macbook_air_m2", 5: "us_macbook_m1",
            6: "eu_windows_laptop", 7: "us_windows_laptop_gaming", 8: "us_windows_laptop_budget",
            9: "linux_desktop",
        }
        hw = hardware_map.get(self.hardware_combo.currentIndex(), "us_windows_desktop")
        addr_text = self.address_input.text().strip()
        billing = {"full": addr_text, "country": "US"}

        result = pre_forge_validate(bin6, billing, hw)

        parts = []
        if result.get("bin_info"):
            bi = result["bin_info"]
            parts.append(f"Card: {bi.get('bank','?')} {bi.get('level','?').title()} {bi.get('network','?').upper()} ({bi.get('country','?')})")

        if result["errors"]:
            for e in result["errors"]:
                parts.append(f"<span style='color:#f44336;'>ERROR: {e}</span>")
        if result["warnings"]:
            for w in result["warnings"]:
                parts.append(f"<span style='color:#ff9800;'>WARN: {w}</span>")
        if result["recommendations"]:
            for r in result["recommendations"]:
                parts.append(f"<span style='color:#4fc3f7;'>TIP: {r}</span>")

        optimal_hw = result.get("optimal_hardware", [])
        if optimal_hw:
            parts.append(f"<span style='color:#00e676;'>Optimal HW: {', '.join(optimal_hw[:3])}</span>")
        optimal_arch = result.get("optimal_archetype", "")
        if optimal_arch:
            parts.append(f"<span style='color:#00e676;'>Optimal Archetype: {optimal_arch}</span>")

        if result["passed"] and not result["warnings"]:
            parts.insert(0, "<span style='color:#00e676;'>PRE-FORGE CHECK PASSED</span>")
        elif result["passed"]:
            parts.insert(0, "<span style='color:#ffeb3b;'>PRE-FORGE CHECK: CAUTION</span>")
        else:
            parts.insert(0, "<span style='color:#f44336;'>PRE-FORGE CHECK FAILED</span>")

        self.preflight_label.setText("<br>".join(parts))

    def on_target_changed(self, index):
        """Update UI when target selection changes"""
        target_name = self.target_combo.currentData()
        target = GenesisEngine.get_target_by_name(target_name)
        
        if target:
            self.target_notes.setText(target.notes or f"Recommended age: {target.recommended_age_days} days")
            self.age_spin.setValue(target.recommended_age_days)
            
            # Set browser preference
            if target.browser_preference == "firefox":
                self.browser_combo.setCurrentIndex(0)
            else:
                self.browser_combo.setCurrentIndex(1)
    
    def forge_profile(self):
        """Start profile generation"""
        # Validate inputs
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Please enter a persona name")
            return
        
        if not self.email_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Please enter an email address")
            return
        
        # Get target
        target_name = self.target_combo.currentData()
        target = GenesisEngine.get_target_by_name(target_name)
        
        if not target:
            QMessageBox.warning(self, "Error", "Invalid target selection")
            return
        
        # Build config
        hardware_map = {
            0: "us_windows_desktop",
            1: "us_windows_desktop_amd",
            2: "us_windows_desktop_intel",
            3: "us_macbook_pro",
            4: "us_macbook_air_m2",
            5: "us_macbook_m1",
            6: "eu_windows_laptop",
            7: "us_windows_laptop_gaming",
            8: "us_windows_laptop_budget",
            9: "linux_desktop",
        }
        
        selected_hw = hardware_map.get(self.hardware_combo.currentIndex(), "us_windows_desktop")
        
        # V7.5: BIN-aware hardware optimization
        bin6 = self.bin_input.text().strip().replace(" ", "")[:6]
        if bin6 and len(bin6) == 6 and bin6.isdigit() and FORGE_INTEL_AVAILABLE:
            import random as _rand
            validation = pre_forge_validate(bin6, {"full": self.address_input.text().strip(), "country": "US"}, selected_hw)
            optimal_hw_list = validation.get("optimal_hardware", [])
            if optimal_hw_list and selected_hw not in optimal_hw_list:
                selected_hw = _rand.choice(optimal_hw_list)
                self.preflight_label.setText(
                    f"<span style='color:#00e676;'>Auto-optimized HW to: {selected_hw} (matches {validation.get('card_level','?')} card)</span>"
                )
        
        config = ProfileConfig(
            target=target,
            persona_name=self.name_input.text().strip(),
            persona_email=self.email_input.text().strip(),
            persona_address={
                "full": self.address_input.text().strip(),
                "phone": self.phone_input.text().strip(),
            },
            age_days=self.age_spin.value(),
            browser=self.browser_combo.currentText().lower(),
            include_social_history=self.social_check.isChecked(),
            include_shopping_history=self.shopping_check.isChecked(),
            hardware_profile=selected_hw
        )
        
        # Disable UI
        self.forge_btn.setEnabled(False)
        self.quick_forge_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.launch_btn.setVisible(False)
        
        # Start worker
        self.worker = ForgeWorker(self.engine, config)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()
    
    def on_progress(self, message: str):
        """Update status during generation"""
        self.status_label.setText(message)
        self.status_label.setStyleSheet("color: #FFB74D; font-size: 14px;")
    
    def on_finished(self, result):
        """Handle generation completion"""
        self.forge_btn.setEnabled(True)
        self.quick_forge_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        if isinstance(result, Exception):
            self.status_label.setText(f"Error: {str(result)}")
            self.status_label.setStyleSheet("color: #ff4466; font-size: 14px;")
            QMessageBox.critical(self, "Forge Failed", str(result))
        else:
            self.last_profile = result
            self.launch_btn.setVisible(True)
            self.view_profile_btn.setVisible(True)
            
            # V7.5: Post-forge quality score
            quality_text = ""
            if FORGE_INTEL_AVAILABLE:
                try:
                    qs = score_profile_quality(result.profile_path)
                    quality_text = (
                        f"\n\nQUALITY SCORE: {qs['icon']} {qs['score']}/100 — {qs['verdict']}\n"
                        f"Size: {qs['size_mb']} MB | Files: {qs['file_count']}\n"
                    )
                    for check_name, check_ok in qs.get("checks", []):
                        quality_text += f"  {'✅' if check_ok else '❌'} {check_name}\n"
                    
                    verdict_color = "#00ff88" if qs['verdict'] == 'GO' else "#ffeb3b" if qs['verdict'] == 'CAUTION' else "#ff4466"
                    self.status_label.setText(f"{qs['icon']} Profile forged — {qs['verdict']} ({qs['score']}/100)")
                    self.status_label.setStyleSheet(f"color: {verdict_color}; font-size: 14px;")
                except Exception:
                    self.status_label.setText("Profile forged successfully")
                    self.status_label.setStyleSheet("color: #00ff88; font-size: 14px;")
            else:
                self.status_label.setText("Profile forged successfully")
                self.status_label.setStyleSheet("color: #00ff88; font-size: 14px;")
            
            self.output_label.setText(f"Output: {result.profile_path}")
            
            QMessageBox.information(
                self, 
                "Profile Ready — Forge Complete",
                f"Profile created at:\n{result.profile_path}\n\n"
                f"History entries: {result.history_count}\n"
                f"Cookies: {result.cookies_count}\n"
                f"Age: {result.age_days} days"
                f"{quality_text}\n"
                f"Click 'Launch Browser' to use this profile."
            )
    
    def quick_forge(self):
        """Quick Forge: use default values for rapid profile generation (no persona required)."""
        import random, string
        first = random.choice(["James","Mary","Robert","Patricia","John","Jennifer","Michael"])
        last = random.choice(["Smith","Johnson","Williams","Brown","Jones","Garcia","Miller"])
        rand_num = ''.join(random.choices(string.digits, k=4))
        
        self.name_input.setText(f"{first} {last}")
        self.email_input.setText(f"{first.lower()}.{last.lower()}{rand_num}@gmail.com")
        self.address_input.setText(f"{random.randint(100,9999)} Main St")
        self.phone_input.setText(f"+1 555 {random.randint(100,999)} {random.randint(1000,9999)}")
        self.age_spin.setValue(90)
        
        self.quick_forge_btn.setEnabled(False)
        self.forge_profile()
    
    def open_profile_directory(self):
        """Open profile directory in the system file manager."""
        if self.last_profile and self.last_profile.profile_path:
            path = str(self.last_profile.profile_path)
            try:
                import subprocess
                subprocess.Popen(["xdg-open", path])
            except Exception:
                QMessageBox.information(self, "Profile Path", path)
    
    def launch_browser(self):
        """Launch browser with the generated profile"""
        if not self.last_profile:
            return
        
        browser = self.last_profile.browser_type
        profile_path = self.last_profile.profile_path
        
        if browser == "firefox":
            cmd = f"firefox --profile {profile_path}"
        else:
            cmd = f"chromium --user-data-dir={profile_path}"
        
        os.system(f"{cmd} &")
        
        self.status_label.setText(f"Session initiated — {browser} launched")


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    try:
        from titan_enterprise_theme import apply_enterprise_theme_to_app
        apply_enterprise_theme_to_app(app, "#ff6b35")
    except ImportError:
        pass

    splash = None
    try:
        from titan_splash import show_titan_splash
        splash = show_titan_splash(app, "GENESIS — THE FORGE", "#ff6b35")
    except Exception:
        pass
    
    window = GenesisApp()
    window.show()
    if splash:
        splash.finish(window)
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
