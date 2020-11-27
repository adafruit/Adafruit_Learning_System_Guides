import board
import digitalio
import neopixel
from adafruit_magtag.magtag import MagTag

from adafruit_led_animation.animation.comet import Comet
from adafruit_led_animation.animation.sparkle import Sparkle
from adafruit_led_animation.animation.solid import Solid
from adafruit_led_animation.animation.colorcycle import ColorCycle
from adafruit_led_animation.sequence import AnimationSequence, AnimateOnce
from adafruit_led_animation.group import AnimationGroup
from adafruit_led_animation.color import RED, GREEN, BLUE, WHITE, GOLD

# =============== CUSTOMISATIONS ================
# The pin to which you connected your NeoPixel strip.
strip_pin = board.D10
# The number of NeoPixels on the strip.
strip_num = 30

# The LED brightness, where 0.0 is 0% (off) and 1.0 is 100% brightness, e.g. 0.3 is 30%.
pixel_brightness = 0.2

# IF YOU ADD NEW COLORS, YOU MUST IMPORT THEM.
# The colors to cycle through. Can be any number of colors.
color_cycle_colors = (RED, GREEN)
# The speed of the color cycle in seconds. Decreasing speeds it up, increasing slows it down.
cycle_speed = 0.5

# The sparkle color.
sparkle_color = GOLD
# The sparkle speed in seconds. Decreasing speeds it up, increasing slows it down.
sparkle_speed = 0.1

# The comet colors.
comet_one_color = WHITE
comet_two_color = BLUE

# The speed of the comet on the MagTag NeoPixels.
magtag_comet_speed = 0.06
# The length of the comet tail on the MagTag NeoPixels.
magtag_comet_tail = 3
# The speed of the comet on the strip of NeoPixels.
strip_comet_speed = 0.03
# The length of the comet tail on the strip of NeoPixels.
strip_comet_tail = 15
# ===============================================

# Setup MagTag library.
magtag = MagTag()

# Setup pixels.
pixels = magtag.peripherals.neopixels
pixels.brightness = pixel_brightness
magtag.peripherals.neopixel_disable = False
strip = neopixel.NeoPixel(strip_pin, strip_num, brightness=pixel_brightness, auto_write=False)

# Create animations in sequences and groups.
animations = AnimationSequence(
    AnimationGroup(
        ColorCycle(pixels, cycle_speed, color_cycle_colors),
        ColorCycle(strip, cycle_speed, color_cycle_colors),
        sync=True,
    ),
    AnimationGroup(
        Sparkle(pixels, sparkle_speed, sparkle_color, 15),
        Sparkle(strip, sparkle_speed, sparkle_color, 1),
    ),
    AnimationSequence(
        AnimateOnce(
            AnimationGroup(
                Comet(pixels, magtag_comet_speed, comet_one_color, tail_length=magtag_comet_tail),
                Comet(strip, strip_comet_speed, comet_one_color, tail_length=strip_comet_tail),
            ),
            AnimationGroup(
                Comet(pixels, magtag_comet_speed, comet_two_color, tail_length=magtag_comet_tail),
                Comet(strip, strip_comet_speed, comet_two_color, tail_length=strip_comet_tail),
            ),
        ),
    ),
    AnimationGroup(
        # Turn the LEDs off.
        Solid(pixels, 0),
        Solid(strip, 0),
    ),
    auto_clear=True,
)

# Main loop.
while True:
    if magtag.peripherals.button_a_pressed:
        animations.activate(0)
    elif magtag.peripherals.button_b_pressed:
        animations.activate(1)
    elif magtag.peripherals.button_c_pressed:
        animations.activate(2)
    elif magtag.peripherals.button_d_pressed:
        animations.activate(3)
    animations.animate()
