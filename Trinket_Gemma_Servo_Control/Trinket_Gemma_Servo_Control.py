import time
import board
from analogio import AnalogIn
import simpleio

# servo pin for the M0 boards:
servo = simpleio.Servo(board.A2)
angle = 0

# potentiometer 
trimpot = AnalogIn(board.A1)  # pot pin for servo control

def remapRange(value, leftMin, leftMax, rightMin, rightMax):
    # this remaps a value from original (left) range to new (right) range
    # Figure out how 'wide' each range is
    leftSpan = leftMax - leftMin
    rightSpan = rightMax - rightMin

    # Convert the left range into a 0-1 range (int)
    valueScaled = int(value - leftMin) / int(leftSpan)

    # Convert the 0-1 range into a value in the right range.
    return int(rightMin + (valueScaled * rightSpan))

while True:
    angle = remapRange(trimpot.value, 0, 65535, 0, 180)
    servo.angle = angle
    #time.sleep(0.05)
