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
    
    def get_profile_for_address(self, address: Dict[str, str]) -> Optional[LocationProfile]:
        """
        Get location profile matching billing address.
        
        Args:
            address: Dict with country, city, state, zip
            
        Returns:
            Best matching LocationProfile
        """
        country = address.get("country", "US").upper()
        city = address.get("city", "").lower().replace(" ", "_")
        state = address.get("state", "").lower()
        
        # Try exact city match
        key = f"{country.lower()}_{city}"
        if key in self.database:
            return self.database[key]
        
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
                return self.database[state_cities[state]]
        
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
            return self.database[country_defaults[country]]
        
        # Default to New York
        return self.database["us_new_york"]
    
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
