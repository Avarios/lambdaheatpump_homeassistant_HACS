"""Binary sensor entities for Lambda Heat Pump integration."""
from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_NUM_HEATPUMPS,
    CONF_NUM_BOILERS,
    DOMAIN,
    INDEX_HEATPUMP,
    INDEX_BOILER,
    MODULE_HEATPUMP,
    MODULE_BOILER,
    HEATPUMP_REGISTERS,
    BOILER_REGISTERS,
    RegisterDefinition,
    calc_register_address,
)
from .coordinator import LambdaCoordinator
from .entity_base import LambdaBaseEntity

_LOGGER = logging.getLogger(__name__)

# Register names that are binary (0=OFF, non-zero=ON)
_BINARY_REGISTER_NAMES = {"relay_2nd_stage", "boiler_pump_state"}


def _is_binary_register(reg: RegisterDefinition) -> bool:
    """Return True if this RO register should be a binary sensor."""
    return reg.access == "RO" and reg.name in _BINARY_REGISTER_NAMES


class LambdaBinarySensor(LambdaBaseEntity, BinarySensorEntity):
    """Binary sensor entity for a Lambda Heat Pump binary read-only register."""

    def __init__(
        self,
        coordinator: LambdaCoordinator,
        config_entry_id: str,
        module_type: str,
        module_index: int,
        subindex: int,
        register_def: RegisterDefinition,
    ) -> None:
        """Initialize the binary sensor.

        Args:
            coordinator: The LambdaCoordinator instance.
            config_entry_id: HA config entry ID.
            module_type: Module type string (e.g. "heatpump").
            module_index: Modbus index for address calculation (e.g. INDEX_HEATPUMP=1).
            subindex: Zero-based module instance index.
            register_def: The RegisterDefinition for this binary sensor.
        """
        super().__init__(coordinator, config_entry_id, module_type, subindex, register_def)
        self._module_index = module_index
        self._address = calc_register_address(module_index, subindex, register_def.number)

    @property
    def is_on(self) -> bool | None:
        """Return True if the binary register value is non-zero."""
        if self.coordinator.data is None:
            return None
        raw = self.coordinator.data.get(self._address)
        if raw is None:
            return None
        return raw != 0


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Lambda Heat Pump binary sensor entities from a config entry."""
    coordinator: LambdaCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    config = config_entry.data
    entry_id = config_entry.entry_id
    entities: list[LambdaBinarySensor] = []

    def add_binary_sensors(
        module_type: str,
        module_index: int,
        subindex: int,
        registers: list[RegisterDefinition],
    ) -> None:
        for reg in registers:
            if _is_binary_register(reg):
                entities.append(
                    LambdaBinarySensor(
                        coordinator,
                        entry_id,
                        module_type,
                        module_index,
                        subindex,
                        reg,
                    )
                )

    # Heat pumps (Index 1) — relay_2nd_stage (Register 19)
    num_hp = config.get(CONF_NUM_HEATPUMPS, 0)
    for subindex in range(num_hp):
        add_binary_sensors(MODULE_HEATPUMP, INDEX_HEATPUMP, subindex, HEATPUMP_REGISTERS)

    # Boilers (Index 2) — boiler_pump_state (Register 05)
    num_boilers = config.get(CONF_NUM_BOILERS, 0)
    for subindex in range(num_boilers):
        add_binary_sensors(MODULE_BOILER, INDEX_BOILER, subindex, BOILER_REGISTERS)

    async_add_entities(entities)
