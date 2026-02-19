"""
Tests for FingerprintInjector – hardware_concurrency CDP preload injection.

Covers:
 - FingerprintConfig.hardware_concurrency default value
 - generate_hardware_concurrency_script() output shape
 - inject_cdp_preload() calls execute_cdp_cmd with correct args
 - NetlinkHWBridge.sync_with_injector picks up the configured value
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, call
import pytest

# Make the fingerprint_injector module importable without the full OS environment
INJECTOR_DIR = Path(__file__).parent.parent / "iso/config/includes.chroot/opt/titan/core"
sys.path.insert(0, str(INJECTOR_DIR))

from fingerprint_injector import FingerprintConfig, FingerprintInjector, NetlinkHWBridge, create_injector


# ---------------------------------------------------------------------------
# FingerprintConfig defaults
# ---------------------------------------------------------------------------

class TestFingerprintConfigDefaults:
    """hardware_concurrency field exists and defaults to 16."""

    def test_default_hardware_concurrency(self):
        cfg = FingerprintConfig(profile_uuid="test-uuid-001")
        assert cfg.hardware_concurrency == 16

    def test_custom_hardware_concurrency(self):
        cfg = FingerprintConfig(profile_uuid="test-uuid-002", hardware_concurrency=4)
        assert cfg.hardware_concurrency == 4

    def test_hardware_concurrency_is_int(self):
        cfg = FingerprintConfig(profile_uuid="test-uuid-003")
        assert isinstance(cfg.hardware_concurrency, int)


# ---------------------------------------------------------------------------
# generate_hardware_concurrency_script
# ---------------------------------------------------------------------------

class TestGenerateHardwareConcurrencyScript:
    """generate_hardware_concurrency_script() returns correct JavaScript."""

    def test_script_is_string(self):
        injector = create_injector("script-test-001")
        script = injector.generate_hardware_concurrency_script()
        assert isinstance(script, str)

    def test_script_contains_define_property(self):
        injector = create_injector("script-test-002")
        script = injector.generate_hardware_concurrency_script()
        assert "Object.defineProperty" in script
        assert "hardwareConcurrency" in script

    def test_script_embeds_configured_value(self):
        injector = create_injector("script-test-003", hardware_concurrency=8)
        script = injector.generate_hardware_concurrency_script()
        assert "8" in script

    def test_script_embeds_default_value(self):
        injector = create_injector("script-test-004")
        script = injector.generate_hardware_concurrency_script()
        assert "16" in script

    def test_script_not_configurable(self):
        """Property must be non-configurable to prevent page-level override."""
        injector = create_injector("script-test-005")
        script = injector.generate_hardware_concurrency_script()
        assert "configurable: false" in script

    def test_script_is_iife(self):
        """Script should be wrapped in an IIFE to avoid global scope pollution."""
        injector = create_injector("script-test-006")
        script = injector.generate_hardware_concurrency_script()
        assert "(function" in script

    def test_script_changes_with_concurrency_value(self):
        injector_16 = create_injector("script-test-007a", hardware_concurrency=16)
        injector_4 = create_injector("script-test-007b", hardware_concurrency=4)
        assert injector_16.generate_hardware_concurrency_script() != \
               injector_4.generate_hardware_concurrency_script()


# ---------------------------------------------------------------------------
# inject_cdp_preload
# ---------------------------------------------------------------------------

class TestInjectCdpPreload:
    """inject_cdp_preload() calls execute_cdp_cmd with correct arguments."""

    def _make_driver(self):
        driver = MagicMock()
        driver.execute_cdp_cmd = MagicMock(return_value={})
        return driver

    def test_calls_execute_cdp_cmd(self):
        injector = create_injector("cdp-test-001")
        driver = self._make_driver()
        injector.inject_cdp_preload(driver)
        driver.execute_cdp_cmd.assert_called_once()

    def test_uses_correct_cdp_command(self):
        injector = create_injector("cdp-test-002")
        driver = self._make_driver()
        injector.inject_cdp_preload(driver)
        cmd, params = driver.execute_cdp_cmd.call_args[0]
        assert cmd == "Page.addScriptToEvaluateOnNewDocument"

    def test_source_key_in_params(self):
        injector = create_injector("cdp-test-003")
        driver = self._make_driver()
        injector.inject_cdp_preload(driver)
        _, params = driver.execute_cdp_cmd.call_args[0]
        assert "source" in params

    def test_injected_script_contains_hardware_concurrency(self):
        injector = create_injector("cdp-test-004", hardware_concurrency=12)
        driver = self._make_driver()
        injector.inject_cdp_preload(driver)
        _, params = driver.execute_cdp_cmd.call_args[0]
        assert "hardwareConcurrency" in params["source"]
        assert "12" in params["source"]


# ---------------------------------------------------------------------------
# NetlinkHWBridge.sync_with_injector uses hardware_concurrency from config
# ---------------------------------------------------------------------------

class TestNetlinkHWBridgeSyncConcurrency:
    """sync_with_injector sends hardware_concurrency value from config."""

    def test_sync_uses_config_hardware_concurrency(self):
        bridge = NetlinkHWBridge()
        bridge.connected = True
        bridge._pid = 1234
        bridge.sock = MagicMock()

        injector = create_injector("netlink-test-001", hardware_concurrency=8)
        bridge.send_profile = MagicMock(return_value=True)

        bridge.sync_with_injector(injector)

        sent_profile = bridge.send_profile.call_args[0][0]
        assert sent_profile["cpu_cores"] == 8

    def test_sync_default_concurrency_is_16(self):
        bridge = NetlinkHWBridge()
        bridge.connected = True
        bridge._pid = 1234
        bridge.sock = MagicMock()

        injector = create_injector("netlink-test-002")  # default = 16
        bridge.send_profile = MagicMock(return_value=True)

        bridge.sync_with_injector(injector)

        sent_profile = bridge.send_profile.call_args[0][0]
        assert sent_profile["cpu_cores"] == 16

    def test_sync_returns_false_on_no_injector(self):
        bridge = NetlinkHWBridge()
        result = bridge.sync_with_injector(None)
        assert result is False
