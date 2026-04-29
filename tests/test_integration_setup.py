"""Integration setup/teardown tests for __init__.py (task 12.4).

Tests async_setup_entry and async_unload_entry with mocked Modbus client
and coordinator.

Requirements: 8.1, 8.5
"""
from __future__ import annotations

import sys
import types
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

# ---------------------------------------------------------------------------
# Stubs for homeassistant modules
# ---------------------------------------------------------------------------

def _ensure_stub(name: str) -> types.ModuleType:
    if name not in sys.modules:
        sys.modules[name] = types.ModuleType(name)
    return sys.modules[name]


for _mod in [
    "homeassistant",
    "homeassistant.config_entries",
    "homeassistant.const",
    "homeassistant.core",
    "homeassistant.exceptions",
    "homeassistant.helpers",
    "homeassistant.helpers.update_coordinator",
]:
    _ensure_stub(_mod)

# ConfigEntry stub
_ce = sys.modules["homeassistant.config_entries"]
if not hasattr(_ce, "ConfigEntry"):
    class _ConfigEntryStub:
        def __init__(self, entry_id="test_entry_id", data=None):
            self.entry_id = entry_id
            self.data = data or {}
    _ce.ConfigEntry = _ConfigEntryStub  # type: ignore[attr-defined]

# ConfigEntryNotReady stub
_exc = sys.modules["homeassistant.exceptions"]
if not hasattr(_exc, "ConfigEntryNotReady"):
    class _ConfigEntryNotReady(Exception):
        pass
    _exc.ConfigEntryNotReady = _ConfigEntryNotReady  # type: ignore[attr-defined]

# Re-export so __init__.py can import it
ConfigEntryNotReady = _exc.ConfigEntryNotReady  # type: ignore[attr-defined]

_const = sys.modules["homeassistant.const"]
_const.CONF_HOST = "host"  # type: ignore[attr-defined]
_const.CONF_PORT = "port"  # type: ignore[attr-defined]

# DataUpdateCoordinator stub
class _FakeDataUpdateCoordinator:
    def __init__(self, hass, logger, *, name, update_interval):
        self.hass = hass
        self.logger = logger
        self.name = name
        self.update_interval = update_interval
        self.data = {}

    async def async_config_entry_first_refresh(self):
        pass

    def __class_getitem__(cls, item):
        return cls

_uc = sys.modules["homeassistant.helpers.update_coordinator"]
_uc.DataUpdateCoordinator = _FakeDataUpdateCoordinator  # type: ignore[attr-defined]

class _UpdateFailed(Exception):
    pass

_uc.UpdateFailed = _UpdateFailed  # type: ignore[attr-defined]

_core = sys.modules["homeassistant.core"]
_core.HomeAssistant = object  # type: ignore[attr-defined]

# ---------------------------------------------------------------------------
# Now import the module under test
# ---------------------------------------------------------------------------

from custom_components.lambda_heat_pump import async_setup_entry, async_unload_entry
from custom_components.lambda_heat_pump.const import DOMAIN, PLATFORMS

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ENTRY_DATA = {
    "host": "192.168.1.100",
    "port": 502,
    "num_heatpumps": 1,
    "num_heating_circuits": 0,
    "num_boilers": 0,
    "num_buffers": 0,
    "num_solar": 0,
    "enable_ambient": False,
    "enable_emanager": False,
    "scan_interval": 30,
}


def _make_entry(entry_id="test_entry_id", data=None):
    entry = MagicMock()
    entry.entry_id = entry_id
    entry.data = data or ENTRY_DATA
    return entry


def _make_hass():
    """Create a minimal hass-like object with a real dict for hass.data."""
    hass = MagicMock()
    hass.data = {}
    # async_forward_entry_setups and async_unload_platforms return True
    hass.config_entries = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    return hass


# ---------------------------------------------------------------------------
# Test: Successful setup
# ---------------------------------------------------------------------------

