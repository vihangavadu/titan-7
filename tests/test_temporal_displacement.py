"""
Tests for TemporalDisplacement - libfaketime integration.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, PropertyMock
from pathlib import Path
from titan.titan_core import TemporalDisplacement


class TestTemporalAvailability:
    """Test libfaketime detection."""

    def test_is_available_when_lib_exists(self, temporal):
        """Returns True when libfaketime .so exists on disk."""
        with patch.object(Path, "exists", return_value=True):
            assert temporal.is_available() is True

    def test_is_available_when_lib_missing(self, temporal):
        """Returns False when libfaketime .so is not found."""
        with patch.object(Path, "exists", return_value=False):
            assert temporal.is_available() is False

    def test_libfaketime_path_is_linux(self, temporal):
        """Default path targets x86_64 Linux."""
        assert "x86_64-linux-gnu" in temporal.LIBFAKETIME_PATH


class TestTemporalActivation:
    """Test time displacement activation."""

    def test_activate_returns_env_vars(self, temporal):
        """activate() returns LD_PRELOAD and FAKETIME env vars."""
        with patch.object(Path, "exists", return_value=True):
            env = temporal.activate(offset_days=90)
            assert "LD_PRELOAD" in env
            assert "FAKETIME" in env
            assert "FAKETIME_NO_CACHE" in env
            assert env["FAKETIME_NO_CACHE"] == "1"

    def test_activate_sets_state(self, temporal):
        """activate() sets is_active and offset_days."""
        with patch.object(Path, "exists", return_value=True):
            temporal.activate(offset_days=60)
            assert temporal.is_active is True
            assert temporal.offset_days == 60

    def test_activate_faketime_format(self, temporal):
        """FAKETIME value starts with @ and contains a date."""
        with patch.object(Path, "exists", return_value=True):
            env = temporal.activate(offset_days=30)
            assert env["FAKETIME"].startswith("@")
            # Should contain a parseable date after @
            date_str = env["FAKETIME"][1:]
            parsed = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            assert isinstance(parsed, datetime)

    def test_activate_offset_is_backwards(self, temporal):
        """Activated time should be in the past by offset_days."""
        with patch.object(Path, "exists", return_value=True):
            env = temporal.activate(offset_days=90)
            date_str = env["FAKETIME"][1:]
            fake_time = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            now = datetime.now()
            diff = (now - fake_time).days
            # Allow 1 day tolerance for midnight edge cases
            assert 89 <= diff <= 91

    def test_activate_returns_empty_when_unavailable(self, temporal):
        """Returns empty dict when libfaketime is not installed."""
        with patch.object(Path, "exists", return_value=False):
            env = temporal.activate(offset_days=90)
            assert env == {}
            assert temporal.is_active is False


class TestTemporalDeactivation:
    """Test time displacement deactivation."""

    def test_deactivate_resets_state(self, temporal):
        """deactivate() clears is_active and offset_days."""
        temporal.is_active = True
        temporal.offset_days = 90
        temporal.deactivate()
        assert temporal.is_active is False
        assert temporal.offset_days == 0

    def test_deactivate_idempotent(self, temporal):
        """Calling deactivate() when already inactive is safe."""
        temporal.deactivate()
        assert temporal.is_active is False
        assert temporal.offset_days == 0


class TestTemporalApparentTime:
    """Test get_apparent_time()."""

    def test_apparent_time_with_offset(self, temporal):
        """get_apparent_time() returns now minus offset_days."""
        temporal.offset_days = 45
        apparent = temporal.get_apparent_time()
        expected = datetime.now() - timedelta(days=45)
        diff = abs((apparent - expected).total_seconds())
        assert diff < 2  # within 2 seconds

    def test_apparent_time_zero_offset(self, temporal):
        """With zero offset, apparent time equals real time."""
        temporal.offset_days = 0
        apparent = temporal.get_apparent_time()
        diff = abs((apparent - datetime.now()).total_seconds())
        assert diff < 2

    def test_initial_state(self, temporal):
        """Fresh instance has correct initial state."""
        assert temporal.is_active is False
        assert temporal.offset_days == 0
        assert temporal._original_env == {}
