"""Focused reverse engineering of Multilogin 6 - architecture extraction."""
import re
import os

BASE = r'C:\Users\Administrator\Downloads\titan-7\titan-7\titan-7\tools\multilogin6\extracted\app_src'

def read_file(path):
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        return f.read()

bundle = read_file(os.path.join(BASE, 'dist', 'bundle.js'))
express = read_file(os.path.join(BASE, 'dist', 'express-server.js'))
preload = read_file(os.path.join(BASE, 'dist', 'preload.js'))

print("=" * 80)
print("MULTILOGIN 6.5.0 - FOCUSED ARCHITECTURE ANALYSIS")
print("=" * 80)

# 1. API endpoints from express server
print("\n## 1. EXPRESS SERVER API ROUTES")
# Find route registrations in express server
for m in re.finditer(r'app\.(get|post|put|delete|patch|use)\("(/[^"]+)"', express):
    print(f"  {m.group(1).upper():6s} {m.group(2)}")
# Also look for router patterns
for m in re.finditer(r'router\.(get|post|put|delete|patch)\("(/[^"]+)"', express):
    print(f"  {m.group(1).upper():6s} {m.group(2)}")
# Alternative: look for path strings near HTTP method keywords
for m in re.finditer(r'"(GET|POST|PUT|DELETE|PATCH)"[^"]{0,30}"(/[^"]+)"', express):
    print(f"  {m.group(1):6s} {m.group(2)}")

# 2. IPC channels (Electron main<->renderer communication)
print("\n## 2. IPC CHANNELS (Main <-> Renderer)")
ipc_channels = set()
for m in re.finditer(r'"((?:ipc-|on-|get-|set-|start-|stop-|create-|update-|delete-|save-|load-|import-|export-|clone-|share-|browser-|profile-|proxy-|app-|config-|headless-|team-|session-|cookie-|fingerprint-)[^"]{2,60})"', bundle + preload):
    ipc_channels.add(m.group(1))
for ch in sorted(ipc_channels):
    print(f"  {ch}")

# 3. Key property/method names from prototypes
print("\n## 3. PROTOTYPE METHODS (Key Classes)")
methods = set()
for m in re.finditer(r'\.prototype\.(\w{5,50})\s*=\s*function', bundle):
    methods.add(m.group(1))
# Also __awaiter patterns
for m in re.finditer(r'\.prototype\.(\w{5,50})\s*=\s*(?:function|async)', bundle):
    methods.add(m.group(1))
interesting = [m for m in methods if any(kw in m.lower() for kw in 
    ['profile', 'browser', 'proxy', 'finger', 'cookie', 'start', 'stop',
     'create', 'update', 'delete', 'launch', 'save', 'load', 'import',
     'export', 'clone', 'share', 'team', 'session', 'headless', 'config',
     'port', 'navigate', 'selenium', 'automation', 'watchdog', 'splash',
     'theme', 'license', 'auth', 'login', 'account', 'member', 'group',
     'folder', 'tag', 'note', 'status', 'transfer', 'sync', 'backup',
     'restore', 'encrypt', 'decrypt', 'hash', 'random', 'generate'])]
for m in sorted(interesting):
    print(f"  {m}")

# 4. App Properties / Configuration
print("\n## 4. APP CONFIGURATION (app.properties)")
# Search for property keys
prop_keys = set()
for m in re.finditer(r'"((?:app\.|multilogin\.|browser\.|headless\.|proxy\.|automation\.)[^"]{3,60})"', bundle + express):
    prop_keys.add(m.group(1))
for k in sorted(prop_keys):
    print(f"  {k}")

