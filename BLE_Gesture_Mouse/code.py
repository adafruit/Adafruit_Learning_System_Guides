import time
import board
import digitalio
import adafruit_lsm6ds.lsm6ds33
import adafruit_apds9960.apds9960
from adafruit_hid.mouse import Mouse

import adafruit_ble
from adafruit_ble.advertising import Advertisement
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.standard.hid import HIDService
from adafruit_ble.services.standard.device_info import DeviceInfoService

#  setup I2C
i2c = board.I2C()

#  setup accelerometer
lsm6ds33 = adafruit_lsm6ds.lsm6ds33.LSM6DS33(i2c)
#  setup proximity sensor
apds9960 = adafruit_apds9960.apds9960.APDS9960(i2c)

#  enable proximity sensor
apds9960.enable_proximity = True

#  x and y axis setup
x_axis = 0
y_axis = 0

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
        x = lsm6ds33.acceleration[1]
        y = lsm6ds33.acceleration[0]

        #  if onboard button is pressed, sends left mouse click
        if click.value is False:
            mouse.click(Mouse.LEFT_BUTTON)
            time.sleep(0.2)
        #  debugging print for x and y values
        #  time.monotonic() is used so that the
        #  code is not delayed with time.sleep
        if (clock + 2) < time.monotonic():
            print("x", steps(x))
            print("y", steps(y))
            clock = time.monotonic()
        #  mouse movement left and right
        if steps(x) > 11.0:
            mouse.move(x=1)
        if steps(x) < 9.0:
            mouse.move(x=-1)

        if steps(x) > 19.0:
            mouse.move(x=8)
        if steps(x) < 1.0:
            mouse.move(x=-8)
        #  mouse movement up and down
        #  and mouse scrolling using
        #  proximity sensor
        if steps(y) > 11.0:
            if apds9960.proximity > distance:
                #  scroll down
                mouse.move(wheel=1)
                time.sleep(0.1)
            else:
                #  move down
                mouse.move(y=-1)
        if steps(y) < 9.0:
            if apds9960.proximity > distance:
                #  scroll up
                mouse.move(wheel=-1)
                time.sleep(0.1)
            else:
                #  move up
                mouse.move(y=1)

        if steps(y) > 15.0:
            if apds9960.proximity > distance:
                #  scroll down
                mouse.move(wheel=3)
            else:
                #  move down
                mouse.move(y=-8)
        if steps(y) < 1.0:
            if apds9960.proximity > distance:
                #  scroll up
                mouse.move(wheel=-3)
            else:
            #  move up
                mouse.move(y=8)
        #print(apds9960.proximity)
    ble.start_advertising(advertisement)
