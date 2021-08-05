# Cyber Flower: Digital Valentine
#
# 'Roses are red,
#  Violets are blue,
#  This flower changes color,
#  To show its love for you.'
#
# Load this on a Gemma M0 running CircuitPython and it will smoothly animate
# the DotStar LED between different color hues.  Touch the D0 pad and it will
# cause the pixel to pulse like a heart beat.  You might need to also attach a
# wire to the ground pin to ensure capacitive touch sensing can work on battery
# power.  For example strip the insulation from a wire and solder it to ground,
# then solder a wire (with the insulation still attached) to D0, and wrap
# both wires around the stem of a flower like a double-helix.  When you touch
# the wires you'll ground yourself (touching the bare ground wire) and cause
# enough capacitance in the D0 wire (even though it's still insulated) to
# trigger the heartbeat.  Or just leave D0 unconnected to have a nicely
# animated lit-up flower!
#
# Note that on power-up the flower will wait about 5 seconds before turning on
# the LED.  During this time the board's red LED will flash and this is an
# indication that it's waiting to power on.  Place the flower down so nothing
# is touching it and then pick it up again after the DotStar LED starts
# animating.  This will ensure the capacitive touch sensing isn't accidentally
# calibrated with your body touching it (making it less accurate).
#
# Also note this depends on two external modules to be loaded on the Gemma M0:
#  - Adafruit CircuitPython DotStar:
# https://github.com/adafruit/Adafruit_CircuitPython_DotStar
#  - Adafruit CircuitPython FancyLED:
# https://github.com/adafruit/Adafruit_CircuitPython_FancyLED
#
# You _must_ have both adafruit_dotstar.mpy and the adafruit_fancyled folder
# and files within it on your board for this code to work!  If you run into
# trouble or can't get the dependencies see the main_simple.py code as an
# alternative that has no dependencies but slightly more complex code.
#
# Author: Tony DiCola
# License: MIT License
import math
import time

import adafruit_dotstar
import adafruit_fancyled.adafruit_fancyled as fancy
import board
import digitalio
import touchio

# Variables that control the code.  Try changing these to modify speed, color,
# etc.
START_DELAY = 5.0  # How many seconds to wait after power up before
# jumping into the animation and initializing the
# touch input.  This gives you time to take move your
# fingers off the flower so the capacitive touch
# sensing is better calibrated.  During the delay
# the small red LED on the board will flash.

TOUCH_PIN = board.D0  # The board pin to listen for touches and trigger the
# heart beat animation.  You can change this to any
# other pin like board.D2 or board.D1.  Make sure not
# to touch this pin as the board powers on or the
# capacitive sensing will get confused (just reset
# the board and try again).

BRIGHTNESS = 1.0  # The brightness of the colors.  Set this to a value
# anywhere within 0 and 1.0, where 1.0 is full bright.
# For example 0.5 would be half brightness.

RAINBOW_PERIOD_S = 18.0  # How many seconds it takes for the default rainbow
# cycle animation to perform a full cycle.  Increase
# this to slow down the animation or decrease to speed
# it up.

HEARTBEAT_BPM = 60.0  # Heartbeat animation beats per minute.  Increase to
# speed up the heartbeat, and decrease to slow down.

HEARTBEAT_HUE = 300.0  # The color hue to use when animating the heartbeat
# animation.  Pick a value in the range of 0 to 359
# degrees, see the hue spectrum here:
#   https://en.wikipedia.org/wiki/Hue
# A value of 300 is a nice pink color.

# First initialize the DotStar LED and turn it off.
dotstar = adafruit_dotstar.DotStar(board.APA102_SCK, board.APA102_MOSI, 1)
dotstar[0] = (0, 0, 0)

# Also make sure the on-board red LED is turned off.
red_led = digitalio.DigitalInOut(board.L)
red_led.switch_to_output(value=False)

# Wait the startup delay period while flashing the red LED.  This gives time
# to move your hand away from the flower/stem so the capacitive touch sensing
# is initialized and calibrated with a good non-touch starting state.
start = time.monotonic()
while time.monotonic() - start <= START_DELAY:
    # Blink the red LED on and off every half second.
    red_led.value = True
    time.sleep(0.5)
    red_led.value = False
    time.sleep(0.5)

# Setup the touch input.
touch = touchio.TouchIn(TOUCH_PIN)

# Convert periods to frequencies that are used later in animations.
rainbow_freq = 1.0 / RAINBOW_PERIOD_S

# Calculcate periods and values used by the heartbeat animation.
beat_period = 60.0 / HEARTBEAT_BPM
beat_quarter_period = beat_period / 4.0  # Quarter period controls the speed of
# the heartbeat drop-off (using an
# exponential decay function).
beat_phase = beat_period / 5.0  # Phase controls how long in-between


# the two parts of the heart beat
# (the 'ba-boom' of the beat).

# Handy function for linear interpolation of a value.  Pass in a value
# x that's within the range x0...x1 and a range y0...y1 to get an output value
# y that's proportionally within y0...y1 based on x within x0...x1.  Handy for
# transforming a value in one range to a value in another (like Arduino's map
# function).

# pylint: disable=redefined-outer-name
def lerp(x, x0, x1, y0, y1):
    return y0 + (x - x0) * ((y1 - y0) / (x1 - x0))


# Main loop below will run forever:
while True:
    # Get the current time at the start of the animation update.
    current = time.monotonic()
    # Now check if the touch input is being touched and choose a different
    # animation to run, either a rainbow cycle or heartbeat.
    if touch.value:
        # The touch input is being touched, so figure out the color using
        # a heartbeat animation.
        # This works using exponential decay of the color value (brightness)
        # over time:
        #   https://en.wikipedia.org/wiki/Exponential_decay
        # A heart beat is made of two sub-beats (the 'ba-boom') so two decay
        # functions are calculated using the same fall-off period but slightly
        # out of phase so one occurs a little bit after the other.
        t0 = current % beat_period
        t1 = (current + beat_phase) % beat_period
        x0 = math.pow(math.e, -t0 / beat_quarter_period)
        x1 = math.pow(math.e, -t1 / beat_quarter_period)
        # After calculating both exponential decay values pick the biggest one
        # as the secondary one will occur after the first.  Scale each by
        # the global brightness and then convert to RGB color using the fixed
        # hue but modulating the color value (brightness).  Luckily the result
        # of the exponential decay is a value that goes from 1.0 to 0.0 just
        # like we expect for full bright to zero brightness with HSV color
        # (i.e. no interpolation is necessary).
        val = max(x0, x1) * BRIGHTNESS
        color = fancy.gamma_adjust(fancy.CHSV(HEARTBEAT_HUE / 359.0, 1.0, val))
        dotstar[0] = color.pack()
    else:
        # The touch input is not being touched (touch.value is False) so
        # compute the hue with a smooth cycle over time.
        # First use the sine function to smoothly generate a value that goes
        # from -1.0 to 1.0 at a certain frequency to match the rainbow period.
        x = math.sin(2.0 * math.pi * rainbow_freq * current)
        # Then compute the hue by converting the sine wave value from something
        # that goes from -1.0 to 1.0 to instead go from 0 to 1.0 hue.
        hue = lerp(x, -1.0, 1.0, 0.0, 1.0)
        # Finally update the DotStar LED by converting the HSV color at the
        # specified hue to a RGB color the LED understands.
        color = fancy.gamma_adjust(fancy.CHSV(hue, 1.0, BRIGHTNESS))
        dotstar[0] = color.pack()
