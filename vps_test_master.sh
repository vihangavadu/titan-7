#!/bin/bash
# TITAN V8.0 — Master App Test Runner
# Each app tested in isolated subprocess with timeout
export QT_QPA_PLATFORM=offscreen
export DISPLAY=:99
export PYTHONDONTWRITEBYTECODE=1

pkill Xvfb 2>/dev/null; sleep 1
Xvfb :99 -screen 0 1920x1080x24 &>/dev/null &
sleep 1

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  TITAN V8.0 — COMPREHENSIVE APP TEST (subprocess isolated)  ║"
echo "║  $(date '+%Y-%m-%d %H:%M:%S')                                        ║"
echo "╚══════════════════════════════════════════════════════════════╝"

TOTAL_PASS=0
TOTAL_FAIL=0
TOTAL_WARN=0

run_app_test() {
    local APP_LABEL="$1"
    local TEST_SCRIPT="$2"
    local TIMEOUT_SEC="$3"

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  TESTING: $APP_LABEL (timeout: ${TIMEOUT_SEC}s)"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    OUTPUT=$(timeout "$TIMEOUT_SEC" python3 -c "$TEST_SCRIPT" 2>&1)
    EXIT_CODE=$?

    echo "$OUTPUT" | grep -E "^  [✅❌⚠️ℹ️]"

    local P=$(echo "$OUTPUT" | grep -c "^  ✅")
    local F=$(echo "$OUTPUT" | grep -c "^  ❌")
    local W=$(echo "$OUTPUT" | grep -c "^  ⚠️")

    if [ "$EXIT_CODE" -eq 124 ]; then
        echo "  ❌ TIMED OUT after ${TIMEOUT_SEC}s"
        F=$((F+1))
    elif [ "$EXIT_CODE" -ne 0 ] && [ "$EXIT_CODE" -ne 1 ]; then
        echo "  ❌ CRASHED with exit code $EXIT_CODE"
        F=$((F+1))
    fi

    TOTAL_PASS=$((TOTAL_PASS+P))
    TOTAL_FAIL=$((TOTAL_FAIL+F))
    TOTAL_WARN=$((TOTAL_WARN+W))

    echo "  ── Result: $P pass / $F fail / $W warn"
}

# ═══════════════════════════════════════════════════════════════
# TEST 1: TITAN DEV HUB (Non-GUI)
# ═══════════════════════════════════════════════════════════════
run_app_test "TITAN Dev Hub (AI IDE)" '
import sys, os, tempfile
from pathlib import Path
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, "/opt/titan/apps")
sys.path.insert(0, "/opt/titan/core")

P=F=0
def p(m):
    global P; P+=1; print(f"  ✅ {m}", flush=True)
def f(m):
    global F; F+=1; print(f"  ❌ {m}", flush=True)
def i(m):
    print(f"  ℹ️  {m}", flush=True)

try:
    import titan_dev_hub as dh
    p("Import titan_dev_hub: OK")
except Exception as e:
    f(f"Import: {e}"); sys.exit(1)

# AIProviderConfig
try:
    c = dh.AIProviderConfig(name="t", provider_type="openai", api_key="k", endpoint="e", model="m")
    assert c.name == "t"
    p("AIProviderConfig: OK")
except Exception as e:
    f(f"AIProviderConfig: {e}")

# AIProviderManager
try:
    tmp = tempfile.mkdtemp()
    mgr = dh.AIProviderManager(config_path=Path(tmp)/"cfg.json")
    p("AIProviderManager: instantiated")
    for prov in ["openai", "copilot", "windsurf", "anthropic", "local"]:
        try:
            mgr.configure_provider(prov, f"key-{prov}", model="test-model")
            p(f"  configure_provider({prov}): OK")
        except Exception as e:
            f(f"  configure_provider({prov}): {e}")
    mgr.active_provider = "openai"
    p("active_provider set: OK")
    mgr.save_config()
    if (Path(tmp)/"cfg.json").exists():
        p("save_config: file created")
    else:
        f("save_config: no file")
    i(f"Providers: {list(mgr.providers.keys())}")
except Exception as e:
    f(f"AIProviderManager: {e}")

