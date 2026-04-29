"""Unit tests for LambdaSelect and async_setup_entry (tasks 9.1, 9.2)."""
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
    "homeassistant.components.select",
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


class _SelectEntity:
    pass


_sel_mod = sys.modules["homeassistant.components.select"]
_sel_mod.SelectEntity = _SelectEntity  # type: ignore[attr-defined]

_ce = sys.modules["homeassistant.config_entries"]
_ce.ConfigEntry = object  # type: ignore[attr-defined]

# ---------------------------------------------------------------------------
# Import modules under test
# ---------------------------------------------------------------------------

from custom_components.lambda_heat_pump.select import (
    LambdaSelect,
    _is_select_register,
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
    HP_REQUEST_TYPE,
    BUFFER_REQUEST_TYPE,
    HC_OPERATING_MODE,
    calc_register_address,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CONFIG_ENTRY_ID = "test_entry_select"


def make_coordinator(data: dict | None = None):
    coord = MagicMock()
    coord.data = data if data is not None else {}
    coord.last_update_success = True
    coord.async_write_register = AsyncMock(return_value=True)
    return coord


def make_select(
    module_type=MODULE_HEATPUMP,
    module_index=INDEX_HEATPUMP,
    subindex=0,
    register_def=None,
    data: dict | None = None,
):
    if register_def is None:
        register_def = next(r for r in HEATPUMP_REGISTERS if r.name == "request_type")
    coord = make_coordinator(data=data)
    return LambdaSelect(coord, CONFIG_ENTRY_ID, module_type, module_index, subindex, register_def)


def run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Tests: helper functions
# ---------------------------------------------------------------------------

class TestIsSelectRegister:
    def test_rw_enum_is_select(self):
        reg = next(r for r in HEATPUMP_REGISTERS if r.name == "request_type")
        assert _is_select_register(reg) is True

    def test_rw_non_enum_is_not_select(self):
        reg = next(r for r in HEATPUMP_REGISTERS if r.name == "request_flow_temp")
        assert _is_select_register(reg) is False

    def test_ro_enum_is_not_select(self):
        reg = next(r for r in HEATPUMP_REGISTERS if r.name == "hp_state")
        assert _is_select_register(reg) is False

    def test_buffer_request_type_is_select(self):
        reg = next(r for r in BUFFER_REGISTERS if r.name == "buffer_request_type")
        assert _is_select_register(reg) is True

    def test_hc_operating_mode_is_select(self):
        reg = next(r for r in HEATING_CIRCUIT_REGISTERS if r.name == "hc_operating_mode")
        assert _is_select_register(reg) is True

    def test_boiler_max_temp_is_not_select(self):
        reg = next(r for r in BOILER_REGISTERS if r.name == "boiler_max_temp")
        assert _is_select_register(reg) is False


class TestToUint16:
    def test_negative_minus_one(self):
        assert _to_uint16(-1) == 65535

    def test_zero_unchanged(self):
        assert _to_uint16(0) == 0

    def test_positive_unchanged(self):
        assert _to_uint16(3) == 3


# ---------------------------------------------------------------------------
# Tests: LambdaSelect.options
# ---------------------------------------------------------------------------

class TestOptions:
    def test_hp_request_type_options(self):
        entity = make_select()
        assert entity._attr_options == list(HP_REQUEST_TYPE.values())

    def test_buffer_request_type_options(self):
        reg = next(r for r in BUFFER_REGISTERS if r.name == "buffer_request_type")
        entity = make_select(
            module_type=MODULE_BUFFER,
            module_index=INDEX_BUFFER,
            register_def=reg,
        )
        assert entity._attr_options == list(BUFFER_REQUEST_TYPE.values())

    def test_hc_operating_mode_options(self):
        reg = next(r for r in HEATING_CIRCUIT_REGISTERS if r.name == "hc_operating_mode")
        entity = make_select(
            module_type=MODULE_HEATING_CIRCUIT,
            module_index=INDEX_HEATING_CIRCUIT,
            register_def=reg,
        )
        assert entity._attr_options == list(HC_OPERATING_MODE.values())


# ---------------------------------------------------------------------------
# Tests: LambdaSelect.current_option
# ---------------------------------------------------------------------------

class TestCurrentOption:
    def test_returns_none_when_data_is_none(self):
        entity = make_select()
        entity.coordinator.data = None
        assert entity.current_option is None

    def test_returns_none_when_address_missing(self):
        entity = make_select(data={})
        assert entity.current_option is None

    def test_known_value_maps_to_string(self):
        reg = next(r for r in HEATPUMP_REGISTERS if r.name == "request_type")
        addr = calc_register_address(INDEX_HEATPUMP, 0, reg.number)
        entity = make_select(register_def=reg, data={addr: 2})
        assert entity.current_option == "CENTRAL HEATING"

    def test_zero_maps_to_no_request(self):
        reg = next(r for r in HEATPUMP_REGISTERS if r.name == "request_type")
        addr = calc_register_address(INDEX_HEATPUMP, 0, reg.number)
        entity = make_select(register_def=reg, data={addr: 0})
        assert entity.current_option == "NO REQUEST"

    def test_unknown_value_returns_fallback_string(self):
        reg = next(r for r in HEATPUMP_REGISTERS if r.name == "request_type")
        addr = calc_register_address(INDEX_HEATPUMP, 0, reg.number)
        entity = make_select(register_def=reg, data={addr: 99})
        assert entity.current_option == "99"

    def test_buffer_request_type_negative_one(self):
        # BUFFER_REQUEST_TYPE has -1: "INVALID REQUEST"
        # Raw stored as UINT16: -1 → 65535
        reg = next(r for r in BUFFER_REGISTERS if r.name == "buffer_request_type")
        addr = calc_register_address(INDEX_BUFFER, 0, reg.number)
        entity = make_select(
            module_type=MODULE_BUFFER,
            module_index=INDEX_BUFFER,
            register_def=reg,
            data={addr: 65535},  # -1 as UINT16
        )
        assert entity.current_option == "INVALID REQUEST"

    def test_hc_operating_mode_automatic(self):
        reg = next(r for r in HEATING_CIRCUIT_REGISTERS if r.name == "hc_operating_mode")
        addr = calc_register_address(INDEX_HEATING_CIRCUIT, 0, reg.number)
        entity = make_select(
            module_type=MODULE_HEATING_CIRCUIT,
            module_index=INDEX_HEATING_CIRCUIT,
            register_def=reg,
            data={addr: 2},
        )
        assert entity.current_option == "AUTOMATIC"


# ---------------------------------------------------------------------------
# Tests: async_select_option
# ---------------------------------------------------------------------------

class TestAsyncSelectOption:
    def test_writes_correct_raw_value(self):
        reg = next(r for r in HEATPUMP_REGISTERS if r.name == "request_type")
        addr = calc_register_address(INDEX_HEATPUMP, 0, reg.number)
        entity = make_select(register_def=reg, data={addr: 0})
        run(entity.async_select_option("CENTRAL HEATING"))
        entity.coordinator.async_write_register.assert_called_once_with(addr, 2)

    def test_writes_zero_for_no_request(self):
        reg = next(r for r in HEATPUMP_REGISTERS if r.name == "request_type")
        addr = calc_register_address(INDEX_HEATPUMP, 0, reg.number)
        entity = make_select(register_def=reg, data={addr: 2})
        run(entity.async_select_option("NO REQUEST"))
        entity.coordinator.async_write_register.assert_called_once_with(addr, 0)

    def test_unknown_option_does_not_write(self):
        reg = next(r for r in HEATPUMP_REGISTERS if r.name == "request_type")
        addr = calc_register_address(INDEX_HEATPUMP, 0, reg.number)
        entity = make_select(register_def=reg, data={addr: 0})
        run(entity.async_select_option("NONEXISTENT OPTION"))
        entity.coordinator.async_write_register.assert_not_called()

    def test_buffer_invalid_request_writes_uint16(self):
        # "INVALID REQUEST" → raw = -1 → UINT16 = 65535
        reg = next(r for r in BUFFER_REGISTERS if r.name == "buffer_request_type")
        addr = calc_register_address(INDEX_BUFFER, 0, reg.number)
        entity = make_select(
            module_type=MODULE_BUFFER,
            module_index=INDEX_BUFFER,
            register_def=reg,
            data={addr: 0},
        )
        run(entity.async_select_option("INVALID REQUEST"))
        entity.coordinator.async_write_register.assert_called_once_with(addr, 65535)

    def test_hc_operating_mode_writes_correct_value(self):
        reg = next(r for r in HEATING_CIRCUIT_REGISTERS if r.name == "hc_operating_mode")
        addr = calc_register_address(INDEX_HEATING_CIRCUIT, 0, reg.number)
        entity = make_select(
            module_type=MODULE_HEATING_CIRCUIT,
            module_index=INDEX_HEATING_CIRCUIT,
            register_def=reg,
            data={addr: 0},
        )
        run(entity.async_select_option("FLOORDRY"))
        entity.coordinator.async_write_register.assert_called_once_with(addr, 7)


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


async def _run_setup(config: dict) -> list[LambdaSelect]:
    from custom_components.lambda_heat_pump.select import async_setup_entry
    coord = make_coordinator(data={})
    hass = _FakeHass(coord)
    entry = _FakeConfigEntry(config)
    added: list[LambdaSelect] = []
    async_add_entities = lambda entities: added.extend(entities)
    await async_setup_entry(hass, entry, async_add_entities)
    return added


class TestAsyncSetupEntry:
    def test_single_heatpump_select_entities(self):
        # HP RW enum: request_type(15) = 1
        config = {"num_heatpumps": 1, "num_boilers": 0, "num_buffers": 0,
                  "num_solar": 0, "num_heating_circuits": 0,
                  "enable_ambient": False, "enable_emanager": False}
        entities = run(_run_setup(config))
        assert len(entities) == 1
        assert entities[0]._register_def.name == "request_type"

    def test_single_buffer_select_entities(self):
        # Buffer RW enum: buffer_request_type(5) = 1
        config = {"num_heatpumps": 0, "num_boilers": 0, "num_buffers": 1,
                  "num_solar": 0, "num_heating_circuits": 0,
                  "enable_ambient": False, "enable_emanager": False}
        entities = run(_run_setup(config))
        assert len(entities) == 1
        assert entities[0]._register_def.name == "buffer_request_type"

    def test_single_heating_circuit_select_entities(self):
        # HC RW enum: hc_operating_mode(6) = 1
        config = {"num_heatpumps": 0, "num_boilers": 0, "num_buffers": 0,
                  "num_solar": 0, "num_heating_circuits": 1,
                  "enable_ambient": False, "enable_emanager": False}
        entities = run(_run_setup(config))
        assert len(entities) == 1
        assert entities[0]._register_def.name == "hc_operating_mode"

    def test_boiler_has_no_select_entities(self):
        config = {"num_heatpumps": 0, "num_boilers": 1, "num_buffers": 0,
                  "num_solar": 0, "num_heating_circuits": 0,
                  "enable_ambient": False, "enable_emanager": False}
        entities = run(_run_setup(config))
        assert entities == []

    def test_solar_has_no_select_entities(self):
        config = {"num_heatpumps": 0, "num_boilers": 0, "num_buffers": 0,
                  "num_solar": 1, "num_heating_circuits": 0,
                  "enable_ambient": False, "enable_emanager": False}
        entities = run(_run_setup(config))
        assert entities == []

    def test_ambient_has_no_select_entities(self):
        config = {"num_heatpumps": 0, "num_boilers": 0, "num_buffers": 0,
                  "num_solar": 0, "num_heating_circuits": 0,
                  "enable_ambient": True, "enable_emanager": False}
        entities = run(_run_setup(config))
        assert entities == []

    def test_emanager_has_no_select_entities(self):
        config = {"num_heatpumps": 0, "num_boilers": 0, "num_buffers": 0,
                  "num_solar": 0, "num_heating_circuits": 0,
                  "enable_ambient": False, "enable_emanager": True}
        entities = run(_run_setup(config))
        assert entities == []

    def test_no_entities_when_all_disabled(self):
        config = {"num_heatpumps": 0, "num_boilers": 0, "num_buffers": 0,
                  "num_solar": 0, "num_heating_circuits": 0,
                  "enable_ambient": False, "enable_emanager": False}
        entities = run(_run_setup(config))
        assert entities == []

    def test_multiple_heatpumps_create_multiple_selects(self):
        config = {"num_heatpumps": 3, "num_boilers": 0, "num_buffers": 0,
                  "num_solar": 0, "num_heating_circuits": 0,
                  "enable_ambient": False, "enable_emanager": False}
        entities = run(_run_setup(config))
        assert len(entities) == 3

    def test_combined_modules_correct_count(self):
        # 2 HP (2) + 2 buffers (2) + 3 HC (3) = 7
        config = {"num_heatpumps": 2, "num_boilers": 1, "num_buffers": 2,
                  "num_solar": 1, "num_heating_circuits": 3,
                  "enable_ambient": True, "enable_emanager": True}
        entities = run(_run_setup(config))
        assert len(entities) == 7

    def test_all_entities_are_lambda_select(self):
        config = {"num_heatpumps": 2, "num_boilers": 1, "num_buffers": 2,
                  "num_solar": 1, "num_heating_circuits": 3,
                  "enable_ambient": True, "enable_emanager": True}
        entities = run(_run_setup(config))
        assert all(isinstance(e, LambdaSelect) for e in entities)

    def test_unique_ids_are_distinct(self):
        config = {"num_heatpumps": 5, "num_boilers": 5, "num_buffers": 5,
                  "num_solar": 2, "num_heating_circuits": 12,
                  "enable_ambient": True, "enable_emanager": True}
        entities = run(_run_setup(config))
        ids = [e._attr_unique_id for e in entities]
        assert len(ids) == len(set(ids)), "Duplicate unique IDs found"

    def test_heatpump_select_correct_address(self):
        reg = next(r for r in HEATPUMP_REGISTERS if r.name == "request_type")
        config = {"num_heatpumps": 1, "num_boilers": 0, "num_buffers": 0,
                  "num_solar": 0, "num_heating_circuits": 0,
                  "enable_ambient": False, "enable_emanager": False}
        entities = run(_run_setup(config))
        assert entities[0]._address == calc_register_address(INDEX_HEATPUMP, 0, reg.number)

    def test_buffer_select_correct_address(self):
        reg = next(r for r in BUFFER_REGISTERS if r.name == "buffer_request_type")
        config = {"num_heatpumps": 0, "num_boilers": 0, "num_buffers": 1,
                  "num_solar": 0, "num_heating_circuits": 0,
                  "enable_ambient": False, "enable_emanager": False}
        entities = run(_run_setup(config))
        assert entities[0]._address == calc_register_address(INDEX_BUFFER, 0, reg.number)
