#!/usr/bin/env python3
"""
FIREFOX PROFILE INJECTOR v2.0 - LSNG EDITION
=============================================
Full implementation based on Firefox Profile Storage Research Guide.

Implements:
- Mozilla 64-bit URL hash algorithm
- PRTime microsecond timestamps
- rev_host reversed hostname format
- GUID generation (12-char URL-safe Base64)
- LSNG (Local Storage Next Generation) with Snappy compression
- Origin sanitization algorithm
- originAttributes cookie partitioning
- Natural visit_type distribution
- Quota Manager .metadata-v2 files

Author: LUCID EMPIRE
Version: 8.1.0-TITAN
"""

import sqlite3
import json
import time
import uuid
import struct
import random
import hashlib
import os
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from urllib.parse import urlparse
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import string

try:
    import snappy
    HAS_SNAPPY = True
except ImportError:
    HAS_SNAPPY = False

try:
    import lz4.block
    HAS_LZ4 = True
except ImportError:
    HAS_LZ4 = False


# =============================================================================
# MOZILLA URL HASH ALGORITHM
# =============================================================================

def mozilla_url_hash(url: str) -> int:
    """
    Calculate Mozilla's 64-bit URL hash for places.sqlite.
    
    This is a Python implementation of the hash function used in Firefox's
    HashFunctions.h. The hash is used as a primary lookup key in moz_places.
    
    Args:
        url: The normalized URL string
        
    Returns:
        64-bit integer hash value
    """
    # Mozilla uses a variant of the DJB2 hash algorithm
    # Constants from Mozilla source
    GOLDEN_RATIO = 0x9E3779B9
    
    h = 0
    for char in url.encode('utf-8'):
        h = ((h << 5) - h + char) & 0xFFFFFFFFFFFFFFFF  # 64-bit mask
    
    # Mix the hash
    h ^= (h >> 33)
    h = (h * 0xFF51AFD7ED558CCD) & 0xFFFFFFFFFFFFFFFF
    h ^= (h >> 33)
    h = (h * 0xC4CEB9FE1A85EC53) & 0xFFFFFFFFFFFFFFFF
    h ^= (h >> 33)
    
    # Return as signed 64-bit (SQLite INTEGER)
    if h >= 0x8000000000000000:
        h -= 0x10000000000000000
    
    return h


def mozilla_url_hash_v2(url: str) -> int:
    """
    Alternative hash using AddToHash pattern from Mozilla.
    More accurate to Firefox 50+ implementation.
    """
    def rotate_left(val, bits, width=64):
        mask = (1 << width) - 1
        return ((val << bits) | (val >> (width - bits))) & mask
    
    h = 0
    for byte in url.encode('utf-8'):
        h = rotate_left(h, 5)
        h = (h ^ byte) & 0xFFFFFFFFFFFFFFFF
    
    # Return as signed
    if h >= 0x8000000000000000:
        h -= 0x10000000000000000
    
    return h


# =============================================================================
# GUID GENERATION
# =============================================================================

# URL-safe Base64 alphabet for Firefox GUIDs
GUID_ALPHABET = string.ascii_lowercase + string.ascii_uppercase + string.digits + '-_'

def generate_firefox_guid(seed: int = None) -> str:
    """
    Generate a 12-character URL-safe Base64 GUID for Firefox.
    
    Firefox uses a specialized format: 12 characters from the alphabet
    [a-zA-Z0-9-_] providing 72 bits of entropy.
    
    Args:
        seed: Optional seed for reproducible GUIDs
        
    Returns:
        12-character GUID string
    """
    if seed is not None:
        rng = random.Random(seed)
    else:
        rng = random.Random()
    
    return ''.join(rng.choice(GUID_ALPHABET) for _ in range(12))


# =============================================================================
# REV_HOST GENERATION
# =============================================================================

