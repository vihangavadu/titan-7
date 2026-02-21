"""
TITAN V7.0 SINGULARITY - Linux Location Spoofer
Cross-platform location spoofing for Linux-based TITAN OS

Implements location spoofing without Windows registry:
1. Firefox geo.provider overrides via user.js
2. System timezone modification
3. Locale environment variables
4. Browser geolocation API injection
"""

import os
import json
import subprocess
from pathlib import Path
from typing import Dict, Optional, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger("TITAN-V7-LOCATION")


@dataclass
class GeoCoordinates:
    """Geographic coordinates with accuracy"""
    latitude: float
    longitude: float
    accuracy: float = 100.0  # meters
    altitude: Optional[float] = None


@dataclass
class LocationProfile:
    """Complete location profile for spoofing"""
    coordinates: GeoCoordinates
    timezone: str
    locale: str
    language: str
    country_code: str
    region: str
    city: str
    postal_code: str


# Comprehensive location database
LOCATION_DATABASE: Dict[str, LocationProfile] = {
    # United States
    "us_new_york": LocationProfile(
        coordinates=GeoCoordinates(40.7128, -74.0060, 100.0),
        timezone="America/New_York",
        locale="en_US.UTF-8",
        language="en-US,en",
        country_code="US",
        region="New York",
        city="New York",
        postal_code="10001"
    ),
    "us_los_angeles": LocationProfile(
        coordinates=GeoCoordinates(34.0522, -118.2437, 100.0),
        timezone="America/Los_Angeles",
        locale="en_US.UTF-8",
        language="en-US,en",
        country_code="US",
        region="California",
        city="Los Angeles",
        postal_code="90001"
    ),
    "us_chicago": LocationProfile(
        coordinates=GeoCoordinates(41.8781, -87.6298, 100.0),
        timezone="America/Chicago",
        locale="en_US.UTF-8",
        language="en-US,en",
        country_code="US",
        region="Illinois",
        city="Chicago",
        postal_code="60601"
    ),
    "us_houston": LocationProfile(
        coordinates=GeoCoordinates(29.7604, -95.3698, 100.0),
        timezone="America/Chicago",
        locale="en_US.UTF-8",
        language="en-US,en",
        country_code="US",
        region="Texas",
        city="Houston",
        postal_code="77001"
    ),
    "us_phoenix": LocationProfile(
        coordinates=GeoCoordinates(33.4484, -112.0740, 100.0),
        timezone="America/Phoenix",
        locale="en_US.UTF-8",
        language="en-US,en",
        country_code="US",
        region="Arizona",
        city="Phoenix",
        postal_code="85001"
    ),
    "us_austin": LocationProfile(
        coordinates=GeoCoordinates(30.2672, -97.7431, 100.0),
        timezone="America/Chicago",
        locale="en_US.UTF-8",
        language="en-US,en",
        country_code="US",
        region="Texas",
        city="Austin",
        postal_code="78701"
    ),
    "us_seattle": LocationProfile(
        coordinates=GeoCoordinates(47.6062, -122.3321, 100.0),
        timezone="America/Los_Angeles",
        locale="en_US.UTF-8",
        language="en-US,en",
        country_code="US",
        region="Washington",
        city="Seattle",
        postal_code="98101"
    ),
    "us_miami": LocationProfile(
        coordinates=GeoCoordinates(25.7617, -80.1918, 100.0),
        timezone="America/New_York",
        locale="en_US.UTF-8",
        language="en-US,en",
        country_code="US",
        region="Florida",
        city="Miami",
        postal_code="33101"
    ),
    # United Kingdom
    "uk_london": LocationProfile(
        coordinates=GeoCoordinates(51.5074, -0.1278, 100.0),
        timezone="Europe/London",
        locale="en_GB.UTF-8",
        language="en-GB,en",
        country_code="GB",
        region="England",
        city="London",
        postal_code="EC1A 1BB"
    ),
    "uk_manchester": LocationProfile(
        coordinates=GeoCoordinates(53.4808, -2.2426, 100.0),
        timezone="Europe/London",
        locale="en_GB.UTF-8",
        language="en-GB,en",
        country_code="GB",
        region="England",
        city="Manchester",
        postal_code="M1 1AE"
    ),
    # Canada
    "ca_toronto": LocationProfile(
        coordinates=GeoCoordinates(43.6532, -79.3832, 100.0),
        timezone="America/Toronto",
        locale="en_CA.UTF-8",
        language="en-CA,en",
        country_code="CA",
        region="Ontario",
        city="Toronto",
        postal_code="M5H 2N2"
    ),
    "ca_vancouver": LocationProfile(
        coordinates=GeoCoordinates(49.2827, -123.1207, 100.0),
        timezone="America/Vancouver",
        locale="en_CA.UTF-8",
        language="en-CA,en",
        country_code="CA",
        region="British Columbia",
        city="Vancouver",
        postal_code="V6B 1A1"
    ),
    # Australia
    "au_sydney": LocationProfile(
        coordinates=GeoCoordinates(-33.8688, 151.2093, 100.0),
        timezone="Australia/Sydney",
        locale="en_AU.UTF-8",
        language="en-AU,en",
        country_code="AU",
        region="New South Wales",
        city="Sydney",
        postal_code="2000"
    ),
    "au_melbourne": LocationProfile(
        coordinates=GeoCoordinates(-37.8136, 144.9631, 100.0),
        timezone="Australia/Melbourne",
        locale="en_AU.UTF-8",
        language="en-AU,en",
        country_code="AU",
        region="Victoria",
        city="Melbourne",
        postal_code="3000"
    ),
    # Germany
    "de_berlin": LocationProfile(
        coordinates=GeoCoordinates(52.5200, 13.4050, 100.0),
        timezone="Europe/Berlin",
        locale="de_DE.UTF-8",
        language="de-DE,de,en",
        country_code="DE",
        region="Berlin",
        city="Berlin",
        postal_code="10115"
    ),
    # France
    "fr_paris": LocationProfile(
        coordinates=GeoCoordinates(48.8566, 2.3522, 100.0),
        timezone="Europe/Paris",
        locale="fr_FR.UTF-8",
        language="fr-FR,fr,en",
        country_code="FR",
        region="Île-de-France",
        city="Paris",
        postal_code="75001"
    ),
    # Netherlands
    "nl_amsterdam": LocationProfile(
        coordinates=GeoCoordinates(52.3676, 4.9041, 100.0),
        timezone="Europe/Amsterdam",
        locale="nl_NL.UTF-8",
        language="nl-NL,nl,en",
        country_code="NL",
        region="North Holland",
        city="Amsterdam",
        postal_code="1012"
    ),
    # Spain
    "es_madrid": LocationProfile(
        coordinates=GeoCoordinates(40.4168, -3.7038, 100.0),
        timezone="Europe/Madrid",
        locale="es_ES.UTF-8",
        language="es-ES,es,en",
        country_code="ES",
        region="Madrid",
        city="Madrid",
        postal_code="28001"
    ),
    # Italy
    "it_rome": LocationProfile(
        coordinates=GeoCoordinates(41.9028, 12.4964, 100.0),
        timezone="Europe/Rome",
        locale="it_IT.UTF-8",
        language="it-IT,it,en",
        country_code="IT",
        region="Lazio",
        city="Rome",
        postal_code="00100"
    ),
    # Additional US cities
    "us_dallas": LocationProfile(
        coordinates=GeoCoordinates(32.7767, -96.7970, 100.0),
        timezone="America/Chicago",
        locale="en_US.UTF-8",
        language="en-US,en",
        country_code="US",
        region="Texas",
        city="Dallas",
        postal_code="75201"
    ),
    "us_denver": LocationProfile(
        coordinates=GeoCoordinates(39.7392, -104.9903, 100.0),
        timezone="America/Denver",
        locale="en_US.UTF-8",
        language="en-US,en",
        country_code="US",
        region="Colorado",
        city="Denver",
        postal_code="80201"
    ),
    "us_atlanta": LocationProfile(
        coordinates=GeoCoordinates(33.7490, -84.3880, 100.0),
        timezone="America/New_York",
        locale="en_US.UTF-8",
        language="en-US,en",
        country_code="US",
        region="Georgia",
        city="Atlanta",
        postal_code="30301"
    ),
    "us_san_francisco": LocationProfile(
        coordinates=GeoCoordinates(37.7749, -122.4194, 100.0),
        timezone="America/Los_Angeles",
        locale="en_US.UTF-8",
        language="en-US,en",
        country_code="US",
        region="California",
        city="San Francisco",
        postal_code="94102"
    ),
    "us_boston": LocationProfile(
        coordinates=GeoCoordinates(42.3601, -71.0589, 100.0),
        timezone="America/New_York",
        locale="en_US.UTF-8",
        language="en-US,en",
        country_code="US",
        region="Massachusetts",
        city="Boston",
        postal_code="02101"
    ),
}


