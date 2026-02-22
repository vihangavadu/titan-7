#!/bin/bash
export QT_QPA_PLATFORM=offscreen
export DISPLAY=:99
cd /opt/titan/apps

python3 << 'PYEOF'
import sys, inspect
sys.path.insert(0, '/opt/titan/core')
sys.path.insert(0, '/opt/titan/apps')

from PyQt6.QtWidgets import QMainWindow, QWidget

apps = ['titan_dev_hub', 'app_unified', 'app_genesis', 'app_cerberus', 'app_kyc', 'app_bug_reporter']
for a in apps:
    try:
        mod = __import__(a)
        qmw = []
        qw = []
        other = []
        for name, obj in inspect.getmembers(mod, inspect.isclass):
            if obj.__module__ != a:
                continue
            if issubclass(obj, QMainWindow):
                qmw.append(name)
            elif issubclass(obj, QWidget):
                qw.append(name)
            else:
                other.append(name)
        print(f"{a}:")
        if qmw:
            print(f"  QMainWindow: {qmw}")
        if qw:
            print(f"  QWidget: {qw}")
        if not qmw and not qw:
            print(f"  NO GUI CLASS — other: {other[:8]}")
    except Exception as e:
        print(f"{a}: ERROR — {type(e).__name__}: {e}")
PYEOF
