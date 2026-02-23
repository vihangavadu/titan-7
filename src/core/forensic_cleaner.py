#!/usr/bin/env python3
"""
Forensic Cleaner: rewrites all SQLite databases in a Titan profile
to match EXACT real Firefox schemas, PRAGMAs, and formatting.
Run AFTER profile generation as a post-processing step.
"""
import sqlite3, os, struct, json, secrets, random, time, shutil, logging
from pathlib import Path
_log = logging.getLogger('TITAN-FORENSIC-CLEANER')

def clean_profile(profile_path):
    pp = Path(profile_path)
    if not pp.exists():
        print('Profile not found:', profile_path)
        return
    
    fixes = 0
    
    # ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
    # 1. COOKIES.SQLITE ΓÇö exact real Firefox schema
    # ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
    cookies_db = pp / 'cookies.sqlite'
    if cookies_db.exists():
        # Read existing data
        conn = sqlite3.connect(str(cookies_db))
        rows = conn.execute('SELECT * FROM moz_cookies').fetchall()
        cols = [d[0] for d in conn.execute('SELECT * FROM moz_cookies LIMIT 0').description]
        conn.close()
        
        # Recreate with exact real Firefox schema
        cookies_db.unlink()
        for wal in [cookies_db.with_suffix('.sqlite-wal'), cookies_db.with_suffix('.sqlite-shm')]:
            if wal.exists(): wal.unlink()
        
        conn = sqlite3.connect(str(cookies_db))
        c = conn.cursor()
        c.execute('PRAGMA page_size = 32768')
        c.execute('PRAGMA journal_mode = WAL')
        c.execute('PRAGMA user_version = 17')
        c.execute("""CREATE TABLE moz_cookies (id INTEGER PRIMARY KEY, originAttributes TEXT NOT NULL DEFAULT '', name TEXT, value TEXT, host TEXT, path TEXT, expiry INTEGER, lastAccessed INTEGER, creationTime INTEGER, isSecure INTEGER, isHttpOnly INTEGER, inBrowserElement INTEGER DEFAULT 0, sameSite INTEGER DEFAULT 0, rawSameSite INTEGER DEFAULT 0, schemeMap INTEGER DEFAULT 0)""")
        
        # Re-insert data
        for row in rows:
            placeholders = ','.join(['?'] * len(row))
            c.execute(f'INSERT OR IGNORE INTO moz_cookies VALUES ({placeholders})', row)
        conn.commit()
        conn.close()
        fixes += 1
        print('[CLEAN] cookies.sqlite: exact real Firefox schema + user_version=17')
    
    # ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
    # 2. PERMISSIONS.SQLITE ΓÇö exact real Firefox schema
    # ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
    perm_db = pp / 'permissions.sqlite'
    if perm_db.exists():
        conn = sqlite3.connect(str(perm_db))
        perms_data = conn.execute('SELECT * FROM moz_perms').fetchall()
        hosts_data = []
        try: hosts_data = conn.execute('SELECT * FROM moz_hosts').fetchall()
        except Exception as _e: _log.warning(f'moz_hosts not present (expected on fresh profile): {_e}')
        conn.close()
        
        perm_db.unlink()
        conn = sqlite3.connect(str(perm_db))
        c = conn.cursor()
        c.execute('PRAGMA page_size = 32768')
        c.execute('PRAGMA journal_mode = DELETE')
        c.execute('PRAGMA user_version = 12')
        c.execute('VACUUM')
        c.execute("CREATE TABLE moz_hosts ( id INTEGER PRIMARY KEY,host TEXT,type TEXT,permission INTEGER,expireType INTEGER,expireTime INTEGER,modificationTime INTEGER,isInBrowserElement INTEGER)")
        c.execute("CREATE TABLE moz_perms ( id INTEGER PRIMARY KEY,origin TEXT,type TEXT,permission INTEGER,expireType INTEGER,expireTime INTEGER,modificationTime INTEGER)")
        for row in perms_data:
            c.execute('INSERT OR IGNORE INTO moz_perms VALUES (?,?,?,?,?,?,?)', row[:7])
        for row in hosts_data:
            c.execute('INSERT OR IGNORE INTO moz_hosts VALUES (?,?,?,?,?,?,?,?)', row[:8])
        conn.commit(); conn.close()
        fixes += 1
        print('[CLEAN] permissions.sqlite: exact schema + journal=DELETE + user_version=12')
    
    # ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
    # 3. CONTENT-PREFS.SQLITE ΓÇö exact real Firefox schema
    # ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
    cp_db = pp / 'content-prefs.sqlite'
    if cp_db.exists():
        conn = sqlite3.connect(str(cp_db))
        groups = conn.execute('SELECT * FROM groups').fetchall()
        settings = conn.execute('SELECT * FROM settings').fetchall()
        prefs = conn.execute('SELECT * FROM prefs').fetchall()
        conn.close()
        
        cp_db.unlink()
        conn = sqlite3.connect(str(cp_db))
        c = conn.cursor()
        c.execute('PRAGMA page_size = 32768')
        c.execute('PRAGMA journal_mode = DELETE')
        c.execute('PRAGMA auto_vacuum = 2')
        c.execute('PRAGMA user_version = 6')
        c.execute('VACUUM')
        c.execute("CREATE TABLE groups (id           INTEGER PRIMARY KEY,                    name         TEXT NOT NULL)")
        c.execute("CREATE TABLE settings (id           INTEGER PRIMARY KEY,                    name         TEXT NOT NULL)")
        c.execute("CREATE TABLE prefs (id           INTEGER PRIMARY KEY,                    groupID      INTEGER REFERENCES groups(id),                    settingID    INTEGER NOT NULL REFERENCES settings(id),                    value        BLOB,                    timestamp INTEGER NOT NULL DEFAULT 0)")
        c.execute("CREATE INDEX groups_idx ON groups(name)")
        c.execute("CREATE INDEX settings_idx ON settings(name)")
        c.execute("CREATE INDEX prefs_idx ON prefs(timestamp, groupID, settingID)")
        for row in groups: c.execute('INSERT OR IGNORE INTO groups VALUES (?,?)', row)
        for row in settings: c.execute('INSERT OR IGNORE INTO settings VALUES (?,?)', row)
        for row in prefs: c.execute('INSERT OR IGNORE INTO prefs VALUES (?,?,?,?,?)', row[:5])
        conn.commit(); conn.close()
        fixes += 1
        print('[CLEAN] content-prefs.sqlite: exact schema + indices + auto_vacuum=2 + user_version=6')
    
    # ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
    # 4. FORMHISTORY.SQLITE ΓÇö exact real Firefox schema
    # ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
    fh_db = pp / 'formhistory.sqlite'
    if fh_db.exists():
        conn = sqlite3.connect(str(fh_db))
        fh_data = conn.execute('SELECT id,fieldname,value,timesUsed,firstUsed,lastUsed,guid FROM moz_formhistory').fetchall()
        conn.close()
        
        fh_db.unlink()
        for wal in [fh_db.with_suffix('.sqlite-wal'), fh_db.with_suffix('.sqlite-shm')]:
            if wal.exists(): wal.unlink()
    else:
        fh_data = []
    
    conn = sqlite3.connect(str(fh_db))
    c = conn.cursor()
    c.execute('PRAGMA page_size = 32768')
    c.execute('PRAGMA journal_mode = DELETE')
    c.execute('PRAGMA user_version = 5')
    c.execute('VACUUM')
    c.execute("""CREATE TABLE moz_formhistory (
      id INTEGER PRIMARY KEY, fieldname TEXT NOT NULL, value TEXT NOT NULL, timesUsed INTEGER, firstUsed INTEGER, lastUsed INTEGER, guid TEXT
      
    )""")
    c.execute("CREATE INDEX moz_formhistory_index ON moz_formhistory(fieldname)")
    c.execute("CREATE INDEX moz_formhistory_lastused_index ON moz_formhistory(lastUsed)")
    c.execute("CREATE INDEX moz_formhistory_guid_index ON moz_formhistory(guid)")
    c.execute("""CREATE TABLE moz_deleted_formhistory (
      id INTEGER PRIMARY KEY, timeDeleted INTEGER, guid TEXT
      
    )""")
    c.execute("""CREATE TABLE moz_sources (
      id INTEGER PRIMARY KEY, source TEXT NOT NULL
      
    )""")
    c.execute("""CREATE TABLE moz_history_to_sources (
      history_id INTEGER, source_id INTEGER
      ,
        PRIMARY KEY (history_id, source_id),
        FOREIGN KEY (history_id) REFERENCES moz_formhistory(id) ON DELETE CASCADE,
        FOREIGN KEY (source_id) REFERENCES moz_sources(id) ON DELETE CASCADE
    )""")
    for row in fh_data:
        guid = row[6] if row[6] else secrets.token_hex(6)
        c.execute('INSERT OR IGNORE INTO moz_formhistory VALUES (?,?,?,?,?,?,?)', 
                  (row[0], row[1] or '', row[2] or '', row[3], row[4], row[5], guid))
    conn.commit(); conn.close()
    fixes += 1
    print('[CLEAN] formhistory.sqlite: exact real Firefox schema + indices + user_version=5')
    
    # ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
    # 5. KEY4.DB ΓÇö exact real Firefox NSS schema
    # ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
    key4 = pp / 'key4.db'
    if key4.exists():
        conn = sqlite3.connect(str(key4))
        meta = conn.execute('SELECT * FROM metaData').fetchall()
        conn.close()
        key4.unlink()
    else:
        meta = [('password', os.urandom(20), b'\x00'*16), ('Version', b'', b'\x01')]
    
    conn = sqlite3.connect(str(key4))
    c = conn.cursor()
    c.execute('PRAGMA page_size = 32768')
    c.execute('PRAGMA journal_mode = DELETE')
    c.execute('VACUUM')
    c.execute("CREATE TABLE metaData (id PRIMARY KEY UNIQUE ON CONFLICT REPLACE, item1, item2)")
    c.execute("CREATE TABLE nssPrivate (id PRIMARY KEY UNIQUE ON CONFLICT ABORT, a0, a1, a2, a3, a4, a10, a11, a12, a80, a81, a82, a83, a84, a85, a86, a87, a88, a89, a8a, a8b, a8c, a90, a100, a101, a102, a103, a104, a105, a106, a107, a108, a109, a10a, a10b, a10c, a110, a111, a120, a121, a122, a123, a124, a125, a126, a127, a128, a129, a12a, a130, a131, a132, a133, a134, a160, a161, a162, a163, a164, a165, a166, a170, a180, a181, a200, a201, a202, a210, a300, a301, a302, a400, a401, a402, a403, a404, a405, a406, a480, a481, a482, a500, a501, a502, a503, ace0)")
    c.execute("CREATE INDEX issuer ON nssPrivate (a81)")
    c.execute("CREATE INDEX subject ON nssPrivate (a101)")
    c.execute("CREATE INDEX ckaid ON nssPrivate (a102)")
    c.execute("CREATE INDEX label ON nssPrivate (a3)")
    for row in meta:
        c.execute('INSERT OR REPLACE INTO metaData VALUES (?,?,?)', row[:3])
    conn.commit(); conn.close()
    fixes += 1
    print('[CLEAN] key4.db: exact NSS schema + page_size=32768 + indices')
    
    # ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
    # 6. CERT9.DB ΓÇö exact real Firefox NSS schema
    # ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
    cert9 = pp / 'cert9.db'
    if cert9.exists(): cert9.unlink()
    
    conn = sqlite3.connect(str(cert9))
    c = conn.cursor()
    c.execute('PRAGMA page_size = 32768')
    c.execute('PRAGMA journal_mode = DELETE')
    c.execute('VACUUM')
    c.execute("CREATE TABLE nssPublic (id PRIMARY KEY UNIQUE ON CONFLICT ABORT, a0, a1, a2, a3, a4, a10, a11, a12, a80, a81, a82, a83, a84, a85, a86, a87, a88, a89, a8a, a8b, a8c, a90, a100, a101, a102, a103, a104, a105, a106, a107, a108, a109, a10a, a10b, a10c, a110, a111, a120, a121, a122, a123, a124, a125, a126, a127, a128, a129, a12a, a130, a131, a132, a133, a134, a160, a161, a162, a163, a164, a165, a166, a170, a180, a181, a200, a201, a202, a210, a300, a301, a302, a400, a401, a402, a403, a404, a405, a406, a480, a481, a482, a500, a501, a502, a503, ace0)")
    c.execute("CREATE INDEX issuer ON nssPublic (a81)")
    c.execute("CREATE INDEX subject ON nssPublic (a101)")
    c.execute("CREATE INDEX ckaid ON nssPublic (a102)")
    c.execute("CREATE INDEX label ON nssPublic (a3)")
    conn.commit(); conn.close()
    fixes += 1
    print('[CLEAN] cert9.db: exact NSS nssPublic schema + page_size=32768')
    
    # ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
    # 7. STORAGE.SQLITE ΓÇö exact real Firefox schema
    # ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
    st_db = pp / 'storage.sqlite'
    if st_db.exists(): st_db.unlink()
    
    conn = sqlite3.connect(str(st_db))
    c = conn.cursor()
    c.execute('PRAGMA page_size = 512')
    c.execute('PRAGMA journal_mode = DELETE')
    c.execute('PRAGMA user_version = 131075')
    c.execute('VACUUM')
    c.execute("CREATE TABLE database( cache_version INTEGER NOT NULL DEFAULT 0)")
    c.execute("CREATE TABLE cache( valid INTEGER NOT NULL DEFAULT 0, build_id TEXT NOT NULL DEFAULT '')")
    c.execute("CREATE TABLE repository( id INTEGER PRIMARY KEY, name TEXT NOT NULL)")
    c.execute("CREATE TABLE origin( repository_id INTEGER NOT NULL, suffix TEXT, group_ TEXT NOT NULL, origin TEXT NOT NULL, client_usages TEXT NOT NULL DEFAULT '', usage INTEGER NOT NULL DEFAULT 0, last_access_time INTEGER NOT NULL DEFAULT 0, last_maintenance_date INTEGER NOT NULL DEFAULT 0, accessed INTEGER NOT NULL DEFAULT 0, persisted INTEGER NOT NULL DEFAULT 0)")
    c.execute("INSERT INTO database VALUES (1)")
    c.execute("INSERT INTO cache VALUES (1, '20241028182834')")
    c.execute("INSERT INTO repository VALUES (0, 'default')")
    c.execute("INSERT INTO repository VALUES (1, 'temporary')")
    c.execute("INSERT INTO repository VALUES (2, 'private')")
    c.execute("INSERT INTO repository VALUES (3, 'persistent')")
    conn.commit(); conn.close()
    fixes += 1
    print('[CLEAN] storage.sqlite: exact schema + page_size=512 + user_version=131075')
    
    # ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
    # 8. Clean WAL/SHM files ΓÇö checkpoint WAL into main DB
    # ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
    for db_name in ['places.sqlite', 'cookies.sqlite', 'favicons.sqlite']:
        db_path = pp / db_name
        if db_path.exists():
            conn = sqlite3.connect(str(db_path))
            conn.execute('PRAGMA wal_checkpoint(TRUNCATE)')
            conn.close()
    
    # Remove stale WAL/SHM for non-WAL databases
    for db_name in ['formhistory.sqlite', 'permissions.sqlite', 'content-prefs.sqlite']:
        for ext in ['-wal', '-shm']:
            f = pp / (db_name + ext)
            if f.exists(): f.unlink()
    
    fixes += 1
    print('[CLEAN] WAL checkpointed, stale WAL/SHM removed')
    
    # ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
    # 9. Move sessionstore.js to proper location
    # ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
    ss = pp / 'sessionstore.js'
    if ss.exists():
        # Real Firefox has sessionstore.jsonlz4 not .js
        # Move to .titan/ since we can't easily create lz4 format
        titan_dir = pp / '.titan'
        titan_dir.mkdir(exist_ok=True)
        shutil.move(str(ss), str(titan_dir / 'sessionstore.js'))
        fixes += 1
        print('[CLEAN] sessionstore.js moved to .titan/')
    
    # ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
    # 10. Verify places.sqlite has user_version
    # ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
    places_db = pp / 'places.sqlite'
    if places_db.exists():
        conn = sqlite3.connect(str(places_db))
        uv = conn.execute('PRAGMA user_version').fetchone()[0]
        if uv == 0:
            conn.execute('PRAGMA user_version = 77')
            conn.commit()
            print('[CLEAN] places.sqlite: set user_version = 77')
        conn.close()
    
    total = sum(f.stat().st_size for f in pp.rglob('*') if f.is_file())
    print(f'\n[DONE] {fixes} forensic fixes applied. Profile size: {total/1e6:.1f} MB')
    return fixes


