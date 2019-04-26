"""
IoT environmental sensor node.

Adafruit invests time and resources providing this open source code.
Please support Adafruit and open source hardware by purchasing
products from Adafruit!

Written by Dave Astels for Adafruit Industries
Copyright (c) 2019 Adafruit Industries
Licensed under the MIT license.

All text above must be included in any redistribution.
"""

import adafruit_logging as logging

try:
    import struct
except ImportError:
    import ustruct as struct

logger = logging.getLogger('main')

class AirQualitySensor (object):

    def __init__(self, uart):
        self._uart = uart
        self._buffer = []
        self._pm10_standard = 0
        self._pm25_standard = 0
        self._pm100_standard = 0
        self._pm10_env = 0
        self._pm25_env = 0
        self._pm100_env = 0
        self._particles_03um = 0
        self._particles_05um = 0
        self._particles_10um = 0
        self._particles_25um = 0
        self._particles_50um = 0
        self._particles_100um = 0

    def read(self):
        data = self._uart.read(32)  # read up to 32 bytes
        data = list(data)

        self._buffer += data

        while self._buffer and self._buffer[0] != 0x42:
            self._buffer.pop(0)

        if len(self._buffer) > 200:
            self._buffer = []  # avoid an overrun if all bad data
            return False
        if len(self._buffer) < 32:
            return False

        if self._buffer[1] != 0x4d:
            self._buffer.pop(0)
            return False

        frame_len = struct.unpack(">H", bytes(self._buffer[2:4]))[0]
        if frame_len != 28:
            self._buffer = []
            return False

        logger.debug('buffer length: %d', len(self._buffer) - 4)
        frame = struct.unpack(">HHHHHHHHHHHHHH", bytes(self._buffer[4:32]))

        self._pm10_standard, self._pm25_standard, self._pm100_standard, self._pm10_env, \
          self._pm25_env, self._pm100_env, self._particles_03um, self._particles_05um, \
          self._particles_10um, self._particles_25um, self._particles_50um, \
          self._particles_100um, _, checksum = frame

        check = sum(self._buffer[0:30])

        if check != checksum:
            self._buffer = []
            return False

        return True

    @property
    def pm10_standard(self):
        return self._pm10_standard

    @property
    def pm25_standard(self):
        return self._pm25_standard

    @property
    def pm100_standard(self):
        return self._pm100_standard

    @property
    def pm10_env(self):
        return self._pm10_env

    @property
    def pm25_env(self):
        return self._pm25_env

    @property
    def pm100_env(self):
        return self._pm100_env

    @property
    def particles_03um(self):
        return self._particles_03um

    @property
    def particles_05um(self):
        return self._particles_05um

    @property
    def particles_10um(self):
        return self._particles_10um

    @property
    def particles_25um(self):
        return self._particles_25um

    @property
    def particles_50um(self):
        return self._particles_50um

    @property
    def particles_100um(self):
        return self._particles_100um
