"""
'mib_char_lcd_light.py'
=================================================
light sensor circuit. displays output on charlcd
requires:
- CircuitPython_CharLCD Module
"""

import time
import analogio
import digitalio
import adafruit_character_lcd
from board import D7, D8, D9, D10, D11, D12, D13, A0

#   Character LCD Config:
#   modify this if you have a different sized charlcd
lcd_columns = 16
lcd_rows = 2

#   Metro Express Pin Config:
lcd_rs = digitalio.DigitalInOut(D7)
lcd_en = digitalio.DigitalInOut(D8)
lcd_d7 = digitalio.DigitalInOut(D12)
lcd_d6 = digitalio.DigitalInOut(D11)
lcd_d5 = digitalio.DigitalInOut(D10)
lcd_d4 = digitalio.DigitalInOut(D9)
lcd_backlight = digitalio.DigitalInOut(D13)

light = analogio.AnalogIn(A0)

#   Init the lcd class
lcd = adafruit_character_lcd.Character_LCD(
    lcd_rs, lcd_en, lcd_d4, lcd_d5, lcd_d6, lcd_d7, lcd_columns, lcd_rows, lcd_backlight
)

while True:
    lcd.clear()
    percent = str(100 - ((light.value / 65535) * 100))
    nice = percent[: percent.find(".")]
    lcd.message(nice + "% bright")
    lcd.message(str(light.value))
    time.sleep(1)
    # increment our elapsed_secs variable each time a second passes
