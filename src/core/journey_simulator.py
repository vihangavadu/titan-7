import time
import sys
import time
import sys

class Journey:
    def execute_manual_handover(self):
        """
        The 'Kill Switch' for automation. 
        Stops the script but leaves the browser open for the human.
        """
        print("\n" + "="*40)
        print(">>> INITIATING MANUAL HANDOVER PROTOCOL <<<")
        print(">>> AUTOMATION ENDING. DO NOT TOUCH FOR 180s <<<")
        print("="*40)
        
        # 1. The Silence Window (Letting pixels settle)
        for i in range(180, 0, -1):
            print(f"Silence Window: {i}s remaining...", end='\r')
            time.sleep(1)
            
        print("\n\n>>> HANDOVER COMPLETE. YOU HAVE CONTROL. <<<")
        print(">>> PROCEED TO CHECKOUT MANUALLY. <<<")
        
        # Exit script code 0 (Clean exit)
        sys.exit(0)



class HumanMouse:
    """
    Bezier Curve Mouse Movement (CHRONOS_TASK.md Module 3, Requirement 2)
    
    Implements Cubic Bezier math:
    B(t) = (1-t)^3 P0 + 3(1-t)^2 t P1 + 3(1-t) t^2 P2 + t^3 P3
    
    Adds "Micro-sleeps" (random floats) between movement steps.
    """
    
    def __init__(self, driver: webdriver.Chrome):
        self.driver = driver
        self.logger = get_logger()
    
    def cubic_bezier(self, t: float, p0: Tuple[int, int], p1: Tuple[int, int], 
                     p2: Tuple[int, int], p3: Tuple[int, int]) -> Tuple[float, float]:
        """
        Calculate point on cubic Bezier curve at parameter t.
        
        Formula: B(t) = (1-t)^3 P0 + 3(1-t)^2 t P1 + 3(1-t) t^2 P2 + t^3 P3
        
        Args:
            t: Parameter between 0 and 1
            p0, p1, p2, p3: Control points (x, y)
            
        Returns:
            (x, y) coordinates on the curve
        """
        # Calculate Bezier curve components
        one_minus_t = 1 - t
        
        # B(t) formula components
        term0 = (one_minus_t ** 3) * np.array(p0)
        term1 = 3 * (one_minus_t ** 2) * t * np.array(p1)
        term2 = 3 * one_minus_t * (t ** 2) * np.array(p2)
        term3 = (t ** 3) * np.array(p3)
        
        point = term0 + term1 + term2 + term3
        
        return int(point[0]), int(point[1])
    
    def move_to(self, target_x: int, target_y: int, duration: float = 1.0):
        """
        Move mouse to target position using Bezier curve with micro-sleeps.
        
        Args:
            target_x: Target X coordinate
            target_y: Target Y coordinate
            duration: Total movement duration in seconds
        """
        try:
            # Get current position (approximate center of viewport)
            viewport_width = self.driver.execute_script("return window.innerWidth;")
            viewport_height = self.driver.execute_script("return window.innerHeight;")
            
            start_x = viewport_width // 2
            start_y = viewport_height // 2
            
            # Generate random control points for natural curve
            control1_x = start_x + random.randint(-100, 100)
            control1_y = start_y + random.randint(-100, 100)
            control2_x = target_x + random.randint(-50, 50)
            control2_y = target_y + random.randint(-50, 50)
            
            p0 = (start_x, start_y)
            p1 = (control1_x, control1_y)
            p2 = (control2_x, control2_y)
            p3 = (target_x, target_y)
            
            # Calculate number of steps based on duration
            num_steps = int(duration * 100)  # 100 steps per second
            
            # Move along the Bezier curve
            prev_x, prev_y = p0
            for i in range(num_steps):
                t = i / num_steps
                x, y = self.cubic_bezier(t, p0, p1, p2, p3)
                
                # Create fresh ActionChains for each step to execute immediately
                action = ActionChains(self.driver)
                action.move_by_offset(x - prev_x, y - prev_y)
                action.perform()
                
                # Micro-sleep (random float between movements)
                micro_sleep = random.uniform(0.001, 0.01)
                time.sleep(micro_sleep)
                
                prev_x, prev_y = x, y
            self.logger.info(f"Bezier mouse movement: ({start_x},{start_y}) -> ({target_x},{target_y})")
            
        except Exception as e:
            self.logger.warning(f"Mouse movement warning: {e}")
    
    def random_movement(self):
        """Execute random mouse movements for entropy"""
        try:
            viewport_width = self.driver.execute_script("return window.innerWidth;")
            viewport_height = self.driver.execute_script("return window.innerHeight;")
            
            # Random target within viewport
            target_x = random.randint(100, viewport_width - 100)
            target_y = random.randint(100, viewport_height - 100)
            
            duration = random.uniform(0.5, 2.0)
            self.move_to(target_x, target_y, duration)
            
        except Exception as e:
            self.logger.warning(f"Random movement warning: {e}")


