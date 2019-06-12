"""
A CircuitPython 'multimedia' dial demo
Uses a ItsyBitsy M0 + Rotary Encoder -> HID keyboard out with neopixel ring
"""

import time
import board
from digitalio import DigitalInOut, Direction, Pull
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode
from adafruit_hid.consumer_control import ConsumerControl
from adafruit_hid.consumer_control_code import ConsumerControlCode
import neopixel

DOT_COLOR = 0xFF0000              # set to your favorite webhex color
PRESSED_DOT_COLOR = 0x008080      # set to your second-favorite color
LIT_TIMEOUT = 15                  # after n seconds, turn off ring

# NeoPixel LED ring on pin D1
# Ring code will auto-adjust if not 16 so change to any value!
ring = neopixel.NeoPixel(board.D5, 16, brightness=0.2)
dot_location = 0  # what dot is currently lit

# Encoder button is a digital input with pullup on D9
button = DigitalInOut(board.D9)
button.direction = Direction.INPUT
button.pull = Pull.UP

# Rotary encoder inputs with pullup on D10 & D11
rot_a = DigitalInOut(board.D10)
rot_a.direction = Direction.INPUT
rot_a.pull = Pull.UP
rot_b = DigitalInOut(board.D11)
rot_b.direction = Direction.INPUT
rot_b.pull = Pull.UP

# Used to do HID output, see below
kbd = Keyboard()

# time keeper, so we know when to turn off the LED
timestamp = time.monotonic()

######################### MAIN LOOP ##############################

# the counter counts up and down, it can roll over! 16-bit value
encoder_counter = 0
# direction tells you the last tick which way it went
encoder_direction = 0

# constants to help us track what edge is what
A_POSITION = 0
B_POSITION = 1
UNKNOWN_POSITION = -1  # initial state so we know if something went wrong

rising_edge = falling_edge = UNKNOWN_POSITION

# get initial/prev state and store at beginning
last_button = button.value
rotary_prev_state = [rot_a.value, rot_b.value]

while True:
    # reset encoder and wait for the next turn
    encoder_direction = 0

    # take a 'snapshot' of the rotary encoder state at this time
    rotary_curr_state = [rot_a.value, rot_b.value]

    if rotary_curr_state != rotary_prev_state:
        #print("Changed")
        if rotary_prev_state == [True, True]:
            # we caught the first falling edge!
            if not rotary_curr_state[A_POSITION]:
                #print("Falling A")
                falling_edge = A_POSITION
            elif not rotary_curr_state[B_POSITION]:
                #print("Falling B")
                falling_edge = B_POSITION
            else:
                # uhh something went deeply wrong, lets start over
                continue

        if rotary_curr_state == [True, True]:
            # Ok we hit the final rising edge
            if not rotary_prev_state[B_POSITION]:
                rising_edge = B_POSITION
                # print("Rising B")
            elif not rotary_prev_state[A_POSITION]:
                rising_edge = A_POSITION
                # print("Rising A")
            else:
                # uhh something went deeply wrong, lets start over
                continue

            # check first and last edge
            if (rising_edge == A_POSITION) and (falling_edge == B_POSITION):
                encoder_counter -= 1
                encoder_direction = -1
                print("%d dec" % encoder_counter)
            elif (rising_edge == B_POSITION) and (falling_edge == A_POSITION):
                encoder_counter += 1
                encoder_direction = 1
                print("%d inc" % encoder_counter)
            else:
                # (shrug) something didn't work out, oh well!
                encoder_direction = 0

            # reset our edge tracking
            rising_edge = falling_edge = UNKNOWN_POSITION

    rotary_prev_state = rotary_curr_state

    # Check if rotary encoder went up
    if encoder_direction == 1:
        ConsumerControl().send(ConsumerControlCode.VOLUME_DECREMENT) #Turn Down Volume
    #    kbd.press(Keycode.LEFT_ARROW)
    #    kbd.release_all()
    # Check if rotary encoder went down
    if encoder_direction == -1:
        ConsumerControl().send(ConsumerControlCode.VOLUME_INCREMENT) #Turn Up Volume
    #    kbd.press(Keycode.RIGHT_ARROW)
    #    kbd.release_all()
    # Button was 'just pressed'
    if (not button.value) and last_button:
        print("Button pressed!")
        kbd.press(Keycode.SPACE) #Keycode for spacebar
        kbd.release_all()
        ring[dot_location] = PRESSED_DOT_COLOR # show it was pressed on ring
        timestamp = time.monotonic()        # something happened!
    elif button.value and (not last_button):
        print("Button Released!")
        # kbd.press(Keycode.SHIFT, Keycode.SIX)
        # kbd.release_all()
        ring[dot_location] = DOT_COLOR      # show it was released on ring
        timestamp = time.monotonic()        # something happened!
    last_button = button.value

    if encoder_direction != 0:
        timestamp = time.monotonic()        # something happened!
        # spin neopixel LED around!
        previous_location = dot_location
        dot_location += encoder_direction   # move dot in the direction
        dot_location += len(ring)           # in case we moved negative, wrap around
        dot_location %= len(ring)
        if button.value:
            ring[dot_location] = DOT_COLOR  # turn on new dot
        else:
            ring[dot_location] = PRESSED_DOT_COLOR # turn on new dot
        ring[previous_location] = 0         # turn off previous dot

    if time.monotonic() > timestamp + LIT_TIMEOUT:
        ring[dot_location] = 0   # turn off ring light temporarily
