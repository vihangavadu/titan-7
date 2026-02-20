"""Generate forensically clean localStorage with realistic key names"""
import sqlite3, secrets, random, json, hashlib, base64, struct
from datetime import timedelta
from .config import *

# Realistic localStorage keys per domain (no synthetic _c_* padding)
REALISTIC_LS_KEYS = {
    "google.com": {
        "NID": lambda: secrets.token_hex(64),
        "CONSENT": lambda: f"YES+cb.{int(CREATED.timestamp())}",
        "SEARCH_SAMESITE": lambda: "CgQI5ZoB",
        "sb_wiz.zpc.gws-wiz-serp.bm": lambda: "1",
        "ds_ntp:num_personal_suggestions": lambda: str(random.randint(3,8)),
        "cr/uxr/ui.prf": lambda: json.dumps({"tz":PERSONA_TIMEZONE,"ul":PERSONA_LOCALE.split("-")[0]}),
    },
    "youtube.com": {
        "yt-player-volume": lambda: json.dumps({"data":json.dumps({"volume":random.randint(40,90),"muted":False}),"creation":int(CREATED.timestamp()*1000)}),
        "yt-player-quality": lambda: json.dumps({"data":"auto","creation":int(CREATED.timestamp()*1000)}),
        "yt-player-bandaid-host": lambda: "redirector.googlevideo.com",
        "yt-html5-player-modules::subtitlesModuleData::display-settings": lambda: json.dumps({"fontFamily":4,"color":"#fff","fontSizeIncrement":0,"background":"#080808","backgroundOpacity":"0.75"}),
        "ytidb::LAST_RESULT_ENTRY_KEY": lambda: json.dumps([{"key":"ytidb::LAST_RESULT_ENTRY_KEY","value":True,"expiration":int((NOW+timedelta(days=365)).timestamp()*1000)}]),
        "yt.innertube::nextId": lambda: str(random.randint(100,500)),
        "yt.innertube::requests": lambda: json.dumps({"count":random.randint(500,2000),"firstRequestMs":int(CREATED.timestamp()*1000)}),
        "yt-remote-device-id": lambda: secrets.token_hex(16),
        "yt-remote-connected-devices": lambda: json.dumps([]),
    },
    "github.com": {
        "logged_in": lambda: "true",
        "color_mode": lambda: json.dumps({"color_mode":"auto","light_theme":{"name":"light","color_mode":"light"},"dark_theme":{"name":"dark","color_mode":"dark"}}),
        "preferred_color_mode": lambda: "dark",
        "tz": lambda: PERSONA_TIMEZONE,
        "has_hierarchical_foci": lambda: "true",
        "dismissed-hierarchical-foci": lambda: "[]",
        "primer.octicons.iconsByName": lambda: json.dumps({"mark-github":"<svg>...</svg>"}),
    },
    "amazon.com": {
        "csm-hit": lambda: f"tb:{secrets.token_hex(8)}+s-{secrets.token_hex(8)}|{int(NOW.timestamp()*1000)}",
        "session-id": lambda: secrets.token_hex(16),
        "ubid-main": lambda: secrets.token_hex(16),
        "session-token": lambda: secrets.token_hex(64),
        "a]p-page-shared-counts": lambda: json.dumps({"dp":random.randint(10,50),"hp":random.randint(5,20)}),
    },
    "reddit.com": {
        "recent_srs": lambda: json.dumps(["gaming","GameDeals","Steam","pcgaming","pcmasterrace","programming"]),
        "reddit.timestamp": lambda: str(int(NOW.timestamp())),
        "initiate": lambda: "true",
        "redesign_optout": lambda: "false",
        "eu_cookie_v2": lambda: "3",
    },
    "facebook.com": {
        "dpr": lambda: "2",
        "_js_datr": lambda: secrets.token_hex(16),
    },
    "eneba.com": {
        "cart_viewed": lambda: "true",
        "currency": lambda: {"US":"USD","CA":"CAD","GB":"GBP","AU":"AUD","DE":"EUR","FR":"EUR","NL":"EUR","JP":"JPY","BR":"BRL","MX":"MXN"}.get(BILLING.get("country","US"),"USD"),
        "region": lambda: "global",
        "cookie_consent": lambda: json.dumps({"analytics":True,"marketing":True,"functional":True,"ts":int((NOW-timedelta(days=25)).timestamp()*1000)}),
        "locale": lambda: PERSONA_LOCALE.split("-")[0],
        "recently_viewed": lambda: json.dumps([{"slug":"crypto-gift-card-50-usd","ts":int((NOW-timedelta(days=3)).timestamp()*1000)},{"slug":"steam-gift-card-20-eur","ts":int((NOW-timedelta(days=10)).timestamp()*1000)}]),
        "user_preferences": lambda: json.dumps({"theme":"light","notifications":True}),
    },
    "linkedin.com": {
        "voyager-web:badges-count": lambda: str(random.randint(0,5)),
        "C_C_M": lambda: secrets.token_hex(8),
        "timezone": lambda: PERSONA_TIMEZONE,
        "li_theme": lambda: "system",
    },
    "steampowered.com": {
        "wishlistCount": lambda: str(random.randint(5,30)),
        "strInventoryLastContext": lambda: "730",
        "strResponsiveCSSChecked": lambda: "1",
    },
    "twitter.com": {
        "d_prefs": lambda: json.dumps({"dark_mode":"0","sensitive_media":"0"}),
        "rweb_optin": lambda: "side_nav_animation_v1:on",
        "night_mode": lambda: "0",
    },
    "g2a.com": {
        "currency": lambda: {"US":"USD","CA":"CAD","GB":"GBP","AU":"AUD","DE":"EUR","FR":"EUR","NL":"EUR","JP":"JPY","BR":"BRL","MX":"MXN"}.get(BILLING.get("country","US"),"USD"),
        "country": lambda: BILLING.get("country", "US"),
        "g2a_locale": lambda: PERSONA_LOCALE.split("-")[0],
    },
}

