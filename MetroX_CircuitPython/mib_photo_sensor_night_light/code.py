"""
'mib_photo_sensor_night_light_sensor.py'.

=================================================
turns off and on a led using a photo sensor
"""

import analogio
import board
import digitalio

threshold_value = 60000

led = digitalio.DigitalInOut(board.D9)
led.switch_to_output()
light_sensor = analogio.AnalogIn(board.A0)


while True:
    if light_sensor.value > threshold_value:
        led.value = True
    else:
        led.value = False
