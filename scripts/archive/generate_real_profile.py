"""
TITAN V8.1 — Forensically Clean Firefox Profile Generator
Produces a genuine Firefox profile directory with NO antidetect artifacts.
All files match standard Firefox profile format exactly.
"""
import sys, os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from profgen.config import PROFILE_UUID, STORAGE_MB, AGE_DAYS, PERSONA_NAME, NOW, CREATED
from profgen import gen_places, gen_cookies, gen_storage, gen_formhistory, gen_firefox_files

OUTPUT = Path(__file__).parent / "profiles" / PROFILE_UUID

def main():
    print("=" * 50)
    print("TITAN V8.1 — FORENSICALLY CLEAN PROFILE GENERATOR")
    print(f"UUID: {PROFILE_UUID}")
    print(f"Persona: {PERSONA_NAME}")
    print(f"Age: {AGE_DAYS} days | Target: {STORAGE_MB}MB+")
    print(f"Created: {CREATED.strftime('%Y-%m-%d')} -> {NOW.strftime('%Y-%m-%d')}")
    print("=" * 50)

    OUTPUT.mkdir(parents=True, exist_ok=True)

    # Core Firefox databases
    hist = gen_places.generate(OUTPUT)
    cookies = gen_cookies.generate(OUTPUT)
    storage = gen_storage.generate(OUTPUT)
    forms = gen_formhistory.generate(OUTPUT)

    # All standard Firefox files (no antidetect artifacts)
    gen_firefox_files.generate(OUTPUT)

    # Calculate total size
    total = sum(f.stat().st_size for f in OUTPUT.rglob("*") if f.is_file())

    print()
    print("=" * 50)
    print("PROFILE COMPLETE — FORENSICALLY CLEAN")
    print("=" * 50)
    print(f"  Path:        {OUTPUT}")
    print(f"  Total Size:  {total/(1024*1024):.1f}MB")
    print(f"  History:     {hist} entries (varied visit types + subpages)")
    print(f"  Cookies:     {cookies} (spread creation times)")
    print(f"  localStorage:{storage} entries (realistic keys)")
    print(f"  FormHistory: {forms} entries (searches + logins + misc)")
    print()
    print("  Standard Firefox files present:")
    ff = ["places.sqlite","cookies.sqlite","formhistory.sqlite",
          "favicons.sqlite","permissions.sqlite","content-prefs.sqlite",
          "prefs.js","times.json","compatibility.ini","extensions.json",
          "handlers.json","xulstore.json","search.json","sessionstore.js",
          "SiteSecurityServiceState.bin","cert9.db","key4.db","pkcs11.txt",
          "sessionCheckpoints.json"]
    for f in ff:
        exists = (OUTPUT / f).exists()
        print(f"    {'[OK]' if exists else '[!!]'} {f}")
    print()
    print("  NO antidetect artifacts:")
    bad = ["commerce_tokens.json","hardware_profile.json",
           "fingerprint_config.json","profile_metadata.json",
           "profile.json","history.json","cookies.json"]
    for f in bad:
        exists = (OUTPUT / f).exists()
        print(f"    {'[!!] FOUND' if exists else '[OK] absent'} {f}")
    print("=" * 50)

if __name__ == "__main__":
    main()
