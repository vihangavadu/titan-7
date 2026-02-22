#!/usr/bin/env python3
"""
TITAN V8.1 SINGULARITY — Profile Burner

Browser-driven profile aging: launches a real Camoufox/Firefox browser attached
to a profile directory and visits high-trust sites to generate authentic artifacts
(cookies, localStorage, cache, sessionStorage, IndexedDB) that synthetic generation
cannot replicate.

Original: Used Selenium + Chrome. Adapted for Playwright + Camoufox on Linux.

Integration points:
  - genesis_core.py: Call after forge_profile() to add real browser artifacts
  - advanced_profile_generator.py: Complement synthetic profiles with real visits
  - referrer_warmup.py: Use as alternative real-browser warmup engine
  - temporal_entropy.py: Use EntropyGenerator.organic_pause() between visits
  - time_dilator.py: Run after burn to densify backdated history
"""

import os
import time
import random
import logging
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List

logger = logging.getLogger("TITAN-PROFILE-BURNER")

# Optional Playwright — graceful fallback
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    sync_playwright = None
    PLAYWRIGHT_AVAILABLE = False

# Optional temporal entropy integration
try:
    from temporal_entropy import EntropyGenerator, get_human_jitter
    ENTROPY_AVAILABLE = True
except ImportError:
    EntropyGenerator = None
    ENTROPY_AVAILABLE = False
    def get_human_jitter(min_ms=8, max_ms=32):
        import secrets
        return (min_ms + secrets.randbelow(max_ms - min_ms + 1)) / 1000.0


# ═══════════════════════════════════════════════════════════════════════════════
# HIGH-TRUST SITE POOL
# ═══════════════════════════════════════════════════════════════════════════════

BURN_SITES = [
    {"url": "https://www.google.com", "title": "Google", "actions": ["search"], "dwell": (3, 8)},
    {"url": "https://www.youtube.com", "title": "YouTube", "actions": ["scroll"], "dwell": (5, 15)},
    {"url": "https://www.amazon.com", "title": "Amazon", "actions": ["scroll", "click"], "dwell": (5, 12)},
    {"url": "https://www.reddit.com", "title": "Reddit", "actions": ["scroll"], "dwell": (4, 10)},
    {"url": "https://en.wikipedia.org", "title": "Wikipedia", "actions": ["scroll", "click"], "dwell": (3, 8)},
    {"url": "https://www.github.com", "title": "GitHub", "actions": ["scroll"], "dwell": (3, 6)},
    {"url": "https://stackoverflow.com", "title": "Stack Overflow", "actions": ["scroll"], "dwell": (3, 8)},
    {"url": "https://www.bbc.com", "title": "BBC", "actions": ["scroll", "click"], "dwell": (4, 10)},
    {"url": "https://www.netflix.com", "title": "Netflix", "actions": ["scroll"], "dwell": (2, 5)},
    {"url": "https://www.linkedin.com", "title": "LinkedIn", "actions": ["scroll"], "dwell": (3, 7)},
    {"url": "https://www.microsoft.com", "title": "Microsoft", "actions": ["scroll"], "dwell": (2, 5)},
    {"url": "https://www.apple.com", "title": "Apple", "actions": ["scroll"], "dwell": (2, 5)},
    {"url": "https://www.weather.com", "title": "Weather", "actions": ["scroll"], "dwell": (2, 4)},
    {"url": "https://www.nytimes.com", "title": "NY Times", "actions": ["scroll"], "dwell": (4, 10)},
    {"url": "https://www.ebay.com", "title": "eBay", "actions": ["scroll", "click"], "dwell": (4, 8)},
]


