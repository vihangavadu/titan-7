"""
TITAN V7.0.2 SINGULARITY — DarkWeb & Forum Intelligence Monitor
Monitors reputed forums, CC shops, and darkweb sources for:
- New carding vectors and methods
- Fresh BIN lists and site drops
- Antifraud updates and bypasses
- CC shop ratings and stock quality

Architecture:
  1. CURATED SOURCE DATABASE: Rated forums, CC shops, Telegram channels
  2. MANUAL LOGIN SESSION: Operator logs in via real browser → cookies extracted
  3. AUTO-ENGAGEMENT: Handles forum rules (like/comment to unlock posts)
  4. FEED SCRAPER: Parses new posts, extracts actionable intelligence
  5. ALERT SYSTEM: Notifies operator of high-value new intel

Session Flow:
  Operator configures sources in Settings →
  Opens login browser for each source →
  Logs in manually (CAPTCHA, 2FA handled by human) →
  System extracts cookies/session →
  Background monitor scrapes on schedule →
  New intel appears in Intel Feed tab

Usage:
    from intel_monitor import IntelMonitor, get_sources, get_feed
    
    monitor = IntelMonitor()
    monitor.configure_source("source_id", cookies={...})
    feed = monitor.fetch_feed("source_id")
    alerts = monitor.get_alerts()
"""

import os
import json
import time
import hashlib
import logging
import subprocess
import re
import shutil
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

logger = logging.getLogger("TITAN-V7-INTEL-MONITOR")


# ═══════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════

class SourceType(Enum):
    FORUM = "forum"
    CC_SHOP = "cc_shop"
    TELEGRAM = "telegram"
    MARKET = "market"
    PASTE = "paste"
    RSS = "rss"


class SourceAccess(Enum):
    CLEARNET = "clearnet"       # Regular HTTPS
    TOR = "tor"                 # .onion via Tor
    I2P = "i2p"                 # .i2p via I2P


class SourceStatus(Enum):
    ACTIVE = "active"           # Source is up and monitored
    CONFIGURED = "configured"   # Credentials set, not yet fetching
    LOGIN_REQUIRED = "login_required"  # Needs manual login
    DOWN = "down"               # Source unreachable
    BANNED = "banned"           # Account banned/suspended
    UNCONFIGURED = "unconfigured"  # No credentials yet


class PostVisibility(Enum):
    """Forum post visibility rules"""
    PUBLIC = "public"                   # Anyone can read
    REGISTERED = "registered"           # Must be logged in
    LIKE_REQUIRED = "like_required"     # Must like post to see content
    REPLY_REQUIRED = "reply_required"   # Must reply to see content
    REPUTATION = "reputation"           # Need minimum reputation
    VIP = "vip"                         # Paid VIP section
    VOUCHED = "vouched"                 # Need vouches from existing members


class AlertPriority(Enum):
    CRITICAL = "critical"   # New vector, major bypass, fresh dump
    HIGH = "high"           # New BIN list, site drop, method update
    MEDIUM = "medium"       # Discussion, tip, minor update
    LOW = "low"             # General chatter


@dataclass
class IntelSource:
    """A monitored intelligence source"""
    source_id: str
    name: str
    source_type: SourceType
    access: SourceAccess
    url: str                            # Base URL (clearnet or .onion)
    rating: float                       # 1-5 star community rating
    description: str
    login_required: bool
    post_visibility: PostVisibility     # Default visibility rules
    auto_engage: bool                   # Can system auto-like/comment?
    engagement_template: str            # Template for auto-comments
    sections: List[str]                 # Forum sections to monitor
    refresh_minutes: int                # How often to check
    country_focus: List[str]            # Which CC countries they focus on
    specialties: List[str]              # What they're known for
    status: SourceStatus = SourceStatus.UNCONFIGURED
    last_fetch: str = ""
    notes: str = ""


@dataclass
class IntelPost:
    """A scraped intelligence post"""
    post_id: str
    source_id: str
    title: str
    author: str
    content: str                    # May be truncated if behind engagement wall
    url: str
    timestamp: str
    category: str                   # method, bin_list, site_drop, vector, discussion
    priority: AlertPriority
    tags: List[str]
    requires_engagement: bool       # True if content is behind like/reply wall
    engagement_done: bool           # True if system already engaged
    is_read: bool = False
    is_bookmarked: bool = False


