#!/usr/bin/env python3
"""
TITAN V8.1 SINGULARITY — Time Dilator

Injects backdated browsing history into Firefox/Camoufox profiles to create
an 'aged' browsing narrative. Adapted from Prometheus-Core for Titan V8.1.

Original: Targeted Chrome's Default/History with WebKit timestamps (1601 epoch).
Adapted:  Targets Firefox's places.sqlite with Mozilla microsecond timestamps (Unix epoch).

Integration points:
  - genesis_core.py: Call after profile generation to densify history
  - advanced_profile_generator.py: Complement synthetic profiles with temporal depth
  - profile_realism_engine.py: Add realistic visit distribution after realism pass
  - temporal_entropy.py: Use EntropyGenerator for realistic timing patterns
"""

import sqlite3
import random
import time
import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any

logger = logging.getLogger("TITAN-TIME-DILATOR")

# ═══════════════════════════════════════════════════════════════════════════════
# HIGH-TRUST DOMAIN POOL
# ═══════════════════════════════════════════════════════════════════════════════

HIGH_TRUST_DOMAINS = [
    ("https://www.google.com/search?q=weather", "Google Search - Weather"),
    ("https://www.youtube.com", "YouTube"),
    ("https://www.amazon.com", "Amazon.com: Online Shopping"),
    ("https://www.reddit.com", "Reddit - Dive into anything"),
    ("https://en.wikipedia.org/wiki/Main_Page", "Wikipedia, the free encyclopedia"),
    ("https://github.com", "GitHub: Let's build from here"),
    ("https://stackoverflow.com", "Stack Overflow - Where Developers Learn"),
    ("https://www.cnn.com", "CNN - Breaking News"),
    ("https://www.bbc.com", "BBC Home"),
    ("https://www.netflix.com", "Netflix"),
    ("https://www.linkedin.com", "LinkedIn: Log In or Sign Up"),
    ("https://www.microsoft.com", "Microsoft - Cloud, Computers, Apps"),
    ("https://www.apple.com", "Apple"),
    ("https://www.twitch.tv", "Twitch"),
    ("https://www.espn.com", "ESPN: Serving Sports Fans"),
    ("https://www.adobe.com", "Adobe: Creative, marketing and document management solutions"),
    ("https://www.dropbox.com", "Dropbox"),
    ("https://www.salesforce.com", "Salesforce: The Customer Company"),
    ("https://chat.openai.com", "ChatGPT"),
    ("https://www.walmart.com", "Walmart.com"),
    ("https://www.ebay.com", "Electronics, Cars, Fashion | eBay"),
    ("https://www.target.com", "Target"),
    ("https://www.bestbuy.com", "Best Buy"),
    ("https://www.nytimes.com", "The New York Times"),
    ("https://www.weather.com", "Weather.com"),
]


