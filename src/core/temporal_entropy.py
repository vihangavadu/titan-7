#!/usr/bin/env python3
"""
TITAN V8.1 SINGULARITY — Temporal Entropy Generator

Advanced temporal entropy generation with Poisson distribution.
Creates realistic browsing patterns, circadian rhythms, and organic pause timing
for profile aging and behavioral simulation.

Recovered from Prometheus-Core and adapted for Titan V8.1.
numpy/scipy are OPTIONAL — pure-Python fallbacks provided.

Integration points:
  - genesis_core.py: Use generate_segments() for profile aging timeline
  - referrer_warmup.py: Use organic_pause() between warmup visits
  - integration_bridge.py: Use circadian patterns for session timing
  - ghost_motor_v6.py: Use get_human_jitter() for mouse movement delays
"""
import math
import random
import secrets
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple, Optional

logger = logging.getLogger("TITAN-TEMPORAL-ENTROPY")

# Optional numpy/scipy — graceful fallback to pure Python
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    np = None
    NUMPY_AVAILABLE = False

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

LONG_PAUSE_MEAN_SECONDS = 60
LONG_PAUSE_STD_SECONDS = 15
LONG_PAUSE_MIN_SECONDS = 30
LONG_PAUSE_MAX_SECONDS = 90
REGULAR_PAUSE_MIN_SECONDS = 1
REGULAR_PAUSE_MAX_SECONDS = 5


# ═══════════════════════════════════════════════════════════════════════════════
# STANDALONE HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def get_human_jitter(min_ms=8, max_ms=32):
    """Cryptographically secure human-like jitter in seconds for mouse delays."""
    ms = min_ms + secrets.randbelow(max_ms - min_ms + 1)
    return ms / 1000.0


def get_secure_delay(min_seconds, max_seconds):
    """Cryptographically secure delay to prevent pattern prediction."""
    rand_float = secrets.randbelow(1000000) / 1000000.0
    return min_seconds + ((max_seconds - min_seconds) * rand_float)


def _poisson_pure_python(lam, size):
    """Pure-Python Poisson random variate generator (no numpy needed)."""
    results = []
    rng = secrets.SystemRandom()
    for _ in range(size):
        L = math.exp(-lam)
        k = 0
        p = 1.0
        while True:
            k += 1
            p *= rng.random()
            if p < L:
                break
        results.append(k - 1)
    return results


def _normal_pure_python(mean, std):
    """Pure-Python normal variate (no numpy needed)."""
    rng = secrets.SystemRandom()
    return max(0, rng.gauss(mean, std))


def _clip(value, low, high):
    """Clip value to range [low, high]."""
    return max(low, min(high, value))


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN CLASS
# ═══════════════════════════════════════════════════════════════════════════════

