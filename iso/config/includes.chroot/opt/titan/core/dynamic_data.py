"""
TITAN V7.5 SINGULARITY — Dynamic Data Generator
Replaces hardcoded databases with Ollama-powered dynamic generation + caching.

Modules that benefit:
    - target_discovery.py: SITE_DATABASE (140 hardcoded → 500+ dynamic)
    - target_presets.py: TARGET_PRESETS (9 hardcoded → auto-generate for any domain)
    - three_ds_strategy.py: NON_VBV_BINS, COUNTRY_PROFILES, MERCHANT_3DS_PATTERNS

Each generator:
    1. Takes seed data (the existing hardcoded entries) as examples
    2. Asks Ollama to generate more in the same format
    3. Caches results to disk (24h TTL)
    4. Falls back to seed data if Ollama is unavailable
"""

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("TITAN-DYNAMIC-DATA")

try:
    from ollama_bridge import (
        generate_with_cache, is_ollama_available, query_ollama_json,
        query_llm_json, invalidate_cache, get_cache_stats,
        get_provider_status, resolve_provider_for_task,
    )
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    def generate_with_cache(cache_key, prompt, fallback=None, **kw):
        return fallback
    def is_ollama_available():
        return False
    def resolve_provider_for_task(task_type="default"):
        return None

# Backward compat alias
OLLAMA_AVAILABLE = LLM_AVAILABLE


# ═══════════════════════════════════════════════════════════════════════════
# 1. MERCHANT SITE GENERATOR — Expands SITE_DATABASE
# ═══════════════════════════════════════════════════════════════════════════

MERCHANT_SITE_PROMPT = """You are a payment security researcher. Generate {count} NEW merchant websites that accept credit cards online.

For each site, provide a JSON object with these exact fields:
- domain: the website domain (e.g. "example-store.com")
- name: human-readable store name
- category: one of: gaming, gift_cards, digital, electronics, fashion, crypto, shopify, subscriptions, travel, food_delivery, software, education, health, home_goods, sports, entertainment, misc
- difficulty: one of: easy, moderate, hard
- psp: payment processor, one of: stripe, adyen, braintree, authorize_net, worldpay, checkout_com, square, paypal, shopify_payments, klarna, mollie, nmi, unknown
- three_ds: one of: none, conditional, always
- fraud_engine: one of: forter, riskified, sift, kount, seon, signifyd, none, basic, unknown
- is_shopify: boolean
- country_focus: array of 2-letter country codes where cards work best
- max_amount: max safe transaction amount in USD (number)
- success_rate: estimated success rate 0.0-1.0
- products: what they sell (short string)
- notes: operational notes (short string)

Here are {seed_count} examples of the format:
{seed_examples}

IMPORTANT RULES:
- Generate REAL websites that actually exist and accept credit cards
- Do NOT repeat any domain from the examples above
- Focus on sites with Stripe, Shopify Payments, or Authorize.net (lower 3DS friction)
- Include a mix of categories
- Prefer sites with "easy" or "moderate" difficulty
- Return a JSON array of objects

Generate {count} new entries:"""


def generate_merchant_sites(seed_sites: List[Dict], count: int = 100) -> List[Dict]:
    """
    Generate additional merchant sites using Ollama.
    
    Args:
        seed_sites: Existing hardcoded sites as dicts (used as examples)
        count: How many new sites to generate
    
    Returns:
        List of new site dicts (merged with seed if Ollama available)
    """
    # Format seed examples (show first 5)
    seed_examples = json.dumps(seed_sites[:5], indent=2, default=str)
    
    prompt = MERCHANT_SITE_PROMPT.format(
        count=count,
        seed_count=min(5, len(seed_sites)),
        seed_examples=seed_examples
    )
    
    result = generate_with_cache(
        cache_key=f"merchant_sites_{count}",
        prompt=prompt,
        fallback=[],
        temperature=0.4,
        max_tokens=16384,
        timeout=300,
        task_type="site_discovery"
    )
    
    if isinstance(result, list):
        # Validate and clean results
        valid = []
        existing_domains = {s.get("domain", "").lower() for s in seed_sites}
        for site in result:
            if isinstance(site, dict) and "domain" in site:
                domain = site["domain"].lower().strip()
                if domain and domain not in existing_domains:
                    existing_domains.add(domain)
                    valid.append(site)
        logger.info(f"Ollama generated {len(valid)} new merchant sites")
        return valid
    
    return []


# ═══════════════════════════════════════════════════════════════════════════
# 2. TARGET PRESET GENERATOR — Auto-generates presets for any domain
# ═══════════════════════════════════════════════════════════════════════════

