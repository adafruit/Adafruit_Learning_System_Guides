# SPDX-FileCopyrightText: Copyright (c) 2022 Dan Halbert for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2022 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
CircuitPython asyncio example for two NeoPixel rings and one button.
REMOVE THIS LINE AND THE REST OF THIS DOCSTRING BEFORE SUBMITTING TO LEARN
THERE ARE TWO POSSIBLE THINGS IN THE CODE TO UPDATE.

One: Update BUTTON to the pin that matches the pin to which the button is connected.

For example, on the QT Py RP2040, you would leave it as BUTTON to use the built-in Boot button.
On the FunHouse, you would update BUTTON to BUTTON_UP to use the built-in up button.
On the Feather M4 Express, you would wire the external button to A0, and update BUTTON to A0.

Two: THIS IS ONLY NECESSARY IF THE BUILT-IN BUTTON IS ACTIVE HIGH. For example the built-in
buttons on the Circuit Playground Bluefruit and the MagTag are active high.
If your button is ACTIVE HIGH, under "async def monitor_button(button, animation_controls)",
update the following line of code:
    with keypad.Keys((button,), value_when_pressed=False, pull=True) as key:
To the following:
    with keypad.Keys((button,), value_when_pressed=True, pull=True) as key:
"""
import asyncio
import board
import neopixel
import keypad
from rainbowio import colorwheel

button_pin = board.BUTTON  # The pin the button is connected to.
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


async def rainbow_cycle(animation_controls):
    """Rainbow cycle animation on ring one."""
    while True:
        for j in range(255, -1, -1) if animation_controls.reverse else range(0, 256, 1):
            for i in range(num_pixels):
                rc_index = (i * 256 // num_pixels) + j
                ring_one[i] = colorwheel(rc_index & 255)
            ring_one.show()
            await asyncio.sleep(animation_controls.wait)


async def blink(animation_controls):
    """Blink animation on ring two."""
    while True:
        ring_two[:] = [(0, 0, abs(ring_two[0][2] - 255))] * num_pixels
        await asyncio.sleep(animation_controls.delay)
        ring_two.show()
        await asyncio.sleep(animation_controls.wait)


async def monitor_button(button, animation_controls):
    """Monitor button that reverses rainbow direction and changes blink speed.
    Assume button is active low.
    """
    with keypad.Keys((button,), value_when_pressed=False, pull=True) as key:
        while True:
            key_event = key.events.get()
            if key_event:
                if key_event.pressed:
                    animation_controls.reverse = True
                    animation_controls.delay = 0.1
                elif key_event.released:
                    animation_controls.reverse = False
                    animation_controls.delay = 0.5
            # Let another task run.
            await asyncio.sleep(0)


async def main():
    animation_controls = AnimationControls()
    buttons_task = asyncio.create_task(monitor_button(button_pin, animation_controls))
    animation_task = asyncio.create_task(rainbow_cycle(animation_controls))
    blink_task = asyncio.create_task(blink(animation_controls))

    # This will run forever, because no tasks ever finish.
    await asyncio.gather(buttons_task, animation_task, blink_task)

asyncio.run(main())
