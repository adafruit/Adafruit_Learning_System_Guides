"""
'photo_sensor.py'.

=================================================
uses LIGHT to control a LED
"""
import analogio
import board
import pulseio
from simpleio import map_range

LED = pulseio.PWMOut(board.D9)
LIGHT = analogio.AnalogIn(board.A0)


while True:
    LIGHT_VAL = map_range(LIGHT.value, 20000, 32766, 0, 32766)
    LED.duty_cycle = int(LIGHT_VAL)
