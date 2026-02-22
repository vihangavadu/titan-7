#!/usr/bin/env python3
"""
TITAN V8.0 — Comprehensive App Test Harness
Runs each GUI app headless via Xvfb, finds all buttons/widgets,
clicks them, tests features, and generates a real report.
"""

import sys
import os
import time
import traceback
import subprocess
import json
from datetime import datetime

# Ensure paths
sys.path.insert(0, "/opt/titan/apps")
sys.path.insert(0, "/opt/titan/core")

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["DISPLAY"] = ":99"

from PyQt6.QtWidgets import (
    QApplication, QPushButton, QToolButton, QTabWidget, QTabBar,
    QComboBox, QLineEdit, QTextEdit, QPlainTextEdit, QCheckBox,
    QRadioButton, QSpinBox, QDoubleSpinBox, QSlider, QMenuBar,
    QMenu, QStatusBar, QLabel, QGroupBox, QStackedWidget,
    QTableWidget, QTreeWidget, QListWidget, QProgressBar, QWidget,
    QMainWindow
)
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt, QTimer

PASS = 0
FAIL = 0
WARN = 0
RESULTS = []

def log(status, msg):
    global PASS, FAIL, WARN
    if status == "PASS":
        PASS += 1
        print(f"  ✅ {msg}")
    elif status == "FAIL":
        FAIL += 1
        print(f"  ❌ {msg}")
    elif status == "WARN":
        WARN += 1
        print(f"  ⚠️  {msg}")
    else:
        print(f"  ℹ️  {msg}")
    RESULTS.append({"status": status, "msg": msg})


def discover_widgets(window):
    """Discover all interactive widgets in a window."""
    info = {
        "buttons": [],
        "tabs": [],
        "combos": [],
        "line_edits": [],
        "text_edits": [],
        "checkboxes": [],
        "radio_buttons": [],
        "spinboxes": [],
        "sliders": [],
        "tables": [],
        "trees": [],
        "lists": [],
        "labels": [],
        "groups": [],
        "progress_bars": [],
        "menus": [],
        "statusbar": None,
        "stacked": [],
    }

    for w in window.findChildren(QWidget):
        try:
            name = w.objectName() or w.__class__.__name__
            if isinstance(w, (QPushButton, QToolButton)):
                text = w.text() if hasattr(w, 'text') else name
                info["buttons"].append({"widget": w, "text": text, "name": name, "enabled": w.isEnabled()})
            elif isinstance(w, QTabWidget):
                tabs = []
                for i in range(w.count()):
                    tabs.append(w.tabText(i))
                info["tabs"].append({"widget": w, "tabs": tabs, "name": name})
            elif isinstance(w, QComboBox):
                items = [w.itemText(i) for i in range(min(w.count(), 20))]
                info["combos"].append({"widget": w, "items": items, "name": name})
            elif isinstance(w, QLineEdit):
                info["line_edits"].append({"widget": w, "text": w.text(), "name": name})
            elif isinstance(w, (QTextEdit, QPlainTextEdit)):
                info["text_edits"].append({"widget": w, "name": name})
            elif isinstance(w, QCheckBox):
                info["checkboxes"].append({"widget": w, "text": w.text(), "name": name, "checked": w.isChecked()})
            elif isinstance(w, QRadioButton):
                info["radio_buttons"].append({"widget": w, "text": w.text(), "name": name})
            elif isinstance(w, (QSpinBox, QDoubleSpinBox)):
                info["spinboxes"].append({"widget": w, "name": name, "value": w.value()})
            elif isinstance(w, QSlider):
                info["sliders"].append({"widget": w, "name": name, "value": w.value()})
            elif isinstance(w, QTableWidget):
                info["tables"].append({"widget": w, "rows": w.rowCount(), "cols": w.columnCount(), "name": name})
            elif isinstance(w, QTreeWidget):
                info["trees"].append({"widget": w, "name": name})
            elif isinstance(w, QListWidget):
                info["lists"].append({"widget": w, "count": w.count(), "name": name})
            elif isinstance(w, QGroupBox):
                info["groups"].append({"widget": w, "title": w.title(), "name": name})
            elif isinstance(w, QProgressBar):
                info["progress_bars"].append({"widget": w, "name": name, "value": w.value()})
            elif isinstance(w, QStatusBar):
                info["statusbar"] = w
            elif isinstance(w, QStackedWidget):
                info["stacked"].append({"widget": w, "count": w.count(), "name": name})
        except Exception:
            pass

    # Menus
    menubar = window.menuBar() if hasattr(window, 'menuBar') else None
    if menubar:
        for action in menubar.actions():
            menu = action.menu()
            if menu:
                sub_actions = []
                for sa in menu.actions():
                    if not sa.isSeparator():
                        sub_actions.append(sa.text())
                info["menus"].append({"name": action.text(), "actions": sub_actions})

    return info


