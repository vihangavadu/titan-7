#!/usr/bin/env python3
"""
TITAN OS — Persona Enrichment Engine
═══════════════════════════════════════════════════════════════════════════

PROBLEM: Generic bank decline when persona purchase history doesn't match
         the target item (e.g., "kitchen shopper" buying gaming gift cards).

SOLUTION: AI-powered demographic profiling that predicts realistic purchase
          patterns from name/address/email/age/occupation and validates
          purchase coherence BEFORE the operation.

Architecture:
    1. DemographicProfiler — Extract signals from name/email/address/age
    2. PurchasePatternPredictor — Predict likely purchases from demographics
    3. CoherenceValidator — Block out-of-pattern purchases before they fail
    4. OSINTEnricher — Optional self-hosted OSINT integration

Self-Hosted Tools Integration (Optional):
    - Sherlock (GitHub username → social profiles)
    - Holehe (email → registered accounts)
    - Maigret (username → 2500+ sites)
    - theHarvester (email → public data sources)
    - Photon (web scraper for person data)

Version: 8.1.0
Author: TITAN Development Team
"""

import re
import json
import logging
import hashlib
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta

logger = logging.getLogger("titan.persona_enrichment")


# ═══════════════════════════════════════════════════════════════════════════
# DEMOGRAPHIC SIGNALS
# ═══════════════════════════════════════════════════════════════════════════

class AgeGroup(Enum):
    """Age-based demographic segments"""
    GEN_Z = "gen_z"           # 18-27
    MILLENNIAL = "millennial"  # 28-43
    GEN_X = "gen_x"           # 44-59
    BOOMER = "boomer"         # 60-78
    SILENT = "silent"         # 79+


class OccupationCategory(Enum):
    """Occupation-based behavioral segments"""
    TECH = "tech"                    # Software, IT, Engineering
    HEALTHCARE = "healthcare"        # Medical, Nursing, Pharma
    EDUCATION = "education"          # Teachers, Professors
    FINANCE = "finance"              # Banking, Accounting, Insurance
    RETAIL = "retail"                # Sales, Customer Service
    TRADES = "trades"                # Construction, Electrician, Plumber
    CREATIVE = "creative"            # Design, Marketing, Media
    HOSPITALITY = "hospitality"      # Restaurant, Hotel, Tourism
    GOVERNMENT = "government"        # Public Sector, Military
    RETIRED = "retired"              # No active occupation
    STUDENT = "student"              # College, University
    UNEMPLOYED = "unemployed"        # Job seeking


class IncomeLevel(Enum):
    """Income-based purchasing power"""
    LOW = "low"           # <$35k
    LOWER_MID = "lower_mid"  # $35k-$60k
    MIDDLE = "middle"     # $60k-$100k
    UPPER_MID = "upper_mid"  # $100k-$200k
    HIGH = "high"         # $200k+


@dataclass
class DemographicProfile:
    """Extracted demographic signals from persona data"""
    # Core identity
    full_name: str
    email: str
    age: int
    gender: Optional[str] = None  # M/F/Other
    
    # Location signals
    city: str = ""
    state: str = ""
    country: str = "US"
    zip_code: str = ""
    
    # Behavioral signals
    age_group: AgeGroup = AgeGroup.MILLENNIAL
    occupation_category: OccupationCategory = OccupationCategory.UNEMPLOYED
    income_level: IncomeLevel = IncomeLevel.MIDDLE
    
    # Inferred interests (from email domain, name patterns, etc.)
    interests: List[str] = field(default_factory=list)
    tech_savvy: float = 0.5  # 0.0-1.0
    online_shopper: float = 0.5  # 0.0-1.0


# ═══════════════════════════════════════════════════════════════════════════
# PURCHASE PATTERN PREDICTION
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class PurchaseCategory:
    """A category of purchases with likelihood score"""
    name: str
    likelihood: float  # 0.0-1.0
    typical_merchants: List[str]
    typical_items: List[str]
    avg_amount_range: Tuple[float, float]


