#!/usr/bin/env python3
"""
Selective patcher: Extract only files that need patching from the ML6 ASAR,
apply Genesis modifications, save patched files to overlay directory.

On deployment (Linux), the full ASAR repacking happens there where we have
the .deb installed. This script prepares the patch overlay.
"""

import struct
import json
import os
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
ASAR_PATH = SCRIPT_DIR.parent / "extracted" / "data" / "opt" / "Multilogin" / "resources" / "app.asar"
OUTPUT_DIR = SCRIPT_DIR / "patch_overlay"
GENESIS_BRIDGE_PORT = 36200

# Files to extract and patch
FILES_TO_PATCH = [
    "/package.json",
    "/dist/bundle.js",
    "/dist/express-server.js",
    "/dist/preload.js",
    "/renderer/multilogin/en/index.html",
    "/renderer/multilogin/en/splash.html",
    "/renderer/multilogin/en/main.7a8d80207b5bcadd.js",
]

# Also patch all locale index.html and splash.html
LOCALE_DIRS = ["de", "es", "fr", "ja", "ko", "pt", "ru", "vi", "zh-Hans"]


class AsarReader:
    def __init__(self, path):
        self.path = path
        with open(path, 'rb') as f:
            raw = f.read(16)
            sizes = struct.unpack('<4I', raw)
            json_len = sizes[3]
            self.header = json.loads(f.read(json_len).decode('utf-8'))
            self.header_end = 8 + sizes[1]

    def read_file(self, file_path):
        node = self._find(file_path)
        if not node or 'offset' not in node:
            return None
        with open(self.path, 'rb') as f:
            f.seek(self.header_end + int(node['offset']))
            return f.read(node['size'])

    def _find(self, path):
        parts = path.strip('/').split('/')
        node = self.header
        for p in parts:
            if 'files' not in node or p not in node['files']:
                return None
            node = node['files'][p]
        return node


def patch_package_json(content):
    content = content.replace(b'"name": "Multilogin"', b'"name": "GenesisAppX"')
    content = content.replace(b'"description": "Multilogin"', b'"description": "Genesis AppX - Titan OS Anti-Detect Browser"')
    content = content.replace(b'"author": "Multilogin"', b'"author": "Titan OS"')
    content = content.replace(b'"homepage": "https://multilogin.com"', b'"homepage": "https://titan-os.local"')
    return content


def patch_bundle_js(content):
    text = content.decode('utf-8', errors='replace')
    count = 0

    # Rebrand
    for old, new in [
        ('Multilogin', 'Genesis AppX'),
        ('multiloginapp.com', 'genesis-appx.local'),
        ('multiloginapp_log', 'genesis_appx_log'),
        ('.multiloginapp.com', '.genesis-appx.local'),
        ('mla-app-core/1.0.0', 'genesis-appx/1.0.0'),
        ('mla-app-core/', 'genesis-appx/'),
    ]:
        n = text.count(old)
        if n:
            text = text.replace(old, new)
            count += n

    # Slower watchdog ping
    text = text.replace('headlessPingInterval:1e4', 'headlessPingInterval:3e4')

    # Override splash title
    text = text.replace('e.config.brand', '"Genesis AppX"')

    print(f"  bundle.js: {count} brand replacements + config patches")
    return text.encode('utf-8')


def patch_express_server(content):
    text = content.decode('utf-8', errors='replace')
    # Minimal patching - the Genesis Bridge API handles most endpoints
    return text.encode('utf-8')


def patch_preload_js(content):
    text = content.decode('utf-8', errors='replace')
    text = text.replace('"Multilogin"', '"Genesis AppX"')
    # Inject Genesis brand into APP_THEMES (preload has no user-facing Multilogin string)
    # Override dark theme to Genesis emerald accent
    text = text.replace('APP_THEMES={dark:"#202123"', 'APP_THEMES={dark:"#064e3b"')
    # Add Genesis brand marker at module boundary
    text = text.replace('t.__esModule=!0,t.APP_THEMES=', 't.__esModule=!0,t.GENESIS_APPX_BRAND="Genesis AppX",t.APP_THEMES=')
    count = 1 if "GENESIS_APPX_BRAND" in text else 0
    print(f"  preload.js: {count} Genesis brand injection + theme override")
    return text.encode('utf-8')


