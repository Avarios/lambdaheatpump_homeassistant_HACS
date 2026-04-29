"""Unit tests for config_flow.py – LambdaHeatPumpConfigFlow validation logic.

These tests exercise _validate_user_input and _is_valid_host directly,
without requiring a running Home Assistant instance.
"""
from __future__ import annotations

import sys
import types

# ---------------------------------------------------------------------------
# Minimal stubs so config_flow.py can be imported without a full HA install
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

# ConfigFlow base class stub
_ce = sys.modules["homeassistant.config_entries"]
if not hasattr(_ce, "ConfigFlow"):
    class _ConfigFlowStub:
        def __init_subclass__(cls, domain: str = "", **kwargs):
            super().__init_subclass__(**kwargs)

        async def async_set_unique_id(self, uid: str) -> None:
            self._unique_id = uid

        def _abort_if_unique_id_configured(self) -> None:
            pass

        def async_show_form(self, *, step_id, data_schema, errors=None):
            return {"type": "form", "step_id": step_id, "errors": errors or {}}

        def async_create_entry(self, *, title, data):
            return {"type": "create_entry", "title": title, "data": data}

        def async_update_reload_and_abort(self, entry, *, data):
            return {"type": "abort", "reason": "reconfigure_successful", "data": data}

    _ce.ConfigFlow = _ConfigFlowStub  # type: ignore[attr-defined]

if not hasattr(_ce, "FlowResult"):
    _ce.FlowResult = dict  # type: ignore[attr-defined]

if not hasattr(_ce, "OptionsFlow"):
    class _OptionsFlowStub:
        def async_show_form(self, *, step_id, data_schema, errors=None):
            return {"type": "form", "step_id": step_id, "errors": errors or {}}

        def async_create_entry(self, *, title="", data):
            return {"type": "create_entry", "title": title, "data": data}

    _ce.OptionsFlow = _OptionsFlowStub  # type: ignore[attr-defined]

if not hasattr(_ce, "ConfigEntry"):
    class _ConfigEntryStub:
        def __init__(self, data=None, options=None):
            self.data = data or {}
            self.options = options or {}

    _ce.ConfigEntry = _ConfigEntryStub  # type: ignore[attr-defined]

_const = sys.modules["homeassistant.const"]
_const.CONF_HOST = "host"  # type: ignore[attr-defined]
_const.CONF_PORT = "port"  # type: ignore[attr-defined]
_const.CONF_SCAN_INTERVAL = "scan_interval"  # type: ignore[attr-defined]

# ---------------------------------------------------------------------------

import pytest

