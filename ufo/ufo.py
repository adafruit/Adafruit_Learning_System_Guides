"""
UFO Flying Saucer with Circuit Playground Express
https://learn.adafruit.com/ufo-circuit-playground-express/
Plays UFO lights and sounds if the board is upside down only,
Tilt to change light color, cycle speed, tone pitch
"""

import time

from adafruit_circuitplayground.express import cpx

def simple_circle(wait, red, green, blue):
    """timing, color values per channel"""
    baseFreq = int(20 + (green * 0.3))  # tone value derived from rotation

    for i in range(10):
        cpx.pixels[i] = ((0, 0, 0))
        cpx.start_tone(baseFreq + i)  # increasing pitch sweep
        time.sleep(wait)

    for i in range(10):
        cpx.pixels[i] = ((red, green, blue))
        time.sleep(wait)


# Main loop gets x, y and z axis acceleration, prints the values, and turns on
# lights if the UFO is upside down, plays tones
while True:
    R = 0
    G = 0
    B = 0
    x, y, z = cpx.acceleration  # read the accelerometer values

    R = 10 * (R + abs(int(x)))  # scale up the accel values into color values
    G = 10 * (G + abs(int(y)))
    B = 10 * (B + abs(int(z)))

    # check for upside down state on z axis
    if z < 0:  # any negative number on z axis means it's upside down enough
        speed = (0.01 * (B * 0.025))
        simple_circle(speed, R, G, B)  # speed based on tilt, .01 is good start

    else:  # right side up means no colors or sound!
        cpx.pixels.fill((0, 0, 0))
        cpx.stop_tone()
