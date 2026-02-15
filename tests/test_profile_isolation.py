"""
Tests for ProfileIsolator - Process isolation via namespaces and cgroups.
"""

import pytest
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from titan.profile_isolation import (
    ProfileIsolatorError,
    ResourceLimits,
    CgroupManager,
)


class TestResourceLimits:
    """Test ResourceLimits dataclass."""

    def test_default_values(self):
        """Default resource limits are reasonable."""
        limits = ResourceLimits()
        assert limits.memory_max_mb == 4096
        assert limits.cpu_quota_percent == 100
        assert limits.pids_max == 500
        assert limits.io_weight == 100

    def test_custom_values(self):
        """Custom resource limits are accepted."""
        limits = ResourceLimits(
            memory_max_mb=2048,
            cpu_quota_percent=50,
            pids_max=200,
            io_weight=50,
        )
        assert limits.memory_max_mb == 2048
        assert limits.cpu_quota_percent == 50
        assert limits.pids_max == 200
        assert limits.io_weight == 50

    def test_zero_values(self):
        """Zero values are technically valid."""
        limits = ResourceLimits(memory_max_mb=0, cpu_quota_percent=0, pids_max=0, io_weight=0)
        assert limits.memory_max_mb == 0


class TestCgroupManager:
    """Test CgroupManager for resource isolation."""

    def test_init_sets_profile_id(self):
        """CgroupManager stores profile_id."""
        mgr = CgroupManager("test_profile")
        assert mgr.profile_id == "test_profile"

    def test_cgroup_name_format(self):
        """Cgroup name is prefixed with 'titan-'."""
        mgr = CgroupManager("my_profile")
        assert mgr.cgroup_name == "titan-my_profile"

    def test_cgroup_path(self):
        """Cgroup path is under /sys/fs/cgroup."""
        mgr = CgroupManager("test")
        # Use PurePosixPath for comparison since cgroup paths are Linux-only
        path_str = mgr.cgroup_path.as_posix()
        assert path_str.startswith("/sys/fs/cgroup")
        assert "titan-test" in path_str

    def test_is_cgroup_v2_checks_controllers_file(self):
        """is_cgroup_v2() checks for cgroup.controllers file."""
        mgr = CgroupManager("test")
        with patch.object(Path, "exists", return_value=True):
            assert mgr.is_cgroup_v2() is True
        with patch.object(Path, "exists", return_value=False):
            assert mgr.is_cgroup_v2() is False

    def test_create_returns_false_without_cgroup_v2(self):
        """create() returns False when cgroup v2 is unavailable."""
        mgr = CgroupManager("test")
        with patch.object(mgr, "is_cgroup_v2", return_value=False):
            result = mgr.create(ResourceLimits())
            assert result is False


class TestProfileIsolatorError:
    """Test custom exception."""

    def test_is_exception(self):
        """ProfileIsolatorError is an Exception subclass."""
        assert issubclass(ProfileIsolatorError, Exception)

    def test_can_raise(self):
        """Can be raised and caught."""
        with pytest.raises(ProfileIsolatorError, match="test error"):
            raise ProfileIsolatorError("test error")
