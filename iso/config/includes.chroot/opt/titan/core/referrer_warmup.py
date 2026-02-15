"""
TITAN V7.0 SINGULARITY - Referrer Chain Warmup
Creates organic navigation paths with valid document.referrer chains

Problem: Direct URL navigation creates empty document.referrer = bot signature
Solution: Navigate through search engines to create valid referrer chains

This module provides:
1. Google search navigation
2. Organic click-through to target
3. Valid referrer chain creation
4. Pre-checkout warmup navigation
"""

import sys
import random
import time
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse, quote_plus

logger = logging.getLogger("TITAN-V7-WARMUP")


@dataclass
class WarmupStep:
    """Single step in warmup navigation"""
    url: str
    wait_seconds: float
    action: str  # "navigate", "search", "click", "scroll"
    selector: Optional[str] = None
    search_query: Optional[str] = None


@dataclass
class WarmupPlan:
    """Complete warmup navigation plan"""
    target_domain: str
    target_url: str
    steps: List[WarmupStep] = field(default_factory=list)
    total_duration: float = 0.0


class ReferrerWarmup:
    """
    Creates organic navigation paths to establish valid referrer chains.
    
    Flow:
    1. Start at Google
    2. Search for target-related query
    3. Click organic result (not ad)
    4. Navigate naturally to target page
    
    This creates:
    - google.com -> target.com (valid referrer)
    - Natural search history
    - Organic discovery pattern
    """
    
    # Search queries by target type
    SEARCH_QUERIES = {
        "amazon.com": [
            "amazon deals today",
            "amazon electronics sale",
            "buy laptop amazon",
            "amazon prime deals",
            "amazon shopping",
        ],
        "ebay.com": [
            "ebay electronics",
            "buy on ebay",
            "ebay deals",
            "ebay auction items",
        ],
        "walmart.com": [
            "walmart online shopping",
            "walmart deals",
            "buy electronics walmart",
        ],
        "bestbuy.com": [
            "best buy electronics",
            "best buy laptop deals",
            "best buy tv sale",
        ],
        "target.com": [
            "target shopping online",
            "target deals today",
            "target electronics",
        ],
        "default": [
            "{domain} shopping",
            "{domain} deals",
            "buy from {domain}",
            "{domain} online store",
        ]
    }
    
    # Pre-warmup sites (build general browsing history)
    WARMUP_SITES = [
        ("https://www.google.com", 3, "Start at Google"),
        ("https://www.youtube.com", 5, "Visit YouTube briefly"),
        ("https://www.reddit.com", 4, "Check Reddit"),
        ("https://news.ycombinator.com", 3, "Tech news"),
        ("https://weather.com", 2, "Check weather"),
    ]
    
    def __init__(self, humanize_timing: bool = True):
        """
        Initialize warmup engine.
        
        Args:
            humanize_timing: Add random delays to simulate human behavior
        """
        self.humanize = humanize_timing
    
    def _get_search_query(self, domain: str) -> str:
        """Get appropriate search query for domain"""
        queries = self.SEARCH_QUERIES.get(domain, self.SEARCH_QUERIES["default"])
        query = random.choice(queries)
        return query.format(domain=domain.replace(".com", "").replace(".co.uk", ""))
    
    def _humanize_delay(self, base_seconds: float) -> float:
        """Add human-like randomness to timing"""
        if not self.humanize:
            return base_seconds
        # Add 20-50% random variation
        variation = base_seconds * random.uniform(0.2, 0.5)
        return base_seconds + variation
    
    def create_warmup_plan(self, target_url: str, 
                           include_pre_warmup: bool = True) -> WarmupPlan:
        """
        Create a warmup navigation plan for target URL.
        
        Args:
            target_url: Final destination URL
            include_pre_warmup: Include general browsing before target
            
        Returns:
            WarmupPlan with navigation steps
        """
        parsed = urlparse(target_url)
        domain = parsed.netloc.replace("www.", "")
        
        plan = WarmupPlan(
            target_domain=domain,
            target_url=target_url
        )
        
        # Pre-warmup: General browsing
        if include_pre_warmup:
            # Pick 2-3 random warmup sites
            sites = random.sample(self.WARMUP_SITES, min(3, len(self.WARMUP_SITES)))
            for url, duration, desc in sites:
                plan.steps.append(WarmupStep(
                    url=url,
                    wait_seconds=self._humanize_delay(duration),
                    action="navigate"
                ))
        
        # Step 1: Go to Google
        plan.steps.append(WarmupStep(
            url="https://www.google.com",
            wait_seconds=self._humanize_delay(2),
            action="navigate"
        ))
        
        # Step 2: Search for target
        search_query = self._get_search_query(domain)
        google_search_url = f"https://www.google.com/search?q={quote_plus(search_query)}"
        
        plan.steps.append(WarmupStep(
            url=google_search_url,
            wait_seconds=self._humanize_delay(3),
            action="search",
            search_query=search_query
        ))
        
        # Step 3: Click organic result — navigate to domain homepage
        homepage = f"https://www.{domain}"
        plan.steps.append(WarmupStep(
            url=homepage,
            wait_seconds=self._humanize_delay(5),
            action="click",
            selector=f'a[href*="{domain}"]'
        ))
        
        # Step 4: Navigate to target (if different from homepage)
        if target_url != homepage and target_url != f"{homepage}/":
            plan.steps.append(WarmupStep(
                url=target_url,
                wait_seconds=self._humanize_delay(3),
                action="navigate"
            ))
        
        # Calculate total duration
        plan.total_duration = sum(step.wait_seconds for step in plan.steps)
        
        return plan
    
    def execute_with_playwright(self, plan: WarmupPlan, page) -> bool:
        """
        Execute warmup plan using Playwright page.
        
        Args:
            plan: WarmupPlan to execute
            page: Playwright page object
            
        Returns:
            True if successful
        """
        logger.info(f"Executing warmup plan for {plan.target_domain}")
        logger.info(f"Total steps: {len(plan.steps)}, Est. duration: {plan.total_duration:.0f}s")
        
        try:
            for i, step in enumerate(plan.steps):
                logger.info(f"Step {i+1}/{len(plan.steps)}: {step.action} -> {step.url[:50]}...")
                
                if step.action == "navigate":
                    page.goto(step.url, wait_until="domcontentloaded")
                
                elif step.action == "search":
                    # Go to Google and perform search
                    page.goto("https://www.google.com", wait_until="domcontentloaded")
                    time.sleep(1)
                    
                    # Type search query character-by-character for realism
                    search_box = page.locator('textarea[name="q"], input[name="q"]').first
                    if search_box:
                        search_box.click()
                        for char in step.search_query:
                            search_box.press(char)
                            time.sleep(random.uniform(0.05, 0.15))
                        time.sleep(random.uniform(0.3, 0.8))
                        search_box.press("Enter")
                        page.wait_for_load_state("domcontentloaded")
                
                elif step.action == "click":
                    # Click an actual organic search result link on the SERP
                    # Google wraps results in <a> tags with data-ved attributes
                    # Clicking these creates a proper referrer via Google's redirect
                    clicked = False
                    if step.selector:
                        try:
                            # Try multiple organic result selectors (Google changes these)
                            for selector in [
                                f'#search a[href*="{step.url.split("//")[-1].split("/")[0]}"]',
                                f'a[href*="{step.url.split("//")[-1].split("/")[0]}"]',
                                '#search .g a',
                                step.selector,
                            ]:
                                try:
                                    link = page.locator(selector).first
                                    if link and link.is_visible():
                                        link.click()
                                        page.wait_for_load_state("domcontentloaded")
                                        clicked = True
                                        break
                                except Exception:
                                    continue
                        except Exception:
                            pass
                    
                    if not clicked:
                        # Last resort: direct navigation (no referrer, but continues flow)
                        logger.warning(f"Could not click organic result, falling back to direct nav")
                        page.goto(step.url, wait_until="domcontentloaded")
                
                # Wait between steps
                time.sleep(step.wait_seconds)
                
                # Random scroll to simulate reading
                if random.random() > 0.3:
                    scroll_amount = random.randint(200, 600)
                    page.evaluate(f"window.scrollBy(0, {scroll_amount})")
                    time.sleep(random.uniform(0.5, 1.5))
            
            logger.info("Warmup complete - referrer chain established")
            return True
            
        except Exception as e:
            logger.error(f"Warmup failed: {e}")
            return False
    
    def get_manual_instructions(self, plan: WarmupPlan) -> str:
        """
        Get manual instructions for operator to follow.
        
        Returns human-readable navigation instructions.
        """
        instructions = []
        instructions.append("=" * 60)
        instructions.append("REFERRER CHAIN WARMUP - MANUAL INSTRUCTIONS")
        instructions.append("=" * 60)
        instructions.append(f"Target: {plan.target_url}")
        instructions.append(f"Estimated time: {plan.total_duration:.0f} seconds")
        instructions.append("")
        
        for i, step in enumerate(plan.steps):
            wait_str = f"(wait ~{step.wait_seconds:.0f}s)"
            
            if step.action == "navigate":
                instructions.append(f"{i+1}. Navigate to: {step.url} {wait_str}")
            elif step.action == "search":
                instructions.append(f"{i+1}. Search Google for: \"{step.search_query}\" {wait_str}")
            elif step.action == "click":
                instructions.append(f"{i+1}. Click organic result to: {step.url} {wait_str}")
            
            instructions.append(f"   - Scroll page naturally")
            instructions.append(f"   - Move mouse around")
            instructions.append("")
        
        instructions.append("=" * 60)
        instructions.append("After completing these steps, your referrer chain is valid.")
        instructions.append("Proceed with normal checkout flow.")
        instructions.append("=" * 60)
        
        return "\n".join(instructions)


def create_warmup_plan(target_url: str) -> WarmupPlan:
    """Convenience function to create warmup plan"""
    warmup = ReferrerWarmup()
    return warmup.create_warmup_plan(target_url)


def get_warmup_instructions(target_url: str) -> str:
    """Get manual warmup instructions for target"""
    warmup = ReferrerWarmup()
    plan = warmup.create_warmup_plan(target_url)
    return warmup.get_manual_instructions(plan)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) < 2:
        print("Usage: python referrer_warmup.py <target_url>")
        sys.exit(1)
    target = sys.argv[1]
    warmup = ReferrerWarmup()
    plan = warmup.create_warmup_plan(target)
    print(f"Target: {target}")
    print(f"Steps: {len(plan.steps)} | Duration: {plan.total_duration:.0f}s")
    print(warmup.get_manual_instructions(plan))
