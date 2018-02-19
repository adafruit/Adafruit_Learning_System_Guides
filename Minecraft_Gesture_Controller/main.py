###############################################
# Minecraft Gesture Controller
# 
#Written by <jenfoxbot@gmail.com>
# MIT License V.asof2018
# Also coffee/beer ware license :)
#Super awesome thanks to:
# Richard Albritton, Tony DiCola, John Parker
# All the awesome people who wrote the libraries
################################################

##########################
##        Libraries     ##
##########################
import touchio
import board
import busio
import time
#Libraries for HID Keyboard & Mouse
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from adafruit_hid.mouse import Mouse
#Libraries for accelerometer
import adafruit_lis3dh

#######################
#     CPX Setup       #
#######################
pin1 = board.A1
pin2 = board.A2
pin3 = board.A3
pin4 = board.A4

############################
# Keyboard & Mouse Setup   #
############################
# The keyboard object!
kbd = Keyboard()
# we're americans :)
layout = KeyboardLayoutUS(kbd)
#The mouse object! 
mouse = Mouse()

#######################
# Accelerometer Setup #
#######################
#Initialize Accelerometer
i2c = busio.I2C(board.ACCELEROMETER_SCL, board.ACCELEROMETER_SDA)
lis3dh = adafruit_lis3dh.LIS3DH_I2C(i2c, address=25)
# Set range of accelerometer (can be RANGE_2_G, RANGE_4_G, RANGE_8_G or RANGE_16_G).
lis3dh.range = adafruit_lis3dh.RANGE_8_G

###########################
## Controller Functions  ##
###########################
def Map(x, in_min, in_max, out_min, out_max):
    return int((x - in_min)*(out_max - out_min) / (in_max - in_min) + out_min)

def Move(upDown_axis, isBackward): 
    axis_new = abs(upDown_axis)
    #If you are touching A4, walk backwards, else walk forwards
    if isBackward:
        print('backwards') #Debugging
        if (axis_new > 1.2): #walk threshold
            if(axis_new > 2.5): #run threshold
                kbd.press(Keycode.LEFT_CONTROL, Keycode.S)
                time.sleep(0.1)
                kbd.release_all()
            else:
                kbd.press(Keycode.S)
                time.sleep(0.1)
            kbd.release_all()
    else:
         if (axis_new > 1.2): #walk threshold
            if(axis_new > 2.5): #run threshold
                kbd.press(Keycode.LEFT_CONTROL)
                time.sleep(0.1)
                kbd.release_all()
            else:
                kbd.press(Keycode.W)
                time.sleep(0.1)
            kbd.release_all()
        
def Turn(upDown_axis, frontBack_axis, leftRight_axis, lookUp):
    leftRight_adj = int(leftRight_axis) #currently z_axis
    upDown_adj = int(upDown_axis) #currently y_axis

    leftRight_new = Map(leftRight_adj, -3, 3, -100, 100)
    if(lookUp and abs(upDown_adj) < 1.2):
        upDown_new = Map(upDown_adj, -1, 1, -100, 100)
    else:
        upDown_new = 0
    if abs(leftRight_new) < 127:  
        mouse.move(-leftRight_new, upDown_new)
    else:
        mouse.move(0, 0)

def Jump(upDown_axis):
    upDown = abs(upDown_axis)
    if(upDown > 3):
        kbd.press(Keycode.SPACE, Keycode.W)
    kbd.release_all()

def Give(upDown_axis, frontBack_axis):
    frontBack_new = abs(frontBack_axis)
    if abs(upDown_axis) < 1:
        if(frontBack_new > 2):
            print('give')
            mouse.click(Mouse.RIGHT_BUTTON)
            mouse.release_all()

def Attack():
    print('attack')
    mouse.click(Mouse.LEFT_BUTTON)
    time.sleep(0.1)
    mouse.release_all()

def Inventory():
    print('inventory') #Debugging -- view in serial monitor
    kbd.press(Keycode.E)
    time.sleep(0.01)
    kbd.release_all()

def ESC():
    print('ESC') #Debugging -- view in serial monitor
    kbd.press(Keycode.ESCAPE)
    time.sleep(0.01)
    kbd.release_all()

def touch(pin):  
    touch = touchio.TouchIn(pin)
    touch.threshold = 2000
    rawValue = touch.raw_value
    if touch.value:
        touchTrig = True
    else:
        touchTrig = False
    return touchTrig
    touch.deinit()

def readAxes():
    x_axis, y_axis, z_axis = lis3dh.acceleration
    x = x_axis / 9.806
    y = y_axis / 9.806
    z = z_axis / 9.806
    time.sleep(0.01)
    return x, y, z

###########################
##     Main Function     ## 
###########################
def __main__():
    while True:
    # Read accelerometer values (in m / s ^ 2).  Returns a 3-tuple of x, y, x axis
        x, y, z = readAxes()
    #Read finger pads and act accordingly
        if touch(pin1):
            Attack()
        if touch(pin2):
            Inventory()
        if touch(pin3):
            ESC()
        isBackward = touch(pin4)
        lookUp = touch(pin4)
    #Run through the motions! .. literally :)
        Move(y, isBackward)
        Turn(y, x, z, lookUp)
        Jump(y)
        Give(y,x)

    # Small delay to keep things responsive but give time for interrupt processing.
        time.sleep(0.01)

## Debugging Ahead!! ##
#Use the following 2 lines to figure out which axis is upDown, frontBack, or LeftRight
#   and also for debugging!
    #print('x = {}G, y = {}G, z = {}G'.format(x, y, z))
    #time.sleep(0.3)


__main__()
