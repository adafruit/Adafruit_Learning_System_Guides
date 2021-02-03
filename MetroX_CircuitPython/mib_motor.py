"""
'mib_motor.py'.

=================================================
spins a DC motor using pulseio
"""

import time
import board
import pulseio

motor_pin = board.D9
motor = pulseio.PWMOut(motor_pin, frequency=1000)


def motor_on_then_off_with_speed():
    """turns the motor on, then off, using PWM."""
    on_speed = 0.80
    on_time = 2.5
    off_speed = 0.10
    off_time = 1.0
    motor.duty_cycle = int(on_speed * 65535)
    time.sleep(on_time)
    motor.duty_cycle = int(off_speed * 65535)
    time.sleep(off_time)


def motor_acceleration():
    """accelerates the motor forwards and backwards."""
    delay_time = 0.05
    for speed in range(0, 100, 1):
        motor.duty_cycle = int(speed / 100 * 65535)
        time.sleep(delay_time)
    for speed in range(100, 0, -1):
        motor.duty_cycle = int(speed / 100 * 65535)
        time.sleep(delay_time)


while True:
    motor_on_then_off_with_speed()
    # motor_acceleration()