TARGET_PRESET_PROMPT = """You are a browser fingerprint expert. Generate a realistic browser profile preset for the website: {domain}

The preset should include data that makes a browser profile look like a real user who regularly visits this site.

Return a JSON object with these exact fields:
- domain: "{domain}"
- name: human-readable name for this target
- category: one of: gaming_marketplace, retail, electronics, gaming_platform, digital_goods, subscription, crypto, financial
- history_domains: array of 8-12 domains a real user would also visit (include the target + related sites + general browsing)
- history_weight: object mapping each history_domain to a visit weight (1-30, higher = more visits)
- cookies: array of cookie objects with fields: domain, name, age_days (optional), value (optional)
- localstorage: object mapping domains to key-value pairs of localStorage data
- recommended_archetype: one of: gamer, student_developer, casual_shopper, professional, crypto_trader
- three_ds_rate: estimated 3DS trigger rate 0.0-1.0
- min_age_days: minimum profile age in days (30-120)
- recommended_age_days: recommended profile age (60-180)
- warmup_searches: array of 3-5 Google search queries a real user would make before visiting this site
- referrer_chain: array of 2-4 domains showing how a user would navigate to this site

Make it realistic. A real person browsing {domain} would also visit social media, news, entertainment sites.
The cookies should include real cookie names that {domain} actually sets.
The warmup searches should be natural queries someone would type before buying from {domain}.

Return ONLY the JSON object:"""


def generate_target_preset(domain: str) -> Optional[Dict]:
    """
    Auto-generate a target preset for any domain using Ollama.
    
    Args:
        domain: The target website domain
    
    Returns:
        Preset dict or None if generation fails
    """
    prompt = TARGET_PRESET_PROMPT.format(domain=domain)
    
    result = generate_with_cache(
        cache_key=f"preset_{domain}",
        prompt=prompt,
        fallback=None,
        temperature=0.3,
        max_tokens=4096,
        timeout=120,
        task_type="preset_generation"
    )
    
    if isinstance(result, dict) and "domain" in result:
        logger.info(f"Generated preset for {domain}")
        return result
    
    return None


def generate_bulk_presets(domains: List[str]) -> List[Dict]:
    """Generate presets for multiple domains."""
    presets = []
    for domain in domains:
        preset = generate_target_preset(domain)
        if preset:
            presets.append(preset)
    return presets


# ═══════════════════════════════════════════════════════════════════════════
# 3. BIN DATABASE GENERATOR — Expands NON_VBV_BINS
# ═══════════════════════════════════════════════════════════════════════════

BIN_PROMPT = """You are a payment card security researcher. Generate {count} NEW credit card BIN entries for country: {country} ({country_name}).

Each BIN entry should be a JSON object with:
- bin: 6-digit BIN number (string)
- bank: issuing bank name
- country: 2-letter country code
- network: one of: visa, mastercard, discover, amex
- card_type: one of: credit, debit
- card_level: one of: classic, gold, platinum, signature, world, infinite, business
- vbv_status: one of: non_vbv, low_vbv, conditional_vbv
- three_ds_rate: estimated 3DS trigger rate 0.0-1.0 (lower is better)
- avs_enforced: boolean
- notes: operational notes about this BIN
- recommended_targets: array of 3-5 merchant domains where this BIN works well

Here are existing BINs for {country} as examples:
{seed_examples}

RULES:
- Generate REALISTIC BIN numbers from real banks in {country_name}
- Do NOT repeat any BIN from the examples
- Focus on BINs with LOW 3DS rates (non_vbv or low_vbv)
- Include a mix of Visa and Mastercard
- Prefer credit cards over debit
- Return a JSON array

Generate {count} new BIN entries:"""


def generate_bins_for_country(country: str, country_name: str,
                               seed_bins: List[Dict], count: int = 20) -> List[Dict]:
    """
    Generate additional BIN entries for a country using Ollama.
    
    Args:
        country: 2-letter country code
        country_name: Full country name
        seed_bins: Existing BINs as dicts (used as examples)
        count: How many new BINs to generate
    
    Returns:
        List of new BIN dicts
    """
    seed_examples = json.dumps(seed_bins[:3], indent=2, default=str)
    
    prompt = BIN_PROMPT.format(
        count=count,
        country=country,
        country_name=country_name,
        seed_examples=seed_examples
    )
    
    result = generate_with_cache(
        cache_key=f"bins_{country}_{count}",
        prompt=prompt,
        fallback=[],
        temperature=0.3,
        max_tokens=8192,
        timeout=180,
        task_type="bin_generation"
    )
    
    if isinstance(result, list):
        existing_bins = {b.get("bin", "") for b in seed_bins}
        valid = [b for b in result if isinstance(b, dict) and b.get("bin") and b["bin"] not in existing_bins]
        logger.info(f"Ollama generated {len(valid)} new BINs for {country}")
        return valid
    
    return []


