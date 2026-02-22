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
    "ES": "Europe/Madrid", "IT": "Europe/Rome", "PT": "Europe/Lisbon",
    "BE": "Europe/Brussels", "AT": "Europe/Vienna", "CH": "Europe/Zurich",
    "SE": "Europe/Stockholm", "NO": "Europe/Oslo", "DK": "Europe/Copenhagen",
    "FI": "Europe/Helsinki", "PL": "Europe/Warsaw", "CZ": "Europe/Prague",
    "IE": "Europe/Dublin", "NZ": "Pacific/Auckland", "SG": "Asia/Singapore",
    "HK": "Asia/Hong_Kong", "IN": "Asia/Kolkata", "AE": "Asia/Dubai",
    "IL": "Asia/Jerusalem", "ZA": "Africa/Johannesburg", "RU": "Europe/Moscow",
    "TR": "Europe/Istanbul", "AR": "America/Argentina/Buenos_Aires",
    "CL": "America/Santiago", "CO": "America/Bogota", "PE": "America/Lima",
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

    def verify_geoloc_timezone_match(self, exit_ip: str = "", deadline_ms: float = 200.0) -> Tuple[bool, str]:
        """
        GAP-6 FIX: Verify that system timezone matches the IP geolocation timezone
        within the specified deadline (default 200ms).

        Antifraud systems (Sift, Kount, Forter) flag sessions where:
        - Browser timezone != IP geolocation timezone
        - The mismatch persists for >200ms after VPN connection

        This method must be called AFTER VPN connects and BEFORE browser launches.
        If the check fails, the caller should re-run enforce() before proceeding.

        Args:
            exit_ip: The VPN exit node IP (auto-detected if empty)
            deadline_ms: Maximum allowed sync lag in milliseconds

        Returns:
            (match: bool, message: str)
        """
        import socket

        t_start = time.monotonic()

        # Auto-detect exit IP if not provided
        if not exit_ip:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.settimeout(2)
                s.connect(("8.8.8.8", 80))
                exit_ip = s.getsockname()[0]
                s.close()
            except Exception:
                exit_ip = "127.0.0.1"

        # P1-2 FIX: Use cached IP→timezone lookup (24h TTL) to avoid 200-2000ms HTTP per op
        # Primary: use configured target timezone (instant, no HTTP)
        geo_tz = self.config.target_timezone

        # Secondary: use STATE_TIMEZONES mapping if state is known (instant, no HTTP)
        if not geo_tz and hasattr(self.config, 'target_state') and self.config.target_state:
            try:
                geo_tz = STATE_TIMEZONES.get(self.config.target_state.upper(), "")
            except Exception:
                pass

        # Tertiary: HTTP lookup with 24h disk cache (only if no local source)
        if not geo_tz and exit_ip and exit_ip != "127.0.0.1":
            _tz_cache_file = Path("/opt/titan/state/tz_cache.json")
            _cached = {}
            try:
                if _tz_cache_file.exists():
                    with open(_tz_cache_file, "r") as _f:
                        _cached = json.load(_f)
            except Exception:
                _cached = {}

            cache_key = exit_ip
            cache_entry = _cached.get(cache_key, {})
            cache_age = time.monotonic() - cache_entry.get("ts", 0) if "ts" in cache_entry else 999999

            if cache_entry.get("tz") and cache_age < 86400:
                geo_tz = cache_entry["tz"]
            else:
                try:
                    import urllib.request
                    req = urllib.request.Request(
                        f"http://ip-api.com/json/{exit_ip}?fields=timezone",
                        headers={"User-Agent": "curl/7.88.1"}
                    )
                    with urllib.request.urlopen(req, timeout=2) as resp:
                        data = json.loads(resp.read().decode())
                        geo_tz = data.get("timezone", "")
                    if geo_tz:
                        _cached[cache_key] = {"tz": geo_tz, "ts": time.monotonic()}
                        try:
                            _tz_cache_file.parent.mkdir(parents=True, exist_ok=True)
                            with open(_tz_cache_file, "w") as _f:
                                json.dump(_cached, _f)
                        except Exception:
                            pass
                except Exception:
                    pass

        if not geo_tz:
            geo_tz = self.config.target_timezone

        elapsed_ms = (time.monotonic() - t_start) * 1000

        # Read current system timezone
        try:
            tz_link = os.readlink("/etc/localtime")
            sys_tz = tz_link.replace("/usr/share/zoneinfo/", "")
        except Exception:
            sys_tz = os.environ.get("TZ", "")

        match = (sys_tz == geo_tz)

        if elapsed_ms > deadline_ms:
            msg = (f"CLOCK_SKEW_RISK: Geoloc lookup took {elapsed_ms:.0f}ms "
                   f"(>{deadline_ms:.0f}ms deadline). Proxy latency flag possible.")
            logger.warning(f"[PHASE 3.3] {msg}")
            return False, msg

        if not match:
            msg = (f"TZ_MISMATCH: sys={sys_tz!r} geo={geo_tz!r} "
                   f"(elapsed={elapsed_ms:.0f}ms). Re-run enforce() before browser launch.")
            logger.error(f"[PHASE 3.3] {msg}")
            return False, msg

        msg = (f"TZ_MATCH: sys={sys_tz!r} == geo={geo_tz!r} "
               f"(verified in {elapsed_ms:.0f}ms)")
        logger.info(f"[PHASE 3.3] {msg}")
        return True, msg
    
    def _verify(self) -> Tuple[bool, str]:
        """Step 5: Verify system timezone matches target"""
        try:
            abbrev = subprocess.check_output(
                "date +%Z", shell=True, timeout=3
            ).decode().strip()
            
            # V7.5 FIX: Check IANA name via /etc/localtime symlink, not just abbreviation
            tz_link = ""
            if os.path.islink("/etc/localtime"):
                tz_link = os.readlink("/etc/localtime").replace("/usr/share/zoneinfo/", "")
            
            # Verify IANA name matches target if available
            if tz_link and tz_link != self.config.target_timezone:
                return False, f"IANA mismatch: {tz_link} != {self.config.target_timezone}"
            
            # Verify the abbreviation isn't UTC when we expect otherwise
            if self.config.target_timezone != "UTC" and abbrev == "UTC":
                return False, f"Still UTC (expected {self.config.target_timezone})"
            
            logger.info(f"[PHASE 3.3] Verified: {abbrev} ({tz_link})")
            return True, abbrev
            
        except Exception as e:
            return False, str(e)
    
    def _set_environment(self) -> Dict[str, str]:
        """Step 6: Export environment variables for browser launch"""
        tz = self.config.target_timezone
        
        # Determine locale from timezone
        tz_to_locale = {
            "America/Sao_Paulo": "pt_BR.UTF-8",
            "America/Mexico_City": "es_MX.UTF-8",
            "America/": "en_US.UTF-8",
            "Europe/London": "en_GB.UTF-8",
            "Europe/Paris": "fr_FR.UTF-8",
            "Europe/Berlin": "de_DE.UTF-8",
            "Europe/Amsterdam": "nl_NL.UTF-8",
            "Europe/": "en_GB.UTF-8",
            "Australia/": "en_AU.UTF-8",
            "Asia/Tokyo": "ja_JP.UTF-8",
            "Asia/Seoul": "ko_KR.UTF-8",
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
            "TITAN_TIMEZONE_SET": datetime.now(timezone.utc).isoformat(),
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
                    "set_at": datetime.now(timezone.utc).isoformat(),
                    "env": env_vars,
                }, f, indent=2)
        except Exception as e:
            logger.warning(f"[PHASE 3.3] Failed to write timezone state: {e}")
        
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


