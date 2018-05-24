# Code for the Trash Panda tutorial with Adafruit Crickit and Circuit Playground Express 5/2018 Dano Wall

from digitalio import DigitalInOut, Direction, Pull
from adafruit_seesaw.seesaw import Seesaw
from adafruit_seesaw.pwmout import PWMOut
from adafruit_motor import servo
from busio import I2C
import board
import time

# Create seesaw object
i2c = I2C(board.SCL, board.SDA)
seesaw = Seesaw(i2c)

led = DigitalInOut(board.D13)
led.direction = Direction.OUTPUT

# Create servos list
servos = []
for ss_pin in (17, 16, 15, 14):
    pwm = PWMOut(seesaw, ss_pin)
    pwm.frequency = 50
    _servo = servo.Servo(pwm, min_pulse=600, max_pulse=2500)
    _servo.angle = 90   # starting angle, middle
    servos.append(_servo)
    
print("Its TRASH PANDA TIME!")

while True:
    print("tick")
    led.value = True
    servos[0].angle = 0
    time.sleep(0.5)
    servos[1].angle = 180
    time.sleep(0.5)
    servos[2].angle = 0
    time.sleep(0.5)
    print("tock")
    led.value = False
    servos[0].angle = 180
    time.sleep(0.5)
    servos[1].angle = 0
    time.sleep(0.5)
    servos[2].angle = 180
    time.sleep(0.5)
