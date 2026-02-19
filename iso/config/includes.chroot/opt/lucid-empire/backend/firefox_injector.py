"""
LUCID EMPIRE: Firefox Profile Injector
Objective: Inject commerce tokens, cookies, and browsing history into Firefox profile
Classification: LEVEL 6 AGENCY
"""

import sqlite3
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse
import logging
import shutil
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FirefoxProfileInjector:
    """
    Injects commerce tokens, cookies, and browsing history into Firefox profile.
    
    This is the critical component that makes the browser appear "aged" with
    real browsing history and cookies already present.
    """
    
    def __init__(self):
        """Initialize the injector with default settings"""
        # Expanded list of 300+ high-trust domains for cookie injection
        # Organized by category for realistic browsing patterns
        self.high_trust_domains = [
            # Search Engines & Portals (20)
            "google.com", "bing.com", "yahoo.com", "duckduckgo.com", "baidu.com",
            "yandex.com", "ask.com", "aol.com", "msn.com", "ecosia.org",
            "startpage.com", "brave.com", "qwant.com", "search.com", "dogpile.com",
            "webcrawler.com", "lycos.com", "excite.com", "altavista.com", "infoseek.com",
            
            # Social Media (25)
            "facebook.com", "twitter.com", "instagram.com", "linkedin.com", "pinterest.com",
            "reddit.com", "tumblr.com", "tiktok.com", "snapchat.com", "whatsapp.com",
            "telegram.org", "discord.com", "twitch.tv", "vk.com", "weibo.com",
            "medium.com", "quora.com", "flickr.com", "deviantart.com", "behance.net",
            "dribbble.com", "meetup.com", "nextdoor.com", "mastodon.social", "threads.net",
            
            # E-Commerce (40)
            "amazon.com", "ebay.com", "walmart.com", "target.com", "bestbuy.com",
            "costco.com", "homedepot.com", "lowes.com", "wayfair.com", "overstock.com",
            "etsy.com", "aliexpress.com", "wish.com", "shopify.com", "bigcommerce.com",
            "newegg.com", "zappos.com", "macys.com", "nordstrom.com", "kohls.com",
            "sephora.com", "ulta.com", "chewy.com", "petco.com", "petsmart.com",
            "ikea.com", "williams-sonoma.com", "crateandbarrel.com", "potterybarn.com", "westelm.com",
            "nike.com", "adidas.com", "underarmour.com", "footlocker.com", "finishline.com",
            "gamestop.com", "steam.com", "epicgames.com", "gog.com", "greenmangaming.com",
            
            # Payment & Finance (25)
            "paypal.com", "stripe.com", "square.com", "venmo.com", "cashapp.com",
            "chase.com", "bankofamerica.com", "wellsfargo.com", "capitalone.com", "discover.com",
            "americanexpress.com", "citi.com", "usbank.com", "pnc.com", "tdbank.com",
            "coinbase.com", "binance.com", "kraken.com", "gemini.com", "robinhood.com",
            "fidelity.com", "vanguard.com", "schwab.com", "etrade.com", "ameritrade.com",
            
            # Tech Giants (20)
            "apple.com", "microsoft.com", "github.com", "gitlab.com", "bitbucket.org",
            "stackoverflow.com", "aws.amazon.com", "cloud.google.com", "azure.microsoft.com", "digitalocean.com",
            "heroku.com", "vercel.com", "netlify.com", "cloudflare.com", "fastly.com",
            "oracle.com", "ibm.com", "salesforce.com", "adobe.com", "atlassian.com",
            
            # Entertainment & Streaming (30)
            "youtube.com", "netflix.com", "hulu.com", "disneyplus.com", "hbomax.com",
            "primevideo.com", "peacocktv.com", "paramountplus.com", "appletv.com", "crunchyroll.com",
            "spotify.com", "apple.com/music", "pandora.com", "soundcloud.com", "deezer.com",
            "tidal.com", "audible.com", "kindle.com", "scribd.com", "blinkist.com",
            "twitch.tv", "mixer.com", "youtube.com/gaming", "facebook.com/gaming", "kick.com",
            "imdb.com", "rottentomatoes.com", "metacritic.com", "letterboxd.com", "tvtime.com",
            
            # News & Media (30)
            "cnn.com", "bbc.com", "nytimes.com", "washingtonpost.com", "wsj.com",
            "reuters.com", "apnews.com", "usatoday.com", "foxnews.com", "msnbc.com",
            "nbcnews.com", "abcnews.go.com", "cbsnews.com", "huffpost.com", "businessinsider.com",
            "forbes.com", "bloomberg.com", "cnbc.com", "marketwatch.com", "ft.com",
            "theguardian.com", "independent.co.uk", "dailymail.co.uk", "mirror.co.uk", "telegraph.co.uk",
            "vice.com", "vox.com", "theatlantic.com", "newyorker.com", "wired.com",
            
            # Technology & Gaming News (20)
            "techcrunch.com", "theverge.com", "engadget.com", "arstechnica.com", "gizmodo.com",
            "cnet.com", "zdnet.com", "tomsguide.com", "tomshardware.com", "pcmag.com",
            "ign.com", "gamespot.com", "kotaku.com", "polygon.com", "eurogamer.net",
            "pcgamer.com", "rockpapershotgun.com", "destructoid.com", "giantbomb.com", "escapistmagazine.com",
            
            # Productivity & Tools (20)
            "dropbox.com", "box.com", "drive.google.com", "onedrive.com", "icloud.com",
            "notion.so", "evernote.com", "trello.com", "asana.com", "monday.com",
            "slack.com", "zoom.us", "teams.microsoft.com", "webex.com", "gotomeeting.com",
            "calendly.com", "doodle.com", "typeform.com", "surveymonkey.com", "jotform.com",
            
            # Travel & Booking (20)
            "booking.com", "expedia.com", "hotels.com", "airbnb.com", "vrbo.com",
            "kayak.com", "trivago.com", "priceline.com", "hotwire.com", "travelocity.com",
            "tripadvisor.com", "yelp.com", "opentable.com", "resy.com", "doordash.com",
            "ubereats.com", "grubhub.com", "postmates.com", "instacart.com", "shipt.com",
            
            # Education (15)
            "coursera.org", "udemy.com", "edx.org", "khanacademy.org", "skillshare.com",
            "linkedin.com/learning", "pluralsight.com", "codecademy.com", "freecodecamp.org", "udacity.com",
            "duolingo.com", "babbel.com", "rosettastone.com", "masterclass.com", "brilliant.org",
            
            # Gift Cards & Digital Goods (15)
            "eneba.com", "g2a.com", "kinguin.net", "cdkeys.com", "greenmangaming.com",
            "humblebundle.com", "fanatical.com", "giftcards.com", "gyft.com", "raise.com",
            "cardpool.com", "cardcash.com", "giftdeals.com", "egifter.com", "prezzee.com",
            
            # Utilities & Services (20)
            "weather.com", "accuweather.com", "wunderground.com", "timeanddate.com", "worldtimebuddy.com",
            "speedtest.net", "fast.com", "whatismyip.com", "ipchicken.com", "browserleaks.com",
            "virustotal.com", "haveibeenpwned.com", "lastpass.com", "1password.com", "bitwarden.com",
            "protonmail.com", "tutanota.com", "mailchimp.com", "sendgrid.com", "twilio.com",
            
            # Reference & Knowledge (15)
            "wikipedia.org", "wikimedia.org", "britannica.com", "dictionary.com", "thesaurus.com",
            "merriam-webster.com", "oxforddictionaries.com", "urbandictionary.com", "howstuffworks.com", "answers.com",
            "snopes.com", "factcheck.org", "politifact.com", "archive.org", "gutenberg.org",
        ]
        
        self.search_terms = [
            "best deals online", "how to save money", "product reviews",
            "compare prices", "discount codes", "online shopping tips",
            "gift card deals", "crypto prices", "tech news", "weather today",
            "news headlines", "sports scores", "movie reviews", "recipes",
            "travel deals", "hotel booking", "flight tickets", "car rental",
            "job search", "resume tips", "interview questions", "salary comparison",
            "home improvement", "diy projects", "gardening tips", "cooking recipes",
            "fitness tips", "workout routines", "healthy eating", "weight loss",
            "investment strategies", "stock market", "cryptocurrency", "personal finance",
            "streaming services", "new movies", "tv shows", "video games"
        ]
    
    def find_firefox_profile(self) -> Optional[Path]:
        """
        Find the default Firefox profile directory
        
        Returns:
            Path to Firefox profile directory or None if not found
        """
        import platform
        system = platform.system()
        
        if system == "Windows":
            base_path = Path(os.environ.get("APPDATA", "")) / "Mozilla" / "Firefox" / "Profiles"
        elif system == "Darwin":
            base_path = Path.home() / "Library" / "Application Support" / "Firefox" / "Profiles"
        else:  # Linux
            base_path = Path.home() / ".mozilla" / "firefox"
        
        if not base_path.exists():
            logger.warning(f"Firefox profiles directory not found: {base_path}")
            return None
        
        # Find the default profile (usually ends with .default or .default-release)
        for profile_dir in base_path.iterdir():
            if profile_dir.is_dir() and ("default" in profile_dir.name.lower()):
                logger.info(f"Found Firefox profile: {profile_dir}")
                return profile_dir
        
        # If no default, use first available
        for profile_dir in base_path.iterdir():
            if profile_dir.is_dir():
                logger.info(f"Using Firefox profile: {profile_dir}")
                return profile_dir
        
        return None
    
    def create_fresh_profile(self, profile_path: Path) -> bool:
        """
        Create a fresh Firefox profile directory with required databases
        
        Args:
            profile_path: Path where to create the profile
            
        Returns:
            True if successful
        """
        try:
            profile_path.mkdir(parents=True, exist_ok=True)
            
            # Create empty places.sqlite
            places_db = profile_path / "places.sqlite"
            self._init_places_database(places_db)
            
            # Create empty cookies.sqlite
            cookies_db = profile_path / "cookies.sqlite"
            self._init_cookies_database(cookies_db)
            
            # Create prefs.js
            prefs_file = profile_path / "prefs.js"
            self._init_prefs_file(prefs_file)
            
            logger.info(f"Created fresh profile at {profile_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create profile: {str(e)}")
            return False
    
    def _init_places_database(self, db_path: Path) -> None:
        """Initialize places.sqlite with required schema"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create moz_places table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS moz_places (
                id INTEGER PRIMARY KEY,
                url TEXT UNIQUE,
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
            )
        ''')
        
        # Create moz_historyvisits table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS moz_historyvisits (
                id INTEGER PRIMARY KEY,
                from_visit INTEGER,
                place_id INTEGER,
                visit_date INTEGER,
                visit_type INTEGER,
                session INTEGER DEFAULT 0
            )
        ''')
        
        # Create moz_origins table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS moz_origins (
                id INTEGER PRIMARY KEY,
                prefix TEXT NOT NULL,
                host TEXT NOT NULL,
                frecency INTEGER NOT NULL,
                UNIQUE (prefix, host)
            )
        ''')
        
        # Create moz_bookmarks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS moz_bookmarks (
                id INTEGER PRIMARY KEY,
                type INTEGER,
                fk INTEGER DEFAULT NULL,
                parent INTEGER,
                position INTEGER,
                title TEXT,
                keyword_id INTEGER,
                folder_type TEXT,
                dateAdded INTEGER,
                lastModified INTEGER,
                guid TEXT UNIQUE
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _init_cookies_database(self, db_path: Path) -> None:
        """Initialize cookies.sqlite with required schema"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS moz_cookies (
                id INTEGER PRIMARY KEY,
                baseDomain TEXT,
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
                schemeMap INTEGER DEFAULT 0,
                CONSTRAINT moz_uniqueid UNIQUE (name, host, path, originAttributes)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _init_prefs_file(self, prefs_path: Path) -> None:
        """Initialize prefs.js with basic Firefox preferences"""
        prefs = [
            '// Mozilla User Preferences',
            '// Auto-generated by LUCID EMPIRE',
            '',
            'user_pref("browser.startup.homepage_override.mstone", "ignore");',
            'user_pref("browser.shell.checkDefaultBrowser", false);',
            'user_pref("browser.tabs.warnOnClose", false);',
            'user_pref("browser.sessionstore.resume_from_crash", false);',
            'user_pref("datareporting.policy.dataSubmissionEnabled", false);',
            'user_pref("toolkit.telemetry.enabled", false);',
            'user_pref("browser.newtabpage.enabled", false);',
            'user_pref("privacy.trackingprotection.enabled", false);',
        ]
        
        with open(prefs_path, 'w') as f:
            f.write('\n'.join(prefs))
    
    def inject_profile(
        self, 
        profile_path: str,
        commerce_vault: Dict[str, Any],
        browsing_history: List[Dict[str, Any]],
        aging_days: int = 60
    ) -> bool:
        """
        Main injection method - injects all data into Firefox profile
        
        Args:
            profile_path: Path to Firefox profile directory
            commerce_vault: Dict with commerce tokens from CommerceInjector
            browsing_history: List of history entries
            aging_days: How many days back to age the profile
            
        Returns:
            True if successful, False otherwise
        """
        try:
            profile = Path(profile_path)
            
            if not profile.exists():
                logger.info(f"Profile doesn't exist, creating: {profile}")
                self.create_fresh_profile(profile)
            
            # 1. Inject cookies
            cookies_db = profile / "cookies.sqlite"
            self._inject_cookies(cookies_db, commerce_vault, aging_days)
            
            # 2. Inject browsing history
            places_db = profile / "places.sqlite"
            self._inject_history(places_db, browsing_history, aging_days)
            
            # 3. Generate additional high-trust cookies
            self._inject_high_trust_cookies(cookies_db, aging_days)
            
            # 4. Inject localStorage data via prefs.js
            prefs_file = profile / "prefs.js"
            self._inject_localStorage(prefs_file, commerce_vault)
            
            # 5. Generate formhistory for autofill
            formhistory_db = profile / "formhistory.sqlite"
            self._inject_formhistory(formhistory_db, commerce_vault)
            
            logger.info(f"Profile injection complete for {profile}")
            return True
            
        except Exception as e:
            logger.error(f"Profile injection failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def _inject_cookies(
        self, 
        cookies_db: Path, 
        commerce_vault: Dict[str, Any],
        aging_days: int
    ) -> None:
        """
        Inject commerce-related cookies into Firefox cookies.sqlite
        
        Creates entries for:
        - Stripe payment verification cookies
        - Shopify session cookies
        - Steam authentication cookies
        - PayPal verification cookies
        """
        if not cookies_db.exists():
            self._init_cookies_database(cookies_db)
        
        conn = sqlite3.connect(cookies_db)
        cursor = conn.cursor()
        
        now = int(datetime.now().timestamp() * 1000000)  # microseconds
        creation_base = now - (aging_days * 24 * 60 * 60 * 1000000)
        
        cookies_to_inject = [
            # Stripe cookies
            {
                'baseDomain': 'stripe.com',
                'host': '.stripe.com',
                'name': '__stripe_mid',
                'value': commerce_vault.get('stripe_mid', self._generate_guid()),
                'path': '/',
                'expiry': int((datetime.now() + timedelta(days=365)).timestamp()),
                'creationTime': creation_base + random.randint(0, 86400000000),
            },
            {
                'baseDomain': 'stripe.com',
                'host': '.stripe.com',
                'name': '__stripe_sid',
                'value': commerce_vault.get('stripe_fingerprint', self._generate_token()),
                'path': '/',
                'expiry': int((datetime.now() + timedelta(days=365)).timestamp()),
                'creationTime': creation_base + random.randint(0, 86400000000),
            },
            # Shopify cookies
            {
                'baseDomain': 'shopify.com',
                'host': '.shopify.com',
                'name': '_shopify_s',
                'value': commerce_vault.get('shopify_session_id', self._generate_guid()),
                'path': '/',
                'expiry': int((datetime.now() + timedelta(days=365)).timestamp()),
                'creationTime': creation_base + random.randint(0, 86400000000),
            },
            {
                'baseDomain': 'shopify.com',
                'host': '.shopify.com',
                'name': '_shopify_y',
                'value': commerce_vault.get('shopify_verify_token', self._generate_token()),
                'path': '/',
                'expiry': int((datetime.now() + timedelta(days=365)).timestamp()),
                'creationTime': creation_base + random.randint(0, 86400000000),
            },
            # Steam cookies
            {
                'baseDomain': 'steampowered.com',
                'host': '.steampowered.com',
                'name': 'steamLoginSecure',
                'value': self._generate_token(64),
                'path': '/',
                'expiry': int((datetime.now() + timedelta(days=365)).timestamp()),
                'creationTime': creation_base + random.randint(0, 86400000000),
            },
            # PayPal cookies
            {
                'baseDomain': 'paypal.com',
                'host': '.paypal.com',
                'name': 'cookie_check',
                'value': 'yes',
                'path': '/',
                'expiry': int((datetime.now() + timedelta(days=365)).timestamp()),
                'creationTime': creation_base + random.randint(0, 86400000000),
            },
            {
                'baseDomain': 'paypal.com',
                'host': '.paypal.com',
                'name': 'ts',
                'value': self._generate_token(32),
                'path': '/',
                'expiry': int((datetime.now() + timedelta(days=365)).timestamp()),
                'creationTime': creation_base + random.randint(0, 86400000000),
            },
        ]
        
        for cookie in cookies_to_inject:
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO moz_cookies 
                    (baseDomain, originAttributes, name, value, host, path, expiry, 
                     lastAccessed, creationTime, isSecure, isHttpOnly, inBrowserElement, 
                     sameSite, rawSameSite, schemeMap)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    cookie['baseDomain'],
                    '',
                    cookie['name'],
                    cookie['value'],
                    cookie['host'],
                    cookie['path'],
                    cookie['expiry'],
                    now,
                    cookie['creationTime'],
                    1,  # isSecure
                    0,  # isHttpOnly
                    0,  # inBrowserElement
                    0,  # sameSite
                    0,  # rawSameSite
                    2,  # schemeMap (HTTPS)
                ))
            except Exception as e:
                logger.warning(f"Failed to insert cookie {cookie['name']}: {e}")
        
        conn.commit()
        conn.close()
        logger.info(f"Injected {len(cookies_to_inject)} commerce cookies")
    
    def _inject_high_trust_cookies(self, cookies_db: Path, aging_days: int) -> None:
        """
        Inject cookies from high-trust domains (Google, Facebook, etc.)
        to make the browser appear well-used
        """
        conn = sqlite3.connect(cookies_db)
        cursor = conn.cursor()
        
        now = int(datetime.now().timestamp() * 1000000)
        creation_base = now - (aging_days * 24 * 60 * 60 * 1000000)
        
        trust_cookies = []
        
        # Google cookies
        trust_cookies.extend([
            {
                'baseDomain': 'google.com',
                'host': '.google.com',
                'name': 'NID',
                'value': self._generate_token(178),
                'path': '/',
            },
            {
                'baseDomain': 'google.com',
                'host': '.google.com',
                'name': '1P_JAR',
                'value': datetime.now().strftime("%Y-%m-%d-%H"),
                'path': '/',
            },
            {
                'baseDomain': 'google.com',
                'host': '.google.com',
                'name': 'AEC',
                'value': self._generate_token(64),
                'path': '/',
            },
        ])
        
        # YouTube cookies
        trust_cookies.extend([
            {
                'baseDomain': 'youtube.com',
                'host': '.youtube.com',
                'name': 'VISITOR_INFO1_LIVE',
                'value': self._generate_token(11),
                'path': '/',
            },
            {
                'baseDomain': 'youtube.com',
                'host': '.youtube.com',
                'name': 'YSC',
                'value': self._generate_token(11),
                'path': '/',
            },
        ])
        
        # Facebook cookies
        trust_cookies.extend([
            {
                'baseDomain': 'facebook.com',
                'host': '.facebook.com',
                'name': 'fr',
                'value': self._generate_token(48),
                'path': '/',
            },
            {
                'baseDomain': 'facebook.com',
                'host': '.facebook.com',
                'name': 'datr',
                'value': self._generate_token(24),
                'path': '/',
            },
        ])
        
        # Twitter cookies
        trust_cookies.extend([
            {
                'baseDomain': 'twitter.com',
                'host': '.twitter.com',
                'name': 'guest_id',
                'value': f"v1%3A{int(datetime.now().timestamp())}",
                'path': '/',
            },
        ])
        
        # Amazon cookies
        trust_cookies.extend([
            {
                'baseDomain': 'amazon.com',
                'host': '.amazon.com',
                'name': 'session-id',
                'value': f"{random.randint(100, 999)}-{random.randint(1000000, 9999999)}-{random.randint(1000000, 9999999)}",
                'path': '/',
            },
            {
                'baseDomain': 'amazon.com',
                'host': '.amazon.com',
                'name': 'ubid-main',
                'value': f"{random.randint(100, 999)}-{random.randint(1000000, 9999999)}-{random.randint(1000000, 9999999)}",
                'path': '/',
            },
        ])
        
        for cookie in trust_cookies:
            try:
                creation_time = creation_base + random.randint(0, aging_days * 24 * 60 * 60 * 1000000)
                cursor.execute('''
                    INSERT OR REPLACE INTO moz_cookies 
                    (baseDomain, originAttributes, name, value, host, path, expiry, 
                     lastAccessed, creationTime, isSecure, isHttpOnly, inBrowserElement, 
                     sameSite, rawSameSite, schemeMap)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    cookie['baseDomain'],
                    '',
                    cookie['name'],
                    cookie['value'],
                    cookie['host'],
                    cookie['path'],
                    int((datetime.now() + timedelta(days=365)).timestamp()),
                    now,
                    creation_time,
                    1, 0, 0, 0, 0, 2,
                ))
            except Exception as e:
                logger.warning(f"Failed to insert trust cookie: {e}")
        
        conn.commit()
        conn.close()
        logger.info(f"Injected {len(trust_cookies)} high-trust cookies")
    
    def _inject_history(
        self, 
        places_db: Path, 
        browsing_history: List[Dict[str, Any]],
        aging_days: int
    ) -> None:
        """
        Inject browsing history into Firefox places.sqlite
        
        Args:
            places_db: Path to places.sqlite
            browsing_history: List of history entries with url, title, timestamp
            aging_days: How many days back to generate history
        """
        if not places_db.exists():
            self._init_places_database(places_db)
        
        conn = sqlite3.connect(places_db)
        cursor = conn.cursor()
        
        # If no history provided, generate realistic browsing history
        if not browsing_history:
            browsing_history = self._generate_browsing_history(aging_days)
        
        for entry in browsing_history:
            try:
                url = entry.get('url', '')
                title = entry.get('title', url)
                
                # Parse URL for rev_host
                parsed = urlparse(url)
                rev_host = self._reverse_host(parsed.netloc)
                
                # Convert timestamp to microseconds
                if isinstance(entry.get('timestamp'), str):
                    ts = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
                    visit_date = int(ts.timestamp() * 1000000)
                else:
                    visit_date = int(entry.get('timestamp', datetime.now().timestamp()) * 1000000)
                
                # Generate GUID
                guid = self._generate_guid()[:12]
                
                # Insert into moz_places
                cursor.execute('''
                    INSERT OR IGNORE INTO moz_places 
                    (url, title, rev_host, visit_count, hidden, typed, frecency, 
                     last_visit_date, guid, foreign_count, url_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    url,
                    title,
                    rev_host,
                    entry.get('visit_count', random.randint(1, 5)),
                    0,  # hidden
                    0,  # typed
                    random.randint(100, 1000),  # frecency
                    visit_date,
                    guid,
                    0,  # foreign_count
                    hash(url) & 0xFFFFFFFF,  # url_hash
                ))
                
                # Get place_id
                cursor.execute('SELECT id FROM moz_places WHERE url = ?', (url,))
                result = cursor.fetchone()
                if result:
                    place_id = result[0]
                    
                    # Insert visit record
                    cursor.execute('''
                        INSERT INTO moz_historyvisits 
                        (from_visit, place_id, visit_date, visit_type, session)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        0,  # from_visit
                        place_id,
                        visit_date,
                        1,  # visit_type (1 = LINK)
                        0,  # session
                    ))
                    
            except Exception as e:
                logger.warning(f"Failed to insert history entry: {e}")
        
        conn.commit()
        conn.close()
        logger.info(f"Injected {len(browsing_history)} history entries")
    
    def _generate_browsing_history(self, aging_days: int) -> List[Dict[str, Any]]:
        """
        Generate realistic browsing history for the aging period
        
        Creates entries for:
        - Google searches
        - News sites
        - Social media
        - Shopping sites
        - Entertainment sites
        """
        history = []
        now = datetime.now()
        
        # Generate entries spread across aging period
        for day_offset in range(aging_days, 0, -1):
            # Random number of visits per day (2-10)
            visits_today = random.randint(2, 10)
            
            for _ in range(visits_today):
                hour = random.randint(8, 23)
                minute = random.randint(0, 59)
                visit_time = now - timedelta(days=day_offset, hours=24-hour, minutes=minute)
                
                # Pick a random site category
                category = random.choice(['search', 'news', 'social', 'shopping', 'entertainment'])
                
                if category == 'search':
                    term = random.choice(self.search_terms)
                    history.append({
                        'url': f"https://www.google.com/search?q={term.replace(' ', '+')}",
                        'title': f"{term} - Google Search",
                        'timestamp': visit_time.isoformat(),
                        'visit_count': random.randint(1, 3),
                    })
                elif category == 'news':
                    news_sites = [
                        ('https://www.cnn.com/', 'CNN - Breaking News'),
                        ('https://www.bbc.com/news', 'BBC News'),
                        ('https://www.reuters.com/', 'Reuters'),
                        ('https://news.ycombinator.com/', 'Hacker News'),
                    ]
                    site = random.choice(news_sites)
                    history.append({
                        'url': site[0],
                        'title': site[1],
                        'timestamp': visit_time.isoformat(),
                        'visit_count': random.randint(1, 5),
                    })
                elif category == 'social':
                    social_sites = [
                        ('https://www.facebook.com/', 'Facebook'),
                        ('https://twitter.com/', 'Twitter'),
                        ('https://www.reddit.com/', 'Reddit'),
                        ('https://www.linkedin.com/', 'LinkedIn'),
                    ]
                    site = random.choice(social_sites)
                    history.append({
                        'url': site[0],
                        'title': site[1],
                        'timestamp': visit_time.isoformat(),
                        'visit_count': random.randint(1, 10),
                    })
                elif category == 'shopping':
                    shopping_sites = [
                        ('https://www.amazon.com/', 'Amazon.com'),
                        ('https://www.ebay.com/', 'eBay'),
                        ('https://www.walmart.com/', 'Walmart'),
                        ('https://www.target.com/', 'Target'),
                    ]
                    site = random.choice(shopping_sites)
                    history.append({
                        'url': site[0],
                        'title': site[1],
                        'timestamp': visit_time.isoformat(),
                        'visit_count': random.randint(1, 3),
                    })
                else:  # entertainment
                    entertainment_sites = [
                        ('https://www.youtube.com/', 'YouTube'),
                        ('https://www.netflix.com/', 'Netflix'),
                        ('https://www.spotify.com/', 'Spotify'),
                        ('https://www.twitch.tv/', 'Twitch'),
                    ]
                    site = random.choice(entertainment_sites)
                    history.append({
                        'url': site[0],
                        'title': site[1],
                        'timestamp': visit_time.isoformat(),
                        'visit_count': random.randint(1, 8),
                    })
        
        logger.info(f"Generated {len(history)} browsing history entries for {aging_days} days")
        return history
    
    def _inject_localStorage(
        self, 
        prefs_file: Path, 
        commerce_vault: Dict[str, Any]
    ) -> None:
        """
        Inject localStorage values via Firefox webappsstore.sqlite
        and prefs.js for commerce verification tokens
        """
        # Read existing prefs.js
        existing_prefs = ""
        if prefs_file.exists():
            with open(prefs_file, 'r') as f:
                existing_prefs = f.read()
        
        # Prepare localStorage items to inject
        localStorage_items = {
            'stripe_verified': commerce_vault.get('stripe_mid', ''),
            'shopify_verified': commerce_vault.get('shopify_verify_token', ''),
            'paypal_verified': commerce_vault.get('paypal_verified_email', ''),
            'commerce_trust_level': 'high',
            'device_fingerprint': self._generate_token(32),
        }
        
        # Build prefs.js entries
        new_prefs = [
            '',
            '// LUCID EMPIRE: Commerce Trust Tokens',
        ]
        
        for key, value in localStorage_items.items():
            if value:
                escaped_value = str(value).replace('"', '\\"')
                new_prefs.append(f'user_pref("extensions.lucid.{key}", "{escaped_value}");')
        
        # Steam purchase history
        steam_history = commerce_vault.get('steam_purchase_history', [])
        if steam_history:
            steam_json = json.dumps(steam_history).replace('"', '\\"')
            new_prefs.append(f'user_pref("extensions.lucid.steam_purchases", "{steam_json}");')
        
        # Write updated prefs.js
        with open(prefs_file, 'w') as f:
            f.write(existing_prefs)
            f.write('\n'.join(new_prefs))
        
        logger.info("Injected localStorage values into prefs.js")
    
    def _inject_formhistory(
        self, 
        formhistory_db: Path, 
        commerce_vault: Dict[str, Any]
    ) -> None:
        """
        Inject form autofill data into formhistory.sqlite
        for instant checkout capability
        """
        conn = sqlite3.connect(formhistory_db)
        cursor = conn.cursor()
        
        # Create table if not exists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS moz_formhistory (
                id INTEGER PRIMARY KEY,
                fieldname TEXT NOT NULL,
                value TEXT NOT NULL,
                timesUsed INTEGER,
                firstUsed INTEGER,
                lastUsed INTEGER,
                guid TEXT
            )
        ''')
        
        # Get fullz data from commerce vault (if provided)
        fullz = commerce_vault.get('fullz', {})
        
        now = int(datetime.now().timestamp() * 1000000)
        first_used = now - (60 * 24 * 60 * 60 * 1000000)  # 60 days ago
        
        form_entries = [
            ('email', fullz.get('email', 'user@example.com')),
            ('firstName', fullz.get('first_name', 'John')),
            ('lastName', fullz.get('last_name', 'Doe')),
            ('name', f"{fullz.get('first_name', 'John')} {fullz.get('last_name', 'Doe')}"),
            ('address', fullz.get('address', '123 Main Street')),
            ('city', fullz.get('city', 'Springfield')),
            ('state', fullz.get('state', 'IL')),
            ('zip', fullz.get('zip', '62701')),
            ('phone', fullz.get('phone', '555-123-4567')),
        ]
        
        for fieldname, value in form_entries:
            if value:
                try:
                    cursor.execute('''
                        INSERT OR REPLACE INTO moz_formhistory 
                        (fieldname, value, timesUsed, firstUsed, lastUsed, guid)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        fieldname,
                        value,
                        random.randint(3, 15),
                        first_used,
                        now,
                        self._generate_guid()[:12],
                    ))
                except Exception as e:
                    logger.warning(f"Failed to insert form entry: {e}")
        
        conn.commit()
        conn.close()
        logger.info(f"Injected {len(form_entries)} form history entries")
    
    def _reverse_host(self, host: str) -> str:
        """Convert domain to Firefox reverse notation"""
        if not host:
            return ""
        parts = host.split('.')
        return '.'.join(reversed(parts)) + '.'
    
    def _generate_guid(self) -> str:
        """Generate a random GUID"""
        import uuid
        return str(uuid.uuid4())
    
    def _generate_token(self, length: int = 32) -> str:
        """Generate a random base64-like token"""
        import base64
        random_bytes = bytes(random.getrandbits(8) for _ in range(length))
        return base64.b64encode(random_bytes).decode('utf-8')[:length]


# Convenience function for direct use
def inject_firefox_profile(
    profile_path: str,
    commerce_vault: Dict[str, Any],
    browsing_history: List[Dict[str, Any]] = None,
    aging_days: int = 60
) -> bool:
    """
    Convenience function to inject data into Firefox profile
    
    Args:
        profile_path: Path to Firefox profile
        commerce_vault: Commerce tokens from CommerceInjector
        browsing_history: Optional list of history entries
        aging_days: How many days back to age
        
    Returns:
        True if successful
    """
    injector = FirefoxProfileInjector()
    return injector.inject_profile(
        profile_path, 
        commerce_vault, 
        browsing_history or [], 
        aging_days
    )


if __name__ == "__main__":
    # Test the injector
    print("LUCID EMPIRE: Firefox Profile Injector Test")
    print("=" * 50)
    
    injector = FirefoxProfileInjector()
    
    # Find Firefox profile
    profile = injector.find_firefox_profile()
    if profile:
        print(f"Found Firefox profile: {profile}")
    else:
        print("No Firefox profile found, will create test profile")
        profile = Path("./test_profile")
    
    # Test commerce vault
    test_vault = {
        'stripe_mid': 'test_stripe_123',
        'shopify_session_id': 'test_shopify_456',
        'steam_purchase_history': [{'game': 'Counter-Strike 2', 'price': 14.99}],
        'fullz': {
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
        }
    }
    
    # Run injection
    result = injector.inject_profile(str(profile), test_vault, [], 60)
    print(f"Injection result: {'SUCCESS' if result else 'FAILED'}")
