#!/usr/bin/env python3
"""
TITAN V8.1 — Real End-to-End Test with Deep Storage Analysis
================================================================
1. Generate a REAL profile with sample persona data
2. Run Cerberus card validation pipeline
3. Inject purchase history
4. Run Integration Bridge assembly
5. Deep-analyze ALL generated browser storage files
6. Report every issue and gap found
"""
import os, sys, json, sqlite3, shutil, time, hashlib, struct, asyncio
from pathlib import Path
from datetime import datetime, timedelta, timezone
from collections import defaultdict

sys.path.insert(0, '/opt/titan')
os.environ.setdefault('TITAN_CLOUD_URL', 'http://127.0.0.1:11434/v1')
os.environ.setdefault('TITAN_API_KEY', 'ollama')
os.environ.setdefault('TITAN_MODEL', 'qwen2.5:7b')
os.environ.setdefault('DISPLAY', ':1')

PROFILE_DIR = '/tmp/titan_real_e2e'
PROFILE_UUID = 'E2E-REAL-001'
REPORT = {'issues': [], 'warnings': [], 'stats': {}, 'passes': []}

def issue(category, msg):
    REPORT['issues'].append(f'[{category}] {msg}')
    print(f'  ❌ ISSUE [{category}] {msg}')

def warn(category, msg):
    REPORT['warnings'].append(f'[{category}] {msg}')
    print(f'  ⚠ WARN [{category}] {msg}')

def ok(category, msg):
    REPORT['passes'].append(f'[{category}] {msg}')
    print(f'  ✓ OK [{category}] {msg}')

# ═══════════════════════════════════════════════════════════════
# SAMPLE PERSONA DATA (realistic US-based profile)
# ═══════════════════════════════════════════════════════════════
PERSONA = {
    'name': 'Marcus D. Rivera',
    'email': 'marcus.d.rivera94@gmail.com',
    'phone': '+15125559847',
    'address': '3201 RED RIVER ST',
    'apt': 'APT 204',
    'city': 'AUSTIN',
    'state': 'TX',
    'zip': '78705',
    'country': 'US',
    'dob': '1994-06-15',
}

CARD = {
    'number': '4532015112830366',   # Visa test (Luhn-valid)
    'exp_month': 11,
    'exp_year': 2027,
    'cvv': '847',
    'bin': '453201',
    'network': 'visa',
    'last4': '0366',
}

TARGET = 'eneba'
PROFILE_AGE_DAYS = 120

print('╔══════════════════════════════════════════════════════════════╗')
print('║  TITAN V8.1 — REAL END-TO-END TEST + STORAGE ANALYSIS    ║')
print('╚══════════════════════════════════════════════════════════════╝')

# ═══════════════════════════════════════════════════════════════
# STEP 1: GENERATE PROFILE
# ═══════════════════════════════════════════════════════════════
print('\n' + '='*65)
print('STEP 1: GENERATE FULL BROWSER PROFILE')
print('='*65)

if os.path.exists(PROFILE_DIR):
    shutil.rmtree(PROFILE_DIR)
os.makedirs(PROFILE_DIR, exist_ok=True)

from core.advanced_profile_generator import AdvancedProfileGenerator, AdvancedProfileConfig

gen = AdvancedProfileGenerator(output_dir=PROFILE_DIR)
cfg = AdvancedProfileConfig(
    profile_uuid=PROFILE_UUID,
    persona_name=PERSONA['name'],
    persona_email=PERSONA['email'],
    billing_address={
        'address': PERSONA['address'],
        'city': PERSONA['city'],
        'state': PERSONA['state'],
        'zip': PERSONA['zip'],
        'country': PERSONA['country'],
    },
    profile_age_days=PROFILE_AGE_DAYS,
    localstorage_size_mb=12,
    indexeddb_size_mb=6,
    cache_size_mb=8,
)

t0 = time.time()
profile_result = gen.generate(cfg)
gen_time = time.time() - t0

profile_path = None
if hasattr(profile_result, 'profile_path'):
    profile_path = str(profile_result.profile_path)
elif hasattr(profile_result, 'path'):
    profile_path = str(profile_result.path)
else:
    profile_path = os.path.join(PROFILE_DIR, PROFILE_UUID)

print(f'  Profile generated in {gen_time:.1f}s at: {profile_path}')
REPORT['stats']['generation_time_sec'] = round(gen_time, 1)

if not os.path.exists(profile_path):
    issue('GEN', f'Profile path does not exist: {profile_path}')
    sys.exit(1)

# ═══════════════════════════════════════════════════════════════
# STEP 2: CERBERUS CARD VALIDATION
# ═══════════════════════════════════════════════════════════════
print('\n' + '='*65)
print('STEP 2: CERBERUS CARD VALIDATION')
print('='*65)

from core.cerberus_core import CerberusValidator, CardAsset

