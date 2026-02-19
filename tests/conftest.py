"""
Lucid Titan Test Environment - Shared Fixtures & Configuration

Provides pytest fixtures for all Titan subsystems:
- TitanController, GenesisEngine, TemporalDisplacement, BrowserProfile
- ProfileIsolator, CgroupManager
- Profgen config utilities
- Mock data generators
"""

import os
import sys
import json
import shutil
import tempfile
import pytest
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

# Add project root and titan module to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "titan"))
sys.path.insert(0, str(PROJECT_ROOT / "profgen"))
# Also add ISO core modules so tests can cover deployed code paths
ISO_CORE = PROJECT_ROOT / "iso" / "config" / "includes.chroot" / "opt" / "titan"
if ISO_CORE.exists():
    sys.path.insert(0, str(ISO_CORE))
    sys.path.insert(0, str(ISO_CORE / "core"))

from titan.titan_core import (
    TitanController,
    GenesisEngine,
    TemporalDisplacement,
    BrowserProfile,
    Persona,
    ProfilePhase,
)


# ---------------------------------------------------------------------------
# Temporary directory fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_titan_dir(tmp_path):
    """Provide a clean temporary directory for Titan operations."""
    titan_dir = tmp_path / ".titan"
    titan_dir.mkdir()
    (titan_dir / "profiles").mkdir()
    return titan_dir


@pytest.fixture
def tmp_profiles_dir(tmp_titan_dir):
    """Provide a clean temporary profiles directory."""
    return tmp_titan_dir / "profiles"


# ---------------------------------------------------------------------------
# Core module fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def temporal():
    """Create a TemporalDisplacement instance."""
    return TemporalDisplacement()


@pytest.fixture
def genesis(tmp_profiles_dir):
    """Create a GenesisEngine with a temp profiles directory."""
    return GenesisEngine(tmp_profiles_dir)


@pytest.fixture
def titan_controller(tmp_titan_dir):
    """Create a TitanController with a temp base directory."""
    return TitanController(base_dir=tmp_titan_dir)


# ---------------------------------------------------------------------------
# BrowserProfile fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_profile():
    """Create a sample BrowserProfile for testing."""
    return BrowserProfile(
        profile_id="test_profile_001",
        uuid="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        persona=Persona.WINDOWS,
        created_at=datetime.now(),
        apparent_age_days=90,
        canvas_seed=123456789,
        webgl_seed=987654321,
        audio_seed=555555555,
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        stripe_mid="abc123def456",
        stripe_sid="sid_test_789012",
        adyen_rp_uid="rp-uid-test-001",
        trust_anchors=["google.com", "facebook.com", "amazon.com"],
        browsing_history=[
            {
                "url": "https://www.google.com/",
                "title": "Google",
                "visit_time": (datetime.now() - timedelta(days=80)).isoformat(),
                "visit_type": "typed",
                "phase": "inception",
            },
            {
                "url": "https://www.amazon.com/",
                "title": "Amazon",
                "visit_time": (datetime.now() - timedelta(days=40)).isoformat(),
                "visit_type": "link",
                "phase": "warming",
            },
        ],
        cookies=[
            {
                "host": ".google.com",
                "name": "_session_id",
                "value": "mock_cookie_value_001",
                "path": "/",
                "expiry": int((datetime.now() + timedelta(days=365)).timestamp()),
                "created": int((datetime.now() - timedelta(days=90)).timestamp()),
                "is_secure": True,
                "is_http_only": True,
            }
        ],
    )