class LinuxLocationSpoofer:
    """
    Location spoofing for Linux-based systems.
    
    Usage:
        spoofer = LinuxLocationSpoofer()
        
        # Get profile for billing address
        profile = spoofer.get_profile_for_address({
            "country": "US",
            "city": "New York",
            "state": "NY"
        })
        
        # Apply to Firefox profile
        spoofer.apply_to_firefox_profile("/path/to/profile", profile)
        
        # Get environment variables
        env = spoofer.get_environment_vars(profile)
    """
    
    def __init__(self):
        self.database = LOCATION_DATABASE
    
    def get_profile(self, key: str) -> Optional[LocationProfile]:
        """Get location profile by key"""
        return self.database.get(key)
    
    def get_profile_for_address(self, address: Dict[str, str],
                                profile_seed: int = None) -> Optional[LocationProfile]:
        """
        Get location profile matching billing address.
        
        Args:
            address: Dict with country, city, state, zip
            profile_seed: Optional seed for coordinate jitter (use profile UUID hash)
            
        Returns:
            Best matching LocationProfile with per-profile coordinate jitter
        """
        country = address.get("country", "US").upper()
        city = address.get("city", "").lower().replace(" ", "_")
        state = address.get("state", "").lower()
        
        # Helper for jitter
        def _maybe_jitter(p):
            return self._apply_coordinate_jitter(p, profile_seed) if profile_seed else p
        
        # Try exact city match
        key = f"{country.lower()}_{city}"
        if key in self.database:
            return _maybe_jitter(self.database[key])
        
        # Try state-based match for US
        if country == "US":
            state_cities = {
                "ny": "us_new_york",
                "new york": "us_new_york",
                "nj": "us_new_york",
                "ct": "us_new_york",
                "ca": "us_los_angeles",
                "california": "us_los_angeles",
                "il": "us_chicago",
                "illinois": "us_chicago",
                "in": "us_chicago",
                "wi": "us_chicago",
                "tx": "us_houston",
                "texas": "us_houston",
                "az": "us_phoenix",
                "arizona": "us_phoenix",
                "nm": "us_phoenix",
                "wa": "us_seattle",
                "washington": "us_seattle",
                "or": "us_seattle",
                "fl": "us_miami",
                "florida": "us_miami",
                "ga": "us_miami",
                "sc": "us_miami",
                "nc": "us_miami",
                "pa": "us_new_york",
                "ma": "us_new_york",
                "oh": "us_chicago",
                "mi": "us_chicago",
                "mn": "us_chicago",
                "co": "us_phoenix",
                "va": "us_new_york",
                "md": "us_new_york",
                "dc": "us_new_york",
            }
            if state in state_cities:
                return _maybe_jitter(self.database[state_cities[state]])
        
        # Try country match
        country_defaults = {
            "US": "us_new_york",
            "GB": "uk_london",
            "UK": "uk_london",
            "CA": "ca_toronto",
            "AU": "au_sydney",
            "DE": "de_berlin",
            "FR": "fr_paris",
            "NL": "nl_amsterdam",
        }
        if country in country_defaults:
            return _maybe_jitter(self.database[country_defaults[country]])
        
        # Default to New York
        profile = self.database["us_new_york"]
        return self._apply_coordinate_jitter(profile, profile_seed) if profile_seed else profile
    
    def _apply_coordinate_jitter(self, profile: LocationProfile,
                                  seed: int) -> LocationProfile:
        """
        V7.6 V12-FIX: Apply per-profile coordinate jitter to prevent
        all profiles in the same city from reporting identical GPS coords.
        
        Adds a seeded random offset within ~2km radius — realistic for
        residential addresses within a metro area.
        """
        import random as _rng
        rng = _rng.Random(seed)
        # ~0.018 degrees ≈ 2km at equator
        lat_jitter = rng.gauss(0, 0.008)
        lng_jitter = rng.gauss(0, 0.008)
        accuracy_jitter = rng.uniform(50, 200)
        
        jittered_coords = GeoCoordinates(
            latitude=round(profile.coordinates.latitude + lat_jitter, 6),
            longitude=round(profile.coordinates.longitude + lng_jitter, 6),
            accuracy=accuracy_jitter,
        )
        
        return LocationProfile(
            coordinates=jittered_coords,
            timezone=profile.timezone,
            locale=profile.locale,
            language=profile.language,
            country_code=profile.country_code,
            region=profile.region,
            city=profile.city,
            postal_code=profile.postal_code,
        )
    
    def apply_to_firefox_profile(self, profile_path: str, location: LocationProfile) -> bool:
        """
        Apply location settings to Firefox profile via user.js.
        
        Args:
            profile_path: Path to Firefox profile directory
            location: LocationProfile to apply
            
        Returns:
            True if successful
        """
        profile_dir = Path(profile_path)
        if not profile_dir.exists():
            logger.error(f"Profile directory not found: {profile_path}")
            return False
        
        user_js = profile_dir / "user.js"
        
        # Firefox geolocation preferences
        prefs = [
            f'user_pref("geo.provider.network.url", "data:application/json,{{\\"location\\": {{\\"lat\\": {location.coordinates.latitude}, \\"lng\\": {location.coordinates.longitude}}}, \\"accuracy\\": {location.coordinates.accuracy}}}");',
            # V7.5 FIX: Use Linux-specific prefs, not Windows/macOS
            'user_pref("geo.provider.use_geoclue", false);',
            'user_pref("geo.provider.use_gpsd", false);',
            'user_pref("geo.provider.testing", true);',
            f'user_pref("intl.accept_languages", "{location.language}");',
            f'user_pref("javascript.use_us_english_locale", {"true" if location.country_code == "US" else "false"});',
        ]
        
        try:
            # V7.5 FIX: Check for existing location prefs to avoid duplicates
            existing = ""
            if user_js.exists():
                existing = user_js.read_text()
            if "TITAN Location Spoofing" in existing:
                logger.debug("Location prefs already present in user.js, skipping")
                return True
            
            with open(user_js, "a") as f:
                f.write("\n// TITAN Location Spoofing\n")
                for pref in prefs:
                    f.write(pref + "\n")
            
            logger.info(f"Applied location to Firefox profile: {location.city}, {location.country_code}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply location: {e}")
            return False
    
    def get_environment_vars(self, location: LocationProfile) -> Dict[str, str]:
        """
        Get environment variables for location spoofing.
        
        These should be set before launching the browser.
        """
        return {
            "TZ": location.timezone,
            "LANG": location.locale,
            "LC_ALL": location.locale,
            "LANGUAGE": location.language.split(",")[0],
            "TITAN_GEO_LAT": str(location.coordinates.latitude),
            "TITAN_GEO_LNG": str(location.coordinates.longitude),
            "TITAN_GEO_COUNTRY": location.country_code,
            "TITAN_GEO_CITY": location.city,
        }
    
    def set_system_timezone(self, timezone: str) -> bool:
        """
        Set system timezone (requires root).
        
        Args:
            timezone: Timezone string (e.g., "America/New_York")
            
        Returns:
            True if successful
        """
        try:
            # Check if timezone is valid
            tz_file = Path(f"/usr/share/zoneinfo/{timezone}")
            if not tz_file.exists():
                logger.error(f"Invalid timezone: {timezone}")
                return False
            
            # Try timedatectl (systemd)
            result = subprocess.run(
                ["timedatectl", "set-timezone", timezone],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                logger.info(f"System timezone set to: {timezone}")
                return True
            
            # Fallback: symlink /etc/localtime
            subprocess.run(
                ["ln", "-sf", str(tz_file), "/etc/localtime"],
                check=True
            )
            
            # Update /etc/timezone
            with open("/etc/timezone", "w") as f:
                f.write(timezone + "\n")
            
            logger.info(f"System timezone set to: {timezone}")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to set timezone: {e}")
            return False
        except PermissionError:
            logger.warning("Cannot set system timezone without root")
            return False
    
    def get_camoufox_config(self, location: LocationProfile) -> Dict[str, Any]:
        """
        Get Camoufox-compatible configuration for location.
        
        Returns config dict to pass to Camoufox.
        """
        return {
            "geolocation:latitude": location.coordinates.latitude,
            "geolocation:longitude": location.coordinates.longitude,
            "geolocation:accuracy": location.coordinates.accuracy,
            "timezone": location.timezone,
            "locale": location.locale.split(".")[0].replace("_", "-"),
        }
    
    def write_location_config(self, profile_path: str, location: LocationProfile) -> bool:
        """
        Write location config to profile directory for titan-browser to load.
        """
        config_file = Path(profile_path) / "location_config.json"
        
        try:
            config = {
                "latitude": location.coordinates.latitude,
                "longitude": location.coordinates.longitude,
                "accuracy": location.coordinates.accuracy,
                "timezone": location.timezone,
                "locale": location.locale,
                "language": location.language,
                "country": location.country_code,
                "city": location.city,
                "region": location.region,
                "postal_code": location.postal_code,
            }
            
            with open(config_file, "w") as f:
                json.dump(config, f, indent=2)
            
            logger.info(f"Location config written to: {config_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to write location config: {e}")
            return False


# Convenience function
def get_location_spoofer() -> LinuxLocationSpoofer:
    """Get singleton location spoofer instance"""
    return LinuxLocationSpoofer()


# =============================================================================
# TITAN V7.6 P0 CRITICAL ENHANCEMENTS
# =============================================================================

import time
import random
import math
import hashlib
import threading
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Tuple, Callable


class LocationSignalType(Enum):
    """Types of location signals that must be synchronized"""
    GPS_COORDINATES = "gps"
    TIMEZONE = "timezone"
    LOCALE = "locale"
    IP_GEOLOCATION = "ip_geo"
    WIFI_FINGERPRINT = "wifi"
    CELL_TOWER = "cell"
    BROWSER_API = "browser"
    SYSTEM_CLOCK = "clock"


class ConsistencyLevel(Enum):
    """Location consistency validation levels"""
    STRICT = "strict"           # All signals must match exactly
    MODERATE = "moderate"       # Allow minor discrepancies
    PERMISSIVE = "permissive"   # Allow regional differences


@dataclass
class LocationSignal:
    """Individual location signal for consistency checking"""
    signal_type: LocationSignalType
    latitude: Optional[float]
    longitude: Optional[float]
    timezone: Optional[str]
    country_code: Optional[str]
    confidence: float = 1.0
    timestamp: float = 0.0
    source: str = "unknown"


@dataclass
class ConsistencyReport:
    """Report of location consistency validation"""
    is_consistent: bool
    confidence_score: float
    signals_checked: int
    discrepancies: List[Dict[str, Any]]
    recommendations: List[str]
    timestamp: float


@dataclass
class GeoJitterConfig:
    """Configuration for geographic jitter simulation"""
    max_drift_meters: float = 50.0
    drift_interval_seconds: float = 30.0
    movement_pattern: str = "brownian"  # brownian, circular, stationary
    speed_variation: float = 0.3
    enable_altitude_drift: bool = True
    altitude_drift_meters: float = 5.0


@dataclass 
class LocationSwitchRequest:
    """Request to switch location with travel simulation"""
    from_profile: LocationProfile
    to_profile: LocationProfile
    travel_mode: str = "flight"  # flight, drive, instant
    requested_at: float = 0.0
    estimated_arrival: float = 0.0
    status: str = "pending"


class LocationConsistencyValidator:
    """
    V7.6 P0 CRITICAL: Validate that all location signals are consistent.
    
    Ensures IP geolocation, timezone, locale, browser API, and GPS
    coordinates all indicate the same geographic region to avoid
    detection from signal mismatches.
    
    Usage:
        validator = get_location_consistency_validator()
        
        # Add signals from various sources
        validator.add_signal(gps_signal)
        validator.add_signal(ip_signal)
        validator.add_signal(timezone_signal)
        
        # Validate consistency
        report = validator.validate_consistency()
        if not report.is_consistent:
            for fix in report.recommendations:
                print(f"Fix needed: {fix}")
    """
    
    def __init__(self, level: ConsistencyLevel = ConsistencyLevel.MODERATE):
        self.level = level
        self.signals: List[LocationSignal] = []
        self.tolerance_km = self._get_tolerance_km()
        self.timezone_mappings = self._load_timezone_mappings()
        self._lock = threading.Lock()
        logger.info(f"LocationConsistencyValidator initialized with {level.value} level")
    
    def _get_tolerance_km(self) -> float:
        """Get distance tolerance based on consistency level"""
        tolerances = {
            ConsistencyLevel.STRICT: 50.0,
            ConsistencyLevel.MODERATE: 200.0,
            ConsistencyLevel.PERMISSIVE: 500.0,
        }
        return tolerances.get(self.level, 200.0)
    
    def _load_timezone_mappings(self) -> Dict[str, Tuple[float, float]]:
        """Load timezone to approximate coordinates mapping"""
        return {
            "America/New_York": (40.7128, -74.0060),
            "America/Los_Angeles": (34.0522, -118.2437),
            "America/Chicago": (41.8781, -87.6298),
            "America/Phoenix": (33.4484, -112.0740),
            "America/Denver": (39.7392, -104.9903),
            "America/Toronto": (43.6532, -79.3832),
            "America/Vancouver": (49.2827, -123.1207),
            "Europe/London": (51.5074, -0.1278),
            "Europe/Paris": (48.8566, 2.3522),
            "Europe/Berlin": (52.5200, 13.4050),
            "Europe/Amsterdam": (52.3676, 4.9041),
            "Australia/Sydney": (-33.8688, 151.2093),
            "Australia/Melbourne": (-37.8136, 144.9631),
            "Asia/Tokyo": (35.6762, 139.6503),
            "Asia/Singapore": (1.3521, 103.8198),
        }
    
    def add_signal(self, signal: LocationSignal) -> None:
        """Add a location signal for consistency checking"""
        with self._lock:
            signal.timestamp = time.time()
            self.signals.append(signal)
            # Keep only recent signals (last 5 minutes)
            cutoff = time.time() - 300
            self.signals = [s for s in self.signals if s.timestamp > cutoff]
    
    def clear_signals(self) -> None:
        """Clear all recorded signals"""
        with self._lock:
            self.signals.clear()
    
    def _haversine_distance(self, lat1: float, lon1: float, 
                            lat2: float, lon2: float) -> float:
        """Calculate distance between two points in kilometers"""
        R = 6371  # Earth's radius in km
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat / 2) ** 2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * 
             math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    def _check_coordinate_consistency(self) -> List[Dict[str, Any]]:
        """Check if all coordinate signals are consistent"""
        discrepancies = []
        coord_signals = [s for s in self.signals 
                        if s.latitude is not None and s.longitude is not None]
        
        if len(coord_signals) < 2:
            return discrepancies
        
        # Compare all pairs
        for i, s1 in enumerate(coord_signals):
            for s2 in coord_signals[i+1:]:
                distance = self._haversine_distance(
                    s1.latitude, s1.longitude,
                    s2.latitude, s2.longitude
                )
                if distance > self.tolerance_km:
                    discrepancies.append({
                        "type": "coordinate_mismatch",
                        "signal1": s1.signal_type.value,
                        "signal2": s2.signal_type.value,
                        "distance_km": round(distance, 2),
                        "tolerance_km": self.tolerance_km,
                        "severity": "high" if distance > self.tolerance_km * 2 else "medium"
                    })
        
        return discrepancies
    
    def _check_timezone_consistency(self) -> List[Dict[str, Any]]:
        """Check if timezone matches coordinate locations"""
        discrepancies = []
        
        tz_signals = [s for s in self.signals if s.timezone]
        coord_signals = [s for s in self.signals 
                        if s.latitude is not None and s.longitude is not None]
        
        if not tz_signals or not coord_signals:
            return discrepancies
        
        for tz_signal in tz_signals:
            if tz_signal.timezone not in self.timezone_mappings:
                continue
            
            tz_lat, tz_lon = self.timezone_mappings[tz_signal.timezone]
            
            for coord_signal in coord_signals:
                distance = self._haversine_distance(
                    coord_signal.latitude, coord_signal.longitude,
                    tz_lat, tz_lon
                )
                
                # Timezone regions can be large, use 2x tolerance
                if distance > self.tolerance_km * 2:
                    discrepancies.append({
                        "type": "timezone_coordinate_mismatch",
                        "timezone": tz_signal.timezone,
                        "coord_source": coord_signal.signal_type.value,
                        "distance_km": round(distance, 2),
                        "severity": "high"
                    })
        
        return discrepancies
    
    def _check_country_consistency(self) -> List[Dict[str, Any]]:
        """Check if all country codes match"""
        discrepancies = []
        
        country_signals = [s for s in self.signals if s.country_code]
        
        if len(country_signals) < 2:
            return discrepancies
        
        countries = set(s.country_code for s in country_signals)
        
        if len(countries) > 1:
            discrepancies.append({
                "type": "country_mismatch",
                "countries": list(countries),
                "sources": [s.signal_type.value for s in country_signals],
                "severity": "critical"
            })
        
        return discrepancies
    
    def _generate_recommendations(self, discrepancies: List[Dict]) -> List[str]:
        """Generate recommendations to fix discrepancies"""
        recommendations = []
        
        for d in discrepancies:
            if d["type"] == "coordinate_mismatch":
                recommendations.append(
                    f"Synchronize {d['signal1']} and {d['signal2']} coordinates "
                    f"(currently {d['distance_km']}km apart)"
                )
            elif d["type"] == "timezone_coordinate_mismatch":
                recommendations.append(
                    f"Timezone {d['timezone']} doesn't match coordinates from "
                    f"{d['coord_source']} - update timezone or coordinates"
                )
            elif d["type"] == "country_mismatch":
                recommendations.append(
                    f"Multiple countries detected: {d['countries']} - "
                    "ensure all location signals use same country"
                )
        
        return recommendations
    
    def validate_consistency(self) -> ConsistencyReport:
        """
        Validate consistency across all location signals.
        
        Returns:
            ConsistencyReport with validation results
        """
        with self._lock:
            discrepancies = []
            
            # Run all consistency checks
            discrepancies.extend(self._check_coordinate_consistency())
            discrepancies.extend(self._check_timezone_consistency())
            discrepancies.extend(self._check_country_consistency())
            
            # Calculate confidence score
            critical_count = sum(1 for d in discrepancies if d.get("severity") == "critical")
            high_count = sum(1 for d in discrepancies if d.get("severity") == "high")
            medium_count = sum(1 for d in discrepancies if d.get("severity") == "medium")
            
            confidence = 1.0 - (critical_count * 0.4 + high_count * 0.2 + medium_count * 0.1)
            confidence = max(0.0, confidence)
            
            is_consistent = len(discrepancies) == 0
            if self.level == ConsistencyLevel.PERMISSIVE:
                is_consistent = critical_count == 0
            elif self.level == ConsistencyLevel.MODERATE:
                is_consistent = critical_count == 0 and high_count == 0
            
            recommendations = self._generate_recommendations(discrepancies)
            
            return ConsistencyReport(
                is_consistent=is_consistent,
                confidence_score=confidence,
                signals_checked=len(self.signals),
                discrepancies=discrepancies,
                recommendations=recommendations,
                timestamp=time.time()
            )
    
    def validate_profile(self, profile: LocationProfile) -> ConsistencyReport:
        """
        Validate a LocationProfile for internal consistency.
        """
        self.clear_signals()
        
        # Add GPS signal
        self.add_signal(LocationSignal(
            signal_type=LocationSignalType.GPS_COORDINATES,
            latitude=profile.coordinates.latitude,
            longitude=profile.coordinates.longitude,
            timezone=profile.timezone,
            country_code=profile.country_code,
            source="profile_gps"
        ))
        
        # Add timezone signal
        self.add_signal(LocationSignal(
            signal_type=LocationSignalType.TIMEZONE,
            latitude=None,
            longitude=None,
            timezone=profile.timezone,
            country_code=profile.country_code,
            source="profile_timezone"
        ))
        
        return self.validate_consistency()


