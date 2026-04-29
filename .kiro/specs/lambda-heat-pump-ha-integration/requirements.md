# Requirements Document: Lambda Heat Pump Home Assistant Integration

## Introduction

This integration connects Lambda heat pumps to Home Assistant via the Modbus TCP protocol.
It enables reading all sensor data and controlling the heat pump directly from Home Assistant.
The integration is designed as a Custom Integration (HACS-compatible) and supports multiple heat pumps, heating circuits, boilers, buffer tanks, solar modules, and general modules (Ambient, E-Manager) in a single configuration entry.

## Glossary

- **Integration**: The Home Assistant Custom Integration for Lambda heat pumps
- **Modbus_Client**: The component that manages the persistent TCP connection to the heat pump control unit
- **Config_Flow**: The Home Assistant UI configuration wizard for setting up the integration
- **Entity**: A Home Assistant entity (Sensor, Number, Select, Binary Sensor)
- **Coordinator**: The Home Assistant DataUpdateCoordinator that coordinates cyclic polling of Modbus registers
- **Register_Address**: Four-digit Modbus register address in the format Index-Subindex-Number (e.g. 1104)
- **Heatpump**: Lambda heat pump module (Index 1, Subindex 0-4)
- **Boiler**: Lambda domestic hot water module (Index 2, Subindex 0-4)
- **Buffer**: Lambda buffer tank / pool module (Index 3, Subindex 0-4)
- **Solar**: Lambda solar module (Index 4, Subindex 0-1)
- **Heating_Circuit**: Lambda heating circuit module (Index 5, Subindex 0-11)
- **General_Ambient**: Lambda general ambient module (Index 0, Subindex 0)
- **General_EManager**: Lambda general E-Manager module (Index 0, Subindex 1)
- **RO**: Read-Only register
- **RW**: Read-Write register
- **Datapoint_00_49**: Modbus datapoints with Number 00-49 that must be refreshed regularly when written (5-minute timeout)
- **Datapoint_50plus**: Modbus datapoints with Number >= 50 that are written once and stored permanently

---

## Requirements

### Requirement 1: UI Configuration (Config Flow)

**User Story:** As a user, I want to set up the integration through the Home Assistant user interface, so that I do not need to manually edit YAML files.

#### Acceptance Criteria

1. WHEN the user adds the integration, THE Config_Flow SHALL display an input form with the following fields: IP address of the heat pump, port (default: 502), number of heat pumps (1-5), number of heating circuits (0-12), number of boilers (0-5), number of buffer tanks (0-5), number of solar modules (0-2), enable ambient sensor (boolean, default: false), enable E-Manager (boolean, default: false).
2. WHEN the user enters an invalid IP address, THE Config_Flow SHALL display an error message and reject the input.
3. WHEN the user enters a port outside the range 1-65535, THE Config_Flow SHALL display an error message and reject the input.
4. WHEN the user completes the configuration, THE Config_Flow SHALL test the connection to the heat pump and display a meaningful error message on failure.
5. WHEN the configuration is completed successfully, THE Integration SHALL create all configured entities in Home Assistant.
6. WHEN the user reconfigures the integration (Options Flow), THE Config_Flow SHALL pre-fill the existing settings and allow changes.

---

### Requirement 2: Persistent Modbus TCP Connection

**User Story:** As an operator, I want the integration to maintain a persistent Modbus connection, so that the heat pump control unit is not disturbed by frequent connection setup and teardown.

#### Acceptance Criteria

1. THE Modbus_Client SHALL establish a single TCP connection to the control unit and reuse it for all read and write operations.
2. WHEN more than 45 seconds have passed since the last communication, THE Modbus_Client SHALL perform a keep-alive read to prevent the control unit's connection timeout (1 minute).
3. WHEN the connection to the control unit is interrupted, THE Modbus_Client SHALL automatically attempt reconnection with exponential backoff (max. 5 minutes).
4. IF a Modbus communication error occurs, THEN THE Modbus_Client SHALL log the error and mark affected entities as unavailable.
5. WHEN Home Assistant is restarted, THE Modbus_Client SHALL automatically re-establish the connection.
6. THE Modbus_Client SHALL use Modbus function code 0x03 for read access and 0x10 for write access.
7. THE Modbus_Client SHALL use Unit ID 1 for all communications.

---

### Requirement 3: Cyclic Polling of Sensor Data

**User Story:** As a user, I want all sensor data to be updated regularly, so that I always see current values in Home Assistant.

#### Acceptance Criteria

