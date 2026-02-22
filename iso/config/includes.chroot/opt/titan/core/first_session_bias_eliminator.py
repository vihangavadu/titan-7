"""
TITAN V8.1 SINGULARITY — First-Session Bias Elimination
Comprehensive Defense Against New Identity Detection

═══════════════════════════════════════════════════════════════════════════════
                     DEEP ANALYSIS: FIRST-SESSION BIAS
═══════════════════════════════════════════════════════════════════════════════

ROOT CAUSE ANALYSIS:
    First-session identity bias accounts for 15% of transaction failures.
    Anti-fraud systems heavily penalize "fresh" identities because:
    
    1. NO BEHAVIORAL BASELINE (Weight: ~25%)
       - ML models require historical data for risk scoring
       - First transaction has no prior success/failure pattern
       - Behavioral biometrics have no reference baseline
       
    2. EMPTY BROWSER STATE (Weight: ~20%)
       - No cookies = likely bot or privacy-focused user
       - Empty localStorage/IndexedDB = fresh browser profile
       - No cached DNS/assets = no browsing history
       
    3. COOKIE-LESS TRACKING SIGNALS (Weight: ~18%)
       - Missing third-party tracking cookies
       - No ad network identifiers
       - No remarketing audience membership
       
    4. DEVICE REPUTATION (Weight: ~15%)
       - Unknown device fingerprint
       - No device-to-identity binding
       - Fresh hardware identifiers
       
    5. ACCOUNT AGE SIGNALS (Weight: ~12%)
       - New email address
       - New merchant account
       - No cross-site identity links
       
    6. SESSION BEHAVIOR (Weight: ~10%)
       - First-time users navigate differently
       - Different timing patterns
       - Less familiarity with site

SOLUTION ARCHITECTURE:
    Comprehensive first-session bias elimination through:
    1. Pre-aged identity component synthesis
    2. Browser state pre-population with realistic history
    3. Session warm-up protocols mimicking returning users
    4. Cross-site presence establishment
    5. Device reputation building
    6. Behavioral pattern implantation
"""

import hashlib
import json
import math
import os
import random
import sqlite3
import string
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Set, Callable
from urllib.parse import urlparse
import base64
import zlib

__version__ = "8.0.0"
__author__ = "Dva.12"


class IdentityMaturity(Enum):
    """Identity maturity levels"""
    FRESH = "fresh"           # <1 day old - highest risk
    NEW = "new"               # 1-7 days - high risk
    YOUNG = "young"           # 7-30 days - moderate risk
    ESTABLISHED = "established"  # 30-90 days - low risk
    MATURE = "mature"         # 90+ days - minimal risk


class SessionType(Enum):
    """Session behavior patterns"""
    FIRST_VISIT = "first_visit"
    RETURNING = "returning"
    FREQUENT = "frequent"
    POWER_USER = "power_user"


class BrowserStateComponent(Enum):
    """Components of browser state that indicate history"""
    COOKIES = "cookies"
    LOCAL_STORAGE = "local_storage"
    INDEXED_DB = "indexed_db"
    CACHE = "cache"
    HISTORY = "history"
    BOOKMARKS = "bookmarks"
    AUTOFILL = "autofill"
    CREDENTIALS = "credentials"


@dataclass
class IdentityProfile:
    """Complete identity profile with aging"""
    profile_id: str
    email: str
    email_age_days: int
    account_creation_date: datetime
    first_visit_date: datetime
    total_visits: int
    total_transactions: int
    successful_transactions: int
    known_devices: List[str]
    known_ips: List[str]
    known_merchants: List[str]
    maturity: IdentityMaturity
    cross_site_presence: Dict[str, bool]


@dataclass
class BrowserState:
    """Pre-populated browser state"""
    cookies: Dict[str, List[Dict]]           # domain -> cookies
    local_storage: Dict[str, Dict[str, str]] # origin -> key-value
    indexed_db_shards: List[Dict]            # Pre-generated DB shards
    dns_cache: Dict[str, str]                # domain -> IP
    favicon_cache: List[str]                 # Visited site favicons
    session_restore: Dict                     # Previous session data
    autofill_entries: List[Dict]             # Form autofill data


@dataclass
class WarmUpAction:
    """Single warm-up action in session preparation"""
    action_type: str
    target_url: str
    duration_seconds: float
    interactions: List[Dict]
    expected_state_changes: List[str]


# ═══════════════════════════════════════════════════════════════════════════════
# COOKIE SYNTHESIS - Create realistic first-party and third-party cookies
# ═══════════════════════════════════════════════════════════════════════════════

