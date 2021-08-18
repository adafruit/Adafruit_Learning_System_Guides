import time

import board
import simpleio

servo = simpleio.Servo(board.A2)

while True:
    for angle in range(0, 180, 5):  # 0-180 degrees, 5 degrees at a time
        servo.angle = angle
        time.sleep(0.05)
    for angle in range(180, 0, -5):  # 180-0 degrees, 5 degrees at a time
        servo.angle = angle
        time.sleep(0.05)
