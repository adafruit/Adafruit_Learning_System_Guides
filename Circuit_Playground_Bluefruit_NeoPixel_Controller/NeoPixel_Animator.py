"""
NeoPixel Animator code for Circuit Playground Bluefruit NeoPixel Animation and Color Remote Control.
To be used with another Circuit Playground Bluefruit running the Remote Control code.
"""

import board
import neopixel
from adafruit_circuitplayground.bluefruit import cpb
from adafruit_led_animation.animation import Blink, Comet, Sparkle, AnimationGroup,\
    AnimationSequence
import adafruit_led_animation.color as color

from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.nordic import UARTService

from adafruit_bluefruit_connect.packet import Packet
from adafruit_bluefruit_connect.color_packet import ColorPacket
from adafruit_bluefruit_connect.button_packet import ButtonPacket

# The number of NeoPixels in the externally attached strip
# If using two strips connected to the same pin, count only one strip for this number!
STRIP_PIXEL_NUMBER = 30

# Setup for blink animation
BLINK_SPEED = 0.5  # Lower numbers increase the animation speed
BLINK_INITIAL_COLOR = color.RED  # Color before Remote Control is connected

# Setup for comet animation
COMET_SPEED = 0.03  # Lower numbers increase the animation speed
CPB_COMET_TAIL_LENGTH = 5  # The length of the comet on the Circuit Playground Bluefruit
STRIP_COMET_TAIL_LENGTH = 15  # The length of the comet on the NeoPixel strip
CPB_COMET_BOUNCE = False  # Set to True to make the comet "bounce" the opposite direction on CPB
STRIP_COMET_BOUNCE = True  # Set to False to stop comet from "bouncing" on NeoPixel strip

# Setup for sparkle animation
SPARKLE_SPEED = 0.03  # Lower numbers increase the animation speed

# Create the NeoPixel strip
strip_pixels = neopixel.NeoPixel(board.A1, STRIP_PIXEL_NUMBER, auto_write=False)

# Setup BLE connection
ble = BLERadio()
uart = UARTService()
advertisement = ProvideServicesAdvertisement(uart)

# Setup animations
animations = AnimationSequence(
    AnimationGroup(
        Blink(cpb.pixels, BLINK_SPEED, BLINK_INITIAL_COLOR),
        Blink(strip_pixels, BLINK_SPEED, BLINK_INITIAL_COLOR),
        sync=True
    ),
    AnimationGroup(
        Comet(cpb.pixels, COMET_SPEED, color.MAGENTA, tail_length=CPB_COMET_TAIL_LENGTH,
              bounce=CPB_COMET_BOUNCE),
        Comet(strip_pixels, COMET_SPEED, color.MAGENTA, tail_length=STRIP_COMET_TAIL_LENGTH,
              bounce=STRIP_COMET_BOUNCE)
    ),
    AnimationGroup(
        Sparkle(cpb.pixels, SPARKLE_SPEED, color.PURPLE),
        Sparkle(strip_pixels, SPARKLE_SPEED, color.PURPLE)
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
            if uart.in_waiting:  # Check to see if any data is available from the Remote Control.
                try:
                    packet = Packet.from_stream(uart)  # Create the packet object.
                except ValueError:
                    continue
                if isinstance(packet, ColorPacket):  # If the packet is color packet...
                    if mode == 0:  # And mode is 0...
                        animations.color = packet.color  # Update the animation to the color.
                        # Uncomment below to see the color tuple printed to the serial console.
                        # print("Color:", packet.color)
                        animation_color = packet.color  # Keep track of the current color...
                    elif mode == 1:  # Because if mode is 1...
                        animations.color = animation_color  # Freeze the animation color.
                        # Uncomment below to see the color tuple printed to the serial console.
                        # print("Color:", animation_color)
                elif isinstance(packet, ButtonPacket):  # If the packet is a button packet...
                    # Check to see if it's BUTTON_1 (which is being sent by the slide switch)
                    if packet.button == ButtonPacket.BUTTON_1:
                        if packet.pressed:  # If Remote Control switch is to the left...
                            print("Remote Control switch is to the left: LEDs off!")
                        else:  # If the Remote Control switch is to the right...
                            print("Remote Control switch is to the right: LEDs on!")
                        # If the Remote Control switch is moved from right to left...
                        if packet.pressed and not blanked:
                            animations.fill(color.BLACK)  # Turn off the LEDs.
                        blanked = packet.pressed  # Track the state of the slide switch.
                    if packet.pressed:  # If the buttons on the Remote Control are pressed...
                        if packet.button == ButtonPacket.LEFT:  # If button A is pressed...
                            print("A pressed: animation mode changed.")
                            animations.next()  # Change to the next animation.
                        elif packet.button == ButtonPacket.RIGHT:  # If button B is pressed...
                            mode += 1  # Increase the mode by 1.
                            if mode == 1:  # If mode is 1, print the following:
                                print("B pressed: color frozen!")
                            if mode > 1:  # If mode is > 1...
                                mode = 0  # Set mode to 0, and print the following:
                                print("B pressed: color changing!")
