#!/bin/bash
export PYTHONPATH="/opt/titan:/opt/titan/core:/opt/titan/apps"

echo "=========================================="
echo "REPO TREE vs VPS — DEEP GAP CHECK"
echo "=========================================="

# 1. Check for missing directories that exist in local repo
echo ""
echo "=== [1] DIRECTORIES IN LOCAL REPO — CHECK VPS ==="
for d in extensions extensions/ghost_motor extensions/tx_monitor lib models patches patches/librewolf patches/ghostery profgen tools vpn testing state config scripts/install scripts/vps; do
  if [ -d "/opt/titan/src/$d" ] || [ -d "/opt/titan/$d" ]; then
    count=$(find "/opt/titan/src/$d" "/opt/titan/$d" -maxdepth 1 -type f 2>/dev/null | wc -l)
    echo "  OK: $d ($count files)"
  else
    echo "  MISSING: $d"
  fi
done

# 2. Key files that should exist
echo ""
echo "=== [2] KEY FILES CHECK ==="
files=(
  "src/extensions/golden_trap.js"
  "src/extensions/ghost_motor/ghost_motor.js"
  "src/extensions/ghost_motor/manifest.json"
  "src/extensions/tx_monitor/tx_monitor.js"
  "src/extensions/tx_monitor/manifest.json"
  "src/extensions/tx_monitor/background.js"
  "src/lib/integrity_shield.c"
  "src/lib/network_shield_original.c"
  "src/lib/tcp_fingerprint.c"
  "src/lib/vps_hw_shield.c"
  "src/lib/xdp_loader.c"
  "src/vpn/xray-server.json"
  "src/vpn/xray-client.json"
  "src/vpn/setup-vps-relay.sh"
  "src/vpn/setup-exit-node.sh"
  "src/tools/autofill_entropy.py"
  "src/tools/dump_history.py"
  "src/tools/inspect_profile.py"
  "src/tools/profile_counts.py"
  "src/tools/state_architect.py"
  "src/tools/top_sites_sync.py"
  "src/assets/motions/generate_motions.py"
  "src/bin/titan_mission_control.py"
  "src/branding/generate_branding.py"
  "src/branding/install_branding.sh"
  "src/config/oblivion_template.json"
  "src/config/llm_config.json"
  "src/build.sh"
)
missing=0
for f in "${files[@]}"; do
  if [ ! -f "/opt/titan/$f" ]; then
    echo "  MISSING: $f"
    missing=$((missing+1))
  fi
done
echo "  Missing files: $missing"

# 3. KYC module full audit
echo ""
echo "=== [3] KYC MODULE AUDIT ==="
echo "-- Core KYC files --"
for f in kyc_core.py kyc_enhanced.py kyc_voice_engine.py waydroid_sync.py tof_depth_synthesis.py; do
  if [ -f "/opt/titan/core/$f" ]; then
    lines=$(wc -l < "/opt/titan/core/$f")
    echo "  OK: core/$f ($lines lines)"
  else
    echo "  MISSING: core/$f"
  fi
done

echo ""
echo "-- KYC App --"
if [ -f "/opt/titan/apps/app_kyc.py" ]; then
  lines=$(wc -l < "/opt/titan/apps/app_kyc.py")
  tabs=$(grep -c "addTab" /opt/titan/apps/app_kyc.py 2>/dev/null)
  echo "  OK: apps/app_kyc.py ($lines lines, $tabs tabs)"
  grep "addTab.*'" /opt/titan/apps/app_kyc.py 2>/dev/null | sed "s/.*addTab.*'\(.*\)'.*/    -> \1/"
else
  echo "  MISSING: apps/app_kyc.py"
fi

echo ""
echo "-- Waydroid/Android --"
for f in scripts/setup_waydroid_android.sh scripts/deploy_android_vm.sh; do
  if [ -f "/opt/titan/$f" ]; then
    lines=$(wc -l < "/opt/titan/$f")
    echo "  OK: $f ($lines lines)"
  else
    echo "  MISSING: $f"
  fi
done

echo ""
echo "-- Android directory --"
if [ -d "/opt/titan/android" ]; then
  echo "  OK: /opt/titan/android exists"
  ls -la /opt/titan/android/ 2>/dev/null
else
  echo "  MISSING: /opt/titan/android"
fi

echo ""
echo "-- Waydroid status --"
which waydroid 2>/dev/null && echo "  waydroid binary: found" || echo "  waydroid binary: NOT INSTALLED"
systemctl is-active waydroid-container 2>/dev/null && echo "  waydroid service: active" || echo "  waydroid service: not active"

# 4. Check KYC capabilities in the codebase
echo ""
echo "=== [4] KYC CAPABILITIES IN CODEBASE ==="
python3 << 'PYEOF'
import ast, os, re

# Scan kyc modules for classes and functions
for mod_file in ["kyc_core.py", "kyc_enhanced.py", "kyc_voice_engine.py", "tof_depth_synthesis.py", "waydroid_sync.py"]:
    fpath = f"/opt/titan/core/{mod_file}"
    if not os.path.exists(fpath):
        print(f"  {mod_file}: NOT FOUND")
        continue
    try:
        content = open(fpath).read()
        tree = ast.parse(content)
        classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        funcs = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and not n.name.startswith('_')]
        print(f"  {mod_file}:")
        if classes:
            print(f"    Classes: {', '.join(classes)}")
        if funcs[:15]:
            print(f"    Functions: {', '.join(funcs[:15])}")
    except Exception as e:
        print(f"  {mod_file}: PARSE ERROR: {e}")

# Check app_kyc tabs and features
print()
print("  app_kyc.py tab features:")
try:
    content = open("/opt/titan/apps/app_kyc.py").read()
    imports = re.findall(r'from\s+(\w+)\s+import\s+(.+)', content)
    core_imports = [(m,c.strip()) for m,c in imports if not m.startswith(("PyQt","pathlib","datetime","os","sys","json"))]
    for mod, classes in core_imports:
        print(f"    import {mod}: {classes[:80]}")
except Exception as e:
    print(f"    ERROR: {e}")
PYEOF

echo ""
echo "=========================================="
echo "REPO TREE CHECK COMPLETE"
echo "=========================================="
