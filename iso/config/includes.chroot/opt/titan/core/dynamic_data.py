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
