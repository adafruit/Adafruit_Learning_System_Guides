# SPDX-FileCopyrightText: 2022 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import board
import adafruit_lis3dh
import simpleio
import adafruit_ble
from adafruit_ble.advertising import Advertisement
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.standard.hid import HIDService
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode

#  I2C setup
i2c = board.I2C()
lis3dh = adafruit_lis3dh.LIS3DH_I2C(i2c)

#  range of LIS3DH
lis3dh.range = adafruit_lis3dh.RANGE_2_G

#  BLE HID setup
hid = HIDService()

advertisement = ProvideServicesAdvertisement(hid)
advertisement.appearance = 961
scan_response = Advertisement()
scan_response.complete_name = "CircuitPython HID"

#  BLE instance
ble = adafruit_ble.BLERadio()

#  keyboard HID setup
keyboard = Keyboard(hid.devices)

#  BLE advertisement
if not ble.connected:
    print("advertising")
    ble.start_advertising(advertisement, scan_response)
else:
    print("connected")
    print(ble.connections)

while True:
    while not ble.connected:
        pass
	#  while BLE connected
    while ble.connected:
        #  read LIS3DH
        x, y, z = [
            value / adafruit_lis3dh.STANDARD_GRAVITY for value in lis3dh.acceleration
        ]
        #  map Y coordinate of LIS3DH
        mapped_y = simpleio.map_range(y, -1.1, 1.1, 0, 3)
        #  convert mapped value to an integer
        plane = int(mapped_y)

        #  if you're tilting down...
        if plane == 0:
            #  send R, glider moves right
            keyboard.press(Keycode.R)
            #  debug
            #  print("right")
        #  if there's no tilt...
        if plane == 1:
            #  release all keys, send nothing to glider
            keyboard.release_all()
            #  debug
            #  print("none")
        #  if you're tilting up...
        if plane == 2:
            #  send L, glider moves left
            keyboard.press(Keycode.L)
            #  debug
            #  print("left")
        time.sleep(0.01)
    #  if BLE disconnects, begin advertising again
    ble.start_advertising(advertisement)
