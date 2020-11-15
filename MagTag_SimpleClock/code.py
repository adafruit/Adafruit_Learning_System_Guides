# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense
import time
from adafruit_magtag.magtag import MagTag

HOUR_MODE_24 = False    # we're american, dammit!

magtag = MagTag()
magtag.network.connect()

# Color
magtag.add_text(
    text_font="Helvetica-Bold-100.bdf",
    text_position=(
        (magtag.graphics.display.width // 2) - 1,
        (magtag.graphics.display.height // 2) - 1,
    ),
    text_anchor_point=(0.5, 0.5),
)

timestamp = None
last_timestr = None
while True:
    if not timestamp or (time.monotonic() - timestamp > 3600):
        magtag.get_local_time() # resync time once an hour
        timestamp = time.monotonic()
    now = time.localtime()
    hour = now[3]
    minute = now[4]
    if HOUR_MODE_24:
        timestr = "%d:%02d" % (hour, minute)
    else:
        is_pm = (hour >= 12)
        hour %= 12
        if hour == 0:
            hour = 12
        timestr = "%d:%02d" % (hour, minute)
    if timestr != last_timestr:
        magtag.set_text(timestr)
        last_timestr = timestr
    time.sleep(1)