cv = CerberusValidator()
card = CardAsset(
    number=CARD['number'],
    exp_month=CARD['exp_month'],
    exp_year=CARD['exp_year'],
    cvv=CARD['cvv'],
    holder_name=PERSONA['name'],
)

t0 = time.time()
try:
    validation_result = asyncio.run(cv.validate(card))
except TypeError:
    validation_result = cv.validate(card)
cerb_time = time.time() - t0
print(f'  Validation completed in {cerb_time*1000:.0f}ms')
print(f'  Result: {str(validation_result)[:200]}')
REPORT['stats']['cerberus_time_ms'] = round(cerb_time * 1000)

# BIN Scoring
from core import score_bin
bin_result = score_bin(CARD['bin'])
print(f'  BIN Score: {getattr(bin_result, "overall_score", "?")}')
print(f'  Bank: {getattr(bin_result, "bank", "?")}')
print(f'  Level: {getattr(bin_result, "card_level", "?")}')
REPORT['stats']['bin_score'] = getattr(bin_result, 'overall_score', 0)

# AVS Check
from core import check_avs
avs_result = check_avs(
    card_address=f'{PERSONA["address"]} {PERSONA["apt"]}',
    card_zip=PERSONA['zip'],
    card_state=PERSONA['state'],
    input_address=f'{PERSONA["address"]} {PERSONA["apt"]}',
    input_zip=PERSONA['zip'],
    input_state=PERSONA['state'],
)
print(f'  AVS Code: {avs_result.avs_code}, Confidence: {avs_result.confidence}')

# Geo Match
from core import check_geo
geo_result = check_geo(
    billing_state='TX',
    exit_ip_state='TX',
    browser_timezone='America/Chicago',
)
print(f'  Geo Match: consistent={geo_result["consistent"]}, score={geo_result["score"]}')

if not geo_result['consistent']:
    issue('GEO', 'Geo mismatch for same-state TX/TX/Chicago')

# MaxDrain
from core.cerberus_enhanced import MaxDrainEngine
md = MaxDrainEngine()
drain_plan = md.generate_plan(bin_number=CARD['bin'], amount_limit=500.0, country='US')
print(f'  MaxDrain Plan: {str(drain_plan)[:150]}')

# ═══════════════════════════════════════════════════════════════
# STEP 3: INJECT PURCHASE HISTORY
# ═══════════════════════════════════════════════════════════════
print('\n' + '='*65)
print('STEP 3: INJECT PURCHASE HISTORY')
print('='*65)

from core import inject_purchase_history

t0 = time.time()
purchase_result = inject_purchase_history(
    profile_path=profile_path,
    full_name=PERSONA['name'],
    email=PERSONA['email'],
    card_last_four=CARD['last4'],
    card_network=CARD['network'],
    card_exp=f'{CARD["exp_month"]}/{CARD["exp_year"] % 100}',
    billing_address=PERSONA['address'],
    billing_city=PERSONA['city'],
    billing_state=PERSONA['state'],
    billing_zip=PERSONA['zip'],
    num_purchases=8,
    profile_age_days=PROFILE_AGE_DAYS,
)
purchase_time = time.time() - t0
print(f'  Purchase history injected in {purchase_time*1000:.0f}ms')
print(f'  Result: {str(purchase_result)[:200]}')
REPORT['stats']['purchase_inject_time_ms'] = round(purchase_time * 1000)

# ═══════════════════════════════════════════════════════════════
# STEP 4: INTEGRATION BRIDGE ASSEMBLY
# ═══════════════════════════════════════════════════════════════
print('\n' + '='*65)
print('STEP 4: INTEGRATION BRIDGE ASSEMBLY')
print('='*65)

from core.integration_bridge import TitanIntegrationBridge, BridgeConfig

bridge_cfg = BridgeConfig(
    profile_uuid=PROFILE_UUID,
    profile_path=Path(profile_path),
    target_domain='eneba.com',
    billing_address={
        'address': PERSONA['address'],
        'city': PERSONA['city'],
        'state': PERSONA['state'],
        'zip': PERSONA['zip'],
        'country': PERSONA['country'],
    },
    browser_type='firefox',
)
bridge = TitanIntegrationBridge(config=bridge_cfg)
bridge_methods = [m for m in dir(bridge) if not m.startswith('_') and callable(getattr(bridge, m))]
print(f'  Bridge instantiated with {len(bridge_methods)} methods: {bridge_methods[:8]}')

# Try running preflight
from core.preflight_validator import PreFlightValidator
pf = PreFlightValidator()
pf_methods = [m for m in dir(pf) if not m.startswith('_') and callable(getattr(pf, m))]
print(f'  PreFlight validator: {len(pf_methods)} check methods')

# Fingerprint injection
from core.fingerprint_injector import FingerprintInjector, FingerprintConfig
try:
    fp_cfg = FingerprintConfig()
    fi = FingerprintInjector(config=fp_cfg)
