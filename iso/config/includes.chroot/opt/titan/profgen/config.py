"""Profile configuration and shared constants.

OPERATOR: Set these values PER-OPERATION before running profgen.
All downstream generators (cookies, localStorage, places, prefs)
derive timezone, locale, and geo from these values.
Never leave defaults for a real operation.
"""
import sqlite3, secrets, hashlib, random, string, struct, os, json
from datetime import datetime, timedelta
from pathlib import Path


def firefox_sqlite_connect(db_path, page_size=32768):
    """Create a SQLite connection with Firefox-matching PRAGMA settings.
    
    Real Firefox uses:
      - page_size = 32768 (32KB pages)
      - journal_mode = WAL (Write-Ahead Logging)
      - auto_vacuum = INCREMENTAL
      - wal_autocheckpoint = 512
      - foreign_keys = ON (for places.sqlite)
    
    Using default SQLite settings (page_size=4096, journal_mode=DELETE)
    is an INSTANT forensic detection vector.
    """
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    c.execute(f"PRAGMA page_size = {page_size}")
    c.execute("PRAGMA journal_mode = WAL")
    c.execute("PRAGMA auto_vacuum = INCREMENTAL")
    c.execute("PRAGMA wal_autocheckpoint = 512")
    c.execute("PRAGMA foreign_keys = ON")
    conn.commit()
    return conn

# ══════════════════════════════════════════════════════════════════════════
# OPERATOR-SET PERSONA (override via env or titan_profile.json)
# ══════════════════════════════════════════════════════════════════════════
_profile_json = Path(os.environ.get("TITAN_PROFILE_JSON", "/opt/titan/state/active_profile.json"))
if _profile_json.exists():
    _pj = json.loads(_profile_json.read_text())
else:
    _pj = {}

PROFILE_UUID = _pj.get("profile_uuid", os.environ.get("TITAN_PROFILE_UUID", secrets.token_hex(16)))
PERSONA_FIRST = _pj.get("first_name", os.environ.get("TITAN_FIRST_NAME", "alex"))
PERSONA_LAST = _pj.get("last_name", os.environ.get("TITAN_LAST_NAME", "mercer"))
PERSONA_NAME = f"{PERSONA_FIRST} {PERSONA_LAST}"
PERSONA_EMAIL = _pj.get("email", os.environ.get("TITAN_EMAIL", "a.mercer.dev@gmail.com"))
PERSONA_PHONE = _pj.get("phone", os.environ.get("TITAN_PHONE", "+15125550123"))

BILLING = _pj.get("billing", {
    "street": os.environ.get("TITAN_BILLING_STREET", "2400 Nueces St Apt 402"),
    "city":   os.environ.get("TITAN_BILLING_CITY",   "Austin"),
    "state":  os.environ.get("TITAN_BILLING_STATE",  "TX"),
    "zip":    os.environ.get("TITAN_BILLING_ZIP",    "78705"),
    "country":os.environ.get("TITAN_BILLING_COUNTRY","US"),
})

CARD_LAST4 = _pj.get("card_last4", os.environ.get("TITAN_CARD_LAST4", "8921"))
AGE_DAYS = int(_pj.get("age_days", os.environ.get("TITAN_AGE_DAYS", "95")))
STORAGE_MB = int(_pj.get("storage_mb", os.environ.get("TITAN_STORAGE_MB", "500")))
NOW = datetime.now()
CREATED = NOW - timedelta(days=AGE_DAYS)

