"""
'mib_servo.py'.

=================================================
sweeping a servo with an analog potentiometer
requires:
- Adafruit_CircuitPython_Motor
"""
import time
import analogio
import board
import pulseio
from adafruit_motor import servo


SERVO = servo.Servo(pulseio.PWMOut(board.D9))
POTE = analogio.AnalogIn(board.A0)


def servo_sweep():
    """sweeps the servo."""
    for angle_fwd in range(0, 180, 1):
        SERVO.angle = angle_fwd
        time.sleep(0.01)
    for angle_bkwd in range(180, 0, -1):
        SERVO.angle = angle_bkwd
        time.sleep(0.01)


def pote_sweep():
    """assigns servo value to an analog potentiometer value."""
    val = POTE.value / 65536
    SERVO.angle = 180 * val
    time.sleep(0.05)


while True:
    servo_sweep()
    # pote_sweep()
