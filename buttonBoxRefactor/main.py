#!/usr/bin/env python3
import boardStateDriver
from time import sleep
from board import SCL, SDA
import busio
from adafruit_neotrellis.neotrellis import NeoTrellis
print('started')
# create the i2c object for the trellis
i2c_bus = busio.I2C(SCL, SDA)
# create the trellis object with the given i2c object
theTrellis = NeoTrellis(i2c_bus)
# create an instance of the driver for the board which handles logical updates,
# instantiate it with a blank board
boardDriver = boardStateDriver.boardState(16)
#
# assign what function should be called when the rising edge of
# a pushed button event occurs by adding it to the callbacks list
# this will always automatically pass an event 
# object created by the board to the assigned function
for i in range(16):
    theTrellis.activate_key(i, NeoTrellis.EDGE_RISING)
    theTrellis.callbacks[i] = boardDriver.boardLogic
# main program loop where all major code execution should happen
boardDriver.choseMode()
while True:
    # always wait 0.02 seconds before reading/writing to the trellis because
    # it can only update every 17 milliseconds
    sleep(0.02)
    if boardDriver.mode == 'sim':
        boardDriver.animation()
    # redraw the physical board by reading from the logical board
    for i in range(16):
        theTrellis.pixels[i] = boardDriver.getColor(i)
        # run all callbacks triggered by button presses via the sync method
    if boardDriver.condition == True:
        boardDriver.clearBoard()
        boardDriver.condition = False
        sleep(3)
    theTrellis.sync()
