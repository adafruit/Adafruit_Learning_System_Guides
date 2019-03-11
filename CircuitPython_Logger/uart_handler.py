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
# from adafruit_logger.uart_handler import UartHandler
# from adafruit_logger import *
#
# uart = busio.UART(board.TX, board.RX, baudrate=115200)
# logger = Logger(UartHandler(uart))
# logger.level = INFO
# logger.info('testing')

from adafruit_logger import LoggingHandler

class UartHandler(LoggingHandler):
    """Send logging output to a serial port."""

    def __init__(self, uart):
        """Create an instance.

        :param uart: the busio.UART instance to which to write messages

        """
        self._uart = uart

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
        self._uart.write(bytes(self.format(level, msg), 'utf-8'))
