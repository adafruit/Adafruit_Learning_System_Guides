import time

from adafruit_circuitplayground import cp

# Red, green, blue, and simple mixes of 2 or 3.
# Add your own choices here.
COLORS = (
    (0, 255, 0),
    (0, 0, 255),
    (255, 0, 0),
    (0, 255, 255),
    (255, 255, 0),
    (255, 0, 255),
    (255, 255, 255),
)

# Light level at which to turn off the nightlight.
# A typical level might be in the 20's or 30's. You'll need to experiment
# If you don't want the nightlight to turn off at all, set this to a large number like 9999.
TURN_OFF = 9999

# The NeoPixels are really bright, so limit how bright they can get with MAX_BRIGHTNESS.
# Increase its value if the nightlight is not bright enough, or decrease if it's
# too bright even at the lowest setting.
# MAX_BRIGHTNESS should be <= 1.0.
MAX_BRIGHTNESS = 0.5
BRIGHTNESS_STEPS = 15

# Start at a low brightness, green, 2 pixels,
brightness_step = 2
color_index = 0
num_pixels = 2
cp.pixels.auto_write = False

while True:
    if cp.light > TURN_OFF:
        # Indicate the nightlight is off.
        cp.red_led = True
        continue
    else:
        cp.red_led = False

    # Decrease brightness.
    if cp.touch_A7:
        # Don't go below 1.
        brightness_step = max(1, brightness_step - 1)

    # Increase brightness.
    if cp.touch_A6:
        # Don't go above BRIGHTNESS_STEPS.
        brightness_step = min(BRIGHTNESS_STEPS, brightness_step + 1)

    # Change color.
    if cp.touch_A3:
        # Cycle through 0 to len(COLORS)-1 and then wrap around.
        color_index = (color_index + 1) % len(COLORS)

    # Increase number of pixels.
    if cp.touch_A5:
        # Don't go below 1.
        num_pixels = max(1, num_pixels - 1)

    # Decrease number of pixels.
    if cp.touch_A4:
        # Don't go above 10 (number on Circuit Playgrounds).
        num_pixels = min(10, num_pixels + 1)


    # Scale brightness to be 0.0 - MAX_BRIGHTNESS.
    cp.pixels.brightness = (brightness_step / BRIGHTNESS_STEPS) * MAX_BRIGHTNESS
    for i in range(num_pixels):
        cp.pixels[i] = COLORS[color_index]
    for i in range(num_pixels, 10):
        cp.pixels[i] = 0
    cp.pixels.show()

    time.sleep(0.2)
