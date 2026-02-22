#!/usr/bin/env python3
"""Audit which core modules are integrated into GUI apps vs orphaned."""
import os, re

TITAN = r"c:\Users\Administrator\Downloads\titan-7\titan-7\iso\config\includes.chroot\opt\titan"
core_dir = os.path.join(TITAN, "core")
apps_dir = os.path.join(TITAN, "apps")

# Get all core modules
core_modules = set()
for f in os.listdir(core_dir):
    if f.endswith('.py') and f != '__init__.py' and not f.startswith('test_'):
        core_modules.add(f[:-3])

# For each app, find which core modules it imports
app_imports = {}
all_gui_used = set()

for app in sorted(os.listdir(apps_dir)):
    if not app.endswith('.py'):
        continue
    path = os.path.join(apps_dir, app)
    with open(path, 'r', encoding='utf-8', errors='ignore') as fh:
        content = fh.read()
    
    imported = set()
    for m in re.finditer(r'from\s+(\w+)\s+import', content):
        mod = m.group(1)
        if mod in core_modules:
            imported.add(mod)
    for m in re.finditer(r'import\s+(\w+)', content):
        mod = m.group(1)
        if mod in core_modules:
            imported.add(mod)
    
    if imported:
        app_imports[app] = sorted(imported)
        all_gui_used.update(imported)

orphaned = sorted(core_modules - all_gui_used)

print(f"TOTAL CORE MODULES: {len(core_modules)}")
print(f"USED IN GUI APPS:   {len(all_gui_used)}")
print(f"ORPHANED FROM GUI:  {len(orphaned)}")
print()

# Show each app and its module count
print("=" * 70)
print("APP -> MODULE INTEGRATION MAP")
print("=" * 70)
for app, mods in sorted(app_imports.items()):
    print(f"\n{app} ({len(mods)} core modules):")
    for m in mods:
        print(f"  + {m}")

print()
print("=" * 70)
print(f"ORPHANED MODULES ({len(orphaned)} modules with NO GUI integration):")
print("=" * 70)
for m in orphaned:
    # Get main class from the module
    mod_path = os.path.join(core_dir, m + ".py")
    classes = []
    try:
        with open(mod_path, 'r', encoding='utf-8', errors='ignore') as fh:
            for line in fh:
                cm = re.match(r'^class\s+(\w+)', line)
                if cm:
                    classes.append(cm.group(1))
    except:
        pass
    cls_str = ", ".join(classes[:3]) if classes else "?"
    size_kb = os.path.getsize(mod_path) // 1024
    print(f"  !! {m}.py ({size_kb}KB) -> {cls_str}")

# Count tabs in each GUI app
print()
print("=" * 70)
print("APP TAB ANALYSIS")
print("=" * 70)
for app in sorted(os.listdir(apps_dir)):
    if not app.endswith('.py'):
        continue
    path = os.path.join(apps_dir, app)
    with open(path, 'r', encoding='utf-8', errors='ignore') as fh:
        content = fh.read()
    
    tabs = re.findall(r'addTab\([^,]+,\s*["\']([^"\']+)', content)
    size_kb = os.path.getsize(path) // 1024
    is_main = 'QMainWindow' in content
    has_dep = 'DEPRECATED' in content[:500]
    
    if tabs or is_main:
        dep = " [DEPRECATED]" if has_dep else ""
        print(f"\n{app} ({size_kb}KB){dep}:")
        if tabs:
            for t in tabs:
                print(f"  TAB: {t}")
        else:
            print(f"  (no tabs / utility)")
