"""Extract Angular component names and UI features from Multilogin 6 renderer."""
import re
import os

BASE = r'C:\Users\Administrator\Downloads\titan-7\titan-7\titan-7\tools\multilogin6\extracted\app_src'
main_js = os.path.join(BASE, 'renderer', 'multilogin', 'en', 'main.7a8d80207b5bcadd.js')

with open(main_js, 'r', encoding='utf-8', errors='replace') as f:
    code = f.read()

print("=" * 80)
print("MULTILOGIN 6 RENDERER (Angular) - UI COMPONENT ANALYSIS")
print("=" * 80)

# 1. Angular component selectors
print("\n## 1. ANGULAR COMPONENT SELECTORS")
selectors = set()
for m in re.finditer(r'selector:\s*"([^"]+)"', code):
    selectors.add(m.group(1))
for s in sorted(selectors):
    print(f"  {s}")

# 2. Component class names
print("\n## 2. COMPONENT CLASS NAMES")
components = set()
for m in re.finditer(r'class\s+(\w+Component)\b', code):
    components.add(m.group(1))
# Also look for minified component references
for m in re.finditer(r'"(\w+Component)"', code):
    components.add(m.group(1))
for c in sorted(components):
    print(f"  {c}")

# 3. Service class names
print("\n## 3. SERVICE CLASSES")
services = set()
for m in re.finditer(r'class\s+(\w+Service)\b', code):
    services.add(m.group(1))
for m in re.finditer(r'"(\w+Service)"', code):
    services.add(m.group(1))
for s in sorted(services):
    print(f"  {s}")

# 4. Route paths
print("\n## 4. ANGULAR ROUTES")
routes = set()
for m in re.finditer(r'path:\s*"([^"]*)"', code):
    routes.add(m.group(1))
for r_str in sorted(routes):
    if r_str and len(r_str) < 60:
        print(f"  /{r_str}")

# 5. UI feature strings (buttons, labels, menus)
print("\n## 5. UI FEATURE LABELS")
labels = set()
for pat in ['Create.*profile', 'Edit.*profile', 'Clone.*profile', 'Share.*profile',
            'Delete.*profile', 'Start.*browser', 'Stop.*browser', 'Transfer.*profile',
            'Import.*cookie', 'Export.*cookie', 'Proxy.*setting', 'Fingerprint',
            'Browser.*profile', 'Team.*member', 'Quick.*profile', 'Group',
            'Folder', 'Tag', 'Note', 'Status', 'Active.*session',
            'Canvas', 'WebGL', 'WebRTC', 'Geolocation', 'Timezone',
            'Font', 'Audio', 'Navigator', 'Screen', 'Language',
            'User.?[Aa]gent', 'Resolution', 'Cookie.*import', 'Cookie.*export',
            'Mimic', 'Stealthfox', 'Automation', 'Selenium', 'Puppeteer',
            'REST.*API', 'Local.*API', 'Headless']:
    for m in re.finditer(rf'"([^"]*{pat}[^"]*)"', code, re.IGNORECASE):
        s = m.group(1)
        if 3 < len(s) < 80:
            labels.add(s)
for l in sorted(labels)[:60]:
    print(f"  {l}")

# 6. API/HTTP calls from renderer
print("\n## 6. HTTP API CALLS FROM RENDERER")
api_calls = set()
for m in re.finditer(r'"((?:GET|POST|PUT|DELETE|PATCH))"[^"]{0,50}"([^"]+)"', code):
    api_calls.add(f"{m.group(1)} {m.group(2)}")
for m in re.finditer(r'\.(?:get|post|put|delete|patch)\s*\(\s*["`]([^"`]+)["`]', code):
    api_calls.add(m.group(1))
# URL patterns with localhost
for m in re.finditer(r'"(https?://(?:127\.0\.0\.1|localhost)[^"]*)"', code):
    api_calls.add(m.group(1))
for a in sorted(api_calls)[:40]:
    print(f"  {a}")

# 7. Modal/Dialog names
print("\n## 7. MODALS & DIALOGS")
modals = set()
for m in re.finditer(r'"(\w*(?:Dialog|Modal|Popup|Sheet|Drawer)\w*)"', code):
    modals.add(m.group(1))
for m_str in sorted(modals):
    print(f"  {m_str}")

# 8. Feature flags / settings
print("\n## 8. FINGERPRINT CONFIGURATION FIELDS")
fp_fields = set()
for m in re.finditer(r'"((?:canvas|webgl|webrtc|geolocation|timezone|navigator|'
                     r'fonts|audio|screen|language|doNotTrack|hardwareConcurrency|'
                     r'deviceMemory|platform|vendor|plugins|mediaDevices|'
                     r'connection|battery|speech|bluetooth|storage|'
                     r'maxTouchPoints|colorDepth|pixelRatio)[^"]*)"', code, re.IGNORECASE):
    s = m.group(1)
    if len(s) < 50:
        fp_fields.add(s)
for f in sorted(fp_fields):
    print(f"  {f}")

print("\n" + "=" * 80)
print("ANALYSIS COMPLETE")
