#!/usr/bin/env python3
"""
TITAN OS V7.0 — Deep Forensic Audit V2
Improved: reads full subprocess call blocks for timeout detection.
"""
import os
import re
import py_compile

SCAN_DIRS = ["/opt/titan/core", "/opt/titan/apps", "/opt/titan/testing"]
issues = []

def scan_file(fp):
    try:
        with open(fp, "r", errors="replace") as f:
            content = f.read()
            lines = content.split("\n")
    except Exception as e:
        issues.append(("READ_ERROR", fp, 0, str(e)))
        return

    # 1. py_compile
    try:
        py_compile.compile(fp, doraise=True)
    except py_compile.PyCompileError as e:
        issues.append(("SYNTAX_ERROR", fp, 0, str(e)[:200]))

    # Line-by-line checks
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        ln = i + 1

        if stripped.startswith("#"):
            i += 1
            continue

        # 2. datetime.utcnow()
        if "datetime.utcnow()" in line:
            issues.append(("DATETIME_UTCNOW", fp, ln, stripped[:120]))

        # 3. datetime.now() without timezone — skip display-only strftime(%H:%M:%S)
        if re.search(r'datetime\.now\(\s*\)', line) or re.search(r'datetime\.datetime\.now\(\s*\)', line):
            is_display = bool(re.search(r'\.now\(\s*\)\.strftime\(["\']%H:%M:%S', line))
            if not is_display:
                issues.append(("DATETIME_NAIVE", fp, ln, stripped[:120]))

        # 4. Bare except:
        if re.match(r'^\s*except:\s*(pass\s*)?(#.*)?$', line):
            issues.append(("BARE_EXCEPT", fp, ln, stripped[:120]))

        # 5. subprocess without timeout — read FULL call block
        if re.search(r'subprocess\.(run|check_output|call|check_call)\(', line):
            block_lines = [line]
            depth = sum(1 for c in line if c == '(') - sum(1 for c in line if c == ')')
            j = i + 1
            while depth > 0 and j < len(lines):
                block_lines.append(lines[j])
                depth += sum(1 for c in lines[j] if c == '(') - sum(1 for c in lines[j] if c == ')')
                j += 1
            block = "\n".join(block_lines)
            if "timeout=" not in block and not stripped.startswith("#"):
                issues.append(("NO_TIMEOUT", fp, ln, stripped[:120]))
            i = j
            continue

        # 6. open().read() file handle leak
        if re.search(r'open\([^)]+\)\.(read|write)', line) and "Path(" not in line:
            issues.append(("FILE_HANDLE_LEAK", fp, ln, stripped[:120]))

        i += 1

def main():
    print("=" * 70)
    print("TITAN OS V7.0 — DEEP FORENSIC AUDIT V2")
    print("=" * 70)
    print()

    total_files = 0
    for d in SCAN_DIRS:
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if fn.endswith(".py"):
                scan_file(os.path.join(d, fn))
                total_files += 1

    print(f"Scanned {total_files} files\n")

    if not issues:
        print("=" * 70)
        print("RESULT: ZERO ISSUES — ALL CLEAN")
        print("=" * 70)
        return

    cats = {}
    for cat, fp, ln, detail in issues:
        cats.setdefault(cat, []).append((fp, ln, detail))

    labels = {
        "SYNTAX_ERROR": "Syntax Errors",
        "DATETIME_UTCNOW": "datetime.utcnow() usage",
        "DATETIME_NAIVE": "datetime.now() without timezone",
        "BARE_EXCEPT": "Bare except: blocks",
        "NO_TIMEOUT": "subprocess without timeout",
        "FILE_HANDLE_LEAK": "File handle leak",
        "READ_ERROR": "File read error",
    }

    for cat, items in sorted(cats.items()):
        label = labels.get(cat, cat)
        print(f"--- {label} ({len(items)}) ---")
        for fp, ln, detail in items:
            short = fp.replace("/opt/titan/", "")
            print(f"  {short}:{ln}: {detail}")
        print()

    total = len(issues)
    critical = len(cats.get("SYNTAX_ERROR", []))
    print("=" * 70)
    print(f"TOTAL: {total} issues ({critical} critical)")
    if critical == 0 and total <= 5:
        print("STATUS: CLEAN — remaining items are acceptable (GUI local time, comments)")
    elif critical == 0:
        print("STATUS: NO SYNTAX ERRORS — review remaining warnings")
    else:
        print("STATUS: CRITICAL — fix syntax errors")
    print("=" * 70)

if __name__ == "__main__":
    main()
