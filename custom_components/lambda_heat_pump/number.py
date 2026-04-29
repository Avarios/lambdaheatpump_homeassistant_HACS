"""Number entities for Lambda Heat Pump integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
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


def _is_number_register(reg: RegisterDefinition) -> bool:
    """Return True if this RW register should be a Number entity (not Select/enum)."""
    return reg.access == "RW" and reg.options is None


def _to_uint16(value: int) -> int:
    """Convert a signed INT16 value to UINT16 representation for Modbus."""
    if value < 0:
        return value + 65536
    return value


class LambdaNumber(LambdaBaseEntity, NumberEntity):
    """Number entity for a Lambda Heat Pump read-write register."""

    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        coordinator: LambdaCoordinator,
        config_entry_id: str,
        module_type: str,
        module_index: int,
        subindex: int,
        register_def: RegisterDefinition,
    ) -> None:
        """Initialize the number entity.

        Args:
            coordinator: The LambdaCoordinator instance.
            config_entry_id: HA config entry ID.
            module_type: Module type string (e.g. "heatpump").
            module_index: Modbus index for address calculation (e.g. INDEX_HEATPUMP=1).
            subindex: Zero-based module instance index.
            register_def: The RegisterDefinition for this number entity.
        """
        super().__init__(coordinator, config_entry_id, module_type, subindex, register_def)
        self._module_index = module_index
        self._address = calc_register_address(module_index, subindex, register_def.number)

        # Set HA number attributes from register definition
        if register_def.device_class:
            self._attr_device_class = register_def.device_class
        if register_def.unit:
            self._attr_native_unit_of_measurement = register_def.unit

        self._attr_native_step = register_def.step

        if register_def.min_value is not None:
            self._attr_native_min_value = register_def.min_value
        if register_def.max_value is not None:
            self._attr_native_max_value = register_def.max_value

    @property
    def native_value(self) -> float | None:
        """Return the current value, scaled from raw register data."""
        if self.coordinator.data is None:
            return None
        raw = self.coordinator.data.get(self._address)
        if raw is None:
            return None

        reg = self._register_def

        # Handle INT16 signed interpretation for raw values stored as UINT16
        if reg.data_type == "INT16":
            if raw > 32767:
                raw = raw - 65536

        scaled = raw * reg.scale
        if reg.scale == 1:
            return float(int(raw))
        return round(scaled, 10)

    async def async_set_native_value(self, value: float) -> None:
        """Set the number value, converting to raw and writing via coordinator."""
        reg = self._register_def

        # Validate range before writing
        if reg.min_value is not None and value < reg.min_value:
            _LOGGER.error(
                "Value %s for %s is below minimum %s — write rejected",
                value,
                self._attr_name,
                reg.min_value,
            )
            return
        if reg.max_value is not None and value > reg.max_value:
            _LOGGER.error(
                "Value %s for %s is above maximum %s — write rejected",
                value,
                self._attr_name,
                reg.max_value,
            )
            return

        # Convert scaled value back to raw integer
        raw = round(value / reg.scale)

        # For INT16 registers, convert negative values to UINT16 representation
        if reg.data_type == "INT16":
            raw = _to_uint16(raw)

        await self.coordinator.async_write_register(self._address, raw)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Lambda Heat Pump number entities from a config entry."""
    coordinator: LambdaCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    config = config_entry.data
    entry_id = config_entry.entry_id
    entities: list[LambdaNumber] = []

    def add_numbers(
        module_type: str,
        module_index: int,
        subindex: int,
        registers: list[RegisterDefinition],
    ) -> None:
        for reg in registers:
            if _is_number_register(reg):
                entities.append(
                    LambdaNumber(
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
        add_numbers(MODULE_HEATPUMP, INDEX_HEATPUMP, subindex, HEATPUMP_REGISTERS)

    # Boilers (Index 2, Subindex 0..num_boilers-1)
    num_boilers = config.get(CONF_NUM_BOILERS, 0)
    for subindex in range(num_boilers):
        add_numbers(MODULE_BOILER, INDEX_BOILER, subindex, BOILER_REGISTERS)

    # Buffers (Index 3, Subindex 0..num_buffers-1)
    num_buffers = config.get(CONF_NUM_BUFFERS, 0)
    for subindex in range(num_buffers):
        add_numbers(MODULE_BUFFER, INDEX_BUFFER, subindex, BUFFER_REGISTERS)

    # Solar (Index 4, Subindex 0..num_solar-1)
    num_solar = config.get(CONF_NUM_SOLAR, 0)
    for subindex in range(num_solar):
        add_numbers(MODULE_SOLAR, INDEX_SOLAR, subindex, SOLAR_REGISTERS)

    # Heating circuits (Index 5, Subindex 0..num_heating_circuits-1)
    num_hc = config.get(CONF_NUM_HEATING_CIRCUITS, 0)
    for subindex in range(num_hc):
        add_numbers(MODULE_HEATING_CIRCUIT, INDEX_HEATING_CIRCUIT, subindex, HEATING_CIRCUIT_REGISTERS)

    # General Ambient (Index 0, Subindex 0) — only if enabled
    # Includes ambient_temp_actual (RW, Register 02)
    if config.get(CONF_ENABLE_AMBIENT, False):
        add_numbers(MODULE_AMBIENT, INDEX_GENERAL, SUBINDEX_AMBIENT, AMBIENT_REGISTERS)

    # General E-Manager (Index 0, Subindex 1) — only if enabled
    # Includes emanager_actual_power (RW, Register 02)
    if config.get(CONF_ENABLE_EMANAGER, False):
        add_numbers(MODULE_EMANAGER, INDEX_GENERAL, SUBINDEX_EMANAGER, EMANAGER_REGISTERS)

    async_add_entities(entities)