@dataclass
class SessionConfig:
    """Session configuration for a source"""
    source_id: str
    cookies: Dict[str, str] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)
    user_agent: str = ""
    csrf_token: str = ""
    session_id: str = ""
    login_timestamp: str = ""
    expires_at: str = ""
    proxy: str = ""                 # SOCKS5 proxy for Tor
    auto_engage_enabled: bool = False
    engage_like: bool = True        # Auto-like posts
    engage_reply: bool = False      # Auto-reply (more risky)
    reply_templates: List[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# CURATED SOURCE DATABASE
# ═══════════════════════════════════════════════════════════════════════════

INTEL_SOURCES: List[IntelSource] = [
    # ─── TOP RATED FORUMS ───────────────────────────────────────────────
    IntelSource(
        "nulled", "Nulled.to", SourceType.FORUM, SourceAccess.CLEARNET,
        "https://nulled.to", 4.5,
        "Major cracking/carding forum. Methods, configs, tools, BIN lists. "
        "Very active community. Posts require likes/replies to view hidden content.",
        True, PostVisibility.LIKE_REQUIRED, True,
        "Thanks for sharing! +rep",
        ["Carding", "Methods", "Tutorials", "Tools", "BIN Lists", "Autoshop"],
        30, ["US", "GB", "CA", "EU"],
        ["methods", "configs", "tools", "bins", "tutorials"],
        notes="Must like posts to see hidden content. Auto-like supported."
    ),
    IntelSource(
        "cracked", "Cracked.io", SourceType.FORUM, SourceAccess.CLEARNET,
        "https://cracked.io", 4.3,
        "Large cracking forum. Carding section, method sharing, tool releases. "
        "Reply-to-view on most posts.",
        True, PostVisibility.REPLY_REQUIRED, True,
        "Good info, thanks for the share!",
        ["Carding", "Methods", "Tools", "Marketplace", "Tutorials"],
        30, ["US", "GB", "EU"],
        ["methods", "tools", "accounts", "configs"],
        notes="Must reply to see hidden content. Use varied reply templates."
    ),
    IntelSource(
        "breached", "BreachForums", SourceType.FORUM, SourceAccess.CLEARNET,
        "https://breachforums.st", 4.7,
        "Premier data breach forum. Database leaks, combo lists, vulnerability disclosures. "
        "High-quality intel on new vectors and antifraud changes.",
        True, PostVisibility.REGISTERED, False,
        "",
        ["Databases", "Leaks", "Carding", "Fraud", "Methods"],
        15, ["US", "GB", "EU", "GLOBAL"],
        ["databases", "leaks", "vectors", "antifraud_intel"],
        notes="Best source for new antifraud bypass intel. High reputation requirement for some sections."
    ),
    IntelSource(
        "sinisterly", "Sinisterly", SourceType.FORUM, SourceAccess.CLEARNET,
        "https://sinisterly.com", 3.8,
        "SE and fraud forum. Carding tutorials, social engineering methods. "
        "Beginner-friendly but has advanced sections.",
        True, PostVisibility.LIKE_REQUIRED, True,
        "Appreciate the knowledge drop!",
        ["Carding", "Social Engineering", "Methods", "Tutorials"],
        60, ["US", "GB"],
        ["tutorials", "social_engineering", "methods"],
        notes="Good for beginner methods. Like-to-view on tutorials."
    ),
    IntelSource(
        "darkforums", "Dark Forums", SourceType.FORUM, SourceAccess.TOR,
        "http://darkforumexample.onion", 4.0,
        "Tor-based fraud forum. Advanced methods, private sections. "
        "Vouched access for premium content.",
        True, PostVisibility.VOUCHED, False,
        "",
        ["Advanced Methods", "Private Deals", "BIN Intel"],
        60, ["US", "EU", "GLOBAL"],
        ["advanced_methods", "private_bins", "vendor_deals"],
        notes="Tor only. Need vouches for premium sections. High-quality intel."
    ),
    IntelSource(
        "altenen", "Altenen", SourceType.FORUM, SourceAccess.CLEARNET,
        "https://altenen.is", 4.2,
        "Long-running carding forum. Methods, tools, vendor reviews. "
        "Active marketplace section.",
        True, PostVisibility.REPLY_REQUIRED, True,
        "Solid method, thanks for sharing this.",
        ["Carding", "Methods", "Tools", "Vendor Reviews", "Marketplace"],
        30, ["US", "GB", "EU", "GLOBAL"],
        ["methods", "vendor_reviews", "tools", "marketplace"],
        notes="Reply-to-view on most method posts."
    ),
    IntelSource(
        "club2crd", "Club2CRD", SourceType.FORUM, SourceAccess.CLEARNET,
        "https://club2crd.cx", 3.9,
        "Carding-focused forum. Methods, BIN lists, CC shop reviews. "
        "Active community with daily new posts.",
        True, PostVisibility.LIKE_REQUIRED, True,
        "Thanks for the update!",
        ["Methods", "BIN Lists", "Shop Reviews", "Tools"],
        45, ["US", "GB", "CA"],
        ["methods", "bins", "shop_reviews"],
        notes="Like-to-view. Good for CC shop reviews and BIN intel."
    ),
    IntelSource(
        "carder_world", "Carder.World", SourceType.FORUM, SourceAccess.CLEARNET,
        "https://carder.world", 3.7,
        "Carding community forum. Beginner to advanced sections. "
        "Vendor marketplace with escrow.",
        True, PostVisibility.REGISTERED, False,
        "",
        ["Beginner", "Advanced", "Marketplace", "Reviews"],
        60, ["US", "EU"],
        ["methods", "marketplace", "reviews"],
        notes="Registration required. Good for vendor ratings."
    ),

    # ─── CC SHOPS (for monitoring stock quality, not purchasing) ─────────
    IntelSource(
        "yale_lodge", "Yale Lodge", SourceType.CC_SHOP, SourceAccess.CLEARNET,
        "https://yalelodge.cm", 4.5,
        "Top-rated CC shop. Known for valid rates >80%. "
        "US, UK, CA, AU bases. Premium pricing but high quality.",
        True, PostVisibility.REGISTERED, False,
        "",
        ["US Bases", "UK Bases", "CA Bases", "AU Bases"],
        120, ["US", "GB", "CA", "AU"],
        ["cc_bases", "validity_rates", "bin_selection"],
        notes="Monitor for new BIN drops and validity rates. Do NOT auto-engage."
    ),
    IntelSource(
        "briansclub", "BriansClub", SourceType.CC_SHOP, SourceAccess.TOR,
        "http://briansclubexample.onion", 4.6,
        "Largest CC shop by volume. Database of millions of cards. "
        "BIN checker, validity guarantee, auto-refund.",
        True, PostVisibility.REGISTERED, False,
        "",
        ["Search", "BIN Checker", "New Adds", "Stats"],
        120, ["US", "GB", "CA", "EU", "GLOBAL"],
        ["volume", "bin_availability", "validity_stats"],
        notes="Tor only. Monitor 'New Adds' for fresh dumps. Check validity stats."
    ),
    IntelSource(
        "jokers_stash_successor", "Joker's Legacy", SourceType.CC_SHOP, SourceAccess.TOR,
        "http://jokerslegacyexample.onion", 4.0,
        "Successor to Joker's Stash. Dumps and CVV bases. "
        "Known for US and EU inventory.",
        True, PostVisibility.REGISTERED, False,
        "",
        ["Dumps", "CVV", "New Bases"],
        120, ["US", "EU"],
        ["dumps", "cvv", "fresh_bases"],
        notes="Tor only. Monitor for fresh base announcements."
    ),
    IntelSource(
        "unicc_successor", "UniCC Legacy", SourceType.CC_SHOP, SourceAccess.TOR,
        "http://unicclegacyexample.onion", 3.8,
        "Successor shop with CVV/fullz inventory. "
        "Auto-checker and refund policy.",
        True, PostVisibility.REGISTERED, False,
        "",
        ["CVV", "Fullz", "Auto-Check"],
        180, ["US", "GB", "CA"],
        ["cvv", "fullz", "auto_check"],
        notes="Tor only. Monitor for quality BIN announcements."
    ),

    # ─── TELEGRAM CHANNELS ──────────────────────────────────────────────
    IntelSource(
        "tg_card_methods", "Card Methods TG", SourceType.TELEGRAM, SourceAccess.CLEARNET,
        "https://t.me/example_card_methods", 3.5,
        "Telegram channel sharing carding methods and BIN lists. "
        "Public channel, no engagement required.",
        False, PostVisibility.PUBLIC, False,
        "",
        ["Methods", "BINs", "Alerts"],
        10, ["US", "GB", "EU"],
        ["methods", "bins", "quick_alerts"],
        notes="Public Telegram. Fast updates. Mixed quality — verify before using."
    ),
    IntelSource(
        "tg_antifraud_intel", "Antifraud Intel TG", SourceType.TELEGRAM, SourceAccess.CLEARNET,
        "https://t.me/example_antifraud_intel", 4.0,
        "Telegram channel tracking antifraud system changes. "
        "Alerts when merchants update their fraud engines.",
        False, PostVisibility.PUBLIC, False,
        "",
        ["Antifraud Updates", "PSP Changes", "3DS Changes"],
        10, ["GLOBAL"],
        ["antifraud_changes", "psp_updates", "3ds_changes"],
        notes="High-value intel on antifraud changes. Automated monitoring."
    ),

    # ─── PASTE / RSS FEEDS ──────────────────────────────────────────────
    IntelSource(
        "rss_krebsonsecurity", "KrebsOnSecurity", SourceType.RSS, SourceAccess.CLEARNET,
        "https://krebsonsecurity.com/feed/", 4.8,
        "Brian Krebs security blog. Reports on CC shop takedowns, "
        "new fraud techniques, law enforcement actions.",
        False, PostVisibility.PUBLIC, False,
        "",
        ["Breaches", "Fraud", "Law Enforcement"],
        60, ["GLOBAL"],
        ["breach_news", "le_actions", "fraud_trends"],
        notes="Public RSS. Essential for knowing about shop takedowns and LE activity."
    ),
    IntelSource(
        "rss_bleepingcomputer", "BleepingComputer", SourceType.RSS, SourceAccess.CLEARNET,
        "https://www.bleepingcomputer.com/feed/", 4.5,
        "Security news. Covers data breaches, malware, fraud campaigns.",
        False, PostVisibility.PUBLIC, False,
        "",
        ["Security", "Breaches", "Malware"],
        60, ["GLOBAL"],
        ["breach_news", "security_updates"],
        notes="Public RSS. Good for early breach notifications."
    ),
]


# ═══════════════════════════════════════════════════════════════════════════
# AUTO-ENGAGEMENT ENGINE
# Handles forum rules: like/comment to unlock hidden content
# ═══════════════════════════════════════════════════════════════════════════

# Varied reply templates to avoid spam detection
DEFAULT_REPLY_TEMPLATES = [
    "Thanks for sharing this, very useful info!",
    "Appreciate the detailed breakdown, +rep",
    "Good stuff, been looking for something like this.",
    "Solid method, thanks for the contribution.",
    "This is exactly what I needed, thanks!",
    "Great share, looking forward to more from you.",
    "Helpful info, thanks for taking the time to post.",
    "Nice work on this, very thorough.",
    "Thanks for the update, this is valuable.",
    "Good to see quality posts like this, respect.",
    "Bookmarked for later, thanks for sharing.",
    "This community keeps delivering, thanks!",
    "Exactly what I was researching, perfect timing.",
    "Quality content as always, much appreciated.",
    "Thanks for keeping us updated on this.",
]


class AutoEngagement:
    """
    Handles forum engagement rules to unlock hidden post content.
    
    Many forums hide post content behind like/reply requirements.
    This engine manages automatic engagement while staying natural:
    - Varied reply templates (never repeat same message)
    - Randomized timing between engagements
    - Tracks which posts have been engaged
    - Respects rate limits to avoid bans
    """
    
    # Engagement cooldown per source (seconds)
    COOLDOWN = {
        "like": 5,          # Wait 5s between likes
        "reply": 30,        # Wait 30s between replies
        "follow": 60,       # Wait 60s between follows
    }
    
    # Max engagements per hour per source
    MAX_PER_HOUR = {
        "like": 30,
        "reply": 10,
        "follow": 5,
    }
    
    def __init__(self):
        self._engagement_log: Dict[str, List[float]] = {}
        self._used_templates: Dict[str, List[int]] = {}
    
    def can_engage(self, source_id: str, engage_type: str) -> bool:
        """Check if we can engage without hitting rate limits"""
        key = f"{source_id}:{engage_type}"
        now = time.time()
        
        if key not in self._engagement_log:
            self._engagement_log[key] = []
            return True
        
        # Clean old entries (>1 hour)
        self._engagement_log[key] = [
            t for t in self._engagement_log[key] if now - t < 3600
        ]
        
        # Check rate limit
        max_per_hour = self.MAX_PER_HOUR.get(engage_type, 10)
        if len(self._engagement_log[key]) >= max_per_hour:
            return False
        
        # Check cooldown
        if self._engagement_log[key]:
            last = self._engagement_log[key][-1]
            cooldown = self.COOLDOWN.get(engage_type, 10)
            if now - last < cooldown:
                return False
        
        return True
    
    def record_engagement(self, source_id: str, engage_type: str):
        """Record an engagement action"""
        key = f"{source_id}:{engage_type}"
        if key not in self._engagement_log:
            self._engagement_log[key] = []
        self._engagement_log[key].append(time.time())
    
    def get_reply_text(self, source_id: str, 
                       custom_templates: List[str] = None) -> str:
        """Get a varied reply text, avoiding recently used templates"""
        templates = custom_templates or DEFAULT_REPLY_TEMPLATES
        
        if source_id not in self._used_templates:
            self._used_templates[source_id] = []
        
        used = self._used_templates[source_id]
        
        # Find unused template
        available = [i for i in range(len(templates)) if i not in used]
        if not available:
            # Reset if all used
            self._used_templates[source_id] = []
            available = list(range(len(templates)))
        
        import random
        idx = random.choice(available)
        self._used_templates[source_id].append(idx)
        
        return templates[idx]


# ═══════════════════════════════════════════════════════════════════════════
# INTEL KEYWORD DETECTION
# Identifies high-value posts from scraped content
# ═══════════════════════════════════════════════════════════════════════════

INTEL_KEYWORDS = {
    "critical": {
        "keywords": [
            "new method", "fresh method", "working method", "0day", "zero-day",
            "bypass 3ds", "bypass forter", "bypass riskified", "bypass sift",
            "antifraud bypass", "new vector", "fresh bins", "high valid",
            "90% valid", "95% valid", "100% valid", "just tested",
            "unlimited method", "cashout method",
        ],
        "priority": AlertPriority.CRITICAL,
    },
    "high": {
        "keywords": [
            "bin list", "working bins", "non vbv", "non-vbv", "2d bins",
            "site drop", "new site", "easy site", "shopify method",
            "stripe method", "adyen bypass", "amazon method",
            "bestbuy method", "walmart method", "checker update",
            "validity rate", "refund method", "fullz", "fresh base",
        ],
        "priority": AlertPriority.HIGH,
    },
    "medium": {
        "keywords": [
            "tutorial", "guide", "how to", "step by step",
            "opsec", "antidetect", "residential proxy", "socks5",
            "cc to btc", "gift card", "cashapp", "crypto cashout",
            "drop address", "virtual card", "prepaid",
        ],
        "priority": AlertPriority.MEDIUM,
    },
}


def classify_post(title: str, content: str) -> Tuple[AlertPriority, List[str]]:
    """Classify a post by priority and matched keywords"""
    text = (title + " " + content).lower()
    matched_tags = []
    highest_priority = AlertPriority.LOW
    
    for level, config in INTEL_KEYWORDS.items():
        for kw in config["keywords"]:
            if kw.lower() in text:
                matched_tags.append(kw)
                if config["priority"].value < highest_priority.value or highest_priority == AlertPriority.LOW:
                    highest_priority = config["priority"]
    
    return highest_priority, list(set(matched_tags))


# ═══════════════════════════════════════════════════════════════════════════
# SESSION MANAGER
# Handles manual login → cookie extraction → session reuse
# ═══════════════════════════════════════════════════════════════════════════

class SessionManager:
    """
    Manages login sessions for monitored sources.
    
    Flow:
    1. Operator clicks "Login" in settings → real browser opens to source URL
    2. Operator logs in manually (handles CAPTCHA, 2FA, etc.)
    3. Operator clicks "Extract Session" → cookies/headers captured
    4. System stores session and reuses for automated fetching
    5. When session expires, operator is notified to re-login
    """
    
    SESSION_DIR = Path("/opt/titan/data/intel_monitor/sessions")
    
    def __init__(self):
        self.sessions: Dict[str, SessionConfig] = {}
        self._load_sessions()
    
    def _load_sessions(self):
        """Load saved sessions from disk"""
        if not self.SESSION_DIR.exists():
            return
        
        for session_file in self.SESSION_DIR.glob("*.json"):
            try:
                data = json.loads(session_file.read_text())
                source_id = data.get("source_id", session_file.stem)
                self.sessions[source_id] = SessionConfig(
                    source_id=source_id,
                    cookies=data.get("cookies", {}),
                    headers=data.get("headers", {}),
                    user_agent=data.get("user_agent", ""),
                    csrf_token=data.get("csrf_token", ""),
                    session_id=data.get("session_id", ""),
                    login_timestamp=data.get("login_timestamp", ""),
                    expires_at=data.get("expires_at", ""),
                    proxy=data.get("proxy", ""),
                    auto_engage_enabled=data.get("auto_engage_enabled", False),
                    engage_like=data.get("engage_like", True),
                    engage_reply=data.get("engage_reply", False),
                    reply_templates=data.get("reply_templates", []),
                )
            except Exception as e:
                logger.warning(f"Could not load session {session_file}: {e}")
    
    def save_session(self, config: SessionConfig):
        """Save session to disk"""
        self.sessions[config.source_id] = config
        try:
            self.SESSION_DIR.mkdir(parents=True, exist_ok=True)
            path = self.SESSION_DIR / f"{config.source_id}.json"
            data = {
                "source_id": config.source_id,
                "cookies": config.cookies,
                "headers": config.headers,
                "user_agent": config.user_agent,
                "csrf_token": config.csrf_token,
                "session_id": config.session_id,
                "login_timestamp": config.login_timestamp,
                "expires_at": config.expires_at,
                "proxy": config.proxy,
                "auto_engage_enabled": config.auto_engage_enabled,
                "engage_like": config.engage_like,
                "engage_reply": config.engage_reply,
                "reply_templates": config.reply_templates,
            }
            path.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Could not save session: {e}")
    
    def get_session(self, source_id: str) -> Optional[SessionConfig]:
        """Get session for a source"""
        return self.sessions.get(source_id)
    
    def is_session_valid(self, source_id: str) -> bool:
        """Check if a session is still likely valid"""
        session = self.sessions.get(source_id)
        if not session or not session.cookies:
            return False
        if session.expires_at:
            try:
                expires = datetime.fromisoformat(session.expires_at.rstrip("Z"))
                if datetime.now(timezone.utc) > expires.replace(tzinfo=timezone.utc) if expires.tzinfo is None else expires:
                    return False
            except (ValueError, TypeError):
                pass
        return True
    
    def extract_cookies_from_browser(self, source_id: str,
                                      profile_path: str = None) -> Dict[str, str]:
        """
        Extract cookies from a Firefox profile after manual login.
        
        The operator should:
        1. Open Firefox with the specified profile
        2. Navigate to the source URL and log in
        3. Close the browser
        4. Call this method to extract cookies
        
        Returns dict of cookie name → value.
        """
        if not profile_path:
            # Default Camoufox profile path
            profile_path = str(Path.home() / ".camoufox" / "profiles" / "intel_monitor")
        
        cookies_db = Path(profile_path) / "cookies.sqlite"
        if not cookies_db.exists():
            return {}
        
        cookies = {}
        try:
            import sqlite3
            conn = sqlite3.connect(str(cookies_db))
            cursor = conn.cursor()
            
            # Get source URL domain
            source = next((s for s in INTEL_SOURCES if s.source_id == source_id), None)
            if source:
                from urllib.parse import urlparse
                domain = urlparse(source.url).hostname
                
                cursor.execute(
                    "SELECT name, value FROM moz_cookies WHERE host LIKE ?",
                    (f"%{domain}%",)
                )
                for name, value in cursor.fetchall():
                    cookies[name] = value
            
            conn.close()
        except Exception as e:
            logger.error(f"Cookie extraction failed: {e}")
        
        return cookies
    
    def open_login_browser(self, source_id: str) -> Dict[str, str]:
        """
        Open a real browser for the operator to login manually.
        
        Returns instructions for the operator.
        """
        source = next((s for s in INTEL_SOURCES if s.source_id == source_id), None)
        if not source:
            return {"error": f"Unknown source: {source_id}"}
        
        profile_dir = self.SESSION_DIR / "browser_profiles" / source_id
        profile_dir.mkdir(parents=True, exist_ok=True)
        
        # Build browser command
        browser_cmd = ["firefox", "--profile", str(profile_dir)]
        
        if source.access == SourceAccess.TOR:
            # Use Tor Browser if available
            tor_browser = shutil.which("tor-browser") or shutil.which("torbrowser")
            if tor_browser:
                browser_cmd = [tor_browser]
            else:
                return {
                    "error": "Tor Browser not found. Install tor-browser or set SOCKS5 proxy.",
                    "manual_url": source.url,
                    "proxy_hint": "socks5://127.0.0.1:9050",
                }
        
        return {
            "source_id": source_id,
            "source_name": source.name,
            "url": source.url,
            "browser_command": " ".join(browser_cmd),
            "profile_path": str(profile_dir),
            "instructions": [
                f"1. Browser will open to: {source.url}",
                "2. Log in manually (handle any CAPTCHA, 2FA, etc.)",
                "3. Once logged in, browse to verify access works",
                "4. Close the browser",
                "5. Click 'Extract Session' in TITAN to capture cookies",
                "6. System will use these cookies for automated monitoring",
            ],
            "access_type": source.access.value,
            "login_required": source.login_required,
        }


# ═══════════════════════════════════════════════════════════════════════════
# FEED FETCHER
# Scrapes posts from configured sources
# ═══════════════════════════════════════════════════════════════════════════

class FeedFetcher:
    """
    Fetches and parses posts from monitored sources.
    
    Uses curl with session cookies for authenticated requests.
    Supports clearnet and Tor (.onion) sources.
    """
    
    TOR_PROXY = "socks5h://127.0.0.1:9050"
    
    def fetch_page(self, url: str, session: SessionConfig = None,
                   use_tor: bool = False, timeout: int = 30) -> Optional[str]:
        """Fetch a page with optional authentication and Tor routing"""
        cmd = [
            "curl", "-sL", "--max-time", str(timeout),
            "-A", session.user_agent if session and session.user_agent else
                  "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
        ]
        
        # Add Tor proxy
        if use_tor or (session and session.proxy):
            proxy = (session.proxy if session and session.proxy else self.TOR_PROXY)
            cmd.extend(["--proxy", proxy])
        
        # Add cookies
        if session and session.cookies:
            cookie_str = "; ".join(f"{k}={v}" for k, v in session.cookies.items())
            cmd.extend(["-b", cookie_str])
        
        # Add custom headers
        if session and session.headers:
            for k, v in session.headers.items():
                cmd.extend(["-H", f"{k}: {v}"])
        
        # Add CSRF token if present
        if session and session.csrf_token:
            cmd.extend(["-H", f"X-CSRF-Token: {session.csrf_token}"])
        
        cmd.append(url)
        
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 10)
            if proc.returncode == 0 and proc.stdout:
                return proc.stdout
        except Exception as e:
            logger.error(f"Fetch failed for {url}: {e}")
        
        return None
    
    def parse_rss(self, xml_content: str, source_id: str) -> List[IntelPost]:
        """Parse RSS/Atom feed into IntelPost list"""
        posts = []
        
        # Simple RSS parser (no external deps)
        items = re.findall(r'<item>(.*?)</item>', xml_content, re.DOTALL)
        if not items:
            items = re.findall(r'<entry>(.*?)</entry>', xml_content, re.DOTALL)
        
        for item in items[:20]:  # Max 20 items per feed
            title = re.search(r'<title[^>]*>(.*?)</title>', item, re.DOTALL)
            link = re.search(r'<link[^>]*>(.*?)</link>', item, re.DOTALL)
            if not link:
                link = re.search(r'<link[^>]*href="([^"]*)"', item)
            desc = re.search(r'<description[^>]*>(.*?)</description>', item, re.DOTALL)
            if not desc:
                desc = re.search(r'<content[^>]*>(.*?)</content>', item, re.DOTALL)
            pub_date = re.search(r'<pubDate[^>]*>(.*?)</pubDate>', item, re.DOTALL)
            author = re.search(r'<author[^>]*>(.*?)</author>', item, re.DOTALL)
            
            title_text = title.group(1).strip() if title else "Untitled"
            # Clean CDATA
            title_text = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', title_text)
            
            link_text = link.group(1).strip() if link else ""
            link_text = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', link_text)
            
            content_text = desc.group(1).strip() if desc else ""
            content_text = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', content_text)
            content_text = re.sub(r'<[^>]+>', '', content_text)[:500]
            
            priority, tags = classify_post(title_text, content_text)
            
            post_id = hashlib.md5(
                (source_id + title_text + link_text).encode()
            ).hexdigest()[:12]
            
            posts.append(IntelPost(
                post_id=post_id,
                source_id=source_id,
                title=title_text,
                author=author.group(1).strip() if author else "Unknown",
                content=content_text,
                url=link_text,
                timestamp=pub_date.group(1).strip() if pub_date else datetime.now(timezone.utc).isoformat(),
                category="news",
                priority=priority,
                tags=tags,
                requires_engagement=False,
                engagement_done=True,
            ))
        
        return posts


