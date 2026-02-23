#!/usr/bin/env python3
"""
Apply all 10 V8.3 gap fixes to Titan OS VPS.
Run as: python3 apply_v83_gaps.py
"""
import re

def patch_file(path, patches):
    """Apply list of (old, new) patches to a file."""
    content = open(path).read()
    for old, new in patches:
        if old in content:
            content = content.replace(old, new, 1)
            print(f"  [PATCHED] {path}: applied patch")
        else:
            print(f"  [SKIP]    {path}: pattern not found (already applied?)")
    open(path, 'w').write(content)

print("\n=== TITAN OS V8.3 GAP FIXER ===\n")

# ─── FIX 1: privacy.trackingprotection.enabled — should be False not True ───
# Real Firefox users have tracking protection OFF by default (it's a red flag
# when it's True because it signals a privacy-conscious setup, not a normal user)
print("[1/10] Fix privacy.trackingprotection.enabled in profile_realism_engine.py")
patch_file('/opt/titan/core/profile_realism_engine.py', [
    ("p('privacy.trackingprotection.enabled',True)",
     "p('privacy.trackingprotection.enabled',False)"),
])

# ─── FIX 2: gen_storage.py — O(n²) JSON sizing fix (devin branch) ────────────
print("[2/10] Fix gen_storage.py O(n²) JSON sizing loop")
patch_file('/opt/titan/profgen/gen_storage.py', [
    # Convert ga_domains list to set for O(1) lookup
    ('ga_domains = ["youtube.com","reddit.com","amazon.com","eneba.com",\n                     "g2a.com","newegg.com","bestbuy.com","steampowered.com",\n                     "ubereats.com","linkedin.com"]',
     'ga_domains = {"youtube.com","reddit.com","amazon.com","eneba.com","g2a.com","newegg.com","bestbuy.com","steampowered.com","ubereats.com","linkedin.com"}'),
    # Fix O(n²) while loop — hoist fill_keys and use current_size tracking
    ('            while len(json.dumps(pad_obj)) < target_size:',
     '            current_size = len(json.dumps(pad_obj))\n            while current_size < target_size:'),
    # After pad_obj["data"][fk] = ... add current_size update
    ('                pad_obj["data"][fk] = secrets.token_hex(random.randint(32, 256))',
     '                hex_val = secrets.token_hex(random.randint(32, 256))\n                pad_obj["data"][fk] = hex_val\n                current_size += len(fk) + len(hex_val) + 6'),
])

# ─── FIX 3: genesis_core.py — Add Chrome 134 UA entries ──────────────────────
print("[3/10] Add Chrome 134 UA to genesis_core.py")
patch_file('/opt/titan/core/genesis_core.py', [
    # Add Chrome 134 alongside 133 in Windows UA list
    ('Chrome/133.0.0.0 Safari/537.36"\n                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"',
     'Chrome/133.0.0.0 Safari/537.36"\n                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"'),
])

# ─── FIX 4: fingerprint_injector.py — Firefox buildID spoof ──────────────────
print("[4/10] Add Firefox navigator.buildID spoof to fingerprint_injector.py")
FIREFOX_BUILDID_PATCH = '''
    def generate_firefox_buildid_script(self) -> str:
        """
        V8.3: Spoof navigator.buildID for Firefox profiles.
        Real Firefox exposes navigator.buildID as a 14-digit timestamp string.
        Without this, fingerprinters can detect that the browser is not real Firefox.
        """
        import hashlib
        seed = int(hashlib.sha256(self.config.profile_uuid.encode()).hexdigest()[:8], 16)
        # Generate a plausible Firefox build ID (YYYYMMDDHHMMSS format)
        # Use dates from Firefox 115-133 ESR/stable release range
        build_dates = [
            "20240101000000", "20240201000000", "20240301000000",
            "20240401000000", "20240501000000", "20240601000000",
            "20240701000000", "20240801000000", "20240901000000",
            "20241001000000", "20241101000000", "20241201000000",
            "20250101000000", "20250201000000", "20260212191108",
        ]
        build_id = build_dates[seed % len(build_dates)]
        return f"""
(function() {{
    'use strict';
    try {{
        Object.defineProperty(navigator, 'buildID', {{
            get: function() {{ return '{build_id}'; }},
            configurable: false,
            enumerable: true,
        }});
    }} catch(e) {{}}
}})();
"""

'''

