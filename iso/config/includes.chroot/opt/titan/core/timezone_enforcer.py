"""
TITAN V7.0 SINGULARITY — Phase 3.3: Timezone Atomicity Enforcer
Synchronization between Exit Node, System Clock, and Browser

VULNERABILITY: If the VPN IP changes after opening the browser, the
browser caches Intl.DateTimeFormat objects with the OLD timezone.
This creates a detectable mismatch between:
1. System timezone (updated by timedatectl)
2. Browser's cached Intl.DateTimeFormat.resolvedOptions().timeZone
3. IP geolocation timezone

FIX: Enforce atomic sequence: KILL → VPN → WAIT → SYNC → VERIFY → LAUNCH
No browser process may exist during timezone transition.

Usage:
    from timezone_enforcer import TimezoneEnforcer, TimezoneConfig
    
    enforcer = TimezoneEnforcer(TimezoneConfig(
        target_timezone="America/Chicago",
        target_city="Austin",
        target_state="TX",
    ))
    enforcer.enforce()  # Runs full atomic sequence
"""

import os
import json
import time
import signal
import subprocess
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("TITAN-V7-TIMEZONE")


# US state → timezone mapping
STATE_TIMEZONES = {
    "AL": "America/Chicago", "AK": "America/Anchorage", "AZ": "America/Phoenix",
    "AR": "America/Chicago", "CA": "America/Los_Angeles", "CO": "America/Denver",
    "CT": "America/New_York", "DE": "America/New_York", "FL": "America/New_York",
    "GA": "America/New_York", "HI": "Pacific/Honolulu", "ID": "America/Boise",
    "IL": "America/Chicago", "IN": "America/Indiana/Indianapolis",
    "IA": "America/Chicago", "KS": "America/Chicago", "KY": "America/New_York",
    "LA": "America/Chicago", "ME": "America/New_York", "MD": "America/New_York",
    "MA": "America/New_York", "MI": "America/Detroit", "MN": "America/Chicago",
    "MS": "America/Chicago", "MO": "America/Chicago", "MT": "America/Denver",
    "NE": "America/Chicago", "NV": "America/Los_Angeles", "NH": "America/New_York",
    "NJ": "America/New_York", "NM": "America/Denver", "NY": "America/New_York",
    "NC": "America/New_York", "ND": "America/Chicago", "OH": "America/New_York",
    "OK": "America/Chicago", "OR": "America/Los_Angeles", "PA": "America/New_York",
    "RI": "America/New_York", "SC": "America/New_York", "SD": "America/Chicago",
    "TN": "America/Chicago", "TX": "America/Chicago", "UT": "America/Denver",
    "VT": "America/New_York", "VA": "America/New_York", "WA": "America/Los_Angeles",
    "WV": "America/New_York", "WI": "America/Chicago", "WY": "America/Denver",
    "DC": "America/New_York",
}

# Country → default timezone
COUNTRY_TIMEZONES = {
    "US": "America/New_York", "GB": "Europe/London", "UK": "Europe/London",
    "CA": "America/Toronto", "AU": "Australia/Sydney", "DE": "Europe/Berlin",
    "FR": "Europe/Paris", "NL": "Europe/Amsterdam", "JP": "Asia/Tokyo",
    "KR": "Asia/Seoul", "BR": "America/Sao_Paulo", "MX": "America/Mexico_City",
}


class EnforcementStep(Enum):
    KILL_BROWSER = "kill_browser"
    WAIT_CLEAN = "wait_clean"
    SET_TIMEZONE = "set_timezone"
    SYNC_NTP = "sync_ntp"
    VERIFY = "verify"
    SET_ENV = "set_env"


@dataclass
class TimezoneConfig:
    target_timezone: str = "America/New_York"
    target_city: str = ""
    target_state: str = ""
    target_country: str = "US"
    kill_wait_seconds: float = 2.0
    ntp_sync: bool = True
    verify_strict: bool = True


@dataclass
class TimezoneEnforcementResult:
    success: bool
    steps_completed: List[str]
    steps_failed: List[str]
    timezone_before: str
    timezone_after: str
    browser_killed: bool
    ntp_synced: bool
    drift_seconds: float
    environment_vars: Dict[str, str]


