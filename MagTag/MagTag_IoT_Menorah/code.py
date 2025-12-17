# SPDX-FileCopyrightText: 2025 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""MagTag IoT Menorah"""
import time
import displayio
from adafruit_magtag.magtag import MagTag
from adafruit_display_shapes.circle import Circle

# latitude
lat = 42.36
# longitude
long = -71.06
# timezone offset from GMT
tz_offset = -5
hanukkah_date = [12, 14] # month, date
# open meteo API for sunset, today and tomorrow
sunset_fetch = (f"https://api.open-meteo.com/v1/forecast?"
                f"latitude={lat}&longitude={long}&daily=sunset"
                f"&timezone=auto&forecast_days=2&timeformat=unixtime")
today_sunset = ["daily", "sunset", 0]
tomorrow_sunset = ["daily", "sunset", 1]
#  create MagTag and connect to network
try:
    magtag = MagTag(
    url=sunset_fetch,
    json_path=(today_sunset, tomorrow_sunset),
    default_bg=0x000000,
    )
    magtag.network.connect()
except (ConnectionError, ValueError, RuntimeError) as e:
    print("*** MagTag(), Some error occured, retrying! -", e)
    # Exit program and restart in 1 seconds.
    magtag.exit_and_deep_sleep(1)

#  displayio groups
group = displayio.Group()
menorah_group = displayio.Group()
circle_group = displayio.Group()

#  import menorah bitmap
filename = "/magtag_menorah.bmp"
menorah = displayio.OnDiskBitmap(filename)
menorah_grid = displayio.TileGrid(menorah, pixel_shader=menorah.pixel_shader)

#  add bitmap to its group
menorah_group.append(menorah_grid)
#  add menorah group to the main group
group.append(menorah_group)

#  list of circle positions
spots = (
    (148, 16), # shamash
    (272, 31), # 1st
    (242, 31), # 2nd
    (212, 31), # 3rd
    (182, 31), # 4th
    (114, 31), # 5th
    (84, 31), # 6th
    (54, 31), # 7th
    (24, 31), # 8th
    )

#  creating the circles & pulling in positions from spots
for spot in spots:
    circle = Circle(x0=spot[0], y0=spot[1], r=13, fill=0xFFFFFF)
	#  adding circles to their display group
    circle_group.append(circle)

#  adding circles group to main display group
group.append(circle_group)

#  grabs time from network
magtag.get_local_time()
#  parses time into month, date, etc
now = time.localtime()
print(f"now is {now}")
month = now[1]
day = now[2]
day_count = 0
seconds_to_sleep = 3600
# check if its hanukkah
if month == hanukkah_date[0]:
    # get the night count for hanukkah
    if hanukkah_date[1] <= day <= hanukkah_date[1] + 8:
        day_count = (day - hanukkah_date[1]) + 1
        print(f"it's the {day_count} night of hanukkah!")
    elif day > hanukkah_date[1] + 8:
        day_count = 8
    unix_now = time.mktime(now)
    # adjust unixtime to your timezone (otherwise in GMT-0)
    unix_now = unix_now + -(tz_offset*3600)
    print(unix_now)
    sunsets = magtag.fetch()
    if unix_now < sunsets[0]:
        seconds_to_sleep = sunsets[0] - unix_now
        # don't light the next candle until sunset
        if 0 < day_count < 8:
            day_count -= 1
            print("the sun is still up")
    else:
        seconds_to_sleep = sunsets[1] - unix_now
    if day_count > 0:
        #  sets colors of circles to transparent to reveal flames
        for i in range(day_count + 1):
            circle_group[i].fill = None
            time.sleep(0.1)

#  updates display with bitmap and current candles
magtag.display.root_group = group
time.sleep(5)
magtag.display.refresh()
time.sleep(5)

#  goes into deep sleep till next sunset
print("entering deep sleep")
print(f"sleeping for {seconds_to_sleep} seconds")
magtag.exit_and_deep_sleep(seconds_to_sleep)

#  entire code will run again after deep sleep cycle
#  similar to hitting the reset button