class EntropyGenerator:
    """
    Generates temporal entropy using Poisson distribution for realistic aging.
    Simulates organic user behavior over extended time periods.

    Usage:
        from temporal_entropy import EntropyGenerator

        gen = EntropyGenerator(config={'random_seed': 42})
        segments = gen.generate_segments(total_days=90, num_segments=12)
        pause = gen.organic_pause()
        pattern = gen.generate_circadian_pattern(days=90)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self._rng = secrets.SystemRandom()

        self.poisson_lambda = self.config.get('poisson_lambda', 2.5)
        self.min_interval = self.config.get('min_interval_hours', 2)
        self.max_interval = self.config.get('max_interval_hours', 168)

        seed = self.config.get('random_seed')
        if seed:
            random.seed(seed)
            if NUMPY_AVAILABLE:
                np.random.seed(seed)

        self.page_visit_count = 0
        self.long_pause_threshold = random.randint(3, 5)

    # ─── Segment Generation ──────────────────────────────────────────

    def generate_segments(self, total_days: int, num_segments: Optional[int] = None) -> List[Dict]:
        """
        Generate time advancement segments using Poisson distribution.

        Args:
            total_days: Total number of days to age
            num_segments: Number of segments (default 12)

        Returns:
            List of segment dicts with timing, activity level, and actions
        """
        if num_segments is None:
            num_segments = self.config.get('entropy_segments', 12)

        total_hours = total_days * 24
        intervals = self._generate_poisson_intervals(num_segments, total_hours)

        segments = []
        current_time = 0
        base_date = datetime.utcnow() - timedelta(days=total_days)

        for i, interval in enumerate(intervals):
            segment_date = base_date + timedelta(hours=current_time)
            activity = self._calculate_activity_level(segment_date)

            segments.append({
                'index': i,
                'advance_hours': interval,
                'cumulative_hours': current_time + interval,
                'timestamp': segment_date + timedelta(hours=interval),
                'activity_level': activity,
                'checkpoint': i % 3 == 0,
                'is_weekend': segment_date.weekday() >= 5,
                'hour_of_day': segment_date.hour,
                'actions': self._generate_segment_actions(activity),
            })
            current_time += interval

        return segments

    def _generate_poisson_intervals(self, num_segments: int, total_hours: float) -> List[float]:
        """Generate Poisson-distributed time intervals."""
        if NUMPY_AVAILABLE:
            raw = np.random.poisson(self.poisson_lambda, num_segments).astype(float)
            raw = np.maximum(raw, 0.5)
            scale = total_hours / max(np.sum(raw), 1)
            intervals = raw * scale
            intervals = np.clip(intervals, self.min_interval, self.max_interval)
            noise = np.random.normal(0, 0.1, num_segments)
            intervals = intervals * (1 + noise)
            intervals = np.maximum(intervals, self.min_interval)
            return intervals.tolist()
        else:
            raw = _poisson_pure_python(self.poisson_lambda, num_segments)
            raw = [max(r, 0.5) for r in raw]
            total_raw = sum(raw) or 1
            scale = total_hours / total_raw
            intervals = [r * scale for r in raw]
            intervals = [_clip(i, self.min_interval, self.max_interval) for i in intervals]
            return intervals

    # ─── Activity Level ──────────────────────────────────────────────

    def _calculate_activity_level(self, ts: datetime) -> str:
        hour = ts.hour
        weekend = ts.weekday() >= 5
        if weekend:
            return 'high' if 10 <= hour <= 22 else ('medium' if 8 <= hour <= 23 else 'low')
        else:
            if 9 <= hour <= 11 or 14 <= hour <= 16 or 19 <= hour <= 21:
                return 'high'
            return 'medium' if 7 <= hour <= 22 else 'low'

    def _generate_segment_actions(self, activity_level: str) -> List[str]:
        pools = {
            'high': ['browse_products', 'add_to_cart', 'search', 'watch_video',
                     'read_article', 'click_ads', 'form_submission', 'download',
                     'share_social', 'comment', 'review', 'purchase'],
            'medium': ['browse_homepage', 'read_article', 'search', 'scroll',
                       'click_link', 'view_image', 'check_email', 'update_profile'],
            'low': ['idle', 'scroll', 'refresh', 'check_notifications'],
        }
        counts = {'high': (5, 15), 'medium': (3, 8), 'low': (1, 3)}
        lo, hi = counts.get(activity_level, (3, 8))
        n = self._rng.randint(lo, hi)
        pool = pools.get(activity_level, pools['medium'])
        return [self._rng.choice(pool) for _ in range(n)]

    # ─── Circadian Pattern ───────────────────────────────────────────

    def generate_circadian_pattern(self, days: int) -> List[Dict]:
        """
        Generate activity pattern following circadian rhythm.

        Returns list of activity windows with day, period, start time, duration, intensity.
        """
        pattern = []
        for day in range(days):
            base = datetime.utcnow() - timedelta(days=days - day)

            windows = [
                ('morning', self._rng.randint(6, 7), self._rng.uniform(0.5, 2), 'medium'),
                ('midday', self._rng.randint(11, 12), self._rng.uniform(1, 2.5), 'medium'),
                ('evening', self._rng.randint(18, 20), self._rng.uniform(1.5, 3), 'high'),
            ]

            if self._rng.random() < 0.2:
                windows.append(('night', self._rng.randint(22, 23), self._rng.uniform(0.5, 1.5), 'low'))

            for period, hour, duration, intensity in windows:
                start = base.replace(hour=hour, minute=self._rng.randint(0, 59),
                                     second=0, microsecond=0)
                pattern.append({
                    'day': day,
                    'date': base,
                    'period': period,
                    'start': start,
                    'duration_hours': duration,
                    'intensity': intensity,
                })
        return pattern

    # ─── Organic Pause ───────────────────────────────────────────────

    def organic_pause(self, force_long: bool = False) -> float:
        """
        Generate organic browsing pause with realistic timing.

        Humans browse in bursts then pause 30-90s every 3-5 pages.
        Regular pauses 1-5s use gamma distribution for natural feel.

        Returns:
            Pause duration in seconds (also sleeps for that duration).
        """
        self.page_visit_count += 1
        should_long = (self.page_visit_count >= self.long_pause_threshold) or force_long

        if should_long:
            dur = _normal_pure_python(LONG_PAUSE_MEAN_SECONDS, LONG_PAUSE_STD_SECONDS)
            dur = _clip(dur, LONG_PAUSE_MIN_SECONDS, LONG_PAUSE_MAX_SECONDS)
            self.logger.info(f"[Organic Gap] Long pause after {self.page_visit_count} pages: {dur:.1f}s")
            self.page_visit_count = 0
            self.long_pause_threshold = random.randint(3, 5)
        else:
            if NUMPY_AVAILABLE:
                dur = float(np.random.gamma(2.0, 1.0))
            else:
                dur = self._rng.gammavariate(2.0, 1.0)
            dur = _clip(dur, REGULAR_PAUSE_MIN_SECONDS, REGULAR_PAUSE_MAX_SECONDS)

        time.sleep(dur)
        return dur

    # ─── Search Query Generation ─────────────────────────────────────

    def generate_search_query(self) -> str:
        """Generate a realistic search query for warmup browsing."""
        templates = [
            "best {} 2024", "how to {}", "{} reviews", "{} vs {}",
            "cheap {}", "{} near me", "{} tutorial", "buy {} online",
        ]
        topics = [
            "laptop", "phone", "shoes", "restaurant", "hotel",
            "camera", "headphones", "watch", "book", "course",
            "software", "game", "movie", "recipe", "workout",
        ]
        tpl = self._rng.choice(templates)
        if tpl.count('{}') == 2:
            return tpl.format(self._rng.choice(topics), self._rng.choice(topics))
        return tpl.format(self._rng.choice(topics))

    # ─── Mouse Path Generation ───────────────────────────────────────

    def generate_mouse_path(self, num_points: int = 5) -> List[Tuple[int, int]]:
        """Generate realistic random mouse path coordinates."""
        return [(self._rng.randint(100, 1800), self._rng.randint(100, 900))
                for _ in range(num_points)]

    def get_status(self) -> Dict[str, Any]:
        """Return module status for health checks."""
        return {
            "available": True,
            "numpy": NUMPY_AVAILABLE,
            "scipy": SCIPY_AVAILABLE,
            "poisson_lambda": self.poisson_lambda,
            "version": "8.1",
        }
