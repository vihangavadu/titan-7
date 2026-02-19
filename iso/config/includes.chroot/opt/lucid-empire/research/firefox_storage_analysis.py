#!/usr/bin/env python3
"""
FIREFOX LOCAL STORAGE REVERSE ENGINEERING
==========================================
Analyzes Firefox profile structure for LUCID profile injection

Author: LUCID EMPIRE Research Division
Date: 2026-02-05
"""

import sqlite3
import os
import json
import struct
from pathlib import Path
from datetime import datetime
import lz4.block  # pip install lz4

# Find Firefox profile
APPDATA = os.environ.get('APPDATA', '')
FIREFOX_PROFILES = Path(APPDATA) / 'Mozilla' / 'Firefox' / 'Profiles'

def find_default_profile():
    """Find the default Firefox profile directory"""
    if not FIREFOX_PROFILES.exists():
        return None
    
    for profile_dir in FIREFOX_PROFILES.iterdir():
        if profile_dir.is_dir() and 'default' in profile_dir.name.lower():
            return profile_dir
    
    # Return first profile if no default found
    for profile_dir in FIREFOX_PROFILES.iterdir():
        if profile_dir.is_dir():
            return profile_dir
    
    return None


def analyze_cookies_database(profile_path):
    """Analyze cookies.sqlite structure"""
    print("\n" + "="*70)
    print("1. COOKIES DATABASE (cookies.sqlite)")
    print("="*70)
    
    db_path = profile_path / 'cookies.sqlite'
    if not db_path.exists():
        print("  [!] cookies.sqlite not found")
        return {}
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Get schema
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='moz_cookies'")
    schema = cursor.fetchone()[0]
    print(f"\n[SCHEMA]\n{schema}\n")
    
    # Get column info
    cursor.execute("PRAGMA table_info(moz_cookies)")
    columns = cursor.fetchall()
    print("[COLUMNS]")
    for col in columns:
        print(f"  {col[1]:20} {col[2]:15} {'NOT NULL' if col[3] else 'NULLABLE'}")
    
    # Sample data
    cursor.execute("""
        SELECT name, host, value, expiry, lastAccessed, creationTime, 
               isSecure, isHttpOnly, sameSite, schemeMap
        FROM moz_cookies LIMIT 5
    """)
    
    print("\n[SAMPLE DATA]")
    for row in cursor.fetchall():
        print(f"  Host: {row[1]}")
        print(f"    Name: {row[0]}")
        print(f"    Value: {str(row[2])[:50]}...")
        try:
            expiry_str = datetime.fromtimestamp(row[3]).isoformat() if row[3] and row[3] < 4102444800 else str(row[3])
        except:
            expiry_str = str(row[3])
        print(f"    Expiry: {row[3]} ({expiry_str})")
        print(f"    Created: {row[5]} (microseconds since epoch)")
        print(f"    Secure: {bool(row[6])}, HttpOnly: {bool(row[7])}, SameSite: {row[8]}")
        print()
    
    # Important findings
    findings = {
        'table_name': 'moz_cookies',
        'time_format': 'microseconds since Unix epoch (divide by 1000000 for seconds)',
        'key_columns': ['name', 'host', 'path', 'originAttributes'],
        'injection_columns': ['name', 'value', 'host', 'path', 'expiry', 'lastAccessed', 
                              'creationTime', 'isSecure', 'isHttpOnly', 'sameSite', 'schemeMap']
    }
    
    conn.close()
    return findings


