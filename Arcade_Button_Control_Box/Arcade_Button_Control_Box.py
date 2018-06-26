import time

import digitalio
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode
import board

# A simple neat keyboard demo in circuitpython

# The button pins we'll use, each will have an internal pullup
buttonpins = [board.D12, board.D11, board.D10, board.D9, board.D6, board.D5]
ledpins = [board.A0, board.A1, board.A2, board.A3, board.A4, board.A5]

# The keycode sent for each button, will be paired with a control key
buttonkeys = [Keycode.A, Keycode.B, Keycode.C, Keycode.D, Keycode.E, Keycode.F]
controlkey = Keycode.LEFT_CONTROL

# the keyboard object!
kbd = Keyboard()
# our array of button objects
buttons = []
leds = []

# make all pin objects, make them inputs w/pullups
for pin in buttonpins:
    button = digitalio.DigitalInOut(pin)
    button.direction = digitalio.Direction.INPUT
    button.pull = digitalio.Pull.UP
    buttons.append(button)
for pin in ledpins:
    led = digitalio.DigitalInOut(pin)
    led.direction = digitalio.Direction.OUTPUT
    leds.append(led)

led = digitalio.DigitalInOut(D13)
led.switch_to_output()

print("Waiting for button presses")

while True:
    # check each button
    for button in buttons:
        if not button.value:  # pressed?
            i = buttons.index(button)
            leds[i].value = True

            print("Button #%d Pressed" % i)

            # turn on the LED
            led.value = True

            while not button.value:
                pass  # wait for it to be released!
            # type the keycode!
            k = buttonkeys[i]  # get the corresp. keycode
            kbd.press(controlkey, k)
            kbd.release_all()

            # turn off the LED
            led.value = False
            leds[i].value = False

    time.sleep(0.01)
