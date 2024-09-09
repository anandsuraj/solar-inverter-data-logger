import json
import os
import threading
import requests
import MySQLdb
import datetime
import pytz
import time
import sys
import io
import contextlib

import common
import equipment

# Define the local timezone for timestamp conversion
timezoneLocal = pytz.timezone('Asia/Calcutta')

def universal2local(timeUniversal):
    """
    Converts a UTC datetime to local time and formats it as a string.
    """
    timeLocal = timeUniversal.replace(tzinfo=pytz.utc).astimezone(timezoneLocal)
    return timezoneLocal.normalize(timeLocal).strftime('%Y-%m-%d %H:%M:%S.%f %Z%z')

@contextlib.contextmanager
def stdoutIO(stdout=None):
    """
    Context manager for capturing stdout output.
    """
    old = sys.stdout
    if stdout is None:
        stdout = io.StringIO()
    sys.stdout = stdout
    yield stdout
    sys.stdout = old

class configurationS(object):
    """
    Class to manage software configuration.
    """
    def __init__(self):
        super(configurationS, self).__init__()
        self.settings = []
        self.measurements = []
        self.measurementValues = []
        self.measurementSets = {}
        self.measurementCount = 0
        self.servers = {}
        self.combinations = {}
        self.combinationCount = 0

    def cancel(self):
        """
        Resets measurement values.
        """
        self.measurementValues = []

    def load(self, filename):
        """
        Loads the configuration from a JSON file and processes it.
        """
        with open(filename) as filehandle:
            self.settings = json.load(filehandle)
        
        # Extract server configurations, measurement sets, and combinations
        self.servers = self.settings['servers']
        self.measurementSets = self.settings['measurementSets']
        self.combinations = self.settings['combinations']
        
        # Process combinations to gather unique measurements
        combination = {}
        combinationIndex = 0
        while combination is not None:
            try:
                combination = self.combinations['combination' + str(combinationIndex)]
            except KeyError:
                combination = None
            else:
                variables = self.settings['measurementSets'][str(combination['measurementSet'])]
                variable = {}
                variableIndex = 0
                while variable is not None:
                    try:
                        variable = variables['variable' + str(variableIndex)]
                    except KeyError:
                        variable = None
                    else:
                        if str(variable) not in self.measurements:
                            self.measurements.append(str(variable))
                    variableIndex += 1
            combinationIndex += 1

        # Update counts of combinations and measurements
        self.combinationCount = combinationIndex
        self.measurementCount = len(self.measurements)

class configurationH(object):
    """
    Class to manage hardware configuration.
    """
    def __init__(self):
        super(configurationH, self).__init__()
        # Dictionary of supported hardware devices
        self.devices = {
            0: ('SMA Solar Technology', 'Sunny Boy', 'inverterSunnyBoy'),
            1: ('SMA Solar Technology', 'Sunny Web Box', 'loggerSunnyWebBox'),
            2: ('Helios Systems', 'HS100', 'inverterHelios'),
            3: ('Enertech', '<blank>'),
            4: ('Danfoss', '<blank>'),
            5: ('Statcon Energiaa', 'SMB096', 'combinerSMB096'),
            6: ('Beijing EPSolar Technology', 'TracerA', 'chargerTracerA'),
            7: ('Delta Electronics', 'RPI', 'inverterRPI'),
            8: ('ABB', 'PVS800', 'inverterPVS800')
        }
        self.device = ''
        self.deviceType = ''
        self.manufacturer = ''
        self.modelNumber = 0
        self.serialNumber = 0
        self.identity = {}
        self.isLoaded = -1
        self.isAttached = -1
        self.toStore = ''

    def load(self, filename):
        """
        Loads the hardware configuration from a JSON file.
        """
        with open(filename) as filehandle:
            settings = json.load(filehandle)
            self.deviceType = settings['type']
            self.manufacturer = settings['manufacturer']
            self.modelNumber = settings['modelNumber']
            self.serialNumber = settings['serialNumber']
            self.identity = settings['identity']
            self.toStore = settings['toStore']
            self.isLoaded = 0
        return self.isLoaded

    def attach(self):
        """
        Attaches the hardware configuration to the software.
        """
        if self.isLoaded == -1:
            print('Attach Hardware Configuration Fail - Load incorrect')
        else:
            deviceIndex = -1
            for key, value in self.devices.items():
                if (value[0] == self.manufacturer) and (value[1] == self.modelNumber):
                    deviceIndex = key
                    self.isAttached = 1

            if self.isAttached == 1:
                with stdoutIO() as s:
                    exec('self.device = equipment.' + self.devices[deviceIndex][2] + '()')
                self.device.attach(self.identity)
                self.isAttached = 0
            else:
                print('Attach Hardware Configuration Fail - Host unrecognized')
        return self.isAttached

    def read(self, measurementName):
        """
        Reads the value of a measurement from the hardware or Raspberry Pi.
        """
        try:
            measurementIndex = [key for key, value in self.device.labels.items() if value == measurementName][0]
        except IndexError:
            try:
                measurementValue = common.getParameterHandler(measurementName)
            except KeyError:
                return -1
            else:
                return measurementValue
        else:
            return self.device.read(measurementIndex)

    def cancel(self):
        """
        Cancels the current set of measurements.
        """
        self.device.cancel()

