# CircuitPython for the Adafruit Learning System Tutorial
# Universal Marionette Kit
# Project by Dano Wall, code by Mike Barela for Adafruit Industries
# MIT License
import time
from adafruit_crickit import crickit

# For signal control, we'll chat directly with seesaw, use 'ss' to shorted typing!
ss = crickit.seesaw

# four buttons with pullups, connect to ground to activate
BUTTON_1 = crickit.SIGNAL1  # button #1 connected to signal port 1 & ground
BUTTON_2 = crickit.SIGNAL2  # button #2 connected to signal port 2 & ground
BUTTON_3 = crickit.SIGNAL3  # button #3 connected to signal port 3 & ground
BUTTON_4 = crickit.SIGNAL4  # button #4 connected to signal port 4 & ground

ss.pin_mode(BUTTON_1, ss.INPUT_PULLUP)  # Set as input with a pullup resistor
ss.pin_mode(BUTTON_2, ss.INPUT_PULLUP)
ss.pin_mode(BUTTON_3, ss.INPUT_PULLUP)
ss.pin_mode(BUTTON_4, ss.INPUT_PULLUP)

while True:
    if not ss.digital_read(BUTTON_1):
        print("Button 1 pressed")
        crickit.servo_1.angle = 40
        time.sleep(0.1)
    else:
        crickit.servo_1.angle = 140
    if not ss.digital_read(BUTTON_2):
        print("Button 2 pressed")
        crickit.servo_2.angle = 140
        time.sleep(0.1)
    else:
        crickit.servo_2.angle = 40
    if not ss.digital_read(BUTTON_3):
        print("Button 3 pressed")
        crickit.servo_3.angle = 40
        time.sleep(0.1)
    else:
        crickit.servo_3.angle = 140
    if not ss.digital_read(BUTTON_4):
        print("Button 4 pressed")
        crickit.servo_4.angle = 140
        time.sleep(0.1)
    else:
        crickit.servo_4.angle = 40
