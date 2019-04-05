"""
This Code uses the:
* Adafruit LCD backpack using MCP23008 I2C expander
* Maxbotic LV-EZ1 Ultrasonic Sensor

Tested with the Trinket M0
The ultrasonic sensor and pin use should be Gemma M0 compatible
This sketch reads the LV-EZ1 by pulse count
Then prints the distance to the LCD and python console

The circuit:
* 5V to Trinket M0 USB or BAT pin, I2C Backpack 5V and EZ1 +5
* GND to Trinket M0 GND pin, I2C Backpack GND and EZ1 GND
* Display I2C Backpack SLK to Trinket GPIO #2
* Display I2C backpack SDA to Trinket GPIO #0
* LV-EZ1 Ultrasonic Sensor PW pin to Trinket GPIO #1
* Backlight can be hard wired by connecting LCD pin 16, 17 or 18 to GND
"""

import time

import adafruit_character_lcd
import board
import busio
import pulseio

ez1pin = board.D1  # Trinket GPIO #1

# i2c LCD initialize bus and class
i2c = busio.I2C(board.SCL, board.SDA)
cols = 16
rows = 2
lcd = adafruit_character_lcd.Character_LCD_I2C(i2c, cols, rows)

# calculated mode or median distance
mode_result = 0

# pulseio can store multiple pulses
# read in time for pin to transition
samples = 18
pulses = pulseio.PulseIn(board.D1, maxlen=samples)

# sensor reads which are in range will be stored here
rangevalue = [0, 0, 0, 0, 0, 0, 0, 0, 0]

# 25ms sensor power up pause
time.sleep(.25)


def tof_cm(time_of_flight):
    """
    EZ1 ultrasonic sensor is measuring "time of flight"
    Converts time of flight into distance in centimeters
    """
    convert_to_cm = 58
    cm = time_of_flight / convert_to_cm

    return cm


def tof_inches(time_of_flight):
    """
    EZ1 ultrasonic sensor is measuring "time of flight"
    Converts time of flight into distance in inches
    """
    convert_to_inches = 147
    inches = time_of_flight / convert_to_inches

    return inches


def find_mode(x):
    """
    find the mode (most common value reported)
    will return median (center of sorted list)
    should mode not be found
    """
    n = len(x)

    max_count = 0
    mode = 0
    bimodal = 0
    counter = 0
    index = 0

    while index < (n - 1):
        prev_count = counter
        counter = 0

        while (x[index]) == (x[index + 1]):
            counter += 1
            index += 1

        if (counter > prev_count) and (counter > max_count):
            mode = x[index]
            max_count = counter
            bimodal = 0

        if counter == 0:
            index += 1

        # If the dataset has 2 or more modes.
        if counter == max_count:
            bimodal = 1

        # Return the median if there is no mode.
        if (mode == 0) or (bimodal == 1):
            mode = x[int(n / 2)]

        return mode


while True:

    # wait between samples
    time.sleep(.5)

    if len(pulses) == samples:
        j = 0  # rangevalue array counter

        # only save the values within range
        # range readings take 49mS
        # pulse width is .88mS to 37.5mS
        for i in range(0, samples):
            tof = pulses[i]  # time of flight - PWM HIGH

            if 880 < tof < 37500:
                if j < len(rangevalue):
                    rangevalue[j] = tof_cm(tof)
                    j += 1

        # clear pulse samples
        pulses.clear()  # clear all values in pulses[]

        # sort samples
        rangevalue = sorted(rangevalue)

        # returns mode or median
        mode_result = int(find_mode(rangevalue))

        # python console prints both centimeter and inches distance
        cm2in = .393701
        mode_result_in = mode_result * cm2in
        print(mode_result, "cm", "\t\t", int(mode_result_in), "in")

        # result must be in char/string format for LCD printing
        digit_string = str(mode_result)

        lcd.clear()
        lcd.message("Range: ")  # write to LCD
        lcd.message("    ")
        lcd.message(digit_string)
        lcd.message("cm")

        time.sleep(2)
