"""
LUCID EMPIRE v7.0-TITAN - Genesis Engine
=========================================
Profile fabrication engine for creating realistic browser histories,
cookies, and localStorage with temporal displacement (profile aging).
"""

import hashlib
import json
import random
import sqlite3
import struct
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class IdentityCore:
    """Core identity information for a persona."""
    first_name: str
    last_name: str
    email: str
    phone: str = ""
    address_line1: str = ""
    city: str = ""
    state: str = ""
    postal_code: str = ""
    country: str = "US"
    date_of_birth: str = ""
    
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


@dataclass
class ProxyConfig:
    """Proxy configuration for network masking."""
    type: str = "socks5"  # http, socks4, socks5
    host: str = ""
    port: int = 0
    username: str = ""
    password: str = ""
    
    @property
    def url(self) -> str:
        if self.username and self.password:
            return f"{self.type}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.type}://{self.host}:{self.port}"


@dataclass
class CommerceTrustAnchor:
    """Trust anchor data for e-commerce platforms."""
    platform: str  # stripe, paypal, adyen
    trust_token: str = ""
    device_id: str = ""
    session_history: List[Dict] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.trust_token:
            self.trust_token = hashlib.sha256(
                f"{self.platform}:{uuid.uuid4()}".encode()
            ).hexdigest()
        if not self.device_id:
            self.device_id = str(uuid.uuid4())


