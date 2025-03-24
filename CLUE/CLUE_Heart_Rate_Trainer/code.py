# SPDX-FileCopyrightText: 2020 John Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Heart Rate Trainer
Read heart rate data from a heart rate peripheral using the standard BLE
Heart Rate service.
Displays BPM value and percentage of max heart rate on CLUE
"""

import time
from adafruit_clue import clue
import adafruit_ble
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.standard.device_info import DeviceInfoService
from adafruit_ble_heart_rate import HeartRateService

clue_data = clue.simple_text_display(title="Heart Rate", title_color = clue.PINK,
                                     title_scale=1, text_scale=3)

alarm_enable = True

# target heart rate for interval training
# Change this number depending on your max heart rate, usually figured
# as (220 - your age).
max_rate = 180

# PyLint can't find BLERadio for some reason so special case it here.
ble = adafruit_ble.BLERadio()    # pylint: disable=no-member

hr_connection = None

# Start with a fresh connection.
if ble.connected:
    print("SCAN")
    print("BLE")
    time.sleep(1)

    for connection in ble.connections:
        if HeartRateService in connection:
            connection.disconnect()
        break

while True:
    print("Scanning...")
    print("SCAN")
    print("BLE")
    time.sleep(1)
    clue_data[0].text = "BPM: ---"
    clue_data[0].color = ((30, 0, 0))
    clue_data[1].text = "Scanning..."
    clue_data[3].text = ""
    clue_data[1].color = ((130, 130, 0))
    clue_data.show()

    for adv in ble.start_scan(ProvideServicesAdvertisement, timeout=5):
        if HeartRateService in adv.services:
            print("found a HeartRateService advertisement")
            hr_connection = ble.connect(adv)
            #display_dots()
            print("....")
            time.sleep(2)
            print("Connected")
            break

    # Stop scanning whether or not we are connected.
    ble.stop_scan()
    print("Stopped scan")
    time.sleep(0.1)

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
            #print(values)  # returns the full heart_rate data set
            if values:
                bpm = (values.heart_rate)
                if bpm is not 0:
                    pct_target = (round(100*(bpm/max_rate)))
                if values.heart_rate is 0:
                    print("----")
                    clue_data[0].text = "BPM: ---"
                    clue_data[0].color = ((80, 0, 0))
                    clue_data[1].text = "Target: --"
                    clue_data[1].color = ((0, 0, 80))
                else:
                    clue_data[0].text = "BPM: {0:d}".format(bpm)
                    clue_data[0].color = clue.RED

                    clue_data[1].text = "Target: {0:d}%".format(pct_target)
                    if pct_target < 90:
                        alarm = False
                        clue_data[1].color = clue.CYAN
                    else:
                        alarm = True
                        clue_data[1].color = clue.RED

                    clue_data[3].text = "Max HR: : {0:d}".format(max_rate)
                    clue_data[3].color = clue.BLUE
                    clue_data.show()

                    if alarm and alarm_enable:
                        clue.start_tone(2000)
                    else:
                        clue.stop_tone()

                    # Inputs
                    if clue.button_a:
                        if clue.touch_2:  # hold cap touch 2 for bigger change rate
                            max_rate = max_rate -10
                        else:
                            max_rate = max_rate - 1
                    if clue.button_b:
                        if clue.touch_2:
                            max_rate = max_rate + 10
                        else:
                            max_rate = max_rate + 1

                    if clue.touch_0:
                        alarm_enable = False
                    if clue.touch_1:
                        alarm_enable = True

            time.sleep(0.2)
