# SPDX-FileCopyrightText: 2020 Eva Herrada for Adafruit Industries
#
# SPDX-License-Identifier: MIT

from time import time
import adafruit_ble
import board
import pyloton

ble = adafruit_ble.BLERadio()    # pylint: disable=no-member

CONNECTION_TIMEOUT = 45

HEART = True
SPEED = True
CADENCE = True
AMS = True
DEBUG = False

# 84.229 is wheel circumference (700x23 in my case)
pyloton = pyloton.Pyloton(ble, board.DISPLAY, 84.229, HEART, SPEED, CADENCE, AMS, DEBUG)

pyloton.show_splash()

ams = pyloton.ams_connect()


start = time()
hr_connection = None
speed_cadence_connections = []
while True:
    if HEART:
        if not hr_connection:
            print("Attempting to connect to a heart rate monitor")
            hr_connection = pyloton.heart_connect()
            ble.stop_scan()
    if SPEED or CADENCE:
        if not speed_cadence_connections:
            print("Attempting to connect to speed and cadence monitors")
            speed_cadence_connections = pyloton.speed_cadence_connect()

    if time()-start >= CONNECTION_TIMEOUT:
        pyloton.timeout()
        break
    # Stop scanning whether or not we are connected.
    ble.stop_scan()

    #pylint: disable=too-many-boolean-expressions
    if ((not HEART or (hr_connection and hr_connection.connected)) and
            ((not SPEED and not CADENCE) or
             (speed_cadence_connections and speed_cadence_connections[0].connected)) and
            (not AMS or (ams and ams.connected))):
        break

pyloton.setup_display()

while ((not HEART or hr_connection.connected) and
       ((not SPEED or not CADENCE) or
        (speed_cadence_connections and speed_cadence_connections[0].connected)) and
       (not AMS or ams.connected)):
    pyloton.update_display()
    pyloton.ams_remote()

print("\n\nNot all sensors are connected. Please reset to try again\n\n")