def patch_index_html(content):
    text = content.decode('utf-8', errors='replace')

    # Rebrand title
    text = text.replace('<title>MlaAppUi</title>', '<title>Genesis AppX</title>')

    # Inject Genesis Bridge API connector + auth bypass
    genesis_inject = """
    <script>
      // Genesis AppX - Auth Bypass & Bridge Connection
      window.__GENESIS_APPX__ = true;
      window.__GENESIS_BRIDGE__ = 'http://127.0.0.1:""" + str(GENESIS_BRIDGE_PORT) + """';

      // Intercept fetch to redirect ML6 API calls to Genesis Bridge
      (function(){
        var _f = window.fetch;
        window.fetch = function(u, o) {
          var s = typeof u === 'string' ? u : (u && u.url) || '';
          // List of paths to redirect to Genesis Bridge
          var bridge = ['/bridge/','/rest/','/api/v1/','/version','/browser-cores',
            '/systemScreen','/msgs/','/mimic/','/stealth_fox/','/download-browser','/health'];
          for (var i = 0; i < bridge.length; i++) {
            if (s.indexOf(bridge[i]) !== -1) {
              try {
                var p = new URL(s, 'http://localhost').pathname;
                var q = new URL(s, 'http://localhost').search;
                return _f(window.__GENESIS_BRIDGE__ + p + q, o);
              } catch(e) {}
            }
          }
          return _f(u, o);
        };

        // Also intercept XMLHttpRequest
        var _xo = XMLHttpRequest.prototype.open;
        XMLHttpRequest.prototype.open = function(m, u) {
          var s = typeof u === 'string' ? u : '';
          var bridge = ['/bridge/','/rest/','/api/v1/'];
          for (var i = 0; i < bridge.length; i++) {
            if (s.indexOf(bridge[i]) !== -1) {
              try {
                var p = new URL(s, 'http://localhost').pathname;
                var q = new URL(s, 'http://localhost').search;
                return _xo.call(this, m, window.__GENESIS_BRIDGE__ + p + q);
              } catch(e) {}
            }
          }
          return _xo.apply(this, arguments);
        };
        console.log('[Genesis AppX] Bridge at ' + window.__GENESIS_BRIDGE__);
      })();
    </script>"""

    text = text.replace('</head>', genesis_inject + '\n  </head>')

    # Rebrand colors: ML6 blue -> Genesis emerald green
    color_map = [
        ('--primary:#174bc9', '--primary:#10b981'),
        ('--primary-100:#e3ecff', '--primary-100:#d1fae5'),
        ('--primary-200:#d0dbf4', '--primary-200:#a7f3d0'),
        ('--primary-300:#b6c8f3', '--primary-300:#6ee7b7'),
        ('--primary-400:#456fd3', '--primary-400:#34d399'),
        ('--primary-500:#0036ba', '--primary-500:#059669'),
        ('--primary-600:#26337a', '--primary-600:#065f46'),
        ('--primary-700:#000066', '--primary-700:#064e3b'),
    ]
    for old, new in color_map:
        text = text.replace(old, new)

    return text.encode('utf-8')


def patch_splash_html(content):
    text = content.decode('utf-8', errors='replace')
    text = text.replace('<title>MlaAppUi</title>', '<title>Genesis AppX</title>')
    text = text.replace(
        '</body>',
        '  <div style="position:fixed;bottom:20px;left:0;right:0;text-align:center;'
        'color:#10b981;font-family:system-ui,sans-serif;font-size:18px;font-weight:700;'
        'text-shadow:0 1px 4px rgba(0,0,0,.6);">Genesis AppX</div>\n  </body>'
    )
    return text.encode('utf-8')


