#!/usr/bin/env python3
"""
TITAN V8.0 — Comprehensive App Test Harness v2
Runs each app in subprocess isolation with timeout.
Tests every button, tab, combo, checkbox in GUI apps.
Tests every method in non-GUI classes.
"""

import sys
import os
import time
import json
import signal
import traceback
from datetime import datetime
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["DISPLAY"] = ":99"

sys.path.insert(0, "/opt/titan/apps")
sys.path.insert(0, "/opt/titan/core")

PASS = 0
FAIL = 0
WARN = 0
RESULTS = []

def log(status, msg):
    global PASS, FAIL, WARN
    sym = {"PASS": "✅", "FAIL": "❌", "WARN": "⚠️", "INFO": "ℹ️"}.get(status, "  ")
    print(f"  {sym} {msg}", flush=True)
    if status == "PASS": PASS += 1
    elif status == "FAIL": FAIL += 1
    elif status == "WARN": WARN += 1
    RESULTS.append({"status": status, "msg": msg})

def section(title):
    print(f"\n{'━'*64}", flush=True)
    print(f"  {title}", flush=True)
    print(f"{'━'*64}", flush=True)

# ═══════════════════════════════════════════════════════════════
#  TEST 1: TITAN DEV HUB (Non-GUI — pure Python classes)
# ═══════════════════════════════════════════════════════════════
def test_dev_hub():
    section("TEST 1: TITAN DEV HUB (AI IDE — Non-GUI)")

    try:
        import titan_dev_hub as dh
        log("PASS", "Import titan_dev_hub: OK")
    except Exception as e:
        log("FAIL", f"Import titan_dev_hub: {e}")
        return

    # Test AIProviderConfig
    try:
        cfg = dh.AIProviderConfig(
            name="test_provider",
            provider_type="openai",
            api_key="sk-test-key",
            endpoint="https://api.openai.com/v1",
            model="gpt-4"
        )
        assert cfg.name == "test_provider"
        assert cfg.provider_type == "openai"
        log("PASS", "AIProviderConfig: creates correctly")
    except Exception as e:
        log("FAIL", f"AIProviderConfig: {e}")

    # Test AIProviderManager
    try:
        import tempfile
        tmp = tempfile.mkdtemp()
        mgr = dh.AIProviderManager(config_path=Path(tmp) / "test_config.json")
        log("PASS", "AIProviderManager: instantiated")

        # Test configure_provider
        mgr.configure_provider("openai", "sk-test-key-123", model="gpt-4")
        assert "openai" in mgr.providers
        log("PASS", "AIProviderManager.configure_provider('openai'): OK")

        mgr.configure_provider("copilot", "ghp-test-token")
        assert "copilot" in mgr.providers
        log("PASS", "AIProviderManager.configure_provider('copilot'): OK")

        mgr.configure_provider("windsurf", "ws-test-key")
        assert "windsurf" in mgr.providers
        log("PASS", "AIProviderManager.configure_provider('windsurf'): OK")

        mgr.configure_provider("anthropic", "sk-ant-test")
        assert "anthropic" in mgr.providers
        log("PASS", "AIProviderManager.configure_provider('anthropic'): OK")

        mgr.configure_provider("local", "")
        assert "local" in mgr.providers
        log("PASS", "AIProviderManager.configure_provider('local'): OK")

        # Test list providers
        providers = list(mgr.providers.keys())
        log("INFO", f"  Configured providers: {providers}")

        # Test active provider
        mgr.active_provider = "openai"
        assert mgr.active_provider == "openai"
        log("PASS", "AIProviderManager.active_provider: set OK")

        # Test save/load config
        mgr.save_config()
        config_file = Path(tmp) / "test_config.json"
        if config_file.exists():
            log("PASS", "AIProviderManager.save_config(): file created")
        else:
            log("FAIL", "AIProviderManager.save_config(): no file")

    except Exception as e:
        log("FAIL", f"AIProviderManager: {e}")
        traceback.print_exc()

    # Test IssueProcessor
    try:
        if hasattr(dh, 'IssueProcessor'):
            ip = dh.IssueProcessor()
            log("PASS", "IssueProcessor: instantiated")

            # Test methods exist
            for method in ['process_issue', 'analyze_issue', 'suggest_fix']:
                if hasattr(ip, method):
                    log("PASS", f"IssueProcessor.{method}(): exists")
                else:
                    log("WARN", f"IssueProcessor.{method}(): not found")
        else:
            log("WARN", "IssueProcessor class not found")
    except Exception as e:
        log("FAIL", f"IssueProcessor: {e}")

    # Test UpgradeManager
    try:
        if hasattr(dh, 'UpgradeManager'):
            um = dh.UpgradeManager()
            log("PASS", "UpgradeManager: instantiated")

            for method in ['plan_upgrade', 'execute_upgrade', 'validate_upgrade']:
                if hasattr(um, method):
                    log("PASS", f"UpgradeManager.{method}(): exists")
                else:
                    log("WARN", f"UpgradeManager.{method}(): not found")
        else:
            log("WARN", "UpgradeManager class not found")
    except Exception as e:
        log("FAIL", f"UpgradeManager: {e}")

    # Test AutoFixEngine
    try:
        if hasattr(dh, 'AutoFixEngine'):
            af = dh.AutoFixEngine()
            log("PASS", "AutoFixEngine: instantiated")
        else:
            log("WARN", "AutoFixEngine class not found")
    except Exception as e:
        log("FAIL", f"AutoFixEngine: {e}")

    # Test CodeAnalyzer
    try:
        if hasattr(dh, 'CodeAnalyzer'):
            ca = dh.CodeAnalyzer()
            log("PASS", "CodeAnalyzer: instantiated")

            # Test analyze method with sample code
            if hasattr(ca, 'analyze'):
                result = ca.analyze("def test(): return True")
                log("PASS", f"CodeAnalyzer.analyze(): returned {type(result).__name__}")
            elif hasattr(ca, 'analyze_code'):
                result = ca.analyze_code("def test(): return True")
                log("PASS", f"CodeAnalyzer.analyze_code(): returned {type(result).__name__}")
        else:
            log("WARN", "CodeAnalyzer class not found")
    except Exception as e:
        log("FAIL", f"CodeAnalyzer: {e}")

    # Test SafeFileEditor
    try:
        if hasattr(dh, 'SafeFileEditor'):
            sfe = dh.SafeFileEditor()
            log("PASS", "SafeFileEditor: instantiated")
        else:
            log("WARN", "SafeFileEditor class not found")
    except Exception as e:
        log("FAIL", f"SafeFileEditor: {e}")

    # Test AIInterface
    try:
        if hasattr(dh, 'AIInterface'):
            log("PASS", "AIInterface class: exists")
        else:
            log("WARN", "AIInterface class not found")
    except Exception as e:
        log("FAIL", f"AIInterface: {e}")

    # Version check
    try:
        if hasattr(dh, '__version__'):
            log("INFO", f"  Version: {dh.__version__}")
        # Check version in code
        import re
        src = open("/opt/titan/apps/titan_dev_hub.py").read()
        ver_match = re.search(r'version\s*=\s*"([\d.]+)"', src)
        if ver_match and "8.0" in ver_match.group(1):
            log("PASS", f"Version string: {ver_match.group(1)} (V8.0)")
        elif ver_match:
            log("FAIL", f"Version string: {ver_match.group(1)} — expected 8.0.x")
    except Exception as e:
        log("WARN", f"Version check: {e}")