1. THE Coordinator SHALL poll all RO and RW registers of all configured modules at a configurable interval (default: 30 seconds).
2. WHEN RW registers with datapoint Number 00-49 have been written, THE Coordinator SHALL re-write these values within 4 minutes to prevent the control unit's 5-minute timeout.
3. WHEN a polling cycle fails, THE Coordinator SHALL log the error and retry at the next interval.
4. THE Coordinator SHALL query registers of multiple modules in a single polling round to minimize the number of Modbus requests.

---

### Requirement 4: Heat Pump Sensors (Read-Only)

**User Story:** As a user, I want to see all measured values of each configured heat pump as separate sensors in Home Assistant, so that I can monitor the operating state.

#### Acceptance Criteria

1. THE Integration SHALL create the following sensor entities for each configured heat pump (Subindex 0-4):
   - Error state (Register 00, UINT16, Enum: NONE/MESSAGE/WARNING/ALARM/FAULT)
   - Error number (Register 01, INT16)
   - Heat pump state (Register 02, UINT16, Enum with 14 states)
   - Operating state (Register 03, UINT16, Enum with 19 states)
   - Flow line temperature (Register 04, INT16, factor 0.01 °C)
   - Return line temperature (Register 05, INT16, factor 0.01 °C)
   - Volume flow heat sink (Register 06, INT16, factor 0.01 l/min)
   - Energy source inlet temperature (Register 07, INT16, factor 0.01 °C)
   - Energy source outlet temperature (Register 08, INT16, factor 0.01 °C)
   - Volume flow energy source (Register 09, INT16, factor 0.01 l/min)
   - Compressor rating (Register 10, UINT16, factor 0.01 %)
   - Heating capacity (Register 11, INT16, factor 0.1 kW)
   - Frequency inverter power consumption (Register 12, INT16, Watt)
   - COP (Register 13, INT16, factor 0.01)
   - Relay state 2nd heating stage (Register 19, INT16, Binary)
   - Statistics electrical energy since reset (Register 20-21, INT32, Wh)
   - Statistics thermal energy since reset (Register 22-23, INT32, Wh)
2. WHEN a heat pump with Subindex N is configured, THE Integration SHALL calculate the Register_Address as `1 * 1000 + N * 100 + Number` (e.g. heat pump 2, register 04 = address 1104).
3. THE Integration SHALL represent enum values (error state, heat pump state, operating state) as human-readable text states in Home Assistant.
4. THE Integration SHALL register temperature sensors with unit °C, power sensors with kW/W, and volume flow sensors with l/min in Home Assistant.
5. THE Integration SHALL process INT32 registers (statistics) by reading two consecutive 16-bit registers and combining them into a 32-bit value.

---

### Requirement 5: Heat Pump Controls (Read-Write)

**User Story:** As a user, I want to control the heat pump through Home Assistant, so that I can set heating requests and target temperatures.

#### Acceptance Criteria

1. THE Integration SHALL create the following controllable entities for each configured heat pump:
   - Modbus release password (Register 14, UINT16, Number entity)
   - Request type (Register 15, INT16, Select entity: NO REQUEST / FLOW PUMP CIRCULATION / CENTRAL HEATING / CENTRAL COOLING / DOMESTIC HOT WATER)
   - Request flow line temperature (Register 16, INT16, Number entity, 0.0-70.0 °C, step 0.1 °C)
   - Request return line temperature (Register 17, INT16, Number entity, 0.0-65.0 °C, step 0.1 °C)
   - Request heat sink temperature difference (Register 18, INT16, Number entity, 0.0-35.0 K, step 0.1 K)
2. WHEN the user sets the request type, THE Integration SHALL first write the release password to Register 14 and then write the request type to Register 15.
3. WHEN an RW register with Number 00-49 is written, THE Coordinator SHALL store this value as an active write value and re-write it within 4 minutes.
4. WHEN the user enters a value outside the defined range, THE Integration SHALL reject the input and display an error message in Home Assistant.
5. IF the release password has been entered incorrectly 10 times, THEN THE Integration SHALL log an error and notify the user.

---

### Requirement 6: Support for Additional Modules (Boiler, Buffer, Solar, Heating Circuit)

**User Story:** As a user, I want to monitor and control boilers, buffer tanks, solar modules, and heating circuits in Home Assistant, so that I can centrally manage the entire heating system.

#### Acceptance Criteria

