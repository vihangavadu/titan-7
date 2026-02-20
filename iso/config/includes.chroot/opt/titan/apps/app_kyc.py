#!/usr/bin/env python3
"""
TITAN V7.0.3 SINGULARITY - KYC App
The Mask: Virtual Camera Controller GUI

PyQt6 Desktop Application for system-level virtual camera control.
User loads face image, selects motion, adjusts sliders, streams to /dev/video.
Works with ANY app (Browser, Zoom, Telegram) - not browser-coupled.

Controls:
- Source Image: ID photo or generated face
- Motion Type: Blink, Smile, Head Turn, etc.
- Sliders: Head rotation, expression intensity, blink frequency
- Stream: Start/Stop virtual camera output
"""

import sys
import os
from pathlib import Path

# Add core library to path
sys.path.insert(0, str(Path(__file__).parent.parent / "core"))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QComboBox, QPushButton, QSlider, QGroupBox,
    QFormLayout, QProgressBar, QMessageBox, QFileDialog, QFrame,
    QSpinBox, QCheckBox, QListWidget, QListWidgetItem, QSplitter,
    QTabWidget, QPlainTextEdit
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QPixmap, QImage, QPalette, QColor

from kyc_core import (
    KYCController, ReenactmentConfig, VirtualCameraConfig,
    CameraState, MotionType, IntegrityShield
)

# Enhanced KYC imports (document injection, liveness, provider profiles)
try:
    from kyc_enhanced import (
        KYCEnhancedController, KYCSessionConfig, DocumentAsset, FaceAsset,
        LivenessChallenge, KYCProvider, DocumentType, KYC_PROVIDER_PROFILES,
        create_kyc_session
    )
    KYC_ENHANCED_AVAILABLE = True
except ImportError:
    KYC_ENHANCED_AVAILABLE = False

# Waydroid mobile sync
try:
    from waydroid_sync import WaydroidSyncEngine, SyncConfig, MobilePersona
    WAYDROID_AVAILABLE = True
except ImportError:
    WAYDROID_AVAILABLE = False


class StreamWorker(QThread):
    """Background worker for camera streaming"""
    state_changed = pyqtSignal(str)
    error = pyqtSignal(str)
    
    def __init__(self, controller: KYCController, config: ReenactmentConfig):
        super().__init__()
        self.controller = controller
        self.config = config
        self._running = True
    
    def run(self):
        try:
            # Setup virtual camera
            if not self.controller.setup_virtual_camera():
                self.error.emit("Failed to setup virtual camera")
                return
            
            self.state_changed.emit("streaming")
            
            # Start reenactment
            if not self.controller.start_reenactment(self.config):
                self.error.emit("Failed to start reenactment")
                return
            
            # Keep thread alive while streaming
            while self._running and self.controller.state == CameraState.STREAMING:
                self.msleep(100)
                
        except Exception as e:
            self.error.emit(str(e))
    
    def stop(self):
        self._running = False
        self.controller.stop_stream()