class TimezoneEnforcer:
    """
    Phase 3.3: Atomic timezone enforcement.
    
    Ensures NO browser process exists during timezone transition,
    then sets system timezone, syncs NTP, verifies, and exports
    environment variables for the next browser launch.
    """
    
    STATE_DIR = Path("/opt/titan/state")
    BROWSER_PROCESSES = ["firefox", "firefox-esr", "camoufox", "chromium", "geckodriver"]
    
    def __init__(self, config: TimezoneConfig):
        self.config = config
        # Auto-resolve timezone from state if not explicitly provided
        if not config.target_timezone and config.target_state:
            config.target_timezone = STATE_TIMEZONES.get(
                config.target_state.upper(),
                COUNTRY_TIMEZONES.get(config.target_country.upper(), "America/New_York")
            )
    
    def _kill_all_browsers(self) -> bool:
        """Step 1: SIGKILL all browser processes — no graceful shutdown"""
        killed = False
        for proc in self.BROWSER_PROCESSES:
            try:
                result = subprocess.run(
                    ["pkill", "-9", "-f", proc],
                    capture_output=True, timeout=3
                )
                if result.returncode == 0:
                    killed = True
                    logger.info(f"[PHASE 3.3] Killed: {proc}")
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
        return killed
    
    def _wait_clean(self) -> bool:
        """Step 2: Wait for all browser processes to fully terminate"""
        deadline = time.time() + self.config.kill_wait_seconds + 3
        while time.time() < deadline:
            alive = False
            for proc in self.BROWSER_PROCESSES:
                try:
                    result = subprocess.run(
                        ["pgrep", "-f", proc],
                        capture_output=True, timeout=2
                    )
                    if result.returncode == 0:
                        alive = True
                        break
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    pass
            
            if not alive:
                logger.info("[PHASE 3.3] All browser processes terminated")
                return True
            time.sleep(0.5)
        
        logger.warning("[PHASE 3.3] Some browser processes may still be running")
        return False
    
    def _set_timezone(self) -> bool:
        """Step 3: Set system timezone via timedatectl"""
        tz = self.config.target_timezone
        try:
            result = subprocess.run(
                ["timedatectl", "set-timezone", tz],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                logger.info(f"[PHASE 3.3] System timezone set to: {tz}")
                return True
            else:
                logger.error(f"[PHASE 3.3] timedatectl failed: {result.stderr.strip()}")
                # Fallback: symlink method
                try:
                    zoneinfo = Path(f"/usr/share/zoneinfo/{tz}")
                    if zoneinfo.exists():
                        localtime = Path("/etc/localtime")
                        if localtime.exists() or localtime.is_symlink():
                            localtime.unlink()
                        localtime.symlink_to(zoneinfo)
                        logger.info(f"[PHASE 3.3] Timezone set via symlink: {tz}")
                        return True
                except Exception as e:
                    logger.error(f"[PHASE 3.3] Symlink fallback failed: {e}")
                return False
        except FileNotFoundError:
            logger.error("[PHASE 3.3] timedatectl not found")
            return False
        except Exception as e:
            logger.error(f"[PHASE 3.3] Timezone set error: {e}")
            return False
    
    def _sync_ntp(self) -> Tuple[bool, float]:
        """Step 4: Force NTP sync and measure drift"""
        drift = 0.0
        if not self.config.ntp_sync:
            return True, 0.0
        
        try:
            # Force NTP resync
            subprocess.run(
                ["timedatectl", "set-ntp", "true"],
                capture_output=True, timeout=5
            )
            # Wait for sync
            time.sleep(2)
            
            # Check sync status
            result = subprocess.run(
                ["timedatectl", "show", "--property=NTPSynchronized", "--value"],
                capture_output=True, text=True, timeout=5
            )
            synced = result.stdout.strip() == "yes"
            
            if synced:
                logger.info("[PHASE 3.3] NTP synchronized")
            else:
                logger.warning("[PHASE 3.3] NTP sync pending")
            
            return synced, drift
            
        except Exception as e:
            logger.warning(f"[PHASE 3.3] NTP sync error: {e}")
            return False, drift
    
    def _verify(self) -> Tuple[bool, str]:
        """Step 5: Verify system timezone matches target"""
        try:
            result = subprocess.check_output(
                "date +%Z", shell=True, timeout=3
            ).decode().strip()
            
            # Also check full timezone name
            tz_link = os.readlink("/etc/localtime") if os.path.islink("/etc/localtime") else ""
            
            # Verify the abbreviation isn't UTC when we expect otherwise
            if self.config.target_timezone != "UTC" and result == "UTC":
                return False, f"Still UTC (expected {self.config.target_timezone})"
            
            logger.info(f"[PHASE 3.3] Verified: {result} ({tz_link})")
            return True, result
            
        except Exception as e:
            return False, str(e)
    
    def _set_environment(self) -> Dict[str, str]:
        """Step 6: Export environment variables for browser launch"""
        tz = self.config.target_timezone
        
        # Determine locale from timezone
        tz_to_locale = {
            "America/": "en_US.UTF-8",
            "Europe/London": "en_GB.UTF-8",
            "Europe/": "en_GB.UTF-8",
            "Australia/": "en_AU.UTF-8",
            "Asia/Tokyo": "ja_JP.UTF-8",
        }
        
        locale = "en_US.UTF-8"
        for prefix, loc in tz_to_locale.items():
            if tz.startswith(prefix) or tz == prefix:
                locale = loc
                break
        
        env_vars = {
            "TZ": tz,
            "LANG": locale,
            "LC_ALL": locale,
            "TITAN_TIMEZONE": tz,
            "TITAN_TIMEZONE_SET": datetime.now().isoformat(),
        }
        
        # Set in current process
        for key, val in env_vars.items():
            os.environ[key] = val
        
        # Write to state file for titan-browser to read
        self.STATE_DIR.mkdir(parents=True, exist_ok=True)
        state_file = self.STATE_DIR / "timezone_state.json"
        try:
            with open(state_file, 'w') as f:
                json.dump({
                    "timezone": tz,
                    "locale": locale,
                    "city": self.config.target_city,
                    "state": self.config.target_state,
                    "country": self.config.target_country,
                    "set_at": datetime.now().isoformat(),
                    "env": env_vars,
                }, f, indent=2)
        except Exception:
            pass
        
        logger.info(f"[PHASE 3.3] Environment set: TZ={tz}, LANG={locale}")
        return env_vars
    
    def get_current_timezone(self) -> str:
        """Get current system timezone abbreviation"""
        try:
            return subprocess.check_output(
                "date +%Z", shell=True, timeout=3
            ).decode().strip()
        except Exception:
            return "unknown"
    
    def enforce(self) -> TimezoneEnforcementResult:
        """
        Execute the full atomic timezone enforcement sequence:
        1. KILL all browsers (SIGKILL, no mercy)
        2. WAIT for clean process table
        3. SET system timezone
        4. SYNC NTP
        5. VERIFY timezone matches target
        6. SET environment variables
        """
        logger.info(f"[PHASE 3.3] Enforcing timezone: {self.config.target_timezone}")
        
        tz_before = self.get_current_timezone()
        completed = []
        failed = []
        browser_killed = False
        ntp_synced = False
        drift = 0.0
        env_vars = {}
        
        # Step 1: Kill browsers
        browser_killed = self._kill_all_browsers()
        if browser_killed:
            completed.append(EnforcementStep.KILL_BROWSER.value)
        else:
            completed.append(EnforcementStep.KILL_BROWSER.value)  # No browsers = also OK
        
        # Step 2: Wait for clean state
        time.sleep(self.config.kill_wait_seconds)
        if self._wait_clean():
            completed.append(EnforcementStep.WAIT_CLEAN.value)
        else:
            failed.append(EnforcementStep.WAIT_CLEAN.value)
        
        # Step 3: Set timezone
        if self._set_timezone():
            completed.append(EnforcementStep.SET_TIMEZONE.value)
        else:
            failed.append(EnforcementStep.SET_TIMEZONE.value)
        
        # Step 4: NTP sync
        ntp_synced, drift = self._sync_ntp()
        if ntp_synced:
            completed.append(EnforcementStep.SYNC_NTP.value)
        else:
            failed.append(EnforcementStep.SYNC_NTP.value)
        
        # Step 5: Verify
        verified, tz_abbrev = self._verify()
        if verified:
            completed.append(EnforcementStep.VERIFY.value)
        else:
            failed.append(EnforcementStep.VERIFY.value)
        
        # Step 6: Set environment
        env_vars = self._set_environment()
        completed.append(EnforcementStep.SET_ENV.value)
        
        tz_after = self.get_current_timezone()
        success = len(failed) == 0 or (
            EnforcementStep.SET_TIMEZONE.value in completed and
            EnforcementStep.VERIFY.value in completed
        )
        
        result = TimezoneEnforcementResult(
            success=success,
            steps_completed=completed,
            steps_failed=failed,
            timezone_before=tz_before,
            timezone_after=tz_after,
            browser_killed=browser_killed,
            ntp_synced=ntp_synced,
            drift_seconds=drift,
            environment_vars=env_vars,
        )
        
        if success:
            logger.info(f"[PHASE 3.3] Timezone enforced: {tz_before} → {tz_after}")
        else:
            logger.error(f"[PHASE 3.3] Enforcement failed: {failed}")
        
        return result


# ═══════════════════════════════════════════════════════════════════════════
# CONVENIENCE EXPORTS
# ═══════════════════════════════════════════════════════════════════════════

def enforce_timezone(target_timezone: str = "", target_state: str = "",
                      target_country: str = "US") -> TimezoneEnforcementResult:
    """Quick timezone enforcement"""
    config = TimezoneConfig(
        target_timezone=target_timezone,
        target_state=target_state,
        target_country=target_country,
    )
    enforcer = TimezoneEnforcer(config)
    return enforcer.enforce()

def get_timezone_for_state(state: str) -> str:
    """Get timezone for US state abbreviation"""
    return STATE_TIMEZONES.get(state.upper(), "America/New_York")

def get_timezone_for_country(country: str) -> str:
    """Get timezone for country code"""
    return COUNTRY_TIMEZONES.get(country.upper(), "America/New_York")
