# SPDX-FileCopyrightText: Prof. John Gallaugher
# SPDX-FileCopyrightText: 2019 Noe Ruiz for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# Code written by Prof. John Gallaugher, modified by Noe Ruiz for Adafruit Industries
# Adafruit Circuit Playground Express Bluefruit

import time
import board
import digitalio
import neopixel

from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.nordic import UARTService

from audiopwmio import PWMAudioOut as AudioOut
from audiocore import WaveFile

from adafruit_bluefruit_connect.packet import Packet
from adafruit_bluefruit_connect.color_packet import ColorPacket
from adafruit_bluefruit_connect.button_packet import ButtonPacket

# setup pixels
pixels = neopixel.NeoPixel(board.NEOPIXEL, 10, brightness=1, auto_write=True)

# name colors so you don't need to refer to numbers
RED = (255, 0, 0)
ORANGE = (255, 50, 0)
BLACK = (0, 0, 0)
GREEN = (0, 255, 0)
PURPLE = (100, 0, 255)
YELLOW = (255,230, 0)
BLUE = (0, 0, 255)
# setup bluetooth
ble = BLERadio()
uart_service = UARTService()
advertisement = ProvideServicesAdvertisement(uart_service)

# External Audio Stuff
speaker_enable = digitalio.DigitalInOut(board.SPEAKER_ENABLE)
speaker_enable.direction = digitalio.Direction.OUTPUT
speaker_enable.value = True

audio = AudioOut(board.SPEAKER)  # Speaker
wave_file = None

def play_wav(name, loop=False):
    """
    Play a WAV file in the 'sounds' directory.
    :param name: partial file name string, complete name will be built around
                 this, e.g. passing 'foo' will play file 'sounds/foo.wav'.
    :param loop: if True, sound will repeat indefinitely (until interrupted
                 by another sound).
    """
    global wave_file  # pylint: disable=global-statement
    print("playing", name)
    if wave_file:
        wave_file.close()
    try:
        wave_file = open('sounds/' + name + '.wav', 'rb') # using wave files from sounds folder
        wave = WaveFile(wave_file)
        audio.play(wave, loop=loop)
    except OSError:
        pass # we'll just skip playing then

while True:
    # set CPXb up so that it can be discovered by the app
    ble.start_advertising(advertisement)
    while not ble.connected:
        pass

    # Now we're connected

    while ble.connected:

        if uart_service.in_waiting:
            try:
                packet = Packet.from_stream(uart_service)
            except ValueError:
                continue # or pass.

            if isinstance(packet, ColorPacket): # check if a color was sent from color picker
                pixels.fill(packet.color)
            if isinstance(packet, ButtonPacket): # check if a button was pressed from control pad
                if packet.pressed:
                    if packet.button == ButtonPacket.BUTTON_1: # if button #1
                        pixels.fill(BLUE)
                        play_wav("bluefruit")
                        time.sleep(3)
                        pixels.fill(BLACK)
                    if packet.button == ButtonPacket.BUTTON_2: # if button #2
                        pixels.fill(ORANGE)
                        play_wav("halloween")
                        time.sleep(3)
                        pixels.fill(BLACK)
                    if packet.button == ButtonPacket.BUTTON_3: # if button #2
                        pixels.fill(PURPLE)
                        play_wav("muhaha")
                        time.sleep(2)
                        pixels.fill(BLACK)
                    if packet.button == ButtonPacket.BUTTON_4: # if button #2
                        pixels.fill(GREEN)
                        play_wav("neopixels")
                        time.sleep(3)
                        pixels.fill(BLACK)
                    if packet.button == ButtonPacket.UP: # if button #2
                        pixels.fill(YELLOW)
                        play_wav("organic")
                        time.sleep(2.6)
                        pixels.fill(BLACK)
                    if packet.button == ButtonPacket.DOWN: # if button #2
                        pixels.fill(PURPLE)
                        play_wav("python")
                        time.sleep(2)
                        pixels.fill(BLACK)
                    if packet.button == ButtonPacket.LEFT: # if button #2
                        pixels.fill(GREEN)
                        play_wav("smell")
                        time.sleep(2.5)
                        pixels.fill(BLACK)
                    if packet.button == ButtonPacket.RIGHT: # if button #2
                        pixels.fill(ORANGE)
                        play_wav("who")
                        time.sleep(2)
                        pixels.fill(BLACK)
