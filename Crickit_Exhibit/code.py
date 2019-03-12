"""
Crickit Exhibit
Project by Dano Wall and Isaac Wellish
Code by Isaac Wellish
The Crickit Exhibit demonstrates almost all of the capabilities
which CRICKIT can offer in one project
"""

# Functions:
#1. Hit a button to trigger a solenoid
#2. Hit a button to turn on an electromagnet
#3. Touch conductive tape to trigger a neopixel animation
#4. Turn a potentiometer to control a servo
#5. Shine light on the CPX to trigger and change the speed of a DC motor
#6. Hit both buttons to trigger a sound from the speaker!

import time
from adafruit_crickit import crickit
import board
import neopixel
from analogio import AnalogIn
from simpleio import map_range, tone

# RGB values
RED = (255, 0, 0)
YELLOW = (255, 150, 0)
GREEN = (0, 255, 0)
CYAN = (0, 255, 255)
BLUE = (0, 0, 255)
PURPLE = (180, 0, 255)

# For signal control, we'll chat directly with seesaw, use 'ss' to shorted typing!
# create seesaw object
ss = crickit.seesaw

# Two buttons are pullups, connect to ground to activate
BUTTON_1 = crickit.SIGNAL1
BUTTON_2 = crickit.SIGNAL2

ss.pin_mode(BUTTON_1, ss.INPUT_PULLUP)
ss.pin_mode(BUTTON_2, ss.INPUT_PULLUP)

#solenoid at drive spot 1
crickit.drive_1.frequency = 1000

#electromagnet at drive spot 2
crickit.drive_2.frequency = 1000

# initialize NeoPixels to num_pixels
num_pixels = 30

# The following line sets up a NeoPixel strip on Crickit CPX pin A1
pixels = neopixel.NeoPixel(board.A1, num_pixels, brightness=0.3, auto_write=False)

#sleep var for pushing both buttons
SLEEP_DELAY = 0.1

# NeoPixel function
def color_chase(color, wait):
    for i in range(num_pixels):
        pixels[i] = color
        time.sleep(wait)
        pixels.show()
    time.sleep(0.5)

# potentiometer connected to signal #3
pot = crickit.SIGNAL8

# initialize the light sensor on the CPX and the DC motor
light_in = AnalogIn(board.LIGHT)

while True:

    # button + solenoid & electromagnet code
    # button 1 - solenoid on
    if not ss.digital_read(BUTTON_1):
        print("Button 1 pressed")
        crickit.drive_1.fraction = 1.0  # all the way on
        time.sleep(0.01)
        crickit.drive_1.fraction = 0.0  # all the way off
        time.sleep(0.5)
    else:
        crickit.drive_1.fraction = 0.0

    # button 2 electromagnet on
    if not ss.digital_read(BUTTON_2):
        print("Button 2 pressed")
        crickit.drive_2.fraction = 1.0  # all the way on
        time.sleep(0.5)
    else:
        crickit.drive_2.fraction = 0.0  # all the way off

    # Capacitive touch + neopixel code
    touch_raw_value = crickit.touch_1.raw_value

    if touch_raw_value>800:
        print("chase")
        color_chase(PURPLE, 0.1)
    else:
        pixels.fill((0,0,0))
        pixels.show()

    # potentiomter + servo

    # uncomment this line to see the values of the pot
    # print((ss.analog_read(pot),))
    # time.sleep(0.25)

    # maps the range of the pot to the range of the servo
    angle = map_range(ss.analog_read(pot), 0, 1023, 180, 0)

    # sets the servo equal to the relative position on the pot
    crickit.servo_1.angle = angle

    # Light sensor + DC motor

    # uncomment to see values of light
    # print(light_in.value)
    # time.sleep(0.5)

    # reads the on-board light sensor and graphs the brighness with NeoPixels
    # light value remaped to motor speed
    peak = map_range(light_in.value, 3000, 62000, 0, 1)

    # DC motor
    crickit.dc_motor_1.throttle = peak  # full speed forward

    # hit both buttons to trigger noise
    if not ss.digital_read(BUTTON_1) and not ss.digital_read(BUTTON_2):
        print("Buttons 1 and 2 pressed")
        for f in (262, 294, 330, 349, 392, 440, 494, 523):
            tone(board.A0, f, 0.25)
            time.sleep(SLEEP_DELAY)
