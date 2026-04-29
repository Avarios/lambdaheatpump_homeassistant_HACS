"""Unit tests for data scaling and INT32 composition (task 12.2).

Tests:
- Scaling logic: raw_value * scale for factors 0.01, 0.1, 1
- INT16 sign handling: raw > 32767 → raw - 65536
- INT32 composition: _combine_int32(high, low) from sensor.py
- Round-trip: round(scaled / scale) == raw
- Requirements: 4.1, 4.5
"""
from __future__ import annotations

import sys
import types

# ---------------------------------------------------------------------------
# Stubs for homeassistant modules
# ---------------------------------------------------------------------------

def _ensure_stub(name: str) -> types.ModuleType:
    if name not in sys.modules:
        sys.modules[name] = types.ModuleType(name)
    return sys.modules[name]


for _mod in [
    "homeassistant",
    "homeassistant.core",
    "homeassistant.config_entries",
    "homeassistant.helpers",
    "homeassistant.helpers.update_coordinator",
    "homeassistant.helpers.device_registry",
    "homeassistant.helpers.entity_platform",
    "homeassistant.components",
    "homeassistant.components.sensor",
    "homeassistant.components.number",
]:
    _ensure_stub(_mod)

_ep = sys.modules["homeassistant.helpers.entity_platform"]
_ep.AddEntitiesCallback = object  # type: ignore[attr-defined]


class _FakeCoordinatorEntity:
    def __init__(self, coordinator):
        self.coordinator = coordinator

    def __class_getitem__(cls, item):
        return cls


class _FakeDataUpdateCoordinator:
    def __init__(self, *args, **kwargs):
        self.data = None

    def __class_getitem__(cls, item):
        return cls


_uc = sys.modules["homeassistant.helpers.update_coordinator"]
_uc.CoordinatorEntity = _FakeCoordinatorEntity  # type: ignore[attr-defined]
_uc.DataUpdateCoordinator = _FakeDataUpdateCoordinator  # type: ignore[attr-defined]
_uc.UpdateFailed = Exception  # type: ignore[attr-defined]


class _DeviceInfo(dict):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


_dr = sys.modules["homeassistant.helpers.device_registry"]
_dr.DeviceInfo = _DeviceInfo  # type: ignore[attr-defined]

_core = sys.modules["homeassistant.core"]
_core.HomeAssistant = object  # type: ignore[attr-defined]

_sensor_mod = sys.modules["homeassistant.components.sensor"]
_sensor_mod.SensorEntity = object  # type: ignore[attr-defined]
_sensor_mod.SensorDeviceClass = object  # type: ignore[attr-defined]
_sensor_mod.SensorStateClass = object  # type: ignore[attr-defined]

_number_mod = sys.modules["homeassistant.components.number"]
_number_mod.NumberEntity = object  # type: ignore[attr-defined]
_number_mod.NumberMode = type("NumberMode", (), {"BOX": "box"})()  # type: ignore[attr-defined]

_ce = sys.modules["homeassistant.config_entries"]
_ce.ConfigEntry = object  # type: ignore[attr-defined]

# ---------------------------------------------------------------------------
# Imports under test
# ---------------------------------------------------------------------------

from custom_components.lambda_heat_pump.sensor import _combine_int32
from custom_components.lambda_heat_pump.number import _to_uint16

# ---------------------------------------------------------------------------
# Helpers: pure scaling functions (mirrors the logic in sensor.py / number.py)
# ---------------------------------------------------------------------------

def raw_to_scaled(raw: int, scale: float) -> float:
    """Apply scale factor to a raw register value (as in LambdaSensor.native_value)."""
    if scale == 1:
        return float(raw)
    return round(raw * scale, 10)


def scaled_to_raw(scaled: float, scale: float) -> int:
    """Convert a scaled value back to raw integer (as in LambdaNumber.async_set_native_value)."""
    return round(scaled / scale)


def int16_from_raw(raw: int) -> int:
    """Interpret a UINT16 raw value as signed INT16 (as in LambdaNumber.native_value)."""
    if raw > 32767:
        return raw - 65536
    return raw


def split_int32(value: int) -> tuple[int, int]:
    """Split a signed INT32 into (high_word, low_word) UINT16 pair."""
    unsigned = value & 0xFFFFFFFF
    high = (unsigned >> 16) & 0xFFFF
    low = unsigned & 0xFFFF
    return high, low