class TestSuccessfulSetup:
    def test_coordinator_stored_in_hass_data(self):
        """After successful setup, coordinator and client are stored in hass.data."""
        hass = _make_hass()
        entry = _make_entry()

        with (
            patch("custom_components.lambda_heat_pump.modbus_client.LambdaModbusClient") as MockClient,
            patch("custom_components.lambda_heat_pump.coordinator.LambdaCoordinator") as MockCoord,
        ):
            mock_client = MockClient.return_value
            mock_client.connect = AsyncMock(return_value=True)

            mock_coord = MockCoord.return_value
            mock_coord.async_config_entry_first_refresh = AsyncMock()

            result = asyncio.run(async_setup_entry(hass, entry))

        assert result is True
        assert DOMAIN in hass.data
        assert entry.entry_id in hass.data[DOMAIN]
        stored = hass.data[DOMAIN][entry.entry_id]
        assert "coordinator" in stored
        assert "client" in stored

    def test_client_created_with_correct_host_and_port(self):
        """LambdaModbusClient is instantiated with host and port from config entry."""
        hass = _make_hass()
        entry = _make_entry(data={**ENTRY_DATA, "host": "10.0.0.5", "port": 1502})

        with (
            patch("custom_components.lambda_heat_pump.modbus_client.LambdaModbusClient") as MockClient,
            patch("custom_components.lambda_heat_pump.coordinator.LambdaCoordinator") as MockCoord,
        ):
            mock_client = MockClient.return_value
            mock_client.connect = AsyncMock(return_value=True)
            mock_coord = MockCoord.return_value
            mock_coord.async_config_entry_first_refresh = AsyncMock()

            asyncio.run(async_setup_entry(hass, entry))

        MockClient.assert_called_once_with("10.0.0.5", 1502)

    def test_platforms_are_forwarded(self):
        """async_forward_entry_setups is called with the correct platforms."""
        hass = _make_hass()
        entry = _make_entry()

        with (
            patch("custom_components.lambda_heat_pump.modbus_client.LambdaModbusClient") as MockClient,
            patch("custom_components.lambda_heat_pump.coordinator.LambdaCoordinator") as MockCoord,
        ):
            mock_client = MockClient.return_value
            mock_client.connect = AsyncMock(return_value=True)
            mock_coord = MockCoord.return_value
            mock_coord.async_config_entry_first_refresh = AsyncMock()

            asyncio.run(async_setup_entry(hass, entry))

        hass.config_entries.async_forward_entry_setups.assert_called_once_with(
            entry, PLATFORMS
        )

    def test_coordinator_first_refresh_called(self):
        """async_config_entry_first_refresh is called during setup."""
        hass = _make_hass()
        entry = _make_entry()

        with (
            patch("custom_components.lambda_heat_pump.modbus_client.LambdaModbusClient") as MockClient,
            patch("custom_components.lambda_heat_pump.coordinator.LambdaCoordinator") as MockCoord,
        ):
            mock_client = MockClient.return_value
            mock_client.connect = AsyncMock(return_value=True)
            mock_coord = MockCoord.return_value
            mock_coord.async_config_entry_first_refresh = AsyncMock()

            asyncio.run(async_setup_entry(hass, entry))

        mock_coord.async_config_entry_first_refresh.assert_called_once()


# ---------------------------------------------------------------------------
# Test: Failed connection on setup (Requirement 8.1)
# ---------------------------------------------------------------------------

class TestFailedConnectionOnSetup:
    def test_raises_config_entry_not_ready_on_connection_failure(self):
        """If connection fails, ConfigEntryNotReady is raised (HA retries automatically).

        Validates: Requirement 8.1 – integration must not block startup;
        ConfigEntryNotReady signals HA to retry in the background.
        """
        hass = _make_hass()
        entry = _make_entry()

        with (
            patch("custom_components.lambda_heat_pump.modbus_client.LambdaModbusClient") as MockClient,
            patch("custom_components.lambda_heat_pump.coordinator.LambdaCoordinator"),
        ):
            mock_client = MockClient.return_value
            mock_client.connect = AsyncMock(return_value=False)

            with pytest.raises(ConfigEntryNotReady):
                asyncio.run(async_setup_entry(hass, entry))

    def test_hass_data_not_populated_on_connection_failure(self):
        """On connection failure, nothing is stored in hass.data."""
        hass = _make_hass()
        entry = _make_entry()

        with (
            patch("custom_components.lambda_heat_pump.modbus_client.LambdaModbusClient") as MockClient,
            patch("custom_components.lambda_heat_pump.coordinator.LambdaCoordinator"),
        ):
            mock_client = MockClient.return_value
            mock_client.connect = AsyncMock(return_value=False)

            try:
                asyncio.run(async_setup_entry(hass, entry))
            except ConfigEntryNotReady:
                pass

        # hass.data should not contain the entry
        assert entry.entry_id not in hass.data.get(DOMAIN, {})

    def test_platforms_not_forwarded_on_connection_failure(self):
        """Platforms are not set up when the connection cannot be established."""
        hass = _make_hass()
        entry = _make_entry()

        with (
            patch("custom_components.lambda_heat_pump.modbus_client.LambdaModbusClient") as MockClient,
            patch("custom_components.lambda_heat_pump.coordinator.LambdaCoordinator"),
        ):
            mock_client = MockClient.return_value
            mock_client.connect = AsyncMock(return_value=False)

            try:
                asyncio.run(async_setup_entry(hass, entry))
            except ConfigEntryNotReady:
                pass

        hass.config_entries.async_forward_entry_setups.assert_not_called()


