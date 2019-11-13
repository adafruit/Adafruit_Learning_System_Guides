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

import adafruit_dotstar
import board
import neopixel
from digitalio import DigitalInOut, Direction
from math import modf, pi, pow, sin
from random import getrandbits
from richbutton import RichButton
from rotaryio import IncrementalEncoder
from time import monotonic

# Configurable defaults

pixel_hue = 0.0         # Red at start
pixel_brightness = 0.4  # 40% brightness at start
pixel_gamma = 2.6       # Controls brightness linearity
ring_1_offset = 10      # Alignment of top pixel on 1st NeoPixel ring
ring_2_offset = 10      # Alignment of top pixel on 2nd NeoPixel ring
ring_2_flip = True      # If True, reverse order of pixels on 2nd ring
cycle_interval = 0      # If >0 auto-cycle through play modes @ this interval
speed = 1.0             # Initial animation speed for modes that use it
xray_bits = 0x0821      # Initial bit pattern for "X-ray" mode

# Things you probably don't want to change, unless adding new modes

PLAY_MODE_SPIN = 0               # Revolving pulse
PLAY_MODE_XRAY = 1               # Watchmen-inspired "X-ray goggles"
PLAY_MODE_SCAN = 2               # Scanline effect
PLAY_MODE_SPARKLE = 3            # Random dots
PLAY_MODES = 4                   # Number of PLAY modes
play_mode = PLAY_MODE_SPIN       # Initial PLAY mode

CONFIG_MODE_COLOR = 0            # Setting color (hue)
CONFIG_MODE_BRIGHTNESS = 1       # Setting brightness
CONFIG_MODE_ALIGN = 2            # Top pixel indicator
CONFIG_MODES = 3                 # Number of CONFIG modes
config_mode = CONFIG_MODE_COLOR  # Initial CONFIG mode
configuring = False              # NOT configuring at start
# CONFIG_MODE_ALIGN is only used to test the values of ring_1_offset and
# ring_2_offset. The single lit pixel should appear at the top of each ring.
# If it does not, adjust each of those two values (integer from 0 to 15)
# until the pixel appears at the top (or physically reposition the rings).
# Some of the animation modes rely on the two rings being aligned a certain
# way. Once adjusted, you can reduce the value of CONFIG_MODES and this
# mode will be skipped in config state.

# Initialize hardware - PIN DEFINITIONS APPEAR HERE

# Turn off onboard DotStar LED
dotstar = adafruit_dotstar.DotStar(board.APA102_SCK, board.APA102_MOSI, 1)
dotstar.brightness = 0

# Turn off onboard discrete LED
led = DigitalInOut(board.D13)
led.direction = Direction.OUTPUT
led.value = 0

# Declare NeoPixels on pin D0, 32 pixels long. Set to max brightness because
# on-the-fly brightness slows down NeoPixel lib, so we'll do our own here.
pixels = neopixel.NeoPixel(board.D0, 32, brightness=1.0, auto_write=False)

# Declare rotary encoder on pins D4 and D3, and click button on pin D2.
# If encoder behaves backwards from what you want, swap pins here.
encoder = IncrementalEncoder(board.D4, board.D3)
encoder_button = RichButton(board.D2)


# Set one pixel in both 16-pixel rings. Pass in pixel index (0 to 15) and
# relative brightness (0.0 to 1.0). Actual resulting brightness will be a
# function of global brightness and gamma correction.
def setPixel(pixel_num, brightness):
    # Clamp passed brightness to 0.0-1.0 range,
    # apply global brightness and gamma correction
    brightness = max(min(brightness, 1.0), 0.0) * pixel_brightness
    brightness = pow(brightness, pixel_gamma) * 255.0
    # local_color is adjusted brightness applied to global pixel_color
    local_color = (
        int(pixel_color[0] * brightness + 0.5),
        int(pixel_color[1] * brightness + 0.5),
        int(pixel_color[2] * brightness + 0.5))
    # Roll over pixel_num as needed to 0-15 range, then store color
    p = (pixel_num + ring_1_offset) & 15
    pixels[p] = local_color
    # Determine corresponding pixel for second ring. Mirror direction if
    # configured for such, correct for any rotational difference, then
    # perform similar roll-over as above before storing color.
    if ring_2_flip:
        pixel_num = 15 - pixel_num
    p = 16 + ((pixel_num + ring_2_offset) & 15)
    pixels[p] = local_color


# Return a brightness level (0.0 to 1.0) corresponding to a position (0.0
# to 1.0) within a triangle wave (spanning 0.0 to 1.0) with wave's peak
# brightness at a given position (0.0 to 1.0) within its span. Positions
# outside the wave's span return 0.0. Basically, this: _/\_
def triangle_wave(x, peak = 0.5):
    if 0.0 <= x < 1.0:
        if x <= peak:
            return x / peak
        else:
            return (1.0 - x) / (1.0 - peak)
    else:
        return 0.0


# Given a hue value as a float, where the fractional portion (0.0 to 1.0)
# indicates the actual hue (starting from red at 0, to green at 1/3, to
# blue at 2/3, and back to red at 1.0), return an RGB color as a 3-tuple
# with values from 0.0 to 1.0.
def hue_to_rgb(hue):
    hue = modf(hue)[0]
    n = (hue * 6.0) % 6.0
    f = modf(n)[0]
    if n < 1.0:
        return (1.0, f, 0.0)
    elif n < 2.0:
        return (1.0 - f, 1.0, 0.0)
    elif n < 3.0:
        return (0.0, 1.0, f)
    elif n < 4.0:
        return (0.0, 1.0 - f, 1.0)
    elif n < 5.0:
        return (f, 0.0, 1.0)
    else:
        return (1.0, 0.0, 1.0 - f)


