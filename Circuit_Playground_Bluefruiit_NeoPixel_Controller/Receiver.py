"""
Receiver code for Circuit Playground Bluefruit NeoPixel Animation and Color controller. To be used
with control code.
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

strip_pixels = neopixel.NeoPixel(board.A1, 30, auto_write=False)

ble = BLERadio()
uart = UARTService()
advertisement = ProvideServicesAdvertisement(uart)

animations = AnimationSequence(
    AnimationGroup(
        Blink(cpb.pixels, 0.5, color.RED),
        Blink(strip_pixels, 0.5, color.RED),
        sync=True
    ),
    AnimationGroup(
        Comet(cpb.pixels, 0.05, color.MAGENTA, tail_length=5),
        Comet(strip_pixels, 0.03, color.MAGENTA, tail_length=15)
    ),
    AnimationGroup(
        Sparkle(cpb.pixels, 0.05, color.PURPLE),
        Sparkle(strip_pixels, 0.05, color.PURPLE)
    ),
)

animation_color = None
mode = 0
blanked = False
while True:
    ble.start_advertising(advertisement)
    was_connected = False
    while not was_connected or ble.connected:
        if not blanked:
            animations.animate()
        if ble.connected:
            was_connected = True
            if uart.in_waiting:
                try:
                    packet = Packet.from_stream(uart)
                except ValueError as e:
                    continue
                if isinstance(packet, ColorPacket):
                    if mode == 0:
                        animations.change_color(packet.color)
                        print("Color:", packet.color)
                        animation_color = packet.color
                    elif mode == 1:
                        animations.change_color(animation_color)
                        print("Color:", animation_color)
                elif isinstance(packet, ButtonPacket):
                    if packet.button == ButtonPacket.BUTTON_1:
                        print("Controller switch is to the", "left: LEDs off!" if packet.pressed
                              else "right: LEDs on!")
                        if packet.pressed and not blanked:
                            animations.fill(color.BLACK)
                        blanked = packet.pressed
                    if packet.pressed:
                        if packet.button == ButtonPacket.LEFT:
                            print("A pressed: animation mode changed.")
                            animations.next()
                        elif packet.button == ButtonPacket.RIGHT:
                            mode += 1
                            if mode == 1:
                                print("B pressed: color frozen!")
                            if mode > 1:
                                mode = 0
                                print("B pressed: color changing!")