def generate_rev_host(hostname: str) -> str:
    """
    Generate reversed hostname for moz_places.rev_host.
    
    Firefox stores hostnames in reverse order with a trailing dot
    to enable efficient B-Tree index prefix searches.
    
    Example: google.com -> moc.elgoog.
    
    Args:
        hostname: The hostname (without protocol)
        
    Returns:
        Reversed hostname with trailing dot
    """
    # Remove any port number
    if ':' in hostname:
        hostname = hostname.split(':')[0]
    
    # Split by dots and reverse
    parts = hostname.split('.')
    reversed_parts = '.'.join(reversed(parts))
    
    # Add trailing dot
    return reversed_parts + '.'


# =============================================================================
# PRTIME CONVERSION
# =============================================================================

def to_prtime(dt: datetime = None, unix_timestamp: float = None) -> int:
    """
    Convert datetime or Unix timestamp to PRTime (microseconds since epoch).
    
    Firefox uses NSPR PRTime format: microseconds since 1970-01-01 00:00:00 UTC.
    
    Args:
        dt: datetime object (optional)
        unix_timestamp: Unix timestamp in seconds (optional)
        
    Returns:
        PRTime value (microseconds)
    """
    if dt is not None:
        return int(dt.timestamp() * 1_000_000)
    elif unix_timestamp is not None:
        return int(unix_timestamp * 1_000_000)
    else:
        return int(time.time() * 1_000_000)


def from_prtime(prtime: int) -> datetime:
    """
    Convert PRTime to datetime object.
    
    Args:
        prtime: PRTime value in microseconds
        
    Returns:
        datetime object
    """
    return datetime.fromtimestamp(prtime / 1_000_000)


# =============================================================================
# ORIGIN SANITIZATION (LSNG)
# =============================================================================

def sanitize_origin(url: str) -> str:
    """
    Sanitize origin URL to LSNG directory name format.
    
    Firefox replaces special characters with '+' for filesystem safety.
    Format: protocol+++hostname[+port]
    
    Examples:
        https://www.google.com -> https+++www.google.com
        http://localhost:8080 -> http+++localhost+8080
        
    Args:
        url: Full URL or origin
        
    Returns:
        Sanitized directory name
    """
    parsed = urlparse(url)
    scheme = parsed.scheme or 'https'
    host = parsed.netloc or parsed.path.split('/')[0]
    
    # Handle port
    if ':' in host:
        host_part, port = host.rsplit(':', 1)
        sanitized = f"{scheme}+++{host_part}+{port}"
    else:
        sanitized = f"{scheme}+++{host}"
    
    return sanitized


def desanitize_origin(folder_name: str) -> str:
    """
    Convert sanitized folder name back to origin URL.
    
    Args:
        folder_name: Sanitized directory name
        
    Returns:
        Original URL
    """
    # Split scheme and rest
    parts = folder_name.split('+++', 1)
    if len(parts) != 2:
        return folder_name
    
    scheme, rest = parts
    
    # Check for port (last + followed by digits)
    if '+' in rest:
        # Could be port or just part of the hostname
        last_plus = rest.rfind('+')
        potential_port = rest[last_plus + 1:]
        if potential_port.isdigit():
            host = rest[:last_plus]
            port = potential_port
            return f"{scheme}://{host}:{port}"
    
    return f"{scheme}://{rest}"


# =============================================================================
# SNAPPY COMPRESSION FOR LSNG
# =============================================================================

def compress_value_snappy(value: str) -> Tuple[bytes, int]:
    """
    Compress a value using Snappy for LSNG data.sqlite.
    
    Args:
        value: String value to compress
        
    Returns:
        Tuple of (compressed_bytes, compression_type)
        compression_type: 0=uncompressed, 1=snappy
    """
    value_bytes = value.encode('utf-8')
    
    if HAS_SNAPPY and len(value_bytes) > 64:  # Only compress if > 64 bytes
        try:
            compressed = snappy.compress(value_bytes)
            if len(compressed) < len(value_bytes):
                return compressed, 1  # Snappy compressed
        except:
            pass
    
    return value_bytes, 0  # Uncompressed


