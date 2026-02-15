"""
Tests for BrowserProfile dataclass and serialization.
"""

import pytest
from datetime import datetime, timedelta
from titan.titan_core import BrowserProfile, Persona


class TestBrowserProfileCreation:
    """Test BrowserProfile instantiation and defaults."""

    def test_create_minimal_profile(self):
        """Profile can be created with only required fields."""
        profile = BrowserProfile(
            profile_id="min_001",
            uuid="uuid-min-001",
            persona=Persona.WINDOWS,
            created_at=datetime.now(),
            apparent_age_days=30,
        )
        assert profile.profile_id == "min_001"
        assert profile.persona == Persona.WINDOWS
        assert profile.apparent_age_days == 30
        assert profile.canvas_seed == 0
        assert profile.webgl_seed == 0
        assert profile.audio_seed == 0
        assert profile.user_agent == ""
        assert profile.trust_anchors == []
        assert profile.browsing_history == []
        assert profile.cookies == []

    def test_create_full_profile(self, sample_profile):
        """Profile with all fields populated."""
        assert sample_profile.profile_id == "test_profile_001"
        assert sample_profile.persona == Persona.WINDOWS
        assert sample_profile.apparent_age_days == 90
        assert sample_profile.canvas_seed == 123456789
        assert len(sample_profile.trust_anchors) == 3
        assert len(sample_profile.browsing_history) == 2
        assert len(sample_profile.cookies) == 1

    def test_all_personas(self):
        """Profile can be created for each persona type."""
        for persona in Persona:
            profile = BrowserProfile(
                profile_id=f"persona_{persona.name}",
                uuid=f"uuid-{persona.name}",
                persona=persona,
                created_at=datetime.now(),
                apparent_age_days=60,
            )
            assert profile.persona == persona

    def test_zero_age_profile(self):
        """Profile with zero apparent age is valid."""
        profile = BrowserProfile(
            profile_id="zero_age",
            uuid="uuid-zero",
            persona=Persona.LINUX,
            created_at=datetime.now(),
            apparent_age_days=0,
        )
        assert profile.apparent_age_days == 0

    def test_large_age_profile(self):
        """Profile with very large apparent age is valid."""
        profile = BrowserProfile(
            profile_id="old_profile",
            uuid="uuid-old",
            persona=Persona.MACOS,
            created_at=datetime.now(),
            apparent_age_days=365,
        )
        assert profile.apparent_age_days == 365


class TestBrowserProfileSerialization:
    """Test BrowserProfile.to_dict() serialization."""

    def test_to_dict_has_all_keys(self, sample_profile, helpers):
        """to_dict() returns all required keys."""
        d = sample_profile.to_dict()
        helpers.assert_valid_profile_dict(d)

    def test_to_dict_persona_is_string(self, sample_profile):
        """Persona is serialized as its name string."""
        d = sample_profile.to_dict()
        assert d["persona"] == "WINDOWS"
        assert isinstance(d["persona"], str)

    def test_to_dict_created_at_is_iso(self, sample_profile):
        """created_at is serialized as ISO format string."""
        d = sample_profile.to_dict()
        # Should be parseable back
        parsed = datetime.fromisoformat(d["created_at"])
        assert isinstance(parsed, datetime)

    def test_to_dict_counts_not_full_data(self, sample_profile):
        """to_dict() includes counts, not full history/cookies arrays."""
        d = sample_profile.to_dict()
        assert "browsing_history_count" in d
        assert "cookies_count" in d
        assert "browsing_history" not in d
        assert "cookies" not in d
        assert d["browsing_history_count"] == 2
        assert d["cookies_count"] == 1

    def test_to_dict_seeds_are_integers(self, sample_profile):
        """Fingerprint seeds remain as integers in serialized form."""
        d = sample_profile.to_dict()
        assert isinstance(d["canvas_seed"], int)
        assert isinstance(d["webgl_seed"], int)
        assert isinstance(d["audio_seed"], int)

    def test_to_dict_trust_anchors_is_list(self, sample_profile):
        """Trust anchors serialized as a list of strings."""
        d = sample_profile.to_dict()
        assert isinstance(d["trust_anchors"], list)
        for anchor in d["trust_anchors"]:
            assert isinstance(anchor, str)

    def test_to_dict_linux_persona(self, sample_profile_linux):
        """Linux profile serializes correctly."""
        d = sample_profile_linux.to_dict()
        assert d["persona"] == "LINUX"
        assert d["browsing_history_count"] == 0

    def test_to_dict_macos_persona(self, sample_profile_macos):
        """macOS profile serializes correctly."""
        d = sample_profile_macos.to_dict()
        assert d["persona"] == "MACOS"
