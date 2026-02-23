"""
TITAN V7.6 SINGULARITY — Web Intelligence (SerpAPI + Fallback)
Real-time web search for operational intelligence gathering.

Provides:
1. Merchant Recon       — Search for merchant antifraud info, payment processors
2. BIN Intelligence     — Search for BIN/issuer data from public sources
3. Threat Monitoring    — Track antifraud vendor updates and new detections
4. News Monitoring      — Payment security news and fraud prevention updates
5. OSINT Enrichment     — Enrich operational data with public web intelligence

Providers (priority order):
    0. SearXNG (self-hosted)   — private, unlimited, aggregates 70+ engines
    1. SerpAPI (Google Search) — best quality, requires API key
    2. Serper.dev              — fast, cheap alternative
    3. DuckDuckGo (free)       — no API key needed, rate-limited

Architecture:
    - Results cached to /opt/titan/data/web_intel_cache/
    - Cache TTL: 4 hours (web data changes frequently)
    - Thread-safe singleton via get_web_intel()
    - Auto-stores results in vector memory if available
"""

import json
import time
import hashlib
import logging
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone

__version__ = "8.0.0"
__author__ = "Dva.12"

logger = logging.getLogger("TITAN-WEBINTEL")

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

_CACHE_DIR = Path("/opt/titan/data/web_intel_cache")
_CACHE_TTL_HOURS = 4

# Load titan.env if present
_TITAN_ENV = Path("/opt/titan/config/titan.env")
if _TITAN_ENV.exists():
    for _line in _TITAN_ENV.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            _k, _v = _k.strip(), _v.strip()
            if _v and not _v.startswith("REPLACE_WITH") and _k not in os.environ:
                os.environ[_k] = _v


# ═══════════════════════════════════════════════════════════════════════════════
# PROVIDER DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

_SERPAPI_AVAILABLE = False
_SERPER_AVAILABLE = False
_DUCKDUCKGO_AVAILABLE = False

try:
    from serpapi import GoogleSearch as SerpAPISearch
    _SERPAPI_AVAILABLE = True
except ImportError:
    pass

try:
    import requests as _requests
    _SERPER_AVAILABLE = True  # serper.dev uses plain HTTP
except ImportError:
    _requests = None

try:
    from duckduckgo_search import DDGS
    _DUCKDUCKGO_AVAILABLE = True
except ImportError:
    pass


# ═══════════════════════════════════════════════════════════════════════════════
# DATA TYPES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class WebSearchResult:
    """A single web search result."""
    title: str
    url: str
    snippet: str
    source: str = ""        # provider that returned this
    position: int = 0       # rank position
    timestamp: float = 0.0  # when this was fetched


@dataclass
class WebIntelReport:
    """Aggregated web intelligence report."""
    query: str
    results: List[WebSearchResult]
    provider: str
    cached: bool = False
    search_time_ms: float = 0.0
    timestamp: float = 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# CACHE LAYER
# ═══════════════════════════════════════════════════════════════════════════════

def _cache_key(query: str) -> str:
    return hashlib.sha256(query.lower().strip().encode()).hexdigest()[:16]


def _cache_path(query: str) -> Path:
    return _CACHE_DIR / f"{_cache_key(query)}.json"


def _read_cache(query: str) -> Optional[List[Dict]]:
    path = _cache_path(query)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        cached_at = data.get("_cached_at", 0)
        if time.time() - cached_at > _CACHE_TTL_HOURS * 3600:
            return None  # expired
        return data.get("results", [])
    except Exception:
        return None


def _write_cache(query: str, results: List[Dict], provider: str):
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "_cached_at": time.time(),
            "_query": query,
            "_provider": provider,
            "results": results,
        }
        _cache_path(query).write_text(json.dumps(data, indent=2))
    except Exception as e:
        logger.warning(f"Cache write failed: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# SEARCH PROVIDERS
# ═══════════════════════════════════════════════════════════════════════════════

def _search_serpapi(query: str, num_results: int = 5) -> List[Dict]:
    """Search via SerpAPI (Google Search)."""
    api_key = os.getenv("SERPAPI_KEY", os.getenv("SERPAPI_API_KEY", ""))
    if not api_key or not _SERPAPI_AVAILABLE:
        return []

    try:
        params = {
            "q": query,
            "api_key": api_key,
            "num": num_results,
            "engine": "google",
        }
        search = SerpAPISearch(params)
        data = search.get_dict()

        results = []
        for i, item in enumerate(data.get("organic_results", [])[:num_results]):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "source": "serpapi",
                "position": i + 1,
            })
        return results

    except Exception as e:
        logger.warning(f"SerpAPI search failed: {e}")
        return []


