import board
import analogio
import time
import neopixel

# Initialize input/output pins
sensorpin = board.A1        # input pin for the potentiometer 
sensor = analogio.AnalogIn(sensorpin)

pixpin = board.D1           # pin where NeoPixels are connected
numpix = 8                  # number of neopixels
strip  = neopixel.NeoPixel(pixpin, numpix, brightness=.15, auto_write=False) 

colorvalue = 0
sensorvalue = 0

def wheel(pos):
    # Input a value 0 to 255 to get a color value.
    # The colours are a transition r - g - b - back to r.
    if (pos < 0) or (pos > 255):
        return (0, 0, 0)
    if (pos < 85):
        return (int(pos * 3), int(255 - (pos*3)), 0)
    elif (pos < 170):
        pos -= 85
        return (int(255 - pos*3), 0, int(pos*3))
    else:
        pos -= 170
        return (0, int(pos*3), int(255 - pos*3))

def remapRange(value, leftMin, leftMax, rightMin, rightMax):
    # this remaps a value from original (left) range to new (right) range
    # Figure out how 'wide' each range is
    leftSpan = leftMax - leftMin
    rightSpan = rightMax - rightMin

    # Convert the left range into a 0-1 range (int)
    valueScaled = int(value - leftMin) / int(leftSpan)

    # Convert the 0-1 range into a value in the right range.
    return int(rightMin + (valueScaled * rightSpan))

# Loop forever...
while True:  

    # remap the potentiometer analog sensor values from 0-65535 to RGB 0-255
    colorvalue = remapRange(sensor.value, 0, 65535, 0, 255)

    for i in range( 0, len(strip) ):
        strip[i] = wheel(colorvalue)
    strip.write()
