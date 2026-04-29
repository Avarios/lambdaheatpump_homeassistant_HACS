"""Constants and register definitions for Lambda Heat Pump integration."""
from __future__ import annotations

from dataclasses import dataclass, field

DOMAIN = "lambda_heat_pump"

# Default configuration values
DEFAULT_PORT = 502
DEFAULT_SCAN_INTERVAL = 30
DEFAULT_NUM_HEATPUMPS = 1
DEFAULT_NUM_HEATING_CIRCUITS = 0
DEFAULT_NUM_BOILERS = 0
DEFAULT_NUM_BUFFERS = 0
DEFAULT_NUM_SOLAR = 0
DEFAULT_ENABLE_AMBIENT = False
DEFAULT_ENABLE_EMANAGER = False

# Configuration keys
CONF_NUM_HEATPUMPS = "num_heatpumps"
CONF_NUM_HEATING_CIRCUITS = "num_heating_circuits"
CONF_NUM_BOILERS = "num_boilers"
CONF_NUM_BUFFERS = "num_buffers"
CONF_NUM_SOLAR = "num_solar"
CONF_ENABLE_AMBIENT = "enable_ambient"
CONF_ENABLE_EMANAGER = "enable_emanager"
CONF_SCAN_INTERVAL = "scan_interval"

# Platforms
PLATFORMS = ["sensor", "binary_sensor", "number", "select"]

# Module type identifiers
MODULE_HEATPUMP = "heatpump"
MODULE_BOILER = "boiler"
MODULE_BUFFER = "buffer"
MODULE_SOLAR = "solar"
MODULE_HEATING_CIRCUIT = "heating_circuit"
MODULE_AMBIENT = "ambient"
MODULE_EMANAGER = "emanager"

# Module indices (Modbus address index)
INDEX_GENERAL = 0   # Ambient (subindex 0) and EManager (subindex 1)
INDEX_HEATPUMP = 1
INDEX_BOILER = 2
INDEX_BUFFER = 3
INDEX_SOLAR = 4
INDEX_HEATING_CIRCUIT = 5

SUBINDEX_AMBIENT = 0
SUBINDEX_EMANAGER = 1


@dataclass
class RegisterDefinition:
    """Definition of a single Modbus register."""

    number: int                          # Datapoint number (00-99)
    name: str                            # Internal name
    label: str                           # Human-readable display name
    access: str                          # "RO" or "RW"
    data_type: str                       # "UINT16", "INT16", "INT32"
    unit: str | None                     # Unit string (°C, kW, W, l/min, %)
    scale: float                         # Scaling factor (e.g. 0.01)
    device_class: str | None             # HA Device Class
    state_class: str | None              # HA State Class
    options: dict[int, str] | None       # Enum mapping for Select/Sensor
    min_value: float | None              # Minimum value for Number entities
    max_value: float | None              # Maximum value for Number entities
    step: float = 1.0                    # Step size for Number entities


# ---------------------------------------------------------------------------
# Enum Definitions
# ---------------------------------------------------------------------------

HP_ERROR_STATE: dict[int, str] = {
    0: "NONE",
    1: "MESSAGE",
    2: "WARNING",
    3: "ALARM",
    4: "FAULT",
}

HP_STATE: dict[int, str] = {
    0: "INIT",
    1: "REFERENCE",
    2: "RESTART-BLOCK",
    3: "READY",
    4: "START PUMPS",
    5: "START COMPRESSOR",
    6: "PRE-REGULATION",
    7: "REGULATION",
    9: "COOLING",
    10: "DEFROSTING",
    20: "STOPPING",
    30: "FAULT-LOCK",
    31: "ALARM-BLOCK",
    40: "ERROR-RESET",
}

HP_OPERATING_STATE: dict[int, str] = {
    0: "STBY",
    1: "CH",
    2: "DHW",
    3: "CC",
    4: "CIRCULATE",
    5: "DEFROST",
    6: "OFF",
    7: "FROST",
    8: "STBY-FROST",
    10: "SUMMER",
    11: "HOLIDAY",
    12: "ERROR",
    13: "WARNING",
    14: "INFO-MESSAGE",
    15: "TIME-BLOCK",
    16: "RELEASE-BLOCK",
    17: "MINTEMP-BLOCK",
    18: "FIRMWARE-DOWNLOAD",
}