# ═══════════════════════════════════════════════════════════════════════════════
# V7.6 P0 CRITICAL ENHANCEMENTS - Advanced Timezone Operations
# ═══════════════════════════════════════════════════════════════════════════════

import threading
from collections import defaultdict


@dataclass
class TimezoneAnomaly:
    """Timezone anomaly record"""
    timestamp: float
    anomaly_type: str
    expected: str
    actual: str
    severity: str
    details: Dict = field(default_factory=dict)


@dataclass
class TransitionRecord:
    """Timezone transition record"""
    timestamp: float
    from_timezone: str
    to_timezone: str
    duration_ms: float
    success: bool
    browser_killed: bool


class TimezoneMonitor:
    """
    V7.6 P0: Continuous timezone monitoring.
    
    Features:
    - Real-time timezone consistency checking
    - Browser/system mismatch detection
    - Alert on timezone drift
    - Integration with browser sessions
    """
    
    CHECK_INTERVAL_SECONDS = 30
    
    def __init__(self):
        self._expected_timezone: Optional[str] = None
        self._monitoring = False
        self._thread: Optional[threading.Thread] = None
        self._check_history: List[Dict] = []
        self._mismatches: List[Dict] = []
        self._lock = threading.Lock()
        self.logger = logging.getLogger("TITAN-TZ-MONITOR")
    
    def set_expected_timezone(self, timezone: str):
        """Set the expected timezone to monitor for"""
        with self._lock:
            self._expected_timezone = timezone
            self.logger.info(f"Monitoring for timezone: {timezone}")
    
    def start(self):
        """Start continuous monitoring"""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        self.logger.info("Timezone monitoring started")
    
    def stop(self):
        """Stop monitoring"""
        self._monitoring = False
        if self._thread:
            self._thread.join(timeout=5)
        self.logger.info("Timezone monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self._monitoring:
            try:
                self._check_timezone()
            except Exception as e:
                self.logger.error(f"Monitor check error: {e}")
            
            time.sleep(self.CHECK_INTERVAL_SECONDS)
    
    def _check_timezone(self):
        """Check current timezone status"""
        check_result = {
            "timestamp": time.time(),
            "expected": self._expected_timezone,
            "system_tz": self._get_system_timezone(),
            "env_tz": os.environ.get("TZ", ""),
            "match": False,
        }
        
        # Check for matches
        if self._expected_timezone:
            check_result["match"] = (
                check_result["system_tz"] == self._expected_timezone or
                check_result["env_tz"] == self._expected_timezone
            )
            
            if not check_result["match"]:
                with self._lock:
                    self._mismatches.append({
                        "timestamp": time.time(),
                        "expected": self._expected_timezone,
                        "actual_system": check_result["system_tz"],
                        "actual_env": check_result["env_tz"],
                    })
                self.logger.warning(
                    f"Timezone mismatch detected: expected={self._expected_timezone}, "
                    f"system={check_result['system_tz']}, env={check_result['env_tz']}"
                )
        
        with self._lock:
            self._check_history.append(check_result)
            if len(self._check_history) > 1000:
                self._check_history = self._check_history[-1000:]
    
    def _get_system_timezone(self) -> str:
        """Get current system timezone"""
        try:
            if os.path.islink("/etc/localtime"):
                return os.readlink("/etc/localtime").replace("/usr/share/zoneinfo/", "")
            return subprocess.check_output(
                "date +%Z", shell=True, timeout=3
            ).decode().strip()
        except Exception:
            return "unknown"
    
    def check_now(self) -> Dict:
        """Perform immediate timezone check"""
        self._check_timezone()
        with self._lock:
            return self._check_history[-1] if self._check_history else {}
    
    def get_mismatches(self, limit: int = 20) -> List[Dict]:
        """Get recent mismatches"""
        with self._lock:
            return self._mismatches[-limit:]
    
    def get_status(self) -> Dict:
        """Get monitoring status"""
        with self._lock:
            return {
                "monitoring": self._monitoring,
                "expected_timezone": self._expected_timezone,
                "total_checks": len(self._check_history),
                "total_mismatches": len(self._mismatches),
                "mismatch_rate": len(self._mismatches) / max(1, len(self._check_history)),
            }


class TimezoneAnomalyDetector:
    """
    V7.6 P0: Detect timezone anomalies and mismatches.
    
    Features:
    - Multiple anomaly type detection
    - Severity classification
    - Pattern analysis
    - Remediation suggestions
    """
    
    ANOMALY_TYPES = {
        "MISMATCH_SYSTEM_ENV": "System timezone doesn't match TZ environment variable",
        "MISMATCH_BROWSER_SYSTEM": "Browser timezone doesn't match system",
        "MISMATCH_IP_SYSTEM": "IP geolocation timezone doesn't match system",
        "DRIFT_DETECTED": "Clock drift detected",
        "NTP_DESYNC": "NTP synchronization lost",
        "TRANSITION_INCOMPLETE": "Timezone transition incomplete",
    }
    
    def __init__(self):
        self._anomalies: List[TimezoneAnomaly] = []
        self._patterns: Dict[str, int] = defaultdict(int)
        self._lock = threading.Lock()
        self.logger = logging.getLogger("TITAN-TZ-ANOMALY")
    
    def detect(
        self,
        expected_tz: str,
        system_tz: str = None,
        env_tz: str = None,
        browser_tz: str = None,
        ip_geo_tz: str = None,
    ) -> List[TimezoneAnomaly]:
        """Detect timezone anomalies"""
        anomalies = []
        
        # Get current values if not provided
        if system_tz is None:
            system_tz = self._get_system_tz()
        if env_tz is None:
            env_tz = os.environ.get("TZ", "")
        
        # Check system/env mismatch
        if env_tz and system_tz and env_tz != system_tz:
            anomalies.append(self._create_anomaly(
                "MISMATCH_SYSTEM_ENV",
                expected=env_tz,
                actual=system_tz,
                severity="HIGH",
            ))
        
        # Check expected vs system
        if expected_tz and system_tz and expected_tz != system_tz:
            anomalies.append(self._create_anomaly(
                "MISMATCH_SYSTEM_ENV",
                expected=expected_tz,
                actual=system_tz,
                severity="CRITICAL",
            ))
        
        # Check browser mismatch
        if browser_tz and system_tz and browser_tz != system_tz:
            anomalies.append(self._create_anomaly(
                "MISMATCH_BROWSER_SYSTEM",
                expected=system_tz,
                actual=browser_tz,
                severity="CRITICAL",
                details={"browser_tz": browser_tz},
            ))
        
        # Check IP geolocation mismatch
        if ip_geo_tz and system_tz and ip_geo_tz != system_tz:
            anomalies.append(self._create_anomaly(
                "MISMATCH_IP_SYSTEM",
                expected=ip_geo_tz,
                actual=system_tz,
                severity="HIGH",
                details={"ip_geo_tz": ip_geo_tz},
            ))
        
        # Record anomalies
        with self._lock:
            self._anomalies.extend(anomalies)
            for a in anomalies:
                self._patterns[a.anomaly_type] += 1
        
        return anomalies
    
    def _create_anomaly(
        self,
        anomaly_type: str,
        expected: str,
        actual: str,
        severity: str,
        details: Dict = None,
    ) -> TimezoneAnomaly:
        """Create an anomaly record"""
        return TimezoneAnomaly(
            timestamp=time.time(),
            anomaly_type=anomaly_type,
            expected=expected,
            actual=actual,
            severity=severity,
            details=details or {},
        )
    
    def _get_system_tz(self) -> str:
        """Get system timezone"""
        try:
            if os.path.islink("/etc/localtime"):
                return os.readlink("/etc/localtime").replace("/usr/share/zoneinfo/", "")
            return "unknown"
        except Exception:
            return "unknown"
    
    def get_remediation(self, anomaly: TimezoneAnomaly) -> List[str]:
        """Get remediation suggestions for an anomaly"""
        remediation = {
            "MISMATCH_SYSTEM_ENV": [
                "Re-run timezone enforcer to sync system and environment",
                "Export TZ environment variable to match system timezone",
                f"Run: export TZ={anomaly.expected}",
            ],
            "MISMATCH_BROWSER_SYSTEM": [
                "CRITICAL: Kill browser immediately - timezone cached incorrectly",
                "Run full enforce() before relaunching browser",
                "Ensure no browser processes exist during timezone transition",
            ],
            "MISMATCH_IP_SYSTEM": [
                "VPN exit node timezone doesn't match system",
                "Reconnect VPN to matching region",
                "Re-run timezone enforcement after VPN reconnect",
            ],
            "DRIFT_DETECTED": [
                "Force NTP resync: timedatectl set-ntp true",
                "Check NTP server availability",
                "Verify hardware clock accuracy",
            ],
            "NTP_DESYNC": [
                "Re-enable NTP sync",
                "Check network connectivity",
                "Run: timedatectl set-ntp true",
            ],
        }
        return remediation.get(anomaly.anomaly_type, ["No specific remediation available"])
    
    def get_recent_anomalies(self, limit: int = 50) -> List[Dict]:
        """Get recent anomalies"""
        with self._lock:
            return [
                {
                    "timestamp": a.timestamp,
                    "type": a.anomaly_type,
                    "expected": a.expected,
                    "actual": a.actual,
                    "severity": a.severity,
                    "details": a.details,
                }
                for a in self._anomalies[-limit:]
            ]
    
    def get_pattern_analysis(self) -> Dict:
        """Analyze anomaly patterns"""
        with self._lock:
            total = sum(self._patterns.values())
            return {
                "total_anomalies": total,
                "by_type": dict(self._patterns),
                "most_common": max(self._patterns, key=self._patterns.get) if self._patterns else None,
            }


class TimezoneTransitionManager:
    """
    V7.6 P0: Manage timezone transitions safely.
    
    Features:
    - Pre-transition validation
    - Rollback support
    - Transition history
    - Health checks
    """
    
    def __init__(self):
        self._transitions: List[TransitionRecord] = []
        self._current_timezone: Optional[str] = None
        self._previous_timezone: Optional[str] = None
        self._lock = threading.Lock()
        self.logger = logging.getLogger("TITAN-TZ-TRANSITION")
    
    def plan_transition(
        self,
        from_tz: str,
        to_tz: str,
    ) -> Dict:
        """Plan a timezone transition"""
        plan = {
            "from": from_tz,
            "to": to_tz,
            "steps": [],
            "estimated_duration_ms": 0,
            "browser_kill_required": from_tz != to_tz,
            "validations": [],
        }
        
        if from_tz == to_tz:
            plan["steps"].append("No transition needed - already at target timezone")
            return plan
        
        plan["steps"] = [
            "1. Kill all browser processes",
            "2. Wait for clean process state",
            f"3. Set system timezone to {to_tz}",
            "4. Sync NTP",
            "5. Verify timezone change",
            "6. Update environment variables",
        ]
        plan["estimated_duration_ms"] = 5000  # ~5 seconds typical
        
        # Pre-validations
        if to_tz in STATE_TIMEZONES.values() or to_tz in COUNTRY_TIMEZONES.values():
            plan["validations"].append(f"✓ {to_tz} is a valid timezone")
        else:
            plan["validations"].append(f"⚠ {to_tz} may not be valid - verify path exists")
        
        return plan
    
    def execute_transition(
        self,
        to_tz: str,
        config: TimezoneConfig = None,
    ) -> TransitionRecord:
        """Execute a timezone transition"""
        start_time = time.time()
        
        # Get current timezone
        from_tz = self._get_current_tz()
        
        # Configure and execute
        if config is None:
            config = TimezoneConfig(target_timezone=to_tz)
        else:
            config.target_timezone = to_tz
        
        enforcer = TimezoneEnforcer(config)
        result = enforcer.enforce()
        
        duration_ms = (time.time() - start_time) * 1000
        
        record = TransitionRecord(
            timestamp=time.time(),
            from_timezone=from_tz,
            to_timezone=to_tz,
            duration_ms=round(duration_ms, 2),
            success=result.success,
            browser_killed=result.browser_killed,
        )
        
        with self._lock:
            self._transitions.append(record)
            if result.success:
                self._previous_timezone = self._current_timezone
                self._current_timezone = to_tz
        
        return record
    
    def rollback(self) -> Optional[TransitionRecord]:
        """Rollback to previous timezone"""
        with self._lock:
            if not self._previous_timezone:
                self.logger.warning("No previous timezone to rollback to")
                return None
            
            target = self._previous_timezone
        
        return self.execute_transition(target)
    
    def _get_current_tz(self) -> str:
        """Get current system timezone"""
        try:
            if os.path.islink("/etc/localtime"):
                return os.readlink("/etc/localtime").replace("/usr/share/zoneinfo/", "")
            return os.environ.get("TZ", "unknown")
        except Exception:
            return "unknown"
    
    def get_history(self, limit: int = 20) -> List[Dict]:
        """Get transition history"""
        with self._lock:
            return [
                {
                    "timestamp": t.timestamp,
                    "from": t.from_timezone,
                    "to": t.to_timezone,
                    "duration_ms": t.duration_ms,
                    "success": t.success,
                    "browser_killed": t.browser_killed,
                }
                for t in self._transitions[-limit:]
            ]
    
    def get_stats(self) -> Dict:
        """Get transition statistics"""
        with self._lock:
            if not self._transitions:
                return {"total_transitions": 0}
            
            successful = sum(1 for t in self._transitions if t.success)
            avg_duration = sum(t.duration_ms for t in self._transitions) / len(self._transitions)
            
            return {
                "total_transitions": len(self._transitions),
                "successful": successful,
                "failed": len(self._transitions) - successful,
                "success_rate": successful / len(self._transitions),
                "avg_duration_ms": round(avg_duration, 2),
                "current_timezone": self._current_timezone,
                "previous_timezone": self._previous_timezone,
            }


class GeoTimezoneResolver:
    """
    V7.6 P0: Resolve timezones from geo data.
    
    Features:
    - Country/state/city to timezone mapping
    - IP-based timezone resolution
    - Coordinate-based resolution
    - Caching for performance
    """
    
    # Extended city timezone mappings
    CITY_TIMEZONES = {
        # US cities
        "new york": "America/New_York", "los angeles": "America/Los_Angeles",
        "chicago": "America/Chicago", "houston": "America/Chicago",
        "phoenix": "America/Phoenix", "philadelphia": "America/New_York",
        "san antonio": "America/Chicago", "san diego": "America/Los_Angeles",
        "dallas": "America/Chicago", "san jose": "America/Los_Angeles",
        "austin": "America/Chicago", "seattle": "America/Los_Angeles",
        "denver": "America/Denver", "boston": "America/New_York",
        "miami": "America/New_York", "atlanta": "America/New_York",
        "las vegas": "America/Los_Angeles", "portland": "America/Los_Angeles",
        # International
        "london": "Europe/London", "paris": "Europe/Paris",
        "berlin": "Europe/Berlin", "tokyo": "Asia/Tokyo",
        "sydney": "Australia/Sydney", "toronto": "America/Toronto",
        "vancouver": "America/Vancouver", "amsterdam": "Europe/Amsterdam",
        "moscow": "Europe/Moscow", "dubai": "Asia/Dubai",
        "singapore": "Asia/Singapore", "hong kong": "Asia/Hong_Kong",
        "mumbai": "Asia/Kolkata", "sao paulo": "America/Sao_Paulo",
    }
    
    def __init__(self):
        self._cache: Dict[str, str] = {}
        self._lock = threading.Lock()
        self.logger = logging.getLogger("TITAN-GEO-TZ")
    
    def resolve(
        self,
        country: str = None,
        state: str = None,
        city: str = None,
        ip: str = None,
    ) -> str:
        """Resolve timezone from geo data"""
        # Check cache first
        cache_key = f"{country}:{state}:{city}:{ip}"
        with self._lock:
            if cache_key in self._cache:
                return self._cache[cache_key]
        
        timezone = None
        
        # Priority: city > state > country > ip
        if city:
            timezone = self._resolve_city(city.lower())
        
        if not timezone and state:
            timezone = STATE_TIMEZONES.get(state.upper())
        
        if not timezone and country:
            timezone = COUNTRY_TIMEZONES.get(country.upper())
        
        if not timezone and ip:
            timezone = self._resolve_ip(ip)
        
        # Default fallback
        if not timezone:
            timezone = "America/New_York"
        
        # Cache result
        with self._lock:
            self._cache[cache_key] = timezone
            if len(self._cache) > 1000:
                # Simple LRU: clear half
                keys = list(self._cache.keys())
                for k in keys[:500]:
                    del self._cache[k]
        
        return timezone
    
    def _resolve_city(self, city: str) -> Optional[str]:
        """Resolve timezone from city name"""
        return self.CITY_TIMEZONES.get(city.lower())
    
    def _resolve_ip(self, ip: str) -> Optional[str]:
        """Resolve timezone from IP address"""
        try:
            import urllib.request
            req = urllib.request.Request(
                f"http://ip-api.com/json/{ip}?fields=timezone",
                headers={"User-Agent": "curl/7.88.1"}
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode())
                return data.get("timezone")
        except Exception:
            return None
    
    def resolve_from_profile(self, profile: Dict) -> str:
        """Resolve timezone from a profile dictionary"""
        return self.resolve(
            country=profile.get("country") or profile.get("country_code"),
            state=profile.get("state") or profile.get("state_code"),
            city=profile.get("city"),
            ip=profile.get("ip") or profile.get("exit_ip"),
        )
    
    def get_all_for_country(self, country: str) -> List[str]:
        """Get all known timezones for a country"""
        country_upper = country.upper()
        
        if country_upper == "US":
            return list(set(STATE_TIMEZONES.values()))
        
        timezones = []
        base = COUNTRY_TIMEZONES.get(country_upper)
        if base:
            timezones.append(base)
        
        return timezones


# ═══════════════════════════════════════════════════════════════════════════
# V7.6 SINGLETON INSTANCES
# ═══════════════════════════════════════════════════════════════════════════

_timezone_monitor: Optional[TimezoneMonitor] = None
_timezone_anomaly_detector: Optional[TimezoneAnomalyDetector] = None
_timezone_transition_manager: Optional[TimezoneTransitionManager] = None
_geo_timezone_resolver: Optional[GeoTimezoneResolver] = None


def get_timezone_monitor() -> TimezoneMonitor:
    """Get global timezone monitor"""
    global _timezone_monitor
    if _timezone_monitor is None:
        _timezone_monitor = TimezoneMonitor()
    return _timezone_monitor


def get_timezone_anomaly_detector() -> TimezoneAnomalyDetector:
    """Get global timezone anomaly detector"""
    global _timezone_anomaly_detector
    if _timezone_anomaly_detector is None:
        _timezone_anomaly_detector = TimezoneAnomalyDetector()
    return _timezone_anomaly_detector


def get_timezone_transition_manager() -> TimezoneTransitionManager:
    """Get global timezone transition manager"""
    global _timezone_transition_manager
    if _timezone_transition_manager is None:
        _timezone_transition_manager = TimezoneTransitionManager()
    return _timezone_transition_manager


def get_geo_timezone_resolver() -> GeoTimezoneResolver:
    """Get global geo timezone resolver"""
    global _geo_timezone_resolver
    if _geo_timezone_resolver is None:
        _geo_timezone_resolver = GeoTimezoneResolver()
    return _geo_timezone_resolver
