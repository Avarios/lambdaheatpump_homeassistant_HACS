"""Unit tests for LambdaBaseEntity (task 5.1)."""
from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Stubs for homeassistant modules
# ---------------------------------------------------------------------------

def _ensure_stub(name: str) -> types.ModuleType:
    if name not in sys.modules:
        sys.modules[name] = types.ModuleType(name)
    return sys.modules[name]


for _mod in [
    "homeassistant",
    "homeassistant.core",
    "homeassistant.helpers",
    "homeassistant.helpers.update_coordinator",
    "homeassistant.helpers.device_registry",
]:
    _ensure_stub(_mod)

# CoordinatorEntity stub
class _FakeCoordinatorEntity:
    def __init__(self, coordinator):
        self.coordinator = coordinator

    def __class_getitem__(cls, item):
        return cls

_uc = sys.modules["homeassistant.helpers.update_coordinator"]
_uc.CoordinatorEntity = _FakeCoordinatorEntity  # type: ignore[attr-defined]

# DataUpdateCoordinator stub (needed by coordinator.py import)
class _FakeDataUpdateCoordinator:
    def __init__(self, hass, logger, *, name, update_interval):
        self.hass = hass
        self.name = name
        self.update_interval = update_interval
        self.data = None
        self.last_update_success = True

    def __class_getitem__(cls, item):
        return cls

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

# ---------------------------------------------------------------------------
# Import module under test
# ---------------------------------------------------------------------------

