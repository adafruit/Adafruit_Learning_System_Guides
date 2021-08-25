"""Simple rainbow example for 30-pixel NeoPixel strip"""
import digitalio
import board
import neopixel

NUM_PIXELS = 30  # NeoPixel strip length (in pixels)

enable = digitalio.DigitalInOut(board.D10)
enable.direction = digitalio.Direction.OUTPUT
enable.value = True

strip = neopixel.NeoPixel(board.D5, NUM_PIXELS, brightness=1)


def wheel(pos):
    # Input a value 0 to 255 to get a color value.
    # The colours are a transition r - g - b - back to r.
    if pos < 0 or pos > 255:
        return (0, 0, 0)
    if pos < 85:
        return (255 - pos * 3, pos * 3, 0)
    if pos < 170:
        pos -= 85
        return (0, 255 - pos * 3, pos * 3)
    pos -= 170
    return (pos * 3, 0, 255 - pos * 3)


while True:
    for i in range(255):
        strip.fill((wheel(i)))
