"""DataUpdateCoordinator for Lambda Heat Pump integration."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_NUM_HEATPUMPS,
    CONF_NUM_HEATING_CIRCUITS,
    CONF_NUM_BOILERS,
    CONF_NUM_BUFFERS,
    CONF_NUM_SOLAR,
    CONF_ENABLE_AMBIENT,
    CONF_ENABLE_EMANAGER,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    INDEX_GENERAL,
    INDEX_HEATPUMP,
    INDEX_BOILER,
    INDEX_BUFFER,
    INDEX_SOLAR,
    INDEX_HEATING_CIRCUIT,
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
)
from .modbus_client import LambdaModbusClient

_LOGGER = logging.getLogger(__name__)

# Maximum gap between register addresses to still treat them as one contiguous block
_MAX_BLOCK_GAP = 10

# RW registers with Number 00-49 must be re-written every 4 minutes (240 s)
# to prevent the control unit's 5-minute timeout from discarding them.
_RW_REFRESH_INTERVAL = 240  # seconds

# A register Number is "00-49" when address % 100 < 50
_RW_NUMBER_THRESHOLD = 50

# Heat pump request_type register Number is 15; password is 14
_REQUEST_TYPE_NUMBER = 15
_PASSWORD_NUMBER = 14


class LambdaCoordinator(DataUpdateCoordinator[dict[int, int]]):
    """Coordinator that polls all configured Lambda heat pump registers."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: LambdaModbusClient,
        config: dict,
    ) -> None:
        scan_interval = config.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self._client = client
        self._config = config
        self._register_addresses: list[int] = self._build_register_list()
        # Stores {address: raw_value} for RW registers with Number 00-49
        self._active_writes: dict[int, int] = {}
        self._refresh_task: asyncio.Task | None = None

    # ------------------------------------------------------------------
    # Register list construction
    # ------------------------------------------------------------------

    def _build_register_list(self) -> list[int]:
        """Build the sorted list of all register addresses to poll."""
        addresses: set[int] = set()

        # Heat pumps (Index 1, Subindex 0..num_heatpumps-1)
        num_hp = self._config.get(CONF_NUM_HEATPUMPS, 0)
        for subindex in range(num_hp):
            for reg in HEATPUMP_REGISTERS:
                addr = calc_register_address(INDEX_HEATPUMP, subindex, reg.number)
                addresses.add(addr)
                # INT32 registers occupy two consecutive addresses
                if reg.data_type == "INT32":
                    addresses.add(addr + 1)

        # Boilers (Index 2, Subindex 0..num_boilers-1)
        num_boilers = self._config.get(CONF_NUM_BOILERS, 0)
        for subindex in range(num_boilers):
            for reg in BOILER_REGISTERS:
                addresses.add(calc_register_address(INDEX_BOILER, subindex, reg.number))

        # Buffers (Index 3, Subindex 0..num_buffers-1)
        num_buffers = self._config.get(CONF_NUM_BUFFERS, 0)
        for subindex in range(num_buffers):
            for reg in BUFFER_REGISTERS:
                addresses.add(calc_register_address(INDEX_BUFFER, subindex, reg.number))

        # Solar (Index 4, Subindex 0..num_solar-1)
        num_solar = self._config.get(CONF_NUM_SOLAR, 0)
        for subindex in range(num_solar):
            for reg in SOLAR_REGISTERS:
                addresses.add(calc_register_address(INDEX_SOLAR, subindex, reg.number))

        # Heating circuits (Index 5, Subindex 0..num_heating_circuits-1)
        num_hc = self._config.get(CONF_NUM_HEATING_CIRCUITS, 0)
        for subindex in range(num_hc):
            for reg in HEATING_CIRCUIT_REGISTERS:
                addresses.add(calc_register_address(INDEX_HEATING_CIRCUIT, subindex, reg.number))

        # General Ambient (Index 0, Subindex 0)
        if self._config.get(CONF_ENABLE_AMBIENT, False):
            for reg in AMBIENT_REGISTERS:
                addresses.add(calc_register_address(INDEX_GENERAL, SUBINDEX_AMBIENT, reg.number))

        # General E-Manager (Index 0, Subindex 1)
        if self._config.get(CONF_ENABLE_EMANAGER, False):
            for reg in EMANAGER_REGISTERS:
                addresses.add(calc_register_address(INDEX_GENERAL, SUBINDEX_EMANAGER, reg.number))

        return sorted(addresses)

    # ------------------------------------------------------------------
    # Block grouping
    # ------------------------------------------------------------------

    @staticmethod
    def _group_into_blocks(addresses: list[int]) -> list[tuple[int, int]]:
        """Group sorted addresses into contiguous read blocks.

        Returns a list of (start_address, count) tuples.  Addresses within
        _MAX_BLOCK_GAP of each other are merged into a single block so that
        the number of Modbus requests is minimised.
        """
        if not addresses:
            return []

        blocks: list[tuple[int, int]] = []
        block_start = addresses[0]
        block_end = addresses[0]

        for addr in addresses[1:]:
            if addr - block_end <= _MAX_BLOCK_GAP:
                block_end = addr
            else:
                blocks.append((block_start, block_end - block_start + 1))
                block_start = addr
                block_end = addr

        blocks.append((block_start, block_end - block_start + 1))
        return blocks

    # ------------------------------------------------------------------
    # DataUpdateCoordinator interface
    # ------------------------------------------------------------------

    async def _async_update_data(self) -> dict[int, int]:
        """Read all configured registers and return {address: raw_value}."""
        if not self._register_addresses:
            return {}

        blocks = self._group_into_blocks(self._register_addresses)
        result: dict[int, int] = {}

        for start, count in blocks:
            values = await self._client.read_registers(start, count)
            if values is None:
                raise UpdateFailed(
                    f"Failed to read {count} registers starting at address {start}"
                )
            for offset, value in enumerate(values):
                result[start + offset] = value

        # Return only the addresses we actually care about
        return {addr: result[addr] for addr in self._register_addresses if addr in result}

    # ------------------------------------------------------------------
    # RW refresh mechanism (Requirements 3.2, 5.2, 5.3)
    # ------------------------------------------------------------------

    async def async_write_register(self, address: int, value: int) -> bool:
        """Write a register value and store it for periodic refresh if Number 00-49.

        For address where ``address % 100 == 15`` (request_type), the password
        register (address - 1) is written first if it is present in
        ``_active_writes``.
        """
        # Special case: writing request_type (Number 15) → write password first
        if address % 100 == _REQUEST_TYPE_NUMBER:
            password_address = address - 1  # Number 14
            if password_address in self._active_writes:
                pw_ok = await self._client.write_registers(
                    password_address, [self._active_writes[password_address]]
                )
                if not pw_ok:
                    _LOGGER.warning(
                        "Failed to write password register %d before request_type",
                        password_address,
                    )

        ok = await self._client.write_registers(address, [value])
        if not ok:
            _LOGGER.warning("Failed to write register %d with value %d", address, value)
            return False

        # Store in refresh store only for Number 00-49
        if address % 100 < _RW_NUMBER_THRESHOLD:
            self._active_writes[address] = value

        # Start the background refresh task on first write if not already running
        self._ensure_refresh_task()

        return True

    async def _async_refresh_rw_registers(self) -> None:
        """Re-write all active RW registers (Number 00-49) to prevent timeout."""
        if not self._active_writes:
            return
        for address, value in list(self._active_writes.items()):
            ok = await self._client.write_registers(address, [value])
            if not ok:
                _LOGGER.warning(
                    "RW refresh failed for register %d (value %d)", address, value
                )

    async def _refresh_loop(self) -> None:
        """Background task: call _async_refresh_rw_registers every 4 minutes."""
        try:
            while True:
                await asyncio.sleep(_RW_REFRESH_INTERVAL)
                await self._async_refresh_rw_registers()
        except asyncio.CancelledError:
            pass

    def _ensure_refresh_task(self) -> None:
        """Start the background refresh task if it is not already running."""
        if self._refresh_task is None or self._refresh_task.done():
            self._refresh_task = asyncio.ensure_future(self._refresh_loop())

    def stop_refresh_task(self) -> None:
        """Cancel the background refresh task (call on integration unload)."""
        if self._refresh_task and not self._refresh_task.done():
            self._refresh_task.cancel()
            self._refresh_task = None
