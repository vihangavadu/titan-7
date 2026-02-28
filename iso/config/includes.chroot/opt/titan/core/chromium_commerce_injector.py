"""
Commerce Injector: Synthesizes realistic purchase funnel and download artifacts in Chromium profiles.
"""
import sqlite3
import random
from datetime import datetime, timedelta
from pathlib import Path
import uuid

def to_webkit(dt_obj):
    epoch_start = datetime(1601, 1, 1)
    delta = dt_obj - epoch_start
    return int(delta.total_seconds() * 1000000)

def inject_golden_chain(history_db, base_url, order_id, t0=None):
    """
    Injects a realistic purchase funnel sequence into the History DB.
    base_url: e.g. 'https://target-site.com'
    order_id: e.g. 'ORD-99283'
    t0: datetime for the 'thank you' event (defaults to now)
    """
    t0 = t0 or datetime.now()
    events = [
        (f"{base_url}/product/jordan-4-retro", "Product Page", t0 - timedelta(minutes=5)),
        (f"{base_url}/cart", "Cart", t0 - timedelta(minutes=3)),
        (f"{base_url}/checkout/shipping", "Checkout", t0 - timedelta(minutes=2)),
        (f"{base_url}/checkout/thank_you?order_id={order_id}", "Order Success", t0),
    ]
    conn = sqlite3.connect(history_db)
    c = conn.cursor()
    # Insert URLs if not present
    url_map = {}
    for url, title, dt in events:
        try:
            c.execute("INSERT INTO urls (url, title, visit_count, typed_count, last_visit_time, hidden) VALUES (?, ?, ?, ?, ?, ?)",
                      (url, title, 1, 0, to_webkit(dt), 0))
            url_id = c.lastrowid
        except sqlite3.IntegrityError:
            c.execute("SELECT id FROM urls WHERE url=?", (url,))
            url_id = c.fetchone()[0]
        url_map[url] = url_id
    # Insert visits
    for url, title, dt in events:
        url_id = url_map[url]
        c.execute("INSERT INTO visits (url, visit_time, from_visit, transition, segment_id, visit_duration) VALUES (?, ?, ?, ?, ?, ?)",
                  (url_id, to_webkit(dt), 0, 806936371, 0, random.randint(1000000, 60000000)))
    conn.commit()
    conn.close()

def inject_download(history_db, order_id, file_name=None, t0=None):
    """
    Injects a fake download row into the downloads table.
    file_name: e.g. 'invoice_ORD-99283.pdf'
    t0: datetime for download (defaults to now)
    """
    t0 = t0 or datetime.now()
    file_name = file_name or f"invoice_{order_id}.pdf"
    fake_path = f"C:/Users/Admin/Downloads/{file_name}"
    url = f"https://target-site.com/invoice/{order_id}.pdf"
    guid = str(uuid.uuid4())
    # create a simple hash blob (md5 of filename)
    import hashlib
    h = hashlib.md5(fake_path.encode('utf-8')).digest()
    end_time = to_webkit(t0 + timedelta(seconds=5))
    # connect with timeout and retry on locked DB
    for attempt in range(5):
        try:
            conn = sqlite3.connect(history_db, timeout=30)
            c = conn.cursor()
            c.execute("""
                INSERT INTO downloads (guid, current_path, target_path, start_time, received_bytes, total_bytes, state, danger_type, interrupt_reason, hash, end_time, opened, last_access_time, transient, referrer, site_url, embedder_download_data, tab_url, tab_referrer_url, etag, last_modified, mime_type, original_mime_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                guid, fake_path, fake_path, to_webkit(t0), 123456, 123456, 1, 0, 0, h, end_time, 0, to_webkit(t0), 0, '', url, '', '', '', '', '', 'application/pdf', 'application/pdf'
            ))
            conn.commit()
            conn.close()
            break
        except sqlite3.OperationalError as e:
            if 'locked' in str(e).lower():
                import time
                time.sleep(1)
                continue
            else:
                raise
    else:
        raise sqlite3.OperationalError('Failed to write download row: DB locked')
