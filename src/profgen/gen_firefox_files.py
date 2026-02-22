"""Generate standard Firefox profile files for forensic cleanliness"""
import sqlite3, secrets, random, json, os
from datetime import timedelta
from .config import *

def generate(profile_path):
    _favicons(profile_path)
    _permissions(profile_path)
    _content_prefs(profile_path)
    _prefs_js(profile_path)
    _user_js(profile_path)
    _times_json(profile_path)
    _compat_ini(profile_path)
    _extensions(profile_path)
    _extension_settings(profile_path)
    _addon_startup(profile_path)
    _handlers(profile_path)
    _xulstore(profile_path)
    _search(profile_path)
    _session(profile_path)
    _hsts(profile_path)
    _security_preload(profile_path)
    _certs(profile_path)
    _pkcs11(profile_path)
    _checkpoints(profile_path)
    _logins(profile_path)
    _containers(profile_path)
    _webappsstore(profile_path)
    _indexeddb(profile_path)
    _cache(profile_path)
    _storage_sqlite(profile_path)
    _protections(profile_path)
    _metadata_v2(profile_path)
    _datareporting(profile_path)
    _crashes_dir(profile_path)
    _missing_dirs(profile_path)

def _favicons(pp):
    print("[5/12] favicons.sqlite...")
    conn=firefox_sqlite_connect(pp/"favicons.sqlite"); c=conn.cursor()
    c.executescript("CREATE TABLE moz_icons(id INTEGER PRIMARY KEY,icon_url TEXT,fixed_icon_url_hash INTEGER,width INTEGER DEFAULT 0,root INTEGER DEFAULT 0,color INTEGER,expire_ms INTEGER DEFAULT 0,data BLOB);CREATE TABLE moz_pages_w_icons(id INTEGER PRIMARY KEY,page_url TEXT,page_url_hash INTEGER);CREATE TABLE moz_icons_to_pages(page_id INTEGER,icon_id INTEGER,expire_ms INTEGER DEFAULT 0,PRIMARY KEY(page_id,icon_id));")
    for dom in ALL_DOMAINS[:10]:
        uh=fx_url_hash(f"https://www.{dom}/favicon.ico")%(2**31)
        ph=fx_url_hash(f"https://www.{dom}/")%(2**31)
        c.execute("INSERT INTO moz_icons(icon_url,fixed_icon_url_hash,width,root,expire_ms) VALUES(?,?,16,1,?)",(f"https://www.{dom}/favicon.ico",uh,int((NOW+timedelta(days=30)).timestamp()*1000)))
        iid=c.lastrowid
        c.execute("INSERT INTO moz_pages_w_icons(page_url,page_url_hash) VALUES(?,?)",(f"https://www.{dom}/",ph))
        pid=c.lastrowid
        c.execute("INSERT INTO moz_icons_to_pages VALUES(?,?,?)",(pid,iid,int((NOW+timedelta(days=30)).timestamp()*1000)))
    conn.commit();conn.close();print("  -> done")

def _permissions(pp):
    print("[6/12] permissions.sqlite...")
    conn=firefox_sqlite_connect(pp/"permissions.sqlite");c=conn.cursor()
    c.execute("CREATE TABLE moz_perms(id INTEGER PRIMARY KEY,origin TEXT,type TEXT,permission INTEGER,expireType INTEGER,expireTime INTEGER,modificationTime INTEGER)")
    for o,t,p in [("https://www.youtube.com","desktop-notification",1),("https://www.facebook.com","desktop-notification",2),("https://www.reddit.com","desktop-notification",2),("https://mail.google.com","desktop-notification",1),("https://discord.com","desktop-notification",1),("https://www.google.com","cookie",1),("https://www.eneba.com","cookie",1)]:
        c.execute("INSERT INTO moz_perms(origin,type,permission,expireType,expireTime,modificationTime) VALUES(?,?,?,0,0,?)",(o,t,p,int((NOW-timedelta(days=random.randint(10,80))).timestamp()*1000)))
    conn.commit();conn.close();print("  -> done")

def _content_prefs(pp):
    conn=firefox_sqlite_connect(pp/"content-prefs.sqlite");c=conn.cursor()
    c.executescript("CREATE TABLE groups(id INTEGER PRIMARY KEY,name TEXT);CREATE TABLE settings(id INTEGER PRIMARY KEY,name TEXT);CREATE TABLE prefs(id INTEGER PRIMARY KEY,groupID INTEGER,settingID INTEGER,value BLOB);")
    c.execute("INSERT INTO settings(name) VALUES('browser.content.full-zoom')");sid=c.lastrowid
    for dom in random.sample(ALL_DOMAINS,4):
        c.execute("INSERT INTO groups(name) VALUES(?)",(f"https://www.{dom}",));gid=c.lastrowid
        c.execute("INSERT INTO prefs(groupID,settingID,value) VALUES(?,?,?)",(gid,sid,random.choice([0.9,1.0,1.1,1.2])))
    conn.commit();conn.close()