def patch_main_js(content):
    text = content.decode('utf-8', errors='replace')
    count = 0

    # Auth bypass: make canActivate always return true
    old = 'canActivate(){return!this.store.collaborationMember}'
    if old in text:
        text = text.replace(old, 'canActivate(){return!0}')
        count += 1

    # Force isLoggedIn to always resolve true
    # Pattern: isLoggedIn(){...return new Promise...}
    # We inject a short-circuit at the start
    text = re.sub(
        r'(isLoggedIn\(\)\{)',
        r'\1return Promise.resolve(!0);',
        text,
        count=2
    )
    count += 1

    # Hide signup
    text = text.replace('r.showSignUp=!0', 'r.showSignUp=!1')
    text = text.replace('showSignUp=!0===', 'showSignUp=!1===')

    # Rebrand strings
    for old_s, new_s in [
        ('Multilogin', 'Genesis AppX'),
        ('multilogin.com', 'genesis-appx.local'),
        ('"User login"', '"Genesis AppX"'),
        ('"Log in"', '"Enter"'),
        ('" Forgot password? "', '""'),
    ]:
        n = text.count(old_s)
        if n:
            text = text.replace(old_s, new_s)
            count += n

    # Default route to /profile instead of /login
    text = text.replace('"/login"', '"/profile"')
    text = text.replace("'/login'", "'/profile'")

    print(f"  main.js: {count} patches applied")
    return text.encode('utf-8')


def main():
    print("=" * 70)
    print("GENESIS APPX — SELECTIVE ASAR PATCHER")
    print("=" * 70)

    if not ASAR_PATH.exists():
        print(f"ERROR: ASAR not found at {ASAR_PATH}")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    asar = AsarReader(str(ASAR_PATH))
    print(f"ASAR loaded: header_end={asar.header_end}")

    # Build full file list
    all_files = list(FILES_TO_PATCH)
    for lang in LOCALE_DIRS:
        all_files.append(f"/renderer/multilogin/{lang}/index.html")
        all_files.append(f"/renderer/multilogin/{lang}/splash.html")
        # Each locale has its own main.js with same hash name
        all_files.append(f"/renderer/multilogin/{lang}/main.7a8d80207b5bcadd.js")

    patched = 0
    skipped = 0

    for fpath in all_files:
        data = asar.read_file(fpath)
        if data is None:
            print(f"  [SKIP] {fpath} — not in ASAR")
            skipped += 1
            continue

        fname = fpath.split('/')[-1]
        print(f"  Patching {fpath} ({len(data)} bytes)...")

        # Apply appropriate patcher
        if fname == "package.json":
            data = patch_package_json(data)
        elif fname == "bundle.js":
            data = patch_bundle_js(data)
        elif fname == "express-server.js":
            data = patch_express_server(data)
        elif fname == "preload.js":
            data = patch_preload_js(data)
        elif fname == "index.html":
            data = patch_index_html(data)
        elif fname == "splash.html":
            data = patch_splash_html(data)
        elif fname.startswith("main.") and fname.endswith(".js"):
            data = patch_main_js(data)

        # Write patched file
        out_path = OUTPUT_DIR / fpath.lstrip('/')
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, 'wb') as f:
            f.write(data)
        patched += 1

    print(f"\n  Patched: {patched}, Skipped: {skipped}")
    print(f"  Output: {OUTPUT_DIR}")

    # Also create a manifest of patched files
    manifest = {"patched_files": [str(p.relative_to(OUTPUT_DIR)) for p in OUTPUT_DIR.rglob("*") if p.is_file()]}
    with open(OUTPUT_DIR / "PATCH_MANIFEST.json", 'w') as f:
        json.dump(manifest, f, indent=2)

    print(f"\n{'=' * 70}")
    print("PATCHING COMPLETE")
    print(f"{'=' * 70}")
    print(f"\nTo deploy on Linux VPS:")
    print(f"  1. Install ML6: dpkg -i multilogin.deb")
    print(f"  2. Copy overlay: cp -r patch_overlay/* /opt/Multilogin/resources/app.asar.extracted/")
    print(f"  3. Or use deploy_genesis_appx.sh which handles everything")


if __name__ == "__main__":
    main()
