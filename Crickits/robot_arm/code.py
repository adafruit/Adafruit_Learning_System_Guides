# SPDX-FileCopyrightText: 2018 Limor Fried for Adafruit Industries
#
# SPDX-License-Identifier: MIT

#import time
from busio import I2C
from adafruit_seesaw.seesaw import Seesaw
from adafruit_seesaw.pwmout import PWMOut
from adafruit_motor import servo
import board

print("5 Servo Robot Arm Demo!")

# Create seesaw object
i2c = I2C(board.SCL, board.SDA)
seesaw = Seesaw(i2c)

pots = (2, 3, 40, 41, 11)

# Create servos list
servos = []
for ss_pin in (17, 16, 15, 14, 22):
    pwm = PWMOut(seesaw, ss_pin)
    pwm.frequency = 50
    _servo = servo.Servo(pwm)
    servos.append(_servo)

# Maps a number from one range to another.
def map_range(x, in_min, in_max, out_min, out_max):
    mapped = (x-in_min) * (out_max - out_min) / (in_max-in_min) + out_min
    if out_min <= out_max:
        return max(min(mapped, out_max), out_min)
    return min(max(mapped, out_max), out_min)

servo_angles = [90] * 4

while True:
    readings = []
    angles = []
    for i in range(len(pots)):
	# Read 5 potentiometers
        reading = seesaw.analog_read(pots[i])
        readings.append(reading)
	# Map 10-bit value to servo angle
        if i == 5:
	    # The 5th servo is for the claw and it doesnt need full range
            angle = int(map_range(reading, 0, 1023, 0, 50))
        else:
	    # Other 4 servos are for motion, map to 180 degrees!
            angle = int(map_range(reading, 0, 1023, 0, 180))
        angles.append(angle)
	# set the angle
        servos[i].angle = angle
    # For our debugging!
    print(readings, angles)