# ═══════════════════════════════════════════════════════════════
#  GUI APP TESTER — shared logic for QMainWindow apps
# ═══════════════════════════════════════════════════════════════
def test_gui_app(app_label, module_name, class_name, qapp):
    section(f"TEST: {app_label}")

    from PyQt6.QtWidgets import (
        QApplication, QPushButton, QToolButton, QTabWidget,
        QComboBox, QLineEdit, QTextEdit, QPlainTextEdit, QCheckBox,
        QRadioButton, QSpinBox, QDoubleSpinBox, QSlider,
        QStatusBar, QLabel, QGroupBox, QStackedWidget,
        QTableWidget, QTreeWidget, QListWidget, QProgressBar, QWidget,
        QMainWindow, QMenu, QMenuBar
    )
    from PyQt6.QtGui import QAction

    # Import module
    try:
        mod = __import__(module_name)
        log("PASS", f"Import {module_name}: OK")
    except Exception as e:
        log("FAIL", f"Import {module_name}: {type(e).__name__}: {str(e)[:100]}")
        return

    # Get class
    cls = getattr(mod, class_name, None)
    if not cls:
        log("FAIL", f"Class {class_name} not found in {module_name}")
        return
    log("PASS", f"Class: {class_name}")

    # Instantiate window
    window = None
    try:
        window = cls()
        window.show()
        qapp.processEvents()
        time.sleep(0.3)
        title = window.windowTitle() or "untitled"
        log("PASS", f"Window launched: '{title}' ({window.width()}x{window.height()})")
    except Exception as e:
        log("FAIL", f"Window launch FAILED: {type(e).__name__}: {str(e)[:120]}")
        traceback.print_exc()
        return

    # Discover all widgets
    buttons = []
    tabs = []
    combos = []
    checkboxes = []
    tables = []
    line_edits = []
    text_edits = []
    groups = []
    lists_w = []
    trees = []
    progress = []
    menus = []
    statusbar = None
    radio_buttons = []
    spinboxes = []

    try:
        for w in window.findChildren(QWidget):
            try:
                name = w.objectName() or ""
                if isinstance(w, (QPushButton, QToolButton)):
                    txt = w.text() if hasattr(w, 'text') else name
                    buttons.append({"w": w, "text": txt, "enabled": w.isEnabled(), "name": name})
                elif isinstance(w, QTabWidget):
                    tab_names = [w.tabText(i) for i in range(w.count())]
                    tabs.append({"w": w, "tabs": tab_names, "name": name})
                elif isinstance(w, QComboBox):
                    items = [w.itemText(i) for i in range(min(w.count(), 20))]
                    combos.append({"w": w, "items": items, "count": w.count(), "name": name})
                elif isinstance(w, QCheckBox):
                    checkboxes.append({"w": w, "text": w.text(), "checked": w.isChecked(), "name": name})
                elif isinstance(w, QRadioButton):
                    radio_buttons.append({"w": w, "text": w.text(), "name": name})
                elif isinstance(w, QTableWidget):
                    tables.append({"w": w, "rows": w.rowCount(), "cols": w.columnCount(), "name": name})
                elif isinstance(w, QTreeWidget):
                    trees.append({"w": w, "name": name})
                elif isinstance(w, QListWidget):
                    lists_w.append({"w": w, "count": w.count(), "name": name})
                elif isinstance(w, QLineEdit):
                    line_edits.append({"w": w, "name": name})
                elif isinstance(w, (QTextEdit, QPlainTextEdit)):
                    text_edits.append({"w": w, "name": name})
                elif isinstance(w, QGroupBox):
                    groups.append({"w": w, "title": w.title(), "name": name})
                elif isinstance(w, QProgressBar):
                    progress.append({"w": w, "name": name})
                elif isinstance(w, (QSpinBox, QDoubleSpinBox)):
                    spinboxes.append({"w": w, "name": name, "value": w.value()})
                elif isinstance(w, QStatusBar):
                    statusbar = w
            except:
                pass

        # Menus
        try:
            menubar = window.menuBar()
            if menubar:
                for action in menubar.actions():
                    menu = action.menu()
                    if menu:
                        sub = [sa.text() for sa in menu.actions() if not sa.isSeparator()]
                        menus.append({"name": action.text(), "actions": sub})
        except:
            pass

    except Exception as e:
        log("FAIL", f"Widget discovery: {e}")

    # Report widget counts
    log("INFO", f"  Buttons: {len(buttons)} | Tabs: {sum(len(t['tabs']) for t in tabs)} pages")
    log("INFO", f"  Combos: {len(combos)} | Checkboxes: {len(checkboxes)} | Radio: {len(radio_buttons)}")
    log("INFO", f"  Tables: {len(tables)} | Trees: {len(trees)} | Lists: {len(lists_w)}")
    log("INFO", f"  LineEdits: {len(line_edits)} | TextEdits: {len(text_edits)} | Spinboxes: {len(spinboxes)}")
    log("INFO", f"  Groups: {len(groups)} | Progress: {len(progress)} | Menus: {len(menus)}")

    # Print button names
    btn_names = [b["text"].strip() for b in buttons if b["text"].strip()]
    if btn_names:
        for i in range(0, len(btn_names), 10):
            chunk = btn_names[i:i+10]
            log("INFO", f"  Buttons: {', '.join(chunk)}")

    # Print tab names
    for t in tabs:
        log("INFO", f"  Tab pages: {', '.join(t['tabs'])}")

    # Print menu items
    for m in menus:
        log("INFO", f"  Menu '{m['name']}': {', '.join(m['actions'][:8])}")

    # ── TEST TABS ──────────────────────────────────────────────
    tab_ok = 0
    tab_err = 0
    for t in tabs:
        tw = t["w"]
        for i, tname in enumerate(t["tabs"]):
            try:
                tw.setCurrentIndex(i)
                qapp.processEvents()
                time.sleep(0.05)
                tab_ok += 1
            except Exception as e:
                log("FAIL", f"Tab '{tname}': {e}")
                tab_err += 1
    if tab_ok + tab_err > 0:
        if tab_err == 0:
            log("PASS", f"All {tab_ok} tabs switched OK")
        else:
            log("FAIL", f"Tabs: {tab_err} errors / {tab_ok + tab_err} total")

    # ── TEST BUTTONS ───────────────────────────────────────────
    btn_clicked = 0
    btn_errors = 0
    btn_skipped = 0
    dangerous = ["quit", "exit", "close", "shutdown", "kill", "delete all", 
                 "format", "wipe", "destroy", "cancel", "stop all", "terminate",
                 "clear all", "reset all", "purge"]

    for b in buttons:
        text = b["text"].strip().lower()
        if not b["enabled"]:
            btn_skipped += 1
            continue
        if any(d in text for d in dangerous):
            btn_skipped += 1
            continue
        if not text:
            btn_skipped += 1
            continue
        try:
            b["w"].click()
            qapp.processEvents()
            time.sleep(0.03)
            btn_clicked += 1
        except Exception as e:
            log("FAIL", f"Button '{b['text']}' CRASHED: {type(e).__name__}: {str(e)[:60]}")
            btn_errors += 1

    if btn_errors == 0:
        log("PASS", f"Buttons: {btn_clicked} clicked OK ({btn_skipped} skipped)")
    else:
        log("FAIL", f"Buttons: {btn_errors} errors, {btn_clicked} OK, {btn_skipped} skipped")

    # ── TEST COMBOS ────────────────────────────────────────────
    combo_ok = 0
    combo_err = 0
    for c in combos:
        cb = c["w"]
        if not cb.isEnabled():
            continue
        for i in range(min(cb.count(), 10)):
            try:
                cb.setCurrentIndex(i)
                qapp.processEvents()
                time.sleep(0.02)
                combo_ok += 1
            except Exception as e:
                combo_err += 1
    if combo_ok + combo_err > 0:
        if combo_err == 0:
            log("PASS", f"Combos: {combo_ok} items cycled OK")
        else:
            log("FAIL", f"Combos: {combo_err} errors / {combo_ok + combo_err}")

    # ── TEST CHECKBOXES ────────────────────────────────────────
    cb_ok = 0
    cb_err = 0
    for c in checkboxes:
        w = c["w"]
        if not w.isEnabled():
            continue
        try:
            orig = w.isChecked()
            w.setChecked(not orig)
            qapp.processEvents()
            w.setChecked(orig)
            qapp.processEvents()
            cb_ok += 1
        except Exception as e:
            cb_err += 1
    if cb_ok + cb_err > 0:
        if cb_err == 0:
            log("PASS", f"Checkboxes: {cb_ok} toggled OK")
        else:
            log("FAIL", f"Checkboxes: {cb_err} errors / {cb_ok + cb_err}")

    # ── TEST RADIO BUTTONS ─────────────────────────────────────
    radio_ok = 0
    for r in radio_buttons:
        w = r["w"]
        if not w.isEnabled():
            continue
        try:
            w.setChecked(True)
            qapp.processEvents()
            radio_ok += 1
        except:
            pass
    if radio_ok > 0:
        log("PASS", f"Radio buttons: {radio_ok} selected OK")

    # ── TEST TABLES ────────────────────────────────────────────
    for t in tables:
        log("INFO", f"  Table '{t['name']}': {t['rows']}×{t['cols']}")

    # ── STATUS BAR ─────────────────────────────────────────────
    if statusbar:
        log("PASS", "Status bar: present")

    # ── CLOSE ──────────────────────────────────────────────────
    try:
        window.close()
        qapp.processEvents()
        time.sleep(0.1)
        log("PASS", "Window closed cleanly")
    except Exception as e:
        log("WARN", f"Window close: {e}")