# ═══════════════════════════════════════════════════════════════════════════
# 4. COUNTRY PROFILE GENERATOR — Expands COUNTRY_PROFILES
# ═══════════════════════════════════════════════════════════════════════════

COUNTRY_PROMPT = """You are a payment security researcher. Generate detailed country profiles for credit card operations in these countries: {countries}

For each country, provide a JSON object with:
- code: 2-letter ISO country code
- name: full country name
- difficulty: one of: easy, moderate, hard
- psd2_enforced: boolean (true for EU/EEA countries)
- three_ds_base_rate: base 3DS trigger rate 0.0-1.0
- avs_common: boolean (true if AVS is commonly enforced)
- best_card_types: array of: credit, debit
- best_networks: array of: visa, mastercard, amex, discover
- notes: detailed operational notes (2-4 sentences about 3DS adoption, bank behavior, exemptions)
- recommended_targets: array of 3-6 merchant domains that work well with cards from this country

Here are existing profiles as examples:
{seed_examples}

RULES:
- Be accurate about PSD2 enforcement (only EU/EEA countries)
- Be accurate about 3DS adoption rates
- Include specific bank names in the notes
- Focus on actionable intelligence
- Return a JSON array

Generate profiles for: {countries}"""


def generate_country_profiles(country_codes: List[str],
                                seed_profiles: List[Dict]) -> List[Dict]:
    """
    Generate country profiles for new countries using Ollama.
    
    Args:
        country_codes: List of 2-letter country codes to generate
        seed_profiles: Existing profiles as dicts (used as examples)
    
    Returns:
        List of new country profile dicts
    """
    seed_examples = json.dumps(seed_profiles[:3], indent=2, default=str)
    countries = ", ".join(country_codes)
    
    prompt = COUNTRY_PROMPT.format(
        countries=countries,
        seed_examples=seed_examples
    )
    
    result = generate_with_cache(
        cache_key=f"countries_{'_'.join(sorted(country_codes))}",
        prompt=prompt,
        fallback=[],
        temperature=0.3,
        max_tokens=8192,
        timeout=180,
        task_type="country_profiles"
    )
    
    if isinstance(result, list):
        logger.info(f"Ollama generated {len(result)} country profiles")
        return result
    
    return []


# ═══════════════════════════════════════════════════════════════════════════
# 5. DISCOVERY DORK GENERATOR — Expands DISCOVERY_DORKS
# ═══════════════════════════════════════════════════════════════════════════

DORK_PROMPT = """You are a Google dorking expert for finding e-commerce websites. Generate {count} NEW Google dork queries to discover merchant websites that accept credit cards.

Each entry should be a JSON object with:
- query: the Google dork query string (use operators like site:, inurl:, intitle:, "exact match")
- category: one of: shopify, gaming, gift_cards, digital, electronics, fashion, crypto, subscriptions, software, travel, food_delivery, health, education, home_goods, sports, misc
- expected_psp: likely payment processor: stripe, shopify_payments, authorize_net, braintree, adyen, nmi, unknown

Here are existing dorks as examples:
{seed_examples}

RULES:
- Generate UNIQUE dork queries (not duplicates of examples)
- Focus on finding sites with Stripe, Shopify Payments, or Authorize.net
- Exclude major retailers (amazon, walmart, ebay, etc.) using -site: operators
- Include a mix of categories
- Queries should find SMALL/MEDIUM merchants (easier targets)
- Use advanced Google operators effectively
- Return a JSON array

Generate {count} new dork queries:"""


def generate_discovery_dorks(seed_dorks: List[Dict], count: int = 50) -> List[Dict]:
    """
    Generate additional discovery dork queries using Ollama.
    
    Args:
        seed_dorks: Existing dorks as dicts (used as examples)
        count: How many new dorks to generate
    
    Returns:
        List of new dork dicts
    """
    seed_examples = json.dumps(seed_dorks[:5], indent=2, default=str)
    
    prompt = DORK_PROMPT.format(
        count=count,
        seed_examples=seed_examples
    )
    
    result = generate_with_cache(
        cache_key=f"dorks_{count}",
        prompt=prompt,
        fallback=[],
        temperature=0.5,
        max_tokens=8192,
        timeout=180,
        task_type="dork_generation"
    )
    
    if isinstance(result, list):
        # Deduplicate against seed
        existing_queries = {d.get("query", "").lower() for d in seed_dorks}
        valid = [d for d in result if isinstance(d, dict) and d.get("query", "").lower() not in existing_queries]
        logger.info(f"Ollama generated {len(valid)} new discovery dorks")
        return valid
    
    return []


