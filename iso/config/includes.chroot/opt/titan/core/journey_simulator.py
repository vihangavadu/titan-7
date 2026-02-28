#!/usr/bin/env python3
"""
TITAN V8.1 SINGULARITY — Journey Simulator

Simulates realistic multi-site browsing journeys for profile warming.
Generates authentic browsing artifacts by driving a real browser through
natural navigation patterns: search → click → browse → back → new search.

Original: Used Selenium + Chrome. Adapted for Playwright + Camoufox on Linux.

Integration points:
  - referrer_warmup.py: Use as enhanced warmup with real browser execution
  - profile_burner.py: Complements burn cycle with structured journey patterns
  - integration_bridge.py: Call before operation for pre-visit warming
  - temporal_entropy.py: Uses organic_pause() for realistic timing
"""

import random
import time
import logging
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger("TITAN-JOURNEY-SIM")

try:
    from playwright.sync_api import sync_playwright, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    sync_playwright = Page = None
    PLAYWRIGHT_AVAILABLE = False

try:
    from temporal_entropy import get_human_jitter
except ImportError:
    def get_human_jitter(min_ms=8, max_ms=32):
        import secrets
        return (min_ms + secrets.randbelow(max_ms - min_ms + 1)) / 1000.0


# ═══════════════════════════════════════════════════════════════════════════════
# JOURNEY TEMPLATES
# ═══════════════════════════════════════════════════════════════════════════════

JOURNEY_TEMPLATES = {
    "shopper": {
        "description": "E-commerce browsing journey",
        "steps": [
            {"type": "search", "query": "best deals online {year}"},
            {"type": "visit", "url": "https://www.amazon.com", "dwell": (5, 15)},
            {"type": "scroll", "amount": (3, 8)},
            {"type": "visit", "url": "https://www.ebay.com", "dwell": (4, 10)},
            {"type": "search", "query": "product reviews {topic}"},
            {"type": "visit", "url": "https://www.walmart.com", "dwell": (3, 8)},
            {"type": "scroll", "amount": (2, 5)},
        ],
    },
    "researcher": {
        "description": "Information-seeking journey",
        "steps": [
            {"type": "search", "query": "how to {topic}"},
            {"type": "visit", "url": "https://en.wikipedia.org", "dwell": (5, 12)},
            {"type": "scroll", "amount": (4, 10)},
            {"type": "visit", "url": "https://stackoverflow.com", "dwell": (3, 8)},
            {"type": "search", "query": "{topic} tutorial 2024"},
            {"type": "visit", "url": "https://github.com", "dwell": (3, 6)},
        ],
    },
    "casual": {
        "description": "Casual browsing journey",
        "steps": [
            {"type": "visit", "url": "https://www.google.com", "dwell": (2, 4)},
            {"type": "search", "query": "news today"},
            {"type": "visit", "url": "https://www.reddit.com", "dwell": (5, 15)},
            {"type": "scroll", "amount": (5, 12)},
            {"type": "visit", "url": "https://www.youtube.com", "dwell": (8, 20)},
            {"type": "visit", "url": "https://www.weather.com", "dwell": (2, 4)},
        ],
    },
    "professional": {
        "description": "Work-related browsing journey",
        "steps": [
            {"type": "visit", "url": "https://www.linkedin.com", "dwell": (4, 8)},
            {"type": "search", "query": "industry trends {year}"},
            {"type": "visit", "url": "https://www.microsoft.com", "dwell": (3, 6)},
            {"type": "visit", "url": "https://www.salesforce.com", "dwell": (2, 5)},
            {"type": "search", "query": "project management tools"},
            {"type": "visit", "url": "https://www.notion.so", "dwell": (3, 7)},
        ],
    },
    "target_warmup": {
        "description": "Pre-operation target site warming",
        "steps": [
            {"type": "search", "query": "{target_domain} reviews"},
            {"type": "visit", "url": "https://www.google.com", "dwell": (2, 4)},
            {"type": "search", "query": "{target_domain} coupon code"},
            {"type": "visit", "url": "{target_url}", "dwell": (5, 12)},
            {"type": "scroll", "amount": (3, 8)},
            {"type": "visit", "url": "{target_url}", "dwell": (4, 8)},
        ],
    },
}

TOPICS = ["laptop", "phone", "camera", "shoes", "headphones", "software",
          "cooking", "fitness", "travel", "investing", "python", "design"]


