#!/usr/bin/env python3
"""TITAN OS V7.0 — Full Verification Script"""
import py_compile, os, sys

dirs = {
    "Core": "/opt/titan/core",
    "Apps": "/opt/titan/apps",
    "Testing": "/opt/titan/testing",
}

total_pass = 0
total_fail = 0
failures = []

for label, d in dirs.items():
    p = f = 0
    if not os.path.isdir(d):
        print(f"{label}: directory not found")
        continue
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".py"):
            continue
        fp = os.path.join(d, fn)
        try:
            py_compile.compile(fp, doraise=True)
            p += 1
        except py_compile.PyCompileError as e:
            f += 1
            failures.append(f"{fp}: {e}")
    print(f"{label}: {p} PASS, {f} FAIL")
    total_pass += p
    total_fail += f

print()
if failures:
    print("=== FAILURES ===")
    for fail in failures:
        print(f"  FAIL: {fail}")
    print()

print(f"=== TOTAL: {total_pass} PASS, {total_fail} FAIL ===")
if total_fail == 0:
    print("STATUS: ALL MODULES VERIFIED OK")
else:
    print(f"STATUS: {total_fail} MODULES NEED ATTENTION")

# Also check for remaining datetime.utcnow
print()
print("--- Checking for datetime.utcnow remnants ---")
utcnow_count = 0
for label, d in dirs.items():
    if not os.path.isdir(d):
        continue
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".py"):
            continue
        fp = os.path.join(d, fn)
        try:
            with open(fp, "r") as fh:
                for i, line in enumerate(fh, 1):
                    if "datetime.utcnow" in line:
                        print(f"  {fp}:{i}: {line.strip()}")
                        utcnow_count += 1
        except Exception:
            pass

if utcnow_count == 0:
    print("  CLEAN: No datetime.utcnow found anywhere")
else:
    print(f"  WARNING: {utcnow_count} occurrences remaining")

# Check bare except
print()
print("--- Checking for bare except: blocks ---")
bare_count = 0
for label, d in dirs.items():
    if not os.path.isdir(d):
        continue
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".py"):
            continue
        fp = os.path.join(d, fn)
        try:
            with open(fp, "r") as fh:
                for i, line in enumerate(fh, 1):
                    stripped = line.strip()
                    if stripped == "except:" or stripped.startswith("except: "):
                        print(f"  {fp}:{i}: {stripped}")
                        bare_count += 1
        except Exception:
            pass

if bare_count == 0:
    print("  CLEAN: No bare except: blocks found")
else:
    print(f"  INFO: {bare_count} bare except: blocks remaining")
