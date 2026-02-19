"""Generate diverse formhistory.sqlite — not just persona fields"""
import sqlite3, secrets, random
from datetime import timedelta
from .config import *

def generate(profile_path):
    print("[4/12] formhistory.sqlite (diverse form entries)...")
    db = profile_path / "formhistory.sqlite"
    conn = firefox_sqlite_connect(db)
    c = conn.cursor()

    c.executescript("""
        CREATE TABLE moz_formhistory (
            id INTEGER PRIMARY KEY, fieldname TEXT, value TEXT,
            timesUsed INTEGER, firstUsed INTEGER, lastUsed INTEGER, guid TEXT
        );
        CREATE INDEX moz_formhistory_index ON moz_formhistory(fieldname, value);
        CREATE INDEX moz_formhistory_lastused_index ON moz_formhistory(lastUsed);
        CREATE INDEX moz_formhistory_guid_index ON moz_formhistory(guid);
    """)

    n = 0
    def af(fieldname, value, times_used=None, first_days_ago=None, last_days_ago=None):
        nonlocal n
        tu = times_used or random.randint(1, 12)
        fda = first_days_ago or random.randint(30, AGE_DAYS)
        lda = last_days_ago or random.randint(0, 10)
        fu = NOW - timedelta(days=fda, hours=random.randint(0,12))
        lu = NOW - timedelta(days=lda, hours=random.randint(0,12))
        c.execute("""INSERT INTO moz_formhistory(fieldname,value,timesUsed,firstUsed,lastUsed,guid)
            VALUES(?,?,?,?,?,?)""",
            (fieldname, value, tu, int(fu.timestamp()*1e6), int(lu.timestamp()*1e6), fx_guid()))
        n += 1

    # ── Persona fields (expected) ──
    af("name", PERSONA_NAME, 8, 80, 2)
    af("email", PERSONA_EMAIL, 12, 85, 1)
    af("tel", PERSONA_PHONE, 5, 60, 5)
    af("address-line1", BILLING["street"], 4, 50, 5)
    af("address-level2", BILLING["city"], 4, 50, 5)
    af("address-level1", BILLING["state"], 4, 50, 5)
    af("postal-code", BILLING["zip"], 4, 50, 5)
    af("country", BILLING["country"], 4, 50, 5)
    af("given-name", PERSONA_FIRST, 6, 75, 3)
    af("family-name", PERSONA_LAST, 6, 75, 3)
    af("cc-name", PERSONA_NAME, 3, 40, 8)

    # ── Search queries (natural browsing behavior) ──
    searches = [
        ("searchbar-history", "python list comprehension"),
        ("searchbar-history", "best gaming gift cards 2025"),
        ("searchbar-history", "react hooks tutorial"),
        ("searchbar-history", f"{BILLING.get('city', 'austin').lower()} weather"),
        ("searchbar-history", "cheap steam keys"),
        ("searchbar-history", "eneba crypto gift card"),
        ("searchbar-history", "javascript async await"),
        ("searchbar-history", "ubuntu 24.04 download"),
        ("searchbar-history", "best online deals free shipping"),
        ("searchbar-history", "node.js express tutorial"),
        ("searchbar-history", "how to use github actions"),
        ("searchbar-history", "leetcode two sum solution"),
        ("searchbar-history", "best laptop 2025"),
        ("searchbar-history", "spotify student discount"),
        ("searchbar-history", "discord bot python"),
    ]
    for fn, val in searches:
        af(fn, val, random.randint(1,5), random.randint(10, 90), random.randint(0, 30))

    # ── Login form fields (various sites) ──
    af("username", PERSONA_EMAIL, 10, 85, 1)
    af("login", PERSONA_EMAIL, 6, 80, 2)
    af("login_field", PERSONA_EMAIL, 3, 70, 5)
    af("user", PERSONA_NAME.replace(" ",""), 4, 60, 8)

    # ── Comment/message fields ──
    comments = [
        ("comment", "thanks for the help!"),
        ("comment", "this worked perfectly"),
        ("message", "hey, check this out"),
        ("body", "I agree with this approach"),
        ("text", "great tutorial"),
    ]
    for fn, val in comments:
        af(fn, val, random.randint(1,3), random.randint(15, 60), random.randint(5, 30))

    # ── Misc form fields ──
    af("q", "eneba gift cards", 3, 20, 4)
    af("q", "g2a reviews", 2, 30, 15)
    af("q", "steam wallet codes", 2, 25, 10)
    af("search", "crypto", 4, 35, 5)
    af("search", "gift card", 3, 20, 3)
    af("search_query", "coding tutorial", 2, 60, 20)
    af("coupon", "WELCOME10", 1, 15, 15)
    af("promo", "FIRSTORDER", 1, 20, 20)

    conn.commit()
    conn.close()
    print(f"  -> {n} form entries (persona + searches + logins + misc)")
    return n
