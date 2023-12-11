# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense
import time
import rtc
from adafruit_magtag.magtag import MagTag

# The time of the thing!
EVENT_YEAR = 2021
EVENT_MONTH = 1
EVENT_DAY = 20
EVENT_HOUR = 12
EVENT_MINUTE = 00
# we'll make a python-friendly structure
event_time = time.struct_time(
    (
        EVENT_YEAR,
        EVENT_MONTH,
        EVENT_DAY,
        EVENT_HOUR,
        EVENT_MINUTE,
        0,  # we don't track seconds
        -1,
        -1,
        False,
    )
)  # we dont know day of week/year or DST

# Set up where we'll be fetching data from
# Check http://worldtimeapi.org/timezones for valid values
# pylint: disable=line-too-long
DATA_SOURCE = "http://worldtimeapi.org/api/timezone/America/New_York"
#DATA_SOURCE = "http://worldtimeapi.org/api/timezone/Europe/Stockholm"

magtag = MagTag()
magtag.network.connect()

magtag.add_text(
    text_font="Arial-Bold-24.bdf",
    text_position=(10, (magtag.graphics.display.height // 2) - 1,),
    line_spacing=0.85,
)

magtag.graphics.qrcode(b"https://buildbackbetter.com/", qr_size=3, x=200, y=25)

timestamp = None
lasttimefetch_stamp = None
while True:
    if not lasttimefetch_stamp or (time.monotonic() - lasttimefetch_stamp) > 3600:
        try:
            # America/New_York - 2020-11-15T11:14:49.970836-05:00
            # Europe/Stockholm - 2020-11-15T17:15:01.186119+01:00
            response = magtag.network.requests.get(DATA_SOURCE)
            datetime_str = response.json()['datetime']
            year = int(datetime_str[0:4])
            month = int(datetime_str[5:7])
            mday = int(datetime_str[8:10])
            hours = int(datetime_str[11:13])
            minutes = int(datetime_str[14:16])
            seconds = int(datetime_str[17:19])
            rtc.RTC().datetime = time.struct_time((year, month, mday, hours, minutes, seconds, 0, 0, False))
            lasttimefetch_stamp = time.monotonic()
        except (ValueError, RuntimeError, ConnectionError, OSError) as e:
            print("Some error occured, retrying! -", e)
            continue

    if not timestamp or (time.monotonic() - timestamp) > 60:  # once a minute
        now = time.localtime()
        print("Current time:", now)
        remaining = time.mktime(event_time) - time.mktime(now)
        print("Time remaining (s):", remaining)
        if remaining < 0:
            print("EVENT TIME")
            magtag.set_text("It's Time\nTo Party!")
            magtag.peripherals.neopixel_disable = False
            while True:  # that's all folks
                magtag.peripherals.neopixels.fill(0xFF0000)  # red
                time.sleep(0.25)
                magtag.peripherals.neopixels.fill(0xFFFFFF)  # white
                time.sleep(0.25)
                magtag.peripherals.neopixels.fill(0x0000FF)  # blue
                time.sleep(0.25)
        secs_remaining = remaining % 60
        remaining //= 60
        mins_remaining = remaining % 60
        remaining //= 60
        hours_remaining = remaining % 24
        remaining //= 24
        days_remaining = remaining
        print(
            "%d days, %d hours, %d minutes and %s seconds"
            % (days_remaining, hours_remaining, mins_remaining, secs_remaining)
        )
        magtag.set_text(
            "%d Days\n%d Hours\n%d Mins"
            % (days_remaining, hours_remaining, mins_remaining)
        )
        timestamp = time.monotonic()
    # wait around
    time.sleep(1)
