"""
TITAN V7.0 SINGULARITY - Advanced Profile Generator
Implements the "Alex Mercer" Advanced Identity Injection Protocol

This module generates high-trust browser profiles with:
1. Temporal Narrative Construction (95-day history arc)
2. 500MB+ localStorage/IndexedDB per profile
3. Full web storage injection (cookies, cache, service workers)
4. Hardware binding with exact fingerprint matching
5. Commerce trust tokens (Stripe, PayPal, Adyen)
6. Geo-locked proxy configuration

Target: 90%+ Success Rate via "Golden Ticket" Identity Synthesis
Reference: Advanced Identity Injection Protocol.txt
"""

import os
import sys
import json
import sqlite3
import hashlib
import secrets
import random
import struct
import math
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from enum import Enum
import logging

logger = logging.getLogger("TITAN-V7-ADVANCED")


def _fx_sqlite(db_path, page_size=32768):
    """SQLite connection with Firefox-matching PRAGMA settings.
    Real Firefox uses page_size=32768, journal_mode=WAL, auto_vacuum=INCREMENTAL.
    Default SQLite settings (page_size=4096, journal_mode=DELETE) are an instant
    forensic detection vector for synthetic profiles."""
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    c.execute(f"PRAGMA page_size = {page_size}")
    c.execute("PRAGMA journal_mode = WAL")
    c.execute("PRAGMA auto_vacuum = INCREMENTAL")
    c.execute("PRAGMA wal_autocheckpoint = 512")
    c.execute("PRAGMA foreign_keys = ON")
    conn.commit()
    return conn


class NarrativePhase(Enum):
    """Temporal narrative phases for profile aging"""
    DISCOVERY = "discovery"      # Month 1: Academic/Discovery
    DEVELOPMENT = "development"  # Month 2: Usage/Development
    SEASONED = "seasoned"        # Month 3: Established user


@dataclass
class TemporalEvent:
    """Single event in the temporal narrative"""
    domain: str
    path: str
    days_ago: int
    visit_count: int = 1
    is_conversion: bool = False  # Did user "convert" (signup, purchase, etc.)
    phase: NarrativePhase = NarrativePhase.DISCOVERY
    referrer: Optional[str] = None
    session_duration_seconds: int = 120


@dataclass
class AdvancedProfileConfig:
    """Configuration for advanced profile generation"""
    profile_uuid: str
    persona_name: str
    persona_email: str
    
    # Billing/Shipping
    billing_address: Dict[str, str]
    
    # Hardware binding — defaults to Windows 11 (most common real-world target)
    hardware_profile: str = "us_windows_desktop"
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0"
    screen_resolution: str = "1920x1080"
    platform: str = "Win32"
    
    # Fingerprint
    canvas_noise_level: float = 0.001
    webgl_vendor: str = "Google Inc. (NVIDIA)"
    webgl_renderer: str = "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)"
    
    # Temporal
    profile_age_days: int = 95
    
    # Proxy
    proxy_region: str = "us-tx-austin"
    proxy_isp_targets: List[str] = field(default_factory=lambda: ["google_fiber", "att_fiber"])
    
    # Storage targets
    localstorage_size_mb: int = 500
    indexeddb_size_mb: int = 200
    cache_size_mb: int = 300


@dataclass
class GeneratedAdvancedProfile:
    """Output from advanced profile generation"""
    profile_id: str
    profile_path: Path
    profile_size_mb: float
    history_entries: int
    cookies_count: int
    localstorage_entries: int
    indexeddb_entries: int
    trust_tokens: int
    narrative_phases: Dict[str, int]
    created_at: datetime


# Pre-defined narrative templates
NARRATIVE_TEMPLATES = {
    "student_developer": {
        "name": "Student Developer (Alex Mercer)",
        "phases": {
            NarrativePhase.DISCOVERY: [
                # Academic phase
                TemporalEvent("overleaf.com", "/templates", 95, 12, False, NarrativePhase.DISCOVERY),
                TemporalEvent("spotify.com", "/student", 92, 3, True, NarrativePhase.DISCOVERY),
                TemporalEvent("arxiv.org", "/list/cs.CV/recent", 85, 25, False, NarrativePhase.DISCOVERY),
                TemporalEvent("chegg.com", "/study", 82, 8, True, NarrativePhase.DISCOVERY),
                TemporalEvent("coursera.org", "/learn/machine-learning", 78, 15, True, NarrativePhase.DISCOVERY),
                TemporalEvent("stackoverflow.com", "/questions/tagged/python", 75, 30, False, NarrativePhase.DISCOVERY),
                TemporalEvent("newegg.com", "/cart", 70, 5, True, NarrativePhase.DISCOVERY),
            ],
            NarrativePhase.DEVELOPMENT: [
                # Developer phase
                TemporalEvent("aws.amazon.com", "/console", 65, 8, False, NarrativePhase.DEVELOPMENT),
                TemporalEvent("digitalocean.com", "/billing", 58, 4, True, NarrativePhase.DEVELOPMENT),
                TemporalEvent("github.com", "/user/neural-net-v1", 46, 40, False, NarrativePhase.DEVELOPMENT),
                TemporalEvent("ubereats.com", "/checkout", 53, 3, True, NarrativePhase.DEVELOPMENT),
                TemporalEvent("doordash.com", "/orders", 48, 5, True, NarrativePhase.DEVELOPMENT),
                TemporalEvent("leetcode.com", "/problems", 42, 20, False, NarrativePhase.DEVELOPMENT),
                TemporalEvent("hackerrank.com", "/dashboard", 38, 10, False, NarrativePhase.DEVELOPMENT),
            ],
            NarrativePhase.SEASONED: [
                # Seasoned user phase
                TemporalEvent("steampowered.com", "/app/1245620", 32, 5, True, NarrativePhase.SEASONED),
                TemporalEvent("linkedin.com", "/premium", 25, 8, True, NarrativePhase.SEASONED),
                TemporalEvent("levels.fyi", "/t/software-engineer", 10, 5, False, NarrativePhase.SEASONED),
                TemporalEvent("amazon.com", "/prime", 6, 3, True, NarrativePhase.SEASONED),
                TemporalEvent("bestbuy.com", "/site/electronics", 4, 2, False, NarrativePhase.SEASONED),
            ],
        },
        "trust_domains": [
            "google.com", "gmail.com", "youtube.com", "github.com",
            "linkedin.com", "facebook.com", "twitter.com", "reddit.com"
        ],
        "commerce_domains": [
            "amazon.com", "newegg.com", "bestbuy.com", "steam", "ubereats.com"
        ],
    },
    "professional": {
        "name": "Professional",
        "phases": {
            NarrativePhase.DISCOVERY: [
                TemporalEvent("linkedin.com", "/feed", 95, 20, False, NarrativePhase.DISCOVERY),
                TemporalEvent("glassdoor.com", "/Reviews", 90, 10, False, NarrativePhase.DISCOVERY),
                TemporalEvent("indeed.com", "/jobs", 85, 15, False, NarrativePhase.DISCOVERY),
                TemporalEvent("wsj.com", "/news", 80, 25, False, NarrativePhase.DISCOVERY),
            ],
            NarrativePhase.DEVELOPMENT: [
                TemporalEvent("slack.com", "/workspace", 65, 50, True, NarrativePhase.DEVELOPMENT),
                TemporalEvent("zoom.us", "/meeting", 60, 30, True, NarrativePhase.DEVELOPMENT),
                TemporalEvent("notion.so", "/workspace", 55, 40, True, NarrativePhase.DEVELOPMENT),
                TemporalEvent("figma.com", "/files", 50, 20, True, NarrativePhase.DEVELOPMENT),
            ],
            NarrativePhase.SEASONED: [
                TemporalEvent("amazon.com", "/gp/buy", 30, 8, True, NarrativePhase.SEASONED),
                TemporalEvent("costco.com", "/checkout", 20, 3, True, NarrativePhase.SEASONED),
                TemporalEvent("target.com", "/cart", 10, 4, True, NarrativePhase.SEASONED),
            ],
        },
        "trust_domains": [
            "google.com", "gmail.com", "linkedin.com", "outlook.com"
        ],
        "commerce_domains": [
            "amazon.com", "costco.com", "target.com", "bestbuy.com"
        ],
    },
    "gamer": {
        "name": "Gamer",
        "phases": {
            NarrativePhase.DISCOVERY: [
                TemporalEvent("steampowered.com", "/explore", 95, 30, False, NarrativePhase.DISCOVERY),
                TemporalEvent("twitch.tv", "/directory", 90, 50, False, NarrativePhase.DISCOVERY),
                TemporalEvent("discord.com", "/channels", 85, 100, True, NarrativePhase.DISCOVERY),
                TemporalEvent("reddit.com", "/r/gaming", 80, 40, False, NarrativePhase.DISCOVERY),
            ],
            NarrativePhase.DEVELOPMENT: [
                TemporalEvent("epicgames.com", "/store", 65, 20, True, NarrativePhase.DEVELOPMENT),
                TemporalEvent("gog.com", "/games", 60, 15, True, NarrativePhase.DEVELOPMENT),
                TemporalEvent("humble.com", "/store", 55, 10, True, NarrativePhase.DEVELOPMENT),
                TemporalEvent("g2a.com", "/category/games", 50, 8, False, NarrativePhase.DEVELOPMENT),
            ],
            NarrativePhase.SEASONED: [
                TemporalEvent("eneba.com", "/store", 30, 5, True, NarrativePhase.SEASONED),
                TemporalEvent("newegg.com", "/gaming", 20, 4, True, NarrativePhase.SEASONED),
                TemporalEvent("amazon.com", "/gaming", 10, 3, True, NarrativePhase.SEASONED),
            ],
        },
        "trust_domains": [
            "google.com", "youtube.com", "twitch.tv", "discord.com", "reddit.com"
        ],
        "commerce_domains": [
            "steampowered.com", "epicgames.com", "eneba.com", "newegg.com", "amazon.com"
        ],
    },
    "retiree": {
        "name": "Retiree",
        "phases": {
            NarrativePhase.DISCOVERY: [
                TemporalEvent("weather.com", "/", 95, 30, False, NarrativePhase.DISCOVERY),
                TemporalEvent("webmd.com", "/drugs", 90, 15, False, NarrativePhase.DISCOVERY),
                TemporalEvent("aarp.org", "/benefits", 85, 10, True, NarrativePhase.DISCOVERY),
                TemporalEvent("facebook.com", "/", 80, 40, True, NarrativePhase.DISCOVERY),
                TemporalEvent("cnn.com", "/", 75, 25, False, NarrativePhase.DISCOVERY),
            ],
            NarrativePhase.DEVELOPMENT: [
                TemporalEvent("amazon.com", "/gp/goldbox", 65, 12, True, NarrativePhase.DEVELOPMENT),
                TemporalEvent("walmart.com", "/grocery", 58, 8, True, NarrativePhase.DEVELOPMENT),
                TemporalEvent("youtube.com", "/results?search_query=gardening", 50, 20, False, NarrativePhase.DEVELOPMENT),
                TemporalEvent("nextdoor.com", "/news_feed", 45, 15, True, NarrativePhase.DEVELOPMENT),
            ],
            NarrativePhase.SEASONED: [
                TemporalEvent("costco.com", "/checkout", 30, 5, True, NarrativePhase.SEASONED),
                TemporalEvent("target.com", "/cart", 20, 4, True, NarrativePhase.SEASONED),
                TemporalEvent("bestbuy.com", "/site/electronics", 10, 3, True, NarrativePhase.SEASONED),
            ],
        },
        "trust_domains": [
            "google.com", "gmail.com", "facebook.com", "youtube.com", "weather.com"
        ],
        "commerce_domains": [
            "amazon.com", "walmart.com", "costco.com", "target.com", "bestbuy.com"
        ],
    },
    "casual_shopper": {
        "name": "Casual Shopper",
        "phases": {
            NarrativePhase.DISCOVERY: [
                TemporalEvent("instagram.com", "/explore", 95, 35, True, NarrativePhase.DISCOVERY),
                TemporalEvent("pinterest.com", "/ideas", 90, 20, True, NarrativePhase.DISCOVERY),
                TemporalEvent("tiktok.com", "/foryou", 85, 50, False, NarrativePhase.DISCOVERY),
                TemporalEvent("youtube.com", "/", 80, 30, False, NarrativePhase.DISCOVERY),
            ],
            NarrativePhase.DEVELOPMENT: [
                TemporalEvent("amazon.com", "/s?k=trending", 65, 15, True, NarrativePhase.DEVELOPMENT),
                TemporalEvent("shein.com", "/new-in", 58, 10, True, NarrativePhase.DEVELOPMENT),
                TemporalEvent("target.com", "/deals", 50, 8, True, NarrativePhase.DEVELOPMENT),
                TemporalEvent("etsy.com", "/featured", 45, 12, True, NarrativePhase.DEVELOPMENT),
                TemporalEvent("walmart.com", "/browse", 40, 6, True, NarrativePhase.DEVELOPMENT),
            ],
            NarrativePhase.SEASONED: [
                TemporalEvent("amazon.com", "/gp/buy", 25, 8, True, NarrativePhase.SEASONED),
                TemporalEvent("bestbuy.com", "/cart", 15, 3, True, NarrativePhase.SEASONED),
                TemporalEvent("eneba.com", "/store", 8, 4, True, NarrativePhase.SEASONED),
            ],
        },
        "trust_domains": [
            "google.com", "gmail.com", "youtube.com", "instagram.com", "facebook.com"
        ],
        "commerce_domains": [
            "amazon.com", "target.com", "walmart.com", "bestbuy.com", "etsy.com", "eneba.com"
        ],
    },
}