class ProfileBurner:
    """
    Launches a real browser session attached to a profile to generate
    authentic browsing artifacts that pass forensic analysis.

    Usage:
        burner = ProfileBurner("/opt/titan/profiles/TITAN-XXXX")
        result = burner.burn(num_sites=10)
    """

    def __init__(self, profile_path: str, headless: bool = True, sites: List[Dict] = None):
        self.profile_path = Path(profile_path)
        self.headless = headless
        self.sites = sites or BURN_SITES
        self.entropy = EntropyGenerator() if ENTROPY_AVAILABLE else None
        self._browser = None
        self._context = None
        self._page = None

    def burn(self, num_sites: int = 10, proxy: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute the burn cycle: visit sites, generate real artifacts.

        Args:
            num_sites: Number of sites to visit
            proxy: Optional proxy URL (socks5://host:port)

        Returns:
            Result dict with stats
        """
        if not PLAYWRIGHT_AVAILABLE:
            logger.error("Playwright not available. Install: pip install playwright")
            return {"success": False, "error": "playwright_missing"}

        if not self.profile_path.exists():
            logger.error(f"Profile path not found: {self.profile_path}")
            return {"success": False, "error": "profile_not_found"}

        results = {
            "success": False,
            "sites_visited": 0,
            "cookies_generated": 0,
            "errors": [],
            "duration_seconds": 0,
        }
        start = time.time()

        try:
            pw = sync_playwright().start()

            # Launch Firefox/Camoufox with the target profile
            launch_args = ["--no-remote"]
            browser_kwargs = {
                "headless": self.headless,
                "args": launch_args,
            }

            # Try Camoufox first, fall back to Firefox
            try:
                self._browser = pw.firefox.launch_persistent_context(
                    user_data_dir=str(self.profile_path),
                    **browser_kwargs,
                    proxy={"server": proxy} if proxy else None,
                )
                self._page = self._browser.pages[0] if self._browser.pages else self._browser.new_page()
            except Exception as e:
                logger.error(f"Browser launch failed: {e}")
                results["errors"].append(str(e))
                pw.stop()
                return results

            # Visit sites
            visit_order = random.sample(self.sites, min(num_sites, len(self.sites)))
            for site in visit_order:
                try:
                    self._visit_site(site)
                    results["sites_visited"] += 1
                except Exception as e:
                    logger.warning(f"Failed to visit {site['url']}: {e}")
                    results["errors"].append(f"{site['url']}: {e}")

                # Organic pause between sites
                if self.entropy:
                    self.entropy.organic_pause()
                else:
                    time.sleep(random.uniform(2, 6))

            # Count cookies generated
            try:
                cookies = self._browser.cookies()
                results["cookies_generated"] = len(cookies)
            except Exception:
                pass

            results["success"] = True

        except Exception as e:
            logger.error(f"Burn cycle failed: {e}")
            results["errors"].append(str(e))
        finally:
            try:
                if self._browser:
                    self._browser.close()
            except Exception:
                pass
            try:
                pw.stop()
            except Exception:
                pass

        results["duration_seconds"] = round(time.time() - start, 1)
        logger.info(f"Burn complete: {results['sites_visited']} sites, "
                    f"{results['cookies_generated']} cookies, {results['duration_seconds']}s")
        return results

    def _visit_site(self, site: Dict):
        """Visit a single site and perform actions."""
        url = site["url"]
        actions = site.get("actions", ["scroll"])
        dwell_min, dwell_max = site.get("dwell", (3, 8))

        logger.info(f"Visiting: {url}")
        self._page.goto(url, wait_until="domcontentloaded", timeout=30000)

        # Dwell time
        dwell = random.uniform(dwell_min, dwell_max)

        for action in actions:
            if action == "scroll":
                self._human_scroll()
            elif action == "search":
                self._human_search()
            elif action == "click":
                self._human_click()

            time.sleep(get_human_jitter(200, 800))

        time.sleep(dwell)

    def _human_scroll(self):
        """Scroll the page like a human."""
        try:
            scrolls = random.randint(2, 6)
            for _ in range(scrolls):
                amount = random.randint(100, 500)
                self._page.evaluate(f"window.scrollBy(0, {amount})")
                time.sleep(random.uniform(0.3, 1.5))
        except Exception:
            pass

    def _human_search(self):
        """Perform a Google search if on Google."""
        try:
            queries = ["weather today", "best restaurants near me", "latest news",
                       "how to cook pasta", "movie reviews 2024", "workout routine"]
            query = random.choice(queries)
            search_input = self._page.query_selector('textarea[name="q"], input[name="q"]')
            if search_input:
                search_input.click()
                time.sleep(random.uniform(0.5, 1))
                for char in query:
                    search_input.type(char)
                    time.sleep(random.uniform(0.05, 0.15))
                time.sleep(random.uniform(0.5, 1.5))
                search_input.press("Enter")
                time.sleep(random.uniform(2, 4))
        except Exception:
            pass

    def _human_click(self):
        """Click a random link on the page."""
        try:
            links = self._page.query_selector_all("a[href]")
            if links and len(links) > 3:
                link = random.choice(links[1:min(10, len(links))])
                link.click(timeout=5000)
                time.sleep(random.uniform(2, 5))
                self._page.go_back(timeout=10000)
        except Exception:
            pass

    def get_status(self) -> Dict[str, Any]:
        """Return module status."""
        return {
            "available": PLAYWRIGHT_AVAILABLE,
            "entropy_available": ENTROPY_AVAILABLE,
            "profile_exists": self.profile_path.exists(),
            "site_pool_size": len(self.sites),
            "version": "8.1",
        }
