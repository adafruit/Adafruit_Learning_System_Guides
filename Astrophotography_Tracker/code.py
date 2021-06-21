import time
import board
import digitalio

worm_ratio = 40/1
belt_ratio = 100/60
gear_ratio = worm_ratio * belt_ratio

steps = 200 # Steps per revolution
microsteps = 64 # Microstepping resolution
total_steps = steps * microsteps # Total microsteps per revolution

wait = 1/ ((gear_ratio * total_steps) / 86164.1)

step = digitalio.DigitalInOut(board.D6)
direct = digitalio.DigitalInOut(board.D5)

step.direction = digitalio.Direction.OUTPUT
direct.direction = digitalio.Direction.OUTPUT

direct.value = True

while True:
    step.value = True
    time.sleep(0.001)
    step.value = False
    time.sleep(wait - 0.001)