# ---------------------------------------------------------------------------
# Test: Teardown / async_unload_entry (Requirement 8.5)
# ---------------------------------------------------------------------------

class TestTeardown:
    def test_unload_disconnects_modbus_client(self):
        """On unload, client.disconnect() is called to close the TCP connection.

        Validates: Requirement 8.5 – Modbus_Client SHALL cleanly close the TCP connection.
        """
        hass = _make_hass()
        entry = _make_entry()

        mock_client = MagicMock()
        mock_client.disconnect = AsyncMock()

        mock_coord = MagicMock()
        mock_coord.stop_refresh_task = MagicMock()

        hass.data[DOMAIN] = {
            entry.entry_id: {
                "coordinator": mock_coord,
                "client": mock_client,
            }
        }

        result = asyncio.run(async_unload_entry(hass, entry))

        assert result is True
        mock_client.disconnect.assert_called_once()

    def test_unload_calls_stop_refresh_task(self):
        """On unload, coordinator.stop_refresh_task() is called.

        Validates: Requirement 8.5 – integration cleans up background tasks on unload.
        """
        hass = _make_hass()
        entry = _make_entry()

        mock_client = MagicMock()
        mock_client.disconnect = AsyncMock()

        mock_coord = MagicMock()
        mock_coord.stop_refresh_task = MagicMock()

        hass.data[DOMAIN] = {
            entry.entry_id: {
                "coordinator": mock_coord,
                "client": mock_client,
            }
        }

        asyncio.run(async_unload_entry(hass, entry))

        mock_coord.stop_refresh_task.assert_called_once()

    def test_unload_removes_entry_from_hass_data(self):
        """After unload, the entry is removed from hass.data[DOMAIN]."""
        hass = _make_hass()
        entry = _make_entry()

        mock_client = MagicMock()
        mock_client.disconnect = AsyncMock()

        mock_coord = MagicMock()
        mock_coord.stop_refresh_task = MagicMock()

        hass.data[DOMAIN] = {
            entry.entry_id: {
                "coordinator": mock_coord,
                "client": mock_client,
            }
        }

        asyncio.run(async_unload_entry(hass, entry))

        assert entry.entry_id not in hass.data.get(DOMAIN, {})

    def test_unload_calls_async_unload_platforms(self):
        """async_unload_platforms is called with the correct platforms on teardown."""
        hass = _make_hass()
        entry = _make_entry()

        mock_client = MagicMock()
        mock_client.disconnect = AsyncMock()

        mock_coord = MagicMock()
        mock_coord.stop_refresh_task = MagicMock()

        hass.data[DOMAIN] = {
            entry.entry_id: {
                "coordinator": mock_coord,
                "client": mock_client,
            }
        }

        asyncio.run(async_unload_entry(hass, entry))

        hass.config_entries.async_unload_platforms.assert_called_once_with(
            entry, PLATFORMS
        )

    def test_unload_returns_false_when_platform_unload_fails(self):
        """If async_unload_platforms returns False, unload returns False."""
        hass = _make_hass()
        entry = _make_entry()
        hass.config_entries.async_unload_platforms = AsyncMock(return_value=False)

        mock_client = MagicMock()
        mock_client.disconnect = AsyncMock()

        mock_coord = MagicMock()
        mock_coord.stop_refresh_task = MagicMock()

        hass.data[DOMAIN] = {
            entry.entry_id: {
                "coordinator": mock_coord,
                "client": mock_client,
            }
        }

        result = asyncio.run(async_unload_entry(hass, entry))

        assert result is False
        # Client should NOT be disconnected if platform unload failed
        mock_client.disconnect.assert_not_called()
