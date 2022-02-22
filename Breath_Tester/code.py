# SPDX-FileCopyrightText: 2018 Mikey Sklar for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time

import adafruit_sgp30
import board
import busio

i2c = busio.I2C(board.SCL, board.SDA, frequency=100000)

# Create library object on our I2C port
sgp30 = adafruit_sgp30.Adafruit_SGP30(i2c)
sgp30.iaq_init()
sgp30.set_iaq_baseline(0x8973, 0x8aae)

# highest tVOC recorded in 30 seconds
highest_breath_result = 0


def warmup_message():
    warmup_time = 20
    warmup_counter = 0

    # initial read required to get sensor going
    sgp30.iaq_measure()

    print()
    print("Warming Up [%d seconds]..." % warmup_time)

    while warmup_counter <= 20:
        print('.', end='')
        time.sleep(1)
        warmup_counter += 1


def get_breath_reading():
    breath_time = 30  # seconds to record breath reading
    # one second count up to breath_time value
    breath_counter = 0
    # initialize list with empty values
    breath_saves = [0] * (breath_time + 1)

    print()
    print("We will collect breath samples for 30 seconds.")
    print("Take a deep breath and exhale into the straw.")
    input(" *** Press a key when ready. *** ")
    print()

    while breath_counter <= breath_time:
        _, tvoc = sgp30.iaq_measure()
        breath_saves[breath_counter] = tvoc
        print(tvoc, ', ', end='')
        time.sleep(1)
        breath_counter += 1

    breath_saves = sorted(breath_saves)
    result = breath_saves[breath_counter - 1]

    return result


# show the highest reading recorded


def show_results(breath_result):
    print()
    print()
    print("peak VOC reading:", breath_result)
    print()
    input("Press any key to test again")
    print()


# main
while True:
    warmup_message()
    highest_breath_result = get_breath_reading()
    show_results(highest_breath_result)