# Demographic → Purchase Pattern Mapping
# Based on consumer behavior research and e-commerce analytics
DEMOGRAPHIC_PURCHASE_PATTERNS = {
    # ── AGE GROUP PATTERNS ──────────────────────────────────────────
    AgeGroup.GEN_Z: {
        "gaming": 0.75,
        "fashion": 0.70,
        "tech_gadgets": 0.65,
        "streaming": 0.80,
        "food_delivery": 0.75,
        "beauty": 0.60,
        "home_goods": 0.20,
        "automotive": 0.15,
        "health": 0.25,
    },
    AgeGroup.MILLENNIAL: {
        "gaming": 0.55,
        "fashion": 0.65,
        "tech_gadgets": 0.70,
        "streaming": 0.75,
        "food_delivery": 0.70,
        "home_goods": 0.60,
        "baby_kids": 0.45,
        "fitness": 0.55,
        "travel": 0.50,
    },
    AgeGroup.GEN_X: {
        "home_goods": 0.75,
        "automotive": 0.60,
        "health": 0.65,
        "garden": 0.50,
        "tools": 0.55,
        "books": 0.50,
        "fashion": 0.45,
        "tech_gadgets": 0.50,
        "gaming": 0.25,
    },
    AgeGroup.BOOMER: {
        "health": 0.80,
        "home_goods": 0.70,
        "garden": 0.65,
        "books": 0.60,
        "automotive": 0.50,
        "travel": 0.55,
        "pharmacy": 0.75,
        "gaming": 0.10,
        "fashion": 0.35,
    },
    
    # ── OCCUPATION PATTERNS ─────────────────────────────────────────
    OccupationCategory.TECH: {
        "tech_gadgets": 0.85,
        "gaming": 0.70,
        "software": 0.80,
        "books": 0.60,
        "streaming": 0.75,
        "food_delivery": 0.65,
    },
    OccupationCategory.HEALTHCARE: {
        "health": 0.75,
        "fitness": 0.65,
        "books": 0.55,
        "home_goods": 0.60,
        "pharmacy": 0.70,
    },
    OccupationCategory.STUDENT: {
        "gaming": 0.70,
        "food_delivery": 0.80,
        "streaming": 0.85,
        "books": 0.65,
        "tech_gadgets": 0.60,
        "fashion": 0.65,
    },
    OccupationCategory.CREATIVE: {
        "fashion": 0.75,
        "tech_gadgets": 0.70,
        "books": 0.65,
        "streaming": 0.70,
        "home_decor": 0.60,
    },
    OccupationCategory.RETIRED: {
        "health": 0.85,
        "pharmacy": 0.80,
        "garden": 0.70,
        "books": 0.65,
        "home_goods": 0.70,
        "travel": 0.50,
    },
}

