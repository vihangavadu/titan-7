#!/usr/bin/env python3
"""Deep audit of Titan X VPS codebase for detectable vectors and hidden issues."""
import os
import re
import sys

core_dir = '/opt/titan/src/core'
apps_dir = '/opt/titan/src/apps'
issues = []


def scan_file(fpath, relpath):
    try:
        content = open(fpath).read()
        lines = content.split('\n')
    except Exception:
        return

    for i, line in enumerate(lines, 1):
        ln = line.strip()

        # 1. DEBUG flags left on
        if re.search(r'DEBUG\s*=\s*True', ln) and not ln.startswith('#'):
            issues.append(('DEBUG_FLAG', relpath, i, ln[:100]))

        # 2. Hardcoded test/dummy API keys
        if re.search(r'(sk_test_|pk_test_|AKIAIOSFODNN|xoxb-|ghp_|Bearer test)', ln):
            if not ln.startswith('#'):
                issues.append(('TEST_API_KEY', relpath, i, ln[:100]))

        # 3. Wrong path references (/opt/titan/core instead of /opt/titan/src/core)
        if '/opt/titan/core' in ln and '/opt/titan/src/core' not in ln:
            if not ln.startswith('#'):
                issues.append(('WRONG_PATH', relpath, i, ln[:120]))

        # 4. Detectable user-agent strings
        if 'User-Agent' in ln and re.search(r'(python-requests|urllib3|aiohttp)', ln, re.I):
            issues.append(('DETECTABLE_UA', relpath, i, ln[:120]))

        # 5. Debug print statements
        if ln.startswith('print(') and 'debug' in ln.lower():
            issues.append(('DEBUG_PRINT', relpath, i, ln[:120]))

        # 6. Hardcoded passwords/secrets (not from env)
        pw_match = re.search(r'(password|passwd|secret)\s*=\s*["\']([^"\']{4,})', ln, re.I)
        if pw_match and not ln.startswith('#'):
            if 'environ' not in ln and 'getenv' not in ln and 'config' not in ln.lower():
                if 'example' not in ln.lower() and 'placeholder' not in ln.lower():
                    issues.append(('HARDCODED_SECRET', relpath, i, ln[:120]))

        # 7. HTTP instead of HTTPS for external URLs (not localhost)
        http_match = re.search(r'http://(?!localhost|127\.0\.0\.1|0\.0\.0\.0)[a-zA-Z0-9]', ln)
        if http_match and not ln.startswith('#') and 'example' not in ln.lower():
            if '"""' not in ln and "'''" not in ln and 'doc' not in ln.lower():
                issues.append(('HTTP_NOT_HTTPS', relpath, i, ln[:140]))

        # 8. Detectable Titan strings in network-facing code
        if re.search(r'["\']Titan["\']|["\']TITAN["\']', ln):
            if 'header' in ln.lower() or 'user.agent' in ln.lower() or 'x-' in ln.lower():
                issues.append(('TITAN_IN_HEADER', relpath, i, ln[:120]))

        # 9. Hardcoded IPs that could be VPS
        if re.search(r'72\.62\.72\.48', ln) and not ln.startswith('#'):
            issues.append(('HARDCODED_VPS_IP', relpath, i, ln[:120]))

        # 10. Sleep(0) or no-delay patterns in transaction code
        if 'sleep(0)' in ln and not ln.startswith('#'):
            issues.append(('ZERO_DELAY', relpath, i, ln[:100]))

        # 11. TODO/FIXME/HACK markers that indicate unfinished code
        if re.search(r'#\s*(TODO|FIXME|HACK|XXX|BROKEN):', ln, re.I):
            issues.append(('TODO_MARKER', relpath, i, ln[:120]))

        # 12. Bare except clauses (swallows errors silently)
        if ln == 'except:' or ln.startswith('except:'):
            issues.append(('BARE_EXCEPT', relpath, i, ln[:80]))

        # 13. Hardcoded port numbers that conflict
        if re.search(r'port\s*=\s*80\b', ln) and not ln.startswith('#'):
            if 'default' not in ln.lower() and '8080' not in ln:
                issues.append(('PORT_80_HARDCODED', relpath, i, ln[:100]))


# Scan core and apps
for root_dir in [core_dir, apps_dir]:
    if not os.path.isdir(root_dir):
        print(f"SKIP: {root_dir} not found")
        continue
    for f in sorted(os.listdir(root_dir)):
        if f.endswith('.py'):
            scan_file(os.path.join(root_dir, f), f'{os.path.basename(root_dir)}/{f}')

# Also scan bridge APIs
bridge_dirs = [
    '/opt/titan/tools/cerberus_appx',
    '/opt/titan/tools/kyc_appx',
    '/opt/titan/tools/multilogin6/genesis_appx',
]
for bd in bridge_dirs:
    if os.path.isdir(bd):
        for f in sorted(os.listdir(bd)):
            if f.endswith('.py'):
                scan_file(os.path.join(bd, f), f'tools/{os.path.basename(bd)}/{f}')

# Summary
cats = {}
for cat, path, line, text in issues:
    cats.setdefault(cat, []).append((path, line, text))

print(f'TOTAL ISSUES: {len(issues)}')
print(f'CATEGORIES: {len(cats)}')
print()
for cat in sorted(cats.keys()):
    items = cats[cat]
    print(f'[{cat}] ({len(items)} found)')
    for path, line, text in items[:8]:
        print(f'  {path}:{line} -> {text}')
    if len(items) > 8:
        print(f'  ... and {len(items)-8} more')
    print()
