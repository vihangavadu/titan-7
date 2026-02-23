"""
Top Sites Sync: Populates Default/Top Sites DB with most-visited URLs from History.
"""
import sqlite3
from collections import Counter
from pathlib import Path

def sync_top_sites(history_db, top_sites_db, top_n=10):
    conn = sqlite3.connect(history_db)
    c = conn.cursor()
    c.execute("SELECT urls.url FROM visits JOIN urls ON visits.url = urls.id")
    urls = [row[0] for row in c.fetchall()]
    conn.close()
    top = Counter(urls).most_common(top_n)
    conn2 = sqlite3.connect(top_sites_db)
    c2 = conn2.cursor()
    c2.execute("DELETE FROM top_sites")
    for i, (url, count) in enumerate(top):
        # Table schema: url, url_rank, title
        c2.execute("INSERT INTO top_sites (url, url_rank, title) VALUES (?, ?, ?)", (url, i+1, url))
    conn2.commit()
    conn2.close()

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: top_sites_sync.py <history_db> <top_sites_db>")
        exit(1)
    sync_top_sites(sys.argv[1], sys.argv[2])
