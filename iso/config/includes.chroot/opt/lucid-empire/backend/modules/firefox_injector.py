#!/usr/bin/env python3
"""
FIREFOX PROFILE INJECTOR
========================
Injects cookies, history, form data, and localStorage into Firefox profiles.
Compatible with Firefox/Camoufox profile structure.

Author: LUCID EMPIRE
Version: 7.0.0-TITAN
"""

import sqlite3
import json
import time
import uuid
import struct
import random
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from urllib.parse import urlparse
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

try:
    import lz4.block
    HAS_LZ4 = True
except ImportError:
    HAS_LZ4 = False


@dataclass
class CookieEntry:
    """Cookie entry for injection"""
    name: str
    value: str
    host: str
    path: str = "/"
    expiry: Optional[int] = None  # Unix seconds, None = session
    secure: bool = True
    http_only: bool = False
    same_site: int = 0  # 0=None, 1=Lax, 2=Strict
    creation_time: Optional[int] = None  # microseconds


@dataclass  
class HistoryEntry:
    """History entry for injection"""
    url: str
    title: str
    visit_count: int = 1
    typed: bool = False
    visit_type: int = 1  # 1=link, 2=typed
    visit_date: Optional[int] = None  # microseconds


@dataclass
class FormEntry:
    """Form autofill entry"""
    fieldname: str
    value: str
    times_used: int = 1
    first_used: Optional[int] = None
    last_used: Optional[int] = None


@dataclass
class LocalStorageEntry:
    """localStorage entry"""
    origin: str  # e.g., https://stripe.com
    key: str
    value: str


