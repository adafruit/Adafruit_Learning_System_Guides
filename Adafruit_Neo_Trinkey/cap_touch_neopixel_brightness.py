"""CircuitPython Capacitive Touch NeoPixel Brightness Control Exmaple"""
import time
import board
import touchio
import neopixel
from _pixelbuf import colorwheel

touch1 = touchio.TouchIn(board.TOUCH1)
touch2 = touchio.TouchIn(board.TOUCH2)

pixels = neopixel.NeoPixel(board.NEOPIXEL, 4, auto_write=False)


def rainbow(color_index):
    for led in range(4):
        pixel_index = (led * 256 // 4) + color_index
        pixels[led] = colorwheel(pixel_index & 255)
    pixels.show()


touched = time.monotonic()
color = 0
while True:
    color = color + 1
    if color > 255:
        color = 0

    rainbow(color)

    if time.monotonic() - touched < 0.15:
        continue
    if touch1.value:
        # Touch pad 1 to increase the brightness.
        pixels.brightness += 0.05
        pixels.show()
        touched = time.monotonic()
    elif touch2.value:
        # Touch pad 2 to decrease the brightness.
        pixels.brightness -= 0.05
        pixels.show()
        touched = time.monotonic()
