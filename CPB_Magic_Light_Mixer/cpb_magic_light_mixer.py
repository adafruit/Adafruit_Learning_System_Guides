# Magic Light Bulb remote color mixer
# Sends RGB color values, read from three faders on CPB to the bulb
# https://www.magiclightbulbs.com/collections/bluetooth-bulbs

import adafruit_ble
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble_magic_light import MagicLightService
import _bleio
import board
from analogio import AnalogIn
from adafruit_circuitplayground import cp


def find_connection():
    for connection in radio.connections:
        if MagicLightService not in connection:  # Filter services
            continue
        return connection, connection[MagicLightService]
    return None, None

radio = adafruit_ble.BLERadio()


def scale(value):
    # Scale a value from 0-65535 (AnalogIn range) to 0-255 (RGB range)
    return int(value / 65535 * 255)
a4 = AnalogIn(board.A4)  # red slider
a5 = AnalogIn(board.A5)  # green slider
a6 = AnalogIn(board.A6)  # blue slider

cp.pixels.brightness = 0.1
dimmer = 1.0

active_connection, bulb = find_connection()  # In case already connected

while True:
    if not active_connection:  # There's no connection, so let's scan for one
        cp.pixels[0] = (60, 40, 0)  # set CPB NeoPixel 0 to yellow while searching
        print("Scanning for Magic Light...")
        # Scan and filter for advertisements with ProvideServicesAdvertiesment type
        for advertisement in radio.start_scan(ProvideServicesAdvertisement):
            # Filter further for advertisements with MagicLightService
            if MagicLightService in advertisement.services:
                active_connection = radio.connect(advertisement)
                print("Connected to Magic Light")
                cp.pixels[0] = (0, 0, 255)  # Set NeoPixel 0 to blue when connected
                # Play a happy tone
                cp.play_tone(440, 0.1)
                cp.play_tone(880, 0.1)
                print("Adjust slide potentiometers to mix RGB colors")
                try:
                    bulb = active_connection[MagicLightService]
                except _bleio.ConnectionError:
                    print("disconnected")
                    continue
                break
        radio.stop_scan()  # Now that we're connected, stop scanning

    while active_connection.connected:  # Connected, now we can set attrs to change colors
        # Toggle slide switch to go to half or full brightness
        if cp.switch:
            cp.red_led = True
            dimmer = 0.5
        else:
            cp.red_led = False
            dimmer = 1.0

        # Press the 'A' button to momentarily black the bulb
        if cp.button_a:
            dimmer = 0.0

        r = scale(a4.value * dimmer)
        g = scale(a5.value * dimmer)
        b = scale(a6.value * dimmer)

        # Press the 'B' button to momentarily white the bulb
        if cp.button_b:
            r, g, b = (255, 255, 255)

        color = (r, g, b)

        try:
            bulb[0] = color  # Send color to bulb's color characteristic
        except _bleio.ConnectionError:
            print("disconnected")
            continue
        cp.pixels[2] = (r, 0, 0)
        cp.pixels[3] = (0, g, 0)
        cp.pixels[4] = (0, 0, b)
        cp.pixels[7] = (color)

    active_connection = None  # Not connected, start scanning again
    cp.pixels[0] = (60, 40, 0)
