import board
import time
import pulseio
from digitalio import DigitalInOut, Direction, Pull
from analogio import AnalogIn
import adafruit_motor.servo

pwm = pulseio.PWMOut(board.D5, frequency=50)
servo = adafruit_motor.servo.Servo(pwm)
switch = DigitalInOut(board.D7)
switch.direction = Direction.INPUT
switch.pull = Pull.UP
pot = AnalogIn(board.A0)

continuous = adafruit_motor.servo.ContinuousServo(pwm)


def val(pin):
    # divides voltage (65535) to get a value between 0 and 1
    return pin.value / 65535


while True:

    if switch.value:
        continuous.throttle = val(pot) * -1
    else:
        continuous.throttle = val(pot) * 1

    time.sleep(0.001)
