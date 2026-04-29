"""Unit tests for LambdaCoordinator (task 4.1)."""
from __future__ import annotations

import sys
import types
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

# ---------------------------------------------------------------------------
# Stubs for homeassistant modules (must happen before importing coordinator)
# ---------------------------------------------------------------------------

def _ensure_stub(name: str) -> types.ModuleType:
    if name not in sys.modules:
        sys.modules[name] = types.ModuleType(name)
    return sys.modules[name]


for _mod in [
    "homeassistant",
    "homeassistant.core",
    "homeassistant.helpers",
    "homeassistant.helpers.update_coordinator",
]:
    _ensure_stub(_mod)

# Minimal DataUpdateCoordinator stub (must support generic subscript like [dict[int,int]])
class _FakeDataUpdateCoordinator:
    def __init__(self, hass, logger, *, name, update_interval):
        self.hass = hass
        self.logger = logger
        self.name = name
        self.update_interval = update_interval
        self.data = None

    async def async_config_entry_first_refresh(self):
        self.data = await self._async_update_data()

    def __class_getitem__(cls, item):
        return cls

_uc = sys.modules["homeassistant.helpers.update_coordinator"]
_uc.DataUpdateCoordinator = _FakeDataUpdateCoordinator  # type: ignore[attr-defined]

class _UpdateFailed(Exception):
    pass

_uc.UpdateFailed = _UpdateFailed  # type: ignore[attr-defined]

_core = sys.modules["homeassistant.core"]
_core.HomeAssistant = object  # type: ignore[attr-defined]

# ---------------------------------------------------------------------------
# Now import the module under test
# ---------------------------------------------------------------------------

