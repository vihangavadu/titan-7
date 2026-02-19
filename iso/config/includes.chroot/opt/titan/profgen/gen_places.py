"""Generate forensically clean places.sqlite with full schema"""
import sqlite3, secrets, random
from datetime import timedelta
from .config import *

def generate(profile_path):
    print("[1/12] places.sqlite (history + bookmarks + downloads)...")
    db = profile_path / "places.sqlite"
    conn = firefox_sqlite_connect(db)
    c = conn.cursor()

    # Full Firefox schema
    c.executescript("""
        CREATE TABLE moz_places (
            id INTEGER PRIMARY KEY, url TEXT, title TEXT, rev_host TEXT,
            visit_count INTEGER DEFAULT 0, hidden INTEGER DEFAULT 0,
            typed INTEGER DEFAULT 0, frecency INTEGER DEFAULT -1,
            last_visit_date INTEGER, guid TEXT, foreign_count INTEGER DEFAULT 0,
            url_hash INTEGER DEFAULT 0, description TEXT,
            preview_image_url TEXT, origin_id INTEGER,
            site_name TEXT
        );
        CREATE TABLE moz_historyvisits (
            id INTEGER PRIMARY KEY, from_visit INTEGER DEFAULT 0,
            place_id INTEGER, visit_date INTEGER,
            visit_type INTEGER DEFAULT 1, session INTEGER DEFAULT 0,
            FOREIGN KEY(place_id) REFERENCES moz_places(id)
        );
        CREATE TABLE moz_origins (
            id INTEGER PRIMARY KEY, prefix TEXT NOT NULL,
            host TEXT NOT NULL, frecency INTEGER NOT NULL,
            recalc_frecency INTEGER NOT NULL DEFAULT 0,
            alt_frecency INTEGER,
            recalc_alt_frecency INTEGER NOT NULL DEFAULT 0,
            UNIQUE (prefix, host)
        );
        CREATE TABLE moz_bookmarks (
            id INTEGER PRIMARY KEY, type INTEGER, fk INTEGER,
            parent INTEGER, position INTEGER, title TEXT,
            keyword_id INTEGER, folder_type TEXT,
            dateAdded INTEGER, lastModified INTEGER, guid TEXT,
            syncStatus INTEGER NOT NULL DEFAULT 0,
            syncChangeCounter INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE moz_bookmarks_deleted (
            guid TEXT PRIMARY KEY, dateRemoved INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE moz_keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT, keyword TEXT UNIQUE,
            place_id INTEGER
        );
        CREATE TABLE moz_anno_attributes (
            id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL
        );
        CREATE TABLE moz_annos (
            id INTEGER PRIMARY KEY, place_id INTEGER NOT NULL,
            anno_attribute_id INTEGER, content TEXT,
            flags INTEGER DEFAULT 0, expiration INTEGER DEFAULT 0,
            type INTEGER DEFAULT 0, dateAdded INTEGER DEFAULT 0,
            lastModified INTEGER DEFAULT 0
        );
        CREATE TABLE moz_items_annos (
            id INTEGER PRIMARY KEY, item_id INTEGER NOT NULL,
            anno_attribute_id INTEGER, content TEXT,
            flags INTEGER DEFAULT 0, expiration INTEGER DEFAULT 0,
            type INTEGER DEFAULT 0, dateAdded INTEGER DEFAULT 0,
            lastModified INTEGER DEFAULT 0
        );
        CREATE TABLE moz_inputhistory (
            place_id INTEGER NOT NULL, input TEXT NOT NULL,
            use_count INTEGER, PRIMARY KEY (place_id, input)
        );
        CREATE TABLE moz_meta (key TEXT PRIMARY KEY, value NOT NULL);

        CREATE INDEX moz_places_url_hashindex ON moz_places(url_hash);
        CREATE INDEX moz_places_hostindex ON moz_places(rev_host);
        CREATE INDEX moz_places_frecencyindex ON moz_places(frecency);
        CREATE INDEX moz_places_lastvisitdateindex ON moz_places(last_visit_date);
        CREATE INDEX moz_historyvisits_placedateindex ON moz_historyvisits(place_id, visit_date);
        CREATE INDEX moz_historyvisits_dateindex ON moz_historyvisits(visit_date);
        CREATE INDEX moz_bookmarks_itemindex ON moz_bookmarks(fk, type);
        CREATE INDEX moz_bookmarks_parentindex ON moz_bookmarks(parent, position);
        CREATE INDEX moz_bookmarks_itemlastmodifiedindex ON moz_bookmarks(fk, lastModified);
    """)

    # ── Origins ──
    origin_map = {}
    for i, dom in enumerate(ALL_DOMAINS):
        c.execute("INSERT INTO moz_origins(prefix,host,frecency) VALUES(?,?,?)",
            ("https://", f"www.{dom}", random.randint(500, 8000)))
        origin_map[dom] = c.lastrowid

    # ── URL deduplication: track place_id per URL (real Firefox reuses places) ──
    place_map = {}  # url -> {place_id, visit_count, last_visit_date, typed}
    now_us = int(NOW.timestamp() * 1e6)

    def get_or_create_place(url, title, dom, visit_date_us, is_typed, origin_id=None):
        """Get existing place_id for URL or create new one. Tracks visit_count & last_visit_date."""
        if url in place_map:
            pm = place_map[url]
            pm['visit_count'] += 1
            if visit_date_us > pm['last_visit_date']:
                pm['last_visit_date'] = visit_date_us
            if is_typed:
                pm['typed'] = 1
            return pm['place_id']
        rev = ".".join(reversed(dom.split("."))) + "."
        oid = origin_id or origin_map.get(dom)
        c.execute("""INSERT INTO moz_places(url,title,rev_host,visit_count,typed,
            last_visit_date,guid,url_hash,origin_id,hidden) VALUES(?,?,?,1,?,?,?,?,?,0)""",
            (url, title, rev, 1 if is_typed else 0, visit_date_us,
             fx_guid(), fx_url_hash(url), oid))
        pid = c.lastrowid
        place_map[url] = {
            'place_id': pid, 'visit_count': 1,
            'last_visit_date': visit_date_us, 'typed': 1 if is_typed else 0
        }
        return pid

    # ── Bookmark folders (Firefox default structure) ──
    bk_time = int(CREATED.timestamp() * 1e6)
    bk_mod = int(NOW.timestamp() * 1e6)
    # Root
    c.execute("INSERT INTO moz_bookmarks(id,type,parent,position,title,dateAdded,lastModified,guid) VALUES(1,2,0,0,'',?,?,?)",
        (bk_time, bk_mod, "root________"))
    # Menu
    c.execute("INSERT INTO moz_bookmarks(id,type,parent,position,title,dateAdded,lastModified,guid) VALUES(2,2,1,0,'Bookmarks Menu',?,?,?)",
        (bk_time, bk_mod, "menu________"))
    # Toolbar
    c.execute("INSERT INTO moz_bookmarks(id,type,parent,position,title,dateAdded,lastModified,guid) VALUES(3,2,1,1,'Bookmarks Toolbar',?,?,?)",
        (bk_time, bk_mod, "toolbar_____"))
    # Unfiled
    c.execute("INSERT INTO moz_bookmarks(id,type,parent,position,title,dateAdded,lastModified,guid) VALUES(4,2,1,2,'Other Bookmarks',?,?,?)",
        (bk_time, bk_mod, "unfiled_____"))
    # Mobile
    c.execute("INSERT INTO moz_bookmarks(id,type,parent,position,title,dateAdded,lastModified,guid) VALUES(5,2,1,3,'Mobile Bookmarks',?,?,?)",
        (bk_time, bk_mod, "mobile______"))

    # Toolbar bookmarks (realistic set)
    toolbar_bks = [
        ("YouTube","https://www.youtube.com/",12),
        ("GitHub","https://github.com/",20),
        ("Reddit","https://www.reddit.com/",35),
        ("Gmail","https://mail.google.com/",5),
        ("Steam","https://store.steampowered.com/",40),
        ("Eneba","https://www.eneba.com/",55),
        ("Amazon","https://www.amazon.com/",60),
    ]
    for pos, (title, url, days_ago) in enumerate(toolbar_bks):
        dom = url.split("//")[1].split("/")[0].replace("www.","").replace("store.","").replace("mail.","")
        added = int((NOW - timedelta(days=days_ago)).timestamp() * 1e6)
        pid = get_or_create_place(url, title, dom, added, True, origin_map.get(dom))
        c.execute("UPDATE moz_places SET foreign_count = foreign_count + 1 WHERE id = ?", (pid,))
        c.execute("INSERT INTO moz_bookmarks(type,fk,parent,position,title,dateAdded,lastModified,guid) VALUES(1,?,3,?,?,?,?,?)",
            (pid, pos, title, added, bk_mod, fx_guid()))

    # Other bookmarks (unfiled folder)
    unfiled_bks = [
        ("LeetCode","https://leetcode.com/",30),
        ("Coursera","https://www.coursera.org/",70),
        ("Stack Overflow","https://stackoverflow.com/",65),
    ]
    for pos, (title, url, days_ago) in enumerate(unfiled_bks):
        dom = url.split("//")[1].split("/")[0].replace("www.","")
        added = int((NOW - timedelta(days=days_ago)).timestamp() * 1e6)
        pid = get_or_create_place(url, title, dom, added, True)
        c.execute("UPDATE moz_places SET foreign_count = foreign_count + 1 WHERE id = ?", (pid,))
        c.execute("INSERT INTO moz_bookmarks(type,fk,parent,position,title,dateAdded,lastModified,guid) VALUES(1,?,4,?,?,?,?,?)",
            (pid, pos, title, added, bk_mod, fx_guid()))

    # ── Session IDs (realistic: ~2-5 sessions per day) ──
    session_id = 1
    session_map = {}  # day -> session_id
    for day in range(AGE_DAYS):
        sessions_today = random.randint(1, 4)
        session_map[day] = [session_id + i for i in range(sessions_today)]
        session_id += sessions_today

    # Track last visit_id per session for from_visit referral chains
    session_last_visit = {}
    n = 0

    def add_visit(url, title, dom, days_ago_approx, vtype=None, origin_id=None):
        """Add a visit with proper from_visit chain and URL dedup."""
        nonlocal n
        vt = spread_time(days_ago_approx)
        day_key = min(max(int((NOW - vt).days), 0), AGE_DAYS - 1)
        sess = random.choice(session_map.get(day_key, [1]))
        if vtype is None:
            vtype = rand_visit_type()
        is_typed = (vtype == TRANSITION_TYPED)
        visit_date_us = int(vt.timestamp() * 1e6)
        pid = get_or_create_place(url, title, dom, visit_date_us, is_typed, origin_id)
        # from_visit: link clicks reference previous visit in same session
        from_v = 0
        if vtype == TRANSITION_LINK and sess in session_last_visit:
            from_v = session_last_visit[sess]
        c.execute("""INSERT INTO moz_historyvisits(from_visit,place_id,visit_date,
            visit_type,session) VALUES(?,?,?,?,?)""",
            (from_v, pid, visit_date_us, vtype, sess))
        vid = c.lastrowid
        session_last_visit[sess] = vid
        n += 1
        return vid

    # ── Narrative phase history ──
    for phase, events in PHASES.items():
        for dom, path, days_ago, vc in events:
            for i in range(vc):
                url = f"https://www.{dom}{path}"
                add_visit(url, title_for(dom, path), dom,
                          days_ago + random.randint(-2, 2),
                          origin_id=origin_map.get(dom))

    # ── Pareto filler (with subpages, not just root) ──
    for dom, day_off, vc in pareto_visits(ALL_DOMAINS, AGE_DAYS, 2000):
        subpage = rand_subpage(dom)
        url = f"https://www.{dom}{subpage}"
        add_visit(url, title_for(dom, subpage), dom, day_off,
                  origin_id=origin_map.get(dom))

    # ── Trust domain recurring visits (every 2-4 days, with skip days) ──
    for dom in TRUST_DOMAINS:
        day = 0
        while day < AGE_DAYS:
            # Skip some days organically
            if random.random() < 0.15:
                day += random.randint(1, 3)
                continue
            subpage = rand_subpage(dom)
            url = f"https://www.{dom}{subpage}"
            add_visit(url, title_for(dom, subpage), dom, day,
                      origin_id=origin_map.get(dom))
            day += random.randint(2, 4)

    # ── Redirect chains (real browsers always have these) ──
    # V7.0.3 PATCH: Real browsing generates HTTP 301/302 redirect entries.
    # Firefox records the redirect source as hidden=1, visit_type=5 or 6,
    # and chains it via from_visit to the final destination.
    # Having ZERO redirect entries is a strong synthetic detection vector
    # because every real user hits redirects (http→https, short URLs, etc.)
    redirect_chains = [
        # (source_url, dest_url, dest_title, domain, days_ago)
        ("http://google.com/", "https://www.google.com/", "Google", "google.com", random.randint(5, AGE_DAYS)),
        ("http://github.com/", "https://github.com/", "GitHub", "github.com", random.randint(10, AGE_DAYS)),
        ("http://reddit.com/", "https://www.reddit.com/", "Reddit", "reddit.com", random.randint(8, AGE_DAYS)),
        ("http://youtube.com/", "https://www.youtube.com/", "YouTube", "youtube.com", random.randint(3, AGE_DAYS)),
        ("http://amazon.com/", "https://www.amazon.com/", "Amazon", "amazon.com", random.randint(15, AGE_DAYS)),
        ("https://youtu.be/dQw4w9WgXcQ", "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "YouTube", "youtube.com", random.randint(10, 50)),
        ("https://bit.ly/3xK9mT2", "https://www.eneba.com/store", "Eneba", "eneba.com", random.randint(5, 30)),
        ("http://www.linkedin.com/in/someone", "https://www.linkedin.com/in/someone", "LinkedIn", "linkedin.com", random.randint(20, AGE_DAYS)),
        ("https://t.co/abc123", "https://www.reddit.com/r/gaming", "Reddit - Gaming", "reddit.com", random.randint(5, 40)),
        ("http://steampowered.com/", "https://store.steampowered.com/", "Steam Store", "steampowered.com", random.randint(10, AGE_DAYS)),
    ]
    for src_url, dest_url, dest_title, dom, days_ago in redirect_chains:
        vt = spread_time(days_ago)
        visit_date_us = int(vt.timestamp() * 1e6)
        day_key = min(max(int((NOW - vt).days), 0), AGE_DAYS - 1)
        sess = random.choice(session_map.get(day_key, [1]))
        # Source URL: hidden=1 (Firefox hides redirect sources from history UI)
        src_rev = "." if "://" not in src_url.split("//")[1].split("/")[0] else ".".join(reversed(src_url.split("//")[1].split("/")[0].split("."))) + "."
        c.execute("""INSERT INTO moz_places(url,title,rev_host,visit_count,typed,
            last_visit_date,guid,url_hash,hidden) VALUES(?,?,?,1,1,?,?,?,1)""",
            (src_url, "", src_rev, visit_date_us, fx_guid(), fx_url_hash(src_url)))
        src_pid = c.lastrowid
        # Redirect visit (type 5=permanent or 6=temporary)
        redir_type = random.choice([TRANSITION_REDIRECT_PERMANENT, TRANSITION_REDIRECT_TEMPORARY])
        c.execute("""INSERT INTO moz_historyvisits(from_visit,place_id,visit_date,visit_type,session)
            VALUES(0,?,?,?,?)""", (src_pid, visit_date_us, redir_type, sess))
        src_vid = c.lastrowid
        # Destination visit chained from the redirect
        dest_pid = get_or_create_place(dest_url, dest_title, dom, visit_date_us + random.randint(100000, 500000), False, origin_map.get(dom))
        c.execute("""INSERT INTO moz_historyvisits(from_visit,place_id,visit_date,visit_type,session)
            VALUES(?,?,?,1,?)""", (src_vid, dest_pid, visit_date_us + random.randint(100000, 500000), sess))
        session_last_visit[sess] = c.lastrowid
        n += 2

    # ── Non-www and mixed-scheme URLs (real browsers have varied URL formats) ──
    # Having 100% https://www.* URLs is a synthetic detection vector
    nowww_urls = [
        ("https://github.com/trending", "Trending - GitHub", "github.com", random.randint(5, 60)),
        ("https://github.com/notifications", "Notifications - GitHub", "github.com", random.randint(1, 30)),
        ("https://stackoverflow.com/questions", "Stack Overflow", "stackoverflow.com", random.randint(10, 70)),
        ("https://leetcode.com/problems", "LeetCode", "leetcode.com", random.randint(15, 50)),
        ("https://discord.com/channels/@me", "Discord", "discord.com", random.randint(5, 40)),
        ("https://mail.google.com/mail/u/0/#inbox", "Gmail - Inbox", "google.com", random.randint(1, 80)),
        ("https://docs.google.com/document/d/1abc", "Google Docs", "google.com", random.randint(10, 50)),
        ("https://store.steampowered.com/app/730", "Steam - CS2", "steampowered.com", random.randint(5, 30)),
        ("http://localhost:3000/", "localhost", "localhost", random.randint(20, 60)),
        ("http://192.168.1.1/", "Router Admin", "192.168.1.1", random.randint(40, 80)),
    ]
    for url, title, dom, days_ago in nowww_urls:
        rev = ".".join(reversed(dom.split("."))) + "." if "." in dom else dom + "."
        visit_date_us = int(spread_time(days_ago).timestamp() * 1e6)
        c.execute("""INSERT INTO moz_places(url,title,rev_host,visit_count,typed,
            last_visit_date,guid,url_hash,hidden) VALUES(?,?,?,?,?,?,?,?,0)""",
            (url, title, rev, random.randint(1, 15), random.choice([0, 0, 1]),
             visit_date_us, fx_guid(), fx_url_hash(url)))
        pid = c.lastrowid
        for _ in range(random.randint(1, 5)):
            vt = spread_time(random.randint(0, days_ago))
            sess = random.choice(session_map.get(random.randint(0, AGE_DAYS-1), [1]))
            c.execute("""INSERT INTO moz_historyvisits(place_id,visit_date,visit_type,session)
                VALUES(?,?,?,?)""", (pid, int(vt.timestamp()*1e6), random.choice([1, 2]), sess))
            n += 1

    # ── about:* pages (real browsers always have these) ──
    about_pages = [
        ("about:home", "Firefox Home", AGE_DAYS),
        ("about:blank", "", AGE_DAYS - 1),
        ("about:newtab", "New Tab", AGE_DAYS - 2),
        ("about:preferences", "Settings", random.randint(30, AGE_DAYS)),
        ("about:addons", "Add-ons Manager", random.randint(40, AGE_DAYS)),
    ]
    for url, title, days_ago in about_pages:
        rev = "."
        c.execute("""INSERT INTO moz_places(url,title,rev_host,visit_count,typed,
            last_visit_date,guid,url_hash,hidden) VALUES(?,?,?,?,1,?,?,?,0)""",
            (url, title, rev, random.randint(5, 50),
             int((NOW - timedelta(days=random.randint(0, 3))).timestamp() * 1e6),
             fx_guid(), fx_url_hash(url)))
        pid = c.lastrowid
        # Add multiple visits spread across profile age
        for _ in range(random.randint(3, 15)):
            vt = spread_time(random.randint(0, days_ago))
            c.execute("""INSERT INTO moz_historyvisits(place_id,visit_date,visit_type,session)
                VALUES(?,?,?,?)""", (pid, int(vt.timestamp()*1e6), TRANSITION_TYPED,
                random.choice(session_map.get(random.randint(0, AGE_DAYS-1), [1]))))
            n += 1

    # ── Download history (moz_annos) ──
    downloads = [
        ("https://github.com/torvalds/linux/archive/refs/heads/master.zip","linux-master.zip",60),
        ("https://nodejs.org/dist/v20.11.0/node-v20.11.0-win-x64.zip","node-v20.11.0-win-x64.zip",45),
        ("https://code.visualstudio.com/sha/download?build=stable&os=win32-x64-user","VSCodeUserSetup-x64-1.85.1.exe",80),
        ("https://dl.discordapp.net/distro/app/stable/win/x86/1.0.9032/DiscordSetup.exe","DiscordSetup.exe",55),
    ]
    # Create download annotation attribute
    c.execute("INSERT INTO moz_anno_attributes(name) VALUES('downloads/destinationFileURI')")
    dl_attr = c.lastrowid
    c.execute("INSERT INTO moz_anno_attributes(name) VALUES('downloads/metaData')")
    meta_attr = c.lastrowid

    for url, fname, days_ago in downloads:
        vt = spread_time(days_ago)
        visit_date_us = int(vt.timestamp() * 1e6)
        after_proto = url.split("://", 1)[1] if "://" in url else url
        dl_host = after_proto.split("/")[0]
        rev = ".".join(reversed(dl_host.split("."))) + "."
        c.execute("""INSERT INTO moz_places(url,title,rev_host,visit_count,typed,
            last_visit_date,guid,url_hash,hidden) VALUES(?,?,?,1,0,?,?,?,1)""",
            (url, fname, rev, visit_date_us, fx_guid(), fx_url_hash(url)))
        pid = c.lastrowid
        c.execute("""INSERT INTO moz_historyvisits(place_id,visit_date,visit_type,session)
            VALUES(?,?,?,?)""", (pid, visit_date_us, TRANSITION_DOWNLOAD, 1))
        c.execute("""INSERT INTO moz_annos(place_id,anno_attribute_id,content,dateAdded,lastModified)
            VALUES(?,?,?,?,?)""",
            (pid, dl_attr, f"file:///C:/Users/{PERSONA_FIRST}/Downloads/{fname}",
             visit_date_us, visit_date_us))
        n += 1

    # ── Input history (URL bar autocomplete) ──
    input_entries = [("gith",3),("yout",8),("red",5),("eneb",4),("amaz",6),
                     ("stea",3),("goog",10),("link",2),("g2a",2)]
    # Get some place IDs for common domains
    for inp, use_count in input_entries:
        c.execute("SELECT id FROM moz_places WHERE url LIKE ? LIMIT 1",
            (f"%{inp}%",))
        row = c.fetchone()
        if row:
            c.execute("INSERT OR IGNORE INTO moz_inputhistory(place_id,input,use_count) VALUES(?,?,?)",
                (row[0], inp, use_count))

    # ── Post-processing: update visit_count, last_visit_date, frecency for deduped places ──
    for url, pm in place_map.items():
        frec = fx_frecency(pm['visit_count'], pm['last_visit_date'], now_us)
        c.execute("""UPDATE moz_places SET visit_count=?, last_visit_date=?,
            frecency=?, typed=? WHERE id=?""",
            (pm['visit_count'], pm['last_visit_date'], frec, pm['typed'], pm['place_id']))

    # ── Update origin frecency from actual place data ──
    c.execute("""UPDATE moz_origins SET frecency = (
        SELECT COALESCE(SUM(frecency), 0) FROM moz_places
        WHERE moz_places.origin_id = moz_origins.id AND frecency > 0)""")

    # ── Compute moz_meta from real data (not hardcoded) ──
    c.execute("SELECT COUNT(*) FROM moz_origins WHERE frecency > 0")
    ofc = c.fetchone()[0]
    c.execute("SELECT COALESCE(SUM(frecency),0) FROM moz_origins WHERE frecency > 0")
    ofs = c.fetchone()[0]
    c.execute("SELECT COALESCE(SUM(frecency*frecency),0) FROM moz_origins WHERE frecency > 0")
    ofss = c.fetchone()[0]
    c.execute("INSERT INTO moz_meta VALUES('origin_frecency_count',?)", (ofc,))
    c.execute("INSERT INTO moz_meta VALUES('origin_frecency_sum',?)", (ofs,))
    c.execute("INSERT INTO moz_meta VALUES('origin_frecency_sum_of_squares',?)", (ofss,))

    # ── V7.0.3 PATCH: moz_places_metadata table ──
    # Firefox 118+ creates this table for Places metadata (visit types, etc.)
    # Missing table = forensic detection vector on newer Firefox builds.
    c.executescript("""
        CREATE TABLE IF NOT EXISTS moz_places_metadata (
            id INTEGER PRIMARY KEY,
            place_id INTEGER NOT NULL,
            referrer_place_id INTEGER,
            created_at INTEGER NOT NULL DEFAULT 0,
            updated_at INTEGER NOT NULL DEFAULT 0,
            total_view_time INTEGER NOT NULL DEFAULT 0,
            typing_time INTEGER NOT NULL DEFAULT 0,
            key_presses INTEGER NOT NULL DEFAULT 0,
            scrolling_time INTEGER NOT NULL DEFAULT 0,
            scrolling_distance INTEGER NOT NULL DEFAULT 0,
            document_type INTEGER NOT NULL DEFAULT 0,
            search_query_id INTEGER,
            FOREIGN KEY(place_id) REFERENCES moz_places(id)
        );
        CREATE TABLE IF NOT EXISTS moz_places_metadata_search_queries (
            id INTEGER PRIMARY KEY,
            search_string TEXT NOT NULL UNIQUE
        );
        CREATE TABLE IF NOT EXISTS moz_previews_tombstones (
            hash TEXT PRIMARY KEY
        );
        CREATE INDEX IF NOT EXISTS moz_places_metadata_placecreated_idx
            ON moz_places_metadata(place_id, created_at);
    """)
    # Populate with realistic metadata for top places
    # V7.0.3 PATCH: Use heavy-tailed (log-normal) distributions instead of
    # uniform random.  Real user engagement follows a power-law: most pages
    # are glanced at for 5-15s, a few are read for 1-5 min, and rare pages
    # get 10+ min (e.g. long articles, videos).  Uniform random(5000,300000)
    # is a flat distribution that fraud detection ML models flag as synthetic.
    import math
    c.execute("SELECT id, last_visit_date FROM moz_places WHERE visit_count > 3 ORDER BY frecency DESC LIMIT 80")
    top_places = c.fetchall()
    for pid, lvd in top_places:
        created = lvd - random.randint(0, 86400 * 30) * 1000000 if lvd else now_us
        # Log-normal: median ~12s, 90th percentile ~90s, rare outliers 5+ min
        view_time = max(2000, int(math.exp(random.gauss(9.4, 1.2))))  # ms
        # Typing: most pages 0, some light typing, rare heavy input
        typing = int(max(0, math.exp(random.gauss(5, 2.5)) - 100)) if random.random() < 0.4 else 0
        # Key presses correlate with typing time
        keys = max(0, int(typing / random.uniform(50, 150))) if typing > 0 else 0
        # Scroll: heavy-tailed — quick pages no scroll, articles deep scroll
        scroll_time = int(max(0, math.exp(random.gauss(7.5, 2.0)) - 500)) if random.random() < 0.65 else 0
        scroll_dist = int(scroll_time * random.uniform(0.1, 0.5)) if scroll_time > 0 else 0
        c.execute("""INSERT OR IGNORE INTO moz_places_metadata
            (place_id, created_at, updated_at, total_view_time, typing_time,
             key_presses, scrolling_time, scrolling_distance, document_type)
            VALUES(?,?,?,?,?,?,?,?,?)""",
            (pid, created, lvd or now_us, view_time, typing, keys,
             scroll_time, scroll_dist, random.choice([0, 0, 0, 1])))

    conn.commit()
    conn.close()
    print(f"  -> {n} visits, {len(place_map)} unique places, {len(toolbar_bks)+len(unfiled_bks)} bookmarks, {len(downloads)} downloads")
    return n