1. THE Integration SHALL create the following sensor and control entities for each configured boiler (Index 2, Subindex 0-4):
   - Error number (Register 00, RO, INT16)
   - Operating state (Register 01, RO, UINT16, Enum: STBY/DHW/LEGIO/SUMMER/FROST/HOLIDAY/PRO-STOP/ERROR/OFF/PROMPT-DHW/TRAILING-STOP/TEMP-LOCK/STBY-FROST)
   - Actual high temperature (Register 02, RO, INT16, factor 0.1 °C)
   - Actual low temperature (Register 03, RO, INT16, factor 0.1 °C)
   - Actual circulation temperature (Register 04, RO, INT16, factor 0.1 °C)
   - Actual circulation pump state (Register 05, RO, INT16, Binary: 0=OFF / 1=ON)
   - Set maximum boiler temperature (Register 50, RW, INT16, factor 0.1 °C, min=25.0 °C, max=65.0 °C)

2. THE Integration SHALL create the following sensor and control entities for each configured buffer tank (Index 3, Subindex 0-4):
   - Error number (Register 00, RO, INT16)
   - Operating state (Register 01, RO, UINT16, Enum: STBY/HEATING/COOLING/SUMMER/FROST/HOLIDAY/PRO-STOP/ERROR/OFF/STBY-FROST)
   - Actual high temperature (Register 02, RO, INT16, factor 0.1 °C)
   - Actual low temperature (Register 03, RO, INT16, factor 0.1 °C)
   - Modbus buffer temperature high setpoint (Register 04, RW, INT16, factor 0.1 °C, min=0 °C, max=90 °C)
   - Request type (Register 05, RW, INT16, Enum: INVALID REQUEST=-1 / NO REQUEST=0 / FLOW PUMP CIRCULATION=1 / CENTRAL HEATING=2 / CENTRAL COOLING=3)
   - Request flow line temperature setpoint (Register 06, RW, INT16, factor 0.1 °C, min=0.0 °C, max=65.0 °C)
   - Request return line temperature setpoint (Register 07, RW, INT16, factor 0.1 °C, min=0.0 °C, max=60.0 °C)
   - Request heat sink temperature difference setpoint (Register 08, RW, INT16, factor 0.1 K, min=0.0 K, max=35.0 K)
   - Modbus request heating capacity (Register 09, RW, INT16, factor 0.1 kW, min=0.0 kW, optional)
   - Set maximum buffer temperature (Register 50, RW, INT16, factor 0.1 °C, min=25.0 °C, max=60.0 °C)

3. THE Integration SHALL create the following sensor and control entities for each configured solar module (Index 4, Subindex 0-1):
   - Error number (Register 00, RO, INT16)
   - Operating state (Register 01, RO, UINT16, Enum: STBY/HEATING/SUMMER/ERROR/OFF)
   - Collector temperature (Register 02, RO, INT16, factor 0.1 °C)
   - Buffer 1 temperature (Register 03, RO, INT16, factor 0.1 °C)
   - Buffer 2 temperature (Register 04, RO, INT16, factor 0.1 °C)
   - Set maximum buffer temperature (Register 50, RW, INT16, factor 0.1 °C, min=25.0 °C, max=90.0 °C)
   - Set buffer changeover temperature (Register 51, RW, INT16, factor 0.1 °C, min=25.0 °C, max=90.0 °C)

4. THE Integration SHALL create the following sensor and control entities for each configured heating circuit (Index 5, Subindex 0-11):
   - Error number (Register 00, RO, INT16)
   - Operating state (Register 01, RO, UINT16, Enum with 21 states: HEATING/ECO/COOLING/FLOORDRY/FROST/MAX-TEMP/ERROR/SERVICE/HOLIDAY/CH-SUMMER/CC-WINTER/PRIO-STOP/OFF/RELEASE-OFF/TIME-OFF/STBY/STBY-HEATING/STBY-ECO/STBY-COOLING/STBY-FROST/STBY-FLOORDRY)
   - Flow line temperature (Register 02, RO, INT16, factor 0.1 °C)
   - Return line temperature (Register 03, RO, INT16, factor 0.1 °C)
   - Room device temperature (Register 04, RW, INT16, factor 0.1 °C, min=-29.9 °C, max=99.9 °C)
   - Setpoint flow line temperature (Register 05, RW, INT16, factor 0.1 °C, min=15.0 °C, max=65.0 °C)
   - Operating mode (Register 06, RW, INT16, Enum: OFF/MANUAL/AUTOMATIC/AUTO-HEATING/AUTO-COOLING/FROST/SUMMER/FLOORDRY)
   - Target flow line temperature (Register 07, RO, INT16, factor 0.1 °C)
   - Set offset flow line temperature setpoint (Register 50, RW, INT16, factor 0.1 °C, min=-10.0 K, max=10.0 K)
   - Set setpoint room heating temperature (Register 51, RW, INT16, factor 0.1 °C, min=15.0 °C, max=40.0 °C)
   - Set setpoint room cooling temperature (Register 52, RW, INT16, factor 0.1 °C, min=15.0 °C, max=40.0 °C)

