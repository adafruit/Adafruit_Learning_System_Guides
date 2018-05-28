import time

import adafruit_dotstar
import board

# For Trinket M0, Gemma M0, and ItsyBitsy M0 Express
led = adafruit_dotstar.DotStar(board.APA102_SCK, board.APA102_MOSI, 1)


# For Feather M0 Express, Metro M0 Express, and Circuit Playground Express
# led = neopixel.NeoPixel(board.NEOPIXEL, 1)


def wheel(pos):
    # Input a value 0 to 255 to get a color value.
    # The colours are a transition r - g - b - back to r.
    if pos < 0 or pos > 255:
        return 0, 0, 0
    if pos < 85:
        return int(255 - pos * 3), int(pos * 3), 0
    if pos < 170:
        pos -= 85
        return 0, int(255 - pos * 3), int(pos * 3)
    pos -= 170
    return int(pos * 3), 0, int(255 - (pos * 3))


led.brightness = 0.3

i = 0
while True:
    i = (i + 1) % 256  # run from 0 to 255
    led.fill(wheel(i))
    time.sleep(0.1)
