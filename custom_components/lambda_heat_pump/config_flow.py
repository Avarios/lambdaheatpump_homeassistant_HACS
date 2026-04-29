"""Config flow for Lambda Heat Pump integration."""
from __future__ import annotations

import ipaddress
import logging
import re
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, FlowResult, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL

from .const import (
    CONF_ENABLE_AMBIENT,
    CONF_ENABLE_EMANAGER,
    CONF_NUM_BOILERS,
    CONF_NUM_BUFFERS,
    CONF_NUM_HEATPUMPS,
    CONF_NUM_HEATING_CIRCUITS,
    CONF_NUM_SOLAR,
    DEFAULT_ENABLE_AMBIENT,
    DEFAULT_ENABLE_EMANAGER,
    DEFAULT_NUM_BOILERS,
    DEFAULT_NUM_BUFFERS,
    DEFAULT_NUM_HEATPUMPS,
    DEFAULT_NUM_HEATING_CIRCUITS,
    DEFAULT_NUM_SOLAR,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .modbus_client import LambdaModbusClient

_LOGGER = logging.getLogger(__name__)

# Hostname regex: allows labels separated by dots, each label 1-63 chars
_HOSTNAME_RE = re.compile(
    r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)*"
    r"[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?$"
)


def _is_valid_host(host: str) -> bool:
    """Return True if *host* is a valid IPv4/IPv6 address or hostname."""
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        pass
    return bool(_HOSTNAME_RE.match(host))


def _build_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    """Build the user-input schema with optional pre-filled defaults."""
    d = defaults or {}
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=d.get(CONF_HOST, "")): str,
            vol.Required(CONF_PORT, default=d.get(CONF_PORT, DEFAULT_PORT)): int,
            vol.Required(
                CONF_NUM_HEATPUMPS,
                default=d.get(CONF_NUM_HEATPUMPS, DEFAULT_NUM_HEATPUMPS),
            ): int,
            vol.Required(
                CONF_NUM_HEATING_CIRCUITS,
                default=d.get(CONF_NUM_HEATING_CIRCUITS, DEFAULT_NUM_HEATING_CIRCUITS),
            ): int,
            vol.Required(
                CONF_NUM_BOILERS,
                default=d.get(CONF_NUM_BOILERS, DEFAULT_NUM_BOILERS),
            ): int,
            vol.Required(
                CONF_NUM_BUFFERS,
                default=d.get(CONF_NUM_BUFFERS, DEFAULT_NUM_BUFFERS),
            ): int,
            vol.Required(
                CONF_NUM_SOLAR,
                default=d.get(CONF_NUM_SOLAR, DEFAULT_NUM_SOLAR),
            ): int,
            vol.Required(
                CONF_ENABLE_AMBIENT,
                default=d.get(CONF_ENABLE_AMBIENT, DEFAULT_ENABLE_AMBIENT),
            ): bool,
            vol.Required(
                CONF_ENABLE_EMANAGER,
                default=d.get(CONF_ENABLE_EMANAGER, DEFAULT_ENABLE_EMANAGER),
            ): bool,
            vol.Required(
                CONF_SCAN_INTERVAL,
                default=d.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            ): int,
        }
    )


def _validate_user_input(user_input: dict[str, Any]) -> dict[str, str]:
    """Validate all fields and return a dict of field -> error_code.

    Returns an empty dict when everything is valid.
    """
    errors: dict[str, str] = {}

    host = user_input.get(CONF_HOST, "").strip()
    if not host or not _is_valid_host(host):
        errors[CONF_HOST] = "invalid_host"

    port = user_input.get(CONF_PORT)
    if not isinstance(port, int) or not (1 <= port <= 65535):
        errors[CONF_PORT] = "invalid_port"

    num_heatpumps = user_input.get(CONF_NUM_HEATPUMPS)
    if not isinstance(num_heatpumps, int) or not (1 <= num_heatpumps <= 5):
        errors[CONF_NUM_HEATPUMPS] = "invalid_num_heatpumps"

    num_heating_circuits = user_input.get(CONF_NUM_HEATING_CIRCUITS)
    if not isinstance(num_heating_circuits, int) or not (0 <= num_heating_circuits <= 12):
        errors[CONF_NUM_HEATING_CIRCUITS] = "invalid_num_heating_circuits"

    num_boilers = user_input.get(CONF_NUM_BOILERS)
    if not isinstance(num_boilers, int) or not (0 <= num_boilers <= 5):
        errors[CONF_NUM_BOILERS] = "invalid_num_boilers"

    num_buffers = user_input.get(CONF_NUM_BUFFERS)
    if not isinstance(num_buffers, int) or not (0 <= num_buffers <= 5):
        errors[CONF_NUM_BUFFERS] = "invalid_num_buffers"

    num_solar = user_input.get(CONF_NUM_SOLAR)
    if not isinstance(num_solar, int) or not (0 <= num_solar <= 2):
        errors[CONF_NUM_SOLAR] = "invalid_num_solar"

    scan_interval = user_input.get(CONF_SCAN_INTERVAL)
    if not isinstance(scan_interval, int) or not (10 <= scan_interval <= 300):
        errors[CONF_SCAN_INTERVAL] = "invalid_scan_interval"

    return errors


class LambdaHeatPumpConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the UI configuration wizard for Lambda Heat Pump."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step shown to the user."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Strip whitespace from host
            user_input[CONF_HOST] = user_input.get(CONF_HOST, "").strip()

            errors = _validate_user_input(user_input)

            if not errors:
                # Attempt a connection test
                client = LambdaModbusClient(
                    host=user_input[CONF_HOST],
                    port=user_input[CONF_PORT],
                )
                try:
                    connected = await client.connect()
                    if not connected:
                        errors["base"] = "cannot_connect"
                    else:
                        await client.disconnect()
                except Exception:  # noqa: BLE001
                    _LOGGER.exception(
                        "Unexpected error testing connection to %s:%s",
                        user_input[CONF_HOST],
                        user_input[CONF_PORT],
                    )
                    errors["base"] = "cannot_connect"

            if not errors:
                # Unique entry per host+port combination
                await self.async_set_unique_id(
                    f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}"
                )
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"Lambda Heat Pump ({user_input[CONF_HOST]})",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_build_schema(user_input),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle reconfiguration of an existing entry."""
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        errors: dict[str, str] = {}

        if user_input is not None:
            user_input[CONF_HOST] = user_input.get(CONF_HOST, "").strip()
            errors = _validate_user_input(user_input)

            if not errors:
                client = LambdaModbusClient(
                    host=user_input[CONF_HOST],
                    port=user_input[CONF_PORT],
                )
                try:
                    connected = await client.connect()
                    if not connected:
                        errors["base"] = "cannot_connect"
                    else:
                        await client.disconnect()
                except Exception:  # noqa: BLE001
                    _LOGGER.exception(
                        "Unexpected error testing connection to %s:%s",
                        user_input[CONF_HOST],
                        user_input[CONF_PORT],
                    )
                    errors["base"] = "cannot_connect"

            if not errors:
                return self.async_update_reload_and_abort(
                    entry,
                    data=user_input,
                )

        current = entry.data if entry else {}
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_build_schema(user_input or current),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> "LambdaHeatPumpOptionsFlow":
        """Return the options flow handler."""
        return LambdaHeatPumpOptionsFlow(config_entry)


class LambdaHeatPumpOptionsFlow(OptionsFlow):
    """Handle options (reconfiguration) for an existing Lambda Heat Pump entry."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Store the config entry for pre-filling defaults."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show the options form pre-filled with current values."""
        errors: dict[str, str] = {}

        if user_input is not None:
            user_input[CONF_HOST] = user_input.get(CONF_HOST, "").strip()
            errors = _validate_user_input(user_input)

            if not errors:
                client = LambdaModbusClient(
                    host=user_input[CONF_HOST],
                    port=user_input[CONF_PORT],
                )
                try:
                    connected = await client.connect()
                    if not connected:
                        errors["base"] = "cannot_connect"
                    else:
                        await client.disconnect()
                except Exception:  # noqa: BLE001
                    _LOGGER.exception(
                        "Unexpected error testing connection to %s:%s",
                        user_input[CONF_HOST],
                        user_input[CONF_PORT],
                    )
                    errors["base"] = "cannot_connect"

            if not errors:
                return self.async_create_entry(title="", data=user_input)

        # Pre-fill with current config entry data
        current = {**self._config_entry.data, **self._config_entry.options}
        return self.async_show_form(
            step_id="init",
            data_schema=_build_schema(user_input or current),
            errors=errors,
        )
