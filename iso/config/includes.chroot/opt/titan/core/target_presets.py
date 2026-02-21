"""
TITAN V7.0 SINGULARITY - Target Presets
Pre-configured target site profiles for optimized profile generation

Each target has:
- Domain and category
- History domains to include
- Cookie configurations
- localStorage keys
- Hardware recommendations
- 3DS risk assessment
- KYC requirements
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum


class TargetCategory(Enum):
    """Target site categories"""
    GAMING_MARKETPLACE = "gaming_marketplace"
    RETAIL = "retail"
    ELECTRONICS = "electronics"
    GAMING_PLATFORM = "gaming_platform"
    DIGITAL_GOODS = "digital_goods"
    SUBSCRIPTION = "subscription"
    CRYPTO = "crypto"
    FINANCIAL = "financial"


@dataclass
class TargetPreset:
    """Complete target site configuration"""
    name: str
    domain: str
    category: TargetCategory
    
    # History generation
    history_domains: List[str] = field(default_factory=list)
    history_weight: Dict[str, int] = field(default_factory=dict)
    
    # Cookie configuration
    cookies: List[Dict[str, Any]] = field(default_factory=list)
    
    # localStorage keys
    localstorage: Dict[str, Dict[str, str]] = field(default_factory=dict)
    
    # Hardware recommendation
    recommended_hardware: str = "windows_desktop_nvidia"
    
    # Archetype
    recommended_archetype: str = "casual_shopper"
    
    # Risk assessment
    three_ds_rate: float = 0.25
    kyc_required: bool = False
    kyc_trigger: str = ""
    
    # Profile requirements
    min_age_days: int = 60
    recommended_age_days: int = 90
    min_storage_mb: int = 300
    recommended_storage_mb: int = 500
    
    # Referrer chain
    referrer_chain: List[str] = field(default_factory=list)
    
    # Search queries for warmup
    warmup_searches: List[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# GAMING MARKETPLACE TARGETS
# ═══════════════════════════════════════════════════════════════════════════

ENEBA_PRESET = TargetPreset(
    name="Eneba",
    domain="eneba.com",
    category=TargetCategory.GAMING_MARKETPLACE,
    
    history_domains=[
        "eneba.com",
        "g2a.com",
        "kinguin.net",
        "steam.com",
        "reddit.com",
        "youtube.com",
        "twitch.tv",
        "discord.com",
        "github.com",
        "spotify.com",
    ],
    
    history_weight={
        "reddit.com": 20,
        "youtube.com": 25,
        "twitch.tv": 15,
        "steam.com": 10,
        "github.com": 12,
        "eneba.com": 8,
        "g2a.com": 5,
        "kinguin.net": 4,
        "discord.com": 15,
        "spotify.com": 20,
    },
    
    cookies=[
        {"domain": ".eneba.com", "name": "_ga", "age_days": 60},
        {"domain": ".eneba.com", "name": "locale", "value": "en-US"},
        {"domain": ".eneba.com", "name": "currency", "value": "USD"},
        {"domain": ".google.com", "name": "NID", "age_days": 90},
        {"domain": ".youtube.com", "name": "VISITOR_INFO1_LIVE", "age_days": 60},
    ],
    
    localstorage={
        "eneba.com": {
            "cart_viewed": "true",
            "currency": "USD",
            "region": "US",
            "cookie_consent": "accepted",
        },
        "youtube.com": {
            "yt-player-volume": '{"data":"{\\"volume\\":75,\\"muted\\":false}"}',
        },
    },
    
    recommended_hardware="macbook_m2_pro",
    recommended_archetype="student_developer",
    
    three_ds_rate=0.15,
    kyc_required=False,
    
    min_age_days=60,
    recommended_age_days=90,
    min_storage_mb=300,
    recommended_storage_mb=500,
    
    referrer_chain=[
        "google.com",
        "reddit.com/r/GameDeals",
        "eneba.com",
    ],
    
    warmup_searches=[
        "eneba reviews reddit",
        "cheap game keys",
        "eneba vs g2a",
        "steam key deals",
    ],
)


G2A_PRESET = TargetPreset(
    name="G2A",
    domain="g2a.com",
    category=TargetCategory.GAMING_MARKETPLACE,
    
    history_domains=[
        "g2a.com",
        "eneba.com",
        "kinguin.net",
        "steam.com",
        "reddit.com",
        "youtube.com",
        "twitch.tv",
        "discord.com",
    ],
    
    history_weight={
        "reddit.com": 20,
        "youtube.com": 25,
        "twitch.tv": 15,
        "steam.com": 12,
        "g2a.com": 10,
        "eneba.com": 5,
        "kinguin.net": 4,
        "discord.com": 15,
    },
    
    cookies=[
        {"domain": ".g2a.com", "name": "_ga", "age_days": 60},
        {"domain": ".g2a.com", "name": "currency", "value": "USD"},
        {"domain": ".google.com", "name": "NID", "age_days": 90},
    ],
    
    localstorage={
        "g2a.com": {
            "currency": "USD",
            "country": "US",
        },
    },
    
    recommended_hardware="windows_desktop_nvidia",
    recommended_archetype="gamer",
    
    three_ds_rate=0.20,
    kyc_required=False,
    
    min_age_days=60,
    recommended_age_days=90,
    
    referrer_chain=[
        "google.com",
        "reddit.com/r/GameDeals",
        "g2a.com",
    ],
    
    warmup_searches=[
        "g2a reviews",
        "cheap steam keys",
        "g2a legit",
    ],
)


KINGUIN_PRESET = TargetPreset(
    name="Kinguin",
    domain="kinguin.net",
    category=TargetCategory.GAMING_MARKETPLACE,
    
    history_domains=[
        "kinguin.net",
        "g2a.com",
        "eneba.com",
        "steam.com",
        "reddit.com",
        "youtube.com",
    ],
    
    recommended_hardware="macbook_m2_pro",
    recommended_archetype="student_developer",
    
    three_ds_rate=0.18,
    kyc_required=False,
    
    min_age_days=60,
    recommended_age_days=90,
    
    warmup_searches=[
        "kinguin reviews",
        "kinguin vs g2a",
    ],
)


# ═══════════════════════════════════════════════════════════════════════════
# GAMING PLATFORM TARGETS
# ═══════════════════════════════════════════════════════════════════════════

STEAM_PRESET = TargetPreset(
    name="Steam",
    domain="store.steampowered.com",
    category=TargetCategory.GAMING_PLATFORM,
    
    history_domains=[
        "store.steampowered.com",
        "steamcommunity.com",
        "reddit.com",
        "youtube.com",
        "twitch.tv",
        "discord.com",
        "pcgamer.com",
        "ign.com",
    ],
    
    history_weight={
        "reddit.com": 20,
        "youtube.com": 30,
        "twitch.tv": 20,
        "store.steampowered.com": 15,
        "steamcommunity.com": 10,
        "discord.com": 15,
        "pcgamer.com": 5,
        "ign.com": 5,
    },
    
    cookies=[
        {"domain": ".steampowered.com", "name": "steamLoginSecure", "age_days": 30},
        {"domain": ".steampowered.com", "name": "browserid", "age_days": 90},
    ],
    
    recommended_hardware="windows_gaming_rtx4080",
    recommended_archetype="gamer",
    
    three_ds_rate=0.25,
    kyc_required=False,
    
    min_age_days=90,
    recommended_age_days=120,
    
    warmup_searches=[
        "steam sale",
        "best steam games 2026",
        "steam deck games",
    ],
)


PLAYSTATION_PRESET = TargetPreset(
    name="PlayStation Store",
    domain="store.playstation.com",
    category=TargetCategory.GAMING_PLATFORM,
    
    history_domains=[
        "store.playstation.com",
        "playstation.com",
        "reddit.com",
        "youtube.com",
        "ign.com",
        "pushsquare.com",
    ],
    
    recommended_hardware="windows_desktop_nvidia",
    recommended_archetype="gamer",
    
    three_ds_rate=0.20,
    kyc_required=False,
    
    min_age_days=60,
    recommended_age_days=90,
    
    warmup_searches=[
        "ps5 games",
        "playstation store sale",
    ],
)


XBOX_PRESET = TargetPreset(
    name="Xbox Store",
    domain="xbox.com",
    category=TargetCategory.GAMING_PLATFORM,
    
    history_domains=[
        "xbox.com",
        "microsoft.com",
        "reddit.com",
        "youtube.com",
        "ign.com",
    ],
    
    recommended_hardware="windows_desktop_nvidia",
    recommended_archetype="gamer",
    
    three_ds_rate=0.20,
    kyc_required=False,
    
    min_age_days=60,
    recommended_age_days=90,
    
    warmup_searches=[
        "xbox game pass",
        "xbox series x games",
    ],
)


# ═══════════════════════════════════════════════════════════════════════════
# RETAIL TARGETS
# ═══════════════════════════════════════════════════════════════════════════

AMAZON_US_PRESET = TargetPreset(
    name="Amazon US",
    domain="amazon.com",
    category=TargetCategory.RETAIL,
    
    history_domains=[
        "amazon.com",
        "google.com",
        "reddit.com",
        "youtube.com",
        "facebook.com",
        "instagram.com",
        "twitter.com",
        "ebay.com",
        "walmart.com",
    ],
    
    history_weight={
        "google.com": 30,
        "youtube.com": 25,
        "reddit.com": 15,
        "amazon.com": 20,
        "facebook.com": 10,
        "instagram.com": 8,
        "twitter.com": 5,
        "ebay.com": 5,
        "walmart.com": 5,
    },
    
    cookies=[
        {"domain": ".amazon.com", "name": "session-id", "age_days": 90},
        {"domain": ".amazon.com", "name": "ubid-main", "age_days": 90},
        {"domain": ".amazon.com", "name": "x-main", "age_days": 60},
    ],
    
    localstorage={
        "amazon.com": {
            "csm-hit": "tb:s-{rand_hex12}|{rand_hex12}&t:{timestamp_ms}",
        },
    },
    
    recommended_hardware="windows_desktop_nvidia",
    recommended_archetype="casual_shopper",
    
    three_ds_rate=0.30,
    kyc_required=False,
    kyc_trigger="High-value orders (>$500), new accounts",
    
    min_age_days=90,
    recommended_age_days=120,
    min_storage_mb=400,
    recommended_storage_mb=600,
    
    referrer_chain=[
        "google.com",
        "amazon.com",
    ],
    
    warmup_searches=[
        "amazon deals",
        "amazon prime day",
        "amazon reviews",
    ],
)


AMAZON_UK_PRESET = TargetPreset(
    name="Amazon UK",
    domain="amazon.co.uk",
    category=TargetCategory.RETAIL,
    
    history_domains=[
        "amazon.co.uk",
        "google.co.uk",
        "reddit.com",
        "youtube.com",
        "bbc.co.uk",
        "ebay.co.uk",
    ],
    
    recommended_hardware="windows_desktop_nvidia",
    recommended_archetype="casual_shopper",
    
    three_ds_rate=0.35,
    kyc_required=False,
    
    min_age_days=90,
    recommended_age_days=120,
    
    warmup_searches=[
        "amazon uk deals",
        "amazon uk prime",
    ],
)


BESTBUY_PRESET = TargetPreset(
    name="Best Buy",
    domain="bestbuy.com",
    category=TargetCategory.ELECTRONICS,
    
    history_domains=[
        "bestbuy.com",
        "amazon.com",
        "newegg.com",
        "reddit.com",
        "youtube.com",
        "tomsguide.com",
        "cnet.com",
    ],
    
    recommended_hardware="windows_desktop_nvidia",
    recommended_archetype="professional",
    
    three_ds_rate=0.40,
    kyc_required=False,
    
    min_age_days=90,
    recommended_age_days=120,
    
    warmup_searches=[
        "best buy deals",
        "best buy reviews",
        "best buy vs amazon",
    ],
)


# ═══════════════════════════════════════════════════════════════════════════
# TARGET REGISTRY
# ═══════════════════════════════════════════════════════════════════════════

TARGET_PRESETS: Dict[str, TargetPreset] = {
    # Gaming Marketplaces
    "eneba": ENEBA_PRESET,
    "g2a": G2A_PRESET,
    "kinguin": KINGUIN_PRESET,
    
    # Gaming Platforms
    "steam": STEAM_PRESET,
    "playstation": PLAYSTATION_PRESET,
    "xbox": XBOX_PRESET,
    
    # Retail
    "amazon_us": AMAZON_US_PRESET,
    "amazon_uk": AMAZON_UK_PRESET,
    "bestbuy": BESTBUY_PRESET,
}


def get_target_preset(name: str) -> Optional[TargetPreset]:
    """Get target preset by name (case-insensitive)"""
    return TARGET_PRESETS.get(name.lower().replace(" ", "_").replace("-", "_"))


def list_targets() -> List[Dict[str, Any]]:
    """List all available targets for GUI dropdown"""
    return [
        {
            "id": key,
            "name": preset.name,
            "domain": preset.domain,
            "category": preset.category.value,
            "3ds_rate": preset.three_ds_rate,
            "kyc_required": preset.kyc_required,
            "min_age_days": preset.min_age_days,
        }
        for key, preset in TARGET_PRESETS.items()
    ]


def get_targets_by_category(category: TargetCategory) -> List[TargetPreset]:
    """Get all targets in a category"""
    return [p for p in TARGET_PRESETS.values() if p.category == category]


# ═══════════════════════════════════════════════════════════════════════════
# AUTO-MAPPER: Generate Genesis presets from target_intelligence entries
# Bridges GAP between 9 manual presets and 31+ intelligence targets
# ═══════════════════════════════════════════════════════════════════════════

# Category-to-demographic mapping for auto-generated presets
_CATEGORY_DEFAULTS = {
    "gaming": {
        "history_weight": {"youtube.com": 0.30, "twitch.tv": 0.20, "reddit.com": 0.15,
                           "discord.com": 0.10, "store.steampowered.com": 0.10},
        "hardware": "windows_gaming_rtx4080",
        "persona_age_range": (18, 35),
        "min_age_days": 60,
        "recommended_age_days": 120,
        "min_storage_mb": 200,
    },
    "digital_goods": {
        "history_weight": {"google.com": 0.25, "youtube.com": 0.20, "reddit.com": 0.15,
                           "amazon.com": 0.10, "ebay.com": 0.05},
        "hardware": "windows_desktop_i7",
        "persona_age_range": (20, 45),
        "min_age_days": 30,
        "recommended_age_days": 90,
        "min_storage_mb": 150,
    },
    "gift_cards": {
        "history_weight": {"google.com": 0.25, "amazon.com": 0.15, "walmart.com": 0.10,
                           "target.com": 0.10, "reddit.com": 0.10},
        "hardware": "windows_desktop_i5",
        "persona_age_range": (25, 55),
        "min_age_days": 45,
        "recommended_age_days": 90,
        "min_storage_mb": 200,
    },
    "crypto": {
        "history_weight": {"google.com": 0.20, "coinmarketcap.com": 0.15,
                           "reddit.com": 0.15, "twitter.com": 0.10, "youtube.com": 0.10},
        "hardware": "windows_desktop_i7",
        "persona_age_range": (20, 40),
        "min_age_days": 30,
        "recommended_age_days": 60,
        "min_storage_mb": 100,
    },
    "retail": {
        "history_weight": {"google.com": 0.25, "amazon.com": 0.15, "youtube.com": 0.10,
                           "reddit.com": 0.10, "walmart.com": 0.05},
        "hardware": "windows_desktop_i5",
        "persona_age_range": (25, 60),
        "min_age_days": 90,
        "recommended_age_days": 180,
        "min_storage_mb": 400,
    },
    "ads": {
        "history_weight": {"google.com": 0.25, "facebook.com": 0.15, "youtube.com": 0.10,
                           "linkedin.com": 0.10, "twitter.com": 0.05},
        "hardware": "macbook_m2_pro",
        "persona_age_range": (22, 45),
        "min_age_days": 60,
        "recommended_age_days": 120,
        "min_storage_mb": 300,
    },
}

# Map intelligence target categories to preset defaults
_INTEL_CATEGORY_MAP = {
    "gaming": "gaming", "grey_market": "gaming", "authorized_retailer": "gaming",
    "gift_card": "gift_cards", "crypto": "crypto", "retail": "retail",
    "ads": "ads", "digital": "digital_goods", "regional": "gaming",
    "subscription": "digital_goods", "travel": "retail", "fashion": "retail",
    "food_delivery": "retail", "electronics": "retail", "misc": "digital_goods",
}


def generate_preset_from_intel(target_name: str) -> Optional[TargetPreset]:
    """
    Auto-generate a Genesis-compatible TargetPreset from target_intelligence data.
    
    Bridges the gap between the 31+ intelligence targets and the Genesis Engine
    by generating reasonable profile forging parameters based on the target's
    category, fraud engine, and security posture.
    """
    try:
        from target_intelligence import TARGETS, TargetIntelligence
    except ImportError:
        return None
    
    intel = TARGETS.get(target_name.lower())
    if not intel:
        return None
    
    # Determine category defaults
    cat_key = "digital_goods"  # fallback
    for note in (intel.notes or []):
        note_lower = note.lower()
        for keyword, mapped in _INTEL_CATEGORY_MAP.items():
            if keyword in note_lower:
                cat_key = mapped
                break
    
    # Check friction level for category hints
    domain_lower = intel.domain.lower()
    if any(g in domain_lower for g in ["steam", "xbox", "playstation", "g2a", "eneba", "kinguin",
                                        "gamivo", "cdkeys", "gamesplanet", "fanatical", "humble"]):
        cat_key = "gaming"
    elif any(a in domain_lower for a in ["ads.google", "ads.pinterest", "business.facebook"]):
        cat_key = "ads"
    elif any(c in domain_lower for c in ["bitrefill", "coinsbee"]):
        cat_key = "crypto"
    elif any(r in domain_lower for r in ["amazon", "bestbuy", "walmart", "target.com"]):
        cat_key = "retail"
    elif any(gc in domain_lower for gc in ["cardcash", "raise.com"]):
        cat_key = "gift_cards"
    
    defaults = _CATEGORY_DEFAULTS.get(cat_key, _CATEGORY_DEFAULTS["digital_goods"])
    
    # Build warmup searches from domain
    domain_short = intel.domain.split(".")[0]
    warmup_searches = [
        f"{intel.name} reviews",
        f"{intel.name} deals",
        f"best {cat_key.replace('_', ' ')} sites",
    ]
    
    # Build referrer chain
    referrer_chain = ["google.com", "reddit.com", intel.domain]
    
    # V7.5 FIX: Map category to valid TargetCategory enum values
    cat_enum_map = {
        "gaming": TargetCategory.GAMING_MARKETPLACE,
        "retail": TargetCategory.RETAIL,
        "crypto": TargetCategory.CRYPTO,
        "gift_cards": TargetCategory.DIGITAL_GOODS,
        "digital_goods": TargetCategory.DIGITAL_GOODS,
        "ads": TargetCategory.SUBSCRIPTION,
    }
    
    # V7.5 FIX: Build history_domains from weight keys + target domain
    history_domains = [intel.domain] + list(defaults["history_weight"].keys())
    
    preset = TargetPreset(
        name=intel.name,
        domain=intel.domain,
        category=cat_enum_map.get(cat_key, TargetCategory.DIGITAL_GOODS),
        three_ds_rate=intel.three_ds_rate,
        recommended_hardware=defaults["hardware"],
        history_domains=history_domains,
        history_weight=defaults["history_weight"],
        min_age_days=defaults["min_age_days"],
        recommended_age_days=defaults["recommended_age_days"],
        min_storage_mb=defaults["min_storage_mb"],
        warmup_searches=warmup_searches,
        referrer_chain=referrer_chain,
    )
    return preset


def get_target_preset_auto(name: str) -> Optional[TargetPreset]:
    """
    Get target preset by name, falling back to:
    1. Manual preset (hardcoded)
    2. Auto-generation from target_intelligence
    3. Ollama-powered dynamic generation for ANY domain
    """
    # Try manual preset first
    preset = get_target_preset(name)
    if preset:
        return preset
    
    # Auto-generate from intelligence data
    preset = generate_preset_from_intel(name)
    if preset:
        return preset
    
    # Ollama-powered generation for unknown domains
    return _generate_preset_via_ollama(name)


def _generate_preset_via_ollama(name_or_domain: str) -> Optional[TargetPreset]:
    """
    Generate a target preset for ANY domain using Ollama.
    Falls back to None if Ollama is unavailable.
    """
    try:
        from dynamic_data import generate_target_preset as ollama_gen, is_ollama_available
        if not is_ollama_available():
            return None
        
        # If name looks like a domain, use it directly; otherwise try to resolve
        domain = name_or_domain
        if "." not in domain:
            domain = f"{domain}.com"
        
        result = ollama_gen(domain)
        if not result:
            return None
        
        # Convert Ollama result dict to TargetPreset
        cat_map = {
            "gaming_marketplace": TargetCategory.GAMING_MARKETPLACE,
            "retail": TargetCategory.RETAIL,
            "electronics": TargetCategory.ELECTRONICS,
            "gaming_platform": TargetCategory.GAMING_PLATFORM,
            "digital_goods": TargetCategory.DIGITAL_GOODS,
            "subscription": TargetCategory.SUBSCRIPTION,
            "crypto": TargetCategory.CRYPTO,
            "financial": TargetCategory.FINANCIAL,
        }
        
        preset = TargetPreset(
            name=result.get("name", domain.split(".")[0].title()),
            domain=domain,
            category=cat_map.get(result.get("category", ""), TargetCategory.DIGITAL_GOODS),
            history_domains=result.get("history_domains", [domain, "google.com", "youtube.com"]),
            history_weight=result.get("history_weight", {}),
            cookies=[c for c in result.get("cookies", []) if isinstance(c, dict)],
            localstorage=result.get("localstorage", {}),
            recommended_archetype=result.get("recommended_archetype", "casual_shopper"),
            three_ds_rate=float(result.get("three_ds_rate", 0.25)),
            min_age_days=int(result.get("min_age_days", 60)),
            recommended_age_days=int(result.get("recommended_age_days", 90)),
            warmup_searches=result.get("warmup_searches", [f"{domain} reviews"]),
            referrer_chain=result.get("referrer_chain", ["google.com", domain]),
        )
        
        # Cache it in TARGET_PRESETS so subsequent lookups are instant
        key = name_or_domain.lower().replace(" ", "_").replace("-", "_").replace(".", "_")
        TARGET_PRESETS[key] = preset
        
        return preset
    except ImportError:
        return None
    except Exception:
        return None


def list_all_targets() -> List[Dict[str, Any]]:
    """
    List ALL available targets, including both manual presets and
    auto-generated presets from target_intelligence.
    """
    all_targets = list_targets()  # manual presets
    manual_ids = {t["id"] for t in all_targets}
    
    try:
        from target_intelligence import TARGETS
        for key, intel in TARGETS.items():
            if key not in manual_ids:
                all_targets.append({
                    "id": key,
                    "name": intel.name,
                    "domain": intel.domain,
                    "category": "auto",
                    "3ds_rate": intel.three_ds_rate,
                    "kyc_required": getattr(intel, 'kyc_required', False),
                    "min_age_days": 60,
                    "source": "auto_mapped",
                })
    except ImportError:
        pass
    
    return all_targets


if __name__ == "__main__":
    print("TITAN V7.0 Target Presets")
    print("=" * 50)
    
    for target in list_targets():
        print(f"\n{target['name']} ({target['domain']})")
        print(f"  Category: {target['category']}")
        print(f"  3DS Risk: {target['3ds_rate']*100:.0f}%")
        print(f"  KYC Required: {'Yes' if target['kyc_required'] else 'No'}")
        print(f"  Min Age: {target['min_age_days']} days")


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 P0 CRITICAL ENHANCEMENTS - Advanced Preset Management
# ═══════════════════════════════════════════════════════════════════════════════

import threading
import time
import json
import hashlib
import logging
import copy
from collections import defaultdict

logger = logging.getLogger("TITAN-PRESETS")


@dataclass
class PresetVersion:
    """Preset version information"""
    version: str
    created_at: float
    changes: List[str]
    checksum: str


@dataclass
class ValidationResult:
    """Preset validation result"""
    valid: bool
    errors: List[str]
    warnings: List[str]
    suggestions: List[str]


@dataclass
class MigrationRecord:
    """Preset migration record"""
    preset_name: str
    from_version: str
    to_version: str
    migrated_at: float
    changes_applied: List[str]
    success: bool


class PresetVersionManager:
    """
    V7.6 P0: Version and track preset changes.
    
    Features:
    - Semantic versioning for presets
    - Change history tracking
    - Checksum verification
    - Rollback support
    """
    
    VERSION = "7.6.0"
    
    def __init__(self):
        self._versions: Dict[str, List[PresetVersion]] = defaultdict(list)
        self._lock = threading.Lock()
        self.logger = logging.getLogger("TITAN-PRESET-VERSION")
    
    def compute_checksum(self, preset: TargetPreset) -> str:
        """Compute checksum for a preset"""
        data = {
            "name": preset.name,
            "domain": preset.domain,
            "category": preset.category.value,
            "three_ds_rate": preset.three_ds_rate,
            "min_age_days": preset.min_age_days,
            "history_domains": sorted(preset.history_domains),
        }
        json_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()[:16]
    
    def register_version(
        self,
        preset_name: str,
        preset: TargetPreset,
        version: str = None,
        changes: List[str] = None,
    ):
        """Register a new version of a preset"""
        with self._lock:
            if version is None:
                existing = self._versions.get(preset_name, [])
                if existing:
                    last = existing[-1].version
                    parts = last.split(".")
                    parts[-1] = str(int(parts[-1]) + 1)
                    version = ".".join(parts)
                else:
                    version = "1.0.0"
            
            pv = PresetVersion(
                version=version,
                created_at=time.time(),
                changes=changes or ["Initial version"],
                checksum=self.compute_checksum(preset),
            )
            
            self._versions[preset_name].append(pv)
            self.logger.info(f"Registered preset {preset_name} v{version}")
    
    def get_version_history(self, preset_name: str) -> List[Dict]:
        """Get version history for a preset"""
        with self._lock:
            versions = self._versions.get(preset_name, [])
            return [
                {
                    "version": v.version,
                    "created_at": v.created_at,
                    "changes": v.changes,
                    "checksum": v.checksum,
                }
                for v in versions
            ]
    
    def get_latest_version(self, preset_name: str) -> Optional[str]:
        """Get latest version string for a preset"""
        with self._lock:
            versions = self._versions.get(preset_name, [])
            return versions[-1].version if versions else None
    
    def verify_checksum(self, preset_name: str, preset: TargetPreset) -> Dict:
        """Verify preset matches its registered checksum"""
        with self._lock:
            versions = self._versions.get(preset_name, [])
            if not versions:
                return {"verified": False, "error": "No versions registered"}
            
            current_checksum = self.compute_checksum(preset)
            latest = versions[-1]
            
            return {
                "verified": current_checksum == latest.checksum,
                "current_checksum": current_checksum,
                "expected_checksum": latest.checksum,
                "version": latest.version,
            }


class PresetValidator:
    """
    V7.6 P0: Validate preset configurations.
    
    Features:
    - Schema validation
    - Cross-field consistency checks
    - Domain verification
    - Security requirement validation
    """
    
    # Required fields for a valid preset
    REQUIRED_FIELDS = ["name", "domain", "category"]
    
    # Reasonable ranges for numeric fields
    RANGES = {
        "three_ds_rate": (0.0, 1.0),
        "min_age_days": (0, 365),
        "recommended_age_days": (0, 730),
        "min_storage_mb": (0, 10000),
        "recommended_storage_mb": (0, 50000),
    }
    
    def __init__(self):
        self._validation_cache: Dict[str, ValidationResult] = {}
        self._lock = threading.Lock()
        self.logger = logging.getLogger("TITAN-PRESET-VALIDATOR")
    
    def validate(self, preset: TargetPreset) -> ValidationResult:
        """Validate a preset configuration"""
        errors = []
        warnings = []
        suggestions = []
        
        # Required field checks
        for field in self.REQUIRED_FIELDS:
            if not getattr(preset, field, None):
                errors.append(f"Missing required field: {field}")
        
        # Domain validation
        if preset.domain:
            if not "." in preset.domain:
                errors.append(f"Invalid domain format: {preset.domain}")
            if preset.domain.startswith("http"):
                warnings.append("Domain should not include protocol (http/https)")
        
        # Range validation
        for field, (min_val, max_val) in self.RANGES.items():
            value = getattr(preset, field, None)
            if value is not None:
                if value < min_val or value > max_val:
                    errors.append(f"{field} out of range: {value} (expected {min_val}-{max_val})")
        
        # Consistency checks
        if preset.recommended_age_days < preset.min_age_days:
            warnings.append("recommended_age_days should be >= min_age_days")
        
        if preset.recommended_storage_mb < preset.min_storage_mb:
            warnings.append("recommended_storage_mb should be >= min_storage_mb")
        
        # History domains validation
        if not preset.history_domains:
            warnings.append("No history_domains specified - profile may be thin")
        else:
            if preset.domain not in preset.history_domains:
                suggestions.append(f"Consider adding {preset.domain} to history_domains")
            
            if len(preset.history_domains) < 5:
                suggestions.append("Consider adding more history_domains for realistic profile")
        
        # Cookie validation
        if preset.cookies:
            for i, cookie in enumerate(preset.cookies):
                if not isinstance(cookie, dict):
                    errors.append(f"Cookie {i} is not a dictionary")
                elif "domain" not in cookie or "name" not in cookie:
                    warnings.append(f"Cookie {i} missing 'domain' or 'name' fields")
        
        # Category-specific validation
        if preset.category == TargetCategory.GAMING_MARKETPLACE:
            gaming_domains = ["steam", "twitch", "discord", "youtube"]
            has_gaming = any(
                any(g in d.lower() for g in gaming_domains)
                for d in preset.history_domains
            )
            if not has_gaming:
                suggestions.append("Gaming marketplace preset should include gaming-related history domains")
        
        # Security level suggestions
        if preset.three_ds_rate < 0.1:
            suggestions.append("Very low 3DS rate - consider verifying this is accurate")
        elif preset.three_ds_rate > 0.7:
            suggestions.append("High 3DS rate - ensure profile has strong 3DS bypass capabilities")
        
        result = ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
        )
        
        # Cache result
        with self._lock:
            self._validation_cache[preset.name] = result
        
        return result
    
    def validate_all(self) -> Dict[str, ValidationResult]:
        """Validate all registered presets"""
        results = {}
        for key, preset in TARGET_PRESETS.items():
            results[key] = self.validate(preset)
        return results
    
    def get_invalid_presets(self) -> List[str]:
        """Get list of invalid preset names"""
        results = self.validate_all()
        return [name for name, result in results.items() if not result.valid]


class PresetMigrator:
    """
    V7.6 P0: Migrate presets between versions.
    
    Features:
    - Version compatibility checks
    - Field migration transformations
    - Data preservation
    - Migration rollback
    """
    
    # Migration rules: version -> list of (field, transformation)
    MIGRATIONS = {
        "7.5.0": [
            ("history_domains", lambda v: v if v else []),
            ("warmup_searches", lambda v: v if v else []),
        ],
        "7.6.0": [
            ("min_storage_mb", lambda v: max(v or 0, 200)),
            ("recommended_storage_mb", lambda v: max(v or 0, 400)),
        ],
    }
    
    def __init__(self):
        self._migrations: List[MigrationRecord] = []
        self._backups: Dict[str, TargetPreset] = {}
        self._lock = threading.Lock()
        self.logger = logging.getLogger("TITAN-PRESET-MIGRATOR")
    
    def migrate(
        self,
        preset: TargetPreset,
        from_version: str,
        to_version: str,
    ) -> TargetPreset:
        """Migrate a preset from one version to another"""
        with self._lock:
            # Backup original
            self._backups[preset.name] = copy.deepcopy(preset)
            
            changes_applied = []
            
            # Apply migrations for each version
            versions = sorted(self.MIGRATIONS.keys())
            for version in versions:
                if version > from_version and version <= to_version:
                    for field, transform in self.MIGRATIONS[version]:
                        old_value = getattr(preset, field, None)
                        new_value = transform(old_value)
                        if old_value != new_value:
                            setattr(preset, field, new_value)
                            changes_applied.append(f"{field}: {old_value} -> {new_value}")
            
            record = MigrationRecord(
                preset_name=preset.name,
                from_version=from_version,
                to_version=to_version,
                migrated_at=time.time(),
                changes_applied=changes_applied,
                success=True,
            )
            self._migrations.append(record)
            
            self.logger.info(
                f"Migrated {preset.name} from {from_version} to {to_version}: "
                f"{len(changes_applied)} changes"
            )
            
            return preset
    
    def rollback(self, preset_name: str) -> Optional[TargetPreset]:
        """Rollback a preset to its pre-migration state"""
        with self._lock:
            return self._backups.get(preset_name)
    
    def get_migration_history(self, preset_name: str = None) -> List[Dict]:
        """Get migration history"""
        with self._lock:
            migrations = self._migrations
            if preset_name:
                migrations = [m for m in migrations if m.preset_name == preset_name]
            
            return [
                {
                    "preset": m.preset_name,
                    "from": m.from_version,
                    "to": m.to_version,
                    "migrated_at": m.migrated_at,
                    "changes": m.changes_applied,
                    "success": m.success,
                }
                for m in migrations
            ]
    
    def migrate_all(self, to_version: str = "7.6.0") -> Dict[str, bool]:
        """Migrate all presets to target version"""
        results = {}
        
        for key, preset in TARGET_PRESETS.items():
            try:
                self.migrate(preset, "7.0.0", to_version)
                results[key] = True
            except Exception as e:
                self.logger.error(f"Failed to migrate {key}: {e}")
                results[key] = False
        
        return results


class DynamicPresetBuilder:
    """
    V7.6 P0: Build presets dynamically based on live data.
    
    Features:
    - Domain analysis for preset generation
    - Competitive analysis integration
    - Real-time 3DS rate estimation
    - Smart history domain selection
    """
    
    # Common history domains by category
    CATEGORY_HISTORY = {
        TargetCategory.GAMING_MARKETPLACE: [
            "youtube.com", "twitch.tv", "discord.com", "reddit.com",
            "steam.com", "steamcommunity.com", "gamefaqs.com",
        ],
        TargetCategory.RETAIL: [
            "google.com", "amazon.com", "ebay.com", "youtube.com",
            "reddit.com", "facebook.com", "instagram.com",
        ],
        TargetCategory.ELECTRONICS: [
            "google.com", "youtube.com", "reddit.com", "tomshardware.com",
            "amazon.com", "newegg.com", "rtings.com",
        ],
        TargetCategory.CRYPTO: [
            "google.com", "coinmarketcap.com", "coingecko.com",
            "reddit.com", "twitter.com", "youtube.com",
        ],
        TargetCategory.DIGITAL_GOODS: [
            "google.com", "youtube.com", "reddit.com", "twitter.com",
            "facebook.com", "amazon.com",
        ],
    }
    
    # 3DS rate estimates by category
    CATEGORY_3DS_ESTIMATES = {
        TargetCategory.GAMING_MARKETPLACE: 0.20,
        TargetCategory.RETAIL: 0.35,
        TargetCategory.ELECTRONICS: 0.45,
        TargetCategory.GAMING_PLATFORM: 0.25,
        TargetCategory.DIGITAL_GOODS: 0.20,
        TargetCategory.SUBSCRIPTION: 0.30,
        TargetCategory.CRYPTO: 0.05,
        TargetCategory.FINANCIAL: 0.60,
    }
    
    def __init__(self):
        self._built_presets: Dict[str, TargetPreset] = {}
        self._build_stats = {
            "total_built": 0,
            "from_intel": 0,
            "from_analysis": 0,
        }
        self._lock = threading.Lock()
        self.logger = logging.getLogger("TITAN-DYNAMIC-BUILDER")
    
    def build(
        self,
        domain: str,
        name: str = None,
        category: TargetCategory = None,
        use_intel: bool = True,
    ) -> TargetPreset:
        """Build a preset dynamically for a domain"""
        with self._lock:
            # Check if already built
            if domain in self._built_presets:
                return self._built_presets[domain]
        
        # Try to get intel first
        intel_preset = None
        if use_intel:
            intel_preset = generate_preset_from_intel(domain.split(".")[0])
        
        if intel_preset:
            with self._lock:
                self._built_presets[domain] = intel_preset
                self._build_stats["total_built"] += 1
                self._build_stats["from_intel"] += 1
            return intel_preset
        
        # Build from scratch
        if name is None:
            name = domain.split(".")[0].title()
        
        if category is None:
            category = self._guess_category(domain)
        
        # Get category-appropriate history
        history = self.CATEGORY_HISTORY.get(category, self.CATEGORY_HISTORY[TargetCategory.DIGITAL_GOODS])
        
        # Estimate 3DS rate
        three_ds_rate = self.CATEGORY_3DS_ESTIMATES.get(category, 0.25)
        
        # Build history weights
        history_weight = {}
        for i, h in enumerate(history):
            history_weight[h] = max(5, 25 - (i * 3))
        
        preset = TargetPreset(
            name=name,
            domain=domain,
            category=category,
            history_domains=[domain] + history[:8],
            history_weight=history_weight,
            cookies=[
                {"domain": f".{domain}", "name": "_ga", "age_days": 60},
            ],
            localstorage={
                domain: {
                    "visited": "true",
                    "consent": "accepted",
                },
            },
            recommended_hardware="windows_desktop_nvidia",
            recommended_archetype="casual_shopper",
            three_ds_rate=three_ds_rate,
            kyc_required=False,
            min_age_days=60,
            recommended_age_days=90,
            min_storage_mb=300,
            recommended_storage_mb=500,
            referrer_chain=["google.com", "reddit.com", domain],
            warmup_searches=[
                f"{name} reviews",
                f"{name} deals",
                f"best {category.value.replace('_', ' ')} sites",
            ],
        )
        
        with self._lock:
            self._built_presets[domain] = preset
            self._build_stats["total_built"] += 1
            self._build_stats["from_analysis"] += 1
        
        return preset
    
    def _guess_category(self, domain: str) -> TargetCategory:
        """Guess category based on domain"""
        domain_lower = domain.lower()
        
        gaming_keywords = ["game", "steam", "xbox", "playstation", "twitch", "g2a", "eneba"]
        crypto_keywords = ["coin", "crypto", "bit", "exchange", "wallet"]
        retail_keywords = ["shop", "store", "buy", "market", "amazon", "ebay"]
        electronics_keywords = ["tech", "electronic", "computer", "newegg", "bestbuy"]
        
        for kw in gaming_keywords:
            if kw in domain_lower:
                return TargetCategory.GAMING_MARKETPLACE
        
        for kw in crypto_keywords:
            if kw in domain_lower:
                return TargetCategory.CRYPTO
        
        for kw in electronics_keywords:
            if kw in domain_lower:
                return TargetCategory.ELECTRONICS
        
        for kw in retail_keywords:
            if kw in domain_lower:
                return TargetCategory.RETAIL
        
        return TargetCategory.DIGITAL_GOODS
    
    def get_build_stats(self) -> Dict:
        """Get build statistics"""
        with self._lock:
            return dict(self._build_stats)
    
    def clear_cache(self):
        """Clear built preset cache"""
        with self._lock:
            self._built_presets.clear()


# ═══════════════════════════════════════════════════════════════════════════
# V7.6 SINGLETON INSTANCES
# ═══════════════════════════════════════════════════════════════════════════

_preset_version_manager: Optional[PresetVersionManager] = None
_preset_validator: Optional[PresetValidator] = None
_preset_migrator: Optional[PresetMigrator] = None
_dynamic_preset_builder: Optional[DynamicPresetBuilder] = None


def get_preset_version_manager() -> PresetVersionManager:
    """Get global preset version manager"""
    global _preset_version_manager
    if _preset_version_manager is None:
        _preset_version_manager = PresetVersionManager()
    return _preset_version_manager


def get_preset_validator() -> PresetValidator:
    """Get global preset validator"""
    global _preset_validator
    if _preset_validator is None:
        _preset_validator = PresetValidator()
    return _preset_validator


def get_preset_migrator() -> PresetMigrator:
    """Get global preset migrator"""
    global _preset_migrator
    if _preset_migrator is None:
        _preset_migrator = PresetMigrator()
    return _preset_migrator


def get_dynamic_preset_builder() -> DynamicPresetBuilder:
    """Get global dynamic preset builder"""
    global _dynamic_preset_builder
    if _dynamic_preset_builder is None:
        _dynamic_preset_builder = DynamicPresetBuilder()
    return _dynamic_preset_builder
