#!/usr/bin/env python3
"""Fix remaining issues found by verification sweep."""
import re, os

fixes = [
    # 1. forensic_synthesis_engine.py - datetime.utcnow
    {
        "file": "/opt/titan/core/forensic_synthesis_engine.py",
        "old": "from datetime import datetime, timedelta",
        "new": "from datetime import datetime, timedelta, timezone",
    },
    {
        "file": "/opt/titan/core/forensic_synthesis_engine.py",
        "old": "self.now = datetime.utcnow()",
        "new": "self.now = datetime.now(timezone.utc)",
    },
    # 2. forensic_cleaner.py - bare except
    {
        "file": "/opt/titan/core/forensic_cleaner.py",
        "find_line": "except: pass",
        "replace_line": "except Exception: pass",
    },
    # 3. forensic_monitor.py - bare except at line ~238
    {
        "file": "/opt/titan/core/forensic_monitor.py",
        "find_line": "        except:",
        "replace_line": "        except Exception:",
        "context_before": "return hashlib",
    },
    # 4. profile_realism_engine.py - bare except
    {
        "file": "/opt/titan/core/profile_realism_engine.py",
        "find_line": "except: pass",
        "replace_line": "except Exception: pass",
    },
    # 5. app_kyc.py - bare except
    {
        "file": "/opt/titan/apps/app_kyc.py",
        "find_line": "except:",
        "replace_line": "except Exception:",
    },
    # 6. app_unified.py - bare except
    {
        "file": "/opt/titan/apps/app_unified.py",
        "find_line": "except:",
        "replace_line": "except Exception:",
    },
    # 7. detection_emulator.py - bare except
    {
        "file": "/opt/titan/testing/detection_emulator.py",
        "find_line": "except:",
        "replace_line": "except Exception:",
    },
]

for fix in fixes:
    fp = fix["file"]
    if not os.path.exists(fp):
        print(f"SKIP: {fp} not found")
        continue

    with open(fp, "r") as f:
        content = f.read()

    if "old" in fix and "new" in fix:
        if fix["old"] in content:
            content = content.replace(fix["old"], fix["new"], 1)
            print(f"FIXED: {fp} -- replaced '{fix['old'][:50]}...'")
        else:
            print(f"SKIP: {fp} -- old string not found: '{fix['old'][:50]}...'")
    elif "find_line" in fix:
        lines = content.split("\n")
        found = False
        for i, line in enumerate(lines):
            if line.strip() == fix["find_line"].strip():
                # If context_before specified, check nearby lines
                if "context_before" in fix:
                    nearby = "\n".join(lines[max(0,i-5):i])
                    if fix["context_before"] not in nearby:
                        continue
                old_line = lines[i]
                indent = len(old_line) - len(old_line.lstrip())
                lines[i] = " " * indent + fix["replace_line"].strip()
                found = True
                print(f"FIXED: {fp}:{i+1} -- {fix['find_line'].strip()} -> {fix['replace_line'].strip()}")
                break
        if not found:
            print(f"SKIP: {fp} -- line not found: '{fix['find_line'].strip()}'")
        content = "\n".join(lines)

    with open(fp, "w") as f:
        f.write(content)

print("\nDone. Re-run verify_titan.py to confirm.")