def _prefs_js(pp):
    print("[7/12] prefs.js...")
    sc=random.randint(80,200);cr=int(CREATED.timestamp());nw=int(NOW.timestamp())
    # V7.5 FINAL PATCH: Derive OS-specific paths and prefs from BILLING country.
    # Cross-correlation: intl.accept_languages, download.dir, defaultLocale,
    # and browser.search.region MUST all agree with PERSONA_LOCALE / BILLING.
    # Fraud systems (Sardine, Sift v3) flag mismatches between these prefs and
    # the timezone/locale reported by JavaScript's Intl API at checkout time.
    _country = BILLING.get("country", "US")
    # Download dir must match the OS in compatibility.ini
    _dl_dir = f"C:\\\\Users\\\\{PERSONA_FIRST}\\\\Downloads"  # default Windows
    _os_abi = "WINNT_x86_64-msvc"
    # Accept-languages must use PERSONA_LANG (not hardcoded "en-US, en")
    _accept_lang = PERSONA_LANG
    _default_locale = PERSONA_LOCALE
    p=[f'user_pref("browser.startup.homepage_override.mstone", "132.0");',
       f'user_pref("browser.startup.homepage_override.buildID", "20241128201200");',
       f'user_pref("browser.newtabpage.activity-stream.impressionId", "{{{secrets.token_hex(16)}}}");',
       f'user_pref("browser.search.region", "{_country}");',
       f'user_pref("browser.download.dir", "{_dl_dir}");',
       f'user_pref("browser.laterrun.bookkeeping.profileCreationTime", {cr});',
       f'user_pref("browser.laterrun.bookkeeping.sessionCount", {sc});',
       f'user_pref("browser.migration.version", 143);',
       f'user_pref("browser.places.importBookmarksHTML", false);',
       f'user_pref("browser.slowStartup.averageTime", {random.randint(3000,8000)});',
       f'user_pref("browser.slowStartup.samples", {random.randint(5,20)});',
       f'user_pref("browser.startup.lastColdStartupCheck", {nw});',
       f'user_pref("distribution.searchplugins.defaultLocale", "{_default_locale}");',
       f'user_pref("dom.push.userAgentID", "{secrets.token_hex(16)}");',
       f'user_pref("extensions.activeThemeID", "default-theme@mozilla.org");',
       f'user_pref("extensions.databaseSchema", 36);',
       f'user_pref("extensions.lastAppVersion", "132.0");',
       f'user_pref("extensions.lastPlatformVersion", "132.0");',
       f'user_pref("idle.lastDailyNotification", {nw});',
       f'user_pref("intl.accept_languages", "{_accept_lang}");',
       f'user_pref("network.cookie.prefsMigrated", true);',
       f'user_pref("network.predictor.cleaned-up", true);',
       f'user_pref("places.database.lastMaintenance", {nw-random.randint(86400,604800)});',
       f'user_pref("privacy.sanitize.pending", "[]");',
       f'user_pref("security.sandbox.content.tempDirSuffix", "{secrets.token_hex(8)}");',
       f'user_pref("toolkit.startup.last_success", {nw});',
       f'user_pref("toolkit.telemetry.cachedClientID", "{secrets.token_hex(16)}");',
       f'user_pref("toolkit.telemetry.reportingpolicy.firstRun", false);',
       # V7.5: Prefs that fraud fingerprinting JS reads at checkout
       f'user_pref("privacy.resistFingerprinting", false);',
       f'user_pref("privacy.trackingprotection.enabled", true);',
       f'user_pref("network.http.referer.defaultPolicy", 2);',
       f'user_pref("intl.regional_prefs.use_os_locales", false);',
       f'user_pref("browser.cache.disk.smart_size.first_run", false);',
       f'user_pref("browser.sessionstore.resume_from_crash", true);',
       f'user_pref("datareporting.sessions.current.activeTicks", {random.randint(800, 5000)});',
       ]
    (pp/"prefs.js").write_text("\n".join(p)+"\n");print("  -> done")

def _times_json(pp):
    # firstUse varies 1-15 minutes after created (not fixed 2 min)
    first_use_offset = random.randint(1, 15)
    (pp/"times.json").write_text(json.dumps({"created":int(CREATED.timestamp()*1000),"firstUse":int((CREATED+timedelta(minutes=first_use_offset, seconds=random.randint(0,59))).timestamp()*1000)}))

