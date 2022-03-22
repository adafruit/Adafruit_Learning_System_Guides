# SPDX-FileCopyrightText: 2022 Eva Herrada for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time

import board
from adafruit_lc709203f import LC709203F
import adafruit_pcf8523
from simpleio import tone
import neopixel
from adafruit_led_animation.animation.rainbow import Rainbow

rtc = adafruit_pcf8523.PCF8523(board.I2C())
battery = LC709203F(board.I2C())
indicator = neopixel.NeoPixel(board.A1, 1)

LEDs = neopixel.NeoPixel(board.A2, 20)
LEDs.fill((0, 0, 0))
rainbow = Rainbow(LEDs, speed=0.1, period=2)

days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
sleep = {
    0: (22, 50),
    1: (23, 08),
    2: (22, 50),
    3: (22, 50),
    4: (22, 50),
    5: None,
    6: None,
}
wake = {
    0: (11, 30),
    1: (9, 50),
    2: (9, 50),
    3: (9, 50),
    4: (9, 50),
    5: (9, 50),
    6: (11, 30),
}

BPM = 160

ringtone = [
    (330, 0.5),
    (294, 0.5),
    (185, 1),
    (208, 1),
    (277, 0.5),
    (247, 0.5),
    (147, 1),
    (165, 1),
    (247, 0.5),
    (220, 0.5),
    (139, 1),
    (165, 1),
    (220, 2),
]

SET_DATE = False  # Set this to True on first run and False for subsequent runs
if SET_DATE:
    # Make sure to set this to the current date and time before using
    YEAR = 2022
    MONTH = 3
    DAY = 21
    HOUR = 16
    MINUTE = 54
    SEC = 0
    WDAY = 1  # 0 Sunday, 1 Monday, etc.
    t = time.struct_time((YEAR, MONTH, DAY, HOUR, MINUTE, SEC, WDAY, -1, -1))

    print("Setting time to:", t)  # uncomment for debugging
    rtc.datetime = t
    print()

on_always = True  # Set to False for animation only to be on when alarm rings

indicate = True

start = time.monotonic()
wait = 1

while True:
    if on_always:
        rainbow.animate()
    if time.monotonic() - start > wait:
        start = time.monotonic()
        wait = 1
        t = rtc.datetime
        bat = min(max(int(battery.cell_percent), 0), 100)

        g = int((bat / 100) * 255)
        r = int((1 - (bat / 100)) * 255)
        if bat >= 15:
            indicator.fill([r, g, 0])

        if bat < 15:
            if indicate:
                indicator.fill([0, 0, 0])
                indicate = False
            else:
                indicator.fill([r, g, 0])
                indicate = True

        print(f"Date: {days[t.tm_wday]} {t.tm_mday}/{t.tm_mon}/{t.tm_year}")
        print(f"Time: {t.tm_hour}:{t.tm_min}:{t.tm_sec}")
        print(f"Batt: {bat}%\n")

        night = sleep[t.tm_wday]
        morning = wake[t.tm_wday]

        if night:
            if night[0] == t.tm_hour and night[1] == t.tm_min:
                for i in ringtone:
                    print(i[0])
                    tone(board.A0, i[0], i[1] * (60 / BPM))
                wait = 60
                if not on_always:
                    while time.monotonic() - start < 5:
                        rainbow.animate()
                    rainbow.fill([0, 0, 0])

        if morning:
            if morning[0] == t.tm_hour and morning[1] == t.tm_min:
                for i in ringtone:
                    print(i[0])
                    tone(board.A0, i[0], i[1] * (60 / BPM))
                wait = 60
                if not on_always:
                    while time.monotonic() - start < 5:
                        rainbow.animate()
                    rainbow.fill([0, 0, 0])
