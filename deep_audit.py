#!/usr/bin/env python3
"""
TITAN OS V7.0 — Deep Forensic Audit
Scans ALL .py files for every known gap category.
"""
import os
import re
import py_compile
import sys

SCAN_DIRS = [
    "/opt/titan/core",
    "/opt/titan/apps",
    "/opt/titan/testing",
]

issues = []

def scan_file(fp):
    """Scan a single file for all known gap categories."""
    try:
        with open(fp, "r", errors="replace") as f:
            content = f.read()
            lines = content.split("\n")
    except Exception as e:
        issues.append(("READ_ERROR", fp, 0, str(e)))
        return

    # 1. py_compile check
    try:
        py_compile.compile(fp, doraise=True)
    except py_compile.PyCompileError as e:
        issues.append(("SYNTAX_ERROR", fp, 0, str(e)[:200]))

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # 2. datetime.utcnow()
        if "datetime.utcnow()" in line:
            issues.append(("DATETIME_UTCNOW", fp, i, stripped[:120]))

        # 3. datetime.now() without timezone (naive)
        # Match datetime.now() but NOT datetime.now(timezone.utc) or datetime.now(tz=...)
        if re.search(r'datetime\.now\(\s*\)', line):
            issues.append(("DATETIME_NAIVE", fp, i, stripped[:120]))

        # 4. Bare except:
        if stripped == "except:" or stripped == "except: pass" or re.match(r'^except:\s*(#.*)?$', stripped):
            issues.append(("BARE_EXCEPT", fp, i, stripped[:120]))

        # 5. Hardcoded wrong Ollama model
        if "titan-mistral" in line and "ollama" in fp.lower():
            issues.append(("WRONG_MODEL", fp, i, stripped[:120]))

        # 6. Windows Camoufox path on Linux system
        if "C:\\Program Files\\Camoufox" in line or "C:/Program Files/Camoufox" in line:
            issues.append(("WINDOWS_PATH", fp, i, stripped[:120]))

        # 7. Old Camoufox pref path (should be /opt/camoufox/...)
        if "/usr/lib/camoufox" in line.lower() and "comment" not in line.lower() and not stripped.startswith("#"):
            issues.append(("OLD_CAMOUFOX_PATH", fp, i, stripped[:120]))

        # 8. subprocess without timeout (only flag subprocess.run/check_output without timeout=)
        if re.search(r'subprocess\.(run|check_output|call|check_call)\(', line):
            # Look ahead up to 5 lines for timeout=
            block = "\n".join(lines[i-1:min(i+5, len(lines))])
            if "timeout=" not in block and "timeout =" not in block:
                # Skip if check=False (intentionally fire-and-forget)
                if "check=False" not in block:
                    issues.append(("NO_TIMEOUT", fp, i, stripped[:120]))

        # 9. open() without context manager (potential file handle leak)
        # Only flag .read() or .write() chained directly on open()
        if re.search(r'open\([^)]+\)\.(read|write)', line) and "Path(" not in line:
            issues.append(("FILE_HANDLE_LEAK", fp, i, stripped[:120]))

        # 10. Hardcoded API keys or passwords (basic check)
        if re.search(r'(api_key|apikey|password|secret)\s*=\s*["\'][^"\']{8,}', line, re.IGNORECASE):
            if not stripped.startswith("#") and "environ" not in line and "getenv" not in line and "os.environ" not in line:
                issues.append(("HARDCODED_SECRET", fp, i, stripped[:120]))

    # 11. Check imports: datetime used but timezone not imported
    if "datetime.now(timezone.utc)" in content or "datetime.utcnow" in content:
        if "from datetime import" in content:
            import_line = [l for l in lines if "from datetime import" in l]
            if import_line and "timezone" not in import_line[0]:
                issues.append(("MISSING_TZ_IMPORT", fp, 0, import_line[0].strip()[:120]))


def main():
    print("=" * 70)
    print("TITAN OS V7.0 — DEEP FORENSIC AUDIT")
    print("=" * 70)
    print()

    total_files = 0
    for d in SCAN_DIRS:
        if not os.path.isdir(d):
            print(f"WARN: {d} not found")
            continue
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".py"):
                continue
            fp = os.path.join(d, fn)
            scan_file(fp)
            total_files += 1

    print(f"Scanned {total_files} files\n")

    if not issues:
        print("=" * 70)
        print("RESULT: ZERO ISSUES FOUND — ALL CLEAN")
        print("=" * 70)
        return

    # Group by category
    categories = {}
    for cat, fp, line, detail in issues:
        categories.setdefault(cat, []).append((fp, line, detail))

    cat_labels = {
        "SYNTAX_ERROR": "Syntax Errors (py_compile)",
        "DATETIME_UTCNOW": "datetime.utcnow() usage",
        "DATETIME_NAIVE": "datetime.now() without timezone",
        "BARE_EXCEPT": "Bare except: blocks",
        "WRONG_MODEL": "Hardcoded wrong Ollama model",
        "WINDOWS_PATH": "Windows paths on Linux system",
        "OLD_CAMOUFOX_PATH": "Old Camoufox path",
        "NO_TIMEOUT": "subprocess call without timeout",
        "FILE_HANDLE_LEAK": "Potential file handle leak",
        "HARDCODED_SECRET": "Possible hardcoded secret",
        "MISSING_TZ_IMPORT": "Missing timezone import",
        "READ_ERROR": "File read error",
    }

    for cat, items in sorted(categories.items()):
        label = cat_labels.get(cat, cat)
        print(f"--- {label} ({len(items)} found) ---")
        for fp, line, detail in items:
            short_fp = fp.replace("/opt/titan/", "")
            if line > 0:
                print(f"  {short_fp}:{line}: {detail}")
            else:
                print(f"  {short_fp}: {detail}")
        print()

    print("=" * 70)
    total = len(issues)
    critical = len(categories.get("SYNTAX_ERROR", []))
    print(f"TOTAL ISSUES: {total} ({critical} critical syntax errors)")
    if critical == 0:
        print("STATUS: NO SYNTAX ERRORS — issues above are warnings/improvements")
    else:
        print("STATUS: CRITICAL — syntax errors must be fixed")
    print("=" * 70)


if __name__ == "__main__":
    main()
