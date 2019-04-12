"""
UART based message handler for CircuitPython logging.

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
# import board
# import busio
# from uart_handler import UartHandler
# import adafruit_logging as logging
#
# uart = busio.UART(board.TX, board.RX, baudrate=115200)
# logger = logging.getLogger('uart')
# logger.addHandler(UartHandler(uart))
# logger.level = logging.INFO
# logger.info('testing')

from adafruit_logging import LoggingHandler
from adafruit_ble.uart import UARTServer

class BLEHandler(LoggingHandler):
    """Send logging output to the BLE uart port."""

    def __init__(self):
        """Create an instance.

        :param uart: the busio.UART instance to which to write messages

        """
        self._advertising_now = False
        self._uart = UARTServer()
        self._uart.start_advertising()

    def format(self, level, msg):
        """Generate a string to log.

        :param level: The level at which to log
        :param msg: The core message

        """
        return super().format(level, msg) + '\r\n'

    def emit(self, level, msg):
        """Generate the message and write it to the UART.

        :param level: The level at which to log
        :param msg: The core message

        """
        while not self._uart.connected:
            pass

        data = bytes(self.format(level, msg), 'utf-8')
        for i in range(len(data)):
            self._uart.write(data[i:i+1])
