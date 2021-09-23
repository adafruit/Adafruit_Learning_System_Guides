import time
import adafruit_dotstar
from rainbowio import colorwheel
import board
import touchio

pixel = adafruit_dotstar.DotStar(board.APA102_SCK, board.APA102_MOSI, 1, brightness=.1)

touch = touchio.TouchIn(board.D1)

hue = 0
while True:
    hue = hue + touch.value * 3
    if hue > 255:  # Wrap back around to red
        hue = hue - 255
    pixel[0] = colorwheel(hue)
    time.sleep(.05)
