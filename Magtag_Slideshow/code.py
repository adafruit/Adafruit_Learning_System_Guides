# Magtag Slideshow
# auto plays .bmp images in /slides folder
# press left and right buttons to go back or forward one slide
# press down button to toggle autoplay mode
# press up button to toggle sound

import time
import terminalio
from adafruit_magtag.magtag import MagTag
from adafruit_slideshow import PlayBackOrder, SlideShow, PlayBackDirection

magtag = MagTag()


def blink(color, duration):
    magtag.peripherals.neopixel_disable = False
    magtag.peripherals.neopixels.fill(color)
    time.sleep(duration)
    magtag.peripherals.neopixel_disable = True


RED = 0x880000
GREEN = 0x008800
BLUE = 0x000088
YELLOW = 0x884400
CYAN = 0x0088BB
MAGENTA = 0x9900BB
WHITE = 0x888888

blink(WHITE, 0.3)

# pylint: disable=no-member
magtag.add_text(
    text_font=terminalio.FONT,
    text_position=(
        5,
        (magtag.graphics.display.height // 2) - 1,
    ),
    text_scale=3,
)
magtag.set_text("MagTag Slideshow")
time.sleep(5)
magtag.add_text(
    text_font=terminalio.FONT,
    text_position=(3, 120),
    text_scale=1,
)
magtag.set_text("  back        mute      pause/play     fwd", 1)
time.sleep(8)

timestamp = time.monotonic()
sound_toggle = True  # state of sound feedback
autoplay_toggle = True  # state of autoplay
auto_pause = 60  # time between slides in auto mode

# Create the slideshow object that plays through alphabetically.
slideshow = SlideShow(
    magtag.graphics.display,
    None,
    auto_advance=autoplay_toggle,
    folder="/slides",
    loop=True,
    order=PlayBackOrder.ALPHABETICAL,
    dwell=auto_pause,
)

while True:
    slideshow.update()
    if magtag.peripherals.button_a_pressed:
        if sound_toggle:
            magtag.peripherals.play_tone(220, 0.15)
        blink(YELLOW, 0.4)
        slideshow.direction = PlayBackDirection.BACKWARD
        time.sleep(5)
        slideshow.advance()

    if magtag.peripherals.button_b_pressed:
        if not sound_toggle:
            magtag.peripherals.play_tone(660, 0.15)
            blink(CYAN, 0.4)
        else:
            blink(MAGENTA, 0.4)
        sound_toggle = not sound_toggle

    if magtag.peripherals.button_c_pressed:
        if not autoplay_toggle:
            if sound_toggle:
                magtag.peripherals.play_tone(440, 0.15)
            blink(GREEN, 0.4)
            autoplay_toggle = True
            slideshow.direction = PlayBackDirection.FORWARD
            slideshow.auto_advance = True
        else:
            if sound_toggle:
                magtag.peripherals.play_tone(110, 0.15)
            blink(RED, 0.4)
            autoplay_toggle = False
            slideshow.auto_advance = False

    if magtag.peripherals.button_d_pressed:
        if sound_toggle:
            magtag.peripherals.play_tone(880, 0.15)
        blink(BLUE, 0.4)
        slideshow.direction = PlayBackDirection.FORWARD
        time.sleep(5)
        slideshow.advance()

    time.sleep(0.01)
