# Solar Inverter Data Parsing and Storage

This repository contains code for interfacing with various solar inverter devices and logging their data to a centralized database. The code handles communication with different types of solar inverters and loggers, parses their measurements, and performs data validation and filtering. 

## Overview

The code is designed to work with the following devices:
1. **ABB PVS800 Central Inverter** - Communicates via Modbus TCP.
2. **Statcon Energiaa SMB-096 Combiner** - Communicates via Modbus RS485/RS422/RS232.
3. **SMA Sunny Web Box Logger** - Communicates via HTTP requests.

### Features

- **Data Retrieval**: Fetches real-time measurements from solar inverters and loggers.
- **Data Parsing**: Converts raw measurement data into readable formats.
- **Data Validation**: Applies thresholds to ensure data integrity and relevance.
- **Error Handling**: Manages communication errors and data inconsistencies.

## Installation

To use the code, ensure you have the following Python libraries installed:

```bash
pip install minimalmodbus pyModbusTCP requests
```

## Device Interfaces

### ABB PVS800 Central Inverter

The `inverterPVS800` class interfaces with the ABB PVS800 Central Inverter via Modbus TCP. It handles data retrieval, parsing, and validation.

**Constructor**:
- Initializes measurement labels, register addresses, and factors for the inverter.

**Methods**:
- `attach(identity)`: Connects to the inverter using the provided IP address and threshold values.
- `detach()`: Disconnects and resets internal state.
- `measure()`: Retrieves measurements from the inverter.
- `filter()`: Validates measurements against thresholds.
- `read(measurementIndex)`: Returns the measurement value for a given index.
- `cancel()`: Resets measurements and validity.

### Statcon Energiaa SMB-096 Combiner

The `combinerSMB096` class communicates with the Statcon Energiaa SMB-096 Combiner via Modbus RS485/RS422/RS232.

**Constructor**:
- Initializes measurement labels and factors for the combiner.

**Methods**:
- `attach(identity)`: Connects to the combiner using port name, baud rate, and slave address.
- `detach()`: Disconnects and resets internal state.
- `measure()`: Retrieves measurements from the combiner.
- `filter()`: Validates measurements against thresholds.
- `read(measurementIndex)`: Returns the measurement value for a given index.
- `cancel()`: Resets measurements and validity.

### SMA Sunny Web Box Logger

The `loggerSunnyWebBox` class interfaces with the SMA Sunny Web Box Logger via HTTP requests.

**Constructor**:
- Initializes measurement labels and address for the logger.

**Methods**:
- `attach(identity)`: Sets up the logger URL.
- `detach()`: Resets internal state.
- `measure()`: Fetches and parses data from the logger's web interface.
- `read(measurementIndex)`: Returns the measurement value for a given index.
- `cancel()`: Resets measurements and validity.

## Usage

To use the classes:

1. **Instantiate the class** for the device you want to interface with.
2. **Attach** the device using the `attach()` method with appropriate connection details.
3. **Retrieve measurements** using the `measure()` method.
4. **Filter measurements** using the `filter()` method (if necessary).
5. **Read specific measurements** using the `read()` method.
6. **Detach** the device using the `detach()` method when done.

Example usage:

```python
# Example for ABB PVS800
inverter = inverterPVS800()
inverter.attach({'threshold': {...}, 'IPAddress': '192.168.1.100'})
inverter.measure()
data = inverter.read(1)  # Read the first measurement
inverter.detach()
```

## Contributing

Contributions to improve the code, add new features, or fix bugs are welcome. Please follow the standard Git workflow for contributions.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact

For questions or support, please contact [surya13493@gmail.com](mailto:surya13493@gmail.com).