# Singleton instance
_consistency_validator: Optional[LocationConsistencyValidator] = None

def get_location_consistency_validator() -> LocationConsistencyValidator:
    """Get singleton LocationConsistencyValidator instance"""
    global _consistency_validator
    if _consistency_validator is None:
        _consistency_validator = LocationConsistencyValidator()
    return _consistency_validator


class GeoJitterEngine:
    """
    V7.6 P0 CRITICAL: Add realistic micro-movements to GPS coordinates.
    
    Static GPS coordinates are a detection vector - real devices show
    natural micro-drift from GPS accuracy variations, user movement,
    and environmental factors. This engine simulates realistic jitter.
    
    Usage:
        jitter = get_geo_jitter_engine()
        
        # Configure jitter pattern
        jitter.configure(GeoJitterConfig(
            max_drift_meters=50,
            movement_pattern="brownian"
        ))
        
        # Get jittered coordinates
        lat, lon = jitter.get_jittered_position(base_lat, base_lon)
        
        # Start continuous jitter thread
        jitter.start_continuous_jitter(callback)
    """
    
    def __init__(self, config: Optional[GeoJitterConfig] = None):
        self.config = config or GeoJitterConfig()
        self.base_latitude: Optional[float] = None
        self.base_longitude: Optional[float] = None
        self.base_altitude: Optional[float] = None
        self.current_offset_lat = 0.0
        self.current_offset_lon = 0.0
        self.current_offset_alt = 0.0
        self._jitter_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._callbacks: List[Callable] = []
        self._lock = threading.Lock()
        self._last_jitter_time = 0.0
        logger.info("GeoJitterEngine initialized")
    
    def configure(self, config: GeoJitterConfig) -> None:
        """Update jitter configuration"""
        self.config = config
        logger.debug(f"GeoJitterEngine configured: pattern={config.movement_pattern}")
    
    def set_base_position(self, latitude: float, longitude: float,
                          altitude: Optional[float] = None) -> None:
        """Set the base position for jitter calculations"""
        with self._lock:
            self.base_latitude = latitude
            self.base_longitude = longitude
            self.base_altitude = altitude
            self.current_offset_lat = 0.0
            self.current_offset_lon = 0.0
            self.current_offset_alt = 0.0
    
    def _meters_to_degrees(self, meters: float, latitude: float) -> Tuple[float, float]:
        """Convert meters to lat/lon degrees at given latitude"""
        # 1 degree latitude ≈ 111km everywhere
        lat_degrees = meters / 111000
        
        # Longitude degrees vary by latitude
        lon_degrees = meters / (111000 * math.cos(math.radians(latitude)))
        
        return lat_degrees, lon_degrees
    
    def _brownian_step(self) -> Tuple[float, float]:
        """Generate Brownian motion step"""
        # Random direction and distance
        angle = random.uniform(0, 2 * math.pi)
        distance = random.gauss(0, self.config.max_drift_meters / 3)
        
        dx = distance * math.cos(angle)
        dy = distance * math.sin(angle)
        
        return dx, dy
    
    def _circular_step(self) -> Tuple[float, float]:
        """Generate circular motion pattern (pacing)"""
        # Time-based circular motion
        t = time.time() / self.config.drift_interval_seconds
        radius = self.config.max_drift_meters * 0.5
        
        dx = radius * math.cos(t * 2 * math.pi)
        dy = radius * math.sin(t * 2 * math.pi)
        
        return dx, dy
    
    def _stationary_jitter(self) -> Tuple[float, float]:
        """Generate small stationary jitter (GPS noise)"""
        # Small random noise simulating GPS accuracy variations
        dx = random.gauss(0, 5)  # ~5 meter standard deviation
        dy = random.gauss(0, 5)
        return dx, dy
    
    def _apply_movement_pattern(self) -> None:
        """Apply configured movement pattern to update offsets"""
        if self.config.movement_pattern == "brownian":
            dx, dy = self._brownian_step()
            self.current_offset_lat += dy
            self.current_offset_lon += dx
        elif self.config.movement_pattern == "circular":
            dx, dy = self._circular_step()
            self.current_offset_lat = dy
            self.current_offset_lon = dx
        else:  # stationary
            dx, dy = self._stationary_jitter()
            self.current_offset_lat = dy
            self.current_offset_lon = dx
        
        # Add speed variation
        if self.config.speed_variation > 0:
            variation = 1.0 + random.uniform(
                -self.config.speed_variation,
                self.config.speed_variation
            )
            self.current_offset_lat *= variation
            self.current_offset_lon *= variation
        
        # Clamp to max drift
        max_offset = self.config.max_drift_meters
        total_offset = math.sqrt(
            self.current_offset_lat ** 2 + 
            self.current_offset_lon ** 2
        )
        
        if total_offset > max_offset:
            scale = max_offset / total_offset
            self.current_offset_lat *= scale
            self.current_offset_lon *= scale
        
        # Altitude drift
        if self.config.enable_altitude_drift:
            self.current_offset_alt += random.gauss(0, 1)
            max_alt = self.config.altitude_drift_meters
            self.current_offset_alt = max(-max_alt, min(max_alt, self.current_offset_alt))
    
    def get_jittered_position(self, base_lat: Optional[float] = None,
                               base_lon: Optional[float] = None) -> Tuple[float, float, float]:
        """
        Get current position with jitter applied.
        
        Args:
            base_lat: Base latitude (uses stored if None)
            base_lon: Base longitude (uses stored if None)
            
        Returns:
            Tuple of (latitude, longitude, accuracy_meters)
        """
        with self._lock:
            lat = base_lat if base_lat is not None else self.base_latitude
            lon = base_lon if base_lon is not None else self.base_longitude
            
            if lat is None or lon is None:
                raise ValueError("Base position not set")
            
            # Check if we should update jitter
            now = time.time()
            if now - self._last_jitter_time > self.config.drift_interval_seconds:
                self._apply_movement_pattern()
                self._last_jitter_time = now
            
            # Convert meter offsets to degrees
            lat_offset, lon_offset = self._meters_to_degrees(
                self.current_offset_lat, lat
            )
            _, lon_offset = self._meters_to_degrees(
                self.current_offset_lon, lat
            )
            
            jittered_lat = lat + lat_offset
            jittered_lon = lon + lon_offset
            
            # Accuracy reflects the jitter amount
            accuracy = max(10.0, math.sqrt(
                self.current_offset_lat ** 2 + 
                self.current_offset_lon ** 2
            ))
            
            return jittered_lat, jittered_lon, accuracy
    
    def get_jittered_altitude(self, base_alt: Optional[float] = None) -> float:
        """Get altitude with jitter"""
        with self._lock:
            alt = base_alt if base_alt is not None else self.base_altitude or 0.0
            return alt + self.current_offset_alt
    
    def register_callback(self, callback: Callable[[float, float, float], None]) -> None:
        """Register callback for continuous jitter updates"""
        with self._lock:
            self._callbacks.append(callback)
    
    def start_continuous_jitter(self) -> None:
        """Start background thread for continuous jitter updates"""
        if self._jitter_thread is not None and self._jitter_thread.is_alive():
            return
        
        self._stop_event.clear()
        self._jitter_thread = threading.Thread(
            target=self._jitter_loop,
            daemon=True,
            name="GeoJitterEngine"
        )
        self._jitter_thread.start()
        logger.info("Continuous geo jitter started")
    
    def stop_continuous_jitter(self) -> None:
        """Stop continuous jitter thread"""
        self._stop_event.set()
        if self._jitter_thread is not None:
            self._jitter_thread.join(timeout=5.0)
        logger.info("Continuous geo jitter stopped")
    
    def _jitter_loop(self) -> None:
        """Background loop for continuous jitter"""
        while not self._stop_event.is_set():
            try:
                lat, lon, accuracy = self.get_jittered_position()
                
                with self._lock:
                    for callback in self._callbacks:
                        try:
                            callback(lat, lon, accuracy)
                        except Exception as e:
                            logger.error(f"Jitter callback error: {e}")
                
            except Exception as e:
                logger.error(f"Jitter loop error: {e}")
            
            self._stop_event.wait(self.config.drift_interval_seconds)


