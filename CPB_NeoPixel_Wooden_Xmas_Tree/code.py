# SPDX-FileCopyrightText: 2019 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import random
import board
import neopixel
import adafruit_fancyled.adafruit_fancyled as fancy
from adafruit_bluefruit_connect.packet import Packet
from adafruit_bluefruit_connect.button_packet import ButtonPacket
from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.nordic import UARTService

# setting up # of neopixels
TREE_LEDS = 12
CPX_LEDS = 10
#  setting up pins for neopixels
TREE_PIN = board.A1
CPX_PIN = board.D8

#  neopixel setup
tree = neopixel.NeoPixel(TREE_PIN, TREE_LEDS, brightness=0.5, auto_write=False)
cpx = neopixel.NeoPixel(CPX_PIN, CPX_LEDS, brightness=0.1, auto_write=False)

#  BLE setup
ble = BLERadio()
uart = UARTService()
advertisement = ProvideServicesAdvertisement(uart)
advertising = False

#  to turn neopixels off
OFF = (0, 0, 0)

#  fancyLED color palettes

fairy_palette = [fancy.CRGB(1.0, 0.0, 0.0),
                 fancy.CRGB(1.0, 0.5, 0.0),
                 fancy.CRGB(0.0, 0.5, 0.0),
                 fancy.CRGB(0.0, 1.0, 1.0),
                 fancy.CRGB(0.0, 0.0, 1.0),
                 fancy.CRGB(0.75, 0.0, 1.0)]

merry_palette = [fancy.CRGB(1.0, 0.0, 0.0),
                 fancy.CRGB(0.0, 1.0, 0.0)]

winter_palette = [fancy.CRGB(0.0, 0.75, 0.0),
                  fancy.CRGB(0.0, 1.0, 1.0),
                  fancy.CRGB(0.75, 0.0, 1.0),
                  fancy.CRGB(1.0, 1.0, 1.0),
                  fancy.CRGB(0.0, 0.75, 0.0),
                  fancy.CRGB(0.75, 0.0, 1.0),
                  fancy.CRGB(0.0, 0.0, 1.0),
                  fancy.CRGB(0.0, 1.0, 1.0),
                  fancy.CRGB(1.0, 0.0, 1.0)]

star_palette = [fancy.CRGB(1.0, 0.75, 0.0),
                fancy.CRGB(1.0, 1.0, 1.0),
                fancy.CRGB(1.0, 0.75, 0.0),
                fancy.CRGB(0.75, 0.75, 0.75),
                fancy.CRGB(1.0, 0.75, 0.0)]

hanukkah_palette = [fancy.CRGB(0.0, 1.0, 1.0),
                    fancy.CRGB(0.0, 0.0, 1.0),
                    fancy.CRGB(1.0, 0.75, 0.0),
                    fancy.CRGB(0.0, 0.0, 1.0),
                    fancy.CRGB(1.0, 1.0, 1.0)]

#  default offset value
offset = 0

def gimel():
    for i in range(TREE_LEDS):
        color = fancy.palette_lookup(hanukkah_palette, (offset - i) / 5)
        color = fancy.gamma_adjust(color, brightness=0.3)
        tree[i] = color.pack()
    tree.show()

    for i in range(CPX_LEDS):
        color = fancy.palette_lookup(hanukkah_palette, (offset - i) / 3)
        color = fancy.gamma_adjust(color, brightness=0.3)
        cpx[i] = color.pack()
    cpx.show()

#  neopixel animations

def jazzy():
    for i in range(TREE_LEDS):
        color = fancy.palette_lookup(fairy_palette, (offset - i) / 4.8)
        color = fancy.gamma_adjust(color, brightness=0.3)
        tree[i] = color.pack()
    tree.show()

    for i in range(CPX_LEDS):
        color = fancy.palette_lookup(fairy_palette, (offset + i) / 4)
        color = fancy.gamma_adjust(color, brightness=0.3)
        cpx[i] = color.pack()
    cpx.show()

def latkes():
    for i in range(TREE_LEDS):
        color = fancy.palette_lookup(hanukkah_palette, (offset - 24) / TREE_LEDS)
        color = fancy.gamma_adjust(color, brightness=0.3)
        tree[i] = color.pack()
    tree.show()

    for i in range(CPX_LEDS):
        color = fancy.palette_lookup(hanukkah_palette, (offset - 20) / CPX_LEDS)
        color = fancy.gamma_adjust(color, brightness=0.3)
        cpx[i] = color.pack()
    cpx.show()

def twinkle():
    for i in range(60):
        color = fancy.palette_lookup(fairy_palette, offset + i / CPX_LEDS)
        color = fancy.gamma_adjust(color, brightness=0.25)
        p = random.randint(0, (CPX_LEDS - 1))
        cpx[p] = color.pack()
    cpx.show()

    for i in range(60):
        color = fancy.palette_lookup(fairy_palette, offset + i / TREE_LEDS)
        color = fancy.gamma_adjust(color, brightness=0.25)
        p = random.randint(0, (TREE_LEDS - 1))
        tree[p] = color.pack()
    tree.show()