def test_buttons(info, app_name):
    """Click every enabled button and check for crashes."""
    buttons = info["buttons"]
    clicked = 0
    errors = 0
    skipped = 0

    for btn_info in buttons:
        btn = btn_info["widget"]
        text = btn_info["text"].strip()

        # Skip dangerous buttons
        dangerous = ["quit", "exit", "close", "shutdown", "kill", "delete all", "format", "wipe", "destroy"]
        if any(d in text.lower() for d in dangerous):
            log("INFO", f"  Skipped dangerous button: '{text}'")
            skipped += 1
            continue

        if not btn.isEnabled():
            skipped += 1
            continue

        try:
            btn.click()
            QApplication.processEvents()
            time.sleep(0.05)
            clicked += 1
        except Exception as e:
            log("FAIL", f"  Button '{text}' CRASHED: {type(e).__name__}: {str(e)[:80]}")
            errors += 1

    return clicked, errors, skipped


def test_tabs(info, app_name):
    """Switch through every tab."""
    switched = 0
    errors = 0
    for tab_info in info["tabs"]:
        tw = tab_info["widget"]
        for i, tab_name in enumerate(tab_info["tabs"]):
            try:
                tw.setCurrentIndex(i)
                QApplication.processEvents()
                time.sleep(0.05)
                switched += 1
            except Exception as e:
                log("FAIL", f"  Tab '{tab_name}' CRASHED: {e}")
                errors += 1
    return switched, errors


def test_combos(info, app_name):
    """Cycle through combo box items."""
    tested = 0
    errors = 0
    for combo_info in info["combos"]:
        cb = combo_info["widget"]
        if not cb.isEnabled():
            continue
        for i in range(min(cb.count(), 10)):
            try:
                cb.setCurrentIndex(i)
                QApplication.processEvents()
                time.sleep(0.02)
                tested += 1
            except Exception as e:
                errors += 1
    return tested, errors


def test_checkboxes(info, app_name):
    """Toggle every checkbox."""
    toggled = 0
    errors = 0
    for cb_info in info["checkboxes"]:
        cb = cb_info["widget"]
        if not cb.isEnabled():
            continue
        try:
            original = cb.isChecked()
            cb.setChecked(not original)
            QApplication.processEvents()
            cb.setChecked(original)  # restore
            QApplication.processEvents()
            toggled += 1
        except Exception as e:
            errors += 1
    return toggled, errors


