#!/usr/bin/env python3
"""
Fix remaining subprocess calls missing timeout.
This version reads the FULL call block (all parens balanced) before checking.
Also fixes malformed timeout placement from previous script (e.g. newline before timeout).
"""
import os
import re

SCAN_DIRS = ["/opt/titan/core", "/opt/titan/apps", "/opt/titan/testing"]
fixes = 0
files_modified = []

def process_file(fp):
    global fixes
    with open(fp, "r") as f:
        content = f.read()
    
    original = content
    lines = content.split("\n")
    new_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Skip comments
        if line.strip().startswith("#"):
            new_lines.append(line)
            i += 1
            continue
        
        # Detect subprocess call
        if re.search(r'subprocess\.(run|check_output|call|check_call)\(', line):
            # Collect FULL call block until parens balance
            block_lines = [line]
            depth = 0
            for ch in line:
                if ch == '(': depth += 1
                elif ch == ')': depth -= 1
            
            j = i + 1
            while depth > 0 and j < len(lines):
                block_lines.append(lines[j])
                for ch in lines[j]:
                    if ch == '(': depth += 1
                    elif ch == ')': depth -= 1
                j += 1
            
            block = "\n".join(block_lines)
            
            # Fix malformed timeout placement: "\n, timeout=30)" -> ", timeout=30\n)"
            # Pattern: line ends with value, next line starts with ", timeout=N)"
            fixed_block_lines = []
            for k, bl in enumerate(block_lines):
                # Fix case where previous fix put timeout on wrong line
                if re.match(r'^\s*,\s*timeout=\d+\)', bl.strip()):
                    # Merge with previous line
                    if fixed_block_lines:
                        prev = fixed_block_lines[-1].rstrip()
                        timeout_match = re.search(r'timeout=(\d+)', bl)
                        tv = timeout_match.group(0) if timeout_match else "timeout=30"
                        # Remove the standalone timeout line, add to prev
                        if prev.endswith(","):
                            fixed_block_lines[-1] = prev + f" {tv}"
                        else:
                            fixed_block_lines[-1] = prev + f", {tv}"
                        # Keep the closing paren on its own line with proper indent
                        indent = len(bl) - len(bl.lstrip())
                        fixed_block_lines.append(" " * indent + ")")
                        fixes += 1
                        continue
                fixed_block_lines.append(bl)
            
            block_lines = fixed_block_lines
            block = "\n".join(block_lines)
            
            # Now check if timeout is truly missing
            if "timeout=" not in block:
                # Determine timeout
                tv = "30"
                if "clang" in block: tv = "120"
                elif "curl" in block: tv = "30"
                elif "ip " in block or "tc " in block: tv = "15"
                elif "lsmod" in block or "modprobe" in block: tv = "10"
                elif "ffmpeg" in block: tv = "60"
                
                # Find last line with closing paren
                for k in range(len(block_lines) - 1, -1, -1):
                    bl = block_lines[k]
                    if ")" in bl:
                        idx = bl.rfind(")")
                        before = bl[:idx].rstrip()
                        after = bl[idx:]
                        if before.endswith(","):
                            block_lines[k] = f"{before} timeout={tv}{after}"
                        else:
                            block_lines[k] = f"{before}, timeout={tv}{after}"
                        fixes += 1
                        short = fp.replace("/opt/titan/", "")
                        print(f"  +timeout={tv}: {short}:{i+1}")
                        break
            
            new_lines.extend(block_lines)
            i = j
            continue
        
        new_lines.append(line)
        i += 1
    
    new_content = "\n".join(new_lines)
    if new_content != original:
        with open(fp, "w") as f:
            f.write(new_content)
        files_modified.append(fp)

def main():
    print("=" * 60)
    print("FIXING REMAINING SUBPROCESS TIMEOUTS")
    print("=" * 60)
    
    for d in SCAN_DIRS:
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if fn.endswith(".py"):
                process_file(os.path.join(d, fn))
    
    print(f"\nFixes: {fixes}")
    print(f"Files modified: {len(files_modified)}")
    
    # Verify
    import py_compile
    errors = 0
    for fp in files_modified:
        try:
            py_compile.compile(fp, doraise=True)
        except py_compile.PyCompileError as e:
            print(f"  SYNTAX ERROR: {fp}: {str(e)[:150]}")
            errors += 1
    
    if files_modified:
        if errors == 0:
            print(f"All {len(files_modified)} modified files compile OK")
        else:
            print(f"WARNING: {errors} syntax errors!")
    else:
        print("No changes needed")

if __name__ == "__main__":
    main()