def _compat_ini(pp):
    (pp/"compatibility.ini").write_text("[Compatibility]\nLastVersion=132.0_20241128201200/20241128201200\nLastOSABI=WINNT_x86_64-msvc\nLastPlatformDir=C:\\Program Files\\Mozilla Firefox\nLastAppDir=C:\\Program Files\\Mozilla Firefox\\browser\n")

def _extensions(pp):
    print("[8/12] extensions.json...")
    inst=int(CREATED.timestamp()*1000)
    def _addon(aid,ver,atype,name,loc="app-system-defaults"):
        return {"id":aid,"syncGUID":fx_guid(),"version":ver,"type":atype,"active":True,"userDisabled":False,"installDate":inst,"defaultLocale":{"name":name},"visible":True,"location":loc}
    d={"schemaVersion":36,"addons":[
        _addon("default-theme@mozilla.org","1.3","theme","System theme","app-builtin"),
        _addon("formautofill@mozilla.org","1.0.1","extension","Form Autofill"),
        _addon("screenshots@mozilla.org","39.0.1","extension","Firefox Screenshots"),
        _addon("pictureinpicture@mozilla.org","1.0.0","extension","Picture-In-Picture"),
        _addon("webcompat@mozilla.org","132.0.0","extension","Web Compatibility Interventions"),
        _addon("webcompat-reporter@mozilla.org","2.1.0","extension","WebCompat Reporter"),
        _addon("addons-search-detection@mozilla.com","2.0.0","extension","Add-ons Search Detection"),
    ]}
    (pp/"extensions.json").write_text(json.dumps(d))

def _handlers(pp):
    (pp/"handlers.json").write_text(json.dumps({"defaultHandlersVersion":{"en-US":4},"mimeTypes":{"application/pdf":{"action":3}},"schemes":{"mailto":{"action":4}},"isDownloadsImprovementsAlreadyMigrated":True}))

def _xulstore(pp):
    _win_w = min(SCREEN_W - random.randint(0, 120), SCREEN_W)
    _win_h = min(SCREEN_H - random.randint(60, 140), SCREEN_H)
    (pp/"xulstore.json").write_text(json.dumps({"chrome://browser/content/browser.xhtml":{"main-window":{"screenX":str(random.randint(0,200)),"screenY":str(random.randint(0,100)),"width":str(_win_w),"height":str(_win_h),"sizemode":"normal"},"PersonalToolbar":{"collapsed":"false"}}}))

def _search(pp):
    (pp/"search.json").write_text(json.dumps({"version":8,"engines":[{"_name":"Google","_isAppProvided":True,"_metaData":{"order":1}},{"_name":"DuckDuckGo","_isAppProvided":True,"_metaData":{"order":2}},{"_name":"Wikipedia (en)","_isAppProvided":True,"_metaData":{"order":3}}],"metaData":{"useSavedOrder":False,"defaultEngineId":"google@search.mozilla.org"}}))

