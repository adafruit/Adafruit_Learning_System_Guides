# SPDX-FileCopyrightText: 2022 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import board
import simpleio
import adafruit_bmp280
import pwmio
import displayio
from adafruit_motor import servo
import terminalio
from adafruit_clue import clue
from adafruit_display_text import label

#  board display
#  scaling for terminalio font
display = board.DISPLAY
group = displayio.Group(scale=3)

#  text elements
temp_header = "Temperature:"
press_header = "Pressure:"
temp_text = "   ºC"
press_text = "   hPa"
font = terminalio.FONT
blue = 0x0000FF
red = 0xFF0000

#  pwm setup for servo
pwm = pwmio.PWMOut(board.D0, duty_cycle=2 ** 15, frequency=50)
gauge = servo.Servo(pwm)

#  bmp280 sensor setup
i2c = board.I2C()  # uses board.SCL and board.SDA
bmp280 = adafruit_bmp280.Adafruit_BMP280_I2C(i2c)

bmp280.sea_level_pressure = 1013.25

#  temperature text elements
temp_label = label.Label(font, text=temp_header, color=red, x=5, y=10)
temp_data = label.Label(font, text=temp_text, color=red, x=5, y=25)

#  pressure text elements
press_label = label.Label(font, text=press_header, color=blue, x=5, y=50)
press_data = label.Label(font, text=press_text, color=blue, x=5, y=65)

#  adding text to display group
group.append(temp_label)
group.append(press_label)
group.append(temp_data)
group.append(press_data)

display.show(group)

#  function to convert celcius to fahrenheit
def c_to_f(temp):
    temp_f = (temp * 9/5) + 32
    return temp_f

#  function to convert hPa to inHg
def hpa_to_inHg(hPa):
    inches_mercury = hPa * 0.02953
    return inches_mercury

#  time.monotonic clock
clock = 0
#  units state
us_units = False

while True:
    #  non-blocking 2 second delay
    if (clock + 2) < time.monotonic():
        #  map servo range to barometric pressure range
        servo_value = simpleio.map_range(bmp280.pressure, 970, 1050, 180, 0)
        #  set servo to pressure
        gauge.angle = servo_value
        #  print data for debugging
        print("\nTemperature: %0.1f C" % bmp280.temperature)
        print("Pressure: %0.1f hPa" % bmp280.pressure)
        print(servo_value)
        #  if not US units...
        if not us_units:
            #  update temp & pressure text in celcius and hPa
            temp_data.text = "%0.1f ºC" % bmp280.temperature
            press_data.text = "%0.1f hPa" % bmp280.pressure
        #  if US units...
        if us_units:
            #  convert celcius to fahrenheit
            temp_fahrenheit = c_to_f(bmp280.temperature)
            #  convert hPa to inHg
            pressure_inHg = hpa_to_inHg(bmp280.pressure)
            #  update temp & pressure text
            temp_data.text = "%0.1f ºF" % temp_fahrenheit
            press_data.text = "%0.1f inHg" % pressure_inHg
        #  reset time.monotonic() clock
        clock = time.monotonic()
    #  if a button is pressed, us_units is False, show imperial
    if clue.button_a:
        us_units = False
    #  if b button is pressed, us_units is True, show US units
    if clue.button_b:
        us_units = True