HP_REQUEST_TYPE: dict[int, str] = {
    0: "NO REQUEST",
    1: "FLOW PUMP CIRCULATION",
    2: "CENTRAL HEATING",
    3: "CENTRAL COOLING",
    4: "DOMESTIC HOT WATER",
}

BOILER_OPERATING_STATE: dict[int, str] = {
    0: "STBY",
    1: "DHW",
    2: "LEGIO",
    3: "SUMMER",
    4: "FROST",
    5: "HOLIDAY",
    6: "PRO-STOP",
    7: "ERROR",
    8: "OFF",
    9: "PROMPT-DHW",
    10: "TRAILING-STOP",
    11: "TEMP-LOCK",
    12: "STBY-FROST",
}

BUFFER_OPERATING_STATE: dict[int, str] = {
    0: "STBY",
    1: "HEATING",
    2: "COOLING",
    3: "SUMMER",
    4: "FROST",
    5: "HOLIDAY",
    6: "PRO-STOP",
    7: "ERROR",
    8: "OFF",
    9: "STBY-FROST",
}

BUFFER_REQUEST_TYPE: dict[int, str] = {
    -1: "INVALID REQUEST",
    0: "NO REQUEST",
    1: "FLOW PUMP CIRCULATION",
    2: "CENTRAL HEATING",
    3: "CENTRAL COOLING",
}

SOLAR_OPERATING_STATE: dict[int, str] = {
    0: "STBY",
    1: "HEATING",
    2: "SUMMER",
    3: "ERROR",
    4: "OFF",
}

HC_OPERATING_STATE: dict[int, str] = {
    0: "HEATING",
    1: "ECO",
    2: "COOLING",
    3: "FLOORDRY",
    4: "FROST",
    5: "MAX-TEMP",
    6: "ERROR",
    7: "SERVICE",
    8: "HOLIDAY",
    9: "CH-SUMMER",
    10: "CC-WINTER",
    11: "PRIO-STOP",
    12: "OFF",
    13: "RELEASE-OFF",
    14: "TIME-OFF",
    15: "STBY",
    16: "STBY-HEATING",
    17: "STBY-ECO",
    18: "STBY-COOLING",
    19: "STBY-FROST",
    20: "STBY-FLOORDRY",
}

HC_OPERATING_MODE: dict[int, str] = {
    0: "OFF",
    1: "MANUAL",
    2: "AUTOMATIC",
    3: "AUTO-HEATING",
    4: "AUTO-COOLING",
    5: "FROST",
    6: "SUMMER",
    7: "FLOORDRY",
}

AMBIENT_OPERATING_STATE: dict[int, str] = {
    0: "OFF",
    1: "AUTOMATIK",
    2: "MANUAL",
    3: "ERROR",
}

EMANAGER_OPERATING_STATE: dict[int, str] = {
    0: "OFF",
    1: "AUTOMATIK",
    2: "MANUAL",
    3: "ERROR",
    4: "OFFLINE",
}


# ---------------------------------------------------------------------------
# Register Lists
# ---------------------------------------------------------------------------

