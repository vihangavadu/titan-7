"""
Autofill Entropy: Injects realistic, non-financial autofill keys into Web Data DB.
"""
import sqlite3
from datetime import datetime

def inject_autofill(web_data_db):
    conn = sqlite3.connect(web_data_db)
    c = conn.cursor()
    now = int(datetime.now().timestamp())
    autofill = [
        ("search_term", "how to fix sink", now),
        ("search_term", "best netflix movies 2025", now),
        ("user_email", "john.d", now),
        ("user_email", "john.doe@", now),
        ("search_term", "stripe refund policy", now),
        ("search_term", "amazon returns", now),
    ]
    for name, value, date_created in autofill:
        c.execute("INSERT INTO autofill (name, value, date_created, date_last_used, count) VALUES (?, ?, ?, ?, ?)", (name, value, date_created, date_created, 1))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: autofill_entropy.py <web_data_db>")
        exit(1)
    inject_autofill(sys.argv[1])