except Exception:
    try:
        fi = FingerprintInjector(FingerprintConfig())
    except Exception as e:
        print(f'  FingerprintInjector: skipped ({e})')
        fi = None
if fi:
    fi_methods = [m for m in dir(fi) if not m.startswith('_') and callable(getattr(fi, m))]
    print(f'  FingerprintInjector: {len(fi_methods)} methods')

# Form autofill injection
try:
    from core.form_autofill_injector import FormAutofillInjector
    fai = FormAutofillInjector()
    fai_methods = [m for m in dir(fai) if not m.startswith('_') and callable(getattr(fai, m))]
    print(f'  FormAutofillInjector: {len(fai_methods)} methods')
except Exception as e:
    print(f'  FormAutofillInjector: skipped ({e})')

# ═══════════════════════════════════════════════════════════════
# STEP 5: DEEP STORAGE ANALYSIS
# ═══════════════════════════════════════════════════════════════
print('\n' + '='*65)
print('STEP 5: DEEP BROWSER STORAGE ANALYSIS')
print('='*65)

# --- 5A: File Inventory ---
print('\n--- 5A: File Inventory ---')
file_inventory = {}
total_size = 0
for root, dirs, files in os.walk(profile_path):
    for f in files:
        fp = os.path.join(root, f)
        sz = os.path.getsize(fp)
        rel = os.path.relpath(fp, profile_path)
        file_inventory[rel] = sz
        total_size += sz

REPORT['stats']['total_files'] = len(file_inventory)
REPORT['stats']['total_size_mb'] = round(total_size / 1e6, 1)
print(f'  Total files: {len(file_inventory)}')
print(f'  Total size: {total_size / 1e6:.1f} MB')

# Check critical files exist
CRITICAL_FILES = ['places.sqlite', 'cookies.sqlite', 'hardware_profile.json', 'profile_metadata.json']
for cf in CRITICAL_FILES:
    if cf in file_inventory:
        ok('INVENTORY', f'{cf} exists ({file_inventory[cf]} bytes)')
    else:
        issue('INVENTORY', f'CRITICAL file missing: {cf}')

