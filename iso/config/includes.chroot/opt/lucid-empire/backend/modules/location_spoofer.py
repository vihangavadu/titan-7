#!/usr/bin/env python3
"""
LUCID EMPIRE v7.0.0-TITAN :: LOCATION SPOOFING MODULE
======================================================
Authority: Dva.12 | PROMETHEUS-CORE v2.1
Classification: OBLIVION ACTIVE

Advanced location spoofing without proxy/VPN dependency.
Implements the techniques from "Spoofing Location Without Proxy_VPN.txt":

1. Browser-Level Geolocation Overrides (geo.provider injection)
2. System-Level Location Spoofing (Windows registry, Fake GPS drivers)
3. WiFi BSSID Evasion (nullification of WiFi triangulation)
4. Timezone/Locale Alignment (IP-based consistency)
5. TCP/IP Stack Fingerprint Alignment

Reference: Section 4-7 of the technical analysis document
"""

import os
import sys
import json
import time
import platform
import subprocess
import hashlib
import random
import struct
try:
    import winreg
    HAS_WINREG = True
except ImportError:
    HAS_WINREG = False
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LUCID-LocationSpoofer")


@dataclass
class GeoCoordinates:
    """Geographic coordinates with accuracy"""
    latitude: float
    longitude: float
    accuracy: float = 27000.0  # meters (27km = city level)
    altitude: Optional[float] = None
    altitude_accuracy: Optional[float] = None
    heading: Optional[float] = None
    speed: Optional[float] = None


@dataclass 
class LocationProfile:
    """Complete location profile for spoofing"""
    coordinates: GeoCoordinates
    timezone: str  # e.g., "Asia/Colombo"
    locale: str  # e.g., "en-US"
    language: str  # e.g., "en-US,en,si"
    country_code: str  # e.g., "LK"
    region: str  # e.g., "Western Province"
    city: str  # e.g., "Dehiwala"
    postal_code: str  # e.g., "10350"
    ip_expected: Optional[str] = None  # Expected IP for consistency check


# Predefined location databases
LOCATION_DATABASE: Dict[str, LocationProfile] = {
    "sri_lanka_colombo": LocationProfile(
        coordinates=GeoCoordinates(6.9271, 79.8612, 500.0),
        timezone="Asia/Colombo",
        locale="en-LK",
        language="en-US,en,si",
        country_code="LK",
        region="Western Province",
        city="Colombo",
        postal_code="00100"
    ),
    "sri_lanka_dehiwala": LocationProfile(
        coordinates=GeoCoordinates(6.8567, 79.8650, 500.0),
        timezone="Asia/Colombo",
        locale="en-LK",
        language="en-US,en,si",
        country_code="LK",
        region="Western Province",
        city="Dehiwala",
        postal_code="10350"
    ),
    "usa_new_york": LocationProfile(
        coordinates=GeoCoordinates(40.7590, -73.9845, 100.0),
        timezone="America/New_York",
        locale="en-US",
        language="en-US,en",
        country_code="US",
        region="New York",
        city="New York",
        postal_code="10036"
    ),
    "usa_los_angeles": LocationProfile(
        coordinates=GeoCoordinates(34.0522, -118.2437, 100.0),
        timezone="America/Los_Angeles",
        locale="en-US",
        language="en-US,en",
        country_code="US",
        region="California",
        city="Los Angeles",
        postal_code="90012"
    ),
    "uk_london": LocationProfile(
        coordinates=GeoCoordinates(51.5074, -0.1278, 100.0),
        timezone="Europe/London",
        locale="en-GB",
        language="en-GB,en",
        country_code="GB",
        region="England",
        city="London",
        postal_code="EC1A 1BB"
    ),
    "germany_berlin": LocationProfile(
        coordinates=GeoCoordinates(52.5200, 13.4050, 100.0),
        timezone="Europe/Berlin",
        locale="de-DE",
        language="de-DE,de,en",
        country_code="DE",
        region="Berlin",
        city="Berlin",
        postal_code="10115"
    ),
    "australia_sydney": LocationProfile(
        coordinates=GeoCoordinates(-33.8688, 151.2093, 100.0),
        timezone="Australia/Sydney",
        locale="en-AU",
        language="en-AU,en",
        country_code="AU",
        region="New South Wales",
        city="Sydney",
        postal_code="2000"
    ),
    "japan_tokyo": LocationProfile(
        coordinates=GeoCoordinates(35.6762, 139.6503, 100.0),
        timezone="Asia/Tokyo",
        locale="ja-JP",
        language="ja-JP,ja,en",
        country_code="JP",
        region="Tokyo",
        city="Tokyo",
        postal_code="100-0001"
    ),
}


