import time
import board
from analogio import AnalogIn
import neopixel

pixels = neopixel.NeoPixel(board.NEOPIXEL, 10, auto_write=False)  # CPX NeoPixels
potentiometer = AnalogIn(board.A1)  # potentiometer connected to A1, power & ground

def show_value(val):         # Show value 0-9 on CPX NeoPixels
    for i in range(val):
        pixels[i] = (10*(i+1), 0, 0)
    for i in range(val, 10):
        pixels[i] = (0, 0, 0)
    pixels.show()
    return

while True:
    
    show_value(int(potentiometer.value / 6500))  # Show on NeoPixels
    print((potentiometer.value,))                # Print value

    time.sleep(0.25)                   # Wait a bit before checking all again
