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


from adafruit_logging import Handler, NOTSET

from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.nordic import UARTService


class BLEHandler(Handler):
    """Send logging output to the BLE uart port."""

    def __init__(self, level: int = NOTSET):
        """Create an instance.

        :param uart: the busio.UART instance to which to write messages
        """
        super().__init__(level)
        self._advertising_now = False
        ble = BLERadio()
        self._uart = UARTService()
        self._advertisement = ProvideServicesAdvertisement(self._uart)
        ble.start_advertising(self._advertisement)

    def format(self, record):
        """Generate a string to log.

        :param record: The record (message object) to be logged
        """
        return super().format(record) + "\r\n"

    def emit(self, record):
        """Generate the message and write it to the UART.

        :param record: The record (message object) to be logged
        """
        data = bytes(self.format(record), "utf-8")
        self._uart.write(data)
