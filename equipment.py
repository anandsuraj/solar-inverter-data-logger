import datetime
import requests
import minimalmodbus
from pyModbusTCP.client import ModbusClient

# Constants for measurement labels and factors
MEASUREMENT_LABELS_PVS800 = {
    1: 'currentGrid', 2: 'powerGrid', 3: 'frequencyGrid', 4: 'pfGrid', 5: 'reactivepowerGrid',
    6: 'voltagePV', 7: 'currentPV', 8: 'powerPV', 9: 'temperatureInverter', 10: 'modeInverter',
    11: 'uptimeInverter', 12: 'electricityGeneration', 13: 'kiloGeneration', 14: 'megaGeneration',
    15: 'gigaGeneration', 16: 'breakercountGrid', 17: 'breakercountPV'
}

MEASUREMENT_LABELS_SMB096 = {
    1: 'current1', 2: 'current2', 3: 'current3', 4: 'current4', 5: 'current5',
    6: 'current6', 7: 'current7', 8: 'current8', 9: 'current9', 10: 'current10',
    11: 'current11', 12: 'current12', 13: 'voltage_DC', 14: 'status_spd', 15: 'status_switch',
    16: 'temperature_scb'
}

MEASUREMENT_LABELS_SUNNY_WEB_BOX = {
    0: 'power_D', 1: 'energyToday_D', 2: 'energyCumulative_D'
}

FACTORS_PVS800 = {
    1: 1, 2: 10, 3: 100, 4: 1, 5: 1, 6: 1, 7: 1, 8: 1, 9: 1, 10: 1, 11: 1, 12: 1, 13: 1, 14: 1, 15: 1, 16: 1, 17: 1
}

FACTORS_SMB096 = {
    1: 100, 2: 100, 3: 100, 4: 100, 5: 100, 6: 100, 7: 100, 8: 100, 9: 100, 10: 100, 11: 100, 12: 100,
    13: 1, 14: 1, 15: 1, 16: 10
}

# Base class for Modbus devices
class ModbusDevice:
    def __init__(self, labels, factors):
        self.labels = labels
        self.factors = factors
        self.threshold = {}
        self.payload = []
        self.timestmp = ''
        self.sanity = -1

    def attach(self, identity):
        raise NotImplementedError("Subclasses should implement this method")

    def detach(self):
        self.payload = []
        self.timestmp = ''
        self.sanity = -1

    def measure(self):
        raise NotImplementedError("Subclasses should implement this method")

    def filter(self):
        for index in range(len(self.labels)):
            label = self.labels[index + 1]
            if label in self.threshold:
                threshold = self.threshold[label]
                value = float(self.payload[index])
                if threshold['type'] == 'max' and value > float(threshold['value']):
                    return -1
                if threshold['type'] == 'min' and value < float(threshold['value']):
                    return -1
                if threshold['type'] == 'pass' and (value >= float(threshold['valueMax']) or value <= float(threshold['valueMin'])):
                    return -1
        return 0

    def read(self, measurementIndex):
        if self.sanity != 0:
            self.measure()
        self.sanity = self.filter()
        return self.payload[measurementIndex - 1] if 0 <= measurementIndex - 1 < len(self.payload) else None

    def cancel(self):
        self.payload = []
        self.sanity = -1


class InverterPVS800(ModbusDevice):
    def __init__(self):
        super().__init__(MEASUREMENT_LABELS_PVS800, FACTORS_PVS800)
        self.registerAddresses = {
            1: 106, 2: 109, 3: 111, 4: 112, 5: 113, 6: 133, 7: 117, 8: 118, 9: 119,
            10: 120, 11: 124, 12: 125, 13: 126, 14: 127, 15: 128, 16: 129, 17: 130
        }
        self.handle = None
        self.IPAddress = ''

    def attach(self, identity):
        self.threshold = identity.get('threshold', {})
        self.IPAddress = identity.get('IPAddress', '')
        self.handle = ModbusClient(host=self.IPAddress, auto_open=True)

    def detach(self):
        super().detach()
        self.handle = None
        self.IPAddress = ''

    def measure(self):
        self.timestmp = str(datetime.datetime.now())
        self.payload = []
        for index in range(len(self.labels)):
            registerData = float(self.handle.read_holding_registers(self.registerAddresses[index + 1], 1)[0]) / float(self.factors[index + 1])
            self.payload.append(str(registerData))
        self.sanity = 0


class CombinerSMB096(ModbusDevice):
    def __init__(self):
        super().__init__(MEASUREMENT_LABELS_SMB096, FACTORS_SMB096)
        self.portName = ''
        self.baudrate = 0
        self.slaveAddress = 0
        self.handle = None

    def attach(self, identity):
        self.threshold = identity.get('threshold', {})
        self.portName = identity.get('portName', '')
        self.baudrate = int(identity.get('baudrate', 9600))
        self.slaveAddress = int(identity.get('slaveAddress', 0))
        minimalmodbus.BAUDRATE = self.baudrate
        self.handle = minimalmodbus.Instrument(self.portName, self.slaveAddress)

    def detach(self):
        super().detach()
        self.portName = ''
        self.baudrate = 0
        self.slaveAddress = 0
        self.handle = None

    def measure(self):
        self.timestmp = str(datetime.datetime.now())
        self.payload = []
        for index in range(len(self.labels)):
            registerAddress = index
            registerData = float(self.handle.read_register(registerAddress, functioncode=3)) / float(self.factors[index + 1])
            self.payload.append(str(registerData))
        self.sanity = 0


class LoggerSunnyWebBox(ModbusDevice):
    def __init__(self):
        super().__init__(MEASUREMENT_LABELS_SUNNY_WEB_BOX, {})

    def attach(self, identity):
        self.address = identity.get('address', '')

    def detach(self):
        super().detach()
        self.address = ''

    def measure(self):
        self.timestmp = str(datetime.datetime.now())
        self.payload = []
        try:
            text = requests.get(f"{self.address}home.htm?saltpepper={self.timestmp}").text
            self.payload = self._parse_sunny_web_box_data(text)
            self.sanity = 0
        except Exception as e:
            print(f"Error measuring data: {e}")
            self.sanity = -1

    def _parse_sunny_web_box_data(self, text):
        def extract_value(subtext, unit):
            if subtext.find(unit) != -1:
                value = float(subtext[:subtext.find(' ')])
                if unit == 'kW':
                    return value * 1000.0
                elif unit == 'Wh':
                    return value / 1000.0
                elif unit == 'MWh':
                    return value * 1000.0
                return value
            return 0.0

        subtext = text
        values = []
        units = ['Power', 'DailyYield', 'TotalYield']
        for unit in units:
            subtext = subtext[subtext.find(f'{unit}\"'):]
            subtext = subtext[subtext.find('>') + 1:]
            unit_type = subtext[subtext.find(' ') + 1:subtext.find('<')]
            values.append(str(extract_value(subtext, unit_type)))
        return values
