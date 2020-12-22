import time
import adafruit_dotstar
import board
import random
import touchio
from adafruit_pixel_framebuf import PixelFramebuffer
from adafruit_led_animation.animation.rainbowchase import RainbowChase
from adafruit_led_animation.animation.rainbowcomet import RainbowComet
from adafruit_led_animation.animation.chase import Chase
from adafruit_led_animation.color import PINK

from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.nordic import UARTService
from adafruit_bluefruit_connect.packet import Packet
from adafruit_bluefruit_connect.color_packet import ColorPacket
from adafruit_bluefruit_connect.button_packet import ButtonPacket

################################################################################
# Customize variables

# Set capacitive touch pin
TOUCH_PIN = board.D11

# These are the pixels covered by the brass cap touch
# We will try to avoid using these pixels in the "twinkle" default animation
COVERED_PIXELS = [40,41,42,48,49,50,56,57,58]

# Adjust this higher if touch is too sensitive
TOUCH_THRESHOLD = 3000

# Adjust SCROLL_TEXT_COLOR_CHANGE_WAIT lower to make the color changes for
# the text scroll animation faster
SCROLL_TEXT_COLOR_CHANGE_WAIT = 5

# Change this text that will be displayed when tapping 2 on the
# Bluefruit app control pad (after connecting on your phone)
SCROLL_TEXT_CUSTOM_WORD = "hello world"

# Increase number to slow down scrolling
SCROLL_TEXT_WAIT = 0.05

# How bright each pixel in the default twinkling animation will be
TWINKLE_BRIGHTNESS = 0.1

###############################################################################
# Initialize hardware

touch_pad = TOUCH_PIN
touch = touchio.TouchIn(touch_pad)
touch.threshold = TOUCH_THRESHOLD

ble = BLERadio()
uart_service = UARTService()
advertisement = ProvideServicesAdvertisement(uart_service)

# Colors
YELLOW = (255, 150, 0)
TEAL = (0, 255, 120)
CYAN = (0, 255, 255)
PURPLE = (180, 0, 255)
TWINKLEY = (255, 255, 255)
OFF = (0, 0, 0)

# Setup Dotstar grid and pixel framebuffer for fancy animations
pixel_width = 8
pixel_height = 8
num_pixels = pixel_width * pixel_height
pixels = adafruit_dotstar.DotStar(board.A1, board.A2, num_pixels, auto_write=False, brightness=0.1)
pixel_framebuf = PixelFramebuffer(
    pixels,
    pixel_width,
    pixel_height,
    rotation=1,
    alternating=False,
    reverse_x=True
)
# Fancy animations from https://learn.adafruit.com/circuitpython-led-animations
rainbow_chase = RainbowChase(pixels, speed=0.1, size=3, spacing=6, step=8)
chase = Chase(pixels, speed=0.1, color=CYAN, size=3, spacing=6)
rainbow_comet = RainbowComet(pixels, speed=0.1, tail_length=5, bounce=True, colorwheel_offset=170)


def scroll_framebuf_neg_x(word, color, shift_x, shift_y):
    pixel_framebuf.fill(0)
    color_int = int('0x%02x%02x%02x' % color, 16)

    # negate x so that the word can be shown from left to right
    pixel_framebuf.text(word, -shift_x, shift_y, color_int)
    pixel_framebuf.display()
    time.sleep(SCROLL_TEXT_WAIT)

def scroll_text(packet, word):
    # scroll through entire length of string.
    # each letter is always 5 pixels wide, plus 1 space per letter
    scroll_len = (len(word) * 5) + len(word)
    color_list = [CYAN, TWINKLEY, PINK, PURPLE, YELLOW]

    color_i = 0
    color_wait_tick = 0
    # start the scroll from off the grid at -pixel_width
    for x_pos in range(-pixel_width, scroll_len):
        # detect touch
        if touch.value:
            pixel_framebuf.fill(0)
            pixel_framebuf.display()
            return;

        # detect new packet
        if isinstance(packet, ButtonPacket) and packet.pressed:
            return;

        color = color_list[color_i]
        scroll_framebuf_neg_x(word, color, x_pos, 0)

        # Only change colors after SCROLL_TEXT_COLOR_CHANGE_WAIT
        color_wait_tick = color_wait_tick + 1
        if color_wait_tick == SCROLL_TEXT_COLOR_CHANGE_WAIT:
            color_i = color_i + 1
            color_wait_tick = 0

        if color_i == len(color_list):
            color_i=0

    # wait a bit before scrolling again
    time.sleep(.5)