# Purchase Category → Merchant/Item Definitions
PURCHASE_CATEGORY_DEFINITIONS = {
    "gaming": PurchaseCategory(
        name="Gaming",
        likelihood=0.0,  # Will be set dynamically
        typical_merchants=["steampowered.com", "g2a.com", "eneba.com", "gamestop.com", "bestbuy.com"],
        typical_items=["Game Key", "Gift Card", "Gaming Mouse", "Headset", "Controller"],
        avg_amount_range=(15.0, 80.0),
    ),
    "tech_gadgets": PurchaseCategory(
        name="Tech Gadgets",
        likelihood=0.0,
        typical_merchants=["amazon.com", "bestbuy.com", "newegg.com", "bhphotovideo.com"],
        typical_items=["USB Cable", "Phone Case", "Wireless Charger", "Bluetooth Speaker", "Webcam"],
        avg_amount_range=(20.0, 150.0),
    ),
    "home_goods": PurchaseCategory(
        name="Home Goods",
        likelihood=0.0,
        typical_merchants=["amazon.com", "target.com", "wayfair.com", "homedepot.com", "walmart.com"],
        typical_items=["Kitchen Utensils", "Storage Bins", "Bedding", "Towels", "Small Appliances"],
        avg_amount_range=(25.0, 120.0),
    ),
    "fashion": PurchaseCategory(
        name="Fashion",
        likelihood=0.0,
        typical_merchants=["amazon.com", "target.com", "macys.com", "nordstrom.com", "zappos.com"],
        typical_items=["T-Shirt", "Jeans", "Sneakers", "Jacket", "Accessories"],
        avg_amount_range=(30.0, 150.0),
    ),
    "food_delivery": PurchaseCategory(
        name="Food Delivery",
        likelihood=0.0,
        typical_merchants=["ubereats.com", "doordash.com", "grubhub.com", "postmates.com"],
        typical_items=["Restaurant Order", "Grocery Delivery", "Fast Food"],
        avg_amount_range=(15.0, 60.0),
    ),
    "streaming": PurchaseCategory(
        name="Streaming Services",
        likelihood=0.0,
        typical_merchants=["netflix.com", "spotify.com", "hulu.com", "disney.com", "youtube.com"],
        typical_items=["Monthly Subscription", "Premium Upgrade", "Gift Subscription"],
        avg_amount_range=(10.0, 25.0),
    ),
    "health": PurchaseCategory(
        name="Health & Wellness",
        likelihood=0.0,
        typical_merchants=["cvs.com", "walgreens.com", "amazon.com", "vitacost.com"],
        typical_items=["Vitamins", "Supplements", "First Aid", "Personal Care"],
        avg_amount_range=(15.0, 80.0),
    ),
    "pharmacy": PurchaseCategory(
        name="Pharmacy",
        likelihood=0.0,
        typical_merchants=["cvs.com", "walgreens.com", "riteaid.com", "walmart.com"],
        typical_items=["Prescription Refill", "OTC Medicine", "Medical Supplies"],
        avg_amount_range=(10.0, 100.0),
    ),
    "books": PurchaseCategory(
        name="Books & Media",
        likelihood=0.0,
        typical_merchants=["amazon.com", "barnesandnoble.com", "audible.com", "kobo.com"],
        typical_items=["Paperback Book", "E-book", "Audiobook", "Magazine Subscription"],
        avg_amount_range=(10.0, 40.0),
    ),
    "automotive": PurchaseCategory(
        name="Automotive",
        likelihood=0.0,
        typical_merchants=["autozone.com", "advanceautoparts.com", "amazon.com", "rockauto.com"],
        typical_items=["Oil Filter", "Wiper Blades", "Car Accessories", "Cleaning Supplies"],
        avg_amount_range=(15.0, 100.0),
    ),
    "garden": PurchaseCategory(
        name="Garden & Outdoor",
        likelihood=0.0,
        typical_merchants=["homedepot.com", "lowes.com", "amazon.com", "walmart.com"],
        typical_items=["Seeds", "Garden Tools", "Fertilizer", "Outdoor Decor"],
        avg_amount_range=(20.0, 90.0),
    ),
    "fitness": PurchaseCategory(
        name="Fitness & Sports",
        likelihood=0.0,
        typical_merchants=["amazon.com", "dickssportinggoods.com", "nike.com", "underarmour.com"],
        typical_items=["Yoga Mat", "Dumbbells", "Fitness Tracker", "Athletic Wear"],
        avg_amount_range=(25.0, 120.0),
    ),
    "baby_kids": PurchaseCategory(
        name="Baby & Kids",
        likelihood=0.0,
        typical_merchants=["amazon.com", "target.com", "walmart.com", "buybuybaby.com"],
        typical_items=["Diapers", "Baby Formula", "Toys", "Kids Clothing"],
        avg_amount_range=(20.0, 100.0),
    ),
    "travel": PurchaseCategory(
        name="Travel",
        likelihood=0.0,
        typical_merchants=["expedia.com", "booking.com", "airbnb.com", "southwest.com"],
        typical_items=["Flight Ticket", "Hotel Booking", "Luggage", "Travel Accessories"],
        avg_amount_range=(50.0, 500.0),
    ),
    "software": PurchaseCategory(
        name="Software & Apps",
        likelihood=0.0,
        typical_merchants=["microsoft.com", "adobe.com", "apple.com", "steam.com"],
        typical_items=["Software License", "App Subscription", "Cloud Storage", "Antivirus"],
        avg_amount_range=(10.0, 150.0),
    ),
    "beauty": PurchaseCategory(
        name="Beauty & Cosmetics",
        likelihood=0.0,
        typical_merchants=["sephora.com", "ulta.com", "amazon.com", "target.com"],
        typical_items=["Makeup", "Skincare", "Hair Products", "Fragrance"],
        avg_amount_range=(20.0, 100.0),
    ),
    "tools": PurchaseCategory(
        name="Tools & Hardware",
        likelihood=0.0,
        typical_merchants=["homedepot.com", "lowes.com", "harborfreight.com", "amazon.com"],
        typical_items=["Power Tools", "Hand Tools", "Hardware", "Safety Equipment"],
        avg_amount_range=(25.0, 200.0),
    ),
    "home_decor": PurchaseCategory(
        name="Home Decor",
        likelihood=0.0,
        typical_merchants=["wayfair.com", "target.com", "amazon.com", "ikea.com"],
        typical_items=["Wall Art", "Decorative Pillows", "Candles", "Rugs"],
        avg_amount_range=(20.0, 150.0),
    ),
}


# ═══════════════════════════════════════════════════════════════════════════
# DEMOGRAPHIC PROFILER
# ═══════════════════════════════════════════════════════════════════════════

