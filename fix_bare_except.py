#!/usr/bin/env python3
"""Fix bare except: blocks and any remaining datetime.utcnow on VPS."""
import os, re

files_to_fix = [
    "/opt/titan/core/forensic_cleaner.py",
    "/opt/titan/core/forensic_monitor.py",
    "/opt/titan/core/profile_realism_engine.py",
    "/opt/titan/apps/app_kyc.py",
    "/opt/titan/apps/app_unified.py",
    "/opt/titan/testing/detection_emulator.py",
    "/opt/titan/core/forensic_synthesis_engine.py",
]

total_fixed = 0
for fp in files_to_fix:
    if not os.path.exists(fp):
        continue
    with open(fp, "r") as f:
        lines = f.readlines()
    changed = False
    for i, line in enumerate(lines):
        stripped = line.rstrip("\n")
        lstripped = stripped.lstrip()
        # Fix bare except:
        if lstripped == "except:" or lstripped == "except: pass":
            indent = len(stripped) - len(lstripped)
            if lstripped == "except: pass":
                lines[i] = " " * indent + "except Exception: pass\n"
            else:
                lines[i] = " " * indent + "except Exception:\n"
            print(f"FIXED bare except: {fp}:{i+1}")
            changed = True
            total_fixed += 1
        # Fix datetime.utcnow()
        if "datetime.utcnow()" in line:
            lines[i] = line.replace("datetime.utcnow()", "datetime.now(timezone.utc)")
            print(f"FIXED utcnow: {fp}:{i+1}")
            changed = True
            total_fixed += 1
    if changed:
        with open(fp, "w") as f:
            f.writelines(lines)

print(f"\nTotal fixes applied: {total_fixed}")
