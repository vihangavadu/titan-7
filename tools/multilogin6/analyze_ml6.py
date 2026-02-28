"""Reverse engineer Multilogin 6 bundle.js to extract architecture details."""
import re
import json
import os

BASE = r'C:\Users\Administrator\Downloads\titan-7\titan-7\titan-7\tools\multilogin6\extracted\app_src'

def read_file(path):
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        return f.read()

# Read all dist files
bundle = read_file(os.path.join(BASE, 'dist', 'bundle.js'))
express = read_file(os.path.join(BASE, 'dist', 'express-server.js'))
preload = read_file(os.path.join(BASE, 'dist', 'preload.js'))
zombie = read_file(os.path.join(BASE, 'dist', 'zombie-killer.js'))

all_code = bundle + express + preload + zombie

print("=" * 80)
print("MULTILOGIN 6.5.0 REVERSE ENGINEERING ANALYSIS")
print("=" * 80)

# 1. Find all URL patterns (API endpoints, external services)
print("\n## 1. API ENDPOINTS & URLs")
urls = set()
for m in re.finditer(r'"((?:/api/|https?://)[^"]{3,120})"', all_code):
    urls.add(m.group(1))
for u in sorted(urls):
    print(f"  {u}")

# 2. Find string literals related to profiles
print("\n## 2. PROFILE-RELATED STRINGS")
profile_strings = set()
for m in re.finditer(r'"([^"]*(?:profile|Profile)[^"]{0,60})"', all_code):
    s = m.group(1)
    if len(s) > 3 and len(s) < 80 and not s.startswith('http'):
        profile_strings.add(s)
for s in sorted(profile_strings)[:50]:
    print(f"  {s}")

# 3. Find fingerprint-related strings
print("\n## 3. FINGERPRINT / ANTI-DETECT STRINGS")
fp_strings = set()
for pat in ['fingerprint', 'canvas', 'webgl', 'webrtc', 'geolocation', 'timezone',
            'navigator', 'screen', 'audio', 'font', 'useragent', 'user.agent',
            'hardwareConcurrency', 'deviceMemory', 'platform']:
    for m in re.finditer(rf'"([^"]*{pat}[^"]*)"', all_code, re.IGNORECASE):
        s = m.group(1)
        if 3 < len(s) < 80:
            fp_strings.add(s)
for s in sorted(fp_strings)[:60]:
    print(f"  {s}")

# 4. Browser-related strings
print("\n## 4. BROWSER TYPES & MANAGEMENT")
browser_strings = set()
for pat in ['mimic', 'stealthfox', 'chromium', 'firefox', 'browser_type',
            'browserType', 'Mimic', 'Stealthfox']:
    for m in re.finditer(rf'"([^"]*{pat}[^"]*)"', all_code, re.IGNORECASE):
        s = m.group(1)
        if 3 < len(s) < 80:
            browser_strings.add(s)
for s in sorted(browser_strings)[:40]:
    print(f"  {s}")

# 5. Proxy-related
print("\n## 5. PROXY & NETWORK STRINGS")
proxy_strings = set()
for pat in ['proxy', 'socks', 'http_proxy', 'proxyType', 'proxy_type']:
    for m in re.finditer(rf'"([^"]*{pat}[^"]*)"', all_code, re.IGNORECASE):
        s = m.group(1)
        if 3 < len(s) < 80:
            proxy_strings.add(s)
for s in sorted(proxy_strings)[:30]:
    print(f"  {s}")

# 6. Cookie-related
print("\n## 6. COOKIE & STORAGE STRINGS")
cookie_strings = set()
for pat in ['cookie', 'localStorage', 'indexedDB', 'storage']:
    for m in re.finditer(rf'"([^"]*{pat}[^"]*)"', all_code, re.IGNORECASE):
        s = m.group(1)
        if 3 < len(s) < 80 and 'node_modules' not in s:
            cookie_strings.add(s)