5. WHEN the count of a module type is configured to 0, THE Integration SHALL not create any entities for that module type.
6. THE Integration SHALL calculate the Register_Address for all modules using the scheme `Index * 1000 + Subindex * 100 + Number`.

---

### Requirement 7: Home Assistant Entity Conventions

**User Story:** As a Home Assistant user, I want the integration to follow HA conventions, so that it integrates seamlessly into my existing setup.

#### Acceptance Criteria

1. THE Integration SHALL assign a unique entity ID to each entity following the scheme `lambda_heat_pump_{module_type}_{instance}_{datapoint}`.
2. THE Integration SHALL assign a human-readable display name to each entity in the form `Lambda {ModuleType} {Instance} {Datapoint}`.
3. THE Integration SHALL assign all entities to a Home Assistant Device per configured heat pump unit.
4. THE Integration SHALL set the correct Home Assistant Device Classes (temperature, power, energy, etc.) for all sensor entities.
5. THE Integration SHALL set the correct State Classes (measurement, total_increasing) for energy and measurement sensors.
6. WHEN an entity cannot be read, THE Integration SHALL set the entity state to `unavailable`.
7. THE Integration SHALL provide a `manifest.json` with correct HACS metadata (domain, name, version, dependencies).
8. THE Integration SHALL provide translations (strings.json / translations/en.json) for all UI texts of the Config Flow.

---

### Requirement 8: Error Handling and Robustness

**User Story:** As an operator, I want the integration to run stably and handle errors cleanly, so that the heat pump is not disturbed by faulty communication.

#### Acceptance Criteria

1. IF the connection to the heat pump cannot be established when Home Assistant starts, THEN THE Integration SHALL not block the startup and SHALL periodically attempt reconnection.
2. IF a Modbus timeout occurs, THEN THE Modbus_Client SHALL mark the connection as interrupted and start a reconnection attempt.
3. IF an invalid register value is received (e.g. outside the expected value range), THEN THE Integration SHALL log the value and set the entity to `unavailable`.
4. THE Integration SHALL write all errors to the Home Assistant log with appropriate log levels (DEBUG, WARNING, ERROR).
5. WHEN the integration is unloaded, THE Modbus_Client SHALL cleanly close the TCP connection.
6. THE Integration SHALL be thread-safe and correctly serialize concurrent read and write accesses to the Modbus_Client.

---

### Requirement 9: General Modules (Ambient Sensor and E-Manager)

**User Story:** As a user, I want to monitor and control the general ambient sensor and E-Manager module in Home Assistant, so that I can integrate outdoor temperature and energy management into my heating system.

#### Acceptance Criteria

1. WHERE the ambient sensor is enabled, THE Integration SHALL create the following entities for the General_Ambient module (Index 0, Subindex 0):
   - Error number (Register 00, RO, INT16)
   - Operating state (Register 01, RO, UINT16, Enum: OFF/AUTOMATIK/MANUAL/ERROR)
   - Actual ambient temperature (Register 02, RW, INT16, factor 0.1 °C, min=-50.0 °C, max=80.0 °C)
   - Average ambient temperature 1h (Register 03, RO, INT16, factor 0.1 °C)
   - Calculated ambient temperature (Register 04, RO, INT16, factor 0.1 °C)

2. WHERE the E-Manager is enabled, THE Integration SHALL create the following entities for the General_EManager module (Index 0, Subindex 1):
   - Error number (Register 00, RO, INT16)
   - Operating state (Register 01, RO, UINT16, Enum: OFF/AUTOMATIK/MANUAL/ERROR/OFFLINE)
   - Actual power input or excess (Register 02, RW, UINT16 or INT16, Watt: UINT16 for input power 0-65535W, INT16 for excess power -32768-32767W, depending on system settings)
   - Actual power consumption (Register 03, RO, INT16, Watt)
   - Power consumption setpoint (Register 04, RO, INT16, Watt)

3. WHEN the ambient sensor is disabled, THE Integration SHALL not create any entities for the General_Ambient module.
4. WHEN the E-Manager is disabled, THE Integration SHALL not create any entities for the General_EManager module.
5. THE Integration SHALL calculate the Register_Address for general modules using the scheme `0 * 1000 + Subindex * 100 + Number` (Ambient: Subindex 0, E-Manager: Subindex 1).