# ═══════════════════════════════════════════════════════════════════════════
# 6. WARMUP SEARCH GENERATOR — Dynamic search queries for any target
# ═══════════════════════════════════════════════════════════════════════════

WARMUP_PROMPT = """Generate {count} realistic Google search queries that a real person would type before visiting and buying from {domain}.

The searches should show a natural progression:
1. General interest/research queries
2. Comparison/review queries
3. Specific product/deal queries
4. Direct navigation queries

Return a JSON array of strings (just the search queries).

Example for "g2a.com": ["cheap game keys", "g2a reviews reddit", "g2a vs eneba prices", "g2a steam key deals", "buy game key online"]

Generate {count} searches for {domain}:"""


def generate_warmup_searches(domain: str, count: int = 10) -> List[str]:
    """Generate realistic warmup search queries for a domain."""
    prompt = WARMUP_PROMPT.format(domain=domain, count=count)
    
    result = generate_with_cache(
        cache_key=f"warmup_{domain}_{count}",
        prompt=prompt,
        fallback=[],
        temperature=0.5,
        max_tokens=2048,
        timeout=60,
        task_type="warmup_searches"
    )
    
    if isinstance(result, list):
        return [s for s in result if isinstance(s, str)]
    return []


# ═══════════════════════════════════════════════════════════════════════════
# MASTER EXPANSION FUNCTION — Expand all hardcoded data at once
# ═══════════════════════════════════════════════════════════════════════════

def expand_all_databases(site_seeds: List[Dict] = None,
                          bin_seeds: Dict[str, List[Dict]] = None,
                          dork_seeds: List[Dict] = None,
                          profile_seeds: List[Dict] = None) -> Dict[str, Any]:
    """
    Expand all hardcoded databases using Ollama.
    Call this once at startup or on-demand to populate caches.
    
    Returns dict with expansion results/stats.
    """
    stats = {
        "llm_available": is_ollama_available() if LLM_AVAILABLE else False,
        "provider_status": get_provider_status() if LLM_AVAILABLE else {},
        "expansions": {}
    }
    
    if not stats["llm_available"]:
        logger.warning("No LLM provider available — using seed data only")
        return stats
    
    # Expand merchant sites
    if site_seeds:
        new_sites = generate_merchant_sites(site_seeds, count=100)
        stats["expansions"]["merchant_sites"] = len(new_sites)
    
    # Expand BINs per country
    if bin_seeds:
        total_bins = 0
        for country, bins in bin_seeds.items():
            country_name = {
                "US": "United States", "CA": "Canada", "GB": "United Kingdom",
                "FR": "France", "DE": "Germany", "NL": "Netherlands",
                "AU": "Australia", "IT": "Italy", "ES": "Spain",
                "JP": "Japan", "BR": "Brazil", "MX": "Mexico",
            }.get(country, country)
            new_bins = generate_bins_for_country(country, country_name, bins, count=15)
            total_bins += len(new_bins)
        stats["expansions"]["bins"] = total_bins
    
    # Expand discovery dorks
    if dork_seeds:
        new_dorks = generate_discovery_dorks(dork_seeds, count=50)
        stats["expansions"]["discovery_dorks"] = len(new_dorks)
    
    logger.info(f"Database expansion complete: {stats['expansions']}")
    return stats


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 DATA QUALITY VALIDATOR — Validate generated data quality
# ═══════════════════════════════════════════════════════════════════════════════

from dataclasses import dataclass, field
from typing import Callable, Tuple
import re
import time


@dataclass
class ValidationResult:
    """Result of data quality validation."""
    valid: bool
    quality_score: float  # 0.0-1.0
    errors: List[str]
    warnings: List[str]
    records_checked: int
    records_passed: int


