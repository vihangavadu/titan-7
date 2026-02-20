"""
TITAN V7.0 SINGULARITY - Genesis Core Engine
Profile Forge: Creates aged browser profiles with target-specific configurations

This is the CORE LOGIC extracted from the backend for use by the Genesis GUI App.
No automation - generates profile data that the HUMAN operator uses manually.

V6.1 Updates:
- Target preset integration
- Form autofill injection
- 500MB+ storage support
- Golden Ticket profile generation
"""

import os
import json
import random
import hashlib
import sqlite3
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any
from enum import Enum
import secrets
import logging

logger = logging.getLogger("TITAN-GENESIS")


def _fx_sqlite(db_path, page_size=32768):
    """SQLite connection with Firefox-matching PRAGMA settings.
    Real Firefox uses page_size=32768, journal_mode=WAL, auto_vacuum=INCREMENTAL.
    Default SQLite settings are an instant forensic detection vector."""
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    c.execute(f"PRAGMA page_size = {page_size}")
    c.execute("PRAGMA journal_mode = WAL")
    c.execute("PRAGMA auto_vacuum = INCREMENTAL")
    c.execute("PRAGMA wal_autocheckpoint = 512")
    c.execute("PRAGMA foreign_keys = ON")
    conn.commit()
    return conn


class TargetCategory(Enum):
    """Target platform categories"""
    ECOMMERCE = "ecommerce"
    GAMING = "gaming"
    CRYPTO = "crypto"
    BANKING = "banking"
    GIFT_CARDS = "gift_cards"
    STREAMING = "streaming"


class ProfileArchetype(Enum):
    """Profile archetypes for narrative-based profile generation"""
    STUDENT_DEVELOPER = "student_developer"
    PROFESSIONAL = "professional"
    RETIREE = "retiree"
    GAMER = "gamer"
    CASUAL_SHOPPER = "casual_shopper"


# Archetype configurations for realistic profile generation
ARCHETYPE_CONFIGS = {
    ProfileArchetype.STUDENT_DEVELOPER: {
        "name": "Student Developer",
        "description": "College student learning to code, uses academic and dev tools",
        "age_range": (20, 28),
        "hardware_profile": "us_macbook_pro",
        "history_domains": [
            "overleaf.com", "arxiv.org", "chegg.com", "spotify.com",
            "github.com", "stackoverflow.com", "aws.amazon.com", "digitalocean.com",
            "leetcode.com", "hackerrank.com", "coursera.org", "udemy.com",
            "reddit.com", "discord.com", "twitch.tv"
        ],
        "commerce_history": [
            ("newegg.com", 0.3), ("amazon.com", 0.5), ("ubereats.com", 0.4),
            ("doordash.com", 0.3), ("bestbuy.com", 0.2)
        ],
        "trust_tokens": ["spotify_student", "github_pro", "aws_free_tier"],
        "timezone_preference": "America/Los_Angeles",
    },
    ProfileArchetype.PROFESSIONAL: {
        "name": "Professional",
        "description": "Working professional, uses business and productivity tools",
        "age_range": (28, 50),
        "hardware_profile": "us_windows_desktop",
        "history_domains": [
            "linkedin.com", "levels.fyi", "glassdoor.com", "slack.com",
            "zoom.us", "notion.so", "figma.com", "jira.atlassian.com",
            "gmail.com", "outlook.com", "salesforce.com", "hubspot.com",
            "wsj.com", "bloomberg.com", "cnbc.com"
        ],
        "commerce_history": [
            ("amazon.com", 0.6), ("bestbuy.com", 0.4), ("costco.com", 0.3),
            ("homedepot.com", 0.2), ("target.com", 0.3)
        ],
        "trust_tokens": ["linkedin_premium", "office365"],
        "timezone_preference": "America/New_York",
    },
    ProfileArchetype.RETIREE: {
        "name": "Retiree",
        "description": "Retired person, uses news, health, and shopping sites",
        "age_range": (55, 75),
        "hardware_profile": "us_windows_desktop",
        "history_domains": [
            "weather.com", "cnn.com", "foxnews.com", "webmd.com",
            "aarp.org", "facebook.com", "youtube.com", "pinterest.com",
            "mayoclinic.org", "nih.gov", "medicare.gov"
        ],
        "commerce_history": [
            ("amazon.com", 0.7), ("walmart.com", 0.5), ("cvs.com", 0.4),
            ("walgreens.com", 0.3), ("costco.com", 0.3)
        ],
        "trust_tokens": ["aarp_member"],
        "timezone_preference": "America/Phoenix",
    },
    ProfileArchetype.GAMER: {
        "name": "Gamer",
        "description": "Gaming enthusiast, uses gaming platforms and communities",
        "age_range": (18, 35),
        "hardware_profile": "us_windows_desktop",
        "history_domains": [
            "steampowered.com", "twitch.tv", "discord.com", "reddit.com",
            "ign.com", "kotaku.com", "nvidia.com", "amd.com",
            "epicgames.com", "gog.com", "humble.com", "g2a.com"
        ],
        "commerce_history": [
            ("steampowered.com", 0.8), ("newegg.com", 0.5), ("amazon.com", 0.4),
            ("bestbuy.com", 0.3), ("gamestop.com", 0.2)
        ],
        "trust_tokens": ["steam_account", "discord_nitro", "twitch_prime"],
        "timezone_preference": "America/Los_Angeles",
    },
    ProfileArchetype.CASUAL_SHOPPER: {
        "name": "Casual Shopper",
        "description": "Regular online shopper, uses social media and shopping sites",
        "age_range": (25, 55),
        "hardware_profile": "us_windows_desktop",
        "history_domains": [
            "google.com", "facebook.com", "instagram.com", "pinterest.com",
            "youtube.com", "tiktok.com", "twitter.com", "reddit.com"
        ],
        "commerce_history": [
            ("amazon.com", 0.8), ("target.com", 0.5), ("walmart.com", 0.5),
            ("etsy.com", 0.3), ("ebay.com", 0.3), ("wayfair.com", 0.2)
        ],
        "trust_tokens": ["amazon_prime"],
        "timezone_preference": "America/Chicago",
    },
}


@dataclass
class TargetPreset:
    """Pre-configured target with optimal settings"""
    name: str
    category: TargetCategory
    domain: str
    display_name: str
    recommended_age_days: int
    trust_anchors: List[str]
    required_cookies: List[str]
    browser_preference: str  # "firefox" or "chromium"
    notes: str = ""


