"""
Tests for TitanController - Central orchestration module.
"""

import pytest
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock
from titan.titan_core import (
    TitanController, GenesisEngine, TemporalDisplacement,
    BrowserProfile, Persona, ProfilePhase,
)


class TestTitanControllerInit:
    """Test TitanController initialization."""

    def test_creates_base_dir(self, tmp_path):
        """Controller creates base directory if missing."""
        base = tmp_path / "new_titan"
        assert not base.exists()
        ctrl = TitanController(base_dir=base)
        assert base.exists()

    def test_creates_profiles_subdir(self, tmp_titan_dir):
        """Controller ensures profiles subdirectory exists."""
        ctrl = TitanController(base_dir=tmp_titan_dir)
        assert (tmp_titan_dir / "profiles").exists()

    def test_default_persona_is_windows(self, titan_controller):
        """Default persona is WINDOWS."""
        assert titan_controller.current_persona == Persona.WINDOWS

    def test_no_current_profile_initially(self, titan_controller):
        """No profile loaded at startup."""
        assert titan_controller.current_profile is None

    def test_not_initialized_at_start(self, titan_controller):
        """is_initialized is False before calling initialize()."""
        assert titan_controller.is_initialized is False

    def test_has_genesis_engine(self, titan_controller):
        """Controller has a GenesisEngine instance."""
        assert isinstance(titan_controller.genesis, GenesisEngine)

    def test_has_temporal_displacement(self, titan_controller):
        """Controller has a TemporalDisplacement instance."""
        assert isinstance(titan_controller.temporal, TemporalDisplacement)

    def test_network_shield_initially_none(self, titan_controller):
        """Network shield is None (lazy loaded)."""
        assert titan_controller.network_shield is None


class TestTitanControllerConfig:
    """Test configuration save/load."""

    def test_save_config(self, titan_controller, tmp_titan_dir):
        """_save_config() writes config.json."""
        titan_controller._save_config()
        config_file = tmp_titan_dir / "config.json"
        assert config_file.exists()
        with open(config_file) as f:
            data = json.load(f)
        assert data["persona"] == "WINDOWS"
        assert "last_updated" in data

    def test_load_config_restores_persona(self, tmp_titan_dir):
        """_load_config() restores persona from disk."""
        config_file = tmp_titan_dir / "config.json"
        with open(config_file, "w") as f:
            json.dump({"persona": "LINUX"}, f)
        ctrl = TitanController(base_dir=tmp_titan_dir)
        assert ctrl.current_persona == Persona.LINUX

    def test_load_config_missing_file(self, tmp_titan_dir):
        """Missing config.json defaults to WINDOWS."""
        config_file = tmp_titan_dir / "config.json"
        if config_file.exists():
            config_file.unlink()
        ctrl = TitanController(base_dir=tmp_titan_dir)
        assert ctrl.current_persona == Persona.WINDOWS


class TestSetPersona:
    """Test persona switching."""

    def test_set_windows(self, titan_controller):
        """Set persona to windows."""
        result = titan_controller.set_persona("windows")
        assert titan_controller.current_persona == Persona.WINDOWS
        assert result["persona"] == "WINDOWS"
        assert "user_agent" in result

    def test_set_linux(self, titan_controller):
        """Set persona to linux."""
        result = titan_controller.set_persona("linux")
        assert titan_controller.current_persona == Persona.LINUX
        assert "Linux" in result["user_agent"]

    def test_set_macos(self, titan_controller):
        """Set persona to macos."""
        result = titan_controller.set_persona("macos")
        assert titan_controller.current_persona == Persona.MACOS
        assert "Macintosh" in result["user_agent"]

    def test_case_insensitive(self, titan_controller):
        """Persona name is case-insensitive."""
        titan_controller.set_persona("WINDOWS")
        assert titan_controller.current_persona == Persona.WINDOWS
        titan_controller.set_persona("Linux")
        assert titan_controller.current_persona == Persona.LINUX

    def test_invalid_persona_raises(self, titan_controller):
        """Unknown persona raises ValueError."""
        with pytest.raises(ValueError, match="Unknown persona"):
            titan_controller.set_persona("android")

    def test_set_persona_saves_config(self, titan_controller, tmp_titan_dir):
        """Setting persona persists to config.json."""
        titan_controller.set_persona("macos")
        with open(tmp_titan_dir / "config.json") as f:
            data = json.load(f)
        assert data["persona"] == "MACOS"


