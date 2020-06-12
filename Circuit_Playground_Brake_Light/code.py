# pylint:disable=invalid-name,import-error,missing-module-docstring

# Great pdf on moving average filters:
# https://www.analog.com/media/en/technical-documentation/dsp-book/dsp_book_Ch15.pdf
import time
import math
from adafruit_circuitplayground import cp

brightness = 0
l = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
l1 = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
      0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
      0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
      0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
      0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

i = 0
sleep = False
decel = 0
while True:
    x, y, z = cp.acceleration

    # moving average n=10, not super smooth, but not terrible either
    l.append(z)
    l.pop(0)
    avg = sum(l)/10

    # moving average n=50, very smooth
    l1.append(z)
    l1.pop(0)
    avg1 = sum(l1)/50

    if avg - avg1 > 1:
        if i > 3:
            if not cp.shake(shake_threshold=10):
                cp.pixels.fill((0, 0, 255))
                cp.pixels.brightness = 0.25
                start = time.monotonic()
                sleep = True
        i += 1

    # sleep variable is for short circuiting
    elif not sleep or time.monotonic() - start > 0.4:
        cp.pixels.fill((255, 0, 0))
        cp.pixels.brightness = abs(math.sin(brightness)) * 0.25
        brightness += 0.05
        i = 0
        sleep = False
        decel = 0 

    time.sleep(0.02)