# ══════════════════════════════════════════════════════════════════════════
# DERIVED GEO / TIMEZONE / LOCALE (auto-computed from BILLING)
# All downstream generators MUST use these — never hardcode tz/locale.
# ══════════════════════════════════════════════════════════════════════════
_STATE_TZ = {
    "AL":"America/Chicago","AK":"America/Anchorage","AZ":"America/Phoenix",
    "AR":"America/Chicago","CA":"America/Los_Angeles","CO":"America/Denver",
    "CT":"America/New_York","DE":"America/New_York","FL":"America/New_York",
    "GA":"America/New_York","HI":"Pacific/Honolulu","ID":"America/Boise",
    "IL":"America/Chicago","IN":"America/Indiana/Indianapolis",
    "IA":"America/Chicago","KS":"America/Chicago","KY":"America/New_York",
    "LA":"America/Chicago","ME":"America/New_York","MD":"America/New_York",
    "MA":"America/New_York","MI":"America/Detroit","MN":"America/Chicago",
    "MS":"America/Chicago","MO":"America/Chicago","MT":"America/Denver",
    "NE":"America/Chicago","NV":"America/Los_Angeles","NH":"America/New_York",
    "NJ":"America/New_York","NM":"America/Denver","NY":"America/New_York",
    "NC":"America/New_York","ND":"America/Chicago","OH":"America/New_York",
    "OK":"America/Chicago","OR":"America/Los_Angeles","PA":"America/New_York",
    "RI":"America/New_York","SC":"America/New_York","SD":"America/Chicago",
    "TN":"America/Chicago","TX":"America/Chicago","UT":"America/Denver",
    "VT":"America/New_York","VA":"America/New_York","WA":"America/Los_Angeles",
    "WV":"America/New_York","WI":"America/Chicago","WY":"America/Denver",
    "DC":"America/New_York",
}
_COUNTRY_TZ = {
    "US":"America/New_York","GB":"Europe/London","CA":"America/Toronto",
    "AU":"Australia/Sydney","DE":"Europe/Berlin","FR":"Europe/Paris",
    "NL":"Europe/Amsterdam","JP":"Asia/Tokyo","LK":"Asia/Colombo",
    "IN":"Asia/Kolkata","BR":"America/Sao_Paulo","MX":"America/Mexico_City",
}
_TZ_OFFSETS = {
    "America/New_York":-18000,"America/Chicago":-21600,"America/Denver":-25200,
    "America/Los_Angeles":-28800,"America/Phoenix":-25200,"America/Anchorage":-32400,
    "Pacific/Honolulu":-36000,"America/Boise":-25200,"America/Detroit":-18000,
    "America/Indiana/Indianapolis":-18000,"Europe/London":0,"Europe/Berlin":3600,
    "Europe/Paris":3600,"Europe/Amsterdam":3600,"Asia/Tokyo":32400,
    "Asia/Colombo":19800,"Asia/Kolkata":19800,"America/Toronto":-18000,
    "Australia/Sydney":39600,"America/Sao_Paulo":-10800,"America/Mexico_City":-21600,
}

def _resolve_timezone():
    state = BILLING.get("state", "")
    country = BILLING.get("country", "US")
    if country == "US" and state in _STATE_TZ:
        return _STATE_TZ[state]
    return _COUNTRY_TZ.get(country, "America/New_York")

PERSONA_TIMEZONE = _pj.get("timezone", os.environ.get("TITAN_TIMEZONE", _resolve_timezone()))
PERSONA_TZ_OFFSET = _TZ_OFFSETS.get(PERSONA_TIMEZONE, -18000)
PERSONA_LOCALE = _pj.get("locale", os.environ.get("TITAN_LOCALE", "en-US"))
PERSONA_LANG = _pj.get("language", os.environ.get("TITAN_LANG", "en-US,en"))

# Screen resolution (must match WebGL/Facebook wd cookie/xulstore)
SCREEN_W = int(_pj.get("screen_w", os.environ.get("TITAN_SCREEN_W", "1920")))
SCREEN_H = int(_pj.get("screen_h", os.environ.get("TITAN_SCREEN_H", "1080")))

# Derive fingerprint seeds from profile UUID hash (not sequential)
_h = hashlib.sha512(PROFILE_UUID.encode()).hexdigest()
CANVAS_SEED = int(_h[:10], 16)
AUDIO_SEED = int(_h[10:20], 16)
WEBGL_SEED = int(_h[20:30], 16)

def leave_wal_ghosts(db_path):
    """Create empty -wal and -shm files alongside a SQLite database.
    
    Real Firefox uses journal_mode=WAL, which creates *-wal and *-shm
    sidecar files.  After a clean shutdown SQLite checkpoints the WAL
    and truncates (but does NOT delete) these files.  Their **complete
    absence** is an instant synthetic-profile detection vector because
    no real Firefox profile has ever existed without them.
    
    Call this AFTER conn.close() for every .sqlite file we produce.
    """
    import os as _os
    db_str = str(db_path)
    wal = db_str + "-wal"
    shm = db_str + "-shm"
    # Create as empty files (post-checkpoint state) if they don't exist
    if not _os.path.exists(wal):
        open(wal, 'wb').close()
    if not _os.path.exists(shm):
        # SHM is typically 32KB even when empty (memory-mapped region header)
        with open(shm, 'wb') as f:
            f.write(b'\x00' * 32768)