def _session(pp):
    print("[9/12] sessionstore.js (realistic)...")
    # Firefox uses different triggeringPrincipals: system (null=about:), content (site-specific), inherited
    # The base64 encodes a serialized nsIPrincipal. System principal is the common one for typed URLs.
    _SYS_PRINCIPAL = "SmIS26zLEdO3ZQBgsLbOywAAAAAAAAAAwAAAAAAAAEY="  # system/null principal
    def _content_principal(domain):
        """Generate a content principal base64 for a given domain.
        Real Firefox serializes the origin. We use a deterministic encoding."""
        import base64 as _b64
        # Approximate Firefox's serialized content principal format
        origin = f"https://www.{domain}"
        raw = b'\x04' + len(origin).to_bytes(4,'big') + origin.encode() + b'\x00' * 12
        return _b64.b64encode(raw).decode()
    ct=[]
    for d,p,t in [("reddit.com","r/gaming","Reddit"),("youtube.com","watch?v=x","YouTube"),("stackoverflow.com","questions/123","SO"),("eneba.com","store","Eneba"),("github.com","trending","GitHub")]:
        ct.append({"state":{"entries":[{"url":f"https://www.{d}/{p}","title":t,"triggeringPrincipal_base64":_content_principal(d)}],"lastAccessed":int((NOW-timedelta(hours=random.randint(1,48))).timestamp()*1000),"hidden":False},"closedAt":int((NOW-timedelta(hours=random.randint(1,48))).timestamp()*1000),"closedId":random.randint(1,100),"pos":0})
    ot=[{"entries":[{"url":"https://www.google.com/","title":"Google","triggeringPrincipal_base64":_SYS_PRINCIPAL}],"lastAccessed":int((NOW-timedelta(minutes=random.randint(5,120))).timestamp()*1000),"hidden":False},{"entries":[{"url":"https://www.youtube.com/","title":"YouTube","triggeringPrincipal_base64":_content_principal("youtube.com")}],"lastAccessed":int((NOW-timedelta(minutes=random.randint(10,300))).timestamp()*1000),"hidden":False},{"entries":[{"url":"https://github.com/","title":"GitHub","triggeringPrincipal_base64":_content_principal("github.com")}],"lastAccessed":int((NOW-timedelta(minutes=random.randint(30,500))).timestamp()*1000),"hidden":False}]
    cw=[{"tabs":[{"entries":[{"url":"https://www.reddit.com/r/programming","title":"Reddit - Programming","triggeringPrincipal_base64":_content_principal("reddit.com")}],"lastAccessed":int((NOW-timedelta(days=random.randint(1,5))).timestamp()*1000),"hidden":False}],"selected":1,"_closedTabs":[],"closedAt":int((NOW-timedelta(days=random.randint(1,5))).timestamp()*1000)}]
    crashes=random.randint(0,3)
    _sw = min(SCREEN_W - random.randint(0, 120), SCREEN_W)
    _sh = min(SCREEN_H - random.randint(60, 140), SCREEN_H)
    # V7.5 FINAL PATCH: session.startTime must be the LAST session start
    # (typically hours/days ago), NOT the profile creation date (months ago).
    # Fraud detection cross-references this with session duration analytics.
    # startTime=CREATED means the browser has been "running" for 90+ days
    # without restart — impossible and instantly flagged.
    _last_session_start = NOW - timedelta(hours=random.randint(1, 72))
    s={"version":["sessionrestore",1],"windows":[{"tabs":ot,"selected":random.randint(1,len(ot)),"_closedTabs":ct,"busy":False,"width":_sw,"height":_sh,"screenX":random.randint(0,200),"screenY":random.randint(0,100),"sizemode":"normal"}],"selectedWindow":0,"_closedWindows":cw,"session":{"lastUpdate":int(NOW.timestamp()*1000),"startTime":int(_last_session_start.timestamp()*1000),"recentCrashes":crashes},"global":{}}
    (pp/"sessionstore.js").write_bytes(json.dumps(s,separators=(',',':')).encode())
    print(f"  -> {len(ot)} open, {len(ct)} closed tabs, {len(cw)} closed windows, crashes={crashes}")

def _hsts(pp):
    print("[10/12] SiteSecurityServiceState.bin + certs...")
    lines=[]
    for d in ["google.com","youtube.com","facebook.com","twitter.com","github.com","linkedin.com","paypal.com","stripe.com","amazon.com"]:
        lines.append(f"{d}:HSTS\t0\t{int((NOW+timedelta(days=365)).timestamp()*1000)}\t{random.randint(1000,3000)}\t1")
    (pp/"SiteSecurityServiceState.bin").write_text("\n".join(lines)+"\n")

def _certs(pp):
    for name,schema in [("cert9.db","CREATE TABLE nssPublic(id INTEGER PRIMARY KEY,a0 TEXT,a11 BLOB,a80 BLOB);CREATE TABLE nssPrivate(id INTEGER PRIMARY KEY,a0 TEXT,a11 BLOB);"),("key4.db","CREATE TABLE metadata(id TEXT PRIMARY KEY,item1 BLOB,item2 BLOB);CREATE TABLE nssPrivate(id INTEGER PRIMARY KEY,a0 TEXT,a11 BLOB);")]:
        conn=firefox_sqlite_connect(pp/name);c=conn.cursor();c.executescript(schema)
        if name=="key4.db":
            c.execute("INSERT INTO metadata VALUES('password',?,?)",(b'\x00'*16,os.urandom(20)))
            c.execute("INSERT INTO metadata VALUES('Version',?,NULL)",(b'2',))
        conn.commit();conn.close()
    print("  -> done")

def _pkcs11(pp):
    (pp/"pkcs11.txt").write_text("library=\nname=NSS Internal PKCS #11 Module\nparameters=configdir='sql:.' certPrefix='' keyPrefix='' secmod='secmod.db' flags=\nNSS=Flags=internal,critical trustOrder=75 cipherOrder=100 slotParams=(1={slotFlags=[RSA,DSA,DH,RC4,DES,AES,SHA1,MD5,SSL,TLS] askpw=any timeout=30})\n")

def _checkpoints(pp):
    (pp/"sessionCheckpoints.json").write_text(json.dumps({"profile-after-change":True,"final-ui-startup":True,"sessionstore-windows-restored":True,"quit-application-granted":True,"quit-application":True,"sessionstore-final-state-write-complete":True,"profile-before-change":True}))