# --- 5B: places.sqlite (Browsing History) ---
print('\n--- 5B: Browsing History (places.sqlite) ---')
places_path = os.path.join(profile_path, 'places.sqlite')
if os.path.exists(places_path):
    conn = sqlite3.connect(places_path)
    c = conn.cursor()
    
    # Count entries
    total_places = c.execute('SELECT COUNT(*) FROM moz_places').fetchone()[0]
    total_visits = c.execute('SELECT COUNT(*) FROM moz_historyvisits').fetchone()[0]
    REPORT['stats']['history_entries'] = total_places
    REPORT['stats']['history_visits'] = total_visits
    print(f'  Total places: {total_places}')
    print(f'  Total visits: {total_visits}')
    
    if total_places < 100:
        issue('HISTORY', f'Too few history entries: {total_places} (need 100+ for {PROFILE_AGE_DAYS}-day profile)')
    else:
        ok('HISTORY', f'{total_places} places, {total_visits} visits')
    
    # Check visit timestamps span the profile age
    ts_rows = c.execute('SELECT MIN(visit_date), MAX(visit_date) FROM moz_historyvisits').fetchone()
    if ts_rows[0] and ts_rows[1]:
        # Firefox uses microseconds since epoch
        min_ts = ts_rows[0]
        max_ts = ts_rows[1]
        
        # Detect timestamp format (PRTime = microseconds since epoch)
        if min_ts > 1e15:  # microseconds
            min_dt = datetime.fromtimestamp(min_ts / 1e6, tz=timezone.utc)
            max_dt = datetime.fromtimestamp(max_ts / 1e6, tz=timezone.utc)
        elif min_ts > 1e12:  # milliseconds
            min_dt = datetime.fromtimestamp(min_ts / 1e3, tz=timezone.utc)
            max_dt = datetime.fromtimestamp(max_ts / 1e3, tz=timezone.utc)
        else:  # seconds
            min_dt = datetime.fromtimestamp(min_ts, tz=timezone.utc)
            max_dt = datetime.fromtimestamp(max_ts, tz=timezone.utc)
        
        span_days = (max_dt - min_dt).days
        now = datetime.now(tz=timezone.utc)
        age_days = (now - min_dt).days
        freshness_days = (now - max_dt).days
        
        REPORT['stats']['history_span_days'] = span_days
        REPORT['stats']['history_oldest_days_ago'] = age_days
        REPORT['stats']['history_newest_days_ago'] = freshness_days
        
        print(f'  Oldest visit: {min_dt.strftime("%Y-%m-%d")} ({age_days} days ago)')
        print(f'  Newest visit: {max_dt.strftime("%Y-%m-%d")} ({freshness_days} days ago)')
        print(f'  Span: {span_days} days')
        
        if age_days < PROFILE_AGE_DAYS - 10:
            issue('HISTORY-TS', f'History oldest ({age_days}d) does not reach profile age ({PROFILE_AGE_DAYS}d)')
        else:
            ok('HISTORY-TS', f'Oldest visit {age_days}d ago covers {PROFILE_AGE_DAYS}d profile age')
        
        if freshness_days > 3:
            warn('HISTORY-TS', f'Newest visit is {freshness_days} days old (should be < 2 days for fresh profile)')
        else:
            ok('HISTORY-TS', f'Most recent visit is {freshness_days}d ago (fresh)')
        
        if span_days < PROFILE_AGE_DAYS * 0.6:
            issue('HISTORY-TS', f'Visit span ({span_days}d) too narrow for {PROFILE_AGE_DAYS}d profile')
        else:
            ok('HISTORY-TS', f'Visit span {span_days}d covers profile age well')
    else:
        issue('HISTORY-TS', 'No visit timestamps found')
    
    # Check URL diversity
    domains = c.execute('''
        SELECT DISTINCT SUBSTR(url, INSTR(url, '://') + 3, 
               CASE WHEN INSTR(SUBSTR(url, INSTR(url, '://') + 3), '/') > 0 
                    THEN INSTR(SUBSTR(url, INSTR(url, '://') + 3), '/') - 1
                    ELSE LENGTH(url) END)
        FROM moz_places WHERE url LIKE 'http%'
    ''').fetchall()
    unique_domains = len(domains)
    REPORT['stats']['unique_domains'] = unique_domains
    print(f'  Unique domains: {unique_domains}')
    
    if unique_domains < 20:
        issue('HISTORY-DOMAIN', f'Too few unique domains: {unique_domains} (need 20+)')
    else:
        ok('HISTORY-DOMAIN', f'{unique_domains} unique domains')
    
    # Check for target-relevant domains
    target_domains = ['eneba.com', 'g2a.com', 'steam', 'google.com', 'youtube.com']
    found_targets = []
    for td in target_domains:
        cnt = c.execute("SELECT COUNT(*) FROM moz_places WHERE url LIKE ?", (f'%{td}%',)).fetchone()[0]
        if cnt > 0:
            found_targets.append(f'{td}({cnt})')
    print(f'  Target-relevant domains in history: {found_targets}')
    
    # Check visit type distribution
    try:
        visit_types = c.execute('SELECT visit_type, COUNT(*) FROM moz_historyvisits GROUP BY visit_type').fetchall()
        print(f'  Visit type distribution: {dict(visit_types)}')
        # Type 1=link, 2=typed, 3=bookmark, 4=embed, 5=redirect_permanent, 6=redirect_temporary, 7=download
        type_map = {1: 'link', 2: 'typed', 3: 'bookmark', 4: 'embed', 5: 'redir_perm', 6: 'redir_temp', 7: 'download'}
        has_typed = any(vt == 2 for vt, _ in visit_types)
        has_link = any(vt == 1 for vt, _ in visit_types)
        if not has_typed:
            warn('HISTORY-TYPES', 'No typed visits (visit_type=2) - all visits appear as link clicks')
        else:
            ok('HISTORY-TYPES', 'Has typed URL visits (natural behavior)')
    except Exception as e:
        warn('HISTORY-TYPES', f'Could not check visit types: {e}')
    
    # Check for suspicious patterns (all same second, sequential timestamps)
    ts_list = [r[0] for r in c.execute('SELECT visit_date FROM moz_historyvisits ORDER BY visit_date LIMIT 200').fetchall()]
    if len(ts_list) >= 10:
        # Check if timestamps are too evenly spaced
        diffs = [ts_list[i+1] - ts_list[i] for i in range(min(50, len(ts_list)-1))]
        if len(set(diffs)) < 3:
            issue('HISTORY-PATTERN', f'Timestamps too uniform (only {len(set(diffs))} unique intervals) - looks machine-generated')
        else:
            ok('HISTORY-PATTERN', f'{len(set(diffs))} unique intervals in first 50 visits (natural variance)')
        
        # Check if any visits in the future
        now_us = int(time.time() * 1e6)
        future_visits = sum(1 for ts in ts_list if ts > now_us * 1.001)
        if future_visits > 0:
            issue('HISTORY-FUTURE', f'{future_visits} visits have future timestamps!')
    
    # Check frecency scores
    frecency_zero = c.execute('SELECT COUNT(*) FROM moz_places WHERE frecency = 0 OR frecency IS NULL').fetchone()[0]
    frecency_total = c.execute('SELECT COUNT(*) FROM moz_places').fetchone()[0]
    frecency_pct = frecency_zero / frecency_total * 100 if frecency_total > 0 else 0
    if frecency_pct > 50:
        warn('HISTORY-FRECENCY', f'{frecency_pct:.0f}% of places have zero frecency (Firefox may recalculate)')
    else:
        ok('HISTORY-FRECENCY', f'{100-frecency_pct:.0f}% of places have non-zero frecency')
    
    conn.close()
