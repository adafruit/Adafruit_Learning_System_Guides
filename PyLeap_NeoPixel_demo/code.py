import time
import board
import neopixel

pixels = neopixel.NeoPixel(board.NEOPIXEL, 10, brightness=0.2, auto_write=False)

while True:
    for j in range(255):
        for i in range(len(pixels)):
            rc_index = (i * 256 // len(pixels)) + j
            pixels[i] = neopixel._pixelbuf.wheel(rc_index)
        pixels.show()
