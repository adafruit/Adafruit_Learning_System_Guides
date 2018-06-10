import time
from busio import I2C
from adafruit_seesaw.seesaw import Seesaw
from adafruit_seesaw.pwmout import PWMOut
from adafruit_motor import motor, servo
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

# Create servo object
pwm = PWMOut(seesaw, 17)     # Servo 1 is on s.s. pin 17
pwm.frequency = 50           # Servos like 50 Hz signals
my_servo = servo.Servo(pwm)  # Create my_servo with pwm signa
my_servo.angle = 90

def smooth_move(start, stop, num_steps):
    return [(start + (stop-start)*i/num_steps) for i in range(num_steps)]

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

last_touch1 = False
last_touch4 = False


while True:
    touch_vals = (seesaw.touch_read(0), seesaw.touch_read(3))
    # print(touch_vals)

    touch1 = False
    if seesaw.touch_read(0) > 500:
        touch1 = True

    if touch1 != last_touch1:
        if touch1:
            start_angle = my_servo.angle
            end_angle = start_angle - 20
            end_angle = max(0, min(end_angle, 180))
            print("left from", start_angle, "to", end_angle)
            for a in smooth_move(start_angle, end_angle, 25):
                my_servo.angle = a
                time.sleep(0.03)
        last_touch1 = touch1

    touch4 = False
    if seesaw.touch_read(3) > 500:
        touch4 = True

    if touch4 != last_touch4:
        if touch4:
            start_angle = my_servo.angle
            end_angle = start_angle + 20
            end_angle = max(0, min(end_angle, 180))
            print("right from", start_angle, "to", end_angle)
            for a in smooth_move(start_angle, end_angle, 25):
                my_servo.angle = a
                time.sleep(0.03)
        last_touch4 = touch4

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
                motor_b.throttle = 0.4
            else:
                motor_b.throttle = 0.3
        else:
            motor_b.throttle = 0
        last_buttonb = buttonb.value

    if switch.value != last_switch:
        motor_a.throttle = switch.value
    if motor_a.throttle:
        print("GRAB")
    else:
        print("RELEASE")
        last_switch = switch.value

    time.sleep(0.01)
