#!/usr/bin/env python3
"""
TITAN V7.0 SINGULARITY - Core Controller

This is the central orchestration module for the TITAN architecture.
It integrates all sub-systems:
- Network Shield (eBPF/XDP packet manipulation)
- Temporal Displacement (libfaketime integration)
- Profile Manager (browser profile isolation)
- Genesis Engine (identity synthesis and aging)

Source: Unified Agent [cite: 1, 15]

Usage:
    from titan_core import TitanController
    
    titan = TitanController()
    titan.initialize()
    titan.set_persona("windows")
    titan.create_profile("merchant_profile_01")
"""

import os
import sys
import json
import hashlib
import uuid
import logging
import subprocess
import sqlite3
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum, IntEnum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [TITAN] %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


class Persona(IntEnum):
    """Operating system personas for identity synthesis."""
    LINUX = 0
    WINDOWS = 1
    MACOS = 2


class ProfilePhase(Enum):
    """Genesis Engine profile aging phases."""
    INCEPTION = "inception"      # T-90 to T-60 days
    WARMING = "warming"          # T-60 to T-30 days
    KILL_CHAIN = "kill_chain"    # T-30 to T-0 days


@dataclass
class BrowserProfile:
    """
    Represents a synthesized browser identity profile.
    
    Contains all the data needed to create a consistent, aged
    digital identity that passes modern anti-fraud checks.
    
    Source: [cite: 1, 7]
    """
    profile_id: str
    uuid: str
    persona: Persona
    created_at: datetime
    apparent_age_days: int
    
    # Browser fingerprint seeds (for consistent noise generation)
    canvas_seed: int = 0
    webgl_seed: int = 0
    audio_seed: int = 0
    
    # Network signature
    user_agent: str = ""
    
    # Commerce tokens
    stripe_mid: str = ""
    stripe_sid: str = ""
    adyen_rp_uid: str = ""
    
    # Metadata
    trust_anchors: List[str] = field(default_factory=list)
    browsing_history: List[Dict] = field(default_factory=list)
    cookies: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize the profile to a dictionary."""
        return {
            "profile_id": self.profile_id,
            "uuid": self.uuid,
            "persona": self.persona.name,
            "created_at": self.created_at.isoformat(),
            "apparent_age_days": self.apparent_age_days,
            "canvas_seed": self.canvas_seed,
            "webgl_seed": self.webgl_seed,
            "audio_seed": self.audio_seed,
            "user_agent": self.user_agent,
            "stripe_mid": self.stripe_mid,
            "stripe_sid": self.stripe_sid,
            "adyen_rp_uid": self.adyen_rp_uid,
            "trust_anchors": self.trust_anchors,
            "browsing_history_count": len(self.browsing_history),
            "cookies_count": len(self.cookies),
        }


class TemporalDisplacement:
    """
    Manages system-wide time manipulation via libfaketime.
    
    This module provides the ability to "backdate" all system calls
    related to time, creating the illusion that the profile was
    created in the past.
    
    Source: [cite: 1]
    """
    
    LIBFAKETIME_PATH = "/usr/lib/x86_64-linux-gnu/faketime/libfaketime.so.1"
    
    def __init__(self):
        self.is_active = False
        self.offset_days = 0
        self._original_env = {}
    
    def is_available(self) -> bool:
        """Check if libfaketime is installed."""
        return Path(self.LIBFAKETIME_PATH).exists()
    
    def activate(self, offset_days: int) -> Dict[str, str]:
        """
        Get environment variables for time displacement.
        
        Args:
            offset_days: Number of days to shift time backwards
            
        Returns:
            Dictionary of environment variables to set
        """
        if not self.is_available():
            logger.warning("libfaketime not available, time displacement disabled")
            return {}
        
        # Calculate the fake date
        fake_date = datetime.now() - timedelta(days=offset_days)
        fake_time_str = fake_date.strftime("@%Y-%m-%d %H:%M:%S")
        
        env_vars = {
            "LD_PRELOAD": self.LIBFAKETIME_PATH,
            "FAKETIME": fake_time_str,
            "FAKETIME_NO_CACHE": "1",
        }
        
        self.is_active = True
        self.offset_days = offset_days
        
        logger.info(f"Temporal displacement activated: -{offset_days} days")
        logger.info(f"Apparent time: {fake_date.isoformat()}")
        
        return env_vars
    
    def deactivate(self) -> None:
        """Disable time displacement."""
        self.is_active = False
        self.offset_days = 0
        logger.info("Temporal displacement deactivated")
    
    def get_apparent_time(self) -> datetime:
        """Get the current apparent (fake) time."""
        return datetime.now() - timedelta(days=self.offset_days)


class GenesisEngine:
    """
    Profile synthesis and aging engine.
    
    Automates the creation of "digital provenance" by generating
    backdated browser profiles with realistic browsing history,
    cookies, and commerce tokens.
    
    Source: [cite: 1, 7]
    """
    
    # Trust anchor domains for the inception phase
    TRUST_ANCHORS = [
        "google.com",
        "facebook.com",
        "microsoft.com",
        "amazon.com",
        "apple.com",
        "github.com",
        "linkedin.com",
        "twitter.com",
    ]
    
    # Persona-specific browsing themes
    PERSONA_THEMES = {
        "gamer": [
            "store.steampowered.com",
            "twitch.tv",
            "discord.com",
            "reddit.com/r/gaming",
            "nvidia.com",
            "epicgames.com",
        ],
        "professional": [
            "linkedin.com",
            "slack.com",
            "notion.so",
            "zoom.us",
            "github.com",
            "medium.com",
        ],
        "shopper": [
            "amazon.com",
            "ebay.com",
            "etsy.com",
            "walmart.com",
            "target.com",
            "bestbuy.com",
        ],
    }
    
    # User agent strings by persona
    USER_AGENTS = {
        Persona.WINDOWS: (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        Persona.MACOS: (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        Persona.LINUX: (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
    }
    
    def __init__(self, profiles_dir: Path):
        self.profiles_dir = profiles_dir
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self.temporal = TemporalDisplacement()
    
    def _generate_seed(self, profile_uuid: str, salt: str) -> int:
        """Generate a deterministic seed from profile UUID."""
        hash_input = f"{profile_uuid}:{salt}"
        hash_bytes = hashlib.sha256(hash_input.encode()).digest()
        return int.from_bytes(hash_bytes[:8], byteorder='big')
    
    def _generate_stripe_tokens(self, profile_uuid: str, age_days: int) -> tuple:
        """
        Generate Stripe commerce tokens.
        
        Source: [cite: 1, 8]
        """
        # Generate deterministic machine ID (backdated)
        mid_seed = self._generate_seed(profile_uuid, "stripe_mid")
        mid = hashlib.md5(str(mid_seed).encode()).hexdigest()
        
        # Generate session ID
        sid_seed = self._generate_seed(profile_uuid, "stripe_sid")
        sid = hashlib.md5(str(sid_seed).encode()).hexdigest()[:24]
        
        return mid, sid
    
    def _generate_adyen_tokens(self, profile_uuid: str) -> str:
        """
        Generate Adyen commerce tokens.
        
        Source: [cite: 1, 8]
        """
        rp_seed = self._generate_seed(profile_uuid, "adyen_rp_uid")
        return str(uuid.UUID(int=rp_seed % (2**128)))
    
    def _generate_browsing_history(
        self, 
        theme: str, 
        age_days: int,
        profile_uuid: str
    ) -> List[Dict]:
        """
        Generate realistic browsing history entries.
        
        Follows the three-phase aging model:
        - Phase 1 (Inception): Trust anchors
        - Phase 2 (Warming): Theme-specific browsing
        - Phase 3 (Kill Chain): Target merchant visits
        
        Source: [cite: 1, 7]
        """
        history = []
        base_time = datetime.now() - timedelta(days=age_days)
        
        # Phase 1: Inception (T-90 to T-60)
        for i, anchor in enumerate(self.TRUST_ANCHORS):
            visit_time = base_time + timedelta(days=i * 3, hours=i * 2)
            history.append({
                "url": f"https://www.{anchor}/",
                "title": anchor.split('.')[0].title(),
                "visit_time": visit_time.isoformat(),
                "visit_type": "typed",
                "phase": "inception",
            })
        
        # Phase 2: Warming (T-60 to T-30)
        theme_sites = self.PERSONA_THEMES.get(theme, self.PERSONA_THEMES["shopper"])
        for i, site in enumerate(theme_sites):
            visit_time = base_time + timedelta(days=30 + i * 5, hours=i * 3)
            history.append({
                "url": f"https://{site}/",
                "title": site.split('/')[0].replace('.', ' ').title(),
                "visit_time": visit_time.isoformat(),
                "visit_type": "link",
                "phase": "warming",
            })
        
        # Phase 3: Kill Chain (T-30 to T-0)
        # Add more frequent visits in the final phase
        for i in range(10):
            visit_time = base_time + timedelta(days=60 + i * 3, hours=i)
            history.append({
                "url": f"https://www.{theme_sites[i % len(theme_sites)]}/browse",
                "title": f"Browsing - {theme_sites[i % len(theme_sites)]}",
                "visit_time": visit_time.isoformat(),
                "visit_type": "link",
                "phase": "kill_chain",
            })
        
        return history
    
    def _generate_cookies(
        self, 
        trust_anchors: List[str],
        age_days: int,
        profile_uuid: str
    ) -> List[Dict]:
        """
        Generate backdated cookie entries.
        
        Source: [cite: 1, 7]
        """
        cookies = []
        base_time = datetime.now() - timedelta(days=age_days)
        
        for i, anchor in enumerate(trust_anchors):
            cookie_time = base_time + timedelta(days=i * 2)
            expiry_time = cookie_time + timedelta(days=365)
            
            # Generate cookie value from profile seed
            cookie_seed = self._generate_seed(profile_uuid, f"cookie_{anchor}")
            cookie_value = hashlib.md5(str(cookie_seed).encode()).hexdigest()
            
            cookies.append({
                "host": f".{anchor}",
                "name": "_session_id",
                "value": cookie_value,
                "path": "/",
                "expiry": int(expiry_time.timestamp()),
                "created": int(cookie_time.timestamp()),
                "is_secure": True,
                "is_http_only": True,
            })
        
        return cookies
    
    def create_profile(
        self,
        profile_id: str,
        persona: Persona = Persona.WINDOWS,
        age_days: int = 90,
        theme: str = "shopper"
    ) -> BrowserProfile:
        """
        Create a new synthesized browser profile.
        
        Args:
            profile_id: Unique identifier for the profile
            persona: Target OS persona
            age_days: Apparent age of the profile in days
            theme: Browsing theme for history generation
            
        Returns:
            BrowserProfile object with all synthesized data
        """
        logger.info(f"Creating profile: {profile_id}")
        logger.info(f"  Persona: {persona.name}")
        logger.info(f"  Apparent age: {age_days} days")
        logger.info(f"  Theme: {theme}")
        
        # Generate master UUID
        profile_uuid = str(uuid.uuid4())
        
        # Generate deterministic seeds for fingerprint consistency
        canvas_seed = self._generate_seed(profile_uuid, "canvas")
        webgl_seed = self._generate_seed(profile_uuid, "webgl")
        audio_seed = self._generate_seed(profile_uuid, "audio")
        
        # Generate commerce tokens
        stripe_mid, stripe_sid = self._generate_stripe_tokens(profile_uuid, age_days)
        adyen_rp_uid = self._generate_adyen_tokens(profile_uuid)
        
        # Generate browsing history
        history = self._generate_browsing_history(theme, age_days, profile_uuid)
        
        # Generate cookies
        cookies = self._generate_cookies(self.TRUST_ANCHORS, age_days, profile_uuid)
        
        # Create profile object
        profile = BrowserProfile(
            profile_id=profile_id,
            uuid=profile_uuid,
            persona=persona,
            created_at=datetime.now(),
            apparent_age_days=age_days,
            canvas_seed=canvas_seed,
            webgl_seed=webgl_seed,
            audio_seed=audio_seed,
            user_agent=self.USER_AGENTS[persona],
            stripe_mid=stripe_mid,
            stripe_sid=stripe_sid,
            adyen_rp_uid=adyen_rp_uid,
            trust_anchors=self.TRUST_ANCHORS.copy(),
            browsing_history=history,
            cookies=cookies,
        )
        
        # Save profile to disk
        self._save_profile(profile)
        
        logger.info(f"Profile created successfully: {profile_id}")
        return profile
    
    def _save_profile(self, profile: BrowserProfile) -> None:
        """Save profile data to disk in a single opaque state file.
        Avoids creating forensic artifact files like profile.json, history.json, cookies.json."""
        profile_dir = self.profiles_dir / profile.profile_id
        profile_dir.mkdir(parents=True, exist_ok=True)
        
        # Store all data in a single state file with innocuous name
        state = {
            "meta": profile.to_dict(),
            "history": profile.browsing_history,
            "cookies": profile.cookies,
        }
        state_file = profile_dir / ".parentlock.state"
        with open(state_file, 'w') as f:
            json.dump(state, f)
        
        logger.debug(f"Profile saved to: {profile_dir}")

    def generate_firefox_profile(self, profile_id: str, skip_storage: bool = False) -> Path:
        """
        Generate a full forensically clean Firefox profile directory using
        the profgen pipeline. This bridges the development TitanController
        to the production-grade profgen generators.

        Args:
            profile_id: Unique identifier for the profile.
            skip_storage: If True, skip heavy localStorage generation.

        Returns:
            Path to the generated Firefox profile directory.
        """
        profile_dir = self.profiles_dir / profile_id / "firefox"
        profile_dir.mkdir(parents=True, exist_ok=True)

        try:
            from profgen import generate_profile
            stats = generate_profile(profile_dir, skip_storage=skip_storage)
            logger.info(f"Firefox profile generated: {profile_dir}")
            logger.info(f"  Stats: {stats}")
            return profile_dir
        except ImportError:
            logger.warning("profgen package not available — falling back to basic profile")
            return profile_dir
    
    def load_profile(self, profile_id: str) -> Optional[BrowserProfile]:
        """Load an existing profile from disk."""
        profile_dir = self.profiles_dir / profile_id
        state_file = profile_dir / ".parentlock.state"
        
        if not state_file.exists():
            logger.error(f"Profile not found: {profile_id}")
            return None
        
        with open(state_file, 'r') as f:
            state = json.load(f)
        
        data = state.get("meta", {})
        history = state.get("history", [])
        cookies = state.get("cookies", [])
        
        profile = BrowserProfile(
            profile_id=data["profile_id"],
            uuid=data["uuid"],
            persona=Persona[data["persona"]],
            created_at=datetime.fromisoformat(data["created_at"]),
            apparent_age_days=data["apparent_age_days"],
            canvas_seed=data["canvas_seed"],
            webgl_seed=data["webgl_seed"],
            audio_seed=data["audio_seed"],
            user_agent=data["user_agent"],
            stripe_mid=data["stripe_mid"],
            stripe_sid=data["stripe_sid"],
            adyen_rp_uid=data["adyen_rp_uid"],
            trust_anchors=data["trust_anchors"],
            browsing_history=history,
            cookies=cookies,
        )
        
        logger.info(f"Profile loaded: {profile_id}")
        return profile
    
    def list_profiles(self) -> List[str]:
        """List all available profiles."""
        profiles = []
        for item in self.profiles_dir.iterdir():
            if item.is_dir() and (item / ".parentlock.state").exists():
                profiles.append(item.name)
        return profiles


class TitanController:
    """
    Central controller for the TITAN architecture.
    
    Orchestrates all sub-systems and provides a unified interface
    for identity synthesis operations.
    
    Source: [cite: 1, 15]
    """
    
    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or Path.home() / ".titan"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        self.profiles_dir = self.base_dir / "profiles"
        self.config_file = self.base_dir / "config.json"
        
        # Initialize sub-systems
        self.genesis = GenesisEngine(self.profiles_dir)
        self.temporal = TemporalDisplacement()
        self.network_shield = None  # Lazy load
        
        self.current_persona = Persona.WINDOWS
        self.current_profile: Optional[BrowserProfile] = None
        self.is_initialized = False
        
        self._load_config()
        
        logger.info("TitanController initialized")
        logger.info(f"Base directory: {self.base_dir}")
    
    def _load_config(self) -> None:
        """Load configuration from disk."""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                self.current_persona = Persona[config.get("persona", "WINDOWS")]
    
    def _save_config(self) -> None:
        """Save configuration to disk."""
        config = {
            "persona": self.current_persona.name,
            "last_updated": datetime.now().isoformat(),
        }
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)
    
    def initialize(self, interface: str = "eth0") -> bool:
        """
        Initialize all TITAN sub-systems.
        
        Args:
            interface: Network interface for the eBPF shield
            
        Returns:
            True if initialization successful
        """
        logger.info("Initializing TITAN sub-systems...")
        
        # Check for libfaketime
        if self.temporal.is_available():
            logger.info("[OK] libfaketime available")
        else:
            logger.warning("[WARN] libfaketime not installed")
        
        # Initialize network shield (requires root)
        if os.geteuid() == 0:
            try:
                from titan.ebpf.network_shield_loader import NetworkShield
                self.network_shield = NetworkShield(interface=interface)
                logger.info("[OK] Network Shield initialized")
            except ImportError:
                logger.warning("[WARN] Network Shield module not available")
        else:
            logger.warning("[WARN] Network Shield requires root privileges")
        
        self.is_initialized = True
        logger.info("TITAN initialization complete")
        
        return True
    
    def set_persona(self, persona: str) -> Dict[str, Any]:
        """
        Switch the active OS persona.
        
        Args:
            persona: Target persona name ('linux', 'windows', 'macos')
            
        Returns:
            Dictionary with the current configuration
        """
        persona_map = {
            "linux": Persona.LINUX,
            "windows": Persona.WINDOWS,
            "macos": Persona.MACOS,
        }
        
        persona_lower = persona.lower()
        if persona_lower not in persona_map:
            raise ValueError(f"Unknown persona: {persona}")
        
        self.current_persona = persona_map[persona_lower]
        self._save_config()
        
        # Update network shield if loaded
        if self.network_shield and self.network_shield.is_loaded:
            self.network_shield.set_persona(persona)
        
        logger.info(f"Persona set to: {self.current_persona.name}")
        
        return {
            "persona": self.current_persona.name,
            "user_agent": GenesisEngine.USER_AGENTS[self.current_persona],
        }
    
    def create_profile(
        self,
        profile_id: str,
        age_days: int = 90,
        theme: str = "shopper"
    ) -> BrowserProfile:
        """
        Create a new synthesized identity profile.
        
        Args:
            profile_id: Unique identifier for the profile
            age_days: Apparent age in days
            theme: Browsing behavior theme
            
        Returns:
            The created BrowserProfile
        """
        profile = self.genesis.create_profile(
            profile_id=profile_id,
            persona=self.current_persona,
            age_days=age_days,
            theme=theme
        )
        
        self.current_profile = profile
        return profile
    
    def load_profile(self, profile_id: str) -> Optional[BrowserProfile]:
        """Load an existing profile."""
        profile = self.genesis.load_profile(profile_id)
        if profile:
            self.current_profile = profile
            self.current_persona = profile.persona
        return profile
    
    def list_profiles(self) -> List[str]:
        """List all available profiles."""
        return self.genesis.list_profiles()
    
    def get_browser_env(self) -> Dict[str, str]:
        """
        Get environment variables for launching a browser with the current profile.
        
        Returns:
            Dictionary of environment variables
        """
        env = os.environ.copy()
        
        # Add temporal displacement if profile has age
        if self.current_profile and self.current_profile.apparent_age_days > 0:
            temporal_env = self.temporal.activate(
                self.current_profile.apparent_age_days
            )
            env.update(temporal_env)
        
        # Add profile-specific variables using innocuous names
        if self.current_profile:
            env["MOZ_PROFILER_SESSION"] = self.current_profile.profile_id
            env["MOZ_GFX_SEED"] = str(self.current_profile.canvas_seed)
            env["MOZ_MEDIA_SEED"] = str(self.current_profile.audio_seed)
        
        return env
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of all TITAN sub-systems."""
        status = {
            "initialized": self.is_initialized,
            "persona": self.current_persona.name,
            "current_profile": None,
            "temporal_displacement": {
                "available": self.temporal.is_available(),
                "active": self.temporal.is_active,
                "offset_days": self.temporal.offset_days,
            },
            "network_shield": {
                "available": self.network_shield is not None,
                "loaded": False,
            },
            "profiles_count": len(self.list_profiles()),
        }
        
        if self.current_profile:
            status["current_profile"] = self.current_profile.to_dict()
        
        if self.network_shield:
            status["network_shield"]["loaded"] = self.network_shield.is_loaded
        
        return status
    
    def shutdown(self) -> None:
        """Gracefully shutdown all TITAN sub-systems."""
        logger.info("Shutting down TITAN...")
        
        if self.network_shield and self.network_shield.is_loaded:
            self.network_shield.unload()
        
        self.temporal.deactivate()
        self._save_config()
        
        logger.info("TITAN shutdown complete")


