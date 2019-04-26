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

import time
import adafruit_gps
import adafruit_logging as logging


logger = logging.getLogger('main')

class Gps(object):

    def __init__(self, uart):
        self._gps = adafruit_gps.GPS(uart, debug=False)
        self._latitude = 0
        self._longitude = 0


    def begin(self):
        self._gps.send_command(b'PMTK314,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0')
        self._gps.send_command(b'PMTK220,1000')


    def get_fix(self):
        try:
            logger.debug('Calling gps update')
            self._gps.update()
            logger.debug('Back from gps update')
            while not self._gps.has_fix:
                # Try again if we don't have a fix yet.
                logger.debug('Waiting for fix...')
                time.sleep(0.1)
                self._gps.update()
            return True
        except UnicodeError:
            return False


    def read(self):
        logger.debug('Reading GPS')
        self._latitude = self._gps.latitude
        self._longitude = self._gps.longitude


    @property
    def latitude(self):
        return self._latitude


    @property
    def longitude(self):
        return self._longitude