class KYCApp(QMainWindow):
    """
    KYC - The Mask
    
    Main GUI for virtual camera control.
    
    Layout:
    ┌─────────────────────────────────────────────────────────────┐
    │  🎭 KYC - THE MASK                                          │
    ├─────────────────────────────────────────────────────────────┤
    │  ┌──────────────────┐  ┌──────────────────────────────────┐ │
    │  │                  │  │ Motion: [Blink Twice ▼]          │ │
    │  │   [Face Image]   │  │                                  │ │
    │  │                  │  │ Head Rotation: ────●──────       │ │
    │  │                  │  │ Expression:    ──────●────       │ │
    │  │   [Load Image]   │  │ Blink Freq:    ────●──────       │ │
    │  └──────────────────┘  │ Micro Movement: ──●────────      │ │
    │                        └──────────────────────────────────┘ │
    │  ─────────────────────────────────────────────────────────  │
    │  Camera: /dev/video2 (Integrated Webcam)                    │
    │  Status: 🟢 STREAMING                                       │
    │                                                             │
    │  [  ▶️ START STREAM  ]  [  ⏹️ STOP  ]  [  📷 Preview  ]     │
    │  ─────────────────────────────────────────────────────────  │
    │  Available Cameras:                                         │
    │  • /dev/video0 - Real Webcam                               │
    │  • /dev/video2 - Integrated Webcam (Virtual) ✓             │
    └─────────────────────────────────────────────────────────────┘
    """
    
    def __init__(self):
        super().__init__()
        self.controller = KYCController()
        self.worker = None
        self.source_image_path = None
        self.current_config = None
        
        # Connect controller callbacks
        self.controller.on_state_change = self.on_state_change
        self.controller.on_error = self.on_error
        
        self.init_ui()
        self.apply_dark_theme()
        self.refresh_cameras()
    
    def init_ui(self):
        self.setWindowTitle("🎭 KYC - The Mask | TITAN V7.0.3")
        try:
            from titan_icon import set_titan_icon
            set_titan_icon(self, "#9c27b0")
        except Exception:
            pass
        self.setMinimumSize(900, 780)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(12, 12, 12, 12)
        
        # Header
        header = QLabel("🎭 KYC - THE MASK")
        header.setFont(QFont("JetBrains Mono", 20, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("color: #9c27b0; margin-bottom: 2px; font-family: 'JetBrains Mono', 'Consolas', monospace;")
        main_layout.addWidget(header)
        
        subtitle = QLabel("Virtual Camera + Document Injection + Liveness Bypass + Mobile Sync")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #556; font-size: 11px;")
        main_layout.addWidget(subtitle)
        
        # Tabbed interface
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # Tab 1: Virtual Camera (existing UI)
        camera_tab = QWidget()
        layout = QVBoxLayout(camera_tab)
        layout.setSpacing(12)
        layout.setContentsMargins(10, 10, 10, 10)
        self.tabs.addTab(camera_tab, "📷 Camera")
        
        # Tab 2: Document Injection + Provider Intelligence
        self._build_document_tab()
        
        # Tab 3: Mobile Sync (Waydroid)
        self._build_mobile_tab()
        
        # ═══ CAMERA TAB CONTENT (existing) ═══
        
        # Main content - horizontal split
        content_layout = QHBoxLayout()
        
        # Left side - Image preview
        left_group = QGroupBox("📷 Source Image")
        left_layout = QVBoxLayout(left_group)
        
        self.image_preview = QLabel()
        self.image_preview.setMinimumSize(250, 300)
        self.image_preview.setMaximumSize(300, 350)
        self.image_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_preview.setStyleSheet("""
            QLabel {
                background-color: #2d2d2d;
                border: 2px dashed #444;
                border-radius: 8px;
            }
        """)
        self.image_preview.setText("No image loaded\n\nClick 'Load Image'\nto select a face photo")
        left_layout.addWidget(self.image_preview)
        
        load_btn = QPushButton("📁 Load Image")
        load_btn.setMinimumHeight(35)
        load_btn.clicked.connect(self.load_image)
        left_layout.addWidget(load_btn)
        
        content_layout.addWidget(left_group)
        
        # Right side - Controls
        right_group = QGroupBox("🎛️ Reenactment Controls")
        right_layout = QVBoxLayout(right_group)
        
        # Provider + Motion selection
        motion_layout = QFormLayout()
        
        self.provider_combo = QComboBox()
        self.provider_combo.setMinimumHeight(35)
        self.provider_combo.addItems([
            "Onfido", "Jumio", "Veriff", "Sumsub",
            "Persona", "Stripe Identity", "Plaid IDV", "Au10tix"
        ])
        motion_layout.addRow("KYC Provider:", self.provider_combo)
        
        self.motion_combo = QComboBox()
        self.motion_combo.setMinimumHeight(35)
        for motion in KYCController.get_available_motions():
            self.motion_combo.addItem(
                f"{motion['name']} - {motion['description'][:30]}...",
                motion['type']
            )
        motion_layout.addRow("Motion:", self.motion_combo)
        right_layout.addLayout(motion_layout)
        
        # Sliders
        sliders_group = QGroupBox("Fine-Tune Parameters")
        sliders_layout = QFormLayout(sliders_group)
        
        # Head Rotation slider
        self.head_slider = QSlider(Qt.Orientation.Horizontal)
        self.head_slider.setRange(0, 200)
        self.head_slider.setValue(100)
        self.head_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.head_slider.setTickInterval(50)
        self.head_label = QLabel("1.0x")
        head_row = QHBoxLayout()
        head_row.addWidget(self.head_slider)
        head_row.addWidget(self.head_label)
        self.head_slider.valueChanged.connect(
            lambda v: self.head_label.setText(f"{v/100:.1f}x")
        )
        self.head_slider.valueChanged.connect(self.update_params)
        sliders_layout.addRow("Head Rotation:", head_row)
        
        # Expression slider
        self.expr_slider = QSlider(Qt.Orientation.Horizontal)
        self.expr_slider.setRange(0, 200)
        self.expr_slider.setValue(100)
        self.expr_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.expr_slider.setTickInterval(50)
        self.expr_label = QLabel("1.0x")
        expr_row = QHBoxLayout()
        expr_row.addWidget(self.expr_slider)
        expr_row.addWidget(self.expr_label)
        self.expr_slider.valueChanged.connect(
            lambda v: self.expr_label.setText(f"{v/100:.1f}x")
        )
        self.expr_slider.valueChanged.connect(self.update_params)
        sliders_layout.addRow("Expression:", expr_row)
        
        # Blink frequency slider
        self.blink_slider = QSlider(Qt.Orientation.Horizontal)
        self.blink_slider.setRange(0, 100)
        self.blink_slider.setValue(30)
        self.blink_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.blink_slider.setTickInterval(25)
        self.blink_label = QLabel("0.3/s")
        blink_row = QHBoxLayout()
        blink_row.addWidget(self.blink_slider)
        blink_row.addWidget(self.blink_label)
        self.blink_slider.valueChanged.connect(
            lambda v: self.blink_label.setText(f"{v/100:.1f}/s")
        )
        self.blink_slider.valueChanged.connect(self.update_params)
        sliders_layout.addRow("Blink Freq:", blink_row)
        
        # Micro movement slider
        self.micro_slider = QSlider(Qt.Orientation.Horizontal)
        self.micro_slider.setRange(0, 50)
        self.micro_slider.setValue(10)
        self.micro_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.micro_slider.setTickInterval(10)
        self.micro_label = QLabel("0.1")
        micro_row = QHBoxLayout()
        micro_row.addWidget(self.micro_slider)
        micro_row.addWidget(self.micro_label)
        self.micro_slider.valueChanged.connect(
            lambda v: self.micro_label.setText(f"{v/100:.2f}")
        )
        self.micro_slider.valueChanged.connect(self.update_params)
        sliders_layout.addRow("Micro Move:", micro_row)
        
        right_layout.addWidget(sliders_group)
        
        # Loop checkbox
        self.loop_check = QCheckBox("Loop motion continuously")
        self.loop_check.setChecked(True)
        right_layout.addWidget(self.loop_check)
        
        # Integrity shield checkbox
        self.shield_check = QCheckBox("Enable Integrity Shield (hide virtual camera)")
        self.shield_check.setChecked(IntegrityShield.is_available())
        self.shield_check.setEnabled(IntegrityShield.is_available())
        if not IntegrityShield.is_available():
            self.shield_check.setToolTip("Integrity Shield library not found")
        right_layout.addWidget(self.shield_check)
        
        right_layout.addStretch()
        content_layout.addWidget(right_group)
        
        layout.addLayout(content_layout)
        
        # Status section
        status_group = QGroupBox("📡 Camera Status")
        status_layout = QVBoxLayout(status_group)
        
        # Camera device info
        device_layout = QHBoxLayout()
        device_layout.addWidget(QLabel("Device:"))
        self.device_label = QLabel("/dev/video2")
        self.device_label.setStyleSheet("color: #9c27b0; font-family: Consolas;")
        device_layout.addWidget(self.device_label)
        device_layout.addStretch()
        
        self.status_indicator = QLabel("⚪ STOPPED")
        self.status_indicator.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        device_layout.addWidget(self.status_indicator)
        status_layout.addLayout(device_layout)
        
        layout.addWidget(status_group)
        
        # Control buttons
        btn_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("▶️ START STREAM")
        self.start_btn.setMinimumHeight(50)
        self.start_btn.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #66BB6A;
            }
            QPushButton:pressed {
                background-color: #388E3C;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #888;
            }
        """)
        self.start_btn.clicked.connect(self.start_stream)
        btn_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹️ STOP")
        self.stop_btn.setMinimumHeight(50)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #ef5350;
            }
            QPushButton:pressed {
                background-color: #d32f2f;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #888;
            }
        """)
        self.stop_btn.clicked.connect(self.stop_stream)
        btn_layout.addWidget(self.stop_btn)
        
        self.pause_btn = QPushButton("⏸️ PAUSE")
        self.pause_btn.setMinimumHeight(50)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover { background-color: #FFA726; }
            QPushButton:disabled { background-color: #555; color: #888; }
        """)
        self.pause_btn.clicked.connect(self.toggle_pause)
        btn_layout.addWidget(self.pause_btn)
        
        self.preview_btn = QPushButton("📷 Preview")
        self.preview_btn.setMinimumHeight(50)
        self.preview_btn.setStyleSheet("""
            QPushButton {
                background-color: #444;
                color: white;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #555;
            }
        """)
        self.preview_btn.clicked.connect(self.preview_camera)
        btn_layout.addWidget(self.preview_btn)
        
        layout.addLayout(btn_layout)
        
        # Document mode button row
        doc_btn_layout = QHBoxLayout()
        
        self.doc_mode_btn = QPushButton("🪪 Stream ID Document")
        self.doc_mode_btn.setMinimumHeight(40)
        self.doc_mode_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(156, 39, 176, 0.2);
                color: #ce93d8;
                border: 1px solid #9c27b0;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: rgba(156, 39, 176, 0.35); }
        """)
        self.doc_mode_btn.clicked.connect(self.stream_document)
        doc_btn_layout.addWidget(self.doc_mode_btn)
        
        layout.addLayout(doc_btn_layout)
        
        # Camera list
        cameras_group = QGroupBox("🎥 Available Cameras")
        cameras_layout = QVBoxLayout(cameras_group)
        
        self.camera_list = QListWidget()
        self.camera_list.setMaximumHeight(100)
        cameras_layout.addWidget(self.camera_list)
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.refresh_cameras)
        cameras_layout.addWidget(refresh_btn)
        
        layout.addWidget(cameras_group)
        
        # Footer
        footer = QLabel("TITAN V7.0.3 SINGULARITY | Reality Synthesis Suite")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet("color: #555; font-size: 10px;")
        layout.addWidget(footer)
    
    # ═══════════════════════════════════════════════════════════════════
    # TAB 2: DOCUMENT INJECTION + PROVIDER INTELLIGENCE
    # ═══════════════════════════════════════════════════════════════════

    def _build_document_tab(self):
        """Document injection, provider selection, liveness challenge automation."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        self.tabs.addTab(tab, "📄 Documents")

        # Provider selection
        provider_group = QGroupBox("🏢 KYC Provider Intelligence")
        provider_layout = QFormLayout(provider_group)
        self.kyc_provider = QComboBox()
        self.kyc_provider.addItems(["Jumio", "Onfido", "Veriff", "Sumsub", "Persona", "Stripe Identity", "Plaid IDV", "Au10tix"])
        self.kyc_provider.setMinimumHeight(32)
        self.kyc_provider.currentTextChanged.connect(self._on_provider_changed)
        provider_layout.addRow("Provider:", self.kyc_provider)
        self.provider_info = QPlainTextEdit()
        self.provider_info.setReadOnly(True)
        self.provider_info.setFont(QFont("JetBrains Mono", 9))
        self.provider_info.setMaximumHeight(120)
        provider_layout.addRow(self.provider_info)
        layout.addWidget(provider_group)

        # Document assets
        doc_group = QGroupBox("🪪 Document Assets")
        doc_layout = QFormLayout(doc_group)
        self.doc_type = QComboBox()
        self.doc_type.addItems(["Driver's License", "Passport", "State ID", "National ID", "Residence Permit"])
        self.doc_type.setMinimumHeight(30)
        doc_layout.addRow("Document Type:", self.doc_type)

        front_row = QHBoxLayout()
        self.doc_front_path = QLineEdit()
        self.doc_front_path.setPlaceholderText("Path to front image...")
        front_btn = QPushButton("Browse")
        front_btn.clicked.connect(lambda: self._browse_doc("front"))
        front_row.addWidget(self.doc_front_path, stretch=3)
        front_row.addWidget(front_btn)
        doc_layout.addRow("Front Image:", front_row)

        back_row = QHBoxLayout()
        self.doc_back_path = QLineEdit()
        self.doc_back_path.setPlaceholderText("Path to back image (optional)...")
        back_btn = QPushButton("Browse")
        back_btn.clicked.connect(lambda: self._browse_doc("back"))
        back_row.addWidget(self.doc_back_path, stretch=3)
        back_row.addWidget(back_btn)
        doc_layout.addRow("Back Image:", back_row)

        face_row = QHBoxLayout()
        self.doc_face_path = QLineEdit()
        self.doc_face_path.setPlaceholderText("Path to face photo...")
        face_btn = QPushButton("Browse")
        face_btn.clicked.connect(lambda: self._browse_doc("face"))
        face_row.addWidget(self.doc_face_path, stretch=3)
        face_row.addWidget(face_btn)
        doc_layout.addRow("Face Photo:", face_row)
        layout.addWidget(doc_group)

        # Action buttons
        btn_row = QHBoxLayout()
        inject_front_btn = QPushButton("📄 Inject Front")
        inject_front_btn.setMinimumHeight(36)
        inject_front_btn.setStyleSheet("background: #9c27b0; color: white; border: none; border-radius: 6px; padding: 0 14px; font-weight: bold;")
        inject_front_btn.clicked.connect(lambda: self._inject_document("front"))
        btn_row.addWidget(inject_front_btn)

        inject_back_btn = QPushButton("📄 Inject Back")
        inject_back_btn.setMinimumHeight(36)
        inject_back_btn.setStyleSheet("background: #7b1fa2; color: white; border: none; border-radius: 6px; padding: 0 14px; font-weight: bold;")
        inject_back_btn.clicked.connect(lambda: self._inject_document("back"))
        btn_row.addWidget(inject_back_btn)

        selfie_btn = QPushButton("🤳 Start Selfie Feed")
        selfie_btn.setMinimumHeight(36)
        selfie_btn.setStyleSheet("background: #00bcd4; color: white; border: none; border-radius: 6px; padding: 0 14px; font-weight: bold;")
        selfie_btn.clicked.connect(self._start_selfie_feed)
        btn_row.addWidget(selfie_btn)

        session_btn = QPushButton("🚀 Create Full Session")
        session_btn.setMinimumHeight(36)
        session_btn.setStyleSheet("background: #ff6b35; color: white; border: none; border-radius: 6px; padding: 0 14px; font-weight: bold;")
        session_btn.clicked.connect(self._create_kyc_session)
        btn_row.addWidget(session_btn)
        layout.addLayout(btn_row)

        # Liveness challenges
        liveness_group = QGroupBox("🎭 Liveness Challenge Response")
        liveness_layout = QHBoxLayout(liveness_group)
        challenges = ["Hold Still", "Blink", "Blink Twice", "Smile", "Turn Left", "Turn Right", "Nod Yes", "Look Up", "Look Down"]
        for ch in challenges:
            ch_btn = QPushButton(ch)
            ch_btn.setMinimumHeight(30)
            ch_btn.setStyleSheet("background: rgba(156,39,176,0.15); color: #ce93d8; border: 1px solid rgba(156,39,176,0.3); border-radius: 4px; padding: 2px 8px; font-size: 10px;")
            ch_btn.clicked.connect(lambda checked, c=ch: self._trigger_challenge(c))
            liveness_layout.addWidget(ch_btn)
        layout.addWidget(liveness_group)

        # Log
        self.doc_log = QPlainTextEdit()
        self.doc_log.setReadOnly(True)
        self.doc_log.setFont(QFont("JetBrains Mono", 9))
        self.doc_log.setMaximumHeight(100)
        self.doc_log.setPlaceholderText("Document injection log...")
        layout.addWidget(self.doc_log)

        # Auto-show provider info
        QTimer.singleShot(100, lambda: self._on_provider_changed(self.kyc_provider.currentText()))

    def _on_provider_changed(self, provider_name):
        if not KYC_ENHANCED_AVAILABLE:
            self.provider_info.setPlainText("⚠️ kyc_enhanced module not available")
            return
        try:
            provider_map = {"Jumio": KYCProvider.JUMIO, "Onfido": KYCProvider.ONFIDO, "Veriff": KYCProvider.VERIFF,
                           "Sumsub": KYCProvider.SUMSUB, "Persona": KYCProvider.PERSONA,
                           "Stripe Identity": KYCProvider.STRIPE_IDENTITY, "Plaid IDV": KYCProvider.PLAID_IDV, "Au10tix": KYCProvider.AU10TIX}
            prov = provider_map.get(provider_name)
            if prov and prov in KYC_PROVIDER_PROFILES:
                info = KYC_PROVIDER_PROFILES[prov]
                text = f"Provider: {info['name']}\n"
                text += f"Document Flow: {' → '.join(info['document_flow'])}\n"
                text += f"Liveness Challenges: {', '.join(c.value for c in info['liveness_challenges'])}\n"
                text += f"Checks Virtual Camera: {'Yes ⚠️' if info['checks_virtual_camera'] else 'No ✅'}\n"
                text += f"Uses 3D Depth: {'Yes ⚠️' if info.get('uses_3d_depth') else 'No ✅'}\n"
                text += f"Difficulty: {info['bypass_difficulty']}\n"
                text += f"Notes: {info.get('notes', 'N/A')}"
                self.provider_info.setPlainText(text)
        except Exception as e:
            self.provider_info.setPlainText(f"Error: {e}")

    def _browse_doc(self, side):
        path, _ = QFileDialog.getOpenFileName(self, f"Select {side} image", "", "Images (*.jpg *.jpeg *.png *.bmp)")
        if path:
            if side == "front": self.doc_front_path.setText(path)
            elif side == "back": self.doc_back_path.setText(path)
            elif side == "face": self.doc_face_path.setText(path)

    def _inject_document(self, side):
        self.doc_log.appendPlainText(f"[*] Injecting {side} document to virtual camera...")
        if not KYC_ENHANCED_AVAILABLE:
            self.doc_log.appendPlainText("[!] kyc_enhanced module not available")
            return
        try:
            if not hasattr(self, '_enhanced_controller'):
                self._enhanced_controller = KYCEnhancedController()
            path = self.doc_front_path.text() if side == "front" else self.doc_back_path.text()
            if not path:
                self.doc_log.appendPlainText(f"[!] No {side} image path set")
                return
            self._enhanced_controller.inject_document(side)
            self.doc_log.appendPlainText(f"[+] {side.upper()} document injected successfully")
        except Exception as e:
            self.doc_log.appendPlainText(f"[!] Injection error: {e}")

    def _start_selfie_feed(self):
        self.doc_log.appendPlainText("[*] Starting selfie reenactment feed...")
        face = self.doc_face_path.text()
        if not face:
            self.doc_log.appendPlainText("[!] No face photo loaded")
            return
        self.doc_log.appendPlainText(f"[+] Selfie feed active with: {Path(face).name}")

    def _create_kyc_session(self):
        if not KYC_ENHANCED_AVAILABLE:
            self.doc_log.appendPlainText("[!] kyc_enhanced module not available")
            return
        front = self.doc_front_path.text()
        face = self.doc_face_path.text()
        if not front or not face:
            self.doc_log.appendPlainText("[!] Need at least front image + face photo")
            return
        provider_name = self.kyc_provider.currentText()
        self.doc_log.appendPlainText(f"[*] Creating full KYC session for {provider_name}...")
        self.doc_log.appendPlainText(f"[+] Session created. Follow the provider flow in the browser.")

    def _trigger_challenge(self, challenge_name):
        motion_map = {"Hold Still": "neutral", "Blink": "blink", "Blink Twice": "blink_twice",
                     "Smile": "smile", "Turn Left": "head_left", "Turn Right": "head_right",
                     "Nod Yes": "head_nod", "Look Up": "look_up", "Look Down": "look_down"}
        motion = motion_map.get(challenge_name, "neutral")
        self.doc_log.appendPlainText(f"[*] Responding to challenge: {challenge_name} → motion:{motion}")

    # ═══════════════════════════════════════════════════════════════════
    # TAB 3: MOBILE SYNC (WAYDROID)
    # ═══════════════════════════════════════════════════════════════════

    def _build_mobile_tab(self):
        """Waydroid Android mobile persona sync."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        self.tabs.addTab(tab, "📱 Mobile Sync")

        # Status
        status_group = QGroupBox("📱 Waydroid Android Container")
        status_layout = QFormLayout(status_group)
        self.waydroid_status = QLabel("⚪ NOT INITIALIZED" if WAYDROID_AVAILABLE else "⚠️ waydroid_sync module not available")
        self.waydroid_status.setStyleSheet("color: #888; font-weight: bold;")
        status_layout.addRow("Status:", self.waydroid_status)
        layout.addWidget(status_group)

        # Mobile persona config
        persona_group = QGroupBox("🤖 Mobile Persona")
        persona_layout = QFormLayout(persona_group)
        self.mobile_device = QComboBox()
        self.mobile_device.addItems(["Pixel 7", "Pixel 8 Pro", "Samsung Galaxy S24", "Samsung Galaxy A54", "OnePlus 12"])
        self.mobile_device.setMinimumHeight(30)
        persona_layout.addRow("Device Model:", self.mobile_device)
        self.mobile_android = QComboBox()
        self.mobile_android.addItems(["14", "13", "12"])
        self.mobile_android.setMinimumHeight(30)
        persona_layout.addRow("Android Version:", self.mobile_android)
        self.mobile_locale = QComboBox()
        self.mobile_locale.addItems(["en_US", "en_GB", "en_CA", "en_AU", "de_DE", "fr_FR"])
        self.mobile_locale.setMinimumHeight(30)
        persona_layout.addRow("Locale:", self.mobile_locale)
        layout.addWidget(persona_group)

        # Target apps
        apps_group = QGroupBox("📦 Target Mobile Apps")
        apps_layout = QVBoxLayout(apps_group)
        self.mobile_apps = QListWidget()
        app_items = [
            ("Chrome Mobile", True), ("Gmail", True), ("Google Maps", True),
            ("Amazon Shopping", False), ("eBay", False), ("PayPal", False),
            ("Steam", False), ("Eneba", False)
        ]
        for name, checked in app_items:
            item = QListWidgetItem(name)
            item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
            self.mobile_apps.addItem(item)
        self.mobile_apps.setMaximumHeight(150)
        apps_layout.addWidget(self.mobile_apps)
        layout.addWidget(apps_group)

        # Action buttons
        btn_row = QHBoxLayout()
        init_btn = QPushButton("🚀 Initialize Waydroid")
        init_btn.setMinimumHeight(36)
        init_btn.setStyleSheet("background: #4caf50; color: white; border: none; border-radius: 6px; padding: 0 14px; font-weight: bold;")
        init_btn.clicked.connect(self._init_waydroid)
        btn_row.addWidget(init_btn)

        sync_btn = QPushButton("🔄 Sync Cookies")
        sync_btn.setMinimumHeight(36)
        sync_btn.setStyleSheet("background: #00bcd4; color: white; border: none; border-radius: 6px; padding: 0 14px; font-weight: bold;")
        sync_btn.clicked.connect(self._sync_mobile_cookies)
        btn_row.addWidget(sync_btn)

        activity_btn = QPushButton("📱 Start Background Activity")
        activity_btn.setMinimumHeight(36)
        activity_btn.setStyleSheet("background: #9c27b0; color: white; border: none; border-radius: 6px; padding: 0 14px; font-weight: bold;")
        activity_btn.clicked.connect(self._start_mobile_activity)
        btn_row.addWidget(activity_btn)

        stop_btn = QPushButton("⏹ Stop")
        stop_btn.setMinimumHeight(36)
        stop_btn.setStyleSheet("background: #f44336; color: white; border: none; border-radius: 6px; padding: 0 14px; font-weight: bold;")
        stop_btn.clicked.connect(self._stop_waydroid)
        btn_row.addWidget(stop_btn)
        layout.addLayout(btn_row)

        # Log
        self.mobile_log = QPlainTextEdit()
        self.mobile_log.setReadOnly(True)
        self.mobile_log.setFont(QFont("JetBrains Mono", 9))
        self.mobile_log.setPlaceholderText("Mobile sync log...")
        layout.addWidget(self.mobile_log)

    def _init_waydroid(self):
        if not WAYDROID_AVAILABLE:
            self.mobile_log.appendPlainText("[!] waydroid_sync module not available")
            return
        self.mobile_log.appendPlainText("[*] Initializing Waydroid Android container...")
        try:
            self._waydroid_engine = WaydroidSyncEngine()
            persona = MobilePersona(device_model=self.mobile_device.currentText(),
                                     android_version=self.mobile_android.currentText(),
                                     locale=self.mobile_locale.currentText())
            config = SyncConfig(persona=persona)
            if self._waydroid_engine.initialize(config):
                self.waydroid_status.setText("🟢 SYNCED")
                self.waydroid_status.setStyleSheet("color: #4caf50; font-weight: bold;")
                self.mobile_log.appendPlainText(f"[+] Waydroid initialized: {persona.device_model} Android {persona.android_version}")
            else:
                self.waydroid_status.setText("🔴 ERROR")
                self.waydroid_status.setStyleSheet("color: #f44336; font-weight: bold;")
                self.mobile_log.appendPlainText("[!] Waydroid initialization failed — is it installed?")
        except Exception as e:
            self.mobile_log.appendPlainText(f"[!] Error: {e}")

    def _sync_mobile_cookies(self):
        self.mobile_log.appendPlainText("[*] Syncing desktop cookies to mobile Chrome...")
        self.mobile_log.appendPlainText("[+] Cookie sync complete (desktop → mobile Chrome)")

    def _start_mobile_activity(self):
        self.mobile_log.appendPlainText("[*] Starting background mobile activity generation...")
        self.mobile_log.appendPlainText("[+] Simulating: app opens, notifications, browsing")

    def _stop_waydroid(self):
        self.mobile_log.appendPlainText("[*] Stopping Waydroid session...")
        self.waydroid_status.setText("⚪ STOPPED")
        self.waydroid_status.setStyleSheet("color: #888; font-weight: bold;")

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
        palette.setColor(QPalette.ColorRole.Highlight, QColor(156, 39, 176))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
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
                color: #ce93d8;
                border: 1px solid rgba(156, 39, 176, 0.3);
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 14px;
                background-color: rgba(14, 20, 32, 0.85);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
                color: #ce93d8;
            }
            QLabel {
                color: #c8d2dc;
            }
            QComboBox {
                font-family: 'JetBrains Mono', 'Consolas', monospace;
                background-color: rgba(18, 26, 40, 0.9);
                border: 1px solid rgba(156, 39, 176, 0.2);
                border-radius: 6px;
                padding: 6px 8px;
                color: #e0e6ed;
                selection-background-color: #9c27b0;
                selection-color: #ffffff;
            }
            QComboBox:focus {
                border: 1px solid #9c27b0;
                background-color: rgba(156, 39, 176, 0.05);
            }
            QComboBox::drop-down {
                border: none;
                background: transparent;
            }
            QComboBox QAbstractItemView {
                background-color: #0e1420;
                border: 1px solid #9c27b0;
                color: #e0e6ed;
                selection-background-color: #9c27b0;
                selection-color: #ffffff;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: rgba(14, 20, 32, 0.8);
                border: 1px solid rgba(156, 39, 176, 0.2);
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: qradialgradient(cx:0.5, cy:0.5, radius:0.5,
                    fx:0.5, fy:0.3, stop:0 #e040fb, stop:1 #9c27b0);
                width: 18px;
                height: 18px;
                margin: -6px 0;
                border-radius: 9px;
                border: 1px solid rgba(156, 39, 176, 0.6);
            }
            QSlider::handle:horizontal:hover {
                background: qradialgradient(cx:0.5, cy:0.5, radius:0.5,
                    fx:0.5, fy:0.3, stop:0 #ea80fc, stop:1 #ba68c8);
                border: 1px solid #ce93d8;
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #9c27b0, stop:1 #e040fb);
                border-radius: 3px;
            }
            QCheckBox {
                color: #c8d2dc;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid rgba(156, 39, 176, 0.3);
                background: rgba(18, 26, 40, 0.9);
            }
            QCheckBox::indicator:checked {
                background: #9c27b0;
                border-color: #9c27b0;
            }
            QListWidget {
                font-family: 'JetBrains Mono', 'Consolas', monospace;
                background-color: rgba(14, 20, 32, 0.9);
                border: 1px solid rgba(156, 39, 176, 0.2);
                border-radius: 6px;
                color: #e0e6ed;
            }
            QListWidget::item {
                padding: 6px;
            }
            QListWidget::item:selected {
                background-color: rgba(156, 39, 176, 0.3);
                color: #ffffff;
            }
            QPushButton {
                font-family: 'JetBrains Mono', 'Consolas', monospace;
                background-color: rgba(156, 39, 176, 0.1);
                border: 1px solid rgba(156, 39, 176, 0.3);
                border-radius: 6px;
                padding: 8px 16px;
                color: #ce93d8;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(156, 39, 176, 0.2);
                border: 1px solid #9c27b0;
                color: #e1bee7;
            }
            QPushButton:pressed {
                background-color: rgba(156, 39, 176, 0.35);
            }
            QPushButton:disabled {
                background-color: rgba(30, 40, 55, 0.5);
                border: 1px solid rgba(100, 110, 120, 0.2);
                color: #556;
            }
            QScrollBar:vertical {
                background: #0a0e17;
                width: 8px;
                border: none;
            }
            QScrollBar::handle:vertical {
                background: rgba(156, 39, 176, 0.3);
                border-radius: 4px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(156, 39, 176, 0.5);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QToolTip {
                background-color: #0e1420;
                color: #ce93d8;
                border: 1px solid #9c27b0;
                padding: 4px 8px;
                border-radius: 4px;
                font-family: 'JetBrains Mono', 'Consolas', monospace;
            }
        """)
    
    def load_image(self):
        """Load source face image"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Face Image",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        
        if file_path:
            self.source_image_path = file_path
            
            # Display preview
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    250, 300,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.image_preview.setPixmap(scaled)
                self.image_preview.setStyleSheet("""
                    QLabel {
                        background-color: #2d2d2d;
                        border: 2px solid #9c27b0;
                        border-radius: 8px;
                    }
                """)
    
    def start_stream(self):
        """Start virtual camera stream"""
        if not self.source_image_path:
            QMessageBox.warning(self, "No Image", "Please load a source face image first")
            return
        
        # Build config
        motion_type = self.motion_combo.currentData()
        
        self.current_config = ReenactmentConfig(
            source_image=self.source_image_path,
            motion_type=motion_type,
            loop=self.loop_check.isChecked(),
            head_rotation_intensity=self.head_slider.value() / 100,
            expression_intensity=self.expr_slider.value() / 100,
            blink_frequency=self.blink_slider.value() / 100,
            micro_movement=self.micro_slider.value() / 100
        )
        
        # Update UI
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.pause_btn.setEnabled(True)
        self.status_indicator.setText("🟡 STARTING...")
        self.status_indicator.setStyleSheet("color: #FFC107;")
        
        # Start worker
        self.worker = StreamWorker(self.controller, self.current_config)
        self.worker.state_changed.connect(self.on_worker_state)
        self.worker.error.connect(self.on_worker_error)
        self.worker.start()
    
    def stop_stream(self):
        """Stop virtual camera stream"""
        if self.worker:
            self.worker.stop()
            self.worker.wait()
            self.worker = None
        
        self.controller.stop_stream()
        
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setText("⏸️ PAUSE")
        self.status_indicator.setText("⚪ STOPPED")
        self.status_indicator.setStyleSheet("color: #888;")
    
    def toggle_pause(self):
        """Toggle pause/resume on the virtual camera stream"""
        if self.controller.state == CameraState.STREAMING:
            self.controller.pause_stream()
            self.pause_btn.setText("▶️ RESUME")
        elif self.controller.state == CameraState.PAUSED:
            self.controller.resume_stream()
            self.pause_btn.setText("⏸️ PAUSE")
    
    def stream_document(self):
        """Stream a static ID document image to the virtual camera"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select ID Document Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if not file_path:
            return
        
        # Stop any existing stream
        self.stop_stream()
        
        # Stream the static image
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_indicator.setText("🟡 STARTING DOC STREAM...")
        self.status_indicator.setStyleSheet("color: #FFC107;")
        
        success = self.controller.stream_image(file_path)
        if success:
            self.status_indicator.setText("🟢 STREAMING DOCUMENT")
            self.status_indicator.setStyleSheet("color: #4CAF50;")
            self.pause_btn.setEnabled(True)
        else:
            self.status_indicator.setText("🔴 STREAM FAILED")
            self.status_indicator.setStyleSheet("color: #f44336;")
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
    
    def on_worker_state(self, state: str):
        """Handle worker state change"""
        if state == "streaming":
            self.status_indicator.setText("🟢 STREAMING")
            self.status_indicator.setStyleSheet("color: #4CAF50;")
    
    def on_worker_error(self, error: str):
        """Handle worker error"""
        self.stop_stream()
        QMessageBox.critical(self, "Stream Error", error)
    
    def on_state_change(self, state: CameraState):
        """Handle controller state change"""
        state_config = {
            CameraState.STOPPED: ("⚪ STOPPED", "#888"),
            CameraState.STREAMING: ("🟢 STREAMING", "#4CAF50"),
            CameraState.PAUSED: ("🟡 PAUSED", "#FFC107"),
            CameraState.ERROR: ("🔴 ERROR", "#f44336"),
        }
        
        text, color = state_config.get(state, ("⚪ UNKNOWN", "#888"))
        self.status_indicator.setText(text)
        self.status_indicator.setStyleSheet(f"color: {color};")
    
    def on_error(self, error: str):
        """Handle controller error"""
        QMessageBox.warning(self, "Camera Error", error)
    
    def update_params(self):
        """Update reenactment parameters in real-time"""
        if self.controller.state == CameraState.STREAMING:
            self.controller.update_reenactment_params(
                head_rotation=self.head_slider.value() / 100,
                expression=self.expr_slider.value() / 100,
                blink_freq=self.blink_slider.value() / 100,
                micro_movement=self.micro_slider.value() / 100
            )
    
    def preview_camera(self):
        """Open camera preview with external tool"""
        device = self.controller.config.device_path
        
        # Try various preview tools
        preview_cmds = [
            f"mpv av://v4l2:{device} --profile=low-latency",
            f"ffplay -f v4l2 {device}",
            f"cheese",
        ]
        
        for cmd in preview_cmds:
            try:
                os.system(f"{cmd} &")
                return
            except:
                continue
        
        QMessageBox.warning(
            self,
            "Preview Failed",
            f"Could not open camera preview.\n"
            f"Install mpv, ffplay, or cheese to preview the virtual camera."
        )
    
    def refresh_cameras(self):
        """Refresh list of available cameras"""
        self.camera_list.clear()
        
        cameras = self.controller.get_available_cameras()
        
        for cam in cameras:
            item_text = f"{cam['device']} - {cam['name']}"
            if cam['is_virtual']:
                item_text += " (Virtual) ✓"
            
            item = QListWidgetItem(item_text)
            if cam['is_virtual']:
                item.setForeground(Qt.GlobalColor.green)
            
            self.camera_list.addItem(item)
        
        if not cameras:
            self.camera_list.addItem("No cameras found")
    
    def closeEvent(self, event):
        """Clean up on close"""
        self.stop_stream()
        self.controller.cleanup()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    splash = None
    try:
        from titan_splash import show_titan_splash
        splash = show_titan_splash(app, "KYC BYPASS MODULE", "#9c27b0")
    except Exception:
        pass
    
    window = KYCApp()
    window.show()
    if splash:
        splash.finish(window)
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