@pytest.fixture
def sample_profile_linux():
    """Create a Linux persona BrowserProfile."""
    return BrowserProfile(
        profile_id="test_linux_001",
        uuid="linux-uuid-0001-0002-0003-000000000001",
        persona=Persona.LINUX,
        created_at=datetime.now(),
        apparent_age_days=60,
        user_agent=(
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        trust_anchors=["google.com", "github.com"],
        browsing_history=[],
        cookies=[],
    )


@pytest.fixture
def sample_profile_macos():
    """Create a macOS persona BrowserProfile."""
    return BrowserProfile(
        profile_id="test_macos_001",
        uuid="macos-uuid-0001-0002-0003-000000000001",
        persona=Persona.MACOS,
        created_at=datetime.now(),
        apparent_age_days=45,
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        trust_anchors=["google.com", "apple.com"],
        browsing_history=[],
        cookies=[],
    )


# ---------------------------------------------------------------------------
# Mock data fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_operation_input_text():
    """Sample operation input text for parsing tests."""
    return """
TARGET_SITE = eneba
PURCHASE_ITEM = Steam Gift Card $50
PURCHASE_AMOUNT_USD = $49.99

PERSONA_FIRST_NAME = John
PERSONA_LAST_NAME = Smith
PERSONA_EMAIL = john.smith@example.com
PERSONA_PHONE = +1-555-0123

BILLING_STREET = 123 Main Street
BILLING_CITY = New York
BILLING_STATE = NY
BILLING_ZIP = 10001
BILLING_COUNTRY = US

SHIPPING_STREET = 123 Main Street
SHIPPING_CITY = New York
SHIPPING_STATE = NY
SHIPPING_ZIP = 10001
SHIPPING_COUNTRY = US

CARD_NUMBER = 4111 1111 1111 1111
CARD_EXP_MONTH = 12
CARD_EXP_YEAR = 2027
CARD_CVV = 123
CARD_HOLDER_NAME = John Smith
CARD_NETWORK = VISA

PROFILE_ARCHETYPE = gamer
HARDWARE_PROFILE = gaming_desktop
PROXY_REGION = us-ny-newyork
"""


@pytest.fixture
def mock_config_json():
    """Sample Titan config.json content."""
    return {
        "persona": "WINDOWS",
        "last_updated": datetime.now().isoformat(),
    }


@pytest.fixture
def saved_profile_on_disk(genesis, sample_profile):
    """Create and save a profile to disk, return the profile."""
    genesis._save_profile(sample_profile)
    return sample_profile


# ---------------------------------------------------------------------------
# Profgen fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def profgen_config():
    """Import and return profgen config module values."""
    try:
        from config import (
            PROFILE_UUID, PERSONA_NAME, PERSONA_EMAIL,
            TRUST_DOMAINS, COMMERCE_DOMAINS, ALL_DOMAINS,
            AGE_DAYS, CANVAS_SEED, AUDIO_SEED, WEBGL_SEED,
            SUBPAGES, PHASES,
        )
        return {
            "profile_uuid": PROFILE_UUID,
            "persona_name": PERSONA_NAME,
            "persona_email": PERSONA_EMAIL,
            "trust_domains": TRUST_DOMAINS,
            "commerce_domains": COMMERCE_DOMAINS,
            "all_domains": ALL_DOMAINS,
            "age_days": AGE_DAYS,
            "canvas_seed": CANVAS_SEED,
            "audio_seed": AUDIO_SEED,
            "webgl_seed": WEBGL_SEED,
            "subpages": SUBPAGES,
            "phases": PHASES,
        }
    except ImportError:
        pytest.skip("profgen.config not available")


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

class TitanTestHelpers:
    """Utility methods for Titan tests."""

    @staticmethod
    def create_profile_state(profile_dir: Path, profile_data: dict,
                             history: list = None, cookies: list = None):
        """Write a .parentlock.state file to a directory (replaces profile.json/history.json/cookies.json)."""
        profile_dir.mkdir(parents=True, exist_ok=True)
        state = {
            "meta": profile_data,
            "history": history or [],
            "cookies": cookies or [],
        }
        with open(profile_dir / ".parentlock.state", "w") as f:
            json.dump(state, f)

    @staticmethod
    def assert_valid_profile_dict(profile_dict: dict):
        """Assert that a profile dict has all required keys."""
        required_keys = [
            "profile_id", "uuid", "persona", "created_at",
            "apparent_age_days", "canvas_seed", "webgl_seed",
            "audio_seed", "user_agent", "stripe_mid", "stripe_sid",
            "adyen_rp_uid", "trust_anchors",
            "browsing_history_count", "cookies_count",
        ]
        for key in required_keys:
            assert key in profile_dict, f"Missing key: {key}"

    @staticmethod
    def assert_valid_history_entry(entry: dict):
        """Assert that a browsing history entry is well-formed."""
        required = ["url", "title", "visit_time", "visit_type", "phase"]
        for key in required:
            assert key in entry, f"Missing history key: {key}"
        assert entry["phase"] in ("inception", "warming", "kill_chain")

    @staticmethod
    def assert_valid_cookie_entry(entry: dict):
        """Assert that a cookie entry is well-formed."""
        required = ["host", "name", "value", "path", "expiry", "created",
                     "is_secure", "is_http_only"]
        for key in required:
            assert key in entry, f"Missing cookie key: {key}"


@pytest.fixture
def helpers():
    """Provide TitanTestHelpers instance."""
    return TitanTestHelpers()
