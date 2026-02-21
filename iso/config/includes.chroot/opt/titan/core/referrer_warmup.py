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
        # V7.5 FIX: Strip any TLD, not just .com/.co.uk
        domain_name = domain.split(".")[0]
        return query.format(domain=domain_name)
    
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
                        # V7.5 FIX: Use type() for characters, press() is for key names
                        search_box.type(step.search_query, delay=random.uniform(50, 150))
                        time.sleep(random.uniform(0.3, 0.8))
                        search_box.press("Enter")
                        page.wait_for_load_state("domcontentloaded")
                    else:
                        # Fallback: use direct search URL
                        page.goto(step.url, wait_until="domcontentloaded")
                
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
                
                elif step.action == "scroll":
                    # V7.5 FIX: Handle scroll action
                    scroll_amount = random.randint(300, 800)
                    page.evaluate(f"window.scrollBy(0, {scroll_amount})")
                
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


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 P0 CRITICAL ENHANCEMENTS - Advanced Warmup Operations
# ═══════════════════════════════════════════════════════════════════════════════

import threading
import hashlib
import json
from collections import defaultdict
from enum import Enum


class WarmupStatus(Enum):
    """Warmup campaign status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class WarmupCampaign:
    """Warmup campaign configuration"""
    campaign_id: str
    target_url: str
    plan: WarmupPlan
    status: WarmupStatus = WarmupStatus.PENDING
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    success: bool = False
    referrer_validated: bool = False
    error_message: Optional[str] = None


@dataclass
class ReferrerValidation:
    """Referrer chain validation result"""
    valid: bool
    referrer_url: Optional[str]
    expected_referrer: Optional[str]
    chain_length: int
    issues: List[str]
    validated_at: float


@dataclass
class WarmupMetrics:
    """Warmup analytics metrics"""
    total_campaigns: int
    successful_campaigns: int
    failed_campaigns: int
    avg_duration_seconds: float
    avg_steps: float
    success_rate_pct: float
    most_used_targets: Dict[str, int]
    referrer_validation_rate: float


class WarmupCampaignManager:
    """
    V7.6 P0: Manage multiple warmup campaigns with scheduling.
    
    Features:
    - Campaign creation and tracking
    - Parallel campaign execution
    - Campaign scheduling
    - History and audit trail
    - Retry logic for failed campaigns
    """
    
    def __init__(self, max_concurrent: int = 3, max_retries: int = 2):
        self.max_concurrent = max_concurrent
        self.max_retries = max_retries
        
        # Campaign storage
        self._campaigns: Dict[str, WarmupCampaign] = {}
        self._active_campaigns: List[str] = []
        self._completed_campaigns: List[str] = []
        
        # Retry tracking
        self._retry_counts: Dict[str, int] = defaultdict(int)
        
        # Scheduling
        self._scheduled: List[Dict] = []
        
        self._lock = threading.RLock()
        self.logger = logging.getLogger("TITAN-WARMUP-MANAGER")
    
    def create_campaign(self, target_url: str,
                        include_pre_warmup: bool = True) -> WarmupCampaign:
        """Create a new warmup campaign"""
        campaign_id = hashlib.sha256(
            f"{target_url}:{time.time()}:{random.random()}".encode()
        ).hexdigest()[:16]
        
        warmup = ReferrerWarmup()
        plan = warmup.create_warmup_plan(target_url, include_pre_warmup)
        
        campaign = WarmupCampaign(
            campaign_id=campaign_id,
            target_url=target_url,
            plan=plan,
        )
        
        with self._lock:
            self._campaigns[campaign_id] = campaign
        
        self.logger.info(f"Created campaign {campaign_id} for {target_url}")
        return campaign
    
    def start_campaign(self, campaign_id: str, page=None) -> bool:
        """Start a warmup campaign"""
        with self._lock:
            if campaign_id not in self._campaigns:
                return False
            
            if len(self._active_campaigns) >= self.max_concurrent:
                self.logger.warning("Max concurrent campaigns reached")
                return False
            
            campaign = self._campaigns[campaign_id]
            campaign.status = WarmupStatus.IN_PROGRESS
            campaign.started_at = time.time()
            self._active_campaigns.append(campaign_id)
        
        try:
            if page:
                warmup = ReferrerWarmup()
                success = warmup.execute_with_playwright(campaign.plan, page)
            else:
                # Manual execution - assume success
                success = True
            
            with self._lock:
                campaign.success = success
                campaign.status = WarmupStatus.COMPLETED if success else WarmupStatus.FAILED
                campaign.completed_at = time.time()
                
                if campaign_id in self._active_campaigns:
                    self._active_campaigns.remove(campaign_id)
                self._completed_campaigns.append(campaign_id)
            
            return success
            
        except Exception as e:
            with self._lock:
                campaign.status = WarmupStatus.FAILED
                campaign.error_message = str(e)
                campaign.completed_at = time.time()
                
                if campaign_id in self._active_campaigns:
                    self._active_campaigns.remove(campaign_id)
            
            # Check retry
            if self._retry_counts[campaign_id] < self.max_retries:
                self._retry_counts[campaign_id] += 1
                self.logger.info(f"Retrying campaign {campaign_id} (attempt {self._retry_counts[campaign_id]})")
                return self.start_campaign(campaign_id, page)
            
            self.logger.error(f"Campaign {campaign_id} failed: {e}")
            return False
    
    def cancel_campaign(self, campaign_id: str):
        """Cancel a campaign"""
        with self._lock:
            if campaign_id in self._campaigns:
                self._campaigns[campaign_id].status = WarmupStatus.CANCELLED
                if campaign_id in self._active_campaigns:
                    self._active_campaigns.remove(campaign_id)
    
    def schedule_campaign(self, target_url: str, schedule_time: float):
        """Schedule a campaign for future execution"""
        campaign = self.create_campaign(target_url)
        
        with self._lock:
            self._scheduled.append({
                "campaign_id": campaign.campaign_id,
                "schedule_time": schedule_time,
            })
        
        self.logger.info(f"Scheduled campaign {campaign.campaign_id} for {schedule_time}")
        return campaign
    
    def get_campaign(self, campaign_id: str) -> Optional[WarmupCampaign]:
        """Get campaign by ID"""
        return self._campaigns.get(campaign_id)
    
    def get_active_campaigns(self) -> List[WarmupCampaign]:
        """Get all active campaigns"""
        with self._lock:
            return [self._campaigns[cid] for cid in self._active_campaigns]
    
    def get_stats(self) -> Dict:
        """Get campaign manager statistics"""
        with self._lock:
            total = len(self._campaigns)
            completed = [c for c in self._campaigns.values() if c.status == WarmupStatus.COMPLETED]
            successful = [c for c in completed if c.success]
            failed = [c for c in self._campaigns.values() if c.status == WarmupStatus.FAILED]
            
            return {
                "total_campaigns": total,
                "active": len(self._active_campaigns),
                "completed": len(completed),
                "successful": len(successful),
                "failed": len(failed),
                "success_rate": len(successful) / max(1, len(completed)) * 100,
                "scheduled": len(self._scheduled),
            }


class ReferrerChainValidator:
    """
    V7.6 P0: Validate referrer chains are established correctly.
    
    Features:
    - JavaScript referrer extraction
    - Chain integrity verification
    - Expected referrer matching
    - Validation history tracking
    """
    
    # Expected referrer patterns
    EXPECTED_REFERRERS = {
        "google": ["google.com", "www.google.com", "google.co.uk"],
        "bing": ["bing.com", "www.bing.com"],
        "duckduckgo": ["duckduckgo.com"],
        "direct": [None, "", "null"],
    }
    
    def __init__(self):
        self._validations: List[ReferrerValidation] = []
        self._lock = threading.Lock()
        self.logger = logging.getLogger("TITAN-REFERRER-VALIDATOR")
    
    def validate_with_page(self, page, expected_source: str = "google") -> ReferrerValidation:
        """
        Validate referrer using Playwright page.
        
        Args:
            page: Playwright page object
            expected_source: Expected referrer source type
        
        Returns:
            ReferrerValidation result
        """
        issues = []
        
        try:
            # Extract document.referrer via JavaScript
            referrer = page.evaluate("document.referrer")
            
            # Parse referrer
            referrer_domain = None
            if referrer:
                try:
                    parsed = urlparse(referrer)
                    referrer_domain = parsed.netloc
                except Exception:
                    pass
            
            # Check expected patterns
            expected_patterns = self.EXPECTED_REFERRERS.get(expected_source, [])
            
            if expected_source == "direct":
                # Direct navigation - referrer should be empty
                valid = not referrer or referrer == ""
                if not valid:
                    issues.append(f"Expected empty referrer for direct nav, got: {referrer}")
            else:
                # Search engine navigation - check domain match
                valid = any(
                    pattern and referrer_domain and pattern in referrer_domain
                    for pattern in expected_patterns
                )
                
                if not valid:
                    issues.append(
                        f"Referrer '{referrer_domain}' doesn't match expected {expected_source} patterns"
                    )
            
            # Additional checks
            if referrer and len(referrer) > 2000:
                issues.append("Referrer URL suspiciously long")
            
            # Check for common bot signatures
            if referrer and any(sig in referrer.lower() for sig in ["selenium", "puppeteer", "playwright", "automation"]):
                issues.append("Referrer contains automation signature")
                valid = False
            
            # Build validation result
            validation = ReferrerValidation(
                valid=valid and len(issues) == 0,
                referrer_url=referrer,
                expected_referrer=expected_source,
                chain_length=1 if referrer else 0,
                issues=issues,
                validated_at=time.time(),
            )
            
        except Exception as e:
            validation = ReferrerValidation(
                valid=False,
                referrer_url=None,
                expected_referrer=expected_source,
                chain_length=0,
                issues=[f"Validation error: {e}"],
                validated_at=time.time(),
            )
        
        with self._lock:
            self._validations.append(validation)
        
        if validation.valid:
            self.logger.info(f"Referrer valid: {validation.referrer_url}")
        else:
            self.logger.warning(f"Referrer invalid: {validation.issues}")
        
        return validation
    
    def validate_chain_history(self, history: List[str]) -> ReferrerValidation:
        """
        Validate a navigation history chain.
        
        Args:
            history: List of URLs in navigation order
        
        Returns:
            ReferrerValidation for the chain
        """
        issues = []
        
        if len(history) < 2:
            issues.append("Chain too short - no referrer established")
        
        # Check for search engine in chain
        has_search_engine = False
        for url in history[:-1]:  # Exclude final URL
            if any(se in url for se in ["google.com", "bing.com", "duckduckgo.com"]):
                has_search_engine = True
                break
        
        if not has_search_engine:
            issues.append("No search engine in referrer chain")
        
        # Check for suspicious patterns
        unique_domains = set()
        for url in history:
            try:
                parsed = urlparse(url)
                unique_domains.add(parsed.netloc)
            except Exception:
                pass
        
        if len(unique_domains) < 2:
            issues.append("All navigation on same domain - no external referrer")
        
        validation = ReferrerValidation(
            valid=len(issues) == 0,
            referrer_url=history[-2] if len(history) >= 2 else None,
            expected_referrer="chain",
            chain_length=len(history),
            issues=issues,
            validated_at=time.time(),
        )
        
        with self._lock:
            self._validations.append(validation)
        
        return validation
    
    def get_validation_stats(self) -> Dict:
        """Get validation statistics"""
        with self._lock:
            if not self._validations:
                return {"total": 0}
            
            valid_count = sum(1 for v in self._validations if v.valid)
            
            return {
                "total": len(self._validations),
                "valid": valid_count,
                "invalid": len(self._validations) - valid_count,
                "success_rate": valid_count / len(self._validations) * 100,
                "common_issues": self._get_common_issues(),
            }
    
    def _get_common_issues(self) -> Dict[str, int]:
        """Get most common validation issues"""
        issue_counts = defaultdict(int)
        for v in self._validations:
            for issue in v.issues:
                # Normalize issue for counting
                normalized = issue.split(":")[0] if ":" in issue else issue
                issue_counts[normalized] += 1
        return dict(sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:5])


class WarmupAnalytics:
    """
    V7.6 P0: Track warmup success rates and patterns.
    
    Features:
    - Success rate tracking by target
    - Duration analytics
    - Failure pattern analysis
    - Performance optimization insights
    """
    
    def __init__(self, retention_count: int = 500):
        self.retention_count = retention_count
        
        # Analytics data
        self._campaign_records: List[Dict] = []
        self._target_stats: Dict[str, Dict] = defaultdict(lambda: {
            "attempts": 0,
            "successes": 0,
            "failures": 0,
            "total_duration": 0,
        })
        
        # Time-series data
        self._hourly_stats: Dict[int, Dict] = {}
        
        self._lock = threading.Lock()
        self.logger = logging.getLogger("TITAN-WARMUP-ANALYTICS")
    
    def record_campaign(self, campaign: WarmupCampaign):
        """Record a completed campaign for analytics"""
        with self._lock:
            duration = 0
            if campaign.started_at and campaign.completed_at:
                duration = campaign.completed_at - campaign.started_at
            
            record = {
                "campaign_id": campaign.campaign_id,
                "target_url": campaign.target_url,
                "target_domain": campaign.plan.target_domain,
                "success": campaign.success,
                "duration": duration,
                "steps": len(campaign.plan.steps),
                "referrer_validated": campaign.referrer_validated,
                "completed_at": campaign.completed_at or time.time(),
                "error": campaign.error_message,
            }
            
            self._campaign_records.append(record)
            
            # Trim to retention limit
            if len(self._campaign_records) > self.retention_count:
                self._campaign_records = self._campaign_records[-self.retention_count:]
            
            # Update target stats
            domain = campaign.plan.target_domain
            self._target_stats[domain]["attempts"] += 1
            self._target_stats[domain]["total_duration"] += duration
            
            if campaign.success:
                self._target_stats[domain]["successes"] += 1
            else:
                self._target_stats[domain]["failures"] += 1
            
            # Update hourly stats
            hour = int(time.time() // 3600)
            if hour not in self._hourly_stats:
                self._hourly_stats[hour] = {"campaigns": 0, "successes": 0}
            self._hourly_stats[hour]["campaigns"] += 1
            if campaign.success:
                self._hourly_stats[hour]["successes"] += 1
    
    def get_metrics(self) -> WarmupMetrics:
        """Get comprehensive analytics metrics"""
        with self._lock:
            if not self._campaign_records:
                return WarmupMetrics(
                    total_campaigns=0,
                    successful_campaigns=0,
                    failed_campaigns=0,
                    avg_duration_seconds=0,
                    avg_steps=0,
                    success_rate_pct=0,
                    most_used_targets={},
                    referrer_validation_rate=0,
                )
            
            total = len(self._campaign_records)
            successful = sum(1 for r in self._campaign_records if r["success"])
            failed = total - successful
            
            durations = [r["duration"] for r in self._campaign_records if r["duration"] > 0]
            avg_duration = sum(durations) / len(durations) if durations else 0
            
            steps = [r["steps"] for r in self._campaign_records]
            avg_steps = sum(steps) / len(steps) if steps else 0
            
            validated = sum(1 for r in self._campaign_records if r["referrer_validated"])
            
            # Most used targets
            target_counts = defaultdict(int)
            for r in self._campaign_records:
                target_counts[r["target_domain"]] += 1
            most_used = dict(sorted(target_counts.items(), key=lambda x: x[1], reverse=True)[:5])
            
            return WarmupMetrics(
                total_campaigns=total,
                successful_campaigns=successful,
                failed_campaigns=failed,
                avg_duration_seconds=round(avg_duration, 2),
                avg_steps=round(avg_steps, 1),
                success_rate_pct=round(successful / total * 100, 2),
                most_used_targets=most_used,
                referrer_validation_rate=round(validated / total * 100, 2),
            )
    
    def get_target_performance(self, domain: str) -> Dict:
        """Get performance stats for specific target"""
        with self._lock:
            stats = self._target_stats.get(domain, {})
            if not stats or stats.get("attempts", 0) == 0:
                return {"domain": domain, "no_data": True}
            
            return {
                "domain": domain,
                "attempts": stats["attempts"],
                "successes": stats["successes"],
                "failures": stats["failures"],
                "success_rate": stats["successes"] / stats["attempts"] * 100,
                "avg_duration": stats["total_duration"] / stats["attempts"],
            }
    
    def get_failure_patterns(self) -> Dict:
        """Analyze failure patterns"""
        with self._lock:
            failures = [r for r in self._campaign_records if not r["success"]]
            
            if not failures:
                return {"total_failures": 0}
            
            # Group by error message
            error_counts = defaultdict(int)
            for f in failures:
                error = f.get("error") or "Unknown error"
                # Normalize error
                normalized = error.split(":")[0] if ":" in error else error[:50]
                error_counts[normalized] += 1
            
            # Group by target
            target_failures = defaultdict(int)
            for f in failures:
                target_failures[f["target_domain"]] += 1
            
            return {
                "total_failures": len(failures),
                "error_types": dict(sorted(error_counts.items(), key=lambda x: x[1], reverse=True)),
                "failure_by_target": dict(sorted(target_failures.items(), key=lambda x: x[1], reverse=True)[:5]),
            }
    
    def export_report(self, filepath: str):
        """Export analytics report to file"""
        report = {
            "generated_at": time.time(),
            "metrics": {
                "total_campaigns": self.get_metrics().total_campaigns,
                "success_rate": self.get_metrics().success_rate_pct,
                "avg_duration": self.get_metrics().avg_duration_seconds,
            },
            "target_stats": dict(self._target_stats),
            "failure_patterns": self.get_failure_patterns(),
            "hourly_stats": self._hourly_stats,
        }
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        self.logger.info(f"Analytics report exported to {filepath}")


class AdaptiveWarmupEngine:
    """
    V7.6 P0: Adaptive warmup based on target requirements.
    
    Features:
    - Target-specific warmup strategies
    - Dynamic step adjustment
    - Learn from success/failure patterns
    - Risk-based warmup intensity
    """
    
    # Target risk levels
    RISK_LEVELS = {
        "amazon.com": "high",
        "ebay.com": "medium",
        "walmart.com": "medium",
        "bestbuy.com": "high",
        "target.com": "medium",
        "newegg.com": "high",
        "default": "low",
    }
    
    # Strategy parameters by risk level
    STRATEGY_PARAMS = {
        "low": {
            "pre_warmup_sites": 1,
            "search_dwell_time": 2,
            "page_dwell_time": 3,
            "scroll_probability": 0.3,
        },
        "medium": {
            "pre_warmup_sites": 2,
            "search_dwell_time": 4,
            "page_dwell_time": 5,
            "scroll_probability": 0.5,
        },
        "high": {
            "pre_warmup_sites": 3,
            "search_dwell_time": 6,
            "page_dwell_time": 8,
            "scroll_probability": 0.7,
        },
    }
    
    def __init__(self, analytics: WarmupAnalytics = None):
        self.analytics = analytics
        
        # Learning state
        self._target_adjustments: Dict[str, Dict] = {}
        
        self._lock = threading.Lock()
        self.logger = logging.getLogger("TITAN-ADAPTIVE-WARMUP")
    
    def get_risk_level(self, domain: str) -> str:
        """Get risk level for target domain"""
        return self.RISK_LEVELS.get(domain, self.RISK_LEVELS["default"])
    
    def get_strategy(self, domain: str) -> Dict:
        """Get warmup strategy for target domain"""
        risk = self.get_risk_level(domain)
        base_params = self.STRATEGY_PARAMS[risk].copy()
        
        # Apply learned adjustments
        with self._lock:
            if domain in self._target_adjustments:
                for key, adjustment in self._target_adjustments[domain].items():
                    if key in base_params:
                        base_params[key] = base_params[key] + adjustment
        
        return {
            "risk_level": risk,
            **base_params,
        }
    
    def create_adaptive_plan(self, target_url: str) -> WarmupPlan:
        """Create an adaptive warmup plan based on target"""
        parsed = urlparse(target_url)
        domain = parsed.netloc.replace("www.", "")
        
        strategy = self.get_strategy(domain)
        
        plan = WarmupPlan(
            target_domain=domain,
            target_url=target_url,
        )
        
        # Add pre-warmup sites based on strategy
        num_sites = strategy["pre_warmup_sites"]
        warmup_sites = random.sample(
            ReferrerWarmup.WARMUP_SITES,
            min(num_sites, len(ReferrerWarmup.WARMUP_SITES))
        )
        
        for url, _, _ in warmup_sites:
            plan.steps.append(WarmupStep(
                url=url,
                wait_seconds=strategy["page_dwell_time"] * random.uniform(0.8, 1.2),
                action="navigate",
            ))
        
        # Add search step
        search_query = self._get_adaptive_query(domain)
        plan.steps.append(WarmupStep(
            url="https://www.google.com",
            wait_seconds=strategy["search_dwell_time"],
            action="search",
            search_query=search_query,
        ))
        
        # Add click to target
        plan.steps.append(WarmupStep(
            url=f"https://www.{domain}",
            wait_seconds=strategy["page_dwell_time"],
            action="click",
            selector=f'a[href*="{domain}"]',
        ))
        
        # Add scroll step if high probability
        if random.random() < strategy["scroll_probability"]:
            plan.steps.append(WarmupStep(
                url=target_url,
                wait_seconds=2,
                action="scroll",
            ))
        
        # Navigate to final target
        plan.steps.append(WarmupStep(
            url=target_url,
            wait_seconds=strategy["page_dwell_time"],
            action="navigate",
        ))
        
        plan.total_duration = sum(s.wait_seconds for s in plan.steps)
        
        self.logger.info(
            f"Adaptive plan created for {domain}: "
            f"risk={strategy['risk_level']}, steps={len(plan.steps)}, "
            f"duration={plan.total_duration:.1f}s"
        )
        
        return plan
    
    def _get_adaptive_query(self, domain: str) -> str:
        """Get search query adapted from analytics"""
        base_queries = ReferrerWarmup.SEARCH_QUERIES.get(
            domain, ReferrerWarmup.SEARCH_QUERIES["default"]
        )
        query = random.choice(base_queries)
        domain_name = domain.split(".")[0]
        return query.format(domain=domain_name)
    
    def learn_from_result(self, domain: str, success: bool, duration: float):
        """Learn from campaign result to adjust strategy"""
        with self._lock:
            if domain not in self._target_adjustments:
                self._target_adjustments[domain] = {
                    "page_dwell_time": 0,
                    "search_dwell_time": 0,
                    "pre_warmup_sites": 0,
                }
            
            if success:
                # Successful - slightly reduce dwell times for efficiency
                self._target_adjustments[domain]["page_dwell_time"] -= 0.1
            else:
                # Failed - increase dwell times
                self._target_adjustments[domain]["page_dwell_time"] += 0.5
                self._target_adjustments[domain]["search_dwell_time"] += 0.3
        
        self.logger.debug(f"Learned from {domain} result: success={success}")
    
    def reset_learning(self, domain: Optional[str] = None):
        """Reset learned adjustments"""
        with self._lock:
            if domain:
                self._target_adjustments.pop(domain, None)
            else:
                self._target_adjustments.clear()


# ═══════════════════════════════════════════════════════════════════════════
# V7.6 SINGLETON INSTANCES
# ═══════════════════════════════════════════════════════════════════════════

_warmup_campaign_manager: Optional[WarmupCampaignManager] = None
_referrer_chain_validator: Optional[ReferrerChainValidator] = None
_warmup_analytics: Optional[WarmupAnalytics] = None
_adaptive_warmup_engine: Optional[AdaptiveWarmupEngine] = None


def get_warmup_campaign_manager() -> WarmupCampaignManager:
    """Get global warmup campaign manager"""
    global _warmup_campaign_manager
    if _warmup_campaign_manager is None:
        _warmup_campaign_manager = WarmupCampaignManager()
    return _warmup_campaign_manager


def get_referrer_chain_validator() -> ReferrerChainValidator:
    """Get global referrer chain validator"""
    global _referrer_chain_validator
    if _referrer_chain_validator is None:
        _referrer_chain_validator = ReferrerChainValidator()
    return _referrer_chain_validator


def get_warmup_analytics() -> WarmupAnalytics:
    """Get global warmup analytics"""
    global _warmup_analytics
    if _warmup_analytics is None:
        _warmup_analytics = WarmupAnalytics()
    return _warmup_analytics


def get_adaptive_warmup_engine() -> AdaptiveWarmupEngine:
    """Get global adaptive warmup engine"""
    global _adaptive_warmup_engine
    if _adaptive_warmup_engine is None:
        _adaptive_warmup_engine = AdaptiveWarmupEngine(analytics=get_warmup_analytics())
    return _adaptive_warmup_engine
