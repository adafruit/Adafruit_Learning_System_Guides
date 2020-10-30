"""
Blinking multiple LEDs at different rates.

Circuit Playground Neopixels.
"""
import time
import digitalio
import board
from adafruit_circuitplayground import cp

BLINK_MAP = {
    "RED": {
        "ON": 0.25,
        "OFF": 0.25,
        "PREV_TIME": -1,
        "INDEX": 1,
        "COLOR": (255, 0, 0)
    },
    "GREEN": {
        "ON": 0.5,
        "OFF": 0.5,
        "PREV_TIME": -1,
        "INDEX": 3,
        "COLOR": (0, 255, 0)
    },
    "BLUE": {
        "ON": 1.0,
        "OFF": 1.0,
        "PREV_TIME": -1,
        "INDEX": 6,
        "COLOR": (0, 0, 255)
    },
    "YELLOW": {
        "ON": 2.0,
        "OFF": 2.0,
        "PREV_TIME": -1,
        "INDEX": 8,
        "COLOR": (255, 255, 0)
    }
}

cp.pixels.brightness = 0.02

while True:
    # Store the current time to refer to later.
    now = time.monotonic()

    for color in BLINK_MAP.keys():

        # Is LED currently OFF?
        if cp.pixels[BLINK_MAP[color]["INDEX"]] == (0, 0, 0):
            # Is it time to turn ON?
            if now >= BLINK_MAP[color]["PREV_TIME"] + BLINK_MAP[color]["OFF"]:
                cp.pixels[BLINK_MAP[color]["INDEX"]] = BLINK_MAP[color]["COLOR"]
                BLINK_MAP[color]["PREV_TIME"] = now
        else:  # LED is ON:
            # Is it time to turn OFF?
            if now >= BLINK_MAP[color]["PREV_TIME"] + BLINK_MAP[color]["ON"]:
                cp.pixels[BLINK_MAP[color]["INDEX"]] = (0, 0, 0)
                BLINK_MAP[color]["PREV_TIME"] = now