class JourneyBehavior:
    """
    Behavioral Patterns (CHRONOS_TASK.md Module 3, Requirement 3)
    
    Implements:
    - random_scroll(): Scroll down, but occasionally scroll up (regression)
    - loss_of_focus(): Switch to about:blank to trigger visibilityState: hidden
    """
    
    def __init__(self, driver: webdriver.Chrome):
        self.driver = driver
        self.logger = get_logger()
        self.mouse = HumanMouse(driver)
    
    def random_scroll(self):
        """
        Random scrolling with occasional upward regression.
        Mimics natural reading/browsing behavior.
        """
        try:
            # 70% chance to scroll down, 30% chance to scroll up
            scroll_direction = "down" if random.random() < 0.7 else "up"
            
            # Random scroll amount
            scroll_amount = random.randint(100, 800)
            
            if scroll_direction == "down":
                self.driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
                self.logger.info(f"Scrolled down: {scroll_amount}px")
            else:
                self.driver.execute_script(f"window.scrollBy(0, -{scroll_amount});")
                self.logger.info(f"Scrolled up (regression): {scroll_amount}px")
            
            # Random pause after scroll
            time.sleep(random.uniform(0.5, 2.0))
            
        except Exception as e:
            self.logger.warning(f"Scroll warning: {e}")
    
    def loss_of_focus(self):
        """
        Loss of Focus pattern.
        Switch to about:blank for 1-4 seconds to trigger visibilityState: hidden.
        Simulates user switching tabs or minimizing window.
        """
        try:
            current_url = self.driver.current_url
            
            # Switch to about:blank
            self.driver.execute_script("window.open('about:blank', '_blank');")
            
            # Switch to the new tab
            windows = self.driver.window_handles
            if len(windows) > 1:
                self.driver.switch_to.window(windows[-1])
                
                # Stay on blank page for random duration
                duration = random.uniform(1.0, 4.0)
                self.logger.info(f"Loss of focus: {duration:.1f}s on about:blank")
                time.sleep(duration)
                
                # Close blank tab and return to original
                self.driver.close()
                self.driver.switch_to.window(windows[0])
                
                self.logger.info("Focus restored to original tab")
            
        except Exception as e:
            self.logger.warning(f"Loss of focus warning: {e}")
    
    def random_click(self):
        """Random click on page elements"""
        try:
            # Try to find clickable elements
            clickable_elements = self.driver.find_elements("css selector", "a, button, [role='button']")
            
            if clickable_elements:
                element = random.choice(clickable_elements[:10])  # Limit to first 10
                
                # Move mouse to element with Bezier curve
                location = element.location
                self.mouse.move_to(location['x'], location['y'], duration=random.uniform(0.5, 1.5))
                
                # Random pause before click
                time.sleep(random.uniform(0.2, 0.8))
                
                # Click
                element.click()
                self.logger.info(f"Clicked element: {element.tag_name}")
                
                # Wait for potential page load
                time.sleep(random.uniform(1.0, 3.0))
                
        except Exception as e:
            self.logger.warning(f"Random click warning: {e}")
    
    def typing_simulation(self, text: str):
        """
        Simulate human typing with realistic delays.
        
        Args:
            text: Text to type
        """
        try:
            action = ActionChains(self.driver)
            
            for char in text:
                action.send_keys(char)
                
                # Random typing delay (50-150ms per character)
                time.sleep(random.uniform(0.05, 0.15))
            
            action.perform()
            self.logger.info(f"Typed text with human-like delays")
            
        except Exception as e:
            self.logger.warning(f"Typing simulation warning: {e}")


