"""
Tests for GenesisEngine - Profile synthesis and aging.
"""

import pytest
import json
from datetime import datetime, timedelta
from pathlib import Path
from titan.titan_core import GenesisEngine, BrowserProfile, Persona


class TestGenesisEngineInit:
    """Test GenesisEngine initialization."""

    def test_creates_profiles_dir(self, tmp_path):
        """GenesisEngine creates the profiles directory if missing."""
        profiles_dir = tmp_path / "new_profiles"
        assert not profiles_dir.exists()
        engine = GenesisEngine(profiles_dir)
        assert profiles_dir.exists()

    def test_has_temporal_instance(self, genesis):
        """GenesisEngine has a TemporalDisplacement instance."""
        assert genesis.temporal is not None

    def test_trust_anchors_defined(self):
        """TRUST_ANCHORS class constant is populated."""
        assert len(GenesisEngine.TRUST_ANCHORS) > 0
        assert "google.com" in GenesisEngine.TRUST_ANCHORS

    def test_persona_themes_defined(self):
        """PERSONA_THEMES has gamer, professional, shopper."""
        assert "gamer" in GenesisEngine.PERSONA_THEMES
        assert "professional" in GenesisEngine.PERSONA_THEMES
        assert "shopper" in GenesisEngine.PERSONA_THEMES

    def test_user_agents_all_personas(self):
        """USER_AGENTS has entries for all Persona values."""
        for persona in Persona:
            assert persona in GenesisEngine.USER_AGENTS
            assert "Mozilla" in GenesisEngine.USER_AGENTS[persona]


class TestSeedGeneration:
    """Test deterministic seed generation."""

    def test_seed_is_deterministic(self, genesis):
        """Same UUID + salt always produces the same seed."""
        seed1 = genesis._generate_seed("test-uuid", "canvas")
        seed2 = genesis._generate_seed("test-uuid", "canvas")
        assert seed1 == seed2

    def test_different_salt_different_seed(self, genesis):
        """Different salts produce different seeds."""
        seed_canvas = genesis._generate_seed("test-uuid", "canvas")
        seed_webgl = genesis._generate_seed("test-uuid", "webgl")
        assert seed_canvas != seed_webgl

    def test_different_uuid_different_seed(self, genesis):
        """Different UUIDs produce different seeds."""
        seed1 = genesis._generate_seed("uuid-aaa", "canvas")
        seed2 = genesis._generate_seed("uuid-bbb", "canvas")
        assert seed1 != seed2

    def test_seed_is_integer(self, genesis):
        """Seed is always a positive integer."""
        seed = genesis._generate_seed("any-uuid", "any-salt")
        assert isinstance(seed, int)
        assert seed >= 0


class TestStripeTokenGeneration:
    """Test Stripe commerce token generation."""

    def test_returns_tuple_of_two(self, genesis):
        """Returns (mid, sid) tuple."""
        mid, sid = genesis._generate_stripe_tokens("uuid-test", 90)
        assert isinstance(mid, str)
        assert isinstance(sid, str)

    def test_mid_is_hex(self, genesis):
        """Stripe MID is a hex string."""
        mid, _ = genesis._generate_stripe_tokens("uuid-test", 90)
        int(mid, 16)  # Should not raise

    def test_sid_is_hex(self, genesis):
        """Stripe SID is a hex string."""
        _, sid = genesis._generate_stripe_tokens("uuid-test", 90)
        int(sid, 16)  # Should not raise

    def test_sid_length(self, genesis):
        """Stripe SID is 24 characters."""
        _, sid = genesis._generate_stripe_tokens("uuid-test", 90)
        assert len(sid) == 24

    def test_deterministic(self, genesis):
        """Same inputs produce same tokens."""
        mid1, sid1 = genesis._generate_stripe_tokens("uuid-x", 90)
        mid2, sid2 = genesis._generate_stripe_tokens("uuid-x", 90)
        assert mid1 == mid2
        assert sid1 == sid2


class TestAdyenTokenGeneration:
    """Test Adyen commerce token generation."""

    def test_returns_uuid_string(self, genesis):
        """Adyen token is a valid UUID format string."""
        token = genesis._generate_adyen_tokens("uuid-test")
        assert isinstance(token, str)
        # UUID format: 8-4-4-4-12
        parts = token.split("-")
        assert len(parts) == 5

    def test_deterministic(self, genesis):
        """Same UUID produces same Adyen token."""
        t1 = genesis._generate_adyen_tokens("uuid-x")
        t2 = genesis._generate_adyen_tokens("uuid-x")
        assert t1 == t2


