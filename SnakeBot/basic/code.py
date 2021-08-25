import time
from adafruit_crickit import crickit

ss = crickit.seesaw

left_wheel = crickit.dc_motor_1
right_wheel = crickit.dc_motor_2


# These allow easy correction for motor speed variation.
# Factors are determined by observation and fiddling.
# Start with both having a factor of 1.0 (i.e. none) and
# adjust until the bot goes more or less straight
def set_right(speed):
    right_wheel.throttle = speed * 0.9

def set_left(speed):
    left_wheel.throttle = speed


# Uncomment this to find the above factors
# set_right(1.0)
# set_left(1.0)
# while True:
#     pass

while True:
    # tack left
    set_left(0.25)
    set_right(1.0)
    time.sleep(0.75)

    # tack right
    set_left(1.0)
    set_right(0.25)
    time.sleep(0.75)