else:
    issue('HISTORY', 'places.sqlite MISSING')

# --- 5C: cookies.sqlite ---
print('\n--- 5C: Cookies (cookies.sqlite) ---')
cookies_path = os.path.join(profile_path, 'cookies.sqlite')
if os.path.exists(cookies_path):
    conn = sqlite3.connect(cookies_path)
    c = conn.cursor()
    
    total_cookies = c.execute('SELECT COUNT(*) FROM moz_cookies').fetchone()[0]
    REPORT['stats']['total_cookies'] = total_cookies
    print(f'  Total cookies: {total_cookies}')
    
    if total_cookies < 20:
        issue('COOKIES', f'Too few cookies: {total_cookies} (need 20+ for believable profile)')
    elif total_cookies < 50:
        warn('COOKIES', f'Low cookie count: {total_cookies} (50+ recommended)')
    else:
        ok('COOKIES', f'{total_cookies} cookies')
    
    # Cookie domains
    cookie_domains = c.execute('SELECT DISTINCT host FROM moz_cookies').fetchall()
    REPORT['stats']['cookie_domains'] = len(cookie_domains)
    print(f'  Unique cookie domains: {len(cookie_domains)}')
    sample_domains = [d[0] for d in cookie_domains[:15]]
    print(f'  Sample: {sample_domains}')
    
    # Check for essential cookie types
    essential_cookies = {
        'google': ['NID', 'SID', 'HSID', '1P_JAR', 'CONSENT', 'APISID'],
        'facebook': ['c_user', 'xs', 'fr', 'datr'],
        'youtube': ['PREF', 'VISITOR_INFO', 'YSC', 'LOGIN_INFO'],
    }
    for service, expected in essential_cookies.items():
        found = c.execute(f"SELECT name FROM moz_cookies WHERE host LIKE '%{service}%'").fetchall()
        found_names = [f[0] for f in found]
        missing = [e for e in expected if e not in found_names]
        if found_names:
            if missing:
                warn('COOKIES-AUTH', f'{service}: has {len(found_names)} cookies but missing: {missing[:3]}')
            else:
                ok('COOKIES-AUTH', f'{service}: all expected cookies present')
        else:
            warn('COOKIES-AUTH', f'{service}: no cookies at all')
    
    # Check expiry dates
    now_sec = int(time.time())
    expired = c.execute('SELECT COUNT(*) FROM moz_cookies WHERE expiry > 0 AND expiry < ?', (now_sec,)).fetchone()[0]
    session = c.execute('SELECT COUNT(*) FROM moz_cookies WHERE expiry = 0').fetchone()[0]
    future = c.execute('SELECT COUNT(*) FROM moz_cookies WHERE expiry > ?', (now_sec,)).fetchone()[0]
    REPORT['stats']['cookies_expired'] = expired
    REPORT['stats']['cookies_session'] = session
    REPORT['stats']['cookies_valid'] = future
    print(f'  Expired: {expired}, Session: {session}, Valid: {future}')
    
    if expired > total_cookies * 0.5:
        issue('COOKIES-EXPIRY', f'{expired}/{total_cookies} cookies already expired ({expired/total_cookies*100:.0f}%)')
    else:
        ok('COOKIES-EXPIRY', f'{expired} expired out of {total_cookies} total')
    
    # Check httpOnly and secure flags
    httponly = c.execute('SELECT COUNT(*) FROM moz_cookies WHERE isHttpOnly = 1').fetchone()[0]
    secure = c.execute('SELECT COUNT(*) FROM moz_cookies WHERE isSecure = 1').fetchone()[0]
    sameSite = c.execute('SELECT COUNT(*) FROM moz_cookies WHERE sameSite > 0').fetchone()[0]
    print(f'  HttpOnly: {httponly}, Secure: {secure}, SameSite: {sameSite}')
    
    if httponly == 0:
        warn('COOKIES-FLAGS', 'No httpOnly cookies (auth cookies should be httpOnly)')
    
    # Check creation timestamps
    try:
        oldest_cookie = c.execute('SELECT MIN(creationTime) FROM moz_cookies').fetchone()[0]
        newest_cookie = c.execute('SELECT MAX(creationTime) FROM moz_cookies').fetchone()[0]
        if oldest_cookie and newest_cookie:
            if oldest_cookie > 1e15:
                oldest_dt = datetime.fromtimestamp(oldest_cookie / 1e6, tz=timezone.utc)
                newest_dt = datetime.fromtimestamp(newest_cookie / 1e6, tz=timezone.utc)
            else:
                oldest_dt = datetime.fromtimestamp(oldest_cookie, tz=timezone.utc)
                newest_dt = datetime.fromtimestamp(newest_cookie, tz=timezone.utc)
            cookie_span = (newest_dt - oldest_dt).days
            print(f'  Cookie creation span: {cookie_span} days ({oldest_dt.strftime("%Y-%m-%d")} to {newest_dt.strftime("%Y-%m-%d")})')
            if cookie_span < PROFILE_AGE_DAYS * 0.3:
                issue('COOKIES-TS', f'Cookie creation span ({cookie_span}d) much shorter than profile age ({PROFILE_AGE_DAYS}d)')
            else:
                ok('COOKIES-TS', f'Cookie span {cookie_span}d reasonable for {PROFILE_AGE_DAYS}d profile')
    except Exception as e:
        warn('COOKIES-TS', f'Could not check cookie timestamps: {e}')
    
    conn.close()
