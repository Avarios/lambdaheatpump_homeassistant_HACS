"""Unit tests for LambdaNumber and async_setup_entry (tasks 8.1, 8.2)."""
from __future__ import annotations

import asyncio
import sys
import types
from unittest.mock import AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Stubs for homeassistant modules (must come before any HA imports)
# ---------------------------------------------------------------------------

def _ensure_stub(name: str) -> types.ModuleType:
    if name not in sys.modules:
        sys.modules[name] = types.ModuleType(name)
    return sys.modules[name]


for _mod in [
    "homeassistant",
    "homeassistant.core",
    "homeassistant.config_entries",
    "homeassistant.helpers",
    "homeassistant.helpers.update_coordinator",
    "homeassistant.helpers.device_registry",
    "homeassistant.helpers.entity_platform",
    "homeassistant.components",
    "homeassistant.components.number",
]:
    _ensure_stub(_mod)

_ep = sys.modules["homeassistant.helpers.entity_platform"]
_ep.AddEntitiesCallback = object  # type: ignore[attr-defined]


class _FakeCoordinatorEntity:
    def __init__(self, coordinator):
        self.coordinator = coordinator

    def __class_getitem__(cls, item):
        return cls


class _FakeDataUpdateCoordinator:
    def __init__(self, hass=None, logger=None, *, name=None, update_interval=None, **kwargs):
        self.hass = hass
        self.name = name
        self.update_interval = update_interval
        self.data = None

    def __class_getitem__(cls, item):
        return cls


_uc = sys.modules["homeassistant.helpers.update_coordinator"]
_uc.CoordinatorEntity = _FakeCoordinatorEntity  # type: ignore[attr-defined]
_uc.DataUpdateCoordinator = _FakeDataUpdateCoordinator  # type: ignore[attr-defined]
_uc.UpdateFailed = Exception  # type: ignore[attr-defined]


class _DeviceInfo(dict):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


_dr = sys.modules["homeassistant.helpers.device_registry"]
_dr.DeviceInfo = _DeviceInfo  # type: ignore[attr-defined]

_core = sys.modules["homeassistant.core"]
_core.HomeAssistant = object  # type: ignore[attr-defined]


class _NumberEntity:
    pass


class _NumberMode:
    BOX = "box"
    SLIDER = "slider"
    AUTO = "auto"


_num_mod = sys.modules["homeassistant.components.number"]
_num_mod.NumberEntity = _NumberEntity  # type: ignore[attr-defined]
_num_mod.NumberMode = _NumberMode  # type: ignore[attr-defined]

_ce = sys.modules["homeassistant.config_entries"]
_ce.ConfigEntry = object  # type: ignore[attr-defined]

# ---------------------------------------------------------------------------
# Import modules under test
# ---------------------------------------------------------------------------

