"""
Adafruit IO based message handler for CircuitPython logging.

Adafruit invests time and resources providing this open source code.
Please support Adafruit and open source hardware by purchasing
products from Adafruit!

Written by Dave Astels for Adafruit Industries
Copyright (c) 2018 Adafruit Industries
Licensed under the MIT license.

All text above must be included in any redistribution.
"""

#pylint:disable=missing-super-argument

# Example:
#
# from aio_handler import AIOHandler
# import adafruit_logging as logging
# l = logging.getLogger('aio')
# l.addHandler(AIOHandler('test'))
# l.level = logging.ERROR
# l.error("test")

import board
import busio
from digitalio import DigitalInOut
import neopixel
from adafruit_logging import LoggingHandler
from adafruit_esp32spi import adafruit_esp32spi, adafruit_esp32spi_wifimanager
from adafruit_io.adafruit_io import RESTClient, AdafruitIO_RequestError

try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise


class AIOHandler(LoggingHandler):

    def __init__(self, name):
        """Create an instance."""
        # PyPortal ESP32 Setup
        esp32_cs = DigitalInOut(board.ESP_CS)
        esp32_ready = DigitalInOut(board.ESP_BUSY)
        esp32_reset = DigitalInOut(board.ESP_RESET)
        spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
        esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)
        status_light = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.2)
        wifi = adafruit_esp32spi_wifimanager.ESPSPI_WiFiManager(esp, secrets, status_light)

        # Set your Adafruit IO Username and Key in secrets.py
        # (visit io.adafruit.com if you need to create an account,
        # or if you need your Adafruit IO key.)
        ADAFRUIT_IO_USER = secrets['adafruit_io_user']
        ADAFRUIT_IO_KEY = secrets['adafruit_io_key']

        # Create an instance of the Adafruit IO REST client
        self._io = RESTClient(ADAFRUIT_IO_USER, ADAFRUIT_IO_KEY, wifi)

        self._name = '{0}-logging'.format(name)
        try:
            # Get the logging feed from Adafruit IO
            self._log_feed = self._io.get_feed(self._name)
        except AdafruitIO_RequestError:
            # If no logging feed exists, create one
            self._log_feed = self._io.create_new_feed(self._name)

    def emit(self, level, msg):
        """Generate the message and write it to the UART.

        :param level: The level at which to log
        :param msg: The core message

        """
        self._io.send_data(self._log_feed['key'], self.format(level, msg))