def stagger_mtime(file_path, days_ago, jitter_hours=6):
    """Set file modification time to look organically aged.
    
    If every file in a profile has mtime within the same second (when
    profgen ran), that is an **instant forensic flag**.  Real profiles
    have mtimes spread across weeks/months because Firefox touches each
    database at different points in the profile's lifetime.
    
    Args:
        file_path: Path to the file.
        days_ago:  Approximate age in days (0 = recent).
        jitter_hours: Random jitter window.
    """
    import os as _os
    target = NOW - timedelta(days=days_ago,
                             hours=random.randint(0, jitter_hours),
                             minutes=random.randint(0, 59),
                             seconds=random.randint(0, 59))
    ts = target.timestamp()
    _os.utime(str(file_path), (ts, ts))
    # Also stagger WAL/SHM if present (they should be slightly newer)
    for suffix in ["-wal", "-shm"]:
        sidecar = str(file_path) + suffix
        if _os.path.exists(sidecar):
            ts2 = ts + random.randint(60, 7200)  # 1 min – 2 hours newer
            _os.utime(sidecar, (ts2, ts2))


def inject_freelist_pages(db_path, num_pages=None):
    """Add empty freelist pages to a SQLite database to simulate fragmentation.
    
    A freshly-created SQLite file has freelist_count=0.  Real Firefox
    databases accumulate free pages from DELETE/UPDATE operations over
    weeks of use.  Zero fragmentation across ALL databases is a strong
    synthetic signal.
    
    This works by creating a temp table, inserting junk rows to force
    page allocation, then dropping the table — leaving freed pages on
    the freelist exactly like real-world churn.
    """
    if num_pages is None:
        num_pages = random.randint(2, 12)
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    c.execute("CREATE TABLE _frag_tmp(d BLOB)")
    # Each row ~32KB pushes SQLite to allocate new pages
    for _ in range(num_pages):
        c.execute("INSERT INTO _frag_tmp VALUES(?)", (os.urandom(30000),))
    conn.commit()
    c.execute("DROP TABLE _frag_tmp")
    conn.commit()
    # Run incremental vacuum to move some (not all) pages to freelist
    c.execute("PRAGMA incremental_vacuum(1)")
    conn.commit()
    conn.close()


TRUST_DOMAINS = ["google.com","gmail.com","youtube.com","github.com",
    "linkedin.com","facebook.com","twitter.com","reddit.com"]
COMMERCE_DOMAINS = ["amazon.com","newegg.com","bestbuy.com",
    "steampowered.com","ubereats.com","eneba.com","g2a.com"]
ALL_DOMAINS = TRUST_DOMAINS + COMMERCE_DOMAINS

# Visit type constants (Firefox)
TRANSITION_LINK = 1
TRANSITION_TYPED = 2
TRANSITION_BOOKMARK = 3
TRANSITION_EMBED = 4
TRANSITION_REDIRECT_PERMANENT = 5
TRANSITION_REDIRECT_TEMPORARY = 6
TRANSITION_DOWNLOAD = 7
TRANSITION_FRAMED_LINK = 8