# ═══════════════════════════════════════════════════════════════════════════
# INTEL MONITOR — MAIN ENGINE
# ═══════════════════════════════════════════════════════════════════════════

class IntelMonitor:
    """
    V7.0.2: DarkWeb & Forum Intelligence Monitor.
    
    Monitors configured sources for new carding vectors, BIN lists,
    method updates, antifraud changes, and CC shop quality.
    
    Usage:
        monitor = IntelMonitor()
        
        # List available sources
        sources = monitor.get_sources()
        
        # Configure a source (after manual login)
        monitor.configure_source("nulled", cookies={...})
        
        # Fetch latest feed
        feed = monitor.fetch_feed("rss_krebsonsecurity")
        
        # Get all alerts (high-priority intel)
        alerts = monitor.get_alerts()
        
        # Get full feed across all sources
        all_posts = monitor.get_all_feeds()
    """
    
    DATA_DIR = Path("/opt/titan/data/intel_monitor")
    FEED_CACHE = DATA_DIR / "feed_cache"
    
    def __init__(self):
        self.sources = {s.source_id: s for s in INTEL_SOURCES}
        self.session_mgr = SessionManager()
        self.engagement = AutoEngagement()
        self.fetcher = FeedFetcher()
        self._feed_cache: Dict[str, List[IntelPost]] = {}
        self._load_feed_cache()
    
    def _load_feed_cache(self):
        """Load cached feeds from disk"""
        if not self.FEED_CACHE.exists():
            return
        for cache_file in self.FEED_CACHE.glob("*.json"):
            try:
                data = json.loads(cache_file.read_text())
                source_id = cache_file.stem
                self._feed_cache[source_id] = [
                    IntelPost(**post) for post in data.get("posts", [])
                    if isinstance(post, dict)
                ]
            except Exception as e:
                logger.debug(f"Could not load feed cache {cache_file.name}: {e}")
    
    def _save_feed_cache(self, source_id: str, posts: List[IntelPost]):
        """Save feed cache to disk"""
        try:
            self.FEED_CACHE.mkdir(parents=True, exist_ok=True)
            path = self.FEED_CACHE / f"{source_id}.json"
            data = {
                "source_id": source_id,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "posts": [
                    {
                        "post_id": p.post_id, "source_id": p.source_id,
                        "title": p.title, "author": p.author,
                        "content": p.content, "url": p.url,
                        "timestamp": p.timestamp, "category": p.category,
                        "priority": p.priority.value if isinstance(p.priority, AlertPriority) else p.priority,
                        "tags": p.tags,
                        "requires_engagement": p.requires_engagement,
                        "engagement_done": p.engagement_done,
                        "is_read": p.is_read,
                        "is_bookmarked": p.is_bookmarked,
                    }
                    for p in posts[:100]  # Cache max 100 posts per source
                ],
            }
            path.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.warning(f"Could not save feed cache: {e}")
    
    # ═══════════════════════════════════════════════════════════════════════
    # SOURCE MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════
    
    def get_sources(self, source_type: str = None) -> List[Dict]:
        """Get all available sources with their status"""
        results = []
        for sid, source in self.sources.items():
            if source_type and source.source_type.value != source_type:
                continue
            
            session_valid = self.session_mgr.is_session_valid(sid)
            
            results.append({
                "source_id": source.source_id,
                "name": source.name,
                "type": source.source_type.value,
                "access": source.access.value,
                "url": source.url,
                "rating": source.rating,
                "description": source.description,
                "login_required": source.login_required,
                "post_visibility": source.post_visibility.value,
                "auto_engage": source.auto_engage,
                "sections": source.sections,
                "refresh_minutes": source.refresh_minutes,
                "specialties": source.specialties,
                "status": "active" if session_valid else (
                    "login_required" if source.login_required else "ready"
                ),
                "session_valid": session_valid,
                "last_fetch": source.last_fetch,
                "notes": source.notes,
                "cached_posts": len(self._feed_cache.get(sid, [])),
            })
        
        # Sort by rating descending
        results.sort(key=lambda x: x["rating"], reverse=True)
        return results
    
    def get_source(self, source_id: str) -> Optional[Dict]:
        """Get a single source by ID"""
        sources = self.get_sources()
        return next((s for s in sources if s["source_id"] == source_id), None)
    
    def configure_source(self, source_id: str,
                         cookies: Dict[str, str] = None,
                         headers: Dict[str, str] = None,
                         user_agent: str = None,
                         proxy: str = None,
                         auto_engage: bool = None,
                         engage_like: bool = None,
                         engage_reply: bool = None,
                         reply_templates: List[str] = None) -> Dict:
        """
        Configure a source with login session and engagement settings.
        
        Call this after the operator has manually logged in and
        extracted cookies (or provide cookies directly).
        """
        if source_id not in self.sources:
            return {"error": f"Unknown source: {source_id}"}
        
        session = self.session_mgr.get_session(source_id) or SessionConfig(source_id=source_id)
        
        if cookies:
            session.cookies = cookies
        if headers:
            session.headers = headers
        if user_agent:
            session.user_agent = user_agent
        if proxy:
            session.proxy = proxy
        if auto_engage is not None:
            session.auto_engage_enabled = auto_engage
        if engage_like is not None:
            session.engage_like = engage_like
        if engage_reply is not None:
            session.engage_reply = engage_reply
        if reply_templates:
            session.reply_templates = reply_templates
        
        session.login_timestamp = datetime.now(timezone.utc).isoformat()
        # Default expiry: 24 hours
        session.expires_at = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
        
        self.session_mgr.save_session(session)
        
        return {
            "source_id": source_id,
            "status": "configured",
            "session_valid": True,
            "cookies_count": len(session.cookies),
            "auto_engage": session.auto_engage_enabled,
            "expires_at": session.expires_at,
        }
    
    def open_login(self, source_id: str) -> Dict:
        """Open browser for manual login"""
        return self.session_mgr.open_login_browser(source_id)
    
    def extract_session(self, source_id: str, profile_path: str = None) -> Dict:
        """Extract cookies from browser profile after manual login"""
        cookies = self.session_mgr.extract_cookies_from_browser(source_id, profile_path)
        if cookies:
            return self.configure_source(source_id, cookies=cookies)
        return {"error": "No cookies found. Make sure you logged in and closed the browser."}
    
    # ═══════════════════════════════════════════════════════════════════════
    # FEED FETCHING
    # ═══════════════════════════════════════════════════════════════════════
    
    def fetch_feed(self, source_id: str) -> List[Dict]:
        """
        Fetch latest posts from a source.
        
        For RSS feeds: no authentication needed.
        For forums: uses stored session cookies.
        For Tor sources: routes through Tor SOCKS5 proxy.
        """
        source = self.sources.get(source_id)
        if not source:
            return [{"error": f"Unknown source: {source_id}"}]
        
        session = self.session_mgr.get_session(source_id)
        use_tor = source.access == SourceAccess.TOR
        
        # Check if login is needed
        if source.login_required and not self.session_mgr.is_session_valid(source_id):
            return [{"error": f"Login required for {source.name}. Configure session first."}]
        
        posts = []
        
        if source.source_type == SourceType.RSS:
            # RSS feed — simple fetch and parse
            html = self.fetcher.fetch_page(source.url, session, use_tor)
            if html:
                posts = self.fetcher.parse_rss(html, source_id)
        else:
            # Forum/shop — fetch main page and extract post titles/links
            html = self.fetcher.fetch_page(source.url, session, use_tor)
            if html:
                posts = self._parse_forum_page(html, source)
        
        # Update cache
        if posts:
            # Merge with existing cache (avoid duplicates)
            existing_ids = {p.post_id for p in self._feed_cache.get(source_id, [])}
            new_posts = [p for p in posts if p.post_id not in existing_ids]
            
            cached = self._feed_cache.get(source_id, [])
            cached = new_posts + cached
            cached = cached[:100]  # Keep max 100
            self._feed_cache[source_id] = cached
            self._save_feed_cache(source_id, cached)
            
            source.last_fetch = datetime.now(timezone.utc).isoformat()
        
        return [self._post_to_dict(p) for p in posts]
    
    def get_cached_feed(self, source_id: str) -> List[Dict]:
        """Get cached feed for a source (no network request)"""
        posts = self._feed_cache.get(source_id, [])
        return [self._post_to_dict(p) for p in posts]
    
    def get_all_feeds(self) -> List[Dict]:
        """Get all cached feeds merged and sorted by timestamp"""
        all_posts = []
        for source_id, posts in self._feed_cache.items():
            all_posts.extend(posts)
        
        all_posts.sort(key=lambda p: p.timestamp, reverse=True)
        return [self._post_to_dict(p) for p in all_posts[:200]]
    
    def get_alerts(self, min_priority: str = "high") -> List[Dict]:
        """Get high-priority alerts across all feeds"""
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        min_level = priority_order.get(min_priority, 1)
        
        alerts = []
        for source_id, posts in self._feed_cache.items():
            for p in posts:
                p_level = priority_order.get(
                    p.priority.value if isinstance(p.priority, AlertPriority) else p.priority, 3
                )
                if p_level <= min_level:
                    alerts.append(self._post_to_dict(p))
        
        alerts.sort(key=lambda x: priority_order.get(x["priority"], 3))
        return alerts[:50]
    
    def _parse_forum_page(self, html: str, source: IntelSource) -> List[IntelPost]:
        """Extract post titles and links from a forum page"""
        posts = []
        
        # Generic forum post extraction (title + link patterns)
        # Pattern 1: <a href="..." class="...thread...">Title</a>
        thread_patterns = [
            r'<a[^>]*href="([^"]*thread[^"]*)"[^>]*>(.*?)</a>',
            r'<a[^>]*href="([^"]*topic[^"]*)"[^>]*>(.*?)</a>',
            r'<a[^>]*href="([^"]*showthread[^"]*)"[^>]*>(.*?)</a>',
            r'<a[^>]*class="[^"]*thread-title[^"]*"[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
            r'<h3[^>]*class="[^"]*title[^"]*"[^>]*>\s*<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
        ]
        
        seen_titles = set()
        for pattern in thread_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE | re.DOTALL)
            for link, title in matches:
                title_clean = re.sub(r'<[^>]+>', '', title).strip()
                if not title_clean or len(title_clean) < 5:
                    continue
                if title_clean in seen_titles:
                    continue
                seen_titles.add(title_clean)
                
                # Make URL absolute
                if link.startswith("/"):
                    from urllib.parse import urlparse
                    parsed = urlparse(source.url)
                    link = f"{parsed.scheme}://{parsed.netloc}{link}"
                elif not link.startswith("http"):
                    link = source.url.rstrip("/") + "/" + link
                
                priority, tags = classify_post(title_clean, "")
                
                post_id = hashlib.md5(
                    (source.source_id + title_clean).encode()
                ).hexdigest()[:12]
                
                # Determine if content is behind engagement wall
                requires_engagement = source.post_visibility in (
                    PostVisibility.LIKE_REQUIRED,
                    PostVisibility.REPLY_REQUIRED,
                )
                
                posts.append(IntelPost(
                    post_id=post_id,
                    source_id=source.source_id,
                    title=title_clean,
                    author="Unknown",
                    content="[Content requires engagement — click to view and engage]" if requires_engagement else "",
                    url=link,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    category="thread",
                    priority=priority,
                    tags=tags,
                    requires_engagement=requires_engagement,
                    engagement_done=False,
                ))
        
        return posts[:30]  # Max 30 posts per fetch
    
    def _post_to_dict(self, p: IntelPost) -> Dict:
        """Convert IntelPost to dict"""
        priority_val = p.priority.value if isinstance(p.priority, AlertPriority) else p.priority
        return {
            "post_id": p.post_id,
            "source_id": p.source_id,
            "source_name": self.sources.get(p.source_id, IntelSource(
                "", p.source_id, SourceType.FORUM, SourceAccess.CLEARNET,
                "", 0, "", False, PostVisibility.PUBLIC, False, "", [], 0, [], []
            )).name,
            "title": p.title,
            "author": p.author,
            "content": p.content[:300],
            "url": p.url,
            "timestamp": p.timestamp,
            "category": p.category,
            "priority": priority_val,
            "priority_icon": {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "⚪"}.get(priority_val, "⚪"),
            "tags": p.tags,
            "requires_engagement": p.requires_engagement,
            "engagement_done": p.engagement_done,
            "is_read": p.is_read,
            "is_bookmarked": p.is_bookmarked,
        }
    
    # ═══════════════════════════════════════════════════════════════════════
    # SETTINGS / CONFIG API (for GUI settings tab)
    # ═══════════════════════════════════════════════════════════════════════
    
    def get_settings(self) -> Dict:
        """Get current monitor settings for GUI settings tab"""
        configured = sum(1 for sid in self.sources 
                        if self.session_mgr.is_session_valid(sid))
        
        return {
            "total_sources": len(self.sources),
            "configured_sources": configured,
            "unconfigured_sources": len(self.sources) - configured,
            "tor_proxy": FeedFetcher.TOR_PROXY,
            "session_dir": str(SessionManager.SESSION_DIR),
            "feed_cache_dir": str(self.FEED_CACHE),
            "total_cached_posts": sum(
                len(posts) for posts in self._feed_cache.values()
            ),
            "sources": self.get_sources(),
            "engagement_templates": DEFAULT_REPLY_TEMPLATES,
        }
    
    def update_settings(self, tor_proxy: str = None,
                        refresh_all_minutes: int = None) -> Dict:
        """Update global monitor settings"""
        if tor_proxy:
            FeedFetcher.TOR_PROXY = tor_proxy
        
        if refresh_all_minutes:
            for source in self.sources.values():
                source.refresh_minutes = refresh_all_minutes
        
        return self.get_settings()