def decompress_value_snappy(blob: bytes, compression_type: int) -> str:
    """
    Decompress a value from LSNG data.sqlite.
    
    Args:
        blob: Binary blob from database
        compression_type: 0=uncompressed, 1=snappy
        
    Returns:
        Decompressed string value
    """
    if compression_type == 1 and HAS_SNAPPY:
        try:
            decompressed = snappy.decompress(blob)
            return decompressed.decode('utf-8')
        except:
            pass
    
    return blob.decode('utf-8')


# =============================================================================
# STRUCTURED CLONE ENCODING (Simplified)
# =============================================================================

def encode_structured_clone(value: str) -> bytes:
    """
    Encode a string value in a simplified Structured Clone format.
    
    Note: Full Structured Clone is complex. This is a simplified version
    that works for string values (most common in LocalStorage).
    
    Args:
        value: String value to encode
        
    Returns:
        Structured Clone encoded bytes
    """
    # Simplified: Just UTF-16LE encode with a header
    # Real Structured Clone has a more complex binary format
    value_bytes = value.encode('utf-16-le')
    
    # Simple header: 4 bytes length + data
    header = struct.pack('<I', len(value))
    
    return header + value_bytes


def decode_structured_clone(data: bytes) -> str:
    """
    Decode a Structured Clone encoded string.
    
    Args:
        data: Structured Clone encoded bytes
        
    Returns:
        Decoded string
    """
    try:
        # Try to read as simple header + UTF-16LE
        length = struct.unpack('<I', data[:4])[0]
        value_bytes = data[4:4 + length * 2]
        return value_bytes.decode('utf-16-le')
    except:
        # Fallback: try as plain UTF-8
        return data.decode('utf-8', errors='replace')


# =============================================================================
# VISIT TYPE DISTRIBUTION
# =============================================================================

class VisitTypeDistribution:
    """
    Generates realistic visit_type distributions for history injection.
    
    Anti-fraud systems analyze the ratio of visit types to detect bots.
    A natural distribution should have mostly link clicks (type 1),
    some typed URLs (type 2), and occasional bookmarks/reloads.
    """
    
    # Visit type constants
    TRANSITION_LINK = 1
    TRANSITION_TYPED = 2
    TRANSITION_BOOKMARK = 3
    TRANSITION_EMBED = 4
    TRANSITION_REDIRECT_PERMANENT = 5
    TRANSITION_REDIRECT_TEMPORARY = 6
    TRANSITION_DOWNLOAD = 7
    TRANSITION_FRAMED_LINK = 8
    TRANSITION_RELOAD = 9
    
    # Natural distribution weights (based on typical user behavior)
    DISTRIBUTION = {
        TRANSITION_LINK: 65,           # 65% - clicking links
        TRANSITION_TYPED: 15,          # 15% - typing URLs
        TRANSITION_BOOKMARK: 5,        # 5% - from bookmarks
        TRANSITION_EMBED: 3,           # 3% - embedded content
        TRANSITION_REDIRECT_PERMANENT: 4,  # 4% - 301 redirects
        TRANSITION_REDIRECT_TEMPORARY: 4,  # 4% - 302 redirects
        TRANSITION_DOWNLOAD: 1,        # 1% - downloads
        TRANSITION_FRAMED_LINK: 2,     # 2% - framed links
        TRANSITION_RELOAD: 1,          # 1% - reloads
    }
    
    def __init__(self, seed: int = None):
        self.rng = random.Random(seed)
        
        # Build weighted list
        self._types = []
        self._weights = []
        for visit_type, weight in self.DISTRIBUTION.items():
            self._types.append(visit_type)
            self._weights.append(weight)
    
    def get_visit_type(self, is_first_visit: bool = False, 
                       is_typed_url: bool = False) -> int:
        """
        Get a visit type for a history entry.
        
        Args:
            is_first_visit: True if first visit to this URL (favors typed/link)
            is_typed_url: True if user explicitly typed this URL
            
        Returns:
            Visit type integer
        """
        if is_typed_url:
            return self.TRANSITION_TYPED
        
        if is_first_visit:
            # First visits are usually link clicks or typed
            return self.rng.choices(
                [self.TRANSITION_LINK, self.TRANSITION_TYPED],
                weights=[80, 20]
            )[0]
        
        return self.rng.choices(self._types, weights=self._weights)[0]
    
    def generate_visit_chain(self, length: int) -> List[int]:
        """
        Generate a realistic chain of visit types.
        
        Args:
            length: Number of visits in the chain
            
        Returns:
            List of visit types
        """
        chain = []
        for i in range(length):
            chain.append(self.get_visit_type(is_first_visit=(i == 0)))
        return chain


