# CircuitPlaygroundExpress_Temperature
# reads the on-board temperature sensor and prints the value

import time

import adafruit_thermistor
import board

thermistor = adafruit_thermistor.Thermistor(
    board.TEMPERATURE, 10000, 10000, 25, 3950)

while True:
    print("Temperature is: %f C and %f F" % (thermistor.temperature,
                                             (thermistor.temperature * 9 / 5 + 32)))

    time.sleep(0.25)
