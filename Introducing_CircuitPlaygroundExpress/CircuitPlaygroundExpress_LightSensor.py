# CircuitPlaygroundExpress_LightSensor
# reads the on-board light sensor and graphis the brighness with NeoPixels

from digitalio import DigitalInOut, Direction
from analogio import AnalogIn
import board
import neopixel
import time

pixels = neopixel.NeoPixel(board.NEOPIXEL, 10, auto_write=0, brightness=.1)
pixels.fill((0,0,0))
pixels.show()

led = DigitalInOut(board.D13)
led.direction = Direction.OUTPUT

analogin = AnalogIn(board.LIGHT)

# def mapColor(pin): #helper
#     return pin.value / 100
#
def remapRange(value, leftMin, leftMax, rightMin, rightMax):
    #this remaps a value from original (left) range to new (right) range
    # Figure out how 'wide' each range is
    leftSpan = leftMax - leftMin
    rightSpan = rightMax - rightMin

    # Convert the left range into a 0-1 range (int)
    valueScaled = int(value - leftMin) / int(leftSpan)

    # Convert the 0-1 range into a value in the right range.
    return int(rightMin + (valueScaled * rightSpan))


while True:
    #light value remaped to pixel position
    #print("Value translate %d" % remapRange(analogin.value, 0, 65000, 0, 9))
    peak = remapRange(analogin.value, 0, 65000, 0, 9)
    for i in range(0, peak, 1):
        #light up pixels in range 0 to the remaped light read
        pixels[i] = (0,255,0)
        #turn off pixels above peak range
        for j in range(peak+1, 10, 1):
            pixels[j] = (0, 0, 0)
        pixels.show()

    time.sleep(0.1)
