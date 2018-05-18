from busio import I2C
from adafruit_seesaw.seesaw import Seesaw
from adafruit_seesaw.pwmout import PWMOut
from adafruit_motor import motor
import board
import time

# Create seesaw object
i2c = I2C(board.SCL, board.SDA)
seesaw = Seesaw(i2c)

# Create one motor on seesaw PWM pins 22 & 23
motor_a = motor.DCMotor(PWMOut(seesaw, 22), PWMOut(seesaw, 23))
motor_a.throttle = 0.5  # half speed forward

# Create drive (PWM) object
my_drive = PWMOut(seesaw, 13)    # Drive 1 is on s.s. pin 13
my_drive.frequency = 1000        # Our default frequency is 1KHz

while True:

    my_drive.duty_cycle = 32768  # half on
    time.sleep(0.8)

    my_drive.duty_cycle = 16384  # dim
    time.sleep(0.1)
    
    # and repeat!