class DataQualityValidator:
    """
    V7.6 Data Quality Validator - Validates generated data
    for accuracy, completeness, and consistency.
    """
    
    # Validation rules
    DOMAIN_PATTERN = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9-_.]+\.[a-zA-Z]{2,}$')
    BIN_PATTERN = re.compile(r'^\d{6}$')
    COUNTRY_PATTERN = re.compile(r'^[A-Z]{2}$')
    
    VALID_CATEGORIES = {
        "gaming", "gift_cards", "digital", "electronics", "fashion", "crypto",
        "shopify", "subscriptions", "travel", "food_delivery", "software",
        "education", "health", "home_goods", "sports", "entertainment", "misc",
        "gaming_marketplace", "retail", "gaming_platform", "digital_goods",
        "subscription", "financial"
    }
    
    VALID_PSPS = {
        "stripe", "adyen", "braintree", "authorize_net", "worldpay", "checkout_com",
        "square", "paypal", "shopify_payments", "klarna", "mollie", "nmi", "unknown",
        "internal", "checkout"
    }
    
    VALID_NETWORKS = {"visa", "mastercard", "amex", "discover", "jcb", "unionpay"}
    
    def __init__(self):
        self._validations_performed = 0
        self._validation_stats: Dict[str, int] = {"passed": 0, "failed": 0}
    
    def validate_merchant_site(self, site: Dict) -> Tuple[bool, List[str]]:
        """Validate a single merchant site entry."""
        errors = []
        
        # Required fields
        required = ["domain", "name", "category"]
        for field in required:
            if field not in site:
                errors.append(f"Missing required field: {field}")
        
        # Domain format
        domain = site.get("domain", "")
        if not self.DOMAIN_PATTERN.match(domain):
            errors.append(f"Invalid domain format: {domain}")
        
        # Category
        category = site.get("category", "").lower()
        if category and category not in self.VALID_CATEGORIES:
            errors.append(f"Invalid category: {category}")
        
        # PSP
        psp = site.get("psp", "").lower()
        if psp and psp not in self.VALID_PSPS:
            errors.append(f"Invalid PSP: {psp}")
        
        # Success rate range
        success_rate = site.get("success_rate", 0.5)
        if isinstance(success_rate, (int, float)):
            if success_rate < 0 or success_rate > 1:
                errors.append(f"Success rate out of range: {success_rate}")
        
        return len(errors) == 0, errors
    
    def validate_bin_entry(self, bin_entry: Dict) -> Tuple[bool, List[str]]:
        """Validate a single BIN entry."""
        errors = []
        
        # BIN format
        bin_num = str(bin_entry.get("bin", ""))
        if not self.BIN_PATTERN.match(bin_num):
            errors.append(f"Invalid BIN format: {bin_num}")
        
        # Country code
        country = bin_entry.get("country", "")
        if not self.COUNTRY_PATTERN.match(country):
            errors.append(f"Invalid country code: {country}")
        
        # Network
        network = bin_entry.get("network", "").lower()
        if network and network not in self.VALID_NETWORKS:
            errors.append(f"Invalid network: {network}")
        
        # 3DS rate range
        three_ds_rate = bin_entry.get("three_ds_rate", 0.5)
        if isinstance(three_ds_rate, (int, float)):
            if three_ds_rate < 0 or three_ds_rate > 1:
                errors.append(f"3DS rate out of range: {three_ds_rate}")
        
        return len(errors) == 0, errors
    
    def validate_dataset(self, data: List[Dict], 
                         validator: Callable[[Dict], Tuple[bool, List[str]]]) -> ValidationResult:
        """Validate an entire dataset."""
        all_errors = []
        all_warnings = []
        passed = 0
        
        for item in data:
            valid, errors = validator(item)
            if valid:
                passed += 1
            else:
                all_errors.extend(errors[:3])  # Limit errors per item
        
        total = len(data)
        quality_score = passed / total if total > 0 else 0
        
        self._validations_performed += 1
        self._validation_stats["passed" if quality_score >= 0.8 else "failed"] += 1
        
        return ValidationResult(
            valid=quality_score >= 0.8,
            quality_score=round(quality_score, 2),
            errors=all_errors[:20],  # Limit total errors
            warnings=all_warnings[:10],
            records_checked=total,
            records_passed=passed
        )
    
    def get_stats(self) -> Dict:
        """Get validation statistics."""
        return {
            "validations_performed": self._validations_performed,
            **self._validation_stats
        }


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 DATA FUSION ENGINE — Merge and dedupe data from multiple sources
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class FusionResult:
    """Result of data fusion."""
    merged_count: int
    duplicates_removed: int
    conflicts_resolved: int
    source_stats: Dict[str, int]