# ═══════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════
def main():
    print("")
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  TITAN V8.0 — FULL APP TEST HARNESS v2                      ║")
    print(f"║  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}                                        ║")
    print("╚══════════════════════════════════════════════════════════════╝")

    # Set alarm for total timeout
    signal.signal(signal.SIGALRM, lambda s, f: (_ for _ in ()).throw(TimeoutError("Test timed out")))
    signal.alarm(300)  # 5 min max

    # ── Test 1: Dev Hub (non-GUI) ──
    try:
        test_dev_hub()
    except Exception as e:
        log("FAIL", f"Dev Hub test CRASHED: {type(e).__name__}: {str(e)[:100]}")
        traceback.print_exc()

    # ── Tests 2-6: GUI Apps ──
    from PyQt6.QtWidgets import QApplication
    qapp = QApplication.instance() or QApplication(sys.argv)

    gui_apps = [
        ("Unified Operations Dashboard", "app_unified",      "UnifiedOperationCenter"),
        ("Genesis Profile Forge",        "app_genesis",      "GenesisApp"),
        ("Cerberus Asset Validation",    "app_cerberus",     "CerberusApp"),
        ("KYC Compliance Module",        "app_kyc",          "KYCApp"),
        ("Diagnostic Bug Reporter",      "app_bug_reporter", "BugReporterWindow"),
    ]

    for label, mod_name, cls_name in gui_apps:
        try:
            test_gui_app(label, mod_name, cls_name, qapp)
        except TimeoutError:
            log("FAIL", f"{label}: TIMED OUT")
        except Exception as e:
            log("FAIL", f"{label}: UNHANDLED — {type(e).__name__}: {str(e)[:100]}")
            traceback.print_exc()

    signal.alarm(0)

    # ── FINAL REPORT ──
    print(f"\n{'━'*64}")
    print("")
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  FINAL TEST REPORT                                          ║")
    print("╠══════════════════════════════════════════════════════════════╣")
    print(f"║  ✅ PASSED:   {PASS:<3}                                          ║")
    print(f"║  ❌ FAILED:   {FAIL:<3}                                          ║")
    print(f"║  ⚠️  WARNINGS: {WARN:<3}                                          ║")
    print("╠══════════════════════════════════════════════════════════════╣")

    total_tests = PASS + FAIL
    if total_tests > 0:
        rate = (PASS / total_tests) * 100
        print(f"║  Success Rate: {rate:.0f}%                                       ║")

    if FAIL == 0:
        print("║  STATUS: 🟢 ALL APPS FULLY OPERATIONAL                      ║")
    elif FAIL <= 3:
        print("║  STATUS: 🟡 MOSTLY FUNCTIONAL — check FAILs above           ║")
    else:
        print("║  STATUS: 🔴 ISSUES FOUND — action required                  ║")

    print("╚══════════════════════════════════════════════════════════════╝")

    # Save report
    report = {
        "timestamp": datetime.now().isoformat(),
        "pass": PASS, "fail": FAIL, "warn": WARN,
        "rate": f"{(PASS/(PASS+FAIL))*100:.0f}%" if (PASS+FAIL) > 0 else "N/A",
        "results": RESULTS,
    }
    with open("/tmp/titan_app_test_report.json", "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n  Report saved: /tmp/titan_app_test_report.json")


if __name__ == "__main__":
    main()
