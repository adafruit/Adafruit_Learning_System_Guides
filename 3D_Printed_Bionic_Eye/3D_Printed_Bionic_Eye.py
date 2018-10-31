# Bionic Eye sketch for Adafruit Trinket.
#
# written by Bill Earl for Arduino
# ported to CircuitPython by Mikey Sklar
# for Adafruit Industries
#
# Required library is the Adafruit_SoftServo library
# available at https://github.com/adafruit/Adafruit_SoftServo
# The standard Arduino IDE servo library will not work with 8 bit
# AVR microcontrollers like Trinket and Gemma due to differences
# in available timer hardware and programming. We simply refresh
# by piggy-backing on the timer0 millis() counter
#
# Trinket:        Bat+    Gnd       Pin #0  Pin #2
# Connection:     Servo+  Servo-    Tilt    Rotate
#                 (Red)   (Black)   Servo   Servo
#                                   (Orange)(Orange)

import time
import random
import board
import pulseio
from adafruit_motor import servo

# we are intentionally avoiding Trinket Pin #1 (board.A0)
# as it does not have PWM capability
tilt_servo_pin = board.A2   # servo control line (orange) Trinket Pin #0
rotate_servo_pin = board.A1 # servo control line (orange) Trinket Pin #2

# servo object setup for the M0 boards:
tilt_pwm = pulseio.PWMOut(tilt_servo_pin, duty_cycle=2 ** 15, frequency=50)
rotate_pwm = pulseio.PWMOut(rotate_servo_pin, duty_cycle=2 ** 15, frequency=50)
tilt_servo = servo.Servo(tilt_pwm)
rotate_servo = servo.Servo(rotate_pwm)

# servo timing and angle range
tilt_min = 120      # lower limit to tilt rotation range
max_rotate = 180    # rotation range limited to half circle

while True:

    # servo tilt - on average move every 500ms
    if random.randint(0,100) > 80:
        tilt_servo.angle = random.randint(tilt_min, max_rotate)
        time.sleep(.25)

    # servo rotate - on average move every 500ms
    if random.randint(0,100) > 90:
        rotate_servo.angle = random.randint(0, max_rotate)
        time.sleep(.25)