def merry():
    for i in range(TREE_LEDS):
        color = fancy.palette_lookup(merry_palette, (offset + i) / (TREE_LEDS / 2))
        color = fancy.gamma_adjust(color, brightness=0.25)
        tree[i] = color.pack()
    tree.show()

    for i in range(60):
        color = fancy.palette_lookup(star_palette, (offset + i) / CPX_LEDS)
        color = fancy.gamma_adjust(color, brightness=0.25)
        p = random.randint(0, (CPX_LEDS - 1))
        cpx[p] = color.pack()
    cpx.show()

def festive():
    for i in range(TREE_LEDS):
        color = fancy.palette_lookup(merry_palette, (offset - i) / 2)
        color = fancy.gamma_adjust(color, brightness=0.25)
        tree[i] = color.pack()
    tree.show()

    for i in range(CPX_LEDS):
        color = fancy.palette_lookup(star_palette, (offset + i) / CPX_LEDS)
        color = fancy.gamma_adjust(color, brightness=0.25)
        cpx[i] = color.pack()
    cpx.show()

def fancy_swirl():
    for i in range(TREE_LEDS):
        color = fancy.palette_lookup(winter_palette, (offset + i) / TREE_LEDS)
        color = fancy.gamma_adjust(color, brightness=0.25)
        tree[i] = color.pack()
    tree.show()

    for i in range(CPX_LEDS):
        color = fancy.palette_lookup(star_palette, (offset - i) / CPX_LEDS)
        color = fancy.gamma_adjust(color, brightness=0.25)
        cpx[i] = color.pack()
    cpx.show()

#  states for different neopixel displays
fairies = False
feeling_fancy = False
feeling_festive = False
feeling_jazzy = False
feeling_merry = False
frying_latkes = False
rolling_gimel = False

while True:
    #  states to trigger the different neopixel modes
    if fairies:
        twinkle()
        offset += 0.5
    if feeling_fancy:
        fancy_swirl()
        offset += 0.05
    if feeling_festive:
        festive()
        offset += 0.05
    if feeling_jazzy:
        jazzy()
        offset += 0.08
    if feeling_merry:
        merry()
        offset += 0.12
    if frying_latkes:
        latkes()
        offset += 0.05
    if rolling_gimel:
        gimel()
        offset += 0.05

    if not ble.connected and not advertising:
        #  not connected in the app yet
        ble.start_advertising(advertisement)
        advertising = True

    if ble.connected:
        # after connected via app
        advertising = False
        if uart.in_waiting:
            #  waiting for input from app
            packet = Packet.from_stream(uart)
            if isinstance(packet, ButtonPacket):
                #  if buttons in the app are pressed
                if packet.pressed:
                    #  fairies
                    if packet.button == ButtonPacket.UP:
                        fairies = True
                        feeling_fancy = False
                        feeling_festive = False
                        feeling_jazzy = False
                        feeling_merry = False
                        frying_latkes = False
                        rolling_gimel = False
                    #  fancy
                    if packet.button == ButtonPacket.LEFT:
                        fairies = False
                        feeling_fancy = True
                        feeling_festive = False
                        feeling_jazzy = False
                        feeling_merry = False
                        frying_latkes = False
                        rolling_gimel = False
                    #  festive
                    if packet.button == ButtonPacket.RIGHT:
                        fairies = False
                        feeling_fancy = False
                        feeling_festive = True
                        feeling_jazzy = False
                        feeling_merry = False
                        frying_latkes = False
                        rolling_gimel = False
                    #  jazzy
                    if packet.button == ButtonPacket.DOWN:
                        fairies = False
                        feeling_fancy = False
                        feeling_festive = False
                        feeling_jazzy = True
                        feeling_merry = False
                        frying_latkes = False
                        rolling_gimel = False
                    #  merry
                    if packet.button == ButtonPacket.BUTTON_1:
                        fairies = False
                        feeling_fancy = False
                        feeling_festive = False
                        feeling_jazzy = False
                        feeling_merry = True
                        frying_latkes = False
                        rolling_gimel = False
                    #  latkes
                    if packet.button == ButtonPacket.BUTTON_2:
                        fairies = False
                        feeling_fancy = False
                        feeling_festive = False
                        feeling_jazzy = False
                        feeling_merry = False
                        frying_latkes = True
                        rolling_gimel = False
                    #  gimel
                    if packet.button == ButtonPacket.BUTTON_3:
                        fairies = False
                        feeling_fancy = False
                        feeling_festive = False
                        feeling_jazzy = False
                        feeling_merry = False
                        frying_latkes = False
                        rolling_gimel = True
                    #  off
                    if packet.button == ButtonPacket.BUTTON_4:
                        fairies = False
                        feeling_fancy = False
                        feeling_festive = False
                        feeling_jazzy = False
                        feeling_merry = False
                        frying_latkes = False
                        rolling_gimel = False
                        cpx.fill(OFF)
                        tree.fill(OFF)
                        tree.show()
                        cpx.show()