HEATPUMP_REGISTERS: list[RegisterDefinition] = [
    RegisterDefinition(0, "hp_error_state", "Error State", "RO", "UINT16", None, 1, "problem", None, HP_ERROR_STATE, None, None),
    RegisterDefinition(1, "hp_error_number", "Error Number", "RO", "INT16", None, 1, None, "measurement", None, None, None),
    RegisterDefinition(2, "hp_state", "Heat Pump State", "RO", "UINT16", None, 1, None, None, HP_STATE, None, None),
    RegisterDefinition(3, "operating_state", "Operating State", "RO", "UINT16", None, 1, None, None, HP_OPERATING_STATE, None, None),
    RegisterDefinition(4, "t_flow", "Flow Line Temperature", "RO", "INT16", "°C", 0.01, "temperature", "measurement", None, None, None),
    RegisterDefinition(5, "t_return", "Return Line Temperature", "RO", "INT16", "°C", 0.01, "temperature", "measurement", None, None, None),
    RegisterDefinition(6, "vol_sink", "Volume Flow Heat Sink", "RO", "INT16", "L/min", 0.01, "volume_flow_rate", "measurement", None, None, None),
    RegisterDefinition(7, "t_eq_in", "Energy Source Inlet Temperature", "RO", "INT16", "°C", 0.01, "temperature", "measurement", None, None, None),
    RegisterDefinition(8, "t_eq_out", "Energy Source Outlet Temperature", "RO", "INT16", "°C", 0.01, "temperature", "measurement", None, None, None),
    RegisterDefinition(9, "vol_source", "Volume Flow Energy Source", "RO", "INT16", "L/min", 0.01, "volume_flow_rate", "measurement", None, None, None),
    RegisterDefinition(10, "compressor_rating", "Compressor Rating", "RO", "UINT16", "%", 0.01, "power_factor", "measurement", None, None, None),
    RegisterDefinition(11, "qp_heating", "Heating Capacity", "RO", "INT16", "kW", 0.1, "power", "measurement", None, None, None),
    RegisterDefinition(12, "fi_power", "Frequency Inverter Power Consumption", "RO", "INT16", "W", 1, "power", "measurement", None, None, None),
    RegisterDefinition(13, "cop", "COP", "RO", "INT16", None, 0.01, None, "measurement", None, None, None),
    RegisterDefinition(14, "request_password", "Modbus Release Password", "RW", "UINT16", None, 1, None, None, None, None, None),
    RegisterDefinition(15, "request_type", "Request Type", "RW", "INT16", None, 1, None, None, HP_REQUEST_TYPE, None, None),
    RegisterDefinition(16, "request_flow_temp", "Request Flow Line Temperature", "RW", "INT16", "°C", 0.1, "temperature", None, None, 0.0, 70.0, 0.1),
    RegisterDefinition(17, "request_return_temp", "Request Return Line Temperature", "RW", "INT16", "°C", 0.1, "temperature", None, None, 0.0, 65.0, 0.1),
    RegisterDefinition(18, "request_temp_diff", "Request Heat Sink Temperature Difference", "RW", "INT16", "K", 0.1, None, None, None, 0.0, 35.0, 0.1),
    RegisterDefinition(19, "relay_2nd_stage", "Relay State 2nd Heating Stage", "RO", "INT16", None, 1, None, None, None, None, None),
    RegisterDefinition(20, "stat_energy_e", "Statistics Electrical Energy", "RO", "INT32", "Wh", 1, "energy", "total_increasing", None, None, None),
    RegisterDefinition(22, "stat_energy_q", "Statistics Thermal Energy", "RO", "INT32", "Wh", 1, "energy", "total_increasing", None, None, None),
]

BOILER_REGISTERS: list[RegisterDefinition] = [
    RegisterDefinition(0, "boiler_error_number", "Error Number", "RO", "INT16", None, 1, None, None, None, None, None),
    RegisterDefinition(1, "boiler_operating_state", "Operating State", "RO", "UINT16", None, 1, None, None, BOILER_OPERATING_STATE, None, None),
    RegisterDefinition(2, "boiler_temp_high", "Actual High Temperature", "RO", "INT16", "°C", 0.1, "temperature", "measurement", None, None, None),
    RegisterDefinition(3, "boiler_temp_low", "Actual Low Temperature", "RO", "INT16", "°C", 0.1, "temperature", "measurement", None, None, None),
    RegisterDefinition(4, "boiler_temp_circulation", "Actual Circulation Temperature", "RO", "INT16", "°C", 0.1, "temperature", "measurement", None, None, None),
    RegisterDefinition(5, "boiler_pump_state", "Actual Circulation Pump State", "RO", "INT16", None, 1, None, None, None, None, None),
    RegisterDefinition(50, "boiler_max_temp", "Set Maximum Boiler Temperature", "RW", "INT16", "°C", 0.1, "temperature", None, None, 25.0, 65.0, 0.1),
]

