# Author: Isaac Wellish
# Code adapted from Tony Dicola's CircuitPython code using the DS18x20 temp sensor
# as well as John Park's CircuitPython code determining soil moisture from nails

import time
from adafruit_onewire.bus import OneWireBus
from adafruit_ds18x20 import DS18X20
import board
import touchio
import neopixel
import analogio
from simpleio import map_range

# Initialize neopixels
pixels = neopixel.NeoPixel(board.NEOPIXEL, 10, brightness=.1)

# set variables for capacitive touch inputs, later used for soil moisture variables
touch = touchio.TouchIn(board.A1)
touch2 = touchio.TouchIn(board.A2)

DRY_VALUE = 3100  # calibrate this by hand!
WET_VALUE = 4000  # calibrate this by hand!
tempThreshhold = 43 #celius temperature of threshold for ideal compost temperature

# Initialize one-wire bus on board pin A3.
ow_bus = OneWireBus(board.A3)

# Scan for sensors and grab the first one found.
ds18 = DS18X20(ow_bus, ow_bus.scan()[0])

# Initialize the light senor on board to use for neopixel brightness later
light = analogio.AnalogIn(board.LIGHT)

# Main loop
while True:

    # SOIL MOISTURE READINGS

    # set capacitive touch inputs for nails to take in soil moisture levels
    value_A1 = touch.raw_value
    value_A2 = touch2.raw_value

    # take the average of both moisture levels
    avgMoist = value_A1 + value_A2 / 2
    print("Moisture level:",(avgMoist,))

    # TEMPERATURE READINGS

    # variable for temperature
    compostTemp = ds18.temperature

    # print the temperature
    print('Temperature: {0:0.3f}C'.format(compostTemp))

    # IF STATEMENTS TO DETERMINE STATE OF COMPOST

    # RED & YELLOW = TOO COLD & TOO DRY
    if((compostTemp<tempThreshhold) and (avgMoist<DRY_VALUE)):
        pixels[0] = (255,0,0)    # red
        pixels[1] = (255,255,0)  # yellow
        pixels[2] = (255,0,0)
        pixels[3] = (255,255,0)
        pixels[4] = (255,0,0)
        pixels[5] = (255,255,0)
        pixels[6] = (255,0,0)
        pixels[7] = (255,255,0)
        pixels[8] = (255,0,0)
        pixels[9] = (255,255,0)

        print("Not hot enough, too dry")

    # BLUE & YELLOW = TOO COLD & TOO WET
    elif((compostTemp<tempThreshhold) and (avgMoist>WET_VALUE)):
        pixels[0] = (0,0,255)    # blue
        pixels[1] = (255,255,0)  # yellow
        pixels[2] = (0,0,255)
        pixels[3] = (255,255,0)
        pixels[4] = (0,0,255)
        pixels[5] = (255,255,0)
        pixels[6] = (0,0,255)
        pixels[7] = (255,255,0)
        pixels[8] = (0,0,255)
        pixels[9] = (255,255,0)
        print("Not hot enough, too wet")

    # GREEN & YELLOW = TOO COLD & MOISTURE LEVEL OPTIMUM
    elif((compostTemp<tempThreshhold) and (avgMoist >DRY_VALUE and avgMoist<WET_VALUE)):
        pixels[0] = (0,255,0)    # green
        pixels[1] = (255,255,0)  # yellow
        pixels[2] = (0,255,0)
        pixels[3] = (255,255,0)
        pixels[4] = (0,255,0)
        pixels[5] = (255,255,0)
        pixels[6] = (0,255,0)
        pixels[7] = (255,255,0)
        pixels[8] = (0,255,0)
        pixels[9] = (255,255,0)
        print("Not hot enough, right moisture level")

    # ALL GREEN = COMPOST AT OPTIMUM TEMPERATURE & MOISTURE
    elif compostTemp > tempThreshhold:
        pixels.fill((0,255,0))  # green
        print("Compost Ready")

    # LIGHTING CONFIGURATION

    # print value of light sensor
    print((light.value,))

    # map light snesor range to neopixel brightness range
    peak = map_range(light.value, 2000, 62000, 0.01, 0.3)

    # print neopixel brightness levels
    print(peak)

    # show neopixels
    pixels.show()

    # update neopixel brightness based on level of exposed light
    pixels = neopixel.NeoPixel(board.NEOPIXEL, 10, brightness=peak)

    # pause for three seconds
    time.sleep(3)

# END PROGRAM
