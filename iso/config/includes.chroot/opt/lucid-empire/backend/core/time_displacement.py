# LUCID EMPIRE :: TIME DISPLACEMENT
# Temporal offset management for profile aging
# V7.0: Bridges to /opt/titan/core/timezone_enforcer.py for system-level TZ control

import os
import sys
import datetime

# V7.0: Bridge to Titan timezone enforcer
sys.path.insert(0, "/opt/titan/core")
try:
    from timezone_enforcer import get_timezone_for_state, get_timezone_for_country
    TITAN_V6_AVAILABLE = True
except ImportError:
    TITAN_V6_AVAILABLE = False


class TimeDisplacement:
    """Manages temporal offsets for profile anti-detection.
    
    V7.0: Extended with timezone-aware displacement and
    TZ environment variable propagation for browser launch.
    """
    
    def __init__(self, days_offset=0, timezone=None):
        self.days_offset = days_offset
        self.timezone = timezone
    
    def get_displaced_time(self):
        """Get current time with displacement applied."""
        now = datetime.datetime.now()
        return now - datetime.timedelta(days=self.days_offset)
    
    def set_environment(self):
        """Set environment for libfaketime + timezone."""
        env = os.environ.copy()
        if self.days_offset > 0:
            env["FAKETIME"] = f"-{self.days_offset}d"
        if self.timezone:
            env["TZ"] = self.timezone
        return env
    
    def set_timezone_for_state(self, state):
        """V7.0: Set TZ based on US state abbreviation."""
        if TITAN_V6_AVAILABLE:
            self.timezone = get_timezone_for_state(state)
        else:
            self.timezone = "America/New_York"
        os.environ["TZ"] = self.timezone
        return self.timezone
    
    def set_timezone_for_country(self, country):
        """V7.0: Set TZ based on country code."""
        if TITAN_V6_AVAILABLE:
            self.timezone = get_timezone_for_country(country)
        else:
            self.timezone = "America/New_York"
        os.environ["TZ"] = self.timezone
        return self.timezone