class ForensicCleaner:
    """Wrapper class for forensic profile cleaning operations."""
    
    def __init__(self, profile_path=None):
        self.profile_path = profile_path or "/opt/titan/profiles"
    
    def clean(self, profile_path=None):
        """Clean a profile directory."""
        path = profile_path or self.profile_path
        return clean_profile(path)
    
    def clean_all(self, profiles_dir=None):
        """Clean all profiles in a directory."""
        pdir = Path(profiles_dir or self.profile_path)
        results = []
        if pdir.is_dir():
            for sub in pdir.iterdir():
                if sub.is_dir() and (sub / 'places.sqlite').exists():
                    results.append(clean_profile(str(sub)))
        return results


class EmergencyWiper:
    """Emergency data destruction for forensic cleanup."""
    
    def __init__(self, targets=None):
        self.targets = targets or [
            "/opt/titan/profiles",
            "/opt/titan/state",
            "/opt/titan/data",
            "/tmp/titan_*",
        ]
    
    def wipe(self):
        """Securely wipe all target directories."""
        wiped = 0
        for target in self.targets:
            p = Path(target)
            if '*' in str(p):
                import glob
                for match in glob.glob(str(p)):
                    shutil.rmtree(match, ignore_errors=True)
                    wiped += 1
            elif p.exists():
                if p.is_dir():
                    shutil.rmtree(str(p), ignore_errors=True)
                else:
                    p.unlink(missing_ok=True)
                wiped += 1
        return wiped
    
    def secure_delete(self, path):
        """Overwrite file with random data before deletion."""
        p = Path(path)
        if p.is_file():
            size = p.stat().st_size
            with open(str(p), 'wb') as f:
                f.write(os.urandom(size))
            p.unlink()


if __name__ == '__main__':
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else '/tmp/titan_forensic_test/FORENSIC-001'
    clean_profile(path)