def main():
    """Command-line interface for TITAN."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="TITAN V7.0 SINGULARITY Controller"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Status command
    subparsers.add_parser("status", help="Show TITAN status")
    
    # Create profile command
    create_parser = subparsers.add_parser("create", help="Create a new profile")
    create_parser.add_argument("profile_id", help="Profile identifier")
    create_parser.add_argument(
        "-a", "--age", type=int, default=90,
        help="Apparent age in days"
    )
    create_parser.add_argument(
        "-t", "--theme",
        choices=["gamer", "professional", "shopper"],
        default="shopper",
        help="Browsing theme"
    )
    create_parser.add_argument(
        "-p", "--persona",
        choices=["windows", "macos", "linux"],
        default="windows",
        help="OS persona"
    )
    
    # List profiles command
    subparsers.add_parser("list", help="List all profiles")
    
    # Load profile command
    load_parser = subparsers.add_parser("load", help="Load a profile")
    load_parser.add_argument("profile_id", help="Profile identifier")
    
    args = parser.parse_args()
    
    titan = TitanController()
    
    if args.command == "status":
        status = titan.get_status()
        print(json.dumps(status, indent=2, default=str))
        
    elif args.command == "create":
        titan.set_persona(args.persona)
        profile = titan.create_profile(
            profile_id=args.profile_id,
            age_days=args.age,
            theme=args.theme
        )
        print(json.dumps(profile.to_dict(), indent=2))
        
    elif args.command == "list":
        profiles = titan.list_profiles()
        if profiles:
            print("Available profiles:")
            for p in profiles:
                print(f"  - {p}")
        else:
            print("No profiles found")
            
    elif args.command == "load":
        profile = titan.load_profile(args.profile_id)
        if profile:
            print(json.dumps(profile.to_dict(), indent=2))
        else:
            print(f"Profile not found: {args.profile_id}")
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