class DemographicProfiler:
    """
    Extract demographic signals from persona data (name, email, address, age).
    Uses heuristics and pattern matching to infer occupation, income, interests.
    """
    
    # Email domain → Occupation/Interest signals
    EMAIL_DOMAIN_SIGNALS = {
        # Tech companies
        "google.com": (OccupationCategory.TECH, ["tech_gadgets", "software"], 0.9),
        "microsoft.com": (OccupationCategory.TECH, ["tech_gadgets", "software"], 0.9),
        "apple.com": (OccupationCategory.TECH, ["tech_gadgets", "software"], 0.9),
        "amazon.com": (OccupationCategory.TECH, ["tech_gadgets", "software"], 0.85),
        "meta.com": (OccupationCategory.TECH, ["tech_gadgets", "software"], 0.85),
        "netflix.com": (OccupationCategory.TECH, ["streaming", "tech_gadgets"], 0.85),
        
        # Education
        ".edu": (OccupationCategory.EDUCATION, ["books", "software"], 0.7),
        "university": (OccupationCategory.STUDENT, ["books", "food_delivery", "gaming"], 0.8),
        "college": (OccupationCategory.STUDENT, ["books", "food_delivery", "gaming"], 0.8),
        
        # Healthcare
        "hospital": (OccupationCategory.HEALTHCARE, ["health", "pharmacy"], 0.8),
        "clinic": (OccupationCategory.HEALTHCARE, ["health", "pharmacy"], 0.8),
        "medical": (OccupationCategory.HEALTHCARE, ["health", "pharmacy"], 0.8),
        
        # Government
        ".gov": (OccupationCategory.GOVERNMENT, ["home_goods", "automotive"], 0.7),
        ".mil": (OccupationCategory.GOVERNMENT, ["automotive", "tools"], 0.8),
        
        # Generic email providers (no signal)
        "gmail.com": (None, [], 0.5),
        "yahoo.com": (None, [], 0.5),
        "outlook.com": (None, [], 0.5),
        "hotmail.com": (None, [], 0.5),
        "aol.com": (OccupationCategory.RETIRED, ["health", "garden"], 0.6),  # AOL = older demographic
    }
    
    # Name patterns → Gender inference (simple heuristic)
    MALE_NAME_PATTERNS = ["john", "michael", "david", "james", "robert", "william", "richard", "thomas", "charles", "daniel"]
    FEMALE_NAME_PATTERNS = ["mary", "patricia", "jennifer", "linda", "barbara", "elizabeth", "susan", "jessica", "sarah", "karen"]
    
    def profile(self, name: str, email: str, age: int, address: Dict[str, str]) -> DemographicProfile:
        """
        Generate demographic profile from persona data.
        
        Args:
            name: Full name
            email: Email address
            age: Age in years
            address: Dict with city, state, country, zip
            
        Returns:
            DemographicProfile with inferred signals
        """
        profile = DemographicProfile(
            full_name=name,
            email=email,
            age=age,
            city=address.get("city", ""),
            state=address.get("state", ""),
            country=address.get("country", "US"),
            zip_code=address.get("zip", ""),
        )
        
        # 1. Age group classification
        profile.age_group = self._classify_age_group(age)
        
        # 2. Gender inference (simple heuristic)
        profile.gender = self._infer_gender(name)
        
        # 3. Occupation inference from email domain
        occupation, interests, tech_score = self._infer_from_email(email)
        if occupation:
            profile.occupation_category = occupation
        profile.interests.extend(interests)
        profile.tech_savvy = tech_score
        
        # 4. Income inference from age + occupation
        profile.income_level = self._infer_income(age, profile.occupation_category)
        
        # 5. Online shopper score (age + tech savvy)
        profile.online_shopper = self._calculate_online_shopper_score(age, tech_score)
        
        logger.info(f"[PROFILER] {name} → {profile.age_group.value}, {profile.occupation_category.value}, {profile.income_level.value}")
        return profile
    
    def _classify_age_group(self, age: int) -> AgeGroup:
        """Map age to demographic age group"""
        if age < 28:
            return AgeGroup.GEN_Z
        elif age < 44:
            return AgeGroup.MILLENNIAL
        elif age < 60:
            return AgeGroup.GEN_X
        elif age < 79:
            return AgeGroup.BOOMER
        else:
            return AgeGroup.SILENT
    
    def _infer_gender(self, name: str) -> Optional[str]:
        """Simple gender inference from first name"""
        first_name = name.split()[0].lower() if name else ""
        if any(pattern in first_name for pattern in self.MALE_NAME_PATTERNS):
            return "M"
        elif any(pattern in first_name for pattern in self.FEMALE_NAME_PATTERNS):
            return "F"
        return None
    
    def _infer_from_email(self, email: str) -> Tuple[Optional[OccupationCategory], List[str], float]:
        """Infer occupation and interests from email domain"""
        domain = email.split("@")[-1].lower() if "@" in email else ""
        
        # Check exact matches first
        for pattern, (occupation, interests, tech_score) in self.EMAIL_DOMAIN_SIGNALS.items():
            if pattern in domain:
                return occupation, interests, tech_score
        
        # Default: no signal
        return None, [], 0.5
    
    def _infer_income(self, age: int, occupation: OccupationCategory) -> IncomeLevel:
        """Infer income level from age + occupation"""
        # Base income by occupation
        occupation_income_map = {
            OccupationCategory.TECH: IncomeLevel.UPPER_MID,
            OccupationCategory.FINANCE: IncomeLevel.UPPER_MID,
            OccupationCategory.HEALTHCARE: IncomeLevel.MIDDLE,
            OccupationCategory.EDUCATION: IncomeLevel.MIDDLE,
            OccupationCategory.CREATIVE: IncomeLevel.MIDDLE,
            OccupationCategory.GOVERNMENT: IncomeLevel.MIDDLE,
            OccupationCategory.TRADES: IncomeLevel.LOWER_MID,
            OccupationCategory.RETAIL: IncomeLevel.LOWER_MID,
            OccupationCategory.HOSPITALITY: IncomeLevel.LOW,
            OccupationCategory.STUDENT: IncomeLevel.LOW,
            OccupationCategory.UNEMPLOYED: IncomeLevel.LOW,
            OccupationCategory.RETIRED: IncomeLevel.MIDDLE,
        }
        
        base_income = occupation_income_map.get(occupation, IncomeLevel.MIDDLE)
        
        # Age adjustment: peak earning years are 45-60
        if 45 <= age <= 60 and base_income in (IncomeLevel.MIDDLE, IncomeLevel.UPPER_MID):
            # Bump up one level for peak earners
            if base_income == IncomeLevel.MIDDLE:
                return IncomeLevel.UPPER_MID
            elif base_income == IncomeLevel.UPPER_MID:
                return IncomeLevel.HIGH
        
        return base_income
    
    def _calculate_online_shopper_score(self, age: int, tech_savvy: float) -> float:
        """Calculate likelihood of being an active online shopper"""
        # Younger + tech savvy = higher online shopping
        age_factor = max(0.3, 1.0 - (age - 18) / 100)  # Decreases with age
        return min(1.0, (age_factor + tech_savvy) / 2)


