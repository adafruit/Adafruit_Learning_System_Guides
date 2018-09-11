import time
import board
from analogio import AnalogIn
import neopixel

NUMPIXELS = 10  # Circuit Playground Express has 10 pixels
pixels = neopixel.NeoPixel(board.NEOPIXEL, NUMPIXELS, auto_write=False)  # CPX NeoPixels
potentiometer = AnalogIn(board.A1)  # potentiometer connected to A1, power & ground

def show_value(val):            # Show value 0-9 on CPX NeoPixels
    for i in range(val):
        pixels[i] = (50, 0, 0)  # Red
    for i in range(val, NUMPIXELS):
        pixels[i] = (0, 0, 0)
    pixels.show()
    return

while True:

    show_value(int(potentiometer.value / 65520 * NUMPIXELS))  # Show on NeoPixels
    print((potentiometer.value,))                             # Print value

    time.sleep(0.25)                   # Wait a bit before checking all again
