import os
import board
from digitalio import DigitalInOut, Direction
import time
import touchio

# Set this to True to turn the touchpads into a keyboard
ENABLE_KEYBOARD = True

# Used if we do HID output, see below
if ENABLE_KEYBOARD:
    from adafruit_hid.keyboard import Keyboard
    from adafruit_hid.keycode import Keycode
    from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
    import usb_hid
    kbd = Keyboard(usb_hid.devices)
    layout = KeyboardLayoutUS(kbd)

#print(dir(board), os.uname()) # Print a little about ourselves

led = DigitalInOut(board.D13)
led.direction = Direction.OUTPUT

touches = [DigitalInOut(board.CAP0)]
for p in (board.CAP1, board.CAP2, board.CAP3):
    touches.append(touchio.TouchIn(p))

leds = []
for p in (board.LED4, board.LED5, board.LED6, board.LED7):
    led = DigitalInOut(p)
    led.direction = Direction.OUTPUT
    led.value = True
    time.sleep(0.25)
    leds.append(led)
for led in leds:
    led.value = False


cap_touches = [False, False, False, False]

def read_caps():
    t0_count = 0
    t0 = touches[0]
    t0.direction = Direction.OUTPUT
    t0.value = True
    t0.direction = Direction.INPUT
    # funky idea but we can 'diy' the one non-hardware captouch device by hand
    # by reading the drooping voltage on a tri-state pin.
    t0_count = t0.value + t0.value + t0.value + t0.value + t0.value + \
               t0.value + t0.value + t0.value + t0.value + t0.value + \
               t0.value + t0.value + t0.value + t0.value + t0.value
    cap_touches[0] = t0_count > 2
    cap_touches[1] = touches[1].raw_value > 3000
    cap_touches[2] = touches[2].raw_value > 3000
    cap_touches[3] = touches[3].raw_value > 3000
    return cap_touches

while True:
    caps = read_caps()
    print(caps)
    # light up the matching LED
    for i,c in enumerate(caps):
        leds[i].value = c
    if caps[0]:
        if ENABLE_KEYBOARD:
            # Zoom
            kbd.press(Keycode.ALT, Keycode.V)
            kbd.release(Keycode.V)
            time.sleep(0.25)
            kbd.press(Keycode.A)
            kbd.release_all()
    if caps[1]:
        if ENABLE_KEYBOARD:
            # Teams
            # Note that video toggle doesn't work in the web app
            kbd.press(Keycode.CONTROL, Keycode.SHIFT, Keycode.M)
            kbd.release(Keycode.M)
            time.sleep(0.5)
            kbd.press(Keycode.O)
            kbd.release_all()
    if caps[2]:
        if ENABLE_KEYBOARD:
            # Skype
            kbd.press(Keycode.CONTROL, Keycode.M)
            kbd.release(Keycode.M)
            time.sleep(0.5)
            kbd.press(Keycode.SHIFT, Keycode.K)
            kbd.release_all()
    if caps[3]:
        if ENABLE_KEYBOARD:
            # Jitsi
            kbd.press(Keycode.M)
            kbd.release(Keycode.M)
            time.sleep(0.5)
            kbd.press(Keycode.V)
            kbd.release_all()
    time.sleep(.2)