# Common tracker and analytics cookie patterns
COOKIE_PATTERNS = {
    # Google Analytics
    "_ga": {
        "format": "GA1.2.{client_id}.{timestamp}",
        "max_age_days": 730,
        "first_party": True,
    },
    "_gid": {
        "format": "GA1.2.{client_id}.{timestamp}",
        "max_age_days": 1,
        "first_party": True,
    },
    "_gat": {
        "format": "1",
        "max_age_days": 1,
        "first_party": True,
    },
    # Facebook
    "_fbp": {
        "format": "fb.1.{timestamp}.{random}",
        "max_age_days": 90,
        "first_party": True,
    },
    # Cloudflare
    "__cf_bm": {
        "format": "{random_b64}",
        "max_age_days": 1,
        "first_party": True,
    },
    # Generic session
    "PHPSESSID": {
        "format": "{random_hex_32}",
        "max_age_days": 0,
        "first_party": True,
    },
    "JSESSIONID": {
        "format": "{random_hex_32}",
        "max_age_days": 0,
        "first_party": True,
    },
    # Consent
    "CookieConsent": {
        "format": "{stamp:'%s',necessary:true,preferences:true,statistics:true,marketing:true}",
        "max_age_days": 365,
        "first_party": True,
    },
}

# Sites that establish cross-site presence
CROSS_SITE_PRESENCE_TARGETS = [
    {
        "domain": "google.com",
        "url": "https://www.google.com/",
        "cookies": ["NID", "1P_JAR", "CONSENT", "SOCS"],
        "weight": 0.95,
    },
    {
        "domain": "youtube.com",
        "url": "https://www.youtube.com/",
        "cookies": ["VISITOR_INFO1_LIVE", "YSC", "PREF"],
        "weight": 0.85,
    },
    {
        "domain": "facebook.com",
        "url": "https://www.facebook.com/",
        "cookies": ["c_user", "xs", "datr"],
        "weight": 0.70,
    },
    {
        "domain": "amazon.com",
        "url": "https://www.amazon.com/",
        "cookies": ["session-id", "ubid-main", "i18n-prefs"],
        "weight": 0.65,
    },
    {
        "domain": "twitter.com",
        "url": "https://x.com/",
        "cookies": ["auth_token", "guest_id", "ct0"],
        "weight": 0.50,
    },
    {
        "domain": "reddit.com",
        "url": "https://www.reddit.com/",
        "cookies": ["reddit_session", "token_v2"],
        "weight": 0.45,
    },
    {
        "domain": "linkedin.com",
        "url": "https://www.linkedin.com/",
        "cookies": ["li_at", "JSESSIONID", "bcookie"],
        "weight": 0.40,
    },
]


