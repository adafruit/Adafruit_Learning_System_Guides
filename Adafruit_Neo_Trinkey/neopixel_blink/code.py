"""CircuitPython NeoPixel Blink example - blinking the built-in NeoPixels."""
import time
import board
import neopixel

pixels = neopixel.NeoPixel(board.NEOPIXEL, 4)

while True:
    pixels.fill((255, 0, 0))
    time.sleep(0.5)
    pixels.fill((0, 0, 0))
    time.sleep(0.5)
