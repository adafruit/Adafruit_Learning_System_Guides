# SPDX-FileCopyrightText: 2018 John Edgar Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# Motion Sensor Alarm
# uses Gemma M0, vibration sensor on A0/GND, & piezo on D0/GND
import time
import pwmio
from analogio import AnalogIn
import board

piezo = pwmio.PWMOut(board.D0, duty_cycle=0, frequency=440,
                       variable_frequency=True)

vibrationPin = AnalogIn(board.A0)


def get_voltage(pin):
    return (pin.value * 3.3) / 65536


while True:
    print((get_voltage(vibrationPin),))
    vibration = get_voltage(vibrationPin)

    if vibration < 1:  # the sensor has been tripped, you can adjust this value
        # for sensitivity
        for f in (2620, 4400, 2620, 4400, 2620, 4400, 2620, 4400):
            piezo.frequency = f
            piezo.duty_cycle = 65536 // 2  # on 50%
            time.sleep(0.2)  # on 1/5 second
            piezo.duty_cycle = 0  # off
            time.sleep(0.02)  # pause
    time.sleep(0.01)  # debounce delay
