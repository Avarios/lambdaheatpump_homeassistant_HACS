"""Tests for entity creation counts and types across all platforms (task 12.3).

Verifies that async_setup_entry for each platform creates the correct number
and types of entities for various configurations, covering all module types
including Ambient and EManager.

Validates: Requirements 1.5, 4.1, 5.1, 6.1, 6.2, 6.3, 6.4, 9.1, 9.2
"""
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


_HA_MODS = [
    "homeassistant",
    "homeassistant.core",
    "homeassistant.config_entries",
    "homeassistant.helpers",
    "homeassistant.helpers.update_coordinator",
    "homeassistant.helpers.device_registry",
    "homeassistant.helpers.entity_platform",
    "homeassistant.components",
    "homeassistant.components.sensor",
    "homeassistant.components.binary_sensor",
    "homeassistant.components.number",
    "homeassistant.components.select",
]
for _mod in _HA_MODS:
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

_ce = sys.modules["homeassistant.config_entries"]
_ce.ConfigEntry = object  # type: ignore[attr-defined]

# Sensor stubs
class _SensorEntity:
    pass

_sensor_mod = sys.modules["homeassistant.components.sensor"]
_sensor_mod.SensorEntity = _SensorEntity  # type: ignore[attr-defined]
_sensor_mod.SensorDeviceClass = object  # type: ignore[attr-defined]
_sensor_mod.SensorStateClass = object  # type: ignore[attr-defined]

# Binary sensor stubs
class _BinarySensorEntity:
    pass

_bs_mod = sys.modules["homeassistant.components.binary_sensor"]
_bs_mod.BinarySensorEntity = _BinarySensorEntity  # type: ignore[attr-defined]

# Number stubs
class _NumberEntity:
    pass

class _NumberMode:
    BOX = "box"
    SLIDER = "slider"
    AUTO = "auto"

_num_mod = sys.modules["homeassistant.components.number"]
_num_mod.NumberEntity = _NumberEntity  # type: ignore[attr-defined]
_num_mod.NumberMode = _NumberMode  # type: ignore[attr-defined]

# Select stubs
class _SelectEntity:
    pass

_sel_mod = sys.modules["homeassistant.components.select"]
_sel_mod.SelectEntity = _SelectEntity  # type: ignore[attr-defined]

# ---------------------------------------------------------------------------
# Import modules under test
# ---------------------------------------------------------------------------

from custom_components.lambda_heat_pump.sensor import (
    LambdaSensor,
    _is_sensor_register,
    async_setup_entry as sensor_setup,
)
from custom_components.lambda_heat_pump.binary_sensor import (
    LambdaBinarySensor,
    _is_binary_register,
    async_setup_entry as binary_sensor_setup,
)
from custom_components.lambda_heat_pump.number import (
    LambdaNumber,
    _is_number_register,
    async_setup_entry as number_setup,
)
from custom_components.lambda_heat_pump.select import (
    LambdaSelect,
    _is_select_register,
    async_setup_entry as select_setup,
)
from custom_components.lambda_heat_pump.const import (
    DOMAIN,
    HEATPUMP_REGISTERS,
    BOILER_REGISTERS,
    BUFFER_REGISTERS,
    SOLAR_REGISTERS,
    HEATING_CIRCUIT_REGISTERS,
    AMBIENT_REGISTERS,
    EMANAGER_REGISTERS,
)

# ---------------------------------------------------------------------------
# Expected entity counts per module (from design.md Property 7)
# ---------------------------------------------------------------------------

# Counts derived directly from register definitions
_HP_SENSORS = sum(1 for r in HEATPUMP_REGISTERS if _is_sensor_register(r))
_HP_BINARY = sum(1 for r in HEATPUMP_REGISTERS if _is_binary_register(r))
_HP_NUMBERS = sum(1 for r in HEATPUMP_REGISTERS if _is_number_register(r))
_HP_SELECTS = sum(1 for r in HEATPUMP_REGISTERS if _is_select_register(r))
HP_TOTAL = _HP_SENSORS + _HP_BINARY + _HP_NUMBERS + _HP_SELECTS  # 22

