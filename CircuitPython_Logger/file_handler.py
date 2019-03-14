"""
File based message handler for CircuitPython logging.

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
#
# from file_handler import FileHandler
# import adafruit_logging as logging
# l = logging.getLogger('file')
# l.addHandler(FileHandler('log.txt'))
# l.level = logging.ERROR
# l.error("test")

from adafruit_logging import LoggingHandler

class FileHandler(LoggingHandler):

    def __init__(self, filename):
        """Create an instance.

        :param filename: the name of the file to which to write messages

        """
        self._filename = filename

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
        with open(self._filename, 'a+') as f:
            f.write(self.format(level, msg))
