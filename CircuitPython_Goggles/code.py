# SPDX-FileCopyrightText: 2019 Phillip Burgess for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# pylint: disable=import-error


# NeoPixel goggles code for CircuitPython
#
# With a rotary encoder attached (pins are declred in the "Initialize
# hardware" section of the code), you can select animation modes and
# configurable attributes (color, brightness, etc.). TAP the encoder
# button to switch between modes/settings, HOLD the encoder button to
# toggle between PLAY and CONFIGURE states.
#
# With no rotary encoder attached, you can select an animation mode
# and configure attributes in the "Configurable defaults" section
# (including an option to auto-cycle through the animation modes).
#
# Things to Know:
# - FancyLED library is NOT used here because it's a bit too much for the
#   Trinket M0 to handle (animation was very slow).
# - Animation modes are all monochromatic (single color, varying only in
#   brightness). More a design decision than a technical one...of course
#   NeoPixels can be individual colors, but folks like customizing and the
#   monochromatic approach makes it easier to select a color. Also keeps the
#   code a bit simpler, since Trinket space & performance is limited.
# - Animation is monotonic time driven; there are no sleep() calls. This
#   ensures that animation is constant-time regardless of the hardware or
#   CircuitPython performance over time, or other goings on (e.g. garbage
#   collection), only the frame rate (smoothness) varies; overall timing
#   remains consistent.

from math import modf, pi, sin
from random import getrandbits
from time import monotonic
from digitalio import DigitalInOut, Direction
from richbutton import RichButton
from rotaryio import IncrementalEncoder
import adafruit_dotstar
import board
import neopixel

# Configurable defaults

PIXEL_HUE = 0.0         # Red at start
PIXEL_BRIGHTNESS = 0.4  # 40% brightness at start
PIXEL_GAMMA = 2.6       # Controls brightness linearity
RING_1_OFFSET = 10      # Alignment of top pixel on 1st NeoPixel ring
RING_2_OFFSET = 10      # Alignment of top pixel on 2nd NeoPixel ring
RING_2_FLIP = True      # If True, reverse order of pixels on 2nd ring
CYCLE_INTERVAL = 0      # If >0 auto-cycle through play modes @ this interval
SPEED = 1.0             # Initial animation speed for modes that use it
XRAY_BITS = 0x0821      # Initial bit pattern for "X-ray" mode

# Things you probably don't want to change, unless adding new modes

PLAY_MODE_SPIN = 0               # Revolving pulse
PLAY_MODE_XRAY = 1               # Watchmen-inspired "X-ray goggles"
PLAY_MODE_SCAN = 2               # Scanline effect
PLAY_MODE_SPARKLE = 3            # Random dots
PLAY_MODES = 4                   # Number of PLAY modes
PLAY_MODE = PLAY_MODE_SPIN       # Initial PLAY mode

CONFIG_MODE_COLOR = 0            # Setting color (hue)
CONFIG_MODE_BRIGHTNESS = 1       # Setting brightness
CONFIG_MODE_ALIGN = 2            # Top pixel indicator
CONFIG_MODES = 3                 # Number of CONFIG modes
CONFIG_MODE = CONFIG_MODE_COLOR  # Initial CONFIG mode
CONFIGURING = False              # NOT configuring at start
# CONFIG_MODE_ALIGN is only used to test the values of RING_1_OFFSET and
# RING_2_OFFSET. The single lit pixel should appear at the top of each ring.
# If it does not, adjust each of those two values (integer from 0 to 15)
# until the pixel appears at the top (or physically reposition the rings).
# Some of the animation modes rely on the two rings being aligned a certain
# way. Once adjusted, you can reduce the value of CONFIG_MODES and this
# mode will be skipped in config state.

# Initialize hardware - PIN DEFINITIONS APPEAR HERE

# Turn off onboard DotStar LED
DOTSTAR = adafruit_dotstar.DotStar(board.APA102_SCK, board.APA102_MOSI, 1)
DOTSTAR.brightness = 0

# Turn off onboard discrete LED
LED = DigitalInOut(board.D13)
LED.direction = Direction.OUTPUT
LED.value = 0

# Declare NeoPixels on pin D0, 32 pixels long. Set to max brightness because
# on-the-fly brightness slows down NeoPixel lib, so we'll do our own here.
PIXELS = neopixel.NeoPixel(board.D0, 32, brightness=1.0, auto_write=False)

# Declare rotary encoder on pins D4 and D3, and click button on pin D2.
# If encoder behaves backwards from what you want, swap pins here.
ENCODER = IncrementalEncoder(board.D4, board.D3)
ENCODER_BUTTON = RichButton(board.D2)


