"""
Bluetooth Controlled Room Lights using a Circuit Playground Bluetooth
   Scroll between 7 modes and control brightness with your smartphone via Bluetooth
   Full tutorial https://learn.adafruit.com/easy-no-solder-bluetooth-controlled-room-lights/overview
Code by Kattni Rembor & Erin St Blaine for Adafruit Industries
Adafruit invests time and resources to bring you this code! Please support our shop!
"""

# pylint: disable=attribute-defined-outside-init
# pylint: disable=too-few-public-methods

import board
import neopixel
from adafruit_led_animation.animation.solid import Solid
from adafruit_led_animation.animation.comet import Comet
from adafruit_led_animation.animation.rainbow import Rainbow
from adafruit_led_animation.animation.rainbowcomet import RainbowComet
from adafruit_led_animation.animation.sparkle import Sparkle
from adafruit_led_animation.animation.sparklepulse import SparklePulse
from adafruit_led_animation.sequence import AnimationSequence
from adafruit_led_animation.group import AnimationGroup
from adafruit_led_animation.animation import Animation
from adafruit_led_animation.sequence import AnimateOnce
from adafruit_led_animation.color import (
    AMBER,
    ORANGE,
    WHITE,
    RED,
    BLACK,
    colorwheel,
)


from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.nordic import UARTService

from adafruit_bluefruit_connect.packet import Packet
from adafruit_bluefruit_connect.button_packet import ButtonPacket
from adafruit_bluefruit_connect.color_packet import ColorPacket

NUM_LEDS = 240  # change to reflect your LED strip
NEOPIXEL_PIN = board.A1  # change to reflect your wiring

# Declare a NeoPixel object on NEOPIXEL_PIN with NUM_LEDS pixels,
# no auto-write.
# Set brightness to max, we'll control it later in the code
pixels = neopixel.NeoPixel(
    NEOPIXEL_PIN,
    NUM_LEDS,
    brightness=1.0,
    auto_write=False,
    # pixel_order=(1,0,2,3) #uncomment if using RGBW NeoPixels
)


ble = BLERadio()
uart_service = UARTService()
advertisement = ProvideServicesAdvertisement(uart_service)


class RainbowFade(Animation):
    """ fades the entire strip through the whole spectrum """

    _color_index = 150  # choose start color (0-255)

    def __init__(self, pixel_object, speed, name):  # define animation
        super().__init__(pixel_object, speed=speed, color=WHITE, name=name)

    def draw(self):  # draw the animation
        """ fades the entire strip through the whole spectrum """
        self.color = colorwheel(self._color_index + 1)
        self._color_index = (self._color_index + 1) % 256
        self.fill(self.color)


# ANIMATION DEFINITIONS --
#    create as many animations as you'd like and define their attributes here.
#    They can be a single line or a group of animations - the groups will play
#    at the same time, overlaid on top of each other.


readingLight = Solid(pixels, color=0xFF7D13)  # warm white color HEX code
brightWhite = Solid(pixels, color=(150, 150, 150))
rainbow = Rainbow(pixels, speed=0.1, period=10, step=0.5)
rainbowfade = RainbowFade(pixels, speed=0.4, name="rainbowfade")
powerup = RainbowComet(pixels, speed=0, tail_length=50, bounce=False)
off = Solid(pixels, color=BLACK)

# startup animation will play just once
startup = AnimateOnce(powerup)

# starrynight and fire are animation groups with layered effects.
starrynight = AnimationGroup(
    SparklePulse(pixels, speed=0.01, color=(0, 0, 150), period=1),
    Comet(pixels, speed=0, tail_length=8, color=(150, 150, 150), bounce=False),
)

fire = AnimationGroup(
    Comet(pixels, speed=0, tail_length=1, color=BLACK),
    Sparkle(pixels, speed=0.05, num_sparkles=10, color=AMBER),
    Sparkle(pixels, speed=0.05, num_sparkles=10, color=RED),
    Sparkle(pixels, speed=0.05, num_sparkles=20, color=ORANGE),
    Sparkle(pixels, speed=0.05, num_sparkles=5, color=0xFF7D13),
    Sparkle(pixels, speed=0.05, num_sparkles=10, color=BLACK),
)

# Here is the animation playlist where you set the order of modes

animations = AnimationSequence(
    readingLight, fire, rainbow, starrynight, rainbowfade, brightWhite, auto_clear=True,
)


MODE = 0

while True:
    if MODE == 0:  # If currently off...
        startup.animate()
        while startup.animate():
            pass
        MODE = 1
    # Advertise when not connected

    elif MODE >= 1:  # If not OFF MODE...
        ble.start_advertising(advertisement)
        while not ble.connected:
            if MODE == 2:
                pass
            elif MODE == 1:
                animations.animate()
    # Now we're connected

    while ble.connected:
        if uart_service.in_waiting:
            packet = Packet.from_stream(uart_service)
            # Color Picker Functionality
            if isinstance(packet, ColorPacket):
                MODE = 2
                # Set all the pixels to one color and stay there.
                pixels.fill(packet.color)
                pixels.show()
            # Control Pad Functionality
            elif isinstance(packet, ButtonPacket):
                if packet.pressed:
                    if packet.button == ButtonPacket.BUTTON_1:
                        MODE = 1
                        animations.activate(1)
                    elif packet.button == ButtonPacket.BUTTON_2:
                        MODE = 1
                        animations.activate(2)
                    elif packet.button == ButtonPacket.BUTTON_3:
                        MODE = 1
                        animations.activate(3)
                    elif packet.button == ButtonPacket.BUTTON_4:
                        MODE = 1
                        animations.activate(4)
                    # change the mode with right arrow
                    elif packet.button == ButtonPacket.RIGHT:
                        MODE = 1
                        animations.next()
                    elif packet.button == ButtonPacket.LEFT:
                        MODE = 4
                        off.animate()
                    # change the brightness with up and down arrows
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
        if MODE == 1:
            animations.animate()
        if MODE == 4:
            animations.freeze()
