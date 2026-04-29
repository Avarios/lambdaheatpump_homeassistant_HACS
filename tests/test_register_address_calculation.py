"""Unit tests for calc_register_address() in const.py.

Validates: Requirements 4.2, 6.6, 9.5
"""
import pytest

from custom_components.lambda_heat_pump.const import (
    INDEX_GENERAL,
    INDEX_HEATPUMP,
    INDEX_BOILER,
    INDEX_BUFFER,
    INDEX_SOLAR,
    INDEX_HEATING_CIRCUIT,
    SUBINDEX_AMBIENT,
    SUBINDEX_EMANAGER,
    calc_register_address,
)


# ---------------------------------------------------------------------------
# Design-doc examples (exact values from design.md)
# ---------------------------------------------------------------------------

class TestDesignDocExamples:
    """Verify the concrete examples listed in the design document."""

    def test_heatpump_1_register_04(self):
        # Heat pump 1, register 04: 1*1000 + 0*100 + 4 = 1004
        assert calc_register_address(INDEX_HEATPUMP, 0, 4) == 1004

    def test_heatpump_2_register_04(self):
        # Heat pump 2, register 04: 1*1000 + 1*100 + 4 = 1104
        assert calc_register_address(INDEX_HEATPUMP, 1, 4) == 1104

    def test_heating_circuit_1_register_00(self):
        # Heating circuit 1, register 00: 5*1000 + 0*100 + 0 = 5000
        assert calc_register_address(INDEX_HEATING_CIRCUIT, 0, 0) == 5000

    def test_heating_circuit_12_register_06(self):
        # Heating circuit 12, register 06: 5*1000 + 11*100 + 6 = 6106
        assert calc_register_address(INDEX_HEATING_CIRCUIT, 11, 6) == 6106

    def test_general_ambient_register_02(self):
        # General Ambient, register 02: 0*1000 + 0*100 + 2 = 2
        assert calc_register_address(INDEX_GENERAL, SUBINDEX_AMBIENT, 2) == 2

    def test_general_emanager_register_02(self):
        # General E-Manager, register 02: 0*1000 + 1*100 + 2 = 102
        assert calc_register_address(INDEX_GENERAL, SUBINDEX_EMANAGER, 2) == 102

    def test_boiler_5_register_50(self):
        # Boiler 5, register 50: 2*1000 + 4*100 + 50 = 2450
        assert calc_register_address(INDEX_BOILER, 4, 50) == 2450

    def test_solar_2_register_51(self):
        # Solar 2, register 51: 4*1000 + 1*100 + 51 = 4151
        assert calc_register_address(INDEX_SOLAR, 1, 51) == 4151


# ---------------------------------------------------------------------------
# Formula correctness
# ---------------------------------------------------------------------------

class TestFormula:
    """Verify the formula index*1000 + subindex*100 + number directly."""

    @pytest.mark.parametrize("index,subindex,number", [
        (0, 0, 0),
        (0, 0, 99),
        (0, 1, 0),
        (1, 0, 0),
        (5, 11, 99),
    ])
    def test_formula(self, index, subindex, number):
        expected = index * 1000 + subindex * 100 + number
        assert calc_register_address(index, subindex, number) == expected


# ---------------------------------------------------------------------------
# Module-type index constants
# ---------------------------------------------------------------------------

class TestModuleIndexConstants:
    """Verify the module index constants match the specification."""

    def test_index_general_is_0(self):
        assert INDEX_GENERAL == 0

    def test_index_heatpump_is_1(self):
        assert INDEX_HEATPUMP == 1

    def test_index_boiler_is_2(self):
        assert INDEX_BOILER == 2

    def test_index_buffer_is_3(self):
        assert INDEX_BUFFER == 3

    def test_index_solar_is_4(self):
        assert INDEX_SOLAR == 4

    def test_index_heating_circuit_is_5(self):
        assert INDEX_HEATING_CIRCUIT == 5

    def test_subindex_ambient_is_0(self):
        assert SUBINDEX_AMBIENT == 0

    def test_subindex_emanager_is_1(self):
        assert SUBINDEX_EMANAGER == 1


# ---------------------------------------------------------------------------
# All module types – first and last subindex, register 0 and 99
# ---------------------------------------------------------------------------

