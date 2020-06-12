import time
import math
from adafruit_circuitplayground import cp

brightness = 0

# List that holds the last 10 z-axis acceleration values read from the accelerometer.
# Used for the n=10 moving average
last10 = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

# List that holds the last 50 z-axis acceleration values read from the accelerometer.
# Used for the n=50 moving average
last50 = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
          0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
          0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
          0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
          0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

consecutive_triggers = 0
cp.pixels.fill((255, 0, 0))

light_on = False

while True:
    x, y, z = cp.acceleration

    # moving average n=10, not super smooth, but it substantially lowers the amount of noise
    last10.append(z)
    last10.pop(0)
    avg10 = sum(last10)/10

    # moving average n=50, very smooth
    last50.append(z)
    last50.pop(0)
    avg50 = sum(last50)/50

    # If the difference between the moving average of the last 10 points and the moving average of
    # the last 50 points is greater than 1 m/s^2, this is true
    if avg10 - avg50 > 1:
        if consecutive_triggers > 3: # Is true when avg10-avg50 > 1m/s^2 at least 3 times in a row
            # Detects shake. Due to the very low shake threshold, this alone would have very low
            # specificity. This was mitigated by having it only run when the acceleration
            # difference is greater than 1 m/s^2 at least 3 times in a row.
            if not cp.shake(shake_threshold=10):
                # Set brightness to max, timestamp when it was set to max, and set light_on to true
                cp.pixels.brightness = 1
                start = time.monotonic()
                light_on = True
        consecutive_triggers += 1 # increase it whether or not the light is turned on

    # light_on variable is for short circuiting. Not really necessary, just makes things run faster
    elif not light_on or time.monotonic() - start > 0.4:
        # Sine wave used for the color breathing effect.
        # Max brightness can be adjusted with the coefficient.
        cp.pixels.brightness = abs(math.sin(brightness)) * 0.5
        brightness += 0.05
        consecutive_triggers = 0
        light_on = False

    time.sleep(0.02)
