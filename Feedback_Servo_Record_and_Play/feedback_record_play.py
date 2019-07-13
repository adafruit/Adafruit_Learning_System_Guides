# Example code for recording and playing back servo motion with a
# analog feedback servo

import time
import board
import pulseio
from simpleio import map_range
from adafruit_motor import servo
from analogio import AnalogIn
from digitalio import DigitalInOut, Direction, Pull

# Pin setup
RECORD_PIN = board.D10
PLAY_PIN = board.D9
LED_PIN = board.D13
SERVO_PIN = board.A1
FEEDBACK_PIN = board.A5

# Record setup
CALIB_MIN = 2816
CALIB_MAX = 49632
ANGLE_MIN = 0
ANGLE_MAX = 180
SAMPLE_COUNT = 512
SAMPLE_DELAY = 0.025

# Setup record button
record_button = DigitalInOut(RECORD_PIN)
record_button.direction = Direction.INPUT
record_button.pull = Pull.UP

# Setup play button
play_button = DigitalInOut(PLAY_PIN)
play_button.direction = Direction.INPUT
play_button.pull = Pull.UP

# Setup LED
led = DigitalInOut(LED_PIN)
led.direction = Direction.OUTPUT
led.value = False

# Setup servo
pwm = pulseio.PWMOut(SERVO_PIN, duty_cycle=2 ** 15, frequency=50)
servo = servo.Servo(pwm)
servo.angle = None

# Setup feedback
feedback = AnalogIn(FEEDBACK_PIN)

# Servo positions stored here
position = [None]*SAMPLE_COUNT

print("Servo RecordPlay")

def play_servo():
    print("Playing...", end="")
    count = 0
    while play_button.value:
        print(".", end="")
        angle = position[count]
        if angle is None:
            break
        servo.angle = angle
        count += 1
        if count >= SAMPLE_COUNT:
            break
        time.sleep(SAMPLE_DELAY)
    print("Done.")
    servo.angle = None
    time.sleep(0.250)

def record_servo():
    for i in range(len(position)):
        position[i] = None
    servo.angle = None
    led.value = True
    print("Recording...", end="")
    count = 0
    while record_button.value:
        print(".", end='')
        position[count] = map_range(feedback.value, CALIB_MIN, CALIB_MAX, ANGLE_MIN, ANGLE_MAX)
        count += 1
        if count >= SAMPLE_COUNT:
            break
        time.sleep(SAMPLE_DELAY)
    led.value = False
    print("Done.")
    time.sleep(0.250)

while True:
    if not record_button.value:
        time.sleep(0.01)
        # wait for released
        while not record_button.value:
            pass
        time.sleep(0.02)
        # OK released!
        record_servo()

    if not play_button.value:
        time.sleep(0.01)
        # wait for released
        while not play_button.value:
            pass
        time.sleep(0.02)
        # OK released!
        play_servo()
