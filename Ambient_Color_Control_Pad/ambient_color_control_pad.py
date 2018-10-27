# Ambient Color Control Pad
# NeoTrellis to select colors of NeoPixel strip
# NeoTrellis connected to Feather M4 (need the extra memory vs. M0) SCL, SDA
# NeoPixel 120 strip connected to pin D5
# NeoPixel strip powered over 5V 2A DC wall power supply
# On/off button RGB connects En to GND, LED to D13

import time
import board
from board import SCL, SDA
import busio
import neopixel
from adafruit_neotrellis.neotrellis import NeoTrellis
from digitalio import DigitalInOut, Direction

button_LED = DigitalInOut(board.D13)
button_LED.direction = Direction.OUTPUT
button_LED.value = True

pixel_pin = board.D5
num_pixels = 120

pixels = neopixel.NeoPixel(pixel_pin, num_pixels, auto_write=False)

# create the i2c object for the trellis
i2c_bus = busio.I2C(SCL, SDA)

# create the trellis object
trellis = NeoTrellis(i2c_bus)

# color definitions
OFF = (0, 0, 0)
RED = (255, 0, 0)
YELLOW = (255, 150, 0)
GREEN = (0, 255, 0)
YELLOW_GREEN = (127, 255, 0)
CYAN = (0, 255, 255)
LIGHT_BLUE = (0, 127, 255)
BLUE = (0, 0, 255)
PURPLE = (127, 0, 255)
ORANGE = (255, 80, 0)
PINK = (255, 0, 255)
ROUGE = (255, 0, 127)
WHITE = (100, 100, 100)
WHITE_WARM = (120, 100, 80)
WHITE_COOL = (80, 100, 120)
WHITE_GREEN = (80, 120, 100)


COLORS = [  # pixel colors
    RED, ORANGE, YELLOW, YELLOW_GREEN,
    GREEN, CYAN, LIGHT_BLUE, BLUE,
    PURPLE, PINK, ROUGE, WHITE,
    WHITE_WARM, WHITE_COOL, WHITE_GREEN, OFF
]

pixels.fill(COLORS[1])  # turn on the strip
pixels.show()


def dimmed_colors(color_values):
    (red_value, green_value, blue_value) = color_values
    return (red_value // 10, green_value // 10, blue_value // 10)


# this will be called when button events are received
def blink(event):
    # turn the trellis LED on when a rising edge is detected
    # do the chase for the NeoPixel strip
    if event.edge == NeoTrellis.EDGE_RISING:
        trellis.pixels[event.number] = dimmed_colors(COLORS[event.number])
        for chase_off in range(num_pixels):  # chase LEDs off
            pixels[chase_off] = (OFF)
            pixels.show()
            time.sleep(0.005)

        for chase_on in range(num_pixels - 1, -1, -1):  # chase LEDs on
            pixels[chase_on] = (COLORS[event.number])
            pixels.show()
            time.sleep(0.03)

    # turn the trellis LED back to full color when a rising edge is detected
    elif event.edge == NeoTrellis.EDGE_FALLING:
        trellis.pixels[event.number] = COLORS[event.number]


# boot up animation on trellis
trellis.pixels.brightness = 0.2
for i in range(16):
    # activate rising edge events on all keys
    trellis.activate_key(i, NeoTrellis.EDGE_RISING)
    # activate falling edge events on all keys
    trellis.activate_key(i, NeoTrellis.EDGE_FALLING)
    # set all keys to trigger the blink callback
    trellis.callbacks[i] = blink

    # light the trellis LEDs on startup
    trellis.pixels[i] = COLORS[i]
    time.sleep(.05)

print("  Ambient Color Control Pad")
print("    ---press a button to change the ambient color---")

while True:

    # call the sync function call any triggered callbacks
    trellis.sync()
    # the trellis can only be read every 17 milliseconds or so
    time.sleep(.02)