class DataFusionEngine:
    """
    V7.6 Data Fusion Engine - Merges data from multiple sources,
    deduplicates entries, and resolves conflicts.
    """
    
    def __init__(self):
        self._merge_history: List[Dict] = []
    
    def merge_merchant_sites(self, *sources: List[Dict],
                             key_field: str = "domain") -> Tuple[List[Dict], FusionResult]:
        """
        Merge merchant site data from multiple sources.
        
        Args:
            *sources: Multiple lists of site dicts
            key_field: Field to use as unique key
        
        Returns:
            (merged_list, fusion_result)
        """
        seen: Dict[str, Dict] = {}
        duplicates = 0
        conflicts = 0
        source_counts = {}
        
        for idx, source in enumerate(sources):
            source_name = f"source_{idx}"
            source_counts[source_name] = len(source)
            
            for item in source:
                key = item.get(key_field, "").lower().strip()
                if not key:
                    continue
                
                if key in seen:
                    duplicates += 1
                    # Resolve conflict - prefer higher quality data
                    existing = seen[key]
                    merged = self._resolve_conflict(existing, item)
                    if merged != existing:
                        conflicts += 1
                        seen[key] = merged
                else:
                    seen[key] = item
        
        merged = list(seen.values())
        
        result = FusionResult(
            merged_count=len(merged),
            duplicates_removed=duplicates,
            conflicts_resolved=conflicts,
            source_stats=source_counts
        )
        
        self._merge_history.append({
            "timestamp": time.time(),
            "result": result
        })
        
        return merged, result
    
    def merge_bin_databases(self, *sources: List[Dict]) -> Tuple[List[Dict], FusionResult]:
        """Merge BIN databases from multiple sources."""
        return self.merge_merchant_sites(*sources, key_field="bin")
    
    def _resolve_conflict(self, existing: Dict, new: Dict) -> Dict:
        """
        Resolve conflict between two records.
        Strategy: prefer record with more fields / higher quality indicators.
        """
        # Score each record
        existing_score = self._quality_score(existing)
        new_score = self._quality_score(new)
        
        if new_score > existing_score:
            return new
        return existing
    
    def _quality_score(self, record: Dict) -> float:
        """Calculate quality score for a record."""
        score = 0.0
        
        # More fields = higher quality
        score += len(record) * 0.1
        
        # Specific quality indicators
        if record.get("notes"):
            score += 0.5
        if record.get("success_rate"):
            score += 0.3
        if record.get("recommended_targets"):
            score += 0.4
        if record.get("three_ds_rate") is not None:
            score += 0.3
        
        return score
    
    def deduplicate(self, data: List[Dict], key_field: str) -> Tuple[List[Dict], int]:
        """
        Remove duplicates from a dataset.
        
        Returns:
            (deduplicated_list, duplicates_removed_count)
        """
        seen = set()
        result = []
        duplicates = 0
        
        for item in data:
            key = str(item.get(key_field, "")).lower().strip()
            if key and key not in seen:
                seen.add(key)
                result.append(item)
            else:
                duplicates += 1
        
        return result, duplicates


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 INTELLIGENT CACHE MANAGER — Smart caching with TTL and invalidation
# ═══════════════════════════════════════════════════════════════════════════════

from pathlib import Path
import hashlib


@dataclass
class CacheEntry:
    """A cache entry with metadata."""
    key: str
    data: Any
    created_at: float
    ttl_seconds: int
    hits: int = 0
    last_accessed: float = 0