# ═══════════════════════════════════════════════════════════════════════════
# CONVENIENCE EXPORTS
# ═══════════════════════════════════════════════════════════════════════════

def get_intel_sources(source_type=None):
    """Get all intel sources"""
    return IntelMonitor().get_sources(source_type)

def get_intel_feed(source_id):
    """Get cached feed for a source"""
    return IntelMonitor().get_cached_feed(source_id)

def get_intel_alerts(min_priority="high"):
    """Get high-priority intel alerts"""
    return IntelMonitor().get_alerts(min_priority)

def get_intel_settings():
    """Get monitor settings"""
    return IntelMonitor().get_settings()


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 INTEL CORRELATION ENGINE — Correlate intel across multiple sources
# ═══════════════════════════════════════════════════════════════════════════════

from collections import defaultdict


@dataclass
class CorrelatedIntel:
    """Correlated intelligence from multiple sources."""
    correlation_id: str
    topic: str
    sources: List[str]
    posts: List[str]  # post IDs
    first_seen: float
    last_updated: float
    confidence: float
    keywords: List[str]
    summary: str


class IntelCorrelationEngine:
    """
    V7.6 Intel Correlation Engine - Correlates related intel
    across multiple sources to identify trends and validate info.
    """
    
    # Topic patterns for correlation
    TOPIC_PATTERNS = {
        "3ds_bypass": [
            r"3ds", r"3d.?secure", r"otp.?bypass", r"verification.?bypass"
        ],
        "new_method": [
            r"new.?method", r"fresh.?method", r"working.?method", r"2024.?method"
        ],
        "bin_drop": [
            r"fresh.?bin", r"new.?bin", r"bin.?list", r"nonvbv", r"non-?vbv"
        ],
        "site_target": [
            r"amazon", r"bestbuy", r"walmart", r"target", r"ebay", r"shopify"
        ],
        "psp_change": [
            r"stripe", r"adyen", r"forter", r"riskified", r"sift", r"signifyd"
        ],
        "shop_news": [
            r"shop.?down", r"shop.?up", r"new.?shop", r"shop.?exit", r"validity"
        ],
    }
    
    def __init__(self):
        self._correlations: Dict[str, CorrelatedIntel] = {}
        self._post_to_correlation: Dict[str, str] = {}
    
    def _extract_topics(self, text: str) -> List[str]:
        """Extract topics from text."""
        topics = []
        text_lower = text.lower()
        
        for topic, patterns in self.TOPIC_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    topics.append(topic)
                    break
        
        return topics
    
    def correlate_post(self, post: IntelPost) -> Optional[CorrelatedIntel]:
        """
        Correlate a post with existing correlations or create new one.
        
        Args:
            post: The post to correlate
        
        Returns:
            Updated or new correlation
        """
        text = post.title + " " + post.content
        topics = self._extract_topics(text)
        
        if not topics:
            return None
        
        # Find matching correlation
        best_match = None
        best_overlap = 0
        
        for corr_id, corr in self._correlations.items():
            # Check topic overlap
            overlap = len(set(topics) & set(self._extract_topics(corr.topic)))
            if overlap > best_overlap:
                best_overlap = overlap
                best_match = corr
        
        now = time.time()
        
        if best_match and best_overlap > 0:
            # Update existing correlation
            if post.source_id not in best_match.sources:
                best_match.sources.append(post.source_id)
            if post.post_id not in best_match.posts:
                best_match.posts.append(post.post_id)
            best_match.last_updated = now
            best_match.confidence = min(1.0, len(best_match.sources) * 0.2)
            best_match.keywords = list(set(best_match.keywords + post.tags))
            
            self._post_to_correlation[post.post_id] = best_match.correlation_id
            return best_match
        else:
            # Create new correlation
            corr_id = hashlib.md5(
                f"{topics[0]}{now}".encode()
            ).hexdigest()[:12]
            
            correlation = CorrelatedIntel(
                correlation_id=corr_id,
                topic=topics[0],
                sources=[post.source_id],
                posts=[post.post_id],
                first_seen=now,
                last_updated=now,
                confidence=0.2,
                keywords=post.tags,
                summary=post.title[:100]
            )
            
            self._correlations[corr_id] = correlation
            self._post_to_correlation[post.post_id] = corr_id
            return correlation
    
    def correlate_batch(self, posts: List[IntelPost]) -> List[CorrelatedIntel]:
        """Correlate a batch of posts."""
        updated = set()
        
        for post in posts:
            result = self.correlate_post(post)
            if result:
                updated.add(result.correlation_id)
        
        return [self._correlations[cid] for cid in updated]
    
    def get_trending_topics(self, hours: int = 24) -> List[Dict]:
        """Get trending topics from recent correlations."""
        cutoff = time.time() - (hours * 3600)
        
        recent = [
            c for c in self._correlations.values()
            if c.last_updated > cutoff
        ]
        
        # Sort by confidence and source count
        recent.sort(key=lambda x: (x.confidence, len(x.sources)), reverse=True)
        
        return [
            {
                "topic": c.topic,
                "sources": len(c.sources),
                "posts": len(c.posts),
                "confidence": c.confidence,
                "summary": c.summary,
                "keywords": c.keywords[:5]
            }
            for c in recent[:10]
        ]
    
    def get_cross_source_validated(self) -> List[CorrelatedIntel]:
        """Get intel validated across multiple sources."""
        return [
            c for c in self._correlations.values()
            if len(c.sources) >= 2 and c.confidence >= 0.4
        ]


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 SOURCE REPUTATION TRACKER — Track source reputation over time
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class SourceReputation:
    """Reputation data for an intel source."""
    source_id: str
    base_rating: float
    accuracy_score: float
    freshness_score: float
    reliability_score: float
    overall_score: float
    accurate_posts: int
    inaccurate_posts: int
    total_posts: int
    last_updated: float


