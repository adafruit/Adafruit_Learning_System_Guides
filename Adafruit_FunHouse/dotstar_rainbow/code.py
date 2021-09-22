"""CircuitPython DotStar rainbow example for FunHouse"""
import time
import board
import adafruit_dotstar
from rainbowio import colorwheel

dots = adafruit_dotstar.DotStar(board.DOTSTAR_CLOCK, board.DOTSTAR_DATA, 5, auto_write=False)
dots.brightness = 0.3


def rainbow(delay):
    for color_value in range(255):
        for led in range(5):
            pixel_index = (led * 256 // 5) + color_value
            dots[led] = colorwheel(pixel_index & 255)
        dots.show()
        time.sleep(delay)


while True:
    rainbow(0.01)
