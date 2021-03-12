import time
import adafruit_dotstar
import adafruit_pypixelbuf
import board
import touchio

pixel = adafruit_dotstar.DotStar(board.APA102_SCK, board.APA102_MOSI, 1, brightness=.1)

touch = touchio.TouchIn(board.D1)

hue = 0
while True:
    hue = hue + touch.value * 3
    if hue > 255:  # Wrap back around to red
        hue = hue - 255
    pixel[0] = adafruit_pypixelbuf.colorwheel(hue)
    time.sleep(.05)