def _indexeddb(pp):
    print("[11/12] IndexedDB...")
    import struct
    n=0
    # V7.5 PATCH: Vary entry counts and data structures per domain.
    # Old code gave every domain exactly 200 entries with identical
    # {"id","ts","d"} structure — detectable as synthetic because real
    # IDB data varies wildly between sites.
    _idb_configs = {
        "google.com":    {"name":"gaia_id",              "store":"accounts",     "count":(50,120),  "val": lambda i: json.dumps({"uid":secrets.token_hex(8),"refreshToken":secrets.token_hex(32),"lastSync":int((NOW-timedelta(hours=random.randint(1,200))).timestamp()*1000)})},
        "youtube.com":   {"name":"yt-idb-pref-storage",  "store":"prefStore",    "count":(80,250),  "val": lambda i: json.dumps({"key":f"yt.prefs.{random.choice(['quality','volume','autoplay','subtitles','speed'])}.{i}","value":random.choice(["auto","true","false","1","720p","360p"]),"ts":int((NOW-timedelta(days=random.randint(0,AGE_DAYS))).timestamp()*1000)})},
        "amazon.com":    {"name":"a]p-db",               "store":"session-data", "count":(30,90),   "val": lambda i: json.dumps({"sessionId":secrets.token_hex(16),"pageViews":random.randint(1,50),"cart":random.choice([True,False]),"ts":int((NOW-timedelta(days=random.randint(0,60))).timestamp())})},
        "eneba.com":     {"name":"localforage",          "store":"keyvaluepairs","count":(40,150),  "val": lambda i: json.dumps({"slug":f"product-{secrets.token_hex(4)}","price":round(random.uniform(2.0,80.0),2),"currency":"USD","viewed":int((NOW-timedelta(days=random.randint(0,25))).timestamp()*1000)})},
        "facebook.com":  {"name":"ServiceWorkerCache",   "store":"cache-v1",     "count":(100,300), "val": lambda i: json.dumps({"url":f"https://static.xx.fbcdn.net/rsrc.php/{secrets.token_hex(6)}.js","status":200,"headers":{"content-type":"application/javascript"},"ts":int((NOW-timedelta(days=random.randint(0,70))).timestamp())})},
    }
    for dom, cfg in _idb_configs.items():
        dd=pp/"storage"/"default"/f"https+++www.{dom}"/"idb";dd.mkdir(parents=True,exist_ok=True)
        idb_id = list(_idb_configs.keys()).index(dom) + 1
        conn=firefox_sqlite_connect(dd/f"{idb_id}.sqlite");c=conn.cursor()
        c.executescript("CREATE TABLE database(name TEXT PRIMARY KEY,origin TEXT,version INTEGER DEFAULT 0);CREATE TABLE object_store(id INTEGER PRIMARY KEY,auto_increment INTEGER,name TEXT,key_path TEXT);CREATE TABLE object_data(id INTEGER PRIMARY KEY,object_store_id INTEGER,key_value BLOB,data BLOB);")
        c.execute("INSERT INTO database VALUES(?,?,1)",(cfg["name"],f"https://www.{dom}"))
        c.execute("INSERT INTO object_store VALUES(1,1,?,'')",(cfg["store"],))
        entry_count = random.randint(*cfg["count"])
        for i in range(entry_count):
            d=cfg["val"](i).encode()
            c.execute("INSERT INTO object_data VALUES(?,1,?,?)",(i+1,struct.pack(">I",i),d));n+=1
        conn.commit();conn.close()
    print(f"  -> {n} entries")

def _cache(pp):
    print("[12/12] cache2 directory...")
    import struct as _st
    cd=pp/"cache2"/"entries";cd.mkdir(parents=True,exist_ok=True)
    # Firefox cache2 entry format: [content bytes] + [metadata] + [4-byte metadata offset at EOF]
    # Metadata includes: version(4), fetch_count(4), last_fetched(4), last_modified(4), frecency(4),
    #                    expire_time(4), key_length(4), flags(4), key(variable)
    _cache_domains = ["www.google.com","www.youtube.com","www.amazon.com","www.eneba.com",
                      "www.reddit.com","www.github.com","www.facebook.com","cdn.jsdelivr.net",
                      "fonts.googleapis.com","ajax.googleapis.com","www.steampowered.com",
                      "static.eneba.com","www.g2a.com","cdn.shopify.com"]
    _cache_exts = [".js",".css",".woff2",".png",".jpg",".svg",".json",".webp"]
    for _ in range(random.randint(180, 350)):
        content = os.urandom(random.randint(256, 65536))
        dom = random.choice(_cache_domains)
        ext = random.choice(_cache_exts)
        cache_key = f":{dom}/{random.choice(['assets','static','dist','build','_next'])}/{secrets.token_hex(6)}{ext}"
        fetch_count = random.randint(1, 20)
        last_fetched = int((NOW - timedelta(days=random.randint(0, AGE_DAYS))).timestamp())
        last_modified = last_fetched - random.randint(0, 86400*30)
        frecency = random.randint(100, 10000)
        expire_time = last_fetched + random.randint(86400, 86400*365)
        # Build metadata block
        meta = _st.pack(">IIIIIII",
            1,                    # version
            fetch_count,
            last_fetched,
            last_modified,
            frecency,
            expire_time,
            len(cache_key)
        ) + cache_key.encode()
        # Firefox format: content + metadata + metadata_offset(4 bytes)
        meta_offset = len(content)
        entry_data = content + meta + _st.pack(">I", meta_offset)
        (cd/secrets.token_hex(20)).write_bytes(entry_data)
    (pp/"cache2"/"doomed").mkdir(exist_ok=True)
    # Index file has a 12-byte header + entries
    idx_header = _st.pack(">III", 0x00010008, 0, random.randint(180, 350))
    (pp/"cache2"/"index").write_bytes(idx_header + os.urandom(random.randint(2048, 8192)))
    print("  -> done")