class FirefoxProfileInjector:
    """
    Injects data into Firefox/Camoufox profile databases.
    
    Supports:
    - cookies.sqlite (HTTP cookies)
    - places.sqlite (browsing history)
    - formhistory.sqlite (form autofill)
    - webappsstore.sqlite (localStorage)
    - times.json (profile age)
    - sessionstore.jsonlz4 (session data)
    """
    
    def __init__(self, profile_path: str, aging_days: int = 90):
        """
        Initialize the injector.
        
        Args:
            profile_path: Path to Firefox profile directory
            aging_days: Number of days to backdate profile artifacts
        """
        self.profile_path = Path(profile_path)
        self.aging_days = aging_days
        
        # Calculate time references
        self.now = int(time.time())
        self.now_us = self.now * 1_000_000  # microseconds
        self.now_ms = self.now * 1_000  # milliseconds
        
        # Backdated times
        self.creation_time = self.now - (aging_days * 86400)
        self.creation_time_us = self.creation_time * 1_000_000
        self.creation_time_ms = self.creation_time * 1_000
        
        # Validate profile path
        if not self.profile_path.exists():
            raise ValueError(f"Profile path does not exist: {profile_path}")
    
    # =========================================================================
    # COOKIES
    # =========================================================================
    
    def inject_cookie(self, cookie: CookieEntry) -> bool:
        """
        Inject a cookie into cookies.sqlite
        
        Args:
            cookie: CookieEntry object
            
        Returns:
            True if successful
        """
        db_path = self.profile_path / 'cookies.sqlite'
        
        # Calculate times
        creation_time = cookie.creation_time or self.creation_time_us
        last_accessed = creation_time
        expiry = cookie.expiry or (self.now + 365 * 86400)
        
        conn = sqlite3.connect(str(db_path))
        try:
            conn.execute("""
                INSERT OR REPLACE INTO moz_cookies 
                (name, value, host, path, expiry, lastAccessed, creationTime,
                 isSecure, isHttpOnly, sameSite, schemeMap, originAttributes,
                 inBrowserElement, isPartitionedAttributeSet)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 2, '', 0, 0)
            """, (
                cookie.name,
                cookie.value,
                cookie.host,
                cookie.path,
                expiry,
                last_accessed,
                creation_time,
                int(cookie.secure),
                int(cookie.http_only),
                cookie.same_site
            ))
            conn.commit()
            return True
        except Exception as e:
            print(f"[!] Error injecting cookie: {e}")
            return False
        finally:
            conn.close()
    
    def inject_cookies_batch(self, cookies: List[CookieEntry]) -> int:
        """Inject multiple cookies. Returns count of successful injections."""
        success = 0
        for cookie in cookies:
            if self.inject_cookie(cookie):
                success += 1
        return success
    
    # =========================================================================
    # BROWSING HISTORY
    # =========================================================================
    
    def inject_history(self, entry: HistoryEntry) -> Optional[int]:
        """
        Inject a history entry into places.sqlite
        
        Args:
            entry: HistoryEntry object
            
        Returns:
            place_id if successful, None otherwise
        """
        db_path = self.profile_path / 'places.sqlite'
        
        # Parse URL for rev_host
        parsed = urlparse(entry.url)
        host = parsed.netloc
        rev_host = '.'.join(reversed(host.split('.'))) + '.'
        
        # Calculate visit date
        visit_date = entry.visit_date or self.now_us
        
        # Generate GUID
        guid = str(uuid.uuid4())[:12]
        
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        try:
            # Check if URL already exists
            cursor.execute("SELECT id FROM moz_places WHERE url = ?", (entry.url,))
            existing = cursor.fetchone()
            
            if existing:
                place_id = existing[0]
                # Update existing entry
                cursor.execute("""
                    UPDATE moz_places 
                    SET visit_count = visit_count + ?, 
                        last_visit_date = MAX(last_visit_date, ?),
                        frecency = frecency + 10
                    WHERE id = ?
                """, (entry.visit_count, visit_date, place_id))
            else:
                # Insert new place
                url_hash = abs(hash(entry.url)) % (10**15)
                cursor.execute("""
                    INSERT INTO moz_places 
                    (url, title, rev_host, visit_count, hidden, typed, 
                     frecency, last_visit_date, guid, url_hash, foreign_count)
                    VALUES (?, ?, ?, ?, 0, ?, 100, ?, ?, ?, 0)
                """, (
                    entry.url,
                    entry.title,
                    rev_host,
                    entry.visit_count,
                    1 if entry.typed else 0,
                    visit_date,
                    guid,
                    url_hash
                ))
                place_id = cursor.lastrowid
            
            # Insert visit record
            cursor.execute("""
                INSERT INTO moz_historyvisits 
                (from_visit, place_id, visit_date, visit_type, session, source)
                VALUES (0, ?, ?, ?, 0, 0)
            """, (place_id, visit_date, entry.visit_type))
            
            conn.commit()
            return place_id
            
        except Exception as e:
            print(f"[!] Error injecting history: {e}")
            conn.rollback()
            return None
        finally:
            conn.close()
    
    def inject_history_batch(self, entries: List[HistoryEntry]) -> int:
        """Inject multiple history entries. Returns count of successful injections."""
        success = 0
        for entry in entries:
            if self.inject_history(entry) is not None:
                success += 1
        return success
    
    def generate_browsing_history(self, days: int = None, 
                                   persona: str = 'general') -> List[HistoryEntry]:
        """
        Generate realistic browsing history for a persona.
        
        Args:
            days: Number of days of history to generate (default: aging_days)
            persona: Persona type (general, gamer, developer, trader, shopper)
            
        Returns:
            List of HistoryEntry objects
        """
        days = days or self.aging_days
        
        SITE_POOLS = {
            'general': [
                ('https://google.com', 'Google'),
                ('https://youtube.com', 'YouTube'),
                ('https://facebook.com', 'Facebook'),
                ('https://twitter.com', 'Twitter'),
                ('https://reddit.com', 'Reddit'),
                ('https://amazon.com', 'Amazon'),
                ('https://wikipedia.org', 'Wikipedia'),
                ('https://instagram.com', 'Instagram'),
                ('https://linkedin.com', 'LinkedIn'),
                ('https://netflix.com', 'Netflix'),
            ],
            'developer': [
                ('https://github.com', 'GitHub'),
                ('https://stackoverflow.com', 'Stack Overflow'),
                ('https://docs.python.org', 'Python Documentation'),
                ('https://developer.mozilla.org', 'MDN Web Docs'),
                ('https://npmjs.com', 'npm'),
                ('https://docker.com', 'Docker'),
                ('https://aws.amazon.com', 'Amazon AWS'),
                ('https://news.ycombinator.com', 'Hacker News'),
            ],
            'gamer': [
                ('https://store.steampowered.com', 'Steam'),
                ('https://twitch.tv', 'Twitch'),
                ('https://discord.com', 'Discord'),
                ('https://reddit.com/r/gaming', 'Reddit Gaming'),
                ('https://epicgames.com', 'Epic Games'),
                ('https://xbox.com', 'Xbox'),
                ('https://playstation.com', 'PlayStation'),
            ],
            'trader': [
                ('https://coinbase.com', 'Coinbase'),
                ('https://binance.com', 'Binance'),
                ('https://tradingview.com', 'TradingView'),
                ('https://coingecko.com', 'CoinGecko'),
                ('https://reddit.com/r/cryptocurrency', 'Reddit Crypto'),
                ('https://finance.yahoo.com', 'Yahoo Finance'),
            ],
            'shopper': [
                ('https://amazon.com', 'Amazon'),
                ('https://ebay.com', 'eBay'),
                ('https://walmart.com', 'Walmart'),
                ('https://target.com', 'Target'),
                ('https://bestbuy.com', 'Best Buy'),
                ('https://etsy.com', 'Etsy'),
                ('https://aliexpress.com', 'AliExpress'),
            ]
        }
        
        # Combine general with persona-specific
        sites = SITE_POOLS['general'].copy()
        if persona in SITE_POOLS:
            sites.extend(SITE_POOLS[persona])
        
        entries = []
        
        for day in range(days, 0, -1):
            # Random number of visits per day (more on weekends)
            date = datetime.now() - timedelta(days=day)
            is_weekend = date.weekday() >= 5
            visits_per_day = random.randint(10, 25) if is_weekend else random.randint(5, 15)
            
            for _ in range(visits_per_day):
                url, title = random.choice(sites)
                
                # Random time during the day (prefer evening hours)
                hour = random.choices(
                    range(24),
                    weights=[1,1,1,1,1,1,2,3,4,5,5,5,5,5,5,5,6,7,8,9,9,8,5,3],
                    k=1
                )[0]
                
                visit_date = date.replace(
                    hour=hour, 
                    minute=random.randint(0, 59),
                    second=random.randint(0, 59)
                )
                visit_date_us = int(visit_date.timestamp() * 1_000_000)
                
                entries.append(HistoryEntry(
                    url=url,
                    title=title,
                    visit_count=1,
                    typed=random.random() < 0.3,  # 30% typed
                    visit_type=2 if random.random() < 0.3 else 1,
                    visit_date=visit_date_us
                ))
        
        return entries
    
    # =========================================================================
    # FORM HISTORY
    # =========================================================================
    
    def inject_form_data(self, entry: FormEntry) -> bool:
        """
        Inject form autofill data into formhistory.sqlite
        
        Args:
            entry: FormEntry object
            
        Returns:
            True if successful
        """
        db_path = self.profile_path / 'formhistory.sqlite'
        
        # Calculate times
        first_used = entry.first_used or self.creation_time_us
        last_used = entry.last_used or self.now_us
        guid = str(uuid.uuid4())[:12]
        
        conn = sqlite3.connect(str(db_path))
        try:
            conn.execute("""
                INSERT OR REPLACE INTO moz_formhistory 
                (fieldname, value, timesUsed, firstUsed, lastUsed, guid)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                entry.fieldname,
                entry.value,
                entry.times_used,
                first_used,
                last_used,
                guid
            ))
            conn.commit()
            return True
        except Exception as e:
            print(f"[!] Error injecting form data: {e}")
            return False
        finally:
            conn.close()
    
    def inject_identity(self, identity: Dict[str, str]) -> int:
        """
        Inject identity data as form autofill entries.
        
        Args:
            identity: Dictionary with keys like 'first_name', 'email', etc.
            
        Returns:
            Count of successful injections
        """
        FIELD_MAPPINGS = {
            'first_name': ['first_name', 'firstname', 'fname', 'given-name'],
            'last_name': ['last_name', 'lastname', 'lname', 'family-name'],
            'email': ['email', 'e-mail', 'emailaddress'],
            'phone': ['phone', 'telephone', 'tel', 'mobile'],
            'address': ['address', 'street', 'address1', 'street-address'],
            'city': ['city', 'locality'],
            'state': ['state', 'region', 'province'],
            'zip': ['zip', 'zipcode', 'postal', 'postal-code', 'postalcode'],
            'country': ['country', 'country-name'],
            'cc_name': ['ccname', 'cc-name', 'cardname'],
        }
        
        success = 0
        for field, value in identity.items():
            if field in FIELD_MAPPINGS:
                for variant in FIELD_MAPPINGS[field]:
                    entry = FormEntry(fieldname=variant, value=value, times_used=random.randint(3, 10))
                    if self.inject_form_data(entry):
                        success += 1
        
        return success
    
    # =========================================================================
    # LOCAL STORAGE
    # =========================================================================
    
    def inject_local_storage(self, entry: LocalStorageEntry) -> bool:
        """
        Inject localStorage data into webappsstore.sqlite
        
        Args:
            entry: LocalStorageEntry object
            
        Returns:
            True if successful
        """
        db_path = self.profile_path / 'webappsstore.sqlite'
        
        # Parse origin and create reversed domain
        parsed = urlparse(entry.origin)
        domain = parsed.netloc.split(':')[0]
        port = parsed.port or (443 if parsed.scheme == 'https' else 80)
        
        reversed_domain = '.'.join(reversed(domain.split('.'))) + '.'
        origin_key = f"{reversed_domain}:{parsed.scheme}:{port}"
        scope = f"{parsed.scheme}://{domain}"
        
        conn = sqlite3.connect(str(db_path))
        try:
            conn.execute("""
                INSERT OR REPLACE INTO webappsstore2 
                (originAttributes, originKey, scope, key, value)
                VALUES ('', ?, ?, ?, ?)
            """, (origin_key, scope, entry.key, entry.value))
            conn.commit()
            return True
        except Exception as e:
            print(f"[!] Error injecting localStorage: {e}")
            return False
        finally:
            conn.close()
    
    # =========================================================================
    # PROFILE AGING
    # =========================================================================
    
    def age_profile(self) -> bool:
        """
        Backdate profile creation time in times.json
        
        Returns:
            True if successful
        """
        times_path = self.profile_path / 'times.json'
        
        try:
            if times_path.exists():
                with open(times_path) as f:
                    times = json.load(f)
            else:
                times = {}
            
            times['created'] = self.creation_time_ms
            times['firstUse'] = self.creation_time_ms
            
            with open(times_path, 'w') as f:
                json.dump(times, f)
            
            return True
        except Exception as e:
            print(f"[!] Error aging profile: {e}")
            return False
    
    # =========================================================================
    # SESSION STORE
    # =========================================================================
    
    def read_session_store(self) -> Optional[Dict]:
        """Read sessionstore.jsonlz4"""
        if not HAS_LZ4:
            print("[!] lz4 module not installed")
            return None
        
        session_path = self.profile_path / 'sessionstore.jsonlz4'
        if not session_path.exists():
            return None
        
        try:
            with open(session_path, 'rb') as f:
                magic = f.read(8)
                if magic != b'mozLz40\0':
                    return None
                
                size = struct.unpack('<I', f.read(4))[0]
                compressed = f.read()
                decompressed = lz4.block.decompress(compressed, uncompressed_size=size)
                return json.loads(decompressed)
        except Exception as e:
            print(f"[!] Error reading session store: {e}")
            return None
    
    def write_session_store(self, session_data: Dict) -> bool:
        """Write sessionstore.jsonlz4"""
        if not HAS_LZ4:
            print("[!] lz4 module not installed")
            return False
        
        session_path = self.profile_path / 'sessionstore.jsonlz4'
        
        try:
            json_bytes = json.dumps(session_data).encode('utf-8')
            compressed = lz4.block.compress(json_bytes)
            
            with open(session_path, 'wb') as f:
                f.write(b'mozLz40\0')
                f.write(struct.pack('<I', len(json_bytes)))
                f.write(compressed)
            
            return True
        except Exception as e:
            print(f"[!] Error writing session store: {e}")
            return False
    
    # =========================================================================
    # COMPLETE PROFILE INJECTION
    # =========================================================================
    
    def inject_complete_profile(self, 
                                 identity: Dict[str, str],
                                 commerce_cookies: List[CookieEntry],
                                 local_storage: List[LocalStorageEntry] = None,
                                 persona: str = 'general',
                                 target_url: str = None) -> Dict[str, int]:
        """
        Perform complete profile injection.
        
        Args:
            identity: Identity data dictionary
            commerce_cookies: List of commerce trust cookies
            local_storage: List of localStorage entries
            persona: Browsing persona type
            target_url: Target URL to include in history
            
        Returns:
            Dictionary with injection statistics
        """
        stats = {
            'profile_aged': False,
            'cookies_injected': 0,
            'history_injected': 0,
            'forms_injected': 0,
            'local_storage_injected': 0
        }
        
        # 1. Age the profile
        stats['profile_aged'] = self.age_profile()
        
        # 2. Inject commerce cookies
        stats['cookies_injected'] = self.inject_cookies_batch(commerce_cookies)
        
        # 3. Generate and inject browsing history
        history = self.generate_browsing_history(persona=persona)
        
        # Add target URL visits
        if target_url:
            for day in range(14, 0, -1):  # Last 2 weeks
                visit_date = (datetime.now() - timedelta(days=day))
                visit_date_us = int(visit_date.timestamp() * 1_000_000)
                history.append(HistoryEntry(
                    url=target_url,
                    title='Target Site',
                    visit_type=2,
                    visit_date=visit_date_us
                ))
        
        stats['history_injected'] = self.inject_history_batch(history)
        
        # 4. Inject identity as form data
        stats['forms_injected'] = self.inject_identity(identity)
        
        # 5. Inject localStorage
        if local_storage:
            for entry in local_storage:
                if self.inject_local_storage(entry):
                    stats['local_storage_injected'] += 1
        
        return stats


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def create_stripe_cookies(profile_uuid: str, aging_days: int = 90) -> List[CookieEntry]:
    """Generate Stripe commerce trust cookies"""
    creation_time = int((time.time() - aging_days * 86400) * 1_000_000)
    
    # Generate deterministic device ID from profile UUID
    device_hash = hashlib.sha256(f"stripe:device:{profile_uuid}".encode()).hexdigest()[:16]
    timestamp = int((time.time() - aging_days * 86400) * 1000)
    
    mid_value = f"v3|{timestamp}|{device_hash}"
    
    return [
        CookieEntry(
            name='__stripe_mid',
            value=mid_value,
            host='.stripe.com',
            creation_time=creation_time
        ),
        CookieEntry(
            name='__stripe_sid',
            value=f"v2|{hashlib.sha256(profile_uuid.encode()).hexdigest()[:24]}",
            host='.stripe.com'
        )
    ]


def create_adyen_cookies(profile_uuid: str, aging_days: int = 90) -> List[CookieEntry]:
    """Generate Adyen commerce trust cookies"""
    creation_time = int((time.time() - aging_days * 86400) * 1_000_000)
    
    device_id = hashlib.sha256(f"adyen:device:{profile_uuid}".encode()).hexdigest()[:12]
    timestamp = hex(int(time.time() - aging_days * 86400))[2:]
    
    return [
        CookieEntry(
            name='_RP_UID',
            value=f"{device_id}-{timestamp}-{uuid.uuid4().hex[:8]}",
            host='.adyen.com',
            http_only=True,
            same_site=1,
            creation_time=creation_time
        )
    ]


def create_paypal_cookies(profile_uuid: str, aging_days: int = 90) -> List[CookieEntry]:
    """Generate PayPal commerce trust cookies"""
    creation_time = int((time.time() - aging_days * 86400) * 1_000_000)
    
    id_part = hashlib.sha256(profile_uuid.encode()).hexdigest()[:32]
    timestamp = hex(int(time.time() - aging_days * 86400))[2:]
    
    return [
        CookieEntry(
            name='TLTSID',
            value=f"{id_part}:{timestamp}",
            host='.paypal.com',
            http_only=True,
            same_site=1,
            creation_time=creation_time
        )
    ]


# =============================================================================
# MAIN / TESTING
# =============================================================================

if __name__ == '__main__':
    import sys
    
    print("="*70)
    print("FIREFOX PROFILE INJECTOR - TITAN V7.0.0")
    print("="*70)
    
    # Test with a sample profile
    if len(sys.argv) > 1:
        profile_path = sys.argv[1]
    else:
        # Find default Firefox profile
        import os
        appdata = os.environ.get('APPDATA', '')
        profiles_dir = Path(appdata) / 'Mozilla' / 'Firefox' / 'Profiles'
        
        if profiles_dir.exists():
            for p in profiles_dir.iterdir():
                if p.is_dir() and 'default' in p.name.lower():
                    profile_path = str(p)
                    break
            else:
                print("[!] No Firefox profile found")
                sys.exit(1)
        else:
            print("[!] Firefox profiles directory not found")
            sys.exit(1)
    
    print(f"\n[*] Profile: {profile_path}")
    
    # Create injector
    injector = FirefoxProfileInjector(profile_path, aging_days=90)
    
    # Test identity
    test_identity = {
        'first_name': 'John',
        'last_name': 'Smith',
        'email': 'john.smith@gmail.com',
        'phone': '+1-212-555-0123',
        'address': '123 Main Street',
        'city': 'New York',
        'state': 'NY',
        'zip': '10001',
    }
    
    # Generate commerce cookies
    profile_uuid = str(uuid.uuid4())
    commerce_cookies = []
    commerce_cookies.extend(create_stripe_cookies(profile_uuid, 90))
    commerce_cookies.extend(create_adyen_cookies(profile_uuid, 90))
    commerce_cookies.extend(create_paypal_cookies(profile_uuid, 90))
    
    print(f"\n[*] Generated {len(commerce_cookies)} commerce cookies")
    
    # Perform injection (dry run - just show stats)
    print("\n[*] Injection capabilities ready:")
    print(f"    - Profile aging: {injector.aging_days} days")
    print(f"    - Commerce cookies: {len(commerce_cookies)}")
    print(f"    - Identity fields: {len(test_identity)}")
    print(f"    - History generation: {injector.aging_days * 10} estimated entries")
    
    print("\n[+] Firefox Profile Injector ready for deployment")
