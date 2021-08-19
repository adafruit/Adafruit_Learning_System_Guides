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

from adafruit_portalbase import PortalBase

# Example:
#
# from aio_handler import AIOHandler
# import adafruit_logging as logging
# l = logging.getLogger('aio')
# # Pass in the device object based on portal_base
# # (Funhouse, PyPortal, MagTag, etc) as the 2nd parameter
# l.addHandler(AIOHandler('test'), portal_device)
# l.level = logging.ERROR
# l.error("test")

from adafruit_logging import LoggingHandler

class AIOHandler(LoggingHandler):

    def __init__(self, name, portal_device):
        """Create an instance."""
        self._log_feed_name=f"{name}-logging"
        if not issubclass(type(portal_device), PortalBase):
            raise TypeError("portal_device must be a PortalBase or subclass of PortalBase")
        self._portal_device = portal_device


    def emit(self, level, msg):
        """Generate the message and write it to the AIO Feed.

        :param level: The level at which to log
        :param msg: The core message

        """
        self._portal_device.push_to_io(self._log_feed_name, self.format(level, msg))
