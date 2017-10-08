from digitalio import DigitalInOut, Direction
import board 
import neopixel
import time

pixpin = board.D1
numpix = 5

led = DigitalInOut(board.D13)
led.direction = Direction.OUTPUT

strip = neopixel.NeoPixel(pixpin, numpix, brightness=1, auto_write=True)

def colorWipe(color, wait):
    for j in range(len(strip)):
	strip[j] = (color)
	time.sleep(wait)

while True:
    colorWipe( (50, 0, 50), .1 ) # Purple LEDs
