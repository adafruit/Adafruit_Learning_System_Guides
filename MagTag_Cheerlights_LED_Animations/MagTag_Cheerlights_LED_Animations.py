# SPDX-FileCopyrightText: 2020 Kattni Rembor, written for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense
import time
import board
import neopixel
from adafruit_magtag.magtag import MagTag

from adafruit_led_animation.animation.comet import Comet
from adafruit_led_animation.animation.sparkle import Sparkle
from adafruit_led_animation.animation.chase import Chase
from adafruit_led_animation.animation.blink import Blink
from adafruit_led_animation.animation.pulse import Pulse
from adafruit_led_animation.sequence import AnimationSequence
from adafruit_led_animation.group import AnimationGroup
from adafruit_led_animation.color import RED, GREEN, BLUE, CYAN, WHITE,\
    OLD_LACE, PURPLE, MAGENTA, YELLOW, ORANGE, PINK

# =============== CUSTOMISATIONS ================
# The strip LED brightness, where 0.0 is 0% (off) and 1.0 is 100% brightness, e.g. 0.3 is 30%
strip_pixel_brightness = 1
# The MagTag LED brightness, where 0.0 is 0% (off) and 1.0 is 100% brightness, e.g. 0.3 is 30%.
magtag_pixel_brightness = 0.5

# The rate interval in seconds at which the Cheerlights data is fetched.
# Defaults to one minute (60 seconds).
refresh_rate = 60
# ===============================================

# Set up where we'll be fetching data from
DATA_SOURCE = "http://api.thingspeak.com/channels/1417/field/1/last.json"
COLOR_LOCATION = ['field1']
DATE_LOCATION = ['created_at']

magtag = MagTag(
    url=DATA_SOURCE,
    json_path=(COLOR_LOCATION, DATE_LOCATION),
)
magtag.network.connect()

strip_pixels = neopixel.NeoPixel(board.D10, 30, brightness=strip_pixel_brightness)
magtag_pixels = magtag.peripherals.neopixels
magtag_pixels.brightness = magtag_pixel_brightness

# Cheerlights color
magtag.add_text(
    text_scale=2,
    text_position=(10, 15),
    text_transform=lambda x: "New Color: {}".format(x),  # pylint: disable=unnecessary-lambda
)
# datestamp
magtag.add_text(
    text_scale=2,
    text_position=(10, 65),
    text_transform=lambda x: "Updated on:\n{}".format(x),  # pylint: disable=unnecessary-lambda
)

timestamp = None
while True:
    if not timestamp or ((time.monotonic() - timestamp) > refresh_rate):  # Refresh rate in seconds
        try:
            # Turn on the MagTag NeoPixels.
            magtag.peripherals.neopixel_disable = False

            # Fetch the color and datetime, and print it to the serial console.
            cheerlights_update_info = magtag.fetch()
            print("Response is", cheerlights_update_info)

            # Get the color from the fetched info for use below.
            cheerlights_color = cheerlights_update_info[0]

            # If red, blue or pink, do a comet animation in the specified color.
            if cheerlights_color in ('red', 'blue', 'pink'):
                if cheerlights_color == 'red':
                    comet_color = RED
                elif cheerlights_color == 'blue':
                    comet_color = BLUE
                elif cheerlights_color == 'pink':
                    comet_color = PINK
                animations = AnimationSequence(
                    AnimationGroup(
                        Comet(magtag_pixels, 0.3, color=comet_color, tail_length=3),
                        Comet(strip_pixels, 0.05, color=comet_color, tail_length=15),
                    )
                )

            # If green or orange, do a pulse animation in the specified color.
            if cheerlights_color in ('green', 'orange'):
                if cheerlights_color == 'green':
                    pulse_color = GREEN
                elif cheerlights_color == 'orange':
                    pulse_color = ORANGE
                animations = AnimationSequence(
                    AnimationGroup(
                        Pulse(magtag_pixels, speed=0.1, color=pulse_color, period=3),
                        Pulse(strip_pixels, speed=0.1, color=pulse_color, period=3),
                    )
                )

            # If oldlace, warmmwhite or magenta, do a sparkle animation in the specified color.
            if cheerlights_color in ('oldlace', 'warmwhite', 'magenta'):
                if cheerlights_color in ('oldlace', 'warmwhite'):
                    sparkle_color = OLD_LACE
                elif cheerlights_color == 'magenta':
                    sparkle_color = MAGENTA
                animations = AnimationSequence(
                    AnimationGroup(
                        Sparkle(magtag_pixels, speed=0.1, color=sparkle_color, num_sparkles=1),
                        Sparkle(strip_pixels, speed=0.01, color=sparkle_color, num_sparkles=15),
                    )
                )

            # If cyan or purple, do a blink animation in the specified color.
            if cheerlights_color in ('cyan', 'purple'):
                if cheerlights_color == 'cyan':
                    blink_color = CYAN
                elif cheerlights_color == 'purple':
                    blink_color = PURPLE
                animations = AnimationSequence(
                    AnimationGroup(
                        Blink(magtag_pixels, speed=0.5, color=blink_color),
                        Blink(strip_pixels, speed=0.5, color=blink_color),
                    )
                )

            # If white or yellow, do a chase animation in the specified color.
            if cheerlights_color in ('white', 'yellow'):
                if cheerlights_color == 'white':
                    chase_color = WHITE
                elif cheerlights_color == 'yellow':
                    chase_color = YELLOW
                animations = AnimationSequence(
                    AnimationGroup(
                        Chase(magtag_pixels, speed=0.1, size=2, spacing=1, color=chase_color),
                        Chase(strip_pixels, speed=0.1, size=3, spacing=2, color=chase_color),
                    )
                )

            timestamp = time.monotonic()
        except (ValueError, RuntimeError) as e:
            # Catch any random errors so the code will continue running.
            print("Some error occured, retrying! -", e)
    try:
        # This runs the animations.
        animations.animate()
    except NameError:
        # If Cheerlights adds a color not included above, the code would fail. This allows it to
        # continue to retry until a valid color comes up.
        print("There may be a Cheerlights color not included above.")
