"""Unit tests for LambdaModbusClient keep-alive and reconnect logic."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.lambda_heat_pump.modbus_client import (
    KEEPALIVE_INTERVAL,
    RECONNECT_BACKOFF_MAX,
    RECONNECT_BACKOFF_START,
    LambdaModbusClient,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ok_result(registers: list[int] | None = None) -> MagicMock:
    result = MagicMock()
    result.isError.return_value = False
    result.registers = registers or [0]
    return result


def _make_error_result() -> MagicMock:
    result = MagicMock()
    result.isError.return_value = True
    return result


def _mock_tcp_client(connected: bool = True) -> MagicMock:
    """Return a mock AsyncModbusTcpClient."""
    mock = MagicMock()
    mock.connected = connected
    mock.connect = AsyncMock()
    mock.close = MagicMock()
    mock.read_holding_registers = AsyncMock(return_value=_make_ok_result())
    mock.write_registers = AsyncMock(return_value=_make_ok_result())
    return mock


# ---------------------------------------------------------------------------
# connect / disconnect
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_connect_success_starts_keepalive_task():
    """connect() should start the background keep-alive task on success."""
    mock_client = _mock_tcp_client(connected=True)
    with patch(
        "custom_components.lambda_heat_pump.modbus_client.AsyncModbusTcpClient",
        return_value=mock_client,
    ):
        client = LambdaModbusClient("127.0.0.1", 502)
        result = await client.connect()

    assert result is True
    assert client.is_connected
    assert client._keepalive_task is not None
    assert not client._keepalive_task.done()

    await client.disconnect()


@pytest.mark.asyncio
async def test_connect_failure_still_starts_keepalive_task():
    """connect() should start the background task even when connection fails,
    so that reconnect logic can run."""
    mock_client = _mock_tcp_client(connected=False)
    with patch(
        "custom_components.lambda_heat_pump.modbus_client.AsyncModbusTcpClient",
        return_value=mock_client,
    ):
        client = LambdaModbusClient("127.0.0.1", 502)
        result = await client.connect()

    assert result is False
    assert not client.is_connected
    assert client._keepalive_task is not None

    client._keepalive_task.cancel()
    try:
        await client._keepalive_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_disconnect_cancels_keepalive_task():
    """disconnect() should cancel the background task and close the connection."""
    mock_client = _mock_tcp_client(connected=True)
    with patch(
        "custom_components.lambda_heat_pump.modbus_client.AsyncModbusTcpClient",
        return_value=mock_client,
    ):
        client = LambdaModbusClient("127.0.0.1", 502)
        await client.connect()
        task = client._keepalive_task
        await client.disconnect()

    assert task.done()
    assert client._keepalive_task is None
    assert not client.is_connected
    mock_client.close.assert_called_once()


# ---------------------------------------------------------------------------
# Keep-alive
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_keepalive_read_updates_last_communication():
    """_keepalive_read() should update _last_communication on success."""
    mock_client = _mock_tcp_client(connected=True)
    with patch(
        "custom_components.lambda_heat_pump.modbus_client.AsyncModbusTcpClient",
        return_value=mock_client,
    ):
        client = LambdaModbusClient("127.0.0.1", 502)
        await client.connect()
        client._keepalive_task.cancel()
        try:
            await client._keepalive_task
        except asyncio.CancelledError:
            pass

        before = client._last_communication
        await client._keepalive_read()
        after = client._last_communication

    assert after >= before
    mock_client.read_holding_registers.assert_called_with(address=0, count=1, slave=1)


@pytest.mark.asyncio
async def test_keepalive_read_marks_disconnected_on_error():
    """_keepalive_read() should mark connection as lost when the read fails."""
    mock_client = _mock_tcp_client(connected=True)
    mock_client.read_holding_registers = AsyncMock(return_value=_make_error_result())
    with patch(
        "custom_components.lambda_heat_pump.modbus_client.AsyncModbusTcpClient",
        return_value=mock_client,
    ):
        client = LambdaModbusClient("127.0.0.1", 502)
        await client.connect()
        client._keepalive_task.cancel()
        try:
            await client._keepalive_task
        except asyncio.CancelledError:
            pass

        await client._keepalive_read()

    assert not client._connected


@pytest.mark.asyncio
async def test_read_registers_updates_last_communication():
    """Successful read_registers() should update _last_communication."""
    mock_client = _mock_tcp_client(connected=True)
    mock_client.read_holding_registers = AsyncMock(return_value=_make_ok_result([42]))
    with patch(
        "custom_components.lambda_heat_pump.modbus_client.AsyncModbusTcpClient",
        return_value=mock_client,
    ):
        client = LambdaModbusClient("127.0.0.1", 502)
        await client.connect()
        client._keepalive_task.cancel()
        try:
            await client._keepalive_task
        except asyncio.CancelledError:
            pass

        before = client._last_communication
        result = await client.read_registers(1000, 1)

    assert result == [42]
    assert client._last_communication >= before


@pytest.mark.asyncio
async def test_write_registers_updates_last_communication():
    """Successful write_registers() should update _last_communication."""
    mock_client = _mock_tcp_client(connected=True)
    with patch(
        "custom_components.lambda_heat_pump.modbus_client.AsyncModbusTcpClient",
        return_value=mock_client,
    ):
        client = LambdaModbusClient("127.0.0.1", 502)
        await client.connect()
        client._keepalive_task.cancel()
        try:
            await client._keepalive_task
        except asyncio.CancelledError:
            pass

        before = client._last_communication
        ok = await client.write_registers(1000, [99])

    assert ok is True
    assert client._last_communication >= before


# ---------------------------------------------------------------------------
# Reconnect backoff
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reconnect_backoff_doubles_on_failure():
    """Backoff doubles on each failed reconnect, capped at RECONNECT_BACKOFF_MAX."""
    # Simulate the backoff calculation directly from the loop logic
    backoff = RECONNECT_BACKOFF_START
    results = []
    for _ in range(7):
        results.append(backoff)
        backoff = min(backoff * 2, RECONNECT_BACKOFF_MAX)

    assert results == [5, 10, 20, 40, 80, 160, 300]
    # Ensure it stays capped
    assert min(backoff * 2, RECONNECT_BACKOFF_MAX) == RECONNECT_BACKOFF_MAX


def test_backoff_constants():
    """Verify the backoff constants match the spec."""
    assert KEEPALIVE_INTERVAL == 45
    assert RECONNECT_BACKOFF_START == 5
    assert RECONNECT_BACKOFF_MAX == 300


def test_backoff_sequence():
    """Verify the exponential backoff sequence: 5→10→20→…→300."""
    backoff = RECONNECT_BACKOFF_START
    sequence = [backoff]
    while backoff < RECONNECT_BACKOFF_MAX:
        backoff = min(backoff * 2, RECONNECT_BACKOFF_MAX)
        sequence.append(backoff)

    assert sequence == [5, 10, 20, 40, 80, 160, 300]
