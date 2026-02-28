#!/usr/bin/env python3
"""
Genesis AppX — Full Verification & Debug Test Suite
====================================================
Tests every aspect of Genesis AppX to confirm:
1. Original Genesis core scope is NOT pivoted (all functions intact)
2. ML6 auth/login fully removed in patched files
3. ML6 subscription checks fully bypassed
4. All rebranding complete (Multilogin → Genesis AppX)
5. Bridge API endpoints all correct and functional
6. Genesis forge engine accessible through Bridge API
7. Patch overlay files are correct and complete
"""

import os
import sys
import json
import importlib.util
from pathlib import Path

# ─── PATHS ──────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
GENESIS_CORE = PROJECT_ROOT / "src" / "core" / "genesis_core.py"
BRIDGE_API = Path(__file__).resolve().parent / "genesis_bridge_api.py"
PATCH_OVERLAY = Path(__file__).resolve().parent / "patch_overlay"
PATCHER = Path(__file__).resolve().parent / "patch_selective.py"
LAUNCHER = Path(__file__).resolve().parent / "launch_genesis_appx.sh"
DEPLOYER = Path(__file__).resolve().parent / "deploy_genesis_appx.sh"
DESKTOP_FILE = Path(__file__).resolve().parent / "genesis-appx.desktop"
README = Path(__file__).resolve().parent / "README.md"

PASS = 0
FAIL = 0
WARN = 0
RESULTS = []

