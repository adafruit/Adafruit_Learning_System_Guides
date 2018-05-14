# Trinket IO demo - captouch to dotstar

import time

import board
import busio
import touchio

touch0 = touchio.TouchIn(board.D1)
touch1 = touchio.TouchIn(board.D3)
touch2 = touchio.TouchIn(board.D4)

dotstar = busio.SPI(board.APA102_SCK, board.APA102_MOSI)

r = g = b = 0


def setPixel(red, green, blue):
    if not dotstar.try_lock():
        return
    print("setting pixel to: %d %d %d" % (red, green, blue))

    data = bytearray([0x00, 0x00, 0x00, 0x00,
                      0xff, blue, green, red,
                      0xff, 0xff, 0xff, 0xff])
    dotstar.write(data)
    dotstar.unlock()
    time.sleep(0.01)


while True:
    if touch0.value:
        r = (r + 1) % 256
    if touch1.value:
        g = (g + 1) % 256
    if touch2.value:
        b = (b + 1) % 256

    setPixel(r, g, b)
