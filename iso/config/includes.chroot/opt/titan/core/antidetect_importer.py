#!/usr/bin/env python3
"""
OBLIVION FORGE NEXUS v5.0 - Advanced Profile Importer
Imports forged profiles into anti-detect browsers with full fingerprint synchronization
"""

import os
import sys
import json
import shutil
import sqlite3
import zipfile
import hashlib
import argparse
import tempfile
import platform
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

# ── Titan Core Module Wiring ────────────────────────────────────────────
try:
    from fingerprint_injector import FingerprintInjector, FingerprintConfig
    _FP_INJECTOR_AVAILABLE = True
except ImportError:
    _FP_INJECTOR_AVAILABLE = False

try:
    from location_spoofer_linux import LinuxLocationSpoofer, get_location_spoofer
    _LOCATION_SPOOFER_AVAILABLE = True
except ImportError:
    _LOCATION_SPOOFER_AVAILABLE = False

try:
    from titan_session import get_session, save_session
    _SESSION_AVAILABLE = True
except ImportError:
    _SESSION_AVAILABLE = False

class OblivionImporter:
    """Advanced profile importer with fingerprint synchronization"""
    
    def __init__(self, target_software: str = "multilogin"):
        self.target_software = target_software.lower()
        self.profiles_path = None
        self.fingerprint_db = {}
        
        # Software-specific paths
        self.software_paths = {
            "camoufox": {
                "windows": [
                    os.path.expanduser("~/AppData/Local/Camoufox"),
                    "C:/Program Files/Camoufox"
                ],
                "darwin": [
                    os.path.expanduser("~/Library/Application Support/Camoufox"),
                    "/Applications/Camoufox.app/Contents/Resources"
                ],
                "linux": [
                    "/opt/camoufox",
                    os.path.expanduser("~/.camoufox"),
                    "/opt/titan/profiles"
                ]
            },
            "multilogin": {
                "windows": [
                    os.path.expanduser("~/AppData/Local/Multilogin"),
                    "C:/Program Files/Multilogin"
                ],
                "darwin": [
                    os.path.expanduser("~/Library/Application Support/Multilogin"),
                    "/Applications/Multilogin.app/Contents/Resources"
                ],
                "linux": [
                    os.path.expanduser("~/.multilogin"),
                    "/opt/multilogin"
                ]
            },
            "dolphin": {
                "windows": [
                    os.path.expanduser("~/AppData/Local/Dolphin"),
                    "C:/Program Files/Dolphin Anti-Browser"
                ],
                "darwin": [
                    os.path.expanduser("~/Library/Application Support/Dolphin"),
                ],
                "linux": [
                    os.path.expanduser("~/.dolphin"),
                ]
            },
            "indigo": {
                "windows": [
                    os.path.expanduser("~/AppData/Local/Indigo"),
                ],
                "darwin": [
                    os.path.expanduser("~/Library/Application Support/Indigo"),
                ]
            }
        }
        
        self.find_target_path()
    
    def find_target_path(self) -> bool:
        """Find target anti-detect software installation"""
        system = platform.system().lower()
        
        if self.target_software not in self.software_paths:
            print(f"[!] Unsupported software: {self.target_software}")
            return False
        
        if system not in self.software_paths[self.target_software]:
            print(f"[!] Unsupported platform: {system}")
            return False
        
        # Check paths
        for path_str in self.software_paths[self.target_software][system]:
            path = Path(path_str)
            if path.exists():
                print(f"[+] Found {self.target_software} at: {path}")
                
                # Determine profiles directory
                if self.target_software == "camoufox":
                    self.profiles_path = path / "profiles"
                elif self.target_software == "multilogin":
                    self.profiles_path = path / "profiles"
                elif self.target_software == "dolphin":
                    self.profiles_path = path / "browser_profiles"
                elif self.target_software == "indigo":
                    self.profiles_path = path / "profiles"
                
                if not self.profiles_path.exists():
                    self.profiles_path.mkdir(parents=True, exist_ok=True)
                
                return True
        
        print(f"[!] {self.target_software} not found in standard locations")
        return False
    
    def import_profile(self, source_path: str, profile_name: str = None,
                      fingerprint_config: Dict = None) -> bool:
        """Import profile with full fingerprint synchronization"""
        
        source = Path(source_path)
        if not source.exists():
            print(f"[!] Source profile not found: {source_path}")
            return False
        
        # Generate profile name
        if not profile_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            profile_name = f"oblivion_forged_{timestamp}"
        
        # Create profile directory
        profile_dir = self.profiles_path / profile_name
        profile_dir.mkdir(exist_ok=True)
        
        try:
            print(f"[+] Importing profile: {profile_name}")
            
            # Copy or extract source
            if source.is_file() and source.suffix == '.zip':
                with zipfile.ZipFile(source, 'r') as zip_ref:
                    zip_ref.extractall(profile_dir)
            else:
                shutil.copytree(source, profile_dir, dirs_exist_ok=True)
            
            # Synchronize fingerprint
            self.synchronize_fingerprint(profile_dir, fingerprint_config)
            
            # Create software-specific metadata
            self.create_software_metadata(profile_dir, profile_name)
            
            # Validate import
            validation = self.validate_import(profile_dir)
            
            if validation["success"]:
                print(f"[+] Profile imported successfully: {profile_dir}")
                print(f"    Fingerprint: {validation['fingerprint_status']}")
                print(f"    Cookies: {validation['cookies_count']}")
                print(f"    Storage: {validation['storage_status']}")
                return True
            else:
                print(f"[!] Import validation failed")
                return False
            
        except Exception as e:
            print(f"[!] Import failed: {e}")
            # Cleanup on failure
            try:
                shutil.rmtree(profile_dir, ignore_errors=True)
            except:
                pass
            return False
    
    def synchronize_fingerprint(self, profile_dir: Path, 
                              config: Optional[Dict] = None) -> bool:
        """Synchronize browser fingerprint across all artifacts"""
        try:
            # Default fingerprint config
            if not config:
                config = {
                    "canvas": "noise",
                    "webgl": "noise",
                    "audio": "noise",
                    "timezone": "auto",
                    "geolocation": "auto",
                    "screen": {
                        "width": 1920,
                        "height": 1080,
                        "colorDepth": 24
                    },
                    "fonts": [
                        "Arial", "Times New Roman", "Courier New",
                        "Verdana", "Georgia", "Trebuchet MS"
                    ],
                    "plugins": [
                        "Chrome PDF Plugin",
                        "Chrome PDF Viewer",
                        "Native Client"
                    ],
                    "mimeTypes": [
                        "application/pdf",
                        "text/pdf"
                    ]
                }
            
            # ── Camoufox / Firefox profile handling ──
            if self.target_software == "camoufox":
                return self._synchronize_firefox_fingerprint(profile_dir, config)
            
            # ── Chrome-based profile handling (Multilogin/Dolphin/Indigo) ──
            # 1. Update Preferences file
            prefs_path = profile_dir / "Preferences"
            if prefs_path.exists():
                with open(prefs_path, 'r', encoding='utf-8') as f:
                    prefs = json.load(f)
                
                # Ensure fingerprint section
                if "oblivion_fingerprint" not in prefs:
                    prefs["oblivion_fingerprint"] = {}
                
                prefs["oblivion_fingerprint"].update({
                    "synchronized": True,
                    "timestamp": datetime.now().isoformat(),
                    "config": config
                })
                
                # Update platform-specific settings
                if platform.system() == "Windows":
                    prefs["platform"] = "Win32"
                    prefs["user_agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                elif platform.system() == "Darwin":
                    prefs["platform"] = "MacIntel"
                    prefs["user_agent"] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                
                with open(prefs_path, 'w', encoding='utf-8') as f:
                    json.dump(prefs, f, indent=2)
            
            # 2. Create fingerprint manifest
            manifest = {
                "engine": "OblivionForge v5.0",
                "import_timestamp": datetime.now().isoformat(),
                "target_software": self.target_software,
                "fingerprint_hash": hashlib.sha256(
                    json.dumps(config, sort_keys=True).encode()
                ).hexdigest()[:32],
                "artifacts": self.scan_artifacts(profile_dir)
            }
            
            manifest_path = profile_dir / "fingerprint_manifest.json"
            with open(manifest_path, 'w') as f:
                json.dump(manifest, f, indent=2)
            
            # 3. Inject fingerprint into Local State (Chrome)
            local_state_path = profile_dir / "Local State"
            if local_state_path.exists():
                with open(local_state_path, 'r', encoding='utf-8') as f:
                    local_state = json.load(f)
                
                if "oblivion" not in local_state:
                    local_state["oblivion"] = {}
                
                local_state["oblivion"]["fingerprint_injected"] = True
                local_state["oblivion"]["import_timestamp"] = datetime.now().isoformat()
                
                with open(local_state_path, 'w', encoding='utf-8') as f:
                    json.dump(local_state, f, ensure_ascii=False, indent=2)
            
            print(f"[+] Fingerprint synchronized")
            return True
            
        except Exception as e:
            print(f"[!] Fingerprint synchronization failed: {e}")
            return False
    
    def _synchronize_firefox_fingerprint(self, profile_dir: Path, config: Dict) -> bool:
        """Synchronize fingerprint for Firefox/Camoufox profiles.
        
        Firefox uses prefs.js/user.js instead of Preferences JSON,
        cookies.sqlite instead of Cookies SQLite, and places.sqlite
        for history. This method wires fingerprint_injector to produce
        Camoufox-native hardening files.
        """
        try:
            # 1. Use fingerprint_injector for real FP hardening
            if _FP_INJECTOR_AVAILABLE:
                profile_uuid = hashlib.sha256(
                    json.dumps(config, sort_keys=True).encode()
                ).hexdigest()[:32]
                fp_cfg = FingerprintConfig(profile_uuid=profile_uuid)
                fp_injector = FingerprintInjector(fp_cfg)
                
                # Write policies.json (highest priority pref lock)
                fp_injector.write_policies_json(profile_dir)
                
                # Write user.js (defense-in-depth pref lock)
                fp_injector.write_user_js(profile_dir)
                
                # Write fingerprint_config.json
                fp_injector.write_to_profile(profile_dir)
                
                logger.info("[CAMOUFOX] Firefox fingerprint synchronized via FingerprintInjector")
            
            # 2. Create fingerprint manifest
            manifest = {
                "engine": "OblivionForge v5.0 + Camoufox",
                "import_timestamp": datetime.now().isoformat(),
                "target_software": "camoufox",
                "browser_type": "firefox",
                "fingerprint_hash": hashlib.sha256(
                    json.dumps(config, sort_keys=True).encode()
                ).hexdigest()[:32],
                "hardening": {
                    "policies_json": (profile_dir / "distribution" / "policies.json").exists(),
                    "user_js": (profile_dir / "user.js").exists(),
                    "fingerprint_config": (profile_dir / "fingerprint_config.json").exists(),
                    "location_config": (profile_dir / "location_config.json").exists(),
                },
                "artifacts": self.scan_artifacts(profile_dir)
            }
            
            manifest_path = profile_dir / "fingerprint_manifest.json"
            with open(manifest_path, 'w') as f:
                json.dump(manifest, f, indent=2)
            
            print(f"[+] Camoufox fingerprint synchronized")
            return True
            
        except Exception as e:
            logger.error(f"[CAMOUFOX] Firefox fingerprint sync failed: {e}")
            return False
    
    def get_camoufox_launch_config(self, profile_name: str,
                                    proxy: Optional[str] = None,
                                    headless: bool = False) -> Dict[str, Any]:
        """Generate a Camoufox launch config dict for integration_bridge.
        
        Returns a dict that can be passed directly to Camoufox(**kwargs).
        Reads the profile's camoufox_profile.json and fingerprint_config.json
        to build the full launch parameters.
        """
        if not self.profiles_path:
            return {}
        
        profile_dir = self.profiles_path / profile_name
        if not profile_dir.exists():
            logger.warning(f"Profile not found: {profile_name}")
            return {}
        
        # Start with base Camoufox kwargs
        launch_config = {
            "headless": headless,
            "humanize": True,
            "block_webrtc": True,
            "config": {},
        }
        
        # Load camoufox_profile.json for FP config
        meta_file = profile_dir / "camoufox_profile.json"
        if meta_file.exists():
            try:
                with open(meta_file, 'r') as f:
                    meta = json.load(f)
                camoufox_cfg = meta.get("camoufox_config", {})
                if camoufox_cfg:
                    launch_config["config"].update(camoufox_cfg)
            except Exception as e:
                logger.debug(f"Failed to read camoufox_profile.json: {e}")
        
        # Load location_config.json for geo/timezone
        loc_file = profile_dir / "location_config.json"
        if loc_file.exists():
            try:
                with open(loc_file, 'r') as f:
                    loc = json.load(f)
                launch_config["config"]["geolocation:latitude"] = loc.get("latitude", 0)
                launch_config["config"]["geolocation:longitude"] = loc.get("longitude", 0)
                launch_config["config"]["geolocation:accuracy"] = loc.get("accuracy", 100)
                if loc.get("timezone"):
                    launch_config["config"]["timezone"] = loc["timezone"]
                if loc.get("locale"):
                    locale_str = loc["locale"].split(".")[0].replace("_", "-")
                    launch_config["config"]["locale"] = locale_str
            except Exception as e:
                logger.debug(f"Failed to read location_config.json: {e}")
        
        # Add proxy if provided
        if proxy:
            launch_config["proxy"] = {"server": proxy}
        
        # Record in session if available
        if _SESSION_AVAILABLE:
            try:
                session = get_session()
                session["active_browser"] = "camoufox"
                session["active_profile"] = profile_name
                session["profile_path"] = str(profile_dir)
                save_session(session)
            except Exception:
                pass
        
        return launch_config
    
    def import_to_camoufox(self, source_path: str, profile_name: str = None,
                           fingerprint_config: Dict = None,
                           proxy: Optional[str] = None) -> Dict[str, Any]:
        """Convenience method: import profile and return Camoufox launch config.
        
        Combines import_profile() + get_camoufox_launch_config() in one call.
        Returns the launch config dict on success, empty dict on failure.
        """
        if self.target_software != "camoufox":
            logger.warning("import_to_camoufox requires target_software='camoufox'")
            return {}
        
        if not profile_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            profile_name = f"camoufox_forged_{timestamp}"
        
        success = self.import_profile(source_path, profile_name, fingerprint_config)
        if not success:
            return {}
        
        return self.get_camoufox_launch_config(profile_name, proxy=proxy)
    
    def scan_artifacts(self, profile_dir: Path) -> Dict[str, Any]:
        """Scan profile for all artifacts"""
        artifacts = {
            "cookies": [],
            "localstorage": [],
            "history": [],
            "cache": [],
            "databases": [],
            "preferences": []
        }
        
        try:
            # Scan for SQLite databases
            for db_file in profile_dir.rglob("*.sqlite"):
                try:
                    conn = sqlite3.connect(db_file)
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    tables = [row[0] for row in cursor.fetchall()]
                    conn.close()
                    
                    artifacts["databases"].append({
                        "path": str(db_file.relative_to(profile_dir)),
                        "tables": tables
                    })
                except:
                    pass
            
            # Scan for cookies
            cookie_files = [
                profile_dir / "Cookies",
                profile_dir / "Default" / "Network" / "Cookies",
                profile_dir / "cookies.sqlite"
            ]
            
            for cookie_file in cookie_files:
                if cookie_file.exists():
                    artifacts["cookies"].append(str(cookie_file.relative_to(profile_dir)))
            
            # Scan for cache
            cache_dirs = ["Cache", "Application Cache", "Cache/Cache_Data"]
            for cache_dir in cache_dirs:
                cache_path = profile_dir / cache_dir
                if cache_path.exists():
                    artifacts["cache"].append(str(cache_path.relative_to(profile_dir)))
            
            # Check preferences
            if (profile_dir / "Preferences").exists():
                artifacts["preferences"].append("Preferences")
            
        except Exception as e:
            print(f"[!] Artifact scan failed: {e}")
        
        return artifacts
    
    def create_software_metadata(self, profile_dir: Path, profile_name: str):
        """Create software-specific metadata files"""
        
        base_metadata = {
            "name": profile_name,
            "created": datetime.now().isoformat(),
            "engine": "OblivionForge v5.0",
            "notes": "Advanced synthetic profile with detection bypass"
        }
        
        if self.target_software == "camoufox":
            metadata = {
                **base_metadata,
                "browser": "firefox",
                "engine": "Camoufox (Patched Firefox)",
                "os": platform.system().lower(),
                "navigator": {
                    "userAgent": "Mozilla/5.0 (X11; Linux x86_64; rv:146.0) Gecko/20100101 Firefox/146.0",
                    "platform": "Linux x86_64" if platform.system() == "Linux" else "Win32",
                    "language": "en-US",
                    "languages": ["en-US", "en"]
                },
                "fingerprint": {
                    "canvas": "c++_level",
                    "webgl": "c++_level",
                    "audio": "c++_level",
                    "webrtc": "blocked",
                    "humanize": True
                },
                "camoufox_config": {},
                "proxy": {"mode": "none"}
            }
            
            # Wire fingerprint_injector for real FP data
            if _FP_INJECTOR_AVAILABLE:
                try:
                    fp_cfg = FingerprintConfig(profile_uuid=profile_name)
                    fp_injector = FingerprintInjector(fp_cfg)
                    camoufox_cfg = fp_injector.get_camoufox_config()
                    metadata["camoufox_config"] = camoufox_cfg
                    
                    # Write policies.json + user.js (locks prefs against Camoufox C++ override)
                    fp_injector.harden_profile(profile_dir)
                    logger.info(f"[CAMOUFOX] Fingerprint hardened: policies.json + user.js written")
                except Exception as e:
                    logger.warning(f"[CAMOUFOX] Fingerprint injection partial: {e}")
            
            # Wire location_spoofer for geo/timezone/locale
            if _LOCATION_SPOOFER_AVAILABLE:
                try:
                    spoofer = get_location_spoofer()
                    spoofer.write_location_config(str(profile_dir), spoofer.get_current_location())
                    logger.info(f"[CAMOUFOX] Location config written")
                except Exception as e:
                    logger.debug(f"[CAMOUFOX] Location config skipped: {e}")
            
            meta_file = profile_dir / "camoufox_profile.json"
            
        elif self.target_software == "multilogin":
            metadata = {
                **base_metadata,
                "browser": "mimic",
                "os": "windows" if platform.system() == "Windows" else "macos",
                "navigator": {
                    "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "platform": "Win32",
                    "language": "en-US",
                    "languages": ["en-US", "en"]
                },
                "canvas": {"mode": "noise"},
                "webgl": {"mode": "noise"},
                "audio": {"mode": "noise"},
                "timezone": {"mode": "real"},
                "geolocation": {"mode": "real"},
                "storage": {"mode": "real"},
                "extensions": [],
                "proxy": {"mode": "none"}
            }
            
            meta_file = profile_dir / "profile.json"
            
        elif self.target_software == "dolphin":
            metadata = {
                **base_metadata,
                "browserType": "chrome",
                "osType": "windows",
                "fingerprint": {
                    "webrtc": "disabled",
                    "canvas": "randomized",
                    "webgl": "randomized"
                }
            }
            
            meta_file = profile_dir / "dolphin_profile.json"
            
        elif self.target_software == "indigo":
            metadata = {
                **base_metadata,
                "profile_type": "chrome",
                "platform": "windows",
                "fingerprint_settings": {
                    "canvas_noise": True,
                    "webgl_noise": True,
                    "audio_noise": True
                }
            }
            
            meta_file = profile_dir / "indigo_profile.json"
        
        else:
            metadata = base_metadata
            meta_file = profile_dir / "metadata.json"
        
        # Write metadata
        with open(meta_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"[+] {self.target_software} metadata created: {meta_file}")
    
    def validate_import(self, profile_dir: Path) -> Dict[str, Any]:
        """Validate imported profile integrity"""
        validation = {
            "success": False,
            "fingerprint_status": "unknown",
            "cookies_count": 0,
            "storage_status": "unknown",
            "errors": []
        }
        
        try:
            # Check fingerprint manifest
            manifest_path = profile_dir / "fingerprint_manifest.json"
            if manifest_path.exists():
                validation["fingerprint_status"] = "synchronized"
            else:
                validation["fingerprint_status"] = "not_synchronized"
                validation["errors"].append("Missing fingerprint manifest")
            
            # Count cookies — handle both Chrome and Firefox formats
            cookie_files = [
                # Chrome-based
                profile_dir / "Cookies",
                profile_dir / "Default" / "Network" / "Cookies",
                # Firefox/Camoufox
                profile_dir / "cookies.sqlite",
            ]
            
            for cookie_file in cookie_files:
                if cookie_file.exists():
                    try:
                        conn = sqlite3.connect(cookie_file)
                        cursor = conn.cursor()
                        # Firefox uses 'moz_cookies', Chrome uses 'cookies'
                        for table in ("moz_cookies", "cookies"):
                            try:
                                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                                count = cursor.fetchone()[0]
                                validation["cookies_count"] += count
                                break
                            except sqlite3.OperationalError:
                                continue
                        conn.close()
                    except:
                        pass
            
            # Check storage — handle both Chrome and Firefox paths
            storage_paths = [
                # Chrome-based
                profile_dir / "Local Storage",
                profile_dir / "IndexedDB",
                profile_dir / "Session Storage",
                # Firefox/Camoufox
                profile_dir / "webappsstore.sqlite",
                profile_dir / "storage",
            ]
            
            storage_exists = any(path.exists() for path in storage_paths)
            validation["storage_status"] = "found" if storage_exists else "missing"
            
            # For Camoufox, also validate hardening files
            if self.target_software == "camoufox":
                validation["hardening"] = {
                    "policies_json": (profile_dir / "distribution" / "policies.json").exists(),
                    "user_js": (profile_dir / "user.js").exists(),
                    "fingerprint_config": (profile_dir / "fingerprint_config.json").exists(),
                }
                # Camoufox profiles succeed if fingerprint is synced (cookies may be forged later)
                if validation["fingerprint_status"] == "synchronized":
                    validation["success"] = True
            else:
                # Chrome-based: need cookies + storage + fingerprint
                if (validation["fingerprint_status"] == "synchronized" and 
                    validation["cookies_count"] > 0 and
                    validation["storage_status"] == "found"):
                    validation["success"] = True
            
        except Exception as e:
            validation["errors"].append(f"Validation error: {e}")
        
        return validation
    
    def list_profiles(self) -> List[Dict[str, Any]]:
        """List all imported profiles"""
        if not self.profiles_path or not self.profiles_path.exists():
            return []
        
        profiles = []
        for item in self.profiles_path.iterdir():
            if item.is_dir():
                # Look for metadata files
                meta_files = [
                    item / "camoufox_profile.json",
                    item / "profile.json",
                    item / "dolphin_profile.json",
                    item / "indigo_profile.json",
                    item / "fingerprint_manifest.json"
                ]
                
                profile_data = {
                    "name": item.name,
                    "path": str(item),
                    "imported": "unknown",
                    "fingerprint": "unknown",
                    "cookies": 0
                }
                
                # Check for metadata
                for meta_file in meta_files:
                    if meta_file.exists():
                        try:
                            with open(meta_file, 'r') as f:
                                meta = json.load(f)
                            
                            if "created" in meta:
                                profile_data["imported"] = meta["created"]
                            if "engine" in meta:
                                profile_data["engine"] = meta["engine"]
                            
                            break
                        except:
                            pass
                
                # Count cookies
                cookie_file = item / "Cookies"
                if cookie_file.exists():
                    try:
                        conn = sqlite3.connect(cookie_file)
                        cursor = conn.cursor()
                        cursor.execute("SELECT COUNT(*) FROM cookies")
                        profile_data["cookies"] = cursor.fetchone()[0]
                        conn.close()
                    except:
                        pass
                
                profiles.append(profile_data)
        
        return profiles

def main():
    parser = argparse.ArgumentParser(
        description="OBLIVION FORGE NEXUS v5.0 - Advanced Profile Importer",
        epilog="""
Examples:
  # Import to Multilogin
  oblivion_importer.py --software multilogin --import /path/to/profile
  
  # Import with custom name
  oblivion_importer.py --software dolphin --import /path/to/profile --name "Business_Profile"
  
  # List all profiles
  oblivion_importer.py --software multilogin --list
  
  # Import with fingerprint config
  oblivion_importer.py --software multilogin --import /path/to/profile --fingerprint-config fingerprint.json
        """
    )
    
    parser.add_argument("--software", default="camoufox",
                       choices=["camoufox", "multilogin", "dolphin", "indigo"],
                       help="Target anti-detect software (default: camoufox)")
    parser.add_argument("--import", dest="import_path",
                       help="Path to forged profile to import")
    parser.add_argument("--name",
                       help="Profile name (default: auto-generated)")
    parser.add_argument("--list", action="store_true",
                       help="List all imported profiles")
    parser.add_argument("--fingerprint-config",
                       help="JSON file with fingerprint configuration")
    parser.add_argument("--output",
                       help="Output validation results to file")
    
    args = parser.parse_args()
    
    # Initialize importer
    importer = OblivionImporter(args.software)
    
    if args.list:
        profiles = importer.list_profiles()
        print(f"\\n[+] Found {len(profiles)} profiles in {args.software}:")
        for profile in profiles:
            print(f"    • {profile['name']}")
            print(f"      Imported: {profile.get('imported', 'unknown')}")
            print(f"      Cookies: {profile.get('cookies', 0)}")
            print(f"      Engine: {profile.get('engine', 'unknown')}")
            print()
    
    elif args.import_path:
        # Load fingerprint config if provided
        fingerprint_config = None
        if args.fingerprint_config:
            try:
                with open(args.fingerprint_config, 'r') as f:
                    fingerprint_config = json.load(f)
            except Exception as e:
                print(f"[!] Failed to load fingerprint config: {e}")
        
        # Import profile
        success = importer.import_profile(
            source_path=args.import_path,
            profile_name=args.name,
            fingerprint_config=fingerprint_config
        )
        
        if success and args.output:
            # Get validation results
            profile_dir = importer.profiles_path / (args.name or f"oblivion_forged_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            validation = importer.validate_import(profile_dir)
            
            with open(args.output, 'w') as f:
                json.dump(validation, f, indent=2)
            print(f"[+] Validation results saved to {args.output}")
    
    else:
        print("[!] Either --import or --list is required")
        parser.print_help()

if __name__ == "__main__":
    main()