else:
    issue('COOKIES', 'cookies.sqlite MISSING')

# --- 5D: localStorage ---
print('\n--- 5D: localStorage (storage/default/) ---')
storage_path = os.path.join(profile_path, 'storage', 'default')
if os.path.exists(storage_path):
    ls_domains = os.listdir(storage_path)
    REPORT['stats']['localstorage_domains'] = len(ls_domains)
    print(f'  localStorage domains: {len(ls_domains)}')
    
    total_ls_size = 0
    domain_sizes = {}
    for domain_dir in ls_domains:
        dp = os.path.join(storage_path, domain_dir)
        ds = 0
        for root, dirs, files in os.walk(dp):
            for f in files:
                ds += os.path.getsize(os.path.join(root, f))
        domain_sizes[domain_dir] = ds
        total_ls_size += ds
    
    REPORT['stats']['localstorage_total_mb'] = round(total_ls_size / 1e6, 1)
    print(f'  Total localStorage size: {total_ls_size / 1e6:.1f} MB')
    
    # Check each domain's ls/data.sqlite for content
    empty_domains = []
    valid_domains = []
    for domain_dir in ls_domains:
        ls_db = os.path.join(storage_path, domain_dir, 'ls', 'data.sqlite')
        if os.path.exists(ls_db):
            try:
                conn = sqlite3.connect(ls_db)
                c = conn.cursor()
                tables = c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                table_names = [t[0] for t in tables]
                
                total_entries = 0
                for tn in table_names:
                    try:
                        cnt = c.execute(f'SELECT COUNT(*) FROM "{tn}"').fetchone()[0]
                        total_entries += cnt
                    except:
                        pass
                
                if total_entries == 0:
                    empty_domains.append(domain_dir)
                else:
                    valid_domains.append((domain_dir, total_entries))
                
                # Sample some keys for content analysis
                for tn in table_names:
                    try:
                        keys = c.execute(f'SELECT key FROM "{tn}" LIMIT 5').fetchall()
                        if keys:
                            key_names = [k[0] for k in keys]
                            # Check for realistic key names
                            suspicious_keys = [k for k in key_names if k.startswith('test_') or k == 'key' or k.startswith('dummy')]
                            if suspicious_keys:
                                warn('LS-KEYS', f'{domain_dir}: suspicious key names: {suspicious_keys}')
                    except:
                        pass
                
                conn.close()
            except Exception as e:
                warn('LS-DB', f'{domain_dir}: could not read ls/data.sqlite: {e}')
        
        # Check indexedDB
        idb_dir = os.path.join(storage_path, domain_dir, 'idb')
        if os.path.exists(idb_dir):
            idb_files = os.listdir(idb_dir)
            if not idb_files:
                warn('IDB', f'{domain_dir}: empty indexedDB directory')
    
    print(f'  Valid domains (with data): {len(valid_domains)}')
    print(f'  Empty domains: {len(empty_domains)}')
    
    if empty_domains:
        warn('LS-EMPTY', f'{len(empty_domains)} domains with empty localStorage: {empty_domains[:5]}')
    
    if len(valid_domains) < 5:
        issue('LS-COUNT', f'Too few domains with localStorage data: {len(valid_domains)}')
    else:
        ok('LS-COUNT', f'{len(valid_domains)} domains with active localStorage')
    
    # Print top domains by size
    top_domains = sorted(domain_sizes.items(), key=lambda x: x[1], reverse=True)[:10]
    print(f'  Top domains by size:')
    for d, s in top_domains:
        print(f'    {d}: {s/1024:.0f} KB')
    
    # Verify domain naming convention (Firefox format: https+++www.domain.com)
    bad_format = [d for d in ls_domains if not d.startswith('http')]
    if bad_format:
        issue('LS-FORMAT', f'Non-standard domain dir names: {bad_format[:5]}')
    else:
        ok('LS-FORMAT', 'All domain directories use Firefox naming convention')
    
    # Check for target-relevant localStorage
    target_ls = [d for d in ls_domains if 'eneba' in d.lower() or 'g2a' in d.lower() or 'steam' in d.lower()]
    if target_ls:
        ok('LS-TARGET', f'Target-relevant localStorage found: {target_ls}')
    else:
        warn('LS-TARGET', f'No target-relevant localStorage (eneba/g2a/steam)')

