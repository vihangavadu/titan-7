"""
PROMETHEUS-CORE v3.1 :: MODULE: TIME DILATOR
AUTHORITY: Dva.13 | STATUS: OPERATIONAL
PURPOSE: Temporal Manipulation of Chromium History Artifacts.
         Injects synthetic browsing history backdated to create an 'Aged' narrative.
"""

import sqlite3
import random
import time
import os
from datetime import datetime, timedelta
from pathlib import Path

class TimeDilator:
    def __init__(self, profile_path):
        self.profile_path = Path(profile_path)
        self.history_db = self.profile_path / "Default" / "History"
        
        # High-Trust Domain Pool for History Injection
        self.domains = [
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
            ("https://chat.openai.com", "ChatGPT")
        ]

    def to_webkit(self, dt_obj):
        """Converts Python datetime to WebKit microsecond timestamp."""
        # WebKit epoch: Jan 1, 1601
        epoch_start = datetime(1601, 1, 1)
        delta = dt_obj - epoch_start
        return int(delta.total_seconds() * 1000000)

    def generate_timeline(self, days_back=90, target_entries=2000):
        """
        Generates a realistic list of timestamps over the last `days_back` days,
        continuing until at least `target_entries` timestamps are generated.
        Uses a probability curve to simulate human sleep/wake cycles.
        """
        timeline = []
        now = datetime.now()
        start_date = now - timedelta(days=days_back)

        # Seed the generation loop across the time window, creating clusters
        current = start_date
        attempts = 0
        while current < now or len(timeline) < target_entries:
            # Safety to avoid infinite loops
            attempts += 1
            if attempts > target_entries * 10:
                break

            # Skip ahead by random minutes (5 mins to 240 minutes)
            step_minutes = random.randint(5, 240)
            current += timedelta(minutes=step_minutes)

            if current > now:
                # Wrap sampling back to start_date with a small offset to densify
                current = start_date + timedelta(seconds=random.randint(0, 3600))

            # "Human Filter": Reduce probability of browsing at night hours
            hour = current.hour
            if 1 <= hour <= 6 and random.random() > 0.15:
                # Mostly sleep hours, skip most samples
                continue

            # Add a cluster of visits (1-6 pages) at this time
            cluster_size = random.randint(1, 6)
            for _ in range(cluster_size):
                visit_time = current + timedelta(seconds=random.randint(5, 300))
                timeline.append(visit_time)

        # Trim or sort timeline
        timeline = sorted(timeline)[:max(len(timeline), target_entries)]
        return timeline

    def inject_history(self, days_back=90, target_entries=2000, seed=None):
        """
        Writes the backdated timeline into the SQLite database.
        days_back: how far back to distribute visits
        target_entries: minimum number of visit rows to insert
        seed: RNG seed for deterministic injection
        """
        if seed is not None:
            random.seed(seed)

        print(f"[TIME DILATOR] Initiating temporal shift on: {self.history_db}")

        if not self.history_db.exists():
            print("  [!] History DB not found. Run the Burner first.")
            return

        timeline = self.generate_timeline(days_back=days_back, target_entries=target_entries)
        print(f"  > Generated {len(timeline)} historical vectors spanning {days_back} days (target {target_entries}).")

        conn = sqlite3.connect(self.history_db)
        c = conn.cursor()

        # 1. Populate URLs table
        url_map = {} # map url to ID

        # Check existing max ID
        try:
            c.execute("SELECT MAX(id) FROM urls")
            max_id = c.fetchone()[0]
            current_id = (max_id if max_id else 0) + 1
        except:
            current_id = 1

        print("  > Injecting URL references and updating visit counts...")
        for url, title in self.domains:
            # Insert URL or update existing
            try:
                c.execute("INSERT INTO urls (id, url, title, visit_count, typed_count, last_visit_time, hidden) VALUES (?, ?, ?, ?, ?, ?, ?)",
                          (current_id, url, title, random.randint(5, 50), 0, self.to_webkit(datetime.now()), 0))
                url_map[url] = current_id
                current_id += 1
            except sqlite3.IntegrityError:
                # URL might already exist from the Burner phase, fetch its ID and update
                c.execute("SELECT id, visit_count FROM urls WHERE url=?", (url,))
                row = c.fetchone()
                if row:
                    url_map[url] = row[0]
                    try:
                        c.execute("UPDATE urls SET visit_count = visit_count + ? WHERE id=?", (random.randint(1, 30), row[0]))
                    except Exception:
                        pass

        # 2. Populate Visits table (The Timeline)
        print("  > Weaving temporal visit chains... this may take a while for large targets...")
        inserted = 0
        for dt in timeline:
            url, _ = random.choice(self.domains)
            url_id = url_map.get(url)

            if url_id:
                webkit_time = self.to_webkit(dt)
                # visit_duration: random microseconds (simulated)
                # transition: 806936371 (Link) or 268435457 (Typed) - using Link primarily
                try:
                    c.execute("INSERT INTO visits (url, visit_time, from_visit, transition, segment_id, visit_duration) VALUES (?, ?, ?, ?, ?, ?)",
                              (url_id, webkit_time, 0, 806936371, 0, random.randint(1000000, 60000000)))
                    inserted += 1
                except Exception as e:
                    # If a constraint error occurs, skip
                    continue

        conn.commit()
        conn.close()
        print(f"[TIME DILATOR] History shift complete. Inserted {inserted} visits. Profile aged {days_back} days.")

if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description='Inject backdated browsing history into a Chromium profile')
    ap.add_argument('--profile', '-p', default='generated_profiles/37ab1612-c285-4314-b32a-6a06d35d6d84', help='Path to profile root')
    ap.add_argument('--days-back', type=int, default=90, help='Days to backdate')
    ap.add_argument('--target', type=int, default=2000, help='Target number of visit rows to insert')
    ap.add_argument('--seed', type=int, default=None, help='RNG seed for deterministic injection')
    args = ap.parse_args()

    if os.path.exists(args.profile):
        td = TimeDilator(args.profile)
        td.inject_history(days_back=args.days_back, target_entries=args.target, seed=args.seed)
    else:
        print('[ERROR] Profile path not found:', args.profile)