def test_app(app_label, module_name, class_name, qapp):
    """Full test of one app."""
    global PASS, FAIL, WARN

    print(f"\n{'━'*64}")
    print(f"  TESTING: {app_label}")
    print(f"{'━'*64}")

    # 1. Import
    try:
        mod = __import__(module_name)
        log("PASS", f"Import {module_name}: OK")
    except Exception as e:
        log("FAIL", f"Import {module_name}: {type(e).__name__}: {str(e)[:100]}")
        return

    # 2. Find the main window class
    cls = None
    if class_name:
        cls = getattr(mod, class_name, None)
    if not cls:
        # Try common patterns
        for candidate in ["MainWindow", "TitanDevHub", "TitanBugReporter", 
                          "UnifiedDashboard", "GenesisApp", "CerberusApp", "KYCApp"]:
            cls = getattr(mod, candidate, None)
            if cls:
                break

    if not cls:
        # List all classes in module
        classes = [x for x in dir(mod) if not x.startswith('_')]
        log("WARN", f"No main window class found. Available: {', '.join(classes[:15])}")
        # Try to find any QMainWindow subclass
        for attr_name in classes:
            attr = getattr(mod, attr_name, None)
            if isinstance(attr, type) and issubclass(attr, QMainWindow):
                cls = attr
                log("INFO", f"  Found QMainWindow subclass: {attr_name}")
                break

    if not cls:
        log("FAIL", f"No launchable window class in {module_name}")
        return

    log("PASS", f"Window class: {cls.__name__}")

    # 3. Instantiate
    window = None
    try:
        window = cls()
        window.show()
        QApplication.processEvents()
        time.sleep(0.2)
        log("PASS", f"Window launched: {window.windowTitle() or 'untitled'}")
        log("INFO", f"  Size: {window.width()}x{window.height()}")
    except Exception as e:
        log("FAIL", f"Window launch FAILED: {type(e).__name__}: {str(e)[:120]}")
        traceback.print_exc()
        return

    # 4. Discover widgets
    try:
        info = discover_widgets(window)

        total_buttons = len(info["buttons"])
        enabled_buttons = len([b for b in info["buttons"] if b["enabled"]])
        total_tabs_widgets = len(info["tabs"])
        total_tab_pages = sum(len(t["tabs"]) for t in info["tabs"])
        total_combos = len(info["combos"])
        total_checkboxes = len(info["checkboxes"])
        total_tables = len(info["tables"])
        total_trees = len(info["trees"])
        total_lists = len(info["lists"])
        total_groups = len(info["groups"])
        total_labels = len([w for w in window.findChildren(QLabel)])
        total_menus = len(info["menus"])
        total_progress = len(info["progress_bars"])
        total_line_edits = len(info["line_edits"])
        total_text_edits = len(info["text_edits"])

        log("INFO", f"  Buttons: {total_buttons} ({enabled_buttons} enabled)")
        log("INFO", f"  Tab widgets: {total_tabs_widgets} ({total_tab_pages} pages)")
        log("INFO", f"  Combos: {total_combos} | Checkboxes: {total_checkboxes}")
        log("INFO", f"  Tables: {total_tables} | Trees: {total_trees} | Lists: {total_lists}")
        log("INFO", f"  Groups: {total_groups} | Labels: {total_labels}")
        log("INFO", f"  Menus: {total_menus} | Progress: {total_progress}")
        log("INFO", f"  LineEdits: {total_line_edits} | TextEdits: {total_text_edits}")

        # Button names
        btn_names = [b["text"] for b in info["buttons"] if b["text"].strip()][:30]
        if btn_names:
            log("INFO", f"  Button labels: {', '.join(btn_names[:15])}")
            if len(btn_names) > 15:
                log("INFO", f"  ... and {len(btn_names)-15} more")

        # Tab names
        for t in info["tabs"]:
            log("INFO", f"  Tab pages: {', '.join(t['tabs'])}")

        # Menu items
        for m in info["menus"]:
            log("INFO", f"  Menu '{m['name']}': {', '.join(m['actions'][:10])}")

    except Exception as e:
        log("FAIL", f"Widget discovery FAILED: {e}")
        traceback.print_exc()
        if window:
            window.close()
        return

    # 5. Test tabs
    try:
        tab_switched, tab_errors = test_tabs(info, app_label)
        if total_tab_pages > 0:
            if tab_errors == 0:
                log("PASS", f"Tabs: {tab_switched}/{total_tab_pages} switched OK")
            else:
                log("FAIL", f"Tabs: {tab_errors} errors out of {total_tab_pages}")
    except Exception as e:
        log("FAIL", f"Tab test crashed: {e}")

    # 6. Test buttons
    try:
        btn_clicked, btn_errors, btn_skipped = test_buttons(info, app_label)
        if btn_errors == 0:
            log("PASS", f"Buttons: {btn_clicked} clicked OK ({btn_skipped} skipped)")
        else:
            log("FAIL", f"Buttons: {btn_errors} errors, {btn_clicked} OK, {btn_skipped} skipped")
    except Exception as e:
        log("FAIL", f"Button test crashed: {e}")

    # 7. Test combos
    try:
        combo_tested, combo_errors = test_combos(info, app_label)
        if total_combos > 0:
            if combo_errors == 0:
                log("PASS", f"Combos: {combo_tested} items cycled OK")
            else:
                log("FAIL", f"Combos: {combo_errors} errors")
    except Exception as e:
        log("FAIL", f"Combo test crashed: {e}")

    # 8. Test checkboxes
    try:
        cb_toggled, cb_errors = test_checkboxes(info, app_label)
        if total_checkboxes > 0:
            if cb_errors == 0:
                log("PASS", f"Checkboxes: {cb_toggled} toggled OK")
            else:
                log("FAIL", f"Checkboxes: {cb_errors} errors")
    except Exception as e:
        log("FAIL", f"Checkbox test crashed: {e}")

    # 9. Check statusbar
    if info["statusbar"]:
        log("PASS", f"Status bar: present")
    else:
        log("INFO", f"  No status bar")

    # 10. Test tables
    for tbl in info["tables"]:
        log("INFO", f"  Table '{tbl['name']}': {tbl['rows']} rows × {tbl['cols']} cols")

    # Cleanup
    try:
        window.close()
        QApplication.processEvents()
        time.sleep(0.1)
        log("PASS", f"Window closed cleanly")
    except Exception as e:
        log("WARN", f"Window close: {e}")