# 5. Profile structure - find object keys that define browser profiles
print("\n## 5. PROFILE OBJECT STRUCTURE")
profile_keys = set()
for m in re.finditer(r'"((?:os|osVariant|resolution|browser|browserVersion|'
                     r'userAgent|userAgentData|doNotTrack|hardwareConcurrency|'
                     r'deviceMemory|maxTouchPoints|language|languages|'
                     r'platform|vendor|plugins|mimeTypes|timezone|'
                     r'webGlVendor|webGlRenderer|canvas|webRtc|'
                     r'mediaDevices|audioContext|fonts|screen|'
                     r'geolocation|dns|connection|battery|bluetooth|'
                     r'speech|gamepads|credentials|permissions|notifications|'
                     r'networkType|storage|indexedDb|serviceWorker|'
                     r'webSocket|webWorker|sharedWorker|webAssembly|'
                     r'proxy|proxyType|noiseType|maskType|realType|'
                     r'passiveFingerprint|activeFingerprint)[^"]*)"', 
                     bundle, re.IGNORECASE):
    s = m.group(1)
    if len(s) < 60:
        profile_keys.add(s)
for k in sorted(profile_keys):
    print(f"  {k}")

# 6. Headless/CLI architecture
print("\n## 6. HEADLESS & CLI ARCHITECTURE")
headless_strings = set()
for m in re.finditer(r'"([^"]*(?:headless|zombie|watchdog|indigo|mla-app|mla_app)[^"]*)"', bundle + express + preload, re.IGNORECASE):
    s = m.group(1)
    if 3 < len(s) < 100 and not s.startswith('http'):
        headless_strings.add(s)
for s in sorted(headless_strings):
    print(f"  {s}")

# 7. Browser Profile Management Flow
print("\n## 7. BROWSER TYPES & PROFILE MANAGEMENT")
# Look for Mimic/Stealthfox references  
mgmt_strings = set()
for m in re.finditer(r'"([^"]*(?:mimic|stealthfox|Mimic|Stealthfox|indigo|Indigo|browserProfile|BrowserProfile|profileId|ProfileId)[^"]*)"', bundle):
    s = m.group(1)
    if 3 < len(s) < 80:
        mgmt_strings.add(s)
for s in sorted(mgmt_strings):
    print(f"  {s}")

# 8. External service URLs  
print("\n## 8. EXTERNAL SERVICE URLs")
ext_urls = set()
for m in re.finditer(r'"(https?://[^"]{5,100})"', bundle + express):
    u = m.group(1)
    if not any(skip in u for skip in ['github.com/expressjs', 'nodejs.org', 
                                       'mozilla.org', 'w3.org', 'ietf.org',
                                       'json-schema.org', 'schemas.xmlsoap',
                                       'opensource.org']):
        ext_urls.add(u)
for u in sorted(ext_urls):
    print(f"  {u}")

# 9. Properties file paths  
print("\n## 9. FILE PATHS & DATA LOCATIONS")
paths = set()
for m in re.finditer(r'"([^"]*(?:\.properties|\.json|\.cfg|/\.[^"]*|app[Dd]ata|[Pp]rofile|[Ll]ocal [Ss]tate|Cookies|History)[^"]*)"', bundle):
    s = m.group(1)
    if 3 < len(s) < 100 and not any(skip in s for skip in ['application/json', 'text/json', 'application/vnd']):
        paths.add(s)
for p in sorted(paths):
    print(f"  {p}")

# 10. Preload script - what renderer can access
print("\n## 10. PRELOAD BRIDGE (Renderer API)")
preload_funcs = set()
for m in re.finditer(r'"([a-zA-Z][a-zA-Z0-9_]{3,40})"', preload[:50000]):
    name = m.group(1)
    if any(kw in name.lower() for kw in ['profile', 'browser', 'proxy', 'start', 'stop',
                                           'create', 'save', 'load', 'config', 'theme',
                                           'app', 'window', 'ipc', 'event', 'channel',
                                           'session', 'cookie', 'update', 'get', 'set']):
        preload_funcs.add(name)
for f in sorted(preload_funcs)[:50]:
    print(f"  {f}")

print("\n" + "=" * 80)
print("ANALYSIS COMPLETE")