else:
    issue('LS', 'storage/default/ directory MISSING')

# --- 5E: Cache ---
print('\n--- 5E: Browser Cache (cache2/) ---')
cache_path = os.path.join(profile_path, 'cache2', 'entries')
if os.path.exists(cache_path):
    cache_files = os.listdir(cache_path)
    cache_total = sum(os.path.getsize(os.path.join(cache_path, f)) for f in cache_files)
    REPORT['stats']['cache_files'] = len(cache_files)
    REPORT['stats']['cache_size_mb'] = round(cache_total / 1e6, 1)
    print(f'  Cache entries: {len(cache_files)}')
    print(f'  Cache size: {cache_total / 1e6:.1f} MB')
    
    if len(cache_files) < 10:
        issue('CACHE', f'Too few cache entries: {len(cache_files)}')
    else:
        ok('CACHE', f'{len(cache_files)} cache entries ({cache_total/1e6:.1f} MB)')
    
    # Check cache entry sizes for realism (should vary)
    sizes = sorted([os.path.getsize(os.path.join(cache_path, f)) for f in cache_files])
    if len(sizes) >= 5:
        min_s, max_s = sizes[0], sizes[-1]
        ratio = max_s / max(min_s, 1)
        if ratio < 2:
            warn('CACHE-SIZE', f'Cache entries too uniform in size (min={min_s}, max={max_s})')
        else:
            ok('CACHE-SIZE', f'Cache sizes vary naturally ({min_s/1024:.0f}KB to {max_s/1024:.0f}KB)')
else:
    warn('CACHE', 'cache2/entries/ directory missing')

# --- 5F: hardware_profile.json ---
print('\n--- 5F: Hardware Profile ---')
hw_path = os.path.join(profile_path, 'hardware_profile.json')
if os.path.exists(hw_path):
    hw = json.load(open(hw_path))
    REPORT['stats']['hardware_keys'] = len(hw)
    print(f'  Hardware profile keys: {list(hw.keys())}')
    
    # Check essential hardware fields
    essential_hw = ['userAgent', 'screen', 'canvas', 'webgl', 'audio', 'platform', 'languages']
    found_hw = [k for k in essential_hw if k in hw or any(k.lower() in hk.lower() for hk in hw.keys())]
    missing_hw = [k for k in essential_hw if k not in found_hw]
    
    if missing_hw:
        issue('HARDWARE', f'Missing hardware profile fields: {missing_hw}')
    else:
        ok('HARDWARE', f'All {len(essential_hw)} essential hardware fields present')
    
    # Check userAgent consistency
    ua = hw.get('userAgent', hw.get('user_agent', ''))
    if ua:
        if 'Windows' in ua or 'Win64' in ua:
            ok('HARDWARE-UA', f'UserAgent: Windows-based ({ua[:60]}...)')
        elif 'Linux' in ua:
            warn('HARDWARE-UA', f'UserAgent shows Linux - should match target OS fingerprint')
        else:
            warn('HARDWARE-UA', f'UserAgent unusual: {ua[:80]}')
    else:
        issue('HARDWARE-UA', 'No userAgent in hardware profile')
    
    # Check screen resolution
    screen = hw.get('screen', hw.get('screen_resolution', {}))
    if screen:
        ok('HARDWARE-SCREEN', f'Screen: {screen}')
    else:
        warn('HARDWARE-SCREEN', 'No screen resolution in hardware profile')
    
    # Print full profile for analysis
    print(f'  Full hardware profile:')
    for k, v in hw.items():
        val_str = str(v)[:100]
        print(f'    {k}: {val_str}')
else:
    issue('HARDWARE', 'hardware_profile.json MISSING')

# --- 5G: profile_metadata.json ---
print('\n--- 5G: Profile Metadata ---')
meta_path = os.path.join(profile_path, 'profile_metadata.json')
if os.path.exists(meta_path):
    meta = json.load(open(meta_path))
    print(f'  Metadata keys: {list(meta.keys())}')
    
    # Check essential metadata
    essential_meta = ['profile_uuid', 'persona_name', 'persona_email', 'created_at', 'profile_age_days']
    found_meta = []
    for em in essential_meta:
        for mk in meta.keys():
            if em.lower() in mk.lower() or mk.lower() in em.lower():
                found_meta.append(em)
                break
    missing_meta = [em for em in essential_meta if em not in found_meta]
    
    if missing_meta:
        warn('METADATA', f'Missing metadata fields: {missing_meta}')
    else:
        ok('METADATA', f'All essential metadata fields present')
    
    # Check UUID matches
    stored_uuid = meta.get('profile_uuid', meta.get('uuid', ''))
    if stored_uuid and PROFILE_UUID in str(stored_uuid):
        ok('METADATA-UUID', f'Profile UUID matches: {stored_uuid}')
    elif stored_uuid:
        warn('METADATA-UUID', f'UUID mismatch: expected {PROFILE_UUID}, got {stored_uuid}')
    
    # Check persona name
    stored_name = meta.get('persona_name', meta.get('name', ''))
    if stored_name and PERSONA['name'] in str(stored_name):
        ok('METADATA-NAME', f'Persona name matches: {stored_name}')
    elif stored_name:
        warn('METADATA-NAME', f'Name mismatch: expected {PERSONA["name"]}, got {stored_name}')
    
    print(f'  Full metadata:')
    for k, v in meta.items():
        val_str = str(v)[:120]
        print(f'    {k}: {val_str}')
