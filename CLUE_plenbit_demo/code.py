# SPDX-FileCopyrightText: 2020 Limor Fried for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import busio
import board
from digitalio import DigitalInOut, Direction
from adafruit_pca9685 import PCA9685
from adafruit_motor import servo

led = DigitalInOut(board.P16)
led.direction = Direction.OUTPUT

i2c = busio.I2C(board.SCL, board.SDA)
pca = PCA9685(i2c, address=0x68)
pca.frequency = 50
servoSetInit = (1000, 630, 500, 600, 240, 600, 1000, 720)
servoAngle = [1000, 630, 500, 600, 240, 600, 1000, 720]
motionSpeed = 15
servos = []
for c in range(8):
    servos.append(servo.Servo(pca.channels[c], min_pulse=800, max_pulse=2200))

def servoInitialSet():
    print("Initialize servos")
    for i in range(8):
        servos[i].angle = servoSetInit[i] / 10

def servoFree(n = None):
    if n:
        print("Release servo #", n)
        servos[n].angle = None
    else:
        print("Release all servos")
        for s in servos:
            s.angle = None

def servoWrite(num, degrees):
    degrees = min(max(degrees, 0), 180)
    servos[num].angle = degrees

# angle is a list of 8 target values
def setAngle(angle, msec):
    step = [0, 0, 0, 0, 0, 0, 0, 0]
    msec = msec / motionSpeed # now 15//default 10; //speedy 20   Speed Adj
    for val in range(8):
        target = servoSetInit[val] - angle[val]
        target = min(max(target, 0), 1800)
        if target != servoAngle[val]: # Target != Present
            step[val] = (target - servoAngle[val]) / msec
    #print(step)
    for _ in range(msec):
        for val in range(8):
            servoAngle[val] += step[val]
            #print("setting servo %d to %d" % (val, int(servoAngle[val] / 10)))
            servoWrite(val, servoAngle[val] / 10)
        #time.sleep(msec / 1000)
    print(servoAngle)

servoInitialSet()

led.value = False
setAngle([0, 0, -200, 0, 0, 0, 0, 0], 500)
setAngle([0, 0, -1800, 0, 0, 0, 1800, 0], 500)
setAngle([900, 0, -1800, 0, -900, 0, 1800, 0], 500)
setAngle([900, 0, -200, 0, -900, 0, 0, 0], 500)
setAngle([900, 0, -1800, 0, -900, 0, 1800, 0], 500)
setAngle([900, 0, -200, 0, -900, 0, 0, 0], 500)
setAngle([0, 0, -200, 0, 0, 0, 0, 0], 500)
led.value = True

servoFree()