_BOILER_SENSORS = sum(1 for r in BOILER_REGISTERS if _is_sensor_register(r))
_BOILER_BINARY = sum(1 for r in BOILER_REGISTERS if _is_binary_register(r))
_BOILER_NUMBERS = sum(1 for r in BOILER_REGISTERS if _is_number_register(r))
_BOILER_SELECTS = sum(1 for r in BOILER_REGISTERS if _is_select_register(r))
BOILER_TOTAL = _BOILER_SENSORS + _BOILER_BINARY + _BOILER_NUMBERS + _BOILER_SELECTS  # 7

_BUFFER_SENSORS = sum(1 for r in BUFFER_REGISTERS if _is_sensor_register(r))
_BUFFER_BINARY = sum(1 for r in BUFFER_REGISTERS if _is_binary_register(r))
_BUFFER_NUMBERS = sum(1 for r in BUFFER_REGISTERS if _is_number_register(r))
_BUFFER_SELECTS = sum(1 for r in BUFFER_REGISTERS if _is_select_register(r))
BUFFER_TOTAL = _BUFFER_SENSORS + _BUFFER_BINARY + _BUFFER_NUMBERS + _BUFFER_SELECTS  # 11

_SOLAR_SENSORS = sum(1 for r in SOLAR_REGISTERS if _is_sensor_register(r))
_SOLAR_BINARY = sum(1 for r in SOLAR_REGISTERS if _is_binary_register(r))
_SOLAR_NUMBERS = sum(1 for r in SOLAR_REGISTERS if _is_number_register(r))
_SOLAR_SELECTS = sum(1 for r in SOLAR_REGISTERS if _is_select_register(r))
SOLAR_TOTAL = _SOLAR_SENSORS + _SOLAR_BINARY + _SOLAR_NUMBERS + _SOLAR_SELECTS  # 7

_HC_SENSORS = sum(1 for r in HEATING_CIRCUIT_REGISTERS if _is_sensor_register(r))
_HC_BINARY = sum(1 for r in HEATING_CIRCUIT_REGISTERS if _is_binary_register(r))
_HC_NUMBERS = sum(1 for r in HEATING_CIRCUIT_REGISTERS if _is_number_register(r))
_HC_SELECTS = sum(1 for r in HEATING_CIRCUIT_REGISTERS if _is_select_register(r))
HC_TOTAL = _HC_SENSORS + _HC_BINARY + _HC_NUMBERS + _HC_SELECTS  # 11

_AMBIENT_SENSORS = sum(1 for r in AMBIENT_REGISTERS if _is_sensor_register(r))
_AMBIENT_BINARY = sum(1 for r in AMBIENT_REGISTERS if _is_binary_register(r))
_AMBIENT_NUMBERS = sum(1 for r in AMBIENT_REGISTERS if _is_number_register(r))
_AMBIENT_SELECTS = sum(1 for r in AMBIENT_REGISTERS if _is_select_register(r))
AMBIENT_TOTAL = _AMBIENT_SENSORS + _AMBIENT_BINARY + _AMBIENT_NUMBERS + _AMBIENT_SELECTS  # 5

_EMANAGER_SENSORS = sum(1 for r in EMANAGER_REGISTERS if _is_sensor_register(r))
_EMANAGER_BINARY = sum(1 for r in EMANAGER_REGISTERS if _is_binary_register(r))
_EMANAGER_NUMBERS = sum(1 for r in EMANAGER_REGISTERS if _is_number_register(r))
_EMANAGER_SELECTS = sum(1 for r in EMANAGER_REGISTERS if _is_select_register(r))
EMANAGER_TOTAL = _EMANAGER_SENSORS + _EMANAGER_BINARY + _EMANAGER_NUMBERS + _EMANAGER_SELECTS  # 5

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

CONFIG_ENTRY_ID = "test_entity_creation"


def make_coordinator():
    coord = MagicMock()
    coord.data = {}
    coord.last_update_success = True
    return coord


class _FakeConfigEntry:
    def __init__(self, data: dict):
        self.data = data
        self.entry_id = CONFIG_ENTRY_ID


class _FakeHass:
    def __init__(self, coordinator):
        self.data = {DOMAIN: {CONFIG_ENTRY_ID: coordinator}}


