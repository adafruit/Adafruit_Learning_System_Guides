"""
LED Sunflower Mobile with Circuit Playground Bluefruit
Full tutorial:
https://learn.adafruit.com/sound-reactive-sunflower-baby-crib-mobile-with-bluetooth-control
Adafruit invests time and resources providing this open source code.
Please support Adafruit and open source hardware by purchasing
products from Adafruit!
Written by Erin St Blaine & Dan Halbert for Adafruit Industries
Copyright (c) 2020-2021 Adafruit Industries
Licensed under the MIT license.
All text above must be included in any redistribution.

"""

import array
import math
import audiobusio
import board
import neopixel
from digitalio import DigitalInOut, Direction, Pull

from adafruit_bluefruit_connect.packet import Packet
from adafruit_bluefruit_connect.button_packet import ButtonPacket
from adafruit_bluefruit_connect.color_packet import ColorPacket
from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.nordic import UARTService

from adafruit_led_animation.helper import PixelMap
from adafruit_led_animation.sequence import AnimationSequence
from adafruit_led_animation.group import AnimationGroup
from adafruit_led_animation.animation.sparkle import Sparkle
from adafruit_led_animation.animation.rainbow import Rainbow
from adafruit_led_animation.animation.rainbowchase import RainbowChase
from adafruit_led_animation.animation.rainbowcomet import RainbowComet
from adafruit_led_animation.animation.chase import Chase
from adafruit_led_animation.animation.comet import Comet
from adafruit_led_animation.animation.solid import Solid
from adafruit_led_animation.color import colorwheel
from adafruit_led_animation.color import (
    BLACK,
    RED,
    ORANGE,
    BLUE,
    PURPLE,
    WHITE,
)

YELLOW = (25, 15, 0)

# Setup BLE
ble = BLERadio()
uart = UARTService()
advertisement = ProvideServicesAdvertisement(uart)

# Color of the peak pixel.
PEAK_COLOR = (100, 0, 255)
# Number of total pixels - 10 build into Circuit Playground
NUM_PIXELS = 30


fairylights = DigitalInOut(board.A4)
fairylights.direction = Direction.OUTPUT
fairylights.value = True

# Exponential scaling factor.
# Should probably be in range -10 .. 10 to be reasonable.
CURVE = 2
SCALE_EXPONENT = math.pow(10, CURVE * -0.1)

# Number of samples to read at once.
NUM_SAMPLES = 160

brightness_increment = 0

# Restrict value to be between floor and ceiling.
def constrain(value, floor, ceiling):
    return max(floor, min(value, ceiling))


# Scale input_value between output_min and output_max, exponentially.
def log_scale(input_value, input_min, input_max, output_min, output_max):
    normalized_input_value = (input_value - input_min) / \
                             (input_max - input_min)
    return output_min + \
        math.pow(normalized_input_value, SCALE_EXPONENT) \
        * (output_max - output_min)


# Remove DC bias before computing RMS.
def normalized_rms(values):
    minbuf = int(mean(values))
    samples_sum = sum(
        float(sample - minbuf) * (sample - minbuf)
        for sample in values
    )

    return math.sqrt(samples_sum / len(values))


def mean(values):
    return sum(values) / len(values)


