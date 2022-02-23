# SPDX-FileCopyrightText: 2018 Limor Fried for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
from digitalio import DigitalInOut, Direction, Pull
import adafruit_lis3dh
from busio import I2C
from adafruit_seesaw.seesaw import Seesaw
from adafruit_seesaw.pwmout import PWMOut
from adafruit_motor import servo
import neopixel
import board

# create accelerometer
i2c1 = I2C(board.ACCELEROMETER_SCL, board.ACCELEROMETER_SDA)
lis3dh = adafruit_lis3dh.LIS3DH_I2C(i2c1, address=0x19)
lis3dh.range = adafruit_lis3dh.RANGE_8_G

# Create seesaw object
i2c = I2C(board.SCL, board.SDA)
seesaw = Seesaw(i2c)

# Create servo object
pwm = PWMOut(seesaw, 17)    # Servo 1 is on s.s. pin 17
pwm.frequency = 50          # Servos like 50 Hz signals
my_servo = servo.Servo(pwm) # Create my_servo with pwm signal

# LED for debugging
led = DigitalInOut(board.D13)
led.direction = Direction.OUTPUT

# two buttons!
button_a = DigitalInOut(board.BUTTON_A)
button_a.direction = Direction.INPUT
button_a.pull = Pull.DOWN
button_b = DigitalInOut(board.BUTTON_B)
button_b.direction = Direction.INPUT
button_b.pull = Pull.DOWN

# NeoPixels!
pixels = neopixel.NeoPixel(board.NEOPIXEL, 10, brightness=1)
pixels.fill((0,0,0))

#################### log file for logging mode!
logfile = "/log.csv"
# check that we could append if wanted to
try:
    fp = None
    fp = open(logfile, "a")
    print("File system writable!")
# pylint: disable=bare-except
except:
    print("Not logging, trapeeze mode!")

# If we log, have some helper variables
logging = False
logpoints = 0
outstr = ""

# When its time to release the trapeze
release = False

while True:
    if button_a.value: # A pressed
        while button_a.value:	# wait for release
            pass
        if fp:  # start or stop logging
            logging = not logging
            print("Logging: ", logging)
            time.sleep(0.25)
        else:
            my_servo.angle = 180      # open

    if button_b.value: # B pressed
        while button_b.value:	# wait for release
            pass
        my_servo.angle = 0      # close

    x, y, z = lis3dh.acceleration

    # To keep from corrupting the filesys, take 25 readings at once
    if logging and fp:
        outstr += "%0.2F, %0.2F, %0.2F\n" % (x, y, z)
        logpoints += 1

        if logpoints > 25:
            led.value = True
            #print("Writing: "+outstr)
            fp.write(outstr+"\n")
            fp.flush()
            led.value = False
            logpoints = 0
    else:
        # display some neopixel output!
        if z > 20:
            # MAXIMUM EFFORT!
            pixels.fill((0, 255, 0))
            if release:
                my_servo.angle = 180

        elif z < 3 and y > 0: # means at the outer edge
            release = True
            # flash red when we peak
            pixels.fill((255, 0, 0))

        else:
            pixels.fill((0,0,int(abs(z)*2)))

    time.sleep(0.05)
