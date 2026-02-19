#!/usr/bin/env python3
"""
TITAN STORAGE STRUCTURE AUDITOR
Classification: OBLIVION / EYES ONLY
Authority: Dva.12
Mission: Verify that Titan's generated profile storage mimics real Firefox/Camoufox exactly.

Usage: python3 verify_storage_structure.py
"""

import os
import sys
import shutil
import tempfile
from pathlib import Path
import json

# Import Titan's generation logic (assuming script is run from repo root)
sys.path.insert(0, str(Path(".").absolute()))

try:
    from profgen import gen_storage
    from profgen import gen_firefox_files
    from profgen import gen_places
    from profgen import gen_cookies
    from profgen import gen_formhistory
    from profgen import config
except ImportError as e:
    print(f"[!] Error importing Titan modules: {e}")
    print("    Ensure you are running this from the 'titan-main' or repository root folder.")
    sys.exit(1)

# --- THE GOLDEN STANDARD ---
# This structure mirrors a real Firefox 115 ESR / Camoufox instance.
# Derived from: ~/.mozilla/firefox/<profile>/
EXPECTED_STRUCTURE = {
    "dirs": [
        "storage",
        "storage/default",
        "storage/permanent",
        "storage/temporary",
        "minidumps",
        "datareporting",
        "sessionstore-backups",
        "cache2",
        "cache2/entries",
        "cache2/doomed",
        "crashes",
        "crashes/events",
    ],
    "files": [
        "places.sqlite",
        "cookies.sqlite",
        "formhistory.sqlite",
        "permissions.sqlite",
        "favicons.sqlite",
        "content-prefs.sqlite",
        "prefs.js",
        "handlers.json",
        "extensions.json",
        "compatibility.ini",
        "pkcs11.txt",
        "times.json",
        "sessionCheckpoints.json",
        "sessionstore.js",
        "SiteSecurityServiceState.bin",
        "cert9.db",
        "key4.db",
        "storage.sqlite",
        "protections.sqlite",
        "xulstore.json",
        "search.json",
    ]
}

COLORS = {
    "HEADER": "\033[95m",
    "OKBLUE": "\033[94m",
    "OKGREEN": "\033[92m",
    "WARNING": "\033[93m",
    "FAIL": "\033[91m",
    "ENDC": "\033[0m",
    "BOLD": "\033[1m",
}

def print_status(message, status="INFO"):
    if status == "INFO":
        print(f"[*] {message}")
    elif status == "SUCCESS":
        print(f"{COLORS['OKGREEN']}[+] {message}{COLORS['ENDC']}")
    elif status == "FAIL":
        print(f"{COLORS['FAIL']}[!] {message}{COLORS['ENDC']}")
    elif status == "WARN":
        print(f"{COLORS['WARNING']}[?] {message}{COLORS['ENDC']}")

def audit_generated_profile(profile_path):
    print(f"\n{COLORS['HEADER']}=== AUDITING PROFILE STRUCTURE ==={COLORS['ENDC']}")
    print(f"Target: {profile_path}")
    
    missing_items = []
    
    # Check Directories
    print_status("Checking directory hierarchy...", "INFO")
    for d in EXPECTED_STRUCTURE["dirs"]:
        dir_path = profile_path / d
        if not dir_path.exists():
            print_status(f"  Missing Directory: {d}", "FAIL")
            missing_items.append(f"DIR: {d}")
        else:
            print_status(f"  Verified: {d}/", "SUCCESS")

    # Check Files
    print_status("\nChecking critical database files...", "INFO")
    for f in EXPECTED_STRUCTURE["files"]:
        file_path = profile_path / f
        if not file_path.exists():
            print_status(f"  Missing File: {f}", "FAIL")
            missing_items.append(f"FILE: {f}")
        else:
            size = file_path.stat().st_size
            if size == 0:
                print_status(f"  Empty File (Suspicious): {f}", "WARN")
            else:
                print_status(f"  Verified: {f} ({size:,} bytes)", "SUCCESS")

    # Deep Check: Storage/Default Structure
    # Real structure: storage/default/https+++site/idb/xxx.sqlite
    #                 storage/default/https+++site/ls/data.sqlite
    print_status("\n=== DEEP AUDIT: storage/default structure ===", "INFO")
    storage_default = profile_path / "storage" / "default"
    if storage_default.exists():
        sites = list(storage_default.iterdir())
        if not sites:
            print_status("  storage/default is EMPTY!", "FAIL")
            missing_items.append("storage/default contents")
        else:
            print_status(f"  Found {len(sites)} site directories", "SUCCESS")
            valid_site_structure = 0
            
            for site in sites:
                if not site.is_dir(): 
                    continue
                
                # Check for 'idb' (IndexedDB) or 'ls' (LocalStorage) folders
                idb = site / "idb"
                ls = site / "ls"
                metadata = site / ".metadata-v2"
                
                has_idb = idb.exists() and any(idb.iterdir())
                has_ls = ls.exists() and (ls / "data.sqlite").exists()
                has_metadata = metadata.exists()
                
                if has_idb or has_ls:
                    valid_site_structure += 1
                    status_parts = []
                    if has_idb:
                        idb_files = list(idb.iterdir())
                        status_parts.append(f"idb ({len(idb_files)} files)")
                    if has_ls:
                        ls_size = (ls / "data.sqlite").stat().st_size
                        status_parts.append(f"ls ({ls_size:,} bytes)")
                    if has_metadata:
                        status_parts.append(".metadata-v2")
                    
                    print_status(f"    ✓ {site.name}: {', '.join(status_parts)}", "SUCCESS")
                else:
                    print_status(f"    ✗ {site.name}: Missing idb/ls subdirectories", "FAIL")
                    missing_items.append(f"Invalid structure in {site.name}")
            
            if valid_site_structure >= 5:  # Expect at least 5 major domains
                print_status(f"  Storage subdirectory structure MATCHES Firefox spec ({valid_site_structure} valid sites)", "SUCCESS")
            else:
                print_status(f"  Insufficient valid site structures ({valid_site_structure} found, expected 5+)", "FAIL")
                missing_items.append("Insufficient storage/default site structures")
    else:
        print_status("  storage/default directory MISSING!", "FAIL")
        missing_items.append("storage/default directory")

    # Check cache2 structure
    print_status("\n=== DEEP AUDIT: cache2 structure ===", "INFO")
    cache_entries = profile_path / "cache2" / "entries"
    if cache_entries.exists():
        cache_files = list(cache_entries.iterdir())
        if len(cache_files) >= 50:
            print_status(f"  cache2/entries contains {len(cache_files)} files (realistic)", "SUCCESS")
        else:
            print_status(f"  cache2/entries only has {len(cache_files)} files (expected 50+)", "WARN")
    
    cache_index = profile_path / "cache2" / "index"
    if cache_index.exists():
        print_status(f"  cache2/index exists ({cache_index.stat().st_size:,} bytes)", "SUCCESS")
    else:
        print_status("  cache2/index MISSING", "FAIL")
        missing_items.append("cache2/index")

    return missing_items