else:
    issue('METADATA', 'profile_metadata.json MISSING')

# --- 5H: formhistory.sqlite ---
print('\n--- 5H: Form History (formhistory.sqlite) ---')
form_path = os.path.join(profile_path, 'formhistory.sqlite')
if os.path.exists(form_path):
    conn = sqlite3.connect(form_path)
    c = conn.cursor()
    try:
        count = c.execute('SELECT COUNT(*) FROM moz_formhistory').fetchone()[0]
        print(f'  Form entries: {count}')
        
        if count > 0:
            entries = c.execute('SELECT fieldname, value FROM moz_formhistory LIMIT 20').fetchall()
            fields = defaultdict(list)
            for fn, fv in entries:
                fields[fn].append(fv[:40])
            print(f'  Fields: {dict(fields)}')
            
            # Check if persona data is in form history
            has_name = any(PERSONA['name'].lower() in str(v).lower() for fn, v in entries)
            has_email = any(PERSONA['email'].lower() in str(v).lower() for fn, v in entries)
            if has_name:
                ok('FORM', 'Persona name found in form history')
            else:
                warn('FORM', 'Persona name not in form history (would be added during browser use)')
            if has_email:
                ok('FORM', 'Persona email found in form history')
        else:
            warn('FORM', 'Form history empty (populated during browser interaction)')
    except Exception as e:
        warn('FORM-DB', f'Could not read form history: {e}')
    conn.close()
else:
    warn('FORM', 'formhistory.sqlite not created (will be generated during browser use)')

# --- 5I: Cross-consistency checks ---
print('\n--- 5I: Cross-Consistency Checks ---')

# Check that localStorage domains correlate with browsing history domains
if os.path.exists(places_path) and os.path.exists(storage_path):
    conn = sqlite3.connect(places_path)
    history_domains = set()
    for row in conn.execute("SELECT DISTINCT url FROM moz_places WHERE url LIKE 'http%'").fetchall():
        url = row[0]
        try:
            parts = url.split('://')[1].split('/')[0]
            history_domains.add(parts.lower())
        except:
            pass
    conn.close()
    
    ls_domain_names = set()
    for d in os.listdir(storage_path):
        # Convert Firefox dir format (https+++www.google.com) to domain
        clean = d.replace('https+++', '').replace('http+++', '').replace('+++', '.')
        ls_domain_names.add(clean.lower())
    
    # Check overlap
    overlap = history_domains & ls_domain_names
    ls_only = ls_domain_names - history_domains
    hist_only = history_domains - ls_domain_names
    
    print(f'  History domains: {len(history_domains)}')
    print(f'  localStorage domains: {len(ls_domain_names)}')
    print(f'  Overlap: {len(overlap)}')
    
    if len(overlap) < min(len(ls_domain_names), len(history_domains)) * 0.3:
        issue('CONSISTENCY', f'Low overlap between history and localStorage domains ({len(overlap)}/{min(len(ls_domain_names), len(history_domains))})')
    else:
        ok('CONSISTENCY', f'{len(overlap)} domains appear in both history and localStorage')
    
    if ls_only:
        sample_ls_only = list(ls_only)[:5]
        warn('CONSISTENCY', f'Domains with localStorage but no history: {sample_ls_only}')

# ═══════════════════════════════════════════════════════════════
# FINAL REPORT
# ═══════════════════════════════════════════════════════════════
print('\n' + '='*65)
print('FINAL E2E ANALYSIS REPORT')
print('='*65)

print(f'\n  Issues Found: {len(REPORT["issues"])}')
for i in REPORT['issues']:
    print(f'    ❌ {i}')

print(f'\n  Warnings: {len(REPORT["warnings"])}')
for w in REPORT['warnings']:
    print(f'    ⚠ {w}')

print(f'\n  Passed: {len(REPORT["passes"])}')

print(f'\n  Stats:')
for k, v in sorted(REPORT['stats'].items()):
    print(f'    {k}: {v}')

# Save report
report_path = '/opt/titan/state/e2e_real_report.json'
with open(report_path, 'w') as f:
    json.dump(REPORT, f, indent=2)
print(f'\n  Full report saved: {report_path}')

verdict = 'OPERATION-READY' if len(REPORT['issues']) == 0 else f'{len(REPORT["issues"])} ISSUES NEED FIXING'
print(f'\n  VERDICT: {verdict}')
print('='*65)
