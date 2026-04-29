"""Select entities for Lambda Heat Pump integration."""
from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
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


def _is_select_register(reg: RegisterDefinition) -> bool:
    """Return True if this RW register should be a Select entity (enum)."""
    return reg.access == "RW" and reg.options is not None


def _to_uint16(value: int) -> int:
    """Convert a signed INT16 value to UINT16 representation for Modbus."""
    if value < 0:
        return value + 65536
    return value


class LambdaSelect(LambdaBaseEntity, SelectEntity):
    """Select entity for a Lambda Heat Pump read-write enum register."""

    def __init__(
        self,
        coordinator: LambdaCoordinator,
        config_entry_id: str,
        module_type: str,
        module_index: int,
        subindex: int,
        register_def: RegisterDefinition,
    ) -> None:
        """Initialize the select entity.

        Args:
            coordinator: The LambdaCoordinator instance.
            config_entry_id: HA config entry ID.
            module_type: Module type string (e.g. "heatpump").
            module_index: Modbus index for address calculation (e.g. INDEX_HEATPUMP=1).
            subindex: Zero-based module instance index.
            register_def: The RegisterDefinition for this select entity.
        """
        super().__init__(coordinator, config_entry_id, module_type, subindex, register_def)
        self._module_index = module_index
        self._address = calc_register_address(module_index, subindex, register_def.number)

        # Build the list of option strings from the enum dict
        self._attr_options = list(register_def.options.values())  # type: ignore[union-attr]

    @property
    def current_option(self) -> str | None:
        """Return the currently selected option string."""
        if self.coordinator.data is None:
            return None
        raw = self.coordinator.data.get(self._address)
        if raw is None:
            return None

        reg = self._register_def

        # Interpret raw value as signed INT16 if needed
        if reg.data_type == "INT16" and raw > 32767:
            raw = raw - 65536

        # Map raw value to string; fall back to str(raw) for unknown values
        return reg.options.get(raw, str(raw))  # type: ignore[union-attr]

    async def async_select_option(self, option: str) -> None:
        """Select an option by string, reverse-mapping to raw int and writing."""
        reg = self._register_def

        # Reverse-lookup: find the raw int key for the given option string
        raw: int | None = None
        for key, val in reg.options.items():  # type: ignore[union-attr]
            if val == option:
                raw = key
                break

        if raw is None:
            _LOGGER.error(
                "Option '%s' not found in options for %s — write rejected",
                option,
                self._attr_name,
            )
            return

        # For INT16 registers, convert negative values to UINT16 for Modbus
        if reg.data_type == "INT16":
            raw = _to_uint16(raw)

        await self.coordinator.async_write_register(self._address, raw)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Lambda Heat Pump select entities from a config entry."""
    coordinator: LambdaCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    config = config_entry.data
    entry_id = config_entry.entry_id
    entities: list[LambdaSelect] = []

    def add_selects(
        module_type: str,
        module_index: int,
        subindex: int,
        registers: list[RegisterDefinition],
    ) -> None:
        for reg in registers:
            if _is_select_register(reg):
                entities.append(
                    LambdaSelect(
                        coordinator,
                        entry_id,
                        module_type,
                        module_index,
                        subindex,
                        reg,
                    )
                )

    # Heat pumps — request_type (Register 15, RW, INT16, HP_REQUEST_TYPE)
    num_hp = config.get(CONF_NUM_HEATPUMPS, 0)
    for subindex in range(num_hp):
        add_selects(MODULE_HEATPUMP, INDEX_HEATPUMP, subindex, HEATPUMP_REGISTERS)

    # Boilers — no RW enum registers
    num_boilers = config.get(CONF_NUM_BOILERS, 0)
    for subindex in range(num_boilers):
        add_selects(MODULE_BOILER, INDEX_BOILER, subindex, BOILER_REGISTERS)

    # Buffers — buffer_request_type (Register 05, RW, INT16, BUFFER_REQUEST_TYPE)
    num_buffers = config.get(CONF_NUM_BUFFERS, 0)
    for subindex in range(num_buffers):
        add_selects(MODULE_BUFFER, INDEX_BUFFER, subindex, BUFFER_REGISTERS)

    # Solar — no RW enum registers
    num_solar = config.get(CONF_NUM_SOLAR, 0)
    for subindex in range(num_solar):
        add_selects(MODULE_SOLAR, INDEX_SOLAR, subindex, SOLAR_REGISTERS)

    # Heating circuits — hc_operating_mode (Register 06, RW, INT16, HC_OPERATING_MODE)
    num_hc = config.get(CONF_NUM_HEATING_CIRCUITS, 0)
    for subindex in range(num_hc):
        add_selects(MODULE_HEATING_CIRCUIT, INDEX_HEATING_CIRCUIT, subindex, HEATING_CIRCUIT_REGISTERS)

    # General Ambient — no RW enum registers
    if config.get(CONF_ENABLE_AMBIENT, False):
        add_selects(MODULE_AMBIENT, INDEX_GENERAL, SUBINDEX_AMBIENT, AMBIENT_REGISTERS)

    # General E-Manager — no RW enum registers
    if config.get(CONF_ENABLE_EMANAGER, False):
        add_selects(MODULE_EMANAGER, INDEX_GENERAL, SUBINDEX_EMANAGER, EMANAGER_REGISTERS)

    async_add_entities(entities)