class SourceReputationTracker:
    """
    V7.6 Source Reputation Tracker - Tracks and scores source
    reputation based on intel accuracy and reliability.
    """
    
    def __init__(self):
        self._reputations: Dict[str, SourceReputation] = {}
        self._feedback: Dict[str, List[Dict]] = defaultdict(list)
    
    def initialize_source(self, source: IntelSource):
        """Initialize reputation for a source."""
        self._reputations[source.source_id] = SourceReputation(
            source_id=source.source_id,
            base_rating=source.rating,
            accuracy_score=source.rating / 5.0,
            freshness_score=1.0,
            reliability_score=1.0,
            overall_score=source.rating / 5.0,
            accurate_posts=0,
            inaccurate_posts=0,
            total_posts=0,
            last_updated=time.time()
        )
    
    def record_feedback(self, source_id: str, post_id: str,
                       accurate: bool, fresh: bool = True,
                       notes: str = ""):
        """
        Record feedback on a post from a source.
        
        Args:
            source_id: Source ID
            post_id: Post ID
            accurate: Whether the intel was accurate
            fresh: Whether the intel was timely
            notes: Optional notes
        """
        self._feedback[source_id].append({
            "post_id": post_id,
            "accurate": accurate,
            "fresh": fresh,
            "notes": notes,
            "timestamp": time.time()
        })
        
        self._update_reputation(source_id)
    
    def _update_reputation(self, source_id: str):
        """Recalculate reputation based on feedback."""
        if source_id not in self._reputations:
            return
        
        rep = self._reputations[source_id]
        feedback = self._feedback.get(source_id, [])
        
        if not feedback:
            return
        
        # Calculate scores from recent feedback (last 30 days)
        recent_cutoff = time.time() - (30 * 24 * 3600)
        recent = [f for f in feedback if f["timestamp"] > recent_cutoff]
        
        if recent:
            accurate_count = sum(1 for f in recent if f["accurate"])
            fresh_count = sum(1 for f in recent if f["fresh"])
            
            rep.accuracy_score = accurate_count / len(recent)
            rep.freshness_score = fresh_count / len(recent)
            rep.accurate_posts += accurate_count
            rep.inaccurate_posts += len(recent) - accurate_count
        
        rep.total_posts = len(feedback)
        
        # Reliability based on consistency
        if len(feedback) >= 5:
            # Calculate variance in accuracy over windows
            windows = [feedback[i:i+5] for i in range(0, len(feedback)-4, 5)]
            if windows:
                accuracies = [
                    sum(1 for f in w if f["accurate"]) / len(w)
                    for w in windows
                ]
                if len(accuracies) > 1:
                    import statistics
                    variance = statistics.variance(accuracies)
                    rep.reliability_score = max(0, 1 - variance * 2)
        
        # Overall score
        rep.overall_score = (
            rep.accuracy_score * 0.5 +
            rep.freshness_score * 0.3 +
            rep.reliability_score * 0.2
        )
        
        rep.last_updated = time.time()
    
    def get_reputation(self, source_id: str) -> Optional[Dict]:
        """Get reputation for a source."""
        rep = self._reputations.get(source_id)
        if not rep:
            return None
        
        return {
            "source_id": rep.source_id,
            "base_rating": rep.base_rating,
            "accuracy_score": round(rep.accuracy_score, 2),
            "freshness_score": round(rep.freshness_score, 2),
            "reliability_score": round(rep.reliability_score, 2),
            "overall_score": round(rep.overall_score, 2),
            "accurate_posts": rep.accurate_posts,
            "inaccurate_posts": rep.inaccurate_posts,
            "total_posts": rep.total_posts
        }
    
    def get_rankings(self) -> List[Dict]:
        """Get sources ranked by reputation."""
        rankings = []
        for source_id, rep in self._reputations.items():
            rankings.append({
                "source_id": source_id,
                "overall_score": rep.overall_score,
                "accuracy": rep.accuracy_score,
                "total_posts": rep.total_posts
            })
        
        rankings.sort(key=lambda x: x["overall_score"], reverse=True)
        return rankings


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 THREAT FEED AGGREGATOR — Aggregate feeds with deduplication
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class AggregatedPost:
    """A post aggregated from multiple sources."""
    aggregate_id: str
    canonical_title: str
    sources: List[str]
    post_ids: List[str]
    content: str
    priority: AlertPriority
    first_seen: float
    dedup_confidence: float


