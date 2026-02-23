#!/usr/bin/env python3
"""Dump Chromium History visits to CSV or stdout.
Usage: python tools/dump_history.py --profile generated_profiles/37ab... [--out out.csv]
"""
import sqlite3
import argparse
from datetime import datetime, timedelta
from pathlib import Path

WEBKIT_EPOCH_START = datetime(1601, 1, 1)

def webkit_to_dt(microseconds):
    try:
        return WEBKIT_EPOCH_START + timedelta(microseconds=int(microseconds))
    except Exception:
        return None


def dump_history(history_db_path, out_path=None, limit=None):
    db = Path(history_db_path)
    if not db.exists():
        raise FileNotFoundError(f"History DB not found: {db}")

    conn = sqlite3.connect(str(db))
    c = conn.cursor()

    # Select visits joined with urls
    q = """
    SELECT urls.url, urls.title, visits.visit_time, visits.visit_duration, visits.transition
    FROM visits
    JOIN urls ON visits.url = urls.id
    ORDER BY visits.visit_time ASC
    """
    if limit:
        q = q.replace('\n    ORDER BY visits.visit_time ASC', '\n    ORDER BY visits.visit_time ASC LIMIT %d' % int(limit))

    rows = c.execute(q).fetchall()
    conn.close()

    lines = []
    header = ['timestamp_utc','timestamp_local','url','title','visit_duration_ms','transition']
    lines.append(','.join(header))
    for url, title, visit_time, visit_duration, transition in rows:
        dt = webkit_to_dt(visit_time)
        if dt:
            ts_utc = dt.isoformat() + 'Z'
            ts_local = (dt + (datetime.now() - datetime.utcnow())).isoformat()
        else:
            ts_utc = ''
            ts_local = ''
        title = title.replace('\n',' ').replace(',', ' ')
        url = url.replace(',', '%2C')
        lines.append(f"{ts_utc},{ts_local},{url},{title},{visit_duration},{transition}")

    output = '\n'.join(lines)
    if out_path:
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(output)
        print(f"Wrote {len(rows)} visit rows to {out_path}")
    else:
        print(output)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--profile', required=False, default='generated_profiles/37ab1612-c285-4314-b32a-6a06d35d6d84', help='Path to profile root')
    ap.add_argument('--out', required=False, help='CSV output file')
    ap.add_argument('--limit', type=int, required=False, help='Limit number of rows')
    args = ap.parse_args()

    history_db = Path(args.profile) / 'Default' / 'History'
    dump_history(history_db, out_path=args.out, limit=args.limit)
