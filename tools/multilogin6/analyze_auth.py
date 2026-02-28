"""Analyze ML6 bundle.js for auth/login patterns to understand what to patch."""
import re
import os

BASE = r'C:\Users\Administrator\Downloads\titan-7\titan-7\titan-7\tools\multilogin6\extracted\app_src'

def read_file(path):
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        return f.read()

bundle = read_file(os.path.join(BASE, 'dist', 'bundle.js'))
express = read_file(os.path.join(BASE, 'dist', 'express-server.js'))

print("=" * 80)
print("ML6 AUTH/LOGIN ANALYSIS")
print("=" * 80)

# 1. Find auth token patterns in bundle
print("\n## 1. AUTH TOKEN PATTERNS (bundle.js)")
for m in re.finditer(r'apiToken|authToken|bearerToken|accessToken|refreshToken', bundle):
    start = max(0, m.start() - 80)
    end = min(len(bundle), m.end() + 80)
    ctx = bundle[start:end].replace('\n', ' ')
    print(f"  ...{ctx}...")
    print()

# 2. Find login/auth flow in bundle
print("\n## 2. LOGIN FLOW PATTERNS")
for pat in ['isAuthenticated', 'isLoggedIn', 'loginRequired', 'requireAuth',
            'checkAuth', 'validateToken', 'onToken', 'signOut', 'logOut']:
    for m in re.finditer(pat, bundle, re.IGNORECASE):
        start = max(0, m.start() - 60)
        end = min(len(bundle), m.end() + 60)
        ctx = bundle[start:end].replace('\n', ' ')
        print(f"  [{pat}] ...{ctx}...")
        print()

# 3. Express server auth middleware
print("\n## 3. EXPRESS AUTH MIDDLEWARE")
for pat in ['apiToken', 'authorization', 'auth', 'token', 'bearer']:
    for m in re.finditer(rf'"{pat}"', express, re.IGNORECASE):
        start = max(0, m.start() - 80)
        end = min(len(express), m.end() + 80)
        ctx = express[start:end].replace('\n', ' ')
        print(f"  [{pat}] ...{ctx}...")
        print()

# 4. Config/startup patterns - how the app initializes
print("\n## 4. APP STARTUP / CONFIG PATTERNS")
for pat in ['headlessPort', 'expressPort', 'startExpress', 'config.brand',
            'app.properties', 'splashScreen', 'showSplash', 'mainWindow',
            'BrowserWindow', 'loadURL', 'loadFile']:
    count = 0
    for m in re.finditer(pat, bundle):
        if count >= 2:
            break
        start = max(0, m.start() - 60)
        end = min(len(bundle), m.end() + 60)
        ctx = bundle[start:end].replace('\n', ' ')
        print(f"  [{pat}] ...{ctx}...")
        print()
        count += 1

# 5. Find the main window URL loading
print("\n## 5. MAIN WINDOW URL LOADING")
for pat in ['loadURL', 'loadFile', 'getUiPath', 'splashScreen', 'index.html']:
    for m in re.finditer(pat, bundle):
        start = max(0, m.start() - 100)
        end = min(len(bundle), m.end() + 100)
        ctx = bundle[start:end].replace('\n', ' ')
        print(f"  [{pat}] ...{ctx}...")
        print()

# 6. Brand/name references
print("\n## 6. BRAND REFERENCES")
for pat in ['Multilogin', 'multilogin', 'MlaApp', 'mla-app']:
    count = bundle.count(pat)
    print(f"  '{pat}' appears {count} times in bundle.js")

for pat in ['Multilogin', 'multilogin', 'MlaApp']:
    count = express.count(pat)
    print(f"  '{pat}' appears {count} times in express-server.js")

# 7. Renderer main.js - auth routes
print("\n## 7. RENDERER AUTH ROUTES")
renderer_main = read_file(os.path.join(BASE, 'renderer', 'multilogin', 'en', 'main.7a8d80207b5bcadd.js'))
for pat in ['login', 'signup', 'forgot', 'reset', 'confirm', 'migration', 'canActivate', 'AuthGuard', 'isAuth']:
    count = 0
    for m in re.finditer(pat, renderer_main, re.IGNORECASE):
        if count >= 3:
            break
        start = max(0, m.start() - 60)
        end = min(len(renderer_main), m.end() + 60)
        ctx = renderer_main[start:end].replace('\n', ' ')
        print(f"  [{pat}] ...{ctx}...")
        count += 1
    if count:
        print()

print("\n" + "=" * 80)
print("ANALYSIS COMPLETE")
