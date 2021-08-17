"""
'MOTOR.py'.

=================================================
spin a DC MOTOR using digitalio
"""

import time
import board
import digitalio

MOTOR_PIN = board.D9
MOTOR = digitalio.DigitalInOut(MOTOR_PIN)
MOTOR.switch_to_output()


def motor_on_then_off():
    """toggles the motor."""
    on_time = 2.5
    off_time = 1.0
    MOTOR.value = True
    time.sleep(on_time)
    MOTOR.value = False
    time.sleep(off_time)


while True:
    motor_on_then_off()
