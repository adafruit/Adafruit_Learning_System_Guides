# Nintendo R.O.B. control with Accelerometer, code in CircuitPython
# Using an Adafruit Circuit Playground Express board with an IR LED
# Anne Barela for Adafruit Industries, MIT License, May, 2018
# Acknowledgement to info at http://atariage.com/forums/topic/177286
# -any-interest-in-nes-rob-homebrews/ and Limor Ladyada Fried

import time
import gc
from digitalio import DigitalInOut, Direction
from adafruit_circuitplayground.express import cpx
import board

# Commands, each 8 bit command is preceded by the 5 bit Init sequence
Init = [0, 0, 0, 1, 0]            # This must precede any command
Up = [1, 0, 1, 1, 1, 0, 1, 1]     # Move arms/body down
Down = [1, 1, 1, 1, 1, 0, 1, 1]   # Move arms/body up
Left = [1, 0, 1, 1, 1, 0, 1, 0]   # Twist body left
Right = [1, 1, 1, 0, 1, 0, 1, 0]  # Twist body right
Close = [1, 0, 1, 1, 1, 1, 1, 0]  # Close arms
Open = [1, 1, 1, 0, 1, 1, 1, 0]   # Open arms
Test = [1, 1, 1, 0, 1, 0, 1, 1]   # Turns R.O.B. head LED on

print("R.O.B. Start")

# Circuit Playground Express IR LED Setup
IRled = DigitalInOut(board.REMOTEOUT)
IRled.direction = Direction.OUTPUT

# This function performs the LED flashing of a passed command
# Note timing is very tight. Machine instructions are 2-5 ms or so
# so that is why the time for cycles doing work is < 16.66667 ms (1/60)
# Each pulse/space is 1.5 milliseconds out of 16.7 total ms (NTSC)

def IR_Command(cmd):
    gc.collect()                     # collect memory now
    # Output initialization and then command cmd
    for val in Init+cmd:             # For each value in initial+command
        if val:                      # if it's a one, flash the IR LED
            IRled.value = True       # Turn IR LED turn on for 1.5 ms
            time.sleep(0.0015)       # 1.5 ms on
            IRled.value = False      # Turn IR LED off for 15 ms
            time.sleep(0.0150)       # 15 ms
        else:
            time.sleep(0.0167)       # 1 cycle turn off

while True:                          # Main Loop poll switches, do commands
    x, y, z = cpx.acceleration       # Read accelerometer
    print((x, y, z))                 # Print for debug
    if x > 5 and y > -8:             # Clockwise from back
        IR_Command(Right)            # Turn Right
    if x < -5 and y > -8:            # Counterclockwise from back
        IR_Command(Left)             # Turn Left
    if x > 1 and y < -10:            # Move direction of USB
        IR_Command(Up)               # Body up
    if x < -1 and y < -10:           # Move in direction of battery con
        IR_Command(Down)             # Body Down
    if cpx.button_a:
        IR_Command(Open)             # Button A opens arms
    if cpx.button_b:
        IR_Command(Close)            # Button B closes arms
    if cpx.switch:                   # Toggle switch turns "test" on
        IR_Command(Test)             # which is the LED on R.O.B.s head
    time.sleep(0.1)
