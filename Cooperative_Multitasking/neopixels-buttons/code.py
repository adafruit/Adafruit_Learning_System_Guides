import asyncio

import board
import keypad
import neopixel
from rainbowio import colorwheel

pixel_pin = board.A0
num_pixels = 24

pixels = neopixel.NeoPixel(pixel_pin, num_pixels, brightness=0.03, auto_write=False)


class Controls:
    def __init__(self):
        self.reverse = False
        self.wait = 0.0


async def rainbow_cycle(controls):
    while True:
        # Increment by 2 instead of 1 to speed the cycle up a bit.
        for j in range(255, -1, -2) if controls.reverse else range(0, 256, 2):
            for i in range(num_pixels):
                rc_index = (i * 256 // num_pixels) + j
                pixels[i] = colorwheel(rc_index & 255)
            pixels.show()
            await asyncio.sleep(controls.wait)


async def monitor_buttons(reverse_pin, slower_pin, faster_pin, controls):
    """Monitor buttons that reverse direction and change animation speed.
    Assume buttons are active low.
    """
    with keypad.Keys(
        (reverse_pin, slower_pin, faster_pin), value_when_pressed=False, pull=True
    ) as keys:
        while True:
            key_event = keys.events.get()
            if key_event and key_event.pressed:
                key_number = key_event.key_number
                if key_number == 0:
                    controls.reverse = not controls.reverse
                elif key_number == 1:
                    # Lengthen the interval.
                    controls.wait = controls.wait + 0.001
                elif key_number == 2:
                    # Shorten the interval.
                    controls.wait = max(0.0, controls.wait - 0.001)
            # Let another task run.
            await asyncio.sleep(0)


async def main():
    controls = Controls()

    buttons_task = asyncio.create_task(
        monitor_buttons(board.A1, board.A2, board.A3, controls)
    )
    animation_task = asyncio.create_task(rainbow_cycle(controls))

    # This will run forever, because no tasks ever finish.
    await asyncio.gather(buttons_task, animation_task)


asyncio.run(main())