async def _collect_all_entities(config: dict) -> dict[str, list]:
    """Run all four platform setup functions and return entities by platform."""
    coord = make_coordinator()
    hass = _FakeHass(coord)
    entry = _FakeConfigEntry(config)

    sensors: list = []
    binary_sensors: list = []
    numbers: list = []
    selects: list = []

    await sensor_setup(hass, entry, lambda e: sensors.extend(e))
    await binary_sensor_setup(hass, entry, lambda e: binary_sensors.extend(e))
    await number_setup(hass, entry, lambda e: numbers.extend(e))
    await select_setup(hass, entry, lambda e: selects.extend(e))

    return {
        "sensors": sensors,
        "binary_sensors": binary_sensors,
        "numbers": numbers,
        "selects": selects,
        "all": sensors + binary_sensors + numbers + selects,
    }


def run(coro):
    return asyncio.run(coro)

# ---------------------------------------------------------------------------
# Tests: Per-module entity counts match design.md Property 7
# ---------------------------------------------------------------------------

class TestModuleEntityCounts:
    """Verify design.md Property 7 entity counts for each module type."""

    def test_hp_total_is_22(self):
        assert HP_TOTAL == 22, f"Expected 22 HP entities, got {HP_TOTAL}"

    def test_boiler_total_is_7(self):
        assert BOILER_TOTAL == 7, f"Expected 7 boiler entities, got {BOILER_TOTAL}"

    def test_buffer_total_is_11(self):
        assert BUFFER_TOTAL == 11, f"Expected 11 buffer entities, got {BUFFER_TOTAL}"

    def test_solar_total_is_7(self):
        assert SOLAR_TOTAL == 7, f"Expected 7 solar entities, got {SOLAR_TOTAL}"

    def test_hc_total_is_11(self):
        assert HC_TOTAL == 11, f"Expected 11 HC entities, got {HC_TOTAL}"

    def test_ambient_total_is_5(self):
        assert AMBIENT_TOTAL == 5, f"Expected 5 ambient entities, got {AMBIENT_TOTAL}"

    def test_emanager_total_is_5(self):
        assert EMANAGER_TOTAL == 5, f"Expected 5 EManager entities, got {EMANAGER_TOTAL}"


# ---------------------------------------------------------------------------
# Tests: No entities created when counts are zero / modules disabled
# ---------------------------------------------------------------------------

class TestNoEntitiesWhenDisabled:
    """Requirement 6.5, 9.3, 9.4: zero counts produce no entities."""

    def test_all_zero_produces_no_entities(self):
        config = {
            "num_heatpumps": 0, "num_boilers": 0, "num_buffers": 0,
            "num_solar": 0, "num_heating_circuits": 0,
            "enable_ambient": False, "enable_emanager": False,
        }
        result = run(_collect_all_entities(config))
        assert result["all"] == []

    def test_ambient_disabled_produces_no_ambient_entities(self):
        config = {
            "num_heatpumps": 0, "num_boilers": 0, "num_buffers": 0,
            "num_solar": 0, "num_heating_circuits": 0,
            "enable_ambient": False, "enable_emanager": False,
        }
        result = run(_collect_all_entities(config))
        ambient_names = {r.name for r in AMBIENT_REGISTERS}
        for e in result["all"]:
            assert e._register_def.name not in ambient_names

    def test_emanager_disabled_produces_no_emanager_entities(self):
        config = {
            "num_heatpumps": 0, "num_boilers": 0, "num_buffers": 0,
            "num_solar": 0, "num_heating_circuits": 0,
            "enable_ambient": False, "enable_emanager": False,
        }
        result = run(_collect_all_entities(config))
        emanager_names = {r.name for r in EMANAGER_REGISTERS}
        for e in result["all"]:
            assert e._register_def.name not in emanager_names


# ---------------------------------------------------------------------------
# Tests: Single module of each type
# ---------------------------------------------------------------------------