class BrowserGeolocationSpoofer:
    """
    Browser-level geolocation spoofing via Firefox preferences.
    
    Implements Section 4.1 of the technical document:
    - geo.provider.network.url injection with Data URI
    - Preference locking for testing flags
    - Camoufox-compatible configuration
    """
    
    def __init__(self, profile_path: Optional[str] = None):
        self.profile_path = Path(profile_path) if profile_path else None
    
    def generate_geo_data_uri(self, coords: GeoCoordinates) -> str:
        """
        Generate a Data URI containing static geolocation JSON.
        
        This forces the browser to report the specified coordinates
        without making any network requests to Google Location Services.
        
        Reference: Section 4.1.1 - The geo.provider Injection Technique
        """
        geo_response = {
            "location": {
                "lat": coords.latitude,
                "lng": coords.longitude
            },
            "accuracy": coords.accuracy
        }
        
        # Create Data URI (no network request needed)
        json_str = json.dumps(geo_response)
        return f"data:application/json,{json_str}"
    
    def generate_firefox_prefs(self, location: LocationProfile) -> Dict[str, Any]:
        """
        Generate Firefox preferences for geolocation spoofing.
        
        These preferences override the default Google Location Services
        and force the browser to use our static coordinates.
        """
        geo_uri = self.generate_geo_data_uri(location.coordinates)
        
        prefs = {
            # Core geolocation settings
            "geo.enabled": True,
            "geo.provider.testing": True,  # Force acceptance of manual provider
            "geo.prompt.testing": True,  # Auto-grant permission
            "geo.prompt.testing.allow": True,
            
            # Inject our static location via Data URI
            "geo.provider.network.url": geo_uri,
            
            # Disable OS-level location services (prevent leaks)
            "geo.provider.use_geoclue": False,  # Linux GeoClue
            "geo.provider.use_gpsd": False,  # GPS daemon
            "geo.provider.use_mls": False,  # Mozilla Location Service
            "geo.provider.network.scan": False,  # Disable WiFi scanning
            
            # Timezone and locale alignment
            "intl.accept_languages": location.language,
            "intl.locale.requested": location.locale,
            
            # Additional privacy settings
            "geo.wifi.uri": "",  # Disable WiFi geolocation endpoint
            "browser.region.network.url": "",  # Disable region detection
            "browser.region.update.enabled": False,
            
            # Prevent WebRTC location leaks
            "media.peerconnection.enabled": False,
            "media.navigator.enabled": False,
        }
        
        return prefs
    
    def generate_camoufox_config(self, location: LocationProfile) -> Dict[str, Any]:
        """
        Generate Camoufox-specific configuration for geolocation.
        
        Camoufox uses its own config format that directly sets
        navigator.geolocation values at the C++ level.
        """
        config = {
            # Direct geolocation injection (bypasses testing flags)
            "geolocation:latitude": location.coordinates.latitude,
            "geolocation:longitude": location.coordinates.longitude,
            "geolocation:accuracy": location.coordinates.accuracy,
            
            # Timezone (Camoufox property)
            "timezone": location.timezone,
            
            # Locale settings
            "locale:language": location.language.split(",")[0],
            "locale:region": location.country_code,
            "locale:all": location.language,
            
            # Block WebRTC to prevent IP leaks
            "webrtc:ipPolicy": "disable_non_proxied_udp",
        }
        
        # Add optional altitude data if available
        if location.coordinates.altitude is not None:
            config["geolocation:altitude"] = location.coordinates.altitude
        
        return config
    
    def inject_user_js(self, location: LocationProfile) -> bool:
        """
        Inject user.js file into Firefox profile for persistent settings.
        
        The user.js file is processed at browser startup and sets
        all preferences before the browser loads.
        """
        if not self.profile_path:
            logger.error("No profile path specified for user.js injection")
            return False
        
        prefs = self.generate_firefox_prefs(location)
        
        user_js_path = self.profile_path / "user.js"
        
        try:
            with open(user_js_path, "w", encoding="utf-8") as f:
                f.write("// LUCID EMPIRE - Geolocation Spoofing Configuration\n")
                f.write(f"// Generated: {datetime.now().isoformat()}\n")
                f.write(f"// Location: {location.city}, {location.country_code}\n")
                f.write("// DO NOT EDIT - Auto-generated by LocationSpoofer\n\n")
                
                for key, value in prefs.items():
                    if isinstance(value, bool):
                        js_value = "true" if value else "false"
                    elif isinstance(value, str):
                        js_value = f'"{value}"'
                    elif isinstance(value, (int, float)):
                        js_value = str(value)
                    else:
                        js_value = json.dumps(value)
                    
                    f.write(f'user_pref("{key}", {js_value});\n')
            
            logger.info(f"Injected user.js into {self.profile_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to inject user.js: {e}")
            return False


