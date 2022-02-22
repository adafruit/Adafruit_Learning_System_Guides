# SPDX-FileCopyrightText: 2018 Limor Fried for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import audioio
import audiocore
from digitalio import DigitalInOut, Pull, Direction
from adafruit_seesaw.seesaw import Seesaw
from adafruit_seesaw.pwmout import PWMOut
from adafruit_motor import stepper
from busio import I2C
import neopixel
import board

# Create seesaw object
i2c = I2C(board.SCL, board.SDA)
seesaw = Seesaw(i2c)

led = DigitalInOut(board.D13)
led.direction = Direction.OUTPUT

buttona = DigitalInOut(board.BUTTON_A)
buttona.direction = Direction.INPUT
buttona.pull = Pull.DOWN

buttonb = DigitalInOut(board.BUTTON_B)
buttonb.direction = Direction.INPUT
buttonb.pull = Pull.DOWN

BOTTOM_SENSOR = 2
TOP_SENSOR = 3
seesaw.pin_mode(BOTTOM_SENSOR, seesaw.INPUT_PULLUP)
seesaw.pin_mode(TOP_SENSOR, seesaw.INPUT_PULLUP)

# Create one stepper motor using the 4 'drive' PWM pins 13, 43, 12 and 42
pwms = [PWMOut(seesaw, 13), PWMOut(seesaw, 43), PWMOut(seesaw, 12), PWMOut(seesaw, 42)]
for p in pwms:
    p.frequency = 2000
stepper_motor = stepper.StepperMotor(pwms[0], pwms[1], pwms[2], pwms[3])

pixels = neopixel.NeoPixel(board.NEOPIXEL, 10, brightness=1)
pixels.fill((0,0,0))


def rainbow():
    pixels.fill((20,0,0))
    time.sleep(0.05)
    pixels.fill((20,20,0))
    time.sleep(0.05)
    pixels.fill((0,20,0))
    time.sleep(0.05)
    pixels.fill((0,20,20))
    time.sleep(0.05)
    pixels.fill((0,0,20))
    time.sleep(0.05)
    pixels.fill((20,0,20))
    time.sleep(0.05)

# Audio playback object and helper to play a full file
a = audioio.AudioOut(board.A0)
def play_file(wavfile):
    with open(wavfile, "rb") as file:
        wavf = audiocore.WaveFile(file)
        a.play(wavf)
        while a.playing:
            rainbow()


last_b_time = last_a_time = 0
steps = speed = 0
MINIMUM_SPEED = 1  # in taps per second
drift_counter = 0
TOUCH_THRESH = 900
won = False

def reset():
    print("Resetting..", end="")
    while seesaw.digital_read(BOTTOM_SENSOR):
        stepper_motor.onestep(direction=stepper.BACKWARD, style=stepper.DOUBLE)
    print("Done!")

print("Racooon crawl!")

reset()
paused = False

while True:
    # pause button B
    if buttonb.value:
        while buttonb.value:
            pass
        paused = not paused

    # reset button A
    if buttona.value:
        while buttona.value:
            pass
        pixels.fill((0, 0, 0))
        reset()

    if not seesaw.digital_read(TOP_SENSOR):
        play_file("madeit.wav")
        for i in range(20):
            rainbow()
        reset()
    #print(seesaw.touch_read(0))
    #print(seesaw.touch_read(3))
    if seesaw.touch_read(0) > TOUCH_THRESH:
        while seesaw.touch_read(0) > TOUCH_THRESH:
            pass
        last_a_time = time.monotonic()

    if seesaw.touch_read(3) > TOUCH_THRESH:
        while seesaw.touch_read(3) > TOUCH_THRESH:
            pass
        last_b_time = time.monotonic()

    delta_a = time.monotonic() - last_a_time
    delta_b = time.monotonic() - last_b_time
    #print("Lately... %0.1f & %0.1f" % (delta_a, delta_b))

    speed = 1.0 / max(delta_a, delta_b)
    print("Speed %0.1f\tSteps %d" % (speed, steps))
    if speed > MINIMUM_SPEED:
        # Climb up
        pixels.fill((0, int(speed*10), 0))
        for i in range(6):
            stepper_motor.onestep(direction=stepper.FORWARD, style=stepper.DOUBLE)
            steps += 1
    elif not paused:
        # Fall down
        pixels.fill((50, 0, 0))
        if seesaw.digital_read(BOTTOM_SENSOR):
            stepper_motor.onestep(direction=stepper.BACKWARD)
            steps -= 1