class TestSingleModuleEntityCreation:
    """Verify correct total entity count for a single instance of each module."""

    def test_single_heatpump(self):
        config = {
            "num_heatpumps": 1, "num_boilers": 0, "num_buffers": 0,
            "num_solar": 0, "num_heating_circuits": 0,
            "enable_ambient": False, "enable_emanager": False,
        }
        result = run(_collect_all_entities(config))
        assert len(result["all"]) == HP_TOTAL
        assert len(result["sensors"]) == _HP_SENSORS
        assert len(result["binary_sensors"]) == _HP_BINARY
        assert len(result["numbers"]) == _HP_NUMBERS
        assert len(result["selects"]) == _HP_SELECTS

    def test_single_boiler(self):
        config = {
            "num_heatpumps": 0, "num_boilers": 1, "num_buffers": 0,
            "num_solar": 0, "num_heating_circuits": 0,
            "enable_ambient": False, "enable_emanager": False,
        }
        result = run(_collect_all_entities(config))
        assert len(result["all"]) == BOILER_TOTAL
        assert len(result["sensors"]) == _BOILER_SENSORS
        assert len(result["binary_sensors"]) == _BOILER_BINARY
        assert len(result["numbers"]) == _BOILER_NUMBERS
        assert len(result["selects"]) == _BOILER_SELECTS

    def test_single_buffer(self):
        config = {
            "num_heatpumps": 0, "num_boilers": 0, "num_buffers": 1,
            "num_solar": 0, "num_heating_circuits": 0,
            "enable_ambient": False, "enable_emanager": False,
        }
        result = run(_collect_all_entities(config))
        assert len(result["all"]) == BUFFER_TOTAL
        assert len(result["sensors"]) == _BUFFER_SENSORS
        assert len(result["binary_sensors"]) == _BUFFER_BINARY
        assert len(result["numbers"]) == _BUFFER_NUMBERS
        assert len(result["selects"]) == _BUFFER_SELECTS

    def test_single_solar(self):
        config = {
            "num_heatpumps": 0, "num_boilers": 0, "num_buffers": 0,
            "num_solar": 1, "num_heating_circuits": 0,
            "enable_ambient": False, "enable_emanager": False,
        }
        result = run(_collect_all_entities(config))
        assert len(result["all"]) == SOLAR_TOTAL
        assert len(result["sensors"]) == _SOLAR_SENSORS
        assert len(result["binary_sensors"]) == _SOLAR_BINARY
        assert len(result["numbers"]) == _SOLAR_NUMBERS
        assert len(result["selects"]) == _SOLAR_SELECTS

    def test_single_heating_circuit(self):
        config = {
            "num_heatpumps": 0, "num_boilers": 0, "num_buffers": 0,
            "num_solar": 0, "num_heating_circuits": 1,
            "enable_ambient": False, "enable_emanager": False,
        }
        result = run(_collect_all_entities(config))
        assert len(result["all"]) == HC_TOTAL
        assert len(result["sensors"]) == _HC_SENSORS
        assert len(result["binary_sensors"]) == _HC_BINARY
        assert len(result["numbers"]) == _HC_NUMBERS
        assert len(result["selects"]) == _HC_SELECTS

    def test_ambient_only(self):
        config = {
            "num_heatpumps": 0, "num_boilers": 0, "num_buffers": 0,
            "num_solar": 0, "num_heating_circuits": 0,
            "enable_ambient": True, "enable_emanager": False,
        }
        result = run(_collect_all_entities(config))
        assert len(result["all"]) == AMBIENT_TOTAL
        assert len(result["sensors"]) == _AMBIENT_SENSORS
        assert len(result["binary_sensors"]) == _AMBIENT_BINARY
        assert len(result["numbers"]) == _AMBIENT_NUMBERS
        assert len(result["selects"]) == _AMBIENT_SELECTS

    def test_emanager_only(self):
        config = {
            "num_heatpumps": 0, "num_boilers": 0, "num_buffers": 0,
            "num_solar": 0, "num_heating_circuits": 0,
            "enable_ambient": False, "enable_emanager": True,
        }
        result = run(_collect_all_entities(config))
        assert len(result["all"]) == EMANAGER_TOTAL
        assert len(result["sensors"]) == _EMANAGER_SENSORS
        assert len(result["binary_sensors"]) == _EMANAGER_BINARY
        assert len(result["numbers"]) == _EMANAGER_NUMBERS
        assert len(result["selects"]) == _EMANAGER_SELECTS

# ---------------------------------------------------------------------------
# Tests: Multiple instances scale linearly
# ---------------------------------------------------------------------------

