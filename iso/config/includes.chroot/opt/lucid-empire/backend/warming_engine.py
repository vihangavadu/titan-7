"""
LUCID EMPIRE: Target Warming Engine
Objective: Visit target website during aging period to build browsing history
Classification: LEVEL 6 AGENCY

Note: Uses Playwright for browser-based warming. Falls back to requests-based
warming if Playwright is not available.
"""

import asyncio
import random
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import Playwright, fall back to requests-based approach
try:
    from playwright.async_api import async_playwright, Browser, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright not installed. Using requests-based warming fallback.")

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class TargetWarmingEngine:
    """
    Simulates realistic browsing behavior for target website.
    
    Creates believable history by:
    - Visiting target site multiple times over aging period
    - Simulating cart abandonment behavior
    - Generating natural visit patterns
    - Recording all visits for history injection
    """
    
    def __init__(self, headless: bool = True):
        """
        Initialize warming engine
        
        Args:
            headless: Run browser in headless mode
        """
        self.headless = headless
        self.visit_history: List[Dict[str, Any]] = []
        
        # User agents for variety
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        ]
    
    async def warm_target_async(
        self,
        target_url: str,
        target_product: Optional[str] = None,
        aging_days: int = 60,
        visit_count: int = 5,
        proxy: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Warm target site with multiple visits using Playwright
        
        Args:
            target_url: The target website URL
            target_product: Optional product page URL
            aging_days: Number of days to simulate aging
            visit_count: Number of visits to simulate
            proxy: Optional proxy string
            
        Returns:
            Dictionary with visit history and status
        """
        if not PLAYWRIGHT_AVAILABLE:
            return await self._warm_target_fallback(target_url, aging_days, visit_count)
        
        self.visit_history = []
        
        try:
            async with async_playwright() as p:
                # Configure browser
                browser_args = {
                    'headless': self.headless,
                }
                
                if proxy:
                    browser_args['proxy'] = {'server': proxy}
                
                browser = await p.chromium.launch(**browser_args)
                
                # Create context with realistic settings
                context = await browser.new_context(
                    user_agent=random.choice(self.user_agents),
                    viewport={'width': 1920, 'height': 1080},
                    locale='en-US',
                )
                
                page = await context.new_page()
                
                # Simulate visits over the aging period
                visit_times = self._generate_visit_times(aging_days, visit_count)
                
                for i, visit_time in enumerate(visit_times):
                    try:
                        logger.info(f"Warming visit {i+1}/{len(visit_times)} for {target_url}")
                        
                        # Visit main page
                        await self._perform_visit(page, target_url, visit_time)
                        
                        # If product URL provided, visit it too (simulating browsing)
                        if target_product and i > 0:
                            await self._perform_visit(page, target_product, visit_time)
                            
                            # Simulate cart abandonment on some visits
                            if i >= len(visit_times) - 3:
                                await self._simulate_cart_interaction(page, visit_time)
                        
                        # Random delay between actions
                        await asyncio.sleep(random.uniform(0.5, 2.0))
                        
                    except Exception as e:
                        logger.warning(f"Visit {i+1} failed: {e}")
                
                await browser.close()
            
            logger.info(f"Warming complete: {len(self.visit_history)} visits recorded")
            
            return {
                'success': True,
                'target_url': target_url,
                'visits': len(self.visit_history),
                'history': self.visit_history,
                'aging_days': aging_days,
                'timestamp': datetime.now().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Warming failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'history': self.visit_history,
            }
    
    async def _perform_visit(
        self, 
        page: 'Page', 
        url: str, 
        visit_time: datetime
    ) -> None:
        """
        Perform a single page visit with human-like behavior
        """
        try:
            # Navigate to page
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            
            # Wait for page to settle
            await asyncio.sleep(random.uniform(1, 3))
            
            # Scroll behavior (human-like)
            scroll_steps = random.randint(2, 5)
            for _ in range(scroll_steps):
                await page.evaluate(f'window.scrollBy(0, {random.randint(200, 500)})')
                await asyncio.sleep(random.uniform(0.3, 1.0))
            
            # Maybe click a random link
            if random.random() > 0.7:
                try:
                    links = await page.query_selector_all('a[href]')
                    if links:
                        link = random.choice(links[:10])  # Pick from first 10 links
                        await link.click(timeout=5000)
                        await asyncio.sleep(random.uniform(1, 2))
                        await page.go_back()
                except:
                    pass
            
            # Record visit
            self.visit_history.append({
                'url': url,
                'title': await page.title() or url,
                'timestamp': visit_time.isoformat(),
                'visit_count': 1,
                'action': 'browse',
                'duration_seconds': random.randint(30, 180),
            })
            
        except Exception as e:
            logger.warning(f"Visit to {url} failed: {e}")
    
    async def _simulate_cart_interaction(
        self, 
        page: 'Page', 
        visit_time: datetime
    ) -> None:
        """
        Simulate adding to cart and abandoning (builds trust signals)
        """
        try:
            # Look for add to cart button
            add_to_cart_selectors = [
                'button:has-text("Add to Cart")',
                'button:has-text("Add to Basket")',
                '[data-action="add-to-cart"]',
                '.add-to-cart',
                '#add-to-cart-button',
            ]
            
            for selector in add_to_cart_selectors:
                try:
                    button = await page.query_selector(selector)
                    if button:
                        await button.click(timeout=5000)
                        await asyncio.sleep(random.uniform(1, 2))
                        
                        self.visit_history.append({
                            'url': page.url,
                            'title': await page.title() or 'Cart Action',
                            'timestamp': visit_time.isoformat(),
                            'action': 'add_to_cart',
                            'abandoned': True,
                        })
                        
                        logger.info("Cart interaction simulated")
                        break
                except:
                    continue
                    
        except Exception as e:
            logger.debug(f"Cart simulation failed: {e}")
    
    async def _warm_target_fallback(
        self,
        target_url: str,
        aging_days: int,
        visit_count: int
    ) -> Dict[str, Any]:
        """
        Fallback warming using requests (no browser automation)
        Generates synthetic visit history
        """
        logger.info("Using fallback warming (no browser)")
        
        self.visit_history = []
        visit_times = self._generate_visit_times(aging_days, visit_count)
        
        for i, visit_time in enumerate(visit_times):
            # Just generate history entries without actual visits
            self.visit_history.append({
                'url': target_url,
                'title': f'Target Site Visit {i+1}',
                'timestamp': visit_time.isoformat(),
                'visit_count': random.randint(1, 3),
                'action': 'browse',
                'duration_seconds': random.randint(30, 180),
                'synthetic': True,  # Mark as synthetic
            })
            
            # Add cart abandonment for recent visits
            if i >= visit_count - 3:
                self.visit_history.append({
                    'url': f'{target_url}/cart',
                    'title': 'Shopping Cart',
                    'timestamp': (visit_time + timedelta(minutes=5)).isoformat(),
                    'action': 'cart_view',
                    'abandoned': True,
                    'synthetic': True,
                })
        
        return {
            'success': True,
            'target_url': target_url,
            'visits': len(self.visit_history),
            'history': self.visit_history,
            'aging_days': aging_days,
            'mode': 'fallback',
            'timestamp': datetime.now().isoformat(),
        }
    
    def _generate_visit_times(
        self, 
        aging_days: int, 
        visit_count: int
    ) -> List[datetime]:
        """
        Generate realistic visit timestamps spread over aging period
        
        Pattern:
        - 1 visit 3 days ago
        - 1 visit 1 day ago  
        - 1 visit 5 hours ago
        - Additional visits spread throughout aging period
        """
        now = datetime.now()
        visit_times = []
        
        # Required visits (from desired outcome)
        visit_times.append(now - timedelta(days=3, hours=random.randint(2, 8)))
        visit_times.append(now - timedelta(days=1, hours=random.randint(1, 12)))
        visit_times.append(now - timedelta(hours=5, minutes=random.randint(0, 30)))
        
        # Additional visits spread throughout aging period
        remaining_visits = max(0, visit_count - 3)
        for _ in range(remaining_visits):
            days_back = random.randint(4, aging_days)
            hours_back = random.randint(0, 23)
            visit_times.append(now - timedelta(days=days_back, hours=hours_back))
        
        # Sort chronologically (oldest first)
        visit_times.sort()
        
        return visit_times
    
    def warm_target_sync(
        self,
        target_url: str,
        target_product: Optional[str] = None,
        aging_days: int = 60,
        visit_count: int = 5,
        proxy: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Synchronous wrapper for warm_target_async
        """
        return asyncio.run(
            self.warm_target_async(
                target_url, 
                target_product, 
                aging_days, 
                visit_count,
                proxy
            )
        )
    
    def generate_synthetic_history(
        self,
        target_url: str,
        aging_days: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Generate synthetic browsing history for the target site
        without actually visiting it
        
        Args:
            target_url: Target website URL
            aging_days: Number of days to generate history for
            
        Returns:
            List of history entries ready for Firefox injection
        """
        history = []
        now = datetime.now()
        
        # Parse domain from URL
        from urllib.parse import urlparse
        parsed = urlparse(target_url)
        domain = parsed.netloc
        
        # Generate visits over aging period
        visit_days = [3, 1]  # Required: 3 days ago, 1 day ago
        visit_days.extend(random.sample(range(4, aging_days), min(5, aging_days - 4)))
        
        for days_back in sorted(visit_days, reverse=True):
            visit_time = now - timedelta(
                days=days_back,
                hours=random.randint(8, 22),
                minutes=random.randint(0, 59)
            )
            
            # Main page visit
            history.append({
                'url': target_url,
                'title': f'{domain.replace("www.", "").title()} - Homepage',
                'timestamp': visit_time.isoformat(),
                'visit_count': random.randint(1, 3),
            })
            
            # Product page (if recent)
            if days_back <= 3:
                product_time = visit_time + timedelta(minutes=random.randint(5, 20))
                history.append({
                    'url': f'{target_url}/product/item-{random.randint(1000, 9999)}',
                    'title': f'Product Detail - {domain}',
                    'timestamp': product_time.isoformat(),
                    'visit_count': 1,
                })
                
                # Cart view (abandonment)
                cart_time = product_time + timedelta(minutes=random.randint(2, 10))
                history.append({
                    'url': f'{target_url}/cart',
                    'title': f'Shopping Cart - {domain}',
                    'timestamp': cart_time.isoformat(),
                    'visit_count': 1,
                })
        
        # Add 5 hours ago visit
        recent_time = now - timedelta(hours=5, minutes=random.randint(0, 30))
        history.append({
            'url': target_url,
            'title': f'{domain.replace("www.", "").title()} - Homepage',
            'timestamp': recent_time.isoformat(),
            'visit_count': 1,
        })
        
        logger.info(f"Generated {len(history)} synthetic history entries for {target_url}")
        return history


# Convenience function
def warm_target(
    target_url: str,
    target_product: Optional[str] = None,
    aging_days: int = 60,
    visit_count: int = 5,
    proxy: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience function to warm a target site
    """
    engine = TargetWarmingEngine(headless=True)
    return engine.warm_target_sync(target_url, target_product, aging_days, visit_count, proxy)


def generate_target_history(target_url: str, aging_days: int = 60) -> List[Dict[str, Any]]:
    """
    Generate synthetic browsing history for target site
    """
    engine = TargetWarmingEngine()
    return engine.generate_synthetic_history(target_url, aging_days)


if __name__ == "__main__":
    # Test the warming engine
    print("LUCID EMPIRE: Target Warming Engine Test")
    print("=" * 50)
    
    engine = TargetWarmingEngine(headless=True)
    
    # Generate synthetic history (no browser needed)
    print("\nGenerating synthetic history for amazon.com...")
    history = engine.generate_synthetic_history("https://www.amazon.com", aging_days=60)
    
    print(f"Generated {len(history)} history entries:")
    for entry in history[:5]:
        print(f"  - {entry['timestamp'][:10]}: {entry['url'][:50]}...")
    
    if len(history) > 5:
        print(f"  ... and {len(history) - 5} more entries")
    
    print(f"\nPlaywright available: {PLAYWRIGHT_AVAILABLE}")
    if PLAYWRIGHT_AVAILABLE:
        print("Full browser-based warming is available")
    else:
        print("Install playwright for browser-based warming: pip install playwright && playwright install")
