"""
Read heart rate data from a heart rate peripheral using the standard BLE
Heart Rate service.
"""

import adafruit_ble
import board
from adafruit_ble_heart_rate import HeartRateService
import pyloton
import time


# PyLint can't find BLERadio for some reason so special case it here.
ble = adafruit_ble.BLERadio()    # pylint: disable=no-member

display = board.DISPLAY

pyloton = pyloton.Pyloton(ble, display)
#pyloton.show_splash()

hr_connection = None
# Start with a fresh connection.
if ble.connected:
    for connection in ble.connections:
        if HeartRateService in connection:
            connection.disconnect()
        break
start = time.time()
hr_connection = None
s_and_c_connection = []
while True:
    if not hr_connection:
        print("Running hr_connection")
        hr_connection = pyloton.heart_connect()
        ble.stop_scan()
    if not s_and_c_connection:
        print("Running s_and_c_connection")
        s_and_c_connection = pyloton.s_and_c_connect()

    if time.time()-start >= 45:
        pyloton.timeout()
        break
    # Stop scanning whether or not we are connected.
    ble.stop_scan()
    if hr_connection and hr_connection.connected and s_and_c_connection:
        #pyloton.show_splash(display)

        print("Fetch connection")
        hr_service = hr_connection[HeartRateService]
        print("Location:", hr_service.location)
        while hr_connection.connected:
            pyloton.update_display(hr_service)
