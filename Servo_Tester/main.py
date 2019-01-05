"""
Servo Tester

Adafruit invests time and resources providing this open source code.
Please support Adafruit and open source hardware by purchasing
products from Adafruit!

Written by Dave Astels for Adafruit Industries
Copyright (c) 2018 Adafruit Industries
Licensed under the MIT license.

All text above must be included in any redistribution.
"""

import time
import board
import busio
import digitalio
import rotaryio
import pulseio
import adafruit_ssd1306
from adafruit_motor import servo
from adafruit_debouncer import Debouncer

#--------------------------------------------------------------------------------
# Initialize Rotary encoder

button_io = digitalio.DigitalInOut(board.D12)
button_io.direction = digitalio.Direction.INPUT
button_io.pull = digitalio.Pull.UP
button = Debouncer(button_io)
rotary_encoder = rotaryio.IncrementalEncoder(board.D10, board.D11)

#--------------------------------------------------------------------------------
# Initialize I2C and OLED

i2c = busio.I2C(board.SCL, board.SDA)

oled = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c)
oled.fill(0)
oled.show()

min_pulses = [ 500,  550,  600,  650,  700,  750,  800,  850,  900,  950, 1000]
max_pulses = [2000, 2050, 2100, 2150, 2200, 2250, 2300, 2350, 2400, 2450, 2500]

min_pulse_index = 10
max_pulse_index = 0

#-------------------------------------------------------------------------------
# Initialize servo

pwm = pulseio.PWMOut(board.D5, frequency=50)
test_servo = servo.Servo(pwm, min_pulse=1000, max_pulse=2000)
test_servo.angle = 0

current_position = None               # current encoder position
change = 0                            # the change in encoder position
angle = 0
mode = 0
sweep_time = 1.0
last_movement_at = 0.0
delta = 5


def get_encoder_change(encoder, pos):
    new_position = encoder.position
    if pos is None:
        return (new_position, 0)
    else:
        return (new_position, new_position - pos)

#--------------------------------------------------------------------------------
# Main loop

while True:
    now = time.monotonic()
    button.update()

    if mode == 1:
        if now >= (last_movement_at + sweep_time / 36):
            last_movement_at = now
            angle += delta
            if (angle > 180) or (angle < 0):
                delta *= -1
                angle += delta

    if button.fell:
        servo.angle = 0
        if mode == 0:
            mode = 1
            sweep_time = 1.0
            last_movement_at = now
        elif mode == 1:
            mode = 2
            angle = 0
        elif mode == 2:
            mode = 3
            angle = 180
        elif mode == 3:
            mode = 0
            angle = 0

    else:
        current_position, change = get_encoder_change(rotary_encoder, current_position)
        if change != 0:
            if mode == 0:
                angle = min(180, max(0, angle + change * 5))
            elif mode == 1:
                sweep_time = min(5.0, max(1.0, sweep_time + change * 0.1))
            elif mode == 2:
                min_pulse_index = min(10, max(min_pulse_index + change, 0))
                test_servo = servo.Servo(pwm,
                                         min_pulse=min_pulses[min_pulse_index],
                                         max_pulse=max_pulses[max_pulse_index])
                angle = 0
            elif mode == 3:
                max_pulse_index = min(10, max(max_pulse_index + change, 0))
                test_servo = servo.Servo(pwm,
                                         min_pulse=min_pulses[min_pulse_index],
                                         max_pulse=max_pulses[max_pulse_index])
                angle = 180

    oled.fill(0)
    if mode == 0:
        oled.text("Angle: {0}".format(angle), 0, 0)
    elif mode == 1:
        oled.text("Sweep time: {0}".format(sweep_time), 0, 0)
    elif mode == 2:
        oled.text("Min width: {0}".format(min_pulses[min_pulse_index]), 0, 0)
    elif mode == 3:
        oled.text("Max width: {0}".format(max_pulses[max_pulse_index]), 0, 0)
    oled.show()

    test_servo.angle = angle