class TestMultipleInstancesScaleLinearly:
    """Entity count must scale exactly with module count."""

    def test_multiple_heatpumps(self):
        for n in [1, 2, 3, 5]:
            config = {
                "num_heatpumps": n, "num_boilers": 0, "num_buffers": 0,
                "num_solar": 0, "num_heating_circuits": 0,
                "enable_ambient": False, "enable_emanager": False,
            }
            result = run(_collect_all_entities(config))
            assert len(result["all"]) == n * HP_TOTAL, f"n={n}: expected {n * HP_TOTAL}"

    def test_multiple_boilers(self):
        for n in [1, 2, 5]:
            config = {
                "num_heatpumps": 0, "num_boilers": n, "num_buffers": 0,
                "num_solar": 0, "num_heating_circuits": 0,
                "enable_ambient": False, "enable_emanager": False,
            }
            result = run(_collect_all_entities(config))
            assert len(result["all"]) == n * BOILER_TOTAL, f"n={n}: expected {n * BOILER_TOTAL}"

    def test_multiple_buffers(self):
        for n in [1, 3, 5]:
            config = {
                "num_heatpumps": 0, "num_boilers": 0, "num_buffers": n,
                "num_solar": 0, "num_heating_circuits": 0,
                "enable_ambient": False, "enable_emanager": False,
            }
            result = run(_collect_all_entities(config))
            assert len(result["all"]) == n * BUFFER_TOTAL, f"n={n}: expected {n * BUFFER_TOTAL}"

    def test_multiple_solar(self):
        for n in [1, 2]:
            config = {
                "num_heatpumps": 0, "num_boilers": 0, "num_buffers": 0,
                "num_solar": n, "num_heating_circuits": 0,
                "enable_ambient": False, "enable_emanager": False,
            }
            result = run(_collect_all_entities(config))
            assert len(result["all"]) == n * SOLAR_TOTAL, f"n={n}: expected {n * SOLAR_TOTAL}"

    def test_multiple_heating_circuits(self):
        for n in [1, 6, 12]:
            config = {
                "num_heatpumps": 0, "num_boilers": 0, "num_buffers": 0,
                "num_solar": 0, "num_heating_circuits": n,
                "enable_ambient": False, "enable_emanager": False,
            }
            result = run(_collect_all_entities(config))
            assert len(result["all"]) == n * HC_TOTAL, f"n={n}: expected {n * HC_TOTAL}"


# ---------------------------------------------------------------------------
# Tests: Combined configurations
# ---------------------------------------------------------------------------

class TestCombinedConfigurations:
    """Verify total entity count for mixed configurations."""

    def test_one_of_each_module(self):
        config = {
            "num_heatpumps": 1, "num_boilers": 1, "num_buffers": 1,
            "num_solar": 1, "num_heating_circuits": 1,
            "enable_ambient": True, "enable_emanager": True,
        }
        result = run(_collect_all_entities(config))
        expected = HP_TOTAL + BOILER_TOTAL + BUFFER_TOTAL + SOLAR_TOTAL + HC_TOTAL + AMBIENT_TOTAL + EMANAGER_TOTAL
        assert len(result["all"]) == expected

    def test_max_configuration(self):
        # Maximum allowed: 5 HP, 5 boilers, 5 buffers, 2 solar, 12 HC + ambient + emanager
        config = {
            "num_heatpumps": 5, "num_boilers": 5, "num_buffers": 5,
            "num_solar": 2, "num_heating_circuits": 12,
            "enable_ambient": True, "enable_emanager": True,
        }
        result = run(_collect_all_entities(config))
        expected = (
            5 * HP_TOTAL
            + 5 * BOILER_TOTAL
            + 5 * BUFFER_TOTAL
            + 2 * SOLAR_TOTAL
            + 12 * HC_TOTAL
            + AMBIENT_TOTAL
            + EMANAGER_TOTAL
        )
        assert len(result["all"]) == expected

    def test_hp_and_ambient_and_emanager(self):
        config = {
            "num_heatpumps": 2, "num_boilers": 0, "num_buffers": 0,
            "num_solar": 0, "num_heating_circuits": 0,
            "enable_ambient": True, "enable_emanager": True,
        }
        result = run(_collect_all_entities(config))
        expected = 2 * HP_TOTAL + AMBIENT_TOTAL + EMANAGER_TOTAL
        assert len(result["all"]) == expected

    def test_boiler_and_buffer_and_solar(self):
        config = {
            "num_heatpumps": 0, "num_boilers": 3, "num_buffers": 2,
            "num_solar": 2, "num_heating_circuits": 0,
            "enable_ambient": False, "enable_emanager": False,
        }
        result = run(_collect_all_entities(config))
        expected = 3 * BOILER_TOTAL + 2 * BUFFER_TOTAL + 2 * SOLAR_TOTAL
        assert len(result["all"]) == expected


