#!/usr/bin/env python3
"""
Genesis AppX ASAR Patcher
=========================
Extracts ML6 app.asar, applies patches to:
1. Remove login/auth requirement (bypass cloud dependency)
2. Rebrand from "Multilogin" to "Genesis AppX"
3. Redirect API calls to local Genesis Bridge API
4. Add Genesis-specific UI features
5. Repackage as modified app.asar

Usage:
    python patch_ml6_asar.py [--source /path/to/app.asar] [--output /path/to/output/]
"""

import struct
import json
import os
import sys
import re
import shutil
import hashlib
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# ─── Configuration ──────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).parent
DEFAULT_ASAR = SCRIPT_DIR.parent / "extracted" / "data" / "opt" / "Multilogin" / "resources" / "app.asar"
DEFAULT_OUTPUT = SCRIPT_DIR / "patched"

GENESIS_BRIDGE_PORT = 36200
GENESIS_BRIDGE_URL = f"http://127.0.0.1:{GENESIS_BRIDGE_PORT}"


# ═══════════════════════════════════════════════════════════════════════════
# ASAR READER / WRITER
# ═══════════════════════════════════════════════════════════════════════════

class AsarArchive:
    """Read and write Electron ASAR archives."""

    def __init__(self, path: str):
        self.path = Path(path)
        self.header = {}
        self.header_end = 0
        self._read_header()

    def _read_header(self):
        with open(self.path, 'rb') as f:
            raw = f.read(16)
            sizes = struct.unpack('<4I', raw)
            json_len = sizes[3]
            header_json = f.read(json_len).decode('utf-8')
            self.header = json.loads(header_json)
            self.header_end = 8 + sizes[1]

    def extract_file(self, file_path: str) -> Optional[bytes]:
        """Extract a single file from the ASAR by its internal path."""
        node = self._find_node(file_path)
        if not node or 'offset' not in node:
            return None

        offset = int(node['offset'])
        size = node.get('size', 0)
        abs_offset = self.header_end + offset

        with open(self.path, 'rb') as f:
            f.seek(abs_offset)
            return f.read(size)

    def extract_all(self, output_dir: Path, filter_fn=None):
        """Extract all files to output_dir."""
        files = []
        self._walk(self.header, '', files)

        for path, node in files:
            if filter_fn and not filter_fn(path):
                continue
            if node.get('unpacked'):
                continue
            if 'offset' not in node:
                continue

            data = self.extract_file(path)
            if data is not None:
                out_path = output_dir / path.lstrip('/')
                out_path.parent.mkdir(parents=True, exist_ok=True)
                with open(out_path, 'wb') as f:
                    f.write(data)

    def _find_node(self, file_path: str) -> Optional[Dict]:
        parts = file_path.strip('/').split('/')
        node = self.header
        for part in parts:
            if 'files' not in node:
                return None
            if part not in node['files']:
                return None
            node = node['files'][part]
        return node

    def _walk(self, node: Dict, path: str, results: List):
        if 'files' in node:
            for name, child in node['files'].items():
                self._walk(child, f"{path}/{name}", results)
        else:
            results.append((path, node))

    @staticmethod
    def repack(source_dir: Path, output_path: Path):
        """Repack a directory into an ASAR archive."""
        print(f"Repacking ASAR from {source_dir} -> {output_path}")

        # Build header and collect file data
        header = {"files": {}}
        file_data_parts = []
        current_offset = 0

        def build_header(dir_path: Path, header_node: Dict):
            nonlocal current_offset
            for item in sorted(dir_path.iterdir()):
                rel = item.name
                if item.is_dir():
                    header_node["files"][rel] = {"files": {}}
                    build_header(item, header_node["files"][rel])
                elif item.is_file():
                    size = item.stat().st_size
                    header_node["files"][rel] = {
                        "offset": str(current_offset),
                        "size": size
                    }
                    file_data_parts.append(item)
                    current_offset += size

        build_header(source_dir, header)

        # Serialize header
        header_json = json.dumps(header, separators=(',', ':')).encode('utf-8')
        json_len = len(header_json)

        # ASAR header structure:
        # uint32: pickle_size (4)
        # uint32: header_data_size (json_len + 8)
        # uint32: header_string_size (json_len + 4)
        # uint32: json_length (json_len)
        # [json bytes]
        # [padding to align]
        # [file data]

        header_data_size = json_len + 8
        header_string_size = json_len + 4

        header_bytes = struct.pack('<4I', 4, header_data_size, header_string_size, json_len)
        header_bytes += header_json

        # Pad to align (header_end = 8 + header_data_size)
        header_end = 8 + header_data_size
        if len(header_bytes) < header_end:
            header_bytes += b'\x00' * (header_end - len(header_bytes))

        # Write output
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(header_bytes)
            for file_path in file_data_parts:
                with open(file_path, 'rb') as src:
                    f.write(src.read())

        total_size = output_path.stat().st_size
        print(f"  ASAR written: {total_size:,} bytes ({total_size/1024/1024:.1f} MB)")
        return output_path


