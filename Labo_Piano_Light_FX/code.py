import board
from rainbowio import colorwheel
import neopixel
from analogio import AnalogIn

n_pixels = 10  # Number of pixels you are using
dc_offset = 0  # DC offset in mic signal - if unusure, leave 0
noise = 100  # Noise/hum/interference in mic signal
lvl = 10  # Current "dampened" audio level
maxbrt = 127  # Maximum brightness of the neopixels (0-255)
wheelStart = 0  # Start of the RGB spectrum we'll use
wheelEnd = 255  # End of the RGB spectrum we'll use

mic_pin = AnalogIn(board.A7)

# Set up NeoPixels and turn them all off.
strip = neopixel.NeoPixel(board.NEOPIXEL, n_pixels,
                          brightness=0.1, auto_write=False)
strip.fill(0)
strip.show()


def remapRangeSafe(value, leftMin, leftMax, rightMin, rightMax):
    # this remaps a value from original (left) range to new (right) range

    # Force the input value to within left min & max
    if value < leftMin:
        value = leftMin
    if value > leftMax:
        value = leftMax

    # Figure out how 'wide' each range is
    leftSpan = leftMax - leftMin
    rightSpan = rightMax - rightMin

    # Convert the left range into a 0-1 range (int)
    valueScaled = int(value - leftMin) / int(leftSpan)

    # Convert the 0-1 range into a value in the right range.
    return int(rightMin + (valueScaled * rightSpan))


while True:
    n = int((mic_pin.value / 65536) * 1000)  # 10-bit ADC format
    n = abs(n - 512 - dc_offset)  # Center on zero

    if n >= noise:  # Remove noise/hum
        n = n - noise

    # "Dampened" reading (else looks twitchy) - divide by 8 (2^3)
    lvl = int(((lvl * 7) + n) / 8)

    # Color pixels based on rainbow gradient
    vlvl = remapRangeSafe(lvl, 0, 255, wheelStart, wheelEnd)
    for i in range(0, len(strip)):
        strip[i] = colorwheel(vlvl)
        # Set strip brightness based oncode audio level
        brightness = remapRangeSafe(lvl, 50, 255, 0, maxbrt)
        strip.brightness = float(brightness) / 255.0
    strip.show()