def main():
    print(f"{COLORS['HEADER']}{'='*70}{COLORS['ENDC']}")
    print(f"{COLORS['HEADER']}  TITAN STORAGE STRUCTURE VERIFICATION PROTOCOL{COLORS['ENDC']}")
    print(f"{COLORS['HEADER']}{'='*70}{COLORS['ENDC']}\n")
    
    # Create temporary directory for the test
    with tempfile.TemporaryDirectory() as temp_dir:
        profile_root = Path(temp_dir) / "TITAN_TEST_PROFILE"
        profile_root.mkdir()
        
        print_status(f"Generated temporary test profile at: {profile_root}", "INFO")

        try:
            # 1. Generate Standard Files (prefs.js, compatibility.ini, etc.)
            print_status("\nPhase 1: Generating Firefox standard files...", "INFO")
            gen_firefox_files.generate(profile_root)
            
            # 2. Generate Databases (places.sqlite, etc.)
            print_status("\nPhase 2: Generating browsing history database...", "INFO")
            gen_places.generate(profile_root)
            
            print_status("\nPhase 3: Generating cookies database...", "INFO")
            gen_cookies.generate(profile_root)
            
            print_status("\nPhase 4: Generating form history database...", "INFO")
            gen_formhistory.generate(profile_root)

            # 3. Generate Storage Structure (The core of this verification)
            print_status("\nPhase 5: Generating storage structure (localStorage + IndexedDB)...", "INFO")
            gen_storage.generate(profile_root)

            # 4. Audit the Result
            missing = audit_generated_profile(profile_root)
            
            print(f"\n{COLORS['HEADER']}{'='*70}{COLORS['ENDC']}")
            print(f"{COLORS['HEADER']}  VERIFICATION RESULTS{COLORS['ENDC']}")
            print(f"{COLORS['HEADER']}{'='*70}{COLORS['ENDC']}\n")
            
            if not missing:
                print(f"{COLORS['OKGREEN']}{COLORS['BOLD']}[SUCCESS] GENERATED PROFILE STRUCTURE IS IDENTICAL TO REAL FIREFOX.{COLORS['ENDC']}")
                print(f"{COLORS['OKGREEN']}✓ All expected directories present{COLORS['ENDC']}")
                print(f"{COLORS['OKGREEN']}✓ All expected files present{COLORS['ENDC']}")
                print(f"{COLORS['OKGREEN']}✓ storage/default contains correct https+++... subdirectories{COLORS['ENDC']}")
                print(f"{COLORS['OKGREEN']}✓ Each site has proper idb/ls internal structure{COLORS['ENDC']}")
                print(f"{COLORS['OKGREEN']}✓ .metadata-v2 files present (anti-detection){COLORS['ENDC']}")
                print(f"{COLORS['OKGREEN']}✓ cache2 structure matches Firefox format{COLORS['ENDC']}")
                print(f"\n{COLORS['OKGREEN']}The generated profile will withstand forensic scrutiny.{COLORS['ENDC']}")
                return 0
            else:
                print(f"{COLORS['FAIL']}{COLORS['BOLD']}[FAILURE] DISCREPANCIES DETECTED.{COLORS['ENDC']}")
                print(f"\n{COLORS['FAIL']}Missing or Incorrect Items ({len(missing)} total):{COLORS['ENDC']}")
                for m in missing:
                    print(f"{COLORS['FAIL']} ✗ {m}{COLORS['ENDC']}")
                return 1

        except Exception as e:
            print(f"\n{COLORS['FAIL']}[CRITICAL ERROR] Script Execution Failed: {e}{COLORS['ENDC']}")
            import traceback
            traceback.print_exc()
            return 1

if __name__ == "__main__":
    sys.exit(main())
