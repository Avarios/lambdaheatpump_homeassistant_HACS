"""Sensor entities for Lambda Heat Pump integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_NUM_HEATPUMPS,
    CONF_NUM_BOILERS,
    CONF_NUM_BUFFERS,
    CONF_NUM_SOLAR,
    CONF_NUM_HEATING_CIRCUITS,
    CONF_ENABLE_AMBIENT,
    CONF_ENABLE_EMANAGER,
    DOMAIN,
    INDEX_GENERAL,
    INDEX_HEATPUMP,
    INDEX_BOILER,
    INDEX_BUFFER,
    INDEX_SOLAR,
    INDEX_HEATING_CIRCUIT,
    SUBINDEX_AMBIENT,
    SUBINDEX_EMANAGER,
    MODULE_HEATPUMP,
    MODULE_BOILER,
    MODULE_BUFFER,
    MODULE_SOLAR,
    MODULE_HEATING_CIRCUIT,
    MODULE_AMBIENT,
    MODULE_EMANAGER,
    HEATPUMP_REGISTERS,
    BOILER_REGISTERS,
    BUFFER_REGISTERS,
    SOLAR_REGISTERS,
    HEATING_CIRCUIT_REGISTERS,
    AMBIENT_REGISTERS,
    EMANAGER_REGISTERS,
    RegisterDefinition,
    calc_register_address,
)
from .coordinator import LambdaCoordinator
from .entity_base import LambdaBaseEntity

_LOGGER = logging.getLogger(__name__)

# Binary registers that belong to binary_sensor.py, not sensor.py
_BINARY_REGISTER_NAMES = {"relay_2nd_stage", "boiler_pump_state"}


def _is_sensor_register(reg: RegisterDefinition) -> bool:
    """Return True if this RO register should be a sensor (not binary_sensor)."""
    return reg.access == "RO" and reg.name not in _BINARY_REGISTER_NAMES


def _combine_int32(high: int, low: int) -> int:
    """Combine two UINT16 register values into a signed INT32.

    The Modbus convention is: high word at the lower address, low word at address+1.
    The combined 32-bit value is interpreted as a signed integer.
    """
    raw = ((high & 0xFFFF) << 16) | (low & 0xFFFF)
    # Convert to signed INT32
    if raw >= 0x80000000:
        raw -= 0x100000000
    return raw


class LambdaSensor(LambdaBaseEntity, SensorEntity):
    """Sensor entity for a Lambda Heat Pump read-only register."""

    def __init__(
        self,
        coordinator: LambdaCoordinator,
        config_entry_id: str,
        module_type: str,
        module_index: int,
        subindex: int,
        register_def: RegisterDefinition,
    ) -> None:
        """Initialize the sensor.

        Args:
            coordinator: The LambdaCoordinator instance.
            config_entry_id: HA config entry ID.
            module_type: Module type string (e.g. "heatpump").
            module_index: Modbus index for address calculation (e.g. INDEX_HEATPUMP=1).
            subindex: Zero-based module instance index.
            register_def: The RegisterDefinition for this sensor.
        """
        super().__init__(coordinator, config_entry_id, module_type, subindex, register_def)
        self._module_index = module_index
        self._address = calc_register_address(module_index, subindex, register_def.number)

        # HA sensor attributes from register definition
        if register_def.device_class:
            self._attr_device_class = register_def.device_class
        if register_def.state_class:
            self._attr_state_class = register_def.state_class
        if register_def.unit:
            self._attr_native_unit_of_measurement = register_def.unit

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        if self.coordinator.data is None:
            return None

        raw = self.coordinator.data.get(self._address)
        if raw is None:
            return None

        reg = self._register_def

        # INT32: combine two consecutive 16-bit registers
        if reg.data_type == "INT32":
            high_raw = self.coordinator.data.get(self._address)
            low_raw = self.coordinator.data.get(self._address + 1)
            if high_raw is None or low_raw is None:
                return None
            combined = _combine_int32(high_raw, low_raw)
            return combined * reg.scale if reg.scale != 1 else combined

        # Enum: return string label
        if reg.options is not None:
            return reg.options.get(raw, str(raw))

        # Numeric: apply scale
        scaled = raw * reg.scale
        # Return int when scale is 1 to avoid float representation
        if reg.scale == 1:
            return int(raw)
        return round(scaled, 10)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Lambda Heat Pump sensor entities from a config entry."""
    coordinator: LambdaCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    config = config_entry.data
    entry_id = config_entry.entry_id
    entities: list[LambdaSensor] = []

    # Helper to add sensors for a module type
    def add_sensors(
        module_type: str,
        module_index: int,
        subindex: int,
        registers: list[RegisterDefinition],
    ) -> None:
        for reg in registers:
            if _is_sensor_register(reg):
                entities.append(
                    LambdaSensor(
                        coordinator,
                        entry_id,
                        module_type,
                        module_index,
                        subindex,
                        reg,
                    )
                )

    # Heat pumps (Index 1, Subindex 0..num_heatpumps-1)
    num_hp = config.get(CONF_NUM_HEATPUMPS, 0)
    for subindex in range(num_hp):
        add_sensors(MODULE_HEATPUMP, INDEX_HEATPUMP, subindex, HEATPUMP_REGISTERS)

    # Boilers (Index 2, Subindex 0..num_boilers-1)
    num_boilers = config.get(CONF_NUM_BOILERS, 0)
    for subindex in range(num_boilers):
        add_sensors(MODULE_BOILER, INDEX_BOILER, subindex, BOILER_REGISTERS)

    # Buffers (Index 3, Subindex 0..num_buffers-1)
    num_buffers = config.get(CONF_NUM_BUFFERS, 0)
    for subindex in range(num_buffers):
        add_sensors(MODULE_BUFFER, INDEX_BUFFER, subindex, BUFFER_REGISTERS)

    # Solar (Index 4, Subindex 0..num_solar-1)
    num_solar = config.get(CONF_NUM_SOLAR, 0)
    for subindex in range(num_solar):
        add_sensors(MODULE_SOLAR, INDEX_SOLAR, subindex, SOLAR_REGISTERS)

    # Heating circuits (Index 5, Subindex 0..num_heating_circuits-1)
    num_hc = config.get(CONF_NUM_HEATING_CIRCUITS, 0)
    for subindex in range(num_hc):
        add_sensors(MODULE_HEATING_CIRCUIT, INDEX_HEATING_CIRCUIT, subindex, HEATING_CIRCUIT_REGISTERS)

    # General Ambient (Index 0, Subindex 0) — only if enabled
    if config.get(CONF_ENABLE_AMBIENT, False):
        add_sensors(MODULE_AMBIENT, INDEX_GENERAL, SUBINDEX_AMBIENT, AMBIENT_REGISTERS)

    # General E-Manager (Index 0, Subindex 1) — only if enabled
    if config.get(CONF_ENABLE_EMANAGER, False):
        add_sensors(MODULE_EMANAGER, INDEX_GENERAL, SUBINDEX_EMANAGER, EMANAGER_REGISTERS)

    async_add_entities(entities)