# Realistic cache/app data key patterns (replaces _c_* padding)
CACHE_KEY_PATTERNS = [
    lambda i,d: (f"sw-cache-{d.split('.')[0]}-v{random.randint(1,4)}-asset-{i}", lambda: secrets.token_hex(random.randint(128,512))),
    lambda i,d: (f"idb-{d.split('.')[0]}-store-{i}", lambda: json.dumps({"v":random.randint(1,5),"d":secrets.token_hex(random.randint(64,256)),"ts":int((NOW-timedelta(days=random.randint(0,AGE_DAYS))).timestamp()*1000)})),
    lambda i,d: (f"_segment.{d.split('.')[0]}.user.{secrets.token_hex(4)}", lambda: json.dumps({"traits":{},"sessionId":random.randint(1000,9999)})),
    lambda i,d: (f"persist:root-{d.split('.')[0]}", lambda: json.dumps({"user":json.dumps({"loggedIn":True}),"preferences":json.dumps({"lang":PERSONA_LOCALE.split("-")[0]}),"_persist":json.dumps({"version":1,"rehydrated":True})})),
    lambda i,d: (f"https://www.{d}::ServiceWorkerRegistration", lambda: json.dumps({"scope":f"https://www.{d}/","scriptURL":f"https://www.{d}/sw.js"})),
    lambda i,d: (f"gtm.{secrets.token_hex(4)}", lambda: json.dumps({"event":"gtm.load","gtm.uniqueEventId":random.randint(1,100)})),
    lambda i,d: (f"intercom.intercom-state-{secrets.token_hex(4)}", lambda: json.dumps({"user":{"anonymous_id":secrets.token_hex(12)}})),
    lambda i,d: (f"ajs_user_id", lambda: secrets.token_hex(16)),
    lambda i,d: (f"ajs_anonymous_id", lambda: f'"{secrets.token_hex(16)}"'),
    lambda i,d: (f"mp_{secrets.token_hex(8)}_mixpanel", lambda: json.dumps({"distinct_id":secrets.token_hex(16),"$device_id":secrets.token_hex(16),"$initial_referrer":"$direct"})),
    lambda i,d: (f"ab.storage.deviceId.{secrets.token_hex(4)}", lambda: json.dumps({"g":secrets.token_hex(16),"e":int((NOW+timedelta(days=365)).timestamp()*1000)})),
    lambda i,d: (f"_dd_s", lambda: f"rum=0&expire={int((NOW+timedelta(minutes=15)).timestamp()*1000)}"),
    lambda i,d: (f"optimizely_data${d}", lambda: json.dumps({"revision":str(random.randint(100,999)),"session_id":secrets.token_hex(8)})),
    lambda i,d: (f"amplitude_id_{secrets.token_hex(8)}_{d.split('.')[0]}", lambda: json.dumps({"deviceId":secrets.token_hex(16),"userId":None,"optOut":False,"sessionId":int(NOW.timestamp()*1000),"lastEventTime":int(NOW.timestamp()*1000),"eventId":random.randint(50,500),"identifyId":random.randint(1,20),"sequenceNumber":random.randint(50,500)})),
]