def _search_serper(query: str, num_results: int = 5) -> List[Dict]:
    """Search via Serper.dev API."""
    api_key = os.getenv("SERPER_API_KEY", "")
    if not api_key or not _SERPER_AVAILABLE:
        return []

    try:
        resp = _requests.post(
            "https://google.serper.dev/search",
            headers={
                "X-API-KEY": api_key,
                "Content-Type": "application/json",
            },
            json={"q": query, "num": num_results},
            timeout=10,
        )
        if resp.status_code != 200:
            logger.warning(f"Serper API returned {resp.status_code}")
            return []

        data = resp.json()
        results = []
        for i, item in enumerate(data.get("organic", [])[:num_results]):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "source": "serper",
                "position": i + 1,
            })
        return results

    except Exception as e:
        logger.warning(f"Serper search failed: {e}")
        return []


def _search_duckduckgo(query: str, num_results: int = 5) -> List[Dict]:
    """Search via DuckDuckGo (free, no API key)."""
    if not _DUCKDUCKGO_AVAILABLE:
        return []

    try:
        with DDGS() as ddgs:
            raw_results = list(ddgs.text(query, max_results=num_results))

        results = []
        for i, item in enumerate(raw_results[:num_results]):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("href", item.get("link", "")),
                "snippet": item.get("body", item.get("snippet", "")),
                "source": "duckduckgo",
                "position": i + 1,
            })
        return results

    except Exception as e:
        logger.warning(f"DuckDuckGo search failed: {e}")
        return []


def _search_searxng(query: str, num_results: int = 5) -> List[Dict]:
    """Search via self-hosted SearXNG instance (highest priority).
    Deploy via Hostinger Docker Catalog → SearXNG.
    Set TITAN_SEARXNG_URL in titan.env (default: http://127.0.0.1:8888).
    """
    searxng_url = os.getenv("TITAN_SEARXNG_URL", "http://127.0.0.1:8888")
    if not _requests:
        return []

    try:
        resp = _requests.get(
            f"{searxng_url}/search",
            params={
                "q": query,
                "format": "json",
                "categories": "general",
                "language": "en",
                "safesearch": "0",
                "pageno": "1",
            },
            timeout=10,
            headers={"User-Agent": "Titan-WebIntel/8.0"},
        )
        if resp.status_code != 200:
            logger.debug(f"SearXNG returned {resp.status_code}")
            return []

        data = resp.json()
        results = []
        for i, item in enumerate(data.get("results", [])[:num_results]):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": item.get("content", ""),
                "source": "searxng",
                "position": i + 1,
            })
        return results

    except _requests.exceptions.ConnectionError:
        logger.debug("SearXNG not reachable — skipping")
        return []
    except Exception as e:
        logger.warning(f"SearXNG search failed: {e}")
        return []


def _search_urllib_fallback(query: str, num_results: int = 5) -> List[Dict]:
    """
    Last-resort fallback using urllib to hit DuckDuckGo HTML API.
    No external dependencies required.
    """
    import urllib.request
    import urllib.parse
    import re

    try:
        encoded = urllib.parse.quote_plus(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded}"
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

        # Parse results from HTML (basic regex extraction)
        results = []
        # DuckDuckGo HTML results are in <a class="result__a" href="...">
        links = re.findall(
            r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
            html, re.DOTALL
        )
        snippets = re.findall(
            r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>',
            html, re.DOTALL
        )

        for i, (link, title) in enumerate(links[:num_results]):
            # Clean HTML tags from title
            clean_title = re.sub(r'<[^>]+>', '', title).strip()
            clean_snippet = ""
            if i < len(snippets):
                clean_snippet = re.sub(r'<[^>]+>', '', snippets[i]).strip()

            # DuckDuckGo wraps URLs in a redirect
            if "uddg=" in link:
                actual_url = urllib.parse.unquote(
                    link.split("uddg=")[1].split("&")[0]
                )
            else:
                actual_url = link

            results.append({
                "title": clean_title,
                "url": actual_url,
                "snippet": clean_snippet,
                "source": "duckduckgo_html",
                "position": i + 1,
            })

        return results

    except Exception as e:
        logger.warning(f"DuckDuckGo HTML fallback failed: {e}")
        return []


