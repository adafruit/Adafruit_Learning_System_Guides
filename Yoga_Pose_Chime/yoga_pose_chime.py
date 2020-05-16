# Yoga pose timer
# Requires CLUE with solenoid transistor driver circuit

import time
import board
from digitalio import DigitalInOut, Direction
from adafruit_clue import clue
from adafruit_slideshow import SlideShow, PlayBackDirection

pose_time = 30  # choose the time to hold each pose in seconds

solenoid = DigitalInOut(board.D2)  # pad #2 on CLUE driving a MOSFET
solenoid.direction = Direction.OUTPUT
solenoid.value = False

def chime(repeat):
    for _ in range(repeat):
        solenoid.value = True
        time.sleep(0.03)
        solenoid.value = False
        time.sleep(0.25)

slideshow = SlideShow(clue.display, None, folder="/icons", auto_advance=False)

while True:
    if clue.proximity > 10:
        time.sleep(1)
        chime(1)
        time.sleep(pose_time)
        chime(2)
        slideshow.direction = PlayBackDirection.FORWARD
        slideshow.advance()

    if clue.button_b:  # skip ahead
        slideshow.direction = PlayBackDirection.FORWARD
        slideshow.advance()

    if clue.button_a:  # skip back
        slideshow.direction = PlayBackDirection.BACKWARD
        slideshow.advance()