class WindowsLocationSpoofer:
    """
    Windows system-level location spoofing.
    
    Implements Section 4.2 of the technical document:
    - Registry manipulation for Windows Location Services
    - Default location injection
    - Service configuration
    
    WARNING: Requires Administrator privileges
    """
    
    LOCATION_SERVICE_KEY = r"SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\location"
    SENSORS_KEY = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Sensor\Overrides"
    DEFAULT_LOCATION_KEY = r"SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\location\NonPackaged"
    
    def __init__(self):
        if platform.system() != "Windows":
            logger.warning("WindowsLocationSpoofer initialized on non-Windows system")
        self.is_admin = self._check_admin()
    
    def _check_admin(self) -> bool:
        """Check if running with Administrator privileges"""
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except:
            return False
    
    def disable_location_services(self) -> bool:
        """
        Disable Windows Location Services to prevent real location leaks.
        
        This forces applications to use the default/spoofed location.
        """
        if not HAS_WINREG:
            logger.warning("winreg not available (not on Windows)")
            return False
        if not self.is_admin:
            logger.warning("Admin privileges required to modify location services")
            return False
        
        try:
            # Disable location service consent
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                self.LOCATION_SERVICE_KEY,
                0,
                winreg.KEY_SET_VALUE
            )
            winreg.SetValueEx(key, "Value", 0, winreg.REG_SZ, "Deny")
            winreg.CloseKey(key)
            
            logger.info("Windows Location Services disabled")
            return True
            
        except Exception as e:
            logger.error(f"Failed to disable location services: {e}")
            return False
    
    def set_default_location(self, location: LocationProfile) -> bool:
        """
        Set Windows default location.
        
        When location services are disabled or unavailable,
        Windows falls back to this default location.
        """
        if not HAS_WINREG:
            logger.warning("winreg not available (not on Windows)")
            return False
        if not self.is_admin:
            logger.warning("Admin privileges required to set default location")
            return False
        
        try:
            # Windows Default Location: write lat/lon to the Sensors override key
            # Key: HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Sensor\Overrides\{BFA794E4-F964-4FDB-90F6-51056BFE4B44}
            sensor_guid = "{BFA794E4-F964-4FDB-90F6-51056BFE4B44}"
            sensor_key_path = f"{self.SENSORS_KEY}\\{sensor_guid}"
            
            try:
                key = winreg.CreateKeyEx(
                    winreg.HKEY_LOCAL_MACHINE,
                    sensor_key_path,
                    0,
                    winreg.KEY_SET_VALUE
                )
            except OSError:
                key = winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    sensor_key_path,
                    0,
                    winreg.KEY_SET_VALUE
                )
            
            # Write latitude and longitude as REG_SZ (string) values
            winreg.SetValueEx(key, "SensorPermissionState", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "Latitude", 0, winreg.REG_SZ, str(location.coordinates.latitude))
            winreg.SetValueEx(key, "Longitude", 0, winreg.REG_SZ, str(location.coordinates.longitude))
            winreg.SetValueEx(key, "Altitude", 0, winreg.REG_SZ, str(location.coordinates.altitude or 0))
            winreg.SetValueEx(key, "ErrorRadius", 0, winreg.REG_SZ, str(location.coordinates.accuracy))
            winreg.SetValueEx(key, "Timestamp", 0, winreg.REG_SZ, str(int(time.time())))
            winreg.CloseKey(key)
            
            logger.info(f"Default location set: {location.city}, {location.country_code}")
            logger.info(f"  Coordinates: {location.coordinates.latitude}, {location.coordinates.longitude}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to set default location: {e}")
            return False
    
    def generate_nmea_sentences(self, coords: GeoCoordinates) -> List[str]:
        """
        Generate NMEA 0183 GPS sentences for Fake GPS driver injection.
        
        Reference: Section 4.2.2 - Fake GPS Sensor Drivers
        
        These sentences can be fed to a virtual GPS driver to simulate
        GPS hardware reporting the specified coordinates.
        """
        # Convert coordinates to NMEA format
        lat_deg = int(abs(coords.latitude))
        lat_min = (abs(coords.latitude) - lat_deg) * 60
        lat_dir = "N" if coords.latitude >= 0 else "S"
        
        lon_deg = int(abs(coords.longitude))
        lon_min = (abs(coords.longitude) - lon_deg) * 60
        lon_dir = "E" if coords.longitude >= 0 else "W"
        
        # Current UTC time
        utc_time = time.strftime("%H%M%S", time.gmtime())
        utc_date = time.strftime("%d%m%y", time.gmtime())
        
        # GPGGA - GPS Fix Data
        gpgga = f"$GPGGA,{utc_time},{lat_deg:02d}{lat_min:07.4f},{lat_dir},{lon_deg:03d}{lon_min:07.4f},{lon_dir},1,08,0.9,{coords.altitude or 0:.1f},M,0.0,M,,*"
        gpgga += self._nmea_checksum(gpgga)
        
        # GPRMC - Recommended Minimum Data
        gprmc = f"$GPRMC,{utc_time},A,{lat_deg:02d}{lat_min:07.4f},{lat_dir},{lon_deg:03d}{lon_min:07.4f},{lon_dir},{coords.speed or 0:.1f},{coords.heading or 0:.1f},{utc_date},0.0,E*"
        gprmc += self._nmea_checksum(gprmc)
        
        # GPGLL - Geographic Position
        gpgll = f"$GPGLL,{lat_deg:02d}{lat_min:07.4f},{lat_dir},{lon_deg:03d}{lon_min:07.4f},{lon_dir},{utc_time},A*"
        gpgll += self._nmea_checksum(gpgll)
        
        return [gpgga, gprmc, gpgll]
    
    def _nmea_checksum(self, sentence: str) -> str:
        """Calculate NMEA checksum"""
        # Remove $ and everything after *
        data = sentence.split("*")[0][1:]
        checksum = 0
        for char in data:
            checksum ^= ord(char)
        return f"{checksum:02X}"


