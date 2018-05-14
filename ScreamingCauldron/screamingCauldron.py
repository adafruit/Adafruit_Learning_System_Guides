# Screaming Cauldron
# for Adafruit Industries Learning Guide

import time

import board
import neopixel
from analogio import AnalogIn
from digitalio import DigitalInOut, Direction

led = DigitalInOut(board.D13)  # on board red LED
led.direction = Direction.OUTPUT

aFXPin = DigitalInOut(board.D2)  # pin used to drive the AudioFX board
aFXPin.direction = Direction.OUTPUT

aFXPin.value = False  # runs once at startup
time.sleep(.1)  # pause a moment
aFXPin.value = True  # then turn it off

analog0in = AnalogIn(board.D1)
neoPin = board.D0  # pin int0 which the NeoPixels are plugged
numPix = 30  # number of NeoPixels
pixels = neopixel.NeoPixel(neoPin, numPix, auto_write=0, brightness=.8)
pixels.fill((0, 0, 0,))
pixels.show()


def get_voltage(pin):
    return (pin.value * 3.3) / 65536


def remap_range(value, left_min, left_max, right_min, right_max):
    # this remaps a value from original (left) range to new (right) range
    # Figure out how 'wide' each range is
    leftSpan = left_max - left_min
    rightSpan = right_max - right_min

    # Convert the left range into a 0-1 range (int)
    valueScaled = int(value - left_min) / int(leftSpan)

    # Convert the 0-1 range into a value in the right range.
    return int(right_min + (valueScaled * rightSpan))


while True:
    distRaw = analog0in.value  # read the raw sensor value
    print("A0: %f" % distRaw)  # write raw value to REPL
    distRedColor = remap_range(distRaw, 0, 64000, 0, 255)
    distGreenColor = remap_range(distRaw, 0, 64000, 200, 0)
    if distRaw > 40000:  # at about 4 inches, this goes off!
        led.value = True
        aFXPin.value = False
        time.sleep(.35)

    else:
        led.value = False
        aFXPin.value = True

    # change pixel colors based on proximity

    print(distRedColor, distGreenColor, (distRedColor + distGreenColor))
    pixels.fill((distRedColor, distGreenColor, 0))

    pixels.write()

    time.sleep(0.1)