# ---------------------------------------------------------------------------
# Tests: Scaling factors 0.01, 0.1, 1
# ---------------------------------------------------------------------------

class TestScalingFactor001:
    """Scale factor 0.01 — used for temperatures, volume flow, COP, compressor rating."""

    def test_typical_temperature(self):
        # 45.23 °C → raw 4523
        assert abs(raw_to_scaled(4523, 0.01) - 45.23) < 1e-9

    def test_zero(self):
        assert raw_to_scaled(0, 0.01) == 0.0

    def test_negative_raw(self):
        # -5.00 °C → raw -500 (after INT16 sign handling, raw=65036)
        raw_signed = -500
        assert abs(raw_to_scaled(raw_signed, 0.01) - (-5.0)) < 1e-9

    def test_max_int16(self):
        # 327.67 → raw 32767
        assert abs(raw_to_scaled(32767, 0.01) - 327.67) < 1e-9

    def test_round_trip(self):
        for raw in [0, 1, 100, 4523, 32767, -1, -500, -32768]:
            scaled = raw_to_scaled(raw, 0.01)
            assert scaled_to_raw(scaled, 0.01) == raw


class TestScalingFactor01:
    """Scale factor 0.1 — used for temperatures in boiler, buffer, solar, heating circuit."""

    def test_typical_temperature(self):
        # 55.0 °C → raw 550
        assert abs(raw_to_scaled(550, 0.1) - 55.0) < 1e-9

    def test_zero(self):
        assert raw_to_scaled(0, 0.1) == 0.0

    def test_negative_raw(self):
        # -10.0 °C → raw -100
        assert abs(raw_to_scaled(-100, 0.1) - (-10.0)) < 1e-9

    def test_max_int16(self):
        # 3276.7 → raw 32767
        assert abs(raw_to_scaled(32767, 0.1) - 3276.7) < 1e-9

    def test_round_trip(self):
        for raw in [0, 1, 100, 550, 32767, -1, -100, -32768]:
            scaled = raw_to_scaled(raw, 0.1)
            assert scaled_to_raw(scaled, 0.1) == raw


class TestScalingFactor1:
    """Scale factor 1 — used for power (W), energy (Wh), error numbers, etc."""

    def test_typical_power(self):
        assert raw_to_scaled(1500, 1) == 1500.0

    def test_zero(self):
        assert raw_to_scaled(0, 1) == 0.0

    def test_negative(self):
        assert raw_to_scaled(-100, 1) == -100.0

    def test_returns_float(self):
        result = raw_to_scaled(42, 1)
        assert isinstance(result, float)

    def test_round_trip(self):
        for raw in [0, 1, 1500, 32767, -1, -32768]:
            scaled = raw_to_scaled(raw, 1)
            assert scaled_to_raw(scaled, 1) == raw


# ---------------------------------------------------------------------------
# Tests: INT16 sign handling
# ---------------------------------------------------------------------------

class TestInt16SignHandling:
    """raw > 32767 is interpreted as negative INT16 (two's complement)."""

    def test_positive_unchanged(self):
        assert int16_from_raw(0) == 0
        assert int16_from_raw(1) == 1
        assert int16_from_raw(32767) == 32767

    def test_boundary_32768_is_negative(self):
        # 32768 = 0x8000 → -32768 in INT16
        assert int16_from_raw(32768) == -32768

    def test_65535_is_minus_one(self):
        # 0xFFFF → -1
        assert int16_from_raw(65535) == -1

    def test_typical_negative_temperature(self):
        # -5 °C with scale 0.01 → raw INT16 = -500 → stored as UINT16 = 65036
        raw_uint16 = 65036  # 65536 - 500
        signed = int16_from_raw(raw_uint16)
        assert signed == -500
        assert abs(raw_to_scaled(signed, 0.01) - (-5.0)) < 1e-9

    def test_to_uint16_roundtrip(self):
        """_to_uint16 and int16_from_raw are inverses for INT16 range."""
        for v in [-32768, -1, -500, 0, 1, 32767]:
            uint16 = _to_uint16(v)
            assert 0 <= uint16 <= 65535
            assert int16_from_raw(uint16) == v


# ---------------------------------------------------------------------------
# Tests: _combine_int32
# ---------------------------------------------------------------------------

