# SPDX-FileCopyrightText: 2018 Dave Astels for Adafruit Industries
#
# SPDX-License-Identifier: MIT

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

from adafruit_logging import Handler

class UartHandler(Handler):
    """Send logging output to a serial port."""

    def __init__(self, uart):
        """Create an instance.

        :param uart: the busio.UART instance to which to write messages

        """
        self._uart = uart

    def format(self, record):
        """Generate a string to log.

        :param record: The record (message object) to be logged
        """
        return super().format(record) + '\r\n'

    def emit(self, record):
        """Generate the message and write it to the UART.

        :param record: The record (message object) to be logged
        """
        self._uart.write(bytes(self.format(record), 'utf-8'))
