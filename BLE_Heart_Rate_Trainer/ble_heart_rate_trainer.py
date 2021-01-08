"""
Heart Rate Trainer
Read heart rate data from a heart rate peripheral using the standard BLE
Heart Rate service.
Displays BPM value to Seven Segment FeatherWing
Displays percentage of max heart rate on another 7Seg FeatherWing
"""

import time
import board

import adafruit_ble
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.standard.device_info import DeviceInfoService
from adafruit_ble_heart_rate import HeartRateService

from adafruit_ht16k33.segments import Seg7x4

from digitalio import DigitalInOut, Direction

# Feather on-board status LEDs setup
red_led = DigitalInOut(board.RED_LED)
red_led.direction = Direction.OUTPUT
red_led.value = True

blue_led = DigitalInOut(board.BLUE_LED)
blue_led.direction = Direction.OUTPUT
blue_led.value = False

# target heart rate for interval training
# Change this number depending on your max heart rate, usually figured
# as (220 - your age).
max_rate = 180

# Seven Segment FeatherWing setup
i2c = board.I2C()
display_A = Seg7x4(i2c, address=0x70)  # this will be the BPM display
display_A.fill(0)  # Clear the display
# Second display has A0 address jumpered
display_B = Seg7x4(i2c, address=0x71)  # this will be the % target display
display_B.fill(0)  # Clear the display

# display_A "b.P.M."
display_A.set_digit_raw(0, 0b11111100)
display_A.set_digit_raw(1, 0b11110011)
display_A.set_digit_raw(2, 0b00110011)
display_A.set_digit_raw(3, 0b10100111)
# display_B "Prct"
display_B.set_digit_raw(0, 0b01110011)
display_B.set_digit_raw(1, 0b01010000)
display_B.set_digit_raw(2, 0b01011000)
display_B.set_digit_raw(3, 0b01000110)
time.sleep(3)

display_A.fill(0)
for h in range(4):
    display_A.set_digit_raw(h, 0b10000000)
# display_B show maximum heart rate value
display_B.fill(0)
display_B.print(max_rate)
time.sleep(2)

# PyLint can't find BLERadio for some reason so special case it here.
ble = adafruit_ble.BLERadio()  # pylint: disable=no-member

hr_connection = None


def display_SCAN():
    display_A.fill(0)
    display_A.set_digit_raw(0, 0b01101101)
    display_A.set_digit_raw(1, 0b00111001)
    display_A.set_digit_raw(2, 0b01110111)
    display_A.set_digit_raw(3, 0b00110111)


def display_bLE():
    display_B.fill(0)
    display_B.set_digit_raw(0, 0b00000000)
    display_B.set_digit_raw(1, 0b01111100)
    display_B.set_digit_raw(2, 0b00111000)
    display_B.set_digit_raw(3, 0b01111001)


def display_dots():  # "...."
    for j in range(4):
        display_A.set_digit_raw(j, 0b10000000)
        display_B.set_digit_raw(j, 0b10000000)


def display_dashes():  # "----"
    for k in range(4):
        display_A.set_digit_raw(k, 0b01000000)
        display_B.set_digit_raw(k, 0b01000000)


# Start with a fresh connection.
if ble.connected:
    display_SCAN()
    display_bLE()
    time.sleep(1)

    for connection in ble.connections:
        if HeartRateService in connection:
            connection.disconnect()
        break

while True:
    print("Scanning...")
    red_led.value = True
    blue_led.value = False
    display_SCAN()
    display_bLE()
    time.sleep(1)

    for adv in ble.start_scan(ProvideServicesAdvertisement, timeout=5):
        if HeartRateService in adv.services:
            print("found a HeartRateService advertisement")
            hr_connection = ble.connect(adv)
            display_dots()
            time.sleep(2)
            print("Connected")
            blue_led.value = True
            red_led.value = False
            break

    # Stop scanning whether or not we are connected.
    ble.stop_scan()
    print("Stopped scan")
    red_led.value = False
    blue_led.value = True
    time.sleep(0.5)

    if hr_connection and hr_connection.connected:
        print("Fetch connection")
        if DeviceInfoService in hr_connection:
            dis = hr_connection[DeviceInfoService]
            try:
                manufacturer = dis.manufacturer
            except AttributeError:
                manufacturer = "(Manufacturer Not specified)"
            try:
                model_number = dis.model_number
            except AttributeError:
                model_number = "(Model number not specified)"
            print("Device:", manufacturer, model_number)
        else:
            print("No device information")
        hr_service = hr_connection[HeartRateService]
        print("Location:", hr_service.location)

        while hr_connection.connected:
            values = hr_service.measurement_values
            print(values)  # returns the full heart_rate data set
            if values:
                bpm = values.heart_rate
                if bpm != 0:
                    pct_target = round(100 * (bpm / max_rate))
                display_A.fill(0)  # clear the display
                display_B.fill(0)
                if values.heart_rate == 0:
                    display_dashes()
                else:
                    display_A.fill(0)
                    display_B.print(pct_target)
                    time.sleep(0.1)
                    display_A.print(bpm)

            time.sleep(0.9)
            display_A.set_digit_raw(0, 0b00000000)