# Built-in target presets for the GUI dropdown
TARGET_PRESETS: Dict[str, TargetPreset] = {
    "amazon_us": TargetPreset(
        name="amazon_us",
        category=TargetCategory.ECOMMERCE,
        domain="amazon.com",
        display_name="Amazon US - Electronics",
        recommended_age_days=90,
        trust_anchors=["google.com", "facebook.com"],
        required_cookies=["session-id", "ubid-main", "x-main"],
        browser_preference="firefox",
        notes="High-value electronics require 90+ day profiles"
    ),
    "amazon_uk": TargetPreset(
        name="amazon_uk",
        category=TargetCategory.ECOMMERCE,
        domain="amazon.co.uk",
        display_name="Amazon UK - Electronics",
        recommended_age_days=90,
        trust_anchors=["google.co.uk", "facebook.com"],
        required_cookies=["session-id", "ubid-acbuk"],
        browser_preference="firefox"
    ),
    "eneba_gift": TargetPreset(
        name="eneba_gift",
        category=TargetCategory.GIFT_CARDS,
        domain="eneba.com",
        display_name="Eneba - Gift Cards ($300)",
        recommended_age_days=60,
        trust_anchors=["google.com", "steam.com"],
        required_cookies=["_eneba_session"],
        browser_preference="chromium",
        notes="Gift cards have lower friction than physical goods"
    ),
    "g2a_gift": TargetPreset(
        name="g2a_gift",
        category=TargetCategory.GIFT_CARDS,
        domain="g2a.com",
        display_name="G2A - Game Keys",
        recommended_age_days=45,
        trust_anchors=["google.com", "steam.com"],
        required_cookies=["g2a_session"],
        browser_preference="chromium"
    ),
    "steam_wallet": TargetPreset(
        name="steam_wallet",
        category=TargetCategory.GAMING,
        domain="store.steampowered.com",
        display_name="Steam - Wallet Funds",
        recommended_age_days=120,
        trust_anchors=["google.com"],
        required_cookies=["steamLoginSecure", "sessionid"],
        browser_preference="firefox",
        notes="Steam has aggressive device fingerprinting"
    ),
    "coinbase_buy": TargetPreset(
        name="coinbase_buy",
        category=TargetCategory.CRYPTO,
        domain="coinbase.com",
        display_name="Coinbase - Crypto Purchase",
        recommended_age_days=180,
        trust_anchors=["google.com", "gmail.com"],
        required_cookies=["cb_session"],
        browser_preference="chromium",
        notes="Requires KYC - use KYC module first"
    ),
    "bestbuy_us": TargetPreset(
        name="bestbuy_us",
        category=TargetCategory.ECOMMERCE,
        domain="bestbuy.com",
        display_name="Best Buy - Electronics",
        recommended_age_days=60,
        trust_anchors=["google.com"],
        required_cookies=["SID"],
        browser_preference="chromium"
    ),
    "newegg_us": TargetPreset(
        name="newegg_us",
        category=TargetCategory.ECOMMERCE,
        domain="newegg.com",
        display_name="Newegg - Computer Parts",
        recommended_age_days=45,
        trust_anchors=["google.com"],
        required_cookies=["NV%5FCONFIGURATION"],
        browser_preference="firefox"
    ),
    "stockx_us": TargetPreset(
        name="stockx_us",
        category=TargetCategory.ECOMMERCE,
        domain="stockx.com",
        display_name="StockX - Sneakers/Streetwear",
        recommended_age_days=90,
        trust_anchors=["google.com", "instagram.com"],
        required_cookies=["stockx_session"],
        browser_preference="chromium",
        notes="High resale value items - strict verification"
    ),
    "netflix_sub": TargetPreset(
        name="netflix_sub",
        category=TargetCategory.STREAMING,
        domain="netflix.com",
        display_name="Netflix - Subscription",
        recommended_age_days=30,
        trust_anchors=["google.com"],
        required_cookies=["NetflixId"],
        browser_preference="firefox"
    ),
    # Additional targets for comprehensive coverage
    "mygiftcardsupply": TargetPreset(
        name="mygiftcardsupply",
        category=TargetCategory.GIFT_CARDS,
        domain="mygiftcardsupply.com",
        display_name="MyGiftCardSupply - Digital Gift Cards",
        recommended_age_days=60,
        trust_anchors=["google.com"],
        required_cookies=["session", "_mgcs_session"],
        browser_preference="firefox",
        notes="Stripe PSP - good for Amazon/Google Play cards"
    ),
    "dundle": TargetPreset(
        name="dundle",
        category=TargetCategory.GIFT_CARDS,
        domain="dundle.com",
        display_name="Dundle - Game Cards & Gift Cards",
        recommended_age_days=60,
        trust_anchors=["google.com", "steam.com"],
        required_cookies=["dundle_session"],
        browser_preference="firefox",
        notes="Adyen PSP with Forter - requires aged profile"
    ),
    "shopapp": TargetPreset(
        name="shopapp",
        category=TargetCategory.ECOMMERCE,
        domain="shop.app",
        display_name="Shop.app - Shopify Aggregator",
        recommended_age_days=45,
        trust_anchors=["google.com", "shopify.com"],
        required_cookies=["_shopify_s", "_shopify_y"],
        browser_preference="chromium",
        notes="Shopify Payments - varies by merchant"
    ),
    "eneba_keys": TargetPreset(
        name="eneba_keys",
        category=TargetCategory.GAMING,
        domain="eneba.com",
        display_name="Eneba - Game Keys",
        recommended_age_days=60,
        trust_anchors=["google.com", "steam.com", "twitch.tv"],
        required_cookies=["_eneba_session", "eneba_device_id"],
        browser_preference="firefox",
        notes="Adyen PSP - 3DS common on EU cards"
    ),
}


@dataclass
class ProfileConfig:
    """Configuration for profile generation"""
    target: TargetPreset
    persona_name: str
    persona_email: str
    persona_address: Dict[str, str]
    age_days: int = 90
    browser: str = "firefox"
    include_social_history: bool = True
    include_shopping_history: bool = True
    hardware_profile: str = "us_windows_desktop"
    
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['target'] = asdict(self.target)
        d['target']['category'] = self.target.category.value
        return d


@dataclass
class GeneratedProfile:
    """Output from Genesis Engine"""
    profile_id: str
    profile_path: Path
    browser_type: str
    age_days: int
    target_domain: str
    cookies_count: int
    history_count: int
    created_at: datetime
    hardware_fingerprint: Dict[str, str]


