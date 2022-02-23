# SPDX-FileCopyrightText: 2018 Mikey Sklar for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time

import adafruit_CCS811
import board
import busio
import neopixel

# i2c interface for the gas sensor
i2c_bus = busio.I2C(board.SCL, board.SDA)
ccs = adafruit_CCS811.CCS811(i2c_bus)

# Three Different NeoPixel 8 LED Lengths for Output:
# 1 - Temperature - Circuit Playground Built-In LEDs
# 2 - Total Volatile Organic Compounds [strip]
# 3 - Co2 Output - NeoPixel [strip]
num_leds = 8
temperature_pix = neopixel.NeoPixel(board.NEOPIXEL, num_leds, brightness=.1)
tvoc_pix = neopixel.NeoPixel(board.A1, num_leds, bpp=4, brightness=.1)
co2_pix = neopixel.NeoPixel(board.A2, num_leds, bpp=4, brightness=.1)
led_draw = .05  # delay for LED pixel turn on/off

# wait for the sensor to be ready and calibrate the thermistor
while not ccs.data_ready:
    pass
temp = ccs.temperature
ccs.temp_offset = temp - 25.0


def clear_pix(delay):
    # clear all LEDs for breathing effect
    for i in range(0, num_leds):
        temperature_pix[i] = (0, 0, 0)
        co2_pix[i] = (0, 0, 0, 0)
        tvoc_pix[i] = (0, 0, 0, 0)
        time.sleep(delay)


def co2_led_meter():
    # Show Carbon Dioxide on a NeoPixel Strip
    co2_floor = 400
    co2_ceiling = 8192

    # Map CO2 range to 8 LED NeoPixel Stick
    co2_range = co2_ceiling - co2_floor
    co2_led_steps = co2_range / num_leds
    co2_leds = int((ccs.eCO2 - co2_floor) / co2_led_steps)

    # Insert Colors
    for i in range(0, (co2_leds - 1)):
        co2_pix[i] = (255, 0, 255, 0)
        time.sleep(led_draw)


def tvoc_led_meter():
    # Show Total Volatile Organic Compounds on a NeoPixel Strip
    tvoc_floor = 0
    tvoc_ceiling = 1187

    # Map CO2 range to 8 LED NeoPixel Stick
    tvoc_range = tvoc_ceiling - tvoc_floor
    tvoc_led_steps = tvoc_range / num_leds
    tvoc_leds = int(ccs.TVOC / tvoc_led_steps)

    # Insert Colors
    for i in range(0, (tvoc_leds - 1)):
        tvoc_pix[i] = (0, 0, 255, 0)
        time.sleep(led_draw)


def temp_led_meter():
    # Show Temperature on Circuit Playground built-in NeoPixels
    temp_floor = 23
    temp_ceiling = 36

    # Map temperature range to 8 LEDs on Circuit Playground
    temp_range = temp_ceiling - temp_floor
    temp_led_steps = temp_range / num_leds
    temp_leds = int((ccs.temperature - temp_floor) / temp_led_steps)

    # Insert Colors
    for i in range(0, (temp_leds - 1)):
        temperature_pix[i] = (255, 255, 0)
        time.sleep(led_draw)


while True:
    # print to console
    # - co2
    # - total voltatile organic compounds
    # - temperature in celsius
    print("CO2: ", ccs.eCO2, " TVOC:", ccs.TVOC, " temp:", ccs.temperature)

    co2_led_meter()
    tvoc_led_meter()
    temp_led_meter()

    time.sleep(.5)
    clear_pix(led_draw)