# IssueProcessor
for cls_name in ["IssueProcessor", "UpgradeManager", "AutoFixEngine", "CodeAnalyzer",
                  "SafeFileEditor", "AIInterface", "BatchOperationHandler", "ChatMessage"]:
    if hasattr(dh, cls_name):
        try:
            obj = getattr(dh, cls_name)
            if callable(obj) and cls_name != "ChatMessage":
                inst = obj()
                p(f"{cls_name}: instantiated")
                methods = [m for m in dir(inst) if not m.startswith("_") and callable(getattr(inst, m, None))]
                i(f"  Methods: {", ".join(methods[:10])}")
            else:
                p(f"{cls_name}: exists")
        except Exception as e:
            f(f"{cls_name}: {type(e).__name__}: {str(e)[:60]}")
    else:
        print(f"  ⚠️  {cls_name}: not found", flush=True)

# Version check
import re
src = open("/opt/titan/apps/titan_dev_hub.py").read()
v = re.search(r"version\s*=\s*\"([\d.]+)\"", src)
if v and "8.0" in v.group(1):
    p(f"Version: {v.group(1)}")
elif v:
    f(f"Version: {v.group(1)} — expected 8.0.x")

# Branding
if "V8.0 MAXIMUM" in src:
    p("V8.0 MAXIMUM branding: present")
else:
    f("V8.0 MAXIMUM branding: missing")

sys.exit(0)
' 30

