"""
TITAN V8.1 SINGULARITY — Profile Generator Package

Unified entry point for generating forensically clean Firefox profiles.
Calls all sub-generators in the correct order with proper error handling.

Usage:
    from profgen import generate_profile
    generate_profile(Path("/path/to/profile"))
"""
from pathlib import Path
import logging
import time

logger = logging.getLogger("TITAN-PROFGEN")


def generate_profile(profile_path, skip_storage=False):
    """
    Generate a complete forensically clean Firefox profile.

    Args:
        profile_path: Path to the target profile directory.
        skip_storage: If True, skip the heavy localStorage generation (for testing).

    Returns:
        dict with generation statistics.
    """
    from . import gen_places
    from . import gen_cookies
    from . import gen_storage
    from . import gen_firefox_files
    from . import gen_formhistory
    from .config import (leave_wal_ghosts, stagger_mtime, inject_freelist_pages,
                         AGE_DAYS)
    import random

    profile_path = Path(profile_path)
    profile_path.mkdir(parents=True, exist_ok=True)

    stats = {}
    t0 = time.time()

    print(f"\n{'='*60}")
    print(f"  TITAN PROFILE GENERATOR — V8.1")
    print(f"  Target: {profile_path}")
    print(f"{'='*60}\n")

    # 1. Browsing history + bookmarks + downloads
    stats["history_visits"] = gen_places.generate(profile_path)

    # 2. Cookies (spread creation times)
    stats["cookies"] = gen_cookies.generate(profile_path)

    # 3. localStorage (500MB+ with realistic keys)
    if not skip_storage:
        stats["storage_entries"] = gen_storage.generate(profile_path)
    else:
        stats["storage_entries"] = 0
        print("[3/12] localStorage — SKIPPED (skip_storage=True)")

    # 4. Form history (diverse entries)
    stats["form_entries"] = gen_formhistory.generate(profile_path)

    # 5-12. Standard Firefox files (prefs.js, extensions, certs, cache, etc.)
    gen_firefox_files.generate(profile_path)

    # ══════════════════════════════════════════════════════════════
    # ANTI-DETECTION PASS: WAL ghosts, mtime stagger, fragmentation
    # ══════════════════════════════════════════════════════════════
    print("[AD] Anti-detection hardening pass...")

    # Every .sqlite file needs WAL/SHM ghosts and organic mtime
    _db_age_map = {
        "places.sqlite":        AGE_DAYS,
        "cookies.sqlite":       AGE_DAYS - random.randint(0, 3),
        "formhistory.sqlite":   AGE_DAYS - random.randint(5, 15),
        "favicons.sqlite":      AGE_DAYS - random.randint(1, 5),
        "permissions.sqlite":   AGE_DAYS - random.randint(10, 30),
        "content-prefs.sqlite": AGE_DAYS - random.randint(20, 40),
        "storage.sqlite":       AGE_DAYS - random.randint(2, 10),
        "protections.sqlite":   AGE_DAYS - random.randint(5, 15),
        "webappsstore.sqlite":  AGE_DAYS - random.randint(0, 5),
    }
    for db_name, age in _db_age_map.items():
        db_file = profile_path / db_name
        if db_file.exists():
            leave_wal_ghosts(db_file)
            inject_freelist_pages(db_file, random.randint(2, 8))
            stagger_mtime(db_file, max(age, 1))

    # Stagger non-database files with realistic ages
    _file_age_map = {
        "prefs.js":              random.randint(0, 3),
        "user.js":               AGE_DAYS - random.randint(0, 10),
        "times.json":            AGE_DAYS,
        "compatibility.ini":     random.randint(0, 7),
        "extensions.json":       AGE_DAYS - random.randint(0, 5),
        "extension-settings.json": AGE_DAYS - random.randint(0, 5),
        "handlers.json":         AGE_DAYS - random.randint(10, 30),
        "xulstore.json":         random.randint(0, 14),
        "search.json":           AGE_DAYS - random.randint(0, 10),
        "sessionstore.js":       0,
        "containers.json":       AGE_DAYS - random.randint(0, 3),
        "logins.json":           AGE_DAYS - random.randint(0, 5),
        "signedInUser.json":     AGE_DAYS - random.randint(0, 5),
        "SiteSecurityServiceState.bin": random.randint(0, 7),
        "SecurityPreloadState.bin": random.randint(0, 7),
        "pkcs11.txt":            AGE_DAYS,
        "sessionCheckpoints.json": 0,
        "addonStartup.json.lz4": random.randint(0, 3),
    }
    for fname, age in _file_age_map.items():
        fpath = profile_path / fname
        if fpath.exists():
            stagger_mtime(fpath, max(age, 0))

    # localStorage data.sqlite files
    sdir = profile_path / "storage" / "default"
    if sdir.exists():
        for origin_dir in sdir.iterdir():
            ls_db = origin_dir / "ls" / "data.sqlite"
            if ls_db.exists():
                leave_wal_ghosts(ls_db)
                stagger_mtime(ls_db, random.randint(1, AGE_DAYS // 2))

    print("[AD] Anti-detection pass complete")

    elapsed = time.time() - t0
    stats["elapsed_seconds"] = round(elapsed, 1)

    print(f"\n{'='*60}")
    print(f"  PROFILE GENERATION COMPLETE")
    print(f"  Visits: {stats['history_visits']}  |  Cookies: {stats['cookies']}")
    print(f"  Storage entries: {stats['storage_entries']}  |  Form entries: {stats['form_entries']}")
    print(f"  Time: {stats['elapsed_seconds']}s")
    print(f"{'='*60}\n")

    return stats