def analyze_places_database(profile_path):
    """Analyze places.sqlite (history, bookmarks)"""
    print("\n" + "="*70)
    print("2. PLACES DATABASE (places.sqlite) - History & Bookmarks")
    print("="*70)
    
    db_path = profile_path / 'places.sqlite'
    if not db_path.exists():
        print("  [!] places.sqlite not found")
        return {}
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # List all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"\n[TABLES] {tables}\n")
    
    # moz_places schema
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='moz_places'")
    print("[moz_places SCHEMA]")
    print(cursor.fetchone()[0])
    
    # moz_historyvisits schema
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='moz_historyvisits'")
    print("\n[moz_historyvisits SCHEMA]")
    print(cursor.fetchone()[0])
    
    # Sample history
    cursor.execute("""
        SELECT p.url, p.title, p.visit_count, p.frecency, 
               v.visit_date, v.visit_type, v.from_visit
        FROM moz_places p
        LEFT JOIN moz_historyvisits v ON p.id = v.place_id
        WHERE p.visit_count > 0
        ORDER BY v.visit_date DESC
        LIMIT 5
    """)
    
    print("\n[SAMPLE HISTORY]")
    for row in cursor.fetchall():
        visit_time = datetime.fromtimestamp(row[4] / 1000000) if row[4] else None
        print(f"  URL: {row[0][:60]}...")
        print(f"    Title: {row[1]}")
        print(f"    Visits: {row[2]}, Frecency: {row[3]}")
        print(f"    Last Visit: {visit_time}")
        print(f"    Visit Type: {row[5]} (1=link, 2=typed, 3=bookmark, 4=embed, 5=redirect)")
        print()
    
    # Visit types reference
    print("\n[VISIT TYPES]")
    print("  1 = TRANSITION_LINK (clicked link)")
    print("  2 = TRANSITION_TYPED (typed in address bar)")
    print("  3 = TRANSITION_BOOKMARK (from bookmark)")
    print("  4 = TRANSITION_EMBED (embedded content)")
    print("  5 = TRANSITION_REDIRECT_PERMANENT (301)")
    print("  6 = TRANSITION_REDIRECT_TEMPORARY (302)")
    print("  7 = TRANSITION_DOWNLOAD (download)")
    print("  8 = TRANSITION_FRAMED_LINK (iframe)")
    
    findings = {
        'tables': tables,
        'time_format': 'microseconds since Unix epoch',
        'history_injection': {
            'moz_places': ['url', 'title', 'visit_count', 'hidden', 'typed', 'frecency', 'last_visit_date', 'guid'],
            'moz_historyvisits': ['from_visit', 'place_id', 'visit_date', 'visit_type', 'session']
        }
    }
    
    conn.close()
    return findings


def analyze_formhistory(profile_path):
    """Analyze formhistory.sqlite (autofill data)"""
    print("\n" + "="*70)
    print("3. FORM HISTORY (formhistory.sqlite)")
    print("="*70)
    
    db_path = profile_path / 'formhistory.sqlite'
    if not db_path.exists():
        print("  [!] formhistory.sqlite not found")
        return {}
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='moz_formhistory'")
    result = cursor.fetchone()
    if result:
        print(f"\n[SCHEMA]\n{result[0]}\n")
    
    cursor.execute("SELECT fieldname, value, timesUsed, firstUsed, lastUsed FROM moz_formhistory LIMIT 10")
    
    print("[SAMPLE DATA]")
    for row in cursor.fetchall():
        first_used = datetime.fromtimestamp(row[3] / 1000000) if row[3] else None
        last_used = datetime.fromtimestamp(row[4] / 1000000) if row[4] else None
        print(f"  Field: {row[0]}")
        print(f"    Value: {row[1][:30]}{'...' if len(str(row[1])) > 30 else ''}")
        print(f"    Used: {row[2]} times, First: {first_used}, Last: {last_used}")
        print()
    
    findings = {
        'time_format': 'microseconds since Unix epoch',
        'injection_columns': ['fieldname', 'value', 'timesUsed', 'firstUsed', 'lastUsed', 'guid']
    }
    
    conn.close()
    return findings