# Insert before write_to_profile method
patch_file('/opt/titan/core/fingerprint_injector.py', [
    ('    def write_to_profile(self, profile_path: Path):',
     FIREFOX_BUILDID_PATCH + '    def write_to_profile(self, profile_path: Path):'),
])

# ─── FIX 5: fingerprint_injector.py — Chrome 134 brand version ───────────────
print("[5/10] Add Chrome 134 brand version to ClientHintsSpoofing")
patch_file('/opt/titan/core/fingerprint_injector.py', [
    ("    BRAND_VERSIONS = {\n        '133':",
     "    BRAND_VERSIONS = {\n        '134': {'brand': 'Chromium', 'version': '134', 'full_version': '134.0.6998.89', 'brands': [{'brand': 'Chromium', 'version': '134'}, {'brand': 'Google Chrome', 'version': '134'}, {'brand': 'Not-A.Brand', 'version': '99'}]},\n        '133':"),
])

# ─── FIX 6: profile_isolation.py — Add Camoufox launch wrapper ───────────────
print("[6/10] Add Camoufox isolation wrapper to profile_isolation.py")
CAMOUFOX_PATCH = '''

def launch_camoufox_isolated(profile_path: str, proxy_url: str = None,
                              headless: bool = False) -> 'subprocess.Popen':
    """
    V8.3: Launch Camoufox inside a Linux namespace isolation container.
    Combines profile_isolation.py namespace isolation with Camoufox browser launch.
    This prevents browser processes from leaking data outside the isolated environment.

    Args:
        profile_path: Path to the Firefox/Camoufox profile directory
        proxy_url: Optional SOCKS5/HTTP proxy URL (e.g. socks5://127.0.0.1:1080)
        headless: Run in headless mode

    Returns:
        subprocess.Popen handle for the isolated browser process
    """
    import subprocess
    import shutil

    camoufox_bin = shutil.which('camoufox') or '/opt/camoufox/camoufox'
    if not camoufox_bin or not __import__('os').path.exists(camoufox_bin):
        raise FileNotFoundError("Camoufox binary not found. Install at /opt/camoufox/camoufox")

    cmd = ['unshare', '--mount', '--pid', '--fork']
    cmd += [camoufox_bin, '--profile', profile_path]
    if headless:
        cmd += ['--headless']
    if proxy_url:
        cmd += ['--proxy-server', proxy_url]

    env = __import__('os').environ.copy()
    env['DISPLAY'] = env.get('DISPLAY', ':0')

    proc = subprocess.Popen(cmd, env=env)
    return proc


def launch_browser_isolated(profile_path: str, proxy_url: str = None) -> 'subprocess.Popen':
    """V8.3: Alias for launch_camoufox_isolated for integration_bridge compatibility."""
    return launch_camoufox_isolated(profile_path, proxy_url)

'''

patch_file('/opt/titan/core/profile_isolation.py', [
    ('if __name__ == "__main__":',
     CAMOUFOX_PATCH + '\nif __name__ == "__main__":'),
])

# ─── FIX 7: profile_isolation.py — Add bwrap (bubblewrap) support ────────────
print("[7/10] Add bubblewrap (bwrap) support to profile_isolation.py")
BWRAP_PATCH = '''

def launch_with_bwrap(cmd: list, profile_path: str = None) -> 'subprocess.Popen':
    """
    V8.3: Launch a process inside bubblewrap (bwrap) sandbox.
    More portable than unshare — works rootless without CAP_SYS_ADMIN.
    Provides mount, PID, network namespace isolation.

    Args:
        cmd: Command list to execute inside sandbox
        profile_path: Optional profile path to bind-mount read-write

    Returns:
        subprocess.Popen handle
    """
    import subprocess
    import shutil

    bwrap = shutil.which('bwrap')
    if not bwrap:
        raise FileNotFoundError("bubblewrap (bwrap) not installed. Run: apt install bubblewrap")

    bwrap_cmd = [
        bwrap,
        '--ro-bind', '/usr', '/usr',
        '--ro-bind', '/lib', '/lib',
        '--ro-bind', '/lib64', '/lib64',
        '--ro-bind', '/bin', '/bin',
        '--ro-bind', '/sbin', '/sbin',
        '--ro-bind', '/etc', '/etc',
        '--proc', '/proc',
        '--dev', '/dev',
        '--tmpfs', '/tmp',
        '--unshare-pid',
        '--unshare-net',
        '--die-with-parent',
    ]
    if profile_path:
        bwrap_cmd += ['--bind', profile_path, profile_path]

    bwrap_cmd += ['--'] + cmd
    return subprocess.Popen(bwrap_cmd)

'''