from custom_components.lambda_heat_pump.entity_base import LambdaBaseEntity
from custom_components.lambda_heat_pump.const import (
    DOMAIN,
    MODULE_HEATPUMP,
    MODULE_BOILER,
    MODULE_BUFFER,
    MODULE_SOLAR,
    MODULE_HEATING_CIRCUIT,
    MODULE_AMBIENT,
    MODULE_EMANAGER,
    HEATPUMP_REGISTERS,
    BOILER_REGISTERS,
    AMBIENT_REGISTERS,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CONFIG_ENTRY_ID = "test_entry_abc123"


_SENTINEL = object()


def make_coordinator(data=_SENTINEL, last_update_success=True):
    coord = MagicMock()
    coord.data = {1004: 4523} if data is _SENTINEL else data
    coord.last_update_success = last_update_success
    return coord


def make_entity(module_type=MODULE_HEATPUMP, subindex=0, register_def=None, data=None):
    if register_def is None:
        register_def = HEATPUMP_REGISTERS[4]  # t_flow, number=4
    coord = make_coordinator(data=data)
    return LambdaBaseEntity(coord, CONFIG_ENTRY_ID, module_type, subindex, register_def)


# ---------------------------------------------------------------------------
# Tests: unique_id
# ---------------------------------------------------------------------------

class TestUniqueId:
    def test_unique_id_format(self):
        reg = HEATPUMP_REGISTERS[4]  # number=4
        entity = make_entity(MODULE_HEATPUMP, subindex=0, register_def=reg)
        assert entity._attr_unique_id == f"{CONFIG_ENTRY_ID}_heatpump_0_4"

    def test_unique_id_uses_subindex(self):
        reg = HEATPUMP_REGISTERS[4]  # number=4
        entity = make_entity(MODULE_HEATPUMP, subindex=2, register_def=reg)
        assert entity._attr_unique_id == f"{CONFIG_ENTRY_ID}_heatpump_2_4"

    def test_unique_id_uses_register_number(self):
        reg = HEATPUMP_REGISTERS[0]  # number=0 (error_state)
        entity = make_entity(MODULE_HEATPUMP, subindex=0, register_def=reg)
        assert entity._attr_unique_id == f"{CONFIG_ENTRY_ID}_heatpump_0_0"

    def test_unique_id_uses_module_type(self):
        reg = BOILER_REGISTERS[0]  # number=0
        entity = make_entity(MODULE_BOILER, subindex=0, register_def=reg)
        assert entity._attr_unique_id == f"{CONFIG_ENTRY_ID}_boiler_0_0"

    def test_unique_ids_are_distinct_across_subindices(self):
        reg = HEATPUMP_REGISTERS[4]
        ids = {
            make_entity(MODULE_HEATPUMP, subindex=i, register_def=reg)._attr_unique_id
            for i in range(5)
        }
        assert len(ids) == 5

    def test_unique_ids_are_distinct_across_registers(self):
        ids = {
            make_entity(MODULE_HEATPUMP, subindex=0, register_def=reg)._attr_unique_id
            for reg in HEATPUMP_REGISTERS
        }
        assert len(ids) == len(HEATPUMP_REGISTERS)


# ---------------------------------------------------------------------------
# Tests: name
# ---------------------------------------------------------------------------

class TestName:
    def test_name_heat_pump_instance_1(self):
        reg = HEATPUMP_REGISTERS[4]  # label="Flow Line Temperature"
        entity = make_entity(MODULE_HEATPUMP, subindex=0, register_def=reg)
        assert entity._attr_name == "Lambda Heat Pump 1 Flow Line Temperature"

    def test_name_heat_pump_instance_2(self):
        reg = HEATPUMP_REGISTERS[4]
        entity = make_entity(MODULE_HEATPUMP, subindex=1, register_def=reg)
        assert entity._attr_name == "Lambda Heat Pump 2 Flow Line Temperature"

    def test_name_boiler(self):
        reg = BOILER_REGISTERS[2]  # label="Actual High Temperature"
        entity = make_entity(MODULE_BOILER, subindex=0, register_def=reg)
        assert entity._attr_name == "Lambda Boiler 1 Actual High Temperature"

    def test_name_heating_circuit(self):
        reg = HEATPUMP_REGISTERS[4]
        entity = make_entity(MODULE_HEATING_CIRCUIT, subindex=2, register_def=reg)
        assert entity._attr_name == "Lambda Heating Circuit 3 Flow Line Temperature"

    def test_name_ambient(self):
        reg = AMBIENT_REGISTERS[2]  # label="Actual Ambient Temperature"
        entity = make_entity(MODULE_AMBIENT, subindex=0, register_def=reg)
        assert entity._attr_name == "Lambda Ambient 1 Actual Ambient Temperature"

    def test_name_emanager(self):
        reg = HEATPUMP_REGISTERS[0]
        entity = make_entity(MODULE_EMANAGER, subindex=0, register_def=reg)
        assert entity._attr_name == "Lambda E-Manager 1 Error State"

    def test_instance_number_is_1_based(self):
        """subindex=0 → instance 1, subindex=4 → instance 5."""
        reg = HEATPUMP_REGISTERS[0]
        for subindex in range(5):
            entity = make_entity(MODULE_HEATPUMP, subindex=subindex, register_def=reg)
            assert f" {subindex + 1} " in entity._attr_name


# ---------------------------------------------------------------------------
# Tests: device_info
# ---------------------------------------------------------------------------

class TestDeviceInfo:
    def test_device_info_has_identifiers(self):
        entity = make_entity()
        di = entity._attr_device_info
        assert "identifiers" in di
        assert (DOMAIN, f"{CONFIG_ENTRY_ID}_heatpump_0") in di["identifiers"]

    def test_device_info_manufacturer_is_lambda(self):
        entity = make_entity()
        assert entity._attr_device_info["manufacturer"] == "Lambda"

    def test_device_info_name_heat_pump_1(self):
        entity = make_entity(MODULE_HEATPUMP, subindex=0)
        assert entity._attr_device_info["name"] == "Lambda Heat Pump 1"

    def test_device_info_name_heat_pump_2(self):
        entity = make_entity(MODULE_HEATPUMP, subindex=1)
        assert entity._attr_device_info["name"] == "Lambda Heat Pump 2"

    def test_device_info_model_heatpump(self):
        entity = make_entity(MODULE_HEATPUMP)
        assert entity._attr_device_info["model"] == "Lambda Heat Pump"

    def test_device_info_model_boiler(self):
        entity = make_entity(MODULE_BOILER)
        assert entity._attr_device_info["model"] == "Lambda Boiler"

    def test_same_module_instance_shares_device(self):
        """Two entities for the same module instance must share the same device identifier."""
        reg1 = HEATPUMP_REGISTERS[0]
        reg2 = HEATPUMP_REGISTERS[4]
        e1 = make_entity(MODULE_HEATPUMP, subindex=0, register_def=reg1)
        e2 = make_entity(MODULE_HEATPUMP, subindex=0, register_def=reg2)
        assert e1._attr_device_info["identifiers"] == e2._attr_device_info["identifiers"]

    def test_different_subindices_have_different_devices(self):
        """Entities for different subindices must have different device identifiers."""
        reg = HEATPUMP_REGISTERS[0]
        e1 = make_entity(MODULE_HEATPUMP, subindex=0, register_def=reg)
        e2 = make_entity(MODULE_HEATPUMP, subindex=1, register_def=reg)
        assert e1._attr_device_info["identifiers"] != e2._attr_device_info["identifiers"]


# ---------------------------------------------------------------------------
# Tests: available
# ---------------------------------------------------------------------------

class TestAvailable:
    def test_available_when_data_present_and_success(self):
        coord = make_coordinator(data={1004: 100}, last_update_success=True)
        entity = LambdaBaseEntity(coord, CONFIG_ENTRY_ID, MODULE_HEATPUMP, 0, HEATPUMP_REGISTERS[4])
        assert entity.available is True

    def test_unavailable_when_data_is_none(self):
        coord = make_coordinator(data=None, last_update_success=True)
        entity = LambdaBaseEntity(coord, CONFIG_ENTRY_ID, MODULE_HEATPUMP, 0, HEATPUMP_REGISTERS[4])
        assert entity.available is False

    def test_unavailable_when_last_update_failed(self):
        coord = make_coordinator(data={1004: 100}, last_update_success=False)
        entity = LambdaBaseEntity(coord, CONFIG_ENTRY_ID, MODULE_HEATPUMP, 0, HEATPUMP_REGISTERS[4])
        assert entity.available is False

    def test_unavailable_when_data_none_and_update_failed(self):
        coord = make_coordinator(data=None, last_update_success=False)
        entity = LambdaBaseEntity(coord, CONFIG_ENTRY_ID, MODULE_HEATPUMP, 0, HEATPUMP_REGISTERS[4])
        assert entity.available is False
