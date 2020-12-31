import time

import board
import adafruit_thermistor

thermistor = adafruit_thermistor.Thermistor(
    board.TEMPERATURE, 10000, 10000, 25, 3950)

while True:
    print((thermistor.temperature,))
    # print(((thermistor.temperature * 9 / 5 + 32),))  # Fahrenheit
    time.sleep(0.25)