from custom_components.lambda_heat_pump.config_flow import (
    _is_valid_host,
    _validate_user_input,
    LambdaHeatPumpOptionsFlow,
)
from custom_components.lambda_heat_pump.const import (
    CONF_ENABLE_AMBIENT,
    CONF_ENABLE_EMANAGER,
    CONF_NUM_BOILERS,
    CONF_NUM_BUFFERS,
    CONF_NUM_HEATPUMPS,
    CONF_NUM_HEATING_CIRCUITS,
    CONF_NUM_SOLAR,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_INPUT: dict = {
    "host": "192.168.1.100",
    "port": 502,
    CONF_NUM_HEATPUMPS: 1,
    CONF_NUM_HEATING_CIRCUITS: 0,
    CONF_NUM_BOILERS: 0,
    CONF_NUM_BUFFERS: 0,
    CONF_NUM_SOLAR: 0,
    CONF_ENABLE_AMBIENT: False,
    CONF_ENABLE_EMANAGER: False,
    "scan_interval": 30,
}


def _input(**overrides) -> dict:
    return {**VALID_INPUT, **overrides}


# ---------------------------------------------------------------------------
# _is_valid_host
# ---------------------------------------------------------------------------

class TestIsValidHost:
    def test_valid_ipv4(self):
        assert _is_valid_host("192.168.1.1")

    def test_valid_ipv4_loopback(self):
        assert _is_valid_host("127.0.0.1")

    def test_valid_ipv6(self):
        assert _is_valid_host("::1")
        assert _is_valid_host("2001:db8::1")

    def test_valid_hostname(self):
        assert _is_valid_host("myheatpump")
        assert _is_valid_host("heat-pump.local")
        assert _is_valid_host("lambda.example.com")

    def test_empty_string(self):
        assert not _is_valid_host("")

    def test_invalid_hostname_spaces(self):
        assert not _is_valid_host("my host")

    def test_invalid_hostname_leading_dash(self):
        assert not _is_valid_host("-invalid.host")


# ---------------------------------------------------------------------------
# _validate_user_input – valid input
# ---------------------------------------------------------------------------

class TestValidateUserInputValid:
    def test_minimal_valid(self):
        assert _validate_user_input(VALID_INPUT) == {}

    def test_max_values(self):
        errors = _validate_user_input(_input(
            port=65535,
            **{
                CONF_NUM_HEATPUMPS: 5,
                CONF_NUM_HEATING_CIRCUITS: 12,
                CONF_NUM_BOILERS: 5,
                CONF_NUM_BUFFERS: 5,
                CONF_NUM_SOLAR: 2,
                "scan_interval": 300,
            }
        ))
        assert errors == {}

    def test_boundary_min_values(self):
        errors = _validate_user_input(_input(
            port=1,
            **{
                CONF_NUM_HEATPUMPS: 1,
                CONF_NUM_HEATING_CIRCUITS: 0,
                CONF_NUM_BOILERS: 0,
                CONF_NUM_BUFFERS: 0,
                CONF_NUM_SOLAR: 0,
                "scan_interval": 10,
            }
        ))
        assert errors == {}

    def test_hostname_accepted(self):
        errors = _validate_user_input(_input(host="lambda.local"))
        assert errors == {}


# ---------------------------------------------------------------------------
# _validate_user_input – invalid host
# ---------------------------------------------------------------------------

class TestValidateHost:
    def test_empty_host(self):
        errors = _validate_user_input(_input(host=""))
        assert "host" in errors
        assert errors["host"] == "invalid_host"

    def test_host_with_spaces(self):
        errors = _validate_user_input(_input(host="my host"))
        assert errors.get("host") == "invalid_host"


# ---------------------------------------------------------------------------
# _validate_user_input – invalid port
# ---------------------------------------------------------------------------

class TestValidatePort:
    def test_port_zero(self):
        errors = _validate_user_input(_input(port=0))
        assert errors.get("port") == "invalid_port"

    def test_port_too_high(self):
        errors = _validate_user_input(_input(port=65536))
        assert errors.get("port") == "invalid_port"

    def test_port_negative(self):
        errors = _validate_user_input(_input(port=-1))
        assert errors.get("port") == "invalid_port"


# ---------------------------------------------------------------------------
# _validate_user_input – num_heatpumps
# ---------------------------------------------------------------------------

class TestValidateNumHeatpumps:
    def test_zero_rejected(self):
        errors = _validate_user_input(_input(**{CONF_NUM_HEATPUMPS: 0}))
        assert errors.get(CONF_NUM_HEATPUMPS) == "invalid_num_heatpumps"

    def test_six_rejected(self):
        errors = _validate_user_input(_input(**{CONF_NUM_HEATPUMPS: 6}))
        assert errors.get(CONF_NUM_HEATPUMPS) == "invalid_num_heatpumps"

    def test_one_accepted(self):
        assert _validate_user_input(_input(**{CONF_NUM_HEATPUMPS: 1})) == {}

    def test_five_accepted(self):
        assert _validate_user_input(_input(**{CONF_NUM_HEATPUMPS: 5})) == {}


# ---------------------------------------------------------------------------
# _validate_user_input – num_heating_circuits
# ---------------------------------------------------------------------------

class TestValidateNumHeatingCircuits:
    def test_negative_rejected(self):
        errors = _validate_user_input(_input(**{CONF_NUM_HEATING_CIRCUITS: -1}))
        assert errors.get(CONF_NUM_HEATING_CIRCUITS) == "invalid_num_heating_circuits"

    def test_thirteen_rejected(self):
        errors = _validate_user_input(_input(**{CONF_NUM_HEATING_CIRCUITS: 13}))
        assert errors.get(CONF_NUM_HEATING_CIRCUITS) == "invalid_num_heating_circuits"

    def test_zero_accepted(self):
        assert _validate_user_input(_input(**{CONF_NUM_HEATING_CIRCUITS: 0})) == {}

    def test_twelve_accepted(self):
        assert _validate_user_input(_input(**{CONF_NUM_HEATING_CIRCUITS: 12})) == {}


# ---------------------------------------------------------------------------
# _validate_user_input – num_boilers
# ---------------------------------------------------------------------------

class TestValidateNumBoilers:
    def test_negative_rejected(self):
        errors = _validate_user_input(_input(**{CONF_NUM_BOILERS: -1}))
        assert errors.get(CONF_NUM_BOILERS) == "invalid_num_boilers"

    def test_six_rejected(self):
        errors = _validate_user_input(_input(**{CONF_NUM_BOILERS: 6}))
        assert errors.get(CONF_NUM_BOILERS) == "invalid_num_boilers"

    def test_zero_accepted(self):
        assert _validate_user_input(_input(**{CONF_NUM_BOILERS: 0})) == {}

    def test_five_accepted(self):
        assert _validate_user_input(_input(**{CONF_NUM_BOILERS: 5})) == {}


# ---------------------------------------------------------------------------
# _validate_user_input – num_buffers
# ---------------------------------------------------------------------------

class TestValidateNumBuffers:
    def test_negative_rejected(self):
        errors = _validate_user_input(_input(**{CONF_NUM_BUFFERS: -1}))
        assert errors.get(CONF_NUM_BUFFERS) == "invalid_num_buffers"

    def test_six_rejected(self):
        errors = _validate_user_input(_input(**{CONF_NUM_BUFFERS: 6}))
        assert errors.get(CONF_NUM_BUFFERS) == "invalid_num_buffers"

    def test_zero_accepted(self):
        assert _validate_user_input(_input(**{CONF_NUM_BUFFERS: 0})) == {}

    def test_five_accepted(self):
        assert _validate_user_input(_input(**{CONF_NUM_BUFFERS: 5})) == {}


# ---------------------------------------------------------------------------
# _validate_user_input – num_solar
# ---------------------------------------------------------------------------

class TestValidateNumSolar:
    def test_negative_rejected(self):
        errors = _validate_user_input(_input(**{CONF_NUM_SOLAR: -1}))
        assert errors.get(CONF_NUM_SOLAR) == "invalid_num_solar"

    def test_three_rejected(self):
        errors = _validate_user_input(_input(**{CONF_NUM_SOLAR: 3}))
        assert errors.get(CONF_NUM_SOLAR) == "invalid_num_solar"

    def test_zero_accepted(self):
        assert _validate_user_input(_input(**{CONF_NUM_SOLAR: 0})) == {}

    def test_two_accepted(self):
        assert _validate_user_input(_input(**{CONF_NUM_SOLAR: 2})) == {}


# ---------------------------------------------------------------------------
# _validate_user_input – scan_interval
# ---------------------------------------------------------------------------

class TestValidateScanInterval:
    def test_nine_rejected(self):
        errors = _validate_user_input(_input(scan_interval=9))
        assert errors.get("scan_interval") == "invalid_scan_interval"

    def test_three_hundred_one_rejected(self):
        errors = _validate_user_input(_input(scan_interval=301))
        assert errors.get("scan_interval") == "invalid_scan_interval"

    def test_ten_accepted(self):
        assert _validate_user_input(_input(scan_interval=10)) == {}

    def test_three_hundred_accepted(self):
        assert _validate_user_input(_input(scan_interval=300)) == {}


# ---------------------------------------------------------------------------
# Multiple errors at once
# ---------------------------------------------------------------------------

class TestMultipleErrors:
    def test_multiple_invalid_fields(self):
        bad_input = {
            "host": "",
            "port": 0,
            CONF_NUM_HEATPUMPS: 0,
            CONF_NUM_HEATING_CIRCUITS: 13,
            CONF_NUM_BOILERS: 6,
            CONF_NUM_BUFFERS: 6,
            CONF_NUM_SOLAR: 3,
            CONF_ENABLE_AMBIENT: False,
            CONF_ENABLE_EMANAGER: False,
            "scan_interval": 5,
        }
        errors = _validate_user_input(bad_input)
        assert "host" in errors
        assert "port" in errors
        assert CONF_NUM_HEATPUMPS in errors
        assert CONF_NUM_HEATING_CIRCUITS in errors
        assert CONF_NUM_BOILERS in errors
        assert CONF_NUM_BUFFERS in errors
        assert CONF_NUM_SOLAR in errors
        assert "scan_interval" in errors


# ---------------------------------------------------------------------------
# LambdaHeatPumpOptionsFlow
# ---------------------------------------------------------------------------

import asyncio
from unittest.mock import patch, AsyncMock


def _make_entry(data=None, options=None):
    """Create a minimal ConfigEntry-like stub."""
    class _FakeEntry:
        pass
    entry = _FakeEntry()
    entry.data = data or {}
    entry.options = options or {}
    return entry


class TestOptionsFlowInit:
    """Tests for LambdaHeatPumpOptionsFlow.async_step_init."""

    def test_shows_form_with_no_input(self):
        """Without user_input the form is shown pre-filled from entry data."""
        entry = _make_entry(data=VALID_INPUT)
        flow = LambdaHeatPumpOptionsFlow(entry)
        result = asyncio.run(flow.async_step_init(user_input=None))
        assert result["type"] == "form"
        assert result["step_id"] == "init"
        assert result["errors"] == {}

    def test_prefills_from_entry_data(self):
        """The schema defaults should reflect the stored config entry values."""
        custom_data = {**VALID_INPUT, "port": 1234}
        entry = _make_entry(data=custom_data)
        flow = LambdaHeatPumpOptionsFlow(entry)
        result = asyncio.run(flow.async_step_init(user_input=None))
        assert result["type"] == "form"

    def test_options_override_data(self):
        """Options values take precedence over data values when pre-filling."""
        entry = _make_entry(
            data=VALID_INPUT,
            options={"port": 9999},
        )
        flow = LambdaHeatPumpOptionsFlow(entry)
        result = asyncio.run(flow.async_step_init(user_input=None))
        assert result["type"] == "form"

    def test_validation_errors_shown(self):
        """Invalid user_input triggers validation errors and re-shows the form."""
        entry = _make_entry(data=VALID_INPUT)
        flow = LambdaHeatPumpOptionsFlow(entry)
        bad_input = {**VALID_INPUT, "port": 0}
        result = asyncio.run(flow.async_step_init(user_input=bad_input))
        assert result["type"] == "form"
        assert "port" in result["errors"]

    def test_host_stripped_before_validation(self):
        """Whitespace around the host is stripped before validation."""
        entry = _make_entry(data=VALID_INPUT)
        flow = LambdaHeatPumpOptionsFlow(entry)
        padded_input = {**VALID_INPUT, "host": "  192.168.1.100  "}

        with patch(
            "custom_components.lambda_heat_pump.config_flow.LambdaModbusClient"
        ) as MockClient:
            instance = MockClient.return_value
            instance.connect = AsyncMock(return_value=True)
            instance.disconnect = AsyncMock()
            result = asyncio.run(flow.async_step_init(user_input=padded_input))

        # Should not have a host error (whitespace was stripped)
        assert "host" not in result.get("errors", {})

    def test_successful_submission_creates_entry(self):
        """Valid input with successful connection creates an options entry."""
        entry = _make_entry(data=VALID_INPUT)
        flow = LambdaHeatPumpOptionsFlow(entry)

        with patch(
            "custom_components.lambda_heat_pump.config_flow.LambdaModbusClient"
        ) as MockClient:
            instance = MockClient.return_value
            instance.connect = AsyncMock(return_value=True)
            instance.disconnect = AsyncMock()
            result = asyncio.run(flow.async_step_init(user_input=VALID_INPUT))

        assert result["type"] == "create_entry"
        assert result["data"] == VALID_INPUT

    def test_cannot_connect_shows_base_error(self):
        """A failed connection test sets errors['base'] = 'cannot_connect'."""
        entry = _make_entry(data=VALID_INPUT)
        flow = LambdaHeatPumpOptionsFlow(entry)

        with patch(
            "custom_components.lambda_heat_pump.config_flow.LambdaModbusClient"
        ) as MockClient:
            instance = MockClient.return_value
            instance.connect = AsyncMock(return_value=False)
            result = asyncio.run(flow.async_step_init(user_input=VALID_INPUT))

        assert result["type"] == "form"
        assert result["errors"].get("base") == "cannot_connect"
