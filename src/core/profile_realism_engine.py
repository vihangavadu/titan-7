#!/usr/bin/env python3
"""TITAN V8.1 - Profile Realism Engine: adds ALL missing Firefox infrastructure + scales to 500MB+"""
import os,sys,json,sqlite3,hashlib,secrets,random,struct,time,zlib,base64,logging
from pathlib import Path
from datetime import datetime,timedelta, timezone
from typing import Dict,List,Any
logger=logging.getLogger('TITAN-REALISM')

def _fx_sqlite(db_path,page_size=32768,journal_mode='wal',auto_vacuum=0):
    conn=sqlite3.connect(str(db_path));c=conn.cursor()
    c.execute(f'PRAGMA page_size={page_size}');c.execute(f'PRAGMA journal_mode={journal_mode}')
    c.execute(f'PRAGMA auto_vacuum={auto_vacuum}');conn.commit();return conn

def _make_favicon_png(r,g,b):
    def _chunk(ct,data):
        c=ct+data;crc=struct.pack('>I',zlib.crc32(c)&0xffffffff)
        return struct.pack('>I',len(data))+c+crc
    w,h=16,16;hdr=b'\x89PNG\r\n\x1a\n'
    ihdr=struct.pack('>IIBBBBB',w,h,8,2,0,0,0);raw=b''
    for y in range(h):
        raw+=b'\x00'
        for x in range(w): raw+=bytes([r,g,b])
    return hdr+_chunk(b'IHDR',ihdr)+_chunk(b'IDAT',zlib.compress(raw))+_chunk(b'IEND',b'')

DOMAIN_COLORS={
    'google.com':(66,133,244),'youtube.com':(255,0,0),'facebook.com':(24,119,242),
    'twitter.com':(29,155,240),'github.com':(36,41,47),'reddit.com':(255,69,0),
    'amazon.com':(255,153,0),'linkedin.com':(0,119,181),'steampowered.com':(27,40,56),
    'eneba.com':(65,201,129),'g2a.com':(249,96,28),'walmart.com':(0,113,206),
    'bestbuy.com':(0,70,190),'newegg.com':(225,56,0),'target.com':(204,0,0),
    'paypal.com':(0,48,135),'stripe.com':(99,91,255),'netflix.com':(229,9,20),
    'spotify.com':(30,215,96),'twitch.tv':(145,71,255),'gmail.com':(234,67,53),
    'wikipedia.org':(0,0,0),'stackoverflow.com':(244,128,36),'medium.com':(0,0,0),
}

def _ctime_iso(ts): return datetime.fromtimestamp(ts).strftime('%Y-%m-%dT%H:%M:%S.000Z')
def _http_date(ts):
    dt=datetime.utcfromtimestamp(ts)
    days=['Mon','Tue','Wed','Thu','Fri','Sat','Sun']
    mos=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
    return '%s, %02d %s %d %02d:%02d:%02d GMT'%(days[dt.weekday()],dt.day,mos[dt.month-1],dt.year,dt.hour,dt.minute,dt.second)

# ================================================================
# MAIN ENTRY
# ================================================================
class ProfileRealismEngine:
    """Wrapper class for profile realism enhancement operations."""
    
    def __init__(self, config=None):
        self.config = config or {}
    
    def enhance(self, profile_path, config=None):
        """Enhance a profile with realistic Firefox artifacts."""
        return enhance_profile(profile_path, config or self.config)
    
    def get_status(self):
        """Return engine status."""
        return {"available": True, "version": "8.1"}