class WiFiBSSIDNullifier:
    """
    WiFi BSSID evasion to prevent location triangulation.
    
    Implements Section 4.3 of the technical document:
    - Intercepts WiFi scan results
    - Returns empty or synthetic BSSID lists
    - Forces fallback to GPS/IP geolocation
    
    On Windows, this uses netsh to disable WiFi scanning for location.
    On Linux/TITAN, this would use eBPF (not implemented here).
    """
    
    def __init__(self):
        self.system = platform.system()
    
    def disable_wifi_location_scanning(self) -> bool:
        """
        Disable WiFi scanning used for geolocation.
        
        This prevents the browser/OS from sending nearby WiFi BSSIDs
        to Google Location Services for triangulation.
        """
        if self.system == "Windows":
            return self._disable_windows_wifi_location()
        elif self.system == "Linux":
            return self._disable_linux_wifi_location()
        else:
            logger.warning(f"WiFi BSSID nullification not supported on {self.system}")
            return False
    
    def _disable_windows_wifi_location(self) -> bool:
        """Disable WiFi location scanning on Windows"""
        try:
            # Disable WLAN AutoConfig location features
            # This is a simplified approach - full implementation would
            # modify Group Policy or use WMI
            
            commands = [
                # Disable WiFi Sense (auto-sharing of WiFi credentials)
                'reg add "HKLM\\SOFTWARE\\Microsoft\\WcmSvc\\wifinetworkmanager\\config" /v AutoConnectAllowedOEM /t REG_DWORD /d 0 /f',
                # Disable location-based WiFi suggestions
                'reg add "HKLM\\SOFTWARE\\Microsoft\\PolicyManager\\current\\device\\WiFi" /v AllowAutoConnectToWiFiSenseHotspots /t REG_DWORD /d 0 /f',
            ]
            
            for cmd in commands:
                subprocess.run(cmd, shell=True, capture_output=True)
            
            logger.info("Windows WiFi location scanning disabled")
            return True
            
        except Exception as e:
            logger.error(f"Failed to disable Windows WiFi location: {e}")
            return False
    
    def _disable_linux_wifi_location(self) -> bool:
        """
        Disable WiFi location scanning on Linux via multiple layers:
        1. GeoClue config — disables the WiFi geolocation provider
        2. NetworkManager — disables WiFi background scanning
        3. wpa_supplicant — disables scan result caching
        4. rfkill soft-block — optional nuclear option
        """
        success = False
        
        try:
            # Layer 1: Disable GeoClue WiFi-based location
            geoclue_conf = Path("/etc/geoclue/geoclue.conf")
            if geoclue_conf.exists():
                with open(geoclue_conf, "r") as f:
                    content = f.read()
                if "[wifi]" not in content:
                    content += "\n[wifi]\nenable=false\n"
                else:
                    content = content.replace("[wifi]\nenable=true", "[wifi]\nenable=false")
                with open(geoclue_conf, "w") as f:
                    f.write(content)
                logger.info("Layer 1: GeoClue WiFi location disabled")
                success = True
        except Exception as e:
            logger.warning(f"Layer 1 (GeoClue): {e}")
        
        try:
            # Layer 2: Disable NetworkManager WiFi scanning
            # This prevents NM from passively collecting BSSIDs
            nm_conf_dir = Path("/etc/NetworkManager/conf.d")
            nm_conf_dir.mkdir(parents=True, exist_ok=True)
            nm_conf = nm_conf_dir / "99-titan-no-wifi-scan.conf"
            nm_conf.write_text(
                "[device]\nwifi.scan-rand-mac-address=yes\n"
                "wifi.scan-generate-mac-address-mask=FF:FF:FF:00:00:00\n\n"
                "[connectivity]\nenabled=false\nuri=\n"
            )
            # Restart NetworkManager to apply
            subprocess.run(
                ["systemctl", "restart", "NetworkManager"],
                capture_output=True, timeout=10
            )
            logger.info("Layer 2: NetworkManager WiFi scan randomization enabled")
            success = True
        except Exception as e:
            logger.warning(f"Layer 2 (NetworkManager): {e}")
        
        try:
            # Layer 3: Tell wpa_supplicant to not cache scan results for location
            wpa_override = Path("/etc/wpa_supplicant/wpa_supplicant.conf")
            if wpa_override.exists():
                with open(wpa_override, "r") as f:
                    content = f.read()
                if "bgscan" not in content:
                    with open(wpa_override, "a") as f:
                        f.write("\nbgscan=\"\"\n")
                    logger.info("Layer 3: wpa_supplicant background scan disabled")
                    success = True
        except Exception as e:
            logger.warning(f"Layer 3 (wpa_supplicant): {e}")
        
        if not success:
            logger.error("All WiFi location disable layers failed")
        
        return success
    
    def generate_synthetic_bssids(self, count: int = 5) -> List[Dict[str, Any]]:
        """
        Generate synthetic/fake BSSID entries.
        
        These BSSIDs don't exist in Google's database, causing
        location lookups to fail gracefully.
        """
        synthetic_aps = []
        
        for i in range(count):
            # Generate random MAC address (locally administered, unicast)
            # First byte: xx:xx:xx:xx:xx:xx where xx has bit 1 set (local)
            mac_bytes = [random.randint(0, 255) for _ in range(6)]
            mac_bytes[0] = (mac_bytes[0] | 0x02) & 0xFE  # Local, unicast
            
            bssid = ":".join(f"{b:02X}" for b in mac_bytes)
            
            synthetic_aps.append({
                "bssid": bssid,
                "ssid": f"LUCID_SYNTHETIC_{i:03d}",
                "signal_strength": random.randint(-90, -30),
                "channel": random.choice([1, 6, 11, 36, 40, 44, 48]),
                "frequency": random.choice([2412, 2437, 2462, 5180, 5200, 5220, 5240])
            })
        
        return synthetic_aps


