"""
TITAN V8.1 SINGULARITY — Forensic Detection Widget
Real-time forensic monitoring dashboard with LLM-powered analysis.
"""

import sys
import json
import time
import threading
from datetime import datetime, timezone
from pathlib import Path

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
        QScrollArea, QFrame, QPushButton, QProgressBar, QGridLayout,
        QGroupBox, QSplitter, QCheckBox, QSpinBox
    )
    from PyQt6.QtCore import QTimer, QThread, pyqtSignal, Qt
    from PyQt6.QtGui import QFont, QColor, QPalette
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False

# Import forensic monitor
try:
    from forensic_monitor import ForensicMonitor
    MONITOR_AVAILABLE = True
except ImportError:
    try:
        from core.forensic_monitor import ForensicMonitor
        MONITOR_AVAILABLE = True
    except ImportError:
        MONITOR_AVAILABLE = False

if not PYQT_AVAILABLE:
    class _QThreadStub:
        pass
    QThread = _QThreadStub
    def pyqtSignal(*args, **kwargs):
        return None

class ForensicAnalysisThread(QThread):
    """Background thread for forensic analysis."""
    analysis_complete = pyqtSignal(dict)
    
    def __init__(self, monitor):
        super().__init__()
        self.monitor = monitor
        self.running = True
    
    def run(self):
        """Run forensic analysis in background."""
        try:
            # Collect system state
            system_state = self.monitor.scan_system_state()
            
            # Analyze with LLM
            analysis = self.monitor.analyze_with_llm(system_state)
            
            self.analysis_complete.emit({
                "system_state": system_state,
                "analysis": analysis,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        except Exception as e:
            print(f"Forensic analysis error: {e}")
    
    def stop(self):
        """Stop the analysis thread."""
        self.running = False

class ThreatIndicator(QFrame):
    """Visual threat level indicator."""
    
    def __init__(self):
        super().__init__()
        self.setFixedHeight(60)
        self.setStyleSheet("""
            QFrame {
                background: #1a1a1a;
                border: 2px solid #333;
                border-radius: 8px;
                margin: 4px;
            }
            QLabel {
                background: transparent;
                color: #fff;
                font-family: 'JetBrains Mono', monospace;
                font-weight: bold;
            }
        """)
        
        layout = QHBoxLayout(self)
        
        # Threat level label
        self.threat_label = QLabel("🔍 SCANNING...")
        self.threat_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.threat_label.setStyleSheet("font-size: 18px; color: #4CAF50;")
        
        layout.addWidget(self.threat_label)
    
    def update_threat_level(self, risk_level: str):
        """Update threat level display."""
        colors = {
            "low": "#4CAF50",      # Green
            "medium": "#FFC107",   # Yellow  
            "high": "#FF9800",     # Orange
            "critical": "#F44336"   # Red
        }
        
        icons = {
            "low": "🟢",
            "medium": "🟡", 
            "high": "🟠",
            "critical": "🔴"
        }
        
        color = colors.get(risk_level, "#4CAF50")
        icon = icons.get(risk_level, "🔍")
        
        self.threat_label.setText(f"{icon} THREAT LEVEL: {risk_level.upper()}")
        self.threat_label.setStyleSheet(f"font-size: 18px; color: {color};")
        
        # Update border color
        self.setStyleSheet(f"""
            QFrame {{
                background: #1a1a1a;
                border: 2px solid {color};
                border-radius: 8px;
                margin: 4px;
            }}
            QLabel {{
                background: transparent;
                color: #fff;
                font-family: 'JetBrains Mono', monospace;
                font-weight: bold;
            }}
        """)

class IssueListWidget(QScrollArea):
    """Widget to display detected issues."""
    
    def __init__(self):
        super().__init__()
        self.setWidgetResizable(True)
        self.setMinimumHeight(200)
        
        # Create container widget
        self.container = QWidget()
        self.container.setLayout(QVBoxLayout())
        self.setWidget(self.container)
        
        self.setStyleSheet("""
            QScrollArea {
                background: #0a0a0a;
                border: 1px solid #333;
                border-radius: 4px;
            }
            QWidget {
                background: transparent;
            }
        """)
    
    def add_issue(self, issue: dict):
        """Add an issue to the list."""
        issue_frame = QFrame()
        issue_frame.setStyleSheet("""
            QFrame {
                background: #1a1a1a;
                border: 1px solid #333;
                border-radius: 4px;
                margin: 2px;
                padding: 8px;
            }
            QLabel {
                color: #fff;
                font-family: 'JetBrains Mono', monospace;
            }
        """)
        
        layout = QVBoxLayout(issue_frame)
        
        # Issue title with severity color
        severity_colors = {
            "info": "#2196F3",
            "warning": "#FFC107", 
            "danger": "#FF9800",
            "critical": "#F44336"
        }
        
        color = severity_colors.get(issue.get("severity", "info"), "#2196F3")
        
        title = QLabel(f"🚨 {issue.get('title', 'Unknown Issue')}")
        title.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 12px;")
        layout.addWidget(title)
        
        # Description
        desc = QLabel(issue.get("description", ""))
        desc.setStyleSheet("color: #ccc; font-size: 10px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # Evidence
        if issue.get("evidence"):
            evidence = QLabel(f"📋 Evidence: {issue['evidence']}")
            evidence.setStyleSheet("color: #888; font-size: 9px; font-style: italic;")
            evidence.setWordWrap(True)
            layout.addWidget(evidence)
        
        # Recommendation
        if issue.get("recommendation"):
            rec = QLabel(f"💡 Recommendation: {issue['recommendation']}")
            rec.setStyleSheet("color: #4CAF50; font-size: 9px;")
            rec.setWordWrap(True)
            layout.addWidget(rec)
        
        self.container.layout().addWidget(issue_frame)
    
    def clear_issues(self):
        """Clear all issues."""
        # Clear layout
        while self.container.layout().count():
            child = self.container.layout().takeAt(0)
            if child.widget():
                child.widget().deleteLater()

class ForensicWidget(QWidget):
    """Main forensic monitoring widget."""
    
    def __init__(self):
        super().__init__()
        self.monitor = ForensicMonitor() if MONITOR_AVAILABLE else None
        self.analysis_thread = None
        self.last_analysis = None
        
        self.init_ui()
        self.setup_timer()
        self.start_monitoring()
    
    def init_ui(self):
        """Initialize the UI."""
        self.setWindowTitle("🔍 TITAN Forensic Monitor")
        self.setMinimumSize(800, 600)
        
        # Apply dark theme
        self.setStyleSheet("""
            QWidget {
                background: #0a0a0a;
                color: #fff;
                font-family: 'JetBrains Mono', monospace;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #333;
                border-radius: 8px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #4CAF50;
            }
            QPushButton {
                background: #1a1a1a;
                color: #fff;
                border: 1px solid #333;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #2a2a2a;
                border-color: #4CAF50;
            }
            QPushButton:pressed {
                background: #333;
            }
            QTextEdit {
                background: #0a0a0a;
                color: #fff;
                border: 1px solid #333;
                border-radius: 4px;
                padding: 8px;
                font-family: 'JetBrains Mono', monospace;
                font-size: 10px;
            }
        """)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Header with threat indicator
        header_layout = QHBoxLayout()
        
        # Title
        title = QLabel("🔍 TITAN FORENSIC MONITOR")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #4CAF50;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Status indicator
        self.status_label = QLabel("🔄 Initializing...")
        self.status_label.setStyleSheet("color: #FFC107;")
        header_layout.addWidget(self.status_label)
        
        main_layout.addLayout(header_layout)
        
        # Threat level indicator
        self.threat_indicator = ThreatIndicator()
        main_layout.addWidget(self.threat_indicator)
        
        # Create splitter for main content
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel - Issues and alerts
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Issues group
        issues_group = QGroupBox("🚨 DETECTED ISSUES")
        self.issues_list = IssueListWidget()
        issues_layout = QVBoxLayout()
        issues_layout.addWidget(self.issues_list)
        issues_group.setLayout(issues_layout)
        left_layout.addWidget(issues_group)
        
        # Missing components group
        missing_group = QGroupBox("⚠️ MISSING COMPONENTS")
        self.missing_text = QTextEdit()
        self.missing_text.setMaximumHeight(150)
        self.missing_text.setReadOnly(True)
        missing_layout = QVBoxLayout()
        missing_layout.addWidget(self.missing_text)
        missing_group.setLayout(missing_layout)
        left_layout.addWidget(missing_group)
        
        splitter.addWidget(left_panel)
        
        # Right panel - Instructions and analysis
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Instructions group
        instructions_group = QGroupBox("📋 MONITORING INSTRUCTIONS")
        self.instructions_text = QTextEdit()
        self.instructions_text.setReadOnly(True)
        if self.monitor:
            self.instructions_text.setPlainText(self.monitor.get_monitoring_instructions())
        instructions_layout = QVBoxLayout()
        instructions_layout.addWidget(self.instructions_text)
        instructions_group.setLayout(instructions_layout)
        right_layout.addWidget(instructions_group)
        
        # Analysis results group
        analysis_group = QGroupBox("🧠 LLM ANALYSIS")
        self.analysis_text = QTextEdit()
        self.analysis_text.setReadOnly(True)
        analysis_layout = QVBoxLayout()
        analysis_layout.addWidget(self.analysis_text)
        analysis_group.setLayout(analysis_layout)
        right_layout.addWidget(analysis_group)
        
        splitter.addWidget(right_panel)
        
        # Set splitter proportions
        splitter.setSizes([400, 400])
        main_layout.addWidget(splitter)
        
        # Control panel
        control_layout = QHBoxLayout()
        
        # Scan now button
        self.scan_btn = QPushButton("🔍 SCAN NOW")
        self.scan_btn.clicked.connect(self.manual_scan)
        control_layout.addWidget(self.scan_btn)
        
        # Auto-scan checkbox
        self.auto_scan_cb = QCheckBox("Auto-scan (5 min)")
        self.auto_scan_cb.setChecked(True)
        control_layout.addWidget(self.auto_scan_cb)
        
        # Clear cache button
        self.clear_btn = QPushButton("🗑️ CLEAR CACHE")
        self.clear_btn.clicked.connect(self.clear_cache)
        control_layout.addWidget(self.clear_btn)
        
        control_layout.addStretch()
        
        # Last scan time
        self.last_scan_label = QLabel("Never scanned")
        self.last_scan_label.setStyleSheet("color: #888; font-size: 9px;")
        control_layout.addWidget(self.last_scan_label)
        
        main_layout.addLayout(control_layout)
    
    def setup_timer(self):
        """Setup automatic scanning timer."""
        self.timer = QTimer()
        self.timer.timeout.connect(self.auto_scan)
        self.timer.start(300000)  # 5 minutes
    
    def start_monitoring(self):
        """Start the monitoring system."""
        if not self.monitor:
            self.status_label.setText("❌ Monitor unavailable")
            return
        
        self.status_label.setText("🟢 Active")
        self.status_label.setStyleSheet("color: #4CAF50;")
        
        # Initial scan
        self.auto_scan()
    
    def auto_scan(self):
        """Perform automatic scan."""
        if not self.auto_scan_cb.isChecked() or not self.monitor:
            return
        
        self.manual_scan()
    
    def manual_scan(self):
        """Perform manual scan."""
        if not self.monitor:
            return
        
        if self.analysis_thread and self.analysis_thread.isRunning():
            return  # Scan already in progress
        
        self.status_label.setText("🔄 Scanning...")
        self.status_label.setStyleSheet("color: #FFC107;")
        self.scan_btn.setEnabled(False)
        
        # Start analysis thread
        self.analysis_thread = ForensicAnalysisThread(self.monitor)
        self.analysis_thread.analysis_complete.connect(self.on_analysis_complete)
        self.analysis_thread.start()
    
    def on_analysis_complete(self, result: dict):
        """Handle completed analysis."""
        self.last_analysis = result
        self.last_scan_label.setText(f"Last scan: {datetime.now().strftime('%H:%M:%S')}")
        
        # Update UI with results
        analysis = result.get("analysis", {})
        
        # Update threat level
        risk_level = analysis.get("risk_level", "low")
        self.threat_indicator.update_threat_level(risk_level)
        
        # Update issues
        self.issues_list.clear_issues()
        for issue in analysis.get("issues", []):
            self.issues_list.add_issue(issue)
        
        # Update missing components
        missing_text = ""
        for component in analysis.get("missing_components", []):
            missing_text += f"⚠️ {component.get('component', 'Unknown')}\n"
            missing_text += f"   Importance: {component.get('importance', 'unknown')}\n"
            missing_text += f"   Impact: {component.get('impact', 'unknown')}\n\n"
        
        self.missing_text.setPlainText(missing_text or "✅ All components present")
        
        # Update analysis
        analysis_summary = f"""
RISK LEVEL: {risk_level.upper()}

SUMMARY:
{analysis.get('summary', 'No summary available')}

RECOMMENDATIONS:
"""
        for rec in analysis.get("recommendations", []):
            analysis_summary += f"• {rec}\n"
        
        if analysis.get("detectable_artifacts"):
            analysis_summary += "\nDETECTABLE ARTIFACTS:\n"
            for artifact in analysis.get("detectable_artifacts", []):
                analysis_summary += f"• {artifact.get('artifact', 'Unknown')} (Risk: {artifact.get('risk', 'unknown')})\n"
        
        self.analysis_text.setPlainText(analysis_summary)
        
        # Update status
        self.status_label.setText("🟢 Active")
        self.status_label.setStyleSheet("color: #4CAF50;")
        self.scan_btn.setEnabled(True)
    
    def clear_cache(self):
        """Clear forensic cache."""
        if self.monitor and hasattr(self.monitor, 'cache_dir'):
            try:
                for file in self.monitor.cache_dir.glob("*.json"):
                    file.unlink()
                self.status_label.setText("🗑️ Cache cleared")
                self.status_label.setStyleSheet("color: #FFC107;")
            except Exception as e:
                self.status_label.setText(f"❌ Cache error: {e}")
                self.status_label.setStyleSheet("color: #F44336;")

def main():
    """Main function to run the forensic widget."""
    if not PYQT_AVAILABLE:
        print("PyQt6 not available")
        return
    
    if not MONITOR_AVAILABLE:
        print("Forensic monitor not available")
        return
    
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # Apply enterprise theme if available
    try:
        from titan_theme import apply_titan_theme
        apply_titan_theme(app)
    except ImportError:
        pass
    
    widget = ForensicWidget()
    widget.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