if __name__ == '__main__':
    cH = configurationH()
    cS = configurationS()
    # Load software and hardware configurations
    cS.load('/home/pi/marshal/cS.json')
    cH.load('/home/pi/marshal/cH.json')
    # Attach hardware device
    cH.attach()
    cS.cancel()
    cH.cancel()

    # Retrieve measurements for all unique variables
    for measurementName in cS.measurements:
        cS.measurementValues.append(str(cH.read(measurementName)))

    # Process each combination and send data to the appropriate server
    for combinationIndex in range(cS.combinationCount):
        combination = cS.combinations['combination' + str(combinationIndex)]
        server = cS.servers[combination['server']]
        variables = cS.measurementSets[combination['measurementSet']]
        requestPayload = {}
        measurementData = {}
        
        # Gather measurement data
        variableName = ''
        variableIndex = 0
        while variableName is not None:
            try:
                variableName = variables.get('variableAlternate' + str(variableIndex)) if cH.device.sanity == -1 else variables.get('variable' + str(variableIndex))
            except KeyError:
                variableName = None
            else:
                if variableName:
                    measurementData[str(variableName)] = cS.measurementValues[cS.measurements.index(str(variableName))]
            variableIndex += 1

        hostData = {
            'type': cH.deviceType,
            'serialNumber': cH.serialNumber,
            'manufacturer': cH.manufacturer,
            'modelNumber': cH.modelNumber,
            'toStore': cH.toStore,
            'isOnDemand': 'False',
            'isSane': cH.device.sanity
        }

        requestPayload['t'] = universal2local(datetime.datetime.now()).strip(' IST+0530')
        requestPayload['h'] = hostData
        requestPayload['m'] = measurementData

        if variableIndex == 1:
            exit()

        if server['protocol'] == 'http':
            # Send data via HTTP request
            url = f"{server['protocol']}://{server['hostname']}:{server.get('portnumber', '')}{server['path']}"
            response = requests.post(url, auth=(server['username'], server['password']), json=requestPayload, verify=server.get('certificate', True))

            responsePayload = json.loads(response.text)
            measurementData = {}
            variableIndex = 0

            # Handle on-demand data requests
            while variableName is not None:
                try:
                    variableName = responsePayload.get('variable' + str(variableIndex))
                except KeyError:
                    variableName = None
                else:
                    if variableName:
                        measurementData[str(variableName)] = cH.read(str(variableName))
                variableIndex += 1

            if variableIndex > 1:
                hostData['isOnDemand'] = "True"
                requestPayload['t'] = universal2local(datetime.datetime.now()).strip(' IST+0530')
                requestPayload['h'] = hostData
                requestPayload['m'] = measurementData
                url = f"{server['protocol']}://{server['hostname']}:{server.get('portnumber', '')}{server['path']}"
                response = requests.post(url, auth=(server['username'], server['password']), json=requestPayload, verify=server.get('certificate', True))
                responsePayload = json.loads(response.text)

        elif server['protocol'] == 'mysql':
            # Insert data into MySQL database
            columns = ", ".join([f"`{col}`" for col in measurementData.keys()])
            values = ", ".join([f"'{val}'" for val in measurementData.values()])
            sqlQuery = f"INSERT INTO {server['table']} ({columns}) VALUES ({values})"
            conn = MySQLdb.connect(host=server['hostname'], user=server['username'], passwd=server['password'], db=server['database'])
            cursor = conn.cursor()
            cursor.execute(sqlQuery)
            conn.commit()
            cursor.close()
            conn.close()