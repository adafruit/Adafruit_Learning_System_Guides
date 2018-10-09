import time
import random
import board
from board import SCL, SDA
import digitalio
import busio
from adafruit_neotrellis.neotrellis import NeoTrellis

# create the i2c object for the trellis
i2c_bus = busio.I2C(SCL, SDA)

# create the trellis
trellis = NeoTrellis(i2c_bus)

button_pin = board.D6

button = digitalio.DigitalInOut(button_pin)
button.direction = digitalio.Direction.INPUT
button.pull = digitalio.Pull.UP

# some color definitions
OFF = (0, 0, 0)
RED = (25, 0, 0)
YELLOW = (25, 15, 0)
GREEN = (0, 25, 0)
CYAN = (0, 25, 25)
BLUE = (0, 0, 25)
PURPLE = (18, 0, 25)
WHITE = (127, 127, 127)

PUSH_COLOR = GREEN
ANIM_COLOR = WHITE

COLORS = [RED, YELLOW, GREEN, CYAN, BLUE, PURPLE]


# this will be called when button events are received
def blink(event):
    # turn the LED on when a rising edge is detected
    if event.edge == NeoTrellis.EDGE_RISING:
        if button.value:
            trellis.pixels[event.number] = WHITE
        else:
            for j in range(16):
                trellis.pixels[j] = ANIM_COLOR
                time.sleep(.05)
                trellis.pixels[j] = OFF
                time.sleep(.05)

    # turn the LED off when a rising edge is detected
    elif event.edge == NeoTrellis.EDGE_FALLING:
        trellis.pixels[event.number] = random.choice([RED, YELLOW, GREEN, CYAN, BLUE, PURPLE])

for i in range(16):
    # activate rising edge events on all keys
    trellis.activate_key(i, NeoTrellis.EDGE_RISING)
    # activate falling edge events on all keys
    trellis.activate_key(i, NeoTrellis.EDGE_FALLING)
    # set all keys to trigger the blink callback
    trellis.callbacks[i] = blink

    # cycle the LEDs on startup
    trellis.pixels[i] = ANIM_COLOR
    time.sleep(.05)

for i in range(16):
    trellis.pixels[i] = OFF
    time.sleep(.05)

while True:
    # call the sync function call any triggered callbacks
    trellis.sync()
    # the trellis can only be read every 17 millisecons or so
    time.sleep(.02)