class IntelligentCacheManager:
    """
    V7.6 Intelligent Cache Manager - Smart caching with TTL,
    automatic invalidation, and persistence.
    """
    
    DEFAULT_TTL = 86400  # 24 hours
    
    def __init__(self, cache_dir: str = "/opt/titan/state/dynamic_cache"):
        self._cache: Dict[str, CacheEntry] = {}
        self._cache_dir = Path(cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._stats = {"hits": 0, "misses": 0, "evictions": 0}
        self._load_persistent_cache()
    
    def _load_persistent_cache(self):
        """Load cached data from disk."""
        try:
            for cache_file in self._cache_dir.glob("*.json"):
                try:
                    with open(cache_file) as f:
                        data = json.load(f)
                        if self._is_entry_valid(data):
                            self._cache[data["key"]] = CacheEntry(
                                key=data["key"],
                                data=data["data"],
                                created_at=data["created_at"],
                                ttl_seconds=data.get("ttl_seconds", self.DEFAULT_TTL),
                                hits=data.get("hits", 0),
                                last_accessed=data.get("last_accessed", 0)
                            )
                except (json.JSONDecodeError, KeyError):
                    pass
        except Exception as e:
            logger.warning(f"Failed to load persistent cache: {e}")
    
    def _is_entry_valid(self, entry: Dict) -> bool:
        """Check if cache entry is still valid."""
        created = entry.get("created_at", 0)
        ttl = entry.get("ttl_seconds", self.DEFAULT_TTL)
        return time.time() - created < ttl
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached data."""
        entry = self._cache.get(key)
        
        if entry:
            # Check TTL
            if time.time() - entry.created_at > entry.ttl_seconds:
                self.invalidate(key)
                self._stats["misses"] += 1
                return None
            
            entry.hits += 1
            entry.last_accessed = time.time()
            self._stats["hits"] += 1
            return entry.data
        
        self._stats["misses"] += 1
        return None
    
    def set(self, key: str, data: Any, ttl_seconds: int = None):
        """Set cached data."""
        ttl = ttl_seconds or self.DEFAULT_TTL
        
        entry = CacheEntry(
            key=key,
            data=data,
            created_at=time.time(),
            ttl_seconds=ttl,
            last_accessed=time.time()
        )
        
        self._cache[key] = entry
        
        # Persist to disk
        self._persist_entry(entry)
    
    def _persist_entry(self, entry: CacheEntry):
        """Persist cache entry to disk."""
        try:
            cache_file = self._cache_dir / f"{self._hash_key(entry.key)}.json"
            with open(cache_file, 'w') as f:
                json.dump({
                    "key": entry.key,
                    "data": entry.data,
                    "created_at": entry.created_at,
                    "ttl_seconds": entry.ttl_seconds,
                    "hits": entry.hits,
                    "last_accessed": entry.last_accessed
                }, f)
        except Exception as e:
            logger.warning(f"Failed to persist cache entry: {e}")
    
    def _hash_key(self, key: str) -> str:
        """Generate file-safe hash for cache key."""
        return hashlib.md5(key.encode()).hexdigest()
    
    def invalidate(self, key: str):
        """Invalidate a cache entry."""
        if key in self._cache:
            del self._cache[key]
            self._stats["evictions"] += 1
            
            # Remove from disk
            cache_file = self._cache_dir / f"{self._hash_key(key)}.json"
            if cache_file.exists():
                cache_file.unlink()
    
    def invalidate_pattern(self, pattern: str):
        """Invalidate all entries matching pattern."""
        to_remove = [k for k in self._cache if pattern in k]
        for key in to_remove:
            self.invalidate(key)
    
    def cleanup_expired(self) -> int:
        """Remove expired entries."""
        expired = []
        now = time.time()
        
        for key, entry in self._cache.items():
            if now - entry.created_at > entry.ttl_seconds:
                expired.append(key)
        
        for key in expired:
            self.invalidate(key)
        
        return len(expired)
    
    def get_stats(self) -> Dict:
        """Get cache statistics."""
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total if total > 0 else 0
        
        return {
            "entries": len(self._cache),
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "hit_rate": f"{hit_rate:.1%}",
            "evictions": self._stats["evictions"]
        }


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 DATA ENRICHMENT PIPELINE — Enrich generated data with additional context
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class EnrichmentResult:
    """Result of data enrichment."""
    enriched_count: int
    fields_added: int
    enrichment_sources: List[str]
    processing_time_ms: float


class DataEnrichmentPipeline:
    """
    V7.6 Data Enrichment Pipeline - Enriches generated data
    with additional context from various sources.
    """
    
    # Known enrichment data
    PSP_CHARACTERISTICS = {
        "stripe": {"3ds_rate": 0.15, "avs_strict": True, "velocity_check": True},
        "adyen": {"3ds_rate": 0.25, "avs_strict": True, "velocity_check": True},
        "braintree": {"3ds_rate": 0.30, "avs_strict": True, "velocity_check": True},
        "shopify_payments": {"3ds_rate": 0.10, "avs_strict": False, "velocity_check": False},
        "authorize_net": {"3ds_rate": 0.20, "avs_strict": True, "velocity_check": True},
        "paypal": {"3ds_rate": 0.35, "avs_strict": True, "velocity_check": True},
    }
    
    CATEGORY_RISK_LEVELS = {
        "gaming": "medium", "gift_cards": "high", "digital": "high",
        "electronics": "medium", "fashion": "low", "crypto": "very_high",
        "subscriptions": "low", "travel": "medium", "software": "medium",
    }
    
    def __init__(self):
        self._enrichments_performed = 0
    
    def enrich_merchant_sites(self, sites: List[Dict]) -> Tuple[List[Dict], EnrichmentResult]:
        """
        Enrich merchant site data with additional context.
        """
        t0 = time.time()
        fields_added = 0
        sources = set()
        
        for site in sites:
            # Add PSP characteristics
            psp = site.get("psp", "").lower()
            if psp in self.PSP_CHARACTERISTICS:
                chars = self.PSP_CHARACTERISTICS[psp]
                if "psp_3ds_rate" not in site:
                    site["psp_3ds_rate"] = chars["3ds_rate"]
                    fields_added += 1
                if "psp_avs_strict" not in site:
                    site["psp_avs_strict"] = chars["avs_strict"]
                    fields_added += 1
                sources.add("psp_characteristics")
            
            # Add category risk level
            category = site.get("category", "").lower()
            if category in self.CATEGORY_RISK_LEVELS:
                if "risk_level" not in site:
                    site["risk_level"] = self.CATEGORY_RISK_LEVELS[category]
                    fields_added += 1
                sources.add("category_risk")
            
            # Calculate composite score
            if "composite_score" not in site:
                site["composite_score"] = self._calculate_composite_score(site)
                fields_added += 1
                sources.add("composite_scoring")
        
        elapsed_ms = (time.time() - t0) * 1000
        self._enrichments_performed += 1
        
        return sites, EnrichmentResult(
            enriched_count=len(sites),
            fields_added=fields_added,
            enrichment_sources=list(sources),
            processing_time_ms=round(elapsed_ms, 1)
        )
    
    def enrich_bin_data(self, bins: List[Dict]) -> Tuple[List[Dict], EnrichmentResult]:
        """Enrich BIN data with additional context."""
        t0 = time.time()
        fields_added = 0
        sources = set()
        
        for bin_entry in bins:
            # Add network-specific data
            network = bin_entry.get("network", "").lower()
            if network == "visa":
                if "issuer_country_check" not in bin_entry:
                    bin_entry["issuer_country_check"] = True
                    fields_added += 1
            elif network == "mastercard":
                if "identity_check" not in bin_entry:
                    bin_entry["identity_check"] = True
                    fields_added += 1
            sources.add("network_characteristics")
            
            # Add card level scoring
            card_level = bin_entry.get("card_level", "").lower()
            level_scores = {
                "classic": 50, "gold": 65, "platinum": 80,
                "signature": 90, "infinite": 95, "world_elite": 95
            }
            if "level_score" not in bin_entry:
                bin_entry["level_score"] = level_scores.get(card_level, 60)
                fields_added += 1
                sources.add("card_level_scoring")
        
        elapsed_ms = (time.time() - t0) * 1000
        
        return bins, EnrichmentResult(
            enriched_count=len(bins),
            fields_added=fields_added,
            enrichment_sources=list(sources),
            processing_time_ms=round(elapsed_ms, 1)
        )
    
    def _calculate_composite_score(self, site: Dict) -> int:
        """Calculate composite difficulty score for a site."""
        score = 50  # Base score
        
        # Adjust based on difficulty
        difficulty = site.get("difficulty", "moderate").lower()
        if difficulty == "easy":
            score += 20
        elif difficulty == "hard":
            score -= 20
        
        # Adjust based on 3DS
        three_ds = site.get("three_ds", "conditional").lower()
        if three_ds == "none":
            score += 15
        elif three_ds == "always":
            score -= 25
        
        # Adjust based on fraud engine
        fraud_engine = site.get("fraud_engine", "unknown").lower()
        if fraud_engine in ("none", "basic"):
            score += 15
        elif fraud_engine in ("forter", "riskified"):
            score -= 15
        
        # Adjust based on success rate
        success_rate = site.get("success_rate", 0.5)
        if isinstance(success_rate, (int, float)):
            score += int((success_rate - 0.5) * 40)
        
        return max(0, min(100, score))
    
    def get_stats(self) -> Dict:
        """Get enrichment statistics."""
        return {
            "enrichments_performed": self._enrichments_performed
        }


# Global instances
_quality_validator: Optional[DataQualityValidator] = None
_fusion_engine: Optional[DataFusionEngine] = None
_cache_manager: Optional[IntelligentCacheManager] = None
_enrichment_pipeline: Optional[DataEnrichmentPipeline] = None


def get_quality_validator() -> DataQualityValidator:
    """Get global data quality validator."""
    global _quality_validator
    if _quality_validator is None:
        _quality_validator = DataQualityValidator()
    return _quality_validator


def get_fusion_engine() -> DataFusionEngine:
    """Get global data fusion engine."""
    global _fusion_engine
    if _fusion_engine is None:
        _fusion_engine = DataFusionEngine()
    return _fusion_engine


def get_cache_manager() -> IntelligentCacheManager:
    """Get global intelligent cache manager."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = IntelligentCacheManager()
    return _cache_manager


def get_enrichment_pipeline() -> DataEnrichmentPipeline:
    """Get global data enrichment pipeline."""
    global _enrichment_pipeline
    if _enrichment_pipeline is None:
        _enrichment_pipeline = DataEnrichmentPipeline()
    return _enrichment_pipeline