# Manually chosen pixels to display "Y"
# in the proper orientation
def yes(color):
    pixels[26] = color
    pixels[27] = color
    pixels[28] = color
    pixels[36] = color
    pixels[44] = color
    pixels[21] = color
    pixels.show()
    time.sleep(0.1)
    pixels.fill(0)

# Manually chosen pixels to display "N"
# in the proper orientation
def no(color):
    pixels[26] = color
    pixels[19] = color
    pixels[12] = color
    pixels[27] = color
    pixels[28] = color
    pixels[29] = color
    pixels[30] = color
    pixels[37] = color
    pixels[44] = color
    pixels.show()
    time.sleep(0.1)
    pixels.fill(0)

def yes_or_no():
    pixels.fill(0)
    print(touch.raw_value)
    value = 0
    pick=0

    pick = random.randint(0,64)
    time.sleep(0.1)

    if pick % 2:
        print('picked yes!');
        yes(PINK)
        time.sleep(1)
    else:
        print('picked no!');
        no(TEAL)
        time.sleep(1)


def twinkle_show():
    pixels.brightness = TWINKLE_BRIGHTNESS
    pixels.show()
    time.sleep(.1)
    if touch.value:
        return;

def twinkle():
    # randomly choose 3 pixels
    spark1 = random.randint(0, num_pixels-1)
    spark2 = random.randint(0, num_pixels-1)
    spark3 = random.randint(0, num_pixels-1)

    # make sure that none of the chosen pixels are covered
    while spark1 in COVERED_PIXELS:
        spark1 = random.randint(0, num_pixels-1)
    while spark2 in COVERED_PIXELS:
        spark2 = random.randint(0, num_pixels-1)
    while spark3 in COVERED_PIXELS:
        spark3 = random.randint(0, num_pixels-1)

    # Control when chosen pixels turn on for dazzling effect
    pixels[spark1] = TWINKLEY
    pixels[spark2] = OFF
    pixels[spark3] = OFF
    twinkle_show()
    pixels[spark1] = TWINKLEY
    pixels[spark2] = TWINKLEY
    pixels[spark3] = OFF
    twinkle_show()
    pixels[spark1] = TWINKLEY
    pixels[spark2] = TWINKLEY
    pixels[spark3] = TWINKLEY
    twinkle_show()
    pixels[spark1] = OFF
    pixels[spark2] = TWINKLEY
    pixels[spark3] = TWINKLEY
    twinkle_show()
    pixels[spark1] = OFF
    pixels[spark2] = OFF
    pixels[spark3] = TWINKLEY
    twinkle_show()

    pixels.fill(OFF)
    pixels.show()
    time.sleep(0.6)

# Initial empty state
state = ""

while True:
    # Advertise when not connected.
    ble.start_advertising(advertisement)

    while not ble.connected:
        if touch.value:
            yes_or_no()
        else:
            twinkle()

    while ble.connected:
        # Set the state
        if uart_service.in_waiting:
            # Packet is arriving.
            packet = Packet.from_stream(uart_service)

            # set state string based on pressed button from Bluefruit app
            # and to prevent redundant hits
            if isinstance(packet, ButtonPacket) and packet.pressed:
                # UP button pressed
                if packet.button == ButtonPacket.UP and state != "chase":
                    state = "chase"
                # DOWN button
                elif packet.button == ButtonPacket.DOWN and state != "comet":
                    state = "comet"
                # 1 button
                elif packet.button == '1' and state != "rainbowchase":
                    state = "rainbowchase"
                # 2 button
                elif packet.button == '2' and state != "hello":
                    state = "hello"

        # Touch is handled as an interrupt state
        if touch.value:
            yes_or_no()

        # Act upon the state
        if state == "chase":
            chase.animate()
        elif state == "comet":
            rainbow_comet.animate()
        elif state == "rainbowchase":
            rainbow_chase.animate()
        elif state == "hello":
            pixels.fill(0)
            scroll_text(packet, SCROLL_TEXT_CUSTOM_WORD)
        else:
            chase.animate()
