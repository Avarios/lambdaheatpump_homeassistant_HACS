"""Lambda Heat Pump Home Assistant Integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN, PLATFORMS

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Lambda Heat Pump from a config entry."""
    from .modbus_client import LambdaModbusClient
    from .coordinator import LambdaCoordinator

    host: str = entry.data[CONF_HOST]
    port: int = entry.data[CONF_PORT]

    client = LambdaModbusClient(host, port)

    connected = await client.connect()
    if not connected:
        raise ConfigEntryNotReady(
            f"Could not connect to Lambda heat pump at {host}:{port}"
        )

    coordinator = LambdaCoordinator(hass, client, dict(entry.data))

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator,
        "client": client,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Lambda Heat Pump config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        entry_data = hass.data[DOMAIN].pop(entry.entry_id, {})
        coordinator = entry_data.get("coordinator")
        if coordinator is not None:
            coordinator.stop_refresh_task()
        client = entry_data.get("client")
        if client is not None:
            await client.disconnect()

    return unload_ok
