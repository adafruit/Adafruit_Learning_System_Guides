# SPDX-FileCopyrightText: 2022 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
import pwmio
import neopixel
from adafruit_motor import servo
from adafruit_led_animation.animation.comet import Comet
from adafruit_led_animation.sequence import AnimationSequence
from adafruit_led_animation.color import PURPLE

#  create 2 PWM instances for the servos
left_pwm = pwmio.PWMOut(board.A3, duty_cycle=2 ** 15, frequency=50)
right_pwm = pwmio.PWMOut(board.A6, duty_cycle=2 ** 15, frequency=50)

#  left wing servo
left_servo = servo.Servo(left_pwm)
#  right wing servo
right_servo = servo.Servo(right_pwm)

#  use onboard neopixels on CPX
pixel_pin = board.NEOPIXEL
#  number of onboard neopixels
num_pixels = 10

#  neopixels object
pixels = neopixel.NeoPixel(pixel_pin, num_pixels, brightness=0.05, auto_write=False)

#  comet animation
comet = Comet(pixels, speed=0.01, color=PURPLE, tail_length=10, bounce=True)

#  create animation sequence
animations = AnimationSequence(comet)

#  beginning angles for each wing
left_angle = 100
right_angle = 30

while True:
	#  run comet animation while servos move
    animations.animate()

	#  left angle decreases by 10
    left_angle = left_angle - 10
	#  once it's less than 30 degrees, reset to 100
    if left_angle < 30:
        left_angle = 100
	#  right angle increases by 10
    right_angle = right_angle + 10
	#  once it's greater than 100, reset to 30
    if right_angle > 100:
        right_angle = 30
	#  move left wing
    left_servo.angle = left_angle
	#  move right wing
    right_servo.angle = right_angle
	#  delay
    time.sleep(0.05)
