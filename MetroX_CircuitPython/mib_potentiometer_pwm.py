"""
'mib_potentiometer_pwm.py'.

=================================================
fades a led using a potentiometer
"""

import analogio
import board
import pulseio

led = pulseio.PWMOut(board.D9)
pot = analogio.AnalogIn(board.A0)

while True:
    led.duty_cycle = pot.value
