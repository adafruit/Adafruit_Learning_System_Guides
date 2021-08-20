# 3D_Printed_Guardian_Sword
# https://learn.adafruit.com/breath-of-the-wild-guardian-sword-led-3d-printed

import time

import board
import neopixel

pin = board.D4  # DIGITAL IO pin for NeoPixel OUTPUT from GEMMA
pixel_count = 93  # number of neopixels
delayval = .01  # 10 ms delay

APIXELS = 14  # number of first orange pixels
BPIXELS = 84  # number of blue pixels
CPIXELS = 93  # second orange pixels

# initialize neopixels
pixels = neopixel.NeoPixel(pin, pixel_count, brightness=1, auto_write=False)

while True:

    # For the first 14 pixels, make them orange,
    # starting from pixel number 0.
    for i in range(0, APIXELS):
        # Set Pixels to Orange Color
        pixels[i] = (255, 50, 0)
        # This sends the updated pixel color to the hardware.
        pixels.write()
        # Delay for a period of time (in milliseconds).
        time.sleep(delayval)

    # Fill up 84 pixels with blue,
    # starting with pixel number 14.
    for i in range(APIXELS, BPIXELS):
        # Set Pixels to Orange Color
        pixels[i] = (0, 250, 200)
        # This sends the updated pixel color to the hardware.
        pixels.write()
        # Delay for a period of time (in milliseconds).
        time.sleep(delayval)

    # Fill up 9 pixels with orange,
    # starting from pixel number 84.
    for i in range(BPIXELS, CPIXELS):
        # Set Pixels to Orange Color
        pixels[i] = (250, 50, 0)
        # This sends the updated pixel color to the hardware.
        pixels.write()
        # Delay for a period of time (in milliseconds).
        time.sleep(delayval)
