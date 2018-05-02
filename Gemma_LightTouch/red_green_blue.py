"""Touch each pad to change red, green, and blue values on the LED"""
import time
import touchio
import adafruit_dotstar
import board

DOTSTAR = adafruit_dotstar.DotStar(board.APA102_SCK, board.APA102_MOSI, 1)
TOUCH_A0 = touchio.TouchIn(board.A0)
TOUCH_A1 = touchio.TouchIn(board.A1)
TOUCH_A2 = touchio.TouchIn(board.A2)

r = g = b = 0

while True:
    if TOUCH_A0.value:
        r = (r + 1) % 256
    if TOUCH_A1.value:
        g = (g + 1) % 256
    if TOUCH_A2.value:
        b = (b + 1) % 256

    DOTSTAR[0] = (r, g, b)
    print((r, g, b))
    time.sleep(0.01)
