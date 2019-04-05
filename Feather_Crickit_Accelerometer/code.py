import time
import busio
import board
from adafruit_seesaw.seesaw import Seesaw
from adafruit_seesaw.pwmout import PWMOut
from adafruit_motor import servo
import adafruit_lsm9ds0

# Setup hardware
i2c = busio.I2C(board.SCL, board.SDA)

sensor = adafruit_lsm9ds0.LSM9DS0_I2C(i2c)
seesaw = Seesaw(i2c)

# Create servo objects
pwm1 = PWMOut(seesaw, 17)
pwm1.frequency = 50
servo1 = servo.Servo(pwm1, min_pulse=500, max_pulse=2500)

# Center the servo
servo1.angle = 90

while True:
    # Read the accel
    x, y, z = sensor.acceleration

    # Clip the value
    if y < -10:
        y = -10
    if y > 10:
        y = 10

    # print(((y / 10) + 1) * 90)

    # Set the angle
    servo1.angle = ((-y / 10) + 1) * 90

    time.sleep(0.1)