def analyze_webappsstore(profile_path):
    """Analyze webappsstore.sqlite (localStorage)"""
    print("\n" + "="*70)
    print("4. WEB APP STORAGE (webappsstore.sqlite) - localStorage")
    print("="*70)
    
    db_path = profile_path / 'webappsstore.sqlite'
    if not db_path.exists():
        print("  [!] webappsstore.sqlite not found")
        return {}
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table'")
    for row in cursor.fetchall():
        if row[0]:
            print(f"\n[SCHEMA]\n{row[0]}\n")
    
    cursor.execute("SELECT originAttributes, originKey, scope, key, value FROM webappsstore2 LIMIT 5")
    
    print("[SAMPLE DATA]")
    for row in cursor.fetchall():
        print(f"  Origin: {row[2]}")
        print(f"    Key: {row[3]}")
        print(f"    Value: {str(row[4])[:50]}...")
        print()
    
    # Origin key format: reversed domain (e.g., moc.elgoog.:https:443)
    print("\n[ORIGIN KEY FORMAT]")
    print("  Format: reversed_domain:protocol:port")
    print("  Example: moc.elgoog.:https:443 = google.com over HTTPS")
    
    findings = {
        'origin_format': 'reversed_domain:protocol:port',
        'injection_columns': ['originAttributes', 'originKey', 'scope', 'key', 'value']
    }
    
    conn.close()
    return findings


def analyze_storage_folder(profile_path):
    """Analyze storage/ folder (IndexedDB, Cache)"""
    print("\n" + "="*70)
    print("5. STORAGE FOLDER (IndexedDB, Service Workers, Cache)")
    print("="*70)
    
    storage_path = profile_path / 'storage'
    if not storage_path.exists():
        print("  [!] storage folder not found")
        return {}
    
    print("\n[DIRECTORY STRUCTURE]")
    
    for root, dirs, files in os.walk(storage_path):
        level = root.replace(str(storage_path), '').count(os.sep)
        indent = '  ' * level
        print(f"{indent}{os.path.basename(root)}/")
        
        if level < 3:  # Only show first 3 levels
            subindent = '  ' * (level + 1)
            for file in files[:5]:  # Limit files shown
                print(f"{subindent}{file}")
            if len(files) > 5:
                print(f"{subindent}... and {len(files) - 5} more files")
    
    # Storage.sqlite
    storage_db = profile_path / 'storage.sqlite'
    if storage_db.exists():
        print("\n[storage.sqlite - Origin Metadata]")
        conn = sqlite3.connect(str(storage_db))
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"  Tables: {tables}")
        
        if 'database' in tables:
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='database'")
            print(f"\n  {cursor.fetchone()[0]}")
        
        conn.close()
    
    return {'structure': 'IndexedDB per-origin folders'}


def analyze_times_json(profile_path):
    """Analyze times.json (profile creation time)"""
    print("\n" + "="*70)
    print("6. TIMES.JSON (Profile Age - CRITICAL FOR AGING)")
    print("="*70)
    
    times_path = profile_path / 'times.json'
    if not times_path.exists():
        print("  [!] times.json not found")
        return {}
    
    with open(times_path) as f:
        times = json.load(f)
    
    print(f"\n[CONTENT]\n{json.dumps(times, indent=2)}\n")
    
    if 'created' in times:
        created = datetime.fromtimestamp(times['created'] / 1000)
        print(f"[PROFILE CREATED] {created}")
        print(f"  Raw value: {times['created']} (milliseconds since epoch)")
    
    print("\n[AGING INJECTION]")
    print("  To age profile by 90 days:")
    print("  1. Subtract 90 * 24 * 60 * 60 * 1000 from 'created'")
    print("  2. Update 'firstUse' similarly")
    
    return times