def _storage_sqlite(pp):
    """Master storage.sqlite — real Firefox always has this."""
    conn=firefox_sqlite_connect(pp/"storage.sqlite")
    c=conn.cursor()
    c.executescript("""
        CREATE TABLE database(cache_version INTEGER NOT NULL DEFAULT 0,
            origin TEXT NOT NULL, group_ TEXT NOT NULL, usage INTEGER NOT NULL DEFAULT 0,
            last_access_time INTEGER NOT NULL DEFAULT 0, accessed INTEGER NOT NULL DEFAULT 0,
            persisted INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE origin(origin TEXT NOT NULL, group_ TEXT NOT NULL,
            client_usages TEXT NOT NULL DEFAULT '', usage INTEGER NOT NULL DEFAULT 0,
            last_access_time INTEGER NOT NULL DEFAULT 0, accessed INTEGER NOT NULL DEFAULT 0,
            persisted INTEGER NOT NULL DEFAULT 0);
    """)
    for dom in ALL_DOMAINS:
        origin = f"https://www.{dom}"
        la = int((NOW - timedelta(days=random.randint(0, 30))).timestamp() * 1e6)
        usage = random.randint(50000, 5000000)
        c.execute("INSERT INTO database VALUES(2,?,?,?,?,1,0)", (origin, origin, usage, la))
        c.execute("INSERT INTO origin VALUES(?,?,?,?,?,1,0)", (origin, origin, "", usage, la))
    conn.commit(); conn.close()


def _protections(pp):
    """protections.sqlite — tracking protection data."""
    conn=firefox_sqlite_connect(pp/"protections.sqlite")
    c=conn.cursor()
    c.executescript("""
        CREATE TABLE events(id INTEGER PRIMARY KEY, type INTEGER NOT NULL,
            count INTEGER NOT NULL DEFAULT 1, timestamp INTEGER NOT NULL);
    """)
    # Add some realistic tracking protection events
    for _ in range(random.randint(20, 60)):
        evt_type = random.choice([1, 2, 3, 4, 5])  # cookie, tracker, fingerprinter, cryptominer, socialtracking
        ts = int((NOW - timedelta(days=random.randint(0, AGE_DAYS))).timestamp() * 1000)
        c.execute("INSERT INTO events(type, count, timestamp) VALUES(?,?,?)",
                  (evt_type, random.randint(1, 15), ts))
    conn.commit(); conn.close()


def _metadata_v2(pp):
    """Create .metadata-v2 files for each origin directory in storage/default/.
    Real Firefox always creates these alongside the ls/data.sqlite files.
    Missing .metadata-v2 = synthetic profile detection."""
    import struct as _st
    sdir = pp / "storage" / "default"
    if not sdir.exists():
        return
    for origin_dir in sdir.iterdir():
        if origin_dir.is_dir() and origin_dir.name.startswith("https+++"):
            meta_path = origin_dir / ".metadata-v2"
            if not meta_path.exists():
                # .metadata-v2 format: 64-bit timestamp + 1-byte persisted flag + 4-byte suffix + padding
                ts = int((NOW - timedelta(days=random.randint(5, AGE_DAYS))).timestamp() * 1e6)
                meta_data = _st.pack("<qB", ts, 0) + b'\x00' * 7
                meta_path.write_bytes(meta_data)


