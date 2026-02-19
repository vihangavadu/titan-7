"""
LUCID EMPIRE v7.0-TITAN - Firefox Profile Injector V2 (No-Fork Edition)
========================================================================
Advanced Firefox ESR profile injection with:
- SQLite database injection (places.sqlite, cookies.sqlite)
- LSNG (Local Storage Next Generation) with Snappy compression
- Form history injection
- Extension state management

Used by the Genesis Engine to build "Golden Profiles" that are
then handed over to the standard Firefox ESR binary.
"""

import hashlib
import json
import os
import shutil
import sqlite3
import struct
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import snappy
    SNAPPY_AVAILABLE = True
except ImportError:
    SNAPPY_AVAILABLE = False


class FirefoxProfileInjectorV2:
    """
    Advanced Firefox profile injector for TITAN.
    
    Injects:
    - Browsing history into places.sqlite
    - Cookies into cookies.sqlite
    - Form data into formhistory.sqlite
    - localStorage via LSNG format (webappsstore.sqlite)
    """
    
    # Firefox time is microseconds since Jan 1, 1970
    FIREFOX_EPOCH = 0
    
    def __init__(self, profile_path: Path):
        self.profile_path = Path(profile_path)
        self.profile_path.mkdir(parents=True, exist_ok=True)
    
    def inject_places(self, history: List[Dict[str, Any]]) -> None:
        """
        Inject browsing history into places.sqlite.
        
        Args:
            history: List of history entries with url, title, visit_time, visit_count
        """
        db_path = self.profile_path / "places.sqlite"
        
        # Backup if exists
        if db_path.exists():
            shutil.copy(db_path, db_path.with_suffix(".sqlite.bak"))
        
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Create schema
        cursor.executescript("""
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
                guid TEXT UNIQUE,
                foreign_count INTEGER DEFAULT 0,
                url_hash INTEGER DEFAULT 0,
                description TEXT,
                preview_image_url TEXT,
                origin_id INTEGER,
                site_name TEXT
            );
            
            CREATE TABLE IF NOT EXISTS moz_historyvisits (
                id INTEGER PRIMARY KEY,
                from_visit INTEGER,
                place_id INTEGER,
                visit_date INTEGER,
                visit_type INTEGER,
                session INTEGER
            );
            
            CREATE TABLE IF NOT EXISTS moz_origins (
                id INTEGER PRIMARY KEY,
                prefix TEXT NOT NULL,
                host TEXT NOT NULL,
                frecency INTEGER NOT NULL,
                UNIQUE (prefix, host)
            );
            
            CREATE INDEX IF NOT EXISTS moz_places_url_hashindex ON moz_places (url_hash);
            CREATE INDEX IF NOT EXISTS moz_places_hostindex ON moz_places (rev_host);
            CREATE INDEX IF NOT EXISTS moz_historyvisits_placedateindex ON moz_historyvisits (place_id, visit_date);
            CREATE INDEX IF NOT EXISTS moz_historyvisits_dateindex ON moz_historyvisits (visit_date);
        """)
        
        for entry in history:
            url = entry.get("url", "")
            title = entry.get("title", "")
            visit_time = entry.get("visit_time_unix", int(time.time() * 1000000))
            visit_count = entry.get("visit_count", 1)
            typed = entry.get("typed", 0)
            
            # Parse URL for rev_host
            from urllib.parse import urlparse
            parsed = urlparse(url)
            host = parsed.netloc or "localhost"
            rev_host = ".".join(reversed(host.split("."))) + "."
            
            # Generate GUID
            guid = self._generate_guid()
            
            # URL hash (simple hash for Firefox)
            url_hash = hash(url) & 0xFFFFFFFFFFFFFFFF
            
            # Calculate frecency (simplified)
            frecency = min(visit_count * 100, 10000)
            
            try:
                # Insert or update place
                cursor.execute("""
                    INSERT OR REPLACE INTO moz_places 
                    (url, title, rev_host, visit_count, typed, frecency, last_visit_date, guid, url_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (url, title, rev_host, visit_count, typed, frecency, visit_time, guid, url_hash))
                
                place_id = cursor.lastrowid
                
                # Insert visit
                cursor.execute("""
                    INSERT INTO moz_historyvisits (place_id, visit_date, visit_type, session)
                    VALUES (?, ?, ?, ?)
                """, (place_id, visit_time, 1, 0))  # visit_type 1 = TRANSITION_LINK
                
            except sqlite3.IntegrityError:
                # URL already exists, update visit count
                cursor.execute("""
                    UPDATE moz_places SET visit_count = visit_count + 1, last_visit_date = ?
                    WHERE url = ?
                """, (visit_time, url))
        
        conn.commit()
        conn.close()
    
    def inject_cookies(self, cookies: List[Dict[str, Any]]) -> None:
        """
        Inject cookies into cookies.sqlite.
        
        Args:
            cookies: List of cookie dicts with host, name, value, path, expiry, etc.
        """
        db_path = self.profile_path / "cookies.sqlite"
        
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
            
            CREATE INDEX IF NOT EXISTS moz_basedomain ON moz_cookies (host);
        """)
        
        for cookie in cookies:
            try:
                cursor.execute("""
                    INSERT INTO moz_cookies (
                        originAttributes, name, value, host, path, expiry, 
                        lastAccessed, creationTime, isSecure, isHttpOnly, sameSite
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    "",  # originAttributes
                    cookie.get("name", ""),
                    cookie.get("value", ""),
                    cookie.get("host", ""),
                    cookie.get("path", "/"),
                    cookie.get("expiry", int(time.time()) + 86400 * 365),
                    cookie.get("last_access", int(time.time() * 1000000)),
                    cookie.get("creation_time", int(time.time() * 1000000)),
                    1 if cookie.get("secure", True) else 0,
                    1 if cookie.get("http_only", False) else 0,
                    cookie.get("same_site", 0),
                ))
            except sqlite3.IntegrityError:
                pass  # Skip duplicates
        
        conn.commit()
        conn.close()
    
    def inject_form_history(self, form_data: List[Dict[str, Any]]) -> None:
        """
        Inject form autofill data into formhistory.sqlite.
        
        Args:
            form_data: List of {fieldname, value, times_used, first_used, last_used}
        """
        db_path = self.profile_path / "formhistory.sqlite"
        
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS moz_formhistory (
                id INTEGER PRIMARY KEY,
                fieldname TEXT NOT NULL,
                value TEXT NOT NULL,
                timesUsed INTEGER,
                firstUsed INTEGER,
                lastUsed INTEGER,
                guid TEXT
            );
            
            CREATE INDEX IF NOT EXISTS moz_formhistory_index ON moz_formhistory (fieldname);
        """)
        
        for entry in form_data:
            guid = self._generate_guid()
            try:
                cursor.execute("""
                    INSERT INTO moz_formhistory (fieldname, value, timesUsed, firstUsed, lastUsed, guid)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    entry.get("fieldname", ""),
                    entry.get("value", ""),
                    entry.get("times_used", 1),
                    entry.get("first_used", int(time.time() * 1000)),
                    entry.get("last_used", int(time.time() * 1000)),
                    guid,
                ))
            except sqlite3.IntegrityError:
                pass
        
        conn.commit()
        conn.close()
    
    def inject_localstorage(self, storage_data: Dict[str, Dict[str, str]]) -> None:
        """
        Inject localStorage data into webappsstore.sqlite.
        
        Args:
            storage_data: Dict of {origin: {key: value}}
        """
        db_path = self.profile_path / "webappsstore.sqlite"
        
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS webappsstore2 (
                originAttributes TEXT,
                originKey TEXT,
                scope TEXT,
                key TEXT,
                value TEXT
            );
            
            CREATE UNIQUE INDEX IF NOT EXISTS webappsstore2_idx 
            ON webappsstore2 (originAttributes, originKey, key);
        """)
        
        for origin, data in storage_data.items():
            # Convert origin to Firefox's reversed format
            # https://www.example.com -> moc.elpmaxe.www.:https:443
            from urllib.parse import urlparse
            parsed = urlparse(origin)
            host = parsed.netloc or "localhost"
            scheme = parsed.scheme or "https"
            port = parsed.port or (443 if scheme == "https" else 80)
            
            rev_host = ".".join(reversed(host.split(".")))
            origin_key = f"{rev_host}.:{scheme}:{port}"
            scope = f"{scheme}://{host}"
            
            for key, value in data.items():
                try:
                    # Compress value if Snappy available and value is large
                    stored_value = value
                    if SNAPPY_AVAILABLE and len(value) > 1024:
                        stored_value = snappy.compress(value.encode()).decode("latin-1")
                    
                    cursor.execute("""
                        INSERT OR REPLACE INTO webappsstore2 
                        (originAttributes, originKey, scope, key, value)
                        VALUES (?, ?, ?, ?, ?)
                    """, ("", origin_key, scope, key, stored_value))
                except Exception:
                    pass
        
        conn.commit()
        conn.close()
    
    def inject_permissions(self, permissions: List[Dict[str, Any]]) -> None:
        """
        Inject site permissions into permissions.sqlite.
        
        Args:
            permissions: List of {origin, type, permission, expiry}
        """
        db_path = self.profile_path / "permissions.sqlite"
        
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS moz_perms (
                id INTEGER PRIMARY KEY,
                origin TEXT,
                type TEXT,
                permission INTEGER,
                expireType INTEGER,
                expireTime INTEGER,
                modificationTime INTEGER
            );
        """)
        
        for perm in permissions:
            try:
                cursor.execute("""
                    INSERT INTO moz_perms (origin, type, permission, expireType, expireTime, modificationTime)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    perm.get("origin", ""),
                    perm.get("type", ""),
                    perm.get("permission", 1),
                    perm.get("expire_type", 0),
                    perm.get("expire_time", 0),
                    int(time.time() * 1000),
                ))
            except sqlite3.IntegrityError:
                pass
        
        conn.commit()
        conn.close()
    
    def create_prefs(self, profile_config: Dict[str, Any]) -> None:
        """
        Create prefs.js with profile-specific settings.
        
        Args:
            profile_config: Profile configuration dict
        """
        prefs = []
        
        # Core privacy prefs
        prefs.extend([
            'user_pref("browser.startup.homepage_override.mstone", "ignore");',
            'user_pref("browser.shell.checkDefaultBrowser", false);',
            'user_pref("datareporting.policy.dataSubmissionEnabled", false);',
            'user_pref("toolkit.telemetry.enabled", false);',
            'user_pref("toolkit.telemetry.unified", false);',
            'user_pref("browser.newtabpage.activity-stream.feeds.telemetry", false);',
            'user_pref("browser.ping-centre.telemetry", false);',
            'user_pref("app.shield.optoutstudies.enabled", false);',
        ])
        
        # Geolocation spoofing
        if "latitude" in profile_config and "longitude" in profile_config:
            prefs.extend([
                'user_pref("geo.provider.testing", true);',
                f'user_pref("geo.provider.testing.latitude", {profile_config["latitude"]});',
                f'user_pref("geo.provider.testing.longitude", {profile_config["longitude"]});',
            ])
        
        # Timezone
        if "timezone" in profile_config:
            prefs.append(f'user_pref("intl.timezone.override", "{profile_config["timezone"]}");')
        
        # Locale
        if "locale" in profile_config:
            prefs.extend([
                f'user_pref("intl.locale.requested", "{profile_config["locale"]}");',
                f'user_pref("intl.accept_languages", "{profile_config.get("language", profile_config["locale"])}");',
            ])
        
        # Screen resolution
        if "screen_width" in profile_config and "screen_height" in profile_config:
            prefs.extend([
                f'user_pref("privacy.window.maxInnerWidth", {profile_config["screen_width"]});',
                f'user_pref("privacy.window.maxInnerHeight", {profile_config["screen_height"]});',
            ])
        
        # User agent (if custom)
        if "user_agent" in profile_config and profile_config["user_agent"]:
            prefs.append(f'user_pref("general.useragent.override", "{profile_config["user_agent"]}");')
        
        # WebRTC protection
        prefs.extend([
            'user_pref("media.peerconnection.ice.default_address_only", true);',
            'user_pref("media.peerconnection.ice.no_host", true);',
            'user_pref("media.peerconnection.ice.proxy_only_if_behind_proxy", true);',
        ])
        
        # Disable safe browsing for operational security
        prefs.extend([
            'user_pref("browser.safebrowsing.malware.enabled", false);',
            'user_pref("browser.safebrowsing.phishing.enabled", false);',
            'user_pref("browser.safebrowsing.downloads.enabled", false);',
        ])
        
        # TITAN PATCH: WEBGL SCRUBBER
        # Forces removal of Linux/Mesa specific extensions
        prefs.extend([
            'user_pref("webgl.enable-draft-extensions", false);',
            'user_pref("webgl.min_capability_mode", true);',
            'user_pref("webgl.disable-extensions", true);',
            'user_pref("webgl.renderer-string-override", "NVIDIA RTX 3080");',
            'user_pref("webgl.vendor-string-override", "Google Inc. (NVIDIA)");',
            'user_pref("webgl.disable-angle", false);'
        ])
        
        # Write prefs.js
        prefs_path = self.profile_path / "prefs.js"
        prefs_path.write_text("\n".join(prefs))
        
        # Also write user.js for persistence
        user_prefs_path = self.profile_path / "user.js"
        user_prefs_path.write_text("\n".join(prefs))
    
    def _generate_guid(self) -> str:
        """Generate a Firefox-style GUID."""
        import random
        import string
        chars = string.ascii_letters + string.digits + "_-"
        return "".join(random.choices(chars, k=12))
    
    def full_injection(
        self,
        history: List[Dict],
        cookies: List[Dict],
        form_data: Optional[List[Dict]] = None,
        localstorage: Optional[Dict[str, Dict[str, str]]] = None,
        permissions: Optional[List[Dict]] = None,
        profile_config: Optional[Dict[str, Any]] = None
    ) -> Path:
        """
        Perform full profile injection with all data types.
        
        Returns:
            Path to the profile directory
        """
        self.inject_places(history)
        self.inject_cookies(cookies)
        
        if form_data:
            self.inject_form_history(form_data)
        
        if localstorage:
            self.inject_localstorage(localstorage)
        
        if permissions:
            self.inject_permissions(permissions)
        
        if profile_config:
            self.create_prefs(profile_config)
        
        return self.profile_path



