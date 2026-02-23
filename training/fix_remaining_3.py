#!/usr/bin/env python3
"""Fix remaining 3 gaps: gen_storage set, Chrome 134 UA, Chrome 134 brand."""
import re

# ── Fix 1: gen_storage.py ga_domains list → set ──────────────────────────────
path = '/opt/titan/profgen/gen_storage.py'
content = open(path).read()
# Find the ga_domains list and convert to set (change [ to { and ] to })
# The list spans multiple lines, use regex
old_pattern = r'ga_domains = \["youtube\.com".*?"linkedin\.com"\]'
new_value = 'ga_domains = {"youtube.com","reddit.com","amazon.com","eneba.com","g2a.com","newegg.com","bestbuy.com","steampowered.com","ubereats.com","linkedin.com"}'
new_content = re.sub(old_pattern, new_value, content, flags=re.DOTALL)
if new_content != content:
    open(path, 'w').write(new_content)
    print("[OK] gen_storage.py: ga_domains list -> set")
else:
    print("[SKIP] gen_storage.py: already set or pattern mismatch")
    # Show what we found
    m = re.search(r'ga_domains = .{0,200}', content, re.DOTALL)
    if m: print("  Found:", repr(m.group(0)[:100]))

# ── Fix 2: genesis_core.py — add Chrome 134 UA alongside 133 ─────────────────
path = '/opt/titan/core/genesis_core.py'
content = open(path).read()
if 'Chrome/134' not in content:
    # Replace first occurrence of Chrome/133 with Chrome/134
    new_content = content.replace(
        'Chrome/133.0.0.0 Safari/537.36"',
        'Chrome/134.0.0.0 Safari/537.36"',
        1  # only first occurrence
    )
    if new_content != content:
        open(path, 'w').write(new_content)
        print("[OK] genesis_core.py: first Chrome/133 UA -> Chrome/134")
    else:
        print("[SKIP] genesis_core.py: no Chrome/133 found")
else:
    print("[SKIP] genesis_core.py: Chrome/134 already present")

# ── Fix 3: fingerprint_injector.py — add Chrome 134 brand version ────────────
path = '/opt/titan/core/fingerprint_injector.py'
content = open(path).read()
if "'134'" not in content and 'Chrome/134' not in content:
    # Find BRAND_VERSIONS dict and prepend 134 entry
    brand_134 = (
        "        '134': {'brand': 'Chromium', 'version': '134', "
        "'full_version': '134.0.6998.89', 'brands': ["
        "{'brand': 'Chromium', 'version': '134'}, "
        "{'brand': 'Google Chrome', 'version': '134'}, "
        "{'brand': 'Not-A.Brand', 'version': '99'}]},\n"
    )
    # Find the BRAND_VERSIONS dict start
    idx = content.find("    BRAND_VERSIONS = {")
    if idx == -1:
        idx = content.find("BRAND_VERSIONS = {")
    if idx != -1:
        # Find the first entry after the opening brace
        brace_idx = content.find('{', idx) + 1
        newline_idx = content.find('\n', brace_idx) + 1
        new_content = content[:newline_idx] + brand_134 + content[newline_idx:]
        open(path, 'w').write(new_content)
        print("[OK] fingerprint_injector.py: Chrome 134 brand version added")
    else:
        print("[SKIP] fingerprint_injector.py: BRAND_VERSIONS not found")
else:
    print("[SKIP] fingerprint_injector.py: Chrome 134 already present")

# ── Verify all 10 ────────────────────────────────────────────────────────────
print("\n=== FINAL VERIFICATION ===")
checks = {
    'tracking_protection_False':   ("/opt/titan/core/profile_realism_engine.py",   "trackingprotection.enabled',False"),
    'gen_storage_set_lookup':      ("/opt/titan/profgen/gen_storage.py",            "ga_domains = {"),
    'gen_storage_current_size':    ("/opt/titan/profgen/gen_storage.py",            "current_size"),
    'chrome_134_ua':               ("/opt/titan/core/genesis_core.py",              "Chrome/134"),
    'chrome_134_brand':            ("/opt/titan/core/fingerprint_injector.py",      "'134'"),
    'firefox_buildid_spoof':       ("/opt/titan/core/fingerprint_injector.py",      "generate_firefox_buildid_script"),
    'camoufox_isolation':          ("/opt/titan/core/profile_isolation.py",         "launch_camoufox_isolated"),
    'bwrap_support':               ("/opt/titan/core/profile_isolation.py",         "launch_with_bwrap"),
    'TemporalEntropy_alias':       ("/opt/titan/core/temporal_entropy.py",          "TemporalEntropy = EntropyGenerator"),
    'GampTriangulationV2_alias':   ("/opt/titan/core/gamp_triangulation_v2.py",     "GampTriangulationV2 = GAMPTriangulation"),
}
passed = 0
for name, (fpath, needle) in checks.items():
    try:
        found = needle in open(fpath).read()
        print("  [OK]  " + name if found else "  [FAIL] " + name)
        if found: passed += 1
    except Exception as e:
        print("  [ERR] " + name + ": " + str(e))

print("\n  PASSED: %d/10" % passed)
if passed == 10:
    print("  ALL 10 V8.3 GAPS FIXED")
else:
    print("  %d STILL NEED ATTENTION" % (10 - passed))
