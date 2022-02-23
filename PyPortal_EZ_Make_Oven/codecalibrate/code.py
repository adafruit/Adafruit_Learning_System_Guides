# SPDX-FileCopyrightText: 2019 Dan Cogliano for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import sys
import board
import busio
import digitalio
from adafruit_mcp9600 import MCP9600

SENSOR_ADDR = 0X67

i2c = busio.I2C(board.SCL, board.SDA,frequency=200000)
try:
    sensor = MCP9600(i2c,SENSOR_ADDR,"K")
except ValueError as e:
    print(e)
    print("Unable to connect to the thermocouple sensor.")
    sys.exit(1)

oven = digitalio.DigitalInOut(board.D4)
oven.direction = digitalio.Direction.OUTPUT

def oven_control(enable=False):
    #board.D4
    oven.value = enable

check_temp = 100
print("This program will determine calibration settings ")
print("for your oven to use with the EZ Make Oven.\n\n")
for i in range(10):
    print("Calibration will start in %d seconds..." % (10-i))
    time.sleep(1)
print("Starting...")
print("Calibrating oven temperature to %d C" % check_temp)
finish = False
oven_control(True)
maxloop=300
counter = 0
while not finish:
    time.sleep(1)
    counter += 1
    current_temp = sensor.temperature
    print("%.02f C" % current_temp)
    if current_temp >= check_temp:
        finish = True
        oven_control(False)
    if counter >= maxloop:
        raise Exception("Oven not working or bad sensor")

print("checking oven lag time and temperature")
finish = False
start_time = time.monotonic()
start_temp = sensor.temperature
last_temp = start_temp

while not finish:
    time.sleep(1)
    current_temp = sensor.temperature
    print(current_temp)
    if current_temp <= last_temp:
        finish = True
    last_temp = current_temp

lag_temp = last_temp - check_temp
lag_time = int(time.monotonic() - start_time)

print("** Calibration Results **")
print("Modify config.json with these values for your oven:")
print("calibrate_temp:", lag_temp)
print("calibrate_seconds:",lag_time)
