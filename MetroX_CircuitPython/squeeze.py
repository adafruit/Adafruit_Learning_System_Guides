"""
'squeeze.py'.

=================================================
force sensitive resistor (fsr) with circuitpython
"""

import analogio
import board
import pulseio

FORCE_SENS_RESISTOR = analogio.AnalogIn(board.A2)
LED = pulseio.PWMOut(board.D10)

while True:
    LED.duty_cycle = FORCE_SENS_RESISTOR.value