from custom_components.lambda_heat_pump.coordinator import LambdaCoordinator, _MAX_BLOCK_GAP
from custom_components.lambda_heat_pump.const import (
    calc_register_address,
    INDEX_HEATPUMP,
    INDEX_BOILER,
    INDEX_BUFFER,
    INDEX_SOLAR,
    INDEX_HEATING_CIRCUIT,
    INDEX_GENERAL,
    SUBINDEX_AMBIENT,
    SUBINDEX_EMANAGER,
    HEATPUMP_REGISTERS,
    BOILER_REGISTERS,
    BUFFER_REGISTERS,
    SOLAR_REGISTERS,
    HEATING_CIRCUIT_REGISTERS,
    AMBIENT_REGISTERS,
    EMANAGER_REGISTERS,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_coordinator(config: dict, read_return=None) -> tuple[LambdaCoordinator, MagicMock]:
    """Create a coordinator with a mocked client."""
    client = MagicMock()
    if read_return is None:
        # Default: return a list of zeros for any read
        async def _read(address, count):
            return [0] * count
        client.read_registers = _read
    else:
        client.read_registers = AsyncMock(return_value=read_return)
    hass = MagicMock()
    coord = LambdaCoordinator(hass, client, config)
    return coord, client


# ---------------------------------------------------------------------------
# Tests: _build_register_list
# ---------------------------------------------------------------------------

class TestBuildRegisterList:
    def test_empty_config_returns_no_addresses(self):
        coord, _ = make_coordinator({})
        assert coord._register_addresses == []

    def test_single_heatpump_includes_all_hp_registers(self):
        coord, _ = make_coordinator({"num_heatpumps": 1})
        addresses = coord._register_addresses
        for reg in HEATPUMP_REGISTERS:
            addr = calc_register_address(INDEX_HEATPUMP, 0, reg.number)
            assert addr in addresses, f"Expected address {addr} for HP reg {reg.number}"

    def test_int32_registers_include_second_word(self):
        coord, _ = make_coordinator({"num_heatpumps": 1})
        addresses = coord._register_addresses
        # stat_energy_e is INT32 at number 20 → addresses 1020 and 1021
        assert 1020 in addresses
        assert 1021 in addresses
        # stat_energy_q is INT32 at number 22 → addresses 1022 and 1023
        assert 1022 in addresses
        assert 1023 in addresses

    def test_two_heatpumps_includes_both_subindices(self):
        coord, _ = make_coordinator({"num_heatpumps": 2})
        addresses = coord._register_addresses
        # HP1 subindex 0, register 4 → 1004
        assert 1004 in addresses
        # HP2 subindex 1, register 4 → 1104
        assert 1104 in addresses

    def test_boiler_registers_included(self):
        coord, _ = make_coordinator({"num_boilers": 1})
        addresses = coord._register_addresses
        for reg in BOILER_REGISTERS:
            addr = calc_register_address(INDEX_BOILER, 0, reg.number)
            assert addr in addresses

    def test_buffer_registers_included(self):
        coord, _ = make_coordinator({"num_buffers": 1})
        addresses = coord._register_addresses
        for reg in BUFFER_REGISTERS:
            addr = calc_register_address(INDEX_BUFFER, 0, reg.number)
            assert addr in addresses

    def test_solar_registers_included(self):
        coord, _ = make_coordinator({"num_solar": 1})
        addresses = coord._register_addresses
        for reg in SOLAR_REGISTERS:
            addr = calc_register_address(INDEX_SOLAR, 0, reg.number)
            assert addr in addresses

    def test_heating_circuit_registers_included(self):
        coord, _ = make_coordinator({"num_heating_circuits": 1})
        addresses = coord._register_addresses
        for reg in HEATING_CIRCUIT_REGISTERS:
            addr = calc_register_address(INDEX_HEATING_CIRCUIT, 0, reg.number)
            assert addr in addresses

    def test_ambient_disabled_by_default(self):
        coord, _ = make_coordinator({})
        addresses = coord._register_addresses
        for reg in AMBIENT_REGISTERS:
            addr = calc_register_address(INDEX_GENERAL, SUBINDEX_AMBIENT, reg.number)
            assert addr not in addresses

    def test_ambient_enabled(self):
        coord, _ = make_coordinator({"enable_ambient": True})
        addresses = coord._register_addresses
        for reg in AMBIENT_REGISTERS:
            addr = calc_register_address(INDEX_GENERAL, SUBINDEX_AMBIENT, reg.number)
            assert addr in addresses

    def test_emanager_enabled(self):
        coord, _ = make_coordinator({"enable_emanager": True})
        addresses = coord._register_addresses
        for reg in EMANAGER_REGISTERS:
            addr = calc_register_address(INDEX_GENERAL, SUBINDEX_EMANAGER, reg.number)
            assert addr in addresses

    def test_addresses_are_sorted(self):
        coord, _ = make_coordinator({
            "num_heatpumps": 2,
            "num_boilers": 1,
            "enable_ambient": True,
        })
        addresses = coord._register_addresses
        assert addresses == sorted(addresses)

    def test_no_duplicate_addresses(self):
        coord, _ = make_coordinator({
            "num_heatpumps": 3,
            "num_boilers": 2,
            "num_buffers": 2,
            "num_solar": 1,
            "num_heating_circuits": 4,
            "enable_ambient": True,
            "enable_emanager": True,
        })
        addresses = coord._register_addresses
        assert len(addresses) == len(set(addresses))


# ---------------------------------------------------------------------------
# Tests: _group_into_blocks
# ---------------------------------------------------------------------------

class TestGroupIntoBlocks:
    def test_empty_list(self):
        assert LambdaCoordinator._group_into_blocks([]) == []

    def test_single_address(self):
        assert LambdaCoordinator._group_into_blocks([5]) == [(5, 1)]

    def test_consecutive_addresses_merged(self):
        blocks = LambdaCoordinator._group_into_blocks([10, 11, 12, 13])
        assert blocks == [(10, 4)]

    def test_gap_within_threshold_merged(self):
        # Gap of _MAX_BLOCK_GAP should still be merged
        blocks = LambdaCoordinator._group_into_blocks([10, 10 + _MAX_BLOCK_GAP])
        assert len(blocks) == 1

    def test_gap_exceeding_threshold_splits(self):
        # Gap of _MAX_BLOCK_GAP + 1 should split
        blocks = LambdaCoordinator._group_into_blocks([10, 10 + _MAX_BLOCK_GAP + 1])
        assert len(blocks) == 2
        assert blocks[0] == (10, 1)
        assert blocks[1] == (10 + _MAX_BLOCK_GAP + 1, 1)

    def test_multiple_groups(self):
        # Two separate clusters
        blocks = LambdaCoordinator._group_into_blocks([1, 2, 3, 100, 101, 102])
        assert len(blocks) == 2
        assert blocks[0] == (1, 3)
        assert blocks[1] == (100, 3)

    def test_block_count_correct(self):
        # Addresses 1000-1023 (HP registers) should form one or few blocks
        coord, _ = make_coordinator({"num_heatpumps": 1})
        blocks = LambdaCoordinator._group_into_blocks(coord._register_addresses)
        # All HP registers are within address range 1000-1023, should be one block
        hp_blocks = [b for b in blocks if 1000 <= b[0] <= 1023]
        assert len(hp_blocks) == 1


# ---------------------------------------------------------------------------
# Tests: _async_update_data
# ---------------------------------------------------------------------------

class TestAsyncUpdateData:
    def test_returns_empty_dict_when_no_registers(self):
        coord, _ = make_coordinator({})
        result = asyncio.run(coord._async_update_data())
        assert result == {}

    def test_returns_dict_with_register_addresses(self):
        coord, client = make_coordinator({"num_heatpumps": 1})

        async def _read(address, count):
            return [address + i for i in range(count)]

        client.read_registers = _read
        result = asyncio.run(coord._async_update_data())

        # All expected addresses should be in the result
        for addr in coord._register_addresses:
            assert addr in result

    def test_raises_update_failed_on_read_error(self):
        coord, client = make_coordinator({"num_heatpumps": 1})
        client.read_registers = AsyncMock(return_value=None)

        with pytest.raises(Exception):  # UpdateFailed
            asyncio.run(coord._async_update_data())

    def test_values_correctly_mapped(self):
        """Verify that values from the Modbus response are mapped to the right addresses."""
        # Use a minimal config: just ambient (addresses 0-4)
        coord, client = make_coordinator({"enable_ambient": True})

        # Ambient registers: numbers 0,1,2,3,4 → addresses 0,1,2,3,4
        expected_values = {0: 10, 1: 20, 2: 30, 3: 40, 4: 50}

        async def _read(address, count):
            return [expected_values.get(address + i, 0) for i in range(count)]

        client.read_registers = _read
        result = asyncio.run(coord._async_update_data())

        for addr, val in expected_values.items():
            assert result[addr] == val

    def test_only_configured_addresses_returned(self):
        """Result should only contain addresses in _register_addresses, not block padding."""
        coord, client = make_coordinator({"num_heatpumps": 1})

        async def _read(address, count):
            return list(range(count))

        client.read_registers = _read
        result = asyncio.run(coord._async_update_data())

        for addr in result:
            assert addr in coord._register_addresses

    def test_scan_interval_applied(self):
        from datetime import timedelta
        coord, _ = make_coordinator({"scan_interval": 60})
        assert coord.update_interval == timedelta(seconds=60)

    def test_default_scan_interval(self):
        from datetime import timedelta
        from custom_components.lambda_heat_pump.const import DEFAULT_SCAN_INTERVAL
        coord, _ = make_coordinator({})
        assert coord.update_interval == timedelta(seconds=DEFAULT_SCAN_INTERVAL)


# ---------------------------------------------------------------------------
# Tests: async_write_register and RW refresh mechanism (task 4.2)
# ---------------------------------------------------------------------------

class TestAsyncWriteRegister:
    def test_write_stores_in_active_writes_for_number_00_49(self):
        """RW registers with Number 00-49 must be stored in _active_writes."""
        coord, client = make_coordinator({"num_heatpumps": 1})
        client.write_registers = AsyncMock(return_value=True)

        # address 1015 → Number 15 (< 50) → should be stored
        asyncio.run(coord.async_write_register(1015, 2))
        assert coord._active_writes[1015] == 2

    def test_write_does_not_store_for_number_50_plus(self):
        """RW registers with Number >= 50 must NOT be stored in _active_writes."""
        coord, client = make_coordinator({"num_boilers": 1})
        client.write_registers = AsyncMock(return_value=True)

        # address 2050 → Number 50 (>= 50) → must not be stored
        asyncio.run(coord.async_write_register(2050, 300))
        assert 2050 not in coord._active_writes

    def test_write_returns_true_on_success(self):
        coord, client = make_coordinator({"num_heatpumps": 1})
        client.write_registers = AsyncMock(return_value=True)
        result = asyncio.run(coord.async_write_register(1016, 500))
        assert result is True

    def test_write_returns_false_on_failure(self):
        coord, client = make_coordinator({"num_heatpumps": 1})
        client.write_registers = AsyncMock(return_value=False)
        result = asyncio.run(coord.async_write_register(1016, 500))
        assert result is False

    def test_write_request_type_writes_password_first(self):
        """Writing register 15 (request_type) must first write register 14 (password)."""
        coord, client = make_coordinator({"num_heatpumps": 1})
        calls = []

        async def _write(address, values):
            calls.append(address)
            return True

        client.write_registers = _write

        # Pre-populate password in active_writes
        coord._active_writes[1014] = 1234

        asyncio.run(coord.async_write_register(1015, 2))

        # Password (1014) must be written before request_type (1015)
        assert calls[0] == 1014
        assert calls[1] == 1015

    def test_write_request_type_skips_password_if_not_in_active_writes(self):
        """If password is not in _active_writes, only request_type is written."""
        coord, client = make_coordinator({"num_heatpumps": 1})
        calls = []

        async def _write(address, values):
            calls.append(address)
            return True

        client.write_registers = _write

        asyncio.run(coord.async_write_register(1015, 2))

        assert calls == [1015]

    def test_write_updates_existing_active_write(self):
        """Writing the same address twice should update the stored value."""
        coord, client = make_coordinator({"num_heatpumps": 1})
        client.write_registers = AsyncMock(return_value=True)

        asyncio.run(coord.async_write_register(1016, 100))
        asyncio.run(coord.async_write_register(1016, 200))

        assert coord._active_writes[1016] == 200


class TestRefreshRwRegisters:
    def test_refresh_rewrites_all_active_writes(self):
        """_async_refresh_rw_registers must re-write every entry in _active_writes."""
        coord, client = make_coordinator({"num_heatpumps": 1})
        written = {}

        async def _write(address, values):
            written[address] = values[0]
            return True

        client.write_registers = _write

        coord._active_writes = {1014: 1234, 1015: 2, 1016: 450}
        asyncio.run(coord._async_refresh_rw_registers())

        assert written == {1014: 1234, 1015: 2, 1016: 450}

    def test_refresh_does_nothing_when_no_active_writes(self):
        coord, client = make_coordinator({})
        client.write_registers = AsyncMock(return_value=True)

        asyncio.run(coord._async_refresh_rw_registers())

        client.write_registers.assert_not_called()

    def test_refresh_continues_on_write_failure(self):
        """A failed write during refresh must not stop the remaining writes."""
        coord, client = make_coordinator({"num_heatpumps": 1})
        call_count = 0

        async def _write(address, values):
            nonlocal call_count
            call_count += 1
            return False  # always fail

        client.write_registers = _write

        coord._active_writes = {1014: 1234, 1015: 2, 1016: 450}
        asyncio.run(coord._async_refresh_rw_registers())

        # All three registers should have been attempted
        assert call_count == 3


class TestRefreshTask:
    def test_stop_refresh_task_cancels_task(self):
        coord, client = make_coordinator({"num_heatpumps": 1})
        client.write_registers = AsyncMock(return_value=True)

        async def _run():
            # Trigger task creation via a write
            await coord.async_write_register(1015, 2)
            assert coord._refresh_task is not None
            coord.stop_refresh_task()
            assert coord._refresh_task is None

        asyncio.run(_run())

    def test_ensure_refresh_task_starts_task(self):
        coord, _ = make_coordinator({})

        async def _run():
            assert coord._refresh_task is None
            coord._ensure_refresh_task()
            assert coord._refresh_task is not None
            coord.stop_refresh_task()

        asyncio.run(_run())
