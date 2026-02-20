#!/usr/bin/env python3
"""
TITAN V7.0.3 SINGULARITY - Genesis Profile Forge: Profile Generation GUI

PyQt6 Desktop Application for creating aged browser profiles.
User selects target from dropdown, enters persona details, clicks "Forge".
Profile is generated for MANUAL use by the human operator.

NO AUTOMATION - This is augmentation, not a bot.
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
    QTabWidget, QCheckBox, QFrame, QSplitter
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QIcon, QPalette, QColor

from genesis_core import (
    GenesisEngine, ProfileConfig, TargetPreset, GeneratedProfile,
    TARGET_PRESETS, TargetCategory
)


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
        self.apply_dark_theme()
    
    def init_ui(self):
        self.setWindowTitle("🔥 GENESIS - The Forge | TITAN V7.0.3")
        try:
            from titan_icon import set_titan_icon
            set_titan_icon(self, "#ff6b35")
        except Exception:
            pass
        self.setMinimumSize(600, 700)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header = QLabel("🔥 GENESIS - THE FORGE")
        header.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("color: #ff6b35; margin-bottom: 10px;")
        layout.addWidget(header)
        
        subtitle = QLabel("Profile Generation for Human Operations")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #888; font-size: 12px;")
        layout.addWidget(subtitle)
        
        # Target Selection Group
        target_group = QGroupBox("🎯 Target Selection")
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
        self.target_notes.setStyleSheet("color: #888; font-style: italic;")
        self.target_notes.setWordWrap(True)
        target_layout.addRow("", self.target_notes)
        
        layout.addWidget(target_group)
        
        # Persona Group
        persona_group = QGroupBox("👤 Persona Details")
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
        
        layout.addWidget(persona_group)
        
        # Profile Settings Group
        settings_group = QGroupBox("⚙️ Profile Settings")
        settings_layout = QFormLayout(settings_group)
        
        self.age_spin = QSpinBox()
        self.age_spin.setRange(7, 365)
        self.age_spin.setValue(90)
        self.age_spin.setSuffix(" days")
        self.age_spin.setMinimumHeight(30)
        settings_layout.addRow("Profile Age:", self.age_spin)
        
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
        
        # Forge Button
        self.forge_btn = QPushButton("🔥 FORGE PROFILE")
        self.forge_btn.setMinimumHeight(50)
        self.forge_btn.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.forge_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff6b35;
                color: white;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #ff8c5a;
            }
            QPushButton:pressed {
                background-color: #cc5629;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #888;
            }
        """)
        self.forge_btn.clicked.connect(self.forge_profile)
        layout.addWidget(self.forge_btn)
        
        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMinimumHeight(8)
        layout.addWidget(self.progress_bar)
        
        # Status Group
        status_group = QGroupBox("📊 Status")
        status_layout = QVBoxLayout(status_group)
        
        self.status_label = QLabel("Ready to forge")
        self.status_label.setStyleSheet("color: #4CAF50; font-size: 14px;")
        status_layout.addWidget(self.status_label)
        
        self.output_label = QLabel("Output: -")
        self.output_label.setStyleSheet("color: #888;")
        self.output_label.setWordWrap(True)
        status_layout.addWidget(self.output_label)
        
        # Launch browser button (hidden until profile is ready)
        self.launch_btn = QPushButton("🚀 Launch Browser with Profile")
        self.launch_btn.setMinimumHeight(40)
        self.launch_btn.setVisible(False)
        self.launch_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #66BB6A;
            }
        """)
        self.launch_btn.clicked.connect(self.launch_browser)
        status_layout.addWidget(self.launch_btn)
        
        layout.addWidget(status_group)
        
        # Spacer
        layout.addStretch()
        
        # Footer
        footer = QLabel("TITAN V7.0.3 SINGULARITY | Reality Synthesis Suite")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet("color: #555; font-size: 10px;")
        layout.addWidget(footer)
        
        # Initialize target notes
        self.on_target_changed(0)
    
    def apply_dark_theme(self):
        """Apply Dark Cyberpunk theme — matches Unified Operation Center"""
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(10, 14, 23))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(200, 210, 220))
        palette.setColor(QPalette.ColorRole.Base, QColor(14, 20, 32))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(18, 26, 40))
        palette.setColor(QPalette.ColorRole.Text, QColor(200, 210, 220))
        palette.setColor(QPalette.ColorRole.Button, QColor(18, 26, 40))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(200, 210, 220))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(255, 107, 53))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(10, 14, 23))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(14, 20, 32))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(200, 210, 220))
        self.setPalette(palette)

        self.setStyleSheet("""
            QMainWindow {
                background-color: #0a0e17;
            }
            QGroupBox {
                font-weight: bold;
                font-family: 'JetBrains Mono', 'Consolas', 'Courier New', monospace;
                color: #ff6b35;
                border: 1px solid rgba(255, 107, 53, 0.3);
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 14px;
                background-color: rgba(14, 20, 32, 0.85);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
                color: #ff6b35;
            }
            QLabel {
                color: #c8d2dc;
            }
            QLineEdit, QComboBox, QSpinBox {
                font-family: 'JetBrains Mono', 'Consolas', monospace;
                background-color: rgba(18, 26, 40, 0.9);
                border: 1px solid rgba(255, 107, 53, 0.2);
                border-radius: 6px;
                padding: 6px 8px;
                color: #e0e6ed;
                selection-background-color: #ff6b35;
                selection-color: #0a0e17;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
                border: 1px solid #ff6b35;
                background-color: rgba(255, 107, 53, 0.05);
            }
            QComboBox::drop-down {
                border: none;
                background: transparent;
            }
            QComboBox QAbstractItemView {
                background-color: #0e1420;
                border: 1px solid #ff6b35;
                color: #e0e6ed;
                selection-background-color: #ff6b35;
                selection-color: #0a0e17;
            }
            QPushButton {
                font-family: 'JetBrains Mono', 'Consolas', monospace;
                background-color: rgba(255, 107, 53, 0.1);
                border: 1px solid rgba(255, 107, 53, 0.3);
                border-radius: 6px;
                padding: 8px 16px;
                color: #ff6b35;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(255, 107, 53, 0.2);
                border: 1px solid #ff6b35;
            }
            QPushButton:pressed {
                background-color: rgba(255, 107, 53, 0.3);
            }
            QPushButton:disabled {
                background-color: rgba(30, 40, 55, 0.5);
                border: 1px solid rgba(100, 110, 120, 0.2);
                color: #556;
            }
            QCheckBox {
                color: #c8d2dc;
                spacing: 8px;
            }
            QCheckBox::indicator:checked {
                background-color: #ff6b35;
                border: 1px solid #ff6b35;
                border-radius: 3px;
            }
            QProgressBar {
                border: 1px solid rgba(255, 107, 53, 0.3);
                border-radius: 4px;
                background-color: rgba(14, 20, 32, 0.8);
                text-align: center;
                color: #ff6b35;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #ff6b35, stop:1 #ff9800);
                border-radius: 3px;
            }
            QScrollBar:vertical {
                background: #0a0e17;
                width: 8px;
                border: none;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 107, 53, 0.3);
                border-radius: 4px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255, 107, 53, 0.5);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QToolTip {
                background-color: #0e1420;
                color: #ff6b35;
                border: 1px solid #ff6b35;
                padding: 4px 8px;
                border-radius: 4px;
                font-family: 'JetBrains Mono', 'Consolas', monospace;
            }
        """)
    
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
            hardware_profile=hardware_map.get(self.hardware_combo.currentIndex(), "us_windows_desktop")
        )
        
        # Disable UI
        self.forge_btn.setEnabled(False)
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
        self.status_label.setStyleSheet("color: #FFC107; font-size: 14px;")
    
    def on_finished(self, result):
        """Handle generation completion"""
        self.forge_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        if isinstance(result, Exception):
            self.status_label.setText(f"Error: {str(result)}")
            self.status_label.setStyleSheet("color: #f44336; font-size: 14px;")
            QMessageBox.critical(self, "Forge Failed", str(result))
        else:
            self.last_profile = result
            self.status_label.setText(f"✅ Profile forged successfully!")
            self.status_label.setStyleSheet("color: #4CAF50; font-size: 14px;")
            self.output_label.setText(f"Output: {result.profile_path}")
            self.launch_btn.setVisible(True)
            
            QMessageBox.information(
                self, 
                "Profile Ready",
                f"Profile created at:\n{result.profile_path}\n\n"
                f"History entries: {result.history_count}\n"
                f"Cookies: {result.cookies_count}\n"
                f"Age: {result.age_days} days\n\n"
                f"Click 'Launch Browser' to use this profile."
            )
    
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
        
        self.status_label.setText(f"🚀 Launched {browser} with profile")


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    splash = None
    try:
        from titan_splash import show_titan_splash
        splash = show_titan_splash(app, "GENESIS ENGINE", "#ff6b35")
    except Exception:
        pass
    
    window = GenesisApp()
    window.show()
    if splash:
        splash.finish(window)
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