# =============================================================================
# QUOTA MANAGER METADATA
# =============================================================================

def create_metadata_v2(origin: str, creation_time: int = None) -> bytes:
    """
    Create .metadata-v2 file content for Quota Manager.
    
    Without this file, Firefox considers the storage directory corrupt.
    
    Args:
        origin: The origin URL
        creation_time: PRTime creation timestamp
        
    Returns:
        Binary content for .metadata-v2 file
    """
    if creation_time is None:
        creation_time = to_prtime()
    
    # .metadata-v2 format (based on Firefox source)
    # 8 bytes: creation time (PRTime)
    # 4 bytes: flags (usually 0)
    # Rest: origin string (null-terminated)
    
    data = struct.pack('<Q', creation_time)  # 8 bytes: creation time
    data += struct.pack('<I', 0)  # 4 bytes: flags
    data += origin.encode('utf-8') + b'\x00'  # null-terminated origin
    
    return data


def create_metadata_files(storage_path: Path, origin: str, 
                          creation_time: int = None):
    """
    Create all required metadata files for a storage origin.
    
    Args:
        storage_path: Path to the origin's storage directory
        origin: The origin URL
        creation_time: PRTime creation timestamp
    """
    storage_path.mkdir(parents=True, exist_ok=True)
    
    # Create .metadata-v2
    metadata_content = create_metadata_v2(origin, creation_time)
    (storage_path / '.metadata-v2').write_bytes(metadata_content)
    
    # Create .metadata (older format, some Firefox versions check this)
    (storage_path / '.metadata').write_bytes(metadata_content[:12])


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class CookieEntry:
    """Cookie entry with full Firefox schema support."""
    name: str
    value: str
    host: str
    path: str = "/"
    expiry: Optional[int] = None  # Unix seconds
    secure: bool = True
    http_only: bool = False
    same_site: int = 0  # 0=Unset, 1=Lax, 2=Strict, 3=None
    raw_same_site: int = 0
    creation_time: Optional[int] = None  # PRTime (microseconds)
    last_accessed: Optional[int] = None  # PRTime (microseconds)
    base_domain: Optional[str] = None
    origin_attributes: str = ''  # For container/partitioning
    in_browser_element: int = 0


@dataclass
class HistoryEntry:
    """History entry with full Firefox schema support."""
    url: str
    title: str
    visit_count: int = 1
    typed: bool = False
    hidden: bool = False
    frecency: int = 100
    visit_type: int = 1
    visit_date: Optional[int] = None  # PRTime
    from_visit: int = 0
    session: int = 0


@dataclass
class LocalStorageEntry:
    """LSNG Local Storage entry."""
    origin: str  # Full URL: https://example.com
    key: str
    value: str
    partition_key: Optional[str] = None  # For State Partitioning


# =============================================================================
# FIREFOX PROFILE INJECTOR v2
# =============================================================================