# ═══════════════════════════════════════════════════════════════════════════
# PURCHASE PATTERN PREDICTOR
# ═══════════════════════════════════════════════════════════════════════════

class PurchasePatternPredictor:
    """
    Predict likely purchase categories and merchants from demographic profile.
    Uses weighted combination of age group + occupation + income patterns.
    """
    
    def predict(self, profile: DemographicProfile) -> Dict[str, PurchaseCategory]:
        """
        Predict purchase pattern for a demographic profile.
        
        Returns:
            Dict of category_name → PurchaseCategory with likelihood scores
        """
        # Start with base patterns from age group
        age_patterns = DEMOGRAPHIC_PURCHASE_PATTERNS.get(profile.age_group, {})
        occupation_patterns = DEMOGRAPHIC_PURCHASE_PATTERNS.get(profile.occupation_category, {})
        
        # Combine patterns with weighted average
        # Age group = 60%, Occupation = 40%
        combined_scores = {}
        all_categories = set(age_patterns.keys()) | set(occupation_patterns.keys())
        
        for category in all_categories:
            age_score = age_patterns.get(category, 0.3)  # Default 0.3 if not in age pattern
            occ_score = occupation_patterns.get(category, 0.3)  # Default 0.3 if not in occupation pattern
            
            # Weighted combination
            combined_score = (age_score * 0.6) + (occ_score * 0.4)
            
            # Boost if in explicit interests
            if category in profile.interests:
                combined_score = min(1.0, combined_score * 1.3)
            
            # Income adjustment: high-ticket items require higher income
            if category in ("travel", "automotive", "tools") and profile.income_level in (IncomeLevel.LOW, IncomeLevel.LOWER_MID):
                combined_score *= 0.6
            
            combined_scores[category] = combined_score
        
        # Convert to PurchaseCategory objects
        result = {}
        for category_name, likelihood in combined_scores.items():
            if category_name in PURCHASE_CATEGORY_DEFINITIONS:
                cat = PURCHASE_CATEGORY_DEFINITIONS[category_name]
                result[category_name] = PurchaseCategory(
                    name=cat.name,
                    likelihood=round(likelihood, 2),
                    typical_merchants=cat.typical_merchants,
                    typical_items=cat.typical_items,
                    avg_amount_range=cat.avg_amount_range,
                )
        
        # Sort by likelihood
        result = dict(sorted(result.items(), key=lambda x: x[1].likelihood, reverse=True))
        
        logger.info(f"[PREDICTOR] Top 3 categories for {profile.full_name}: " +
                   ", ".join(f"{k}={v.likelihood:.2f}" for k, v in list(result.items())[:3]))
        
        return result


# ═══════════════════════════════════════════════════════════════════════════
# COHERENCE VALIDATOR
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class CoherenceResult:
    """Result of purchase coherence validation"""
    coherent: bool
    confidence: float  # 0.0-1.0
    category_match: Optional[str]  # Which category the purchase matches
    likelihood_score: float  # Likelihood of this persona buying this item
    warning_message: str = ""
    recommended_alternatives: List[str] = field(default_factory=list)


