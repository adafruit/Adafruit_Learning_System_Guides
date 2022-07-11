# SPDX-FileCopyrightText: 2022 Carter Nelson for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
import rtc
import socketpool
import wifi
import adafruit_ntp
import neopixel

# --| User Config |--------------------------------
TZ_OFFSET = -7  # time zone offset in hours from UTC
WAKE_UP_HOUR = 07  # alarm time hour (24hr)
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

# Get current time using NTP
print("Fetching time from NTP.")
pool = socketpool.SocketPool(wifi.radio)
ntp = adafruit_ntp.NTP(pool, tz_offset=TZ_OFFSET)
rtc.RTC().datetime = ntp.datetime

# Fill with sleepy time colors
pixels.fill(SLEEP_COLOR)

# Wait for wake up time
now = time.localtime()
print("Current time: {:2}:{:02}".format(now.tm_hour, now.tm_min))
print("Waiting for alarm {:2}:{:02}".format(WAKE_UP_HOUR, WAKE_UP_MIN))
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
