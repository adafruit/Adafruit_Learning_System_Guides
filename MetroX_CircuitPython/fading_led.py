"""
'fading_led.py'.

=================================================
fades a LED using pulseio's PWM
"""

import pulseio
import board

led = pulseio.PWMOut(board.D13, frequency=500, duty_cycle=0)

while True:
    for i in range(100):
        if i < 50:  # fade up
            led.duty_cycle = int(i * 2 * 65535 / 100)
        else:  # fade down
            led.duty_cycle = 65535 - int((i - 50) * 2 * 65535 / 100)
