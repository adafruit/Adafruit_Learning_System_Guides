# Magtag Slideshow
# auto plays .bmp images in /slides folder
# press left and right buttons to go back or forward one slide
# press down button to toggle autoplay mode
# press up button to toggle NeoPixels

import time
import board
from digitalio import DigitalInOut, Direction, Pull
import displayio
import adafruit_il0373
from adafruit_slideshow import SlideShow, PlayBackDirection
import neopixel

displayio.release_displays()
display_bus = displayio.FourWire(board.SPI(), command=board.EPD_DC,
                                 chip_select=board.EPD_CS,
                                 reset=board.EPD_RESET, baudrate=1000000)
time.sleep(1)
display = adafruit_il0373.IL0373(
    display_bus,
    width=296,
    height=128,
    rotation=270,
    black_bits_inverted=False,
    color_bits_inverted=False,
    grayscale=True,
    refresh_time=1,
    seconds_per_frame=1  # this overrides the default 180, just be careful
)

forward_button = DigitalInOut(board.BUTTON_D)
back_button = DigitalInOut(board.BUTTON_A)
pixel_button = DigitalInOut(board.BUTTON_B)
pixel_enable = DigitalInOut(board.NEOPIXEL_POWER)
autoplay_button = DigitalInOut(board.BUTTON_C)
led = DigitalInOut(board.D13)

forward_button.pull = Pull.UP
back_button.pull = Pull.UP
pixel_button.pull = Pull.UP
autoplay_button.pull = Pull.UP

led.direction = Direction.OUTPUT
pixel_enable.direction = Direction.OUTPUT

pixel_enable.value = False  # Set this False to use NeoPixels
led.value = True

RED = (0xff0000)
GREEN = (0x00ff00)
BLUE = (0x0000ff)
YELLOW = (0xbb6600)
CYAN = (0x0088bb)
MAGENTA = (0x9900bb)
WHITE = (0xaaaaaa)
BLACK = (0x000000)

pixels = neopixel.NeoPixel(board.NEOPIXEL, 4, brightness=0.04, auto_write=False)

def blink_pixels(color, seconds):
    pixels.fill(color)
    pixels.show()
    time.sleep(seconds)
    pixels.fill(BLACK)
    pixels.show()

blink_pixels(WHITE, 1)

def light_pixels(color):
    pixels.fill(color)
    pixels.show()

slideshow = SlideShow(
    display,
    None,
    folder="/slides",
    auto_advance=False,
    dwell=0,
)

print(slideshow.current_image_name)
display.refresh()
time.sleep(1)

pixel_toggle = False  # holds state of the pixels
autoplay_toggle = True
auto_pause = 60  # time between slides in auto mode
timestamp = None

while True:
    if not timestamp or (time.monotonic() - timestamp) > auto_pause:
        timestamp = time.monotonic()
        if autoplay_toggle:
            slideshow.advance()
            print(slideshow.current_image_name)
            display.refresh()

    if not forward_button.value:  # button is pressed when it goes false
        led.value = True
        light_pixels(CYAN)
        slideshow.direction = PlayBackDirection.FORWARD
        slideshow.advance()
        print(slideshow.current_image_name)
        display.refresh()
        light_pixels(BLACK)

    if not back_button.value:
        led.value = True
        light_pixels(MAGENTA)
        slideshow.direction = PlayBackDirection.BACKWARD
        slideshow.advance()
        print(slideshow.current_image_name)
        display.refresh()
        light_pixels(BLACK)

    if not pixel_button.value:
        led.value = True
        if not pixel_toggle:
            light_pixels(YELLOW)
            pixel_toggle = True
            time.sleep(0.35)  # debounce
        else:
            light_pixels(BLACK)
            pixel_toggle = False
            time.sleep(0.35)  # debounce

    if not autoplay_button.value:
        led.value = True
        if not autoplay_toggle:
            autoplay_toggle = True
            light_pixels(GREEN)
            print("Autoplay ON")
            time.sleep(0.25)
            light_pixels(BLACK)

        else:
            autoplay_toggle = False
            light_pixels(RED)
            print("Autoplay off")
            time.sleep(0.25)
            light_pixels(BLACK)

    led.value = False
