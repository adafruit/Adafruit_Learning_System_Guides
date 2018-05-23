import time
from adafruit_circuitplayground.express import cpx
import simpleio

cpx.pixels.auto_write = False
cpx.pixels.brightness = 0.3

while True:
    # light value remaped to pixel position
    peak = simpleio.map_range(cpx.light, 0, 320, 0, 10)
    print(cpx.light)
    print(int(peak))

    for i in range(0, 10, 1):
        if i <= peak:
            cpx.pixels[i] = (0, 255, 255)
        else:
            cpx.pixels[i] = (0, 0, 0)
    cpx.pixels.show()
    time.sleep(0.05)
