"""
This example script shows how to blink multiple LEDs at different
rates simultaneously without each affecting the others.
"""

import time
import board
import digitalio

BLINK_LIST = [
    {
        "ON": 0.25,
        "OFF": 0.25,
        "PREV_TIME": -1,
        "PIN": board.D5,
    },
    {
        "ON": 0.5,
        "OFF": 0.5,
        "PREV_TIME": -1,
        "PIN": board.D6,
    },
    {
        "ON": 1.0,
        "OFF": 1.0,
        "PREV_TIME": -1,
        "PIN": board.D9,
    },
    {
        "ON": 2.0,
        "OFF": 2.0,
        "PREV_TIME": -1,
        "PIN": board.D10,
    }
]

for led in BLINK_LIST:
    led["PIN"] = digitalio.DigitalInOut(led["PIN"])
    led["PIN"].direction = digitalio.Direction.OUTPUT

while True:
    # Store the current time to refer to later.
    now = time.monotonic()

    for led in BLINK_LIST:
        if led["PIN"].value is False:
            if now >= led["PREV_TIME"] + led["OFF"]:
                led["PREV_TIME"] = now
                led["PIN"].value = True
        if led["PIN"].value is True:
            if now >= led["PREV_TIME"] + led["ON"]:
                led["PREV_TIME"] = now
                led["PIN"].value = False