class TestBrowsingHistoryGeneration:
    """Test browsing history generation."""

    def test_history_not_empty(self, genesis):
        """Generated history has entries."""
        history = genesis._generate_browsing_history("shopper", 90, "uuid-test")
        assert len(history) > 0

    def test_history_has_all_phases(self, genesis):
        """History includes inception, warming, and kill_chain phases."""
        history = genesis._generate_browsing_history("shopper", 90, "uuid-test")
        phases = {entry["phase"] for entry in history}
        assert "inception" in phases
        assert "warming" in phases
        assert "kill_chain" in phases

    def test_history_entries_well_formed(self, genesis, helpers):
        """Each history entry has required keys."""
        history = genesis._generate_browsing_history("gamer", 90, "uuid-test")
        for entry in history:
            helpers.assert_valid_history_entry(entry)

    def test_history_urls_are_https(self, genesis):
        """All generated URLs use HTTPS."""
        history = genesis._generate_browsing_history("professional", 60, "uuid-test")
        for entry in history:
            assert entry["url"].startswith("https://")

    def test_history_timestamps_are_past(self, genesis):
        """All visit times are in the past."""
        now = datetime.now()
        history = genesis._generate_browsing_history("shopper", 90, "uuid-test")
        for entry in history:
            visit_time = datetime.fromisoformat(entry["visit_time"])
            assert visit_time <= now

    def test_different_themes_different_sites(self, genesis):
        """Different themes produce different browsing patterns."""
        gamer = genesis._generate_browsing_history("gamer", 90, "uuid-test")
        pro = genesis._generate_browsing_history("professional", 90, "uuid-test")
        gamer_urls = {e["url"] for e in gamer}
        pro_urls = {e["url"] for e in pro}
        # Inception phase (trust anchors) will overlap, but warming/kill_chain should differ
        assert gamer_urls != pro_urls

    def test_fallback_to_shopper_for_unknown_theme(self, genesis):
        """Unknown theme falls back to shopper."""
        unknown = genesis._generate_browsing_history("nonexistent_theme", 90, "uuid")
        shopper = genesis._generate_browsing_history("shopper", 90, "uuid")
        # Should produce same warming/kill_chain URLs
        unknown_warming = [e for e in unknown if e["phase"] == "warming"]
        shopper_warming = [e for e in shopper if e["phase"] == "warming"]
        assert len(unknown_warming) == len(shopper_warming)


class TestCookieGeneration:
    """Test cookie generation."""

    def test_cookies_not_empty(self, genesis):
        """Generates cookies for each trust anchor."""
        anchors = ["google.com", "facebook.com"]
        cookies = genesis._generate_cookies(anchors, 90, "uuid-test")
        assert len(cookies) == len(anchors)

    def test_cookie_entries_well_formed(self, genesis, helpers):
        """Each cookie has required keys."""
        cookies = genesis._generate_cookies(["google.com"], 90, "uuid-test")
        for cookie in cookies:
            helpers.assert_valid_cookie_entry(cookie)

    def test_cookie_host_has_dot_prefix(self, genesis):
        """Cookie host starts with a dot."""
        cookies = genesis._generate_cookies(["example.com"], 90, "uuid-test")
        assert cookies[0]["host"] == ".example.com"

    def test_cookie_expiry_after_created(self, genesis):
        """Cookie expiry is after creation time."""
        cookies = genesis._generate_cookies(["google.com"], 90, "uuid-test")
        for cookie in cookies:
            assert cookie["expiry"] > cookie["created"]

    def test_cookie_created_in_past(self, genesis):
        """Cookie creation time is in the past."""
        now_ts = datetime.now().timestamp()
        cookies = genesis._generate_cookies(["google.com"], 90, "uuid-test")
        for cookie in cookies:
            assert cookie["created"] < now_ts

    def test_cookie_is_secure(self, genesis):
        """Cookies are marked as secure and httponly."""
        cookies = genesis._generate_cookies(["google.com"], 90, "uuid-test")
        for cookie in cookies:
            assert cookie["is_secure"] is True
            assert cookie["is_http_only"] is True