class TestCombineInt32:
    """INT32 composition from two UINT16 registers (Requirement 4.5)."""

    def test_zero(self):
        assert _combine_int32(0, 0) == 0

    def test_positive_small(self):
        # 1 = 0x00000001 → high=0, low=1
        assert _combine_int32(0, 1) == 1

    def test_positive_large(self):
        # 1_000_000 = 0x000F4240 → high=0x000F=15, low=0x4240=16960
        assert _combine_int32(15, 16960) == 1_000_000

    def test_max_positive(self):
        # 2^31 - 1 = 0x7FFFFFFF → high=0x7FFF, low=0xFFFF
        assert _combine_int32(0x7FFF, 0xFFFF) == 2_147_483_647

    def test_negative_one(self):
        # -1 = 0xFFFFFFFF → high=0xFFFF, low=0xFFFF
        assert _combine_int32(0xFFFF, 0xFFFF) == -1

    def test_min_negative(self):
        # -2^31 = 0x80000000 → high=0x8000, low=0x0000
        assert _combine_int32(0x8000, 0x0000) == -2_147_483_648

    def test_small_negative(self):
        # -1000 = 0xFFFFFC18 → high=0xFFFF, low=0xFC18=64536
        assert _combine_int32(0xFFFF, 0xFC18) == -1000

    def test_energy_value_typical(self):
        # 500_000 Wh = 0x0007A120 → high=0x0007=7, low=0xA120=41248
        assert _combine_int32(7, 41248) == 500_000


# ---------------------------------------------------------------------------
# Tests: split_int32 / combine_int32 round-trip
# ---------------------------------------------------------------------------

class TestInt32RoundTrip:
    """combine_int32(split_int32(v)) == v for all INT32 values (Requirement 4.5)."""

    def test_zero(self):
        high, low = split_int32(0)
        assert _combine_int32(high, low) == 0

    def test_positive_one(self):
        high, low = split_int32(1)
        assert _combine_int32(high, low) == 1

    def test_max_positive(self):
        v = 2_147_483_647
        high, low = split_int32(v)
        assert _combine_int32(high, low) == v

    def test_negative_one(self):
        high, low = split_int32(-1)
        assert _combine_int32(high, low) == -1

    def test_min_negative(self):
        v = -2_147_483_648
        high, low = split_int32(v)
        assert _combine_int32(high, low) == v

    def test_typical_energy_values(self):
        for v in [0, 1, 1000, 500_000, 1_000_000, 10_000_000, -1, -1000, -500_000]:
            high, low = split_int32(v)
            assert _combine_int32(high, low) == v, f"Round-trip failed for {v}"

    def test_boundary_values(self):
        for v in [0x7FFF0000, 0x0000FFFF, 0x7FFFFFFF, -0x80000000, -0x00010000]:
            high, low = split_int32(v)
            assert _combine_int32(high, low) == v


# ---------------------------------------------------------------------------
# Tests: Scaling round-trip for all spec-defined scale factors
# ---------------------------------------------------------------------------

class TestScalingRoundTrip:
    """scaled_to_raw(raw_to_scaled(raw, scale), scale) == raw for all spec scales."""

    def test_all_scales_positive_values(self):
        scales = [0.01, 0.1, 1]
        raws = [0, 1, 100, 1000, 32767]
        for scale in scales:
            for raw in raws:
                scaled = raw_to_scaled(raw, scale)
                recovered = scaled_to_raw(scaled, scale)
                assert recovered == raw, f"Round-trip failed: scale={scale}, raw={raw}"

    def test_all_scales_negative_values(self):
        scales = [0.01, 0.1, 1]
        raws = [-1, -100, -1000, -32768]
        for scale in scales:
            for raw in raws:
                scaled = raw_to_scaled(raw, scale)
                recovered = scaled_to_raw(scaled, scale)
                assert recovered == raw, f"Round-trip failed: scale={scale}, raw={raw}"

    def test_scale_001_specific_values(self):
        # Temperatures from the spec examples
        pairs = [(4523, 45.23), (3891, 38.91), (0, 0.0), (-500, -5.0)]
        for raw, expected_scaled in pairs:
            assert abs(raw_to_scaled(raw, 0.01) - expected_scaled) < 1e-9
            assert scaled_to_raw(expected_scaled, 0.01) == raw

    def test_scale_01_specific_values(self):
        # Temperatures from the spec examples
        pairs = [(550, 55.0), (450, 45.0), (215, 21.5), (200, 20.0)]
        for raw, expected_scaled in pairs:
            assert abs(raw_to_scaled(raw, 0.1) - expected_scaled) < 1e-9
            assert scaled_to_raw(expected_scaled, 0.1) == raw
