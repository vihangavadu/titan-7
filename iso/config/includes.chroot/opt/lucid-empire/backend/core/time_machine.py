# LUCID EMPIRE :: TIME MACHINE
# Advanced temporal manipulation for profile consistency
# V7.0: Bridges to /opt/titan/core/timezone_enforcer.py for atomic enforcement

import os
import sys
import time
import datetime

try:
    import pytz
except ImportError:
    pytz = None

# V7.0: Bridge to Titan timezone enforcer
sys.path.insert(0, "/opt/titan/core")
try:
    from timezone_enforcer import (
        TimezoneEnforcer, TimezoneConfig,
        enforce_timezone, get_timezone_for_state, get_timezone_for_country,
        STATE_TIMEZONES, COUNTRY_TIMEZONES,
    )
    TITAN_V6_AVAILABLE = True
except ImportError:
    TITAN_V6_AVAILABLE = False


class TimeMachine:
    """Advanced temporal control system.
    
    V7.0: Now delegates timezone enforcement to TimezoneEnforcer
    for atomic kill→VPN→sync→verify→launch sequencing.
    """
    
    def __init__(self, timezone="UTC"):
        if pytz:
            self.tz = pytz.timezone(timezone)
        else:
            self.tz = None
        self.timezone_str = timezone
        self.base_time = None
    
    def set_base_time(self, days_ago):
        """Set base time for profile."""
        now = datetime.datetime.now(self.tz) if self.tz else datetime.datetime.now()
        self.base_time = now - datetime.timedelta(days=days_ago)
    
    def get_time_progression(self, elapsed_seconds):
        """Calculate time progression from base."""
        if not self.base_time:
            return datetime.datetime.now(self.tz) if self.tz else datetime.datetime.now()
        return self.base_time + datetime.timedelta(seconds=elapsed_seconds)
    
    def sync_system_time(self):
        """Synchronize system time (read-only)."""
        return time.time()
    
    def enforce_timezone(self, target_timezone="", target_state="", target_country="US"):
        """V7.0: Atomic timezone enforcement via TimezoneEnforcer.
        
        Sequence: Kill browsers → Set TZ → NTP sync → Verify → Set env
        """
        if not TITAN_V6_AVAILABLE:
            # Fallback: just set TZ env var
            tz = target_timezone or self.timezone_str
            os.environ["TZ"] = tz
            return {"success": True, "timezone": tz, "method": "env_only"}
        
        result = enforce_timezone(
            target_timezone=target_timezone,
            target_state=target_state,
            target_country=target_country,
        )
        return {
            "success": result.success,
            "timezone_before": result.timezone_before,
            "timezone_after": result.timezone_after,
            "browser_killed": result.browser_killed,
            "ntp_synced": result.ntp_synced,
            "method": "titan_v6_enforcer",
        }
    
    @staticmethod
    def get_timezone_for_state(state):
        """V7.0: Get timezone for US state abbreviation."""
        if TITAN_V6_AVAILABLE:
            return get_timezone_for_state(state)
        return STATE_TIMEZONES.get(state.upper(), "America/New_York") if 'STATE_TIMEZONES' in dir() else "America/New_York"
    
    @staticmethod
    def get_timezone_for_country(country):
        """V7.0: Get timezone for country code."""
        if TITAN_V6_AVAILABLE:
            return get_timezone_for_country(country)
        return "America/New_York"
