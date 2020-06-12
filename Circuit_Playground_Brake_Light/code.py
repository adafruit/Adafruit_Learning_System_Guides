import time
import math
from adafruit_circuitplayground import cp

brightness = 0
l10 = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
l50 = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
       0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
       0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
       0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
       0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

i = 0
cp.pixels.fill((255, 0, 0))

sleep = False

while True:
    x, y, z = cp.acceleration

    # moving average n=10, not super smooth, but it substantially lowers the amount of noise
    l10.append(z)
    l10.pop(0)
    avg10 = sum(l10)/10

    # moving average n=50, very smooth
    l50.append(z)
    l50.pop(0)
    avg50 = sum(l50)/50

    # If the difference between the moving average of the last 10 points and the moving average of
    # the last 50 points is greater than 1 m/s^2, this is true
    if avg10 - avg50 > 1:
        if i > 3:
            # Detects shake. Due to the very low shake threshold, this alone would have very low
            # specificity. This was mitigated by having it only run when the acceleration
            # difference is greater than 1 m/s^2 at least 3 times in a row.
            if not cp.shake(shake_threshold=10):
                cp.pixels.brightness = 1
                start = time.monotonic()
                sleep = True
        i += 1

    # sleep variable is for short circuiting. Not really necessary, but it makes things run faster
    elif not sleep or time.monotonic() - start > 0.4:
        # Sine wave used for the color breathing effect.
        # Max brightness can be adjusted with the coefficient.
        cp.pixels.brightness = abs(math.sin(brightness)) * 0.5
        brightness += 0.05
        i = 0
        sleep = False

    time.sleep(0.02)
