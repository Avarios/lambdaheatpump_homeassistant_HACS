"""Unit tests for LambdaBinarySensor and async_setup_entry (task 7.1)."""
from __future__ import annotations

import asyncio
import sys
import types
from unittest.mock import MagicMock

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
    "homeassistant.components.binary_sensor",
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


class _BinarySensorEntity:
    pass


_bs_mod = sys.modules["homeassistant.components.binary_sensor"]
_bs_mod.BinarySensorEntity = _BinarySensorEntity  # type: ignore[attr-defined]

_ce = sys.modules["homeassistant.config_entries"]
_ce.ConfigEntry = object  # type: ignore[attr-defined]

# ---------------------------------------------------------------------------
# Import modules under test
# ---------------------------------------------------------------------------

from custom_components.lambda_heat_pump.binary_sensor import (
    LambdaBinarySensor,
    _is_binary_register,
    _BINARY_REGISTER_NAMES,
)
from custom_components.lambda_heat_pump.const import (
    MODULE_HEATPUMP,
    MODULE_BOILER,
    INDEX_HEATPUMP,
    INDEX_BOILER,
    HEATPUMP_REGISTERS,
    BOILER_REGISTERS,
    calc_register_address,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CONFIG_ENTRY_ID = "test_entry_binary"


def make_coordinator(data: dict | None = None):
    coord = MagicMock()
    coord.data = data if data is not None else {}
    coord.last_update_success = True
    return coord


def make_binary_sensor(
    module_type=MODULE_HEATPUMP,
    module_index=INDEX_HEATPUMP,
    subindex=0,
    register_def=None,
    data: dict | None = None,
):
    if register_def is None:
        register_def = next(r for r in HEATPUMP_REGISTERS if r.name == "relay_2nd_stage")
    coord = make_coordinator(data=data)
    return LambdaBinarySensor(coord, CONFIG_ENTRY_ID, module_type, module_index, subindex, register_def)


# ---------------------------------------------------------------------------
# Tests: _is_binary_register
# ---------------------------------------------------------------------------

class TestIsBinaryRegister:
    def test_relay_2nd_stage_is_binary(self):
        reg = next(r for r in HEATPUMP_REGISTERS if r.name == "relay_2nd_stage")
        assert _is_binary_register(reg) is True

    def test_boiler_pump_state_is_binary(self):
        reg = next(r for r in BOILER_REGISTERS if r.name == "boiler_pump_state")
        assert _is_binary_register(reg) is True

    def test_numeric_ro_register_is_not_binary(self):
        reg = next(r for r in HEATPUMP_REGISTERS if r.name == "t_flow")
        assert _is_binary_register(reg) is False

    def test_rw_register_is_not_binary(self):
        reg = next(r for r in HEATPUMP_REGISTERS if r.name == "request_password")
        assert _is_binary_register(reg) is False

    def test_enum_ro_register_is_not_binary(self):
        reg = next(r for r in HEATPUMP_REGISTERS if r.name == "hp_error_state")
        assert _is_binary_register(reg) is False


# ---------------------------------------------------------------------------
# Tests: LambdaBinarySensor.is_on
# ---------------------------------------------------------------------------

class TestIsOn:
    def test_is_on_when_value_is_1(self):
        reg = next(r for r in HEATPUMP_REGISTERS if r.name == "relay_2nd_stage")
        addr = calc_register_address(INDEX_HEATPUMP, 0, reg.number)
        sensor = make_binary_sensor(data={addr: 1})
        assert sensor.is_on is True

    def test_is_off_when_value_is_0(self):
        reg = next(r for r in HEATPUMP_REGISTERS if r.name == "relay_2nd_stage")
        addr = calc_register_address(INDEX_HEATPUMP, 0, reg.number)
        sensor = make_binary_sensor(data={addr: 0})
        assert sensor.is_on is False

    def test_is_on_when_value_is_nonzero(self):
        reg = next(r for r in HEATPUMP_REGISTERS if r.name == "relay_2nd_stage")
        addr = calc_register_address(INDEX_HEATPUMP, 0, reg.number)
        sensor = make_binary_sensor(data={addr: 5})
        assert sensor.is_on is True

    def test_returns_none_when_data_is_none(self):
        sensor = make_binary_sensor(data=None)
        sensor.coordinator.data = None
        assert sensor.is_on is None

    def test_returns_none_when_address_missing(self):
        sensor = make_binary_sensor(data={})
        assert sensor.is_on is None

    def test_boiler_pump_state_on(self):
        reg = next(r for r in BOILER_REGISTERS if r.name == "boiler_pump_state")
        addr = calc_register_address(INDEX_BOILER, 0, reg.number)
        sensor = make_binary_sensor(
            module_type=MODULE_BOILER,
            module_index=INDEX_BOILER,
            register_def=reg,
            data={addr: 1},
        )
        assert sensor.is_on is True

    def test_boiler_pump_state_off(self):
        reg = next(r for r in BOILER_REGISTERS if r.name == "boiler_pump_state")
        addr = calc_register_address(INDEX_BOILER, 0, reg.number)
        sensor = make_binary_sensor(
            module_type=MODULE_BOILER,
            module_index=INDEX_BOILER,
            register_def=reg,
            data={addr: 0},
        )
        assert sensor.is_on is False

    def test_second_heatpump_uses_correct_address(self):
        reg = next(r for r in HEATPUMP_REGISTERS if r.name == "relay_2nd_stage")
        addr_hp2 = calc_register_address(INDEX_HEATPUMP, 1, reg.number)
        sensor = make_binary_sensor(subindex=1, data={addr_hp2: 1})
        assert sensor.is_on is True


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


async def _run_setup(config: dict) -> list[LambdaBinarySensor]:
    from custom_components.lambda_heat_pump.binary_sensor import async_setup_entry
    coord = make_coordinator(data={})
    hass = _FakeHass(coord)
    entry = _FakeConfigEntry(config)
    added: list[LambdaBinarySensor] = []
    async_add_entities = lambda entities: added.extend(entities)
    await async_setup_entry(hass, entry, async_add_entities)
    return added


def run(coro):
    return asyncio.run(coro)


class TestAsyncSetupEntry:
    def test_single_heatpump_creates_one_binary_sensor(self):
        # HP has exactly 1 binary register: relay_2nd_stage
        config = {
            "num_heatpumps": 1,
            "num_boilers": 0,
        }
        entities = run(_run_setup(config))
        assert len(entities) == 1
        assert entities[0]._register_def.name == "relay_2nd_stage"

    def test_two_heatpumps_creates_two_binary_sensors(self):
        config = {"num_heatpumps": 2, "num_boilers": 0}
        entities = run(_run_setup(config))
        assert len(entities) == 2

    def test_single_boiler_creates_one_binary_sensor(self):
        # Boiler has exactly 1 binary register: boiler_pump_state
        config = {"num_heatpumps": 0, "num_boilers": 1}
        entities = run(_run_setup(config))
        assert len(entities) == 1
        assert entities[0]._register_def.name == "boiler_pump_state"

    def test_no_entities_when_counts_zero(self):
        config = {"num_heatpumps": 0, "num_boilers": 0}
        entities = run(_run_setup(config))
        assert entities == []

    def test_combined_hp_and_boiler(self):
        config = {"num_heatpumps": 2, "num_boilers": 3}
        entities = run(_run_setup(config))
        # 2 HP × 1 binary + 3 boilers × 1 binary = 5
        assert len(entities) == 5

    def test_all_entities_are_lambda_binary_sensor(self):
        config = {"num_heatpumps": 2, "num_boilers": 2}
        entities = run(_run_setup(config))
        assert all(isinstance(e, LambdaBinarySensor) for e in entities)

    def test_unique_ids_are_distinct(self):
        config = {"num_heatpumps": 5, "num_boilers": 5}
        entities = run(_run_setup(config))
        ids = [e._attr_unique_id for e in entities]
        assert len(ids) == len(set(ids)), "Duplicate unique IDs found"

    def test_heatpump_entity_module_type(self):
        config = {"num_heatpumps": 1, "num_boilers": 0}
        entities = run(_run_setup(config))
        assert entities[0]._module_type == MODULE_HEATPUMP

    def test_boiler_entity_module_type(self):
        config = {"num_heatpumps": 0, "num_boilers": 1}
        entities = run(_run_setup(config))
        assert entities[0]._module_type == MODULE_BOILER