class AdvancedProfileGenerator:
    """
    Generates high-trust browser profiles with 500MB+ storage.
    
    Implements the "Alex Mercer" Advanced Identity Injection Protocol
    for 90%+ success rate on high-value targets.
    
    Usage:
        generator = AdvancedProfileGenerator()
        
        config = AdvancedProfileConfig(
            profile_uuid="AM-8821-TRUSTED",
            persona_name="Alex J. Mercer",
            persona_email="a.mercer.dev@gmail.com",
            billing_address={
                "address": "2400 NUECES ST, APT 402",
                "city": "AUSTIN",
                "state": "TX",
                "zip": "78705",
                "country": "US"
            }
        )
        
        profile = generator.generate(config, template="student_developer")
    """
    
    def __init__(self, output_dir: str = "/opt/titan/profiles"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate(self, 
                 config: AdvancedProfileConfig,
                 template: str = "student_developer") -> GeneratedAdvancedProfile:
        """
        Generate a complete advanced profile with 500MB+ storage.
        
        Args:
            config: Profile configuration
            template: Narrative template name
            
        Returns:
            GeneratedAdvancedProfile with full storage
        """
        logger.info(f"[*] INITIATING '{config.profile_uuid}' SYNTHESIS...")
        
        # Create profile directory
        profile_path = self.output_dir / config.profile_uuid
        profile_path.mkdir(parents=True, exist_ok=True)
        
        # Get narrative template
        narrative = NARRATIVE_TEMPLATES.get(template, NARRATIVE_TEMPLATES["student_developer"])
        
        # Generate all components
        history_count = self._generate_history(profile_path, config, narrative)
        cookies_count = self._generate_cookies(profile_path, config, narrative)
        ls_count = self._generate_localstorage(profile_path, config, narrative)
        idb_count = self._generate_indexeddb(profile_path, config, narrative)
        tokens_count = self._generate_trust_tokens(profile_path, config)
        self._generate_cache(profile_path, config, narrative)
        self._generate_service_workers(profile_path, config, narrative)
        self._generate_hardware_profile(profile_path, config)
        self._generate_fingerprint_config(profile_path, config)
        self._generate_proxy_config(profile_path, config)
        self._generate_metadata(profile_path, config, template)
        self._generate_form_autofill(profile_path, config)  # Zero-decline autofill
        self._generate_sessionstore(profile_path, config)  # V7.0: LZ4 session store
        
        # V7.6: P0 Critical Components for Maximum Operational Success
        try:
            self._generate_site_engagement(profile_path, config, narrative)
            self._generate_notification_permissions(profile_path, config)
            self._generate_bookmarks(profile_path, config, narrative)
            self._generate_favicons(profile_path, config, narrative)
            logger.info("[V7.6] All P0 critical components generated")
        except Exception as exc:
            logger.warning("[V7.6] P0 component generation partial: %s", exc)
        
        # Calculate profile size
        profile_size = self._calculate_size(profile_path)
        
        # Count phases
        phase_counts = {
            "discovery": len(narrative["phases"].get(NarrativePhase.DISCOVERY, [])),
            "development": len(narrative["phases"].get(NarrativePhase.DEVELOPMENT, [])),
            "seasoned": len(narrative["phases"].get(NarrativePhase.SEASONED, [])),
        }
        
        logger.info(f"[+] IDENTITY '{config.profile_uuid}' SERIALIZED.")
        logger.info(f"[+] PROFILE SIZE: {profile_size:.1f} MB")
        logger.info(f"[+] HISTORY ENTRIES: {history_count}")
        logger.info(f"[+] TRUST TOKENS: {tokens_count}")
        
        return GeneratedAdvancedProfile(
            profile_id=config.profile_uuid,
            profile_path=profile_path,
            profile_size_mb=profile_size,
            history_entries=history_count,
            cookies_count=cookies_count,
            localstorage_entries=ls_count,
            indexeddb_entries=idb_count,
            trust_tokens=tokens_count,
            narrative_phases=phase_counts,
            created_at=datetime.now()
        )
    
    def _generate_history(self, profile_path: Path, config: AdvancedProfileConfig, 
                          narrative: Dict) -> int:
        """Generate browsing history with temporal narrative"""
        places_db = profile_path / "places.sqlite"
        conn = _fx_sqlite(places_db)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS moz_places (
                id INTEGER PRIMARY KEY,
                url TEXT,
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
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS moz_historyvisits (
                id INTEGER PRIMARY KEY,
                from_visit INTEGER,
                place_id INTEGER,
                visit_date INTEGER,
                visit_type INTEGER DEFAULT 1,
                session INTEGER DEFAULT 0
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS moz_origins (
                id INTEGER PRIMARY KEY,
                prefix TEXT NOT NULL,
                host TEXT NOT NULL,
                frecency INTEGER NOT NULL,
                UNIQUE (prefix, host)
            )
        """)
        
        entry_count = 0
        base_time = datetime.now()
        
        # Generate from narrative phases
        # V7.0 HARDENING: Pareto distribution + circadian rhythm
        for phase, events in narrative["phases"].items():
            for event in events:
                # Generate multiple visits per event
                for i in range(event.visit_count):
                    # V7.0: Circadian rhythm weighting
                    # Peaks at 10:00, 14:00, 20:00; troughs at 03:00-06:00
                    hour = self._circadian_weighted_hour()
                    visit_time = base_time - timedelta(
                        days=event.days_ago,
                        hours=-(hour),  # set to exact circadian hour
                        minutes=random.randint(0, 59)
                    )
                    visit_time = visit_time.replace(hour=hour)
                    
                    url = f"https://www.{event.domain}{event.path}"
                    title = self._generate_title(event.domain, event.path)
                    rev_host = ".".join(reversed(event.domain.split("."))) + "."
                    guid = secrets.token_urlsafe(9)[:12]
                    
                    cursor.execute("""
                        INSERT INTO moz_places 
                        (url, title, rev_host, visit_count, typed, last_visit_date, guid)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (url, title, rev_host, event.visit_count, 1, 
                          int(visit_time.timestamp() * 1000000), guid))
                    
                    place_id = cursor.lastrowid
                    
                    cursor.execute("""
                        INSERT INTO moz_historyvisits 
                        (place_id, visit_date, visit_type, session)
                        VALUES (?, ?, ?, ?)
                    """, (place_id, int(visit_time.timestamp() * 1000000), 1, i))
                    
                    entry_count += 1
        
        # V7.0 HARDENING: Add Pareto-distributed filler history
        # Research: "Pareto Distribution (80/20 rule) to model realistic browsing"
        # 80% of visits go to 20% of domains (power-law)
        all_domains = narrative.get("trust_domains", []) + narrative.get("commerce_domains", [])
        if all_domains:
            pareto_visits = self._pareto_distribute_visits(
                all_domains, config.profile_age_days, target_entries=2000
            )
            for domain, day_offset, visit_count in pareto_visits:
                hour = self._circadian_weighted_hour()
                visit_time = base_time - timedelta(days=day_offset)
                visit_time = visit_time.replace(hour=hour, minute=random.randint(0, 59))
                url = f"https://www.{domain}/"
                title = f"{domain.split('.')[0].title()} - Home"
                rev_host = ".".join(reversed(domain.split("."))) + "."
                guid = secrets.token_urlsafe(9)[:12]
                cursor.execute("""
                    INSERT INTO moz_places 
                    (url, title, rev_host, visit_count, typed, last_visit_date, guid)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (url, title, rev_host, visit_count, 1,
                      int(visit_time.timestamp() * 1000000), guid))
                place_id = cursor.lastrowid
                cursor.execute("""
                    INSERT INTO moz_historyvisits
                    (place_id, visit_date, visit_type, session)
                    VALUES (?, ?, ?, ?)
                """, (place_id, int(visit_time.timestamp() * 1000000), 1, 0))
                entry_count += 1

        # Add trust domain visits
        for domain in narrative.get("trust_domains", []):
            for day in range(0, config.profile_age_days, 3):  # Every 3 days
                hour = self._circadian_weighted_hour()
                visit_time = base_time - timedelta(days=day)
                visit_time = visit_time.replace(hour=hour, minute=random.randint(0, 59))
                url = f"https://www.{domain}/"
                title = f"{domain.split('.')[0].title()} - Home"
                rev_host = ".".join(reversed(domain.split("."))) + "."
                guid = secrets.token_urlsafe(9)[:12]
                
                cursor.execute("""
                    INSERT INTO moz_places 
                    (url, title, rev_host, visit_count, typed, last_visit_date, guid)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (url, title, rev_host, random.randint(5, 20), 1,
                      int(visit_time.timestamp() * 1000000), guid))
                
                entry_count += 1
        
        conn.commit()
        conn.close()
        
        return entry_count
    
    def _generate_cookies(self, profile_path: Path, config: AdvancedProfileConfig,
                          narrative: Dict) -> int:
        """Generate aged cookies with trust tokens"""
        cookies_db = profile_path / "cookies.sqlite"
        conn = _fx_sqlite(cookies_db)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS moz_cookies (
                id INTEGER PRIMARY KEY,
                originAttributes TEXT DEFAULT '',
                name TEXT,
                value TEXT,
                host TEXT,
                path TEXT DEFAULT '/',
                expiry INTEGER,
                lastAccessed INTEGER,
                creationTime INTEGER,
                isSecure INTEGER DEFAULT 1,
                isHttpOnly INTEGER DEFAULT 1,
                inBrowserElement INTEGER DEFAULT 0,
                sameSite INTEGER DEFAULT 0,
                rawSameSite INTEGER DEFAULT 0,
                schemeMap INTEGER DEFAULT 0
            )
        """)
        
        cookie_count = 0
        base_time = datetime.now()
        creation_time = base_time - timedelta(days=config.profile_age_days)
        
        # Trust anchor cookies
        trust_cookies = {
            "google.com": [
                ("SID", secrets.token_hex(32)),
                ("HSID", secrets.token_hex(16)),
                ("SSID", secrets.token_hex(16)),
                ("APISID", secrets.token_hex(16)),
                ("SAPISID", secrets.token_hex(16)),
                ("NID", secrets.token_hex(64)),
                ("1P_JAR", f"{base_time.year}-{base_time.month:02d}-{base_time.day:02d}-{random.randint(10,23)}"),
            ],
            "facebook.com": [
                ("c_user", str(random.randint(100000000, 999999999))),
                ("xs", secrets.token_hex(32)),
                ("fr", secrets.token_hex(24)),
                ("datr", secrets.token_hex(16)),
            ],
            "github.com": [
                ("_gh_sess", secrets.token_hex(64)),
                ("logged_in", "yes"),
                ("dotcom_user", config.persona_name.lower().replace(" ", "")),
            ],
            "linkedin.com": [
                ("li_at", secrets.token_hex(64)),
                ("JSESSIONID", f"ajax:{secrets.token_hex(16)}"),
                ("bcookie", f"v=2&{secrets.token_hex(16)}"),
            ],
        }
        
        for domain, cookies in trust_cookies.items():
            for name, value in cookies:
                cursor.execute("""
                    INSERT INTO moz_cookies 
                    (originAttributes, name, value, host, expiry, lastAccessed, creationTime, isSecure, isHttpOnly, sameSite, rawSameSite, schemeMap)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    "",  # V7.0: proper originAttributes for default container
                    name, value, f".{domain}",
                    int((base_time + timedelta(days=365)).timestamp()),
                    int(base_time.timestamp() * 1000000),
                    int(creation_time.timestamp() * 1000000),
                    1, 1,
                    0, 0, 2  # V7.0: sameSite=None, schemeMap=2 (HTTPS)
                ))
                cookie_count += 1
        
        # Commerce cookies — diverse PSPs like a real user (not just Stripe)
        _uuid4 = self._generate_stripe_sid  # reuse UUID v4 generator
        all_psp_cookies = [
            (".stripe.com", "__stripe_mid", self._generate_stripe_mid(config)),
            (".stripe.com", "__stripe_sid", _uuid4()),
            (".paypal.com", "TLTSID", secrets.token_hex(32)),
            (".paypal.com", "ts", secrets.token_hex(16)),
            (".paypal.com", "x-pp-s", secrets.token_hex(32)),
            (".adyen.com", "adyen-device-fingerprint", secrets.token_hex(32)),
            (".braintreegateway.com", "_braintree_device_id", _uuid4()),
            (".shopify.com", "_shopify_y", secrets.token_hex(32)),
            (".shopify.com", "_shopify_sa_t", secrets.token_hex(32)),
            (".klarna.com", "klarna_client_id", _uuid4()),
            (".squareup.com", "_sq_device_id", _uuid4()),
            (".amazon.com", "at-main", secrets.token_hex(40)),
        ]
        # A real user doesn't use ALL PSPs — randomly select 5-8 for this profile
        num_psp_cookies = random.randint(5, min(8, len(all_psp_cookies)))
        commerce_cookies = random.sample(all_psp_cookies, num_psp_cookies)
        
        for domain, name, value in commerce_cookies:
            cursor.execute("""
                INSERT INTO moz_cookies 
                (originAttributes, name, value, host, expiry, lastAccessed, creationTime, isSecure, isHttpOnly, sameSite, rawSameSite, schemeMap)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "",  # V7.0: default container originAttributes
                name, value, domain,
                int((base_time + timedelta(days=365)).timestamp()),
                int(base_time.timestamp() * 1000000),
                int((creation_time - timedelta(days=30)).timestamp() * 1000000),
                1, 0,
                0, 0, 2  # V7.0: sameSite=None, schemeMap=2 (HTTPS)
            ))
            cookie_count += 1
        
        conn.commit()
        conn.close()
        
        return cookie_count
    
    def _generate_localstorage(self, profile_path: Path, config: AdvancedProfileConfig,
                                narrative: Dict) -> int:
        """Generate 500MB+ localStorage data"""
        storage_dir = profile_path / "storage" / "default"
        storage_dir.mkdir(parents=True, exist_ok=True)
        
        entry_count = 0
        target_size_bytes = config.localstorage_size_mb * 1024 * 1024
        current_size = 0
        
        # Generate localStorage for each trust domain
        all_domains = narrative.get("trust_domains", []) + narrative.get("commerce_domains", [])
        
        for domain in all_domains:
            domain_dir = storage_dir / f"https+++www.{domain}"
            domain_dir.mkdir(parents=True, exist_ok=True)
            
            ls_db = domain_dir / "ls" / "data.sqlite"
            ls_db.parent.mkdir(parents=True, exist_ok=True)
            
            conn = _fx_sqlite(ls_db)
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS data (
                    key TEXT PRIMARY KEY,
                    utf16Length INTEGER NOT NULL DEFAULT 0,
                    compressed INTEGER NOT NULL DEFAULT 0,
                    lastAccessTime INTEGER NOT NULL DEFAULT 0,
                    value BLOB NOT NULL
                )
            """)
            
            # Generate domain-specific localStorage
            ls_data = self._generate_domain_localstorage(domain, config)
            
            for key, value in ls_data.items():
                # V7.5 FIX: Real Firefox LSNG stores values as UTF-16LE BLOBs
                # with a 4-byte LE length header. utf16Length = character count.
                value_str = value if isinstance(value, str) else str(value)
                utf16_chars = len(value_str)
                value_blob = value_str.encode("utf-16-le")
                # Prepend 4-byte LE length header (character count)
                value_with_header = struct.pack("<I", utf16_chars) + value_blob
                
                cursor.execute("""
                    INSERT OR REPLACE INTO data (key, value, utf16Length, lastAccessTime)
                    VALUES (?, ?, ?, ?)
                """, (key, value_with_header, utf16_chars, int(datetime.now().timestamp() * 1e6)))
                
                current_size += len(key) + len(value_with_header)
                entry_count += 1
            
            conn.commit()
            conn.close()
            
            # Add padding data to reach target size
            if current_size < target_size_bytes:
                padding_needed = (target_size_bytes - current_size) // len(all_domains)
                self._add_padding_data(domain_dir / "ls" / "data.sqlite", padding_needed)
                current_size += padding_needed
        
        logger.info(f"[+] LOCALSTORAGE: {current_size / (1024*1024):.1f} MB generated")
        return entry_count
    
    def _generate_domain_localstorage(self, domain: str, config: AdvancedProfileConfig) -> Dict[str, str]:
        """Generate domain-specific localStorage entries with realistic content"""
        base_time = datetime.now()
        creation_time = base_time - timedelta(days=config.profile_age_days)
        
        common_data = {
            "_ga": f"GA1.2.{random.randint(1000000000, 9999999999)}.{int(creation_time.timestamp())}",
            "_gid": f"GA1.2.{random.randint(1000000000, 9999999999)}.{int(base_time.timestamp())}",
            "amplitude_id": json.dumps({
                "deviceId": secrets.token_hex(16),
                "userId": None,
                "optOut": False,
                "sessionId": int(base_time.timestamp() * 1000),
                "lastEventTime": int(base_time.timestamp() * 1000),
                "eventId": random.randint(100, 500),
                "identifyId": random.randint(1, 10),
                "sequenceNumber": random.randint(100, 500),
            }),
            "__mp_opt_in_out_v2": json.dumps({secrets.token_hex(16): {"opt_in": True}}),
            "_dd_s": f"rum=0&expire={int(base_time.timestamp() * 1000) + 900000}",
        }
        
        tz = self._get_tz_for_state(config.billing_address.get("state", "TX"))
        persona_first = config.persona_name.split()[0].lower() if config.persona_name else "user"
        
        domain_specific = {
            "google.com": {
                "NID": secrets.token_hex(64),
                "CONSENT": f"YES+cb.{int(creation_time.timestamp())}",
                "SEARCH_SAMESITE": "CgQI5ZoB",
                "sb_wiz.zpc.gws-wiz-serp.aq": "1",
                "DV": secrets.token_hex(8),
                "__Secure-ENID": secrets.token_hex(32),
            },
            "youtube.com": {
                "yt-player-bandwidth": str(random.randint(2000000, 80000000)),
                "yt-player-quality": json.dumps({"data": random.choice(["hd1080", "hd720", "large"]), "expiration": int(base_time.timestamp() * 1000) + 2592000000, "creation": int(creation_time.timestamp() * 1000)}),
                "ytidb::LAST_RESULT_ENTRY_KEY": json.dumps({"data": f"\"winterIsComing-{secrets.token_hex(6)}\"", "expiration": int(base_time.timestamp() * 1000) + 2592000000, "creation": int(creation_time.timestamp() * 1000)}),
                "yt-html5-player-modules::subtitlesModuleData::module-enabled": "true",
                "yt.innertube::nextId": str(random.randint(1, 999)),
                "yt.innertube::requests": json.dumps([{"baseUrl": "https://www.youtube.com/api/stats/playback", "count": random.randint(50, 500)}]),
            },
            "github.com": {
                "logged_in": "true",
                "color_mode": json.dumps({"color_mode": "auto", "light_theme": {"name": "light", "color_mode": "light"}, "dark_theme": {"name": "dark", "color_mode": "dark"}}),
                "preferred_color_mode": random.choice(["dark", "light"]),
                "tz": tz,
                "has_hierarchical_leftnav": "true",
                "saved_hierarchical_leftnav_state": json.dumps({"org": {"expanded": True}, "repos": {"expanded": True}}),
            },
            "amazon.com": {
                "csm-hit": f"tb:{secrets.token_hex(8)}+s-{secrets.token_hex(8)}|{int(base_time.timestamp() * 1000)}",
                "session-id": f"{random.randint(100, 999)}-{random.randint(1000000, 9999999)}-{random.randint(1000000, 9999999)}",
                "ubid-main": f"{random.randint(100, 999)}-{random.randint(1000000, 9999999)}-{random.randint(1000000, 9999999)}",
                "session-token": secrets.token_urlsafe(108),
                "i18n-prefs": "USD",
                "lc-main": "en_US",
                "sp-cdn": '"L5Z9:' + config.billing_address.get("state", "TX") + '"',
                "skin": "noskin",
                "aws-target-data": json.dumps({"s": ["DESKTOP"], "v": "1"}),
            },
            "facebook.com": {
                "dpr": str(random.choice([1, 1.5, 2])),
                "wd": config.screen_resolution.replace("x", "x") if hasattr(config, 'screen_resolution') else "1920x1080",
                "datr": secrets.token_hex(16),
                "presence": json.dumps({"t3": [], "utc3": int(base_time.timestamp()), "v": 1}),
            },
            "reddit.com": {
                "recent_srs": json.dumps({"srs": ["t5_" + secrets.token_hex(3) for _ in range(random.randint(5, 15))]}),
                "USER_LOCALE": "en",
                "eu_cookie_v2": "3",
                "redesign_optout": random.choice(["true", "false"]),
                "loid": secrets.token_hex(13),
                "edgebucket": secrets.token_hex(16),
            },
            "twitter.com": {
                "night_mode": random.choice(["0", "1", "2"]),
                "rweb_optin": "side_nav_animation",
                "d_prefs": f"MToxLGNvbnNlbnRfdmVyc2lvbjoyLHRleHRfdmVyc2lvbjoxMDAw",
            },
            "linkedin.com": {
                "lang": "\"v=2&lang=en-us\"",
                "timezone": tz,
                "G_ENABLED_IDPS": "google",
                "AnalyticsSyncHistory": json.dumps([{"ts": int((base_time - timedelta(days=random.randint(0, 30))).timestamp()), "type": "page_view"}]),
            },
            "stripe.com": {
                "__stripe_mid": self._generate_stripe_mid(config),
                "__stripe_sid": self._generate_stripe_sid(),
                "cid": secrets.token_hex(16),
                "machine_identifier": secrets.token_hex(16),
            },
            "steampowered.com": {
                "steamMachineAuth": secrets.token_hex(20),
                "steamRememberLogin": "true",
                "strInventoryLastContext": "730_2",
                "sessionid": secrets.token_hex(12),
                "steamCountry": f"US%7C{secrets.token_hex(16)}",
            },
            "eneba.com": {
                "_eneba_session": secrets.token_hex(32),
                "cart": json.dumps({"items": [], "updated_at": int(base_time.timestamp())}),
                "currency": "USD",
                "locale": "en",
                "ab_tests": json.dumps({"checkout_v2": True, "new_search": random.choice([True, False])}),
            },
            "walmart.com": {
                "vtc": secrets.token_hex(32),
                "com.wm.reflector": f'"reflectorid:{secrets.token_hex(16)}"',
                "tb_sw_supported": "true",
                "adblocked": "false",
                "_m": "9",
                "type": "guest",
                "assortmentStoreId": str(random.randint(1000, 9999)),
            },
            "bestbuy.com": {
                "UID": secrets.token_hex(16),
                "SID": secrets.token_hex(16),
                "CTT": secrets.token_hex(8),
                "locStoreId": str(random.randint(100, 2000)),
                "locDestZip": config.billing_address.get("zip", "78705"),
            },
            "newegg.com": {
                "NV%5FPRODUCTION%5FCART": json.dumps({"ItemCount": 0, "CheckedItemCount": 0}),
                "NV%5FWELCOME": str(random.randint(1, 5)),
                "NV%5FCONFIGURATION": json.dumps({"Site": "USA", "SiteId": 1, "Currency": "USD"}),
            },
        }
        
        result = common_data.copy()
        if domain in domain_specific:
            result.update(domain_specific[domain])
        
        return result
    
    def _get_tz_for_state(self, state: str) -> str:
        """Get timezone string from US state abbreviation"""
        tz_map = {
            "AK": "America/Anchorage", "HI": "Pacific/Honolulu",
            "WA": "America/Los_Angeles", "OR": "America/Los_Angeles", "CA": "America/Los_Angeles", "NV": "America/Los_Angeles",
            "MT": "America/Denver", "ID": "America/Boise", "WY": "America/Denver", "UT": "America/Denver",
            "CO": "America/Denver", "AZ": "America/Phoenix", "NM": "America/Denver",
            "ND": "America/Chicago", "SD": "America/Chicago", "NE": "America/Chicago", "KS": "America/Chicago",
            "OK": "America/Chicago", "TX": "America/Chicago", "MN": "America/Chicago", "IA": "America/Chicago",
            "MO": "America/Chicago", "AR": "America/Chicago", "LA": "America/Chicago", "WI": "America/Chicago",
            "IL": "America/Chicago", "MS": "America/Chicago", "AL": "America/Chicago", "TN": "America/Chicago",
            "MI": "America/Detroit", "IN": "America/Indiana/Indianapolis",
            "OH": "America/New_York", "KY": "America/New_York", "WV": "America/New_York",
            "VA": "America/New_York", "NC": "America/New_York", "SC": "America/New_York",
            "GA": "America/New_York", "FL": "America/New_York",
            "PA": "America/New_York", "NY": "America/New_York", "NJ": "America/New_York",
            "CT": "America/New_York", "RI": "America/New_York", "MA": "America/New_York",
            "VT": "America/New_York", "NH": "America/New_York", "ME": "America/New_York",
            "MD": "America/New_York", "DE": "America/New_York", "DC": "America/New_York",
        }
        return tz_map.get(state, "America/Chicago")
    
    def _generate_indexeddb(self, profile_path: Path, config: AdvancedProfileConfig,
                            narrative: Dict) -> int:
        """Generate realistic IndexedDB data per domain"""
        idb_dir = profile_path / "storage" / "default"
        idb_dir.mkdir(parents=True, exist_ok=True)
        
        entry_count = 0
        base_time = datetime.now()
        
        all_domains = list(set(
            narrative.get("trust_domains", []) + narrative.get("commerce_domains", [])
        ))
        
        for domain in all_domains:
            domain_dir = idb_dir / f"https+++www.{domain}" / "idb"
            domain_dir.mkdir(parents=True, exist_ok=True)
            
            idb_file = domain_dir / f"{hashlib.md5(domain.encode()).hexdigest()[:16]}.sqlite"
            conn = _fx_sqlite(idb_file)
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS object_data (
                    id INTEGER PRIMARY KEY,
                    object_store_id INTEGER,
                    key_value BLOB,
                    data BLOB,
                    file_ids TEXT
                )
            """)
            
            records = self._generate_domain_idb_records(domain, config, base_time)
            for i, record in enumerate(records):
                cursor.execute("""
                    INSERT INTO object_data (object_store_id, key_value, data)
                    VALUES (?, ?, ?)
                """, (record.get("store_id", 1), struct.pack(">I", i), json.dumps(record["data"]).encode()))
                entry_count += 1
            
            conn.commit()
            conn.close()
        
        return entry_count
    
    def _generate_domain_idb_records(self, domain: str, config: AdvancedProfileConfig, base_time: datetime) -> List[Dict]:
        """Generate realistic IndexedDB records per domain"""
        records = []
        persona_first = config.persona_name.split()[0] if config.persona_name else "User"
        billing = config.billing_address
        
        if "amazon.com" in domain:
            # Order history, recently viewed, cart
            categories = ["Electronics", "Books", "Home & Kitchen", "Clothing", "Sports"]
            for i in range(random.randint(5, 15)):
                days_ago = random.randint(2, config.profile_age_days)
                records.append({"store_id": 1, "data": {
                    "type": "recently_viewed",
                    "asin": f"B{secrets.token_hex(4).upper()}",
                    "title": f"{random.choice(categories)} item #{random.randint(1000,9999)}",
                    "price": round(random.uniform(9.99, 299.99), 2),
                    "viewed_at": int((base_time - timedelta(days=days_ago)).timestamp() * 1000),
                    "category": random.choice(categories),
                }})
            records.append({"store_id": 2, "data": {
                "type": "cart_state", "items": [], "subtotal": 0, "updated_at": int(base_time.timestamp() * 1000),
            }})
        elif "youtube.com" in domain:
            # Watch history
            for i in range(random.randint(30, 100)):
                days_ago = random.randint(0, config.profile_age_days)
                records.append({"store_id": 1, "data": {
                    "videoId": secrets.token_urlsafe(8)[:11],
                    "title": f"Video {secrets.token_hex(3)}",
                    "channelName": f"Channel{random.randint(1,999)}",
                    "watchedAt": int((base_time - timedelta(days=days_ago)).timestamp() * 1000),
                    "duration": random.randint(60, 3600),
                    "percentWatched": round(random.uniform(0.3, 1.0), 2),
                }})
        elif "steampowered.com" in domain or "steam" in domain:
            # Game library, play sessions
            game_ids = [random.randint(200000, 2500000) for _ in range(random.randint(5, 30))]
            for gid in game_ids:
                records.append({"store_id": 1, "data": {
                    "appid": gid, "playtime_forever": random.randint(60, 50000),
                    "last_played": int((base_time - timedelta(days=random.randint(0, 60))).timestamp()),
                }})
        elif "eneba.com" in domain:
            records.append({"store_id": 1, "data": {
                "type": "user_prefs", "currency": "USD", "region": "US",
                "last_search": random.choice(["xbox game pass", "ps plus", "nintendo eshop", "steam gift card"]),
                "wishlist_count": random.randint(0, 8),
            }})
        elif "google.com" in domain:
            records.append({"store_id": 1, "data": {
                "type": "search_settings", "safe_search": "off", "results_per_page": 10,
                "language": "en", "region": "US",
            }})
        elif "facebook.com" in domain:
            for i in range(random.randint(10, 40)):
                records.append({"store_id": 1, "data": {
                    "type": "feed_cache", "post_id": secrets.token_hex(8),
                    "timestamp": int((base_time - timedelta(days=random.randint(0, 30))).timestamp()),
                    "seen": True,
                }})
        elif "walmart.com" in domain:
            for i in range(random.randint(3, 10)):
                records.append({"store_id": 1, "data": {
                    "type": "recently_viewed", "upc": secrets.token_hex(6).upper(),
                    "name": f"Household item #{random.randint(100,9999)}",
                    "price": round(random.uniform(4.99, 149.99), 2),
                    "store_id": str(random.randint(1000, 9999)),
                }})
        elif "bestbuy.com" in domain:
            for i in range(random.randint(3, 8)):
                records.append({"store_id": 1, "data": {
                    "type": "recently_viewed", "sku": str(random.randint(6000000, 6999999)),
                    "name": random.choice(["4K TV", "Laptop", "Headphones", "SSD", "Monitor", "Keyboard"]),
                    "price": round(random.uniform(29.99, 1499.99), 2),
                }})
        else:
            # Generic site data
            records.append({"store_id": 1, "data": {
                "type": "user_preferences", "theme": random.choice(["light", "dark", "auto"]),
                "notifications": random.choice([True, False]),
                "last_visit": int(base_time.timestamp()),
            }})
        
        return records
    
    def _generate_trust_tokens(self, profile_path: Path, config: AdvancedProfileConfig) -> int:
        """Generate commerce trust tokens"""
        tokens_file = profile_path / "commerce_tokens.json"
        
        base_time = datetime.now()
        creation_time = base_time - timedelta(days=config.profile_age_days)
        
        tokens = {
            "stripe": {
                "__stripe_mid": self._generate_stripe_mid(config),
                "__stripe_sid": self._generate_stripe_sid(),
                "created_at": creation_time.isoformat(),
                "age_days": config.profile_age_days,
            },
            "paypal": {
                "TLTSID": secrets.token_hex(32),
                "ts": secrets.token_hex(16),
                "created_at": creation_time.isoformat(),
            },
            "adyen": {
                "_RP_UID": secrets.token_hex(24),
                "adyen-device-fingerprint": secrets.token_hex(32),
                "created_at": creation_time.isoformat(),
            },
            "braintree": {
                "braintree_device_id": secrets.token_hex(32),
                "created_at": creation_time.isoformat(),
            },
        }
        
        with open(tokens_file, "w") as f:
            json.dump(tokens, f, indent=2)
        
        return len(tokens)
    
    def _generate_cache(self, profile_path: Path, config: AdvancedProfileConfig,
                        narrative: Dict):
        """Generate browser cache2 data with valid nsDiskCacheEntry headers.
        
        V7.5 FIX: Real Firefox cache2/entries files have a 32-byte
        nsDiskCacheEntry header. Pure random bytes = instant forensic flag.
        Header: version(4) + fetchCount(4) + lastFetched(4) + lastModified(4)
                + frecency(4) + expirationTime(4) + keySize(4) + flags(4)
        Followed by the key (URL) then the payload body.
        """
        cache_dir = profile_path / "cache2" / "entries"
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        target_size = config.cache_size_mb * 1024 * 1024
        current_size = 0
        base_ts = int(datetime.now().timestamp())
        
        all_domains = narrative.get("trust_domains", []) + narrative.get("commerce_domains", [])
        cache_urls = []
        for d in (all_domains or ["google.com"]):
            for suffix in ["/", "/favicon.ico", "/style.css", "/main.js", "/logo.png"]:
                cache_urls.append(f"https://www.{d}{suffix}")
        
        url_idx = 0
        while current_size < target_size:
            url = cache_urls[url_idx % len(cache_urls)]
            url_idx += 1
            key_bytes = url.encode("ascii")
            
            # nsDiskCacheEntry 32-byte header
            version = 3
            fetch_count = random.randint(1, 50)
            age_secs = random.randint(0, config.profile_age_days * 86400)
            last_fetched = base_ts - age_secs
            last_modified = last_fetched - random.randint(0, 3600)
            frecency = random.randint(10, 10000)
            expiration = base_ts + random.randint(3600, 86400 * 365)
            key_size = len(key_bytes)
            flags = 0
            
            header = struct.pack("<IIIIIIII",
                                 version, fetch_count, last_fetched, last_modified,
                                 frecency, expiration, key_size, flags)
            
            body_size = random.randint(10 * 1024, 1024 * 1024)
            body = os.urandom(body_size)
            
            # HTTP metadata tail (simplified)
            meta = f"request-method: GET\r\nresponse-head: HTTP/1.1 200 OK\r\ncontent-type: application/octet-stream\r\n".encode()
            meta_size = struct.pack("<I", len(meta))
            
            cache_hash = hashlib.sha1(key_bytes).hexdigest()[:40]
            cache_file = cache_dir / cache_hash
            
            with open(cache_file, "wb") as f:
                f.write(header)
                f.write(key_bytes)
                f.write(body)
                f.write(meta_size)
                f.write(meta)
            
            file_total = 32 + len(key_bytes) + body_size + 4 + len(meta)
            current_size += file_total
        
        logger.info(f"[+] CACHE: {current_size / (1024*1024):.1f} MB generated (with nsDiskCacheEntry headers)")
    
    def _generate_service_workers(self, profile_path: Path, config: AdvancedProfileConfig,
                                   narrative: Dict):
        """Generate service worker registrations"""
        sw_dir = profile_path / "storage" / "default"
        sw_dir.mkdir(parents=True, exist_ok=True)
        
        # Create service worker registrations for key domains
        sw_domains = ["google.com", "youtube.com", "twitter.com"]
        
        for domain in sw_domains:
            domain_dir = sw_dir / f"https+++www.{domain}" / "cache"
            domain_dir.mkdir(parents=True, exist_ok=True)
            
            # Create cache storage
            cache_db = domain_dir / "caches.sqlite"
            conn = _fx_sqlite(cache_db)
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS caches (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    namespace INTEGER DEFAULT 0
                )
            """)
            
            cursor.execute("INSERT INTO caches (name) VALUES (?)", (f"{domain}-cache-v1",))
            
            conn.commit()
            conn.close()
    
    # Cross-validated hardware presets — each entry is a COHERENT real-world machine.
    # CPU tier, RAM, battery capacity, and form factor are all internally consistent.
    # Prevents antifraud HW fingerprint analysis from flagging "impossible" combos.
    _HW_PRESETS = {
        "Win32": [
            # Mid-range desktop
            {"cpu": "12th Gen Intel Core i5-12400", "cores": "6", "memory": "16GB",
             "vendor": "Dell Inc.", "product": "XPS 8950", "battery_wh": None,
             "form_factor": "Desktop", "device_description": "Dell XPS Desktop"},
            # High-end desktop
            {"cpu": "13th Gen Intel Core i7-13700K", "cores": "16", "memory": "32GB",
             "vendor": "ASUSTeK Computer Inc.", "product": "ROG Strix G15CF", "battery_wh": None,
             "form_factor": "Desktop", "device_description": "ASUS ROG Desktop"},
            # Mid-range gaming desktop
            {"cpu": "AMD Ryzen 7 5800X", "cores": "8", "memory": "32GB",
             "vendor": "Micro-Star International Co., Ltd.", "product": "MS-7C91", "battery_wh": None,
             "form_factor": "Desktop", "device_description": "MSI Gaming Desktop"},
            # Budget office desktop
            {"cpu": "12th Gen Intel Core i3-12100", "cores": "4", "memory": "8GB",
             "vendor": "Lenovo", "product": "ThinkCentre M70s Gen 3", "battery_wh": None,
             "form_factor": "Desktop", "device_description": "Lenovo ThinkCentre"},
            # Mid-range laptop
            {"cpu": "12th Gen Intel Core i7-12700H", "cores": "14", "memory": "16GB",
             "vendor": "HP", "product": "HP ENVY x360 15-ew0xxx", "battery_wh": 51.0,
             "form_factor": "Notebook", "device_description": "HP ENVY Laptop"},
            # Gaming laptop
            {"cpu": "13th Gen Intel Core i9-13900HX", "cores": "24", "memory": "32GB",
             "vendor": "ASUSTeK Computer Inc.", "product": "ROG Strix SCAR 17", "battery_wh": 90.0,
             "form_factor": "Notebook", "device_description": "ASUS ROG Laptop"},
            # Budget laptop
            {"cpu": "AMD Ryzen 5 5500U", "cores": "6", "memory": "8GB",
             "vendor": "Lenovo", "product": "IdeaPad 5 15ALC05", "battery_wh": 56.5,
             "form_factor": "Notebook", "device_description": "Lenovo IdeaPad Laptop"},
        ],
        "MacIntel": [
            # MacBook Pro M2 Pro — coherent: 10-core, 16GB unified, 70Wh
            {"cpu": "Apple M2 Pro", "cores": "10", "memory": "16GB",
             "vendor": "Apple Inc.", "product": "MacBookPro18,3", "battery_wh": 69.6,
             "form_factor": "Notebook", "device_description": "MacBook Pro 14-inch"},
            # MacBook Pro M2 Max — coherent: 12-core, 32GB, 100Wh
            {"cpu": "Apple M2 Max", "cores": "12", "memory": "32GB",
             "vendor": "Apple Inc.", "product": "MacBookPro18,4", "battery_wh": 99.6,
             "form_factor": "Notebook", "device_description": "MacBook Pro 16-inch"},
            # MacBook Air M2 — coherent: 8-core, 8GB, 52Wh
            {"cpu": "Apple M2", "cores": "8", "memory": "8GB",
             "vendor": "Apple Inc.", "product": "Mac14,2", "battery_wh": 52.6,
             "form_factor": "Notebook", "device_description": "MacBook Air 13-inch"},
            # Mac mini M2 — no battery (desktop)
            {"cpu": "Apple M2", "cores": "8", "memory": "16GB",
             "vendor": "Apple Inc.", "product": "Mac14,3", "battery_wh": None,
             "form_factor": "Desktop", "device_description": "Mac mini"},
        ],
    }

    def _generate_hardware_profile(self, profile_path: Path, config: AdvancedProfileConfig):
        """Generate hardware fingerprint configuration using cross-validated presets.
        
        Each preset is a real-world coherent machine — CPU tier, RAM, battery capacity,
        and form factor are all internally consistent to defeat HW fingerprint analysis.
        """
        hw_file = profile_path / "hardware_profile.json"

        presets = self._HW_PRESETS.get(config.platform, self._HW_PRESETS["Win32"])
        template = random.choice(presets)

        hw_config = {
            "cpu": template["cpu"],
            "cores": template["cores"],
            "memory": template["memory"],
            "gpu": config.webgl_renderer,
            "gpu_vendor": config.webgl_vendor,
            "gpu_renderer": config.webgl_renderer,
            "screen": config.screen_resolution,
            "platform": config.platform,
            "vendor": template["vendor"],
            "product": template["product"],
            "form_factor": template["form_factor"],
            "battery_wh": template["battery_wh"],
            "device_description": template["device_description"],
            "user_agent": config.user_agent,
            "uuid": secrets.token_hex(16),
            "board_serial": secrets.token_hex(8).upper(),
        }

        with open(hw_file, "w") as f:
            json.dump(hw_config, f, indent=2)
    
    def _generate_fingerprint_config(self, profile_path: Path, config: AdvancedProfileConfig):
        """Generate fingerprint injection configuration"""
        fp_file = profile_path / "fingerprint_config.json"
        
        seed = int(hashlib.sha256(config.profile_uuid.encode()).hexdigest()[:8], 16)
        
        fp_config = {
            "canvas_seed": seed,
            "canvas_noise_level": config.canvas_noise_level,
            "webgl_vendor": config.webgl_vendor,
            "webgl_renderer": config.webgl_renderer,
            "audio_seed": seed + 1,
            "audio_noise_level": 0.0001,
            "deterministic": True,
            "profile_uuid": config.profile_uuid,
        }
        
        with open(fp_file, "w") as f:
            json.dump(fp_config, f, indent=2)
    
    def _generate_proxy_config(self, profile_path: Path, config: AdvancedProfileConfig):
        """Generate proxy configuration"""
        proxy_file = profile_path / "proxy_config.json"
        
        proxy_config = {
            "type": "residential",
            "region": config.proxy_region,
            "isp_targets": config.proxy_isp_targets,
            "sticky_session": True,
            "session_duration_minutes": 30,
        }
        
        with open(proxy_file, "w") as f:
            json.dump(proxy_config, f, indent=2)

    # ═══════════════════════════════════════════════════════════════════════════
    # V7.6 UPGRADE: P0 CRITICAL COMPONENTS FOR MAXIMUM OPERATIONAL SUCCESS
    # Site Engagement, Notification Permissions, Bookmarks, Favicons
    # ═══════════════════════════════════════════════════════════════════════════

    def _generate_site_engagement(self, profile_path: Path, config: AdvancedProfileConfig, 
                                   narrative: Dict):
        """
        Generate Chrome Site Engagement database with realistic scores.
        
        Site Engagement is Chrome's trust scoring system - sites with higher
        engagement get more permissions (autoplay, notifications, etc).
        Fraud engines check this database for profile authenticity.
        """
        # Only for Chromium-based browsers
        if "firefox" in config.user_agent.lower():
            return
        
        default_path = profile_path / "Default"
        default_path.mkdir(exist_ok=True)
        
        engagement_db = default_path / "Site Engagement"
        conn = sqlite3.connect(engagement_db)
        cursor = conn.cursor()
        
        CHROME_EPOCH_OFFSET = 11644473600 * 1000000
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT NOT NULL PRIMARY KEY,
                value TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS site_engagement (
                origin TEXT NOT NULL PRIMARY KEY,
                score REAL NOT NULL DEFAULT 0,
                last_shortcut_launch_time INTEGER NOT NULL DEFAULT 0,
                last_engagement_time INTEGER NOT NULL DEFAULT 0,
                notifications_suppressed INTEGER NOT NULL DEFAULT 0
            )
        """)
        
        cursor.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", ("version", "4"))
        
        # Build engagement from narrative domains
        all_domains = list(set(
            narrative.get("trust_domains", []) + narrative.get("commerce_domains", [])
        ))
        
        base_time = datetime.now()
        for domain in all_domains:
            origin = f"https://www.{domain}"
            # Score based on domain type (trust domains higher)
            if domain in narrative.get("trust_domains", []):
                score = random.uniform(50.0, 95.0)  # High engagement
            else:
                score = random.uniform(15.0, 50.0)  # Moderate engagement
            
            last_engagement = int((base_time - timedelta(days=random.randint(0, 3))).timestamp() * 1000000) + CHROME_EPOCH_OFFSET
            
            cursor.execute(
                "INSERT OR REPLACE INTO site_engagement (origin, score, last_shortcut_launch_time, last_engagement_time, notifications_suppressed) VALUES (?, ?, ?, ?, ?)",
                (origin, round(score, 2), 0, last_engagement, 0)
            )
        
        conn.commit()
        conn.close()
        logger.debug("[V7.6] Site engagement scores generated")

    def _generate_notification_permissions(self, profile_path: Path, config: AdvancedProfileConfig):
        """
        Generate notification permissions showing realistic user decisions.
        
        Real users accept/deny notification prompts over time.
        Empty permissions = obvious synthetic profile.
        """
        # Firefox uses permissions.sqlite
        if "firefox" in config.user_agent.lower():
            perms_db = profile_path / "permissions.sqlite"
            conn = _fx_sqlite(perms_db)
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS moz_perms (
                    id INTEGER PRIMARY KEY,
                    origin TEXT,
                    type TEXT,
                    permission INTEGER,
                    expireType INTEGER DEFAULT 0,
                    expireTime INTEGER DEFAULT 0,
                    modificationTime INTEGER
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS moz_hosts (
                    id INTEGER PRIMARY KEY,
                    host TEXT,
                    type TEXT,
                    permission INTEGER,
                    expireType INTEGER DEFAULT 0,
                    expireTime INTEGER DEFAULT 0,
                    modificationTime INTEGER,
                    isInBrowserElement INTEGER DEFAULT 0
                )
            """)
            
            # Notification decisions
            notification_sites = [
                ("https://www.youtube.com", 1),  # Allow
                ("https://mail.google.com", 1),  # Allow
                ("https://www.facebook.com", 1),  # Allow
                ("https://twitter.com", 2),  # Deny
                ("https://www.reddit.com", 2),  # Deny
                ("https://www.amazon.com", 2),  # Deny spam
                ("https://www.linkedin.com", 2),  # Deny
            ]
            
            base_time = datetime.now()
            for i, (origin, permission) in enumerate(random.sample(notification_sites, min(5, len(notification_sites)))):
                mod_time = int((base_time - timedelta(days=random.randint(10, config.profile_age_days))).timestamp() * 1000)
                cursor.execute(
                    "INSERT INTO moz_perms (origin, type, permission, modificationTime) VALUES (?, ?, ?, ?)",
                    (origin, "desktop-notification", permission, mod_time)
                )
            
            conn.commit()
            conn.close()
        else:
            # Chrome uses Preferences JSON
            default_path = profile_path / "Default"
            default_path.mkdir(exist_ok=True)
            
            prefs_file = default_path / "Preferences"
            prefs = {}
            if prefs_file.exists():
                try:
                    with open(prefs_file, 'r') as f:
                        prefs = json.load(f)
                except:
                    pass
            
            if "profile" not in prefs:
                prefs["profile"] = {}
            if "content_settings" not in prefs["profile"]:
                prefs["profile"]["content_settings"] = {}
            if "exceptions" not in prefs["profile"]["content_settings"]:
                prefs["profile"]["content_settings"]["exceptions"] = {}
            
            notification_sites = [
                ("https://www.youtube.com", 1),
                ("https://mail.google.com", 1),
                ("https://www.facebook.com", 1),
                ("https://twitter.com", 2),
                ("https://www.amazon.com", 2),
            ]
            
            notifications = {}
            base_time = datetime.now()
            for site, decision in random.sample(notification_sites, min(4, len(notification_sites))):
                timestamp = int((base_time - timedelta(days=random.randint(10, config.profile_age_days))).timestamp())
                notifications[f"{site},*"] = {
                    "last_modified": str(timestamp * 1000000),
                    "setting": decision,
                    "expiration": "0"
                }
            
            prefs["profile"]["content_settings"]["exceptions"]["notifications"] = notifications
            
            with open(prefs_file, 'w') as f:
                json.dump(prefs, f, indent=2)
        
        logger.debug("[V7.6] Notification permissions generated")

    def _generate_bookmarks(self, profile_path: Path, config: AdvancedProfileConfig, 
                            narrative: Dict):
        """
        Generate bookmarks with realistic temporal evolution.
        
        Real users accumulate bookmarks over time. Empty bookmarks = suspicious.
        """
        # Firefox: add moz_bookmarks to places.sqlite
        if "firefox" in config.user_agent.lower():
            places_db = profile_path / "places.sqlite"
            if not places_db.exists():
                return
            
            conn = _fx_sqlite(places_db)
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS moz_bookmarks (
                    id INTEGER PRIMARY KEY,
                    type INTEGER DEFAULT 1,
                    fk INTEGER,
                    parent INTEGER,
                    position INTEGER DEFAULT 0,
                    title TEXT,
                    keyword_id INTEGER,
                    folder_type TEXT,
                    dateAdded INTEGER,
                    lastModified INTEGER,
                    guid TEXT
                )
            """)
            
            base_time = datetime.now()
            age_base = base_time - timedelta(days=config.profile_age_days)
            
            # Create root folders
            cursor.execute(
                "INSERT INTO moz_bookmarks (id, type, parent, title, dateAdded, lastModified, guid) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (1, 2, 0, "", int(age_base.timestamp() * 1000000), int(base_time.timestamp() * 1000000), "root________")
            )
            cursor.execute(
                "INSERT INTO moz_bookmarks (id, type, parent, title, dateAdded, lastModified, guid) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (2, 2, 1, "Bookmarks Toolbar", int(age_base.timestamp() * 1000000), int(base_time.timestamp() * 1000000), "toolbar_____")
            )
            cursor.execute(
                "INSERT INTO moz_bookmarks (id, type, parent, title, dateAdded, lastModified, guid) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (3, 2, 1, "Other Bookmarks", int(age_base.timestamp() * 1000000), int(base_time.timestamp() * 1000000), "unfiled_____")
            )
            
            # Add bookmarks from trust domains
            bookmark_id = 100
            for domain in narrative.get("trust_domains", [])[:8]:
                date_added = int((age_base + timedelta(days=random.randint(0, config.profile_age_days // 2))).timestamp() * 1000000)
                guid = secrets.token_urlsafe(9)[:12]
                
                # First insert into moz_places
                url = f"https://www.{domain}/"
                title = f"{domain.split('.')[0].title()}"
                cursor.execute(
                    "INSERT OR IGNORE INTO moz_places (url, title, guid) VALUES (?, ?, ?)",
                    (url, title, secrets.token_urlsafe(9)[:12])
                )
                fk = cursor.lastrowid or random.randint(1, 1000)
                
                cursor.execute(
                    "INSERT INTO moz_bookmarks (id, type, fk, parent, position, title, dateAdded, lastModified, guid) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (bookmark_id, 1, fk, 2, bookmark_id - 100, title, date_added, date_added, guid)
                )
                bookmark_id += 1
            
            conn.commit()
            conn.close()
        else:
            # Chrome: create Bookmarks JSON
            default_path = profile_path / "Default"
            default_path.mkdir(exist_ok=True)
            
            CHROME_EPOCH_OFFSET = 11644473600 * 1000000
            base_time = datetime.now()
            age_base = base_time - timedelta(days=config.profile_age_days)
            
            bookmark_items = []
            for domain in narrative.get("trust_domains", [])[:6]:
                date_added = int((age_base + timedelta(days=random.randint(0, config.profile_age_days // 2))).timestamp() * 1000000) + CHROME_EPOCH_OFFSET
                bookmark_items.append({
                    "date_added": str(date_added),
                    "guid": secrets.token_hex(8) + "-" + secrets.token_hex(4) + "-" + secrets.token_hex(4) + "-" + secrets.token_hex(4) + "-" + secrets.token_hex(12),
                    "id": str(random.randint(100, 9999)),
                    "name": domain.split('.')[0].title(),
                    "type": "url",
                    "url": f"https://www.{domain}/"
                })
            
            bookmarks_data = {
                "checksum": secrets.token_hex(16),
                "roots": {
                    "bookmark_bar": {
                        "children": bookmark_items,
                        "date_added": str(int(age_base.timestamp() * 1000000) + CHROME_EPOCH_OFFSET),
                        "date_modified": str(int(base_time.timestamp() * 1000000) + CHROME_EPOCH_OFFSET),
                        "guid": secrets.token_hex(8) + "-" + secrets.token_hex(4) + "-" + secrets.token_hex(4) + "-" + secrets.token_hex(4) + "-" + secrets.token_hex(12),
                        "id": "1",
                        "name": "Bookmarks bar",
                        "type": "folder"
                    },
                    "other": {"children": [], "date_added": str(int(age_base.timestamp() * 1000000) + CHROME_EPOCH_OFFSET), "date_modified": "0", "id": "2", "name": "Other bookmarks", "type": "folder"},
                    "synced": {"children": [], "date_added": str(int(age_base.timestamp() * 1000000) + CHROME_EPOCH_OFFSET), "date_modified": "0", "id": "3", "name": "Mobile bookmarks", "type": "folder"}
                },
                "version": 1
            }
            
            with open(default_path / "Bookmarks", 'w') as f:
                json.dump(bookmarks_data, f, indent=3)
        
        logger.debug("[V7.6] Bookmarks generated")

    def _generate_favicons(self, profile_path: Path, config: AdvancedProfileConfig, 
                           narrative: Dict):
        """
        Generate favicons database.
        
        Chrome/Firefox store favicons in a separate database. Empty favicon
        database + filled history = obvious synthetic profile.
        """
        all_domains = list(set(
            narrative.get("trust_domains", []) + narrative.get("commerce_domains", [])
        ))
        
        # Firefox: favicons.sqlite
        if "firefox" in config.user_agent.lower():
            favicons_db = profile_path / "favicons.sqlite"
            conn = _fx_sqlite(favicons_db)
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS moz_icons (
                    id INTEGER PRIMARY KEY,
                    icon_url TEXT NOT NULL,
                    fixed_icon_url_hash INTEGER NOT NULL,
                    width INTEGER NOT NULL DEFAULT 0,
                    root INTEGER NOT NULL DEFAULT 0,
                    color INTEGER,
                    expire_ms INTEGER NOT NULL DEFAULT 0,
                    data BLOB
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS moz_pages_w_icons (
                    id INTEGER PRIMARY KEY,
                    page_url TEXT NOT NULL,
                    page_url_hash INTEGER NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS moz_icons_to_pages (
                    page_id INTEGER NOT NULL,
                    icon_id INTEGER NOT NULL,
                    expire_ms INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (page_id, icon_id)
                )
            """)
            
            base_time = datetime.now()
            for i, domain in enumerate(all_domains[:50]):
                icon_url = f"https://www.{domain}/favicon.ico"
                page_url = f"https://www.{domain}/"
                
                url_hash = hash(icon_url) & 0x7FFFFFFF
                page_hash = hash(page_url) & 0x7FFFFFFF
                
                expire_ms = int((base_time + timedelta(days=30)).timestamp() * 1000)
                
                cursor.execute(
                    "INSERT INTO moz_icons (icon_url, fixed_icon_url_hash, width, expire_ms) VALUES (?, ?, ?, ?)",
                    (icon_url, url_hash, 16, expire_ms)
                )
                icon_id = cursor.lastrowid
                
                cursor.execute(
                    "INSERT INTO moz_pages_w_icons (page_url, page_url_hash) VALUES (?, ?)",
                    (page_url, page_hash)
                )
                page_id = cursor.lastrowid
                
                cursor.execute(
                    "INSERT INTO moz_icons_to_pages (page_id, icon_id, expire_ms) VALUES (?, ?, ?)",
                    (page_id, icon_id, expire_ms)
                )
            
            conn.commit()
            conn.close()
        else:
            # Chrome: Favicons database
            default_path = profile_path / "Default"
            default_path.mkdir(exist_ok=True)
            
            CHROME_EPOCH_OFFSET = 11644473600 * 1000000
            
            favicon_db = default_path / "Favicons"
            conn = sqlite3.connect(favicon_db)
            cursor = conn.cursor()
            
            cursor.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")
            cursor.execute("CREATE TABLE IF NOT EXISTS favicons (id INTEGER PRIMARY KEY, url TEXT NOT NULL, icon_type INTEGER DEFAULT 1)")
            cursor.execute("CREATE TABLE IF NOT EXISTS favicon_bitmaps (id INTEGER PRIMARY KEY, icon_id INTEGER, last_updated INTEGER, image_data BLOB, width INTEGER DEFAULT 0, height INTEGER DEFAULT 0)")
            cursor.execute("CREATE TABLE IF NOT EXISTS icon_mapping (id INTEGER PRIMARY KEY, page_url TEXT, icon_id INTEGER)")
            
            cursor.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", ("version", "8"))
            
            base_time = datetime.now()
            for i, domain in enumerate(all_domains[:50]):
                favicon_url = f"https://www.{domain}/favicon.ico"
                
                cursor.execute("INSERT INTO favicons (url, icon_type) VALUES (?, ?)", (favicon_url, 1))
                icon_id = cursor.lastrowid
                
                last_updated = int((base_time - timedelta(days=random.randint(0, config.profile_age_days))).timestamp() * 1000000) + CHROME_EPOCH_OFFSET
                cursor.execute(
                    "INSERT INTO favicon_bitmaps (icon_id, last_updated, width, height) VALUES (?, ?, ?, ?)",
                    (icon_id, last_updated, 16, 16)
                )
                
                cursor.execute(
                    "INSERT INTO icon_mapping (page_url, icon_id) VALUES (?, ?)",
                    (f"https://www.{domain}/", icon_id)
                )
            
            conn.commit()
            conn.close()
        
        logger.debug("[V7.6] Favicons generated")
    
    def _generate_metadata(self, profile_path: Path, config: AdvancedProfileConfig,
                           template: str):
        """Generate profile metadata"""
        meta_file = profile_path / "profile_metadata.json"
        
        metadata = {
            "profile_id": config.profile_uuid,
            "persona_name": config.persona_name,
            "persona_email": config.persona_email,
            "template": template,
            "created_at": datetime.now().isoformat(),
            "profile_age_days": config.profile_age_days,
            "billing_address": config.billing_address,
            "hardware_profile": config.hardware_profile,
            "platform": config.platform,
            "screen_resolution": config.screen_resolution,
            "proxy_region": config.proxy_region,
            "target_storage_mb": config.localstorage_size_mb + config.indexeddb_size_mb + config.cache_size_mb,
        }
        
        with open(meta_file, "w") as f:
            json.dump(metadata, f, indent=2)
    
    def _generate_form_autofill(self, profile_path: Path, config: AdvancedProfileConfig):
        """Generate form autofill data for zero-decline"""
        try:
            from form_autofill_injector import FormAutofillInjector, PersonaAutofill
            
            # Parse name
            name_parts = config.persona_name.split()
            first_name = name_parts[0] if name_parts else ""
            last_name = name_parts[-1] if len(name_parts) > 1 else ""
            
            # Parse address
            billing = config.billing_address
            address_line1 = billing.get("address", "")
            address_parts = address_line1.split(",")
            line1 = address_parts[0].strip() if address_parts else address_line1
            line2 = address_parts[1].strip() if len(address_parts) > 1 else ""
            
            persona = PersonaAutofill(
                full_name=config.persona_name,
                first_name=first_name,
                last_name=last_name,
                email=config.persona_email,
                phone=billing.get("phone", ""),
                address_line1=line1,
                address_line2=line2,
                city=billing.get("city", ""),
                state=billing.get("state", ""),
                zip_code=billing.get("zip", ""),
                country=billing.get("country", "US"),
            )
            
            injector = FormAutofillInjector(str(profile_path))
            injector.inject_all(persona, config.profile_age_days)
            
            logger.info(f"[+] Form autofill injected for {config.persona_name}")
            
        except ImportError as e:
            logger.warning(f"Form autofill not available: {e}")
    
    def _generate_stripe_mid(self, config: AdvancedProfileConfig) -> str:
        """Generate pre-aged Stripe __stripe_mid as UUID v4 (real format).
        
        V7.5 PATCH: Real __stripe_mid is a standard UUID v4.
        Old format (hash.timestamp.random) was flagged by Stripe Radar.
        """
        creation_time = datetime.now() - timedelta(days=config.profile_age_days + 30)
        seed = hashlib.sha256(
            f"{config.profile_uuid}:{int(creation_time.timestamp())}".encode()
        ).digest()
        b = bytearray(seed[:16])
        b[6] = (b[6] & 0x0F) | 0x40  # version 4
        b[8] = (b[8] & 0x3F) | 0x80  # variant 1
        h = bytes(b).hex()
        return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"
    
    @staticmethod
    def _generate_stripe_sid() -> str:
        """Generate __stripe_sid as UUID v4 (real Stripe format)."""
        b = bytearray(secrets.token_bytes(16))
        b[6] = (b[6] & 0x0F) | 0x40
        b[8] = (b[8] & 0x3F) | 0x80
        h = bytes(b).hex()
        return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"
    
    def _generate_title(self, domain: str, path: str) -> str:
        """Generate realistic page title"""
        titles = {
            "overleaf.com": "Overleaf - LaTeX Editor",
            "spotify.com": "Spotify - Web Player",
            "arxiv.org": "arXiv.org - Computer Science",
            "github.com": "GitHub - Your Repositories",
            "amazon.com": "Amazon.com - Shopping",
            "google.com": "Google",
            "youtube.com": "YouTube",
        }
        return titles.get(domain, f"{domain.split('.')[0].title()} - {path.split('/')[-1].title()}")
    
    # ═══════════════════════════════════════════════════════════════════
    # V7.0 HARDENING: Pareto Distribution + Circadian Rhythm
    # Reference: Research Synthesis §4.2 — Mathematical History Generation
    # ═══════════════════════════════════════════════════════════════════

    def _circadian_weighted_hour(self) -> int:
        """
        Generate a visit hour weighted by circadian rhythm.
        Research: 'Visits are clustered during waking hours with peaks
        in the evening (18:00-22:00) and lulls during the night (02:00-06:00).'
        
        Uses a sinusoidal model with three peaks:
        - Morning peak at 10:00 (work/school)
        - Afternoon peak at 14:00 (lunch browsing)
        - Evening peak at 20:00 (leisure browsing)
        """
        # Probability weight per hour (0-23), normalized
        weights = [
            0.02, 0.01, 0.01, 0.01, 0.01, 0.02,  # 00-05: night trough
            0.03, 0.05, 0.06, 0.08, 0.09, 0.08,  # 06-11: morning rise + peak
            0.07, 0.08, 0.09, 0.07, 0.06, 0.06,  # 12-17: afternoon
            0.07, 0.08, 0.09, 0.08, 0.06, 0.04,  # 18-23: evening peak + decline
        ]
        return random.choices(range(24), weights=weights, k=1)[0]

    def _pareto_distribute_visits(self, domains: list, age_days: int,
                                   target_entries: int = 2000) -> list:
        """
        Distribute visits across domains using Pareto (80/20) power law.
        Research: 'The engine uses a Pareto Distribution to model
        realistic browsing behavior.'
        
        80% of visits go to top 20% of domains.
        Temporal distribution follows a decay curve — recent days
        have dense activity, older days have sparse visits.
        
        Returns:
            List of (domain, day_offset, visit_count) tuples
        """
        n_domains = len(domains)
        if n_domains == 0:
            return []
        
        # Pareto weights: domain rank → visit share (alpha=1.5)
        alpha = 1.5
        pareto_weights = [1.0 / ((i + 1) ** alpha) for i in range(n_domains)]
        total_w = sum(pareto_weights)
        pareto_weights = [w / total_w for w in pareto_weights]
        
        # Shuffle domains so the "top" domains are random each time
        shuffled = list(domains)
        random.shuffle(shuffled)
        
        visits = []
        for _ in range(target_entries):
            # Pick domain by Pareto weight
            domain = random.choices(shuffled, weights=pareto_weights, k=1)[0]
            
            # Temporal decay: more recent days get more visits
            # Exponential decay — lambda = 3.0/age_days
            lam = 3.0 / max(age_days, 1)
            day_offset = min(int(random.expovariate(lam)), age_days - 1)
            day_offset = max(0, day_offset)
            
            visit_count = random.randint(1, 5)
            visits.append((domain, day_offset, visit_count))
        
        return visits

    def _generate_sessionstore(self, profile_path: Path, config: AdvancedProfileConfig):
        """
        V7.0 HARDENING: Generate sessionstore.jsonlz4 with LZ4 compression.
        Research §4.4: 'Session data is stored in sessionstore.jsonlz4,
        which uses a proprietary Mozilla compression format.'
        
        Mozilla uses a custom header 'mozLz40\0' + 4-byte LE size + lz4 block.
        """
        session_data = {
            "version": ["sessionrestore", 1],
            "windows": [{
                "tabs": [{
                    "entries": [{
                        "url": "about:home",
                        "title": "New Tab",
                        "triggeringPrincipal_base64": "SmIS26zLEdO3ZQBgsLbOywAAAAAAAAAAwAAAAAAAAEY=",
                    }],
                    "lastAccessed": int(datetime.now().timestamp() * 1000),
                    "hidden": False,
                }],
                "selected": 1,
                "_closedTabs": [],
            }],
            "selectedWindow": 0,
            "_closedWindows": [],
            "session": {
                "lastUpdate": int(datetime.now().timestamp() * 1000),
                "startTime": int((datetime.now() - timedelta(days=config.profile_age_days)).timestamp() * 1000),
                "recentCrashes": 0,
            },
            "global": {},
        }
        
        json_bytes = json.dumps(session_data, separators=(',', ':')).encode('utf-8')
        
        # Mozilla LZ4 format: magic + uncompressed_size(4 LE) + lz4_block
        try:
            import lz4.block
            compressed = lz4.block.compress(json_bytes, store_size=False)
        except ImportError:
            # Fallback: write uncompressed JSON if lz4 not available
            session_file = profile_path / "sessionstore.js"
            with open(session_file, 'wb') as f:
                f.write(json_bytes)
            logger.info("[+] Session store written (uncompressed, lz4 not available)")
            return
        
        magic = b'mozLz40\0'
        size_bytes = struct.pack('<I', len(json_bytes))
        
        session_file = profile_path / "sessionstore.jsonlz4"
        with open(session_file, 'wb') as f:
            f.write(magic)
            f.write(size_bytes)
            f.write(compressed)
        
        logger.info(f"[+] Session store: {len(json_bytes)} bytes → {len(compressed)} bytes (LZ4)")

    def _add_padding_data(self, db_path: Path, size_bytes: int):
        """Add realistic-looking bulk data to reach target size.
        Instead of random hex, generates plausible analytics/cache entries."""
        conn = _fx_sqlite(db_path)
        cursor = conn.cursor()
        
        chunk_size = 1024 * 1024  # 1MB chunks
        chunks_needed = max(1, size_bytes // chunk_size)
        
        # Realistic key prefixes that analytics and ad platforms use
        prefixes = [
            "_segment_", "_fbp_", "_gcl_", "ajs_anonymous_id_",
            "intercom-session-", "mp_", "optimizely_data_",
            "__hstc_cache_", "__hssc_cache_", "_cs_c_",
            "_shopify_sa_", "_shopify_s_", "_tt_",
            "_pin_unauth_", "_uetsid_", "_uetvid_",
        ]
        
        base_time = int(datetime.now().timestamp() * 1000)
        
        for i in range(chunks_needed):
            prefix = prefixes[i % len(prefixes)]
            key = f"{prefix}{secrets.token_hex(8)}"
            # Build a large JSON blob that looks like cached analytics state
            events = []
            num_events = chunk_size // 512  # ~512 bytes per event
            for j in range(num_events):
                events.append({
                    "e": secrets.token_hex(4),
                    "ts": base_time - random.randint(0, 86400000 * 90),
                    "p": {"r": secrets.token_hex(6), "v": random.randint(1, 100)},
                })
            value = json.dumps({"v": 2, "events": events})
            
            cursor.execute("""
                INSERT OR REPLACE INTO data (key, value, utf16Length, lastAccessTime)
                VALUES (?, ?, ?, ?)
            """, (key, value, len(value), int(datetime.now().timestamp() * 1e6)))
        
        conn.commit()
        conn.close()
    
    def _calculate_size(self, profile_path: Path) -> float:
        """Calculate total profile size in MB"""
        total_size = 0
        for path in profile_path.rglob("*"):
            if path.is_file():
                total_size += path.stat().st_size
        return total_size / (1024 * 1024)


# Convenience function
def synthesize_identity(
    profile_uuid: str,
    persona_name: str,
    persona_email: str,
    billing_address: Dict[str, str],
    template: str = "student_developer",
    storage_size_mb: int = 500
) -> GeneratedAdvancedProfile:
    """
    Synthesize a high-trust identity profile.
    
    This is the main entry point for the Advanced Identity Injection Protocol.
    
    Args:
        profile_uuid: Unique identifier (e.g., "AM-8821-TRUSTED")
        persona_name: Full name (e.g., "Alex J. Mercer")
        persona_email: Email (e.g., "a.mercer.dev@gmail.com")
        billing_address: Dict with address, city, state, zip, country
        template: Narrative template ("student_developer", "professional", "gamer")
        storage_size_mb: Target localStorage size (default 500MB)
        
    Returns:
        GeneratedAdvancedProfile with full storage
    """
    config = AdvancedProfileConfig(
        profile_uuid=profile_uuid,
        persona_name=persona_name,
        persona_email=persona_email,
        billing_address=billing_address,
        localstorage_size_mb=storage_size_mb,
    )
    
    generator = AdvancedProfileGenerator()
    return generator.generate(config, template)


# Example usage
if __name__ == "__main__":
    # Synthesize Alex Mercer identity
    profile = synthesize_identity(
        profile_uuid="AM-8821-TRUSTED",
        persona_name="Alex J. Mercer",
        persona_email="a.mercer.dev@gmail.com",
        billing_address={
            "address": "2400 NUECES ST, APT 402",
            "city": "AUSTIN",
            "state": "TX",
            "zip": "78705",
            "country": "US"
        },
        template="student_developer",
        storage_size_mb=500
    )
    
    print(f"\n[+] Profile generated: {profile.profile_path}")
    print(f"[+] Size: {profile.profile_size_mb:.1f} MB")
    print(f"[+] History: {profile.history_entries} entries")
    print(f"[+] Cookies: {profile.cookies_count}")
    print(f"[+] LocalStorage: {profile.localstorage_entries} entries")
    print(f"[+] Trust Tokens: {profile.trust_tokens}")
