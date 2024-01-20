# SPDX-FileCopyrightText: 2023 John Park for Adafruit Industries
# SPDX-License-Identifier: MIT
# PowerWash Simulator controller
"""
Hardware:
# QT Py RP2040, BNO055, Wiichuck adapter, Piezo driver on D10 ('MO' pin on silk)
 User control:
    nozzle heading/roll (sensor is mounted "sideways" in washer handle) = mouse x/y
    nozzle tap/shake = next nozzle tip
    wii C button (while level) = rotate nozzle tip
    wii Z button = trigger water
    wii joystick = WASD
    wii roll right = change stance stand/crouch/prone
    wii roll left = jump
    wii pitch up + C button = set target angle offset
    wii pitch down = show dirt
    wii pitch down + C button = toggle aim mode
"""

import time
import math
import board
from simpleio import map_range, tone
import adafruit_bno055
import usb_hid
from adafruit_hid.mouse import Mouse
from adafruit_hid.keycode import Keycode
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from adafruit_nunchuk import Nunchuk

# ===========================================
# constants
DEBUG = False
CURSOR = True  # use to toggle cursor movment during testing/use
SENSOR_PACKET_FACTOR = 10  # Ratio of BNo055 data packets per Wiichuck packet
HORIZONTAL_RATE = 127  # mouse x speed
VERTICAL_RATE = 63  # mouse y speed
WII_C_KEY_1 = Keycode.R  # rotate nozzle
WII_C_KEY_2 = Keycode.C  # aim mode
WII_PITCH_UP = 270  # value to trigger wiichuk up state
WII_PITCH_DOWN = 730  # value to trigger wiichuck down state
WII_ROLL_LEFT = 280  # value to trigger wiichuck left state
WII_ROLL_RIGHT = 740  # value to trigger wiichuck right state
TAP_THRESHOLD = 6  # Tap sensitivity threshold; depends on the physical sensor mount
TAP_DEBOUNCE = 0.3  # Time for accelerometer to settle after tap (seconds)

# ===========================================
# Instantiate I2C interface connection
# i2c = board.I2C()  # For board.SCL and board.SDA
i2c = board.STEMMA_I2C()  # For the built-in STEMMA QT connection

# ===========================================
# setup USB HID mouse and keyboard
mouse = Mouse(usb_hid.devices)
keyboard = Keyboard(usb_hid.devices)
layout = KeyboardLayoutUS(keyboard)

# ===========================================
# wii nunchuk setup
wiichuk = Nunchuk(i2c)

# ===========================================
# Instantiate the BNo055 sensor
sensor = adafruit_bno055.BNO055_I2C(i2c)
sensor.mode = 0x0C  # Set the sensor to NDOF_MODE

# ===========================================
# beep function
def beep(freq=440, duration=0.2):
    """Play the piezo element for duration (sec) at freq (Hz).
    This is a blocking method."""
    tone(board.D10, freq, duration)

# ===========================================
# debug print function
def printd(line):
    """Prints a string if DEBUG is True."""
    if DEBUG:
        print(line)

# ===========================================
# euclidean distance function
def euclidean_distance(reference, measured):
    """Calculate the Euclidean distance between reference and measured points
    in a universe. The point position tuples can be colors, compass,
    accelerometer, absolute position, or almost any other multiple value data
    set.
    reference: A tuple or list of reference point position values.
    measured: A tuple or list of measured point position values."""
    # Create list of deltas using list comprehension
    deltas = [(reference[idx] - count) for idx, count in enumerate(measured)]
    # Resolve squared deltas to a Euclidean difference and return the result
    # pylint:disable=c-extension-no-member
    return math.sqrt(sum([d ** 2 for d in deltas]))

# ===========================================
# BNO055 offsets
# Preset the sensor calibration offsets
# User sets this up once for geographic location using `bno055_calibrator.py` in library examples
sensor.offsets_magnetometer = (198, 238, 465)
sensor.offsets_gyroscope = (-2, 0, -1)
sensor.offsets_accelerometer = (-28, -5, -29)
printd(f"offsets_magnetometer set to: {sensor.offsets_magnetometer}")
printd(f"offsets_gyroscope set to: {sensor.offsets_gyroscope}")
printd(f"offsets_accelerometer set to: {sensor.offsets_accelerometer}")

# ===========================================
# controller states
wii_roll_state = 1  # roll left 0, center 1, roll right 2
wii_pitch_state = 1  # pitch down 0, center 1, pitch up 2
wii_last_roll_state = 1
wii_last_pitch_state = 1
c_button_state = False
z_button_state = False

sensor_packet_count = 0  # Initialize the BNo055 packet counter

print("PowerWash controller ready, point at center of screen for initial offset:")
beep(400, 0.1)
beep(440, 0.2)
time.sleep(3)
# The target angle offset used to reorient the wand to point at the display
#pylint:disable=(unnecessary-comprehension)
target_angle_offset = [angle for angle in sensor.euler]
beep(220, 0.4)
print("......reoriented", target_angle_offset)


