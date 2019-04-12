# Circuit Playground Express Piñata by Dano Wall for Adafruit Industries
# CircuitPython code by Mike Barela for Adafruit Industries, MIT License
import time
import random
import board
import pulseio
from adafruit_motor import servo
from adafruit_circuitplayground.express import cpx

# create a PWMOut object on CPX Pin A1
pwm = pulseio.PWMOut(board.A1, frequency=50)
# Create a servo object cpx_servo
cpx_servo = servo.Servo(pwm)

hits = 0
max_hits = random.randint(3, 10)
cpx.detect_taps = 1  # Detect single taps
cpx_servo.angle = 0
cpx.pixels.fill((0, 0, 0))  # All NeoPixels off

while hits < max_hits:
    if cpx.tapped:
        print("Hit!")
        hits += 1
        cpx.pixels.fill((255, 255, 255))  # All White
        cpx.play_file("hit.wav")
        time.sleep(1.0)  # Wait time in seconds
        cpx.pixels.fill((0, 0, 0))  # All off
    time.sleep(0.1)

# Hits Reached, Payout!
print("Release!")
cpx.pixels.fill((0, 255, 0))  # All green
cpx.play_file("candy.wav")
cpx_servo.angle = 180
print("Press Reset or power cycle to reset device")
while True:
    pass     # Infinite loop, press Reset button to reset
