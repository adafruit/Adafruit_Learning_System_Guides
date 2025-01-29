# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-FileCopyrightText: 2025 Tim Cocks for Adafruit Industries
# SPDX-License-Identifier: MIT
"""CircuitPython Adafruit Sparkle Motion IR remote control NeoPixels example."""
import time

import board
import pulseio
from rainbowio import colorwheel

import neopixel
import adafruit_irremote

pulsein = pulseio.PulseIn(board.IR, maxlen=120, idle_state=True)
decoder = adafruit_irremote.NonblockingGenericDecode(pulsein)

IR_CODE_UP = (0, 253, 160, 95)
IR_CODE_DOWN = (0, 253, 176, 79)

IR_CODE_RIGHT = (0, 253, 80, 175)
IR_CODE_LEFT = (0, 253, 16, 239)

t0 = next_heartbeat = time.monotonic()

pixel = neopixel.NeoPixel(board.D21, 8)

brightness = 1
pixel.brightness = brightness / 10

color_number = 160
pixel.fill(colorwheel(color_number))
while True:
    for message in decoder.read():
        print(f"t={time.monotonic() - t0:.3} New IR Message")
        if isinstance(message, adafruit_irremote.IRMessage):
            if message.code == IR_CODE_UP:
                brightness = min(brightness + 1, 10)
            elif message.code == IR_CODE_DOWN:
                brightness = max(brightness - 1, 0)
            elif message.code == IR_CODE_RIGHT:
                color_number = (color_number + 32) % 256
            elif message.code == IR_CODE_LEFT:
                color_number = (color_number - 32) % 256

            pixel.brightness = brightness / 10
            pixel.fill(colorwheel(color_number))

            print("Decoded:", message.code)
            print("Brightness: ", brightness/10, " Color: ", hex(colorwheel(color_number)))
        elif isinstance(message, adafruit_irremote.NECRepeatIRMessage):
            print("NEC repeat!")
        elif isinstance(message, adafruit_irremote.UnparseableIRMessage):
            print("Failed to decode", message.reason)
        print("----------------------------")