class TimeDilator:
    """
    Injects backdated browsing history into Firefox/Camoufox places.sqlite.

    Uses Mozilla microsecond timestamps (microseconds since Unix epoch 1970-01-01),
    NOT Chrome WebKit timestamps (microseconds since 1601-01-01).

    Usage:
        td = TimeDilator("/opt/titan/profiles/TITAN-XXXX")
        td.inject_history(days_back=90, target_entries=2000)
    """

    def __init__(self, profile_path, domains=None):
        self.profile_path = Path(profile_path)
        self.places_db = self.profile_path / "places.sqlite"
        self.domains = domains or HIGH_TRUST_DOMAINS

    @staticmethod
    def to_mozilla_timestamp(dt_obj):
        """Convert Python datetime to Mozilla microsecond timestamp (Unix epoch)."""
        return int(dt_obj.timestamp() * 1_000_000)

    def generate_timeline(self, days_back=90, target_entries=2000):
        """
        Generate realistic timestamps with human sleep/wake cycle filtering.

        Returns sorted list of datetime objects distributed over days_back.
        """
        timeline = []
        now = datetime.now()
        start_date = now - timedelta(days=days_back)

        current = start_date
        attempts = 0
        while len(timeline) < target_entries:
            attempts += 1
            if attempts > target_entries * 10:
                break

            step_minutes = random.randint(5, 240)
            current += timedelta(minutes=step_minutes)

            if current > now:
                current = start_date + timedelta(seconds=random.randint(0, 3600))

            hour = current.hour
            if 1 <= hour <= 6 and random.random() > 0.15:
                continue

            cluster_size = random.randint(1, 6)
            for _ in range(cluster_size):
                visit_time = current + timedelta(seconds=random.randint(5, 300))
                timeline.append(visit_time)

        timeline.sort()
        return timeline[:max(len(timeline), target_entries)]

    def inject_history(self, days_back=90, target_entries=2000, seed=None):
        """
        Write backdated history into Firefox places.sqlite.

        Args:
            days_back: How far back to distribute visits
            target_entries: Minimum number of visit rows
            seed: RNG seed for deterministic injection
        """
        if seed is not None:
            random.seed(seed)

        logger.info(f"Initiating temporal shift on: {self.places_db}")

        if not self.places_db.exists():
            logger.error("places.sqlite not found. Generate profile first via genesis_core.")
            return False

        timeline = self.generate_timeline(days_back=days_back, target_entries=target_entries)
        logger.info(f"Generated {len(timeline)} visit vectors spanning {days_back} days")

        conn = sqlite3.connect(str(self.places_db))
        c = conn.cursor()

        # Get next available place ID
        try:
            c.execute("SELECT MAX(id) FROM moz_places")
            row = c.fetchone()
            next_id = (row[0] if row[0] else 0) + 1
        except Exception:
            next_id = 1

        # Insert URLs into moz_places
        url_map = {}
        for url, title in self.domains:
            try:
                frecency = random.randint(100, 2000)
                visit_count = random.randint(5, 50)
                last_visit = self.to_mozilla_timestamp(datetime.now() - timedelta(hours=random.randint(0, 48)))

                c.execute("""
                    INSERT OR IGNORE INTO moz_places
                    (id, url, title, rev_host, visit_count, hidden, typed, frecency, last_visit_date)
                    VALUES (?, ?, ?, ?, ?, 0, 1, ?, ?)
                """, (next_id, url, title, self._reverse_host(url), visit_count, frecency, last_visit))

                url_map[url] = next_id
                next_id += 1
            except sqlite3.IntegrityError:
                c.execute("SELECT id FROM moz_places WHERE url=?", (url,))
                row = c.fetchone()
                if row:
                    url_map[url] = row[0]
                    c.execute("UPDATE moz_places SET visit_count = visit_count + ? WHERE id=?",
                              (random.randint(1, 20), row[0]))

        # Insert visits into moz_historyvisits
        inserted = 0
        for dt in timeline:
            url, _ = random.choice(self.domains)
            place_id = url_map.get(url)
            if not place_id:
                continue

            moz_ts = self.to_mozilla_timestamp(dt)
            # visit_type: 1=LINK, 2=TYPED, 3=BOOKMARK, 5=EMBED, 6=FRECENCY
            visit_type = random.choice([1, 1, 1, 2, 1])
            try:
                c.execute("""
                    INSERT INTO moz_historyvisits (place_id, visit_date, visit_type, session)
                    VALUES (?, ?, ?, 0)
                """, (place_id, moz_ts, visit_type))
                inserted += 1
            except Exception:
                continue

        # Update frecency for visited places
        for place_id in url_map.values():
            c.execute("UPDATE moz_places SET frecency = visit_count * 100 WHERE id=?", (place_id,))

        conn.commit()
        conn.close()
        logger.info(f"History shift complete. Inserted {inserted} visits. Profile aged {days_back} days.")
        return True

    @staticmethod
    def _reverse_host(url):
        """Generate rev_host for moz_places (Firefox requirement)."""
        try:
            from urllib.parse import urlparse
            host = urlparse(url).hostname or ""
            return host[::-1] + "."
        except Exception:
            return ".com."

    def get_status(self) -> Dict[str, Any]:
        """Return module status."""
        return {
            "available": True,
            "places_db_exists": self.places_db.exists(),
            "domain_pool_size": len(self.domains),
            "version": "8.1",
        }


if __name__ == '__main__':
    import argparse
    logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(name)s | %(message)s')

    ap = argparse.ArgumentParser(description='TITAN V8.1 — Inject backdated history into Firefox profile')
    ap.add_argument('--profile', '-p', required=True, help='Path to Firefox/Camoufox profile directory')
    ap.add_argument('--days-back', type=int, default=90, help='Days to backdate')
    ap.add_argument('--target', type=int, default=2000, help='Target number of visit rows')
    ap.add_argument('--seed', type=int, default=None, help='RNG seed for deterministic injection')
    args = ap.parse_args()

    if os.path.exists(args.profile):
        td = TimeDilator(args.profile)
        td.inject_history(days_back=args.days_back, target_entries=args.target, seed=args.seed)
    else:
        print(f'[ERROR] Profile path not found: {args.profile}')