BUFFER_REGISTERS: list[RegisterDefinition] = [
    RegisterDefinition(0, "buffer_error_number", "Error Number", "RO", "INT16", None, 1, None, None, None, None, None),
    RegisterDefinition(1, "buffer_operating_state", "Operating State", "RO", "UINT16", None, 1, None, None, BUFFER_OPERATING_STATE, None, None),
    RegisterDefinition(2, "buffer_temp_high", "Actual High Temperature", "RO", "INT16", "°C", 0.1, "temperature", "measurement", None, None, None),
    RegisterDefinition(3, "buffer_temp_low", "Actual Low Temperature", "RO", "INT16", "°C", 0.1, "temperature", "measurement", None, None, None),
    RegisterDefinition(4, "buffer_modbus_temp_high", "Modbus Buffer Temperature High Setpoint", "RW", "INT16", "°C", 0.1, "temperature", None, None, 0.0, 90.0, 0.1),
    RegisterDefinition(5, "buffer_request_type", "Request Type", "RW", "INT16", None, 1, None, None, BUFFER_REQUEST_TYPE, None, None),
    RegisterDefinition(6, "buffer_request_flow_temp", "Request Flow Line Temperature Setpoint", "RW", "INT16", "°C", 0.1, "temperature", None, None, 0.0, 65.0, 0.1),
    RegisterDefinition(7, "buffer_request_return_temp", "Request Return Line Temperature Setpoint", "RW", "INT16", "°C", 0.1, "temperature", None, None, 0.0, 60.0, 0.1),
    RegisterDefinition(8, "buffer_request_temp_diff", "Request Heat Sink Temperature Difference Setpoint", "RW", "INT16", "K", 0.1, None, None, None, 0.0, 35.0, 0.1),
    RegisterDefinition(9, "buffer_request_capacity", "Modbus Request Heating Capacity", "RW", "INT16", "kW", 0.1, "power", None, None, 0.0, None, 0.1),
    RegisterDefinition(50, "buffer_max_temp", "Set Maximum Buffer Temperature", "RW", "INT16", "°C", 0.1, "temperature", None, None, 25.0, 60.0, 0.1),
]

SOLAR_REGISTERS: list[RegisterDefinition] = [
    RegisterDefinition(0, "solar_error_number", "Error Number", "RO", "INT16", None, 1, None, None, None, None, None),
    RegisterDefinition(1, "solar_operating_state", "Operating State", "RO", "UINT16", None, 1, None, None, SOLAR_OPERATING_STATE, None, None),
    RegisterDefinition(2, "solar_collector_temp", "Collector Temperature", "RO", "INT16", "°C", 0.1, "temperature", "measurement", None, None, None),
    RegisterDefinition(3, "solar_buffer1_temp", "Buffer 1 Temperature", "RO", "INT16", "°C", 0.1, "temperature", "measurement", None, None, None),
    RegisterDefinition(4, "solar_buffer2_temp", "Buffer 2 Temperature", "RO", "INT16", "°C", 0.1, "temperature", "measurement", None, None, None),
    RegisterDefinition(50, "solar_max_buffer_temp", "Set Maximum Buffer Temperature", "RW", "INT16", "°C", 0.1, "temperature", None, None, 25.0, 90.0, 0.1),
    RegisterDefinition(51, "solar_buffer_changeover_temp", "Set Buffer Changeover Temperature", "RW", "INT16", "°C", 0.1, "temperature", None, None, 25.0, 90.0, 0.1),
]