def volume_color(volume):
    return 200, volume * (255 // NUM_PIXELS), 0


# Main program

# Set up NeoPixels and turn them all off.
pixels = neopixel.NeoPixel(board.A1, NUM_PIXELS, brightness=0.1, auto_write=False)
pixels.fill(0)
pixels.show()

mic = audiobusio.PDMIn(board.MICROPHONE_CLOCK, board.MICROPHONE_DATA,
                       sample_rate=16000, bit_depth=16)

# Record an initial sample to calibrate. Assume it's quiet when we start.
samples = array.array('H', [0] * NUM_SAMPLES)
mic.record(samples, len(samples))
# Set lowest level to expect, plus a little.
input_floor = normalized_rms(samples) + 30
# OR: used a fixed floor
# input_floor = 50

# You might want to print the input_floor to help adjust other values.
print(input_floor)

# Corresponds to sensitivity: lower means more pixels light up with lower sound
# Adjust this as you see fit.
input_ceiling = input_floor + 100

peak = 0

# Cusomize LED Animations  ------------------------------------------------------
rainbow = Rainbow(pixels, speed=0, period=6, name="rainbow", step=2.4)
rainbow_chase = RainbowChase(pixels, speed=0.1, size=5, spacing=5, step=5)
chase = Chase(pixels, speed=0.2, color=ORANGE, size=2, spacing=6)
rainbow_comet = RainbowComet(pixels, speed=0.1, tail_length=30, bounce=True)
rainbow_comet2 = RainbowComet(
    pixels, speed=0.1, tail_length=104, colorwheel_offset=80, bounce=True
    )
rainbow_comet3 = RainbowComet(
    pixels, speed=0, tail_length=25, colorwheel_offset=80, step=4, bounce=False
    )
strum = RainbowComet(
    pixels, speed=0.1, tail_length=25, bounce=False, colorwheel_offset=50, step=4
    )
sparkle = Sparkle(pixels, speed=0.1, color=BLUE, num_sparkles=10)
sparkle2 = Sparkle(pixels, speed=0.5, color=PURPLE, num_sparkles=4)
off = Solid(pixels, color=BLACK)

# Animations Playlist - reorder as desired. AnimationGroups play at the same time
animations = AnimationSequence(

    rainbow_comet2, #
    rainbow_comet, #
    chase, #
    rainbow_chase, #
    rainbow, #

    AnimationGroup(
        sparkle,
        strum,
        ),
    AnimationGroup(
        sparkle2,
        rainbow_comet3,
        ),
    off,
    auto_clear=True,
    auto_reset=True,
)


MODE = 1
LASTMODE = 1 # start up in sound reactive mode
i = 0
# Are we already advertising?
advertising = False

while True:
    animations.animate()
    if not ble.connected and not advertising:
        ble.start_advertising(advertisement)
        advertising = True

    # Are we connected via Bluetooth now?
    if ble.connected:
        # Once we're connected, we're not advertising any more.
        advertising = False
        # Have we started to receive a packet?
        if uart.in_waiting:
            packet = Packet.from_stream(uart)
            if isinstance(packet, ColorPacket):
                # Set all the pixels to one color and stay there.
                pixels.fill(packet.color)
                pixels.show()
                MODE = 2
            elif isinstance(packet, ButtonPacket):
                if packet.pressed:
                    if packet.button == ButtonPacket.BUTTON_1:
                        animations.activate(1)
                    elif packet.button == ButtonPacket.BUTTON_2:
                        MODE = 1
                        animations.activate(2)
                    elif packet.button == ButtonPacket.BUTTON_3:
                        MODE = 1
                        animations.activate(3)
                    elif packet.button == ButtonPacket.BUTTON_4:
                        MODE = 4

                    elif packet.button == ButtonPacket.UP:
                        pixels.brightness = pixels.brightness + 0.1
                        pixels.show()
                        if pixels.brightness > 1:
                            pixels.brightness = 1
                    elif packet.button == ButtonPacket.DOWN:
                        pixels.brightness = pixels.brightness - 0.1
                        pixels.show()
                        if pixels.brightness < 0.1:
                            pixels.brightness = 0.1
                    elif packet.button == ButtonPacket.RIGHT:
                        MODE = 1
                        animations.next()
                    elif packet.button == ButtonPacket.LEFT:
                        animations.activate(7)
            animations.animate()

        if MODE == 2:
            animations.freeze()
        if MODE == 4:
            animations.freeze()
            pixels.fill(YELLOW)
            mic.record(samples, len(samples))
            magnitude = normalized_rms(samples)
            # You might want to print this to see the values.
            #print(magnitude)

            # Compute scaled logarithmic reading in the range 0 to NUM_PIXELS
            c = log_scale(constrain(magnitude, input_floor, input_ceiling),
                          input_floor, input_ceiling, 0, NUM_PIXELS)

            # Light up pixels that are below the scaled and interpolated magnitude.
            #pixels.fill(0)
            for i in range(NUM_PIXELS):
                if i < c:
                    pixels[i] = volume_color(i)
                # Light up the peak pixel and animate it slowly dropping.
                if c >= peak:
                    peak = min(c, NUM_PIXELS - 1)
                elif peak > 0:
                    peak = peak - 0.01
                if peak > 0:
                    pixels[int(peak)] = PEAK_COLOR
            pixels.show()
