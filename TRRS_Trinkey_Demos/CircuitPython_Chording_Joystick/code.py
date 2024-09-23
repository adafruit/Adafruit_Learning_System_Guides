# SPDX-FileCopyrightText: 2024 Bill Binko
# SPDX-License-Identifier: MIT

import time
import array
import board
import digitalio
import keypad
#Custom version of Gamepad compatible w/the XBox Adaptive Controller (XAC)
import xac_gamepad
# pylint: disable=wildcard-import, unused-wildcard-import
from XACsettings import *

#Use Keypad library to read buttons wired between ground and Tip/Ring1
keys = keypad.Keys((board.TIP,board.RING_1), value_when_pressed=False, pull=True)

time.sleep(1.0)
gp = xac_gamepad.XACGamepad()

class RollingAverage:
    def __init__(self, size):
        self.size=size
        self.buffer = array.array('d')
        for _ in range(size):
            self.buffer.append(0.0)
        self.pos = 0
    def addValue(self,val):
        self.buffer[self.pos] = val
        self.pos = (self.pos + 1) % self.size
    def average(self):
        return sum(self.buffer) / self.size

ground = digitalio.DigitalInOut(board.RING_2)
ground.direction=digitalio.Direction.OUTPUT
ground.value = False

ground2 = digitalio.DigitalInOut(board.SLEEVE)
ground2.direction=digitalio.Direction.OUTPUT
ground2.value = False


#Our joystick goes from 0-255 with a center at 128
FORWARD = 0
REVERSE=255
CENTER=128
LEFT=0
RIGHT=255

#These two are how much we should smooth the joystick - higher numbers smooth more but add lag
VERT_AVG_COUNT=8
HOR_AVG_COUNT=8
#We need two Rolling Average Objects to smooth our values
xAvg = RollingAverage(HOR_AVG_COUNT)
yAvg = RollingAverage(VERT_AVG_COUNT)

gp.reset_all()

#Set Initial State variables
leftDown=False
rightDown=False
movingForward = False
joyChanged=False

#main loop - read switches and set joystick output
while True:
    event=keys.events.get()
    #Calculate the rolling average for the X and Y
    lastXAvg = xAvg.average()
    lastYAvg = yAvg.average()
    if event:
        if event.pressed:
            if event.key_number==0:
                leftDown=True
            elif event.key_number==1:
                rightDown=True
        else:
            if event.key_number==0:
                leftDown=False
            elif event.key_number==1:
                rightDown=False

    #At this point, we know whether we need to move the joystick
    #Start with the assumption that we're in the center.
    x=CENTER
    y=CENTER
    #If BOTH are down, we are always moving North
    if leftDown and rightDown:
        movingForward = True
        x=CENTER
        y=FORWARD
    #Simlarly, if neither or down we are stopped
    elif not leftDown and not rightDown:
        movingForward = False
        x=CENTER
        y=CENTER
    #Otherwise our direction depends on whether we WERE movingForward last iteration
    elif movingForward:
        #If So, we are moving NorthWest or NorthEast
        if leftDown:
            x=LEFT
            y=FORWARD
        elif rightDown:
            x=RIGHT
            y=FORWARD
    else:
        #If not, we are moving West or East
        if leftDown:
            x=LEFT
            y=CENTER
        elif rightDown:
            x=RIGHT
            y=CENTER
    #We know x and y, so do some smoothing
    xAvg.addValue(x)
    yAvg.addValue(y)
    #We need to send integers so calculate the average and truncate it
    newX = int(xAvg.average())
    newY = int(yAvg.average())
    #We only call move_joysticks if one of the values has changed from last time
    if (newX != lastXAvg or newY != lastYAvg):
        gp.move_joysticks(x=newX,y=newY)
        print((newX, newY,))
    #Sleep to avoid overwhelming the XAC
    time.sleep(0.05)