HEATING_CIRCUIT_REGISTERS: list[RegisterDefinition] = [
    RegisterDefinition(0, "hc_error_number", "Error Number", "RO", "INT16", None, 1, None, None, None, None, None),
    RegisterDefinition(1, "hc_operating_state", "Operating State", "RO", "UINT16", None, 1, None, None, HC_OPERATING_STATE, None, None),
    RegisterDefinition(2, "hc_flow_temp", "Flow Line Temperature", "RO", "INT16", "°C", 0.1, "temperature", "measurement", None, None, None),
    RegisterDefinition(3, "hc_return_temp", "Return Line Temperature", "RO", "INT16", "°C", 0.1, "temperature", "measurement", None, None, None),
    RegisterDefinition(4, "hc_room_temp", "Room Device Temperature", "RW", "INT16", "°C", 0.1, "temperature", "measurement", None, -29.9, 99.9, 0.1),
    RegisterDefinition(5, "hc_setpoint_flow_temp", "Setpoint Flow Line Temperature", "RW", "INT16", "°C", 0.1, "temperature", None, None, 15.0, 65.0, 0.1),
    RegisterDefinition(6, "hc_operating_mode", "Operating Mode", "RW", "INT16", None, 1, None, None, HC_OPERATING_MODE, None, None),
    RegisterDefinition(7, "hc_target_flow_temp", "Target Flow Line Temperature", "RO", "INT16", "°C", 0.1, "temperature", "measurement", None, None, None),
    RegisterDefinition(50, "hc_offset_flow_temp", "Set Offset Flow Line Temperature Setpoint", "RW", "INT16", "K", 0.1, None, None, None, -10.0, 10.0, 0.1),
    RegisterDefinition(51, "hc_setpoint_room_heating", "Set Setpoint Room Heating Temperature", "RW", "INT16", "°C", 0.1, "temperature", None, None, 15.0, 40.0, 0.1),
    RegisterDefinition(52, "hc_setpoint_room_cooling", "Set Setpoint Room Cooling Temperature", "RW", "INT16", "°C", 0.1, "temperature", None, None, 15.0, 40.0, 0.1),
]

AMBIENT_REGISTERS: list[RegisterDefinition] = [
    RegisterDefinition(0, "ambient_error_number", "Error Number", "RO", "INT16", None, 1, None, None, None, None, None),
    RegisterDefinition(1, "ambient_operating_state", "Operating State", "RO", "UINT16", None, 1, None, None, AMBIENT_OPERATING_STATE, None, None),
    RegisterDefinition(2, "ambient_temp_actual", "Actual Ambient Temperature", "RW", "INT16", "°C", 0.1, "temperature", "measurement", None, -50.0, 80.0, 0.1),
    RegisterDefinition(3, "ambient_temp_avg_1h", "Average Ambient Temperature 1h", "RO", "INT16", "°C", 0.1, "temperature", "measurement", None, None, None),
    RegisterDefinition(4, "ambient_temp_calculated", "Calculated Ambient Temperature", "RO", "INT16", "°C", 0.1, "temperature", "measurement", None, None, None),
]

EMANAGER_REGISTERS: list[RegisterDefinition] = [
    RegisterDefinition(0, "emanager_error_number", "Error Number", "RO", "INT16", None, 1, None, None, None, None, None),
    RegisterDefinition(1, "emanager_operating_state", "Operating State", "RO", "UINT16", None, 1, None, None, EMANAGER_OPERATING_STATE, None, None),
    RegisterDefinition(2, "emanager_actual_power", "Actual Power Input or Excess", "RW", "UINT16", "W", 1, "power", "measurement", None, None, None),
    RegisterDefinition(3, "emanager_power_consumption", "Actual Power Consumption", "RO", "INT16", "W", 1, "power", "measurement", None, None, None),
    RegisterDefinition(4, "emanager_power_setpoint", "Power Consumption Setpoint", "RO", "INT16", "W", 1, "power", "measurement", None, None, None),
]


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def calc_register_address(index: int, subindex: int, number: int) -> int:
    """Calculate the Modbus register address from index, subindex, and number.

    Formula: address = index * 1000 + subindex * 100 + number

    Examples:
        Heat pump 1, register 04:  1 * 1000 + 0 * 100 + 4  = 1004
        Heat pump 2, register 04:  1 * 1000 + 1 * 100 + 4  = 1104
        Heating circuit 12, reg 6: 5 * 1000 + 11 * 100 + 6 = 6106
        General Ambient, reg 02:   0 * 1000 + 0 * 100 + 2  = 2
        General E-Manager, reg 02: 0 * 1000 + 1 * 100 + 2  = 102
    """
    return index * 1000 + subindex * 100 + number