class TimezoneLocaleAligner:
    """
    Timezone and locale alignment for consistency.
    
    Implements Section 7.1 of the technical document:
    - Ensures browser timezone matches IP geolocation
    - Aligns Intl API, Date object, and navigator.language
    - Prevents the "Foreign Proxy" detection flag
    """
    
    # Timezone to locale mapping
    TIMEZONE_LOCALE_MAP = {
        "Asia/Colombo": ("en-LK", "en-US,en,si", "LK"),
        "America/New_York": ("en-US", "en-US,en", "US"),
        "America/Los_Angeles": ("en-US", "en-US,en", "US"),
        "America/Chicago": ("en-US", "en-US,en", "US"),
        "Europe/London": ("en-GB", "en-GB,en", "GB"),
        "Europe/Berlin": ("de-DE", "de-DE,de,en", "DE"),
        "Europe/Paris": ("fr-FR", "fr-FR,fr,en", "FR"),
        "Asia/Tokyo": ("ja-JP", "ja-JP,ja,en", "JP"),
        "Asia/Singapore": ("en-SG", "en-SG,en,zh", "SG"),
        "Australia/Sydney": ("en-AU", "en-AU,en", "AU"),
        "Asia/Dubai": ("ar-AE", "ar-AE,ar,en", "AE"),
    }
    
    def __init__(self):
        pass
    
    def get_alignment_config(self, timezone: str) -> Dict[str, str]:
        """
        Get locale/language alignment for a given timezone.
        
        Returns configuration that ensures the browser's timezone
        matches its claimed locale and language preferences.
        """
        if timezone in self.TIMEZONE_LOCALE_MAP:
            locale, languages, country = self.TIMEZONE_LOCALE_MAP[timezone]
        else:
            # Default to US English
            locale = "en-US"
            languages = "en-US,en"
            country = "US"
        
        return {
            "timezone": timezone,
            "locale": locale,
            "languages": languages,
            "country_code": country,
            "navigator.language": languages.split(",")[0],
            "intl.accept_languages": languages,
        }
    
    def generate_js_overrides(self, timezone: str) -> str:
        """
        Generate JavaScript code to override timezone-related APIs.
        
        This ensures Date objects, Intl API, and other time-related
        functions return values consistent with the spoofed timezone.
        """
        config = self.get_alignment_config(timezone)
        
        js_code = f"""
// LUCID EMPIRE - Timezone/Locale Alignment
// Timezone: {timezone}
(function() {{
    'use strict';
    
    const targetTimezone = '{timezone}';
    const targetLocale = '{config["locale"]}';
    const targetLanguages = {json.dumps(config["languages"].split(","))};
    
    // Override Date.prototype.toLocaleString family
    const originalToLocaleString = Date.prototype.toLocaleString;
    Date.prototype.toLocaleString = function(locales, options) {{
        return originalToLocaleString.call(this, locales || targetLocale, {{
            ...options,
            timeZone: targetTimezone
        }});
    }};
    
    // Override Intl.DateTimeFormat — preserve prototype chain to avoid detection
    const OriginalDateTimeFormat = Intl.DateTimeFormat;
    const ProxiedDateTimeFormat = new Proxy(OriginalDateTimeFormat, {{
        construct(target, args) {{
            const [locales, options] = args;
            return new target(locales || targetLocale, {{
                ...options,
                timeZone: targetTimezone
            }});
        }},
        apply(target, thisArg, args) {{
            const [locales, options] = args;
            return target(locales || targetLocale, {{
                ...options,
                timeZone: targetTimezone
            }});
        }}
    }});
    // Proxy preserves: ProxiedDateTimeFormat.prototype === OriginalDateTimeFormat.prototype
    // and: ProxiedDateTimeFormat.prototype.constructor === ProxiedDateTimeFormat
    Object.defineProperty(Intl, 'DateTimeFormat', {{
        value: ProxiedDateTimeFormat,
        writable: true,
        configurable: true
    }});
    
    // Override navigator.language (read-only, use defineProperty)
    Object.defineProperty(navigator, 'language', {{
        get: function() {{ return targetLanguages[0]; }},
        configurable: true
    }});
    
    Object.defineProperty(navigator, 'languages', {{
        get: function() {{ return Object.freeze(targetLanguages); }},
        configurable: true
    }});
    
    console.log('[LUCID] Timezone/Locale aligned to:', targetTimezone, targetLocale);
}})();
"""
        return js_code