class FirefoxProfileInjectorV2:
    """
    Advanced Firefox profile injector implementing full LSNG support.
    
    Based on Firefox Profile Storage Research Guide specifications.
    """
    
    def __init__(self, profile_path: str, aging_days: int = 90):
        """
        Initialize the injector.
        
        Args:
            profile_path: Path to Firefox profile directory
            aging_days: Number of days to backdate artifacts
        """
        self.profile_path = Path(profile_path)
        self.aging_days = aging_days
        
        # Time references
        self.now = datetime.now()
        self.creation_date = self.now - timedelta(days=aging_days)
        
        # PRTime values
        self.now_prtime = to_prtime(self.now)
        self.creation_prtime = to_prtime(self.creation_date)
        
        # Unix timestamps
        self.now_unix = int(self.now.timestamp())
        self.creation_unix = int(self.creation_date.timestamp())
        
        # Helpers
        self.visit_distribution = VisitTypeDistribution()
        
        # Validate profile
        if not self.profile_path.exists():
            self.profile_path.mkdir(parents=True)
    
    # =========================================================================
    # COOKIES (cookies.sqlite)
    # =========================================================================
    
    def inject_cookie(self, cookie: CookieEntry) -> bool:
        """
        Inject a cookie into cookies.sqlite with full schema support.
        """
        db_path = self.profile_path / 'cookies.sqlite'
        
        # Calculate baseDomain from host
        base_domain = cookie.base_domain
        if not base_domain:
            host = cookie.host.lstrip('.')
            parts = host.split('.')
            if len(parts) >= 2:
                base_domain = '.'.join(parts[-2:])
            else:
                base_domain = host
        
        # Calculate timestamps
        creation_time = cookie.creation_time or self.creation_prtime
        last_accessed = cookie.last_accessed or self.now_prtime
        expiry = cookie.expiry or (self.now_unix + 365 * 86400)
        
        conn = sqlite3.connect(str(db_path))
        try:
            # Create table if needed (with full schema)
            conn.execute('''
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
                    CONSTRAINT moz_uniqueid UNIQUE (name, host, path, originAttributes)
                )
            ''')
            
            conn.execute('''
                INSERT OR REPLACE INTO moz_cookies 
                (baseDomain, originAttributes, name, value, host, path,
                 expiry, lastAccessed, creationTime, isSecure, isHttpOnly,
                 inBrowserElement, sameSite, rawSameSite)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                base_domain,
                cookie.origin_attributes,
                cookie.name,
                cookie.value,
                cookie.host,
                cookie.path,
                expiry,
                last_accessed,
                creation_time,
                int(cookie.secure),
                int(cookie.http_only),
                cookie.in_browser_element,
                cookie.same_site,
                cookie.raw_same_site
            ))
            
            conn.commit()
            return True
            
        except Exception as e:
            print(f"[!] Cookie injection error: {e}")
            return False
        finally:
            conn.close()
    
    # =========================================================================
    # HISTORY (places.sqlite)
    # =========================================================================
    
    def inject_history(self, entry: HistoryEntry) -> Optional[int]:
        """
        Inject history entry with proper url_hash and rev_host.
        """
        db_path = self.profile_path / 'places.sqlite'
        
        # Parse URL
        parsed = urlparse(entry.url)
        hostname = parsed.netloc
        
        # Generate rev_host
        rev_host = generate_rev_host(hostname)
        
        # Generate url_hash
        url_hash = mozilla_url_hash(entry.url)
        
        # Generate GUID
        guid = generate_firefox_guid()
        
        # Calculate visit date
        visit_date = entry.visit_date or self.now_prtime
        
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        try:
            # Ensure tables exist
            self._ensure_places_tables(conn)
            
            # Check if URL exists
            cursor.execute("SELECT id, visit_count FROM moz_places WHERE url_hash = ? AND url = ?", 
                          (url_hash, entry.url))
            existing = cursor.fetchone()
            
            if existing:
                place_id = existing[0]
                new_count = existing[1] + entry.visit_count
                cursor.execute('''
                    UPDATE moz_places 
                    SET visit_count = ?, last_visit_date = ?, frecency = frecency + 10
                    WHERE id = ?
                ''', (new_count, visit_date, place_id))
            else:
                cursor.execute('''
                    INSERT INTO moz_places 
                    (url, title, rev_host, visit_count, hidden, typed, frecency,
                     last_visit_date, guid, url_hash, foreign_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                ''', (
                    entry.url,
                    entry.title,
                    rev_host,
                    entry.visit_count,
                    int(entry.hidden),
                    int(entry.typed),
                    entry.frecency,
                    visit_date,
                    guid,
                    url_hash
                ))
                place_id = cursor.lastrowid
            
            # Insert visit record
            cursor.execute('''
                INSERT INTO moz_historyvisits 
                (from_visit, place_id, visit_date, visit_type, session)
                VALUES (?, ?, ?, ?, ?)
            ''', (entry.from_visit, place_id, visit_date, entry.visit_type, entry.session))
            
            conn.commit()
            return place_id
            
        except Exception as e:
            print(f"[!] History injection error: {e}")
            conn.rollback()
            return None
        finally:
            conn.close()
    
    def _ensure_places_tables(self, conn: sqlite3.Connection):
        """Ensure places.sqlite tables exist with correct schema."""
        conn.execute('''
            CREATE TABLE IF NOT EXISTS moz_places (
                id INTEGER PRIMARY KEY,
                url LONGVARCHAR,
                title LONGVARCHAR,
                rev_host LONGVARCHAR,
                visit_count INTEGER DEFAULT 0,
                hidden INTEGER DEFAULT 0 NOT NULL,
                typed INTEGER DEFAULT 0 NOT NULL,
                frecency INTEGER DEFAULT -1 NOT NULL,
                last_visit_date INTEGER,
                guid TEXT,
                foreign_count INTEGER DEFAULT 0 NOT NULL,
                url_hash INTEGER DEFAULT 0 NOT NULL
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS moz_historyvisits (
                id INTEGER PRIMARY KEY,
                from_visit INTEGER,
                place_id INTEGER,
                visit_date INTEGER,
                visit_type INTEGER,
                session INTEGER
            )
        ''')
        
        # Create indexes
        try:
            conn.execute('CREATE INDEX IF NOT EXISTS moz_places_url_hashindex ON moz_places(url_hash)')
            conn.execute('CREATE INDEX IF NOT EXISTS moz_places_hostindex ON moz_places(rev_host)')
        except:
            pass
    
    # =========================================================================
    # LSNG LOCAL STORAGE
    # =========================================================================
    
    def inject_local_storage(self, entry: LocalStorageEntry) -> bool:
        """
        Inject data into LSNG storage/default/ structure.
        """
        # Sanitize origin to folder name
        folder_name = sanitize_origin(entry.origin)
        
        # Add partition key if present
        if entry.partition_key:
            folder_name += f"^partitionKey=({entry.partition_key})"
        
        # Create directory structure
        storage_path = self.profile_path / 'storage' / 'default' / folder_name
        ls_path = storage_path / 'ls'
        ls_path.mkdir(parents=True, exist_ok=True)
        
        # Create metadata files
        create_metadata_files(storage_path, entry.origin, self.creation_prtime)
        
        # Create/update data.sqlite
        db_path = ls_path / 'data.sqlite'
        
        try:
            # Compress value
            value_blob, compression_type = compress_value_snappy(entry.value)
            utf16_length = len(entry.value)
            
            conn = sqlite3.connect(str(db_path))
            
            # Create table with LSNG schema
            conn.execute('''
                CREATE TABLE IF NOT EXISTS data (
                    key TEXT PRIMARY KEY,
                    utf16_length INTEGER NOT NULL DEFAULT 0,
                    conversion_type INTEGER NOT NULL DEFAULT 0,
                    compression_type INTEGER NOT NULL DEFAULT 0,
                    value BLOB,
                    last_vacuum_size INTEGER NOT NULL DEFAULT 0
                )
            ''')
            
            conn.execute('''
                INSERT OR REPLACE INTO data 
                (key, utf16_length, conversion_type, compression_type, value, last_vacuum_size)
                VALUES (?, ?, 0, ?, ?, 0)
            ''', (entry.key, utf16_length, compression_type, value_blob))
            
            conn.commit()
            conn.close()
            
            # Create usage file
            (ls_path / 'usage').write_text(str(len(value_blob)))
            
            return True
            
        except Exception as e:
            print(f"[!] LocalStorage injection error: {e}")
            return False
    
    # =========================================================================
    # PROFILE AGING
    # =========================================================================
    
    def age_profile(self) -> bool:
        """
        Backdate profile creation time in times.json.
        """
        times_path = self.profile_path / 'times.json'
        
        try:
            # Creation time in milliseconds
            creation_ms = int(self.creation_date.timestamp() * 1000)
            
            times_data = {
                'created': creation_ms,
                'firstUse': creation_ms
            }
            
            with open(times_path, 'w') as f:
                json.dump(times_data, f)
            
            return True
            
        except Exception as e:
            print(f"[!] Profile aging error: {e}")
            return False
    
    # =========================================================================
    # BULK GENERATION
    # =========================================================================
    
    def generate_realistic_history(self, days: int = None,
                                    sites: List[Tuple[str, str]] = None,
                                    persona: str = 'general') -> int:
        """
        Generate realistic browsing history with natural visit type distribution.
        
        Args:
            days: Number of days of history
            sites: List of (url, title) tuples
            persona: Browsing persona
            
        Returns:
            Number of history entries injected
        """
        days = days or self.aging_days
        
        DEFAULT_SITES = {
            'general': [
                ('https://www.google.com/search?q=news', 'news - Google Search'),
                ('https://www.youtube.com', 'YouTube'),
                ('https://www.reddit.com', 'Reddit'),
                ('https://twitter.com', 'Twitter'),
                ('https://www.amazon.com', 'Amazon'),
                ('https://www.facebook.com', 'Facebook'),
                ('https://www.instagram.com', 'Instagram'),
                ('https://www.linkedin.com', 'LinkedIn'),
                ('https://www.wikipedia.org', 'Wikipedia'),
                ('https://www.netflix.com', 'Netflix'),
            ],
            'developer': [
                ('https://github.com', 'GitHub'),
                ('https://stackoverflow.com', 'Stack Overflow'),
                ('https://developer.mozilla.org', 'MDN Web Docs'),
                ('https://docs.python.org', 'Python Documentation'),
                ('https://news.ycombinator.com', 'Hacker News'),
            ],
            'shopper': [
                ('https://www.amazon.com', 'Amazon'),
                ('https://www.ebay.com', 'eBay'),
                ('https://www.walmart.com', 'Walmart'),
                ('https://www.target.com', 'Target'),
                ('https://www.bestbuy.com', 'Best Buy'),
            ]
        }
        
        sites = sites or (DEFAULT_SITES.get(persona, []) + DEFAULT_SITES['general'])
        
        count = 0
        session_id = random.randint(1, 1000000)
        
        for day in range(days, 0, -1):
            date = self.now - timedelta(days=day)
            
            # Visits per day (more on weekends)
            is_weekend = date.weekday() >= 5
            daily_visits = random.randint(15, 30) if is_weekend else random.randint(5, 15)
            
            # New session each day
            session_id = random.randint(1, 1000000)
            previous_place_id = 0
            
            for _ in range(daily_visits):
                url, title = random.choice(sites)
                
                # Random time during waking hours
                hour = random.choices(
                    range(24),
                    weights=[1,1,1,1,1,1,2,3,5,6,6,6,6,6,6,6,7,8,9,9,8,6,4,2],
                    k=1
                )[0]
                
                visit_time = date.replace(
                    hour=hour,
                    minute=random.randint(0, 59),
                    second=random.randint(0, 59)
                )
                
                # Get natural visit type
                visit_type = self.visit_distribution.get_visit_type(
                    is_first_visit=(previous_place_id == 0)
                )
                
                entry = HistoryEntry(
                    url=url,
                    title=title,
                    visit_type=visit_type,
                    visit_date=to_prtime(visit_time),
                    from_visit=previous_place_id if random.random() > 0.3 else 0,
                    session=session_id,
                    typed=(visit_type == VisitTypeDistribution.TRANSITION_TYPED)
                )
                
                place_id = self.inject_history(entry)
                if place_id:
                    count += 1
                    previous_place_id = place_id
        
        return count


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def create_commerce_cookies_v2(profile_uuid: str, aging_days: int = 90) -> List[CookieEntry]:
    """
    Create commerce trust cookies with full schema compliance.
    """
    creation_time = to_prtime(datetime.now() - timedelta(days=aging_days))
    now_time = to_prtime()
    
    cookies = []
    
    # Stripe __stripe_mid (Machine ID)
    device_hash = hashlib.sha256(f"stripe:device:{profile_uuid}".encode()).hexdigest()[:16]
    timestamp_ms = int((time.time() - aging_days * 86400) * 1000)
    
    cookies.append(CookieEntry(
        name='__stripe_mid',
        value=f"v3|{timestamp_ms}|{device_hash}",
        host='.stripe.com',
        base_domain='stripe.com',
        creation_time=creation_time,
        last_accessed=now_time,
        same_site=0,
        secure=True
    ))
    
    # Stripe __stripe_sid (Session ID)
    cookies.append(CookieEntry(
        name='__stripe_sid',
        value=f"v2|{hashlib.sha256(profile_uuid.encode()).hexdigest()[:24]}|{int(time.time())}",
        host='.stripe.com',
        base_domain='stripe.com',
        same_site=0,
        secure=True
    ))
    
    # Adyen _RP_UID
    adyen_device = hashlib.sha256(f"adyen:{profile_uuid}".encode()).hexdigest()[:12]
    adyen_ts = hex(int(time.time() - aging_days * 86400))[2:]
    
    cookies.append(CookieEntry(
        name='_RP_UID',
        value=f"{adyen_device}-{adyen_ts}-{uuid.uuid4().hex[:8]}",
        host='.adyen.com',
        base_domain='adyen.com',
        creation_time=creation_time,
        last_accessed=now_time,
        same_site=1,  # Lax
        http_only=True,
        secure=True
    ))
    
    # PayPal TLTSID
    paypal_id = hashlib.sha256(f"paypal:{profile_uuid}".encode()).hexdigest()[:32]
    
    cookies.append(CookieEntry(
        name='TLTSID',
        value=f"{paypal_id}:{adyen_ts}",
        host='.paypal.com',
        base_domain='paypal.com',
        creation_time=creation_time,
        last_accessed=now_time,
        same_site=1,
        http_only=True,
        secure=True
    ))
    
    return cookies


# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    print("="*70)
    print("FIREFOX PROFILE INJECTOR v2.0 - LSNG EDITION")
    print("Based on Firefox Profile Storage Research Guide")
    print("="*70)
    
    # Demo URL hash
    test_url = "https://www.google.com"
    url_hash = mozilla_url_hash(test_url)
    print(f"\n[URL Hash] {test_url}")
    print(f"  Hash: {url_hash}")
    
    # Demo rev_host
    rev = generate_rev_host("www.google.com")
    print(f"\n[rev_host] www.google.com -> {rev}")
    
    # Demo GUID
    guid = generate_firefox_guid()
    print(f"\n[GUID] Generated: {guid}")
    
    # Demo origin sanitization
    origin = "https://www.example.com:8080"
    sanitized = sanitize_origin(origin)
    print(f"\n[LSNG] {origin} -> {sanitized}")
    
    # Demo visit types
    dist = VisitTypeDistribution()
    visits = [dist.get_visit_type() for _ in range(100)]
    print(f"\n[Visit Types] Sample of 100:")
    for vt in range(1, 10):
        count = visits.count(vt)
        print(f"  Type {vt}: {count}%")
    
    print("\n[+] Firefox Profile Injector v2.0 ready")
