# SPDX-FileCopyrightText: 2020 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

'''BLE Synth
File for the Circuit Playground Bluefruit
Amp Portion'''
from adafruit_circuitplayground.bluefruit import cpb
from adafruit_led_animation.animation import Comet, AnimationGroup,\
    AnimationSequence
import adafruit_led_animation.color as color
from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.nordic import UARTService
from adafruit_bluefruit_connect.packet import Packet
from adafruit_bluefruit_connect.color_packet import ColorPacket
from adafruit_bluefruit_connect.button_packet import ButtonPacket

#  easily call for NeoPixels to be off
off = (0, 0, 0)
#  state to debounce on CPB end
tone = False

# Setup for comet animation
COMET_SPEED = 0.04  # Lower numbers increase the animation speed
CPB_COMET_TAIL_LENGTH = 5  # The length of the comet on the Circuit Playground Bluefruit
CPB_COMET_BOUNCE = False  # Set to True to make the comet "bounce" the opposite direction on CPB

animations = AnimationSequence(
    AnimationGroup(
        Comet(cpb.pixels, COMET_SPEED, off, tail_length=CPB_COMET_TAIL_LENGTH,
              bounce=CPB_COMET_BOUNCE)))

#  note frequencies
C4 = 261.63
Csharp4 = 277.18
D4 = 293.66
Dsharp4 = 311.13
E4 = 329.63
F4 = 349.23
Fsharp4 = 369.99
G4 = 392
Gsharp4 = 415.3
A4 = 440
Asharp4 = 466.16
B4 = 493.88

#  note array
note = [C4, Csharp4, D4, Dsharp4, E4, F4,
        Fsharp4, G4, Gsharp4, A4, Asharp4, B4]

#  colors to recieve from color packet & for neopixels
color_C = color.RED
color_Csharp = color.ORANGE
color_D = color.YELLOW
color_Dsharp = color.GREEN
color_E = color.TEAL
color_F = color.CYAN
color_Fsharp = color.BLUE
color_G = color.PURPLE
color_Gsharp = color.MAGENTA
color_A = color.GOLD
color_Asharp = color.PINK
color_B = color.WHITE

#  color array
color = [color_C, color_Csharp, color_D, color_Dsharp, color_E,
         color_F, color_Fsharp, color_G, color_Gsharp, color_A,
         color_Asharp, color_B]

# Setup BLE connection
ble = BLERadio()
uart = UARTService()
advertisement = ProvideServicesAdvertisement(uart)

while True:
    #  connect via BLE
    ble.start_advertising(advertisement)  # Start advertising.
    was_connected = False
    while not was_connected or ble.connected:
        if ble.connected:  # If BLE is connected...
            was_connected = True
            #  start animations
            animations.animate()
            #  look for packets
            if uart.in_waiting:
                try:
                    packet = Packet.from_stream(uart)  # Create the packet object.
                except ValueError:
                    continue
                #  if it's a color packet:
                if isinstance(packet, ColorPacket):
                    for i in range(12):
                        colors = color[i]
                        notes = note[i]
                        #  if the packet matches one of our colors:
                        if packet.color == colors and not tone:
                            #  animate with that color
                            animations.color = colors
                            #  play matching note
                            cpb.start_tone(notes)
                            tone = True
                #  if it's a button packet aka feather's button has been released:
                elif isinstance(packet, ButtonPacket) and packet.pressed:
                    if packet.button == ButtonPacket.RIGHT and tone:
                        tone = False
                        #  stop playing the note
                        cpb.stop_tone()
                        #  turn off the neopixels but keep animation active
                        animations.color = off