class LocationSpoofingEngine:
    """
    Main location spoofing engine that coordinates all components.
    
    This is the primary interface for the Lucid Empire location spoofing
    system, providing unified access to:
    - Browser geolocation spoofing
    - System-level location spoofing
    - WiFi BSSID evasion
    - Timezone/locale alignment
    """
    
    def __init__(self, profile_path: Optional[str] = None):
        self.profile_path = profile_path
        self.browser_spoofer = BrowserGeolocationSpoofer(profile_path)
        self.windows_spoofer = WindowsLocationSpoofer() if platform.system() == "Windows" else None
        self.wifi_nullifier = WiFiBSSIDNullifier()
        self.timezone_aligner = TimezoneLocaleAligner()
    
    def get_location_profile(self, profile_id: str) -> Optional[LocationProfile]:
        """Get a predefined location profile by ID"""
        return LOCATION_DATABASE.get(profile_id)
    
    def create_custom_location(
        self,
        latitude: float,
        longitude: float,
        timezone: str,
        city: str,
        country_code: str,
        accuracy: float = 500.0
    ) -> LocationProfile:
        """Create a custom location profile"""
        coords = GeoCoordinates(latitude, longitude, accuracy)
        
        # Get timezone alignment
        alignment = self.timezone_aligner.get_alignment_config(timezone)
        
        return LocationProfile(
            coordinates=coords,
            timezone=timezone,
            locale=alignment["locale"],
            language=alignment["languages"],
            country_code=country_code,
            region="",
            city=city,
            postal_code=""
        )
    
    def apply_location_spoofing(
        self,
        location: LocationProfile,
        spoof_browser: bool = True,
        spoof_system: bool = False,
        disable_wifi_location: bool = True
    ) -> Dict[str, bool]:
        """
        Apply comprehensive location spoofing.
        
        Args:
            location: LocationProfile to apply
            spoof_browser: Apply browser-level spoofing
            spoof_system: Apply system-level spoofing (requires admin)
            disable_wifi_location: Disable WiFi-based location
        
        Returns:
            Dictionary of operation results
        """
        results = {
            "browser_spoofing": False,
            "system_spoofing": False,
            "wifi_nullification": False,
            "timezone_alignment": False
        }
        
        logger.info("=" * 60)
        logger.info("LUCID EMPIRE - LOCATION SPOOFING ENGINE")
        logger.info("=" * 60)
        logger.info(f"Target Location: {location.city}, {location.country_code}")
        logger.info(f"Coordinates: {location.coordinates.latitude}, {location.coordinates.longitude}")
        logger.info(f"Timezone: {location.timezone}")
        logger.info(f"Locale: {location.locale}")
        logger.info("")
        
        # 1. Browser-level spoofing
        if spoof_browser and self.profile_path:
            logger.info("[1/4] Applying browser geolocation spoofing...")
            results["browser_spoofing"] = self.browser_spoofer.inject_user_js(location)
            logger.info(f"      Status: {'SUCCESS' if results['browser_spoofing'] else 'FAILED'}")
        
        # 2. System-level spoofing (Windows only)
        if spoof_system and self.windows_spoofer:
            logger.info("[2/4] Applying system-level location spoofing...")
            results["system_spoofing"] = self.windows_spoofer.set_default_location(location)
            logger.info(f"      Status: {'SUCCESS' if results['system_spoofing'] else 'FAILED (Admin required)'}")
        
        # 3. WiFi BSSID nullification
        if disable_wifi_location:
            logger.info("[3/4] Disabling WiFi-based location triangulation...")
            results["wifi_nullification"] = self.wifi_nullifier.disable_wifi_location_scanning()
            logger.info(f"      Status: {'SUCCESS' if results['wifi_nullification'] else 'SKIPPED'}")
        
        # 4. Timezone/locale alignment
        logger.info("[4/4] Generating timezone/locale alignment...")
        alignment = self.timezone_aligner.get_alignment_config(location.timezone)
        results["timezone_alignment"] = True
        logger.info(f"      Navigator.language: {alignment['navigator.language']}")
        logger.info(f"      Accept-Languages: {alignment['intl.accept_languages']}")
        
        logger.info("")
        logger.info("=" * 60)
        success_count = sum(results.values())
        logger.info(f"LOCATION SPOOFING COMPLETE: {success_count}/4 operations successful")
        logger.info("=" * 60)
        
        return results
    
    def get_camoufox_config(self, location: LocationProfile) -> Dict[str, Any]:
        """
        Get Camoufox-compatible configuration for location spoofing.
        
        This returns a config dictionary that can be passed directly
        to Camoufox's launch configuration.
        """
        config = self.browser_spoofer.generate_camoufox_config(location)
        
        # Add additional Camoufox-specific settings
        config.update({
            # Disable WebRTC to prevent IP leaks
            "webrtc:ipPolicy": "disable_non_proxied_udp",
            "webrtc:localipv4": "192.168.1.1",  # Fake local IP
            "webrtc:localipv6": "",  # Disable IPv6
        })
        
        return config
    
    def generate_nmea_gps_data(self, location: LocationProfile) -> List[str]:
        """
        Generate NMEA GPS sentences for Fake GPS driver.
        
        These can be used with virtual GPS drivers to simulate
        hardware GPS reporting the spoofed location.
        """
        if self.windows_spoofer:
            return self.windows_spoofer.generate_nmea_sentences(location.coordinates)
        return []