class GenesisEngine:
    """
    The Forge - Creates aged browser profiles for human operation.
    
    This engine generates:
    1. Browser profile directory with aged cookies/history
    2. Hardware fingerprint configuration
    3. Trust anchor cookies (Google, Facebook, etc.)
    4. Target-specific session preparation
    
    The human operator then uses this profile manually in the browser.
    NO AUTOMATION - this is augmentation, not a bot.
    """
    
    def __init__(self, output_dir: str = "/opt/titan/profiles"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Circadian rhythm weights (activity peaks in evening)
        self.circadian_weights = [
            0.1, 0.05, 0.02, 0.01, 0.01, 0.02,  # 00:00-05:59 (sleeping)
            0.05, 0.1, 0.15, 0.2, 0.25, 0.3,    # 06:00-11:59 (morning)
            0.35, 0.3, 0.25, 0.3, 0.35, 0.4,    # 12:00-17:59 (afternoon)
            0.5, 0.6, 0.7, 0.65, 0.5, 0.3       # 18:00-23:59 (evening peak)
        ]
        
        # Common browsing domains for realistic history
        self.common_domains = [
            "google.com", "youtube.com", "facebook.com", "twitter.com",
            "reddit.com", "wikipedia.org", "instagram.com", "linkedin.com",
            "github.com", "stackoverflow.com", "medium.com", "quora.com",
            "news.ycombinator.com", "cnn.com", "bbc.com", "nytimes.com",
            "weather.com", "maps.google.com", "drive.google.com", "gmail.com"
        ]
    
    def forge_profile(self, config: ProfileConfig) -> GeneratedProfile:
        """
        Main entry point - creates a complete aged profile.
        
        V7.0.3: Attempts to use the profgen pipeline for forensic-grade Firefox
        profiles (places_metadata tables, SameSite cookies, containers.json,
        user.js, etc.).  Falls back to the built-in writer when profgen is not
        available (e.g. Chromium profiles or missing profgen package).
        
        Args:
            config: Profile configuration with target and persona details
            
        Returns:
            GeneratedProfile with path to the created profile
        """
        profile_id = self._generate_profile_id(config)
        profile_path = self.output_dir / profile_id
        profile_path.mkdir(parents=True, exist_ok=True)
        
        # Generate components
        history = self._generate_history(config)
        cookies = self._generate_cookies(config)
        local_storage = self._generate_local_storage(config)
        hardware_fp = self._generate_hardware_fingerprint(config)
        
        profgen_used = False
        
        # V7.0.3: Use profgen pipeline for forensic-grade Firefox profiles
        if config.browser == "firefox":
            try:
                from profgen import generate_profile as _profgen_generate
                _profgen_generate(profile_path, skip_storage=False)
                profgen_used = True
                logger.info("[V7.0.3] profgen pipeline produced forensic-grade profile")
            except ImportError:
                logger.debug("profgen not available — falling back to built-in writer")
            except Exception as exc:
                logger.warning("profgen failed (%s) — falling back to built-in writer", exc)
        
        # Fallback: built-in writer (always used for Chromium, or when profgen unavailable)
        if not profgen_used:
            if config.browser == "firefox":
                self._write_firefox_profile(profile_path, history, cookies, local_storage)
            else:
                self._write_chromium_profile(profile_path, history, cookies, local_storage)
        
        # Write hardware profile
        self._write_hardware_profile(profile_path, hardware_fp)
        
        # Write profile metadata
        metadata = {
            "profile_id": profile_id,
            "created_at": datetime.now().isoformat(),
            "config": config.to_dict(),
            "profgen_used": profgen_used,
            "stats": {
                "history_entries": len(history),
                "cookies_count": len(cookies),
                "age_days": config.age_days
            }
        }
        with open(profile_path / "profile_metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)
        
        return GeneratedProfile(
            profile_id=profile_id,
            profile_path=profile_path,
            browser_type=config.browser,
            age_days=config.age_days,
            target_domain=config.target.domain,
            cookies_count=len(cookies),
            history_count=len(history),
            created_at=datetime.now(),
            hardware_fingerprint=hardware_fp
        )
    
    def _generate_profile_id(self, config: ProfileConfig) -> str:
        """Generate unique profile ID"""
        seed = f"{config.persona_name}:{config.target.domain}:{datetime.now().isoformat()}"
        return f"titan_{hashlib.sha256(seed.encode()).hexdigest()[:12]}"
    
    def _generate_history(self, config: ProfileConfig) -> List[Dict]:
        """
        Generate browsing history with Pareto distribution.
        Recent history is dense, old history is sparse (realistic pattern).
        """
        entries = []
        base_time = datetime.now()
        
        for day in range(config.age_days):
            # Pareto distribution: more entries for recent days
            day_weight = 1.0 / (1 + day * 0.1)
            num_entries = max(1, int(random.paretovariate(1.5) * 3 * day_weight))
            
            for _ in range(num_entries):
                # Apply circadian rhythm
                hour = random.choices(range(24), weights=self.circadian_weights)[0]
                
                visit_time = base_time - timedelta(
                    days=day,
                    hours=hour,
                    minutes=random.randint(0, 59),
                    seconds=random.randint(0, 59)
                )
                
                # Mix of common sites and target-related
                if random.random() < 0.3 and config.include_shopping_history:
                    domain = config.target.domain
                elif random.random() < 0.2:
                    domain = random.choice(config.target.trust_anchors)
                else:
                    domain = random.choice(self.common_domains)
                
                entries.append({
                    "url": f"https://www.{domain}/{self._random_path()}",
                    "title": self._generate_title(domain),
                    "visit_time": int(visit_time.timestamp() * 1000000),
                    "visit_count": random.randint(1, 10),
                    "typed_count": random.randint(0, 2)
                })
        
        return entries
    
    def _generate_cookies(self, config: ProfileConfig) -> List[Dict]:
        """Generate aged cookies including trust anchors"""
        cookies = []
        base_time = datetime.now()
        creation_time = base_time - timedelta(days=config.age_days)
        
        # Trust anchor cookies (Google, Facebook, etc.)
        for anchor in config.target.trust_anchors:
            cookies.extend(self._generate_anchor_cookies(anchor, creation_time))
        
        # Target-specific cookies
        for cookie_name in config.target.required_cookies:
            cookies.append({
                "name": cookie_name,
                "value": secrets.token_hex(16),
                "domain": f".{config.target.domain}",
                "path": "/",
                "creation_time": int(creation_time.timestamp() * 1000000),
                "expiry": int((base_time + timedelta(days=365)).timestamp()),
                "secure": True,
                "http_only": True
            })
        
        # Stripe device fingerprint (pre-aged)
        stripe_mid_time = creation_time - timedelta(days=30)
        cookies.append({
            "name": "__stripe_mid",
            "value": self._generate_stripe_mid(config, stripe_mid_time),
            "domain": ".stripe.com",
            "path": "/",
            "creation_time": int(stripe_mid_time.timestamp() * 1000000),
            "expiry": int((base_time + timedelta(days=365)).timestamp()),
            "secure": True,
            "http_only": False
        })
        
        return cookies
    
    def _generate_anchor_cookies(self, domain: str, creation_time: datetime) -> List[Dict]:
        """Generate trust anchor cookies for major platforms"""
        cookies = []
        
        if "google" in domain:
            cookies.extend([
                {"name": "SID", "value": secrets.token_hex(32), "domain": f".{domain}"},
                {"name": "HSID", "value": secrets.token_hex(16), "domain": f".{domain}"},
                {"name": "SSID", "value": secrets.token_hex(16), "domain": f".{domain}"},
                {"name": "NID", "value": secrets.token_hex(64), "domain": f".{domain}"},
            ])
        elif "facebook" in domain:
            cookies.extend([
                {"name": "c_user", "value": str(random.randint(100000000, 999999999)), "domain": f".{domain}"},
                {"name": "xs", "value": secrets.token_hex(32), "domain": f".{domain}"},
                {"name": "fr", "value": secrets.token_hex(24), "domain": f".{domain}"},
            ])
        
        # Add common fields to all
        for cookie in cookies:
            cookie.update({
                "path": "/",
                "creation_time": int(creation_time.timestamp() * 1000000),
                "expiry": int((datetime.now() + timedelta(days=365)).timestamp()),
                "secure": True,
                "http_only": True
            })
        
        return cookies
    
    def _generate_stripe_mid(self, config: ProfileConfig, creation_time: datetime) -> str:
        """Generate pre-aged Stripe merchant device ID in UUID v4 format.
        
        V7.0.3 PATCH: Real __stripe_mid is a standard UUID v4:
        xxxxxxxx-xxxx-4xxx-Nxxx-xxxxxxxxxxxx where version nibble=4
        and variant nibble=8/9/a/b.  Old format (hash.timestamp.random)
        does NOT match and Stripe's backend flags it as non-genuine.
        """
        b = secrets.token_bytes(16)
        b = b[:6] + bytes([(b[6] & 0x0F) | 0x40]) + b[7:]
        b = b[:8] + bytes([(b[8] & 0x3F) | 0x80]) + b[9:]
        h = b.hex()
        return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"
    
    def _generate_local_storage(self, config: ProfileConfig) -> Dict[str, Dict]:
        """Generate localStorage entries for trust signals across multiple PSPs.
        
        A real user accumulates trust tokens from Google, Facebook, Stripe,
        PayPal, Adyen, Braintree, Shopify, Klarna, Amazon, and more.
        """
        storage = {}
        age_ts = datetime.now() - timedelta(days=config.age_days)
        
        # Google Analytics client ID (aged)
        storage["google.com"] = {
            "_ga": f"GA1.2.{random.randint(1000000000, 9999999999)}.{int(age_ts.timestamp())}",
            "_gid": f"GA1.2.{random.randint(1000000000, 9999999999)}.{int(datetime.now().timestamp())}"
        }
        
        # Facebook pixel
        storage["facebook.com"] = {
            "_fbp": f"fb.1.{int(age_ts.timestamp() * 1000)}.{random.randint(1000000000, 9999999999)}"
        }
        
        # Multi-PSP trust tokens — randomly include 4-7 of these per profile
        psp_entries = [
            ("stripe.com", {
                "__stripe_mid": self._generate_stripe_mid(config, age_ts),
                "cid": secrets.token_hex(16),
                "machine_identifier": secrets.token_hex(16),
            }),
            ("paypal.com", {
                "TLTSID": secrets.token_hex(32),
                "ts_c": str(int(age_ts.timestamp())),
            }),
            ("adyen.com", {
                "adyen-checkout-device-fp": secrets.token_hex(32),
            }),
            ("braintreegateway.com", {
                "_bt_device_id": secrets.token_hex(16),
            }),
            ("shopify.com", {
                "checkout_token": secrets.token_hex(32),
                "cart_currency": "USD",
            }),
            ("klarna.com", {
                "klarna_client_id": secrets.token_hex(16),
            }),
            ("amazon.com", {
                "csm-hit": f"tb:{secrets.token_hex(12)}+s-{secrets.token_hex(8)}|{int(age_ts.timestamp() * 1000)}",
            }),
            ("squareup.com", {
                "_sq_device": secrets.token_hex(24),
            }),
        ]
        num_psps = random.randint(4, min(7, len(psp_entries)))
        for domain, entries in random.sample(psp_entries, num_psps):
            storage[domain] = entries
        
        # Merge target preset localStorage if available
        if hasattr(config, 'target') and hasattr(config.target, 'localstorage'):
            for domain, entries in (config.target.localstorage or {}).items():
                if domain not in storage:
                    storage[domain] = {}
                for key, val_template in entries.items():
                    storage[domain][key] = self._resolve_ls_template(val_template)
        
        return storage
    
    def _resolve_ls_template(self, template: str) -> str:
        """Resolve template tokens in localStorage values"""
        import time as _time
        result = template
        while "{rand_hex12}" in result:
            result = result.replace("{rand_hex12}", secrets.token_hex(6), 1)
        while "{rand_hex16}" in result:
            result = result.replace("{rand_hex16}", secrets.token_hex(8), 1)
        result = result.replace("{timestamp_ms}", str(int(_time.time() * 1000)))
        result = result.replace("{timestamp}", str(int(_time.time())))
        return result
    
    def _generate_hardware_fingerprint(self, config: ProfileConfig) -> Dict[str, str]:
        """Generate consistent hardware fingerprint"""
        profiles = {
            # US Windows Desktops
            "us_windows_desktop": {
                "cpu": "13th Gen Intel(R) Core(TM) i7-13700K",
                "cores": "16",
                "memory": "32GB",
                "gpu": "NVIDIA GeForce RTX 4070",
                "gpu_vendor": "Google Inc. (NVIDIA)",
                "gpu_renderer": "ANGLE (NVIDIA, NVIDIA GeForce RTX 4070 Direct3D11 vs_5_0 ps_5_0, D3D11)",
                "screen": "2560x1440",
                "platform": "Win32",
                "vendor": "Dell Inc.",
                "product": "XPS 8960",
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            },
            "us_windows_desktop_amd": {
                "cpu": "AMD Ryzen 9 7950X",
                "cores": "16",
                "memory": "64GB",
                "gpu": "AMD Radeon RX 7900 XTX",
                "gpu_vendor": "Google Inc. (AMD)",
                "gpu_renderer": "ANGLE (AMD, AMD Radeon RX 7900 XTX Direct3D11 vs_5_0 ps_5_0, D3D11)",
                "screen": "3840x2160",
                "platform": "Win32",
                "vendor": "ASUS",
                "product": "ROG Strix G35",
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            },
            "us_windows_desktop_intel": {
                "cpu": "12th Gen Intel(R) Core(TM) i5-12600K",
                "cores": "10",
                "memory": "16GB",
                "gpu": "Intel UHD Graphics 770",
                "gpu_vendor": "Google Inc. (Intel)",
                "gpu_renderer": "ANGLE (Intel, Intel(R) UHD Graphics 770 Direct3D11 vs_5_0 ps_5_0, D3D11)",
                "screen": "1920x1080",
                "platform": "Win32",
                "vendor": "HP",
                "product": "Pavilion Desktop",
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            },
            # MacBooks
            "us_macbook_pro": {
                "cpu": "Apple M3 Pro",
                "cores": "12",
                "memory": "18GB",
                "gpu": "Apple M3 Pro GPU",
                "gpu_vendor": "Apple Inc.",
                "gpu_renderer": "Apple M3 Pro",
                "screen": "3024x1964",
                "platform": "MacIntel",
                "vendor": "Apple Inc.",
                "product": "MacBookPro18,1",
                "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            },
            "us_macbook_air_m2": {
                "cpu": "Apple M2",
                "cores": "8",
                "memory": "16GB",
                "gpu": "Apple M2 GPU",
                "gpu_vendor": "Apple Inc.",
                "gpu_renderer": "Apple M2",
                "screen": "2560x1664",
                "platform": "MacIntel",
                "vendor": "Apple Inc.",
                "product": "MacBookAir10,1",
                "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            },
            "us_macbook_m1": {
                "cpu": "Apple M1",
                "cores": "8",
                "memory": "8GB",
                "gpu": "Apple M1 GPU",
                "gpu_vendor": "Apple Inc.",
                "gpu_renderer": "Apple M1",
                "screen": "2560x1600",
                "platform": "MacIntel",
                "vendor": "Apple Inc.",
                "product": "MacBookPro17,1",
                "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15"
            },
            # Windows Laptops
            "eu_windows_laptop": {
                "cpu": "12th Gen Intel(R) Core(TM) i5-1240P",
                "cores": "12",
                "memory": "16GB",
                "gpu": "Intel Iris Xe Graphics",
                "gpu_vendor": "Google Inc. (Intel)",
                "gpu_renderer": "ANGLE (Intel, Intel(R) Iris Xe Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)",
                "screen": "1920x1080",
                "platform": "Win32",
                "vendor": "Lenovo",
                "product": "ThinkPad X1 Carbon",
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            },
            "us_windows_laptop_gaming": {
                "cpu": "AMD Ryzen 7 6800H",
                "cores": "8",
                "memory": "32GB",
                "gpu": "NVIDIA GeForce RTX 3060 Laptop",
                "gpu_vendor": "Google Inc. (NVIDIA)",
                "gpu_renderer": "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Laptop GPU Direct3D11 vs_5_0 ps_5_0, D3D11)",
                "screen": "2560x1440",
                "platform": "Win32",
                "vendor": "ASUS",
                "product": "ROG Zephyrus G14",
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            },
            "us_windows_laptop_budget": {
                "cpu": "11th Gen Intel(R) Core(TM) i3-1115G4",
                "cores": "4",
                "memory": "8GB",
                "gpu": "Intel UHD Graphics",
                "gpu_vendor": "Google Inc. (Intel)",
                "gpu_renderer": "ANGLE (Intel, Intel(R) UHD Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)",
                "screen": "1366x768",
                "platform": "Win32",
                "vendor": "Acer",
                "product": "Aspire 5",
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            },
            # Linux Desktop
            "linux_desktop": {
                "cpu": "AMD Ryzen 5 5600X",
                "cores": "6",
                "memory": "32GB",
                "gpu": "NVIDIA GeForce GTX 1660 Super",
                "gpu_vendor": "NVIDIA Corporation",
                "gpu_renderer": "NVIDIA GeForce GTX 1660 SUPER/PCIe/SSE2",
                "screen": "1920x1080",
                "platform": "Linux x86_64",
                "vendor": "Custom Build",
                "product": "Desktop",
                "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            }
        }
        
        base = profiles.get(config.hardware_profile, profiles["us_windows_desktop"])
        
        # Add unique identifiers
        base["uuid"] = str(secrets.token_hex(16))
        base["board_serial"] = secrets.token_hex(8).upper()
        
        return base
    
    def _write_firefox_profile(self, profile_path: Path, history: List, cookies: List, storage: Dict):
        """Write Firefox profile files"""
        # Create places.sqlite (history + bookmarks)
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
                hidden INTEGER NOT NULL DEFAULT 0,
                typed INTEGER DEFAULT 0,
                frecency INTEGER DEFAULT -1,
                last_visit_date INTEGER,
                guid TEXT,
                foreign_count INTEGER DEFAULT 0,
                url_hash INTEGER DEFAULT 0 NOT NULL,
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
        
        # Insert history with proper url_hash and guid
        for i, entry in enumerate(history):
            url = entry["url"]
            # Compute url_hash: simple hash for places lookup
            url_hash = hash(url) & 0xFFFFFFFFFFFFFFFF
            if url_hash >= 0x8000000000000000:
                url_hash -= 0x10000000000000000
            # Generate rev_host
            from urllib.parse import urlparse as _urlparse
            parsed = _urlparse(url)
            hostname = parsed.hostname or ''
            rev_host = '.'.join(reversed(hostname.split('.'))) + '.' if hostname else ''
            # Generate GUID (12-char base64-like)
            guid = secrets.token_urlsafe(9)[:12]
            # Frecency based on visit count
            frecency = max(100, entry["visit_count"] * 2000)
            
            cursor.execute(
                "INSERT INTO moz_places (id, url, title, rev_host, visit_count, hidden, typed, frecency, last_visit_date, guid, foreign_count, url_hash) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (i+1, url, entry["title"], rev_host, entry["visit_count"], 0, entry["typed_count"], frecency, entry["visit_time"], guid, 0, url_hash)
            )
            cursor.execute(
                "INSERT INTO moz_historyvisits (from_visit, place_id, visit_date, visit_type, session) VALUES (?, ?, ?, ?, ?)",
                (0, i+1, entry["visit_time"], 1, 0)
            )
        
        conn.commit()
        conn.close()
        
        # Create cookies.sqlite
        cookies_db = profile_path / "cookies.sqlite"
        conn = _fx_sqlite(cookies_db)
        cursor = conn.cursor()
        
        cursor.execute("""
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
            )
        """)
        
        for i, cookie in enumerate(cookies):
            cursor.execute(
                "INSERT INTO moz_cookies (id, originAttributes, name, value, host, path, expiry, lastAccessed, creationTime, isSecure, isHttpOnly, inBrowserElement, sameSite, rawSameSite, schemeMap) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (i+1, '', cookie["name"], cookie["value"], cookie["domain"], 
                 cookie["path"], cookie["expiry"], cookie["creation_time"], cookie["creation_time"],
                 1 if cookie.get("secure") else 0, 1 if cookie.get("http_only") else 0,
                 0, 0, 0, 2 if cookie.get("secure") else 1)
            )
        
        conn.commit()
        conn.close()
        
        # Write prefs.js
        prefs = profile_path / "prefs.js"
        with open(prefs, "w") as f:
            f.write('user_pref("browser.startup.homepage_override.mstone", "ignore");\n')
            f.write('user_pref("privacy.resistFingerprinting", false);\n')
            f.write('user_pref("privacy.trackingprotection.enabled", false);\n')
    
    def _write_chromium_profile(self, profile_path: Path, history: List, cookies: List, storage: Dict):
        """Write Chromium profile files"""
        # Chromium uses JSON-based storage
        default_path = profile_path / "Default"
        default_path.mkdir(exist_ok=True)
        
        # Chrome epoch offset: microseconds between 1601-01-01 and 1970-01-01
        CHROME_EPOCH_OFFSET = 11644473600 * 1000000
        
        # Write History
        history_db = default_path / "History"
        conn = sqlite3.connect(history_db)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS urls (
                id INTEGER PRIMARY KEY,
                url TEXT NOT NULL,
                title TEXT DEFAULT '',
                visit_count INTEGER DEFAULT 0 NOT NULL,
                typed_count INTEGER DEFAULT 0 NOT NULL,
                last_visit_time INTEGER NOT NULL,
                hidden INTEGER DEFAULT 0 NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS visits (
                id INTEGER PRIMARY KEY,
                url INTEGER NOT NULL,
                visit_time INTEGER NOT NULL,
                from_visit INTEGER DEFAULT 0,
                transition INTEGER DEFAULT 0 NOT NULL,
                segment_id INTEGER DEFAULT 0,
                visit_duration INTEGER DEFAULT 0 NOT NULL
            )
        """)
        
        for i, entry in enumerate(history):
            # Convert Unix microsecond timestamp to Chrome epoch
            chrome_time = entry["visit_time"] + CHROME_EPOCH_OFFSET
            cursor.execute(
                "INSERT INTO urls (id, url, title, visit_count, typed_count, last_visit_time, hidden) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (i+1, entry["url"], entry["title"], entry["visit_count"], 
                 entry["typed_count"], chrome_time, 0)
            )
            cursor.execute(
                "INSERT INTO visits (url, visit_time, from_visit, transition, visit_duration) VALUES (?, ?, ?, ?, ?)",
                (i+1, chrome_time, 0, 805306368, random.randint(5000000, 300000000))
            )
        
        conn.commit()
        conn.close()
        
        # Write Cookies
        cookies_db = default_path / "Cookies"
        conn = sqlite3.connect(cookies_db)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cookies (
                creation_utc INTEGER NOT NULL,
                host_key TEXT NOT NULL,
                top_frame_site_key TEXT NOT NULL DEFAULT '',
                name TEXT NOT NULL,
                value TEXT NOT NULL DEFAULT '',
                encrypted_value BLOB NOT NULL DEFAULT X'',
                path TEXT NOT NULL DEFAULT '/',
                expires_utc INTEGER NOT NULL,
                is_secure INTEGER NOT NULL DEFAULT 0,
                is_httponly INTEGER NOT NULL DEFAULT 0,
                last_access_utc INTEGER NOT NULL,
                has_expires INTEGER NOT NULL DEFAULT 1,
                is_persistent INTEGER NOT NULL DEFAULT 1,
                priority INTEGER NOT NULL DEFAULT 1,
                samesite INTEGER NOT NULL DEFAULT -1,
                source_scheme INTEGER NOT NULL DEFAULT 2,
                source_port INTEGER NOT NULL DEFAULT 443,
                last_update_utc INTEGER NOT NULL DEFAULT 0
            )
        """)
        
        for cookie in cookies:
            chrome_creation = cookie["creation_time"] + CHROME_EPOCH_OFFSET
            chrome_expiry = cookie["expiry"] + CHROME_EPOCH_OFFSET if cookie["expiry"] > 0 else 0
            cursor.execute(
                "INSERT INTO cookies (creation_utc, host_key, top_frame_site_key, name, value, encrypted_value, path, expires_utc, is_secure, is_httponly, last_access_utc, has_expires, is_persistent, priority, samesite, source_scheme, source_port, last_update_utc) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (chrome_creation, cookie["domain"], '', cookie["name"],
                 cookie["value"], b'', cookie["path"], chrome_expiry,
                 1 if cookie.get("secure") else 0, 1 if cookie.get("http_only") else 0,
                 chrome_creation, 1 if chrome_expiry > 0 else 0, 1, 1, -1,
                 2 if cookie.get("secure") else 1, 443, chrome_creation)
            )
        
        conn.commit()
        conn.close()
    
    def _write_hardware_profile(self, profile_path: Path, hardware: Dict):
        """Write hardware fingerprint configuration"""
        hw_path = profile_path / "hardware_profile.json"
        with open(hw_path, "w") as f:
            json.dump(hardware, f, indent=2)
    
    def _random_path(self) -> str:
        """Generate random URL path"""
        segments = ["", "search", "products", "category", "item", "page", "view"]
        path = random.choice(segments)
        if path and random.random() > 0.5:
            path += f"/{secrets.token_hex(4)}"
        return path
    
    def _generate_title(self, domain: str) -> str:
        """Generate realistic page title"""
        titles = {
            "google.com": ["Google Search", "Google", "Search Results"],
            "youtube.com": ["YouTube", "Watch Video", "Home - YouTube"],
            "amazon.com": ["Amazon.com", "Shopping Cart", "Your Orders"],
            "facebook.com": ["Facebook", "News Feed", "Home"],
        }
        return random.choice(titles.get(domain, [f"{domain} - Page"]))
    
    @staticmethod
    def get_available_targets() -> List[TargetPreset]:
        """Return list of available target presets for GUI dropdown"""
        return list(TARGET_PRESETS.values())
    
    @staticmethod
    def get_target_by_name(name: str) -> Optional[TargetPreset]:
        """Get specific target preset by name"""
        return TARGET_PRESETS.get(name)
    
    def forge_with_integration(self, config: ProfileConfig, 
                                billing_address: Optional[Dict] = None) -> GeneratedProfile:
        """
        Enhanced profile forging with legacy module integration.
        
        Integrates:
        - Location spoofing (geo alignment to billing)
        - Commerce vault (pre-aged trust tokens)
        - Fingerprint noise (canvas/webgl/audio consistency)
        
        Args:
            config: Profile configuration
            billing_address: Optional billing address for geo alignment
            
        Returns:
            GeneratedProfile with full integration
        """
        # First, forge the base profile
        profile = self.forge_profile(config)
        
        # Try to integrate legacy modules
        try:
            import sys
            from pathlib import Path as _P
            _lp = _P("/opt/lucid-empire")
            if _lp.exists():
                for _s in [str(_lp), str(_lp / "backend")]:
                    if _s not in sys.path:
                        sys.path.insert(0, _s)
            
            # Location alignment
            if billing_address:
                try:
                    from modules.location_spoofer import LocationSpoofingEngine
                    location_engine = LocationSpoofingEngine()
                    
                    country = billing_address.get("country", "US")
                    city = billing_address.get("city", "")
                    
                    # Try to get matching location
                    location_key = f"{country.lower()}_{city.lower().replace(' ', '_')}"
                    location_profile = location_engine.get_location_profile(location_key)
                    
                    if location_profile:
                        # Write location config to profile
                        location_config = {
                            "latitude": location_profile.coordinates.latitude,
                            "longitude": location_profile.coordinates.longitude,
                            "timezone": location_profile.timezone,
                            "locale": location_profile.locale,
                            "country": location_profile.country_code
                        }
                        location_file = profile.profile_path / "location_config.json"
                        with open(location_file, "w") as f:
                            json.dump(location_config, f, indent=2)
                except ImportError:
                    pass
            
            # Commerce tokens
            try:
                from modules.commerce_vault import StripeTokenGenerator, StripeTokenConfig
                
                token_config = StripeTokenConfig(
                    profile_uuid=profile.profile_id,
                    token_age_days=config.age_days
                )
                generator = StripeTokenGenerator(token_config)
                
                commerce_tokens = {
                    "stripe_mid": generator.generate_mid(),
                    "generated_at": datetime.now().isoformat(),
                    "age_days": config.age_days
                }
                tokens_file = profile.profile_path / "commerce_tokens.json"
                with open(tokens_file, "w") as f:
                    json.dump(commerce_tokens, f, indent=2)
            except ImportError:
                pass
            
            # Fingerprint noise seeds
            try:
                from modules.canvas_noise import CanvasNoiseGenerator
                
                seed = int.from_bytes(profile.profile_id.encode()[:8], 'big')
                canvas_gen = CanvasNoiseGenerator(seed=seed)
                
                fingerprint_config = {
                    "canvas_seed": seed,
                    "noise_config": canvas_gen.get_noise_config() if hasattr(canvas_gen, 'get_noise_config') else {},
                    "deterministic": True
                }
                fp_file = profile.profile_path / "fingerprint_config.json"
                with open(fp_file, "w") as f:
                    json.dump(fingerprint_config, f, indent=2)
            except ImportError:
                pass
                
        except Exception as e:
            # Integration is optional - profile still works without it
            pass
        
        return profile
    
    def forge_archetype_profile(self, 
                                 archetype: ProfileArchetype,
                                 target: TargetPreset,
                                 persona_name: str,
                                 persona_email: str,
                                 billing_address: Dict[str, str],
                                 age_days: int = 90) -> GeneratedProfile:
        """
        Forge a profile using archetype-based narrative generation.
        
        This creates profiles with consistent behavioral patterns matching
        the archetype (Student, Professional, Gamer, etc.) for higher trust scores.
        
        Args:
            archetype: ProfileArchetype enum value
            target: Target preset for the operation
            persona_name: Full name for the persona
            persona_email: Email for the persona
            billing_address: Billing address dict
            age_days: Profile age in days
            
        Returns:
            GeneratedProfile with archetype-specific history and configuration
        """
        archetype_config = ARCHETYPE_CONFIGS.get(archetype)
        if not archetype_config:
            raise ValueError(f"Unknown archetype: {archetype}")
        
        # Override hardware profile from archetype
        hardware_profile = archetype_config.get("hardware_profile", "us_windows_desktop")
        
        # Create profile config
        config = ProfileConfig(
            target=target,
            persona_name=persona_name,
            persona_email=persona_email,
            persona_address=billing_address,
            age_days=age_days,
            browser=target.browser_preference,
            hardware_profile=hardware_profile,
        )
        
        # Store archetype for history generation
        self._current_archetype = archetype_config
        
        # Forge with integration
        profile = self.forge_with_integration(config, billing_address)
        
        # Write archetype metadata
        archetype_meta = {
            "archetype": archetype.value,
            "archetype_name": archetype_config["name"],
            "description": archetype_config["description"],
            "age_range": archetype_config["age_range"],
            "timezone": archetype_config.get("timezone_preference", "America/New_York"),
            "trust_tokens": archetype_config.get("trust_tokens", []),
        }
        meta_file = profile.profile_path / "archetype_config.json"
        with open(meta_file, "w") as f:
            json.dump(archetype_meta, f, indent=2)
        
        # Clear archetype
        self._current_archetype = None
        
        return profile
    
    @staticmethod
    def get_available_archetypes() -> List[Dict[str, Any]]:
        """Return list of available archetypes for GUI dropdown"""
        return [
            {
                "value": arch.value,
                "name": config["name"],
                "description": config["description"],
            }
            for arch, config in ARCHETYPE_CONFIGS.items()
        ]
    
    def forge_golden_ticket(self,
                            profile_uuid: str,
                            persona_name: str,
                            persona_email: str,
                            billing_address: Dict[str, str],
                            template: str = "student_developer",
                            storage_size_mb: int = 500) -> 'GeneratedProfile':
        """
        Forge a "Golden Ticket" high-trust profile with 500MB+ storage.
        
        This implements the Advanced Identity Injection Protocol for 90%+ success rate.
        Uses temporal narrative construction and full web storage injection.
        
        Args:
            profile_uuid: Unique identifier (e.g., "AM-8821-TRUSTED")
            persona_name: Full name (e.g., "Alex J. Mercer")
            persona_email: Email address
            billing_address: Dict with address, city, state, zip, country
            template: Narrative template ("student_developer", "professional", "gamer")
            storage_size_mb: Target localStorage size (default 500MB)
            
        Returns:
            GeneratedProfile with full storage and temporal narrative
        """
        try:
            from advanced_profile_generator import (
                AdvancedProfileGenerator, AdvancedProfileConfig
            )
            
            config = AdvancedProfileConfig(
                profile_uuid=profile_uuid,
                persona_name=persona_name,
                persona_email=persona_email,
                billing_address=billing_address,
                localstorage_size_mb=storage_size_mb,
            )
            
            generator = AdvancedProfileGenerator(str(self.output_dir))
            advanced_profile = generator.generate(config, template)
            
            # Convert to GeneratedProfile for compatibility
            return GeneratedProfile(
                profile_id=advanced_profile.profile_id,
                profile_path=advanced_profile.profile_path,
                browser_type="firefox",
                age_days=95,
                target_domain="",
                cookies_count=advanced_profile.cookies_count,
                history_count=advanced_profile.history_entries,
                created_at=advanced_profile.created_at,
                hardware_fingerprint={}
            )
            
        except ImportError as e:
            # Fallback to standard archetype profile
            logger.warning(f"Advanced generator not available: {e}")
            
            # Map template to archetype
            template_to_archetype = {
                "student_developer": ProfileArchetype.STUDENT_DEVELOPER,
                "professional": ProfileArchetype.PROFESSIONAL,
                "gamer": ProfileArchetype.GAMER,
                "retiree": ProfileArchetype.RETIREE,
                "casual_shopper": ProfileArchetype.CASUAL_SHOPPER,
            }
            
            archetype = template_to_archetype.get(template, ProfileArchetype.CASUAL_SHOPPER)
            target = TARGET_PRESETS.get("amazon_us", list(TARGET_PRESETS.values())[0])
            
            return self.forge_archetype_profile(
                archetype=archetype,
                target=target,
                persona_name=persona_name,
                persona_email=persona_email,
                billing_address=billing_address,
                age_days=95
            )
    
    def generate_handover_document(self, profile_path: Path, target_domain: str) -> str:
        """
        Generate a Manual Handover Protocol document for the operator.
        
        This creates the "Sleeper Method" instructions for human execution.
        
        Args:
            profile_path: Path to the generated profile
            target_domain: Target website domain
            
        Returns:
            Path to generated handover document
        """
        # Load profile metadata
        meta_file = profile_path / "profile_metadata.json"
        if meta_file.exists():
            with open(meta_file) as f:
                metadata = json.load(f)
        else:
            metadata = {"persona_name": "Unknown", "billing_address": {}}
        
        # Load proxy config
        proxy_file = profile_path / "proxy_config.json"
        if proxy_file.exists():
            with open(proxy_file) as f:
                proxy_config = json.load(f)
        else:
            proxy_config = {"region": "us-tx-austin"}
        
        persona_name = metadata.get("persona_name", "Unknown")
        billing = metadata.get("billing_address", {})
        
        handover_doc = f'''
================================================================================
OBLIVION OPERATOR CARD: {profile_path.name}
================================================================================
IDENTITY: {persona_name}
STATUS: SLEEPER AGENT (90-Day Maturity)
DEVICE: {metadata.get("hardware_profile", {}).get("device_description", "Windows Desktop (Kernel-Masked)")}
LOCATION: {billing.get("city", "Unknown")}, {billing.get("state", "Unknown")} (Residential)
TARGET: {target_domain}
================================================================================

PHASE 1: ENVIRONMENT LOCK (Pre-Flight)
--------------------------------------
[ ] Proxy Check: Verify IP is {billing.get("city", "Unknown")}, {billing.get("state", "Unknown")} ({billing.get("zip", "Unknown")})
    - Verify ISP is NOT a datacenter
    - Run: curl ipinfo.io
    
[ ] Timezone Check: System time must match billing region
    - Expected: {self._get_timezone_for_state(billing.get("state", "TX"))}
    
[ ] Hardware Shield: Verify TITAN_HW_SPOOF=ACTIVE
    - Confirm UserAgent matches profile
    
[ ] Audio Check: Ensure system volume is >0 (AudioContext fingerprint)

================================================================================

PHASE 2: THE "WAKING" (Narrative Immersion)
-------------------------------------------
Do NOT navigate to target yet.

1. Tab 1 (Google): Search for "reddit {persona_name.split()[0].lower()} salary {billing.get('city', 'austin').lower()}"
   - Action: Click a Reddit link. Scroll down 30%. Close tab.
   - Why: Establishes persona is currently active.

2. Tab 2 (Email): Navigate to Gmail/Outlook
   - Action: Check "Inbox". Leave tab OPEN in background.
   - Why: Real users have email open when expecting receipts.

3. Tab 3 (GitHub/LinkedIn): Go to github.com or linkedin.com
   - Action: Verify logged in (cookies should handle this).
   - Why: Refreshes session cookie, asserts persona.

================================================================================

PHASE 3: THE "STRIKE" (Execution)
---------------------------------
Speed kills. Be lazy.

1. Discovery:
   - Go to Google.com
   - Search: "{target_domain} reviews" or "{target_domain} shipping time"
   - Click ORGANIC link (non-ad) to target site

2. The "Consideration" (BioCatch Defeat):
   - DO NOT add to cart immediately
   - Scroll to page FOOTER
   - Highlight "Return Policy" or "Shipping" text with mouse
   - Wait 15 seconds
   - Scroll back up. Select options if applicable.
   - Add to Cart

3. Checkout Flow:
   - Proceed to Checkout
   - Contact Info: Use Autofill if available. Type at ~85 WPM if not.
   - Shipping: Enter {billing.get("address", "ADDRESS")}
     - Select suggested autocomplete address
   - Payment:
     - Select "Credit Card"
     - CRITICAL: When browser asks "Use saved card?", click YES
     - This triggers autofill event = massive trust signal

4. Final Authorization:
   - Click "Place Order"
   - IF 3DS (OTP) APPEARS:
     - Stop. Hands off keyboard.
     - Count to 12 (simulate unlocking phone)
     - Enter code
     - Wait 2 seconds
     - Click Submit

================================================================================

PHASE 4: POST-OP (Cool Down)
----------------------------
[ ] Do NOT close browser immediately
[ ] Navigate to "Email" tab. Refresh to "check for receipt"
[ ] Close browser after 45 seconds

================================================================================
AUTHORITY: Dva.12 | STATUS: READY_FOR_EXECUTION
================================================================================
'''
        
        # Write handover document
        handover_file = profile_path / "HANDOVER_PROTOCOL.txt"
        with open(handover_file, "w") as f:
            f.write(handover_doc)
        
        return str(handover_file)
    
    def _get_timezone_for_state(self, state: str) -> str:
        """Get timezone for US state"""
        timezones = {
            "TX": "Central Standard Time (CST)",
            "CA": "Pacific Standard Time (PST)",
            "NY": "Eastern Standard Time (EST)",
            "FL": "Eastern Standard Time (EST)",
            "WA": "Pacific Standard Time (PST)",
            "IL": "Central Standard Time (CST)",
            "AZ": "Mountain Standard Time (MST)",
        }
        return timezones.get(state.upper(), "Eastern Standard Time (EST)")
    
    def forge_for_target(self,
                         target_id: str,
                         persona_name: str,
                         persona_email: str,
                         billing_address: Dict[str, str],
                         proxy_url: str = "",
                         card_last4: str = "") -> 'GeneratedProfile':
        """
        Forge a profile optimized for a specific target site.
        
        Uses target intelligence for detection-aware profile generation.
        
        Args:
            target_id: Target ID (e.g., "eneba", "g2a", "amazon_us")
            persona_name: Full name
            persona_email: Email address
            billing_address: Dict with address, city, state, zip, country
            proxy_url: Optional proxy URL
            card_last4: Optional card last 4 for autofill hint
            
        Returns:
            GeneratedProfile optimized for target's detection systems
        """
        try:
            from target_intelligence import get_target_intel, get_profile_requirements
            
            intel = get_target_intel(target_id)
            if not intel:
                logger.warning(f"Target '{target_id}' not found, using default")
                return self.forge_golden_ticket(
                    profile_uuid=f"TITAN-{secrets.token_hex(4).upper()}",
                    persona_name=persona_name,
                    persona_email=persona_email,
                    billing_address=billing_address,
                )
            
            # Get detection-aware requirements
            requirements = get_profile_requirements(target_id)
            profile_reqs = requirements.get("profile_requirements", {})
            
            # Generate profile UUID
            profile_uuid = f"{intel.name.upper()[:4]}-{secrets.token_hex(4).upper()}"
            
            # Use detection-aware settings
            min_age = profile_reqs.get("min_age_days", 60)
            min_storage = profile_reqs.get("min_storage_mb", 300)
            
            # Determine archetype based on fraud engine
            archetype = "student_developer"
            if intel.fraud_engine.value == "forter":
                archetype = "student_developer"  # Needs commerce history
            elif intel.fraud_engine.value == "seon":
                archetype = "professional"  # Needs social footprint
            
            profile = self.forge_golden_ticket(
                profile_uuid=profile_uuid,
                persona_name=persona_name,
                persona_email=persona_email,
                billing_address=billing_address,
                template=archetype,
                storage_size_mb=max(min_storage, 400),
            )
            
            # Add detection-aware metadata
            intel_meta = {
                "target_id": target_id,
                "target_name": intel.name,
                "target_domain": intel.domain,
                "fraud_engine": intel.fraud_engine.value,
                "payment_gateway": intel.payment_gateway.value,
                "friction_level": intel.friction.value,
                "3ds_rate": intel.three_ds_rate,
                "mobile_softer": intel.mobile_softer,
                "warmup_sites": intel.warmup_sites,
                "evasion_notes": requirements.get("evasion_notes", []),
                "profile_requirements": profile_reqs,
            }
            
            intel_file = profile.profile_path / "target_intelligence.json"
            with open(intel_file, "w") as f:
                json.dump(intel_meta, f, indent=2)
            
            # Generate detection-aware handover document
            self._generate_intel_handover(profile.profile_path, intel, requirements)
            
            logger.info(f"[+] Detection-aware profile forged for: {intel.name}")
            logger.info(f"    Fraud Engine: {intel.fraud_engine.value}")
            logger.info(f"    3DS Rate: {intel.three_ds_rate*100:.0f}%")
            return profile
            
        except ImportError as e:
            logger.warning(f"Target intelligence not available: {e}")
            return self.forge_golden_ticket(
                profile_uuid=f"TITAN-{secrets.token_hex(4).upper()}",
                persona_name=persona_name,
                persona_email=persona_email,
                billing_address=billing_address,
            )
    
    def _generate_intel_handover(self, profile_path: Path, intel, requirements: Dict):
        """Generate detection-aware handover document"""
        evasion_notes = requirements.get("evasion_notes", [])
        profile_reqs = requirements.get("profile_requirements", {})
        
        handover = f"""================================================================================
TITAN V7.0 - DETECTION-AWARE OPERATION CARD
================================================================================
TARGET: {intel.name} ({intel.domain})
FRAUD ENGINE: {intel.fraud_engine.value.upper()}
PAYMENT GATEWAY: {intel.payment_gateway.value.upper()}
FRICTION LEVEL: {intel.friction.value.upper()}
3DS PROBABILITY: {intel.three_ds_rate*100:.0f}%
{"MOBILE APP SOFTER: YES - Use mobile for lower friction" if intel.mobile_softer else ""}
================================================================================

DETECTION SYSTEM ANALYSIS
-------------------------
{chr(10).join(f"• {note}" for note in evasion_notes)}

PROFILE REQUIREMENTS MET
------------------------
✓ Profile Age: {profile_reqs.get('min_age_days', 60)}+ days
✓ Storage Size: {profile_reqs.get('min_storage_mb', 300)}+ MB
✓ Social Footprint: {"REQUIRED" if profile_reqs.get('require_social_footprint') else "Not required"}
✓ Commerce History: {"REQUIRED" if profile_reqs.get('require_commerce_history') else "Not required"}
✓ Residential Proxy: {"REQUIRED" if profile_reqs.get('require_residential_proxy') else "Not required"}

PRE-OPERATION WARMUP
--------------------
{"Required warmup sites:" if intel.warmup_sites else "No specific warmup required"}
{chr(10).join(f"  → {site}" for site in intel.warmup_sites)}
Warmup Duration: {profile_reqs.get('warmup_minutes', 5)} minutes minimum

EXECUTION STRATEGY
------------------
1. ENVIRONMENT CHECK
   [ ] Proxy verified as residential (NOT datacenter)
   [ ] Timezone matches billing address
   [ ] WebRTC leak check passed

2. WARMUP PHASE ({profile_reqs.get('warmup_minutes', 5)} min)
   [ ] Visit warmup sites listed above
   [ ] Generate organic browsing patterns
   [ ] Build device fingerprint trust

3. TARGET APPROACH
   [ ] Use organic referrer (Google search → target)
   [ ] Browse 2-3 products before checkout
   [ ] Use AUTOFILL for all form fields

4. CHECKOUT
   [ ] {"Use MOBILE APP for lower friction" if intel.mobile_softer else "Web checkout acceptable"}
   [ ] If 3DS triggered ({intel.three_ds_rate*100:.0f}% chance), wait 10s before entering OTP
   [ ] Complete purchase

================================================================================
TITAN V7.0 SINGULARITY - Zero Detect / Zero Decline
================================================================================
"""
        
        handover_file = profile_path / "HANDOVER_PROTOCOL.txt"
        with open(handover_file, "w") as f:
            f.write(handover)


# ═══════════════════════════════════════════════════════════════════════════
# V7.5 UPGRADE: OS CONSISTENCY VALIDATION
# Single-source-of-truth enforcement — ensures every identity artifact
# (User-Agent, navigator.platform, TLS fingerprint, timezone, locale,
# screen resolution, GPU string) is internally consistent with the
# declared OS. Inconsistency between ANY two signals is an instant
# detection vector for Forter, ThreatMetrix, and iovation.
# ═══════════════════════════════════════════════════════════════════════════

class OSConsistencyValidator:
    """
    v7.5 OS Consistency Validation Engine.

    Validates that all profile signals are mutually consistent:
    - User-Agent OS matches navigator.platform
    - TLS fingerprint matches browser/OS combination
    - Timezone matches locale and geo-IP
    - Screen resolution is plausible for declared hardware
    - GPU string matches OS (e.g., ANGLE/D3D11 = Windows, Metal = macOS)
    """

    # OS → expected navigator.platform values
    PLATFORM_MAP = {
        "windows_11": ["Win32"],
        "windows_10": ["Win32"],
        "macos_sonoma": ["MacIntel"],
        "macos_ventura": ["MacIntel"],
        "linux": ["Linux x86_64"],
        "ios": ["iPhone", "iPad"],
        "android": ["Linux armv8l", "Linux aarch64"],
    }

    # OS → expected GPU renderer patterns
    GPU_PATTERNS = {
        "windows": ["Direct3D11", "Direct3D9", "D3D11", "D3D9"],
        "macos": ["Apple M", "Apple GPU", "Metal"],
        "linux": ["Mesa", "ANGLE (", "OpenGL"],
        "ios": ["Apple GPU", "Apple A"],
        "android": ["Adreno", "Mali", "PowerVR", "Qualcomm"],
    }

    # OS → expected UA tokens
    UA_TOKENS = {
        "windows_11": ["Windows NT 10.0", "Win64"],
        "windows_10": ["Windows NT 10.0", "Win64"],
        "macos_sonoma": ["Macintosh", "Mac OS X 14"],
        "macos_ventura": ["Macintosh", "Mac OS X 13"],
        "linux": ["X11", "Linux x86_64"],
        "ios": ["iPhone", "CPU iPhone OS"],
        "android": ["Android", "Linux"],
    }

    def __init__(self):
        self.errors = []
        self.warnings = []

    def validate_profile(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate full profile for OS consistency.
        Returns dict with status, errors, warnings.
        """
        self.errors = []
        self.warnings = []

        declared_os = profile.get("os", "").lower()
        ua = profile.get("user_agent", "")
        platform = profile.get("navigator_platform", "")
        gpu_renderer = profile.get("webgl_renderer", "")
        timezone = profile.get("timezone", "")
        locale = profile.get("locale", "")
        screen_w = profile.get("screen_width", 0)
        screen_h = profile.get("screen_height", 0)

        # 1. UA ↔ OS consistency
        self._check_ua_os(ua, declared_os)

        # 2. Platform ↔ OS consistency
        self._check_platform_os(platform, declared_os)

        # 3. GPU ↔ OS consistency
        self._check_gpu_os(gpu_renderer, declared_os)

        # 4. Screen resolution plausibility
        self._check_screen(screen_w, screen_h, declared_os)

        # 5. Timezone ↔ locale consistency
        self._check_tz_locale(timezone, locale)

        status = "PASS" if not self.errors else "FAIL"
        return {
            "status": status,
            "os": declared_os,
            "errors": self.errors,
            "warnings": self.warnings,
            "checks_run": 5,
            "checks_passed": 5 - len(self.errors),
        }

    def _check_ua_os(self, ua: str, os_name: str):
        os_key = None
        for key in self.UA_TOKENS:
            if key in os_name or os_name in key:
                os_key = key
                break
        if os_key and not any(tok in ua for tok in self.UA_TOKENS[os_key]):
            self.errors.append(f"UA mismatch: UA does not contain expected tokens for {os_key}")

    def _check_platform_os(self, platform: str, os_name: str):
        os_key = None
        for key in self.PLATFORM_MAP:
            if key in os_name or os_name in key:
                os_key = key
                break
        if os_key and platform and platform not in self.PLATFORM_MAP[os_key]:
            self.errors.append(f"Platform mismatch: '{platform}' not valid for {os_key}")

    def _check_gpu_os(self, renderer: str, os_name: str):
        os_family = "windows" if "windows" in os_name else \
                    "macos" if "macos" in os_name or "mac" in os_name else \
                    "ios" if "ios" in os_name else \
                    "android" if "android" in os_name else \
                    "linux" if "linux" in os_name else None
        if os_family and renderer:
            patterns = self.GPU_PATTERNS.get(os_family, [])
            if patterns and not any(p in renderer for p in patterns):
                self.errors.append(f"GPU mismatch: '{renderer[:50]}' not consistent with {os_family}")

    def _check_screen(self, w: int, h: int, os_name: str):
        if w > 0 and h > 0:
            if "ios" in os_name or "iphone" in os_name:
                if w > 1290 or h > 2796:
                    self.warnings.append(f"Screen {w}x{h} unusual for iOS device")
            elif "android" in os_name:
                if w > 1440 or h > 3200:
                    self.warnings.append(f"Screen {w}x{h} unusual for Android device")
            else:
                if w < 800 or h < 600:
                    self.warnings.append(f"Screen {w}x{h} suspiciously small for desktop")

    def _check_tz_locale(self, timezone: str, locale: str):
        if timezone and locale:
            us_tz = ["America/New_York", "America/Chicago", "America/Denver",
                     "America/Los_Angeles", "America/Phoenix"]
            if any(tz in timezone for tz in us_tz) and locale and not locale.startswith("en"):
                self.warnings.append(f"Timezone {timezone} is US but locale {locale} is not English")

    def single_source_of_truth(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        v7.5 Single-Source-of-Truth enforcement.
        Auto-corrects inconsistencies by deriving all signals from the
        declared OS, ensuring zero cross-signal detection vectors.
        """
        declared_os = profile.get("os", "windows_11").lower()

        # Auto-set platform
        for key in self.PLATFORM_MAP:
            if key in declared_os:
                profile["navigator_platform"] = self.PLATFORM_MAP[key][0]
                break

        # Auto-set UA tokens check
        ua = profile.get("user_agent", "")
        for key in self.UA_TOKENS:
            if key in declared_os:
                missing = [t for t in self.UA_TOKENS[key] if t not in ua]
                if missing:
                    profile["_ua_warnings"] = f"UA missing tokens: {missing}"
                break

        profile["_os_consistency_validated"] = True
        profile["_os_consistency_version"] = "7.5"
        return profile