# Realistic subpages per domain
SUBPAGES = {
    "google.com": ["/search?q=python+tutorials","/search?q=gaming+gift+cards",
        "/search?q=weather","/search?q=crypto+news","/maps","/translate",
        "/search?q=best+laptop+2025","/search?q=sri+lanka+news","/search?q=firefox+extensions"],
    "gmail.com": ["/mail/u/0/#inbox","/mail/u/0/#sent","/mail/u/0/#drafts"],
    "youtube.com": ["/watch?v=dQw4w9WgXcQ","/feed/subscriptions",
        "/results?search_query=coding+tutorial","/shorts","/feed/trending",
        "/watch?v=J---aiyznGQ","/watch?v=LXb3EKWsInQ","/playlist?list=WL"],
    "github.com": ["/trending","/notifications","/settings",
        "/explore","/pulls","/issues","/torvalds/linux","/microsoft/vscode"],
    "linkedin.com": ["/feed","/messaging","/jobs","/mynetwork"],
    "facebook.com": ["/marketplace","/groups","/gaming","/friends","/events"],
    "twitter.com": ["/home","/explore","/notifications","/messages","/settings","/i/bookmarks"],
    "reddit.com": ["/r/gaming","/r/pcmasterrace","/r/Steam",
        "/r/GameDeals","/r/programming","/r/technology","/r/webdev","/r/learnpython"],
    "amazon.com": ["/gp/cart","/gp/buy","/dp/B0BSHF7WHW",
        "/gp/yourstore","/gp/history","/dp/B09V3KXJPB","/gp/css/order-history"],
    "newegg.com": ["/Gaming/Store","/Components/Store","/p/N82E16814126595",
        "/Laptops-Notebooks/SubCategory/ID-32","/p/N82E16835181103"],
    "bestbuy.com": ["/site/electronics/pcmcat702600702702.c",
        "/site/gaming-pcs/pcmcat159700050004.c","/site/laptops/pcmcat138500050001.c",
        "/site/computer-accessories/pcmcat112500050037.c"],
    "steampowered.com": ["/app/1245620","/app/730","/explore",
        "/wishlist","/checkout","/app/570","/app/440","/search/?term=rpg"],
    "ubereats.com": ["/feed","/orders","/checkout","/store/mcdonalds","/store/subway"],
    "eneba.com": ["/store","/store/crypto-gift-cards","/cart",
        "/store/game-keys","/checkout","/user/orders","/store/playstation-network",
        "/store/xbox-gift-cards","/store/nintendo-eshop"],
    "g2a.com": ["/category/gaming-c189","/cart","/user/inventory",
        "/category/gift-cards-c193","/category/software-c186"],
}

# Narrative phases (domain, path, days_ago, visit_count)
PHASES = {
    "discovery": [
        ("overleaf.com","/templates",95,12),("spotify.com","/student",92,3),
        ("arxiv.org","/list/cs.CV",85,25),("stackoverflow.com","/questions",75,30),
        ("coursera.org","/learn",78,15),("newegg.com","/cart",70,5),
        ("chegg.com","/study",82,8),
    ],
    "development": [
        ("github.com","/user/repos",46,40),("aws.amazon.com","/console",65,8),
        ("leetcode.com","/problems",42,20),("hackerrank.com","/dashboard",38,10),
        ("ubereats.com","/checkout",53,3),("doordash.com","/orders",48,5),
        ("digitalocean.com","/billing",58,4),
    ],
    "seasoned": [
        ("steampowered.com","/app/1245620",32,5),("linkedin.com","/premium",25,8),
        ("amazon.com","/prime",6,3),("eneba.com","/store",4,8),
        ("eneba.com","/cart",2,3),("eneba.com","/checkout",1,2),
        ("bestbuy.com","/site/electronics",15,4),
    ],
}

# Base64url alphabet used by Firefox for GUIDs
_GUID_ALPHA = string.ascii_letters + string.digits + '_-'

def fx_guid():
    """Generate a Firefox-style 12-character GUID (base64url alphabet)"""
    return ''.join(random.choices(_GUID_ALPHA, k=12))

def fx_url_hash(url):
    """Compute a URL hash matching Firefox's moz_places url_hash.
    Firefox uses prefix_hash << 32 + host_hash via mozilla::HashString.
    We approximate with a stable 48-bit hash."""
    h = hashlib.md5(url.encode()).digest()
    return struct.unpack('<q', h[:8])[0] & 0x0000FFFFFFFFFFFF

def fx_frecency(visit_count, last_visit_date, now_us):
    """Estimate a Firefox-like frecency score.
    Real Firefox weighs by visit type, recency buckets, and bonuses.
    This approximation produces realistic-looking values."""
    if visit_count == 0 or last_visit_date == 0:
        return -1
    days_since = max((now_us - last_visit_date) / 1e6 / 86400, 0.1)
    # Recency bucket weight (Firefox uses 100/70/50/30/10)
    if days_since <= 4:
        bucket_w = 100
    elif days_since <= 14:
        bucket_w = 70
    elif days_since <= 31:
        bucket_w = 50
    elif days_since <= 90:
        bucket_w = 30
    else:
        bucket_w = 10
    # visit_type bonus (typed=2000, bookmark=75, link=100, default=0)
    type_bonus = random.choice([100, 100, 100, 2000, 75])
    raw = visit_count * max(type_bonus * bucket_w / 100, 1)
    # Add slight noise to avoid uniform values
    return max(int(raw * random.uniform(0.85, 1.15)), 1)

def circ_hour():
    """Circadian-weighted visit hour"""
    w=[.01,.005,.005,.005,.005,.01,.03,.05,.06,.08,.09,.08,
       .07,.08,.09,.07,.06,.06,.07,.08,.09,.08,.06,.03]
    return random.choices(range(24), weights=w, k=1)[0]