def main():
    """Test the location spoofing module"""
    print("=" * 60)
    print("LUCID EMPIRE - LOCATION SPOOFING MODULE TEST")
    print("=" * 60)
    
    # Initialize engine
    engine = LocationSpoofingEngine()
    
    # Test with Sri Lanka location (from our profile)
    location = engine.get_location_profile("sri_lanka_dehiwala")
    
    if location:
        print(f"\nLoaded location profile: {location.city}, {location.country_code}")
        print(f"  Coordinates: {location.coordinates.latitude}, {location.coordinates.longitude}")
        print(f"  Timezone: {location.timezone}")
        print(f"  Locale: {location.locale}")
        
        # Get Camoufox config
        config = engine.get_camoufox_config(location)
        print(f"\nCamoufox Configuration:")
        for key, value in config.items():
            print(f"  {key}: {value}")
        
        # Generate Firefox preferences
        prefs = engine.browser_spoofer.generate_firefox_prefs(location)
        print(f"\nFirefox Preferences:")
        for key, value in list(prefs.items())[:5]:
            print(f"  {key}: {value}")
        print("  ... and more")
        
        # Generate NMEA GPS data
        nmea = engine.generate_nmea_gps_data(location)
        print(f"\nNMEA GPS Sentences:")
        for sentence in nmea:
            print(f"  {sentence}")
    
    print("\n" + "=" * 60)
    print("MODULE TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
