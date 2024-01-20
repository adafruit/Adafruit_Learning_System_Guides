# SPDX-FileCopyrightText: 2022 Charlyn G for Adafruit Industries
#
# SPDX-License-Identifier: MIT
#
# Code for the Adafruit Learning System tutorial
#   Exercise Buddy: Motion aware BLE media controller
#   https://learn.adafruit.com/exercise-buddy/overview
#
import time
import board
import supervisor

import neopixel
import adafruit_ble
import adafruit_lis3dh
from adafruit_ble.advertising.standard import SolicitServicesAdvertisement
from adafruit_ble_apple_media import AppleMediaService, UnsupportedCommand

# Initialize the accelerometer
i2c = board.I2C()  # uses board.SCL and board.SDA
# i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller
lis3dh = adafruit_lis3dh.LIS3DH_I2C(i2c)

#  Initialize BLE radio
radio = adafruit_ble.BLERadio()
a = SolicitServicesAdvertisement()
a.solicited_services.append(AppleMediaService)
radio.start_advertising(a)

# Neopixel indicator
pixel_pin = board.NEOPIXEL
pixel = neopixel.NeoPixel(pixel_pin, 1, brightness=0.5)
YELLOW = (200, 150, 0)
CYAN = (0, 100, 100)
PINK = (231, 84, 128)
pixel.fill(PINK)

while not radio.connected:
    pass

print("connected")
pixel.fill(YELLOW)

# Initialize variables
last_x = 0
last_y = 0
last_z = 0
paused = True

WAIT = 0.2
WIGGLE_ROOM = 5  # Increase this for more jitter compensation.


def is_same_pos(last_position, current_position):
    # Returns true if current_position is similar enough
    # to last_position, within the specified wiggle room.
    diff = abs(current_position - last_position)
    print((diff,))
    return diff <= WIGGLE_ROOM


def not_enough_movement(x, y, z):
    same_x = is_same_pos(last_x, x)
    same_y = is_same_pos(last_y, y)
    same_z = is_same_pos(last_z, z)
    return same_x and same_y and same_z


while radio.connected:

    for connection in radio.connections:
        if not connection.paired:
            connection.pair()
            print("paired")
            pixel.fill(PINK)
            time.sleep(1)

        if connection.paired:
            pixel.fill(CYAN)
            ams = connection[AppleMediaService]
            print("app:", ams.player_name)

            try:
                xf, yf, zf = lis3dh.acceleration

                if not_enough_movement(xf, yf, zf):
                    # Keep pausing.
                    print("pause!")
                    paused = True
                    ams.pause()

                else:
                    last_x = xf
                    last_y = yf
                    last_z = zf

                    if paused:
                        print("play!")
                        paused = False
                        ams.play()

            except OSError:
                supervisor.reload()
            except UnsupportedCommand:
                # This means that we tried to pause but there's
                # probably nothing playing yet, so just wait a bit
                # and try again.
                pixel.fill(PINK)
                time.sleep(10)
                supervisor.reload()

            time.sleep(WAIT)

print("disconnected")
pixel.fill(PINK)