for s in sorted(cookie_strings)[:30]:
    print(f"  {s}")

# 7. Express server routes
print("\n## 7. EXPRESS SERVER ROUTES")
routes = set()
for m in re.finditer(r'\.(get|post|put|delete|patch)\s*\(\s*"(/[^"]+)"', express):
    method = m.group(1).upper()
    path = m.group(2)
    routes.add(f"{method} {path}")
# Also look for route patterns in the minified code
for m in re.finditer(r'"((?:GET|POST|PUT|DELETE|PATCH))"[^"]*"(/[^"]+)"', express):
    routes.add(f"{m.group(1)} {m.group(2)}")
for r_str in sorted(routes):
    print(f"  {r_str}")

# 8. Key class/module names from the bundle
print("\n## 8. KEY MODULE/CLASS NAMES")
class_names = set()
for m in re.finditer(r'\.prototype\.(\w{4,40})\s*=', bundle):
    name = m.group(1)
    if any(kw in name.lower() for kw in ['profile', 'browser', 'proxy', 'fingerprint',
                                           'cookie', 'start', 'stop', 'create', 'update',
                                           'delete', 'launch', 'save', 'load', 'import',
                                           'export', 'clone', 'share', 'team', 'session']):
        class_names.add(name)
for n in sorted(class_names)[:50]:
    print(f"  {n}")

# 9. Configuration/settings keys
print("\n## 9. CONFIGURATION KEYS")
config_keys = set()
for m in re.finditer(r'"((?:dns|doNotTrack|mediaDevices|webRTC|canvas|webGL|'
                     r'audio|fonts|screen|timezone|language|geolocation|'
                     r'navigator|storage|plugins|hardwareConcurrency|'
                     r'deviceMemory|platform|vendor|maxTouchPoints|'
                     r'connection|battery|bluetooth)[^"]*)"', all_code, re.IGNORECASE):
    s = m.group(1)
    if 3 < len(s) < 60:
        config_keys.add(s)
for k in sorted(config_keys):
    print(f"  {k}")

# 10. Automation/Selenium detection
print("\n## 10. AUTOMATION & DETECTION STRINGS")
auto_strings = set()
for pat in ['selenium', 'puppeteer', 'headless', 'automation', 'webdriver',
            'zombie', 'kill', 'spawn', 'child_process', 'execFile']:
    for m in re.finditer(rf'"([^"]*{pat}[^"]*)"', all_code, re.IGNORECASE):
        s = m.group(1)
        if 3 < len(s) < 80:
            auto_strings.add(s)
for s in sorted(auto_strings)[:30]:
    print(f"  {s}")

# 11. Look for JSON config structures in the code
print("\n## 11. EMBEDDED JSON STRUCTURES")
# Find objects with fingerprint-related keys
for m in re.finditer(r'\{[^{}]*(?:canvas|webgl|webrtc|geolocation|timezone|fonts|screen|audio|navigator)[^{}]*\}', bundle[:500000]):
    s = m.group(0)
    if len(s) > 30 and len(s) < 500:
        # Check if it has multiple relevant keys
        relevant = sum(1 for kw in ['canvas', 'webgl', 'webrtc', 'geolocation', 'timezone',
                                     'fonts', 'screen', 'audio', 'navigator', 'dns', 'plugins']
                       if kw in s.lower())
        if relevant >= 2:
            print(f"  {s[:200]}...")
            print()

print("\n## 12. FILE/PATH REFERENCES")
path_strings = set()
for m in re.finditer(r'"([^"]*(?:\.json|\.properties|\.cfg|\.ini|\.conf|Preferences|Local State|Cookies|History|Login Data|Web Data)[^"]*)"', all_code):
    s = m.group(1)
    if 3 < len(s) < 100:
        path_strings.add(s)
for s in sorted(path_strings):
    print(f"  {s}")

print("\n" + "=" * 80)
print("ANALYSIS COMPLETE")
print("=" * 80)
