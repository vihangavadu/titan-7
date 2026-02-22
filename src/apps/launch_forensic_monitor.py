#!/usr/bin/env python3
"""
TITAN V8.1 SINGULARITY — Forensic Monitor Launcher
Quick launcher for the forensic detection widget.
"""

import sys
import os
from pathlib import Path

# Add the current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(current_dir / "core"))

def main():
    """Launch the forensic monitor widget."""
    print("🔍 Starting TITAN Forensic Monitor...")
    
    try:
        # Import and launch the widget
        from forensic_widget import ForensicWidget
        from PyQt6.QtWidgets import QApplication
        
        app = QApplication(sys.argv)
        
        # Apply enterprise theme if available
        try:
            from titan_enterprise_theme import apply_enterprise_theme
            apply_enterprise_theme(app)
            print("✅ Enterprise theme applied")
        except ImportError:
            print("⚠️ Enterprise theme not available")
        
        # Create and show widget
        widget = ForensicWidget()
        widget.show()
        
        print("✅ Forensic monitor started")
        print("📊 The widget will scan the system every 5 minutes")
        print("🧠 LLM analysis will provide intelligent threat assessment")
        print("🚨 Real-time alerts for forensic artifacts and security issues")
        
        sys.exit(app.exec())
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("⚠️ Make sure PyQt6 and required dependencies are installed")
        return 1
    except Exception as e:
        print(f"❌ Error starting forensic monitor: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