class CoherenceValidator:
    """
    Validate if a target purchase is coherent with persona's demographic profile.
    Blocks out-of-pattern purchases BEFORE they trigger bank declines.
    """
    
    # Merchant → Primary Category mapping
    MERCHANT_CATEGORY_MAP = {
        "steampowered.com": "gaming",
        "g2a.com": "gaming",
        "eneba.com": "gaming",
        "gamestop.com": "gaming",
        "bestbuy.com": "tech_gadgets",
        "newegg.com": "tech_gadgets",
        "amazon.com": "home_goods",  # Default, but sells everything
        "target.com": "home_goods",
        "walmart.com": "home_goods",
        "cvs.com": "pharmacy",
        "walgreens.com": "pharmacy",
        "ubereats.com": "food_delivery",
        "doordash.com": "food_delivery",
        "netflix.com": "streaming",
        "spotify.com": "streaming",
        "homedepot.com": "tools",
        "lowes.com": "tools",
        "sephora.com": "beauty",
        "ulta.com": "beauty",
    }
    
    # Item keywords → Category mapping
    ITEM_KEYWORD_MAP = {
        "gaming": ["game", "gaming", "gift card", "steam", "xbox", "playstation", "nintendo", "controller", "headset"],
        "tech_gadgets": ["phone", "laptop", "tablet", "usb", "cable", "charger", "speaker", "webcam", "mouse", "keyboard"],
        "home_goods": ["kitchen", "utensil", "bedding", "towel", "storage", "furniture", "appliance"],
        "fashion": ["shirt", "jeans", "shoes", "jacket", "dress", "pants", "sneakers"],
        "food_delivery": ["restaurant", "food", "delivery", "meal"],
        "health": ["vitamin", "supplement", "first aid", "personal care"],
        "pharmacy": ["prescription", "medicine", "otc", "medical"],
        "books": ["book", "ebook", "audiobook", "magazine"],
        "automotive": ["oil", "filter", "wiper", "car", "auto"],
        "garden": ["seed", "plant", "fertilizer", "garden"],
        "fitness": ["yoga", "dumbbell", "fitness", "athletic"],
        "baby_kids": ["diaper", "baby", "formula", "toy", "kids"],
        "tools": ["drill", "saw", "hammer", "tool", "hardware"],
        "beauty": ["makeup", "skincare", "cosmetic", "fragrance"],
    }
    
    # Coherence thresholds
    COHERENT_THRESHOLD = 0.40  # Likelihood >= 40% = coherent
    CAUTION_THRESHOLD = 0.25   # 25-40% = caution warning
    INCOHERENT_THRESHOLD = 0.25  # <25% = block
    
    def __init__(self, predictor: PurchasePatternPredictor):
        self.predictor = predictor
    
    def validate(self, 
                 profile: DemographicProfile,
                 target_merchant: str,
                 target_item: str = "",
                 amount: float = 0.0) -> CoherenceResult:
        """
        Validate if the target purchase is coherent with the persona's profile.
        
        Args:
            profile: Demographic profile
            target_merchant: Target merchant domain (e.g., "g2a.com")
            target_item: Item description (optional, for better categorization)
            amount: Purchase amount (optional, for income validation)
            
        Returns:
            CoherenceResult with validation verdict
        """
        # 1. Predict purchase patterns for this persona
        patterns = self.predictor.predict(profile)
        
        # 2. Determine category of target purchase
        target_category = self._categorize_purchase(target_merchant, target_item)
        
        if not target_category:
            # Unknown merchant/item — default to moderate coherence
            return CoherenceResult(
                coherent=True,
                confidence=0.5,
                category_match=None,
                likelihood_score=0.5,
                warning_message=f"Unknown merchant '{target_merchant}' — cannot validate coherence. Proceeding with caution.",
            )
        
        # 3. Check if this category is in the persona's predicted patterns
        if target_category not in patterns:
            # Category not predicted at all — very low coherence
            top_categories = list(patterns.keys())[:3]
            return CoherenceResult(
                coherent=False,
                confidence=0.9,
                category_match=target_category,
                likelihood_score=0.1,
                warning_message=(
                    f"⚠️ INCOHERENT PURCHASE: {profile.full_name} ({profile.age}y, {profile.occupation_category.value}) "
                    f"buying '{target_category}' from {target_merchant} is OUT OF PATTERN. "
                    f"This persona typically buys: {', '.join(top_categories)}. "
                    f"High risk of 'generic bank decline' or fraud block."
                ),
                recommended_alternatives=[patterns[cat].typical_merchants[0] for cat in top_categories if patterns[cat].typical_merchants],
            )
        
        # 4. Get likelihood score for this category
        category_data = patterns[target_category]
        likelihood = category_data.likelihood
        
        # 5. Amount validation (if provided)
        amount_coherent = True
        if amount > 0:
            min_amt, max_amt = category_data.avg_amount_range
            if amount < min_amt * 0.5 or amount > max_amt * 2.0:
                amount_coherent = False
                likelihood *= 0.7  # Reduce likelihood for unusual amounts
        
        # 6. Determine coherence verdict
        if likelihood >= self.COHERENT_THRESHOLD:
            return CoherenceResult(
                coherent=True,
                confidence=likelihood,
                category_match=target_category,
                likelihood_score=likelihood,
                warning_message=f"✅ COHERENT: {profile.full_name} buying '{target_category}' is consistent with profile (likelihood={likelihood:.0%}).",
            )
        elif likelihood >= self.CAUTION_THRESHOLD:
            return CoherenceResult(
                coherent=True,
                confidence=likelihood,
                category_match=target_category,
                likelihood_score=likelihood,
                warning_message=(
                    f"⚠️ CAUTION: {profile.full_name} buying '{target_category}' is SLIGHTLY out of pattern (likelihood={likelihood:.0%}). "
                    f"Consider using a more typical category for this persona."
                ),
            )
        else:
            top_categories = list(patterns.keys())[:3]
            return CoherenceResult(
                coherent=False,
                confidence=0.8,
                category_match=target_category,
                likelihood_score=likelihood,
                warning_message=(
                    f"🚫 INCOHERENT: {profile.full_name} buying '{target_category}' has LOW likelihood ({likelihood:.0%}). "
                    f"Recommended categories: {', '.join(top_categories)}."
                ),
                recommended_alternatives=[patterns[cat].typical_merchants[0] for cat in top_categories[:3] if patterns[cat].typical_merchants],
            )
    
    def _categorize_purchase(self, merchant: str, item: str = "") -> Optional[str]:
        """Determine purchase category from merchant domain and item description"""
        merchant_lower = merchant.lower()
        item_lower = item.lower()
        
        # 1. Check merchant mapping
        for merchant_pattern, category in self.MERCHANT_CATEGORY_MAP.items():
            if merchant_pattern in merchant_lower:
                return category
        
        # 2. Check item keywords
        if item_lower:
            for category, keywords in self.ITEM_KEYWORD_MAP.items():
                if any(kw in item_lower for kw in keywords):
                    return category
        
        # 3. Unknown
        return None