def analyze_session_store(profile_path):
    """Analyze sessionstore.jsonlz4 (tabs, session data)"""
    print("\n" + "="*70)
    print("7. SESSION STORE (sessionstore.jsonlz4)")
    print("="*70)
    
    session_path = profile_path / 'sessionstore.jsonlz4'
    if not session_path.exists():
        print("  [!] sessionstore.jsonlz4 not found")
        return {}
    
    print("\n[FORMAT]")
    print("  File type: LZ4 compressed JSON with Mozilla header")
    print("  Header: 'mozLz40\\0' (8 bytes)")
    print("  Size field: 4 bytes little-endian (uncompressed size)")
    print("  Data: LZ4 block compressed JSON")
    
    try:
        with open(session_path, 'rb') as f:
            magic = f.read(8)
            if magic == b'mozLz40\0':
                size = struct.unpack('<I', f.read(4))[0]
                compressed = f.read()
                decompressed = lz4.block.decompress(compressed, uncompressed_size=size)
                session = json.loads(decompressed)
                
                print(f"\n[STRUCTURE]")
                print(f"  Keys: {list(session.keys())}")
                
                if 'windows' in session:
                    print(f"  Windows: {len(session['windows'])}")
                    if session['windows']:
                        window = session['windows'][0]
                        print(f"  Tabs in first window: {len(window.get('tabs', []))}")
                
                if 'session' in session:
                    print(f"  Session info: {session['session']}")
                
    except Exception as e:
        print(f"  [!] Error reading session: {e}")
    
    return {'format': 'mozLz4 compressed JSON'}