def set_pixel(pixel_num, brightness):
    """Set one pixel in both 16-pixel rings. Pass in pixel index (0 to 15)
       and relative brightness (0.0 to 1.0). Actual resulting brightness
       will be a function of global brightness and gamma correction."""
    # Clamp passed brightness to 0.0-1.0 range,
    # apply global brightness and gamma correction
    brightness = max(min(brightness, 1.0), 0.0) * PIXEL_BRIGHTNESS
    brightness = pow(brightness, PIXEL_GAMMA) * 255.0
    # local_color is adjusted brightness applied to global PIXEL_COLOR
    local_color = (
        int(PIXEL_COLOR[0] * brightness + 0.5),
        int(PIXEL_COLOR[1] * brightness + 0.5),
        int(PIXEL_COLOR[2] * brightness + 0.5))
    # Roll over pixel_num as needed to 0-15 range, then store color
    pixel_num_wrapped = (pixel_num + RING_1_OFFSET) & 15
    PIXELS[pixel_num_wrapped] = local_color
    # Determine corresponding pixel for second ring. Mirror direction if
    # configured for such, correct for any rotational difference, then
    # perform similar roll-over as above before storing color.
    if RING_2_FLIP:
        pixel_num = 15 - pixel_num
    pixel_num_wrapped = 16 + ((pixel_num + RING_2_OFFSET) & 15)
    PIXELS[pixel_num_wrapped] = local_color


def triangle_wave(pos, peak=0.5):
    """Return a brightness level (0.0 to 1.0) corresponding to a position
       (0.0 to 1.0) within a triangle wave (spanning 0.0 to 1.0) with wave's
       peak brightness at a given position (0.0 to 1.0) within its span.
       Positions outside the wave's span return 0.0."""
    if 0.0 <= pos < 1.0:
        if pos <= peak:
            return pos / peak
        return (1.0 - pos) / (1.0 - peak)
    return 0.0


def hue_to_rgb(hue):
    """Given a hue value as a float, where the fractional portion
       (0.0 to 1.0) indicates the actual hue (starting from red at 0,
       to green at 1/3, to blue at 2/3, and back to red at 1.0),
       return an RGB color as a 3-tuple with values from 0.0 to 1.0."""
    hue = modf(hue)[0]
    sixth = (hue * 6.0) % 6.0
    ramp = modf(sixth)[0]
    if sixth < 1.0:
        return (1.0, ramp, 0.0)
    if sixth < 2.0:
        return (1.0 - ramp, 1.0, 0.0)
    if sixth < 3.0:
        return (0.0, 1.0, ramp)
    if sixth < 4.0:
        return (0.0, 1.0 - ramp, 1.0)
    if sixth < 5.0:
        return (ramp, 0.0, 1.0)
    return (1.0, 0.0, 1.0 - ramp)


def random_bits():
    """Generate random bit pattern, avoiding adjacent set bits (w/wrap)"""
    pattern = getrandbits(16)
    pattern |= (pattern & 1) << 16   # Replicate bit 0 at bit 16
    return pattern & ~(pattern >> 1) # Mask out adjacent set bits


# Some last-minute state initialization

POS = 0                              # Initial swirl animation position
PIXEL_COLOR = hue_to_rgb(PIXEL_HUE)  # Initial color
ENCODER_PRIOR = ENCODER.position     # Initial encoder position
TIME_PRIOR = monotonic()             # Initial time
LAST_CYCLE_TIME = TIME_PRIOR         # For mode auto-cycling
SPARKLE_BITS_PREV = 0                # First bits for sparkle animation
SPARKLE_BITS_NEXT = 0                # Next bits for sparkle animation
PREV_WEIGHT = 2                      # Force initial sparkle refresh


# Main loop

