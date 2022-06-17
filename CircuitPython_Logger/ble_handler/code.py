# SPDX-FileCopyrightText: 2019 Dave Astels for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
BLE based message handler for CircuitPython logging.

Adafruit invests time and resources providing this open source code.
Please support Adafruit and open source hardware by purchasing
products from Adafruit!

Written by Dave Astels for Adafruit Industries
Copyright (c) 2018 Adafruit Industries
Licensed under the MIT license.

All text above must be included in any redistribution.
"""


from adafruit_logging import Handler
from adafruit_ble.uart import UARTServer

class BLEHandler(Handler):
    """Send logging output to the BLE uart port."""

    def __init__(self):
        """Create an instance.

        :param uart: the busio.UART instance to which to write messages
        """
        self._advertising_now = False
        self._uart = UARTServer()
        self._uart.start_advertising()

    def format(self, record):
        """Generate a string to log.

        :param record: The record (message object) to be logged
        """
        return super().format(record) + '\r\n'

    def emit(self, record):
        """Generate the message and write it to the UART.

        :param record: The record (message object) to be logged
        """
        while not self._uart.connected:
            pass
        data = bytes(self.format(record), 'utf-8')
        self._uart.write(data)
