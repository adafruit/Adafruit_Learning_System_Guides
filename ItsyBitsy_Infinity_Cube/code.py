"""
Code for ItsyBitsy nRF52840 Infinity Cube.
"""

import board
import neopixel
from adafruit_led_animation.animation.comet import Comet
from adafruit_led_animation.animation.sparkle import Sparkle
from adafruit_led_animation.group import AnimationGroup
from adafruit_led_animation.sequence import AnimationSequence
import adafruit_led_animation.color as color

from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.nordic import UARTService

from adafruit_bluefruit_connect.packet import Packet
from adafruit_bluefruit_connect.color_packet import ColorPacket
from adafruit_bluefruit_connect.button_packet import ButtonPacket

# The number of NeoPixels in the externally attached strip
# If using two strips connected to the same pin, count only one strip for this number!
STRIP_PIXEL_NUMBER = 43

# Setup for comet animation
COMET_SPEED = 0.05  # Lower numbers increase the animation speed
STRIP_COMET_TAIL_LENGTH = 10  # The length of the comet on the NeoPixel strip
STRIP_COMET_BOUNCE = False  # Set to False to stop comet from "bouncing" on NeoPixel strip

# Setup for sparkle animation
SPARKLE_SPEED = 0.1  # Lower numbers increase the animation speed

# Create the NeoPixel strip
strip_pixels = neopixel.NeoPixel(board.D5, STRIP_PIXEL_NUMBER, auto_write=False)

# Setup BLE connection
ble = BLERadio()
uart = UARTService()
advertisement = ProvideServicesAdvertisement(uart)

# Setup animations
animations = AnimationSequence(
    AnimationGroup(
        Sparkle(strip_pixels, SPARKLE_SPEED, color.TEAL)
    ),
    AnimationGroup(
        Comet(strip_pixels, COMET_SPEED, color.TEAL, tail_length=STRIP_COMET_TAIL_LENGTH,
              bounce=STRIP_COMET_BOUNCE)
    ),
)

animation_color = None
mode = 0
blanked = False

while True:
    ble.start_advertising(advertisement)  # Start advertising.
    was_connected = False
    while not was_connected or ble.connected:
        if not blanked:  # If LED-off signal is not being sent...
            animations.animate()  # Run the animations.
        if ble.connected:  # If BLE is connected...
            was_connected = True
            if uart.in_waiting:  # Check to see if any data is available.
                try:
                    packet = Packet.from_stream(uart)  # Create the packet object.
                except ValueError:
                    continue
                if isinstance(packet, ColorPacket):  # If the packet is color packet...
                    if mode == 0:  # And mode is 0...
                        animations.color = packet.color  # Update the animation to the color.
                        print("Color:", packet.color)
                        animation_color = packet.color  # Keep track of the current color...
                    elif mode == 1:  # Because if mode is 1...
                        animations.color = animation_color  # Freeze the animation color.
                        print("Color:", animation_color)
                elif isinstance(packet, ButtonPacket):  # If the packet is a button packet...
                    if packet.pressed:  # If the buttons in the app are pressed...
                        if packet.button == ButtonPacket.LEFT:  # If left arrow is pressed...
                            print("A pressed: animation mode changed.")
                            animations.next()  # Change to the next animation.
                        elif packet.button == ButtonPacket.RIGHT:  # If right arrow is pressed...
                            mode += 1  # Increase the mode by 1.
                            if mode == 1:  # If mode is 1, print the following:
                                print("Right pressed: color frozen!")
                            if mode > 1:  # If mode is > 1...
                                mode = 0  # Set mode to 0, and print the following:
                                print("Right pressed: color changing!")