while True:
    ACTION = ENCODER_BUTTON.action()
    if ACTION is RichButton.TAP:
        # Encoder button tapped, cycle through play or config modes:
        if CONFIGURING:
            CONFIG_MODE = (CONFIG_MODE + 1) % CONFIG_MODES
        else:
            PLAY_MODE = (PLAY_MODE + 1) % PLAY_MODES
    elif ACTION is RichButton.DOUBLE_TAP:
        # DOUBLE_TAP not currently used, but this is where it would go.
        pass
    elif ACTION is RichButton.HOLD:
        # Encoder button held, toggle between PLAY and CONFIG modes:
        CONFIGURING = not CONFIGURING
    elif ACTION is RichButton.RELEASE:
        # RELEASE not currently used (play/config state changes when HOLD
        # is detected), but this is where it would go.
        pass

    # Process encoder input. Code always uses the ENCODER_CHANGE value
    # for relative adjustments.
    ENCODER_POSITION = ENCODER.position
    ENCODER_CHANGE = ENCODER_POSITION - ENCODER_PRIOR
    ENCODER_PRIOR = ENCODER_POSITION

    # Same idea, but for elapsed time (so time-based animation continues
    # at the next position, it doesn't jump around as when multiplying
    # monotonic() by SPEED.
    TIME_NOW = monotonic()
    TIME_CHANGE = TIME_NOW - TIME_PRIOR
    TIME_PRIOR = TIME_NOW

    if CONFIGURING:
        # In config mode, different pixel patterns indicate which
        # adjustment is being made (e.g. alternating pixels = hue mode).
        if CONFIG_MODE is CONFIG_MODE_COLOR:
            PIXEL_HUE = modf(PIXEL_HUE + ENCODER_CHANGE * 0.01)[0]
            PIXEL_COLOR = hue_to_rgb(PIXEL_HUE)
            for i in range(0, 16):
                set_pixel(i, i & 1)  # Turn on alternating pixels
        elif CONFIG_MODE is CONFIG_MODE_BRIGHTNESS:
            PIXEL_BRIGHTNESS += ENCODER_CHANGE * 0.025
            PIXEL_BRIGHTNESS = max(min(PIXEL_BRIGHTNESS, 1.0), 0.0)
            for i in range(0, 16):
                set_pixel(i, (i & 2) >> 1)  # Turn on pixel pairs
        elif CONFIG_MODE is CONFIG_MODE_ALIGN:
            C = 1      # First pixel on
            for i in range(0, 16):
                set_pixel(i, C)
                C = 0  # All other pixels off
    else:
        # In play mode. Auto-cycle animations if CYCLE_INTERVAL is set.
        if CYCLE_INTERVAL > 0:
            if TIME_NOW - LAST_CYCLE_TIME > CYCLE_INTERVAL:
                PLAY_MODE = (PLAY_MODE + 1) % PLAY_MODES
                LAST_CYCLE_TIME = TIME_NOW

        if PLAY_MODE is PLAY_MODE_XRAY:
            # In XRAY mode, encoder selects random bit patterns
            if abs(ENCODER_CHANGE) > 1:
                XRAY_BITS = random_bits()
            # Unset bits pulsate ever-so-slightly
            DIM = 0.42 + sin(monotonic() * 2) * 0.08
            for i in range(16):
                if XRAY_BITS & (1 << i):
                    set_pixel(i, 1.0)
                else:
                    set_pixel(i, DIM)
        else:
            # In all other modes, encoder adjusts speed/direction
            SPEED += ENCODER_CHANGE * 0.05
            SPEED = max(min(SPEED, 4.0), -4.0)
            POS += TIME_CHANGE * SPEED
            if PLAY_MODE is PLAY_MODE_SPIN:
                for i in range(16):
                    frac = modf(POS + i / 15.0)[0]  # 0.0-1.0 around ring
                    if frac < 0:
                        frac = 1.0 + frac
                    set_pixel(i, triangle_wave(frac, 0.5 - SPEED * 0.125))
            elif PLAY_MODE is PLAY_MODE_SCAN:
                if POS >= 0:
                    S = 2.0 - modf(POS)[0] * 4.0
                else:
                    S = 2.0 - (1.0 + modf(POS)[0]) * 4.0
                for i in range(16):
                    Y = sin((i / 7.5 + 0.5) * pi)  # Pixel Y coord
                    D = 0.5 - abs(Y - S) * 0.6     # Distance to scanline
                    set_pixel(i, triangle_wave(D))
            elif PLAY_MODE is PLAY_MODE_SPARKLE:
                NEXT_WEIGHT = modf(abs(POS * 2.0))[0]
                if SPEED < 0:
                    NEXT_WEIGHT = 1.0 - NEXT_WEIGHT
                if NEXT_WEIGHT < PREV_WEIGHT:
                    SPARKLE_BITS_PREV = SPARKLE_BITS_NEXT
                    while True:
                        SPARKLE_BITS_NEXT = random_bits()
                        if not SPARKLE_BITS_NEXT & SPARKLE_BITS_PREV:
                            break  # No bits in common, good!
                PREV_WEIGHT = 1.0 - NEXT_WEIGHT
                for i in range(16):
                    bit = 1 << i
                    if SPARKLE_BITS_PREV & bit:
                        result = PREV_WEIGHT
                    elif SPARKLE_BITS_NEXT & bit:
                        result = NEXT_WEIGHT
                    else:
                        result = 0
                    set_pixel(i, result)
                PREV_WEIGHT = NEXT_WEIGHT
    PIXELS.show()
