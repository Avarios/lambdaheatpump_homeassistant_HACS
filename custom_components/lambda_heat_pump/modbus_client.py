"""Persistent Modbus TCP client for Lambda heat pump integration."""
from __future__ import annotations

import asyncio
import logging
import time

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException

_LOGGER = logging.getLogger(__name__)

UNIT_ID = 1

# Keep-alive: send a dummy read if no communication for this many seconds
KEEPALIVE_INTERVAL = 45

# Reconnect backoff: start at 5s, double each attempt, cap at 300s
RECONNECT_BACKOFF_START = 5
RECONNECT_BACKOFF_MAX = 300


class LambdaModbusClient:
    """Manages a persistent Modbus TCP connection to a Lambda heat pump.

    All read/write operations use FC 0x03 (read holding registers) and
    FC 0x10 (write multiple registers) with Unit ID 1.  An asyncio.Lock
    serialises concurrent access so that only one Modbus transaction is
    in flight at any time.

    A background task handles keep-alive (dummy read on register 0 every
    45 s of inactivity) and automatic reconnection with exponential backoff
    (5 s → 10 s → 20 s → … → 300 s max).
    """

    def __init__(self, host: str, port: int) -> None:
        self._host = host
        self._port = port
        self._client: AsyncModbusTcpClient | None = None
        self._lock = asyncio.Lock()
        self._connected = False
        self._last_communication: float = 0.0
        self._keepalive_task: asyncio.Task | None = None

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    async def connect(self) -> bool:
        """Establish the TCP connection and start the keep-alive/reconnect task.

        Returns True on success, False on failure.
        """
        async with self._lock:
            if self._connected and self._client is not None and self._client.connected:
                return True

            success = await self._do_connect()

        # Start background task regardless of initial connection result so
        # that reconnect logic can kick in even when the first attempt fails.
        if self._keepalive_task is None or self._keepalive_task.done():
            self._keepalive_task = asyncio.ensure_future(self._keepalive_loop())

        return success

    async def _do_connect(self) -> bool:
        """Low-level connect (must be called with lock held or during init)."""
        self._client = AsyncModbusTcpClient(host=self._host, port=self._port)
        try:
            await self._client.connect()
            if self._client.connected:
                self._connected = True
                self._last_communication = time.monotonic()
                _LOGGER.debug(
                    "Connected to Lambda heat pump at %s:%s",
                    self._host,
                    self._port,
                )
                return True
            else:
                _LOGGER.warning(
                    "Failed to connect to Lambda heat pump at %s:%s",
                    self._host,
                    self._port,
                )
                self._connected = False
                return False
        except Exception as exc:  # noqa: BLE001
            _LOGGER.error(
                "Error connecting to Lambda heat pump at %s:%s: %s",
                self._host,
                self._port,
                exc,
            )
            self._connected = False
            return False

    async def disconnect(self) -> None:
        """Close the TCP connection cleanly and stop the background task."""
        # Stop the background keep-alive/reconnect task first
        if self._keepalive_task is not None and not self._keepalive_task.done():
            self._keepalive_task.cancel()
            try:
                await self._keepalive_task
            except asyncio.CancelledError:
                pass
            self._keepalive_task = None

        async with self._lock:
            if self._client is not None:
                try:
                    self._client.close()
                    _LOGGER.debug(
                        "Disconnected from Lambda heat pump at %s:%s",
                        self._host,
                        self._port,
                    )
                except Exception as exc:  # noqa: BLE001
                    _LOGGER.warning("Error during disconnect: %s", exc)
                finally:
                    self._connected = False
                    self._client = None

    # ------------------------------------------------------------------
    # Background keep-alive / reconnect loop
    # ------------------------------------------------------------------

    async def _keepalive_loop(self) -> None:
        """Background task: keep-alive reads and exponential-backoff reconnect."""
        backoff = RECONNECT_BACKOFF_START
        while True:
            try:
                await asyncio.sleep(1)

                if self.is_connected:
                    # Reset backoff on successful connection
                    backoff = RECONNECT_BACKOFF_START
                    elapsed = time.monotonic() - self._last_communication
                    if elapsed >= KEEPALIVE_INTERVAL:
                        _LOGGER.debug(
                            "Keep-alive: %.0f s since last communication, sending dummy read",
                            elapsed,
                        )
                        await self._keepalive_read()
                else:
                    # Not connected – attempt reconnect after backoff delay
                    _LOGGER.debug(
                        "Connection lost, reconnecting in %s s (backoff)", backoff
                    )
                    await asyncio.sleep(backoff - 1)  # -1 because we already slept 1 s
                    async with self._lock:
                        success = await self._do_connect()
                    if success:
                        _LOGGER.info(
                            "Reconnected to Lambda heat pump at %s:%s",
                            self._host,
                            self._port,
                        )
                        backoff = RECONNECT_BACKOFF_START
                    else:
                        backoff = min(backoff * 2, RECONNECT_BACKOFF_MAX)
                        _LOGGER.debug("Reconnect failed, next attempt in %s s", backoff)

            except asyncio.CancelledError:
                return
            except Exception as exc:  # noqa: BLE001
                _LOGGER.warning("Unexpected error in keep-alive loop: %s", exc)

    async def _keepalive_read(self) -> None:
        """Perform a dummy read on register 0 to keep the connection alive."""
        async with self._lock:
            if not (self._connected and self._client is not None and self._client.connected):
                return
            try:
                result = await self._client.read_holding_registers(
                    address=0, count=1, slave=UNIT_ID
                )
                if result.isError():
                    _LOGGER.warning("Keep-alive read failed: %s", result)
                    self._connected = False
                else:
                    self._last_communication = time.monotonic()
            except Exception as exc:  # noqa: BLE001
                _LOGGER.warning("Keep-alive read exception: %s", exc)
                self._connected = False

    @property
    def is_connected(self) -> bool:
        """Return True if the client is currently connected."""
        return (
            self._connected
            and self._client is not None
            and self._client.connected
        )

    # ------------------------------------------------------------------
    # Register access
    # ------------------------------------------------------------------

    async def read_registers(self, address: int, count: int) -> list[int] | None:
        """Read *count* holding registers starting at *address* (FC 0x03).

        Returns a list of raw UINT16 values, or None on error.
        """
        async with self._lock:
            if not self.is_connected:
                _LOGGER.warning(
                    "read_registers called while not connected (address=%s, count=%s)",
                    address,
                    count,
                )
                return None

            try:
                result = await self._client.read_holding_registers(  # type: ignore[union-attr]
                    address=address,
                    count=count,
                    slave=UNIT_ID,
                )
                if result.isError():
                    _LOGGER.warning(
                        "Modbus read error at address %s (count=%s): %s",
                        address,
                        count,
                        result,
                    )
                    self._connected = False
                    return None

                self._last_communication = time.monotonic()
                return list(result.registers)

            except ModbusException as exc:
                _LOGGER.warning(
                    "ModbusException reading address %s (count=%s): %s",
                    address,
                    count,
                    exc,
                )
                self._connected = False
                return None
            except Exception as exc:  # noqa: BLE001
                _LOGGER.error(
                    "Unexpected error reading address %s (count=%s): %s",
                    address,
                    count,
                    exc,
                )
                self._connected = False
                return None

    async def write_registers(self, address: int, values: list[int]) -> bool:
        """Write *values* to consecutive registers starting at *address* (FC 0x10).

        Returns True on success, False on error.
        """
        async with self._lock:
            if not self.is_connected:
                _LOGGER.warning(
                    "write_registers called while not connected (address=%s)",
                    address,
                )
                return False

            try:
                result = await self._client.write_registers(  # type: ignore[union-attr]
                    address=address,
                    values=values,
                    slave=UNIT_ID,
                )
                if result.isError():
                    _LOGGER.warning(
                        "Modbus write error at address %s: %s",
                        address,
                        result,
                    )
                    self._connected = False
                    return False

                self._last_communication = time.monotonic()
                return True

            except ModbusException as exc:
                _LOGGER.warning(
                    "ModbusException writing address %s: %s",
                    address,
                    exc,
                )
                self._connected = False
                return False
            except Exception as exc:  # noqa: BLE001
                _LOGGER.error(
                    "Unexpected error writing address %s: %s",
                    address,
                    exc,
                )
                self._connected = False
                return False
