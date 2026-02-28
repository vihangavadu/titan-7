#!/usr/bin/env python3
"""
Titan X - Launch All GUI Apps
Launches all 11 standalone PyQt6 GUI applications for manual verification.
"""

import sys
import os

# Set up paths
TITAN_ROOT = "/root/Downloads/titan-7/titan-7/titan-7"
sys.path.insert(0, f"{TITAN_ROOT}/src")
sys.path.insert(0, f"{TITAN_ROOT}/src/core")
sys.path.insert(0, f"{TITAN_ROOT}/src/apps")

os.environ["TITAN_ROOT"] = TITAN_ROOT
os.environ["PYTHONPATH"] = f"{TITAN_ROOT}/src:{TITAN_ROOT}/src/core:{TITAN_ROOT}/src/apps"

from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QLabel, QGridLayout, QFrame
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

# All 11 GUI Apps
APPS = [
    ("Titan Launcher", "titan_launcher", "TitanLauncher", "#00d4ff"),
    ("Operations Center", "titan_operations", "TitanOperations", "#00d4ff"),
    ("Intelligence Hub", "titan_intelligence", "TitanIntelligence", "#ff6b35"),
    ("Network Control", "titan_network", "TitanNetwork", "#00ff88"),
    ("Admin Panel", "titan_admin", "TitanAdmin", "#ff3366"),
    ("Profile Forge", "app_profile_forge", "TitanProfileForge", "#9d4edd"),
    ("Card Validator (Cerberus)", "app_card_validator", "TitanCardValidator", "#ffd700"),
    ("KYC - The Mask", "app_kyc", "KYCApp", "#00ffcc"),
    ("Browser Launch", "app_browser_launch", "TitanBrowserLaunch", "#4dabf7"),
    ("Bug Reporter", "app_bug_reporter", "BugReporterWindow", "#ff8c00"),
    ("Settings", "app_settings", "TitanSettings", "#888888"),
]

class AppLauncherHub(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TITAN X V10.0 - App Launcher Hub")
        self.setMinimumSize(800, 600)
        self.setStyleSheet("""
            QMainWindow { background-color: #0a0a0f; }
            QLabel { color: #ffffff; }
            QPushButton {
                background-color: #1a1a2e;
                color: #ffffff;
                border: 2px solid #00d4ff;
                border-radius: 8px;
                padding: 15px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #00d4ff;
                color: #000000;
            }
            QPushButton:pressed {
                background-color: #0099cc;
            }
        """)
        
        self.app_windows = {}
        self.init_ui()
    
    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Header
        header = QLabel("TITAN X V10.0 — App Launcher Hub")
        header.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        header.setStyleSheet("color: #00d4ff;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        subtitle = QLabel("Click any app to launch it for manual verification")
        subtitle.setFont(QFont("Arial", 12))
        subtitle.setStyleSheet("color: #888888;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)
        
        # App Grid
        grid_frame = QFrame()
        grid_frame.setStyleSheet("background-color: #12121a; border-radius: 10px; padding: 20px;")
        grid_layout = QGridLayout(grid_frame)
        grid_layout.setSpacing(15)
        
        for i, (name, module, classname, color) in enumerate(APPS):
            btn = QPushButton(name)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #1a1a2e;
                    color: #ffffff;
                    border: 2px solid {color};
                    border-radius: 8px;
                    padding: 20px;
                    font-size: 13px;
                    font-weight: bold;
                    min-height: 60px;
                }}
                QPushButton:hover {{
                    background-color: {color};
                    color: #000000;
                }}
            """)
            btn.clicked.connect(lambda checked, m=module, c=classname, n=name: self.launch_app(m, c, n))
            row = i // 3
            col = i % 3
            grid_layout.addWidget(btn, row, col)
        
        layout.addWidget(grid_frame)
        
        # Launch All Button
        launch_all_btn = QPushButton("🚀 LAUNCH ALL APPS")
        launch_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #00d4ff;
                color: #000000;
                border: none;
                border-radius: 8px;
                padding: 20px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #00ffff;
            }
        """)
        launch_all_btn.clicked.connect(self.launch_all)
        layout.addWidget(launch_all_btn)
        
        # Status
        self.status_label = QLabel("Ready - Click an app to launch")
        self.status_label.setStyleSheet("color: #00ff88; font-size: 12px;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
    
    def launch_app(self, module_name, class_name, display_name):
        try:
            if display_name in self.app_windows and self.app_windows[display_name].isVisible():
                self.app_windows[display_name].raise_()
                self.app_windows[display_name].activateWindow()
                self.status_label.setText(f"✅ {display_name} already open - brought to front")
                return
            
            self.status_label.setText(f"⏳ Loading {display_name}...")
            self.status_label.repaint()
            
            module = __import__(module_name)
            app_class = getattr(module, class_name)
            window = app_class()
            window.show()
            window.raise_()
            
            self.app_windows[display_name] = window
            self.status_label.setText(f"✅ {display_name} launched successfully")
            self.status_label.setStyleSheet("color: #00ff88; font-size: 12px;")
            
        except Exception as e:
            self.status_label.setText(f"❌ Failed to launch {display_name}: {str(e)[:50]}")
            self.status_label.setStyleSheet("color: #ff3366; font-size: 12px;")
            print(f"Error launching {display_name}: {e}")
    
    def launch_all(self):
        self.status_label.setText("⏳ Launching all apps...")
        for name, module, classname, color in APPS:
            self.launch_app(module, classname, name)
        self.status_label.setText(f"✅ All {len(APPS)} apps launched")

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    hub = AppLauncherHub()
    hub.show()
    hub.raise_()
    
    print("="*60)
    print("  TITAN X V10.0 - App Launcher Hub")
    print("  All 11 GUI apps ready for manual verification")
    print("="*60)
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