class PoissonJourney:
    """
    Poisson Distribution Timing (CHRONOS_TASK.md Module 3, Requirement 1)
    
    Implements function that calculates random "Time Jumps" between T-90 days and T-0.
    Ensures browser is fully closed (process killed) between jumps to flush .wal files.
    """
    
    def __init__(self, total_days: int = 90):
        self.logger = get_logger()
        self.entropy_gen = EntropyGenerator()
        self.total_days = total_days
    
    def generate_time_jumps(self, num_segments: int = 12) -> List[Dict[str, Any]]:
        """
        Calculate random "Time Jumps" using Poisson distribution.
        
        Args:
            num_segments: Number of time jump segments
            
        Returns:
            List of time jump specifications
        """
        self.logger.info(f"Generating Poisson-distributed time jumps for {self.total_days} days")
        
        # Use EntropyGenerator to create Poisson-distributed segments
        segments = self.entropy_gen.generate_segments(
            total_days=self.total_days,
            num_segments=num_segments
        )
        
        # Convert segments to time jump schedule
        time_jumps = []
        
        for segment in segments:
            time_jump = {
                'index': segment['index'],
                'days_ago': self.total_days - (segment['cumulative_hours'] / 24),
                'activity_level': segment['activity_level'],
                'actions': segment['actions'],
                'checkpoint': segment['checkpoint'],
                'duration_hours': segment['advance_hours'],
                'timestamp': segment['timestamp']
            }
            
            time_jumps.append(time_jump)
        
        self.logger.info(f"Generated {len(time_jumps)} time jump segments")
        return time_jumps
    
    def should_kill_browser(self, jump_index: int, total_jumps: int) -> bool:
        """
        Determine if browser should be killed after this jump.
        
        Browser MUST be fully closed between jumps to flush .wal files to disk.
        (CHRONOS_TASK.md Module 3, Requirement 1)
        
        Args:
            jump_index: Current jump index (0-based)
            total_jumps: Total number of jumps
            
        Returns:
            bool: True if browser should be killed
        """
        # Kill browser after every jump except the last one
        return jump_index < (total_jumps - 1)


# Convenience functions
def create_human_mouse(driver: webdriver.Chrome) -> HumanMouse:
    """Factory function to create HumanMouse instance"""
    return HumanMouse(driver)


def create_journey_behavior(driver: webdriver.Chrome) -> JourneyBehavior:
    """Factory function to create JourneyBehavior instance"""
    return JourneyBehavior(driver)


def generate_poisson_schedule(days: int = 90, segments: int = 12) -> List[Dict]:
    """
    Factory function to generate Poisson-distributed time jump schedule.
    
    Example:
        schedule = generate_poisson_schedule(90, 12)
        for jump in schedule:
            print(f"Jump to T-{jump['days_ago']} days")
    """
    journey = PoissonJourney(total_days=days)
    return journey.generate_time_jumps(num_segments=segments)


