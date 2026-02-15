#!/usr/bin/env python3
"""
LUCID EMPIRE - Real-World Profile Fabrication Test
Tests actual profile creation with all Firefox Research Guide features.
"""

import tempfile
import shutil
from pathlib import Path
from backend.modules import (
    FirefoxProfileInjectorV2,
    HistoryEntryV2,
    CookieEntryV2,
    LocalStorageEntryV2,
    create_commerce_cookies_v2,
    mozilla_url_hash,
    generate_rev_host
)

print('='*60)
print('REAL-WORLD PROFILE FABRICATION TEST')
print('='*60)

# Create temp profile
temp_dir = tempfile.mkdtemp(prefix='lucid_prod_test_')
print(f'\n[1] Created test profile: {temp_dir}')

try:
    # Initialize
    injector = FirefoxProfileInjectorV2(profile_path=temp_dir, aging_days=90)
    
    # Age profile
    injector.age_profile()
    print('[2] Profile aged (times.json created)')
    
    # Generate history (reduced for speed)
    count = injector.generate_realistic_history(days=5, persona='shopper')
    print(f'[3] Injected {count} realistic history entries')
    
    # Commerce cookies
    cookies = create_commerce_cookies_v2('production-test-uuid', 90)
    for c in cookies:
        injector.inject_cookie(c)
    print(f'[4] Injected {len(cookies)} commerce trust cookies')
    
    # LSNG localStorage
    injector.inject_local_storage(LocalStorageEntryV2(
        origin='https://stripe.com',
        key='deviceId',
        value='{"id":"dev_prod_12345","created":1700000000}'
    ))
    print('[5] Injected LSNG localStorage (Snappy compressed)')
    
    # Verify structure
    profile_path = Path(temp_dir)
    checks = [
        ('times.json', profile_path / 'times.json'),
        ('places.sqlite', profile_path / 'places.sqlite'),
        ('cookies.sqlite', profile_path / 'cookies.sqlite'),
        ('LSNG storage', profile_path / 'storage' / 'default'),
        ('.metadata-v2', profile_path / 'storage' / 'default' / 'https+++stripe.com' / '.metadata-v2'),
        ('data.sqlite', profile_path / 'storage' / 'default' / 'https+++stripe.com' / 'ls' / 'data.sqlite'),
    ]
    
    print('\n[6] Structure Verification:')
    all_ok = True
    for name, path in checks:
        exists = path.exists()
        status = '[OK]' if exists else '[MISSING]'
        print(f'    {status} {name}')
        if not exists:
            all_ok = False
    
    # Test URL hash
    url = 'https://www.amazon.com/dp/B08N5WRWNW'
    hash_val = mozilla_url_hash(url)
    rev = generate_rev_host('www.amazon.com')
    print(f'\n[7] URL Hash Test:')
    print(f'    URL: {url}')
    print(f'    Hash: {hash_val}')
    print(f'    rev_host: {rev}')
    
    print('\n' + '='*60)
    if all_ok:
        print('SUCCESS: REAL-WORLD PROFILE FABRICATION COMPLETE')
    else:
        print('WARNING: Some components missing')
    print('='*60)
    
finally:
    shutil.rmtree(temp_dir, ignore_errors=True)
    print('\n[Cleanup] Temp profile removed')
