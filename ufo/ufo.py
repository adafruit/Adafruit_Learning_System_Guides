#  UFO Circuit Playground Express
#  Plays UFO lights and sounds if the board is upside down only!

from adafruit_circuitplayground.express import cpx
import neopixel
import board
import time


# The two files assigned to buttons A & B
audiofiles = ["ufo.wav", "ufoUp.wav"]

pixels = neopixel.NeoPixel(board.NEOPIXEL, 10, brightness=.8)

def simpleCircle(wait, R, G, B): # timing, color values per channel

    for i in range(10):
        pixels[i] = ((0, 0, 0))
        time.sleep(wait)

    for i in range(10):
        pixels[i] = ((R, G, B))
        time.sleep(wait)

# Main loop gets x, y and z axis acceleration, prints the values, and turns on
# lights if the UFO is upside down, plays music

while True:
    R = 0
    G = 0
    B = 0
    x, y, z = cpx.acceleration # read the accelerometer values
    #  print(x, y, z)
    R = 10 * (R + abs(int(x))) # scale up the accel values into color values
    G = 10 * (G + abs(int(y)))
    B = 10 * (B + abs(int(z)))
    #  print(R, G, B)

    # check for upside down state on z axis
    if z < 0: # any negative number on z axis means it's upside down enough
        simpleCircle(.03, R, G, B)
        cpx.play_file(audiofiles[0])

    else: # right side up, no colors or sound!
        pixels.fill((0, 0, 0))
