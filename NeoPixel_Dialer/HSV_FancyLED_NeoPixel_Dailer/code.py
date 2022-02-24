# SPDX-FileCopyrightText: 2018 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time

import adafruit_character_lcd
import adafruit_fancyled.adafruit_fancyled as fancy
import board
import digitalio
import neopixel
from analogio import AnalogIn

lcd_rs = digitalio.DigitalInOut(board.D5)
lcd_en = digitalio.DigitalInOut(board.D6)
lcd_d7 = digitalio.DigitalInOut(board.D12)
lcd_d6 = digitalio.DigitalInOut(board.D11)
lcd_d5 = digitalio.DigitalInOut(board.D10)
lcd_d4 = digitalio.DigitalInOut(board.D9)
lcd_columns = 16
lcd_rows = 2

lcd = adafruit_character_lcd.Character_LCD(
    lcd_rs, lcd_en, lcd_d4, lcd_d5, lcd_d6, lcd_d7, lcd_columns, lcd_rows
)

potH = AnalogIn(board.A0)  # pot for hue
potS = AnalogIn(board.A1)  # pot for saturation
potV = AnalogIn(board.A2)  # pot for value
pixpin = board.D13  # NeoPixel pin
numpix = 8

strip = neopixel.NeoPixel(pixpin, numpix, brightness=1.0)


def val(pin):
    # divides voltage (65535) to get a value between 0 and 1
    return pin.value / 65535


def round_pot_h():
    # rounds decimal value to 2 decimal places
    return round(val(potH), 2)


def round_pot_s():
    return round(val(potS), 2)


def round_pot_v():
    return round(val(potV), 2)


while True:
    # calls for HSV values
    color = fancy.CHSV(val(potH), val(potS), val(potV))
    # converts float HSV values to integer RGB values
    packed = color.pack()
    # writes converted int values to NeoPixels
    strip.fill(packed)

    lcd.set_cursor(3, 0)
    # text at the top of the screen
    lcd.message('H + S + V =')
    lcd.set_cursor(1, 1)
    # sends the rounded value and converts it to a string
    lcd.message(str(round_pot_h()))
    lcd.set_cursor(6, 1)
    lcd.message(str(round_pot_s()))
    lcd.set_cursor(11, 1)
    lcd.message(str(round_pot_v()))
    time.sleep(0.5)
    # refreshes screen to display most recent pot values
    lcd.clear()