# Singleton instance
_geo_jitter_engine: Optional[GeoJitterEngine] = None

def get_geo_jitter_engine() -> GeoJitterEngine:
    """Get singleton GeoJitterEngine instance"""
    global _geo_jitter_engine
    if _geo_jitter_engine is None:
        _geo_jitter_engine = GeoJitterEngine()
    return _geo_jitter_engine


class LocationSwitchManager:
    """
    V7.6 P0 CRITICAL: Handle location switching with realistic travel delays.
    
    Instant location changes are a detection vector. This manager
    enforces realistic travel times based on distance and travel mode,
    with queuing and gradual location transitions.
    
    Usage:
        manager = get_location_switch_manager()
        
        # Request location switch
        request = manager.request_switch(
            from_profile=current_location,
            to_profile=new_location,
            travel_mode="flight"
        )
        
        # Check if ready
        if manager.is_switch_ready(request):
            manager.execute_switch(request)
    """
    
    # Average speeds in km/h for travel modes
    TRAVEL_SPEEDS = {
        "walk": 5,
        "drive": 80,
        "flight": 800,
        "instant": float('inf'),
    }
    
    # Minimum delays in hours
    MIN_DELAYS = {
        "walk": 0.0,
        "drive": 0.5,
        "flight": 2.0,  # Check-in, security, etc.
        "instant": 0.0,
    }
    
    def __init__(self):
        self.pending_requests: List[LocationSwitchRequest] = []
        self.completed_requests: List[LocationSwitchRequest] = []
        self.current_location: Optional[LocationProfile] = None
        self._lock = threading.Lock()
        self._switch_listeners: List[Callable] = []
        logger.info("LocationSwitchManager initialized")
    
    def set_current_location(self, profile: LocationProfile) -> None:
        """Set current location"""
        with self._lock:
            self.current_location = profile
    
    def _calculate_distance(self, from_profile: LocationProfile,
                           to_profile: LocationProfile) -> float:
        """Calculate distance between profiles in kilometers"""
        R = 6371  # Earth radius
        
        lat1 = math.radians(from_profile.coordinates.latitude)
        lat2 = math.radians(to_profile.coordinates.latitude)
        delta_lat = lat2 - lat1
        delta_lon = math.radians(
            to_profile.coordinates.longitude - 
            from_profile.coordinates.longitude
        )
        
        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1) * math.cos(lat2) *
             math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    def _estimate_travel_time(self, distance_km: float, 
                              travel_mode: str) -> float:
        """Estimate travel time in seconds"""
        speed = self.TRAVEL_SPEEDS.get(travel_mode, 80)
        min_delay = self.MIN_DELAYS.get(travel_mode, 0)
        
        if speed == float('inf'):
            return 0
        
        travel_hours = distance_km / speed
        total_hours = travel_hours + min_delay
        
        # Add some randomness (10%)
        total_hours *= random.uniform(0.9, 1.1)
        
        return total_hours * 3600  # Convert to seconds
    
    def request_switch(self, from_profile: LocationProfile,
                       to_profile: LocationProfile,
                       travel_mode: str = "flight") -> LocationSwitchRequest:
        """
        Request a location switch with travel time simulation.
        
        Returns:
            LocationSwitchRequest that can be queried for readiness
        """
        distance = self._calculate_distance(from_profile, to_profile)
        travel_time = self._estimate_travel_time(distance, travel_mode)
        
        request = LocationSwitchRequest(
            from_profile=from_profile,
            to_profile=to_profile,
            travel_mode=travel_mode,
            requested_at=time.time(),
            estimated_arrival=time.time() + travel_time,
            status="pending"
        )
        
        with self._lock:
            self.pending_requests.append(request)
        
        logger.info(
            f"Location switch requested: {from_profile.city} -> {to_profile.city}, "
            f"mode={travel_mode}, distance={distance:.0f}km, "
            f"ETA={timedelta(seconds=int(travel_time))}"
        )
        
        return request
    
    def is_switch_ready(self, request: LocationSwitchRequest) -> bool:
        """Check if a switch request is ready to execute"""
        return time.time() >= request.estimated_arrival
    
    def get_remaining_time(self, request: LocationSwitchRequest) -> float:
        """Get remaining time in seconds until switch is ready"""
        return max(0, request.estimated_arrival - time.time())
    
    def execute_switch(self, request: LocationSwitchRequest) -> bool:
        """
        Execute a pending location switch.
        
        Returns:
            True if switch was executed
        """
        if not self.is_switch_ready(request):
            logger.warning("Cannot execute switch - travel time not elapsed")
            return False
        
        with self._lock:
            if request in self.pending_requests:
                self.pending_requests.remove(request)
            
            request.status = "completed"
            self.completed_requests.append(request)
            self.current_location = request.to_profile
            
            # Notify listeners
            for listener in self._switch_listeners:
                try:
                    listener(request)
                except Exception as e:
                    logger.error(f"Switch listener error: {e}")
        
        logger.info(f"Location switched to: {request.to_profile.city}")
        return True
    
    def force_instant_switch(self, to_profile: LocationProfile,
                             reason: str = "operator_override") -> bool:
        """
        Force immediate location switch (bypasses travel time).
        
        Use only when operationally required. Logs the bypass for audit.
        """
        logger.warning(
            f"Instant location switch forced: {to_profile.city}, "
            f"reason={reason}"
        )
        
        with self._lock:
            self.current_location = to_profile
        
        return True
    
    def get_pending_requests(self) -> List[LocationSwitchRequest]:
        """Get all pending switch requests"""
        with self._lock:
            return list(self.pending_requests)
    
    def cancel_request(self, request: LocationSwitchRequest) -> bool:
        """Cancel a pending switch request"""
        with self._lock:
            if request in self.pending_requests:
                self.pending_requests.remove(request)
                request.status = "cancelled"
                logger.info(f"Switch request cancelled: -> {request.to_profile.city}")
                return True
        return False
    
    def add_switch_listener(self, callback: Callable[[LocationSwitchRequest], None]) -> None:
        """Add listener for switch completion events"""
        with self._lock:
            self._switch_listeners.append(callback)