class ThreatFeedAggregator:
    """
    V7.6 Threat Feed Aggregator - Aggregates intel from multiple
    sources with deduplication and normalization.
    """
    
    # Similarity threshold for deduplication
    SIMILARITY_THRESHOLD = 0.7
    
    def __init__(self):
        self._aggregated: Dict[str, AggregatedPost] = {}
        self._post_to_aggregate: Dict[str, str] = {}
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity using token overlap."""
        tokens1 = set(re.findall(r'\w+', text1.lower()))
        tokens2 = set(re.findall(r'\w+', text2.lower()))
        
        if not tokens1 or not tokens2:
            return 0
        
        intersection = tokens1 & tokens2
        union = tokens1 | tokens2
        
        return len(intersection) / len(union) if union else 0
    
    def aggregate_post(self, post: IntelPost) -> AggregatedPost:
        """
        Aggregate a post, deduplicating against existing posts.
        
        Args:
            post: Post to aggregate
        
        Returns:
            Aggregated post (new or existing)
        """
        # Find matching aggregate
        best_match = None
        best_similarity = 0
        
        for agg_id, agg in self._aggregated.items():
            similarity = self._calculate_similarity(post.title, agg.canonical_title)
            if similarity > best_similarity and similarity >= self.SIMILARITY_THRESHOLD:
                best_similarity = similarity
                best_match = agg
        
        if best_match:
            # Deduplicate into existing
            if post.source_id not in best_match.sources:
                best_match.sources.append(post.source_id)
            if post.post_id not in best_match.post_ids:
                best_match.post_ids.append(post.post_id)
            best_match.dedup_confidence = max(best_match.dedup_confidence, best_similarity)
            
            # Upgrade priority if higher from new source
            post_priority = post.priority if isinstance(post.priority, AlertPriority) else AlertPriority(post.priority)
            if post_priority.value < best_match.priority.value:
                best_match.priority = post_priority
            
            self._post_to_aggregate[post.post_id] = best_match.aggregate_id
            return best_match
        else:
            # Create new aggregate
            agg_id = hashlib.md5(
                f"{post.title}{post.post_id}".encode()
            ).hexdigest()[:12]
            
            post_priority = post.priority if isinstance(post.priority, AlertPriority) else AlertPriority(post.priority)
            
            aggregate = AggregatedPost(
                aggregate_id=agg_id,
                canonical_title=post.title,
                sources=[post.source_id],
                post_ids=[post.post_id],
                content=post.content,
                priority=post_priority,
                first_seen=time.time(),
                dedup_confidence=1.0
            )
            
            self._aggregated[agg_id] = aggregate
            self._post_to_aggregate[post.post_id] = agg_id
            return aggregate
    
    def aggregate_batch(self, posts: List[IntelPost]) -> Dict[str, int]:
        """
        Aggregate a batch of posts.
        
        Returns:
            Stats on new vs deduplicated
        """
        new_count = 0
        dedup_count = 0
        
        for post in posts:
            before_count = len(self._aggregated)
            self.aggregate_post(post)
            if len(self._aggregated) > before_count:
                new_count += 1
            else:
                dedup_count += 1
        
        return {
            "processed": len(posts),
            "new": new_count,
            "deduplicated": dedup_count
        }
    
    def get_unique_feed(self, priority_filter: Optional[str] = None,
                       limit: int = 50) -> List[Dict]:
        """Get deduplicated feed."""
        aggregates = list(self._aggregated.values())
        
        if priority_filter:
            target = AlertPriority(priority_filter)
            aggregates = [a for a in aggregates if a.priority.value <= target.value]
        
        # Sort by first seen, newest first
        aggregates.sort(key=lambda x: x.first_seen, reverse=True)
        
        return [
            {
                "id": a.aggregate_id,
                "title": a.canonical_title,
                "sources": a.sources,
                "source_count": len(a.sources),
                "priority": a.priority.value,
                "first_seen": a.first_seen,
                "content_preview": a.content[:200] if a.content else ""
            }
            for a in aggregates[:limit]
        ]
    
    def get_multi_source_intel(self) -> List[Dict]:
        """Get intel confirmed by multiple sources."""
        multi = [a for a in self._aggregated.values() if len(a.sources) >= 2]
        multi.sort(key=lambda x: len(x.sources), reverse=True)
        
        return [
            {
                "title": a.canonical_title,
                "sources": a.sources,
                "source_count": len(a.sources),
                "priority": a.priority.value,
                "confidence": "high" if len(a.sources) >= 3 else "medium"
            }
            for a in multi
        ]


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 INTEL REPORT GENERATOR — Generate intelligence reports
# ═══════════════════════════════════════════════════════════════════════════════

class IntelReportGenerator:
    """
    V7.6 Intel Report Generator - Generates formatted intelligence
    reports from collected data.
    """
    
    REPORT_DIR = Path("/opt/titan/data/intel_reports")
    
    def __init__(self, monitor: Optional[IntelMonitor] = None,
                 aggregator: Optional[ThreatFeedAggregator] = None,
                 correlation: Optional[IntelCorrelationEngine] = None):
        """
        Initialize report generator.
        
        Args:
            monitor: IntelMonitor instance
            aggregator: ThreatFeedAggregator instance
            correlation: IntelCorrelationEngine instance
        """
        self.monitor = monitor or IntelMonitor()
        self.aggregator = aggregator or ThreatFeedAggregator()
        self.correlation = correlation or IntelCorrelationEngine()
    
    def generate_daily_brief(self) -> Dict:
        """
        Generate daily intelligence brief.
        
        Returns:
            Structured daily report
        """
        now = datetime.now(timezone.utc)
        
        # Get alerts from last 24 hours
        alerts = self.monitor.get_alerts(min_priority="high")
        
        # Get trending topics
        trending = self.correlation.get_trending_topics(hours=24)
        
        # Get multi-source validated intel
        validated = self.aggregator.get_multi_source_intel()
        
        report = {
            "report_type": "daily_brief",
            "generated_at": now.isoformat(),
            "period": "24h",
            "summary": {
                "critical_alerts": len([a for a in alerts if a.get("priority") == "critical"]),
                "high_alerts": len([a for a in alerts if a.get("priority") == "high"]),
                "trending_topics": len(trending),
                "multi_source_intel": len(validated)
            },
            "critical_intel": [
                {
                    "title": a["title"],
                    "source": a["source_name"],
                    "url": a["url"],
                    "tags": a["tags"]
                }
                for a in alerts[:5] if a.get("priority") == "critical"
            ],
            "trending": trending[:5],
            "validated_intel": validated[:5],
            "source_activity": {
                source_id: len(posts)
                for source_id, posts in self.monitor._feed_cache.items()
            }
        }
        
        return report
    
    def generate_topic_report(self, topic: str) -> Dict:
        """
        Generate focused report on a specific topic.
        
        Args:
            topic: Topic to report on (e.g., "3ds_bypass", "amazon")
        
        Returns:
            Topic-focused report
        """
        # Search all posts for topic
        relevant_posts = []
        topic_lower = topic.lower()
        
        for source_id, posts in self.monitor._feed_cache.items():
            for post in posts:
                if topic_lower in post.title.lower() or topic_lower in post.content.lower():
                    relevant_posts.append(post)
        
        # Sort by timestamp
        relevant_posts.sort(key=lambda p: p.timestamp, reverse=True)
        
        return {
            "report_type": "topic_report",
            "topic": topic,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_posts": len(relevant_posts),
            "sources": list(set(p.source_id for p in relevant_posts)),
            "timeline": [
                {
                    "date": p.timestamp[:10] if len(p.timestamp) >= 10 else p.timestamp,
                    "title": p.title,
                    "source": p.source_id,
                    "priority": p.priority.value if isinstance(p.priority, AlertPriority) else p.priority
                }
                for p in relevant_posts[:20]
            ],
            "key_insights": self._extract_insights(relevant_posts)
        }
    
    def _extract_insights(self, posts: List[IntelPost]) -> List[str]:
        """Extract key insights from posts."""
        insights = []
        
        # Count priority distribution
        priorities = defaultdict(int)
        for p in posts:
            pval = p.priority.value if isinstance(p.priority, AlertPriority) else p.priority
            priorities[pval] += 1
        
        if priorities.get("critical", 0) > 0:
            insights.append(f"{priorities['critical']} critical priority items detected")
        
        # Count source distribution
        sources = defaultdict(int)
        for p in posts:
            sources[p.source_id] += 1
        
        if len(sources) > 1:
            top_source = max(sources.items(), key=lambda x: x[1])
            insights.append(f"Most activity from {top_source[0]} ({top_source[1]} posts)")
        
        # Tag analysis
        all_tags = []
        for p in posts:
            all_tags.extend(p.tags)
        
        tag_counts = defaultdict(int)
        for tag in all_tags:
            tag_counts[tag] += 1
        
        if tag_counts:
            top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            tag_str = ", ".join([t[0] for t in top_tags])
            insights.append(f"Common keywords: {tag_str}")
        
        return insights
    
    def save_report(self, report: Dict, filename: str = None) -> str:
        """Save report to file."""
        self.REPORT_DIR.mkdir(parents=True, exist_ok=True)
        
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"intel_report_{timestamp}.json"
        
        path = self.REPORT_DIR / filename
        path.write_text(json.dumps(report, indent=2, default=str))
        
        return str(path)
    
    def generate_markdown_report(self, report: Dict) -> str:
        """Generate markdown formatted report."""
        lines = []
        
        lines.append(f"# Intel Report: {report.get('report_type', 'Unknown')}")
        lines.append(f"\nGenerated: {report.get('generated_at', 'Unknown')}")
        lines.append("")
        
        if "summary" in report:
            lines.append("## Summary")
            for key, value in report["summary"].items():
                lines.append(f"- **{key.replace('_', ' ').title()}**: {value}")
            lines.append("")
        
        if "critical_intel" in report and report["critical_intel"]:
            lines.append("## Critical Intel")
            for item in report["critical_intel"]:
                lines.append(f"- [{item['title']}]({item['url']})")
                lines.append(f"  - Source: {item['source']}")
                if item.get('tags'):
                    lines.append(f"  - Tags: {', '.join(item['tags'])}")
            lines.append("")
        
        if "trending" in report and report["trending"]:
            lines.append("## Trending Topics")
            for topic in report["trending"]:
                lines.append(f"- **{topic['topic']}**: {topic['sources']} sources, {topic['posts']} posts")
            lines.append("")
        
        return "\n".join(lines)


# Global instances
_intel_correlation: Optional[IntelCorrelationEngine] = None
_reputation_tracker: Optional[SourceReputationTracker] = None
_feed_aggregator: Optional[ThreatFeedAggregator] = None
_report_generator: Optional[IntelReportGenerator] = None


def get_intel_correlation() -> IntelCorrelationEngine:
    """Get global intel correlation engine."""
    global _intel_correlation
    if _intel_correlation is None:
        _intel_correlation = IntelCorrelationEngine()
    return _intel_correlation


def get_reputation_tracker() -> SourceReputationTracker:
    """Get global reputation tracker."""
    global _reputation_tracker
    if _reputation_tracker is None:
        _reputation_tracker = SourceReputationTracker()
    return _reputation_tracker


def get_feed_aggregator() -> ThreatFeedAggregator:
    """Get global feed aggregator."""
    global _feed_aggregator
    if _feed_aggregator is None:
        _feed_aggregator = ThreatFeedAggregator()
    return _feed_aggregator


def get_report_generator() -> IntelReportGenerator:
    """Get global report generator."""
    global _report_generator
    if _report_generator is None:
        _report_generator = IntelReportGenerator()
    return _report_generator