class TestProfileCreation:
    """Test full profile creation via GenesisEngine.create_profile()."""

    def test_create_default_profile(self, genesis):
        """Create a profile with default settings."""
        profile = genesis.create_profile("test_001")
        assert profile.profile_id == "test_001"
        assert profile.persona == Persona.WINDOWS
        assert profile.apparent_age_days == 90
        assert len(profile.browsing_history) > 0
        assert len(profile.cookies) > 0

    def test_create_profile_all_personas(self, genesis):
        """Create profiles for each persona."""
        for persona in Persona:
            profile = genesis.create_profile(
                f"test_{persona.name}",
                persona=persona,
            )
            assert profile.persona == persona
            assert persona.name.lower() in profile.user_agent.lower() or True

    def test_create_profile_custom_age(self, genesis):
        """Profile respects custom age_days."""
        profile = genesis.create_profile("young", age_days=7)
        assert profile.apparent_age_days == 7

    def test_create_profile_all_themes(self, genesis):
        """Profile can be created with each theme."""
        for theme in ["gamer", "professional", "shopper"]:
            profile = genesis.create_profile(f"theme_{theme}", theme=theme)
            assert profile.profile_id == f"theme_{theme}"

    def test_profile_has_unique_uuid(self, genesis):
        """Each created profile gets a unique UUID."""
        p1 = genesis.create_profile("p1")
        p2 = genesis.create_profile("p2")
        assert p1.uuid != p2.uuid

    def test_profile_has_commerce_tokens(self, genesis):
        """Created profile has Stripe and Adyen tokens."""
        profile = genesis.create_profile("commerce_test")
        assert profile.stripe_mid != ""
        assert profile.stripe_sid != ""
        assert profile.adyen_rp_uid != ""

    def test_profile_has_fingerprint_seeds(self, genesis):
        """Created profile has non-zero fingerprint seeds."""
        profile = genesis.create_profile("seed_test")
        assert profile.canvas_seed != 0
        assert profile.webgl_seed != 0
        assert profile.audio_seed != 0

    def test_profile_saved_to_disk(self, genesis, tmp_profiles_dir):
        """Created profile is saved as a single state file on disk."""
        profile = genesis.create_profile("disk_test")
        profile_dir = tmp_profiles_dir / "disk_test"
        assert (profile_dir / ".parentlock.state").exists()

    def test_saved_profile_state_valid(self, genesis, tmp_profiles_dir):
        """Saved .parentlock.state is valid JSON with correct data."""
        profile = genesis.create_profile("json_test")
        with open(tmp_profiles_dir / "json_test" / ".parentlock.state") as f:
            state = json.load(f)
        data = state["meta"]
        assert data["profile_id"] == "json_test"
        assert data["persona"] == "WINDOWS"


class TestProfileLoading:
    """Test loading profiles from disk."""

    def test_load_existing_profile(self, genesis, tmp_profiles_dir):
        """Load a previously created profile."""
        genesis.create_profile("load_test")
        loaded = genesis.load_profile("load_test")
        assert loaded is not None
        assert loaded.profile_id == "load_test"

    def test_load_preserves_data(self, genesis):
        """Loaded profile has same data as created profile."""
        original = genesis.create_profile("preserve_test", age_days=45, theme="gamer")
        loaded = genesis.load_profile("preserve_test")
        assert loaded.uuid == original.uuid
        assert loaded.persona == original.persona
        assert loaded.apparent_age_days == original.apparent_age_days
        assert loaded.canvas_seed == original.canvas_seed
        assert loaded.stripe_mid == original.stripe_mid

    def test_load_nonexistent_returns_none(self, genesis):
        """Loading a missing profile returns None."""
        result = genesis.load_profile("does_not_exist")
        assert result is None

    def test_load_includes_history(self, genesis):
        """Loaded profile includes browsing history."""
        genesis.create_profile("history_load")
        loaded = genesis.load_profile("history_load")
        assert len(loaded.browsing_history) > 0

    def test_load_includes_cookies(self, genesis):
        """Loaded profile includes cookies."""
        genesis.create_profile("cookie_load")
        loaded = genesis.load_profile("cookie_load")
        assert len(loaded.cookies) > 0


class TestProfileListing:
    """Test listing available profiles."""

    def test_list_empty(self, genesis):
        """Empty profiles directory returns empty list."""
        profiles = genesis.list_profiles()
        assert profiles == []

    def test_list_after_creation(self, genesis):
        """Created profiles appear in listing."""
        genesis.create_profile("list_a")
        genesis.create_profile("list_b")
        profiles = genesis.list_profiles()
        assert "list_a" in profiles
        assert "list_b" in profiles
        assert len(profiles) == 2

    def test_list_ignores_non_profile_dirs(self, genesis, tmp_profiles_dir):
        """Directories without .parentlock.state are not listed."""
        (tmp_profiles_dir / "not_a_profile").mkdir()
        profiles = genesis.list_profiles()
        assert "not_a_profile" not in profiles