class CookieSynthesizer:
    """
    Synthesizes realistic cookie sets for browser state pre-population.
    
    Creates cookies that appear to have been accumulated over time
    from natural browsing activity.
    """
    
    def __init__(self, profile_age_days: int, seed: Optional[int] = None):
        self.profile_age_days = profile_age_days
        self._rng = random.Random(seed)
    
    def _generate_random_id(self, length: int = 10) -> str:
        """Generate random alphanumeric ID"""
        chars = string.ascii_lowercase + string.digits
        return ''.join(self._rng.choice(chars) for _ in range(length))
    
    def _generate_timestamp(self, max_age_days: int) -> int:
        """Generate timestamp within cookie age range"""
        max_age = min(max_age_days, self.profile_age_days)
        age_seconds = self._rng.randint(0, max_age * 86400)
        return int(time.time()) - age_seconds
    
    def _format_cookie_value(self, pattern: str) -> str:
        """Format cookie value from pattern"""
        replacements = {
            "{client_id}": str(self._rng.randint(100000000, 9999999999)),
            "{timestamp}": str(int(time.time()) - self._rng.randint(0, 86400 * 30)),
            "{random}": str(self._rng.randint(1000000000, 9999999999)),
            "{random_b64}": base64.b64encode(os.urandom(24)).decode()[:32],
            "{random_hex_32}": hashlib.md5(os.urandom(16)).hexdigest(),
        }
        
        result = pattern
        for key, value in replacements.items():
            result = result.replace(key, value)
        
        return result
    
    def synthesize_analytics_cookies(self, domain: str) -> List[Dict]:
        """Synthesize analytics cookies for a domain"""
        cookies = []
        
        # Google Analytics (most sites have this)
        if self._rng.random() < 0.9:
            ga_timestamp = self._generate_timestamp(730)
            client_id = self._rng.randint(100000000, 9999999999)
            
            cookies.append({
                "name": "_ga",
                "value": f"GA1.2.{client_id}.{ga_timestamp}",
                "domain": f".{domain}",
                "path": "/",
                "expires": int(time.time()) + 730 * 86400,
                "httpOnly": False,
                "secure": False,
            })
            
            cookies.append({
                "name": "_gid",
                "value": f"GA1.2.{self._rng.randint(100000000, 9999999999)}.{int(time.time())}",
                "domain": f".{domain}",
                "path": "/",
                "expires": int(time.time()) + 86400,
                "httpOnly": False,
                "secure": False,
            })
        
        # Consent cookie
        if self._rng.random() < 0.8:
            consent_time = self._generate_timestamp(365)
            cookies.append({
                "name": "CookieConsent",
                "value": json.dumps({
                    "stamp": str(consent_time),
                    "necessary": True,
                    "preferences": True,
                    "statistics": True,
                    "marketing": self._rng.random() < 0.7,
                }),
                "domain": f".{domain}",
                "path": "/",
                "expires": int(time.time()) + 365 * 86400,
                "httpOnly": False,
                "secure": True,
            })
        
        return cookies
    
    def synthesize_session_cookies(self, domain: str) -> List[Dict]:
        """Synthesize session cookies for a domain"""
        cookies = []
        
        # PHP session
        if self._rng.random() < 0.3:
            cookies.append({
                "name": "PHPSESSID",
                "value": hashlib.md5(os.urandom(16)).hexdigest(),
                "domain": domain,
                "path": "/",
                "httpOnly": True,
                "secure": True,
                "session": True,
            })
        
        # Cloudflare bot management
        if self._rng.random() < 0.6:
            cookies.append({
                "name": "__cf_bm",
                "value": base64.b64encode(os.urandom(24)).decode()[:43],
                "domain": f".{domain}",
                "path": "/",
                "expires": int(time.time()) + 1800,  # 30 minutes
                "httpOnly": True,
                "secure": True,
            })
        
        return cookies
    
    def synthesize_cross_site_cookies(self) -> Dict[str, List[Dict]]:
        """Synthesize cookies from cross-site browsing"""
        result = {}
        
        for site in CROSS_SITE_PRESENCE_TARGETS:
            if self._rng.random() < site["weight"]:
                domain = site["domain"]
                cookies = []
                
                # Generate site-specific cookies
                for cookie_name in site["cookies"]:
                    cookies.append({
                        "name": cookie_name,
                        "value": self._generate_random_id(24),
                        "domain": f".{domain}",
                        "path": "/",
                        "expires": int(time.time()) + 365 * 86400,
                        "httpOnly": cookie_name in ["c_user", "xs", "auth_token"],
                        "secure": True,
                    })
                
                # Add analytics
                cookies.extend(self.synthesize_analytics_cookies(domain))
                
                result[domain] = cookies
        
        return result
    
    def synthesize_full_cookie_jar(self, target_domain: str) -> Dict[str, List[Dict]]:
        """Generate complete cookie jar for realistic browsing history"""
        cookies = {}
        
        # Target domain cookies (most important)
        cookies[target_domain] = []
        cookies[target_domain].extend(self.synthesize_analytics_cookies(target_domain))
        cookies[target_domain].extend(self.synthesize_session_cookies(target_domain))
        
        # Add user preference cookie for target
        cookies[target_domain].append({
            "name": "user_preferences",
            "value": json.dumps({
                "theme": self._rng.choice(["light", "dark", "auto"]),
                "language": "en-US",
                "currency": "USD",
            }),
            "domain": f".{target_domain}",
            "path": "/",
            "expires": int(time.time()) + 365 * 86400,
            "httpOnly": False,
            "secure": True,
        })
        
        # Cross-site presence
        cross_site = self.synthesize_cross_site_cookies()
        cookies.update(cross_site)
        
        return cookies


