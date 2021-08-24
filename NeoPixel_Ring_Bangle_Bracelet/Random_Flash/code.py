import board
import neopixel

try:
    import urandom as random
except ImportError:
    import random

numpix = 64  # Number of NeoPixels
pixpin = board.D1  # Pin where NeoPixels are connected
strip = neopixel.NeoPixel(pixpin, numpix, brightness=0.0)
colors = [
    [232, 100, 255],  # Purple
    [200, 200, 20],  # Yellow
    [30, 200, 200],  # Blue
]

while True:  # Loop forever...
    c = random.randint(0, len(colors) - 1)  # Choose random color index
    j = random.randint(0, numpix - 1)  # Choose random pixel
    strip[j] = colors[c]  # Set pixel to color
    for i in range(1, 5):
        strip.brightness = i / 5.0  # Ramp up brightness
        strip.write()
    for i in range(5, 0, -1):
        strip.brightness = i / 5.0  # Ramp down brightness
        strip.write()
    strip[j] = [0, 0, 0]  # Set pixel to 'off'