class GenesisEngine:
    """
    Profile fabrication engine.
    
    Creates realistic browser profiles with:
    - Browsing history spanning the aging period
    - Cookies from major sites with appropriate timestamps
    - localStorage/sessionStorage data
    - Form autofill data
    """
    
    # Common domains for history generation
    HISTORY_DOMAINS = {
        "shopping": [
            "amazon.com", "ebay.com", "walmart.com", "target.com", "bestbuy.com",
            "etsy.com", "wayfair.com", "homedepot.com", "lowes.com", "costco.com"
        ],
        "social": [
            "facebook.com", "twitter.com", "instagram.com", "linkedin.com",
            "reddit.com", "pinterest.com", "tiktok.com", "snapchat.com"
        ],
        "news": [
            "cnn.com", "bbc.com", "nytimes.com", "washingtonpost.com",
            "theguardian.com", "reuters.com", "apnews.com", "foxnews.com"
        ],
        "entertainment": [
            "youtube.com", "netflix.com", "spotify.com", "twitch.tv",
            "hulu.com", "disneyplus.com", "hbomax.com", "primevideo.com"
        ],
        "finance": [
            "chase.com", "bankofamerica.com", "wellsfargo.com", "capitalone.com",
            "paypal.com", "venmo.com", "mint.com", "creditkarma.com"
        ],
        "tech": [
            "github.com", "stackoverflow.com", "medium.com", "dev.to",
            "hackernews.ycombinator.com", "techcrunch.com", "wired.com"
        ],
        "search": [
            "google.com", "bing.com", "duckduckgo.com"
        ],
    }
    
    # Common page titles by domain
    PAGE_TITLES = {
        "amazon.com": ["Amazon.com: Online Shopping", "Your Orders", "Today's Deals", "Prime Video"],
        "google.com": ["Google", "Google Search", "Gmail", "Google Maps"],
        "facebook.com": ["Facebook", "News Feed", "Messenger", "Marketplace"],
        "youtube.com": ["YouTube", "Home - YouTube", "Watch Later", "Subscriptions"],
        "twitter.com": ["Twitter", "Home / Twitter", "Notifications", "Messages"],
        "netflix.com": ["Netflix", "Home - Netflix", "My List", "New & Popular"],
    }
    
    def __init__(self, profile_dir: Path):
        self.profile_dir = profile_dir
        self.profile_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_history(
        self,
        aging_days: int = 90,
        entries_count: int = 500,
        categories: Optional[List[str]] = None,
        seed: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate realistic browsing history.
        
        Args:
            aging_days: How many days back to generate history
            entries_count: Number of history entries to generate
            categories: List of categories to include (shopping, social, etc.)
            seed: Random seed for reproducibility
        """
        if seed:
            random.seed(seed)
        
        if categories is None:
            categories = list(self.HISTORY_DOMAINS.keys())
        
        history = []
        base_time = datetime.now()
        
        # Distribute entries across the aging period with realistic patterns
        for i in range(entries_count):
            # Random day within aging period, weighted toward more recent
            days_ago = int(random.paretovariate(1.5)) % aging_days
            
            # Random time of day (weighted toward evening)
            hour = random.choices(
                range(24),
                weights=[1,1,1,1,1,2,3,4,5,6,6,5,4,4,5,6,7,8,9,9,8,6,4,2]
            )[0]
            minute = random.randint(0, 59)
            second = random.randint(0, 59)
            
            visit_time = base_time - timedelta(
                days=days_ago,
                hours=random.randint(0, 23) - hour,
                minutes=minute,
                seconds=second
            )
            
            # Select category and domain
            category = random.choice(categories)
            domains = self.HISTORY_DOMAINS.get(category, self.HISTORY_DOMAINS["search"])
            domain = random.choice(domains)
            
            # Generate URL
            paths = ["", "/", "/home", "/search", "/browse", "/products", "/account"]
            path = random.choice(paths)
            url = f"https://www.{domain}{path}"
            
            # Get title
            titles = self.PAGE_TITLES.get(domain, [f"{domain.split('.')[0].title()}"])
            title = random.choice(titles)
            
            # Visit count and typing (realistic patterns)
            visit_count = random.randint(1, 20) if domain in ["google.com", "youtube.com", "facebook.com"] else random.randint(1, 5)
            typed = 1 if random.random() < 0.3 else 0  # 30% typed directly
            
            history.append({
                "url": url,
                "title": title,
                "visit_time": visit_time.isoformat(),
                "visit_time_unix": int(visit_time.timestamp() * 1000000),  # microseconds
                "visit_count": visit_count,
                "typed": typed,
                "domain": domain,
                "category": category,
            })
        
        # Sort by time descending (most recent first)
        history.sort(key=lambda x: x["visit_time"], reverse=True)
        
        return history
    
    def generate_cookies(
        self,
        aging_days: int = 90,
        domains: Optional[List[str]] = None,
        seed: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate realistic cookies for common domains.
        
        Args:
            aging_days: Cookie age in days
            domains: Specific domains to generate cookies for
            seed: Random seed for reproducibility
        """
        if seed:
            random.seed(seed)
        
        if domains is None:
            # Flatten all domains
            domains = []
            for category_domains in self.HISTORY_DOMAINS.values():
                domains.extend(category_domains)
            domains = list(set(domains))[:30]  # Limit to 30 domains
        
        cookies = []
        base_time = datetime.now()
        creation_time = base_time - timedelta(days=aging_days)
        
        # Inject Trust Anchors (Stripe, Adyen, PayPal)
        # Section 4.2 & 7.3: Commerce Trust Anchors
        trust_anchors = [
            {"domain": "stripe.com", "name": "__stripe_mid", "prefix": "m_"},
            {"domain": "stripe.com", "name": "__stripe_sid", "prefix": "s_"},
            {"domain": "adyen.com", "name": "_RP_UID", "prefix": "adyen-"},
            {"domain": "paypal.com", "name": "ts_c", "prefix": "vr_"},
        ]

        for anchor in trust_anchors:
            # Add to list of domains if not present to ensure host match
            if anchor["domain"] not in domains:
                domains.append(anchor["domain"])
            
            val = f"{anchor['prefix']}{uuid.uuid4()}"
            cookies.append({
                "host": f".{anchor['domain']}",
                "name": anchor["name"],
                "value": val,
                "path": "/",
                "expiry": int((base_time + timedelta(days=365*2)).timestamp()),
                "creation_time": int(creation_time.timestamp() * 1000000),
                "last_access": int(base_time.timestamp() * 1000000),
                "secure": True,
                "http_only": False, # Often accessible by fraud scripts
            })

        for domain in domains:
            # Session/preference cookies
            cookies.append({
                "host": f".{domain}",
                "name": "_ga",
                "value": f"GA1.2.{random.randint(100000000, 999999999)}.{int(creation_time.timestamp())}",
                "path": "/",
                "expiry": int((base_time + timedelta(days=730)).timestamp()),
                "creation_time": int(creation_time.timestamp() * 1000000),
                "last_access": int(base_time.timestamp() * 1000000),
                "secure": True,
                "http_only": False,
            })
            
            # Session ID cookie
            cookies.append({
                "host": f".{domain}",
                "name": "session_id",
                "value": hashlib.sha256(f"{domain}:{seed}:{random.random()}".encode()).hexdigest()[:32],
                "path": "/",
                "expiry": int((base_time + timedelta(days=30)).timestamp()),
                "creation_time": int((base_time - timedelta(days=random.randint(1, 30))).timestamp() * 1000000),
                "last_access": int(base_time.timestamp() * 1000000),
                "secure": True,
                "http_only": True,
            })
            
            # Consent cookie
            cookies.append({
                "host": f".{domain}",
                "name": "cookie_consent",
                "value": "accepted",
                "path": "/",
                "expiry": int((base_time + timedelta(days=365)).timestamp()),
                "creation_time": int(creation_time.timestamp() * 1000000),
                "last_access": int(creation_time.timestamp() * 1000000),
                "secure": True,
                "http_only": False,
            })
        
        return cookies
    
    def generate_localstorage(
        self,
        aging_days: int = 90,
        domains: Optional[List[str]] = None,
        seed: Optional[str] = None
    ) -> Dict[str, Dict[str, str]]:
        """
        Generate localStorage data for domains.
        
        Returns dict of {origin: {key: value}}
        """
        if seed:
            random.seed(seed)
        
        if domains is None:
            domains = ["google.com", "youtube.com", "facebook.com", "amazon.com", "twitter.com"]
        
        storage = {}
        creation_time = datetime.now() - timedelta(days=aging_days)
        
        for domain in domains:
            origin = f"https://www.{domain}"
            storage[origin] = {
                "theme": random.choice(["light", "dark", "auto"]),
                "language": "en-US",
                "last_visit": str(int(creation_time.timestamp() * 1000)),
                "user_preferences": json.dumps({
                    "notifications": random.choice([True, False]),
                    "autoplay": random.choice([True, False]),
                }),
            }
        
        return storage
    
    def create_firefox_profile(
        self,
        history: List[Dict],
        cookies: List[Dict],
        output_dir: Optional[Path] = None
    ) -> Path:
        """
        Create a Firefox profile directory with injected data.
        
        Args:
            history: Generated history entries
            cookies: Generated cookies
            output_dir: Output directory for profile
        
        Returns:
            Path to created profile directory
        """
        if output_dir is None:
            output_dir = self.profile_dir / "firefox_profile"
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create places.sqlite (history/bookmarks)
        places_db = output_dir / "places.sqlite"
        self._create_places_db(places_db, history)
        
        # Create cookies.sqlite
        cookies_db = output_dir / "cookies.sqlite"
        self._create_cookies_db(cookies_db, cookies)
        
        # Create webappsstore.sqlite (LocalStorage)
        # Section 5.2: SQLite Database Injection
        webapps_db = output_dir / "webappsstore.sqlite"
        # Generate local storage data
        local_storage_data = self.generate_localstorage(
            aging_days=90, 
            domains=list(self.HISTORY_DOMAINS["shopping"]) + list(self.HISTORY_DOMAINS["finance"])
        )
        self._create_webappsstore_db(webapps_db, local_storage_data)
        
        # Create prefs.js
        prefs_file = output_dir / "prefs.js"
        self._create_prefs_js(prefs_file)
        
        return output_dir
    
    def _create_webappsstore_db(self, db_path: Path, storage_data: Dict[str, Dict[str, str]]) -> None:
        """
        Create Firefox webappsstore.sqlite database (LocalStorage).
        Note: Modern Firefox uses LSNG (Snappy), but webappsstore.sqlite is often
        checked for migration or backward compatibility.
        """
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS webappsstore2 (
                originAttributes TEXT NOT NULL DEFAULT '',
                originKey TEXT NOT NULL,
                scope TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                PRIMARY KEY (originAttributes, originKey, scope, key)
            );
        """)
        
        for origin, data in storage_data.items():
            # In webappsstore.sqlite, the originKey is usually the reversed host + protocol
            # But specific format varies. We use the standard format.
            # E.g., moc.elgoog.www.:https:443
            try:
                from urllib.parse import urlparse
                parsed = urlparse(origin)
                host_parts = parsed.netloc.split('.')
                reversed_host = ".".join(reversed(host_parts)) + "."
                scheme = parsed.scheme
                port = parsed.port if parsed.port else (443 if scheme == 'https' else 80)
                
                origin_key = f"{reversed_host}:{scheme}:{port}"
                
                for k, v in data.items():
                    cursor.execute("""
                        INSERT INTO webappsstore2 (originKey, scope, key, value)
                        VALUES (?, ?, ?, ?)
                    """, (origin_key, origin_key, k, v))
            except Exception as e:
                print(f"Error processing origin {origin}: {e}")
                continue
                
        conn.commit()
        conn.close()

    def _create_places_db(self, db_path: Path, history: List[Dict]) -> None:
        """Create Firefox places.sqlite database."""
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Create tables
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS moz_places (
                id INTEGER PRIMARY KEY,
                url TEXT NOT NULL,
                title TEXT,
                rev_host TEXT,
                visit_count INTEGER DEFAULT 0,
                hidden INTEGER DEFAULT 0,
                typed INTEGER DEFAULT 0,
                frecency INTEGER DEFAULT -1,
                last_visit_date INTEGER,
                guid TEXT,
                foreign_count INTEGER DEFAULT 0,
                url_hash INTEGER DEFAULT 0,
                description TEXT,
                preview_image_url TEXT,
                origin_id INTEGER
            );
            
            CREATE TABLE IF NOT EXISTS moz_historyvisits (
                id INTEGER PRIMARY KEY,
                from_visit INTEGER,
                place_id INTEGER,
                visit_date INTEGER,
                visit_type INTEGER,
                session INTEGER
            );
            
            CREATE INDEX IF NOT EXISTS moz_places_url_hashindex ON moz_places (url_hash);
            CREATE INDEX IF NOT EXISTS moz_historyvisits_placedateindex ON moz_historyvisits (place_id, visit_date);
        """)
        
        # Insert history
        for i, entry in enumerate(history):
            # Insert place
            url = entry["url"]
            # Create rev_host (reversed hostname)
            from urllib.parse import urlparse
            parsed = urlparse(url)
            rev_host = ".".join(reversed(parsed.netloc.split("."))) + "."
            
            guid = f"{''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=12))}"
            
            cursor.execute("""
                INSERT INTO moz_places (id, url, title, rev_host, visit_count, typed, frecency, last_visit_date, guid)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                i + 1,
                url,
                entry["title"],
                rev_host,
                entry["visit_count"],
                entry["typed"],
                random.randint(100, 10000),
                entry["visit_time_unix"],
                guid
            ))
            
            # Insert visit
            cursor.execute("""
                INSERT INTO moz_historyvisits (place_id, visit_date, visit_type, session)
                VALUES (?, ?, ?, ?)
            """, (
                i + 1,
                entry["visit_time_unix"],
                1,  # TRANSITION_LINK
                random.randint(1, 100)
            ))
        
        conn.commit()
        conn.close()
    
    def _create_cookies_db(self, db_path: Path, cookies: List[Dict]) -> None:
        """Create Firefox cookies.sqlite database."""
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS moz_cookies (
                id INTEGER PRIMARY KEY,
                originAttributes TEXT NOT NULL DEFAULT '',
                name TEXT,
                value TEXT,
                host TEXT,
                path TEXT,
                expiry INTEGER,
                lastAccessed INTEGER,
                creationTime INTEGER,
                isSecure INTEGER,
                isHttpOnly INTEGER,
                inBrowserElement INTEGER DEFAULT 0,
                sameSite INTEGER DEFAULT 0,
                rawSameSite INTEGER DEFAULT 0,
                schemeMap INTEGER DEFAULT 0
            );
        """)
        
        for i, cookie in enumerate(cookies):
            cursor.execute("""
                INSERT INTO moz_cookies (
                    id, name, value, host, path, expiry, lastAccessed, creationTime, isSecure, isHttpOnly
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                i + 1,
                cookie["name"],
                cookie["value"],
                cookie["host"],
                cookie["path"],
                cookie["expiry"],
                cookie["last_access"],
                cookie["creation_time"],
                1 if cookie["secure"] else 0,
                1 if cookie["http_only"] else 0
            ))
        
        conn.commit()
        conn.close()
    
    def _create_prefs_js(self, prefs_path: Path) -> None:
        """Create Firefox prefs.js file."""
        prefs = [
            'user_pref("browser.startup.homepage_override.mstone", "ignore");',
            'user_pref("browser.shell.checkDefaultBrowser", false);',
            'user_pref("browser.startup.page", 1);',
            'user_pref("datareporting.policy.dataSubmissionEnabled", false);',
            'user_pref("toolkit.telemetry.enabled", false);',
            'user_pref("browser.newtabpage.activity-stream.feeds.telemetry", false);',
            'user_pref("browser.ping-centre.telemetry", false);',
            'user_pref("privacy.trackingprotection.enabled", true);',
            'user_pref("network.cookie.cookieBehavior", 4);',
            'user_pref("dom.webnotifications.enabled", false);',
        ]
        
        prefs_path.write_text("\n".join(prefs))
