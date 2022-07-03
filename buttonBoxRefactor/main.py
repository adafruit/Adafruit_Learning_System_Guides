# SPDX-FileCopyrightText: 2022 Cameron Kerley
#
# SPDX-License-Identifier: MIT
#!/usr/bin/env python3
from time import sleep
from board import SCL, SDA
from adafruit_neotrellis.neotrellis import NeoTrellis
import busio
import boardStateDriver
# let users connected via serial know the script started and libs import success
print('started')
# create the i2c object for the trellis
i2c_bus = busio.I2C(SCL, SDA)
# create the trellis object with the given i2c object
theTrellis = NeoTrellis(i2c_bus)
# create an instance of the driver for the board which handles logical updates,
# instantiate it with a blank board
boardDriver = boardStateDriver.boardState(16)
#
# assign what function should be called when the rising edge 
# of a pushed button event occurs by adding it to the callbacks list
# this will always automatically pass an event object created by the board to the assigned function
for i in range(16):
    theTrellis.activate_key(i, NeoTrellis.EDGE_RISING)
    theTrellis.callbacks[i] = boardDriver.boardLogic
# main program loop where all major code execution should happen
boardDriver.choseMode()
while True:
    # during the making of this game i read
    # the trellis can only update every 17 milliseconds i.e. sleep(0.2) every loop
    # however i researched and used debouncing for the driver,
    # Please refer to boardStateDriver.boardLogic() & .debounce()
    if boardDriver.mode == 'sim':
        boardDriver.animation()
    # redraw the physical board by reading from the logical board
    for i in range(16):
        theTrellis.pixels[i] = boardDriver.getColor(i)
    #
    if boardDriver.condition is True:
        boardDriver.clearBoard()
        boardDriver.condition = False
        sleep(3)
    # neotrellis.py uses the following time scale to sync callbacks: N*0.0005
    # this game is n=16 which is only 0.008 secs to sync not 0.17 secs
    # run all callbacks triggered by button presses via the sync method
    theTrellis.sync()
