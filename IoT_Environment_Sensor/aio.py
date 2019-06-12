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
import gc
import board
import busio
from digitalio import DigitalInOut
from adafruit_esp32spi import adafruit_esp32spi
import adafruit_esp32spi.adafruit_esp32spi_requests as requests
import adafruit_logging as logging
import rtc

logger = logging.getLogger('main')

TIME_SERVICE = "https://io.adafruit.com/api/v2/%s/integrations/time/strftime?x-aio-key=%s"
# our strftime is %Y-%m-%d %H:%M:%S.%L %j %u %z %Z see http://strftime.net/ for decoding details
# See https://apidock.com/ruby/DateTime/strftime for full options
TIME_SERVICE_STRFTIME = '&fmt=%25Y-%25m-%25d+%25H%3A%25M%3A%25S.%25L+%25j+%25u+%25z+%25Z'



# Get wifi details and more from a settings.py file
try:
    from secrets import secrets
except ImportError:
    logger.critical('WiFi settings are kept in settings.py, please add them there!')
    raise

class AIO(object):

    def __init__(self):
        try:
            esp32_cs = DigitalInOut(board.ESP_CS)
            esp32_busy = DigitalInOut(board.ESP_BUSY)
            esp32_reset = DigitalInOut(board.ESP_RESET)
            self._onboard_esp = True
        except AttributeError:
            esp32_cs = DigitalInOut(board.D10)
            esp32_busy = DigitalInOut(board.D9)
            esp32_reset = DigitalInOut(board.D6)
            self._onboard_esp = False

        spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
        self._esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_busy, esp32_reset)

        if self._esp.status == adafruit_esp32spi.WL_IDLE_STATUS:
            logger.debug('ESP32 found and in idle mode')
        logger.info('Firmware vers. %s', self._esp.firmware_version)
        logger.info('MAC addr: %s', ':'.join([hex(i)[2:4] for i in self._esp.MAC_address]))

        requests.set_interface(self._esp)

    @property
    def onboard_esp(self):
        return self._onboard_esp

    def connect(self):
        logger.debug("Connecting...")
        while not self._esp.is_connected:
            try:
                self._esp.connect_AP(secrets['ssid'], secrets['password'])
            except RuntimeError as e:
                logger.error("could not connect to AP, retrying: %s", e)
                continue

    def post(self, feed, payload):
        api_url = 'https://io.adafruit.com/api/v2/{0}/feeds/{1}/data'.format(secrets['aio_username'], feed)# pylint: disable=line-too-long
        logger.info('POSTing to %s', api_url)
        logger.info('payload: %s', str(payload))
        auth_header = {'X-AIO-KEY':secrets['aio_key']}
        self.connect()
        r = None
        tries = 0
        while True:
            if tries == 5:
                return False
            tries += 1
            try:
                r = requests.post(api_url, headers=auth_header, json=payload)
                logger.info('Status: %d', r.status_code)
                if r.status_code == 200:
                    logger.debug('Headers: %s', str(r.headers))
                    logger.debug('Text: %s', str(r.json()))
                else:
                    logger.debug('Text: %s', str(r.json()))
                break
            except RuntimeError as err:
                logger.error('Error posting: %s', str(err))
                logger.info('Resetting and reconnecting')
                self._esp.reset()
                self.connect()
        r.close()
        return r.status_code == 200

    # pylint:disable=too-many-locals
    def refresh_local_time(self):
        # pylint: disable=line-too-long
        """Fetch and "set" the local time of this microcontroller to the local time at the location, using an internet time API.
        Copied from adafruit_pyportal
        :param str location: Your city and country, e.g. ``"New York, US"``.
        """
        # pylint: enable=line-too-long
        api_url = None
        try:
            aio_username = secrets['aio_username']
            aio_key = secrets['aio_key']
        except KeyError:
            raise KeyError("\n\nOur time service requires a login/password to rate-limit. Please register for a free adafruit.io account and place the user/key in your secrets file under 'aio_username' and 'aio_key'")# pylint: disable=line-too-long

        location = secrets['timezone']
        if location:
            logger.debug('Getting time for timezone %s', location)
            api_url = (TIME_SERVICE + "&tz=%s") % (aio_username, aio_key, location)
        else: # we'll try to figure it out from the IP address
            logger.debug("Getting time from IP address")
            api_url = TIME_SERVICE % (aio_username, aio_key)
        api_url += TIME_SERVICE_STRFTIME
        logger.debug('Requesting time from %s', api_url)
        try:
            self.connect()
            response = requests.get(api_url)
            logger.debug('Time reply: %s', response.text)
            times = response.text.split(' ')
            the_date = times[0]
            the_time = times[1]
            year_day = int(times[2])
            week_day = int(times[3])
            is_dst = None  # no way to know yet
        except KeyError:
            raise KeyError("Was unable to lookup the time, try setting secrets['timezone'] according to http://worldtimeapi.org/timezones")  # pylint: disable=line-too-long
        year, month, mday = [int(x) for x in the_date.split('-')]
        the_time = the_time.split('.')[0]
        hours, minutes, seconds = [int(x) for x in the_time.split(':')]
        now = time.struct_time((year, month, mday, hours, minutes, seconds, week_day, year_day,
                                is_dst))
        rtc.RTC().datetime = now
        logger.debug('Fetched time: %s', str(now))

        # now clean up
        response.close()
        response = None
        gc.collect()
        return now
