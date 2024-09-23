# SPDX-FileCopyrightText: 2024 by John Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT
# adapted from Bill Binko's Chording Switches code
'''
Xbox Adaptive Controller USB port joystick
Use a two axis joystick, or combo of pots, soft pots, etc.
wired to TRRS 3.mm plug:
 Tip = X
 Ring 1 = Y
 Ring 2 = GND
 Sleeve = VCC
'''
import time
import array
import board
import analogio
import digitalio
#Custom version of Gamepad compatible w/the XBox Adaptive Controller (XAC)
import xac_gamepad
# pylint: disable=wildcard-import, unused-wildcard-import
from XACsettings import *

time.sleep(1.0)
gp = xac_gamepad.XACGamepad()

class RollingAverage:
    def __init__(self, size):
        self.size=size
        # pylint: disable=c-extension-no-member
        self.buffer = array.array('d')
        for _ in range(size):
            self.buffer.append(0.0)
        self.pos = 0
    def addValue(self,val):
        self.buffer[self.pos] = val
        self.pos = (self.pos + 1) % self.size
    def average(self):
        return sum(self.buffer) / self.size

# Two analog inputs for TIP and RING_1
hor = analogio.AnalogIn(board.TIP)
vert = analogio.AnalogIn(board.RING_1)

# RING_2 as ground
ground = digitalio.DigitalInOut(board.RING_2)
ground.direction=digitalio.Direction.OUTPUT
ground.value = False

# SLEEVE as VCC (3.3V)
vcc = digitalio.DigitalInOut(board.SLEEVE)
vcc.direction=digitalio.Direction.OUTPUT
vcc.value = True

def range_map(value, in_min, in_max, out_min, out_max):
    # pylint: disable=line-too-long
    return int(max(out_min,min(out_max,(value - in_min) * (out_max - out_min) // (in_max - in_min) + out_min)))

# These two are how much we should smooth the joystick - higher numbers smooth more but add lag
VERT_AVG_COUNT=3
HOR_AVG_COUNT=3
#We need two Rolling Average Objects to smooth our values
xAvg = RollingAverage(HOR_AVG_COUNT)
yAvg = RollingAverage(VERT_AVG_COUNT)

gp.reset_all()


while True:
    x = range_map(hor.value, 540, 65000, 0, 255)
    y = range_map(vert.value, 65000, 540, 0, 255)

    #Calculate the rolling average for the X and Y
    lastXAvg = xAvg.average()
    lastYAvg = yAvg.average()

    #We know x and y, so do some smoothing
    xAvg.addValue(x)
    yAvg.addValue(y)
    #We need to send integers so calculate the average and truncate it
    newX = int(xAvg.average())
    newY = int(yAvg.average())

    #We only call move_joysticks if one of the values has changed from last time
    if (newX != lastXAvg or newY != lastYAvg):
        gp.move_joysticks(x=newX,y=newY)
        # print(hor.value, vert.value)  # print debug raw values
        # print((newX, newY,))  # print debug remapped, averaged values
    #Sleep to avoid overwhelming the XAC
    time.sleep(0.05)
