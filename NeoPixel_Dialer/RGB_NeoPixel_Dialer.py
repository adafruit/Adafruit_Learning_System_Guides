import math
import time

import adafruit_character_lcd
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

potR = AnalogIn(board.A0)  # pot pin for R val
potG = AnalogIn(board.A1)  # pot pin for G val
potB = AnalogIn(board.A2)  # pot pin for B val
pixpin = board.D13  # neopixel pin
numpix = 8

strip = neopixel.NeoPixel(pixpin, numpix, brightness=0.1)


def val(pin):
    # divides voltage (65535) to get a value between 0 and 255
    return pin.value / 257


while True:
    strip.fill((int(val(potR)), int(val(potG)), int(val(potB))))
    # int converts float val to an integer

    lcd.set_cursor(3, 0)
    # text at the top of the screen
    lcd.message('R + G + B =')
    lcd.set_cursor(2, 1)
    # str converts float val to a string, trunc removes decimal values
    lcd.message(str(math.trunc(val(potR))))
    lcd.set_cursor(6, 1)
    lcd.message(str(math.trunc(val(potG))))
    lcd.set_cursor(10, 1)
    lcd.message(str(math.trunc(val(potB))))
    time.sleep(0.5)
    # refreshes screen to send updated values from pots
    lcd.clear()