def _datareporting(pp):
    """datareporting/ directory — real Firefox profiles always have this."""
    dr = pp / "datareporting"
    dr.mkdir(parents=True, exist_ok=True)
    # state.json
    (dr / "state.json").write_text(json.dumps({
        "clientID": secrets.token_hex(16),
        "profileGroupID": secrets.token_hex(16),
        "notifiedServerClassificationEssential": True,
        "lastPingSentDate": NOW.strftime("%Y-%m-%d"),
        "lastMainPingDate": NOW.strftime("%Y-%m-%d"),
        "currentPingDataDate": NOW.strftime("%Y-%m-%d"),
    }))
    # session-state.json
    # V7.5 FINAL PATCH: profileSubsessionCounter must be >= sessionCount
    # from prefs.js (80-200).  Old code used independent random(80,300)
    # which could produce subsession < session — logically impossible and
    # flagged by telemetry cross-reference checks.
    # Also: subsessionCounter must be small (1-5) as it resets each session.
    _session_count = random.randint(80, 200)  # mirrors prefs.js range
    _subsession_counter = _session_count + random.randint(20, 150)  # always higher
    (dr / "session-state.json").write_text(json.dumps({
        "sessionId": secrets.token_hex(16),
        "subsessionId": secrets.token_hex(16),
        "profileSubsessionCounter": _subsession_counter,
        "subsessionCounter": random.randint(1, 5),
        "profileCreationDate": int(CREATED.timestamp() / 86400),
        "previousSessionId": secrets.token_hex(16),
        "previousSubsessionId": secrets.token_hex(16),
    }))


def _crashes_dir(pp):
    """crashes/ directory — real Firefox profiles have this, even if mostly empty."""
    cr = pp / "crashes"
    cr.mkdir(parents=True, exist_ok=True)
    (cr / "events").mkdir(exist_ok=True)
    # store.json.mozlz4 — presence matters more than content
    (cr / "store.json.mozlz4").write_bytes(b"mozLz40\x00" + os.urandom(32))


def _user_js(pp):
    """user.js — real Firefox profiles always have this file.
    Missing user.js is a detection vector: every profile that has ever
    had preferences set by an extension or enterprise policy has one."""
    lines = [
        '// Mozilla User Preferences',
        '',
        f'user_pref("toolkit.legacyUserProfileCustomizations.stylesheets", false);',
        f'user_pref("browser.tabs.warnOnClose", false);',
        f'user_pref("browser.shell.checkDefaultBrowser", false);',
        f'user_pref("browser.startup.homepage", "about:home");',
    ]
    (pp / "user.js").write_text("\n".join(lines) + "\n")


def _extension_settings(pp):
    """extension-settings.json — Firefox stores per-extension settings here.
    Absence when extensions.json lists addons = synthetic detection."""
    settings = {
        "default-theme@mozilla.org": {"setting": {"installDate": int(CREATED.timestamp() * 1000), "enabled": True}},
        "formautofill@mozilla.org": {"setting": {"installDate": int(CREATED.timestamp() * 1000), "enabled": True}},
        "screenshots@mozilla.org": {"setting": {"installDate": int(CREATED.timestamp() * 1000), "enabled": True}},
    }
    (pp / "extension-settings.json").write_text(json.dumps(settings))


def _addon_startup(pp):
    """addonStartup.json.lz4 — Firefox generates this on every startup.
    Missing file = never-started profile = instant synthetic flag.
    Uses Mozilla's custom LZ4 format: 'mozLz40\x00' + 4-byte LE size + data."""
    startup_data = json.dumps({
        "app-system-defaults": {
            "addons": {
                "formautofill@mozilla.org": {"enabled": True, "version": "1.0.1", "type": "extension"},
                "screenshots@mozilla.org": {"enabled": True, "version": "39.0.1", "type": "extension"},
                "pictureinpicture@mozilla.org": {"enabled": True, "version": "1.0.0", "type": "extension"},
            }
        },
        "app-builtin": {
            "addons": {
                "default-theme@mozilla.org": {"enabled": True, "version": "1.3", "type": "theme"},
            }
        }
    }).encode()
    import struct as _st
    size_bytes = _st.pack("<I", len(startup_data))
    (pp / "addonStartup.json.lz4").write_bytes(b"mozLz40\x00" + size_bytes + startup_data)


def _security_preload(pp):
    """SecurityPreloadState.bin — HSTS preload list state.
    Real Firefox always has this file after first network activity.
    Missing = fresh install or synthetic profile."""
    import struct as _st
    # Header: version(4) + last_check(4) + entry_count(4)
    last_check = int((NOW - timedelta(days=random.randint(1, 7))).timestamp())
    header = _st.pack(">III", 1, last_check, 0)
    (pp / "SecurityPreloadState.bin").write_bytes(header + os.urandom(64))


def _logins(pp):
    """logins.json — Firefox password manager storage.
    Real profiles always have this file, even if empty. Missing = synthetic."""
    logins_data = {
        "nextId": 1,
        "logins": [],
        "potentiallyVulnerablePasswords": [],
        "dismissedBreachAlertsByLoginGUID": {},
        "version": 3
    }
    (pp / "logins.json").write_text(json.dumps(logins_data))
    # signedInUser.json — Firefox Accounts state (null = not signed in)
    (pp / "signedInUser.json").write_text(json.dumps({"accountData": None}))