while True:
    # ===========================================
    # BNO055
    # Get the Euler angle values from the sensor
    # The Euler angle limits are: +180 to -180 pitch, +360 to -360 heading, +90 to -90 roll
    sensor_euler = sensor.euler
    sensor_packet_count += 1  # Increment the BNo055 packet counter
    # Adjust the Euler angle values with the target_position_offset
    heading, roll, pitch = [
                            position - target_angle_offset[idx] for idx,
                            position in enumerate(sensor_euler)
    ]
    printd(f"heading {heading}, roll {roll}")
    # Scale the heading for horizontal movement range
    # horizontal_mov = map_range(heading, 220, 260, -30.0, 30.0)
    horizontal_mov = int(map_range(heading, -16, 16, HORIZONTAL_RATE*-1, HORIZONTAL_RATE))
    printd(f"mouse x: {horizontal_mov}")

    # Scale the roll for vertical movement range
    vertical_mov = int(map_range(roll, 9, -9, VERTICAL_RATE*-1, VERTICAL_RATE))
    printd(f"mouse y: {vertical_mov}")
    if CURSOR:
        mouse.move(x=horizontal_mov)
        mouse.move(y=vertical_mov)

    # ===========================================
    # sensor packet ratio
    # Read the wiichuck every "n" times the BNo055 is read
    if sensor_packet_count >= SENSOR_PACKET_FACTOR:
        sensor_packet_count = 0  # Reset the BNo055 packet counter

        # ===========================================
        # wiichuck joystick
        joy_x, joy_y = wiichuk.joystick
        printd(f"joystick = {wiichuk.joystick}")
        if joy_x < 25:
            keyboard.press(Keycode.A)
        else:
            keyboard.release(Keycode.A)

        if joy_x > 225:
            keyboard.press(Keycode.D)
        else:
            keyboard.release(Keycode.D)

        if joy_y > 225:
            keyboard.press(Keycode.W)
        else:
            keyboard.release(Keycode.W)

        if joy_y < 25:
            keyboard.press(Keycode.S)
        else:
            keyboard.release(Keycode.S)

        # ===========================================
        # wiichuck accel
        wii_roll, wii_pitch, wii_az = wiichuk.acceleration
        printd(f"roll:, {wii_roll}, pitch:, {wii_pitch}")
        if wii_roll <= WII_ROLL_LEFT:
            wii_roll_state = 0
            if wii_last_roll_state != 0:
                keyboard.press(Keycode.SPACE)  # jump
                wii_last_roll_state = 0
        elif WII_ROLL_LEFT < wii_roll < WII_ROLL_RIGHT:  # centered
            wii_roll_state = 1
            if wii_last_roll_state != 1:
                keyboard.release(Keycode.LEFT_CONTROL)
                keyboard.release(Keycode.SPACE)
                wii_last_roll_state = 1
        else:
            wii_roll_state = 2
            if wii_last_roll_state != 2:
                keyboard.press(Keycode.LEFT_CONTROL)  # change stance
                wii_last_roll_state = 2

        if wii_pitch <= WII_PITCH_UP:  # up used as modifier
            wii_pitch_state = 0
            if wii_last_pitch_state != 0:
                beep(freq=660)
                wii_last_pitch_state = 0
        elif WII_PITCH_UP < wii_pitch < WII_PITCH_DOWN:  # level
            wii_pitch_state = 1
            if wii_last_pitch_state != 1:
                wii_last_pitch_state = 1
        else:
            wii_pitch_state = 2  # down sends command and is modifier
            if wii_last_pitch_state != 2:
                keyboard.send(Keycode.TAB)
                beep(freq=110)
                wii_last_pitch_state = 2

        # ===========================================
        # wiichuck buttons
        if wii_pitch_state == 0:  # button use when wiichuck is held level
            if wiichuk.buttons.C and c_button_state is False:
                target_angle_offset = [angle for angle in sensor_euler]
                beep()
                beep()
                c_button_state = True
            if not wiichuk.buttons.C and c_button_state is True:
                c_button_state = False

        elif wii_pitch_state == 1:  # level
            if wiichuk.buttons.C and c_button_state is False:
                keyboard.press(WII_C_KEY_1)
                c_button_state = True
            if not wiichuk.buttons.C and c_button_state is True:
                keyboard.release(WII_C_KEY_1)
                c_button_state = False

        elif wii_pitch_state == 2:  # down
            if wiichuk.buttons.C and c_button_state is False:
                keyboard.press(WII_C_KEY_2)
                c_button_state = True
            if not wiichuk.buttons.C and c_button_state is True:
                keyboard.release(WII_C_KEY_2)
                c_button_state = False

        if wiichuk.buttons.Z and z_button_state is False:
            mouse.press(Mouse.LEFT_BUTTON)
            z_button_state = True
        if not wiichuk.buttons.Z and z_button_state is True:
            mouse.release(Mouse.LEFT_BUTTON)
            z_button_state = False

    # ===========================================
    # BNO055 tap detection
    # Detect a single tap on any axis of the BNo055 accelerometer
    accel_sample_1 = sensor.acceleration  # Read one sample
    accel_sample_2 = sensor.acceleration  # Read the next sample
    if euclidean_distance(accel_sample_1, accel_sample_2) >= TAP_THRESHOLD:
        # The difference between two consecutive samples exceeded the threshold ()
        # (equivalent to a high-pass filter)
        mouse.move(wheel=1)
        printd("SINGLE tap detected")
        beep()
        time.sleep(TAP_DEBOUNCE)  # Debounce delay
