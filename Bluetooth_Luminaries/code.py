# SPDX-FileCopyrightText: 2019 Phillip Burgess for Adafruit Industries
# SPDX-FileCopyrightText: 2019 Dan Halbert for Adafruit Industries
# SPDX-FileCopyrightText: 2019 Erin St Blaine for Adafruit Industries
#
# SPDX-License-Identifier: MIT

""" FancyLED Palette and Color Picker Control with BlueFruit App
    Code by Phil Burgess, Dan Halbert & Erin St Blaine for Adafruit Industries
"""
import board
import neopixel
import touchio
import adafruit_fancyled.adafruit_fancyled as fancy
from adafruit_bluefruit_connect.packet import Packet
from adafruit_bluefruit_connect.button_packet import ButtonPacket
from adafruit_bluefruit_connect.color_packet import ColorPacket


from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.nordic import UARTService



NUM_LEDS = 24             # change to reflect your total number of ring LEDs
RING_PIN = board.A1       # change to reflect your wiring
CPX_PIN = board.D8        # CPX Neopixels live on pin D8

touch_A2 = touchio.TouchIn(board.A2)
touch_A3 = touchio.TouchIn(board.A3)
touch_A4 = touchio.TouchIn(board.A4)
touch_A5 = touchio.TouchIn(board.A5)
touch_A6 = touchio.TouchIn(board.A6)
touch_TX = touchio.TouchIn(board.TX)

# Palettes can have any number of elements in various formats
# check https://learn.adafruit.com/fancyled-library-for-circuitpython/colors
# for more info
# Declare a 6-element RGB rainbow palette
PALETTE_RAINBOW = [fancy.CRGB(1.0, 0.0, 0.0),  # Red
                   fancy.CRGB(0.5, 0.3, 0.0),  # Orange
                   fancy.CRGB(0.5, 0.5, 0.0),  # Yellow
                   fancy.CRGB(0.3, 0.7, 0.0),  # Yellow Green
                   fancy.CRGB(0.0, 1.0, 0.0),  # Green
                   fancy.CRGB(0.0, 0.7, 0.3),  # Teal
                   fancy.CRGB(0.0, 0.5, 0.5),  # Cyan
                   fancy.CRGB(0.0, 0.3, 0.7),  # Blue
                   fancy.CRGB(0.0, 0.0, 1.0),  # Blue
                   fancy.CRGB(0.5, 0.0, 0.5),  # Magenta
                   fancy.CRGB(0.7, 0.0, 0.3)]  # Purple

# Reading Lamp mode - Warm Yellow
PALETTE_BRIGHT = [fancy.CRGB(255, 183, 55)]

# Black Only palette for "off" mode
PALETTE_DARK = [fancy.CRGB(0, 0, 0)]

# Declare a FIRE palette
PALETTE_FIRE = [fancy.CRGB(160, 30, 0),  # Reds and Yellows
                fancy.CRGB(27, 65, 0),
                fancy.CRGB(0, 0, 0),
                fancy.CRGB(224, 122, 0),
                fancy.CRGB(0, 0, 0),
                fancy.CRGB(250, 80, 0),
                fancy.CRGB(0, 0, 0),
                fancy.CRGB(0, 0, 0),
                fancy.CRGB(200, 40, 0)]

# Declare a NeoPixel object on NEOPIXEL_PIN with NUM_LEDS pixels,
# no auto-write.
# Set brightness to max because we'll be using FancyLED's brightness control.
ring = neopixel.NeoPixel(RING_PIN, NUM_LEDS, brightness=1.0, auto_write=False)
cpx = neopixel.NeoPixel(CPX_PIN, NUM_LEDS, brightness=1.0, auto_write=False)

offset = 0  # Positional offset into color palette to get it to 'spin'
offset_increment = 6
OFFSET_MAX = 1000000

# Setup BLE
ble = BLERadio()
uart = UARTService()
advertisement = ProvideServicesAdvertisement(uart)


def set_palette(palette):
    for i in range(NUM_LEDS):
        # Load each pixel's color from the palette using an offset, run it
        # through the gamma function, pack RGB value and assign to pixel.
        color = fancy.palette_lookup(palette, (offset + i) / NUM_LEDS)
        color = fancy.gamma_adjust(color, brightness=1.0)
        ring[i] = color.pack()
    ring.show()

    for i in range(NUM_LEDS):
        # Load each pixel's color from the palette using an offset, run it
        # through the gamma function, pack RGB value and assign to pixel.
        color = fancy.palette_lookup(palette, (offset + i) / NUM_LEDS)
        color = fancy.gamma_adjust(color, brightness=1.0)
        cpx[i] = color.pack()
    cpx.show()

# set initial palette to run on startup
palette_choice = PALETTE_FIRE

# True if cycling a palette
cycling = True

# Are we already advertising?
advertising = False


while True:

    if cycling:
        set_palette(palette_choice)
        offset = (offset + offset_increment) % OFFSET_MAX

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
                cycling = False
                # Set all the pixels to one color and stay there.
                ring.fill(packet.color)
                cpx.fill(packet.color)
                ring.show()
                cpx.show()
            elif isinstance(packet, ButtonPacket):
                cycling = True
                if packet.pressed:
                    if packet.button == ButtonPacket.BUTTON_1:
                        palette_choice = PALETTE_DARK
                    elif packet.button == ButtonPacket.BUTTON_2:
                        palette_choice = PALETTE_BRIGHT
                    elif packet.button == ButtonPacket.BUTTON_3:
                        palette_choice = PALETTE_FIRE
                        offset_increment = 6
                    elif packet.button == ButtonPacket.BUTTON_4:
                        palette_choice = PALETTE_RAINBOW
                        offset_increment = 1

                # change the speed of the animation by incrementing offset
                    elif packet.button == ButtonPacket.UP:
                        offset_increment += 1
                    elif packet.button == ButtonPacket.DOWN:
                        offset_increment -= 1

    # Whether or not we're connected via Bluetooth,
    # we also want to handle touch inputs.
    if touch_A2.value:
        cycling = True
        palette_choice = PALETTE_DARK
    elif touch_A3.value:
        cycling = True
        palette_choice = PALETTE_BRIGHT
    elif touch_A4.value:
        cycling = True
        palette_choice = PALETTE_FIRE
        offset_increment = 6
    elif touch_A5.value:
        cycling = True
        palette_choice = PALETTE_RAINBOW
        offset_increment = 1
    # Also check for touch speed control
#    if touch_A6.value:
#        offset_increment += 1
#    if touch_TX.value:
#        offset_increment -= 1
