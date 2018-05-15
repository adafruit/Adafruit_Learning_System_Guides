import board
import neopixel

try:
    import urandom as random  # for v1.0 API support
except ImportError:
    import random

numpix = 17  # Number of NeoPixels
pixpin = board.D1  # Pin where NeoPixels are connected
strip = neopixel.NeoPixel(pixpin, numpix)

minAlpha = 0.1  # Minimum brightness
maxAlpha = 0.4  # Maximum brightness
alpha = (minAlpha + maxAlpha) / 2  # Start in middle
alphaDelta = 0.008  # Amount to change brightness each time through loop
alphaUp = True  # If True, brightness increasing, else decreasing

strip.fill([255, 0, 0])  # Fill red, or change to R,G,B of your liking

while True:  # Loop forever...
    if random.randint(1, 5) == 5:  # 1-in-5 random chance
        alphaUp = not alphaUp  # of reversing direction
    if alphaUp:  # Increasing brightness?
        alpha += alphaDelta  # Add some amount
        if alpha >= maxAlpha:  # At or above max?
            alpha = maxAlpha  # Limit to max
            alphaUp = False  # and switch direction
    else:  # Else decreasing brightness
        alpha -= alphaDelta  # Subtract some amount
        if alpha <= minAlpha:  # At or below min?
            alpha = minAlpha  # Limit to min
            alphaUp = True  # and switch direction

    strip.brightness = alpha  # Set brightness to 0.0 to 1.0
    strip.write()  # and issue data to LED strip
