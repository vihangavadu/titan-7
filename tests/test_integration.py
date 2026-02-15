"""
Integration tests - End-to-end workflows across Titan subsystems.
"""

import pytest
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch
from titan.titan_core import (
    TitanController, GenesisEngine, TemporalDisplacement,
    BrowserProfile, Persona,
)


class TestFullProfileLifecycle:
    """Test complete profile create → save → load → use cycle."""

    def test_create_save_load_roundtrip(self, titan_controller):
        """Profile survives a full create → load roundtrip."""
        original = titan_controller.create_profile(
            "roundtrip_001", age_days=60, theme="gamer"
        )
        titan_controller.current_profile = None

        loaded = titan_controller.load_profile("roundtrip_001")
        assert loaded is not None
        assert loaded.profile_id == original.profile_id
        assert loaded.uuid == original.uuid
        assert loaded.persona == original.persona
        assert loaded.apparent_age_days == original.apparent_age_days
        assert loaded.canvas_seed == original.canvas_seed
        assert loaded.webgl_seed == original.webgl_seed
        assert loaded.audio_seed == original.audio_seed
        assert loaded.stripe_mid == original.stripe_mid
        assert loaded.stripe_sid == original.stripe_sid
        assert loaded.adyen_rp_uid == original.adyen_rp_uid
        assert loaded.user_agent == original.user_agent
        assert len(loaded.browsing_history) == len(original.browsing_history)
        assert len(loaded.cookies) == len(original.cookies)

    def test_multiple_profiles_independent(self, titan_controller):
        """Multiple profiles don't interfere with each other."""
        p1 = titan_controller.create_profile("multi_1", theme="gamer")
        titan_controller.set_persona("linux")
        p2 = titan_controller.create_profile("multi_2", theme="professional")
        titan_controller.set_persona("macos")
        p3 = titan_controller.create_profile("multi_3", theme="shopper")

        # Reload and verify independence
        l1 = titan_controller.load_profile("multi_1")
        l2 = titan_controller.load_profile("multi_2")
        l3 = titan_controller.load_profile("multi_3")

        assert l1.uuid != l2.uuid != l3.uuid
        assert l1.persona == Persona.WINDOWS
        assert l2.persona == Persona.LINUX
        assert l3.persona == Persona.MACOS
        assert l1.canvas_seed != l2.canvas_seed
        assert l2.canvas_seed != l3.canvas_seed

    def test_profile_listing_after_operations(self, titan_controller):
        """Profile listing stays consistent after create/load operations."""
        titan_controller.create_profile("list_a")
        titan_controller.create_profile("list_b")
        titan_controller.create_profile("list_c")

        profiles = titan_controller.list_profiles()
        assert len(profiles) == 3
        assert set(profiles) == {"list_a", "list_b", "list_c"}

        # Loading doesn't change the list
        titan_controller.load_profile("list_b")
        assert len(titan_controller.list_profiles()) == 3


class TestPersonaProfileInteraction:
    """Test persona switching affects profile creation."""

    def test_persona_determines_user_agent(self, titan_controller):
        """Profile user_agent matches the active persona."""
        for persona_name, expected_fragment in [
            ("windows", "Windows NT"),
            ("linux", "X11; Linux"),
            ("macos", "Macintosh"),
        ]:
            titan_controller.set_persona(persona_name)
            profile = titan_controller.create_profile(f"ua_{persona_name}")
            assert expected_fragment in profile.user_agent

    def test_persona_switch_mid_session(self, titan_controller):
        """Switching persona between profile creations works correctly."""
        titan_controller.set_persona("windows")
        p_win = titan_controller.create_profile("switch_win")

        titan_controller.set_persona("linux")
        p_lin = titan_controller.create_profile("switch_lin")

        assert p_win.persona == Persona.WINDOWS
        assert p_lin.persona == Persona.LINUX
        assert "Windows" in p_win.user_agent
        assert "Linux" in p_lin.user_agent


class TestBrowserEnvIntegration:
    """Test browser environment generation with real profiles."""

    def test_env_contains_all_profile_data(self, titan_controller):
        """Browser env has all expected TITAN_ variables."""
        profile = titan_controller.create_profile("env_full", age_days=45)
        env = titan_controller.get_browser_env()

        assert env["MOZ_PROFILER_SESSION"] == "env_full"
        assert env["MOZ_GFX_SEED"] == str(profile.canvas_seed)
        assert env["MOZ_MEDIA_SEED"] == str(profile.audio_seed)

    def test_env_inherits_system_env(self, titan_controller):
        """Browser env includes system environment variables."""
        titan_controller.create_profile("sys_env")
        env = titan_controller.get_browser_env()
        # PATH should be inherited from system
        assert "PATH" in env or "Path" in env