# Singleton instance
_location_switch_manager: Optional[LocationSwitchManager] = None

def get_location_switch_manager() -> LocationSwitchManager:
    """Get singleton LocationSwitchManager instance"""
    global _location_switch_manager
    if _location_switch_manager is None:
        _location_switch_manager = LocationSwitchManager()
    return _location_switch_manager


class MultiSourceLocationSync:
    """
    V7.6 P0 CRITICAL: Synchronize location across all sources.
    
    Ensures browser geolocation API, system timezone, locale settings,
    environment variables, and network-level geolocation all report
    consistent location data simultaneously.
    
    Usage:
        sync = get_multi_source_location_sync()
        
        # Configure all sources for a location
        sync.configure_profile(profile)
        
        # Apply to all sources atomically
        results = sync.apply_all()
        
        # Verify synchronization
        status = sync.verify_sync_status()
    """
    
    def __init__(self):
        self.spoofer = LinuxLocationSpoofer()
        self.jitter_engine = get_geo_jitter_engine()
        self.validator = get_location_consistency_validator()
        self.current_profile: Optional[LocationProfile] = None
        self._firefox_profiles: List[str] = []
        self._env_vars: Dict[str, str] = {}
        self._lock = threading.Lock()
        logger.info("MultiSourceLocationSync initialized")
    
    def add_firefox_profile(self, profile_path: str) -> None:
        """Register a Firefox profile for location sync"""
        with self._lock:
            if profile_path not in self._firefox_profiles:
                self._firefox_profiles.append(profile_path)
    
    def configure_profile(self, profile: LocationProfile) -> None:
        """
        Configure target location profile for synchronization.
        """
        with self._lock:
            self.current_profile = profile
            self._env_vars = self.spoofer.get_environment_vars(profile)
            
            # Configure jitter engine
            self.jitter_engine.set_base_position(
                profile.coordinates.latitude,
                profile.coordinates.longitude,
                profile.coordinates.altitude
            )
    
    def apply_firefox_profile(self, profile_path: str) -> bool:
        """Apply location to a specific Firefox profile"""
        if self.current_profile is None:
            logger.error("No profile configured")
            return False
        
        return self.spoofer.apply_to_firefox_profile(
            profile_path, self.current_profile
        )
    
    def apply_all_firefox_profiles(self) -> Dict[str, bool]:
        """Apply location to all registered Firefox profiles"""
        results = {}
        with self._lock:
            for profile_path in self._firefox_profiles:
                results[profile_path] = self.apply_firefox_profile(profile_path)
        return results
    
    def apply_system_timezone(self) -> bool:
        """Apply timezone to system (requires root)"""
        if self.current_profile is None:
            return False
        return self.spoofer.set_system_timezone(self.current_profile.timezone)
    
    def apply_environment_vars(self) -> Dict[str, str]:
        """
        Get environment variables to apply.
        
        Returns dict that should be passed to subprocess.Popen(env=...)
        """
        with self._lock:
            env = os.environ.copy()
            env.update(self._env_vars)
            return env
    
    def apply_all(self) -> Dict[str, Any]:
        """
        Apply location to all sources atomically.
        
        Returns:
            Dict with results for each source
        """
        if self.current_profile is None:
            return {"error": "No profile configured"}
        
        results = {
            "profile": f"{self.current_profile.city}, {self.current_profile.country_code}",
            "firefox_profiles": {},
            "system_timezone": False,
            "environment_vars": False,
            "jitter_configured": False,
            "consistency_validated": False,
        }
        
        # Apply to Firefox profiles
        results["firefox_profiles"] = self.apply_all_firefox_profiles()
        
        # Try system timezone (may fail without root)
        try:
            results["system_timezone"] = self.apply_system_timezone()
        except Exception as e:
            logger.warning(f"System timezone not set: {e}")
        
        # Environment vars are always available
        results["environment_vars"] = len(self._env_vars) > 0
        
        # Verify jitter is configured
        results["jitter_configured"] = self.jitter_engine.base_latitude is not None
        
        # Validate consistency
        report = self.validator.validate_profile(self.current_profile)
        results["consistency_validated"] = report.is_consistent
        results["consistency_score"] = report.confidence_score
        
        logger.info(f"Location sync applied: {results}")
        return results
    
    def verify_sync_status(self) -> Dict[str, Any]:
        """
        Verify current synchronization status across all sources.
        """
        status = {
            "is_synced": False,
            "profile": None,
            "sources": {},
            "issues": []
        }
        
        if self.current_profile is None:
            status["issues"].append("No profile configured")
            return status
        
        status["profile"] = f"{self.current_profile.city}, {self.current_profile.country_code}"
        
        # Check environment TZ
        system_tz = os.environ.get("TZ", "")
        expected_tz = self.current_profile.timezone
        status["sources"]["environment_tz"] = system_tz == expected_tz
        if not status["sources"]["environment_tz"]:
            status["issues"].append(f"TZ mismatch: {system_tz} vs {expected_tz}")
        
        # Check jitter engine
        status["sources"]["jitter_engine"] = (
            self.jitter_engine.base_latitude == self.current_profile.coordinates.latitude
        )
        
        # Check Firefox profiles
        for profile_path in self._firefox_profiles:
            config_file = Path(profile_path) / "location_config.json"
            if config_file.exists():
                try:
                    with open(config_file) as f:
                        config = json.load(f)
                    matches = config.get("city") == self.current_profile.city
                    status["sources"][f"firefox:{profile_path}"] = matches
                except Exception:
                    status["sources"][f"firefox:{profile_path}"] = False
        
        # Overall sync status
        status["is_synced"] = (
            len(status["issues"]) == 0 and
            all(status["sources"].values())
        )
        
        return status
    
    def get_current_position_with_jitter(self) -> Optional[Dict[str, float]]:
        """Get current position with jitter applied"""
        if self.current_profile is None:
            return None
        
        lat, lon, accuracy = self.jitter_engine.get_jittered_position()
        
        return {
            "latitude": lat,
            "longitude": lon,
            "accuracy": accuracy,
            "altitude": self.jitter_engine.get_jittered_altitude(
                self.current_profile.coordinates.altitude
            ),
            "base_city": self.current_profile.city,
            "base_country": self.current_profile.country_code,
        }
    
    def start_continuous_sync(self, interval_seconds: float = 30.0) -> None:
        """Start continuous location synchronization with jitter"""
        self.jitter_engine.config.drift_interval_seconds = interval_seconds
        self.jitter_engine.start_continuous_jitter()
    
    def stop_continuous_sync(self) -> None:
        """Stop continuous synchronization"""
        self.jitter_engine.stop_continuous_jitter()


# Singleton instance
_multi_source_sync: Optional[MultiSourceLocationSync] = None

def get_multi_source_location_sync() -> MultiSourceLocationSync:
    """Get singleton MultiSourceLocationSync instance"""
    global _multi_source_sync
    if _multi_source_sync is None:
        _multi_source_sync = MultiSourceLocationSync()
    return _multi_source_sync