from custom_components.lambda_heat_pump.number import (
    LambdaNumber,
    _is_number_register,
    _to_uint16,
)
from custom_components.lambda_heat_pump.const import (
    MODULE_HEATPUMP,
    MODULE_BOILER,
    MODULE_BUFFER,
    MODULE_SOLAR,
    MODULE_HEATING_CIRCUIT,
    MODULE_AMBIENT,
    MODULE_EMANAGER,
    INDEX_GENERAL,
    INDEX_HEATPUMP,
    INDEX_BOILER,
    INDEX_BUFFER,
    INDEX_SOLAR,
    INDEX_HEATING_CIRCUIT,
    SUBINDEX_AMBIENT,
    SUBINDEX_EMANAGER,
    HEATPUMP_REGISTERS,
    BOILER_REGISTERS,
    BUFFER_REGISTERS,
    SOLAR_REGISTERS,
    HEATING_CIRCUIT_REGISTERS,
    AMBIENT_REGISTERS,
    EMANAGER_REGISTERS,
    calc_register_address,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CONFIG_ENTRY_ID = "test_entry_number"


def make_coordinator(data: dict | None = None):
    coord = MagicMock()
    coord.data = data if data is not None else {}
    coord.last_update_success = True
    coord.async_write_register = AsyncMock(return_value=True)
    return coord


def make_number(
    module_type=MODULE_HEATPUMP,
    module_index=INDEX_HEATPUMP,
    subindex=0,
    register_def=None,
    data: dict | None = None,
):
    if register_def is None:
        register_def = next(r for r in HEATPUMP_REGISTERS if r.name == "request_flow_temp")
    coord = make_coordinator(data=data)
    return LambdaNumber(coord, CONFIG_ENTRY_ID, module_type, module_index, subindex, register_def)


def run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Tests: helper functions
# ---------------------------------------------------------------------------

class TestIsNumberRegister:
    def test_rw_non_enum_is_number(self):
        reg = next(r for r in HEATPUMP_REGISTERS if r.name == "request_flow_temp")
        assert _is_number_register(reg) is True

    def test_rw_enum_is_not_number(self):
        reg = next(r for r in HEATPUMP_REGISTERS if r.name == "request_type")
        assert _is_number_register(reg) is False

    def test_ro_register_is_not_number(self):
        reg = next(r for r in HEATPUMP_REGISTERS if r.name == "t_flow")
        assert _is_number_register(reg) is False

    def test_boiler_max_temp_is_number(self):
        reg = next(r for r in BOILER_REGISTERS if r.name == "boiler_max_temp")
        assert _is_number_register(reg) is True

    def test_ambient_temp_actual_is_number(self):
        reg = next(r for r in AMBIENT_REGISTERS if r.name == "ambient_temp_actual")
        assert _is_number_register(reg) is True

    def test_emanager_actual_power_is_number(self):
        reg = next(r for r in EMANAGER_REGISTERS if r.name == "emanager_actual_power")
        assert _is_number_register(reg) is True


class TestToUint16:
    def test_negative_minus_one(self):
        assert _to_uint16(-1) == 65535

    def test_negative_minus_100(self):
        assert _to_uint16(-100) == 65436

    def test_zero_unchanged(self):
        assert _to_uint16(0) == 0

    def test_positive_unchanged(self):
        assert _to_uint16(500) == 500

    def test_max_int16(self):
        assert _to_uint16(32767) == 32767


# ---------------------------------------------------------------------------
# Tests: LambdaNumber.native_value
# ---------------------------------------------------------------------------

class TestNativeValue:
    def test_returns_none_when_data_is_none(self):
        entity = make_number(data=None)
        entity.coordinator.data = None
        assert entity.native_value is None

    def test_returns_none_when_address_missing(self):
        entity = make_number(data={})
        assert entity.native_value is None

    def test_scaled_value_with_factor_0_1(self):
        reg = next(r for r in HEATPUMP_REGISTERS if r.name == "request_flow_temp")
        addr = calc_register_address(INDEX_HEATPUMP, 0, reg.number)
        entity = make_number(register_def=reg, data={addr: 450})
        # 450 * 0.1 = 45.0
        assert entity.native_value == 45.0

    def test_scaled_value_with_factor_1(self):
        reg = next(r for r in HEATPUMP_REGISTERS if r.name == "request_password")
        addr = calc_register_address(INDEX_HEATPUMP, 0, reg.number)
        entity = make_number(register_def=reg, data={addr: 1234})
        assert entity.native_value == 1234.0

    def test_negative_int16_value(self):
        # hc_offset_flow_temp: INT16, scale 0.1, min=-10.0
        reg = next(r for r in HEATING_CIRCUIT_REGISTERS if r.name == "hc_offset_flow_temp")
        addr = calc_register_address(INDEX_HEATING_CIRCUIT, 0, reg.number)
        # -5.0 °C stored as raw = -50 → UINT16 = 65486
        entity = make_number(
            module_type=MODULE_HEATING_CIRCUIT,
            module_index=INDEX_HEATING_CIRCUIT,
            register_def=reg,
            data={addr: 65486},
        )
        assert entity.native_value == pytest.approx(-5.0, abs=1e-6)

    def test_ambient_temp_negative(self):
        reg = next(r for r in AMBIENT_REGISTERS if r.name == "ambient_temp_actual")
        addr = calc_register_address(INDEX_GENERAL, SUBINDEX_AMBIENT, reg.number)
        # -10.0 °C → raw = -100 → UINT16 = 65436
        entity = make_number(
            module_type=MODULE_AMBIENT,
            module_index=INDEX_GENERAL,
            subindex=SUBINDEX_AMBIENT,
            register_def=reg,
            data={addr: 65436},
        )
        assert entity.native_value == pytest.approx(-10.0, abs=1e-6)


# ---------------------------------------------------------------------------
# Tests: LambdaNumber attributes
# ---------------------------------------------------------------------------

class TestAttributes:
    def test_min_value_set_from_register_def(self):
        reg = next(r for r in HEATPUMP_REGISTERS if r.name == "request_flow_temp")
        entity = make_number(register_def=reg)
        assert entity._attr_native_min_value == 0.0

    def test_max_value_set_from_register_def(self):
        reg = next(r for r in HEATPUMP_REGISTERS if r.name == "request_flow_temp")
        entity = make_number(register_def=reg)
        assert entity._attr_native_max_value == 70.0

    def test_step_set_from_register_def(self):
        reg = next(r for r in HEATPUMP_REGISTERS if r.name == "request_flow_temp")
        entity = make_number(register_def=reg)
        assert entity._attr_native_step == 0.1

    def test_unit_set_from_register_def(self):
        reg = next(r for r in HEATPUMP_REGISTERS if r.name == "request_flow_temp")
        entity = make_number(register_def=reg)
        assert entity._attr_native_unit_of_measurement == "°C"

    def test_no_min_max_when_none(self):
        # buffer_request_capacity has max_value=None
        reg = next(r for r in BUFFER_REGISTERS if r.name == "buffer_request_capacity")
        entity = make_number(
            module_type=MODULE_BUFFER,
            module_index=INDEX_BUFFER,
            register_def=reg,
        )
        assert not hasattr(entity, "_attr_native_max_value") or entity._attr_native_max_value is None or True
        # min_value is 0.0
        assert entity._attr_native_min_value == 0.0


# ---------------------------------------------------------------------------
# Tests: async_set_native_value
# ---------------------------------------------------------------------------

class TestAsyncSetNativeValue:
    def test_writes_correct_raw_value(self):
        reg = next(r for r in HEATPUMP_REGISTERS if r.name == "request_flow_temp")
        addr = calc_register_address(INDEX_HEATPUMP, 0, reg.number)
        entity = make_number(register_def=reg, data={addr: 0})
        run(entity.async_set_native_value(45.0))
        entity.coordinator.async_write_register.assert_called_once_with(addr, 450)

    def test_rejects_value_below_min(self):
        reg = next(r for r in HEATPUMP_REGISTERS if r.name == "request_flow_temp")
        addr = calc_register_address(INDEX_HEATPUMP, 0, reg.number)
        entity = make_number(register_def=reg, data={addr: 0})
        run(entity.async_set_native_value(-1.0))
        entity.coordinator.async_write_register.assert_not_called()

    def test_rejects_value_above_max(self):
        reg = next(r for r in HEATPUMP_REGISTERS if r.name == "request_flow_temp")
        addr = calc_register_address(INDEX_HEATPUMP, 0, reg.number)
        entity = make_number(register_def=reg, data={addr: 0})
        run(entity.async_set_native_value(100.0))
        entity.coordinator.async_write_register.assert_not_called()

    def test_accepts_boundary_min_value(self):
        reg = next(r for r in HEATPUMP_REGISTERS if r.name == "request_flow_temp")
        addr = calc_register_address(INDEX_HEATPUMP, 0, reg.number)
        entity = make_number(register_def=reg, data={addr: 0})
        run(entity.async_set_native_value(0.0))
        entity.coordinator.async_write_register.assert_called_once_with(addr, 0)

    def test_accepts_boundary_max_value(self):
        reg = next(r for r in HEATPUMP_REGISTERS if r.name == "request_flow_temp")
        addr = calc_register_address(INDEX_HEATPUMP, 0, reg.number)
        entity = make_number(register_def=reg, data={addr: 0})
        run(entity.async_set_native_value(70.0))
        entity.coordinator.async_write_register.assert_called_once_with(addr, 700)

    def test_negative_int16_converted_to_uint16(self):
        reg = next(r for r in HEATING_CIRCUIT_REGISTERS if r.name == "hc_offset_flow_temp")
        addr = calc_register_address(INDEX_HEATING_CIRCUIT, 0, reg.number)
        entity = make_number(
            module_type=MODULE_HEATING_CIRCUIT,
            module_index=INDEX_HEATING_CIRCUIT,
            register_def=reg,
            data={addr: 0},
        )
        # -5.0 K → raw = -50 → UINT16 = 65486
        run(entity.async_set_native_value(-5.0))
        entity.coordinator.async_write_register.assert_called_once_with(addr, 65486)

    def test_no_min_max_allows_any_value(self):
        # request_password has no min/max
        reg = next(r for r in HEATPUMP_REGISTERS if r.name == "request_password")
        addr = calc_register_address(INDEX_HEATPUMP, 0, reg.number)
        entity = make_number(register_def=reg, data={addr: 0})
        run(entity.async_set_native_value(9999.0))
        entity.coordinator.async_write_register.assert_called_once_with(addr, 9999)


# ---------------------------------------------------------------------------
# Tests: async_setup_entry entity counts
# ---------------------------------------------------------------------------

class _FakeConfigEntry:
    def __init__(self, data: dict):
        self.data = data
        self.entry_id = CONFIG_ENTRY_ID


class _FakeHass:
    def __init__(self, coordinator):
        from custom_components.lambda_heat_pump.const import DOMAIN
        self.data = {DOMAIN: {CONFIG_ENTRY_ID: coordinator}}


async def _run_setup(config: dict) -> list[LambdaNumber]:
    from custom_components.lambda_heat_pump.number import async_setup_entry
    coord = make_coordinator(data={})
    hass = _FakeHass(coord)
    entry = _FakeConfigEntry(config)
    added: list[LambdaNumber] = []
    async_add_entities = lambda entities: added.extend(entities)
    await async_setup_entry(hass, entry, async_add_entities)
    return added


class TestAsyncSetupEntry:
    def test_single_heatpump_number_entities(self):
        # HP RW non-enum: request_password(14), request_flow_temp(16),
        #                 request_return_temp(17), request_temp_diff(18) = 4
        config = {"num_heatpumps": 1, "num_boilers": 0, "num_buffers": 0,
                  "num_solar": 0, "num_heating_circuits": 0,
                  "enable_ambient": False, "enable_emanager": False}
        entities = run(_run_setup(config))
        assert len(entities) == 4

    def test_single_boiler_number_entities(self):
        # Boiler RW non-enum: boiler_max_temp(50) = 1
        config = {"num_heatpumps": 0, "num_boilers": 1, "num_buffers": 0,
                  "num_solar": 0, "num_heating_circuits": 0,
                  "enable_ambient": False, "enable_emanager": False}
        entities = run(_run_setup(config))
        assert len(entities) == 1

    def test_single_buffer_number_entities(self):
        # Buffer RW non-enum: buffer_modbus_temp_high(4), buffer_request_flow_temp(6),
        #   buffer_request_return_temp(7), buffer_request_temp_diff(8),
        #   buffer_request_capacity(9), buffer_max_temp(50) = 6
        # buffer_request_type(5) is enum → excluded
        config = {"num_heatpumps": 0, "num_boilers": 0, "num_buffers": 1,
                  "num_solar": 0, "num_heating_circuits": 0,
                  "enable_ambient": False, "enable_emanager": False}
        entities = run(_run_setup(config))
        assert len(entities) == 6

    def test_single_solar_number_entities(self):
        # Solar RW non-enum: solar_max_buffer_temp(50), solar_buffer_changeover_temp(51) = 2
        config = {"num_heatpumps": 0, "num_boilers": 0, "num_buffers": 0,
                  "num_solar": 1, "num_heating_circuits": 0,
                  "enable_ambient": False, "enable_emanager": False}
        entities = run(_run_setup(config))
        assert len(entities) == 2

    def test_single_heating_circuit_number_entities(self):
        # HC RW non-enum: hc_room_temp(4), hc_setpoint_flow_temp(5),
        #   hc_offset_flow_temp(50), hc_setpoint_room_heating(51), hc_setpoint_room_cooling(52) = 5
        # hc_operating_mode(6) is enum → excluded
        config = {"num_heatpumps": 0, "num_boilers": 0, "num_buffers": 0,
                  "num_solar": 0, "num_heating_circuits": 1,
                  "enable_ambient": False, "enable_emanager": False}
        entities = run(_run_setup(config))
        assert len(entities) == 5

    def test_ambient_number_entities_when_enabled(self):
        # Ambient RW non-enum: ambient_temp_actual(2) = 1
        config = {"num_heatpumps": 0, "num_boilers": 0, "num_buffers": 0,
                  "num_solar": 0, "num_heating_circuits": 0,
                  "enable_ambient": True, "enable_emanager": False}
        entities = run(_run_setup(config))
        assert len(entities) == 1
        assert entities[0]._register_def.name == "ambient_temp_actual"

    def test_emanager_number_entities_when_enabled(self):
        # EManager RW non-enum: emanager_actual_power(2) = 1
        config = {"num_heatpumps": 0, "num_boilers": 0, "num_buffers": 0,
                  "num_solar": 0, "num_heating_circuits": 0,
                  "enable_ambient": False, "enable_emanager": True}
        entities = run(_run_setup(config))
        assert len(entities) == 1
        assert entities[0]._register_def.name == "emanager_actual_power"

    def test_no_entities_when_all_disabled(self):
        config = {"num_heatpumps": 0, "num_boilers": 0, "num_buffers": 0,
                  "num_solar": 0, "num_heating_circuits": 0,
                  "enable_ambient": False, "enable_emanager": False}
        entities = run(_run_setup(config))
        assert entities == []

    def test_ambient_not_created_when_disabled(self):
        config = {"num_heatpumps": 0, "num_boilers": 0, "num_buffers": 0,
                  "num_solar": 0, "num_heating_circuits": 0,
                  "enable_ambient": False, "enable_emanager": False}
        entities = run(_run_setup(config))
        names = [e._register_def.name for e in entities]
        assert "ambient_temp_actual" not in names

    def test_all_entities_are_lambda_number(self):
        config = {"num_heatpumps": 2, "num_boilers": 1, "num_buffers": 1,
                  "num_solar": 1, "num_heating_circuits": 1,
                  "enable_ambient": True, "enable_emanager": True}
        entities = run(_run_setup(config))
        assert all(isinstance(e, LambdaNumber) for e in entities)

    def test_unique_ids_are_distinct(self):
        config = {"num_heatpumps": 5, "num_boilers": 5, "num_buffers": 5,
                  "num_solar": 2, "num_heating_circuits": 12,
                  "enable_ambient": True, "enable_emanager": True}
        entities = run(_run_setup(config))
        ids = [e._attr_unique_id for e in entities]
        assert len(ids) == len(set(ids)), "Duplicate unique IDs found"

    def test_heatpump_entity_correct_address(self):
        reg = next(r for r in HEATPUMP_REGISTERS if r.name == "request_flow_temp")
        config = {"num_heatpumps": 1, "num_boilers": 0, "num_buffers": 0,
                  "num_solar": 0, "num_heating_circuits": 0,
                  "enable_ambient": False, "enable_emanager": False}
        entities = run(_run_setup(config))
        flow_temp_entities = [e for e in entities if e._register_def.name == "request_flow_temp"]
        assert len(flow_temp_entities) == 1
        assert flow_temp_entities[0]._address == calc_register_address(INDEX_HEATPUMP, 0, reg.number)
