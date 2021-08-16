# Minecraft Gesture Controller
#
# Written by <jenfoxbot@gmail.com>
# MIT License V.asof2018
# Also coffee/beer ware license :)
# Super awesome thanks to:
# Richard Albritton, Tony DiCola, John Parker
# All the awesome people who wrote the libraries

# Libraries


import time

# Libraries for accelerometer
import adafruit_lis3dh
import board
import busio
# General purpose libraries
import touchio
# Libraries for HID Keyboard & Mouse
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from adafruit_hid.keycode import Keycode
from adafruit_hid.mouse import Mouse

# CPX Setup
touch_a1 = touchio.TouchIn(board.A1)
touch_a1.threshold = 2000
touch_a2 = touchio.TouchIn(board.A2)
touch_a2.threshold = 2000
touch_a3 = touchio.TouchIn(board.A3)
touch_a3.threshold = 2000
touch_a4 = touchio.TouchIn(board.A4)
touch_a4.threshold = 2000

# Keyboard & Mouse Setup

# The keyboard object!
kbd = Keyboard(usb_hid.devices)
# we're americans :)
layout = KeyboardLayoutUS(kbd)
# The mouse object!
mouse = Mouse(usb_hid.devices)

# Accelerometer Setup

# Initialize Accelerometer
i2c = busio.I2C(board.ACCELEROMETER_SCL, board.ACCELEROMETER_SDA)
lis3dh = adafruit_lis3dh.LIS3DH_I2C(i2c, address=25)
# Set range of accelerometer
# (can be RANGE_2_G, RANGE_4_G, RANGE_8_G or RANGE_16_G).
lis3dh.range = adafruit_lis3dh.RANGE_8_G


# Controller Functions

# A helper to 'remap' an input range to an output range
def Map(x, in_min, in_max, out_min, out_max):
    return int(
        (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min
    )


def Move(upDown_axis, isBackward):
    axis_new = abs(upDown_axis)
    # If you are touching A4, walk backwards, else walk forwards
    if isBackward:
        print("backwards")  # Debugging
        if axis_new > 1.2:  # walk threshold
            if axis_new > 2.5:  # run threshold
                kbd.press(Keycode.LEFT_CONTROL, Keycode.S)
                time.sleep(0.1)
                kbd.release_all()
            else:
                kbd.press(Keycode.S)
                time.sleep(0.1)
            kbd.release_all()
    else:
        if axis_new > 1.2:  # walk threshold
            if axis_new > 2.5:  # run threshold
                kbd.press(Keycode.LEFT_CONTROL)
                time.sleep(0.1)
                kbd.release_all()
            else:
                kbd.press(Keycode.W)
                time.sleep(0.1)
            kbd.release_all()


def Turn(upDown_axis, leftRight_axis, lookUp):
    leftRight_adj = int(leftRight_axis)  # currently z_axis
    upDown_adj = int(upDown_axis)  # currently y_axis

    leftRight_new = Map(leftRight_adj, -3, 3, -100, 100)
    if lookUp and abs(upDown_adj) < 1.2:
        upDown_new = Map(upDown_adj, -1, 1, -100, 100)
    else:
        upDown_new = 0
    if abs(leftRight_new) < 127:
        mouse.move(-leftRight_new, upDown_new)
    else:
        mouse.move(0, 0)


def Jump(upDown_axis):
    upDown = abs(upDown_axis)
    if upDown > 3:
        kbd.press(Keycode.SPACE, Keycode.W)
    kbd.release_all()


def Give(upDown_axis, frontBack_axis):
    frontBack_new = abs(frontBack_axis)
    if abs(upDown_axis) < 1:
        if frontBack_new > 2:
            print("give")
            mouse.click(Mouse.RIGHT_BUTTON)
            mouse.release_all()


def Attack():
    """Attack! By clicking the left mouse button"""
    print("attack")
    mouse.click(Mouse.LEFT_BUTTON)
    time.sleep(0.1)
    mouse.release_all()


def Inventory():
    """Open up inventory, press the E keyboard key"""
    print("inventory")  # Debugging -- view in serial monitor
    kbd.press(Keycode.E)
    time.sleep(0.01)
    kbd.release_all()


def ESC():
    """Escape by pressing the ESCape key"""
    print("ESC")  # Debugging -- view in serial monitor
    kbd.press(Keycode.ESCAPE)
    time.sleep(0.01)
    kbd.release_all()


def readAxes():
    """Convert acceleration from m/s^2 to G, with a delay"""
    x, y, z = lis3dh.acceleration
    time.sleep(0.01)
    return (x / 9.806, y / 9.806, z / 9.806)  # 9.806 m/s^2 per G


# Main Function
while True:
    # Read accelerometer values (in G).  Returns a 3-tuple of x, y, x axis
    pos_x, pos_y, pos_z = readAxes()

    # Read finger pads and act accordingly
    if touch_a1.value:
        Attack()

    if touch_a2.value:
        Inventory()

    if touch_a3.value:
        ESC()

    is_backward = touch_a4.value
    look_up = touch_a4.value

    # Run through the motions! .. literally :)
    Move(pos_y, is_backward)
    Turn(pos_y, pos_z, look_up)
    Jump(pos_y)
    Give(pos_y, pos_x)

    # Small delay to keep things responsive but
    # give time for interrupt processing.
    time.sleep(0.01)

    # Debugging Ahead!!
    # Use the following 2 lines to figure out which
    # axis is upDown, frontBack, or LeftRight
    # and also for debugging!
    # print('x = {}G, y = {}G, z = {}G'.format(x, y, z))
    # time.sleep(0.3)