# ---------------------------------------------------------------------------
# Tests: Entity types are correct
# ---------------------------------------------------------------------------

class TestEntityTypes:
    """Verify that each platform creates the correct entity class instances."""

    def test_sensor_platform_creates_only_lambda_sensors(self):
        config = {
            "num_heatpumps": 1, "num_boilers": 1, "num_buffers": 1,
            "num_solar": 1, "num_heating_circuits": 1,
            "enable_ambient": True, "enable_emanager": True,
        }
        result = run(_collect_all_entities(config))
        assert all(isinstance(e, LambdaSensor) for e in result["sensors"])

    def test_binary_sensor_platform_creates_only_lambda_binary_sensors(self):
        config = {
            "num_heatpumps": 2, "num_boilers": 2, "num_buffers": 0,
            "num_solar": 0, "num_heating_circuits": 0,
            "enable_ambient": False, "enable_emanager": False,
        }
        result = run(_collect_all_entities(config))
        assert all(isinstance(e, LambdaBinarySensor) for e in result["binary_sensors"])

    def test_number_platform_creates_only_lambda_numbers(self):
        config = {
            "num_heatpumps": 1, "num_boilers": 1, "num_buffers": 1,
            "num_solar": 1, "num_heating_circuits": 1,
            "enable_ambient": True, "enable_emanager": True,
        }
        result = run(_collect_all_entities(config))
        assert all(isinstance(e, LambdaNumber) for e in result["numbers"])

    def test_select_platform_creates_only_lambda_selects(self):
        config = {
            "num_heatpumps": 2, "num_buffers": 2, "num_boilers": 0,
            "num_solar": 0, "num_heating_circuits": 2,
            "enable_ambient": False, "enable_emanager": False,
        }
        result = run(_collect_all_entities(config))
        assert all(isinstance(e, LambdaSelect) for e in result["selects"])

    def test_binary_sensors_only_for_hp_and_boiler(self):
        # Only HP (relay_2nd_stage) and Boiler (boiler_pump_state) have binary registers
        config = {
            "num_heatpumps": 1, "num_boilers": 1, "num_buffers": 1,
            "num_solar": 1, "num_heating_circuits": 1,
            "enable_ambient": True, "enable_emanager": True,
        }
        result = run(_collect_all_entities(config))
        # 1 HP binary + 1 boiler binary = 2
        assert len(result["binary_sensors"]) == _HP_BINARY + _BOILER_BINARY

    def test_selects_only_for_hp_buffer_hc(self):
        # Only HP (request_type), Buffer (buffer_request_type), HC (hc_operating_mode) have RW enums
        config = {
            "num_heatpumps": 1, "num_boilers": 1, "num_buffers": 1,
            "num_solar": 1, "num_heating_circuits": 1,
            "enable_ambient": True, "enable_emanager": True,
        }
        result = run(_collect_all_entities(config))
        expected_selects = _HP_SELECTS + _BOILER_SELECTS + _BUFFER_SELECTS + _SOLAR_SELECTS + _HC_SELECTS
        assert len(result["selects"]) == expected_selects


# ---------------------------------------------------------------------------
# Tests: Unique IDs are distinct across all platforms
# ---------------------------------------------------------------------------

class TestUniqueIds:
    """Requirement 7.1: All entity unique IDs must be pairwise distinct."""

    def test_unique_ids_distinct_single_of_each(self):
        config = {
            "num_heatpumps": 1, "num_boilers": 1, "num_buffers": 1,
            "num_solar": 1, "num_heating_circuits": 1,
            "enable_ambient": True, "enable_emanager": True,
        }
        result = run(_collect_all_entities(config))
        ids = [e._attr_unique_id for e in result["all"]]
        assert len(ids) == len(set(ids)), "Duplicate unique IDs found"

    def test_unique_ids_distinct_max_configuration(self):
        config = {
            "num_heatpumps": 5, "num_boilers": 5, "num_buffers": 5,
            "num_solar": 2, "num_heating_circuits": 12,
            "enable_ambient": True, "enable_emanager": True,
        }
        result = run(_collect_all_entities(config))
        ids = [e._attr_unique_id for e in result["all"]]
        assert len(ids) == len(set(ids)), "Duplicate unique IDs found in max configuration"