# ═══════════════════════════════════════════════════════════════
# GENERIC GUI APP TEST FUNCTION
# ═══════════════════════════════════════════════════════════════
gui_test_code() {
    local MODULE="$1"
    local CLASS="$2"
    cat << PYEOF
import sys, os, time
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["DISPLAY"] = ":99"
sys.path.insert(0, "/opt/titan/apps")
sys.path.insert(0, "/opt/titan/core")

# Suppress network-heavy imports
import unittest.mock as mock

# Mock Google search to prevent hanging
try:
    import importlib
    # Pre-patch googlesearch if it exists
    sys.modules['googlesearch'] = mock.MagicMock()
    sys.modules['googlesearch.googlesearch'] = mock.MagicMock()
except:
    pass

from PyQt6.QtWidgets import (
    QApplication, QPushButton, QToolButton, QTabWidget,
    QComboBox, QCheckBox, QRadioButton, QSpinBox, QDoubleSpinBox,
    QTableWidget, QTreeWidget, QListWidget, QLineEdit, QTextEdit,
    QPlainTextEdit, QGroupBox, QProgressBar, QStatusBar, QWidget,
    QMainWindow, QSlider
)

P=F=W=0
def p(m):
    global P; P+=1; print(f"  ✅ {m}", flush=True)
def f(m):
    global F; F+=1; print(f"  ❌ {m}", flush=True)
def w(m):
    global W; W+=1; print(f"  ⚠️  {m}", flush=True)
def i(m):
    print(f"  ℹ️  {m}", flush=True)

# Import
try:
    mod = __import__("$MODULE")
    p("Import $MODULE: OK")
except Exception as e:
    f(f"Import $MODULE: {e}")
    sys.exit(1)

# QApp
qapp = QApplication.instance() or QApplication(sys.argv)

# Instantiate
try:
    cls = getattr(mod, "$CLASS")
    win = cls()
    win.show()
    qapp.processEvents()
    time.sleep(0.5)
    title = win.windowTitle() or "untitled"
    p(f"Window: '{title}' ({win.width()}x{win.height()})")
except Exception as e:
    f(f"Window launch: {type(e).__name__}: {str(e)[:100]}")
    import traceback; traceback.print_exc()
    sys.exit(1)

# Discover widgets
buttons = []
tabs = []
combos = []
checkboxes = []
radios = []
tables = []
line_edits = []
text_edits = []
groups = []
lists_w = []
trees = []
progress = []
spinboxes = []
sliders = []
has_statusbar = False

for child in win.findChildren(QWidget):
    try:
        nm = child.objectName() or ""
        if isinstance(child, (QPushButton, QToolButton)):
            txt = child.text() if hasattr(child, "text") else nm
            buttons.append({"w": child, "t": txt, "e": child.isEnabled()})
        elif isinstance(child, QTabWidget):
            tn = [child.tabText(j) for j in range(child.count())]
            tabs.append({"w": child, "tabs": tn})
        elif isinstance(child, QComboBox):
            combos.append({"w": child, "c": child.count()})
        elif isinstance(child, QCheckBox):
            checkboxes.append({"w": child, "t": child.text()})
        elif isinstance(child, QRadioButton):
            radios.append({"w": child, "t": child.text()})
        elif isinstance(child, QTableWidget):
            tables.append({"w": child, "r": child.rowCount(), "c": child.columnCount()})
        elif isinstance(child, QLineEdit):
            line_edits.append(child)
        elif isinstance(child, (QTextEdit, QPlainTextEdit)):
            text_edits.append(child)
        elif isinstance(child, QGroupBox):
            groups.append(child.title())
        elif isinstance(child, QListWidget):
            lists_w.append({"w": child, "c": child.count()})
        elif isinstance(child, QTreeWidget):
            trees.append(child)
        elif isinstance(child, QProgressBar):
            progress.append(child)
        elif isinstance(child, (QSpinBox, QDoubleSpinBox)):
            spinboxes.append(child)
        elif isinstance(child, QSlider):
            sliders.append(child)
        elif isinstance(child, QStatusBar):
            has_statusbar = True
    except:
        pass

# Report counts
total_btns = len(buttons)
enabled_btns = len([b for b in buttons if b["e"]])
total_tabs = sum(len(t["tabs"]) for t in tabs)
i(f"Buttons: {total_btns} ({enabled_btns} enabled) | Tab pages: {total_tabs}")
i(f"Combos: {len(combos)} | Checkboxes: {len(checkboxes)} | Radios: {len(radios)}")
i(f"Tables: {len(tables)} | Trees: {len(trees)} | Lists: {len(lists_w)}")
i(f"LineEdits: {len(line_edits)} | TextEdits: {len(text_edits)} | Spinboxes: {len(spinboxes)}")
i(f"Groups: {len(groups)} | Progress: {len(progress)} | StatusBar: {has_statusbar}")

# Button names
btn_names = [b["t"].strip() for b in buttons if b["t"].strip()]
for j in range(0, len(btn_names), 12):
    chunk = btn_names[j:j+12]
    i(f"Buttons: {', '.join(chunk)}")

# Tab names
for t in tabs:
    i(f"Tabs: {', '.join(t['tabs'])}")

# Group names
if groups:
    i(f"Groups: {', '.join(groups[:15])}")

# Table details
for idx, t in enumerate(tables):
    i(f"Table {idx}: {t['r']} rows × {t['c']} cols")

# ── TEST TABS ──
tab_ok = tab_err = 0
for t in tabs:
    tw = t["w"]
    for j in range(len(t["tabs"])):
        try:
            tw.setCurrentIndex(j)
            qapp.processEvents()
            time.sleep(0.03)
            tab_ok += 1
        except Exception as e:
            f(f"Tab '{t['tabs'][j]}': {e}")
            tab_err += 1
if tab_ok > 0:
    if tab_err == 0:
        p(f"Tabs: all {tab_ok} switched OK")
    else:
        f(f"Tabs: {tab_err} errors / {tab_ok+tab_err}")

# ── TEST BUTTONS ──
dangerous = ["quit","exit","close","shutdown","kill","delete all","format","wipe",
             "destroy","cancel","stop all","terminate","clear all","reset all","purge",
             "stop","abort","remove all"]
btn_ok = btn_err = btn_skip = 0
for b in buttons:
    txt = b["t"].strip().lower()
    if not b["e"] or not txt or any(d in txt for d in dangerous):
        btn_skip += 1
        continue
    try:
        b["w"].click()
        qapp.processEvents()
        time.sleep(0.02)
        btn_ok += 1
    except Exception as e:
        f(f"Button '{b['t']}': {type(e).__name__}: {str(e)[:50]}")
        btn_err += 1

if btn_err == 0:
    p(f"Buttons: {btn_ok} clicked OK ({btn_skip} skipped)")
else:
    f(f"Buttons: {btn_err} errors, {btn_ok} OK, {btn_skip} skipped")

# ── TEST COMBOS ──
combo_ok = combo_err = 0
for c in combos:
    cb = c["w"]
    if not cb.isEnabled():
        continue
    for j in range(min(c["c"], 10)):
        try:
            cb.setCurrentIndex(j)
            qapp.processEvents()
            combo_ok += 1
        except:
            combo_err += 1
if combo_ok > 0:
    if combo_err == 0:
        p(f"Combos: {combo_ok} items cycled OK")
    else:
        f(f"Combos: {combo_err} errors / {combo_ok+combo_err}")

# ── TEST CHECKBOXES ──
cb_ok = cb_err = 0
for c in checkboxes:
    cw = c["w"]
    if not cw.isEnabled():
        continue
    try:
        orig = cw.isChecked()
        cw.setChecked(not orig)
        qapp.processEvents()
        cw.setChecked(orig)
        qapp.processEvents()
        cb_ok += 1
    except:
        cb_err += 1
if cb_ok > 0:
    if cb_err == 0:
        p(f"Checkboxes: {cb_ok} toggled OK")
    else:
        f(f"Checkboxes: {cb_err} errors / {cb_ok+cb_err}")

# ── TEST RADIOS ──
r_ok = 0
for r in radios:
    rw = r["w"]
    if not rw.isEnabled():
        continue
    try:
        rw.setChecked(True)
        qapp.processEvents()
        r_ok += 1
    except:
        pass
if r_ok > 0:
    p(f"Radio buttons: {r_ok} tested OK")

# ── STATUSBAR ──
if has_statusbar:
    p("Status bar: present")

# ── CLOSE ──
try:
    win.close()
    qapp.processEvents()
    p("Window closed cleanly")
except Exception as e:
    w(f"Window close: {e}")

sys.exit(0)
PYEOF
}

