import time
import board
import neopixel

# On CircuitPlayground Express, and boards with built in status NeoPixel -> board.NEOPIXEL
# Otherwise choose an open pin connected to the Data In of the NeoPixel strip, i.e. board.D1
pixel_pin = board.NEOPIXEL

# On a Raspberry pi, use this instead, not all pins are supported
# pixel_pin = board.D18

# The number of NeoPixels
num_pixels = 10

# Increase or decrease between 0 and 1 to increase or decrease the brightness of the LEDs
brightness = 0.6

# The order of the pixel colors - RGB or GRB. Some NeoPixels have red and green reversed!
# For RGBW NeoPixels, simply change the ORDER to RGBW or GRBW.
ORDER = neopixel.GRB

pixels = neopixel.NeoPixel(pixel_pin, num_pixels, brightness=brightness, auto_write=False,
                           pixel_order=ORDER)


def wheel(pos):
    # Input a value 0 to 255 to get a color value.
    # The colours are a transition r - g - b - back to r.
    if pos < 0 or pos > 255:
        r = g = b = 0
    elif pos < 85:
        r = int(pos * 3)
        g = int(255 - pos * 3)
        b = 0
    elif pos < 170:
        pos -= 85
        r = int(255 - pos * 3)
        g = 0
        b = int(pos * 3)
    else:
        pos -= 170
        r = 0
        g = int(pos * 3)
        b = int(255 - pos * 3)
    return (r, g, b) if ORDER in (neopixel.RGB, neopixel.GRB) else (r, g, b, 0)


def rainbow_swirl(wait):
    for j in range(255):
        for i in range(num_pixels):
            pixel_index = (i * 256 // num_pixels) + j
            pixels[i] = wheel(pixel_index & 255)
        pixels.show()
        time.sleep(wait)


def rainbow_fill(wait):
    for j in range(255):
        for i in range(num_pixels):
            pixel_index = int(i + j)
            pixels[i] = wheel(pixel_index & 255)
        pixels.show()
        time.sleep(wait)


def christmas_flash(duration):
    pixels.fill((255, 0, 0))
    pixels.show()
    time.sleep(duration)
    pixels.fill((255, 255, 255))
    pixels.show()
    time.sleep(duration)


while True:
    for _ in range(5):
        christmas_flash(0.5)

    for _ in range(5):
        christmas_flash(0.1)

    pixels.fill((255, 0, 0))
    pixels.show()
    time.sleep(1)

    rainbow_fill(0.001)  # Increase the number to slow down the rainbow

    pixels.fill((0, 0, 0))
    pixels.show()
    time.sleep(1)
    rainbow_swirl(0.001)  # Increase the number to slow down the rainbow