def visit_trust_anchors(driver: webdriver.Chrome) -> bool:
    """
    Visit "High Authority" trust anchor sites before the target site.
    
    These sites establish cookies that signal financial trust, professional trust,
    identity trust, and high-income demographic signals to fraud detection engines.
    
    Veritas V5 Protocol: Trust Anchor System
    - PayPal: Financial Trust
    - LinkedIn: Professional Trust  
    - Google Accounts: Identity Trust
    - NY Times: High-Income Demographic Signal
    - Amazon: E-commerce Trust
    
    Each site is visited with scroll and wait (3-5 seconds) to allow tracking pixels
    to fire. Note: This creates the intended behavior pattern; actual pixel firing
    depends on site implementation and cannot be verified from client-side code.
    
    LEVEL 10 REQUIREMENT: Hardcoded trust anchors - visits at least 3 before target.
    
    Args:
        driver: Selenium WebDriver instance
        
    Returns:
        bool: True if at least 3 trust anchors visited successfully
    """
    logger = get_logger()
    
    # Level 9: Strict Trust Anchors from config
    trust_anchors = getattr(Config, 'TRUST_ANCHORS', ["linkedin.com", "amazon.com", "nytimes.com"])
    trust_anchor_sites = [
        {'url': f"https://{site}", 'name': site.split('.')[0].capitalize(), 'trust_type': 'Trust Anchor'}
        for site in trust_anchors
    ]
    
    logger.info("=" * 60)
    logger.info("[LEVEL 10 - VERITAS V5] Trust Anchor System - Starting")
    logger.info("=" * 60)
    
    success_count = 0
    
    for anchor in trust_anchor_sites:
        try:
            logger.info(f"[Trust Anchor] Visiting {anchor['name']} ({anchor['trust_type']})")
            
            # Navigate to trust anchor site
            driver.get(anchor['url'])
            
            # Wait for page to load (Bursty Traffic Simulation)
            logger.info("  → Bursty Traffic Simulation: Poisson wait for page load")
            poisson_wait()
            
            # Scroll to trigger tracking pixels
            scroll_amount = random.randint(300, 800)
            driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
            logger.info(f"  → Scrolled {scroll_amount}px to trigger tracking pixels")
            
            # Wait using Poisson distribution for tracking pixel
            wait_time = poisson_wait()
            logger.info(f"  → Waiting {wait_time:.1f}s for tracking pixel to fire (Poisson)")
            
            # Additional scroll for natural behavior
            if random.random() > 0.5:
                scroll_up = random.randint(100, 300)
                driver.execute_script(f"window.scrollBy(0, -{scroll_up});")
            
            logger.info(f"  ✓ {anchor['name']} visit complete")
            success_count += 1
            
        except Exception as e:
            logger.warning(f"  ⚠ Failed to visit {anchor['name']}: {e}")
            # Continue to next anchor even if one fails
            continue
    
    logger.info("=" * 60)
    logger.info(f"[LEVEL 10 - VERITAS V5] Trust Anchor System Complete: {success_count}/{len(trust_anchor_sites)} sites")
    
    # LEVEL 10 REQUIREMENT: Must visit at least 3 trust anchors
    if success_count < 3:
        logger.error(f"[LEVEL 10 FAILURE] Only {success_count} trust anchors visited - minimum is 3")
        logger.info("=" * 60)
        return False
    
    logger.info(f"[LEVEL 10 SUCCESS] Minimum 3 trust anchors requirement met")
    logger.info("=" * 60)
    
    return True


def perform_history_generation(driver: webdriver.Chrome, 
                               target_site: Optional[str] = None,
                               include_trust_anchors: bool = True) -> bool:
    """
    Perform comprehensive history generation with trust anchors.
    
    Veritas V5 Protocol:
    1. Visit high-authority trust anchor sites first (if enabled)
    2. Visit generic browsing sites (Wikipedia, CNN)
    3. Visit target site (if specified)
    
    This creates a realistic browsing history that appears organic to fraud detection
    engines like Stripe Radar and Adyen.
    
    Args:
        driver: Selenium WebDriver instance
        target_site: Optional target site to visit after building history
        include_trust_anchors: Whether to include trust anchor visits (default: True)
        
    Returns:
        bool: Success status
    """
    logger = get_logger()
    
    try:
        logger.info("[History Generation] Starting Veritas V5 protocol")
        
        # Phase 1: Visit Trust Anchors (High Authority Cookies)
        if include_trust_anchors:
            if not visit_trust_anchors(driver):
                logger.warning("[History Generation] Trust anchor visits had issues, continuing...")
        
        # Phase 2: Visit Generic Sites (Baseline History)
        generic_sites = [
            'https://www.wikipedia.org',
            'https://www.cnn.com'
        ]
        
        logger.info("[History Generation] Visiting generic sites for baseline history")
        
        for site in generic_sites:
            try:
                logger.info(f"  → Visiting {site}")
                driver.get(site)
                
                # Natural behavior
                time.sleep(random.uniform(2, 4))
                
                # Scroll
                scroll_amount = random.randint(200, 600)
                driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
                
                # Dwell time
                time.sleep(random.uniform(3, 6))
                
                logger.info(f"  ✓ {site} complete")
                
            except Exception as e:
                logger.warning(f"  ⚠ Failed to visit {site}: {e}")
        
        # Phase 3: Visit Target Site (if specified)
        if target_site:
            logger.info(f"[History Generation] Visiting target site: {target_site}")
            try:
                driver.get(target_site)
                time.sleep(random.uniform(3, 5))
                
                # Scroll on target site
                scroll_amount = random.randint(300, 700)
                driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
                
                logger.info("  ✓ Target site visit complete")
                
            except Exception as e:
                logger.warning(f"  ⚠ Failed to visit target site: {e}")
                return False
        
        logger.info("[History Generation] Veritas V5 protocol complete")
        return True
        
    except Exception as e:
        logger.error(f"[History Generation] Failed: {e}")
        return False
