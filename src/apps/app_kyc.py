#!/usr/bin/env python3
"""
TITAN V8.2 SINGULARITY — Verification Compliance Module
Virtual Camera Controller GUI

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
import json
import subprocess
import shutil
from pathlib import Path
from datetime import datetime

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

try:
    from kyc_core import (
        KYCController, ReenactmentConfig, VirtualCameraConfig,
        CameraState, MotionType, IntegrityShield
    )
    KYC_CORE_AVAILABLE = True
except ImportError:
    KYCController = ReenactmentConfig = VirtualCameraConfig = None
    CameraState = MotionType = IntegrityShield = None
    KYC_CORE_AVAILABLE = False

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

# Voice engine for speech KYC challenges
try:
    from kyc_voice_engine import KYCVoiceEngine, SpeechVideoConfig, VoiceProfile, VoiceGender
    VOICE_AVAILABLE = True
except ImportError:
    VOICE_AVAILABLE = False

# Cognitive core for behavioral modeling
try:
    from cognitive_core import TitanCognitiveCore as CognitiveEngine
    BehaviorProfile = None
    COGNITIVE_AVAILABLE = True
except ImportError:
    COGNITIVE_AVAILABLE = False

# V7.5 AI Intelligence Engine
try:
    from ai_intelligence_engine import get_ai_status, is_ai_available, audit_profile
    from ghost_motor_v6 import get_forter_safe_params
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False

# V8.2: Cross-app session state
try:
    from titan_session import get_session, save_session
    _SESSION_OK = True
except ImportError:
    _SESSION_OK = False
    def get_session(): return {}
    def save_session(d): return False

# V8.1 Deep Identity Verification (formerly orphaned)
try:
    from verify_deep_identity import DeepIdentityOrchestrator, IdentityConsistencyChecker
    DEEP_IDENTITY_AVAILABLE = True
except ImportError:
    DEEP_IDENTITY_AVAILABLE = False

# V8.1 ToF Depth Synthesis for 3D liveness bypass (formerly orphaned)
try:
    from tof_depth_synthesis import (
        FaceDepthGenerator, DepthQuality, SensorType,
        FacialLandmarks, get_depth_generator, generate_depth_sequence,
    )
    TOF_DEPTH_AVAILABLE = True
except ImportError:
    TOF_DEPTH_AVAILABLE = False


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
        self.setWindowTitle("TITAN V8.2 — KYC Studio")
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
        header = QLabel("VERIFICATION COMPLIANCE MODULE")
        header.setFont(QFont("Inter", 20, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("color: #9c27b0; margin-bottom: 2px;")
        main_layout.addWidget(header)
        
        subtitle = QLabel("Virtual Camera + Document Injection + Liveness Response + Mobile Sync")
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
        
        # Tab 4: Voice + Video Recording (speech KYC challenges)
        self._build_voice_tab()
        
        # Tab 5: Android Image Management (from CascadeProjects reference)
        self._build_android_tab()
        
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
        self.device_label.setStyleSheet("color: #3A75C4; font-family: Consolas;")
        device_layout.addWidget(self.device_label)
        device_layout.addStretch()
        
        self.status_indicator = QLabel("⚪ STOPPED")
        self.status_indicator.setFont(QFont("Inter", 12, QFont.Weight.Bold))
        device_layout.addWidget(self.status_indicator)
        status_layout.addLayout(device_layout)
        
        layout.addWidget(status_group)
        
        # Control buttons
        btn_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("▶️ START STREAM")
        self.start_btn.setMinimumHeight(50)
        self.start_btn.setFont(QFont("Inter", 12, QFont.Weight.Bold))
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
                background-color: rgba(58, 117, 196, 0.2);
                color: #4A8AD8;
                border: 1px solid #3A75C4;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: rgba(58, 117, 196, 0.35); }
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
        footer = QLabel("TITAN V8.0 MAXIMUM | Verification Compliance")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet("color: #64748B; font-size: 10px;")
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
        inject_front_btn.setStyleSheet("background: #3A75C4; color: white; border: none; border-radius: 6px; padding: 0 14px; font-weight: bold;")
        inject_front_btn.clicked.connect(lambda: self._inject_document("front"))
        btn_row.addWidget(inject_front_btn)

        inject_back_btn = QPushButton("📄 Inject Back")
        inject_back_btn.setMinimumHeight(36)
        inject_back_btn.setStyleSheet("background: #2D5F9E; color: white; border: none; border-radius: 6px; padding: 0 14px; font-weight: bold;")
        inject_back_btn.clicked.connect(lambda: self._inject_document("back"))
        btn_row.addWidget(inject_back_btn)

        selfie_btn = QPushButton("🤳 Start Selfie Feed")
        selfie_btn.setMinimumHeight(36)
        selfie_btn.setStyleSheet("background: #3A75C4; color: white; border: none; border-radius: 6px; padding: 0 14px; font-weight: bold;")
        selfie_btn.clicked.connect(self._start_selfie_feed)
        btn_row.addWidget(selfie_btn)

        session_btn = QPushButton("🚀 Create Full Session")
        session_btn.setMinimumHeight(36)
        session_btn.setStyleSheet("background: #E6A817; color: white; border: none; border-radius: 6px; padding: 0 14px; font-weight: bold;")
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
            ch_btn.setStyleSheet("background: rgba(58,117,196,0.15); color: #4A8AD8; border: 1px solid rgba(58,117,196,0.3); border-radius: 4px; padding: 2px 8px; font-size: 10px;")
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
        sync_btn.setStyleSheet("background: #3A75C4; color: white; border: none; border-radius: 6px; padding: 0 14px; font-weight: bold;")
        sync_btn.clicked.connect(self._sync_mobile_cookies)
        btn_row.addWidget(sync_btn)

        activity_btn = QPushButton("📱 Start Background Activity")
        activity_btn.setMinimumHeight(36)
        activity_btn.setStyleSheet("background: #3A75C4; color: white; border: none; border-radius: 6px; padding: 0 14px; font-weight: bold;")
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
        try:
            cookie_src = Path("/opt/titan/profiles")
            if cookie_src.exists():
                profiles = sorted(cookie_src.iterdir(), reverse=True)
                if profiles:
                    latest = profiles[0] / "Default" / "cookies.json"
                    if latest.exists():
                        dest = Path("/tmp/titan_mobile_cookies.json")
                        shutil.copy2(str(latest), str(dest))
                        result = subprocess.run(
                            ["waydroid", "shell", "--", "am", "broadcast",
                             "-a", "com.titan.COOKIE_SYNC", "-e", "path", str(dest)],
                            capture_output=True, text=True, timeout=15
                        )
                        self.mobile_log.appendPlainText(f"[+] Cookie sync complete — {latest.name}")
                        return
            self.mobile_log.appendPlainText("[!] No profiles found to sync cookies from")
        except FileNotFoundError:
            self.mobile_log.appendPlainText("[!] Waydroid not installed — cannot sync cookies")
        except subprocess.TimeoutExpired:
            self.mobile_log.appendPlainText("[!] Waydroid command timed out")
        except Exception as e:
            self.mobile_log.appendPlainText(f"[!] Error: {e}")

    def _start_mobile_activity(self):
        self.mobile_log.appendPlainText("[*] Starting background mobile activity generation...")
        try:
            apps = []
            for i in range(self.mobile_apps.count()):
                item = self.mobile_apps.item(i)
                if item.checkState() == Qt.CheckState.Checked:
                    apps.append(item.text())
            pkg_map = {
                "Chrome Mobile": "com.android.chrome",
                "Gmail": "com.google.android.gm",
                "Google Maps": "com.google.android.apps.maps",
                "Amazon Shopping": "com.amazon.mShop.android.shopping",
                "eBay": "com.ebay.mobile",
                "PayPal": "com.paypal.android.p2pmobile",
                "Steam": "com.valvesoftware.android.steam.community",
                "Eneba": "com.eneba.app",
            }
            for app_name in apps[:3]:
                pkg = pkg_map.get(app_name, "")
                if pkg:
                    subprocess.Popen(
                        ["waydroid", "shell", "--", "am", "start", "-n", f"{pkg}/.MainActivity"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )
                    self.mobile_log.appendPlainText(f"[+] Launched {app_name} ({pkg})")
            self.mobile_log.appendPlainText("[+] Background activity started")
        except FileNotFoundError:
            self.mobile_log.appendPlainText("[!] Waydroid not installed")
        except Exception as e:
            self.mobile_log.appendPlainText(f"[!] Error: {e}")

    def _stop_waydroid(self):
        self.mobile_log.appendPlainText("[*] Stopping Waydroid session...")
        try:
            subprocess.run(["waydroid", "session", "stop"], capture_output=True, timeout=15)
            self.mobile_log.appendPlainText("[+] Waydroid session stopped")
        except FileNotFoundError:
            self.mobile_log.appendPlainText("[!] Waydroid not installed")
        except Exception as e:
            self.mobile_log.appendPlainText(f"[!] Error: {e}")
        self.waydroid_status.setText("⚪ STOPPED")
        self.waydroid_status.setStyleSheet("color: #888; font-weight: bold;")

    # ═══════════════════════════════════════════════════════════════════
    # TAB 5: ANDROID IMAGE MANAGEMENT (from CascadeProjects reference)
    # ═══════════════════════════════════════════════════════════════════

    _DEVICE_PROFILES = {
        "Pixel 9 Pro": {
            "ro.product.model": "Pixel 9 Pro", "ro.product.brand": "google",
            "ro.product.manufacturer": "Google", "ro.hardware": "caiman",
            "ro.build.tags": "release-keys", "ro.build.type": "user",
            "ro.boot.verifiedbootstate": "green", "ro.boot.flash.locked": "1",
            "ro.secure": "1", "ro.debuggable": "0", "ro.kernel.qemu": "0",
            "ro.com.google.gmsversion": "android_16_202601",
        },
        "Samsung Galaxy S24 Ultra": {
            "ro.product.model": "SM-S928B", "ro.product.brand": "samsung",
            "ro.product.manufacturer": "Samsung", "ro.hardware": "s5e9945",
            "ro.build.tags": "release-keys", "ro.build.type": "user",
            "ro.boot.verifiedbootstate": "green", "ro.boot.flash.locked": "1",
            "ro.secure": "1", "ro.debuggable": "0", "ro.kernel.qemu": "0",
        },
        "Samsung Galaxy S21 Ultra 5G": {
            "ro.product.model": "SM-G998U1", "ro.product.brand": "samsung",
            "ro.product.manufacturer": "Samsung", "ro.hardware": "exynos2100",
            "ro.build.tags": "release-keys", "ro.build.type": "user",
            "ro.boot.verifiedbootstate": "green", "ro.secure": "1",
        },
        "OnePlus 12": {
            "ro.product.model": "CPH2583", "ro.product.brand": "OnePlus",
            "ro.product.manufacturer": "OnePlus", "ro.hardware": "qcom",
            "ro.build.tags": "release-keys", "ro.build.type": "user",
            "ro.secure": "1", "ro.debuggable": "0",
        },
    }

    def _build_android_tab(self):
        """Android Image Management — system properties, device profiles, Redroid cloud deployment, keybox."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        self.tabs.addTab(tab, "📱 Android Image")

        # Device Profile Selector
        profile_grp = QGroupBox("🔧 Device Identity Profile")
        pg_layout = QVBoxLayout(profile_grp)

        profile_row = QHBoxLayout()
        profile_row.addWidget(QLabel("Device:"))
        self.android_profile_combo = QComboBox()
        self.android_profile_combo.addItems(list(self._DEVICE_PROFILES.keys()))
        self.android_profile_combo.setMinimumWidth(220)
        profile_row.addWidget(self.android_profile_combo)

        load_profile_btn = QPushButton("Load Profile")
        load_profile_btn.setStyleSheet("background: #3A75C4; color: white; padding: 8px 16px; border-radius: 6px; font-weight: bold;")
        load_profile_btn.clicked.connect(self._load_device_profile)
        profile_row.addWidget(load_profile_btn)

        apply_waydroid_btn = QPushButton("Apply to Waydroid")
        apply_waydroid_btn.setStyleSheet("background: #4caf50; color: white; padding: 8px 16px; border-radius: 6px; font-weight: bold;")
        apply_waydroid_btn.clicked.connect(self._apply_profile_to_waydroid)
        profile_row.addWidget(apply_waydroid_btn)

        profile_row.addStretch()
        pg_layout.addLayout(profile_row)

        # System Properties Editor
        self.sys_props_edit = QPlainTextEdit()
        self.sys_props_edit.setFont(QFont("JetBrains Mono", 9))
        self.sys_props_edit.setPlaceholderText("# System properties (build.prop format)\n# key=value per line\nro.product.model=Pixel 9 Pro\nro.product.brand=google\n...")
        self.sys_props_edit.setMaximumHeight(200)
        pg_layout.addWidget(self.sys_props_edit)

        layout.addWidget(profile_grp)

        # Redroid Cloud Android
        redroid_grp = QGroupBox("☁️ Cloud Android (Redroid/Docker)")
        rg_layout = QVBoxLayout(redroid_grp)

        info_label = QLabel("Deploy a headless Android container on the VPS via Docker + Redroid.")
        info_label.setStyleSheet("color: #8892b0; font-size: 11px;")
        info_label.setWordWrap(True)
        rg_layout.addWidget(info_label)

        redroid_row = QHBoxLayout()
        self.redroid_image = QComboBox()
        self.redroid_image.addItems([
            "redroid/redroid:12.0.0-latest",
            "redroid/redroid:13.0.0-latest",
            "redroid/redroid:14.0.0-latest",
        ])
        redroid_row.addWidget(QLabel("Image:"))
        redroid_row.addWidget(self.redroid_image)

        deploy_btn = QPushButton("Deploy Container")
        deploy_btn.setStyleSheet("background: #4caf50; color: white; padding: 8px 16px; border-radius: 6px; font-weight: bold;")
        deploy_btn.clicked.connect(self._deploy_redroid)
        redroid_row.addWidget(deploy_btn)

        status_btn = QPushButton("Check Status")
        status_btn.setStyleSheet("background: #3A75C4; color: white; padding: 8px 14px; border-radius: 6px;")
        status_btn.clicked.connect(self._check_redroid_status)
        redroid_row.addWidget(status_btn)

        stop_btn = QPushButton("Stop Container")
        stop_btn.setStyleSheet("background: #f44336; color: white; padding: 8px 14px; border-radius: 6px;")
        stop_btn.clicked.connect(self._stop_redroid)
        redroid_row.addWidget(stop_btn)
        rg_layout.addLayout(redroid_row)

        layout.addWidget(redroid_grp)

        # Keybox Management
        keybox_grp = QGroupBox("🔐 Keybox & Attestation")
        kg_layout = QVBoxLayout(keybox_grp)

        kb_info = QLabel("Manage keybox.xml for hardware attestation spoofing (MEETS_STRONG_INTEGRITY).")
        kb_info.setStyleSheet("color: #8892b0; font-size: 11px;")
        kb_info.setWordWrap(True)
        kg_layout.addWidget(kb_info)

        kb_row = QHBoxLayout()
        self.keybox_path = QLineEdit()
        self.keybox_path.setPlaceholderText("Path to keybox.xml (from rooted Pixel device)")
        kb_row.addWidget(self.keybox_path)
        kb_browse = QPushButton("Browse")
        kb_browse.clicked.connect(lambda: self._browse_file(self.keybox_path, "Select Keybox", "XML (*.xml)"))
        kb_row.addWidget(kb_browse)
        kb_encrypt = QPushButton("Encrypt & Install")
        kb_encrypt.setStyleSheet("background: #9c27b0; color: white; padding: 8px 14px; border-radius: 6px; font-weight: bold;")
        kb_encrypt.clicked.connect(self._encrypt_keybox)
        kb_row.addWidget(kb_encrypt)
        kg_layout.addLayout(kb_row)

        self.keybox_status = QLabel("No keybox loaded")
        self.keybox_status.setStyleSheet("color: #888; font-size: 11px;")
        kg_layout.addWidget(self.keybox_status)

        layout.addWidget(keybox_grp)

        # Android Log
        self.android_log = QPlainTextEdit()
        self.android_log.setReadOnly(True)
        self.android_log.setFont(QFont("JetBrains Mono", 9))
        self.android_log.setPlaceholderText("Android image management log...")
        self.android_log.setMaximumHeight(180)
        layout.addWidget(self.android_log)

        layout.addStretch()

    def _browse_file(self, line_edit, title, file_filter):
        path, _ = QFileDialog.getOpenFileName(self, title, "", file_filter)
        if path:
            line_edit.setText(path)

    def _load_device_profile(self):
        profile_name = self.android_profile_combo.currentText()
        props = self._DEVICE_PROFILES.get(profile_name, {})
        lines = [f"# Device Profile: {profile_name}", f"# Generated: {datetime.now().isoformat()}", ""]
        for k, v in props.items():
            lines.append(f"{k}={v}")
        self.sys_props_edit.setPlainText("\n".join(lines))
        self.android_log.appendPlainText(f"[+] Loaded device profile: {profile_name} ({len(props)} properties)")

    def _apply_profile_to_waydroid(self):
        text = self.sys_props_edit.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Android", "Load a device profile first")
            return
        props = {}
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                props[k.strip()] = v.strip()

        self.android_log.appendPlainText(f"[*] Applying {len(props)} properties to Waydroid...")
        applied = 0
        for k, v in props.items():
            try:
                result = subprocess.run(
                    ["waydroid", "prop", "set", k, v],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    applied += 1
                else:
                    self.android_log.appendPlainText(f"[!] Failed: {k} — {result.stderr.strip()[:80]}")
            except FileNotFoundError:
                self.android_log.appendPlainText("[!] Waydroid not installed")
                return
            except Exception as e:
                self.android_log.appendPlainText(f"[!] Error setting {k}: {e}")

        self.android_log.appendPlainText(f"[+] Applied {applied}/{len(props)} properties")
        if applied > 0:
            self.android_log.appendPlainText("[*] Restart Waydroid session for changes to take effect")

    def _deploy_redroid(self):
        image = self.redroid_image.currentText()
        self.android_log.appendPlainText(f"[*] Deploying Redroid container: {image}...")
        try:
            check = subprocess.run(["docker", "--version"], capture_output=True, text=True, timeout=5)
            if check.returncode != 0:
                self.android_log.appendPlainText("[!] Docker not available")
                return
        except FileNotFoundError:
            self.android_log.appendPlainText("[!] Docker not installed. Install with: curl -fsSL https://get.docker.com | sh")
            return

        try:
            subprocess.run(["docker", "rm", "-f", "cloud-android"], capture_output=True, timeout=10)
            result = subprocess.run([
                "docker", "run", "-d", "--name", "cloud-android",
                "--privileged", "--pull", "always",
                "-v", "/opt/cloud-android/data:/data",
                "-p", "5555:5555",
                image,
                "androidboot.redroid_gpu_mode=guest",
            ], capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                self.android_log.appendPlainText(f"[+] Redroid container deployed: {result.stdout.strip()[:12]}")
                self.android_log.appendPlainText("[+] ADB available at localhost:5555")
            else:
                self.android_log.appendPlainText(f"[!] Deploy failed: {result.stderr.strip()[:200]}")
        except subprocess.TimeoutExpired:
            self.android_log.appendPlainText("[!] Docker command timed out (image may still be pulling)")
        except Exception as e:
            self.android_log.appendPlainText(f"[!] Error: {e}")

    def _check_redroid_status(self):
        try:
            result = subprocess.run(
                ["docker", "inspect", "--format", "{{.State.Status}}", "cloud-android"],
                capture_output=True, text=True, timeout=10
            )
            status = result.stdout.strip()
            if status == "running":
                self.android_log.appendPlainText(f"[+] Redroid container: RUNNING")
                adb_check = subprocess.run(
                    ["adb", "connect", "localhost:5555"],
                    capture_output=True, text=True, timeout=10
                )
                self.android_log.appendPlainText(f"[+] ADB: {adb_check.stdout.strip()}")
            elif status:
                self.android_log.appendPlainText(f"[*] Redroid container status: {status}")
            else:
                self.android_log.appendPlainText("[*] No Redroid container found")
        except FileNotFoundError:
            self.android_log.appendPlainText("[!] Docker not installed")
        except Exception as e:
            self.android_log.appendPlainText(f"[!] Error: {e}")

    def _stop_redroid(self):
        try:
            subprocess.run(["docker", "stop", "cloud-android"], capture_output=True, timeout=15)
            subprocess.run(["docker", "rm", "cloud-android"], capture_output=True, timeout=10)
            self.android_log.appendPlainText("[+] Redroid container stopped and removed")
        except FileNotFoundError:
            self.android_log.appendPlainText("[!] Docker not installed")
        except Exception as e:
            self.android_log.appendPlainText(f"[!] Error: {e}")

    def _encrypt_keybox(self):
        kb_path = self.keybox_path.text().strip()
        if not kb_path or not os.path.isfile(kb_path):
            QMessageBox.warning(self, "Keybox", "Select a valid keybox.xml file")
            return

        self.android_log.appendPlainText(f"[*] Encrypting keybox: {kb_path}...")
        try:
            dest_dir = Path("/opt/titan/android/keybox")
            dest_dir.mkdir(parents=True, exist_ok=True)

            # Read and validate XML
            with open(kb_path, "r") as f:
                content = f.read()
            if "<Keybox" not in content and "<keybox" not in content:
                self.android_log.appendPlainText("[!] File does not appear to be a valid keybox.xml")
                return

            # Encrypt with openssl
            encrypted_path = dest_dir / "keybox_encrypted.bin"
            key_hex = os.urandom(32).hex()
            iv_hex = os.urandom(16).hex()

            result = subprocess.run([
                "openssl", "enc", "-aes-256-cbc",
                "-in", kb_path,
                "-out", str(encrypted_path),
                "-K", key_hex, "-iv", iv_hex,
            ], capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                # Save key metadata
                meta = {"key": key_hex, "iv": iv_hex, "source": kb_path,
                        "encrypted_at": datetime.now().isoformat()}
                (dest_dir / "keybox_meta.json").write_text(json.dumps(meta, indent=2))
                self.keybox_status.setText(f"Keybox encrypted: {encrypted_path.name}")
                self.keybox_status.setStyleSheet("color: #4caf50; font-weight: bold;")
                self.android_log.appendPlainText(f"[+] Keybox encrypted → {encrypted_path}")
                self.android_log.appendPlainText(f"[+] Key metadata saved to {dest_dir / 'keybox_meta.json'}")
            else:
                self.android_log.appendPlainText(f"[!] Encryption failed: {result.stderr.strip()[:200]}")
        except FileNotFoundError:
            self.android_log.appendPlainText("[!] openssl not found — install with: apt install openssl")
        except Exception as e:
            self.android_log.appendPlainText(f"[!] Error: {e}")

    def apply_dark_theme(self):
        """Apply Enterprise HRUX theme from centralized theme module."""
        try:
            from titan_enterprise_theme import apply_enterprise_theme
            apply_enterprise_theme(self, "#9c27b0")
        except ImportError:
            pass  # Fallback: no theme applied
    
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
                        border: 2px solid #3A75C4;
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
    
    # ═══════════════════════════════════════════════════════════════════
    # TAB 4: VOICE + VIDEO RECORDING (Speech KYC Challenges)
    # ═══════════════════════════════════════════════════════════════════

    def _build_voice_tab(self):
        """Voice synthesis for 'record a video saying X' KYC challenges."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        self.tabs.addTab(tab, "🎤 Voice")

        # Status
        voice_status = QGroupBox("🎤 Voice Engine Status")
        vs_layout = QVBoxLayout(voice_status)
        self.voice_status_label = QLabel("Checking voice engine...")
        self.voice_status_label.setStyleSheet("color: #aaa; font-size: 12px;")
        vs_layout.addWidget(self.voice_status_label)
        layout.addWidget(voice_status)

        # Check voice engine
        if VOICE_AVAILABLE:
            try:
                engine = KYCVoiceEngine()
                status = engine.get_status()
                backend = status['backend']
                if status['available']:
                    self.voice_status_label.setText(f"✅ Voice engine ready — Backend: {backend.upper()}")
                    self.voice_status_label.setStyleSheet("color: #4caf50; font-size: 12px; font-weight: bold;")
                else:
                    self.voice_status_label.setText("⚠️ No TTS backend found — install espeak-ng or piper")
                    self.voice_status_label.setStyleSheet("color: #ff9800; font-size: 12px;")
            except Exception as e:
                self.voice_status_label.setText(f"❌ Voice engine error: {e}")
                self.voice_status_label.setStyleSheet("color: #f44336; font-size: 12px;")
        else:
            self.voice_status_label.setText("❌ kyc_voice_engine module not available")
            self.voice_status_label.setStyleSheet("color: #f44336; font-size: 12px;")

        # Speech text input
        speech_group = QGroupBox("💬 Speech Challenge")
        sg_layout = QVBoxLayout(speech_group)

        sg_layout.addWidget(QLabel("Text to speak (what the KYC provider asks you to say):"))
        self.speech_text = QPlainTextEdit()
        self.speech_text.setPlaceholderText(
            "Example: My name is John Davis and today is February twentieth two thousand twenty six"
        )
        self.speech_text.setMaximumHeight(80)
        sg_layout.addWidget(self.speech_text)

        # Voice settings
        voice_settings = QHBoxLayout()

        voice_settings.addWidget(QLabel("Voice:"))
        self.voice_gender_combo = QComboBox()
        self.voice_gender_combo.addItems(["Male", "Female"])
        self.voice_gender_combo.setMinimumWidth(100)
        voice_settings.addWidget(self.voice_gender_combo)

        voice_settings.addWidget(QLabel("Accent:"))
        self.voice_accent_combo = QComboBox()
        self.voice_accent_combo.addItems(["US English", "British English", "Australian"])
        self.voice_accent_combo.setMinimumWidth(130)
        voice_settings.addWidget(self.voice_accent_combo)

        voice_settings.addWidget(QLabel("Speed:"))
        self.voice_speed_spin = QSpinBox()
        self.voice_speed_spin.setRange(50, 200)
        self.voice_speed_spin.setValue(100)
        self.voice_speed_spin.setSuffix("%")
        voice_settings.addWidget(self.voice_speed_spin)

        voice_settings.addStretch()
        sg_layout.addLayout(voice_settings)

        # Voice reference (for cloning)
        ref_layout = QHBoxLayout()
        ref_layout.addWidget(QLabel("Voice reference (optional, for cloning):"))
        self.voice_ref_path = QLineEdit()
        self.voice_ref_path.setPlaceholderText("Path to reference voice .wav (leave empty for default)")
        ref_layout.addWidget(self.voice_ref_path)
        voice_ref_btn = QPushButton("Browse")
        voice_ref_btn.clicked.connect(self._browse_voice_ref)
        ref_layout.addWidget(voice_ref_btn)
        sg_layout.addLayout(ref_layout)

        layout.addWidget(speech_group)

        # Action buttons
        action_group = QGroupBox("🎬 Actions")
        ag_layout = QVBoxLayout(action_group)

        btn_row1 = QHBoxLayout()
        self.test_speech_btn = QPushButton("🔊 Test Speech (Audio Only)")
        self.test_speech_btn.setMinimumHeight(40)
        self.test_speech_btn.clicked.connect(self._test_speech)
        btn_row1.addWidget(self.test_speech_btn)

        self.speak_to_cam_btn = QPushButton("🎬 Speak to Camera (Video + Audio)")
        self.speak_to_cam_btn.setMinimumHeight(40)
        self.speak_to_cam_btn.setStyleSheet("QPushButton { background-color: #3A75C4; color: white; font-weight: bold; font-size: 13px; }")
        self.speak_to_cam_btn.clicked.connect(self._speak_to_camera)
        btn_row1.addWidget(self.speak_to_cam_btn)
        ag_layout.addLayout(btn_row1)

        btn_row2 = QHBoxLayout()
        self.stop_voice_btn = QPushButton("⏹ Stop")
        self.stop_voice_btn.setMinimumHeight(35)
        self.stop_voice_btn.clicked.connect(self._stop_voice)
        btn_row2.addWidget(self.stop_voice_btn)
        btn_row2.addStretch()
        ag_layout.addLayout(btn_row2)

        layout.addWidget(action_group)

        # Voice log
        log_group = QGroupBox("📋 Voice Log")
        lg_layout = QVBoxLayout(log_group)
        self.voice_log = QPlainTextEdit()
        self.voice_log.setReadOnly(True)
        self.voice_log.setMaximumHeight(150)
        self.voice_log.setStyleSheet("background-color: #1a1a2e; color: #8892b0; font-family: 'JetBrains Mono', monospace; font-size: 11px;")
        lg_layout.addWidget(self.voice_log)
        layout.addWidget(log_group)

        layout.addStretch()

    def _browse_voice_ref(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Voice Reference", "", "Audio (*.wav *.mp3 *.ogg)")
        if path:
            self.voice_ref_path.setText(path)

    def _get_voice_profile(self):
        """Build VoiceProfile from GUI settings"""
        if not VOICE_AVAILABLE:
            return None
        gender = VoiceGender.FEMALE if self.voice_gender_combo.currentIndex() == 1 else VoiceGender.MALE
        accent_map = {0: "us", 1: "gb", 2: "au"}
        accent = accent_map.get(self.voice_accent_combo.currentIndex(), "us")
        speed = self.voice_speed_spin.value() / 100.0
        ref = self.voice_ref_path.text().strip() or None
        return VoiceProfile(gender=gender, accent=accent, speed=speed, reference_audio=ref)

    def _voice_log(self, msg):
        self.voice_log.appendPlainText(f"[{__import__('datetime').datetime.now().strftime('%H:%M:%S')}] {msg}")

    def _test_speech(self):
        """Generate and play speech audio only (no video)"""
        if not VOICE_AVAILABLE:
            QMessageBox.warning(self, "Voice", "Voice engine not available")
            return
        text = self.speech_text.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Voice", "Enter text to speak")
            return
        self._voice_log(f"Generating speech: '{text[:50]}...'")
        try:
            engine = KYCVoiceEngine()
            engine.on_log = lambda msg, lvl: self._voice_log(msg)
            voice = self._get_voice_profile()
            result = engine.generate_speech(text, voice, "/tmp/titan_test_speech.wav")
            if result:
                self._voice_log(f"✓ Speech generated: {result}")
                import subprocess
                subprocess.Popen(["paplay", result] if __import__('shutil').which("paplay") else ["aplay", result])
                self._voice_log("Playing audio...")
            else:
                self._voice_log("✗ Speech generation failed")
        except Exception as e:
            self._voice_log(f"✗ Error: {e}")

    def _speak_to_camera(self):
        """Full pipeline: generate speech + talking video → stream to camera"""
        if not VOICE_AVAILABLE:
            QMessageBox.warning(self, "Voice", "Voice engine not available")
            return
        text = self.speech_text.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Voice", "Enter text to speak")
            return
        if not self.source_image_path:
            QMessageBox.warning(self, "Voice", "Load a face image first (Camera tab)")
            return

        self._voice_log(f"Starting speech+video: '{text[:50]}...'")
        self.speak_to_cam_btn.setEnabled(False)
        self.speak_to_cam_btn.setText("⏳ Generating...")

        try:
            engine = KYCVoiceEngine()
            engine.on_log = lambda msg, lvl: self._voice_log(msg)
            voice = self._get_voice_profile()

            config = SpeechVideoConfig(
                text=text,
                face_image=self.source_image_path,
                voice=voice,
                camera_device=self.controller.config.device_path,
            )

            # Run in thread to avoid blocking GUI
            import threading
            def run():
                try:
                    ok = engine.speak_to_camera(config)
                    self._voice_log("✓ Speech+video complete" if ok else "✗ Speech+video failed")
                except Exception as e:
                    self._voice_log(f"✗ Error: {e}")
                finally:
                    self.speak_to_cam_btn.setEnabled(True)
                    self.speak_to_cam_btn.setText("🎬 Speak to Camera (Video + Audio)")

            t = threading.Thread(target=run, daemon=True)
            t.start()

        except Exception as e:
            self._voice_log(f"✗ Error: {e}")
            self.speak_to_cam_btn.setEnabled(True)
            self.speak_to_cam_btn.setText("🎬 Speak to Camera (Video + Audio)")

    def _stop_voice(self):
        """Stop any active voice streaming"""
        if VOICE_AVAILABLE:
            try:
                engine = KYCVoiceEngine()
                engine.stop()
                self._voice_log("Stopped")
            except Exception:
                pass

    def closeEvent(self, event):
        """Clean up on close"""
        self.stop_stream()
        self.controller.cleanup()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    try:
        from titan_enterprise_theme import apply_enterprise_theme_to_app
        apply_enterprise_theme_to_app(app, "#9c27b0")
    except ImportError:
        pass

    splash = None
    try:
        from titan_splash import show_titan_splash
        splash = show_titan_splash(app, "KYC BYPASS & COMPLIANCE", "#9c27b0")
    except Exception:
        pass
    
    window = KYCApp()
    window.show()
    if splash:
        splash.finish(window)
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
