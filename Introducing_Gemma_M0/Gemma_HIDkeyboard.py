# Gemma IO demo - Keyboard emu

import digitalio
import touchio
from board import *
import time
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode

# A simple neat keyboard demo in circuitpython

# The button pins we'll use, each will have an internal pullup
buttonpins = [D2, D0]
# our array of button objects
buttons = []
# One pin will be capacitive touch
ptcbutton = touchio.TouchIn(D1)

# The keycode sent for each button, will be paired with a control key
buttonkeys = [Keycode.A, Keycode.B, Keycode.C]
controlkey = Keycode.SHIFT

# the keyboard object!
kbd = Keyboard()

# make all pin objects, make them inputs w/pullups
for pin in buttonpins:
    button = digitalio.DigitalInOut(pin)
    button.direction = digitalio.Direction.INPUT
    button.pull = digitalio.Pull.UP   
    buttons.append(button)

led = digitalio.DigitalInOut(D13)
led.direction = digitalio.Direction.OUTPUT
 
print("Waiting for button presses")

while True:
    # check each button
    for button in buttons:
        if (not button.value):   # pressed?
            i = buttons.index(button)
            print("Button #%d Pressed" % i)

            # turn on the LED
            led.value = True

            while (not button.value):
                pass  # wait for it to be released!
            # type the keycode!
            k = buttonkeys[i]    # get the corresp. keycode
            kbd.press(controlkey, k)
            kbd.release_all()

            # turn off the LED
            led.value = False
    
    time.sleep(0.01)