patch_file('/opt/titan/core/profile_isolation.py', [
    ('def launch_browser_isolated(profile_path: str, proxy_url: str = None)',
     BWRAP_PATCH + '\ndef launch_browser_isolated(profile_path: str, proxy_url: str = None)'),
])

# ─── FIX 8: temporal_entropy.py — Add TemporalEntropy alias ──────────────────
print("[8/10] Add TemporalEntropy alias to temporal_entropy.py")
patch_file('/opt/titan/core/temporal_entropy.py', [
    ('logger = logging.getLogger("TITAN-TEMPORAL-ENTROPY")',
     'logger = logging.getLogger("TITAN-TEMPORAL-ENTROPY")\n\n# V8.3: Alias for backward compatibility\nTemporalEntropy = None  # defined after EntropyGenerator class'),
])
# Append alias at end of file
content = open('/opt/titan/core/temporal_entropy.py').read()
if 'TemporalEntropy = EntropyGenerator' not in content:
    content += '\n\n# V8.3: TemporalEntropy is the canonical import name\nTemporalEntropy = EntropyGenerator\n'
    open('/opt/titan/core/temporal_entropy.py', 'w').write(content)
    print("  [PATCHED] temporal_entropy.py: TemporalEntropy alias added")

# ─── FIX 9: gamp_triangulation_v2.py — Add GampTriangulationV2 alias ─────────
print("[9/10] Add GampTriangulationV2 alias to gamp_triangulation_v2.py")
content = open('/opt/titan/core/gamp_triangulation_v2.py').read()
if 'GampTriangulationV2 = GAMPTriangulation' not in content:
    content += '\n\n# V8.3: GampTriangulationV2 is the canonical import name\nGampTriangulationV2 = GAMPTriangulation\n'
    open('/opt/titan/core/gamp_triangulation_v2.py', 'w').write(content)
    print("  [PATCHED] gamp_triangulation_v2.py: GampTriangulationV2 alias added")

# ─── FIX 10: Verify all fixes ────────────────────────────────────────────────
print("\n[10/10] Verifying all fixes...")
import sys
sys.path.insert(0, '/opt/titan')

checks = {
    'tracking_protection_False': lambda: 'privacy.trackingprotection.enabled\',False' in open('/opt/titan/core/profile_realism_engine.py').read(),
    'gen_storage_set_lookup': lambda: 'ga_domains = {' in open('/opt/titan/profgen/gen_storage.py').read(),
    'gen_storage_current_size': lambda: 'current_size' in open('/opt/titan/profgen/gen_storage.py').read(),
    'chrome_134_ua': lambda: 'Chrome/134' in open('/opt/titan/core/genesis_core.py').read(),
    'chrome_134_brand': lambda: "'134'" in open('/opt/titan/core/fingerprint_injector.py').read(),
    'firefox_buildid_spoof': lambda: 'generate_firefox_buildid_script' in open('/opt/titan/core/fingerprint_injector.py').read(),
    'camoufox_isolation': lambda: 'launch_camoufox_isolated' in open('/opt/titan/core/profile_isolation.py').read(),
    'bwrap_support': lambda: 'launch_with_bwrap' in open('/opt/titan/core/profile_isolation.py').read(),
    'TemporalEntropy_alias': lambda: 'TemporalEntropy = EntropyGenerator' in open('/opt/titan/core/temporal_entropy.py').read(),
    'GampTriangulationV2_alias': lambda: 'GampTriangulationV2 = GAMPTriangulation' in open('/opt/titan/core/gamp_triangulation_v2.py').read(),
}

passed = 0
failed = 0
for name, check in checks.items():
    try:
        result = check()
        if result:
            print(f"  [OK]  {name}")
            passed += 1
        else:
            print(f"  [FAIL] {name}")
            failed += 1
    except Exception as e:
        print(f"  [ERR] {name}: {e}")
        failed += 1

print(f"\n  PASSED: {passed}/10")
print(f"  FAILED: {failed}/10")
if failed == 0:
    print("\n  ALL V8.3 GAPS FIXED SUCCESSFULLY")
else:
    print(f"\n  {failed} FIXES NEED MANUAL REVIEW")
