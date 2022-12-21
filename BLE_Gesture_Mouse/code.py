# SPDX-FileCopyrightText: 2021 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
import digitalio
import simpleio
import adafruit_lsm6ds.lsm6ds33
import adafruit_apds9960.apds9960
from adafruit_hid.mouse import Mouse

import adafruit_ble
from adafruit_ble.advertising import Advertisement
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.standard.hid import HIDService
from adafruit_ble.services.standard.device_info import DeviceInfoService

#  setup I2C
i2c = board.I2C()  # uses board.SCL and board.SDA
# i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller

#  setup accelerometer
lsm6ds33 = adafruit_lsm6ds.lsm6ds33.LSM6DS33(i2c)
#  setup proximity sensor
apds9960 = adafruit_apds9960.apds9960.APDS9960(i2c)

#  enable proximity sensor
apds9960.enable_proximity = True

#  setup for onboard button
click = digitalio.DigitalInOut(board.SWITCH)
click.direction = digitalio.Direction.INPUT
click.pull = digitalio.Pull.UP

#  rounding algorhythm used for mouse movement
#  as used in the HID mouse CircuitPython example
mouse_min = -9
mouse_max = 9
step = (mouse_max - mouse_min) / 20.0

def steps(axis):
    return round((axis - mouse_min) / step)

#  time.monotonic() variable
clock = 0

#  variable for distance for proximity scrolling
distance = 245

#  setup for HID and BLE
hid = HIDService()

device_info = DeviceInfoService(software_revision=adafruit_ble.__version__,
                                manufacturer="Adafruit Industries")
advertisement = ProvideServicesAdvertisement(hid)
advertisement.appearance = 961
scan_response = Advertisement()
scan_response.complete_name = "CircuitPython HID"

ble = adafruit_ble.BLERadio()

if not ble.connected:
    print("advertising")
    ble.start_advertising(advertisement, scan_response)
else:
    print("already connected")
    print(ble.connections)

#  setup for mouse
mouse = Mouse(hid.devices)

while True:
    while not ble.connected:
        pass
    while ble.connected:
        #  sets x and y values for accelerometer x and y values
        #  x and y are swapped for orientation of feather
        y, x, z = lsm6ds33.acceleration

        #  map range of horizontal movement to mouse x movement
        horizontal_mov = simpleio.map_range(steps(x), 1.0, 20.0, -15.0, 15.0)
        #  map range of vertical movement to mouse y movement
        vertical_mov = simpleio.map_range(steps(y), 20.0, 1.0, -15.0, 15.0)
        #  map range of mouse y movement to scrolling
        scroll_dir = simpleio.map_range(vertical_mov, -15.0, 15.0, 3.0, -3.0)

        #  if onboard button is pressed, sends left mouse click
        if not click.value:
            mouse.click(Mouse.LEFT_BUTTON)
            time.sleep(0.2)
        #  if the proximity sensor is covered
        #  scroll the mouse
        if apds9960.proximity > distance:
            mouse.move(wheel=int(scroll_dir))
        #  otherwise move mouse cursor in x and y directions
        else:
            mouse.move(x=int(horizontal_mov))
            mouse.move(y=int(vertical_mov))

        #  debugging print for x and y values
        #  time.monotonic() is used so that the
        #  code is not delayed with time.sleep
        if (clock + 2) < time.monotonic():
            print("x", steps(x))
            print("y", steps(y))
            clock = time.monotonic()

    ble.start_advertising(advertisement)
