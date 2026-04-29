"""Unit tests for LambdaSensor and async_setup_entry (tasks 6.1, 6.2)."""
from __future__ import annotations

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
    "homeassistant.components.sensor",
]:
    _ensure_stub(_mod)

# AddEntitiesCallback stub
_ep = sys.modules["homeassistant.helpers.entity_platform"]
_ep.AddEntitiesCallback = object  # type: ignore[attr-defined]

# CoordinatorEntity stub
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

# DeviceInfo stub
class _DeviceInfo(dict):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

_dr = sys.modules["homeassistant.helpers.device_registry"]
_dr.DeviceInfo = _DeviceInfo  # type: ignore[attr-defined]

_core = sys.modules["homeassistant.core"]
_core.HomeAssistant = object  # type: ignore[attr-defined]

# SensorEntity stub
class _SensorEntity:
    pass

_sensor_mod = sys.modules["homeassistant.components.sensor"]
_sensor_mod.SensorEntity = _SensorEntity  # type: ignore[attr-defined]
_sensor_mod.SensorDeviceClass = object  # type: ignore[attr-defined]
_sensor_mod.SensorStateClass = object  # type: ignore[attr-defined]

# ConfigEntry stub
_ce = sys.modules["homeassistant.config_entries"]
_ce.ConfigEntry = object  # type: ignore[attr-defined]

# ---------------------------------------------------------------------------
# Import modules under test
# ---------------------------------------------------------------------------

