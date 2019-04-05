"""Touch each pad to change red, green, and blue values on the LED"""
import time

import adafruit_dotstar
import board
import touchio

led = adafruit_dotstar.DotStar(board.APA102_SCK, board.APA102_MOSI, 1)
touch_A0 = touchio.TouchIn(board.A0)
touch_A1 = touchio.TouchIn(board.A1)
touch_A2 = touchio.TouchIn(board.A2)

r = g = b = 0

while True:
    if touch_A0.value:
        r = (r + 1) % 256
    if touch_A1.value:
        g = (g + 1) % 256
    if touch_A2.value:
        b = (b + 1) % 256

    led[0] = (r, g, b)
    print((r, g, b))
    time.sleep(0.01)