def main():
    global PASS, FAIL, WARN

    print("")
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  TITAN V8.0 — FULL APP TEST HARNESS                        ║")
    print(f"║  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}                                        ║")
    print("╚══════════════════════════════════════════════════════════════╝")

    qapp = QApplication.instance()
    if not qapp:
        qapp = QApplication(sys.argv)

    apps = [
        ("TITAN Dev Hub (AI IDE)",          "titan_dev_hub",    "TitanDevHub"),
        ("Unified Operations Dashboard",    "app_unified",      None),
        ("Genesis Profile Forge",           "app_genesis",      None),
        ("Cerberus Asset Validation",       "app_cerberus",     None),
        ("KYC Compliance Module",           "app_kyc",          None),
        ("Diagnostic Bug Reporter",         "app_bug_reporter", None),
    ]

    for app_label, module_name, class_name in apps:
        try:
            test_app(app_label, module_name, class_name, qapp)
        except Exception as e:
            log("FAIL", f"{app_label}: UNHANDLED CRASH — {type(e).__name__}: {str(e)[:120]}")
            traceback.print_exc()

    # Final report
    print(f"\n{'━'*64}")
    print("")
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  FINAL TEST REPORT                                          ║")
    print("╠══════════════════════════════════════════════════════════════╣")
    print(f"║  ✅ PASSED:   {PASS:<3}                                          ║")
    print(f"║  ❌ FAILED:   {FAIL:<3}                                          ║")
    print(f"║  ⚠️  WARNINGS: {WARN:<3}                                          ║")
    print("╠══════════════════════════════════════════════════════════════╣")

    if FAIL == 0:
        print("║  STATUS: 🟢 ALL APPS OPERATIONAL                            ║")
    elif FAIL <= 3:
        print("║  STATUS: 🟡 MOSTLY FUNCTIONAL — check FAILs above           ║")
    else:
        print("║  STATUS: 🔴 ISSUES FOUND — action required                  ║")

    print("╚══════════════════════════════════════════════════════════════╝")

    # Save JSON report
    report = {
        "timestamp": datetime.now().isoformat(),
        "pass": PASS,
        "fail": FAIL,
        "warn": WARN,
        "results": RESULTS,
    }
    with open("/tmp/titan_app_test_report.json", "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n  Report saved: /tmp/titan_app_test_report.json")


if __name__ == "__main__":
    main()
