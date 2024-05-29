# SPDX-FileCopyrightText: 2024 Bill Binko
# SPDX-License-Identifier: MIT

import time
import board
import analogio
import digitalio
import usb_hid
from adafruit_hid.mouse import Mouse
# pylint: disable=wildcard-import, line-too-long
#import some settings that are specific to joystick/platform
from settings import *

#Calculated value from imported settings
centerVert = int((highVert - lowVert)/2.0)
deadVert = abs((highVert - lowVert)*deadPct)

centerHor = int((highHor - lowHor)/2.0)
deadHor = abs((highHor - lowHor)*deadPct)

#Create a HID Mouse device
mouse = Mouse(usb_hid.devices)

#Setup the RING_2 as Ground
ground = digitalio.DigitalInOut(board.RING_2)
ground.direction=digitalio.Direction.OUTPUT
ground.value = False
#And SLEEVE as VCC (3.3V)
vcc = digitalio.DigitalInOut(board.SLEEVE)
vcc.direction=digitalio.Direction.OUTPUT
vcc.value = True

#setup the switch on the tip to detect a plug being inserted
switch = digitalio.DigitalInOut(board.TIP_SWITCH)
switch.direction=digitalio.Direction.OUTPUT
switch.value=False
#These values shouldn't need changing w/Joystick changes
switchMin = 500
switchMax = 5000

#Two analog inputs for TIP and RING_1
hor = analogio.AnalogIn(board.TIP)
vert = analogio.AnalogIn(board.RING_1)

#A convenience cunction similar to Arduino's mapping function
def range_map(value, in_min, in_max, out_min, out_max):
    return int(max(out_min,min(out_max,(value - in_min) * (out_max - out_min) // (in_max - in_min) + out_min)))

#Start Main Loop
while True:
    #Check to be sure cord is plugged in
    switch.value=False #Start with TIP_SWITCH pulled Low
    if hor.value < switchMin: #TIP is pulled Low
        switch.value = True #change TIP_SWITCH pin to high
        if hor.value > switchMax: #TIP is now pulled High
            print("no plug")
            time.sleep(.5) #sleep when there's no plug
            continue

    #Ok, the switch is inserted, start reading/processing joystick motions
    horVal = hor.value
    vertVal = vert.value
#    print((horVal, vertVal,))

    #ignore any motions inside the center dead zone (default 10% of full throw)
    if abs(centerHor - horVal) > deadHor or abs(centerVert - vertVal) > deadVert:
        #map X and Y to the analog inputs (settings.py sets these values)
        mouse_x = range_map(horVal, lowHor, highHor, -maxMouseMove, maxMouseMove)
        mouse_y = range_map(vertVal, lowVert, highVert, -maxMouseMove, maxMouseMove)

        if mouse_x != 0 or mouse_y != 0: #don't bother moving if both 0
            mouse.move(invertHor * mouse_x, invertVert * mouse_y)

    #wait a bit to not flood the USB port
    time.sleep(0.025)
