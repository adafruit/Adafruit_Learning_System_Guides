# SPDX-FileCopyrightText: Copyright (c) 2022 Dan Halbert for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2022 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
CircuitPython asyncio example for two NeoPixel rings and one button.
"""
import asyncio
import board
import neopixel
import keypad
from rainbowio import colorwheel

button_pin = board.A0  # The pin the button is connected to.
num_pixels = 16  # The number of NeoPixels on a single ring.
brightness = 0.2  # The LED brightness.

# Set up NeoPixel rings.
ring_one = neopixel.NeoPixel(board.A1, num_pixels, brightness=brightness, auto_write=False)
ring_two = neopixel.NeoPixel(board.A2, num_pixels, brightness=brightness, auto_write=False)


class AnimationControls:
    """The controls to allow you to vary the rainbow and blink animations."""
    def __init__(self):
        self.reverse = False
        self.wait = 0.0
        self.delay = 0.5


async def rainbow_cycle(controls):
    """Rainbow cycle animation on ring one."""
    while True:
        for j in range(255, -1, -1) if controls.reverse else range(0, 256, 1):
            for i in range(num_pixels):
                rc_index = (i * 256 // num_pixels) + j
                ring_one[i] = colorwheel(rc_index & 255)
            ring_one.show()
            await asyncio.sleep(controls.wait)


async def blink(controls):
    """Blink animation on ring two."""
    while True:
        ring_two.fill((0, 0, 255))
        ring_two.show()
        await asyncio.sleep(controls.delay)
        ring_two.fill((0, 0, 0))
        ring_two.show()
        await asyncio.sleep(controls.delay)
        await asyncio.sleep(controls.wait)


async def monitor_button(button, controls):
    """Monitor button that reverses rainbow direction and changes blink speed.
    Assume button is active low.
    """
    with keypad.Keys((button,), value_when_pressed=False, pull=True) as key:
        while True:
            key_event = key.events.get()
            if key_event:
                if key_event.pressed:
                    controls.reverse = True
                    controls.delay = 0.1
                elif key_event.released:
                    controls.reverse = False
                    controls.delay = 0.5
            await asyncio.sleep(0)


async def main():
    animation_controls = AnimationControls()
    button_task = asyncio.create_task(monitor_button(button_pin, animation_controls))
    animation_task = asyncio.create_task(rainbow_cycle(animation_controls))
    blink_task = asyncio.create_task(blink(animation_controls))

    # This will run forever, because no tasks ever finish.
    await asyncio.gather(button_task, animation_task, blink_task)

asyncio.run(main())
