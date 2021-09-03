import time
import board
from digitalio import DigitalInOut, Direction, Pull

#  LED setup for onboard LED
led = DigitalInOut(board.LED)
led.direction = Direction.OUTPUT

#  button setup
switch = DigitalInOut(board.D4)
switch.direction = Direction.INPUT
switch.pull = Pull.UP

#  variable for number count
n = 0

while True:

	#  when switch is NOT pressed...
    if switch.value:
		#  LED is off
        led.value = False
	#  when switch is pressed...
    else:
		#  LED is on
        led.value = True
		#  value of n increases by 1
        n += 1
		#  n is printed to the REPL
        print("led ON %i" % n)
	#  delay
    time.sleep(0.01)
