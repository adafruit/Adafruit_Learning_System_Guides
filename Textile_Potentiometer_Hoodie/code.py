import analogio
import board
from rainbowio import colorwheel
import neopixel

# Initialize input/output pins
sensor_pin = board.A1  # input pin for the potentiometer
sensor = analogio.AnalogIn(sensor_pin)

pix_pin = board.D1  # pin where NeoPixels are connected
num_pix = 8  # number of neopixels
strip = neopixel.NeoPixel(pix_pin, num_pix, brightness=.15, auto_write=False)

color_value = 0
sensor_value = 0


def remap_range(value, left_min, left_max, right_min, right_max):
    # this remaps a value from original (left) range to new (right) range
    # Figure out how 'wide' each range is
    left_span = left_max - left_min
    right_span = right_max - right_min

    # Convert the left range into a 0-1 range (int)
    valueScaled = int(value - left_min) / int(left_span)

    # Convert the 0-1 range into a value in the right range.
    return int(right_min + (valueScaled * right_span))


# Loop forever...
while True:

    # remap the potentiometer analog sensor values from 0-65535 to RGB 0-255
    color_value = remap_range(sensor.value, 0, 65535, 0, 255)

    for i in range(len(strip)):
        strip[i] = colorwheel(color_value)
    strip.write()
