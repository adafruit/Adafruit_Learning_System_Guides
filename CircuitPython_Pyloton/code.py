from time import time
import adafruit_ble
import board
from adafruit_ble_heart_rate import HeartRateService
import pyloton

# PyLint can't find BLERadio for some reason so special case it here.
ble = adafruit_ble.BLERadio()    # pylint: disable=no-member

display = board.DISPLAY


heart=True
speed=True
cad=True
ams=True
debug=False

# 84.229 is wheel circumference (700x23 in my case)
pyloton = pyloton.Pyloton(ble, display, 84.229, heart, speed, cad, ams, debug)

pyloton.show_splash()

ams = pyloton.ams_connect()


start = time()
hr_connection = None
speed_cad_connections = []
radio = None
while True:
    if heart:
        if not hr_connection:
            print("Running hr_connection")
            hr_connection = pyloton.heart_connect()
            ble.stop_scan()
    if speed or cad:
        if not speed_cad_connections:
            print("Running speed_cad_connection")
            speed_cad_connections = pyloton.speed_cad_connect()

    if time()-start >= 45:
        pyloton.timeout()
        break
    # Stop scanning whether or not we are connected.
    ble.stop_scan()

    # You may need to remove some parts of the following line depending on what
    # devices you are using.
    print(type(hr_connection))
    print(type(speed_cad_connections))
    print(type(ams))
    if hr_connection and hr_connection.connected and speed_cad_connections[0] and speed_cad_connections[0].connected and ams and ams.connected:
        pyloton.setup_display()
        break

# You may need to remove some parts of the following line depending on what devices you are using.
while hr_connection.connected and speed_cad_connections[0].connected and ams.connected:
    pyloton.update_display()
    pyloton.ams_remote()

print("\n\nNot all sensors are connected. Please reset to try again\n\n")
