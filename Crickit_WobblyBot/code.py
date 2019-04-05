"""
Continuous servo based walking/waddling/etc robot.

Adafruit invests time and resources providing this open source code.
Please support Adafruit and open source hardware by purchasing
products from Adafruit!

Written by Dave Astels for Adafruit Industries
Copyright (c) 2018 Adafruit Industries
Licensed under the MIT license.

All text above must be included in any redistribution.
"""

import time
from adafruit_crickit import crickit

tail = crickit.dc_motor_1

# Each servo corresponds to one of the legs
front_right = crickit.continuous_servo_1
front_left = crickit.continuous_servo_2
rear_right = crickit.continuous_servo_3
rear_left = crickit.continuous_servo_4

# Useful groups of legs
all_legs = [front_right, front_left, rear_right, rear_left]
front_legs = [front_right, front_left]
rear_legs = [rear_right, rear_left]
right_legs = [front_right, rear_right]
left_legs = [front_left, rear_left]

# The sign (+1/-1) for forward motion for each servo
direction_values = {front_right: +1,
                    front_left: -1,
                    rear_right: +1,
                    rear_left: -1}

# Tweak the pwn ranges for each servo so that throttle of 0 stops the motor
pwm_ranges = {front_right: (500, 2400),
              front_left: (500, 2400),
              rear_right: (500, 2400),
              rear_left: (500, 2400)}


def init():
    for leg in all_legs:
        limits = pwm_ranges[leg]
        leg.set_pulse_width_range(min_pulse=limits[0], max_pulse=limits[1])
        leg.throttle = 0


def wag(speed):
    tail.throttle = speed
    time.sleep(0.1)
    tail.throttle = 0.0
    time.sleep(0.25)


def wag_for(seconds):
    target_time = time.monotonic() + seconds
    wag_throttle = 1.0
    while time.monotonic() < target_time:
        wag(wag_throttle)
        wag_throttle *= -1


def forward(servo_or_servos, speed):
    if isinstance(servo_or_servos, list):
        for servo in servo_or_servos:
            servo.throttle = speed * direction_values[servo]
    else:
        servo_or_servos.throttle = speed * direction_values[servo_or_servos]


def reverse(servo_or_servos, speed):
    if isinstance(servo_or_servos, list):
        for servo in servo_or_servos:
            servo.throttle = speed * -1 * direction_values[servo]
    else:
        servo_or_servos.throttle = speed * -1 * direction_values[servo_or_servos]


def stop(servo_or_servos):
    if isinstance(servo_or_servos, list):
        for servo in servo_or_servos:
            servo.throttle = 0
    else:
        servo_or_servos.throttle = 0


def rotate_clockwise(speed):
    forward(left_legs, speed)
    reverse(right_legs, speed)


def rotate_counterclockwise(speed):
    forward(right_legs, speed)
    reverse(left_legs, speed)


def crawl_forward(speed):
    forward(all_legs, speed)


def crawl_backward(speed):
    reverse(all_legs, speed)


def turtle():
    stop([rear_right, rear_left])
    stop(rear_left)
    forward(front_right, 0.5)
    forward(front_left, 0.5)


def snake_step():
    stop(all_legs)
    forward(right_legs, 0.5)
    time.sleep(1.0)
    stop(right_legs)
    forward(left_legs, 0.5)
    time.sleep(1.0)
    stop(left_legs)


init()

def demo1():
    crawl_forward(0.5)
    wag_for(5.0)
    rotate_clockwise(0.25)
    wag_for(3.0)
    crawl_backward(0.5)
    wag_for(2.0)
    rotate_counterclockwise(0.25)
    wag_for(3.0)
    crawl_forward(0.5)
    wag_for(5.0)
    stop(all_legs)

demo1()