# ═══════════════════════════════════════════════════════════════════════════
# OSINT ENRICHER (OPTIONAL)
# ═══════════════════════════════════════════════════════════════════════════

class OSINTEnricher:
    """
    Optional integration with self-hosted OSINT tools for enhanced profiling.
    
    Supported tools (all self-hosted, no external API calls):
    - Sherlock: GitHub username → social profiles
    - Holehe: Email → registered accounts
    - Maigret: Username → 2500+ sites
    - theHarvester: Email → public data sources
    - Photon: Web scraper for person data
    
    All tools are OPTIONAL. If not installed, enrichment is skipped.
    """
    
    def __init__(self, tools_dir: Path = Path("/opt/titan/osint_tools")):
        self.tools_dir = tools_dir
        self.sherlock_path = tools_dir / "sherlock" / "sherlock.py"
        self.holehe_path = tools_dir / "holehe" / "holehe.py"
        self.maigret_path = tools_dir / "maigret" / "maigret.py"
        
        # Check which tools are available
        self.sherlock_available = self.sherlock_path.exists()
        self.holehe_available = self.holehe_path.exists()
        self.maigret_available = self.maigret_path.exists()
        
        if not any([self.sherlock_available, self.holehe_available, self.maigret_available]):
            logger.info("[OSINT] No OSINT tools detected — enrichment disabled")
        else:
            logger.info(f"[OSINT] Available tools: Sherlock={self.sherlock_available}, Holehe={self.holehe_available}, Maigret={self.maigret_available}")
    
    def enrich_from_email(self, email: str, timeout: int = 30) -> Dict[str, any]:
        """
        Enrich profile using email address.
        
        Uses Holehe to find which services the email is registered on.
        Returns dict with discovered accounts and inferred interests.
        """
        if not self.holehe_available:
            return {}
        
        try:
            result = subprocess.run(
                ["python3", str(self.holehe_path), email, "--no-color"],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            
            # Parse Holehe output for registered services
            # Format: "[+] Email used on: service1, service2, ..."
            accounts = []
            for line in result.stdout.split("\n"):
                if "[+]" in line and "used on" in line.lower():
                    services = line.split(":")[-1].strip().split(",")
                    accounts.extend([s.strip() for s in services])
            
            # Infer interests from registered accounts
            interests = self._infer_interests_from_accounts(accounts)
            
            return {
                "registered_accounts": accounts,
                "inferred_interests": interests,
                "source": "holehe",
            }
        
        except subprocess.TimeoutExpired:
            logger.warning(f"[OSINT] Holehe timeout for {email}")
            return {}
        except Exception as e:
            logger.debug(f"[OSINT] Holehe failed for {email}: {e}")
            return {}
    
    def _infer_interests_from_accounts(self, accounts: List[str]) -> List[str]:
        """Infer interests from registered account names"""
        interests = []
        account_interest_map = {
            "steam": "gaming",
            "twitch": "gaming",
            "discord": "gaming",
            "epicgames": "gaming",
            "spotify": "streaming",
            "netflix": "streaming",
            "github": "tech_gadgets",
            "linkedin": "professional",
            "instagram": "fashion",
            "pinterest": "home_decor",
            "etsy": "creative",
            "goodreads": "books",
            "strava": "fitness",
            "myfitnesspal": "fitness",
        }
        
        for account in accounts:
            account_lower = account.lower()
            for service, interest in account_interest_map.items():
                if service in account_lower and interest not in interests:
                    interests.append(interest)
        
        return interests


# ═══════════════════════════════════════════════════════════════════════════
# MAIN ENGINE
# ═══════════════════════════════════════════════════════════════════════════

class PersonaEnrichmentEngine:
    """
    Main engine that combines all components:
    1. Profile demographics from name/email/age/address
    2. Predict purchase patterns
    3. Validate purchase coherence
    4. Optional OSINT enrichment
    """
    
    def __init__(self, enable_osint: bool = False):
        self.profiler = DemographicProfiler()
        self.predictor = PurchasePatternPredictor()
        self.validator = CoherenceValidator(self.predictor)
        self.osint = OSINTEnricher() if enable_osint else None
        
        logger.info(f"[ENGINE] Persona Enrichment Engine initialized (OSINT={'enabled' if enable_osint else 'disabled'})")
    
    def enrich_and_validate(self,
                            name: str,
                            email: str,
                            age: int,
                            address: Dict[str, str],
                            target_merchant: str,
                            target_item: str = "",
                            amount: float = 0.0) -> Tuple[DemographicProfile, Dict[str, PurchaseCategory], CoherenceResult]:
        """
        Full pipeline: profile → predict → validate.
        
        Returns:
            (demographic_profile, purchase_patterns, coherence_result)
        """
        # 1. Profile demographics
        profile = self.profiler.profile(name, email, age, address)
        
        # 2. Optional OSINT enrichment
        if self.osint:
            osint_data = self.osint.enrich_from_email(email)
            if osint_data.get("inferred_interests"):
                profile.interests.extend(osint_data["inferred_interests"])
                logger.info(f"[OSINT] Enriched {name} with interests: {osint_data['inferred_interests']}")
        
        # 3. Predict purchase patterns
        patterns = self.predictor.predict(profile)
        
        # 4. Validate coherence
        coherence = self.validator.validate(profile, target_merchant, target_item, amount)
        
        return profile, patterns, coherence


# ═══════════════════════════════════════════════════════════════════════════
# CLI INTERFACE
# ═══════════════════════════════════════════════════════════════════════════

def main():
    """CLI for testing persona enrichment"""
    import argparse
    
    parser = argparse.ArgumentParser(description="TITAN Persona Enrichment Engine")
    parser.add_argument("--name", required=True, help="Full name")
    parser.add_argument("--email", required=True, help="Email address")
    parser.add_argument("--age", type=int, required=True, help="Age in years")
    parser.add_argument("--city", default="", help="City")
    parser.add_argument("--state", default="", help="State")
    parser.add_argument("--country", default="US", help="Country code")
    parser.add_argument("--merchant", required=True, help="Target merchant (e.g., g2a.com)")
    parser.add_argument("--item", default="", help="Item description")
    parser.add_argument("--amount", type=float, default=0.0, help="Purchase amount")
    parser.add_argument("--osint", action="store_true", help="Enable OSINT enrichment")
    
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    
    engine = PersonaEnrichmentEngine(enable_osint=args.osint)
    
    address = {
        "city": args.city,
        "state": args.state,
        "country": args.country,
    }
    
    profile, patterns, coherence = engine.enrich_and_validate(
        args.name, args.email, args.age, address,
        args.merchant, args.item, args.amount
    )
    
    print("\n" + "="*80)
    print("DEMOGRAPHIC PROFILE")
    print("="*80)
    print(f"Name: {profile.full_name}")
    print(f"Age: {profile.age} ({profile.age_group.value})")
    print(f"Occupation: {profile.occupation_category.value}")
    print(f"Income: {profile.income_level.value}")
    print(f"Tech Savvy: {profile.tech_savvy:.0%}")
    print(f"Online Shopper: {profile.online_shopper:.0%}")
    if profile.interests:
        print(f"Interests: {', '.join(profile.interests)}")
    
    print("\n" + "="*80)
    print("PREDICTED PURCHASE PATTERNS (Top 5)")
    print("="*80)
    for i, (cat_name, cat_data) in enumerate(list(patterns.items())[:5], 1):
        print(f"{i}. {cat_data.name}: {cat_data.likelihood:.0%} likelihood")
        print(f"   Merchants: {', '.join(cat_data.typical_merchants[:3])}")
        print(f"   Items: {', '.join(cat_data.typical_items[:3])}")
        print(f"   Amount: ${cat_data.avg_amount_range[0]:.0f}-${cat_data.avg_amount_range[1]:.0f}")
    
    print("\n" + "="*80)
    print("COHERENCE VALIDATION")
    print("="*80)
    print(f"Target: {args.merchant} ({args.item or 'no item specified'})")
    print(f"Coherent: {'✅ YES' if coherence.coherent else '🚫 NO'}")
    print(f"Confidence: {coherence.confidence:.0%}")
    print(f"Category: {coherence.category_match or 'unknown'}")
    print(f"Likelihood: {coherence.likelihood_score:.0%}")
    print(f"\n{coherence.warning_message}")
    
    if coherence.recommended_alternatives:
        print(f"\nRecommended merchants: {', '.join(coherence.recommended_alternatives)}")
    
    print("="*80)


if __name__ == "__main__":
    main()