# ═══════════════════════════════════════════════════════════════
# TEST 2: UNIFIED OPERATIONS DASHBOARD
# ═══════════════════════════════════════════════════════════════
run_app_test "Unified Operations Dashboard" "$(gui_test_code app_unified UnifiedOperationCenter)" 60

# ═══════════════════════════════════════════════════════════════
# TEST 3: GENESIS PROFILE FORGE
# ═══════════════════════════════════════════════════════════════
run_app_test "Genesis Profile Forge" "$(gui_test_code app_genesis GenesisApp)" 45

# ═══════════════════════════════════════════════════════════════
# TEST 4: CERBERUS ASSET VALIDATION
# ═══════════════════════════════════════════════════════════════
run_app_test "Cerberus Asset Validation" "$(gui_test_code app_cerberus CerberusApp)" 45

# ═══════════════════════════════════════════════════════════════
# TEST 5: KYC COMPLIANCE MODULE
# ═══════════════════════════════════════════════════════════════
run_app_test "KYC Compliance Module" "$(gui_test_code app_kyc KYCApp)" 45

# ═══════════════════════════════════════════════════════════════
# TEST 6: DIAGNOSTIC BUG REPORTER
# ═══════════════════════════════════════════════════════════════
run_app_test "Diagnostic Bug Reporter" "$(gui_test_code app_bug_reporter BugReporterWindow)" 45

# ═══════════════════════════════════════════════════════════════
# FINAL REPORT
# ═══════════════════════════════════════════════════════════════
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  FINAL TEST REPORT                                          ║"
echo "╠══════════════════════════════════════════════════════════════╣"
printf "║  ✅ PASSED:   %-3s                                          ║\n" "$TOTAL_PASS"
printf "║  ❌ FAILED:   %-3s                                          ║\n" "$TOTAL_FAIL"
printf "║  ⚠️  WARNINGS: %-3s                                          ║\n" "$TOTAL_WARN"
echo "╠══════════════════════════════════════════════════════════════╣"

TOTAL=$((TOTAL_PASS + TOTAL_FAIL))
if [ "$TOTAL" -gt 0 ]; then
    RATE=$(( (TOTAL_PASS * 100) / TOTAL ))
    printf "║  Success Rate: %s%%                                       ║\n" "$RATE"
fi

if [ "$TOTAL_FAIL" -eq 0 ]; then
    echo "║  STATUS: 🟢 ALL APPS FULLY OPERATIONAL                      ║"
elif [ "$TOTAL_FAIL" -le 3 ]; then
    echo "║  STATUS: 🟡 MOSTLY FUNCTIONAL — check FAILs above           ║"
else
    echo "║  STATUS: 🔴 ISSUES FOUND — action required                  ║"
fi
echo "╚══════════════════════════════════════════════════════════════╝"

pkill Xvfb 2>/dev/null
