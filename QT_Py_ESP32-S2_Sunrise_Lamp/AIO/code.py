# SPDX-FileCopyrightText: 2022 Carter Nelson for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
import rtc
import wifi
import ssl
import socketpool
import adafruit_requests
import neopixel

# --| User Config |--------------------------------
WAKE_UP_HOUR = 7  # alarm time hour (24hr)
WAKE_UP_MIN = 30  # alarm time minute
SLEEP_COLOR = (0, 25, 150)  # sleepy time color as tuple
WAKEUP_COLOR = (255, 100, 0)  # wake up color as tuple
FADE_STEPS = 100  # wake up fade animation steps
FADE_DELAY = 0.1  # wake up fade animation speed
NEO_PIN = board.SCK  # neopixel pin
NEO_CNT = 12  # neopixel count
# -------------------------------------------------

# Set up NeoPixels
pixels = neopixel.NeoPixel(NEO_PIN, NEO_CNT)

# Get wifi details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

# Setup AIO time query URL
TIME_URL = "https://io.adafruit.com/api/v2/"
TIME_URL += secrets["aio_username"]
TIME_URL += "/integrations/time/strftime?x-aio-key="
TIME_URL += secrets["aio_key"]
TIME_URL += "&fmt=%25Y%3A%25m%3A%25d%3A%25H%3A%25M%3A%25S"

# Connect to local network
try:
    wifi.radio.connect(secrets["ssid"], secrets["password"])
except ConnectionError:
    print("Wifi failed to connect.")
    while True:
        pixels.fill(0)
        time.sleep(0.5)
        pixels.fill(0x220000)
        time.sleep(0.5)

print("Wifi connected.")

# Get current time using AIO
print("Fetching time.")
pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, ssl.create_default_context())
response = [int(x) for x in requests.get(TIME_URL).text.split(":")]
response += [0, 0, -1]
rtc.RTC().datetime = time.struct_time(response)

# Fill with sleepy time colors
pixels.fill(SLEEP_COLOR)

# Wait for wake up time
now = time.localtime()
print("Current time: {}:{}".format(now.tm_hour, now.tm_min))
print("Waiting for alarm {}:{}".format(WAKE_UP_HOUR, WAKE_UP_MIN))
while not (now.tm_hour == WAKE_UP_HOUR and now.tm_min == WAKE_UP_MIN):
    # just sleep until next time check
    time.sleep(30)
    now = time.localtime()

# Sunrise animation
print("Waking up!")
r1, g1, b1 = SLEEP_COLOR
r2, g2, b2 = WAKEUP_COLOR
dr = (r2 - r1) / FADE_STEPS
dg = (g2 - g1) / FADE_STEPS
db = (b2 - b1) / FADE_STEPS

for _ in range(FADE_STEPS):
    r1 += dr
    g1 += dg
    b1 += db
    pixels.fill((int(r1), int(g1), int(b1)))
    time.sleep(FADE_DELAY)

print("Done.")