def enhance_profile(profile_path, config=None):
    pp=Path(profile_path)
    if not pp.exists(): raise FileNotFoundError(profile_path)
    config=config or {}
    profile_age=config.get('profile_age_days',95)
    ua=config.get('user_agent','Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0')
    bt=datetime.now(timezone.utc); ct=bt-timedelta(days=profile_age)
    creation_ts=int(ct.timestamp()); creation_us=int(ct.timestamp()*1e6)
    logger.info('[REALISM] Enhancing %s',profile_path)
    # A: Infrastructure files
    _gen_prefs_js(pp,config,ua,creation_ts)
    _gen_times_json(pp,creation_ts)
    _gen_compat_ini(pp,ua)
    _gen_small_files(pp,creation_ts)
    # B: SQLite databases
    _gen_favicons(pp,profile_age)
    _gen_permissions(pp,creation_us)
    _gen_content_prefs(pp)
    _gen_extra_sqlite(pp)
    # C: Security
    _gen_nss_dbs(pp)
    _gen_hsts(pp)
    # D: Bookmarks
    _add_bookmarks(pp,profile_age)
    # E: Scale localStorage 150MB+
    _scale_ls(pp,config,target_mb=160)
    # F: Scale IndexedDB 100MB+
    _scale_idb(pp,config,target_mb=110)
    # G: Real HTTP cache 200MB+
    _gen_cache(pp,config,target_mb=220)
    # H: Directory structure
    _gen_dirs(pp,creation_ts,profile_age)
    total=sum(f.stat().st_size for f in pp.rglob('*') if f.is_file())
    logger.info('[REALISM] Done: %d MB',total//1000000)
    return total

# ================================================================
# PART A: prefs.js and infrastructure
# ================================================================
def _gen_prefs_js(pp,config,ua,cts):
    now=int(time.time()); sid=secrets.token_hex(16); sess=random.randint(40,300)
    lines=['// Mozilla User Preferences']
    def p(k,v):
        if isinstance(v,bool): lines.append('user_pref("%s", %s);'%(k,str(v).lower()))
        elif isinstance(v,int): lines.append('user_pref("%s", %d);'%(k,v))
        else: lines.append('user_pref("%s", "%s");'%(k,str(v).replace('"','\\"')))
    p('app.normandy.first_run',False)
    p('app.normandy.migrationsApplied',12)
    p('app.normandy.user_id',sid)
    p('app.shield.optoutstudies.enabled',False)
    p('app.update.lastUpdateTime.addon-background-update-timer',cts+random.randint(86400,864000))
    p('app.update.lastUpdateTime.browser-cleanup-thumbnails',cts+random.randint(86400,864000))
    p('app.update.lastUpdateTime.search-engine-update-timer',cts+random.randint(86400,864000))
    p('app.update.lastUpdateTime.services-settings-poll-changes',cts+random.randint(86400,864000))
    p('browser.bookmarks.addedImportButton',True)
    p('browser.bookmarks.restore_default_bookmarks',False)
    p('browser.contentblocking.category','standard')
    p('browser.contextual-services.contextId','{'+secrets.token_hex(16)+'}')
    p('browser.download.viewableInternally.typeWasRegistered.avif',True)
    p('browser.download.viewableInternally.typeWasRegistered.webp',True)
    p('browser.engagement.ctrlTab.has-used',True)
    p('browser.engagement.downloads-button.has-used',True)
    p('browser.engagement.home-button.has-used',True)
    p('browser.laterrun.bookkeeping.profileCreationTime',cts)
    p('browser.laterrun.bookkeeping.sessionCount',sess)
    p('browser.laterrun.enabled',True)
    p('browser.migration.version',146)
    p('browser.newtabpage.activity-stream.impressionId','{'+secrets.token_hex(16)+'}')
    p('browser.newtabpage.storageVersion',1)
    p('browser.pagethumbnails.storage_version',3)
    p('browser.places.smartBookmarksVersion',4)
    p('browser.proton.toolbar.version',3)
    p('browser.region.update.updated',cts+random.randint(3600,86400))
    p('browser.rights.3.shown',True)
    p('browser.search.region','US')
    p('browser.search.suggest.enabled.private',True)
    p('privacy.resistFingerprinting',False)
    p('privacy.trackingprotection.enabled',True)
    p('privacy.trackingprotection.socialtracking.enabled',True)
    p('browser.contentblocking.category','strict')
    p('browser.sessionstore.upgradeBackup.latestBuildID','20260212191108')
    p('browser.shell.mostRecentDateSetAsDefault',str(now-random.randint(0,86400*30)))
    p('browser.slowStartup.averageTime',random.randint(3000,12000))
    p('browser.slowStartup.samples',random.randint(3,15))
    p('browser.startup.couldRestoreSession.count',random.randint(1,8))
    p('browser.startup.homepage','https://www.google.com')
    p('browser.startup.homepage_override.buildID','20260212191108')
    p('browser.startup.homepage_override.mstone','147.0.4')
    p('browser.startup.lastColdStartupCheck',now-random.randint(0,86400))
    p('browser.urlbar.placeholderName','Google')
    p('browser.urlbar.quicksuggest.migrationVersion',2)
    p('browser.urlbar.quicksuggest.scenario','history')
    p('browser.urlbar.tipShownCount.searchTip_onboard',4)
    p('datareporting.policy.dataSubmissionPolicyAcceptedVersion',2)
    p('datareporting.policy.dataSubmissionPolicyNotifiedTime',_ctime_iso(cts))
    p('distribution.iniFile.exists.appversion','147.0.4')
    p('distribution.iniFile.exists.value',False)
    p('doh-rollout.balrog-migration-done',True)
    p('doh-rollout.doneFirstRun',True)
    p('doh-rollout.home-region','US')
    p('dom.forms.autocomplete.formautofill',True)
    p('dom.push.userAgentID',secrets.token_hex(16))
    p('dom.security.https_only_mode_ever_enabled',True)
    p('extensions.activeThemeID','default-theme@mozilla.org')
    p('extensions.blocklist.pingCountVersion',random.randint(1,10))
    p('extensions.databaseSchema',36)
    p('extensions.getAddons.databaseSchema',6)
    p('extensions.lastAppBuildId','20260212191108')
    p('extensions.lastAppVersion','147.0.4')
    p('extensions.lastPlatformVersion','147.0.4')
    p('extensions.pendingOperations',False)
    p('extensions.webcompat.perform_injections',True)
    p('extensions.webcompat.perform_ua_overrides',True)
    p('gecko.handlerService.defaultHandlersVersion',1)
    p('general.autoScroll',True)
    p('gfx.webrender.all',True)
    p('idle.lastDailyNotification',now-random.randint(0,86400))
    p('intl.accept_languages','en-US, en')
    _abi='x86_64-msvc' if 'Windows' in ua else ('x86_64-gcc3' if 'Macintosh' not in ua else 'x86_64-gcc3')
    p('media.gmp-gmpopenh264.abi',_abi)
    p('media.gmp-gmpopenh264.version','2.3.2')
    p('media.gmp-manager.buildID','20260212191108')
    p('media.gmp-manager.lastCheck',now-random.randint(0,86400))
    p('network.cookie.prefsMigrated',True)
    p('network.predictor.cleaned-up',True)
    p('network.predictor.enabled',True)
    p('network.prefetch-next',True)
    p('pdfjs.enabledCache.state',True)
    p('pdfjs.migrationVersion',2)
    p('places.database.lastMaintenance',now-random.randint(0,86400*7))
    p('places.history.enabled',True)
    p('privacy.bounceTrackingProtection.hasMigratedUserActivationData',True)
    p('security.sandbox.content.tempDirSuffix',secrets.token_hex(8))
    p('services.settings.clock_skew_seconds',random.randint(-5,5))
    p('services.settings.last_update_seconds',now-random.randint(0,86400))
    p('signon.rememberSignons',True)
    p('storage.vacuum.last.index',2)
    p('storage.vacuum.last.places.sqlite',now-random.randint(86400,86400*30))
    p('toolkit.startup.last_success',now-random.randint(0,86400))
    p('toolkit.telemetry.cachedClientID',secrets.token_hex(16))
    p('toolkit.telemetry.previousBuildID','20260212191108')
    p('toolkit.telemetry.reportingpolicy.firstRun',False)
    p('trailhead.firstrun.didSeeAboutWelcome',True)
    (pp/'prefs.js').write_text('\n'.join(lines)+'\n')

def _gen_times_json(pp,cts):
    (pp/'times.json').write_text(json.dumps({'created':cts*1000,'firstUse':cts*1000+random.randint(0,60000)}))

def _gen_compat_ini(pp,ua=''):
    if 'Windows' in ua:
        abi='WINNT_x86_64-msvc'
        pdir='C:\\Program Files\\Mozilla Firefox'
        adir='C:\\Program Files\\Mozilla Firefox\\browser'
    elif 'Macintosh' in ua:
        abi='Darwin_x86_64-gcc3'
        pdir='/Applications/Firefox.app/Contents/MacOS'
        adir='/Applications/Firefox.app/Contents/MacOS/browser'
    else:
        abi='Linux_x86_64-gcc3'
        pdir='/usr/lib/firefox-esr'
        adir='/usr/lib/firefox-esr/browser'
    (pp/'compatibility.ini').write_text('[Compatibility]\nLastVersion=147.0.4_20260212191108/20260212191108\nLastOSABI=%s\nLastPlatformDir=%s\nLastAppDir=%s\n'%(abi,pdir,adir))

def _gen_small_files(pp,cts):
    (pp/'pkcs11.txt').write_text('library=\nname=NSS Internal PKCS #11 Module\nNSS=Flags=internal,critical trustOrder=75 cipherOrder=100 slotParams=(1={askpw=any timeout=30})\n')
    (pp/'handlers.json').write_text(json.dumps({'defaultHandlersVersion':{'en-US':4},'mimeTypes':{'application/pdf':{'action':3,'ask':False}},'schemes':{'mailto':{'action':4,'handlers':[{'name':'Gmail','uriTemplate':'https://mail.google.com/mail/?extsrc=mailto&url=%s'}]}}}))
    (pp/'extensions.json').write_text(json.dumps({'schemaVersion':36,'addons':[{'id':'default-theme@mozilla.org','syncGUID':secrets.token_hex(12),'version':'1.3','type':'theme','active':True,'location':'app-builtin','visible':True},{'id':'formautofill@mozilla.org','syncGUID':secrets.token_hex(12),'version':'1.0.1','type':'extension','active':True,'location':'app-system-defaults','visible':True}]}))
    (pp/'addons.json').write_text(json.dumps({'schema':6,'addons':[]}))
    (pp/'logins.json').write_text(json.dumps({'nextId':1,'logins':[],'potentiallyVulnerablePasswords':[],'dismissedBreachAlertsByLoginGUID':{},'version':3}))
    (pp/'AlternateServices.txt').write_text('')
    (pp/'containers.json').write_text(json.dumps({'version':5,'lastUserContextId':5,'identities':[{'icon':'fingerprint','color':'blue','l10nId':'user-context-personal','public':True,'userContextId':1},{'icon':'briefcase','color':'orange','l10nId':'user-context-work','public':True,'userContextId':2},{'icon':'dollar','color':'green','l10nId':'user-context-banking','public':True,'userContextId':3},{'icon':'cart','color':'pink','l10nId':'user-context-shopping','public':True,'userContextId':4},{'icon':'fence','color':'purple','l10nId':'user-context-facebook-container','public':False,'userContextId':5}]}))
    (pp/'sessionCheckpoints.json').write_text(json.dumps({'profile-after-change':True,'final-ui-startup':True,'sessionstore-windows-restored':True}))
    (pp/'xulstore.json').write_text(json.dumps({'chrome://browser/content/browser.xhtml':{'main-window':{'screenX':'4','screenY':'4','width':'1920','height':'1080','sizemode':'maximized'}}}))
    (pp/'shield-preference-experiments.json').write_text(json.dumps({'data':[]}))
    # protections.sqlite - real SQLite DB
    _pc=sqlite3.connect(str(pp/'protections.sqlite'));_pcc=_pc.cursor()
    _pcc.execute('PRAGMA page_size=32768');_pcc.execute('PRAGMA journal_mode=delete')
    _pcc.execute('CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,type INTEGER NOT NULL,count INTEGER NOT NULL DEFAULT 1,timestamp INTEGER NOT NULL)')
    _pc.commit();_pc.close()
    # domain_to_categories.sqlite - real SQLite DB
    _dc=sqlite3.connect(str(pp/'domain_to_categories.sqlite'));_dcc=_dc.cursor()
    _dcc.execute('PRAGMA page_size=32768');_dcc.execute('PRAGMA journal_mode=delete')
    _dcc.execute('CREATE TABLE IF NOT EXISTS categories(id INTEGER PRIMARY KEY,domain TEXT NOT NULL,category INTEGER NOT NULL DEFAULT 0)')
    _dc.commit();_dc.close()

# ================================================================
# PART B: SQLite databases
# ================================================================
def _gen_favicons(pp,profile_age):
    conn=_fx_sqlite(pp/'favicons.sqlite');c=conn.cursor()
    conn.execute('PRAGMA user_version=12')
    c.executescript("""
        CREATE TABLE IF NOT EXISTS moz_icons(id INTEGER PRIMARY KEY,icon_url TEXT NOT NULL,fixed_icon_url_hash INTEGER NOT NULL,width INTEGER NOT NULL DEFAULT 0,root INTEGER NOT NULL DEFAULT 0,color INTEGER,expire_ms INTEGER NOT NULL DEFAULT 0,data BLOB);
        CREATE TABLE IF NOT EXISTS moz_pages_w_icons(id INTEGER PRIMARY KEY,page_url TEXT NOT NULL,page_url_hash INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS moz_icons_to_pages(page_id INTEGER NOT NULL,icon_id INTEGER NOT NULL,expire_ms INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(page_id,icon_id));
        CREATE INDEX IF NOT EXISTS moz_icons_iconurlhashindex ON moz_icons(fixed_icon_url_hash);
    """)
    now_ms=int(time.time()*1000);exp=now_ms+86400000*30;iid=1;pid=1
    for domain,(r,g,b) in DOMAIN_COLORS.items():
        png=_make_favicon_png(r,g,b)
        iu='https://www.%s/favicon.ico'%domain;pu='https://www.%s/'%domain
        uh=hash(iu)&0x7FFFFFFFFFFFFFFF;ph=hash(pu)&0x7FFFFFFFFFFFFFFF
        for w in [16,32]:
            c.execute('INSERT INTO moz_icons VALUES(?,?,?,?,?,?,?,?)',(iid,iu,uh,w,1,(r<<16)|(g<<8)|b,exp,png))
            c.execute('INSERT OR IGNORE INTO moz_pages_w_icons VALUES(?,?,?)',(pid,pu,ph))
            c.execute('INSERT OR IGNORE INTO moz_icons_to_pages VALUES(?,?,?)',(pid,iid,exp))
            iid+=1
        pid+=1
    conn.commit();conn.close()

def _gen_permissions(pp,creation_us):
    conn=_fx_sqlite(pp/'permissions.sqlite',journal_mode='delete');c=conn.cursor()
    conn.execute('PRAGMA user_version=12')
    c.execute('CREATE TABLE IF NOT EXISTS moz_perms(id INTEGER PRIMARY KEY,origin TEXT,type TEXT,permission INTEGER,expireType INTEGER,expireTime INTEGER,modificationTime INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS moz_hosts(id INTEGER PRIMARY KEY,host TEXT,type TEXT,permission INTEGER,expireType INTEGER,expireTime INTEGER,modificationTime INTEGER,isInBrowserElement INTEGER)')
    pid=1;now=int(time.time()*1000)
    for origin,perm in [('https://www.youtube.com',1),('https://www.facebook.com',2),('https://www.reddit.com',2),('https://mail.google.com',1),('https://www.twitter.com',2)]:
        c.execute('INSERT INTO moz_perms VALUES(?,?,?,?,?,?,?)',(pid,origin,'desktop-notification',perm,0,0,now-random.randint(0,86400000*30)));pid+=1
    for d in ['google.com','youtube.com','facebook.com','amazon.com']:
        c.execute('INSERT INTO moz_perms VALUES(?,?,?,?,?,?,?)',(pid,'https://www.'+d,'persistent-storage',1,0,0,now-random.randint(0,86400000*60)));pid+=1
    conn.commit();conn.close()

def _gen_content_prefs(pp):
    conn=_fx_sqlite(pp/'content-prefs.sqlite',journal_mode='delete',auto_vacuum=2);c=conn.cursor()
    conn.execute('PRAGMA user_version=6')
    c.executescript("""
        CREATE TABLE IF NOT EXISTS groups(id INTEGER PRIMARY KEY,name TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS settings(id INTEGER PRIMARY KEY,name TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS prefs(id INTEGER PRIMARY KEY,groupID INTEGER,settingID INTEGER,value BLOB,timestamp INTEGER NOT NULL DEFAULT 0);
    """)
    c.execute("INSERT INTO settings(id,name) VALUES(1,'browser.content.full-zoom')")
    for i,(site,zoom) in enumerate([('reddit.com','1.1'),('github.com','1.0'),('stackoverflow.com','1.1'),('docs.google.com','0.9')],1):
        c.execute('INSERT INTO groups(id,name) VALUES(?,?)',(i,site))
        c.execute('INSERT INTO prefs(groupID,settingID,value,timestamp) VALUES(?,1,?,?)',(i,zoom,int(time.time())-random.randint(86400,86400*60)))
    conn.commit();conn.close()

def _gen_extra_sqlite(pp):
    # webappsstore.sqlite
    conn=_fx_sqlite(pp/'webappsstore.sqlite',journal_mode='delete');c=conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS webappsstore2(originAttributes TEXT,originKey TEXT,scope TEXT,key TEXT,value TEXT)')
    c.execute('CREATE INDEX IF NOT EXISTS scope_index ON webappsstore2(originAttributes,originKey)')
    conn.commit();conn.close()
    # storage.sqlite
    conn=_fx_sqlite(pp/'storage.sqlite',page_size=512,journal_mode='delete');c=conn.cursor()
    conn.execute('PRAGMA user_version=131075')
    c.executescript('''
        CREATE TABLE IF NOT EXISTS database(cache_version INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS cache(valid INTEGER NOT NULL DEFAULT 0, build_id TEXT NOT NULL DEFAULT '');
        CREATE TABLE IF NOT EXISTS repository(id INTEGER PRIMARY KEY, name TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS origin(repository_id INTEGER NOT NULL, suffix TEXT, group_ TEXT NOT NULL, origin TEXT NOT NULL, client_usages TEXT NOT NULL DEFAULT '', usage INTEGER NOT NULL DEFAULT 0, last_access_time INTEGER NOT NULL DEFAULT 0, last_maintenance_date INTEGER NOT NULL DEFAULT 0, accessed INTEGER NOT NULL DEFAULT 0, persisted INTEGER NOT NULL DEFAULT 0);
        INSERT OR IGNORE INTO database(cache_version) VALUES(1);
        INSERT OR IGNORE INTO cache(valid, build_id) VALUES(1, '20260212191108');
        INSERT OR IGNORE INTO repository(id, name) VALUES(0, 'default');
        INSERT OR IGNORE INTO repository(id, name) VALUES(1, 'temporary');
        INSERT OR IGNORE INTO repository(id, name) VALUES(2, 'private');
        INSERT OR IGNORE INTO repository(id, name) VALUES(3, 'persistent');
    ''')
    conn.commit();conn.close()

# ================================================================
# PART C: Security
# ================================================================
def _gen_nss_dbs(pp):
    # key4.db
    conn=sqlite3.connect(str(pp/'key4.db'));c=conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS metaData(id PRIMARY KEY UNIQUE ON CONFLICT REPLACE,item1,item2)')
    c.execute('CREATE TABLE IF NOT EXISTS nssPrivate(id PRIMARY KEY UNIQUE ON CONFLICT ABORT,a0,a1,a2,a3,a4,a10,a11,a12,a80,a81,a82,a83,a84,a85,a86,a87,a88,a89,a8a,a8b,a8c,a90,a100,a101,a102,a103,a104,a105,a106,a107,a108,a109,a10a,a10b,a10c,a110,a111,a120,a121,a122,a123,a124,a125,a126,a127,a128,a129,a12a,a130,a131,a132,a133,a134,a160,a161,a162,a163,a164,a165,a166,a170,a180,a181,a200,a201,a202,a210,a300,a301,a302,a400,a401,a402,a403,a404,a405,a406,a480,a481,a482,a500,a501,a502,a503,ace0)')
    c.execute('CREATE INDEX IF NOT EXISTS issuer ON nssPrivate(a81)')
    c.execute('CREATE INDEX IF NOT EXISTS subject ON nssPrivate(a101)')
    c.execute('CREATE INDEX IF NOT EXISTS ckaid ON nssPrivate(a102)')
    c.execute('CREATE INDEX IF NOT EXISTS label ON nssPrivate(a3)')
    c.execute("INSERT OR REPLACE INTO metaData VALUES('password',?,?)",(os.urandom(20),b'\x00'*16))
    c.execute("INSERT OR REPLACE INTO metaData VALUES('Version',?,?)",(b'',b'\x01'))
    conn.commit();conn.close()
    # cert9.db
    conn=sqlite3.connect(str(pp/'cert9.db'));c=conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS nssPublic(id PRIMARY KEY UNIQUE ON CONFLICT ABORT,a0,a1,a2,a3,a4,a10,a11,a12,a80,a81,a82,a83,a84,a85,a86,a87,a88,a89,a8a,a8b,a8c,a90,a100,a101,a102,a103,a104,a105,a106,a107,a108,a109,a10a,a10b,a10c,a110,a111,a120,a121,a122,a123,a124,a125,a126,a127,a128,a129,a12a,a130,a131,a132,a133,a134,a160,a161,a162,a163,a164,a165,a166,a170,a180,a181,a200,a201,a202,a210,a300,a301,a302,a400,a401,a402,a403,a404,a405,a406,a480,a481,a482,a500,a501,a502,a503,ace0)')
    c.execute('CREATE INDEX IF NOT EXISTS issuer ON nssPublic(a81)')
    c.execute('CREATE INDEX IF NOT EXISTS subject ON nssPublic(a101)')
    c.execute('CREATE INDEX IF NOT EXISTS ckaid ON nssPublic(a102)')
    c.execute('CREATE INDEX IF NOT EXISTS label ON nssPublic(a3)')
    conn.commit();conn.close()

def _gen_hsts(pp):
    now=int(time.time()*1000);lines=[]
    for d in ['google.com','youtube.com','facebook.com','twitter.com','github.com','linkedin.com','amazon.com','paypal.com','stripe.com','steampowered.com','eneba.com']:
        lines.append('%s:HSTS\t0\t%d\t%d\t1,0,0'%(d,now+86400000*random.randint(30,365),random.randint(1000,3000)))
    (pp/'SiteSecurityServiceState.bin').write_text('\n'.join(lines)+'\n')

# ================================================================
# PART D: Bookmarks
# ================================================================
def _add_bookmarks(pp,profile_age):
    conn=sqlite3.connect(str(pp/'places.sqlite'));c=conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS moz_bookmarks(id INTEGER PRIMARY KEY,type INTEGER,fk INTEGER DEFAULT NULL,parent INTEGER,position INTEGER,title TEXT,keyword_id INTEGER,folder_type TEXT,dateAdded INTEGER,lastModified INTEGER,guid TEXT,syncStatus INTEGER NOT NULL DEFAULT 0,syncChangeCounter INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS moz_bookmarks_deleted(guid TEXT PRIMARY KEY,dateRemoved INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS moz_keywords(id INTEGER PRIMARY KEY AUTOINCREMENT,keyword TEXT UNIQUE,place_id INTEGER,post_data TEXT);
        CREATE INDEX IF NOT EXISTS moz_bookmarks_itemindex ON moz_bookmarks(fk,type);
        CREATE INDEX IF NOT EXISTS moz_bookmarks_parentindex ON moz_bookmarks(parent,position);
        CREATE UNIQUE INDEX IF NOT EXISTS moz_bookmarks_guid_uniqueindex ON moz_bookmarks(guid);
    """)
    now_us=int(time.time()*1e6);base_us=now_us-profile_age*86400*1000000
    # Root folders
    for bid,btype,fk,par,pos,title,guid in [(1,2,None,0,0,'','root________'),(2,2,None,1,0,'Bookmarks Menu','menu________'),(3,2,None,1,1,'Bookmarks Toolbar','toolbar_____'),(4,2,None,1,2,'Other Bookmarks','unfiled_____'),(5,2,None,1,3,'Mobile Bookmarks','mobile______')]:
        c.execute('INSERT OR IGNORE INTO moz_bookmarks(id,type,fk,parent,position,title,dateAdded,lastModified,guid) VALUES(?,?,?,?,?,?,?,?,?)',(bid,btype,fk,par,pos,title,base_us,base_us,guid))
    # Bookmarks
    bid=6
    for url,title,parent in [('https://www.google.com/','Google',3),('https://mail.google.com/','Gmail',3),('https://www.youtube.com/','YouTube',3),('https://github.com/','GitHub',3),('https://stackoverflow.com/','Stack Overflow',4),('https://www.reddit.com/','Reddit',4),('https://www.amazon.com/','Amazon',2),('https://store.steampowered.com/','Steam Store',2),('https://www.linkedin.com/','LinkedIn',2)]:
        place=c.execute('SELECT id FROM moz_places WHERE url=?',(url,)).fetchone()
        if place: fk=place[0]
        else:
            rev='.'.join(reversed(url.split('://')[1].split('/')[0].split('.')))+'.';c.execute('INSERT INTO moz_places(url,title,rev_host,visit_count,typed,guid) VALUES(?,?,?,?,?,?)',(url,title,rev,random.randint(1,50),1,secrets.token_hex(6)));fk=c.lastrowid
        added=base_us+random.randint(0,profile_age*86400*1000000//2)
        c.execute('INSERT OR IGNORE INTO moz_bookmarks(id,type,fk,parent,position,title,dateAdded,lastModified,guid) VALUES(?,?,?,?,?,?,?,?,?)',(bid,1,fk,parent,bid-6,title,added,added+random.randint(0,86400000000),secrets.token_hex(6)));bid+=1
    conn.commit();conn.close()

# ================================================================
# PART E: Scale localStorage to 150MB+
# ================================================================
def _scale_ls(pp,config,target_mb=160):
    sd=pp/'storage'/'default'
    if not sd.exists(): sd.mkdir(parents=True)
    current=sum(f.stat().st_size for f in sd.rglob('*') if f.is_file())
    remaining=(target_mb*1024*1024)-current
    if remaining<=0: return
    domains=['google.com','youtube.com','facebook.com','amazon.com','twitter.com','reddit.com','github.com','linkedin.com','gmail.com','steampowered.com','eneba.com','walmart.com','bestbuy.com','newegg.com','netflix.com','spotify.com','twitch.tv','medium.com','stackoverflow.com','wikipedia.org']
    bpd=remaining//len(domains)
    for domain in domains:
        dd=sd/('https+++www.'+domain);ls=dd/'ls';idb=dd/'idb'
        ls.mkdir(parents=True,exist_ok=True);idb.mkdir(parents=True,exist_ok=True)
        conn=_fx_sqlite(ls/'data.sqlite');c=conn.cursor()
        c.execute('CREATE TABLE IF NOT EXISTS data(key TEXT PRIMARY KEY,utf16Length INTEGER NOT NULL DEFAULT 0,compressed INTEGER NOT NULL DEFAULT 0,lastAccessTime INTEGER NOT NULL DEFAULT 0,value BLOB NOT NULL)')
        c.execute('CREATE TABLE IF NOT EXISTS database(origin TEXT NOT NULL,last_vacuum_time INTEGER NOT NULL DEFAULT 0,last_analyze_time INTEGER NOT NULL DEFAULT 0,last_vacuum_size INTEGER NOT NULL DEFAULT 0)')
        now_us=int(time.time()*1e6);total=0;i=0
        # Domain-specific realistic keys
        entries=_gen_domain_ls(domain,bpd)
        for key,value in entries:
            ts=now_us-random.randint(0,86400*1000000*90)
            vb=value.encode() if isinstance(value,str) else value
            try: c.execute('INSERT OR REPLACE INTO data VALUES(?,?,?,?,?)',(key,len(value),0,ts,vb));total+=len(vb)
            except Exception: pass
            if total>=bpd: break
        conn.commit();conn.close()

def _gen_domain_ls(domain,target_bytes):
    """Generate realistic localStorage entries for a domain."""
    entries=[]
    # Domain-specific keys first
    if 'google' in domain:
        entries+=[('_ga','GA1.2.%d.%d'%(random.randint(100000,999999),int(time.time())-random.randint(86400,86400*90))),('_gid','GA1.2.%d.%d'%(random.randint(100000,999999),int(time.time()))),('NID',secrets.token_hex(64)),('CONSENT','YES+cb.%d'%int(time.time()))]
        for i in range(200):
            entries.append(('sb_wiz.zpc.gws-wiz-serp.%d'%i,json.dumps({'q':secrets.token_hex(random.randint(4,20)),'ts':int(time.time())-random.randint(0,86400*90),'results':random.randint(1000,99000000)})))
    elif 'youtube' in domain:
        for i in range(500):
            vid=secrets.token_urlsafe(8)[:11]
            entries.append(('yt-player-%s'%vid,json.dumps({'videoId':vid,'position':random.randint(0,7200),'duration':random.randint(60,7200),'timestamp':int(time.time()*1000)-random.randint(0,86400000*90)})))
        entries.append(('yt-player-bandwidth',str(random.randint(2000000,80000000))))
        entries.append(('yt-player-quality',json.dumps({'data':'hd1080','expiration':int(time.time()*1000)+2592000000})))
    elif 'facebook' in domain:
        for i in range(200):
            entries.append(('LSD:%s'%secrets.token_hex(8),json.dumps({'token':secrets.token_hex(16),'ts':int(time.time())-random.randint(0,86400*60)})))
    elif 'amazon' in domain:
        cats=['Electronics','Books','Home & Kitchen','Clothing','Sports','Toys','Grocery','Beauty']
        for i in range(300):
            entries.append(('csm-%s'%secrets.token_hex(6),json.dumps({'asin':'B'+secrets.token_hex(4).upper(),'category':random.choice(cats),'price':round(random.uniform(4.99,499.99),2),'ts':int(time.time())-random.randint(0,86400*90)})))
    elif 'twitter' in domain:
        for i in range(300):
            entries.append(('twid:%s'%secrets.token_hex(6),json.dumps({'type':random.choice(['tweet','like','retweet','view']),'id':str(random.randint(10**17,10**18)),'ts':int(time.time())-random.randint(0,86400*60)})))
    elif 'reddit' in domain:
        subs=['technology','programming','gaming','news','science','AskReddit','videos','funny','pics','worldnews','pcgaming','buildapc','linux','python','javascript']
        for i in range(400):
            entries.append(('recent_srs:%d'%i,json.dumps({'sr':'t5_'+secrets.token_hex(3),'name':random.choice(subs),'visited':int(time.time())-random.randint(0,86400*90)})))
    elif 'github' in domain:
        for i in range(200):
            entries.append(('repo-cache-%d'%i,json.dumps({'repo':'user/repo-%s'%secrets.token_hex(4),'stars':random.randint(0,50000),'lang':random.choice(['Python','JavaScript','TypeScript','Rust','Go','C++','Java'])})))
    elif 'steam' in domain:
        for i in range(100):
            entries.append(('appid-%d'%random.randint(200000,2500000),json.dumps({'name':'Game %s'%secrets.token_hex(3),'playtime':random.randint(0,50000),'achievements':random.randint(0,100)})))
    elif 'eneba' in domain:
        for i in range(80):
            entries.append(('product-view-%d'%i,json.dumps({'productId':secrets.token_hex(8),'category':random.choice(['Game Keys','Gift Cards','Subscriptions']),'platform':random.choice(['Steam','Xbox','PlayStation','Nintendo']),'price':round(random.uniform(2.99,79.99),2)})))
    # Pad with realistic-looking analytics/cache/sw data
    total=sum(len(v) for _,v in entries)
    entries+=_gen_padding(domain.split('.')[0],max(0,target_bytes-total))
    return entries

def _gen_padding(prefix,remaining):
    """Generate realistic-looking padding entries (analytics, cache, sw data)."""
    entries=[];current=0;i=0
    while current<remaining and i<10000:
        rtype=random.randint(0,3)
        if rtype==0:  # analytics event
            v=json.dumps({'event':random.choice(['page_view','click','scroll','impression','conversion']),'ts':int(time.time())-random.randint(0,86400*90),'sessionId':secrets.token_hex(8),'properties':dict(('p%d'%j,secrets.token_hex(random.randint(4,32))) for j in range(random.randint(2,8)))})
        elif rtype==1:  # cached API response
            v=base64.b64encode(os.urandom(random.randint(2048,16384))).decode()
        elif rtype==2:  # service worker cache
            v=json.dumps({'url':'https://cdn.example.com/assets/%s.%s'%(secrets.token_hex(16),random.choice(['js','css','woff2','png'])),'headers':{'content-type':random.choice(['text/javascript','text/css','font/woff2']),'etag':'"%s"'%secrets.token_hex(16)},'body':base64.b64encode(os.urandom(random.randint(512,8192))).decode()})
        else:  # structured record
            v=json.dumps({'id':random.randint(1,999999),'data':dict(('f%d'%j,secrets.token_hex(random.randint(8,64))) for j in range(random.randint(3,12))),'meta':{'ts':int(time.time())-random.randint(0,86400*90),'v':random.randint(1,5)}})
        k='%s:%s:%s'%(prefix,['analytics','cache','sw','rec'][rtype],secrets.token_hex(6))
        entries.append((k,v));current+=len(v)+len(k);i+=1
    return entries

# ================================================================
# PART F: Scale IndexedDB to 100MB+
# ================================================================
def _scale_idb(pp,config,target_mb=110):
    sd=pp/'storage'/'default'
    current=sum(f.stat().st_size for f in sd.rglob('idb/*.sqlite') if f.is_file()) if sd.exists() else 0
    remaining=(target_mb*1024*1024)-current
    if remaining<=0: return
    idb_domains={'google.com':['search_cache','offline_pages','sync_data'],'youtube.com':['watch_history','player_cache','thumbnail_cache','recommendations'],'facebook.com':['feed_cache','message_cache','notification_cache','media_cache'],'amazon.com':['product_cache','order_history','recommendation_cache'],'twitter.com':['tweet_cache','timeline_cache','notification_cache'],'reddit.com':['subreddit_cache','post_cache','comment_cache'],'gmail.com':['email_cache','attachment_index','label_cache'],'steampowered.com':['game_library','achievement_cache','friend_cache'],'netflix.com':['title_cache','continue_watching','my_list'],'spotify.com':['track_cache','playlist_cache','recently_played']}
    bpd=remaining//max(len(idb_domains),1)
    for domain,stores in idb_domains.items():
        dd=sd/('https+++www.'+domain)/'idb';dd.mkdir(parents=True,exist_ok=True)
        dbh=hashlib.md5(domain.encode()).hexdigest()[:16]
        conn=_fx_sqlite(dd/(dbh+'.sqlite'));c=conn.cursor()
        c.execute('CREATE TABLE IF NOT EXISTS object_data(id INTEGER PRIMARY KEY,object_store_id INTEGER,key_value BLOB,data BLOB,file_ids TEXT)')
        c.execute('CREATE TABLE IF NOT EXISTS object_store(id INTEGER PRIMARY KEY,auto_increment INTEGER NOT NULL DEFAULT 0,name TEXT NOT NULL,key_path TEXT)')
        c.execute('CREATE TABLE IF NOT EXISTS database(name TEXT PRIMARY KEY,origin TEXT,version INTEGER NOT NULL DEFAULT 0,last_vacuum_time INTEGER NOT NULL DEFAULT 0,last_analyze_time INTEGER NOT NULL DEFAULT 0,last_vacuum_size INTEGER NOT NULL DEFAULT 0)')
        for i,sn in enumerate(stores,1): c.execute('INSERT OR IGNORE INTO object_store VALUES(?,?,?,?)',(i,1,sn,'id'))
        rid=100000;cb=0  # Start from high offset to avoid conflict with existing records
        while cb<bpd and rid<1000000:
            sid=random.randint(1,len(stores))
            data=json.dumps({'id':rid,'type':stores[sid-1],'timestamp':int(time.time()*1000)-random.randint(0,86400000*90),'payload':dict(('f%d'%j,secrets.token_hex(random.randint(16,128))) for j in range(random.randint(3,15))),'meta':{'v':random.randint(1,5),'src':random.choice(['api','cache','sync','local'])}}).encode()
            c.execute('INSERT OR REPLACE INTO object_data(id,object_store_id,key_value,data) VALUES(?,?,?,?)',(rid,sid,struct.pack('>I',rid),data))
            cb+=len(data);rid+=1
        conn.commit();conn.close()

# ================================================================
# PART G: Real HTTP cache with metadata
# ================================================================
def _gen_cache(pp,config,target_mb=220):
    cd=pp/'cache2'/'entries';cd.mkdir(parents=True,exist_ok=True)
    # Remove old random cache files
    import shutil as _shu
    for f in cd.iterdir():
        if f.is_file(): f.unlink()
        elif f.is_dir(): _shu.rmtree(f)
    current=0;target=target_mb*1024*1024
    resources=_cache_templates()
    while current<target:
        res=random.choice(resources)
        content=_cache_content(res)
        meta=_cache_meta(res,len(content))
        offset=len(content)
        entry=content+meta+struct.pack('<I',offset)
        fn=hashlib.sha1(res['url'].encode()).hexdigest()
        (cd/fn).write_bytes(entry)
        current+=len(entry)

def _cache_templates():
    t=[]
    cdns=['cdn.jsdelivr.net','unpkg.com','cdnjs.cloudflare.com','static.xx.fbcdn.net','www.gstatic.com','s.pinimg.com']
    for _ in range(50): t.append({'url':'https://%s/npm/%s/dist/bundle.min.js'%(random.choice(cdns),secrets.token_hex(8)),'ct':'application/javascript','sr':(50000,500000),'type':'js'})
    for _ in range(30): t.append({'url':'https://%s/css/%s.min.css'%(random.choice(cdns),secrets.token_hex(6)),'ct':'text/css','sr':(10000,100000),'type':'css'})
    imgs=['images-na.ssl-images-amazon.com','m.media-amazon.com','i.ytimg.com','pbs.twimg.com','avatars.githubusercontent.com','encrypted-tbn0.gstatic.com']
    for _ in range(100):
        ext=random.choice(['jpg','png','webp'])
        t.append({'url':'https://%s/images/%s.%s'%(random.choice(imgs),secrets.token_hex(16),ext),'ct':'image/%s'%('jpeg' if ext=='jpg' else ext),'sr':(5000,800000),'type':'image'})
    for _ in range(15): t.append({'url':'https://fonts.gstatic.com/s/%s/v%d/%s.woff2'%(random.choice(['roboto','opensans','lato','montserrat']),random.randint(20,35),secrets.token_hex(8)),'ct':'font/woff2','sr':(20000,80000),'type':'font'})
    for _ in range(40):
        dom=random.choice(['www.google.com','www.youtube.com','www.facebook.com','api.twitter.com','www.reddit.com'])
        t.append({'url':'https://%s/api/%s'%(dom,secrets.token_hex(8)),'ct':'application/json','sr':(500,50000),'type':'json'})
    return t

def _cache_content(res):
    lo,hi=res['sr'];sz=random.randint(lo,hi);rt=res['type']
    if rt=='js':
        toks=['var ','function(',')){','return ','this.','new ','if(','else{','for(','.prototype.','module.exports=','window.','document.','addEventListener(','querySelector(','JSON.parse(','Promise.','async ','await ','fetch(','const ','let ','class ','extends ',]
        c='';
        while len(c)<sz: c+=random.choice(toks)+secrets.token_hex(random.randint(2,12))+random.choice([';','','\n'])
        return c[:sz].encode()
    elif rt=='css':
        sels=['.container','#main','body','div','span','a:hover','.btn','.nav','header','footer','.card','.modal','@media','.flex','.grid','h1','p','input']
        props=['display:','position:','margin:','padding:','color:','background:','font-size:','border:','width:','height:','opacity:','transform:','transition:']
        c='';
        while len(c)<sz: c+='%s{%s%s}'%(random.choice(sels),random.choice(props),secrets.token_hex(4))
        return c[:sz].encode()
    elif rt=='image':
        ct=res['ct']
        if 'jpeg' in ct: hdr=bytes([0xFF,0xD8,0xFF,0xE0,0x00,0x10,0x4A,0x46,0x49,0x46,0x00,0x01]);return hdr+os.urandom(sz-len(hdr))
        elif 'png' in ct: png=_make_favicon_png(random.randint(0,255),random.randint(0,255),random.randint(0,255));return png+os.urandom(max(0,sz-len(png)))
        elif 'webp' in ct: hdr=b'RIFF'+struct.pack('<I',sz-8)+b'WEBP';return hdr+os.urandom(sz-len(hdr))
        return os.urandom(sz)
    elif rt=='font': hdr=b'wOF2'+struct.pack('>I',0x00010000)+struct.pack('>I',sz);return hdr+os.urandom(sz-len(hdr))
    elif rt=='json':
        d=json.dumps({'data':dict(('k%d'%i,secrets.token_hex(random.randint(8,64))) for i in range(random.randint(5,50)))})
        while len(d)<sz: d+=json.dumps({'x':secrets.token_hex(64)})
        return d[:sz].encode()
    return os.urandom(sz)

def _cache_meta(res,content_len):
    now=int(time.time());ver=3;fc=random.randint(1,20);lf=now-random.randint(0,86400*30);lm=lf-random.randint(0,86400*90)
    frec=random.randint(100,10000);exp=now+random.randint(86400,86400*365)
    parts=res['url'].split('//');host=parts[1].split('/')[0] if len(parts)>1 else 'unknown'
    dom='.'.join(host.split('.')[-2:])
    key=('O^partitionKey=%%28https%%2C%s%%29,:https://%s'%(dom,parts[1] if len(parts)>1 else '')).encode()
    m=struct.pack('<I',ver)+struct.pack('<I',fc)+struct.pack('<I',lf)+struct.pack('<I',lm)+struct.pack('<I',frec)+struct.pack('<I',exp)+struct.pack('<I',len(key))+key
    hdrs=('HTTP/1.1 200 OK\r\nContent-Type: %s\r\nContent-Length: %d\r\nETag: "%s"\r\nCache-Control: public, max-age=%d\r\nLast-Modified: %s\r\nServer: %s\r\n\r\n'%(res['ct'],content_len,secrets.token_hex(16),random.randint(3600,31536000),_http_date(lm),random.choice(['gws','cloudflare','nginx','AmazonS3','Apache']))).encode()
    m+=struct.pack('<I',len(hdrs))+hdrs
    return m

# ================================================================
# PART H: Directory structure
# ================================================================
def _gen_dirs(pp,cts,profile_age):
    # datareporting/
    dr=pp/'datareporting';dr.mkdir(exist_ok=True)
    (dr/'state.json').write_text(json.dumps({'currentPolicyVersion':2,'policyVersion':2,'isDefaultBrowser':False,'dataSubmissionPolicyAcceptedVersion':2,'dataSubmissionPolicyNotifiedTime':_ctime_iso(cts)}))
    (dr/'session-state.json').write_text(json.dumps({'previousSessionId':secrets.token_hex(16),'subsessionId':secrets.token_hex(16),'profileSubsessionCounter':random.randint(50,500),'subsessionCounter':random.randint(1,10),'previousSubsessionId':secrets.token_hex(16)}))
    # Other dirs
    for d in ['security_state','storage/permanent/chrome/idb','sessionstore-backups','startupCache','bookmarkbackups','crashes/events','crashes/store','saved-telemetry-pings']:
        (pp/d).mkdir(parents=True,exist_ok=True)
    (pp/'security_state'/'TransportSecurity.txt').write_text('')
    # bounce-tracking-protection.sqlite (Firefox 120+)
    _bt=sqlite3.connect(str(pp/'bounce-tracking-protection.sqlite'));_btc=_bt.cursor()
    _btc.execute('PRAGMA page_size=32768');_btc.execute('PRAGMA journal_mode=delete')
    _btc.execute('CREATE TABLE IF NOT EXISTS bounce_tracking(id INTEGER PRIMARY KEY,site_origin TEXT NOT NULL UNIQUE,bounce_time INTEGER NOT NULL DEFAULT 0,user_activation_time INTEGER NOT NULL DEFAULT 0)')
    _bt.commit();_bt.close()
    # ls-archive.sqlite (localStorage archive - real Firefox always has this)
    _la=sqlite3.connect(str(pp/'storage'/'ls-archive.sqlite'));_lac=_la.cursor()
    _lac.execute('PRAGMA page_size=4096');_lac.execute('PRAGMA journal_mode=delete')
    _lac.execute('CREATE TABLE IF NOT EXISTS data(originKey TEXT NOT NULL,key TEXT NOT NULL,utf16Length INTEGER NOT NULL DEFAULT 0,compressed INTEGER NOT NULL DEFAULT 0,lastAccessTime INTEGER NOT NULL DEFAULT 0,value BLOB NOT NULL,originAttributes TEXT NOT NULL DEFAULT \'\',PRIMARY KEY(originAttributes,originKey,key))')
    _la.commit();_la.close()
    # storage/permanent/chrome/.metadata-v2
    md2=pp/'storage'/'permanent'/'chrome'/'.metadata-v2'
    md2.parent.mkdir(parents=True,exist_ok=True)
    md2.write_bytes(struct.pack('<Q',int(time.time()*1000000))+b'\x00'*54)  # 62-byte metadata