def generate(profile_path):
    print("[3/12] localStorage (500MB+ with realistic keys)...")
    sdir = profile_path / "storage" / "default"
    total = 0
    ec = 0
    # SQLite stores text ~60% efficiently vs raw, so overshoot by 1.7x
    target = int(STORAGE_MB * 1024 * 1024 * 1.7)

    for dom in ALL_DOMAINS:
        dd = sdir / f"https+++www.{dom}" / "ls"
        dd.mkdir(parents=True, exist_ok=True)
        conn = firefox_sqlite_connect(dd / "data.sqlite")
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS data(
            key TEXT PRIMARY KEY, utf16Length INTEGER NOT NULL DEFAULT 0,
            compressed INTEGER NOT NULL DEFAULT 0, lastAccessTime INTEGER NOT NULL DEFAULT 0,
            value BLOB NOT NULL
        )""")

        # Domain-specific keys
        dom_keys = REALISTIC_LS_KEYS.get(dom, {})
        # Only add GA cookies to domains that realistically use Google Analytics
        ga_domains = ["youtube.com","reddit.com","amazon.com","eneba.com",
                      "g2a.com","newegg.com","bestbuy.com","steampowered.com",
                      "ubereats.com","linkedin.com"]
        if dom in ga_domains:
            ga_id = f"GA1.1.{random.randint(1000000000,9999999999)}.{int((NOW-timedelta(days=random.randint(20,AGE_DAYS))).timestamp())}"
            dom_keys["_ga"] = lambda _gid=ga_id: _gid
            dom_keys["_gid"] = lambda: f"GA1.1.{random.randint(1000000000,9999999999)}.{int(NOW.timestamp())}"

        for k, vfn in dom_keys.items():
            v = vfn() if callable(vfn) else vfn
            la_time = int((NOW - timedelta(hours=random.randint(0, 72*24))).timestamp() * 1e6)
            c.execute("INSERT OR REPLACE INTO data(key,utf16Length,lastAccessTime,value) VALUES(?,?,?,?)",
                (k, len(v), la_time, v))
            total += len(k) + len(v); ec += 1

        conn.commit()
        conn.close()

    # Padding with realistic cache/analytics keys (not _c_*)
    print(f"  Base: {total/(1024*1024):.1f}MB — padding to {STORAGE_MB}MB with realistic keys...")
    remaining = target - total
    pad_per = max(remaining // len(ALL_DOMAINS), 0)

    for dom in ALL_DOMAINS:
        db = sdir / f"https+++www.{dom}" / "ls" / "data.sqlite"
        conn = firefox_sqlite_connect(db)
        c = conn.cursor()

        written = 0
        idx = 0
        while written < pad_per:
            pattern = random.choice(CACHE_KEY_PATTERNS)
            k, vfn = pattern(idx, dom)
            v = vfn()
            # V7.5 PATCH: Old code appended raw base64(random_bytes) to the
            # end of realistic JSON values.  This creates an obvious pattern:
            # valid JSON followed by a wall of base64 gibberish.  Fraud ML
            # models trained on real localStorage can detect this instantly.
            #
            # New approach: pad by wrapping data in realistic nested JSON
            # structures (caches, state objects, serialized Redux stores)
            # that naturally contain large string fields.
            target_size = random.choice([512, 1024, 2048, 4096, 8192]) if written < pad_per * 0.5 else random.choice([256, 512, 1024])
            pad_obj = {
                "v": random.randint(1, 5),
                "ts": int((NOW - timedelta(days=random.randint(0, AGE_DAYS))).timestamp() * 1000),
                "data": {},
                "meta": {"source": random.choice(["sw-cache", "idb-sync", "persist", "analytics", "gtm"]),
                         "rev": str(random.randint(100, 9999))}
            }
            # Fill data with plausible key-value pairs until target size
            fill_keys = ["state", "payload", "entries", "config", "cache", "tokens", "assets", "chunks"]
            while len(json.dumps(pad_obj)) < target_size:
                fk = random.choice(fill_keys) + str(random.randint(0, 99))
                pad_obj["data"][fk] = secrets.token_hex(random.randint(32, 256))
            v = json.dumps(pad_obj)

            try:
                la_time = int((NOW - timedelta(hours=random.randint(0, AGE_DAYS*24))).timestamp() * 1e6)
                c.execute("INSERT OR REPLACE INTO data(key,utf16Length,lastAccessTime,value) VALUES(?,?,?,?)",
                    (k, len(v), la_time, v))
                written += len(k) + len(v)
                total += len(k) + len(v)
                ec += 1
            except Exception:
                pass
            idx += 1

        conn.commit()
        conn.close()

    print(f"  -> {ec} entries, {total/(1024*1024):.1f}MB total")
    return ec
