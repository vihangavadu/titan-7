import os
import sys
import hashlib
import json

# === TITAN OS // PRE-FLIGHT INTEGRITY SCANNER ===
# AUTHORITY: KINETIC
# TARGET: V7 ISO BUILD READINESS

REQUIRED_ASSETS = {
    "CORE": [
        "titan/titan_core.py",
        "titan/__init__.py",
        "titan/profile_isolation.py",
        "titan/TITAN_CORE_v5.py"
    ],
    "STEALTH_KERNEL": [
        "titan/hardware_shield/titan_hw.c",
        "titan/hardware_shield/dkms.conf",
        "titan/hardware_shield/Makefile",
        "titan/ebpf/network_shield.c",
        "titan/ebpf/tcp_fingerprint.c"
    ],
    "GENESIS_ENGINE": [
        "profgen/__init__.py",
        "profgen/config.py",
        "profgen/gen_firefox_files.py",
        "profgen/gen_places.py",
        "profgen/gen_cookies.py",
        "profgen/gen_storage.py",
        "profgen/gen_formhistory.py"
    ],
    "ISO_CONFIG": [
        "iso/auto/config",
        "iso/config/includes.chroot/etc/nftables.conf",
        "iso/config/includes.chroot/etc/sysctl.d/99-titan-hardening.conf"
    ],
    "PATCHERS": [
        "scripts/titan_finality_patcher.py",
        "scripts/build_iso.sh"
    ]
}

def print_status(component, status, message=""):
    color = "\033[92m" if status == "OK" or status == "SECURE" or status == "EXECUTABLE" or status == "VALID" else "\033[91m"
    if status == "WARNING": color = "\033[93m"
    reset = "\033[0m"
    print(f"[{component.ljust(25)}] {color}{status.ljust(10)}{reset} {message}")

def check_file_existence(filepath):
    if os.path.exists(filepath):
        return True
    return False

def scan_for_placeholders(filepath):
    """Scans config files for dangerous default values."""
    dangerous_tokens = ["YOUR_API_KEY", "CHANGE_ME", "0.0.0.0", "default_password"]
    found = []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            for token in dangerous_tokens:
                if token in content:
                    found.append(token)
    except Exception:
        pass
    return found

def verify_dkms_config():
    """Verifies that the Kernel Module is correctly configured for build."""
    dkms_path = "titan/hardware_shield/dkms.conf"
    if not os.path.exists(dkms_path):
        return False
    with open(dkms_path, 'r') as f:
        content = f.read()
        # Adjusted to match the actual file content which might have different formatting
        if "PACKAGE_NAME=\"titan-hw\"" in content and ("BUILT_MODULE_NAME=\"titan_hw\"" in content or "BUILT_MODULE_NAME[0]=\"titan_hw\"" in content):
            return True
    return False

def main():
    print("\n" + "="*70)
    print(" L U C I D   T I T A N   O S   //   D E E P   S C A N ")
    print("="*70 + "\n")
    
    all_systems_go = True
    
    # 1. ASSET VERIFICATION
    print(">>> PHASE 1: ASSET INTEGRITY")
    for category, files in REQUIRED_ASSETS.items():
        for file in files:
            if check_file_existence(file):
                print_status(file.split('/')[-1], "OK")
            else:
                print_status(file.split('/')[-1], "MISSING", f"CRITICAL: {file} not found")
                all_systems_go = False
                
    # 2. CONFIGURATION SAFETY
    print("\n>>> PHASE 2: CONFIGURATION SANITIZATION")
    config_files = ["iso/config/includes.chroot/opt/titan/config/titan.env", "titan_v6_cloud_brain/docker-compose.yml"]
    for conf in config_files:
        if os.path.exists(conf):
            issues = scan_for_placeholders(conf)
            if issues:
                print_status(conf, "WARNING", f"Found tokens: {issues}")
                # Warnings don't stop the build, but operator should know
            else:
                print_status(conf, "SECURE")
        else:
             print_status(conf, "MISSING", "Optional config not found")
                
    # 3. KERNEL MODULE CHECK
    print("\n>>> PHASE 3: KERNEL MASKING")
    if verify_dkms_config():
        print_status("DKMS Config", "VALID", "Kernel module ready for injection")
    else:
        print_status("DKMS Config", "INVALID", "Check dkms.conf syntax or existence")
        all_systems_go = False
        
    # 4. EXECUTABLE PERMISSIONS
    print("\n>>> PHASE 4: EXECUTION READINESS")
    scripts = ["scripts/build_iso.sh", "scripts/titan_finality_patcher.py", "scripts/verify_v7_readiness.py"]
    for script in scripts:
        if os.path.exists(script):
            if os.access(script, os.X_OK):
                print_status(script, "EXECUTABLE")
            else:
                print_status(script, "LOCKED", "Run: chmod +x " + script)
                all_systems_go = False
        else:
            print_status(script, "MISSING")
            all_systems_go = False

    print("\n" + "="*70)
    if all_systems_go:
        print(" [ SYSTEM STATUS: GREEN ] - READY FOR ISO COMPILATION")
        print(" RECOMMENDATION: Execute 'scripts/titan_finality_patcher.py' before building.")
    else:
        print(" [ SYSTEM STATUS: RED ] - ABORT BUILD. RESOLVE CRITICAL ERRORS.")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