def rand_subpage(domain):
    """Pick a random realistic subpage for a domain (biased away from root)"""
    pages = SUBPAGES.get(domain)
    if not pages:
        # Generic subpages for unlisted domains
        generic = ["/about","/contact","/help","/faq","/terms","/privacy",
                   "/login","/account","/search","/blog"]
        return random.choice(generic)
    return random.choice(pages)

def rand_visit_type():
    """Weighted random visit type like a real user"""
    types = [TRANSITION_LINK]*60 + [TRANSITION_TYPED]*20 + \
            [TRANSITION_BOOKMARK]*10 + [TRANSITION_REDIRECT_TEMPORARY]*8 + \
            [TRANSITION_FRAMED_LINK]*2
    return random.choice(types)

def spread_time(days_ago, jitter_hours=3):
    """Create a visit time with organic jitter, clamped to avoid deep night"""
    h = circ_hour()
    base = NOW - timedelta(days=days_ago)
    jitter = random.randint(-jitter_hours*60, jitter_hours*60)
    base = base.replace(hour=h, minute=random.randint(0,59),
                        second=random.randint(0,59),
                        microsecond=random.randint(0,999999))
    result = base + timedelta(minutes=jitter)
    # Clamp: if jitter pushed into deep night (0-4am), shift to morning
    if result.hour < 5 and h >= 5:
        result = result.replace(hour=random.randint(6, 9))
    return result

def pareto_visits(domains, age, n=2000):
    """Pareto-distributed visits across domains"""
    nd = len(domains)
    a = 1.5
    wt = [1/((i+1)**a) for i in range(nd)]
    s = sum(wt)
    wt = [x/s for x in wt]
    sh = list(domains)
    random.shuffle(sh)
    out = []
    for _ in range(n):
        d = random.choices(sh, weights=wt, k=1)[0]
        day = min(int(random.expovariate(3/max(age,1))), age-1)
        out.append((d, max(0, day), random.randint(1,5)))
    return out

def title_for(domain, path="/"):
    """Realistic page title"""
    t = {"google.com":"Google","youtube.com":"YouTube","github.com":"GitHub",
         "amazon.com":"Amazon.com: Online Shopping","eneba.com":"Eneba - Cheap Game Keys & Gift Cards",
         "reddit.com":"Reddit - Dive into anything","steampowered.com":"Steam Store",
         "linkedin.com":"LinkedIn: Log In or Sign Up","facebook.com":"Facebook",
         "twitter.com":"X","gmail.com":"Gmail - Inbox","g2a.com":"G2A.COM - Game Keys",
         "newegg.com":"Newegg - Computer Parts & Electronics",
         "bestbuy.com":"Best Buy: Expert Service. Unbeatable Price.",
         "ubereats.com":"Uber Eats - Food Delivery","spotify.com":"Spotify - Web Player",
         "overleaf.com":"Overleaf - LaTeX Editor","arxiv.org":"arXiv.org e-Print archive",
         "stackoverflow.com":"Stack Overflow","coursera.org":"Coursera - Online Courses",
         "leetcode.com":"LeetCode - Coding Challenges","hackerrank.com":"HackerRank",
         "chegg.com":"Chegg Study","digitalocean.com":"DigitalOcean",
         "doordash.com":"DoorDash - Food Delivery","aws.amazon.com":"AWS Management Console"}
    base = t.get(domain, domain.split('.')[0].title())
    if path and path != "/":
        seg = path.strip("/").split("/")[-1].replace("-"," ").replace("_"," ")
        if "?" in seg:
            seg = seg.split("?")[0]
        if seg and len(seg) > 1:
            base += f" - {seg.title()}"
    return base

def stripe_mid():
    """Generate a Stripe __stripe_mid cookie in dot-separated format.
    
    Format: {prefix}.{timestamp}.{suffix}
    This matches real Stripe __stripe_mid format with:
      - Random prefix (16 hex chars)
      - Unix timestamp in middle
      - Random suffix (16 hex chars)
    """
    import time
    
    prefix = secrets.token_hex(8)  # 16 hex chars = 8 bytes
    timestamp = int(time.time())
    suffix = secrets.token_hex(8)  # 16 hex chars = 8 bytes
    return f"{prefix}.{timestamp}.{suffix}"