class TestProfileDataIntegrity:
    """Test data integrity across the profile pipeline."""

    def test_history_phases_chronological(self, genesis):
        """Browsing history phases are in chronological order."""
        profile = genesis.create_profile("chrono_test", age_days=90)
        phases_seen = []
        for entry in profile.browsing_history:
            phase = entry["phase"]
            if not phases_seen or phases_seen[-1] != phase:
                phases_seen.append(phase)

        # Phases should appear in order: inception → warming → kill_chain
        assert phases_seen == ["inception", "warming", "kill_chain"]

    def test_cookie_timestamps_match_profile_age(self, genesis):
        """Cookie creation times align with profile apparent age."""
        profile = genesis.create_profile("cookie_age", age_days=90)
        now_ts = datetime.now().timestamp()
        for cookie in profile.cookies:
            age_seconds = now_ts - cookie["created"]
            age_days = age_seconds / 86400
            # Cookies should be created within the profile's age window
            assert age_days <= 95  # Allow some margin
            assert age_days >= 0

    def test_trust_anchors_in_history(self, genesis):
        """Trust anchor domains appear in inception phase history."""
        profile = genesis.create_profile("anchor_test", age_days=90)
        inception_urls = [
            e["url"] for e in profile.browsing_history
            if e["phase"] == "inception"
        ]
        for anchor in GenesisEngine.TRUST_ANCHORS:
            matching = [u for u in inception_urls if anchor in u]
            assert len(matching) > 0, f"Trust anchor {anchor} not in inception history"

    def test_serialization_roundtrip_fidelity(self, genesis):
        """Profile → JSON → Profile preserves all data."""
        original = genesis.create_profile("fidelity_test", age_days=120, theme="professional")
        original_dict = original.to_dict()

        # Save and reload
        loaded = genesis.load_profile("fidelity_test")
        loaded_dict = loaded.to_dict()

        # Compare all serialized fields
        for key in original_dict:
            assert original_dict[key] == loaded_dict[key], f"Mismatch on key: {key}"


class TestStatusReporting:
    """Test status reporting across subsystem states."""

    def test_status_reflects_full_workflow(self, titan_controller):
        """Status updates correctly through a full workflow."""
        # Initial
        s1 = titan_controller.get_status()
        assert s1["initialized"] is False
        assert s1["profiles_count"] == 0

        # After profile creation
        titan_controller.create_profile("workflow_1")
        s2 = titan_controller.get_status()
        assert s2["profiles_count"] == 1
        assert s2["current_profile"]["profile_id"] == "workflow_1"

        # After persona switch and second profile
        titan_controller.set_persona("linux")
        titan_controller.create_profile("workflow_2")
        s3 = titan_controller.get_status()
        assert s3["persona"] == "LINUX"
        assert s3["profiles_count"] == 2
        assert s3["current_profile"]["profile_id"] == "workflow_2"

    def test_status_json_serializable(self, titan_controller):
        """Status dict can be serialized to JSON."""
        titan_controller.create_profile("json_status")
        status = titan_controller.get_status()
        json_str = json.dumps(status, default=str)
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed["current_profile"]["profile_id"] == "json_status"


class TestShutdownIntegration:
    """Test shutdown across subsystems."""

    def test_shutdown_preserves_profiles(self, titan_controller):
        """Profiles on disk survive shutdown."""
        titan_controller.create_profile("survive_shutdown")
        titan_controller.shutdown()

        # Create new controller pointing to same dir
        new_ctrl = TitanController(base_dir=titan_controller.base_dir)
        profiles = new_ctrl.list_profiles()
        assert "survive_shutdown" in profiles

    def test_shutdown_preserves_persona_config(self, titan_controller):
        """Persona setting survives shutdown and reload."""
        titan_controller.set_persona("macos")
        titan_controller.shutdown()

        new_ctrl = TitanController(base_dir=titan_controller.base_dir)
        assert new_ctrl.current_persona == Persona.MACOS