class TestCreateProfile:
    """Test profile creation via controller."""

    def test_create_profile_default(self, titan_controller):
        """Create profile with defaults."""
        profile = titan_controller.create_profile("ctrl_test_001")
        assert profile.profile_id == "ctrl_test_001"
        assert profile.persona == Persona.WINDOWS

    def test_create_profile_uses_current_persona(self, titan_controller):
        """Profile uses the controller's current persona."""
        titan_controller.set_persona("linux")
        profile = titan_controller.create_profile("linux_prof")
        assert profile.persona == Persona.LINUX

    def test_create_profile_sets_current(self, titan_controller):
        """Creating a profile sets it as current_profile."""
        profile = titan_controller.create_profile("current_test")
        assert titan_controller.current_profile is profile

    def test_create_profile_custom_age(self, titan_controller):
        """Custom age_days is respected."""
        profile = titan_controller.create_profile("age_test", age_days=30)
        assert profile.apparent_age_days == 30

    def test_create_profile_custom_theme(self, titan_controller):
        """Custom theme is respected."""
        profile = titan_controller.create_profile("theme_test", theme="gamer")
        # Gamer theme should have gaming-related URLs in history
        urls = [e["url"] for e in profile.browsing_history]
        gaming_urls = [u for u in urls if any(
            site in u for site in ["steam", "twitch", "discord", "epic"]
        )]
        assert len(gaming_urls) > 0


class TestLoadProfile:
    """Test profile loading via controller."""

    def test_load_existing(self, titan_controller):
        """Load a previously created profile."""
        titan_controller.create_profile("load_ctrl")
        titan_controller.current_profile = None
        loaded = titan_controller.load_profile("load_ctrl")
        assert loaded is not None
        assert loaded.profile_id == "load_ctrl"
        assert titan_controller.current_profile is loaded

    def test_load_updates_persona(self, titan_controller):
        """Loading a profile updates current_persona to match."""
        titan_controller.set_persona("linux")
        titan_controller.create_profile("linux_load")
        titan_controller.set_persona("windows")
        titan_controller.load_profile("linux_load")
        assert titan_controller.current_persona == Persona.LINUX

    def test_load_nonexistent(self, titan_controller):
        """Loading missing profile returns None."""
        result = titan_controller.load_profile("ghost_profile")
        assert result is None


class TestListProfiles:
    """Test profile listing via controller."""

    def test_list_empty(self, titan_controller):
        """No profiles initially."""
        assert titan_controller.list_profiles() == []

    def test_list_after_create(self, titan_controller):
        """Created profiles appear in list."""
        titan_controller.create_profile("list_1")
        titan_controller.create_profile("list_2")
        profiles = titan_controller.list_profiles()
        assert "list_1" in profiles
        assert "list_2" in profiles


class TestGetBrowserEnv:
    """Test browser environment variable generation."""

    def test_env_without_profile(self, titan_controller):
        """get_browser_env() works without a loaded profile."""
        env = titan_controller.get_browser_env()
        assert isinstance(env, dict)
        # Should not have profile vars without a profile
        assert "MOZ_PROFILER_SESSION" not in env

    def test_env_with_profile(self, titan_controller):
        """get_browser_env() includes profile vars when profile is loaded."""
        titan_controller.create_profile("env_test")
        env = titan_controller.get_browser_env()
        assert "MOZ_PROFILER_SESSION" in env
        assert env["MOZ_PROFILER_SESSION"] == "env_test"
        assert "MOZ_GFX_SEED" in env
        assert "MOZ_MEDIA_SEED" in env

    def test_env_seeds_are_strings(self, titan_controller):
        """Environment variable values are strings."""
        titan_controller.create_profile("str_test")
        env = titan_controller.get_browser_env()
        assert isinstance(env["MOZ_GFX_SEED"], str)
        assert isinstance(env["MOZ_MEDIA_SEED"], str)


class TestGetStatus:
    """Test status reporting."""

    def test_status_structure(self, titan_controller):
        """Status dict has expected keys."""
        status = titan_controller.get_status()
        assert "initialized" in status
        assert "persona" in status
        assert "current_profile" in status
        assert "temporal_displacement" in status
        assert "network_shield" in status
        assert "profiles_count" in status

    def test_status_initial(self, titan_controller):
        """Initial status values are correct."""
        status = titan_controller.get_status()
        assert status["initialized"] is False
        assert status["persona"] == "WINDOWS"
        assert status["current_profile"] is None
        assert status["profiles_count"] == 0
        assert status["network_shield"]["available"] is False

    def test_status_after_profile_create(self, titan_controller):
        """Status reflects created profile."""
        titan_controller.create_profile("status_test")
        status = titan_controller.get_status()
        assert status["current_profile"] is not None
        assert status["current_profile"]["profile_id"] == "status_test"
        assert status["profiles_count"] == 1


class TestInitialize:
    """Test TITAN initialization."""

    def test_initialize_non_root(self, titan_controller):
        """Initialize works when not running as root (skips network shield)."""
        with patch("os.geteuid", create=True, return_value=1000):
            result = titan_controller.initialize()
            assert result is True
            assert titan_controller.is_initialized is True
            assert titan_controller.network_shield is None


class TestShutdown:
    """Test graceful shutdown."""

    def test_shutdown_deactivates_temporal(self, titan_controller):
        """Shutdown deactivates temporal displacement."""
        titan_controller.temporal.is_active = True
        titan_controller.temporal.offset_days = 90
        titan_controller.shutdown()
        assert titan_controller.temporal.is_active is False
        assert titan_controller.temporal.offset_days == 0

    def test_shutdown_saves_config(self, titan_controller, tmp_titan_dir):
        """Shutdown saves config to disk."""
        titan_controller.shutdown()
        assert (tmp_titan_dir / "config.json").exists()
