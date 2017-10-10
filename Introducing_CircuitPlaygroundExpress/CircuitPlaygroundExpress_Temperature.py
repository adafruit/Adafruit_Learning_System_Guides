# CircuitPlaygroundExpress_Temperature
# reads the on-board temperature sensor and prints the value

import adafruit_thermistor
import board
import time

thermistor = adafruit_thermistor.Thermistor(board.TEMPERATURE, 10000, 10000, 25, 3950)


while True:
    #print("Analog Voltage: %f" % getVoltage(analogin))
    #print("Temp is: %f C" % thermistor.temperature)
    #print("\t\t\t\t\tand: %f F." % (thermistor.temperature*9/5+32))

    print("Temperature is: %f C and %f F" % (thermistor.temperature,
                                    (thermistor.temperature*9/5+32)))

    time.sleep(0.25)