# ═══════════════════════════════════════════════════════════════════════════
# PATCHERS
# ═══════════════════════════════════════════════════════════════════════════

class ML6Patcher:
    """Apply patches to ML6 extracted files."""

    def __init__(self, extract_dir: Path):
        self.dir = extract_dir
        self.stats = {"files_patched": 0, "replacements": 0}

    def patch_all(self):
        """Apply all patches."""
        print("\n=== PATCHING ML6 FILES ===\n")

        self.patch_package_json()
        self.patch_bundle_js()
        self.patch_express_server()
        self.patch_preload_js()
        self.patch_renderer_html()
        self.patch_renderer_main_js()
        self.patch_renderer_css()

        print(f"\n=== PATCHING COMPLETE ===")
        print(f"  Files patched: {self.stats['files_patched']}")
        print(f"  Total replacements: {self.stats['replacements']}")

    def _patch_file(self, rel_path: str, replacements: List[Tuple[str, str]], encoding='utf-8'):
        """Apply string replacements to a file."""
        fpath = self.dir / rel_path
        if not fpath.exists():
            print(f"  [SKIP] {rel_path} - not found")
            return False

        with open(fpath, 'r', encoding=encoding, errors='replace') as f:
            content = f.read()

        original = content
        count = 0
        for old, new in replacements:
            n = content.count(old)
            if n > 0:
                content = content.replace(old, new)
                count += n

        if count > 0:
            with open(fpath, 'w', encoding=encoding) as f:
                f.write(content)
            print(f"  [OK] {rel_path} - {count} replacements")
            self.stats["files_patched"] += 1
            self.stats["replacements"] += count
            return True
        else:
            print(f"  [--] {rel_path} - no changes needed")
            return False

    def _patch_file_regex(self, rel_path: str, patterns: List[Tuple[str, str]], encoding='utf-8'):
        """Apply regex replacements to a file."""
        fpath = self.dir / rel_path
        if not fpath.exists():
            print(f"  [SKIP] {rel_path} - not found")
            return False

        with open(fpath, 'r', encoding=encoding, errors='replace') as f:
            content = f.read()

        count = 0
        for pattern, replacement in patterns:
            new_content, n = re.subn(pattern, replacement, content)
            if n > 0:
                content = new_content
                count += n

        if count > 0:
            with open(fpath, 'w', encoding=encoding) as f:
                f.write(content)
            print(f"  [OK] {rel_path} - {count} regex replacements")
            self.stats["files_patched"] += 1
            self.stats["replacements"] += count
            return True
        return False

    # ─── package.json ────────────────────────────────────────────────────

    def patch_package_json(self):
        print("1. Patching package.json...")
        self._patch_file("package.json", [
            ('"name": "Multilogin"', '"name": "GenesisAppX"'),
            ('"description": "Multilogin"', '"description": "Genesis AppX - Titan OS Anti-Detect Browser"'),
            ('"author": "Multilogin"', '"author": "Titan OS"'),
            ('"homepage": "https://multilogin.com"', '"homepage": "https://titan-os.local"'),
            ('https://bitbucket.org/grvtydev/mla-app-core', 'https://github.com/titan-os/genesis-appx'),
        ])

    # ─── bundle.js (Main Process) ───────────────────────────────────────

    def patch_bundle_js(self):
        print("2. Patching dist/bundle.js (main process)...")

        fpath = self.dir / "dist" / "bundle.js"
        if not fpath.exists():
            print("  [SKIP] dist/bundle.js not found")
            return

        with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()

        original_len = len(content)
        replacements = 0

        # --- PATCH 1: Rebrand strings ---
        brand_replacements = [
            ('Multilogin', 'Genesis AppX'),
            ('multiloginapp.com', 'genesis-appx.local'),
            ('multiloginapp_log', 'genesis_appx_log'),
            ('.multiloginapp.com', '.genesis-appx.local'),
            ('mla-app-core/1.0.0', 'genesis-appx/1.0.0'),
            ('mla-app-core/', 'genesis-appx/'),
        ]
        for old, new in brand_replacements:
            n = content.count(old)
            if n:
                content = content.replace(old, new)
                replacements += n

        # --- PATCH 2: Force headless config to use local mode ---
        # The config has: lang:void 0,devTools:!1,watchdog:{headlessPingInterval:1e4}
        # We want to ensure it starts without requiring auth
        content = content.replace(
            'headlessPingInterval:1e4',
            'headlessPingInterval:3e4'  # Slower ping, less aggressive
        )

        # --- PATCH 3: Override splash screen title ---
        content = content.replace(
            'e.config.brand',
            '"Genesis AppX"'
        )

        # --- PATCH 4: Skip update checks ---
        content = content.replace(
            'lastNotifiedVersion',
            'skipVersionCheck'
        )

        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"  [OK] dist/bundle.js - {replacements}+ patches applied (size: {original_len} -> {len(content)})")
        self.stats["files_patched"] += 1
        self.stats["replacements"] += replacements

    # ─── express-server.js ───────────────────────────────────────────────

    def patch_express_server(self):
        print("3. Patching dist/express-server.js...")
        # The express server is mostly framework code - minimal patching needed
        # The Genesis Bridge API runs separately and handles the custom endpoints
        self._patch_file("dist/express-server.js", [
            ('multilogin', 'genesis-appx'),
        ])

    # ─── preload.js ──────────────────────────────────────────────────────

    def patch_preload_js(self):
        print("4. Patching dist/preload.js...")
        self._patch_file("dist/preload.js", [
            ('"Multilogin"', '"Genesis AppX"'),
            ("'Multilogin'", "'Genesis AppX'"),
        ])

    # ─── Renderer HTML (all languages) ───────────────────────────────────

    def patch_renderer_html(self):
        print("5. Patching renderer HTML files...")
        renderer_dir = self.dir / "renderer" / "multilogin"
        if not renderer_dir.exists():
            # Try alternate path
            renderer_dir = self.dir / "renderer"

        if not renderer_dir.exists():
            print("  [SKIP] renderer directory not found")
            return

        # Patch all index.html files across all locales
        count = 0
        for html_file in renderer_dir.rglob("index.html"):
            rel = html_file.relative_to(self.dir)
            with open(html_file, 'r', encoding='utf-8', errors='replace') as f:
                html = f.read()

            original = html

            # Rebrand title
            html = html.replace('<title>MlaAppUi</title>', '<title>Genesis AppX</title>')

            # Inject Genesis Bridge API connection + auth bypass script
            genesis_inject = """
    <script>
      // Genesis AppX - Auth Bypass & Bridge API Connection
      window.__GENESIS_APPX__ = true;
      window.__GENESIS_BRIDGE_URL__ = 'http://127.0.0.1:""" + str(GENESIS_BRIDGE_PORT) + """';
      window.__GENESIS_AUTH_BYPASS__ = true;

      // Override fetch to intercept auth-related calls
      const _origFetch = window.fetch;
      window.fetch = function(url, opts) {
        const urlStr = typeof url === 'string' ? url : url.url || '';

        // Redirect auth endpoints to Genesis bridge
        if (urlStr.includes('/bridge/apiToken') ||
            urlStr.includes('/bridge/onToken') ||
            urlStr.includes('/bridge/signOut') ||
            urlStr.includes('/bridge/isShowRegistrationBlock') ||
            urlStr.includes('/bridge/startSection') ||
            urlStr.includes('/rest/v1/plans/current') ||
            urlStr.includes('/rest/ui/v1/global-config') ||
            urlStr.includes('/uaa/rest/') ||
            urlStr.includes('/bridge/events') ||
            urlStr.includes('/bridge/browserTypeVersions') ||
            urlStr.includes('/bridge/isProfileExperimentalFeaturesEnabled') ||
            urlStr.includes('/bridge/availableSystemFonts') ||
            urlStr.includes('/bridge/persistentFonts') ||
            urlStr.includes('/bridge/connectionSettings') ||
            urlStr.includes('/systemScreenResolution') ||
            urlStr.includes('/browser-cores-version') ||
            urlStr.includes('/version') ||
            urlStr.includes('/msgs/startup/i18n') ||
            urlStr.includes('/mimic/random_fonts') ||
            urlStr.includes('/stealth_fox/') ||
            urlStr.includes('/download-browser-core/') ||
            urlStr.includes('/rest/ui/v1/group/profile/list')) {
          const bridgeUrl = window.__GENESIS_BRIDGE_URL__ + new URL(urlStr, 'http://localhost').pathname + new URL(urlStr, 'http://localhost').search;
          return _origFetch(bridgeUrl, opts);
        }

        // Redirect profile API calls to Genesis bridge
        if (urlStr.includes('/api/v1/')) {
          const bridgeUrl = window.__GENESIS_BRIDGE_URL__ + new URL(urlStr, 'http://localhost').pathname;
          return _origFetch(bridgeUrl, opts);
        }

        return _origFetch(url, opts);
      };

      // Override XMLHttpRequest for older API calls
      const _origXHROpen = XMLHttpRequest.prototype.open;
      XMLHttpRequest.prototype.open = function(method, url) {
        const urlStr = typeof url === 'string' ? url : '';
        if (urlStr.includes('/bridge/') || urlStr.includes('/rest/') || urlStr.includes('/api/v1/')) {
          const bridgeUrl = window.__GENESIS_BRIDGE_URL__ + new URL(urlStr, 'http://localhost').pathname + new URL(urlStr, 'http://localhost').search;
          return _origXHROpen.call(this, method, bridgeUrl);
        }
        return _origXHROpen.apply(this, arguments);
      };

      console.log('[Genesis AppX] Bridge API connected at ' + window.__GENESIS_BRIDGE_URL__);
    </script>"""

            # Insert before closing </head> or before first <script>
            if '</head>' in html:
                html = html.replace('</head>', genesis_inject + '\n  </head>')
            elif '<script>' in html:
                html = html.replace('<script>', genesis_inject + '\n    <script>', 1)

            # Rebrand CSS colors (primary blue -> Genesis green/dark theme)
            html = html.replace('--primary:#174bc9', '--primary:#10b981')
            html = html.replace('--primary-100:#e3ecff', '--primary-100:#d1fae5')
            html = html.replace('--primary-200:#d0dbf4', '--primary-200:#a7f3d0')
            html = html.replace('--primary-300:#b6c8f3', '--primary-300:#6ee7b7')
            html = html.replace('--primary-400:#456fd3', '--primary-400:#34d399')
            html = html.replace('--primary-500:#0036ba', '--primary-500:#059669')
            html = html.replace('--primary-600:#26337a', '--primary-600:#065f46')
            html = html.replace('--primary-700:#000066', '--primary-700:#064e3b')

            # Make sidebar darker for Genesis brand
            html = html.replace('--sidebar-background:var(--background-accent)',
                                '--sidebar-background:#111827')

            if html != original:
                with open(html_file, 'w', encoding='utf-8') as f:
                    f.write(html)
                count += 1

        # Patch splash screens
        for splash in renderer_dir.rglob("splash.html"):
            with open(splash, 'r', encoding='utf-8', errors='replace') as f:
                html = f.read()
            html = html.replace('<title>MlaAppUi</title>', '<title>Genesis AppX</title>')
            # Add a text overlay on the splash
            html = html.replace(
                '</body>',
                '  <div style="position:fixed;bottom:20px;left:0;right:0;text-align:center;color:#10b981;font-family:sans-serif;font-size:18px;font-weight:bold;text-shadow:0 1px 3px rgba(0,0,0,0.5);">Genesis AppX - Powered by Titan OS</div>\n  </body>'
            )
            with open(splash, 'w', encoding='utf-8') as f:
                f.write(html)
            count += 1

        print(f"  [OK] {count} HTML files patched")
        self.stats["files_patched"] += count
        self.stats["replacements"] += count * 5  # Approximate

    # ─── Renderer main.js (Angular app) ──────────────────────────────────

    def patch_renderer_main_js(self):
        print("6. Patching renderer main.js (Angular app)...")
        renderer_dir = self.dir / "renderer" / "multilogin"
        if not renderer_dir.exists():
            print("  [SKIP] renderer directory not found")
            return

        count = 0
        for main_js in renderer_dir.rglob("main.*.js"):
            rel = main_js.relative_to(self.dir)
            with open(main_js, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()

            original = content

            # --- PATCH: Auth guard bypass ---
            # The auth guard checks isLoggedIn() - make it always return true
            # Pattern: canActivate(){return!this.store.collaborationMember}
            # Pattern: canActivate(){...isLoggedIn()...}
            content = content.replace(
                'canActivate(){return!this.store.collaborationMember}',
                'canActivate(){return!0}'  # Always allow
            )

            # Bypass the main auth guard that checks isLoggedIn
            # Pattern: u.authGuard.isLoggedIn().then(q=>{
            content = re.sub(
                r'\.authGuard\.isLoggedIn\(\)\.then\(',
                '.authGuard.isLoggedIn=function(){return Promise.resolve(!0)},function(){return Promise.resolve(!0)}(',
                content,
                count=1
            )

            # Force isLoggedIn to always return true
            # This catches: isLoggedIn(){...complex auth check...}
            content = re.sub(
                r'isLoggedIn\(\)\{[^}]{0,200}return\s+new\s+Promise',
                'isLoggedIn(){return new Promise(function(r){return r(!0)});var _x=new Promise',
                content,
                count=2
            )

            # --- PATCH: Remove signup/registration prompts ---
            content = content.replace('showSignUp=!0===', 'showSignUp=!1===')
            content = content.replace('r.showSignUp=!0', 'r.showSignUp=!1')

            # --- PATCH: Rebrand UI strings ---
            brand_replacements = [
                ('Multilogin', 'Genesis AppX'),
                ('multilogin.com', 'genesis-appx.local'),
                ('"User login"', '"Genesis AppX"'),
                ('"Log in"', '"Enter"'),
                ('" Forgot password? "', '""'),
                ('"Sign up"', '""'),
            ]
            for old, new in brand_replacements:
                content = content.replace(old, new)

            # --- PATCH: Default to profile page (skip login) ---
            content = content.replace('"/login"', '"/profile"')
            content = content.replace("'/login'", "'/profile'")

            if content != original:
                with open(main_js, 'w', encoding='utf-8') as f:
                    f.write(content)
                count += 1

        # Also patch the lazy-loaded chunks for any auth references
        for chunk_js in renderer_dir.rglob("*.js"):
            if 'main.' in chunk_js.name:
                continue  # Already handled
            with open(chunk_js, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            original = content
            content = content.replace('Multilogin', 'Genesis AppX')
            content = content.replace('multilogin.com', 'genesis-appx.local')
            if content != original:
                with open(chunk_js, 'w', encoding='utf-8') as f:
                    f.write(content)
                count += 1

        print(f"  [OK] {count} JS files patched")
        self.stats["files_patched"] += count

    # ─── CSS ─────────────────────────────────────────────────────────────

    def patch_renderer_css(self):
        print("7. Patching renderer CSS...")
        renderer_dir = self.dir / "renderer" / "multilogin"
        if not renderer_dir.exists():
            return

        count = 0
        for css_file in renderer_dir.rglob("*.css"):
            with open(css_file, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            original = content

            # Rebrand primary colors to Genesis green
            content = content.replace('#174bc9', '#10b981')
            content = content.replace('#0036ba', '#059669')
            content = content.replace('#26337a', '#065f46')
            content = content.replace('#000066', '#064e3b')
            content = content.replace('#e3ecff', '#d1fae5')
            content = content.replace('#d0dbf4', '#a7f3d0')

            if content != original:
                with open(css_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                count += 1

        print(f"  [OK] {count} CSS files patched")
        self.stats["files_patched"] += count


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Genesis AppX ASAR Patcher")
    parser.add_argument("--source", default=str(DEFAULT_ASAR), help="Path to ML6 app.asar")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output directory for patched files")
    parser.add_argument("--no-repack", action="store_true", help="Don't repack into ASAR (keep extracted)")
    args = parser.parse_args()

    source = Path(args.source)
    output = Path(args.output)

    if not source.exists():
        print(f"ERROR: Source ASAR not found: {source}")
        sys.exit(1)

    print("=" * 70)
    print("GENESIS APPX ASAR PATCHER")
    print("=" * 70)
    print(f"  Source: {source}")
    print(f"  Output: {output}")
    print()

    # Step 1: Extract ASAR
    extract_dir = output / "extracted"
    if extract_dir.exists():
        shutil.rmtree(extract_dir)

    print("Step 1: Extracting ASAR archive...")
    asar = AsarArchive(str(source))
    asar.extract_all(extract_dir)
    file_count = sum(1 for _ in extract_dir.rglob("*") if _.is_file())
    print(f"  Extracted {file_count} files")

    # Step 2: Apply patches
    print("\nStep 2: Applying patches...")
    patcher = ML6Patcher(extract_dir)
    patcher.patch_all()

    # Step 3: Repack
    if not args.no_repack:
        print("\nStep 3: Repacking ASAR...")
        output_asar = output / "app.asar"
        AsarArchive.repack(extract_dir, output_asar)
        print(f"\n  Patched ASAR ready at: {output_asar}")
    else:
        print(f"\n  Patched files at: {extract_dir}")

    print("\n" + "=" * 70)
    print("PATCHING COMPLETE")
    print("=" * 70)
    print(f"\nNext steps:")
    print(f"  1. Start Genesis Bridge API: python genesis_bridge_api.py")
    print(f"  2. Replace /opt/Multilogin/resources/app.asar with patched version")
    print(f"  3. Launch: /opt/Multilogin/multilogin")


if __name__ == "__main__":
    main()