class JourneySimulator:
    """
    Drives a real browser through structured browsing journeys.

    Usage:
        sim = JourneySimulator("/opt/titan/profiles/TITAN-XXXX")
        result = sim.run_journey("shopper")
        result = sim.run_journey("target_warmup", target_url="https://store.example.com")
    """

    def __init__(self, profile_path: str = None, headless: bool = True):
        self.profile_path = profile_path
        self.headless = headless
        self._pw = None
        self._browser = None
        self._page = None

    def run_journey(self, journey_type: str = "casual",
                    target_url: str = None,
                    proxy: str = None,
                    num_loops: int = 1) -> Dict[str, Any]:
        """
        Execute a browsing journey.

        Args:
            journey_type: Template name from JOURNEY_TEMPLATES
            target_url: Target URL for target_warmup journey
            proxy: Optional proxy (socks5://host:port)
            num_loops: Number of times to repeat the journey

        Returns:
            Result dict with stats
        """
        if not PLAYWRIGHT_AVAILABLE:
            logger.error("Playwright not installed")
            return {"success": False, "error": "playwright_missing"}

        template = JOURNEY_TEMPLATES.get(journey_type)
        if not template:
            logger.error(f"Unknown journey type: {journey_type}")
            return {"success": False, "error": f"unknown_journey: {journey_type}"}

        results = {"success": False, "steps_completed": 0, "errors": [], "duration": 0}
        start = time.time()

        try:
            self._pw = sync_playwright().start()

            launch_kwargs = {"headless": self.headless}
            if proxy:
                launch_kwargs["proxy"] = {"server": proxy}

            if self.profile_path:
                self._browser = self._pw.firefox.launch_persistent_context(
                    user_data_dir=self.profile_path, **launch_kwargs)
                self._page = self._browser.pages[0] if self._browser.pages else self._browser.new_page()
            else:
                browser = self._pw.firefox.launch(**launch_kwargs)
                self._browser = browser.new_context()
                self._page = self._browser.new_page()

            # Execute journey loops
            topic = random.choice(TOPICS)
            target_domain = ""
            if target_url:
                from urllib.parse import urlparse
                target_domain = urlparse(target_url).hostname or target_url

            for loop in range(num_loops):
                for step in template["steps"]:
                    try:
                        self._execute_step(step, topic=topic,
                                           target_url=target_url,
                                           target_domain=target_domain)
                        results["steps_completed"] += 1
                    except Exception as e:
                        logger.warning(f"Step failed: {step.get('type')}: {e}")
                        results["errors"].append(str(e))

                    time.sleep(get_human_jitter(500, 2000))

            results["success"] = True

        except Exception as e:
            logger.error(f"Journey failed: {e}")
            results["errors"].append(str(e))
        finally:
            self._cleanup()

        results["duration"] = round(time.time() - start, 1)
        logger.info(f"Journey '{journey_type}' complete: {results['steps_completed']} steps, "
                    f"{results['duration']}s")
        return results

    def _execute_step(self, step: Dict, topic: str = "", target_url: str = "",
                      target_domain: str = ""):
        """Execute a single journey step."""
        step_type = step["type"]
        year = "2024"

        if step_type == "visit":
            url = step["url"]
            url = url.replace("{target_url}", target_url or "https://www.google.com")
            dwell_min, dwell_max = step.get("dwell", (3, 8))

            logger.debug(f"Visiting: {url}")
            self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(random.uniform(dwell_min, dwell_max))

        elif step_type == "search":
            query = step["query"]
            query = query.replace("{topic}", topic)
            query = query.replace("{year}", year)
            query = query.replace("{target_domain}", target_domain or "example")

            logger.debug(f"Searching: {query}")
            self._page.goto(f"https://www.google.com/search?q={query}",
                            wait_until="domcontentloaded", timeout=30000)
            time.sleep(random.uniform(2, 5))

        elif step_type == "scroll":
            lo, hi = step.get("amount", (2, 5))
            scrolls = random.randint(lo, hi)
            for _ in range(scrolls):
                self._page.evaluate(f"window.scrollBy(0, {random.randint(100, 500)})")
                time.sleep(random.uniform(0.3, 1.5))

    def _cleanup(self):
        """Clean up browser resources."""
        try:
            if self._browser:
                self._browser.close()
        except Exception:
            pass
        try:
            if self._pw:
                self._pw.stop()
        except Exception:
            pass
        self._browser = None
        self._page = None
        self._pw = None

    def execute_manual_handover(self, countdown: int = 180):
        """
        Stop automation but leave browser open for human takeover.
        Used at checkout phase — operator takes manual control.
        """
        logger.info("INITIATING MANUAL HANDOVER PROTOCOL")
        logger.info(f"Automation ending. Browser remains open for {countdown}s silence window.")
        for i in range(countdown, 0, -1):
            if i % 30 == 0:
                logger.info(f"Silence window: {i}s remaining...")
            time.sleep(1)
        logger.info("HANDOVER COMPLETE. Operator has control.")

    def get_status(self) -> Dict[str, Any]:
        """Return module status."""
        return {
            "available": PLAYWRIGHT_AVAILABLE,
            "journey_templates": list(JOURNEY_TEMPLATES.keys()),
            "version": "8.1",
        }
