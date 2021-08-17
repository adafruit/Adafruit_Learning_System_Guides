"""
'servo.py'.

=================================================
move a hobby servo (towerpro sg92r) w/ 3-wire interface
requires:
- Adafruit_CircuitPython_Motor
"""
import time
import board
import pwmio
from adafruit_motor import servo

SERVO = servo.Servo(pwmio.PWMOut(board.D9))

while True:
    SERVO.angle = 0
    time.sleep(2)
    SERVO.angle = 90
    time.sleep(2)