# ═══════════════════════════════════════════════════════════════════════════════
# WEB INTELLIGENCE ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class TitanWebIntel:
    """
    Web intelligence engine for Titan OS.

    Searches the web for real-time operational intelligence using
    multiple providers with automatic fallback.

    Usage:
        intel = get_web_intel()

        # Basic search
        results = intel.search("amazon.com antifraud system 2025")

        # Merchant recon
        report = intel.recon_merchant("shopify.com")

        # BIN intelligence
        report = intel.search_bin_intel("411111")

        # Threat monitoring
        report = intel.monitor_threats("forter")

        # Payment security news
        report = intel.security_news()
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._search_count = 0
        self._cache_hits = 0
        self._provider_order = self._detect_providers()
        logger.info(f"Web Intel initialized. Providers: {self._provider_order}")

    def _detect_providers(self) -> List[str]:
        """Detect available search providers in priority order."""
        providers = []
        # SearXNG is top priority — self-hosted, unlimited, no API key
        if os.getenv("TITAN_SEARXNG_URL") or _requests:
            providers.append("searxng")
        if _SERPAPI_AVAILABLE and os.getenv("SERPAPI_KEY", os.getenv("SERPAPI_API_KEY", "")):
            providers.append("serpapi")
        if _SERPER_AVAILABLE and os.getenv("SERPER_API_KEY", ""):
            providers.append("serper")
        if _DUCKDUCKGO_AVAILABLE:
            providers.append("duckduckgo")
        providers.append("urllib_fallback")  # always available
        return providers

    @property
    def is_available(self) -> bool:
        """Check if any search provider is available."""
        return len(self._provider_order) > 0

    def search(self, query: str, num_results: int = 5,
               use_cache: bool = True) -> List[Dict]:
        """
        Search the web using the best available provider.

        Args:
            query: Search query
            num_results: Max results to return
            use_cache: Whether to use cached results

        Returns:
            List of result dicts with title, url, snippet, source
        """
        # Check cache
        if use_cache:
            cached = _read_cache(query)
            if cached:
                self._cache_hits += 1
                logger.debug(f"Cache hit for: {query[:50]}")
                return cached[:num_results]

        # Try providers in order
        results = []
        provider_used = "none"

        for provider in self._provider_order:
            try:
                if provider == "searxng":
                    results = _search_searxng(query, num_results)
                elif provider == "serpapi":
                    results = _search_serpapi(query, num_results)
                elif provider == "serper":
                    results = _search_serper(query, num_results)
                elif provider == "duckduckgo":
                    results = _search_duckduckgo(query, num_results)
                elif provider == "urllib_fallback":
                    results = _search_urllib_fallback(query, num_results)

                if results:
                    provider_used = provider
                    break

            except Exception as e:
                logger.warning(f"Provider {provider} failed: {e}")
                continue

        # Cache results
        if results:
            _write_cache(query, results, provider_used)
            self._search_count += 1

            # Auto-store in vector memory if available
            self._store_in_vector_memory(query, results)

        return results

    def recon_merchant(self, domain: str) -> WebIntelReport:
        """
        Gather intelligence about a merchant's antifraud and payment setup.
        Runs multiple targeted searches.
        """
        t0 = time.time()
        all_results = []

        queries = [
            f"{domain} payment processor antifraud",
            f"{domain} checkout fraud detection system",
            f'"{domain}" 3D secure payment gateway',
        ]

        for q in queries:
            results = self.search(q, num_results=3)
            all_results.extend(results)

        # Deduplicate by URL
        seen_urls = set()
        unique_results = []
        for r in all_results:
            if r["url"] not in seen_urls:
                seen_urls.add(r["url"])
                unique_results.append(r)

        elapsed = (time.time() - t0) * 1000
        return WebIntelReport(
            query=f"merchant_recon:{domain}",
            results=[WebSearchResult(**r) for r in unique_results[:10]],
            provider="multi",
            search_time_ms=round(elapsed, 2),
            timestamp=time.time(),
        )

    def search_bin_intel(self, bin_number: str) -> WebIntelReport:
        """Search for BIN/issuer intelligence from public sources."""
        t0 = time.time()
        bin6 = bin_number[:6]

        results = self.search(
            f"BIN {bin6} issuing bank card type country",
            num_results=5
        )

        elapsed = (time.time() - t0) * 1000
        return WebIntelReport(
            query=f"bin_intel:{bin6}",
            results=[WebSearchResult(**r) for r in results],
            provider=results[0]["source"] if results else "none",
            search_time_ms=round(elapsed, 2),
            timestamp=time.time(),
        )

    def monitor_threats(self, vendor: str = None) -> WebIntelReport:
        """Monitor antifraud vendor updates and new detection methods."""
        t0 = time.time()

        if vendor:
            query = f"{vendor} antifraud detection update 2025 2026"
        else:
            query = "antifraud detection ecommerce update 2025 2026 new methods"

        results = self.search(query, num_results=5)

        elapsed = (time.time() - t0) * 1000
        return WebIntelReport(
            query=f"threat_monitor:{vendor or 'general'}",
            results=[WebSearchResult(**r) for r in results],
            provider=results[0]["source"] if results else "none",
            search_time_ms=round(elapsed, 2),
            timestamp=time.time(),
        )

    def security_news(self) -> WebIntelReport:
        """Get latest payment security and fraud prevention news."""
        t0 = time.time()

        results = self.search(
            "payment fraud prevention news 2025 2026 ecommerce security",
            num_results=5
        )

        elapsed = (time.time() - t0) * 1000
        return WebIntelReport(
            query="security_news",
            results=[WebSearchResult(**r) for r in results],
            provider=results[0]["source"] if results else "none",
            search_time_ms=round(elapsed, 2),
            timestamp=time.time(),
        )

    def search_antifraud_bypass(self, vendor: str) -> WebIntelReport:
        """Search for known weaknesses or bypass methods for an antifraud vendor."""
        t0 = time.time()

        queries = [
            f"{vendor} antifraud bypass limitations weaknesses",
            f"{vendor} fraud detection false positive rate",
            f"{vendor} ecommerce integration issues",
        ]

        all_results = []
        for q in queries:
            results = self.search(q, num_results=3)
            all_results.extend(results)

        # Deduplicate
        seen = set()
        unique = []
        for r in all_results:
            if r["url"] not in seen:
                seen.add(r["url"])
                unique.append(r)

        elapsed = (time.time() - t0) * 1000
        return WebIntelReport(
            query=f"antifraud_bypass:{vendor}",
            results=[WebSearchResult(**r) for r in unique[:10]],
            provider="multi",
            search_time_ms=round(elapsed, 2),
            timestamp=time.time(),
        )

    def _store_in_vector_memory(self, query: str, results: List[Dict]):
        """Auto-store search results in vector memory for future recall."""
        try:
            from titan_vector_memory import get_vector_memory
            mem = get_vector_memory()
            if not mem.is_available:
                return

            for r in results[:3]:  # Store top 3 results
                content = f"Web search: {query} | {r.get('title', '')} | {r.get('snippet', '')}"
                doc_id = hashlib.sha256(r.get("url", "").encode()).hexdigest()[:16]
                mem.store_knowledge(
                    key=f"web_{doc_id}",
                    content=content,
                    metadata={
                        "source": "web_search",
                        "query": query[:200],
                        "url": r.get("url", ""),
                        "provider": r.get("source", "unknown"),
                    }
                )
        except Exception:
            pass  # Non-critical — don't break search if memory fails

    def get_stats(self) -> Dict:
        """Get web intel statistics."""
        return {
            "available": self.is_available,
            "providers": self._provider_order,
            "primary_provider": self._provider_order[0] if self._provider_order else "none",
            "total_searches": self._search_count,
            "cache_hits": self._cache_hits,
            "serpapi_key_set": bool(os.getenv("SERPAPI_KEY", os.getenv("SERPAPI_API_KEY", ""))),
            "serper_key_set": bool(os.getenv("SERPER_API_KEY", "")),
            "duckduckgo_available": _DUCKDUCKGO_AVAILABLE,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON ACCESS
# ═══════════════════════════════════════════════════════════════════════════════

_web_intel: Optional[TitanWebIntel] = None
_web_lock = threading.Lock()


def get_web_intel() -> TitanWebIntel:
    """Get singleton TitanWebIntel instance."""
    global _web_intel
    with _web_lock:
        if _web_intel is None:
            _web_intel = TitanWebIntel()
    return _web_intel


def is_web_intel_available() -> bool:
    """Check if web intel is operational."""
    try:
        intel = get_web_intel()
        return intel.is_available
    except Exception:
        return False