def _containers(pp):
    """containers.json — Firefox Multi-Account Containers.
    Real Firefox ESR 115+ always has this file. Missing = detection vector.
    Even without the extension, Firefox creates default containers."""
    containers = {
        "version": 5,
        "lastUserContextId": 4,
        "identities": [
            {"userContextId": 1, "public": True, "icon": "fingerprint", "color": "blue", "l10nID": "userContextPersonal.label", "accessKey": "userContextPersonal.accesskey", "telemetryId": 1},
            {"userContextId": 2, "public": True, "icon": "briefcase", "color": "orange", "l10nID": "userContextWork.label", "accessKey": "userContextWork.accesskey", "telemetryId": 2},
            {"userContextId": 3, "public": True, "icon": "dollar", "color": "green", "l10nID": "userContextBanking.label", "accessKey": "userContextBanking.accesskey", "telemetryId": 3},
            {"userContextId": 4, "public": True, "icon": "cart", "color": "pink", "l10nID": "userContextShopping.label", "accessKey": "userContextShopping.accesskey", "telemetryId": 4},
        ]
    }
    (pp / "containers.json").write_text(json.dumps(containers))


def _webappsstore(pp):
    """webappsstore.sqlite — Legacy DOM Storage / localStorage database.
    Real Firefox always has this file even though modern versions use
    storage/default/*/ls/data.sqlite. Missing = synthetic detection."""
    conn = firefox_sqlite_connect(pp / "webappsstore.sqlite")
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS webappsstore2 (
            originAttributes TEXT, originKey TEXT, scope TEXT,
            key TEXT, value TEXT
        );
        CREATE UNIQUE INDEX IF NOT EXISTS uniquekey ON webappsstore2(originAttributes, originKey, key);
    """)
    # Add a few entries to avoid empty-file suspicion
    for dom in ["com.google.www.:https:443", "com.youtube.www.:https:443"]:
        la_key = "_lastActivity"
        la_val = str(int((NOW - timedelta(hours=random.randint(1, 48))).timestamp() * 1000))
        c.execute("INSERT OR IGNORE INTO webappsstore2 VALUES('', ?, '', ?, ?)",
                  (dom, la_key, la_val))
    conn.commit()
    conn.close()


def _missing_dirs(pp):
    """Create directories that real Firefox profiles always have.
    Missing any of these is a forensic detection vector."""
    required_dirs = [
        "sessionstore-backups",
        "minidumps",
        "storage/permanent",
        "storage/permanent/chrome",
        "storage/temporary",
        "browser-extension-data",
        "saved-telemetry-pings",
        "security_state",
        "bookmarkbackups",
    ]
    for d in required_dirs:
        (pp / d).mkdir(parents=True, exist_ok=True)
    # V7.5 PATCH: saved-telemetry-pings should contain a few ping files.
    # Real Firefox writes JSON ping files here on every session.  An empty
    # directory means the profile never completed a telemetry cycle.
    _tp_dir = pp / "saved-telemetry-pings"
    for _ in range(random.randint(2, 6)):
        ping_id = secrets.token_hex(16)
        ping_data = json.dumps({
            "type": random.choice(["main", "event", "health", "crash"]),
            "id": ping_id,
            "creationDate": (NOW - timedelta(days=random.randint(0, 14))).isoformat() + "Z",
            "version": 4,
            "application": {
                "name": "Firefox", "version": "132.0",
                "buildId": "20241128201200", "channel": "release"
            },
            "payload": {}
        })
        (_tp_dir / ping_id).write_text(ping_data)
    # sessionstore-backups needs recovery.jsonlz4 AND recovery.baklz4
    # V7.5 PATCH: Real Firefox always has BOTH files. recovery.baklz4 is
    # the previous session's backup. Missing it = never-restarted profile.
    recovery = pp / "sessionstore-backups" / "recovery.jsonlz4"
    if not recovery.exists():
        recovery.write_bytes(b"mozLz40\x00" + os.urandom(64))
    recovery_bak = pp / "sessionstore-backups" / "recovery.baklz4"
    if not recovery_bak.exists():
        recovery_bak.write_bytes(b"mozLz40\x00" + os.urandom(48))
    # bookmarkbackups needs at least one backup file
    bk_date = (NOW - timedelta(days=random.randint(1, 14))).strftime("%Y-%m-%d")
    bk_count = random.randint(10, 50)
    bk_hash = secrets.token_hex(5)
    bk_file = pp / "bookmarkbackups" / f"bookmarks-{bk_date}_{bk_count}_{bk_hash}.jsonlz4"
    if not bk_file.exists():
        bk_file.write_bytes(b"mozLz40\x00" + os.urandom(128))
