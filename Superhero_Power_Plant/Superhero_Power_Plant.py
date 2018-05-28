import board
import neopixel

try:
    import urandom as random  # for v1.0 API support
except ImportError:
    import random

num_pix = 17  # Number of NeoPixels
pix_pin = board.D1  # Pin where NeoPixels are connected
strip = neopixel.NeoPixel(pix_pin, num_pix)

min_alpha = 0.1  # Minimum brightness
max_alpha = 0.4  # Maximum brightness
alpha = (min_alpha + max_alpha) / 2  # Start in middle
alpha_delta = 0.01  # Amount to change brightness each time through loop
alpha_up = True  # If True, brightness increasing, else decreasing

strip.fill([0, 0, 255])  # Fill blue, or change to R,G,B of your liking

while True:  # Loop forever...
    if random.randint(1, 5) == 5:  # 1-in-5 random chance
        alpha_up = not alpha_up  # of reversing direction
    if alpha_up:  # Increasing brightness?
        alpha += alpha_delta  # Add some amount
        if alpha >= max_alpha:  # At or above max?
            alpha = max_alpha  # Limit to max
            alpha_up = False  # and switch direction
    else:  # Else decreasing brightness
        alpha -= alpha_delta  # Subtract some amount
        if alpha <= min_alpha:  # At or below min?
            alpha = min_alpha  # Limit to min
            alpha_up = True  # and switch direction

    strip.brightness = alpha  # Set brightness to 0.0 to 1.0
    strip.write()  # and issue data to LED strip