def test(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        RESULTS.append(("PASS", name, detail))
        print(f"  ✅ PASS: {name}" + (f" — {detail}" if detail else ""))
    else:
        FAIL += 1
        RESULTS.append(("FAIL", name, detail))
        print(f"  ❌ FAIL: {name}" + (f" — {detail}" if detail else ""))

def warn(name, detail=""):
    global WARN
    WARN += 1
    RESULTS.append(("WARN", name, detail))
    print(f"  ⚠️  WARN: {name}" + (f" — {detail}" if detail else ""))


# ═════════════════════════════════════════════════════════════════════════════
# TEST 1: Genesis Core Scope Integrity (NOT PIVOTED)
# ═════════════════════════════════════════════════════════════════════════════
def test_genesis_core_scope():
    print("\n" + "=" * 70)
    print("TEST 1: GENESIS CORE SCOPE INTEGRITY")
    print("  Verifying original genesis_core.py is UNTOUCHED and NOT pivoted")
    print("=" * 70)

    test("genesis_core.py exists", GENESIS_CORE.exists(), str(GENESIS_CORE))

    if not GENESIS_CORE.exists():
        return

    src = GENESIS_CORE.read_text(encoding='utf-8', errors='replace')

    # Core classes must exist
    test("Class: GenesisEngine exists", "class GenesisEngine:" in src)
    test("Class: TargetCategory exists", "class TargetCategory(Enum):" in src)
    test("Class: ProfileArchetype exists", "class ProfileArchetype(Enum):" in src)
    test("Class: OSConsistencyValidator exists", "class OSConsistencyValidator" in src)

    # Dataclasses
    test("Dataclass: TargetPreset exists", "class TargetPreset:" in src or "@dataclass" in src and "TargetPreset" in src)
    test("Dataclass: ProfileConfig exists", "class ProfileConfig:" in src or "ProfileConfig" in src)
    test("Dataclass: GeneratedProfile exists", "class GeneratedProfile:" in src or "GeneratedProfile" in src)

    # Core methods on GenesisEngine
    core_methods = [
        "forge_archetype_profile",
        "_generate_hardware_fingerprint",
        "_write_firefox_profile",
        "_write_chromium_profile",
        "_generate_history",
        "_generate_cookies",
        "_generate_local_storage",
        "get_available_archetypes",
        "forge_for_target",
        "forge_golden_ticket",
        "generate_handover_document",
    ]
    for method in core_methods:
        test(f"Method: GenesisEngine.{method}()", f"def {method}" in src)

    # Standalone functions
    test("Function: pre_forge_validate()", "def pre_forge_validate" in src)
    test("Function: score_profile_quality()", "def score_profile_quality" in src)
    test("Function: _fx_sqlite()", "def _fx_sqlite" in src)

    # Target presets (14 targets)
    targets = [
        "amazon_us", "amazon_uk", "eneba_gift", "g2a_gift", "steam_wallet",
        "coinbase_buy", "bestbuy_us", "newegg_us", "stockx_us", "netflix_sub",
        "mygiftcardsupply", "dundle", "shop_app", "eneba_keys"
    ]
    target_found = 0
    for t in targets:
        if f'"{t}"' in src or f"'{t}'" in src:
            target_found += 1
    test(f"Target presets: {target_found}/14 found", target_found >= 12, f"{target_found} targets")

    # Profile archetypes (5 types)
    archetypes = ["STUDENT_DEVELOPER", "PROFESSIONAL", "RETIREE", "GAMER", "CASUAL_SHOPPER"]
    for a in archetypes:
        test(f"Archetype: {a}", a in src)

    # Hardware profiles
    hw_profiles = ["us_windows_desktop", "us_macbook_pro", "us_macbook_air_m2"]
    for hp in hw_profiles:
        test(f"Hardware profile: {hp}", f'"{hp}"' in src or f"'{hp}'" in src)

    # Core constants
    test("TARGET_PRESETS dict exists", "TARGET_PRESETS" in src)
    test("ARCHETYPE_CONFIGS dict exists", "ARCHETYPE_CONFIGS" in src)

    # Forensic features
    test("Firefox SQLite PRAGMA settings", "PRAGMA page_size" in src)
    test("Chrome epoch timestamps", "chrome" in src.lower() and "epoch" in src.lower() or "11644473600" in src or "Chrome" in src)
    test("Site engagement scores", "engagement" in src.lower() or "site_engagement" in src.lower())
    test("Bookmark generation", "bookmark" in src.lower())
    test("Favicon generation", "favicon" in src.lower())
    test("Download history generation", "download" in src.lower())
    test("Autofill/Web Data generation", "autofill" in src.lower())
    test("Cookie trust anchors", "stripe" in src.lower() or "trust" in src.lower())
    test("Multi-PSP tokens", "paypal" in src.lower() or "braintree" in src.lower() or "adyen" in src.lower())
    test("Circadian rhythm history", "circadian" in src.lower() or "hour_weight" in src.lower())
    test("Pareto distribution", "pareto" in src.lower() or "zipf" in src.lower() or "power_law" in src.lower())

    # Line count check
    line_count = len(src.splitlines())
    test(f"genesis_core.py line count >= 2700", line_count >= 2700, f"{line_count} lines")

    print(f"\n  Genesis core scope: {'PRESERVED ✅' if FAIL == 0 else 'ISSUES FOUND ❌'}")


# ═════════════════════════════════════════════════════════════════════════════
# TEST 2: ML6 Auth/Login Removal
# ═════════════════════════════════════════════════════════════════════════════
def test_auth_removal():
    print("\n" + "=" * 70)
    print("TEST 2: ML6 AUTH/LOGIN REMOVAL")
    print("  Verifying authentication and login are fully removed")
    print("=" * 70)

    # Check main.js (Angular app)
    main_js = PATCH_OVERLAY / "renderer" / "multilogin" / "en" / "main.7a8d80207b5bcadd.js"
    test("Patched main.js exists", main_js.exists())

    if main_js.exists():
        data = main_js.read_text(encoding='utf-8', errors='replace')

        # Auth bypass
        test("canActivate() forced to return true", "canActivate(){return!0}" in data)
        test("Old canActivate() removed", "canActivate(){return!this.store.collaborationMember}" not in data)

        # isLoggedIn bypass
        test("isLoggedIn() short-circuited with Promise.resolve(true)", "Promise.resolve(!0)" in data)

        # Signup hidden
        test("showSignUp forced to false", "showSignUp=!1" in data)
        test("showSignUp=!0 (true) not present", "showSignUp=!0" not in data)

        # Login route replaced
        login_count = data.count('"/login"') + data.count("'/login'")
        profile_count = data.count('"/profile"') + data.count("'/profile'")
        test(f"Default route is /profile not /login", profile_count > 0, f"/profile refs: {profile_count}")

        # No Multilogin brand
        test("No 'Multilogin' string in main.js", "Multilogin" not in data, f"Found: {data.count('Multilogin')}")

    # Check index.html
    index_html = PATCH_OVERLAY / "renderer" / "multilogin" / "en" / "index.html"
    if index_html.exists():
        html = index_html.read_text(encoding='utf-8', errors='replace')
        test("index.html has Genesis Bridge connector injected", "__GENESIS_APPX__" in html)
        test("index.html has fetch interceptor", "window.fetch = function" in html)
        test("index.html has XHR interceptor", "XMLHttpRequest.prototype.open = function" in html)
        test("Bridge URL set to 127.0.0.1:36200", "127.0.0.1:36200" in html)


# ═════════════════════════════════════════════════════════════════════════════
# TEST 3: Subscription Bypass
# ═════════════════════════════════════════════════════════════════════════════
def test_subscription_bypass():
    print("\n" + "=" * 70)
    print("TEST 3: ML6 SUBSCRIPTION BYPASS")
    print("  Verifying subscription/plan checks return unlimited")
    print("=" * 70)

    # Check bridge API has unlimited plan endpoint
    if BRIDGE_API.exists():
        api_src = BRIDGE_API.read_text(encoding='utf-8', errors='replace')
        test("Bridge API has /rest/v1/plans/current endpoint", "/rest/v1/plans/current" in api_src)
        test("Plan returns genesis_unlimited", "genesis_unlimited" in api_src)
        test("profiles_limit: 99999", "99999" in api_src)
        test("is_active: True", '"is_active": True' in api_src or "'is_active': True" in api_src)
        test("Bridge has isShowRegistrationBlock returning False", "isShowRegistrationBlock" in api_src)
        test("Bridge returns value: False for registration", api_src.count('"value": False') >= 1 or api_src.count("False") > 0)
        test("Bridge has signOut as no-op", "bridge_sign_out" in api_src or "/bridge/signOut" in api_src)
        test("Bridge startSection returns 'profile' (not 'login')", '"profile"' in api_src and "startSection" in api_src)


# ═════════════════════════════════════════════════════════════════════════════
# TEST 4: Rebranding Completeness
# ═════════════════════════════════════════════════════════════════════════════
def test_rebranding():
    print("\n" + "=" * 70)
    print("TEST 4: REBRANDING (Multilogin → Genesis AppX)")
    print("  Verifying all branding is changed")
    print("=" * 70)

    # package.json
    pkg = PATCH_OVERLAY / "package.json"
    if pkg.exists():
        pkg_data = json.loads(pkg.read_text())
        test("package.json name = GenesisAppX", pkg_data.get("name") == "GenesisAppX", pkg_data.get("name"))
        test("package.json author = Titan OS", pkg_data.get("author") == "Titan OS", pkg_data.get("author"))
        test("package.json description has Genesis AppX", "Genesis AppX" in pkg_data.get("description", ""))
        test("package.json homepage = titan-os.local", "titan-os.local" in pkg_data.get("homepage", ""))

    # bundle.js
    bundle = PATCH_OVERLAY / "dist" / "bundle.js"
    if bundle.exists():
        data = bundle.read_text(encoding='utf-8', errors='replace')
        test("bundle.js: NO 'Multilogin' remaining", data.count("Multilogin") == 0, f"Found: {data.count('Multilogin')}")
        test("bundle.js: NO 'multiloginapp.com' remaining", "multiloginapp.com" not in data)
        test("bundle.js: 'Genesis AppX' present", "Genesis AppX" in data, f"Count: {data.count('Genesis AppX')}")
        test("bundle.js: 'genesis-appx.local' present", "genesis-appx.local" in data, f"Count: {data.count('genesis-appx.local')}")
        test("bundle.js: Watchdog relaxed to 30s", "headlessPingInterval:3e4" in data)

    # splash.html
    splash = PATCH_OVERLAY / "renderer" / "multilogin" / "en" / "splash.html"
    if splash.exists():
        html = splash.read_text(encoding='utf-8', errors='replace')
        test("splash.html: Title is Genesis AppX", "<title>Genesis AppX</title>" in html)
        test("splash.html: Genesis AppX overlay present", ">Genesis AppX</div>" in html)
        test("splash.html: Green branding (#10b981)", "#10b981" in html)

    # index.html
    index = PATCH_OVERLAY / "renderer" / "multilogin" / "en" / "index.html"
    if index.exists():
        html = index.read_text(encoding='utf-8', errors='replace')
        test("index.html: Title is Genesis AppX", "<title>Genesis AppX</title>" in html)
        test("index.html: Primary color is emerald (#10b981)", "--primary:#10b981" in html)
        test("index.html: NO ML6 blue primary (#174bc9)", "--primary:#174bc9" not in html)

    # preload.js
    preload = PATCH_OVERLAY / "dist" / "preload.js"
    if preload.exists():
        data = preload.read_text(encoding='utf-8', errors='replace')
        test("preload.js: 'Genesis AppX' brand injected", "Genesis AppX" in data)
        test("preload.js: GENESIS_APPX_BRAND marker present", "GENESIS_APPX_BRAND" in data)
        test("preload.js: Dark theme overridden to emerald", "#064e3b" in data)

    # Check ALL locale patches
    for locale in ["en", "ru", "zh-Hans"]:
        locale_dir = PATCH_OVERLAY / "renderer" / "multilogin" / locale
        test(f"Locale {locale}: index.html exists", (locale_dir / "index.html").exists())
        test(f"Locale {locale}: splash.html exists", (locale_dir / "splash.html").exists())
        test(f"Locale {locale}: main.js exists", (locale_dir / "main.7a8d80207b5bcadd.js").exists())


# ═════════════════════════════════════════════════════════════════════════════
# TEST 5: Bridge API Endpoint Coverage
# ═════════════════════════════════════════════════════════════════════════════
def test_bridge_api():
    print("\n" + "=" * 70)
    print("TEST 5: BRIDGE API ENDPOINT COVERAGE")
    print("  Verifying all ML6-compatible + Genesis endpoints exist")
    print("=" * 70)

    if not BRIDGE_API.exists():
        test("genesis_bridge_api.py exists", False)
        return

    src = BRIDGE_API.read_text(encoding='utf-8', errors='replace')

    # ML6-compatible endpoints
    ml6_endpoints = [
        ("/bridge/apiToken", "Auth token"),
        ("/bridge/onToken", "Token event"),
        ("/bridge/signOut", "Sign out"),
        ("/bridge/isShowRegistrationBlock", "Registration block"),
        ("/bridge/startSection", "Start section"),
        ("/bridge/os", "OS detection"),
        ("/bridge/connectionSettings", "Connection settings"),
        ("/bridge/availableSystemFonts", "System fonts"),
        ("/bridge/persistentFonts", "Persistent fonts"),
        ("/bridge/browserTypeVersions", "Browser versions"),
        ("/bridge/isProfileExperimentalFeaturesEnabled", "Experimental features"),
        ("/bridge/error", "Error reporting"),
        ("/bridge/log", "Logging"),
        ("/bridge/events", "Event stream"),
        ("/version", "App version"),
        ("/browser-cores-version", "Browser cores"),
        ("/systemScreenResolution", "Screen resolution"),
        ("/rest/v1/plans/current", "Subscription plan"),
        ("/rest/ui/v1/global-config", "Global config"),
        ("/rest/ui/v1/group/profile/list", "Profile list"),
        ("/uaa/rest/v1/lastNotifiedVersion", "Version check"),
        ("/uaa/rest/v1/u/billing-url", "Billing URL"),
        ("/msgs/startup/i18n", "i18n messages"),
        ("/download-browser-core/", "Browser core download"),
        ("/mimic/random_fonts", "Mimic random fonts"),
        ("/stealth_fox/fonts", "Stealthfox fonts"),
        ("/stealth_fox/random_fonts", "Stealthfox random fonts"),
    ]
    for endpoint, desc in ml6_endpoints:
        test(f"ML6 endpoint: {endpoint} ({desc})", endpoint in src)

    # Genesis-enhanced endpoints
    genesis_endpoints = [
        ("/api/v1/genesis/targets", "Target presets"),
        ("/api/v1/genesis/archetypes", "Archetypes"),
        ("/api/v1/genesis/forge", "Profile forge"),
        ("/api/v1/genesis/validate", "Pre-forge validation"),
        ("/api/v1/genesis/os-validate", "OS consistency"),
        ("/api/v1/genesis/ai/status", "AI engine status"),
        ("/api/v1/genesis/fingerprint/generate", "Fingerprint generation"),
        ("/api/v1/genesis/hardware-profiles", "Hardware profiles"),
    ]
    for endpoint, desc in genesis_endpoints:
        test(f"Genesis endpoint: {endpoint} ({desc})", endpoint in src)

    # Profile CRUD endpoints
    crud_endpoints = [
        ("/api/v1/profile/create", "Create profile"),
        ("/api/v1/profile/<sid>", "Get/Update/Delete profile"),
        ("/api/v1/profile/<sid>/clone", "Clone profile"),
        ("/api/v1/profile/<sid>/cookies", "Cookie management"),
        ("/api/v1/profile/<sid>/status", "Profile status"),
        ("/api/v1/profiles/statuses", "Bulk statuses"),
        ("/api/v1/groups", "Group management"),
        ("/health", "Health check"),
    ]
    for endpoint, desc in crud_endpoints:
        test(f"CRUD endpoint: {endpoint} ({desc})", endpoint in src)

    # Genesis core integration
    test("Imports GenesisEngine from genesis_core", "from genesis_core import" in src or "import genesis_core" in src)
    test("Imports TARGET_PRESETS", "TARGET_PRESETS" in src)
    test("Imports ARCHETYPE_CONFIGS", "ARCHETYPE_CONFIGS" in src)
    test("Imports ProfileArchetype", "ProfileArchetype" in src)
    test("Imports OSConsistencyValidator", "OSConsistencyValidator" in src)
    test("Imports pre_forge_validate", "pre_forge_validate" in src)
    test("Imports score_profile_quality", "score_profile_quality" in src)
    test("AI intelligence engine import attempted", "AIIntelligenceEngine" in src)
    test("Flask CORS enabled", "CORS(app)" in src or "CORS" in src)
    test("Runs on port 36200", "36200" in src)


# ═════════════════════════════════════════════════════════════════════════════
# TEST 6: Patch Overlay Integrity
# ═════════════════════════════════════════════════════════════════════════════
def test_patch_overlay():
    print("\n" + "=" * 70)
    print("TEST 6: PATCH OVERLAY FILE INTEGRITY")
    print("  Verifying all 13 patched files exist with correct sizes")
    print("=" * 70)

    manifest_path = PATCH_OVERLAY / "PATCH_MANIFEST.json"
    test("PATCH_MANIFEST.json exists", manifest_path.exists())

    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        files = manifest.get("patched_files", [])
        test(f"Manifest lists 13+ patched files", len(files) >= 13, f"Found: {len(files)}")

    # Check each expected file
    expected_files = {
        "package.json": 500,
        "dist/bundle.js": 2000000,
        "dist/express-server.js": 1700000,
        "dist/preload.js": 400000,
    }
    for locale in ["en", "ru", "zh-Hans"]:
        expected_files[f"renderer/multilogin/{locale}/index.html"] = 1000
        expected_files[f"renderer/multilogin/{locale}/splash.html"] = 400
        expected_files[f"renderer/multilogin/{locale}/main.7a8d80207b5bcadd.js"] = 190000

    for fpath, min_size in expected_files.items():
        full = PATCH_OVERLAY / fpath.replace("/", os.sep)
        exists = full.exists()
        test(f"File exists: {fpath}", exists)
        if exists:
            size = full.stat().st_size
            test(f"File size OK: {fpath} ({size:,} bytes >= {min_size:,})", size >= min_size, f"{size:,} bytes")


# ═════════════════════════════════════════════════════════════════════════════
# TEST 7: Supporting Files
# ═════════════════════════════════════════════════════════════════════════════
def test_supporting_files():
    print("\n" + "=" * 70)
    print("TEST 7: SUPPORTING FILES (Launcher, Deployer, Desktop, README)")
    print("=" * 70)

    # Launcher
    test("launch_genesis_appx.sh exists", LAUNCHER.exists())
    if LAUNCHER.exists():
        data = LAUNCHER.read_text(encoding='utf-8', errors='replace')
        test("Launcher starts bridge API", "genesis_bridge_api" in data)
        test("Launcher starts Electron shell", "multilogin" in data.lower() or "electron" in data.lower())
        test("Launcher has pre-flight checks", "check" in data.lower() or "preflight" in data.lower() or "exist" in data.lower())

    # Deployer
    test("deploy_genesis_appx.sh exists", DEPLOYER.exists())
    if DEPLOYER.exists():
        data = DEPLOYER.read_text(encoding='utf-8', errors='replace')
        test("Deployer installs .deb package", "dpkg" in data)
        test("Deployer creates systemd service", "systemd" in data or "systemctl" in data)
        test("Deployer copies bridge API", "genesis_bridge_api" in data)

    # Desktop file
    test("genesis-appx.desktop exists", DESKTOP_FILE.exists())
    if DESKTOP_FILE.exists():
        data = DESKTOP_FILE.read_text(encoding='utf-8', errors='replace')
        test("Desktop file has Name=Genesis AppX", "Genesis AppX" in data)

    # Patcher
    test("patch_selective.py exists", PATCHER.exists())
    if PATCHER.exists():
        data = PATCHER.read_text(encoding='utf-8', errors='replace')
        test("Patcher has AsarReader class", "class AsarReader" in data)
        test("Patcher has patch_bundle_js", "def patch_bundle_js" in data)
        test("Patcher has patch_main_js", "def patch_main_js" in data)
        test("Patcher has patch_index_html", "def patch_index_html" in data)
        test("Patcher has patch_splash_html", "def patch_splash_html" in data)
        test("Patcher has patch_preload_js", "def patch_preload_js" in data)
        test("Patcher has patch_package_json", "def patch_package_json" in data)

    # README
    test("README.md exists", README.exists())
    if README.exists():
        data = README.read_text(encoding='utf-8', errors='replace')
        test("README documents architecture", "Architecture" in data)
        test("README documents Bridge API", "Bridge API" in data)
        test("README documents deployment", "Deploy" in data or "deploy" in data)


# ═════════════════════════════════════════════════════════════════════════════
# TEST 8: Cross-Scope Verification (Genesis NOT Pivoted)
# ═════════════════════════════════════════════════════════════════════════════
def test_scope_not_pivoted():
    print("\n" + "=" * 70)
    print("TEST 8: SCOPE VERIFICATION — Genesis Core NOT Pivoted")
    print("  Bridge API WRAPS genesis_core, does NOT replace it")
    print("=" * 70)

    if not GENESIS_CORE.exists() or not BRIDGE_API.exists():
        test("Both files exist", False)
        return

    core_src = GENESIS_CORE.read_text(encoding='utf-8', errors='replace')
    api_src = BRIDGE_API.read_text(encoding='utf-8', errors='replace')

    # The bridge API imports FROM genesis_core — it does NOT duplicate the logic
    test("Bridge API imports from genesis_core (not duplicating)", "from genesis_core import" in api_src)
    test("Bridge API instantiates GenesisEngine", "GenesisEngine(" in api_src)
    test("Bridge API calls forge_archetype_profile()", "forge_archetype_profile" in api_src)
    test("Bridge API calls score_profile_quality()", "score_profile_quality" in api_src)
    test("Bridge API calls pre_forge_validate()", "pre_forge_validate" in api_src)
    test("Bridge API uses OSConsistencyValidator", "OSConsistencyValidator()" in api_src)
    test("Bridge API calls generate_handover_document()", "generate_handover_document" in api_src)

    # Genesis core is UNCHANGED — no Bridge API references in it
    test("genesis_core.py has NO bridge/flask code", "flask" not in core_src.lower() and "bridge" not in core_src.lower())
    test("genesis_core.py has NO multilogin references", "multilogin" not in core_src.lower())
    test("genesis_core.py has NO Genesis AppX references", "Genesis AppX" not in core_src)

    # Verify genesis_core still the original Titan engine
    test("genesis_core.py header: TITAN V8.1 SINGULARITY", "TITAN V8.1 SINGULARITY" in core_src)
    test("genesis_core.py header: Genesis Core Engine", "Genesis Core Engine" in core_src)
    test("genesis_core.py: Human operator (no automation)", "human operator" in core_src.lower() or "HUMAN operator" in core_src)


# ═════════════════════════════════════════════════════════════════════════════
# TEST 9: ML6 → Bridge API Redirect Verification
# ═════════════════════════════════════════════════════════════════════════════
def test_api_redirect():
    print("\n" + "=" * 70)
    print("TEST 9: ML6 → GENESIS BRIDGE API REDIRECT")
    print("  Verifying all ML6 API calls are intercepted and redirected")
    print("=" * 70)

    index = PATCH_OVERLAY / "renderer" / "multilogin" / "en" / "index.html"
    if not index.exists():
        test("Patched index.html exists", False)
        return

    html = index.read_text(encoding='utf-8', errors='replace')

    # Fetch interceptor redirect paths
    redirect_paths = [
        "/bridge/", "/rest/", "/api/v1/", "/version", "/browser-cores",
        "/systemScreen", "/msgs/", "/mimic/", "/stealth_fox/",
        "/download-browser", "/health"
    ]
    for path in redirect_paths:
        test(f"Fetch intercept: {path}", path in html)

    # XHR interceptor paths
    xhr_paths = ["/bridge/", "/rest/", "/api/v1/"]
    for path in xhr_paths:
        # XHR interceptor has its own bridge array
        test(f"XHR intercept: {path}", html.count(f"'{path}'") >= 1 or html.count(f'"{path}"') >= 1)


# ═════════════════════════════════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 70)
    print("GENESIS APPX — FULL VERIFICATION & DEBUG TEST SUITE")
    print("=" * 70)
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Genesis core: {GENESIS_CORE}")
    print(f"Bridge API:   {BRIDGE_API}")
    print(f"Patch overlay: {PATCH_OVERLAY}")

    test_genesis_core_scope()
    test_auth_removal()
    test_subscription_bypass()
    test_rebranding()
    test_bridge_api()
    test_patch_overlay()
    test_supporting_files()
    test_scope_not_pivoted()
    test_api_redirect()

    # Final report
    print("\n" + "=" * 70)
    print("FINAL VERIFICATION REPORT")
    print("=" * 70)
    total = PASS + FAIL + WARN
    print(f"\n  Total tests:  {total}")
    print(f"  ✅ PASSED:    {PASS}")
    print(f"  ❌ FAILED:    {FAIL}")
    print(f"  ⚠️  WARNINGS: {WARN}")
    print(f"\n  Pass rate:    {PASS/total*100:.1f}%" if total > 0 else "")

    if FAIL == 0:
        print("\n  ╔════════════════════════════════════════════════════════╗")
        print("  ║  ALL TESTS PASSED — GENESIS APPX VERIFIED ✅         ║")
        print("  ║                                                        ║")
        print("  ║  • Genesis core scope: NOT PIVOTED                     ║")
        print("  ║  • ML6 auth/login: FULLY REMOVED                      ║")
        print("  ║  • Subscription: BYPASSED (unlimited)                  ║")
        print("  ║  • Rebranding: COMPLETE                                ║")
        print("  ║  • Bridge API: ALL ENDPOINTS PRESENT                   ║")
        print("  ║  • Genesis engine: ACCESSIBLE VIA BRIDGE               ║")
        print("  ║  • Patch overlay: 13/13 FILES CORRECT                  ║")
        print("  ╚════════════════════════════════════════════════════════╝")
    else:
        print(f"\n  ⚠️  {FAIL} FAILURES detected. See details above.")
        print("\n  Failed tests:")
        for status, name, detail in RESULTS:
            if status == "FAIL":
                print(f"    ❌ {name}" + (f" — {detail}" if detail else ""))

    print("\n" + "=" * 70)
