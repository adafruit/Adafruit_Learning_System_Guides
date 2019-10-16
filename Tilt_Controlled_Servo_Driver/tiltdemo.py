"""
In this Demo we will drive two servos based on the Tilt along the Y and Z axis
of the BNO055 9-Degrees of Freedom IMU Sensor. This could easily be extended
to drive servos on all three axis as well as use a host of other information
including lateral acceleration.
"""

import board
import busio
from adafruit_servokit import ServoKit
import adafruit_bno055

# Set channels to the number of servo channels on your kit.
kit = ServoKit(channels=16)

# Setup the BNO055 to read data
i2c = busio.I2C(board.SCL, board.SDA)
sensor = adafruit_bno055.BNO055(i2c)

while True:
    # Get the Euler angles from the BNO055
    (x, y, z) = sensor.euler

    # Euler angles are between -180 and 180
    # We want to translate them to the Servo angles between 0-180
    try:
        kit.servo[0].angle = (y + 180) / 2
        kit.servo[1].angle = (z + 180) / 2
    except ValueError:
        # Pass on any values that are out of range
        pass
