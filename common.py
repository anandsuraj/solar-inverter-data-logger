import os
import sys
import StringIO
import contextlib
import netifaces as ni

@contextlib.contextmanager
def stdoutIO(stdout=None):
    old = sys.stdout
    if stdout is None:
        stdout = StringIO.StringIO()
    sys.stdout = stdout
    yield stdout
    sys.stdout = old

# A dictionary of parameter names and their shell command names
commandsDictionarySh = {
    'temperature_gpu': '/opt/vc/bin/vcgencmd measure_temp | awk \'{print substr($1, 6, 4)}\'',
    'temperature_cpu': 'cat /sys/class/thermal/thermal_zone0/temp',
    'uname': 'uname -a',
    'reference': 'cat /etc/rpi-issue',
    'release_os': 'cat /etc/os-release',
    'revision_processor': 'cat /proc/cpuinfo | grep "Revision" | cut -d \' \' -f 2',
    'serialnumber_processor': 'cat /proc/cpuinfo | grep "Serial" | cut -d \' \' -f 2',
    'hostname': 'echo $HOSTNAME',
    'username': 'whoami',
    'date': 'date'
}

# A dictionary of parameter names and their Python command names
commandsDictionaryPy = {
    'ipv4_eth0': 'ni.ifaddresses(\'eth0\')[2][0][\'addr\']',
    'ipv4_wlan0': 'ni.ifaddresses(\'wlan0\')[2][0][\'addr\']'
}

# A dictionary of formatting elements for different types of response formats
styleguide = {
    'header': {
        'html': '<html>\n<body>\n<table>\n<tbody>\n'
    },
    'simpleheader': {
        'html': '<html>\n<body>\n'
    },
    'entryLeft': {
        'html': '\t<tr>\n\t\t<td id=\"'
    },
    'entryMid': {
        'html': '\">'
    },
    'entryRight': {
        'html': '</td>\n\t</tr>\n'
    },
    'footer': {
        'html': '</tbody>\n</table>\n</body>\n</html>'
    },
    'simplefooter': {
        'html': '</body>\n</html>'
    }
}

# A wrapper function to retrieve values of parameters using either Shell or Python
def getParameterHandler(parameterName):
    if parameterName in commandsDictionarySh:
        return os.popen(commandsDictionarySh[parameterName]).read().strip('\n')
    elif parameterName in commandsDictionaryPy:
        with stdoutIO() as s:
            exec(commandsDictionaryPy[parameterName])
        return s.getvalue()
    else:
        return ''
