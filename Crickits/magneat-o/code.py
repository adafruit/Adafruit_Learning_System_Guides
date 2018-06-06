import time
from busio import I2C
from adafruit_seesaw.seesaw import Seesaw
from adafruit_seesaw.pwmout import PWMOut
from adafruit_motor import motor
from digitalio import DigitalInOut, Direction, Pull
import board

print("Mag Neat-o!")

# Create seesaw object
i2c = I2C(board.SCL, board.SDA)
seesaw = Seesaw(i2c)

# Create one motor on seesaw PWM pins 22 & 23
motor_a = motor.DCMotor(PWMOut(seesaw, 22), PWMOut(seesaw, 23))
# Create another motor on seesaw PWM pins 19 & 18
motor_b = motor.DCMotor(PWMOut(seesaw, 19), PWMOut(seesaw, 18))

buttona = DigitalInOut(board.BUTTON_A)
buttona.direction = Direction.INPUT
buttona.pull = Pull.DOWN

buttonb = DigitalInOut(board.BUTTON_B)
buttonb.direction = Direction.INPUT
buttonb.pull = Pull.DOWN

switch = DigitalInOut(board.SLIDE_SWITCH)
switch.direction = Direction.INPUT
switch.pull = Pull.UP

last_buttona = buttona.value
last_buttonb = buttonb.value
last_switch = switch.value

while True:
    if buttona.value != last_buttona:
        if buttona.value:
            print("down")
            if motor_a.throttle:
                print("haulin!")
                motor_b.throttle = -0.1
            else:
                motor_b.throttle = -0.1
        else:
            motor_b.throttle = 0
        last_buttona = buttona.value

    if buttonb.value != last_buttonb:
        if buttonb.value:
            print("up")
            if motor_a.throttle:
                print("haulin!")
                motor_b.throttle = 0.3
            else:
                motor_b.throttle = 0.25
        else:
            motor_b.throttle = 0
        last_buttonb = buttonb.value

    if switch.value != last_switch:
        motor_a.throttle = switch.value
        last_switch = switch.value

    time.sleep(0.01)