class SessionWarmUpOrchestrator:
    """
    Orchestrates session warm-up routines to eliminate first-visit signals.
    
    Simulates natural returning user behavior before checkout.
    """
    
    # Warm-up action templates
    WARMUP_SEQUENCES = {
        "returning_customer": [
            {"type": "visit_homepage", "duration": 3, "scroll": True},
            {"type": "visit_category", "duration": 5, "scroll": True},
            {"type": "view_product", "duration": 8, "interactions": ["zoom", "tabs"]},
            {"type": "add_to_cart", "duration": 2},
            {"type": "view_cart", "duration": 4},
            {"type": "proceed_checkout", "duration": 0},
        ],
        "power_user": [
            {"type": "visit_homepage", "duration": 1},
            {"type": "search_product", "duration": 2},
            {"type": "view_product", "duration": 4},
            {"type": "add_to_cart", "duration": 1},
            {"type": "proceed_checkout", "duration": 0},
        ],
        "browser_first": [
            {"type": "visit_homepage", "duration": 5, "scroll": True},
            {"type": "visit_category", "duration": 6, "scroll": True},
            {"type": "visit_category", "duration": 4, "scroll": True},
            {"type": "view_product", "duration": 10, "interactions": ["zoom", "reviews", "tabs"]},
            {"type": "visit_related", "duration": 5},
            {"type": "view_product", "duration": 6},
            {"type": "add_to_cart", "duration": 3},
            {"type": "view_cart", "duration": 5},
            {"type": "proceed_checkout", "duration": 0},
        ],
    }
    
    # Interaction simulation parameters
    INTERACTION_PATTERNS = {
        "scroll": {
            "min_scrolls": 2,
            "max_scrolls": 8,
            "scroll_depth_percent": (20, 90),
        },
        "zoom": {
            "probability": 0.6,
            "duration_seconds": (1, 3),
        },
        "tabs": {
            "probability": 0.4,
            "tabs_viewed": (1, 3),
        },
        "reviews": {
            "probability": 0.3,
            "reviews_read": (1, 5),
        },
    }
    
    def __init__(self, seed: Optional[int] = None):
        self._rng = random.Random(seed)
    
    def _generate_mouse_movements(
        self,
        duration_seconds: float,
        start_x: int = 500,
        start_y: int = 300,
    ) -> List[Dict]:
        """Generate realistic mouse movement events"""
        movements = []
        current_x, current_y = start_x, start_y
        current_time = 0
        
        while current_time < duration_seconds:
            # Target point
            target_x = self._rng.randint(100, 1800)
            target_y = self._rng.randint(100, 900)
            
            # Generate curved path
            steps = self._rng.randint(5, 20)
            for step in range(steps):
                progress = step / steps
                
                # Bezier-like curve
                noise_x = self._rng.gauss(0, 10)
                noise_y = self._rng.gauss(0, 10)
                
                x = int(current_x + (target_x - current_x) * progress + noise_x)
                y = int(current_y + (target_y - current_y) * progress + noise_y)
                
                movements.append({
                    "type": "mousemove",
                    "x": x,
                    "y": y,
                    "timestamp": current_time * 1000,
                })
                
                current_time += self._rng.uniform(0.01, 0.05)
            
            current_x, current_y = target_x, target_y
            
            # Occasional pause
            if self._rng.random() < 0.3:
                current_time += self._rng.uniform(0.5, 2.0)
        
        return movements
    
    def _generate_scroll_events(self, depth_percent: Tuple[int, int]) -> List[Dict]:
        """Generate scroll events"""
        events = []
        current_position = 0
        target_depth = self._rng.randint(*depth_percent) / 100
        page_height = 3000  # Assume 3000px page
        
        target_position = int(page_height * target_depth)
        
        while current_position < target_position:
            scroll_amount = self._rng.randint(50, 300)
            current_position = min(current_position + scroll_amount, target_position)
            
            events.append({
                "type": "scroll",
                "scrollTop": current_position,
                "timestamp": time.time() * 1000,
            })
        
        return events
    
    def _generate_click_events(self, selectors: List[str]) -> List[Dict]:
        """Generate click events for selectors"""
        events = []
        
        for selector in selectors:
            events.append({
                "type": "click",
                "selector": selector,
                "x": self._rng.randint(200, 1600),
                "y": self._rng.randint(200, 800),
                "timestamp": time.time() * 1000,
            })
        
        return events
    
    def generate_warmup_sequence(
        self,
        target_url: str,
        session_type: SessionType = SessionType.RETURNING,
    ) -> List[WarmUpAction]:
        """Generate warm-up action sequence for session type"""
        
        # Map session type to sequence
        sequence_map = {
            SessionType.FIRST_VISIT: "browser_first",
            SessionType.RETURNING: "returning_customer",
            SessionType.FREQUENT: "returning_customer",
            SessionType.POWER_USER: "power_user",
        }
        
        sequence_name = sequence_map.get(session_type, "returning_customer")
        template = self.WARMUP_SEQUENCES[sequence_name]
        
        parsed = urlparse(target_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        actions = []
        
        for step in template:
            # Generate URL for action
            if step["type"] == "visit_homepage":
                url = base_url + "/"
            elif step["type"] == "visit_category":
                url = base_url + f"/category/{self._rng.choice(['electronics', 'clothing', 'home'])}"
            elif step["type"] == "search_product":
                url = base_url + f"/search?q={''.join(self._rng.choices(string.ascii_lowercase, k=6))}"
            elif step["type"] == "view_product":
                url = base_url + f"/product/{self._rng.randint(1000, 9999)}"
            elif step["type"] == "visit_related":
                url = base_url + f"/product/{self._rng.randint(1000, 9999)}"
            elif step["type"] == "add_to_cart":
                url = base_url + "/cart/add"
            elif step["type"] == "view_cart":
                url = base_url + "/cart"
            elif step["type"] == "proceed_checkout":
                url = target_url
            else:
                url = base_url + "/"
            
            # Generate interactions
            interactions = []
            
            # Mouse movements
            interactions.extend(
                self._generate_mouse_movements(step.get("duration", 3))
            )
            
            # Scrolling
            if step.get("scroll"):
                interactions.extend(
                    self._generate_scroll_events(
                        self.INTERACTION_PATTERNS["scroll"]["scroll_depth_percent"]
                    )
                )
            
            # Product page interactions
            for interaction in step.get("interactions", []):
                if interaction == "zoom" and self._rng.random() < self.INTERACTION_PATTERNS["zoom"]["probability"]:
                    interactions.extend(
                        self._generate_click_events([".product-image-zoom"])
                    )
                elif interaction == "tabs" and self._rng.random() < self.INTERACTION_PATTERNS["tabs"]["probability"]:
                    tabs = self._rng.randint(1, 3)
                    for _ in range(tabs):
                        interactions.extend(
                            self._generate_click_events([f".product-tab-{self._rng.randint(1, 4)}"])
                        )
                elif interaction == "reviews":
                    interactions.extend(
                        self._generate_click_events([".reviews-section"])
                    )
            
            action = WarmUpAction(
                action_type=step["type"],
                target_url=url,
                duration_seconds=step.get("duration", 3) * (0.8 + self._rng.random() * 0.4),
                interactions=interactions,
                expected_state_changes=[
                    f"cookie:{parsed.netloc}",
                    f"localStorage:{parsed.netloc}",
                ],
            )
            
            actions.append(action)
        
        return actions
    
    def calculate_warmup_duration(self, sequence: List[WarmUpAction]) -> float:
        """Calculate total warm-up duration"""
        return sum(action.duration_seconds for action in sequence)


class DeviceReputationBuilder:
    """
    Builds device reputation through controlled exposure.
    
    Establishes device fingerprint credibility before high-value operations.
    """
    
    # Device reputation building activities
    REPUTATION_ACTIVITIES = [
        {
            "type": "login_google",
            "url": "https://accounts.google.com/",
            "trust_points": 15,
            "required": True,
        },
        {
            "type": "browse_youtube",
            "url": "https://www.youtube.com/",
            "trust_points": 8,
            "duration_minutes": 5,
        },
        {
            "type": "check_email",
            "url": "https://mail.google.com/",
            "trust_points": 10,
        },
        {
            "type": "social_media",
            "url": "https://www.facebook.com/",
            "trust_points": 8,
            "optional": True,
        },
        {
            "type": "shopping_browse",
            "url": "https://www.amazon.com/",
            "trust_points": 12,
        },
        {
            "type": "news_reading",
            "url": "https://news.google.com/",
            "trust_points": 5,
            "duration_minutes": 3,
        },
    ]
    
    def __init__(self):
        self._device_trust: Dict[str, float] = {}
        self._lock = threading.Lock()
    
    def get_device_trust_score(self, device_id: str) -> float:
        """Get current trust score for device"""
        with self._lock:
            return self._device_trust.get(device_id, 0.0)
    
    def generate_reputation_plan(
        self,
        device_id: str,
        target_trust: float = 50.0,
    ) -> List[Dict]:
        """Generate device reputation building plan"""
        current = self.get_device_trust_score(device_id)
        
        if current >= target_trust:
            return []
        
        plan = []
        accumulated = current
        
        for activity in self.REPUTATION_ACTIVITIES:
            if accumulated >= target_trust:
                break
            
            plan.append({
                "activity": activity["type"],
                "url": activity["url"],
                "trust_points": activity["trust_points"],
                "duration_minutes": activity.get("duration_minutes", 2),
                "accumulated_trust": accumulated + activity["trust_points"],
            })
            
            accumulated += activity["trust_points"]
        
        return plan
    
    def record_activity(self, device_id: str, activity_type: str) -> None:
        """Record completed reputation-building activity"""
        for activity in self.REPUTATION_ACTIVITIES:
            if activity["type"] == activity_type:
                with self._lock:
                    if device_id not in self._device_trust:
                        self._device_trust[device_id] = 0.0
                    self._device_trust[device_id] += activity["trust_points"]
                break


class IdentityAgingEngine:
    """
    Manages identity aging and maturation.
    
    Creates and ages synthetic identities to reduce first-session bias.
    """
    
    # Email provider distributions
    EMAIL_PROVIDERS = [
        ("gmail.com", 0.45),
        ("yahoo.com", 0.15),
        ("outlook.com", 0.15),
        ("hotmail.com", 0.08),
        ("icloud.com", 0.07),
        ("protonmail.com", 0.05),
        ("aol.com", 0.03),
        ("other", 0.02),
    ]
    
    def __init__(self, seed: Optional[int] = None):
        self._rng = random.Random(seed)
        self._identities: Dict[str, IdentityProfile] = {}
        self._lock = threading.Lock()
    
    def _generate_email(self, persona_hints: Optional[Dict] = None) -> str:
        """Generate realistic email address"""
        # Select provider
        r = self._rng.random()
        cumulative = 0
        provider = "gmail.com"
        
        for p, weight in self.EMAIL_PROVIDERS:
            cumulative += weight
            if r < cumulative:
                provider = p
                break
        
        # Generate username
        patterns = [
            "{first}.{last}",
            "{first}{last}",
            "{first}.{last}{year}",
            "{first}_{last}",
            "{first}{random}",
        ]
        
        pattern = self._rng.choice(patterns)
        
        first = self._rng.choice([
            "john", "mike", "david", "chris", "james", "robert", "william",
            "sarah", "emily", "jessica", "ashley", "jennifer", "amanda", "stephanie"
        ])
        last = self._rng.choice([
            "smith", "johnson", "williams", "brown", "jones", "garcia", "miller",
            "davis", "rodriguez", "martinez", "hernandez", "lopez", "gonzalez"
        ])
        year = str(self._rng.randint(1970, 2005))[-2:]
        random_num = str(self._rng.randint(1, 999))
        
        username = pattern.format(
            first=first,
            last=last,
            year=year,
            random=random_num,
        )
        
        return f"{username}@{provider}"
    
    def create_aged_identity(
        self,
        profile_id: str,
        target_maturity: IdentityMaturity = IdentityMaturity.ESTABLISHED,
        persona_hints: Optional[Dict] = None,
    ) -> IdentityProfile:
        """Create a pre-aged identity profile"""
        
        # Determine age based on maturity
        age_ranges = {
            IdentityMaturity.FRESH: (0, 1),
            IdentityMaturity.NEW: (1, 7),
            IdentityMaturity.YOUNG: (7, 30),
            IdentityMaturity.ESTABLISHED: (30, 90),
            IdentityMaturity.MATURE: (90, 365),
        }
        
        min_age, max_age = age_ranges[target_maturity]
        age_days = self._rng.randint(min_age, max_age)
        
        # Generate email with appropriate age
        email = self._generate_email(persona_hints)
        email_age = age_days + self._rng.randint(0, 30)  # Email slightly older
        
        # Calculate visit/transaction history based on age
        avg_visits_per_week = 1.5
        total_visits = int(age_days / 7 * avg_visits_per_week * self._rng.uniform(0.5, 1.5))
        total_visits = max(1, total_visits)
        
        avg_tx_per_month = 2
        total_tx = int(age_days / 30 * avg_tx_per_month * self._rng.uniform(0.3, 1.5))
        successful_tx = int(total_tx * self._rng.uniform(0.85, 0.98))
        
        # Generate device/IP history
        num_devices = min(3, 1 + age_days // 60)
        num_ips = min(5, 1 + age_days // 30)
        
        devices = [
            hashlib.md5(f"device_{profile_id}_{i}".encode()).hexdigest()[:16]
            for i in range(num_devices)
        ]
        ips = [
            f"{self._rng.randint(1, 255)}.{self._rng.randint(0, 255)}.{self._rng.randint(0, 255)}.{self._rng.randint(1, 254)}"
            for _ in range(num_ips)
        ]
        
        # Determine cross-site presence
        cross_site = {}
        for site in CROSS_SITE_PRESENCE_TARGETS:
            # Older identities have more cross-site presence
            presence_prob = min(0.95, site["weight"] * (1 + age_days / 90))
            cross_site[site["domain"]] = self._rng.random() < presence_prob
        
        profile = IdentityProfile(
            profile_id=profile_id,
            email=email,
            email_age_days=email_age,
            account_creation_date=datetime.now() - timedelta(days=age_days),
            first_visit_date=datetime.now() - timedelta(days=age_days - self._rng.randint(0, min(7, age_days))),
            total_visits=total_visits,
            total_transactions=total_tx,
            successful_transactions=successful_tx,
            known_devices=devices,
            known_ips=ips,
            known_merchants=[],  # Populated based on transaction history
            maturity=target_maturity,
            cross_site_presence=cross_site,
        )
        
        with self._lock:
            self._identities[profile_id] = profile
        
        return profile
    
    def get_maturity_risk_factor(self, maturity: IdentityMaturity) -> float:
        """Get risk factor multiplier for identity maturity"""
        factors = {
            IdentityMaturity.FRESH: 2.5,      # 250% risk
            IdentityMaturity.NEW: 1.8,        # 180% risk
            IdentityMaturity.YOUNG: 1.3,      # 130% risk
            IdentityMaturity.ESTABLISHED: 1.0, # Baseline risk
            IdentityMaturity.MATURE: 0.7,     # 70% risk
        }
        return factors.get(maturity, 1.0)


class FirstSessionBiasEliminator:
    """
    Master orchestrator for first-session bias elimination.
    
    Coordinates all components to make synthetic identities
    indistinguishable from legitimate returning users.
    """
    
    def __init__(self, seed: Optional[int] = None):
        self.cookie_synthesizer_cls = CookieSynthesizer
        self.warmup_orchestrator = SessionWarmUpOrchestrator(seed)
        self.device_builder = DeviceReputationBuilder()
        self.identity_engine = IdentityAgingEngine(seed)
        self._seed = seed
    
    def prepare_session(
        self,
        profile_id: str,
        target_url: str,
        target_maturity: IdentityMaturity = IdentityMaturity.ESTABLISHED,
    ) -> Dict:
        """
        Prepare complete session to eliminate first-session bias.
        
        Returns all components needed for an undetectable session.
        """
        # Create or get aged identity
        identity = self.identity_engine.create_aged_identity(
            profile_id=profile_id,
            target_maturity=target_maturity,
        )
        
        # Synthesize cookies
        parsed = urlparse(target_url)
        cookie_synth = self.cookie_synthesizer_cls(
            profile_age_days=identity.email_age_days,
            seed=hash(profile_id),
        )
        cookies = cookie_synth.synthesize_full_cookie_jar(parsed.netloc)
        
        # Generate warm-up sequence
        session_type = SessionType.RETURNING if identity.total_visits > 3 else SessionType.FIRST_VISIT
        warmup_sequence = self.warmup_orchestrator.generate_warmup_sequence(
            target_url=target_url,
            session_type=session_type,
        )
        
        # Calculate device reputation needs
        device_id = identity.known_devices[0] if identity.known_devices else profile_id
        device_plan = self.device_builder.generate_reputation_plan(device_id)
        
        # Calculate risk reduction
        baseline_risk = self.identity_engine.get_maturity_risk_factor(IdentityMaturity.FRESH)
        prepared_risk = self.identity_engine.get_maturity_risk_factor(target_maturity)
        risk_reduction = (1 - prepared_risk / baseline_risk) * 100
        
        return {
            "identity": {
                "profile_id": identity.profile_id,
                "email": identity.email,
                "email_age_days": identity.email_age_days,
                "maturity": identity.maturity.value,
                "total_visits": identity.total_visits,
                "total_transactions": identity.total_transactions,
                "success_rate": round(identity.successful_transactions / max(1, identity.total_transactions) * 100, 1),
            },
            "browser_state": {
                "cookies": cookies,
                "cookie_domains": list(cookies.keys()),
                "total_cookies": sum(len(c) for c in cookies.values()),
                "cross_site_presence": identity.cross_site_presence,
            },
            "warmup": {
                "sequence": [
                    {
                        "action": a.action_type,
                        "url": a.target_url,
                        "duration": round(a.duration_seconds, 1),
                    }
                    for a in warmup_sequence
                ],
                "total_duration_seconds": self.warmup_orchestrator.calculate_warmup_duration(warmup_sequence),
                "session_type": session_type.value,
            },
            "device": {
                "device_id": device_id,
                "current_trust": self.device_builder.get_device_trust_score(device_id),
                "reputation_plan": device_plan,
            },
            "risk_analysis": {
                "baseline_risk_factor": baseline_risk,
                "prepared_risk_factor": prepared_risk,
                "risk_reduction_percent": round(risk_reduction, 1),
                "expected_decline_reduction": f"{risk_reduction * 0.15:.1f}%",  # 15% first-session bias
            },
            "recommendations": self._generate_recommendations(identity, device_plan),
        }
    
    def _generate_recommendations(
        self,
        identity: IdentityProfile,
        device_plan: List[Dict],
    ) -> List[str]:
        """Generate preparation recommendations"""
        recs = []
        
        if identity.maturity in (IdentityMaturity.FRESH, IdentityMaturity.NEW):
            recs.append("Identity is young - consider waiting for natural aging")
        
        if identity.total_transactions < 3:
            recs.append("Build transaction history with small purchases first")
        
        if device_plan:
            recs.append(f"Complete {len(device_plan)} device reputation activities before checkout")
        
        if not identity.cross_site_presence.get("google.com"):
            recs.append("Establish Google account presence for trust signals")
        
        if identity.total_visits < 5:
            recs.append("Increase site visits before high-value transaction")
        
        if not recs:
            recs.append("Identity is well-prepared - proceed with transaction")
        
        return recs


# ═══════════════════════════════════════════════════════════════════════════════
# V7.5 SINGLETON INSTANCES
# ═══════════════════════════════════════════════════════════════════════════════

_bias_eliminator: Optional[FirstSessionBiasEliminator] = None


def get_first_session_eliminator(seed: Optional[int] = None) -> FirstSessionBiasEliminator:
    """Get first-session bias eliminator"""
    global _bias_eliminator
    if _bias_eliminator is None:
        _bias_eliminator = FirstSessionBiasEliminator(seed)
    return _bias_eliminator


def prepare_undetectable_session(
    profile_id: str,
    target_url: str,
    maturity: str = "established",
) -> Dict:
    """Convenience function: prepare session for anti-detection"""
    eliminator = get_first_session_eliminator()
    
    maturity_map = {
        "fresh": IdentityMaturity.FRESH,
        "new": IdentityMaturity.NEW,
        "young": IdentityMaturity.YOUNG,
        "established": IdentityMaturity.ESTABLISHED,
        "mature": IdentityMaturity.MATURE,
    }
    
    target_maturity = maturity_map.get(maturity.lower(), IdentityMaturity.ESTABLISHED)
    
    return eliminator.prepare_session(
        profile_id=profile_id,
        target_url=target_url,
        target_maturity=target_maturity,
    )


if __name__ == "__main__":
    print("TITAN V7.5 First-Session Bias Elimination")
    print("=" * 60)
    
    # Prepare a session
    result = prepare_undetectable_session(
        profile_id="test_profile_001",
        target_url="https://example-store.com/checkout",
        maturity="established",
    )
    
    print(f"\n🆔 IDENTITY:")
    print(f"  Email: {result['identity']['email']}")
    print(f"  Age: {result['identity']['email_age_days']} days")
    print(f"  Maturity: {result['identity']['maturity']}")
    print(f"  Visits: {result['identity']['total_visits']}")
    print(f"  Transactions: {result['identity']['total_transactions']}")
    
    print(f"\n🍪 BROWSER STATE:")
    print(f"  Cookie Domains: {len(result['browser_state']['cookie_domains'])}")
    print(f"  Total Cookies: {result['browser_state']['total_cookies']}")
    print(f"  Cross-site Presence: {sum(result['browser_state']['cross_site_presence'].values())}/{len(result['browser_state']['cross_site_presence'])} sites")
    
    print(f"\n🔥 WARM-UP:")
    print(f"  Duration: {result['warmup']['total_duration_seconds']:.0f} seconds")
    print(f"  Session Type: {result['warmup']['session_type']}")
    print(f"  Actions: {len(result['warmup']['sequence'])}")
    
    print(f"\n📉 RISK ANALYSIS:")
    print(f"  Baseline Risk: {result['risk_analysis']['baseline_risk_factor']}x")
    print(f"  Prepared Risk: {result['risk_analysis']['prepared_risk_factor']}x")
    print(f"  Risk Reduction: {result['risk_analysis']['risk_reduction_percent']}%")
    print(f"  Expected Decline Reduction: {result['risk_analysis']['expected_decline_reduction']}")
    
    print(f"\n💡 RECOMMENDATIONS:")
    for rec in result['recommendations']:
        print(f"  • {rec}")
