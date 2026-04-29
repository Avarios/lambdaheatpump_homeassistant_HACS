"""Base entity class for Lambda Heat Pump integration."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    MODULE_HEATPUMP,
    MODULE_BOILER,
    MODULE_BUFFER,
    MODULE_SOLAR,
    MODULE_HEATING_CIRCUIT,
    MODULE_AMBIENT,
    MODULE_EMANAGER,
    RegisterDefinition,
)
from .coordinator import LambdaCoordinator

# Human-readable module type labels for display names and device names
_MODULE_DISPLAY_NAMES: dict[str, str] = {
    MODULE_HEATPUMP: "Heat Pump",
    MODULE_BOILER: "Boiler",
    MODULE_BUFFER: "Buffer",
    MODULE_SOLAR: "Solar",
    MODULE_HEATING_CIRCUIT: "Heating Circuit",
    MODULE_AMBIENT: "Ambient",
    MODULE_EMANAGER: "E-Manager",
}

# HA device model strings per module type
_MODULE_MODELS: dict[str, str] = {
    MODULE_HEATPUMP: "Lambda Heat Pump",
    MODULE_BOILER: "Lambda Boiler",
    MODULE_BUFFER: "Lambda Buffer",
    MODULE_SOLAR: "Lambda Solar",
    MODULE_HEATING_CIRCUIT: "Lambda Heating Circuit",
    MODULE_AMBIENT: "Lambda Ambient Sensor",
    MODULE_EMANAGER: "Lambda E-Manager",
}


class LambdaBaseEntity(CoordinatorEntity[LambdaCoordinator]):
    """Base class for all Lambda Heat Pump entities."""

    _attr_has_entity_name = False

    def __init__(
        self,
        coordinator: LambdaCoordinator,
        config_entry_id: str,
        module_type: str,
        subindex: int,
        register_def: RegisterDefinition,
    ) -> None:
        """Initialize the base entity.

        Args:
            coordinator: The LambdaCoordinator instance.
            config_entry_id: The HA config entry ID (used for unique_id and device identifiers).
            module_type: Module type string (e.g. "heatpump", "boiler").
            subindex: Zero-based module instance index.
            register_def: The RegisterDefinition for this entity.
        """
        super().__init__(coordinator)
        self._module_type = module_type
        self._subindex = subindex
        self._register_def = register_def

        # Instance number is 1-based
        instance = subindex + 1
        module_label = _MODULE_DISPLAY_NAMES.get(module_type, module_type.replace("_", " ").title())

        # unique_id: {config_entry_id}_{module_type}_{subindex}_{number}
        self._attr_unique_id = (
            f"{config_entry_id}_{module_type}_{subindex}_{register_def.number}"
        )

        # name: "Lambda {ModuleType} {Instance} {Datapoint}"
        self._attr_name = f"Lambda {module_label} {instance} {register_def.label}"

        # device_info: one HA device per module instance
        device_id = f"{config_entry_id}_{module_type}_{subindex}"
        device_name = f"Lambda {module_label} {instance}"
        model = _MODULE_MODELS.get(module_type, "Lambda Module")

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=device_name,
            manufacturer="Lambda",
            model=model,
        )

    @property
    def available(self) -> bool:
        """Return True only when coordinator has data and last update succeeded."""
        return (
            self.coordinator.data is not None
            and self.coordinator.last_update_success
        )
