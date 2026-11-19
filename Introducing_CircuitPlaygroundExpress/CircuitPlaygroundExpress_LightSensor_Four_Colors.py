"""Maps light level to multiple circles of colors.

The light intensity level is divided into four bands.
Dim light creates a growing circle of blue lights,
followed by circles of green, yellow, and then red lights
for the highest intensity."""

import time
import board
import neopixel
from analogio import AnalogIn

NUM_LEDS = 10

pixels = neopixel.NeoPixel(board.NEOPIXEL, NUM_LEDS, auto_write=0, brightness=.3)
pixels.fill((0, 0, 0))
pixels.show()

sensor = AnalogIn(board.LIGHT)
hues = (
    (  0,   0, 255),  # Blue
    (  0, 255,   0),  # Green
    (255, 255,   0),  # Yellow
    (255,   0,   0),  # Red
)

while True:
    normalized_brightness = sensor.value / 65535
    hues_position = normalized_brightness * len(hues)
    hue_idx = int(hues_position)
    hue_fill_fraction = hues_position - hue_idx

    pixels.fill((0, 0, 0))

    for led_idx in range(int(hue_fill_fraction * NUM_LEDS) + 1):
        pixels[9 - led_idx] = hues[hue_idx]

    pixels.show()

    time.sleep(0.01)
