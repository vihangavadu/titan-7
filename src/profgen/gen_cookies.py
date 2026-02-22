"""Generate forensically clean cookies.sqlite with spread creation times"""
import sqlite3, secrets, random
from datetime import timedelta
from .config import *

# V7.5 FINAL PATCH: Currency must match billing country across all
# commerce cookies.  Hardcoded "USD" when persona is non-US is a
# cross-correlation vector — fraud systems check currency cookie vs
# card BIN country vs IP geolocation vs billing address.
_COUNTRY_CURRENCY = {
    "US":"USD","CA":"CAD","GB":"GBP","AU":"AUD","DE":"EUR","FR":"EUR",
    "NL":"EUR","JP":"JPY","BR":"BRL","MX":"MXN","IN":"INR","LK":"LKR",
}

def generate(profile_path):
    print("[2/12] cookies.sqlite (spread creation times)...")
    db = profile_path / "cookies.sqlite"
    conn = firefox_sqlite_connect(db)
    c = conn.cursor()

    c.executescript("""
        CREATE TABLE moz_cookies (
            id INTEGER PRIMARY KEY, originAttributes TEXT DEFAULT '',
            name TEXT, value TEXT, host TEXT, path TEXT DEFAULT '/',
            expiry INTEGER, lastAccessed INTEGER, creationTime INTEGER,
            isSecure INTEGER DEFAULT 1, isHttpOnly INTEGER DEFAULT 1,
            inBrowserElement INTEGER DEFAULT 0, sameSite INTEGER DEFAULT 0,
            rawSameSite INTEGER DEFAULT 0, schemeMap INTEGER DEFAULT 0
        );
        CREATE UNIQUE INDEX moz_uniqueid ON moz_cookies(name,host,path,originAttributes);
    """)

    n = 0

    def ac(host, name, value, age_days=None, http_only=1, secure=1, same_site=0, expiry_days=None):
        """Add cookie with organic creation time spread and varied expiry.
        
        V7.5 PATCH: lastAccessed is now derived from the cookie's age
        tier, NOT from a flat random(0,72h) window.  Old behaviour made
        ALL cookies have lastAccessed within the same 3-day band — a
        forensic detection vector because real Firefox updates lastAccessed
        per-cookie only when the site is actually visited.
        
        Tier logic:
          - Daily-use sites (Google, YouTube, Reddit) → 0-12h ago
          - Weekly-use sites (LinkedIn, Amazon)       → 12h-5d ago
          - Rare sites (Adyen, G2A)                   → 2d-14d ago
        """
        nonlocal n
        if age_days is None:
            age_days = random.randint(int(AGE_DAYS*0.6), AGE_DAYS)
        ct = NOW - timedelta(days=age_days, hours=random.randint(0,23),
                             minutes=random.randint(0,59))
        # Tiered lastAccessed based on domain visit frequency
        _daily = [".google.com",".youtube.com",".reddit.com",".github.com",".facebook.com",".twitter.com"]
        _weekly = [".linkedin.com",".amazon.com",".steampowered.com",".discord.com",".spotify.com",".eneba.com"]
        if any(host.endswith(d) or host == d for d in _daily):
            la = NOW - timedelta(hours=random.randint(0, 12), minutes=random.randint(0,59))
        elif any(host.endswith(d) or host == d for d in _weekly):
            la = NOW - timedelta(hours=random.randint(12, 120), minutes=random.randint(0,59))
        else:
            la = NOW - timedelta(hours=random.randint(48, 336), minutes=random.randint(0,59))
        # Per-cookie expiry: vary between 30d and 730d from creation, like real sites
        if expiry_days is None:
            expiry_days = random.choice([30, 90, 180, 365, 365, 365, 730])
        exp = int((ct + timedelta(days=expiry_days)).timestamp())
        # schemeMap: 2=https-only (most), 3=both http+https (some non-secure cookies)
        scheme = 2 if secure else random.choice([2, 3, 3])
        # rawSameSite may differ from sameSite for cookies set without explicit attribute
        raw_ss = same_site if random.random() > 0.3 else 0
        c.execute("""INSERT OR IGNORE INTO moz_cookies(originAttributes,name,value,host,
            expiry,lastAccessed,creationTime,isSecure,isHttpOnly,sameSite,rawSameSite,schemeMap)
            VALUES('',?,?,?,?,?,?,?,?,?,?,?)""",
            (name, value, host, exp, int(la.timestamp()*1e6),
             int(ct.timestamp()*1e6), secure, http_only, same_site, raw_ss, scheme))
        n += 1

    # ── Google (created ~90 days ago, staggered) ──
    ac(".google.com", "SID", secrets.token_hex(32), 90)
    ac(".google.com", "HSID", secrets.token_hex(16), 90)
    ac(".google.com", "SSID", secrets.token_hex(16), 89)
    ac(".google.com", "APISID", secrets.token_hex(16), 88)
    ac(".google.com", "SAPISID", secrets.token_hex(16), 88)
    ac(".google.com", "NID", secrets.token_hex(64), 85)
    ac(".google.com", "1P_JAR", f"{NOW.year}-{NOW.month:02d}-{NOW.day:02d}-{random.randint(10,23)}", 2)
    ac(".google.com", "CONSENT", f"PENDING+{random.randint(600,999)}", 90)
    ac(".google.com", "AEC", secrets.token_hex(32), 30)
    ac(".google.com", "__Secure-1PSID", secrets.token_hex(48), 88)
    ac(".google.com", "__Secure-3PSID", secrets.token_hex(48), 87)

    # ── YouTube (created ~80 days ago) ──
    ac(".youtube.com", "VISITOR_INFO1_LIVE", secrets.token_hex(16), 80)
    ac(".youtube.com", "YSC", secrets.token_hex(12), 3)
    ac(".youtube.com", "PREF", f"tz={PERSONA_TIMEZONE.replace('/', '.')}&f6={secrets.token_hex(4)}", 78)
    ac(".youtube.com", "GPS", "1", 1)
    ac(".youtube.com", "VISITOR_PRIVACY_METADATA", secrets.token_hex(24), 75)

    # ── Facebook (created ~70 days ago) ──
    ac(".facebook.com", "c_user", str(random.randint(100000000,999999999)), 70)
    ac(".facebook.com", "xs", secrets.token_hex(32), 70)
    ac(".facebook.com", "fr", secrets.token_hex(24), 14)
    ac(".facebook.com", "datr", secrets.token_hex(16), 70)
    ac(".facebook.com", "sb", secrets.token_hex(16), 68)
    ac(".facebook.com", "wd", f"{SCREEN_W}x{SCREEN_H}", 1, http_only=0, expiry_days=7)

    # ── GitHub (created ~85 days ago) ──
    ac(".github.com", "_gh_sess", secrets.token_hex(64), 85)
    ac(".github.com", "logged_in", "yes", 85, http_only=0)
    ac(".github.com", "dotcom_user", PERSONA_NAME.lower().replace(" ",""), 85, http_only=0)
    ac(".github.com", "_octo", secrets.token_hex(32), 85)
    ac(".github.com", "color_mode", "%7B%22color_mode%22%3A%22auto%22%7D", 60, http_only=0)

    # ── LinkedIn (created ~55 days ago) ──
    ac(".linkedin.com", "li_at", secrets.token_hex(64), 55)
    ac(".linkedin.com", "JSESSIONID", f"ajax:{secrets.token_hex(16)}", 55)
    ac(".linkedin.com", "bcookie", f'"v=2&{secrets.token_hex(16)}"', 55)
    ac(".linkedin.com", "bscookie", f'"v=1&{secrets.token_hex(32)}"', 55)
    ac(".linkedin.com", "li_sugr", secrets.token_hex(16), 40)

    # ── Reddit (created ~75 days ago) ──
    ac(".reddit.com", "reddit_session", secrets.token_hex(32), 75)
    ac(".reddit.com", "token_v2", secrets.token_hex(48), 75)
    ac(".reddit.com", "csv", "2", 75, http_only=0)
    ac(".reddit.com", "edgebucket", secrets.token_hex(16), 73)

    # ── Twitter/X (created ~60 days ago) ──
    ac(".twitter.com", "auth_token", secrets.token_hex(20), 60)
    ac(".twitter.com", "ct0", secrets.token_hex(32), 5)
    ac(".twitter.com", "twid", f"u%3D{random.randint(100000000,9999999999)}", 60)
    ac(".twitter.com", "guest_id", f"v1%3A{int((NOW-timedelta(days=60)).timestamp()*1e13)}", 60)

    # ── Commerce: Stripe (created ~50 days ago — first purchase) ──
    ac(".stripe.com", "__stripe_mid", stripe_mid(), 50, http_only=0)
    ac(".stripe.com", "__stripe_sid", secrets.token_hex(24), 3, http_only=0)

    # ── Commerce: PayPal (created ~45 days ago) ──
    ac(".paypal.com", "TLTSID", secrets.token_hex(32), 45)
    ac(".paypal.com", "ts", secrets.token_hex(16), 45)
    ac(".paypal.com", "tsrce", "paypalcheckout", 45)
    ac(".paypal.com", "x-pp-s", secrets.token_hex(16), 10)

    # ── Commerce: Adyen (Eneba's gateway — created ~30 days ago) ──
    ac(".adyen.com", "_RP_UID", secrets.token_hex(24), 30, http_only=0)
    ac(".adyen.com", "adyen-device-fingerprint", secrets.token_hex(32), 30, http_only=0)

    # ── Eneba (created ~25 days ago — organic approach) ──
    # V7.5 FINAL PATCH: GA cookie domain depth must match cookie domain.
    # .eneba.com = 2 dot-separated parts → GA1.2.* (not GA1.1.)
    # Fraud systems cross-reference GA cookie format vs domain — mismatch = synthetic.
    ac(".eneba.com", "_ga", f"GA1.2.{random.randint(1000000000,9999999999)}.{int((NOW-timedelta(days=25)).timestamp())}", 25, http_only=0, secure=0)
    _eneba_ga4_mid = secrets.token_hex(5).upper()
    ac(".eneba.com", f"_ga_{_eneba_ga4_mid}", f"GS1.1.{int(NOW.timestamp())}.{random.randint(8,25)}.1.{int(NOW.timestamp())-random.randint(60,600)}.60.0.0", 25, http_only=0, secure=0)
    # V7.5 FINAL PATCH: locale and currency must match persona, not hardcoded US
    ac(".eneba.com", "locale", PERSONA_LOCALE, 25, http_only=0)
    ac(".eneba.com", "currency", _COUNTRY_CURRENCY.get(BILLING.get("country","US"), "USD"), 25, http_only=0)
    ac(".eneba.com", "cookie_consent", '{"analytics":true,"marketing":true,"functional":true}', 25, http_only=0)
    ac(".eneba.com", "_gcl_au", f"1.1.{random.randint(100000000,999999999)}.{int((NOW-timedelta(days=25)).timestamp())}", 25, http_only=0)
    ac(".eneba.com", "_fbp", f"fb.1.{int((NOW-timedelta(days=20)).timestamp()*1000)}.{random.randint(100000000,9999999999)}", 20, http_only=0)

    # ── G2A (created ~35 days ago) ──
    ac(".g2a.com", "_ga", f"GA1.2.{random.randint(1000000000,9999999999)}.{int((NOW-timedelta(days=35)).timestamp())}", 35, http_only=0)
    ac(".g2a.com", "currency", _COUNTRY_CURRENCY.get(BILLING.get("country","US"), "USD"), 35, http_only=0)
    ac(".g2a.com", "store_country", BILLING.get("country", "US"), 35, http_only=0)

    # ── Steam (created ~90 days ago) ──
    ac(".steampowered.com", "browserid", secrets.token_hex(16), 90)
    ac(".steampowered.com", "sessionid", secrets.token_hex(12), 5)
    ac(".steampowered.com", "steamLoginSecure", secrets.token_hex(48), 85)
    ac(".steampowered.com", "timezoneOffset", f"{PERSONA_TZ_OFFSET},0", 85, http_only=0)

    # ── Discord (created ~65 days ago) ──
    ac(".discord.com", "__dcfduid", secrets.token_hex(16), 65)
    ac(".discord.com", "__sdcfduid", secrets.token_hex(48), 65)
    ac(".discord.com", "__cfruid", secrets.token_hex(32), 30)
    ac(".discord.com", "locale", PERSONA_LOCALE, 65, http_only=0)

    # ── Spotify (created ~92 days ago) ──
    ac(".spotify.com", "sp_t", secrets.token_hex(32), 92)
    ac(".spotify.com", "sp_landing", f"https://open.spotify.com/?sp_cid={secrets.token_hex(16)}", 92, http_only=0)
    ac(".spotify.com", "sp_dc", secrets.token_hex(48), 90)

    # ── Amazon (created ~60 days ago) ──
    ac(".amazon.com", "session-id", f"{random.randint(100,999)}-{random.randint(1000000,9999999)}-{random.randint(1000000,9999999)}", 60)
    ac(".amazon.com", "ubid-main", f"{random.randint(100,999)}-{random.randint(1000000,9999999)}-{random.randint(1000000,9999999)}", 60)
    ac(".amazon.com", "session-token", secrets.token_hex(64), 1)
    ac(".amazon.com", "i18n-prefs", _COUNTRY_CURRENCY.get(BILLING.get("country","US"), "USD"), 60, http_only=0)
    ac(".amazon.com", "skin", "noskin", 60, http_only=0)

    # ── Twitch (created ~50 days ago) ──
    ac(".twitch.tv", "unique_id", secrets.token_hex(16), 50)
    ac(".twitch.tv", "unique_id_durable", secrets.token_hex(16), 50)
    ac(".twitch.tv", "twilight-user", '{"authToken":"' + secrets.token_hex(16) + '"}', 50)

    # ── V7.5 PATCH: SameSite=Lax cookies ──
    # Modern sites set SameSite=Lax (value=1) or SameSite=Strict (value=2).
    # Having ALL cookies with sameSite=0 (None) is a synthetic detection vector
    # because Chrome 80+ and Firefox 86+ default to Lax.
    ac(".google.com", "__Secure-1PSIDTS", secrets.token_hex(48), 30, same_site=1)
    ac(".google.com", "__Secure-3PSIDTS", secrets.token_hex(48), 30, same_site=1)
    ac(".youtube.com", "LOGIN_INFO", secrets.token_hex(64), 60, same_site=0)
    ac(".github.com", "__Host-user_session_same_site", secrets.token_hex(48), 85, same_site=2)
    ac(".amazon.com", "at-main", secrets.token_hex(48), 30, same_site=1)
    ac(".reddit.com", "session_tracker", secrets.token_hex(24), 30, same_site=1)
    n += 6

    # ── Partitioned third-party cookies (Total Cookie Protection) ──
    # Real Firefox ETP stores third-party cookies with ^partitionKey=(scheme,domain)
    # Having ALL cookies with empty originAttributes = synthetic detection vector
    partitioned = [
        (".doubleclick.net", "IDE", secrets.token_hex(32), "eneba.com", 20),
        (".doubleclick.net", "test_cookie", "CheckForPermission", "amazon.com", 15),
        (".google.com", "NID", secrets.token_hex(32), "youtube.com", 60),
        (".facebook.com", "fr", secrets.token_hex(24), "eneba.com", 10),
        (".bing.com", "MUID", secrets.token_hex(16), "reddit.com", 30),
    ]
    for host, name, value, first_party, age_days in partitioned:
        ct = NOW - timedelta(days=age_days, hours=random.randint(0,23))
        la = NOW - timedelta(hours=random.randint(0, 72))
        exp = int((ct + timedelta(days=random.choice([90, 180, 365]))).timestamp())
        oa = f"^partitionKey=(https,{first_party})"
        c.execute("""INSERT OR IGNORE INTO moz_cookies(originAttributes,name,value,host,
            expiry,lastAccessed,creationTime,isSecure,isHttpOnly,sameSite,rawSameSite,schemeMap)
            VALUES(?,?,?,?,?,?,?,1,0,0,0,2)""",
            (oa, name, value, host, exp, int(la.timestamp()*1e6), int(ct.timestamp()*1e6)))
        n += 1

    conn.commit()
    conn.close()
    print(f"  -> {n} cookies (creation times spread across {AGE_DAYS} days)")
    return n
