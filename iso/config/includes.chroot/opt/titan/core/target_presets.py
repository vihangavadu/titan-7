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


if __name__ == "__main__":
    print("TITAN V7.0 Target Presets")
    print("=" * 50)
    
    for target in list_targets():
        print(f"\n{target['name']} ({target['domain']})")
        print(f"  Category: {target['category']}")
        print(f"  3DS Risk: {target['3ds_rate']*100:.0f}%")
        print(f"  KYC Required: {'Yes' if target['kyc_required'] else 'No'}")
        print(f"  Min Age: {target['min_age_days']} days")