def analyze_prefs_js(profile_path):
    """Analyze prefs.js (user preferences)"""
    print("\n" + "="*70)
    print("8. PREFS.JS (User Preferences)")
    print("="*70)
    
    prefs_path = profile_path / 'prefs.js'
    if not prefs_path.exists():
        print("  [!] prefs.js not found")
        return {}
    
    with open(prefs_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract prefs
    prefs = {}
    for line in content.split('\n'):
        if line.startswith('user_pref('):
            try:
                # Parse user_pref("name", value);
                parts = line.split(',', 1)
                name = parts[0].replace('user_pref("', '').strip()
                value = parts[1].rsplit(')', 1)[0].strip()
                prefs[name] = value
            except:
                pass
    
    # Show interesting prefs
    interesting_patterns = ['network.cookie', 'privacy', 'places.history', 
                           'browser.cache', 'security', 'dom.storage']
    
    print("\n[RELEVANT PREFERENCES]")
    for pattern in interesting_patterns:
        matching = {k: v for k, v in prefs.items() if pattern in k}
        if matching:
            print(f"\n  {pattern}:")
            for k, v in list(matching.items())[:5]:
                print(f"    {k} = {v[:50]}{'...' if len(v) > 50 else ''}")
    
    return {'total_prefs': len(prefs)}


def analyze_logins(profile_path):
    """Analyze logins.json (encrypted passwords)"""
    print("\n" + "="*70)
    print("9. LOGINS (logins.json + key4.db)")
    print("="*70)
    
    logins_path = profile_path / 'logins.json'
    key_path = profile_path / 'key4.db'
    
    print("\n[FILES]")
    print(f"  logins.json: {'EXISTS' if logins_path.exists() else 'NOT FOUND'}")
    print(f"  key4.db: {'EXISTS' if key_path.exists() else 'NOT FOUND'}")
    
    if logins_path.exists():
        with open(logins_path) as f:
            logins = json.load(f)
        
        print(f"\n[STRUCTURE]")
        print(f"  Version: {logins.get('version')}")
        print(f"  Logins count: {len(logins.get('logins', []))}")
        
        if logins.get('logins'):
            print("\n[SAMPLE LOGIN ENTRY]")
            login = logins['logins'][0]
            for key in ['hostname', 'formSubmitURL', 'httpRealm', 'encryptedUsername', 
                        'encryptedPassword', 'timeCreated', 'timeLastUsed']:
                if key in login:
                    val = str(login[key])[:50]
                    print(f"    {key}: {val}...")
    
    print("\n[ENCRYPTION]")
    print("  Passwords encrypted with NSS (key4.db)")
    print("  key4.db uses SQLite with NSS key storage")
    print("  Master password or OS key required for decryption")
    
    return {'encrypted': True}


def generate_injection_module():
    """Generate Python code for profile injection"""
    print("\n" + "="*70)
    print("INJECTION MODULE TEMPLATE")
    print("="*70)
    
    code = '''
class FirefoxProfileInjector:
    """Inject data into Firefox profile databases"""
    
    def __init__(self, profile_path):
        self.profile_path = Path(profile_path)
    
    def inject_cookie(self, name, value, host, path='/', expiry=None,
                      secure=True, http_only=False, same_site=0,
                      creation_time=None):
        """Inject a cookie into cookies.sqlite"""
        import time
        
        if creation_time is None:
            creation_time = int(time.time() * 1000000)  # microseconds
        
        if expiry is None:
            expiry = int(time.time()) + 365 * 24 * 60 * 60  # 1 year
        
        conn = sqlite3.connect(self.profile_path / 'cookies.sqlite')
        conn.execute("""
            INSERT OR REPLACE INTO moz_cookies 
            (name, value, host, path, expiry, lastAccessed, creationTime,
             isSecure, isHttpOnly, sameSite, schemeMap, originAttributes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '')
        """, (name, value, host, path, expiry, creation_time, creation_time,
              int(secure), int(http_only), same_site, 2))
        conn.commit()
        conn.close()
    
    def inject_history(self, url, title, visit_count=1, typed=1,
                       visit_date=None, frecency=100):
        """Inject browsing history into places.sqlite"""
        import time
        import uuid
        
        if visit_date is None:
            visit_date = int(time.time() * 1000000)
        
        conn = sqlite3.connect(self.profile_path / 'places.sqlite')
        cursor = conn.cursor()
        
        # Insert into moz_places
        guid = str(uuid.uuid4())[:12]
        cursor.execute("""
            INSERT INTO moz_places (url, title, visit_count, typed, 
                                    frecency, last_visit_date, guid)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (url, title, visit_count, typed, frecency, visit_date, guid))
        
        place_id = cursor.lastrowid
        
        # Insert into moz_historyvisits
        cursor.execute("""
            INSERT INTO moz_historyvisits (place_id, visit_date, visit_type)
            VALUES (?, ?, ?)
        """, (place_id, visit_date, 2))  # 2 = typed
        
        conn.commit()
        conn.close()
        return place_id
    
    def inject_form_data(self, fieldname, value, times_used=1,
                         first_used=None, last_used=None):
        """Inject form autofill data"""
        import time
        import uuid
        
        now = int(time.time() * 1000000)
        if first_used is None:
            first_used = now
        if last_used is None:
            last_used = now
        
        conn = sqlite3.connect(self.profile_path / 'formhistory.sqlite')
        conn.execute("""
            INSERT OR REPLACE INTO moz_formhistory 
            (fieldname, value, timesUsed, firstUsed, lastUsed, guid)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (fieldname, value, times_used, first_used, last_used, 
              str(uuid.uuid4())[:12]))
        conn.commit()
        conn.close()
    
    def inject_local_storage(self, origin, key, value):
        """Inject localStorage data"""
        # Reverse the domain
        parts = origin.split('://')
        protocol = parts[0]
        domain = parts[1].split(':')[0] if ':' in parts[1] else parts[1].split('/')[0]
        port = '443' if protocol == 'https' else '80'
        
        reversed_domain = '.'.join(reversed(domain.split('.'))) + '.'
        origin_key = f"{reversed_domain}:{protocol}:{port}"
        scope = f"{protocol}://{domain}"
        
        conn = sqlite3.connect(self.profile_path / 'webappsstore.sqlite')
        conn.execute("""
            INSERT OR REPLACE INTO webappsstore2 
            (originAttributes, originKey, scope, key, value)
            VALUES ('', ?, ?, ?, ?)
        """, (origin_key, scope, key, value))
        conn.commit()
        conn.close()
    
    def age_profile(self, days=90):
        """Backdate profile creation time"""
        import time
        
        times_path = self.profile_path / 'times.json'
        if times_path.exists():
            with open(times_path) as f:
                times = json.load(f)
            
            offset_ms = days * 24 * 60 * 60 * 1000
            times['created'] = times.get('created', int(time.time() * 1000)) - offset_ms
            
            with open(times_path, 'w') as f:
                json.dump(times, f)
'''
    print(code)
    return code


def main():
    print("="*70)
    print("FIREFOX PROFILE STORAGE REVERSE ENGINEERING")
    print("LUCID EMPIRE Research Division")
    print("="*70)
    
    profile = find_default_profile()
    if not profile:
        print("[!] No Firefox profile found")
        return
    
    print(f"\n[PROFILE] {profile}\n")
    
    findings = {}
    findings['cookies'] = analyze_cookies_database(profile)
    findings['places'] = analyze_places_database(profile)
    findings['formhistory'] = analyze_formhistory(profile)
    findings['webappsstore'] = analyze_webappsstore(profile)
    findings['storage'] = analyze_storage_folder(profile)
    findings['times'] = analyze_times_json(profile)
    findings['session'] = analyze_session_store(profile)
    findings['prefs'] = analyze_prefs_js(profile)
    findings['logins'] = analyze_logins(profile)
    
    generate_injection_module()
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY - KEY FINDINGS FOR LUCID PROFILE INJECTION")
    print("="*70)
    
    summary = """
    ┌─────────────────────────────────────────────────────────────────────┐
    │                    FIREFOX STORAGE STRUCTURE                        │
    ├─────────────────────────────────────────────────────────────────────┤
    │                                                                     │
    │  PROFILE LOCATION:                                                  │
    │    %APPDATA%\\Mozilla\\Firefox\\Profiles\\{random}.default-release │
    │                                                                     │
    │  TIME FORMAT: Microseconds since Unix epoch (÷1000000 = seconds)    │
    │                                                                     │
    │  KEY FILES FOR INJECTION:                                           │
    │  ─────────────────────────                                          │
    │  ┌────────────────────────┬───────────────────────────────────────┐│
    │  │ File                   │ Purpose                               ││
    │  ├────────────────────────┼───────────────────────────────────────┤│
    │  │ cookies.sqlite         │ HTTP cookies (moz_cookies table)      ││
    │  │ places.sqlite          │ History & bookmarks                   ││
    │  │ formhistory.sqlite     │ Form autofill data                    ││
    │  │ webappsstore.sqlite    │ localStorage (webappsstore2 table)    ││
    │  │ times.json             │ Profile creation timestamp            ││
    │  │ prefs.js               │ User preferences                      ││
    │  │ storage/               │ IndexedDB per-origin                  ││
    │  └────────────────────────┴───────────────────────────────────────┘│
    │                                                                     │
    │  AGING STRATEGY:                                                    │
    │  1. Modify times.json 'created' field (subtract days * 86400000)    │
    │  2. Backdate cookie creationTime fields                             │
    │  3. Backdate history visit_date fields                              │
    │  4. Backdate formhistory firstUsed/lastUsed fields                  │
    │                                                                     │
    │  ORIGIN KEY FORMAT (localStorage):                                  │
    │    reversed.domain.:protocol:port                                   │
    │    Example: moc.elgoog.:https:443                                   │
    │                                                                     │
    └─────────────────────────────────────────────────────────────────────┘
    """
    print(summary)
    
    # Save findings
    output_path = Path(__file__).parent / 'firefox_storage_findings.json'
    with open(output_path, 'w') as f:
        json.dump(findings, f, indent=2, default=str)
    print(f"\n[+] Findings saved to: {output_path}")


if __name__ == '__main__':
    main()
