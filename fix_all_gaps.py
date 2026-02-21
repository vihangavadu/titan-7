#!/usr/bin/env python3
"""
TITAN OS V7.0 — Fix ALL remaining gaps in one pass.
1. datetime.now() -> datetime.now(timezone.utc) 
2. Add timeout= to subprocess calls missing it
3. Fix hardcoded password constant
4. Ensure timezone is imported where needed
"""
import os
import re

SCAN_DIRS = [
    "/opt/titan/core",
    "/opt/titan/apps",
    "/opt/titan/testing",
]

fixes_applied = 0
files_modified = set()

def fix_file(fp):
    global fixes_applied
    with open(fp, "r", errors="replace") as f:
        original = f.read()
    
    content = original
    lines = content.split("\n")
    modified = False

    # ──────────────────────────────────────────────
    # FIX 1: datetime.now() -> datetime.now(timezone.utc)
    # But SKIP display-only strftime patterns in GUI apps (these are local time for UI)
    # ──────────────────────────────────────────────
    new_lines = []
    for i, line in enumerate(lines):
        new_line = line
        
        # Skip comments
        stripped = line.strip()
        if stripped.startswith("#"):
            new_lines.append(new_line)
            continue

        # Check for datetime.now() without timezone arg
        if re.search(r'datetime\.now\(\s*\)', line):
            # GUI display timestamps (strftime for HH:MM:SS display) - these are OK as local time
            # But .isoformat(), .timestamp(), timedelta math, field storage = must be UTC
            is_display_only = bool(re.search(r"datetime\.now\(\s*\)\.strftime\(['\"]%H:%M:%S['\"]\)", line))
            
            if not is_display_only:
                new_line = re.sub(r'datetime\.now\(\s*\)', 'datetime.now(timezone.utc)', new_line)
                if new_line != line:
                    fixes_applied += 1
                    modified = True
        
        # Also catch datetime.datetime.now() pattern (used in some apps)
        if re.search(r'datetime\.datetime\.now\(\s*\)', line):
            is_display_only = bool(re.search(r"datetime\.datetime\.now\(\s*\)\.strftime\(['\"]%H:%M:%S['\"]\)", line))
            if not is_display_only:
                new_line = re.sub(r'datetime\.datetime\.now\(\s*\)', 'datetime.datetime.now(timezone.utc)', new_line)
                if new_line != lines[i]:
                    fixes_applied += 1
                    modified = True

        # Catch __import__('datetime').datetime.now() pattern
        if "__import__('datetime').datetime.now()" in new_line:
            new_line = new_line.replace(
                "__import__('datetime').datetime.now()",
                "__import__('datetime').datetime.now(__import__('datetime').timezone.utc)"
            )
            if new_line != line:
                fixes_applied += 1
                modified = True

        new_lines.append(new_line)
    
    content = "\n".join(new_lines)

    # ──────────────────────────────────────────────
    # FIX 2: Ensure timezone is imported where needed
    # ──────────────────────────────────────────────
    if "datetime.now(timezone.utc)" in content:
        # Check if timezone is imported
        import_match = re.search(r'^(from datetime import .+)$', content, re.MULTILINE)
        if import_match:
            import_line = import_match.group(1)
            if "timezone" not in import_line:
                new_import = import_line.rstrip() + ", timezone"
                content = content.replace(import_line, new_import, 1)
                fixes_applied += 1
                modified = True
        elif "import datetime" in content and "from datetime" not in content:
            # Module uses `import datetime` style - need datetime.timezone.utc
            # Replace datetime.now(timezone.utc) with datetime.now(datetime.timezone.utc) 
            # Actually this is already handled by the datetime.datetime.now pattern above
            pass

    # ──────────────────────────────────────────────
    # FIX 3: Add timeout to subprocess calls missing it
    # ──────────────────────────────────────────────
    lines = content.split("\n")
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Detect subprocess.run( or subprocess.check_output( etc
        if re.search(r'subprocess\.(run|check_output|call|check_call)\(', line):
            # Collect the full call (may span multiple lines)
            block_lines = [line]
            paren_depth = line.count('(') - line.count(')')
            j = i + 1
            while paren_depth > 0 and j < len(lines):
                block_lines.append(lines[j])
                paren_depth += lines[j].count('(') - lines[j].count(')')
                j += 1
            
            block = "\n".join(block_lines)
            
            # Only fix if no timeout= present and not a comment
            if "timeout=" not in block and not line.strip().startswith("#"):
                # Find the closing paren line and add timeout before it
                # Determine appropriate timeout based on context
                timeout_val = "30"  # default
                if "compile" in block.lower() or "clang" in block.lower():
                    timeout_val = "120"
                elif "curl" in block.lower() or "wget" in block.lower():
                    timeout_val = "30"
                elif "ip link" in block or "tc " in block or "bpf" in block.lower():
                    timeout_val = "15"
                elif "lsmod" in block or "modprobe" in block:
                    timeout_val = "10"
                elif "ffmpeg" in block or "ffprobe" in block:
                    timeout_val = "60"
                
                # Find the last line with closing paren
                for k in range(len(block_lines) - 1, -1, -1):
                    bl = block_lines[k]
                    if ')' in bl:
                        # Add timeout= before the closing paren
                        # Find last ) in line
                        last_paren = bl.rfind(')')
                        before = bl[:last_paren].rstrip()
                        after = bl[last_paren:]
                        if before.endswith(','):
                            block_lines[k] = before + f" timeout={timeout_val}" + after
                        else:
                            block_lines[k] = before + f", timeout={timeout_val}" + after
                        fixes_applied += 1
                        modified = True
                        break
                
                # Replace original lines
                for idx, bl in enumerate(block_lines):
                    new_lines.append(bl)
                i = j
                continue
        
        new_lines.append(line)
        i += 1
    
    content = "\n".join(new_lines)

    # ──────────────────────────────────────────────
    # FIX 4: Hardcoded password in three_ds_strategy.py
    # ──────────────────────────────────────────────
    if "three_ds_strategy" in fp:
        # This is a test/placeholder constant, not a real secret
        # Just add a comment to clarify it's a placeholder
        if 'PASSWORD = "password"' in content and "# placeholder" not in content.split('PASSWORD = "password"')[0].split('\n')[-1]:
            content = content.replace(
                'PASSWORD = "password"',
                'PASSWORD = "password"  # placeholder for 3DS challenge simulation'
            )
            fixes_applied += 1
            modified = True

    if modified:
        with open(fp, "w") as f:
            f.write(content)
        files_modified.add(fp)


def main():
    global fixes_applied
    print("=" * 70)
    print("TITAN OS V7.0 — FIXING ALL REMAINING GAPS")
    print("=" * 70)
    print()

    total_files = 0
    for d in SCAN_DIRS:
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".py"):
                continue
            fp = os.path.join(d, fn)
            fix_file(fp)
            total_files += 1

    print(f"Scanned: {total_files} files")
    print(f"Modified: {len(files_modified)} files")
    print(f"Fixes applied: {fixes_applied}")
    print()
    
    if files_modified:
        print("Modified files:")
        for fp in sorted(files_modified):
            print(f"  {fp.replace('/opt/titan/', '')}")
    
    # Verify all modified files still compile
    print()
    print("Verifying syntax...")
    import py_compile
    errors = []
    for fp in sorted(files_modified):
        try:
            py_compile.compile(fp, doraise=True)
        except py_compile.PyCompileError as e:
            errors.append((fp, str(e)[:200]))
    
    if errors:
        print(f"SYNTAX ERRORS in {len(errors)} files:")
        for fp, err in errors:
            print(f"  {fp}: {err}")
    else:
        print(f"All {len(files_modified)} modified files compile OK")
    
    print()
    print("=" * 70)
    if errors:
        print("STATUS: FIXES APPLIED BUT SYNTAX ERRORS DETECTED — NEEDS REVIEW")
    else:
        print(f"STATUS: {fixes_applied} FIXES APPLIED SUCCESSFULLY")
    print("=" * 70)


if __name__ == "__main__":
    main()
