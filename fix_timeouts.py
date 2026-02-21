#!/usr/bin/env python3
"""
Fix remaining subprocess calls missing timeout= on VPS.
Handles multi-line subprocess.run() calls that the previous script missed.
"""
import os
import re

FIXES = 0

def add_timeout_to_subprocess(content, fp):
    """Find all subprocess.run/check_output calls and add timeout if missing."""
    global FIXES
    lines = content.split("\n")
    result = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Skip comments
        if line.strip().startswith("#"):
            result.append(line)
            i += 1
            continue
        
        # Detect subprocess call start
        match = re.search(r'subprocess\.(run|check_output|call|check_call)\(', line)
        if match:
            # Collect full call block
            block_start = i
            block_lines = [line]
            paren_depth = 0
            for ch in line:
                if ch == '(':
                    paren_depth += 1
                elif ch == ')':
                    paren_depth -= 1
            
            j = i + 1
            while paren_depth > 0 and j < len(lines):
                block_lines.append(lines[j])
                for ch in lines[j]:
                    if ch == '(':
                        paren_depth += 1
                    elif ch == ')':
                        paren_depth -= 1
                j += 1
            
            block_text = "\n".join(block_lines)
            
            if "timeout=" not in block_text:
                # Determine timeout value
                timeout_val = "30"
                if "clang" in block_text or "compile" in block_text.lower():
                    timeout_val = "120"
                elif "curl" in block_text:
                    timeout_val = "30"
                elif "ip link" in block_text or "ip " in block_text:
                    timeout_val = "15"
                elif "tc " in block_text or "bpf" in block_text.lower():
                    timeout_val = "15"
                elif "lsmod" in block_text or "modprobe" in block_text:
                    timeout_val = "10"
                elif "v4l2" in block_text:
                    timeout_val = "10"
                
                # Find the line with the final closing paren
                for k in range(len(block_lines) - 1, -1, -1):
                    bl = block_lines[k]
                    if ")" in bl:
                        # Find the position of the last significant )
                        idx = bl.rfind(")")
                        before = bl[:idx].rstrip()
                        after = bl[idx:]
                        
                        if before.endswith(","):
                            block_lines[k] = f"{before} timeout={timeout_val}{after}"
                        else:
                            block_lines[k] = f"{before}, timeout={timeout_val}{after}"
                        
                        FIXES += 1
                        short = fp.replace("/opt/titan/", "")
                        print(f"  FIXED: {short}:{block_start+1} +timeout={timeout_val}")
                        break
                
                result.extend(block_lines)
                i = j
                continue
        
        result.append(line)
        i += 1
    
    return "\n".join(result)


def main():
    global FIXES
    
    files = [
        "/opt/titan/core/kyc_core.py",
        "/opt/titan/core/kyc_enhanced.py",
        "/opt/titan/core/network_shield.py",
        "/opt/titan/core/network_shield_loader.py",
        "/opt/titan/core/ollama_bridge.py",
        "/opt/titan/core/target_discovery.py",
        "/opt/titan/apps/app_cerberus.py",
    ]
    
    print("Fixing remaining subprocess timeout gaps...")
    print()
    
    for fp in files:
        if not os.path.exists(fp):
            continue
        with open(fp, "r") as f:
            content = f.read()
        
        new_content = add_timeout_to_subprocess(content, fp)
        
        if new_content != content:
            with open(fp, "w") as f:
                f.write(new_content)
    
    print(f"\nTotal timeout fixes: {FIXES}")
    
    # Verify
    print("\nVerifying syntax...")
    import py_compile
    errors = 0
    for fp in files:
        if not os.path.exists(fp):
            continue
        try:
            py_compile.compile(fp, doraise=True)
        except py_compile.PyCompileError as e:
            print(f"  SYNTAX ERROR: {fp}: {e}")
            errors += 1
    
    if errors == 0:
        print("All files compile OK")
    else:
        print(f"{errors} files have syntax errors!")


if __name__ == "__main__":
    main()