class TestAllModuleTypes:
    """Spot-check address calculation for every module type."""

    @pytest.mark.parametrize("index,subindex,number,expected", [
        # General Ambient (Index 0, Subindex 0)
        (INDEX_GENERAL, 0, 0, 0),
        (INDEX_GENERAL, 0, 99, 99),
        # General E-Manager (Index 0, Subindex 1)
        (INDEX_GENERAL, 1, 0, 100),
        (INDEX_GENERAL, 1, 99, 199),
        # Heat Pump (Index 1, Subindex 0-4)
        (INDEX_HEATPUMP, 0, 0, 1000),
        (INDEX_HEATPUMP, 4, 99, 1499),
        # Boiler (Index 2, Subindex 0-4)
        (INDEX_BOILER, 0, 0, 2000),
        (INDEX_BOILER, 4, 99, 2499),
        # Buffer (Index 3, Subindex 0-4)
        (INDEX_BUFFER, 0, 0, 3000),
        (INDEX_BUFFER, 4, 99, 3499),
        # Solar (Index 4, Subindex 0-1)
        (INDEX_SOLAR, 0, 0, 4000),
        (INDEX_SOLAR, 1, 99, 4199),
        # Heating Circuit (Index 5, Subindex 0-11)
        (INDEX_HEATING_CIRCUIT, 0, 0, 5000),
        (INDEX_HEATING_CIRCUIT, 11, 99, 6199),
    ])
    def test_module_address(self, index, subindex, number, expected):
        assert calc_register_address(index, subindex, number) == expected


# ---------------------------------------------------------------------------
# Boundary / edge cases
# ---------------------------------------------------------------------------

class TestBoundaryValues:
    """Test boundary values and special cases."""

    def test_all_zeros(self):
        """Minimum possible address."""
        assert calc_register_address(0, 0, 0) == 0

    def test_maximum_address(self):
        """Maximum address: index=5, subindex=11, number=99."""
        assert calc_register_address(5, 11, 99) == 6199

    def test_general_ambient_index_0(self):
        """General Ambient uses Index 0 – address must not be offset by 1000."""
        addr = calc_register_address(0, 0, 0)
        assert addr == 0
        assert addr < 1000  # must be below heat-pump range

    def test_heating_circuit_12_subindex_11(self):
        """Heating Circuit 12 uses Subindex 11 – highest HC subindex."""
        addr = calc_register_address(5, 11, 0)
        assert addr == 6100

    def test_number_boundary_0(self):
        """Register number 0 contributes 0 to the address."""
        assert calc_register_address(1, 0, 0) == 1000

    def test_number_boundary_99(self):
        """Register number 99 is the maximum datapoint number."""
        assert calc_register_address(1, 0, 99) == 1099

    def test_subindex_boundary_0(self):
        """Subindex 0 contributes 0 to the address."""
        assert calc_register_address(1, 0, 5) == 1005

    def test_subindex_boundary_11(self):
        """Subindex 11 is the maximum (Heating Circuit 12)."""
        assert calc_register_address(5, 11, 5) == 6105


# ---------------------------------------------------------------------------
# Uniqueness – no two distinct (index, subindex, number) triples share an address
# ---------------------------------------------------------------------------

class TestAddressUniqueness:
    """Verify that all valid (index, subindex, number) triples produce unique addresses."""

    # Per-module valid (index, max_subindex) pairs from the specification:
    #   General Ambient/EManager: index 0, subindex 0-1
    #   Heat Pump:                index 1, subindex 0-4
    #   Boiler:                   index 2, subindex 0-4
    #   Buffer:                   index 3, subindex 0-4
    #   Solar:                    index 4, subindex 0-1
    #   Heating Circuit:          index 5, subindex 0-11
    _VALID_PAIRS = (
        [(0, s) for s in range(2)]   +  # General (Ambient + EManager)
        [(1, s) for s in range(5)]   +  # Heat Pump
        [(2, s) for s in range(5)]   +  # Boiler
        [(3, s) for s in range(5)]   +  # Buffer
        [(4, s) for s in range(2)]   +  # Solar
        [(5, s) for s in range(12)]     # Heating Circuit
    )

    def test_all_addresses_unique(self):
        """
        For every valid (index, subindex) pair defined in the specification and
        every register number 0-99, the calculated address must be unique.

        Note: The formula index*1000 + subindex*100 + number is injective only
        within the spec-defined (index, subindex) pairs, not across the full
        Cartesian product of all indices × all subindices.
        """
        addresses = [
            calc_register_address(idx, sub, num)
            for (idx, sub) in self._VALID_PAIRS
            for num in range(100)
        ]
        assert len(addresses) == len(set(addresses)), (
            "Duplicate register addresses detected – address formula is not injective "
            "within the spec-defined module ranges"
        )

    def test_heatpump_subindices_unique(self):
        """All five heat pumps (subindex 0-4) must have distinct addresses for the same register."""
        addresses = [calc_register_address(INDEX_HEATPUMP, sub, 4) for sub in range(5)]
        assert len(addresses) == len(set(addresses))

    def test_heating_circuit_subindices_unique(self):
        """All twelve heating circuits (subindex 0-11) must have distinct addresses."""
        addresses = [calc_register_address(INDEX_HEATING_CIRCUIT, sub, 0) for sub in range(12)]
        assert len(addresses) == len(set(addresses))

    def test_ambient_and_emanager_distinct(self):
        """Ambient (subindex 0) and E-Manager (subindex 1) must not share addresses."""
        ambient_addrs = {calc_register_address(0, 0, n) for n in range(100)}
        emanager_addrs = {calc_register_address(0, 1, n) for n in range(100)}
        assert ambient_addrs.isdisjoint(emanager_addrs)