# Generate random bit pattern that avoids adjacent set bits (wraps around)
def random_bits():
    pattern = getrandbits(16)
    pattern |= (pattern & 1) << 16   # Replicate bit 0 at bit 16
    return pattern & ~(pattern >> 1) # Mask out adjacent set bits


# Some last-minute state initialization

pos = 0                              # Initial swirl animation position
pixel_color = hue_to_rgb(pixel_hue)  # Initial color
encoder_prior = encoder.position     # Initial encoder position
time_prior = monotonic()             # Initial time
last_cycle_time = time_prior         # For mode auto-cycling
sparkle_bits_prev = 0                # First bits for sparkle animation
sparkle_bits_next = 0                # Next bits for sparkle animation
prev_weight = 2                      # Force initial sparkle refresh


# Main loop

while True:
    action = encoder_button.action()
    if action is RichButton.TAP:
        # Encoder button tapped, cycle through play or config modes:
        if configuring:
            config_mode = (config_mode + 1) % CONFIG_MODES
        else:
            play_mode = (play_mode + 1) % PLAY_MODES
    elif action is RichButton.DOUBLE_TAP:
        # DOUBLE_TAP not currently used, but this is where it would go.
        pass
    elif action is RichButton.HOLD:
        # Encoder button held, toggle between PLAY and CONFIG modes:
        configuring = not configuring
    elif action is RichButton.RELEASE:
        # RELEASE not currently used (play/config state changes when HOLD
        # is detected), but this is where it would go.
        pass

    # Process encoder input. Code always uses the encoder_change value
    # for relative adjustments.
    encoder_position = encoder.position
    encoder_change = encoder.position - encoder_prior
    encoder_prior = encoder_position

    # Same idea, but for elapsed time (so time-based animation continues
    # at the next position, it doesn't jump around as when multiplying
    # monotonic() by speed.
    time_now = monotonic()
    time_change = time_now - time_prior
    time_prior = time_now

    if configuring:
        # In config mode, different pixel patterns indicate which
        # adjustment is being made (e.g. alternating pixels = hue mode).
        if config_mode is CONFIG_MODE_COLOR:
            pixel_hue = modf(pixel_hue + encoder_change * 0.01)[0]
            pixel_color = hue_to_rgb(pixel_hue)
            for i in range(0, 16):
                setPixel(i, i & 1)  # Turn on alternating pixels
        elif config_mode is CONFIG_MODE_BRIGHTNESS:
            pixel_brightness += encoder_change * 0.025
            pixel_brightness = max(min(pixel_brightness, 1.0), 0.0)
            for i in range(0, 16):
                setPixel(i, (i & 2) >> 1)  # Turn on pixel pairs
        elif config_mode is CONFIG_MODE_ALIGN:
            c = 1      # First pixel on
            for i in range(0, 16):
                setPixel(i, c)
                c = 0  # All other pixels off
    else:
        # In play mode. Auto-cycle animations if cycle_interval is set.
        if cycle_interval > 0:
            if time_now - last_cycle_time > cycle_interval:
                play_mode = (play_mode + 1) % PLAY_MODES
                last_cycle_time = time_now

        if play_mode is PLAY_MODE_XRAY:
            # In XRAY mode, encoder selects random bit patterns
            if abs(encoder_change) > 1:
                xray_bits = random_bits()
            # Unset bits pulsate ever-so-slightly
            dim = 0.42 + sin(monotonic() * 2) * 0.08
            for i in range(16):
                if xray_bits & (1 << i):
                    setPixel(i, 1.0)
                else:
                    setPixel(i, dim)
        else:
            # In all other modes, encoder adjusts speed/direction
            speed += encoder_change * 0.05
            speed = max(min(speed, 4.0), -4.0)
            pos += time_change * speed
            if play_mode is PLAY_MODE_SPIN:
                for i in range(16):
                    frac = modf(pos + i / 15.0)[0]  # 0.0-1.0 around ring
                    if frac < 0:
                        frac = 1.0 + frac
                    setPixel(i, triangle_wave(frac, 0.5 - speed * 0.125))
            elif play_mode is PLAY_MODE_SCAN:
                if pos >= 0:
                    s = 2.0 - modf(pos)[0] * 4.0
                else:
                    s = 2.0 - (1.0 + modf(pos)[0]) * 4.0
                for i in range(16):
                    y = sin((i / 7.5 + 0.5) * pi)  # Pixel Y coord
                    d = 0.5 - abs(y - s) * 0.6     # Distance to scanline
                    setPixel(i, triangle_wave(d))
            elif play_mode is PLAY_MODE_SPARKLE:
                next_weight = modf(abs(pos * 2.0))[0]
                if speed < 0:
                    next_weight = 1.0 - next_weight
                if next_weight < prev_weight:
                    sparkle_bits_prev = sparkle_bits_next
                    while True:
                        sparkle_bits_next = random_bits()
                        if not sparkle_bits_next & sparkle_bits_prev:
                            break  # No bits in common, good!
                prev_weight = 1.0 - next_weight
                for i in range(16):
                    bit = 1 << i
                    if sparkle_bits_prev & bit:
                        result = prev_weight
                    elif sparkle_bits_next & bit:
                        result = next_weight
                    else:
                        result = 0
                    setPixel(i, result)
                prev_weight = next_weight
    pixels.show()