from custom_components.lambda_heat_pump.sensor import LambdaSensor, _combine_int32, _is_sensor_register
from custom_components.lambda_heat_pump.const import (
    MODULE_HEATPUMP,
    MODULE_BOILER,
    MODULE_BUFFER,
    MODULE_SOLAR,
    MODULE_HEATING_CIRCUIT,
    MODULE_AMBIENT,
    MODULE_EMANAGER,
    INDEX_HEATPUMP,
    INDEX_BOILER,
    INDEX_BUFFER,
    INDEX_SOLAR,
    INDEX_HEATING_CIRCUIT,
    INDEX_GENERAL,
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
    RegisterDefinition,
    HP_ERROR_STATE,
    HP_STATE,
    HP_OPERATING_STATE,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CONFIG_ENTRY_ID = "test_entry_abc"


def make_coordinator(data: dict | None = None):
    coord = MagicMock()
    coord.data = data if data is not None else {}
    coord.last_update_success = True
    return coord


def make_sensor(
    module_type=MODULE_HEATPUMP,
    module_index=INDEX_HEATPUMP,
    subindex=0,
    register_def=None,
    data: dict | None = None,
):
    if register_def is None:
        register_def = HEATPUMP_REGISTERS[4]  # t_flow
    coord = make_coordinator(data=data)
    return LambdaSensor(coord, CONFIG_ENTRY_ID, module_type, module_index, subindex, register_def)


# ---------------------------------------------------------------------------
# Tests: _combine_int32
# ---------------------------------------------------------------------------

class TestCombineInt32:
    def test_positive_value(self):
        # 1000000 = 0x000F4240 → high=0x000F, low=0x4240
        high = 0x000F
        low = 0x4240
        assert _combine_int32(high, low) == 1000000

    def test_zero(self):
        assert _combine_int32(0, 0) == 0

    def test_max_positive(self):
        # 2^31 - 1 = 0x7FFFFFFF
        assert _combine_int32(0x7FFF, 0xFFFF) == 2147483647

    def test_negative_one(self):
        # -1 = 0xFFFFFFFF
        assert _combine_int32(0xFFFF, 0xFFFF) == -1

    def test_min_negative(self):
        # -2^31 = 0x80000000
        assert _combine_int32(0x8000, 0x0000) == -2147483648

    def test_small_negative(self):
        # -1000 = 0xFFFFFC18 → high=0xFFFF, low=0xFC18
        assert _combine_int32(0xFFFF, 0xFC18) == -1000


# ---------------------------------------------------------------------------
# Tests: _is_sensor_register
# ---------------------------------------------------------------------------

class TestIsSensorRegister:
    def test_ro_numeric_is_sensor(self):
        reg = HEATPUMP_REGISTERS[4]  # t_flow, RO, no options
        assert _is_sensor_register(reg) is True

    def test_ro_enum_is_sensor(self):
        reg = HEATPUMP_REGISTERS[0]  # hp_error_state, RO, has options
        assert _is_sensor_register(reg) is True

    def test_rw_register_is_not_sensor(self):
        reg = HEATPUMP_REGISTERS[14]  # request_password, RW
        assert _is_sensor_register(reg) is False

    def test_relay_2nd_stage_is_not_sensor(self):
        # relay_2nd_stage is RO but binary → goes to binary_sensor.py
        relay_reg = next(r for r in HEATPUMP_REGISTERS if r.name == "relay_2nd_stage")
        assert _is_sensor_register(relay_reg) is False

    def test_boiler_pump_state_is_not_sensor(self):
        pump_reg = next(r for r in BOILER_REGISTERS if r.name == "boiler_pump_state")
        assert _is_sensor_register(pump_reg) is False


# ---------------------------------------------------------------------------
# Tests: LambdaSensor.native_value — numeric registers
# ---------------------------------------------------------------------------

class TestNativeValueNumeric:
    def test_temperature_with_scale_001(self):
        # t_flow: scale=0.01, raw=4523 → 45.23
        reg = HEATPUMP_REGISTERS[4]  # t_flow
        addr = calc_register_address(INDEX_HEATPUMP, 0, reg.number)
        sensor = make_sensor(data={addr: 4523})
        assert abs(sensor.native_value - 45.23) < 1e-9

    def test_temperature_with_scale_01(self):
        # boiler_temp_high: scale=0.1, raw=550 → 55.0
        reg = BOILER_REGISTERS[2]  # boiler_temp_high
        addr = calc_register_address(INDEX_BOILER, 0, reg.number)
        sensor = make_sensor(
            module_type=MODULE_BOILER,
            module_index=INDEX_BOILER,
            register_def=reg,
            data={addr: 550},
        )
        assert abs(sensor.native_value - 55.0) < 1e-9

    def test_scale_1_returns_int(self):
        # fi_power: scale=1, raw=1500 → 1500 (int)
        reg = HEATPUMP_REGISTERS[12]  # fi_power
        addr = calc_register_address(INDEX_HEATPUMP, 0, reg.number)
        sensor = make_sensor(register_def=reg, data={addr: 1500})
        assert sensor.native_value == 1500
        assert isinstance(sensor.native_value, int)

    def test_returns_none_when_data_is_none(self):
        sensor = make_sensor(data=None)
        sensor.coordinator.data = None
        assert sensor.native_value is None

    def test_returns_none_when_address_missing(self):
        sensor = make_sensor(data={})
        assert sensor.native_value is None

    def test_second_heatpump_uses_correct_address(self):
        reg = HEATPUMP_REGISTERS[4]  # t_flow
        addr_hp2 = calc_register_address(INDEX_HEATPUMP, 1, reg.number)  # 1104
        sensor = make_sensor(subindex=1, data={addr_hp2: 3891})
        assert abs(sensor.native_value - 38.91) < 1e-9


# ---------------------------------------------------------------------------
# Tests: LambdaSensor.native_value — enum registers
# ---------------------------------------------------------------------------

class TestNativeValueEnum:
    def test_hp_error_state_known_value(self):
        reg = HEATPUMP_REGISTERS[0]  # hp_error_state
        addr = calc_register_address(INDEX_HEATPUMP, 0, reg.number)
        sensor = make_sensor(register_def=reg, data={addr: 0})
        assert sensor.native_value == "NONE"

    def test_hp_error_state_fault(self):
        reg = HEATPUMP_REGISTERS[0]
        addr = calc_register_address(INDEX_HEATPUMP, 0, reg.number)
        sensor = make_sensor(register_def=reg, data={addr: 4})
        assert sensor.native_value == "FAULT"

    def test_hp_state_regulation(self):
        reg = HEATPUMP_REGISTERS[2]  # hp_state
        addr = calc_register_address(INDEX_HEATPUMP, 0, reg.number)
        sensor = make_sensor(register_def=reg, data={addr: 7})
        assert sensor.native_value == "REGULATION"

    def test_operating_state_stby(self):
        reg = HEATPUMP_REGISTERS[3]  # operating_state
        addr = calc_register_address(INDEX_HEATPUMP, 0, reg.number)
        sensor = make_sensor(register_def=reg, data={addr: 0})
        assert sensor.native_value == "STBY"

    def test_unknown_enum_value_returns_string(self):
        reg = HEATPUMP_REGISTERS[0]  # hp_error_state
        addr = calc_register_address(INDEX_HEATPUMP, 0, reg.number)
        sensor = make_sensor(register_def=reg, data={addr: 99})
        assert sensor.native_value == "99"

    def test_boiler_operating_state(self):
        reg = BOILER_REGISTERS[1]  # boiler_operating_state
        addr = calc_register_address(INDEX_BOILER, 0, reg.number)
        sensor = make_sensor(
            module_type=MODULE_BOILER,
            module_index=INDEX_BOILER,
            register_def=reg,
            data={addr: 1},
        )
        assert sensor.native_value == "DHW"


# ---------------------------------------------------------------------------
# Tests: LambdaSensor.native_value — INT32 registers
# ---------------------------------------------------------------------------

class TestNativeValueInt32:
    def test_stat_energy_e_positive(self):
        reg = HEATPUMP_REGISTERS[20]  # stat_energy_e, number=20, INT32
        addr = calc_register_address(INDEX_HEATPUMP, 0, reg.number)  # 1020
        # Value 1000000 Wh = 0x000F4240 → high=0x000F=15, low=0x4240=16960
        sensor = make_sensor(register_def=reg, data={addr: 15, addr + 1: 16960})
        assert sensor.native_value == 1000000

    def test_stat_energy_q_zero(self):
        reg = HEATPUMP_REGISTERS[21]  # stat_energy_q, number=22, INT32
        addr = calc_register_address(INDEX_HEATPUMP, 0, reg.number)
        sensor = make_sensor(register_def=reg, data={addr: 0, addr + 1: 0})
        assert sensor.native_value == 0

    def test_int32_missing_high_word_returns_none(self):
        reg = HEATPUMP_REGISTERS[20]  # stat_energy_e
        addr = calc_register_address(INDEX_HEATPUMP, 0, reg.number)
        sensor = make_sensor(register_def=reg, data={addr + 1: 100})
        assert sensor.native_value is None

    def test_int32_missing_low_word_returns_none(self):
        reg = HEATPUMP_REGISTERS[20]
        addr = calc_register_address(INDEX_HEATPUMP, 0, reg.number)
        sensor = make_sensor(register_def=reg, data={addr: 0})
        assert sensor.native_value is None


# ---------------------------------------------------------------------------
# Tests: LambdaSensor attributes from RegisterDefinition
# ---------------------------------------------------------------------------

class TestSensorAttributes:
    def test_device_class_temperature(self):
        reg = HEATPUMP_REGISTERS[4]  # t_flow, device_class="temperature"
        sensor = make_sensor(register_def=reg)
        assert sensor._attr_device_class == "temperature"

    def test_state_class_measurement(self):
        reg = HEATPUMP_REGISTERS[4]  # state_class="measurement"
        sensor = make_sensor(register_def=reg)
        assert sensor._attr_state_class == "measurement"

    def test_unit_of_measurement(self):
        reg = HEATPUMP_REGISTERS[4]  # unit="°C"
        sensor = make_sensor(register_def=reg)
        assert sensor._attr_native_unit_of_measurement == "°C"

    def test_no_unit_when_none(self):
        reg = HEATPUMP_REGISTERS[0]  # hp_error_state, unit=None
        sensor = make_sensor(register_def=reg)
        assert not hasattr(sensor, "_attr_native_unit_of_measurement") or \
               getattr(sensor, "_attr_native_unit_of_measurement", None) is None

    def test_energy_state_class_total_increasing(self):
        reg = HEATPUMP_REGISTERS[20]  # stat_energy_e
        sensor = make_sensor(register_def=reg)
        assert sensor._attr_state_class == "total_increasing"


# ---------------------------------------------------------------------------
# Tests: async_setup_entry entity counts
# ---------------------------------------------------------------------------

import asyncio

# Minimal stubs for async_setup_entry
class _FakeConfigEntry:
    def __init__(self, data: dict):
        self.data = data
        self.entry_id = CONFIG_ENTRY_ID


class _FakeHass:
    def __init__(self, coordinator):
        from custom_components.lambda_heat_pump.const import DOMAIN
        self.data = {DOMAIN: {CONFIG_ENTRY_ID: coordinator}}


async def _run_setup(config: dict) -> list[LambdaSensor]:
    from custom_components.lambda_heat_pump.sensor import async_setup_entry
    coord = make_coordinator(data={})
    hass = _FakeHass(coord)
    entry = _FakeConfigEntry(config)
    added: list[LambdaSensor] = []
    async_add_entities = lambda entities: added.extend(entities)
    await async_setup_entry(hass, entry, async_add_entities)
    return added


def run(coro):
    return asyncio.run(coro)


class TestAsyncSetupEntry:
    def test_single_heatpump_sensor_count(self):
        # HP has 22 registers total; 2 binary (relay_2nd_stage) + 5 RW = 7 excluded
        # RO non-binary: 22 - 1 binary - 5 RW = 16 sensors
        config = {
            "num_heatpumps": 1,
            "num_boilers": 0,
            "num_buffers": 0,
            "num_solar": 0,
            "num_heating_circuits": 0,
            "enable_ambient": False,
            "enable_emanager": False,
        }
        entities = run(_run_setup(config))
        # All entities should be LambdaSensor
        assert all(isinstance(e, LambdaSensor) for e in entities)
        # Count RO non-binary HP registers
        expected = sum(1 for r in HEATPUMP_REGISTERS if _is_sensor_register(r))
        assert len(entities) == expected

    def test_no_entities_when_all_zero(self):
        config = {
            "num_heatpumps": 0,
            "num_boilers": 0,
            "num_buffers": 0,
            "num_solar": 0,
            "num_heating_circuits": 0,
            "enable_ambient": False,
            "enable_emanager": False,
        }
        entities = run(_run_setup(config))
        assert entities == []

    def test_ambient_entities_when_enabled(self):
        config = {
            "num_heatpumps": 0,
            "num_boilers": 0,
            "num_buffers": 0,
            "num_solar": 0,
            "num_heating_circuits": 0,
            "enable_ambient": True,
            "enable_emanager": False,
        }
        entities = run(_run_setup(config))
        expected = sum(1 for r in AMBIENT_REGISTERS if _is_sensor_register(r))
        assert len(entities) == expected

    def test_no_ambient_entities_when_disabled(self):
        config = {
            "num_heatpumps": 0,
            "num_boilers": 0,
            "num_buffers": 0,
            "num_solar": 0,
            "num_heating_circuits": 0,
            "enable_ambient": False,
            "enable_emanager": False,
        }
        entities = run(_run_setup(config))
        assert len(entities) == 0

    def test_emanager_entities_when_enabled(self):
        config = {
            "num_heatpumps": 0,
            "num_boilers": 0,
            "num_buffers": 0,
            "num_solar": 0,
            "num_heating_circuits": 0,
            "enable_ambient": False,
            "enable_emanager": True,
        }
        entities = run(_run_setup(config))
        expected = sum(1 for r in EMANAGER_REGISTERS if _is_sensor_register(r))
        assert len(entities) == expected

    def test_multiple_heatpumps(self):
        config = {
            "num_heatpumps": 3,
            "num_boilers": 0,
            "num_buffers": 0,
            "num_solar": 0,
            "num_heating_circuits": 0,
            "enable_ambient": False,
            "enable_emanager": False,
        }
        entities = run(_run_setup(config))
        per_hp = sum(1 for r in HEATPUMP_REGISTERS if _is_sensor_register(r))
        assert len(entities) == 3 * per_hp

    def test_boiler_sensors(self):
        config = {
            "num_heatpumps": 0,
            "num_boilers": 2,
            "num_buffers": 0,
            "num_solar": 0,
            "num_heating_circuits": 0,
            "enable_ambient": False,
            "enable_emanager": False,
        }
        entities = run(_run_setup(config))
        per_boiler = sum(1 for r in BOILER_REGISTERS if _is_sensor_register(r))
        assert len(entities) == 2 * per_boiler

    def test_heating_circuit_sensors(self):
        config = {
            "num_heatpumps": 0,
            "num_boilers": 0,
            "num_buffers": 0,
            "num_solar": 0,
            "num_heating_circuits": 2,
            "enable_ambient": False,
            "enable_emanager": False,
        }
        entities = run(_run_setup(config))
        per_hc = sum(1 for r in HEATING_CIRCUIT_REGISTERS if _is_sensor_register(r))
        assert len(entities) == 2 * per_hc

    def test_combined_config(self):
        config = {
            "num_heatpumps": 1,
            "num_boilers": 1,
            "num_buffers": 1,
            "num_solar": 1,
            "num_heating_circuits": 1,
            "enable_ambient": True,
            "enable_emanager": True,
        }
        entities = run(_run_setup(config))
        expected = (
            sum(1 for r in HEATPUMP_REGISTERS if _is_sensor_register(r))
            + sum(1 for r in BOILER_REGISTERS if _is_sensor_register(r))
            + sum(1 for r in BUFFER_REGISTERS if _is_sensor_register(r))
            + sum(1 for r in SOLAR_REGISTERS if _is_sensor_register(r))
            + sum(1 for r in HEATING_CIRCUIT_REGISTERS if _is_sensor_register(r))
            + sum(1 for r in AMBIENT_REGISTERS if _is_sensor_register(r))
            + sum(1 for r in EMANAGER_REGISTERS if _is_sensor_register(r))
        )
        assert len(entities) == expected

    def test_entity_module_types_correct(self):
        """Entities for boiler should have boiler module type."""
        config = {
            "num_heatpumps": 0,
            "num_boilers": 1,
            "num_buffers": 0,
            "num_solar": 0,
            "num_heating_circuits": 0,
            "enable_ambient": False,
            "enable_emanager": False,
        }
        entities = run(_run_setup(config))
        for e in entities:
            assert e._module_type == MODULE_BOILER

    def test_unique_ids_are_distinct(self):
        config = {
            "num_heatpumps": 2,
            "num_boilers": 2,
            "num_buffers": 1,
            "num_solar": 1,
            "num_heating_circuits": 2,
            "enable_ambient": True,
            "enable_emanager": True,
        }
        entities = run(_run_setup(config))
        ids = [e._attr_unique_id for e in entities]
        assert len(ids) == len(set(ids)), "Duplicate unique IDs found"
