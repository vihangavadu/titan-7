def get_human_jitter(min_ms=8, max_ms=32):
    """
    Returns a cryptographically secure, human-like jitter (in seconds) for mouse movement delays.
    Args:
        min_ms: Minimum jitter in milliseconds (default 8)
        max_ms: Maximum jitter in milliseconds (default 32)
    Returns:
        float: Jitter in seconds
    """
    import secrets
    ms = min_ms + secrets.randbelow(max_ms - min_ms + 1)
    return ms / 1000.0
"""
Entropy Generator: Advanced temporal entropy generation with Poisson distribution.
Creates realistic browsing patterns and time advancement strategies.
"""
import numpy as np
from scipy import stats
import random
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple, Optional
import logging


import secrets
import random
LONG_PAUSE_MEAN_SECONDS = 60  # Mean duration for long pauses
LONG_PAUSE_STD_SECONDS = 15   # Standard deviation for long pauses
LONG_PAUSE_MIN_SECONDS = 30   # Minimum long pause duration
LONG_PAUSE_MAX_SECONDS = 90   # Maximum long pause duration
REGULAR_PAUSE_MIN_SECONDS = 1 # Minimum regular pause duration
REGULAR_PAUSE_MAX_SECONDS = 5 # Maximum regular pause duration


class EntropyGenerator:
    """
    Generates temporal entropy using Poisson distribution for realistic aging patterns.
    Simulates organic user behavior over extended time periods.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize Entropy Generator with configuration."""
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.poisson_lambda = self.config.get('poisson_lambda', 2.5)
        self.min_interval = self.config.get('min_interval_hours', 2)
        self.max_interval = self.config.get('max_interval_hours', 168)
        
        # Seed for reproducibility
        self.random_seed = self.config.get('random_seed', None)
        if self.random_seed:
            random.seed(self.random_seed)
            np.random.seed(self.random_seed)
        
        # Veritas V5: Organic pause tracking
        self.page_visit_count = 0
        self.long_pause_threshold = random.randint(3, 5)  # Trigger long pause every 3-5 pages
    
    def generate_segments(self, total_days: int, num_segments: Optional[int] = None) -> List[Dict]:
        """
        Generate time advancement segments using Poisson distribution.
        
        Args:
            total_days: Total number of days to age
            num_segments: Number of segments (auto-calculated if None)
            
        Returns:
            List of segment dictionaries with timing information
        """
        if num_segments is None:
            num_segments = self.config.get('entropy_segments', 12)
        
        total_hours = total_days * 24
        segments = []
        
        # Generate Poisson-distributed intervals
        intervals = self._generate_poisson_intervals(num_segments, total_hours)
        
        current_time = 0
        base_date = datetime.utcnow() - timedelta(days=total_days)
        
        for i, interval in enumerate(intervals):
            # Activity level based on time of day
            segment_date = base_date + timedelta(hours=current_time)
            activity_level = self._calculate_activity_level(segment_date)
            
            segment = {
                'index': i,
                'advance_hours': interval,
                'cumulative_hours': current_time + interval,
                'timestamp': segment_date + timedelta(hours=interval),
                'activity_level': activity_level,
                'checkpoint': i % 3 == 0,  # GAMP checkpoint every 3rd segment
                'is_weekend': segment_date.weekday() >= 5,
                'hour_of_day': segment_date.hour,
                'actions': self._generate_segment_actions(activity_level)
            }
            
            segments.append(segment)
            current_time += interval
        
                # Long Pause: 30-90 seconds (simulates reading or multitasking)
                # Use normal distribution centered at LONG_PAUSE_MEAN_SECONDS
                pause_duration = float(secrets.SystemRandom().normalvariate(LONG_PAUSE_MEAN_SECONDS, LONG_PAUSE_STD_SECONDS))
                pause_duration = float(np.clip(pause_duration, LONG_PAUSE_MIN_SECONDS, LONG_PAUSE_MAX_SECONDS))
                # Log before resetting counter for clarity
                pages_before_reset = self.page_visit_count
                self.logger.info(f"[Organic Gap] Long Pause triggered (after {pages_before_reset} pages): {pause_duration:.1f}s")
                # Reset counter and set new threshold
                self.page_visit_count = 0
                self.long_pause_threshold = self._secure_random.randint(3, 5)
        intervals = raw_intervals * scale_factor
        
        # Apply constraints
        intervals = np.clip(intervals, self.min_interval, self.max_interval)
        
        # Normalize to fit total time
        current_total = np.sum(intervals)
        if current_total > 0:
            intervals = intervals * (total_hours / current_total)
        
        # Add some noise
        noise = np.random.normal(0, 0.1, num_segments)
        intervals = intervals * (1 + noise)
        
        # Final constraint check
        intervals = np.maximum(intervals, self.min_interval)
        # Hardened entropy: cryptographically secure delay
        def get_secure_delay(min_seconds, max_seconds):
            """
            Uses cryptographic randomness to prevent mathematical prediction of sleep patterns.
            """
            rand_float = secrets.randbelow(1000000) / 1000000.0
            range_span = max_seconds - min_seconds
            return min_seconds + (range_span * rand_float)
        
        return intervals.tolist()
    
    def _calculate_activity_level(self, timestamp: datetime) -> str:
        """Calculate activity level based on time patterns."""
        
        hour = timestamp.hour
        is_weekend = timestamp.weekday() >= 5
        
        # Weekend patterns
        if is_weekend:
            if 10 <= hour <= 22:
                return 'high'
            elif 8 <= hour <= 23:
                return 'medium'
            else:
                return 'low'
        
        # Weekday patterns
        else:
            if 9 <= hour <= 11 or 14 <= hour <= 16 or 19 <= hour <= 21:
                return 'high'
            elif 7 <= hour <= 22:
                return 'medium'
            else:
                return 'low'
    
    def _generate_segment_actions(self, activity_level: str) -> List[str]:
        """Generate list of actions for a segment based on activity level."""
        
        action_pools = {
            'high': [
                'browse_products', 'add_to_cart', 'search', 'watch_video',
                'read_article', 'click_ads', 'form_submission', 'download',
                'share_social', 'comment', 'review', 'purchase'
            ],
            'medium': [
                'browse_homepage', 'read_article', 'search', 'scroll',
                'click_link', 'view_image', 'check_email', 'update_profile'
            ],
            'low': [
                'idle', 'scroll', 'refresh', 'check_notifications'
            ]
        }
        self._secure_random = secrets.SystemRandom()
        num_actions = self._secure_random.randint(min_actions, max_actions)
        pool = action_pools.get(activity_level, action_pools['medium'])
        return [self._secure_random.choice(pool) for _ in range(num_actions)]
        # Number of actions based on activity level
        num_actions_map = {'high': (5, 15), 'medium': (3, 8), 'low': (1, 3)}
        min_actions, max_actions = num_actions_map.get(activity_level, (3, 8))
        
        num_actions = random.randint(min_actions, max_actions)
        
        return [random.choice(pool) for _ in range(num_actions)]
    
    def generate_actions(self, activity_level: str) -> List[Dict]:
        """
        Generate detailed action specifications for browser automation.
        
        Args:
            activity_level: Level of activity (high/medium/low)
            
        Returns:
            List of action dictionaries with parameters
        """
        actions = []
        base_actions = self._generate_segment_actions(activity_level)
        
        for action_type in base_actions:
            action = self._create_action_spec(action_type)
            actions.append(action)
        
        return actions
    
    def _create_action_spec(self, action_type: str) -> Dict:
        """Create detailed action specification."""
        
        action = {
            'type': action_type,
            'timestamp': datetime.utcnow(),
            'parameters': {}
        }
        
        if action_type == 'scroll':
            action['parameters'] = {
                'direction': self._secure_random.choice(['down', 'up']),
                'amount': self._secure_random.randint(100, 800),
                'duration': self._secure_random.uniform(0.5, 2.0)
            }
        
        elif action_type == 'click_link':
            action['parameters'] = {
                'selector': self._secure_random.choice(['a', 'button', '.btn', '[role="button"]']),
                'index': self._secure_random.randint(0, 10),
                'wait_after': self._secure_random.uniform(1, 3)
            }
        
        elif action_type == 'search':
            action['parameters'] = {
                'query': self._generate_search_query(),
                'submit_delay': self._secure_random.uniform(0.5, 2),
                'typing_speed': self._secure_random.uniform(0.05, 0.15)
            }
        
        elif action_type == 'mouse_movement':
            action['parameters'] = {
                'pattern': self._secure_random.choice(['bezier', 'linear', 'random']),
                'duration': self._secure_random.uniform(0.3, 1.5),
                'points': self._generate_mouse_path()
            }
        
        elif action_type == 'form_submission':
            action['parameters'] = {
                'fields': self._secure_random.randint(2, 6),
                'typing_delays': [self._secure_random.uniform(0.05, 0.2) for _ in range(6)],
                'submit_delay': self._secure_random.uniform(1, 3)
            }
        
        return action
    
    def _generate_search_query(self) -> str:
        """Generate realistic search query."""
        
        query_templates = [
            "best {} 2024",
            "how to {}",
            "{} reviews",
            "{} vs {}",
            "cheap {}",
            "{} near me",
            "{} tutorial",
            "buy {} online"
        ]
        
        topics = [
            "laptop", "phone", "shoes", "restaurant", "hotel",
            "camera", "headphones", "watch", "book", "course",
            "software", "game", "movie", "recipe", "workout"
        ]
        
        template = self._secure_random.choice(query_templates)
        
        if '{}' in template:
            if template.count('{}') == 2:
                return template.format(self._secure_random.choice(topics), self._secure_random.choice(topics))
            else:
                return template.format(self._secure_random.choice(topics))
        
        return template
    
    def _generate_mouse_path(self) -> List[Tuple[int, int]]:
        """Generate realistic mouse movement path."""
        
        num_points = self._secure_random.randint(3, 8)
        points = []
        
        for _ in range(num_points):
            x = self._secure_random.randint(100, 1800)
            y = self._secure_random.randint(100, 900)
            points.append((x, y))
        
        return points
    
    def generate_circadian_pattern(self, days: int) -> List[Dict]:
        """
        Generate activity pattern following circadian rhythm.
        
        Args:
            days: Number of days to generate pattern for
            
        Returns:
            List of activity windows with timing
        """
        pattern = []
        
        for day in range(days):
            base_date = datetime.utcnow() - timedelta(days=days-day)
            
            # Morning activity (6-9 AM)
                morning_start = base_date.replace(hour=self._secure_random.randint(6, 7), 
                                                 minute=self._secure_random.randint(0, 59))
                morning_duration = self._secure_random.uniform(0.5, 2)
            
            # Midday activity (11 AM - 2 PM)
                midday_start = base_date.replace(hour=self._secure_random.randint(11, 12),
                                                minute=self._secure_random.randint(0, 59))
                midday_duration = self._secure_random.uniform(1, 2.5)
            
            # Evening activity (6-10 PM)
                evening_start = base_date.replace(hour=self._secure_random.randint(18, 20),
                                                 minute=self._secure_random.randint(0, 59))
                evening_duration = self._secure_random.uniform(1.5, 3)
            
            # Add some days with night activity
                if self._secure_random.random() < 0.2:  # 20% chance
                    night_start = base_date.replace(hour=self._secure_random.randint(22, 23),
                                                   minute=self._secure_random.randint(0, 59))
                    night_duration = self._secure_random.uniform(0.5, 1.5)
                
                pattern.append({
                    'day': day,
                    'date': base_date,
                    'period': 'night',
                    'start': night_start,
                    'duration': night_duration,
                    'intensity': 'low'
                })
            
            # Add regular periods
            for period, start, duration in [
                ('morning', morning_start, morning_duration),
                ('midday', midday_start, midday_duration),
                ('evening', evening_start, evening_duration)
            ]:
                pattern.append({
                    'day': day,
                    'date': base_date,
                    'period': period,
                    'start': start,
                    'duration': duration,
                    'intensity': 'high' if period == 'evening' else 'medium'
                })
        
        return pattern
    
    def organic_pause(self, force_long: bool = False) -> float:
        """
        Generate organic browsing pauses with localized random distribution.
        
        Veritas V5 Protocol: Organic Gaps
        - Robots browse linearly with uniform delays
        - Humans browse in bursts with long pauses
        - Every 3-5 pages: trigger "Long Pause" (30-90 seconds) to simulate reading/multitasking
        - Regular pauses: 1-5 seconds with localized distribution
        
        This adds time to generation but drastically increases trust scores.
        
        Args:
            force_long: Force a long pause regardless of page count
            
        Returns:
            float: Pause duration in seconds
        """
        self.page_visit_count += 1
        
        # Check if we should trigger a long pause
        should_long_pause = (self.page_visit_count >= self.long_pause_threshold) or force_long
        
        if should_long_pause:
            # Long Pause: 30-90 seconds (simulates reading or multitasking)
            # Use normal distribution centered at LONG_PAUSE_MEAN_SECONDS
            pause_duration = np.random.normal(LONG_PAUSE_MEAN_SECONDS, LONG_PAUSE_STD_SECONDS)
            pause_duration = np.clip(pause_duration, LONG_PAUSE_MIN_SECONDS, LONG_PAUSE_MAX_SECONDS)
            
            # Log before resetting counter for clarity
            pages_before_reset = self.page_visit_count
            self.logger.info(f"[Organic Gap] Long Pause triggered (after {pages_before_reset} pages): {pause_duration:.1f}s")
            
            # Reset counter and set new threshold
            self.page_visit_count = 0
            self.long_pause_threshold = random.randint(3, 5)
            
        else:
            # Regular pause: 1-5 seconds with localized random distribution
            # Use gamma distribution for more realistic human timing
            shape = 2.0  # Shape parameter for gamma distribution
            scale = 1.0  # Scale parameter
            
            pause_duration = np.random.gamma(shape, scale)
            pause_duration = np.clip(pause_duration, REGULAR_PAUSE_MIN_SECONDS, REGULAR_PAUSE_MAX_SECONDS)
            
            self.logger.debug(f"[Organic Gap] Regular pause: {pause_duration:.2f}s")
        
        # Execute the pause
        time.sleep(pause_duration)
        
        return pause_duration